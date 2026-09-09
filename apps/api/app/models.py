from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field


T = TypeVar("T")


class SourceMode(str, Enum):
    MOCK = "mock"
    SIMULATION = "simulation"
    REPLAY = "replay"
    PAPER = "paper"
    LIVE = "live"


class SystemModeValue(str, Enum):
    MOCK = "MOCK"
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"
    PAPER = "PAPER"
    LIVE = "LIVE"


class CapabilityStatus(str, Enum):
    RESERVED = "reserved"
    MOCK = "mock"
    BETA = "beta"
    PRODUCTION = "production"


class ResponseMeta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    event_time: str
    arrival_time: str
    source: SourceMode = SourceMode.MOCK
    quality_score: float = Field(ge=0.0, le=1.0)
    trust_score: float = Field(ge=0.0, le=1.0)
    replay_snapshot_id: str | None = None
    capability_status: CapabilityStatus = CapabilityStatus.MOCK


class ApiEnvelope(BaseModel, Generic[T]):
    meta: ResponseMeta
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    retryable: bool = False
    mode: SystemModeValue = SystemModeValue.MOCK


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class HealthState(BaseModel):
    status: Literal["alive"]
    service: str = "trade-vision-api"
    version: str = "0.1.0"


class OperatorIdentity(BaseModel):
    actor_id: str
    role: Literal["viewer", "operator", "risk_manager", "admin"]
    auth_mode: Literal["mock_header"]
    permissions: list[str]
    live_trading_allowed: bool = False


class RbacDecision(BaseModel):
    allowed: bool
    required_roles: list[str]
    actor: OperatorIdentity
    reason: str


class PanelBounds(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=12)
    h: int = Field(ge=1, le=12)


class PanelConfig(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    panel_type: str = Field(min_length=1, max_length=80)
    module: str = Field(min_length=1, max_length=80)
    bounds: PanelBounds
    state: dict[str, Any] = Field(default_factory=dict)
    capability_requirement: str


class WorkspaceLayout(BaseModel):
    version: int = Field(default=1, ge=1)
    workspace_id: str = Field(min_length=1, max_length=80)
    active_workspace: str = Field(min_length=1, max_length=80)
    panels: list[PanelConfig]
    global_settings: dict[str, Any] = Field(default_factory=dict)
    updated_at: str


class ReadyState(BaseModel):
    status: Literal["ready", "not_ready"]
    not_ready: list[str]
    required_capabilities: int
    total_capabilities: int


class StorageStatus(BaseModel):
    status: Literal["ready", "error"]
    db_path: str
    audit_events: int
    replay_sessions: int
    replay_events: int
    capability_snapshots: int
    point_in_time_snapshots: int = 0
    feature_versions: int = 0
    workspace_layouts: int = 0
    request_logs: int = 0
    behavior_analysis_results: int = 0
    behavior_memory_records: int = 0
    behavior_benchmark_runs: int = 0
    behavior_safety_reports: int = 0
    memory_quarantines: int = 0
    golden_replay_fixtures: int = 0
    behavior_benchmark_reports: int = 0
    release_checklists: int = 0
    release_approvals: int = 0
    release_evidence_bundles: int = 0
    release_evidence_artifacts: int = 0
    behavior_scenario_coverage_reports: int = 0
    executor_transport_outbox: int = 0


class RequestLogRecord(BaseModel):
    request_id: str
    run_id: str
    decision_id: str | None
    timestamp: str
    method: str
    path: str
    status_code: int
    latency_ms: float
    actor_id: str
    role: str
    mode: SystemModeValue
    error_code: str | None = None


class ObservabilityStatus(BaseModel):
    status: Literal["ready"]
    log_format: Literal["json"]
    request_count: int
    error_count: int
    p95_latency_ms: float
    recent_events: list[RequestLogRecord]
    required_fields: list[str]


class SystemMode(BaseModel):
    mode: SystemModeValue
    display_label: str
    immutable: bool
    allows_live_orders: bool
    allows_broker_credentials: bool
    watermark_text: str


class TimeProviderState(BaseModel):
    time_mode: Literal["realtime", "virtual", "paused", "stepped"]
    virtual_timestamp_ns: int
    wall_clock_time: str
    drift_ms: float
    source: Literal["mock", "system", "ntp", "ptp", "exchange_sync"]
    sequence_number: int


class KillSwitchState(BaseModel):
    state: Literal["armed", "triggered", "reset_pending"]
    reason: str | None
    source: Literal["user_ui", "risk_engine", "circuit_breaker", "heartbeat_timeout", "system"] | None
    actor_id: str | None
    triggered_at: str | None
    blocks_order_paths: bool


class KillSwitchTriggerRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
    source: Literal["user_ui", "risk_engine", "circuit_breaker", "heartbeat_timeout", "system"] = "user_ui"
    actor_id: str = Field(min_length=1, max_length=80)


class KillSwitchResetRequest(BaseModel):
    actor_id: str = Field(min_length=1, max_length=80)
    confirmation: Literal["RESET_MOCK_KILL_SWITCH"]


class CapabilityManifestItem(BaseModel):
    name: str
    status: CapabilityStatus
    ui_module: str
    backend_services: list[str]
    required_data_contracts: list[str]
    mock_replacement_strategy: str
    required_for_startup: bool
    promotion_gates: list[str]


class CapabilityManifest(BaseModel):
    capabilities: list[CapabilityManifestItem]


class MarketEvent(BaseModel):
    event_id: str
    parent_event_id: str | None
    virtual_timestamp_ns: int
    source_mode: SystemModeValue
    sequence_number: int
    symbol: str
    payload: dict[str, Any]
    watermark: str | None


class PipelineStep(BaseModel):
    name: str
    status: CapabilityStatus
    latency_ms: float
    message: str


class PipelineState(BaseModel):
    mode: SystemModeValue
    steps: list[PipelineStep]
    fast_path_enabled: bool
    live_order_routing_enabled: bool


class EngineVote(BaseModel):
    engine: str
    vote: Literal["LONG", "SHORT", "WAIT", "REDUCE", "BLOCK", "PASS"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class NarrativeExplanation(BaseModel):
    text: str
    read_only: bool
    cannot_execute_orders: bool
    cannot_override_risk: bool


class NarrativeAuditEntry(BaseModel):
    timestamp: str
    narrative_id: str
    model_version: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation_chain: list[str]
    human_reviewed: bool
    reviewer_id: str | None


class CognitionDecision(BaseModel):
    final_action: Literal["TRADE_PLAN_CANDIDATE", "WAIT", "REDUCE", "BLOCK"]
    confidence: float = Field(ge=0.0, le=1.0)
    votes: list[EngineVote]
    narrative: NarrativeExplanation
    audit: list[NarrativeAuditEntry]


class PortfolioState(BaseModel):
    gross_exposure_pct: float
    sector_concentration_pct: float
    correlation_cluster_risk: Literal["low", "medium", "high"]
    drawdown_governor: Literal["armed", "triggered"]
    live_positions_enabled: bool


class MockRiskReport(BaseModel):
    hypothetical_exposure: float
    max_drawdown_simulated: float
    var95: float
    concentration_risk: dict[str, float]
    kill_switch_distance: float
    disclaimer: str


class MarketDNAState(BaseModel):
    price_score: float
    volatility_score: float
    options_score: float
    breadth_score: float
    event_score: float
    flow_score: float
    calibrated_breakout_probability: float
    calibrated_failure_probability: float
    status: CapabilityStatus


class MicrostructureState(BaseModel):
    order_book_imbalance: float
    sweep_events: int
    absorption_events: int
    spoofing_warnings: int
    hidden_liquidity_suspicion: float
    imbalance_propagation_score: float
    status: CapabilityStatus


class ReplayStartRequest(BaseModel):
    scenario_id: str = Field(default="mock_opening_drive")
    seed: int = Field(default=42, ge=0)


class ReplaySeekRequest(BaseModel):
    session_id: str
    virtual_timestamp_ns: int


class ReplayControlRequest(BaseModel):
    session_id: str


class ReplayStepRequest(BaseModel):
    session_id: str
    steps: int = Field(default=1, ge=1, le=100)


class ReplaySnapshot(BaseModel):
    session_id: str
    scenario_id: str
    seed: int
    state: Literal["idle", "playing", "paused", "stepped"]
    current_timestamp_ns: int
    events: list[MarketEvent]


class ReplayArchiveSummary(BaseModel):
    session_id: str
    scenario_id: str
    seed: int
    state: str
    created_at: str
    event_count: int


class ExecutionSimState(BaseModel):
    slippage_pct: float
    queue_position_estimate: float
    partial_fill_probability: float
    adverse_selection_risk: Literal["low", "medium", "high"]
    simulation_only: bool


class OrderPathStatus(BaseModel):
    live_order_routing_enabled: bool
    simulation_only: bool
    broker_credentials_configured: bool
    kill_switch_state: Literal["armed", "triggered", "reset_pending"]
    accepts_simulated_orders: bool
    blocks_reason: str | None
    required_gates: list[str]


class SimulatedOrderRequest(BaseModel):
    client_order_id: str = Field(min_length=1, max_length=80)
    symbol: str = Field(min_length=1, max_length=40)
    side: Literal["BUY", "SELL"]
    quantity: int = Field(ge=1, le=100_000)
    order_type: Literal["MARKET", "LIMIT"]
    limit_price: float | None = Field(default=None, ge=0.0)
    mode_confirmation: Literal["MOCK_ONLY"]


class SimulatedOrderResult(BaseModel):
    client_order_id: str
    accepted: bool
    decision: Literal["SIMULATED_ACCEPTED", "BLOCKED_BY_KILL_SWITCH", "REJECTED_UNSAFE_MODE", "REJECTED_VALIDATION"]
    reason: str
    simulated_order_id: str | None
    live_route_attempted: bool
    kill_switch_checked: bool
    mode: SystemModeValue


class DataQualityReport(BaseModel):
    lookback_years: float
    survivorship_bias: bool
    look_ahead_leakage: bool
    sample_size: int
    notes: list[str]


class MockIngestRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    seed: int = Field(default=42, ge=0)
    bars: int = Field(default=64, ge=1, le=5000)


class PointInTimeSnapshot(BaseModel):
    snapshot_id: str
    symbol: str
    source_mode: SystemModeValue
    seed: int
    as_of_timestamp_ns: int
    created_at: str
    schema_version: str
    payload_hash: str
    payload: dict[str, Any]
    immutable: bool = True


class MockIngestResult(BaseModel):
    snapshot: PointInTimeSnapshot
    feature_versions: list["FeatureVersionRecord"]


class FeatureVersionRecord(BaseModel):
    feature_hash: str
    name: str
    schema_version: str
    pipeline_version: str
    source_commit: str
    created_at: str
    input_snapshot_id: str
    parameters: dict[str, Any]


TimeframeValue = Literal["1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"]


class CandleBar(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    timeframe: TimeframeValue
    timestamp_ns: int = Field(ge=0)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float | None = Field(default=None, ge=0)
    source: Literal["mock", "snapshot", "legacy_reference", "replay", "external_stub", "user_csv"] = "mock"
    sequence_number: int = Field(ge=1)


class CandleSeries(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    timeframe: TimeframeValue
    bars: list[CandleBar] = Field(default_factory=list)
    snapshot_id: str | None = None
    schema_version: str = "candles.v1"


class BehaviorDataAdapterManifest(BaseModel):
    adapter_version: str
    source_roots: list[str]
    supported_inputs: list[str]
    supported_timeframes: list[TimeframeValue]
    output_contract: Literal["CandleSeries"]
    production_rules: list[str]
    runtime_dependency_on_legacy_stock_app: bool = False


class BehaviorDataAdapterRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=42, ge=0)
    bars: int = Field(default=64, ge=1, le=5000)
    snapshot_id: str | None = None


class BehaviorDataAdapterResult(BaseModel):
    adapter_version: str
    source_snapshot_id: str
    source_payload_hash: str
    series: CandleSeries
    warnings: list[str] = Field(default_factory=list)
    runtime_dependency_on_legacy_stock_app: bool = False


class BehaviorOhlcvImportRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "1m"
    csv_text: str = Field(min_length=20, max_length=1_500_000)
    timestamp_column: str = "timestamp"
    date_column: str | None = None
    time_column: str | None = None
    timezone_offset_minutes: int = Field(default=0, ge=-720, le=840)
    open_column: str = "open"
    high_column: str = "high"
    low_column: str = "low"
    close_column: str = "close"
    volume_column: str = "volume"
    persist_snapshot: bool = False
    decision_time_ns: int | None = Field(default=None, ge=0)


class BehaviorOhlcvImportResult(BaseModel):
    import_version: str
    symbol: str
    timeframe: TimeframeValue
    row_count: int
    parsed_bar_count: int
    persisted_snapshot_id: str | None
    payload_hash: str
    series: CandleSeries
    quality: "BehaviorDataQualityResult"
    point_in_time: "PointInTimeGuardResult"
    warnings: list[str] = Field(default_factory=list)
    safe_for_research: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    runtime_dependency_on_legacy_stock_app: bool = False


class BehaviorDataQualityIssue(BaseModel):
    code: str
    severity: Literal["info", "warning", "blocker"]
    message: str
    sequence_number: int | None = None
    timestamp_ns: int | None = None


class BehaviorDataQualityResult(BaseModel):
    symbol: str
    timeframe: TimeframeValue
    checked_at: str
    total_bars: int
    valid_bars: int
    data_quality_score: float = Field(ge=0.0, le=1.0)
    missing_volume_count: int
    invalid_ohlc_count: int
    duplicate_timestamp_count: int
    non_monotonic_count: int
    gap_count: int
    session_closure_gap_count: int = 0
    abnormal_print_count: int
    split_suspect_count: int
    volume_matching_enabled: bool
    blocks_trade: bool
    issues: list[BehaviorDataQualityIssue]


class PointInTimeGuardRequest(BaseModel):
    series: CandleSeries
    decision_time_ns: int = Field(ge=0)
    execution_time_ns: int | None = Field(default=None, ge=0)
    source_timeframe: TimeframeValue


class PointInTimeGuardResult(BaseModel):
    symbol: str
    source_timeframe: TimeframeValue
    decision_time_ns: int
    execution_time_ns: int | None
    timeframe_duration_ns: int
    allowed_bars: int
    blocked_bars: int
    future_bar_blocked: int
    incomplete_candle_blocked: int
    latest_allowed_timestamp_ns: int | None
    passed: bool
    blocks_trade: bool
    reasons: list[str]


class TimeframeAlignmentRecord(BaseModel):
    timeframe: TimeframeValue
    input_bars: int
    usable_bars: int
    blocked_future_bars: int
    blocked_incomplete_bars: int
    latest_closed_timestamp_ns: int | None
    latest_closed_candle_close_ns: int | None
    aligned: bool
    reason: str


class TimeframeSyncRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    decision_time_ns: int = Field(ge=0)
    execution_time_ns: int | None = Field(default=None, ge=0)
    series: list[CandleSeries]
    required_timeframes: list[TimeframeValue] = Field(default_factory=list)


class TimeframeSyncResult(BaseModel):
    symbol: str
    decision_time_ns: int
    execution_time_ns: int | None
    required_timeframes: list[TimeframeValue]
    records: list[TimeframeAlignmentRecord]
    usable_cutoff_by_timeframe: dict[str, int | None]
    latest_common_close_time_ns: int | None
    passed: bool
    blocks_trade: bool
    reasons: list[str]


class CausalFeatureDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_timeframe: TimeframeValue
    required_fields: list[str] = Field(default_factory=list)
    available_after_ns: int | None = Field(default=None, ge=0)
    depends_on_full_candle: bool = True
    uses_future_data: bool = False
    description: str = ""


class CausalFeatureWhitelist(BaseModel):
    whitelist_version: str
    allowed_feature_names: list[str]
    forbidden_fields: list[str]
    invariant: str


class CausalFeatureValidationRequest(BaseModel):
    decision_time_ns: int = Field(ge=0)
    execution_time_ns: int | None = Field(default=None, ge=0)
    features: list[CausalFeatureDefinition]
    timeframe_sync: TimeframeSyncResult | None = None


class CausalFeatureValidationResult(BaseModel):
    whitelist_version: str
    decision_time_ns: int
    feature_count: int
    allowed_features: list[str]
    blocked_features: list[str]
    issues: list[str]
    passed: bool
    blocks_trade: bool


CandleDirection = Literal["bullish", "bearish", "doji"]
MarketConditionValue = Literal[
    "opening_drive_continuation",
    "opening_drive_reversal",
    "range_balance_day",
    "breakout_day",
    "fake_breakout",
    "vwap_rejection",
    "vwap_support_trend",
    "absorption",
    "distribution",
    "accumulation",
    "compression_before_expansion",
    "choppy_avoid",
    "manipulated_looking",
    "unclassified",
]


class CandleAnatomyRequest(BaseModel):
    series: CandleSeries
    atr_period: int = Field(default=14, ge=2, le=100)
    volume_z_window: int = Field(default=20, ge=2, le=200)
    wick_cluster_lookback: int = Field(default=5, ge=2, le=50)
    breakout_reference_high: float | None = Field(default=None, gt=0)
    breakout_reference_low: float | None = Field(default=None, gt=0)


class CandleAnatomyFeature(BaseModel):
    symbol: str
    timeframe: TimeframeValue
    timestamp_ns: int
    sequence_number: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    direction: CandleDirection
    candle_range: float
    body_size: float
    body_pct: float
    upper_wick_pct: float
    lower_wick_pct: float
    close_location_value: float
    range_atr: float
    volume_z: float | None
    body_to_volume_efficiency: float | None
    effort_vs_result: float | None
    wick_cluster_count: int
    is_inside_bar: bool
    is_outside_bar: bool
    gap_pct: float
    follow_through_count: int
    failed_follow_through: bool
    candle_structure_types: list[str]


class CandleAnatomyResult(BaseModel):
    calculation_version: str
    symbol: str
    timeframe: TimeframeValue
    total_candles: int
    features: list[CandleAnatomyFeature]
    latest: CandleAnatomyFeature | None
    summary: dict[str, Any]


class ChartReasoningRequest(BaseModel):
    series: CandleSeries
    atr_period: int = Field(default=14, ge=2, le=100)
    bb_period: int = Field(default=20, ge=5, le=200)
    hurst_window: int = Field(default=64, ge=16, le=512)
    vcp_window: int = Field(default=12, ge=5, le=60)
    minimum_bars: int = Field(default=30, ge=9, le=500)


class ChartReasoningGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warn", "block"]
    evidence: str
    remediation: str | None = None


class ChartReasoningReport(BaseModel):
    reasoning_version: str
    symbol: str
    timeframe: TimeframeValue
    closed_candle_only: bool
    source_bar_count: int
    latest_timestamp_ns: int | None = None
    latest_sequence_number: int | None = None
    trend_health: str
    chop_risk: str
    rejection_index: float = Field(ge=0.0)
    rubber_band_risk: str
    momentum_cleanliness: str
    mean_reversion_state: str
    time_symmetry_cluster: str
    fractal_noise_score: float = Field(ge=0.0, le=1.0)
    volatility_regime: str
    hv_percentile: float = Field(ge=0.0, le=100.0)
    bb_width_percentile: float = Field(ge=0.0, le=100.0)
    vcp_state: str
    contraction_count: int = Field(ge=0)
    volume_dryup_score: float = Field(ge=0.0, le=1.0)
    trend_persistence_score: float = Field(ge=0.0, le=1.0)
    hurst_exponent: float = Field(ge=0.0, le=1.0)
    fractal_dimension: float = Field(ge=1.0, le=2.0)
    micro_trend_slope: float
    candle_acceleration: float
    candle_mass_index: float = Field(ge=0.0)
    ema_distance_atr: float
    ema_tangled: bool
    hidden_bullish_divergence: bool
    hidden_bearish_divergence: bool
    oscillator_exhaustion: str
    atr_percentile: float = Field(ge=0.0, le=100.0)
    current_atr: float = Field(ge=0.0)
    current_bb_width: float = Field(ge=0.0)
    no_future_leakage: bool
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    reasons: list[str]
    failure_questions: list[str]
    gates: list[ChartReasoningGate]


class ConditionClassifierRequest(BaseModel):
    series: CandleSeries
    anatomy: CandleAnatomyResult | None = None
    vwap: float | None = Field(default=None, gt=0)
    opening_range_high: float | None = Field(default=None, gt=0)
    opening_range_low: float | None = Field(default=None, gt=0)
    support_level: float | None = Field(default=None, gt=0)
    resistance_level: float | None = Field(default=None, gt=0)
    session_phase: str = "unknown"


class CandleConditionRecord(BaseModel):
    timestamp_ns: int
    sequence_number: int
    dominant_condition: MarketConditionValue
    condition_tags: list[MarketConditionValue]
    candle_behavior: str
    pattern_family: str
    trap_probability: float = Field(ge=0.0, le=1.0)
    absorption_score: float = Field(ge=0.0, le=1.0)
    continuation_quality: float = Field(ge=0.0, le=1.0)
    uncertainty_score: float = Field(ge=0.0, le=1.0)
    blocks_trade: bool
    no_trade_reason: str | None = None
    reasons: list[str]


class ConditionClassifierResult(BaseModel):
    classifier_version: str
    symbol: str
    timeframe: TimeframeValue
    records: list[CandleConditionRecord]
    latest: CandleConditionRecord | None
    market_state: MarketConditionValue
    condition_tags: list[MarketConditionValue]
    final_signal_bias: Literal["long", "short", "wait", "avoid"]
    blocks_trade: bool
    no_trade_reason: str | None = None
    reason_tree: dict[str, str]


TradeDirection = Literal["long", "short", "neutral"]
LevelState = Literal[
    "above",
    "below",
    "inside",
    "rejecting",
    "reclaiming",
    "breaking_up",
    "breaking_down",
    "unknown",
]


class VwapOrbCprContextRequest(BaseModel):
    series: CandleSeries
    decision_time_ns: int | None = Field(default=None, ge=0)
    previous_day_high: float | None = Field(default=None, gt=0)
    previous_day_low: float | None = Field(default=None, gt=0)
    previous_close: float | None = Field(default=None, gt=0)
    vwap: float | None = Field(default=None, gt=0)
    opening_range_high: float | None = Field(default=None, gt=0)
    opening_range_low: float | None = Field(default=None, gt=0)
    volume_profile_hvn: float | None = Field(default=None, gt=0)
    volume_profile_lvn: float | None = Field(default=None, gt=0)


class VwapOrbCprContextResult(BaseModel):
    context_version: str
    symbol: str
    timeframe: TimeframeValue
    latest_close: float | None
    calculated_vwap: float | None
    price_vs_vwap_pct: float | None
    vwap_state: LevelState
    opening_range_high: float | None
    opening_range_low: float | None
    opening_range_state: LevelState
    cpr_pivot: float | None
    cpr_bc: float | None
    cpr_tc: float | None
    cpr_state: LevelState
    pdh_state: LevelState
    pdl_state: LevelState
    vpd_state: Literal["at_hvn", "at_lvn", "above_hvn", "below_lvn", "between_nodes", "unknown"]
    support_resistance_flags: list[str]
    level_respect_score: float = Field(ge=0.0, le=1.0)
    blocks_trade: bool
    reasons: list[str]


class HTFConfirmationRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    decision_time_ns: int = Field(ge=0)
    direction: TradeDirection = "long"
    higher_timeframe_series: list[CandleSeries]


class HTFConfirmationRecord(BaseModel):
    timeframe: TimeframeValue
    usable_bars: int
    latest_close: float | None
    first_close: float | None
    slope_pct: float | None
    bias: Literal["bullish", "bearish", "neutral", "unavailable"]
    confirmed: bool
    reason: str


class HTFConfirmationResult(BaseModel):
    context_version: str
    symbol: str
    decision_time_ns: int
    direction: TradeDirection
    records: list[HTFConfirmationRecord]
    confirmed: bool
    blocks_trade: bool
    confidence_adjustment: float
    reasons: list[str]


class GapContextRequest(BaseModel):
    series: CandleSeries
    previous_close: float = Field(gt=0)
    atr: float | None = Field(default=None, gt=0)


class GapContextResult(BaseModel):
    context_version: str
    symbol: str
    timeframe: TimeframeValue
    opening_price: float | None
    latest_close: float | None
    previous_close: float
    gap_pct: float | None
    gap_type: Literal["flat_gap", "gap_up", "gap_down", "large_gap_up", "large_gap_down", "unknown"]
    gap_fill_probability_pct: float
    gap_trap_risk: float = Field(ge=0.0, le=1.0)
    blocks_trade: bool
    reasons: list[str]


class MarketContextRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    direction: TradeDirection = "long"
    stock_return_pct: float
    index_return_pct: float
    sector_return_pct: float
    banknifty_return_pct: float | None = None
    global_risk_score: float = Field(default=0.25, ge=0.0, le=1.0)


class MarketContextResult(BaseModel):
    context_version: str
    symbol: str
    direction: TradeDirection
    index_direction: Literal["up", "down", "flat"]
    sector_strength: Literal["strong", "neutral", "weak"]
    relative_strength_score: float = Field(ge=0.0, le=1.0)
    market_alignment: Literal["supports_long", "supports_short", "mixed", "avoid"]
    blocks_trade: bool
    reasons: list[str]


RecentSignalOutcome = Literal["WIN", "LOSS", "BREAKEVEN", "OPEN", "UNKNOWN"]


class MarketRegimeFeedbackRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    direction: TradeDirection = "long"
    stock_return_pct: float = 0.0
    index_return_pct: float | None = None
    banknifty_return_pct: float | None = None
    sector_return_pct: float | None = None
    advance_decline_ratio: float | None = Field(default=None, ge=0.0)
    sector_advance_decline_ratio: float | None = Field(default=None, ge=0.0)
    stock_returns_pct: list[float] = Field(default_factory=list)
    index_returns_pct: list[float] = Field(default_factory=list)
    sector_returns_pct: list[float] = Field(default_factory=list)
    setup_sample_count: int = Field(default=0, ge=0)
    setup_success_count: int = Field(default=0, ge=0)
    setup_failure_count: int = Field(default=0, ge=0)
    vwap_respect_count: int = Field(default=0, ge=0)
    vwap_sample_count: int = Field(default=0, ge=0)
    breakout_failure_count: int = Field(default=0, ge=0)
    recent_signal_outcomes: list[RecentSignalOutcome] = Field(default_factory=list)
    minimum_sample_size: int = Field(default=30, ge=1, le=1000)
    prior_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    prior_sample_weight: int = Field(default=20, ge=1, le=1000)


class MarketRegimeFeedbackGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warn", "block"]
    evidence: str
    remediation: str | None = None


class MarketRegimeFeedbackReport(BaseModel):
    feedback_version: str
    symbol: str
    timeframe: TimeframeValue
    direction: TradeDirection
    market_context_status: Literal["available", "partial", "unavailable"]
    trend_state: str
    breadth_state: str
    relative_strength_score: float = Field(ge=0.0, le=1.0)
    relative_strength_position: float = Field(ge=0.0, le=100.0)
    rolling_correlation_to_index: float = Field(ge=-1.0, le=1.0)
    leading_lagging_state: str
    prior_confidence: float = Field(ge=0.0, le=1.0)
    posterior_confidence: float = Field(ge=0.0, le=1.0)
    stock_specific_edge: float = Field(ge=-1.0, le=1.0)
    recent_failure_penalty: float = Field(ge=0.0, le=1.0)
    dynamic_confirmation_requirement: str
    cooldown_active: bool
    confidence_cap: Literal["WAIT", "WATCH", "PAPER_CANDIDATE_ALLOWED"]
    minimum_sample_pass: bool
    unavailable_reasons: list[str]
    allowed_live_updates: list[str]
    forbidden_live_updates: list[str]
    no_live_weight_mutation: bool
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    reasons: list[str]
    failure_questions: list[str]
    gates: list[MarketRegimeFeedbackGate]


class MarketStructureLiquidityRequest(BaseModel):
    series: CandleSeries
    bin_count: int = Field(default=24, ge=8, le=80)
    value_area_pct: float = Field(default=0.70, ge=0.50, le=0.90)
    atr_period: int = Field(default=14, ge=2, le=100)
    equal_level_tolerance_atr: float = Field(default=0.15, ge=0.01, le=1.00)
    minimum_bars: int = Field(default=30, ge=9, le=500)


class MarketStructureLiquidityGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warn", "block"]
    evidence: str
    remediation: str | None = None


class MarketStructureZone(BaseModel):
    zone_type: str
    direction: Literal["bullish", "bearish", "neutral"]
    low: float | None = None
    high: float | None = None
    source_sequence_number: int | None = None
    confirmed_after_timestamp_ns: int | None = None
    point_in_time_safe: bool = True
    reason: str


class MarketStructureLiquidityReport(BaseModel):
    structure_version: str
    symbol: str
    timeframe: TimeframeValue
    closed_candle_only: bool
    source_bar_count: int
    latest_timestamp_ns: int | None = None
    latest_sequence_number: int | None = None
    bin_count: int
    auction_state: str
    profile_shape: Literal["D", "P", "b", "thin", "unknown"]
    poc: float | None = None
    vah: float | None = None
    val: float | None = None
    poc_distance_atr: float = Field(ge=0.0)
    value_area_position: Literal["above_value", "inside_value", "below_value", "unknown"]
    hvn_levels: list[float]
    lvn_levels: list[float]
    hvn_lvn_context: str
    tpo_poc: float | None = None
    tpo_value_area_high: float | None = None
    tpo_value_area_low: float | None = None
    tpo_single_print_count: int = Field(ge=0)
    tpo_acceptance_state: str
    vsa_effort_result_state: str
    vsa_downgrade_active: bool
    volume_percentile: float = Field(ge=0.0, le=100.0)
    spread_percentile: float = Field(ge=0.0, le=100.0)
    close_location_value: float = Field(ge=0.0, le=1.0)
    liquidity_pool_detected: bool
    liquidity_pool_side: Literal["above_equal_highs", "below_equal_lows", "both", "none"]
    sweep_direction: Literal["up_sweep", "down_sweep", "none"]
    order_block_zone: MarketStructureZone | None = None
    fvg_zone: MarketStructureZone | None = None
    bos_choch_state: str
    wyckoff_phase: Literal["spring", "utad", "lps", "none"]
    trap_score: float = Field(ge=0.0, le=1.0)
    stop_hunt_score: float = Field(ge=0.0, le=1.0)
    confidence_cap: Literal["WAIT", "WATCH", "RESEARCH_CONTEXT_ONLY"]
    no_future_leakage: bool
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    reasons: list[str]
    failure_questions: list[str]
    gates: list[MarketStructureLiquidityGate]


class ExecutionEventOiRiskRequest(BaseModel):
    series: CandleSeries
    entry_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    target: float | None = Field(default=None, gt=0)
    intended_position_value: float = Field(default=100_000.0, ge=0.0)
    spread_pct: float | None = Field(default=None, ge=0.0, le=10.0)
    average_slippage_pct: float | None = Field(default=None, ge=0.0, le=10.0)
    depth_available: bool = False
    visible_depth_value: float | None = Field(default=None, ge=0.0)
    market_cap_class: Literal["largecap", "midcap", "smallcap", "unknown"] = "unknown"
    expected_move_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    event_context_status: Literal["available", "partial", "unavailable"] = "unavailable"
    days_to_earnings: int | None = Field(default=None, ge=0, le=365)
    macro_event_minutes: int | None = Field(default=None, ge=0, le=10080)
    expiry_day: bool = False
    options_context_status: Literal["available", "partial", "unavailable"] = "unavailable"
    max_pain: float | None = Field(default=None, gt=0)
    call_gamma_wall: float | None = Field(default=None, gt=0)
    put_gamma_wall: float | None = Field(default=None, gt=0)
    oi_concentration_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    iv_percentile: float | None = Field(default=None, ge=0.0, le=100.0)
    iv_skew: float | None = Field(default=None, ge=-100.0, le=100.0)
    minimum_bars: int = Field(default=30, ge=9, le=500)
    target_holding_minutes: int = Field(default=60, ge=1, le=1440)


class ExecutionEventOiRiskGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warn", "block"]
    evidence: str
    remediation: str | None = None


class ExecutionEventOiRiskReport(BaseModel):
    risk_version: str
    symbol: str
    timeframe: TimeframeValue
    closed_candle_only: bool
    source_bar_count: int
    latest_timestamp_ns: int | None = None
    latest_sequence_number: int | None = None
    entry_price: float
    target_move_pct: float | None = None
    stop_distance_pct: float | None = None
    fill_probability: float = Field(ge=0.0, le=1.0)
    slippage_risk: float = Field(ge=0.0, le=1.0)
    impact_cost_pct: float = Field(ge=0.0)
    liquidity_grade: Literal["A", "B", "C", "UNKNOWN"]
    execution_plan_status: Literal["PASS", "WATCH_ONLY", "BLOCKED", "RESEARCH_ONLY"]
    depth_context_status: Literal["available", "ohlcv_proxy", "unavailable"]
    event_context_status: Literal["available", "partial", "unavailable"]
    options_context_status: Literal["available", "partial", "unavailable"]
    single_tick_wick_risk: bool
    gap_through_entry_risk: bool
    event_risk_score: float = Field(ge=0.0, le=1.0)
    earnings_adjustment: Literal["none", "reduce_size", "watch_only", "unavailable"]
    expiry_pinning_risk: Literal["none", "moderate", "high", "unavailable"]
    expected_move_limit: Literal["within_expected_move", "target_beyond_expected_move", "unavailable"]
    expected_move_pct: float | None = None
    gamma_wall_context: str
    max_pain_magnet: str
    confidence_cap: Literal["WAIT", "WATCH", "RESEARCH_CONTEXT_ONLY"]
    unavailable_reasons: list[str]
    no_future_leakage: bool
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    reasons: list[str]
    failure_questions: list[str]
    gates: list[ExecutionEventOiRiskGate]


class PostEntryLifecycleRequest(BaseModel):
    series: CandleSeries
    direction: TradeDirection = "long"
    entry_sequence_number: int | None = Field(default=None, ge=0)
    entry_price: float | None = Field(default=None, gt=0)
    initial_stop_loss: float | None = Field(default=None, gt=0)
    target_1: float | None = Field(default=None, gt=0)
    target_2: float | None = Field(default=None, gt=0)
    atr: float | None = Field(default=None, gt=0)
    vwap: float | None = Field(default=None, gt=0)
    current_vwap: float | None = Field(default=None, gt=0)
    regime_state: Literal["aligned", "flipped", "weakening", "unknown"] = "unknown"
    structure_signal: Literal["none", "utad", "spring", "fakeout", "trap", "clean"] = "none"
    divergence_signal: Literal["none", "bullish", "bearish"] = "none"
    add_on_requested: bool = False
    partial_exit_fraction: float = Field(default=0.50, ge=0.0, le=1.0)
    breakeven_buffer_atr: float = Field(default=0.05, ge=0.0, le=1.0)
    trailing_atr_multiple: float = Field(default=1.50, ge=0.25, le=5.0)
    minimum_post_entry_bars: int = Field(default=3, ge=1, le=100)


class PostEntryLifecycleGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warn", "block"]
    evidence: str
    remediation: str | None = None


class PostEntryLifecycleReport(BaseModel):
    lifecycle_version: str
    symbol: str
    timeframe: TimeframeValue
    direction: TradeDirection
    closed_candle_only: bool
    source_bar_count: int
    post_entry_bar_count: int
    entry_sequence_number: int
    entry_price: float
    initial_stop_loss: float
    current_stop_loss: float
    target_1: float
    target_2: float | None = None
    mfe_r: float
    mae_r: float
    r_multiple_current: float
    trade_state: Literal["WAITING", "ENTRY_READY", "ENTERED", "PARTIAL_EXIT", "TRAILING", "THESIS_WEAKENING", "INVALIDATED", "EXITED"]
    current_thesis_status: Literal["intact", "weakening", "invalidated", "exited", "not_entered"]
    exit_plan: str
    partial_exit_plan: str
    trailing_stop: float | None = None
    invalidation_trigger: str
    thesis_downgrade_reason: str
    add_on_allowed: bool
    confidence_adjustment: Literal["maintain", "reduce", "block_add_on", "exit_required"]
    simulation_actions: list[str]
    no_future_leakage: bool
    simulation_only: bool = True
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    reasons: list[str]
    failure_questions: list[str]
    gates: list[PostEntryLifecycleGate]


class FinalConfluenceVote(BaseModel):
    vote_id: str
    evidence_layer: Literal[
        "risk_safety",
        "data_quality",
        "liquidity",
        "market_regime",
        "structure_levels",
        "volume_auction",
        "relative_strength",
        "indicators",
        "external_ai",
        "post_entry",
    ]
    direction: Literal["long", "short", "neutral", "block"]
    raw_score: float = Field(ge=-1.0, le=1.0)
    weighted_score: float = Field(ge=-7.0, le=7.0)
    priority_rank: int = Field(ge=1, le=9)
    reason: str


class FinalConfluenceConflict(BaseModel):
    conflict_id: str
    rule: str
    severity: Literal["info", "reduce", "downgrade", "block"]
    affected_votes: list[str]
    score_adjustment: float = Field(ge=-7.0, le=0.0)
    reason: str


class FinalConfluenceArbiterRequest(BaseModel):
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=40)
    timeframe: TimeframeValue = "1m"
    direction: TradeDirection = "long"
    data_quality_pass: bool = True
    liquidity_grade: Literal["A", "B", "C", "UNKNOWN"] = "UNKNOWN"
    market_regime_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    relative_strength_score: float = Field(default=0.5, ge=0.0, le=1.0)
    structure_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    volume_auction_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    indicator_signal_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    external_ai_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    trap_score: float = Field(default=0.0, ge=0.0, le=1.0)
    event_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    daily_resistance_conflict: bool = False
    weak_sector: bool = False
    post_entry_thesis_status: Literal["intact", "weakening", "invalidated", "exited", "not_entered"] = "not_entered"
    short_logic_enabled: bool = False
    evidence_count: int = Field(default=0, ge=0, le=1000)
    minimum_evidence_count: int = Field(default=30, ge=1, le=1000)
    low_evidence_flag: bool = False
    required_mtf_complete: bool = True
    entry_plan_authority_present: bool = True
    no_future_leakage: bool = True


class FinalConfluenceArbiterGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warn", "block"]
    evidence: str
    remediation: str | None = None


class FinalConfluenceArbiterReport(BaseModel):
    arbiter_version: str
    symbol: str
    timeframe: TimeframeValue
    direction: TradeDirection
    evidence_hierarchy: list[str]
    confluence_score: int = Field(ge=-7, le=7)
    raw_score: float = Field(ge=-20.0, le=20.0)
    evidence_votes: list[FinalConfluenceVote]
    conflicts_detected: list[FinalConfluenceConflict]
    dominant_blocker: str | None = None
    decision_band: Literal["PAPER_CANDIDATE", "WATCH", "WAIT", "AVOID", "SHORT_PAPER_CANDIDATE"]
    confidence_interval: list[float]
    final_decision: Literal["PAPER-CANDIDATE", "WATCH", "WAIT", "AVOID", "SHORT PAPER-CANDIDATE"]
    human_reason_tree: list[str]
    no_future_leakage: bool
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    reasons: list[str]
    failure_questions: list[str]
    gates: list[FinalConfluenceArbiterGate]


class BehaviorContextRequest(BaseModel):
    series: CandleSeries
    direction: TradeDirection = "long"
    decision_time_ns: int | None = Field(default=None, ge=0)
    previous_day_high: float | None = Field(default=None, gt=0)
    previous_day_low: float | None = Field(default=None, gt=0)
    previous_close: float | None = Field(default=None, gt=0)
    vwap: float | None = Field(default=None, gt=0)
    opening_range_high: float | None = Field(default=None, gt=0)
    opening_range_low: float | None = Field(default=None, gt=0)
    volume_profile_hvn: float | None = Field(default=None, gt=0)
    volume_profile_lvn: float | None = Field(default=None, gt=0)
    higher_timeframe_series: list[CandleSeries] = Field(default_factory=list)
    stock_return_pct: float = 0.0
    index_return_pct: float = 0.0
    sector_return_pct: float = 0.0
    banknifty_return_pct: float | None = None
    global_risk_score: float = Field(default=0.25, ge=0.0, le=1.0)


class BehaviorContextResult(BaseModel):
    context_version: str
    symbol: str
    timeframe: TimeframeValue
    direction: TradeDirection
    levels: VwapOrbCprContextResult
    htf: HTFConfirmationResult | None
    gap: GapContextResult | None
    market: MarketContextResult
    final_context_bias: Literal["supports_long", "supports_short", "mixed", "avoid"]
    context_quality_score: float = Field(ge=0.0, le=1.0)
    blocks_trade: bool
    reason_tree: dict[str, str]


SessionPhaseValue = Literal[
    "09:15-09:30_open_drive",
    "09:30-10:15_real_trend_confirmation",
    "10:15-11:30_continuation_or_fade",
    "11:30-13:30_lunch_compression",
    "13:30-14:30_post_lunch_expansion",
    "14:30-15:15_closing_drive",
    "15:15-15:30_squareoff_fake_spike",
    "outside_regular_session",
]


class SessionSegmentScore(BaseModel):
    session_phase: SessionPhaseValue
    window_start: str
    window_end: str
    bar_count: int
    return_pct: float
    range_pct: float
    avg_volume: float | None
    volume_curve: Literal["rising", "falling", "flat", "unknown"]
    trend_bias: Literal["bullish", "bearish", "range", "choppy", "unknown"]
    continuation_score: float = Field(ge=0.0, le=1.0)
    fakeout_risk: float = Field(ge=0.0, le=1.0)
    trade_quality_score: float = Field(ge=0.0, le=1.0)
    notes: list[str]


class SessionRhythmRequest(BaseModel):
    series: CandleSeries
    decision_time_ns: int | None = Field(default=None, ge=0)
    timezone_offset_minutes: int = Field(default=330, ge=-720, le=840)
    minimum_bars_per_segment: int = Field(default=2, ge=1, le=50)


class SessionRhythmResult(BaseModel):
    rhythm_version: str
    symbol: str
    timeframe: TimeframeValue
    trading_date: str | None
    day_of_week: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "unknown"]
    current_session_phase: SessionPhaseValue
    segments: list[SessionSegmentScore]
    usual_open_behavior: str
    usual_midday_behavior: str
    usual_closing_behavior: str
    best_trade_window: str
    worst_trade_window: str
    fakeout_window: str
    continuation_window: str
    session_personality_score: float = Field(ge=0.0, le=1.0)
    blocks_trade: bool
    no_trade_reason: str | None = None
    reasons: list[str]


class SessionMemoryProfile(BaseModel):
    symbol: str
    profile_version: str
    updated_at: str
    session_phase: SessionPhaseValue
    sample_count: int
    continuation_rate_pct: float
    fakeout_rate_pct: float
    average_move_atr: float
    usual_behavior: str
    best_trade_window: str
    worst_trade_window: str
    evidence_quality: Literal["LOW", "MEDIUM", "STRONG"]
    minimum_sample_pass: bool
    notes: list[str]


class DayOfWeekMemoryRecord(BaseModel):
    day_of_week: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "unknown"]
    sample_count: int
    continuation_rate_pct: float
    reversal_rate_pct: float
    fakeout_rate_pct: float
    average_next_move_atr: float
    best_session_phase: SessionPhaseValue
    worst_session_phase: SessionPhaseValue
    behavior_note: str
    minimum_sample_pass: bool


class DayOfWeekMemoryResult(BaseModel):
    memory_version: str
    symbol: str
    records: list[DayOfWeekMemoryRecord]
    dominant_day_note: str
    minimum_sample_size: int
    total_samples: int
    blocks_strong_probability: bool
    reasons: list[str]


class StockDNASummary(BaseModel):
    symbol: str
    profile_version: str
    updated_at: str
    session_rhythm: SessionRhythmResult
    session_memory: list[SessionMemoryProfile]
    day_of_week_memory: DayOfWeekMemoryResult
    stock_dna: StockDNAProfile
    stock_personality_summary: str
    behavior_edges: list[str]
    risk_warnings: list[str]
    minimum_evidence_pass: bool
    learning_status: Literal["mock_seeded", "learning", "calibrated", "quarantined"]


class StockMemoryProfileRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=42, ge=0)


class StockMemoryProfileReport(BaseModel):
    memory_profile_version: str
    generated_at: str
    symbol: str
    timeframe: TimeframeValue
    snapshot_count: int
    memory_record_count: int
    historical_match_count: int
    minimum_sample_size: int
    minimum_sample_pass: bool
    freshness_score: float = Field(ge=0.0, le=1.0)
    stock_dna_summary: StockDNASummary
    session_summary: dict[str, Any]
    day_of_week_summary: dict[str, Any]
    pattern_memory_summary: dict[str, Any]
    similar_day_summary: dict[str, Any]
    failure_summary: dict[str, Any]
    trust_summary: dict[str, Any]
    no_trade_memory_reasons: list[str]
    output_hash: str
    deterministic: bool
    no_future_leakage: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[RuntimeReadinessGate]
    notes: list[str]


class ExactTimeSessionMemoryRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=71, ge=0)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timezone_offset_minutes: int = Field(default=330, ge=-720, le=840)
    decision_time_ns: int | None = Field(default=None, ge=0)
    minimum_evidence_per_bucket: int = Field(default=30, ge=1, le=1000)


class ExchangeCalendarSessionBoundary(BaseModel):
    exchange: str
    timezone: str
    trading_date: str
    session_phase: SessionPhaseValue
    window_start: str
    window_end: str
    start_minute_of_day: int = Field(ge=0, le=1440)
    end_minute_of_day: int = Field(ge=0, le=1440)
    regular_session: bool
    special_session_class: Literal["normal_day", "holiday", "half_day", "expiry_day", "post_holiday", "results_day", "rbi_fed_day"]
    follows_exchange_calendar: bool


class ExactMinuteBehaviorProfile(BaseModel):
    minute_of_day: int = Field(ge=0, le=1440)
    local_time: str
    session_phase: SessionPhaseValue
    independent_evidence_count: int = Field(ge=0)
    continuation_rate_pct: float = Field(ge=0.0, le=100.0)
    reversal_rate_pct: float = Field(ge=0.0, le=100.0)
    fakeout_rate_pct: float = Field(ge=0.0, le=100.0)
    average_resolution_minutes: float = Field(ge=0.0)
    typical_or_unusual: Literal["typical", "unusual", "low_evidence"]
    current_state_typicality_score: float = Field(ge=0.0, le=1.0)
    common_resolution_time: str
    includes_later_timestamps: bool = False
    evidence_quality: Literal["LOW", "MEDIUM", "STRONG"]
    note: str


class SessionTransitionProfile(BaseModel):
    transition_name: str
    from_phase: SessionPhaseValue
    to_phase: SessionPhaseValue
    transition_time: str
    independent_evidence_count: int = Field(ge=0)
    behavior_change_rate_pct: float = Field(ge=0.0, le=100.0)
    continuation_to_reversal_rate_pct: float = Field(ge=0.0, le=100.0)
    fakeout_risk_delta: float
    note: str


class CalendarBehaviorProfile(BaseModel):
    calendar_class: Literal["normal_day", "monday", "friday", "expiry_day", "post_holiday", "results_day", "rbi_fed_day"]
    independent_evidence_count: int = Field(ge=0)
    continuation_rate_pct: float = Field(ge=0.0, le=100.0)
    reversal_rate_pct: float = Field(ge=0.0, le=100.0)
    fakeout_rate_pct: float = Field(ge=0.0, le=100.0)
    average_next_move_atr: float
    behavior_difference_note: str
    evidence_quality: Literal["LOW", "MEDIUM", "STRONG"]
    minimum_sample_pass: bool


class ExactTimeSessionMemoryGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class ExactTimeSessionMemoryReport(BaseModel):
    memory_version: str
    generated_at: str
    symbol: str
    timeframe: TimeframeValue
    exchange: str
    timezone: str
    trading_date: str
    decision_time_ns: int = Field(ge=0)
    decision_local_time: str
    current_session_phase: SessionPhaseValue
    exchange_boundaries: list[ExchangeCalendarSessionBoundary]
    minute_profiles: list[ExactMinuteBehaviorProfile]
    current_minute_profile: ExactMinuteBehaviorProfile
    session_transitions: list[SessionTransitionProfile]
    calendar_profiles: list[CalendarBehaviorProfile]
    independent_evidence_counts: dict[str, int]
    all_profiles_exclude_later_timestamps: bool
    session_boundaries_follow_exchange_calendar: bool
    exact_time_typicality_summary: str
    likely_resolution_window: str
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[ExactTimeSessionMemoryGate]
    notes: list[str]


class SimulationIntegrityReport(BaseModel):
    data_source: Literal["synthetic_mock", "historical_replay", "external_feed_mock", "live_feed"]
    generation_timestamp: str
    model_version: str | None
    calibration_date: str | None
    assumptions: list[str]
    confidence_interval: tuple[float, float] | None
    disclaimer: str


class AuditEvent(BaseModel):
    event_id: str
    timestamp: str
    level: Literal["info", "warning", "critical"]
    message: str
    source: str
    mode: SystemModeValue


class AuditIntegrityReport(BaseModel):
    event_count: int
    hashed_event_count: int
    chain_valid: bool
    head_hash: str | None
    first_event_time: str | None
    last_event_time: str | None
    algorithm: Literal["sha256-canonical-json"]
    checked_at: str
    issues: list[str]


class KnowledgeGraph(BaseModel):
    schema_version: str
    generated_at: str
    root: str
    summary: dict[str, Any]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class BehaviorAnalyzeRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=42, ge=0)
    replay_snapshot_id: str | None = None


class BehaviorLayerContract(BaseModel):
    layer_index: int
    layer_name: str
    contract_name: str
    status: CapabilityStatus
    required: bool = True


class BehaviorOutputColumn(BaseModel):
    index: int
    name: str
    group: str


class BehaviorSpec(BaseModel):
    purpose: str
    no_blind_prediction_rule: str
    universal_agreement_rule: str
    low_evidence_message: str
    narrative_explanation_only_invariant: str
    layer_contracts: list[BehaviorLayerContract]
    output_columns: list[BehaviorOutputColumn]
    verbatim_registry: list[dict[str, Any]]
    live_trading_blocked: bool
    stock_app_source_root: str


class BehaviorAnalysisResult(BaseModel):
    symbol: str
    timeframe: str
    run_id: str
    result: dict[str, Any]
    columns: list[str]
    safety_gates: list[str]
    reason_tree: dict[str, str]
    live_trade_route_attempted: bool = False


class StockDNAProfile(BaseModel):
    symbol: str
    profile_version: str
    updated_at: str
    source: Literal["mock", "replay", "simulation", "paper", "live"] = "mock"
    usual_open_behavior: str
    usual_midday_behavior: str
    usual_closing_behavior: str
    best_trade_window: str
    worst_trade_window: str
    fakeout_window: str
    continuation_window: str
    level_respect_summary: dict[str, Any]
    notes: list[str]


class BehaviorMemoryRecord(BaseModel):
    memory_id: str
    symbol: str
    trade_date: str
    timeframe: str
    pattern_id: str
    market_state: str
    session_phase: str
    outcome_label: str
    similarity_group: str
    feature_snapshot: dict[str, Any]
    reason: str
    model_version: str
    replay_snapshot_id: str | None = None


class DayShapeVector(BaseModel):
    gap_pct: float
    first_15m_return: float
    first_30m_range: float
    vwap_position_score: float
    trend_slope: float
    pullback_depth: float
    volume_curve: float
    atr_expansion: float
    high_break_time: str
    low_break_time: str
    close_position: float
    rejection_count: int
    breakout_failure_count: int
    vector_values: list[float]


class SimilarDayMatch(BaseModel):
    match_id: str
    symbol: str
    similar_day_id: str
    similarity_score_pct: float
    outcome_label: str
    average_next_move_atr: float
    failure_reason: str | None = None
    replay_available: bool = True
    pattern_id: str = "unknown"
    market_state: str = "unknown"
    session_phase: str = "unknown"
    similarity_method: Literal["cosine_dtw_decay", "seeded_mock"] = "seeded_mock"
    cosine_similarity_pct: float = 0.0
    dtw_similarity_pct: float = 0.0
    time_decay_weight: float = 1.0
    evidence_quality: Literal["LOW", "MEDIUM", "STRONG"] = "LOW"
    minimum_sample_pass: bool = False
    feature_match_summary: str = "legacy seeded similar-day match"
    current_day_shape_vector: DayShapeVector | None = None
    matched_day_shape_vector: DayShapeVector | None = None
    no_trade_reason: str | None = None


class PatternMemoryRequest(BaseModel):
    series: CandleSeries
    previous_close: float | None = Field(default=None, ge=0.0)
    decision_time_ns: int | None = Field(default=None, ge=0)
    minimum_sample_size: int = Field(default=30, ge=1, le=500)
    max_matches: int = Field(default=5, ge=1, le=25)
    timezone_offset_minutes: int = Field(default=330, ge=-720, le=840)


class PatternMemoryResult(BaseModel):
    memory_version: str
    symbol: str
    timeframe: TimeframeValue
    day_shape_vector: DayShapeVector
    vector_fields: list[str]
    similarity_methods: list[str]
    matches: list[SimilarDayMatch]
    historical_match_count: int
    minimum_sample_size: int
    minimum_sample_pass: bool
    evidence_quality: Literal["LOW", "MEDIUM", "STRONG"]
    continuation_probability_pct: float
    reversal_probability_pct: float
    fakeout_probability_pct: float
    range_probability_pct: float
    average_next_move_atr: float
    best_invalidation: str
    similar_day_ids: list[str]
    replay_ready: bool
    no_trade_reason: str | None = None
    reason_tree: dict[str, str]


class SimilarDayReplayResult(BaseModel):
    replay_version: str
    symbol: str
    similar_day_id: str
    match: SimilarDayMatch
    day_shape_vector: DayShapeVector | None
    events: list[MarketEvent]
    deterministic: bool = True
    replay_notes: list[str]


OutcomeLabelValue = Literal[
    "TARGET_HIT",
    "SL_HIT",
    "PARTIAL_WIN",
    "BREAKEVEN",
    "TIME_EXIT",
    "FAKE_BREAKOUT",
    "RETEST_SUCCESS",
    "RETEST_FAIL",
    "CHOP_NO_FOLLOWTHROUGH",
]


class OutcomeLabelRequest(BaseModel):
    series: CandleSeries
    direction: Literal["long", "short"] = "long"
    entry_price: float = Field(gt=0.0)
    stop_loss: float = Field(gt=0.0)
    target: float = Field(gt=0.0)
    entry_timestamp_ns: int | None = Field(default=None, ge=0)
    max_holding_bars: int = Field(default=24, ge=1, le=500)
    pattern_id: str = Field(default="unknown", min_length=1, max_length=120)
    run_id: str | None = None


class OutcomeLabelResult(BaseModel):
    outcome_version: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    direction: Literal["long", "short"]
    pattern_id: str
    outcome_label: OutcomeLabelValue
    bars_to_target: int | None
    bars_to_sl: int | None
    max_profit_before_sl: float
    max_loss_before_target: float
    mfe: float
    mae: float
    target_hit_timestamp_ns: int | None
    sl_hit_timestamp_ns: int | None
    fakeout_detected: bool
    reason: str
    audit_fields: dict[str, Any]


ConservativeOutcomeLabelValue = Literal[
    "TARGET_HIT_FIRST",
    "SL_HIT_FIRST",
    "OVERNIGHT_GAP_TARGET",
    "OVERNIGHT_GAP_SL",
    "GAP_THROUGH_STOP",
    "AMBIGUOUS_BOTH_HIT_SAME_BAR",
    "NEITHER_HIT_TIME_EXIT",
    "PARTIAL_TARGET_THEN_SL",
    "BREAKEVEN",
    "FAKE_BREAKOUT",
    "RETEST_SUCCESS",
    "RETEST_FAIL",
    "CHOP_NO_FOLLOWTHROUGH",
    "NO_FILL",
]


class ConservativeCostModel(BaseModel):
    brokerage_pct_per_side: float = Field(default=0.01, ge=0.0, le=1.0)
    brokerage_cap_rs: float = Field(default=20.0, ge=0.0)
    stt_sell_side_pct: float = Field(default=0.025, ge=0.0, le=1.0)
    gst_pct_on_charges: float = Field(default=18.0, ge=0.0, le=100.0)
    sebi_pct: float = Field(default=0.0001, ge=0.0, le=1.0)
    exchange_transaction_pct: float = Field(default=0.00345, ge=0.0, le=1.0)
    stamp_duty_buy_side_pct: float = Field(default=0.003, ge=0.0, le=1.0)
    impact_cost_pct: float = Field(default=0.015, ge=0.0, le=5.0)
    latency_slippage_pct: float = Field(default=0.01, ge=0.0, le=5.0)
    adverse_selection_penalty_pct: float = Field(default=0.005, ge=0.0, le=5.0)


class ConservativeOutcomeLabelRequest(BaseModel):
    series: CandleSeries
    direction: Literal["long", "short"] = "long"
    entry_price: float = Field(gt=0.0)
    stop_price: float = Field(gt=0.0)
    target_price: float = Field(gt=0.0)
    entry_time_ns: int | None = Field(default=None, ge=0)
    order_type: Literal["market_order", "limit_order", "stop_order"] = "market_order"
    quantity: int = Field(default=1, ge=1, le=1_000_000)
    atr: float = Field(default=1.0, gt=0.0)
    max_holding_bars: int = Field(default=24, ge=1, le=500)
    has_lower_timeframe_sequence: bool = False
    pattern_id: str = Field(default="unknown", min_length=1, max_length=120)
    run_id: str | None = None
    cost_model: ConservativeCostModel = Field(default_factory=ConservativeCostModel)


class ConservativeOutcomeLabelResult(BaseModel):
    outcome_version: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    direction: Literal["long", "short"]
    pattern_id: str
    entry_time_ns: int | None
    entry_price: float
    executable_entry_price: float
    fill_model_version: str
    target_price: float
    stop_price: float
    first_target_time_ns: int | None
    first_stop_time_ns: int | None
    bars_to_target: int | None
    bars_to_stop: int | None
    mfe_price: float
    mae_price: float
    mfe_atr: float
    mae_atr: float
    gross_return_pct: float
    total_cost_pct: float
    net_return_after_costs: float
    outcome_label: ConservativeOutcomeLabelValue
    outcome_horizon_end_ns: int | None
    same_bar_ambiguous: bool
    gap_through_stop: bool
    no_fill: bool
    conservative_ordering_used: bool
    lower_timeframe_required: bool
    reason: str
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    audit_fields: dict[str, Any]


class FailurePatternRecord(BaseModel):
    failure_id: str
    symbol: str
    pattern_id: str
    outcome_label: OutcomeLabelValue
    failure_reason: str
    contributing_factors: list[str]
    severity: Literal["low", "medium", "high"]
    created_at: str


class FailureLibraryResult(BaseModel):
    library_version: str
    symbol: str
    failures: list[FailurePatternRecord]
    most_common_failure: str | None
    no_trade_lessons: list[str]


class LearningTrustRecord(BaseModel):
    trust_id: str
    symbol: str
    pattern_id: str
    sample_count: int
    predicted_probability_pct: float
    actual_success_rate_pct: float
    calibration_error_pct: float
    trust_score: float = Field(ge=0.0, le=1.0)
    evidence_quality: Literal["LOW", "MEDIUM", "STRONG"]
    notes: list[str]


class LearningTrustResult(BaseModel):
    trust_version: str
    symbol: str
    records: list[LearningTrustRecord]
    aggregate_trust_score: float = Field(ge=0.0, le=1.0)
    calibration_status: Literal["LOW_EVIDENCE", "CALIBRATING", "CALIBRATED", "QUARANTINED"]
    minimum_sample_pass: bool
    notes: list[str]


BehaviorSignalValue = Literal[
    "NO_TRADE",
    "BUY_BREAKOUT",
    "SELL_BREAKDOWN",
    "BUY_RETEST",
    "SELL_RETEST",
    "BUY_FADE",
    "SELL_FADE",
    "WATCH_ONLY",
    "AVOID_CHOP",
    "FAKEOUT_WARNING",
]


class BehaviorDecisionRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    rule_signal: BehaviorSignalValue = "WATCH_ONLY"
    direction: Literal["long", "short", "none"] = "none"
    data_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    liquidity_score: float = Field(default=1.0, ge=0.0, le=1.0)
    context_bias: Literal["supports_long", "supports_short", "mixed", "avoid"] = "mixed"
    context_blocks_trade: bool = False
    session_trade_quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    session_blocks_trade: bool = False
    similar_history_continuation_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    similar_history_fakeout_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    pattern_minimum_sample_pass: bool = False
    trust_minimum_sample_pass: bool = False
    trust_score: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_warning: str | None = None
    market_regime_favorable: bool = False
    relative_strength_supports: bool = False
    risk_reward: float = Field(default=0.0, ge=0.0, le=20.0)
    daily_loss_limit_hit: bool = False
    cooldown_active: bool = False
    kill_switch_active: bool = False
    ood_score: float = Field(default=0.0, ge=0.0, le=1.0)
    drift_score: float = Field(default=0.0, ge=0.0, le=1.0)
    replay_snapshot_id: str | None = None


class BehaviorDecisionGate(BaseModel):
    gate: str
    passed: bool
    severity: Literal["info", "warning", "block"]
    reason: str


class ReasonTreeResult(BaseModel):
    reason_version: str
    symbol: str
    nodes: dict[str, str]
    ordered_reasons: list[str]
    read_only: bool = True
    cannot_execute_orders: bool = True
    cannot_override_calibrated_probabilities: bool = True


class NoTradeDecisionRecord(BaseModel):
    symbol: str
    active: bool
    no_trade_reason: str | None
    blocking_gates: list[str]
    wait_for: list[str]


class TradeDecisionResult(BaseModel):
    decision_version: str
    symbol: str
    final_trade_decision: BehaviorSignalValue
    trade_allowed: bool
    universal_agreement_pass: bool
    confidence_pct: float = Field(ge=0.0, le=100.0)
    agreement_checks: dict[str, bool]
    gates: list[BehaviorDecisionGate]
    no_trade: NoTradeDecisionRecord
    reason_tree: ReasonTreeResult
    output_updates: dict[str, Any]
    narrative_explanation: str
    live_trade_route_attempted: bool = False


class BehaviorRiskRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    decision: BehaviorSignalValue = "NO_TRADE"
    account_equity: float = Field(default=1_000_000.0, gt=0.0)
    entry_price: float = Field(default=100.0, gt=0.0)
    stop_loss: float = Field(default=98.0, gt=0.0)
    target: float = Field(default=106.0, gt=0.0)
    confidence_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    liquidity_score: float = Field(default=1.0, ge=0.0, le=1.0)
    slippage_risk_pct: float = Field(default=0.05, ge=0.0, le=10.0)
    sector: str = "UNKNOWN"
    index: str = "UNKNOWN"
    current_sector_exposure_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    current_index_exposure_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    correlation_risk: Literal["low", "medium", "high"] = "low"
    daily_pnl: float = 0.0
    consecutive_losses: int = Field(default=0, ge=0, le=100)
    choppy_regime: bool = False
    max_risk_per_trade_pct: float = Field(default=0.5, gt=0.0, le=5.0)
    max_daily_loss_pct: float = Field(default=2.0, gt=0.0, le=20.0)
    max_portfolio_heat_pct: float = Field(default=6.0, gt=0.0, le=100.0)
    max_sector_exposure_pct: float = Field(default=25.0, gt=0.0, le=100.0)
    max_index_exposure_pct: float = Field(default=40.0, gt=0.0, le=100.0)
    cooldown_after_n_losses: int = Field(default=3, ge=1, le=20)
    cooldown_minutes: int = Field(default=30, ge=1, le=1440)


class PortfolioExposureRecord(BaseModel):
    sector: str
    index: str
    sector_exposure_pct: float
    index_exposure_pct: float
    correlation_risk: Literal["low", "medium", "high"]
    portfolio_heat_pct: float
    blocks_trade: bool
    reasons: list[str]


class DailyLossLimitRecord(BaseModel):
    daily_pnl: float
    max_daily_loss_amount: float
    daily_loss_limit_hit: bool
    cooldown_active: bool
    cooldown_minutes: int
    reasons: list[str]


class RiskSizingResult(BaseModel):
    risk_version: str
    symbol: str
    decision: BehaviorSignalValue
    position_size: int
    risk_per_trade_pct: float
    capital_to_use: float
    max_loss_amount: float
    reward_amount: float
    risk_reward: float
    portfolio: PortfolioExposureRecord
    daily_loss: DailyLossLimitRecord
    trade_allowed: bool
    block_reasons: list[str]
    sizing_formula: str
    no_live_route_attempted: bool = True


BehaviorExecutionOrderType = Literal["MARKET", "LIMIT", "STOP"]
BehaviorExecutionStatus = Literal["FULL_FILL", "PARTIAL_FILL", "NO_FILL", "REJECTED_SIMULATION"]


class BehaviorExecutionRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    side: Literal["BUY", "SELL"] = "BUY"
    order_type: BehaviorExecutionOrderType = "MARKET"
    requested_quantity: int = Field(default=0, ge=0, le=1_000_000)
    entry_price: float = Field(default=100.0, gt=0.0)
    limit_price: float | None = Field(default=None, gt=0.0)
    stop_price: float | None = Field(default=None, gt=0.0)
    bar_open: float = Field(default=100.0, gt=0.0)
    bar_high: float = Field(default=101.0, gt=0.0)
    bar_low: float = Field(default=99.0, gt=0.0)
    bar_close: float = Field(default=100.5, gt=0.0)
    bid_ask_spread_pct: float = Field(default=0.08, ge=0.0, le=10.0)
    available_volume: int = Field(default=100_000, ge=0)
    queue_ahead_quantity: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=120, ge=0, le=60_000)
    impact_coefficient_bps: float = Field(default=4.0, ge=0.0, le=1000.0)
    adverse_selection_score: float = Field(default=0.25, ge=0.0, le=1.0)
    max_participation_rate: float = Field(default=0.08, gt=0.0, le=1.0)
    mode_confirmation: Literal["MOCK_ONLY"] = "MOCK_ONLY"
    seed: int = Field(default=42, ge=0)


class ExecutionCostBreakdown(BaseModel):
    spread_cost_pct: float
    latency_slippage_pct: float
    market_impact_pct: float
    adverse_selection_cost_pct: float
    total_cost_pct: float


class ExecutionSimulationResult(BaseModel):
    execution_version: str
    simulation_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: BehaviorExecutionOrderType
    requested_quantity: int
    filled_quantity: int
    unfilled_quantity: int
    fill_status: BehaviorExecutionStatus
    fill_probability_pct: float
    fill_price: float | None
    reference_price: float
    fill_quality: Literal["excellent", "acceptable", "poor", "rejected", "no_fill"]
    queue_position_estimate: float = Field(ge=0.0, le=1.0)
    partial_fill_probability_pct: float
    no_fill_reason: str | None
    missed_trade_reason: str | None
    adverse_selection_risk: Literal["low", "medium", "high"]
    costs: ExecutionCostBreakdown
    market_impact_model: str
    latency_model: str
    deterministic: bool = True
    simulation_only: bool = True
    live_route_attempted: bool = False
    safety_notes: list[str]


class ExecutionIntentPaperSafetyRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    side: Literal["BUY", "SELL"] = "BUY"
    order_type: BehaviorExecutionOrderType = "LIMIT"
    requested_quantity: int = Field(default=1200, ge=1, le=1_000_000)
    entry_price: float = Field(default=2500.0, gt=0.0)
    limit_price: float | None = Field(default=2498.0, gt=0.0)
    stop_price: float | None = Field(default=None, gt=0.0)
    target_price: float = Field(default=2575.0, gt=0.0)
    bar_open: float = Field(default=2502.0, gt=0.0)
    bar_high: float = Field(default=2512.0, gt=0.0)
    bar_low: float = Field(default=2499.0, gt=0.0)
    bar_close: float = Field(default=2508.0, gt=0.0)
    bid_ask_spread_pct: float = Field(default=0.08, ge=0.0, le=10.0)
    available_volume: int = Field(default=30_000, ge=0)
    queue_ahead_quantity: int = Field(default=4500, ge=0)
    latency_ms: int = Field(default=180, ge=0, le=60_000)
    impact_coefficient_bps: float = Field(default=6.0, ge=0.0, le=1000.0)
    adverse_selection_score: float = Field(default=0.42, ge=0.0, le=1.0)
    max_participation_rate: float = Field(default=0.08, gt=0.0, le=1.0)
    mode_label: Literal["SIMULATION_ESTIMATE"] = "SIMULATION_ESTIMATE"
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"] = "openalgo"
    manual_review_required: bool = True
    seed: int = Field(default=83, ge=0)


class ExecutionIntentLifecycleRecord(BaseModel):
    intent_id: str
    current_state: Literal[
        "DRAFT",
        "PAPER_SIMULATED",
        "MANUAL_REVIEW_REQUIRED",
        "READY_FOR_EXTERNAL_REVIEW",
        "REJECTED",
        "EXPIRED",
        "CANCELLED",
    ]
    allowed_states: list[str]
    created_at: str
    valid_until: str
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"]
    manual_review_required: bool
    next_required_approval: str
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class PaperSimulationEstimateRecord(BaseModel):
    estimate_id: str
    estimate_label: Literal["SIMULATION_ESTIMATE"]
    scenario_name: str
    simulation: ExecutionSimulationResult
    net_cost_pct: float
    no_fill_counted_as_win: bool
    partial_fill_recorded: bool
    slippage_latency_impact_present: bool
    adverse_selection_present: bool
    paper_only: bool


class ExecutionIntentSafetyGateRecord(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str


class ExecutorManualReviewRecord(BaseModel):
    review_id: str
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"]
    review_state: Literal[
        "manual_review_required",
        "blocked_missing_approval",
        "blocked_live_route",
        "ready_for_paper_review",
    ]
    required_checks: list[str]
    forbidden_actions: list[str]
    operator_message: str


class ExecutionIntentPaperSafetyReport(BaseModel):
    paper_safety_version: str
    generated_at: str
    symbol: str
    exchange: str
    intent_lifecycle: ExecutionIntentLifecycleRecord
    paper_estimates: list[PaperSimulationEstimateRecord]
    manual_review: ExecutorManualReviewRecord
    intent_lifecycle_present: bool
    all_execution_outputs_labeled_simulation_estimate: bool
    no_fill_partial_fill_cost_memory_present: bool
    manual_review_required_for_executor_handoff: bool
    no_live_broker_route_enabled: bool
    broker_credentials_present: bool
    broker_order_created: bool
    order_routing_enabled: bool
    live_trading_blocked: bool
    deterministic: bool
    trade_allowed: bool
    gates: list[ExecutionIntentSafetyGateRecord]
    notes: list[str]


class PaperExecutorPermissionRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"] = "openalgo"
    requested_mode: SystemModeValue = SystemModeValue.MOCK
    kill_switch_state: Literal["armed", "triggered", "reset_pending"] = "armed"
    human_veto_active: bool = False
    external_human_approval_present: bool = False
    secondary_approval_present: bool = False
    risk_gate_passed: bool = False
    replay_determinism_passed: bool = False
    paper_validation_passed: bool = False
    exchange_reconciliation_ready: bool = False
    slippage_simulator_ready: bool = True
    point_in_time_data_ready: bool = True
    requested_by: str = Field(default="local_operator", min_length=1, max_length=80)
    secondary_approver: str | None = Field(default=None, max_length=80)
    seed: int = Field(default=84, ge=0)


class ModePermissionMatrixRow(BaseModel):
    mode: SystemModeValue
    research_allowed: bool
    preview_intent_allowed: bool
    external_paper_review_allowed: bool
    live_handoff_allowed: bool
    required_gates: list[str]
    reason: str


class KillSwitchRecheckRecord(BaseModel):
    checked_at: str
    kill_switch_state: Literal["armed", "triggered", "reset_pending"]
    kill_switch_rechecked: bool
    passes_executor_preflight: bool
    blocks_reason: str | None


class HumanApprovalGateRecord(BaseModel):
    approval_id: str
    requested_by: str
    primary_approval_present: bool
    secondary_approval_present: bool
    dual_approval_required: bool
    human_veto_active: bool
    approval_state: Literal["missing", "single_approval_only", "dual_approval_recorded", "veto_active"]
    blocks_reason: str | None


class ExecutorPreflightGateRecord(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warning", "block"]
    evidence: str
    remediation: str


class PaperExecutorPermissionReport(BaseModel):
    permission_version: str
    generated_at: str
    symbol: str
    exchange: str
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"]
    requested_mode: SystemModeValue
    permission_matrix: list[ModePermissionMatrixRow]
    kill_switch_recheck: KillSwitchRecheckRecord
    human_approval: HumanApprovalGateRecord
    preflight_gates: list[ExecutorPreflightGateRecord]
    accepted_for_external_paper_review: bool
    rejected: bool
    rejection_reasons: list[str]
    mode_permission: Literal[
        "mock_preview_only",
        "simulation_preview_only",
        "replay_preview_only",
        "paper_review_blocked",
        "paper_review_ready",
        "live_blocked",
    ]
    broker_credentials_present: bool
    broker_order_created: bool
    trade_allowed: bool
    order_routing_enabled: bool
    live_trading_blocked: bool
    notes: list[str]


class ExecutorHandoffAuditRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"] = "openalgo"
    requested_mode: SystemModeValue = SystemModeValue.MOCK
    requested_by: str = Field(default="local_operator", min_length=1, max_length=80)
    external_human_approval_present: bool = False
    secondary_approval_present: bool = False
    risk_gate_passed: bool = False
    replay_determinism_passed: bool = False
    paper_validation_passed: bool = False
    exchange_reconciliation_ready: bool = False
    seen_duplicate_key: bool = False
    force_expired: bool = False
    seed: int = Field(default=85, ge=0)


class ExecutorHandoffIntentAuditRecord(BaseModel):
    intent_id: str
    duplicate_key: str
    duplicate_intent_blocked: bool
    valid_until: str
    expired: bool
    expiry_enforced: bool
    rejection_reasons: list[str]
    mode_permission: str
    export_status: Literal["audit_only", "blocked_duplicate", "expired", "blocked_preflight"]


class ExecutorHandoffEvidenceBinding(BaseModel):
    binding_name: str
    contract_name: str
    sha256: str
    required: bool
    present: bool


class ExecutorHandoffImmutableReceipt(BaseModel):
    receipt_version: str
    receipt_id: str
    created_at: str
    algorithm: Literal["sha256-canonical-json"]
    canonical_payload_hash: str
    receipt_hash: str
    immutable: bool
    bound_contracts: list[str]
    forbidden_fields_absent: bool


class ExecutorHandoffAuditEnvelope(BaseModel):
    audit_version: str
    generated_at: str
    symbol: str
    exchange: str
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"]
    intent: ExecutorHandoffIntentAuditRecord
    paper_safety: ExecutionIntentPaperSafetyReport
    permission_report: PaperExecutorPermissionReport
    evidence_bindings: list[ExecutorHandoffEvidenceBinding]
    receipt: ExecutorHandoffImmutableReceipt
    duplicate_key_preserved: bool
    expiry_preserved: bool
    rejection_reasons_preserved: bool
    export_disabled_inside_trade_vision: bool
    broker_credentials_present: bool
    broker_order_created: bool
    trade_allowed: bool
    order_routing_enabled: bool
    live_trading_blocked: bool
    notes: list[str]


class BehaviorFrontendPanelMapItem(BaseModel):
    panel_id: str
    title: str
    workspace: Literal["behavior"]
    layer_index: int | None
    layer_name: str
    contract_name: str
    endpoint: str
    output_fields: list[str]
    fallback_state: Literal["loading", "mock", "reserved", "blocked", "offline"]
    capability_name: str
    manifest_status: CapabilityStatus
    required_for_mvp: bool


class BehaviorFrontendPanelMapResult(BaseModel):
    map_version: str
    workspace: Literal["behavior"]
    total_panels: int
    mock_panels: int
    reserved_panels: int
    panels: list[BehaviorFrontendPanelMapItem]
    safety_invariants: list[str]


class BehaviorValidationRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=42, ge=0)
    validation_type: Literal["walk_forward", "out_of_sample"] = "walk_forward"
    folds: int = Field(default=3, ge=1, le=12)
    train_days: int = Field(default=60, ge=5, le=1000)
    test_days: int = Field(default=10, ge=1, le=250)
    minimum_train_samples: int = Field(default=30, ge=1, le=10_000)
    minimum_test_samples: int = Field(default=10, ge=1, le=10_000)


class BehaviorValidationFoldResult(BaseModel):
    fold_index: int
    train_start_day: int
    train_end_day: int
    test_start_day: int
    test_end_day: int
    train_samples: int
    test_samples: int
    leakage_pass: bool
    minimum_sample_pass: bool
    win_rate_pct: float
    profit_factor: float
    expectancy_r: float
    max_drawdown_pct: float
    average_r: float
    median_r: float
    trade_count: int
    notes: list[str]


class BehaviorValidationResult(BaseModel):
    validation_version: str
    symbol: str
    timeframe: TimeframeValue
    validation_type: Literal["walk_forward", "out_of_sample"]
    folds: list[BehaviorValidationFoldResult]
    aggregate_win_rate_pct: float
    aggregate_profit_factor: float
    aggregate_expectancy_r: float
    aggregate_max_drawdown_pct: float
    total_trades: int
    no_future_leakage: bool
    deterministic: bool = True
    live_trading_blocked: bool = True
    promotion_allowed: bool
    promotion_blockers: list[str]
    notes: list[str]


class BehaviorDriftRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    feature_name: str = Field(default="behavior_memory_embedding", min_length=1, max_length=120)
    baseline_mean: float = 0.0
    baseline_std: float = Field(default=1.0, gt=0.0)
    live_mean: float = 0.0
    live_std: float = Field(default=1.0, gt=0.0)
    baseline_sample_count: int = Field(default=120, ge=1)
    live_sample_count: int = Field(default=40, ge=1)
    watch_threshold: float = Field(default=0.25, gt=0.0, le=1.0)
    quarantine_threshold: float = Field(default=0.45, gt=0.0, le=1.0)


class BehaviorDriftResult(BaseModel):
    safety_version: str
    symbol: str
    feature_name: str
    baseline_sample_count: int
    live_sample_count: int
    mean_shift_z: float
    volatility_shift_ratio: float
    population_stability_index: float
    drift_score: float = Field(ge=0.0, le=1.0)
    drift_status: Literal["stable", "watch", "quarantine"]
    memory_quarantine_required: bool
    confidence_multiplier: float = Field(ge=0.0, le=1.0)
    promotion_allowed: bool
    promotion_blockers: list[str]
    notes: list[str]


class OODFeatureCheck(BaseModel):
    feature_name: str = Field(min_length=1, max_length=120)
    current_value: float
    expected_min: float
    expected_max: float
    hard_min: float
    hard_max: float


class OODFeatureResult(BaseModel):
    feature_name: str
    current_value: float
    expected_min: float
    expected_max: float
    hard_min: float
    hard_max: float
    distance_score: float = Field(ge=0.0, le=1.0)
    status: Literal["inside", "soft_outlier", "hard_outlier"]
    reason: str


class BehaviorOODRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    features: list[OODFeatureCheck]
    watch_threshold: float = Field(default=0.35, gt=0.0, le=1.0)
    block_threshold: float = Field(default=0.70, gt=0.0, le=1.0)


class BehaviorOODResult(BaseModel):
    safety_version: str
    symbol: str
    ood_score: float = Field(ge=0.0, le=1.0)
    max_feature_distance: float = Field(ge=0.0, le=1.0)
    ood_status: Literal["normal", "watch", "block"]
    confidence_blocked: bool
    trade_blocked: bool
    feature_results: list[OODFeatureResult]
    promotion_allowed: bool
    promotion_blockers: list[str]
    notes: list[str]


class RealityGapCheckRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    replay_slippage_pct: float = Field(default=0.08, ge=0.0, le=100.0)
    observed_slippage_pct: float = Field(default=0.10, ge=0.0, le=100.0)
    replay_fill_rate_pct: float = Field(default=95.0, ge=0.0, le=100.0)
    observed_fill_rate_pct: float = Field(default=93.0, ge=0.0, le=100.0)
    replay_latency_ms: int = Field(default=120, ge=0, le=120_000)
    observed_latency_ms: int = Field(default=150, ge=0, le=120_000)
    replay_pnl_r: float = 0.2
    observed_pnl_r: float = 0.16
    max_slippage_drift_pct: float = Field(default=0.20, gt=0.0, le=100.0)
    max_fill_rate_drift_pct: float = Field(default=15.0, gt=0.0, le=100.0)
    max_latency_drift_ms: int = Field(default=250, gt=0, le=120_000)
    max_pnl_drift_r: float = Field(default=0.50, gt=0.0, le=100.0)


class RealityGapCheckResult(BaseModel):
    safety_version: str
    symbol: str
    slippage_drift_pct: float
    fill_rate_drift_pct: float
    latency_drift_ms: int
    pnl_drift_r: float
    reality_gap_score: float = Field(ge=0.0, le=1.0)
    alert: bool
    severity: Literal["normal", "watch", "critical"]
    promotion_allowed: bool
    promotion_blockers: list[str]
    notes: list[str]


class BehaviorAcpCheckRecord(BaseModel):
    check_id: str
    purpose: str
    status: Literal["pass", "fail"]
    evidence: str
    blocks_promotion: bool


class BehaviorAcpHardeningResult(BaseModel):
    safety_version: str
    checks: list[BehaviorAcpCheckRecord]
    pass_count: int
    fail_count: int
    promotion_allowed: bool
    promotion_blockers: list[str]
    live_trading_blocked: bool = True
    notes: list[str]


class BehaviorSafetyReport(BaseModel):
    report_version: str
    report_id: str
    symbol: str
    created_at: str
    drift: BehaviorDriftResult
    ood: BehaviorOODResult
    reality_gap: RealityGapCheckResult
    acp: BehaviorAcpHardeningResult
    promotion_allowed: bool
    memory_quarantine_required: bool
    confidence_blocked: bool
    reality_gap_alert: bool
    report_hash: str
    immutable: bool = True
    notes: list[str]


class MemoryQuarantineRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    reason: str = Field(default="safety_report_trigger", min_length=1, max_length=500)
    source_report_id: str | None = Field(default=None, min_length=1, max_length=160)
    actor_id: str = Field(default="system", min_length=1, max_length=120)
    affected_memory_ids: list[str] = Field(default_factory=list)


class MemoryQuarantineRecord(BaseModel):
    quarantine_version: str
    quarantine_id: str
    symbol: str
    created_at: str
    status: Literal["active", "released", "rebuild_pending"]
    reason: str
    source_report_id: str | None
    actor_id: str
    affected_memory_ids: list[str]
    confidence_blocked: bool
    memory_promotion_blocked: bool
    read_policy: Literal["read_allowed_for_audit_only", "read_allowed_low_confidence", "read_blocked"]
    release_requires: list[str]
    notes: list[str]


class MemoryRebuildPlan(BaseModel):
    rebuild_version: str
    plan_id: str
    symbol: str
    quarantine_id: str | None
    created_at: str
    allowed_to_rebuild: bool
    required_inputs: list[str]
    rebuild_steps: list[str]
    promotion_gates: list[str]
    estimated_safe_status: Literal["blocked", "shadow_only", "mock_ready"]
    notes: list[str]


class GoldenReplayFixture(BaseModel):
    fixture_version: str
    fixture_id: str
    symbol: str
    scenario_id: str
    seed: int
    expected_event_count: int
    expected_first_event_id: str
    expected_last_event_id: str
    expected_chain_hash: str
    safety_assertions: list[str]


class GoldenReplayVerificationResult(BaseModel):
    verification_version: str
    fixture: GoldenReplayFixture
    actual_event_count: int
    actual_first_event_id: str | None
    actual_last_event_id: str | None
    actual_chain_hash: str
    deterministic: bool
    passed: bool
    issues: list[str]
    live_trading_blocked: bool = True


class BehaviorBenchmarkReport(BaseModel):
    report_version: str
    report_id: str
    symbol: str
    created_at: str
    walk_forward: BehaviorValidationResult
    out_of_sample: BehaviorValidationResult
    safety_report: BehaviorSafetyReport
    golden_replay_verifications: list[GoldenReplayVerificationResult]
    metrics: dict[str, Any]
    promotion_allowed: bool
    promotion_blockers: list[str]
    report_hash: str
    immutable: bool = True
    live_trading_blocked: bool = True
    notes: list[str]


class ReleaseChecklistGate(BaseModel):
    gate_id: str
    category: Literal["contracts", "data", "validation", "safety", "replay", "risk", "approval"]
    description: str
    status: Literal["pass", "fail"]
    evidence: str
    blocks_release: bool


class MockToReplayReleaseChecklist(BaseModel):
    checklist_version: str
    checklist_id: str
    symbol: str
    target_mode: Literal["REPLAY"]
    created_at: str
    benchmark_report_id: str
    gates: list[ReleaseChecklistGate]
    pass_count: int
    fail_count: int
    technical_release_pass: bool
    release_allowed: bool
    release_blockers: list[str]
    manual_approval_required: bool = True
    live_trading_blocked: bool = True
    notes: list[str]


class ReleaseApprovalRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=32)
    benchmark_report_id: str | None = None
    requested_by: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=10, max_length=500)
    approval_scope: Literal["mock_to_replay"] = "mock_to_replay"
    expires_in_minutes: int = Field(default=1440, ge=5, le=10080)


class ReleaseApprovalDecisionRequest(BaseModel):
    actor_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=5, max_length=500)


class ReleaseApprovalRecord(BaseModel):
    approval_version: str
    approval_id: str
    symbol: str
    target_mode: Literal["REPLAY"]
    approval_scope: Literal["mock_to_replay"]
    benchmark_report_id: str
    checklist_id: str | None
    requested_by: str
    requested_at: str
    reason: str
    status: Literal["requested", "approved", "rejected", "expired"]
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_by: str | None = None
    rejected_at: str | None = None
    rejection_reason: str | None = None
    expires_at: str
    evidence: list[str]
    live_trading_blocked: bool = True


class BenchmarkDrilldown(BaseModel):
    drilldown_version: str
    report_id: str
    symbol: str
    generated_at: str
    metric_groups: dict[str, dict[str, Any]]
    validation_summary: list[str]
    safety_summary: list[str]
    replay_summary: list[str]
    promotion_summary: list[str]
    live_trading_blocked: bool = True


class BehaviorScenarioCoverageItem(BaseModel):
    item_version: str
    scenario_id: str
    scenario_family: Literal[
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
        "unknown",
    ]
    fixture_id: str
    seed: int
    expected_event_count: int
    actual_event_count: int
    deterministic: bool
    passed: bool
    chain_hash: str
    coverage_status: Literal["covered", "failed", "missing"]
    safety_assertions: list[str]
    issues: list[str]
    notes: list[str]


class BehaviorScenarioCoverageReport(BaseModel):
    coverage_version: str
    coverage_id: str
    symbol: str
    benchmark_report_id: str
    generated_at: str
    required_scenario_families: list[str]
    covered_scenario_families: list[str]
    missing_scenario_families: list[str]
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    deterministic_pass_rate_pct: float
    coverage_score_pct: float
    scenario_items: list[BehaviorScenarioCoverageItem]
    promotion_allowed: bool
    promotion_blockers: list[str]
    immutable: bool = True
    live_trading_blocked: bool = True
    notes: list[str]


class RuntimeReadinessGate(BaseModel):
    gate_id: str
    name: str
    status: Literal["pass", "warn", "fail"]
    evidence: str
    blocks_research: bool
    remediation: str | None = None


class RuntimeIndicatorGroup(BaseModel):
    group_id: str
    source: Literal["self_indc", "pta_signal_markers"]
    sample_status: Literal["non_empty_sample", "empty_no_signal_on_sample", "registered_marker"]
    notes: str


class RuntimeReadinessReport(BaseModel):
    readiness_version: str
    generated_at: str
    project_root: str
    stock_app_source_root: str
    self_indicator_total: int
    self_indicator_returned: int
    pta_marker_total: int
    total_output_groups: int
    non_empty_sample_outputs: int
    empty_no_signal_outputs: int
    automated_indicator_tests_passed: int
    automated_indicator_tests_skipped: int
    chart_screens: dict[str, bool]
    research_surfaces: dict[str, bool]
    replay_surfaces: dict[str, bool]
    indicator_groups: list[RuntimeIndicatorGroup]
    gates: list[RuntimeReadinessGate]
    indicator_output_ready: bool
    chart_output_ready: bool
    research_activity_ready: bool
    replay_ready: bool
    safe_mode: bool
    live_trading_blocked: bool = True
    browser_recommended_ports: list[int]
    notes: list[str]


class BehaviorIndicatorRegistryEntry(BaseModel):
    indicator_id: str
    display_name: str
    source: Literal["self_indc", "pta_signal_markers"]
    implementation_path: str
    callable_name: str | None
    family: str
    subfamily: str
    purpose: str = ""
    category: Literal["trend", "momentum", "volatility", "volume", "level", "structure", "trap", "exhaustion", "harmonic", "curve", "smc", "risk", "unclassified"] = "unclassified"
    best_market_regime: str = ""
    bad_market_regime: str = ""
    best_timeframe: str = ""
    output_columns: list[str]
    input_columns: list[str]
    minimum_bars: int = Field(ge=1)
    lookback_bars: int = Field(ge=1)
    timeframes_allowed: list[TimeframeValue]
    continuous_or_event: Literal["continuous", "event", "mixed", "overlay"]
    signal_type: str = ""
    normalization_method: str
    direction_semantics: str
    direction_meaning: str = ""
    lag_behavior: Literal["leading", "lagging", "coincident", "unknown"] = "unknown"
    sequential_signal_window: int = Field(default=5, ge=1, le=100)
    missing_policy: str = "mask_and_explain"
    false_positive_conditions: list[str] = Field(default_factory=list)
    confirmation_rules: list[str] = Field(default_factory=list)
    conflict_rules: list[str] = Field(default_factory=list)
    trade_usage: list[str] = Field(default_factory=list)
    risk_usage: list[str] = Field(default_factory=list)
    no_trade_usage: list[str] = Field(default_factory=list)
    historical_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    historical_failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    per_stock_reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    usable_for_explanation: bool = True
    ontology_version: str = "indicator-ontology.v1"
    closed_bar_only: bool
    point_in_time_safe: bool
    formula_hash: str
    implementation_version: str
    test_fixture: str
    status: Literal["validated", "proxy", "blocked", "retired"]
    default_parameters_json: dict[str, Any] = Field(default_factory=dict)
    warmup_bars_exact: int = Field(ge=0)
    output_schema_json: dict[str, str] = Field(default_factory=dict)
    pit_audit_passed_date: str | None = None
    internal_lookahead_audit_result: Literal["passed", "pending", "failed"]
    centered_or_trailing: Literal["trailing", "centered_blocked", "not_applicable"]
    minimum_volume_policy: Literal["required", "optional", "not_applicable"]
    uses_future_pivots: bool
    confirmation_delay_bars: int = Field(ge=0)
    used_for_probability: bool = False
    live_trading_blocked: bool = True
    notes: list[str] = Field(default_factory=list)


class IndicatorLagVoteRequest(BaseModel):
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=40)
    indicator_id: str
    raw_vote: float = Field(default=1.0, ge=-1.0, le=1.0)
    per_stock_reliability: float = Field(default=1.0, ge=0.0, le=1.0)
    per_regime_reliability: float = Field(default=1.0, ge=0.0, le=1.0)
    freshness_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    current_decision_band: Literal["WAIT", "WATCH", "PAPER-CANDIDATE"] = "WAIT"


class IndicatorLagVoteRecord(BaseModel):
    indicator_id: str
    category: str
    lag_behavior: str
    confirmation_delay_bars: int = Field(ge=0)
    sequential_signal_window: int = Field(ge=1)
    lag_weight: float = Field(ge=0.0, le=1.0)
    delay_adjusted_vote: float = Field(ge=-1.0, le=1.0)
    stale_confirmation_warning: bool
    can_promote_wait_to_watch: bool
    can_promote_watch_to_paper: bool
    explanation_usage_allowed: bool
    post_entry_usage_allowed: bool
    reason: str


class IndicatorLagVotingReport(BaseModel):
    voting_version: str
    symbol: str
    registry_version: str
    indicator_id: str
    vote: IndicatorLagVoteRecord
    all_registry_entries_have_ontology: bool
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True
    gates: list[dict[str, Any]]
    notes: list[str]


class IndicatorSignalOutcomeLabelRequest(BaseModel):
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=40)
    indicator_id: str
    timeframe: TimeframeValue = "1m"
    signal_direction: Literal["bullish", "bearish", "neutral"] = "bullish"
    signal_time_ns: int = Field(default=1_714_724_800_000_000_000, ge=0)
    entry_price: float = Field(default=100.0, gt=0.0)
    stop_price: float = Field(default=98.0, gt=0.0)
    target_price: float = Field(default=104.0, gt=0.0)
    horizon_candles: Literal[3, 5, 9, 12, 20] = 9
    post_signal_bars: list[CandleBar] = Field(default_factory=list)
    has_lower_timeframe_sequence: bool = False


class IndicatorSignalOutcomeLabel(BaseModel):
    label_version: str
    label_id: str
    indicator_id: str
    symbol: str
    timeframe: TimeframeValue
    signal_direction: Literal["bullish", "bearish", "neutral"]
    signal_time_ns: int
    horizon_candles: Literal[3, 5, 9, 12, 20]
    label_status: Literal["pending", "complete"]
    outcome_label: Literal["TARGET_HIT", "SL_HIT", "PARTIAL_WIN", "BREAKEVEN", "TIME_EXIT", "FAKE_BREAKOUT", "RETEST_SUCCESS", "RETEST_FAIL", "CHOP_NO_FOLLOWTHROUGH"]
    target_first: bool
    stop_first: bool
    same_bar_ambiguous: bool
    conservative_stop_first_used: bool
    mfe: float
    mae: float
    bars_to_target: int | None = None
    bars_to_sl: int | None = None
    counted_as_win: bool = False
    counted_as_failure: bool = False
    counted_in_reliability: bool = False
    no_future_leakage: bool = True
    point_in_time_safe: bool = True
    reason: str


class IndicatorSignalHistorySaveRequest(BaseModel):
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=40)
    indicator_id: str
    timeframe: TimeframeValue = "1m"
    signal_direction: Literal["bullish", "bearish", "neutral"] = "bullish"
    signal_time_ns: int = Field(default=1_714_724_800_000_000_000, ge=0)
    decision_time_ns: int = Field(default=1_714_724_800_000_000_000, ge=0)
    session_phase: str = "unknown"
    regime_id: str = "unknown"
    source_snapshot_id: str | None = None
    source_snapshot_hash: str | None = None
    feature_manifest_version: str = "nine-candle-feature-manifest.v1"
    indicator_registry_version: str | None = None
    signal_value: float | None = None
    signal_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_mask: bool = False
    label_request: IndicatorSignalOutcomeLabelRequest


class IndicatorSignalHistoryRecord(BaseModel):
    history_version: str
    history_id: str
    symbol: str
    indicator_id: str
    timeframe: TimeframeValue
    signal_direction: Literal["bullish", "bearish", "neutral"]
    signal_time_ns: int
    decision_time_ns: int
    session_phase: str
    regime_id: str
    source_snapshot_id: str | None = None
    source_snapshot_hash: str | None = None
    feature_manifest_version: str
    indicator_registry_version: str
    signal_value: float | None = None
    signal_strength: float = Field(ge=0.0, le=1.0)
    missing_mask: bool
    label: IndicatorSignalOutcomeLabel
    counted_in_reliability: bool
    created_at: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True


class IndicatorSignalHistorySummary(BaseModel):
    history_version: str
    symbol: str
    indicator_id: str
    timeframe: TimeframeValue
    record_count: int = Field(ge=0)
    counted_record_count: int = Field(ge=0)
    pending_record_count: int = Field(ge=0)
    complete_record_count: int = Field(ge=0)
    latest_history_id: str | None = None
    latest_signal_time_ns: int | None = None
    storage_backed: bool
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True
    records: list[IndicatorSignalHistoryRecord]
    gates: list[dict[str, Any]]
    notes: list[str]


class IndicatorSignalHistoryIngestCurrentRequest(BaseModel):
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=40)
    timeframe: TimeframeValue = "1m"
    use_real_indicators: bool = False
    include_neutral: bool = False
    max_records: int = Field(default=12, ge=1, le=94)
    horizon_candles: Literal[3, 5, 9, 12, 20] = 3


class IndicatorSignalHistoryIngestCurrentReport(BaseModel):
    ingest_version: str
    symbol: str
    timeframe: TimeframeValue
    source_snapshot_id: str
    source_snapshot_hash: str
    feature_manifest_version: str
    indicator_registry_version: str
    use_real_indicators: bool
    requested_indicator_count: int = Field(ge=0)
    eligible_signal_count: int = Field(ge=0)
    saved_record_count: int = Field(ge=0)
    pending_record_count: int = Field(ge=0)
    counted_record_count: int = Field(ge=0)
    skipped_missing_count: int = Field(ge=0)
    skipped_neutral_count: int = Field(ge=0)
    saved_records: list[IndicatorSignalHistoryRecord]
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True
    closed_candle_only: bool = True
    gates: list[dict[str, Any]]
    notes: list[str]


class IndicatorSignalHistoryCompletePendingRequest(BaseModel):
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=40)
    indicator_id: str
    timeframe: TimeframeValue = "1m"
    history_id: str | None = None
    entry_price: float = Field(gt=0.0)
    stop_price: float = Field(gt=0.0)
    target_price: float = Field(gt=0.0)
    post_signal_bars: list[CandleBar] = Field(default_factory=list)
    has_lower_timeframe_sequence: bool = False
    limit: int = Field(default=100, ge=1, le=1000)


class IndicatorSignalHistoryCompletePendingReport(BaseModel):
    completion_version: str
    symbol: str
    indicator_id: str
    timeframe: TimeframeValue
    scanned_pending_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    still_pending_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    completed_records: list[IndicatorSignalHistoryRecord]
    still_pending_records: list[IndicatorSignalHistoryRecord]
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True
    gates: list[dict[str, Any]]
    notes: list[str]


class IndicatorReliabilityBucket(BaseModel):
    bucket_name: str
    sample_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    neutral_count: int = Field(ge=0)
    raw_success_rate: float = Field(ge=0.0, le=1.0)
    bayesian_success_rate: float = Field(ge=0.0, le=1.0)
    reliability_score: float = Field(ge=0.0, le=1.0)


class IndicatorReliabilityReport(BaseModel):
    reliability_version: str
    symbol: str
    indicator_id: str
    timeframe: TimeframeValue
    registry_version: str
    ontology_version: str
    purpose: str
    category: str
    confirmation_delay_bars: int = Field(ge=0)
    lag_weight: float = Field(ge=0.0, le=1.0)
    history_source: Literal["persistent", "fixture"]
    persisted_history_count: int = Field(ge=0)
    fixture_fallback_used: bool
    minimum_sample_size: int = Field(ge=1)
    sample_count: int = Field(ge=0)
    minimum_sample_pass: bool
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    neutral_count: int = Field(ge=0)
    historical_success_rate: float = Field(ge=0.0, le=1.0)
    historical_failure_rate: float = Field(ge=0.0, le=1.0)
    bayesian_success_rate: float = Field(ge=0.0, le=1.0)
    bayesian_failure_rate: float = Field(ge=0.0, le=1.0)
    per_stock_reliability: float = Field(ge=0.0, le=1.0)
    per_regime_reliability: float = Field(ge=0.0, le=1.0)
    per_session_reliability: float = Field(ge=0.0, le=1.0)
    reciprocal_signal_ratio: float = Field(ge=0.0, le=1.0)
    reciprocal_signal_warning: bool
    reliability_state: Literal["low_evidence", "research_usable", "quarantined"]
    reliability_multiplier_for_lag_vote: float = Field(ge=0.0, le=1.0)
    lag_vote_preview: IndicatorLagVoteRecord
    bucket_rollups: list[IndicatorReliabilityBucket]
    recent_labels: list[IndicatorSignalOutcomeLabel]
    ood_quarantine_required: bool
    regime_shift_quarantine_required: bool
    quarantine_reason: str | None = None
    feeds_reciprocal_signal_detector: bool = True
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True
    gates: list[dict[str, Any]]
    notes: list[str]


class BehaviorIndicatorRegistryGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class BehaviorIndicatorRegistryReport(BaseModel):
    registry_version: str
    generated_at: str
    total_output_groups: int
    self_indicator_count: int
    pta_marker_count: int
    entries: list[BehaviorIndicatorRegistryEntry]
    status_counts: dict[str, int]
    family_counts: dict[str, int]
    required_added_indicators_present: bool
    required_added_indicator_ids: list[str]
    proxy_probability_blocked: bool
    all_entries_have_output_schema: bool
    all_entries_have_warmup: bool
    all_entries_have_pit_policy: bool
    runtime_dependency_on_legacy_stock_app: bool = False
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[BehaviorIndicatorRegistryGate]
    notes: list[str]


IndicatorObservationState = Literal[
    "RISING",
    "FALLING",
    "FLAT",
    "ACCELERATING",
    "DECELERATING",
    "OVERBOUGHT",
    "OVERSOLD",
    "TRENDING",
    "CHOPPY",
    "COMPRESSED",
    "EXPANDING",
    "BULLISH_CROSS",
    "BEARISH_CROSS",
    "BULLISH_DIVERGENCE",
    "BEARISH_DIVERGENCE",
    "NO_EVENT",
    "UNAVAILABLE",
    "FAILED",
]


class IndicatorObservationRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=69, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    max_indicators: int = Field(default=16, ge=1, le=94)
    include_unavailable: bool = True


class IndicatorObservation(BaseModel):
    observation_id: str
    snapshot_id: str
    symbol: str
    exchange: str
    indicator_id: str
    output_name: str
    display_name: str
    family: str
    subfamily: str
    timeframe: TimeframeValue
    parameters: dict[str, Any]
    input_columns: list[str]
    input_price_type: Literal["ohlcv", "hlc", "close", "volume", "derived"]
    raw_value: float | str | bool | None
    formatted_value: str
    unit: str
    normalized_value: float | None = Field(default=None, ge=-1.0, le=1.0)
    rolling_percentile: float | None = Field(default=None, ge=0.0, le=100.0)
    session_percentile: float | None = Field(default=None, ge=0.0, le=100.0)
    regime_percentile: float | None = Field(default=None, ge=0.0, le=100.0)
    z_score: float | None = None
    slope_1: float | None = None
    slope_n: float | None = None
    acceleration: float | None = None
    direction: Literal["bullish", "bearish", "neutral", "mixed", "unavailable"]
    state: IndicatorObservationState
    signal: Literal["buy", "sell", "watch", "neutral", "blocked", "unavailable"]
    signal_strength: float | None = Field(default=None, ge=0.0, le=1.0)
    crossed_reference: bool
    reference_name: str | None = None
    reference_value: float | None = None
    distance_from_reference: float | None = None
    divergence_state: Literal["none", "bullish", "bearish", "hidden_bullish", "hidden_bearish", "unavailable"]
    persistence_bars: int = Field(ge=0)
    bars_since_event: int | None = Field(default=None, ge=0)
    warmup_complete: bool
    available: bool
    availability_reason: str
    quality_score: float = Field(ge=0.0, le=1.0)
    point_in_time_safe: bool
    source_bar_close_time: int | None = Field(default=None, ge=0)
    available_time: int | None = Field(default=None, ge=0)
    decision_time: int = Field(ge=0)
    formula_hash: str
    implementation_version: str


class IndicatorObservationGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class IndicatorObservationReport(BaseModel):
    observation_version: str
    generated_at: str
    symbol: str
    exchange: str
    timeframe: TimeframeValue
    snapshot_id: str
    source_snapshot_hash: str
    decision_time: int = Field(ge=0)
    observation_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    multi_output_indicator_count: int = Field(ge=0)
    observations: list[IndicatorObservation]
    all_observations_have_lineage: bool
    all_available_are_point_in_time_safe: bool
    unavailable_observations_preserved: bool
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[IndicatorObservationGate]
    notes: list[str]


PatternLifecycleState = Literal["forming", "confirmed", "failed", "expired", "developing_not_decision_safe"]


class PatternTaxonomyRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=70, ge=0)
    include_activity_records: bool = True


class HarmonicGeometrySpec(BaseModel):
    pattern_names: list[str]
    anchor_fields: list[str]
    ratio_measurements: list[str]
    ratio_tolerance_pct: float = Field(ge=0.0, le=100.0)
    completion_zone_required: bool
    invalidation_zone_required: bool
    detector_version: str


class TrendlineRespectEvidence(BaseModel):
    touch_count: int = Field(ge=0)
    normalized_touch_error: float = Field(ge=0.0)
    close_through_count: int = Field(ge=0)
    slope_stability: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    volume_response: float = Field(ge=0.0, le=1.0)
    post_touch_excursion_atr: float
    trendline_respect_score: float = Field(ge=0.0, le=1.0)
    objective_evidence_required: bool = True


class PatternTaxonomyEntry(BaseModel):
    pattern_id: str
    display_name: str
    family: Literal["candle", "swing", "harmonic", "level", "flow", "indicator_activity", "forecast"]
    subfamily: str
    pattern_names: list[str]
    required_inputs: list[str]
    output_fields: list[str]
    lifecycle_states: list[PatternLifecycleState]
    point_in_time_safe: bool
    detector_version: str
    lineage_source: str
    decorative_only_blocked: bool
    contributes_to_similarity: bool
    activity_record_required: bool
    objective_evidence_fields: list[str]
    notes: list[str]


class PatternActivityRecord(BaseModel):
    activity_id: str
    source_id: str
    activity_present: bool
    activity_type: str
    activity_direction: Literal["long", "short", "neutral", "mixed"]
    activity_strength: float = Field(ge=0.0, le=1.0)
    activity_start_time: int = Field(ge=0)
    activity_end_time: int = Field(ge=0)
    activity_duration_bars: int = Field(ge=0)
    activity_price_zone: str
    activity_timeframe: TimeframeValue
    activity_parameters: dict[str, Any]
    activity_quality: float = Field(ge=0.0, le=1.0)
    activity_confirmation_state: PatternLifecycleState
    activity_invalidation_state: PatternLifecycleState | None = None
    bars_before_outcome: int = Field(ge=0)
    outcome_distribution_after_activity: dict[str, float]
    reciprocal_signal_candidate: bool
    point_in_time_safe: bool


class CandleNeighborEffectSpec(BaseModel):
    anatomy_features: list[str]
    local_windows: list[str]
    no_wick_detection_required: bool
    neighbor_confirmation_required: bool
    historical_next_window_labels_only: bool


class PatternTaxonomyGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class PatternTaxonomyReport(BaseModel):
    taxonomy_version: str
    generated_at: str
    symbol: str
    timeframe: TimeframeValue
    entry_count: int = Field(ge=0)
    required_family_count: int = Field(ge=0)
    entries: list[PatternTaxonomyEntry]
    harmonic_geometry: HarmonicGeometrySpec
    trendline_respect_evidence: TrendlineRespectEvidence
    candle_neighbor_effect: CandleNeighborEffectSpec
    activity_records: list[PatternActivityRecord]
    all_chart_structures_require_activity_records: bool
    all_entries_have_lifecycle_contracts: bool
    decorative_patterns_blocked: bool
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[PatternTaxonomyGate]
    notes: list[str]


class SevenTimeframeFeatureRuntimeRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    seed: int = Field(default=42, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    decision_time_ns: int | None = Field(default=None, ge=0)


class ClosedBarRuntimeRecord(BaseModel):
    timeframe: TimeframeValue
    aggregation_source: Literal["1m_immutable_snapshot"]
    source_1m_bars: int
    bars_per_aggregate: int = Field(ge=1)
    closed_bars: int = Field(ge=0)
    blocked_incomplete_source_bars: int = Field(ge=0)
    latest_bar_open_time_ns: int | None = Field(default=None, ge=0)
    latest_bar_close_time_ns: int | None = Field(default=None, ge=0)
    available_time_ns: int | None = Field(default=None, ge=0)
    decision_time_ns: int = Field(ge=0)
    aligned_to_session_start: bool
    closed_before_decision: bool
    row_hash: str
    notes: list[str]


class RuntimeIndicatorCoverageRecord(BaseModel):
    timeframe: TimeframeValue
    registered_output_groups: int = Field(ge=0)
    validated_output_groups: int = Field(ge=0)
    proxy_output_groups: int = Field(ge=0)
    blocked_output_groups: int = Field(ge=0)
    probability_enabled_groups: int = Field(ge=0)
    availability_mask: dict[str, Literal["available", "proxy_visible_non_probabilistic", "blocked"]]
    sample_values: dict[str, float | str | None]


class SevenTimeframeFeatureRuntimeGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class SevenTimeframeFeatureRuntimeReport(BaseModel):
    runtime_version: str
    generated_at: str
    symbol: str
    source_timeframe: Literal["1m"]
    required_timeframes: list[TimeframeValue]
    source_bar_count: int
    source_snapshot_hash: str
    decision_time_ns: int
    session_start_offset_minutes: int
    closed_bar_records: list[ClosedBarRuntimeRecord]
    indicator_coverage: list[RuntimeIndicatorCoverageRecord]
    total_registered_output_groups: int
    total_timeframe_indicator_slots: int
    closed_bar_guard_passed: bool
    all_required_timeframes_present: bool
    higher_timeframes_closed_before_decision: bool
    registry_version: str
    source_snapshot_shared_with_kronos: bool
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[SevenTimeframeFeatureRuntimeGate]
    notes: list[str]


class MultiTimeframeConflictRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    seed: int = Field(default=72, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    decision_time_ns: int | None = Field(default=None, ge=0)
    primary_timeframe: TimeframeValue = "5m"


class TimeframeStateRecord(BaseModel):
    timeframe: TimeframeValue
    htf_role: Literal["lower", "intermediate", "higher"]
    closed_bars: int = Field(ge=0)
    latest_bar_close_time_ns: int | None = Field(default=None, ge=0)
    developing_bar_visible: bool
    developing_bar_decision_safe: bool = False
    state_direction: Literal["long", "short", "range", "unavailable"]
    state_strength: float = Field(ge=0.0, le=1.0)
    compression_state: Literal["compressed", "expanding", "normal", "unavailable"]
    aligned_with_primary: bool
    conflict_tags: list[str]
    decision_safe: bool


class MultiTimeframeConflictExplanation(BaseModel):
    conflict_type: Literal[
        "full_alignment",
        "lower_timeframe_pullback_inside_higher_timeframe_trend",
        "lower_timeframe_breakout_into_higher_timeframe_resistance",
        "higher_timeframe_reversal_with_lower_timeframe_continuation_lag",
        "timeframe_compression_conflict",
        "timeframe_data_unavailable",
        "developing_bar_blocked",
    ]
    severity: Literal["info", "watch", "block"]
    timeframes: list[TimeframeValue]
    explanation: str
    recommended_action: Literal["ALLOW_RESEARCH", "WAIT", "NO_TRADE", "BLOCK_CONFIDENCE"]


class MultiTimeframeConflictGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class MultiTimeframeConflictReport(BaseModel):
    conflict_version: str
    generated_at: str
    symbol: str
    primary_timeframe: TimeframeValue
    runtime: SevenTimeframeFeatureRuntimeReport
    seven_timeframe_matrix: list[TimeframeStateRecord]
    conflict_explanations: list[MultiTimeframeConflictExplanation]
    lower_timeframes: list[TimeframeValue]
    higher_timeframes: list[TimeframeValue]
    unavailable_timeframes: list[TimeframeValue]
    full_alignment: bool
    developing_bars_blocked_from_decision: bool
    alignment_score: float = Field(ge=0.0, le=1.0)
    final_mtf_state: Literal["supports_long", "supports_short", "mixed", "avoid", "unavailable"]
    blocks_trade: bool
    no_trade_reason: str | None = None
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[MultiTimeframeConflictGate]
    notes: list[str]


class RealMtfPullbackRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    seed: int = Field(default=163, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    decision_time_ns: int | None = Field(default=None, ge=0)
    primary_timeframe: TimeframeValue = "5m"


class RealMtfPullbackGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class RealMtfPullbackTimeframeSummary(BaseModel):
    timeframe: TimeframeValue
    htf_role: Literal["lower", "intermediate", "higher"]
    state_direction: Literal["long", "short", "range", "unavailable"]
    state_strength: float = Field(ge=0.0, le=1.0)
    compression_state: Literal["compressed", "expanding", "normal", "unavailable"]
    decision_safe: bool
    conflict_tags: list[str]


class RealMtfPullbackReport(BaseModel):
    pullback_version: str
    generated_at: str
    symbol: str
    primary_timeframe: TimeframeValue
    source_conflict_version: str
    primary_direction: Literal["long", "short", "range", "unavailable"]
    higher_timeframe_direction: Literal["long", "short", "range", "unavailable"]
    lower_pullback_direction: Literal["long", "short", "range", "unavailable"]
    pullback_state: Literal[
        "pullback_in_trend",
        "trend_continuation",
        "htf_opposition",
        "range_or_unavailable",
        "developing_blocked",
        "mixed_context",
    ]
    closed_htf_context_passed: bool
    lower_timeframe_pullback_detected: bool
    htf_opposition_detected: bool
    compression_warning: bool
    aligned_timeframes: list[TimeframeValue]
    opposition_timeframes: list[TimeframeValue]
    pullback_timeframes: list[TimeframeValue]
    final_action: Literal["WAIT", "WATCH", "AVOID"]
    final_reason: str
    trader_summary: str
    no_future_leakage: bool
    closed_candle_only: bool
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    timeframe_summaries: list[RealMtfPullbackTimeframeSummary]
    gates: list[RealMtfPullbackGate]
    notes: list[str]


class FeatureSnapshotRecord(BaseModel):
    snapshot_id: str
    symbol: str
    timeframe: TimeframeValue
    decision_time_ns: int = Field(ge=0)
    source_snapshot_hash: str
    feature_version: str
    indicator_registry_version: str
    storage_uri: str
    storage_format: Literal["columnar_jsonl_v1", "parquet_reserved"]
    row_hash: str
    created_at: str
    adjusted_price_version: Literal["raw", "adjusted"]
    feature_count: int = Field(ge=0)
    unavailable_feature_count: int = Field(ge=0)
    proxy_excluded_count: int = Field(ge=0)
    blocked_excluded_count: int = Field(ge=0)
    lineage: dict[str, Any]


class FeatureStoreWriteRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    seed: int = Field(default=42, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    adjusted_price_version: Literal["raw", "adjusted"] = "raw"


class FeatureStoreGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class FeatureStoreWriteReport(BaseModel):
    store_version: str
    generated_at: str
    symbol: str
    source_snapshot_hash: str
    feature_version: str
    registry_version: str
    storage_root: str
    records: list[FeatureSnapshotRecord]
    written_record_count: int
    total_feature_rows: int
    resumable: bool
    corruption_check_passed: bool
    raw_adjusted_mix_blocked: bool
    proxy_or_blocked_indicators_excluded: bool
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[FeatureStoreGate]
    notes: list[str]


class FeatureStoreStatusReport(BaseModel):
    store_version: str
    generated_at: str
    storage_root: str
    metadata_table: Literal["behavior_feature_snapshots"]
    record_count: int
    latest_records: list[FeatureSnapshotRecord]
    indexes: list[str]
    corruption_check_passed: bool
    parquet_reserved: bool
    storage_format: Literal["columnar_jsonl_v1"]
    live_trading_blocked: bool = True
    notes: list[str]


class RedundancyAuditRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    seed: int = Field(default=42, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    fit_start_ns: int | None = Field(default=None, ge=0)
    fit_end_ns: int | None = Field(default=None, ge=0)
    evaluation_start_ns: int | None = Field(default=None, ge=0)
    correlation_threshold: float = Field(default=0.90, ge=0.50, le=1.0)
    cross_family_threshold: float = Field(default=0.70, ge=0.10, le=1.0)


class FeatureFamilyScore(BaseModel):
    family: str
    raw_feature_count: int = Field(ge=0)
    eligible_feature_count: int = Field(ge=0)
    independent_feature_count: int = Field(ge=0)
    suppressed_duplicate_count: int = Field(ge=0)
    raw_weight_sum: float = Field(ge=0.0)
    capped_family_weight: float = Field(ge=0.0, le=1.0)
    family_cap_applied: bool
    representative_features: list[str]


class SuppressedDuplicateFeature(BaseModel):
    feature_id: str
    family: str
    cluster_id: str
    kept_representative: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    method: Literal["spearman", "jaccard", "semantic_family"]
    reason: str


class RedundancyCluster(BaseModel):
    cluster_id: str
    family: str
    method: Literal["spearman", "jaccard", "semantic_family"]
    feature_ids: list[str]
    selected_medoid: str
    average_abs_correlation: float = Field(ge=0.0, le=1.0)
    jaccard_similarity: float = Field(ge=0.0, le=1.0)
    cluster_weight: float = Field(ge=0.0, le=1.0)
    suppressed_features: list[str]


class CrossFamilyCorrelationAudit(BaseModel):
    average_inter_family_correlation: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    penalty_applied: bool
    affected_family_pairs: list[str]
    note: str


class RedundancyAuditGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class RedundancyAuditReport(BaseModel):
    redundancy_model_version: str
    generated_at: str
    symbol: str
    source_snapshot_hash: str
    feature_store_version: str
    registry_version: str
    fit_start_ns: int
    fit_end_ns: int
    evaluation_start_ns: int
    fitting_excludes_evaluation_period: bool
    raw_feature_count: int = Field(ge=0)
    eligible_feature_count: int = Field(ge=0)
    redundancy_cluster_count: int = Field(ge=0)
    effective_independent_feature_count: int = Field(ge=0)
    family_weights: dict[str, float]
    family_scores: list[FeatureFamilyScore]
    clusters: list[RedundancyCluster]
    suppressed_duplicate_features: list[SuppressedDuplicateFeature]
    cross_family_audit: CrossFamilyCorrelationAudit
    family_caps_enforced: bool
    duplicate_inflation_blocked: bool
    no_evaluation_leakage: bool
    deterministic: bool = True
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[RedundancyAuditGate]
    notes: list[str]


class ReplayIndicatorValidationRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    scenario_id: str = Field(default="mock_opening_drive", min_length=1, max_length=80)
    seed: int = Field(default=42, ge=0)
    event_count: int = Field(default=24, ge=8, le=240)
    timeframe: TimeframeValue = "1m"


class ReplayIndicatorPoint(BaseModel):
    sequence_number: int = Field(ge=1)
    timestamp_ns: int = Field(ge=0)
    close: float = Field(gt=0)
    sma_3: float | None = None
    ema_5: float
    rsi_5: float = Field(ge=0, le=100)
    vwap: float = Field(gt=0)
    macd_fast_slow: float
    volume_z: float
    signal_flags: list[str]


class ReplayChartPoint(BaseModel):
    timestamp_ns: int = Field(ge=0)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    indicator_overlay: dict[str, float | None]
    markers: list[str]


class ReplayIndicatorValidationReport(BaseModel):
    validation_version: str
    generated_at: str
    run_id: str
    symbol: str
    scenario_id: str
    seed: int
    event_count: int
    candle_count: int
    indicator_count: int
    chart_point_count: int
    replay_session_id: str
    candle_series: CandleSeries
    indicator_points: list[ReplayIndicatorPoint]
    chart_points: list[ReplayChartPoint]
    deterministic: bool
    input_event_chain_hash: str
    output_hash: str
    no_future_leakage: bool
    runtime_dependency_on_legacy_stock_app: bool = False
    safe_mode: bool = True
    live_trading_blocked: bool = True
    gates: list[RuntimeReadinessGate]
    notes: list[str]


class BehaviorChartReplayRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    scenario_id: str = Field(default="mock_opening_drive", min_length=1, max_length=80)
    seed: int = Field(default=42, ge=0)
    event_count: int = Field(default=24, ge=8, le=240)
    timeframe: TimeframeValue = "1m"
    selected_sequence_number: int | None = Field(default=None, ge=1)


class ChartViewport(BaseModel):
    min_price: float
    max_price: float
    min_timestamp_ns: int
    max_timestamp_ns: int
    candle_count: int
    price_padding_pct: float


class ChartOverlaySummary(BaseModel):
    overlay_key: str
    label: str
    visible: bool
    latest_value: float | None
    min_value: float | None
    max_value: float | None
    point_count: int
    purpose: str


class SelectedCandleEvidence(BaseModel):
    sequence_number: int
    timestamp_ns: int
    candle_direction: Literal["bullish", "bearish", "neutral"]
    body_pct: float
    upper_wick_pct: float
    lower_wick_pct: float
    close_location_value: float
    marker_tags: list[str]
    overlay_values: dict[str, float | None]
    evidence_rows: list[str]
    reason: str


class BehaviorChartReplayReport(BaseModel):
    chart_version: str
    generated_at: str
    run_id: str
    base_validation_version: str
    symbol: str
    scenario_id: str
    seed: int
    timeframe: TimeframeValue
    event_count: int
    candle_count: int
    chart_point_count: int
    selected_sequence_number: int
    viewport: ChartViewport
    chart_points: list[ReplayChartPoint]
    overlays: list[ChartOverlaySummary]
    selected_candle: SelectedCandleEvidence
    input_event_chain_hash: str
    base_output_hash: str
    output_hash: str
    deterministic: bool
    no_future_leakage: bool
    runtime_dependency_on_legacy_stock_app: bool = False
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[RuntimeReadinessGate]
    notes: list[str]


class ReplayIndicatorMatrixRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    scenario_id: str = Field(default="mock_opening_drive", min_length=1, max_length=80)
    seed: int = Field(default=42, ge=0)
    event_count: int = Field(default=24, ge=8, le=240)
    timeframe: TimeframeValue = "1m"
    required_matrix_rows: int = Field(default=32, ge=16, le=32)


class ReplayIndicatorMatrixRow(BaseModel):
    row_id: str
    family: str
    layer_index: int | None = None
    contract_name: str
    source: Literal["replay_candle", "derived_overlay", "behavior_proxy", "safety_proxy"]
    latest_value: float | str | bool | None
    normalized_score: float = Field(ge=-1.0, le=1.0)
    signal: Literal["bullish", "bearish", "neutral", "watch", "blocked"]
    chart_overlay_key: str | None = None
    required_inputs: list[str]
    output_fields: dict[str, float | str | bool | None]
    point_in_time_safe: bool
    readiness_status: Literal["ready", "proxy", "blocked"]
    explanation: str


class ReplayIndicatorMatrixReport(BaseModel):
    matrix_version: str
    generated_at: str
    run_id: str
    base_validation_version: str
    symbol: str
    scenario_id: str
    seed: int
    event_count: int
    timeframe: TimeframeValue
    base_indicator_count: int
    matrix_indicator_count: int
    chart_point_count: int
    ready_rows: int
    proxy_rows: int
    blocked_rows: int
    rows: list[ReplayIndicatorMatrixRow]
    base_output_hash: str
    input_event_chain_hash: str
    output_hash: str
    deterministic: bool
    no_future_leakage: bool
    runtime_dependency_on_legacy_stock_app: bool = False
    safe_mode: bool = True
    live_trading_blocked: bool = True
    gates: list[RuntimeReadinessGate]
    notes: list[str]


class BehaviorIndicatorExpansionRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    scenario_id: str = Field(default="mock_opening_drive", min_length=1, max_length=80)
    seed: int = Field(default=42, ge=0)
    event_count: int = Field(default=24, ge=8, le=240)
    timeframe: TimeframeValue = "1m"
    required_matrix_rows: int = Field(default=32, ge=16, le=32)
    include_proxy: bool = True


class IndicatorExpansionItem(BaseModel):
    row_id: str
    family: str
    layer_index: int | None = None
    contract_name: str
    status: Literal["promoted", "proxy", "blocked"]
    signal: Literal["bullish", "bearish", "neutral", "watch", "blocked"]
    latest_value: float | str | bool | None
    normalized_score: float
    chart_overlay_key: str | None = None
    output_fields: dict[str, float | str | bool | None]
    point_in_time_safe: bool
    explanation: str


class BehaviorIndicatorExpansionReport(BaseModel):
    expansion_version: str
    generated_at: str
    run_id: str
    base_matrix_version: str
    symbol: str
    scenario_id: str
    seed: int
    timeframe: TimeframeValue
    event_count: int
    candidate_output_groups: int
    base_indicator_count: int
    matrix_indicator_count: int
    promoted_indicator_count: int
    proxy_indicator_count: int
    blocked_indicator_count: int
    family_coverage: dict[str, int]
    items: list[IndicatorExpansionItem]
    input_event_chain_hash: str
    matrix_output_hash: str
    output_hash: str
    deterministic: bool
    no_future_leakage: bool
    runtime_dependency_on_legacy_stock_app: bool = False
    safe_mode: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[RuntimeReadinessGate]
    notes: list[str]


class KronosRuntimeStatus(BaseModel):
    kronos_version: str
    service_status: Literal["reserved", "unavailable", "mock_ready", "ready", "error"]
    repo_path: str
    repo_present: bool
    service_path: str
    service_present: bool
    mode: Literal["reserved", "mock", "real"]
    selected_model: Literal["none", "Kronos-mini", "Kronos-small", "Kronos-base"]
    model_policy: dict[str, str]
    dependency_isolated: bool
    api_imports_heavy_ml: bool
    research_only: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class KronosModelInfo(BaseModel):
    model_name: str
    status: Literal["reserved", "mock", "available", "excluded"]
    tokenizer_name: str | None = None
    allowed_for_first_real_adapter: bool
    reason: str


class KronosInputValidation(BaseModel):
    validation_version: str
    symbol: str
    timeframe: TimeframeValue
    candle_count: int
    decision_time_ns: int | None = None
    passed: bool
    future_candle_rejected: bool
    nan_or_inf_rejected: bool
    invalid_ohlc_rejected: bool
    incomplete_candle_rejected: bool
    sequence_mismatch_rejected: bool
    granularity_mismatch_rejected: bool
    input_snapshot_hash: str
    blockers: list[str]
    warnings: list[str]


class ForecastUncertaintyMap(BaseModel):
    lower_path: list[float]
    median_path: list[float]
    upper_path: list[float]
    uncertainty_score: float = Field(ge=0.0, le=1.0)
    discarded_for_high_uncertainty: bool


class ForecastExpiryMeta(BaseModel):
    generated_at: str
    valid_until: str
    horizon_bars: int
    expired: bool = False


class KronosForecastSanityCheck(BaseModel):
    passed: bool
    max_allowed_move_pct: float
    max_observed_move_pct: float
    impossible_move_blocked: bool
    reason: str


class KronosForecastPath(BaseModel):
    scenario_id: str
    path_type: Literal["sampled_forecast_path", "median_forecast_path", "fan_band"]
    candles: list[dict[str, float | int]]
    expected_return_pct: float
    expected_move_atr: float
    trend_direction: Literal["LONG", "SHORT", "SIDEWAYS", "UNKNOWN"]
    range_probability: float = Field(ge=0.0, le=100.0)
    continuation_probability: float = Field(ge=0.0, le=100.0)
    reversal_probability: float = Field(ge=0.0, le=100.0)


class KronosForecastRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=42, ge=0)
    lookback_candles: int = Field(default=64, ge=16, le=512)
    forecast_horizon_bars: int = Field(default=12, ge=1, le=120)
    decision_time_ns: int | None = Field(default=None, ge=0)
    series: CandleSeries | None = None
    replay_snapshot_id: str | None = None
    model_name: Literal["Kronos-mini", "Kronos-base"] = "Kronos-mini"


class SharedSnapshotRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=66, ge=0)
    lookback_candles: int = Field(default=64, ge=16, le=512)
    forecast_horizon_bars: int = Field(default=12, ge=1, le=120)
    decision_time_ns: int | None = Field(default=None, ge=0)
    series: CandleSeries | None = None
    corporate_action_version: str = Field(default="corporate-actions.mock.v1", min_length=1, max_length=80)
    calendar_version: str = Field(default="market-calendar.mock.v1", min_length=1, max_length=80)
    model_name: Literal["Kronos-mini", "Kronos-base"] = "Kronos-mini"
    force_kronos_hash_mismatch: bool = False
    force_decision_time_mismatch: bool = False


class SharedAnalysisSnapshot(BaseModel):
    snapshot_id: str
    symbol: str
    timeframe: TimeframeValue
    decision_time_ns: int
    last_bar_timestamp_ns: int
    closed_ohlcv_bars: list[CandleBar]
    source_snapshot_hash: str
    corporate_action_version: str
    calendar_version: str
    immutable: bool = True
    point_in_time_safe: bool = True


PaperGuidanceBand = Literal["WAIT", "WATCH", "ENTER_PAPER", "AVOID", "SKIP"]


class PaperGuidanceRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    timeframe: TimeframeValue
    series: CandleSeries
    decision_time_ns: int | None = Field(default=None, ge=0)
    direction: TradeDirection = "long"
    higher_timeframe_series: list[CandleSeries] = Field(default_factory=list)
    required_higher_timeframes: list[TimeframeValue] = Field(default_factory=list)
    indicator_ids: list[str] = Field(default_factory=list, max_length=94)
    paper_account_id: str | None = Field(default=None, min_length=1, max_length=80)
    include_kronos: bool = False
    include_orb_playbook: bool = True
    historical_match_count: int = Field(default=0, ge=0)
    timezone_offset_minutes: int = Field(default=330, ge=-720, le=840)


class PaperGuidanceSafetyCheck(BaseModel):
    check_id: str
    name: str
    passed: bool
    severity: Literal["info", "warning", "block"]
    evidence: str


class PaperGuidanceSafetyGate(BaseModel):
    gate_version: str
    stage: Literal["D1_SAFETY_GATE"] = "D1_SAFETY_GATE"
    decision_time_ns: int
    mode: SystemModeValue
    kill_switch_state: Literal["armed", "triggered", "reset_pending"]
    passed: bool
    stop_pipeline: bool
    checks: list[PaperGuidanceSafetyCheck]
    blockers: list[str]
    warnings: list[str]
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    broker_order_created: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class ClosedCandleSnapshot(BaseModel):
    snapshot_version: str
    stage: Literal["D2_CLOSED_CANDLE_SNAPSHOT"] = "D2_CLOSED_CANDLE_SNAPSHOT"
    snapshot_id: str
    snapshot_hash: str = Field(min_length=64, max_length=64)
    symbol: str
    timeframe: TimeframeValue
    decision_time_ns: int
    decision_time: str
    timezone_offset_minutes: int
    bar_count: int = Field(ge=1)
    first_bar_timestamp_ns: int
    last_bar_timestamp_ns: int
    last_bar_close_time_ns: int
    closed_ohlcv_bars: list[CandleBar]
    source_schema_version: str
    immutable: Literal[True] = True
    closed_candle_only: Literal[True] = True
    point_in_time_safe: Literal[True] = True


class PaperGuidanceEntryPlan(BaseModel):
    side: Literal["LONG", "SHORT"]
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    invalidation: str
    size_hint: float = Field(ge=0)
    r_ratio: float = Field(gt=0)


class PaperGuidanceEvidenceVote(BaseModel):
    engine_id: str
    vote: Literal["FOR", "AGAINST", "NEUTRAL"]
    weight: float = Field(ge=0.0, le=1.0)
    lag_penalty: float = Field(ge=0.0, le=1.0)
    note: str


class PaperGuidanceEngineReceipt(BaseModel):
    receipt_version: str
    engine_id: str
    stage: Literal["D3A_SETUP", "D3B_MEMORY", "D4_STRUCTURE", "D6_ARBITER"]
    engine_version: str
    source_snapshot_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)
    status: Literal["completed", "degraded", "skipped"]
    identity_match: bool
    output_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    used_for_probability: Literal[False] = False
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class PaperGuidanceMtfEvidence(BaseModel):
    required_timeframes: list[TimeframeValue]
    supplied_timeframes: list[TimeframeValue]
    usable_timeframes: list[TimeframeValue]
    missing_required_timeframes: list[TimeframeValue]
    snapshot_hashes: dict[str, str]
    indicator_runtime_by_timeframe: dict[str, dict[str, Any]] = Field(default_factory=dict)
    confirmed: bool
    blocks_promotion: bool
    reasons: list[str]


class PaperTradeGuidance(BaseModel):
    guidance_version: str
    guidance_id: str
    symbol: str
    timeframe: TimeframeValue
    decision_time: str
    snapshot_hash: str | None = None
    snapshot: ClosedCandleSnapshot | None = None
    final_band: PaperGuidanceBand
    confidence_cap: float = Field(ge=0.0, le=1.0)
    next_action: Literal["DO_NOTHING", "OFFER_PAPER_TICKET"]
    blockers: list[str]
    warnings: list[str]
    reason_for: list[str]
    reason_against: list[str]
    entry_plan: PaperGuidanceEntryPlan | None = None
    evidence_votes: list[PaperGuidanceEvidenceVote] = Field(default_factory=list)
    engine_receipts: list[PaperGuidanceEngineReceipt] = Field(default_factory=list)
    mtf_evidence: PaperGuidanceMtfEvidence | None = None
    orb_ticket: "OrbGuidanceTicket | None" = None
    arbiter_summary: dict[str, Any] = Field(default_factory=dict)
    engines_run: list[str]
    engines_skipped: list[str]
    memory_summary: dict[str, Any]
    risk_summary: dict[str, Any]
    data_quality: BehaviorDataQualityResult
    point_in_time: PointInTimeGuardResult
    safety_gate: PaperGuidanceSafetyGate
    low_evidence_flag: bool
    historical_match_count: int = Field(ge=0)
    minimum_evidence_count: int = Field(ge=1)
    usable_for_probability: Literal[False] = False
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    paper_execution_attempted: Literal[False] = False
    auto_paper_fill_enabled: Literal[False] = False
    broker_credentials_present: Literal[False] = False
    broker_order_created: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


OrbStrategyFamily = Literal["orb_breakout", "orr_reversal", "hybrid_orb"]
OrbRangeMode = Literal["bar_count", "clock_window"]
OrbSignalType = Literal[
    "BREAKOUT_LONG",
    "BREAKDOWN_SHORT",
    "REVERSAL_LONG",
    "REVERSAL_SHORT",
    "NO_SETUP",
]


class OrbSessionDefinition(BaseModel):
    exchange: Literal["NSE"] = "NSE"
    timezone_name: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    timezone_offset_minutes: Literal[330] = 330
    open_time: str = Field(default="09:15", pattern=r"^\d{2}:\d{2}$")
    close_time: str = Field(default="15:30", pattern=r"^\d{2}:\d{2}$")


class OrbStrategyConfig(BaseModel):
    strategy_family: OrbStrategyFamily = "orb_breakout"
    range_mode: OrbRangeMode = "bar_count"
    orb_bar_count: int = Field(default=3, ge=1, le=60)
    range_start: str = Field(default="09:15", pattern=r"^\d{2}:\d{2}$")
    range_end: str = Field(default="09:30", pattern=r"^\d{2}:\d{2}$")
    entry_cutoff: str = Field(default="11:30", pattern=r"^\d{2}:\d{2}$")
    direction: Literal["long", "short", "both"] = "both"
    breakout_buffer_pct: float = Field(default=0.0, ge=0.0, le=2.0)
    require_close_confirmation: bool = True
    require_volume_confirmation: bool = False
    require_vwap_confirmation: bool = False
    reward_risk_ratio: float = Field(default=2.0, gt=0.0, le=10.0)


class OrbBuildRequest(BaseModel):
    series: CandleSeries
    decision_time_ns: int = Field(ge=0)
    source_snapshot_hash: str | None = Field(default=None, min_length=64, max_length=64)
    session: OrbSessionDefinition = Field(default_factory=OrbSessionDefinition)
    config: OrbStrategyConfig = Field(default_factory=OrbStrategyConfig)


class OrbOpeningRange(BaseModel):
    local_session_date: str
    range_mode: OrbRangeMode
    range_start_local: str
    range_end_local: str
    opening_range_high: float
    opening_range_low: float
    opening_range_width: float = Field(ge=0.0)
    opening_range_width_pct: float = Field(ge=0.0)
    range_volume: float = Field(ge=0.0)
    range_vwap: float | None = None
    range_bar_count: int = Field(ge=1)
    first_bar_timestamp_ns: int
    last_bar_timestamp_ns: int
    lock_time_ns: int
    locked: bool


class OrbSignalCandidate(BaseModel):
    signal_type: OrbSignalType
    side: Literal["LONG", "SHORT", "NONE"]
    signal_timestamp_ns: int | None = None
    signal_close_time_ns: int | None = None
    trigger_price: float | None = None
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    invalidation: str
    reward_risk_ratio: float | None = None
    volume_confirmed: bool
    vwap_confirmed: bool
    close_confirmed: bool
    reason: str


class OrbFeatureRecord(BaseModel):
    session_phase: str
    post_range_bar_count: int = Field(ge=0)
    latest_close_vs_orh_pct: float
    latest_close_vs_orl_pct: float
    opening_range_width_atr: float = Field(ge=0.0)
    post_range_volume_ratio: float = Field(ge=0.0)
    false_break_high: bool
    false_break_low: bool
    source_bar_count: int = Field(ge=0)


class OrbBuildResult(BaseModel):
    orb_version: str
    symbol: str
    timeframe: TimeframeValue
    decision_time_ns: int
    source_snapshot_hash: str | None = None
    session: OrbSessionDefinition
    config: OrbStrategyConfig
    opening_range: OrbOpeningRange | None = None
    signal: OrbSignalCandidate
    features: OrbFeatureRecord
    range_locked: bool
    setup_available: bool
    no_future_leakage: bool
    deterministic_hash: str = Field(min_length=64, max_length=64)
    warnings: list[str]
    gates: list[dict[str, Any]]
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    paper_execution_attempted: Literal[False] = False
    broker_order_created: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class OrbCostModel(BaseModel):
    commission_bps_per_side: float = Field(default=1.5, ge=0.0, le=100.0)
    slippage_bps_per_side: float = Field(default=2.0, ge=0.0, le=100.0)


class OrbDiscoveryRequest(BaseModel):
    series: CandleSeries
    strategy_families: list[OrbStrategyFamily] = Field(
        default_factory=lambda: ["orb_breakout", "orr_reversal", "hybrid_orb"]
    )
    orb_bar_counts: list[int] = Field(default_factory=lambda: [3, 6])
    clock_windows: list[tuple[str, str]] = Field(default_factory=list)
    reward_risk_grid: list[float] = Field(default_factory=lambda: [1.0, 2.0, 3.0], min_length=1)
    volume_confirmation_grid: list[bool] = Field(default_factory=lambda: [False, True])
    costs: OrbCostModel = Field(default_factory=OrbCostModel)
    maximum_combinations: int = Field(default=250, ge=1, le=5000)
    minimum_trades: int = Field(default=5, ge=1, le=10000)


class OrbBacktestTrade(BaseModel):
    combo_id: str
    local_session_date: str
    signal_type: OrbSignalType
    side: Literal["LONG", "SHORT"]
    signal_timestamp_ns: int
    entry_timestamp_ns: int
    entry_price: float
    stop_price: float
    target_price: float
    exit_timestamp_ns: int
    exit_price: float
    outcome: Literal["TARGET_HIT", "STOP_HIT", "TIME_EXIT"]
    same_bar_ambiguous: bool
    conservative_stop_first_used: bool
    gross_r: float
    cost_r: float = Field(ge=0.0)
    net_r: float


class OrbComboMetrics(BaseModel):
    combo_id: str
    strategy_family: OrbStrategyFamily
    range_mode: OrbRangeMode
    orb_bar_count: int | None = None
    clock_window: tuple[str, str] | None = None
    reward_risk_ratio: float
    require_volume_confirmation: bool
    trade_count: int = Field(ge=0)
    win_count: int = Field(ge=0)
    loss_count: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
    gross_r: float
    net_r: float
    profit_factor: float = Field(ge=0.0)
    max_drawdown_r: float = Field(ge=0.0)
    profitable_period_rate: float = Field(ge=0.0, le=1.0)
    composite_score: float
    minimum_trades_pass: bool
    no_future_leakage: bool


class OrbDiscoveryResult(BaseModel):
    discovery_version: str
    request_hash: str = Field(min_length=64, max_length=64)
    symbol: str
    timeframe: TimeframeValue
    combination_count: int = Field(ge=0)
    combination_cap_applied: bool
    ranked_combinations: list[OrbComboMetrics]
    best_by_net_profit: OrbComboMetrics | None = None
    best_by_consistency: OrbComboMetrics | None = None
    best_composite: OrbComboMetrics | None = None
    trades: list[OrbBacktestTrade]
    deterministic_hash: str = Field(min_length=64, max_length=64)
    no_future_leakage: bool
    costs_applied: bool
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    paper_execution_attempted: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class OrbDiscoveryJob(BaseModel):
    job_version: str
    job_id: str
    request_hash: str = Field(min_length=64, max_length=64)
    status: Literal["queued", "running", "completed", "failed"]
    progress_pct: float = Field(ge=0.0, le=100.0)
    result: OrbDiscoveryResult | None = None
    error: str | None = None
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class OrbTimingResearchRequest(BaseModel):
    """v1.97 per-stock ORB clock-window timing research (research-only)."""

    symbols_source: Literal["explicit", "trendforge_latest"] = "explicit"
    symbols: list[str] = Field(default_factory=list, max_length=50)
    timeframe: Literal["1m", "3m", "5m", "15m", "30m"] = "5m"
    clock_windows: list[tuple[str, str]] = Field(
        default_factory=lambda: [
            ("09:15", "09:20"),
            ("09:15", "09:30"),
            ("09:15", "09:35"),
            ("09:15", "09:40"),
        ],
        min_length=2,
        max_length=8,
    )
    reward_risk_grid: list[float] = Field(default_factory=lambda: [1.0, 2.0, 3.0], min_length=1)
    volume_confirmation_grid: list[bool] = Field(default_factory=lambda: [False, True], min_length=1)
    strategy_families: list[OrbStrategyFamily] = Field(
        default_factory=lambda: ["orb_breakout", "orr_reversal", "hybrid_orb"]
    )
    minimum_trades: int = Field(default=10, ge=1, le=10000)
    maximum_combinations: int = Field(default=250, ge=1, le=5000)
    start_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    max_workers: int = Field(default=1, ge=1, le=4)


class OrbTimingWindowRow(BaseModel):
    symbol: str
    clock_window: tuple[str, str]
    best_combo_id: str | None = None
    strategy_family: OrbStrategyFamily | None = None
    reward_risk_ratio: float | None = None
    require_volume_confirmation: bool | None = None
    trade_count: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_r: float = 0.0
    consistency: float = 0.0
    max_drawdown_r: float = 0.0
    composite_score: float = 0.0
    minimum_trades_pass: bool = False
    no_future_leakage: bool = True


class OrbTimingLeaderboardEntry(BaseModel):
    symbol: str
    best_window_composite: tuple[str, str] | None = None
    best_window_consistency: tuple[str, str] | None = None
    best_window_net_r: tuple[str, str] | None = None
    verdict: Literal["OK", "INSUFFICIENT_DATA", "NO_SIGNIFICANT_DIFFERENCE"] = "OK"
    top_composite_score: float = 0.0
    composite_spread: float = 0.0
    session_days: int = 0


class OrbTimingResearchResult(BaseModel):
    result_version: str
    run_id: str
    request_hash: str = Field(min_length=64, max_length=64)
    timeframe: str
    clock_windows: list[tuple[str, str]]
    symbols_requested: list[str]
    symbols_completed: list[str]
    symbols_failed: dict[str, str] = Field(default_factory=dict)
    rows: list[OrbTimingWindowRow] = Field(default_factory=list)
    leaderboard: list[OrbTimingLeaderboardEntry] = Field(default_factory=list)
    universe_window_win_counts: dict[str, int] = Field(default_factory=dict)
    no_significant_difference_threshold_r: float = 1.0
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True
    deterministic_hash: str = Field(min_length=64, max_length=64)


class OrbTimingResearchJob(BaseModel):
    job_version: str
    job_id: str
    request_hash: str = Field(min_length=64, max_length=64)
    status: Literal["queued", "running", "completed", "failed"]
    progress_pct: float = Field(ge=0.0, le=100.0)
    current_symbol: str | None = None
    result: OrbTimingResearchResult | None = None
    error: str | None = None
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class OrbOpeningScenario(BaseModel):
    """v2.01: one session's opening possibility, fully classified (PIT-safe)."""

    symbol: str
    session_date: str
    gap_pct: float
    gap_state: Literal["FLAT", "GAP_UP", "GAP_DOWN", "LARGE_GAP_UP", "LARGE_GAP_DOWN"]
    atr_pct: float = Field(ge=0.0)
    pdh: float = Field(gt=0)
    pdl: float = Field(gt=0)
    pdc: float = Field(gt=0)
    pivot: float
    bc: float
    tc: float
    cpr_width: float = Field(ge=0.0)
    width_atr: float = Field(ge=0.0)
    width_pct: float = Field(ge=0.0)
    cpr_class: Literal["NARROW", "NORMAL", "WIDE"]
    zone_at_open: Literal["Z1", "Z2", "Z3", "Z4", "Z5"]
    context_suspect: bool = False
    suspect_reason: str | None = None


class OrbProofThresholds(BaseModel):
    minimum_overall_trades: int = Field(default=20, ge=1, le=100000)
    minimum_oos_trades: int = Field(default=5, ge=1, le=100000)
    minimum_oos_profit_factor: float = Field(default=1.0, ge=0.0, le=100.0)
    minimum_oos_net_r: float = Field(default=0.0, ge=-100000.0, le=100000.0)
    minimum_walk_forward_pass_rate: float = Field(default=0.60, ge=0.0, le=1.0)


class OrbProofRequest(BaseModel):
    discovery_request: OrbDiscoveryRequest
    top_k: int = Field(default=20, ge=1, le=100)
    holdout_fraction: float = Field(default=0.25, ge=0.10, le=0.50)
    walk_forward_folds: int = Field(default=4, ge=2, le=12)
    thresholds: OrbProofThresholds = Field(default_factory=OrbProofThresholds)


class OrbWalkForwardFold(BaseModel):
    fold_id: str
    start_date: str
    end_date: str
    metrics: OrbComboMetrics | None = None
    passed: bool
    reasons: list[str]


class OrbComboProof(BaseModel):
    combo_id: str
    overall_metrics: OrbComboMetrics
    holdout_metrics: OrbComboMetrics | None = None
    walk_forward_folds: list[OrbWalkForwardFold]
    oos_passed: bool
    walk_forward_pass_rate: float = Field(ge=0.0, le=1.0)
    repeated_success_passed: bool
    promotion_eligible: bool
    reasons: list[str]


class OrbProofReport(BaseModel):
    proof_version: str
    proof_id: str
    proof_hash: str = Field(min_length=64, max_length=64)
    request_hash: str = Field(min_length=64, max_length=64)
    symbol: str
    timeframe: TimeframeValue
    train_dates: list[str]
    holdout_dates: list[str]
    combo_proofs: list[OrbComboProof]
    eligible_combo_ids: list[str]
    deterministic: bool
    no_future_leakage: bool
    selection_scope: str = "train_only"
    fold_scheme: str = "expanding_train"
    thresholds_used: dict[str, float] = Field(default_factory=dict)
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class OrbPlaybookPromotionRequest(BaseModel):
    proof_id: str
    combo_id: str
    promoted_by: str = Field(min_length=1, max_length=80)


class OrbPlaybook(BaseModel):
    playbook_version: str
    playbook_id: str
    symbol: str
    timeframe: TimeframeValue
    combo_id: str
    config: OrbStrategyConfig
    proof_id: str
    proof_hash: str = Field(min_length=64, max_length=64)
    metrics: OrbComboMetrics
    promoted_by: str
    promoted_at: str
    status: Literal["active", "retired"] = "active"
    storage_backend: Literal["atomic_json"] = "atomic_json"
    research_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class OrbGuidanceTicket(BaseModel):
    ticket_version: str
    guidance_id: str
    symbol: str
    timeframe: TimeframeValue
    decision_time_ns: int
    source_snapshot_hash: str = Field(min_length=64, max_length=64)
    playbook_id: str | None = None
    proof_id: str | None = None
    proof_hash: str | None = Field(default=None, min_length=64, max_length=64)
    strategy_family: OrbStrategyFamily | None = None
    candidate_state: Literal[
        "NO_PLAYBOOK",
        "NO_SETUP",
        "BLOCKED",
        "WATCH",
        "PAPER_CANDIDATE",
    ]
    final_band: PaperGuidanceBand
    opening_range: OrbOpeningRange | None = None
    signal: OrbSignalCandidate | None = None
    entry_plan: PaperGuidanceEntryPlan | None = None
    proof_metrics: OrbComboMetrics | None = None
    historical_match_count: int = Field(ge=0)
    minimum_evidence_count: int = Field(ge=1)
    mtf_complete: bool
    liquidity_grade: Literal["A", "B", "C", "UNKNOWN"]
    trap_score: float = Field(ge=0.0, le=1.0)
    can_record_paper: bool
    explicit_approval_required: Literal[True] = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    deterministic_hash: str = Field(min_length=64, max_length=64)
    research_only: Literal[True] = True
    simulation_only: Literal[True] = True
    trade_allowed: Literal[False] = False
    paper_execution_attempted: Literal[False] = False
    broker_order_created: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class SimulatedPaperRecordApprovalRequest(BaseModel):
    guidance_id: str = Field(min_length=1, max_length=80)
    source_snapshot_hash: str = Field(min_length=64, max_length=64)
    approved_by: str = Field(min_length=1, max_length=80)
    approval_text: Literal["RECORD_SIMULATED_PAPER_TRADE"]
    quantity: int = Field(default=1, ge=1, le=1_000_000)
    note: str = Field(default="", max_length=500)


class SimulatedPaperTradeRecord(BaseModel):
    record_version: str
    paper_record_id: str
    guidance_id: str
    symbol: str
    timeframe: TimeframeValue
    source_snapshot_hash: str = Field(min_length=64, max_length=64)
    playbook_id: str
    proof_id: str
    proof_hash: str = Field(min_length=64, max_length=64)
    signal_type: OrbSignalType
    side: Literal["LONG", "SHORT"]
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    invalidation: str
    risk_reward_ratio: float = Field(gt=0)
    quantity: int = Field(ge=1)
    approved_by: str
    approved_at: str
    note: str
    status: Literal["RECORDED"] = "RECORDED"
    storage_backend: Literal["atomic_json"] = "atomic_json"
    simulation_only: Literal[True] = True
    human_approved: Literal[True] = True
    trade_allowed: Literal[False] = False
    execution_attempted: Literal[False] = False
    broker_order_created: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class SimulatedPaperLifecycleObservationRequest(BaseModel):
    paper_record_id: str = Field(min_length=1, max_length=80)
    source_snapshot_hash: str = Field(min_length=64, max_length=64)
    series: CandleSeries
    observation_time_ns: int = Field(ge=0)
    max_holding_bars: int = Field(default=24, ge=1, le=500)
    observation_text: Literal["EVALUATE_SIMULATED_PAPER_OUTCOME"]


class SimulatedExecutionCostBreakdown(BaseModel):
    spread_bps: float = Field(ge=0.0)
    slippage_bps: float = Field(ge=0.0)
    impact_bps: float = Field(ge=0.0)
    brokerage_bps: float = Field(ge=0.0)
    total_cost_per_unit: float = Field(ge=0.0)
    total_cost_r: float = Field(ge=0.0)


class SimulatedPaperLifecycleOutcome(BaseModel):
    outcome_version: str
    outcome_id: str
    paper_record_id: str
    guidance_id: str
    playbook_id: str
    proof_id: str
    proof_hash: str = Field(min_length=64, max_length=64)
    symbol: str
    timeframe: TimeframeValue
    source_snapshot_hash: str = Field(min_length=64, max_length=64)
    observation_snapshot_hash: str = Field(min_length=64, max_length=64)
    decision_time_ns: int = Field(ge=0)
    observation_time_ns: int = Field(ge=0)
    side: Literal["LONG", "SHORT"]
    entry_trigger: float = Field(gt=0.0)
    simulated_fill_price: float | None = Field(default=None, gt=0.0)
    exit_price: float | None = Field(default=None, gt=0.0)
    stop: float = Field(gt=0.0)
    target: float = Field(gt=0.0)
    fill_status: Literal["NOT_FILLED", "FILLED"]
    lifecycle_status: Literal["PENDING_TRIGGER", "OPEN", "COMPLETED"]
    outcome_label: Literal[
        "PENDING",
        "NO_FILL",
        "TARGET_HIT",
        "STOP_HIT",
        "TIME_EXIT",
    ]
    completed: bool
    bars_observed: int = Field(ge=0)
    bars_to_fill: int | None = Field(default=None, ge=1)
    bars_to_target: int | None = Field(default=None, ge=1)
    bars_to_stop: int | None = Field(default=None, ge=1)
    same_bar_ambiguous: bool
    conservative_stop_first_used: bool
    mfe: float = Field(ge=0.0)
    mae: float = Field(ge=0.0)
    gross_r: float
    net_r: float
    costs: SimulatedExecutionCostBreakdown
    reason: str
    integrity_hash: str = Field(min_length=64, max_length=64)
    point_in_time_safe: Literal[True] = True
    no_future_leakage: Literal[True] = True
    deterministic: Literal[True] = True
    simulation_only: Literal[True] = True
    human_approved_source: Literal[True] = True
    automatic_fill_attempted: Literal[False] = False
    external_execution_attempted: Literal[False] = False
    broker_order_created: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class OrbPaperReliabilityReport(BaseModel):
    reliability_version: str
    playbook_id: str
    symbol: str
    timeframe: TimeframeValue
    completed_sample_count: int = Field(ge=0)
    win_count: int = Field(ge=0)
    loss_count: int = Field(ge=0)
    time_exit_count: int = Field(ge=0)
    excluded_outcome_count: int = Field(ge=0)
    orphan_outcome_count: int = Field(ge=0)
    minimum_sample_count: int = Field(ge=1)
    minimum_sample_pass: bool
    observed_win_rate: float = Field(ge=0.0, le=1.0)
    bayesian_win_rate: float = Field(ge=0.0, le=1.0)
    average_net_r: float
    reliability_state: Literal[
        "LOW_EVIDENCE",
        "RESEARCH_USABLE",
        "QUARANTINE_RECOMMENDED",
    ]
    last_completed_outcome_id: str | None = None
    reason: str
    can_boost_guidance: Literal[False] = False
    can_promote_playbook: Literal[False] = False
    can_retire_playbook: Literal[False] = False
    model_weights_updated: Literal[False] = False
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class PaperGuidanceStorageMonitor(BaseModel):
    monitor_version: str
    generated_at: str
    stores: list[dict[str, Any]]
    integrity_passed: bool
    guidance_ticket_count: int = Field(ge=0)
    paper_record_count: int = Field(ge=0)
    outcome_record_count: int = Field(ge=0)
    completed_outcome_count: int = Field(ge=0)
    orphan_outcome_count: int = Field(ge=0)
    stale_ticket_count: int = Field(ge=0)
    retention_days: int = Field(ge=1)
    retention_candidate_count: int = Field(ge=0)
    retention_action: Literal["PREVIEW_ONLY"] = "PREVIEW_ONLY"
    last_observation_time_ns: int | None = Field(default=None, ge=0)
    blockers: list[str] = Field(default_factory=list)
    automatic_deletion_enabled: Literal[False] = False
    trade_allowed: Literal[False] = False
    order_routing_enabled: Literal[False] = False
    live_trading_blocked: Literal[True] = True


class KronosSnapshotReceipt(BaseModel):
    receipt_version: str
    snapshot_id: str | None
    source_snapshot_hash: str
    kronos_input_snapshot_id: str | None
    kronos_input_snapshot_hash: str
    decision_time_ns: int | None
    last_bar_timestamp_ns: int | None
    forecast_run_id: str
    identity_echo_complete: bool
    kronos_cannot_execute_orders: bool = True
    kronos_cannot_override_no_trade: bool = True
    kronos_cannot_override_risk: bool = True


class TwinSnapshotIntegrity(BaseModel):
    integrity_version: str
    generated_at: str
    symbol: str
    timeframe: TimeframeValue
    snapshot_id: str
    source_snapshot_hash: str
    decision_time_ns: int
    last_bar_timestamp_ns: int
    kronos_receipt: KronosSnapshotReceipt
    identity_match: bool
    mismatch_fields: list[str]
    fail_closed: bool
    twin_comparison_allowed: bool
    arbiter_action: Literal["BEHAVIOR_ONLY", "WAIT", "NO_TRADE", "RESEARCH_COMPARE_ALLOWED"]
    reason: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class KronosSharedSnapshotForecastReport(BaseModel):
    report_version: str
    generated_at: str
    snapshot: SharedAnalysisSnapshot
    kronos_forecast: KronosForecastResult
    receipt: KronosSnapshotReceipt
    integrity: TwinSnapshotIntegrity
    behavior_can_continue_without_kronos: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class KronosForecastResult(BaseModel):
    forecast_version: str
    generated_at: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    source_mode: Literal["mock", "replay", "simulation", "paper", "live"]
    model_name: str
    model_version: str
    tokenizer_name: str
    input_validation: KronosInputValidation
    forecast_path: KronosForecastPath
    uncertainty: ForecastUncertaintyMap
    expiry: ForecastExpiryMeta
    sanity_check: KronosForecastSanityCheck
    forecast_confidence: float = Field(ge=0.0, le=1.0)
    input_snapshot_id: str | None = None
    input_snapshot_hash: str
    output_hash: str
    deterministic: bool
    no_future_leakage: bool
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    kronos_cannot_execute_orders: bool = True
    kronos_cannot_override_no_trade: bool = True
    kronos_cannot_override_risk: bool = True
    notes: list[str]


class TwinEngineComparison(BaseModel):
    twin_version: str
    generated_at: str
    run_id: str
    symbol: str
    behavior_decision: str
    behavior_trade_allowed: bool
    behavior_risk_blocked: bool
    kronos_available: bool
    kronos_direction: Literal["LONG", "SHORT", "SIDEWAYS", "UNKNOWN"]
    kronos_confidence: float = Field(ge=0.0, le=1.0)
    agreement_state: Literal["AGREE_LONG", "AGREE_SHORT", "SOFT_CONFLICT", "HARD_CONFLICT", "LOW_CONFIDENCE", "LOW_EVIDENCE", "WAIT", "NO_TRADE"]
    arbiter_action: Literal["RESEARCH_CANDIDATE", "WAIT", "NO_TRADE"]
    agreement_score: float = Field(ge=0.0, le=1.0)
    conflict_reasons: list[str]
    evidence_hash: str
    twin_agreement_hash: str
    kronos: KronosForecastResult | None = None
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    kronos_cannot_execute_orders: bool = True
    kronos_cannot_override_no_trade: bool = True
    kronos_cannot_override_risk: bool = True
    notes: list[str]


class KronosMetrics(BaseModel):
    metrics_version: str
    generated_at: str
    service_status: Literal["reserved", "unavailable", "mock_ready", "ready", "error"]
    inference_latency_ms: float
    timeout_count: int
    oom_count: int
    forecast_count: int
    service_latency_below_budget: bool
    api_imports_heavy_ml: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class KronosServiceBridgeStatus(BaseModel):
    bridge_version: str
    generated_at: str
    service_url: str | None
    service_configured: bool
    service_present: bool
    health_checked: bool
    health_ok: bool
    service_status: Literal["reserved", "unavailable", "mock_ready", "ready", "timeout", "error"]
    timeout_ms: int
    fallback_to_mock: bool
    fallback_reason: str
    dependency_isolated: bool = True
    api_imports_heavy_ml: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class KronosBacktestRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=42, ge=0)
    scenario_count: int = Field(default=3, ge=1, le=25)


class KronosBacktestResult(BaseModel):
    backtest_version: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    scenario_count: int
    deterministic: bool
    average_direction_score: float = Field(ge=0.0, le=1.0)
    average_sanity_pass_rate: float = Field(ge=0.0, le=1.0)
    promotion_allowed: bool
    blockers: list[str]
    evidence_hash: str
    valid_until: str | None = None
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    kronos_cannot_execute_orders: bool = True
    kronos_cannot_override_no_trade: bool = True
    kronos_cannot_override_risk: bool = True
    notes: list[str]


class TwinConflictRecord(BaseModel):
    conflict_id: str
    symbol: str
    agreement_state: str
    behavior_decision: str
    kronos_direction: str
    conflict_reasons: list[str]
    evidence_hash: str
    created_at: str


class TwinReliabilityReport(BaseModel):
    reliability_version: str
    symbol: str
    sample_count: int
    behavior_only_accuracy: float = Field(ge=0.0, le=1.0)
    kronos_only_accuracy: float = Field(ge=0.0, le=1.0)
    twin_arbiter_accuracy: float = Field(ge=0.0, le=1.0)
    fakeout_avoidance: float = Field(ge=0.0, le=1.0)
    no_trade_quality: float = Field(ge=0.0, le=1.0)
    calibration_error: float = Field(ge=0.0, le=1.0)
    minimum_sample_pass: bool
    notes: list[str]


class TwinTournamentRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=42, ge=0)
    scenario_count: int = Field(default=3, ge=1, le=12)


class TwinTournamentResult(BaseModel):
    tournament_version: str
    run_id: str
    symbol: str
    scenario_count: int
    deterministic: bool
    behavior_score: float = Field(ge=0.0, le=1.0)
    kronos_score: float = Field(ge=0.0, le=1.0)
    twin_score: float = Field(ge=0.0, le=1.0)
    leaderboard: list[dict[str, float | str]]
    promotion_allowed: bool
    evidence_hash: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class SignalIntentBundle(BaseModel):
    intent_version: str
    intent_id: str
    intent_signature: str
    duplicate_key: str
    duplicate_intent_blocked: bool
    symbol: str
    timeframe: TimeframeValue
    side: Literal["LONG", "SHORT", "WAIT", "NO_TRADE"]
    entry_zone: str
    stop_loss: float | None
    target: float | None
    risk_reward: float
    position_size_suggestion: int
    valid_until: str
    expired: bool
    expiry_enforced: bool
    behavior_decision: str
    kronos_decision: str
    twin_decision: str
    twin_agreement_hash: str
    evidence_hash: str
    kill_switch_state: str
    kill_switch_rechecked: bool
    human_veto_required: bool
    human_veto_active: bool
    mode: SystemModeValue
    mode_permission: Literal["mock_preview_only", "simulation_preview_only", "replay_preview_only", "paper_blocked", "live_blocked"]
    permission_matrix: list[dict[str, str | bool]]
    replay_snapshot_id: str | None
    model_version: str
    rule_version: str
    data_version: str
    feature_version: str
    export_status: Literal["preview_only", "pending_for_openalgo", "cancelled", "expired"]
    export_allowed: bool = False
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class BotHandoffVerificationRequest(BaseModel):
    intent: SignalIntentBundle
    seen_duplicate_keys: list[str] = Field(default_factory=list)
    external_human_approval_present: bool = False
    external_risk_check_passed: bool = False
    external_account_state_checked: bool = False
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"] = "openalgo"


class BotHandoffVerificationReport(BaseModel):
    verifier_version: str
    verified_at: str
    intent_id: str
    symbol: str
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"]
    accepted_for_external_review: bool
    rejected: bool
    rejection_reasons: list[str]
    gate_results: list[dict[str, str | bool]]
    signature_valid: bool
    duplicate_detected: bool
    expired: bool
    mode_permission: str
    kill_switch_rechecked: bool
    human_veto_required: bool
    external_human_approval_present: bool
    external_risk_check_passed: bool
    external_account_state_checked: bool
    broker_credentials_present: bool
    broker_order_created: bool
    export_allowed: bool
    verification_hash: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class ExecutorRejectionExample(BaseModel):
    case_id: str
    title: str
    mutated_fields: dict[str, Any]
    expected_rejection_reasons: list[str]
    expected_executor_action: Literal["reject", "ignore", "manual_review_only"]


class ExecutorDryRunPackageRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"] = "openalgo"
    requested_by: str = Field(default="local_user", min_length=1, max_length=80)
    include_rejection_examples: bool = True
    seen_duplicate_keys: list[str] = Field(default_factory=list)
    external_human_approval_present: bool = False
    external_risk_check_passed: bool = False
    external_account_state_checked: bool = False
    retention_days: int = Field(default=30, ge=1, le=365)


class ExecutorDryRunPackage(BaseModel):
    package_version: str
    package_id: str
    created_at: str
    symbol: str
    target_executor: Literal["openalgo", "trading_bot", "paper_bot"]
    requested_by: str
    intent: SignalIntentBundle
    verification: BotHandoffVerificationReport
    handoff_contract: dict[str, Any]
    executor_required_checks: list[str]
    rejection_examples: list[ExecutorRejectionExample]
    artifact_dir: str
    package_file_path: str
    manifest_file_path: str
    package_sha256: str
    manifest_sha256: str
    package_size_bytes: int
    manifest_size_bytes: int
    package_hash: str
    dry_run_only: bool = True
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class ExecutorDryRunPackageVerification(BaseModel):
    verification_version: str
    package_id: str
    verified_at: str
    package_file_exists: bool
    manifest_file_exists: bool
    package_sha256_matches: bool
    manifest_sha256_matches: bool
    package_json_parseable: bool
    verified: bool
    issues: list[str]
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorGoldenFixture(BaseModel):
    fixture_version: str
    fixture_id: str
    scenario: Literal["accepted_for_review", "missing_external_checks", "duplicate_intent", "expired_intent"]
    expected_accepted_for_external_review: bool
    expected_rejected: bool
    expected_rejection_reasons: list[str]
    package: ExecutorDryRunPackage
    expected_package_sha256: str
    expected_manifest_sha256: str
    expected_package_hash: str
    deterministic: bool = True
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorGoldenFixtureRegistry(BaseModel):
    registry_version: str
    generated_at: str
    fixture_count: int
    fixtures: list[ExecutorGoldenFixture]
    fixture_hashes: dict[str, str]
    registry_hash: str
    deterministic: bool = True
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorGoldenFixtureVerification(BaseModel):
    verification_version: str
    fixture_id: str
    verified_at: str
    package_verification: ExecutorDryRunPackageVerification
    acceptance_matches: bool
    rejection_reasons_match: bool
    package_hash_matches: bool
    safety_invariants_match: bool
    passed: bool
    issues: list[str]
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorAdapterObservedResult(BaseModel):
    fixture_id: str
    accepted_for_external_review: bool
    rejected: bool
    rejection_reasons: list[str]
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorAdapterConformanceRequest(BaseModel):
    adapter_name: str = Field(min_length=1, max_length=100)
    adapter_version: str = Field(min_length=1, max_length=100)
    registry_hash: str = Field(min_length=64, max_length=64)
    observed_results: list[ExecutorAdapterObservedResult]


class ExecutorAdapterConformanceCase(BaseModel):
    fixture_id: str
    expected_accepted_for_external_review: bool
    observed_accepted_for_external_review: bool
    expected_rejected: bool
    observed_rejected: bool
    expected_rejection_reasons: list[str]
    observed_rejection_reasons: list[str]
    outcome_matches: bool
    rejection_reasons_match: bool
    safety_invariants_match: bool
    passed: bool
    issues: list[str]


class ExecutorAdapterConformanceReport(BaseModel):
    conformance_version: str
    evaluated_at: str
    adapter_name: str
    adapter_version: str
    registry_hash: str
    registry_hash_matches: bool
    expected_fixture_count: int
    observed_fixture_count: int
    passed_count: int
    all_passed: bool
    missing_fixture_ids: list[str]
    unexpected_fixture_ids: list[str]
    duplicate_fixture_ids: list[str]
    cases: list[ExecutorAdapterConformanceCase]
    report_hash: str
    signature_algorithm: str
    promotion_allowed: bool = False
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class ExecutorTransportEnqueueRequest(BaseModel):
    package: ExecutorDryRunPackage
    adapter_url: str | None = None
    service_identity: str = Field(default="trade-vision-research", min_length=3, max_length=100)
    max_attempts: int = Field(default=3, ge=1, le=10)


class ExecutorTransportAcknowledgement(BaseModel):
    acknowledgement_version: str
    delivery_id: str
    idempotency_key: str
    adapter_name: str
    adapter_version: str
    receipt_id: str
    received_at: str
    accepted_for_external_review: bool
    duplicate: bool
    package_hash: str
    broker_credentials_received: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorTransportOutboxRecord(BaseModel):
    transport_version: str
    delivery_id: str
    idempotency_key: str
    created_at: str
    updated_at: str
    adapter_url: str | None
    service_identity: str
    package: ExecutorDryRunPackage
    status: Literal["pending", "delivering", "acknowledged", "retry_wait", "manual_review", "cancelled", "dead_letter"]
    attempt_count: int
    max_attempts: int
    next_attempt_at: str | None
    last_attempt_at: str | None
    last_error: str | None
    acknowledgement: ExecutorTransportAcknowledgement | None
    automatic_execution_allowed: bool = False
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorTransportDeliveryResult(BaseModel):
    delivery_version: str
    delivered_at: str
    delivery_id: str
    idempotency_key: str
    status: Literal["acknowledged", "retry_wait", "manual_review", "dead_letter", "cancelled", "circuit_open"]
    attempt_count: int
    retryable: bool
    next_attempt_at: str | None
    acknowledgement: ExecutorTransportAcknowledgement | None
    error_code: str | None
    error_message: str | None
    circuit_state: Literal["closed", "open", "half_open"]
    wait_required: bool = True
    promotion_allowed: bool = False
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ExecutorTransportStatus(BaseModel):
    status_version: str
    generated_at: str
    adapter_url: str | None
    configured: bool
    health_checked: bool
    health_ok: bool
    service_identity: str
    service_auth_configured: bool
    timeout_ms: int
    circuit_state: Literal["closed", "open", "half_open"]
    circuit_failure_count: int
    circuit_failure_threshold: int
    circuit_open_until: str | None
    pending_count: int
    retry_wait_count: int
    acknowledged_count: int
    manual_review_count: int
    cancelled_count: int = 0
    dead_letter_count: int = 0
    automatic_execution_allowed: bool = False
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class ExecutorTransportOperatorAction(BaseModel):
    actor_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=3, max_length=500)


class ExecutorTransportTrace(BaseModel):
    trace_id: str
    delivery_id: str
    event_time: str
    event_type: Literal[
        "enqueued",
        "delivery_started",
        "acknowledged",
        "retry_scheduled",
        "manual_review",
        "dead_lettered",
        "cancelled",
        "operator_retry",
        "recovered",
        "circuit_blocked",
    ]
    status: str
    attempt_count: int
    latency_ms: float | None
    error_code: str | None
    actor_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    previous_trace_hash: str | None = None
    trace_hash: str = ""


class ExecutorTransportWorkerRequest(BaseModel):
    actor_id: str = Field(default="transport_worker", min_length=1, max_length=80)
    concurrency: int = Field(default=2, ge=1, le=8)
    limit: int = Field(default=20, ge=1, le=100)
    stale_after_seconds: int = Field(default=30, ge=5, le=3600)


class ExecutorTransportWorkerRun(BaseModel):
    worker_version: str
    run_id: str
    started_at: str
    completed_at: str
    actor_id: str
    concurrency: int
    recovered_count: int
    due_count: int
    processed_count: int
    acknowledged_count: int
    retry_wait_count: int
    manual_review_count: int
    dead_letter_count: int
    circuit_open_count: int
    results: list[ExecutorTransportDeliveryResult]
    graceful_shutdown: bool = True
    automatic_execution_allowed: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class TransportHealthSample(BaseModel):
    sample_id: str
    sampled_at: str
    configured: bool
    authenticated: bool
    health_ok: bool
    circuit_state: Literal["closed", "open", "half_open"]
    latency_ms: float | None
    pending_count: int
    retry_wait_count: int
    dead_letter_count: int
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class TransportSloObjective(BaseModel):
    objective_id: str
    name: str
    target: float
    observed: float
    unit: str
    status: Literal["pass", "warn", "fail", "low_evidence"]
    sample_count: int
    minimum_sample_count: int
    blocks_promotion: bool
    reason: str


class TransportAlert(BaseModel):
    alert_id: str
    severity: Literal["info", "warning", "critical"]
    code: str
    message: str
    active: bool
    runbook: str


class TransportIncident(BaseModel):
    incident_id: str
    opened_at: str
    updated_at: str
    status: Literal["open", "acknowledged", "resolved"]
    severity: Literal["warning", "critical"]
    title: str
    alert_codes: list[str]
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None
    resolution_note: str | None = None
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class TransportIncidentAction(BaseModel):
    actor_id: str = Field(min_length=1, max_length=80)
    note: str = Field(min_length=3, max_length=500)


class TransportResilienceReport(BaseModel):
    resilience_version: str
    generated_at: str
    evidence_window: int
    health_samples: int
    delivery_attempts: int
    successful_deliveries: int
    failed_deliveries: int
    availability_pct: float
    p95_delivery_latency_ms: float
    retry_rate_pct: float
    backlog_count: int
    dead_letter_count: int
    objectives: list[TransportSloObjective]
    alerts: list[TransportAlert]
    incident: TransportIncident | None
    overall_status: Literal["healthy", "degraded", "critical", "low_evidence"]
    promotion_allowed: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class TransportFaultHarnessRequest(BaseModel):
    sample_count: int = Field(default=1000, ge=100, le=10000)


class TransportFaultScenarioResult(BaseModel):
    scenario: Literal["healthy", "latency_breach", "availability_breach", "backlog_breach", "dead_letter", "circuit_open"]
    expected_status: Literal["healthy", "degraded", "critical"]
    observed_status: Literal["healthy", "degraded", "critical", "low_evidence"]
    expected_alert_code: str | None
    observed_alert_codes: list[str]
    passed: bool


class TransportFaultHarnessReport(BaseModel):
    harness_version: str
    generated_at: str
    sample_count: int
    deterministic: bool
    passed_count: int
    scenario_count: int
    all_passed: bool
    scenarios: list[TransportFaultScenarioResult]
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class TransportTraceIntegrityReport(BaseModel):
    verification_version: str
    verified_at: str
    delivery_id: str | None
    trace_count: int
    verified_count: int
    valid: bool
    issues: list[str]
    head_hash: str | None
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class TransportSecurityCheck(BaseModel):
    check_id: str
    name: str
    passed: bool
    severity: Literal["info", "warning", "critical"]
    evidence: str


class TransportSecurityPosture(BaseModel):
    security_version: str
    generated_at: str
    active_key_configured: bool
    previous_key_configured: bool
    adapter_allowlist: list[str]
    nonce_replay_protection: bool
    timestamp_skew_seconds: int
    max_request_bytes: int
    rate_limit_per_minute: int
    trace_integrity: TransportTraceIntegrityReport
    checks: list[TransportSecurityCheck]
    overall_status: Literal["pass", "warn", "fail"]
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class TransportSecurityThreatResult(BaseModel):
    threat: Literal[
        "invalid_signature",
        "stale_timestamp",
        "replayed_nonce",
        "disallowed_host",
        "oversized_payload",
        "unsafe_ack",
        "trace_tamper",
    ]
    blocked: bool
    expected_control: str


class TransportSecurityThreatReport(BaseModel):
    report_version: str
    generated_at: str
    passed_count: int
    threat_count: int
    all_passed: bool
    results: list[TransportSecurityThreatResult]
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class DeploymentConfigurationFingerprint(BaseModel):
    fingerprint_version: str
    generated_at: str
    fingerprint: str
    expected_fingerprint: str | None
    drift_detected: bool
    non_secret_configuration: dict[str, str | int | bool | None]
    secrets_included: bool = False


class DatabaseBackupArtifact(BaseModel):
    backup_version: str
    backup_id: str
    created_at: str
    source_db: str
    backup_path: str
    size_bytes: int
    sha256: str
    integrity_check: Literal["ok", "failed"]
    table_count: int
    contains_broker_credentials: bool = False
    live_trading_blocked: bool = True


class DatabaseRestoreDrillReport(BaseModel):
    drill_version: str
    drill_id: str
    executed_at: str
    backup_id: str
    backup_sha256_matches: bool
    restore_path: str
    integrity_check: Literal["ok", "failed"]
    source_table_count: int
    restored_table_count: int
    row_count_checks: dict[str, dict[str, int]]
    passed: bool
    production_database_modified: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class DeploymentReadinessCheck(BaseModel):
    check_id: str
    name: str
    status: Literal["pass", "warn", "fail"]
    evidence: str
    blocks_deployment: bool


class DeploymentReadinessReport(BaseModel):
    readiness_version: str
    generated_at: str
    target: Literal["research_mock_stack"]
    configuration: DeploymentConfigurationFingerprint
    checks: list[DeploymentReadinessCheck]
    pass_count: int
    warn_count: int
    fail_count: int
    ready: bool
    live_broker_deployment_allowed: bool = False
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class DeploymentSmokeReport(BaseModel):
    smoke_version: str
    generated_at: str
    checks: list[DeploymentReadinessCheck]
    passed_count: int
    check_count: int
    all_passed: bool
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class StaticSafetyScanFinding(BaseModel):
    finding_id: str
    file_path: str
    line_number: int = Field(ge=1)
    pattern_id: str
    excerpt: str
    severity: Literal["critical", "warning"] = "critical"


class StaticSafetyScanReport(BaseModel):
    scan_version: str
    generated_at: str
    scanned_file_count: int
    scanned_roots: list[str]
    forbidden_pattern_count: int
    findings: list[StaticSafetyScanFinding]
    passed: bool
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class ReleaseArtifactEntry(BaseModel):
    artifact_id: str
    relative_path: str
    sha256: str
    size_bytes: int = Field(ge=0)
    required: bool
    present: bool


class ReleaseCandidateManifest(BaseModel):
    manifest_version: str
    release_id: str
    generated_at: str
    target: Literal["research_mock_stack"]
    artifact_count: int = Field(ge=0)
    artifacts: list[ReleaseArtifactEntry]
    manifest_sha256: str
    manifest_path: str | None = None
    immutable: bool = True
    contains_secrets: bool = False
    contains_broker_credentials: bool = False
    contains_live_orders: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class FinalReleaseGate(BaseModel):
    gate_id: str
    name: str
    status: Literal["pass", "warn", "fail"]
    evidence: str
    blocks_release: bool


class FinalProductionReadinessAudit(BaseModel):
    audit_version: str
    generated_at: str
    target: Literal["research_mock_stack"]
    release_scope: str
    gates: list[FinalReleaseGate]
    pass_count: int
    warn_count: int
    fail_count: int
    research_stack_ready: bool
    production_research_release_candidate: bool
    live_trading_ready: bool = False
    static_safety_scan: StaticSafetyScanReport
    release_manifest: ReleaseCandidateManifest
    deployment_readiness_version: str
    deployment_smoke_version: str
    transport_resilience_version: str
    transport_resilience_status: Literal["healthy", "low_evidence", "degraded", "critical"]
    capability_count: int
    required_capability_count: int
    required_capabilities_covered: bool
    operator_signoff_required: bool = True
    operator_signoff_present: bool = False
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class ReleaseReadinessEvidenceGate(BaseModel):
    gate_id: str
    name: str
    status: Literal["pass", "warn", "fail"]
    evidence: str
    blocks_evidence_ready: bool


class ReleaseReadinessEvidenceReport(BaseModel):
    evidence_version: str
    generated_at: str
    target: Literal["research_mock_stack"]
    evidence_state: Literal["research_release_evidence_ready", "blocked"]
    final_audit_version: str
    final_audit_ready: bool
    final_audit_fail_count: int = Field(ge=0)
    final_audit_warn_count: int = Field(ge=0)
    safety_scan_version: str
    safety_scan_passed: bool
    safety_scan_finding_count: int = Field(ge=0)
    manifest_version: str
    release_id: str
    manifest_sha256: str
    manifest_artifact_count: int = Field(ge=0)
    required_artifacts_missing: list[str]
    blocking_gate_ids: list[str]
    gates: list[ReleaseReadinessEvidenceGate]
    cache_policy: str
    final_audit_cache_ttl_seconds: float = Field(ge=0.0)
    evidence_sources: list[str]
    operator_message: str
    research_release_candidate: bool
    broker_credentials_present: bool = False
    broker_order_created: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    trade_allowed: bool = False
    can_execute_orders: bool = False
    can_export_to_openalgo: bool = False
    notes: list[str]


class TwinMachineDashboard(BaseModel):
    dashboard_version: str
    generated_at: str
    symbol: str
    comparison: TwinEngineComparison
    conflicts: list[TwinConflictRecord]
    reliability: TwinReliabilityReport
    tournament: TwinTournamentResult
    openalgo_intent_preview: SignalIntentBundle
    forecast_path_points: list[dict[str, float | int]]
    forecast_fan: dict[str, list[float]]
    ghost_path_summary: dict[str, float | str | bool]
    safety_gate_matrix: list[dict[str, str | bool]]
    reliability_leaderboard: list[dict[str, float | str]]
    conflict_explorer: list[dict[str, str]]
    recommended_workspace_action: Literal["NO_TRADE", "WAIT", "REPLAY_REVIEW_ONLY", "RESEARCH_COMPARE_ONLY"]
    dashboard_hash: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    notes: list[str]


class MatrixDecisionReadinessRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    scenario_id: str = Field(default="mock_opening_drive", min_length=1, max_length=80)
    seed: int = Field(default=42, ge=0)
    event_count: int = Field(default=24, ge=8, le=240)
    timeframe: TimeframeValue = "1m"
    required_matrix_rows: int = Field(default=32, ge=16, le=32)
    min_agreement_score: float = Field(default=0.55, ge=0.0, le=1.0)
    max_safety_pressure: float = Field(default=0.62, ge=0.0, le=1.0)


class MatrixDecisionGate(BaseModel):
    gate_id: str
    name: str
    status: Literal["pass", "warn", "fail"]
    score: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    evidence: str
    blocks_decision: bool
    remediation: str | None = None


class MatrixDecisionReadinessReport(BaseModel):
    readiness_version: str
    generated_at: str
    run_id: str
    base_matrix_version: str
    symbol: str
    scenario_id: str
    seed: int
    event_count: int
    timeframe: TimeframeValue
    matrix_indicator_count: int
    ready_rows: int
    proxy_rows: int
    blocked_rows: int
    bullish_rows: int
    bearish_rows: int
    watch_rows: int
    neutral_rows: int
    directional_bias: Literal["LONG", "SHORT", "NEUTRAL"]
    readiness_action: Literal["REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE", "WAIT", "NO_TRADE", "BLOCK"]
    simulated_decision_allowed: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    confidence_score: float = Field(ge=0.0, le=1.0)
    agreement_score: float = Field(ge=0.0, le=1.0)
    safety_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    blocker_reasons: list[str]
    gate_summary: dict[str, int]
    used_row_ids: list[str]
    matrix_output_hash: str
    input_event_chain_hash: str
    output_hash: str
    deterministic: bool
    no_future_leakage: bool
    narrative_read_only: bool = True
    live_trading_blocked: bool = True
    gates: list[MatrixDecisionGate]
    reason: str
    notes: list[str]


class TradeLifecycleSimulationRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    scenario_id: str = Field(default="mock_opening_drive", min_length=1, max_length=80)
    seed: int = Field(default=42, ge=0)
    event_count: int = Field(default=24, ge=8, le=240)
    timeframe: TimeframeValue = "1m"
    required_matrix_rows: int = Field(default=32, ge=16, le=32)
    min_agreement_score: float = Field(default=0.55, ge=0.0, le=1.0)
    max_safety_pressure: float = Field(default=0.62, ge=0.0, le=1.0)
    entry_after_bars: int = Field(default=5, ge=1, le=60)
    shadow_quantity: int = Field(default=25, ge=1, le=100_000)
    max_holding_bars: int = Field(default=18, ge=1, le=240)
    respect_readiness_block: bool = True


class TradeLifecycleSimulationReport(BaseModel):
    lifecycle_version: str
    generated_at: str
    run_id: str
    symbol: str
    scenario_id: str
    seed: int
    event_count: int
    timeframe: TimeframeValue
    base_readiness_version: str
    base_chart_version: str
    readiness_action: Literal["REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE", "WAIT", "NO_TRADE", "BLOCK"]
    lifecycle_status: Literal["BLOCKED_BY_READINESS", "SHADOW_SIMULATED", "SHADOW_NO_FILL", "SHADOW_REJECTED"]
    directional_bias: Literal["LONG", "SHORT", "NEUTRAL"]
    entry_type: Literal["NEXT_5M_OPEN_SHADOW"]
    entry_sequence_number: int
    entry_timestamp_ns: int
    entry_price: float
    stop_loss: float
    target: float
    risk_reward: float
    atr_proxy: float
    trade_state_path: list[str]
    readiness: MatrixDecisionReadinessReport
    execution: ExecutionSimulationResult
    outcome: OutcomeLabelResult
    expected_MFE: float
    expected_MAE: float
    bars_to_target: int | None
    bars_to_sl: int | None
    blocker_reasons: list[str]
    lifecycle_gate_summary: dict[str, int]
    gates: list[MatrixDecisionGate]
    input_event_chain_hash: str
    readiness_output_hash: str
    outcome_run_id: str
    execution_simulation_id: str
    output_hash: str
    deterministic: bool
    no_future_leakage: bool
    simulation_only: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    narrative_read_only: bool = True
    reason: str
    notes: list[str]


class TradeLifecycleScenarioConfig(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    scenario_id: str = Field(min_length=1, max_length=80)
    seed: int = Field(ge=0)
    min_agreement_score: float | None = Field(default=None, ge=0.0, le=1.0)
    max_safety_pressure: float | None = Field(default=None, ge=0.0, le=1.0)
    entry_after_bars: int | None = Field(default=None, ge=1, le=60)
    shadow_quantity: int | None = Field(default=None, ge=1, le=100_000)
    respect_readiness_block: bool | None = None


def default_lifecycle_scenarios() -> list[TradeLifecycleScenarioConfig]:
    return [
        TradeLifecycleScenarioConfig(label="Default blocked opening drive", scenario_id="mock_opening_drive", seed=42),
        TradeLifecycleScenarioConfig(label="Candidate pressure probe", scenario_id="mock_opening_drive", seed=123, max_safety_pressure=0.70),
        TradeLifecycleScenarioConfig(label="Noisy fakeout probe", scenario_id="mock_fakeout_pressure", seed=7),
        TradeLifecycleScenarioConfig(label="Liquidity stress probe", scenario_id="mock_liquidity_stress", seed=99, max_safety_pressure=0.55),
    ]


class TradeLifecycleScenarioComparisonRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "1m"
    event_count: int = Field(default=24, ge=8, le=240)
    required_matrix_rows: int = Field(default=32, ge=16, le=32)
    min_agreement_score: float = Field(default=0.55, ge=0.0, le=1.0)
    max_safety_pressure: float = Field(default=0.62, ge=0.0, le=1.0)
    entry_after_bars: int = Field(default=5, ge=1, le=60)
    shadow_quantity: int = Field(default=25, ge=1, le=100_000)
    max_holding_bars: int = Field(default=18, ge=1, le=240)
    respect_readiness_block: bool = True
    scenarios: list[TradeLifecycleScenarioConfig] = Field(default_factory=default_lifecycle_scenarios, min_length=2, max_length=12)


class TradeLifecycleScenarioComparisonItem(BaseModel):
    label: str
    scenario_id: str
    seed: int
    readiness_action: Literal["REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE", "WAIT", "NO_TRADE", "BLOCK"]
    lifecycle_status: Literal["BLOCKED_BY_READINESS", "SHADOW_SIMULATED", "SHADOW_NO_FILL", "SHADOW_REJECTED"]
    directional_bias: Literal["LONG", "SHORT", "NEUTRAL"]
    outcome_label: OutcomeLabelValue
    fill_status: BehaviorExecutionStatus
    fill_quality: Literal["excellent", "acceptable", "poor", "rejected", "no_fill"]
    entry_price: float
    stop_loss: float
    target: float
    risk_reward: float
    expected_MFE: float
    expected_MAE: float
    bars_to_target: int | None
    bars_to_sl: int | None
    blocker_count: int
    trade_state_path: list[str]
    output_hash: str
    trade_allowed: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True


class TradeLifecycleScenarioComparisonReport(BaseModel):
    comparison_version: str
    generated_at: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    event_count: int
    scenario_count: int
    candidate_count: int
    blocked_count: int
    no_fill_count: int
    rejected_count: int
    target_hit_count: int
    stop_hit_count: int
    average_MFE: float
    average_MAE: float
    best_scenario_label: str | None
    worst_scenario_label: str | None
    items: list[TradeLifecycleScenarioComparisonItem]
    all_trade_allowed_false: bool
    all_order_routing_disabled: bool
    all_live_trading_blocked: bool
    all_simulation_only: bool
    deterministic: bool
    no_future_leakage: bool
    output_hash: str
    gates: list[MatrixDecisionGate]
    notes: list[str]


class LifecycleEvidenceDrilldownRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "1m"
    event_count: int = Field(default=24, ge=8, le=240)
    required_matrix_rows: int = Field(default=32, ge=16, le=32)
    min_agreement_score: float = Field(default=0.55, ge=0.0, le=1.0)
    max_safety_pressure: float = Field(default=0.62, ge=0.0, le=1.0)
    entry_after_bars: int = Field(default=5, ge=1, le=60)
    shadow_quantity: int = Field(default=25, ge=1, le=100_000)
    max_holding_bars: int = Field(default=18, ge=1, le=240)
    respect_readiness_block: bool = True
    top_n_rows: int = Field(default=4, ge=1, le=8)
    scenarios: list[TradeLifecycleScenarioConfig] = Field(default_factory=default_lifecycle_scenarios, min_length=2, max_length=12)


class LifecycleEvidenceRowContribution(BaseModel):
    row_id: str
    family: str
    layer_index: int | None = None
    contract_name: str
    source: Literal["replay_candle", "derived_overlay", "behavior_proxy", "safety_proxy"]
    signal: Literal["bullish", "bearish", "neutral", "watch", "blocked"]
    readiness_status: Literal["ready", "proxy", "blocked"]
    normalized_score: float = Field(ge=-1.0, le=1.0)
    contribution_kind: Literal["directional_positive", "directional_negative", "safety_pressure"]
    contribution_score: float = Field(ge=0.0, le=1.0)
    latest_value: float | str | bool | None
    output_fields: dict[str, float | str | bool | None]
    explanation: str


class LifecycleEvidenceScenarioDrilldown(BaseModel):
    label: str
    scenario_id: str
    seed: int
    readiness_action: Literal["REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE", "WAIT", "NO_TRADE", "BLOCK"]
    lifecycle_status: Literal["BLOCKED_BY_READINESS", "SHADOW_SIMULATED", "SHADOW_NO_FILL", "SHADOW_REJECTED"]
    directional_bias: Literal["LONG", "SHORT", "NEUTRAL"]
    outcome_label: OutcomeLabelValue
    fill_status: BehaviorExecutionStatus
    fill_quality: Literal["excellent", "acceptable", "poor", "rejected", "no_fill"]
    agreement_score: float = Field(ge=0.0, le=1.0)
    safety_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    top_directional_drivers: list[LifecycleEvidenceRowContribution]
    top_counter_drivers: list[LifecycleEvidenceRowContribution]
    top_safety_pressures: list[LifecycleEvidenceRowContribution]
    blocker_reasons: list[str]
    reason: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True
    output_hash: str


class LifecycleEvidenceDrilldownReport(BaseModel):
    evidence_version: str
    generated_at: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    event_count: int
    scenario_count: int
    candidate_count: int
    blocked_count: int
    base_comparison_version: str
    comparison_output_hash: str
    dominant_directional_driver: str | None
    dominant_safety_pressure: str | None
    items: list[LifecycleEvidenceScenarioDrilldown]
    all_trade_allowed_false: bool
    all_order_routing_disabled: bool
    all_live_trading_blocked: bool
    deterministic: bool
    no_future_leakage: bool
    narrative_read_only: bool = True
    output_hash: str
    gates: list[MatrixDecisionGate]
    notes: list[str]


class TradeabilityGuidanceRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "1m"
    event_count: int = Field(default=24, ge=8, le=240)
    required_matrix_rows: int = Field(default=32, ge=16, le=32)
    min_agreement_score: float = Field(default=0.55, ge=0.0, le=1.0)
    max_safety_pressure: float = Field(default=0.62, ge=0.0, le=1.0)
    entry_after_bars: int = Field(default=5, ge=1, le=60)
    shadow_quantity: int = Field(default=25, ge=1, le=100_000)
    max_holding_bars: int = Field(default=18, ge=1, le=240)
    respect_readiness_block: bool = True
    top_n_rows: int = Field(default=4, ge=1, le=8)
    guidance_threshold: float = Field(default=0.58, ge=0.0, le=1.0)
    scenarios: list[TradeLifecycleScenarioConfig] = Field(default_factory=default_lifecycle_scenarios, min_length=2, max_length=12)


class TradeabilityImprovementStep(BaseModel):
    step_id: str
    category: Literal[
        "directional_confirmation",
        "safety_pressure",
        "execution_quality",
        "risk_control",
        "evidence_quality",
        "permission_lock",
    ]
    source_row_id: str | None = None
    priority: Literal["critical", "high", "medium", "low"]
    current_value: float | None = None
    target_value: float | None = None
    action: str
    rationale: str
    blocks_promotion: bool


class ScenarioTradeabilityGuidance(BaseModel):
    label: str
    scenario_id: str
    seed: int
    readiness_action: Literal["REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE", "WAIT", "NO_TRADE", "BLOCK"]
    lifecycle_status: Literal["BLOCKED_BY_READINESS", "SHADOW_SIMULATED", "SHADOW_NO_FILL", "SHADOW_REJECTED"]
    directional_bias: Literal["LONG", "SHORT", "NEUTRAL"]
    tradeability_status: Literal["BLOCKED", "AVOID", "RESEARCH_WATCH", "REPLAY_CANDIDATE_RESEARCH_ONLY"]
    next_safe_action: Literal[
        "NO_TRADE",
        "WAIT_FOR_RETEST",
        "IMPROVE_LIQUIDITY",
        "REPLAY_REVIEW_ONLY",
        "AVOID_FAKEOUT",
        "COLLECT_MORE_EVIDENCE",
    ]
    tradeability_score: float = Field(ge=0.0, le=1.0)
    best_driver_row_id: str | None
    worst_safety_row_id: str | None
    agreement_score: float = Field(ge=0.0, le=1.0)
    safety_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    promotion_blockers: list[str]
    improvement_steps: list[TradeabilityImprovementStep]
    reason: str
    must_remain_simulation_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    no_future_leakage: bool = True
    output_hash: str


class TradeabilityGuidanceReport(BaseModel):
    guidance_version: str
    generated_at: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    event_count: int
    scenario_count: int
    blocked_count: int
    avoid_count: int
    research_watch_count: int
    replay_candidate_research_only_count: int
    base_evidence_version: str
    evidence_output_hash: str
    safest_scenario_label: str | None
    riskiest_scenario_label: str | None
    top_global_blocker: str | None
    items: list[ScenarioTradeabilityGuidance]
    all_trade_allowed_false: bool
    all_order_routing_disabled: bool
    all_live_trading_blocked: bool
    deterministic: bool
    no_future_leakage: bool
    narrative_read_only: bool = True
    promotion_allowed: bool = False
    output_hash: str
    gates: list[MatrixDecisionGate]
    notes: list[str]


CombinationSimilarityGroup = Literal[
    "candle_structure",
    "independent_indicator",
    "trend_momentum",
    "level_context",
    "session",
    "volatility_volume",
    "regime_market",
]


class CombinationSimilarityRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=65, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    decision_time_ns: int | None = Field(default=None, ge=0)
    session_phase: str = Field(default="09:30-10:15", min_length=1, max_length=40)
    market_regime: str = Field(default="trend_continuation", min_length=1, max_length=80)
    gap_class: str = Field(default="gap_up_hold", min_length=1, max_length=80)
    minimum_match_count: int = Field(default=30, ge=1, le=100)
    max_matches: int = Field(default=30, ge=1, le=100)
    minimum_separation_bars: int = Field(default=20, ge=1, le=390)
    top_k_initial: int = Field(default=500, ge=50, le=2000)
    top_k_refined: int = Field(default=100, ge=20, le=500)
    allow_relaxed_filters: bool = False


class SequentialSignalStep(BaseModel):
    indicator_id: str
    family: str
    state: str
    candle_offset: int
    value: float | None = None
    threshold: float | None = None
    timestamp_ns: int


class SequentialSignalPattern(BaseModel):
    sequence_id: str
    sequence_hash: str
    ordered_indicators: list[str]
    ordered_states: list[str]
    candle_offsets: list[int]
    max_candle_span: int
    completion_time_ns: int
    expiry_time_ns: int
    same_candle_required: bool = False
    historical_occurrence_count: int
    minimum_sample_pass: bool
    steps: list[SequentialSignalStep]
    point_in_time_safe: bool


class CombinationFeatureContribution(BaseModel):
    group: CombinationSimilarityGroup
    weight: float = Field(ge=0.0, le=1.0)
    similarity_score: float = Field(ge=0.0, le=1.0)
    weighted_score: float = Field(ge=0.0, le=1.0)
    matched_features: list[str]
    explanation: str


class CombinationAnalogMatch(BaseModel):
    analog_id: str
    symbol: str
    timeframe: TimeframeValue
    historical_date: str
    candidate_timestamp_ns: int
    bars_before_decision: int = Field(ge=0)
    session_phase: str
    market_regime: str
    gap_class: str
    total_similarity_pct: float = Field(ge=0.0, le=100.0)
    candle_structure_similarity_pct: float = Field(ge=0.0, le=100.0)
    independent_indicator_similarity_pct: float = Field(ge=0.0, le=100.0)
    trend_momentum_similarity_pct: float = Field(ge=0.0, le=100.0)
    level_context_similarity_pct: float = Field(ge=0.0, le=100.0)
    session_similarity_pct: float = Field(ge=0.0, le=100.0)
    volatility_volume_similarity_pct: float = Field(ge=0.0, le=100.0)
    regime_market_similarity_pct: float = Field(ge=0.0, le=100.0)
    outcome_label: ConservativeOutcomeLabelValue
    target_first: bool
    stop_first: bool
    time_exit: bool
    non_overlap_group_id: str
    distance_metric: Literal["mixed_gower_dtw_jaccard", "mock_mixed_distance"]
    feature_contributions: list[CombinationFeatureContribution]
    sequential_pattern: SequentialSignalPattern
    explanation: str


class CombinationSimilarityGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class CombinationSimilarityReport(BaseModel):
    combination_similarity_version: str
    generated_at: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    source_snapshot_hash: str
    decision_time_ns: int
    hard_context_filters: list[str]
    hard_context_candidate_count: int = Field(ge=0)
    ann_prefilter_method: Literal["deterministic_local_prefilter", "faiss_reserved", "hnsw_reserved"]
    ann_prefilter_candidate_count: int = Field(ge=0)
    exact_refinement_candidate_count: int = Field(ge=0)
    non_overlap_match_count: int = Field(ge=0)
    minimum_match_count: int = Field(ge=1)
    minimum_sample_pass: bool
    evidence_quality: Literal["LOW", "MEDIUM", "STRONG", "LOW_EVIDENCE_RELAXED_FILTERS"]
    weight_config: dict[CombinationSimilarityGroup, float]
    weight_config_version: str
    calibration_status: Literal["uncalibrated_mock", "walk_forward_pending", "walk_forward_passed", "blocked_variance"]
    similarity_methods: list[str]
    matches: list[CombinationAnalogMatch]
    sequential_signal_pattern: SequentialSignalPattern
    continuation_probability_pct: float = Field(ge=0.0, le=100.0)
    reversal_probability_pct: float = Field(ge=0.0, le=100.0)
    fakeout_probability_pct: float = Field(ge=0.0, le=100.0)
    range_probability_pct: float = Field(ge=0.0, le=100.0)
    no_trade_reason: str | None
    deterministic: bool
    point_in_time_safe: bool
    non_overlap_enforced: bool
    hubness_checked: bool
    false_nearest_neighbor_guarded: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    output_hash: str
    gates: list[CombinationSimilarityGate]
    notes: list[str]


class AnalogResearchRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=73, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    decision_time_ns: int | None = Field(default=None, ge=0)
    session_phase: str = Field(default="09:30-10:15", min_length=1, max_length=40)
    market_regime: str = Field(default="trend_continuation", min_length=1, max_length=80)
    gap_class: str = Field(default="gap_up_hold", min_length=1, max_length=80)
    minimum_match_count: int = Field(default=30, ge=1, le=100)
    max_matches: int = Field(default=20, ge=1, le=100)
    max_rule_depth: int = Field(default=3, ge=1, le=5)
    false_discovery_rate_q: float = Field(default=0.10, ge=0.01, le=0.25)
    allow_relaxed_filters: bool = False


class ValueBandDiscoveryRecord(BaseModel):
    feature_id: str
    candidate_band: str
    sample_count: int = Field(ge=0)
    independent_sample_count: int = Field(ge=0)
    outcome_distribution: dict[str, float]
    confidence_interval: tuple[float, float]
    fdr_adjusted_p_value: float = Field(ge=0.0, le=1.0)
    multiple_testing_correction: Literal["benjamini_hochberg"]
    stable_across_folds: bool
    holdout_confirmed: bool
    generalizes: bool
    notes: list[str]


class ConditionalRuleRecord(BaseModel):
    rule_id: str
    conditions: list[str]
    rule_depth: int = Field(ge=1)
    incremental_evidence_count: int = Field(ge=0)
    baseline_win_rate_pct: float = Field(ge=0.0, le=100.0)
    conditional_win_rate_pct: float = Field(ge=0.0, le=100.0)
    incremental_lift_pct: float
    confidence_interval: tuple[float, float]
    fdr_adjusted_p_value: float = Field(ge=0.0, le=1.0)
    cross_validation_passed: bool
    stability_across_folds: bool
    recent_vs_old_delta_pct: float
    regime_stratified: bool
    holdout_confirmed: bool
    generalization_status: Literal["generalizing", "unstable_non_generalizing", "low_evidence"]
    confidence_increase_allowed: bool


class AnalogMatchExplanation(BaseModel):
    analog_id: str
    matched_date: str
    matched_timestamp_ns: int
    symbol: str
    timeframe: TimeframeValue
    distance_metric: str
    matched_features: list[str]
    mismatched_features: list[str]
    matched_values: dict[str, float | str]
    matched_patterns: list[str]
    matched_timeframes: list[str]
    matched_levels: list[str]
    matched_contexts: list[str]
    outcome_label: ConservativeOutcomeLabelValue
    result_path_summary: str
    data_split: Literal["training", "validation", "holdout"]
    candidate_timestamp_precedes_decision: bool
    non_overlap_group_id: str
    warnings: list[str]


class FalseDiscoveryControlReport(BaseModel):
    method: Literal["benjamini_hochberg"]
    tested_hypothesis_count: int = Field(ge=0)
    accepted_hypothesis_count: int = Field(ge=0)
    q_value_threshold: float = Field(ge=0.0, le=1.0)
    all_accepted_have_adjusted_p_value: bool
    notes: list[str]


class AnalogResearchGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class AnalogConditionalResearchReport(BaseModel):
    research_version: str
    generated_at: str
    symbol: str
    timeframe: TimeframeValue
    base_combination: CombinationSimilarityReport
    value_bands: list[ValueBandDiscoveryRecord]
    conditional_rules: list[ConditionalRuleRecord]
    match_explanations: list[AnalogMatchExplanation]
    false_discovery_control: FalseDiscoveryControlReport
    mixed_distance_method: str
    ann_prefilter_ran_before_exact_refinement: bool
    non_overlap_enforced: bool
    all_displayed_analogs_precede_decision: bool
    empty_evidence_returns_low_evidence: bool
    relaxed_filters_visibly_uncalibrated: bool
    incremental_evidence_required_for_confidence: bool
    walk_forward_holdout_passed: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[AnalogResearchGate]
    notes: list[str]


class EventSequenceMiningRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=74, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    decision_time_ns: int | None = Field(default=None, ge=0)
    max_lookback_candles: int = Field(default=5, ge=1, le=30)
    min_sequence_support: int = Field(default=30, ge=1, le=200)
    max_sequences: int = Field(default=8, ge=1, le=30)


class IndicatorEventRecord(BaseModel):
    event_id: str
    indicator_id: str
    output_name: str
    family: str
    state: str
    signal: Literal["buy", "sell", "watch", "neutral", "blocked", "unavailable"]
    nominal_direction: Literal["bullish", "bearish", "neutral", "unavailable"]
    candle_offset: int
    lag_from_previous_candles: int = Field(ge=0)
    same_candle_group: str | None = None
    timestamp_ns: int
    value: float | str | bool | None
    source_observation_id: str
    point_in_time_safe: bool


class EventSequencePatternRecord(BaseModel):
    sequence_id: str
    sequence_hash: str
    ordered_indicators: list[str]
    ordered_states: list[str]
    candle_offsets: list[int]
    events: list[IndicatorEventRecord]
    max_candle_span: int = Field(ge=0)
    same_candle_event_count: int = Field(ge=0)
    non_same_candle_event_count: int = Field(ge=0)
    lag_window_bars: int = Field(ge=0)
    historical_occurrence_count: int = Field(ge=0)
    independent_occurrence_count: int = Field(ge=0)
    outcome_distribution: dict[str, float]
    continuation_probability_pct: float = Field(ge=0.0, le=100.0)
    reversal_probability_pct: float = Field(ge=0.0, le=100.0)
    range_probability_pct: float = Field(ge=0.0, le=100.0)
    fakeout_probability_pct: float = Field(ge=0.0, le=100.0)
    reciprocal_signal_warning: bool
    false_agreement_warning: bool
    confidence_interval: tuple[float, float]
    minimum_sample_pass: bool
    point_in_time_safe: bool
    expired_sequences_reset_to_neutral: bool
    explanation: str


class ReciprocalSignalRecord(BaseModel):
    indicator_id: str
    nominal_direction: Literal["bullish", "bearish"]
    observed_outcome_direction: Literal["bullish", "bearish", "range"]
    symbol: str
    timeframe: TimeframeValue
    session_phase: str
    sample_count: int = Field(ge=0)
    reciprocal_rate_pct: float = Field(ge=0.0, le=100.0)
    confidence_interval: tuple[float, float]
    uses_only_pre_outcome_data: bool
    warning: str


class PriorToCurrentInfluenceRecord(BaseModel):
    influence_id: str
    prior_candle_window: int = Field(ge=1)
    prior_body_ratio_sequence: list[float]
    prior_wick_ratio_sequence: list[float]
    prior_no_wick_sequence: list[bool]
    prior_close_location_sequence: list[float]
    prior_indicator_value_sequence: list[str]
    prior_indicator_signal_sequence: list[str]
    prior_pattern_state_sequence: list[str]
    prior_level_interaction_sequence: list[str]
    current_candle_response: Literal["expansion_up", "expansion_down", "reversal", "range_bound", "fakeout", "no_response"]
    current_candle_response_strength: float = Field(ge=0.0, le=1.0)
    influence_hypothesis: str
    historical_case_count: int = Field(ge=0)
    continuation_probability_pct: float = Field(ge=0.0, le=100.0)
    reversal_probability_pct: float = Field(ge=0.0, le=100.0)
    range_probability_pct: float = Field(ge=0.0, le=100.0)
    supporting_case_ids: list[str]
    counterexample_case_ids: list[str]


class EventSequenceMiningGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class EventSequenceMiningReport(BaseModel):
    sequence_mining_version: str
    generated_at: str
    symbol: str
    exchange: str
    timeframe: TimeframeValue
    decision_time_ns: int
    max_lookback_candles: int
    event_count: int
    same_candle_sequence_count: int
    non_same_candle_sequence_count: int
    sequence_patterns: list[EventSequencePatternRecord]
    reciprocal_signal_records: list[ReciprocalSignalRecord]
    prior_to_current_influence: list[PriorToCurrentInfluenceRecord]
    value_confluence_does_not_require_same_candle_signals: bool
    same_indicators_different_order_are_different_sequences: bool
    signals_after_outcome_excluded: bool
    reciprocal_signal_detector_uses_only_pre_outcome_data: bool
    prior_candle_sequences_compared_to_current_response: bool
    all_sequences_point_in_time_safe: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[EventSequenceMiningGate]
    notes: list[str]


class FalseAgreementConfluenceRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=75, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    max_lookback_candles: int = Field(default=5, ge=1, le=30)
    minimum_independent_evidence: int = Field(default=30, ge=1, le=200)
    redundancy_threshold: float = Field(default=0.85, ge=0.50, le=0.99)


class ConfluenceTimingWindowRecord(BaseModel):
    window_id: str
    window_start_offset: int
    window_end_offset: int
    event_ids: list[str]
    indicator_ids: list[str]
    families: list[str]
    same_candle_only: bool
    delayed_signal_count: int = Field(ge=0)
    independent_family_count: int = Field(ge=0)
    nominal_agreement_direction: Literal["bullish", "bearish", "mixed", "neutral"]
    value_cluster_summary: dict[str, str | float]
    point_in_time_safe: bool


class IndicatorValueConfluenceRecord(BaseModel):
    confluence_id: str
    timing_window_id: str
    feature_values: dict[str, float | str | bool]
    matched_value_bands: list[str]
    redundant_feature_ids: list[str]
    independent_feature_ids: list[str]
    nominal_agreement_score: float = Field(ge=0.0, le=1.0)
    independent_evidence_score: float = Field(ge=0.0, le=1.0)
    redundancy_penalty: float = Field(ge=0.0, le=1.0)
    calibrated_confluence_score: float = Field(ge=0.0, le=1.0)
    confidence_boost_allowed: bool
    confidence_block_reason: str | None = None


class FalseAgreementRecord(BaseModel):
    false_agreement_id: str
    agreement_family_count: int = Field(ge=0)
    nominal_direction: Literal["bullish", "bearish", "mixed"]
    historical_failure_rate_pct: float = Field(ge=0.0, le=100.0)
    independent_evidence_count: int = Field(ge=0)
    redundant_evidence_count: int = Field(ge=0)
    misleading_indicator_ids: list[str]
    failure_modes: list[str]
    confidence_must_be_blocked: bool
    reason: str
    uses_independent_historical_evidence: bool


class FalseAgreementConfluenceGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class FalseAgreementConfluenceReport(BaseModel):
    diagnostic_version: str
    generated_at: str
    symbol: str
    exchange: str
    timeframe: TimeframeValue
    source_sequence_version: str
    source_redundancy_version: str
    confluence_timing_windows: list[ConfluenceTimingWindowRecord]
    indicator_value_confluence_records: list[IndicatorValueConfluenceRecord]
    false_agreement_records: list[FalseAgreementRecord]
    nominal_agreement_count: int = Field(ge=0)
    independent_agreement_count: int = Field(ge=0)
    redundant_agreement_count: int = Field(ge=0)
    false_agreement_warning: bool
    confidence_blocked: bool
    confidence_block_reasons: list[str]
    value_confluence_supports_non_same_candle_signals: bool
    false_agreement_detector_uses_independent_historical_evidence: bool
    redundant_agreement_cannot_increase_confidence: bool
    all_confluence_point_in_time_safe: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[FalseAgreementConfluenceGate]
    notes: list[str]


class DesignSimilarityRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=76, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    design_window_bars: int = Field(default=48, ge=12, le=240)
    minimum_match_count: int = Field(default=30, ge=1, le=200)
    include_overlay_evidence: bool = True


DesignGrammarLabel = Literal[
    "uptrend_channel",
    "downtrend_channel",
    "range_box",
    "u_reversal",
    "w_range_reversal",
    "v_reversal",
    "open_drive_pullback",
    "open_drive_fade",
    "coil_compression",
    "lunch_chop",
    "closing_drive",
]


class ShapeGrammarComponent(BaseModel):
    component_id: str
    label: DesignGrammarLabel
    normalized_points: list[tuple[float, float]]
    slope_signature: list[float]
    swing_sequence: list[str]
    wick_body_rhythm: list[str]
    volume_rhythm: list[str]
    grammar_confidence_pct: float = Field(ge=0.0, le=100.0)
    forming_or_confirmed: Literal["forming", "confirmed", "failed", "developing_not_decision_safe"]
    point_in_time_safe: bool


class GeometryReferenceRecord(BaseModel):
    reference_id: str
    reference_type: Literal["harmonic", "fibonacci", "curve", "trendline", "elliott", "support_resistance"]
    label: str
    anchor_times: list[int]
    anchor_prices_normalized: list[float]
    ratio_labels: list[str]
    distance_to_completion_zone_atr: float
    respect_score: float = Field(ge=0.0, le=1.0)
    contradiction: str | None = None
    confirmation_state: Literal["forming", "confirmed", "failed", "developing_not_decision_safe"]
    reproducible_from_anchors: bool


class DesignSimilarityCandidate(BaseModel):
    candidate_id: str
    historical_date: str
    grammar_label: DesignGrammarLabel
    shape_dtw_score: float = Field(ge=0.0, le=1.0)
    swing_grammar_score: float = Field(ge=0.0, le=1.0)
    candle_rhythm_score: float = Field(ge=0.0, le=1.0)
    level_geometry_score: float = Field(ge=0.0, le=1.0)
    volume_participation_score: float = Field(ge=0.0, le=1.0)
    design_similarity_score_pct: float = Field(ge=0.0, le=100.0)
    outcome_label: ConservativeOutcomeLabelValue
    result_path_summary: str
    counterexample: bool
    matched_components: list[str]
    mismatched_components: list[str]


class ChartOverlayEvidenceRecord(BaseModel):
    overlay_id: str
    overlay_type: Literal["shape_path", "trendline", "harmonic_anchor", "fib_zone", "range_box", "analog_ghost_path"]
    label: str
    points: list[tuple[float, float]]
    color_hint: str
    pane: Literal["price", "volume", "indicator"]
    visible_by_default: bool
    tooltip: str


class DesignSimilarityGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class DesignSimilarityReport(BaseModel):
    design_version: str
    generated_at: str
    symbol: str
    exchange: str
    timeframe: TimeframeValue
    design_window_bars: int
    shape_normalization_method: Literal["log_return_zscore_time_resampled"]
    price_level_invariant: bool
    shifted_price_similarity_delta_pct: float = Field(ge=0.0)
    grammar_components: list[ShapeGrammarComponent]
    geometry_references: list[GeometryReferenceRecord]
    similarity_candidates: list[DesignSimilarityCandidate]
    overlay_evidence: list[ChartOverlayEvidenceRecord]
    dominant_design: DesignGrammarLabel
    counterexample_count: int = Field(ge=0)
    continuation_probability_pct: float = Field(ge=0.0, le=100.0)
    reversal_probability_pct: float = Field(ge=0.0, le=100.0)
    range_probability_pct: float = Field(ge=0.0, le=100.0)
    harmonic_and_trendline_may_contradict: bool
    forming_harmonic_not_labeled_confirmed: bool
    chart_evidence_ready: bool
    all_geometry_reproducible: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[DesignSimilarityGate]
    notes: list[str]


class BandLevelDistanceRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=77, ge=0)
    source_bars: int = Field(default=1950, ge=390, le=3900)
    decision_price: float = Field(default=2500.0, gt=0.0)
    atr: float = Field(default=18.0, gt=0.0)
    include_unavailable_levels: bool = True
    minimum_cluster_sample_count: int = Field(default=30, ge=1, le=200)


class LevelDistanceRecord(BaseModel):
    field_name: str
    level_name: str
    level_family: Literal["vwap", "bollinger", "keltner", "pivot", "daily_level", "cpr", "orb", "vpd_value_area", "fibonacci", "harmonic", "trendline"]
    level_value: float | None
    distance_points: float | None
    distance_pct: float | None
    distance_atr: float | None
    side: Literal["above", "below", "at_level", "unavailable"]
    proximity_bucket: Literal["touching", "near", "moderate", "far", "unavailable"]
    availability: Literal["available", "unavailable", "not_confirmed", "insufficient_history"]
    unavailable_reason: str | None = None
    point_in_time_safe: bool


class RepeatedValueClusterRecord(BaseModel):
    cluster_id: str
    cluster_signature: str
    matched_fields: list[str]
    candidate_band: str
    sample_count: int = Field(ge=0)
    independent_sample_count: int = Field(ge=0)
    confidence_interval: tuple[float, float]
    outcome_distribution: dict[str, float]
    continuation_probability_pct: float = Field(ge=0.0, le=100.0)
    reversal_probability_pct: float = Field(ge=0.0, le=100.0)
    range_probability_pct: float = Field(ge=0.0, le=100.0)
    fakeout_probability_pct: float = Field(ge=0.0, le=100.0)
    minimum_sample_pass: bool
    evidence_quality: Literal["LOW_EVIDENCE", "MEDIUM", "STRONG"]


class LevelDistanceOutcomeInfluence(BaseModel):
    influence_id: str
    field_name: str
    current_bucket: str
    historical_case_count: int = Field(ge=0)
    continuation_delta_pct: float
    reversal_delta_pct: float
    range_delta_pct: float
    fakeout_delta_pct: float
    interpretation: str
    blocks_confidence: bool


class MissingLevelRecord(BaseModel):
    level_name: str
    required_for_family: str
    availability: Literal["unavailable", "not_confirmed", "insufficient_history"]
    reason: str
    fallback_behavior: Literal["exclude_from_similarity", "reduce_coverage", "block_trade_quality"]


class BandLevelDistanceGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class BandLevelDistanceReport(BaseModel):
    distance_version: str
    generated_at: str
    symbol: str
    exchange: str
    timeframe: TimeframeValue
    decision_price: float
    atr: float
    required_distance_fields: list[str]
    distance_records: list[LevelDistanceRecord]
    repeated_value_clusters: list[RepeatedValueClusterRecord]
    outcome_influences: list[LevelDistanceOutcomeInfluence]
    missing_levels: list[MissingLevelRecord]
    all_required_distance_fields_present: bool
    unavailable_levels_not_silently_drawn: bool
    mixed_feature_similarity_handles_unavailable_values: bool
    level_distance_influences_outcomes: bool
    minimum_cluster_sample_pass: bool
    all_available_levels_point_in_time_safe: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[BandLevelDistanceGate]
    notes: list[str]


class PatternByTimeframeRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    primary_timeframe: TimeframeValue = "5m"
    seed: int = Field(default=78, ge=0)
    source_bars: int = Field(default=2520, ge=390, le=10000)
    minimum_sample_size: int = Field(default=30, ge=1, le=300)
    include_higher_timeframe_interactions: bool = True


class TimeframePatternOutcomeRecord(BaseModel):
    timeframe: TimeframeValue
    pattern_id: str
    pattern_family: str
    pattern_label: str
    sample_count: int = Field(ge=0)
    independent_sample_count: int = Field(ge=0)
    win_rate_pct: float = Field(ge=0.0, le=100.0)
    continuation_probability_pct: float = Field(ge=0.0, le=100.0)
    reversal_probability_pct: float = Field(ge=0.0, le=100.0)
    range_probability_pct: float = Field(ge=0.0, le=100.0)
    fakeout_probability_pct: float = Field(ge=0.0, le=100.0)
    avg_mfe_atr: float
    avg_mae_atr: float
    trust_score: float = Field(ge=0.0, le=1.0)
    minimum_sample_pass: bool
    evidence_quality: Literal["LOW_EVIDENCE", "MEDIUM", "STRONG"]
    top_failure_reasons: list[str]
    best_session_phase: str
    worst_session_phase: str
    point_in_time_safe: bool


class TimeframeFailureReasonRecord(BaseModel):
    timeframe: TimeframeValue
    pattern_id: str
    failure_reason: str
    case_count: int = Field(ge=0)
    failure_rate_pct: float = Field(ge=0.0, le=100.0)
    example_dates: list[str]
    no_trade_lesson: str


class HigherTimeframeInteractionRecord(BaseModel):
    lower_timeframe: TimeframeValue
    higher_timeframe: TimeframeValue
    interaction_type: Literal[
        "htf_reversal_zone",
        "htf_support_hold",
        "htf_resistance_rejection",
        "htf_breakout_retest",
        "timeframe_conflict",
    ]
    level_name: str
    support_resistance_state: str
    case_count: int = Field(ge=0)
    trust_adjustment_pct: float
    blocks_confidence: bool
    reason: str


class TimeframePatternTrustImpact(BaseModel):
    timeframe: TimeframeValue
    base_trust_score: float = Field(ge=0.0, le=1.0)
    conflict_adjusted_trust_score: float = Field(ge=0.0, le=1.0)
    conflict_state: Literal[
        "aligned",
        "lower_tf_pullback_inside_htf_trend",
        "lower_tf_breakout_into_htf_resistance",
        "higher_tf_reversal_with_lower_tf_lag",
        "timeframe_compression_conflict",
    ]
    impact_reason: str


class PatternByTimeframeGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class PatternByTimeframeReport(BaseModel):
    pattern_timeframe_version: str
    generated_at: str
    symbol: str
    exchange: str
    primary_timeframe: TimeframeValue
    timeframes: list[TimeframeValue]
    minimum_sample_size: int
    pattern_outcomes: list[TimeframePatternOutcomeRecord]
    failure_reasons: list[TimeframeFailureReasonRecord]
    htf_interactions: list[HigherTimeframeInteractionRecord]
    trust_impacts: list[TimeframePatternTrustImpact]
    all_timeframes_covered: bool
    all_patterns_have_outcome_history: bool
    timeframe_specific_failures_present: bool
    higher_timeframe_interactions_present: bool
    timeframe_conflict_reduces_trust: bool
    minimum_evidence_guard_active: bool
    all_records_point_in_time_safe: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[PatternByTimeframeGate]
    notes: list[str]


class MarketCalendarEventRegimeRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    trading_date: str = "2024-06-20"
    seed: int = Field(default=79, ge=0)
    minimum_event_sample_size: int = Field(default=30, ge=1, le=300)
    include_cross_market_context: bool = True
    current_session_phase: str = "09:30-10:15_real_trend_confirmation"
    gap_type: str = "gap_up_failure_watch"
    primary_timeframe: TimeframeValue = "5m"


class EventRegimeFlagRecord(BaseModel):
    event_class: Literal[
        "normal_day",
        "holiday",
        "half_day",
        "weekly_expiry",
        "monthly_expiry",
        "rbi_day",
        "fed_day",
        "budget_day",
        "election_result_day",
        "earnings_day",
        "special_trading_session",
        "post_holiday",
    ]
    active: bool
    source: Literal["exchange_calendar", "macro_calendar", "corporate_calendar", "manual_research_stub"]
    severity: Literal["info", "caution", "reduce_confidence", "block_trade_quality"]
    evidence_count: int = Field(ge=0)
    point_in_time_known: bool
    confidence_adjustment_pct: float
    no_trade_triggered: bool
    reason: str


class CalendarPatternReliabilityRecord(BaseModel):
    event_class: str
    pattern_family: str
    timeframe: TimeframeValue
    sample_count: int = Field(ge=0)
    independent_sample_count: int = Field(ge=0)
    continuation_probability_pct: float = Field(ge=0.0, le=100.0)
    reversal_probability_pct: float = Field(ge=0.0, le=100.0)
    fakeout_probability_pct: float = Field(ge=0.0, le=100.0)
    avg_move_atr: float
    reliability_score: float = Field(ge=0.0, le=1.0)
    minimum_sample_pass: bool
    reliability_note: str


class EventDaySafetyRuleRecord(BaseModel):
    rule_id: str
    event_class: str
    action: Literal["allow_research", "reduce_confidence", "force_wait", "force_no_trade"]
    triggered: bool
    linked_fields: list[str]
    reason: str
    required_user_message: str


class CalendarContextLinkRecord(BaseModel):
    link_id: str
    source_context: Literal["session_rhythm", "gap_context", "pattern_by_timeframe", "relative_strength", "news_event_filter"]
    event_class: str
    linked_observation: str
    trust_adjustment_pct: float
    blocks_confidence: bool
    explanation: str


class MarketCalendarEventRegimeGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class MarketCalendarEventRegimeReport(BaseModel):
    calendar_regime_version: str
    generated_at: str
    symbol: str
    exchange: str
    trading_date: str
    primary_timeframe: TimeframeValue
    event_flags: list[EventRegimeFlagRecord]
    pattern_reliability: list[CalendarPatternReliabilityRecord]
    safety_rules: list[EventDaySafetyRuleRecord]
    context_links: list[CalendarContextLinkRecord]
    active_event_classes: list[str]
    calendar_specific_reliability_present: bool
    event_day_gates_present: bool
    no_trade_or_reduced_confidence_gate_active: bool
    connected_to_session_gap_and_timeframe_memory: bool
    all_events_point_in_time_known: bool
    minimum_event_evidence_guard_active: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[MarketCalendarEventRegimeGate]
    notes: list[str]


class CrossMarketInfluenceRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    trading_date: str = "2024-06-20"
    session_phase: str = "09:30-10:15_real_trend_confirmation"
    primary_timeframe: TimeframeValue = "5m"
    seed: int = Field(default=80, ge=0)
    minimum_sample_size: int = Field(default=30, ge=1, le=300)
    require_cross_market_context: bool = False
    direction: TradeDirection = "long"


class CrossMarketSignalRecord(BaseModel):
    market_id: Literal[
        "gift_nifty",
        "nikkei_225",
        "hang_seng",
        "us_close_spx",
        "us_close_nasdaq",
        "europe_open_stoxx",
        "dxy",
        "usd_inr",
        "us_10y_yield",
        "india_10y_yield",
        "brent_crude",
    ]
    display_name: str
    return_pct: float | None
    direction: Literal["up", "down", "flat", "unavailable"]
    data_available: bool
    point_in_time_known: bool
    source: Literal["mock_provider", "unavailable"]
    influence_weight: float = Field(ge=0.0, le=1.0)
    influence_note: str


class CrossMarketSessionInfluenceRecord(BaseModel):
    influence_id: str
    session_phase: str
    market_id: str
    affected_behavior: Literal["gap", "opening_drive", "fakeout", "continuation", "range"]
    sample_count: int = Field(ge=0)
    independent_sample_count: int = Field(ge=0)
    effect_direction: Literal["supports_long", "supports_short", "increases_fakeout", "increases_range", "neutral", "unavailable"]
    probability_delta_pct: float
    minimum_sample_pass: bool
    explanation: str


class CrossMarketConflictRecord(BaseModel):
    conflict_id: str
    local_context: str
    external_context: str
    conflict_type: Literal[
        "global_risk_off_vs_local_long",
        "global_risk_on_vs_local_short",
        "currency_pressure",
        "yield_pressure",
        "oil_pressure",
        "missing_context",
    ]
    severity: Literal["info", "caution", "reduce_confidence", "force_wait"]
    confidence_adjustment_pct: float
    blocks_confidence: bool
    no_trade_reason: str | None


class CrossMarketCoverageRecord(BaseModel):
    required_market_id: str
    available: bool
    fallback_behavior: Literal["use_available_context_only", "reduce_coverage", "force_wait_if_required"]
    coverage_penalty_pct: float
    reason: str


class CrossMarketInfluenceGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class CrossMarketInfluenceReport(BaseModel):
    cross_market_version: str
    generated_at: str
    symbol: str
    exchange: str
    trading_date: str
    session_phase: str
    primary_timeframe: TimeframeValue
    direction: TradeDirection
    signals: list[CrossMarketSignalRecord]
    session_influences: list[CrossMarketSessionInfluenceRecord]
    conflicts: list[CrossMarketConflictRecord]
    coverage: list[CrossMarketCoverageRecord]
    context_coverage_pct: float = Field(ge=0.0, le=100.0)
    missing_context_reduces_coverage: bool
    cross_market_not_silently_neutral: bool
    influence_on_gap_opening_fakeout_continuation_present: bool
    no_trade_or_confidence_gate_active: bool
    all_available_context_point_in_time_safe: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[CrossMarketInfluenceGate]
    notes: list[str]


class CorporateActionAbnormalMarketRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    trading_date: str = "2024-06-20"
    seed: int = Field(default=81, ge=0)
    lookback_days: int = Field(default=252, ge=20, le=2000)
    quarantine_window_days: int = Field(default=10, ge=1, le=120)
    minimum_clean_sample_size: int = Field(default=30, ge=1, le=300)
    include_special_corporate_events: bool = True


class CorporateActionEventRecord(BaseModel):
    event_id: str
    event_type: Literal[
        "split",
        "bonus",
        "dividend_adjustment",
        "symbol_change",
        "suspension",
        "special_corporate_event",
    ]
    effective_date: str
    adjustment_factor: float | None
    source: Literal["mock_corporate_action_calendar", "manual_research_stub"]
    affects_ohlcv_continuity: bool
    contaminates_memory_window: bool
    quarantine_start: str
    quarantine_end: str
    reason: str


class AbnormalMarketEventRecord(BaseModel):
    event_id: str
    event_type: Literal[
        "upper_circuit_near",
        "lower_circuit_near",
        "trading_halt",
        "illiquid_spike",
        "single_candle_abnormal_print",
        "missing_halt_context",
    ]
    timestamp_ns: int
    severity: Literal["info", "warning", "blocker"]
    price_impact_pct: float
    volume_anomaly_z: float | None
    blocks_memory_update: bool
    blocks_trade_quality: bool
    reason: str


class MemoryContaminationRecord(BaseModel):
    contamination_id: str
    contamination_type: Literal["corporate_action", "abnormal_market", "halt_or_circuit", "manual_data_quality_flag"]
    affected_memory_tier: Literal["HOT", "WARM", "COLD", "ARCHIVE"]
    affected_window_start: str
    affected_window_end: str
    affected_pattern_families: list[str]
    clean_sample_count_after_exclusion: int = Field(ge=0)
    trust_adjustment_pct: float
    quarantine_required: bool
    rebuild_required: bool
    explanation: str


class MemoryQuarantineActionRecord(BaseModel):
    action_id: str
    action: Literal[
        "exclude_from_similarity",
        "quarantine_warm_memory",
        "reduce_trust",
        "force_no_trade",
        "preserve_raw_data",
        "trigger_rebuild_plan",
    ]
    triggered: bool
    target: str
    reason: str
    human_review_required: bool


class CorporateActionAbnormalMarketGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class CorporateActionAbnormalMarketReport(BaseModel):
    corporate_abnormal_version: str
    generated_at: str
    symbol: str
    exchange: str
    trading_date: str
    corporate_actions: list[CorporateActionEventRecord]
    abnormal_events: list[AbnormalMarketEventRecord]
    contamination_records: list[MemoryContaminationRecord]
    quarantine_actions: list[MemoryQuarantineActionRecord]
    clean_sample_count: int = Field(ge=0)
    corporate_action_filter_active: bool
    abnormal_market_filter_active: bool
    contaminated_memory_quarantined: bool
    trust_reduced_for_contaminated_analogs: bool
    raw_data_preserved_immutable: bool
    no_trade_gate_active: bool
    memory_update_blocked: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[CorporateActionAbnormalMarketGate]
    notes: list[str]


class PositionPortfolioCooldownRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    decision: BehaviorSignalValue = "BUY_BREAKOUT"
    account_equity: float = Field(default=1_000_000.0, gt=0.0)
    entry_price: float = Field(default=2500.0, gt=0.0)
    stop_loss: float = Field(default=2475.0, gt=0.0)
    target: float = Field(default=2575.0, gt=0.0)
    confidence_pct: float = Field(default=68.0, ge=0.0, le=100.0)
    liquidity_score: float = Field(default=0.78, ge=0.0, le=1.0)
    slippage_risk_pct: float = Field(default=0.12, ge=0.0, le=10.0)
    sector: str = "ENERGY"
    index: str = "NIFTY50"
    current_sector_exposure_pct: float = Field(default=18.0, ge=0.0, le=100.0)
    current_index_exposure_pct: float = Field(default=24.0, ge=0.0, le=100.0)
    correlation_cluster_exposure_pct: float = Field(default=19.0, ge=0.0, le=100.0)
    daily_pnl: float = -25000.0
    weekly_pnl: float = -55000.0
    consecutive_losses: int = Field(default=3, ge=0, le=100)
    choppy_regime: bool = False
    max_risk_per_trade_pct: float = Field(default=0.5, gt=0.0, le=5.0)
    max_daily_loss_pct: float = Field(default=2.0, gt=0.0, le=20.0)
    max_weekly_loss_pct: float = Field(default=5.0, gt=0.0, le=40.0)
    max_portfolio_heat_pct: float = Field(default=6.0, gt=0.0, le=100.0)
    max_sector_exposure_pct: float = Field(default=25.0, gt=0.0, le=100.0)
    max_index_exposure_pct: float = Field(default=40.0, gt=0.0, le=100.0)
    max_correlation_cluster_exposure_pct: float = Field(default=30.0, gt=0.0, le=100.0)
    cooldown_after_n_losses: int = Field(default=3, ge=1, le=20)
    cooldown_minutes: int = Field(default=30, ge=1, le=1440)


class AccountRiskSizingRecord(BaseModel):
    sizing_id: str
    entry_price: float
    stop_loss: float
    target: float
    stop_distance: float
    risk_reward: float
    adjusted_risk_pct: float
    raw_position_size: int
    capital_cap_position_size: int
    final_position_size: int
    capital_to_use: float
    max_loss_amount: float
    reward_amount: float
    sizing_blocked: bool
    reason: str


class PortfolioHeatMemoryRecord(BaseModel):
    exposure_id: str
    sector: str
    index: str
    sector_exposure_pct: float
    index_exposure_pct: float
    correlation_cluster_exposure_pct: float
    proposed_trade_heat_pct: float
    projected_portfolio_heat_pct: float
    max_portfolio_heat_pct: float
    blocks_trade: bool
    reasons: list[str]


class DailyWeeklyCooldownRecord(BaseModel):
    daily_pnl: float
    weekly_pnl: float
    max_daily_loss_amount: float
    max_weekly_loss_amount: float
    daily_loss_limit_hit: bool
    weekly_loss_limit_hit: bool
    consecutive_losses: int
    cooldown_after_n_losses: int
    choppy_regime: bool
    cooldown_active: bool
    cooldown_minutes: int
    reasons: list[str]


class ExposureCapRecord(BaseModel):
    cap_id: str
    cap_type: Literal["sector", "index", "correlation_cluster", "portfolio_heat"]
    current_value_pct: float
    proposed_value_pct: float
    max_allowed_pct: float
    pass_cap: bool
    action: Literal["allow_research", "reduce_size", "force_wait", "force_no_trade"]
    reason: str


class PositionPortfolioCooldownScenario(BaseModel):
    scenario_id: str
    label: str
    position_size: int
    projected_heat_pct: float
    daily_loss_limit_hit: bool
    weekly_loss_limit_hit: bool
    cooldown_active: bool
    trade_allowed: bool
    next_safe_action: Literal["RESEARCH_ONLY", "REDUCE_SIZE", "WAIT", "NO_TRADE"]
    blocker_reasons: list[str]


class PositionPortfolioCooldownGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    evidence: str
    remediation: str | None = None


class PositionPortfolioCooldownReport(BaseModel):
    risk_memory_version: str
    generated_at: str
    symbol: str
    exchange: str
    decision: BehaviorSignalValue
    sizing: AccountRiskSizingRecord
    portfolio_heat: PortfolioHeatMemoryRecord
    cooldown: DailyWeeklyCooldownRecord
    exposure_caps: list[ExposureCapRecord]
    scenarios: list[PositionPortfolioCooldownScenario]
    account_risk_sizing_present: bool
    exposure_caps_active: bool
    daily_weekly_loss_gates_active: bool
    cooldown_gate_active: bool
    research_only_sizing_estimate: bool
    no_live_route_attempted: bool
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[PositionPortfolioCooldownGate]
    notes: list[str]


class KronosBarrierProjection(BaseModel):
    projection_version: str
    source_forecast_hash: str
    target_hit_probability_pct: float = Field(ge=0.0, le=100.0)
    stop_hit_probability_pct: float = Field(ge=0.0, le=100.0)
    time_exit_probability_pct: float = Field(ge=0.0, le=100.0)
    expected_mfe: float
    expected_mae: float
    path_chop_probability_pct: float = Field(ge=0.0, le=100.0)
    barrier_sequence_distribution: dict[str, float]
    raw_path_not_direct_evidence: bool = True


class FullBehaviorForecast(BaseModel):
    forecast_version: str
    symbol: str
    behavior_decision: TradeDecisionResult
    combination_similarity: CombinationSimilarityReport
    behavior_target_hit_probability_pct: float = Field(ge=0.0, le=100.0)
    behavior_stop_hit_probability_pct: float = Field(ge=0.0, le=100.0)
    behavior_time_exit_probability_pct: float = Field(ge=0.0, le=100.0)
    behavior_expected_mfe: float
    behavior_expected_mae: float
    behavior_uncertainty_pct: float = Field(ge=0.0, le=100.0)
    risk_or_no_trade_authority: bool = True


class FullTwinAnalysisGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warning", "block"]
    evidence: str
    remediation: str | None = None


class FullTwinAnalysisRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: TimeframeValue = "5m"
    seed: int = Field(default=67, ge=0)
    lookback_candles: int = Field(default=64, ge=16, le=512)
    forecast_horizon_bars: int = Field(default=12, ge=1, le=120)
    force_kronos_hash_mismatch: bool = False
    force_decision_time_mismatch: bool = False
    force_behavior_no_trade: bool = False
    force_kronos_hard_conflict: bool = False


class FullTwinAnalysisReport(BaseModel):
    full_twin_version: str
    generated_at: str
    run_id: str
    symbol: str
    timeframe: TimeframeValue
    shared_snapshot: SharedAnalysisSnapshot
    snapshot_integrity: TwinSnapshotIntegrity
    behavior: FullBehaviorForecast
    kronos: KronosForecastResult
    kronos_barrier_projection: KronosBarrierProjection
    agreement_state: Literal[
        "AGREE_LONG",
        "AGREE_SHORT",
        "SOFT_CONFLICT",
        "HARD_CONFLICT",
        "SNAPSHOT_MISMATCH",
        "LOW_CONFIDENCE",
        "NO_TRADE",
        "WAIT",
    ]
    arbiter_action: Literal["RESEARCH_CANDIDATE", "WAIT", "NO_TRADE"]
    behavior_authority_preserved: bool
    kronos_confidence_boost_allowed: bool
    confidence_delta_from_kronos: float
    final_research_confidence_pct: float = Field(ge=0.0, le=100.0)
    conflict_reasons: list[str]
    gates: list[FullTwinAnalysisGate]
    evidence_hash: str
    deterministic: bool
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    kronos_cannot_execute_orders: bool = True
    kronos_cannot_override_no_trade: bool = True
    kronos_cannot_override_risk: bool = True
    openalgo_broker_route_created: bool = False
    notes: list[str]


class WalkForwardValidationRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframes: list[TimeframeValue] = Field(
        default_factory=lambda: ["1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"],
        min_length=1,
        max_length=9,
    )
    seed: int = Field(default=68, ge=0)
    fold_count: int = Field(default=5, ge=5, le=12)
    train_months: int = Field(default=12, ge=1, le=60)
    test_months: int = Field(default=3, ge=1, le=24)
    step_months: int = Field(default=1, ge=1, le=12)
    minimum_calibration_outcomes: int = Field(default=500, ge=1, le=100_000)
    weight_stability_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    max_relative_weight_variance: float = Field(default=0.20, ge=0.0, le=10.0)
    expected_calibration_error_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    recent_ece_recalibration_trigger: float = Field(default=0.10, ge=0.0, le=1.0)


class WalkForwardFoldResult(BaseModel):
    fold_id: str
    fold_index: int
    timeframe: TimeframeValue
    train_start_ns: int
    train_end_ns: int
    test_start_ns: int
    test_end_ns: int
    train_size_label: str
    test_size_label: str
    sample_count: int
    behavior_precision_at_10: float = Field(ge=0.0, le=1.0)
    kronos_precision_at_10: float = Field(ge=0.0, le=1.0)
    twin_precision_at_10: float = Field(ge=0.0, le=1.0)
    behavior_ece: float = Field(ge=0.0, le=1.0)
    kronos_ece: float = Field(ge=0.0, le=1.0)
    twin_ece: float = Field(ge=0.0, le=1.0)
    behavior_profit_factor: float
    kronos_profit_factor: float
    twin_profit_factor: float
    out_of_sample_only: bool
    no_future_leakage: bool


class EngineValidationSummary(BaseModel):
    engine: Literal["behavior", "kronos", "twin"]
    mean_precision_at_10: float = Field(ge=0.0, le=1.0)
    mean_ece: float = Field(ge=0.0, le=1.0)
    mean_profit_factor: float
    oos_sample_count: int
    calibration_passed: bool
    promotion_allowed: bool = False
    reliability_grade: Literal["research_only", "watch", "acceptable_mock"]
    notes: list[str]


class FamilyWeightStabilityRecord(BaseModel):
    family: str
    mean_weight: float = Field(ge=0.0, le=1.0)
    cross_fold_std: float = Field(ge=0.0)
    relative_variance: float = Field(ge=0.0)
    stable: bool


class WalkForwardValidationGate(BaseModel):
    gate_id: str
    name: str
    passed: bool
    severity: Literal["info", "warning", "block"]
    evidence: str
    remediation: str


class WalkForwardValidationReport(BaseModel):
    validation_version: str
    generated_at: str
    run_id: str
    symbol: str
    timeframes: list[TimeframeValue]
    method: Literal["walk_forward_optimization"]
    fold_count: int
    train_size: str
    test_size: str
    step_size: str
    objective: str
    minimum_calibration_outcomes: int
    expected_calibration_error_threshold: float
    recent_ece_recalibration_trigger: float
    folds: list[WalkForwardFoldResult]
    engine_summaries: list[EngineValidationSummary]
    family_weight_stability: list[FamilyWeightStabilityRecord]
    all_folds_out_of_sample: bool
    weight_stability_passed: bool
    calibration_passed: bool
    recalibration_required: bool
    promotion_allowed: bool = False
    deterministic: bool = True
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    gates: list[WalkForwardValidationGate]
    notes: list[str]
    evidence_hash: str


class ReleaseEvidenceBundle(BaseModel):
    bundle_version: str
    bundle_id: str
    symbol: str
    target_mode: Literal["REPLAY"]
    generated_at: str
    approval: ReleaseApprovalRecord | None
    checklist: MockToReplayReleaseChecklist
    benchmark_report: BehaviorBenchmarkReport
    benchmark_drilldown: BenchmarkDrilldown
    evidence_index: dict[str, str]
    gate_summary: dict[str, Any]
    final_blockers: list[str]
    bundle_hash: str
    immutable: bool = True
    live_trading_blocked: bool = True
    notes: list[str]


class ReleaseEvidenceArtifactExportRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=32)
    approval_id: str | None = None
    requested_by: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=10, max_length=500)
    artifact_format: Literal["json_manifest"] = "json_manifest"
    retention_days: int = Field(default=365, ge=1, le=3650)


class ReleaseEvidenceArtifact(BaseModel):
    artifact_version: str
    artifact_id: str
    symbol: str
    target_mode: Literal["REPLAY"]
    created_at: str
    requested_by: str
    reason: str
    artifact_format: Literal["json_manifest"]
    bundle_id: str
    bundle_hash: str
    artifact_dir: str
    bundle_file_path: str
    bundle_sha256: str
    bundle_size_bytes: int
    manifest_file_path: str
    manifest_sha256: str
    manifest_size_bytes: int
    retention_days: int
    immutable: bool = True
    live_trading_blocked: bool = True
    contains_broker_credentials: bool = False
    contains_live_orders: bool = False


class ReleaseEvidenceArtifactVerification(BaseModel):
    verification_version: str
    artifact_id: str
    verified_at: str
    bundle_file_exists: bool
    manifest_file_exists: bool
    bundle_sha256_matches: bool
    manifest_sha256_matches: bool
    bundle_json_parseable: bool
    verified: bool
    issues: list[str]
    live_trading_blocked: bool = True


class BehaviorBenchmarkRun(BaseModel):
    run_id: str
    symbol: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    completed_at: str | None = None
    mode: SystemModeValue = SystemModeValue.MOCK
    benchmark_type: Literal["mock_contract", "walk_forward", "out_of_sample", "replay"] = "mock_contract"
    metrics: dict[str, Any] = Field(default_factory=dict)
    safety_notes: list[str] = Field(default_factory=list)


class BehaviorReplayRecord(BaseModel):
    run_id: str
    symbol: str
    similar_day_ids: list[str]
    replay_snapshot_id: str | None
    events: list[MarketEvent]
    deterministic: bool = True


class FeatureManifestEntry(BaseModel):
    feature_manifest_version: str
    feature_id: str
    feature_index: int = Field(ge=0)
    feature_type: Literal["numeric", "event", "boolean", "categorical", "sequence", "mixed"]
    feature_block: str
    normalization_method: str
    normalization_formula: str | None = None
    missing_default: float | str | bool | None = None
    missing_mask_enabled: bool = True
    missing_policy: str = "masked_missing_not_zero_signal"
    low_variance_policy: str = "low_variance_flag_not_missing"
    similarity_policy: str = "masked_cosine_min_overlap_0_70"
    is_active: bool = True
    probability_enabled: bool = False


class FeatureManifest(BaseModel):
    feature_manifest_version: str
    source_registry_version: str
    generated_at: str
    feature_count: int = Field(ge=0)
    vector_dimension: int = Field(ge=0)
    stable_order_hash: str
    entries: list[FeatureManifestEntry]
    requires_index_rebuild: bool = False
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class IndicatorSequenceRecord(BaseModel):
    indicator_id: str
    feature_block: str
    manifest_slot: int = Field(default=0, ge=0)
    last_9_values: list[float | None]
    last_9_signals: list[str]
    value_missing_mask: list[bool]
    source_mode: Literal["mock", "real", "masked", "synthetic_fallback"] = "mock"
    runtime_status: str = "mock_generated"
    normalized_from: str | None = None
    raw_output_present: bool = False
    explanation_only: bool = False
    usable_for_probability: bool
    missing_reason: str | None = None


class IndicatorFeatureBlock(BaseModel):
    indicator_id: str
    feature_block: str
    manifest_slot: int = Field(default=0, ge=0)
    last_9_values: list[float | None]
    last_9_signals: list[str]
    matched_winner_count: int = Field(ge=0)
    matched_failure_count: int = Field(ge=0)
    historical_effect: str
    current_alignment: float = Field(ge=0.0, le=1.0)
    source_mode: Literal["mock", "real", "masked", "synthetic_fallback"] = "mock"
    runtime_status: str = "mock_generated"
    normalized_from: str | None = None
    raw_output_present: bool = False
    explanation_only: bool = False
    usable_for_probability: bool
    missing_reason: str | None = None


class NineCandleFeatureVector(BaseModel):
    setup_id: str
    symbol: str
    timeframe: str
    decision_time: str
    source_snapshot_id: str
    feature_manifest_version: str
    vector_dimension: int = Field(ge=0)
    feature_values: list[float]
    feature_missing_mask: list[bool]
    feature_block_values: dict[str, float]
    closed_candle_only: bool = True
    duplicate_or_missing_candle: bool = False
    incomplete_htf_blocked: bool = False
    future_leakage_detected: bool = False


class NineCandleFeatureVectorAudit(BaseModel):
    audit_version: str
    symbol: str
    timeframe: str
    feature_manifest_version: str
    expected_feature_manifest_version: str
    vector_dimension: int = Field(ge=0)
    manifest_feature_count: int = Field(ge=0)
    feature_value_count: int = Field(ge=0)
    missing_mask_count: int = Field(ge=0)
    active_feature_count: int = Field(ge=0)
    probability_enabled_count: int = Field(ge=0)
    usable_probability_feature_count: int = Field(ge=0)
    promoted_runtime_indicator_count: int = Field(default=0, ge=0)
    real_runtime_computed_count: int = Field(default=0, ge=0)
    synthetic_fallback_computed_count: int = Field(default=0, ge=0)
    runtime_unavailable_count: int = Field(default=0, ge=0)
    runtime_failed_count: int = Field(default=0, ge=0)
    runtime_accounting_pass: bool = True
    real_runtime_masked_count: int = Field(default=0, ge=0)
    non_promoted_masked_count: int = Field(default=0, ge=0)
    missing_value_count: int = Field(ge=0)
    normalized_range_pass: bool
    finite_values_pass: bool
    vector_length_pass: bool
    manifest_version_pass: bool
    feature_order_pass: bool
    missing_mask_pass: bool
    probability_mask_pass: bool
    wait_required: bool
    failure_reasons: list[str]
    warnings: list[str]
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class NineCandleEvidencePacket(BaseModel):
    packet_version: str
    evidence_packet_id: str
    evidence_packet_hash: str
    symbol: str
    timeframe: str
    decision_time: str
    source_snapshot_id: str
    feature_manifest_version: str
    source_registry_version: str
    last_9_candles: list[dict[str, Any]]
    indicator_sequences: list[IndicatorSequenceRecord]
    feature_vector: NineCandleFeatureVector
    levels: list[dict[str, Any]]
    session_phase: str
    regime_id: str
    regime_group: str
    data_quality_score: float = Field(ge=0.0, le=1.0)
    closed_candle_only: bool = True
    no_future_leakage: bool = True
    future_bar_blocked: bool = True
    deterministic: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class NineCandleSetupRecord(BaseModel):
    setup_id: str
    symbol: str
    timeframe: str
    decision_time: str | None = None
    source_snapshot_id: str | None = None
    evidence_packet_id: str | None = None
    evidence_packet_hash: str | None = None
    session_phase: str
    regime_id: str
    feature_manifest_version: str
    entry_zone: list[float]
    stop: float
    target: float
    invalidation: float
    data_quality: float = Field(ge=0.0, le=1.0)
    created_at: str
    label_status: Literal["pending", "complete"] = "pending"
    setup_hash: str | None = None
    label_count: int = 0
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class OutcomeHorizonLabel(BaseModel):
    setup_id: str
    horizon_candles: Literal[3, 5, 9, 12, 20]
    label_status: Literal["pending", "complete"]
    outcome_label: Literal["TARGET_HIT", "SL_HIT", "PARTIAL_WIN", "BREAKEVEN", "TIME_EXIT", "FAKE_BREAKOUT", "RETEST_SUCCESS", "RETEST_FAIL", "CHOP_NO_FOLLOWTHROUGH"] = "TIME_EXIT"
    mfe: float
    mae: float
    target_first: bool
    stop_first: bool
    fakeout: bool
    retest_seen: bool
    direction_after_h: Literal["up", "down", "range", "unknown"]
    range_after_h: float
    time_to_target: int | None = None
    time_to_stop: int | None = None
    max_drawdown_before_profit: float
    intrabar_ambiguity_rule: str
    label_hash: str | None = None
    future_leakage_detected: bool = False


class WinnerFailureAnalogResult(BaseModel):
    analog_version: str
    symbol: str
    timeframe: str
    feature_manifest_version: str
    total_matches: int = Field(ge=0)
    winner_like_matches: int = Field(ge=0)
    failure_like_matches: int = Field(ge=0)
    winner_similarity: float = Field(ge=0.0, le=1.0)
    failure_similarity: float = Field(ge=0.0, le=1.0)
    sample_quality: Literal["low", "medium", "strong"]
    retrieval_engine: Literal["numpy_cosine_fallback", "faiss_index_flat_ip_exact", "faiss_approx_reserved"]
    two_stage_filter_applied: bool = True
    approximate_faiss_used: bool = False
    index_version: str
    active_index_hash: str
    notes: list[str]


class AnalogIndexManifest(BaseModel):
    manifest_id: str | None = None
    symbol: str | None = None
    timeframe: str | None = None
    index_version: str
    feature_manifest_version: str
    vector_dimension: int = Field(ge=0)
    record_count: int = Field(ge=0)
    index_hash: str
    index_type: str
    artifact_uri: str | None = None
    artifact_sha256: str | None = None
    artifact_size_bytes: int = Field(default=0, ge=0)
    artifact_format: Literal["json_exact_cosine_v1", "faiss_reserved"] = "json_exact_cosine_v1"
    artifact_verified: bool = False
    active_pointer_swapped_at: str
    atomic_swap_required: bool = True
    validated: bool
    active: bool = True
    previous_index_hash: str | None = None
    build_status: Literal["validated", "rejected"] = "validated"
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class NineCandleModelPrediction(BaseModel):
    model_version: str
    usable_for_probability: bool
    calibrated_target_prob: float = Field(ge=0.0, le=1.0)
    calibrated_stop_prob: float = Field(ge=0.0, le=1.0)
    calibrated_fakeout_prob: float = Field(ge=0.0, le=1.0)
    expected_r_after_cost: float
    model_edge: float
    weights_mutated_live: bool = False
    live_retraining_enabled: bool = False
    paper_candidate_allowed: bool = False


class ProbabilityCalibrationBin(BaseModel):
    predicted_bucket: str
    actual_target_rate: float = Field(ge=0.0, le=1.0)
    actual_stop_rate: float = Field(ge=0.0, le=1.0)
    calibration_error: float = Field(ge=0.0, le=1.0)
    sample_count: int = Field(ge=0)


class FeatureBlockImportanceReport(BaseModel):
    report_version: str
    method: Literal["feature_block_shap", "feature_block_permutation", "mock_reserved"]
    stable_across_walkforward: bool
    top_blocks: list[dict[str, Any]]
    raw_indicator_shap_trusted: bool = False


class NineCandleHybridDecision(BaseModel):
    decision_version: str
    symbol: str
    timeframe: str
    decision: Literal["WAIT", "WATCH", "PAPER-CANDIDATE", "BLOCK"]
    final_edge: float
    model_edge: float
    analog_edge: float
    quality_multiplier: float = Field(ge=0.0, le=1.0)
    sample_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    data_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    freshness_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    overlap_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    proof_score: float = Field(default=0.0, ge=0.0, le=1.0)
    mode: Literal["mock", "replay", "backtest", "paper", "live"] = "mock"
    regime_id: str = "pending"
    regime_group: str = "pending"
    evidence_packet_id: str = "pending"
    evidence_packet_hash: str = "pending"
    safety_gates: list[dict[str, Any]]
    final_reason: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class NineCandleJarvisPanel(BaseModel):
    panel_version: str
    title: str
    symbol: str
    timeframe: str
    decision: Literal["WAIT", "WATCH", "PAPER-CANDIDATE", "BLOCK"]
    memory: WinnerFailureAnalogResult
    alignment: dict[str, float]
    model: NineCandleModelPrediction
    trust: dict[str, str]
    feature_manifest: FeatureManifest
    evidence_packet: NineCandleEvidencePacket
    current_dna: NineCandleFeatureVector
    indicator_drilldown: list[IndicatorFeatureBlock]
    calibration_bins: list[ProbabilityCalibrationBin]
    feature_importance: FeatureBlockImportanceReport
    hybrid_decision: NineCandleHybridDecision
    final_reason: str
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True


class NineCandleBuildRequest(BaseModel):
    symbol: str = Field(default="RELIANCE", min_length=1, max_length=40)
    timeframe: str = Field(default="1m", min_length=1, max_length=16)
    feature_manifest_version: str = "nine-candle-feature-manifest.v1"
    require_htf: bool = True
    allow_incomplete_candle: bool = False
    use_real_indicators: bool = False


class NineCandleSaveSetupRequest(NineCandleBuildRequest):
    source_snapshot_id: str = "mock-9c-current"


class NineCandleOutcomeLabelRequest(BaseModel):
    setup_id: str = "9c-reliance-1m-current"
    symbol: str = "RELIANCE"
    timeframe: str = "1m"
    conservative_intrabar: bool = True
    future_candles: list[dict[str, Any]] = Field(default_factory=list)
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    direction: Literal["long", "short"] = "long"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utc_now().isoformat()
