from __future__ import annotations

import os
import hashlib
import json
import random
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from .models import (
    AuditEvent,
    CapabilityManifestItem,
    CapabilityStatus,
    FeatureVersionRecord,
    KillSwitchState,
    MarketEvent,
    PointInTimeSnapshot,
    SystemMode,
    SystemModeValue,
    TimeProviderState,
    now_iso,
)
from . import storage


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DESIGN_VAULT = Path(os.environ.get("TRADEVISION_DESIGN_VAULT", str(PROJECT_ROOT / "docs")))
KNOWLEDGE_GRAPH_PATH = DESIGN_VAULT / "graph" / "project_graph.json"

SYSTEM_MODE = SystemMode(
    mode=SystemModeValue.MOCK,
    display_label="Practice Mode - No Real Money",
    immutable=True,
    allows_live_orders=False,
    allows_broker_credentials=False,
    watermark_text="MOCK - PRACTICE MODE - NO REAL MONEY",
)

TIME_STATE = TimeProviderState(
    time_mode="virtual",
    virtual_timestamp_ns=1_714_724_800_000_000_000,
    wall_clock_time=now_iso(),
    drift_ms=0.0,
    source="mock",
    sequence_number=1,
)

DEFAULT_KILL_SWITCH = KillSwitchState(
    state="armed",
    reason=None,
    source=None,
    actor_id=None,
    triggered_at=None,
    blocks_order_paths=False,
)

storage.init_db()

KILL_SWITCH = storage.load_kill_switch() or DEFAULT_KILL_SWITCH
storage.save_kill_switch(KILL_SWITCH)

BOOT_EVENT = AuditEvent(
    event_id=str(uuid4()),
    timestamp=now_iso(),
    level="info",
    message="Trade Vision API booted in MOCK mode. Live order routing disabled.",
    source="system",
    mode=SystemModeValue.MOCK,
)
storage.save_audit_event(BOOT_EVENT)

AUDIT_EVENTS: list[AuditEvent] = storage.list_audit_events()


def audit(level: str, message: str, source: str) -> None:
    event = AuditEvent(
        event_id=str(uuid4()),
        timestamp=now_iso(),
        level=level,  # type: ignore[arg-type]
        message=message,
        source=source,
        mode=SYSTEM_MODE.mode,
    )
    storage.save_audit_event(event)
    AUDIT_EVENTS.insert(0, event)
    del AUDIT_EVENTS[100:]


def feature(
    name: str,
    status: CapabilityStatus,
    ui: str,
    services: list[str],
    contracts: list[str],
    strategy: str,
    required: bool = False,
    gates: list[str] | None = None,
) -> CapabilityManifestItem:
    return CapabilityManifestItem(
        name=name,
        status=status,
        ui_module=ui,
        backend_services=services,
        required_data_contracts=contracts,
        mock_replacement_strategy=strategy,
        required_for_startup=required,
        promotion_gates=gates or [],
    )


CAPABILITIES: list[CapabilityManifestItem] = [
    feature("TimeProvider", CapabilityStatus.MOCK, "System", ["time"], ["TimeProviderState"], "backend_clock", True, ["ACP-43"]),
    feature("SystemMode Watermark", CapabilityStatus.MOCK, "System", ["mode"], ["SystemMode"], "response_envelope", True, ["ACP-42"]),
    feature("KillSwitch", CapabilityStatus.MOCK, "System", ["killswitch"], ["KillSwitchState"], "root_guard", True, ["ACP-42"]),
    feature("CapabilityManifest", CapabilityStatus.MOCK, "System", ["features"], ["CapabilityManifest"], "manifest", True, ["ACP-30"]),
    feature("Deterministic Replay Sandbox", CapabilityStatus.MOCK, "Replay", ["replay"], ["ReplaySnapshot", "MarketEvent"], "seeded_mock", True, ["ACP-43"]),
    feature("Knowledge Graph Loader", CapabilityStatus.MOCK, "Knowledge", ["knowledge"], ["KnowledgeGraph"], "project_graph_json", True, []),
    feature("PortfolioGovernor", CapabilityStatus.MOCK, "Cockpit", ["portfolio", "risk"], ["PortfolioState", "MockRiskReport"], "mock_risk", False, ["ACP-19"]),
    feature("RealityGapDetector", CapabilityStatus.MOCK, "System", ["data_quality"], ["DataQualityReport"], "passive_mock", False, ["ACP-46"]),
    feature("MarketDNA", CapabilityStatus.MOCK, "MarketDNA", ["market"], ["MarketDNAState"], "synthetic_generator", False, ["ACP-30"]),
    feature("True Market Microstructure Engine", CapabilityStatus.MOCK, "MarketDNA", ["microstructure"], ["MicrostructureState"], "synthetic_generator", False, ["ACP-21"]),
    feature("Cognitive Coordination Layer", CapabilityStatus.MOCK, "Cockpit", ["decision"], ["CognitionDecision"], "mock_votes", False, ["ACP-29"]),
    feature("Narrative Reasoning Engine", CapabilityStatus.MOCK, "Cockpit", ["decision"], ["NarrativeExplanation", "NarrativeAuditEntry"], "read_only_mock", False, ["ACP-28"]),
    feature("ABIDES Synthetic Market Engine", CapabilityStatus.RESERVED, "Replay", ["abides"], ["MarketEvent"], "future_adapter", False, ["ACP-46"]),
    feature("hftbacktest Microstructure Fill Engine", CapabilityStatus.RESERVED, "Execution", ["hftbacktest"], ["ExecutionSimState"], "future_adapter", False, ["ACP-49"]),
    feature("DoWhy Causal Inference", CapabilityStatus.RESERVED, "MarketDNA", ["causal"], ["CognitionDecision"], "future_adapter", False, ["ACP-25"]),
    feature("CausalNex Causal Graph Builder", CapabilityStatus.RESERVED, "MarketDNA", ["causal_graph"], ["KnowledgeGraph"], "future_adapter", False, ["ACP-25"]),
    feature("QuantLib Greeks Bridge", CapabilityStatus.RESERVED, "MarketDNA", ["options"], ["MarketDNAState"], "future_adapter", False, []),
    feature("py_vollib Volatility Surface", CapabilityStatus.RESERVED, "MarketDNA", ["options"], ["MarketDNAState"], "future_adapter", False, []),
    feature("GammaExposureCalculator", CapabilityStatus.RESERVED, "MarketDNA", ["options"], ["MarketDNAState"], "future_adapter", False, []),
    feature("PatchTST Sequence Encoder", CapabilityStatus.RESERVED, "MarketDNA", ["sequence"], ["MarketDNAState"], "future_adapter", False, ["ACP-16"]),
    feature("TimesNet Periodicity Encoder", CapabilityStatus.RESERVED, "MarketDNA", ["sequence"], ["MarketDNAState"], "future_adapter", False, ["ACP-16"]),
    feature("Chronos Bounded Forecaster", CapabilityStatus.RESERVED, "Research", ["forecast"], ["MarketDNAState"], "future_adapter", False, []),
    feature("River Drift And Calibration", CapabilityStatus.RESERVED, "System", ["drift"], ["DataQualityReport"], "future_adapter", False, ["ACP-20"]),
    feature("Feature Store Versioning", CapabilityStatus.MOCK, "System", ["feature_store"], ["FeatureVersionRecord"], "sqlite_feature_registry", False, ["ACP-47"]),
    feature("Point-in-Time Immutable Data Store", CapabilityStatus.MOCK, "Research", ["data"], ["PointInTimeSnapshot"], "sqlite_snapshot_store", False, ["ACP-47"]),
    feature("Market Data Ingestion Mock", CapabilityStatus.MOCK, "Research", ["data"], ["PointInTimeSnapshot"], "seeded_ohlcv_mock", False, ["ACP-47"]),
    feature("Behavior Real OHLCV Import", CapabilityStatus.MOCK, "Behavior", ["behavior_data"], ["BehaviorOhlcvImportResult", "CandleSeries", "BehaviorDataQualityResult", "PointInTimeGuardResult"], "user_csv_research_import", True, ["TV-V040-001", "TV-V040-002", "TV-V040-003", "TV-V040-004"]),
    feature("Order Path Guard", CapabilityStatus.MOCK, "Execution", ["execution"], ["OrderPathStatus", "SimulatedOrderResult"], "kill_switch_guarded_stub", True, ["ACP-42", "ACP-50"]),
    feature("Structured Observability", CapabilityStatus.MOCK, "System", ["observability"], ["RequestLogRecord", "ObservabilityStatus"], "json_request_log", True, []),
    feature("Behavior Intelligence Contract Lock", CapabilityStatus.MOCK, "Behavior", ["behavior"], ["BehaviorSpec", "BehaviorAnalysisResult"], "contract_lock_mock", True, ["TV-BI-003", "TV-BI-004", "TV-BI-005"]),
    feature("Behavior Data Adapter", CapabilityStatus.MOCK, "Behavior", ["behavior_data"], ["BehaviorDataAdapterResult", "CandleSeries"], "point_in_time_snapshot_adapter", True, ["TV-BI-006", "TV-BI-013"]),
    feature("Behavior Data Quality Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_quality"], ["BehaviorDataQualityResult"], "candle_quality_scanner", True, ["TV-BI-006", "TV-BI-007", "TV-BI-008"]),
    feature("Behavior Point-In-Time Guard", CapabilityStatus.MOCK, "Behavior", ["behavior_guard"], ["PointInTimeGuardResult"], "causal_timestamp_guard", True, ["TV-BI-009", "TV-BI-010", "TV-BI-011", "TV-BI-012"]),
    feature("Behavior Timeframe Synchronization Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_timeframe_sync"], ["TimeframeSyncResult"], "closed_candle_alignment", True, ["TV-BI-011", "TV-BI-012", "TV-BI-013"]),
    feature("Behavior Causal Feature Whitelist", CapabilityStatus.MOCK, "Behavior", ["behavior_causal_whitelist"], ["CausalFeatureWhitelist", "CausalFeatureValidationResult"], "feature_availability_guard", True, ["TV-BI-009", "TV-BI-010"]),
    feature("Candle Structure Intelligence", CapabilityStatus.MOCK, "Behavior", ["behavior_candle_anatomy"], ["CandleAnatomyResult"], "deterministic_candle_math", True, ["TV-BI-014", "TV-BI-015"]),
    feature("Behavior Condition Classifier", CapabilityStatus.MOCK, "Behavior", ["behavior_condition_classifier"], ["ConditionClassifierResult"], "deterministic_structure_rules", True, ["TV-BI-016", "TV-BI-017", "TV-BI-018", "TV-BI-019"]),
    feature("Behavior Level Context Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_context_levels"], ["VwapOrbCprContextResult"], "vwap_orb_cpr_pdh_pdl_vpd_context", True, ["TV-BI-020"]),
    feature("Behavior HTF Confirmation Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_context_htf"], ["HTFConfirmationResult"], "closed_higher_timeframe_context", True, ["TV-BI-011", "TV-BI-012", "TV-BI-020"]),
    feature("Behavior Gap Context Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_context_gap"], ["GapContextResult"], "gap_fill_and_trap_context", True, ["TV-BI-022"]),
    feature("Behavior Market Relative Strength Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_context_market"], ["MarketContextResult"], "index_sector_relative_strength_context", True, ["TV-BI-021"]),
    feature("Behavior Market Structure Liquidity Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_market_structure_liquidity"], ["MarketStructureLiquidityRequest", "MarketStructureLiquidityReport"], "volume_profile_tpo_vsa_smc_wyckoff_trap_context", True, ["AUC-001", "AUC-002", "AUC-006", "VSA-004", "SMC-001", "TRAP-003"]),
    feature("Behavior Execution Event OI Risk Guard", CapabilityStatus.MOCK, "Behavior", ["behavior_execution_event_oi_risk"], ["ExecutionEventOiRiskRequest", "ExecutionEventOiRiskReport"], "spread_slippage_fill_event_oi_expected_move_caps", True, ["EXEC-001", "EXEC-002", "EXEC-003", "EXEC-004", "EXEC-005", "EVENT-001", "EVENT-002", "EVENT-003", "OPT-001", "OPT-002", "OPT-004"]),
    feature("Behavior Post-Entry Lifecycle Manager", CapabilityStatus.MOCK, "Behavior", ["behavior_post_entry_lifecycle"], ["PostEntryLifecycleRequest", "PostEntryLifecycleReport"], "breakeven_partial_trailing_thesis_invalidation_context", True, ["LIFE-001", "LIFE-002", "LIFE-003", "LIFE-004", "LIFE-005", "LIFE-006"]),
    feature("Behavior Final Confluence Conflict Arbiter", CapabilityStatus.MOCK, "Behavior", ["behavior_final_confluence_arbiter"], ["FinalConfluenceArbiterRequest", "FinalConfluenceArbiterReport"], "hierarchical_conflict_resolution_wait_first_final_decision", True, ["ARB-001", "ARB-002", "ARB-003", "ARB-004", "ARB-005", "ARB-006", "ARB-007", "ARB-008"]),
    feature("Behavior Full Context Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_context_full"], ["BehaviorContextResult"], "combined_context_safety_gate", True, ["TV-BI-020", "TV-BI-021", "TV-BI-022"]),
    feature("Behavior Session Rhythm Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_session_rhythm"], ["SessionRhythmResult"], "india_intraday_session_scoring", True, ["TV-BI-024", "TV-BI-025"]),
    feature("Behavior Day-Of-Week Memory", CapabilityStatus.MOCK, "Behavior", ["behavior_day_of_week_memory"], ["DayOfWeekMemoryResult"], "stock_specific_calendar_memory", True, ["TV-BI-024"]),
    feature("Behavior Stock DNA Summary", CapabilityStatus.MOCK, "Behavior", ["behavior_stock_dna_summary"], ["StockDNASummary"], "session_memory_plus_stock_dna_projection", True, ["TV-BI-026", "TV-BI-029"]),
    feature("Behavior Exact-Time Session Memory", CapabilityStatus.MOCK, "Research", ["behavior_exact_time_session_memory"], ["ExactTimeSessionMemoryRequest", "ExactTimeSessionMemoryReport", "ExactMinuteBehaviorProfile", "SessionTransitionProfile", "CalendarBehaviorProfile"], "v0_71_minute_session_day_calendar_profiles_exchange_calendar_counts", True, ["TV-V071-001", "TV-V071-002", "TV-V071-003", "TV-V071-004", "TV-V071-005", "TV-V071-006", "TV-V071-007", "TV-FI-034", "TV-FI-035"]),
    feature("Behavior Pattern Memory Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_pattern_memory"], ["PatternMemoryResult", "DayShapeVector", "SimilarDayMatch"], "day_shape_vector_similarity", True, ["TV-BI-026", "TV-BI-027", "TV-BI-028", "TV-BI-029"]),
    feature("Behavior Similar-Day Replay Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_similar_day_replay"], ["SimilarDayReplayResult", "MarketEvent"], "deterministic_similar_day_replay", True, ["TV-BI-026", "TV-BI-047"]),
    feature("Behavior Outcome Labeling Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_outcome_label"], ["OutcomeLabelResult"], "replay_outcome_labeler", True, ["TV-BI-030", "TV-BI-031", "TV-BI-032"]),
    feature("Behavior Conservative Outcome Labeler", CapabilityStatus.MOCK, "Behavior", ["behavior_conservative_outcome"], ["ConservativeOutcomeLabelRequest", "ConservativeOutcomeLabelResult", "ConservativeCostModel"], "v0_64_open_first_ambiguous_same_bar_no_fill_costed_outcome_labeler", True, ["TV-V064-001", "TV-V064-002", "TV-V064-003", "TV-V064-004", "TV-V064-005"]),
    feature("Behavior Failure Pattern Library", CapabilityStatus.MOCK, "Behavior", ["behavior_failure_library"], ["FailureLibraryResult", "FailurePatternRecord"], "stored_failure_reasoning", True, ["TV-BI-032", "TV-BI-034"]),
    feature("Behavior Learning Trust Table", CapabilityStatus.MOCK, "Behavior", ["behavior_learning_trust"], ["LearningTrustResult", "LearningTrustRecord"], "calibration_error_tracker", True, ["TV-BI-033"]),
    feature("Behavior Decision Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_decision"], ["TradeDecisionResult", "BehaviorDecisionRequest"], "universal_agreement_decision", True, ["TV-BI-034", "TV-BI-035"]),
    feature("Behavior No-Trade Intelligence", CapabilityStatus.MOCK, "Behavior", ["behavior_no_trade"], ["NoTradeDecisionRecord"], "safety_gate_blocker", True, ["TV-BI-034", "TV-BI-036", "TV-BI-037", "TV-BI-038"]),
    feature("Behavior Human-Readable Reason Tree", CapabilityStatus.MOCK, "Behavior", ["behavior_reason_tree"], ["ReasonTreeResult"], "read_only_reason_tree", True, ["TV-BI-035", "TV-BI-054", "TV-BI-055"]),
    feature("Behavior Risk Sizing Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_risk"], ["RiskSizingResult", "BehaviorRiskRequest"], "capital_position_sizer", True, ["TV-BI-036", "TV-BI-038"]),
    feature("Behavior Portfolio Exposure Control", CapabilityStatus.MOCK, "Behavior", ["behavior_portfolio_exposure"], ["PortfolioExposureRecord"], "sector_index_heat_guard", True, ["TV-BI-037"]),
    feature("Behavior Daily Loss Cooldown Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_cooldown"], ["DailyLossLimitRecord"], "loss_limit_cooldown_guard", True, ["TV-BI-036"]),
    feature("Behavior Execution Simulation Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_execution"], ["ExecutionSimulationResult", "BehaviorExecutionRequest"], "deterministic_fill_realism", True, ["TV-BI-039", "TV-BI-040", "TV-BI-041"]),
    feature("Behavior No-Fill And Partial-Fill Model", CapabilityStatus.MOCK, "Behavior", ["behavior_execution"], ["ExecutionSimulationResult"], "limit_miss_queue_partial_fill", True, ["TV-BI-040", "TV-BI-041"]),
    feature("Behavior Slippage Impact Latency Model", CapabilityStatus.MOCK, "Behavior", ["behavior_execution"], ["ExecutionCostBreakdown"], "spread_latency_impact_adverse_selection", True, ["TV-BI-039"]),
    feature("Behavior Frontend Panel Contract Map", CapabilityStatus.MOCK, "Behavior", ["behavior_frontend"], ["BehaviorFrontendPanelMapResult"], "panel_to_contract_source_of_truth", True, ["TV-BI-046"]),
    feature("Behavior Walk-Forward Validation", CapabilityStatus.MOCK, "Behavior", ["behavior_validation"], ["BehaviorValidationResult"], "deterministic_walk_forward_validation", True, ["TV-BI-048"]),
    feature("Behavior Out-Of-Sample Validation", CapabilityStatus.MOCK, "Behavior", ["behavior_validation"], ["BehaviorValidationResult"], "deterministic_out_of_sample_validation", True, ["TV-BI-049"]),
    feature("Behavior Benchmark Report Engine", CapabilityStatus.MOCK, "Behavior", ["behavior_validation"], ["BehaviorValidationResult", "BehaviorBenchmarkRun"], "validation_metrics_report", True, ["TV-BI-047", "TV-BI-048", "TV-BI-049"]),
    feature("Behavior Model Drift Detector", CapabilityStatus.MOCK, "Behavior", ["behavior_safety"], ["BehaviorDriftResult", "BehaviorDriftRequest"], "fixed_baseline_drift_guard", True, ["ACP-20", "TV-BI-050"]),
    feature("Behavior OOD Confidence Guard", CapabilityStatus.MOCK, "Behavior", ["behavior_safety"], ["BehaviorOODResult", "BehaviorOODRequest"], "feature_envelope_confidence_block", True, ["TV-BI-051"]),
    feature("Behavior Reality Gap Detector", CapabilityStatus.MOCK, "Behavior", ["behavior_safety"], ["RealityGapCheckResult", "RealityGapCheckRequest"], "replay_vs_observed_divergence_guard", True, ["ACP-46", "TV-BI-052"]),
    feature("Behavior ACP Hardening Status", CapabilityStatus.MOCK, "Behavior", ["behavior_acp"], ["BehaviorAcpHardeningResult"], "promotion_gate_summary", True, ["ACP-20", "ACP-46", "TV-BI-050", "TV-BI-051", "TV-BI-052"]),
    feature("Behavior Safety Report Store", CapabilityStatus.MOCK, "Behavior", ["behavior_safety"], ["BehaviorSafetyReport"], "immutable_hash_addressed_report_store", True, ["ACP-43", "ACP-46", "TV-BI-052"]),
    feature("Behavior Memory Quarantine Policy", CapabilityStatus.MOCK, "Behavior", ["behavior_memory"], ["MemoryQuarantineRecord", "MemoryRebuildPlan"], "quarantine_and_rebuild_workflow", True, ["ACP-26", "TV-BI-050"]),
    feature("Behavior Golden Replay Fixtures", CapabilityStatus.MOCK, "Behavior", ["behavior_replay"], ["GoldenReplayFixture", "GoldenReplayVerificationResult"], "deterministic_fixture_verification", True, ["ACP-43", "TV-BI-047"]),
    feature("Behavior Chart Replay Workbench", CapabilityStatus.MOCK, "Research", ["behavior_chart"], ["BehaviorChartReplayReport", "ReplayChartPoint", "SelectedCandleEvidence"], "safe_chart_replay_surface", True, ["TV-V041-001", "TV-V041-002", "TV-V041-003", "TV-V041-004"]),
    feature("Behavior Indicator Expansion Workbench", CapabilityStatus.MOCK, "Research", ["behavior_indicators"], ["BehaviorIndicatorExpansionReport", "IndicatorExpansionItem"], "governed_indicator_matrix_promotion", True, ["TV-V042-001", "TV-V042-002", "TV-V042-003", "TV-V042-004"]),
    feature("Behavior Stock Memory Profile", CapabilityStatus.MOCK, "Research", ["behavior_stock_memory_profile"], ["StockMemoryProfileReport"], "stock_dna_session_pattern_failure_trust_unifier", True, ["TV-V043-001", "TV-V043-002", "TV-V043-003", "TV-V043-004", "TV-V043-005"]),
    feature("Kronos Forecast Engine", CapabilityStatus.MOCK, "Research", ["kronos_proxy"], ["KronosRuntimeStatus", "KronosForecastResult"], "research_only_mock_forecast_prior", False, ["KRO-001", "KRO-010", "KRO-011", "KRO-012"]),
    feature("Kronos Shared Snapshot Contract", CapabilityStatus.MOCK, "Research", ["kronos_shared_snapshot"], ["SharedAnalysisSnapshot", "KronosSnapshotReceipt", "TwinSnapshotIntegrity", "KronosSharedSnapshotForecastReport"], "v0_66_identical_snapshot_hash_fail_closed_guard", False, ["TV-V066-001", "TV-V066-002", "TV-V066-003", "TV-V066-004", "TV-FI-071", "TV-FI-072"]),
    feature("Kronos Microservice", CapabilityStatus.MOCK, "Research", ["kronos_service"], ["KronosRuntimeStatus", "KronosServiceBridgeStatus"], "isolated_service_bridge_with_mock_fallback", False, ["KRO-002", "KRO-013", "KRO-014"]),
    feature("Twin Machine Arbiter", CapabilityStatus.MOCK, "Research", ["twin_arbiter"], ["TwinEngineComparison"], "behavior_kronos_conflict_detector", False, ["TWIN-001", "TWIN-002", "TWIN-003", "TWIN-004", "TWIN-005", "TWIN-006"]),
    feature("Full Twin Analysis", CapabilityStatus.MOCK, "Research", ["full_twin_analysis"], ["FullTwinAnalysisRequest", "FullTwinAnalysisReport", "KronosBarrierProjection", "FullBehaviorForecast"], "v0_67_shared_snapshot_behavior_memory_kronos_barrier_comparison", False, ["TV-V067-001", "TV-V067-002", "TV-V067-003", "TV-V067-004", "TV-V067-005", "TV-V067-006", "TV-FI-101", "TV-FI-102"]),
    feature("Behavior Walk-Forward Validation v0.68", CapabilityStatus.MOCK, "Research", ["behavior_walk_forward"], ["WalkForwardValidationRequest", "WalkForwardValidationReport", "WalkForwardFoldResult", "EngineValidationSummary", "FamilyWeightStabilityRecord"], "v0_68_behavior_kronos_twin_oos_calibration_and_weight_stability", True, ["TV-V068-001", "TV-V068-002", "TV-V068-003", "TV-V068-004", "TV-V068-005", "TV-V068-006", "TV-V068-007", "TV-V068-008"]),
    feature("OpenAlgo SignalIntent Export", CapabilityStatus.RESERVED, "Execution", ["openalgo_intent", "openalgo_transport", "openalgo_transport_recovery", "openalgo_transport_resilience", "openalgo_transport_security"], ["SignalIntentBundle", "BotHandoffVerificationReport", "ExecutorDryRunPackage", "ExecutorGoldenFixtureRegistry", "ExecutorAdapterConformanceReport", "ExecutorTransportOutboxRecord", "ExecutorTransportTrace", "ExecutorTransportWorkerRun", "TransportResilienceReport", "TransportIncident", "TransportFaultHarnessReport", "TransportSecurityPosture", "TransportTraceIntegrityReport"], "future_intent_export_only_no_broker_credentials", False, ["OA-001", "OA-002", "OA-003", "OA-004", "OA-005", "OA-DRY-001", "OA-DRY-002", "OA-GOLD-001", "OA-GOLD-002", "OA-CONF-001", "OA-CONF-002", "OA-TRANS-001", "OA-TRANS-002", "OA-RECOVERY-001", "OA-RECOVERY-002", "OA-SLO-001", "OA-SLO-002", "OA-SEC-001", "OA-SEC-002"]),
    feature("OpenAlgo Adapter Simulator", CapabilityStatus.MOCK, "Execution", ["openalgo_adapter_service"], ["ExecutorTransportAcknowledgement"], "isolated_hmac_receipt_service_no_broker_api", False, ["OA-TRANS-001", "OA-TRANS-002", "OA-ADAPTER-001", "OA-ADAPTER-002"]),
    feature("Research Stack Deployment Recovery", CapabilityStatus.MOCK, "System", ["deployment_readiness", "database_backup", "restore_drill"], ["DeploymentReadinessReport", "DatabaseBackupArtifact", "DatabaseRestoreDrillReport"], "brokerless_research_stack_recovery", True, ["DEPLOY-001", "DEPLOY-002", "DEPLOY-003"]),
    feature("Final Research Release Audit", CapabilityStatus.MOCK, "System", ["final_release_audit", "static_safety_scan", "release_manifest"], ["FinalProductionReadinessAudit", "StaticSafetyScanReport", "ReleaseCandidateManifest"], "evidence_based_brokerless_release_gate", True, ["RELEASE-001", "RELEASE-002", "RELEASE-003", "RELEASE-004"]),
    feature("Behavior Benchmark Report Store", CapabilityStatus.MOCK, "Behavior", ["behavior_release"], ["BehaviorBenchmarkReport"], "validation_safety_replay_report", True, ["TV-BI-047", "TV-BI-048", "TV-BI-049"]),
    feature("Mock-To-Replay Release Checklist", CapabilityStatus.MOCK, "Behavior", ["behavior_release"], ["MockToReplayReleaseChecklist", "ReleaseChecklistGate"], "manual_approval_release_gate", True, ["ACP-30", "ACP-43", "ACP-46"]),
    feature("Mock-To-Replay Approval Workflow", CapabilityStatus.MOCK, "Behavior", ["behavior_release"], ["ReleaseApprovalRequest", "ReleaseApprovalRecord"], "audited_manual_approval_stub", True, ["ACP-30", "ACP-43", "TV-BI-054"]),
    feature("Release Evidence Bundle Export", CapabilityStatus.MOCK, "Behavior", ["behavior_release"], ["ReleaseEvidenceBundle", "BenchmarkDrilldown"], "immutable_evidence_bundle", True, ["ACP-30", "ACP-43", "TV-BI-047"]),
    feature("Release Evidence Artifact Export", CapabilityStatus.MOCK, "Behavior", ["behavior_release"], ["ReleaseEvidenceArtifact", "ReleaseEvidenceArtifactVerification"], "checksum_manifest_artifact", True, ["ACP-30", "ACP-43", "TV-BI-047"]),
    feature("Behavior Scenario Coverage Drilldown", CapabilityStatus.MOCK, "Behavior", ["behavior_release"], ["BehaviorScenarioCoverageReport", "BehaviorScenarioCoverageItem"], "golden_replay_scenario_coverage", True, ["ACP-43", "TV-BI-047", "TV-BI-053"]),
    feature("Behavior Runtime Readiness Probe", CapabilityStatus.MOCK, "Research", ["behavior_runtime"], ["RuntimeReadinessReport"], "indicator_chart_replay_research_surface_probe", True, ["TV-RUNTIME-001", "TV-RUNTIME-006"]),
    feature("Behavior Indicator Registry Lock", CapabilityStatus.MOCK, "Research", ["behavior_indicator_registry"], ["BehaviorIndicatorRegistryReport", "BehaviorIndicatorRegistryEntry"], "v0_60_94_indicator_contract_lock", True, ["TV-V060-001", "TV-V060-002", "TV-V060-003", "TV-V060-004", "TV-V060-005", "TV-V060-006"]),
    feature("Behavior Indicator Intelligence Ontology", CapabilityStatus.MOCK, "Research", ["behavior_indicator_lag_voting"], ["IndicatorLagVoteRequest", "IndicatorLagVotingReport", "BehaviorIndicatorRegistryEntry"], "v1_80_indicator_ontology_lag_aware_vote_weighting", True, ["IND-ONT-001", "IND-ONT-002", "IND-ONT-003", "IND-ONT-004", "IND-ONT-005", "IND-ARB-009", "IND-ARB-010", "IND-ARB-011", "IND-ARB-012"]),
    feature("Behavior Indicator Reliability Memory", CapabilityStatus.MOCK, "Research", ["behavior_indicator_reliability_memory"], ["IndicatorSignalOutcomeLabelRequest", "IndicatorSignalOutcomeLabel", "IndicatorReliabilityReport"], "v1_81_outcome_labeled_indicator_reliability_memory", True, ["IND-REL-001", "IND-REL-002", "IND-REL-003", "IND-REL-004", "IND-REL-005", "IND-REL-006"]),
    feature("Behavior Full Timeframe Contract Expansion", CapabilityStatus.MOCK, "Research", ["behavior_timeframe_feature_runtime", "behavior_mtf_conflict", "behavior_indicator_reliability_memory"], ["SevenTimeframeFeatureRuntimeReport", "MultiTimeframeConflictReport", "PatternByTimeframeReport", "IndicatorReliabilityReport"], "v1_82_30m_4h_contract_and_reliability_drilldown", True, ["TV-V182-001", "TV-V182-002", "TV-V182-003", "TV-V182-004", "TV-V182-005"]),
    feature("Behavior Persistent Indicator Signal History", CapabilityStatus.MOCK, "Research", ["behavior_indicator_reliability_memory", "storage_indicator_signal_history"], ["IndicatorSignalHistorySaveRequest", "IndicatorSignalHistoryRecord", "IndicatorSignalHistorySummary", "IndicatorReliabilityReport"], "v1_83_persistent_indicator_signal_history_and_frontend_drilldown", True, ["TV-V183-001", "TV-V183-002", "TV-V183-003", "TV-V183-004", "TV-V183-005", "TV-V183-006"]),
    feature("Behavior Indicator Signal History Ingestion", CapabilityStatus.MOCK, "Research", ["behavior_indicator_signal_history_ingestion", "behavior_indicator_reliability_memory", "storage_indicator_signal_history"], ["IndicatorSignalHistoryIngestCurrentRequest", "IndicatorSignalHistoryIngestCurrentReport", "IndicatorSignalHistoryRecord"], "v1_84_current_closed_candle_indicator_signal_history_ingestion", True, ["TV-V184-001", "TV-V184-002", "TV-V184-003", "TV-V184-004", "TV-V184-005"]),
    feature("Behavior Indicator Pending Outcome Completion", CapabilityStatus.MOCK, "Research", ["behavior_indicator_signal_history_completion", "behavior_indicator_reliability_memory", "storage_indicator_signal_history"], ["IndicatorSignalHistoryCompletePendingRequest", "IndicatorSignalHistoryCompletePendingReport", "IndicatorSignalHistoryRecord"], "v1_85_future_horizon_completion_for_pending_indicator_history", True, ["TV-V185-001", "TV-V185-002", "TV-V185-003", "TV-V185-004", "TV-V185-005"]),
    feature("Paper Guidance Spine P0", CapabilityStatus.MOCK, "Jarvis", ["paper_guidance_spine"], ["PaperGuidanceRequest", "PaperGuidanceSafetyGate", "ClosedCandleSnapshot", "PaperTradeGuidance"], "v1_87_d1_safety_d2_closed_candle_snapshot_contract", True, ["TV-V187-001", "TV-V187-002", "TV-V187-003", "TV-V187-004", "TV-V187-005", "TV-V187-006", "TV-V187-007", "TV-V187-008", "TV-V187-009", "TV-V187-010", "TV-V187-011", "TV-V187-012", "TV-V187-013"]),
    feature("Paper Guidance Spine P1", CapabilityStatus.MOCK, "Jarvis", ["paper_guidance_spine", "final_confluence_arbiter"], ["PaperGuidanceEngineReceipt", "PaperGuidanceMtfEvidence", "PaperTradeGuidance"], "v1_88_snapshot_native_guidance_and_d6_caps", True, [f"TV-V188-{index:03d}" for index in range(1, 21)]),
    feature("ORB Core Foundation", CapabilityStatus.MOCK, "Research", ["orb.core"], ["OrbSessionDefinition", "OrbStrategyConfig", "OrbBuildRequest", "OrbOpeningRange", "OrbSignalCandidate", "OrbBuildResult"], "v1_89_orb_session_range_and_signal_contracts", False, [f"TV-V189-{index:03d}" for index in range(1, 13)]),
    feature("ORB Offline Discovery", CapabilityStatus.MOCK, "Research", ["orb.discovery"], ["OrbDiscoveryRequest", "OrbDiscoveryJob", "OrbDiscoveryResult", "OrbComboMetrics", "OrbBacktestTrade"], "v1_90_capped_cost_aware_async_discovery", False, [f"TV-V190-{index:03d}" for index in range(1, 13)]),
    feature("ORB Proof And Playbooks", CapabilityStatus.MOCK, "Research", ["orb.proof"], ["OrbProofRequest", "OrbProofReport", "OrbComboProof", "OrbPlaybookPromotionRequest", "OrbPlaybook"], "v1_91_oos_walkforward_proof_and_atomic_playbook_store", False, [f"TV-V191-{index:03d}" for index in range(1, 13)]),
    feature("ORB Jarvis Guidance", CapabilityStatus.MOCK, "Jarvis", ["behavior.orb_guidance", "final_confluence_arbiter"], ["OrbGuidanceTicket", "PaperTradeGuidance"], "v1_92_proof_backed_orb_entry_authority_with_existing_veto_gates", True, [f"TV-V192-{index:03d}" for index in range(1, 13)]),
    feature("ORB Simulated Paper Ledger", CapabilityStatus.MOCK, "Jarvis", ["behavior.simulated_paper_ledger"], ["SimulatedPaperRecordApprovalRequest", "SimulatedPaperTradeRecord"], "v1_93_explicit_human_approved_local_paper_record", True, [f"TV-V193-{index:03d}" for index in range(1, 11)]),
    feature("ORB Paper Lifecycle Feedback", CapabilityStatus.MOCK, "Jarvis", ["behavior.orb_paper_lifecycle", "behavior.orb_paper_feedback", "behavior.atomic_json_store"], ["SimulatedPaperLifecycleObservationRequest", "SimulatedPaperLifecycleOutcome", "OrbPaperReliabilityReport", "PaperGuidanceStorageMonitor"], "v1_94_explicit_replay_outcome_feedback_and_fail_closed_storage", True, [f"TV-V194-{index:03d}" for index in range(1, 33)]),
    feature("ORB Opening Scenarios", CapabilityStatus.MOCK, "Research", ["orb.context"], ["OrbOpeningScenario"], "v2_01_gap_cpr_zone_opening_classification", False, [f"TV-V201-{index:03d}" for index in range(1, 7)]),
    feature("Behavior Indicator Observation Contracts", CapabilityStatus.MOCK, "Research", ["behavior_indicator_observations"], ["IndicatorObservationRequest", "IndicatorObservation", "IndicatorObservationReport"], "v0_69_complete_indicator_observation_value_lineage_availability_contract", True, ["TV-V069-001", "TV-V069-002", "TV-V069-003", "TV-V069-004", "TV-V069-005", "TV-V069-006"]),
    feature("Behavior Structure Pattern Registry", CapabilityStatus.MOCK, "Research", ["behavior_pattern_taxonomy"], ["PatternTaxonomyRequest", "PatternTaxonomyReport", "PatternTaxonomyEntry", "PatternActivityRecord", "TrendlineRespectEvidence"], "v0_70_candle_swing_chart_harmonic_level_trendline_flow_pattern_lifecycle_contracts", True, ["TV-V070-001", "TV-V070-002", "TV-V070-003", "TV-V070-004", "TV-V070-005", "TV-V070-006", "TV-V070-007"]),
    feature("Behavior Multi-Timeframe Conflict Engine", CapabilityStatus.MOCK, "Research", ["behavior_mtf_conflict"], ["MultiTimeframeConflictRequest", "MultiTimeframeConflictReport", "TimeframeStateRecord", "MultiTimeframeConflictExplanation"], "v0_72_seven_timeframe_matrix_developing_bar_alignment_conflict_explanations", True, ["TV-V072-001", "TV-V072-002", "TV-V072-003", "TV-V072-004", "TV-V072-005", "TV-FI-036", "TV-FI-037"]),
    feature("Behavior Real MTF Pullback Engine", CapabilityStatus.MOCK, "Research", ["behavior_real_mtf_pullback"], ["RealMtfPullbackRequest", "RealMtfPullbackReport", "RealMtfPullbackTimeframeSummary", "RealMtfPullbackGate"], "v1_63_closed_candle_mtf_pullback_htf_opposition_watch_avoid_classifier", True, ["TV-V163-001", "TV-V163-002", "TV-V163-003", "TV-V163-004", "TV-V163-005", "TV-V163-006"]),
    feature("Behavior Seven-Timeframe Feature Runtime", CapabilityStatus.MOCK, "Research", ["behavior_timeframe_feature_runtime"], ["SevenTimeframeFeatureRuntimeReport", "ClosedBarRuntimeRecord", "RuntimeIndicatorCoverageRecord"], "v0_61_closed_bar_feature_runtime", True, ["TV-V061-001", "TV-V061-002", "TV-V061-003", "TV-V061-004", "TV-V061-005", "TV-V061-006"]),
    feature("Behavior Columnar Historical Feature Store", CapabilityStatus.MOCK, "Research", ["behavior_feature_store"], ["FeatureStoreWriteReport", "FeatureSnapshotRecord", "FeatureStoreStatusReport"], "v0_62_partitioned_feature_store_metadata", True, ["TV-V062-001", "TV-V062-002", "TV-V062-003", "TV-V062-004", "TV-V062-005", "TV-V062-006"]),
    feature("Behavior Redundancy Control", CapabilityStatus.MOCK, "Research", ["behavior_redundancy"], ["RedundancyAuditReport", "RedundancyCluster", "FeatureFamilyScore", "SuppressedDuplicateFeature"], "v0_63_family_caps_and_duplicate_inflation_guard", True, ["TV-V063-001", "TV-V063-002", "TV-V063-003", "TV-V063-004", "TV-V063-005", "TV-V063-006"]),
    feature("Behavior Combination Similarity", CapabilityStatus.MOCK, "Research", ["behavior_combination_similarity"], ["CombinationSimilarityRequest", "CombinationSimilarityReport", "CombinationAnalogMatch", "SequentialSignalPattern"], "v0_65_hard_context_weighted_sequence_non_overlap_analog_retrieval", True, ["TV-V065-001", "TV-V065-002", "TV-V065-003", "TV-V065-004", "TV-V065-005", "TV-V065-006", "TV-V065-007"]),
    feature("Behavior Analog Conditional Research", CapabilityStatus.MOCK, "Research", ["behavior_analog_research"], ["AnalogResearchRequest", "AnalogConditionalResearchReport", "ValueBandDiscoveryRecord", "ConditionalRuleRecord", "AnalogMatchExplanation", "FalseDiscoveryControlReport"], "v0_73_mixed_distance_value_band_conditional_fdr_holdout_explanations", True, ["TV-V073-001", "TV-V073-002", "TV-FI-044", "TV-FI-045", "TV-FI-046", "TV-FI-047", "TV-FI-048", "TV-FI-049", "TV-FI-050", "TV-FI-061", "TV-FI-062", "TV-FI-096"]),
    feature("Behavior Event Sequence Mining", CapabilityStatus.MOCK, "Research", ["behavior_event_sequence_mining"], ["EventSequenceMiningRequest", "EventSequenceMiningReport", "EventSequencePatternRecord", "IndicatorEventRecord", "ReciprocalSignalRecord", "PriorToCurrentInfluenceRecord"], "v0_74_same_candle_lagged_reciprocal_prior_to_current_sequence_mining", True, ["TV-V074-001", "TV-V074-002", "TV-V074-003", "TV-FI-090", "TV-FI-091", "TV-FI-092", "TV-FI-111", "TV-FI-112", "TV-FI-113"]),
    feature("Behavior False Agreement Confluence Diagnostics", CapabilityStatus.MOCK, "Research", ["behavior_false_agreement_confluence"], ["FalseAgreementConfluenceRequest", "FalseAgreementConfluenceReport", "ConfluenceTimingWindowRecord", "IndicatorValueConfluenceRecord", "FalseAgreementRecord"], "v0_75_nominal_agreement_independent_evidence_redundancy_false_agreement_blocks", True, ["TV-V075-001", "TV-V075-002", "TV-V075-003", "TV-V075-004", "TV-V075-005", "TV-V075-006", "TV-FI-092", "TV-FI-094"]),
    feature("Behavior Design Similarity Shape Grammar", CapabilityStatus.MOCK, "Research", ["behavior_design_similarity"], ["DesignSimilarityRequest", "DesignSimilarityReport", "ShapeGrammarComponent", "GeometryReferenceRecord", "DesignSimilarityCandidate", "ChartOverlayEvidenceRecord"], "v0_76_price_invariant_shape_grammar_geometry_overlay_evidence", True, ["TV-V076-001", "TV-V076-002", "TV-V076-003", "TV-V076-004", "TV-FI-038", "TV-FI-039", "TV-FI-040", "TV-FI-078", "TV-FI-082", "TV-FI-093"]),
    feature("Behavior Band Level Distance Memory", CapabilityStatus.MOCK, "Research", ["behavior_band_level_distance"], ["BandLevelDistanceRequest", "BandLevelDistanceReport", "LevelDistanceRecord", "RepeatedValueClusterRecord", "LevelDistanceOutcomeInfluence", "MissingLevelRecord"], "v0_77_band_level_distance_value_cluster_memory", True, ["TV-V077-001", "TV-V077-002", "TV-V077-003", "TV-V077-004", "TV-V077-005", "TV-FI-043", "TV-FI-047", "TV-FI-054", "TV-FI-077"]),
    feature("Behavior Pattern By Timeframe Outcome Memory", CapabilityStatus.MOCK, "Research", ["behavior_pattern_by_timeframe"], ["PatternByTimeframeRequest", "PatternByTimeframeReport", "TimeframePatternOutcomeRecord", "TimeframeFailureReasonRecord", "HigherTimeframeInteractionRecord", "TimeframePatternTrustImpact"], "v0_78_per_timeframe_pattern_outcome_htf_interaction_trust_memory", True, ["TV-V078-001", "TV-V078-002", "TV-V078-003", "TV-V078-004", "TV-V078-005", "TV-V078-006", "TV-FI-081", "TV-FI-082"]),
    feature("Behavior Market Calendar Event Regime Memory", CapabilityStatus.MOCK, "Research", ["behavior_market_calendar_event_regime"], ["MarketCalendarEventRegimeRequest", "MarketCalendarEventRegimeReport", "EventRegimeFlagRecord", "CalendarPatternReliabilityRecord", "EventDaySafetyRuleRecord", "CalendarContextLinkRecord"], "v0_79_calendar_event_regime_reliability_and_safety_gates", True, ["TV-V079-001", "TV-V079-002", "TV-V079-003", "TV-V079-004", "TV-V079-005", "TV-V079-006", "TV-V079-007", "TV-FI-035"]),
    feature("Behavior Cross-Market Influence Memory", CapabilityStatus.MOCK, "Research", ["behavior_cross_market_influence"], ["CrossMarketInfluenceRequest", "CrossMarketInfluenceReport", "CrossMarketSignalRecord", "CrossMarketSessionInfluenceRecord", "CrossMarketConflictRecord", "CrossMarketCoverageRecord"], "v0_80_cross_market_optional_context_coverage_and_conflict_gates", True, ["TV-V080-001", "TV-V080-002", "TV-V080-003", "TV-V080-004", "TV-V080-005", "TV-V080-006", "TV-FI-042", "TV-FI-089"]),
    feature("Behavior Corporate Action Abnormal Market Memory", CapabilityStatus.MOCK, "Research", ["behavior_corporate_action_abnormal_market"], ["CorporateActionAbnormalMarketRequest", "CorporateActionAbnormalMarketReport", "CorporateActionEventRecord", "AbnormalMarketEventRecord", "MemoryContaminationRecord", "MemoryQuarantineActionRecord"], "v0_81_corporate_action_abnormal_market_quarantine_memory", True, ["TV-V081-001", "TV-V081-002", "TV-V081-003", "TV-V081-004", "TV-V081-005", "TV-V081-006", "TV-FI-053", "TV-FI-106"]),
    feature("Behavior Position Portfolio Cooldown Memory", CapabilityStatus.MOCK, "Research", ["behavior_position_portfolio_cooldown"], ["PositionPortfolioCooldownRequest", "PositionPortfolioCooldownReport", "AccountRiskSizingRecord", "PortfolioHeatMemoryRecord", "DailyWeeklyCooldownRecord", "ExposureCapRecord"], "v0_82_position_sizing_portfolio_heat_daily_weekly_cooldown_memory", True, ["TV-V082-001", "TV-V082-002", "TV-V082-003", "TV-V082-004", "TV-V082-005", "TV-BI-036", "TV-BI-037"]),
    feature("Behavior Execution Intent Paper Safety Memory", CapabilityStatus.MOCK, "Research", ["behavior_execution_intent_paper_safety"], ["ExecutionIntentPaperSafetyRequest", "ExecutionIntentPaperSafetyReport", "ExecutionIntentLifecycleRecord", "PaperSimulationEstimateRecord", "ExecutorManualReviewRecord"], "v0_83_execution_intent_paper_simulator_safety_memory", True, ["TV-V083-001", "TV-V083-002", "TV-V083-003", "TV-V083-004", "TV-FI-019", "TV-FI-020", "TV-FI-109", "TV-FI-110"]),
    feature("Behavior Paper Executor Permission Matrix", CapabilityStatus.MOCK, "Research", ["behavior_paper_executor_permission"], ["PaperExecutorPermissionRequest", "PaperExecutorPermissionReport", "ModePermissionMatrixRow", "KillSwitchRecheckRecord", "HumanApprovalGateRecord", "ExecutorPreflightGateRecord"], "v0_84_human_approval_kill_switch_recheck_paper_executor_permission_matrix", True, ["TV-V084-001", "TV-V084-002", "TV-V084-003", "TV-V084-004", "TV-V084-005", "TV-V084-006", "TV-V084-007", "TV-V084-008", "TV-V084-009", "TV-FI-110"]),
    feature("Behavior Executor Handoff Audit Envelope", CapabilityStatus.MOCK, "Research", ["behavior_executor_handoff_audit"], ["ExecutorHandoffAuditRequest", "ExecutorHandoffAuditEnvelope", "ExecutorHandoffImmutableReceipt", "ExecutorHandoffEvidenceBinding", "ExecutorHandoffIntentAuditRecord"], "v0_85_immutable_preflight_receipt_and_handoff_audit_envelope", True, ["TV-V085-001", "TV-V085-002", "TV-V085-003", "TV-V085-004", "TV-V085-005", "TV-FI-110"]),
    feature("Behavior Replay Indicator Chart Validation", CapabilityStatus.MOCK, "Research", ["behavior_replay_indicator_chart"], ["ReplayIndicatorValidationReport", "ReplayIndicatorPoint", "ReplayChartPoint"], "deterministic_replay_to_indicator_chart_probe", True, ["ACP-43", "TV-BI-047"]),
    feature("Behavior Replay Indicator Matrix", CapabilityStatus.MOCK, "Research", ["behavior_replay_indicator_matrix"], ["ReplayIndicatorMatrixReport", "ReplayIndicatorMatrixRow"], "replay_fed_32_row_indicator_matrix", True, ["ACP-43", "TV-BI-047", "TV-BI-053"]),
    feature("Behavior Matrix Decision Readiness", CapabilityStatus.MOCK, "Research", ["behavior_matrix_decision"], ["MatrixDecisionReadinessReport", "MatrixDecisionGate"], "matrix_to_wait_no_trade_replay_candidate_gates", True, ["TV-BI-034", "TV-BI-035", "TV-BI-054"]),
    feature("Behavior Trade Lifecycle Simulation", CapabilityStatus.MOCK, "Research", ["behavior_trade_lifecycle"], ["TradeLifecycleSimulationReport", "OutcomeLabelResult", "ExecutionSimulationResult"], "readiness_to_shadow_lifecycle_state_path", True, ["TV-BI-030", "TV-BI-039", "TV-BI-040", "TV-BI-041", "TV-BI-054"]),
    feature("Behavior Lifecycle Scenario Comparison", CapabilityStatus.MOCK, "Research", ["behavior_lifecycle_comparison"], ["TradeLifecycleScenarioComparisonReport", "TradeLifecycleScenarioComparisonItem"], "multi_scenario_shadow_lifecycle_comparison", True, ["TV-BI-030", "TV-BI-039", "TV-BI-047", "TV-BI-054"]),
    feature("Behavior Lifecycle Evidence Drilldown", CapabilityStatus.MOCK, "Research", ["behavior_lifecycle_evidence"], ["LifecycleEvidenceDrilldownReport", "LifecycleEvidenceScenarioDrilldown", "LifecycleEvidenceRowContribution"], "row_level_driver_and_safety_pressure_audit", True, ["TV-BI-034", "TV-BI-035", "TV-BI-047", "TV-BI-054"]),
    feature("Behavior Tradeability Guidance", CapabilityStatus.MOCK, "Research", ["behavior_tradeability_guidance"], ["TradeabilityGuidanceReport", "ScenarioTradeabilityGuidance", "TradeabilityImprovementStep"], "research_only_blocker_and_improvement_targets", True, ["TV-BI-034", "TV-BI-035", "TV-BI-047", "TV-BI-054"]),
    feature("Stock-App Chart Indicator Backtest Migration", CapabilityStatus.RESERVED, "Behavior", ["migration"], ["BehaviorSpec"], "legacy_source_register", False, ["TV-BI-046"]),
    feature("Latency Budget Manager", CapabilityStatus.RESERVED, "System", ["runtime"], ["PipelineState"], "future_guard", False, ["ACP-44"]),
    feature("SessionEngine", CapabilityStatus.RESERVED, "MarketDNA", ["session"], ["MarketDNAState"], "future_context", False, []),
    feature("Event-Time Market Memory", CapabilityStatus.RESERVED, "MarketDNA", ["event_memory"], ["MarketEvent"], "future_memory", False, ["ACP-22"]),
    feature("Dynamic Temporal Graph Memory", CapabilityStatus.RESERVED, "Knowledge", ["temporal_graph"], ["KnowledgeGraph"], "future_graph", False, ["ACP-23"]),
    feature("Counterfactual Reasoning Engine", CapabilityStatus.RESERVED, "Replay", ["counterfactual"], ["NarrativeExplanation"], "read_only_future", False, ["ACP-25"]),
    feature("Memory Poisoning Protection", CapabilityStatus.RESERVED, "System", ["security"], ["DataQualityReport"], "future_quarantine", False, ["ACP-26"]),
    feature("Market Hierarchy Engine", CapabilityStatus.RESERVED, "MarketDNA", ["hierarchy"], ["MarketDNAState"], "future_context", False, ["ACP-27"]),
    feature("Compute Governor", CapabilityStatus.RESERVED, "System", ["runtime"], ["PipelineState"], "future_guard", False, ["ACP-44"]),
    feature("Exchange Reconciliation", CapabilityStatus.RESERVED, "Execution", ["exchange"], ["ExecutionSimState"], "future_guard", False, ["ACP-50"]),
    feature("Execution Slippage Simulator", CapabilityStatus.MOCK, "Execution", ["behavior_execution"], ["ExecutionSimulationResult", "ExecutionCostBreakdown"], "deterministic_mock_slippage_model", False, ["ACP-49", "TV-BI-039"]),
    feature("LearningGovernor", CapabilityStatus.RESERVED, "System", ["learning"], ["DataQualityReport"], "future_guard", False, []),
    feature("Graph Decay And Compaction", CapabilityStatus.RESERVED, "Knowledge", ["graph"], ["KnowledgeGraph"], "future_hygiene", False, ["ACP-53"]),
]

storage.save_capability_snapshot(CAPABILITIES)


def deterministic_events(seed: int, scenario_id: str, count: int = 16) -> list[MarketEvent]:
    rng = random.Random(f"{scenario_id}:{seed}")
    base = TIME_STATE.virtual_timestamp_ns
    events: list[MarketEvent] = []
    for idx in range(count):
        payload = {
            "price": round(100 + rng.uniform(-1.8, 2.4) + idx * 0.08, 4),
            "volume": rng.randint(800, 4200),
            "imbalance": round(rng.uniform(-0.75, 0.75), 4),
        }
        raw = json.dumps({"idx": idx, "payload": payload, "seed": seed, "scenario": scenario_id}, sort_keys=True)
        events.append(
            MarketEvent(
                event_id=str(uuid5(NAMESPACE_URL, f"tradevision:{scenario_id}:{seed}:{idx}")),
                parent_event_id=events[-1].event_id if events else None,
                virtual_timestamp_ns=base + idx * 60_000_000_000,
                source_mode=SYSTEM_MODE.mode,
                sequence_number=idx + 1,
                symbol="NIFTY-MOCK",
                payload=payload,
                watermark=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            )
        )
    return events


def deterministic_ohlcv_snapshot(symbol: str, seed: int, bars: int) -> tuple[PointInTimeSnapshot, list[FeatureVersionRecord]]:
    rng = random.Random(f"ohlcv:{symbol}:{seed}:{bars}")
    base = TIME_STATE.virtual_timestamp_ns
    rows = []
    price = 100.0 + rng.uniform(-2, 2)
    for idx in range(bars):
        open_price = price
        close_price = max(1.0, open_price + rng.uniform(-1.2, 1.2))
        high = max(open_price, close_price) + rng.uniform(0, 0.8)
        low = min(open_price, close_price) - rng.uniform(0, 0.8)
        volume = rng.randint(1_000, 18_000)
        rows.append(
            {
                "t": base + idx * 60_000_000_000,
                "o": round(open_price, 4),
                "h": round(high, 4),
                "l": round(low, 4),
                "c": round(close_price, 4),
                "v": volume,
            }
        )
        price = close_price

    payload = {
        "symbol": symbol,
        "timeframe": "1m",
        "bars": rows,
        "source": "deterministic_mock",
        "leakage_policy": "point_in_time_only",
    }
    payload_json = json.dumps(payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    snapshot_id = str(uuid5(NAMESPACE_URL, f"tradevision:snapshot:{symbol}:{seed}:{bars}:{payload_hash}"))
    snapshot = PointInTimeSnapshot(
        snapshot_id=snapshot_id,
        symbol=symbol,
        source_mode=SYSTEM_MODE.mode,
        seed=seed,
        as_of_timestamp_ns=rows[-1]["t"],
        created_at=now_iso(),
        schema_version="ohlcv.v1",
        payload_hash=payload_hash,
        payload=payload,
        immutable=True,
    )

    closes = [row["c"] for row in rows]
    returns = [round((closes[i] / closes[i - 1]) - 1.0, 8) for i in range(1, len(closes))]
    avg_return = round(sum(returns) / max(1, len(returns)), 8)
    realized_vol = round((sum((r - avg_return) ** 2 for r in returns) / max(1, len(returns))) ** 0.5, 8)
    features = {
        "return_mean": avg_return,
        "realized_volatility": realized_vol,
        "last_close": closes[-1],
        "sample_size": len(rows),
    }
    feature_records: list[FeatureVersionRecord] = []
    for name, value in features.items():
        parameters = {"value": value, "source_payload_hash": payload_hash}
        feature_hash = hashlib.sha256(json.dumps({"name": name, "snapshot": snapshot_id, "parameters": parameters}, sort_keys=True).encode("utf-8")).hexdigest()
        feature_records.append(
            FeatureVersionRecord(
                feature_hash=feature_hash,
                name=name,
                schema_version="feature.v1",
                pipeline_version="mock-feature-pipeline.v0.3",
                source_commit="local-dev",
                created_at=now_iso(),
                input_snapshot_id=snapshot_id,
                parameters=parameters,
            )
        )
    return snapshot, feature_records
