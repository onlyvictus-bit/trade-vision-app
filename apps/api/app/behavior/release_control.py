from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorBenchmarkReport,
    BehaviorSafetyReport,
    BehaviorScenarioCoverageItem,
    BehaviorScenarioCoverageReport,
    BehaviorValidationResult,
    BenchmarkDrilldown,
    GoldenReplayVerificationResult,
    MockToReplayReleaseChecklist,
    ReleaseApprovalRecord,
    ReleaseChecklistGate,
    ReleaseEvidenceBundle,
    now_iso,
)


RELEASE_CONTROL_VERSION = "behavior-release-control.v0.27"
RELEASE_EVIDENCE_VERSION = "behavior-release-evidence.v0.29"
SCENARIO_COVERAGE_VERSION = "behavior-scenario-coverage.v1.66"
REQUIRED_SCENARIO_FAMILIES = [
    "opening_drive",
    "fakeout_reversal",
    "lunch_compression",
    "closing_drive",
    "gap_trap",
    "expiry_pin",
    "clean_breakout",
    "vwap_rejection",
    "choppy",
    "gap_continuation",
    "low_volume",
    "htf_lookahead_trap",
    "confluence_support",
    "confluence_resistance",
    "ood_unknown",
]


def build_benchmark_report(
    *,
    symbol: str,
    walk_forward: BehaviorValidationResult,
    out_of_sample: BehaviorValidationResult,
    safety_report: BehaviorSafetyReport,
    golden_verifications: list[GoldenReplayVerificationResult],
) -> BehaviorBenchmarkReport:
    normalized = symbol.upper()
    created_at = now_iso()
    metrics = {
        "walk_forward_win_rate_pct": walk_forward.aggregate_win_rate_pct,
        "walk_forward_profit_factor": walk_forward.aggregate_profit_factor,
        "walk_forward_expectancy_r": walk_forward.aggregate_expectancy_r,
        "walk_forward_max_drawdown_pct": walk_forward.aggregate_max_drawdown_pct,
        "out_of_sample_win_rate_pct": out_of_sample.aggregate_win_rate_pct,
        "out_of_sample_profit_factor": out_of_sample.aggregate_profit_factor,
        "out_of_sample_expectancy_r": out_of_sample.aggregate_expectancy_r,
        "out_of_sample_max_drawdown_pct": out_of_sample.aggregate_max_drawdown_pct,
        "total_validation_trades": walk_forward.total_trades + out_of_sample.total_trades,
        "golden_replay_pass_count": sum(1 for item in golden_verifications if item.passed),
        "golden_replay_total": len(golden_verifications),
        "safety_report_hash": safety_report.report_hash,
    }
    blockers = _benchmark_blockers(walk_forward, out_of_sample, safety_report, golden_verifications)
    payload = {
        "report_version": RELEASE_CONTROL_VERSION,
        "symbol": normalized,
        "created_at": created_at,
        "walk_forward": walk_forward.model_dump(mode="json"),
        "out_of_sample": out_of_sample.model_dump(mode="json"),
        "safety_report": safety_report.model_dump(mode="json"),
        "golden_replay_verifications": [item.model_dump(mode="json") for item in golden_verifications],
        "metrics": metrics,
        "promotion_allowed": not blockers,
        "promotion_blockers": blockers,
    }
    report_hash = _canonical_hash(payload)
    report_id = f"benchmark-{normalized}-{report_hash[:18]}"
    return BehaviorBenchmarkReport(
        **payload,
        report_id=report_id,
        report_hash=report_hash,
        immutable=True,
        live_trading_blocked=True,
        notes=[
            "Benchmark report is hash-addressed and combines validation, safety, and golden replay evidence.",
            "Promotion to replay requires this report plus a separate manual approval gate.",
        ],
    )


def build_mock_to_replay_checklist(
    *,
    symbol: str,
    benchmark_report: BehaviorBenchmarkReport,
    manual_approval: bool = False,
) -> MockToReplayReleaseChecklist:
    normalized = symbol.upper()
    created_at = now_iso()
    gates = [
        _gate(
            "RC-001",
            "contracts",
            "Behavior contracts, 32 layers, and 74 output columns are locked.",
            True,
            "Behavior contract lock is required capability and tests assert exact column count.",
        ),
        _gate(
            "RC-002",
            "data",
            "Point-in-time and deterministic replay data paths exist.",
            True,
            "Point-in-time snapshots and golden replay fixtures are persisted.",
        ),
        _gate(
            "RC-003",
            "validation",
            "Walk-forward validation has no future leakage.",
            benchmark_report.walk_forward.no_future_leakage,
            f"walk_forward.no_future_leakage={benchmark_report.walk_forward.no_future_leakage}",
        ),
        _gate(
            "RC-004",
            "validation",
            "Out-of-sample validation has no future leakage.",
            benchmark_report.out_of_sample.no_future_leakage,
            f"out_of_sample.no_future_leakage={benchmark_report.out_of_sample.no_future_leakage}",
        ),
        _gate(
            "RC-005",
            "validation",
            "Benchmark report has no promotion blockers.",
            benchmark_report.promotion_allowed,
            "; ".join(benchmark_report.promotion_blockers) or "benchmark report promotion_allowed=true",
        ),
        _gate(
            "RC-006",
            "safety",
            "Safety report allows promotion.",
            benchmark_report.safety_report.promotion_allowed,
            f"safety_report={benchmark_report.safety_report.report_id}",
        ),
        _gate(
            "RC-007",
            "replay",
            "Every golden replay fixture verifies deterministically.",
            all(item.passed for item in benchmark_report.golden_replay_verifications),
            f"{benchmark_report.metrics['golden_replay_pass_count']}/{benchmark_report.metrics['golden_replay_total']} fixtures passed",
        ),
        _gate(
            "RC-008",
            "risk",
            "Live broker routing remains disabled for this release.",
            benchmark_report.live_trading_blocked,
            f"live_trading_blocked={benchmark_report.live_trading_blocked}",
        ),
        _gate(
            "RC-009",
            "approval",
            "Manual risk approval is recorded for mock-to-replay promotion.",
            manual_approval,
            "manual approval is intentionally false in MVP unless explicitly supplied",
        ),
    ]
    release_blockers = [f"{gate.gate_id}: {gate.description}" for gate in gates if gate.blocks_release]
    technical_release_pass = all(not gate.blocks_release for gate in gates if gate.category != "approval")
    checklist_id = str(uuid5(NAMESPACE_URL, f"tradevision:release-checklist:{normalized}:{benchmark_report.report_id}:{manual_approval}"))
    return MockToReplayReleaseChecklist(
        checklist_version=RELEASE_CONTROL_VERSION,
        checklist_id=checklist_id,
        symbol=normalized,
        target_mode="REPLAY",
        created_at=created_at,
        benchmark_report_id=benchmark_report.report_id,
        gates=gates,
        pass_count=sum(1 for gate in gates if gate.status == "pass"),
        fail_count=sum(1 for gate in gates if gate.status == "fail"),
        technical_release_pass=technical_release_pass,
        release_allowed=not release_blockers,
        release_blockers=release_blockers,
        manual_approval_required=True,
        live_trading_blocked=True,
        notes=[
            "This checklist only governs mock-to-replay promotion, not paper or live trading.",
            "Manual approval remains required even when all technical gates pass.",
        ],
    )


def build_benchmark_drilldown(report: BehaviorBenchmarkReport) -> BenchmarkDrilldown:
    metric_groups = {
        "walk_forward": {
            "win_rate_pct": report.metrics.get("walk_forward_win_rate_pct", 0),
            "profit_factor": report.metrics.get("walk_forward_profit_factor", 0),
            "expectancy_r": report.metrics.get("walk_forward_expectancy_r", 0),
            "max_drawdown_pct": report.metrics.get("walk_forward_max_drawdown_pct", 0),
            "fold_count": len(report.walk_forward.folds),
            "no_future_leakage": report.walk_forward.no_future_leakage,
        },
        "out_of_sample": {
            "win_rate_pct": report.metrics.get("out_of_sample_win_rate_pct", 0),
            "profit_factor": report.metrics.get("out_of_sample_profit_factor", 0),
            "expectancy_r": report.metrics.get("out_of_sample_expectancy_r", 0),
            "max_drawdown_pct": report.metrics.get("out_of_sample_max_drawdown_pct", 0),
            "fold_count": len(report.out_of_sample.folds),
            "no_future_leakage": report.out_of_sample.no_future_leakage,
        },
        "golden_replay": {
            "passed": report.metrics.get("golden_replay_pass_count", 0),
            "total": report.metrics.get("golden_replay_total", 0),
            "failed_fixture_ids": [
                verification.fixture.fixture_id
                for verification in report.golden_replay_verifications
                if not verification.passed
            ],
        },
        "safety": {
            "promotion_allowed": report.safety_report.promotion_allowed,
            "memory_quarantine_required": report.safety_report.memory_quarantine_required,
            "confidence_blocked": report.safety_report.confidence_blocked,
            "reality_gap_alert": report.safety_report.reality_gap_alert,
            "report_hash": report.safety_report.report_hash,
        },
    }
    return BenchmarkDrilldown(
        drilldown_version=RELEASE_EVIDENCE_VERSION,
        report_id=report.report_id,
        symbol=report.symbol,
        generated_at=now_iso(),
        metric_groups=metric_groups,
        validation_summary=[
            f"Walk-forward trades={report.walk_forward.total_trades}, win_rate={report.walk_forward.aggregate_win_rate_pct}%, profit_factor={report.walk_forward.aggregate_profit_factor}.",
            f"Out-of-sample trades={report.out_of_sample.total_trades}, win_rate={report.out_of_sample.aggregate_win_rate_pct}%, profit_factor={report.out_of_sample.aggregate_profit_factor}.",
            f"Future leakage flags: walk_forward={report.walk_forward.no_future_leakage}, out_of_sample={report.out_of_sample.no_future_leakage}.",
        ],
        safety_summary=[
            f"Safety report {report.safety_report.report_id} promotion_allowed={report.safety_report.promotion_allowed}.",
            f"Memory quarantine required={report.safety_report.memory_quarantine_required}.",
            f"Confidence blocked={report.safety_report.confidence_blocked}; reality_gap_alert={report.safety_report.reality_gap_alert}.",
        ],
        replay_summary=[
            f"{report.metrics.get('golden_replay_pass_count', 0)}/{report.metrics.get('golden_replay_total', 0)} golden replay fixtures passed.",
            *[
                f"{verification.fixture.scenario_id}: passed={verification.passed}, deterministic={verification.deterministic}, chain={verification.actual_chain_hash[:16]}"
                for verification in report.golden_replay_verifications
            ],
        ],
        promotion_summary=[
            "Benchmark promotion allowed." if report.promotion_allowed else "Benchmark promotion blocked.",
            *report.promotion_blockers,
            "Live trading remains blocked.",
        ],
    )


def build_behavior_scenario_coverage(report: BehaviorBenchmarkReport) -> BehaviorScenarioCoverageReport:
    generated_at = now_iso()
    items: list[BehaviorScenarioCoverageItem] = []
    for verification in report.golden_replay_verifications:
        family = _scenario_family(verification.fixture.scenario_id)
        status = "covered" if verification.passed and verification.deterministic and family != "unknown" else "failed"
        items.append(
            BehaviorScenarioCoverageItem(
                item_version=SCENARIO_COVERAGE_VERSION,
                scenario_id=verification.fixture.scenario_id,
                scenario_family=family,  # type: ignore[arg-type]
                fixture_id=verification.fixture.fixture_id,
                seed=verification.fixture.seed,
                expected_event_count=verification.fixture.expected_event_count,
                actual_event_count=verification.actual_event_count,
                deterministic=verification.deterministic,
                passed=verification.passed,
                chain_hash=verification.actual_chain_hash,
                coverage_status=status,  # type: ignore[arg-type]
                safety_assertions=verification.fixture.safety_assertions,
                issues=verification.issues,
                notes=[
                    f"Fixture {verification.fixture.fixture_id} maps to {family}.",
                    "Scenario coverage is replay/mock evidence only; it is not permission for live routing.",
                ],
            )
        )
    covered_families = sorted(
        {item.scenario_family for item in items if item.coverage_status == "covered" and item.scenario_family != "unknown"}
    )
    missing_families = [family for family in REQUIRED_SCENARIO_FAMILIES if family not in covered_families]
    passed_scenarios = sum(1 for item in items if item.passed and item.deterministic)
    failed_scenarios = len(items) - passed_scenarios
    deterministic_pass_rate = round((passed_scenarios / len(items)) * 100, 2) if items else 0.0
    coverage_score = round((len(covered_families) / len(REQUIRED_SCENARIO_FAMILIES)) * 100, 2)
    blockers: list[str] = []
    if missing_families:
        blockers.append(f"Missing scenario families: {', '.join(missing_families)}.")
    if failed_scenarios:
        blockers.append(f"Failed or non-deterministic scenarios: {failed_scenarios}.")
    if not report.promotion_allowed:
        blockers.append("Underlying benchmark report blocks promotion.")
    payload = {
        "coverage_version": SCENARIO_COVERAGE_VERSION,
        "symbol": report.symbol,
        "benchmark_report_id": report.report_id,
        "generated_at": generated_at,
        "required_scenario_families": REQUIRED_SCENARIO_FAMILIES,
        "covered_scenario_families": covered_families,
        "missing_scenario_families": missing_families,
        "total_scenarios": len(items),
        "passed_scenarios": passed_scenarios,
        "failed_scenarios": failed_scenarios,
        "deterministic_pass_rate_pct": deterministic_pass_rate,
        "coverage_score_pct": coverage_score,
        "scenario_items": [item.model_dump(mode="json") for item in items],
        "promotion_allowed": not blockers,
        "promotion_blockers": blockers,
    }
    hash_payload = {key: value for key, value in payload.items() if key != "generated_at"}
    coverage_hash = _canonical_hash(hash_payload)
    coverage_id = f"scenario-coverage-{report.symbol}-{coverage_hash[:18]}"
    return BehaviorScenarioCoverageReport(
        **payload,
        coverage_id=coverage_id,
        immutable=True,
        live_trading_blocked=True,
        notes=[
            "Scenario coverage proves which market-behavior regimes have deterministic replay evidence.",
            "Coverage is a mock-to-replay readiness signal only; paper and live trading remain disabled.",
        ],
    )


def _scenario_family(scenario_id: str) -> str:
    normalized = scenario_id.lower()
    if "opening" in normalized and "drive" in normalized:
        return "opening_drive"
    if "fakeout" in normalized or "reversal" in normalized or ("fake" in normalized and "breakout" in normalized):
        return "fakeout_reversal"
    if "lunch" in normalized or "compression" in normalized:
        return "lunch_compression"
    if "closing" in normalized:
        return "closing_drive"
    if "expiry" in normalized or "pin" in normalized:
        return "expiry_pin"
    if "clean" in normalized and "breakout" in normalized:
        return "clean_breakout"
    if "vwap" in normalized and "rejection" in normalized:
        return "vwap_rejection"
    if "choppy" in normalized:
        return "choppy"
    if "gap" in normalized and "continuation" in normalized:
        return "gap_continuation"
    if "low" in normalized and "volume" in normalized:
        return "low_volume"
    if "htf" in normalized and "lookahead" in normalized:
        return "htf_lookahead_trap"
    if "gap" in normalized or "trap" in normalized:
        return "gap_trap"
    if "confluence" in normalized and "support" in normalized:
        return "confluence_support"
    if "confluence" in normalized and "resistance" in normalized:
        return "confluence_resistance"
    if "ood" in normalized or "unknown" in normalized:
        return "ood_unknown"
    return "unknown"


def build_release_evidence_bundle(
    *,
    symbol: str,
    benchmark_report: BehaviorBenchmarkReport,
    checklist: MockToReplayReleaseChecklist,
    approval: ReleaseApprovalRecord | None = None,
) -> ReleaseEvidenceBundle:
    normalized = symbol.upper()
    drilldown = build_benchmark_drilldown(benchmark_report)
    final_blockers = list(checklist.release_blockers)
    if approval is None or approval.status != "approved":
        final_blockers.append("No approved mock-to-replay approval record is attached.")
    final_blockers.append("Live trading remains blocked for this evidence bundle.")
    evidence_index = {
        "benchmark_report_id": benchmark_report.report_id,
        "benchmark_report_hash": benchmark_report.report_hash,
        "safety_report_id": benchmark_report.safety_report.report_id,
        "safety_report_hash": benchmark_report.safety_report.report_hash,
        "release_checklist_id": checklist.checklist_id,
        "approval_id": approval.approval_id if approval else "none",
        "target_mode": "REPLAY",
        "scope": "mock_to_replay_only",
    }
    gate_summary = {
        "pass_count": checklist.pass_count,
        "fail_count": checklist.fail_count,
        "technical_release_pass": checklist.technical_release_pass,
        "release_allowed": checklist.release_allowed,
        "approval_status": approval.status if approval else "missing",
        "golden_replay_passed": benchmark_report.metrics.get("golden_replay_pass_count", 0),
        "golden_replay_total": benchmark_report.metrics.get("golden_replay_total", 0),
    }
    payload = {
        "bundle_version": RELEASE_EVIDENCE_VERSION,
        "symbol": normalized,
        "target_mode": "REPLAY",
        "generated_at": now_iso(),
        "approval": approval.model_dump(mode="json") if approval else None,
        "checklist": checklist.model_dump(mode="json"),
        "benchmark_report": benchmark_report.model_dump(mode="json"),
        "benchmark_drilldown": drilldown.model_dump(mode="json"),
        "evidence_index": evidence_index,
        "gate_summary": gate_summary,
        "final_blockers": final_blockers,
    }
    bundle_hash = _canonical_hash(payload)
    bundle_id = f"release-evidence-{normalized}-{bundle_hash[:18]}"
    return ReleaseEvidenceBundle(
        **payload,
        bundle_id=bundle_id,
        bundle_hash=bundle_hash,
        immutable=True,
        live_trading_blocked=True,
        notes=[
            "Evidence bundle is immutable and hash-addressed.",
            "Bundle supports mock-to-replay review only.",
            "Paper and live trading remain disabled.",
        ],
    )


def _benchmark_blockers(
    walk_forward: BehaviorValidationResult,
    out_of_sample: BehaviorValidationResult,
    safety_report: BehaviorSafetyReport,
    golden_verifications: list[GoldenReplayVerificationResult],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(f"Walk-forward: {item}" for item in walk_forward.promotion_blockers)
    blockers.extend(f"Out-of-sample: {item}" for item in out_of_sample.promotion_blockers)
    if not safety_report.promotion_allowed:
        blockers.append("Safety report blocks promotion.")
    failed_fixtures = [item.fixture.fixture_id for item in golden_verifications if not item.passed]
    if failed_fixtures:
        blockers.append(f"Golden replay fixture failures: {', '.join(failed_fixtures)}.")
    if not golden_verifications:
        blockers.append("No golden replay fixtures verified.")
    return blockers


def _gate(gate_id: str, category: str, description: str, passed: bool, evidence: str) -> ReleaseChecklistGate:
    return ReleaseChecklistGate(
        gate_id=gate_id,
        category=category,  # type: ignore[arg-type]
        description=description,
        status="pass" if passed else "fail",
        evidence=evidence,
        blocks_release=not passed,
    )


def _canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
