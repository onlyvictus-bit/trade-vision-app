from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from ..models import (
    CombinationSimilarityRequest,
    ExecutorDryRunPackageRequest,
    LifecycleEvidenceDrilldownRequest,
    TradeabilityGuidanceRequest,
    TradeLifecycleScenarioComparisonRequest,
    TradeLifecycleSimulationRequest,
)
from .combination_similarity import build_combination_similarity_report
from .execution_intent_paper_safety import build_execution_intent_paper_safety_report
from .external_ai_reliability import build_external_ai_reliability_report
from .jarvis_candle_cause_effect_memory import build_candle_cause_effect_memory_report
from .jarvis_chart_overlay_qa import build_chart_overlay_qa_report
from .jarvis_daily_verified_authority import build_daily_verified_authority_report
from .jarvis_decision_quality_gate import build_decision_quality_gate_report
from .jarvis_indicator_combination_memory import build_indicator_combination_memory_report
from .jarvis_openalgo_handoff_gate import build_openalgo_handoff_gate_report
from .jarvis_paper_execution_loop import build_paper_execution_loop_report
from .jarvis_trading_decision_output import build_trading_decision_output_report
from .jarvis_verified_evidence import build_jarvis_verified_evidence_certificate
from .openalgo_adapter_harness import build_openalgo_adapter_harness_status
from .trade_lifecycle_simulation import (
    build_lifecycle_evidence_drilldown_report,
    build_trade_lifecycle_scenario_comparison_report,
    build_trade_lifecycle_simulation_report,
    build_tradeability_guidance_report,
)


JARVIS_EVIDENCE_ASSEMBLY_VERSION = "jarvis-evidence-assembly.v1.26"

JARVIS_EVIDENCE_ASSEMBLY_TOTAL_BUDGET_MS = 1_500.0
JARVIS_EVIDENCE_ASSEMBLY_STAGE_BUDGETS_MS: dict[str, float] = {
    "decision_room": 220.0,
    "combination_similarity": 90.0,
    "indicator_memory": 90.0,
    "candle_memory": 90.0,
    "external_ai_reliability": 80.0,
    "verified_evidence": 70.0,
    "daily_authority": 70.0,
    "paper_safety": 50.0,
    "lifecycle": 130.0,
    "lifecycle_comparison": 160.0,
    "lifecycle_evidence": 130.0,
    "tradeability": 130.0,
    "paper_loop": 90.0,
    "executor_package": 90.0,
    "package_verification": 90.0,
    "openalgo_transport": 120.0,
    "openalgo_adapter": 90.0,
    "openalgo_handoff": 120.0,
    "decision_quality": 90.0,
    "trading_decision_output": 90.0,
    "chart_overlay_qa": 70.0,
}


def _stage_status(elapsed_ms: float, budget_ms: float) -> str:
    if elapsed_ms > budget_ms * 1.5:
        return "over_budget"
    if elapsed_ms > budget_ms:
        return "warning"
    return "within_budget"


def build_jarvis_evidence_bundle(
    *,
    symbol: str,
    timeframe: str,
    rows: int,
    position: str,
    stale_after_seconds: int,
    project_root: Path,
    build_room: Callable[[str, str, int, str], dict[str, Any]],
    external_records: list[dict[str, Any]],
    export_executor_dry_run_package: Callable[[ExecutorDryRunPackageRequest], Any],
    verify_executor_dry_run_package: Callable[[Any], Any],
    get_transport_status: Callable[..., Any],
    get_deterministic_events: Callable[[int, str, int], list[Any]],
) -> dict[str, Any]:
    normalized = symbol.upper()
    stage_timings: list[dict[str, Any]] = []

    def timed(stage: str, builder: Callable[[], Any]) -> Any:
        started = perf_counter()
        result = builder()
        elapsed_ms = round((perf_counter() - started) * 1000.0, 3)
        budget_ms = JARVIS_EVIDENCE_ASSEMBLY_STAGE_BUDGETS_MS.get(stage, 100.0)
        stage_timings.append(
            {
                "stage": stage,
                "elapsed_ms": elapsed_ms,
                "budget_ms": budget_ms,
                "status": _stage_status(elapsed_ms, budget_ms),
            }
        )
        return result

    room = timed("decision_room", lambda: build_room(normalized, timeframe, rows, position))
    combo = timed(
        "combination_similarity",
        lambda: build_combination_similarity_report(CombinationSimilarityRequest(symbol=normalized, timeframe=timeframe)),
    )
    indicator_memory = timed(
        "indicator_memory",
        lambda: build_indicator_combination_memory_report(room=room, combination_similarity=combo),
    )
    candle_memory = timed("candle_memory", lambda: build_candle_cause_effect_memory_report(room=room))
    reliability = timed(
        "external_ai_reliability",
        lambda: build_external_ai_reliability_report(
        symbol=normalized,
        room=room,
        records=external_records,
        stale_after_seconds=stale_after_seconds,
        ),
    )
    verified = timed(
        "verified_evidence",
        lambda: build_jarvis_verified_evidence_certificate(
        symbol=normalized,
        room=room,
        external_ai_reliability=reliability,
        ),
    )
    daily = timed(
        "daily_authority",
        lambda: build_daily_verified_authority_report(
        symbol=normalized,
        room=room,
        stale_after_seconds=86_400,
        ),
    )
    paper_safety = timed("paper_safety", build_execution_intent_paper_safety_report)
    lifecycle_payload = TradeLifecycleSimulationRequest(symbol=normalized, timeframe=timeframe)
    lifecycle_events = timed(
        "lifecycle_events",
        lambda: get_deterministic_events(lifecycle_payload.seed, lifecycle_payload.scenario_id, lifecycle_payload.event_count),
    )
    lifecycle = timed("lifecycle", lambda: build_trade_lifecycle_simulation_report(lifecycle_payload, lifecycle_events))
    comparison_payload = TradeLifecycleScenarioComparisonRequest(symbol=normalized, timeframe=timeframe)
    comparison = timed(
        "lifecycle_comparison",
        lambda: build_trade_lifecycle_scenario_comparison_report(comparison_payload, get_deterministic_events),
    )
    evidence_payload = LifecycleEvidenceDrilldownRequest(symbol=normalized, timeframe=timeframe)
    lifecycle_evidence = timed(
        "lifecycle_evidence",
        lambda: build_lifecycle_evidence_drilldown_report(evidence_payload, get_deterministic_events),
    )
    guidance_payload = TradeabilityGuidanceRequest(symbol=normalized, timeframe=timeframe)
    guidance = timed("tradeability", lambda: build_tradeability_guidance_report(guidance_payload, get_deterministic_events))
    paper_loop = timed(
        "paper_loop",
        lambda: build_paper_execution_loop_report(
        symbol=normalized,
        jarvis_room=room,
        paper_safety=paper_safety,
        lifecycle=lifecycle,
        lifecycle_comparison=comparison,
        lifecycle_evidence=lifecycle_evidence,
        tradeability=guidance,
        ),
    )
    package = timed(
        "executor_package",
        lambda: export_executor_dry_run_package(ExecutorDryRunPackageRequest(symbol=normalized, target_executor="openalgo")),
    )
    package_verification = timed("package_verification", lambda: verify_executor_dry_run_package(package))
    transport = timed("openalgo_transport", lambda: get_transport_status(check_health=True))
    adapter = timed(
        "openalgo_adapter",
        lambda: build_openalgo_adapter_harness_status(
        project_root=project_root,
        transport_status=transport,
        ),
    )
    handoff = timed(
        "openalgo_handoff",
        lambda: build_openalgo_handoff_gate_report(
        symbol=normalized,
        jarvis_room=room,
        dry_run_package=package,
        package_verification=package_verification,
        transport_status=transport,
        adapter_harness=adapter,
        ),
    )
    quality = timed(
        "decision_quality",
        lambda: build_decision_quality_gate_report(
        symbol=normalized,
        jarvis_room=room,
        external_ai_reliability=reliability,
        verified_evidence=verified,
        daily_authority=daily,
        paper_execution_loop=paper_loop,
        openalgo_handoff_gate=handoff,
        ),
    )
    decision_output = timed(
        "trading_decision_output",
        lambda: build_trading_decision_output_report(
        symbol=normalized,
        jarvis_room=room,
        indicator_memory=indicator_memory,
        candle_memory=candle_memory,
        decision_quality_gate=quality,
        ),
    )
    chart_overlay_qa = timed(
        "chart_overlay_qa",
        lambda: build_chart_overlay_qa_report(
        symbol=normalized,
        jarvis_room=room,
        trading_decision_output=decision_output,
        ),
    )
    total_latency_ms = round(sum(item["elapsed_ms"] for item in stage_timings), 3)
    slow_stage_count = sum(1 for item in stage_timings if item["status"] != "within_budget")
    latency_state = "over_budget" if total_latency_ms > JARVIS_EVIDENCE_ASSEMBLY_TOTAL_BUDGET_MS else "warning" if slow_stage_count else "within_budget"
    return {
        "assembly_version": JARVIS_EVIDENCE_ASSEMBLY_VERSION,
        "symbol": normalized,
        "timeframe": timeframe,
        "latency_state": latency_state,
        "total_latency_ms": total_latency_ms,
        "total_budget_ms": JARVIS_EVIDENCE_ASSEMBLY_TOTAL_BUDGET_MS,
        "slow_stage_count": slow_stage_count,
        "stage_timings": stage_timings,
        "room": room,
        "combination_similarity": combo,
        "indicator_memory": indicator_memory,
        "candle_memory": candle_memory,
        "external_ai_reliability": reliability,
        "verified_evidence": verified,
        "daily_authority": daily,
        "paper_safety": paper_safety,
        "lifecycle": lifecycle,
        "lifecycle_comparison": comparison,
        "lifecycle_evidence": lifecycle_evidence,
        "tradeability": guidance,
        "paper_loop": paper_loop,
        "executor_package": package,
        "executor_package_verification": package_verification,
        "transport_status": transport,
        "adapter_harness": adapter,
        "openalgo_handoff": handoff,
        "decision_quality": quality,
        "trading_decision_output": decision_output,
        "chart_overlay_qa": chart_overlay_qa,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
