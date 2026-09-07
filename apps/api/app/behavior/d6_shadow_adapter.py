"""D6 shadow adapter (M2). Read-only comparator between the host arbiter and D6Engine.

Dormant unless TRADEVISION_D6_SHADOW=on (default off). Never places orders, never
changes bands, never writes ledgers. All outputs are divergence records for review.

Mapping rules (see docs/plans/D6_M2_M3_MILESTONE_SHEET.md M2-A ledger):
- Directional evidence comes ONLY from the five direction engines, asserted solely
  on the setup direction at exact magnitude (no rescaling). Net-score math makes the
  margin check exact and the minimum-evidence check conservative; disagreement is
  recorded as conflict, never silently zeroed. There is deliberately NO generic
  max(v,0)/max(-v,0) splitter in this module.
- risk_safety / data_quality / liquidity votes NEVER enter evidence (risk/gate channels).
- external_ai is excluded (reviewer-only; D6 has no reviewer channel).
- Execution risk comes from the live v1.73 slippage_risk via the spine receipt
  (documented mapping); it is never defaulted or borrowed from event risk.
- LIQUIDITY_RISK table, costs, scavenged quote/portfolio scaffolding, and policy
  thresholds below are versioned ADAPTER judgment (ADAPTER_VERSION), reviewable
  comparator tuning — not market constants, not production thresholds.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from tradevision_d6.engine import D6Engine
from tradevision_d6.models import (
    Costs,
    DirectionalEvidence,
    Horizon,
    Portfolio,
    Request,
    RiskVector,
    Side,
    Snapshot,
)
from tradevision_d6.models import TradePlan as D6TradePlan
from tradevision_d6.proofs import ProofVerifier

FLAG = "TRADEVISION_D6_SHADOW"
ADAPTER_VERSION = "d6-shadow-adapter.v1"

# Versioned adapter judgment: grade -> risk. Reviewable; shadow-comparator only.
LIQUIDITY_RISK = {"A": Decimal("0.2"), "B": Decimal("0.5"), "C": Decimal("0.9"), "UNKNOWN": Decimal("0.7")}
# (layer, arbiter-request field) direction engines. Order is display order only.
DIRECTION_LAYERS = (
    ("market_regime", "market_regime_score"),
    ("structure_levels", "structure_score"),
    ("volume_auction", "volume_auction_score"),
    ("relative_strength", "relative_strength_score"),
    ("indicators", "indicator_signal_score"),
)


def shadow_enabled() -> bool:
    return os.getenv(FLAG, "off").strip().lower() == "on"


def _ns_to_dt(ns: int) -> datetime:
    return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)


def risks_from_spine(*, trap_score: float, event_risk_score: float, data_quality_pass: bool,
                     liquidity_grade: str, execution_slippage_risk: float) -> RiskVector:
    """All five D6 risks from live spine-native sources. No defaults, no borrowing."""
    return RiskVector(
        event=Decimal(str(event_risk_score)),
        trap=Decimal(str(trap_score)),
        data_uncertainty=Decimal("0.0") if data_quality_pass else Decimal("1.0"),
        liquidity=LIQUIDITY_RISK.get(liquidity_grade, LIQUIDITY_RISK["UNKNOWN"]),
        execution=Decimal(str(execution_slippage_risk)),
    )


def build_adapter_policy(horizon: Horizon):
    """Fixed, versioned comparator policy. Provisional tuning, shadow-only."""
    from tradevision_d6.models import GroupSpec, Policy, SourceSpec, StressScenario

    sources = tuple(SourceSpec(name=layer, group="directional", weight=Decimal("1.0"), required=False)
                    for layer, _ in DIRECTION_LAYERS)
    return Policy(
        revision=ADAPTER_VERSION, horizon=horizon, sources=sources,
        groups=(GroupSpec(name="directional", weight=Decimal("1.0")),),
        scenarios=(StressScenario(name="base", cost_multiplier=Decimal("1.0"), gap_multiplier=Decimal("1.0")),
                   StressScenario(name="adverse", cost_multiplier=Decimal("2.0"), gap_multiplier=Decimal("2.0"))),
        risk_caps=RiskVector(event=Decimal("1.0"), trap=Decimal("1.0"), data_uncertainty=Decimal("1.0"),
                             liquidity=Decimal("1.0"), execution=Decimal("1.0")),
        minimum_evidence=Decimal("0.15"), minimum_direction_margin=Decimal("0.10"),
        minimum_quality=Decimal("0.01"), minimum_net_reward_risk=Decimal("0.01"),
        minimum_modeled_expectancy=Decimal("0.01"), risk_per_trade_fraction=Decimal("1.0"),
        portfolio_risk_fraction=Decimal("1.0"), daily_loss_fraction=Decimal("1.0"),
        weekly_loss_fraction=Decimal("1.0"), max_bar_age_seconds=3600, max_quote_age_seconds=3600,
        max_portfolio_age_seconds=3600, max_cost_age_seconds=3600, max_entry_drift_bps=Decimal("1000"),
        minimum_validation_samples=30, minimum_validation_confidence=Decimal("0.5"),
        validation_embargo_seconds=0, max_validation_age_seconds=3600, max_proof_lifetime_seconds=3600,
        validation_method="shadow-adapter-no-validation",
    )


@dataclass(frozen=True, slots=True)
class DivergenceRecord:
    adapter_version: str
    input_hash: str
    arbiter_band: str
    d6_status: str  # D6 Status value, or ADAPTER_ABSTAIN_* pseudo-status
    d6_side: str | None
    d6_permission: str  # str(Decimal) or "n/a"
    causes: tuple[str, ...]


def _evidence_for_direction(layer_scores: dict[str, float], direction: str) -> tuple[list, list[str]]:
    """Corroboration-only feeding (see module docstring for the exactness argument).

    A layer contributes its exact magnitude on the asserted side ONLY when its sign
    agrees with the setup direction; disagreement is returned as conflict notes and
    contributes to NEITHER side. Risk layers never reach this function.
    """
    rows: list = []
    conflicts: list[str] = []
    for layer, _field in DIRECTION_LAYERS:
        raw = layer_scores.get(layer)
        if raw is None:
            continue
        value = Decimal(str(raw))
        if direction == "long" and value > 0:
            rows.append(DirectionalEvidence(source=layer, long=value, short=Decimal("0.0")))
        elif direction == "short" and value < 0:
            rows.append(DirectionalEvidence(source=layer, long=Decimal("0.0"), short=-value))
        else:
            conflicts.append(f"D6_SHADOW_LAYER_DISAGREES:{layer}={raw}")
    return rows, conflicts


def compare(*, symbol: str, timeframe: str, direction: str, layer_scores: dict[str, float],
            risks: RiskVector | None, snapshot_id: str, session_id: str,
            bar_open_ns: int, bar_close_ns: int, decision_ns: int,
            entry: float | None = None, stop: float | None = None, target: float | None = None,
            entry_plan_authority_present: bool = False,
            evidence_count: int = 0, minimum_evidence_count: int = 30,
            short_logic_enabled: bool = False, data_quality_pass: bool = True,
            arbiter_band: str = "WAIT") -> DivergenceRecord | None:
    """Compare host band vs D6 on identical evidence. None when flag off.

    Any unusable input yields a DivergenceRecord with an ADAPTER_ABSTAIN_* status —
    never an exception, never a fabricated evaluation.
    """
    if not shadow_enabled():
        return None
    import hashlib
    import json

    basis = {"v": ADAPTER_VERSION, "s": symbol, "t": timeframe, "d": direction,
             "layers": layer_scores,
             "risks": None if risks is None else {k: str(getattr(risks, k)) for k in
                                                 ("event", "trap", "data_uncertainty", "liquidity", "execution")},
             "snap": snapshot_id, "bo": bar_open_ns, "bc": bar_close_ns, "dn": decision_ns,
             "entry": entry, "stop": stop, "target": target}
    input_hash = hashlib.sha256(json.dumps(basis, sort_keys=True, default=str).encode()).hexdigest()

    def abstain(cause: str) -> DivergenceRecord:
        return DivergenceRecord(ADAPTER_VERSION, input_hash, arbiter_band,
                                "ADAPTER_ABSTAIN", None, "n/a", (cause,))

    if risks is None:
        return abstain("EXECUTION_RISK_UNAVAILABLE")
    try:
        horizon = Horizon.SWING if timeframe in ("daily", "weekly") else Horizon.INTRADAY
        side = {"long": Side.LONG, "short": Side.SHORT}.get(direction)
        if side is None:
            return abstain("NO_DIRECTIONAL_HYPOTHESIS")
        evidence, layer_conflicts = _evidence_for_direction(layer_scores, direction)
        plans: list = []
        if entry_plan_authority_present and entry is not None and stop is not None and target is not None:
            quality = min(1.0, evidence_count / max(minimum_evidence_count, 1))
            plans.append(D6TradePlan(
                side=side, setup_id=f"d6-shadow:{snapshot_id[:16]}", setup_spec_digest=snapshot_id,
                entry=Decimal(str(entry)), stop=Decimal(str(stop)), target=Decimal(str(target)),
                quality=Decimal(str(quality)),
                costs=Costs(round_trip_per_unit=Decimal("0.01"), gap_allowance_per_unit=Decimal("0.02"),
                            model_revision=ADAPTER_VERSION, estimated_at=_ns_to_dt(decision_ns),
                            valid_for_min_units=1, valid_for_max_units=1_000_000)))
        decision_at = _ns_to_dt(decision_ns)
        snapshot = Snapshot(
            snapshot_id=snapshot_id, symbol=symbol.upper(), session_id=session_id, horizon=horizon,
            bar_opened_at=_ns_to_dt(bar_open_ns), bar_closed_at=_ns_to_dt(bar_close_ns),
            data_received_at=decision_at, feature_available_at=decision_at,
            feature_cutoff_at=_ns_to_dt(bar_close_ns), quote_at=decision_at,
            feature_digest=snapshot_id, data_revision=snapshot_id,
            bid=Decimal("1.0"), ask=Decimal("1.0"), tick_size=Decimal("0.01"),
            lot_size=1, capacity_units=1_000_000,
            bar_is_closed=True, data_complete=bool(data_quality_pass),
            corporate_actions_checked=bool(data_quality_pass), event_feed_ok=True,
            session_entry_allowed=True, instrument_eligible=True,
            short_eligible=bool(short_logic_enabled))
        portfolio = Portfolio(
            account_id="d6-shadow-research", revision=ADAPTER_VERSION, observed_at=decision_at,
            equity=Decimal("10000000"), available_notional=Decimal("10000000"),
            open_modeled_risk=Decimal("0"), daily_loss=Decimal("0"), weekly_loss=Decimal("0"),
            kill_switch=False, conflicting_position=False, account_entry_allowed=True)
        request = Request(
            evaluation_at=decision_at, snapshot=snapshot, portfolio=portfolio,
            policy=build_adapter_policy(horizon), evidence=tuple(evidence), plans=tuple(plans),
            risks=risks, proofs=())
        decision = D6Engine(ProofVerifier({})).evaluate(request)
    except Exception as exc:  # noqa: BLE001 - adapter must never raise; record instead
        return abstain(f"ADAPTER_INPUT_REJECTED:{type(exc).__name__}")

    causes = list(layer_conflicts)
    host = arbiter_band.replace("-", "_")
    mine = decision.status.value
    if host != mine:
        causes.append(f"DIVERGE_host={arbiter_band}_d6={decision.status.value}")
    else:
        causes.append(f"AGREE_{decision.status.value}")
    if not plans:
        causes.append("NO_PLAN_NO_SETUP")
    return DivergenceRecord(
        adapter_version=ADAPTER_VERSION, input_hash=input_hash, arbiter_band=arbiter_band,
        d6_status=decision.status.value,
        d6_side=None if decision.selected_side is None else decision.selected_side.value,
        d6_permission=str(decision.trade_permission), causes=tuple(causes))
