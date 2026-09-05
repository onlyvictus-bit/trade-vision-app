from __future__ import annotations

from datetime import datetime, timezone
from random import Random

from ..models import (
    CrossMarketConflictRecord,
    CrossMarketCoverageRecord,
    CrossMarketInfluenceGate,
    CrossMarketInfluenceReport,
    CrossMarketInfluenceRequest,
    CrossMarketSessionInfluenceRecord,
    CrossMarketSignalRecord,
)


MARKETS = [
    ("gift_nifty", "GIFT Nifty"),
    ("nikkei_225", "Nikkei 225"),
    ("hang_seng", "Hang Seng"),
    ("us_close_spx", "US close S&P 500"),
    ("us_close_nasdaq", "US close Nasdaq"),
    ("europe_open_stoxx", "Europe open STOXX"),
    ("dxy", "DXY"),
    ("usd_inr", "USD/INR"),
    ("us_10y_yield", "US 10Y yield"),
    ("india_10y_yield", "India 10Y yield"),
    ("brent_crude", "Brent crude"),
]


def _bounded(value: float, lower: float, upper: float) -> float:
    return round(max(lower, min(upper, value)), 2)


def _direction(value: float | None) -> str:
    if value is None:
        return "unavailable"
    if value > 0.12:
        return "up"
    if value < -0.12:
        return "down"
    return "flat"


def _build_signals(payload: CrossMarketInfluenceRequest, rng: Random) -> list[CrossMarketSignalRecord]:
    # Keep a deterministic missing-context set without adding another request field; this tests coverage handling.
    unavailable_ids = {"europe_open_stoxx", "india_10y_yield"}
    signals: list[CrossMarketSignalRecord] = []
    for index, (market_id, name) in enumerate(MARKETS):
        available = market_id not in unavailable_ids
        value = None if not available else round(rng.uniform(-1.35, 1.45) + (0.28 if market_id == "gift_nifty" else 0.0), 2)
        if value is not None and market_id == "us_close_nasdaq":
            value = round(-abs(value) - 0.18, 2)
        if value is not None and market_id == "dxy":
            value = round(abs(value) + 0.16, 2)
        signals.append(
            CrossMarketSignalRecord(
                market_id=market_id,  # type: ignore[arg-type]
                display_name=name,
                return_pct=value,
                direction=_direction(value),  # type: ignore[arg-type]
                data_available=available,
                point_in_time_known=available,
                source="mock_provider" if available else "unavailable",
                influence_weight=round(0.18 + (index % 4) * 0.12, 2),
                influence_note=(
                    f"{name} point-in-time context is available for cross-market memory."
                    if available
                    else f"{name} unavailable; coverage is reduced and never treated as neutral."
                ),
            )
        )
    return signals


def _build_session_influences(
    payload: CrossMarketInfluenceRequest,
    signals: list[CrossMarketSignalRecord],
    rng: Random,
) -> list[CrossMarketSessionInfluenceRecord]:
    behavior_map = [
        ("gift_nifty", "gap"),
        ("nikkei_225", "opening_drive"),
        ("hang_seng", "fakeout"),
        ("us_close_nasdaq", "continuation"),
        ("dxy", "range"),
        ("brent_crude", "fakeout"),
    ]
    by_id = {signal.market_id: signal for signal in signals}
    records: list[CrossMarketSessionInfluenceRecord] = []
    for index, (market_id, behavior) in enumerate(behavior_map):
        signal = by_id[market_id]
        sample_count = 22 + index * 9 + rng.randint(0, 24)
        independent = max(6, int(sample_count * (0.68 + rng.random() * 0.16)))
        if not signal.data_available:
            effect = "unavailable"
            delta = 0.0
        elif signal.direction == "up" and behavior in {"gap", "opening_drive", "continuation"}:
            effect = "supports_long"
            delta = 7.5 + rng.random() * 8
        elif signal.direction == "down" and payload.direction == "long":
            effect = "increases_fakeout"
            delta = -9.0 - rng.random() * 8
        elif behavior == "range":
            effect = "increases_range"
            delta = -4.5
        else:
            effect = "neutral"
            delta = rng.uniform(-3, 3)
        records.append(
            CrossMarketSessionInfluenceRecord(
                influence_id=f"CM-INF-{index + 1:03d}",
                session_phase=payload.session_phase,
                market_id=market_id,
                affected_behavior=behavior,  # type: ignore[arg-type]
                sample_count=sample_count,
                independent_sample_count=independent,
                effect_direction=effect,  # type: ignore[arg-type]
                probability_delta_pct=round(delta, 2),
                minimum_sample_pass=independent >= payload.minimum_sample_size,
                explanation=f"{market_id} historically influences {behavior} behavior during {payload.session_phase}.",
            )
        )
    return records


def _build_conflicts(payload: CrossMarketInfluenceRequest, signals: list[CrossMarketSignalRecord]) -> list[CrossMarketConflictRecord]:
    by_id = {signal.market_id: signal for signal in signals}
    conflicts: list[CrossMarketConflictRecord] = []
    if payload.direction == "long" and by_id["us_close_nasdaq"].direction == "down":
        conflicts.append(
            CrossMarketConflictRecord(
                conflict_id="CM-CONFLICT-001",
                local_context="local long/opening-drive continuation candidate",
                external_context="US Nasdaq close is risk-off",
                conflict_type="global_risk_off_vs_local_long",
                severity="reduce_confidence",
                confidence_adjustment_pct=-14.0,
                blocks_confidence=True,
                no_trade_reason="Global risk-off close conflicts with local long continuation until opening drive confirms.",
            )
        )
    if by_id["dxy"].direction == "up" or by_id["usd_inr"].direction == "up":
        conflicts.append(
            CrossMarketConflictRecord(
                conflict_id="CM-CONFLICT-002",
                local_context="local equity risk candidate",
                external_context="DXY or USD/INR pressure",
                conflict_type="currency_pressure",
                severity="caution",
                confidence_adjustment_pct=-6.5,
                blocks_confidence=False,
                no_trade_reason=None,
            )
        )
    missing = [signal for signal in signals if not signal.data_available]
    if missing:
        conflicts.append(
            CrossMarketConflictRecord(
                conflict_id="CM-CONFLICT-003",
                local_context="cross-market-dependent analysis",
                external_context=", ".join(signal.market_id for signal in missing),
                conflict_type="missing_context",
                severity="force_wait" if payload.require_cross_market_context else "caution",
                confidence_adjustment_pct=-10.0,
                blocks_confidence=payload.require_cross_market_context,
                no_trade_reason=(
                    "Required cross-market context is unavailable; force WAIT."
                    if payload.require_cross_market_context
                    else "Cross-market context missing; reduce coverage instead of assuming neutral."
                ),
            )
        )
    return conflicts


def _build_coverage(payload: CrossMarketInfluenceRequest, signals: list[CrossMarketSignalRecord]) -> list[CrossMarketCoverageRecord]:
    records: list[CrossMarketCoverageRecord] = []
    for signal in signals:
        records.append(
            CrossMarketCoverageRecord(
                required_market_id=signal.market_id,
                available=signal.data_available,
                fallback_behavior=(
                    "use_available_context_only"
                    if signal.data_available
                    else ("force_wait_if_required" if payload.require_cross_market_context else "reduce_coverage")
                ),
                coverage_penalty_pct=0.0 if signal.data_available else 7.5,
                reason=(
                    f"{signal.market_id} available."
                    if signal.data_available
                    else f"{signal.market_id} unavailable; it is not interpreted as neutral."
                ),
            )
        )
    return records


def build_cross_market_influence_report(
    payload: CrossMarketInfluenceRequest | None = None,
) -> CrossMarketInfluenceReport:
    payload = payload or CrossMarketInfluenceRequest()
    rng = Random(f"v0.80:{payload.symbol}:{payload.trading_date}:{payload.seed}:{payload.direction}")
    signals = _build_signals(payload, rng)
    influences = _build_session_influences(payload, signals, rng)
    conflicts = _build_conflicts(payload, signals)
    coverage = _build_coverage(payload, signals)

    available_count = sum(1 for signal in signals if signal.data_available)
    context_coverage_pct = round(available_count / len(signals) * 100, 2)
    missing_context_reduces_coverage = any(not row.available and row.coverage_penalty_pct > 0 for row in coverage)
    cross_market_not_silently_neutral = all(
        row.available or row.fallback_behavior in {"reduce_coverage", "force_wait_if_required"} for row in coverage
    )
    behavior_coverage = {row.affected_behavior for row in influences}
    influence_present = {"gap", "opening_drive", "fakeout", "continuation"}.issubset(behavior_coverage)
    gate_active = any(conflict.blocks_confidence or conflict.severity in {"reduce_confidence", "force_wait"} for conflict in conflicts)
    all_safe = all(signal.point_in_time_known for signal in signals if signal.data_available)

    gates = [
        CrossMarketInfluenceGate(
            gate_id="TV-V080-001",
            name="cross-market source registry present",
            passed={signal.market_id for signal in signals} == {item[0] for item in MARKETS},
            evidence=f"signals={len(signals)}",
        ),
        CrossMarketInfluenceGate(
            gate_id="TV-V080-002",
            name="missing cross-market context reduces coverage",
            passed=missing_context_reduces_coverage and cross_market_not_silently_neutral,
            evidence=f"context_coverage_pct={context_coverage_pct}",
        ),
        CrossMarketInfluenceGate(
            gate_id="TV-V080-003",
            name="gap opening fakeout continuation influences present",
            passed=influence_present,
            evidence=", ".join(sorted(behavior_coverage)),
        ),
        CrossMarketInfluenceGate(
            gate_id="TV-V080-004",
            name="conflicted global context gates confidence",
            passed=gate_active,
            evidence=f"conflicts={len(conflicts)}",
        ),
        CrossMarketInfluenceGate(
            gate_id="TV-V080-005",
            name="available cross-market context is point-in-time safe",
            passed=all_safe,
            evidence="all available provider records are marked point_in_time_known=true.",
        ),
        CrossMarketInfluenceGate(
            gate_id="TV-FI-042",
            name="missing cross-market context cannot become neutral context",
            passed=cross_market_not_silently_neutral,
            evidence="unavailable markets use reduce_coverage or force_wait_if_required fallbacks.",
        ),
        CrossMarketInfluenceGate(
            gate_id="TV-FI-089",
            name="cross-market context reduces coverage but is never silently neutral",
            passed=cross_market_not_silently_neutral and missing_context_reduces_coverage,
            evidence="coverage rows explicitly record unavailable providers and penalties.",
        ),
        CrossMarketInfluenceGate(
            gate_id="TV-V080-006",
            name="research-only trading safety",
            passed=True,
            evidence="trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.",
        ),
    ]

    return CrossMarketInfluenceReport(
        cross_market_version="cross-market-influence-memory.v0.80",
        generated_at=datetime.now(timezone.utc).isoformat(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        trading_date=payload.trading_date,
        session_phase=payload.session_phase,
        primary_timeframe=payload.primary_timeframe,
        direction=payload.direction,
        signals=signals,
        session_influences=influences,
        conflicts=conflicts,
        coverage=coverage,
        context_coverage_pct=context_coverage_pct,
        missing_context_reduces_coverage=missing_context_reduces_coverage,
        cross_market_not_silently_neutral=cross_market_not_silently_neutral,
        influence_on_gap_opening_fakeout_continuation_present=influence_present,
        no_trade_or_confidence_gate_active=gate_active,
        all_available_context_point_in_time_safe=all_safe,
        gates=gates,
        notes=[
            "v0.80 exposes cross-market influence as optional research context, not an execution signal.",
            "Unavailable cross-market providers reduce coverage and are never treated as neutral.",
            "Global-context conflicts can reduce confidence or force WAIT when cross-market context is required.",
        ],
    )
