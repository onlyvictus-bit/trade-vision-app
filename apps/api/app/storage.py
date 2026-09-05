from __future__ import annotations

import json
import os
import sqlite3
import hashlib
import threading
from pathlib import Path
from typing import Any

from .models import (
    AuditEvent,
    AuditIntegrityReport,
    BehaviorAnalysisResult,
    BehaviorBenchmarkReport,
    BehaviorBenchmarkRun,
    BehaviorMemoryRecord,
    BehaviorReplayRecord,
    BehaviorSafetyReport,
    BehaviorScenarioCoverageReport,
    ConservativeOutcomeLabelResult,
    ReleaseEvidenceArtifact,
    ReleaseEvidenceBundle,
    CapabilityManifestItem,
    ExecutionSimulationResult,
    ExecutorTransportOutboxRecord,
    FeatureVersionRecord,
    FeatureSnapshotRecord,
    FailurePatternRecord,
    GoldenReplayFixture,
    IndicatorSignalHistoryRecord,
    IndicatorSignalHistorySummary,
    KillSwitchState,
    LearningTrustRecord,
    MarketEvent,
    MemoryQuarantineRecord,
    MockToReplayReleaseChecklist,
    NineCandleSetupRecord,
    AnalogIndexManifest,
    OutcomeHorizonLabel,
    OutcomeLabelResult,
    PointInTimeSnapshot,
    RequestLogRecord,
    ReleaseApprovalRecord,
    ReplayArchiveSummary,
    ReplaySnapshot,
    SessionMemoryProfile,
    StorageStatus,
    ObservabilityStatus,
    SimilarDayMatch,
    StockDNAProfile,
    WorkspaceLayout,
    now_iso,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "trade_vision_state.db"
DB_PATH = Path(os.environ.get("TRADEVISION_STATE_DB", str(DEFAULT_DB_PATH)))
SQLITE_BUSY_TIMEOUT_MS = 15_000
_MEMORY_CONN: sqlite3.Connection | None = None
_MEMORY_URI = "file:tradevision_state?mode=memory&cache=shared"
_INIT_LOCK = threading.RLock()
_AUDIT_LOCK = threading.RLock()
_AUDIT_HASH_BACKFILLED = False
_INITIALIZED_DB_TARGETS: set[str] = set()


def _active_db_target_key() -> str:
    raw_path = str(DB_PATH)
    if raw_path == ":memory:":
        return raw_path
    return str(Path(raw_path).resolve())


def _initialized_target_is_valid(target_key: str) -> bool:
    if target_key == ":memory:":
        return _MEMORY_CONN is not None
    return Path(target_key).exists()


def _configure_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def connect() -> sqlite3.Connection:
    global _MEMORY_CONN
    if str(DB_PATH) == ":memory:":
        if _MEMORY_CONN is None:
            _MEMORY_CONN = _configure_connection(
                sqlite3.connect(_MEMORY_URI, uri=True, check_same_thread=False, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)
            )
        return _configure_connection(
            sqlite3.connect(_MEMORY_URI, uri=True, check_same_thread=False, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)
        )
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _configure_connection(sqlite3.connect(DB_PATH, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # Some diagnostic/test environments mount an existing DB read-only.
        # Read paths should still work; write paths will surface their own errors.
        pass
    return conn


def init_db() -> None:
    target_key = _active_db_target_key()
    with _INIT_LOCK:
        if target_key in _INITIALIZED_DB_TARGETS and _initialized_target_is_valid(target_key):
            return
        conn = connect()
        try:
            conn.executescript(
                """
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT NOT NULL,
                mode TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_audit_events_time
                ON audit_events(timestamp DESC);

            CREATE TABLE IF NOT EXISTS kill_switch_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS replay_sessions (
                session_id TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                seed INTEGER NOT NULL,
                state TEXT NOT NULL,
                current_timestamp_ns INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS replay_events (
                session_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                event_json TEXT NOT NULL,
                PRIMARY KEY (session_id, sequence_number),
                FOREIGN KEY (session_id) REFERENCES replay_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS capability_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                capability_count INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS point_in_time_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                source_mode TEXT NOT NULL,
                seed INTEGER NOT NULL,
                as_of_timestamp_ns INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                immutable INTEGER NOT NULL DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_point_in_time_symbol_time
                ON point_in_time_snapshots(symbol, as_of_timestamp_ns DESC);

            CREATE TABLE IF NOT EXISTS feature_versions (
                feature_hash TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                pipeline_version TEXT NOT NULL,
                source_commit TEXT NOT NULL,
                created_at TEXT NOT NULL,
                input_snapshot_id TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                FOREIGN KEY (input_snapshot_id) REFERENCES point_in_time_snapshots(snapshot_id)
            );

            CREATE INDEX IF NOT EXISTS idx_feature_versions_snapshot
                ON feature_versions(input_snapshot_id);

            CREATE TABLE IF NOT EXISTS behavior_feature_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                decision_time_ns INTEGER NOT NULL,
                source_snapshot_hash TEXT NOT NULL,
                feature_version TEXT NOT NULL,
                indicator_registry_version TEXT NOT NULL,
                storage_uri TEXT NOT NULL,
                storage_format TEXT NOT NULL,
                row_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                adjusted_price_version TEXT NOT NULL,
                feature_count INTEGER NOT NULL,
                unavailable_feature_count INTEGER NOT NULL,
                proxy_excluded_count INTEGER NOT NULL,
                blocked_excluded_count INTEGER NOT NULL,
                lineage_json TEXT NOT NULL,
                UNIQUE(symbol, timeframe, decision_time_ns, feature_version, adjusted_price_version)
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_feature_snapshot_lookup
                ON behavior_feature_snapshots(symbol, timeframe, decision_time_ns);

            CREATE INDEX IF NOT EXISTS idx_behavior_feature_snapshot_source
                ON behavior_feature_snapshots(source_snapshot_hash, feature_version);

            CREATE TABLE IF NOT EXISTS indicator_result_cache (
                cache_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source_snapshot_hash TEXT NOT NULL,
                source_snapshot_id TEXT,
                candle_start_time TEXT,
                candle_end_time TEXT,
                candle_count INTEGER NOT NULL,
                indicator_registry_version TEXT NOT NULL,
                feature_manifest_version TEXT NOT NULL,
                promoted_indicator_hash TEXT NOT NULL,
                indicator_id TEXT NOT NULL,
                runtime_status TEXT NOT NULL,
                output_present INTEGER NOT NULL,
                used_for_probability INTEGER NOT NULL DEFAULT 0,
                trade_allowed INTEGER NOT NULL DEFAULT 0,
                order_routing_enabled INTEGER NOT NULL DEFAULT 0,
                live_trading_blocked INTEGER NOT NULL DEFAULT 1,
                artifact_uri TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_indicator_result_cache_snapshot
                ON indicator_result_cache(symbol, timeframe, source_snapshot_hash);

            CREATE INDEX IF NOT EXISTS idx_indicator_result_cache_indicator
                ON indicator_result_cache(symbol, timeframe, indicator_id);

            CREATE INDEX IF NOT EXISTS idx_indicator_result_cache_versions
                ON indicator_result_cache(indicator_registry_version, feature_manifest_version);

            CREATE INDEX IF NOT EXISTS idx_indicator_result_cache_created
                ON indicator_result_cache(created_at DESC);

            CREATE TABLE IF NOT EXISTS indicator_signal_history (
                history_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                indicator_id TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_direction TEXT NOT NULL,
                signal_time_ns INTEGER NOT NULL,
                decision_time_ns INTEGER NOT NULL,
                session_phase TEXT NOT NULL,
                regime_id TEXT NOT NULL,
                source_snapshot_id TEXT,
                source_snapshot_hash TEXT,
                feature_manifest_version TEXT NOT NULL,
                indicator_registry_version TEXT NOT NULL,
                label_status TEXT NOT NULL,
                outcome_label TEXT NOT NULL,
                counted_in_reliability INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                history_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_indicator_signal_history_lookup
                ON indicator_signal_history(symbol, timeframe, indicator_id, signal_time_ns DESC);

            CREATE INDEX IF NOT EXISTS idx_indicator_signal_history_regime
                ON indicator_signal_history(symbol, timeframe, indicator_id, regime_id, session_phase);

            CREATE INDEX IF NOT EXISTS idx_indicator_signal_history_manifest
                ON indicator_signal_history(feature_manifest_version, indicator_registry_version);

            CREATE INDEX IF NOT EXISTS idx_indicator_signal_history_label
                ON indicator_signal_history(label_status, outcome_label, counted_in_reliability);

            CREATE TABLE IF NOT EXISTS workspace_layouts (
                workspace_id TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                layout_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS request_logs (
                request_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                decision_id TEXT,
                timestamp TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                actor_id TEXT NOT NULL,
                role TEXT NOT NULL,
                mode TEXT NOT NULL,
                error_code TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_request_logs_time
                ON request_logs(timestamp DESC);

            CREATE INDEX IF NOT EXISTS idx_request_logs_path
                ON request_logs(path, timestamp DESC);

            CREATE TABLE IF NOT EXISTS behavior_analysis_results (
                run_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                decision_time TEXT NOT NULL,
                model_version TEXT NOT NULL,
                replay_snapshot_id TEXT,
                result_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_analysis_symbol_time
                ON behavior_analysis_results(symbol, decision_time DESC);

            CREATE TABLE IF NOT EXISTS behavior_layer_results (
                run_id TEXT NOT NULL,
                layer_name TEXT NOT NULL,
                contract_name TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT NOT NULL,
                PRIMARY KEY (run_id, contract_name)
            );

            CREATE TABLE IF NOT EXISTS stock_dna_profiles (
                symbol TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_memory_profiles (
                symbol TEXT NOT NULL,
                session_phase TEXT NOT NULL,
                profile_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (symbol, session_phase)
            );

            CREATE TABLE IF NOT EXISTS similar_day_matches (
                match_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                similar_day_id TEXT NOT NULL,
                similarity_score_pct REAL NOT NULL,
                outcome_label TEXT NOT NULL,
                match_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_similar_day_matches_symbol
                ON similar_day_matches(symbol, similarity_score_pct DESC);

            CREATE TABLE IF NOT EXISTS pattern_memory_records (
                memory_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                pattern_id TEXT NOT NULL,
                market_state TEXT NOT NULL,
                session_phase TEXT NOT NULL,
                outcome_label TEXT NOT NULL,
                similarity_group TEXT NOT NULL,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_pattern_memory_symbol_date
                ON pattern_memory_records(symbol, trade_date DESC);

            CREATE INDEX IF NOT EXISTS idx_pattern_memory_pattern
                ON pattern_memory_records(pattern_id, market_state, session_phase);

            CREATE TABLE IF NOT EXISTS outcome_labels (
                outcome_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                outcome_label TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conservative_outcome_labels (
                run_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                outcome_label TEXT NOT NULL,
                net_return_after_costs REAL NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_conservative_outcome_labels_symbol
                ON conservative_outcome_labels(symbol, outcome_label);

            CREATE TABLE IF NOT EXISTS failure_patterns (
                failure_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                pattern_id TEXT NOT NULL,
                failure_reason TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS learning_trust_table (
                trust_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                pattern_id TEXT NOT NULL,
                trust_score REAL NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trade_lifecycle (
                lifecycle_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                trade_state TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS risk_sizing_results (
                risk_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS execution_simulations (
                simulation_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS nine_candle_setups (
                setup_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decision_time TEXT,
                source_snapshot_id TEXT,
                evidence_packet_id TEXT,
                evidence_packet_hash TEXT,
                feature_manifest_version TEXT NOT NULL,
                label_status TEXT NOT NULL,
                setup_hash TEXT NOT NULL,
                setup_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_nine_candle_setups_symbol_time
                ON nine_candle_setups(symbol, timeframe, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_nine_candle_setups_manifest
                ON nine_candle_setups(feature_manifest_version, label_status);

            CREATE TABLE IF NOT EXISTS nine_candle_outcome_labels (
                label_id TEXT PRIMARY KEY,
                setup_id TEXT NOT NULL,
                horizon_candles INTEGER NOT NULL,
                label_status TEXT NOT NULL,
                outcome_label TEXT NOT NULL,
                target_first INTEGER NOT NULL,
                stop_first INTEGER NOT NULL,
                fakeout INTEGER NOT NULL,
                label_hash TEXT NOT NULL,
                label_json TEXT NOT NULL,
                FOREIGN KEY (setup_id) REFERENCES nine_candle_setups(setup_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_nine_candle_labels_setup
                ON nine_candle_outcome_labels(setup_id, horizon_candles);

            CREATE INDEX IF NOT EXISTS idx_nine_candle_labels_outcome
                ON nine_candle_outcome_labels(outcome_label, horizon_candles);

            CREATE TABLE IF NOT EXISTS nine_candle_analog_index_manifests (
                manifest_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                index_version TEXT NOT NULL,
                feature_manifest_version TEXT NOT NULL,
                index_hash TEXT NOT NULL,
                artifact_uri TEXT,
                artifact_sha256 TEXT,
                artifact_size_bytes INTEGER NOT NULL DEFAULT 0,
                artifact_verified INTEGER NOT NULL DEFAULT 0,
                record_count INTEGER NOT NULL,
                vector_dimension INTEGER NOT NULL,
                active INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                active_pointer_swapped_at TEXT NOT NULL,
                manifest_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_nine_candle_analog_index_active
                ON nine_candle_analog_index_manifests(symbol, timeframe, active);

            CREATE INDEX IF NOT EXISTS idx_nine_candle_analog_index_hash
                ON nine_candle_analog_index_manifests(index_hash);

            CREATE TABLE IF NOT EXISTS benchmark_runs (
                run_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                run_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_benchmark_runs_symbol
                ON benchmark_runs(symbol, created_at DESC);

            CREATE TABLE IF NOT EXISTS behavior_benchmark_reports (
                report_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                promotion_allowed INTEGER NOT NULL,
                report_hash TEXT NOT NULL,
                report_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_benchmark_reports_symbol_time
                ON behavior_benchmark_reports(symbol, created_at DESC);

            CREATE TABLE IF NOT EXISTS behavior_scenario_coverage_reports (
                coverage_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                benchmark_report_id TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                coverage_score_pct REAL NOT NULL,
                coverage_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_scenario_coverage_symbol_time
                ON behavior_scenario_coverage_reports(symbol, generated_at DESC);

            CREATE INDEX IF NOT EXISTS idx_behavior_scenario_coverage_benchmark
                ON behavior_scenario_coverage_reports(benchmark_report_id);

            CREATE TABLE IF NOT EXISTS release_checklists (
                checklist_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                target_mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                release_allowed INTEGER NOT NULL,
                checklist_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_release_checklists_symbol_time
                ON release_checklists(symbol, created_at DESC);

            CREATE TABLE IF NOT EXISTS release_approvals (
                approval_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                target_mode TEXT NOT NULL,
                benchmark_report_id TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                approval_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_release_approvals_symbol_status
                ON release_approvals(symbol, status, requested_at DESC);

            CREATE INDEX IF NOT EXISTS idx_release_approvals_report
                ON release_approvals(benchmark_report_id, status);

            CREATE TABLE IF NOT EXISTS release_evidence_bundles (
                bundle_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                target_mode TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                benchmark_report_id TEXT NOT NULL,
                bundle_hash TEXT NOT NULL,
                bundle_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_release_evidence_symbol_time
                ON release_evidence_bundles(symbol, generated_at DESC);

            CREATE INDEX IF NOT EXISTS idx_release_evidence_report
                ON release_evidence_bundles(benchmark_report_id);

            CREATE TABLE IF NOT EXISTS release_evidence_artifacts (
                artifact_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                target_mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                bundle_id TEXT NOT NULL,
                bundle_hash TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                artifact_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_release_artifacts_symbol_time
                ON release_evidence_artifacts(symbol, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_release_artifacts_bundle
                ON release_evidence_artifacts(bundle_id);

            CREATE TABLE IF NOT EXISTS executor_transport_outbox (
                delivery_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL,
                max_attempts INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                next_attempt_at TEXT,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_executor_outbox_status_time
                ON executor_transport_outbox(status, updated_at DESC);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_executor_outbox_idempotency
                ON executor_transport_outbox(idempotency_key);

            CREATE TABLE IF NOT EXISTS executor_transport_traces (
                trace_id TEXT PRIMARY KEY,
                delivery_id TEXT NOT NULL,
                event_time TEXT NOT NULL,
                event_type TEXT NOT NULL,
                trace_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_executor_transport_traces_delivery_time
                ON executor_transport_traces(delivery_id, event_time DESC);

            CREATE TABLE IF NOT EXISTS transport_health_samples (
                sample_id TEXT PRIMARY KEY,
                sampled_at TEXT NOT NULL,
                sample_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_transport_health_samples_time
                ON transport_health_samples(sampled_at DESC);

            CREATE TABLE IF NOT EXISTS transport_incidents (
                incident_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                incident_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_transport_incidents_status_time
                ON transport_incidents(status, updated_at DESC);

            CREATE TABLE IF NOT EXISTS walk_forward_runs (
                run_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drift_events (
                drift_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ood_events (
                ood_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reality_gap_events (
                gap_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS behavior_safety_reports (
                report_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                promotion_allowed INTEGER NOT NULL,
                memory_quarantine_required INTEGER NOT NULL,
                confidence_blocked INTEGER NOT NULL,
                reality_gap_alert INTEGER NOT NULL,
                report_hash TEXT NOT NULL,
                report_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_safety_reports_symbol_time
                ON behavior_safety_reports(symbol, created_at DESC);

            CREATE TABLE IF NOT EXISTS memory_quarantine_records (
                quarantine_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                source_report_id TEXT,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memory_quarantine_symbol_status
                ON memory_quarantine_records(symbol, status, created_at DESC);

            CREATE TABLE IF NOT EXISTS golden_replay_fixtures (
                fixture_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                seed INTEGER NOT NULL,
                fixture_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS openalgo_report_imports (
                report_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                report_hash TEXT NOT NULL,
                report_type TEXT NOT NULL,
                report_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_openalgo_report_imports_symbol_time
                ON openalgo_report_imports(symbol, imported_at DESC);

            CREATE TABLE IF NOT EXISTS trendforge_intakes (
                intake_id TEXT PRIMARY KEY,
                packet_id TEXT NOT NULL UNIQUE,
                received_at TEXT NOT NULL,
                evidence_as_of TEXT NOT NULL,
                intake_state TEXT NOT NULL,
                candidate_count INTEGER NOT NULL,
                review_candidate_count INTEGER NOT NULL,
                payload_sha256 TEXT NOT NULL,
                intake_hash TEXT NOT NULL,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_trendforge_intakes_time
                ON trendforge_intakes(received_at DESC);

            CREATE TABLE IF NOT EXISTS orb_timing_runs (
                run_id TEXT PRIMARY KEY,
                request_hash TEXT NOT NULL UNIQUE,
                result_version TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                symbols_completed INTEGER NOT NULL,
                symbols_failed INTEGER NOT NULL,
                row_count INTEGER NOT NULL,
                deterministic_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                result_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_orb_timing_runs_time
                ON orb_timing_runs(created_at DESC);

            CREATE TABLE IF NOT EXISTS orb_timing_rows (
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                clock_window TEXT NOT NULL,
                strategy_family TEXT,
                reward_risk_ratio REAL,
                trade_count INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                profit_factor REAL NOT NULL,
                net_r REAL NOT NULL,
                consistency REAL NOT NULL,
                max_drawdown_r REAL NOT NULL,
                composite_score REAL NOT NULL,
                minimum_trades_pass INTEGER NOT NULL,
                no_future_leakage INTEGER NOT NULL,
                PRIMARY KEY (run_id, symbol, clock_window)
            );

            CREATE INDEX IF NOT EXISTS idx_orb_timing_rows_symbol
                ON orb_timing_rows(symbol);

            CREATE TABLE IF NOT EXISTS jarvis_usefulness_records (
                usefulness_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                created_at TEXT NOT NULL,
                packet_id TEXT NOT NULL,
                final_action TEXT NOT NULL,
                usefulness_score REAL NOT NULL,
                record_hash TEXT NOT NULL,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jarvis_usefulness_symbol_time
                ON jarvis_usefulness_records(symbol, created_at DESC);

            CREATE TABLE IF NOT EXISTS external_ai_review_records (
                review_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                intake_status TEXT NOT NULL,
                display_allowed INTEGER NOT NULL,
                review_hash TEXT NOT NULL,
                evidence_packet_hash TEXT NOT NULL,
                candidate_response_hash TEXT NOT NULL,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_external_ai_reviews_symbol_time
                ON external_ai_review_records(symbol, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_external_ai_reviews_source_status
                ON external_ai_review_records(source, intake_status, created_at DESC);

            CREATE TABLE IF NOT EXISTS jarvis_ai_comparison_records (
                comparison_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                agreement_state TEXT NOT NULL,
                safe_final_action TEXT NOT NULL,
                evidence_packet_hash TEXT NOT NULL,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jarvis_ai_comparisons_symbol_time
                ON jarvis_ai_comparison_records(symbol, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_jarvis_ai_comparisons_state_time
                ON jarvis_ai_comparison_records(agreement_state, created_at DESC);

            CREATE TABLE IF NOT EXISTS correction_response_records (
                validation_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                display_status TEXT NOT NULL,
                accepted_for_display INTEGER NOT NULL,
                validation_hash TEXT NOT NULL,
                correction_packet_hash TEXT NOT NULL,
                candidate_response_hash TEXT NOT NULL,
                record_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_correction_responses_symbol_time
                ON correction_response_records(symbol, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_correction_responses_source_status
                ON correction_response_records(source, display_status, created_at DESC);

            CREATE TABLE IF NOT EXISTS decision_audit_logs (
                audit_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
            )
            _ensure_audit_hash_columns(conn)
            _ensure_analog_index_manifest_columns(conn)
            _backfill_audit_hashes(conn)
            conn.commit()
        finally:
            conn.close()
        _INITIALIZED_DB_TARGETS.add(target_key)


def _ensure_audit_hash_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(audit_events)").fetchall()}
    if "sequence_number" not in columns:
        conn.execute("ALTER TABLE audit_events ADD COLUMN sequence_number INTEGER")
    if "previous_hash" not in columns:
        conn.execute("ALTER TABLE audit_events ADD COLUMN previous_hash TEXT")
    if "record_hash" not in columns:
        conn.execute("ALTER TABLE audit_events ADD COLUMN record_hash TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_sequence ON audit_events(sequence_number ASC)")


def _ensure_analog_index_manifest_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(nine_candle_analog_index_manifests)").fetchall()}
    if "artifact_uri" not in columns:
        conn.execute("ALTER TABLE nine_candle_analog_index_manifests ADD COLUMN artifact_uri TEXT")
    if "artifact_sha256" not in columns:
        conn.execute("ALTER TABLE nine_candle_analog_index_manifests ADD COLUMN artifact_sha256 TEXT")
    if "artifact_size_bytes" not in columns:
        conn.execute("ALTER TABLE nine_candle_analog_index_manifests ADD COLUMN artifact_size_bytes INTEGER NOT NULL DEFAULT 0")
    if "artifact_verified" not in columns:
        conn.execute("ALTER TABLE nine_candle_analog_index_manifests ADD COLUMN artifact_verified INTEGER NOT NULL DEFAULT 0")


def _audit_record_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_openalgo_report_import(report: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO openalgo_report_imports
            (report_id, symbol, imported_at, report_hash, report_type, report_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report["report_id"],
                report["symbol"],
                report["imported_at"],
                report["report_hash"],
                report["report_type"],
                json.dumps(report, sort_keys=True),
            ),
        )
    return report


def load_latest_openalgo_report_import(symbol: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT report_json
            FROM openalgo_report_imports
            WHERE symbol = ?
            ORDER BY imported_at DESC
            LIMIT 1
            """,
            (symbol.upper(),),
        ).fetchone()
    return json.loads(row["report_json"]) if row else None


def list_openalgo_report_imports(symbol: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
    init_db()
    bounded_limit = max(1, min(limit, 250))
    if symbol:
        query = """
            SELECT report_json
            FROM openalgo_report_imports
            WHERE symbol = ?
            ORDER BY imported_at DESC
            LIMIT ?
        """
        params: tuple[Any, ...] = (symbol.upper(), bounded_limit)
    else:
        query = """
            SELECT report_json
            FROM openalgo_report_imports
            ORDER BY imported_at DESC
            LIMIT ?
        """
        params = (bounded_limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [json.loads(row["report_json"]) for row in rows]


def save_trendforge_intake(record: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO trendforge_intakes
            (intake_id, packet_id, received_at, evidence_as_of, intake_state,
             candidate_count, review_candidate_count, payload_sha256,
             intake_hash, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(packet_id) DO NOTHING
            """,
            (
                record["intakeId"],
                record["packetId"],
                record["receivedAt"],
                record["evidenceAsOf"],
                record["intakeState"],
                record["candidateCount"],
                record["reviewCandidateCount"],
                record["payloadSha256"],
                record["intakeHash"],
                json.dumps(record, sort_keys=True),
            ),
        )
    return record


def list_trendforge_intakes(limit: int = 25) -> list[dict[str, Any]]:
    init_db()
    bounded_limit = max(1, min(limit, 250))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT record_json FROM trendforge_intakes
            ORDER BY received_at DESC LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def save_orb_timing_run(result: dict[str, Any]) -> dict[str, Any]:
    """Persist one v1.97 ORB timing research result (run header + window rows). Idempotent by run_id."""
    init_db()
    created_at = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO orb_timing_runs
            (run_id, request_hash, result_version, timeframe, symbols_completed,
             symbols_failed, row_count, deterministic_hash, created_at, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO NOTHING
            """,
            (
                result["run_id"],
                result["request_hash"],
                result["result_version"],
                result["timeframe"],
                len(result.get("symbols_completed") or []),
                len(result.get("symbols_failed") or {}),
                len(result.get("rows") or []),
                result["deterministic_hash"],
                created_at,
                json.dumps(result, sort_keys=True),
            ),
        )
        for row in result.get("rows") or []:
            window = row.get("clock_window") or ["", ""]
            window_text = f"{window[0]}-{window[1]}" if isinstance(window, list) else str(window)
            conn.execute(
                """
                INSERT OR IGNORE INTO orb_timing_rows
                (run_id, symbol, clock_window, strategy_family, reward_risk_ratio,
                 trade_count, win_rate, profit_factor, net_r, consistency,
                 max_drawdown_r, composite_score, minimum_trades_pass, no_future_leakage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["run_id"],
                    row["symbol"],
                    window_text,
                    row.get("strategy_family"),
                    row.get("reward_risk_ratio"),
                    int(row.get("trade_count") or 0),
                    float(row.get("win_rate") or 0.0),
                    float(row.get("profit_factor") or 0.0),
                    float(row.get("net_r") or 0.0),
                    float(row.get("consistency") or 0.0),
                    float(row.get("max_drawdown_r") or 0.0),
                    float(row.get("composite_score") or 0.0),
                    1 if row.get("minimum_trades_pass") else 0,
                    1 if row.get("no_future_leakage") else 0,
                ),
            )
    return result


def list_orb_timing_runs(limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    bounded_limit = max(1, min(limit, 200))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT result_json FROM orb_timing_runs
            ORDER BY created_at DESC LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
    return [json.loads(row["result_json"]) for row in rows]


def get_orb_timing_run(run_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT result_json FROM orb_timing_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    return None if row is None else json.loads(row["result_json"])


def save_jarvis_usefulness_record(record: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO jarvis_usefulness_records
            (usefulness_id, symbol, timeframe, created_at, packet_id, final_action, usefulness_score, record_hash, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["usefulness_id"],
                record["symbol"],
                record["timeframe"],
                record["created_at"],
                record["packet_id"],
                record["final_action"],
                record["usefulness_score"],
                record["record_hash"],
                json.dumps(record, sort_keys=True),
            ),
        )
    return record


def list_jarvis_usefulness_records(symbol: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
    init_db()
    bounded_limit = max(1, min(limit, 250))
    if symbol:
        query = """
            SELECT record_json
            FROM jarvis_usefulness_records
            WHERE symbol = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params: tuple[Any, ...] = (symbol.upper(), bounded_limit)
    else:
        query = """
            SELECT record_json
            FROM jarvis_usefulness_records
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = (bounded_limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def save_external_ai_review_record(record: dict[str, Any]) -> dict[str, Any]:
    init_db()
    symbol = str(record.get("symbol") or record.get("sanitized_candidate_response", {}).get("symbol") or "UNKNOWN").upper()
    created_at = record.get("created_at") or now_iso()
    review_hash = record.get("review_hash") or _json_hash(record)
    review_id = record.get("review_id") or f"external-ai-review:{review_hash[:24]}"
    enriched = {
        **record,
        "review_id": review_id,
        "symbol": symbol,
        "created_at": created_at,
        "review_hash": review_hash,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO external_ai_review_records
            (review_id, symbol, source, created_at, intake_status, display_allowed,
             review_hash, evidence_packet_hash, candidate_response_hash, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                enriched["review_id"],
                enriched["symbol"],
                enriched.get("source", "manual"),
                enriched["created_at"],
                enriched.get("intake_status", "unknown"),
                1 if enriched.get("display_allowed") else 0,
                enriched["review_hash"],
                enriched.get("evidence_packet_hash", ""),
                enriched.get("candidate_response_hash", ""),
                json.dumps(enriched, sort_keys=True),
            ),
        )
    return enriched


def list_external_ai_review_records(symbol: str | None = None, source: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
    init_db()
    bounded_limit = max(1, min(limit, 250))
    clauses: list[str] = []
    params: list[Any] = []
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.upper())
    if source:
        clauses.append("source = ?")
        params.append(source.lower())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT record_json
        FROM external_ai_review_records
        {where}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(bounded_limit)
    with connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def external_ai_review_summary(symbol: str | None = None, limit: int = 100) -> dict[str, Any]:
    records = list_external_ai_review_records(symbol=symbol, limit=limit)
    accepted = [record for record in records if record.get("display_allowed")]
    rejected = [record for record in records if not record.get("display_allowed")]
    return {
        "summary_version": "jarvis-external-ai-review-audit.v1.06",
        "symbol": symbol.upper() if symbol else None,
        "record_count": len(records),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "sources": sorted({record.get("source", "manual") for record in records}),
        "latest_review_id": records[0]["review_id"] if records else None,
        "latest_status": records[0]["intake_status"] if records else "none",
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def save_jarvis_ai_comparison_record(record: dict[str, Any]) -> dict[str, Any]:
    init_db()
    symbol = str(record.get("symbol") or "UNKNOWN").upper()
    created_at = record.get("created_at") or now_iso()
    comparison_hash = record.get("comparison_hash") or _json_hash(record)
    comparison_id = record.get("comparison_id") or f"jarvis-ai-comparison:{comparison_hash[:24]}"
    agreement_state = str(record.get("agreement_matrix", {}).get("agreement_state") or record.get("agreement_state") or "UNKNOWN")
    safe_final_action = str(record.get("safe_final_action") or "TRADE_VISION_ONLY")
    evidence_packet_hash = str(record.get("evidence_packet_hash") or "")
    enriched = {
        **record,
        "comparison_id": comparison_id,
        "symbol": symbol,
        "created_at": created_at,
        "comparison_hash": comparison_hash,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO jarvis_ai_comparison_records
            (comparison_id, symbol, created_at, agreement_state, safe_final_action,
             evidence_packet_hash, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                enriched["comparison_id"],
                enriched["symbol"],
                enriched["created_at"],
                agreement_state,
                safe_final_action,
                evidence_packet_hash,
                json.dumps(enriched, sort_keys=True),
            ),
        )
    return enriched


def list_jarvis_ai_comparison_records(symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    bounded_limit = max(1, min(limit, 250))
    params: list[Any] = []
    where = ""
    if symbol:
        where = "WHERE symbol = ?"
        params.append(symbol.upper())
    query = f"""
        SELECT record_json
        FROM jarvis_ai_comparison_records
        {where}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(bounded_limit)
    with connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def save_correction_response_record(record: dict[str, Any]) -> dict[str, Any]:
    init_db()
    candidate = record.get("sanitized_candidate_response", {}) if isinstance(record.get("sanitized_candidate_response"), dict) else {}
    symbol = str(record.get("symbol") or candidate.get("symbol") or "UNKNOWN").upper()
    created_at = record.get("created_at") or record.get("validated_at") or now_iso()
    validation_hash = record.get("validation_hash") or _json_hash(record)
    validation_id = record.get("validation_id") or f"correction-response:{validation_hash[:24]}"
    enriched = {
        **record,
        "validation_id": validation_id,
        "symbol": symbol,
        "created_at": created_at,
        "validation_hash": validation_hash,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO correction_response_records
            (validation_id, symbol, source, created_at, display_status, accepted_for_display,
             validation_hash, correction_packet_hash, candidate_response_hash, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                enriched["validation_id"],
                enriched["symbol"],
                enriched.get("source", "manual"),
                enriched["created_at"],
                enriched.get("display_status", "unknown"),
                1 if enriched.get("accepted_for_correction_display") else 0,
                enriched["validation_hash"],
                enriched.get("correction_packet_hash", ""),
                enriched.get("candidate_response_hash", ""),
                json.dumps(enriched, sort_keys=True),
            ),
        )
    return enriched


def list_correction_response_records(symbol: str | None = None, source: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
    init_db()
    bounded_limit = max(1, min(limit, 250))
    clauses: list[str] = []
    params: list[Any] = []
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.upper())
    if source:
        clauses.append("source = ?")
        params.append(source.lower())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT record_json
        FROM correction_response_records
        {where}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(bounded_limit)
    with connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def correction_response_summary(symbol: str | None = None, limit: int = 100) -> dict[str, Any]:
    records = list_correction_response_records(symbol=symbol, limit=limit)
    accepted = [record for record in records if record.get("accepted_for_correction_display")]
    rejected = [record for record in records if not record.get("accepted_for_correction_display")]
    return {
        "summary_version": "jarvis-correction-response-audit.v1.12",
        "symbol": symbol.upper() if symbol else None,
        "record_count": len(records),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "sources": sorted({record.get("source", "manual") for record in records}),
        "latest_validation_id": records[0]["validation_id"] if records else None,
        "latest_status": records[0]["display_status"] if records else "none",
        "latest_packet_hash": records[0].get("correction_packet_hash") if records else None,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_export_to_openalgo": False,
    }


def save_nine_candle_setup(record: NineCandleSetupRecord) -> NineCandleSetupRecord:
    init_db()
    payload = record.model_dump(mode="json")
    setup_hash = record.setup_hash or _json_hash({key: value for key, value in payload.items() if key != "setup_hash"})
    enriched = record.model_copy(update={"setup_hash": setup_hash})
    payload = enriched.model_dump(mode="json")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO nine_candle_setups
            (setup_id, symbol, timeframe, created_at, decision_time, source_snapshot_id,
             evidence_packet_id, evidence_packet_hash, feature_manifest_version, label_status,
             setup_hash, setup_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(setup_id) DO UPDATE SET
                created_at = excluded.created_at,
                decision_time = excluded.decision_time,
                source_snapshot_id = excluded.source_snapshot_id,
                evidence_packet_id = excluded.evidence_packet_id,
                evidence_packet_hash = excluded.evidence_packet_hash,
                feature_manifest_version = excluded.feature_manifest_version,
                label_status = excluded.label_status,
                setup_hash = excluded.setup_hash,
                setup_json = excluded.setup_json
            """,
            (
                enriched.setup_id,
                enriched.symbol,
                enriched.timeframe,
                enriched.created_at,
                enriched.decision_time,
                enriched.source_snapshot_id,
                enriched.evidence_packet_id,
                enriched.evidence_packet_hash,
                enriched.feature_manifest_version,
                enriched.label_status,
                enriched.setup_hash,
                json.dumps(payload, sort_keys=True),
            ),
        )
    return enriched


def save_nine_candle_outcome_labels(setup_id: str, labels: list[OutcomeHorizonLabel]) -> list[OutcomeHorizonLabel]:
    init_db()
    enriched: list[OutcomeHorizonLabel] = []
    for label in labels:
        payload = label.model_dump(mode="json")
        label_hash = label.label_hash or _json_hash({key: value for key, value in payload.items() if key != "label_hash"})
        enriched.append(label.model_copy(update={"setup_id": setup_id, "label_hash": label_hash}))
    with connect() as conn:
        setup_row = conn.execute(
            "SELECT setup_json FROM nine_candle_setups WHERE setup_id = ?",
            (setup_id,),
        ).fetchone()
        if setup_row is None:
            placeholder = _placeholder_nine_candle_setup(setup_id)
            conn.execute(
                """
                INSERT INTO nine_candle_setups
                (setup_id, symbol, timeframe, created_at, decision_time, source_snapshot_id,
                 evidence_packet_id, evidence_packet_hash, feature_manifest_version, label_status,
                 setup_hash, setup_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    placeholder["setup_id"],
                    placeholder["symbol"],
                    placeholder["timeframe"],
                    placeholder["created_at"],
                    placeholder["decision_time"],
                    placeholder["source_snapshot_id"],
                    placeholder["evidence_packet_id"],
                    placeholder["evidence_packet_hash"],
                    placeholder["feature_manifest_version"],
                    placeholder["label_status"],
                    placeholder["setup_hash"],
                    json.dumps(placeholder, sort_keys=True),
                ),
            )
        for label in enriched:
            label_id = f"{setup_id}:H{label.horizon_candles}"
            conn.execute(
                """
                INSERT INTO nine_candle_outcome_labels
                (label_id, setup_id, horizon_candles, label_status, outcome_label,
                 target_first, stop_first, fakeout, label_hash, label_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(label_id) DO UPDATE SET
                    label_status = excluded.label_status,
                    outcome_label = excluded.outcome_label,
                    target_first = excluded.target_first,
                    stop_first = excluded.stop_first,
                    fakeout = excluded.fakeout,
                    label_hash = excluded.label_hash,
                    label_json = excluded.label_json
                """,
                (
                    label_id,
                    setup_id,
                    label.horizon_candles,
                    label.label_status,
                    label.outcome_label,
                    1 if label.target_first else 0,
                    1 if label.stop_first else 0,
                    1 if label.fakeout else 0,
                    label.label_hash,
                    label.model_dump_json(),
                ),
            )
        setup_row = conn.execute(
            "SELECT setup_json FROM nine_candle_setups WHERE setup_id = ?",
            (setup_id,),
        ).fetchone()
        if setup_row is not None:
            setup_payload = json.loads(setup_row["setup_json"])
            setup_payload["label_status"] = "complete"
            setup_payload["label_count"] = len(enriched)
            conn.execute(
                """
                UPDATE nine_candle_setups
                SET label_status = 'complete', setup_json = ?
                WHERE setup_id = ?
                """,
                (json.dumps(setup_payload, sort_keys=True), setup_id),
            )
    return enriched


def _placeholder_nine_candle_setup(setup_id: str) -> dict[str, Any]:
    created_at = now_iso()
    payload = {
        "setup_id": setup_id,
        "symbol": "UNKNOWN",
        "timeframe": "unknown",
        "decision_time": created_at,
        "source_snapshot_id": "label-first-placeholder",
        "evidence_packet_id": None,
        "evidence_packet_hash": None,
        "session_phase": "unknown",
        "regime_id": "unknown",
        "feature_manifest_version": "nine-candle-feature-manifest.v1",
        "entry_zone": [],
        "stop": 0.0,
        "target": 0.0,
        "invalidation": 0.0,
        "data_quality": 0.0,
        "created_at": created_at,
        "label_status": "pending",
        "setup_hash": None,
        "label_count": 0,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    payload["setup_hash"] = _json_hash({key: value for key, value in payload.items() if key != "setup_hash"})
    return payload


def load_nine_candle_setup(setup_id: str) -> NineCandleSetupRecord | None:
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT setup_json FROM nine_candle_setups WHERE setup_id = ?",
            (setup_id,),
        ).fetchone()
    if row is None:
        return None
    return NineCandleSetupRecord.model_validate_json(row["setup_json"])


def list_nine_candle_setups(symbol: str | None = None, timeframe: str | None = None, limit: int = 25) -> list[NineCandleSetupRecord]:
    init_db()
    bounded_limit = max(1, min(limit, 250))
    clauses: list[str] = []
    params: list[Any] = []
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.upper())
    if timeframe:
        clauses.append("timeframe = ?")
        params.append(timeframe)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT setup_json
        FROM nine_candle_setups
        {where}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(bounded_limit)
    with connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [NineCandleSetupRecord.model_validate_json(row["setup_json"]) for row in rows]


def list_nine_candle_outcome_labels(setup_id: str) -> list[OutcomeHorizonLabel]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT label_json
            FROM nine_candle_outcome_labels
            WHERE setup_id = ?
            ORDER BY horizon_candles ASC
            """,
            (setup_id,),
        ).fetchall()
    return [OutcomeHorizonLabel.model_validate_json(row["label_json"]) for row in rows]


def nine_candle_memory_summary(symbol: str | None = None, timeframe: str | None = None, limit: int = 25) -> dict[str, Any]:
    setups = list_nine_candle_setups(symbol=symbol, timeframe=timeframe, limit=limit)
    labels_by_setup = {setup.setup_id: list_nine_candle_outcome_labels(setup.setup_id) for setup in setups}
    complete = [setup for setup in setups if labels_by_setup.get(setup.setup_id)]
    pending = [setup for setup in setups if not labels_by_setup.get(setup.setup_id)]
    return {
        "memory_version": "9c-setup-outcome-memory.v1",
        "symbol": symbol.upper() if symbol else None,
        "timeframe": timeframe,
        "setup_count": len(setups),
        "pending_setup_count": len(pending),
        "complete_setup_count": len(complete),
        "label_count": sum(len(labels) for labels in labels_by_setup.values()),
        "setup_hashes": [setup.setup_hash for setup in setups],
        "latest_setup_id": setups[0].setup_id if setups else None,
        "setups": [setup.model_dump(mode="json") for setup in setups],
        "labels_by_setup": {
            setup_id: [label.model_dump(mode="json") for label in labels]
            for setup_id, labels in labels_by_setup.items()
        },
        "future_label_before_completion_blocked": True,
        "deterministic": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def load_active_nine_candle_analog_index_manifest(symbol: str, timeframe: str) -> AnalogIndexManifest | None:
    init_db()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT manifest_json
            FROM nine_candle_analog_index_manifests
            WHERE symbol = ? AND timeframe = ? AND active = 1
            ORDER BY active_pointer_swapped_at DESC
            LIMIT 1
            """,
            (symbol.upper(), timeframe),
        ).fetchone()
    if row is None:
        return None
    return AnalogIndexManifest.model_validate_json(row["manifest_json"])


def atomic_swap_nine_candle_analog_index_manifest(
    *,
    symbol: str,
    timeframe: str,
    manifest: AnalogIndexManifest,
) -> AnalogIndexManifest:
    init_db()
    normalized = symbol.upper()
    active = load_active_nine_candle_analog_index_manifest(normalized, timeframe)
    if active and active.index_hash == manifest.index_hash and active.validated:
        return active
    swapped_at = now_iso()
    manifest_id = f"9c-index:{normalized}:{timeframe}:{manifest.index_hash[:16]}"
    enriched = manifest.model_copy(
        update={
            "manifest_id": manifest_id,
            "symbol": normalized,
            "timeframe": timeframe,
            "active": True,
            "previous_index_hash": active.index_hash if active else None,
            "active_pointer_swapped_at": swapped_at,
            "build_status": "validated" if manifest.validated else "rejected",
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE nine_candle_analog_index_manifests
            SET active = 0
            WHERE symbol = ? AND timeframe = ?
            """,
            (normalized, timeframe),
        )
        conn.execute(
            """
            INSERT INTO nine_candle_analog_index_manifests
            (manifest_id, symbol, timeframe, index_version, feature_manifest_version,
             index_hash, artifact_uri, artifact_sha256, artifact_size_bytes, artifact_verified,
             record_count, vector_dimension, active, created_at,
             active_pointer_swapped_at, manifest_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(manifest_id) DO UPDATE SET
                active = excluded.active,
                artifact_uri = excluded.artifact_uri,
                artifact_sha256 = excluded.artifact_sha256,
                artifact_size_bytes = excluded.artifact_size_bytes,
                artifact_verified = excluded.artifact_verified,
                active_pointer_swapped_at = excluded.active_pointer_swapped_at,
                manifest_json = excluded.manifest_json
            """,
            (
                enriched.manifest_id,
                normalized,
                timeframe,
                enriched.index_version,
                enriched.feature_manifest_version,
                enriched.index_hash,
                enriched.artifact_uri,
                enriched.artifact_sha256,
                enriched.artifact_size_bytes,
                1 if enriched.artifact_verified else 0,
                enriched.record_count,
                enriched.vector_dimension,
                1,
                swapped_at,
                enriched.active_pointer_swapped_at,
                enriched.model_dump_json(),
            ),
        )
        conn.commit()
    return enriched


def _json_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _audit_hash_payload(
    *,
    event_id: str,
    timestamp: str,
    level: str,
    message: str,
    source: str,
    mode: str,
    payload_json: str,
    sequence_number: int,
    previous_hash: str | None,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "source": source,
        "mode": mode,
        "payload": json.loads(payload_json or "{}"),
        "sequence_number": sequence_number,
        "previous_hash": previous_hash,
    }


def _backfill_audit_hashes(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT event_id, timestamp, level, message, source, mode, payload_json, sequence_number, previous_hash, record_hash
        FROM audit_events
        ORDER BY COALESCE(sequence_number, 999999999), timestamp ASC, event_id ASC
        """
    ).fetchall()
    previous_hash: str | None = None
    sequence_number = 0
    for row in rows:
        sequence_number += 1
        payload = _audit_hash_payload(
            event_id=row["event_id"],
            timestamp=row["timestamp"],
            level=row["level"],
            message=row["message"],
            source=row["source"],
            mode=row["mode"],
            payload_json=row["payload_json"],
            sequence_number=sequence_number,
            previous_hash=previous_hash,
        )
        record_hash = _audit_record_hash(payload)
        if (
            row["sequence_number"] != sequence_number
            or row["previous_hash"] != previous_hash
            or row["record_hash"] != record_hash
        ):
            conn.execute(
                """
                UPDATE audit_events
                SET sequence_number = ?, previous_hash = ?, record_hash = ?
                WHERE event_id = ?
                """,
                (sequence_number, previous_hash, record_hash, row["event_id"]),
            )
        previous_hash = record_hash


def _ensure_audit_hash_ready(conn: sqlite3.Connection) -> None:
    global _AUDIT_HASH_BACKFILLED
    _ensure_audit_hash_columns(conn)
    if not _AUDIT_HASH_BACKFILLED:
        _backfill_audit_hashes(conn)
        _AUDIT_HASH_BACKFILLED = True


def save_audit_event(event: AuditEvent, payload: dict[str, Any] | None = None) -> None:
    with _AUDIT_LOCK:
        with connect() as conn:
            _ensure_audit_hash_ready(conn)
            last = conn.execute(
                """
                SELECT sequence_number, record_hash
                FROM audit_events
                ORDER BY sequence_number DESC
                LIMIT 1
                """
            ).fetchone()
            sequence_number = int(last["sequence_number"] or 0) + 1 if last else 1
            previous_hash = last["record_hash"] if last else None
            payload_json = json.dumps(payload or {}, sort_keys=True)
            event_dict = event.model_dump(mode="json")
            record_hash = _audit_record_hash(
                _audit_hash_payload(
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    level=event.level,
                    message=event.message,
                    source=event.source,
                    mode=event_dict["mode"],
                    payload_json=payload_json,
                    sequence_number=sequence_number,
                    previous_hash=previous_hash,
                )
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO audit_events
                (event_id, timestamp, level, message, source, mode, payload_json, sequence_number, previous_hash, record_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp,
                    event.level,
                    event.message,
                    event.source,
                    event_dict["mode"],
                    payload_json,
                    sequence_number,
                    previous_hash,
                    record_hash,
                ),
            )


def list_audit_events(limit: int = 100) -> list[AuditEvent]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT event_id, timestamp, level, message, source, mode
            FROM audit_events
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [AuditEvent(**dict(row)) for row in rows]


def _load_audit_integrity_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT event_id, timestamp, level, message, source, mode, payload_json, sequence_number, previous_hash, record_hash
        FROM audit_events
        ORDER BY sequence_number ASC
        """
    ).fetchall()


def _build_audit_integrity_report(rows: list[sqlite3.Row]) -> AuditIntegrityReport:
    issues: list[str] = []
    previous_hash: str | None = None
    head_hash: str | None = None
    hashed_count = 0
    for expected_sequence, row in enumerate(rows, start=1):
        if row["sequence_number"] != expected_sequence:
            issues.append(f"sequence_gap:{row['event_id']}")
        if row["previous_hash"] != previous_hash:
            issues.append(f"previous_hash_mismatch:{row['event_id']}")
        expected_hash = _audit_record_hash(
            _audit_hash_payload(
                event_id=row["event_id"],
                timestamp=row["timestamp"],
                level=row["level"],
                message=row["message"],
                source=row["source"],
                mode=row["mode"],
                payload_json=row["payload_json"],
                sequence_number=row["sequence_number"],
                previous_hash=row["previous_hash"],
            )
        )
        if row["record_hash"] != expected_hash:
            issues.append(f"record_hash_mismatch:{row['event_id']}")
        if row["record_hash"]:
            hashed_count += 1
        previous_hash = row["record_hash"]
        head_hash = row["record_hash"]

    return AuditIntegrityReport(
        event_count=len(rows),
        hashed_event_count=hashed_count,
        chain_valid=len(issues) == 0,
        head_hash=head_hash,
        first_event_time=rows[0]["timestamp"] if rows else None,
        last_event_time=rows[-1]["timestamp"] if rows else None,
        algorithm="sha256-canonical-json",
        checked_at=now_iso(),
        issues=issues,
    )


def audit_integrity_report() -> AuditIntegrityReport:
    global _AUDIT_HASH_BACKFILLED
    with _AUDIT_LOCK:
        with connect() as conn:
            _ensure_audit_hash_ready(conn)
            rows = _load_audit_integrity_rows(conn)

    report = _build_audit_integrity_report(rows)
    if report.chain_valid:
        return report

    with _AUDIT_LOCK:
        with connect() as conn:
            _ensure_audit_hash_columns(conn)
            _backfill_audit_hashes(conn)
            _AUDIT_HASH_BACKFILLED = True
            rows = _load_audit_integrity_rows(conn)
    return _build_audit_integrity_report(rows)


def save_kill_switch(state: KillSwitchState) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO kill_switch_state (id, state_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
            """,
            (state.model_dump_json(), now_iso()),
        )


def load_kill_switch() -> KillSwitchState | None:
    with connect() as conn:
        row = conn.execute("SELECT state_json FROM kill_switch_state WHERE id = 1").fetchone()
    if row is None:
        return None
    return KillSwitchState.model_validate_json(row["state_json"])


def archive_replay(snapshot: ReplaySnapshot) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO replay_sessions
            (session_id, scenario_id, seed, state, current_timestamp_ns, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.session_id,
                snapshot.scenario_id,
                snapshot.seed,
                snapshot.state,
                snapshot.current_timestamp_ns,
                now_iso(),
            ),
        )
        conn.execute("DELETE FROM replay_events WHERE session_id = ?", (snapshot.session_id,))
        conn.executemany(
            """
            INSERT INTO replay_events (session_id, sequence_number, event_json)
            VALUES (?, ?, ?)
            """,
            [(snapshot.session_id, event.sequence_number, event.model_dump_json()) for event in snapshot.events],
        )


def load_replay(session_id: str) -> ReplaySnapshot | None:
    with connect() as conn:
        session = conn.execute("SELECT * FROM replay_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if session is None:
            return None
        events = conn.execute(
            """
            SELECT event_json FROM replay_events
            WHERE session_id = ?
            ORDER BY sequence_number ASC
            """,
            (session_id,),
        ).fetchall()
    return ReplaySnapshot(
        session_id=session["session_id"],
        scenario_id=session["scenario_id"],
        seed=session["seed"],
        state=session["state"],
        current_timestamp_ns=session["current_timestamp_ns"],
        events=[MarketEvent.model_validate_json(row["event_json"]) for row in events],
    )


def latest_replay() -> ReplaySnapshot | None:
    with connect() as conn:
        row = conn.execute("SELECT session_id FROM replay_sessions ORDER BY created_at DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return load_replay(row["session_id"])


def list_replays(limit: int = 25) -> list[ReplayArchiveSummary]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT s.session_id, s.scenario_id, s.seed, s.state, s.created_at,
                   COUNT(e.sequence_number) AS event_count
            FROM replay_sessions s
            LEFT JOIN replay_events e ON e.session_id = s.session_id
            GROUP BY s.session_id
            ORDER BY s.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [ReplayArchiveSummary(**dict(row)) for row in rows]


def save_capability_snapshot(capabilities: list[CapabilityManifestItem]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO capability_snapshots (created_at, capability_count, snapshot_json)
            VALUES (?, ?, ?)
            """,
            (
                now_iso(),
                len(capabilities),
                json.dumps([cap.model_dump(mode="json") for cap in capabilities], sort_keys=True),
            ),
        )


def storage_status() -> StorageStatus:
    with connect() as conn:
        audit_count = conn.execute("SELECT COUNT(*) AS n FROM audit_events").fetchone()["n"]
        replay_count = conn.execute("SELECT COUNT(*) AS n FROM replay_sessions").fetchone()["n"]
        replay_event_count = conn.execute("SELECT COUNT(*) AS n FROM replay_events").fetchone()["n"]
        capability_snapshot_count = conn.execute("SELECT COUNT(*) AS n FROM capability_snapshots").fetchone()["n"]
        point_in_time_snapshot_count = conn.execute("SELECT COUNT(*) AS n FROM point_in_time_snapshots").fetchone()["n"]
        feature_version_count = conn.execute("SELECT COUNT(*) AS n FROM feature_versions").fetchone()["n"]
        workspace_layout_count = conn.execute("SELECT COUNT(*) AS n FROM workspace_layouts").fetchone()["n"]
        request_log_count = conn.execute("SELECT COUNT(*) AS n FROM request_logs").fetchone()["n"]
        behavior_analysis_count = conn.execute("SELECT COUNT(*) AS n FROM behavior_analysis_results").fetchone()["n"]
        behavior_memory_count = conn.execute("SELECT COUNT(*) AS n FROM pattern_memory_records").fetchone()["n"]
        behavior_benchmark_count = conn.execute("SELECT COUNT(*) AS n FROM benchmark_runs").fetchone()["n"]
        safety_report_count = conn.execute("SELECT COUNT(*) AS n FROM behavior_safety_reports").fetchone()["n"]
        quarantine_count = conn.execute("SELECT COUNT(*) AS n FROM memory_quarantine_records").fetchone()["n"]
        golden_fixture_count = conn.execute("SELECT COUNT(*) AS n FROM golden_replay_fixtures").fetchone()["n"]
        benchmark_report_count = conn.execute("SELECT COUNT(*) AS n FROM behavior_benchmark_reports").fetchone()["n"]
        release_checklist_count = conn.execute("SELECT COUNT(*) AS n FROM release_checklists").fetchone()["n"]
        release_approval_count = conn.execute("SELECT COUNT(*) AS n FROM release_approvals").fetchone()["n"]
        release_evidence_count = conn.execute("SELECT COUNT(*) AS n FROM release_evidence_bundles").fetchone()["n"]
        release_artifact_count = conn.execute("SELECT COUNT(*) AS n FROM release_evidence_artifacts").fetchone()["n"]
        scenario_coverage_count = conn.execute("SELECT COUNT(*) AS n FROM behavior_scenario_coverage_reports").fetchone()["n"]
        executor_outbox_count = conn.execute("SELECT COUNT(*) AS n FROM executor_transport_outbox").fetchone()["n"]
    return StorageStatus(
        status="ready",
        db_path=str(DB_PATH),
        audit_events=audit_count,
        replay_sessions=replay_count,
        replay_events=replay_event_count,
        capability_snapshots=capability_snapshot_count,
        point_in_time_snapshots=point_in_time_snapshot_count,
        feature_versions=feature_version_count,
        workspace_layouts=workspace_layout_count,
        request_logs=request_log_count,
        behavior_analysis_results=behavior_analysis_count,
        behavior_memory_records=behavior_memory_count,
        behavior_benchmark_runs=behavior_benchmark_count,
        behavior_safety_reports=safety_report_count,
        memory_quarantines=quarantine_count,
        golden_replay_fixtures=golden_fixture_count,
        behavior_benchmark_reports=benchmark_report_count,
        release_checklists=release_checklist_count,
        release_approvals=release_approval_count,
        release_evidence_bundles=release_evidence_count,
        release_evidence_artifacts=release_artifact_count,
        behavior_scenario_coverage_reports=scenario_coverage_count,
        executor_transport_outbox=executor_outbox_count,
    )


def save_point_in_time_snapshot(snapshot: PointInTimeSnapshot) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO point_in_time_snapshots
            (snapshot_id, symbol, source_mode, seed, as_of_timestamp_ns, created_at, schema_version, payload_hash, payload_json, immutable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(snapshot_id) DO NOTHING
            """,
            (
                snapshot.snapshot_id,
                snapshot.symbol,
                snapshot.source_mode,
                snapshot.seed,
                snapshot.as_of_timestamp_ns,
                snapshot.created_at,
                snapshot.schema_version,
                snapshot.payload_hash,
                json.dumps(snapshot.payload, sort_keys=True),
            ),
        )


def list_point_in_time_snapshots(limit: int = 25) -> list[PointInTimeSnapshot]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM point_in_time_snapshots
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_snapshot_from_row(row) for row in rows]


def load_point_in_time_snapshot(snapshot_id: str) -> PointInTimeSnapshot | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM point_in_time_snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
    if row is None:
        return None
    return _snapshot_from_row(row)


def _snapshot_from_row(row: sqlite3.Row) -> PointInTimeSnapshot:
    return PointInTimeSnapshot(
        snapshot_id=row["snapshot_id"],
        symbol=row["symbol"],
        source_mode=row["source_mode"],
        seed=row["seed"],
        as_of_timestamp_ns=row["as_of_timestamp_ns"],
        created_at=row["created_at"],
        schema_version=row["schema_version"],
        payload_hash=row["payload_hash"],
        payload=json.loads(row["payload_json"]),
        immutable=bool(row["immutable"]),
    )


def save_feature_version(record: FeatureVersionRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO feature_versions
            (feature_hash, name, schema_version, pipeline_version, source_commit, created_at, input_snapshot_id, parameters_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.feature_hash,
                record.name,
                record.schema_version,
                record.pipeline_version,
                record.source_commit,
                record.created_at,
                record.input_snapshot_id,
                json.dumps(record.parameters, sort_keys=True),
            ),
        )


def list_feature_versions(limit: int = 100) -> list[FeatureVersionRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM feature_versions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        FeatureVersionRecord(
            feature_hash=row["feature_hash"],
            name=row["name"],
            schema_version=row["schema_version"],
            pipeline_version=row["pipeline_version"],
            source_commit=row["source_commit"],
            created_at=row["created_at"],
            input_snapshot_id=row["input_snapshot_id"],
            parameters=json.loads(row["parameters_json"]),
        )
        for row in rows
    ]


def save_feature_snapshot_record(record: FeatureSnapshotRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO behavior_feature_snapshots
            (snapshot_id, symbol, timeframe, decision_time_ns, source_snapshot_hash, feature_version,
             indicator_registry_version, storage_uri, storage_format, row_hash, created_at,
             adjusted_price_version, feature_count, unavailable_feature_count, proxy_excluded_count,
             blocked_excluded_count, lineage_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.snapshot_id,
                record.symbol,
                record.timeframe,
                record.decision_time_ns,
                record.source_snapshot_hash,
                record.feature_version,
                record.indicator_registry_version,
                record.storage_uri,
                record.storage_format,
                record.row_hash,
                record.created_at,
                record.adjusted_price_version,
                record.feature_count,
                record.unavailable_feature_count,
                record.proxy_excluded_count,
                record.blocked_excluded_count,
                json.dumps(record.lineage, sort_keys=True),
            ),
        )


def list_feature_snapshot_records(limit: int = 100, symbol: str | None = None) -> list[FeatureSnapshotRecord]:
    query = "SELECT * FROM behavior_feature_snapshots"
    if symbol:
        query += " WHERE symbol = ? ORDER BY created_at DESC, timeframe ASC LIMIT ?"
        params: tuple[Any, ...] = (symbol.upper(), limit)
    else:
        query += " ORDER BY created_at DESC, timeframe ASC LIMIT ?"
        params = (limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_feature_snapshot_from_row(row) for row in rows]


def count_feature_snapshot_records() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM behavior_feature_snapshots").fetchone()["n"]


def _feature_snapshot_from_row(row: sqlite3.Row) -> FeatureSnapshotRecord:
    return FeatureSnapshotRecord(
        snapshot_id=row["snapshot_id"],
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        decision_time_ns=row["decision_time_ns"],
        source_snapshot_hash=row["source_snapshot_hash"],
        feature_version=row["feature_version"],
        indicator_registry_version=row["indicator_registry_version"],
        storage_uri=row["storage_uri"],
        storage_format=row["storage_format"],
        row_hash=row["row_hash"],
        created_at=row["created_at"],
        adjusted_price_version=row["adjusted_price_version"],
        feature_count=row["feature_count"],
        unavailable_feature_count=row["unavailable_feature_count"],
        proxy_excluded_count=row["proxy_excluded_count"],
        blocked_excluded_count=row["blocked_excluded_count"],
        lineage=json.loads(row["lineage_json"]),
    )


def save_workspace_layout(layout: WorkspaceLayout) -> WorkspaceLayout:
    updated_layout = layout.model_copy(update={"updated_at": now_iso()})
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO workspace_layouts (workspace_id, version, updated_at, layout_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                version = excluded.version,
                updated_at = excluded.updated_at,
                layout_json = excluded.layout_json
            """,
            (
                updated_layout.workspace_id,
                updated_layout.version,
                updated_layout.updated_at,
                updated_layout.model_dump_json(),
            ),
        )
    return updated_layout


def load_workspace_layout(workspace_id: str) -> WorkspaceLayout | None:
    with connect() as conn:
        row = conn.execute("SELECT layout_json FROM workspace_layouts WHERE workspace_id = ?", (workspace_id,)).fetchone()
    if row is None:
        return None
    return WorkspaceLayout.model_validate_json(row["layout_json"])


def save_request_log(record: RequestLogRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO request_logs
            (request_id, run_id, decision_id, timestamp, method, path, status_code, latency_ms, actor_id, role, mode, error_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.request_id,
                record.run_id,
                record.decision_id,
                record.timestamp,
                record.method,
                record.path,
                record.status_code,
                record.latency_ms,
                record.actor_id,
                record.role,
                record.mode,
                record.error_code,
            ),
        )


def list_request_logs(limit: int = 100) -> list[RequestLogRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM request_logs
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [RequestLogRecord(**dict(row)) for row in rows]


def observability_status(limit: int = 20) -> ObservabilityStatus:
    with connect() as conn:
        rows = conn.execute("SELECT latency_ms, status_code FROM request_logs").fetchall()
        recent = conn.execute(
            """
            SELECT *
            FROM request_logs
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    latencies = sorted(float(row["latency_ms"]) for row in rows)
    if latencies:
        index = min(len(latencies) - 1, int(round(0.95 * (len(latencies) - 1))))
        p95 = round(latencies[index], 3)
    else:
        p95 = 0.0
    return ObservabilityStatus(
        status="ready",
        log_format="json",
        request_count=len(rows),
        error_count=sum(1 for row in rows if int(row["status_code"]) >= 400),
        p95_latency_ms=p95,
        recent_events=[RequestLogRecord(**dict(row)) for row in recent],
        required_fields=[
            "request_id",
            "run_id",
            "decision_id",
            "timestamp",
            "method",
            "path",
            "status_code",
            "latency_ms",
            "actor_id",
            "role",
            "mode",
            "error_code",
        ],
    )


def save_behavior_analysis(result: BehaviorAnalysisResult) -> None:
    payload = result.model_dump(mode="json")
    behavior = result.result
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO behavior_analysis_results
            (run_id, symbol, timeframe, decision_time, model_version, replay_snapshot_id, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.run_id,
                result.symbol,
                result.timeframe,
                str(behavior.get("decision_time", now_iso())),
                str(behavior.get("model_version", "unknown")),
                behavior.get("replay_snapshot_id"),
                json.dumps(payload, sort_keys=True),
            ),
        )


def load_behavior_analysis(run_id: str) -> BehaviorAnalysisResult | None:
    with connect() as conn:
        row = conn.execute("SELECT result_json FROM behavior_analysis_results WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return BehaviorAnalysisResult.model_validate_json(row["result_json"])


def save_stock_dna_profile(profile: StockDNAProfile) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO stock_dna_profiles (symbol, profile_json, updated_at)
            VALUES (?, ?, ?)
            """,
            (profile.symbol, profile.model_dump_json(), profile.updated_at),
        )


def load_stock_dna_profile(symbol: str) -> StockDNAProfile | None:
    with connect() as conn:
        row = conn.execute("SELECT profile_json FROM stock_dna_profiles WHERE symbol = ?", (symbol,)).fetchone()
    if row is None:
        return None
    return StockDNAProfile.model_validate_json(row["profile_json"])


def save_session_memory_profile(profile: SessionMemoryProfile) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO session_memory_profiles
            (symbol, session_phase, profile_json, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (profile.symbol, profile.session_phase, profile.model_dump_json(), profile.updated_at),
        )


def list_session_memory_profiles(symbol: str) -> list[SessionMemoryProfile]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT profile_json
            FROM session_memory_profiles
            WHERE symbol = ?
            ORDER BY session_phase ASC
            """,
            (symbol,),
        ).fetchall()
    return [SessionMemoryProfile.model_validate_json(row["profile_json"]) for row in rows]


def save_behavior_memory_record(record: BehaviorMemoryRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO pattern_memory_records
            (memory_id, symbol, trade_date, timeframe, pattern_id, market_state, session_phase, outcome_label, similarity_group, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.memory_id,
                record.symbol,
                record.trade_date,
                record.timeframe,
                record.pattern_id,
                record.market_state,
                record.session_phase,
                record.outcome_label,
                record.similarity_group,
                record.model_dump_json(),
            ),
        )


def list_behavior_memory(symbol: str, limit: int = 25) -> list[BehaviorMemoryRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT record_json
            FROM pattern_memory_records
            WHERE symbol = ?
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (symbol, limit),
        ).fetchall()
    return [BehaviorMemoryRecord.model_validate_json(row["record_json"]) for row in rows]


def save_similar_day_match(match: SimilarDayMatch) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO similar_day_matches
            (match_id, symbol, similar_day_id, similarity_score_pct, outcome_label, match_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                match.match_id,
                match.symbol,
                match.similar_day_id,
                match.similarity_score_pct,
                match.outcome_label,
                match.model_dump_json(),
            ),
        )


def list_similar_day_matches(symbol: str, limit: int = 10) -> list[SimilarDayMatch]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT match_json
            FROM similar_day_matches
            WHERE symbol = ?
            ORDER BY similarity_score_pct DESC
            LIMIT ?
            """,
            (symbol, limit),
        ).fetchall()
    return [SimilarDayMatch.model_validate_json(row["match_json"]) for row in rows]


def save_outcome_label(result: OutcomeLabelResult) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO outcome_labels
            (outcome_id, run_id, symbol, outcome_label, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"{result.run_id}:{result.pattern_id}",
                result.run_id,
                result.symbol,
                result.outcome_label,
                result.model_dump_json(),
            ),
        )


def list_outcome_labels(symbol: str, limit: int = 100) -> list[OutcomeLabelResult]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM outcome_labels
            WHERE symbol = ?
            ORDER BY outcome_id DESC
            LIMIT ?
            """,
            (symbol, limit),
        ).fetchall()
    return [OutcomeLabelResult.model_validate_json(row["payload_json"]) for row in rows]


def save_conservative_outcome_label(result: ConservativeOutcomeLabelResult) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO conservative_outcome_labels
            (run_id, symbol, timeframe, outcome_label, net_return_after_costs, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result.run_id,
                result.symbol,
                result.timeframe,
                result.outcome_label,
                result.net_return_after_costs,
                result.model_dump_json(),
            ),
        )


def list_conservative_outcome_labels(symbol: str, limit: int = 100) -> list[ConservativeOutcomeLabelResult]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM conservative_outcome_labels
            WHERE symbol = ?
            ORDER BY run_id DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
    return [ConservativeOutcomeLabelResult.model_validate_json(row["payload_json"]) for row in rows]


def save_failure_pattern(record: FailurePatternRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO failure_patterns
            (failure_id, symbol, pattern_id, failure_reason, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.failure_id,
                record.symbol,
                record.pattern_id,
                record.failure_reason,
                record.model_dump_json(),
            ),
        )


def list_failure_patterns(symbol: str, limit: int = 100) -> list[FailurePatternRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM failure_patterns
            WHERE symbol = ?
            ORDER BY failure_id DESC
            LIMIT ?
            """,
            (symbol, limit),
        ).fetchall()
    return [FailurePatternRecord.model_validate_json(row["payload_json"]) for row in rows]


def save_learning_trust_record(record: LearningTrustRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO learning_trust_table
            (trust_id, symbol, pattern_id, trust_score, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.trust_id,
                record.symbol,
                record.pattern_id,
                record.trust_score,
                record.model_dump_json(),
            ),
        )


def list_learning_trust_records(symbol: str, limit: int = 100) -> list[LearningTrustRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM learning_trust_table
            WHERE symbol = ?
            ORDER BY trust_score DESC
            LIMIT ?
            """,
            (symbol, limit),
        ).fetchall()
    return [LearningTrustRecord.model_validate_json(row["payload_json"]) for row in rows]


def save_execution_simulation(result: ExecutionSimulationResult, run_id: str | None = None) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO execution_simulations
            (simulation_id, run_id, symbol, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                result.simulation_id,
                run_id or result.simulation_id,
                result.symbol,
                result.model_dump_json(),
            ),
        )


def list_execution_simulations(symbol: str, limit: int = 100) -> list[ExecutionSimulationResult]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM execution_simulations
            WHERE symbol = ?
            ORDER BY simulation_id DESC
            LIMIT ?
            """,
            (symbol, limit),
        ).fetchall()
    return [ExecutionSimulationResult.model_validate_json(row["payload_json"]) for row in rows]


def save_behavior_safety_report(report: BehaviorSafetyReport) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO behavior_safety_reports
            (report_id, symbol, created_at, promotion_allowed, memory_quarantine_required, confidence_blocked, reality_gap_alert, report_hash, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.report_id,
                report.symbol,
                report.created_at,
                1 if report.promotion_allowed else 0,
                1 if report.memory_quarantine_required else 0,
                1 if report.confidence_blocked else 0,
                1 if report.reality_gap_alert else 0,
                report.report_hash,
                report.model_dump_json(),
            ),
        )


def load_behavior_safety_report(report_id: str) -> BehaviorSafetyReport | None:
    with connect() as conn:
        row = conn.execute("SELECT report_json FROM behavior_safety_reports WHERE report_id = ?", (report_id,)).fetchone()
    if row is None:
        return None
    return BehaviorSafetyReport.model_validate_json(row["report_json"])


def list_behavior_safety_reports(symbol: str | None = None, limit: int = 25) -> list[BehaviorSafetyReport]:
    with connect() as conn:
        if symbol:
            rows = conn.execute(
                """
                SELECT report_json
                FROM behavior_safety_reports
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT report_json
                FROM behavior_safety_reports
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [BehaviorSafetyReport.model_validate_json(row["report_json"]) for row in rows]


def save_memory_quarantine(record: MemoryQuarantineRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_quarantine_records
            (quarantine_id, symbol, created_at, status, source_report_id, record_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.quarantine_id,
                record.symbol,
                record.created_at,
                record.status,
                record.source_report_id,
                record.model_dump_json(),
            ),
        )


def list_memory_quarantines(symbol: str | None = None, active_only: bool = False, limit: int = 25) -> list[MemoryQuarantineRecord]:
    params: list[object] = []
    where: list[str] = []
    if symbol:
        where.append("symbol = ?")
        params.append(symbol)
    if active_only:
        where.append("status IN ('active', 'rebuild_pending')")
    sql = "SELECT record_json FROM memory_quarantine_records"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [MemoryQuarantineRecord.model_validate_json(row["record_json"]) for row in rows]


def save_golden_replay_fixture(fixture: GoldenReplayFixture) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO golden_replay_fixtures
            (fixture_id, symbol, scenario_id, seed, fixture_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                fixture.fixture_id,
                fixture.symbol,
                fixture.scenario_id,
                fixture.seed,
                fixture.model_dump_json(),
            ),
        )


def load_golden_replay_fixture(fixture_id: str) -> GoldenReplayFixture | None:
    with connect() as conn:
        row = conn.execute("SELECT fixture_json FROM golden_replay_fixtures WHERE fixture_id = ?", (fixture_id,)).fetchone()
    if row is None:
        return None
    return GoldenReplayFixture.model_validate_json(row["fixture_json"])


def list_golden_replay_fixtures(limit: int = 25) -> list[GoldenReplayFixture]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT fixture_json
            FROM golden_replay_fixtures
            ORDER BY fixture_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [GoldenReplayFixture.model_validate_json(row["fixture_json"]) for row in rows]


def save_behavior_benchmark_report(report: BehaviorBenchmarkReport) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO behavior_benchmark_reports
            (report_id, symbol, created_at, promotion_allowed, report_hash, report_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.report_id,
                report.symbol,
                report.created_at,
                1 if report.promotion_allowed else 0,
                report.report_hash,
                report.model_dump_json(),
            ),
        )


def load_behavior_benchmark_report(report_id: str) -> BehaviorBenchmarkReport | None:
    with connect() as conn:
        row = conn.execute("SELECT report_json FROM behavior_benchmark_reports WHERE report_id = ?", (report_id,)).fetchone()
    if row is None:
        return None
    return BehaviorBenchmarkReport.model_validate_json(row["report_json"])


def list_behavior_benchmark_reports(symbol: str | None = None, limit: int = 25) -> list[BehaviorBenchmarkReport]:
    with connect() as conn:
        if symbol:
            rows = conn.execute(
                """
                SELECT report_json
                FROM behavior_benchmark_reports
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT report_json
                FROM behavior_benchmark_reports
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [BehaviorBenchmarkReport.model_validate_json(row["report_json"]) for row in rows]


def save_behavior_scenario_coverage_report(report: BehaviorScenarioCoverageReport) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO behavior_scenario_coverage_reports
            (coverage_id, symbol, benchmark_report_id, generated_at, coverage_score_pct, coverage_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.coverage_id,
                report.symbol,
                report.benchmark_report_id,
                report.generated_at,
                report.coverage_score_pct,
                report.model_dump_json(),
            ),
        )


def load_behavior_scenario_coverage_report(coverage_id: str) -> BehaviorScenarioCoverageReport | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT coverage_json FROM behavior_scenario_coverage_reports WHERE coverage_id = ?",
            (coverage_id,),
        ).fetchone()
    if row is None:
        return None
    return BehaviorScenarioCoverageReport.model_validate_json(row["coverage_json"])


def list_behavior_scenario_coverage_reports(symbol: str | None = None, limit: int = 25) -> list[BehaviorScenarioCoverageReport]:
    with connect() as conn:
        if symbol:
            rows = conn.execute(
                """
                SELECT coverage_json
                FROM behavior_scenario_coverage_reports
                WHERE symbol = ?
                ORDER BY generated_at DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT coverage_json
                FROM behavior_scenario_coverage_reports
                ORDER BY generated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [BehaviorScenarioCoverageReport.model_validate_json(row["coverage_json"]) for row in rows]


def save_release_checklist(checklist: MockToReplayReleaseChecklist) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO release_checklists
            (checklist_id, symbol, target_mode, created_at, release_allowed, checklist_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                checklist.checklist_id,
                checklist.symbol,
                checklist.target_mode,
                checklist.created_at,
                1 if checklist.release_allowed else 0,
                checklist.model_dump_json(),
            ),
        )


def load_release_checklist(checklist_id: str) -> MockToReplayReleaseChecklist | None:
    with connect() as conn:
        row = conn.execute("SELECT checklist_json FROM release_checklists WHERE checklist_id = ?", (checklist_id,)).fetchone()
    if row is None:
        return None
    return MockToReplayReleaseChecklist.model_validate_json(row["checklist_json"])


def list_release_checklists(symbol: str | None = None, limit: int = 25) -> list[MockToReplayReleaseChecklist]:
    with connect() as conn:
        if symbol:
            rows = conn.execute(
                """
                SELECT checklist_json
                FROM release_checklists
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT checklist_json
                FROM release_checklists
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [MockToReplayReleaseChecklist.model_validate_json(row["checklist_json"]) for row in rows]


def save_release_approval(record: ReleaseApprovalRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO release_approvals
            (approval_id, symbol, target_mode, benchmark_report_id, status, requested_at, expires_at, approval_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.approval_id,
                record.symbol,
                record.target_mode,
                record.benchmark_report_id,
                record.status,
                record.requested_at,
                record.expires_at,
                record.model_dump_json(),
            ),
        )


def load_release_approval(approval_id: str) -> ReleaseApprovalRecord | None:
    with connect() as conn:
        row = conn.execute("SELECT approval_json FROM release_approvals WHERE approval_id = ?", (approval_id,)).fetchone()
    if row is None:
        return None
    return ReleaseApprovalRecord.model_validate_json(row["approval_json"])


def list_release_approvals(symbol: str | None = None, status: str | None = None, limit: int = 25) -> list[ReleaseApprovalRecord]:
    with connect() as conn:
        conditions = []
        params: list[Any] = []
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = conn.execute(
            f"""
            SELECT approval_json
            FROM release_approvals
            {where}
            ORDER BY requested_at DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    return [ReleaseApprovalRecord.model_validate_json(row["approval_json"]) for row in rows]


def latest_active_release_approval(symbol: str, benchmark_report_id: str, now: str) -> ReleaseApprovalRecord | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT approval_json
            FROM release_approvals
            WHERE symbol = ?
              AND benchmark_report_id = ?
              AND status = 'approved'
              AND expires_at > ?
            ORDER BY requested_at DESC
            LIMIT 1
            """,
            (symbol, benchmark_report_id, now),
        ).fetchone()
    if row is None:
        return None
    return ReleaseApprovalRecord.model_validate_json(row["approval_json"])


def save_release_evidence_bundle(bundle: ReleaseEvidenceBundle) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO release_evidence_bundles
            (bundle_id, symbol, target_mode, generated_at, benchmark_report_id, bundle_hash, bundle_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bundle.bundle_id,
                bundle.symbol,
                bundle.target_mode,
                bundle.generated_at,
                bundle.benchmark_report.report_id,
                bundle.bundle_hash,
                bundle.model_dump_json(),
            ),
        )


def load_release_evidence_bundle(bundle_id: str) -> ReleaseEvidenceBundle | None:
    with connect() as conn:
        row = conn.execute("SELECT bundle_json FROM release_evidence_bundles WHERE bundle_id = ?", (bundle_id,)).fetchone()
    if row is None:
        return None
    return ReleaseEvidenceBundle.model_validate_json(row["bundle_json"])


def list_release_evidence_bundles(symbol: str | None = None, limit: int = 25) -> list[ReleaseEvidenceBundle]:
    with connect() as conn:
        if symbol:
            rows = conn.execute(
                """
                SELECT bundle_json
                FROM release_evidence_bundles
                WHERE symbol = ?
                ORDER BY generated_at DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT bundle_json
                FROM release_evidence_bundles
                ORDER BY generated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [ReleaseEvidenceBundle.model_validate_json(row["bundle_json"]) for row in rows]


def save_release_evidence_artifact(artifact: ReleaseEvidenceArtifact) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO release_evidence_artifacts
            (artifact_id, symbol, target_mode, created_at, bundle_id, bundle_hash, manifest_sha256, artifact_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.artifact_id,
                artifact.symbol,
                artifact.target_mode,
                artifact.created_at,
                artifact.bundle_id,
                artifact.bundle_hash,
                artifact.manifest_sha256,
                artifact.model_dump_json(),
            ),
        )


def load_release_evidence_artifact(artifact_id: str) -> ReleaseEvidenceArtifact | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT artifact_json FROM release_evidence_artifacts WHERE artifact_id = ?",
            (artifact_id,),
        ).fetchone()
    if row is None:
        return None
    return ReleaseEvidenceArtifact.model_validate_json(row["artifact_json"])


def list_release_evidence_artifacts(symbol: str | None = None, limit: int = 25) -> list[ReleaseEvidenceArtifact]:
    with connect() as conn:
        if symbol:
            rows = conn.execute(
                """
                SELECT artifact_json
                FROM release_evidence_artifacts
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT artifact_json
                FROM release_evidence_artifacts
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [ReleaseEvidenceArtifact.model_validate_json(row["artifact_json"]) for row in rows]


def save_executor_transport_record(record: ExecutorTransportOutboxRecord) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO executor_transport_outbox
            (delivery_id, idempotency_key, status, attempt_count, max_attempts, created_at, updated_at, next_attempt_at, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(delivery_id) DO UPDATE SET
                status = excluded.status,
                attempt_count = excluded.attempt_count,
                max_attempts = excluded.max_attempts,
                updated_at = excluded.updated_at,
                next_attempt_at = excluded.next_attempt_at,
                record_json = excluded.record_json
            """,
            (
                record.delivery_id,
                record.idempotency_key,
                record.status,
                record.attempt_count,
                record.max_attempts,
                record.created_at,
                record.updated_at,
                record.next_attempt_at,
                record.model_dump_json(),
            ),
        )


def load_executor_transport_record(delivery_id: str) -> ExecutorTransportOutboxRecord | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT record_json FROM executor_transport_outbox WHERE delivery_id = ?",
            (delivery_id,),
        ).fetchone()
    if row is None:
        return None
    return ExecutorTransportOutboxRecord.model_validate_json(row["record_json"])


def load_executor_transport_by_idempotency(idempotency_key: str) -> ExecutorTransportOutboxRecord | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT record_json FROM executor_transport_outbox WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
    if row is None:
        return None
    return ExecutorTransportOutboxRecord.model_validate_json(row["record_json"])


def list_executor_transport_records(
    status: str | None = None,
    limit: int = 100,
) -> list[ExecutorTransportOutboxRecord]:
    with connect() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT record_json
                FROM executor_transport_outbox
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT record_json
                FROM executor_transport_outbox
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [ExecutorTransportOutboxRecord.model_validate_json(row["record_json"]) for row in rows]


def executor_transport_counts() -> dict[str, int]:
    counts = {"pending": 0, "delivering": 0, "acknowledged": 0, "retry_wait": 0, "manual_review": 0, "cancelled": 0, "dead_letter": 0}
    with connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM executor_transport_outbox GROUP BY status"
        ).fetchall()
    for row in rows:
        counts[row["status"]] = row["n"]
    return counts


def list_due_executor_transport_records(now: str, limit: int = 100) -> list[ExecutorTransportOutboxRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT record_json
            FROM executor_transport_outbox
            WHERE status = 'pending'
               OR (status = 'retry_wait' AND next_attempt_at IS NOT NULL AND next_attempt_at <= ?)
            ORDER BY COALESCE(next_attempt_at, created_at) DESC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
    return [ExecutorTransportOutboxRecord.model_validate_json(row["record_json"]) for row in rows]


def list_stale_delivering_records(stale_before: str, limit: int = 100) -> list[ExecutorTransportOutboxRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT record_json
            FROM executor_transport_outbox
            WHERE status = 'delivering' AND updated_at <= ?
            ORDER BY updated_at ASC
            LIMIT ?
            """,
            (stale_before, limit),
        ).fetchall()
    return [ExecutorTransportOutboxRecord.model_validate_json(row["record_json"]) for row in rows]


def save_executor_transport_trace(trace) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO executor_transport_traces
            (trace_id, delivery_id, event_time, event_type, trace_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (trace.trace_id, trace.delivery_id, trace.event_time, trace.event_type, trace.model_dump_json()),
        )


def list_executor_transport_traces(delivery_id: str | None = None, limit: int = 100):
    from .models import ExecutorTransportTrace

    with connect() as conn:
        if delivery_id:
            rows = conn.execute(
                """
                SELECT trace_json FROM executor_transport_traces
                WHERE delivery_id = ?
                ORDER BY event_time DESC LIMIT ?
                """,
                (delivery_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT trace_json FROM executor_transport_traces ORDER BY event_time DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [ExecutorTransportTrace.model_validate_json(row["trace_json"]) for row in rows]


def latest_executor_transport_trace(delivery_id: str):
    from .models import ExecutorTransportTrace

    with connect() as conn:
        row = conn.execute(
            """
            SELECT trace_json FROM executor_transport_traces
            WHERE delivery_id = ?
            ORDER BY event_time DESC LIMIT 1
            """,
            (delivery_id,),
        ).fetchone()
    return ExecutorTransportTrace.model_validate_json(row["trace_json"]) if row else None


def latest_executor_transport_trace_before(delivery_id: str, event_time: str, trace_id: str):
    from .models import ExecutorTransportTrace

    with connect() as conn:
        row = conn.execute(
            """
            SELECT trace_json FROM executor_transport_traces
            WHERE delivery_id = ?
              AND (event_time < ? OR (event_time = ? AND trace_id < ?))
            ORDER BY event_time DESC, trace_id DESC
            LIMIT 1
            """,
            (delivery_id, event_time, event_time, trace_id),
        ).fetchone()
    return ExecutorTransportTrace.model_validate_json(row["trace_json"]) if row else None


def save_transport_health_sample(sample) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO transport_health_samples (sample_id, sampled_at, sample_json)
            VALUES (?, ?, ?)
            """,
            (sample.sample_id, sample.sampled_at, sample.model_dump_json()),
        )


def list_transport_health_samples(limit: int = 100):
    from .models import TransportHealthSample

    with connect() as conn:
        rows = conn.execute(
            "SELECT sample_json FROM transport_health_samples ORDER BY sampled_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [TransportHealthSample.model_validate_json(row["sample_json"]) for row in rows]


def save_transport_incident(incident) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO transport_incidents (incident_id, status, updated_at, incident_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(incident_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at,
                incident_json = excluded.incident_json
            """,
            (incident.incident_id, incident.status, incident.updated_at, incident.model_dump_json()),
        )


def load_active_transport_incident():
    from .models import TransportIncident

    with connect() as conn:
        row = conn.execute(
            """
            SELECT incident_json FROM transport_incidents
            WHERE status IN ('open', 'acknowledged')
            ORDER BY updated_at DESC LIMIT 1
            """
        ).fetchone()
    return TransportIncident.model_validate_json(row["incident_json"]) if row else None


def list_transport_incidents(limit: int = 100):
    from .models import TransportIncident

    with connect() as conn:
        rows = conn.execute(
            "SELECT incident_json FROM transport_incidents ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [TransportIncident.model_validate_json(row["incident_json"]) for row in rows]


def save_behavior_benchmark_run(run: BehaviorBenchmarkRun) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO benchmark_runs
            (run_id, symbol, status, created_at, completed_at, run_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run.run_id, run.symbol, run.status, run.created_at, run.completed_at, run.model_dump_json()),
        )


def load_behavior_benchmark_run(run_id: str) -> BehaviorBenchmarkRun | None:
    with connect() as conn:
        row = conn.execute("SELECT run_json FROM benchmark_runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return BehaviorBenchmarkRun.model_validate_json(row["run_json"])


def save_indicator_result_cache_row(row: dict[str, Any]) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO indicator_result_cache
            (cache_id, symbol, timeframe, source_snapshot_hash, source_snapshot_id, candle_start_time,
             candle_end_time, candle_count, indicator_registry_version, feature_manifest_version,
             promoted_indicator_hash, indicator_id, runtime_status, output_present, used_for_probability,
             trade_allowed, order_routing_enabled, live_trading_blocked, artifact_uri, artifact_sha256,
             latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_id) DO UPDATE SET
                runtime_status = excluded.runtime_status,
                output_present = excluded.output_present,
                artifact_uri = excluded.artifact_uri,
                artifact_sha256 = excluded.artifact_sha256,
                latency_ms = excluded.latency_ms,
                created_at = excluded.created_at,
                used_for_probability = 0,
                trade_allowed = 0,
                order_routing_enabled = 0,
                live_trading_blocked = 1
            """,
            (
                row["cache_id"],
                row["symbol"],
                row["timeframe"],
                row["source_snapshot_hash"],
                row.get("source_snapshot_id"),
                row.get("candle_start_time"),
                row.get("candle_end_time"),
                int(row["candle_count"]),
                row["indicator_registry_version"],
                row["feature_manifest_version"],
                row["promoted_indicator_hash"],
                row["indicator_id"],
                row["runtime_status"],
                int(bool(row["output_present"])),
                0,
                0,
                0,
                1,
                row["artifact_uri"],
                row["artifact_sha256"],
                float(row["latency_ms"]),
                row["created_at"],
            ),
        )


def save_indicator_signal_history_record(record: IndicatorSignalHistoryRecord) -> IndicatorSignalHistoryRecord:
    init_db()
    payload = record.model_dump(mode="json")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO indicator_signal_history
            (history_id, symbol, indicator_id, timeframe, signal_direction, signal_time_ns,
             decision_time_ns, session_phase, regime_id, source_snapshot_id, source_snapshot_hash,
             feature_manifest_version, indicator_registry_version, label_status, outcome_label,
             counted_in_reliability, created_at, history_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(history_id) DO UPDATE SET
                symbol = excluded.symbol,
                indicator_id = excluded.indicator_id,
                timeframe = excluded.timeframe,
                signal_direction = excluded.signal_direction,
                signal_time_ns = excluded.signal_time_ns,
                decision_time_ns = excluded.decision_time_ns,
                session_phase = excluded.session_phase,
                regime_id = excluded.regime_id,
                source_snapshot_id = excluded.source_snapshot_id,
                source_snapshot_hash = excluded.source_snapshot_hash,
                feature_manifest_version = excluded.feature_manifest_version,
                indicator_registry_version = excluded.indicator_registry_version,
                label_status = excluded.label_status,
                outcome_label = excluded.outcome_label,
                counted_in_reliability = excluded.counted_in_reliability,
                created_at = excluded.created_at,
                history_json = excluded.history_json
            """,
            (
                record.history_id,
                record.symbol,
                record.indicator_id,
                record.timeframe,
                record.signal_direction,
                record.signal_time_ns,
                record.decision_time_ns,
                record.session_phase,
                record.regime_id,
                record.source_snapshot_id,
                record.source_snapshot_hash,
                record.feature_manifest_version,
                record.indicator_registry_version,
                record.label.label_status,
                record.label.outcome_label,
                1 if record.counted_in_reliability else 0,
                record.created_at,
                json.dumps(payload, sort_keys=True),
            ),
        )
    return record


def list_indicator_signal_history_records(
    symbol: str,
    indicator_id: str,
    timeframe: str = "1m",
    *,
    limit: int = 250,
    counted_only: bool = False,
    available_by_decision_time_ns: int | None = None,
    created_at_or_before: str | None = None,
) -> list[IndicatorSignalHistoryRecord]:
    init_db()
    clauses = ["symbol = ?", "indicator_id = ?", "timeframe = ?"]
    params: list[Any] = [symbol.upper(), indicator_id, timeframe]
    if counted_only:
        clauses.append("counted_in_reliability = 1")
    if available_by_decision_time_ns is not None:
        clauses.append("decision_time_ns <= ?")
        params.append(int(available_by_decision_time_ns))
        clauses.append("signal_time_ns <= ?")
        params.append(int(available_by_decision_time_ns))
    if created_at_or_before is not None:
        clauses.append("created_at <= ?")
        params.append(created_at_or_before)
    params.append(max(1, min(int(limit), 2000)))
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT history_json
            FROM indicator_signal_history
            WHERE {' AND '.join(clauses)}
            ORDER BY signal_time_ns DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [IndicatorSignalHistoryRecord.model_validate_json(row["history_json"]) for row in rows]


def build_indicator_signal_history_summary(
    symbol: str,
    indicator_id: str,
    timeframe: str = "1m",
    *,
    limit: int = 250,
) -> IndicatorSignalHistorySummary:
    records = list_indicator_signal_history_records(symbol=symbol, indicator_id=indicator_id, timeframe=timeframe, limit=limit)
    counted = [record for record in records if record.counted_in_reliability]
    complete = [record for record in records if record.label.label_status == "complete"]
    pending = [record for record in records if record.label.label_status == "pending"]
    gates = [
        _simple_gate("IND-HIST-001", "Persistent signal history table available", True, f"records={len(records)}"),
        _simple_gate("IND-HIST-002", "Only completed labels count for reliability", all(record.label.label_status == "complete" for record in counted), f"counted={len(counted)}"),
        _simple_gate("IND-HIST-003", "Research-only safety preserved", True, "trade_allowed=false; order_routing_enabled=false; live_trading_blocked=true"),
    ]
    return IndicatorSignalHistorySummary(
        history_version="indicator-signal-history-store.v1.83",
        symbol=symbol.upper(),
        indicator_id=indicator_id,
        timeframe=timeframe,  # type: ignore[arg-type]
        record_count=len(records),
        counted_record_count=len(counted),
        pending_record_count=len(pending),
        complete_record_count=len(complete),
        latest_history_id=records[0].history_id if records else None,
        latest_signal_time_ns=records[0].signal_time_ns if records else None,
        storage_backed=bool(records),
        records=records,
        gates=gates,
        notes=[
            "Persisted indicator signal history is used for reliability before deterministic fixtures.",
            "Pending labels are stored for audit but excluded from reliability counts.",
            "This history is research-only and cannot route orders.",
        ],
    )


def list_indicator_result_cache_rows(
    symbol: str | None = None,
    timeframe: str | None = None,
    source_snapshot_hash: str | None = None,
    indicator_id: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    init_db()
    clauses: list[str] = []
    params: list[Any] = []
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol.upper())
    if timeframe:
        clauses.append("timeframe = ?")
        params.append(timeframe)
    if source_snapshot_hash:
        clauses.append("source_snapshot_hash = ?")
        params.append(source_snapshot_hash)
    if indicator_id:
        clauses.append("indicator_id = ?")
        params.append(indicator_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, min(int(limit), 2000)))
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM indicator_result_cache
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def delete_indicator_result_cache_row(cache_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM indicator_result_cache WHERE cache_id = ?", (cache_id,)).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM indicator_result_cache WHERE cache_id = ?", (cache_id,))
    return dict(row)


def _simple_gate(gate_id: str, name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": passed,
        "evidence": evidence,
        "remediation": None if passed else "Persist clean completed indicator labels before using reliability history.",
    }
