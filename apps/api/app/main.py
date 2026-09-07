from __future__ import annotations

import json
import hashlib
import os
import tempfile
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    ApiEnvelope,
    CapabilityManifest,
    CapabilityStatus,
    AuditIntegrityReport,
    BehaviorAnalysisResult,
    BehaviorAnalyzeRequest,
    BehaviorAcpHardeningResult,
    BehaviorBenchmarkRun,
    BehaviorBenchmarkReport,
    BotHandoffVerificationRequest,
    BehaviorContextRequest,
    BehaviorDataAdapterRequest,
    BehaviorChartReplayRequest,
    BehaviorDecisionRequest,
    BehaviorDriftRequest,
    BehaviorIndicatorExpansionRequest,
    KronosBacktestRequest,
    KronosForecastRequest,
    BehaviorOhlcvImportRequest,
    BehaviorExecutionRequest,
    BehaviorLayerContract,
    BehaviorMemoryRecord,
    BehaviorOODRequest,
    BehaviorOutputColumn,
    BehaviorRiskRequest,
    BehaviorReplayRecord,
    BehaviorSafetyReport,
    BehaviorScenarioCoverageReport,
    BehaviorSpec,
    BehaviorValidationRequest,
    CandleAnatomyRequest,
    CandleBar,
    CandleSeries,
    CausalFeatureValidationRequest,
    ChartReasoningRequest,
    CognitionDecision,
    ConditionClassifierRequest,
    AnalogResearchRequest,
    CombinationSimilarityRequest,
    ConservativeOutcomeLabelRequest,
    DataQualityReport,
    DatabaseBackupArtifact,
    EngineVote,
    ExecutionEventOiRiskRequest,
    ExecutionSimState,
    ExecutorAdapterConformanceCase,
    ExecutorAdapterConformanceReport,
    ExecutorAdapterConformanceRequest,
    ExecutorAdapterObservedResult,
    ExecutorDryRunPackage,
    ExecutorDryRunPackageRequest,
    ExecutorDryRunPackageVerification,
    ExecutorHandoffAuditRequest,
    ExecutorGoldenFixture,
    ExecutorGoldenFixtureRegistry,
    ExecutorGoldenFixtureVerification,
    ExecutorRejectionExample,
    ExecutorTransportEnqueueRequest,
    ExecutorTransportOperatorAction,
    ExecutorTransportWorkerRequest,
    EventSequenceMiningRequest,
    FalseAgreementConfluenceRequest,
    FinalConfluenceArbiterRequest,
    DesignSimilarityRequest,
    BandLevelDistanceRequest,
    PatternByTimeframeRequest,
    MarketCalendarEventRegimeRequest,
    CrossMarketInfluenceRequest,
    CorporateActionAbnormalMarketRequest,
    ExecutionIntentPaperSafetyRequest,
    PaperExecutorPermissionRequest,
    PaperGuidanceRequest,
    PaperTradeGuidance,
    OrbBuildRequest,
    OrbBuildResult,
    OrbDiscoveryJob,
    OrbDiscoveryRequest,
    OrbTimingResearchJob,
    OrbTimingResearchRequest,
    OrbTimingResearchResult,
    OrbPlaybook,
    OrbPlaybookPromotionRequest,
    OrbProofReport,
    OrbProofRequest,
    OrbGuidanceTicket,
    OrbPaperReliabilityReport,
    PaperGuidanceStorageMonitor,
    SimulatedPaperRecordApprovalRequest,
    SimulatedPaperLifecycleObservationRequest,
    SimulatedPaperLifecycleOutcome,
    SimulatedPaperTradeRecord,
    PositionPortfolioCooldownRequest,
    TransportFaultHarnessRequest,
    TransportIncidentAction,
    GapContextRequest,
    HealthState,
    HTFConfirmationRequest,
    ExactTimeSessionMemoryRequest,
    IndicatorObservationRequest,
    IndicatorLagVoteRequest,
    IndicatorSignalHistoryCompletePendingRequest,
    IndicatorSignalHistoryIngestCurrentRequest,
    IndicatorSignalHistorySaveRequest,
    IndicatorSignalOutcomeLabelRequest,
    KillSwitchResetRequest,
    KillSwitchState,
    KillSwitchTriggerRequest,
    LifecycleEvidenceDrilldownRequest,
    MarketContextRequest,
    MarketRegimeFeedbackRequest,
    MarketStructureLiquidityRequest,
    MarketDNAState,
    MemoryQuarantineRequest,
    MatrixDecisionReadinessRequest,
    MicrostructureState,
    MockIngestRequest,
    MockRiskReport,
    MultiTimeframeConflictRequest,
    NarrativeAuditEntry,
    NarrativeExplanation,
    NineCandleBuildRequest,
    NineCandleOutcomeLabelRequest,
    NineCandleSaveSetupRequest,
    OperatorIdentity,
    OrderPathStatus,
    OutcomeLabelRequest,
    PanelBounds,
    PanelConfig,
    PatternMemoryRequest,
    PatternTaxonomyRequest,
    PipelineState,
    PipelineStep,
    PointInTimeGuardRequest,
    PortfolioState,
    PostEntryLifecycleRequest,
    RealityGapCheckRequest,
    ReadyState,
    ReleaseApprovalDecisionRequest,
    ReleaseApprovalRecord,
    ReleaseApprovalRequest,
    ReleaseEvidenceArtifact,
    ReleaseEvidenceArtifactExportRequest,
    ReleaseEvidenceArtifactVerification,
    ReleaseEvidenceBundle,
    ReplayIndicatorMatrixRequest,
    ReplayArchiveSummary,
    ReplayIndicatorValidationReport,
    ReplayIndicatorValidationRequest,
    ReplayControlRequest,
    ReplaySeekRequest,
    ReplaySnapshot,
    ReplayStepRequest,
    ReplayStartRequest,
    SessionRhythmRequest,
    SimulatedOrderRequest,
    SimulatedOrderResult,
    SharedSnapshotRequest,
    SimulationIntegrityReport,
    SimilarDayMatch,
    StockDNAProfile,
    StockMemoryProfileRequest,
    SystemModeValue,
    TwinTournamentRequest,
    SevenTimeframeFeatureRuntimeRequest,
    FeatureStoreWriteRequest,
    FullTwinAnalysisRequest,
    RedundancyAuditRequest,
    RealMtfPullbackRequest,
    TimeframeSyncRequest,
    TradeabilityGuidanceRequest,
    TradeLifecycleScenarioComparisonRequest,
    TradeLifecycleSimulationRequest,
    VwapOrbCprContextRequest,
    WalkForwardValidationRequest,
    WorkspaceLayout,
    now_iso,
)
from .behavior.pattern_memory import (
    analyze_pattern_memory,
    build_similar_day_replay,
)
from .behavior.outcome_learning import (
    build_failure_library,
    build_learning_trust,
    label_trade_outcome,
)
from .behavior.outcome_labeler import label_conservative_outcome
from .behavior.decision_engine import evaluate_trade_decision
from .behavior.risk_engine import evaluate_behavior_risk
from .behavior.execution_simulator import simulate_behavior_execution
from .behavior.frontend_panels import build_behavior_frontend_panel_map
from .behavior.validation import run_behavior_validation
from .behavior.safety_hardening import (
    build_acp_hardening_status,
    default_drift_request,
    default_ood_request,
    default_reality_gap_request,
    evaluate_behavior_drift,
    evaluate_behavior_ood,
    evaluate_reality_gap,
    high_drift_request,
    high_ood_request,
    high_reality_gap_request,
)
from .behavior.operational_safety import (
    build_golden_replay_fixture,
    build_memory_quarantine,
    build_memory_rebuild_plan,
    build_safety_report,
    verify_golden_replay_fixture,
)
from .behavior.release_control import (
    build_benchmark_drilldown,
    build_benchmark_report,
    build_behavior_scenario_coverage,
    build_mock_to_replay_checklist,
    build_release_evidence_bundle,
)
from .behavior.runtime_readiness import build_runtime_readiness_report
from .behavior.feature_manifest_integrity import build_feature_manifest_integrity_report
from .behavior.indicator_registry import build_indicator_registry_report
from .behavior.indicator_lag_voting import build_indicator_intelligence_summary, build_indicator_lag_voting_report
from .behavior.indicator_reliability_memory import (
    build_indicator_reliability_report,
    build_indicator_signal_history_report,
    label_indicator_signal_outcome,
    save_indicator_signal_history,
)
from .behavior.indicator_signal_history_completion import complete_pending_indicator_signal_history
from .behavior.indicator_signal_history_ingestion import ingest_current_indicator_signal_history
from .behavior.indicator_runtime_bridge import build_indicator_runtime_report
from .behavior.indicator_promotion_gates import build_indicator_promotion_report
from .behavior.indicator_runtime_coverage import build_indicator_runtime_coverage_report
from .behavior.indicator_result_cache import (
    delete_indicator_cache,
    indicator_cache_results,
    indicator_cache_status,
    save_indicator_results,
)
from .behavior.red_team_final_gate import build_tv_prod_red_001_report
from .behavior.level_proximity import build_level_proximity_report
from .behavior.level_confluence import build_level_confluence_report
from .behavior.level_memory_extended import build_level_memory_report
from .behavior.regime_gate import build_regime_gate_report
from .behavior.hypothesis_engine import build_hypothesis_report
from .behavior.nine_candle_calibration import build_model_promotion_guard
from .behavior.nine_candle_history import build_ood_status_report, build_path_analog_report
from .behavior.nine_candle_hybrid import (
    build_analogs as build_nine_candle_analogs,
    build_calibration_bins as build_nine_candle_calibration,
    build_current_dna as build_nine_candle_dna,
    build_evidence_packet as build_nine_candle_evidence_packet,
    build_feature_vector_audit as build_nine_candle_feature_vector_audit,
    build_feature_manifest as build_nine_candle_feature_manifest,
    build_index_manifest as build_nine_candle_index_manifest,
    build_indicator_alignment as build_nine_candle_indicator_alignment,
    build_jarvis_panel as build_nine_candle_jarvis_panel,
    build_model_status as build_nine_candle_model_status,
    build_model_status_for as build_nine_candle_model_status_for,
    build_setup_memory as build_nine_candle_setup_memory,
    label_outcomes as label_nine_candle_outcomes,
    save_setup as save_nine_candle_setup,
    build_calibration_bins_for as build_nine_candle_calibration_for,
)
from .behavior.indicator_observations import build_indicator_observation_report
from .behavior.pattern_taxonomy import build_pattern_taxonomy_report
from .behavior.exact_time_session_memory import build_exact_time_session_memory_report
from .behavior.multi_timeframe_conflict import build_multi_timeframe_conflict_report
from .behavior.real_mtf_pullback import build_real_mtf_pullback_report
from .behavior.timeframe_feature_builder import build_seven_timeframe_feature_runtime
from .behavior.feature_store import feature_store_status, write_feature_store
from .behavior.feature_redundancy import build_redundancy_audit
from .behavior.combination_similarity import build_combination_similarity_report
from .behavior.analog_research import build_analog_conditional_research_report
from .behavior.event_sequence_mining import build_event_sequence_mining_report
from .behavior.false_agreement_confluence import build_false_agreement_confluence_report
from .behavior.design_similarity import build_design_similarity_report
from .behavior.band_level_distance import build_band_level_distance_report
from .behavior.pattern_by_timeframe import build_pattern_by_timeframe_report
from .behavior.market_calendar_event_regime import build_market_calendar_event_regime_report
from .behavior.cross_market_influence import build_cross_market_influence_report
from .behavior.corporate_action_abnormal_market import build_corporate_action_abnormal_market_report
from .behavior.position_portfolio_cooldown import build_position_portfolio_cooldown_report
from .behavior.execution_intent_paper_safety import build_execution_intent_paper_safety_report
from .behavior.paper_executor_permission import build_paper_executor_permission_report
from .behavior.executor_handoff_audit import build_executor_handoff_audit_envelope
from .behavior.jarvis_decision_room import build_jarvis_decision_room_state
from .behavior.jarvis_decision_fusion import build_jarvis_decision_fusion
from .behavior.jarvis_master_panel import build_jarvis_master_panel
from .behavior.jarvis_replay_determinism import build_jarvis_replay_determinism_report
from .behavior.jarvis_production_blockers import build_jarvis_production_blocker_report
from .behavior.jarvis_blocker_resolution import build_jarvis_blocker_resolution_pack
from .behavior.jarvis_preflight_evidence import build_jarvis_preflight_evidence_pack
from .behavior.openalgo_adapter_harness import build_openalgo_adapter_harness_status
from .behavior.gemini_provider import (
    build_external_ai_review_intake,
    build_external_ai_review_sample,
    build_gemini_outbound_review_bundle,
    build_gemini_live_review_report,
    build_gemini_provider_status,
    build_gemini_review_stub,
    build_sample_gemini_review_for_display,
)
from .behavior.external_ai_reliability import build_external_ai_reliability_report
from .behavior.jarvis_external_ai_audit_integrity import build_external_ai_audit_integrity_report
from .behavior.jarvis_decision_evidence_export import build_jarvis_decision_evidence_export
from .behavior.jarvis_daily_verified_authority import build_daily_verified_authority_report
from .behavior.jarvis_indicator_combination_memory import build_indicator_combination_memory_report
from .behavior.jarvis_candle_cause_effect_memory import build_candle_cause_effect_memory_report
from .behavior.jarvis_gemini_fallback_readiness import build_gemini_fallback_readiness_report
from .behavior.jarvis_gemini_live_review_harness import build_gemini_live_review_harness
from .behavior.jarvis_gemini_decision_room import build_gemini_decision_room_report
from .behavior.grok_provider import (
    build_grok_decision_room_report,
    build_grok_live_review_report,
    build_grok_outbound_review_bundle,
    build_grok_provider_status,
)
from .behavior.grok_gateway_provider import (
    build_grok_gateway_review_report,
    build_grok_gateway_status,
)
from .behavior.jarvis_ai_comparison_room import build_jarvis_ai_comparison_room
from .behavior.jarvis_ai_comparison_history import build_jarvis_ai_comparison_history_report
from .behavior.jarvis_ai_review_refresh_guard import build_jarvis_ai_review_refresh_guard
from .behavior.jarvis_ai_refresh_action_harness import build_jarvis_ai_refresh_action_harness, _hash_packet as _hash_refresh_packet
from .behavior.jarvis_ai_refresh_response_intake import build_jarvis_ai_refresh_response_intake
from .behavior.jarvis_ai_refresh_response_ledger import build_jarvis_ai_refresh_response_ledger
from .behavior.jarvis_ai_response_evidence_diff import build_jarvis_ai_response_evidence_diff
from .behavior.jarvis_provider_disagreement_explorer import build_jarvis_provider_disagreement_explorer
from .behavior.jarvis_verified_review_packet import build_jarvis_verified_review_packet
from .behavior.jarvis_openalgo_safe_intent_binding import build_openalgo_safe_intent_binding
from .behavior.jarvis_paper_ready_safety_audit import build_jarvis_paper_ready_safety_audit
from .behavior.ai_credentials_vault import (
    build_ai_credential_status,
    clear_gemini_credential,
    clear_grok_credential,
    save_gemini_credential,
    save_grok_credential,
    test_ai_credential,
)
from .behavior.jarvis_final_production_audit import build_jarvis_final_production_audit
from .behavior.jarvis_openalgo_handoff_gate import build_openalgo_handoff_gate_report
from .behavior.jarvis_openalgo_paper_bridge import build_openalgo_paper_bridge_report
from .behavior.jarvis_paper_execution_loop import build_paper_execution_loop_report
from .behavior.jarvis_readiness_remediation import build_readiness_remediation_report
from .behavior.jarvis_decision_quality_gate import build_decision_quality_gate_report
from .behavior.jarvis_trading_decision_output import build_trading_decision_output_report
from .behavior.jarvis_chart_overlay_qa import build_chart_overlay_qa_report
from .behavior.jarvis_evidence_assembly import build_jarvis_evidence_bundle
from .behavior.jarvis_evidence_cache import (
    build_evidence_cache_key,
    build_evidence_cache_report,
    get_or_build_cached_evidence_bundle,
)
from .behavior.jarvis_latency_budget import build_jarvis_latency_budget_report
from .behavior.jarvis_realtime_freshness import build_realtime_freshness_report
from .behavior.jarvis_verified_evidence import build_jarvis_verified_evidence_certificate
from .behavior.jarvis_review_preflight import build_jarvis_review_preflight_verdict
from .behavior.jarvis_correction_packet import build_jarvis_correction_review_packet
from .behavior.jarvis_correction_response import build_sample_correction_response, validate_correction_response
from .behavior.jarvis_usefulness import build_jarvis_usefulness_record, build_jarvis_usefulness_summary
from .behavior.openalgo_report_importer import import_openalgo_report, summarize_openalgo_report
from .behavior.trendforge_bridge import pull_and_validate_latest
from .behavior.paper_reality_check import build_paper_reality_check
from .behavior.chart_replay import build_chart_replay_report
from .behavior.indicator_expansion import build_indicator_expansion_report
from .behavior.kronos_proxy import (
    build_kronos_backtest_result,
    build_kronos_forecast_with_optional_service,
    build_kronos_metrics,
    build_kronos_service_bridge_status,
    build_kronos_status,
    build_mock_kronos_forecast,
    kronos_models,
    validate_kronos_input,
)
from .behavior.shared_snapshot import build_kronos_shared_snapshot_forecast
from .behavior.orb_guidance import (
    list_guidance_tickets,
    run_paper_guidance_with_orb,
)
from .behavior.simulated_paper_ledger import (
    list_simulated_paper_trades,
    record_simulated_paper_trade,
)
from .behavior.atomic_json_store import AtomicJsonStoreError
from .behavior.orb_paper_lifecycle import (
    evaluate_simulated_paper_lifecycle,
    list_simulated_paper_outcomes,
)
from .behavior.orb_paper_feedback import (
    build_orb_paper_reliability,
    build_paper_guidance_storage_monitor,
)
from .orb import (
    build_orb_candidate,
    get_orb_discovery_job,
    run_orb_discovery_job,
    list_orb_playbooks,
    promote_orb_playbook,
    run_orb_proof,
    submit_orb_discovery,
    export_csv_bytes as orb_timing_export_csv_bytes,
    get_timing_research_job,
    run_timing_research_job,
    submit_timing_research,
)
from fastapi.responses import Response as CsvResponse
from .behavior.full_twin_analysis import build_full_twin_analysis
from .behavior.walk_forward_validation import build_walk_forward_validation_report
from .behavior.stock_memory_profile import build_stock_memory_profile_report
from .behavior.openalgo_transport import (
    deliver_transport,
    enqueue_transport,
    operator_cancel,
    operator_retry,
    run_due_worker,
    transport_status,
)
from .behavior.transport_resilience import (
    acknowledge_incident,
    build_resilience_report,
    record_health_sample,
    run_fault_harness,
)
from .behavior.transport_security import (
    build_security_posture,
    build_threat_report,
    verify_trace_integrity,
)
from .behavior.deployment_recovery import (
    create_database_backup,
    deployment_readiness,
    deployment_smoke,
    restore_drill,
)
from .behavior.final_release_audit import (
    build_final_release_audit,
    build_release_manifest,
    export_release_candidate,
    scan_for_unsafe_live_paths,
)
from .behavior.release_readiness_evidence import build_release_readiness_evidence_report
from .behavior.twin_arbiter import build_twin_engine_comparison
from .behavior.twin_arbiter import (
    build_signal_intent_preview,
    build_twin_conflicts,
    build_twin_machine_dashboard,
    build_twin_reliability,
    build_twin_tournament,
    verify_bot_handoff_intent,
)
from .behavior.replay_indicator_validation import build_replay_indicator_validation_report
from .behavior.replay_indicator_matrix import build_replay_indicator_matrix_report
from .behavior.matrix_decision_readiness import build_matrix_decision_readiness_report
from .behavior.trade_lifecycle_simulation import (
    build_lifecycle_evidence_drilldown_report,
    build_tradeability_guidance_report,
    build_trade_lifecycle_scenario_comparison_report,
    build_trade_lifecycle_simulation_report,
)
from .behavior.causal_whitelist import causal_whitelist, default_safe_features, validate_causal_features
from .behavior.candle_anatomy import analyze_candles
from .behavior.chart_reasoning_volatility import build_chart_reasoning_report
from .behavior.condition_classifier import classify_conditions
from .behavior.context_engines import (
    analyze_behavior_context,
    analyze_gap_context,
    analyze_htf_confirmation,
    analyze_level_context,
    analyze_market_context,
)
from .behavior.market_regime_feedback import build_market_regime_feedback_report
from .behavior.market_structure_liquidity import build_market_structure_liquidity_report
from .behavior.execution_event_oi_risk import build_execution_event_oi_risk_report
from .behavior.execution_event_oi_risk import build_report_with_derivatives_context
from .behavior.post_entry_lifecycle import build_post_entry_lifecycle_report
from .behavior.final_confluence_arbiter import build_final_confluence_arbiter_report
from .behavior.session_memory import (
    analyze_session_rhythm,
    build_day_of_week_memory,
    build_session_memory_profiles,
    build_stock_dna_summary,
)
from .behavior.constants import (
    BEHAVIOR_CORE_PURPOSE,
    BEHAVIOR_LAYER_CONTRACTS,
    BEHAVIOR_LAYER_NAMES,
    EXPECTED_74_COLUMNS,
    LOW_EVIDENCE_MESSAGE,
    NARRATIVE_EXPLANATION_ONLY_INVARIANT,
    NO_BLIND_PREDICTION_RULE,
    UNIVERSAL_AGREEMENT_RULE,
    VERBATIM_REGISTRY,
    mock_behavior_result,
)
from .behavior.data_adapter import adapt_snapshot, adapter_manifest, build_import_snapshot, import_ohlcv_csv
from .behavior.data_quality import scan_data_quality
from .behavior.point_in_time_guard import run_point_in_time_guard
from .behavior.timeframe_sync import synchronize_timeframes
from .order_guard import order_path_status, simulate_order_request
from .observability import configure_logging, record_request
from .responses import api_error, envelope, error_envelope
from .security import authorize, identity_from_request
from . import storage
from .state import (
    AUDIT_EVENTS,
    CAPABILITIES,
    KILL_SWITCH,
    KNOWLEDGE_GRAPH_PATH,
    SYSTEM_MODE,
    TIME_STATE,
    audit,
    deterministic_events,
    deterministic_ohlcv_snapshot,
)


configure_logging()


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RELEASE_ARTIFACT_DIR = PROJECT_ROOT / "data" / "release_evidence_artifacts"
EXECUTOR_DRY_RUN_DIR = PROJECT_ROOT / "data" / "executor_dry_runs"
EXECUTOR_GOLDEN_FIXTURE_DIR = PROJECT_ROOT / "data" / "executor_golden_fixtures"


def _runtime_artifact_dir(default_dir: Path, env_name: str) -> Path:
    configured = os.environ.get(env_name)
    if configured:
        return Path(configured)
    if str(storage.DB_PATH) == ":memory:":
        return Path(tempfile.gettempdir()) / "tradevision-app-artifacts" / default_dir.name
    return default_dir
EXECUTOR_GOLDEN_CREATED_AT = "2026-01-05T03:45:00+00:00"
EXECUTOR_GOLDEN_VALID_UNTIL = "2099-01-01T00:00:00+00:00"
EXECUTOR_GOLDEN_EXPIRED_AT = "2000-01-01T00:00:00+00:00"


app = FastAPI(
    title="Trade Vision API",
    version="0.1.0",
    description="Safe mock-first production spine for Trade Vision.",
)

# OFF by default. In SHADOW this only exposes research analysis endpoints;
# it cannot place/route orders and loads OpenAlgo credentials only when enabled.
from .orb.derivatives.integration import mount as mount_orb_derivatives
mount_orb_derivatives(app, PROJECT_ROOT)


@app.post("/api/v1/integrations/trendforge/pull-latest")
async def trendforge_pull_latest(max_age_seconds: int = 120):
    try:
        record = pull_and_validate_latest(max_age_seconds=max_age_seconds)
    except ValueError as exc:
        raise api_error(422, "trendforge_intake_rejected", str(exc)) from exc
    saved = storage.save_trendforge_intake(record)
    audit(
        "info",
        f"TrendForge packet {saved['packetId']} stored as {saved['intakeState']}",
        "trendforge_bridge",
    )
    return envelope(saved, capability_status=CapabilityStatus.BETA)


@app.get("/api/v1/integrations/trendforge/intakes")
async def trendforge_intakes(limit: int = 25):
    return envelope(
        storage.list_trendforge_intakes(limit=limit),
        capability_status=CapabilityStatus.BETA,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    return await record_request(request, call_next)


VALID_WORKSPACES = {"cockpit", "marketdna", "behavior", "research", "replay", "knowledge", "implementation", "system"}


def default_layout(workspace_id: str) -> WorkspaceLayout:
    if workspace_id not in VALID_WORKSPACES:
        raise api_error(404, "workspace_not_found", f"Workspace not found: {workspace_id}")
    panel_names = {
        "cockpit": ["command_board", "risk", "order_guard", "portfolio", "integrity", "narrative"],
        "marketdna": ["dna", "probability", "microstructure", "integrity"],
        "behavior": ["behavior_analyze", "output_columns", "layer_contracts", "safety_gates", "stock_app_migration", "verbatim_registry"],
        "research": ["workbench", "data_quality", "integrity"],
        "replay": ["replay_controls", "execution_sim", "archive", "pit_snapshots", "feature_registry"],
        "knowledge": ["knowledge_graph", "graph_source"],
        "implementation": ["capability_manifest"],
        "system": ["pipeline", "storage", "audit"],
    }[workspace_id]
    panels = [
        PanelConfig(
            id=name,
            panel_type=name,
            module=workspace_id,
            bounds=PanelBounds(x=(idx % 3) * 4, y=idx // 3, w=8 if idx == 0 else 4, h=3),
            state={},
            capability_requirement="CapabilityManifest",
        )
        for idx, name in enumerate(panel_names)
    ]
    return WorkspaceLayout(
        version=1,
        workspace_id=workspace_id,
        active_workspace=workspace_id,
        panels=panels,
        global_settings={"modeWatermarkVisible": True, "killSwitchVisible": True, "density": "standard"},
        updated_at=now_iso(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=error_envelope("contract_validation_failed", "Request failed schema validation."),
    )


@app.exception_handler(404)
async def not_found_handler(_: Request, exc):
    if isinstance(exc, HTTPException) and isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        return JSONResponse(status_code=404, content={"error": exc.detail})
    return JSONResponse(
        status_code=404,
        content=error_envelope("not_found", "Endpoint not found."),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        content = {"error": exc.detail}
    else:
        content = error_envelope("http_error", str(exc.detail), retryable=exc.status_code >= 500)
    return JSONResponse(status_code=exc.status_code, content=content)


@app.get("/health", response_model=HealthState)
async def health():
    return HealthState(status="alive")


@app.get("/ready", response_model=ReadyState)
async def ready():
    not_ready = [c.name for c in CAPABILITIES if c.required_for_startup and c.status == CapabilityStatus.RESERVED]
    return ReadyState(
        status="ready" if not not_ready else "not_ready",
        not_ready=not_ready,
        required_capabilities=sum(1 for c in CAPABILITIES if c.required_for_startup),
        total_capabilities=len(CAPABILITIES),
    )


@app.get("/api/time")
async def get_time():
    TIME_STATE.wall_clock_time = now_iso()
    TIME_STATE.sequence_number += 1
    return envelope(TIME_STATE)


@app.get("/api/auth/me")
async def get_auth_identity(request: Request):
    return envelope(identity_from_request(request))


@app.get("/api/system/mode")
async def get_mode():
    return envelope(SYSTEM_MODE)


@app.get("/api/system/features")
async def get_features():
    return envelope(CapabilityManifest(capabilities=CAPABILITIES))


@app.get("/api/storage/status")
async def get_storage_status():
    return envelope(storage.storage_status())


@app.get("/api/observability/status")
async def get_observability_status():
    return envelope(storage.observability_status())


@app.get("/api/observability/requests")
async def get_observability_requests():
    return envelope(storage.list_request_logs())


@app.get("/api/layout/{workspace_id}")
async def get_layout(workspace_id: str):
    layout = storage.load_workspace_layout(workspace_id)
    if layout is None:
        layout = storage.save_workspace_layout(default_layout(workspace_id))
    return envelope(layout)


@app.put("/api/layout/{workspace_id}")
async def put_layout(workspace_id: str, payload: WorkspaceLayout):
    if workspace_id not in VALID_WORKSPACES:
        raise api_error(404, "workspace_not_found", f"Workspace not found: {workspace_id}")
    if payload.workspace_id != workspace_id:
        raise api_error(409, "workspace_layout_mismatch", "Layout workspace_id must match the URL workspace_id.")
    if payload.version != 1:
        raise api_error(409, "workspace_layout_version_unsupported", "Only workspace layout version 1 is supported.")
    return envelope(storage.save_workspace_layout(payload))


@app.get("/api/system/killswitch")
async def get_killswitch():
    return envelope(KILL_SWITCH)


@app.post("/api/system/killswitch/trigger")
async def trigger_killswitch(payload: KillSwitchTriggerRequest, request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["operator", "risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    KILL_SWITCH.state = "triggered"
    KILL_SWITCH.reason = payload.reason
    KILL_SWITCH.source = payload.source
    KILL_SWITCH.actor_id = payload.actor_id
    KILL_SWITCH.triggered_at = now_iso()
    KILL_SWITCH.blocks_order_paths = True
    storage.save_kill_switch(KILL_SWITCH)
    audit("critical", f"Kill switch triggered by {payload.actor_id}: {payload.reason}", "killswitch")
    return envelope(KILL_SWITCH)


@app.post("/api/system/killswitch/reset")
async def reset_killswitch(payload: KillSwitchResetRequest, request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    if SYSTEM_MODE.mode != SystemModeValue.MOCK:
        raise api_error(403, "invalid_mode_transition", "Kill switch reset is restricted outside MOCK mode.")
    KILL_SWITCH.state = "armed"
    KILL_SWITCH.reason = None
    KILL_SWITCH.source = None
    KILL_SWITCH.actor_id = payload.actor_id
    KILL_SWITCH.triggered_at = None
    KILL_SWITCH.blocks_order_paths = False
    storage.save_kill_switch(KILL_SWITCH)
    audit("warning", f"Mock kill switch reset by {payload.actor_id}.", "killswitch")
    return envelope(KILL_SWITCH)


@app.get("/api/system/pipeline")
async def get_pipeline():
    steps = [
        PipelineStep(name="TimeProvider", status=CapabilityStatus.MOCK, latency_ms=0.4, message="Virtual mock clock active."),
        PipelineStep(name="SystemMode", status=CapabilityStatus.MOCK, latency_ms=0.2, message="MOCK mode blocks live orders."),
        PipelineStep(name="KillSwitch", status=CapabilityStatus.MOCK, latency_ms=0.3, message=KILL_SWITCH.state),
        PipelineStep(name="Replay", status=CapabilityStatus.MOCK, latency_ms=1.8, message="Seeded deterministic scenario available."),
        PipelineStep(name="KnowledgeGraph", status=CapabilityStatus.MOCK, latency_ms=2.5, message="Reads project_graph.json."),
        PipelineStep(name="PointInTimeStore", status=CapabilityStatus.MOCK, latency_ms=1.2, message="SQLite immutable snapshots ready."),
        PipelineStep(name="OrderPathGuard", status=CapabilityStatus.MOCK, latency_ms=0.3, message="Simulation-only order path checks kill switch."),
        PipelineStep(name="Observability", status=CapabilityStatus.MOCK, latency_ms=0.4, message="Structured request logging and request/run/decision IDs active."),
        PipelineStep(name="BehaviorContractLock", status=CapabilityStatus.MOCK, latency_ms=0.7, message="32 contracts and 74 output columns locked."),
        PipelineStep(name="BehaviorDataAdapter", status=CapabilityStatus.MOCK, latency_ms=0.9, message="Adapts PIT OHLCV snapshots into CandleSeries; no legacy runtime import."),
        PipelineStep(name="BehaviorRealOhlcvImport", status=CapabilityStatus.MOCK, latency_ms=1.1, message="Imports user-supplied OHLCV CSV into research-only CandleSeries with quality and PIT guards."),
        PipelineStep(name="BehaviorDataQuality", status=CapabilityStatus.MOCK, latency_ms=0.8, message="Blocks impossible OHLC, duplicates, non-monotonic candles, and split suspects."),
        PipelineStep(name="BehaviorPointInTimeGuard", status=CapabilityStatus.MOCK, latency_ms=0.5, message="Blocks future and incomplete candles before behavior analysis."),
        PipelineStep(name="BehaviorTimeframeSync", status=CapabilityStatus.MOCK, latency_ms=0.6, message="Aligns multi-timeframe candles using closed-candle cutoffs."),
        PipelineStep(name="BehaviorCausalWhitelist", status=CapabilityStatus.MOCK, latency_ms=0.4, message="Rejects future/full-day/incomplete-HTF feature dependencies."),
        PipelineStep(name="CandleAnatomy", status=CapabilityStatus.MOCK, latency_ms=0.9, message="Computes body, wick, CLV, ATR range, volume effort, gaps, and structure tags."),
        PipelineStep(name="ConditionClassifier", status=CapabilityStatus.MOCK, latency_ms=0.8, message="Classifies breakout, fakeout, range, absorption, accumulation, distribution, chop, and abnormal structure."),
        PipelineStep(name="BehaviorContextEngines", status=CapabilityStatus.MOCK, latency_ms=1.1, message="Evaluates VWAP/ORB/CPR/PDH/PDL/VPD, HTF, gap, index, sector, and relative strength context."),
        PipelineStep(name="BehaviorSessionMemory", status=CapabilityStatus.MOCK, latency_ms=1.0, message="Scores session rhythm, day-of-week behavior, and Stock DNA memory with minimum evidence guards."),
        PipelineStep(name="BehaviorPatternMemory", status=CapabilityStatus.MOCK, latency_ms=1.2, message="Builds 13-field day-shape vectors, ranks similar historical days, and prepares deterministic similar-day replay."),
        PipelineStep(name="BehaviorOutcomeLearning", status=CapabilityStatus.MOCK, latency_ms=1.0, message="Labels replay outcomes, records failure patterns, and calibrates learning trust with minimum evidence guards."),
        PipelineStep(name="BehaviorDecisionEngine", status=CapabilityStatus.MOCK, latency_ms=0.9, message="Applies universal agreement, no-trade intelligence, and read-only reason tree."),
        PipelineStep(name="BehaviorRiskSizing", status=CapabilityStatus.MOCK, latency_ms=0.8, message="Applies position sizing, daily loss, cooldown, and portfolio exposure caps in simulation-only mode."),
        PipelineStep(name="BehaviorExecutionSimulator", status=CapabilityStatus.MOCK, latency_ms=1.0, message="Models no-fill, spread, slippage, latency, queue, impact, partial fill, and adverse selection without live routing."),
        PipelineStep(name="BehaviorFrontendPanelMap", status=CapabilityStatus.MOCK, latency_ms=0.4, message="Maps Behavior workspace panels to contracts, endpoints, fallbacks, and capability statuses."),
        PipelineStep(name="BehaviorValidation", status=CapabilityStatus.MOCK, latency_ms=1.4, message="Runs deterministic walk-forward and out-of-sample validation with leakage and promotion gates."),
        PipelineStep(name="BehaviorSafetyHardening", status=CapabilityStatus.MOCK, latency_ms=0.7, message="Checks drift, OOD confidence blocks, reality-gap alerts, and ACP promotion gates."),
        PipelineStep(name="BehaviorOperationalSafety", status=CapabilityStatus.MOCK, latency_ms=0.6, message="Persists safety reports, memory quarantines, rebuild plans, and golden replay fixtures."),
        PipelineStep(name="BehaviorReleaseControl", status=CapabilityStatus.MOCK, latency_ms=0.8, message="Builds benchmark reports and mock-to-replay release checklists with manual approval gates."),
        PipelineStep(name="BehaviorReleaseApprovalWorkflow", status=CapabilityStatus.MOCK, latency_ms=0.5, message="Persists auditable mock-to-replay approval requests; live trading stays blocked."),
        PipelineStep(name="BehaviorReleaseEvidenceExport", status=CapabilityStatus.MOCK, latency_ms=0.6, message="Builds immutable release evidence bundles for mock-to-replay review."),
        PipelineStep(name="BehaviorReleaseArtifactExport", status=CapabilityStatus.MOCK, latency_ms=0.7, message="Writes checksum-verified JSON/manifest artifacts to local evidence storage."),
        PipelineStep(name="BehaviorScenarioCoverage", status=CapabilityStatus.MOCK, latency_ms=0.6, message="Summarizes deterministic golden replay coverage by market-behavior scenario family."),
        PipelineStep(name="BehaviorRuntimeReadiness", status=CapabilityStatus.MOCK, latency_ms=0.5, message="Verifies migrated indicator, chart, research, and replay surfaces are available without legacy runtime dependency."),
        PipelineStep(name="BehaviorReplayIndicatorChartValidation", status=CapabilityStatus.MOCK, latency_ms=0.7, message="Converts deterministic replay events into candles, indicator overlays, and chart points with stable hashes."),
        PipelineStep(name="BehaviorChartReplayWorkbench", status=CapabilityStatus.MOCK, latency_ms=0.7, message="Packages replay chart points into viewport, overlay summaries, and selected-candle evidence for the Research chart surface."),
        PipelineStep(name="BehaviorIndicatorExpansionWorkbench", status=CapabilityStatus.MOCK, latency_ms=0.8, message="Promotes ready replay-matrix indicators while labeling proxy rows and blocking live/order use."),
        PipelineStep(name="BehaviorReplayIndicatorMatrix", status=CapabilityStatus.MOCK, latency_ms=0.9, message="Expands replay candles into a 32-row point-in-time indicator matrix for chart, research, and safety validation."),
        PipelineStep(name="BehaviorMatrixDecisionReadiness", status=CapabilityStatus.MOCK, latency_ms=0.8, message="Converts the replay indicator matrix into explicit WAIT/NO_TRADE/replay-candidate readiness gates without order routing."),
        PipelineStep(name="BehaviorTradeLifecycleSimulation", status=CapabilityStatus.MOCK, latency_ms=1.1, message="Links readiness, simulated fill, MFE/MAE, outcome label, and trade-state path while keeping live routing blocked."),
        PipelineStep(name="BehaviorLifecycleScenarioComparison", status=CapabilityStatus.MOCK, latency_ms=1.6, message="Compares multiple replay lifecycle scenarios to separate blocked setups from shadow candidates without paper/live execution."),
        PipelineStep(name="BehaviorLifecycleEvidenceDrilldown", status=CapabilityStatus.MOCK, latency_ms=1.9, message="Explains each lifecycle scenario with row-level directional drivers, counter-drivers, and safety pressures."),
        PipelineStep(name="BehaviorTradeabilityGuidance", status=CapabilityStatus.MOCK, latency_ms=2.1, message="Translates lifecycle evidence into research-only tradeability status, blockers, and improvement targets."),
        PipelineStep(name="LiveBrokerRouting", status=CapabilityStatus.RESERVED, latency_ms=0, message="Disabled by design."),
    ]
    return envelope(PipelineState(mode=SYSTEM_MODE.mode, steps=steps, fast_path_enabled=True, live_order_routing_enabled=False))


@app.get("/api/decision/current")
async def get_decision():
    decision = CognitionDecision(
        final_action="WAIT",
        confidence=0.72,
        votes=[
            EngineVote(engine="ForecastEngine", vote="LONG", confidence=0.72, reason="Mock trend impulse is constructive."),
            EngineVote(engine="MicrostructureEngine", vote="WAIT", confidence=0.55, reason="Absorption risk near intended entry."),
            EngineVote(engine="PortfolioGovernor", vote="REDUCE", confidence=0.68, reason="Correlation cluster is medium."),
            EngineVote(engine="SafetyLayer", vote="PASS", confidence=0.98, reason="MOCK mode only; no live order path."),
        ],
        narrative=NarrativeExplanation(
            text="Wait for better entry. Forecast is constructive, but mock microstructure shows liquidity trap risk.",
            read_only=True,
            cannot_execute_orders=True,
            cannot_override_risk=True,
        ),
        audit=[
            NarrativeAuditEntry(
                timestamp=now_iso(),
                narrative_id="mock-narrative-001",
                model_version="mock-v0.1",
                confidence_score=0.72,
                explanation_chain=[
                    "Forecast vote was constructive.",
                    "Microstructure vote reduced confidence.",
                    "Portfolio governor prevented overcommitment.",
                    "Final action is WAIT.",
                ],
                human_reviewed=False,
                reviewer_id=None,
            )
        ],
    )
    return envelope(decision)


@app.get("/api/portfolio/state")
async def get_portfolio():
    return envelope(
        PortfolioState(
            gross_exposure_pct=0.0,
            sector_concentration_pct=22.0,
            correlation_cluster_risk="medium",
            drawdown_governor="armed",
            live_positions_enabled=False,
        )
    )


@app.get("/api/risk/state")
async def get_risk():
    return envelope(
        MockRiskReport(
            hypothetical_exposure=125000.0,
            max_drawdown_simulated=3.2,
            var95=1.6,
            concentration_risk={"index_beta": 0.42, "technology": 0.28, "financials": 0.18},
            kill_switch_distance=4.8,
            disclaimer="Mock risk only. No real money, broker route, or live position is connected.",
        )
    )


@app.get("/api/market/dna")
async def get_market_dna():
    return envelope(
        MarketDNAState(
            price_score=0.68,
            volatility_score=0.44,
            options_score=0.52,
            breadth_score=0.61,
            event_score=0.49,
            flow_score=0.55,
            calibrated_breakout_probability=0.58,
            calibrated_failure_probability=0.29,
            status=CapabilityStatus.MOCK,
        )
    )


@app.get("/api/microstructure/state")
async def get_microstructure():
    return envelope(
        MicrostructureState(
            order_book_imbalance=0.18,
            sweep_events=2,
            absorption_events=3,
            spoofing_warnings=1,
            hidden_liquidity_suspicion=0.47,
            imbalance_propagation_score=0.62,
            status=CapabilityStatus.MOCK,
        )
    )


@app.get("/api/replay/session")
async def get_replay_session():
    replay = storage.latest_replay()
    if replay is None:
        replay = ReplaySnapshot(session_id="mock-session-default", scenario_id="mock_opening_drive", seed=42, state="paused", current_timestamp_ns=TIME_STATE.virtual_timestamp_ns, events=deterministic_events(42, "mock_opening_drive", 8))
        storage.archive_replay(replay)
    return envelope(replay)


@app.post("/api/replay/start")
async def start_replay(payload: ReplayStartRequest):
    session_id = f"{payload.scenario_id}-{payload.seed}"
    events = deterministic_events(payload.seed, payload.scenario_id, 16)
    audit("info", f"Replay started: {session_id}", "replay")
    snapshot = ReplaySnapshot(session_id=session_id, scenario_id=payload.scenario_id, seed=payload.seed, state="playing", current_timestamp_ns=events[0].virtual_timestamp_ns, events=events)
    storage.archive_replay(snapshot)
    return envelope(snapshot)


@app.post("/api/replay/seek")
async def seek_replay(payload: ReplaySeekRequest):
    existing = storage.load_replay(payload.session_id)
    if existing is None:
        raise api_error(404, "replay_session_not_found", f"Replay session not found: {payload.session_id}")
    snapshot = ReplaySnapshot(
        session_id=existing.session_id,
        scenario_id=existing.scenario_id,
        seed=existing.seed,
        state="stepped",
        current_timestamp_ns=payload.virtual_timestamp_ns,
        events=existing.events,
    )
    storage.archive_replay(snapshot)
    return envelope(snapshot)


@app.post("/api/replay/play")
async def play_replay(payload: ReplayControlRequest):
    existing = storage.load_replay(payload.session_id)
    if existing is None:
        raise api_error(404, "replay_session_not_found", f"Replay session not found: {payload.session_id}")
    snapshot = ReplaySnapshot(
        session_id=existing.session_id,
        scenario_id=existing.scenario_id,
        seed=existing.seed,
        state="playing",
        current_timestamp_ns=existing.current_timestamp_ns,
        events=existing.events,
    )
    storage.archive_replay(snapshot)
    audit("info", f"Replay playing: {payload.session_id}", "replay")
    return envelope(snapshot)


@app.post("/api/replay/pause")
async def pause_replay(payload: ReplayControlRequest):
    existing = storage.load_replay(payload.session_id)
    if existing is None:
        raise api_error(404, "replay_session_not_found", f"Replay session not found: {payload.session_id}")
    snapshot = ReplaySnapshot(
        session_id=existing.session_id,
        scenario_id=existing.scenario_id,
        seed=existing.seed,
        state="paused",
        current_timestamp_ns=existing.current_timestamp_ns,
        events=existing.events,
    )
    storage.archive_replay(snapshot)
    audit("info", f"Replay paused: {payload.session_id}", "replay")
    return envelope(snapshot)


@app.post("/api/replay/step")
async def step_replay(payload: ReplayStepRequest):
    existing = storage.load_replay(payload.session_id)
    if existing is None:
        raise api_error(404, "replay_session_not_found", f"Replay session not found: {payload.session_id}")
    event_times = [event.virtual_timestamp_ns for event in existing.events]
    current_index = 0
    for idx, event_time in enumerate(event_times):
        if event_time <= existing.current_timestamp_ns:
            current_index = idx
    next_index = min(len(event_times) - 1, current_index + payload.steps)
    snapshot = ReplaySnapshot(
        session_id=existing.session_id,
        scenario_id=existing.scenario_id,
        seed=existing.seed,
        state="stepped",
        current_timestamp_ns=event_times[next_index],
        events=existing.events,
    )
    storage.archive_replay(snapshot)
    audit("info", f"Replay stepped: {payload.session_id} +{payload.steps}", "replay")
    return envelope(snapshot)


@app.get("/api/replay/archive")
async def replay_archive():
    return envelope(storage.list_replays())


@app.get("/api/execution/simulation")
async def get_execution_sim():
    return envelope(ExecutionSimState(slippage_pct=0.18, queue_position_estimate=0.41, partial_fill_probability=0.62, adverse_selection_risk="high", simulation_only=True))


@app.get("/api/execution/order-path/status")
async def get_order_path_status():
    return envelope(order_path_status(KILL_SWITCH))


@app.post("/api/execution/order-path/simulate")
async def simulate_order_path(payload: SimulatedOrderRequest, request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["operator", "risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    result = simulate_order_request(payload, SYSTEM_MODE, KILL_SWITCH)
    if not result.accepted:
        audit("warning", f"Order-path simulation rejected: {result.decision} {result.reason}", "order_path")
        status_code = 423 if result.decision == "BLOCKED_BY_KILL_SWITCH" else 409
        raise api_error(status_code, result.decision.lower(), result.reason)
    audit("info", f"Simulated order accepted: {result.simulated_order_id}", "order_path")
    return envelope(result)


@app.get("/api/data/quality")
async def get_data_quality():
    status = storage.storage_status()
    return envelope(DataQualityReport(lookback_years=2.0, survivorship_bias=False, look_ahead_leakage=False, sample_size=max(125000, status.point_in_time_snapshots), notes=["MOCK dataset", "Point-in-time immutable snapshot store active", "No live feed connected"]))


@app.post("/api/data/ingest/mock")
async def ingest_mock_data(payload: MockIngestRequest):
    snapshot, features = deterministic_ohlcv_snapshot(payload.symbol, payload.seed, payload.bars)
    storage.save_point_in_time_snapshot(snapshot)
    for record in features:
        storage.save_feature_version(record)
    audit("info", f"Mock point-in-time snapshot stored for {payload.symbol} seed={payload.seed} bars={payload.bars}", "data_ingest")
    return envelope({"snapshot": snapshot.model_dump(mode="json"), "feature_versions": [record.model_dump(mode="json") for record in features]})


@app.get("/api/data/snapshots")
async def list_snapshots():
    return envelope(storage.list_point_in_time_snapshots())


@app.get("/api/data/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    snapshot = storage.load_point_in_time_snapshot(snapshot_id)
    if snapshot is None:
        raise api_error(404, "snapshot_not_found", f"Point-in-time snapshot not found: {snapshot_id}")
    return envelope(snapshot)


@app.get("/api/features/registry")
async def feature_registry():
    return envelope(storage.list_feature_versions())


@app.get("/api/v1/behavior/data/adapter-manifest")
async def behavior_data_adapter_manifest():
    return envelope(adapter_manifest())


@app.post("/api/v1/behavior/data/adapt")
async def behavior_data_adapt(payload: BehaviorDataAdapterRequest):
    if payload.snapshot_id:
        snapshot = storage.load_point_in_time_snapshot(payload.snapshot_id)
        if snapshot is None:
            raise api_error(404, "snapshot_not_found", f"Point-in-time snapshot not found: {payload.snapshot_id}")
    else:
        snapshot, features = deterministic_ohlcv_snapshot(payload.symbol, payload.seed, payload.bars)
        storage.save_point_in_time_snapshot(snapshot)
        for record in features:
            storage.save_feature_version(record)
    result = adapt_snapshot(snapshot, payload.timeframe)
    audit("info", f"Behavior data adapted for {result.series.symbol} from {result.source_snapshot_id}", "behavior_data")
    return envelope(result)


@app.post("/api/v1/behavior/data/import/ohlcv")
async def behavior_import_ohlcv(payload: BehaviorOhlcvImportRequest):
    try:
        result = import_ohlcv_csv(payload)
    except ValueError as exc:
        raise api_error(422, "ohlcv_import_invalid", str(exc), retryable=False) from exc
    if payload.persist_snapshot and result.series.bars:
        storage.save_point_in_time_snapshot(build_import_snapshot(result))
        audit("info", f"User CSV OHLCV snapshot stored for {result.symbol}: {result.persisted_snapshot_id}", "behavior_data_import")
    elif result.safe_for_research:
        audit("info", f"User CSV OHLCV import preview passed for {result.symbol}: bars={result.parsed_bar_count}", "behavior_data_import")
    else:
        audit("warning", f"User CSV OHLCV import blocked for {result.symbol}: score={result.quality.data_quality_score}", "behavior_data_import")
    return envelope(result)


LOCAL_RELIANCE_1M_CSV = Path(r"C:\Users\sakth\Downloads\HSTRY\RELIANCE_NSE_1m.csv")


def _local_reliance_csv_text(rows: int, position: str) -> str:
    bounded_rows = max(1, min(rows, 2000))
    if not LOCAL_RELIANCE_1M_CSV.exists():
        raise api_error(503, "local_reliance_csv_unavailable", f"Local file not found: {LOCAL_RELIANCE_1M_CSV}", retryable=True)
    with LOCAL_RELIANCE_1M_CSV.open("r", encoding="utf-8-sig", errors="replace") as handle:
        header = handle.readline().strip()
        if position == "head":
            data_lines: list[str] = []
            for _ in range(bounded_rows):
                line = handle.readline()
                if not line:
                    break
                data_lines.append(line.strip())
        else:
            tail: deque[str] = deque(maxlen=bounded_rows)
            for line in handle:
                clean = line.strip()
                if clean:
                    tail.append(clean)
            data_lines = list(tail)
    return "\n".join([header, *data_lines])


@app.get("/api/v1/behavior/data/local/reliance-1m/preview")
async def behavior_local_reliance_1m_preview(rows: int = 390, position: str = "tail", persist_snapshot: bool = True):
    if position not in {"head", "tail"}:
        raise api_error(422, "invalid_local_csv_position", "position must be head or tail", retryable=False)
    payload = BehaviorOhlcvImportRequest(
        symbol="RELIANCE",
        timeframe="1m",
        csv_text=_local_reliance_csv_text(rows, position),
        date_column="date",
        time_column="time",
        timezone_offset_minutes=330,
        persist_snapshot=persist_snapshot,
    )
    result = import_ohlcv_csv(payload)
    if persist_snapshot and result.persisted_snapshot_id:
        storage.save_point_in_time_snapshot(build_import_snapshot(result))
    audit("info", f"Local RELIANCE 1m CSV preview imported: rows={result.parsed_bar_count}, position={position}", "behavior_data_import")
    return envelope(result)


@app.get("/api/v1/jarvis/decision-room/state/{symbol}")
async def jarvis_decision_room_state(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    series: CandleSeries
    quality = None
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=True,
        )
        result = import_ohlcv_csv(payload)
        if result.persisted_snapshot_id:
            storage.save_point_in_time_snapshot(build_import_snapshot(result))
        series = result.series
        quality = result.quality
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
        quality = scan_data_quality(series)
    state = build_jarvis_decision_room_state(
        symbol=normalized,
        timeframe=timeframe,
        series=series,
        data_quality=quality,
        system_mode=SYSTEM_MODE.mode,
        kill_switch_active=KILL_SWITCH.state == "triggered",
        kronos_status=build_kronos_status(),
        openalgo_report=storage.load_latest_openalgo_report_import(normalized),
    )
    usefulness_record = storage.save_jarvis_usefulness_record(build_jarvis_usefulness_record(state))
    usefulness_history = storage.list_jarvis_usefulness_records(normalized, limit=30)
    state["usefulness_record"] = usefulness_record
    state["usefulness_summary"] = build_jarvis_usefulness_summary(symbol=normalized, records=usefulness_history)
    audit("info", f"Jarvis decision room state generated for {normalized}: {state['final_action']}", "jarvis_decision_room")
    return envelope(state, capability_status=CapabilityStatus.MOCK)


def _build_jarvis_room_without_persistence(symbol: str, timeframe: str, rows: int, position: str) -> dict[str, Any]:
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=True,
        )
        result = import_ohlcv_csv(payload)
        if result.persisted_snapshot_id:
            storage.save_point_in_time_snapshot(build_import_snapshot(result))
        series = result.series
        quality = result.quality
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
        quality = scan_data_quality(series)
    return build_jarvis_decision_room_state(
        symbol=normalized,
        timeframe=timeframe,
        series=series,
        data_quality=quality,
        system_mode=SYSTEM_MODE.mode,
        kill_switch_active=KILL_SWITCH.state == "triggered",
        kronos_status=build_kronos_status(),
        openalgo_report=storage.load_latest_openalgo_report_import(normalized),
    )


def _jarvis_external_ai_evidence_packet(room: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "trade_vision_decision": room.get("trade_vision_decision", {}),
        "candle_structure": room.get("candle_structure", {}),
        "indicator_snapshot": room.get("indicator_snapshot", {}),
        "multi_timeframe_alignment": room.get("multi_timeframe_alignment", {}),
        "similar_history": room.get("similar_history", {}),
        "safety_summary": room.get("safety_summary", {}),
        "final_action": room.get("final_action"),
    }


@app.get("/api/v1/jarvis/decision-room/fusion/{symbol}")
async def jarvis_decision_room_fusion(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    fusion = build_jarvis_decision_fusion(room, build_gemini_provider_status())
    audit("info", f"Jarvis decision fusion generated for {fusion['symbol']}: {fusion['final_view']}", "jarvis_decision_fusion")
    return envelope(fusion, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/decision-room/master-panel/{symbol}")
async def jarvis_decision_room_master_panel(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    gemini_status = build_gemini_provider_status()
    fusion = build_jarvis_decision_fusion(room, gemini_status)
    panel = build_jarvis_master_panel(room=room, fusion=fusion, gemini_status=gemini_status)
    audit("info", f"Jarvis master panel generated for {panel['symbol']}: {panel['final_action']}", "jarvis_master_panel")
    return envelope(panel, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/decision-room/replay-determinism/{symbol}")
async def jarvis_decision_room_replay_determinism(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    first_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    second_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    report = build_jarvis_replay_determinism_report(first_room, second_room)
    audit("info", f"Jarvis replay determinism checked for {report['symbol']}: {report['deterministic']}", "jarvis_replay_determinism")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/production-blockers/{symbol}")
async def jarvis_production_blockers(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    first_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    second_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    fusion = build_jarvis_decision_fusion(first_room, build_gemini_provider_status())
    replay_report = build_jarvis_replay_determinism_report(first_room, second_room)
    report = build_jarvis_production_blocker_report(
        fusion=fusion,
        replay_determinism=replay_report,
        final_release_audit=build_final_release_audit(),
        deployment_readiness=deployment_readiness(),
        openalgo_transport_status=transport_status(check_health=True),
    )
    audit("info", f"Jarvis production blockers generated for {report['symbol']}: {report['overall_status']}", "jarvis_production_blockers")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/blocker-resolution/{symbol}")
async def jarvis_blocker_resolution(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    first_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    second_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    fusion = build_jarvis_decision_fusion(first_room, build_gemini_provider_status())
    replay_report = build_jarvis_replay_determinism_report(first_room, second_room)
    final_audit = build_final_release_audit()
    deploy = deployment_readiness()
    transport = transport_status(check_health=True)
    blocker_report = build_jarvis_production_blocker_report(
        fusion=fusion,
        replay_determinism=replay_report,
        final_release_audit=final_audit,
        deployment_readiness=deploy,
        openalgo_transport_status=transport,
    )
    pack = build_jarvis_blocker_resolution_pack(
        blocker_report=blocker_report,
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        security_posture=build_security_posture(),
        transport_status=transport,
    )
    audit("info", f"Jarvis blocker resolution pack generated for {pack['symbol']}: {pack['overall_status']}", "jarvis_blocker_resolution")
    return envelope(pack, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/preflight-evidence/{symbol}")
async def jarvis_preflight_evidence(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    first_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    second_room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    fusion = build_jarvis_decision_fusion(first_room, build_gemini_provider_status())
    replay_report = build_jarvis_replay_determinism_report(first_room, second_room)
    final_audit = build_final_release_audit()
    deploy = deployment_readiness()
    transport = transport_status(check_health=True)
    security = build_security_posture()
    blocker_report = build_jarvis_production_blocker_report(
        fusion=fusion,
        replay_determinism=replay_report,
        final_release_audit=final_audit,
        deployment_readiness=deploy,
        openalgo_transport_status=transport,
    )
    resolution = build_jarvis_blocker_resolution_pack(
        blocker_report=blocker_report,
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        security_posture=security,
        transport_status=transport,
    )
    pack = build_jarvis_preflight_evidence_pack(
        blocker_report=blocker_report,
        resolution_pack=resolution,
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        security_posture=security,
        transport_status=transport,
    )
    audit("info", f"Jarvis preflight evidence generated for {pack['symbol']}: {pack['overall_status']}", "jarvis_preflight_evidence")
    return envelope(pack, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/openalgo/adapter-harness/status")
async def openalgo_adapter_harness_status():
    status = build_openalgo_adapter_harness_status(
        project_root=PROJECT_ROOT,
        transport_status=transport_status(check_health=True),
    )
    audit("info", f"OpenAlgo adapter harness status generated: {status['readiness']['dry_run_handoff_ready']}", "openalgo_adapter_harness")
    return envelope(status, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/openalgo/handoff-gate/{symbol}")
async def jarvis_openalgo_handoff_gate(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    package = _export_executor_dry_run_package(ExecutorDryRunPackageRequest(symbol=normalized, target_executor="openalgo"))
    package_verification = _verify_executor_dry_run_package(package)
    transport = transport_status(check_health=True)
    adapter = build_openalgo_adapter_harness_status(
        project_root=PROJECT_ROOT,
        transport_status=transport,
    )
    report = build_openalgo_handoff_gate_report(
        symbol=normalized,
        jarvis_room=room,
        dry_run_package=package,
        package_verification=package_verification,
        transport_status=transport,
        adapter_harness=adapter,
    )
    audit("info", f"OpenAlgo handoff gate generated for {normalized}: {report['handoff_state']}", "jarvis_openalgo_handoff")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/paper-execution-loop/{symbol}")
async def jarvis_paper_execution_loop(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    paper_safety = build_execution_intent_paper_safety_report()
    lifecycle_payload = TradeLifecycleSimulationRequest(symbol=normalized, timeframe=timeframe)
    lifecycle_events = deterministic_events(lifecycle_payload.seed, lifecycle_payload.scenario_id, lifecycle_payload.event_count)
    lifecycle = build_trade_lifecycle_simulation_report(lifecycle_payload, lifecycle_events)
    comparison_payload = TradeLifecycleScenarioComparisonRequest(symbol=normalized, timeframe=timeframe)
    comparison = build_trade_lifecycle_scenario_comparison_report(comparison_payload, deterministic_events)
    evidence_payload = LifecycleEvidenceDrilldownRequest(symbol=normalized, timeframe=timeframe)
    evidence = build_lifecycle_evidence_drilldown_report(evidence_payload, deterministic_events)
    guidance_payload = TradeabilityGuidanceRequest(symbol=normalized, timeframe=timeframe)
    guidance = build_tradeability_guidance_report(guidance_payload, deterministic_events)
    report = build_paper_execution_loop_report(
        symbol=normalized,
        jarvis_room=room,
        paper_safety=paper_safety,
        lifecycle=lifecycle,
        lifecycle_comparison=comparison,
        lifecycle_evidence=evidence,
        tradeability=guidance,
    )
    audit("info", f"Paper execution loop generated for {normalized}: {report['loop_state']}", "jarvis_paper_loop")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


def _build_jarvis_evidence_bundle_for_endpoint(normalized: str, timeframe: str, rows: int, position: str, stale_after_seconds: int) -> dict[str, Any]:
    cache_key = build_evidence_cache_key(
        symbol=normalized,
        timeframe=timeframe,
        rows=rows,
        position=position,
        stale_after_seconds=stale_after_seconds,
    )
    return get_or_build_cached_evidence_bundle(
        cache_key=cache_key,
        builder=lambda: build_jarvis_evidence_bundle(
            symbol=normalized,
            timeframe=timeframe,
            rows=rows,
            position=position,
            stale_after_seconds=stale_after_seconds,
            project_root=PROJECT_ROOT,
            build_room=_build_jarvis_room_without_persistence,
            external_records=storage.list_external_ai_review_records(symbol=normalized, limit=100),
            export_executor_dry_run_package=_export_executor_dry_run_package,
            verify_executor_dry_run_package=_verify_executor_dry_run_package,
            get_transport_status=transport_status,
            get_deterministic_events=deterministic_events,
        ),
    )


@app.get("/api/v1/jarvis/decision-quality-gate/{symbol}")
async def jarvis_decision_quality_gate(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    report = bundle["decision_quality"]
    audit("info", f"Decision quality gate generated for {normalized}: {report['quality_state']}", "jarvis_decision_quality")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/trading-decision-output/{symbol}")
async def jarvis_trading_decision_output(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    report = bundle["trading_decision_output"]
    audit("info", f"Trading decision output generated for {normalized}: {report['output_state']}", "jarvis_trading_output")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/chart-overlay-qa/{symbol}")
async def jarvis_chart_overlay_qa(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    report = bundle["chart_overlay_qa"]
    audit("info", f"Chart overlay QA generated for {normalized}: {report['qa_state']}", "jarvis_chart_overlay_qa")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/evidence-latency-budget/{symbol}")
async def jarvis_evidence_latency_budget(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    report = build_jarvis_latency_budget_report(bundle)
    audit("info", f"Evidence latency budget generated for {normalized}: {report['budget_state']}", "jarvis_latency_budget")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/evidence-cache/{symbol}")
async def jarvis_evidence_cache(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    report = build_evidence_cache_report(bundle)
    audit("info", f"Evidence cache report generated for {normalized}: {report['cache_status']}", "jarvis_evidence_cache")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/realtime-freshness/{symbol}")
async def jarvis_realtime_freshness(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900, max_age_seconds: float = 10.0):
    normalized = _normalize_symbol(symbol)
    bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    latency = build_jarvis_latency_budget_report(bundle)
    report = build_realtime_freshness_report(bundle=bundle, latency_budget=latency, max_age_seconds=max_age_seconds)
    audit("info", f"Realtime freshness generated for {normalized}: {report['freshness_state']}", "jarvis_realtime_freshness")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/gemini/status")
async def jarvis_gemini_status():
    return envelope(build_gemini_provider_status(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/ai/credentials/status")
async def ai_credentials_status():
    return envelope(build_ai_credential_status(), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/ai/credentials/gemini")
async def ai_credentials_save_gemini(payload: dict[str, Any]):
    try:
        slot = int(payload.get("slot", 1))
        api_key = str(payload.get("api_key", ""))
        label = str(payload.get("label", "")) or None
        status = save_gemini_credential(slot=slot, api_key=api_key, label=label)
    except (RuntimeError, ValueError) as exc:
        raise api_error(400, "ai_credential_save_failed", str(exc), retryable=False) from exc
    audit("info", f"Gemini credential slot {slot} saved to local backend vault", "ai_credentials")
    return envelope(status, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/ai/credentials/grok")
async def ai_credentials_save_grok(payload: dict[str, Any]):
    try:
        api_key = str(payload.get("api_key", ""))
        label = str(payload.get("label", "")) or None
        status = save_grok_credential(api_key=api_key, label=label)
    except (RuntimeError, ValueError) as exc:
        raise api_error(400, "ai_credential_save_failed", str(exc), retryable=False) from exc
    audit("info", "Grok credential saved to local backend vault", "ai_credentials")
    return envelope(status, capability_status=CapabilityStatus.MOCK)


@app.delete("/api/v1/ai/credentials/gemini/{slot}")
async def ai_credentials_clear_gemini(slot: int):
    try:
        status = clear_gemini_credential(slot)
    except (RuntimeError, ValueError) as exc:
        raise api_error(400, "ai_credential_clear_failed", str(exc), retryable=False) from exc
    audit("info", f"Gemini credential slot {slot} cleared from local backend vault", "ai_credentials")
    return envelope(status, capability_status=CapabilityStatus.MOCK)


@app.delete("/api/v1/ai/credentials/grok")
async def ai_credentials_clear_grok():
    try:
        status = clear_grok_credential()
    except RuntimeError as exc:
        raise api_error(400, "ai_credential_clear_failed", str(exc), retryable=False) from exc
    audit("info", "Grok credential cleared from local backend vault", "ai_credentials")
    return envelope(status, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/ai/credentials/test-gemini")
async def ai_credentials_test_gemini(payload: dict[str, Any] | None = None):
    try:
        slot = int((payload or {}).get("slot")) if payload and payload.get("slot") is not None else None
        result = test_ai_credential("gemini", slot=slot)
    except ValueError as exc:
        raise api_error(400, "ai_credential_test_failed", str(exc), retryable=False) from exc
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/ai/credentials/test-grok")
async def ai_credentials_test_grok():
    result = test_ai_credential("grok")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/grok/status")
async def jarvis_grok_status():
    return envelope(build_grok_provider_status(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/grok-gateway/status")
async def jarvis_grok_gateway_status(check_health: bool = False):
    return envelope(await build_grok_gateway_status(check_health=check_health), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/grok-gateway/connect")
async def jarvis_grok_gateway_connect():
    status = await build_grok_gateway_status(check_health=True)
    audit("info", f"Grok gateway connect checked: {status['gateway_state']}", "jarvis_grok_gateway")
    return envelope(status, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/grok-gateway/review/{symbol}")
async def jarvis_grok_gateway_review(symbol: str, payload: dict[str, Any] | None = None, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    body = payload or {}
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    evidence_packet = _jarvis_external_ai_evidence_packet(room)
    report = await build_grok_gateway_review_report(symbol=normalized, evidence_packet=evidence_packet, execute=bool(body.get("execute", False)))
    if report.get("review_intake"):
        saved = storage.save_external_ai_review_record({**report["review_intake"], "symbol": normalized, "timeframe": timeframe})
        report["saved_review_id"] = saved["review_id"]
    audit("info", f"Grok gateway review generated for {normalized}: {report['safe_final_action']} / {report['thinking_state']}", "jarvis_grok_gateway")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/grok/live-review/{symbol}")
async def jarvis_grok_live_review(symbol: str, payload: dict[str, Any] | None = None, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    body = payload or {}
    execute = bool(body.get("execute", False))
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    evidence_packet = _jarvis_external_ai_evidence_packet(room)
    report = await build_grok_live_review_report(evidence_packet=evidence_packet, execute=execute)
    saved = storage.save_external_ai_review_record({**report["review_intake"], "symbol": normalized, "timeframe": timeframe})
    report["saved_review_id"] = saved["review_id"]
    audit("info", f"Grok live review report generated for {normalized}: {report['safe_final_action']}", "jarvis_grok_live_review")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/ai-review/compare/{symbol}")
async def jarvis_ai_review_compare(symbol: str, payload: dict[str, Any] | None = None, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    body = payload or {}
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    evidence_packet = _jarvis_external_ai_evidence_packet(room)
    report = await build_jarvis_ai_comparison_room(
        symbol=normalized,
        evidence_packet=evidence_packet,
        execute_gemini=bool(body.get("execute_gemini", False)),
        execute_grok=bool(body.get("execute_grok", False)),
    )
    gemini_saved = storage.save_external_ai_review_record({**report["gemini"].get("review_intake", {}), "symbol": normalized, "timeframe": timeframe})
    grok_saved = storage.save_external_ai_review_record({**report["grok"].get("review_intake", {}), "symbol": normalized, "timeframe": timeframe})
    report["saved_candidate_review_ids"] = {
        "gemini": gemini_saved["review_id"],
        "grok": grok_saved["review_id"],
    }
    comparison_saved = storage.save_jarvis_ai_comparison_record(report)
    report["saved_comparison_id"] = comparison_saved["comparison_id"]
    audit("info", f"Jarvis AI comparison generated for {normalized}: {report['safe_final_action']}", "jarvis_ai_comparison")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/ai-review/comparison-history/{symbol}")
async def jarvis_ai_review_comparison_history(symbol: str, limit: int = 50, stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=limit)
    report = build_jarvis_ai_comparison_history_report(
        symbol=normalized,
        comparison_records=records,
        stale_after_seconds=stale_after_seconds,
    )
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/ai-review/refresh-guard/{symbol}")
async def jarvis_ai_review_refresh_guard(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 50, stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    comparison_records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=limit)
    comparison_history = build_jarvis_ai_comparison_history_report(
        symbol=normalized,
        comparison_records=comparison_records,
        stale_after_seconds=stale_after_seconds,
    )
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    correction_records = storage.list_correction_response_records(symbol=normalized, limit=limit)
    report = build_jarvis_ai_review_refresh_guard(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        comparison_history=comparison_history,
        comparison_records=comparison_records,
        external_review_records=external_records,
        correction_response_records=correction_records,
        stale_after_seconds=stale_after_seconds,
    )
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/ai-review/refresh-action/{symbol}")
async def jarvis_ai_review_refresh_action(symbol: str, payload: dict[str, Any] | None = None, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 50, stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    body = payload or {}
    execute_requested = bool(body.get("execute", False))
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    comparison_records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=limit)
    comparison_history = build_jarvis_ai_comparison_history_report(
        symbol=normalized,
        comparison_records=comparison_records,
        stale_after_seconds=stale_after_seconds,
    )
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    correction_records = storage.list_correction_response_records(symbol=normalized, limit=limit)
    refresh_guard = build_jarvis_ai_review_refresh_guard(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        comparison_history=comparison_history,
        comparison_records=comparison_records,
        external_review_records=external_records,
        correction_response_records=correction_records,
        stale_after_seconds=stale_after_seconds,
    )
    gemini_bundle = build_gemini_outbound_review_bundle(current_evidence_packet, build_gemini_provider_status())
    grok_bundle = build_grok_outbound_review_bundle(current_evidence_packet, build_grok_provider_status())
    report = build_jarvis_ai_refresh_action_harness(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        refresh_guard=refresh_guard,
        gemini_bundle=gemini_bundle,
        grok_bundle=grok_bundle,
        execute_requested=execute_requested,
    )
    audit("warning" if report["refresh_needed"] else "info", f"AI refresh action harness prepared for {normalized}: {report['harness_state']}", "jarvis_ai_refresh")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/ai-review/refresh-response/{symbol}")
async def jarvis_ai_review_refresh_response(symbol: str, payload: dict[str, Any], timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 50, stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    provider = str(payload.get("provider") or "manual")
    candidate_response = payload.get("candidate_response", payload.get("response", {}))
    if not isinstance(candidate_response, dict):
        raise api_error(422, "invalid_refresh_response", "candidate_response must be a JSON object")
    response_packet_hash = payload.get("refresh_packet_hash") or payload.get("packet_hash")
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    comparison_records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=limit)
    comparison_history = build_jarvis_ai_comparison_history_report(symbol=normalized, comparison_records=comparison_records, stale_after_seconds=stale_after_seconds)
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    correction_records = storage.list_correction_response_records(symbol=normalized, limit=limit)
    refresh_guard = build_jarvis_ai_review_refresh_guard(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        comparison_history=comparison_history,
        comparison_records=comparison_records,
        external_review_records=external_records,
        correction_response_records=correction_records,
        stale_after_seconds=stale_after_seconds,
    )
    refresh_action = build_jarvis_ai_refresh_action_harness(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        refresh_guard=refresh_guard,
        gemini_bundle=build_gemini_outbound_review_bundle(current_evidence_packet, build_gemini_provider_status()),
        grok_bundle=build_grok_outbound_review_bundle(current_evidence_packet, build_grok_provider_status()),
        execute_requested=False,
    )
    report = build_jarvis_ai_refresh_response_intake(
        symbol=normalized,
        provider=provider,
        refresh_action=refresh_action,
        candidate_response=candidate_response,
        response_packet_hash=str(response_packet_hash) if response_packet_hash else None,
    )
    saved = storage.save_external_ai_review_record(report["review_record"])
    report["saved_review_id"] = saved["review_id"]
    audit("info" if report["display_allowed"] else "warning", f"AI refresh response intake {provider} for {normalized}: {report['replay_status']}", "jarvis_ai_refresh")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/ai-review/refresh-ledger/{symbol}")
async def jarvis_ai_review_refresh_ledger(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 100, stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    current_evidence_hash = _hash_refresh_packet(current_evidence_packet)
    records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    report = build_jarvis_ai_refresh_response_ledger(
        symbol=normalized,
        records=records,
        current_evidence_packet_hash=current_evidence_hash,
        stale_after_seconds=stale_after_seconds,
    )
    audit("info" if report["blocking_count"] == 0 else "warning", f"AI refresh response ledger for {normalized}: {report['ledger_state']}", "jarvis_ai_refresh")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/ai-review/evidence-diff/{symbol}")
async def jarvis_ai_review_evidence_diff(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 100):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    current_evidence_hash = _hash_refresh_packet(current_evidence_packet)
    records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    report = build_jarvis_ai_response_evidence_diff(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        records=records,
        current_evidence_packet_hash=current_evidence_hash,
    )
    audit("info" if report["blocking_count"] == 0 else "warning", f"AI response evidence diff for {normalized}: {report['diff_state']}", "jarvis_ai_diff")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/ai-review/disagreement-explorer/{symbol}")
async def jarvis_ai_review_disagreement_explorer(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 100):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    current_evidence_hash = _hash_refresh_packet(current_evidence_packet)
    comparison_records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=1)
    latest_comparison = comparison_records[0] if comparison_records else {}
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    evidence_diff = build_jarvis_ai_response_evidence_diff(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        records=external_records,
        current_evidence_packet_hash=current_evidence_hash,
    )
    openalgo_summary = summarize_openalgo_report(storage.load_latest_openalgo_report_import(normalized))
    report = build_jarvis_provider_disagreement_explorer(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        ai_comparison=latest_comparison,
        evidence_diff=evidence_diff,
        kronos_report=build_kronos_status().model_dump(),
        openalgo_summary=openalgo_summary,
    )
    audit("info" if report["blocking_count"] == 0 else "warning", f"Provider disagreement explorer for {normalized}: {report['explorer_state']}", "jarvis_ai_disagreement")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/ai-review/verified-packet/{symbol}")
async def jarvis_ai_review_verified_packet(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 100, stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    comparison_records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=limit)
    comparison_history = build_jarvis_ai_comparison_history_report(
        symbol=normalized,
        comparison_records=comparison_records,
        stale_after_seconds=stale_after_seconds,
    )
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    correction_records = storage.list_correction_response_records(symbol=normalized, limit=limit)
    refresh_guard = build_jarvis_ai_review_refresh_guard(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        comparison_history=comparison_history,
        comparison_records=comparison_records,
        external_review_records=external_records,
        correction_response_records=correction_records,
        stale_after_seconds=stale_after_seconds,
    )
    gemini_status = build_gemini_provider_status()
    grok_status = build_grok_provider_status()
    refresh_action = build_jarvis_ai_refresh_action_harness(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        refresh_guard=refresh_guard,
        gemini_bundle=build_gemini_outbound_review_bundle(current_evidence_packet, gemini_status),
        grok_bundle=build_grok_outbound_review_bundle(current_evidence_packet, grok_status),
        execute_requested=False,
    )
    report = build_jarvis_verified_review_packet(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        gemini_status=gemini_status,
        grok_status=grok_status,
        gemini_bundle=build_gemini_outbound_review_bundle(current_evidence_packet, gemini_status),
        grok_bundle=build_grok_outbound_review_bundle(current_evidence_packet, grok_status),
        review_records=external_records,
        refresh_action=refresh_action,
    )
    audit("info" if report["blocking_count"] == 0 else "warning", f"Verified AI review packet for {normalized}: {report['packet_state']}", "jarvis_ai_packet")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/openalgo/safe-intent-binding/{symbol}")
async def jarvis_openalgo_safe_intent_binding(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 100, stale_after_seconds: int = 900, max_age_seconds: float = 10.0):
    normalized = _normalize_symbol(symbol)
    evidence_bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    room = evidence_bundle["room"]
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    comparison_records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=limit)
    comparison_history = build_jarvis_ai_comparison_history_report(
        symbol=normalized,
        comparison_records=comparison_records,
        stale_after_seconds=stale_after_seconds,
    )
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    correction_records = storage.list_correction_response_records(symbol=normalized, limit=limit)
    refresh_guard = build_jarvis_ai_review_refresh_guard(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        comparison_history=comparison_history,
        comparison_records=comparison_records,
        external_review_records=external_records,
        correction_response_records=correction_records,
        stale_after_seconds=stale_after_seconds,
    )
    gemini_status = build_gemini_provider_status()
    grok_status = build_grok_provider_status()
    gemini_bundle = build_gemini_outbound_review_bundle(current_evidence_packet, gemini_status)
    grok_bundle = build_grok_outbound_review_bundle(current_evidence_packet, grok_status)
    refresh_action = build_jarvis_ai_refresh_action_harness(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        refresh_guard=refresh_guard,
        gemini_bundle=gemini_bundle,
        grok_bundle=grok_bundle,
        execute_requested=False,
    )
    verified_packet = build_jarvis_verified_review_packet(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        gemini_status=gemini_status,
        grok_status=grok_status,
        gemini_bundle=gemini_bundle,
        grok_bundle=grok_bundle,
        review_records=external_records,
        refresh_action=refresh_action,
    )
    current_evidence_hash = _hash_refresh_packet(current_evidence_packet)
    evidence_diff = build_jarvis_ai_response_evidence_diff(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        records=external_records,
        current_evidence_packet_hash=current_evidence_hash,
    )
    disagreement = build_jarvis_provider_disagreement_explorer(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        ai_comparison=comparison_records[0] if comparison_records else {},
        evidence_diff=evidence_diff,
        kronos_report=build_kronos_status().model_dump(),
        openalgo_summary=summarize_openalgo_report(storage.load_latest_openalgo_report_import(normalized)),
    )
    latency = build_jarvis_latency_budget_report(evidence_bundle)
    freshness = build_realtime_freshness_report(bundle=evidence_bundle, latency_budget=latency, max_age_seconds=max_age_seconds)
    provider_status = build_gemini_provider_status()
    outbound_bundle = build_gemini_outbound_review_bundle(current_evidence_packet, provider_status)
    sample_review = build_sample_gemini_review_for_display(current_evidence_packet)
    gemini_room = build_gemini_decision_room_report(
        symbol=normalized,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        sample_review=sample_review,
        realtime_freshness=freshness,
        decision_quality=evidence_bundle["decision_quality"],
        trading_decision_output=evidence_bundle["trading_decision_output"],
    )
    paper_bridge = build_openalgo_paper_bridge_report(
        symbol=normalized,
        handoff_gate=evidence_bundle["openalgo_handoff"],
        decision_quality=evidence_bundle["decision_quality"],
        realtime_freshness=freshness,
        gemini_decision_room=gemini_room,
    )
    report = build_openalgo_safe_intent_binding(
        symbol=normalized,
        jarvis_room=room,
        verified_review_packet=verified_packet,
        disagreement_explorer=disagreement,
        openalgo_handoff_gate=evidence_bundle["openalgo_handoff"],
        openalgo_paper_bridge=paper_bridge,
    )
    audit("info" if report["blocking_count"] == 0 else "warning", f"OpenAlgo-safe intent binding for {normalized}: {report['preview_state']}", "jarvis_openalgo_binding")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/paper-ready-safety-audit/{symbol}")
async def jarvis_paper_ready_safety_audit(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", limit: int = 100, stale_after_seconds: int = 900, max_age_seconds: float = 10.0):
    normalized = _normalize_symbol(symbol)
    evidence_bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    room = evidence_bundle["room"]
    current_evidence_packet = _jarvis_external_ai_evidence_packet(room)
    comparison_records = storage.list_jarvis_ai_comparison_records(symbol=normalized, limit=limit)
    comparison_history = build_jarvis_ai_comparison_history_report(
        symbol=normalized,
        comparison_records=comparison_records,
        stale_after_seconds=stale_after_seconds,
    )
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=limit)
    correction_records = storage.list_correction_response_records(symbol=normalized, limit=limit)
    refresh_guard = build_jarvis_ai_review_refresh_guard(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        comparison_history=comparison_history,
        comparison_records=comparison_records,
        external_review_records=external_records,
        correction_response_records=correction_records,
        stale_after_seconds=stale_after_seconds,
    )
    gemini_status = build_gemini_provider_status()
    grok_status = build_grok_provider_status()
    gemini_bundle = build_gemini_outbound_review_bundle(current_evidence_packet, gemini_status)
    grok_bundle = build_grok_outbound_review_bundle(current_evidence_packet, grok_status)
    refresh_action = build_jarvis_ai_refresh_action_harness(
        symbol=normalized,
        current_evidence_packet=current_evidence_packet,
        refresh_guard=refresh_guard,
        gemini_bundle=gemini_bundle,
        grok_bundle=grok_bundle,
        execute_requested=False,
    )
    verified_packet = build_jarvis_verified_review_packet(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        gemini_status=gemini_status,
        grok_status=grok_status,
        gemini_bundle=gemini_bundle,
        grok_bundle=grok_bundle,
        review_records=external_records,
        refresh_action=refresh_action,
    )
    current_evidence_hash = _hash_refresh_packet(current_evidence_packet)
    evidence_diff = build_jarvis_ai_response_evidence_diff(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        records=external_records,
        current_evidence_packet_hash=current_evidence_hash,
    )
    disagreement = build_jarvis_provider_disagreement_explorer(
        symbol=normalized,
        evidence_packet=current_evidence_packet,
        ai_comparison=comparison_records[0] if comparison_records else {},
        evidence_diff=evidence_diff,
        kronos_report=build_kronos_status().model_dump(),
        openalgo_summary=summarize_openalgo_report(storage.load_latest_openalgo_report_import(normalized)),
    )
    latency = build_jarvis_latency_budget_report(evidence_bundle)
    freshness = build_realtime_freshness_report(bundle=evidence_bundle, latency_budget=latency, max_age_seconds=max_age_seconds)
    provider_status = build_gemini_provider_status()
    outbound_bundle = build_gemini_outbound_review_bundle(current_evidence_packet, provider_status)
    sample_review = build_sample_gemini_review_for_display(current_evidence_packet)
    gemini_room = build_gemini_decision_room_report(
        symbol=normalized,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        sample_review=sample_review,
        realtime_freshness=freshness,
        decision_quality=evidence_bundle["decision_quality"],
        trading_decision_output=evidence_bundle["trading_decision_output"],
    )
    paper_bridge = build_openalgo_paper_bridge_report(
        symbol=normalized,
        handoff_gate=evidence_bundle["openalgo_handoff"],
        decision_quality=evidence_bundle["decision_quality"],
        realtime_freshness=freshness,
        gemini_decision_room=gemini_room,
    )
    binding = build_openalgo_safe_intent_binding(
        symbol=normalized,
        jarvis_room=room,
        verified_review_packet=verified_packet,
        disagreement_explorer=disagreement,
        openalgo_handoff_gate=evidence_bundle["openalgo_handoff"],
        openalgo_paper_bridge=paper_bridge,
    )
    final_audit = _build_current_jarvis_final_audit(normalized, timeframe, rows, position, stale_after_seconds, max_age_seconds)
    report = build_jarvis_paper_ready_safety_audit(
        symbol=normalized,
        jarvis_room=room,
        realtime_freshness=freshness,
        decision_quality=evidence_bundle["decision_quality"],
        verified_review_packet=verified_packet,
        provider_disagreement=disagreement,
        openalgo_safe_binding=binding,
        final_production_audit=final_audit,
    )
    audit("info" if report["blocking_count"] == 0 else "warning", f"Paper-ready safety audit for {normalized}: {report['final_state']}", "jarvis_paper_ready_audit")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/gemini/outbound-bundle/{symbol}")
async def jarvis_gemini_outbound_bundle(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    bundle = build_gemini_outbound_review_bundle(room, build_gemini_provider_status())
    audit("info", f"Gemini outbound review bundle generated for {room['symbol']}: dry_run={bundle['dry_run_only']}", "jarvis_gemini")
    return envelope(bundle, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/gemini/fallback-readiness/{symbol}")
async def jarvis_gemini_fallback_readiness(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    provider_status = build_gemini_provider_status()
    outbound_bundle = build_gemini_outbound_review_bundle(room, provider_status)
    report = build_gemini_fallback_readiness_report(
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
    )
    audit("info", f"Gemini fallback readiness generated for {room['symbol']}: {report['readiness_state']}", "jarvis_gemini")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/gemini/live-review-harness/{symbol}")
async def jarvis_gemini_live_review_harness(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    provider_status = build_gemini_provider_status()
    outbound_bundle = build_gemini_outbound_review_bundle(room, provider_status)
    fallback_readiness = build_gemini_fallback_readiness_report(
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
    )
    report = build_gemini_live_review_harness(
        evidence_packet=room,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        fallback_readiness=fallback_readiness,
        execute=False,
    )
    audit("info", f"Gemini live review harness dry-run generated for {room['symbol']}: {report['execution_state']}", "jarvis_gemini")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/gemini/decision-room/{symbol}")
async def jarvis_gemini_decision_room(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900, max_age_seconds: float = 10.0):
    normalized = _normalize_symbol(symbol)
    evidence_bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    provider_status = build_gemini_provider_status()
    evidence_packet = _jarvis_external_ai_evidence_packet(evidence_bundle["room"])
    outbound_bundle = build_gemini_outbound_review_bundle(evidence_packet, provider_status)
    sample_review = build_sample_gemini_review_for_display(evidence_packet)
    latency = build_jarvis_latency_budget_report(evidence_bundle)
    freshness = build_realtime_freshness_report(bundle=evidence_bundle, latency_budget=latency, max_age_seconds=max_age_seconds)
    report = build_gemini_decision_room_report(
        symbol=normalized,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        sample_review=sample_review,
        realtime_freshness=freshness,
        decision_quality=evidence_bundle["decision_quality"],
        trading_decision_output=evidence_bundle["trading_decision_output"],
    )
    audit("info", f"Gemini decision room generated for {normalized}: {report['safe_final_action']}", "jarvis_gemini_decision_room")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/gemini/live-review/{symbol}")
async def jarvis_gemini_live_review(symbol: str, payload: dict[str, Any] | None = None, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    body = payload or {}
    execute = bool(body.get("execute", False))
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    evidence_packet = _jarvis_external_ai_evidence_packet(room)
    report = await build_gemini_live_review_report(evidence_packet=evidence_packet, execute=execute)
    saved = storage.save_external_ai_review_record({**report["review_intake"], "symbol": normalized, "timeframe": timeframe})
    report["saved_review_id"] = saved["review_id"]
    audit("info", f"Gemini live review report generated for {normalized}: {report['safe_final_action']}", "jarvis_gemini_live_review")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/openalgo/paper-bridge/{symbol}")
async def jarvis_openalgo_paper_bridge(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900, max_age_seconds: float = 10.0):
    normalized = _normalize_symbol(symbol)
    evidence_bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    latency = build_jarvis_latency_budget_report(evidence_bundle)
    freshness = build_realtime_freshness_report(bundle=evidence_bundle, latency_budget=latency, max_age_seconds=max_age_seconds)
    provider_status = build_gemini_provider_status()
    evidence_packet = _jarvis_external_ai_evidence_packet(evidence_bundle["room"])
    outbound_bundle = build_gemini_outbound_review_bundle(evidence_packet, provider_status)
    sample_review = build_sample_gemini_review_for_display(evidence_packet)
    gemini_room = build_gemini_decision_room_report(
        symbol=normalized,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        sample_review=sample_review,
        realtime_freshness=freshness,
        decision_quality=evidence_bundle["decision_quality"],
        trading_decision_output=evidence_bundle["trading_decision_output"],
    )
    report = build_openalgo_paper_bridge_report(
        symbol=normalized,
        handoff_gate=evidence_bundle["openalgo_handoff"],
        decision_quality=evidence_bundle["decision_quality"],
        realtime_freshness=freshness,
        gemini_decision_room=gemini_room,
    )
    audit("info", f"OpenAlgo paper bridge generated for {normalized}: {report['bridge_state']}", "jarvis_openalgo_paper_bridge")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


def _build_current_jarvis_final_audit(normalized: str, timeframe: str, rows: int, position: str, stale_after_seconds: int, max_age_seconds: float) -> dict[str, Any]:
    evidence_bundle = _build_jarvis_evidence_bundle_for_endpoint(normalized, timeframe, rows, position, stale_after_seconds)
    latency = build_jarvis_latency_budget_report(evidence_bundle)
    freshness = build_realtime_freshness_report(bundle=evidence_bundle, latency_budget=latency, max_age_seconds=max_age_seconds)
    provider_status = build_gemini_provider_status()
    evidence_packet = _jarvis_external_ai_evidence_packet(evidence_bundle["room"])
    outbound_bundle = build_gemini_outbound_review_bundle(evidence_packet, provider_status)
    sample_review = build_sample_gemini_review_for_display(evidence_packet)
    gemini_room = build_gemini_decision_room_report(
        symbol=normalized,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        sample_review=sample_review,
        realtime_freshness=freshness,
        decision_quality=evidence_bundle["decision_quality"],
        trading_decision_output=evidence_bundle["trading_decision_output"],
    )
    paper_bridge = build_openalgo_paper_bridge_report(
        symbol=normalized,
        handoff_gate=evidence_bundle["openalgo_handoff"],
        decision_quality=evidence_bundle["decision_quality"],
        realtime_freshness=freshness,
        gemini_decision_room=gemini_room,
    )
    return build_jarvis_final_production_audit(
        symbol=normalized,
        final_release_audit=build_final_release_audit(),
        deployment_readiness=deployment_readiness(),
        realtime_freshness=freshness,
        gemini_decision_room=gemini_room,
        openalgo_paper_bridge=paper_bridge,
        decision_quality=evidence_bundle["decision_quality"],
        trading_decision_output=evidence_bundle["trading_decision_output"],
        chart_overlay_qa=evidence_bundle["chart_overlay_qa"],
    )


@app.get("/api/v1/jarvis/final-production-audit/{symbol}")
async def jarvis_final_production_audit(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900, max_age_seconds: float = 10.0):
    normalized = _normalize_symbol(symbol)
    report = _build_current_jarvis_final_audit(normalized, timeframe, rows, position, stale_after_seconds, max_age_seconds)
    audit("info", f"Jarvis final production audit generated for {normalized}: {report['overall_state']}", "jarvis_final_production_audit")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/readiness-remediation/{symbol}")
async def jarvis_readiness_remediation(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900, max_age_seconds: float = 10.0):
    normalized = _normalize_symbol(symbol)
    final_audit = build_final_release_audit()
    deploy = deployment_readiness()
    jarvis_audit = _build_current_jarvis_final_audit(normalized, timeframe, rows, position, stale_after_seconds, max_age_seconds)
    report = build_readiness_remediation_report(
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        jarvis_final_audit=jarvis_audit,
    )
    audit("info", f"Jarvis readiness remediation generated for {normalized}: {len(report['remediation_steps'])} steps", "jarvis_readiness_remediation")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/gemini/live-review-harness/{symbol}")
async def jarvis_gemini_live_review_harness_execute(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", execute: bool = False):
    room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    provider_status = build_gemini_provider_status()
    outbound_bundle = build_gemini_outbound_review_bundle(room, provider_status)
    fallback_readiness = build_gemini_fallback_readiness_report(
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
    )
    report = build_gemini_live_review_harness(
        evidence_packet=room,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        fallback_readiness=fallback_readiness,
        execute=execute,
    )
    audit("info", f"Gemini live review harness requested for {room['symbol']}: {report['execution_state']}", "jarvis_gemini")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/gemini/outbound-bundle")
async def jarvis_gemini_outbound_bundle_from_payload(payload: dict[str, Any]):
    evidence_packet = payload.get("evidence_packet", payload)
    bundle = build_gemini_outbound_review_bundle(evidence_packet if isinstance(evidence_packet, dict) else {"payload": evidence_packet}, build_gemini_provider_status())
    audit("info", f"Gemini outbound review bundle generated from payload: dry_run={bundle['dry_run_only']}", "jarvis_gemini")
    return envelope(bundle, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/external-ai/review-intake/sample/{symbol}")
async def jarvis_external_ai_review_intake_sample(symbol: str, source: str = "gemini", timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    room = _build_jarvis_room_without_persistence(symbol, timeframe, rows, position)
    evidence_packet = _jarvis_external_ai_evidence_packet(room)
    result = build_external_ai_review_sample(evidence_packet=evidence_packet, source=source)
    result = storage.save_external_ai_review_record({**result, "symbol": room["symbol"], "timeframe": timeframe})
    audit("info", f"External AI review sample intake generated for {room['symbol']}: {result['intake_status']}", "jarvis_external_ai")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/external-ai/review-intake")
async def jarvis_external_ai_review_intake(payload: dict[str, Any]):
    evidence_packet = payload.get("evidence_packet", {})
    candidate_response = payload.get("candidate_response", payload.get("response", {}))
    source = str(payload.get("source", "manual"))
    if not isinstance(evidence_packet, dict):
        evidence_packet = {"payload": evidence_packet}
    if not isinstance(candidate_response, dict):
        candidate_response = {"review_status": "invalid", "raw_response": candidate_response}
    result = build_external_ai_review_intake(
        evidence_packet=evidence_packet,
        candidate_response=candidate_response,
        source=source,
    )
    result = storage.save_external_ai_review_record(result)
    audit("info", f"External AI review intake processed from {result['source']}: {result['intake_status']}", "jarvis_external_ai")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/external-ai/reviews")
async def jarvis_external_ai_review_records(symbol: str | None = None, source: str | None = None, limit: int = 25):
    normalized = _normalize_symbol(symbol) if symbol else None
    return envelope(
        storage.list_external_ai_review_records(symbol=normalized, source=source, limit=limit),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/jarvis/external-ai/review-audit")
async def jarvis_external_ai_review_audit(symbol: str | None = None, limit: int = 100):
    normalized = _normalize_symbol(symbol) if symbol else None
    return envelope(storage.external_ai_review_summary(symbol=normalized, limit=limit), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/external-ai/reliability")
async def jarvis_external_ai_reliability(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    rows: int = 390,
    position: str = "tail",
    stale_after_seconds: int = 900,
):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    records = storage.list_external_ai_review_records(symbol=normalized, limit=100)
    report = build_external_ai_reliability_report(
        symbol=normalized,
        room=room,
        records=records,
        stale_after_seconds=stale_after_seconds,
    )
    audit("info", f"External AI reliability generated for {normalized}: {report['reliability_state']}", "jarvis_external_ai")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/verified-evidence/{symbol}")
async def jarvis_verified_evidence(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    reliability = build_external_ai_reliability_report(
        symbol=normalized,
        room=room,
        records=storage.list_external_ai_review_records(symbol=normalized, limit=100),
        stale_after_seconds=stale_after_seconds,
    )
    certificate = build_jarvis_verified_evidence_certificate(
        symbol=normalized,
        room=room,
        external_ai_reliability=reliability,
    )
    audit("info", f"Jarvis verified evidence certificate generated for {normalized}: {certificate['certificate_state']}", "jarvis_verified_evidence")
    return envelope(certificate, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/review-preflight/{symbol}")
async def jarvis_review_preflight(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    first_room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    second_room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    reliability = build_external_ai_reliability_report(
        symbol=normalized,
        room=first_room,
        records=storage.list_external_ai_review_records(symbol=normalized, limit=100),
        stale_after_seconds=stale_after_seconds,
    )
    certificate = build_jarvis_verified_evidence_certificate(
        symbol=normalized,
        room=first_room,
        external_ai_reliability=reliability,
    )
    fusion = build_jarvis_decision_fusion(first_room, build_gemini_provider_status())
    replay_report = build_jarvis_replay_determinism_report(first_room, second_room)
    final_audit = build_final_release_audit()
    deploy = deployment_readiness()
    transport = transport_status(check_health=True)
    security = build_security_posture()
    blocker_report = build_jarvis_production_blocker_report(
        fusion=fusion,
        replay_determinism=replay_report,
        final_release_audit=final_audit,
        deployment_readiness=deploy,
        openalgo_transport_status=transport,
    )
    resolution = build_jarvis_blocker_resolution_pack(
        blocker_report=blocker_report,
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        security_posture=security,
        transport_status=transport,
    )
    preflight = build_jarvis_preflight_evidence_pack(
        blocker_report=blocker_report,
        resolution_pack=resolution,
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        security_posture=security,
        transport_status=transport,
    )
    verdict = build_jarvis_review_preflight_verdict(
        symbol=normalized,
        verified_evidence=certificate,
        external_ai_reliability=reliability,
        preflight_evidence=preflight,
    )
    audit("info", f"Jarvis review preflight generated for {normalized}: {verdict['verdict_state']}", "jarvis_review_preflight")
    return envelope(verdict, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/correction-review-packet/{symbol}")
async def jarvis_correction_review_packet(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    packet = _build_correction_review_packet_for_symbol(normalized, timeframe, rows, position, stale_after_seconds)
    audit("info", f"Jarvis correction review packet generated for {normalized}: {packet['packet_state']}", "jarvis_correction_packet")
    return envelope(packet, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/correction-review/sample/{symbol}")
async def jarvis_correction_review_sample(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    packet = _build_correction_review_packet_for_symbol(symbol, timeframe, rows, position, stale_after_seconds)
    candidate = build_sample_correction_response(packet)
    validation = validate_correction_response(
        correction_packet=packet,
        candidate_response=candidate,
        source="gemini",
    )
    validation = storage.save_correction_response_record({**validation, "symbol": packet["symbol"]})
    audit("info", f"Jarvis correction review sample validated for {packet['symbol']}: {validation['display_status']}", "jarvis_correction_response")
    return envelope(validation, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/correction-review/validate")
async def jarvis_correction_review_validate(payload: dict[str, Any]):
    symbol = str(payload.get("symbol") or "RELIANCE")
    timeframe = str(payload.get("timeframe") or "1m")
    rows = int(payload.get("rows") or 390)
    position = str(payload.get("position") or "tail")
    stale_after_seconds = int(payload.get("stale_after_seconds") or 900)
    packet = payload.get("correction_packet")
    if not isinstance(packet, dict):
        packet = _build_correction_review_packet_for_symbol(symbol, timeframe, rows, position, stale_after_seconds)
    candidate = payload.get("candidate_response", payload.get("response", {}))
    if not isinstance(candidate, dict):
        candidate = {"review_status": "invalid", "raw_response": candidate}
    validation = validate_correction_response(
        correction_packet=packet,
        candidate_response=candidate,
        source=str(payload.get("source", "manual")),
    )
    validation = storage.save_correction_response_record({**validation, "symbol": packet.get("symbol", symbol)})
    audit("info", f"Jarvis correction review response validated for {packet.get('symbol', symbol)}: {validation['display_status']}", "jarvis_correction_response")
    return envelope(validation, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/correction-review/records")
async def jarvis_correction_review_records(symbol: str | None = None, source: str | None = None, limit: int = 25):
    normalized = _normalize_symbol(symbol) if symbol else None
    return envelope(
        storage.list_correction_response_records(symbol=normalized, source=source, limit=limit),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/jarvis/correction-review/audit")
async def jarvis_correction_review_audit(symbol: str | None = None, limit: int = 100):
    normalized = _normalize_symbol(symbol) if symbol else None
    return envelope(storage.correction_response_summary(symbol=normalized, limit=limit), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/external-ai/audit-integrity")
async def jarvis_external_ai_audit_integrity(symbol: str | None = None, limit: int = 100, stale_after_seconds: int = 86_400):
    normalized = _normalize_symbol(symbol) if symbol else None
    report = build_external_ai_audit_integrity_report(
        symbol=normalized,
        external_review_records=storage.list_external_ai_review_records(symbol=normalized, limit=limit),
        correction_response_records=storage.list_correction_response_records(symbol=normalized, limit=limit),
        stale_after_seconds=stale_after_seconds,
    )
    audit("info", f"External AI audit integrity generated for {normalized or 'ALL'}: {report['integrity_state']}", "jarvis_external_ai")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/daily-verified-authority/{symbol}")
async def jarvis_daily_verified_authority(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 86_400):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    report = build_daily_verified_authority_report(
        symbol=normalized,
        room=room,
        stale_after_seconds=stale_after_seconds,
    )
    audit("info", f"Daily verified authority generated for {normalized}: {report['authority_state']}", "jarvis_daily_authority")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/indicator-combination-memory/{symbol}")
async def jarvis_indicator_combination_memory(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    combo = build_combination_similarity_report(CombinationSimilarityRequest(symbol=normalized, timeframe=timeframe))
    report = build_indicator_combination_memory_report(room=room, combination_similarity=combo)
    audit("info", f"Indicator combination memory generated for {normalized}: {report['memory_state']}", "jarvis_indicator_combination")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/candle-cause-effect-memory/{symbol}")
async def jarvis_candle_cause_effect_memory(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    report = build_candle_cause_effect_memory_report(room=room)
    audit("info", f"Candle cause/effect memory generated for {normalized}: {report['memory_state']}", "jarvis_candle_effect")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/decision-evidence/export/{symbol}")
async def jarvis_decision_evidence_export(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail", stale_after_seconds: int = 900):
    normalized = _normalize_symbol(symbol)
    first_room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    second_room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    provider_status = build_gemini_provider_status()
    external_records = storage.list_external_ai_review_records(symbol=normalized, limit=100)
    correction_records = storage.list_correction_response_records(symbol=normalized, limit=100)
    reliability = build_external_ai_reliability_report(
        symbol=normalized,
        room=first_room,
        records=external_records,
        stale_after_seconds=stale_after_seconds,
    )
    certificate = build_jarvis_verified_evidence_certificate(
        symbol=normalized,
        room=first_room,
        external_ai_reliability=reliability,
    )
    fusion = build_jarvis_decision_fusion(first_room, provider_status)
    replay_report = build_jarvis_replay_determinism_report(first_room, second_room)
    final_audit = build_final_release_audit()
    deploy = deployment_readiness()
    transport = transport_status(check_health=True)
    security = build_security_posture()
    blocker_report = build_jarvis_production_blocker_report(
        fusion=fusion,
        replay_determinism=replay_report,
        final_release_audit=final_audit,
        deployment_readiness=deploy,
        openalgo_transport_status=transport,
    )
    resolution = build_jarvis_blocker_resolution_pack(
        blocker_report=blocker_report,
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        security_posture=security,
        transport_status=transport,
    )
    preflight = build_jarvis_preflight_evidence_pack(
        blocker_report=blocker_report,
        resolution_pack=resolution,
        deployment_readiness=deploy,
        final_release_audit=final_audit,
        security_posture=security,
        transport_status=transport,
    )
    review_preflight = build_jarvis_review_preflight_verdict(
        symbol=normalized,
        verified_evidence=certificate,
        external_ai_reliability=reliability,
        preflight_evidence=preflight,
    )
    audit_integrity = build_external_ai_audit_integrity_report(
        symbol=normalized,
        external_review_records=external_records,
        correction_response_records=correction_records,
        stale_after_seconds=86_400,
    )
    daily_authority = build_daily_verified_authority_report(
        symbol=normalized,
        room=first_room,
        stale_after_seconds=86_400,
    )
    packet = build_jarvis_decision_evidence_export(
        room=first_room,
        fusion=fusion,
        verified_evidence=certificate,
        review_preflight=review_preflight,
        daily_verified_authority=daily_authority,
        external_ai_reliability=reliability,
        external_ai_audit_integrity=audit_integrity,
        correction_audit=storage.correction_response_summary(symbol=normalized, limit=100),
    )
    audit("info", f"Jarvis decision evidence export generated for {normalized}: {packet['export_state']}", "jarvis_decision_evidence")
    return envelope(packet, capability_status=CapabilityStatus.MOCK)


def _build_correction_review_packet_for_symbol(symbol: str, timeframe: str, rows: int, position: str, stale_after_seconds: int) -> dict[str, Any]:
    normalized = _normalize_symbol(symbol)
    first_room = _build_jarvis_room_without_persistence(normalized, timeframe, rows, position)
    provider_status = build_gemini_provider_status()
    reliability = build_external_ai_reliability_report(
        symbol=normalized,
        room=first_room,
        records=storage.list_external_ai_review_records(symbol=normalized, limit=100),
        stale_after_seconds=stale_after_seconds,
    )
    certificate = build_jarvis_verified_evidence_certificate(
        symbol=normalized,
        room=first_room,
        external_ai_reliability=reliability,
    )
    review_preflight = build_jarvis_review_preflight_verdict(
        symbol=normalized,
        verified_evidence=certificate,
        external_ai_reliability=reliability,
        preflight_evidence=_build_review_only_preflight_evidence(normalized),
    )
    return build_jarvis_correction_review_packet(
        symbol=normalized,
        verified_evidence=certificate,
        review_preflight=review_preflight,
        provider_status=provider_status,
    )


def _build_review_only_preflight_evidence(symbol: str) -> dict[str, Any]:
    return {
        "preflight_version": "jarvis-preflight-evidence.v1.01",
        "symbol": symbol.upper(),
        "overall_status": "review_only_correction_path",
        "operator_decision": {
            "paper_review_allowed": False,
            "openalgo_dry_run_allowed": False,
            "live_trading_allowed": False,
        },
        "notes": [
            "Correction packet preflight is display-only and does not run final release audit.",
            "OpenAlgo dry-run review, broker routing, and live trading remain blocked.",
        ],
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


@app.post("/api/v1/jarvis/gemini/review")
async def jarvis_gemini_review(payload: dict[str, Any]):
    evidence_packet = payload.get("evidence_packet", payload)
    candidate_response = payload.get("candidate_response")
    result = build_gemini_review_stub(evidence_packet, candidate_response if isinstance(candidate_response, dict) else None)
    audit("info", f"Gemini review stub produced: {result['review_status']}", "jarvis_gemini")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/jarvis/gemini/review/sample")
async def jarvis_gemini_review_sample(payload: dict[str, Any]):
    result = build_sample_gemini_review_for_display(payload)
    audit("info", f"Gemini sample review display status: {result['display_status']}", "jarvis_gemini")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/jarvis/usefulness/{symbol}")
async def jarvis_usefulness(symbol: str, limit: int = 30):
    normalized = _normalize_symbol(symbol)
    records = storage.list_jarvis_usefulness_records(normalized, limit=limit)
    return envelope(build_jarvis_usefulness_summary(symbol=normalized, records=records), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/data/quality")
async def behavior_data_quality(payload: CandleSeries):
    result = scan_data_quality(payload)
    if result.blocks_trade:
        audit("warning", f"Behavior data quality blocked {payload.symbol}: score={result.data_quality_score}", "behavior_quality")
    return envelope(result)


@app.post("/api/v1/behavior/guards/point-in-time")
async def behavior_point_in_time_guard(payload: PointInTimeGuardRequest):
    result = run_point_in_time_guard(payload)
    if result.blocks_trade:
        audit("warning", f"Point-in-time guard blocked {payload.series.symbol}: {', '.join(result.reasons)}", "behavior_guard")
    return envelope(result)


@app.post("/api/v1/behavior/timeframes/synchronize")
async def behavior_timeframes_synchronize(payload: TimeframeSyncRequest):
    result = synchronize_timeframes(payload)
    if result.blocks_trade:
        audit("warning", f"Timeframe sync blocked {payload.symbol}: {', '.join(result.reasons)}", "behavior_timeframe_sync")
    return envelope(result)


@app.get("/api/v1/behavior/features/causal-whitelist")
async def behavior_causal_feature_whitelist():
    return envelope(causal_whitelist())


@app.post("/api/v1/behavior/features/validate")
async def behavior_causal_features_validate(payload: CausalFeatureValidationRequest):
    result = validate_causal_features(payload)
    if result.blocks_trade:
        audit("warning", f"Causal feature whitelist blocked: {', '.join(result.blocked_features)}", "behavior_causal_whitelist")
    return envelope(result)


@app.get("/api/v1/behavior/features/default-safe")
async def behavior_default_safe_features():
    return envelope(default_safe_features(TIME_STATE.virtual_timestamp_ns))


@app.post("/api/v1/behavior/candles/anatomy")
async def behavior_candle_anatomy(payload: CandleAnatomyRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Candle anatomy requires clean causal candle data.")
    result = analyze_candles(payload)
    return envelope(result)


@app.post("/api/v1/behavior/chart/reasoning/analyze")
async def behavior_chart_reasoning_analyze(payload: ChartReasoningRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Chart reasoning requires clean causal candle data.")
    result = build_chart_reasoning_report(payload)
    return envelope(result)


@app.get("/api/v1/behavior/chart/reasoning/current")
async def behavior_chart_reasoning_current(symbol: str = "RELIANCE", timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=False,
        )
        imported = import_ohlcv_csv(payload)
        series = imported.series
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
    quality = scan_data_quality(series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Chart reasoning requires clean causal candle data.")
    return envelope(build_chart_reasoning_report(ChartReasoningRequest(series=series)), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/conditions/classify")
async def behavior_conditions_classify(payload: ConditionClassifierRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Condition classifier requires clean causal candle data.")
    result = classify_conditions(payload)
    if result.blocks_trade:
        audit("warning", f"Condition classifier blocked {payload.series.symbol}: {result.no_trade_reason}", "behavior_classifier")
    return envelope(result)


@app.post("/api/v1/behavior/context/levels")
async def behavior_context_levels(payload: VwapOrbCprContextRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Level context requires clean causal candle data.")
    result = analyze_level_context(payload)
    if result.blocks_trade:
        audit("warning", f"Level context blocked {payload.series.symbol}: {', '.join(result.support_resistance_flags)}", "behavior_context")
    return envelope(result)


@app.post("/api/v1/behavior/context/htf")
async def behavior_context_htf(payload: HTFConfirmationRequest):
    result = analyze_htf_confirmation(payload)
    if result.blocks_trade:
        audit("warning", f"HTF context blocked {payload.symbol}: {', '.join(result.reasons)}", "behavior_context")
    return envelope(result)


@app.post("/api/v1/behavior/context/gap")
async def behavior_context_gap(payload: GapContextRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Gap context requires clean causal candle data.")
    result = analyze_gap_context(payload)
    if result.blocks_trade:
        audit("warning", f"Gap context blocked {payload.series.symbol}: trap={result.gap_trap_risk}", "behavior_context")
    return envelope(result)


@app.post("/api/v1/behavior/context/market")
async def behavior_context_market(payload: MarketContextRequest):
    result = analyze_market_context(payload)
    if result.blocks_trade:
        audit("warning", f"Market context blocked {payload.symbol}: {', '.join(result.reasons)}", "behavior_context")
    return envelope(result)


@app.post("/api/v1/behavior/market-regime/feedback")
async def behavior_market_regime_feedback(payload: MarketRegimeFeedbackRequest):
    result = build_market_regime_feedback_report(payload)
    if result.confidence_cap == "WAIT" or result.cooldown_active:
        audit("warning", f"Market regime feedback capped {result.symbol}: {result.confidence_cap}", "behavior_market_regime")
    return envelope(result)


@app.get("/api/v1/behavior/market-regime/feedback/current")
async def behavior_market_regime_feedback_current(symbol: str = "RELIANCE", timeframe: str = "5m"):
    normalized = _normalize_symbol(symbol)
    payload = MarketRegimeFeedbackRequest(
        symbol=normalized,
        timeframe=timeframe,  # type: ignore[arg-type]
        direction="long",
        stock_return_pct=0.85,
        index_return_pct=0.25,
        banknifty_return_pct=0.10,
        sector_return_pct=0.18,
        advance_decline_ratio=1.18,
        sector_advance_decline_ratio=1.05,
        stock_returns_pct=[-0.15, 0.05, 0.12, 0.18, 0.22, 0.35, 0.48, 0.52, 0.61, 0.85],
        index_returns_pct=[-0.10, 0.02, 0.05, 0.08, 0.12, 0.18, 0.20, 0.22, 0.24, 0.25],
        sector_returns_pct=[-0.08, 0.01, 0.04, 0.06, 0.10, 0.12, 0.15, 0.16, 0.17, 0.18],
        setup_sample_count=42,
        setup_success_count=25,
        setup_failure_count=17,
        vwap_respect_count=31,
        vwap_sample_count=42,
        breakout_failure_count=9,
        recent_signal_outcomes=["WIN", "LOSS", "WIN", "BREAKEVEN", "WIN"],
    )
    return envelope(build_market_regime_feedback_report(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/market-structure/liquidity/analyze")
async def behavior_market_structure_liquidity_analyze(payload: MarketStructureLiquidityRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Market structure liquidity requires clean causal candle data.")
    result = build_market_structure_liquidity_report(payload)
    if result.confidence_cap == "WAIT" or result.trap_score >= 0.70:
        audit("warning", f"Market structure liquidity capped {result.symbol}: trap={result.trap_score}", "behavior_market_structure")
    return envelope(result)


@app.get("/api/v1/behavior/market-structure/liquidity/current")
async def behavior_market_structure_liquidity_current(symbol: str = "RELIANCE", timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=False,
        )
        imported = import_ohlcv_csv(payload)
        series = imported.series
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
    quality = scan_data_quality(series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Market structure liquidity requires clean causal candle data.")
    return envelope(
        build_market_structure_liquidity_report(MarketStructureLiquidityRequest(series=series)),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/execution-event-oi/risk/analyze")
async def behavior_execution_event_oi_risk_analyze(payload: ExecutionEventOiRiskRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Execution/event/OI risk guard requires clean causal candle data.")
    result = build_execution_event_oi_risk_report(payload)
    # G9: when explicitly enabled, computed derivatives context replaces hand-typed
    # options fields through the identical report path. Any failure (flag off, no
    # provider/expiry, fetch error) keeps the base report — never raises, never blocks.
    try:
        from .orb.derivatives.integration import resolve_context_for_symbol

        _dctx = resolve_context_for_symbol(payload.series.symbol, PROJECT_ROOT)
        if _dctx is not None:
            result = build_report_with_derivatives_context(payload, _dctx)
    except Exception:
        pass
    if result.confidence_cap == "WAIT" or result.execution_plan_status == "BLOCKED":
        audit("warning", f"Execution/event/OI risk capped {result.symbol}: {result.execution_plan_status}", "behavior_execution_event_oi")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/execution-event-oi/risk/current")
async def behavior_execution_event_oi_risk_current(symbol: str = "RELIANCE", timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=False,
        )
        imported = import_ohlcv_csv(payload)
        series = imported.series
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
    quality = scan_data_quality(series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Execution/event/OI risk guard requires clean causal candle data.")
    latest_close = series.bars[-1].close if series.bars else 100.0
    return envelope(
        build_execution_event_oi_risk_report(
            ExecutionEventOiRiskRequest(
                series=series,
                entry_price=latest_close,
                stop_loss=latest_close * 0.99,
                target=latest_close * 1.015,
                event_context_status="unavailable",
                options_context_status="unavailable",
                depth_available=False,
            )
        ),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/post-entry/lifecycle/analyze")
async def behavior_post_entry_lifecycle_analyze(payload: PostEntryLifecycleRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Post-entry lifecycle requires clean causal candle data.")
    result = build_post_entry_lifecycle_report(payload)
    if result.current_thesis_status in {"weakening", "invalidated"}:
        audit("warning", f"Post-entry lifecycle {result.symbol}: {result.current_thesis_status}", "behavior_post_entry")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/post-entry/lifecycle/current")
async def behavior_post_entry_lifecycle_current(symbol: str = "RELIANCE", timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=False,
        )
        imported = import_ohlcv_csv(payload)
        series = imported.series
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
    quality = scan_data_quality(series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Post-entry lifecycle requires clean causal candle data.")
    return envelope(
        build_post_entry_lifecycle_report(PostEntryLifecycleRequest(series=series, add_on_requested=True, regime_state="unknown")),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/final-confluence/arbiter/analyze")
async def behavior_final_confluence_arbiter_analyze(payload: FinalConfluenceArbiterRequest):
    result = build_final_confluence_arbiter_report(payload)
    if result.final_decision in {"WAIT", "AVOID"} or result.dominant_blocker:
        audit("warning", f"Final confluence arbiter {result.symbol}: {result.final_decision} blocker={result.dominant_blocker}", "behavior_final_confluence")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/final-confluence/arbiter/current")
async def behavior_final_confluence_arbiter_current(symbol: str = "RELIANCE", timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=False,
        )
        imported = import_ohlcv_csv(payload)
        series = imported.series
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
    quality = scan_data_quality(series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Final confluence arbiter requires clean causal candle data.")
    chart = build_chart_reasoning_report(ChartReasoningRequest(series=series))
    structure = build_market_structure_liquidity_report(MarketStructureLiquidityRequest(series=series))
    latest_close = series.bars[-1].close if series.bars else 100.0
    execution = build_execution_event_oi_risk_report(
        ExecutionEventOiRiskRequest(
            series=series,
            entry_price=latest_close,
            stop_loss=latest_close * 0.99,
            target=latest_close * 1.015,
            event_context_status="unavailable",
            options_context_status="unavailable",
            depth_available=False,
        )
    )
    lifecycle = build_post_entry_lifecycle_report(
        PostEntryLifecycleRequest(series=series, add_on_requested=True, regime_state="unknown")
    )
    regime = build_market_regime_feedback_report(
        MarketRegimeFeedbackRequest(
            symbol=normalized,
            timeframe=timeframe,  # type: ignore[arg-type]
            direction="long",
            stock_return_pct=0.45,
            index_return_pct=0.20,
            banknifty_return_pct=0.10,
            sector_return_pct=0.18,
            advance_decline_ratio=1.10,
            sector_advance_decline_ratio=1.05,
            stock_returns_pct=[-0.10, 0.02, 0.08, 0.13, 0.21, 0.29, 0.35, 0.42, 0.44, 0.45],
            index_returns_pct=[-0.06, 0.01, 0.04, 0.07, 0.11, 0.14, 0.16, 0.18, 0.19, 0.20],
            sector_returns_pct=[-0.04, 0.01, 0.03, 0.06, 0.09, 0.11, 0.13, 0.15, 0.17, 0.18],
            setup_sample_count=42,
            setup_success_count=24,
            setup_failure_count=18,
            vwap_respect_count=28,
            vwap_sample_count=42,
            breakout_failure_count=8,
            recent_signal_outcomes=["WIN", "LOSS", "WIN", "BREAKEVEN", "WIN"],
        )
    )
    request = FinalConfluenceArbiterRequest(
        symbol=normalized,
        timeframe=timeframe,  # type: ignore[arg-type]
        direction="long",
        data_quality_pass=not quality.blocks_trade,
        liquidity_grade=execution.liquidity_grade,
        market_regime_score=(regime.posterior_confidence * 2.0) - 1.0,
        relative_strength_score=regime.relative_strength_score,
        structure_score=_arbiter_structure_score(structure.trap_score, structure.confidence_cap),
        volume_auction_score=-0.45 if structure.vsa_downgrade_active else 0.25,
        indicator_signal_score=(chart.trend_persistence_score * 2.0) - 1.0,
        external_ai_score=0.0,
        trap_score=structure.trap_score,
        event_risk_score=execution.event_risk_score,
        daily_resistance_conflict=structure.value_area_position == "below_value" and chart.rubber_band_risk == "overextended",
        weak_sector=regime.leading_lagging_state in {"lagging", "weak_laggard"} or regime.breadth_state == "weak",
        post_entry_thesis_status=lifecycle.current_thesis_status,
        evidence_count=5,
        no_future_leakage=chart.no_future_leakage and structure.no_future_leakage and execution.no_future_leakage and lifecycle.no_future_leakage,
    )
    return envelope(build_final_confluence_arbiter_report(request), capability_status=CapabilityStatus.MOCK)


def _arbiter_structure_score(trap_score: float, confidence_cap: str) -> float:
    if trap_score >= 0.70:
        return -0.80
    if confidence_cap == "WAIT":
        return -0.35
    if confidence_cap == "WATCH":
        return 0.20
    return 0.45


@app.post("/api/v1/behavior/context/full")
async def behavior_context_full(payload: BehaviorContextRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Full behavior context requires clean causal candle data.")
    result = analyze_behavior_context(payload)
    if result.blocks_trade:
        audit("warning", f"Full context blocked {payload.series.symbol}: {result.reason_tree.get('final')}", "behavior_context")
    return envelope(result)


@app.post("/api/v1/behavior/session/rhythm")
async def behavior_session_rhythm(payload: SessionRhythmRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Session rhythm requires clean causal candle data.")
    result = analyze_session_rhythm(payload)
    if result.blocks_trade:
        audit("warning", f"Session rhythm blocked {payload.series.symbol}: {result.no_trade_reason}", "behavior_session")
    return envelope(result)


@app.get("/api/v1/behavior/stock/{symbol}/session-memory")
async def behavior_stock_session_memory(symbol: str):
    profile, memory, _ = _ensure_behavior_seed_data(symbol)
    profiles = build_session_memory_profiles(profile.symbol, memory)
    for session_profile in profiles:
        storage.save_session_memory_profile(session_profile)
    return envelope(profiles)


@app.get("/api/v1/behavior/stock/{symbol}/day-of-week-memory")
async def behavior_stock_day_of_week_memory(symbol: str):
    profile, memory, _ = _ensure_behavior_seed_data(symbol)
    return envelope(build_day_of_week_memory(profile.symbol, memory))


@app.get("/api/v1/behavior/exact-time/session-memory/current")
async def behavior_exact_time_session_memory_current(symbol: str = "NIFTY-MOCK", timeframe: str = "5m"):
    return envelope(
        build_exact_time_session_memory_report(ExactTimeSessionMemoryRequest(symbol=symbol, timeframe=timeframe)),  # type: ignore[arg-type]
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/exact-time/session-memory")
async def behavior_exact_time_session_memory(payload: ExactTimeSessionMemoryRequest):
    return envelope(build_exact_time_session_memory_report(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/stock/{symbol}/dna/summary")
async def behavior_stock_dna_summary(symbol: str, payload: SessionRhythmRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Stock DNA summary requires clean causal candle data.")
    profile, memory, _ = _ensure_behavior_seed_data(symbol)
    rhythm = analyze_session_rhythm(payload)
    summary = build_stock_dna_summary(stock_dna=profile, rhythm=rhythm, memory=memory)
    for session_profile in summary.session_memory:
        storage.save_session_memory_profile(session_profile)
    audit("info", f"Stock DNA summary refreshed for {profile.symbol}", "behavior_session")
    return envelope(summary)


@app.post("/api/v1/behavior/pattern-memory/analyze")
async def behavior_pattern_memory_analyze(payload: PatternMemoryRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Pattern memory requires clean causal candle data.")
    _, memory, _ = _ensure_behavior_seed_data(payload.series.symbol)
    result = analyze_pattern_memory(payload, memory)
    for match in result.matches:
        storage.save_similar_day_match(match)
    if result.no_trade_reason:
        audit("warning", f"Pattern memory guarded {payload.series.symbol}: {result.no_trade_reason}", "behavior_pattern_memory")
    else:
        audit("info", f"Pattern memory analyzed {payload.series.symbol}", "behavior_pattern_memory")
    return envelope(result)


@app.get("/api/v1/behavior/stock/{symbol}/pattern-memory")
async def behavior_stock_pattern_memory(symbol: str):
    request = _default_pattern_memory_request(symbol)
    _, memory, _ = _ensure_behavior_seed_data(symbol)
    result = analyze_pattern_memory(request, memory)
    for match in result.matches:
        storage.save_similar_day_match(match)
    return envelope(result)


@app.post("/api/v1/behavior/outcomes/label")
async def behavior_outcome_label(payload: OutcomeLabelRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Outcome labeling requires clean causal candle data.")
    result = label_trade_outcome(payload)
    storage.save_outcome_label(result)
    if result.outcome_label in {"SL_HIT", "FAKE_BREAKOUT", "RETEST_FAIL", "CHOP_NO_FOLLOWTHROUGH"}:
        library = build_failure_library(result.symbol, [], [result])
        for failure in library.failures:
            storage.save_failure_pattern(failure)
        audit("warning", f"Outcome labeled failure for {result.symbol}: {result.outcome_label}", "behavior_outcome")
    else:
        audit("info", f"Outcome labeled for {result.symbol}: {result.outcome_label}", "behavior_outcome")
    return envelope(result)


@app.post("/api/v1/behavior/outcomes/conservative-label")
async def behavior_conservative_outcome_label(payload: ConservativeOutcomeLabelRequest):
    quality = scan_data_quality(payload.series)
    if quality.blocks_trade:
        raise api_error(409, "behavior_data_quality_blocked", "Conservative outcome labeling requires clean causal candle data.")
    result = label_conservative_outcome(payload)
    storage.save_conservative_outcome_label(result)
    if result.outcome_label in {
        "SL_HIT_FIRST",
        "GAP_THROUGH_STOP",
        "AMBIGUOUS_BOTH_HIT_SAME_BAR",
        "FAKE_BREAKOUT",
        "RETEST_FAIL",
        "CHOP_NO_FOLLOWTHROUGH",
        "NO_FILL",
    }:
        audit("warning", f"Conservative outcome labeled risk for {result.symbol}: {result.outcome_label}", "behavior_conservative_outcome")
    else:
        audit("info", f"Conservative outcome labeled for {result.symbol}: {result.outcome_label}", "behavior_conservative_outcome")
    return envelope(result)


@app.get("/api/v1/behavior/outcomes/conservative-label/current")
async def behavior_conservative_outcome_label_current(symbol: str = "NIFTY-MOCK"):
    normalized = _normalize_symbol(symbol)
    result = label_conservative_outcome(_default_conservative_outcome_label_request(normalized))
    storage.save_conservative_outcome_label(result)
    return envelope(result)


@app.get("/api/v1/behavior/stock/{symbol}/failure-library")
async def behavior_failure_library(symbol: str):
    normalized = _normalize_symbol(symbol)
    _, memory, _ = _ensure_behavior_seed_data(normalized)
    stored_outcomes = storage.list_outcome_labels(normalized)
    if not stored_outcomes:
        default_outcome = label_trade_outcome(_default_outcome_label_request(normalized))
        storage.save_outcome_label(default_outcome)
        stored_outcomes = [default_outcome]
    library = build_failure_library(normalized, memory, stored_outcomes)
    for failure in library.failures:
        storage.save_failure_pattern(failure)
    return envelope(library)


@app.get("/api/v1/behavior/stock/{symbol}/trust-table")
async def behavior_learning_trust(symbol: str):
    normalized = _normalize_symbol(symbol)
    _, memory, _ = _ensure_behavior_seed_data(normalized)
    outcomes = storage.list_outcome_labels(normalized)
    if not outcomes:
        default_outcome = label_trade_outcome(_default_outcome_label_request(normalized))
        storage.save_outcome_label(default_outcome)
        outcomes = [default_outcome]
    trust = build_learning_trust(normalized, memory, outcomes)
    for record in trust.records:
        storage.save_learning_trust_record(record)
    return envelope(trust)


@app.get("/api/v1/behavior/stock/{symbol}/memory-profile/current")
async def behavior_stock_memory_profile_current(symbol: str):
    return envelope(_build_stock_memory_profile(symbol=symbol, timeframe="5m", seed=42))


@app.post("/api/v1/behavior/stock/memory-profile")
async def behavior_stock_memory_profile(payload: StockMemoryProfileRequest):
    return envelope(_build_stock_memory_profile(symbol=payload.symbol, timeframe=payload.timeframe, seed=payload.seed))


@app.post("/api/v1/behavior/decision/evaluate")
async def behavior_decision_evaluate(payload: BehaviorDecisionRequest):
    result = evaluate_trade_decision(payload)
    audit(
        "warning" if not result.trade_allowed else "info",
        f"Behavior decision for {result.symbol}: {result.final_trade_decision}",
        "behavior_decision",
    )
    return envelope(result)


@app.get("/api/v1/behavior/decision/current")
async def behavior_decision_current(symbol: str = "NIFTY-MOCK"):
    payload = _default_behavior_decision_request(symbol)
    result = evaluate_trade_decision(payload)
    return envelope(result)


@app.post("/api/v1/behavior/risk/evaluate")
async def behavior_risk_evaluate(payload: BehaviorRiskRequest):
    result = evaluate_behavior_risk(payload)
    audit(
        "warning" if not result.trade_allowed else "info",
        f"Behavior risk sizing for {result.symbol}: size={result.position_size} allowed={result.trade_allowed}",
        "behavior_risk",
    )
    return envelope(result)


@app.get("/api/v1/behavior/risk/current")
async def behavior_risk_current(symbol: str = "NIFTY-MOCK"):
    decision = evaluate_trade_decision(_default_behavior_decision_request(symbol))
    payload = _default_behavior_risk_request(symbol, decision.final_trade_decision, decision.confidence_pct)
    result = evaluate_behavior_risk(payload)
    return envelope(result)


@app.post("/api/v1/behavior/execution/simulate")
async def behavior_execution_simulate(payload: BehaviorExecutionRequest):
    result = simulate_behavior_execution(payload)
    storage.save_execution_simulation(result)
    audit(
        "warning" if result.fill_status in {"NO_FILL", "PARTIAL_FILL", "REJECTED_SIMULATION"} else "info",
        f"Behavior execution simulation for {result.symbol}: {result.fill_status}",
        "behavior_execution",
    )
    return envelope(result)


@app.get("/api/v1/behavior/execution/current")
async def behavior_execution_current(symbol: str = "NIFTY-MOCK"):
    decision = evaluate_trade_decision(_default_behavior_decision_request(symbol))
    risk_payload = _default_behavior_risk_request(symbol, decision.final_trade_decision, decision.confidence_pct)
    risk = evaluate_behavior_risk(risk_payload)
    execution_payload = _default_behavior_execution_request(symbol, risk.position_size)
    result = simulate_behavior_execution(execution_payload)
    storage.save_execution_simulation(result)
    return envelope(result)


@app.post("/api/v1/behavior/validation/run")
async def behavior_validation_run(payload: BehaviorValidationRequest):
    result = run_behavior_validation(payload)
    audit(
        "warning" if not result.promotion_allowed else "info",
        f"Behavior validation {result.validation_type} for {result.symbol}: promotion_allowed={result.promotion_allowed}",
        "behavior_validation",
    )
    return envelope(result)


@app.get("/api/v1/behavior/validation/walk-forward")
async def behavior_validation_walk_forward(symbol: str = "NIFTY-MOCK"):
    return envelope(run_behavior_validation(BehaviorValidationRequest(symbol=symbol, validation_type="walk_forward", folds=3)))


@app.get("/api/v1/behavior/validation/out-of-sample")
async def behavior_validation_out_of_sample(symbol: str = "NIFTY-MOCK"):
    return envelope(run_behavior_validation(BehaviorValidationRequest(symbol=symbol, validation_type="out_of_sample", folds=1)))


@app.post("/api/v1/behavior/safety/drift")
async def behavior_safety_drift(payload: BehaviorDriftRequest):
    result = evaluate_behavior_drift(payload)
    audit(
        "warning" if result.memory_quarantine_required else "info",
        f"Behavior drift check for {result.symbol}: status={result.drift_status} score={result.drift_score}",
        "behavior_safety",
    )
    return envelope(result)


@app.get("/api/v1/behavior/safety/drift/current")
async def behavior_safety_drift_current(symbol: str = "NIFTY-MOCK"):
    return envelope(evaluate_behavior_drift(default_drift_request(symbol)))


@app.post("/api/v1/behavior/safety/ood")
async def behavior_safety_ood(payload: BehaviorOODRequest):
    result = evaluate_behavior_ood(payload)
    audit(
        "warning" if result.confidence_blocked else "info",
        f"Behavior OOD check for {result.symbol}: status={result.ood_status} score={result.ood_score}",
        "behavior_safety",
    )
    return envelope(result)


@app.get("/api/v1/behavior/safety/ood/current")
async def behavior_safety_ood_current(symbol: str = "NIFTY-MOCK"):
    return envelope(evaluate_behavior_ood(default_ood_request(symbol)))


@app.post("/api/v1/behavior/safety/reality-gap")
async def behavior_safety_reality_gap(payload: RealityGapCheckRequest):
    result = evaluate_reality_gap(payload)
    audit(
        "warning" if result.alert else "info",
        f"Behavior reality-gap check for {result.symbol}: severity={result.severity} score={result.reality_gap_score}",
        "behavior_safety",
    )
    return envelope(result)


@app.get("/api/v1/behavior/safety/reality-gap/current")
async def behavior_safety_reality_gap_current(symbol: str = "NIFTY-MOCK"):
    return envelope(evaluate_reality_gap(default_reality_gap_request(symbol)))


@app.get("/api/v1/behavior/acp/status")
async def behavior_acp_status(symbol: str = "NIFTY-MOCK"):
    drift = evaluate_behavior_drift(default_drift_request(symbol))
    ood = evaluate_behavior_ood(default_ood_request(symbol))
    reality_gap = evaluate_reality_gap(default_reality_gap_request(symbol))
    return envelope(build_acp_hardening_status(drift=drift, ood=ood, reality_gap=reality_gap))


@app.get("/api/v1/behavior/safety/report/current")
async def behavior_safety_report_current(symbol: str = "NIFTY-MOCK"):
    report = _build_and_save_behavior_safety_report(symbol, stress=False)
    return envelope(report)


@app.post("/api/v1/behavior/safety/report/run")
async def behavior_safety_report_run(symbol: str = "NIFTY-MOCK", stress: bool = False):
    report = _build_and_save_behavior_safety_report(symbol, stress=stress)
    audit(
        "warning" if not report.promotion_allowed else "info",
        f"Behavior safety report for {report.symbol}: promotion_allowed={report.promotion_allowed}",
        "behavior_safety",
    )
    return envelope(report)


@app.get("/api/v1/behavior/safety/reports")
async def behavior_safety_reports(symbol: str | None = None):
    return envelope(storage.list_behavior_safety_reports(_normalize_symbol(symbol) if symbol else None))


@app.get("/api/v1/behavior/safety/reports/{report_id}")
async def behavior_safety_report_get(report_id: str):
    report = storage.load_behavior_safety_report(report_id)
    if report is None:
        raise api_error(404, "behavior_safety_report_not_found", f"Behavior safety report not found: {report_id}")
    return envelope(report)


@app.post("/api/v1/behavior/memory/quarantine")
async def behavior_memory_quarantine(payload: MemoryQuarantineRequest):
    normalized = _normalize_symbol(payload.symbol)
    _, memory, _ = _ensure_behavior_seed_data(normalized)
    source_report = storage.load_behavior_safety_report(payload.source_report_id) if payload.source_report_id else None
    record = build_memory_quarantine(
        payload,
        available_memory_ids=[item.memory_id for item in memory],
        source_report=source_report,
    )
    storage.save_memory_quarantine(record)
    audit("warning", f"Behavior memory quarantined for {record.symbol}: {record.reason}", "behavior_memory")
    return envelope(record)


@app.get("/api/v1/behavior/memory/quarantine")
async def behavior_memory_quarantines(symbol: str | None = None, active_only: bool = False):
    return envelope(storage.list_memory_quarantines(_normalize_symbol(symbol) if symbol else None, active_only=active_only))


@app.get("/api/v1/behavior/memory/rebuild-plan/{symbol}")
async def behavior_memory_rebuild_plan(symbol: str):
    normalized = _normalize_symbol(symbol)
    quarantines = storage.list_memory_quarantines(normalized, active_only=True)
    return envelope(build_memory_rebuild_plan(symbol=normalized, quarantines=quarantines))


@app.get("/api/v1/behavior/replay/golden-fixtures")
async def behavior_golden_replay_fixtures():
    _ensure_golden_replay_fixtures()
    return envelope(storage.list_golden_replay_fixtures())


@app.get("/api/v1/behavior/replay/golden-fixtures/{fixture_id}/verify")
async def behavior_golden_replay_fixture_verify(fixture_id: str):
    _ensure_golden_replay_fixtures()
    fixture = storage.load_golden_replay_fixture(fixture_id)
    if fixture is None:
        raise api_error(404, "golden_replay_fixture_not_found", f"Golden replay fixture not found: {fixture_id}")
    events = deterministic_events(fixture.seed, fixture.scenario_id, fixture.expected_event_count)
    return envelope(verify_golden_replay_fixture(fixture, events))


def _behavior_layer_contracts() -> list[BehaviorLayerContract]:
    implemented_layers = {1, 2, 7, 8, 9, 11, 12, 13, 15, 17, 18, 20, 21, 22, 23, 26, 27, 28, 29, 30, 31, 32}
    return [
        BehaviorLayerContract(
            layer_index=idx,
            layer_name=layer_name,
            contract_name=contract_name,
            status=CapabilityStatus.MOCK if idx in implemented_layers else CapabilityStatus.RESERVED,
            required=True,
        )
        for idx, (layer_name, contract_name) in enumerate(zip(BEHAVIOR_LAYER_NAMES, BEHAVIOR_LAYER_CONTRACTS), start=1)
    ]


def _behavior_output_columns() -> list[BehaviorOutputColumn]:
    groups = (
        ["base_behavior"] * 8
        + ["probability"] * 6
        + ["expectation"] * 4
        + ["trade_parameters"] * 5
        + ["quality_safety"] * 18
        + ["confidence_decision"] * 4
        + ["production_audit"] * 29
    )
    return [
        BehaviorOutputColumn(index=idx, name=name, group=groups[idx - 1])
        for idx, name in enumerate(EXPECTED_74_COLUMNS, start=1)
    ]


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _build_and_save_behavior_safety_report(symbol: str, *, stress: bool) -> BehaviorSafetyReport:
    normalized = _normalize_symbol(symbol)
    drift = evaluate_behavior_drift(high_drift_request(normalized) if stress else default_drift_request(normalized))
    ood = evaluate_behavior_ood(high_ood_request(normalized) if stress else default_ood_request(normalized))
    reality_gap = evaluate_reality_gap(high_reality_gap_request(normalized) if stress else default_reality_gap_request(normalized))
    acp = build_acp_hardening_status(drift=drift, ood=ood, reality_gap=reality_gap)
    report = build_safety_report(symbol=normalized, drift=drift, ood=ood, reality_gap=reality_gap, acp=acp)
    storage.save_behavior_safety_report(report)
    return report


def _build_and_save_benchmark_report(symbol: str) -> BehaviorBenchmarkReport:
    normalized = _normalize_symbol(symbol)
    walk_forward = run_behavior_validation(BehaviorValidationRequest(symbol=normalized, validation_type="walk_forward", folds=3, seed=42))
    out_of_sample = run_behavior_validation(BehaviorValidationRequest(symbol=normalized, validation_type="out_of_sample", folds=1, seed=42))
    safety_report = _build_and_save_behavior_safety_report(normalized, stress=False)
    _ensure_golden_replay_fixtures()
    verifications = []
    for fixture in storage.list_golden_replay_fixtures(limit=25):
        events = deterministic_events(fixture.seed, fixture.scenario_id, fixture.expected_event_count)
        verifications.append(verify_golden_replay_fixture(fixture, events))
    report = build_benchmark_report(
        symbol=normalized,
        walk_forward=walk_forward,
        out_of_sample=out_of_sample,
        safety_report=safety_report,
        golden_verifications=verifications,
    )
    storage.save_behavior_benchmark_report(report)
    return report


def _build_and_save_behavior_scenario_coverage(symbol: str) -> BehaviorScenarioCoverageReport:
    report = _build_and_save_benchmark_report(symbol)
    coverage = build_behavior_scenario_coverage(report)
    storage.save_behavior_scenario_coverage_report(coverage)
    return coverage


def _build_release_approval_request(payload: ReleaseApprovalRequest) -> ReleaseApprovalRecord:
    normalized = _normalize_symbol(payload.symbol)
    report = storage.load_behavior_benchmark_report(payload.benchmark_report_id) if payload.benchmark_report_id else None
    if payload.benchmark_report_id and report is None:
        raise api_error(404, "behavior_benchmark_report_not_found", f"Behavior benchmark report not found: {payload.benchmark_report_id}")
    if report is None:
        report = _build_and_save_benchmark_report(normalized)
    checklist = build_mock_to_replay_checklist(
        symbol=normalized,
        benchmark_report=report,
        manual_approval=False,
    )
    storage.save_release_checklist(checklist)
    requested_at = now_iso()
    expires_at = (datetime.fromisoformat(requested_at) + timedelta(minutes=payload.expires_in_minutes)).isoformat()
    approval_id = str(uuid5(NAMESPACE_URL, f"tradevision:release-approval:{normalized}:{report.report_id}:{payload.requested_by}:{requested_at}"))
    record = ReleaseApprovalRecord(
        approval_version="release-approval.v0.28",
        approval_id=approval_id,
        symbol=normalized,
        target_mode="REPLAY",
        approval_scope=payload.approval_scope,
        benchmark_report_id=report.report_id,
        checklist_id=checklist.checklist_id,
        requested_by=payload.requested_by,
        requested_at=requested_at,
        reason=payload.reason,
        status="requested",
        expires_at=expires_at,
        evidence=[
            f"benchmark_report_id={report.report_id}",
            f"benchmark_report_hash={report.report_hash}",
            f"release_checklist_id={checklist.checklist_id}",
            f"technical_release_pass={checklist.technical_release_pass}",
            "target_mode=REPLAY",
            "live_trading_blocked=true",
        ],
    )
    storage.save_release_approval(record)
    return record


def _approve_release_approval(approval_id: str, payload: ReleaseApprovalDecisionRequest) -> ReleaseApprovalRecord:
    record = storage.load_release_approval(approval_id)
    if record is None:
        raise api_error(404, "release_approval_not_found", f"Release approval not found: {approval_id}")
    if record.status == "approved":
        return record
    if record.status in {"rejected", "expired"}:
        raise api_error(409, "release_approval_closed", f"Release approval is already {record.status}")
    if payload.actor_id == record.requested_by:
        raise api_error(409, "release_approval_self_approval_blocked", "Release approval requires a different approving actor")
    now = now_iso()
    if datetime.fromisoformat(record.expires_at) <= datetime.fromisoformat(now):
        expired = record.model_copy(update={"status": "expired"})
        storage.save_release_approval(expired)
        raise api_error(409, "release_approval_expired", f"Release approval expired at {record.expires_at}")
    report = storage.load_behavior_benchmark_report(record.benchmark_report_id)
    if report is None:
        raise api_error(409, "release_approval_missing_benchmark_report", "Approval cannot proceed because benchmark evidence is missing")
    checklist = build_mock_to_replay_checklist(
        symbol=record.symbol,
        benchmark_report=report,
        manual_approval=True,
    )
    storage.save_release_checklist(checklist)
    approved = record.model_copy(
        update={
            "status": "approved",
            "approved_by": payload.actor_id,
            "approved_at": now,
            "checklist_id": checklist.checklist_id,
            "evidence": [
                *record.evidence,
                f"approved_by={payload.actor_id}",
                f"approval_reason={payload.reason}",
                f"approved_checklist_id={checklist.checklist_id}",
                f"release_allowed={checklist.release_allowed}",
                "live_trading_blocked=true",
            ],
        }
    )
    storage.save_release_approval(approved)
    return approved


def _reject_release_approval(approval_id: str, payload: ReleaseApprovalDecisionRequest) -> ReleaseApprovalRecord:
    record = storage.load_release_approval(approval_id)
    if record is None:
        raise api_error(404, "release_approval_not_found", f"Release approval not found: {approval_id}")
    if record.status in {"approved", "rejected", "expired"}:
        raise api_error(409, "release_approval_closed", f"Release approval is already {record.status}")
    now = now_iso()
    rejected = record.model_copy(
        update={
            "status": "rejected",
            "rejected_by": payload.actor_id,
            "rejected_at": now,
            "rejection_reason": payload.reason,
            "evidence": [*record.evidence, f"rejected_by={payload.actor_id}", f"rejection_reason={payload.reason}"],
        }
    )
    storage.save_release_approval(rejected)
    return rejected


def _build_and_save_release_evidence_bundle(symbol: str, approval_id: str | None = None) -> ReleaseEvidenceBundle:
    normalized = _normalize_symbol(symbol)
    approval = storage.load_release_approval(approval_id) if approval_id else None
    if approval_id and approval is None:
        raise api_error(404, "release_approval_not_found", f"Release approval not found: {approval_id}")
    if approval and approval.symbol != normalized:
        raise api_error(409, "release_approval_symbol_mismatch", f"Approval {approval.approval_id} belongs to {approval.symbol}, not {normalized}")
    if approval is not None:
        report = storage.load_behavior_benchmark_report(approval.benchmark_report_id)
        if report is None:
            raise api_error(409, "release_approval_missing_benchmark_report", "Approval cannot export evidence because benchmark evidence is missing")
    else:
        report = _build_and_save_benchmark_report(normalized)
        active = storage.latest_active_release_approval(normalized, report.report_id, now_iso())
        if active is not None:
            approval = active
        else:
            approvals = storage.list_release_approvals(normalized, status="approved", limit=10)
            approval = next((item for item in approvals if item.benchmark_report_id == report.report_id), None)
    checklist = build_mock_to_replay_checklist(
        symbol=normalized,
        benchmark_report=report,
        manual_approval=approval is not None and approval.status == "approved",
    )
    storage.save_release_checklist(checklist)
    bundle = build_release_evidence_bundle(
        symbol=normalized,
        benchmark_report=report,
        checklist=checklist,
        approval=approval,
    )
    storage.save_release_evidence_bundle(bundle)
    return bundle


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json_file(path: Path, payload: object) -> tuple[str, int]:
    raw = json.dumps(payload, sort_keys=True, indent=2, default=str).encode("utf-8")
    path.write_bytes(raw)
    return _sha256_bytes(raw), len(raw)


def _export_release_evidence_artifact(payload: ReleaseEvidenceArtifactExportRequest) -> ReleaseEvidenceArtifact:
    normalized = _normalize_symbol(payload.symbol)
    bundle = _build_and_save_release_evidence_bundle(normalized, payload.approval_id)
    created_at = now_iso()
    artifact_id = str(
        uuid5(
            NAMESPACE_URL,
            f"tradevision:release-artifact:{normalized}:{bundle.bundle_id}:{payload.requested_by}:{created_at}",
        )
    )
    release_artifact_root = _runtime_artifact_dir(RELEASE_ARTIFACT_DIR, "TRADEVISION_RELEASE_ARTIFACT_DIR")
    artifact_dir = release_artifact_root / _safe_id(normalized) / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = artifact_dir / "bundle.json"
    manifest_path = artifact_dir / "manifest.json"
    bundle_sha, bundle_size = _write_json_file(bundle_path, bundle.model_dump(mode="json"))
    manifest_payload = {
        "artifact_version": "release-evidence-artifact.v0.30",
        "artifact_id": artifact_id,
        "symbol": normalized,
        "target_mode": "REPLAY",
        "created_at": created_at,
        "requested_by": payload.requested_by,
        "reason": payload.reason,
        "artifact_format": payload.artifact_format,
        "bundle_id": bundle.bundle_id,
        "bundle_hash": bundle.bundle_hash,
        "bundle_file": "bundle.json",
        "bundle_sha256": bundle_sha,
        "bundle_size_bytes": bundle_size,
        "retention_days": payload.retention_days,
        "immutable": True,
        "live_trading_blocked": True,
        "contains_broker_credentials": False,
        "contains_live_orders": False,
    }
    manifest_sha, manifest_size = _write_json_file(manifest_path, manifest_payload)
    artifact = ReleaseEvidenceArtifact(
        artifact_version="release-evidence-artifact.v0.30",
        artifact_id=artifact_id,
        symbol=normalized,
        target_mode="REPLAY",
        created_at=created_at,
        requested_by=payload.requested_by,
        reason=payload.reason,
        artifact_format=payload.artifact_format,
        bundle_id=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        artifact_dir=str(artifact_dir),
        bundle_file_path=str(bundle_path),
        bundle_sha256=bundle_sha,
        bundle_size_bytes=bundle_size,
        manifest_file_path=str(manifest_path),
        manifest_sha256=manifest_sha,
        manifest_size_bytes=manifest_size,
        retention_days=payload.retention_days,
        immutable=True,
        live_trading_blocked=True,
        contains_broker_credentials=False,
        contains_live_orders=False,
    )
    storage.save_release_evidence_artifact(artifact)
    return artifact


def _verify_release_evidence_artifact(artifact: ReleaseEvidenceArtifact) -> ReleaseEvidenceArtifactVerification:
    issues: list[str] = []
    bundle_path = Path(artifact.bundle_file_path)
    manifest_path = Path(artifact.manifest_file_path)
    bundle_exists = bundle_path.exists()
    manifest_exists = manifest_path.exists()
    bundle_hash_matches = False
    manifest_hash_matches = False
    bundle_parseable = False
    if not bundle_exists:
        issues.append("Bundle file is missing.")
    else:
        bundle_bytes = bundle_path.read_bytes()
        bundle_hash_matches = _sha256_bytes(bundle_bytes) == artifact.bundle_sha256
        if not bundle_hash_matches:
            issues.append("Bundle SHA-256 does not match artifact record.")
        try:
            parsed = json.loads(bundle_bytes.decode("utf-8"))
            bundle_parseable = parsed.get("bundle_id") == artifact.bundle_id
            if not bundle_parseable:
                issues.append("Bundle JSON is parseable but bundle_id does not match artifact record.")
        except (UnicodeDecodeError, json.JSONDecodeError):
            issues.append("Bundle JSON is not parseable.")
    if not manifest_exists:
        issues.append("Manifest file is missing.")
    else:
        manifest_hash_matches = _sha256_bytes(manifest_path.read_bytes()) == artifact.manifest_sha256
        if not manifest_hash_matches:
            issues.append("Manifest SHA-256 does not match artifact record.")
    verified = bundle_exists and manifest_exists and bundle_hash_matches and manifest_hash_matches and bundle_parseable
    return ReleaseEvidenceArtifactVerification(
        verification_version="release-evidence-artifact-verification.v0.30",
        artifact_id=artifact.artifact_id,
        verified_at=now_iso(),
        bundle_file_exists=bundle_exists,
        manifest_file_exists=manifest_exists,
        bundle_sha256_matches=bundle_hash_matches,
        manifest_sha256_matches=manifest_hash_matches,
        bundle_json_parseable=bundle_parseable,
        verified=verified,
        issues=issues,
        live_trading_blocked=True,
    )


def _executor_handoff_contract() -> dict[str, object]:
    return {
        "contract_version": "openalgo-executor-handoff-contract.v0.50",
        "format": "json",
        "handoff_file": "package.json",
        "manifest_file": "manifest.json",
        "producer": "Trade Vision research-only API",
        "consumer": "external OpenAlgo/trading-bot adapter",
        "required_top_level_fields": [
            "intent",
            "verification",
            "executor_required_checks",
            "rejection_examples",
            "dry_run_only",
            "broker_order_created",
            "order_routing_enabled",
            "live_trading_blocked",
        ],
        "external_executor_must_recheck": [
            "intent signature",
            "duplicate key",
            "valid_until expiry",
            "kill switch state",
            "human approval",
            "risk limits",
            "account state",
            "paper/live mode permission",
            "broker duplicate order state",
        ],
        "forbidden_trade_vision_fields": [
            "broker_api_key",
            "broker_access_token",
            "broker_session_cookie",
            "order_id",
            "exchange_order_id",
        ],
        "routing_policy": "Trade Vision produces a dry-run intent package only; the external executor must reject or review it and must not treat it as an order.",
    }


def _executor_required_checks() -> list[str]:
    return [
        "Verify package SHA-256 and manifest SHA-256 before parsing.",
        "Verify intent signature from canonical intent fields.",
        "Reject duplicate duplicate_key values.",
        "Reject expired valid_until values.",
        "Reject if kill_switch_state is not armed.",
        "Require human approval before any external paper/live action.",
        "Run external risk check and account-state check.",
        "Reject if package reports broker_order_created=true.",
        "Reject if order_routing_enabled=true inside Trade Vision.",
        "Reject if live_trading_blocked=false inside Trade Vision.",
    ]


def _executor_rejection_examples(intent: SignalIntentBundle) -> list[ExecutorRejectionExample]:
    return [
        ExecutorRejectionExample(
            case_id="OA-DRY-REJECT-EXPIRED",
            title="Expired intent must be rejected",
            mutated_fields={"valid_until": "2000-01-01T00:00:00+00:00", "expired": True},
            expected_rejection_reasons=["Intent is expired."],
            expected_executor_action="reject",
        ),
        ExecutorRejectionExample(
            case_id="OA-DRY-REJECT-DUPLICATE",
            title="Duplicate key must be rejected",
            mutated_fields={"seen_duplicate_keys": [intent.duplicate_key]},
            expected_rejection_reasons=["Duplicate intent key detected."],
            expected_executor_action="reject",
        ),
        ExecutorRejectionExample(
            case_id="OA-DRY-REJECT-TAMPERED-SIDE",
            title="Tampered side must fail signature verification",
            mutated_fields={"side": "LONG" if intent.side != "LONG" else "SHORT"},
            expected_rejection_reasons=["Intent signature is invalid."],
            expected_executor_action="reject",
        ),
        ExecutorRejectionExample(
            case_id="OA-DRY-REVIEW-MISSING-EXTERNAL-CHECKS",
            title="Missing external checks remain manual review only",
            mutated_fields={
                "external_human_approval_present": False,
                "external_risk_check_passed": False,
                "external_account_state_checked": False,
            },
            expected_rejection_reasons=[
                "External human approval is missing.",
                "External risk check is missing or failed.",
                "External account state was not checked.",
            ],
            expected_executor_action="manual_review_only",
        ),
    ]


def _build_openalgo_intent_and_verification(
    *,
    symbol: str,
    target_executor: str,
    seen_duplicate_keys: list[str],
    external_human_approval_present: bool,
    external_risk_check_passed: bool,
    external_account_state_checked: bool,
    valid_until_override: str | None = None,
    verified_at_override: str | None = None,
) -> tuple[SignalIntentBundle, BotHandoffVerificationReport]:
    comparison = _build_current_twin(symbol)
    valid_until = valid_until_override or (comparison.kronos.expiry.valid_until if comparison.kronos else now_iso())
    intent = build_signal_intent_preview(comparison=comparison, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH, valid_until=valid_until)
    verification = verify_bot_handoff_intent(
        BotHandoffVerificationRequest(
            intent=intent,
            seen_duplicate_keys=seen_duplicate_keys,
            target_executor=target_executor,  # type: ignore[arg-type]
            external_human_approval_present=external_human_approval_present,
            external_risk_check_passed=external_risk_check_passed,
            external_account_state_checked=external_account_state_checked,
        ),
        verified_at=verified_at_override,
    )
    return intent, verification


def _export_executor_dry_run_package(
    payload: ExecutorDryRunPackageRequest,
    *,
    created_at_override: str | None = None,
    valid_until_override: str | None = None,
    artifact_root: Path | None = None,
    package_id_salt: str | None = None,
) -> ExecutorDryRunPackage:
    normalized = _normalize_symbol(payload.symbol)
    created_at = created_at_override or now_iso()
    intent, verification = _build_openalgo_intent_and_verification(
        symbol=normalized,
        target_executor=payload.target_executor,
        seen_duplicate_keys=payload.seen_duplicate_keys,
        external_human_approval_present=payload.external_human_approval_present,
        external_risk_check_passed=payload.external_risk_check_passed,
        external_account_state_checked=payload.external_account_state_checked,
        valid_until_override=valid_until_override,
        verified_at_override=created_at_override,
    )
    contract = _executor_handoff_contract()
    required_checks = _executor_required_checks()
    rejection_examples = _executor_rejection_examples(intent) if payload.include_rejection_examples else []
    package_seed = {
        "symbol": normalized,
        "target_executor": payload.target_executor,
        "intent_id": intent.intent_id,
        "verification_hash": verification.verification_hash,
        "requested_by": payload.requested_by,
        "created_at": created_at,
        "package_id_salt": package_id_salt,
    }
    package_id = str(uuid5(NAMESPACE_URL, f"tradevision:executor-dry-run:{json.dumps(package_seed, sort_keys=True)}"))
    dry_run_root = artifact_root or _runtime_artifact_dir(EXECUTOR_DRY_RUN_DIR, "TRADEVISION_EXECUTOR_DRY_RUN_DIR")
    artifact_dir = dry_run_root / _safe_id(normalized) / package_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    package_path = artifact_dir / "package.json"
    manifest_path = artifact_dir / "manifest.json"
    package_payload = {
        "package_version": "openalgo-executor-dry-run-package.v0.50",
        "package_id": package_id,
        "created_at": created_at,
        "symbol": normalized,
        "target_executor": payload.target_executor,
        "requested_by": payload.requested_by,
        "intent": intent.model_dump(mode="json"),
        "verification": verification.model_dump(mode="json"),
        "handoff_contract": contract,
        "executor_required_checks": required_checks,
        "rejection_examples": [item.model_dump(mode="json") for item in rejection_examples],
        "dry_run_only": True,
        "broker_credentials_present": False,
        "broker_order_created": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    package_sha, package_size = _write_json_file(package_path, package_payload)
    manifest_payload = {
        "manifest_version": "openalgo-executor-dry-run-manifest.v0.50",
        "package_id": package_id,
        "created_at": created_at,
        "symbol": normalized,
        "target_executor": payload.target_executor,
        "package_file": "package.json",
        "package_sha256": package_sha,
        "package_size_bytes": package_size,
        "retention_days": payload.retention_days,
        "dry_run_only": True,
        "contains_broker_credentials": False,
        "contains_broker_orders": False,
        "live_trading_blocked": True,
    }
    manifest_sha, manifest_size = _write_json_file(manifest_path, manifest_payload)
    package_hash = hashlib.sha256(f"{package_sha}:{manifest_sha}:{package_id}".encode("utf-8")).hexdigest()
    return ExecutorDryRunPackage(
        package_version="openalgo-executor-dry-run-package.v0.50",
        package_id=package_id,
        created_at=created_at,
        symbol=normalized,
        target_executor=payload.target_executor,
        requested_by=payload.requested_by,
        intent=intent,
        verification=verification,
        handoff_contract=contract,
        executor_required_checks=required_checks,
        rejection_examples=rejection_examples,
        artifact_dir=str(artifact_dir),
        package_file_path=str(package_path),
        manifest_file_path=str(manifest_path),
        package_sha256=package_sha,
        manifest_sha256=manifest_sha,
        package_size_bytes=package_size,
        manifest_size_bytes=manifest_size,
        package_hash=package_hash,
        dry_run_only=True,
        broker_credentials_present=False,
        broker_order_created=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "v0.50 exports an executor dry-run package only.",
            "The package is for external OpenAlgo/trading-bot adapter testing and must not be treated as an order.",
            "Trade Vision remains brokerless and cannot route this package to an exchange.",
        ],
    )


def _verify_executor_dry_run_package(package: ExecutorDryRunPackage) -> ExecutorDryRunPackageVerification:
    issues: list[str] = []
    package_path = Path(package.package_file_path)
    manifest_path = Path(package.manifest_file_path)
    package_exists = package_path.exists()
    manifest_exists = manifest_path.exists()
    package_hash_matches = False
    manifest_hash_matches = False
    package_parseable = False
    if not package_exists:
        issues.append("Dry-run package file is missing.")
    else:
        package_bytes = package_path.read_bytes()
        package_hash_matches = _sha256_bytes(package_bytes) == package.package_sha256
        if not package_hash_matches:
            issues.append("Dry-run package SHA-256 does not match response.")
        try:
            parsed = json.loads(package_bytes.decode("utf-8"))
            package_parseable = parsed.get("package_id") == package.package_id
            if not package_parseable:
                issues.append("Dry-run package JSON is parseable but package_id does not match response.")
            if parsed.get("broker_order_created") is not False or parsed.get("order_routing_enabled") is not False:
                issues.append("Dry-run package reports unsafe order/routing flags.")
        except (UnicodeDecodeError, json.JSONDecodeError):
            issues.append("Dry-run package JSON is not parseable.")
    if not manifest_exists:
        issues.append("Dry-run manifest file is missing.")
    else:
        manifest_hash_matches = _sha256_bytes(manifest_path.read_bytes()) == package.manifest_sha256
        if not manifest_hash_matches:
            issues.append("Dry-run manifest SHA-256 does not match response.")
    verified = package_exists and manifest_exists and package_hash_matches and manifest_hash_matches and package_parseable and not issues
    return ExecutorDryRunPackageVerification(
        verification_version="openalgo-executor-dry-run-verification.v0.50",
        package_id=package.package_id,
        verified_at=now_iso(),
        package_file_exists=package_exists,
        manifest_file_exists=manifest_exists,
        package_sha256_matches=package_hash_matches,
        manifest_sha256_matches=manifest_hash_matches,
        package_json_parseable=package_parseable,
        verified=verified,
        issues=issues,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
    )


def _build_executor_golden_fixtures() -> ExecutorGoldenFixtureRegistry:
    common = {
        "symbol": "NIFTY-MOCK",
        "target_executor": "openalgo",
        "requested_by": "golden_fixture_builder",
        "include_rejection_examples": True,
        "retention_days": 365,
    }
    duplicate_source_intent, _ = _build_openalgo_intent_and_verification(
        symbol="NIFTY-MOCK",
        target_executor="openalgo",
        seen_duplicate_keys=[],
        external_human_approval_present=True,
        external_risk_check_passed=True,
        external_account_state_checked=True,
        valid_until_override=EXECUTOR_GOLDEN_VALID_UNTIL,
        verified_at_override=EXECUTOR_GOLDEN_CREATED_AT,
    )
    scenarios = [
        (
            "executor-golden-accepted-review",
            "accepted_for_review",
            ExecutorDryRunPackageRequest(
                **common,
                external_human_approval_present=True,
                external_risk_check_passed=True,
                external_account_state_checked=True,
            ),
            EXECUTOR_GOLDEN_VALID_UNTIL,
            True,
            False,
            [],
        ),
        (
            "executor-golden-missing-external-checks",
            "missing_external_checks",
            ExecutorDryRunPackageRequest(**common),
            EXECUTOR_GOLDEN_VALID_UNTIL,
            False,
            True,
            [
                "External human approval is missing.",
                "External risk check is missing or failed.",
                "External account state was not checked.",
            ],
        ),
        (
            "executor-golden-duplicate-intent",
            "duplicate_intent",
            ExecutorDryRunPackageRequest(
                **common,
                seen_duplicate_keys=[duplicate_source_intent.duplicate_key],
                external_human_approval_present=True,
                external_risk_check_passed=True,
                external_account_state_checked=True,
            ),
            EXECUTOR_GOLDEN_VALID_UNTIL,
            False,
            True,
            ["Duplicate intent key detected."],
        ),
        (
            "executor-golden-expired-intent",
            "expired_intent",
            ExecutorDryRunPackageRequest(
                **common,
                external_human_approval_present=True,
                external_risk_check_passed=True,
                external_account_state_checked=True,
            ),
            EXECUTOR_GOLDEN_EXPIRED_AT,
            False,
            True,
            ["Intent is expired."],
        ),
    ]
    fixtures: list[ExecutorGoldenFixture] = []
    for fixture_id, scenario, request, valid_until, accepted, rejected, expected_reasons in scenarios:
        package = _export_executor_dry_run_package(
            request,
            created_at_override=EXECUTOR_GOLDEN_CREATED_AT,
            valid_until_override=valid_until,
            artifact_root=_runtime_artifact_dir(EXECUTOR_GOLDEN_FIXTURE_DIR, "TRADEVISION_EXECUTOR_GOLDEN_FIXTURE_DIR") / fixture_id,
            package_id_salt=fixture_id,
        )
        fixtures.append(
            ExecutorGoldenFixture(
                fixture_version="openalgo-executor-golden-fixture.v0.51",
                fixture_id=fixture_id,
                scenario=scenario,  # type: ignore[arg-type]
                expected_accepted_for_external_review=accepted,
                expected_rejected=rejected,
                expected_rejection_reasons=expected_reasons,
                package=package,
                expected_package_sha256=package.package_sha256,
                expected_manifest_sha256=package.manifest_sha256,
                expected_package_hash=package.package_hash,
                deterministic=True,
                broker_order_created=False,
                order_routing_enabled=False,
                live_trading_blocked=True,
            )
        )
    fixture_hashes = {fixture.fixture_id: fixture.expected_package_hash for fixture in fixtures}
    registry_payload = {
        "registry_version": "openalgo-executor-golden-registry.v0.51",
        "generated_at": EXECUTOR_GOLDEN_CREATED_AT,
        "fixture_hashes": fixture_hashes,
    }
    registry_hash = hashlib.sha256(json.dumps(registry_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return ExecutorGoldenFixtureRegistry(
        registry_version="openalgo-executor-golden-registry.v0.51",
        generated_at=EXECUTOR_GOLDEN_CREATED_AT,
        fixture_count=len(fixtures),
        fixtures=fixtures,
        fixture_hashes=fixture_hashes,
        registry_hash=registry_hash,
        deterministic=True,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
    )


def _verify_executor_golden_fixture(fixture: ExecutorGoldenFixture) -> ExecutorGoldenFixtureVerification:
    package_verification = _verify_executor_dry_run_package(fixture.package)
    acceptance_matches = (
        fixture.package.verification.accepted_for_external_review
        == fixture.expected_accepted_for_external_review
        and fixture.package.verification.rejected == fixture.expected_rejected
    )
    rejection_reasons_match = fixture.package.verification.rejection_reasons == fixture.expected_rejection_reasons
    package_hash_matches = (
        fixture.package.package_sha256 == fixture.expected_package_sha256
        and fixture.package.manifest_sha256 == fixture.expected_manifest_sha256
        and fixture.package.package_hash == fixture.expected_package_hash
    )
    safety_invariants_match = (
        fixture.package.dry_run_only
        and not fixture.package.broker_credentials_present
        and not fixture.package.broker_order_created
        and not fixture.package.trade_allowed
        and not fixture.package.order_routing_enabled
        and fixture.package.live_trading_blocked
    )
    issues: list[str] = []
    if not package_verification.verified:
        issues.extend(package_verification.issues)
    if not acceptance_matches:
        issues.append("Fixture acceptance/rejection result does not match its expected outcome.")
    if not rejection_reasons_match:
        issues.append("Fixture rejection reasons do not exactly match the expected registry.")
    if not package_hash_matches:
        issues.append("Fixture package or manifest hash does not match the golden registry.")
    if not safety_invariants_match:
        issues.append("Fixture safety invariants are not locked.")
    return ExecutorGoldenFixtureVerification(
        verification_version="openalgo-executor-golden-verification.v0.51",
        fixture_id=fixture.fixture_id,
        verified_at=now_iso(),
        package_verification=package_verification,
        acceptance_matches=acceptance_matches,
        rejection_reasons_match=rejection_reasons_match,
        package_hash_matches=package_hash_matches,
        safety_invariants_match=safety_invariants_match,
        passed=not issues,
        issues=issues,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
    )


def _reference_executor_conformance_request() -> ExecutorAdapterConformanceRequest:
    registry = _build_executor_golden_fixtures()
    return ExecutorAdapterConformanceRequest(
        adapter_name="trade-vision-reference-adapter",
        adapter_version="reference.v0.52",
        registry_hash=registry.registry_hash,
        observed_results=[
            ExecutorAdapterObservedResult(
                fixture_id=fixture.fixture_id,
                accepted_for_external_review=fixture.package.verification.accepted_for_external_review,
                rejected=fixture.package.verification.rejected,
                rejection_reasons=fixture.package.verification.rejection_reasons,
                broker_credentials_present=False,
                broker_order_created=False,
                order_routing_enabled=False,
                live_trading_blocked=True,
            )
            for fixture in registry.fixtures
        ],
    )


def _evaluate_executor_adapter_conformance(
    request: ExecutorAdapterConformanceRequest,
) -> ExecutorAdapterConformanceReport:
    registry = _build_executor_golden_fixtures()
    expected = {fixture.fixture_id: fixture for fixture in registry.fixtures}
    observed_counts: dict[str, int] = {}
    for item in request.observed_results:
        observed_counts[item.fixture_id] = observed_counts.get(item.fixture_id, 0) + 1
    duplicates = sorted(fixture_id for fixture_id, count in observed_counts.items() if count > 1)
    observed = {item.fixture_id: item for item in request.observed_results}
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    cases: list[ExecutorAdapterConformanceCase] = []
    for fixture_id, fixture in expected.items():
        actual = observed.get(fixture_id)
        if actual is None:
            continue
        outcome_matches = (
            actual.accepted_for_external_review == fixture.expected_accepted_for_external_review
            and actual.rejected == fixture.expected_rejected
        )
        rejection_reasons_match = actual.rejection_reasons == fixture.expected_rejection_reasons
        safety_invariants_match = (
            not actual.broker_credentials_present
            and not actual.broker_order_created
            and not actual.order_routing_enabled
            and actual.live_trading_blocked
        )
        issues: list[str] = []
        if not outcome_matches:
            issues.append("Observed acceptance/rejection does not match the golden fixture.")
        if not rejection_reasons_match:
            issues.append("Observed rejection reasons do not exactly match the golden fixture.")
        if not safety_invariants_match:
            issues.append("Adapter reported broker credentials, order creation, routing, or an unlocked live state.")
        if fixture_id in duplicates:
            issues.append("Adapter returned the fixture more than once.")
        cases.append(
            ExecutorAdapterConformanceCase(
                fixture_id=fixture_id,
                expected_accepted_for_external_review=fixture.expected_accepted_for_external_review,
                observed_accepted_for_external_review=actual.accepted_for_external_review,
                expected_rejected=fixture.expected_rejected,
                observed_rejected=actual.rejected,
                expected_rejection_reasons=fixture.expected_rejection_reasons,
                observed_rejection_reasons=actual.rejection_reasons,
                outcome_matches=outcome_matches,
                rejection_reasons_match=rejection_reasons_match,
                safety_invariants_match=safety_invariants_match,
                passed=not issues,
                issues=issues,
            )
        )
    registry_hash_matches = request.registry_hash == registry.registry_hash
    passed_count = sum(case.passed for case in cases)
    all_passed = (
        registry_hash_matches
        and not missing
        and not unexpected
        and not duplicates
        and len(cases) == registry.fixture_count
        and passed_count == registry.fixture_count
    )
    report_payload = {
        "conformance_version": "openalgo-executor-adapter-conformance.v0.52",
        "adapter_name": request.adapter_name,
        "adapter_version": request.adapter_version,
        "registry_hash": request.registry_hash,
        "registry_hash_matches": registry_hash_matches,
        "missing_fixture_ids": missing,
        "unexpected_fixture_ids": unexpected,
        "duplicate_fixture_ids": duplicates,
        "cases": [case.model_dump(mode="json") for case in cases],
        "all_passed": all_passed,
    }
    report_hash = hashlib.sha256(json.dumps(report_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return ExecutorAdapterConformanceReport(
        conformance_version="openalgo-executor-adapter-conformance.v0.52",
        evaluated_at=now_iso(),
        adapter_name=request.adapter_name,
        adapter_version=request.adapter_version,
        registry_hash=request.registry_hash,
        registry_hash_matches=registry_hash_matches,
        expected_fixture_count=registry.fixture_count,
        observed_fixture_count=len(request.observed_results),
        passed_count=passed_count,
        all_passed=all_passed,
        missing_fixture_ids=missing,
        unexpected_fixture_ids=unexpected,
        duplicate_fixture_ids=duplicates,
        cases=cases,
        report_hash=report_hash,
        signature_algorithm="sha256-canonical-json-integrity-only",
        promotion_allowed=False,
        broker_credentials_present=any(item.broker_credentials_present for item in request.observed_results),
        broker_order_created=any(item.broker_order_created for item in request.observed_results),
        order_routing_enabled=any(item.order_routing_enabled for item in request.observed_results),
        live_trading_blocked=True,
        notes=[
            "v0.52 evaluates an adapter response against the v0.51 golden fixture registry.",
            "The report hash is an integrity checksum, not an authentication signature.",
            "Passing conformance does not enable broker routing or promote the adapter.",
        ],
    )


def _ensure_golden_replay_fixtures() -> None:
    for scenario_id, seed, count in [
        ("golden_opening_drive", 42, 12),
        ("golden_fakeout_reversal", 77, 12),
        ("golden_lunch_compression", 91, 12),
        ("golden_closing_drive", 108, 12),
        ("golden_gap_trap", 123, 12),
        ("golden_expiry_pin", 155, 12),
        ("golden_9c_clean_breakout", 201, 12),
        ("golden_9c_fake_breakout", 202, 12),
        ("golden_9c_vwap_rejection", 203, 12),
        ("golden_9c_choppy", 204, 12),
        ("golden_9c_gap_up_continuation", 205, 12),
        ("golden_9c_low_volume", 206, 12),
        ("golden_9c_htf_lookahead_trap", 207, 12),
        ("golden_9c_near_confluence_support", 208, 12),
        ("golden_9c_near_confluence_resistance", 209, 12),
        ("golden_9c_ood_unknown", 210, 12),
    ]:
        fixture_id = f"golden-nifty-mock-{scenario_id.replace('_', '-')}-{seed}"
        if storage.load_golden_replay_fixture(fixture_id):
            continue
        events = deterministic_events(seed, scenario_id, count)
        fixture = build_golden_replay_fixture(
            symbol="NIFTY-MOCK",
            scenario_id=scenario_id,
            seed=seed,
            events=events,
        )
        storage.save_golden_replay_fixture(fixture)


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def _behavior_run_id(symbol: str, timeframe: str, seed: int) -> str:
    return f"behavior-{_safe_id(_normalize_symbol(symbol))}-{_safe_id(timeframe)}-{seed}"


def _benchmark_run_id(symbol: str, timeframe: str, seed: int) -> str:
    return f"benchmark-{_safe_id(_normalize_symbol(symbol))}-{_safe_id(timeframe)}-{seed}"


def _build_stock_memory_profile(symbol: str, timeframe: str, seed: int):
    normalized = _normalize_symbol(symbol)
    profile, memory, _ = _ensure_behavior_seed_data(normalized)
    pattern_request = _default_pattern_memory_request(normalized)
    pattern = analyze_pattern_memory(pattern_request, memory)
    for match in pattern.matches:
        storage.save_similar_day_match(match)
    rhythm = analyze_session_rhythm(SessionRhythmRequest(series=pattern_request.series, decision_time_ns=pattern_request.decision_time_ns))
    stock_summary = build_stock_dna_summary(stock_dna=profile, rhythm=rhythm, memory=memory)
    for session_profile in stock_summary.session_memory:
        storage.save_session_memory_profile(session_profile)
    outcomes = storage.list_outcome_labels(normalized)
    if not outcomes:
        default_outcome = label_trade_outcome(_default_outcome_label_request(normalized))
        storage.save_outcome_label(default_outcome)
        outcomes = [default_outcome]
    failure_library = build_failure_library(normalized, memory, outcomes)
    for failure in failure_library.failures:
        storage.save_failure_pattern(failure)
    trust = build_learning_trust(normalized, memory, outcomes)
    for record in trust.records:
        storage.save_learning_trust_record(record)
    snapshots = [item for item in storage.list_point_in_time_snapshots(limit=200) if item.symbol == normalized]
    report = build_stock_memory_profile_report(
        symbol=normalized,
        timeframe=timeframe,
        snapshot_count=len(snapshots),
        stock_dna_summary=stock_summary,
        pattern_memory=pattern,
        failure_library=failure_library,
        trust_table=trust,
    )
    audit("warning" if not report.minimum_sample_pass else "info", f"Stock memory profile generated for {normalized}: min_sample={report.minimum_sample_pass}", "behavior_memory")
    return report


def _default_kronos_series(symbol: str, timeframe: str = "5m", bars: int = 64) -> CandleSeries:
    normalized = _normalize_symbol(symbol)
    step = {
        "1m": 60_000_000_000,
        "3m": 180_000_000_000,
        "5m": 300_000_000_000,
        "15m": 900_000_000_000,
        "1H": 3_600_000_000_000,
    }.get(timeframe, 300_000_000_000)
    base = TIME_STATE.virtual_timestamp_ns - max(bars, 16) * step
    price = 100.0
    candle_bars: list[CandleBar] = []
    for idx in range(max(bars, 16)):
        drift = (idx % 11 - 5) * 0.015 + idx * 0.004
        open_price = price
        close = max(1.0, open_price + drift)
        high = max(open_price, close) + 0.42 + (idx % 3) * 0.03
        low = min(open_price, close) - 0.36 - (idx % 4) * 0.02
        candle_bars.append(
            CandleBar(
                symbol=normalized,
                timeframe=timeframe,  # type: ignore[arg-type]
                timestamp_ns=base + idx * step,
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=1_000 + idx * 17 + (idx % 5) * 50,
                source="mock",
                sequence_number=idx + 1,
            )
        )
        price = close
    return CandleSeries(
        symbol=normalized,
        timeframe=timeframe,  # type: ignore[arg-type]
        bars=candle_bars,
        snapshot_id=f"{normalized}-kronos-default",
        schema_version="candles.kronos.mock.v1",
    )


def _build_current_twin(symbol: str):
    behavior = evaluate_trade_decision(_default_behavior_decision_request(symbol))
    kronos = build_kronos_forecast_with_optional_service(KronosForecastRequest(symbol=symbol, timeframe="5m", seed=42), _default_kronos_series(symbol, "5m", 64))
    return build_twin_engine_comparison(symbol=symbol, behavior=behavior, kronos=kronos)


def _default_full_twin_behavior(payload: FullTwinAnalysisRequest):
    behavior = evaluate_trade_decision(_default_behavior_decision_request(payload.symbol))
    if payload.force_behavior_no_trade:
        no_trade = behavior.no_trade.model_copy(
            update={
                "active": True,
                "no_trade_reason": "Forced no-trade diagnostic: Behavior authority must not be overridden by Kronos.",
                "blocking_gates": list(dict.fromkeys(behavior.no_trade.blocking_gates + ["FORCED_NO_TRADE"])),
            }
        )
        return behavior.model_copy(
            update={
                "final_trade_decision": "NO_TRADE",
                "trade_allowed": False,
                "universal_agreement_pass": False,
                "confidence_pct": min(behavior.confidence_pct, 20.0),
                "no_trade": no_trade,
            }
        )
    no_trade = behavior.no_trade.model_copy(
        update={
            "active": False,
            "no_trade_reason": None,
            "blocking_gates": [],
            "wait_for": [],
        }
    )
    candidate_gates = [
        gate.model_copy(update={"passed": True, "severity": "info", "reason": f"v0.67 research candidate diagnostic passed: {gate.gate}."})
        for gate in behavior.gates
    ]
    return behavior.model_copy(
        update={
            "final_trade_decision": "BUY_BREAKOUT",
            "trade_allowed": True,
            "universal_agreement_pass": True,
            "confidence_pct": max(behavior.confidence_pct, 64.0),
            "agreement_checks": {key: True for key in behavior.agreement_checks},
            "gates": candidate_gates,
            "no_trade": no_trade,
            "narrative_explanation": behavior.narrative_explanation + " v0.67 diagnostic permits research comparison only.",
        }
    )


def _default_pattern_memory_request(symbol: str) -> PatternMemoryRequest:
    normalized = _normalize_symbol(symbol)
    base = TIME_STATE.virtual_timestamp_ns
    five = 300_000_000_000
    template = [
        (100.0, 101.0, 99.8, 100.7, 1200.0),
        (100.7, 101.8, 100.4, 101.5, 1500.0),
        (101.5, 102.5, 101.1, 102.2, 1900.0),
        (102.2, 103.0, 101.8, 102.4, 2400.0),
        (102.4, 103.2, 101.9, 102.1, 2600.0),
        (102.1, 102.9, 101.6, 101.9, 2300.0),
        (101.9, 102.4, 101.2, 101.5, 1800.0),
        (101.5, 102.0, 101.0, 101.6, 1600.0),
    ]
    bars = [
        CandleBar(
            symbol=normalized,
            timeframe="5m",
            timestamp_ns=base + idx * five,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source="mock",
            sequence_number=idx + 1,
        )
        for idx, (open_price, high, low, close, volume) in enumerate(template)
    ]
    return PatternMemoryRequest(
        series=CandleSeries(
            symbol=normalized,
            timeframe="5m",
            bars=bars,
            snapshot_id=f"{normalized}-pattern-memory-default",
            schema_version="candles.v1",
        ),
        previous_close=99.6,
        decision_time_ns=bars[-1].timestamp_ns,
        minimum_sample_size=30,
        max_matches=5,
        timezone_offset_minutes=330,
    )


def _default_outcome_label_request(symbol: str) -> OutcomeLabelRequest:
    normalized = _normalize_symbol(symbol)
    base = TIME_STATE.virtual_timestamp_ns
    five = 300_000_000_000
    template = [
        (100.0, 100.8, 99.7, 100.4, 1200.0),
        (100.4, 101.2, 100.1, 101.0, 1500.0),
        (101.0, 101.8, 100.7, 101.6, 1800.0),
        (101.6, 102.6, 101.4, 102.2, 2400.0),
        (102.2, 103.2, 102.0, 103.0, 2900.0),
    ]
    bars = [
        CandleBar(
            symbol=normalized,
            timeframe="5m",
            timestamp_ns=base + idx * five,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source="mock",
            sequence_number=idx + 1,
        )
        for idx, (open_price, high, low, close, volume) in enumerate(template)
    ]
    return OutcomeLabelRequest(
        series=CandleSeries(
            symbol=normalized,
            timeframe="5m",
            bars=bars,
            snapshot_id=f"{normalized}-outcome-default",
            schema_version="candles.v1",
        ),
        direction="long",
        entry_price=100.4,
        stop_loss=99.4,
        target=103.0,
        entry_timestamp_ns=bars[0].timestamp_ns,
        max_holding_bars=24,
        pattern_id="open_drive_vwap_support",
        run_id=f"outcome-{normalized}-mock-default",
    )


def _default_conservative_outcome_label_request(symbol: str) -> ConservativeOutcomeLabelRequest:
    normalized = _normalize_symbol(symbol)
    base = TIME_STATE.virtual_timestamp_ns
    five = 300_000_000_000
    template = [
        (100.0, 100.9, 99.8, 100.5, 1200.0),
        (100.5, 101.4, 100.3, 101.1, 1550.0),
        (101.1, 102.1, 100.8, 101.8, 1900.0),
        (101.8, 103.3, 101.5, 102.9, 2500.0),
        (102.9, 103.6, 102.3, 103.2, 2300.0),
    ]
    bars = [
        CandleBar(
            symbol=normalized,
            timeframe="5m",
            timestamp_ns=base + idx * five,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source="mock",
            sequence_number=idx + 1,
        )
        for idx, (open_price, high, low, close, volume) in enumerate(template)
    ]
    return ConservativeOutcomeLabelRequest(
        series=CandleSeries(
            symbol=normalized,
            timeframe="5m",
            bars=bars,
            snapshot_id=f"{normalized}-conservative-outcome-default",
            schema_version="candles.v1",
        ),
        direction="long",
        entry_price=100.5,
        stop_price=99.4,
        target_price=103.0,
        entry_time_ns=bars[0].timestamp_ns,
        order_type="market_order",
        quantity=1.0,
        atr=1.1,
        max_holding_bars=24,
        has_lower_timeframe_sequence=False,
        pattern_id="open_drive_vwap_support",
        run_id=f"conservative-outcome-{normalized}-mock-default",
    )


def _default_behavior_decision_request(symbol: str) -> BehaviorDecisionRequest:
    normalized = _normalize_symbol(symbol)
    _, memory, _ = _ensure_behavior_seed_data(normalized)
    pattern = analyze_pattern_memory(_default_pattern_memory_request(normalized), memory)
    outcomes = storage.list_outcome_labels(normalized)
    if not outcomes:
        default_outcome = label_trade_outcome(_default_outcome_label_request(normalized))
        storage.save_outcome_label(default_outcome)
        outcomes = [default_outcome]
    trust = build_learning_trust(normalized, memory, outcomes)
    library = build_failure_library(normalized, memory, outcomes)
    return BehaviorDecisionRequest(
        symbol=normalized,
        rule_signal="BUY_BREAKOUT",
        direction="long",
        data_quality_score=0.98,
        liquidity_score=0.73,
        context_bias="supports_long",
        context_blocks_trade=False,
        session_trade_quality_score=0.62,
        session_blocks_trade=False,
        similar_history_continuation_pct=pattern.continuation_probability_pct,
        similar_history_fakeout_pct=pattern.fakeout_probability_pct,
        pattern_minimum_sample_pass=pattern.minimum_sample_pass,
        trust_minimum_sample_pass=trust.minimum_sample_pass,
        trust_score=trust.aggregate_trust_score,
        failure_warning=(
            f"Failure memory warns: {library.most_common_failure}"
            if library.most_common_failure
            else None
        ),
        market_regime_favorable=True,
        relative_strength_supports=True,
        risk_reward=2.1,
        daily_loss_limit_hit=False,
        cooldown_active=False,
        kill_switch_active=KILL_SWITCH.blocks_order_paths,
        ood_score=0.18,
        drift_score=0.12,
        replay_snapshot_id=pattern.matches[0].similar_day_id if pattern.matches else None,
    )


def _default_behavior_risk_request(symbol: str, decision: str, confidence_pct: float) -> BehaviorRiskRequest:
    normalized = _normalize_symbol(symbol)
    return BehaviorRiskRequest(
        symbol=normalized,
        decision=decision,  # type: ignore[arg-type]
        account_equity=1_000_000.0,
        entry_price=101.6,
        stop_loss=99.6,
        target=107.6,
        confidence_pct=confidence_pct,
        liquidity_score=0.73,
        slippage_risk_pct=0.08,
        sector="IT",
        index="NIFTY",
        current_sector_exposure_pct=2.0,
        current_index_exposure_pct=3.0,
        correlation_risk="medium",
        daily_pnl=0.0,
        consecutive_losses=0,
        choppy_regime=False,
        max_risk_per_trade_pct=0.5,
        max_daily_loss_pct=2.0,
        max_portfolio_heat_pct=8.0,
        max_sector_exposure_pct=25.0,
        max_index_exposure_pct=40.0,
        cooldown_after_n_losses=3,
        cooldown_minutes=30,
    )


def _default_behavior_execution_request(symbol: str, requested_quantity: int) -> BehaviorExecutionRequest:
    normalized = _normalize_symbol(symbol)
    return BehaviorExecutionRequest(
        symbol=normalized,
        side="BUY",
        order_type="MARKET",
        requested_quantity=requested_quantity,
        entry_price=101.6,
        bar_open=101.4,
        bar_high=102.2,
        bar_low=101.0,
        bar_close=101.9,
        bid_ask_spread_pct=0.08,
        available_volume=80_000,
        queue_ahead_quantity=2_000,
        latency_ms=120,
        impact_coefficient_bps=4.0,
        adverse_selection_score=0.28,
        max_participation_rate=0.08,
        mode_confirmation="MOCK_ONLY",
        seed=42,
    )


def _ensure_behavior_seed_data(symbol: str) -> tuple[StockDNAProfile, list[BehaviorMemoryRecord], list[SimilarDayMatch]]:
    normalized = _normalize_symbol(symbol)
    profile = storage.load_stock_dna_profile(normalized)
    if profile is None:
        profile = StockDNAProfile(
            symbol=normalized,
            profile_version="stock-dna.mock.v0.12",
            updated_at=now_iso(),
            source="mock",
            usual_open_behavior="opening-drive attempt followed by VWAP confirmation requirement",
            usual_midday_behavior="lower-quality lunch compression with reduced continuation edge",
            usual_closing_behavior="closing drive only trusted when index and sector agree",
            best_trade_window="09:30-10:15",
            worst_trade_window="11:30-13:30",
            fakeout_window="10:15-11:30",
            continuation_window="13:30-14:30",
            level_respect_summary={
                "VWAP": 0.69,
                "PDH": 0.61,
                "PDL": 0.58,
                "CPR": 0.64,
                "ORB": 0.66,
            },
            notes=[
                "Mock Stock DNA is seeded for contract and UI integration only.",
                "Real promotion requires point-in-time OHLCV, outcome labels, and walk-forward validation.",
            ],
        )
        storage.save_stock_dna_profile(profile)

    if not storage.list_behavior_memory(normalized, limit=1):
        records = [
            BehaviorMemoryRecord(
                memory_id=f"{normalized}-memory-vwap-fakeout",
                symbol=normalized,
                trade_date="2024-03-11",
                timeframe="5m",
                pattern_id="open_drive_vwap_retest",
                market_state="fake_breakout",
                session_phase="09:30-10:15 real_trend_confirmation",
                outcome_label="FAKE_BREAKOUT",
                similarity_group="prior_vwap_retest_fakeout_cluster",
                feature_snapshot={"rsi": 62, "adx": 31, "volume_z": 1.8, "vwap_state": "failed_reclaim"},
                reason="Breakout failed after upper wick rejection near VWAP.",
                model_version="behavior-contract-lock.v0.12",
            ),
            BehaviorMemoryRecord(
                memory_id=f"{normalized}-memory-continuation",
                symbol=normalized,
                trade_date="2024-04-08",
                timeframe="5m",
                pattern_id="open_drive_vwap_support",
                market_state="opening_drive_continuation",
                session_phase="09:30-10:15 real_trend_confirmation",
                outcome_label="TARGET_HIT",
                similarity_group="prior_open_drive_continuation_cluster",
                feature_snapshot={"rsi": 67, "adx": 34, "volume_z": 2.1, "vwap_state": "held_pullback"},
                reason="VWAP held on first pullback and index context stayed supportive.",
                model_version="behavior-contract-lock.v0.12",
            ),
            BehaviorMemoryRecord(
                memory_id=f"{normalized}-memory-lunch-chop",
                symbol=normalized,
                trade_date="2024-05-22",
                timeframe="5m",
                pattern_id="lunch_compression",
                market_state="choppy_avoid",
                session_phase="11:30-13:30 lunch_compression",
                outcome_label="CHOP_NO_FOLLOWTHROUGH",
                similarity_group="prior_lunch_chop_cluster",
                feature_snapshot={"rsi": 55, "adx": 18, "volume_z": -0.4, "vwap_state": "flat"},
                reason="Low-volume compression created repeated false starts.",
                model_version="behavior-contract-lock.v0.12",
            ),
        ]
        for record in records:
            storage.save_behavior_memory_record(record)

    if not storage.list_similar_day_matches(normalized, limit=1):
        matches = [
            SimilarDayMatch(
                match_id=f"{normalized}-similar-2024-03-11",
                symbol=normalized,
                similar_day_id="mock-day-2024-03-11",
                similarity_score_pct=81.0,
                outcome_label="FAKE_BREAKOUT",
                average_next_move_atr=-0.64,
                failure_reason="upper wick near resistance with low follow-through",
                replay_available=True,
            ),
            SimilarDayMatch(
                match_id=f"{normalized}-similar-2024-04-08",
                symbol=normalized,
                similar_day_id="mock-day-2024-04-08",
                similarity_score_pct=76.0,
                outcome_label="TARGET_HIT",
                average_next_move_atr=1.22,
                failure_reason=None,
                replay_available=True,
            ),
            SimilarDayMatch(
                match_id=f"{normalized}-similar-2024-05-22",
                symbol=normalized,
                similar_day_id="mock-day-2024-05-22",
                similarity_score_pct=73.0,
                outcome_label="CHOP_NO_FOLLOWTHROUGH",
                average_next_move_atr=-0.12,
                failure_reason="lunch compression and low participation",
                replay_available=True,
            ),
        ]
        for match in matches:
            storage.save_similar_day_match(match)

    return (
        storage.load_stock_dna_profile(normalized) or profile,
        storage.list_behavior_memory(normalized),
        storage.list_similar_day_matches(normalized),
    )


@app.get("/api/v1/behavior/spec")
async def behavior_spec():
    return envelope(
        BehaviorSpec(
            purpose=BEHAVIOR_CORE_PURPOSE,
            no_blind_prediction_rule=NO_BLIND_PREDICTION_RULE,
            universal_agreement_rule=UNIVERSAL_AGREEMENT_RULE,
            low_evidence_message=LOW_EVIDENCE_MESSAGE,
            narrative_explanation_only_invariant=NARRATIVE_EXPLANATION_ONLY_INVARIANT,
            layer_contracts=_behavior_layer_contracts(),
            output_columns=_behavior_output_columns(),
            verbatim_registry=VERBATIM_REGISTRY,
            live_trading_blocked=True,
            stock_app_source_root=r"D:\Projects\trading-platforms\stock-app",
        )
    )


@app.get("/api/v1/behavior/output-columns")
async def behavior_output_columns():
    return envelope(_behavior_output_columns())


@app.get("/api/v1/behavior/frontend/panel-map")
async def behavior_frontend_panel_map():
    return envelope(build_behavior_frontend_panel_map(CAPABILITIES))


@app.get("/api/v1/behavior/runtime/readiness")
async def behavior_runtime_readiness():
    return envelope(build_runtime_readiness_report(PROJECT_ROOT))


@app.get("/api/v1/behavior/indicators/registry")
async def behavior_indicator_registry():
    return envelope(build_indicator_registry_report())


@app.get("/api/v1/behavior/indicators/{indicator_id}/ontology")
async def behavior_indicator_ontology(indicator_id: str):
    registry = build_indicator_registry_report()
    entry = next((item for item in registry.entries if item.indicator_id == indicator_id), None)
    if entry is None:
        raise api_error(404, "indicator_not_found", f"Indicator {indicator_id} is not registered.")
    return envelope(entry, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/indicators/lag-vote")
async def behavior_indicator_lag_vote(payload: IndicatorLagVoteRequest):
    registry = build_indicator_registry_report()
    if not any(item.indicator_id == payload.indicator_id for item in registry.entries):
        raise api_error(404, "indicator_not_found", f"Indicator {payload.indicator_id} is not registered.")
    return envelope(build_indicator_lag_voting_report(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/indicators/reliability/label-signal")
async def behavior_indicator_signal_label(payload: IndicatorSignalOutcomeLabelRequest):
    registry = build_indicator_registry_report()
    if not any(item.indicator_id == payload.indicator_id for item in registry.entries):
        raise api_error(404, "indicator_not_found", f"Indicator {payload.indicator_id} is not registered.")
    return envelope(label_indicator_signal_outcome(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/indicators/reliability/save-history")
async def behavior_indicator_signal_history_save(payload: IndicatorSignalHistorySaveRequest):
    registry = build_indicator_registry_report()
    if not any(item.indicator_id == payload.indicator_id for item in registry.entries):
        raise api_error(404, "indicator_not_found", f"Indicator {payload.indicator_id} is not registered.")
    return envelope(save_indicator_signal_history(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/indicators/reliability/ingest-current")
async def behavior_indicator_signal_history_ingest_current(payload: IndicatorSignalHistoryIngestCurrentRequest):
    return envelope(ingest_current_indicator_signal_history(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/indicators/reliability/complete-pending")
async def behavior_indicator_signal_history_complete_pending(payload: IndicatorSignalHistoryCompletePendingRequest):
    registry = build_indicator_registry_report()
    if not any(item.indicator_id == payload.indicator_id for item in registry.entries):
        raise api_error(404, "indicator_not_found", f"Indicator {payload.indicator_id} is not registered.")
    return envelope(complete_pending_indicator_signal_history(payload), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/indicators/{indicator_id}/signal-history/{symbol}")
async def behavior_indicator_signal_history(indicator_id: str, symbol: str = "RELIANCE", timeframe: str = "1m", limit: int = 250):
    registry = build_indicator_registry_report()
    if not any(item.indicator_id == indicator_id for item in registry.entries):
        raise api_error(404, "indicator_not_found", f"Indicator {indicator_id} is not registered.")
    return envelope(
        build_indicator_signal_history_report(indicator_id=indicator_id, symbol=symbol, timeframe=timeframe, limit=limit),  # type: ignore[arg-type]
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}")
async def behavior_indicator_reliability(indicator_id: str, symbol: str = "RELIANCE", timeframe: str = "1m", low_sample: bool = False, ood: bool = False, regime_shift: bool = False):
    registry = build_indicator_registry_report()
    if not any(item.indicator_id == indicator_id for item in registry.entries):
        raise api_error(404, "indicator_not_found", f"Indicator {indicator_id} is not registered.")
    return envelope(
        build_indicator_reliability_report(
            indicator_id=indicator_id,
            symbol=symbol,
            timeframe=timeframe,  # type: ignore[arg-type]
            force_low_sample=low_sample,
            force_ood=ood,
            force_regime_shift=regime_shift,
        ),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/indicators/{indicator_id}/reliability-drilldown/{symbol}")
async def behavior_indicator_reliability_drilldown(indicator_id: str, symbol: str = "RELIANCE", timeframe: str = "1m", limit: int = 250):
    registry = build_indicator_registry_report()
    if not any(item.indicator_id == indicator_id for item in registry.entries):
        raise api_error(404, "indicator_not_found", f"Indicator {indicator_id} is not registered.")
    reliability = build_indicator_reliability_report(indicator_id=indicator_id, symbol=symbol, timeframe=timeframe)  # type: ignore[arg-type]
    history = build_indicator_signal_history_report(indicator_id=indicator_id, symbol=symbol, timeframe=timeframe, limit=limit)  # type: ignore[arg-type]
    return envelope(
        {
            "drilldown_version": "indicator-reliability-drilldown.v1.83",
            "symbol": symbol.upper(),
            "indicator_id": indicator_id,
            "timeframe": timeframe,
            "reliability": reliability.model_dump(mode="json"),
            "history": history.model_dump(mode="json"),
            "trader_summary": (
                f"{indicator_id} has {reliability.sample_count} counted samples for {symbol.upper()} {timeframe}; "
                f"state={reliability.reliability_state}; source={reliability.history_source}; "
                "it can reduce confidence but cannot approve trades."
            ),
            "used_for_probability": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/indicators/intelligence-summary/{symbol}")
async def behavior_indicator_intelligence_summary(symbol: str = "RELIANCE"):
    summary = build_indicator_intelligence_summary(symbol)
    sample_votes = summary.get("sample_votes", [])
    if sample_votes:
        indicator_id = str(sample_votes[0]["indicator_id"])
        reliability = build_indicator_reliability_report(indicator_id=indicator_id, symbol=symbol)
        summary["reliability_preview"] = {
            "reliability_version": reliability.reliability_version,
            "indicator_id": reliability.indicator_id,
            "sample_count": reliability.sample_count,
            "minimum_sample_pass": reliability.minimum_sample_pass,
            "per_stock_reliability": reliability.per_stock_reliability,
            "reliability_state": reliability.reliability_state,
            "used_for_probability": reliability.used_for_probability,
            "live_trading_blocked": reliability.live_trading_blocked,
        }
    return envelope(summary, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/9c-dna/build")
async def behavior_nine_candle_dna_build(payload: NineCandleBuildRequest):
    return envelope(build_nine_candle_dna(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/9c-dna/save-setup")
async def behavior_nine_candle_save_setup(payload: NineCandleSaveSetupRequest):
    return envelope(save_nine_candle_setup(payload), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/9c-dna/label-outcomes")
async def behavior_nine_candle_label_outcomes(payload: NineCandleOutcomeLabelRequest):
    return envelope(label_nine_candle_outcomes(payload), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/setup-memory/{symbol}")
async def behavior_nine_candle_setup_memory(symbol: str, timeframe: str = "1m", limit: int = 25):
    return envelope(build_nine_candle_setup_memory(symbol, timeframe, limit), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/current/{symbol}")
async def behavior_nine_candle_current(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_nine_candle_dna(NineCandleBuildRequest(symbol=symbol, timeframe=timeframe, use_real_indicators=use_real_indicators)),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/vector-audit/{symbol}")
async def behavior_nine_candle_vector_audit(
    symbol: str,
    timeframe: str = "1m",
    expected_feature_manifest_version: str = "nine-candle-feature-manifest.v1",
    use_real_indicators: bool = False,
):
    return envelope(
        build_nine_candle_feature_vector_audit(symbol, timeframe, expected_feature_manifest_version, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/analogs/{symbol}")
async def behavior_nine_candle_analogs(symbol: str, timeframe: str = "1m"):
    return envelope(build_nine_candle_analogs(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/evidence-packet/{symbol}")
async def behavior_nine_candle_evidence_packet(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(build_nine_candle_evidence_packet(symbol, timeframe, use_real_indicators), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/indicator-runtime/{symbol}")
async def behavior_nine_candle_indicator_runtime(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_indicator_runtime_report(symbol, timeframe, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/indicator-runtime-coverage")
async def behavior_nine_candle_indicator_runtime_coverage():
    return envelope(build_indicator_runtime_coverage_report(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/indicator-promotion/{symbol}")
async def behavior_nine_candle_indicator_promotion(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_indicator_promotion_report(symbol, timeframe, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/indicator-cache/save/{symbol}")
async def behavior_indicator_cache_save(
    symbol: str,
    timeframe: str = "1m",
    use_real_indicators: bool = False,
    force_recompute: bool = False,
    anomalous_snapshot: bool = False,
):
    return envelope(
        save_indicator_results(symbol, timeframe, use_real_indicators, force_recompute, anomalous_snapshot),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/indicator-cache/status/{symbol}")
async def behavior_indicator_cache_status(symbol: str, timeframe: str = "1m"):
    return envelope(indicator_cache_status(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/indicator-cache/results/{symbol}")
async def behavior_indicator_cache_results(symbol: str, timeframe: str = "1m", limit: int = 100):
    return envelope(indicator_cache_results(symbol, timeframe, limit), capability_status=CapabilityStatus.MOCK)


@app.delete("/api/v1/behavior/indicator-cache/{cache_id}")
async def behavior_indicator_cache_delete(cache_id: str):
    return envelope(delete_indicator_cache(cache_id), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/red-team/tv-prod-red-001")
async def behavior_red_team_tv_prod_red_001(symbol: str = "RELIANCE", timeframe: str = "1m"):
    return envelope(build_tv_prod_red_001_report(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/level-proximity/{symbol}")
async def behavior_nine_candle_level_proximity(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_level_proximity_report(symbol, timeframe, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/confluence/{symbol}")
async def behavior_nine_candle_level_confluence(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_level_confluence_report(symbol, timeframe, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/level-memory/{symbol}")
async def behavior_nine_candle_level_memory(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_level_memory_report(symbol, timeframe, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/regime/{symbol}")
async def behavior_nine_candle_regime(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_regime_gate_report(symbol, timeframe, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/hypotheses/{symbol}")
async def behavior_nine_candle_hypotheses(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(
        build_hypothesis_report(symbol, timeframe, use_real_indicators),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/path-analogs/{symbol}")
async def behavior_nine_candle_path_analogs(symbol: str, timeframe: str = "1m", limit: int = 25):
    return envelope(
        build_path_analog_report(symbol, timeframe, limit),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/ood-status/{symbol}")
async def behavior_nine_candle_ood_status(symbol: str, timeframe: str = "1m"):
    return envelope(
        build_ood_status_report(symbol, timeframe),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get("/api/v1/behavior/9c-dna/decision/{symbol}")
async def behavior_nine_candle_decision(symbol: str, timeframe: str = "1m"):
    return envelope(build_nine_candle_jarvis_panel(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/indicator-alignment/{symbol}")
async def behavior_nine_candle_indicator_alignment(symbol: str, timeframe: str = "1m", use_real_indicators: bool = False):
    return envelope(build_nine_candle_indicator_alignment(symbol, timeframe, use_real_indicators), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/model-status")
async def behavior_nine_candle_model_status(symbol: str = "RELIANCE", timeframe: str = "1m"):
    return envelope(build_nine_candle_model_status_for(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/feature-manifest")
async def behavior_nine_candle_feature_manifest():
    return envelope(build_nine_candle_feature_manifest(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/feature-manifest/integrity")
async def behavior_nine_candle_feature_manifest_integrity():
    return envelope(build_feature_manifest_integrity_report(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/calibration")
async def behavior_nine_candle_calibration(symbol: str = "RELIANCE", timeframe: str = "1m"):
    return envelope(build_nine_candle_calibration_for(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/model-promotion-guard")
async def behavior_nine_candle_model_promotion_guard(symbol: str = "RELIANCE", timeframe: str = "1m"):
    return envelope(build_model_promotion_guard(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/9c-dna/index-manifest")
async def behavior_nine_candle_index_manifest(symbol: str = "RELIANCE", timeframe: str = "1m"):
    return envelope(build_nine_candle_index_manifest(symbol, timeframe), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/indicators/observations/current")
async def behavior_indicator_observations_current(symbol: str = "NIFTY-MOCK", timeframe: str = "5m"):
    return envelope(
        build_indicator_observation_report(IndicatorObservationRequest(symbol=symbol, timeframe=timeframe)),  # type: ignore[arg-type]
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/indicators/observations")
async def behavior_indicator_observations(payload: IndicatorObservationRequest):
    return envelope(build_indicator_observation_report(payload), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/patterns/taxonomy/current")
async def behavior_pattern_taxonomy_current(symbol: str = "NIFTY-MOCK", timeframe: str = "5m"):
    return envelope(
        build_pattern_taxonomy_report(PatternTaxonomyRequest(symbol=symbol, timeframe=timeframe)),  # type: ignore[arg-type]
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/patterns/taxonomy")
async def behavior_pattern_taxonomy(payload: PatternTaxonomyRequest):
    return envelope(build_pattern_taxonomy_report(payload), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/timeframes/conflict/current")
async def behavior_timeframe_conflict_current(symbol: str = "NIFTY-MOCK", primary_timeframe: str = "5m"):
    return envelope(
        build_multi_timeframe_conflict_report(MultiTimeframeConflictRequest(symbol=symbol, primary_timeframe=primary_timeframe)),  # type: ignore[arg-type]
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/timeframes/conflict")
async def behavior_timeframe_conflict(payload: MultiTimeframeConflictRequest):
    return envelope(build_multi_timeframe_conflict_report(payload), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/timeframes/pullback/current")
async def behavior_timeframe_pullback_current(symbol: str = "NIFTY-MOCK", primary_timeframe: str = "5m"):
    return envelope(
        build_real_mtf_pullback_report(RealMtfPullbackRequest(symbol=symbol, primary_timeframe=primary_timeframe)),  # type: ignore[arg-type]
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/timeframes/pullback")
async def behavior_timeframe_pullback(payload: RealMtfPullbackRequest):
    return envelope(build_real_mtf_pullback_report(payload), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/features/seven-timeframe/current")
async def behavior_seven_timeframe_feature_runtime_current():
    return envelope(build_seven_timeframe_feature_runtime())


@app.post("/api/v1/behavior/features/seven-timeframe")
async def behavior_seven_timeframe_feature_runtime(payload: SevenTimeframeFeatureRuntimeRequest):
    return envelope(build_seven_timeframe_feature_runtime(payload))


@app.get("/api/v1/behavior/feature-store/status")
async def behavior_feature_store_status():
    return envelope(feature_store_status())


@app.post("/api/v1/behavior/feature-store/write")
async def behavior_feature_store_write(payload: FeatureStoreWriteRequest):
    return envelope(write_feature_store(payload))


@app.get("/api/v1/behavior/redundancy/audit/current")
async def behavior_redundancy_audit_current():
    return envelope(build_redundancy_audit())


@app.post("/api/v1/behavior/redundancy/audit")
async def behavior_redundancy_audit(payload: RedundancyAuditRequest):
    return envelope(build_redundancy_audit(payload))


@app.get("/api/v1/behavior/combination-similarity/current")
async def behavior_combination_similarity_current():
    return envelope(build_combination_similarity_report())


@app.post("/api/v1/behavior/combination-similarity")
async def behavior_combination_similarity(payload: CombinationSimilarityRequest):
    return envelope(build_combination_similarity_report(payload))


@app.get("/api/v1/behavior/analog-research/current")
async def behavior_analog_research_current():
    return envelope(build_analog_conditional_research_report())


@app.post("/api/v1/behavior/analog-research")
async def behavior_analog_research(payload: AnalogResearchRequest):
    return envelope(build_analog_conditional_research_report(payload))


@app.get("/api/v1/behavior/event-sequences/current")
async def behavior_event_sequences_current():
    return envelope(build_event_sequence_mining_report())


@app.post("/api/v1/behavior/event-sequences/mine")
async def behavior_event_sequences_mine(payload: EventSequenceMiningRequest):
    return envelope(build_event_sequence_mining_report(payload))


@app.get("/api/v1/behavior/confluence/diagnostics/current")
async def behavior_confluence_diagnostics_current():
    return envelope(build_false_agreement_confluence_report())


@app.post("/api/v1/behavior/confluence/diagnostics")
async def behavior_confluence_diagnostics(payload: FalseAgreementConfluenceRequest):
    return envelope(build_false_agreement_confluence_report(payload))


@app.get("/api/v1/behavior/design-similarity/current")
async def behavior_design_similarity_current():
    return envelope(build_design_similarity_report())


@app.post("/api/v1/behavior/design-similarity/score")
async def behavior_design_similarity_score(payload: DesignSimilarityRequest):
    return envelope(build_design_similarity_report(payload))


@app.get("/api/v1/behavior/bands/distances")
async def behavior_band_level_distances_current():
    return envelope(build_band_level_distance_report())


@app.post("/api/v1/behavior/value-clusters/discover")
async def behavior_value_clusters_discover(payload: BandLevelDistanceRequest):
    return envelope(build_band_level_distance_report(payload))


@app.get("/api/v1/behavior/patterns/by-timeframe")
async def behavior_patterns_by_timeframe_current():
    return envelope(build_pattern_by_timeframe_report())


@app.post("/api/v1/behavior/patterns/by-timeframe/analyze")
async def behavior_patterns_by_timeframe_analyze(payload: PatternByTimeframeRequest):
    return envelope(build_pattern_by_timeframe_report(payload))


@app.get("/api/v1/behavior/calendar/event-regime/current")
async def behavior_calendar_event_regime_current():
    return envelope(build_market_calendar_event_regime_report())


@app.post("/api/v1/behavior/calendar/event-regime/analyze")
async def behavior_calendar_event_regime_analyze(payload: MarketCalendarEventRegimeRequest):
    return envelope(build_market_calendar_event_regime_report(payload))


@app.get("/api/v1/behavior/cross-market/influence/current")
async def behavior_cross_market_influence_current():
    return envelope(build_cross_market_influence_report())


@app.post("/api/v1/behavior/cross-market/influence/analyze")
async def behavior_cross_market_influence_analyze(payload: CrossMarketInfluenceRequest):
    return envelope(build_cross_market_influence_report(payload))


@app.get("/api/v1/behavior/corporate-abnormal/current")
async def behavior_corporate_abnormal_current():
    return envelope(build_corporate_action_abnormal_market_report())


@app.post("/api/v1/behavior/corporate-abnormal/analyze")
async def behavior_corporate_abnormal_analyze(payload: CorporateActionAbnormalMarketRequest):
    return envelope(build_corporate_action_abnormal_market_report(payload))


@app.get("/api/v1/behavior/risk/portfolio-cooldown/current")
async def behavior_risk_portfolio_cooldown_current():
    return envelope(build_position_portfolio_cooldown_report())


@app.post("/api/v1/behavior/risk/portfolio-cooldown/analyze")
async def behavior_risk_portfolio_cooldown_analyze(payload: PositionPortfolioCooldownRequest):
    return envelope(build_position_portfolio_cooldown_report(payload))


@app.get("/api/v1/behavior/execution-intent/paper-safety/current")
async def behavior_execution_intent_paper_safety_current():
    return envelope(build_execution_intent_paper_safety_report())


@app.post("/api/v1/behavior/execution-intent/paper-safety/analyze")
async def behavior_execution_intent_paper_safety_analyze(payload: ExecutionIntentPaperSafetyRequest):
    return envelope(build_execution_intent_paper_safety_report(payload))


@app.get("/api/v1/behavior/execution-permission/preflight/current")
async def behavior_execution_permission_preflight_current():
    return envelope(build_paper_executor_permission_report(system_mode=SYSTEM_MODE, kill_switch=KILL_SWITCH))


@app.post("/api/v1/behavior/execution-permission/preflight/analyze")
async def behavior_execution_permission_preflight_analyze(payload: PaperExecutorPermissionRequest):
    return envelope(build_paper_executor_permission_report(payload))


@app.get("/api/v1/behavior/executor-handoff/audit/current")
async def behavior_executor_handoff_audit_current():
    return envelope(build_executor_handoff_audit_envelope())


@app.post("/api/v1/behavior/executor-handoff/audit/build")
async def behavior_executor_handoff_audit_build(payload: ExecutorHandoffAuditRequest):
    return envelope(build_executor_handoff_audit_envelope(payload))


@app.get("/api/v1/behavior/replay/indicator-chart/current")
async def behavior_replay_indicator_chart_current():
    payload = ReplayIndicatorValidationRequest()
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    return envelope(build_replay_indicator_validation_report(payload, events))


@app.post("/api/v1/behavior/replay/indicator-chart/validate")
async def behavior_replay_indicator_chart_validate(payload: ReplayIndicatorValidationRequest):
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    try:
        report = build_replay_indicator_validation_report(payload, events)
    except ValueError as exc:
        raise api_error(422, "replay_indicator_validation_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/chart/replay/current")
async def behavior_chart_replay_current():
    payload = BehaviorChartReplayRequest()
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    return envelope(build_chart_replay_report(payload, events))


@app.post("/api/v1/behavior/chart/replay")
async def behavior_chart_replay(payload: BehaviorChartReplayRequest):
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    try:
        report = build_chart_replay_report(payload, events)
    except ValueError as exc:
        raise api_error(422, "behavior_chart_replay_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/indicators/expansion/current")
async def behavior_indicator_expansion_current():
    payload = BehaviorIndicatorExpansionRequest()
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    return envelope(build_indicator_expansion_report(payload, events))


@app.post("/api/v1/behavior/indicators/expansion")
async def behavior_indicator_expansion(payload: BehaviorIndicatorExpansionRequest):
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    try:
        report = build_indicator_expansion_report(payload, events)
    except ValueError as exc:
        raise api_error(422, "behavior_indicator_expansion_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/replay/indicator-matrix/current")
async def behavior_replay_indicator_matrix_current():
    payload = ReplayIndicatorMatrixRequest()
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    return envelope(build_replay_indicator_matrix_report(payload, events))


@app.post("/api/v1/behavior/replay/indicator-matrix/validate")
async def behavior_replay_indicator_matrix_validate(payload: ReplayIndicatorMatrixRequest):
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    try:
        report = build_replay_indicator_matrix_report(payload, events)
    except ValueError as exc:
        raise api_error(422, "replay_indicator_matrix_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/decision/readiness/current")
async def behavior_matrix_decision_readiness_current():
    payload = MatrixDecisionReadinessRequest()
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    return envelope(build_matrix_decision_readiness_report(payload, events))


@app.post("/api/v1/behavior/decision/readiness/validate")
async def behavior_matrix_decision_readiness_validate(payload: MatrixDecisionReadinessRequest):
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    try:
        report = build_matrix_decision_readiness_report(payload, events)
    except ValueError as exc:
        raise api_error(422, "matrix_decision_readiness_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/lifecycle/current")
async def behavior_trade_lifecycle_current():
    payload = TradeLifecycleSimulationRequest()
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    return envelope(build_trade_lifecycle_simulation_report(payload, events))


@app.post("/api/v1/behavior/lifecycle/validate")
async def behavior_trade_lifecycle_validate(payload: TradeLifecycleSimulationRequest):
    events = deterministic_events(payload.seed, payload.scenario_id, payload.event_count)
    try:
        report = build_trade_lifecycle_simulation_report(payload, events)
    except ValueError as exc:
        raise api_error(422, "trade_lifecycle_simulation_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/lifecycle/compare/current")
async def behavior_lifecycle_compare_current():
    payload = TradeLifecycleScenarioComparisonRequest()
    return envelope(build_trade_lifecycle_scenario_comparison_report(payload, deterministic_events))


@app.post("/api/v1/behavior/lifecycle/compare")
async def behavior_lifecycle_compare(payload: TradeLifecycleScenarioComparisonRequest):
    try:
        report = build_trade_lifecycle_scenario_comparison_report(payload, deterministic_events)
    except ValueError as exc:
        raise api_error(422, "lifecycle_scenario_comparison_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/lifecycle/evidence/current")
async def behavior_lifecycle_evidence_current():
    payload = LifecycleEvidenceDrilldownRequest()
    return envelope(build_lifecycle_evidence_drilldown_report(payload, deterministic_events))


@app.post("/api/v1/behavior/lifecycle/evidence")
async def behavior_lifecycle_evidence(payload: LifecycleEvidenceDrilldownRequest):
    try:
        report = build_lifecycle_evidence_drilldown_report(payload, deterministic_events)
    except ValueError as exc:
        raise api_error(422, "lifecycle_evidence_drilldown_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/tradeability/current")
async def behavior_tradeability_current():
    payload = TradeabilityGuidanceRequest()
    return envelope(build_tradeability_guidance_report(payload, deterministic_events))


@app.post("/api/v1/behavior/tradeability")
async def behavior_tradeability(payload: TradeabilityGuidanceRequest):
    try:
        report = build_tradeability_guidance_report(payload, deterministic_events)
    except ValueError as exc:
        raise api_error(422, "tradeability_guidance_failed", str(exc), retryable=False) from exc
    return envelope(report)


@app.get("/api/v1/behavior/capability-manifest")
async def behavior_capability_manifest():
    behavior_names = set(BEHAVIOR_LAYER_NAMES) | {
        "Behavior Intelligence Contract Lock",
        "Stock-App Chart Indicator Backtest Migration",
        "Behavior Stock Memory Profile",
        "Kronos Forecast Engine",
        "Kronos Microservice",
        "Twin Machine Arbiter",
        "OpenAlgo SignalIntent Export",
    }
    behavior_caps = [cap for cap in CAPABILITIES if cap.name in behavior_names or "Behavior" in cap.name or "Kronos" in cap.name or "Twin" in cap.name or "OpenAlgo" in cap.name]
    return envelope(CapabilityManifest(capabilities=behavior_caps))


@app.get("/api/v1/kronos/status")
async def kronos_status():
    return envelope(build_kronos_status(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/kronos/models")
async def kronos_model_registry():
    return envelope(kronos_models(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/kronos/metrics")
async def kronos_metrics():
    return envelope(build_kronos_metrics(), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/kronos/service/status")
async def kronos_service_status():
    return envelope(build_kronos_service_bridge_status(), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/kronos/validate-input")
async def kronos_validate_input(payload: KronosForecastRequest):
    series = payload.series or _default_kronos_series(payload.symbol, payload.timeframe, payload.lookback_candles)
    return envelope(validate_kronos_input(payload, series), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/kronos/forecast")
async def kronos_forecast(payload: KronosForecastRequest):
    series = payload.series or _default_kronos_series(payload.symbol, payload.timeframe, payload.lookback_candles)
    report = build_kronos_forecast_with_optional_service(payload, series)
    if not report.input_validation.passed or not report.sanity_check.passed:
        audit("warning", f"Kronos forecast blocked for {report.symbol}: {', '.join(report.input_validation.blockers)}", "kronos")
    else:
        audit("info", f"Kronos forecast generated for {report.symbol}: {report.forecast_path.trend_direction}", "kronos")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/kronos/forecast-shared-snapshot")
async def kronos_forecast_shared_snapshot(payload: SharedSnapshotRequest):
    report = build_kronos_shared_snapshot_forecast(payload)
    if report.integrity.fail_closed:
        audit("warning", f"Kronos shared snapshot failed closed for {report.snapshot.symbol}: {', '.join(report.integrity.mismatch_fields)}", "kronos_shared_snapshot")
    else:
        audit("info", f"Kronos shared snapshot verified for {report.snapshot.symbol}", "kronos_shared_snapshot")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post(
    "/api/v1/paper-guidance/run",
    response_model=ApiEnvelope[PaperTradeGuidance],
)
async def paper_guidance_run(payload: PaperGuidanceRequest):
    guidance = run_paper_guidance_with_orb(
        payload,
        mode=SYSTEM_MODE,
        kill_switch=KILL_SWITCH,
    )
    audit_level = "info" if guidance.safety_gate.passed else "warning"
    audit(
        audit_level,
        f"Paper guidance {guidance.guidance_version} {guidance.final_band} "
        f"for {guidance.symbol} "
        f"{guidance.timeframe}; snapshot={guidance.snapshot_hash or 'not_minted'}",
        "paper_guidance",
    )
    return envelope(
        guidance,
        capability_status=CapabilityStatus.MOCK,
        quality=guidance.data_quality.data_quality_score,
        trust=guidance.confidence_cap,
    )


@app.get(
    "/api/v1/paper-guidance/orb-tickets",
    response_model=ApiEnvelope[list[OrbGuidanceTicket]],
)
async def paper_guidance_orb_tickets(
    symbol: str | None = None,
    timeframe: str | None = None,
):
    return envelope(
        list_guidance_tickets(symbol=symbol, timeframe=timeframe),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post(
    "/api/v1/paper-guidance/record-simulated",
    response_model=ApiEnvelope[SimulatedPaperTradeRecord],
)
async def paper_guidance_record_simulated(
    payload: SimulatedPaperRecordApprovalRequest,
):
    try:
        record = record_simulated_paper_trade(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AtomicJsonStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    audit(
        "info",
        f"Human-approved simulated ORB paper record {record.paper_record_id} "
        f"for {record.symbol} {record.timeframe}; no order was created",
        "orb_paper_record",
    )
    return envelope(
        record,
        capability_status=CapabilityStatus.MOCK,
        quality=1.0,
        trust=0.0,
    )


@app.get(
    "/api/v1/paper-guidance/paper-records",
    response_model=ApiEnvelope[list[SimulatedPaperTradeRecord]],
)
async def paper_guidance_paper_records(
    symbol: str | None = None,
    timeframe: str | None = None,
):
    try:
        records = list_simulated_paper_trades(
            symbol=symbol,
            timeframe=timeframe,
        )
    except AtomicJsonStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return envelope(records, capability_status=CapabilityStatus.MOCK)


@app.post(
    "/api/v1/paper-guidance/paper-records/observe",
    response_model=ApiEnvelope[SimulatedPaperLifecycleOutcome],
)
async def paper_guidance_observe_simulated_lifecycle(
    payload: SimulatedPaperLifecycleObservationRequest,
):
    try:
        outcome = evaluate_simulated_paper_lifecycle(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AtomicJsonStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    audit(
        "info",
        f"Explicit simulated ORB lifecycle observation "
        f"{outcome.outcome_id} produced {outcome.outcome_label}; "
        "no external execution occurred",
        "orb_paper_lifecycle",
    )
    return envelope(
        outcome,
        capability_status=CapabilityStatus.MOCK,
        quality=1.0 if outcome.point_in_time_safe else 0.0,
        trust=0.0,
    )


@app.get(
    "/api/v1/paper-guidance/paper-outcomes",
    response_model=ApiEnvelope[list[SimulatedPaperLifecycleOutcome]],
)
async def paper_guidance_paper_outcomes(
    paper_record_id: str | None = None,
    playbook_id: str | None = None,
    completed_only: bool = False,
):
    try:
        rows = list_simulated_paper_outcomes(
            paper_record_id=paper_record_id,
            playbook_id=playbook_id,
            completed_only=completed_only,
        )
    except AtomicJsonStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return envelope(rows, capability_status=CapabilityStatus.MOCK)


@app.get(
    "/api/v1/paper-guidance/orb-reliability/{playbook_id}",
    response_model=ApiEnvelope[OrbPaperReliabilityReport],
)
async def paper_guidance_orb_reliability(
    playbook_id: str,
    symbol: str = "UNKNOWN",
    timeframe: str = "5m",
):
    try:
        report = build_orb_paper_reliability(
            playbook_id,
            symbol=symbol,
            timeframe=timeframe,
        )
    except AtomicJsonStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return envelope(
        report,
        capability_status=CapabilityStatus.MOCK,
        quality=1.0 if report.orphan_outcome_count == 0 else 0.0,
        trust=report.bayesian_win_rate if report.minimum_sample_pass else 0.0,
    )


@app.get(
    "/api/v1/paper-guidance/storage-monitor",
    response_model=ApiEnvelope[PaperGuidanceStorageMonitor],
)
async def paper_guidance_storage_monitor():
    report = build_paper_guidance_storage_monitor()
    return envelope(
        report,
        capability_status=CapabilityStatus.MOCK,
        quality=1.0 if report.integrity_passed else 0.0,
        trust=0.0,
    )


@app.post(
    "/api/v1/orb/build",
    response_model=ApiEnvelope[OrbBuildResult],
)
async def orb_build(payload: OrbBuildRequest):
    result = build_orb_candidate(payload)
    audit(
        "info",
        f"ORB v1.89 {result.signal.signal_type} for {result.symbol} "
        f"{result.timeframe}; range_locked={result.range_locked}",
        "orb",
    )
    return envelope(
        result,
        capability_status=CapabilityStatus.MOCK,
        quality=1.0 if result.no_future_leakage else 0.0,
        trust=0.0,
    )


@app.post(
    "/api/v1/orb/discover",
    response_model=ApiEnvelope[OrbDiscoveryJob],
)
async def orb_discover(payload: OrbDiscoveryRequest, background_tasks: BackgroundTasks):
    job = submit_orb_discovery(payload)
    background_tasks.add_task(run_orb_discovery_job, job.job_id, payload)
    audit(
        "info",
        f"ORB discovery queued for {payload.series.symbol.upper()} "
        f"{payload.series.timeframe}; job={job.job_id}",
        "orb_discovery",
    )
    return envelope(job, capability_status=CapabilityStatus.MOCK)


@app.get(
    "/api/v1/orb/discover/{job_id}",
    response_model=ApiEnvelope[OrbDiscoveryJob],
)
async def orb_discover_status(job_id: str):
    job = get_orb_discovery_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ORB discovery job not found")
    return envelope(job, capability_status=CapabilityStatus.MOCK)


@app.post(
    "/api/v1/orb/prove",
    response_model=ApiEnvelope[OrbProofReport],
)
async def orb_prove(payload: OrbProofRequest):
    report = run_orb_proof(payload)
    audit(
        "info",
        f"ORB proof completed for {report.symbol} {report.timeframe}; "
        f"eligible={len(report.eligible_combo_ids)}",
        "orb_proof",
    )
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post(
    "/api/v1/orb/playbooks/promote",
    response_model=ApiEnvelope[OrbPlaybook],
)
async def orb_playbook_promote(payload: OrbPlaybookPromotionRequest):
    try:
        playbook = promote_orb_playbook(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit(
        "info",
        f"ORB playbook promoted for {playbook.symbol} {playbook.timeframe}; "
        f"playbook={playbook.playbook_id}",
        "orb_playbook",
    )
    return envelope(playbook, capability_status=CapabilityStatus.MOCK)


@app.get(
    "/api/v1/orb/playbooks",
    response_model=ApiEnvelope[list[OrbPlaybook]],
)
async def orb_playbooks(symbol: str | None = None, timeframe: str | None = None):
    return envelope(
        list_orb_playbooks(symbol=symbol, timeframe=timeframe),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post(
    "/api/v1/orb/timing-research",
    response_model=ApiEnvelope[OrbTimingResearchJob],
)
async def orb_timing_research_submit(payload: OrbTimingResearchRequest, background_tasks: BackgroundTasks):
    job = submit_timing_research(payload)
    background_tasks.add_task(run_timing_research_job, job.job_id, payload)
    symbol_note = (
        f"{len(payload.symbols)} explicit"
        if payload.symbols_source == "explicit"
        else "trendforge_latest"
    )
    audit(
        "info",
        f"ORB v1.97 timing research queued: {symbol_note} symbols, tf={payload.timeframe}, "
        f"windows={len(payload.clock_windows)}; job={job.job_id}",
        "orb_timing_research",
    )
    return envelope(job, capability_status=CapabilityStatus.MOCK)


@app.get(
    "/api/v1/orb/timing-research/jobs/{job_id}",
    response_model=ApiEnvelope[OrbTimingResearchJob],
)
async def orb_timing_research_status(job_id: str):
    job = get_timing_research_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ORB timing research job not found")
    return envelope(job, capability_status=CapabilityStatus.MOCK)


@app.get(
    "/api/v1/orb/timing-research/runs",
    response_model=ApiEnvelope[list[OrbTimingResearchResult]],
)
async def orb_timing_research_runs(limit: int = 10):
    return envelope(
        storage.list_orb_timing_runs(limit=limit),
        capability_status=CapabilityStatus.MOCK,
    )


@app.get(
    "/api/v1/orb/timing-research/runs/{run_id}",
    response_model=ApiEnvelope[OrbTimingResearchResult],
)
async def orb_timing_research_run(run_id: str):
    result = storage.get_orb_timing_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="ORB timing research run not found")
    return envelope(result, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/orb/timing-research/runs/{run_id}/export.csv")
async def orb_timing_research_export(run_id: str):
    stored = storage.get_orb_timing_run(run_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="ORB timing research run not found")
    result = OrbTimingResearchResult.model_validate(stored)
    csv_bytes = orb_timing_export_csv_bytes(result)
    audit(
        "info",
        f"ORB timing research CSV exported: run={run_id} rows={len(result.rows)}",
        "orb_timing_research",
    )
    return CsvResponse(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="orb_timing_{run_id[:12]}.csv"'},
    )


@app.get("/api/v1/kronos/forecast-shared-snapshot/current")
async def kronos_forecast_shared_snapshot_current(symbol: str = "NIFTY-MOCK"):
    return envelope(build_kronos_shared_snapshot_forecast(SharedSnapshotRequest(symbol=symbol)), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/twin/snapshot-integrity")
async def twin_snapshot_integrity(payload: SharedSnapshotRequest):
    report = build_kronos_shared_snapshot_forecast(payload)
    return envelope(report.integrity, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/kronos/backtest")
async def kronos_backtest(payload: KronosBacktestRequest):
    return envelope(build_kronos_backtest_result(payload), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/kronos/backtest/{run_id}")
async def kronos_backtest_by_id(run_id: str):
    # The first shell is deterministic and stateless; run_id is echoed for UI lookup without promotion.
    result = build_kronos_backtest_result(KronosBacktestRequest())
    return envelope(result.model_copy(update={"run_id": run_id}), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/twin/current")
async def twin_current(symbol: str = "NIFTY-MOCK"):
    return envelope(_build_current_twin(symbol), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/twin/dashboard/current")
async def twin_dashboard_current(symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    conflicts = build_twin_conflicts(symbol, comparison)
    reliability = build_twin_reliability(symbol, sample_count=0)
    tournament = build_twin_tournament(
        TwinTournamentRequest(symbol=symbol, timeframe="5m", seed=42, scenario_count=3),
        [comparison],
    )
    valid_until = comparison.kronos.expiry.valid_until if comparison.kronos else now_iso()
    intent = build_signal_intent_preview(
        comparison=comparison,
        mode=SYSTEM_MODE,
        kill_switch=KILL_SWITCH,
        valid_until=valid_until,
    )
    return envelope(
        build_twin_machine_dashboard(
            symbol=symbol,
            comparison=comparison,
            conflicts=conflicts,
            reliability=reliability,
            tournament=tournament,
            intent_preview=intent,
        ),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/twin/analyze")
async def twin_analyze(payload: KronosForecastRequest):
    behavior = evaluate_trade_decision(_default_behavior_decision_request(payload.symbol))
    series = payload.series or _default_kronos_series(payload.symbol, payload.timeframe, payload.lookback_candles)
    kronos = build_kronos_forecast_with_optional_service(payload, series)
    comparison = build_twin_engine_comparison(symbol=payload.symbol, behavior=behavior, kronos=kronos)
    audit("warning" if comparison.arbiter_action != "RESEARCH_CANDIDATE" else "info", f"Twin comparison {comparison.symbol}: {comparison.agreement_state}", "twin")
    return envelope(comparison, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/twin/full-analysis/current")
async def twin_full_analysis_current(symbol: str = "NIFTY-MOCK"):
    payload = FullTwinAnalysisRequest(symbol=symbol)
    behavior = _default_full_twin_behavior(payload)
    return envelope(build_full_twin_analysis(payload, behavior=behavior), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/twin/full-analysis")
async def twin_full_analysis(payload: FullTwinAnalysisRequest):
    behavior = _default_full_twin_behavior(payload)
    report = build_full_twin_analysis(payload, behavior=behavior)
    audit("warning" if report.arbiter_action != "RESEARCH_CANDIDATE" else "info", f"Full Twin Analysis {report.symbol}: {report.agreement_state}", "full_twin")
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/behavior/full-analysis")
async def behavior_full_analysis(payload: FullTwinAnalysisRequest):
    behavior = _default_full_twin_behavior(payload)
    report = build_full_twin_analysis(payload, behavior=behavior)
    return envelope(report.behavior, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/behavior/walk-forward/current")
async def behavior_walk_forward_current(symbol: str = "NIFTY-MOCK"):
    return envelope(
        build_walk_forward_validation_report(WalkForwardValidationRequest(symbol=symbol)),
        capability_status=CapabilityStatus.MOCK,
    )


@app.post("/api/v1/behavior/walk-forward")
async def behavior_walk_forward(payload: WalkForwardValidationRequest):
    report = build_walk_forward_validation_report(payload)
    audit(
        "warning" if not report.calibration_passed else "info",
        f"v0.68 walk-forward {report.symbol}: calibration_passed={report.calibration_passed}",
        "behavior_walk_forward",
    )
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/twin/conflicts")
async def twin_conflicts(symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    return envelope(build_twin_conflicts(symbol, comparison), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/twin/reliability")
async def twin_reliability(symbol: str = "NIFTY-MOCK"):
    return envelope(build_twin_reliability(symbol, sample_count=0), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/twin/replay")
async def twin_replay(payload: KronosForecastRequest):
    return await twin_analyze(payload)


@app.post("/api/v1/twin/tournament")
async def twin_tournament(payload: TwinTournamentRequest):
    comparisons = [
        build_twin_engine_comparison(
            symbol=payload.symbol,
            behavior=evaluate_trade_decision(_default_behavior_decision_request(payload.symbol)),
            kronos=build_mock_kronos_forecast(
                KronosForecastRequest(symbol=payload.symbol, timeframe=payload.timeframe, seed=payload.seed + idx),
                _default_kronos_series(payload.symbol, payload.timeframe, 64),
            ),
        )
        for idx in range(payload.scenario_count)
    ]
    return envelope(build_twin_tournament(payload, comparisons), capability_status=CapabilityStatus.MOCK)


@app.post("/api/v1/openalgo/preview-intent")
async def openalgo_preview_intent(symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    valid_until = comparison.kronos.expiry.valid_until if comparison.kronos else now_iso()
    return envelope(build_signal_intent_preview(comparison=comparison, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH, valid_until=valid_until), capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/export-intent")
async def openalgo_export_intent(symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    valid_until = comparison.kronos.expiry.valid_until if comparison.kronos else now_iso()
    preview = build_signal_intent_preview(comparison=comparison, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH, valid_until=valid_until)
    # Export remains a pending intent object only; no broker order is created inside Trade Vision.
    status = "expired" if preview.expired else "pending_for_openalgo"
    return envelope(preview.model_copy(update={"export_status": status}), capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/verify-intent")
async def openalgo_verify_intent(payload: BotHandoffVerificationRequest):
    report = verify_bot_handoff_intent(payload)
    audit(
        "warning" if report.rejected else "info",
        f"OpenAlgo/bot handoff verification for {report.symbol}: rejected={report.rejected}",
        "openalgo",
    )
    return envelope(report, capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/verify-intent/current")
async def openalgo_verify_current_intent(symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    valid_until = comparison.kronos.expiry.valid_until if comparison.kronos else now_iso()
    preview = build_signal_intent_preview(comparison=comparison, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH, valid_until=valid_until)
    report = verify_bot_handoff_intent(
        BotHandoffVerificationRequest(
            intent=preview,
            target_executor="openalgo",
            external_human_approval_present=False,
            external_risk_check_passed=False,
            external_account_state_checked=False,
        )
    )
    return envelope(report, capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/executor/spec")
async def openalgo_executor_spec():
    return envelope(
        {
            "spec_version": "openalgo-executor-spec.v0.50",
            "handoff_contract": _executor_handoff_contract(),
            "executor_required_checks": _executor_required_checks(),
            "trade_vision_scope": "research_evidence_and_dry_run_intent_packaging_only",
            "forbidden_inside_trade_vision": [
                "broker credentials",
                "broker login",
                "order placement",
                "order modification",
                "order cancellation",
                "paper/live routing",
            ],
            "artifact_root": str(_runtime_artifact_dir(EXECUTOR_DRY_RUN_DIR, "TRADEVISION_EXECUTOR_DRY_RUN_DIR")),
            "live_trading_blocked": True,
        },
        capability_status=CapabilityStatus.RESERVED,
    )


@app.get("/api/v1/openalgo/executor/dry-run/current")
async def openalgo_executor_dry_run_current(symbol: str = "NIFTY-MOCK"):
    package = _export_executor_dry_run_package(ExecutorDryRunPackageRequest(symbol=symbol))
    audit("info", f"OpenAlgo dry-run executor package created for {package.symbol}: {package.package_id}", "openalgo")
    return envelope(package, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/executor/dry-run/export")
async def openalgo_executor_dry_run_export(payload: ExecutorDryRunPackageRequest):
    package = _export_executor_dry_run_package(payload)
    audit("info", f"OpenAlgo dry-run executor package exported for {package.symbol}: {package.package_id}", "openalgo")
    return envelope(package, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/executor/dry-run/verify")
async def openalgo_executor_dry_run_verify(payload: ExecutorDryRunPackage):
    return envelope(_verify_executor_dry_run_package(payload), capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/executor/golden-fixtures")
async def openalgo_executor_golden_fixtures():
    return envelope(_build_executor_golden_fixtures(), capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/executor/golden-fixtures/verify")
async def openalgo_executor_golden_fixtures_verify():
    registry = _build_executor_golden_fixtures()
    verifications = [_verify_executor_golden_fixture(fixture) for fixture in registry.fixtures]
    return envelope(
        {
            "verification_version": "openalgo-executor-golden-registry-verification.v0.51",
            "registry_version": registry.registry_version,
            "registry_hash": registry.registry_hash,
            "fixture_count": registry.fixture_count,
            "passed_count": sum(item.passed for item in verifications),
            "all_passed": all(item.passed for item in verifications),
            "verifications": [item.model_dump(mode="json") for item in verifications],
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        capability_status=CapabilityStatus.RESERVED,
    )


@app.get("/api/v1/openalgo/executor/golden-fixtures/{fixture_id}")
async def openalgo_executor_golden_fixture(fixture_id: str):
    registry = _build_executor_golden_fixtures()
    fixture = next((item for item in registry.fixtures if item.fixture_id == fixture_id), None)
    if fixture is None:
        raise api_error(404, "executor_golden_fixture_not_found", f"Executor golden fixture not found: {fixture_id}")
    return envelope(fixture, capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/executor/golden-fixtures/{fixture_id}/verify")
async def openalgo_executor_golden_fixture_verify(fixture_id: str):
    registry = _build_executor_golden_fixtures()
    fixture = next((item for item in registry.fixtures if item.fixture_id == fixture_id), None)
    if fixture is None:
        raise api_error(404, "executor_golden_fixture_not_found", f"Executor golden fixture not found: {fixture_id}")
    return envelope(_verify_executor_golden_fixture(fixture), capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/executor/conformance/current")
async def openalgo_executor_conformance_current():
    report = _evaluate_executor_adapter_conformance(_reference_executor_conformance_request())
    return envelope(report, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/executor/conformance/evaluate")
async def openalgo_executor_conformance_evaluate(payload: ExecutorAdapterConformanceRequest):
    report = _evaluate_executor_adapter_conformance(payload)
    audit(
        "info" if report.all_passed else "warning",
        f"Executor adapter conformance {report.adapter_name}@{report.adapter_version}: all_passed={report.all_passed}",
        "openalgo",
    )
    return envelope(report, capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/transport/status")
async def openalgo_transport_status(check_health: bool = False):
    return envelope(
        transport_status(check_health=check_health),
        capability_status=CapabilityStatus.RESERVED,
    )


@app.get("/api/v1/openalgo/transport/outbox")
async def openalgo_transport_outbox(status: str | None = None, limit: int = 100):
    bounded_limit = max(1, min(limit, 500))
    return envelope(
        storage.list_executor_transport_records(status=status, limit=bounded_limit),
        capability_status=CapabilityStatus.RESERVED,
    )


@app.get("/api/v1/openalgo/transport/outbox/{delivery_id}")
async def openalgo_transport_outbox_record(delivery_id: str):
    record = storage.load_executor_transport_record(delivery_id)
    if record is None:
        raise api_error(404, "executor_transport_record_not_found", f"Executor transport record not found: {delivery_id}")
    return envelope(record, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/transport/enqueue")
async def openalgo_transport_enqueue(payload: ExecutorTransportEnqueueRequest):
    try:
        record = enqueue_transport(payload)
    except ValueError as exc:
        raise api_error(422, "invalid_executor_transport_configuration", str(exc))
    audit(
        "info",
        f"Executor transport enqueued for {record.package.symbol}: {record.delivery_id}",
        "openalgo",
    )
    return envelope(record, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/transport/outbox/{delivery_id}/deliver")
async def openalgo_transport_deliver(delivery_id: str):
    try:
        result = deliver_transport(delivery_id)
    except KeyError:
        raise api_error(404, "executor_transport_record_not_found", f"Executor transport record not found: {delivery_id}")
    audit(
        "info" if result.status == "acknowledged" else "warning",
        f"Executor transport delivery {delivery_id}: {result.status}",
        "openalgo",
    )
    return envelope(result, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/transport/worker/run")
async def openalgo_transport_worker_run(payload: ExecutorTransportWorkerRequest, request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["operator", "risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    run = run_due_worker(payload.model_copy(update={"actor_id": identity.actor_id}))
    audit(
        "info" if run.dead_letter_count == 0 else "warning",
        f"Transport recovery worker {run.run_id}: processed={run.processed_count} dead_letter={run.dead_letter_count}",
        "openalgo_transport",
    )
    return envelope(run, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/transport/outbox/{delivery_id}/retry")
async def openalgo_transport_operator_retry(
    delivery_id: str,
    payload: ExecutorTransportOperatorAction,
    request: Request,
):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["operator", "risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    try:
        record = operator_retry(delivery_id, payload.model_copy(update={"actor_id": identity.actor_id}))
    except KeyError:
        raise api_error(404, "executor_transport_record_not_found", f"Executor transport record not found: {delivery_id}")
    except ValueError as exc:
        raise api_error(409, "executor_transport_retry_invalid_state", str(exc))
    audit("warning", f"Transport retry requested by {identity.actor_id}: {delivery_id}", "openalgo_transport")
    return envelope(record, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/transport/outbox/{delivery_id}/cancel")
async def openalgo_transport_operator_cancel(
    delivery_id: str,
    payload: ExecutorTransportOperatorAction,
    request: Request,
):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    try:
        record = operator_cancel(delivery_id, payload.model_copy(update={"actor_id": identity.actor_id}))
    except KeyError:
        raise api_error(404, "executor_transport_record_not_found", f"Executor transport record not found: {delivery_id}")
    except ValueError as exc:
        raise api_error(409, "executor_transport_cancel_invalid_state", str(exc))
    audit("warning", f"Transport cancelled by {identity.actor_id}: {delivery_id}", "openalgo_transport")
    return envelope(record, capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/transport/traces")
async def openalgo_transport_traces(delivery_id: str | None = None, limit: int = 100):
    return envelope(
        storage.list_executor_transport_traces(delivery_id=delivery_id, limit=max(1, min(limit, 500))),
        capability_status=CapabilityStatus.RESERVED,
    )


@app.get("/api/v1/openalgo/resilience/current")
async def openalgo_transport_resilience_current(record_health: bool = False, evidence_window: int = 100):
    return envelope(
        build_resilience_report(
            evidence_window=max(10, min(evidence_window, 1000)),
            record_health=record_health,
        ),
        capability_status=CapabilityStatus.RESERVED,
    )


@app.post("/api/v1/openalgo/resilience/health-sample")
async def openalgo_transport_health_sample(request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["operator", "risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    sample = record_health_sample()
    audit(
        "info" if sample.health_ok else "warning",
        f"OpenAlgo adapter health sample: ok={sample.health_ok} circuit={sample.circuit_state}",
        "openalgo_resilience",
    )
    return envelope(sample, capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/resilience/health-history")
async def openalgo_transport_health_history(limit: int = 100):
    return envelope(
        storage.list_transport_health_samples(limit=max(1, min(limit, 1000))),
        capability_status=CapabilityStatus.RESERVED,
    )


@app.get("/api/v1/openalgo/resilience/incidents")
async def openalgo_transport_incidents(limit: int = 100):
    return envelope(
        storage.list_transport_incidents(limit=max(1, min(limit, 1000))),
        capability_status=CapabilityStatus.RESERVED,
    )


@app.post("/api/v1/openalgo/resilience/incidents/{incident_id}/acknowledge")
async def openalgo_transport_incident_acknowledge(
    incident_id: str,
    payload: TransportIncidentAction,
    request: Request,
):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["operator", "risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    try:
        incident = acknowledge_incident(
            incident_id,
            payload.model_copy(update={"actor_id": identity.actor_id}),
        )
    except KeyError:
        raise api_error(404, "transport_incident_not_found", f"Active incident not found: {incident_id}")
    except ValueError as exc:
        raise api_error(409, "transport_incident_invalid_state", str(exc))
    audit("warning", f"Transport incident acknowledged by {identity.actor_id}: {incident_id}", "openalgo_resilience")
    return envelope(incident, capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/resilience/fault-harness")
async def openalgo_transport_fault_harness(payload: TransportFaultHarnessRequest):
    report = run_fault_harness(payload)
    return envelope(report, capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/security/posture")
async def openalgo_transport_security_posture():
    return envelope(build_security_posture(), capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/security/trace-integrity")
async def openalgo_transport_trace_integrity(delivery_id: str | None = None):
    return envelope(
        verify_trace_integrity(delivery_id=delivery_id),
        capability_status=CapabilityStatus.RESERVED,
    )


@app.get("/api/v1/openalgo/security/threat-report")
async def openalgo_transport_threat_report():
    return envelope(build_threat_report(), capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/report/import")
async def openalgo_report_import(payload: dict[str, Any]):
    try:
        report = import_openalgo_report(payload)
    except ValueError as exc:
        raise api_error(422, "openalgo_report_import_invalid", str(exc))
    storage.save_openalgo_report_import(report)
    audit(
        "warning" if report["safety_result"]["rejection_reasons"] else "info",
        f"OpenAlgo report imported for {report['symbol']}: {report['report_id']} effect={report['jarvis_effect']['effect']}",
        "openalgo_report_import",
    )
    return envelope(report, capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/openalgo/report/current/{symbol}")
async def openalgo_report_current(symbol: str):
    normalized = _normalize_symbol(symbol)
    report = storage.load_latest_openalgo_report_import(normalized)
    return envelope(summarize_openalgo_report(report), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/openalgo/report/reality-check/current/{symbol}")
async def openalgo_report_reality_check_current(symbol: str, timeframe: str = "1m", rows: int = 390, position: str = "tail"):
    normalized = _normalize_symbol(symbol)
    bounded_rows = max(120, min(rows, 2000))
    if normalized == "RELIANCE" and timeframe == "1m" and LOCAL_RELIANCE_1M_CSV.exists():
        payload = BehaviorOhlcvImportRequest(
            symbol="RELIANCE",
            timeframe="1m",
            csv_text=_local_reliance_csv_text(bounded_rows, position if position in {"head", "tail"} else "tail"),
            date_column="date",
            time_column="time",
            timezone_offset_minutes=330,
            persist_snapshot=False,
        )
        imported = import_ohlcv_csv(payload)
        series = imported.series
        quality = scan_data_quality(series)
    else:
        series = _default_kronos_series(normalized, timeframe, bounded_rows)
        quality = scan_data_quality(series)
    report = storage.load_latest_openalgo_report_import(normalized)
    state = build_jarvis_decision_room_state(
        symbol=normalized,
        timeframe=timeframe,
        series=series,
        data_quality=quality,
        system_mode=SYSTEM_MODE.mode,
        kill_switch_active=KILL_SWITCH.state == "triggered",
        kronos_status=build_kronos_status(),
        openalgo_report=report,
    )
    return envelope(state["paper_reality_check"], capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/openalgo/report/imports")
async def openalgo_report_imports(symbol: str | None = None, limit: int = 25):
    normalized = _normalize_symbol(symbol) if symbol else None
    return envelope(storage.list_openalgo_report_imports(symbol=normalized, limit=limit), capability_status=CapabilityStatus.MOCK)


@app.get("/api/v1/deployment/configuration")
async def get_deployment_configuration():
    return envelope(deployment_readiness().configuration)


@app.get("/api/v1/deployment/readiness")
async def get_deployment_readiness():
    return envelope(deployment_readiness())


@app.get("/api/v1/deployment/smoke")
async def get_deployment_smoke():
    return envelope(deployment_smoke())


@app.post("/api/v1/deployment/database/backup")
async def post_deployment_database_backup(request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["risk_manager", "admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    artifact = create_database_backup()
    audit("warning", f"Database backup created by {identity.actor_id}: {artifact.backup_id}", "deployment")
    return envelope(artifact)


@app.post("/api/v1/deployment/database/restore-drill")
async def post_deployment_restore_drill(payload: DatabaseBackupArtifact, request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    try:
        report = restore_drill(payload)
    except FileNotFoundError:
        raise api_error(404, "deployment_backup_not_found", f"Backup not found: {payload.backup_path}")
    except ValueError as exc:
        raise api_error(422, "deployment_restore_drill_invalid", str(exc))
    audit(
        "info" if report.passed else "critical",
        f"Database restore drill by {identity.actor_id}: passed={report.passed} backup={report.backup_id}",
        "deployment",
    )
    return envelope(report)


@app.get("/api/v1/release/final-audit")
async def get_final_release_audit():
    return envelope(build_final_release_audit())


@app.get("/api/v1/release/readiness-evidence")
async def get_release_readiness_evidence(force_refresh: bool = False):
    return envelope(build_release_readiness_evidence_report(force_refresh=force_refresh))


@app.get("/api/v1/release/safety-scan")
async def get_release_safety_scan():
    return envelope(scan_for_unsafe_live_paths())


@app.get("/api/v1/release/candidate/current")
async def get_release_candidate_manifest():
    return envelope(build_release_manifest())


@app.post("/api/v1/release/candidate/export")
async def post_release_candidate_export(request: Request):
    identity = identity_from_request(request)
    rbac = authorize(identity, ["admin"])
    if not rbac.allowed:
        raise api_error(403, "rbac_denied", rbac.reason)
    try:
        manifest = export_release_candidate()
    except ValueError as exc:
        raise api_error(409, "release_audit_blocked", str(exc))
    audit(
        "warning",
        f"Research release candidate exported by {identity.actor_id}: {manifest.release_id}",
        "release",
    )
    return envelope(manifest)


@app.get("/api/v1/openalgo/intents/pending")
async def openalgo_pending_intents(symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    valid_until = comparison.kronos.expiry.valid_until if comparison.kronos else now_iso()
    preview = build_signal_intent_preview(comparison=comparison, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH, valid_until=valid_until)
    return envelope([preview], capability_status=CapabilityStatus.RESERVED)


@app.get("/api/v1/openalgo/intents/{intent_id}")
async def openalgo_intent_by_id(intent_id: str, symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    valid_until = comparison.kronos.expiry.valid_until if comparison.kronos else now_iso()
    preview = build_signal_intent_preview(comparison=comparison, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH, valid_until=valid_until)
    return envelope(preview.model_copy(update={"intent_id": intent_id}), capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/openalgo/intents/{intent_id}/cancel")
async def openalgo_cancel_intent(intent_id: str, symbol: str = "NIFTY-MOCK"):
    comparison = _build_current_twin(symbol)
    valid_until = comparison.kronos.expiry.valid_until if comparison.kronos else now_iso()
    preview = build_signal_intent_preview(comparison=comparison, mode=SYSTEM_MODE, kill_switch=KILL_SWITCH, valid_until=valid_until)
    return envelope(preview.model_copy(update={"intent_id": intent_id, "export_status": "cancelled"}), capability_status=CapabilityStatus.RESERVED)


@app.post("/api/v1/behavior/analyze")
async def behavior_analyze(payload: BehaviorAnalyzeRequest):
    _ensure_behavior_seed_data(payload.symbol)
    decision_time = now_iso()
    result = mock_behavior_result(symbol=payload.symbol, timeframe=payload.timeframe, decision_time=decision_time)
    run_id = _behavior_run_id(payload.symbol, payload.timeframe, payload.seed)
    result["backtest_id"] = run_id
    result["decision_audit_log"] = f"{run_id}; mock behavior contract lock result; no live route attempted"
    safety_gates = [
        "LIVE mode blocked",
        "kill switch checked",
        "point-in-time guard pending real data adapter",
        "minimum evidence guard active",
        "no live route attempted",
    ]
    analysis = BehaviorAnalysisResult(
        symbol=_normalize_symbol(payload.symbol),
        timeframe=payload.timeframe,
        run_id=run_id,
        result=result,
        columns=EXPECTED_74_COLUMNS,
        safety_gates=safety_gates,
        reason_tree={
            "signal_reason": "Legacy rule stack is represented but not promoted to live trading.",
            "candle_reason": "Mock candle state shows upper-wick rejection and absorption risk.",
            "level_reason": "VWAP reclaim confirmation is required before trade consideration.",
            "memory_reason": LOW_EVIDENCE_MESSAGE,
            "risk_reason": "Capital use is zero because this is a contract-lock mock analysis.",
            "block_reason": "Behavior engine is not yet promoted beyond MOCK.",
            "final_reason": result["reason"],
        },
        live_trade_route_attempted=False,
    )
    storage.save_behavior_analysis(analysis)
    audit("info", f"Behavior mock analysis generated for {payload.symbol} {payload.timeframe}", "behavior")
    return envelope(analysis)


@app.get("/api/v1/behavior/stock/{symbol}/dna")
async def behavior_stock_dna(symbol: str):
    profile, _, _ = _ensure_behavior_seed_data(symbol)
    return envelope(profile)


@app.get("/api/v1/behavior/stock/{symbol}/memory")
async def behavior_stock_memory(symbol: str):
    _, memory, _ = _ensure_behavior_seed_data(symbol)
    return envelope(memory)


@app.get("/api/v1/behavior/similar-days/{symbol}")
async def behavior_similar_days(symbol: str):
    request = _default_pattern_memory_request(symbol)
    _, memory, _ = _ensure_behavior_seed_data(symbol)
    result = analyze_pattern_memory(request, memory)
    for match in result.matches:
        storage.save_similar_day_match(match)
    return envelope(result.matches)


@app.get("/api/v1/behavior/similar-days/{symbol}/replay/{similar_day_id}")
async def behavior_similar_day_replay(symbol: str, similar_day_id: str):
    request = _default_pattern_memory_request(symbol)
    _, memory, _ = _ensure_behavior_seed_data(symbol)
    result = analyze_pattern_memory(request, memory)
    match = next((item for item in result.matches if item.similar_day_id == similar_day_id), None)
    if match is None:
        raise api_error(404, "similar_day_not_found", f"Similar day not found: {similar_day_id}")
    return envelope(build_similar_day_replay(symbol, match))


@app.post("/api/v1/behavior/benchmark/run")
async def behavior_benchmark_run(payload: BehaviorAnalyzeRequest):
    _ensure_behavior_seed_data(payload.symbol)
    created_at = now_iso()
    run = BehaviorBenchmarkRun(
        run_id=_benchmark_run_id(payload.symbol, payload.timeframe, payload.seed),
        symbol=_normalize_symbol(payload.symbol),
        status="completed",
        created_at=created_at,
        completed_at=created_at,
        mode=SYSTEM_MODE.mode,
        benchmark_type="mock_contract",
        metrics={
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
            "trade_count": 0,
            "avg_holding_time": "not_applicable_mock_contract",
            "deterministic_seed": payload.seed,
        },
        safety_notes=[
            "Benchmark is a schema and persistence skeleton only.",
            "No live broker route, autonomous order path, or real-money execution exists.",
            "Promotion requires replay, point-in-time, outcome-label, slippage, and ACP gates.",
        ],
    )
    storage.save_behavior_benchmark_run(run)
    audit("info", f"Behavior mock benchmark completed for {payload.symbol} {payload.timeframe}", "behavior")
    return envelope(run)


@app.get("/api/v1/behavior/benchmark/report/current")
async def behavior_benchmark_report_current(symbol: str = "NIFTY-MOCK"):
    report = _build_and_save_benchmark_report(symbol)
    return envelope(report)


@app.post("/api/v1/behavior/benchmark/report/run")
async def behavior_benchmark_report_run(symbol: str = "NIFTY-MOCK"):
    report = _build_and_save_benchmark_report(symbol)
    audit(
        "warning" if not report.promotion_allowed else "info",
        f"Behavior benchmark report for {report.symbol}: promotion_allowed={report.promotion_allowed}",
        "behavior_release",
    )
    return envelope(report)


@app.get("/api/v1/behavior/benchmark/reports")
async def behavior_benchmark_reports(symbol: str | None = None):
    return envelope(storage.list_behavior_benchmark_reports(_normalize_symbol(symbol) if symbol else None))


@app.get("/api/v1/behavior/benchmark/reports/{report_id}")
async def behavior_benchmark_report_get(report_id: str):
    report = storage.load_behavior_benchmark_report(report_id)
    if report is None:
        raise api_error(404, "behavior_benchmark_report_not_found", f"Behavior benchmark report not found: {report_id}")
    return envelope(report)


@app.get("/api/v1/behavior/benchmark/report/drilldown/current")
async def behavior_benchmark_drilldown_current(symbol: str = "NIFTY-MOCK"):
    report = _build_and_save_benchmark_report(symbol)
    return envelope(build_benchmark_drilldown(report))


@app.get("/api/v1/behavior/benchmark/reports/{report_id}/drilldown")
async def behavior_benchmark_report_drilldown(report_id: str):
    report = storage.load_behavior_benchmark_report(report_id)
    if report is None:
        raise api_error(404, "behavior_benchmark_report_not_found", f"Behavior benchmark report not found: {report_id}")
    return envelope(build_benchmark_drilldown(report))


@app.get("/api/v1/behavior/benchmark/scenario-coverage/current")
async def behavior_scenario_coverage_current(symbol: str = "NIFTY-MOCK"):
    return envelope(_build_and_save_behavior_scenario_coverage(symbol))


@app.post("/api/v1/behavior/benchmark/scenario-coverage/run")
async def behavior_scenario_coverage_run(symbol: str = "NIFTY-MOCK"):
    coverage = _build_and_save_behavior_scenario_coverage(symbol)
    audit(
        "info",
        f"Behavior scenario coverage for {coverage.symbol}: coverage_score={coverage.coverage_score_pct}",
        "behavior_release",
    )
    return envelope(coverage)


@app.get("/api/v1/behavior/benchmark/scenario-coverage/reports")
async def behavior_scenario_coverage_reports(symbol: str | None = None):
    normalized = _normalize_symbol(symbol) if symbol else None
    return envelope(storage.list_behavior_scenario_coverage_reports(normalized))


@app.get("/api/v1/behavior/benchmark/scenario-coverage/reports/{coverage_id}")
async def behavior_scenario_coverage_get(coverage_id: str):
    coverage = storage.load_behavior_scenario_coverage_report(coverage_id)
    if coverage is None:
        raise api_error(404, "behavior_scenario_coverage_not_found", f"Behavior scenario coverage report not found: {coverage_id}")
    return envelope(coverage)


@app.get("/api/v1/behavior/benchmark/reports/{report_id}/scenario-coverage")
async def behavior_benchmark_report_scenario_coverage(report_id: str):
    report = storage.load_behavior_benchmark_report(report_id)
    if report is None:
        raise api_error(404, "behavior_benchmark_report_not_found", f"Behavior benchmark report not found: {report_id}")
    coverage = build_behavior_scenario_coverage(report)
    storage.save_behavior_scenario_coverage_report(coverage)
    return envelope(coverage)


@app.get("/api/v1/behavior/release/mock-to-replay/checklist")
async def behavior_mock_to_replay_checklist(symbol: str = "NIFTY-MOCK", manual_approval: bool = False):
    report = _build_and_save_benchmark_report(symbol)
    approved_record = storage.latest_active_release_approval(_normalize_symbol(symbol), report.report_id, now_iso())
    checklist = build_mock_to_replay_checklist(
        symbol=_normalize_symbol(symbol),
        benchmark_report=report,
        manual_approval=manual_approval or approved_record is not None,
    )
    storage.save_release_checklist(checklist)
    return envelope(checklist)


@app.get("/api/v1/behavior/release/evidence/current")
async def behavior_release_evidence_current(symbol: str = "NIFTY-MOCK", approval_id: str | None = None):
    return envelope(_build_and_save_release_evidence_bundle(symbol, approval_id))


@app.post("/api/v1/behavior/release/evidence/export")
async def behavior_release_evidence_export(symbol: str = "NIFTY-MOCK", approval_id: str | None = None):
    bundle = _build_and_save_release_evidence_bundle(symbol, approval_id)
    audit(
        "warning",
        f"Release evidence bundle exported for {bundle.symbol}: bundle_id={bundle.bundle_id}",
        "behavior_release",
    )
    return envelope(bundle)


@app.get("/api/v1/behavior/release/evidence/bundles")
async def behavior_release_evidence_bundles(symbol: str | None = None):
    return envelope(storage.list_release_evidence_bundles(_normalize_symbol(symbol) if symbol else None))


@app.get("/api/v1/behavior/release/evidence/bundles/{bundle_id}")
async def behavior_release_evidence_bundle_get(bundle_id: str):
    bundle = storage.load_release_evidence_bundle(bundle_id)
    if bundle is None:
        raise api_error(404, "release_evidence_bundle_not_found", f"Release evidence bundle not found: {bundle_id}")
    return envelope(bundle)


@app.post("/api/v1/behavior/release/evidence/artifact/export")
async def behavior_release_evidence_artifact_export(payload: ReleaseEvidenceArtifactExportRequest):
    artifact = _export_release_evidence_artifact(payload)
    audit(
        "warning",
        f"Release evidence artifact exported for {artifact.symbol}: artifact_id={artifact.artifact_id}",
        "behavior_release",
    )
    return envelope(artifact)


@app.get("/api/v1/behavior/release/evidence/artifacts")
async def behavior_release_evidence_artifacts(symbol: str | None = None):
    return envelope(storage.list_release_evidence_artifacts(_normalize_symbol(symbol) if symbol else None))


@app.get("/api/v1/behavior/release/evidence/artifacts/{artifact_id}")
async def behavior_release_evidence_artifact_get(artifact_id: str):
    artifact = storage.load_release_evidence_artifact(artifact_id)
    if artifact is None:
        raise api_error(404, "release_evidence_artifact_not_found", f"Release evidence artifact not found: {artifact_id}")
    return envelope(artifact)


@app.get("/api/v1/behavior/release/evidence/artifacts/{artifact_id}/verify")
async def behavior_release_evidence_artifact_verify(artifact_id: str):
    artifact = storage.load_release_evidence_artifact(artifact_id)
    if artifact is None:
        raise api_error(404, "release_evidence_artifact_not_found", f"Release evidence artifact not found: {artifact_id}")
    return envelope(_verify_release_evidence_artifact(artifact))


@app.post("/api/v1/behavior/release/approval/request")
async def behavior_release_approval_request(payload: ReleaseApprovalRequest):
    record = _build_release_approval_request(payload)
    audit(
        "warning",
        f"Mock-to-replay approval requested for {record.symbol}: approval_id={record.approval_id}",
        "behavior_release",
    )
    return envelope(record)


@app.post("/api/v1/behavior/release/approvals/{approval_id}/approve")
async def behavior_release_approval_approve(approval_id: str, payload: ReleaseApprovalDecisionRequest):
    record = _approve_release_approval(approval_id, payload)
    audit(
        "warning",
        f"Mock-to-replay approval approved for {record.symbol}: approval_id={record.approval_id}",
        "behavior_release",
    )
    return envelope(record)


@app.post("/api/v1/behavior/release/approvals/{approval_id}/reject")
async def behavior_release_approval_reject(approval_id: str, payload: ReleaseApprovalDecisionRequest):
    record = _reject_release_approval(approval_id, payload)
    audit(
        "warning",
        f"Mock-to-replay approval rejected for {record.symbol}: approval_id={record.approval_id}",
        "behavior_release",
    )
    return envelope(record)


@app.get("/api/v1/behavior/release/approvals")
async def behavior_release_approvals(symbol: str | None = None, status: str | None = None):
    return envelope(storage.list_release_approvals(_normalize_symbol(symbol) if symbol else None, status))


@app.get("/api/v1/behavior/release/approvals/{approval_id}")
async def behavior_release_approval_get(approval_id: str):
    record = storage.load_release_approval(approval_id)
    if record is None:
        raise api_error(404, "release_approval_not_found", f"Release approval not found: {approval_id}")
    return envelope(record)


@app.get("/api/v1/behavior/release/checklists")
async def behavior_release_checklists(symbol: str | None = None):
    return envelope(storage.list_release_checklists(_normalize_symbol(symbol) if symbol else None))


@app.get("/api/v1/behavior/release/checklists/{checklist_id}")
async def behavior_release_checklist_get(checklist_id: str):
    checklist = storage.load_release_checklist(checklist_id)
    if checklist is None:
        raise api_error(404, "release_checklist_not_found", f"Release checklist not found: {checklist_id}")
    return envelope(checklist)


@app.get("/api/v1/behavior/benchmark/{run_id}")
async def behavior_benchmark_get(run_id: str):
    run = storage.load_behavior_benchmark_run(run_id)
    if run is None:
        raise api_error(404, "behavior_benchmark_not_found", f"Behavior benchmark not found: {run_id}")
    return envelope(run)


@app.get("/api/v1/behavior/benchmark/{run_id}/status")
async def behavior_benchmark_status(run_id: str):
    run = storage.load_behavior_benchmark_run(run_id)
    if run is None:
        raise api_error(404, "behavior_benchmark_not_found", f"Behavior benchmark not found: {run_id}")
    return envelope(run)


@app.get("/api/v1/behavior/replay/{run_id}")
async def behavior_replay(run_id: str):
    analysis = storage.load_behavior_analysis(run_id)
    if analysis is None:
        raise api_error(404, "behavior_analysis_not_found", f"Behavior analysis not found: {run_id}")
    seed = uuid5(NAMESPACE_URL, f"tradevision:behavior-replay:{run_id}").int % 1_000_000
    events = [
        event.model_copy(update={"symbol": analysis.symbol})
        for event in deterministic_events(seed, f"behavior-{run_id}", 8)
    ]
    record = BehaviorReplayRecord(
        run_id=run_id,
        symbol=analysis.symbol,
        similar_day_ids=list(analysis.result.get("similar_day_ids", [])),
        replay_snapshot_id=analysis.result.get("replay_snapshot_id"),
        events=events,
        deterministic=True,
    )
    return envelope(record)


@app.get("/api/audit/events")
async def get_audit_events():
    return envelope(AUDIT_EVENTS)


@app.get("/api/audit/integrity")
async def get_audit_integrity():
    return envelope(storage.audit_integrity_report())


@app.get("/api/simulation/integrity")
async def get_simulation_integrity():
    return envelope(
        SimulationIntegrityReport(
            data_source="synthetic_mock",
            generation_timestamp=now_iso(),
            model_version="mock-v0.1",
            calibration_date=None,
            assumptions=["No live broker route", "Synthetic prices", "Mock microstructure", "Narrative is read-only"],
            confidence_interval=(0.52, 0.72),
            disclaimer="Research and interface validation only. Not investment advice. No real money connected.",
        )
    )


@app.get("/api/knowledge/graph")
async def get_knowledge_graph():
    if not KNOWLEDGE_GRAPH_PATH.exists():
        raise api_error(503, "graph_unavailable", f"Knowledge graph not found at {KNOWLEDGE_GRAPH_PATH}", retryable=True)
    return envelope(json.loads(KNOWLEDGE_GRAPH_PATH.read_text(encoding="utf-8")))

# BEGIN AFRE_V3_OPT_IN_ADDITION
from .orb.adaptive.integration import mount as _mount_adaptive_orb
_mount_adaptive_orb(app)
# END AFRE_V3_OPT_IN_ADDITION
