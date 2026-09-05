from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone

from ..models import (
    OrbPaperReliabilityReport,
    PaperGuidanceStorageMonitor,
    SimulatedPaperLifecycleOutcome,
    now_iso,
)
from .atomic_json_store import store_monitor
from .orb_guidance import (
    ORB_GUIDANCE_STORE_PATH,
    guidance_ticket_store_rows,
)
from .orb_paper_lifecycle import (
    ORB_PAPER_OUTCOME_STORE_PATH,
    list_simulated_paper_outcomes,
    paper_outcome_store_rows,
)
from .paper_guidance_config import (
    PaperGuidanceStorageConfig,
    load_paper_guidance_storage_config,
)
from .simulated_paper_ledger import (
    SIMULATED_PAPER_STORE_PATH,
    simulated_paper_store_rows,
)


ORB_PAPER_RELIABILITY_VERSION = "orb-paper-reliability.v1.94"
PAPER_GUIDANCE_MONITOR_VERSION = "paper-guidance-monitor.v1.94"


def build_orb_paper_reliability(
    playbook_id: str,
    *,
    symbol: str = "UNKNOWN",
    timeframe: str = "5m",
    config: PaperGuidanceStorageConfig | None = None,
) -> OrbPaperReliabilityReport:
    settings = config or load_paper_guidance_storage_config()
    paper_rows = simulated_paper_store_rows()
    outcomes = list_simulated_paper_outcomes(
        playbook_id=playbook_id,
        completed_only=True,
    )
    valid: list[SimulatedPaperLifecycleOutcome] = []
    orphan_count = 0
    excluded_count = 0
    for outcome in outcomes:
        paper = paper_rows.get(outcome.paper_record_id)
        if paper is None:
            orphan_count += 1
            continue
        if not _identity_chain_valid(outcome, paper):
            orphan_count += 1
            continue
        if not _outcome_integrity_valid(outcome):
            excluded_count += 1
            continue
        if outcome.outcome_label not in {"TARGET_HIT", "STOP_HIT", "TIME_EXIT"}:
            excluded_count += 1
            continue
        valid.append(outcome)

    if valid:
        symbol = valid[0].symbol
        timeframe = valid[0].timeframe
    wins = sum(item.outcome_label == "TARGET_HIT" for item in valid)
    losses = sum(item.outcome_label == "STOP_HIT" for item in valid)
    time_exits = sum(item.outcome_label == "TIME_EXIT" for item in valid)
    sample_count = len(valid)
    win_rate = wins / sample_count if sample_count else 0.0
    bayesian = (wins + 1.0) / (sample_count + 2.0)
    average_net_r = (
        sum(item.net_r for item in valid) / sample_count if sample_count else 0.0
    )
    minimum_pass = sample_count >= settings.feedback_minimum_samples
    if not minimum_pass:
        state = "LOW_EVIDENCE"
        reason = (
            f"{sample_count}/{settings.feedback_minimum_samples} completed "
            "point-in-time outcomes; reliability cannot influence guidance."
        )
    elif (
        win_rate < settings.feedback_quarantine_win_rate
        or average_net_r <= 0.0
    ):
        state = "QUARANTINE_RECOMMENDED"
        reason = (
            "Completed paper evidence is weak after costs; operator review and "
            "fresh proof are recommended. No automatic playbook change occurred."
        )
    else:
        state = "RESEARCH_USABLE"
        reason = (
            "Completed paper outcomes are usable as reduce-only reliability "
            "evidence. They cannot promote or raise a guidance band."
        )
    return OrbPaperReliabilityReport(
        reliability_version=ORB_PAPER_RELIABILITY_VERSION,
        playbook_id=playbook_id,
        symbol=symbol.upper(),
        timeframe=timeframe,  # type: ignore[arg-type]
        completed_sample_count=sample_count,
        win_count=wins,
        loss_count=losses,
        time_exit_count=time_exits,
        excluded_outcome_count=excluded_count,
        orphan_outcome_count=orphan_count,
        minimum_sample_count=settings.feedback_minimum_samples,
        minimum_sample_pass=minimum_pass,
        observed_win_rate=round(win_rate, 8),
        bayesian_win_rate=round(bayesian, 8),
        average_net_r=round(average_net_r, 8),
        reliability_state=state,  # type: ignore[arg-type]
        last_completed_outcome_id=valid[0].outcome_id if valid else None,
        reason=reason,
    )


def build_paper_guidance_storage_monitor(
    *,
    config: PaperGuidanceStorageConfig | None = None,
    now_ns: int | None = None,
) -> PaperGuidanceStorageMonitor:
    settings = config or load_paper_guidance_storage_config()
    current_ns = int(now_ns if now_ns is not None else time.time_ns())
    stores = [
        store_monitor(ORB_GUIDANCE_STORE_PATH),
        store_monitor(SIMULATED_PAPER_STORE_PATH),
        store_monitor(ORB_PAPER_OUTCOME_STORE_PATH),
    ]
    integrity = all(item["integrity"] == "PASS" for item in stores)
    blockers = [
        str(item["error"])
        for item in stores
        if item["integrity"] != "PASS" and item["error"]
    ]
    if not integrity:
        return PaperGuidanceStorageMonitor(
            monitor_version=PAPER_GUIDANCE_MONITOR_VERSION,
            generated_at=now_iso(),
            stores=stores,
            integrity_passed=False,
            guidance_ticket_count=0,
            paper_record_count=0,
            outcome_record_count=0,
            completed_outcome_count=0,
            orphan_outcome_count=0,
            stale_ticket_count=0,
            retention_days=settings.retention_days,
            retention_candidate_count=0,
            last_observation_time_ns=None,
            blockers=blockers,
        )

    guidance = guidance_ticket_store_rows()
    papers = simulated_paper_store_rows()
    outcomes = paper_outcome_store_rows()
    stale_count = sum(
        int(
            row.get("_store_metadata", {}).get("expires_at_ns", 0)
        )
        <= current_ns
        for row in guidance.values()
    )
    parsed_outcomes = [
        SimulatedPaperLifecycleOutcome.model_validate(row)
        for row in outcomes.values()
    ]
    orphan_count = sum(
        item.paper_record_id not in papers for item in parsed_outcomes
    )
    cutoff_ns = current_ns - (
        settings.retention_days * 86_400 * 1_000_000_000
    )
    retention_candidates = sum(
        _iso_before_ns(row.get("approved_at"), cutoff_ns)
        for row in papers.values()
    )
    retention_candidates += sum(
        _guidance_before_ns(row, cutoff_ns) for row in guidance.values()
    )
    return PaperGuidanceStorageMonitor(
        monitor_version=PAPER_GUIDANCE_MONITOR_VERSION,
        generated_at=now_iso(),
        stores=stores,
        integrity_passed=True,
        guidance_ticket_count=len(guidance),
        paper_record_count=len(papers),
        outcome_record_count=len(outcomes),
        completed_outcome_count=sum(item.completed for item in parsed_outcomes),
        orphan_outcome_count=orphan_count,
        stale_ticket_count=stale_count,
        retention_days=settings.retention_days,
        retention_candidate_count=retention_candidates,
        last_observation_time_ns=max(
            (item.observation_time_ns for item in parsed_outcomes),
            default=None,
        ),
        blockers=(
            [f"{orphan_count} orphan lifecycle outcome(s) require review."]
            if orphan_count
            else []
        ),
    )


def _identity_chain_valid(
    outcome: SimulatedPaperLifecycleOutcome,
    paper: dict,
) -> bool:
    return (
        paper.get("paper_record_id") == outcome.paper_record_id
        and paper.get("guidance_id") == outcome.guidance_id
        and paper.get("playbook_id") == outcome.playbook_id
        and paper.get("proof_id") == outcome.proof_id
        and paper.get("proof_hash") == outcome.proof_hash
        and paper.get("source_snapshot_hash") == outcome.source_snapshot_hash
        and str(paper.get("symbol", "")).upper() == outcome.symbol
        and paper.get("timeframe") == outcome.timeframe
    )


def _outcome_integrity_valid(
    outcome: SimulatedPaperLifecycleOutcome,
) -> bool:
    payload = outcome.model_dump(mode="json")
    expected = payload.pop("integrity_hash")
    return _hash(payload) == expected


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


def _iso_before_ns(value: object, cutoff_ns: int) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000) < cutoff_ns


def _guidance_before_ns(row: dict, cutoff_ns: int) -> bool:
    metadata = row.get("_store_metadata")
    if not isinstance(metadata, dict):
        return True
    stored_ns = int(metadata.get("stored_at_ns", 0))
    return stored_ns < cutoff_ns
