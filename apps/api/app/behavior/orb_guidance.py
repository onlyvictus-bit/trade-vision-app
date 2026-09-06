from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleSeries,
    FinalConfluenceArbiterRequest,
    KillSwitchState,
    OrbBuildRequest,
    OrbBuildResult,
    OrbGuidanceTicket,
    PaperGuidanceEngineReceipt,
    PaperGuidanceEntryPlan,
    PaperGuidanceEvidenceVote,
    PaperGuidanceRequest,
    PaperTradeGuidance,
    SystemMode,
)
from ..orb import build_orb_candidate, list_orb_playbooks
from .atomic_json_store import load_record_map, update_record_map
from .final_confluence_arbiter import build_final_confluence_arbiter_report
from .paper_guidance_config import (
    PaperGuidanceConfig,
    load_paper_guidance_config,
    load_paper_guidance_storage_config,
)
from .paper_guidance_spine import run_paper_guidance_p1


ORB_GUIDANCE_VERSION = "orb-jarvis-guidance.v1.92"
ORB_GUIDANCE_RECEIPT_VERSION = "paper-guidance-engine-receipt.v1.92"
ORB_GUIDANCE_STORE_PATH = load_paper_guidance_storage_config().guidance_store_path


def run_paper_guidance_with_orb(
    request: PaperGuidanceRequest,
    *,
    mode: SystemMode,
    kill_switch: KillSwitchState,
    config: PaperGuidanceConfig | None = None,
) -> PaperTradeGuidance:
    """Attach a proof-backed ORB setup to the existing WAIT-first guidance spine."""

    settings = config or load_paper_guidance_config()
    base = run_paper_guidance_p1(
        request,
        mode=mode,
        kill_switch=kill_switch,
        config=settings,
    )
    if (
        not request.include_orb_playbook
        or not base.safety_gate.passed
        or base.snapshot is None
        or base.snapshot_hash is None
    ):
        return base

    playbooks = list_orb_playbooks(
        symbol=base.symbol,
        timeframe=base.timeframe,
        active_only=True,
    )
    playbook = playbooks[0] if playbooks else None
    orb_result = None
    if playbook is not None:
        orb_result = build_orb_candidate(
            OrbBuildRequest(
                series=_series_from_guidance(base),
                decision_time_ns=base.snapshot.decision_time_ns,
                source_snapshot_hash=base.snapshot_hash,
                config=playbook.config,
            )
        )

    valid_entry = _valid_entry_plan(orb_result) and bool(
        orb_result
        and (
            request.direction == "neutral"
            or (request.direction == "long" and orb_result.signal.side == "LONG")
            or (request.direction == "short" and orb_result.signal.side == "SHORT")
        )
    )
    mtf_complete = bool(
        base.mtf_evidence is not None
        and not base.mtf_evidence.blocks_promotion
        and not base.mtf_evidence.missing_required_timeframes
    )
    liquidity_grade = str(
        _receipt_summary(base, "EXECUTION_EVENT_OI_RISK").get(
            "liquidity_grade", "UNKNOWN"
        )
    )
    if liquidity_grade not in {"A", "B", "C", "UNKNOWN"}:
        liquidity_grade = "UNKNOWN"
    trap_score = _clamp(
        float(
            _receipt_summary(base, "MARKET_STRUCTURE_LIQUIDITY").get(
                "trap_score", 0.0
            )
        ),
        0.0,
        1.0,
    )
    direction = (
        "short"
        if orb_result is not None and orb_result.signal.side == "SHORT"
        else "long"
    )
    arbiter = build_final_confluence_arbiter_report(
        FinalConfluenceArbiterRequest(
            symbol=base.symbol,
            timeframe=base.timeframe,
            direction=direction,
            data_quality_pass=not base.data_quality.blocks_trade,
            liquidity_grade=liquidity_grade,  # type: ignore[arg-type]
            market_regime_score=_market_regime_score(base, direction),
            relative_strength_score=0.5,
            structure_score=_structure_score(base, direction, valid_entry),
            volume_auction_score=_volume_auction_score(base, direction),
            indicator_signal_score=0.0,
            external_ai_score=0.0,
            trap_score=trap_score,
            event_risk_score=_clamp(
                float(
                    _receipt_summary(base, "EXECUTION_EVENT_OI_RISK").get(
                        "event_risk_score", 0.0
                    )
                ),
                0.0,
                1.0,
            ),
            daily_resistance_conflict=_daily_resistance_conflict(base, direction),
            weak_sector=False,
            post_entry_thesis_status="not_entered",
            evidence_count=base.historical_match_count,
            minimum_evidence_count=base.minimum_evidence_count,
            low_evidence_flag=base.low_evidence_flag,
            required_mtf_complete=mtf_complete,
            entry_plan_authority_present=valid_entry,
            no_future_leakage=bool(
                base.point_in_time.passed
                and (
                    orb_result is None
                    or (
                        orb_result.no_future_leakage
                        and orb_result.source_snapshot_hash == base.snapshot_hash
                    )
                )
            ),
        )
    )

    final_band = (
        "ENTER_PAPER"
        if arbiter.final_decision in {"PAPER-CANDIDATE", "SHORT PAPER-CANDIDATE"}
        else arbiter.final_decision
        if arbiter.final_decision in {"WAIT", "WATCH", "AVOID"}
        else "WAIT"
    )
    entry_plan = _entry_plan(orb_result) if valid_entry else None
    blockers = _clean_base_blockers(base.blockers)
    warnings = _clean_base_warnings(base.warnings)
    reasons = []
    if playbook is None:
        blockers.append(
            "No active proof-backed ORB playbook exists for this symbol and timeframe."
        )
        reasons.append("Run ORB discovery, proof, and explicit promotion before guidance.")
    elif orb_result is None or not orb_result.range_locked:
        blockers.append("The opening range is not locked on the current closed-candle snapshot.")
        reasons.append("Wait until the configured opening range is fully closed.")
    elif not orb_result.setup_available:
        blockers.append("The active ORB playbook has no completed setup on this snapshot.")
        reasons.append(orb_result.signal.reason)
    else:
        reasons.extend(
            [
                orb_result.signal.reason,
                "The ORB setup is bound to the same immutable D2 snapshot used by Jarvis.",
                "The playbook passed server-side proof and promotion before becoming active.",
            ]
        )
    if base.low_evidence_flag:
        blockers.append(
            f"Evidence count {base.historical_match_count} is below "
            f"{base.minimum_evidence_count}; PAPER-CANDIDATE is blocked."
        )
    if not mtf_complete:
        blockers.append("Required MTF evidence is missing or conflicts with the ORB setup.")
    if liquidity_grade == "C":
        blockers.append("Liquidity grade C blocks paper candidacy.")
    if trap_score >= 0.70:
        blockers.append(f"Trap score {trap_score:.2f} blocks the ORB setup.")
    if arbiter.dominant_blocker:
        blockers.append(f"Final arbiter blocker: {arbiter.dominant_blocker}.")

    guidance_id = str(
        uuid5(
            NAMESPACE_URL,
            "tradevision:orb-guidance:v1.92:"
            + base.snapshot_hash
            + ":"
            + (playbook.playbook_id if playbook else "no-playbook")
            + ":"
            + (orb_result.deterministic_hash if orb_result else "no-orb-result")
            + ":"
            + _hash(arbiter.model_dump(mode="json")),
        )
    )
    ticket = _build_ticket(
        guidance_id=guidance_id,
        base=base,
        playbook=playbook,
        orb_result=orb_result,
        final_band=final_band,
        entry_plan=entry_plan,
        liquidity_grade=liquidity_grade,
        trap_score=trap_score,
        mtf_complete=mtf_complete,
        blockers=blockers,
        warnings=warnings,
        reasons=reasons,
    )
    _save_guidance_ticket(ticket)

    orb_receipt = _orb_receipt(base, orb_result, ticket)
    arbiter_receipt = _arbiter_receipt(base, arbiter)
    receipts = [
        receipt
        for receipt in base.engine_receipts
        if receipt.engine_id != "FINAL_CONFLUENCE_ARBITER"
    ]
    receipts.extend([orb_receipt, arbiter_receipt])
    confidence_cap = min(
        settings.p0_confidence_cap,
        arbiter.confidence_interval[1],
        settings.low_evidence_confidence_cap if base.low_evidence_flag else 1.0,
    )
    return base.model_copy(
        update={
            "guidance_version": ORB_GUIDANCE_VERSION,
            "guidance_id": guidance_id,
            "final_band": final_band,
            "confidence_cap": round(confidence_cap, 4),
            "next_action": (
                "OFFER_PAPER_TICKET" if ticket.can_record_paper else "DO_NOTHING"
            ),
            "blockers": _unique(blockers),
            "warnings": _unique(warnings),
            "reason_for": _unique(
                [
                    *base.reason_for,
                    *reasons,
                    *arbiter.human_reason_tree,
                ]
            ),
            "reason_against": _unique(
                [
                    item
                    for item in base.reason_against
                    if "v1.88 has no entry-plan authority" not in item
                ]
                + blockers
            ),
            "entry_plan": entry_plan,
            "evidence_votes": [
                PaperGuidanceEvidenceVote(
                    engine_id=vote.evidence_layer,
                    vote=(
                        "FOR"
                        if vote.direction == "long"
                        else "AGAINST"
                        if vote.direction in {"short", "block"}
                        else "NEUTRAL"
                    ),
                    weight=min(1.0, abs(vote.weighted_score) / 7.0),
                    lag_penalty=0.5 if vote.evidence_layer == "indicators" else 0.0,
                    note=vote.reason,
                )
                for vote in arbiter.evidence_votes
            ],
            "engine_receipts": receipts,
            "orb_ticket": ticket,
            "arbiter_summary": {
                "arbiter_version": arbiter.arbiter_version,
                "decision_band": arbiter.decision_band,
                "final_decision": arbiter.final_decision,
                "confluence_score": arbiter.confluence_score,
                "dominant_blocker": arbiter.dominant_blocker,
                "gates": [gate.model_dump(mode="json") for gate in arbiter.gates],
            },
            "engines_run": _unique(
                [
                    *[
                        item
                        for item in base.engines_run
                        if item != "FINAL_CONFLUENCE_ARBITER"
                    ],
                    "D3A_ORB",
                    "FINAL_CONFLUENCE_ARBITER",
                    "D7_JARVIS_ORB_GUIDANCE",
                ]
            ),
            "engines_skipped": [
                item
                for item in base.engines_skipped
                if not item.startswith("D3A_ORB:")
                and not item.startswith("D7_JARVIS_CARD:")
            ],
            "risk_summary": {
                **base.risk_summary,
                "paper_entry_authority": valid_entry,
                "orb_playbook_active": playbook is not None,
                "orb_snapshot_identity_match": bool(
                    orb_result
                    and orb_result.source_snapshot_hash == base.snapshot_hash
                ),
                "paper_record_requires_human_approval": True,
            },
        }
    )


def load_guidance_ticket(
    guidance_id: str,
    *,
    require_fresh: bool = False,
    now_ns: int | None = None,
) -> OrbGuidanceTicket | None:
    payload = _load_records(ORB_GUIDANCE_STORE_PATH).get(guidance_id)
    if payload is None:
        return None
    if require_fresh:
        metadata = payload.get("_store_metadata")
        if not isinstance(metadata, dict):
            raise ValueError(
                "Guidance ticket has no v1.94 freshness metadata; run guidance again."
            )
        expires_at_ns = int(metadata.get("expires_at_ns", 0))
        if expires_at_ns <= int(now_ns if now_ns is not None else time.time_ns()):
            raise ValueError("Guidance ticket expired; run guidance again before approval.")
    return OrbGuidanceTicket.model_validate(payload)


def list_guidance_tickets(
    *, symbol: str | None = None, timeframe: str | None = None
) -> list[OrbGuidanceTicket]:
    tickets = [
        OrbGuidanceTicket.model_validate(payload)
        for payload in _load_records(ORB_GUIDANCE_STORE_PATH).values()
    ]
    return sorted(
        [
            item
            for item in tickets
            if (symbol is None or item.symbol == symbol.upper())
            and (timeframe is None or item.timeframe == timeframe)
        ],
        key=lambda item: (item.symbol, item.timeframe, item.decision_time_ns, item.guidance_id),
        reverse=True,
    )


def guidance_ticket_store_rows() -> dict[str, dict]:
    return _load_records(ORB_GUIDANCE_STORE_PATH)


def _series_from_guidance(guidance: PaperTradeGuidance) -> CandleSeries:
    snapshot = guidance.snapshot
    if snapshot is None:
        raise ValueError("D2 snapshot is required before ORB can run")
    return CandleSeries(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        bars=snapshot.closed_ohlcv_bars,
        snapshot_id=snapshot.snapshot_id,
        schema_version=snapshot.source_schema_version,
    )


def _valid_entry_plan(result: OrbBuildResult | None) -> bool:
    if (
        result is None
        or not result.setup_available
        or not result.range_locked
        or not result.no_future_leakage
        or result.signal.side not in {"LONG", "SHORT"}
    ):
        return False
    values = (
        result.signal.entry_price,
        result.signal.stop_price,
        result.signal.target_price,
        result.signal.reward_risk_ratio,
    )
    return all(value is not None and float(value) > 0.0 for value in values)


def _entry_plan(result: OrbBuildResult | None) -> PaperGuidanceEntryPlan | None:
    if not _valid_entry_plan(result) or result is None:
        return None
    signal = result.signal
    return PaperGuidanceEntryPlan(
        side=signal.side,  # type: ignore[arg-type]
        entry=float(signal.entry_price),
        stop=float(signal.stop_price),
        target=float(signal.target_price),
        invalidation=signal.invalidation,
        size_hint=0.0,
        r_ratio=float(signal.reward_risk_ratio),
    )


def _build_ticket(
    *,
    guidance_id: str,
    base: PaperTradeGuidance,
    playbook,
    orb_result: OrbBuildResult | None,
    final_band: str,
    entry_plan: PaperGuidanceEntryPlan | None,
    liquidity_grade: str,
    trap_score: float,
    mtf_complete: bool,
    blockers: list[str],
    warnings: list[str],
    reasons: list[str],
) -> OrbGuidanceTicket:
    if playbook is None:
        state = "NO_PLAYBOOK"
    elif orb_result is None or not orb_result.setup_available:
        state = "NO_SETUP"
    elif final_band == "ENTER_PAPER":
        state = "PAPER_CANDIDATE"
    elif final_band == "WATCH":
        state = "WATCH"
    else:
        state = "BLOCKED"
    payload = {
        "ticket_version": ORB_GUIDANCE_VERSION,
        "guidance_id": guidance_id,
        "symbol": base.symbol,
        "timeframe": base.timeframe,
        "decision_time_ns": base.snapshot.decision_time_ns,  # type: ignore[union-attr]
        "source_snapshot_hash": base.snapshot_hash,
        "playbook_id": None if playbook is None else playbook.playbook_id,
        "proof_id": None if playbook is None else playbook.proof_id,
        "proof_hash": None if playbook is None else playbook.proof_hash,
        "strategy_family": (
            None if playbook is None else playbook.config.strategy_family
        ),
        "candidate_state": state,
        "final_band": final_band,
        "opening_range": (
            None
            if orb_result is None or orb_result.opening_range is None
            else orb_result.opening_range.model_dump(mode="json")
        ),
        "signal": (
            None if orb_result is None else orb_result.signal.model_dump(mode="json")
        ),
        "entry_plan": None if entry_plan is None else entry_plan.model_dump(mode="json"),
        "proof_metrics": (
            None if playbook is None else playbook.metrics.model_dump(mode="json")
        ),
        "historical_match_count": base.historical_match_count,
        "minimum_evidence_count": base.minimum_evidence_count,
        "mtf_complete": mtf_complete,
        "liquidity_grade": liquidity_grade,
        "trap_score": trap_score,
        "can_record_paper": final_band == "ENTER_PAPER" and entry_plan is not None,
        "blockers": _unique(blockers),
        "warnings": _unique(warnings),
        "reasons": _unique(reasons),
    }
    return OrbGuidanceTicket(**payload, deterministic_hash=_hash(payload))


def _orb_receipt(
    base: PaperTradeGuidance,
    result: OrbBuildResult | None,
    ticket: OrbGuidanceTicket,
) -> PaperGuidanceEngineReceipt:
    summary = {
        "candidate_state": ticket.candidate_state,
        "playbook_id": ticket.playbook_id,
        "proof_id": ticket.proof_id,
        "signal_type": None if result is None else result.signal.signal_type,
        "range_locked": False if result is None else result.range_locked,
        "entry_plan_present": ticket.entry_plan is not None,
        "can_record_paper": ticket.can_record_paper,
    }
    return PaperGuidanceEngineReceipt(
        receipt_version=ORB_GUIDANCE_RECEIPT_VERSION,
        engine_id="ORB_PLAYBOOK_GUIDANCE",
        stage="D3A_SETUP",
        engine_version="orb-core.v1.89+orb-playbook.v1.91",
        source_snapshot_hash=str(base.snapshot_hash),
        output_hash=_hash(summary),
        status=(
            "completed"
            if result is not None and result.setup_available
            else "degraded"
            if ticket.playbook_id
            else "skipped"
        ),
        identity_match=bool(
            result is None or result.source_snapshot_hash == base.snapshot_hash
        ),
        output_summary=summary,
        warnings=ticket.blockers if not ticket.can_record_paper else [],
    )


def _arbiter_receipt(base: PaperTradeGuidance, arbiter) -> PaperGuidanceEngineReceipt:
    summary = {
        "decision_band": arbiter.decision_band,
        "final_decision": arbiter.final_decision,
        "confluence_score": arbiter.confluence_score,
        "dominant_blocker": arbiter.dominant_blocker,
    }
    return PaperGuidanceEngineReceipt(
        receipt_version=ORB_GUIDANCE_RECEIPT_VERSION,
        engine_id="FINAL_CONFLUENCE_ARBITER",
        stage="D6_ARBITER",
        engine_version=arbiter.arbiter_version,
        source_snapshot_hash=str(base.snapshot_hash),
        output_hash=_hash(summary),
        status="completed",
        identity_match=True,
        output_summary=summary,
    )


def _receipt_summary(base: PaperTradeGuidance, engine_id: str) -> dict:
    receipt = next(
        (item for item in base.engine_receipts if item.engine_id == engine_id),
        None,
    )
    return {} if receipt is None else receipt.output_summary


def _market_regime_score(base: PaperTradeGuidance, direction: str) -> float:
    chart = _receipt_summary(base, "CHART_REASONING")
    score = float(chart.get("trend_persistence_score", 0.5)) * 2.0 - 1.0
    if direction == "short":
        score *= -1.0
    if chart.get("chop_risk") == "high":
        score = min(score, -0.35)
    return _clamp(score, -1.0, 1.0)


def _structure_score(
    base: PaperTradeGuidance, direction: str, orb_entry_authority: bool
) -> float:
    condition = _receipt_summary(base, "CANDLE_CONDITION")
    levels = _receipt_summary(base, "LEVEL_CONTEXT")
    structure = _receipt_summary(base, "MARKET_STRUCTURE_LIQUIDITY")
    parts = [0.75 if orb_entry_authority else -0.25]
    bias = condition.get("signal_bias")
    condition_score = (
        0.65
        if bias == direction
        else -0.65
        if bias in {"long", "short"}
        else -0.15
    )
    if condition.get("blocks_trade"):
        condition_score = min(condition_score, -0.55)
    parts.append(condition_score)
    if "level_respect_score" in levels:
        level_score = float(levels["level_respect_score"]) * 2.0 - 1.0
        if levels.get("blocks_trade"):
            level_score = min(level_score, -0.55)
        parts.append(level_score)
    structure_score = 0.25
    if structure.get("vsa_downgrade_active"):
        structure_score -= 0.55
    structure_score -= float(structure.get("trap_score", 0.0)) * 0.65
    parts.append(structure_score)
    return _clamp(sum(parts) / len(parts), -1.0, 1.0)


def _volume_auction_score(base: PaperTradeGuidance, direction: str) -> float:
    structure = _receipt_summary(base, "MARKET_STRUCTURE_LIQUIDITY")
    score = 0.2
    if structure.get("vsa_downgrade_active"):
        score -= 0.65
    position = structure.get("value_area_position")
    if position == "above_value":
        score += 0.25 if direction == "long" else -0.25
    elif position == "below_value":
        score += 0.25 if direction == "short" else -0.25
    return _clamp(score, -1.0, 1.0)


def _daily_resistance_conflict(base: PaperTradeGuidance, direction: str) -> bool:
    if direction != "long":
        return False
    levels = _receipt_summary(base, "LEVEL_CONTEXT")
    flags = levels.get("support_resistance_flags", [])
    return any(flag in {"rejecting_pdh", "failed_orb_breakout"} for flag in flags)


def _clean_base_blockers(values: list[str]) -> list[str]:
    return [
        item
        for item in values
        if "verified ORB entry/stop/target plan is not available until v1.92"
        not in item
        and "ENTER_PAPER is unavailable in v1.87 P0" not in item
    ]


def _clean_base_warnings(values: list[str]) -> list[str]:
    return [
        item
        for item in values
        if "ORB remains intentionally skipped in v1.88" not in item
    ]


def _save_guidance_ticket(ticket: OrbGuidanceTicket) -> None:
    settings = load_paper_guidance_storage_config()
    stored_at_ns = time.time_ns()
    payload = ticket.model_dump(mode="json")
    payload["_store_metadata"] = {
        "stored_at_ns": stored_at_ns,
        "expires_at_ns": stored_at_ns
        + settings.maximum_ticket_age_seconds * 1_000_000_000,
        "retention_days": settings.retention_days,
    }

    def _upsert(records: dict[str, dict]):
        records[ticket.guidance_id] = payload
        return records, None

    update_record_map(ORB_GUIDANCE_STORE_PATH, _upsert)


def _load_records(path: Path) -> dict[str, dict]:
    return load_record_map(path)


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in values if str(item).strip()))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

# BEGIN AFRE_V3_OPT_IN_ADDITION
def run_adaptive_paper_guidance(service, session_date, event):
    """Persist the same event reducer used by adaptive discovery/proof.

    This versioned path has its own exact policy proof. It does not attach a
    post-proof alpha veto or a second signed-score arbiter to the old path.
    """
    return service.ingest(session_date, event)
# END AFRE_V3_OPT_IN_ADDITION
