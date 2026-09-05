from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorIndicatorExpansionReport,
    BehaviorIndicatorExpansionRequest,
    IndicatorExpansionItem,
    MarketEvent,
    ReplayIndicatorMatrixRequest,
    RuntimeReadinessGate,
)
from .replay_indicator_matrix import build_replay_indicator_matrix_report


EXPANSION_VERSION = "behavior-indicator-expansion-workbench.v0.42"
CANDIDATE_OUTPUT_GROUPS = 94


def build_indicator_expansion_report(
    request: BehaviorIndicatorExpansionRequest,
    events: list[MarketEvent],
) -> BehaviorIndicatorExpansionReport:
    matrix = build_replay_indicator_matrix_report(
        ReplayIndicatorMatrixRequest(
            symbol=request.symbol,
            scenario_id=request.scenario_id,
            seed=request.seed,
            event_count=request.event_count,
            timeframe=request.timeframe,
            required_matrix_rows=request.required_matrix_rows,
        ),
        events,
    )
    items: list[IndicatorExpansionItem] = []
    for row in matrix.rows:
        status = _status(row.readiness_status)
        if status == "proxy" and not request.include_proxy:
            continue
        items.append(
            IndicatorExpansionItem(
                row_id=row.row_id,
                family=row.family,
                layer_index=row.layer_index,
                contract_name=row.contract_name,
                status=status,
                signal=row.signal,
                latest_value=row.latest_value,
                normalized_score=row.normalized_score,
                chart_overlay_key=row.chart_overlay_key,
                output_fields=row.output_fields,
                point_in_time_safe=row.point_in_time_safe,
                explanation=row.explanation,
            )
        )
    counts = Counter(item.status for item in items)
    family_coverage = dict(sorted(Counter(item.family for item in items).items()))
    output_hash = _hash_output(
        {
            "expansion_version": EXPANSION_VERSION,
            "matrix_output_hash": matrix.output_hash,
            "include_proxy": request.include_proxy,
            "items": [item.model_dump(mode="json") for item in items],
        }
    )
    gates = _gates(matrix, items, counts)
    return BehaviorIndicatorExpansionReport(
        expansion_version=EXPANSION_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:{EXPANSION_VERSION}:{matrix.run_id}:{request.include_proxy}")),
        base_matrix_version=matrix.matrix_version,
        symbol=matrix.symbol,
        scenario_id=matrix.scenario_id,
        seed=matrix.seed,
        timeframe=request.timeframe,
        event_count=matrix.event_count,
        candidate_output_groups=CANDIDATE_OUTPUT_GROUPS,
        base_indicator_count=matrix.base_indicator_count,
        matrix_indicator_count=matrix.matrix_indicator_count,
        promoted_indicator_count=counts["promoted"],
        proxy_indicator_count=counts["proxy"],
        blocked_indicator_count=counts["blocked"],
        family_coverage=family_coverage,
        items=items,
        input_event_chain_hash=matrix.input_event_chain_hash,
        matrix_output_hash=matrix.output_hash,
        output_hash=output_hash,
        deterministic=True,
        no_future_leakage=matrix.no_future_leakage,
        runtime_dependency_on_legacy_stock_app=False,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.42 expands the Research indicator surface from 6 base overlays into a governed 32-row replay matrix.",
            "Only ready rows are promoted; proxy rows stay visibly labelled as proxy until implemented with full indicator math.",
            "The full 94-group migrated inventory remains visible through runtime readiness, but only point-in-time-safe rows are exposed here.",
        ],
    )


def _status(readiness_status: str) -> Literal["promoted", "proxy", "blocked"]:
    if readiness_status == "ready":
        return "promoted"
    if readiness_status == "proxy":
        return "proxy"
    return "blocked"


def _gates(matrix, items: list[IndicatorExpansionItem], counts: Counter) -> list[RuntimeReadinessGate]:
    return [
        _gate("TV-V042-001", "Matrix source available", matrix.matrix_indicator_count == 32, f"{matrix.matrix_indicator_count} replay matrix rows available."),
        _gate("TV-V042-002", "Promoted indicators available", counts["promoted"] >= 10, f"{counts['promoted']} rows promoted from ready status."),
        _gate("TV-V042-003", "Proxy rows labelled", counts["proxy"] >= 1, f"{counts['proxy']} rows kept as proxy, not falsely promoted."),
        _gate("TV-V042-004", "No blocked indicator rows exposed as tradable", all(item.status != "blocked" or item.signal == "blocked" for item in items), "Blocked rows cannot become trade signals."),
        _gate("TV-V042-005", "Point-in-time indicator expansion", matrix.no_future_leakage and all(item.point_in_time_safe for item in items), "All exposed indicator rows are point-in-time safe."),
        _gate("TV-V042-006", "Live trading blocked", True, "Indicator expansion is research-only and exposes no order route."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> RuntimeReadinessGate:
    return RuntimeReadinessGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "fail",
        evidence=evidence,
        blocks_research=not passed,
        remediation=None if passed else "Fix indicator expansion before promoting additional research rows.",
    )


def _hash_output(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
