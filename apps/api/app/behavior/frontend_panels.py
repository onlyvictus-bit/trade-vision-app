from __future__ import annotations

from ..models import BehaviorFrontendPanelMapItem, BehaviorFrontendPanelMapResult, CapabilityManifestItem, CapabilityStatus


PANEL_MAP_VERSION = "behavior-frontend-workspace.v0.23"


def build_behavior_frontend_panel_map(capabilities: list[CapabilityManifestItem]) -> BehaviorFrontendPanelMapResult:
    status_by_name = {capability.name: capability.status for capability in capabilities}
    panels = [
        _panel("contract_lock", "Behavior Intelligence Contract Lock", 1, "Data Quality Engine", "BehaviorSpec", "/api/v1/behavior/spec", ["layer_contracts", "output_columns", "verbatim_registry"], "Behavior Intelligence Contract Lock", status_by_name),
        _panel("current_decision", "Current Behavior Decision", 18, "Trade Decision Engine", "BehaviorAnalysisResult", "/api/v1/behavior/analyze", ["final_trade_decision", "trade_allowed", "no_trade_reason"], "Behavior Intelligence Contract Lock", status_by_name),
        _panel("universal_agreement", "Universal Agreement Decision Engine", 18, "Trade Decision Engine", "TradeDecisionResult", "/api/v1/behavior/decision/current", ["final_trade_decision", "agreement_checks", "confidence_pct"], "Behavior Decision Engine", status_by_name),
        _panel("agreement_gates", "Agreement Checks + Safety Gates", 29, "No-Trade Intelligence", "TradeDecisionResult", "/api/v1/behavior/decision/current", ["gates", "no_trade", "wait_for"], "Behavior No-Trade Intelligence", status_by_name),
        _panel("reason_tree", "Human-Readable Reason Tree", 30, "Human-Readable Reason Tree", "ReasonTreeResult", "/api/v1/behavior/decision/current", ["nodes", "ordered_reasons"], "Behavior Human-Readable Reason Tree", status_by_name),
        _panel("risk_sizing", "Risk Sizing + Capital Safety", 31, "Risk-of-Ruin / Capital Safety", "RiskSizingResult", "/api/v1/behavior/risk/current", ["position_size", "risk_per_trade_pct", "capital_to_use"], "Behavior Risk Sizing Engine", status_by_name),
        _panel("portfolio_cooldown", "Portfolio Exposure + Cooldown", 31, "Risk-of-Ruin / Capital Safety", "RiskSizingResult", "/api/v1/behavior/risk/current", ["portfolio", "daily_loss", "block_reasons"], "Behavior Portfolio Exposure Control", status_by_name),
        _panel("execution_fill", "Execution Fill Realism", 3, "Slippage + Brokerage Model", "ExecutionSimulationResult", "/api/v1/behavior/execution/current", ["fill_status", "filled_quantity", "missed_trade_reason"], "Behavior Execution Simulation Engine", status_by_name),
        _panel("execution_costs", "Execution Cost Breakdown", 3, "Slippage + Brokerage Model", "ExecutionCostBreakdown", "/api/v1/behavior/execution/current", ["costs", "queue_position_estimate", "adverse_selection_risk"], "Behavior Slippage Impact Latency Model", status_by_name),
        _panel("context_engines", "Context Engines", 9, "VPD + ORB + CPR/Pivot + VWAP Context", "BehaviorContextResult", "/api/v1/behavior/context/full", ["levels", "htf", "gap", "market"], "Behavior Full Context Engine", status_by_name),
        _panel("context_reason_tree", "Context Reason Tree", 11, "Higher-Timeframe Confirmation", "BehaviorContextResult", "/api/v1/behavior/context/full", ["reason_tree"], "Behavior Full Context Engine", status_by_name),
        _panel("session_rhythm", "Session Rhythm + Stock DNA", 17, "Session Personality & Rhythm", "StockDNASummary", "/api/v1/behavior/stock/{symbol}/dna/summary", ["session_rhythm", "stock_dna", "risk_warnings"], "Behavior Stock DNA Summary", status_by_name),
        _panel("exact_time_session_memory_v071", "Exact-Time Session Memory v0.71", 17, "Session Personality & Rhythm", "ExactTimeSessionMemoryReport", "/api/v1/behavior/exact-time/session-memory/current", ["minute_profiles", "current_minute_profile", "session_transitions", "calendar_profiles", "gates"], "Behavior Exact-Time Session Memory", status_by_name),
        _panel("day_of_week", "Day-of-Week Memory", 17, "Session Personality & Rhythm", "DayOfWeekMemoryResult", "/api/v1/behavior/stock/{symbol}/day-of-week-memory", ["records", "blocks_strong_probability"], "Behavior Day-Of-Week Memory", status_by_name),
        _panel("session_segments", "Session Segment Scores", 17, "Session Personality & Rhythm", "SessionRhythmResult", "/api/v1/behavior/session/rhythm", ["segments", "current_session_phase"], "Behavior Session Rhythm Engine", status_by_name),
        _panel("pattern_memory", "Pattern Memory + Similar-Day Replay", 8, "Intraday Pattern Memory", "PatternMemoryResult", "/api/v1/behavior/stock/{symbol}/pattern-memory", ["day_shape_vector", "matches", "no_trade_reason"], "Behavior Pattern Memory Engine", status_by_name),
        _panel("similar_days", "Similar-Day Matches", 32, "Similar-Day Replay Engine", "SimilarDayMatch", "/api/v1/behavior/similar-days/{symbol}", ["similarity_score_pct", "outcome_label", "feature_match_summary"], "Behavior Similar-Day Replay Engine", status_by_name),
        _panel("combination_similarity", "Combination Similarity", 8, "Intraday Pattern Memory", "CombinationSimilarityReport", "/api/v1/behavior/combination-similarity/current", ["non_overlap_match_count", "continuation_probability_pct", "fakeout_probability_pct", "sequential_signal_pattern", "matches", "gates"], "Behavior Combination Similarity", status_by_name),
        _panel("analog_conditional_research_v073", "Analog Conditional Research v0.73", 8, "Intraday Pattern Memory", "AnalogConditionalResearchReport", "/api/v1/behavior/analog-research/current", ["value_bands", "conditional_rules", "match_explanations", "false_discovery_control", "gates"], "Behavior Analog Conditional Research", status_by_name),
        _panel("event_sequence_mining_v074", "Event Sequence Mining v0.74", 8, "Intraday Pattern Memory", "EventSequenceMiningReport", "/api/v1/behavior/event-sequences/current", ["sequence_patterns", "reciprocal_signal_records", "prior_to_current_influence", "gates"], "Behavior Event Sequence Mining", status_by_name),
        _panel("false_agreement_confluence_v075", "False Agreement + Confluence v0.75", 10, "Indicator Similarity Engine", "FalseAgreementConfluenceReport", "/api/v1/behavior/confluence/diagnostics/current", ["confluence_timing_windows", "indicator_value_confluence_records", "false_agreement_records", "confidence_block_reasons", "gates"], "Behavior False Agreement Confluence Diagnostics", status_by_name),
        _panel("design_similarity_v076", "Design Similarity + Shape Grammar v0.76", 16, "Support/Resistance Memory", "DesignSimilarityReport", "/api/v1/behavior/design-similarity/current", ["grammar_components", "geometry_references", "similarity_candidates", "overlay_evidence", "gates"], "Behavior Design Similarity Shape Grammar", status_by_name),
        _panel("band_level_distance_v077", "Band/Level Distance + Value Clusters v0.77", 16, "Support/Resistance Memory", "BandLevelDistanceReport", "/api/v1/behavior/bands/distances", ["distance_records", "repeated_value_clusters", "outcome_influences", "missing_levels", "gates"], "Behavior Band Level Distance Memory", status_by_name),
        _panel("pattern_by_timeframe_v078", "Pattern-by-Timeframe Outcomes v0.78", 8, "Intraday Pattern Memory", "PatternByTimeframeReport", "/api/v1/behavior/patterns/by-timeframe", ["pattern_outcomes", "failure_reasons", "htf_interactions", "trust_impacts", "gates"], "Behavior Pattern By Timeframe Outcome Memory", status_by_name),
        _panel("market_calendar_event_regime_v079", "Market Calendar + Event Regime v0.79", 17, "Session Personality & Rhythm", "MarketCalendarEventRegimeReport", "/api/v1/behavior/calendar/event-regime/current", ["event_flags", "pattern_reliability", "safety_rules", "context_links", "gates"], "Behavior Market Calendar Event Regime Memory", status_by_name),
        _panel("cross_market_influence_v080", "Cross-Market Influence Memory v0.80", 15, "Index/Market Context", "CrossMarketInfluenceReport", "/api/v1/behavior/cross-market/influence/current", ["signals", "session_influences", "conflicts", "coverage", "gates"], "Behavior Cross-Market Influence Memory", status_by_name),
        _panel("corporate_abnormal_memory_v081", "Corporate Action + Abnormal Market Memory v0.81", 1, "Data Quality Engine", "CorporateActionAbnormalMarketReport", "/api/v1/behavior/corporate-abnormal/current", ["corporate_actions", "abnormal_events", "contamination_records", "quarantine_actions", "gates"], "Behavior Corporate Action Abnormal Market Memory", status_by_name),
        _panel("position_portfolio_cooldown_v082", "Position Sizing + Portfolio Cooldown v0.82", 31, "Risk-of-Ruin / Capital Safety", "PositionPortfolioCooldownReport", "/api/v1/behavior/risk/portfolio-cooldown/current", ["sizing", "portfolio_heat", "cooldown", "exposure_caps", "scenarios", "gates"], "Behavior Position Portfolio Cooldown Memory", status_by_name),
        _panel("execution_intent_paper_safety_v083", "Execution Intent + Paper Safety v0.83", 24, "Trade Lifecycle Tracking", "ExecutionIntentPaperSafetyReport", "/api/v1/behavior/execution-intent/paper-safety/current", ["intent_lifecycle", "paper_estimates", "manual_review", "gates"], "Behavior Execution Intent Paper Safety Memory", status_by_name),
        _panel("paper_executor_permission_v084", "Paper Executor Permission Matrix v0.84", 29, "No-Trade Intelligence", "PaperExecutorPermissionReport", "/api/v1/behavior/execution-permission/preflight/current", ["permission_matrix", "kill_switch_recheck", "human_approval", "preflight_gates", "rejection_reasons"], "Behavior Paper Executor Permission Matrix", status_by_name),
        _panel("executor_handoff_audit_v085", "Executor Handoff Audit Receipt v0.85", 24, "Trade Lifecycle Tracking", "ExecutorHandoffAuditEnvelope", "/api/v1/behavior/executor-handoff/audit/current", ["intent", "evidence_bindings", "receipt", "permission_report", "paper_safety"], "Behavior Executor Handoff Audit Envelope", status_by_name),
        _panel("kronos_shared_snapshot", "Kronos Shared Snapshot Integrity", None, "Forecast Twin", "KronosSharedSnapshotForecastReport", "/api/v1/kronos/forecast-shared-snapshot/current", ["snapshot", "receipt", "integrity", "behavior_can_continue_without_kronos"], "Kronos Shared Snapshot Contract", status_by_name),
        _panel("full_twin_analysis", "Full Twin Analysis", None, "Forecast Twin", "FullTwinAnalysisReport", "/api/v1/twin/full-analysis/current", ["snapshot_integrity", "behavior", "kronos_barrier_projection", "agreement_state", "arbiter_action", "gates"], "Full Twin Analysis", status_by_name),
        _panel("walk_forward_validation_v068", "Walk-Forward Validation v0.68", 26, "Walk-Forward Testing", "WalkForwardValidationReport", "/api/v1/behavior/walk-forward/current", ["engine_summaries", "folds", "family_weight_stability", "gates"], "Behavior Walk-Forward Validation v0.68", status_by_name),
        _panel("outcome_trust", "Outcome Learning + Trust Table", 22, "Learning & Trust Table", "LearningTrustResult", "/api/v1/behavior/stock/{symbol}/trust-table", ["aggregate_trust_score", "calibration_status", "records"], "Behavior Learning Trust Table", status_by_name),
        _panel("conservative_outcome_labeler", "Conservative Outcome Labeler", 24, "Trade Lifecycle Tracking", "ConservativeOutcomeLabelResult", "/api/v1/behavior/outcomes/conservative-label/current", ["outcome_label", "same_bar_ambiguous", "gap_through_stop", "mfe_atr", "mae_atr", "net_return_after_costs"], "Behavior Conservative Outcome Labeler", status_by_name),
        _panel("failure_library", "Failure Pattern Library", 23, "Failure Pattern Library", "FailureLibraryResult", "/api/v1/behavior/stock/{symbol}/failure-library", ["failures", "most_common_failure", "no_trade_lessons"], "Behavior Failure Pattern Library", status_by_name),
        _panel("day_shape_vector", "Day Shape Vector", 8, "Intraday Pattern Memory", "DayShapeVector", "/api/v1/behavior/stock/{symbol}/pattern-memory", ["gap_pct", "first_15m_return", "high_break_time"], "Behavior Pattern Memory Engine", status_by_name),
        _panel("layer_contracts", "32 Layer Contracts", None, "Architecture Register", "BehaviorLayerContract", "/api/v1/behavior/spec", ["layer_index", "layer_name", "contract_name", "status"], "Behavior Intelligence Contract Lock", status_by_name),
        _panel("output_columns", "74 Output Columns", None, "Output Registry", "BehaviorOutputColumn", "/api/v1/behavior/output-columns", ["name", "group", "index"], "Behavior Intelligence Contract Lock", status_by_name),
        _panel("migration_source", "Stock-App Migration Source", None, "Migration Register", "BehaviorSpec", "/api/v1/behavior/spec", ["stock_app_source_root"], "Stock-App Chart Indicator Backtest Migration", status_by_name, fallback_state="reserved", required=False),
        _panel("runtime_readiness", "Indicator + Chart + Replay Runtime Readiness", None, "Runtime Readiness Register", "RuntimeReadinessReport", "/api/v1/behavior/runtime/readiness", ["total_output_groups", "chart_output_ready", "research_activity_ready", "replay_ready"], "Behavior Runtime Readiness Probe", status_by_name),
        _panel("indicator_registry_lock", "Indicator Registry Lock", None, "Indicator Registry", "BehaviorIndicatorRegistryReport", "/api/v1/behavior/indicators/registry", ["total_output_groups", "required_added_indicators_present", "status_counts", "gates"], "Behavior Indicator Registry Lock", status_by_name),
        _panel("indicator_reliability_drilldown_v182", "Indicator Reliability Drilldown v1.82", None, "Indicator Reliability Memory", "IndicatorReliabilityReport", "/api/v1/behavior/indicators/si_macd_ta/reliability/RELIANCE", ["purpose", "category", "confirmation_delay_bars", "lag_weight", "sample_count", "minimum_sample_pass", "reliability_state", "reciprocal_signal_warning", "quarantine_reason", "lag_vote_preview"], "Behavior Indicator Reliability Memory", status_by_name),
        _panel("indicator_signal_history_drilldown_v183", "Persistent Indicator Signal History v1.83", None, "Indicator Reliability Memory", "IndicatorSignalHistorySummary", "/api/v1/behavior/indicators/si_macd_ta/signal-history/RELIANCE", ["record_count", "counted_record_count", "pending_record_count", "complete_record_count", "latest_signal_time_ns", "storage_backed", "records"], "Behavior Persistent Indicator Signal History", status_by_name),
        _panel("indicator_reliability_drilldown_v183", "Indicator Reliability Drilldown v1.83", None, "Indicator Reliability Memory", "IndicatorReliabilityReport", "/api/v1/behavior/indicators/si_macd_ta/reliability-drilldown/RELIANCE", ["trader_summary", "history", "reliability", "history_source", "persisted_history_count", "fixture_fallback_used"], "Behavior Persistent Indicator Signal History", status_by_name),
        _panel("indicator_signal_history_ingestion_v184", "Indicator Signal History Ingestion v1.84", None, "Indicator Reliability Memory", "IndicatorSignalHistoryIngestCurrentReport", "/api/v1/behavior/indicators/reliability/ingest-current", ["saved_record_count", "pending_record_count", "counted_record_count", "skipped_missing_count", "skipped_neutral_count", "gates"], "Behavior Indicator Signal History Ingestion", status_by_name),
        _panel("indicator_pending_outcome_completion_v185", "Indicator Pending Outcome Completion v1.85", None, "Indicator Reliability Memory", "IndicatorSignalHistoryCompletePendingReport", "/api/v1/behavior/indicators/reliability/complete-pending", ["scanned_pending_count", "completed_count", "still_pending_count", "skipped_count", "gates"], "Behavior Indicator Pending Outcome Completion", status_by_name),
        _panel("indicator_observations_v069", "Indicator Observations v0.69", None, "Indicator Observation Contract", "IndicatorObservationReport", "/api/v1/behavior/indicators/observations/current", ["observations", "multi_output_indicator_count", "all_observations_have_lineage", "gates"], "Behavior Indicator Observation Contracts", status_by_name),
        _panel("pattern_taxonomy_v070", "Structure Pattern Registry v0.70", None, "Structure and Pattern Registry", "PatternTaxonomyReport", "/api/v1/behavior/patterns/taxonomy/current", ["entries", "activity_records", "trendline_respect_evidence", "candle_neighbor_effect", "gates"], "Behavior Structure Pattern Registry", status_by_name),
        _panel("multi_timeframe_conflict_v072", "Multi-Timeframe Conflict v0.72", None, "Multi-Timeframe Conflict Engine", "MultiTimeframeConflictReport", "/api/v1/behavior/timeframes/conflict/current", ["seven_timeframe_matrix", "conflict_explanations", "developing_bars_blocked_from_decision", "alignment_score", "gates"], "Behavior Multi-Timeframe Conflict Engine", status_by_name),
        _panel("real_mtf_pullback_v163", "Real MTF Pullback v1.63", 11, "Higher-Timeframe Confirmation", "RealMtfPullbackReport", "/api/v1/behavior/timeframes/pullback/current", ["pullback_state", "final_action", "trader_summary", "opposition_timeframes", "pullback_timeframes", "gates"], "Behavior Real MTF Pullback Engine", status_by_name),
        _panel("seven_timeframe_feature_runtime", "Full-Timeframe Feature Runtime v1.82", None, "Feature Runtime", "SevenTimeframeFeatureRuntimeReport", "/api/v1/behavior/features/seven-timeframe/current", ["required_timeframes", "closed_bar_records", "indicator_coverage", "gates"], "Behavior Full Timeframe Contract Expansion", status_by_name),
        _panel("columnar_feature_store", "Columnar Historical Feature Store", None, "Feature Store", "FeatureStoreStatusReport", "/api/v1/behavior/feature-store/status", ["record_count", "latest_records", "indexes", "corruption_check_passed"], "Behavior Columnar Historical Feature Store", status_by_name),
        _panel("redundancy_control", "Redundancy Control", None, "Feature Weighting", "RedundancyAuditReport", "/api/v1/behavior/redundancy/audit/current", ["family_weights", "clusters", "suppressed_duplicate_features", "cross_family_audit"], "Behavior Redundancy Control", status_by_name),
        _panel("replay_indicator_chart_validation", "Replay Indicator Chart Validation", None, "Runtime Validation Register", "ReplayIndicatorValidationReport", "/api/v1/behavior/replay/indicator-chart/current", ["candle_count", "indicator_count", "chart_point_count", "output_hash"], "Behavior Replay Indicator Chart Validation", status_by_name),
        _panel("replay_indicator_matrix", "Replay Indicator Matrix", None, "Runtime Validation Register", "ReplayIndicatorMatrixReport", "/api/v1/behavior/replay/indicator-matrix/current", ["matrix_indicator_count", "ready_rows", "proxy_rows", "output_hash"], "Behavior Replay Indicator Matrix", status_by_name),
        _panel("matrix_decision_readiness", "Matrix Decision Readiness", None, "Decision Readiness Register", "MatrixDecisionReadinessReport", "/api/v1/behavior/decision/readiness/current", ["readiness_action", "directional_bias", "agreement_score", "safety_score"], "Behavior Matrix Decision Readiness", status_by_name),
        _panel("trade_lifecycle_simulation", "Trade Lifecycle Simulation", 24, "Trade Lifecycle Tracking", "TradeLifecycleSimulationReport", "/api/v1/behavior/lifecycle/current", ["lifecycle_status", "trade_state_path", "outcome", "execution"], "Behavior Trade Lifecycle Simulation", status_by_name),
        _panel("lifecycle_scenario_comparison", "Lifecycle Scenario Comparison", 32, "Similar-Day Replay Engine", "TradeLifecycleScenarioComparisonReport", "/api/v1/behavior/lifecycle/compare/current", ["candidate_count", "blocked_count", "items", "gates"], "Behavior Lifecycle Scenario Comparison", status_by_name),
        _panel("lifecycle_evidence_drilldown", "Lifecycle Evidence Drilldown", 32, "Similar-Day Replay Engine", "LifecycleEvidenceDrilldownReport", "/api/v1/behavior/lifecycle/evidence/current", ["dominant_directional_driver", "dominant_safety_pressure", "items", "top_safety_pressures"], "Behavior Lifecycle Evidence Drilldown", status_by_name),
        _panel("tradeability_guidance", "Tradeability Guidance", 29, "No-Trade Intelligence", "TradeabilityGuidanceReport", "/api/v1/behavior/tradeability/current", ["tradeability_status", "next_safe_action", "promotion_blockers", "improvement_steps"], "Behavior Tradeability Guidance", status_by_name),
        _panel("safety_gates", "Safety Gates", 29, "No-Trade Intelligence", "BehaviorAnalysisResult", "/api/v1/behavior/analyze", ["safety_gates"], "Behavior No-Trade Intelligence", status_by_name),
        _panel("data_quality", "Data Quality", 1, "Data Quality Engine", "DataQualityReport", "/api/data/quality", ["lookback_years", "survivorship_bias", "look_ahead_leakage"], "Behavior Data Quality Engine", status_by_name),
        _panel("lookahead_guard", "Lookahead Guard Status", 2, "Lookahead-Bias Guard", "PointInTimeGuardResult", "/api/v1/behavior/guards/point-in-time", ["passed", "future_bar_blocked", "incomplete_candle_blocked"], "Behavior Point-In-Time Guard", status_by_name),
        _panel("timeframe_sync", "Timeframe Sync", 11, "Higher-Timeframe Confirmation", "TimeframeSyncResult", "/api/v1/behavior/timeframes/synchronize", ["aligned_timeframes", "blocked_timeframes"], "Behavior Timeframe Synchronization Engine", status_by_name),
        _panel("causal_whitelist", "Causal Feature Whitelist", 2, "Lookahead-Bias Guard", "CausalFeatureValidationResult", "/api/v1/behavior/features/causal-whitelist", ["allowed_features", "blocked_features"], "Behavior Causal Feature Whitelist", status_by_name),
        _panel("capability_manifest", "Capability Manifest", None, "Capability Register", "CapabilityManifest", "/api/system/features", ["capabilities", "status", "promotion_gates"], "CapabilityManifest", status_by_name),
    ]
    mock_count = sum(1 for panel in panels if panel.manifest_status == CapabilityStatus.MOCK)
    reserved_count = sum(1 for panel in panels if panel.manifest_status == CapabilityStatus.RESERVED)
    return BehaviorFrontendPanelMapResult(
        map_version=PANEL_MAP_VERSION,
        workspace="behavior",
        total_panels=len(panels),
        mock_panels=mock_count,
        reserved_panels=reserved_count,
        panels=panels,
        safety_invariants=[
            "Every panel must declare a backend endpoint and response contract.",
            "Reserved panels remain visible through CapabilityManifest instead of disappearing.",
            "Narrative and reason-tree panels are explanation-only and cannot execute orders.",
            "Offline or contract-failure states must render safe UI, never blank UI.",
        ],
    )


def _panel(
    panel_id: str,
    title: str,
    layer_index: int | None,
    layer_name: str,
    contract_name: str,
    endpoint: str,
    output_fields: list[str],
    capability_name: str,
    status_by_name: dict[str, CapabilityStatus],
    *,
    fallback_state: str = "mock",
    required: bool = True,
) -> BehaviorFrontendPanelMapItem:
    status = status_by_name.get(capability_name, CapabilityStatus.RESERVED)
    return BehaviorFrontendPanelMapItem(
        panel_id=panel_id,
        title=title,
        workspace="behavior",
        layer_index=layer_index,
        layer_name=layer_name,
        contract_name=contract_name,
        endpoint=endpoint,
        output_fields=output_fields,
        fallback_state=fallback_state,  # type: ignore[arg-type]
        capability_name=capability_name,
        manifest_status=status,
        required_for_mvp=required,
    )
