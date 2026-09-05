import json
import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.behavior import openalgo_transport
from app.behavior import transport_resilience
from app.behavior import deployment_recovery
from app.behavior import final_release_audit
from app.behavior import transport_security
from app import storage


client = TestClient(app)


IST = timezone(timedelta(hours=5, minutes=30))


def ns_ist(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=IST).timestamp() * 1_000_000_000)


def test_health_ready():
    assert client.get("/health").status_code == 200
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_enveloped_endpoints():
    paths = [
        "/api/time",
        "/api/auth/me",
        "/api/storage/status",
        "/api/observability/status",
        "/api/observability/requests",
        "/api/system/mode",
        "/api/system/features",
        "/api/layout/cockpit",
        "/api/system/killswitch",
        "/api/system/pipeline",
        "/api/decision/current",
        "/api/portfolio/state",
        "/api/risk/state",
        "/api/market/dna",
        "/api/microstructure/state",
        "/api/replay/session",
        "/api/replay/archive",
        "/api/execution/simulation",
        "/api/execution/order-path/status",
        "/api/data/quality",
        "/api/audit/events",
        "/api/audit/integrity",
        "/api/knowledge/graph",
        "/api/v1/behavior/spec",
        "/api/v1/behavior/output-columns",
        "/api/v1/behavior/frontend/panel-map",
        "/api/v1/behavior/runtime/readiness",
        "/api/v1/behavior/replay/indicator-chart/current",
        "/api/v1/behavior/chart/replay/current",
        "/api/v1/behavior/chart/reasoning/current",
        "/api/v1/behavior/market-regime/feedback/current",
        "/api/v1/behavior/market-structure/liquidity/current",
        "/api/v1/behavior/execution-event-oi/risk/current",
        "/api/v1/behavior/post-entry/lifecycle/current",
        "/api/v1/behavior/final-confluence/arbiter/current",
        "/api/v1/behavior/indicators/si_macd_ta/ontology",
        "/api/v1/behavior/indicators/si_macd_ta/reliability/RELIANCE",
        "/api/v1/behavior/indicators/intelligence-summary/RELIANCE",
        "/api/v1/behavior/indicators/observations/current",
        "/api/v1/behavior/9c-dna/current/RELIANCE",
        "/api/v1/behavior/9c-dna/setup-memory/RELIANCE",
        "/api/v1/behavior/9c-dna/vector-audit/RELIANCE",
        "/api/v1/behavior/9c-dna/analogs/RELIANCE",
        "/api/v1/behavior/9c-dna/evidence-packet/RELIANCE",
        "/api/v1/behavior/9c-dna/indicator-runtime/RELIANCE",
        "/api/v1/behavior/9c-dna/indicator-runtime-coverage",
        "/api/v1/behavior/9c-dna/indicator-promotion/RELIANCE",
        "/api/v1/behavior/indicator-cache/status/RELIANCE",
        "/api/v1/behavior/indicator-cache/results/RELIANCE",
        "/api/v1/behavior/9c-dna/level-proximity/RELIANCE",
        "/api/v1/behavior/9c-dna/confluence/RELIANCE",
        "/api/v1/behavior/9c-dna/level-memory/RELIANCE",
        "/api/v1/behavior/9c-dna/regime/RELIANCE",
        "/api/v1/behavior/9c-dna/hypotheses/RELIANCE",
        "/api/v1/behavior/9c-dna/path-analogs/RELIANCE",
        "/api/v1/behavior/9c-dna/ood-status/RELIANCE",
        "/api/v1/behavior/9c-dna/decision/RELIANCE",
        "/api/v1/behavior/9c-dna/indicator-alignment/RELIANCE",
        "/api/v1/behavior/9c-dna/model-status",
        "/api/v1/behavior/9c-dna/feature-manifest",
        "/api/v1/behavior/9c-dna/feature-manifest/integrity",
        "/api/v1/behavior/9c-dna/calibration",
        "/api/v1/behavior/9c-dna/model-promotion-guard",
        "/api/v1/behavior/9c-dna/index-manifest",
        "/api/v1/behavior/patterns/taxonomy/current",
        "/api/v1/behavior/timeframes/conflict/current",
        "/api/v1/behavior/timeframes/pullback/current",
        "/api/v1/behavior/indicators/expansion/current",
        "/api/v1/behavior/replay/indicator-matrix/current",
        "/api/v1/behavior/combination-similarity/current",
        "/api/v1/behavior/analog-research/current",
        "/api/v1/behavior/event-sequences/current",
        "/api/v1/behavior/confluence/diagnostics/current",
        "/api/v1/behavior/design-similarity/current",
        "/api/v1/behavior/bands/distances",
        "/api/v1/behavior/patterns/by-timeframe",
        "/api/v1/behavior/calendar/event-regime/current",
        "/api/v1/behavior/cross-market/influence/current",
        "/api/v1/behavior/corporate-abnormal/current",
        "/api/v1/behavior/risk/portfolio-cooldown/current",
        "/api/v1/behavior/execution-intent/paper-safety/current",
        "/api/v1/behavior/execution-permission/preflight/current",
        "/api/v1/behavior/executor-handoff/audit/current",
        "/api/v1/kronos/forecast-shared-snapshot/current",
        "/api/v1/twin/full-analysis/current",
        "/api/v1/behavior/walk-forward/current",
        "/api/v1/behavior/decision/readiness/current",
        "/api/v1/behavior/lifecycle/current",
        "/api/v1/behavior/lifecycle/compare/current",
        "/api/v1/behavior/lifecycle/evidence/current",
        "/api/v1/behavior/tradeability/current",
        "/api/v1/release/final-audit",
        "/api/v1/release/safety-scan",
        "/api/v1/release/candidate/current",
        "/api/v1/behavior/capability-manifest",
        "/api/v1/behavior/data/adapter-manifest",
        "/api/v1/behavior/features/causal-whitelist",
        "/api/v1/behavior/features/default-safe",
        "/api/v1/behavior/stock/NIFTY-MOCK/dna",
        "/api/v1/behavior/stock/NIFTY-MOCK/memory",
        "/api/v1/behavior/stock/NIFTY-MOCK/session-memory",
        "/api/v1/behavior/stock/NIFTY-MOCK/day-of-week-memory",
        "/api/v1/behavior/exact-time/session-memory/current",
        "/api/v1/behavior/stock/NIFTY-MOCK/pattern-memory",
        "/api/v1/behavior/stock/NIFTY-MOCK/failure-library",
        "/api/v1/behavior/stock/NIFTY-MOCK/trust-table",
        "/api/v1/behavior/decision/current",
        "/api/v1/behavior/risk/current",
        "/api/v1/behavior/execution/current",
        "/api/v1/behavior/validation/walk-forward",
        "/api/v1/behavior/validation/out-of-sample",
        "/api/v1/behavior/safety/drift/current",
        "/api/v1/behavior/safety/ood/current",
        "/api/v1/behavior/safety/reality-gap/current",
        "/api/v1/behavior/acp/status",
        "/api/v1/behavior/safety/report/current",
        "/api/v1/behavior/safety/reports",
        "/api/v1/behavior/memory/quarantine",
        "/api/v1/behavior/memory/rebuild-plan/NIFTY-MOCK",
        "/api/v1/behavior/replay/golden-fixtures",
        "/api/v1/behavior/replay/golden-fixtures/golden-nifty-mock-golden-opening-drive-42/verify",
        "/api/v1/behavior/benchmark/report/current",
        "/api/v1/behavior/benchmark/report/drilldown/current",
        "/api/v1/behavior/benchmark/scenario-coverage/current",
        "/api/v1/behavior/benchmark/scenario-coverage/reports",
        "/api/v1/behavior/benchmark/reports",
        "/api/v1/behavior/release/mock-to-replay/checklist",
        "/api/v1/behavior/release/evidence/current",
        "/api/v1/behavior/release/evidence/bundles",
        "/api/v1/behavior/release/evidence/artifacts",
        "/api/v1/behavior/release/approvals",
        "/api/v1/behavior/release/checklists",
        "/api/v1/behavior/similar-days/NIFTY-MOCK",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        body = response.json()
        assert "meta" in body
        assert "data" in body
        assert body["meta"]["source"] == "mock"


def test_kill_switch_blocks_order_paths_flag():
    trigger = client.post(
        "/api/system/killswitch/trigger",
        json={"reason": "test trigger", "source": "user_ui", "actor_id": "pytest"},
    )
    assert trigger.status_code == 200
    assert trigger.json()["data"]["blocks_order_paths"] is True
    from app import storage

    persisted = storage.load_kill_switch()
    assert persisted is not None
    assert persisted.blocks_order_paths is True
    assert persisted.state == "triggered"

    reset = client.post(
        "/api/system/killswitch/reset",
        json={"actor_id": "pytest", "confirmation": "RESET_MOCK_KILL_SWITCH"},
        headers={"X-TradeVision-Role": "risk_manager"},
    )
    assert reset.status_code == 200
    assert reset.json()["data"]["state"] == "armed"
    persisted = storage.load_kill_switch()
    assert persisted is not None
    assert persisted.blocks_order_paths is False


def test_replay_deterministic_for_same_seed():
    first = client.post("/api/replay/start", json={"scenario_id": "mock_opening_drive", "seed": 7}).json()["data"]["events"]
    second = client.post("/api/replay/start", json={"scenario_id": "mock_opening_drive", "seed": 7}).json()["data"]["events"]
    assert first == second
    assert [e["payload"] for e in first] == [e["payload"] for e in second]
    assert [e["watermark"] for e in first] == [e["watermark"] for e in second]


def test_replay_archive_persists_session_events():
    from app import storage

    session = client.post("/api/replay/start", json={"scenario_id": "mock_archive", "seed": 11}).json()["data"]
    persisted = storage.load_replay(session["session_id"])
    assert persisted is not None
    assert persisted.seed == 11
    assert len(persisted.events) == 16

    archive = client.get("/api/replay/archive")
    assert archive.status_code == 200
    ids = {item["session_id"] for item in archive.json()["data"]}
    assert session["session_id"] in ids


def test_replay_controls_are_deterministic_and_persisted():
    session = client.post("/api/replay/start", json={"scenario_id": "mock_controls", "seed": 33}).json()["data"]
    session_id = session["session_id"]
    first_time = session["events"][0]["virtual_timestamp_ns"]
    sixth_time = session["events"][5]["virtual_timestamp_ns"]
    last_time = session["events"][-1]["virtual_timestamp_ns"]

    paused = client.post("/api/replay/pause", json={"session_id": session_id})
    assert paused.status_code == 200
    assert paused.json()["data"]["state"] == "paused"

    stepped = client.post("/api/replay/step", json={"session_id": session_id, "steps": 5})
    assert stepped.status_code == 200
    assert stepped.json()["data"]["state"] == "stepped"
    assert stepped.json()["data"]["current_timestamp_ns"] == sixth_time

    playing = client.post("/api/replay/play", json={"session_id": session_id})
    assert playing.status_code == 200
    assert playing.json()["data"]["state"] == "playing"
    assert playing.json()["data"]["current_timestamp_ns"] == sixth_time

    seek_start = client.post("/api/replay/seek", json={"session_id": session_id, "virtual_timestamp_ns": first_time})
    assert seek_start.status_code == 200
    assert seek_start.json()["data"]["current_timestamp_ns"] == first_time

    seek_end = client.post("/api/replay/seek", json={"session_id": session_id, "virtual_timestamp_ns": last_time})
    assert seek_end.status_code == 200
    assert seek_end.json()["data"]["current_timestamp_ns"] == last_time


def test_storage_status_counts_are_reported():
    status = client.get("/api/storage/status")
    assert status.status_code == 200
    data = status.json()["data"]
    assert data["status"] == "ready"
    assert data["audit_events"] >= 1
    assert data["capability_snapshots"] >= 1
    assert "point_in_time_snapshots" in data
    assert "feature_versions" in data
    assert "request_logs" in data
    assert "behavior_analysis_results" in data
    assert "behavior_memory_records" in data
    assert "behavior_benchmark_runs" in data


def test_capability_manifest_contains_preserved_features():
    caps = client.get("/api/system/features").json()["data"]["capabilities"]
    names = {c["name"] for c in caps}
    for required in ["ABIDES Synthetic Market Engine", "TimeProvider", "KillSwitch", "MarketDNA", "Dynamic Temporal Graph Memory", "Order Path Guard"]:
        assert required in names
    for required in ["Behavior Data Adapter", "Behavior Data Quality Engine", "Behavior Point-In-Time Guard"]:
        assert required in names
    assert "Behavior Real OHLCV Import" in names
    for required in ["Behavior Timeframe Synchronization Engine", "Behavior Causal Feature Whitelist"]:
        assert required in names
    for required in ["Candle Structure Intelligence", "Behavior Condition Classifier"]:
        assert required in names
    for required in ["Behavior Session Rhythm Engine", "Behavior Day-Of-Week Memory", "Behavior Stock DNA Summary"]:
        assert required in names
    for required in ["Behavior Pattern Memory Engine", "Behavior Similar-Day Replay Engine"]:
        assert required in names
    for required in ["Behavior Outcome Labeling Engine", "Behavior Failure Pattern Library", "Behavior Learning Trust Table"]:
        assert required in names
    for required in ["Behavior Decision Engine", "Behavior No-Trade Intelligence", "Behavior Human-Readable Reason Tree"]:
        assert required in names
    for required in ["Behavior Risk Sizing Engine", "Behavior Portfolio Exposure Control", "Behavior Daily Loss Cooldown Engine"]:
        assert required in names
    for required in ["Behavior Execution Simulation Engine", "Behavior No-Fill And Partial-Fill Model", "Behavior Slippage Impact Latency Model", "Execution Slippage Simulator"]:
        assert required in names
    assert "Behavior Frontend Panel Contract Map" in names
    assert "Behavior Replay Indicator Chart Validation" in names
    assert "Behavior Replay Indicator Matrix" in names
    assert "Behavior Matrix Decision Readiness" in names
    assert "Behavior Trade Lifecycle Simulation" in names
    assert "Behavior Lifecycle Scenario Comparison" in names
    for required in ["Behavior Walk-Forward Validation", "Behavior Out-Of-Sample Validation", "Behavior Benchmark Report Engine"]:
        assert required in names


def test_observability_records_request_ids_and_required_fields():
    response = client.get("/api/system/mode")
    assert response.status_code == 200
    assert response.headers["X-TradeVision-Request-Id"]
    assert response.headers["X-TradeVision-Run-Id"]

    status = client.get("/api/observability/status")
    assert status.status_code == 200
    data = status.json()["data"]
    assert data["log_format"] == "json"
    assert data["request_count"] >= 1
    for field in ["request_id", "run_id", "decision_id", "path", "latency_ms", "status_code"]:
        assert field in data["required_fields"]
    assert any(event["path"] == "/api/system/mode" for event in data["recent_events"])


def test_behavior_contract_lock_has_32_contracts_and_74_columns():
    spec = client.get("/api/v1/behavior/spec")
    assert spec.status_code == 200
    data = spec.json()["data"]
    assert data["live_trading_blocked"] is True
    assert len(data["layer_contracts"]) == 32
    assert len(data["output_columns"]) == 74
    assert data["universal_agreement_rule"] == (
        "A trade is allowed only when: signal strength + candle structure + level context + "
        "session rhythm + similar-history outcome + market regime + risk quality ALL agree. "
        "If they disagree, Trade Vision must say WAIT or NO TRADE."
    )
    assert data["stock_app_source_root"] == r"D:\Projects\trading-platforms\stock-app"

    columns = client.get("/api/v1/behavior/output-columns").json()["data"]
    assert len(columns) == 74
    assert columns[0]["name"] == "market_state"
    assert columns[-1]["name"] == "decision_audit_log"


def test_behavior_frontend_panel_map_binds_panels_to_contracts_and_endpoints():
    response = client.get("/api/v1/behavior/frontend/panel-map")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["map_version"] == "behavior-frontend-workspace.v0.23"
    assert result["workspace"] == "behavior"
    assert result["total_panels"] >= 25
    assert result["mock_panels"] >= 20
    panel_ids = {panel["panel_id"] for panel in result["panels"]}
    for required in {
        "universal_agreement",
        "risk_sizing",
        "execution_fill",
        "execution_costs",
        "pattern_memory",
        "failure_library",
        "lookahead_guard",
        "timeframe_sync",
        "causal_whitelist",
        "replay_indicator_chart_validation",
        "replay_indicator_matrix",
        "matrix_decision_readiness",
        "trade_lifecycle_simulation",
        "lifecycle_scenario_comparison",
        "lifecycle_evidence_drilldown",
        "tradeability_guidance",
    }:
        assert required in panel_ids
    for panel in result["panels"]:
        assert panel["title"]
        assert panel["contract_name"]
        assert panel["endpoint"].startswith("/api/")
        assert panel["output_fields"]
        assert panel["manifest_status"] in {"reserved", "mock", "beta", "production"}
        assert panel["fallback_state"] in {"loading", "mock", "reserved", "blocked", "offline"}
    assert any("Every panel must declare" in invariant for invariant in result["safety_invariants"])


def test_behavior_runtime_readiness_exposes_indicator_chart_replay_and_research_status():
    response = client.get("/api/v1/behavior/runtime/readiness")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["readiness_version"] == "behavior-runtime-readiness.v0.32"
    assert result["self_indicator_total"] == 71
    assert result["self_indicator_returned"] == 71
    assert result["pta_marker_total"] == 23
    assert result["total_output_groups"] == 94
    assert result["non_empty_sample_outputs"] == 59
    assert result["empty_no_signal_outputs"] == 12
    assert result["automated_indicator_tests_passed"] == 79
    assert result["automated_indicator_tests_skipped"] == 1
    assert result["indicator_output_ready"] is True
    assert result["chart_output_ready"] is True
    assert result["research_activity_ready"] is True
    assert result["replay_ready"] is True
    assert result["safe_mode"] is True
    assert result["live_trading_blocked"] is True
    assert {5173, 8765, 8010} <= set(result["browser_recommended_ports"])
    assert len(result["indicator_groups"]) == 94
    indicator_ids = {group["group_id"] for group in result["indicator_groups"]}
    assert {
        "si_sweep_inside_rr",
        "si_inside_candle_strategy",
        "si_ichi_trend_osc",
        "si_fmfm300",
    } <= indicator_ids
    assert all(gate["status"] == "pass" for gate in result["gates"])

    panel_ids = {panel["panel_id"] for panel in client.get("/api/v1/behavior/frontend/panel-map").json()["data"]["panels"]}
    assert "runtime_readiness" in panel_ids


def test_v060_indicator_registry_lock_preserves_94_indicator_contracts():
    response = client.get("/api/v1/behavior/indicators/registry")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["registry_version"] == "behavior-indicator-registry-lock.v0.60"
    assert result["self_indicator_count"] == 71
    assert result["pta_marker_count"] == 23
    assert result["total_output_groups"] == 94
    assert len(result["entries"]) == 94
    assert result["required_added_indicators_present"] is True
    assert result["proxy_probability_blocked"] is True
    assert result["all_entries_have_output_schema"] is True
    assert result["all_entries_have_warmup"] is True
    assert result["all_entries_have_pit_policy"] is True
    assert result["runtime_dependency_on_legacy_stock_app"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert all(gate["passed"] for gate in result["gates"])

    entries = {entry["indicator_id"]: entry for entry in result["entries"]}
    assert set(result["required_added_indicator_ids"]) == {
        "si_sweep_inside_rr",
        "si_inside_candle_strategy",
        "si_ichi_trend_osc",
        "si_fmfm300",
    }
    assert entries["si_sweep_inside_rr"]["minimum_bars"] == 50
    assert entries["si_sweep_inside_rr"]["confirmation_delay_bars"] == 1
    assert entries["si_inside_candle_strategy"]["minimum_bars"] == 200
    assert entries["si_ichi_trend_osc"]["minimum_bars"] == 52
    assert entries["si_fmfm300"]["minimum_bars"] == 100
    assert entries["si_fmfm300"]["uses_future_pivots"] is True
    assert entries["si_fmfm300"]["confirmation_delay_bars"] == 20
    assert all(entries[item]["live_trading_blocked"] is True for item in result["required_added_indicator_ids"])
    expected_timeframes = ["1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"]
    assert all(entry["timeframes_allowed"] == expected_timeframes for entry in result["entries"])

    panel_ids = {panel["panel_id"] for panel in client.get("/api/v1/behavior/frontend/panel-map").json()["data"]["panels"]}
    assert "indicator_registry_lock" in panel_ids


def test_v180_ind_ont_001_every_registry_indicator_carries_ontology_metadata():
    response = client.get("/api/v1/behavior/indicators/registry")
    assert response.status_code == 200
    entries = response.json()["data"]["entries"]
    assert len(entries) == 94
    assert all(entry["ontology_version"] == "indicator-ontology.v1" for entry in entries)
    assert all(entry["purpose"] for entry in entries)
    assert all(entry["category"] for entry in entries)
    assert all("confirmation_rules" in entry for entry in entries)
    assert all("conflict_rules" in entry for entry in entries)


def test_v180_ind_ont_002_rsi_is_exhaustion_not_breakout_strength():
    response = client.get("/api/v1/behavior/indicators/si_rsi_div/ontology")
    assert response.status_code == 200
    rsi = response.json()["data"]
    assert rsi["category"] == "exhaustion"
    assert "exhaustion" in rsi["purpose"].lower()
    assert "not standalone breakout strength" in rsi["purpose"].lower()
    assert any("resistance" in rule.lower() for rule in rsi["conflict_rules"])


def test_v180_ind_ont_003_category_and_family_can_differ_without_breaking_redundancy():
    registry = client.get("/api/v1/behavior/indicators/registry").json()["data"]
    rsi = next(entry for entry in registry["entries"] if entry["indicator_id"] == "si_rsi_div")
    assert rsi["family"] == "momentum"
    assert rsi["category"] == "exhaustion"

    redundancy = client.get("/api/v1/behavior/redundancy/audit/current").json()["data"]
    assert redundancy["redundancy_model_version"] == "behavior-redundancy-control.v0.63"
    assert any("exhaustion" in cluster["cluster_id"] for cluster in redundancy["clusters"])


def test_v180_ind_ont_004_list_defaults_are_not_shared_mutable_defaults():
    first = client.get("/api/v1/behavior/indicators/registry").json()["data"]["entries"][0]
    second = client.get("/api/v1/behavior/indicators/registry").json()["data"]["entries"][0]
    first["conflict_rules"].append("test mutation")
    assert "test mutation" not in second["conflict_rules"]


def test_v180_ind_ont_005_registry_count_and_growth_gate_remain_green():
    registry = client.get("/api/v1/behavior/indicators/registry").json()["data"]
    assert registry["total_output_groups"] == 94
    assert len(registry["entries"]) == 94
    assert all(gate["passed"] for gate in registry["gates"])


def test_v180_ind_ont_006_unclassified_indicator_is_safe_explanation_only():
    registry = client.get("/api/v1/behavior/indicators/registry").json()["data"]
    unclassified = next(entry for entry in registry["entries"] if entry["category"] == "unclassified")
    assert unclassified["used_for_probability"] is False
    assert unclassified["usable_for_explanation"] is True
    assert "unknown ontology" in " ".join(unclassified["false_positive_conditions"]).lower()


def test_v180_ind_arb_009_confirmation_delay_reduces_late_indicator_vote_weight():
    response = client.post(
        "/api/v1/behavior/indicators/lag-vote",
        json={"symbol": "TV180", "indicator_id": "si_macd_ta", "raw_vote": 1.0},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    vote = data["vote"]
    assert vote["confirmation_delay_bars"] == 4
    assert vote["lag_weight"] == 0.2
    assert vote["delay_adjusted_vote"] == 0.2
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "IND-ARB-009")["passed"] is True


def test_v180_ind_arb_010_zero_delay_structural_signal_outranks_four_bar_macd():
    fast = client.post(
        "/api/v1/behavior/indicators/lag-vote",
        json={"symbol": "TV180", "indicator_id": "si_inside_out", "raw_vote": 1.0},
    ).json()["data"]["vote"]
    slow = client.post(
        "/api/v1/behavior/indicators/lag-vote",
        json={"symbol": "TV180", "indicator_id": "si_macd_ta", "raw_vote": 1.0},
    ).json()["data"]["vote"]
    assert fast["confirmation_delay_bars"] == 0
    assert fast["delay_adjusted_vote"] > slow["delay_adjusted_vote"]
    assert fast["can_promote_wait_to_watch"] is True
    assert slow["can_promote_wait_to_watch"] is False


def test_v180_ind_arb_011_late_confirmation_cannot_promote_watch_to_paper_alone():
    response = client.post(
        "/api/v1/behavior/indicators/lag-vote",
        json={"symbol": "TV180", "indicator_id": "si_macd_ta", "raw_vote": 1.0, "current_decision_band": "WATCH"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["vote"]["can_promote_watch_to_paper"] is False
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "IND-ARB-011")["passed"] is True


def test_v180_ind_arb_012_stale_confirmation_creates_warning_not_confidence():
    response = client.post(
        "/api/v1/behavior/indicators/lag-vote",
        json={"symbol": "TV180", "indicator_id": "si_fmfm300", "raw_vote": 1.0},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["vote"]["stale_confirmation_warning"] is True
    assert data["vote"]["can_promote_wait_to_watch"] is False
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "IND-ARB-012")["passed"] is True

    summary = client.get("/api/v1/behavior/indicators/intelligence-summary/TV180").json()["data"]
    assert summary["summary_version"] == "indicator-intelligence-summary.v1.80"
    assert summary["live_trading_blocked"] is True


def _indicator_label_bar(symbol: str, timestamp_ns: int, sequence_number: int, open_price: float, high: float, low: float, close: float) -> dict:
    return {
        "symbol": symbol,
        "timeframe": "1m",
        "timestamp_ns": timestamp_ns,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1000,
        "source": "mock",
        "sequence_number": sequence_number,
    }


def test_v181_ind_rel_001_signal_label_waits_until_future_horizon_completes():
    signal_time = ns_ist(2026, 6, 30, 9, 15)
    bars = [
        _indicator_label_bar("TV181", signal_time + 60_000_000_000, 1, 100, 101, 99, 100.5),
        _indicator_label_bar("TV181", signal_time + 120_000_000_000, 2, 100.5, 101.5, 99.5, 101),
    ]
    response = client.post(
        "/api/v1/behavior/indicators/reliability/label-signal",
        json={
            "symbol": "TV181",
            "indicator_id": "si_inside_out",
            "signal_time_ns": signal_time,
            "entry_price": 100,
            "stop_price": 98,
            "target_price": 104,
            "horizon_candles": 5,
            "post_signal_bars": bars,
        },
    )
    assert response.status_code == 200
    label = response.json()["data"]
    assert label["label_status"] == "pending"
    assert label["counted_as_win"] is False
    assert label["counted_in_reliability"] is False
    assert label["no_future_leakage"] is True


def test_v181_ind_rel_002_same_bar_target_stop_collision_uses_conservative_stop_first():
    signal_time = ns_ist(2026, 6, 30, 9, 15)
    bars = [
        _indicator_label_bar("TV181", signal_time + 60_000_000_000, 1, 100, 105, 97, 101),
        _indicator_label_bar("TV181", signal_time + 120_000_000_000, 2, 101, 102, 99, 100),
        _indicator_label_bar("TV181", signal_time + 180_000_000_000, 3, 100, 101, 99, 100.2),
    ]
    label = client.post(
        "/api/v1/behavior/indicators/reliability/label-signal",
        json={
            "symbol": "TV181",
            "indicator_id": "si_inside_out",
            "signal_time_ns": signal_time,
            "entry_price": 100,
            "stop_price": 98,
            "target_price": 104,
            "horizon_candles": 3,
            "post_signal_bars": bars,
        },
    ).json()["data"]
    assert label["label_status"] == "complete"
    assert label["same_bar_ambiguous"] is True
    assert label["conservative_stop_first_used"] is True
    assert label["outcome_label"] == "SL_HIT"
    assert label["counted_as_failure"] is True


def test_v181_ind_rel_003_low_sample_bayesian_shrinkage_blocks_probability():
    report = client.get("/api/v1/behavior/indicators/si_macd_ta/reliability/LOW_SAMPLE?low_sample=true").json()["data"]
    assert report["reliability_version"] == "indicator-reliability-memory.v1.83"
    assert report["sample_count"] < report["minimum_sample_size"]
    assert report["minimum_sample_pass"] is False
    assert report["reliability_state"] == "low_evidence"
    assert report["reliability_multiplier_for_lag_vote"] == 0.5
    assert report["used_for_probability"] is False
    assert report["live_trading_blocked"] is True
    assert next(gate for gate in report["gates"] if gate["gate_id"] == "IND-REL-002")["passed"] is False


def test_v181_ind_rel_004_per_stock_reliability_differs_by_symbol():
    reliance = client.get("/api/v1/behavior/indicators/si_inside_out/reliability/RELIANCE").json()["data"]
    infya = client.get("/api/v1/behavior/indicators/si_inside_out/reliability/INFYA").json()["data"]
    assert reliance["sample_count"] != infya["sample_count"] or reliance["per_stock_reliability"] != infya["per_stock_reliability"]
    assert reliance["symbol"] == "RELIANCE"
    assert infya["symbol"] == "INFYA"
    assert reliance["order_routing_enabled"] is False
    assert infya["order_routing_enabled"] is False


def test_v181_ind_rel_005_reliability_feeds_lag_vote_multiplier_research_only():
    report = client.get("/api/v1/behavior/indicators/si_macd_ta/reliability/RELIANCE").json()["data"]
    vote = report["lag_vote_preview"]
    assert vote["indicator_id"] == "si_macd_ta"
    assert vote["confirmation_delay_bars"] == 4
    assert vote["delay_adjusted_vote"] <= round(report["reliability_multiplier_for_lag_vote"] * 0.2, 6)
    assert vote["can_promote_watch_to_paper"] is False
    assert report["used_for_probability"] is False
    assert report["trade_allowed"] is False


def test_v181_ind_rel_006_quarantine_on_ood_or_regime_shift_blocks_reliability():
    report = client.get("/api/v1/behavior/indicators/si_inside_out/reliability/RELIANCE?ood=true&regime_shift=true").json()["data"]
    assert report["reliability_state"] == "quarantined"
    assert report["ood_quarantine_required"] is True
    assert report["regime_shift_quarantine_required"] is True
    assert report["reliability_multiplier_for_lag_vote"] == 0.5
    assert "quarantine" in report["quarantine_reason"].lower()
    assert next(gate for gate in report["gates"] if gate["gate_id"] == "IND-REL-005")["passed"] is False


def test_v181_ind_rel_007_reciprocal_warning_surfaces_reliably_wrong_indicator():
    report = client.get("/api/v1/behavior/indicators/si_macd_ta/reliability/TVFAIL").json()["data"]
    assert report["reciprocal_signal_warning"] is True
    assert report["reciprocal_signal_ratio"] >= 0.55
    assert report["feeds_reciprocal_signal_detector"] is True
    assert next(gate for gate in report["gates"] if gate["gate_id"] == "IND-REL-004")["passed"] is False


def test_v181_ind_rel_008_intelligence_summary_includes_reliability_preview():
    summary = client.get("/api/v1/behavior/indicators/intelligence-summary/RELIANCE").json()["data"]
    preview = summary["reliability_preview"]
    assert preview["reliability_version"] == "indicator-reliability-memory.v1.83"
    assert preview["minimum_sample_pass"] in {True, False}
    assert preview["used_for_probability"] is False
    assert preview["live_trading_blocked"] is True


def test_v182_timeframe_contract_includes_30m_and_4h_across_registry_runtime_and_mtf():
    expected = ["1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"]
    registry = client.get("/api/v1/behavior/indicators/registry").json()["data"]
    assert all(entry["timeframes_allowed"] == expected for entry in registry["entries"])

    runtime = client.get("/api/v1/behavior/features/seven-timeframe/current").json()["data"]
    assert runtime["required_timeframes"] == expected
    assert [row["timeframe"] for row in runtime["closed_bar_records"]] == expected
    assert runtime["total_timeframe_indicator_slots"] == registry["total_output_groups"] * len(expected)
    assert runtime["trade_allowed"] is False
    assert runtime["order_routing_enabled"] is False
    assert runtime["live_trading_blocked"] is True

    mtf = client.get("/api/v1/behavior/timeframes/conflict/current?symbol=RELIANCE&primary_timeframe=5m").json()["data"]
    assert {row["timeframe"] for row in mtf["seven_timeframe_matrix"]} == set(expected)


def test_v182_timeframe_duration_guard_accepts_30m_and_4h_without_leakage():
    start = ns_ist(2026, 6, 30, 9, 15)
    for timeframe, duration_ns in {"30m": 30 * 60_000_000_000, "4H": 4 * 60 * 60_000_000_000}.items():
        response = client.post(
            "/api/v1/behavior/guards/point-in-time",
            json={
                "source_timeframe": timeframe,
                "decision_time_ns": start + duration_ns,
                "execution_time_ns": start + duration_ns + 1,
                "series": {
                    "symbol": "TV182",
                    "timeframe": timeframe,
                    "bars": [
                        {
                            "symbol": "TV182",
                            "timeframe": timeframe,
                            "timestamp_ns": start,
                            "open": 100,
                            "high": 101,
                            "low": 99,
                            "close": 100.5,
                            "volume": 1000,
                            "source": "mock",
                            "sequence_number": 1,
                        }
                    ],
                },
            },
        )
        assert response.status_code == 200
        result = response.json()["data"]
        assert result["source_timeframe"] == timeframe
        assert result["timeframe_duration_ns"] == duration_ns
        assert result["passed"] is True
        assert result["future_bar_blocked"] == 0
        assert result["incomplete_candle_blocked"] == 0


def test_v182_indicator_reliability_drilldown_accepts_30m_and_4h_research_only():
    for timeframe in ("30m", "4H"):
        report = client.get(f"/api/v1/behavior/indicators/si_macd_ta/reliability/RELIANCE?timeframe={timeframe}").json()["data"]
        assert report["timeframe"] == timeframe
        assert report["purpose"]
        assert report["category"]
        assert report["confirmation_delay_bars"] == report["lag_vote_preview"]["confirmation_delay_bars"]
        assert report["lag_weight"] == report["lag_vote_preview"]["lag_weight"]
        assert report["used_for_probability"] is False
        assert report["trade_allowed"] is False
        assert report["order_routing_enabled"] is False
        assert report["live_trading_blocked"] is True
        assert report["no_future_leakage"] is True


def test_v182_frontend_panel_map_exposes_indicator_reliability_drilldown():
    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["indicator_reliability_drilldown_v182"]
    assert panel["contract_name"] == "IndicatorReliabilityReport"
    assert panel["endpoint"] == "/api/v1/behavior/indicators/si_macd_ta/reliability/RELIANCE"
    assert panel["manifest_status"] == "mock"
    assert {"purpose", "category", "confirmation_delay_bars", "lag_weight", "sample_count", "reliability_state"} <= set(panel["output_fields"])


def test_v182_capability_manifest_tracks_full_timeframe_expansion():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Full Timeframe Contract Expansion")
    assert feature["status"] == "mock"
    assert "SevenTimeframeFeatureRuntimeReport" in feature["required_data_contracts"]
    assert "IndicatorReliabilityReport" in feature["required_data_contracts"]
    assert "TV-V182-005" in feature["promotion_gates"]


def _save_v183_indicator_history(symbol: str, indicator_id: str = "si_inside_out", timeframe: str = "1m", index: int = 0, horizon: int = 3, complete: bool = True) -> dict:
    signal_time = ns_ist(2026, 6, 30, 9, 15) + index * 60_000_000_000
    bars = [
        _indicator_label_bar(symbol, signal_time + 60_000_000_000, 1, 100, 105, 99.2, 104.5),
        _indicator_label_bar(symbol, signal_time + 120_000_000_000, 2, 104.5, 105.2, 103.5, 104.8),
        _indicator_label_bar(symbol, signal_time + 180_000_000_000, 3, 104.8, 105.5, 104.0, 105.1),
    ]
    if not complete:
        bars = bars[:1]
    response = client.post(
        "/api/v1/behavior/indicators/reliability/save-history",
        json={
            "symbol": symbol,
            "indicator_id": indicator_id,
            "timeframe": timeframe,
            "signal_direction": "bullish",
            "signal_time_ns": signal_time,
            "decision_time_ns": signal_time,
            "session_phase": "opening_drive",
            "regime_id": "trend_open",
            "source_snapshot_id": f"snapshot-{symbol}-{index}",
            "source_snapshot_hash": f"hash-{symbol}-{index}",
            "feature_manifest_version": "nine-candle-feature-manifest.v1",
            "signal_value": 1.0,
            "signal_strength": 0.82,
            "missing_mask": False,
            "label_request": {
                "symbol": symbol,
                "indicator_id": indicator_id,
                "timeframe": timeframe,
                "signal_direction": "bullish",
                "signal_time_ns": signal_time,
                "entry_price": 100,
                "stop_price": 98,
                "target_price": 104,
                "horizon_candles": horizon,
                "post_signal_bars": bars,
            },
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_v183_persistent_indicator_signal_history_save_and_readback():
    symbol = "TV183SAVE"
    record = _save_v183_indicator_history(symbol, index=1)
    assert record["history_version"] == "indicator-signal-history-store.v1.83"
    assert record["symbol"] == symbol
    assert record["label"]["label_status"] == "complete"
    assert record["counted_in_reliability"] is True
    assert record["trade_allowed"] is False
    assert record["order_routing_enabled"] is False
    assert record["live_trading_blocked"] is True

    summary = client.get(f"/api/v1/behavior/indicators/si_inside_out/signal-history/{symbol}?timeframe=1m").json()["data"]
    assert summary["history_version"] == "indicator-signal-history-store.v1.83"
    assert summary["record_count"] >= 1
    assert summary["counted_record_count"] >= 1
    assert summary["storage_backed"] is True
    assert summary["no_future_leakage"] is True


def test_v183_reliability_prefers_persisted_history_over_fixture_fallback():
    symbol = "TV183PERSIST"
    for index in range(3):
        _save_v183_indicator_history(symbol, index=index)
    report = client.get(f"/api/v1/behavior/indicators/si_inside_out/reliability/{symbol}?timeframe=1m").json()["data"]
    assert report["reliability_version"] == "indicator-reliability-memory.v1.83"
    assert report["history_source"] == "persistent"
    assert report["fixture_fallback_used"] is False
    assert report["persisted_history_count"] >= 3
    assert report["sample_count"] >= 3
    assert report["minimum_sample_pass"] is False
    assert report["used_for_probability"] is False
    assert report["trade_allowed"] is False


def test_v183_pending_indicator_history_is_stored_but_not_counted():
    symbol = "TV183PEND"
    _save_v183_indicator_history(symbol, index=0, horizon=3, complete=False)
    summary = client.get(f"/api/v1/behavior/indicators/si_inside_out/signal-history/{symbol}?timeframe=1m").json()["data"]
    assert summary["record_count"] >= 1
    assert summary["pending_record_count"] >= 1
    assert summary["counted_record_count"] == 0
    assert next(gate for gate in summary["gates"] if gate["gate_id"] == "IND-HIST-002")["passed"] is True


def test_v183_reliability_drilldown_returns_trader_summary_and_history_packet():
    symbol = "TV183DRILL"
    _save_v183_indicator_history(symbol, index=0)
    drilldown = client.get(f"/api/v1/behavior/indicators/si_inside_out/reliability-drilldown/{symbol}?timeframe=1m").json()["data"]
    assert drilldown["drilldown_version"] == "indicator-reliability-drilldown.v1.83"
    assert drilldown["reliability"]["history_source"] == "persistent"
    assert drilldown["history"]["storage_backed"] is True
    assert "cannot approve trades" in drilldown["trader_summary"]
    assert drilldown["order_routing_enabled"] is False
    assert drilldown["live_trading_blocked"] is True


def test_v183_persistent_history_accepts_30m_and_4h_without_routing():
    for timeframe in ("30m", "4H"):
        symbol = f"TV183{timeframe.replace('H', 'HOUR')}"
        record = _save_v183_indicator_history(symbol, timeframe=timeframe)
        assert record["timeframe"] == timeframe
        assert record["order_routing_enabled"] is False
        summary = client.get(f"/api/v1/behavior/indicators/si_inside_out/signal-history/{symbol}?timeframe={timeframe}").json()["data"]
        assert summary["timeframe"] == timeframe
        assert summary["record_count"] >= 1


def test_v183_panel_map_and_capability_manifest_track_persistent_indicator_history():
    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    assert panels["indicator_signal_history_drilldown_v183"]["contract_name"] == "IndicatorSignalHistorySummary"
    assert panels["indicator_reliability_drilldown_v183"]["endpoint"] == "/api/v1/behavior/indicators/si_macd_ta/reliability-drilldown/RELIANCE"

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Persistent Indicator Signal History")
    assert feature["status"] == "mock"
    assert "IndicatorSignalHistoryRecord" in feature["required_data_contracts"]
    assert "TV-V183-006" in feature["promotion_gates"]


def test_v184_current_indicator_signal_ingestion_writes_pending_history_only():
    symbol = "TV184INGEST"
    result = client.post(
        "/api/v1/behavior/indicators/reliability/ingest-current",
        json={"symbol": symbol, "timeframe": "1m", "max_records": 5},
    ).json()["data"]
    assert result["ingest_version"] == "indicator-signal-history-ingestion.v1.84"
    assert result["symbol"] == symbol
    assert result["saved_record_count"] == 5
    assert result["pending_record_count"] == 5
    assert result["counted_record_count"] == 0
    assert result["closed_candle_only"] is True
    assert result["no_future_leakage"] is True
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert all(record["label"]["label_status"] == "pending" for record in result["saved_records"])
    assert next(gate for gate in result["gates"] if gate["gate_id"] == "IND-INGEST-002")["passed"] is True


def test_v184_current_ingestion_is_idempotent_for_same_snapshot_signal_time_and_horizon():
    symbol = "TV184IDEMP"
    first = client.post(
        "/api/v1/behavior/indicators/reliability/ingest-current",
        json={"symbol": symbol, "timeframe": "1m", "max_records": 3},
    ).json()["data"]
    second = client.post(
        "/api/v1/behavior/indicators/reliability/ingest-current",
        json={"symbol": symbol, "timeframe": "1m", "max_records": 3},
    ).json()["data"]
    assert [record["history_id"] for record in first["saved_records"]] == [record["history_id"] for record in second["saved_records"]]
    indicator_id = first["saved_records"][0]["indicator_id"]
    history = client.get(f"/api/v1/behavior/indicators/{indicator_id}/signal-history/{symbol}?timeframe=1m").json()["data"]
    matching = [record for record in history["records"] if record["history_id"] == first["saved_records"][0]["history_id"]]
    assert len(matching) == 1
    assert history["counted_record_count"] == 0


def test_v184_reliability_keeps_fixture_fallback_when_only_pending_ingested_rows_exist():
    symbol = "TV184PENDING"
    result = client.post(
        "/api/v1/behavior/indicators/reliability/ingest-current",
        json={"symbol": symbol, "timeframe": "1m", "max_records": 1},
    ).json()["data"]
    indicator_id = result["saved_records"][0]["indicator_id"]
    report = client.get(f"/api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}?timeframe=1m").json()["data"]
    assert report["history_source"] == "fixture"
    assert report["fixture_fallback_used"] is True
    assert report["persisted_history_count"] >= 1
    assert report["used_for_probability"] is False
    assert report["trade_allowed"] is False


def test_v184_panel_map_and_capability_manifest_track_current_signal_ingestion():
    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    assert panels["indicator_signal_history_ingestion_v184"]["contract_name"] == "IndicatorSignalHistoryIngestCurrentReport"
    assert panels["indicator_signal_history_ingestion_v184"]["endpoint"] == "/api/v1/behavior/indicators/reliability/ingest-current"

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Indicator Signal History Ingestion")
    assert feature["status"] == "mock"
    assert "IndicatorSignalHistoryIngestCurrentReport" in feature["required_data_contracts"]
    assert "TV-V184-005" in feature["promotion_gates"]


def _v185_completion_payload(record: dict, *, complete: bool = True, collision: bool = False) -> dict:
    signal_time = int(record["signal_time_ns"])
    bearish = record["signal_direction"] == "bearish"
    if bearish:
        entry, stop, target = 100.0, 102.0, 96.0
        first = _indicator_label_bar(record["symbol"], signal_time + 60_000_000_000, 1, 100, 103 if collision else 101, 95, 96.5)
    else:
        entry, stop, target = 100.0, 98.0, 104.0
        first = _indicator_label_bar(record["symbol"], signal_time + 60_000_000_000, 1, 100, 105, 97 if collision else 99, 104.5)
    bars = [
        first,
        _indicator_label_bar(record["symbol"], signal_time + 120_000_000_000, 2, 101, 102, 99, 101),
        _indicator_label_bar(record["symbol"], signal_time + 180_000_000_000, 3, 101, 102, 99, 101),
    ]
    if not complete:
        bars = bars[:1]
    return {
        "symbol": record["symbol"],
        "indicator_id": record["indicator_id"],
        "timeframe": record["timeframe"],
        "history_id": record["history_id"],
        "entry_price": entry,
        "stop_price": stop,
        "target_price": target,
        "post_signal_bars": bars,
    }


def test_v185_complete_pending_indicator_history_counts_completed_future_horizon():
    symbol = "TV185COMPLETE"
    ingest = client.post(
        "/api/v1/behavior/indicators/reliability/ingest-current",
        json={"symbol": symbol, "timeframe": "1m", "max_records": 1},
    ).json()["data"]
    record = ingest["saved_records"][0]
    completion = client.post(
        "/api/v1/behavior/indicators/reliability/complete-pending",
        json=_v185_completion_payload(record),
    ).json()["data"]
    assert completion["completion_version"] == "indicator-signal-history-completion.v1.85"
    assert completion["scanned_pending_count"] == 1
    assert completion["completed_count"] == 1
    assert completion["still_pending_count"] == 0
    assert completion["completed_records"][0]["history_id"] == record["history_id"]
    assert completion["completed_records"][0]["label"]["label_status"] == "complete"
    assert completion["completed_records"][0]["counted_in_reliability"] is True
    assert completion["trade_allowed"] is False
    assert completion["order_routing_enabled"] is False
    assert completion["live_trading_blocked"] is True

    report = client.get(f"/api/v1/behavior/indicators/{record['indicator_id']}/reliability/{symbol}?timeframe=1m").json()["data"]
    assert report["history_source"] == "persistent"
    assert report["fixture_fallback_used"] is False
    assert report["sample_count"] >= 1
    assert report["trade_allowed"] is False


def test_v185_incomplete_future_horizon_stays_pending_and_uncounted():
    symbol = "TV185PENDING"
    ingest = client.post(
        "/api/v1/behavior/indicators/reliability/ingest-current",
        json={"symbol": symbol, "timeframe": "1m", "max_records": 1},
    ).json()["data"]
    record = ingest["saved_records"][0]
    completion = client.post(
        "/api/v1/behavior/indicators/reliability/complete-pending",
        json=_v185_completion_payload(record, complete=False),
    ).json()["data"]
    assert completion["completed_count"] == 0
    assert completion["still_pending_count"] == 1
    assert completion["still_pending_records"][0]["counted_in_reliability"] is False

    history = client.get(f"/api/v1/behavior/indicators/{record['indicator_id']}/signal-history/{symbol}?timeframe=1m").json()["data"]
    assert history["pending_record_count"] >= 1
    assert history["counted_record_count"] == 0


def test_v185_same_bar_target_stop_collision_uses_conservative_stop_first():
    symbol = "TV185COLLISION"
    ingest = client.post(
        "/api/v1/behavior/indicators/reliability/ingest-current",
        json={"symbol": symbol, "timeframe": "1m", "max_records": 1},
    ).json()["data"]
    record = ingest["saved_records"][0]
    completion = client.post(
        "/api/v1/behavior/indicators/reliability/complete-pending",
        json=_v185_completion_payload(record, collision=True),
    ).json()["data"]
    label = completion["completed_records"][0]["label"]
    assert label["label_status"] == "complete"
    assert label["same_bar_ambiguous"] is True
    assert label["conservative_stop_first_used"] is True
    assert label["outcome_label"] == "SL_HIT"
    assert completion["completed_records"][0]["counted_in_reliability"] is True


def test_v185_panel_map_and_capability_manifest_track_pending_completion():
    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    assert panels["indicator_pending_outcome_completion_v185"]["contract_name"] == "IndicatorSignalHistoryCompletePendingReport"
    assert panels["indicator_pending_outcome_completion_v185"]["endpoint"] == "/api/v1/behavior/indicators/reliability/complete-pending"

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Indicator Pending Outcome Completion")
    assert feature["status"] == "mock"
    assert "IndicatorSignalHistoryCompletePendingReport" in feature["required_data_contracts"]
    assert "TV-V185-005" in feature["promotion_gates"]


def test_9c_001_feature_manifest_discovers_all_registry_indicators():
    registry = client.get("/api/v1/behavior/indicators/registry").json()["data"]
    manifest = client.get("/api/v1/behavior/9c-dna/feature-manifest").json()["data"]
    assert manifest["feature_manifest_version"] == "nine-candle-feature-manifest.v1"
    assert manifest["feature_count"] == registry["total_output_groups"]
    assert manifest["vector_dimension"] == registry["total_output_groups"]
    assert [entry["feature_index"] for entry in manifest["entries"]] == list(range(registry["total_output_groups"]))
    assert len({entry["feature_id"] for entry in manifest["entries"]}) == registry["total_output_groups"]


def test_9c_002_feature_manifest_integrity_locks_normalization_and_missing_policy():
    report = client.get("/api/v1/behavior/9c-dna/feature-manifest/integrity").json()["data"]
    assert report["integrity_version"] == "9c-feature-manifest-integrity.v1"
    assert report["feature_count"] == report["vector_dimension"] == 94
    assert report["wait_required"] is False
    assert report["failure_reasons"] == []
    checks = report["checks"]
    assert checks["feature_count_matches_vector_dimension"] is True
    assert checks["feature_indices_contiguous"] is True
    assert checks["feature_ids_unique"] is True
    assert checks["normalization_methods_allowed"] is True
    assert checks["bounded_indicators_not_zscore"] is True
    assert checks["missing_masks_enabled"] is True
    assert checks["missing_defaults_are_not_zero_signals"] is True
    assert checks["low_variance_is_not_missing"] is True
    assert checks["masked_cosine_required"] is True
    assert checks["probability_disabled_until_promotion"] is True
    assert "bounded_minmax" in report["normalization_methods"]
    assert "rolling_zscore_clipped" in report["normalization_methods"]
    assert report["probability_enabled_count"] == 0
    assert report["missing_mask_enabled_count"] == 94
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_9c_002b_feature_manifest_entries_expose_policy_fields():
    manifest = client.get("/api/v1/behavior/9c-dna/feature-manifest").json()["data"]
    rows = manifest["entries"]
    rsi_rows = [row for row in rows if "rsi" in row["feature_id"].lower()]
    assert rsi_rows
    assert all(row["normalization_method"] == "bounded_minmax" for row in rsi_rows)
    assert all(row["missing_policy"] == "masked_missing_not_zero_signal" for row in rows)
    assert all(row["low_variance_policy"] == "low_variance_flag_not_missing" for row in rows)
    assert all(row["similarity_policy"] == "masked_cosine_min_overlap_0_70" for row in rows)
    assert all(row["normalization_formula"] for row in rows)


def test_9c_003_019_vector_uses_missing_mask_not_zero_signal():
    result = client.get("/api/v1/behavior/9c-dna/current/RELIANCE?timeframe=1m").json()["data"]
    assert result["closed_candle_only"] is True
    assert result["future_leakage_detected"] is False
    assert result["vector_dimension"] == len(result["feature_values"]) == len(result["feature_missing_mask"])
    assert any(result["feature_missing_mask"])

    alignment = client.get("/api/v1/behavior/9c-dna/indicator-alignment/RELIANCE?timeframe=1m").json()["data"]
    missing_rows = [row for row in alignment if row["missing_reason"]]
    assert missing_rows
    assert any(value is None for value in missing_rows[0]["last_9_values"])
    assert "missing" in missing_rows[0]["last_9_signals"]


def test_9c_031_feature_vector_audit_proves_manifest_vector_integrity():
    audit = client.get("/api/v1/behavior/9c-dna/vector-audit/RELIANCE?timeframe=1m").json()["data"]
    assert audit["audit_version"] == "9c-feature-vector-audit.v1"
    assert audit["vector_length_pass"] is True
    assert audit["manifest_version_pass"] is True
    assert audit["feature_order_pass"] is True
    assert audit["finite_values_pass"] is True
    assert audit["normalized_range_pass"] is True
    assert audit["missing_mask_pass"] is True
    assert audit["probability_mask_pass"] is True
    assert audit["wait_required"] is False
    assert audit["failure_reasons"] == []
    assert audit["feature_value_count"] == audit["manifest_feature_count"] == audit["vector_dimension"]
    assert audit["missing_mask_count"] == audit["missing_value_count"]
    assert audit["live_trading_blocked"] is True


def test_9c_033_real_indicator_payload_is_normalized_without_changing_default(monkeypatch):
    from app.behavior import nine_candle_hybrid as hybrid
    from app.behavior.indicator_registry import build_indicator_registry_report

    entries = build_indicator_registry_report().entries
    promoted_ids = [entry.indicator_id for entry in entries if entry.indicator_id in hybrid.REAL_RUNTIME_PROMOTED_INDICATORS]
    first_index = next(index for index, entry in enumerate(entries) if entry.indicator_id == promoted_ids[0])
    second_index = next(index for index, entry in enumerate(entries) if entry.indicator_id == promoted_ids[1])

    def fake_outputs(candles, indicator_ids):
        assert indicator_ids == promoted_ids
        outputs = {
            promoted_ids[0]: {"value": [10, 20, 30, 40, 50, 60, 70, 80, 90]},
            promoted_ids[1]: {"state": ["bearish", "bearish", "neutral", "neutral", "neutral", "bullish", "bullish", "bullish", "bullish"]},
        }
        telemetry = [
            {"indicator_id": promoted_ids[0], "status": "computed", "latency_ms": 1.0, "output_present": True, "used_for_9c_vector": True, "error": None},
            {"indicator_id": promoted_ids[1], "status": "computed", "latency_ms": 1.0, "output_present": True, "used_for_9c_vector": True, "error": None},
        ] + [
            {"indicator_id": indicator_id, "status": "no_output", "latency_ms": 1.0, "output_present": False, "used_for_9c_vector": False, "error": None}
            for indicator_id in promoted_ids[2:]
        ]
        return outputs, telemetry

    monkeypatch.setattr(hybrid, "compute_real_indicator_outputs_with_telemetry", fake_outputs)
    default_result = client.get("/api/v1/behavior/9c-dna/current/RELIANCE?timeframe=1m").json()["data"]
    real_result = client.get("/api/v1/behavior/9c-dna/current/RELIANCE?timeframe=1m&use_real_indicators=true").json()["data"]
    assert default_result["source_snapshot_id"] == "mock-closed-9c-current"
    assert real_result["source_snapshot_id"] == "real-indicator-closed-9c-current"
    assert real_result["feature_values"][first_index] == 0.8
    assert real_result["feature_values"][second_index] == 1.0
    assert real_result["feature_missing_mask"][first_index] is False
    assert real_result["feature_missing_mask"][second_index] is False
    assert sum(real_result["feature_missing_mask"]) == real_result["vector_dimension"] - 2

    audit = client.get("/api/v1/behavior/9c-dna/vector-audit/RELIANCE?timeframe=1m&use_real_indicators=true").json()["data"]
    assert audit["wait_required"] is False
    assert audit["normalized_range_pass"] is True
    assert audit["missing_mask_count"] == audit["vector_dimension"] - 2
    assert audit["promoted_runtime_indicator_count"] == len(promoted_ids)
    assert audit["real_runtime_computed_count"] == 2
    assert audit["real_runtime_masked_count"] == len(promoted_ids) - 2
    assert audit["non_promoted_masked_count"] == len(entries) - len(promoted_ids)

    alignment = client.get("/api/v1/behavior/9c-dna/indicator-alignment/RELIANCE?timeframe=1m&use_real_indicators=true").json()["data"]
    first_row = next(row for row in alignment if row["indicator_id"] == promoted_ids[0])
    second_row = next(row for row in alignment if row["indicator_id"] == promoted_ids[1])
    masked_row = next(row for row in alignment if row["indicator_id"] not in promoted_ids)
    assert first_row["manifest_slot"] == first_index
    assert second_row["manifest_slot"] == second_index
    assert first_row["source_mode"] == "real"
    assert second_row["source_mode"] == "real"
    assert first_row["runtime_status"] == "computed"
    assert second_row["runtime_status"] == "computed"
    assert first_row["normalized_from"] == "bounded_minmax"
    assert second_row["normalized_from"] == "bounded_minmax"
    assert first_row["raw_output_present"] is True
    assert second_row["raw_output_present"] is True
    assert first_row["explanation_only"] is True
    assert masked_row["source_mode"] == "masked"
    assert masked_row["runtime_status"] == "not_promoted"


def test_9c_034_real_indicator_failure_masks_outputs_without_false_zero(monkeypatch):
    from app.behavior import nine_candle_hybrid as hybrid

    def broken_outputs(candles, indicator_ids):
        raise ModuleNotFoundError("shared")

    monkeypatch.setattr(hybrid, "compute_real_indicator_outputs_with_telemetry", broken_outputs)
    result = client.get("/api/v1/behavior/9c-dna/current/RELIANCE?timeframe=1m&use_real_indicators=true").json()["data"]
    assert result["source_snapshot_id"] == "real-indicator-closed-9c-current"
    assert all(result["feature_missing_mask"])
    assert all(value == 0.0 for value in result["feature_values"])

    alignment = client.get("/api/v1/behavior/9c-dna/indicator-alignment/RELIANCE?timeframe=1m&use_real_indicators=true").json()["data"]
    assert alignment
    promoted_rows = [row for row in alignment if row["indicator_id"] in hybrid.REAL_RUNTIME_PROMOTED_INDICATORS]
    non_promoted_rows = [row for row in alignment if row["indicator_id"] not in hybrid.REAL_RUNTIME_PROMOTED_INDICATORS]
    assert promoted_rows
    assert non_promoted_rows
    assert all(row["missing_reason"] and "real indicator runtime unavailable" in row["missing_reason"] for row in promoted_rows)
    assert all(row["missing_reason"] == "indicator not yet promoted for local real-runtime 9C bridge" for row in non_promoted_rows)


def test_9c_runtime_003_real_indicator_runtime_exposes_per_indicator_telemetry():
    result = client.get("/api/v1/behavior/9c-dna/indicator-runtime/RELIANCE?timeframe=1m&use_real_indicators=true").json()["data"]
    assert result["use_real_indicators"] is True
    assert result["runtime_state"] == "real_indicator_runtime"
    assert len(result["indicator_telemetry"]) == result["selected_indicator_count"]
    assert result["selected_indicator_count"] == result["level_runtime_selected_count"]
    assert result["selected_indicator_ids"] == result["level_runtime_selected_ids"]
    assert set(result["level_runtime_selected_ids"]).issubset(set(result["vector_promoted_indicator_ids"]))
    assert result["vector_promoted_indicator_count"] == (
        result["level_runtime_selected_count"] + result["vector_promoted_not_level_selected_count"]
    )
    assert result["vector_promoted_not_level_selected_count"] > 0
    assert any("level-runtime selected" in note for note in result["runtime_scope_notes"])
    assert any("9C real-indicator vector path" in note for note in result["runtime_scope_notes"])
    assert result["indicator_telemetry_counts"]
    assert result["indicator_cache_hit_count"] + result["indicator_cache_miss_count"] == len(result["indicator_telemetry"])
    assert result["slow_indicator_count"] == len(result["slow_indicator_ids"])
    assert all("latency_ms" in row and "status" in row and "used_for_9c_vector" in row for row in result["indicator_telemetry"])
    assert all("cache_hit" in row and "source_latency_ms" in row for row in result["indicator_telemetry"])
    assert all(row["status"] in {"computed", "slow_warn", "slow_blocked", "no_output", "error"} for row in result["indicator_telemetry"])


def test_9c_runtime_006_coverage_accounts_for_all_manifest_slots_without_probability():
    result = client.get("/api/v1/behavior/9c-dna/indicator-runtime-coverage").json()["data"]
    assert result["coverage_version"] == "9c-indicator-runtime-coverage.v1"
    assert result["total_manifest_slots"] == len(result["coverage_rows"]) == 94
    assert result["self_indicator_slots"] == 71
    assert result["pta_marker_slots"] == 23
    assert result["vendor_self_registry_count"] == 71
    assert result["vendor_pta_registry_count"] == 23
    assert result["vendor_self_supported_count"] == 71
    assert result["vendor_pta_supported_count"] == 23
    assert result["runtime_promoted_count"] > 0
    assert result["supported_not_promoted_count"] == 94 - result["runtime_promoted_count"]
    assert result["adapter_missing_count"] == 0
    assert result["unsupported_count"] == 0
    assert result["probability_enabled_count"] == 0
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert [row["manifest_slot"] for row in result["coverage_rows"]] == list(range(94))
    assert all(row["probability_enabled"] is False for row in result["coverage_rows"])
    assert all(row["trade_allowed"] is False and row["order_routing_enabled"] is False for row in result["coverage_rows"])
    pta_rows = [row for row in result["coverage_rows"] if row["source"] == "pta_signal_markers"]
    promoted_rows = [row for row in result["coverage_rows"] if row["runtime_support_state"] == "promoted"]
    supported_rows = [row for row in result["coverage_rows"] if row["runtime_support_state"] == "supported_not_promoted"]
    fmfm_row = next(row for row in result["coverage_rows"] if row["indicator_id"] == "si_fmfm300")
    assert pta_rows and all(row["runtime_support_state"] == "supported_not_promoted" for row in pta_rows)
    assert all(row["vendor_present"] is True for row in pta_rows)
    assert all("pta_runtime_adapter_missing" not in row["blocking_reasons"] for row in pta_rows)
    assert promoted_rows and all("explanation_only_until_evidence_promotion" in row["blocking_reasons"] for row in promoted_rows)
    assert supported_rows and all("supported_but_not_promoted_for_9c_runtime" in row["blocking_reasons"] for row in supported_rows)
    assert fmfm_row["runtime_support_state"] == "promoted"
    assert fmfm_row["probability_enabled"] is False
    assert fmfm_row["trade_allowed"] is False
    assert fmfm_row["order_routing_enabled"] is False


def test_9c_runtime_007_pta_vendor_metadata_is_local_and_non_trading():
    from app.vendor.stock_app.shared.indicators.pta_signal_markers import PTA_SIGNAL_METADATA

    assert len(PTA_SIGNAL_METADATA) == 23
    assert sorted(PTA_SIGNAL_METADATA)[:3] == ["pta_amat", "pta_aroon_sig", "pta_chop"]
    result = client.get("/api/v1/behavior/9c-dna/indicator-runtime-coverage").json()["data"]
    pta_rows = [row for row in result["coverage_rows"] if row["source"] == "pta_signal_markers"]
    assert len(pta_rows) == 23
    assert all(row["probability_enabled"] is False for row in pta_rows)
    assert all(row["trade_allowed"] is False for row in pta_rows)
    assert all(row["order_routing_enabled"] is False for row in pta_rows)


def test_9c_runtime_004_indicator_promotion_default_masks_every_probability_path():
    result = client.get("/api/v1/behavior/9c-dna/indicator-promotion/RELIANCE?timeframe=1m").json()["data"]
    assert result["promotion_report_version"] == "9c-indicator-promotion-gates.v1"
    assert result["use_real_indicators"] is False
    assert result["runtime_state"] == "mock_default"
    assert result["total_indicators"] == len(result["promotion_rows"]) == 94
    assert result["promoted_for_runtime_count"] > 0
    assert result["masked_count"] == result["total_indicators"]
    assert result["explanation_only_count"] == 0
    assert result["probability_eligible_count"] == 0
    assert all(row["current_state"] == "masked" for row in result["promotion_rows"])
    assert all(row["probability_gate"] == "blocked" for row in result["promotion_rows"])
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_9c_runtime_005_indicator_promotion_opt_in_allows_explanation_not_probability(monkeypatch):
    from app.behavior import indicator_promotion_gates as gates

    promoted_ids = sorted(gates.REAL_RUNTIME_PROMOTED_INDICATORS)

    def fake_outputs(candles, indicator_ids):
        assert indicator_ids == promoted_ids
        telemetry = [
            {
                "indicator_id": indicator_id,
                "status": "computed",
                "latency_ms": 1.0,
                "output_present": True,
                "used_for_9c_vector": True,
                "error": None,
            }
            for indicator_id in indicator_ids
        ]
        return {indicator_id: {"value": [1, 2, 3]} for indicator_id in indicator_ids}, telemetry

    monkeypatch.setattr(gates, "compute_real_indicator_outputs_with_telemetry", fake_outputs)
    result = client.get(
        "/api/v1/behavior/9c-dna/indicator-promotion/PROMOGATE?timeframe=1m&use_real_indicators=true"
    ).json()["data"]
    promoted_rows = [row for row in result["promotion_rows"] if row["promoted_for_runtime"]]
    non_promoted_rows = [row for row in result["promotion_rows"] if not row["promoted_for_runtime"]]
    assert result["runtime_state"] == "real_indicator_runtime"
    assert len(promoted_rows) == result["promoted_for_runtime_count"] == len(promoted_ids)
    assert result["explanation_only_count"] == len(promoted_rows)
    assert result["probability_eligible_count"] == 0
    assert all(row["current_state"] == "explanation_only" for row in promoted_rows)
    assert all("probability_evidence_pending" in row["blocking_reasons"] for row in promoted_rows)
    assert all("registry_probability_disabled" in row["blocking_reasons"] for row in promoted_rows)
    assert all(row["current_state"] == "masked" for row in non_promoted_rows)
    assert all("not_promoted_for_local_runtime" in row["blocking_reasons"] for row in non_promoted_rows)
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_9c_032_feature_vector_audit_blocks_manifest_version_mismatch():
    audit = client.get(
        "/api/v1/behavior/9c-dna/vector-audit/RELIANCE"
        "?timeframe=1m&expected_feature_manifest_version=nine-candle-feature-manifest.v0"
    ).json()["data"]
    assert audit["manifest_version_pass"] is False
    assert audit["wait_required"] is True
    assert "feature_manifest_version_mismatch" in audit["failure_reasons"]


def test_9c_011_024_mock_model_caps_to_watch_and_blocks_routing():
    result = client.get("/api/v1/behavior/9c-dna/decision/RELIANCE?timeframe=1m").json()["data"]
    assert result["decision"] in {"WAIT", "WATCH"}
    assert result["model"]["model_version"] == "mock"
    assert result["model"]["usable_for_probability"] is False
    assert result["model"]["paper_candidate_allowed"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    gate_status = {gate["gate_id"]: gate["status"] for gate in result["hybrid_decision"]["safety_gates"]}
    assert gate_status["9C-G010"] == "wait"
    assert gate_status["9C-G011"] == "block"
    if gate_status["9C-G006"] == "wait" or gate_status["9C-G007"] == "wait":
        assert result["decision"] == "WAIT"


def test_9c_007_020_outcome_labeler_uses_horizons_and_conservative_intrabar_rule():
    response = client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={"setup_id": "9c-test", "symbol": "RELIANCE", "timeframe": "1m", "conservative_intrabar": True},
    )
    assert response.status_code == 200
    labels = response.json()["data"]
    assert [label["horizon_candles"] for label in labels] == [3, 5, 9, 12, 20]
    assert all(label["label_status"] == "complete" for label in labels)
    assert all(label["intrabar_ambiguity_rule"] == "conservative_stop_first" for label in labels)
    assert labels[0]["stop_first"] is True


def test_9c_035_saved_setup_starts_pending_without_future_labels():
    symbol = "PERSISTPENDING"
    response = client.post(
        "/api/v1/behavior/9c-dna/save-setup",
        json={"symbol": symbol, "timeframe": "1m", "source_snapshot_id": "pytest-pending"},
    )
    assert response.status_code == 200
    setup = response.json()["data"]
    assert setup["setup_id"] == "9c-persistpending-1m-current"
    assert setup["label_status"] == "pending"
    assert setup["label_count"] == 0
    assert setup["setup_hash"]
    assert setup["evidence_packet_hash"]
    assert setup["trade_allowed"] is False
    assert setup["order_routing_enabled"] is False
    assert setup["live_trading_blocked"] is True

    memory = client.get(f"/api/v1/behavior/9c-dna/setup-memory/{symbol}?timeframe=1m").json()["data"]
    assert memory["memory_version"] == "9c-setup-outcome-memory.v1"
    assert memory["setup_count"] >= 1
    assert memory["pending_setup_count"] >= 1
    assert memory["label_count"] == 0
    assert memory["future_label_before_completion_blocked"] is True
    assert memory["labels_by_setup"][setup["setup_id"]] == []


def test_9c_036_labeling_saved_setup_persists_five_deterministic_horizons():
    symbol = "PERSISTCOMPLETE"
    setup = client.post(
        "/api/v1/behavior/9c-dna/save-setup",
        json={"symbol": symbol, "timeframe": "1m", "source_snapshot_id": "pytest-complete"},
    ).json()["data"]
    first = client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={"setup_id": setup["setup_id"], "symbol": symbol, "timeframe": "1m", "conservative_intrabar": True},
    ).json()["data"]
    second = client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={"setup_id": setup["setup_id"], "symbol": symbol, "timeframe": "1m", "conservative_intrabar": True},
    ).json()["data"]
    assert [label["horizon_candles"] for label in first] == [3, 5, 9, 12, 20]
    assert [label["label_hash"] for label in first] == [label["label_hash"] for label in second]
    assert all(label["label_status"] == "complete" for label in first)
    assert first[0]["outcome_label"] == "SL_HIT"
    assert first[1]["outcome_label"] == "SL_HIT"
    assert first[2]["outcome_label"] == "TARGET_HIT"
    assert all(label["future_leakage_detected"] is False for label in first)

    memory = client.get(f"/api/v1/behavior/9c-dna/setup-memory/{symbol}?timeframe=1m").json()["data"]
    assert memory["complete_setup_count"] >= 1
    assert memory["label_count"] == 5
    assert len(memory["labels_by_setup"][setup["setup_id"]]) == 5
    saved = next(item for item in memory["setups"] if item["setup_id"] == setup["setup_id"])
    assert saved["label_status"] == "complete"
    assert saved["label_count"] == 5
    assert memory["trade_allowed"] is False
    assert memory["order_routing_enabled"] is False
    assert memory["live_trading_blocked"] is True


def test_9c_037_future_candles_label_target_before_stop():
    candles = [
        {"open": 100.0, "high": 101.0, "low": 99.4, "close": 100.8},
        {"open": 100.8, "high": 103.4, "low": 100.6, "close": 103.0},
    ] + [
        {"open": 103.0 + idx * 0.1, "high": 103.5 + idx * 0.1, "low": 102.4 + idx * 0.1, "close": 103.2 + idx * 0.1}
        for idx in range(18)
    ]
    response = client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={
            "setup_id": "9c-target-first-fixture",
            "symbol": "RELIANCE",
            "timeframe": "1m",
            "entry_price": 100.0,
            "stop_price": 98.8,
            "target_price": 103.0,
            "direction": "long",
            "future_candles": candles,
        },
    )
    assert response.status_code == 200
    labels = response.json()["data"]
    h3 = next(label for label in labels if label["horizon_candles"] == 3)
    assert h3["label_status"] == "complete"
    assert h3["outcome_label"] == "TARGET_HIT"
    assert h3["target_first"] is True
    assert h3["stop_first"] is False
    assert h3["time_to_target"] == 2
    assert h3["future_leakage_detected"] is False


def test_9c_038_future_candles_same_bar_collision_is_stop_first():
    candles = [
        {"open": 100.0, "high": 102.4, "low": 98.7, "close": 100.2},
        {"open": 100.2, "high": 100.5, "low": 99.8, "close": 100.1},
        {"open": 100.1, "high": 100.4, "low": 99.9, "close": 100.0},
    ]
    response = client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={
            "setup_id": "9c-same-bar-fixture",
            "symbol": "RELIANCE",
            "timeframe": "1m",
            "entry_price": 100.0,
            "stop_price": 99.0,
            "target_price": 102.0,
            "direction": "long",
            "conservative_intrabar": True,
            "future_candles": candles,
        },
    )
    assert response.status_code == 200
    labels = response.json()["data"]
    h3 = next(label for label in labels if label["horizon_candles"] == 3)
    assert h3["outcome_label"] == "SL_HIT"
    assert h3["target_first"] is False
    assert h3["stop_first"] is True
    assert h3["time_to_target"] == 1
    assert h3["time_to_stop"] == 1
    assert h3["intrabar_ambiguity_rule"] == "conservative_stop_first"


def test_9c_039_future_candles_insufficient_horizon_stays_pending():
    candles = [
        {"open": 100.0 + idx * 0.1, "high": 100.4 + idx * 0.1, "low": 99.8 + idx * 0.1, "close": 100.2 + idx * 0.1}
        for idx in range(5)
    ]
    response = client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={
            "setup_id": "9c-insufficient-fixture",
            "symbol": "RELIANCE",
            "timeframe": "1m",
            "entry_price": 100.0,
            "stop_price": 98.0,
            "target_price": 105.0,
            "direction": "long",
            "future_candles": candles,
        },
    )
    assert response.status_code == 200
    labels = response.json()["data"]
    complete = [label for label in labels if label["horizon_candles"] in {3, 5}]
    pending = [label for label in labels if label["horizon_candles"] in {9, 12, 20}]
    assert all(label["label_status"] == "complete" for label in complete)
    assert all(label["label_status"] == "pending" for label in pending)
    assert all(label["target_first"] is False and label["stop_first"] is False for label in pending)
    assert all(label["intrabar_ambiguity_rule"] == "insufficient_future_window" for label in pending)


def test_9c_040_persisted_outcome_labels_feed_path_analog_memory():
    symbol = "MEMBRIDGE"
    setup = client.post(
        "/api/v1/behavior/9c-dna/save-setup",
        json={"symbol": symbol, "timeframe": "1m", "source_snapshot_id": "pytest-memory-bridge"},
    ).json()["data"]
    candles = [
        {"open": 100.0, "high": 101.0, "low": 99.6, "close": 100.8},
        {"open": 100.8, "high": 103.6, "low": 100.7, "close": 103.1},
    ] + [
        {"open": 103.1, "high": 103.7, "low": 102.9, "close": 103.3}
        for _ in range(18)
    ]
    labels = client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={
            "setup_id": setup["setup_id"],
            "symbol": symbol,
            "timeframe": "1m",
            "entry_price": 100.0,
            "stop_price": 98.5,
            "target_price": 103.0,
            "direction": "long",
            "future_candles": candles,
        },
    ).json()["data"]
    assert any(label["outcome_label"] == "TARGET_HIT" for label in labels)

    report = client.get(f"/api/v1/behavior/9c-dna/path-analogs/{symbol}?timeframe=1m").json()["data"]
    assert report["persisted_outcome_memory_used"] is True
    assert report["persisted_outcome_match_count"] >= 1
    assert report["winner_like_matches"] >= 1
    assert report["total_matches"] >= report["persisted_outcome_match_count"]
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_9c_010_021_index_manifest_is_deterministic_and_exact_fallback():
    first = client.get("/api/v1/behavior/9c-dna/index-manifest?symbol=RELIANCE&timeframe=1m").json()["data"]
    second = client.get("/api/v1/behavior/9c-dna/index-manifest?symbol=RELIANCE&timeframe=1m").json()["data"]
    path = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m").json()["data"]
    assert first["index_hash"] == second["index_hash"]
    assert first["index_version"] == "9c-path-analog-index.v1"
    assert first["index_type"] == "numpy_cosine_fallback_exact"
    assert first["record_count"] == path["total_matches"]
    assert first["record_count"] != 184
    assert first["atomic_swap_required"] is True
    assert first["validated"] is True
    assert first["manifest_id"]
    assert first["active"] is True
    assert first["trade_allowed"] is False
    assert first["order_routing_enabled"] is False
    assert first["live_trading_blocked"] is True


def test_9c_041_index_manifest_swaps_when_labeled_memory_changes():
    symbol = "INDEXSWAP"
    storage.init_db()
    with storage.connect() as conn:
        conn.execute("DELETE FROM nine_candle_analog_index_manifests WHERE symbol = ?", (symbol,))
        conn.execute("DELETE FROM nine_candle_outcome_labels WHERE setup_id LIKE '9c-indexswap-%'")
        conn.execute("DELETE FROM nine_candle_setups WHERE setup_id LIKE '9c-indexswap-%'")

    first = client.get(f"/api/v1/behavior/9c-dna/index-manifest?symbol={symbol}&timeframe=1m").json()["data"]
    setup = client.post(
        "/api/v1/behavior/9c-dna/save-setup",
        json={"symbol": symbol, "timeframe": "1m", "source_snapshot_id": "pytest-index-swap"},
    ).json()["data"]
    candles = [
        {"open": 100.0, "high": 100.8, "low": 99.6, "close": 100.4},
        {"open": 100.4, "high": 103.4, "low": 100.2, "close": 103.0},
    ] + [{"open": 103.0, "high": 103.6, "low": 102.8, "close": 103.2} for _ in range(18)]
    client.post(
        "/api/v1/behavior/9c-dna/label-outcomes",
        json={
            "setup_id": setup["setup_id"],
            "symbol": symbol,
            "timeframe": "1m",
            "entry_price": 100.0,
            "stop_price": 98.8,
            "target_price": 103.0,
            "direction": "long",
            "future_candles": candles,
        },
    )

    second = client.get(f"/api/v1/behavior/9c-dna/index-manifest?symbol={symbol}&timeframe=1m").json()["data"]
    third = client.get(f"/api/v1/behavior/9c-dna/index-manifest?symbol={symbol}&timeframe=1m").json()["data"]
    assert second["record_count"] == first["record_count"] + 1
    assert second["index_hash"] != first["index_hash"]
    assert second["previous_index_hash"] == first["index_hash"]
    assert second["active"] is True
    assert second["manifest_id"] == third["manifest_id"]
    assert second["active_pointer_swapped_at"] == third["active_pointer_swapped_at"]
    assert third["index_hash"] == second["index_hash"]
    with storage.connect() as conn:
        active_count = conn.execute(
            "SELECT COUNT(*) AS n FROM nine_candle_analog_index_manifests WHERE symbol = ? AND timeframe = ? AND active = 1",
            (symbol, "1m"),
        ).fetchone()["n"]
    assert active_count == 1


def test_9c_042_index_manifest_writes_verified_artifact():
    symbol = "INDEXARTIFACT"
    storage.init_db()
    with storage.connect() as conn:
        conn.execute("DELETE FROM nine_candle_analog_index_manifests WHERE symbol = ?", (symbol,))

    manifest = client.get(f"/api/v1/behavior/9c-dna/index-manifest?symbol={symbol}&timeframe=1m").json()["data"]
    artifact_path = Path(manifest["artifact_uri"])
    artifact_bytes = artifact_path.read_bytes()
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact_path.exists()
    assert manifest["artifact_format"] == "json_exact_cosine_v1"
    assert manifest["artifact_verified"] is True
    assert manifest["artifact_size_bytes"] == artifact_path.stat().st_size
    assert hashlib.sha256(artifact_bytes).hexdigest() == manifest["artifact_sha256"]
    assert artifact_payload["index_hash"] == manifest["index_hash"]
    assert artifact_payload["record_count"] == manifest["record_count"]
    assert artifact_payload["total_matches"] == manifest["record_count"]
    assert artifact_payload["trade_allowed"] is False
    assert artifact_payload["order_routing_enabled"] is False
    assert artifact_payload["live_trading_blocked"] is True

    second = client.get(f"/api/v1/behavior/9c-dna/index-manifest?symbol={symbol}&timeframe=1m").json()["data"]
    assert second["manifest_id"] == manifest["manifest_id"]
    assert second["artifact_uri"] == manifest["artifact_uri"]
    assert second["artifact_sha256"] == manifest["artifact_sha256"]
    assert second["active_pointer_swapped_at"] == manifest["active_pointer_swapped_at"]


def test_9c_math_001_missing_zero_does_not_create_similarity():
    from app.behavior.nine_candle_hybrid import masked_cosine_similarity

    result = masked_cosine_similarity(
        current_vector=[1.0, 0.0, 0.0, 0.0],
        historical_vector=[1.0, 99.0, -42.0, 7.0],
        current_missing_mask=[False, True, True, True],
        historical_missing_mask=[False, False, False, False],
        min_overlap_ratio=0.70,
    )
    assert result["usable"] is False
    assert result["similarity"] is None
    assert result["valid_overlap_count"] == 1
    assert result["overlap_quality"] == 0.25


def test_9c_math_002_flat_data_sets_low_variance_not_missing():
    from app.behavior.nine_candle_hybrid import normalize_zscore

    result = normalize_zscore(raw_value=10.0, rolling_mean=10.0, rolling_std=0.0)
    assert result["normalized"] == 0.0
    assert result["missing_mask"] is False
    assert result["low_variance_flag"] is True


def test_9c_math_003_bounded_indicator_uses_minmax_only():
    from app.behavior.nine_candle_hybrid import normalize_bounded

    result = normalize_bounded(raw_value=65.0, min_value=0.0, max_value=100.0)
    assert result["method"] == "bounded_minmax"
    assert abs(result["normalized"] - 0.30) < 1e-9
    assert result["missing_mask"] is False


def test_9c_math_006_replay_mode_freshness_is_one_and_live_stale_waits():
    from app.behavior.nine_candle_hybrid import freshness_quality

    replay = freshness_quality("replay", age_seconds=86400, max_allowed_age_seconds=60)
    live = freshness_quality("live", age_seconds=90, max_allowed_age_seconds=60)
    assert replay["freshness_quality"] == 1.0
    assert replay["stale_realtime_penalty"] is False
    assert live["freshness_quality"] == 0.0
    assert live["stale_realtime_penalty"] is True


def test_9c_quality_001_bayesian_sample_quality_controls_decision_cap():
    from app.behavior.nine_candle_hybrid import bayesian_sample_quality

    low = bayesian_sample_quality(wins=8, total=20)
    medium = bayesian_sample_quality(wins=34, total=60)
    strong = bayesian_sample_quality(wins=120, total=184)
    assert low["label"] == "low"
    assert low["decision_cap"] == "WAIT"
    assert medium["decision_cap"] == "WATCH"
    assert strong["decision_cap"] in {"WATCH", "PAPER-CANDIDATE"}
    assert 0.0 <= strong["credible_lower_bound"] <= strong["posterior_win_rate"] <= 1.0


def test_9c_quality_002_decision_exposes_precision_metrics_and_new_gates():
    result = client.get("/api/v1/behavior/9c-dna/decision/RELIANCE?timeframe=1m").json()["data"]
    decision = result["hybrid_decision"]
    assert 0.0 <= decision["sample_quality_score"] <= 1.0
    assert 0.0 <= decision["data_quality_score"] <= 1.0
    assert decision["freshness_quality"] == 1.0
    assert 0.0 <= decision["overlap_quality"] <= 1.0
    assert 0.0 <= decision["proof_score"] <= 1.0
    assert decision["mode"] == "mock"
    assert decision["regime_id"].startswith("trend_up_")
    assert decision["regime_group"] == "trend_up_normal_vol"
    gate_status = {gate["gate_id"]: gate["status"] for gate in decision["safety_gates"]}
    assert gate_status["9C-G001"] == "pass"
    assert gate_status["9C-G006"] in {"pass", "wait"}
    assert gate_status["9C-G007"] in {"pass", "wait"}
    assert gate_status["9C-G013"] == "pass"
    assert gate_status["9C-G014"] == "pass"
    assert gate_status["9C-G015"] in {"pass", "wait"}
    if gate_status["9C-G006"] == "wait" or gate_status["9C-G007"] == "wait":
        assert decision["decision"] == "WAIT"
        assert decision["final_reason"].startswith("WAIT.")


def test_9c_018_feature_manifest_mismatch_blocks_probability():
    from app.behavior.nine_candle_hybrid import _safety_gates, build_analogs, build_model_status_for, bayesian_sample_quality

    analog = build_analogs("RELIANCE", "1m").model_copy(update={"feature_manifest_version": "stale-manifest.v0"})
    model = build_model_status_for("RELIANCE", "1m")
    gates = _safety_gates(
        analog=analog,
        model=model,
        masked={"usable": True, "overlap_quality": 1.0},
        sample=bayesian_sample_quality(analog.winner_like_matches, analog.total_matches),
        freshness={"mode": "mock", "freshness_quality": 1.0, "stale_realtime_penalty": False},
        proof={"proof_score": 0.8, "decision_cap": "PAPER-CANDIDATE"},
        feature_manifest_version="nine-candle-feature-manifest.v1",
        path={"feature_manifest_version": "nine-candle-feature-manifest.v1"},
    )
    gate_status = {gate["gate_id"]: gate for gate in gates}
    assert gate_status["9C-G001"]["status"] == "wait"
    assert "mismatch" in gate_status["9C-G001"]["evidence"]


def test_9c_gate_failure_similarity_and_non_positive_r_block_confidence():
    from app.behavior.nine_candle_hybrid import _safety_gates, build_analogs, build_model_status_for, bayesian_sample_quality

    analog = build_analogs("RELIANCE", "1m").model_copy(update={"winner_similarity": 0.30, "failure_similarity": 0.60})
    model = build_model_status_for("RELIANCE", "1m").model_copy(update={"expected_r_after_cost": 0.0})
    gates = _safety_gates(
        analog=analog,
        model=model,
        masked={"usable": True, "overlap_quality": 1.0},
        sample=bayesian_sample_quality(analog.winner_like_matches, analog.total_matches),
        freshness={"mode": "mock", "freshness_quality": 1.0, "stale_realtime_penalty": False},
        proof={"proof_score": 0.8, "decision_cap": "PAPER-CANDIDATE"},
        feature_manifest_version=analog.feature_manifest_version,
        path={"feature_manifest_version": analog.feature_manifest_version},
    )
    gate_status = {gate["gate_id"]: gate for gate in gates}
    assert gate_status["9C-G006"]["status"] == "wait"
    assert gate_status["9C-G007"]["status"] == "wait"
    assert "Failure similarity" in gate_status["9C-G006"]["evidence"]
    assert "non-positive edge" in gate_status["9C-G007"]["evidence"]


def test_9c_ev_001_same_packet_same_decision_hash():
    first = client.get("/api/v1/behavior/9c-dna/evidence-packet/RELIANCE?timeframe=1m").json()["data"]
    second = client.get("/api/v1/behavior/9c-dna/evidence-packet/RELIANCE?timeframe=1m").json()["data"]
    assert first["evidence_packet_hash"] == second["evidence_packet_hash"]
    assert first["evidence_packet_id"] == second["evidence_packet_id"]
    assert first["deterministic"] is True
    assert len(first["last_9_candles"]) == 9
    assert len(first["indicator_sequences"]) == first["feature_vector"]["vector_dimension"]


def test_9c_ev_002_packet_contains_no_future_candle_and_closed_only():
    packet = client.get("/api/v1/behavior/9c-dna/evidence-packet/RELIANCE?timeframe=1m").json()["data"]
    assert packet["closed_candle_only"] is True
    assert packet["no_future_leakage"] is True
    assert packet["future_bar_blocked"] is True
    assert all(candle["closed"] is True for candle in packet["last_9_candles"])
    assert packet["decision_time"] > packet["last_9_candles"][-1]["event_time"]
    assert packet["trade_allowed"] is False
    assert packet["order_routing_enabled"] is False
    assert packet["live_trading_blocked"] is True


def test_9c_ev_003_decision_references_same_evidence_packet():
    decision_response = client.get("/api/v1/behavior/9c-dna/decision/RELIANCE?timeframe=1m").json()["data"]
    packet = client.get("/api/v1/behavior/9c-dna/evidence-packet/RELIANCE?timeframe=1m").json()["data"]
    decision = decision_response["hybrid_decision"]
    assert decision["evidence_packet_id"] == packet["evidence_packet_id"]
    assert decision["evidence_packet_hash"] == packet["evidence_packet_hash"]
    assert decision_response["evidence_packet"]["evidence_packet_hash"] == packet["evidence_packet_hash"]


def test_9c_ev_005_packet_hash_changes_when_input_changes():
    reliance = client.get("/api/v1/behavior/9c-dna/evidence-packet/RELIANCE?timeframe=1m").json()["data"]
    infy = client.get("/api/v1/behavior/9c-dna/evidence-packet/INFY?timeframe=1m").json()["data"]
    assert reliance["evidence_packet_hash"] != infy["evidence_packet_hash"]
    assert reliance["evidence_packet_id"] != infy["evidence_packet_id"]
    assert reliance["feature_manifest_version"] == infy["feature_manifest_version"]


def test_9c_runtime_001_default_does_not_invoke_real_indicators():
    result = client.get("/api/v1/behavior/9c-dna/indicator-runtime/RELIANCE?timeframe=1m").json()["data"]
    assert result["runtime_version"] == "9c-indicator-runtime-bridge.v1"
    assert result["use_real_indicators"] is False
    assert result["runtime_state"] == "mock_default"
    assert result["selected_indicator_count"] > 0
    assert result["selected_indicator_count"] == result["level_runtime_selected_count"]
    assert result["selected_indicator_ids"] == result["level_runtime_selected_ids"]
    assert result["vector_promoted_indicator_count"] > result["level_runtime_selected_count"]
    assert result["vector_promoted_not_level_selected_count"] == (
        result["vector_promoted_indicator_count"] - result["level_runtime_selected_count"]
    )
    assert result["level_candidates"]
    assert result["missing_outputs"]
    assert {item["reason"] for item in result["missing_outputs"]} == {"real indicator runtime disabled"}
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert result["pta_marker_selected_count"] == 23
    assert result["pta_marker_output_count"] == 0
    assert result["pta_marker_telemetry"] == []
    assert result["pta_markers_used_for_probability"] is False
    assert result["pta_markers_used_for_9c_vector"] is False


def test_9c_runtime_002_cache_hit_is_deterministic():
    first = client.get("/api/v1/behavior/9c-dna/indicator-runtime/RELIANCE?timeframe=1m").json()["data"]
    second = client.get("/api/v1/behavior/9c-dna/indicator-runtime/RELIANCE?timeframe=1m").json()["data"]
    assert first["output_hash"] == second["output_hash"]
    assert second["cache_hit"] is True
    assert first["cache_key_hash"] == second["cache_key_hash"]


def test_9c_runtime_008_real_runtime_probes_pta_markers_without_probability_or_trading():
    result = client.get("/api/v1/behavior/9c-dna/indicator-runtime/RELIANCE?timeframe=1m&use_real_indicators=true").json()["data"]
    assert result["use_real_indicators"] is True
    assert result["vector_promoted_indicator_count"] > result["level_runtime_selected_count"]
    assert "si_fmfm300" in result["vector_promoted_indicator_ids"]
    assert "si_fmfm300" in result["vector_promoted_not_level_selected_ids"]
    assert result["indicator_cache_hit_count"] + result["indicator_cache_miss_count"] == result["selected_indicator_count"]
    assert result["slow_indicator_count"] == len(result["slow_indicator_ids"])
    assert set(result["vector_promoted_not_level_selected_ids"]).isdisjoint(set(result["level_runtime_selected_ids"]))
    assert result["pta_marker_selected_count"] == 23
    assert result["pta_marker_output_count"] == 23
    assert len(result["pta_marker_telemetry"]) == 23
    assert result["pta_marker_dependency"]["dependency"] == "pandas_ta_classic"
    assert result["pta_marker_dependency"]["compute_source"] == "vendor.stock_app.shared.indicators.pta_signal_markers"
    assert result["pta_markers_used_for_probability"] is False
    assert result["pta_markers_used_for_9c_vector"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    statuses = {row["status"] for row in result["pta_marker_telemetry"]}
    assert statuses.issubset({"computed", "no_signal", "dependency_unavailable", "error"})
    assert all(row["used_for_probability"] is False for row in result["pta_marker_telemetry"])
    assert all(row["used_for_9c_vector"] is False for row in result["pta_marker_telemetry"])
    assert all(row["trade_allowed"] is False and row["order_routing_enabled"] is False for row in result["pta_marker_telemetry"])


def test_9c_runtime_009_fmfm300_is_explanation_only_and_not_trade_authority():
    promotion = client.get(
        "/api/v1/behavior/9c-dna/indicator-promotion/RELIANCE?timeframe=1m&use_real_indicators=true"
    ).json()["data"]
    fmfm_promotion = next(row for row in promotion["promotion_rows"] if row["indicator_id"] == "si_fmfm300")
    assert fmfm_promotion["promoted_for_runtime"] is True
    assert fmfm_promotion["current_state"] in {"explanation_only", "masked"}
    assert fmfm_promotion["runtime_status"] in {"computed", "slow_warn", "slow_blocked"}
    assert fmfm_promotion["probability_gate"] == "blocked"
    assert "runtime_cache_hit" in fmfm_promotion
    assert "source_latency_ms" in fmfm_promotion
    assert "probability_evidence_pending" in fmfm_promotion["blocking_reasons"]
    assert "registry_probability_disabled" in fmfm_promotion["blocking_reasons"]
    if fmfm_promotion["runtime_status"] == "slow_blocked":
        assert fmfm_promotion["current_state"] == "masked"
        assert "runtime_status_slow_blocked" in fmfm_promotion["blocking_reasons"]
        assert "latency_gate_failed" in fmfm_promotion["blocking_reasons"]
    assert promotion["runtime_cache_hit_count"] + promotion["runtime_cache_miss_count"] == promotion["promoted_for_runtime_count"]
    assert promotion["slow_indicator_count"] == len(promotion["slow_indicator_ids"])
    assert promotion["trade_allowed"] is False
    assert promotion["order_routing_enabled"] is False
    assert promotion["live_trading_blocked"] is True

    alignment = client.get(
        "/api/v1/behavior/9c-dna/indicator-alignment/RELIANCE?timeframe=1m&use_real_indicators=true"
    ).json()["data"]
    fmfm_alignment = next(row for row in alignment if row["indicator_id"] == "si_fmfm300")
    assert fmfm_alignment["runtime_status"] in {"computed", "slow_warn", "slow_blocked"}
    if fmfm_alignment["runtime_status"] == "slow_blocked":
        assert fmfm_alignment["source_mode"] == "masked"
        assert fmfm_alignment["raw_output_present"] is False
        assert "status=slow_blocked" in fmfm_alignment["missing_reason"]
    else:
        assert fmfm_alignment["source_mode"] == "real"
        assert fmfm_alignment["raw_output_present"] is True
        assert fmfm_alignment["explanation_only"] is True
    assert fmfm_alignment["usable_for_probability"] is False
    assert "excluded from calibrated probability" in fmfm_alignment["historical_effect"]


def test_9c_runtime_010_real_indicator_adapter_cache_reuses_closed_candle_outputs():
    from app.behavior.nine_candle_hybrid import _runtime_closed_candles
    from app.behavior.real_indicator_adapter import clear_real_indicator_runtime_cache, compute_real_indicator_outputs_with_telemetry

    clear_real_indicator_runtime_cache()
    candles = _runtime_closed_candles("RELIANCE", "1m")
    first_outputs, first_telemetry = compute_real_indicator_outputs_with_telemetry(candles, ["si_ichi_trend_osc"])
    second_outputs, second_telemetry = compute_real_indicator_outputs_with_telemetry(candles, ["si_ichi_trend_osc"])

    assert first_outputs == second_outputs
    assert first_telemetry[0]["indicator_id"] == "si_ichi_trend_osc"
    assert second_telemetry[0]["indicator_id"] == "si_ichi_trend_osc"
    assert first_telemetry[0]["cache_hit"] is False
    assert second_telemetry[0]["cache_hit"] is True
    assert second_telemetry[0]["latency_ms"] == 0.0
    assert second_telemetry[0]["source_latency_ms"] == first_telemetry[0]["latency_ms"]
    assert second_telemetry[0]["used_for_9c_vector"] == second_telemetry[0]["output_present"]


def test_icache_000_contract_has_no_numeric_gaps():
    names = set(globals())
    present = {
        int(name.split("_")[2])
        for name in names
        if name.startswith("test_icache_") and name.split("_")[2].isdigit()
    }

    assert set(range(1, 21)).issubset(present)


def test_icache_001_save_creates_exact_safe_indicator_cache_rows():
    result = client.post(
        "/api/v1/behavior/indicator-cache/save/RELIANCE?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]

    assert result["cache_schema_version"] == "indicator-result-cache.v1"
    assert result["saved_count"] == 49
    assert result["reused_count"] == 0
    assert result["failed_count"] == 0
    assert result["cache_status"] == "saved"
    assert result["used_for_probability"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert result["no_future_leakage"] is True
    assert result["closed_candle_only"] is True
    assert all(row["used_for_probability"] is False for row in result["rows"])
    assert all(row["trade_allowed"] is False for row in result["rows"])
    assert all(row["order_routing_enabled"] is False for row in result["rows"])
    assert all(row["live_trading_blocked"] is True for row in result["rows"])


def test_icache_002_reuse_requires_exact_identity_and_verified_artifact():
    first = client.post(
        "/api/v1/behavior/indicator-cache/save/RELIANCE?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    second = client.post(
        "/api/v1/behavior/indicator-cache/save/RELIANCE?timeframe=1m&use_real_indicators=true&force_recompute=false"
    ).json()["data"]

    assert second["source_snapshot_hash"] == first["source_snapshot_hash"]
    assert second["indicator_registry_version"] == first["indicator_registry_version"]
    assert second["feature_manifest_version"] == first["feature_manifest_version"]
    assert second["promoted_indicator_hash"] == first["promoted_indicator_hash"]
    assert second["reused_count"] == first["saved_count"]
    assert second["saved_count"] == 0
    assert second["cache_hit_rate"] == 1.0
    assert all(row["cache_integrity_status"] == "verified" for row in second["rows"])


def test_icache_003_status_and_results_verify_artifact_json_shape():
    client.post(
        "/api/v1/behavior/indicator-cache/save/RELIANCE?timeframe=1m&use_real_indicators=false&force_recompute=true"
    )
    status = client.get("/api/v1/behavior/indicator-cache/status/RELIANCE?timeframe=1m").json()["data"]
    results = client.get("/api/v1/behavior/indicator-cache/results/RELIANCE?timeframe=1m&limit=50").json()["data"]

    assert status["cache_status"] == "hit"
    assert status["verified_count"] >= 13
    assert status["used_for_probability"] is False
    verified_rows = [row for row in results["results"] if row["cache_integrity_status"] == "verified" and row["artifact"] is not None]
    assert len(verified_rows) >= 3
    for row in verified_rows[:3]:
        artifact = row["artifact"]
        assert artifact["cache_schema_version"] == "indicator-result-cache.v1"
        assert artifact["symbol"] == "RELIANCE"
        assert artifact["timeframe"] == "1m"
        assert artifact["indicator_id"] == row["indicator_id"]
        assert artifact["safety"] == {
            "reference_only": True,
            "can_seed_9c_vector": False,
            "used_for_probability": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }


def test_icache_004_delete_removes_row_without_enabling_trading():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/RELIANCE?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    cache_id = saved["rows"][0]["cache_id"]
    deleted = client.delete(f"/api/v1/behavior/indicator-cache/{cache_id}").json()["data"]

    assert deleted["deleted"] is True
    assert deleted["used_for_probability"] is False
    assert deleted["trade_allowed"] is False
    assert deleted["order_routing_enabled"] is False
    assert deleted["live_trading_blocked"] is True
    again = client.delete(f"/api/v1/behavior/indicator-cache/{cache_id}").json()["data"]
    assert again["deleted"] is False


def test_icache_005_cache_id_matches_exact_identity_formula():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/IDFORM?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    row = saved["rows"][0]
    raw = "|".join(
        [
            row["symbol"],
            row["timeframe"],
            row["source_snapshot_hash"],
            row["indicator_id"],
            row["indicator_registry_version"],
            row["feature_manifest_version"],
            row["promoted_indicator_hash"],
        ]
    )
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    assert row["cache_id"] == expected
    assert row["cache_id"] == saved["rows"][0]["artifact_uri"].split("/")[-1].replace(".json", "")


def test_icache_006_artifact_payload_identity_context_telemetry_and_safety_are_present():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/ARTSHAPE?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    row = saved["rows"][0]
    artifact_path = storage.PROJECT_ROOT / row["artifact_uri"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["cache_schema_version"] == "indicator-result-cache.v1"
    assert artifact["symbol"] == row["symbol"]
    assert artifact["timeframe"] == row["timeframe"]
    assert artifact["source_snapshot_hash"] == row["source_snapshot_hash"]
    assert artifact["indicator_id"] == row["indicator_id"]
    assert set(artifact["context"]) == {"volatility_bucket", "volatility_ood", "volatility_threshold_source"}
    assert artifact["telemetry"]["cache_id"] == row["cache_id"]
    assert artifact["safety"]["reference_only"] is True
    assert artifact["safety"]["can_seed_9c_vector"] is False
    assert artifact["safety"]["used_for_probability"] is False
    assert artifact["safety"]["trade_allowed"] is False
    assert artifact["safety"]["order_routing_enabled"] is False
    assert artifact["safety"]["live_trading_blocked"] is True


def test_icache_007_force_recompute_refreshes_same_deterministic_cache_identity():
    first = client.post(
        "/api/v1/behavior/indicator-cache/save/FORCEID?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    second = client.post(
        "/api/v1/behavior/indicator-cache/save/FORCEID?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]

    first_ids = sorted(row["cache_id"] for row in first["rows"])
    second_ids = sorted(row["cache_id"] for row in second["rows"])
    assert first_ids == second_ids
    assert first["saved_count"] == second["saved_count"] == 49
    assert second["reused_count"] == 0
    assert all(row["used_for_probability"] is False for row in second["rows"])
    assert all(row["order_routing_enabled"] is False for row in second["rows"])


def test_icache_008_missing_artifact_is_failed_and_not_reused():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/MISSART?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    row = saved["rows"][0]
    artifact_path = storage.PROJECT_ROOT / row["artifact_uri"]
    artifact_path.unlink(missing_ok=True)

    status = client.get("/api/v1/behavior/indicator-cache/status/MISSART?timeframe=1m").json()["data"]
    missing_rows = [item for item in status["rows"] if item["cache_id"] == row["cache_id"]]
    assert missing_rows
    assert missing_rows[0]["cache_integrity_status"] == "failed"

    reused = client.post(
        "/api/v1/behavior/indicator-cache/save/MISSART?timeframe=1m&use_real_indicators=true&force_recompute=false"
    ).json()["data"]
    assert row["cache_id"] not in {item["cache_id"] for item in reused["rows"] if item["cache_integrity_status"] == "verified"}
    assert reused["reused_count"] < saved["saved_count"]
    assert reused["used_for_probability"] is False
    assert reused["live_trading_blocked"] is True


def test_icache_009_api_paths_share_live_blocked_safety_envelope():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/SAFEENV?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    status = client.get("/api/v1/behavior/indicator-cache/status/SAFEENV?timeframe=1m").json()["data"]
    results = client.get("/api/v1/behavior/indicator-cache/results/SAFEENV?timeframe=1m&limit=5").json()["data"]
    deleted = client.delete(f"/api/v1/behavior/indicator-cache/{saved['rows'][0]['cache_id']}").json()["data"]

    for payload in [saved, status, results, deleted]:
        assert payload["used_for_probability"] is False
        assert payload["trade_allowed"] is False
        assert payload["order_routing_enabled"] is False
        assert payload["live_trading_blocked"] is True


def test_icache_010_limit_parameter_is_bounded():
    client.post(
        "/api/v1/behavior/indicator-cache/save/LIMITTEST?timeframe=1m&use_real_indicators=false&force_recompute=true"
    )
    results = client.get("/api/v1/behavior/indicator-cache/results/LIMITTEST?timeframe=1m&limit=5000").json()["data"]

    assert results["result_count"] <= 2000
    assert results["used_for_probability"] is False
    assert results["live_trading_blocked"] is True


def test_icache_011_stale_registry_version_is_not_verified():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/REGSTALE?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    source_hash = saved["source_snapshot_hash"]
    rows = storage.list_indicator_result_cache_rows("REGSTALE", "1m", source_hash)
    stale_row = dict(rows[0])
    for row in rows:
        storage.delete_indicator_result_cache_row(str(row["cache_id"]))
    stale_row["cache_id"] = f"{stale_row['cache_id']}-stale-registry"
    stale_row["indicator_registry_version"] = "indicator-registry.old"
    storage.save_indicator_result_cache_row(stale_row)

    status = client.get("/api/v1/behavior/indicator-cache/status/REGSTALE?timeframe=1m").json()["data"]
    assert status["stored_count"] == 1
    assert status["verified_count"] == 0
    assert status["failed_count"] == 1
    assert status["rows"][0]["cache_integrity_status"] == "stale_registry_version"
    assert status["rows"][0]["used_for_probability"] is False
    assert status["rows"][0]["order_routing_enabled"] is False


def test_icache_012_cache_save_keeps_mock_default_reference_only():
    result = client.post("/api/v1/behavior/indicator-cache/save/MOCKDEFAULT?timeframe=1m").json()["data"]

    assert result["use_real_indicators"] is False
    assert result["cache_status"] == "saved"
    assert result["saved_count"] == 49
    assert result["reference_only"] is True
    assert all(row["runtime_status"] == "mock_runtime_disabled" for row in result["rows"])
    assert all(row["output_present"] is False for row in result["rows"])
    assert result["used_for_probability"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_icache_013_anomalous_snapshot_is_quarantined_and_not_persisted():
    result = client.post(
        "/api/v1/behavior/indicator-cache/save/ANOMALY?timeframe=1m&use_real_indicators=true&force_recompute=true&anomalous_snapshot=true"
    ).json()["data"]

    assert result["cache_status"] == "anomalous_snapshot_quarantined"
    assert result["anomalous_snapshot_quarantined"] is True
    assert result["cache_integrity_status"] == "quarantined_reference_only"
    assert result["saved_count"] == 0
    assert result["reused_count"] == 0
    assert result["rows"] == []
    assert result["reference_only"] is True
    assert result["can_seed_9c_vector"] is False
    assert result["used_for_probability"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_icache_014_artifacts_are_reference_only_and_never_probability_authority():
    client.post(
        "/api/v1/behavior/indicator-cache/save/REFONLY?timeframe=1m&use_real_indicators=false&force_recompute=true"
    )
    results = client.get("/api/v1/behavior/indicator-cache/results/REFONLY?timeframe=1m&limit=50").json()["data"]

    verified_rows = [row for row in results["results"] if row["cache_integrity_status"] == "verified" and row["artifact"] is not None]
    assert len(verified_rows) >= 2
    for row in verified_rows[:2]:
        assert row["reference_only"] is True
        assert row["can_seed_9c_vector"] is False
        artifact = row["artifact"]
        assert artifact["safety"]["reference_only"] is True
        assert artifact["safety"]["can_seed_9c_vector"] is False
        assert artifact["safety"]["used_for_probability"] is False
        assert artifact["safety"]["trade_allowed"] is False
        assert artifact["safety"]["order_routing_enabled"] is False
        assert artifact["safety"]["live_trading_blocked"] is True


def test_icache_015_sha_mismatch_is_failed_and_not_reused():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/SHAFAIL?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    row = saved["rows"][0]
    artifact_path = storage.PROJECT_ROOT / row["artifact_uri"]
    artifact_path.write_text('{"corrupted":true}', encoding="utf-8")

    status = client.get("/api/v1/behavior/indicator-cache/status/SHAFAIL?timeframe=1m").json()["data"]
    results = client.get("/api/v1/behavior/indicator-cache/results/SHAFAIL?timeframe=1m&limit=50").json()["data"]

    assert status["failed_count"] >= 1
    failed_statuses = {item["cache_integrity_status"] for item in status["rows"]}
    assert "failed" in failed_statuses
    failed_rows = [item for item in results["results"] if item["cache_id"] == row["cache_id"]]
    assert failed_rows
    assert failed_rows[0]["cache_integrity_status"] == "failed"
    assert failed_rows[0]["artifact"] is None
    assert failed_rows[0]["used_for_probability"] is False
    assert failed_rows[0]["trade_allowed"] is False


def test_icache_016_feature_manifest_mismatch_is_stale_and_not_reused():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/VERSIONTEST?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    source_hash = saved["source_snapshot_hash"]
    rows = storage.list_indicator_result_cache_rows("VERSIONTEST", "1m", source_hash)
    stale_row = dict(rows[0])
    for row in rows:
        storage.delete_indicator_result_cache_row(str(row["cache_id"]))
    stale_row["cache_id"] = f"{stale_row['cache_id']}-stale"
    stale_row["feature_manifest_version"] = "nine-candle-feature-manifest.old"
    storage.save_indicator_result_cache_row(stale_row)

    status = client.get("/api/v1/behavior/indicator-cache/status/VERSIONTEST?timeframe=1m").json()["data"]
    assert status["stored_count"] == 1
    assert status["verified_count"] == 0
    assert status["failed_count"] == 1
    assert status["rows"][0]["cache_integrity_status"] == "stale_feature_manifest_version"

    recomputed = client.post(
        "/api/v1/behavior/indicator-cache/save/VERSIONTEST?timeframe=1m&use_real_indicators=true&force_recompute=false"
    ).json()["data"]
    assert recomputed["reused_count"] == 0
    assert recomputed["saved_count"] >= 1
    assert all(row["feature_manifest_version"] != "nine-candle-feature-manifest.old" for row in recomputed["rows"])


def test_icache_017_disk_write_failure_degrades_without_crashing(monkeypatch):
    from app.behavior import indicator_result_cache

    def raise_disk_full(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(indicator_result_cache, "_write_indicator_artifact", raise_disk_full)
    result = indicator_result_cache.save_indicator_results(
        "DISKFULL",
        "1m",
        use_real_indicators=False,
        force_recompute=True,
    )

    assert result["saved_count"] == 0
    assert result["reused_count"] == 0
    assert result["failed_count"] == 49
    assert result["cache_integrity_status"] == "degraded_recomputed"
    assert all(row["cache_integrity_status"] == "failed" for row in result["failed_rows"])
    assert all(row["runtime_status"] == "cache_write_failed" for row in result["failed_rows"])
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_icache_018_same_identity_artifact_is_reproducible():
    first = client.post(
        "/api/v1/behavior/indicator-cache/save/REPRO?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    second = client.post(
        "/api/v1/behavior/indicator-cache/save/REPRO?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]

    first_pairs = sorted((row["cache_id"], row["artifact_sha256"]) for row in first["rows"])
    second_pairs = sorted((row["cache_id"], row["artifact_sha256"]) for row in second["rows"])
    assert first_pairs == second_pairs
    assert first["source_snapshot_hash"] == second["source_snapshot_hash"]
    assert first["promoted_indicator_hash"] == second["promoted_indicator_hash"]


def test_icache_019_wrong_volatility_context_is_stale():
    saved = client.post(
        "/api/v1/behavior/indicator-cache/save/VOLSTALE?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    row = saved["rows"][0]
    artifact_path = storage.PROJECT_ROOT / row["artifact_uri"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["context"]["volatility_bucket"] = "impossible_stale_bucket"
    artifact_json = json.dumps(artifact, sort_keys=True, separators=(",", ":"), default=str)
    artifact_path.write_text(artifact_json, encoding="utf-8")
    db_row = storage.list_indicator_result_cache_rows("VOLSTALE", "1m", saved["source_snapshot_hash"], row["indicator_id"])[0]
    db_row["artifact_sha256"] = hashlib.sha256(artifact_json.encode("utf-8")).hexdigest()
    storage.save_indicator_result_cache_row(db_row)

    status = client.get("/api/v1/behavior/indicator-cache/status/VOLSTALE?timeframe=1m").json()["data"]
    stale_rows = [item for item in status["rows"] if item["cache_id"] == row["cache_id"]]
    assert stale_rows
    assert stale_rows[0]["cache_integrity_status"] == "stale_volatility_bucket"
    assert stale_rows[0]["used_for_probability"] is False
    assert stale_rows[0]["trade_allowed"] is False


def test_icache_020_force_recompute_anomalous_snapshot_remains_quarantined():
    clean = client.post(
        "/api/v1/behavior/indicator-cache/save/FORCEANOM?timeframe=1m&use_real_indicators=false&force_recompute=true"
    ).json()["data"]
    quarantined = client.post(
        "/api/v1/behavior/indicator-cache/save/FORCEANOM?timeframe=1m&use_real_indicators=true&force_recompute=true&anomalous_snapshot=true"
    ).json()["data"]

    assert clean["saved_count"] == 49
    assert quarantined["cache_status"] == "anomalous_snapshot_quarantined"
    assert quarantined["saved_count"] == 0
    assert quarantined["reused_count"] == 0
    assert quarantined["rows"] == []
    assert quarantined["anomalous_snapshot_quarantined"] is True
    assert quarantined["reference_only"] is True
    assert quarantined["live_trading_blocked"] is True


def test_tv_prod_red_001_manipulated_wick_final_gate_blocks_confidence_and_quarantines_cache():
    report = client.get("/api/v1/behavior/red-team/tv-prod-red-001?symbol=RELIANCE&timeframe=1m").json()["data"]

    assert report["red_team_id"] == "TV-PROD-RED-001"
    assert report["red_team_version"] == "tv-prod-red-001.v1"
    assert report["passed"] is True
    assert report["release_blocking"] is False
    assert report["volatility_status"]["volatility_ood"] is True
    assert report["volatility_status"]["gate"]["gate_id"] == "9C-G016"
    assert report["volatility_status"]["gate"]["status"] == "wait"
    assert "manipulated_looking" in report["arbiter"]["consulted_flags"]
    assert "volatility_ood" in report["arbiter"]["consulted_flags"]
    assert report["matched_after_vol_bucketing"] < report["raw_match_count"]
    assert report["arbiter"]["continuation_boost"] <= 0.0
    assert report["decision"] in {"WAIT", "WATCH"}
    assert report["paper_candidate_allowed"] is False
    assert report["cache_status"] == "anomalous_snapshot_quarantined"
    assert report["cache_reference_only"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert {check["check_id"] for check in report["checks"]} == {
        "volatility_ood",
        "manipulated_flag_consulted",
        "volatility_bucket_reduces_matches",
        "continuation_boost_zero",
        "decision_wait_or_watch",
        "paper_candidate_blocked",
        "cache_quarantined",
        "live_trading_blocked",
        "trade_disallowed",
        "order_routing_disabled",
    }
    assert all(check["passed"] for check in report["checks"])


def test_9c_prox_001_distance_atr_nonnegative_and_side_consistent():
    result = client.get("/api/v1/behavior/9c-dna/level-proximity/RELIANCE?timeframe=1m").json()["data"]
    assert result["proximity_version"] == "9c-level-proximity.v1"
    assert result["records"]
    assert result["nearest_level"] == result["records"][0]
    for row in result["records"]:
        assert row["distance_atr"] >= 0.0
        if row["side"] == "above":
            assert row["latest_close"] > row["level_price"]
        elif row["side"] == "below":
            assert row["latest_close"] < row["level_price"]
        else:
            assert row["latest_close"] == row["level_price"]
    assert "invalid_negative_distance_atr" not in result["calculation_warnings"]
    assert "side_label_inconsistent" not in result["calculation_warnings"]


def test_9c_prox_003_zero_distance_no_division_error():
    from app.behavior.level_proximity import _proximity_record

    record = _proximity_record(
        {
            "level_name": "exact",
            "level_price": 100.0,
            "level_type": "test",
            "source_indicator": "unit",
            "source_state": "unit",
            "point_in_time_safe": True,
        },
        latest_close=100.0,
        atr=2.0,
        atr_zero_fallback=False,
    )
    assert record["side"] == "at_level"
    assert record["distance_atr"] == 0.0
    assert record["distance_pct"] == 0.0


def test_9c_prox_002_far_from_all_levels_does_not_create_false_proximity():
    from app.behavior.level_proximity import _proximity_record

    records = [
        _proximity_record(
            {
                "level_name": "far_support",
                "level_price": 80.0,
                "level_type": "support",
                "source_indicator": "unit",
                "source_state": "unit",
            },
            latest_close=100.0,
            atr=2.0,
            atr_zero_fallback=False,
        ),
        _proximity_record(
            {
                "level_name": "far_resistance",
                "level_price": 125.0,
                "level_type": "resistance",
                "source_indicator": "unit",
                "source_state": "unit",
            },
            latest_close=100.0,
            atr=2.0,
            atr_zero_fallback=False,
        ),
    ]
    assert all(record["within_atr_band"] is False for record in records)
    assert [record["side"] for record in records] == ["above", "below"]


def test_9c_conf_001_confluence_zone_uses_median_and_counts():
    from statistics import median

    result = client.get("/api/v1/behavior/9c-dna/confluence/RELIANCE?timeframe=1m").json()["data"]
    assert result["confluence_version"] == "9c-level-confluence.v1"
    assert result["zones"]
    assert result["strongest_zone"] == result["zones"][0]
    for zone in result["zones"]:
        assert zone["contributing_count"] == len(zone["contributing_levels"])
        assert 1 <= zone["zone_strength"] <= 5
        assert zone["zone_price"] == round(float(median(zone["contributing_prices"])), 4)
    assert result["calculation_warnings"] == []


def test_9c_conf_002_scattered_levels_do_not_create_false_confluence():
    from app.behavior.level_confluence import _cluster_zones

    proximity = {
        "latest_close": 100.0,
        "atr": 2.0,
        "atr_band": 0.5,
        "records": [
            {"level_name": "support_far", "level_price": 80.0, "side": "above", "within_atr_band": False, "point_in_time_safe": True},
            {"level_name": "resistance_far", "level_price": 120.0, "side": "below", "within_atr_band": False, "point_in_time_safe": True},
            {"level_name": "resistance_farther", "level_price": 140.0, "side": "below", "within_atr_band": False, "point_in_time_safe": True},
        ],
    }
    zones = _cluster_zones(proximity)
    assert len(zones) == 3
    assert all(zone["contributing_count"] == 1 for zone in zones)
    assert all(zone["zone_strength"] == 1 for zone in zones)


def test_9c_conf_004_mixed_support_resistance_conflict_is_visible():
    from app.behavior.level_confluence import _cluster_zones

    proximity = {
        "latest_close": 100.0,
        "atr": 10.0,
        "atr_band": 0.5,
        "records": [
            {"level_name": "near_support", "level_price": 99.0, "side": "above", "within_atr_band": True, "point_in_time_safe": True},
            {"level_name": "near_resistance", "level_price": 101.0, "side": "below", "within_atr_band": True, "point_in_time_safe": True},
        ],
    }
    zones = _cluster_zones(proximity)
    assert len(zones) == 1
    assert zones[0]["zone_type"] == "mixed"
    assert zones[0]["support_count"] == 1
    assert zones[0]["resistance_count"] == 1
    assert zones[0]["conflict_count"] == 1
    assert zones[0]["net_agreement"] == 0


def test_9c_pit_runtime_proximity_confluence_are_safe_and_closed_only():
    endpoints = [
        "/api/v1/behavior/9c-dna/indicator-runtime/RELIANCE?timeframe=1m",
        "/api/v1/behavior/9c-dna/level-proximity/RELIANCE?timeframe=1m",
        "/api/v1/behavior/9c-dna/confluence/RELIANCE?timeframe=1m",
    ]
    for endpoint in endpoints:
        result = client.get(endpoint).json()["data"]
        assert result["no_future_leakage"] is True
        assert result["future_bar_blocked"] is True
        assert result["closed_candle_only"] is True
        assert result["trade_allowed"] is False
        assert result["order_routing_enabled"] is False
        assert result["live_trading_blocked"] is True


def test_9c_perf_phase1_context_builders_stay_under_budget():
    import time

    budgets = [
        ("/api/v1/behavior/9c-dna/level-proximity/RELIANCE?timeframe=1m", 500.0),
        ("/api/v1/behavior/9c-dna/confluence/RELIANCE?timeframe=1m", 500.0),
        ("/api/v1/behavior/9c-dna/hypotheses/RELIANCE?timeframe=1m", 150.0),
    ]
    for endpoint, budget_ms in budgets:
        started = time.perf_counter()
        result = client.get(endpoint).json()["data"]
        observed_ms = (time.perf_counter() - started) * 1000.0
        assert result["latency_ms"] < budget_ms
        assert observed_ms < budget_ms * 2


def test_9c_levelage_001_held_level_scores_above_broken_level_when_present():
    result = client.get("/api/v1/behavior/9c-dna/level-memory/RELIANCE?timeframe=1m").json()["data"]
    assert result["level_memory_version"] == "9c-level-memory-extended.v1"
    assert result["records"]
    assert result["strongest_level"] == result["records"][0]
    for row in result["records"]:
        assert row["touch_count"] == row["hold_count"] + row["break_count"]
        assert 0.0 <= row["level_strength"] <= 1.0
        assert row["last_test_result"] in {"held", "broken"}
        assert row["strength_trend"] in {"improving", "weakening"}


def test_9c_regime_001_analog_scope_is_regime_filtered():
    result = client.get("/api/v1/behavior/9c-dna/regime/RELIANCE?timeframe=1m").json()["data"]
    assert result["regime_gate_version"] == "9c-regime-gate.v1"
    assert result["regime_id"]
    assert result["regime_group"]
    assert result["broader_regime_group"]
    assert result["analog_scope"]["symbol"] == "RELIANCE"
    assert result["analog_scope"]["timeframe"] == "1m"
    assert result["analog_scope"]["regime_id"] == result["regime_id"]
    assert result["regime_match_required"] is True
    assert {gate["gate_id"] for gate in result["gates"]} == {"9C-RG001", "9C-RG002"}


def test_9c_hyp_001_returns_three_hypotheses_with_probabilities_sum_to_one():
    result = client.get("/api/v1/behavior/9c-dna/hypotheses/RELIANCE?timeframe=1m").json()["data"]
    assert result["hypothesis_version"] == "9c-hypothesis-engine.v1"
    assert len(result["hypotheses"]) == 3
    assert {item["id"] for item in result["hypotheses"]} == {"continuation", "reversal", "fakeout"}
    assert abs(result["probability_sum"] - 1.0) <= 0.001
    assert result["primary_hypothesis"] == result["hypotheses"][0]
    assert result["calculation_warnings"] == []
    for hypothesis in result["hypotheses"]:
        assert 0.0 <= hypothesis["rule_score"] <= 1.0
        assert 0.0 <= hypothesis["raw_probability"] <= 1.0
        assert hypothesis["invalidation_level"] is not None
        assert hypothesis["confirmation_trigger"] is not None
        assert hypothesis["analog_evidence"]["same_regime_required"] is True


def test_9c_logic_001_hypothesis_references_real_proximity_levels():
    proximity = client.get("/api/v1/behavior/9c-dna/level-proximity/RELIANCE?timeframe=1m").json()["data"]
    result = client.get("/api/v1/behavior/9c-dna/hypotheses/RELIANCE?timeframe=1m").json()["data"]
    level_names = {row["level_name"] for row in proximity["records"]}
    factor_text = " ".join(
        factor
        for hypothesis in result["hypotheses"]
        for factor in hypothesis["supporting_factors"] + hypothesis["opposing_factors"]
    )
    assert any(name in factor_text for name in level_names)


def test_9c_logic_002_invalidation_is_on_opposite_side_of_direction():
    result = client.get("/api/v1/behavior/9c-dna/hypotheses/RELIANCE?timeframe=1m").json()["data"]
    latest_close = client.get("/api/v1/behavior/9c-dna/level-proximity/RELIANCE?timeframe=1m").json()["data"]["latest_close"]
    for hypothesis in result["hypotheses"]:
        if hypothesis["direction"] == "LONG":
            assert hypothesis["invalidation_level"] < latest_close
        if hypothesis["direction"] == "SHORT":
            assert hypothesis["invalidation_level"] > latest_close


def test_9c_logic_004_hypothesis_output_is_deterministic():
    first = client.get("/api/v1/behavior/9c-dna/hypotheses/RELIANCE?timeframe=1m").json()["data"]
    second = client.get("/api/v1/behavior/9c-dna/hypotheses/RELIANCE?timeframe=1m").json()["data"]
    assert first["output_hash"] == second["output_hash"]
    assert first["primary_hypothesis"] == second["primary_hypothesis"]


def test_9c_pit_level_memory_regime_hypotheses_are_safe_and_closed_only():
    endpoints = [
        "/api/v1/behavior/9c-dna/level-memory/RELIANCE?timeframe=1m",
        "/api/v1/behavior/9c-dna/regime/RELIANCE?timeframe=1m",
        "/api/v1/behavior/9c-dna/hypotheses/RELIANCE?timeframe=1m",
    ]
    for endpoint in endpoints:
        result = client.get(endpoint).json()["data"]
        assert result["no_future_leakage"] is True
        assert result["future_bar_blocked"] is True
        assert result["closed_candle_only"] is True
        assert result["trade_allowed"] is False
        assert result["order_routing_enabled"] is False
        assert result["live_trading_blocked"] is True


def test_9c_path_001_analogs_return_real_counts_not_hardcoded_184():
    result = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m&limit=12").json()["data"]
    assert result["path_analog_version"] == "9c-path-analog-history.v1"
    assert result["hardcoded_match_count_used"] is False
    assert result["total_matches"] == result["winner_like_matches"] + result["failure_like_matches"] + result["neutral_matches"]
    assert result["total_matches"] != 184
    assert result["window_count"] >= result["regime_scoped_window_count"] >= result["total_matches"] > 0
    assert len(result["top_matches"]) == 12
    assert all(match["feature_manifest_version"] == result["feature_manifest_version"] for match in result["top_matches"])


def test_9c_path_002_path_similarity_is_sorted_and_deterministic():
    first = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m&limit=10").json()["data"]
    second = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m&limit=10").json()["data"]
    assert first["output_hash"] == second["output_hash"]
    scores = [match["similarity_score"] for match in first["top_matches"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)


def test_9c_ood_001_threshold_comes_from_historical_distribution():
    result = client.get("/api/v1/behavior/9c-dna/ood-status/RELIANCE?timeframe=1m").json()["data"]
    assert result["ood_version"] == "9c-ood-status.v1"
    assert result["threshold_source"] == "historical_knn_distance_p95"
    assert result["knn_distance_95th_percentile"] is not None
    assert result["nearest_distance"] is not None
    assert result["gate"]["gate_id"] == "9C-G013"
    assert result["gate"]["status"] in {"pass", "wait"}
    assert "volatility_ood" in result
    assert result["volatility_gate"]["gate_id"] == "9C-G016"
    assert result["volatility_status"]["threshold_source"] == "historical_atr_p90"


def test_9c_vol_001_current_atr_above_historical_p90_sets_volatility_ood():
    from app.behavior.nine_candle_history import _volatility_status

    current = {"atr": 8.0}
    windows = [{"atr": value} for value in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.0]]
    result = _volatility_status(current, windows)

    assert result["volatility_ood"] is True
    assert result["volatility_bucket"] == "extreme"
    assert result["gate"]["gate_id"] == "9C-G016"
    assert result["gate"]["status"] == "wait"


def test_9c_vol_002_path_analogs_expose_volatility_bucket_fields():
    result = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m&limit=12").json()["data"]
    assert result["hardcoded_match_count_used"] is False
    assert result["volatility_bucketed"] is True
    assert "volatility_status" in result
    assert "matched_after_vol_bucketing" in result
    assert result["volatility_gate"]["gate_id"] == "9C-G016"


def test_9c_recency_001_temporal_diversity_and_recency_are_visible():
    result = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m&limit=15").json()["data"]
    assert result["recency_weight_applied"] is True
    assert result["per_week_cap_applied"] is True
    assert 0.0 <= result["temporal_diversity_score"] <= 1.0
    assert all(0.60 <= match["recency_weight"] <= 1.0 for match in result["top_matches"])


def test_9c_path_003_forward_labels_use_conservative_stop_first():
    result = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m&limit=25").json()["data"]
    labels = {match["outcome_label"] for match in result["top_matches"]}
    assert labels
    assert labels <= {"TARGET_HIT", "SL_HIT", "FAKE_BREAKOUT", "CHOP_NO_FOLLOWTHROUGH", "TIME_EXIT"}
    assert any(match["stop_first"] or match["target_first"] or match["outcome_label"] == "TIME_EXIT" for match in result["top_matches"])


def test_9c_pit_path_analogs_and_ood_are_safe_and_closed_only():
    endpoints = [
        "/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m",
        "/api/v1/behavior/9c-dna/ood-status/RELIANCE?timeframe=1m",
    ]
    for endpoint in endpoints:
        result = client.get(endpoint).json()["data"]
        assert result["no_future_leakage"] is True
        assert result["future_bar_blocked"] is True
        assert result["closed_candle_only"] is True
        assert result["trade_allowed"] is False
        assert result["order_routing_enabled"] is False
        assert result["live_trading_blocked"] is True


def test_9c_decision_uses_path_analog_counts_instead_of_fixed_mock_values():
    path = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m").json()["data"]
    decision_panel = client.get("/api/v1/behavior/9c-dna/decision/RELIANCE?timeframe=1m").json()["data"]
    memory = decision_panel["memory"]
    decision = decision_panel["hybrid_decision"]
    assert memory["analog_version"] == "winner-failure-analog.v2.1.path-derived"
    assert memory["total_matches"] == path["total_matches"]
    assert memory["winner_like_matches"] == path["winner_like_matches"]
    assert memory["failure_like_matches"] == path["failure_like_matches"]
    assert memory["total_matches"] != 184
    assert memory["active_index_hash"] == path["output_hash"]
    assert str(path["total_matches"]) in decision["final_reason"]


def test_9c_decision_includes_ood_and_temporal_diversity_gates():
    decision_panel = client.get("/api/v1/behavior/9c-dna/decision/RELIANCE?timeframe=1m").json()["data"]
    gates = {gate["gate_id"]: gate for gate in decision_panel["hybrid_decision"]["safety_gates"]}
    assert gates["9C-G016"]["name"] == "Volatility and shape OOD"
    assert gates["9C-G016"]["status"] in {"pass", "wait"}
    assert "volatility=" in gates["9C-G016"]["evidence"]
    assert gates["9C-G017"]["name"] == "Temporal diversity"
    assert gates["9C-G017"]["status"] in {"pass", "wait"}
    assert "total_matches=" in gates["9C-G017"]["evidence"]


def test_9c_cal_001_model_status_is_evidence_derived_but_mock_blocked():
    path = client.get("/api/v1/behavior/9c-dna/path-analogs/RELIANCE?timeframe=1m").json()["data"]
    model = client.get("/api/v1/behavior/9c-dna/model-status?symbol=RELIANCE&timeframe=1m").json()["data"]
    expected_target = round((path["winner_like_matches"] + 2.0) / (path["total_matches"] + 6.0), 6)
    expected_stop = round((path["failure_like_matches"] + 2.0) / (path["total_matches"] + 6.0), 6)
    assert model["model_version"] == "mock"
    assert model["calibrated_target_prob"] == expected_target
    assert model["calibrated_stop_prob"] == expected_stop
    assert model["model_edge"] == round(expected_target - expected_stop, 6)
    assert model["usable_for_probability"] is False
    assert model["paper_candidate_allowed"] is False
    assert model["weights_mutated_live"] is False
    assert model["live_retraining_enabled"] is False


def test_9c_cal_002_calibration_bins_are_derived_from_path_matches():
    bins = client.get("/api/v1/behavior/9c-dna/calibration?symbol=RELIANCE&timeframe=1m").json()["data"]
    assert bins
    assert sum(row["sample_count"] for row in bins) == 25
    assert all(0.0 <= row["actual_target_rate"] <= 1.0 for row in bins)
    assert all(0.0 <= row["actual_stop_rate"] <= 1.0 for row in bins)
    assert all(0.0 <= row["calibration_error"] <= 1.0 for row in bins)
    assert {row["predicted_bucket"] for row in bins} != {"0.40-0.50", "0.50-0.60", "0.60-0.70"}


def test_9c_paper_001_model_promotion_guard_blocks_mock_model():
    guard = client.get("/api/v1/behavior/9c-dna/model-promotion-guard?symbol=RELIANCE&timeframe=1m").json()["data"]
    assert guard["promotion_guard_version"] == "9c-model-promotion-guard.v1"
    assert guard["model_version"] == "mock"
    assert guard["usable_for_probability"] is False
    assert guard["paper_candidate_allowed"] is False
    assert guard["promotion_allowed"] is False
    assert "model_version=mock" in guard["block_reasons"]
    assert guard["trade_allowed"] is False
    assert guard["order_routing_enabled"] is False
    assert guard["live_trading_blocked"] is True


def test_9c_arbiter_001_manipulated_flag_overrides_to_wait():
    from app.behavior.nine_candle_reasoning_arbiter import build_reasoning_arbiter_report

    report = build_reasoning_arbiter_report(
        "RELIANCE",
        "1m",
        analog_report={"winner_similarity": 0.91, "failure_similarity": 0.12},
        path_report={"volatility_ood": False, "temporal_diversity_score": 0.65},
        ood_report={"ood_flag": False, "shape_ood": False, "volatility_ood": False},
        condition_tags=["manipulated_looking"],
        subsystem_votes={"analog": "LONG", "risk": "LONG", "htf": "LONG"},
    )
    assert report["arbiter_version"] == "9c-reasoning-arbiter.v0.74"
    assert "manipulated_looking" in report["consulted_flags"]
    assert report["override_to_wait"] is True
    assert report["continuation_boost"] <= 0.0
    assert report["paper_candidate_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_9c_disagree_001_hard_conflict_forces_confidence_penalty():
    from app.behavior.nine_candle_reasoning_arbiter import build_subsystem_disagreement_report

    report = build_subsystem_disagreement_report({"analog": "LONG", "risk": "WAIT", "htf": "SHORT"})
    assert report["disagreement_state"] == "hard_conflict"
    assert report["confidence_penalty"] == 1.0
    assert report["confidence_action"] == "force_wait"


def test_9c_audit_001_decision_audit_hash_is_deterministic():
    from app.behavior.nine_candle_reasoning_arbiter import build_decision_audit_record, build_reasoning_arbiter_report

    arbiter = build_reasoning_arbiter_report(
        "RELIANCE",
        "1m",
        analog_report={"winner_similarity": 0.66, "failure_similarity": 0.41},
        ood_report={"ood_flag": False, "shape_ood": False, "volatility_ood": False},
        subsystem_votes={"analog": "LONG", "risk": "WAIT", "htf": "WAIT"},
    )
    gates = [{"gate_id": "9C-G019", "name": "Reasoning arbiter override", "status": "pass", "evidence": "No arbiter override."}]
    first = build_decision_audit_record("RELIANCE", "1m", arbiter_report=arbiter, decision="WAIT", safety_gates=gates)
    second = build_decision_audit_record("RELIANCE", "1m", arbiter_report=arbiter, decision="WAIT", safety_gates=gates)
    assert first["audit_version"] == "9c-decision-audit.v0.74"
    assert first["audit_hash"] == second["audit_hash"]
    assert first["trade_allowed"] is False
    assert first["order_routing_enabled"] is False
    assert first["live_trading_blocked"] is True


def test_9c_drift_001_active_drift_demotes_calibrator_to_rule_only():
    from app.behavior.nine_candle_reasoning_arbiter import build_calibration_drift_report

    report = build_calibration_drift_report(predicted_error_rate=0.05, realized_error_rate=0.32, latency_ms=90.0)
    assert report["drift_version"] == "9c-calibration-drift-monitor.v0.74"
    assert report["prediction_drift"] is True
    assert report["label_drift"] is True
    assert report["active_drift_block"] is True
    assert report["gate"]["gate_id"] == "9C-G018"
    assert report["gate"]["status"] == "wait"
    assert report["calibrator_action"] == "demote_to_rule_only"


def test_9c_decision_includes_arbiter_audit_and_drift_gates():
    panel = client.get("/api/v1/behavior/9c-dna/decision/RELIANCE?timeframe=1m").json()["data"]
    decision = panel["hybrid_decision"]
    gates = {gate["gate_id"]: gate for gate in decision["safety_gates"]}
    assert gates["9C-G018"]["name"] == "Calibration drift monitor"
    assert gates["9C-G018"]["status"] in {"pass", "wait"}
    assert gates["9C-G019"]["name"] == "Reasoning arbiter override"
    assert gates["9C-G019"]["status"] in {"pass", "wait"}
    assert "Arbiter=" in decision["final_reason"]
    assert "Audit=" in decision["final_reason"]
    assert decision["decision"] in {"WAIT", "WATCH"}


def test_9c_cal_003_decision_uses_same_evidence_derived_model_status():
    model = client.get("/api/v1/behavior/9c-dna/model-status?symbol=RELIANCE&timeframe=1m").json()["data"]
    panel = client.get("/api/v1/behavior/9c-dna/decision/RELIANCE?timeframe=1m").json()["data"]
    assert panel["model"]["calibrated_target_prob"] == model["calibrated_target_prob"]
    assert panel["model"]["calibrated_stop_prob"] == model["calibrated_stop_prob"]
    assert panel["hybrid_decision"]["model_edge"] == model["model_edge"]


def test_behavior_replay_indicator_chart_validation_is_deterministic_and_safe():
    payload = {
        "symbol": "INFY",
        "scenario_id": "mock_opening_drive",
        "seed": 123,
        "event_count": 24,
        "timeframe": "1m",
    }
    first = client.post("/api/v1/behavior/replay/indicator-chart/validate", json=payload)
    second = client.post("/api/v1/behavior/replay/indicator-chart/validate", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["validation_version"] == "behavior-replay-indicator-chart.v0.33"
    assert first_result["input_event_chain_hash"] == second_result["input_event_chain_hash"]
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["event_count"] == 24
    assert first_result["candle_count"] == 24
    assert first_result["indicator_count"] >= 6
    assert first_result["chart_point_count"] == 24
    assert len(first_result["indicator_points"]) == 24
    assert len(first_result["chart_points"]) == 24
    assert first_result["no_future_leakage"] is True
    assert first_result["runtime_dependency_on_legacy_stock_app"] is False
    assert first_result["safe_mode"] is True
    assert first_result["live_trading_blocked"] is True
    assert all(gate["status"] == "pass" for gate in first_result["gates"])
    assert first_result["indicator_points"][0]["sequence_number"] == 1
    assert "vwap" in first_result["chart_points"][-1]["indicator_overlay"]

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorReplayIndicatorChartValidation" in pipeline_steps


def test_behavior_replay_indicator_matrix_expands_replay_outputs_safely():
    payload = {
        "symbol": "INFY",
        "scenario_id": "mock_opening_drive",
        "seed": 123,
        "event_count": 24,
        "timeframe": "1m",
        "required_matrix_rows": 32,
    }
    first = client.post("/api/v1/behavior/replay/indicator-matrix/validate", json=payload)
    second = client.post("/api/v1/behavior/replay/indicator-matrix/validate", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["matrix_version"] == "behavior-replay-indicator-matrix.v0.34"
    assert first_result["base_validation_version"] == "behavior-replay-indicator-chart.v0.33"
    assert first_result["base_output_hash"] == second_result["base_output_hash"]
    assert first_result["input_event_chain_hash"] == second_result["input_event_chain_hash"]
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["base_indicator_count"] == 6
    assert first_result["matrix_indicator_count"] == 32
    assert first_result["chart_point_count"] == 24
    assert first_result["ready_rows"] >= 10
    assert first_result["proxy_rows"] >= 10
    assert first_result["blocked_rows"] == 0
    assert first_result["deterministic"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["runtime_dependency_on_legacy_stock_app"] is False
    assert first_result["safe_mode"] is True
    assert first_result["live_trading_blocked"] is True
    assert all(gate["status"] == "pass" for gate in first_result["gates"])
    row_ids = {row["row_id"] for row in first_result["rows"]}
    for required in {
        "vwap_distance_pct",
        "breakout_quality_score",
        "fakeout_risk_score",
        "absorption_score",
        "liquidity_score",
        "slippage_risk_proxy",
        "no_trade_safety_pressure",
    }:
        assert required in row_ids
    assert all(row["point_in_time_safe"] is True for row in first_result["rows"])
    assert all(row["contract_name"] and row["required_inputs"] and row["output_fields"] for row in first_result["rows"])

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorReplayIndicatorMatrix" in pipeline_steps


def test_behavior_matrix_decision_readiness_blocks_live_orders_and_is_deterministic():
    payload = {
        "symbol": "INFY",
        "scenario_id": "mock_opening_drive",
        "seed": 123,
        "event_count": 24,
        "timeframe": "1m",
        "required_matrix_rows": 32,
        "min_agreement_score": 0.55,
        "max_safety_pressure": 0.62,
    }
    first = client.post("/api/v1/behavior/decision/readiness/validate", json=payload)
    second = client.post("/api/v1/behavior/decision/readiness/validate", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["readiness_version"] == "behavior-matrix-decision-readiness.v0.35"
    assert first_result["base_matrix_version"] == "behavior-replay-indicator-matrix.v0.34"
    assert first_result["matrix_output_hash"] == second_result["matrix_output_hash"]
    assert first_result["input_event_chain_hash"] == second_result["input_event_chain_hash"]
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["matrix_indicator_count"] == 32
    assert first_result["ready_rows"] >= 10
    assert first_result["proxy_rows"] >= 10
    assert first_result["blocked_rows"] == 0
    assert first_result["directional_bias"] in {"LONG", "SHORT", "NEUTRAL"}
    assert first_result["readiness_action"] in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE", "WAIT", "NO_TRADE", "BLOCK"}
    assert first_result["trade_allowed"] is False
    assert first_result["order_routing_enabled"] is False
    assert first_result["live_trading_blocked"] is True
    assert first_result["narrative_read_only"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["deterministic"] is True
    assert 0 <= first_result["confidence_score"] <= 1
    assert 0 <= first_result["agreement_score"] <= 1
    assert 0 <= first_result["safety_score"] <= 1
    assert first_result["gate_summary"]["pass"] + first_result["gate_summary"]["fail"] == len(first_result["gates"])
    assert {gate["gate_id"] for gate in first_result["gates"]} >= {"TV-V035-001", "TV-V035-005", "TV-V035-007", "TV-V035-008"}
    assert "order" in first_result["notes"][1].lower()
    assert first_result["used_row_ids"]

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorMatrixDecisionReadiness" in pipeline_steps


def test_behavior_trade_lifecycle_simulation_honors_readiness_and_blocks_live_routes():
    payload = {
        "symbol": "INFY",
        "scenario_id": "mock_opening_drive",
        "seed": 123,
        "event_count": 24,
        "timeframe": "1m",
        "required_matrix_rows": 32,
        "min_agreement_score": 0.55,
        "max_safety_pressure": 0.62,
        "entry_after_bars": 5,
        "shadow_quantity": 25,
        "max_holding_bars": 18,
        "respect_readiness_block": True,
    }
    first = client.post("/api/v1/behavior/lifecycle/validate", json=payload)
    second = client.post("/api/v1/behavior/lifecycle/validate", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["lifecycle_version"] == "behavior-trade-lifecycle-simulation.v0.36"
    assert first_result["base_readiness_version"] == "behavior-matrix-decision-readiness.v0.35"
    assert first_result["base_chart_version"] == "behavior-replay-indicator-chart.v0.33"
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["input_event_chain_hash"] == second_result["input_event_chain_hash"]
    assert first_result["readiness_output_hash"] == second_result["readiness_output_hash"]
    assert first_result["execution_simulation_id"] == second_result["execution_simulation_id"]
    assert first_result["outcome_run_id"] == second_result["outcome_run_id"]
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["deterministic"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["simulation_only"] is True
    assert first_result["trade_allowed"] is False
    assert first_result["order_routing_enabled"] is False
    assert first_result["live_trading_blocked"] is True
    assert first_result["narrative_read_only"] is True
    assert first_result["readiness"]["trade_allowed"] is False
    assert first_result["execution"]["simulation_only"] is True
    assert first_result["execution"]["live_route_attempted"] is False
    if first_result["readiness_action"] in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE"}:
        assert first_result["execution"]["requested_quantity"] == payload["shadow_quantity"]
        assert first_result["lifecycle_status"] in {"SHADOW_SIMULATED", "SHADOW_NO_FILL", "SHADOW_REJECTED"}
        assert first_result["trade_state_path"][:3] == ["WAITING", "SIGNAL_FORMING", "ENTRY_READY"]
    else:
        assert first_result["execution"]["requested_quantity"] == 0
        assert first_result["execution"]["fill_status"] == "REJECTED_SIMULATION"
        assert first_result["lifecycle_status"] == "BLOCKED_BY_READINESS"
        assert first_result["trade_state_path"] == ["WAITING", "SIGNAL_FORMING", "INVALIDATED"]
    assert first_result["outcome"]["outcome_label"] in {
        "TARGET_HIT",
        "SL_HIT",
        "PARTIAL_WIN",
        "BREAKEVEN",
        "TIME_EXIT",
        "FAKE_BREAKOUT",
        "RETEST_SUCCESS",
        "RETEST_FAIL",
        "CHOP_NO_FOLLOWTHROUGH",
    }
    assert first_result["entry_type"] == "NEXT_5M_OPEN_SHADOW"
    assert first_result["risk_reward"] >= 2.9
    assert first_result["lifecycle_gate_summary"]["pass"] + first_result["lifecycle_gate_summary"]["fail"] == len(first_result["gates"])
    assert {gate["gate_id"] for gate in first_result["gates"]} >= {"TV-V036-001", "TV-V036-003", "TV-V036-004", "TV-V036-007"}
    assert "cannot approve" in first_result["reason"].lower() or "blocked before entry" in first_result["reason"].lower()

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorTradeLifecycleSimulation" in pipeline_steps


def test_behavior_lifecycle_scenario_comparison_is_deterministic_and_shadow_only():
    payload = {
        "symbol": "INFY",
        "timeframe": "1m",
        "event_count": 24,
        "required_matrix_rows": 32,
        "min_agreement_score": 0.55,
        "max_safety_pressure": 0.62,
        "entry_after_bars": 5,
        "shadow_quantity": 25,
        "max_holding_bars": 18,
        "respect_readiness_block": True,
        "scenarios": [
            {"label": "default blocked", "scenario_id": "mock_opening_drive", "seed": 42},
            {"label": "candidate probe", "scenario_id": "mock_opening_drive", "seed": 123, "max_safety_pressure": 0.70},
            {"label": "fakeout probe", "scenario_id": "mock_fakeout_pressure", "seed": 7},
            {"label": "liquidity stress", "scenario_id": "mock_liquidity_stress", "seed": 99, "max_safety_pressure": 0.55},
        ],
    }
    first = client.post("/api/v1/behavior/lifecycle/compare", json=payload)
    second = client.post("/api/v1/behavior/lifecycle/compare", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["comparison_version"] == "behavior-lifecycle-scenario-comparison.v0.37"
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["scenario_count"] == 4
    assert len(first_result["items"]) == 4
    assert first_result["candidate_count"] >= 1
    assert first_result["blocked_count"] >= 1
    assert first_result["all_trade_allowed_false"] is True
    assert first_result["all_order_routing_disabled"] is True
    assert first_result["all_live_trading_blocked"] is True
    assert first_result["all_simulation_only"] is True
    assert first_result["deterministic"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["best_scenario_label"]
    assert first_result["worst_scenario_label"]
    assert first_result["average_MFE"] >= 0
    assert first_result["average_MAE"] >= 0
    for first_item, second_item in zip(first_result["items"], second_result["items"]):
        assert first_item["output_hash"] == second_item["output_hash"]
        assert first_item["trade_allowed"] is False
        assert first_item["live_trading_blocked"] is True
        assert first_item["no_future_leakage"] is True
        assert first_item["readiness_action"] in {"REPLAY_BUY_CANDIDATE", "REPLAY_SELL_CANDIDATE", "WAIT", "NO_TRADE", "BLOCK"}
        assert first_item["lifecycle_status"] in {"BLOCKED_BY_READINESS", "SHADOW_SIMULATED", "SHADOW_NO_FILL", "SHADOW_REJECTED"}
        assert first_item["trade_state_path"]
    assert {gate["gate_id"] for gate in first_result["gates"]} >= {"TV-V037-001", "TV-V037-004", "TV-V037-005", "TV-V037-006", "TV-V037-007"}
    assert all(gate["status"] == "pass" for gate in first_result["gates"])

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorLifecycleScenarioComparison" in pipeline_steps

    panel_ids = {panel["panel_id"] for panel in client.get("/api/v1/behavior/frontend/panel-map").json()["data"]["panels"]}
    assert "lifecycle_scenario_comparison" in panel_ids


def test_behavior_lifecycle_evidence_drilldown_explains_rows_and_stays_safe():
    payload = {
        "symbol": "INFY",
        "timeframe": "1m",
        "event_count": 24,
        "required_matrix_rows": 32,
        "min_agreement_score": 0.55,
        "max_safety_pressure": 0.62,
        "entry_after_bars": 5,
        "shadow_quantity": 25,
        "max_holding_bars": 18,
        "respect_readiness_block": True,
        "top_n_rows": 4,
        "scenarios": [
            {"label": "default blocked", "scenario_id": "mock_opening_drive", "seed": 42},
            {"label": "candidate probe", "scenario_id": "mock_opening_drive", "seed": 123, "max_safety_pressure": 0.70},
            {"label": "fakeout probe", "scenario_id": "mock_fakeout_pressure", "seed": 7},
            {"label": "liquidity stress", "scenario_id": "mock_liquidity_stress", "seed": 99, "max_safety_pressure": 0.55},
        ],
    }
    first = client.post("/api/v1/behavior/lifecycle/evidence", json=payload)
    second = client.post("/api/v1/behavior/lifecycle/evidence", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["evidence_version"] == "behavior-lifecycle-evidence-drilldown.v0.38"
    assert first_result["base_comparison_version"] == "behavior-lifecycle-scenario-comparison.v0.37"
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["comparison_output_hash"] == second_result["comparison_output_hash"]
    assert first_result["scenario_count"] == 4
    assert len(first_result["items"]) == 4
    assert first_result["dominant_directional_driver"]
    assert first_result["dominant_safety_pressure"]
    assert first_result["all_trade_allowed_false"] is True
    assert first_result["all_order_routing_disabled"] is True
    assert first_result["all_live_trading_blocked"] is True
    assert first_result["deterministic"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["narrative_read_only"] is True
    for item in first_result["items"]:
        assert item["trade_allowed"] is False
        assert item["order_routing_enabled"] is False
        assert item["live_trading_blocked"] is True
        assert item["no_future_leakage"] is True
        assert item["top_directional_drivers"] or item["top_counter_drivers"]
        assert item["top_safety_pressures"]
        assert "live routing remains blocked" in item["reason"]
        for contribution in item["top_directional_drivers"] + item["top_counter_drivers"] + item["top_safety_pressures"]:
            assert contribution["row_id"]
            assert contribution["contract_name"]
            assert 0 <= contribution["contribution_score"] <= 1
            assert contribution["readiness_status"] in {"ready", "proxy", "blocked"}
    assert {gate["gate_id"] for gate in first_result["gates"]} >= {
        "TV-V038-001",
        "TV-V038-002",
        "TV-V038-003",
        "TV-V038-004",
        "TV-V038-005",
        "TV-V038-006",
        "TV-V038-007",
        "TV-V038-008",
        "TV-V038-009",
    }
    assert all(gate["status"] == "pass" for gate in first_result["gates"])

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorLifecycleEvidenceDrilldown" in pipeline_steps

    panel_ids = {panel["panel_id"] for panel in client.get("/api/v1/behavior/frontend/panel-map").json()["data"]["panels"]}
    assert "lifecycle_evidence_drilldown" in panel_ids

    capabilities = {item["name"] for item in client.get("/api/system/features").json()["data"]["capabilities"]}
    assert "Behavior Lifecycle Evidence Drilldown" in capabilities


def test_behavior_tradeability_guidance_turns_evidence_into_research_only_actions():
    payload = {
        "symbol": "INFY",
        "timeframe": "1m",
        "event_count": 24,
        "required_matrix_rows": 32,
        "min_agreement_score": 0.55,
        "max_safety_pressure": 0.62,
        "entry_after_bars": 5,
        "shadow_quantity": 25,
        "max_holding_bars": 18,
        "respect_readiness_block": True,
        "top_n_rows": 4,
        "guidance_threshold": 0.58,
        "scenarios": [
            {"label": "default blocked", "scenario_id": "mock_opening_drive", "seed": 42},
            {"label": "candidate probe", "scenario_id": "mock_opening_drive", "seed": 123, "max_safety_pressure": 0.70},
            {"label": "fakeout probe", "scenario_id": "mock_fakeout_pressure", "seed": 7},
            {"label": "liquidity stress", "scenario_id": "mock_liquidity_stress", "seed": 99, "max_safety_pressure": 0.55},
        ],
    }
    first = client.post("/api/v1/behavior/tradeability", json=payload)
    second = client.post("/api/v1/behavior/tradeability", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["guidance_version"] == "behavior-lifecycle-tradeability-guidance.v0.39"
    assert first_result["base_evidence_version"] == "behavior-lifecycle-evidence-drilldown.v0.38"
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["evidence_output_hash"] == second_result["evidence_output_hash"]
    assert first_result["scenario_count"] == 4
    assert len(first_result["items"]) == 4
    assert first_result["top_global_blocker"]
    assert first_result["safest_scenario_label"]
    assert first_result["riskiest_scenario_label"]
    assert first_result["promotion_allowed"] is False
    assert first_result["all_trade_allowed_false"] is True
    assert first_result["all_order_routing_disabled"] is True
    assert first_result["all_live_trading_blocked"] is True
    assert first_result["deterministic"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["narrative_read_only"] is True
    statuses = {item["tradeability_status"] for item in first_result["items"]}
    assert statuses <= {"BLOCKED", "AVOID", "RESEARCH_WATCH", "REPLAY_CANDIDATE_RESEARCH_ONLY"}
    assert "BLOCKED" in statuses
    for item in first_result["items"]:
        assert item["must_remain_simulation_only"] is True
        assert item["trade_allowed"] is False
        assert item["order_routing_enabled"] is False
        assert item["live_trading_blocked"] is True
        assert item["no_future_leakage"] is True
        assert 0 <= item["tradeability_score"] <= 1
        assert item["improvement_steps"]
        assert item["promotion_blockers"]
        assert "cannot route orders" in item["reason"]
        assert any(step["category"] == "permission_lock" and step["blocks_promotion"] for step in item["improvement_steps"])
    assert {gate["gate_id"] for gate in first_result["gates"]} >= {
        "TV-V039-001",
        "TV-V039-002",
        "TV-V039-003",
        "TV-V039-004",
        "TV-V039-005",
        "TV-V039-006",
        "TV-V039-007",
        "TV-V039-008",
        "TV-V039-009",
        "TV-V039-010",
    }
    assert all(gate["status"] == "pass" for gate in first_result["gates"])

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorTradeabilityGuidance" in pipeline_steps

    panel_ids = {panel["panel_id"] for panel in client.get("/api/v1/behavior/frontend/panel-map").json()["data"]["panels"]}
    assert "tradeability_guidance" in panel_ids

    capabilities = {item["name"] for item in client.get("/api/system/features").json()["data"]["capabilities"]}
    assert "Behavior Tradeability Guidance" in capabilities


def test_behavior_chart_replay_workbench_exposes_visual_evidence_without_order_power():
    payload = {
        "symbol": "INFY",
        "scenario_id": "mock_opening_drive",
        "seed": 123,
        "event_count": 24,
        "timeframe": "1m",
        "selected_sequence_number": 8,
    }
    first = client.post("/api/v1/behavior/chart/replay", json=payload)
    second = client.post("/api/v1/behavior/chart/replay", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["chart_version"] == "behavior-chart-replay-workbench.v0.41"
    assert first_result["base_validation_version"] == "behavior-replay-indicator-chart.v0.33"
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["candle_count"] == 24
    assert first_result["chart_point_count"] == 24
    assert first_result["selected_sequence_number"] == 8
    assert first_result["viewport"]["candle_count"] == 24
    assert first_result["viewport"]["min_price"] < first_result["viewport"]["max_price"]
    assert len(first_result["chart_points"]) == 24
    assert len(first_result["overlays"]) >= 6
    overlay_keys = {overlay["overlay_key"] for overlay in first_result["overlays"]}
    assert {"ema_5", "vwap", "sma_3", "rsi_5", "macd_fast_slow", "volume_z"} <= overlay_keys
    selected = first_result["selected_candle"]
    assert selected["sequence_number"] == 8
    assert selected["candle_direction"] in {"bullish", "bearish", "neutral"}
    assert 0 <= selected["body_pct"] <= 1
    assert selected["evidence_rows"]
    assert "vwap" in selected["overlay_values"]
    assert first_result["deterministic"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["runtime_dependency_on_legacy_stock_app"] is False
    assert first_result["trade_allowed"] is False
    assert first_result["order_routing_enabled"] is False
    assert first_result["live_trading_blocked"] is True
    assert all(gate["status"] == "pass" for gate in first_result["gates"])
    assert {gate["gate_id"] for gate in first_result["gates"]} >= {"TV-V041-001", "TV-V041-004", "TV-V041-006"}

    current = client.get("/api/v1/behavior/chart/replay/current")
    assert current.status_code == 200
    assert current.json()["data"]["chart_version"] == "behavior-chart-replay-workbench.v0.41"

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorChartReplayWorkbench" in pipeline_steps

    capabilities = {item["name"] for item in client.get("/api/system/features").json()["data"]["capabilities"]}
    assert "Behavior Chart Replay Workbench" in capabilities


def test_behavior_indicator_expansion_promotes_ready_rows_and_labels_proxies():
    payload = {
        "symbol": "INFY",
        "scenario_id": "mock_opening_drive",
        "seed": 123,
        "event_count": 24,
        "timeframe": "1m",
        "required_matrix_rows": 32,
        "include_proxy": True,
    }
    first = client.post("/api/v1/behavior/indicators/expansion", json=payload)
    second = client.post("/api/v1/behavior/indicators/expansion", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["expansion_version"] == "behavior-indicator-expansion-workbench.v0.42"
    assert first_result["base_matrix_version"] == "behavior-replay-indicator-matrix.v0.34"
    assert first_result["output_hash"] == second_result["output_hash"]
    assert first_result["run_id"] == second_result["run_id"]
    assert first_result["candidate_output_groups"] == 94
    assert first_result["base_indicator_count"] == 6
    assert first_result["matrix_indicator_count"] == 32
    assert first_result["promoted_indicator_count"] >= 10
    assert first_result["proxy_indicator_count"] >= 10
    assert first_result["blocked_indicator_count"] == 0
    assert len(first_result["items"]) == 32
    statuses = {item["status"] for item in first_result["items"]}
    assert "promoted" in statuses
    assert "proxy" in statuses
    assert all(item["point_in_time_safe"] is True for item in first_result["items"])
    assert first_result["family_coverage"]
    assert first_result["deterministic"] is True
    assert first_result["no_future_leakage"] is True
    assert first_result["runtime_dependency_on_legacy_stock_app"] is False
    assert first_result["trade_allowed"] is False
    assert first_result["order_routing_enabled"] is False
    assert first_result["live_trading_blocked"] is True
    assert all(gate["status"] == "pass" for gate in first_result["gates"])
    assert {gate["gate_id"] for gate in first_result["gates"]} >= {"TV-V042-001", "TV-V042-002", "TV-V042-003", "TV-V042-006"}

    current = client.get("/api/v1/behavior/indicators/expansion/current")
    assert current.status_code == 200
    assert current.json()["data"]["expansion_version"] == "behavior-indicator-expansion-workbench.v0.42"

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorIndicatorExpansionWorkbench" in pipeline_steps

    capabilities = {item["name"] for item in client.get("/api/system/features").json()["data"]["capabilities"]}
    assert "Behavior Indicator Expansion Workbench" in capabilities


def test_behavior_real_ohlcv_import_parses_valid_csv_and_can_persist_research_snapshot():
    csv_text = "\n".join(
        [
            "timestamp,open,high,low,close,volume",
            "2026-01-05T09:15:00+05:30,100,101,99.8,100.5,10000",
            "2026-01-05T09:16:00+05:30,100.5,101.2,100.1,101.0,12000",
            "2026-01-05T09:17:00+05:30,101.0,101.4,100.7,101.2,11500",
            "2026-01-05T09:18:00+05:30,101.2,101.8,101.0,101.6,13000",
        ]
    )
    payload = {"symbol": "INFY", "timeframe": "1m", "csv_text": csv_text, "persist_snapshot": True}
    first = client.post("/api/v1/behavior/data/import/ohlcv", json=payload)
    second = client.post("/api/v1/behavior/data/import/ohlcv", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    result = first.json()["data"]
    repeated = second.json()["data"]
    assert result["import_version"] == "behavior-real-ohlcv-import.v0.40"
    assert result["payload_hash"] == repeated["payload_hash"]
    assert result["symbol"] == "INFY"
    assert result["row_count"] == 4
    assert result["parsed_bar_count"] == 4
    assert result["quality"]["blocks_trade"] is False
    assert result["point_in_time"]["blocks_trade"] is False
    assert result["safe_for_research"] is True
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert result["runtime_dependency_on_legacy_stock_app"] is False
    assert result["persisted_snapshot_id"].startswith("user-csv-infy-1m-")
    loaded = client.get(f"/api/data/snapshots/{result['persisted_snapshot_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["schema_version"] == "ohlcv.user_csv.v1"

    pipeline_steps = {step["name"] for step in client.get("/api/system/pipeline").json()["data"]["steps"]}
    assert "BehaviorRealOhlcvImport" in pipeline_steps


def test_behavior_real_ohlcv_import_supports_separate_date_time_columns_and_ist():
    csv_text = "\n".join(
        [
            "date,time,open,high,low,close,volume,oi",
            "2026-03-20,09:15:00,1400,1402,1399,1401,10000,0",
            "2026-03-20,09:16:00,1401,1403,1400,1402,12000,0",
            "2026-03-20,09:17:00,1402,1404,1401,1403,11500,0",
        ]
    )
    response = client.post(
        "/api/v1/behavior/data/import/ohlcv",
        json={
            "symbol": "RELIANCE",
            "timeframe": "1m",
            "csv_text": csv_text,
            "date_column": "date",
            "time_column": "time",
            "timezone_offset_minutes": 330,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["parsed_bar_count"] == 3
    assert result["safe_for_research"] is True
    expected = int(datetime(2026, 3, 20, 9, 15, tzinfo=IST).timestamp() * 1_000_000_000)
    assert result["series"]["bars"][0]["timestamp_ns"] == expected
    assert result["series"]["bars"][0]["source"] == "user_csv"
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_behavior_local_reliance_downloaded_csv_preview_is_bounded_and_safe():
    local_path = Path(r"C:\Users\sakth\Downloads\HSTRY\RELIANCE_NSE_1m.csv")
    if not local_path.exists():
        return
    response = client.get("/api/v1/behavior/data/local/reliance-1m/preview?rows=120&position=tail&persist_snapshot=false")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["symbol"] == "RELIANCE"
    assert result["timeframe"] == "1m"
    assert result["row_count"] == 120
    assert result["parsed_bar_count"] == 120
    assert result["series"]["bars"][-1]["source"] == "user_csv"
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_behavior_real_ohlcv_import_blocks_bad_candles_and_duplicate_timestamps():
    csv_text = "\n".join(
        [
            "timestamp,open,high,low,close,volume",
            "2026-01-05T09:15:00+05:30,100,99,98,100.5,10000",
            "2026-01-05T09:15:00+05:30,100.5,101.2,100.1,101.0,12000",
        ]
    )
    response = client.post(
        "/api/v1/behavior/data/import/ohlcv",
        json={"symbol": "INFY", "timeframe": "1m", "csv_text": csv_text, "persist_snapshot": False},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["import_version"] == "behavior-real-ohlcv-import.v0.40"
    assert result["parsed_bar_count"] == 2
    assert result["quality"]["blocks_trade"] is True
    assert result["quality"]["invalid_ohlc_count"] == 1
    assert result["quality"]["duplicate_timestamp_count"] == 1
    assert result["safe_for_research"] is False
    assert result["persisted_snapshot_id"] is None
    assert result["trade_allowed"] is False
    assert result["live_trading_blocked"] is True


def test_behavior_validation_walk_forward_uses_non_overlapping_folds():
    response = client.get("/api/v1/behavior/validation/walk-forward?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["validation_version"] == "behavior-validation.v0.24"
    assert result["validation_type"] == "walk_forward"
    assert len(result["folds"]) == 3
    assert result["no_future_leakage"] is True
    assert result["deterministic"] is True
    assert result["live_trading_blocked"] is True
    for fold in result["folds"]:
        assert fold["train_end_day"] < fold["test_start_day"]
        assert fold["leakage_pass"] is True
        assert fold["train_samples"] >= 30
        assert fold["test_samples"] >= 10
    assert result["total_trades"] == sum(fold["trade_count"] for fold in result["folds"])


def test_behavior_validation_out_of_sample_has_single_holdout_split():
    response = client.get("/api/v1/behavior/validation/out-of-sample?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["validation_type"] == "out_of_sample"
    assert len(result["folds"]) == 1
    fold = result["folds"][0]
    assert fold["train_start_day"] == 0
    assert fold["train_end_day"] < fold["test_start_day"]
    assert result["no_future_leakage"] is True
    assert result["live_trading_blocked"] is True


def test_behavior_validation_is_deterministic_for_same_seed():
    payload = {
        "symbol": "VALIDATE-DETERMINISTIC",
        "timeframe": "5m",
        "seed": 77,
        "validation_type": "walk_forward",
        "folds": 4,
        "train_days": 45,
        "test_days": 8,
    }
    first = client.post("/api/v1/behavior/validation/run", json=payload)
    second = client.post("/api/v1/behavior/validation/run", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    result = first.json()["data"]
    assert result["deterministic"] is True
    assert result["promotion_allowed"] is (len(result["promotion_blockers"]) == 0)


def test_behavior_drift_current_is_stable_and_promotion_aware():
    response = client.get("/api/v1/behavior/safety/drift/current?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["safety_version"] == "behavior-safety-hardening.v0.25"
    assert result["symbol"] == "INFY"
    assert result["drift_status"] == "stable"
    assert result["memory_quarantine_required"] is False
    assert result["promotion_allowed"] is True
    assert result["confidence_multiplier"] == 1.0


def test_behavior_drift_quarantines_large_distribution_shift():
    payload = {
        "symbol": "DRIFT-BAD",
        "feature_name": "volume_curve_memory",
        "baseline_mean": 0.25,
        "baseline_std": 0.1,
        "live_mean": 0.95,
        "live_std": 0.45,
        "baseline_sample_count": 120,
        "live_sample_count": 60,
    }
    response = client.post("/api/v1/behavior/safety/drift", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["drift_status"] == "quarantine"
    assert result["memory_quarantine_required"] is True
    assert result["confidence_multiplier"] == 0.0
    assert result["promotion_allowed"] is False
    assert any("Memory quarantine" in blocker for blocker in result["promotion_blockers"])


def test_behavior_ood_blocks_confidence_on_hard_outliers():
    payload = {
        "symbol": "OOD-BAD",
        "features": [
            {"feature_name": "volume_z", "current_value": 8.2, "expected_min": -2.5, "expected_max": 2.5, "hard_min": -5.0, "hard_max": 5.0},
            {"feature_name": "gap_pct", "current_value": 7.0, "expected_min": -1.5, "expected_max": 1.5, "hard_min": -6.0, "hard_max": 6.0},
        ],
    }
    response = client.post("/api/v1/behavior/safety/ood", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["ood_status"] == "block"
    assert result["confidence_blocked"] is True
    assert result["trade_blocked"] is True
    assert result["promotion_allowed"] is False
    assert {item["status"] for item in result["feature_results"]} == {"hard_outlier"}


def test_behavior_reality_gap_alerts_on_replay_live_divergence():
    payload = {
        "symbol": "GAP-BAD",
        "replay_slippage_pct": 0.08,
        "observed_slippage_pct": 0.72,
        "replay_fill_rate_pct": 96.0,
        "observed_fill_rate_pct": 61.0,
        "replay_latency_ms": 120,
        "observed_latency_ms": 940,
        "replay_pnl_r": 0.35,
        "observed_pnl_r": -0.65,
    }
    response = client.post("/api/v1/behavior/safety/reality-gap", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["alert"] is True
    assert result["severity"] == "critical"
    assert result["promotion_allowed"] is False
    assert "Replay/live slippage divergence exceeds threshold." in result["promotion_blockers"]
    assert "Replay/live fill-rate divergence exceeds threshold." in result["promotion_blockers"]


def test_behavior_acp_status_summarizes_drift_ood_and_reality_gap_gates():
    response = client.get("/api/v1/behavior/acp/status?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["safety_version"] == "behavior-safety-hardening.v0.25"
    assert result["live_trading_blocked"] is True
    assert result["fail_count"] == 0
    assert result["promotion_allowed"] is True
    check_ids = {check["check_id"] for check in result["checks"]}
    assert {"ACP-20", "ACP-46", "TV-BI-050", "TV-BI-051", "TV-BI-052"} <= check_ids


def test_behavior_safety_report_is_hash_addressed_and_persisted():
    response = client.get("/api/v1/behavior/safety/report/current?symbol=INFY")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["report_version"] == "behavior-operational-safety.v0.26"
    assert report["symbol"] == "INFY"
    assert report["immutable"] is True
    assert report["report_id"].startswith("safety-INFY-")
    assert len(report["report_hash"]) == 64
    assert report["promotion_allowed"] is True
    assert report["memory_quarantine_required"] is False

    loaded = client.get(f"/api/v1/behavior/safety/reports/{report['report_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["report_hash"] == report["report_hash"]

    history = client.get("/api/v1/behavior/safety/reports?symbol=INFY")
    assert history.status_code == 200
    assert report["report_id"] in {item["report_id"] for item in history.json()["data"]}


def test_behavior_stress_report_can_trigger_memory_quarantine_and_rebuild_plan():
    stress = client.post("/api/v1/behavior/safety/report/run?symbol=QUARANTINE-MOCK&stress=true")
    assert stress.status_code == 200
    report = stress.json()["data"]
    assert report["promotion_allowed"] is False
    assert report["memory_quarantine_required"] is True
    assert report["confidence_blocked"] is True
    assert report["reality_gap_alert"] is True

    quarantine = client.post(
        "/api/v1/behavior/memory/quarantine",
        json={
            "symbol": "QUARANTINE-MOCK",
            "reason": "pytest stress report quarantine",
            "source_report_id": report["report_id"],
            "actor_id": "pytest",
        },
    )
    assert quarantine.status_code == 200
    record = quarantine.json()["data"]
    assert record["status"] == "active"
    assert record["memory_promotion_blocked"] is True
    assert record["confidence_blocked"] is True
    assert record["source_report_id"] == report["report_id"]
    assert len(record["affected_memory_ids"]) >= 3
    assert "golden replay fixture verification passed" in record["release_requires"]

    active = client.get("/api/v1/behavior/memory/quarantine?symbol=QUARANTINE-MOCK&active_only=true")
    assert active.status_code == 200
    assert record["quarantine_id"] in {item["quarantine_id"] for item in active.json()["data"]}

    rebuild = client.get("/api/v1/behavior/memory/rebuild-plan/QUARANTINE-MOCK")
    assert rebuild.status_code == 200
    plan = rebuild.json()["data"]
    assert plan["allowed_to_rebuild"] is True
    assert plan["quarantine_id"] == record["quarantine_id"]
    assert plan["estimated_safe_status"] == "shadow_only"
    assert "drift_status == stable" in plan["promotion_gates"]
    assert "no live broker route exists" in plan["promotion_gates"]


def test_golden_replay_fixture_verifies_deterministically_and_blocks_live_trading():
    fixtures = client.get("/api/v1/behavior/replay/golden-fixtures")
    assert fixtures.status_code == 200
    items = fixtures.json()["data"]
    assert len(items) >= 16
    scenario_ids = {item["scenario_id"] for item in items}
    expected_v166_scenarios = {
        "golden_opening_drive",
        "golden_fakeout_reversal",
        "golden_lunch_compression",
        "golden_closing_drive",
        "golden_gap_trap",
        "golden_expiry_pin",
        "golden_9c_clean_breakout",
        "golden_9c_fake_breakout",
        "golden_9c_vwap_rejection",
        "golden_9c_choppy",
        "golden_9c_gap_up_continuation",
        "golden_9c_low_volume",
        "golden_9c_htf_lookahead_trap",
        "golden_9c_near_confluence_support",
        "golden_9c_near_confluence_resistance",
        "golden_9c_ood_unknown",
    }
    assert expected_v166_scenarios <= scenario_ids
    fixture = next(item for item in items if item["fixture_id"] == "golden-nifty-mock-golden-opening-drive-42")
    assert fixture["expected_event_count"] == 12
    assert len(fixture["expected_chain_hash"]) == 64

    first = client.get(f"/api/v1/behavior/replay/golden-fixtures/{fixture['fixture_id']}/verify")
    second = client.get(f"/api/v1/behavior/replay/golden-fixtures/{fixture['fixture_id']}/verify")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    result = first.json()["data"]
    assert result["passed"] is True
    assert result["deterministic"] is True
    assert result["issues"] == []
    assert result["actual_chain_hash"] == fixture["expected_chain_hash"]
    assert result["live_trading_blocked"] is True


def test_v166_golden_fixture_regression_pack_verifies_9c_chart_risk_scenarios():
    fixtures = client.get("/api/v1/behavior/replay/golden-fixtures").json()["data"]
    by_scenario = {item["scenario_id"]: item for item in fixtures}
    required = {
        "golden_9c_clean_breakout",
        "golden_9c_fake_breakout",
        "golden_9c_vwap_rejection",
        "golden_9c_choppy",
        "golden_9c_gap_up_continuation",
        "golden_9c_low_volume",
        "golden_9c_htf_lookahead_trap",
        "golden_9c_near_confluence_support",
        "golden_9c_near_confluence_resistance",
        "golden_9c_ood_unknown",
    }
    assert required <= set(by_scenario)
    for scenario_id in sorted(required):
        fixture = by_scenario[scenario_id]
        assert fixture["expected_event_count"] == 12
        assert len(fixture["expected_chain_hash"]) == 64
        assert "fixture verification cannot enable live trading" in fixture["safety_assertions"]
        first = client.get(f"/api/v1/behavior/replay/golden-fixtures/{fixture['fixture_id']}/verify")
        second = client.get(f"/api/v1/behavior/replay/golden-fixtures/{fixture['fixture_id']}/verify")
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["data"] == second.json()["data"]
        verified = first.json()["data"]
        assert verified["passed"] is True
        assert verified["deterministic"] is True
        assert verified["issues"] == []
        assert verified["actual_chain_hash"] == fixture["expected_chain_hash"]
        assert verified["live_trading_blocked"] is True


def test_behavior_benchmark_report_persists_validation_safety_and_replay_evidence():
    response = client.get("/api/v1/behavior/benchmark/report/current?symbol=INFY")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["report_version"] == "behavior-release-control.v0.27"
    assert report["symbol"] == "INFY"
    assert report["immutable"] is True
    assert report["live_trading_blocked"] is True
    assert report["report_id"].startswith("benchmark-INFY-")
    assert len(report["report_hash"]) == 64
    assert report["walk_forward"]["validation_type"] == "walk_forward"
    assert report["out_of_sample"]["validation_type"] == "out_of_sample"
    assert len(report["golden_replay_verifications"]) >= 6
    assert report["metrics"]["golden_replay_pass_count"] == report["metrics"]["golden_replay_total"]
    assert report["metrics"]["total_validation_trades"] == (
        report["walk_forward"]["total_trades"] + report["out_of_sample"]["total_trades"]
    )

    loaded = client.get(f"/api/v1/behavior/benchmark/reports/{report['report_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["report_hash"] == report["report_hash"]

    history = client.get("/api/v1/behavior/benchmark/reports?symbol=INFY")
    assert history.status_code == 200
    assert report["report_id"] in {item["report_id"] for item in history.json()["data"]}


def test_mock_to_replay_release_checklist_requires_manual_approval_and_blocks_live():
    response = client.get("/api/v1/behavior/release/mock-to-replay/checklist?symbol=INFY")
    assert response.status_code == 200
    checklist = response.json()["data"]
    assert checklist["checklist_version"] == "behavior-release-control.v0.27"
    assert checklist["target_mode"] == "REPLAY"
    assert checklist["manual_approval_required"] is True
    assert checklist["live_trading_blocked"] is True
    assert checklist["release_allowed"] is False
    assert any("RC-009" in blocker for blocker in checklist["release_blockers"])
    gates = {gate["gate_id"]: gate for gate in checklist["gates"]}
    assert gates["RC-008"]["status"] == "pass"
    assert gates["RC-009"]["status"] == "fail"
    assert checklist["fail_count"] >= 1

    loaded = client.get(f"/api/v1/behavior/release/checklists/{checklist['checklist_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["benchmark_report_id"] == checklist["benchmark_report_id"]

    history = client.get("/api/v1/behavior/release/checklists?symbol=INFY")
    assert history.status_code == 200
    assert checklist["checklist_id"] in {item["checklist_id"] for item in history.json()["data"]}


def test_mock_to_replay_approval_workflow_is_persisted_and_blocks_live():
    request = client.post(
        "/api/v1/behavior/release/approval/request",
        json={
            "symbol": "INFY",
            "requested_by": "research_operator",
            "reason": "Promote mock evidence to replay review after deterministic validation passed.",
        },
    )
    assert request.status_code == 200
    record = request.json()["data"]
    assert record["approval_version"] == "release-approval.v0.28"
    assert record["symbol"] == "INFY"
    assert record["target_mode"] == "REPLAY"
    assert record["approval_scope"] == "mock_to_replay"
    assert record["status"] == "requested"
    assert record["live_trading_blocked"] is True
    assert "live_trading_blocked=true" in record["evidence"]

    self_approval = client.post(
        f"/api/v1/behavior/release/approvals/{record['approval_id']}/approve",
        json={"actor_id": "research_operator", "reason": "Self approval must be rejected."},
    )
    assert self_approval.status_code == 409
    assert self_approval.json()["error"]["code"] == "release_approval_self_approval_blocked"

    approved = client.post(
        f"/api/v1/behavior/release/approvals/{record['approval_id']}/approve",
        json={"actor_id": "risk_manager", "reason": "Replay review only. Live trading remains disabled."},
    )
    assert approved.status_code == 200
    approved_record = approved.json()["data"]
    assert approved_record["status"] == "approved"
    assert approved_record["approved_by"] == "risk_manager"
    assert approved_record["live_trading_blocked"] is True
    assert any(item.startswith("approved_checklist_id=") for item in approved_record["evidence"])
    assert any(item == "live_trading_blocked=true" for item in approved_record["evidence"])

    loaded = client.get(f"/api/v1/behavior/release/approvals/{record['approval_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["status"] == "approved"

    history = client.get("/api/v1/behavior/release/approvals?symbol=INFY")
    assert history.status_code == 200
    assert record["approval_id"] in {item["approval_id"] for item in history.json()["data"]}


def test_mock_to_replay_approval_rejection_is_audited():
    request = client.post(
        "/api/v1/behavior/release/approval/request",
        json={
            "symbol": "TCS",
            "requested_by": "research_operator",
            "reason": "Create rejection fixture for release governance audit trail.",
        },
    )
    assert request.status_code == 200
    record = request.json()["data"]

    rejected = client.post(
        f"/api/v1/behavior/release/approvals/{record['approval_id']}/reject",
        json={"actor_id": "risk_manager", "reason": "Replay fixture evidence is not ready."},
    )
    assert rejected.status_code == 200
    rejected_record = rejected.json()["data"]
    assert rejected_record["status"] == "rejected"
    assert rejected_record["rejected_by"] == "risk_manager"
    assert rejected_record["rejection_reason"] == "Replay fixture evidence is not ready."
    assert rejected_record["live_trading_blocked"] is True


def test_benchmark_drilldown_exposes_validation_safety_and_replay_evidence():
    report = client.get("/api/v1/behavior/benchmark/report/current?symbol=SBIN")
    assert report.status_code == 200
    report_id = report.json()["data"]["report_id"]

    drilldown = client.get(f"/api/v1/behavior/benchmark/reports/{report_id}/drilldown")
    assert drilldown.status_code == 200
    data = drilldown.json()["data"]
    assert data["drilldown_version"] == "behavior-release-evidence.v0.29"
    assert data["report_id"] == report_id
    assert data["symbol"] == "SBIN"
    assert data["live_trading_blocked"] is True
    assert "walk_forward" in data["metric_groups"]
    assert "out_of_sample" in data["metric_groups"]
    assert "golden_replay" in data["metric_groups"]
    assert "safety" in data["metric_groups"]
    assert any("Walk-forward trades" in item for item in data["validation_summary"])
    assert any("Safety report" in item for item in data["safety_summary"])
    assert any("golden replay fixtures passed" in item for item in data["replay_summary"])
    assert "Live trading remains blocked." in data["promotion_summary"]


def test_behavior_scenario_coverage_drilldown_tracks_required_regimes():
    response = client.get("/api/v1/behavior/benchmark/scenario-coverage/current?symbol=NIFTY-MOCK")
    assert response.status_code == 200
    coverage = response.json()["data"]
    assert coverage["coverage_version"] == "behavior-scenario-coverage.v1.66"
    assert coverage["total_scenarios"] == 16
    assert coverage["passed_scenarios"] == 16
    assert coverage["failed_scenarios"] == 0
    assert coverage["coverage_score_pct"] == 100.0
    assert coverage["deterministic_pass_rate_pct"] == 100.0
    assert coverage["missing_scenario_families"] == []
    assert coverage["live_trading_blocked"] is True
    assert set(coverage["required_scenario_families"]) == {
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
    }
    assert {item["scenario_family"] for item in coverage["scenario_items"]} == set(coverage["required_scenario_families"])

    by_id = client.get(f"/api/v1/behavior/benchmark/scenario-coverage/reports/{coverage['coverage_id']}")
    assert by_id.status_code == 200
    assert by_id.json()["data"] == coverage

    by_symbol = client.get("/api/v1/behavior/benchmark/scenario-coverage/reports?symbol=NIFTY-MOCK")
    assert by_symbol.status_code == 200
    assert any(item["coverage_id"] == coverage["coverage_id"] for item in by_symbol.json()["data"])

    by_report = client.get(f"/api/v1/behavior/benchmark/reports/{coverage['benchmark_report_id']}/scenario-coverage")
    assert by_report.status_code == 200
    assert by_report.json()["data"]["coverage_id"] == coverage["coverage_id"]


def test_release_evidence_bundle_persists_hash_addressed_review_package():
    requested = client.post(
        "/api/v1/behavior/release/approval/request",
        json={
            "symbol": "SBIN",
            "requested_by": "research_operator",
            "reason": "Create v0.29 release evidence bundle for mock-to-replay review.",
        },
    )
    assert requested.status_code == 200
    approval_id = requested.json()["data"]["approval_id"]

    approved = client.post(
        f"/api/v1/behavior/release/approvals/{approval_id}/approve",
        json={"actor_id": "risk_manager", "reason": "Approve mock-to-replay evidence review only."},
    )
    assert approved.status_code == 200
    approval = approved.json()["data"]

    exported = client.post(f"/api/v1/behavior/release/evidence/export?symbol=SBIN&approval_id={approval_id}")
    assert exported.status_code == 200
    bundle = exported.json()["data"]
    assert bundle["bundle_version"] == "behavior-release-evidence.v0.29"
    assert bundle["symbol"] == "SBIN"
    assert bundle["target_mode"] == "REPLAY"
    assert bundle["approval"]["approval_id"] == approval_id
    assert bundle["approval"]["status"] == "approved"
    assert bundle["benchmark_report"]["report_id"] == approval["benchmark_report_id"]
    assert bundle["benchmark_drilldown"]["report_id"] == approval["benchmark_report_id"]
    assert bundle["checklist"]["benchmark_report_id"] == approval["benchmark_report_id"]
    assert bundle["immutable"] is True
    assert bundle["live_trading_blocked"] is True
    assert len(bundle["bundle_hash"]) == 64
    assert bundle["evidence_index"]["approval_id"] == approval_id
    assert bundle["evidence_index"]["target_mode"] == "REPLAY"
    assert "Live trading remains blocked for this evidence bundle." in bundle["final_blockers"]

    loaded = client.get(f"/api/v1/behavior/release/evidence/bundles/{bundle['bundle_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["bundle_hash"] == bundle["bundle_hash"]

    history = client.get("/api/v1/behavior/release/evidence/bundles?symbol=SBIN")
    assert history.status_code == 200
    assert bundle["bundle_id"] in {item["bundle_id"] for item in history.json()["data"]}


def test_release_evidence_artifact_export_writes_manifest_and_verifies_files():
    requested = client.post(
        "/api/v1/behavior/release/approval/request",
        json={
            "symbol": "RELIANCE",
            "requested_by": "research_operator",
            "reason": "Create v0.30 file artifact for controlled evidence export.",
        },
    )
    assert requested.status_code == 200
    approval_id = requested.json()["data"]["approval_id"]
    approved = client.post(
        f"/api/v1/behavior/release/approvals/{approval_id}/approve",
        json={"actor_id": "risk_manager", "reason": "Approve evidence export only; no live trading."},
    )
    assert approved.status_code == 200

    exported = client.post(
        "/api/v1/behavior/release/evidence/artifact/export",
        json={
            "symbol": "RELIANCE",
            "approval_id": approval_id,
            "requested_by": "research_operator",
            "reason": "Export checksum-controlled evidence artifact for mock-to-replay review.",
            "retention_days": 365,
        },
    )
    assert exported.status_code == 200
    artifact = exported.json()["data"]
    assert artifact["artifact_version"] == "release-evidence-artifact.v0.30"
    assert artifact["symbol"] == "RELIANCE"
    assert artifact["target_mode"] == "REPLAY"
    assert artifact["artifact_format"] == "json_manifest"
    assert artifact["immutable"] is True
    assert artifact["live_trading_blocked"] is True
    assert artifact["contains_broker_credentials"] is False
    assert artifact["contains_live_orders"] is False
    assert artifact["bundle_size_bytes"] > 0
    assert artifact["manifest_size_bytes"] > 0
    assert len(artifact["bundle_sha256"]) == 64
    assert len(artifact["manifest_sha256"]) == 64

    from pathlib import Path

    bundle_path = Path(artifact["bundle_file_path"])
    manifest_path = Path(artifact["manifest_file_path"])
    assert bundle_path.exists()
    assert manifest_path.exists()
    assert bundle_path.parent == manifest_path.parent

    verify = client.get(f"/api/v1/behavior/release/evidence/artifacts/{artifact['artifact_id']}/verify")
    assert verify.status_code == 200
    verification = verify.json()["data"]
    assert verification["verification_version"] == "release-evidence-artifact-verification.v0.30"
    assert verification["verified"] is True
    assert verification["issues"] == []
    assert verification["bundle_file_exists"] is True
    assert verification["manifest_file_exists"] is True
    assert verification["bundle_sha256_matches"] is True
    assert verification["manifest_sha256_matches"] is True
    assert verification["bundle_json_parseable"] is True
    assert verification["live_trading_blocked"] is True

    loaded = client.get(f"/api/v1/behavior/release/evidence/artifacts/{artifact['artifact_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["manifest_sha256"] == artifact["manifest_sha256"]

    history = client.get("/api/v1/behavior/release/evidence/artifacts?symbol=RELIANCE")
    assert history.status_code == 200
    assert artifact["artifact_id"] in {item["artifact_id"] for item in history.json()["data"]}


def test_behavior_analyze_returns_exact_74_column_shape_and_no_live_route():
    response = client.post("/api/v1/behavior/analyze", json={"symbol": "INFY", "timeframe": "5m", "seed": 17})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["symbol"] == "INFY"
    assert data["timeframe"] == "5m"
    assert data["run_id"] == "behavior-INFY-5m-17"
    assert len(data["columns"]) == 74
    assert set(data["result"].keys()) == set(data["columns"])
    assert data["result"]["trade_allowed"] is False
    assert data["result"]["minimum_sample_pass"] is False
    assert data["live_trade_route_attempted"] is False
    assert "Low evidence. Similar history is not enough." in data["result"]["no_trade_reason"]
    assert data["result"]["backtest_id"] == data["run_id"]

    replay = client.get(f"/api/v1/behavior/replay/{data['run_id']}")
    assert replay.status_code == 200
    replay_data = replay.json()["data"]
    assert replay_data["run_id"] == data["run_id"]
    assert replay_data["symbol"] == "INFY"
    assert replay_data["deterministic"] is True
    assert len(replay_data["events"]) == 8


def test_behavior_stock_dna_memory_similar_days_and_benchmark_skeleton():
    dna = client.get("/api/v1/behavior/stock/INFY/dna")
    assert dna.status_code == 200
    dna_data = dna.json()["data"]
    assert dna_data["symbol"] == "INFY"
    assert dna_data["profile_version"] == "stock-dna.mock.v0.12"
    assert "VWAP" in dna_data["level_respect_summary"]

    memory = client.get("/api/v1/behavior/stock/INFY/memory")
    assert memory.status_code == 200
    memory_data = memory.json()["data"]
    assert len(memory_data) >= 3
    assert {record["outcome_label"] for record in memory_data} >= {
        "FAKE_BREAKOUT",
        "TARGET_HIT",
        "CHOP_NO_FOLLOWTHROUGH",
    }

    similar = client.get("/api/v1/behavior/similar-days/INFY")
    assert similar.status_code == 200
    similar_data = similar.json()["data"]
    assert len(similar_data) >= 3
    assert similar_data[0]["similarity_score_pct"] >= similar_data[-1]["similarity_score_pct"]

    benchmark = client.post("/api/v1/behavior/benchmark/run", json={"symbol": "INFY", "timeframe": "5m", "seed": 17})
    assert benchmark.status_code == 200
    benchmark_data = benchmark.json()["data"]
    assert benchmark_data["run_id"] == "benchmark-INFY-5m-17"
    assert benchmark_data["status"] == "completed"
    assert benchmark_data["metrics"]["trade_count"] == 0

    loaded = client.get(f"/api/v1/behavior/benchmark/{benchmark_data['run_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"] == benchmark_data

    status = client.get(f"/api/v1/behavior/benchmark/{benchmark_data['run_id']}/status")
    assert status.status_code == 200
    assert status.json()["data"]["status"] == "completed"


def test_behavior_data_adapter_creates_candle_series_without_legacy_runtime_dependency():
    manifest = client.get("/api/v1/behavior/data/adapter-manifest")
    assert manifest.status_code == 200
    manifest_data = manifest.json()["data"]
    assert manifest_data["runtime_dependency_on_legacy_stock_app"] is False
    assert manifest_data["output_contract"] == "CandleSeries"

    adapted = client.post(
        "/api/v1/behavior/data/adapt",
        json={"symbol": "INFY", "timeframe": "1m", "seed": 321, "bars": 8},
    )
    assert adapted.status_code == 200
    data = adapted.json()["data"]
    assert data["runtime_dependency_on_legacy_stock_app"] is False
    assert data["series"]["symbol"] == "INFY"
    assert data["series"]["timeframe"] == "1m"
    assert len(data["series"]["bars"]) == 8
    assert data["series"]["bars"][0]["sequence_number"] == 1
    assert data["series"]["bars"][0]["timestamp_ns"] < data["series"]["bars"][-1]["timestamp_ns"]


def test_behavior_data_quality_blocks_bad_ohlc_and_duplicate_timestamps():
    base = 1_714_724_800_000_000_000
    payload = {
        "symbol": "BAD-DATA",
        "timeframe": "1m",
        "snapshot_id": "manual-bad",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "BAD-DATA",
                "timeframe": "1m",
                "timestamp_ns": base,
                "open": 100.0,
                "high": 99.0,
                "low": 98.0,
                "close": 100.5,
                "volume": None,
                "source": "mock",
                "sequence_number": 1,
            },
            {
                "symbol": "BAD-DATA",
                "timeframe": "1m",
                "timestamp_ns": base,
                "open": 100.5,
                "high": 101.0,
                "low": 100.0,
                "close": 100.8,
                "volume": 1200.0,
                "source": "mock",
                "sequence_number": 2,
            },
        ],
    }
    response = client.post("/api/v1/behavior/data/quality", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["blocks_trade"] is True
    assert result["invalid_ohlc_count"] == 1
    assert result["duplicate_timestamp_count"] == 1
    assert result["missing_volume_count"] == 1
    assert result["volume_matching_enabled"] is False
    assert {issue["code"] for issue in result["issues"]} >= {"invalid_ohlc", "duplicate_timestamp", "missing_volume"}


def test_behavior_data_quality_allows_clean_seeded_snapshot():
    adapted = client.post(
        "/api/v1/behavior/data/adapt",
        json={"symbol": "CLEAN-DATA", "timeframe": "1m", "seed": 88, "bars": 16},
    ).json()["data"]
    response = client.post("/api/v1/behavior/data/quality", json=adapted["series"])
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["blocks_trade"] is False
    assert result["data_quality_score"] == 1.0
    assert result["valid_bars"] == 16
    assert result["issues"] == []


def test_point_in_time_guard_blocks_future_and_incomplete_candles():
    adapted = client.post(
        "/api/v1/behavior/data/adapt",
        json={"symbol": "PIT-BLOCK", "timeframe": "1m", "seed": 44, "bars": 3},
    ).json()["data"]
    first_timestamp = adapted["series"]["bars"][0]["timestamp_ns"]
    response = client.post(
        "/api/v1/behavior/guards/point-in-time",
        json={
            "series": adapted["series"],
            "decision_time_ns": first_timestamp + 30_000_000_000,
            "execution_time_ns": first_timestamp + 60_000_000_000,
            "source_timeframe": "1m",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is False
    assert result["blocks_trade"] is True
    assert result["future_bar_blocked"] >= 1
    assert result["incomplete_candle_blocked"] >= 1


def test_point_in_time_guard_allows_only_closed_candles():
    adapted = client.post(
        "/api/v1/behavior/data/adapt",
        json={"symbol": "PIT-PASS", "timeframe": "1m", "seed": 45, "bars": 3},
    ).json()["data"]
    last_timestamp = adapted["series"]["bars"][-1]["timestamp_ns"]
    response = client.post(
        "/api/v1/behavior/guards/point-in-time",
        json={
            "series": adapted["series"],
            "decision_time_ns": last_timestamp + 60_000_000_000,
            "source_timeframe": "1m",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is True
    assert result["blocks_trade"] is False
    assert result["allowed_bars"] == 3
    assert result["blocked_bars"] == 0


def test_point_in_time_guard_blocks_incomplete_one_hour_candle():
    base = 1_714_724_800_000_000_000
    series = {
        "symbol": "HTF-BLOCK",
        "timeframe": "1H",
        "snapshot_id": "manual-htf",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "HTF-BLOCK",
                "timeframe": "1H",
                "timestamp_ns": base,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 2000.0,
                "source": "mock",
                "sequence_number": 1,
            }
        ],
    }
    response = client.post(
        "/api/v1/behavior/guards/point-in-time",
        json={
            "series": series,
            "decision_time_ns": base + 30 * 60_000_000_000,
            "source_timeframe": "1H",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is False
    assert result["future_bar_blocked"] == 0
    assert result["incomplete_candle_blocked"] == 1
    assert result["allowed_bars"] == 0


def test_timeframe_sync_uses_previous_closed_hour_and_ignores_incomplete_current_hour():
    base = 1_714_724_800_000_000_000
    one_minute = 60_000_000_000
    one_hour = 60 * one_minute
    series_1m = {
        "symbol": "SYNC-PASS",
        "timeframe": "1m",
        "snapshot_id": "sync-1m",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "SYNC-PASS",
                "timeframe": "1m",
                "timestamp_ns": base + idx * one_minute,
                "open": 100.0 + idx,
                "high": 101.0 + idx,
                "low": 99.0 + idx,
                "close": 100.5 + idx,
                "volume": 1000.0,
                "source": "mock",
                "sequence_number": idx + 1,
            }
            for idx in range(5)
        ],
    }
    series_1h = {
        "symbol": "SYNC-PASS",
        "timeframe": "1H",
        "snapshot_id": "sync-1h",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "SYNC-PASS",
                "timeframe": "1H",
                "timestamp_ns": base - one_hour,
                "open": 100.0,
                "high": 102.0,
                "low": 98.0,
                "close": 101.0,
                "volume": 5000.0,
                "source": "mock",
                "sequence_number": 1,
            },
            {
                "symbol": "SYNC-PASS",
                "timeframe": "1H",
                "timestamp_ns": base,
                "open": 101.0,
                "high": 103.0,
                "low": 100.0,
                "close": 102.0,
                "volume": 4500.0,
                "source": "mock",
                "sequence_number": 2,
            },
        ],
    }
    response = client.post(
        "/api/v1/behavior/timeframes/synchronize",
        json={
            "symbol": "SYNC-PASS",
            "decision_time_ns": base + 5 * one_minute,
            "execution_time_ns": base + 6 * one_minute,
            "series": [series_1m, series_1h],
            "required_timeframes": ["1m", "1H"],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is True
    assert result["blocks_trade"] is False
    by_tf = {record["timeframe"]: record for record in result["records"]}
    assert by_tf["1m"]["usable_bars"] == 5
    assert by_tf["1H"]["usable_bars"] == 1
    assert by_tf["1H"]["blocked_incomplete_bars"] == 1
    assert by_tf["1H"]["latest_closed_timestamp_ns"] == base - one_hour


def test_timeframe_sync_blocks_missing_or_unusable_required_timeframe():
    base = 1_714_724_800_000_000_000
    series_1h = {
        "symbol": "SYNC-BLOCK",
        "timeframe": "1H",
        "snapshot_id": "sync-block-1h",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "SYNC-BLOCK",
                "timeframe": "1H",
                "timestamp_ns": base,
                "open": 100.0,
                "high": 102.0,
                "low": 98.0,
                "close": 101.0,
                "volume": 5000.0,
                "source": "mock",
                "sequence_number": 1,
            }
        ],
    }
    response = client.post(
        "/api/v1/behavior/timeframes/synchronize",
        json={
            "symbol": "SYNC-BLOCK",
            "decision_time_ns": base + 30 * 60_000_000_000,
            "series": [series_1h],
            "required_timeframes": ["1m", "1H"],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is False
    assert result["blocks_trade"] is True
    assert "1m" in result["usable_cutoff_by_timeframe"]
    by_tf = {record["timeframe"]: record for record in result["records"]}
    assert by_tf["1H"]["usable_bars"] == 0
    assert by_tf["1H"]["blocked_incomplete_bars"] == 1


def test_causal_feature_whitelist_allows_closed_safe_features():
    base = 1_714_724_800_000_000_000
    one_minute = 60_000_000_000
    series = {
        "symbol": "FEATURE-PASS",
        "timeframe": "5m",
        "snapshot_id": "feature-pass-5m",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "FEATURE-PASS",
                "timeframe": "5m",
                "timestamp_ns": base,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000.0,
                "source": "mock",
                "sequence_number": 1,
            }
        ],
    }
    sync = client.post(
        "/api/v1/behavior/timeframes/synchronize",
        json={
            "symbol": "FEATURE-PASS",
            "decision_time_ns": base + 5 * one_minute,
            "series": [series],
            "required_timeframes": ["5m"],
        },
    ).json()["data"]
    response = client.post(
        "/api/v1/behavior/features/validate",
        json={
            "decision_time_ns": base + 5 * one_minute,
            "features": [
                {
                    "name": "rsi",
                    "source_timeframe": "5m",
                    "required_fields": ["open", "high", "low", "close"],
                    "available_after_ns": base + 5 * one_minute,
                    "depends_on_full_candle": True,
                    "uses_future_data": False,
                    "description": "Closed-candle RSI.",
                }
            ],
            "timeframe_sync": sync,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is True
    assert result["blocked_features"] == []
    assert result["allowed_features"] == ["rsi"]


def test_causal_feature_whitelist_blocks_future_and_full_day_dependencies():
    base = 1_714_724_800_000_000_000
    response = client.post(
        "/api/v1/behavior/features/validate",
        json={
            "decision_time_ns": base,
            "features": [
                {
                    "name": "future_breakout_oracle",
                    "source_timeframe": "5m",
                    "required_fields": ["future_high", "future_close"],
                    "available_after_ns": base,
                    "depends_on_full_candle": True,
                    "uses_future_data": True,
                    "description": "Unsafe oracle feature.",
                },
                {
                    "name": "current_full_day_high",
                    "source_timeframe": "daily",
                    "required_fields": ["full_day_high"],
                    "available_after_ns": base + 1,
                    "depends_on_full_candle": True,
                    "uses_future_data": False,
                    "description": "Unsafe full-day value before close.",
                },
            ],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is False
    assert result["blocks_trade"] is True
    assert set(result["blocked_features"]) == {"future_breakout_oracle", "current_full_day_high"}
    assert any("forbidden fields" in issue for issue in result["issues"])
    assert any("uses_future_data=true" in issue for issue in result["issues"])


def test_causal_feature_whitelist_blocks_incomplete_required_timeframe():
    base = 1_714_724_800_000_000_000
    series = {
        "symbol": "FEATURE-BLOCK",
        "timeframe": "1H",
        "snapshot_id": "feature-block-1h",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "FEATURE-BLOCK",
                "timeframe": "1H",
                "timestamp_ns": base,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000.0,
                "source": "mock",
                "sequence_number": 1,
            }
        ],
    }
    sync = client.post(
        "/api/v1/behavior/timeframes/synchronize",
        json={
            "symbol": "FEATURE-BLOCK",
            "decision_time_ns": base + 30 * 60_000_000_000,
            "series": [series],
            "required_timeframes": ["1H"],
        },
    ).json()["data"]
    response = client.post(
        "/api/v1/behavior/features/validate",
        json={
            "decision_time_ns": base + 30 * 60_000_000_000,
            "features": [
                {
                    "name": "hourly_trend_close",
                    "source_timeframe": "1H",
                    "required_fields": ["close"],
                    "depends_on_full_candle": True,
                    "uses_future_data": False,
                    "description": "Unsafe until the 1H candle closes.",
                }
            ],
            "timeframe_sync": sync,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is False
    assert result["blocked_features"] == ["hourly_trend_close"]
    assert any("no closed candle" in issue for issue in result["issues"])


def test_candle_anatomy_computes_core_candle_math():
    base = 1_714_724_800_000_000_000
    series = {
        "symbol": "ANATOMY",
        "timeframe": "5m",
        "snapshot_id": "anatomy-manual",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "ANATOMY",
                "timeframe": "5m",
                "timestamp_ns": base,
                "open": 100.0,
                "high": 110.0,
                "low": 95.0,
                "close": 108.0,
                "volume": 1000.0,
                "source": "mock",
                "sequence_number": 1,
            }
        ],
    }
    response = client.post("/api/v1/behavior/candles/anatomy", json={"series": series})
    assert response.status_code == 200
    result = response.json()["data"]
    latest = result["latest"]
    assert result["calculation_version"] == "candle-anatomy.v0.15"
    assert latest["direction"] == "bullish"
    assert latest["body_pct"] == 53.3333
    assert latest["upper_wick_pct"] == 13.3333
    assert latest["lower_wick_pct"] == 33.3333
    assert latest["close_location_value"] == 0.8667
    assert "neutral_candle" in latest["candle_structure_types"] or "trend_candle" in latest["candle_structure_types"]


def test_candle_anatomy_detects_absorption_looking_candle():
    base = 1_714_724_800_000_000_000
    one = 300_000_000_000
    bars = []
    for idx, volume in enumerate([1000.0, 1000.0, 1000.0, 10000.0]):
        bars.append(
            {
                "symbol": "ABSORB",
                "timeframe": "5m",
                "timestamp_ns": base + idx * one,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.2 if idx == 3 else 100.8,
                "volume": volume,
                "source": "mock",
                "sequence_number": idx + 1,
            }
        )
    response = client.post(
        "/api/v1/behavior/candles/anatomy",
        json={"series": {"symbol": "ABSORB", "timeframe": "5m", "bars": bars, "snapshot_id": "absorb", "schema_version": "candles.v1"}},
    )
    assert response.status_code == 200
    latest = response.json()["data"]["latest"]
    assert latest["volume_z"] > 1.0
    assert latest["body_pct"] <= 30
    assert "absorption_looking_candle" in latest["candle_structure_types"]


def _v170_chart_series(symbol: str, ranges: list[float], volumes: list[float] | None = None, trend_step: float = 0.05) -> dict:
    base = 1_714_724_800_000_000_000
    one = 300_000_000_000
    bars = []
    price = 100.0
    for idx, candle_range in enumerate(ranges):
        volume = volumes[idx] if volumes else 1000.0 + idx
        open_price = price
        close = price + trend_step
        high = max(open_price, close) + candle_range * 0.35
        low = min(open_price, close) - candle_range * 0.65
        bars.append(
            {
                "symbol": symbol,
                "timeframe": "5m",
                "timestamp_ns": base + idx * one,
                "open": round(open_price, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": float(volume),
                "source": "mock",
                "sequence_number": idx + 1,
            }
        )
        price = close
    return {"symbol": symbol, "timeframe": "5m", "bars": bars, "snapshot_id": f"{symbol}-v170", "schema_version": "candles.v1"}


def test_v170_chart_reasoning_current_endpoint_is_evidence_only_and_closed_candle():
    response = client.get("/api/v1/behavior/chart/reasoning/current?symbol=MOCKV170&timeframe=5m&rows=140")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["reasoning_version"] == "behavior-chart-reasoning-volatility.v1.70"
    assert result["closed_candle_only"] is True
    assert result["no_future_leakage"] is True
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert {"MAX-008", "VOL-001", "VOL-002", "VCP-001", "FRA-001"}.issubset({gate["gate_id"] for gate in result["gates"]})


def test_v170_chart_reasoning_detects_compression_and_vcp():
    ranges = [3.0] * 24 + [2.8, 2.3, 1.9, 1.55, 1.25, 1.0, 0.8, 0.62, 0.5, 0.42, 0.35, 0.3]
    volumes = [3000.0] * 24 + [2600, 2300, 2000, 1700, 1450, 1200, 1000, 850, 720, 600, 500, 420]
    response = client.post(
        "/api/v1/behavior/chart/reasoning/analyze",
        json={"series": _v170_chart_series("VCP", ranges, volumes, trend_step=0.02), "vcp_window": 12},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["vcp_state"] == "vcp_contraction_with_volume_dryup"
    assert result["contraction_count"] >= 3
    assert result["volume_dryup_score"] >= 0.25
    assert result["bb_width_percentile"] <= 100.0
    assert result["used_for_probability"] is False


def test_v170_chart_reasoning_flags_high_rejection_and_chop_context():
    series = _v170_chart_series("REJECT", [1.0] * 39, [1000.0] * 39, trend_step=0.0)
    last = {
        "symbol": "REJECT",
        "timeframe": "5m",
        "timestamp_ns": 1_714_724_800_000_000_000 + 39 * 300_000_000_000,
        "open": 100.0,
        "high": 103.0,
        "low": 99.9,
        "close": 100.1,
        "volume": 1800.0,
        "source": "mock",
        "sequence_number": 40,
    }
    series["bars"].append(last)
    response = client.post("/api/v1/behavior/chart/reasoning/analyze", json={"series": series})
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["rejection_index"] >= 2.0
    assert result["momentum_cleanliness"] == "rejection_polluted"
    assert result["chop_risk"] in {"high", "compression_watch", "low"}
    assert any("rejection" in reason.lower() for reason in result["reasons"])


def test_v170_chart_reasoning_uses_prior_closed_atr_baseline_for_percentile():
    series = _v170_chart_series("ATRBASE", [1.0] * 30 + [10.0], [1000.0] * 31, trend_step=0.03)
    response = client.post(
        "/api/v1/behavior/chart/reasoning/analyze",
        json={"series": series, "atr_period": 3, "minimum_bars": 9},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["atr_percentile"] == 100.0
    assert result["volatility_regime"] in {"expanding_volatility", "extreme_volatility_ood"}
    vol_gate = next(gate for gate in result["gates"] if gate["gate_id"] == "VOL-001")
    assert vol_gate["passed"] is True


def test_condition_classifier_detects_breakout_day_without_blocking():
    base = 1_714_724_800_000_000_000
    one = 300_000_000_000
    bars = [
        {
            "symbol": "BREAKOUT",
            "timeframe": "5m",
            "timestamp_ns": base + idx * one,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": 2000.0 + idx * 500,
            "source": "mock",
            "sequence_number": idx + 1,
        }
        for idx, (open_price, high, low, close) in enumerate(
            [
                (100.0, 102.0, 99.0, 101.5),
                (101.5, 104.0, 101.0, 103.5),
                (103.5, 107.0, 103.0, 106.5),
            ]
        )
    ]
    series = {"symbol": "BREAKOUT", "timeframe": "5m", "bars": bars, "snapshot_id": "breakout", "schema_version": "candles.v1"}
    response = client.post(
        "/api/v1/behavior/conditions/classify",
        json={"series": series, "resistance_level": 105.0, "session_phase": "09:30-10:15 real trend confirmation"},
    )
    assert response.status_code == 200
    latest = response.json()["data"]["latest"]
    assert "breakout_day" in latest["condition_tags"]
    assert response.json()["data"]["final_signal_bias"] == "long"
    assert response.json()["data"]["blocks_trade"] is False


def test_condition_classifier_blocks_fake_breakout():
    base = 1_714_724_800_000_000_000
    one = 300_000_000_000
    bars = [
        {
            "symbol": "FAKEOUT",
            "timeframe": "5m",
            "timestamp_ns": base,
            "open": 104.0,
            "high": 107.0,
            "low": 103.0,
            "close": 106.0,
            "volume": 2500.0,
            "source": "mock",
            "sequence_number": 1,
        },
        {
            "symbol": "FAKEOUT",
            "timeframe": "5m",
            "timestamp_ns": base + one,
            "open": 106.0,
            "high": 108.0,
            "low": 103.0,
            "close": 104.5,
            "volume": 5000.0,
            "source": "mock",
            "sequence_number": 2,
        },
    ]
    series = {"symbol": "FAKEOUT", "timeframe": "5m", "bars": bars, "snapshot_id": "fakeout", "schema_version": "candles.v1"}
    response = client.post(
        "/api/v1/behavior/conditions/classify",
        json={"series": series, "resistance_level": 105.0, "session_phase": "09:30-10:15 real trend confirmation"},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["market_state"] == "fake_breakout"
    assert result["blocks_trade"] is True
    assert "fakeout risk" in result["no_trade_reason"].lower()


def test_condition_classifier_detects_range_balance_and_chop():
    base = 1_714_724_800_000_000_000
    one = 300_000_000_000
    bars = [
        {
            "symbol": "RANGE",
            "timeframe": "5m",
            "timestamp_ns": base + idx * one,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.1 if idx % 2 == 0 else 99.9,
            "volume": 1500.0,
            "source": "mock",
            "sequence_number": idx + 1,
        }
        for idx in range(5)
    ]
    series = {"symbol": "RANGE", "timeframe": "5m", "bars": bars, "snapshot_id": "range", "schema_version": "candles.v1"}
    response = client.post("/api/v1/behavior/conditions/classify", json={"series": series, "session_phase": "11:30-13:30 lunch"})
    assert response.status_code == 200
    result = response.json()["data"]
    assert "range_balance_day" in result["condition_tags"]
    assert result["blocks_trade"] is True
    assert result["final_signal_bias"] == "avoid"


def test_behavior_level_context_detects_vwap_orb_cpr_and_pdh_rejection():
    base = 1_714_724_800_000_000_000
    one = 300_000_000_000
    bars = [
        {
            "symbol": "LEVELS",
            "timeframe": "5m",
            "timestamp_ns": base + idx * one,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "source": "mock",
            "sequence_number": idx + 1,
        }
        for idx, (open_price, high, low, close, volume) in enumerate(
            [
                (100.0, 101.0, 99.0, 100.6, 1000.0),
                (100.6, 102.0, 100.1, 101.4, 1200.0),
                (101.4, 103.0, 101.0, 102.4, 1300.0),
                (102.4, 106.0, 102.1, 104.7, 2200.0),
                (104.7, 105.8, 103.8, 104.4, 2600.0),
            ]
        )
    ]
    series = {"symbol": "LEVELS", "timeframe": "5m", "bars": bars, "snapshot_id": "levels", "schema_version": "candles.v1"}
    response = client.post(
        "/api/v1/behavior/context/levels",
        json={
            "series": series,
            "previous_day_high": 105.0,
            "previous_day_low": 97.0,
            "previous_close": 100.0,
            "opening_range_high": 103.0,
            "opening_range_low": 99.0,
            "volume_profile_hvn": 102.5,
            "volume_profile_lvn": 104.4,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["context_version"] == "behavior-context.v0.16"
    assert result["calculated_vwap"] is not None
    assert result["pdh_state"] == "rejecting"
    assert result["cpr_pivot"] == 100.6667
    assert "rejecting_pdh" in result["support_resistance_flags"]
    assert result["blocks_trade"] is True


def test_behavior_htf_confirmation_blocks_long_against_bearish_closed_hour():
    base = 1_714_724_800_000_000_000
    one_hour = 3_600_000_000_000
    series_1h = {
        "symbol": "HTF-CONTEXT",
        "timeframe": "1H",
        "snapshot_id": "htf-context",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "HTF-CONTEXT",
                "timeframe": "1H",
                "timestamp_ns": base - 2 * one_hour,
                "open": 110.0,
                "high": 111.0,
                "low": 107.0,
                "close": 108.0,
                "volume": 5000.0,
                "source": "mock",
                "sequence_number": 1,
            },
            {
                "symbol": "HTF-CONTEXT",
                "timeframe": "1H",
                "timestamp_ns": base - one_hour,
                "open": 108.0,
                "high": 109.0,
                "low": 100.0,
                "close": 101.0,
                "volume": 7000.0,
                "source": "mock",
                "sequence_number": 2,
            },
            {
                "symbol": "HTF-CONTEXT",
                "timeframe": "1H",
                "timestamp_ns": base,
                "open": 101.0,
                "high": 103.0,
                "low": 100.0,
                "close": 102.0,
                "volume": 1000.0,
                "source": "mock",
                "sequence_number": 3,
            },
        ],
    }
    response = client.post(
        "/api/v1/behavior/context/htf",
        json={
            "symbol": "HTF-CONTEXT",
            "decision_time_ns": base,
            "direction": "long",
            "higher_timeframe_series": [series_1h],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["records"][0]["usable_bars"] == 2
    assert result["records"][0]["bias"] == "bearish"
    assert result["confirmed"] is False
    assert result["blocks_trade"] is True


def test_behavior_gap_context_blocks_large_gap_trap():
    base = 1_714_724_800_000_000_000
    one = 300_000_000_000
    bars = [
        {
            "symbol": "GAP",
            "timeframe": "5m",
            "timestamp_ns": base + idx * one,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": 2000.0,
            "source": "mock",
            "sequence_number": idx + 1,
        }
        for idx, (open_price, high, low, close) in enumerate(
            [
                (102.0, 103.0, 101.5, 102.5),
                (102.5, 103.2, 99.2, 99.7),
            ]
        )
    ]
    series = {"symbol": "GAP", "timeframe": "5m", "bars": bars, "snapshot_id": "gap", "schema_version": "candles.v1"}
    response = client.post("/api/v1/behavior/context/gap", json={"series": series, "previous_close": 100.0})
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["gap_type"] == "large_gap_up"
    assert result["gap_trap_risk"] >= 0.68
    assert result["blocks_trade"] is True


def test_behavior_market_context_blocks_long_when_index_and_sector_are_weak():
    response = client.post(
        "/api/v1/behavior/context/market",
        json={
            "symbol": "RS-WEAK",
            "direction": "long",
            "stock_return_pct": -0.2,
            "index_return_pct": -0.8,
            "sector_return_pct": -0.7,
            "global_risk_score": 0.3,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["index_direction"] == "down"
    assert result["sector_strength"] == "weak"
    assert result["market_alignment"] == "avoid"
    assert result["blocks_trade"] is True


def test_v171_reg_001_sector_weakness_reduces_confidence():
    response = client.post(
        "/api/v1/behavior/market-regime/feedback",
        json={
            "symbol": "REGWEAK",
            "direction": "long",
            "stock_return_pct": 0.95,
            "index_return_pct": 0.20,
            "banknifty_return_pct": 0.12,
            "sector_return_pct": -0.85,
            "advance_decline_ratio": 1.15,
            "sector_advance_decline_ratio": 0.82,
            "setup_sample_count": 44,
            "setup_success_count": 24,
            "setup_failure_count": 20,
            "vwap_respect_count": 16,
            "vwap_sample_count": 44,
            "breakout_failure_count": 18,
            "recent_signal_outcomes": ["WIN", "LOSS", "WIN", "LOSS"],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["feedback_version"] == "market-regime-breadth-rs-bayesian.v1.71"
    assert result["market_context_status"] == "available"
    assert result["trend_state"] == "sector_weakness_against_index"
    assert "require_sector_confirmation" in result["dynamic_confirmation_requirement"]
    assert result["trade_allowed"] is False
    assert result["live_trading_blocked"] is True


def test_v171_reg_002_leading_weak_index_increases_rs_but_stays_research_only():
    response = client.post(
        "/api/v1/behavior/market-regime/feedback",
        json={
            "symbol": "LEADER",
            "direction": "long",
            "stock_return_pct": 1.75,
            "index_return_pct": -0.35,
            "banknifty_return_pct": -0.20,
            "sector_return_pct": -0.10,
            "advance_decline_ratio": 1.10,
            "sector_advance_decline_ratio": 1.05,
            "stock_returns_pct": [-0.1, 0.2, 0.45, 0.75, 1.1, 1.75],
            "index_returns_pct": [0.0, -0.05, -0.08, -0.10, -0.20, -0.35],
            "setup_sample_count": 120,
            "setup_success_count": 74,
            "setup_failure_count": 46,
            "vwap_respect_count": 85,
            "vwap_sample_count": 120,
            "breakout_failure_count": 15,
            "recent_signal_outcomes": ["WIN", "WIN", "LOSS", "WIN"],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["relative_strength_score"] >= 0.65
    assert result["leading_lagging_state"] == "leading_weak_market"
    assert result["confidence_cap"] == "PAPER_CANDIDATE_ALLOWED"
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False


def test_v171_reg_003_missing_index_sector_breadth_caps_watch():
    response = client.post(
        "/api/v1/behavior/market-regime/feedback",
        json={
            "symbol": "MISSINGCTX",
            "direction": "long",
            "stock_return_pct": 1.1,
            "setup_sample_count": 160,
            "setup_success_count": 100,
            "setup_failure_count": 60,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["market_context_status"] == "unavailable"
    assert result["confidence_cap"] == "WATCH"
    assert result["unavailable_reasons"]
    gate = next(item for item in result["gates"] if item["gate_id"] == "REG-003")
    assert gate["passed"] is False


def test_v171_bayes_001_low_sample_uses_prior_shrinkage():
    response = client.post(
        "/api/v1/behavior/market-regime/feedback",
        json={
            "symbol": "LOWSAMPLE",
            "direction": "long",
            "stock_return_pct": 0.5,
            "index_return_pct": 0.2,
            "sector_return_pct": 0.2,
            "advance_decline_ratio": 1.4,
            "setup_sample_count": 6,
            "setup_success_count": 5,
            "setup_failure_count": 1,
            "prior_confidence": 0.5,
            "prior_sample_weight": 20,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["minimum_sample_pass"] is False
    assert 0.55 <= result["posterior_confidence"] <= 0.60
    assert result["confidence_cap"] == "WATCH"


def test_v171_bayes_002_three_failed_signals_activate_cooldown():
    response = client.post(
        "/api/v1/behavior/market-regime/feedback",
        json={
            "symbol": "COOLDOWN",
            "direction": "long",
            "stock_return_pct": 0.2,
            "index_return_pct": 0.2,
            "sector_return_pct": 0.2,
            "advance_decline_ratio": 1.2,
            "setup_sample_count": 90,
            "setup_success_count": 48,
            "setup_failure_count": 42,
            "recent_signal_outcomes": ["WIN", "LOSS", "LOSS", "LOSS"],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["cooldown_active"] is True
    assert result["confidence_cap"] == "WAIT"
    assert "cooldown_active_require_manual_review" in result["dynamic_confirmation_requirement"]
    gate = next(item for item in result["gates"] if item["gate_id"] == "BAYES-002")
    assert gate["passed"] is False


def _v172_bar(seq: int, open_price: float, high: float, low: float, close: float, volume: float) -> dict:
    return {
        "symbol": "TV172",
        "timeframe": "1m",
        "timestamp_ns": ns_ist(2026, 6, 30, 9, 15) + (seq - 1) * 60_000_000_000,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "source": "mock",
        "sequence_number": seq,
    }


def _v172_series(bars: list[dict]) -> dict:
    return {"symbol": "TV172", "timeframe": "1m", "bars": bars, "snapshot_id": "tv172-fixture", "schema_version": "candles.test.v172"}


def _v172_balanced_profile_bars() -> list[dict]:
    bars: list[dict] = []
    for seq in range(1, 41):
        center = 100.0 + ((seq % 7) - 3) * 0.10
        volume = 900.0 + (500.0 if abs(center - 100.0) <= 0.11 else 0.0)
        bars.append(_v172_bar(seq, center - 0.10, center + 0.35, center - 0.35, center + 0.08, volume))
    return bars


def test_v172_auc_001_poc_value_area_and_tpo_are_calculated_from_closed_bars():
    response = client.post(
        "/api/v1/behavior/market-structure/liquidity/analyze",
        json={"series": _v172_series(_v172_balanced_profile_bars()), "bin_count": 16, "minimum_bars": 30},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["structure_version"] == "market-structure-liquidity.v1.72"
    assert data["poc"] is not None
    assert 99.6 <= data["poc"] <= 100.4
    assert data["vah"] >= data["val"]
    assert data["tpo_poc"] is not None
    assert data["tpo_single_print_count"] >= 0
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "AUC-001")["passed"] is True
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "AUC-002")["passed"] is True
    assert data["closed_candle_only"] is True
    assert data["no_future_leakage"] is True
    assert data["trade_allowed"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True


def test_v172_vsa_001_high_volume_narrow_spread_flags_absorption_and_caps_watch():
    bars = _v172_balanced_profile_bars()
    bars[-1] = _v172_bar(40, 100.00, 100.08, 99.98, 100.03, 9_000.0)
    response = client.post(
        "/api/v1/behavior/market-structure/liquidity/analyze",
        json={"series": _v172_series(bars), "bin_count": 16, "minimum_bars": 30},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["vsa_effort_result_state"] == "effort_without_result_absorption"
    assert data["vsa_downgrade_active"] is True
    assert data["confidence_cap"] in {"WAIT", "WATCH"}
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "VSA-004")["passed"] is False


def test_v172_vsa_002_no_demand_and_no_supply_are_detected_without_crashing():
    bars = _v172_balanced_profile_bars()
    bars[-3] = _v172_bar(38, 100.00, 100.50, 99.90, 100.25, 1_000.0)
    bars[-2] = _v172_bar(39, 100.25, 100.70, 100.05, 100.45, 800.0)
    bars[-1] = _v172_bar(40, 100.45, 100.90, 100.25, 100.65, 600.0)
    response = client.post(
        "/api/v1/behavior/market-structure/liquidity/analyze",
        json={"series": _v172_series(bars), "minimum_bars": 30},
    )
    assert response.status_code == 200
    assert response.json()["data"]["vsa_effort_result_state"] == "no_demand_up_candles"

    bars[-3] = _v172_bar(38, 100.65, 100.80, 100.10, 100.35, 1_000.0)
    bars[-2] = _v172_bar(39, 100.35, 100.45, 99.80, 100.05, 800.0)
    bars[-1] = _v172_bar(40, 100.05, 100.15, 99.50, 99.75, 600.0)
    response = client.post(
        "/api/v1/behavior/market-structure/liquidity/analyze",
        json={"series": _v172_series(bars), "minimum_bars": 30},
    )
    assert response.status_code == 200
    assert response.json()["data"]["vsa_effort_result_state"] == "no_supply_down_candles"


def test_v172_smc_002_sweep_above_equal_highs_marks_stop_hunt_and_utad():
    bars = _v172_balanced_profile_bars()
    for seq in range(24, 31):
        bars[seq - 1] = _v172_bar(seq, 104.3, 105.0, 103.8, 104.6, 1_200.0)
    bars[-1] = _v172_bar(40, 104.8, 106.0, 104.0, 104.6, 4_000.0)
    response = client.post(
        "/api/v1/behavior/market-structure/liquidity/analyze",
        json={"series": _v172_series(bars), "minimum_bars": 30},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["liquidity_pool_detected"] is True
    assert data["liquidity_pool_side"] in {"above_equal_highs", "both"}
    assert data["sweep_direction"] == "up_sweep"
    assert data["wyckoff_phase"] == "utad"
    assert data["stop_hunt_score"] > 0.5
    assert data["confidence_cap"] == "WAIT"


def test_v172_smc_003_order_block_and_fvg_are_point_in_time_zones():
    bars = _v172_balanced_profile_bars()
    bars[-5] = _v172_bar(36, 101.0, 101.2, 100.0, 100.3, 1_000.0)
    bars[-4] = _v172_bar(37, 100.4, 103.2, 100.3, 103.0, 3_200.0)
    bars[-3] = _v172_bar(38, 101.0, 101.2, 100.5, 100.8, 1_000.0)
    bars[-2] = _v172_bar(39, 101.5, 101.8, 101.4, 101.7, 1_200.0)
    bars[-1] = _v172_bar(40, 102.4, 102.8, 102.3, 102.6, 1_300.0)
    response = client.post(
        "/api/v1/behavior/market-structure/liquidity/analyze",
        json={"series": _v172_series(bars), "minimum_bars": 30},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["order_block_zone"]["zone_type"] == "order_block"
    assert data["order_block_zone"]["point_in_time_safe"] is True
    assert data["fvg_zone"]["zone_type"] == "fair_value_gap"
    assert data["fvg_zone"]["point_in_time_safe"] is True


def test_v172_current_endpoint_and_capability_manifest_are_present():
    response = client.get("/api/v1/behavior/market-structure/liquidity/current?symbol=TV172&timeframe=1m&rows=160")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["structure_version"] == "market-structure-liquidity.v1.72"
    assert data["used_for_probability"] is False
    assert data["trade_allowed"] is False

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Market Structure Liquidity Engine")
    assert feature["status"] == "mock"
    assert "MarketStructureLiquidityReport" in feature["required_data_contracts"]


def test_v173_exec_002_high_spread_blocks_paper_candidate():
    response = client.post(
        "/api/v1/behavior/execution-event-oi/risk/analyze",
        json={
            "series": _v172_series(_v172_balanced_profile_bars()),
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "target": 101.5,
            "spread_pct": 1.20,
            "average_slippage_pct": 0.45,
            "depth_available": True,
            "visible_depth_value": 1_000_000.0,
            "event_context_status": "available",
            "options_context_status": "unavailable",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["risk_version"] == "execution-event-oi-risk.v1.73"
    assert data["execution_plan_status"] == "BLOCKED"
    assert data["confidence_cap"] == "WAIT"
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "EXEC-002")["passed"] is False
    assert data["trade_allowed"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True


def test_v173_exec_001_single_tick_wick_entry_becomes_wait_only():
    bars = _v172_balanced_profile_bars()
    bars[-1] = _v172_bar(40, 100.00, 105.00, 99.80, 100.10, 2_000.0)
    response = client.post(
        "/api/v1/behavior/execution-event-oi/risk/analyze",
        json={
            "series": _v172_series(bars),
            "entry_price": 105.0,
            "stop_loss": 99.0,
            "target": 107.0,
            "spread_pct": 0.08,
            "average_slippage_pct": 0.04,
            "depth_available": True,
            "visible_depth_value": 1_000_000.0,
            "event_context_status": "available",
            "options_context_status": "unavailable",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["single_tick_wick_risk"] is True
    assert data["confidence_cap"] == "WAIT"
    assert data["execution_plan_status"] == "BLOCKED"
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "EXEC-001")["passed"] is False


def test_v173_exec_005_event_003_opt_004_missing_data_is_marked_unavailable_not_clean():
    response = client.post(
        "/api/v1/behavior/execution-event-oi/risk/analyze",
        json={
            "series": _v172_series(_v172_balanced_profile_bars()),
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "target": 101.0,
            "depth_available": False,
            "event_context_status": "unavailable",
            "options_context_status": "unavailable",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["depth_context_status"] == "ohlcv_proxy"
    assert data["event_context_status"] == "unavailable"
    assert data["options_context_status"] == "unavailable"
    assert "event calendar unavailable" in data["unavailable_reasons"]
    assert "options/OI/gamma context unavailable" in data["unavailable_reasons"]
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "EVENT-003")["passed"] is False
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "OPT-004")["passed"] is False


def test_v173_opt_001_expected_move_limits_unrealistic_target():
    response = client.post(
        "/api/v1/behavior/execution-event-oi/risk/analyze",
        json={
            "series": _v172_series(_v172_balanced_profile_bars()),
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "target": 104.0,
            "spread_pct": 0.05,
            "average_slippage_pct": 0.03,
            "depth_available": True,
            "visible_depth_value": 1_000_000.0,
            "expected_move_pct": 1.50,
            "event_context_status": "available",
            "options_context_status": "available",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["expected_move_limit"] == "target_beyond_expected_move"
    assert data["confidence_cap"] == "WAIT"
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "OPT-001")["passed"] is False


def test_v173_opt_002_gamma_wall_and_expiry_pinning_context_are_surfaced():
    response = client.post(
        "/api/v1/behavior/execution-event-oi/risk/analyze",
        json={
            "series": _v172_series(_v172_balanced_profile_bars()),
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "target": 101.0,
            "spread_pct": 0.05,
            "average_slippage_pct": 0.03,
            "depth_available": True,
            "visible_depth_value": 1_000_000.0,
            "expected_move_pct": 1.50,
            "event_context_status": "available",
            "options_context_status": "available",
            "expiry_day": True,
            "max_pain": 100.20,
            "call_gamma_wall": 100.80,
            "put_gamma_wall": 99.20,
            "oi_concentration_pct": 72.0,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "call_gamma_wall_near_above_resistance" in data["gamma_wall_context"]
    assert "between_gamma_walls_pinning_range" in data["gamma_wall_context"]
    assert data["max_pain_magnet"] == "active_pin_zone"
    assert data["expiry_pinning_risk"] == "high"
    assert data["no_future_leakage"] is True


def test_v173_current_endpoint_and_capability_manifest_are_present():
    response = client.get("/api/v1/behavior/execution-event-oi/risk/current?symbol=TV173&timeframe=1m&rows=160")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["risk_version"] == "execution-event-oi-risk.v1.73"
    assert data["used_for_probability"] is False
    assert data["trade_allowed"] is False

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Execution Event OI Risk Guard")
    assert feature["status"] == "mock"
    assert "ExecutionEventOiRiskReport" in feature["required_data_contracts"]


def _v174_lifecycle_series(post_bars: list[tuple[float, float, float, float]]) -> dict:
    bars = [
        _v172_bar(1, 99.0, 99.4, 98.8, 99.2, 1_000.0),
        _v172_bar(2, 99.2, 99.6, 99.0, 99.4, 1_100.0),
        _v172_bar(3, 99.4, 99.8, 99.2, 99.6, 1_200.0),
        _v172_bar(4, 99.6, 100.1, 99.4, 99.9, 1_300.0),
        _v172_bar(5, 99.9, 100.2, 99.8, 100.0, 1_500.0),
    ]
    for offset, (open_price, high, low, close) in enumerate(post_bars, start=6):
        bars.append(_v172_bar(offset, open_price, high, low, close, 1_700.0 + offset * 20))
    return {"symbol": "TV174", "timeframe": "1m", "bars": bars, "snapshot_id": "tv174-fixture", "schema_version": "candles.test.v174"}


def _v174_payload(post_bars: list[tuple[float, float, float, float]], **overrides):
    payload = {
        "series": _v174_lifecycle_series(post_bars),
        "direction": "long",
        "entry_sequence_number": 5,
        "entry_price": 100.0,
        "initial_stop_loss": 99.0,
        "target_1": 101.0,
        "target_2": 102.0,
        "atr": 1.0,
        "minimum_post_entry_bars": 3,
    }
    payload.update(overrides)
    return payload


def test_v174_life_001_after_1r_reached_stop_moves_to_breakeven():
    response = client.post(
        "/api/v1/behavior/post-entry/lifecycle/analyze",
        json=_v174_payload([(100.0, 100.4, 99.8, 100.3), (100.3, 101.2, 100.2, 100.9), (100.9, 101.1, 100.4, 100.8)]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["lifecycle_version"] == "post-entry-lifecycle-manager.v1.74"
    assert data["mfe_r"] >= 1.0
    assert data["current_stop_loss"] >= data["entry_price"]
    assert "move_stop_to_breakeven_or_better" in "|".join(data["simulation_actions"])
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "LIFE-001")["passed"] is True


def test_v174_life_002_partial_exit_executes_in_simulation_only():
    response = client.post(
        "/api/v1/behavior/post-entry/lifecycle/analyze",
        json=_v174_payload([(100.0, 100.6, 99.8, 100.5), (100.5, 101.2, 100.4, 101.0), (101.0, 101.3, 100.7, 100.9)]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trade_state"] == "PARTIAL_EXIT"
    assert "partial exit" in data["partial_exit_plan"].lower()
    assert "record_simulated_partial_exit" in data["simulation_actions"]
    assert data["simulation_only"] is True
    assert data["trade_allowed"] is False
    assert data["order_routing_enabled"] is False


def test_v174_life_003_vwap_loss_after_long_marks_thesis_weakening():
    response = client.post(
        "/api/v1/behavior/post-entry/lifecycle/analyze",
        json=_v174_payload(
            [(100.0, 100.5, 99.8, 100.4), (100.4, 100.7, 100.1, 100.5), (100.5, 100.6, 100.0, 100.2)],
            current_vwap=100.5,
            initial_stop_loss=98.0,
        ),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trade_state"] == "THESIS_WEAKENING"
    assert data["current_thesis_status"] == "weakening"
    assert data["thesis_downgrade_reason"] == "VWAP lost after long entry"
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "LIFE-003")["passed"] is True


def test_v174_life_004_utad_after_entry_tightens_stop():
    response = client.post(
        "/api/v1/behavior/post-entry/lifecycle/analyze",
        json=_v174_payload(
            [(100.0, 100.6, 99.8, 100.4), (100.4, 100.9, 100.2, 100.7), (100.7, 101.0, 100.5, 100.8)],
            initial_stop_loss=98.0,
            structure_signal="utad",
        ),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trade_state"] == "THESIS_WEAKENING"
    assert data["thesis_downgrade_reason"] == "UTAD after long entry"
    assert data["current_stop_loss"] > 98.0
    assert "tighten_stop_and_block_add_on" in data["simulation_actions"]
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "LIFE-004")["passed"] is True


def test_v174_life_005_regime_flip_reduces_confidence_and_blocks_add_on():
    response = client.post(
        "/api/v1/behavior/post-entry/lifecycle/analyze",
        json=_v174_payload(
            [(100.0, 100.5, 99.8, 100.3), (100.3, 100.8, 100.2, 100.6), (100.6, 100.9, 100.4, 100.7)],
            initial_stop_loss=98.0,
            regime_state="flipped",
            add_on_requested=True,
        ),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["add_on_allowed"] is False
    assert data["confidence_adjustment"] == "block_add_on"
    assert "regime flipped" in data["thesis_downgrade_reason"]
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "LIFE-005")["passed"] is False


def test_v174_life_006_current_endpoint_and_capability_manifest_are_present():
    response = client.get("/api/v1/behavior/post-entry/lifecycle/current?symbol=TV174&timeframe=1m&rows=160")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["lifecycle_version"] == "post-entry-lifecycle-manager.v1.74"
    assert data["simulation_only"] is True
    assert data["trade_allowed"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True
    assert data["no_future_leakage"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Post-Entry Lifecycle Manager")
    assert feature["status"] == "mock"
    assert "PostEntryLifecycleReport" in feature["required_data_contracts"]


def _v175_payload(**overrides):
    payload = {
        "symbol": "TV175",
        "timeframe": "1m",
        "direction": "long",
        "data_quality_pass": True,
        "liquidity_grade": "A",
        "market_regime_score": 0.65,
        "relative_strength_score": 0.75,
        "structure_score": 0.70,
        "volume_auction_score": 0.50,
        "indicator_signal_score": 0.70,
        "external_ai_score": 0.10,
        "trap_score": 0.10,
        "event_risk_score": 0.10,
        "daily_resistance_conflict": False,
        "weak_sector": False,
        "post_entry_thesis_status": "not_entered",
        "evidence_count": 8,
        "no_future_leakage": True,
    }
    payload.update(overrides)
    return payload


def test_v175_arb_001_bullish_indicators_at_daily_resistance_are_downgraded():
    response = client.post(
        "/api/v1/behavior/final-confluence/arbiter/analyze",
        json=_v175_payload(daily_resistance_conflict=True, indicator_signal_score=0.90, structure_score=-0.20),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["arbiter_version"] == "final-confluence-conflict-arbiter.v1.75"
    assert data["final_decision"] in {"WATCH", "WAIT", "AVOID"}
    assert any(conflict["conflict_id"] == "ARB-C001" for conflict in data["conflicts_detected"])
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "ARB-001")["passed"] is True


def test_v175_arb_002_strong_breakout_with_weak_sector_reduces_confidence():
    response = client.post(
        "/api/v1/behavior/final-confluence/arbiter/analyze",
        json=_v175_payload(weak_sector=True, structure_score=0.90, relative_strength_score=0.35),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert any(conflict["conflict_id"] == "ARB-C002" for conflict in data["conflicts_detected"])
    assert data["confidence_interval"][1] <= 1.0
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "ARB-002")["passed"] is True


def test_v175_arb_003_high_trap_score_overrides_analog_strength():
    response = client.post(
        "/api/v1/behavior/final-confluence/arbiter/analyze",
        json=_v175_payload(trap_score=0.86, structure_score=0.95, indicator_signal_score=0.95),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["final_decision"] == "AVOID"
    assert data["dominant_blocker"] == "price action/order-flow proxy > analog or indicator strength"
    assert any(conflict["conflict_id"] == "ARB-C003" for conflict in data["conflicts_detected"])
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "ARB-003")["severity"] == "block"


def test_v175_arb_004_event_risk_downgrades_paper_to_watch():
    response = client.post(
        "/api/v1/behavior/final-confluence/arbiter/analyze",
        json=_v175_payload(
            market_regime_score=1.0,
            relative_strength_score=1.0,
            structure_score=1.0,
            volume_auction_score=1.0,
            indicator_signal_score=1.0,
            external_ai_score=1.0,
            event_risk_score=0.72,
        ),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["final_decision"] == "WATCH"
    assert any(conflict["conflict_id"] == "ARB-C004" for conflict in data["conflicts_detected"])
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "ARB-004")["passed"] is True


def test_v175_arb_005_liquidity_c_blocks_paper_candidate():
    response = client.post(
        "/api/v1/behavior/final-confluence/arbiter/analyze",
        json=_v175_payload(liquidity_grade="C", market_regime_score=1.0, structure_score=1.0, indicator_signal_score=1.0),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["final_decision"] == "AVOID"
    assert data["dominant_blocker"] == "liquidity_grade_c"
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "ARB-005")["passed"] is True


def test_v175_arb_006_post_entry_thesis_break_overrides_original_long_plan():
    response = client.post(
        "/api/v1/behavior/final-confluence/arbiter/analyze",
        json=_v175_payload(post_entry_thesis_status="invalidated", market_regime_score=1.0, structure_score=1.0),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["final_decision"] == "AVOID"
    assert data["dominant_blocker"] == "post_entry_thesis_invalidated"
    assert any(conflict["conflict_id"] == "ARB-C006" for conflict in data["conflicts_detected"])
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "ARB-006")["passed"] is True


def test_v175_arb_007_every_final_decision_has_reason_tree_and_safety_flags():
    response = client.get("/api/v1/behavior/final-confluence/arbiter/current?symbol=TV175&timeframe=1m&rows=160")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["human_reason_tree"]
    assert data["used_for_probability"] is False
    assert data["trade_allowed"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True
    assert next(gate for gate in data["gates"] if gate["gate_id"] == "ARB-007")["passed"] is True


def test_v175_arb_008_evidence_scores_sum_deterministically_and_manifest_is_present():
    payload = _v175_payload()
    first = client.post("/api/v1/behavior/final-confluence/arbiter/analyze", json=payload)
    second = client.post("/api/v1/behavior/final-confluence/arbiter/analyze", json=payload)
    assert first.status_code == second.status_code == 200
    a = first.json()["data"]
    b = second.json()["data"]
    assert a["raw_score"] == b["raw_score"]
    assert a["confluence_score"] == b["confluence_score"]
    assert a["final_decision"] == b["final_decision"]
    assert next(gate for gate in a["gates"] if gate["gate_id"] == "ARB-008")["passed"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Final Confluence Conflict Arbiter")
    assert feature["status"] == "mock"
    assert "FinalConfluenceArbiterReport" in feature["required_data_contracts"]


def test_behavior_full_context_supports_clean_long_context():
    base = 1_714_724_800_000_000_000
    five = 300_000_000_000
    hour = 3_600_000_000_000
    bars = [
        {
            "symbol": "FULLCTX",
            "timeframe": "5m",
            "timestamp_ns": base + idx * five,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": 2000.0 + idx * 250,
            "source": "mock",
            "sequence_number": idx + 1,
        }
        for idx, (open_price, high, low, close) in enumerate(
            [
                (100.0, 101.0, 99.5, 100.8),
                (100.8, 102.0, 100.4, 101.7),
                (101.7, 103.0, 101.2, 102.7),
                (102.7, 104.0, 102.4, 103.5),
            ]
        )
    ]
    htf = {
        "symbol": "FULLCTX",
        "timeframe": "1H",
        "snapshot_id": "fullctx-1h",
        "schema_version": "candles.v1",
        "bars": [
            {
                "symbol": "FULLCTX",
                "timeframe": "1H",
                "timestamp_ns": base - 2 * hour,
                "open": 96.0,
                "high": 99.0,
                "low": 95.0,
                "close": 98.0,
                "volume": 5000.0,
                "source": "mock",
                "sequence_number": 1,
            },
            {
                "symbol": "FULLCTX",
                "timeframe": "1H",
                "timestamp_ns": base - hour,
                "open": 98.0,
                "high": 102.0,
                "low": 97.5,
                "close": 101.0,
                "volume": 8000.0,
                "source": "mock",
                "sequence_number": 2,
            },
        ],
    }
    series = {"symbol": "FULLCTX", "timeframe": "5m", "bars": bars, "snapshot_id": "fullctx", "schema_version": "candles.v1"}
    response = client.post(
        "/api/v1/behavior/context/full",
        json={
            "series": series,
            "direction": "long",
            "decision_time_ns": base + 4 * five,
            "previous_day_high": 106.0,
            "previous_day_low": 96.0,
            "previous_close": 100.0,
            "opening_range_high": 103.0,
            "opening_range_low": 99.5,
            "volume_profile_hvn": 102.8,
            "volume_profile_lvn": 98.0,
            "higher_timeframe_series": [htf],
            "stock_return_pct": 1.4,
            "index_return_pct": 0.45,
            "sector_return_pct": 0.55,
            "global_risk_score": 0.2,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["final_context_bias"] == "supports_long"
    assert result["blocks_trade"] is False
    assert result["htf"]["confirmed"] is True
    assert result["market"]["market_alignment"] == "supports_long"
    assert result["context_quality_score"] >= 0.5


def test_behavior_session_rhythm_scores_india_session_windows():
    bars = []
    for idx, (hour, minute, open_price, high, low, close, volume) in enumerate(
        [
            (9, 15, 100.0, 101.0, 99.8, 100.7, 1200.0),
            (9, 20, 100.7, 101.8, 100.4, 101.5, 1500.0),
            (9, 25, 101.5, 102.5, 101.1, 102.2, 1900.0),
            (9, 30, 102.2, 103.0, 101.9, 102.8, 2200.0),
            (9, 35, 102.8, 103.7, 102.5, 103.4, 2600.0),
            (11, 30, 103.4, 103.6, 102.9, 103.1, 1000.0),
            (11, 35, 103.1, 103.4, 102.8, 103.0, 950.0),
            (11, 40, 103.0, 103.2, 102.6, 102.9, 900.0),
        ]
    ):
        bars.append(
            {
                "symbol": "SESSION",
                "timeframe": "5m",
                "timestamp_ns": ns_ist(2024, 6, 3, hour, minute),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "source": "mock",
                "sequence_number": idx + 1,
            }
        )
    response = client.post(
        "/api/v1/behavior/session/rhythm",
        json={
            "series": {
                "symbol": "SESSION",
                "timeframe": "5m",
                "bars": bars,
                "snapshot_id": "session-rhythm",
                "schema_version": "candles.v1",
            },
            "decision_time_ns": bars[-1]["timestamp_ns"],
            "timezone_offset_minutes": 330,
            "minimum_bars_per_segment": 2,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["rhythm_version"] == "behavior-session-memory.v0.17"
    assert result["day_of_week"] == "Monday"
    assert result["current_session_phase"] == "11:30-13:30_lunch_compression"
    phases = {segment["session_phase"] for segment in result["segments"]}
    assert "09:15-09:30_open_drive" in phases
    assert "11:30-13:30_lunch_compression" in phases
    assert result["best_trade_window"] != "unknown"
    assert 0.0 <= result["session_personality_score"] <= 1.0


def test_behavior_session_memory_profiles_keep_minimum_evidence_guard():
    response = client.get("/api/v1/behavior/stock/INFY/session-memory")
    assert response.status_code == 200
    profiles = response.json()["data"]
    assert len(profiles) == 7
    assert any(profile["sample_count"] >= 1 for profile in profiles)
    assert all(profile["minimum_sample_pass"] is False for profile in profiles)
    assert any(
        "Minimum evidence guard" in note
        for profile in profiles
        for note in profile["notes"]
    )


def test_behavior_day_of_week_memory_blocks_strong_probability_when_low_evidence():
    response = client.get("/api/v1/behavior/stock/INFY/day-of-week-memory")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["memory_version"] == "behavior-session-memory.v0.17"
    assert len(result["records"]) == 7
    assert result["total_samples"] >= 3
    assert result["minimum_sample_size"] == 30
    assert result["blocks_strong_probability"] is True
    assert any("Low evidence" in reason for reason in result["reasons"])


def test_behavior_stock_dna_summary_combines_session_rhythm_and_memory():
    bars = []
    for idx, (hour, minute, open_price, high, low, close, volume) in enumerate(
        [
            (9, 15, 100.0, 101.0, 99.8, 100.7, 1200.0),
            (9, 20, 100.7, 101.8, 100.4, 101.5, 1500.0),
            (9, 25, 101.5, 102.5, 101.1, 102.2, 1900.0),
            (14, 30, 102.2, 103.4, 102.0, 103.1, 2400.0),
            (14, 35, 103.1, 104.2, 102.9, 104.0, 2800.0),
        ]
    ):
        bars.append(
            {
                "symbol": "INFY",
                "timeframe": "5m",
                "timestamp_ns": ns_ist(2024, 6, 3, hour, minute),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "source": "mock",
                "sequence_number": idx + 1,
            }
        )
    response = client.post(
        "/api/v1/behavior/stock/INFY/dna/summary",
        json={
            "series": {
                "symbol": "INFY",
                "timeframe": "5m",
                "bars": bars,
                "snapshot_id": "stock-dna-summary",
                "schema_version": "candles.v1",
            },
            "decision_time_ns": bars[-1]["timestamp_ns"],
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["learning_status"] == "mock_seeded"
    assert result["minimum_evidence_pass"] is False
    assert result["stock_dna"]["symbol"] == "INFY"
    assert len(result["session_memory"]) == 7
    assert result["day_of_week_memory"]["blocks_strong_probability"] is True
    assert result["risk_warnings"]
    assert "minimum evidence" in result["stock_personality_summary"].lower()


def test_behavior_pattern_memory_builds_exact_day_shape_vector_and_ranked_matches():
    bars = []
    for idx, (hour, minute, open_price, high, low, close, volume) in enumerate(
        [
            (9, 15, 100.0, 101.0, 99.8, 100.7, 1200.0),
            (9, 20, 100.7, 101.8, 100.4, 101.5, 1500.0),
            (9, 25, 101.5, 102.5, 101.1, 102.2, 1900.0),
            (9, 30, 102.2, 103.0, 101.8, 102.4, 2400.0),
            (9, 35, 102.4, 103.2, 101.9, 102.1, 2600.0),
            (9, 40, 102.1, 102.9, 101.6, 101.9, 2300.0),
            (9, 45, 101.9, 102.4, 101.2, 101.5, 1800.0),
            (9, 50, 101.5, 102.0, 101.0, 101.6, 1600.0),
        ]
    ):
        bars.append(
            {
                "symbol": "INFY",
                "timeframe": "5m",
                "timestamp_ns": ns_ist(2024, 6, 3, hour, minute),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "source": "mock",
                "sequence_number": idx + 1,
            }
        )
    response = client.post(
        "/api/v1/behavior/pattern-memory/analyze",
        json={
            "series": {
                "symbol": "INFY",
                "timeframe": "5m",
                "bars": bars,
                "snapshot_id": "pattern-memory",
                "schema_version": "candles.v1",
            },
            "previous_close": 99.6,
            "decision_time_ns": bars[-1]["timestamp_ns"],
            "minimum_sample_size": 30,
            "max_matches": 5,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["memory_version"] == "behavior-pattern-memory.v0.18"
    assert result["vector_fields"] == [
        "gap_pct",
        "first_15m_return",
        "first_30m_range",
        "vwap_position_score",
        "trend_slope",
        "pullback_depth",
        "volume_curve",
        "atr_expansion",
        "high_break_time",
        "low_break_time",
        "close_position",
        "rejection_count",
        "breakout_failure_count",
    ]
    assert len(result["day_shape_vector"]["vector_values"]) == 13
    assert result["historical_match_count"] >= 3
    assert result["minimum_sample_pass"] is False
    assert result["evidence_quality"] == "LOW"
    assert result["no_trade_reason"] == "Low evidence. Similar history is not enough."
    assert len(result["matches"]) >= 3
    scores = [match["similarity_score_pct"] for match in result["matches"]]
    assert scores == sorted(scores, reverse=True)
    assert all(match["current_day_shape_vector"] is not None for match in result["matches"])
    assert all(match["matched_day_shape_vector"] is not None for match in result["matches"])
    assert "cosine_similarity" in result["similarity_methods"]
    assert "dtw_distance" in result["similarity_methods"]


def test_behavior_similar_days_endpoint_returns_recomputed_memory_matches():
    response = client.get("/api/v1/behavior/similar-days/INFY")
    assert response.status_code == 200
    matches = response.json()["data"]
    assert len(matches) >= 3
    assert matches[0]["similarity_method"] == "cosine_dtw_decay"
    assert matches[0]["cosine_similarity_pct"] >= 0
    assert matches[0]["dtw_similarity_pct"] >= 0
    assert matches[0]["minimum_sample_pass"] is False
    assert matches[0]["no_trade_reason"] == "Low evidence. Similar history is not enough."
    assert matches[0]["feature_match_summary"]


def test_behavior_similar_day_replay_is_deterministic_and_mock_only():
    matches = client.get("/api/v1/behavior/similar-days/INFY").json()["data"]
    similar_day_id = matches[0]["similar_day_id"]
    first = client.get(f"/api/v1/behavior/similar-days/INFY/replay/{similar_day_id}")
    second = client.get(f"/api/v1/behavior/similar-days/INFY/replay/{similar_day_id}")
    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data == second_data
    assert first_data["replay_version"] == "behavior-pattern-memory.v0.18"
    assert first_data["deterministic"] is True
    assert first_data["similar_day_id"] == similar_day_id
    assert len(first_data["events"]) == 16
    assert {event["source_mode"] for event in first_data["events"]} == {"REPLAY"}
    assert [event["watermark"] for event in first_data["events"]] == [event["watermark"] for event in second_data["events"]]
    assert any("cannot route orders" in note for note in first_data["replay_notes"])


def test_behavior_outcome_labeling_labels_target_before_stop():
    base = ns_ist(2024, 6, 3, 9, 15)
    five = 5 * 60_000_000_000
    bars = [
        {
            "symbol": "OUTCOME-TARGET",
            "timeframe": "5m",
            "timestamp_ns": base,
            "open": 100.0,
            "high": 100.8,
            "low": 99.8,
            "close": 100.5,
            "volume": 2000.0,
            "source": "mock",
            "sequence_number": 1,
        },
        {
            "symbol": "OUTCOME-TARGET",
            "timeframe": "5m",
            "timestamp_ns": base + five,
            "open": 100.5,
            "high": 103.2,
            "low": 100.2,
            "close": 102.8,
            "volume": 2600.0,
            "source": "mock",
            "sequence_number": 2,
        },
    ]
    response = client.post(
        "/api/v1/behavior/outcomes/label",
        json={
            "series": {
                "symbol": "OUTCOME-TARGET",
                "timeframe": "5m",
                "bars": bars,
                "snapshot_id": "outcome-target",
                "schema_version": "candles.v1",
            },
            "direction": "long",
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "target": 103.0,
            "entry_timestamp_ns": base,
            "pattern_id": "open_drive_vwap_support",
            "run_id": "pytest-target-outcome",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["outcome_version"] == "behavior-outcome-learning.v0.19"
    assert result["outcome_label"] == "TARGET_HIT"
    assert result["bars_to_target"] == 2
    assert result["bars_to_sl"] is None
    assert result["mfe"] >= 3.0
    assert result["audit_fields"]["causal_rule"].startswith("Outcome labeling reads only bars")


def test_behavior_outcome_labeling_labels_same_bar_stop_conservatively():
    base = ns_ist(2024, 6, 3, 9, 15)
    bars = [
        {
            "symbol": "OUTCOME-SAMEBAR",
            "timeframe": "5m",
            "timestamp_ns": base,
            "open": 100.0,
            "high": 102.5,
            "low": 98.8,
            "close": 100.4,
            "volume": 2400.0,
            "source": "mock",
            "sequence_number": 1,
        }
    ]
    response = client.post(
        "/api/v1/behavior/outcomes/label",
        json={
            "series": {
                "symbol": "OUTCOME-SAMEBAR",
                "timeframe": "5m",
                "bars": bars,
                "snapshot_id": "outcome-samebar",
                "schema_version": "candles.v1",
            },
            "direction": "long",
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "target": 102.0,
            "entry_timestamp_ns": base,
            "pattern_id": "same_bar_ambiguous",
            "run_id": "pytest-samebar-outcome",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["outcome_label"] == "SL_HIT"
    assert result["bars_to_target"] == 1
    assert result["bars_to_sl"] == 1
    assert "Stop loss was reached before target" in result["reason"]


def _v064_conservative_series(symbol: str, bars: list[dict], snapshot_id: str) -> dict:
    return {
        "symbol": symbol,
        "timeframe": "5m",
        "bars": bars,
        "snapshot_id": snapshot_id,
        "schema_version": "candles.v1",
    }


def _v064_bar(symbol: str, timestamp_ns: int, sequence_number: int, open_price: float, high: float, low: float, close: float) -> dict:
    return {
        "symbol": symbol,
        "timeframe": "5m",
        "timestamp_ns": timestamp_ns,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1500.0 + sequence_number * 100.0,
        "source": "mock",
        "sequence_number": sequence_number,
    }


def test_v064_conservative_outcome_labels_same_bar_as_ambiguous_not_win():
    base = ns_ist(2024, 6, 3, 9, 15)
    symbol = "V064-AMBIG"
    bars = [_v064_bar(symbol, base, 1, 100.2, 102.4, 98.8, 100.1)]
    response = client.post(
        "/api/v1/behavior/outcomes/conservative-label",
        json={
            "series": _v064_conservative_series(symbol, bars, "v064-ambiguous"),
            "direction": "long",
            "entry_price": 100.0,
            "stop_price": 99.0,
            "target_price": 102.0,
            "entry_time_ns": base,
            "order_type": "market_order",
            "quantity": 1.0,
            "atr": 1.0,
            "max_holding_bars": 12,
            "has_lower_timeframe_sequence": False,
            "pattern_id": "same_bar_target_stop",
            "run_id": "pytest-v064-ambiguous",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["outcome_label"] == "AMBIGUOUS_BOTH_HIT_SAME_BAR"
    assert result["same_bar_ambiguous"] is True
    assert result["lower_timeframe_required"] is True
    assert result["conservative_ordering_used"] is True
    assert result["net_return_after_costs"] < 0
    assert result["live_trading_blocked"] is True


def test_v064_conservative_outcome_labels_gap_through_stop_at_open():
    base = ns_ist(2024, 6, 3, 9, 15)
    symbol = "V064-GAPSTOP"
    bars = [_v064_bar(symbol, base, 1, 98.4, 99.2, 97.8, 98.9)]
    response = client.post(
        "/api/v1/behavior/outcomes/conservative-label",
        json={
            "series": _v064_conservative_series(symbol, bars, "v064-gap-stop"),
            "direction": "long",
            "entry_price": 100.0,
            "stop_price": 99.0,
            "target_price": 103.0,
            "entry_time_ns": base,
            "order_type": "market_order",
            "quantity": 1.0,
            "atr": 1.2,
            "max_holding_bars": 12,
            "pattern_id": "gap_through_stop",
            "run_id": "pytest-v064-gapstop",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["outcome_label"] == "GAP_THROUGH_STOP"
    assert result["gap_through_stop"] is True
    assert result["bars_to_stop"] == 1
    assert result["gross_return_pct"] < -0.01


def test_v064_conservative_outcome_labels_target_first_with_costs():
    base = ns_ist(2024, 6, 3, 9, 15)
    five = 5 * 60_000_000_000
    symbol = "V064-TARGET"
    bars = [
        _v064_bar(symbol, base, 1, 100.0, 100.8, 99.6, 100.4),
        _v064_bar(symbol, base + five, 2, 100.4, 101.4, 100.0, 101.2),
        _v064_bar(symbol, base + five * 2, 3, 101.2, 103.2, 100.9, 102.8),
    ]
    response = client.post(
        "/api/v1/behavior/outcomes/conservative-label",
        json={
            "series": _v064_conservative_series(symbol, bars, "v064-target-first"),
            "direction": "long",
            "entry_price": 100.0,
            "stop_price": 99.0,
            "target_price": 103.0,
            "entry_time_ns": base,
            "order_type": "market_order",
            "quantity": 1.0,
            "atr": 1.0,
            "max_holding_bars": 12,
            "pattern_id": "target_first",
            "run_id": "pytest-v064-target",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["outcome_label"] == "TARGET_HIT_FIRST"
    assert result["bars_to_target"] == 3
    assert result["bars_to_stop"] is None
    assert result["total_cost_pct"] > 0
    assert result["net_return_after_costs"] < result["gross_return_pct"]
    assert result["mfe_atr"] >= 3.0


def test_v064_conservative_outcome_limit_order_can_no_fill_when_same_bar_is_unsafe():
    base = ns_ist(2024, 6, 3, 9, 15)
    symbol = "V064-NOFILL"
    bars = [_v064_bar(symbol, base, 1, 101.0, 102.5, 98.7, 100.0)]
    response = client.post(
        "/api/v1/behavior/outcomes/conservative-label",
        json={
            "series": _v064_conservative_series(symbol, bars, "v064-no-fill"),
            "direction": "long",
            "entry_price": 100.0,
            "stop_price": 99.0,
            "target_price": 102.0,
            "entry_time_ns": base,
            "order_type": "limit_order",
            "quantity": 1.0,
            "atr": 1.0,
            "max_holding_bars": 12,
            "has_lower_timeframe_sequence": False,
            "pattern_id": "unsafe_limit_touch",
            "run_id": "pytest-v064-nofill",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["outcome_label"] == "NO_FILL"
    assert result["no_fill"] is True
    assert result["net_return_after_costs"] == 0
    assert result["order_routing_enabled"] is False


def test_v064_conservative_outcome_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    assert any(item["name"] == "Behavior Conservative Outcome Labeler" for item in features)

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    assert panels["conservative_outcome_labeler"]["contract_name"] == "ConservativeOutcomeLabelResult"

    current = client.get("/api/v1/behavior/outcomes/conservative-label/current")
    assert current.status_code == 200
    current_data = current.json()["data"]
    assert current_data["outcome_version"] == "behavior-conservative-outcome-labeler.v0.64"
    assert current_data["live_trading_blocked"] is True


def test_v065_combination_similarity_returns_weighted_non_overlapping_analogs():
    response = client.get("/api/v1/behavior/combination-similarity/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["combination_similarity_version"] == "behavior-combination-similarity.v0.65"
    assert report["minimum_sample_pass"] is True
    assert report["non_overlap_match_count"] == 30
    assert report["ann_prefilter_method"] == "deterministic_local_prefilter"
    assert report["non_overlap_enforced"] is True
    assert report["point_in_time_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert set(report["weight_config"].keys()) == {
        "candle_structure",
        "independent_indicator",
        "trend_momentum",
        "level_context",
        "session",
        "volatility_volume",
        "regime_market",
    }
    assert round(sum(report["weight_config"].values()), 6) == 1.0
    timestamps = [match["candidate_timestamp_ns"] for match in report["matches"]]
    assert len(timestamps) == len(set(timestamps))
    min_separation_ns = 20 * 300_000_000_000
    assert all(abs(left - right) >= min_separation_ns for idx, left in enumerate(timestamps) for right in timestamps[idx + 1 :])
    first_match = report["matches"][0]
    assert first_match["historical_date"]
    assert len(first_match["feature_contributions"]) == 7
    assert first_match["distance_metric"] == "mock_mixed_distance"
    assert "ordered RSI->VWAP->inside-candle" in first_match["explanation"]


def test_v065_combination_similarity_supports_non_same_candle_sequence_windows():
    response = client.post(
        "/api/v1/behavior/combination-similarity",
        json={
            "symbol": "RELIANCE",
            "timeframe": "3m",
            "seed": 6501,
            "source_bars": 1950,
            "minimum_match_count": 30,
            "max_matches": 30,
            "minimum_separation_bars": 24,
            "session_phase": "13:30-14:30",
            "market_regime": "post_lunch_expansion",
            "gap_class": "flat_open",
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    sequence = report["sequential_signal_pattern"]
    assert sequence["same_candle_required"] is False
    assert sequence["max_candle_span"] == 3
    assert sequence["ordered_indicators"] == [
        "rsi_14",
        "vwap_band_state",
        "inside_candle_height_ratio",
        "pivot_resistance_distance",
    ]
    assert sequence["candle_offsets"] == [-3, -2, -1, 0]
    assert sequence["minimum_sample_pass"] is True
    assert all(step["timestamp_ns"] <= sequence["completion_time_ns"] for step in sequence["steps"])
    assert report["matches"][0]["session_phase"] == "13:30-14:30"
    assert report["matches"][0]["market_regime"] == "post_lunch_expansion"
    assert report["matches"][0]["gap_class"] == "flat_open"


def test_v065_combination_similarity_blocks_confidence_when_evidence_is_low():
    response = client.post(
        "/api/v1/behavior/combination-similarity",
        json={
            "symbol": "LOWEVID",
            "timeframe": "5m",
            "seed": 65,
            "source_bars": 390,
            "minimum_match_count": 40,
            "max_matches": 12,
            "minimum_separation_bars": 30,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["minimum_sample_pass"] is False
    assert report["evidence_quality"] == "LOW"
    assert report["no_trade_reason"] == "Low evidence. Combination history is not enough."
    assert any(gate["gate_id"] == "TV-V065-003" and gate["passed"] is False for gate in report["gates"])
    assert report["trade_allowed"] is False


def test_v065_combination_similarity_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    assert any(item["name"] == "Behavior Combination Similarity" for item in features)

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    assert panels["combination_similarity"]["contract_name"] == "CombinationSimilarityReport"
    assert panels["combination_similarity"]["endpoint"] == "/api/v1/behavior/combination-similarity/current"
    assert panels["combination_similarity"]["manifest_status"] == "mock"


def test_v066_shared_snapshot_kronos_contract_matches_identity_fields():
    response = client.post(
        "/api/v1/kronos/forecast-shared-snapshot",
        json={
            "symbol": "RELIANCE",
            "timeframe": "5m",
            "seed": 66,
            "lookback_candles": 64,
            "forecast_horizon_bars": 12,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    snapshot = report["snapshot"]
    receipt = report["receipt"]
    integrity = report["integrity"]
    assert report["report_version"] == "shared-analysis-snapshot.v0.66.kronos-forecast"
    assert snapshot["snapshot_id"] == receipt["kronos_input_snapshot_id"]
    assert snapshot["source_snapshot_hash"] == receipt["kronos_input_snapshot_hash"]
    assert snapshot["decision_time_ns"] == receipt["decision_time_ns"]
    assert snapshot["last_bar_timestamp_ns"] == receipt["last_bar_timestamp_ns"]
    assert integrity["identity_match"] is True
    assert integrity["fail_closed"] is False
    assert integrity["twin_comparison_allowed"] is True
    assert integrity["arbiter_action"] == "RESEARCH_COMPARE_ALLOWED"
    assert report["kronos_forecast"]["trade_allowed"] is False
    assert report["kronos_forecast"]["order_routing_enabled"] is False
    assert report["kronos_forecast"]["live_trading_blocked"] is True
    assert report["behavior_can_continue_without_kronos"] is True


def test_v066_shared_snapshot_kronos_contract_fails_closed_on_hash_mismatch():
    response = client.post(
        "/api/v1/kronos/forecast-shared-snapshot",
        json={
            "symbol": "RELIANCE",
            "timeframe": "5m",
            "seed": 66,
            "force_kronos_hash_mismatch": True,
        },
    )
    assert response.status_code == 200
    integrity = response.json()["data"]["integrity"]
    assert integrity["identity_match"] is False
    assert integrity["fail_closed"] is True
    assert integrity["twin_comparison_allowed"] is False
    assert integrity["arbiter_action"] == "WAIT"
    assert "source_snapshot_hash" in integrity["mismatch_fields"]


def test_v066_shared_snapshot_kronos_contract_fails_closed_on_decision_time_mismatch():
    response = client.post(
        "/api/v1/twin/snapshot-integrity",
        json={
            "symbol": "INFY",
            "timeframe": "3m",
            "seed": 6601,
            "force_decision_time_mismatch": True,
        },
    )
    assert response.status_code == 200
    integrity = response.json()["data"]
    assert integrity["identity_match"] is False
    assert integrity["fail_closed"] is True
    assert integrity["twin_comparison_allowed"] is False
    assert "decision_time_ns" in integrity["mismatch_fields"]
    assert integrity["trade_allowed"] is False
    assert integrity["live_trading_blocked"] is True


def test_v066_shared_snapshot_kronos_contract_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    assert any(item["name"] == "Kronos Shared Snapshot Contract" for item in features)

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    assert panels["kronos_shared_snapshot"]["contract_name"] == "KronosSharedSnapshotForecastReport"
    assert panels["kronos_shared_snapshot"]["endpoint"] == "/api/v1/kronos/forecast-shared-snapshot/current"
    assert panels["kronos_shared_snapshot"]["manifest_status"] == "mock"


def test_v067_full_twin_analysis_compares_barrier_probabilities_after_snapshot_integrity():
    response = client.post(
        "/api/v1/twin/full-analysis",
        json={"symbol": "RELIANCE", "timeframe": "5m", "seed": 67},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["full_twin_version"] == "full-twin-analysis.v0.67"
    assert report["snapshot_integrity"]["identity_match"] is True
    assert report["kronos_barrier_projection"]["projection_version"] == "kronos-barrier-projection.v0.67"
    assert report["kronos_barrier_projection"]["raw_path_not_direct_evidence"] is True
    assert set(report["kronos_barrier_projection"]["barrier_sequence_distribution"]) == {"TARGET_FIRST", "STOP_FIRST", "TIME_EXIT"}
    assert report["behavior"]["combination_similarity"]["combination_similarity_version"] == "behavior-combination-similarity.v0.65"
    assert report["behavior_authority_preserved"] is True
    assert report["kronos_confidence_boost_allowed"] is False
    assert report["confidence_delta_from_kronos"] == 0.0
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["openalgo_broker_route_created"] is False
    assert any(gate["gate_id"] == "TV-V067-003" and gate["passed"] is True for gate in report["gates"])


def test_v067_full_twin_analysis_fails_closed_when_shared_snapshot_mismatches():
    response = client.post(
        "/api/v1/twin/full-analysis",
        json={"symbol": "RELIANCE", "timeframe": "5m", "seed": 67, "force_kronos_hash_mismatch": True},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["snapshot_integrity"]["identity_match"] is False
    assert report["snapshot_integrity"]["fail_closed"] is True
    assert report["agreement_state"] == "SNAPSHOT_MISMATCH"
    assert report["arbiter_action"] == "WAIT"
    assert "source_snapshot_hash" in report["snapshot_integrity"]["mismatch_fields"]
    assert report["trade_allowed"] is False


def test_v067_full_twin_analysis_behavior_no_trade_overrides_kronos_agreement():
    response = client.post(
        "/api/v1/twin/full-analysis",
        json={"symbol": "INFY", "timeframe": "5m", "seed": 6701, "force_behavior_no_trade": True},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["behavior"]["behavior_decision"]["final_trade_decision"] == "NO_TRADE"
    assert report["agreement_state"] == "NO_TRADE"
    assert report["arbiter_action"] == "NO_TRADE"
    assert any("Kronos cannot override" in reason for reason in report["conflict_reasons"])
    assert report["kronos_cannot_override_no_trade"] is True
    assert report["kronos_cannot_override_risk"] is True
    assert report["trade_allowed"] is False


def test_v067_full_twin_analysis_direction_conflict_reduces_to_wait():
    response = client.post(
        "/api/v1/twin/full-analysis",
        json={"symbol": "INFY", "timeframe": "5m", "seed": 6702, "force_kronos_hard_conflict": True},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["agreement_state"] == "HARD_CONFLICT"
    assert report["arbiter_action"] == "WAIT"
    assert any("disagree" in reason.lower() for reason in report["conflict_reasons"])
    assert report["openalgo_broker_route_created"] is False


def test_v067_full_twin_analysis_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    assert any(item["name"] == "Full Twin Analysis" for item in features)

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    assert panels["full_twin_analysis"]["contract_name"] == "FullTwinAnalysisReport"
    assert panels["full_twin_analysis"]["endpoint"] == "/api/v1/twin/full-analysis/current"
    assert panels["full_twin_analysis"]["manifest_status"] == "mock"


def test_v068_walk_forward_validation_publishes_engine_specific_oos_metrics():
    response = client.get("/api/v1/behavior/walk-forward/current?symbol=RELIANCE")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["validation_version"] == "walk-forward-validation.v0.68"
    assert report["symbol"] == "RELIANCE"
    assert report["method"] == "walk_forward_optimization"
    assert report["fold_count"] >= 5
    assert report["all_folds_out_of_sample"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert {summary["engine"] for summary in report["engine_summaries"]} == {"behavior", "kronos", "twin"}
    for fold in report["folds"]:
        assert fold["train_end_ns"] < fold["test_start_ns"]
        assert fold["out_of_sample_only"] is True
        assert fold["no_future_leakage"] is True
        assert 0.0 <= fold["behavior_precision_at_10"] <= 1.0
        assert 0.0 <= fold["kronos_precision_at_10"] <= 1.0
        assert 0.0 <= fold["twin_precision_at_10"] <= 1.0


def test_v068_walk_forward_validation_checks_calibration_and_weight_stability():
    response = client.post(
        "/api/v1/behavior/walk-forward",
        json={"symbol": "INFY", "timeframes": ["1m", "3m", "5m"], "seed": 6801},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["expected_calibration_error_threshold"] == 0.05
    assert report["recent_ece_recalibration_trigger"] == 0.1
    assert report["promotion_allowed"] is False
    assert report["research_only"] is True
    assert all("mean_ece" in summary for summary in report["engine_summaries"])
    assert all("mean_precision_at_10" in summary for summary in report["engine_summaries"])
    assert report["family_weight_stability"]
    if report["weight_stability_passed"]:
        assert all(item["stable"] is True for item in report["family_weight_stability"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V068-004"]["passed"] is True
    assert "Behavior, Kronos, and Twin" in gates["TV-V068-004"]["evidence"]
    assert "promotion_allowed=false" in gates["TV-V068-008"]["evidence"]


def test_v068_walk_forward_validation_blocks_low_evidence_calibration():
    response = client.post(
        "/api/v1/behavior/walk-forward",
        json={
            "symbol": "SBIN",
            "timeframes": ["weekly"],
            "seed": 6802,
            "minimum_calibration_outcomes": 1000,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V068-003"]["passed"] is False
    assert report["calibration_passed"] is False
    assert any(
        "Minimum calibration outcome guard" in note
        for summary in report["engine_summaries"]
        for note in summary["notes"]
    )


def test_v068_walk_forward_validation_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Walk-Forward Validation v0.68")
    assert feature["status"] == "mock"
    assert "WalkForwardValidationReport" in feature["required_data_contracts"]
    assert "TV-V068-005" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["walk_forward_validation_v068"]
    assert panel["contract_name"] == "WalkForwardValidationReport"
    assert panel["endpoint"] == "/api/v1/behavior/walk-forward/current"
    assert panel["manifest_status"] == "mock"


def test_v069_indicator_observations_emit_complete_value_contracts():
    response = client.get("/api/v1/behavior/indicators/observations/current?symbol=RELIANCE&timeframe=5m")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["observation_version"] == "indicator-observation-contracts.v0.69"
    assert report["symbol"] == "RELIANCE"
    assert report["observation_count"] > 0
    assert report["multi_output_indicator_count"] > 0
    assert report["all_observations_have_lineage"] is True
    assert report["all_available_are_point_in_time_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    required_fields = {
        "observation_id",
        "snapshot_id",
        "indicator_id",
        "output_name",
        "raw_value",
        "normalized_value",
        "rolling_percentile",
        "session_percentile",
        "regime_percentile",
        "slope_1",
        "slope_n",
        "acceleration",
        "state",
        "signal",
        "persistence_bars",
        "bars_since_event",
        "available",
        "availability_reason",
        "formula_hash",
        "implementation_version",
    }
    first = report["observations"][0]
    assert required_fields.issubset(first.keys())


def test_v069_indicator_observations_preserve_unavailable_outputs_without_zero_coercion():
    response = client.post(
        "/api/v1/behavior/indicators/observations",
        json={
            "symbol": "INFY",
            "timeframe": "weekly",
            "seed": 6901,
            "source_bars": 390,
            "max_indicators": 12,
            "include_unavailable": True,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    unavailable = [item for item in report["observations"] if item["available"] is False]
    assert unavailable
    assert report["unavailable_observations_preserved"] is True
    assert all(item["raw_value"] is None for item in unavailable)
    assert all(item["state"] == "UNAVAILABLE" for item in unavailable)
    assert all(item["availability_reason"] for item in unavailable)


def test_v069_indicator_observations_are_multi_output_with_shared_lineage():
    response = client.post(
        "/api/v1/behavior/indicators/observations",
        json={"symbol": "SBIN", "timeframe": "5m", "seed": 6902, "max_indicators": 8},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    by_indicator: dict[str, list[dict]] = {}
    for item in report["observations"]:
        by_indicator.setdefault(item["indicator_id"], []).append(item)
    multi = next(items for items in by_indicator.values() if len(items) > 1)
    assert len({item["output_name"] for item in multi}) > 1
    assert len({item["formula_hash"] for item in multi}) == 1
    assert len({item["implementation_version"] for item in multi}) == 1
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V069-002"]["passed"] is True
    assert gates["TV-V069-004"]["passed"] is True
    assert gates["TV-V069-006"]["passed"] is True


def test_v069_indicator_observations_are_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Indicator Observation Contracts")
    assert feature["status"] == "mock"
    assert "IndicatorObservationReport" in feature["required_data_contracts"]
    assert "TV-V069-005" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["indicator_observations_v069"]
    assert panel["contract_name"] == "IndicatorObservationReport"
    assert panel["endpoint"] == "/api/v1/behavior/indicators/observations/current"
    assert panel["manifest_status"] == "mock"


def test_v070_pattern_taxonomy_registers_all_required_pattern_families():
    response = client.get("/api/v1/behavior/patterns/taxonomy/current?symbol=RELIANCE&timeframe=5m")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["taxonomy_version"] == "pattern-market-structure-taxonomy.v0.70"
    assert report["symbol"] == "RELIANCE"
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    families = {entry["family"] for entry in report["entries"]}
    assert {"candle", "swing", "harmonic", "level", "flow", "indicator_activity", "forecast"}.issubset(families)
    assert report["all_entries_have_lifecycle_contracts"] is True
    assert report["decorative_patterns_blocked"] is True
    assert all(entry["activity_record_required"] is True for entry in report["entries"])


def test_v070_pattern_taxonomy_preserves_harmonic_trendline_and_neighbor_contracts():
    response = client.post(
        "/api/v1/behavior/patterns/taxonomy",
        json={"symbol": "INFY", "timeframe": "15m", "seed": 7001},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    harmonic = report["harmonic_geometry"]
    assert {"Gartley", "Bat", "Butterfly", "Crab", "Deep Crab", "Cypher", "AB=CD", "Three Drives"}.issubset(
        set(harmonic["pattern_names"])
    )
    assert harmonic["completion_zone_required"] is True
    assert harmonic["invalidation_zone_required"] is True
    trendline = report["trendline_respect_evidence"]
    assert trendline["objective_evidence_required"] is True
    assert trendline["touch_count"] > 0
    assert "normalized_touch_error" in trendline
    assert "post_touch_excursion_atr" in trendline
    neighbor = report["candle_neighbor_effect"]
    assert neighbor["no_wick_detection_required"] is True
    assert neighbor["neighbor_confirmation_required"] is True
    assert "upper_wick_to_body_ratio" in neighbor["anatomy_features"]
    assert "previous_5_candles" in neighbor["local_windows"]
    assert "next_outcome_window_for_historical_labels_only" in neighbor["local_windows"]


def test_v070_pattern_activity_records_capture_outcome_relationship_fields():
    response = client.post(
        "/api/v1/behavior/patterns/taxonomy",
        json={"symbol": "SBIN", "timeframe": "3m", "seed": 7002, "include_activity_records": True},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["activity_records"]
    activity = report["activity_records"][0]
    required = {
        "activity_present",
        "activity_type",
        "activity_direction",
        "activity_strength",
        "activity_start_time",
        "activity_end_time",
        "activity_duration_bars",
        "activity_price_zone",
        "activity_timeframe",
        "activity_parameters",
        "activity_quality",
        "activity_confirmation_state",
        "activity_invalidation_state",
        "bars_before_outcome",
        "outcome_distribution_after_activity",
    }
    assert required.issubset(activity.keys())
    assert activity["point_in_time_safe"] is True
    assert set(activity["outcome_distribution_after_activity"]) == {"continuation", "reversal", "range", "fakeout"}
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V070-001"]["passed"] is True
    assert gates["TV-V070-004"]["passed"] is True
    assert gates["TV-V070-006"]["passed"] is True


def test_v070_pattern_taxonomy_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Structure Pattern Registry")
    assert feature["status"] == "mock"
    assert "PatternTaxonomyReport" in feature["required_data_contracts"]
    assert "TV-V070-005" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["pattern_taxonomy_v070"]
    assert panel["contract_name"] == "PatternTaxonomyReport"
    assert panel["endpoint"] == "/api/v1/behavior/patterns/taxonomy/current"
    assert panel["manifest_status"] == "mock"


def test_v071_exact_time_session_memory_builds_minute_profiles_without_future_leakage():
    response = client.get("/api/v1/behavior/exact-time/session-memory/current?symbol=RELIANCE&timeframe=5m")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["memory_version"] == "exact-time-session-memory.v0.71"
    assert report["symbol"] == "RELIANCE"
    assert report["minute_profiles"]
    assert report["current_minute_profile"]["includes_later_timestamps"] is False
    assert report["all_profiles_exclude_later_timestamps"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    for profile in report["minute_profiles"]:
        assert profile["independent_evidence_count"] >= 0
        assert profile["includes_later_timestamps"] is False
        assert profile["session_phase"] in {boundary["session_phase"] for boundary in report["exchange_boundaries"]}


def test_v071_exact_time_session_memory_uses_exchange_calendar_boundaries_and_calendar_classes():
    response = client.post(
        "/api/v1/behavior/exact-time/session-memory",
        json={"symbol": "INFY", "timeframe": "3m", "seed": 7101, "minimum_evidence_per_bucket": 30},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["exchange"] == "NSE"
    assert report["timezone"] == "Asia/Calcutta"
    assert report["session_boundaries_follow_exchange_calendar"] is True
    assert len(report["exchange_boundaries"]) >= 7
    assert all(boundary["follows_exchange_calendar"] is True for boundary in report["exchange_boundaries"])
    calendar_classes = {profile["calendar_class"] for profile in report["calendar_profiles"]}
    assert {"normal_day", "monday", "friday", "expiry_day", "post_holiday", "results_day", "rbi_fed_day"}.issubset(calendar_classes)
    assert all(profile["independent_evidence_count"] >= 0 for profile in report["calendar_profiles"])


def test_v071_exact_time_session_memory_tracks_session_transitions_and_evidence_counts():
    response = client.post(
        "/api/v1/behavior/exact-time/session-memory",
        json={"symbol": "SBIN", "timeframe": "15m", "seed": 7102},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["session_transitions"]
    assert report["independent_evidence_counts"]["minute_profiles"] > 0
    assert report["independent_evidence_counts"]["session_transitions"] > 0
    assert report["independent_evidence_counts"]["calendar_profiles"] > 0
    transition = report["session_transitions"][0]
    assert "transition_name" in transition
    assert "behavior_change_rate_pct" in transition
    assert "continuation_to_reversal_rate_pct" in transition
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V071-002"]["passed"] is True
    assert gates["TV-V071-003"]["passed"] is True
    assert gates["TV-V071-004"]["passed"] is True
    assert gates["TV-V071-007"]["passed"] is True


def test_v071_exact_time_session_memory_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Exact-Time Session Memory")
    assert feature["status"] == "mock"
    assert "ExactTimeSessionMemoryReport" in feature["required_data_contracts"]
    assert "TV-FI-034" in feature["promotion_gates"]
    assert "TV-FI-035" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["exact_time_session_memory_v071"]
    assert panel["contract_name"] == "ExactTimeSessionMemoryReport"
    assert panel["endpoint"] == "/api/v1/behavior/exact-time/session-memory/current"
    assert panel["manifest_status"] == "mock"


def test_v072_multi_timeframe_conflict_builds_required_timeframe_matrix():
    response = client.get("/api/v1/behavior/timeframes/conflict/current?symbol=RELIANCE&primary_timeframe=5m")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["conflict_version"] == "multi-timeframe-conflict.v0.72"
    assert report["symbol"] == "RELIANCE"
    assert len(report["seven_timeframe_matrix"]) == 9
    assert {row["timeframe"] for row in report["seven_timeframe_matrix"]} == {"1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"}
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert 0.0 <= report["alignment_score"] <= 1.0


def test_v072_multi_timeframe_conflict_blocks_developing_bars_from_decision():
    response = client.post(
        "/api/v1/behavior/timeframes/conflict",
        json={"symbol": "INFY", "seed": 7201, "source_bars": 1950, "primary_timeframe": "5m"},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    developing = [row for row in report["seven_timeframe_matrix"] if row["developing_bar_visible"]]
    assert developing
    assert report["developing_bars_blocked_from_decision"] is True
    assert all(row["developing_bar_decision_safe"] is False for row in developing)
    assert any(exp["conflict_type"] == "developing_bar_blocked" for exp in report["conflict_explanations"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V072-002"]["passed"] is True


def test_v072_multi_timeframe_conflict_reports_unavailable_and_direction_conflicts():
    response = client.post(
        "/api/v1/behavior/timeframes/conflict",
        json={"symbol": "SBIN", "seed": 7202, "source_bars": 390, "primary_timeframe": "5m"},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["unavailable_timeframes"]
    assert any(exp["conflict_type"] == "timeframe_data_unavailable" for exp in report["conflict_explanations"])
    assert any(exp["severity"] in {"watch", "block"} for exp in report["conflict_explanations"])
    assert report["final_mtf_state"] in {"mixed", "avoid", "unavailable", "supports_long", "supports_short"}
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V072-001"]["passed"] is True
    assert gates["TV-V072-003"]["passed"] is True
    assert gates["TV-V072-004"]["passed"] is True
    assert gates["TV-V072-005"]["passed"] is True


def test_v072_multi_timeframe_conflict_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Multi-Timeframe Conflict Engine")
    assert feature["status"] == "mock"
    assert "MultiTimeframeConflictReport" in feature["required_data_contracts"]
    assert "TV-FI-036" in feature["promotion_gates"]
    assert "TV-FI-037" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["multi_timeframe_conflict_v072"]
    assert panel["contract_name"] == "MultiTimeframeConflictReport"
    assert panel["endpoint"] == "/api/v1/behavior/timeframes/conflict/current"
    assert panel["manifest_status"] == "mock"


def test_mtf_001_real_aggregation_uses_ohlcv_rules():
    from app.behavior.timeframe_feature_builder import NANOSECONDS_PER_MINUTE, build_closed_aggregate_bars

    rows = []
    base = 1_714_698_900_000_000_000
    for index, close in enumerate([101, 102, 103, 104, 105, 106], start=1):
        timestamp = base + (index - 1) * NANOSECONDS_PER_MINUTE
        rows.append(
            {
                "symbol": "UNIT",
                "sequence_number": index,
                "timestamp_ns": timestamp,
                "close_time_ns": timestamp + NANOSECONDS_PER_MINUTE,
                "open": float(100 + index),
                "high": float(101 + index),
                "low": float(99 + index),
                "close": float(close),
                "volume": float(index * 10),
            }
        )

    aggregates = build_closed_aggregate_bars(rows, "3m")
    assert len(aggregates) == 2
    assert aggregates[0]["open"] == 101.0
    assert aggregates[0]["high"] == 104.0
    assert aggregates[0]["low"] == 100.0
    assert aggregates[0]["close"] == 103.0
    assert aggregates[0]["volume"] == 60.0


def test_mtf_002_incomplete_aggregate_is_not_decision_safe():
    from app.behavior.timeframe_feature_builder import NANOSECONDS_PER_MINUTE, build_closed_aggregate_bars

    base = 1_714_698_900_000_000_000
    rows = [
        {
            "symbol": "UNIT",
            "sequence_number": index,
            "timestamp_ns": base + (index - 1) * NANOSECONDS_PER_MINUTE,
            "close_time_ns": base + index * NANOSECONDS_PER_MINUTE,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0 + index,
            "volume": 100.0,
        }
        for index in range(1, 5)
    ]

    aggregates = build_closed_aggregate_bars(rows, "3m")
    assert len(aggregates) == 1
    report = client.post(
        "/api/v1/behavior/timeframes/conflict",
        json={"symbol": "INFY", "seed": 7201, "source_bars": 1951, "primary_timeframe": "5m"},
    ).json()["data"]
    developing = [row for row in report["seven_timeframe_matrix"] if row["developing_bar_visible"]]
    assert developing
    assert all(row["developing_bar_decision_safe"] is False for row in developing)


def test_mtf_003_direction_comes_from_closed_bar_slope_not_seed():
    from app.behavior.multi_timeframe_conflict import _direction_from_aggregates

    up = [{"close": 100.0, "high": 101.0, "low": 99.0}, {"close": 103.0, "high": 104.0, "low": 102.0}]
    down = [{"close": 103.0, "high": 104.0, "low": 102.0}, {"close": 100.0, "high": 101.0, "low": 99.0}]
    flat = [{"close": 100.0, "high": 100.1, "low": 99.9}, {"close": 100.01, "high": 100.1, "low": 99.9}]
    assert _direction_from_aggregates(up) == "long"
    assert _direction_from_aggregates(down) == "short"
    assert _direction_from_aggregates(flat) == "range"


def test_mtf_004_lower_timeframe_pullback_inside_higher_uptrend_is_watch_not_block():
    from app.behavior.multi_timeframe_conflict import _explanations
    from app.models import TimeframeStateRecord

    matrix = [
        TimeframeStateRecord(
            timeframe="3m",
            htf_role="lower",
            closed_bars=10,
            latest_bar_close_time_ns=1,
            developing_bar_visible=False,
            developing_bar_decision_safe=False,
            state_direction="short",
            state_strength=0.62,
            compression_state="normal",
            aligned_with_primary=False,
            conflict_tags=["direction_conflict"],
            decision_safe=True,
        ),
        TimeframeStateRecord(
            timeframe="5m",
            htf_role="lower",
            closed_bars=10,
            latest_bar_close_time_ns=1,
            developing_bar_visible=False,
            developing_bar_decision_safe=False,
            state_direction="long",
            state_strength=0.74,
            compression_state="normal",
            aligned_with_primary=True,
            conflict_tags=[],
            decision_safe=True,
        ),
        TimeframeStateRecord(
            timeframe="15m",
            htf_role="intermediate",
            closed_bars=10,
            latest_bar_close_time_ns=1,
            developing_bar_visible=False,
            developing_bar_decision_safe=False,
            state_direction="long",
            state_strength=0.8,
            compression_state="normal",
            aligned_with_primary=True,
            conflict_tags=[],
            decision_safe=True,
        ),
    ]

    explanations = _explanations(matrix, "5m")
    pullback = next(item for item in explanations if item.conflict_type == "lower_timeframe_pullback_inside_higher_timeframe_trend")
    assert pullback.severity == "watch"
    assert pullback.recommended_action == "WAIT"


def test_mtf_005_higher_timeframe_opposition_blocks_confidence():
    response = client.post(
        "/api/v1/behavior/timeframes/conflict",
        json={"symbol": "INFY", "seed": 7202, "source_bars": 1950, "primary_timeframe": "5m"},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    if any(row["htf_role"] in {"intermediate", "higher"} and "direction_conflict" in row["conflict_tags"] for row in report["seven_timeframe_matrix"]):
        assert any(exp["severity"] == "block" for exp in report["conflict_explanations"])


def test_v163_real_mtf_pullback_endpoint_uses_closed_context_and_blocks_live():
    response = client.get("/api/v1/behavior/timeframes/pullback/current?symbol=RELIANCE&primary_timeframe=5m")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["pullback_version"] == "real-mtf-pullback.v1.63"
    assert report["source_conflict_version"] == "multi-timeframe-conflict.v0.72"
    assert report["symbol"] == "RELIANCE"
    assert report["final_action"] in {"WAIT", "WATCH", "AVOID"}
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["no_future_leakage"] is True
    assert report["closed_candle_only"] is True
    gate_ids = {gate["gate_id"] for gate in report["gates"]}
    assert {"TV-V163-001", "TV-V163-002", "TV-V163-003", "TV-V163-004", "TV-V163-005", "TV-V163-006"}.issubset(gate_ids)


def test_v163_lower_timeframe_pullback_inside_htf_trend_is_watch():
    from app.behavior.real_mtf_pullback import classify_mtf_pullback_context

    matrix = [
        _tf_record("1m", "lower", "short", 0.61),
        _tf_record("3m", "lower", "long", 0.65),
        _tf_record("5m", "lower", "long", 0.7),
        _tf_record("15m", "intermediate", "long", 0.78),
        _tf_record("1H", "intermediate", "long", 0.82),
        _tf_record("daily", "higher", "long", 0.86),
        _tf_record("weekly", "higher", "long", 0.88),
    ]
    result = classify_mtf_pullback_context(matrix, "5m")
    assert result["pullback_state"] == "pullback_in_trend"
    assert result["higher_timeframe_direction"] == "long"
    assert result["pullback_timeframes"] == ["1m"]
    assert result["opposition_timeframes"] == []


def test_v163_higher_timeframe_opposition_returns_avoid():
    response = client.post(
        "/api/v1/behavior/timeframes/pullback",
        json={"symbol": "INFY", "seed": 7202, "source_bars": 1950, "primary_timeframe": "5m"},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    if report["htf_opposition_detected"]:
        assert report["pullback_state"] == "htf_opposition"
        assert report["final_action"] == "AVOID"
        assert report["opposition_timeframes"]


def test_v163_real_mtf_pullback_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Real MTF Pullback Engine")
    assert feature["status"] == "mock"
    assert "RealMtfPullbackReport" in feature["required_data_contracts"]
    assert "TV-V163-001" in feature["promotion_gates"]
    assert "TV-V163-006" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["real_mtf_pullback_v163"]
    assert panel["title"] == "Real MTF Pullback v1.63"
    assert panel["contract_name"] == "RealMtfPullbackReport"
    assert panel["endpoint"] == "/api/v1/behavior/timeframes/pullback/current"
    assert panel["manifest_status"] == "mock"


def _tf_record(timeframe, role, direction, strength):
    from app.models import TimeframeStateRecord

    return TimeframeStateRecord(
        timeframe=timeframe,
        htf_role=role,
        closed_bars=12,
        latest_bar_close_time_ns=1,
        developing_bar_visible=False,
        developing_bar_decision_safe=False,
        state_direction=direction,
        state_strength=strength,
        compression_state="normal",
        aligned_with_primary=direction == "long",
        conflict_tags=[] if direction == "long" else ["direction_conflict"],
        decision_safe=True,
    )


def test_v073_analog_research_uses_mixed_distance_after_prefilter_and_non_overlap():
    response = client.get("/api/v1/behavior/analog-research/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["research_version"] == "analog-conditional-research.v0.73"
    assert "mixed_gower_dtw_jaccard" in report["mixed_distance_method"]
    assert report["ann_prefilter_ran_before_exact_refinement"] is True
    assert report["non_overlap_enforced"] is True
    assert report["all_displayed_analogs_precede_decision"] is True
    assert all(item["candidate_timestamp_precedes_decision"] for item in report["match_explanations"])
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V073-001"]["passed"] is True
    assert gates["TV-FI-096"]["passed"] is True
    assert gates["TV-FI-046"]["passed"] is True


def test_v073_value_band_discovery_applies_fdr_and_holdout():
    response = client.post(
        "/api/v1/behavior/analog-research",
        json={"symbol": "RELIANCE", "timeframe": "5m", "seed": 7301, "minimum_match_count": 30},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["value_bands"]
    assert report["false_discovery_control"]["method"] == "benjamini_hochberg"
    assert report["false_discovery_control"]["tested_hypothesis_count"] >= len(report["value_bands"])
    assert report["false_discovery_control"]["all_accepted_have_adjusted_p_value"] is True
    for band in report["value_bands"]:
        assert band["multiple_testing_correction"] == "benjamini_hochberg"
        assert "fdr_adjusted_p_value" in band
        assert "holdout_confirmed" in band
        assert len(band["confidence_interval"]) == 2
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-047"]["passed"] is True


def test_v073_conditional_rules_require_incremental_evidence_before_confidence_increase():
    response = client.post(
        "/api/v1/behavior/analog-research",
        json={"symbol": "INFY", "timeframe": "3m", "seed": 7302, "minimum_match_count": 30, "max_rule_depth": 3},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["incremental_evidence_required_for_confidence"] is True
    rules = report["conditional_rules"]
    assert rules
    allowed = [rule for rule in rules if rule["confidence_increase_allowed"]]
    assert allowed
    for rule in allowed:
        assert rule["incremental_evidence_count"] >= 30
        assert rule["cross_validation_passed"] is True
        assert rule["holdout_confirmed"] is True
        assert rule["generalization_status"] == "generalizing"
    unstable = [rule for rule in rules if rule["generalization_status"] == "unstable_non_generalizing"]
    assert unstable
    assert all(rule["confidence_increase_allowed"] is False for rule in unstable)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-048"]["passed"] is True
    assert gates["TV-FI-049"]["passed"] is True
    assert gates["TV-FI-050"]["passed"] is True


def test_v073_match_explanations_list_matches_and_mismatches():
    response = client.get("/api/v1/behavior/analog-research/current")
    assert response.status_code == 200
    report = response.json()["data"]
    explanations = report["match_explanations"]
    assert explanations
    for item in explanations:
        assert item["matched_features"]
        assert item["mismatched_features"]
        assert item["matched_values"]
        assert item["matched_patterns"]
        assert item["matched_timeframes"]
        assert item["matched_levels"]
        assert item["matched_contexts"]
        assert item["data_split"] in {"training", "validation", "holdout"}
        assert item["warnings"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-044"]["passed"] is True
    assert gates["TV-FI-045"]["passed"] is True


def test_v073_analog_research_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Analog Conditional Research")
    assert feature["status"] == "mock"
    assert "AnalogConditionalResearchReport" in feature["required_data_contracts"]
    assert "TV-FI-047" in feature["promotion_gates"]
    assert "TV-FI-096" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["analog_conditional_research_v073"]
    assert panel["contract_name"] == "AnalogConditionalResearchReport"
    assert panel["endpoint"] == "/api/v1/behavior/analog-research/current"
    assert panel["manifest_status"] == "mock"


def test_v074_event_sequence_mining_returns_same_and_lagged_chains():
    response = client.get("/api/v1/behavior/event-sequences/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["sequence_mining_version"] == "event-sequence-mining.v0.74"
    assert report["same_candle_sequence_count"] >= 1
    assert report["non_same_candle_sequence_count"] >= 1
    assert report["value_confluence_does_not_require_same_candle_signals"] is True
    assert report["same_indicators_different_order_are_different_sequences"] is True
    assert report["signals_after_outcome_excluded"] is True
    assert report["all_sequences_point_in_time_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    lagged = [pattern for pattern in report["sequence_patterns"] if pattern["lag_window_bars"] >= 2]
    assert lagged
    assert any(pattern["same_candle_event_count"] >= 2 for pattern in report["sequence_patterns"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V074-001"]["passed"] is True
    assert gates["TV-V074-002"]["passed"] is True
    assert gates["TV-FI-090"]["passed"] is True
    assert gates["TV-FI-092"]["passed"] is True


def test_v074_reciprocal_signals_are_pre_outcome_warnings_only():
    response = client.post(
        "/api/v1/behavior/event-sequences/mine",
        json={"symbol": "RELIANCE", "timeframe": "3m", "seed": 7401, "max_lookback_candles": 7},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["reciprocal_signal_detector_uses_only_pre_outcome_data"] is True
    reciprocal = report["reciprocal_signal_records"]
    assert reciprocal
    assert all(item["uses_only_pre_outcome_data"] is True for item in reciprocal)
    assert all(item["warning"] for item in reciprocal)
    assert any(pattern["reciprocal_signal_warning"] is True for pattern in report["sequence_patterns"])
    assert any(pattern["false_agreement_warning"] is True for pattern in report["sequence_patterns"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-091"]["passed"] is True
    assert gates["TV-V074-003"]["passed"] is True


def test_v074_prior_candle_body_wick_indicator_sequence_links_to_current_response():
    response = client.post(
        "/api/v1/behavior/event-sequences/mine",
        json={"symbol": "INFY", "timeframe": "5m", "seed": 7402, "max_lookback_candles": 5},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["prior_candle_sequences_compared_to_current_response"] is True
    records = report["prior_to_current_influence"]
    assert records
    record = records[0]
    assert record["prior_body_ratio_sequence"]
    assert record["prior_wick_ratio_sequence"]
    assert record["prior_no_wick_sequence"]
    assert record["prior_indicator_value_sequence"]
    assert record["prior_indicator_signal_sequence"]
    assert record["current_candle_response"] in {"expansion_up", "expansion_down", "reversal", "range_bound", "fakeout", "no_response"}
    assert record["supporting_case_ids"]
    assert record["counterexample_case_ids"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-111"]["passed"] is True
    assert gates["TV-FI-112"]["passed"] is True
    assert gates["TV-FI-113"]["passed"] is True


def test_v074_event_sequence_mining_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Event Sequence Mining")
    assert feature["status"] == "mock"
    assert "EventSequenceMiningReport" in feature["required_data_contracts"]
    assert "TV-FI-091" in feature["promotion_gates"]
    assert "TV-FI-111" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["event_sequence_mining_v074"]
    assert panel["contract_name"] == "EventSequenceMiningReport"
    assert panel["endpoint"] == "/api/v1/behavior/event-sequences/current"
    assert panel["manifest_status"] == "mock"


def test_v075_confluence_diagnostics_separate_nominal_from_independent_evidence():
    response = client.get("/api/v1/behavior/confluence/diagnostics/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["diagnostic_version"] == "false-agreement-confluence.v0.75"
    assert report["nominal_agreement_count"] >= report["independent_agreement_count"]
    assert report["redundant_agreement_count"] >= 1
    assert report["redundant_agreement_cannot_increase_confidence"] is True
    assert report["all_confluence_point_in_time_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    redundant_records = [item for item in report["indicator_value_confluence_records"] if item["redundant_feature_ids"]]
    assert redundant_records
    assert all(item["confidence_boost_allowed"] is False for item in redundant_records)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V075-003"]["passed"] is True
    assert gates["TV-V075-005"]["passed"] is True


def test_v075_delayed_confluence_timing_windows_are_visible():
    response = client.post(
        "/api/v1/behavior/confluence/diagnostics",
        json={"symbol": "RELIANCE", "timeframe": "3m", "seed": 7501, "max_lookback_candles": 7},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["value_confluence_supports_non_same_candle_signals"] is True
    windows = report["confluence_timing_windows"]
    assert windows
    delayed = [window for window in windows if window["same_candle_only"] is False]
    assert delayed
    assert any(window["delayed_signal_count"] >= 2 for window in delayed)
    assert all(window["point_in_time_safe"] for window in windows)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V075-002"]["passed"] is True
    assert gates["TV-FI-092"]["passed"] is True


def test_v075_false_agreement_blocks_misleading_nominal_consensus():
    response = client.post(
        "/api/v1/behavior/confluence/diagnostics",
        json={"symbol": "INFY", "timeframe": "5m", "seed": 7502, "minimum_independent_evidence": 30},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["false_agreement_warning"] is True
    assert report["confidence_blocked"] is True
    assert report["confidence_block_reasons"]
    false_records = report["false_agreement_records"]
    assert false_records
    for record in false_records:
        assert record["confidence_must_be_blocked"] is True
        assert record["uses_independent_historical_evidence"] is True
        assert record["historical_failure_rate_pct"] > 50
        assert record["failure_modes"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-094"]["passed"] is True
    assert gates["TV-V075-004"]["passed"] is True


def test_v075_confluence_diagnostics_is_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior False Agreement Confluence Diagnostics")
    assert feature["status"] == "mock"
    assert "FalseAgreementConfluenceReport" in feature["required_data_contracts"]
    assert "TV-FI-094" in feature["promotion_gates"]
    assert "TV-V075-003" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["false_agreement_confluence_v075"]
    assert panel["contract_name"] == "FalseAgreementConfluenceReport"
    assert panel["endpoint"] == "/api/v1/behavior/confluence/diagnostics/current"
    assert panel["manifest_status"] == "mock"


def test_v076_design_similarity_is_price_level_invariant_and_research_only():
    response = client.get("/api/v1/behavior/design-similarity/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["design_version"] == "design-similarity-shape-grammar.v0.76"
    assert report["shape_normalization_method"] == "log_return_zscore_time_resampled"
    assert report["price_level_invariant"] is True
    assert report["shifted_price_similarity_delta_pct"] <= 0.001
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V076-001"]["passed"] is True
    assert gates["TV-FI-093"]["passed"] is True


def test_v076_shape_grammar_covers_visual_market_designs_and_counterexamples():
    response = client.post(
        "/api/v1/behavior/design-similarity/score",
        json={"symbol": "RELIANCE", "timeframe": "3m", "seed": 7601, "design_window_bars": 60},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    labels = {component["label"] for component in report["grammar_components"]}
    assert {"open_drive_pullback", "w_range_reversal", "v_reversal", "coil_compression", "range_box", "open_drive_fade"}.issubset(labels)
    assert report["dominant_design"] in labels
    assert report["similarity_candidates"]
    assert report["counterexample_count"] >= 1
    assert any(candidate["counterexample"] is True and candidate["mismatched_components"] for candidate in report["similarity_candidates"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V076-002"]["passed"] is True
    assert gates["TV-FI-082"]["passed"] is True


def test_v076_geometry_references_are_reproducible_and_can_contradict():
    response = client.post(
        "/api/v1/behavior/design-similarity/score",
        json={"symbol": "INFY", "timeframe": "5m", "seed": 7602, "include_overlay_evidence": True},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    refs = report["geometry_references"]
    ref_types = {item["reference_type"] for item in refs}
    assert {"harmonic", "fibonacci", "curve", "trendline", "elliott"}.issubset(ref_types)
    assert report["all_geometry_reproducible"] is True
    assert report["harmonic_and_trendline_may_contradict"] is True
    assert report["forming_harmonic_not_labeled_confirmed"] is True
    harmonic = [item for item in refs if item["reference_type"] == "harmonic"][0]
    assert harmonic["confirmation_state"] == "forming"
    assert harmonic["ratio_labels"]
    trendline = [item for item in refs if item["reference_type"] == "trendline"][0]
    assert trendline["respect_score"] < 0.5
    assert trendline["contradiction"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-038"]["passed"] is True
    assert gates["TV-FI-039"]["passed"] is True
    assert gates["TV-FI-040"]["passed"] is True
    assert gates["TV-FI-078"]["passed"] is True


def test_v076_chart_overlay_evidence_is_frontend_ready_and_mapped():
    response = client.get("/api/v1/behavior/design-similarity/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["chart_evidence_ready"] is True
    overlays = report["overlay_evidence"]
    assert overlays
    assert {item["overlay_type"] for item in overlays}.issuperset({"shape_path", "trendline", "harmonic_anchor", "fib_zone", "analog_ghost_path"})
    assert all(item["points"] and item["tooltip"] and item["pane"] == "price" for item in overlays)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V076-003"]["passed"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Design Similarity Shape Grammar")
    assert feature["status"] == "mock"
    assert "DesignSimilarityReport" in feature["required_data_contracts"]
    assert "TV-FI-093" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["design_similarity_v076"]
    assert panel["contract_name"] == "DesignSimilarityReport"
    assert panel["endpoint"] == "/api/v1/behavior/design-similarity/current"
    assert panel["manifest_status"] == "mock"


def test_v077_band_level_distance_emits_required_distance_fields():
    response = client.get("/api/v1/behavior/bands/distances")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["distance_version"] == "band-level-distance-value-cluster.v0.77"
    assert report["all_required_distance_fields_present"] is True
    assert report["all_available_levels_point_in_time_safe"] is True
    required = set(report["required_distance_fields"])
    fields = {record["field_name"] for record in report["distance_records"]}
    assert required.issubset(fields)
    for field in [
        "distance_to_vwap_band_1",
        "distance_to_vwap_band_2",
        "distance_to_vwap_band_3",
        "distance_to_bb_upper_3",
        "distance_to_bb_lower_3",
        "distance_to_pivot_resistance",
        "distance_to_cpr_top",
        "distance_to_fib_level",
        "distance_to_harmonic_completion_zone",
        "distance_to_trendline",
        "distance_to_orb_high",
        "distance_to_vpd_poc",
        "distance_to_value_area_high",
        "distance_to_value_area_low",
    ]:
        assert field in fields
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V077-001"]["passed"] is True
    assert gates["TV-V077-004"]["passed"] is True


def test_v077_repeated_value_clusters_include_samples_intervals_and_outcomes():
    response = client.post(
        "/api/v1/behavior/value-clusters/discover",
        json={"symbol": "RELIANCE", "timeframe": "3m", "seed": 7701, "minimum_cluster_sample_count": 30},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    clusters = report["repeated_value_clusters"]
    assert clusters
    assert report["minimum_cluster_sample_pass"] is True
    for cluster in clusters:
        assert cluster["sample_count"] >= cluster["independent_sample_count"] >= 30
        assert len(cluster["confidence_interval"]) == 2
        assert cluster["outcome_distribution"]
        assert cluster["matched_fields"]
        assert cluster["evidence_quality"] in {"MEDIUM", "STRONG"}
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V077-002"]["passed"] is True
    assert gates["TV-FI-047"]["passed"] is True
    assert gates["TV-FI-077"]["passed"] is True


def test_v077_missing_or_unconfirmed_levels_are_explicit_not_zero():
    response = client.get("/api/v1/behavior/bands/distances")
    assert response.status_code == 200
    report = response.json()["data"]
    missing = report["missing_levels"]
    assert missing
    assert report["unavailable_levels_not_silently_drawn"] is True
    unavailable_records = [record for record in report["distance_records"] if record["availability"] != "available"]
    assert unavailable_records
    for record in unavailable_records:
        assert record["side"] == "unavailable"
        assert record["level_value"] is None
        assert record["distance_points"] is None
        assert record["unavailable_reason"]
    assert any(item["availability"] == "not_confirmed" for item in missing)
    assert any(item["fallback_behavior"] in {"exclude_from_similarity", "reduce_coverage"} for item in missing)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-FI-043"]["passed"] is True
    assert gates["TV-FI-054"]["passed"] is True


def test_v077_level_distance_influences_outcomes_and_is_manifested():
    response = client.post(
        "/api/v1/behavior/value-clusters/discover",
        json={"symbol": "INFY", "timeframe": "5m", "seed": 7702, "decision_price": 1480.0, "atr": 12.5},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["level_distance_influences_outcomes"] is True
    influences = report["outcome_influences"]
    assert influences
    assert any(item["blocks_confidence"] is True for item in influences)
    assert any("fakeout" in item["interpretation"].lower() or "continuation" in item["interpretation"].lower() for item in influences)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V077-003"]["passed"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Band Level Distance Memory")
    assert feature["status"] == "mock"
    assert "BandLevelDistanceReport" in feature["required_data_contracts"]
    assert "TV-FI-077" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["band_level_distance_v077"]
    assert panel["contract_name"] == "BandLevelDistanceReport"
    assert panel["endpoint"] == "/api/v1/behavior/bands/distances"
    assert panel["manifest_status"] == "mock"


def test_v078_pattern_by_timeframe_covers_all_required_timeframes():
    response = client.get("/api/v1/behavior/patterns/by-timeframe")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["pattern_timeframe_version"] == "pattern-by-timeframe-outcomes.v0.78"
    assert set(report["timeframes"]) == {"1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"}
    assert report["all_timeframes_covered"] is True
    assert report["all_records_point_in_time_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    outcome_timeframes = {record["timeframe"] for record in report["pattern_outcomes"]}
    assert set(report["timeframes"]).issubset(outcome_timeframes)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V078-001"]["passed"] is True
    assert gates["TV-V078-002"]["passed"] is True


def test_v078_timeframe_specific_failure_reasons_and_evidence_guard():
    response = client.post(
        "/api/v1/behavior/patterns/by-timeframe/analyze",
        json={"symbol": "RELIANCE", "primary_timeframe": "3m", "seed": 7801, "minimum_sample_size": 30},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["timeframe_specific_failures_present"] is True
    assert report["minimum_evidence_guard_active"] is True
    assert {record["timeframe"] for record in report["failure_reasons"]} == set(report["timeframes"])
    assert all(record["top_failure_reasons"] for record in report["pattern_outcomes"])
    assert any(record["minimum_sample_pass"] is False for record in report["pattern_outcomes"])
    assert any(record["evidence_quality"] == "LOW_EVIDENCE" for record in report["pattern_outcomes"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V078-003"]["passed"] is True
    assert gates["TV-FI-081"]["passed"] is True


def test_v078_higher_timeframe_interactions_reduce_pattern_trust():
    response = client.post(
        "/api/v1/behavior/patterns/by-timeframe/analyze",
        json={"symbol": "INFY", "primary_timeframe": "5m", "seed": 7802, "include_higher_timeframe_interactions": True},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["higher_timeframe_interactions_present"] is True
    assert report["timeframe_conflict_reduces_trust"] is True
    interactions = report["htf_interactions"]
    assert any(item["interaction_type"] == "htf_resistance_rejection" for item in interactions)
    assert any(item["interaction_type"] == "timeframe_conflict" for item in interactions)
    assert any(item["blocks_confidence"] is True for item in interactions)
    assert any(
        item["conflict_adjusted_trust_score"] < item["base_trust_score"]
        for item in report["trust_impacts"]
    )
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V078-004"]["passed"] is True
    assert gates["TV-V078-005"]["passed"] is True
    assert gates["TV-V078-006"]["passed"] is True


def test_v078_pattern_by_timeframe_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Pattern By Timeframe Outcome Memory")
    assert feature["status"] == "mock"
    assert "PatternByTimeframeReport" in feature["required_data_contracts"]
    assert "TV-V078-005" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["pattern_by_timeframe_v078"]
    assert panel["contract_name"] == "PatternByTimeframeReport"
    assert panel["endpoint"] == "/api/v1/behavior/patterns/by-timeframe"
    assert panel["manifest_status"] == "mock"


def test_v079_market_calendar_event_regime_flags_required_classes():
    response = client.get("/api/v1/behavior/calendar/event-regime/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["calendar_regime_version"] == "market-calendar-event-regime-memory.v0.79"
    classes = {flag["event_class"] for flag in report["event_flags"]}
    assert {
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
    }.issubset(classes)
    assert report["all_events_point_in_time_known"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V079-001"]["passed"] is True
    assert gates["TV-V079-005"]["passed"] is True


def test_v079_calendar_specific_reliability_and_minimum_event_guard():
    response = client.post(
        "/api/v1/behavior/calendar/event-regime/analyze",
        json={"symbol": "RELIANCE", "trading_date": "2024-06-20", "seed": 7901, "minimum_event_sample_size": 30},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert "weekly_expiry" in report["active_event_classes"]
    assert "rbi_day" in report["active_event_classes"]
    assert report["calendar_specific_reliability_present"] is True
    assert report["minimum_event_evidence_guard_active"] is True
    rows = report["pattern_reliability"]
    assert rows
    assert any(row["event_class"] == "weekly_expiry" for row in rows)
    assert any(row["minimum_sample_pass"] is False for row in rows)
    assert all(row["pattern_family"] for row in rows)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V079-002"]["passed"] is True
    assert gates["TV-V079-006"]["passed"] is True


def test_v079_event_day_safety_rules_reduce_or_block_confidence():
    response = client.post(
        "/api/v1/behavior/calendar/event-regime/analyze",
        json={"symbol": "INFY", "trading_date": "2024-06-20", "gap_type": "gap_up_failure_watch", "seed": 7902},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["event_day_gates_present"] is True
    assert report["no_trade_or_reduced_confidence_gate_active"] is True
    triggered = [rule for rule in report["safety_rules"] if rule["triggered"]]
    assert triggered
    assert any(rule["action"] in {"reduce_confidence", "force_wait", "force_no_trade"} for rule in triggered)
    assert any("macro event" in rule["reason"].lower() or "expiry" in rule["reason"].lower() for rule in triggered)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V079-003"]["passed"] is True
    assert gates["TV-V079-007"]["passed"] is True


def test_v079_calendar_links_session_gap_timeframe_and_is_manifested():
    response = client.post(
        "/api/v1/behavior/calendar/event-regime/analyze",
        json={"symbol": "NIFTY-MOCK", "trading_date": "2024-06-20", "primary_timeframe": "15m", "seed": 7903},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["connected_to_session_gap_and_timeframe_memory"] is True
    link_sources = {link["source_context"] for link in report["context_links"]}
    assert {"session_rhythm", "gap_context", "pattern_by_timeframe"}.issubset(link_sources)
    assert any(link["blocks_confidence"] is True for link in report["context_links"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V079-004"]["passed"] is True
    assert gates["TV-FI-035"]["passed"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Market Calendar Event Regime Memory")
    assert feature["status"] == "mock"
    assert "MarketCalendarEventRegimeReport" in feature["required_data_contracts"]
    assert "TV-V079-003" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["market_calendar_event_regime_v079"]
    assert panel["contract_name"] == "MarketCalendarEventRegimeReport"
    assert panel["endpoint"] == "/api/v1/behavior/calendar/event-regime/current"
    assert panel["manifest_status"] == "mock"


def test_v080_cross_market_influence_source_registry_and_safety():
    response = client.get("/api/v1/behavior/cross-market/influence/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["cross_market_version"] == "cross-market-influence-memory.v0.80"
    market_ids = {signal["market_id"] for signal in report["signals"]}
    assert {
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
    }.issubset(market_ids)
    assert report["all_available_context_point_in_time_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V080-001"]["passed"] is True
    assert gates["TV-V080-005"]["passed"] is True


def test_v080_missing_cross_market_context_reduces_coverage_not_neutral():
    response = client.post(
        "/api/v1/behavior/cross-market/influence/analyze",
        json={"symbol": "RELIANCE", "seed": 8001, "require_cross_market_context": False},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["context_coverage_pct"] < 100
    assert report["missing_context_reduces_coverage"] is True
    assert report["cross_market_not_silently_neutral"] is True
    missing_rows = [row for row in report["coverage"] if row["available"] is False]
    assert missing_rows
    assert all(row["fallback_behavior"] == "reduce_coverage" for row in missing_rows)
    assert all(row["coverage_penalty_pct"] > 0 for row in missing_rows)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V080-002"]["passed"] is True
    assert gates["TV-FI-042"]["passed"] is True
    assert gates["TV-FI-089"]["passed"] is True


def test_v080_cross_market_influences_gap_opening_fakeout_and_continuation():
    response = client.post(
        "/api/v1/behavior/cross-market/influence/analyze",
        json={"symbol": "INFY", "seed": 8002, "session_phase": "09:15-09:30_open_drive"},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["influence_on_gap_opening_fakeout_continuation_present"] is True
    affected = {row["affected_behavior"] for row in report["session_influences"]}
    assert {"gap", "opening_drive", "fakeout", "continuation"}.issubset(affected)
    assert any(row["effect_direction"] in {"supports_long", "increases_fakeout", "increases_range"} for row in report["session_influences"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V080-003"]["passed"] is True


def test_v080_conflicted_global_context_gates_confidence_and_is_manifested():
    response = client.post(
        "/api/v1/behavior/cross-market/influence/analyze",
        json={"symbol": "NIFTY-MOCK", "seed": 8003, "direction": "long", "require_cross_market_context": True},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["no_trade_or_confidence_gate_active"] is True
    assert any(conflict["conflict_type"] == "global_risk_off_vs_local_long" for conflict in report["conflicts"])
    assert any(conflict["conflict_type"] == "missing_context" and conflict["blocks_confidence"] is True for conflict in report["conflicts"])
    assert any(row["fallback_behavior"] == "force_wait_if_required" for row in report["coverage"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V080-004"]["passed"] is True
    assert gates["TV-V080-006"]["passed"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Cross-Market Influence Memory")
    assert feature["status"] == "mock"
    assert "CrossMarketInfluenceReport" in feature["required_data_contracts"]
    assert "TV-FI-089" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["cross_market_influence_v080"]
    assert panel["contract_name"] == "CrossMarketInfluenceReport"
    assert panel["endpoint"] == "/api/v1/behavior/cross-market/influence/current"
    assert panel["manifest_status"] == "mock"


def test_v081_corporate_action_filter_detects_contaminated_windows():
    response = client.get("/api/v1/behavior/corporate-abnormal/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["corporate_abnormal_version"] == "corporate-action-abnormal-market-memory.v0.81"
    event_types = {event["event_type"] for event in report["corporate_actions"]}
    assert {"split", "dividend_adjustment", "suspension"}.issubset(event_types)
    assert report["corporate_action_filter_active"] is True
    assert all(event["contaminates_memory_window"] is True for event in report["corporate_actions"])
    assert report["raw_data_preserved_immutable"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V081-001"]["passed"] is True
    assert gates["TV-FI-106"]["passed"] is True


def test_v081_abnormal_market_events_block_memory_and_trade_quality():
    response = client.post(
        "/api/v1/behavior/corporate-abnormal/analyze",
        json={"symbol": "RELIANCE", "trading_date": "2024-06-20", "seed": 8101},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    abnormal_types = {event["event_type"] for event in report["abnormal_events"]}
    assert {"upper_circuit_near", "trading_halt", "single_candle_abnormal_print", "illiquid_spike"}.issubset(abnormal_types)
    assert report["abnormal_market_filter_active"] is True
    assert report["memory_update_blocked"] is True
    assert report["no_trade_gate_active"] is True
    assert all(event["blocks_memory_update"] is True for event in report["abnormal_events"])
    assert any(event["severity"] == "blocker" for event in report["abnormal_events"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V081-002"]["passed"] is True
    assert gates["TV-V081-005"]["passed"] is True


def test_v081_contaminated_memory_quarantine_and_trust_reduction():
    response = client.post(
        "/api/v1/behavior/corporate-abnormal/analyze",
        json={"symbol": "INFY", "trading_date": "2024-06-20", "seed": 8102, "quarantine_window_days": 12},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["contaminated_memory_quarantined"] is True
    assert report["trust_reduced_for_contaminated_analogs"] is True
    assert report["clean_sample_count"] >= 0
    assert any(record["quarantine_required"] is True for record in report["contamination_records"])
    assert any(record["trust_adjustment_pct"] < 0 for record in report["contamination_records"])
    actions = {action["action"]: action for action in report["quarantine_actions"]}
    assert actions["exclude_from_similarity"]["triggered"] is True
    assert actions["quarantine_warm_memory"]["triggered"] is True
    assert actions["trigger_rebuild_plan"]["triggered"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V081-003"]["passed"] is True
    assert gates["TV-V081-004"]["passed"] is True
    assert gates["TV-FI-053"]["passed"] is True


def test_v081_corporate_abnormal_manifested_and_panel_mapped():
    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Corporate Action Abnormal Market Memory")
    assert feature["status"] == "mock"
    assert "CorporateActionAbnormalMarketReport" in feature["required_data_contracts"]
    assert "TV-FI-106" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["corporate_abnormal_memory_v081"]
    assert panel["contract_name"] == "CorporateActionAbnormalMarketReport"
    assert panel["endpoint"] == "/api/v1/behavior/corporate-abnormal/current"
    assert panel["manifest_status"] == "mock"


def test_v082_position_sizing_is_account_risk_based_and_research_only():
    response = client.get("/api/v1/behavior/risk/portfolio-cooldown/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["risk_memory_version"] == "position-portfolio-cooldown-memory.v0.82"
    sizing = report["sizing"]
    assert sizing["raw_position_size"] >= sizing["final_position_size"] >= 0
    assert sizing["capital_cap_position_size"] >= sizing["final_position_size"]
    assert sizing["risk_reward"] >= 0
    assert report["account_risk_sizing_present"] is True
    assert report["research_only_sizing_estimate"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V082-001"]["passed"] is True
    assert gates["TV-V082-005"]["passed"] is True


def test_v082_exposure_caps_and_portfolio_heat_block_risk():
    response = client.post(
        "/api/v1/behavior/risk/portfolio-cooldown/analyze",
        json={
            "symbol": "RELIANCE",
            "current_sector_exposure_pct": 26,
            "current_index_exposure_pct": 38,
            "correlation_cluster_exposure_pct": 35,
            "max_portfolio_heat_pct": 6,
            "seed": 8201,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["exposure_caps_active"] is True
    assert report["portfolio_heat"]["blocks_trade"] is True
    failed_caps = [cap for cap in report["exposure_caps"] if cap["pass_cap"] is False]
    assert failed_caps
    assert any(cap["cap_type"] == "sector" for cap in failed_caps)
    assert any(cap["cap_type"] == "correlation_cluster" for cap in failed_caps)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V082-002"]["passed"] is True
    assert gates["TV-BI-037"]["passed"] is True


def test_v082_daily_weekly_loss_and_cooldown_gates_are_explicit():
    response = client.post(
        "/api/v1/behavior/risk/portfolio-cooldown/analyze",
        json={
            "symbol": "INFY",
            "daily_pnl": -25000,
            "weekly_pnl": -60000,
            "consecutive_losses": 4,
            "choppy_regime": True,
            "seed": 8202,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    cooldown = report["cooldown"]
    assert report["daily_weekly_loss_gates_active"] is True
    assert report["cooldown_gate_active"] is True
    assert cooldown["daily_loss_limit_hit"] is True
    assert cooldown["weekly_loss_limit_hit"] is True
    assert cooldown["cooldown_active"] is True
    assert cooldown["cooldown_minutes"] > 0
    assert any("Daily loss" in reason or "Weekly loss" in reason for reason in cooldown["reasons"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V082-003"]["passed"] is True
    assert gates["TV-V082-004"]["passed"] is True
    assert gates["TV-BI-036"]["passed"] is True


def test_v082_position_portfolio_cooldown_manifested_and_panel_mapped():
    response = client.post(
        "/api/v1/behavior/risk/portfolio-cooldown/analyze",
        json={"symbol": "NIFTY-MOCK", "decision": "BUY_BREAKOUT", "seed": 8203},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["no_live_route_attempted"] is True
    assert all(scenario["trade_allowed"] is False for scenario in report["scenarios"])
    assert any(scenario["next_safe_action"] in {"NO_TRADE", "WAIT", "RESEARCH_ONLY"} for scenario in report["scenarios"])

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Position Portfolio Cooldown Memory")
    assert feature["status"] == "mock"
    assert "PositionPortfolioCooldownReport" in feature["required_data_contracts"]
    assert "TV-V082-005" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["position_portfolio_cooldown_v082"]
    assert panel["contract_name"] == "PositionPortfolioCooldownReport"
    assert panel["endpoint"] == "/api/v1/behavior/risk/portfolio-cooldown/current"
    assert panel["manifest_status"] == "mock"


def test_v083_execution_intent_lifecycle_blocks_live_route():
    response = client.get("/api/v1/behavior/execution-intent/paper-safety/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["paper_safety_version"] == "execution-intent-paper-safety-memory.v0.83"
    assert report["intent_lifecycle_present"] is True
    assert report["intent_lifecycle"]["current_state"] == "MANUAL_REVIEW_REQUIRED"
    assert report["intent_lifecycle"]["manual_review_required"] is True
    assert report["broker_credentials_present"] is False
    assert report["broker_order_created"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["trade_allowed"] is False
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V083-001"]["passed"] is True
    assert gates["TV-FI-110"]["passed"] is True


def test_v083_all_paper_estimates_are_labeled_simulation_estimate():
    response = client.post(
        "/api/v1/behavior/execution-intent/paper-safety/analyze",
        json={"symbol": "RELIANCE", "seed": 8301},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["all_execution_outputs_labeled_simulation_estimate"] is True
    assert report["paper_estimates"]
    for estimate in report["paper_estimates"]:
        assert estimate["estimate_label"] == "SIMULATION_ESTIMATE"
        assert estimate["paper_only"] is True
        assert estimate["simulation"]["simulation_only"] is True
        assert estimate["simulation"]["live_route_attempted"] is False
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V083-002"]["passed"] is True
    assert gates["TV-FI-109"]["passed"] is True


def test_v083_no_fill_partial_fill_and_cost_memory_present():
    response = client.post(
        "/api/v1/behavior/execution-intent/paper-safety/analyze",
        json={
            "symbol": "INFY",
            "requested_quantity": 1500,
            "available_volume": 25_000,
            "bid_ask_spread_pct": 0.12,
            "latency_ms": 260,
            "adverse_selection_score": 0.62,
            "seed": 8302,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    statuses = {estimate["simulation"]["fill_status"] for estimate in report["paper_estimates"]}
    assert {"NO_FILL", "PARTIAL_FILL"} <= statuses
    assert report["no_fill_partial_fill_cost_memory_present"] is True
    assert any(estimate["simulation"]["costs"]["total_cost_pct"] > 0 for estimate in report["paper_estimates"])
    assert all(estimate["no_fill_counted_as_win"] is False for estimate in report["paper_estimates"])
    assert any(estimate["slippage_latency_impact_present"] is True for estimate in report["paper_estimates"])
    assert any(estimate["adverse_selection_present"] is True for estimate in report["paper_estimates"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V083-003"]["passed"] is True
    assert gates["TV-FI-019"]["passed"] is True
    assert gates["TV-FI-020"]["passed"] is True


def test_v083_manual_review_manifested_and_panel_mapped():
    response = client.get("/api/v1/behavior/execution-intent/paper-safety/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["manual_review_required_for_executor_handoff"] is True
    assert report["manual_review"]["review_state"] == "manual_review_required"
    assert "create broker credentials" in report["manual_review"]["forbidden_actions"]
    assert "create broker order" in report["manual_review"]["forbidden_actions"]
    assert "enable live route" in report["manual_review"]["forbidden_actions"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["TV-V083-004"]["passed"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Execution Intent Paper Safety Memory")
    assert feature["status"] == "mock"
    assert "ExecutionIntentPaperSafetyReport" in feature["required_data_contracts"]
    assert "TV-FI-110" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["execution_intent_paper_safety_v083"]
    assert panel["contract_name"] == "ExecutionIntentPaperSafetyReport"
    assert panel["endpoint"] == "/api/v1/behavior/execution-intent/paper-safety/current"
    assert panel["manifest_status"] == "mock"


def test_v084_current_mode_matrix_blocks_external_paper_review():
    response = client.get("/api/v1/behavior/execution-permission/preflight/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["permission_version"] == "paper-executor-permission-matrix.v0.84"
    assert report["requested_mode"] == "MOCK"
    assert report["mode_permission"] == "mock_preview_only"
    assert report["accepted_for_external_paper_review"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    modes = {row["mode"]: row for row in report["permission_matrix"]}
    assert set(modes) == {"MOCK", "SIMULATION", "REPLAY", "PAPER", "LIVE"}
    assert modes["MOCK"]["preview_intent_allowed"] is True
    assert modes["MOCK"]["external_paper_review_allowed"] is False
    assert modes["LIVE"]["live_handoff_allowed"] is False
    gates = {gate["gate_id"]: gate for gate in report["preflight_gates"]}
    assert gates["TV-V084-001"]["passed"] is True
    assert gates["TV-FI-110"]["passed"] is True


def test_v084_paper_mode_missing_approval_and_risk_gates_blocks_preflight():
    response = client.post(
        "/api/v1/behavior/execution-permission/preflight/analyze",
        json={"symbol": "RELIANCE", "requested_mode": "PAPER", "external_human_approval_present": True, "seed": 8401},
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["requested_mode"] == "PAPER"
    assert report["mode_permission"] == "paper_review_blocked"
    assert report["accepted_for_external_paper_review"] is False
    assert report["rejected"] is True
    assert report["human_approval"]["approval_state"] == "single_approval_only"
    assert "Secondary approval is missing." in report["rejection_reasons"]
    assert any("risk_gate_passed=False" == reason for reason in report["rejection_reasons"])
    gates = {gate["gate_id"]: gate for gate in report["preflight_gates"]}
    assert gates["TV-V084-004"]["passed"] is False
    assert gates["TV-V084-005"]["passed"] is False


def test_v084_paper_mode_all_gates_ready_for_external_review_only():
    response = client.post(
        "/api/v1/behavior/execution-permission/preflight/analyze",
        json={
            "symbol": "INFY",
            "requested_mode": "PAPER",
            "external_human_approval_present": True,
            "secondary_approval_present": True,
            "risk_gate_passed": True,
            "replay_determinism_passed": True,
            "paper_validation_passed": True,
            "exchange_reconciliation_ready": True,
            "seed": 8402,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["mode_permission"] == "paper_review_ready"
    assert report["accepted_for_external_paper_review"] is True
    assert report["rejected"] is False
    assert report["human_approval"]["approval_state"] == "dual_approval_recorded"
    assert report["kill_switch_recheck"]["passes_executor_preflight"] is True
    assert all(gate["passed"] is True for gate in report["preflight_gates"])
    paper_row = next(row for row in report["permission_matrix"] if row["mode"] == "PAPER")
    assert paper_row["external_paper_review_allowed"] is True
    assert report["broker_credentials_present"] is False
    assert report["broker_order_created"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v084_live_mode_and_human_veto_are_always_blocked_and_manifested():
    response = client.post(
        "/api/v1/behavior/execution-permission/preflight/analyze",
        json={
            "symbol": "SBIN",
            "requested_mode": "LIVE",
            "kill_switch_state": "triggered",
            "human_veto_active": True,
            "external_human_approval_present": True,
            "secondary_approval_present": True,
            "risk_gate_passed": True,
            "replay_determinism_passed": True,
            "paper_validation_passed": True,
            "exchange_reconciliation_ready": True,
            "seed": 8403,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["mode_permission"] == "live_blocked"
    assert report["accepted_for_external_paper_review"] is False
    assert report["human_approval"]["approval_state"] == "veto_active"
    assert report["kill_switch_recheck"]["passes_executor_preflight"] is False
    assert any("Kill switch is triggered" in reason for reason in report["rejection_reasons"])
    assert any("Human veto is active." == reason for reason in report["rejection_reasons"])
    gates = {gate["gate_id"]: gate for gate in report["preflight_gates"]}
    assert gates["TV-V084-002"]["passed"] is False
    assert gates["TV-V084-003"]["passed"] is False
    assert gates["TV-V084-009"]["passed"] is False

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Paper Executor Permission Matrix")
    assert feature["status"] == "mock"
    assert "PaperExecutorPermissionReport" in feature["required_data_contracts"]
    assert "TV-V084-009" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["paper_executor_permission_v084"]
    assert panel["contract_name"] == "PaperExecutorPermissionReport"
    assert panel["endpoint"] == "/api/v1/behavior/execution-permission/preflight/current"
    assert panel["manifest_status"] == "mock"


def test_v085_handoff_audit_receipt_binds_v083_and_v084_evidence():
    response = client.get("/api/v1/behavior/executor-handoff/audit/current")
    assert response.status_code == 200
    envelope = response.json()["data"]
    assert envelope["audit_version"] == "executor-handoff-audit-envelope.v0.85"
    assert envelope["paper_safety"]["paper_safety_version"] == "execution-intent-paper-safety-memory.v0.83"
    assert envelope["permission_report"]["permission_version"] == "paper-executor-permission-matrix.v0.84"
    bindings = {item["binding_name"]: item for item in envelope["evidence_bindings"]}
    assert set(bindings) == {"paper_safety", "permission_report", "intent"}
    assert bindings["paper_safety"]["contract_name"] == "ExecutionIntentPaperSafetyReport"
    assert bindings["permission_report"]["contract_name"] == "PaperExecutorPermissionReport"
    assert all(len(item["sha256"]) == 64 for item in bindings.values())
    receipt = envelope["receipt"]
    assert receipt["receipt_version"] == "executor-handoff-immutable-receipt.v0.85"
    assert receipt["algorithm"] == "sha256-canonical-json"
    assert receipt["immutable"] is True
    assert len(receipt["canonical_payload_hash"]) == 64
    assert len(receipt["receipt_hash"]) == 64
    assert {"ExecutionIntentPaperSafetyReport", "PaperExecutorPermissionReport", "ExecutorHandoffIntentAuditRecord"} <= set(receipt["bound_contracts"])


def test_v085_preserves_duplicate_key_expiry_and_rejection_reasons():
    response = client.post(
        "/api/v1/behavior/executor-handoff/audit/build",
        json={
            "symbol": "RELIANCE",
            "requested_mode": "PAPER",
            "seen_duplicate_key": True,
            "force_expired": True,
            "external_human_approval_present": True,
            "secondary_approval_present": False,
            "seed": 8501,
        },
    )
    assert response.status_code == 200
    envelope = response.json()["data"]
    intent = envelope["intent"]
    assert len(intent["duplicate_key"]) == 64
    assert intent["duplicate_intent_blocked"] is True
    assert intent["expired"] is True
    assert intent["expiry_enforced"] is True
    assert intent["export_status"] == "blocked_duplicate"
    assert "Duplicate intent key detected." in intent["rejection_reasons"]
    assert "Intent is expired." in intent["rejection_reasons"]
    assert "Secondary approval is missing." in intent["rejection_reasons"]
    assert envelope["duplicate_key_preserved"] is True
    assert envelope["expiry_preserved"] is True
    assert envelope["rejection_reasons_preserved"] is True


def test_v085_paper_ready_receipt_is_audit_only_not_routing_permission():
    response = client.post(
        "/api/v1/behavior/executor-handoff/audit/build",
        json={
            "symbol": "INFY",
            "requested_mode": "PAPER",
            "external_human_approval_present": True,
            "secondary_approval_present": True,
            "risk_gate_passed": True,
            "replay_determinism_passed": True,
            "paper_validation_passed": True,
            "exchange_reconciliation_ready": True,
            "seed": 8502,
        },
    )
    assert response.status_code == 200
    envelope = response.json()["data"]
    assert envelope["permission_report"]["accepted_for_external_paper_review"] is True
    assert envelope["intent"]["export_status"] == "audit_only"
    assert envelope["export_disabled_inside_trade_vision"] is True
    assert envelope["broker_credentials_present"] is False
    assert envelope["broker_order_created"] is False
    assert envelope["trade_allowed"] is False
    assert envelope["order_routing_enabled"] is False
    assert envelope["live_trading_blocked"] is True
    assert envelope["receipt"]["forbidden_fields_absent"] is True


def test_v085_handoff_audit_manifested_and_panel_mapped():
    response = client.get("/api/v1/behavior/executor-handoff/audit/current")
    assert response.status_code == 200
    envelope = response.json()["data"]
    assert envelope["receipt"]["immutable"] is True

    features = client.get("/api/system/features").json()["data"]["capabilities"]
    feature = next(item for item in features if item["name"] == "Behavior Executor Handoff Audit Envelope")
    assert feature["status"] == "mock"
    assert "ExecutorHandoffAuditEnvelope" in feature["required_data_contracts"]
    assert "TV-V085-005" in feature["promotion_gates"]

    panel_map = client.get("/api/v1/behavior/frontend/panel-map").json()["data"]
    panels = {panel["panel_id"]: panel for panel in panel_map["panels"]}
    panel = panels["executor_handoff_audit_v085"]
    assert panel["contract_name"] == "ExecutorHandoffAuditEnvelope"
    assert panel["endpoint"] == "/api/v1/behavior/executor-handoff/audit/current"
    assert panel["manifest_status"] == "mock"


def test_behavior_failure_library_preserves_failure_reasons():
    response = client.get("/api/v1/behavior/stock/INFY/failure-library")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["library_version"] == "behavior-outcome-learning.v0.19"
    assert result["symbol"] == "INFY"
    assert len(result["failures"]) >= 1
    assert result["most_common_failure"] is not None
    assert result["no_trade_lessons"]
    assert {failure["outcome_label"] for failure in result["failures"]} & {
        "SL_HIT",
        "FAKE_BREAKOUT",
        "CHOP_NO_FOLLOWTHROUGH",
    }


def test_behavior_learning_trust_table_calibrates_low_evidence():
    response = client.get("/api/v1/behavior/stock/INFY/trust-table")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["trust_version"] == "behavior-outcome-learning.v0.19"
    assert result["symbol"] == "INFY"
    assert len(result["records"]) >= 1
    assert result["minimum_sample_pass"] is False
    assert result["calibration_status"] == "LOW_EVIDENCE"
    assert 0.0 <= result["aggregate_trust_score"] <= 1.0
    assert any("Low evidence" in note for note in result["notes"])
    assert all(record["sample_count"] < 30 for record in result["records"])


def test_behavior_decision_enforces_universal_agreement_and_no_trade():
    response = client.get("/api/v1/behavior/decision/current?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["decision_version"] == "behavior-decision-engine.v0.20"
    assert result["symbol"] == "INFY"
    assert result["trade_allowed"] is False
    assert result["universal_agreement_pass"] is False
    assert result["final_trade_decision"] in {"NO_TRADE", "WATCH_ONLY", "FAKEOUT_WARNING"}
    assert result["no_trade"]["active"] is True
    assert result["live_trade_route_attempted"] is False
    assert result["reason_tree"]["read_only"] is True
    assert result["reason_tree"]["cannot_execute_orders"] is True
    assert result["reason_tree"]["cannot_override_calibrated_probabilities"] is True
    assert "universal_agreement_rule" in result["reason_tree"]["nodes"]
    assert result["output_updates"]["trade_allowed"] is False
    assert result["output_updates"]["minimum_sample_pass"] is False


def test_behavior_decision_rule_buy_memory_fakeout_becomes_warning_or_no_trade():
    payload = {
        "symbol": "FAKEOUT-BLOCK",
        "rule_signal": "BUY_BREAKOUT",
        "direction": "long",
        "data_quality_score": 0.99,
        "liquidity_score": 0.8,
        "context_bias": "supports_long",
        "context_blocks_trade": False,
        "session_trade_quality_score": 0.7,
        "session_blocks_trade": False,
        "similar_history_continuation_pct": 22.0,
        "similar_history_fakeout_pct": 72.0,
        "pattern_minimum_sample_pass": True,
        "trust_minimum_sample_pass": True,
        "trust_score": 0.7,
        "failure_warning": "Failure memory warns: fake breakout",
        "market_regime_favorable": True,
        "relative_strength_supports": True,
        "risk_reward": 2.4,
        "daily_loss_limit_hit": False,
        "cooldown_active": False,
        "kill_switch_active": False,
        "ood_score": 0.1,
        "drift_score": 0.1,
    }
    response = client.post("/api/v1/behavior/decision/evaluate", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["trade_allowed"] is False
    assert result["final_trade_decision"] == "FAKEOUT_WARNING"
    assert result["no_trade"]["active"] is True
    assert "fakeout" in result["no_trade"]["no_trade_reason"].lower()
    assert result["agreement_checks"]["similar_history_outcome"] is False
    assert any(gate["gate"] == "TRAP_PROBABILITY" and gate["passed"] is False for gate in result["gates"])
    assert "No live route was attempted" in result["reason_tree"]["nodes"]["execution"]


def test_behavior_decision_all_agreement_can_produce_candidate_without_live_route():
    payload = {
        "symbol": "AGREEMENT-PASS",
        "rule_signal": "BUY_RETEST",
        "direction": "long",
        "data_quality_score": 1.0,
        "liquidity_score": 0.9,
        "context_bias": "supports_long",
        "context_blocks_trade": False,
        "session_trade_quality_score": 0.82,
        "session_blocks_trade": False,
        "similar_history_continuation_pct": 68.0,
        "similar_history_fakeout_pct": 18.0,
        "pattern_minimum_sample_pass": True,
        "trust_minimum_sample_pass": True,
        "trust_score": 0.74,
        "failure_warning": None,
        "market_regime_favorable": True,
        "relative_strength_supports": True,
        "risk_reward": 2.8,
        "daily_loss_limit_hit": False,
        "cooldown_active": False,
        "kill_switch_active": False,
        "ood_score": 0.12,
        "drift_score": 0.16,
    }
    response = client.post("/api/v1/behavior/decision/evaluate", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["universal_agreement_pass"] is True
    assert result["trade_allowed"] is True
    assert result["final_trade_decision"] == "BUY_RETEST"
    assert result["live_trade_route_attempted"] is False
    assert result["reason_tree"]["cannot_execute_orders"] is True
    assert result["output_updates"]["final_trade_decision"] == "BUY_RETEST"


def test_behavior_risk_current_blocks_non_trade_decision_and_keeps_size_zero():
    response = client.get("/api/v1/behavior/risk/current?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["risk_version"] == "behavior-risk-engine.v0.21"
    assert result["symbol"] == "INFY"
    assert result["trade_allowed"] is False
    assert result["position_size"] == 0
    assert result["capital_to_use"] == 0.0
    assert result["no_live_route_attempted"] is True
    assert result["block_reasons"]


def test_behavior_risk_sizing_produces_capital_aware_candidate():
    payload = {
        "symbol": "RISK-PASS",
        "decision": "BUY_RETEST",
        "account_equity": 1_000_000.0,
        "entry_price": 100.0,
        "stop_loss": 98.0,
        "target": 106.0,
        "confidence_pct": 74.0,
        "liquidity_score": 0.9,
        "slippage_risk_pct": 0.05,
        "sector": "IT",
        "index": "NIFTY",
        "current_sector_exposure_pct": 1.0,
        "current_index_exposure_pct": 2.0,
        "correlation_risk": "low",
        "daily_pnl": 0.0,
        "consecutive_losses": 0,
        "choppy_regime": False,
        "max_portfolio_heat_pct": 8.0,
    }
    response = client.post("/api/v1/behavior/risk/evaluate", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["trade_allowed"] is True
    assert result["position_size"] > 0
    assert result["risk_reward"] == 3.0
    assert result["risk_per_trade_pct"] <= 0.5
    assert result["capital_to_use"] <= 100_000.0
    assert result["portfolio"]["blocks_trade"] is False
    assert result["daily_loss"]["daily_loss_limit_hit"] is False
    assert result["no_live_route_attempted"] is True


def test_behavior_risk_blocks_daily_loss_cooldown_and_portfolio_heat():
    payload = {
        "symbol": "RISK-BLOCK",
        "decision": "BUY_BREAKOUT",
        "account_equity": 1_000_000.0,
        "entry_price": 100.0,
        "stop_loss": 99.0,
        "target": 103.0,
        "confidence_pct": 80.0,
        "liquidity_score": 0.85,
        "slippage_risk_pct": 0.05,
        "sector": "BANK",
        "index": "BANKNIFTY",
        "current_sector_exposure_pct": 26.0,
        "current_index_exposure_pct": 41.0,
        "correlation_risk": "high",
        "daily_pnl": -21_000.0,
        "consecutive_losses": 3,
        "choppy_regime": True,
    }
    response = client.post("/api/v1/behavior/risk/evaluate", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["trade_allowed"] is False
    assert result["position_size"] == 0
    assert result["daily_loss"]["daily_loss_limit_hit"] is True
    assert result["daily_loss"]["cooldown_active"] is True
    assert result["portfolio"]["blocks_trade"] is True
    assert {"Daily loss limit hit.", "Cooldown active.", "Portfolio exposure gate blocks trade."} <= set(result["block_reasons"])


def test_behavior_execution_current_rejects_when_risk_size_is_zero():
    response = client.get("/api/v1/behavior/execution/current?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["execution_version"] == "behavior-execution-simulator.v0.22"
    assert result["symbol"] == "INFY"
    assert result["fill_status"] == "REJECTED_SIMULATION"
    assert result["requested_quantity"] == 0
    assert result["filled_quantity"] == 0
    assert result["simulation_only"] is True
    assert result["live_route_attempted"] is False
    assert "zero" in result["no_fill_reason"].lower()


def test_behavior_execution_market_order_full_fill_has_cost_breakdown():
    payload = {
        "symbol": "EXEC-FULL",
        "side": "BUY",
        "order_type": "MARKET",
        "requested_quantity": 100,
        "entry_price": 100.0,
        "bar_open": 100.0,
        "bar_high": 101.0,
        "bar_low": 99.8,
        "bar_close": 100.6,
        "bid_ask_spread_pct": 0.06,
        "available_volume": 50_000,
        "queue_ahead_quantity": 100,
        "latency_ms": 80,
        "impact_coefficient_bps": 3.0,
        "adverse_selection_score": 0.2,
        "max_participation_rate": 0.08,
        "mode_confirmation": "MOCK_ONLY",
        "seed": 7,
    }
    response = client.post("/api/v1/behavior/execution/simulate", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["fill_status"] == "FULL_FILL"
    assert result["filled_quantity"] == 100
    assert result["unfilled_quantity"] == 0
    assert result["fill_price"] > payload["entry_price"]
    assert result["costs"]["spread_cost_pct"] > 0
    assert result["costs"]["total_cost_pct"] > 0
    assert result["fill_quality"] in {"excellent", "acceptable", "poor"}
    assert result["simulation_only"] is True
    assert result["live_route_attempted"] is False


def test_behavior_execution_large_market_order_partial_fills():
    payload = {
        "symbol": "EXEC-PARTIAL",
        "side": "BUY",
        "order_type": "MARKET",
        "requested_quantity": 20_000,
        "entry_price": 100.0,
        "bar_open": 100.0,
        "bar_high": 101.2,
        "bar_low": 99.7,
        "bar_close": 101.0,
        "bid_ask_spread_pct": 0.1,
        "available_volume": 40_000,
        "queue_ahead_quantity": 0,
        "latency_ms": 250,
        "impact_coefficient_bps": 8.0,
        "adverse_selection_score": 0.55,
        "max_participation_rate": 0.08,
        "mode_confirmation": "MOCK_ONLY",
        "seed": 8,
    }
    response = client.post("/api/v1/behavior/execution/simulate", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["fill_status"] == "PARTIAL_FILL"
    assert 0 < result["filled_quantity"] < payload["requested_quantity"]
    assert result["unfilled_quantity"] > 0
    assert result["partial_fill_probability_pct"] == 100.0
    assert "Partial fill" in result["missed_trade_reason"]


def test_behavior_execution_limit_order_can_miss_without_touch():
    payload = {
        "symbol": "EXEC-NOFILL",
        "side": "BUY",
        "order_type": "LIMIT",
        "requested_quantity": 500,
        "entry_price": 100.0,
        "limit_price": 98.5,
        "bar_open": 100.0,
        "bar_high": 101.0,
        "bar_low": 99.2,
        "bar_close": 100.6,
        "bid_ask_spread_pct": 0.08,
        "available_volume": 50_000,
        "queue_ahead_quantity": 0,
        "latency_ms": 80,
        "impact_coefficient_bps": 3.0,
        "adverse_selection_score": 0.2,
        "max_participation_rate": 0.08,
        "mode_confirmation": "MOCK_ONLY",
        "seed": 9,
    }
    response = client.post("/api/v1/behavior/execution/simulate", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["fill_status"] == "NO_FILL"
    assert result["filled_quantity"] == 0
    assert result["fill_price"] is None
    assert "not touched" in result["no_fill_reason"]
    assert result["fill_quality"] == "no_fill"


def test_mock_ingest_creates_point_in_time_snapshot_and_feature_versions():
    payload = {"symbol": "PYTEST-MOCK", "seed": 101, "bars": 32}
    response = client.post("/api/data/ingest/mock", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    snapshot = data["snapshot"]

    assert snapshot["symbol"] == "PYTEST-MOCK"
    assert snapshot["source_mode"] == "MOCK"
    assert snapshot["immutable"] is True
    assert snapshot["payload"]["bars"][0]["t"] <= snapshot["payload"]["bars"][-1]["t"]
    assert {feature["name"] for feature in data["feature_versions"]} == {
        "return_mean",
        "realized_volatility",
        "last_close",
        "sample_size",
    }

    loaded = client.get(f"/api/data/snapshots/{snapshot['snapshot_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["payload_hash"] == snapshot["payload_hash"]

    snapshots = client.get("/api/data/snapshots")
    assert snapshots.status_code == 200
    assert snapshot["snapshot_id"] in {item["snapshot_id"] for item in snapshots.json()["data"]}

    registry = client.get("/api/features/registry")
    assert registry.status_code == 200
    assert snapshot["snapshot_id"] in {item["input_snapshot_id"] for item in registry.json()["data"]}


def test_mock_ingest_is_deterministic_for_same_seed_symbol_and_bar_count():
    payload = {"symbol": "PYTEST-DETERMINISTIC", "seed": 202, "bars": 24}
    first = client.post("/api/data/ingest/mock", json=payload).json()["data"]
    second = client.post("/api/data/ingest/mock", json=payload).json()["data"]

    assert first["snapshot"]["snapshot_id"] == second["snapshot"]["snapshot_id"]
    assert first["snapshot"]["payload_hash"] == second["snapshot"]["payload_hash"]
    assert [feature["feature_hash"] for feature in first["feature_versions"]] == [
        feature["feature_hash"] for feature in second["feature_versions"]
    ]


def test_order_path_stub_is_simulation_only_and_accepts_when_armed():
    client.post(
        "/api/system/killswitch/reset",
        json={"actor_id": "pytest", "confirmation": "RESET_MOCK_KILL_SWITCH"},
        headers={"X-TradeVision-Role": "risk_manager"},
    )
    status = client.get("/api/execution/order-path/status")
    assert status.status_code == 200
    guard = status.json()["data"]
    assert guard["live_order_routing_enabled"] is False
    assert guard["broker_credentials_configured"] is False
    assert guard["simulation_only"] is True
    assert guard["accepts_simulated_orders"] is True

    response = client.post(
        "/api/execution/order-path/simulate",
        json={
            "client_order_id": "pytest-order-001",
            "symbol": "NIFTY-MOCK",
            "side": "BUY",
            "quantity": 10,
            "order_type": "MARKET",
            "mode_confirmation": "MOCK_ONLY",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["accepted"] is True
    assert result["decision"] == "SIMULATED_ACCEPTED"
    assert result["live_route_attempted"] is False
    assert result["kill_switch_checked"] is True


def test_kill_switch_blocks_order_path_stub():
    trigger = client.post(
        "/api/system/killswitch/trigger",
        json={"reason": "block order path test", "source": "user_ui", "actor_id": "pytest"},
    )
    assert trigger.status_code == 200

    status = client.get("/api/execution/order-path/status").json()["data"]
    assert status["accepts_simulated_orders"] is False
    assert status["blocks_reason"] == "block order path test"

    response = client.post(
        "/api/execution/order-path/simulate",
        json={
            "client_order_id": "pytest-order-blocked",
            "symbol": "NIFTY-MOCK",
            "side": "SELL",
            "quantity": 5,
            "order_type": "MARKET",
            "mode_confirmation": "MOCK_ONLY",
        },
    )
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "blocked_by_kill_switch"

    reset = client.post(
        "/api/system/killswitch/reset",
        json={"actor_id": "pytest", "confirmation": "RESET_MOCK_KILL_SWITCH"},
        headers={"X-TradeVision-Role": "risk_manager"},
    )
    assert reset.status_code == 200


def test_api_errors_use_normalized_error_envelope():
    missing = client.get("/api/not-real")
    assert missing.status_code == 404
    assert set(missing.json().keys()) == {"error"}
    assert missing.json()["error"]["code"] == "not_found"

    invalid = client.post(
        "/api/execution/order-path/simulate",
        json={
            "client_order_id": "pytest-invalid",
            "symbol": "NIFTY-MOCK",
            "side": "BUY",
            "quantity": 1,
            "order_type": "LIMIT",
            "mode_confirmation": "MOCK_ONLY",
        },
    )
    assert invalid.status_code == 409
    body = invalid.json()
    assert set(body.keys()) == {"error"}
    assert body["error"]["code"] == "rejected_validation"
    assert body["error"]["retryable"] is False


def test_request_validation_errors_use_normalized_error_envelope():
    invalid = client.post("/api/replay/start", json={"scenario_id": "bad", "seed": -1})
    assert invalid.status_code == 422
    assert set(invalid.json().keys()) == {"error"}
    assert invalid.json()["error"]["code"] == "contract_validation_failed"


def test_mock_rbac_boundary_denies_viewer_operator_actions():
    identity = client.get("/api/auth/me", headers={"X-TradeVision-Actor": "viewer_1", "X-TradeVision-Role": "viewer"})
    assert identity.status_code == 200
    assert identity.json()["data"]["role"] == "viewer"
    assert identity.json()["data"]["live_trading_allowed"] is False

    denied_trigger = client.post(
        "/api/system/killswitch/trigger",
        json={"reason": "viewer should not trigger", "source": "user_ui", "actor_id": "viewer_1"},
        headers={"X-TradeVision-Actor": "viewer_1", "X-TradeVision-Role": "viewer"},
    )
    assert denied_trigger.status_code == 403
    assert denied_trigger.json()["error"]["code"] == "rbac_denied"

    denied_order = client.post(
        "/api/execution/order-path/simulate",
        json={
            "client_order_id": "viewer-denied",
            "symbol": "NIFTY-MOCK",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "mode_confirmation": "MOCK_ONLY",
        },
        headers={"X-TradeVision-Actor": "viewer_1", "X-TradeVision-Role": "viewer"},
    )
    assert denied_order.status_code == 403
    assert denied_order.json()["error"]["code"] == "rbac_denied"


def test_workspace_layout_defaults_and_persists_updates():
    response = client.get("/api/layout/replay")
    assert response.status_code == 200
    layout = response.json()["data"]
    assert layout["version"] == 1
    assert layout["workspace_id"] == "replay"
    assert len(layout["panels"]) >= 1
    assert layout["global_settings"]["killSwitchVisible"] is True

    updated = {
        **layout,
        "global_settings": {**layout["global_settings"], "density": "compact"},
        "panels": [
            {**panel, "state": {**panel["state"], "collapsed": panel["id"] == "archive"}}
            for panel in layout["panels"]
        ],
    }
    saved = client.put("/api/layout/replay", json=updated)
    assert saved.status_code == 200
    assert saved.json()["data"]["global_settings"]["density"] == "compact"
    assert any(panel["state"].get("collapsed") is True for panel in saved.json()["data"]["panels"])

    reloaded = client.get("/api/layout/replay")
    assert reloaded.status_code == 200
    assert reloaded.json()["data"]["global_settings"]["density"] == "compact"


def test_workspace_layout_rejects_mismatch_and_unknown_workspace():
    layout = client.get("/api/layout/cockpit").json()["data"]
    mismatch = client.put("/api/layout/replay", json={**layout, "workspace_id": "cockpit"})
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "workspace_layout_mismatch"

    unknown = client.get("/api/layout/unknown")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "workspace_not_found"


def test_audit_integrity_report_is_hash_chained():
    report = client.get("/api/audit/integrity")
    assert report.status_code == 200
    data = report.json()["data"]
    assert data["event_count"] >= 1
    assert data["hashed_event_count"] == data["event_count"]
    assert data["chain_valid"] is True
    assert data["head_hash"] is not None
    assert data["algorithm"] == "sha256-canonical-json"
    assert data["issues"] == []


def test_audit_integrity_survives_concurrent_hash_chain_writes():
    from app.models import AuditEvent, SystemModeValue, now_iso

    prefix = f"audit-concurrent-{uuid4()}"

    def write_event(index: int) -> None:
        storage.save_audit_event(
            AuditEvent(
                event_id=f"{prefix}-{index}",
                timestamp=now_iso(),
                level="info",
                message="concurrent audit chain regression",
                source="test",
                mode=SystemModeValue.MOCK,
            ),
            {"index": index, "prefix": prefix},
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(write_event, range(18)))

    report = client.get("/api/audit/integrity")
    assert report.status_code == 200
    data = report.json()["data"]
    assert data["chain_valid"] is True
    assert data["hashed_event_count"] == data["event_count"]
    assert data["issues"] == []


def test_v043_stock_memory_profile_unifies_memory_and_stays_research_only():
    response = client.get("/api/v1/behavior/stock/INFY/memory-profile/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["memory_profile_version"] == "behavior-stock-memory-profile.v0.43"
    assert report["symbol"] == "INFY"
    assert report["minimum_sample_size"] == 30
    assert report["snapshot_count"] >= 0
    assert report["memory_record_count"] >= 1
    assert report["historical_match_count"] >= 1
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["deterministic"] is True
    assert report["no_future_leakage"] is True
    assert any(gate["gate_id"] == "TV-V043-005" for gate in report["gates"])


def test_kronos_status_is_safe_when_external_repo_or_service_is_absent():
    response = client.get("/api/v1/kronos/status")
    assert response.status_code == 200
    status = response.json()["data"]
    assert status["kronos_version"] == "kronos-research-adapter.v0.46"
    assert status["dependency_isolated"] is True
    assert status["api_imports_heavy_ml"] is False
    assert status["research_only"] is True
    assert status["trade_allowed"] is False
    assert status["order_routing_enabled"] is False
    assert status["live_trading_blocked"] is True


def test_kronos_service_bridge_defaults_to_safe_mock_fallback(monkeypatch):
    monkeypatch.delenv("TRADEVISION_KRONOS_SERVICE_URL", raising=False)
    response = client.get("/api/v1/kronos/service/status")
    assert response.status_code == 200
    status = response.json()["data"]
    assert status["bridge_version"] == "kronos-service-bridge.v0.46"
    assert status["service_configured"] is False
    assert status["fallback_to_mock"] is True
    assert status["api_imports_heavy_ml"] is False
    assert status["trade_allowed"] is False
    assert status["order_routing_enabled"] is False
    assert status["live_trading_blocked"] is True


def test_kronos_model_registry_excludes_large_and_pairs_tokenizers():
    response = client.get("/api/v1/kronos/models")
    assert response.status_code == 200
    models = {item["model_name"]: item for item in response.json()["data"]}
    assert models["Kronos-mini"]["tokenizer_name"] == "Kronos-Tokenizer-2k"
    assert models["Kronos-small"]["tokenizer_name"] == "Kronos-Tokenizer-base"
    assert models["Kronos-large"]["status"] == "excluded"
    assert models["Kronos-large"]["allowed_for_first_real_adapter"] is False


def test_kronos_mock_forecast_is_deterministic_and_cannot_execute():
    payload = {"symbol": "INFY", "timeframe": "5m", "seed": 77, "lookback_candles": 64, "forecast_horizon_bars": 8}
    first = client.post("/api/v1/kronos/forecast", json=payload)
    second = client.post("/api/v1/kronos/forecast", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    a = first.json()["data"]
    b = second.json()["data"]
    assert a["output_hash"] == b["output_hash"]
    assert a["deterministic"] is True
    assert a["input_validation"]["passed"] is True
    assert a["sanity_check"]["passed"] is True
    assert a["trade_allowed"] is False
    assert a["order_routing_enabled"] is False
    assert a["live_trading_blocked"] is True
    assert a["kronos_cannot_execute_orders"] is True
    assert a["kronos_cannot_override_no_trade"] is True
    assert a["kronos_cannot_override_risk"] is True


def test_kronos_service_bridge_failure_does_not_break_forecast(monkeypatch):
    monkeypatch.setenv("TRADEVISION_KRONOS_SERVICE_URL", "http://127.0.0.1:9")
    payload = {"symbol": "INFY", "timeframe": "5m", "seed": 78, "lookback_candles": 64, "forecast_horizon_bars": 8}
    response = client.post("/api/v1/kronos/forecast", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["forecast_version"] == "kronos-research-adapter.v0.46"
    assert result["deterministic"] is True
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert any("bridge service failure" in note or "bridge timeout" in note for note in result["notes"])


def test_main_api_keeps_kronos_heavy_dependencies_out():
    import app.behavior.kronos_proxy as kronos_proxy

    source = Path(kronos_proxy.__file__).read_text(encoding="utf-8")
    forbidden = ["import torch", "import transformers", "import qlib", "import Kronos", "from Kronos"]
    assert all(item not in source for item in forbidden)


def test_kronos_validate_input_rejects_future_and_invalid_candles():
    base = 1_714_724_800_000_000_000
    bars = [
        {
            "symbol": "INFY",
            "timeframe": "5m",
            "timestamp_ns": base,
            "open": 100.0,
            "high": 99.0,
            "low": 101.0,
            "close": 100.5,
            "volume": 1000,
            "source": "mock",
            "sequence_number": 1,
        },
        {
            "symbol": "INFY",
            "timeframe": "5m",
            "timestamp_ns": base + 300_000_000_000,
            "open": 100.5,
            "high": 101.0,
            "low": 100.0,
            "close": 100.8,
            "volume": 1200,
            "source": "mock",
            "sequence_number": 2,
        },
    ]
    payload = {
        "symbol": "INFY",
        "timeframe": "5m",
        "seed": 1,
        "lookback_candles": 64,
        "forecast_horizon_bars": 8,
        "decision_time_ns": base - 1,
        "series": {"symbol": "INFY", "timeframe": "5m", "bars": bars, "snapshot_id": "bad-kronos", "schema_version": "candles.test"},
    }
    response = client.post("/api/v1/kronos/validate-input", json=payload)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["passed"] is False
    assert result["future_candle_rejected"] is True
    assert result["invalid_ohlc_rejected"] is True
    assert result["incomplete_candle_rejected"] is True
    assert result["blockers"]


def test_twin_current_is_research_only_and_blocks_order_routing():
    response = client.get("/api/v1/twin/current?symbol=INFY")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["twin_version"] == "twin-machine-arbiter.v0.47"
    assert result["symbol"] == "INFY"
    assert result["arbiter_action"] in {"WAIT", "NO_TRADE", "RESEARCH_CANDIDATE"}
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert result["kronos_cannot_execute_orders"] is True
    assert result["kronos_cannot_override_no_trade"] is True
    assert result["kronos_cannot_override_risk"] is True


def test_v047_twin_dashboard_bundles_side_by_side_research_view():
    response = client.get("/api/v1/twin/dashboard/current?symbol=INFY")
    assert response.status_code == 200
    dashboard = response.json()["data"]
    assert dashboard["dashboard_version"] == "twin-machine-arbiter.v0.47.dashboard"
    assert dashboard["symbol"] == "INFY"
    assert dashboard["comparison"]["twin_version"] == "twin-machine-arbiter.v0.47"
    assert dashboard["forecast_path_points"]
    assert set(dashboard["forecast_fan"]) == {"lower", "median", "upper"}
    assert dashboard["ghost_path_summary"]["direction"] in {"LONG", "SHORT", "SIDEWAYS", "UNKNOWN"}
    assert dashboard["safety_gate_matrix"]
    assert dashboard["reliability_leaderboard"]
    assert dashboard["openalgo_intent_preview"]["broker_order_created"] is False
    assert dashboard["openalgo_intent_preview"]["order_routing_enabled"] is False
    assert dashboard["trade_allowed"] is False
    assert dashboard["order_routing_enabled"] is False
    assert dashboard["live_trading_blocked"] is True
    assert len(dashboard["dashboard_hash"]) == 64


def test_behavior_capability_manifest_includes_kronos_twin_and_openalgo_slots():
    response = client.get("/api/v1/behavior/capability-manifest")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["data"]["capabilities"]}
    assert "Behavior Stock Memory Profile" in names
    assert "Kronos Forecast Engine" in names
    assert "Kronos Microservice" in names
    assert "Twin Machine Arbiter" in names
    assert "OpenAlgo SignalIntent Export" in names


def test_kronos_metrics_and_backtest_are_safe_research_shells():
    metrics = client.get("/api/v1/kronos/metrics")
    assert metrics.status_code == 200
    m = metrics.json()["data"]
    assert m["api_imports_heavy_ml"] is False
    assert m["live_trading_blocked"] is True

    payload = {"symbol": "INFY", "timeframe": "5m", "seed": 11, "scenario_count": 3}
    backtest = client.post("/api/v1/kronos/backtest", json=payload)
    assert backtest.status_code == 200
    data = backtest.json()["data"]
    assert data["deterministic"] is True
    assert data["promotion_allowed"] is False
    assert data["trade_allowed"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True
    assert data["kronos_cannot_execute_orders"] is True


def test_twin_conflicts_reliability_replay_and_tournament_are_safe():
    conflicts = client.get("/api/v1/twin/conflicts?symbol=INFY")
    assert conflicts.status_code == 200
    assert isinstance(conflicts.json()["data"], list)

    reliability = client.get("/api/v1/twin/reliability?symbol=INFY")
    assert reliability.status_code == 200
    rel = reliability.json()["data"]
    assert rel["minimum_sample_pass"] is False
    assert rel["sample_count"] == 0

    replay = client.post("/api/v1/twin/replay", json={"symbol": "INFY", "timeframe": "5m", "seed": 44})
    assert replay.status_code == 200
    replay_data = replay.json()["data"]
    assert replay_data["trade_allowed"] is False
    assert replay_data["order_routing_enabled"] is False
    assert replay_data["live_trading_blocked"] is True

    tournament = client.post("/api/v1/twin/tournament", json={"symbol": "INFY", "timeframe": "5m", "seed": 44, "scenario_count": 3})
    assert tournament.status_code == 200
    tour = tournament.json()["data"]
    assert tour["deterministic"] is True
    assert len(tour["leaderboard"]) == 3
    assert tour["promotion_allowed"] is False
    assert tour["trade_allowed"] is False
    assert tour["order_routing_enabled"] is False
    assert tour["live_trading_blocked"] is True


def test_openalgo_intent_endpoints_create_no_broker_order():
    preview = client.post("/api/v1/openalgo/preview-intent?symbol=INFY")
    assert preview.status_code == 200
    p = preview.json()["data"]
    assert p["export_status"] == "preview_only"
    assert p["intent_version"] == "openalgo-signal-intent.preview.v0.48"
    assert len(p["intent_signature"]) == 64
    assert len(p["duplicate_key"]) == 64
    assert p["duplicate_intent_blocked"] is False
    assert p["expiry_enforced"] is True
    assert p["expired"] is False
    assert p["kill_switch_rechecked"] is True
    assert p["human_veto_required"] is True
    assert p["human_veto_active"] is False
    assert p["mode_permission"] == "mock_preview_only"
    assert p["export_allowed"] is False
    assert p["permission_matrix"]
    assert p["broker_credentials_present"] is False
    assert p["broker_order_created"] is False
    assert p["trade_allowed"] is False
    assert p["order_routing_enabled"] is False
    assert p["live_trading_blocked"] is True

    exported = client.post("/api/v1/openalgo/export-intent?symbol=INFY")
    assert exported.status_code == 200
    e = exported.json()["data"]
    assert e["export_status"] == "pending_for_openalgo"
    assert e["duplicate_key"] == p["duplicate_key"]
    assert e["broker_credentials_present"] is False
    assert e["broker_order_created"] is False

    pending = client.get("/api/v1/openalgo/intents/pending?symbol=INFY")
    assert pending.status_code == 200
    assert pending.json()["data"][0]["broker_order_created"] is False
    assert pending.json()["data"][0]["kill_switch_rechecked"] is True

    cancelled = client.post(f"/api/v1/openalgo/intents/{p['intent_id']}/cancel?symbol=INFY")
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["export_status"] == "cancelled"


def test_v049_openalgo_bot_gate_rejects_unapproved_current_intent():
    response = client.get("/api/v1/openalgo/verify-intent/current?symbol=INFY")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["verifier_version"] == "openalgo-bot-handoff-verifier.v0.49"
    assert report["rejected"] is True
    assert report["accepted_for_external_review"] is False
    assert report["signature_valid"] is True
    assert report["duplicate_detected"] is False
    assert report["expired"] is False
    assert report["external_human_approval_present"] is False
    assert report["external_risk_check_passed"] is False
    assert report["external_account_state_checked"] is False
    assert report["broker_order_created"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert any("External human approval is missing." == reason for reason in report["rejection_reasons"])


def test_v049_openalgo_bot_gate_accepts_only_external_review_when_checks_present():
    preview = client.post("/api/v1/openalgo/preview-intent?symbol=INFY").json()["data"]
    response = client.post(
        "/api/v1/openalgo/verify-intent",
        json={
            "intent": preview,
            "seen_duplicate_keys": [],
            "external_human_approval_present": True,
            "external_risk_check_passed": True,
            "external_account_state_checked": True,
            "target_executor": "openalgo",
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["accepted_for_external_review"] is True
    assert report["rejected"] is False
    assert report["signature_valid"] is True
    assert report["broker_order_created"] is False
    assert report["export_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v049_openalgo_bot_gate_rejects_duplicate_and_tampered_intent():
    preview = client.post("/api/v1/openalgo/preview-intent?symbol=INFY").json()["data"]
    tampered = {**preview, "side": "LONG" if preview["side"] != "LONG" else "SHORT"}
    response = client.post(
        "/api/v1/openalgo/verify-intent",
        json={
            "intent": tampered,
            "seen_duplicate_keys": [preview["duplicate_key"]],
            "external_human_approval_present": True,
            "external_risk_check_passed": True,
            "external_account_state_checked": True,
            "target_executor": "trading_bot",
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["rejected"] is True
    assert report["signature_valid"] is False
    assert report["duplicate_detected"] is True
    assert "Intent signature is invalid." in report["rejection_reasons"]
    assert "Duplicate intent key detected." in report["rejection_reasons"]


def test_v050_openalgo_executor_spec_is_brokerless_contract():
    response = client.get("/api/v1/openalgo/executor/spec")
    assert response.status_code == 200
    spec = response.json()["data"]
    assert spec["spec_version"] == "openalgo-executor-spec.v0.50"
    assert spec["live_trading_blocked"] is True
    assert "broker credentials" in spec["forbidden_inside_trade_vision"]
    assert "order placement" in spec["forbidden_inside_trade_vision"]
    assert "intent signature" in " ".join(spec["handoff_contract"]["external_executor_must_recheck"])


def test_v050_openalgo_executor_dry_run_package_creates_no_order_and_writes_files():
    response = client.post(
        "/api/v1/openalgo/executor/dry-run/export",
        json={
            "symbol": "INFY",
            "target_executor": "openalgo",
            "requested_by": "pytest",
            "include_rejection_examples": True,
            "external_human_approval_present": True,
            "external_risk_check_passed": True,
            "external_account_state_checked": True,
            "retention_days": 7,
        },
    )
    assert response.status_code == 200
    package = response.json()["data"]
    assert package["package_version"] == "openalgo-executor-dry-run-package.v0.50"
    assert package["dry_run_only"] is True
    assert package["verification"]["accepted_for_external_review"] is True
    assert package["broker_credentials_present"] is False
    assert package["broker_order_created"] is False
    assert package["trade_allowed"] is False
    assert package["order_routing_enabled"] is False
    assert package["live_trading_blocked"] is True
    assert len(package["package_sha256"]) == 64
    assert len(package["manifest_sha256"]) == 64
    assert len(package["package_hash"]) == 64
    assert len(package["rejection_examples"]) >= 3
    assert Path(package["package_file_path"]).exists()
    assert Path(package["manifest_file_path"]).exists()
    assert "Verify intent signature" in " ".join(package["executor_required_checks"])


def test_v050_openalgo_executor_dry_run_verifier_recomputes_hashes():
    package = client.get("/api/v1/openalgo/executor/dry-run/current?symbol=INFY").json()["data"]
    response = client.post("/api/v1/openalgo/executor/dry-run/verify", json=package)
    assert response.status_code == 200
    verification = response.json()["data"]
    assert verification["verification_version"] == "openalgo-executor-dry-run-verification.v0.50"
    assert verification["verified"] is True
    assert verification["package_file_exists"] is True
    assert verification["manifest_file_exists"] is True
    assert verification["package_sha256_matches"] is True
    assert verification["manifest_sha256_matches"] is True
    assert verification["broker_order_created"] is False
    assert verification["order_routing_enabled"] is False
    assert verification["live_trading_blocked"] is True


def test_v051_executor_golden_fixture_registry_is_deterministic():
    first = client.get("/api/v1/openalgo/executor/golden-fixtures")
    second = client.get("/api/v1/openalgo/executor/golden-fixtures")
    assert first.status_code == 200
    assert second.status_code == 200
    a = first.json()["data"]
    b = second.json()["data"]
    assert a["registry_version"] == "openalgo-executor-golden-registry.v0.51"
    assert a["fixture_count"] == 4
    assert a["registry_hash"] == b["registry_hash"]
    assert a["fixture_hashes"] == b["fixture_hashes"]
    assert len(a["registry_hash"]) == 64
    assert all(len(value) == 64 for value in a["fixture_hashes"].values())
    assert a["broker_order_created"] is False
    assert a["order_routing_enabled"] is False
    assert a["live_trading_blocked"] is True


def test_v051_executor_golden_fixtures_cover_acceptance_and_rejections():
    registry = client.get("/api/v1/openalgo/executor/golden-fixtures").json()["data"]
    fixtures = {item["scenario"]: item for item in registry["fixtures"]}
    accepted = fixtures["accepted_for_review"]
    assert accepted["package"]["verification"]["accepted_for_external_review"] is True
    assert accepted["package"]["verification"]["rejected"] is False
    assert accepted["expected_rejection_reasons"] == []

    missing = fixtures["missing_external_checks"]
    assert missing["package"]["verification"]["rejected"] is True
    assert missing["package"]["verification"]["rejection_reasons"] == [
        "External human approval is missing.",
        "External risk check is missing or failed.",
        "External account state was not checked.",
    ]

    duplicate = fixtures["duplicate_intent"]
    assert duplicate["package"]["verification"]["duplicate_detected"] is True
    assert duplicate["package"]["verification"]["rejection_reasons"] == ["Duplicate intent key detected."]

    expired = fixtures["expired_intent"]
    assert expired["package"]["verification"]["expired"] is True
    assert expired["package"]["verification"]["rejection_reasons"] == ["Intent is expired."]

    for fixture in registry["fixtures"]:
        package = fixture["package"]
        assert package["dry_run_only"] is True
        assert package["broker_credentials_present"] is False
        assert package["broker_order_created"] is False
        assert package["trade_allowed"] is False
        assert package["order_routing_enabled"] is False
        assert package["live_trading_blocked"] is True
        assert Path(package["package_file_path"]).exists()
        assert Path(package["manifest_file_path"]).exists()


def test_v051_executor_golden_registry_verifies_every_fixture():
    response = client.get("/api/v1/openalgo/executor/golden-fixtures/verify")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["verification_version"] == "openalgo-executor-golden-registry-verification.v0.51"
    assert result["fixture_count"] == 4
    assert result["passed_count"] == 4
    assert result["all_passed"] is True
    assert all(item["passed"] for item in result["verifications"])
    assert all(item["package_hash_matches"] for item in result["verifications"])
    assert all(item["safety_invariants_match"] for item in result["verifications"])
    assert result["broker_order_created"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_v051_executor_golden_fixture_unknown_id_is_controlled_404():
    response = client.get("/api/v1/openalgo/executor/golden-fixtures/not-real")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "executor_golden_fixture_not_found"


def test_v052_reference_executor_adapter_passes_conformance_without_promotion():
    response = client.get("/api/v1/openalgo/executor/conformance/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["conformance_version"] == "openalgo-executor-adapter-conformance.v0.52"
    assert report["adapter_name"] == "trade-vision-reference-adapter"
    assert report["registry_hash_matches"] is True
    assert report["expected_fixture_count"] == 4
    assert report["observed_fixture_count"] == 4
    assert report["passed_count"] == 4
    assert report["all_passed"] is True
    assert report["missing_fixture_ids"] == []
    assert report["unexpected_fixture_ids"] == []
    assert report["duplicate_fixture_ids"] == []
    assert len(report["report_hash"]) == 64
    assert report["promotion_allowed"] is False
    assert report["broker_credentials_present"] is False
    assert report["broker_order_created"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v052_executor_adapter_conformance_rejects_missing_fixture_and_wrong_registry():
    registry = client.get("/api/v1/openalgo/executor/golden-fixtures").json()["data"]
    observed = [
        {
            "fixture_id": fixture["fixture_id"],
            "accepted_for_external_review": fixture["package"]["verification"]["accepted_for_external_review"],
            "rejected": fixture["package"]["verification"]["rejected"],
            "rejection_reasons": fixture["package"]["verification"]["rejection_reasons"],
            "broker_credentials_present": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
        for fixture in registry["fixtures"][:-1]
    ]
    response = client.post(
        "/api/v1/openalgo/executor/conformance/evaluate",
        json={
            "adapter_name": "candidate-openalgo-adapter",
            "adapter_version": "0.1.0",
            "registry_hash": "0" * 64,
            "observed_results": observed,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["all_passed"] is False
    assert report["registry_hash_matches"] is False
    assert report["passed_count"] == 3
    assert report["missing_fixture_ids"] == ["executor-golden-expired-intent"]
    assert report["promotion_allowed"] is False
    assert report["order_routing_enabled"] is False


def test_v052_executor_adapter_conformance_rejects_unsafe_order_flags():
    registry = client.get("/api/v1/openalgo/executor/golden-fixtures").json()["data"]
    observed = []
    for fixture in registry["fixtures"]:
        result = {
            "fixture_id": fixture["fixture_id"],
            "accepted_for_external_review": fixture["package"]["verification"]["accepted_for_external_review"],
            "rejected": fixture["package"]["verification"]["rejected"],
            "rejection_reasons": fixture["package"]["verification"]["rejection_reasons"],
            "broker_credentials_present": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
        if fixture["scenario"] == "accepted_for_review":
            result["broker_order_created"] = True
            result["order_routing_enabled"] = True
            result["live_trading_blocked"] = False
        observed.append(result)
    response = client.post(
        "/api/v1/openalgo/executor/conformance/evaluate",
        json={
            "adapter_name": "unsafe-candidate",
            "adapter_version": "0.1.0",
            "registry_hash": registry["registry_hash"],
            "observed_results": observed,
        },
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["all_passed"] is False
    assert report["passed_count"] == 3
    assert report["broker_order_created"] is True
    assert report["order_routing_enabled"] is True
    failed = next(item for item in report["cases"] if item["fixture_id"] == "executor-golden-accepted-review")
    assert failed["safety_invariants_match"] is False
    assert any("broker credentials, order creation, routing" in issue for issue in failed["issues"])


def _enqueue_v053_transport(adapter_url: str | None, max_attempts: int = 3, package: dict | None = None):
    package = package or client.get("/api/v1/openalgo/executor/dry-run/current?symbol=INFY").json()["data"]
    return client.post(
        "/api/v1/openalgo/transport/enqueue",
        json={
            "package": package,
            "adapter_url": adapter_url,
            "service_identity": "trade-vision-pytest",
            "max_attempts": max_attempts,
        },
    )


def test_v053_transport_enqueue_is_idempotent_and_persistent():
    package = client.get("/api/v1/openalgo/executor/dry-run/current?symbol=INFY").json()["data"]
    first = _enqueue_v053_transport("http://adapter-idempotent.test", package=package)
    second = _enqueue_v053_transport("http://adapter-idempotent.test", package=package)
    assert first.status_code == 200
    assert second.status_code == 200
    a = first.json()["data"]
    b = second.json()["data"]
    assert a["delivery_id"] == b["delivery_id"]
    assert a["idempotency_key"] == b["idempotency_key"]
    assert a["status"] == "pending"
    assert a["automatic_execution_allowed"] is False
    assert a["broker_credentials_present"] is False
    assert a["broker_order_created"] is False
    assert a["order_routing_enabled"] is False
    assert a["live_trading_blocked"] is True

    stored = client.get(f"/api/v1/openalgo/transport/outbox/{a['delivery_id']}")
    assert stored.status_code == 200
    assert stored.json()["data"]["idempotency_key"] == a["idempotency_key"]


def test_v053_transport_missing_configuration_moves_to_manual_review(monkeypatch):
    monkeypatch.delenv("TRADEVISION_OPENALGO_ADAPTER_URL", raising=False)
    monkeypatch.delenv("TRADEVISION_ADAPTER_SHARED_SECRET", raising=False)
    queued = _enqueue_v053_transport(None).json()["data"]
    delivered = client.post(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/deliver")
    assert delivered.status_code == 200
    result = delivered.json()["data"]
    assert result["status"] == "manual_review"
    assert result["error_code"] == "adapter_url_not_configured"
    assert result["retryable"] is False
    assert result["wait_required"] is True
    assert result["promotion_allowed"] is False
    assert result["broker_order_created"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_v053_transport_acknowledges_safe_adapter_response(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "pytest-service-secret")
    openalgo_transport.reset_transport_circuit()

    def safe_http(_method, _url, *, payload, **_kwargs):
        return {
            "acknowledgement_version": "openalgo-adapter-ack.v0.53",
            "delivery_id": payload["delivery_id"],
            "idempotency_key": payload["idempotency_key"],
            "adapter_name": "pytest-openalgo-adapter",
            "adapter_version": "0.1.0",
            "receipt_id": f"receipt-{payload['delivery_id']}",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "accepted_for_external_review": True,
            "duplicate": False,
            "package_hash": payload["package"]["package_hash"],
            "broker_credentials_received": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }

    monkeypatch.setattr(openalgo_transport, "_http_json", safe_http)
    queued = _enqueue_v053_transport("http://adapter-success.test").json()["data"]
    response = client.post(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/deliver")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "acknowledged"
    assert result["attempt_count"] == 1
    assert result["retryable"] is False
    assert result["acknowledgement"]["accepted_for_external_review"] is True
    assert result["acknowledgement"]["broker_order_created"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_v053_transport_timeout_backoff_and_circuit_breaker(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "pytest-service-secret")
    openalgo_transport.reset_transport_circuit()

    def timeout_http(*_args, **_kwargs):
        raise TimeoutError()

    monkeypatch.setattr(openalgo_transport, "_http_json", timeout_http)
    results = []
    for index in range(3):
        queued = _enqueue_v053_transport(f"http://adapter-timeout-{index}.test").json()["data"]
        delivered = client.post(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/deliver")
        results.append(delivered.json()["data"])

    assert results[0]["status"] == "retry_wait"
    assert results[0]["error_code"] == "adapter_timeout"
    assert results[0]["next_attempt_at"] is not None
    assert results[2]["circuit_state"] == "open"

    blocked = _enqueue_v053_transport("http://adapter-circuit-blocked.test").json()["data"]
    blocked_result = client.post(f"/api/v1/openalgo/transport/outbox/{blocked['delivery_id']}/deliver").json()["data"]
    assert blocked_result["status"] == "circuit_open"
    assert blocked_result["attempt_count"] == 0
    assert blocked_result["broker_order_created"] is False
    assert blocked_result["order_routing_enabled"] is False
    openalgo_transport.reset_transport_circuit()


def test_v053_transport_rejects_unsafe_ack_and_invalid_url(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "pytest-service-secret")
    openalgo_transport.reset_transport_circuit()

    def unsafe_http(_method, _url, *, payload, **_kwargs):
        return {
            "acknowledgement_version": "openalgo-adapter-ack.v0.53",
            "delivery_id": payload["delivery_id"],
            "idempotency_key": payload["idempotency_key"],
            "adapter_name": "unsafe-adapter",
            "adapter_version": "0.1.0",
            "receipt_id": "unsafe-receipt",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "accepted_for_external_review": True,
            "duplicate": False,
            "package_hash": payload["package"]["package_hash"],
            "broker_credentials_received": False,
            "broker_order_created": True,
            "order_routing_enabled": True,
            "live_trading_blocked": False,
        }

    monkeypatch.setattr(openalgo_transport, "_http_json", unsafe_http)
    queued = _enqueue_v053_transport("http://adapter-unsafe.test").json()["data"]
    result = client.post(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/deliver").json()["data"]
    assert result["status"] == "retry_wait"
    assert result["error_code"] == "adapter_delivery_failed"
    assert result["acknowledgement"] is None
    assert result["broker_order_created"] is False
    assert result["order_routing_enabled"] is False

    invalid = _enqueue_v053_transport("file:///tmp/not-an-adapter")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_executor_transport_configuration"


def test_v053_transport_status_and_unknown_record_are_safe(monkeypatch):
    monkeypatch.delenv("TRADEVISION_OPENALGO_ADAPTER_URL", raising=False)
    monkeypatch.delenv("TRADEVISION_ADAPTER_SHARED_SECRET", raising=False)
    openalgo_transport.reset_transport_circuit()
    response = client.get("/api/v1/openalgo/transport/status")
    assert response.status_code == 200
    status = response.json()["data"]
    assert status["status_version"] == "openalgo-adapter-transport.v0.53"
    assert status["configured"] is False
    assert status["service_auth_configured"] is False
    assert status["automatic_execution_allowed"] is False
    assert status["broker_credentials_present"] is False
    assert status["broker_order_created"] is False
    assert status["order_routing_enabled"] is False
    assert status["live_trading_blocked"] is True

    missing = client.get("/api/v1/openalgo/transport/outbox/not-real")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "executor_transport_record_not_found"


def test_v055_due_worker_is_rbac_guarded_and_acknowledges_due_records(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "pytest-service-secret")
    openalgo_transport.reset_transport_circuit()

    def safe_http(_method, _url, *, payload, **_kwargs):
        return {
            "acknowledgement_version": "openalgo-adapter-ack.v0.54",
            "delivery_id": payload["delivery_id"],
            "idempotency_key": payload["idempotency_key"],
            "adapter_name": "worker-test-adapter",
            "adapter_version": "0.54.0",
            "receipt_id": f"worker-{payload['delivery_id']}",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "accepted_for_external_review": True,
            "duplicate": False,
            "package_hash": payload["package"]["package_hash"],
            "broker_credentials_received": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }

    monkeypatch.setattr(openalgo_transport, "_http_json", safe_http)
    queued = _enqueue_v053_transport("http://adapter-worker-v055.test").json()["data"]
    denied = client.post(
        "/api/v1/openalgo/transport/worker/run",
        json={"actor_id": "ignored", "concurrency": 2, "limit": 100, "stale_after_seconds": 30},
        headers={"X-TradeVision-Role": "viewer"},
    )
    assert denied.status_code == 403

    response = client.post(
        "/api/v1/openalgo/transport/worker/run",
        json={"actor_id": "ignored", "concurrency": 2, "limit": 100, "stale_after_seconds": 30},
        headers={"X-TradeVision-Role": "operator", "X-TradeVision-Actor": "worker_operator"},
    )
    assert response.status_code == 200
    run = response.json()["data"]
    assert run["worker_version"] == "openalgo-transport-recovery.v0.55"
    assert run["actor_id"] == "worker_operator"
    assert run["processed_count"] >= 1
    assert run["acknowledged_count"] >= 1
    assert run["automatic_execution_allowed"] is False
    assert run["broker_order_created"] is False
    assert run["order_routing_enabled"] is False
    assert run["live_trading_blocked"] is True
    stored = client.get(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}").json()["data"]
    assert stored["status"] == "acknowledged"


def test_v055_exhausted_delivery_moves_to_dead_letter_and_can_be_retried(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "pytest-service-secret")
    openalgo_transport.reset_transport_circuit()

    def timeout_http(*_args, **_kwargs):
        raise TimeoutError()

    monkeypatch.setattr(openalgo_transport, "_http_json", timeout_http)
    queued = _enqueue_v053_transport("http://adapter-dead-letter-v055.test", max_attempts=1).json()["data"]
    failed = client.post(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/deliver").json()["data"]
    assert failed["status"] == "dead_letter"
    assert failed["retryable"] is False
    assert failed["broker_order_created"] is False
    assert failed["order_routing_enabled"] is False

    retry = client.post(
        f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/retry",
        json={"actor_id": "ignored", "reason": "operator reviewed external adapter recovery"},
        headers={"X-TradeVision-Role": "operator", "X-TradeVision-Actor": "retry_operator"},
    )
    assert retry.status_code == 200
    retried = retry.json()["data"]
    assert retried["status"] == "pending"
    assert retried["attempt_count"] == 1
    assert retried["order_routing_enabled"] is False


def test_v055_cancel_requires_risk_role_and_prevents_delivery():
    queued = _enqueue_v053_transport("http://adapter-cancel-v055.test").json()["data"]
    denied = client.post(
        f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/cancel",
        json={"actor_id": "ignored", "reason": "operator attempted cancellation"},
        headers={"X-TradeVision-Role": "operator"},
    )
    assert denied.status_code == 403

    cancelled = client.post(
        f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/cancel",
        json={"actor_id": "ignored", "reason": "risk manager cancelled stale research intent"},
        headers={"X-TradeVision-Role": "risk_manager", "X-TradeVision-Actor": "risk_manager_1"},
    )
    assert cancelled.status_code == 200
    record = cancelled.json()["data"]
    assert record["status"] == "cancelled"
    assert record["next_attempt_at"] is None
    assert record["broker_order_created"] is False
    assert record["order_routing_enabled"] is False

    delivery = client.post(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/deliver").json()["data"]
    assert delivery["status"] == "cancelled"
    assert delivery["attempt_count"] == 0


def test_v055_stale_inflight_is_recovered_and_transport_traces_are_persisted(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "pytest-service-secret")
    openalgo_transport.reset_transport_circuit()

    def safe_http(_method, _url, *, payload, **_kwargs):
        return {
            "acknowledgement_version": "openalgo-adapter-ack.v0.54",
            "delivery_id": payload["delivery_id"],
            "idempotency_key": payload["idempotency_key"],
            "adapter_name": "recovery-adapter",
            "adapter_version": "0.54.0",
            "receipt_id": f"recovered-{payload['delivery_id']}",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "accepted_for_external_review": True,
            "duplicate": False,
            "package_hash": payload["package"]["package_hash"],
            "broker_credentials_received": False,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }

    monkeypatch.setattr(openalgo_transport, "_http_json", safe_http)
    queued = _enqueue_v053_transport("http://adapter-recovery-v055.test").json()["data"]
    record = storage.load_executor_transport_record(queued["delivery_id"])
    assert record is not None
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    storage.save_executor_transport_record(
        record.model_copy(update={"status": "delivering", "updated_at": stale_time, "last_attempt_at": stale_time})
    )

    response = client.post(
        "/api/v1/openalgo/transport/worker/run",
        json={"actor_id": "ignored", "concurrency": 1, "limit": 100, "stale_after_seconds": 30},
        headers={"X-TradeVision-Role": "operator", "X-TradeVision-Actor": "recovery_worker"},
    )
    run = response.json()["data"]
    assert run["recovered_count"] >= 1
    final = client.get(f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}").json()["data"]
    assert final["status"] == "acknowledged"

    traces = client.get(
        f"/api/v1/openalgo/transport/traces?delivery_id={queued['delivery_id']}&limit=20"
    ).json()["data"]
    event_types = {trace["event_type"] for trace in traces}
    assert {"enqueued", "recovered", "delivery_started", "acknowledged"} <= event_types
    assert all(trace["delivery_id"] == queued["delivery_id"] for trace in traces)


def test_v056_fault_harness_is_deterministic_and_covers_all_resilience_failures():
    first = client.post("/api/v1/openalgo/resilience/fault-harness", json={"sample_count": 1000})
    second = client.post("/api/v1/openalgo/resilience/fault-harness", json={"sample_count": 1000})
    assert first.status_code == 200
    assert second.status_code == 200
    a = first.json()["data"]
    b = second.json()["data"]
    assert a["harness_version"] == "openalgo-transport-fault-harness.v0.56"
    assert a["deterministic"] is True
    assert a["scenario_count"] == 6
    assert a["passed_count"] == 6
    assert a["all_passed"] is True
    assert a["scenarios"] == b["scenarios"]
    assert {item["scenario"] for item in a["scenarios"]} == {
        "healthy",
        "latency_breach",
        "availability_breach",
        "backlog_breach",
        "dead_letter",
        "circuit_open",
    }
    assert a["broker_order_created"] is False
    assert a["order_routing_enabled"] is False
    assert a["live_trading_blocked"] is True


def test_v056_metric_evaluation_marks_small_samples_low_evidence():
    objectives, alerts, status = transport_resilience.evaluate_transport_metrics(
        attempts=1,
        successes=1,
        failures=0,
        availability_pct=100.0,
        p95_latency_ms=10.0,
        retry_rate_pct=0.0,
        backlog_count=0,
        dead_letter_count=0,
        circuit_state="closed",
        health_ok=True,
    )
    assert status == "low_evidence"
    assert alerts == []
    assert all(item.status == "low_evidence" for item in objectives[:3])
    assert objectives[3].status == "pass"


def test_v056_health_history_and_incident_acknowledgement_are_persisted(monkeypatch):
    fake_status = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "service_auth_configured": True,
            "health_checked": True,
            "health_ok": False,
            "circuit_state": "open",
        }
    )
    monkeypatch.setattr(transport_resilience, "transport_status", lambda **_kwargs: fake_status)

    denied = client.post(
        "/api/v1/openalgo/resilience/health-sample",
        headers={"X-TradeVision-Role": "viewer"},
    )
    assert denied.status_code == 403

    sampled = client.post(
        "/api/v1/openalgo/resilience/health-sample",
        headers={"X-TradeVision-Role": "operator", "X-TradeVision-Actor": "slo_operator"},
    )
    assert sampled.status_code == 200
    sample = sampled.json()["data"]
    assert sample["health_ok"] is False
    assert sample["circuit_state"] == "open"
    assert sample["order_routing_enabled"] is False

    history = client.get("/api/v1/openalgo/resilience/health-history?limit=10")
    assert history.status_code == 200
    assert any(item["sample_id"] == sample["sample_id"] for item in history.json()["data"])

    report = client.get("/api/v1/openalgo/resilience/current")
    assert report.status_code == 200
    resilience = report.json()["data"]
    assert resilience["resilience_version"] == "openalgo-transport-resilience.v0.56"
    assert resilience["overall_status"] == "critical"
    assert "TRANSPORT_CIRCUIT_OPEN" in {item["code"] for item in resilience["alerts"]}
    assert resilience["incident"]["status"] == "open"
    assert resilience["promotion_allowed"] is False
    assert resilience["broker_order_created"] is False
    assert resilience["order_routing_enabled"] is False
    incident_id = resilience["incident"]["incident_id"]

    ack_denied = client.post(
        f"/api/v1/openalgo/resilience/incidents/{incident_id}/acknowledge",
        json={"actor_id": "ignored", "note": "viewer cannot acknowledge incidents"},
        headers={"X-TradeVision-Role": "viewer"},
    )
    assert ack_denied.status_code == 403

    acknowledged = client.post(
        f"/api/v1/openalgo/resilience/incidents/{incident_id}/acknowledge",
        json={"actor_id": "ignored", "note": "operator investigating adapter health"},
        headers={"X-TradeVision-Role": "operator", "X-TradeVision-Actor": "incident_operator"},
    )
    assert acknowledged.status_code == 200
    incident = acknowledged.json()["data"]
    assert incident["status"] == "acknowledged"
    assert incident["acknowledged_by"] == "incident_operator"
    assert incident["broker_order_created"] is False
    assert incident["order_routing_enabled"] is False

    incidents = client.get("/api/v1/openalgo/resilience/incidents?limit=10").json()["data"]
    assert any(item["incident_id"] == incident_id and item["status"] == "acknowledged" for item in incidents)


def test_v057_disallowed_adapter_host_and_url_credentials_are_rejected():
    disallowed = _enqueue_v053_transport("https://untrusted.example.com")
    assert disallowed.status_code == 422
    assert disallowed.json()["error"]["code"] == "invalid_executor_transport_configuration"

    credentialed = _enqueue_v053_transport("https://user:password@adapter-safe.test")
    assert credentialed.status_code == 422
    assert credentialed.json()["error"]["code"] == "invalid_executor_transport_configuration"


def test_v057_security_posture_and_threat_report_are_brokerless(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "active-security-key")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "previous-security-key")
    posture = client.get("/api/v1/openalgo/security/posture")
    assert posture.status_code == 200
    data = posture.json()["data"]
    assert data["security_version"] == "openalgo-transport-security.v0.57"
    assert data["active_key_configured"] is True
    assert data["previous_key_configured"] is True
    assert data["nonce_replay_protection"] is True
    assert data["timestamp_skew_seconds"] == 30
    assert data["max_request_bytes"] == 2_000_000
    assert data["rate_limit_per_minute"] == 120
    assert data["trace_integrity"]["valid"] is True
    assert data["overall_status"] == "pass"
    assert data["broker_credentials_present"] is False
    assert data["broker_order_created"] is False
    assert data["order_routing_enabled"] is False
    assert data["live_trading_blocked"] is True

    threat = client.get("/api/v1/openalgo/security/threat-report")
    assert threat.status_code == 200
    report = threat.json()["data"]
    assert report["report_version"] == "openalgo-transport-threat-report.v0.57"
    assert report["passed_count"] == 7
    assert report["threat_count"] == 7
    assert report["all_passed"] is True
    assert all(item["blocked"] for item in report["results"])
    assert report["broker_order_created"] is False
    assert report["order_routing_enabled"] is False


def test_v057_trace_integrity_detects_tampering_and_recovers_after_restore():
    queued = _enqueue_v053_transport("http://adapter-trace-v057.test").json()["data"]
    initial = client.get(
        f"/api/v1/openalgo/security/trace-integrity?delivery_id={queued['delivery_id']}"
    ).json()["data"]
    assert initial["trace_count"] >= 1
    assert initial["valid"] is True
    assert initial["verified_count"] == initial["trace_count"]

    with storage.connect() as connection:
        row = connection.execute(
            """
            SELECT trace_id, trace_json FROM executor_transport_traces
            WHERE delivery_id = ? ORDER BY event_time ASC LIMIT 1
            """,
            (queued["delivery_id"],),
        ).fetchone()
        original_json = row["trace_json"]
        tampered = __import__("json").loads(original_json)
        tampered["actor_id"] = "tampered-actor"
        connection.execute(
            "UPDATE executor_transport_traces SET trace_json = ? WHERE trace_id = ?",
            (__import__("json").dumps(tampered), row["trace_id"]),
        )

    detected = client.get(
        f"/api/v1/openalgo/security/trace-integrity?delivery_id={queued['delivery_id']}"
    ).json()["data"]
    assert detected["valid"] is False
    assert any("trace hash mismatch" in issue for issue in detected["issues"])
    assert detected["broker_order_created"] is False
    assert detected["order_routing_enabled"] is False

    with storage.connect() as connection:
        connection.execute(
            "UPDATE executor_transport_traces SET trace_json = ? WHERE trace_id = ?",
            (original_json, row["trace_id"]),
        )
    restored = client.get(
        f"/api/v1/openalgo/security/trace-integrity?delivery_id={queued['delivery_id']}"
    ).json()["data"]
    assert restored["valid"] is True


def test_v057_trace_integrity_window_fetches_omitted_predecessor_before_mismatch():
    queued = _enqueue_v053_transport("http://adapter-trace-window-v057.test").json()["data"]
    cancelled = client.post(
        f"/api/v1/openalgo/transport/outbox/{queued['delivery_id']}/cancel",
        json={"actor_id": "trace-window-risk-manager", "reason": "create a second trace for window verification"},
        headers={"X-TradeVision-Role": "risk_manager", "X-TradeVision-Actor": "trace_window_risk_manager"},
    )
    assert cancelled.status_code == 200

    full = transport_security.verify_trace_integrity(delivery_id=queued["delivery_id"], limit=10)
    windowed = transport_security.verify_trace_integrity(delivery_id=queued["delivery_id"], limit=1)

    assert full.trace_count >= 2
    assert full.valid is True
    assert windowed.trace_count == 1
    assert windowed.verified_count == 1
    assert windowed.valid is True
    assert windowed.issues == []
    assert windowed.broker_order_created is False
    assert windowed.order_routing_enabled is False
    assert windowed.live_trading_blocked is True


def test_v058_configuration_fingerprint_is_stable_and_excludes_secrets(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "never-include-this-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "never-include-this-previous-secret")
    first = deployment_recovery.configuration_fingerprint()
    second = deployment_recovery.configuration_fingerprint()
    assert first.fingerprint_version == "tradevision-deployment-config.v0.58"
    assert first.fingerprint == second.fingerprint
    assert first.secrets_included is False
    serialized = first.model_dump_json()
    assert "never-include-this-active-secret" not in serialized
    assert "never-include-this-previous-secret" not in serialized
    assert first.non_secret_configuration["adapter_active_key_configured"] is True
    assert first.non_secret_configuration["adapter_previous_key_configured"] is True


def test_v058_database_backup_and_isolated_restore_drill_are_rbac_guarded(monkeypatch, tmp_path):
    backup_dir = tmp_path / "backups"
    restore_dir = tmp_path / "restores"
    monkeypatch.setenv("TRADEVISION_BACKUP_DIR", str(backup_dir))
    monkeypatch.setenv("TRADEVISION_RESTORE_DRILL_DIR", str(restore_dir))

    denied = client.post(
        "/api/v1/deployment/database/backup",
        headers={"X-TradeVision-Role": "operator"},
    )
    assert denied.status_code == 403

    backup_response = client.post(
        "/api/v1/deployment/database/backup",
        headers={"X-TradeVision-Role": "risk_manager", "X-TradeVision-Actor": "backup_operator"},
    )
    assert backup_response.status_code == 200
    backup = backup_response.json()["data"]
    assert backup["backup_version"] == "tradevision-sqlite-backup.v0.58"
    assert backup["integrity_check"] == "ok"
    assert backup["size_bytes"] > 0
    assert len(backup["sha256"]) == 64
    assert Path(backup["backup_path"]).exists()
    assert backup["contains_broker_credentials"] is False
    assert backup["live_trading_blocked"] is True

    restore_denied = client.post(
        "/api/v1/deployment/database/restore-drill",
        json=backup,
        headers={"X-TradeVision-Role": "risk_manager"},
    )
    assert restore_denied.status_code == 403

    restored = client.post(
        "/api/v1/deployment/database/restore-drill",
        json=backup,
        headers={"X-TradeVision-Role": "admin", "X-TradeVision-Actor": "restore_admin"},
    )
    assert restored.status_code == 200
    drill = restored.json()["data"]
    assert drill["drill_version"] == "tradevision-restore-drill.v0.58"
    assert drill["backup_sha256_matches"] is True
    assert drill["integrity_check"] == "ok"
    assert drill["source_table_count"] == drill["restored_table_count"]
    assert drill["passed"] is True
    assert drill["production_database_modified"] is False
    assert drill["broker_order_created"] is False
    assert drill["order_routing_enabled"] is False
    assert Path(drill["restore_path"]).exists()
    assert Path(drill["restore_path"]).resolve() != storage.DB_PATH.resolve()


def test_v058_readiness_and_smoke_pass_for_healthy_brokerless_stack(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "deployment-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "deployment-previous-secret")
    monkeypatch.delenv("TRADEVISION_EXPECTED_CONFIG_FINGERPRINT", raising=False)
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    readiness = deployment_recovery.deployment_readiness()
    assert readiness.readiness_version == "tradevision-deployment-readiness.v0.58"
    assert readiness.target == "research_mock_stack"
    assert readiness.fail_count == 0
    assert readiness.warn_count == 1
    assert readiness.ready is True
    assert readiness.live_broker_deployment_allowed is False
    assert readiness.broker_credentials_present is False
    assert readiness.broker_order_created is False
    assert readiness.order_routing_enabled is False
    assert readiness.live_trading_blocked is True

    smoke = deployment_recovery.deployment_smoke()
    assert smoke.smoke_version == "tradevision-deployment-smoke.v0.58"
    assert smoke.all_passed is True
    assert smoke.passed_count == smoke.check_count
    assert smoke.broker_order_created is False
    assert smoke.order_routing_enabled is False


def test_v059_static_safety_scan_is_clean_and_detects_injected_live_order_path(tmp_path):
    clean = final_release_audit.scan_for_unsafe_live_paths()
    assert clean.scan_version == "tradevision-static-safety-scan.v0.59"
    assert clean.scanned_file_count > 0
    assert clean.passed is True
    assert clean.findings == []
    assert clean.broker_credentials_present is False
    assert clean.broker_order_created is False
    assert clean.order_routing_enabled is False
    assert clean.live_trading_blocked is True

    unsafe = tmp_path / "unsafe_adapter.py"
    unsafe.write_text("def route(client):\n    return client.place_order(symbol='TEST')\n", encoding="utf-8")
    detected = final_release_audit.scan_for_unsafe_live_paths(
        roots=[unsafe],
        project_root=tmp_path,
    )
    assert detected.passed is False
    assert len(detected.findings) == 1
    assert detected.findings[0].pattern_id == "direct_place_order_call"
    assert detected.findings[0].line_number == 2


def test_v059_release_manifest_is_stable_complete_and_secret_free():
    first = final_release_audit.build_release_manifest()
    second = final_release_audit.build_release_manifest()
    assert first.manifest_version == "tradevision-release-candidate-manifest.v0.59"
    assert first.release_id == second.release_id
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.artifact_count == len(first.artifacts)
    assert first.artifact_count >= 15
    assert all(item.present for item in first.artifacts if item.required)
    assert all(len(item.sha256) == 64 for item in first.artifacts if item.present)
    assert "apps/api/app/behavior/red_team_final_gate.py" in {item.relative_path for item in first.artifacts}
    assert first.contains_secrets is False
    assert first.contains_broker_credentials is False
    assert first.contains_live_orders is False
    assert first.order_routing_enabled is False
    assert first.live_trading_blocked is True


def test_v059_final_audit_proves_research_scope_and_never_live(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "release-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "release-previous-secret")
    monkeypatch.delenv("TRADEVISION_EXPECTED_CONFIG_FINGERPRINT", raising=False)
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    fake_resilience = transport_resilience.build_resilience_report().model_copy(
        update={"overall_status": "healthy", "alerts": []}
    )
    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: fake_resilience)
    audit = final_release_audit.build_final_release_audit()
    assert audit.audit_version == "tradevision-final-release-audit.v1.68"
    assert audit.target == "research_mock_stack"
    assert audit.fail_count == 0
    assert audit.research_stack_ready is True
    assert audit.production_research_release_candidate is True
    assert audit.live_trading_ready is False
    assert audit.required_capabilities_covered is True
    assert audit.transport_resilience_status == "healthy"
    assert audit.operator_signoff_required is True
    assert audit.operator_signoff_present is False
    assert audit.broker_credentials_present is False
    assert audit.broker_order_created is False
    assert audit.order_routing_enabled is False
    assert audit.live_trading_blocked is True
    assert "brokerless research" in audit.release_scope.lower()
    red_team_gate = next(gate for gate in audit.gates if gate.gate_id == "tv_prod_red_001")
    assert red_team_gate.status == "pass"
    assert red_team_gate.blocks_release is True
    assert "TV-PROD-RED-001" in red_team_gate.evidence


def test_v059_release_export_is_admin_only_and_writes_hashed_manifest(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADEVISION_RELEASE_DIR", str(tmp_path))
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "release-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "release-previous-secret")
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    fake_resilience = transport_resilience.build_resilience_report().model_copy(
        update={"overall_status": "healthy", "alerts": []}
    )
    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: fake_resilience)

    denied = client.post(
        "/api/v1/release/candidate/export",
        headers={"X-TradeVision-Role": "operator"},
    )
    assert denied.status_code == 403

    exported = client.post(
        "/api/v1/release/candidate/export",
        headers={"X-TradeVision-Role": "admin", "X-TradeVision-Actor": "release-admin"},
    )
    assert exported.status_code == 200
    manifest = exported.json()["data"]
    assert manifest["manifest_path"] is not None
    manifest_path = Path(manifest["manifest_path"])
    assert manifest_path.exists()
    assert manifest_path.parent == tmp_path.resolve()
    assert manifest["contains_live_orders"] is False
    assert manifest["order_routing_enabled"] is False
    assert manifest["live_trading_blocked"] is True


def test_v059_critical_transport_resilience_blocks_release(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "release-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "release-previous-secret")
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    critical = transport_resilience.build_resilience_report().model_copy(
        update={"overall_status": "critical"}
    )
    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: critical)
    audit = final_release_audit.build_final_release_audit()
    assert audit.transport_resilience_status == "critical"
    assert audit.research_stack_ready is False
    assert audit.production_research_release_candidate is False
    assert any(
        gate.gate_id == "transport_resilience" and gate.status == "fail" and gate.blocks_release
        for gate in audit.gates
    )


def test_v167_tv_prod_red_001_failure_blocks_final_release(monkeypatch):
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "release-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "release-previous-secret")
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    fake_resilience = transport_resilience.build_resilience_report().model_copy(
        update={"overall_status": "healthy", "alerts": []}
    )
    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: fake_resilience)
    monkeypatch.setattr(
        final_release_audit,
        "build_tv_prod_red_001_report",
        lambda: {
            "red_team_id": "TV-PROD-RED-001",
            "passed": False,
            "release_blocking": True,
            "paper_candidate_allowed": True,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "decision": "WATCH",
            "cache_status": "unsafe_reused",
            "checks": [
                {"check_id": "volatility_ood", "passed": False, "evidence": "volatility_ood did not fire."},
                {"check_id": "paper_candidate_blocked", "passed": False, "evidence": "paper candidate was not blocked."},
            ],
        },
    )
    audit = final_release_audit.build_final_release_audit()
    assert audit.production_research_release_candidate is False
    assert audit.research_stack_ready is False
    red_team_gate = next(gate for gate in audit.gates if gate.gate_id == "tv_prod_red_001")
    assert red_team_gate.status == "fail"
    assert red_team_gate.blocks_release is True
    assert "volatility_ood" in red_team_gate.evidence
    assert "paper_candidate_blocked" in red_team_gate.evidence


def test_v168_final_audit_reuses_readiness_security_and_smoke_evidence(monkeypatch):
    final_release_audit.clear_final_release_audit_cache()
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "release-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "release-previous-secret")
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    fake_resilience = transport_resilience.build_resilience_report().model_copy(
        update={"overall_status": "healthy", "alerts": []}
    )
    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: fake_resilience)
    monkeypatch.setattr(
        final_release_audit,
        "build_tv_prod_red_001_report",
        lambda: {
            "red_team_id": "TV-PROD-RED-001",
            "passed": True,
            "release_blocking": False,
            "paper_candidate_allowed": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "decision": "WAIT",
            "cache_status": "anomalous_snapshot_quarantined",
            "checks": [{"check_id": "paper_candidate_blocked", "passed": True, "evidence": "blocked"}],
        },
    )

    calls = {"security": 0, "readiness": 0, "smoke": 0}
    real_security = final_release_audit.build_security_posture
    real_readiness = final_release_audit.deployment_readiness
    real_smoke = final_release_audit.deployment_smoke

    def counted_security():
        calls["security"] += 1
        return real_security()

    def forbidden_fallback_security():
        raise AssertionError("deployment_readiness must reuse final-audit security evidence")

    def counted_readiness(*, security=None):
        calls["readiness"] += 1
        assert security is not None
        return real_readiness(security=security)

    def counted_smoke(readiness=None):
        calls["smoke"] += 1
        assert readiness is not None
        return real_smoke(readiness=readiness)

    monkeypatch.setattr(final_release_audit, "build_security_posture", counted_security)
    monkeypatch.setattr(deployment_recovery, "build_security_posture", forbidden_fallback_security)
    monkeypatch.setattr(final_release_audit, "deployment_readiness", counted_readiness)
    monkeypatch.setattr(final_release_audit, "deployment_smoke", counted_smoke)

    audit = final_release_audit.build_final_release_audit()
    cached = final_release_audit.build_final_release_audit()

    assert audit.audit_version == "tradevision-final-release-audit.v1.68"
    assert audit.production_research_release_candidate is True
    assert cached.production_research_release_candidate is True
    assert cached is not audit
    assert calls == {"security": 1, "readiness": 1, "smoke": 1}

    monkeypatch.setattr(
        final_release_audit,
        "build_tv_prod_red_001_report",
        lambda: {
            "red_team_id": "TV-PROD-RED-001",
            "passed": False,
            "release_blocking": True,
            "paper_candidate_allowed": True,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "decision": "WATCH",
            "cache_status": "unsafe_reused",
            "checks": [{"check_id": "paper_candidate_blocked", "passed": False, "evidence": "not blocked"}],
        },
    )
    failed = final_release_audit.build_final_release_audit()
    assert failed.production_research_release_candidate is False
    assert calls == {"security": 2, "readiness": 2, "smoke": 2}


def test_v169_release_readiness_evidence_summarizes_release_sources_without_trading(monkeypatch):
    final_release_audit.clear_final_release_audit_cache()
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "release-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "release-previous-secret")
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    fake_resilience = transport_resilience.build_resilience_report().model_copy(
        update={"overall_status": "healthy", "alerts": []}
    )
    monkeypatch.setattr(final_release_audit, "build_resilience_report", lambda: fake_resilience)
    monkeypatch.setattr(
        final_release_audit,
        "build_tv_prod_red_001_report",
        lambda: {
            "red_team_id": "TV-PROD-RED-001",
            "passed": True,
            "release_blocking": False,
            "paper_candidate_allowed": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "decision": "WAIT",
            "cache_status": "anomalous_snapshot_quarantined",
            "checks": [{"check_id": "paper_candidate_blocked", "passed": True, "evidence": "blocked"}],
        },
    )

    response = client.get("/api/v1/release/readiness-evidence")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["evidence_version"] == "tradevision-release-readiness-evidence.v1.69"
    assert report["final_audit_version"] == "tradevision-final-release-audit.v1.68"
    assert report["manifest_version"] == "tradevision-release-candidate-manifest.v0.59"
    assert report["safety_scan_version"] == "tradevision-static-safety-scan.v0.59"
    assert report["evidence_state"] == "research_release_evidence_ready"
    assert report["research_release_candidate"] is True
    assert report["blocking_gate_ids"] == []
    assert report["trade_allowed"] is False
    assert report["can_execute_orders"] is False
    assert report["can_export_to_openalgo"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["final_audit_cache_ttl_seconds"] == final_release_audit.FINAL_AUDIT_CACHE_TTL_SECONDS
    assert {
        "/api/v1/release/final-audit",
        "/api/v1/release/safety-scan",
        "/api/v1/release/candidate/current",
    }.issubset(set(report["evidence_sources"]))
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["REL-EVID-005"]["status"] == "pass"
    assert gates["REL-EVID-006"]["status"] == "warn"
    assert gates["REL-EVID-006"]["blocks_evidence_ready"] is False


def test_v169_release_readiness_evidence_blocks_when_final_audit_blocks_release(monkeypatch):
    from app.behavior.release_readiness_evidence import build_release_readiness_evidence_report

    final_release_audit.clear_final_release_audit_cache()
    monkeypatch.setenv("TRADEVISION_ADAPTER_SHARED_SECRET", "release-active-secret")
    monkeypatch.setenv("TRADEVISION_ADAPTER_PREVIOUS_SECRET", "release-previous-secret")
    fake_transport = openalgo_transport.transport_status(check_health=False).model_copy(
        update={
            "configured": True,
            "health_checked": True,
            "health_ok": True,
            "service_auth_configured": True,
            "circuit_state": "closed",
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    monkeypatch.setattr(deployment_recovery, "transport_status", lambda **_kwargs: fake_transport)
    healthy_audit = final_release_audit.build_final_release_audit(force_refresh=True)
    failed_gate = healthy_audit.gates[0].model_copy(
        update={"status": "fail", "evidence": "forced test failure", "blocks_release": True}
    )
    blocked_audit = healthy_audit.model_copy(
        update={
            "gates": [failed_gate, *healthy_audit.gates[1:]],
            "fail_count": healthy_audit.fail_count + 1,
            "pass_count": max(0, healthy_audit.pass_count - 1),
            "research_stack_ready": False,
            "production_research_release_candidate": False,
        }
    )

    report = build_release_readiness_evidence_report(audit=blocked_audit)
    assert report.evidence_version == "tradevision-release-readiness-evidence.v1.69"
    assert report.evidence_state == "blocked"
    assert report.research_release_candidate is False
    assert "deployment" in report.blocking_gate_ids
    assert "REL-EVID-001" in report.blocking_gate_ids
    assert report.trade_allowed is False
    assert report.order_routing_enabled is False
    assert report.live_trading_blocked is True


def test_v061_seven_timeframe_feature_runtime_builds_closed_bar_contracts():
    response = client.get("/api/v1/behavior/features/seven-timeframe/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["runtime_version"] == "behavior-timeframe-feature-runtime.v1.82"
    assert report["source_timeframe"] == "1m"
    assert report["required_timeframes"] == ["1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"]
    assert report["source_bar_count"] == 1950
    assert len(report["source_snapshot_hash"]) == 64
    assert report["total_registered_output_groups"] == 94
    assert report["total_timeframe_indicator_slots"] == 94 * 9
    assert report["closed_bar_guard_passed"] is True
    assert report["all_required_timeframes_present"] is True
    assert report["higher_timeframes_closed_before_decision"] is True
    assert report["registry_version"] == "behavior-indicator-registry-lock.v0.60"
    assert report["source_snapshot_shared_with_kronos"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert all(gate["passed"] for gate in report["gates"])

    by_timeframe = {record["timeframe"]: record for record in report["closed_bar_records"]}
    assert by_timeframe["1m"]["closed_bars"] == 1950
    assert by_timeframe["3m"]["closed_bars"] == 650
    assert by_timeframe["5m"]["closed_bars"] == 390
    assert by_timeframe["15m"]["closed_bars"] == 130
    assert by_timeframe["30m"]["closed_bars"] == 65
    assert by_timeframe["1H"]["closed_bars"] == 32
    assert by_timeframe["4H"]["closed_bars"] == 8
    assert by_timeframe["daily"]["closed_bars"] == 5
    assert by_timeframe["weekly"]["closed_bars"] == 1
    assert all(record["closed_before_decision"] is True for record in report["closed_bar_records"])
    assert all(len(record["row_hash"]) == 64 for record in report["closed_bar_records"])

    coverage_by_timeframe = {item["timeframe"]: item for item in report["indicator_coverage"]}
    assert len(coverage_by_timeframe) == 9
    assert coverage_by_timeframe["1m"]["registered_output_groups"] == 94
    assert coverage_by_timeframe["1m"]["probability_enabled_groups"] == 0
    assert coverage_by_timeframe["30m"]["registered_output_groups"] == 94
    assert coverage_by_timeframe["4H"]["registered_output_groups"] == 94
    assert coverage_by_timeframe["weekly"]["registered_output_groups"] == 94
    assert coverage_by_timeframe["weekly"]["blocked_output_groups"] > 0
    assert coverage_by_timeframe["weekly"]["availability_mask"]["si_fmfm300"] == "blocked"


def test_v061_feature_runtime_is_deterministic_and_panel_mapped():
    payload = {"symbol": "RELIANCE", "seed": 7, "source_bars": 1950}
    first = client.post("/api/v1/behavior/features/seven-timeframe", json=payload)
    second = client.post("/api/v1/behavior/features/seven-timeframe", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_report = first.json()["data"]
    second_report = second.json()["data"]
    assert first_report["source_snapshot_hash"] == second_report["source_snapshot_hash"]
    assert [record["row_hash"] for record in first_report["closed_bar_records"]] == [
        record["row_hash"] for record in second_report["closed_bar_records"]
    ]

    panel_response = client.get("/api/v1/behavior/frontend/panel-map")
    assert panel_response.status_code == 200
    panels = panel_response.json()["data"]["panels"]
    runtime_panel = next(panel for panel in panels if panel["panel_id"] == "seven_timeframe_feature_runtime")
    assert runtime_panel["contract_name"] == "SevenTimeframeFeatureRuntimeReport"
    assert runtime_panel["endpoint"] == "/api/v1/behavior/features/seven-timeframe/current"
    assert runtime_panel["manifest_status"] == "mock"


def test_v062_feature_store_writes_partitioned_metadata_and_files():
    payload = {"symbol": "RELIANCE", "seed": 62, "source_bars": 1950, "adjusted_price_version": "raw"}
    response = client.post("/api/v1/behavior/feature-store/write", json=payload)
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["store_version"] == "behavior-feature-store.v0.62"
    assert report["symbol"] == "RELIANCE"
    assert report["feature_version"] == "behavior_features.v0.62"
    assert report["registry_version"] == "behavior-indicator-registry-lock.v0.60"
    assert report["written_record_count"] == 9
    assert report["total_feature_rows"] > 0
    assert report["resumable"] is True
    assert report["corruption_check_passed"] is True
    assert report["raw_adjusted_mix_blocked"] is True
    assert report["proxy_or_blocked_indicators_excluded"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert all(gate["passed"] for gate in report["gates"])

    hashes = {record["source_snapshot_hash"] for record in report["records"]}
    assert hashes == {report["source_snapshot_hash"]}
    timeframes = {record["timeframe"] for record in report["records"]}
    assert timeframes == {"1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"}
    for record in report["records"]:
        path = Path(record["storage_uri"])
        assert path.exists()
        assert "feature-store" in record["storage_uri"]
        assert f"symbol={record['symbol']}" in record["storage_uri"]
        assert f"timeframe={record['timeframe']}" in record["storage_uri"]
        assert "price_version=raw" in record["storage_uri"]
        assert record["storage_format"] == "columnar_jsonl_v1"
        assert len(record["row_hash"]) == 64
        assert record["feature_count"] >= 0
        assert record["proxy_excluded_count"] >= 0
        assert record["blocked_excluded_count"] >= 0
        if record["feature_count"]:
            first_row = path.read_text(encoding="utf-8").splitlines()[0]
            assert '"availability":"available"' in first_row
            assert "proxy_visible_non_probabilistic" not in first_row


def test_v062_feature_store_is_deterministic_statused_and_panel_mapped():
    payload = {"symbol": "TCS", "seed": 620, "source_bars": 1950, "adjusted_price_version": "adjusted"}
    first = client.post("/api/v1/behavior/feature-store/write", json=payload)
    second = client.post("/api/v1/behavior/feature-store/write", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_report = first.json()["data"]
    second_report = second.json()["data"]
    assert first_report["source_snapshot_hash"] == second_report["source_snapshot_hash"]
    assert [record["row_hash"] for record in first_report["records"]] == [
        record["row_hash"] for record in second_report["records"]
    ]
    assert all("price_version=adjusted" in record["storage_uri"] for record in first_report["records"])

    status = client.get("/api/v1/behavior/feature-store/status")
    assert status.status_code == 200
    status_report = status.json()["data"]
    assert status_report["store_version"] == "behavior-feature-store.v0.62"
    assert status_report["metadata_table"] == "behavior_feature_snapshots"
    assert status_report["record_count"] >= 7
    assert status_report["corruption_check_passed"] is True
    assert status_report["parquet_reserved"] is True
    assert status_report["storage_format"] == "columnar_jsonl_v1"
    assert "idx_behavior_feature_snapshot_lookup(symbol, timeframe, decision_time_ns)" in status_report["indexes"]

    panel_response = client.get("/api/v1/behavior/frontend/panel-map")
    assert panel_response.status_code == 200
    panels = panel_response.json()["data"]["panels"]
    store_panel = next(panel for panel in panels if panel["panel_id"] == "columnar_feature_store")
    assert store_panel["contract_name"] == "FeatureStoreStatusReport"
    assert store_panel["endpoint"] == "/api/v1/behavior/feature-store/status"
    assert store_panel["manifest_status"] == "mock"


def test_v063_redundancy_control_caps_families_and_suppresses_duplicates():
    response = client.get("/api/v1/behavior/redundancy/audit/current")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["redundancy_model_version"] == "behavior-redundancy-control.v0.63"
    assert report["feature_store_version"] == "behavior-feature-store.v0.62"
    assert report["registry_version"] == "behavior-indicator-registry-lock.v0.60"
    assert report["raw_feature_count"] == 94
    assert report["eligible_feature_count"] > 0
    assert report["redundancy_cluster_count"] > 0
    assert report["effective_independent_feature_count"] > 0
    assert report["family_caps_enforced"] is True
    assert report["duplicate_inflation_blocked"] is True
    assert report["no_evaluation_leakage"] is True
    assert report["fitting_excludes_evaluation_period"] is True
    assert report["fit_end_ns"] < report["evaluation_start_ns"]
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert all(gate["passed"] for gate in report["gates"])
    assert all(weight <= 1.0 for weight in report["family_weights"].values())
    assert all(score["capped_family_weight"] <= 1.0 for score in report["family_scores"])
    assert any(score["family_cap_applied"] for score in report["family_scores"])
    assert len(report["suppressed_duplicate_features"]) > 0
    first_suppressed = report["suppressed_duplicate_features"][0]
    assert first_suppressed["similarity_score"] >= 0.90
    assert first_suppressed["kept_representative"] != first_suppressed["feature_id"]
    assert report["cross_family_audit"]["threshold"] == 0.7
    assert isinstance(report["cross_family_audit"]["penalty_applied"], bool)


def test_v063_redundancy_control_is_deterministic_and_panel_mapped():
    payload = {
        "symbol": "RELIANCE",
        "seed": 63,
        "source_bars": 1950,
        "fit_start_ns": 1_714_698_900_000_000_000,
        "fit_end_ns": 1_714_815_900_000_000_000,
        "evaluation_start_ns": 1_714_815_960_000_000_000,
    }
    first = client.post("/api/v1/behavior/redundancy/audit", json=payload)
    second = client.post("/api/v1/behavior/redundancy/audit", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_report = first.json()["data"]
    second_report = second.json()["data"]
    assert first_report["source_snapshot_hash"] == second_report["source_snapshot_hash"]
    assert first_report["family_weights"] == second_report["family_weights"]
    assert first_report["clusters"] == second_report["clusters"]
    assert first_report["suppressed_duplicate_features"] == second_report["suppressed_duplicate_features"]
    assert first_report["fit_end_ns"] < first_report["evaluation_start_ns"]

    panel_response = client.get("/api/v1/behavior/frontend/panel-map")
    assert panel_response.status_code == 200
    panels = panel_response.json()["data"]["panels"]
    panel = next(panel for panel in panels if panel["panel_id"] == "redundancy_control")
    assert panel["contract_name"] == "RedundancyAuditReport"
    assert panel["endpoint"] == "/api/v1/behavior/redundancy/audit/current"
    assert panel["manifest_status"] == "mock"


def test_v096_jarvis_decision_room_declares_ui_contract_health_gemini_arbiter_report_reality_widgets_and_usefulness_without_routing():
    response = client.get("/api/v1/jarvis/decision-room/state/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    room = response.json()["data"]
    assert room["room_version"] == "jarvis-decision-room.v0.96"
    assert room["symbol"] == "RELIANCE"
    assert room["timeframe"] == "1m"
    assert room["packet_metadata"]["packet_id"]
    assert room["packet_metadata"]["packet_validity_window_seconds"] == 60
    assert room["packet_metadata"]["seconds_to_expiry_at_creation"] == 60
    assert room["chart_context"]["bar_count"] > 0
    assert room["candle_structure"]["available"] is True
    assert "rsi14" in room["indicator_snapshot"]
    assert room["gemini_summary"]["fallback_key_slots_supported"] == 5
    assert room["gemini_summary"]["provider_version"] == "jarvis-gemini-provider-manager.v0.91"
    assert room["gemini_summary"]["review_schema_version"] == "jarvis-gemini-review-schema.v0.90"
    assert room["kronos_summary"]["can_execute_orders"] is False
    assert room["openalgo_summary"]["live_broker_routing_in_trade_vision"] is False
    decision = room["trade_vision_decision"]
    assert decision["decision_version"] == "jarvis-trade-vision-decision-guide.v0.87"
    assert decision["scenario_label"]
    assert decision["scenario_bias"]
    assert decision["wait_for"]
    assert decision["avoid_if"]
    assert decision["confidence_cap_pct"] <= 55
    assert any(item["alternative"] == "BUY_NOW" for item in decision["rejected_alternatives"])
    assert room["ui_contract"]["ui_contract_version"] == "jarvis-decision-room-ui.v0.95"
    assert room["ui_contract"]["core_panel_count"] == 6
    assert room["ui_contract"]["old_panels_preserved"] is True
    assert any(panel["panel_id"] == "extended_widgets" for panel in room["ui_contract"]["core_panels"])
    assert room["system_health_matrix"]["health_version"] == "jarvis-system-health.v0.88"
    assert room["system_health_matrix"]["overall_health"] in {"healthy", "degraded", "blocked"}
    assert len(room["system_health_matrix"]["rows"]) >= 5
    assert "1m" in room["multi_timeframe_alignment"]["timeframes"]
    review = room["gemini_review_summary"]
    assert review["review_panel_version"] == "jarvis-gemini-review-panel.v0.91"
    assert review["review_source"] == "deterministic_sample_not_live_gemini"
    assert review["live_gemini_called"] is False
    assert review["validation"]["accepted_for_display"] is True
    assert review["validation"]["hallucination_detected"] is False
    assert review["can_execute_orders"] is False
    arbiter = room["decision_arbiter"]
    assert arbiter["arbiter_version"] == "jarvis-decision-arbiter.v0.92"
    assert room["final_action"] == arbiter["final_action"]
    assert arbiter["trade_allowed"] is False
    assert arbiter["order_routing_enabled"] is False
    assert arbiter["live_trading_blocked"] is True
    assert arbiter["can_export_to_openalgo"] is False
    assert arbiter["human_approval_required"] is True
    assert arbiter["gemini_review_accepted"] is True
    assert any(gate["gate_id"] == "JARVIS-ARB-003" for gate in arbiter["hard_gates"])
    reality = room["paper_reality_check"]
    assert reality["reality_check_version"] == "paper-execution-reality-check.v0.94"
    assert reality["paper_only"] is True
    assert reality["trade_allowed"] is False
    assert reality["order_routing_enabled"] is False
    assert reality["live_trading_blocked"] is True
    assert any(gate["gate_id"] == "PAPER-RC-004" for gate in reality["gates"])
    widgets = room["extended_widgets"]
    assert widgets["widgets_version"] == "jarvis-extended-widgets.v0.95"
    assert widgets["trust_score_dashboard"]["trust_label"] in {"usable_research", "watch_only", "low_trust"}
    assert widgets["watchlist_priority_ranker"]["cannot_auto_trade"] is True
    assert widgets["action_checklist"]["total_count"] >= 5
    assert widgets["analog_timeline"]["items"] or widgets["analog_timeline"]["empty_state"]
    assert widgets["trade_allowed"] is False
    assert widgets["order_routing_enabled"] is False
    assert widgets["live_trading_blocked"] is True
    usefulness = room["usefulness_record"]
    assert usefulness["usefulness_version"] == "jarvis-usefulness-tracker.v0.96"
    assert usefulness["packet_id"] == room["packet_metadata"]["packet_id"]
    assert usefulness["trade_allowed"] is False
    assert usefulness["order_routing_enabled"] is False
    assert usefulness["live_trading_blocked"] is True
    assert room["usefulness_summary"]["summary_version"] == "jarvis-usefulness-tracker.v0.96"
    assert room["usefulness_summary"]["record_count"] >= 1
    assert room["trade_allowed"] is False
    assert room["order_routing_enabled"] is False
    assert room["live_trading_blocked"] is True


def test_v097_jarvis_decision_fusion_adds_new_panel_contract_without_routing_or_old_panel_removal():
    response = client.get("/api/v1/jarvis/decision-room/fusion/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    fusion = response.json()["data"]
    assert fusion["fusion_version"] == "jarvis-decision-fusion.v0.97"
    assert fusion["room_version"] == "jarvis-decision-room.v0.96"
    assert fusion["symbol"] == "RELIANCE"
    assert fusion["timeframe"] == "1m"
    assert fusion["single_panel_purpose"]
    assert fusion["ui_rule"]["new_panel_only"] is True
    assert fusion["ui_rule"]["old_panels_preserved"] is True
    assert fusion["ui_rule"]["do_not_edit_existing_panel_behavior"] is True
    assert fusion["gemini_fallback"]["fallback_key_slots_supported"] == 5
    assert fusion["gemini_fallback"]["backend_only_keys"] is True
    assert fusion["gemini_fallback"]["keys_exposed_to_frontend"] is False
    assert {vote["engine"] for vote in fusion["engine_votes"]} == {
        "trade_vision",
        "gemini",
        "kronos",
        "openalgo_report",
        "paper_reality",
    }
    gate_ids = {gate["gate_id"] for gate in fusion["safety_gate_chain"]}
    assert {"FUSION-001", "FUSION-002", "FUSION-003", "FUSION-004", "FUSION-005"}.issubset(gate_ids)
    assert fusion["trade_allowed"] is False
    assert fusion["order_routing_enabled"] is False
    assert fusion["live_trading_blocked"] is True
    assert fusion["can_execute_orders"] is False
    assert fusion["can_override_no_trade"] is False
    assert fusion["can_override_risk"] is False


def test_v098_jarvis_replay_determinism_hashes_decision_relevant_room_fields_only():
    response = client.get("/api/v1/jarvis/decision-room/replay-determinism/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["determinism_version"] == "jarvis-replay-determinism.v0.98"
    assert report["symbol"] == "RELIANCE"
    assert report["timeframe"] == "1m"
    assert report["hash_match"] is True
    assert report["deterministic"] is True
    assert report["first_hash"] == report["second_hash"]
    assert report["canonical_section_count"] >= 15
    assert "trade_vision_decision" in report["canonical_sections"]
    assert "decision_arbiter" in report["canonical_sections"]
    assert any(path.endswith("packet_id") for path in report["ignored_volatile_fields"])
    assert any(path.endswith("created_at") for path in report["ignored_volatile_fields"])
    assert report["diff_paths"] == []
    assert report["replay_scope"]["includes_chart_context"] is True
    assert report["replay_scope"]["includes_indicator_snapshot"] is True
    assert report["replay_scope"]["includes_trade_vision_decision"] is True
    assert report["replay_scope"]["includes_arbiter"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_execute_orders"] is False
    assert report["can_override_no_trade"] is False
    assert report["can_override_risk"] is False


def test_v099_jarvis_production_blockers_explain_remaining_release_and_openalgo_gates():
    response = client.get("/api/v1/jarvis/production-blockers/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["blocker_report_version"] == "jarvis-production-blockers.v0.99"
    assert report["symbol"] == "RELIANCE"
    assert report["timeframe"] == "1m"
    assert report["overall_status"] in {
        "research_blocked",
        "paper_blocked",
        "openalgo_not_configured",
        "research_ready_paper_review_required",
    }
    assert set(report["stage_statuses"]) == {"research_stack", "paper_mode", "openalgo_handoff", "live_trading"}
    assert report["stage_statuses"]["live_trading"]["status"] == "blocked"
    gate_ids = {gate["gate_id"] for gate in report["gates"]}
    assert {"PROD-001", "PROD-002", "PROD-003", "PROD-004", "PROD-005", "PROD-006", "PROD-007", "PROD-008", "PROD-009", "PROD-010"}.issubset(gate_ids)
    assert report["evidence_versions"]["fusion"] == "jarvis-decision-fusion.v0.97"
    assert report["evidence_versions"]["replay_determinism"] == "jarvis-replay-determinism.v0.98"
    assert report["production_scope"]["live_mode_candidate"] is False
    assert report["production_scope"]["brokerless_boundary_preserved"] is True
    assert report["openalgo_handoff"]["allowed_scope"] == "dry_run_or_research_handoff_only"
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_execute_orders"] is False
    assert report["can_export_to_openalgo"] is False
    assert report["can_override_no_trade"] is False
    assert report["can_override_risk"] is False


def test_v100_jarvis_blocker_resolution_pack_maps_blockers_to_safe_operator_actions():
    response = client.get("/api/v1/jarvis/blocker-resolution/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    pack = response.json()["data"]
    assert pack["resolution_version"] == "jarvis-blocker-resolution.v1.00"
    assert pack["symbol"] == "RELIANCE"
    assert pack["timeframe"] == "1m"
    assert pack["source_blocker_report_version"] == "jarvis-production-blockers.v0.99"
    assert pack["remediation_count"] >= 1
    assert pack["must_fix_count"] >= 1
    item_ids = {item["item_id"] for item in pack["remediation_items"]}
    assert "OPENALGO-AUTH-001" in item_ids or "SECURITY-ACTIVE_KEY" in item_ids
    assert any("TRADEVISION_ADAPTER_SHARED_SECRET" in hint for item in pack["remediation_items"] for hint in item["env_hints"])
    assert pack["safe_configuration_template"]["backend_environment_only"] is True
    assert pack["safe_configuration_template"]["frontend_must_not_receive_secrets"] is True
    assert pack["operator_runbook"]
    assert "GET /api/v1/jarvis/blocker-resolution/RELIANCE?timeframe=1m&rows=390&position=tail" in pack["verification_commands"]
    assert pack["cannot_auto_fix"]
    assert pack["trade_allowed"] is False
    assert pack["order_routing_enabled"] is False
    assert pack["live_trading_blocked"] is True
    assert pack["can_execute_orders"] is False
    assert pack["can_export_to_openalgo"] is False
    assert pack["can_override_no_trade"] is False
    assert pack["can_override_risk"] is False


def test_v101_jarvis_preflight_evidence_runner_captures_readiness_without_enabling_routes():
    response = client.get("/api/v1/jarvis/preflight-evidence/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    pack = response.json()["data"]
    assert pack["preflight_version"] == "jarvis-preflight-evidence.v1.01"
    assert pack["symbol"] == "RELIANCE"
    assert pack["timeframe"] == "1m"
    assert pack["check_count"] == 9
    check_ids = {check["check_id"] for check in pack["checklist"]}
    assert {"PREFLIGHT-001", "PREFLIGHT-002", "PREFLIGHT-003", "PREFLIGHT-004", "PREFLIGHT-005", "PREFLIGHT-006", "PREFLIGHT-007", "PREFLIGHT-008", "PREFLIGHT-009"}.issubset(check_ids)
    assert pack["evidence_snapshots"]["production_blockers"]["version"] == "jarvis-production-blockers.v0.99"
    assert pack["evidence_snapshots"]["resolution_pack"]["version"] == "jarvis-blocker-resolution.v1.00"
    assert pack["minimum_evidence_bundle"]
    assert pack["operator_decision"]["live_trading_allowed"] is False
    assert pack["operator_decision"]["manual_approval_required"] is True
    assert "production_blocker_report.json" in pack["artifact_names"]
    assert "openalgo_transport_status.json" in pack["artifact_names"]
    assert pack["trade_allowed"] is False
    assert pack["order_routing_enabled"] is False
    assert pack["live_trading_blocked"] is True
    assert pack["can_execute_orders"] is False
    assert pack["can_export_to_openalgo"] is False
    assert pack["can_override_no_trade"] is False
    assert pack["can_override_risk"] is False


def test_v102_openalgo_local_adapter_harness_reports_safe_dry_run_setup_without_export():
    response = client.get("/api/v1/openalgo/adapter-harness/status")
    assert response.status_code == 200
    harness = response.json()["data"]
    assert harness["harness_version"] == "openalgo-local-adapter-harness.v1.02"
    assert harness["files"]["adapter_root"] is True
    assert harness["files"]["adapter_app"] is True
    assert harness["files"]["adapter_tests"] is True
    assert harness["safety_contract"]["dry_run_only"] is True
    assert harness["safety_contract"]["broker_order_creation_allowed"] is False
    assert harness["safety_contract"]["order_routing_allowed"] is False
    assert harness["launch_plan"]["auto_start_supported"] is False
    assert "TRADEVISION_ADAPTER_SHARED_SECRET" in harness["launch_plan"]["manual_command"]
    assert harness["health_check_plan"]["requires_hmac_headers"] is True
    assert harness["intent_review_plan"]["requires_hmac_headers"] is True
    assert "order_routing_enabled=true" in harness["intent_review_plan"]["must_reject"]
    assert harness["trade_allowed"] is False
    assert harness["order_routing_enabled"] is False
    assert harness["live_trading_blocked"] is True
    assert harness["can_execute_orders"] is False
    assert harness["can_export_to_openalgo"] is False
    assert harness["can_override_no_trade"] is False
    assert harness["can_override_risk"] is False


def test_v103_jarvis_master_panel_combines_evidence_without_replacing_old_panels():
    response = client.get("/api/v1/jarvis/decision-room/master-panel/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    panel = response.json()["data"]
    assert panel["panel_version"] == "jarvis-master-decision-panel.v1.03"
    assert panel["symbol"] == "RELIANCE"
    assert panel["integration_rule"]["new_panel_only"] is True
    assert panel["integration_rule"]["old_panels_preserved"] is True
    assert panel["integration_rule"]["does_not_replace_existing_fusion_panel"] is True
    assert panel["gemini_fallback_policy"]["fallback_key_slots_supported"] == 5
    assert panel["gemini_fallback_policy"]["backend_only_keys"] is True
    assert panel["gemini_fallback_policy"]["keys_exposed_to_frontend"] is False
    assert panel["gemini_fallback_policy"]["timeout_ms"] == 2000
    gate_ids = {gate["gate_id"] for gate in panel["minimal_safety_gate_chain"]}
    assert {"MASTER-001", "MASTER-002", "MASTER-003", "MASTER-004", "MASTER-005", "MASTER-006"}.issubset(gate_ids)
    sources = {item["source"] for item in panel["evidence_stack"]}
    assert {"trade_vision_behavior", "chart_candle_structure", "indicator_matrix", "gemini_review", "kronos_prior", "openalgo_report", "paper_reality"}.issubset(sources)
    assert panel["trade_allowed"] is False
    assert panel["order_routing_enabled"] is False
    assert panel["live_trading_blocked"] is True
    assert panel["can_execute_orders"] is False
    assert panel["can_export_to_openalgo"] is False
    assert panel["can_override_no_trade"] is False
    assert panel["can_override_risk"] is False


def test_v104_gemini_outbound_bundle_is_dry_run_secret_free_and_rotation_ready(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1", "gemini-real-secret-one")
    monkeypatch.setenv("GEMINI_API_KEY_2", "gemini-real-secret-two")
    response = client.get("/api/v1/jarvis/gemini/outbound-bundle/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    bundle = response.json()["data"]
    serialized = json.dumps(bundle, sort_keys=True)
    assert bundle["bundle_version"] == "jarvis-gemini-outbound-review-bundle.v1.04"
    assert bundle["dry_run_only"] is True
    assert bundle["live_call_performed"] is False
    assert bundle["network_call_allowed"] is False
    assert bundle["ready_for_live_call"] is False
    assert bundle["fallback_key_slots_supported"] == 5
    assert bundle["configured_key_slots"] == 2
    assert len(bundle["key_rotation_plan"]) == 5
    assert "fingerprint" not in serialized
    assert "gemini-real-secret-one" not in serialized
    assert "gemini-real-secret-two" not in serialized
    assert bundle["sanitization"]["secrets_included"] is False
    assert bundle["trade_allowed"] is False
    assert bundle["order_routing_enabled"] is False
    assert bundle["live_trading_blocked"] is True
    assert bundle["can_execute_orders"] is False
    assert bundle["can_export_to_openalgo"] is False
    assert bundle["can_override_no_trade"] is False
    assert bundle["can_override_risk"] is False


def test_v104_gemini_outbound_bundle_redacts_payload_secrets_before_preview():
    payload = {
        "evidence_packet": {
            "symbol": "RELIANCE",
            "api_key": "do-not-send-api-key",
            "nested": {
                "authorization": "Bearer do-not-send-token",
                "session_cookie": "do-not-send-cookie",
                "safe_value": "visible",
            },
            "trade_vision_decision": {"final_trade_decision": "NO_TRADE"},
        }
    }
    response = client.post("/api/v1/jarvis/gemini/outbound-bundle", json=payload)
    assert response.status_code == 200
    bundle = response.json()["data"]
    serialized = json.dumps(bundle, sort_keys=True)
    assert bundle["bundle_version"] == "jarvis-gemini-outbound-review-bundle.v1.04"
    assert bundle["sanitization"]["redaction_count"] == 3
    assert "$.api_key" in bundle["sanitization"]["redacted_field_paths"]
    assert "$.nested.authorization" in bundle["sanitization"]["redacted_field_paths"]
    assert "$.nested.session_cookie" in bundle["sanitization"]["redacted_field_paths"]
    assert "do-not-send-api-key" not in serialized
    assert "do-not-send-token" not in serialized
    assert "do-not-send-cookie" not in serialized
    assert bundle["outbound_request_preview"]["evidence_packet"]["api_key"] == "[REDACTED]"
    assert bundle["outbound_request_preview"]["evidence_packet"]["nested"]["safe_value"] == "visible"
    assert bundle["live_call_performed"] is False
    assert bundle["network_call_allowed"] is False
    assert bundle["trade_allowed"] is False
    assert bundle["order_routing_enabled"] is False
    assert bundle["live_trading_blocked"] is True


def test_v105_external_ai_review_intake_accepts_valid_sample_without_authority():
    response = client.get("/api/v1/jarvis/external-ai/review-intake/sample/RELIANCE?source=gemini&timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    intake = response.json()["data"]
    assert intake["intake_version"] == "jarvis-external-ai-review-intake.v1.05"
    assert intake["source"] == "gemini"
    assert intake["intake_status"] in {"accepted_for_display", "downgraded_to_wait"}
    assert intake["display_allowed"] is True
    assert intake["validation"]["schema_validation_passed"] is True
    assert intake["validation"]["hallucination_detected"] is False
    assert intake["binding"]["schema_locked"] is True
    assert intake["binding"]["hallucinated_evidence_rejected"] is True
    assert intake["jarvis_effect"]["confidence_boost_allowed"] is False
    assert intake["trade_allowed"] is False
    assert intake["order_routing_enabled"] is False
    assert intake["live_trading_blocked"] is True
    assert intake["can_execute_orders"] is False
    assert intake["can_export_to_openalgo"] is False
    assert intake["can_override_no_trade"] is False
    assert intake["can_override_risk"] is False


def test_v105_external_ai_review_intake_rejects_hallucinated_or_unsafe_claims():
    payload = {
        "source": "grok",
        "evidence_packet": {
            "trade_vision_decision": {"final_trade_decision": "NO_TRADE"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": ["DATA_QUALITY"]},
        },
        "candidate_response": {
            "review_status": "valid",
            "agrees_with_trade_vision": False,
            "pattern_interpretation": "Invented news and broker confirmation.",
            "entry_guidance": "Buy immediately.",
            "risk_warning": "No risk.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": [],
            "confidence_comment": "Unsafe upgrade.",
            "final_action": "PAPER_CANDIDATE",
            "cited_evidence_keys": ["indicator_snapshot", "fake_news_feed", "broker_position"],
        },
    }
    response = client.post("/api/v1/jarvis/external-ai/review-intake", json=payload)
    assert response.status_code == 200
    intake = response.json()["data"]
    assert intake["source"] == "grok"
    assert intake["intake_status"] == "rejected"
    assert intake["display_allowed"] is False
    assert intake["safe_final_action"] == "TRADE_VISION_ONLY"
    assert intake["validation"]["hallucination_detected"] is True
    assert intake["validation"]["unsafe_override_attempted"] is True
    assert "fake_news_feed" in intake["validation"]["hallucinated_evidence_keys"]
    assert "broker_position" in intake["validation"]["hallucinated_evidence_keys"]
    assert intake["jarvis_effect"]["effect"] == "discard_external_review"
    assert intake["trade_allowed"] is False
    assert intake["order_routing_enabled"] is False
    assert intake["live_trading_blocked"] is True


def test_v105_external_ai_review_intake_redacts_response_secrets():
    payload = {
        "source": "manual",
        "evidence_packet": {
            "trade_vision_decision": {"final_trade_decision": "WAIT"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": []},
        },
        "candidate_response": {
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Weak structure.",
            "entry_guidance": "Wait.",
            "risk_warning": "Below VWAP.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": ["below VWAP"],
            "confidence_comment": "No confidence boost.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["indicator_snapshot", "rsi14", "safety_summary"],
            "api_key": "external-ai-secret",
            "nested": {"authorization": "Bearer external-ai-token"},
        },
    }
    response = client.post("/api/v1/jarvis/external-ai/review-intake", json=payload)
    assert response.status_code == 200
    intake = response.json()["data"]
    serialized = json.dumps(intake, sort_keys=True)
    assert intake["intake_version"] == "jarvis-external-ai-review-intake.v1.05"
    assert intake["source"] == "manual"
    assert intake["sanitization"]["redaction_count"] == 2
    assert "$.api_key" in intake["sanitization"]["redacted_field_paths"]
    assert "$.nested.authorization" in intake["sanitization"]["redacted_field_paths"]
    assert "external-ai-secret" not in serialized
    assert "external-ai-token" not in serialized
    assert intake["sanitized_candidate_response"]["api_key"] == "[REDACTED]"
    assert intake["sanitized_candidate_response"]["nested"]["authorization"] == "[REDACTED]"
    assert intake["trade_allowed"] is False
    assert intake["order_routing_enabled"] is False
    assert intake["live_trading_blocked"] is True


def test_v106_external_ai_review_intake_persists_audit_history():
    sample_response = client.get("/api/v1/jarvis/external-ai/review-intake/sample/RELIANCE?source=gemini&timeframe=1m&rows=390&position=tail")
    assert sample_response.status_code == 200
    sample = sample_response.json()["data"]
    assert sample["review_id"].startswith("external-ai-review:")
    assert sample["review_hash"]
    assert sample["symbol"] == "RELIANCE"

    bad_payload = {
        "source": "grok",
        "evidence_packet": {
            "trade_vision_decision": {"final_trade_decision": "NO_TRADE"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": ["DATA_QUALITY"]},
        },
        "candidate_response": {
            "review_status": "valid",
            "agrees_with_trade_vision": False,
            "pattern_interpretation": "Invented broker signal.",
            "entry_guidance": "Buy now.",
            "risk_warning": "None.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": [],
            "confidence_comment": "Unsafe.",
            "final_action": "PAPER_CANDIDATE",
            "cited_evidence_keys": ["indicator_snapshot", "invented_broker_signal"],
        },
    }
    bad_response = client.post("/api/v1/jarvis/external-ai/review-intake", json=bad_payload)
    assert bad_response.status_code == 200
    rejected = bad_response.json()["data"]
    assert rejected["intake_status"] == "rejected"

    list_response = client.get("/api/v1/jarvis/external-ai/reviews?symbol=RELIANCE&limit=10")
    assert list_response.status_code == 200
    records = list_response.json()["data"]
    assert any(record["review_id"] == sample["review_id"] for record in records)

    grok_response = client.get("/api/v1/jarvis/external-ai/reviews?source=grok&limit=10")
    assert grok_response.status_code == 200
    grok_records = grok_response.json()["data"]
    assert any(record["review_id"] == rejected["review_id"] for record in grok_records)

    audit_response = client.get("/api/v1/jarvis/external-ai/review-audit?limit=100")
    assert audit_response.status_code == 200
    audit = audit_response.json()["data"]
    assert audit["summary_version"] == "jarvis-external-ai-review-audit.v1.06"
    assert audit["record_count"] >= 2
    assert audit["accepted_count"] >= 1
    assert audit["rejected_count"] >= 1
    assert "gemini" in audit["sources"]
    assert "grok" in audit["sources"]
    assert audit["confidence_boost_allowed"] is False
    assert audit["trade_allowed"] is False
    assert audit["order_routing_enabled"] is False
    assert audit["live_trading_blocked"] is True


def test_v107_external_ai_reliability_detects_disagreement_low_evidence_and_blocks_authority():
    symbol = "TVREL107A"
    evidence_packet = {
        "symbol": symbol,
        "trade_vision_decision": {"final_trade_decision": "WAIT"},
        "indicator_snapshot": {"rsi14": 44.0},
        "safety_summary": {"blocking_gates": []},
        "multi_timeframe_alignment": {
            "timeframes": {"daily": "closed_resistance_nearby", "weekly": "closed_range"},
            "htf_confirmation_available": True,
        },
    }
    for source, final_action in (("gemini", "WAIT"), ("grok", "WATCH_ONLY")):
        response = client.post(
            "/api/v1/jarvis/external-ai/review-intake",
            json={
                "source": source,
                "evidence_packet": evidence_packet,
                "candidate_response": {
                    "symbol": symbol,
                    "review_status": "valid",
                    "agrees_with_trade_vision": final_action == "WAIT",
                    "pattern_interpretation": "HTF evidence cited; decision remains display-only.",
                    "entry_guidance": "Wait for Trade Vision confirmation.",
                    "risk_warning": "No external AI authority.",
                    "best_indicator_for_pattern": ["rsi14"],
                    "avoid_if": ["risk gate fails"],
                    "confidence_comment": "External AI cannot boost confidence.",
                    "final_action": final_action,
                    "cited_evidence_keys": [
                        "symbol",
                        "trade_vision_decision",
                        "final_trade_decision",
                        "indicator_snapshot",
                        "rsi14",
                        "safety_summary",
                        "multi_timeframe_alignment",
                        "timeframes",
                        "daily",
                    ],
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["display_allowed"] is True

    reliability_response = client.get(f"/api/v1/jarvis/external-ai/reliability?symbol={symbol}&stale_after_seconds=900")
    assert reliability_response.status_code == 200
    report = reliability_response.json()["data"]
    assert report["reliability_version"] == "jarvis-external-ai-consensus-reliability.v1.07"
    assert report["record_count"] >= 2
    assert set(report["sources_seen"]).issuperset({"gemini", "grok"})
    assert report["action_counts"]["WAIT"] >= 1
    assert report["action_counts"]["WATCH_ONLY"] >= 1
    assert report["disagreement_detected"] is True
    assert report["low_evidence_detected"] is True
    assert report["verified_daily_data"]["only_verified_daily_data_used"] is True
    gate_ids = {gate["gate_id"] for gate in report["gates"]}
    assert {"EXTAI-REL-001", "EXTAI-REL-002", "EXTAI-REL-003", "EXTAI-REL-004", "EXTAI-REL-005"}.issubset(gate_ids)
    assert report["external_ai_reliable_for_decision"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v107_external_ai_reliability_flags_missed_verified_daily_facts_from_sample():
    symbol = "TVREL107B"
    sample_response = client.get(f"/api/v1/jarvis/external-ai/review-intake/sample/{symbol}?source=gemini&timeframe=1m&rows=390&position=tail")
    assert sample_response.status_code == 200

    reliability_response = client.get(f"/api/v1/jarvis/external-ai/reliability?symbol={symbol}&stale_after_seconds=900")
    assert reliability_response.status_code == 200
    report = reliability_response.json()["data"]
    daily = report["verified_daily_data"]
    assert daily["only_verified_daily_data_used"] is True
    assert daily["external_ai_cited_daily_evidence"] is False
    assert {"DAILY-001", "DAILY-002", "DAILY-003"}.issubset(set(daily["missed_verified_daily_facts"]))
    rel004 = next(gate for gate in report["gates"] if gate["gate_id"] == "EXTAI-REL-004")
    assert rel004["passed"] is False
    assert rel004["effect"] == "downgrade"
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False


def test_v107_external_ai_reliability_blocks_unverified_daily_claim_and_detects_stale_empty_history():
    empty_response = client.get("/api/v1/jarvis/external-ai/reliability?symbol=TVEMPTYV107&stale_after_seconds=60")
    assert empty_response.status_code == 200
    empty = empty_response.json()["data"]
    assert empty["record_count"] == 0
    assert empty["stale_review_history"] is True
    assert empty["low_evidence_detected"] is True

    symbol = "TVREL107C"
    payload = {
        "source": "manual",
        "evidence_packet": {
            "symbol": symbol,
            "trade_vision_decision": {"final_trade_decision": "WAIT"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": []},
            "multi_timeframe_alignment": {
                "timeframes": {"daily": "closed_resistance_nearby", "weekly": "closed_range"},
                "htf_confirmation_available": True,
            },
        },
        "candidate_response": {
            "symbol": symbol,
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Daily resistance confirms caution, but this text intentionally omits daily evidence citation.",
            "entry_guidance": "Wait.",
            "risk_warning": "Daily context must be verified.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": ["risk gate fails"],
            "confidence_comment": "No boost.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["symbol", "trade_vision_decision", "final_trade_decision", "indicator_snapshot", "rsi14", "safety_summary"],
        },
    }
    intake_response = client.post("/api/v1/jarvis/external-ai/review-intake", json=payload)
    assert intake_response.status_code == 200
    assert intake_response.json()["data"]["display_allowed"] is True

    reliability_response = client.get(f"/api/v1/jarvis/external-ai/reliability?symbol={symbol}&stale_after_seconds=900")
    assert reliability_response.status_code == 200
    report = reliability_response.json()["data"]
    assert report["verified_daily_data"]["external_ai_mentioned_daily_context"] is True
    assert report["verified_daily_data"]["unverified_daily_claims"] is True
    rel005 = next(gate for gate in report["gates"] if gate["gate_id"] == "EXTAI-REL-005")
    assert rel005["passed"] is False
    assert rel005["effect"] == "block"
    assert report["reliability_state"] == "blocked"
    assert report["external_ai_reliable_for_decision"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["can_execute_orders"] is False
    assert report["can_export_to_openalgo"] is False
    assert report["can_override_no_trade"] is False
    assert report["can_override_risk"] is False


def test_v108_verified_evidence_certificate_lists_allowed_sections_and_missed_items():
    symbol = "TVEVID108A"
    sample_response = client.get(f"/api/v1/jarvis/external-ai/review-intake/sample/{symbol}?source=gemini&timeframe=1m&rows=390&position=tail")
    assert sample_response.status_code == 200

    response = client.get(f"/api/v1/jarvis/verified-evidence/{symbol}?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    certificate = response.json()["data"]
    assert certificate["certificate_version"] == "jarvis-verified-evidence-certificate.v1.08"
    assert "multi_timeframe_alignment" in certificate["allowed_evidence_keys"]
    section_ids = {section["section_id"] for section in certificate["evidence_sections"]}
    assert {"EV-CHART-001", "EV-IND-001", "EV-DAILY-001", "EV-MEM-001", "EV-SAFE-001"}.issubset(section_ids)
    assert certificate["verified_daily_data"]["only_verified_daily_data_used"] is True
    missed_ids = {item["item_id"] for item in certificate["external_ai_missed_items"]}
    assert {"DAILY-001", "DAILY-002", "DAILY-003", "EXTAI-MISS-EVIDENCE"}.issubset(missed_ids)
    assert certificate["required_external_ai_corrections"]
    gate_ids = {gate["gate_id"] for gate in certificate["gates"]}
    assert {"VER-EVID-001", "VER-EVID-002", "VER-EVID-003", "VER-EVID-004", "VER-EVID-005"}.issubset(gate_ids)
    assert certificate["confidence_boost_allowed"] is False
    assert certificate["trade_allowed"] is False
    assert certificate["order_routing_enabled"] is False
    assert certificate["live_trading_blocked"] is True
    assert certificate["can_execute_orders"] is False
    assert certificate["can_export_to_openalgo"] is False


def test_v108_verified_evidence_certificate_blocks_unverified_daily_claims():
    symbol = "TVEVID108B"
    payload = {
        "source": "manual",
        "evidence_packet": {
            "symbol": symbol,
            "trade_vision_decision": {"final_trade_decision": "WAIT"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": []},
            "multi_timeframe_alignment": {
                "timeframes": {"daily": "closed_resistance_nearby", "weekly": "closed_range"},
                "htf_confirmation_available": True,
            },
        },
        "candidate_response": {
            "symbol": symbol,
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Daily resistance supports caution but no daily citation is provided.",
            "entry_guidance": "Wait.",
            "risk_warning": "Daily evidence must be cited.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": ["risk gate fails"],
            "confidence_comment": "No confidence boost.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["symbol", "trade_vision_decision", "final_trade_decision", "indicator_snapshot", "rsi14", "safety_summary"],
        },
    }
    intake_response = client.post("/api/v1/jarvis/external-ai/review-intake", json=payload)
    assert intake_response.status_code == 200
    assert intake_response.json()["data"]["display_allowed"] is True

    response = client.get(f"/api/v1/jarvis/verified-evidence/{symbol}?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    certificate = response.json()["data"]
    assert certificate["certificate_state"] == "blocked"
    blocked_claims = certificate["external_ai_blocked_claims"]
    assert blocked_claims
    assert blocked_claims[0]["claim_id"] == "BLOCKED-DAILY-CLAIM"
    ver004 = next(gate for gate in certificate["gates"] if gate["gate_id"] == "VER-EVID-004")
    assert ver004["passed"] is False
    assert ver004["effect"] == "block"
    assert "Remove or recite daily/weekly/HTF claims" in " ".join(certificate["required_external_ai_corrections"])
    assert certificate["confidence_boost_allowed"] is False
    assert certificate["trade_allowed"] is False
    assert certificate["order_routing_enabled"] is False
    assert certificate["live_trading_blocked"] is True
    assert certificate["can_override_no_trade"] is False
    assert certificate["can_override_risk"] is False


def test_v109_review_preflight_separates_correction_review_from_decision_trust():
    symbol = "TVREV109A"
    sample_response = client.get(f"/api/v1/jarvis/external-ai/review-intake/sample/{symbol}?source=gemini&timeframe=1m&rows=390&position=tail")
    assert sample_response.status_code == 200

    response = client.get(f"/api/v1/jarvis/review-preflight/{symbol}?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    verdict = response.json()["data"]
    assert verdict["review_preflight_version"] == "jarvis-review-preflight-verdict.v1.09"
    targets = {target["target_id"]: target for target in verdict["review_targets"]}
    assert targets["gemini_correction_review"]["allowed"] is True
    assert targets["grok_manual_placeholder"]["allowed"] is True
    assert targets["external_ai_decision_display"]["allowed"] is False
    assert targets["openalgo_dry_run_review"]["allowed"] is False
    assert targets["live_trading"]["allowed"] is False
    assert verdict["external_ai_summary"]["low_evidence_detected"] is True
    assert verdict["verified_evidence_summary"]["allowed_evidence_key_count"] > 0
    assert verdict["verified_evidence_summary"]["missed_item_count"] > 0
    gate_ids = {gate["gate_id"] for gate in verdict["gates"]}
    assert {"REV-PRE-001", "REV-PRE-002", "REV-PRE-003", "REV-PRE-004", "REV-PRE-005", "REV-PRE-006", "REV-PRE-007"}.issubset(gate_ids)
    assert verdict["required_before_resubmission"]
    assert verdict["confidence_boost_allowed"] is False
    assert verdict["trade_allowed"] is False
    assert verdict["order_routing_enabled"] is False
    assert verdict["live_trading_blocked"] is True
    assert verdict["can_execute_orders"] is False
    assert verdict["can_export_to_openalgo"] is False
    assert verdict["can_override_no_trade"] is False
    assert verdict["can_override_risk"] is False


def test_v109_review_preflight_blocks_unsupported_daily_claims_before_review_trust():
    symbol = "TVREV109B"
    payload = {
        "source": "manual",
        "evidence_packet": {
            "symbol": symbol,
            "trade_vision_decision": {"final_trade_decision": "WAIT"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": []},
            "multi_timeframe_alignment": {
                "timeframes": {"daily": "closed_resistance_nearby", "weekly": "closed_range"},
                "htf_confirmation_available": True,
            },
        },
        "candidate_response": {
            "symbol": symbol,
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Daily resistance supports caution without a daily citation.",
            "entry_guidance": "Wait.",
            "risk_warning": "Daily evidence must be cited.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": ["risk gate fails"],
            "confidence_comment": "No confidence boost.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["symbol", "trade_vision_decision", "final_trade_decision", "indicator_snapshot", "rsi14", "safety_summary"],
        },
    }
    intake_response = client.post("/api/v1/jarvis/external-ai/review-intake", json=payload)
    assert intake_response.status_code == 200

    response = client.get(f"/api/v1/jarvis/review-preflight/{symbol}?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    verdict = response.json()["data"]
    assert verdict["verdict_state"] == "blocked"
    rev003 = next(gate for gate in verdict["gates"] if gate["gate_id"] == "REV-PRE-003")
    assert rev003["passed"] is False
    assert rev003["effect"] == "block"
    targets = {target["target_id"]: target for target in verdict["review_targets"]}
    assert targets["external_ai_decision_display"]["allowed"] is False
    assert targets["openalgo_dry_run_review"]["allowed"] is False
    assert targets["live_trading"]["allowed"] is False
    assert verdict["confidence_boost_allowed"] is False
    assert verdict["trade_allowed"] is False
    assert verdict["order_routing_enabled"] is False
    assert verdict["live_trading_blocked"] is True


def test_v110_correction_review_packet_is_dry_run_verified_and_safe():
    symbol = "TVCORR110A"
    sample_response = client.get(f"/api/v1/jarvis/external-ai/review-intake/sample/{symbol}?source=gemini&timeframe=1m&rows=390&position=tail")
    assert sample_response.status_code == 200

    response = client.get(f"/api/v1/jarvis/correction-review-packet/{symbol}?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    packet = response.json()["data"]
    assert packet["packet_version"] == "jarvis-correction-review-packet.v1.10"
    assert packet["packet_hash"]
    assert packet["request_hash"]
    assert packet["dry_run_only"] is True
    assert packet["network_call_allowed"] is False
    assert packet["live_call_performed"] is False
    assert packet["ready_for_correction_review"] is True
    assert packet["ready_for_decision_trust"] is False
    assert packet["ready_for_openalgo"] is False
    assert packet["sanitization"]["secrets_included"] is False
    assert packet["sanitization"]["broker_credentials_included"] is False
    assert packet["sanitization"]["cookies_or_sessions_included"] is False
    assert packet["outbound_request_preview"]["response_format"] == "strict_json"
    assert packet["outbound_request_preview"]["temperature"] == 0.0
    assert "verified_evidence" in packet["outbound_request_preview"]["evidence_packet"]
    assert "review_preflight" in packet["outbound_request_preview"]["evidence_packet"]
    contract = packet["correction_contract"]
    assert contract["must_return_json_only"] is True
    assert contract["cannot_raise_confidence"] is True
    assert contract["cannot_change_trade_vision_decision"] is True
    assert contract["cannot_export_to_openalgo"] is True
    assert "EXTAI-MISS-EVIDENCE" in contract["must_address_missing_items"]
    gate_ids = {gate["gate_id"] for gate in packet["gates"]}
    assert {"CORR-PKT-001", "CORR-PKT-002", "CORR-PKT-003", "CORR-PKT-004", "CORR-PKT-005", "CORR-PKT-006"}.issubset(gate_ids)
    assert packet["confidence_boost_allowed"] is False
    assert packet["trade_allowed"] is False
    assert packet["order_routing_enabled"] is False
    assert packet["live_trading_blocked"] is True
    assert packet["can_execute_orders"] is False
    assert packet["can_export_to_openalgo"] is False
    assert packet["can_override_no_trade"] is False
    assert packet["can_override_risk"] is False


def test_v110_correction_review_packet_uses_review_only_preflight_without_final_audit(monkeypatch):
    from app import main as api_main

    def forbidden_final_audit():
        raise AssertionError("correction review packet must not run final release audit")

    monkeypatch.setattr(api_main, "build_final_release_audit", forbidden_final_audit)

    response = client.get("/api/v1/jarvis/correction-review-packet/TVCORR110FAST?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    packet = response.json()["data"]
    assert packet["ready_for_correction_review"] is True
    assert packet["ready_for_decision_trust"] is False
    assert packet["ready_for_openalgo"] is False
    assert packet["trade_allowed"] is False
    assert packet["order_routing_enabled"] is False
    assert packet["live_trading_blocked"] is True


def test_v110_correction_review_packet_redacts_secret_like_values_in_verified_payload():
    symbol = "TVCORR110B"
    payload = {
        "source": "manual",
        "evidence_packet": {
            "symbol": symbol,
            "trade_vision_decision": {"final_trade_decision": "WAIT"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": []},
            "multi_timeframe_alignment": {
                "timeframes": {"daily": "closed_resistance_nearby", "weekly": "closed_range"},
                "htf_confirmation_available": True,
            },
        },
        "candidate_response": {
            "symbol": symbol,
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Daily context is cited correctly.",
            "entry_guidance": "Wait.",
            "risk_warning": "No boost.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": ["risk gate fails"],
            "confidence_comment": "No confidence boost.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["symbol", "trade_vision_decision", "final_trade_decision", "indicator_snapshot", "rsi14", "safety_summary", "multi_timeframe_alignment", "timeframes", "daily"],
            "api_key": "must-not-leak",
            "nested": {"authorization": "Bearer secret"},
        },
    }
    intake_response = client.post("/api/v1/jarvis/external-ai/review-intake", json=payload)
    assert intake_response.status_code == 200

    response = client.get(f"/api/v1/jarvis/correction-review-packet/{symbol}?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    packet = response.json()["data"]
    serialized = json.dumps(packet, sort_keys=True)
    assert "must-not-leak" not in serialized
    assert "Bearer secret" not in serialized
    assert packet["sanitization"]["secrets_included"] is False
    assert packet["network_call_allowed"] is False
    assert packet["ready_for_decision_trust"] is False
    assert packet["ready_for_openalgo"] is False


def test_v111_correction_response_sample_accepts_display_only_valid_output():
    symbol = "TVCORR111A"
    sample_response = client.get(f"/api/v1/jarvis/external-ai/review-intake/sample/{symbol}?source=gemini&timeframe=1m&rows=390&position=tail")
    assert sample_response.status_code == 200

    response = client.get(f"/api/v1/jarvis/correction-review/sample/{symbol}?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    validation = response.json()["data"]
    assert validation["validation_version"] == "jarvis-correction-response-validator.v1.11"
    assert validation["accepted_for_correction_display"] is True
    assert validation["display_status"] == "accepted_for_correction_display"
    assert validation["base_validation"]["schema_validation_passed"] is True
    assert validation["base_validation"]["hallucination_detected"] is False
    assert validation["citation_validation"]["passed"] is True
    assert validation["missing_item_validation"]["passed"] is True
    assert validation["blocked_claim_validation"]["passed"] is True
    assert validation["action_validation"]["passed"] is True
    assert validation["daily_claim_validation"]["passed"] is True
    gate_ids = {gate["gate_id"] for gate in validation["gates"]}
    assert {"CORR-RESP-001", "CORR-RESP-002", "CORR-RESP-003", "CORR-RESP-004", "CORR-RESP-005", "CORR-RESP-006", "CORR-RESP-007", "CORR-RESP-008"}.issubset(gate_ids)
    assert validation["confidence_boost_allowed"] is False
    assert validation["trade_allowed"] is False
    assert validation["order_routing_enabled"] is False
    assert validation["live_trading_blocked"] is True
    assert validation["can_execute_orders"] is False
    assert validation["can_export_to_openalgo"] is False


def test_v111_correction_response_rejects_invalid_citation_missing_items_and_unsafe_action():
    symbol = "TVCORR111B"
    packet = client.get(f"/api/v1/jarvis/correction-review-packet/{symbol}?timeframe=1m&rows=390&position=tail").json()["data"]
    candidate = {
        "review_status": "valid",
        "agrees_with_trade_vision": True,
        "pattern_interpretation": "Daily resistance says buy immediately with invented broker confirmation.",
        "entry_guidance": "Buy now.",
        "risk_warning": "No risk.",
        "best_indicator_for_pattern": ["rsi14"],
        "avoid_if": [],
        "confidence_comment": "Confidence can increase.",
        "final_action": "PAPER_CANDIDATE",
        "cited_evidence_keys": ["verified_evidence", "invented_broker_confirmation"],
        "addressed_missing_items": [],
        "removed_blocked_claims": [],
    }
    response = client.post(
        "/api/v1/jarvis/correction-review/validate",
        json={"symbol": symbol, "source": "grok", "correction_packet": packet, "candidate_response": candidate},
    )
    assert response.status_code == 200
    validation = response.json()["data"]
    assert validation["validation_version"] == "jarvis-correction-response-validator.v1.11"
    assert validation["accepted_for_correction_display"] is False
    assert validation["display_status"] in {"blocked", "needs_resubmission"}
    assert validation["base_validation"]["hallucination_detected"] is True
    assert "invented_broker_confirmation" in validation["base_validation"]["hallucinated_evidence_keys"]
    assert validation["citation_validation"]["passed"] is False
    assert "invented_broker_confirmation" in validation["citation_validation"]["invalid_citations"]
    assert validation["missing_item_validation"]["passed"] is False
    assert validation["action_validation"]["passed"] is False
    assert validation["safe_final_action"] == "TRADE_VISION_ONLY"
    assert validation["required_resubmission_items"]
    assert validation["trade_allowed"] is False
    assert validation["order_routing_enabled"] is False
    assert validation["live_trading_blocked"] is True
    assert validation["can_override_no_trade"] is False
    assert validation["can_override_risk"] is False


def test_v111_correction_response_rejects_unremoved_blocked_daily_claim():
    symbol = "TVCORR111C"
    payload = {
        "source": "manual",
        "evidence_packet": {
            "symbol": symbol,
            "trade_vision_decision": {"final_trade_decision": "WAIT"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": []},
            "multi_timeframe_alignment": {
                "timeframes": {"daily": "closed_resistance_nearby", "weekly": "closed_range"},
                "htf_confirmation_available": True,
            },
        },
        "candidate_response": {
            "symbol": symbol,
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Daily resistance supports caution without a daily citation.",
            "entry_guidance": "Wait.",
            "risk_warning": "Daily evidence must be cited.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": ["risk gate fails"],
            "confidence_comment": "No confidence boost.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["symbol", "trade_vision_decision", "final_trade_decision", "indicator_snapshot", "rsi14", "safety_summary"],
        },
    }
    intake_response = client.post("/api/v1/jarvis/external-ai/review-intake", json=payload)
    assert intake_response.status_code == 200
    packet = client.get(f"/api/v1/jarvis/correction-review-packet/{symbol}?timeframe=1m&rows=390&position=tail").json()["data"]
    candidate = {
        "review_status": "valid",
        "agrees_with_trade_vision": True,
        "pattern_interpretation": "Daily context was removed from the trade idea.",
        "entry_guidance": "Wait.",
        "risk_warning": "No confidence boost.",
        "best_indicator_for_pattern": ["verified_evidence"],
        "avoid_if": ["Trade Vision safety gate fails."],
        "confidence_comment": "Display-only correction.",
        "final_action": "WAIT",
        "cited_evidence_keys": ["verified_evidence", "verified_daily_data", "review_preflight"],
        "addressed_missing_items": packet["correction_contract"]["must_address_missing_items"],
        "removed_blocked_claims": [],
    }
    response = client.post(
        "/api/v1/jarvis/correction-review/validate",
        json={"symbol": symbol, "source": "manual", "correction_packet": packet, "candidate_response": candidate},
    )
    assert response.status_code == 200
    validation = response.json()["data"]
    assert validation["blocked_claim_validation"]["passed"] is False
    assert "BLOCKED-DAILY-CLAIM" in validation["blocked_claim_validation"]["still_blocked_claims"]
    assert validation["accepted_for_correction_display"] is False
    assert validation["display_status"] == "blocked"
    assert validation["confidence_boost_allowed"] is False
    assert validation["trade_allowed"] is False
    assert validation["order_routing_enabled"] is False
    assert validation["live_trading_blocked"] is True


def test_v112_correction_response_audit_persists_accepted_and_rejected_validations():
    symbol = "TVCORR112A"
    accepted_response = client.get(f"/api/v1/jarvis/correction-review/sample/{symbol}?timeframe=1m&rows=390&position=tail")
    assert accepted_response.status_code == 200
    accepted = accepted_response.json()["data"]
    assert accepted["validation_id"].startswith("correction-response:")
    assert accepted["validation_hash"]
    assert accepted["symbol"] == symbol
    assert accepted["accepted_for_correction_display"] is True

    packet = client.get(f"/api/v1/jarvis/correction-review-packet/{symbol}?timeframe=1m&rows=390&position=tail").json()["data"]
    rejected_response = client.post(
        "/api/v1/jarvis/correction-review/validate",
        json={
            "symbol": symbol,
            "source": "grok",
            "correction_packet": packet,
            "candidate_response": {
                "review_status": "valid",
                "agrees_with_trade_vision": False,
                "pattern_interpretation": "Invented broker route.",
                "entry_guidance": "Buy now.",
                "risk_warning": "None.",
                "best_indicator_for_pattern": ["rsi14"],
                "avoid_if": [],
                "confidence_comment": "Unsafe.",
                "final_action": "PAPER_CANDIDATE",
                "cited_evidence_keys": ["verified_evidence", "fake_broker_route"],
                "addressed_missing_items": [],
                "removed_blocked_claims": [],
            },
        },
    )
    assert rejected_response.status_code == 200
    rejected = rejected_response.json()["data"]
    assert rejected["accepted_for_correction_display"] is False
    assert rejected["validation_id"].startswith("correction-response:")

    records_response = client.get(f"/api/v1/jarvis/correction-review/records?symbol={symbol}&limit=10")
    assert records_response.status_code == 200
    records = records_response.json()["data"]
    assert any(record["validation_id"] == accepted["validation_id"] for record in records)
    assert any(record["validation_id"] == rejected["validation_id"] for record in records)

    grok_response = client.get("/api/v1/jarvis/correction-review/records?source=grok&limit=10")
    assert grok_response.status_code == 200
    grok_records = grok_response.json()["data"]
    assert any(record["validation_id"] == rejected["validation_id"] for record in grok_records)

    audit_response = client.get(f"/api/v1/jarvis/correction-review/audit?symbol={symbol}&limit=100")
    assert audit_response.status_code == 200
    audit = audit_response.json()["data"]
    assert audit["summary_version"] == "jarvis-correction-response-audit.v1.12"
    assert audit["record_count"] >= 2
    assert audit["accepted_count"] >= 1
    assert audit["rejected_count"] >= 1
    assert "gemini" in audit["sources"]
    assert "grok" in audit["sources"]
    assert audit["latest_validation_id"]
    assert audit["latest_packet_hash"]
    assert audit["confidence_boost_allowed"] is False
    assert audit["trade_allowed"] is False
    assert audit["order_routing_enabled"] is False
    assert audit["live_trading_blocked"] is True
    assert audit["can_export_to_openalgo"] is False


def test_v113_external_ai_audit_integrity_verifies_review_and_correction_ledgers():
    symbol = "TVAUD113A"
    review_response = client.get(f"/api/v1/jarvis/external-ai/review-intake/sample/{symbol}?source=gemini&timeframe=1m&rows=390&position=tail")
    assert review_response.status_code == 200
    review = review_response.json()["data"]
    assert review["review_id"].startswith("external-ai-review:")

    correction_response = client.get(f"/api/v1/jarvis/correction-review/sample/{symbol}?timeframe=1m&rows=390&position=tail")
    assert correction_response.status_code == 200
    correction = correction_response.json()["data"]
    assert correction["validation_id"].startswith("correction-response:")

    integrity_response = client.get(f"/api/v1/jarvis/external-ai/audit-integrity?symbol={symbol}&limit=100&stale_after_seconds=86400")
    assert integrity_response.status_code == 200
    integrity = integrity_response.json()["data"]
    assert integrity["integrity_version"] == "jarvis-external-ai-audit-integrity.v1.13"
    assert integrity["external_review_count"] >= 1
    assert integrity["correction_response_count"] >= 1
    assert integrity["accepted_external_review_count"] >= 1
    assert integrity["accepted_correction_response_count"] >= 1
    assert integrity["external_review_issues"] == []
    assert integrity["correction_response_issues"] == []
    assert integrity["authority_issues"] == []
    assert {gate["gate_id"] for gate in integrity["gates"]} >= {
        "AUDIT-INT-001",
        "AUDIT-INT-002",
        "AUDIT-INT-003",
        "AUDIT-INT-004",
        "AUDIT-INT-005",
        "AUDIT-INT-006",
        "AUDIT-INT-007",
    }
    assert integrity["verified_daily_data_policy"]["only_trade_vision_verified_daily_data_allowed"] is True
    assert integrity["external_ai_reliable_for_decision"] is False
    assert integrity["confidence_boost_allowed"] is False
    assert integrity["trade_allowed"] is False
    assert integrity["order_routing_enabled"] is False
    assert integrity["live_trading_blocked"] is True
    assert integrity["can_export_to_openalgo"] is False


def test_v113_external_ai_audit_integrity_warns_on_empty_or_stale_history():
    response = client.get("/api/v1/jarvis/external-ai/audit-integrity?symbol=TVEMPTY113&limit=100&stale_after_seconds=60")
    assert response.status_code == 200
    integrity = response.json()["data"]
    assert integrity["integrity_version"] == "jarvis-external-ai-audit-integrity.v1.13"
    assert integrity["integrity_state"] == "warning"
    assert integrity["ledger_empty_warning"] is True
    assert integrity["stale_review_history"] is True
    gates = {gate["gate_id"]: gate for gate in integrity["gates"]}
    assert gates["AUDIT-INT-005"]["passed"] is False
    assert gates["AUDIT-INT-006"]["passed"] is False
    assert integrity["trade_allowed"] is False
    assert integrity["order_routing_enabled"] is False
    assert integrity["live_trading_blocked"] is True
    assert integrity["can_execute_orders"] is False


def test_v114_jarvis_decision_evidence_export_combines_all_review_evidence():
    symbol = "TVEXP114A"
    client.get(f"/api/v1/jarvis/external-ai/review-intake/sample/{symbol}?source=gemini&timeframe=1m&rows=390&position=tail")
    client.get(f"/api/v1/jarvis/correction-review/sample/{symbol}?timeframe=1m&rows=390&position=tail")

    response = client.get(f"/api/v1/jarvis/decision-evidence/export/{symbol}?timeframe=1m&rows=390&position=tail&stale_after_seconds=86400")
    assert response.status_code == 200
    export = response.json()["data"]
    assert export["export_version"] == "jarvis-decision-evidence-export.v1.14"
    assert export["symbol"] == symbol
    assert export["packet_id"]
    assert export["export_hash"]
    assert export["download_filename"].endswith(".json")
    assert export["section_count"] >= 21
    section_ids = {section["section_id"] for section in export["evidence_sections"]}
    assert {
        "chart_context",
        "candle_structure",
        "indicator_snapshot",
        "sequential_signals",
        "multi_timeframe_alignment",
        "similar_history",
        "trade_vision_decision",
        "kronos_summary",
        "gemini_external_review",
        "openalgo_paper_evidence",
        "safety_summary",
        "decision_arbiter",
        "verified_evidence",
        "review_preflight",
        "daily_verified_authority",
        "external_ai_reliability",
        "external_ai_audit_integrity",
        "correction_audit",
    } <= section_ids
    gates = {gate["gate_id"]: gate for gate in export["gates"]}
    assert "EVID-EXP-001" in gates
    assert "EVID-EXP-012" in gates
    assert gates["EVID-EXP-011"]["passed"] is True
    assert export["review_use_only"] is True
    assert export["network_call_performed"] is False
    assert export["external_ai_reliable_for_decision"] is False
    assert export["confidence_boost_allowed"] is False
    assert export["trade_allowed"] is False
    assert export["order_routing_enabled"] is False
    assert export["live_trading_blocked"] is True
    assert export["can_export_to_openalgo"] is False
    assert export["can_execute_orders"] is False


def test_v114_decision_evidence_export_preserves_low_evidence_warning_without_authority():
    response = client.get("/api/v1/jarvis/decision-evidence/export/TVEMPTY114?timeframe=1m&rows=390&position=tail&stale_after_seconds=60")
    assert response.status_code == 200
    export = response.json()["data"]
    assert export["export_version"] == "jarvis-decision-evidence-export.v1.14"
    gates = {gate["gate_id"]: gate for gate in export["gates"]}
    assert gates["EVID-EXP-005"]["effect"] == "downgrade"
    assert export["trade_allowed"] is False
    assert export["order_routing_enabled"] is False
    assert export["live_trading_blocked"] is True
    assert export["can_override_no_trade"] is False
    assert export["can_override_risk"] is False


def test_v115_daily_verified_authority_blocks_missing_daily_weekly_context():
    response = client.get("/api/v1/jarvis/daily-verified-authority/RELIANCE?timeframe=1m&rows=390&position=tail&stale_after_seconds=86400")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["authority_version"] == "jarvis-daily-verified-authority.v1.15"
    assert report["closed_candle_only"] is True
    assert report["authority_state"] == "blocked"
    assert report["daily_available"] is False
    assert report["weekly_available"] is False
    assert {"daily", "weekly"} <= set(report["missing_timeframes"])
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["DAILY-AUTH-001"]["passed"] is False
    assert gates["DAILY-AUTH-002"]["passed"] is False
    assert report["decision_trust_allowed"] is False
    assert report["decision_confidence_cap_pct"] == 45
    assert report["external_ai_daily_claims_allowed"] is False
    assert report["external_ai_must_cite_keys"] is True
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False


def test_v115_daily_verified_authority_accepts_closed_daily_weekly_module_contract():
    from app.behavior.jarvis_daily_verified_authority import build_daily_verified_authority_report

    room = {
        "symbol": "TVAUTH115",
        "timeframe": "1m",
        "packet_metadata": {"packet_id": "packet-115", "created_at": datetime.now(timezone.utc).isoformat()},
        "multi_timeframe_alignment": {
            "timeframes": {"daily": "closed_support_hold", "weekly": "closed_range_breakout_watch"},
            "alignment_score": 0.72,
            "htf_confirmation_available": True,
        },
    }
    report = build_daily_verified_authority_report(symbol="TVAUTH115", room=room, stale_after_seconds=86400)
    assert report["authority_version"] == "jarvis-daily-verified-authority.v1.15"
    assert report["authority_state"] == "verified"
    assert report["daily_available"] is True
    assert report["weekly_available"] is True
    assert report["missing_timeframes"] == []
    assert report["decision_trust_allowed"] is True
    assert report["decision_confidence_cap_pct"] == 100
    assert report["external_ai_daily_claims_allowed"] is True
    assert all(record["closed_candle_only"] is True for record in report["timeframe_records"])
    assert all(record["citable"] is True for record in report["timeframe_records"])
    assert report["trade_allowed"] is False
    assert report["live_trading_blocked"] is True


def test_v116_indicator_combination_memory_detects_sequential_non_same_candle_pattern():
    response = client.get("/api/v1/jarvis/indicator-combination-memory/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["memory_version"] == "jarvis-indicator-combination-memory.v1.16"
    assert report["combination_similarity_version"] == "behavior-combination-similarity.v0.65"
    assert report["symbol"] == "RELIANCE"
    assert report["memory_hash"]
    assert report["combination_count"] >= 4
    assert report["non_same_candle_sequence_detected"] is True
    sequence = report["sequence_memory"]
    assert sequence["same_candle_required"] is False
    assert sequence["ordered_indicators"] == [
        "rsi_14",
        "vwap_band_state",
        "inside_candle_height_ratio",
        "pivot_resistance_distance",
    ]
    assert sequence["candle_offsets"] == [-3, -2, -1, 0]
    assert sequence["historical_occurrence_count"] >= report["minimum_sample_size"]
    assert report["minimum_sample_pass"] is True
    assert report["evidence_quality"] in {"MEDIUM", "STRONG", "LOW_EVIDENCE_RELAXED_FILTERS"}
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["IND-COMB-003"]["passed"] is True
    assert gates["IND-COMB-004"]["passed"] is True
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False


def test_v116_indicator_combination_memory_blocks_low_sequence_evidence_module_contract():
    from app.behavior.jarvis_indicator_combination_memory import build_indicator_combination_memory_report

    room = {
        "symbol": "TVIND116",
        "timeframe": "1m",
        "indicator_snapshot": {"rsi14": 61.0, "ema_state": "bullish", "vwap_position": "above_vwap", "macd_state": "positive", "volume_z": 1.1},
        "candle_structure": {"pattern": "inside_bar", "body_pct": 18.0, "upper_wick_pct": 20.0, "lower_wick_pct": 62.0},
        "sequential_signals": [{"name": "RSI above 60", "timing": "current", "direction": "bullish"}],
    }
    combo = {
        "combination_similarity_version": "behavior-combination-similarity.v0.65",
        "output_hash": "hash",
        "minimum_sample_pass": False,
        "minimum_match_count": 30,
        "non_overlap_match_count": 8,
        "evidence_quality": "LOW",
        "point_in_time_safe": True,
        "sequential_signal_pattern": {
            "sequence_id": "seq-low",
            "sequence_hash": "seqhash",
            "ordered_indicators": ["rsi_14", "vwap_band_state"],
            "ordered_states": ["bullish_cross_60", "above_vwap_retest_hold"],
            "candle_offsets": [-1, 0],
            "same_candle_required": False,
            "historical_occurrence_count": 8,
            "minimum_sample_pass": False,
        },
        "matches": [],
    }
    report = build_indicator_combination_memory_report(room=room, combination_similarity=combo)
    assert report["memory_version"] == "jarvis-indicator-combination-memory.v1.16"
    assert report["memory_state"] == "warning"
    assert report["non_same_candle_sequence_detected"] is True
    assert report["minimum_sample_pass"] is False
    assert report["sequence_memory"]["minimum_sample_pass"] is False
    assert report["no_trade_reason"] == "Low evidence. Indicator combination history is not enough."
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["IND-COMB-004"]["passed"] is False
    assert gates["IND-COMB-005"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["live_trading_blocked"] is True


def test_v117_candle_cause_effect_memory_compares_previous_current_wick_body_effect():
    response = client.get("/api/v1/jarvis/candle-cause-effect-memory/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["memory_version"] == "jarvis-candle-cause-effect-memory.v1.17"
    assert report["symbol"] == "RELIANCE"
    assert report["memory_hash"]
    assert report["current_pair"]["previous_timestamp_ns"]
    assert report["current_pair"]["current_timestamp_ns"]
    assert report["previous_candle_anatomy"]["body_pct"] >= 0
    assert report["current_candle_anatomy"]["upper_wick_pct"] >= 0
    assert report["cause_effect_features"]["available"] is True
    assert "body_pct_delta" in report["cause_effect_features"]
    assert "upper_wick_pct_delta" in report["cause_effect_features"]
    assert "lower_wick_pct_delta" in report["cause_effect_features"]
    assert report["effect_label"] in {
        "upper_wick_rejection_followed_by_bearish_effect",
        "lower_wick_rejection_followed_by_bullish_effect",
        "no_wick_trend_follow_through",
        "long_body_followed_by_pullback",
        "compression_to_expansion",
        "direction_change_after_prior_candle",
        "mixed_candle_effect",
    }
    assert report["historical_match_count"] >= report["minimum_sample_size"]
    assert report["minimum_sample_pass"] is True
    assert report["evidence_quality"] in {"MEDIUM", "HIGH"}
    assert report["analog_examples"]
    assert report["best_matching_dates"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["CANDLE-EFFECT-002"]["passed"] is True
    assert gates["CANDLE-EFFECT-003"]["passed"] is True
    assert gates["CANDLE-EFFECT-005"]["passed"] is True
    assert gates["CANDLE-EFFECT-006"]["passed"] is True
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False


def test_v117_candle_cause_effect_memory_blocks_low_history_module_contract():
    from app.behavior.jarvis_candle_cause_effect_memory import build_candle_cause_effect_memory_report

    room = {
        "symbol": "TVCANDLE117",
        "timeframe": "1m",
        "chart_context": {
            "bars": [
                {"timestamp_ns": 1_700_000_000_000_000_000, "open": 100, "high": 103, "low": 99, "close": 102, "volume": 1000},
                {"timestamp_ns": 1_700_000_060_000_000_000, "open": 102, "high": 102.2, "low": 100, "close": 100.5, "volume": 1200},
            ]
        },
    }
    report = build_candle_cause_effect_memory_report(room=room)
    assert report["memory_version"] == "jarvis-candle-cause-effect-memory.v1.17"
    assert report["effect_label"] in {"long_body_followed_by_pullback", "direction_change_after_prior_candle", "mixed_candle_effect"}
    assert report["historical_match_count"] == 0
    assert report["minimum_sample_pass"] is False
    assert report["evidence_quality"] == "NONE"
    assert report["memory_state"] == "warning"
    assert report["no_trade_reason"] == "Low evidence. Candle cause/effect history is not enough."
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["CANDLE-EFFECT-001"]["passed"] is True
    assert gates["CANDLE-EFFECT-004"]["passed"] is False
    assert gates["CANDLE-EFFECT-005"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v118_gemini_fallback_readiness_is_backend_only_secret_free_and_dry_run(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1", "gemini-secret-one")
    monkeypatch.setenv("GEMINI_API_KEY_2", "gemini-secret-two")
    monkeypatch.delenv("TRADEVISION_GEMINI_ENABLE_LIVE", raising=False)
    response = client.get("/api/v1/jarvis/gemini/fallback-readiness/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["readiness_version"] == "jarvis-gemini-fallback-readiness.v1.18"
    assert report["configured_key_slots"] == 2
    assert report["fallback_key_slots_supported"] == 5
    assert report["backend_only_keys"] is True
    assert report["keys_exposed_to_frontend"] is False
    assert report["forbidden_key_material_paths"] == []
    assert report["dry_run_only"] is True
    assert report["live_call_performed"] is False
    assert report["network_call_allowed"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False
    serialized = json.dumps(report, sort_keys=True)
    assert "gemini-secret-one" not in serialized
    assert "gemini-secret-two" not in serialized
    assert "fingerprint" not in serialized
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["GEM-FALLBACK-001"]["passed"] is True
    assert gates["GEM-FALLBACK-004"]["passed"] is True
    assert gates["GEM-FALLBACK-005"]["passed"] is True
    assert gates["GEM-FALLBACK-008"]["passed"] is True


def test_v118_gemini_fallback_readiness_detects_forbidden_key_material_module_contract():
    from app.behavior.jarvis_gemini_fallback_readiness import build_gemini_fallback_readiness_report

    provider_status = {
        "provider_version": "test-provider",
        "configured_key_slots": 1,
        "fallback_key_slots_supported": 5,
        "key_slots": [{"slot": 1, "env_name": "GEMINI_API_KEY_1", "configured": True, "fingerprint": "abc123"}],
        "security": {"backend_only_keys": True, "keys_exposed_to_frontend": False},
        "review_schema_version": "schema",
        "selected_model": "gemini-test",
        "timeout_ms": 2000,
        "temperature": 0,
        "circuit_breaker": {"state": "open"},
        "quota_policy": {"rotate_on_rate_limit": True, "rotate_on_quota": True, "rotate_on_transient_error": True, "retry_per_key": 1},
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }
    outbound_bundle = {
        "bundle_version": "test-bundle",
        "review_schema_version": "schema",
        "dry_run_only": True,
        "live_call_performed": False,
        "network_call_allowed": False,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    report = build_gemini_fallback_readiness_report(provider_status=provider_status, outbound_bundle=outbound_bundle)
    assert report["readiness_state"] == "blocked"
    assert report["forbidden_key_material_paths"] == ["key_slots[0].fingerprint"]
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["GEM-FALLBACK-004"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["live_trading_blocked"] is True


def test_v119_gemini_live_review_harness_get_is_dry_run_no_network(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1", "gemini-secret-one")
    monkeypatch.delenv("TRADEVISION_GEMINI_ENABLE_LIVE", raising=False)
    response = client.get("/api/v1/jarvis/gemini/live-review-harness/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["harness_version"] == "jarvis-gemini-live-review-harness.v1.19"
    assert report["execution_state"] == "dry_run_no_network"
    assert report["execute_requested"] is False
    assert report["network_call_attempted"] is False
    assert report["live_call_performed"] is False
    assert report["selected_key_material_exposed"] is False
    assert report["request_body_preview"]["contains_api_key"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    serialized = json.dumps(report, sort_keys=True)
    assert "gemini-secret-one" not in serialized
    assert "x-goog-api-key" not in serialized
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["GEM-LIVE-003"]["passed"] is False
    assert gates["GEM-LIVE-004"]["passed"] is False


def test_v119_gemini_live_review_harness_post_execute_blocks_without_live_gate(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1", "gemini-secret-one")
    monkeypatch.delenv("TRADEVISION_GEMINI_ENABLE_LIVE", raising=False)
    response = client.post("/api/v1/jarvis/gemini/live-review-harness/RELIANCE?timeframe=1m&rows=390&position=tail&execute=true")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["execution_state"] == "blocked_before_network"
    assert report["execute_requested"] is True
    assert report["network_call_attempted"] is False
    assert report["live_call_performed"] is False
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["GEM-LIVE-003"]["passed"] is True
    assert gates["GEM-LIVE-004"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["live_trading_blocked"] is True


def test_v119_gemini_live_review_harness_fake_transport_validates_display_only(monkeypatch):
    from app.behavior.gemini_provider import build_gemini_outbound_review_bundle, build_gemini_provider_status
    from app.behavior.jarvis_gemini_fallback_readiness import build_gemini_fallback_readiness_report
    from app.behavior.jarvis_gemini_live_review_harness import build_gemini_live_review_harness

    monkeypatch.setenv("GEMINI_API_KEY_1", "gemini-secret-one")
    monkeypatch.setenv("TRADEVISION_GEMINI_ENABLE_LIVE", "true")
    evidence_packet = {
        "trade_vision_decision": {"final_trade_decision": "WAIT", "entry_condition": "Wait for retest."},
        "candle_structure": {"pattern": "pullback"},
        "indicator_snapshot": {"vwap_position": "above_vwap", "ema_state": "bullish", "rsi14": 61},
        "safety_summary": {"blocking_gates": []},
    }
    provider_status = build_gemini_provider_status()
    outbound_bundle = build_gemini_outbound_review_bundle(evidence_packet, provider_status)
    fallback = build_gemini_fallback_readiness_report(provider_status=provider_status, outbound_bundle=outbound_bundle)

    def fake_transport(url, headers, body, timeout):
        assert "generateContent" in url
        assert headers["x-goog-api-key"] == "gemini-secret-one"
        assert body["generationConfig"]["response_mime_type"] == "application/json"
        candidate = {
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "pullback above VWAP.",
            "entry_guidance": "Wait for retest.",
            "risk_warning": "Display only.",
            "best_indicator_for_pattern": ["vwap_position", "ema_state"],
            "avoid_if": ["risk gate fails"],
            "confidence_comment": "No confidence boost.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["trade_vision_decision", "candle_structure", "indicator_snapshot", "safety_summary"],
        }
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(candidate)}]}}]}

    report = build_gemini_live_review_harness(
        evidence_packet=evidence_packet,
        provider_status=provider_status,
        outbound_bundle=outbound_bundle,
        fallback_readiness=fallback,
        execute=True,
        transport=fake_transport,
    )
    assert report["execution_state"] == "validated_display_only"
    assert report["network_call_attempted"] is True
    assert report["live_call_performed"] is True
    assert report["response_validation"]["accepted_for_display"] is True
    assert report["parsed_review"]["final_action"] == "WAIT"
    assert report["selected_key_material_exposed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    serialized = json.dumps(report, sort_keys=True)
    assert "gemini-secret-one" not in serialized


def test_v120_openalgo_handoff_gate_blocks_default_manual_review_path():
    response = client.get("/api/v1/jarvis/openalgo/handoff-gate/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["handoff_gate_version"] == "jarvis-openalgo-handoff-gate.v1.20"
    assert report["symbol"] == "RELIANCE"
    assert report["handoff_state"] in {"blocked_manual_review", "warning_manual_review"}
    assert report["dry_run_handoff_allowed"] is False
    assert report["enqueue_allowed"] is False
    assert report["automatic_delivery_allowed"] is False
    assert report["package_summary"]["dry_run_only"] is True
    assert report["package_summary"]["broker_order_created"] is False
    assert report["package_verification"]["verified"] is True
    assert report["bot_handoff_verification"]["rejected"] is True
    assert report["transport_summary"]["order_routing_enabled"] is False
    assert report["intent_summary"]["broker_order_created"] is False
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["OA-HANDOFF-001"]["passed"] is True
    assert gates["OA-HANDOFF-002"]["passed"] is True
    assert gates["OA-HANDOFF-003"]["passed"] is True
    assert gates["OA-HANDOFF-004"]["passed"] is True
    assert gates["OA-HANDOFF-010"]["passed"] is True
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False


def test_v120_openalgo_handoff_gate_rejects_unsafe_package_module_contract():
    from app.behavior.jarvis_openalgo_handoff_gate import build_openalgo_handoff_gate_report

    package = {
        "package_version": "openalgo-executor-dry-run-package.v0.50",
        "package_id": "pkg-unsafe",
        "package_hash": "hash",
        "dry_run_only": True,
        "broker_credentials_present": False,
        "broker_order_created": True,
        "trade_allowed": False,
        "order_routing_enabled": True,
        "live_trading_blocked": False,
        "intent": {
            "intent_id": "intent-unsafe",
            "intent_signature": "sig",
            "side": "BUY",
            "mode_permission": "mock_preview_only",
            "valid_until": "2099-01-01T00:00:00+00:00",
            "expired": False,
            "duplicate_key": "dup",
            "export_allowed": True,
            "broker_credentials_present": False,
            "broker_order_created": True,
            "trade_allowed": True,
            "order_routing_enabled": True,
            "live_trading_blocked": False,
        },
        "verification": {
            "verifier_version": "openalgo-bot-handoff-verifier.v0.49",
            "accepted": False,
            "rejected": True,
            "rejection_reasons": ["unsafe"],
        },
    }
    verification = {"verification_version": "verify", "verified": True, "package_sha256_matches": True, "manifest_sha256_matches": True, "issues": []}
    transport = {"configured": True, "health_ok": True, "service_auth_configured": True, "circuit_state": "closed", "order_routing_enabled": False, "live_trading_blocked": True}
    adapter = {"harness_version": "harness", "readiness": {"dry_run_handoff_ready": True}, "order_routing_enabled": False, "live_trading_blocked": True}
    report = build_openalgo_handoff_gate_report(
        symbol="TV120",
        jarvis_room={"final_action": "WAIT", "trade_vision_decision": {"final_trade_decision": "WAIT"}, "safety_summary": {"blocking_gates": []}},
        dry_run_package=package,
        package_verification=verification,
        transport_status=transport,
        adapter_harness=adapter,
    )
    assert report["handoff_state"] == "blocked_manual_review"
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["OA-HANDOFF-003"]["passed"] is False
    assert gates["OA-HANDOFF-010"]["passed"] is False
    assert report["dry_run_handoff_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v121_paper_execution_loop_gate_summarizes_shadow_lifecycle_without_routing():
    response = client.get("/api/v1/jarvis/paper-execution-loop/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["paper_loop_version"] == "jarvis-paper-execution-loop-gate.v1.21"
    assert report["symbol"] == "RELIANCE"
    assert report["loop_state"] in {"paper_loop_ready", "blocked_by_safety", "manual_review_required"}
    assert report["paper_intent_lifecycle"]["version"] == "execution-intent-paper-safety-memory.v0.83"
    assert report["paper_intent_lifecycle"]["current_state"] == "MANUAL_REVIEW_REQUIRED"
    assert report["paper_intent_lifecycle"]["manual_review_required"] is True
    assert report["shadow_lifecycle"]["version"] == "behavior-trade-lifecycle-simulation.v0.36"
    assert report["shadow_lifecycle"]["trade_state_path"]
    assert report["scenario_evidence_summary"]["comparison_version"] == "behavior-lifecycle-scenario-comparison.v0.37"
    assert report["scenario_evidence_summary"]["evidence_version"] == "behavior-lifecycle-evidence-drilldown.v0.38"
    assert report["tradeability_summary"]["promotion_allowed"] is False
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["PAPER-LOOP-001"]["passed"] is True
    assert gates["PAPER-LOOP-002"]["passed"] is True
    assert gates["PAPER-LOOP-003"]["passed"] is True
    assert gates["PAPER-LOOP-004"]["passed"] is True
    assert gates["PAPER-LOOP-011"]["passed"] is True
    assert report["external_executor_handoff_allowed"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["broker_order_created"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False


def test_v121_paper_execution_loop_gate_rejects_unsafe_lifecycle_module_contract():
    from app.behavior.jarvis_paper_execution_loop import build_paper_execution_loop_report

    paper = {
        "paper_safety_version": "execution-intent-paper-safety-memory.v0.83",
        "intent_lifecycle": {"current_state": "MANUAL_REVIEW_REQUIRED", "manual_review_required": True},
        "all_execution_outputs_labeled_simulation_estimate": True,
        "manual_review_required_for_executor_handoff": True,
        "broker_credentials_present": False,
        "broker_order_created": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    lifecycle = {
        "lifecycle_version": "behavior-trade-lifecycle-simulation.v0.36",
        "simulation_only": False,
        "trade_allowed": True,
        "order_routing_enabled": True,
        "live_trading_blocked": False,
        "deterministic": True,
        "no_future_leakage": True,
    }
    comparison = {"comparison_version": "behavior-lifecycle-scenario-comparison.v0.37", "all_order_routing_disabled": True, "all_live_trading_blocked": True}
    evidence = {"evidence_version": "behavior-lifecycle-evidence-drilldown.v0.38"}
    guidance = {"guidance_version": "behavior-lifecycle-tradeability-guidance.v0.39", "promotion_allowed": False, "trade_allowed": False, "order_routing_enabled": False, "live_trading_blocked": True}
    report = build_paper_execution_loop_report(
        symbol="TV121",
        jarvis_room={"trade_allowed": False, "order_routing_enabled": False, "trade_vision_decision": {"final_trade_decision": "WAIT"}, "safety_summary": {"blocking_gates": []}},
        paper_safety=paper,
        lifecycle=lifecycle,
        lifecycle_comparison=comparison,
        lifecycle_evidence=evidence,
        tradeability=guidance,
    )
    assert report["loop_state"] == "blocked_by_safety"
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["PAPER-LOOP-005"]["passed"] is False
    assert gates["PAPER-LOOP-011"]["passed"] is False
    assert report["paper_loop_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v122_decision_quality_gate_detects_stale_low_evidence_and_blocks_routing():
    response = client.get("/api/v1/jarvis/decision-quality-gate/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["quality_gate_version"] == "jarvis-decision-quality-gate.v1.22"
    assert report["symbol"] == "RELIANCE"
    assert report["quality_state"] in {"research_review_ready", "manual_review_required", "display_blocked"}
    assert report["external_ai_quality"]["reliability_version"] == "jarvis-external-ai-consensus-reliability.v1.07"
    assert report["verified_evidence_quality"]["certificate_version"] == "jarvis-verified-evidence-certificate.v1.08"
    assert report["daily_data_quality"]["authority_version"] == "jarvis-daily-verified-authority.v1.15"
    assert report["paper_loop_quality"]["paper_loop_version"] == "jarvis-paper-execution-loop-gate.v1.21"
    assert report["openalgo_handoff_quality"]["handoff_gate_version"] == "jarvis-openalgo-handoff-gate.v1.20"
    flag_ids = {flag["flag_id"] for flag in report["quality_flags"]}
    assert "low_evidence" in flag_ids
    assert flag_ids.intersection({"stale_review_history", "daily_authority_not_verified", "unverified_daily_claim", "disagreement"})
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["QUAL-001"]["passed"] is True
    assert gates["QUAL-003"]["passed"] is True
    assert gates["QUAL-008"]["passed"] is True
    assert gates["QUAL-009"]["passed"] is True
    assert gates["QUAL-010"]["passed"] is True
    assert gates["QUAL-011"]["passed"] is True
    assert report["decision_trust_allowed"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["broker_order_created"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False


def test_v122_decision_quality_gate_blocks_unverified_daily_claim_and_unexpected_routes():
    from app.behavior.jarvis_decision_quality_gate import build_decision_quality_gate_report

    report = build_decision_quality_gate_report(
        symbol="TV122",
        jarvis_room={"trade_allowed": True, "order_routing_enabled": True, "trade_vision_decision": {"final_trade_decision": "BUY"}},
        external_ai_reliability={
            "reliability_version": "jarvis-external-ai-consensus-reliability.v1.07",
            "disagreement_detected": True,
            "low_evidence_detected": True,
            "stale_review_history": True,
            "record_count": 2,
        },
        verified_evidence={
            "certificate_version": "jarvis-verified-evidence-certificate.v1.08",
            "certificate_state": "blocked",
            "external_ai_blocked_claims": [{"claim_id": "BLOCKED-DAILY-CLAIM"}],
            "external_ai_missed_items": [{"item_id": "EXTAI-MISS-EVIDENCE"}],
            "daily_data_authority": {"daily_claim_requires_citation": True},
        },
        daily_authority={
            "authority_version": "jarvis-daily-verified-authority.v1.15",
            "authority_state": "blocked",
            "daily_available": False,
            "weekly_available": False,
            "operator_message": "Daily data missing.",
        },
        paper_execution_loop={
            "paper_loop_version": "jarvis-paper-execution-loop-gate.v1.21",
            "external_executor_handoff_allowed": True,
            "trade_allowed": True,
            "order_routing_enabled": True,
            "live_trading_blocked": False,
        },
        openalgo_handoff_gate={
            "handoff_gate_version": "jarvis-openalgo-handoff-gate.v1.20",
            "automatic_delivery_allowed": True,
            "order_routing_enabled": True,
            "live_trading_blocked": False,
        },
    )
    assert report["quality_state"] == "display_blocked"
    flag_ids = {flag["flag_id"] for flag in report["quality_flags"]}
    assert {"disagreement", "low_evidence", "stale_review_history", "unverified_daily_claim", "paper_loop_handoff_unexpected", "openalgo_auto_delivery_unexpected"}.issubset(flag_ids)
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["QUAL-002"]["passed"] is False
    assert gates["QUAL-009"]["passed"] is False
    assert gates["QUAL-011"]["passed"] is False
    assert gates["QUAL-012"]["passed"] is False
    assert report["review_display_allowed"] is False
    assert report["external_ai_display_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v123_trading_decision_output_summarizes_chart_memory_plan_and_blocks_execution():
    response = client.get("/api/v1/jarvis/trading-decision-output/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["output_version"] == "jarvis-trading-decision-output.v1.23"
    assert report["symbol"] == "RELIANCE"
    assert report["output_state"] in {"blocked_show_safe_evidence_only", "watch_or_no_trade", "manual_review_required", "research_decision_output_ready"}
    assert report["headline"]
    assert report["chart_screen_focus"]["display_bars_available"] > 0
    assert report["chart_screen_focus"]["show_wait_zone"] is True
    assert "candle_pattern" in report["pattern_now"]
    assert "wick_body_read" in report["pattern_now"]
    assert report["trade_plan"]["entry_type"] == "wait_for_value_reach_then_retest_confirmation"
    assert isinstance(report["trade_plan"]["entry_zone"], list)
    assert report["trade_plan"]["plan_is_research_only"] is True
    evidence_ids = {row["row_id"] for row in report["indicator_and_candle_evidence"]}
    assert {"candle_body_wick", "vwap", "ema", "rsi", "macd", "volume", "levels", "indicator_sequence", "candle_cause_effect"}.issubset(evidence_ids)
    assert isinstance(report["similar_history_cases"], list)
    assert "interpretation" in report["sequential_signal_story"]
    assert report["quality_and_safety"]["quality_gate_version"] == "jarvis-decision-quality-gate.v1.22"
    assert report["quality_and_safety"]["decision_trust_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["broker_order_created"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_export_to_openalgo"] is False


def test_v123_trading_decision_output_direct_builder_preserves_no_trade_blocks():
    from app.behavior.jarvis_trading_decision_output import build_trading_decision_output_report

    room = {
        "symbol": "TV123",
        "timeframe": "1m",
        "chart_context": {"bar_count": 2, "latest_close": 100.5, "bars": [{"close": 100.0}, {"close": 100.5}]},
        "candle_structure": {"pattern": "upper_wick_rejection", "body_pct": 30.0, "upper_wick_pct": 55.0, "lower_wick_pct": 15.0},
        "indicator_snapshot": {"vwap_position": "below_vwap", "ema_state": "bearish", "macd_state": "negative", "rsi14": 42, "volume_z": 1.2, "vwap": 101, "ema9": 100, "ema21": 101, "macd_value": -0.2},
        "levels_and_zones": {"nearest_support": 99.5, "nearest_resistance": 101.2},
        "similar_history": {"matches": [{"start_timestamp_ns": 1714724800000000000, "similarity_score_pct": 88.0, "outcome": "reversal"}]},
        "trade_vision_decision": {
            "final_trade_decision": "NO_TRADE",
            "scenario_label": "wick rejection below VWAP",
            "scenario_bias": "bearish_rejection",
            "entry_condition": "Wait for reclaim.",
            "best_entry_zone": [100.8, 101.0],
            "stop_loss": 99.0,
            "target": 104.0,
            "invalidation_level": 101.2,
            "risk_reward": 3.0,
            "confidence_cap_pct": 45,
            "wait_for": ["VWAP reclaim"],
            "avoid_if": ["Daily resistance rejection"],
            "no_trade_reason": "Rejection and quality gate block action.",
        },
    }
    report = build_trading_decision_output_report(
        symbol="TV123",
        jarvis_room=room,
        indicator_memory={"sequence_memory": {"interpretation": "RSI -> MACD offset sequence"}, "evidence_quality": "LOW", "best_matching_dates": ["2026-01-01"], "non_same_candle_sequence_detected": True},
        candle_memory={"effect_label": "upper_wick_rejection_followed_by_bearish_effect", "evidence_quality": "MEDIUM", "analog_examples": [{"historical_date": "2026-01-02", "similarity_score_pct": 77, "outcome": "reversal", "previous_direction": "bullish", "current_direction": "bearish", "next_direction": "bearish"}]},
        decision_quality_gate={"quality_gate_version": "jarvis-decision-quality-gate.v1.22", "quality_state": "display_blocked", "quality_flags": [{"flag_id": "low_evidence", "severity": "downgrade", "name": "Low evidence", "repair": "More replay"}]},
    )
    assert report["output_state"] == "blocked_show_safe_evidence_only"
    assert report["trade_plan"]["display_action"] == "WAIT"
    assert report["pattern_now"]["wick_body_read"].startswith("Upper-wick rejection")
    assert len(report["similar_history_cases"]) >= 3
    assert report["quality_and_safety"]["trade_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v124_chart_overlay_contract_exposes_entry_stop_target_invalidation_and_markers():
    response = client.get("/api/v1/jarvis/trading-decision-output/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    focus = report["chart_screen_focus"]
    plan = report["trade_plan"]
    assert focus["overlay_entry_zone"] == plan["entry_zone"]
    assert focus["overlay_stop_loss"] == plan["stop_loss"]
    assert focus["overlay_target"] == plan["target"]
    assert focus["overlay_invalidation_level"] == plan["invalidation_level"]
    assert focus["show_wait_zone"] is True
    assert focus["show_safety_banner"] is True
    assert "show_similar_markers" in focus
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v125_chart_overlay_qa_contract_passes_core_overlay_checks():
    response = client.get("/api/v1/jarvis/chart-overlay-qa/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["qa_version"] == "jarvis-chart-overlay-qa.v1.25"
    assert report["symbol"] == "RELIANCE"
    assert report["qa_state"] in {"passed", "warning"}
    assert report["chart_nonblank"] is True
    assert report["bar_count"] > 0
    labels = {label["label"]: label for label in report["overlay_labels"]}
    assert labels["Entry"]["visible"] is True
    assert labels["SL"]["visible"] is True
    assert labels["Target"]["visible"] is True
    assert labels["Invalid"]["visible"] is True
    assert labels["VWAP"]["visible"] is True
    hooks = report["frontend_test_hooks"]
    assert hooks["chart_root"] == "jarvis-decision-chart"
    assert hooks["entry_zone"] == "jarvis-chart-entry-zone"
    assert hooks["stop_line"] == "jarvis-chart-stop-line"
    assert hooks["target_line"] == "jarvis-chart-target-line"
    assert hooks["invalidation_line"] == "jarvis-chart-invalidation-line"
    assert hooks["vwap_line"] == "jarvis-chart-vwap-line"
    checks = {check["check_id"]: check for check in report["checks"]}
    for check_id in ["CHART-QA-001", "CHART-QA-002", "CHART-QA-003", "CHART-QA-004", "CHART-QA-005", "CHART-QA-007", "CHART-QA-010"]:
        assert checks[check_id]["passed"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v125_chart_overlay_qa_direct_builder_blocks_missing_core_levels():
    from app.behavior.jarvis_chart_overlay_qa import build_chart_overlay_qa_report

    report = build_chart_overlay_qa_report(
        symbol="TV125",
        jarvis_room={"timeframe": "1m", "chart_context": {"bars": [{"open": 1, "high": 2, "low": 1, "close": 2}], "overlays": {}}},
        trading_decision_output={
            "chart_screen_focus": {"overlay_entry_zone": [1.1, 1.2], "overlay_target": 2.0},
            "similar_history_cases": [],
            "blocker_rows": [],
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
    )
    assert report["qa_state"] == "failed"
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["CHART-QA-003"]["passed"] is False
    assert checks["CHART-QA-005"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v126_jarvis_evidence_assembly_bundle_preserves_all_downstream_artifacts():
    from app.main import _build_jarvis_evidence_bundle_for_endpoint

    bundle = _build_jarvis_evidence_bundle_for_endpoint("RELIANCE", "1m", 390, "tail", 900)
    assert bundle["assembly_version"] == "jarvis-evidence-assembly.v1.26"
    assert bundle["symbol"] == "RELIANCE"
    assert bundle["room"]["symbol"] == "RELIANCE"
    assert bundle["paper_loop"]["paper_loop_version"] == "jarvis-paper-execution-loop-gate.v1.21"
    assert bundle["openalgo_handoff"]["handoff_gate_version"] == "jarvis-openalgo-handoff-gate.v1.20"
    assert bundle["decision_quality"]["quality_gate_version"] == "jarvis-decision-quality-gate.v1.22"
    assert bundle["trading_decision_output"]["output_version"] == "jarvis-trading-decision-output.v1.23"
    assert bundle["chart_overlay_qa"]["qa_version"] == "jarvis-chart-overlay-qa.v1.25"
    assert bundle["indicator_memory"]["memory_version"] == "jarvis-indicator-combination-memory.v1.16"
    assert bundle["candle_memory"]["memory_version"] == "jarvis-candle-cause-effect-memory.v1.17"
    assert bundle["verified_evidence"]["certificate_version"] == "jarvis-verified-evidence-certificate.v1.08"
    assert bundle["daily_authority"]["authority_version"] == "jarvis-daily-verified-authority.v1.15"
    assert bundle["stage_timings"]
    assert bundle["total_latency_ms"] >= 0
    assert bundle["total_budget_ms"] == 1500.0
    assert bundle["trade_allowed"] is False
    assert bundle["order_routing_enabled"] is False
    assert bundle["live_trading_blocked"] is True


def test_v126_migrated_jarvis_endpoints_use_shared_evidence_assembly_helper():
    import inspect
    import app.main as main

    for endpoint in [main.jarvis_decision_quality_gate, main.jarvis_trading_decision_output, main.jarvis_chart_overlay_qa]:
        source = inspect.getsource(endpoint)
        assert "_build_jarvis_evidence_bundle_for_endpoint" in source
        assert "build_paper_execution_loop_report(" not in source
        assert "build_openalgo_handoff_gate_report(" not in source
    helper_source = inspect.getsource(main._build_jarvis_evidence_bundle_for_endpoint)
    assert "build_jarvis_evidence_bundle(" in helper_source


def test_v127_evidence_latency_budget_endpoint_reports_safe_stage_timings():
    response = client.get("/api/v1/jarvis/evidence-latency-budget/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["latency_budget_version"] == "jarvis-latency-budget.v1.27"
    assert report["assembly_version"] == "jarvis-evidence-assembly.v1.26"
    assert report["symbol"] == "RELIANCE"
    assert report["budget_state"] in {"within_budget", "warning", "over_budget"}
    assert report["total_latency_ms"] >= 0
    assert report["total_budget_ms"] == 1500.0
    stages = {item["stage"]: item for item in report["stage_timings"]}
    for expected in ["decision_room", "indicator_memory", "candle_memory", "decision_quality", "trading_decision_output", "chart_overlay_qa"]:
        assert expected in stages
        assert stages[expected]["elapsed_ms"] >= 0
        assert stages[expected]["budget_ms"] > 0
        assert stages[expected]["status"] in {"within_budget", "warning", "over_budget"}
    assert report["fast_path_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v127_latency_budget_direct_builder_marks_over_budget_and_recommends_degradation():
    from app.behavior.jarvis_latency_budget import build_jarvis_latency_budget_report

    report = build_jarvis_latency_budget_report(
        {
            "assembly_version": "jarvis-evidence-assembly.v1.26",
            "symbol": "TV127",
            "timeframe": "1m",
            "total_latency_ms": 1800.0,
            "total_budget_ms": 1500.0,
            "stage_timings": [
                {"stage": "decision_room", "elapsed_ms": 500.0, "budget_ms": 220.0, "status": "over_budget"},
                {"stage": "chart_overlay_qa", "elapsed_ms": 10.0, "budget_ms": 70.0, "status": "within_budget"},
            ],
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    )
    assert report["latency_budget_version"] == "jarvis-latency-budget.v1.27"
    assert report["budget_state"] == "over_budget"
    assert report["slow_stage_count"] == 1
    assert report["degradation_recommendations"][0]["stage"] == "decision_room"
    assert "Cache imported candle snapshots" in report["degradation_recommendations"][0]["recommendation"]
    assert report["fast_path_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v128_jarvis_evidence_cache_returns_miss_then_hit_and_keeps_safety_locked():
    from app.behavior.jarvis_evidence_cache import clear_jarvis_evidence_cache

    clear_jarvis_evidence_cache()
    first = client.get("/api/v1/jarvis/evidence-cache/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert first.status_code == 200
    first_report = first.json()["data"]
    assert first_report["cache_version"] == "jarvis-evidence-cache.v1.28"
    assert first_report["cache_status"] == "miss"
    assert first_report["cache_fresh"] is True
    assert first_report["trade_allowed"] is False
    assert first_report["order_routing_enabled"] is False
    assert first_report["live_trading_blocked"] is True

    second = client.get("/api/v1/jarvis/evidence-cache/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert second.status_code == 200
    second_report = second.json()["data"]
    assert second_report["cache_status"] == "hit"
    assert second_report["cache_key_hash"] == first_report["cache_key_hash"]
    assert second_report["cache_age_seconds"] >= 0
    assert second_report["cache_ttl_seconds"] == 15.0
    assert second_report["cache_fresh"] is True
    assert second_report["trade_allowed"] is False
    assert second_report["order_routing_enabled"] is False
    assert second_report["live_trading_blocked"] is True


def test_v128_latency_budget_exposes_cache_freshness_metadata():
    from app.behavior.jarvis_evidence_cache import clear_jarvis_evidence_cache

    clear_jarvis_evidence_cache()
    client.get("/api/v1/jarvis/evidence-cache/RELIANCE?timeframe=1m&rows=390&position=tail")
    response = client.get("/api/v1/jarvis/evidence-latency-budget/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["latency_budget_version"] == "jarvis-latency-budget.v1.27"
    assert report["cache_status"] == "hit"
    assert report["cache_fresh"] is True
    assert report["cache_age_seconds"] >= 0
    assert report["cache_ttl_seconds"] == 15.0
    assert report["fast_path_safe"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v129_realtime_freshness_endpoint_forces_wait_on_latency_or_staleness():
    from app.behavior.jarvis_evidence_cache import clear_jarvis_evidence_cache

    clear_jarvis_evidence_cache()
    response = client.get("/api/v1/jarvis/realtime-freshness/RELIANCE?timeframe=1m&rows=390&position=tail&max_age_seconds=10")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["freshness_version"] == "jarvis-realtime-freshness.v1.29"
    assert report["freshness_state"] in {"fresh", "aging", "stale"}
    assert report["safe_display_action"] in {"RESEARCH_ONLY", "WAIT"}
    assert report["cache_status"] in {"miss", "hit"}
    assert report["cache_age_seconds"] >= 0
    assert report["max_age_seconds"] == 10.0
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    if report["freshness_state"] != "fresh" or report["latency_state"] in {"warning", "over_budget"}:
        assert report["force_wait"] is True
        assert report["safe_display_action"] == "WAIT"


def test_v129_realtime_freshness_direct_builder_blocks_stale_cached_evidence():
    from app.behavior.jarvis_realtime_freshness import build_realtime_freshness_report

    report = build_realtime_freshness_report(
        bundle={
            "assembly_version": "jarvis-evidence-assembly.v1.26",
            "symbol": "TV129",
            "timeframe": "1m",
            "cache": {
                "cache_status": "hit",
                "cache_age_seconds": 31.0,
                "cache_ttl_seconds": 15.0,
                "cache_fresh": False,
            },
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        latency_budget={"latency_budget_version": "jarvis-latency-budget.v1.27", "budget_state": "within_budget"},
        max_age_seconds=10.0,
    )
    assert report["freshness_version"] == "jarvis-realtime-freshness.v1.29"
    assert report["freshness_state"] == "stale"
    assert report["safe_display_action"] == "WAIT"
    assert report["trust_effect"] == "block_confidence"
    assert report["evidence_stale"] is True
    assert report["refresh_required"] is True
    assert report["force_wait"] is True
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["FRESH-002"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v130_gemini_decision_room_unifies_review_and_keeps_display_only():
    from app.behavior.jarvis_evidence_cache import clear_jarvis_evidence_cache

    clear_jarvis_evidence_cache()
    response = client.get("/api/v1/jarvis/gemini/decision-room/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["decision_room_version"] == "jarvis-gemini-decision-room.v1.30"
    assert report["symbol"] == "RELIANCE"
    assert report["fallback_key_slots_supported"] == 5
    assert report["dry_run_only"] is True
    assert report["network_call_allowed"] is False
    assert report["live_call_performed"] is False
    assert report["redaction_count"] >= 0
    assert report["confidence_boost_allowed"] is False
    assert report["gemini_can_execute_orders"] is False
    assert report["gemini_can_override_no_trade"] is False
    assert report["gemini_can_override_risk"] is False
    assert report["safe_final_action"] in {"TRADE_VISION_ONLY", "WAIT", "NO_TRADE", "WATCH_ONLY"}
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["GDR-001"]["passed"] is True
    assert gates["GDR-003"]["passed"] is True
    assert gates["GDR-006"]["passed"] is True


def test_v130_gemini_decision_room_direct_builder_downgrades_stale_or_unready_review():
    from app.behavior.jarvis_gemini_decision_room import build_gemini_decision_room_report

    report = build_gemini_decision_room_report(
        symbol="TV130",
        provider_status={
            "status": "unavailable",
            "mode": "live_disabled_safe_stub",
            "configured_key_slots": 0,
            "fallback_key_slots_supported": 5,
            "selected_model": "gemini-1.5-pro",
            "review_schema_version": "jarvis-gemini-review-schema.v0.90",
            "security": {"backend_only_keys": True},
            "can_execute_orders": False,
            "can_override_no_trade": False,
            "can_override_risk": False,
        },
        outbound_bundle={
            "request_hash": "abc",
            "evidence_packet_hash": "def",
            "dry_run_only": True,
            "network_call_allowed": False,
            "live_call_performed": False,
            "sanitization": {"redaction_count": 0, "secrets_included": False},
            "can_execute_orders": False,
            "can_override_no_trade": False,
            "can_override_risk": False,
            "order_routing_enabled": False,
        },
        sample_review={
            "display_allowed": True,
            "display_status": "validated_sample",
            "safe_final_action": "WATCH_ONLY",
            "validation": {"accepted_for_display": True},
            "can_execute_orders": False,
            "can_override_no_trade": False,
            "can_override_risk": False,
        },
        realtime_freshness={"freshness_state": "stale", "force_wait": True, "safe_display_action": "WAIT"},
        decision_quality={"quality_state": "manual_review_required", "manual_review_required": True},
        trading_decision_output={"output_state": "watch_or_no_trade", "trade_plan": {"display_action": "WAIT"}},
    )
    assert report["decision_room_version"] == "jarvis-gemini-decision-room.v1.30"
    assert report["safe_final_action"] == "WAIT"
    assert report["review_display_allowed"] is True
    assert report["freshness_state"] == "stale"
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v131_openalgo_paper_bridge_hardening_endpoint_blocks_live_execution():
    from app.behavior.jarvis_evidence_cache import clear_jarvis_evidence_cache

    clear_jarvis_evidence_cache()
    response = client.get("/api/v1/jarvis/openalgo/paper-bridge/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["bridge_version"] == "jarvis-openalgo-paper-bridge-hardening.v1.31"
    assert report["symbol"] == "RELIANCE"
    assert report["safe_external_scope"] == "paper_or_sim_review_only"
    assert report["openalgo_may_execute"] is False
    assert report["trading_bot_may_execute"] is False
    assert report["live_intent_allowed"] is False
    assert report["external_approval_required"] is True
    assert report["external_risk_check_required"] is True
    assert report["external_account_state_required"] is True
    assert report["manual_operator_review_required"] is True
    assert len(report["required_external_executor_checks"]) >= 8
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["OA-BRIDGE-002"]["passed"] is True
    assert gates["OA-BRIDGE-006"]["passed"] is True
    assert gates["OA-BRIDGE-008"]["passed"] is True


def test_v131_openalgo_paper_bridge_direct_builder_rejects_unsafe_live_flags():
    from app.behavior.jarvis_openalgo_paper_bridge import build_openalgo_paper_bridge_report

    report = build_openalgo_paper_bridge_report(
        symbol="TV131",
        handoff_gate={
            "handoff_hash": "abc",
            "intent_summary": {
                "intent_signature": "sig",
                "duplicate_key": "dup",
                "valid_until": "later",
                "expired": False,
                "export_allowed": True,
                "broker_order_created": False,
                "order_routing_enabled": True,
                "live_trading_blocked": False,
            },
            "package_summary": {"dry_run_only": True, "package_hash": "pkg", "live_trading_blocked": False},
            "package_verification": {"verified": True},
            "transport_summary": {"order_routing_enabled": False, "live_trading_blocked": True},
            "bot_handoff_verification": {"rejected": True},
            "live_trading_blocked": True,
        },
        decision_quality={"order_routing_enabled": False, "live_trading_blocked": True},
        realtime_freshness={"safe_display_action": "WAIT"},
        gemini_decision_room={"confidence_boost_allowed": False, "order_routing_enabled": False},
    )
    assert report["bridge_version"] == "jarvis-openalgo-paper-bridge-hardening.v1.31"
    assert report["bridge_state"] == "blocked"
    assert report["openalgo_may_inspect"] is False
    assert report["openalgo_may_execute"] is False
    assert report["live_intent_allowed"] is False
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["OA-BRIDGE-002"]["passed"] is False
    assert gates["OA-BRIDGE-008"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v132_final_production_audit_endpoint_blocks_live_and_reports_go_no_go():
    from app.behavior.jarvis_evidence_cache import clear_jarvis_evidence_cache

    clear_jarvis_evidence_cache()
    response = client.get("/api/v1/jarvis/final-production-audit/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["audit_version"] == "jarvis-final-production-readiness-audit.v1.32"
    assert report["symbol"] == "RELIANCE"
    assert report["current_safe_scope"] == "research_and_paper_sim_review_only"
    assert report["live_ready"] is False
    assert report["broker_connection_ready"] is False
    assert report["autonomous_execution_ready"] is False
    assert report["go_no_go"]["live_broker_trading"] == "NO_GO"
    assert report["go_no_go"]["autonomous_bot_execution"] == "NO_GO"
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["FINAL-004"]["passed"] is True
    assert gates["FINAL-005"]["passed"] is True
    assert gates["FINAL-009"]["passed"] is True
    assert gates["FINAL-010"]["passed"] is True
    assert report["live_blockers"]


def test_v132_final_production_audit_direct_builder_fails_unsafe_live_flag():
    from app.behavior.jarvis_final_production_audit import build_jarvis_final_production_audit

    report = build_jarvis_final_production_audit(
        symbol="TV132",
        final_release_audit={"fail_count": 0, "live_trading_blocked": True, "order_routing_enabled": False},
        deployment_readiness={"ready": True, "live_trading_blocked": True, "order_routing_enabled": False, "broker_credentials_present": False, "broker_order_created": False},
        realtime_freshness={"safe_display_action": "RESEARCH_ONLY", "live_trading_blocked": True, "order_routing_enabled": False},
        gemini_decision_room={
            "network_call_allowed": False,
            "live_call_performed": False,
            "confidence_boost_allowed": False,
            "gemini_can_execute_orders": False,
            "gemini_can_override_no_trade": False,
            "gemini_can_override_risk": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        openalgo_paper_bridge={
            "safe_external_scope": "paper_or_sim_review_only",
            "openalgo_may_inspect": True,
            "openalgo_may_execute": False,
            "trading_bot_may_execute": False,
            "paper_intent_allowed": True,
            "live_intent_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        decision_quality={"order_routing_enabled": False, "live_trading_blocked": True},
        trading_decision_output={"trade_allowed": False, "order_routing_enabled": True, "live_trading_blocked": False},
        chart_overlay_qa={"qa_state": "passed", "live_trading_blocked": True, "order_routing_enabled": False},
    )
    assert report["audit_version"] == "jarvis-final-production-readiness-audit.v1.32"
    assert report["overall_state"] == "blocked"
    assert report["live_ready"] is False
    assert report["go_no_go"]["live_broker_trading"] == "NO_GO"
    gates = {gate["gate_id"]: gate for gate in report["gates"]}
    assert gates["FINAL-007"]["passed"] is False
    assert gates["FINAL-009"]["passed"] is False
    assert gates["FINAL-010"]["passed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v133_readiness_remediation_endpoint_explains_blockers_without_live_trading():
    response = client.get("/api/v1/jarvis/readiness-remediation/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["remediation_version"] == "jarvis-readiness-remediation.v1.33"
    assert isinstance(report["remediation_steps"], list)
    assert report["safe_to_apply_without_live_trading"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_execute_orders"] is False
    assert report["can_export_to_openalgo"] is False
    assert report["can_override_no_trade"] is False
    assert report["can_override_risk"] is False


def test_v133_readiness_remediation_direct_builder_maps_adapter_security_failures():
    from app.behavior.jarvis_readiness_remediation import build_readiness_remediation_report

    report = build_readiness_remediation_report(
        deployment_readiness={
            "ready": False,
            "checks": [
                {"check_id": "adapter_config", "name": "Adapter configured", "status": "fail", "evidence": "configured=False"},
                {"check_id": "adapter_auth", "name": "Adapter service identity", "status": "fail", "evidence": "configured=False"},
                {"check_id": "security", "name": "Transport security posture", "status": "fail", "evidence": "status=fail"},
            ],
        },
        final_release_audit={
            "production_research_release_candidate": False,
            "gates": [
                {"gate_id": "deployment", "name": "Deployment readiness", "status": "fail", "evidence": "4 fail"},
                {"gate_id": "smoke", "name": "Deployment smoke", "status": "fail", "evidence": "3/4"},
            ],
        },
        jarvis_final_audit={"overall_state": "blocked", "research_ready": False, "paper_sim_ready": False},
    )
    assert report["remediation_version"] == "jarvis-readiness-remediation.v1.33"
    ids = {item["remediation_id"] for item in report["remediation_steps"]}
    assert {"adapter_config", "adapter_auth", "security", "deployment", "smoke"}.issubset(ids)
    assert all(item["requires_code_change"] is False for item in report["remediation_steps"])
    assert all(item["live_trading_must_remain_blocked"] is True for item in report["remediation_steps"])
    assert report["ready_after_operator_config"] is True
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v134_ai_credential_vault_locked_blocks_secret_save(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADEVISION_SECRET_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_AI_CREDENTIAL_VAULT_PATH", str(tmp_path / "ai_credentials.enc"))
    monkeypatch.setenv("TRADEVISION_SECRET_KEY_FILE", str(tmp_path / "missing_secret.key"))

    status_response = client.get("/api/v1/ai/credentials/status")
    assert status_response.status_code == 200
    status = status_response.json()["data"]
    assert status["vault_version"] == "ai-credentials-vault.v1.34"
    assert status["vault_locked"] is True
    assert status["gemini"]["configured_slots"] == 0
    assert status["grok"]["configured"] is False
    assert status["security"]["frontend_receives_plaintext_secret"] is False
    assert status["security"]["browser_password_login_supported"] is False
    assert status["trade_allowed"] is False
    assert status["order_routing_enabled"] is False
    assert status["live_trading_blocked"] is True

    save_response = client.post("/api/v1/ai/credentials/grok", json={"api_key": "xai_test_key_123456"})
    assert save_response.status_code == 400
    assert save_response.json()["error"]["code"] == "ai_credential_save_failed"


def test_v134_ai_credential_vault_uses_local_secret_key_file(monkeypatch, tmp_path):
    key_path = tmp_path / "tradevision_secret.key"
    key_path.write_text("unit-test-file-secret-key", encoding="utf-8")
    monkeypatch.delenv("TRADEVISION_SECRET_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_AI_CREDENTIAL_VAULT_PATH", str(tmp_path / "ai_credentials.enc"))
    monkeypatch.setenv("TRADEVISION_SECRET_KEY_FILE", str(key_path))

    response = client.post("/api/v1/ai/credentials/grok", json={"api_key": "xai_file_secret_key_123456"})
    assert response.status_code == 200
    status = response.json()["data"]
    assert status["vault_locked"] is False
    assert status["secret_key_source"] == "TRADEVISION_SECRET_KEY_FILE"
    assert status["secret_key_file_exists"] is True
    assert status["grok"]["configured"] is True
    assert "xai_file_secret_key_123456" not in json.dumps(status)


def test_v134_ai_credential_vault_saves_masked_gemini_and_grok(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADEVISION_SECRET_KEY", "unit-test-local-secret-key")
    monkeypatch.setenv("TRADEVISION_AI_CREDENTIAL_VAULT_PATH", str(tmp_path / "ai_credentials.enc"))
    monkeypatch.setenv("TRADEVISION_SECRET_KEY_FILE", str(tmp_path / "ignored_secret.key"))

    gemini_response = client.post(
        "/api/v1/ai/credentials/gemini",
        json={"slot": 2, "api_key": "gemini_unit_test_key_abcdef"},
    )
    assert gemini_response.status_code == 200
    gemini = gemini_response.json()["data"]
    assert gemini["vault_locked"] is False
    assert gemini["gemini"]["configured_slots"] == 1
    assert gemini["gemini"]["active_slot"] == 2
    assert gemini["gemini"]["slots"][1]["display"] == "****cdef"
    assert gemini["gemini"]["slots"][1]["secret_returned_to_frontend"] is False
    assert "gemini_unit_test_key_abcdef" not in json.dumps(gemini)

    grok_response = client.post(
        "/api/v1/ai/credentials/grok",
        json={"api_key": "xai_unit_test_key_987654"},
    )
    assert grok_response.status_code == 200
    grok = grok_response.json()["data"]
    assert grok["grok"]["configured"] is True
    assert grok["grok"]["display"] == "****7654"
    assert grok["security"]["cookie_or_session_capture_supported"] is False
    assert "xai_unit_test_key_987654" not in json.dumps(grok)

    test_response = client.post("/api/v1/ai/credentials/test-grok", json={})
    assert test_response.status_code == 200
    test = test_response.json()["data"]
    assert test["test_version"] == "ai-credentials-vault.v1.34.test-stub"
    assert test["configured"] is True
    assert test["live_network_call_performed"] is False
    assert test["order_routing_enabled"] is False


def test_v135_gemini_live_review_disabled_is_trade_vision_only(monkeypatch):
    from app.behavior import gemini_provider

    monkeypatch.delenv("TRADEVISION_GEMINI_ENABLE_LIVE", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_1", raising=False)
    evidence = {
        "trade_vision_decision": {"final_trade_decision": "WAIT"},
        "indicator_snapshot": {"rsi14": 44, "vwap_position": "below_vwap"},
        "safety_summary": {"blocking_gates": []},
    }
    report = asyncio.run(gemini_provider.build_gemini_live_review_report(evidence_packet=evidence, execute=True))
    assert report["live_review_version"] == "jarvis-gemini-live-review.v1.35"
    assert report["live_call_allowed"] is False
    assert report["live_call_performed"] is False
    assert report["safe_final_action"] == "TRADE_VISION_ONLY"
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_execute_orders"] is False
    assert report["can_override_no_trade"] is False
    assert "GEMINI_API_KEY" not in json.dumps(report)


def test_v135_gemini_live_review_uses_fallback_slot_and_validates_response(monkeypatch):
    from app.behavior import gemini_provider

    monkeypatch.setenv("TRADEVISION_GEMINI_ENABLE_LIVE", "true")
    monkeypatch.setenv("GEMINI_API_KEY_1", "gemini_unit_test_key_slot_1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "gemini_unit_test_key_slot_2")

    async def fake_call(*, api_key, slot, evidence_packet, provider_status):
        if slot == 1:
            return {"slot": slot, "performed": True, "success": False, "status_code": 429, "error_message": "quota", "latency_ms": 3}
        return {
            "slot": slot,
            "performed": True,
            "success": True,
            "status_code": 200,
            "latency_ms": 4,
            "candidate_response": {
                "review_status": "valid",
                "agrees_with_trade_vision": True,
                "pattern_interpretation": "Below-VWAP wait structure.",
                "entry_guidance": "Wait for VWAP reclaim.",
                "risk_warning": "Do not trade while below VWAP.",
                "best_indicator_for_pattern": ["vwap_position", "rsi14"],
                "avoid_if": ["price remains below VWAP"],
                "confidence_comment": "External AI cannot boost confidence.",
                "final_action": "WAIT",
                "cited_evidence_keys": ["indicator_snapshot", "vwap_position", "rsi14", "safety_summary"],
            },
            "raw_text_preview": "{\"final_action\":\"WAIT\"}",
        }

    monkeypatch.setattr(gemini_provider, "_call_gemini_api", fake_call)
    evidence = {
        "trade_vision_decision": {"final_trade_decision": "WAIT"},
        "indicator_snapshot": {"rsi14": 44, "vwap_position": "below_vwap"},
        "safety_summary": {"blocking_gates": []},
    }
    report = asyncio.run(gemini_provider.build_gemini_live_review_report(evidence_packet=evidence, execute=True))
    assert report["live_call_allowed"] is True
    assert report["live_call_performed"] is True
    assert report["successful_slot"] == 2
    assert report["attempt_count"] == 2
    assert report["display_allowed"] is True
    assert report["review_intake"]["validation"]["schema_validation_passed"] is True
    assert report["review_intake"]["validation"]["hallucination_detected"] is False
    assert report["safe_final_action"] == "WAIT"
    assert report["order_routing_enabled"] is False
    assert "gemini_unit_test_key" not in json.dumps(report)


def test_v136_grok_live_review_disabled_is_trade_vision_only(monkeypatch):
    from app.behavior import grok_provider

    monkeypatch.delenv("TRADEVISION_GROK_ENABLE_LIVE", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    evidence = {
        "trade_vision_decision": {"final_trade_decision": "WAIT"},
        "indicator_snapshot": {"rsi14": 44, "vwap_position": "below_vwap"},
        "safety_summary": {"blocking_gates": []},
    }
    report = asyncio.run(grok_provider.build_grok_live_review_report(evidence_packet=evidence, execute=True))
    assert report["live_review_version"] == "jarvis-grok-live-review.v1.36"
    assert report["live_call_allowed"] is False
    assert report["live_call_performed"] is False
    assert report["safe_final_action"] == "TRADE_VISION_ONLY"
    assert report["provider_status"]["security"]["browser_password_login_supported"] is False
    assert report["provider_status"]["passgrok_boundary"]["capture_modules_imported"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_execute_orders"] is False
    assert "XAI_API_KEY" not in json.dumps(report)


def test_v136_grok_live_review_validates_mocked_xai_response(monkeypatch):
    from app.behavior import grok_provider

    monkeypatch.setenv("TRADEVISION_GROK_ENABLE_LIVE", "true")
    monkeypatch.setenv("XAI_API_KEY", "xai_unit_test_key_slot")

    async def fake_call(*, evidence_packet, provider_status, outbound_bundle):
        return {
            "performed": True,
            "success": True,
            "status_code": 200,
            "latency_ms": 5,
            "candidate_response": {
                "review_status": "valid",
                "agrees_with_trade_vision": True,
                "pattern_interpretation": "Below-VWAP wait structure.",
                "entry_guidance": "Wait for VWAP reclaim.",
                "risk_warning": "Do not trade while below VWAP.",
                "best_indicator_for_pattern": ["vwap_position", "rsi14"],
                "avoid_if": ["price remains below VWAP"],
                "confidence_comment": "External AI cannot boost confidence.",
                "final_action": "WAIT",
                "cited_evidence_keys": ["indicator_snapshot", "vwap_position", "rsi14", "safety_summary"],
            },
            "raw_text_preview": "{\"final_action\":\"WAIT\"}",
        }

    monkeypatch.setattr(grok_provider, "_call_grok_api", fake_call)
    evidence = {
        "trade_vision_decision": {"final_trade_decision": "WAIT"},
        "indicator_snapshot": {"rsi14": 44, "vwap_position": "below_vwap"},
        "safety_summary": {"blocking_gates": []},
    }
    report = asyncio.run(grok_provider.build_grok_live_review_report(evidence_packet=evidence, execute=True))
    assert report["provider_status"]["status"] == "ready"
    assert report["provider_status"]["api_key_source"] == "XAI_API_KEY"
    assert report["live_call_allowed"] is True
    assert report["live_call_performed"] is True
    assert report["display_allowed"] is True
    assert report["review_intake"]["validation"]["schema_validation_passed"] is True
    assert report["review_intake"]["validation"]["hallucination_detected"] is False
    assert report["safe_final_action"] == "WAIT"
    assert report["order_routing_enabled"] is False
    assert "xai_unit_test_key" not in json.dumps(report)


def test_v093_openalgo_report_import_redacts_and_feeds_jarvis_without_routing():
    payload = {
        "source": "unit_openalgo_report",
        "report": {
            "symbol": "RELIANCE",
            "status": "filled",
            "side": "BUY",
            "quantity": 10,
            "intended_price": 2500.0,
            "fill_price": 2503.0,
            "latency_ms": 80,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "api_key": "should-not-leak",
            "nested": {"authorization": "Bearer should-not-leak"},
        },
    }
    response = client.post("/api/v1/openalgo/report/import", json=payload)
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["importer_version"] == "openalgo-report-importer.v0.93"
    assert report["symbol"] == "RELIANCE"
    assert report["sanitized_report"]["api_key"] == "[REDACTED]"
    assert report["sanitized_report"]["nested"]["authorization"] == "[REDACTED]"
    assert report["redacted_field_paths"] == ["$.api_key", "$.nested.authorization"]
    assert report["broker_order_created"] is False
    assert report["order_routing_enabled"] is False
    assert report["trade_allowed"] is False
    assert report["live_trading_blocked"] is True
    assert report["jarvis_effect"]["can_override_no_trade"] is False

    current_response = client.get("/api/v1/openalgo/report/current/RELIANCE")
    assert current_response.status_code == 200
    current = current_response.json()["data"]
    assert current["status"] == "report_imported"
    assert current["latest_report_id"] == report["report_id"]
    assert current["can_execute_orders"] is False

    room_response = client.get("/api/v1/jarvis/decision-room/state/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert room_response.status_code == 200
    room = room_response.json()["data"]
    assert room["room_version"] == "jarvis-decision-room.v0.96"
    assert room["openalgo_summary"]["status"] == "report_imported"
    assert room["openalgo_summary"]["latest_report_id"] == report["report_id"]
    assert room["paper_reality_check"]["source_report_id"] == report["report_id"]
    assert room["paper_reality_check"]["reality_check_version"] == "paper-execution-reality-check.v0.94"
    assert room["decision_arbiter"]["can_export_to_openalgo"] is False

    reality_response = client.get("/api/v1/openalgo/report/reality-check/current/RELIANCE?timeframe=1m&rows=390&position=tail")
    assert reality_response.status_code == 200
    reality = reality_response.json()["data"]
    assert reality["source_report_id"] == report["report_id"]
    assert reality["paper_only"] is True
    assert reality["trade_allowed"] is False
    assert reality["order_routing_enabled"] is False
    assert reality["broker_order_created"] is False
    assert reality["live_trading_blocked"] is True

    usefulness_response = client.get("/api/v1/jarvis/usefulness/RELIANCE")
    assert usefulness_response.status_code == 200
    usefulness = usefulness_response.json()["data"]
    assert usefulness["summary_version"] == "jarvis-usefulness-tracker.v0.96"
    assert usefulness["record_count"] >= 1
    assert usefulness["trade_allowed"] is False
    assert usefulness["order_routing_enabled"] is False
    assert usefulness["live_trading_blocked"] is True


def test_v093_openalgo_report_import_flags_unsafe_live_report_as_downgrade_only():
    payload = {
        "report": {
            "symbol": "TVUNSAFE",
            "status": "filled",
            "broker_order_created": True,
            "order_routing_enabled": True,
            "live_trading_enabled": True,
            "token": "should-not-leak",
        }
    }
    response = client.post("/api/v1/openalgo/report/import", json=payload)
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["sanitized_report"]["token"] == "[REDACTED]"
    assert report["safety_result"]["safe_for_research_review"] is False
    assert report["jarvis_effect"]["effect"] == "downgrade_to_wait"
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True


def test_v090_gemini_provider_manager_is_backend_only_and_schema_locked():
    response = client.get("/api/v1/jarvis/gemini/status")
    assert response.status_code == 200
    status = response.json()["data"]
    assert status["provider_version"] == "jarvis-gemini-provider-manager.v0.91"
    assert status["fallback_key_slots_supported"] == 5
    assert len(status["key_slots"]) == 5
    assert status["mode"] == "live_disabled_safe_stub"
    assert status["temperature"] == 0.0
    assert status["review_schema_version"] == "jarvis-gemini-review-schema.v0.90"
    assert "final_action" in status["required_review_fields"]
    assert "NO_TRADE" in status["allowed_final_actions"]
    assert status["prompt_policy"]["must_return_json"] is True
    assert status["prompt_policy"]["external_ai_cannot_override_no_trade"] is True
    assert status["security"]["backend_only_keys"] is True
    assert status["security"]["keys_exposed_to_frontend"] is False
    assert status["security"]["keys_logged"] is False
    assert status["can_execute_orders"] is False
    assert status["can_override_no_trade"] is False
    assert status["can_override_risk"] is False
    for slot in status["key_slots"]:
        assert "GEMINI_API_KEY_" in slot["env_name"]
        assert "key" not in slot
        assert "fingerprint" not in slot
        assert "suffix" not in slot
        assert "prefix" not in slot
        assert "secret" not in slot
        assert "token" not in slot


def test_v090_gemini_review_stub_cannot_override_trade_vision():
    response = client.post("/api/v1/jarvis/gemini/review", json={"packet_id": "unit-test", "trade_vision_decision": {"final_trade_decision": "NO_TRADE"}})
    assert response.status_code == 200
    review = response.json()["data"]
    assert review["review_version"] == "jarvis-gemini-provider-manager.v0.91.review"
    assert review["can_execute_orders"] is False
    assert review["can_override_no_trade"] is False
    assert review["can_override_risk"] is False
    assert review["safe_final_action"] in {"TRADE_VISION_ONLY", "WAIT_FOR_VALIDATED_REVIEW"}
    assert len(review["evidence_packet_hash"]) == 64


def test_v090_gemini_review_validation_accepts_cited_packet_evidence():
    payload = {
        "evidence_packet": {
            "trade_vision_decision": {"final_trade_decision": "WAIT"},
            "indicator_snapshot": {"rsi14": 44.0, "vwap_position": "below_vwap"},
            "safety_summary": {"blocking_gates": []},
        },
        "candidate_response": {
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Weak below-VWAP structure.",
            "entry_guidance": "Wait for reclaim.",
            "risk_warning": "VWAP rejection remains active.",
            "best_indicator_for_pattern": ["vwap_position", "rsi14"],
            "avoid_if": ["price remains below VWAP"],
            "confidence_comment": "Evidence supports waiting.",
            "final_action": "WAIT",
            "cited_evidence_keys": ["indicator_snapshot", "rsi14", "vwap_position", "safety_summary"],
        },
    }
    response = client.post("/api/v1/jarvis/gemini/review", json=payload)
    assert response.status_code == 200
    validation = response.json()["data"]["validation"]
    assert validation["schema_validation_passed"] is True
    assert validation["hallucination_detected"] is False
    assert validation["accepted_for_display"] is True


def test_v090_gemini_review_validation_rejects_hallucinated_or_unsafe_response():
    payload = {
        "evidence_packet": {
            "trade_vision_decision": {"final_trade_decision": "NO_TRADE"},
            "indicator_snapshot": {"rsi14": 44.0},
            "safety_summary": {"blocking_gates": ["DATA_QUALITY"]},
        },
        "candidate_response": {
            "review_status": "valid",
            "agrees_with_trade_vision": False,
            "pattern_interpretation": "Invented news breakout.",
            "entry_guidance": "Buy now.",
            "risk_warning": "None.",
            "best_indicator_for_pattern": ["rsi14"],
            "avoid_if": [],
            "confidence_comment": "Unsafe.",
            "final_action": "PAPER_CANDIDATE",
            "cited_evidence_keys": ["indicator_snapshot", "nonexistent_news_signal"],
        },
    }
    response = client.post("/api/v1/jarvis/gemini/review", json=payload)
    assert response.status_code == 200
    validation = response.json()["data"]["validation"]
    assert validation["schema_validation_passed"] is False
    assert validation["hallucination_detected"] is True
    assert validation["unsafe_override_attempted"] is True
    assert validation["accepted_for_display"] is False
    assert "nonexistent_news_signal" in validation["hallucinated_evidence_keys"]


def test_v091_gemini_sample_review_display_is_validated_and_not_live():
    evidence = {
        "trade_vision_decision": {
            "final_trade_decision": "WATCH_ONLY",
            "entry_condition": "Wait for VWAP reclaim.",
            "confidence_cap_pct": 45,
            "avoid_if": ["price remains below VWAP"],
        },
        "candle_structure": {"pattern": "wick_rejection"},
        "indicator_snapshot": {"rsi14": 44.0, "ema_state": "bearish", "vwap_position": "below_vwap", "volume_z": -1.2},
        "safety_summary": {"blocking_gates": []},
        "final_action": "WATCH_ONLY",
    }
    response = client.post("/api/v1/jarvis/gemini/review/sample", json=evidence)
    assert response.status_code == 200
    sample = response.json()["data"]
    assert sample["review_panel_version"] == "jarvis-gemini-review-panel.v0.91"
    assert sample["review_source"] == "deterministic_sample_not_live_gemini"
    assert sample["live_gemini_called"] is False
    assert sample["api_cost_usd"] == 0.0
    assert sample["display_allowed"] is True
    assert sample["validation"]["schema_validation_passed"] is True
    assert sample["validation"]["hallucination_detected"] is False
    assert sample["can_override_no_trade"] is False


def _v137_evidence_packet(final_action: str = "WAIT") -> dict:
    return {
        "trade_vision_decision": {"final_trade_decision": final_action},
        "indicator_snapshot": {"rsi14": 44.0, "vwap_position": "below_vwap"},
        "safety_summary": {"blocking_gates": []},
        "final_action": final_action,
    }


def _v137_provider_report(provider: str, action: str, display_allowed: bool = True) -> dict:
    response = {
        "review_status": "valid",
        "agrees_with_trade_vision": action == "WAIT",
        "pattern_interpretation": f"{provider} sees research-only {action}.",
        "entry_guidance": "Wait for confirmed reclaim.",
        "risk_warning": "External AI cannot override Trade Vision.",
        "best_indicator_for_pattern": ["rsi14", "vwap_position"],
        "avoid_if": ["evidence weakens"],
        "confidence_comment": "Research-only.",
        "final_action": action,
        "cited_evidence_keys": ["trade_vision_decision", "indicator_snapshot", "safety_summary"],
    }
    return {
        "provider_status": {"provider": provider, "status": "ready", "selected_model": f"{provider}-unit"},
        "evidence_packet_hash": "a" * 64,
        "candidate_response": response,
        "review_intake": {
            "candidate_response": response,
            "validation": {
                "schema_validation_passed": True,
                "hallucination_detected": False,
                "hallucinated_evidence_keys": [],
                "missing_fields": [],
                "accepted_for_display": display_allowed,
            },
        },
        "display_allowed": display_allowed,
        "safe_final_action": action,
        "live_call_performed": True,
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def test_v137_ai_comparison_both_unavailable_is_trade_vision_only(monkeypatch):
    from app.behavior import jarvis_ai_comparison_room

    monkeypatch.delenv("TRADEVISION_GEMINI_ENABLE_LIVE", raising=False)
    monkeypatch.delenv("TRADEVISION_GROK_ENABLE_LIVE", raising=False)
    report = asyncio.run(
        jarvis_ai_comparison_room.build_jarvis_ai_comparison_room(
            symbol="RELIANCE",
            evidence_packet=_v137_evidence_packet("WAIT"),
            execute_gemini=False,
            execute_grok=False,
        )
    )
    assert report["comparison_version"] == "jarvis-ai-comparison-room.v1.37"
    assert report["agreement_matrix"]["agreement_state"] == "BOTH_UNAVAILABLE"
    assert report["agreement_matrix"]["displayable_provider_count"] == 0
    assert report["safe_final_action"] == "TRADE_VISION_ONLY"
    assert report["confidence_boost_allowed"] is False
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["can_execute_orders"] is False
    assert report["can_override_no_trade"] is False
    assert report["can_override_risk"] is False


def test_v137_ai_comparison_agreement_is_display_only(monkeypatch):
    from app.behavior import jarvis_ai_comparison_room

    async def fake_gemini(**_kwargs):
        return _v137_provider_report("gemini", "WAIT")

    async def fake_grok(**_kwargs):
        return _v137_provider_report("grok", "WAIT")

    monkeypatch.setattr(jarvis_ai_comparison_room, "build_gemini_live_review_report", fake_gemini)
    monkeypatch.setattr(jarvis_ai_comparison_room, "build_grok_live_review_report", fake_grok)
    report = asyncio.run(
        jarvis_ai_comparison_room.build_jarvis_ai_comparison_room(
            symbol="RELIANCE",
            evidence_packet=_v137_evidence_packet("WAIT"),
            execute_gemini=True,
            execute_grok=True,
        )
    )
    assert report["agreement_matrix"]["agreement_state"] == "AGREE"
    assert report["agreement_matrix"]["displayable_provider_count"] == 2
    assert report["safe_final_action"] == "WAIT"
    assert report["confidence_boost_allowed"] is False
    assert report["can_export_to_openalgo"] is False
    assert all(gate["passed"] for gate in report["gates"] if gate["gate_id"] in {"AICR-001", "AICR-002", "AICR-003", "AICR-006", "AICR-007"})


def test_v137_ai_comparison_hard_conflict_forces_wait(monkeypatch):
    from app.behavior import jarvis_ai_comparison_room

    async def fake_gemini(**_kwargs):
        return _v137_provider_report("gemini", "WAIT")

    async def fake_grok(**_kwargs):
        return _v137_provider_report("grok", "NO_TRADE")

    monkeypatch.setattr(jarvis_ai_comparison_room, "build_gemini_live_review_report", fake_gemini)
    monkeypatch.setattr(jarvis_ai_comparison_room, "build_grok_live_review_report", fake_grok)
    report = asyncio.run(
        jarvis_ai_comparison_room.build_jarvis_ai_comparison_room(
            symbol="RELIANCE",
            evidence_packet=_v137_evidence_packet("WAIT"),
            execute_gemini=True,
            execute_grok=True,
        )
    )
    assert report["agreement_matrix"]["agreement_state"] == "HARD_CONFLICT"
    assert report["agreement_matrix"]["external_ai_disagreement_detected"] is True
    assert report["safe_final_action"] == "WAIT"
    assert report["confidence_boost_allowed"] is False
    assert any(gate["gate_id"] == "AICR-005" and gate["passed"] is False for gate in report["gates"])
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False


def _v138_comparison_record(agreement_state: str = "AGREE", safe_action: str = "WAIT", displayable: int = 2) -> dict:
    return {
        "comparison_id": f"jarvis-ai-comparison:{agreement_state.lower()}",
        "symbol": "RELIANCE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_packet_hash": "a" * 64,
        "agreement_matrix": {
            "agreement_state": agreement_state,
            "displayable_provider_count": displayable,
        },
        "safe_final_action": safe_action,
        "gemini": {"display_allowed": displayable >= 1},
        "grok": {"display_allowed": displayable >= 2},
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def test_v138_ai_comparison_history_empty_is_stale_trade_vision_only():
    from app.behavior.jarvis_ai_comparison_history import build_jarvis_ai_comparison_history_report

    report = build_jarvis_ai_comparison_history_report(symbol="RELIANCE", comparison_records=[], stale_after_seconds=60)
    assert report["history_version"] == "jarvis-ai-comparison-history.v1.38"
    assert report["record_count"] == 0
    assert report["stale_comparison_history"] is True
    assert report["latest_safe_final_action"] == "TRADE_VISION_ONLY"
    assert report["confidence_boost_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert any(gate["gate_id"] == "AICH-001" and gate["passed"] is False for gate in report["gates"])


def test_v138_ai_comparison_history_fresh_agreement_remains_display_only():
    from app.behavior.jarvis_ai_comparison_history import build_jarvis_ai_comparison_history_report

    report = build_jarvis_ai_comparison_history_report(
        symbol="RELIANCE",
        comparison_records=[_v138_comparison_record("AGREE", "WAIT", 2)],
        stale_after_seconds=900,
    )
    assert report["history_state"] == "display_only"
    assert report["agreement_rate"] == 1.0
    assert report["conflict_rate"] == 0.0
    assert report["provider_health"]["gemini"]["displayable_rate"] == 1.0
    assert report["provider_health"]["grok"]["displayable_rate"] == 1.0
    assert report["external_ai_reliable_for_decision"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["can_export_to_openalgo"] is False


def test_v138_ai_comparison_history_conflict_rate_warns_and_blocks_boost():
    from app.behavior.jarvis_ai_comparison_history import build_jarvis_ai_comparison_history_report

    records = [
        _v138_comparison_record("HARD_CONFLICT", "WAIT", 2),
        _v138_comparison_record("SOFT_CONFLICT", "WAIT", 1),
        _v138_comparison_record("AGREE", "WAIT", 2),
    ]
    report = build_jarvis_ai_comparison_history_report(symbol="RELIANCE", comparison_records=records, stale_after_seconds=900)
    assert report["history_state"] == "warning"
    assert report["conflict_rate"] > 0.25
    assert report["latest_agreement_state"] == "HARD_CONFLICT"
    assert report["confidence_boost_allowed"] is False
    assert any(gate["gate_id"] == "AICH-004" and gate["passed"] is False for gate in report["gates"])
    assert any(gate["gate_id"] == "AICH-005" and gate["passed"] is False for gate in report["gates"])


def _v139_current_packet() -> dict:
    return {
        "trade_vision_decision": {"final_trade_decision": "WAIT"},
        "indicator_snapshot": {"rsi14": 44.0, "vwap_position": "below_vwap"},
        "safety_summary": {"blocking_gates": []},
        "final_action": "WAIT",
    }


def _v139_comparison_record(evidence_hash: str, agreement_state: str = "AGREE") -> dict:
    return {
        "comparison_id": "jarvis-ai-comparison:v139",
        "symbol": "RELIANCE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_packet_hash": evidence_hash,
        "agreement_matrix": {"agreement_state": agreement_state, "displayable_provider_count": 2},
        "safe_final_action": "WAIT",
        "gemini": {"display_allowed": True},
        "grok": {"display_allowed": True},
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _v139_external_review(evidence_hash: str) -> dict:
    return {
        "review_id": "external-ai-review:v139",
        "symbol": "RELIANCE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_packet_hash": evidence_hash,
        "display_allowed": True,
        "safe_final_action": "WAIT",
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def test_v139_refresh_guard_empty_history_requires_refresh():
    from app.behavior.jarvis_ai_review_refresh_guard import build_jarvis_ai_review_refresh_guard

    report = build_jarvis_ai_review_refresh_guard(
        symbol="RELIANCE",
        current_evidence_packet=_v139_current_packet(),
        comparison_history={"history_state": "warning", "record_count": 0},
        comparison_records=[],
        external_review_records=[],
        correction_response_records=[],
        stale_after_seconds=60,
    )
    assert report["refresh_guard_version"] == "jarvis-ai-review-refresh-guard.v1.39"
    assert report["refresh_state"] == "refresh_required"
    assert report["needs_external_ai_refresh"] is True
    assert report["comparison_hash_matches_current"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert any(target["target_id"] == "gemini_grok_comparison" for target in report["refresh_targets"])


def test_v139_refresh_guard_matching_fresh_hash_is_display_only():
    from app.behavior import jarvis_ai_review_refresh_guard

    packet = _v139_current_packet()
    evidence_hash = jarvis_ai_review_refresh_guard._hash_packet(packet)
    report = jarvis_ai_review_refresh_guard.build_jarvis_ai_review_refresh_guard(
        symbol="RELIANCE",
        current_evidence_packet=packet,
        comparison_history={"history_state": "display_only", "record_count": 1},
        comparison_records=[_v139_comparison_record(evidence_hash, "AGREE")],
        external_review_records=[_v139_external_review(evidence_hash)],
        correction_response_records=[],
        stale_after_seconds=900,
    )
    assert report["refresh_state"] == "fresh_display_only"
    assert report["needs_external_ai_refresh"] is False
    assert report["comparison_hash_matches_current"] is True
    assert report["external_review_hash_matches_current"] is True
    assert report["confidence_boost_allowed"] is False
    assert report["can_export_to_openalgo"] is False
    assert any(target["target_id"] == "none" for target in report["refresh_targets"])


def test_v139_refresh_guard_mismatch_or_conflict_forces_refresh():
    from app.behavior.jarvis_ai_review_refresh_guard import build_jarvis_ai_review_refresh_guard

    report = build_jarvis_ai_review_refresh_guard(
        symbol="RELIANCE",
        current_evidence_packet=_v139_current_packet(),
        comparison_history={"history_state": "warning", "record_count": 1},
        comparison_records=[_v139_comparison_record("old-hash", "HARD_CONFLICT")],
        external_review_records=[_v139_external_review("old-hash")],
        correction_response_records=[],
        stale_after_seconds=900,
    )
    assert report["refresh_state"] == "refresh_required"
    assert report["needs_external_ai_refresh"] is True
    assert report["latest_comparison_agreement_state"] == "HARD_CONFLICT"
    assert report["comparison_hash_matches_current"] is False
    assert report["external_review_hash_matches_current"] is False
    assert any(target["target_id"] == "correction_review" for target in report["refresh_targets"])
    assert report["trade_allowed"] is False


def _v140_bundle(evidence_hash: str, provider: str = "gemini") -> dict:
    return {
        "bundle_version": f"{provider}-bundle-unit",
        "provider_version": f"{provider}-provider-unit",
        "review_schema_version": "jarvis-gemini-review-schema.v0.90",
        "request_hash": f"{provider}-request-hash",
        "evidence_packet_hash": evidence_hash,
        "dry_run_only": True,
        "network_call_allowed": False,
        "live_call_performed": False,
        "selected_model": f"{provider}-model",
        "sanitization": {
            "secrets_included": False,
            "broker_credentials_included": False,
            "cookies_or_sessions_included": False,
        },
        "outbound_request_preview": {
            "model": f"{provider}-model",
            "response_format": "strict_json",
            "required_fields": ["final_action"],
            "allowed_final_actions": ["NO_TRADE", "WAIT", "WATCH_ONLY", "TRADE_VISION_ONLY"],
            "evidence_packet": {"unit": True},
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _v140_refresh_guard() -> dict:
    return {
        "refresh_guard_version": "jarvis-ai-review-refresh-guard.v1.39",
        "refresh_state": "refresh_required",
        "needs_external_ai_refresh": True,
        "refresh_targets": [{"target_id": "gemini_grok_comparison", "reason": "unit", "order_authority": False}],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def test_v140_ai_refresh_action_harness_prepares_matching_dry_run_packet():
    from app.behavior import jarvis_ai_refresh_action_harness

    packet = _v139_current_packet()
    evidence_hash = jarvis_ai_refresh_action_harness._hash_packet(packet)
    report = jarvis_ai_refresh_action_harness.build_jarvis_ai_refresh_action_harness(
        symbol="RELIANCE",
        current_evidence_packet=packet,
        refresh_guard=_v140_refresh_guard(),
        gemini_bundle=_v140_bundle(evidence_hash, "gemini"),
        grok_bundle=_v140_bundle(evidence_hash, "grok"),
        execute_requested=False,
    )
    assert report["harness_version"] == "jarvis-ai-refresh-action-harness.v1.40"
    assert report["harness_state"] == "refresh_packet_ready"
    assert report["bundle_hashes_match_current"] is True
    assert report["ready_for_operator_review"] is True
    assert report["network_call_allowed"] is False
    assert report["network_call_performed"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["order_routing_enabled"] is False


def test_v140_ai_refresh_action_harness_blocks_mismatched_bundle_hash():
    from app.behavior import jarvis_ai_refresh_action_harness

    packet = _v139_current_packet()
    evidence_hash = jarvis_ai_refresh_action_harness._hash_packet(packet)
    report = jarvis_ai_refresh_action_harness.build_jarvis_ai_refresh_action_harness(
        symbol="RELIANCE",
        current_evidence_packet=packet,
        refresh_guard=_v140_refresh_guard(),
        gemini_bundle=_v140_bundle(evidence_hash, "gemini"),
        grok_bundle=_v140_bundle("old-hash", "grok"),
        execute_requested=False,
    )
    assert report["harness_state"] == "blocked"
    assert report["bundle_hashes_match_current"] is False
    assert any(gate["gate_id"] == "AIRH-004" and gate["passed"] is False for gate in report["gates"])
    assert report["trade_allowed"] is False


def test_v140_ai_refresh_action_harness_execute_request_stays_no_network():
    from app.behavior import jarvis_ai_refresh_action_harness

    packet = _v139_current_packet()
    evidence_hash = jarvis_ai_refresh_action_harness._hash_packet(packet)
    report = jarvis_ai_refresh_action_harness.build_jarvis_ai_refresh_action_harness(
        symbol="RELIANCE",
        current_evidence_packet=packet,
        refresh_guard=_v140_refresh_guard(),
        gemini_bundle=_v140_bundle(evidence_hash, "gemini"),
        grok_bundle=_v140_bundle(evidence_hash, "grok"),
        execute_requested=True,
    )
    assert report["harness_state"] == "operator_review_ready"
    assert report["execute_requested"] is True
    assert report["network_call_allowed"] is False
    assert report["network_call_performed"] is False
    assert any(gate["gate_id"] == "AIRH-006" and gate["passed"] is False for gate in report["gates"])
    assert report["can_execute_orders"] is False


def _v141_refresh_action(provider: str = "gemini") -> dict:
    from app.behavior.jarvis_ai_refresh_action_harness import _hash_packet

    evidence = _v139_current_packet()
    refresh_packet = {
        "symbol": "RELIANCE",
        "evidence_packet_hash": _hash_packet(evidence),
        f"{provider}_request": {
            "provider": provider,
            "outbound_request_preview": {"evidence_packet": evidence},
        },
        "instructions": ["unit"],
    }
    return {
        "harness_version": "jarvis-ai-refresh-action-harness.v1.40",
        "symbol": "RELIANCE",
        "packet_hash": _hash_packet(refresh_packet),
        "current_evidence_packet_hash": _hash_packet(evidence),
        "refresh_packet_preview": refresh_packet,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _v141_candidate(packet_hash: str, cited: list[str] | None = None, final_action: str = "TRADE_VISION_ONLY") -> dict:
    return {
        "packet_hash": packet_hash,
        "review_status": "valid",
        "agrees_with_trade_vision": True,
        "pattern_interpretation": "Wait structure below VWAP.",
        "entry_guidance": "Wait for Trade Vision confirmation.",
        "risk_warning": "External AI is display-only.",
        "best_indicator_for_pattern": ["indicator_snapshot", "vwap_position"],
        "avoid_if": ["safety_summary blocks"],
        "confidence_comment": "No confidence boost.",
        "final_action": final_action,
        "cited_evidence_keys": cited or ["trade_vision_decision", "indicator_snapshot", "safety_summary"],
    }


def test_v141_refresh_response_intake_accepts_matching_packet_for_display_only():
    from app.behavior.jarvis_ai_refresh_response_intake import build_jarvis_ai_refresh_response_intake

    refresh_action = _v141_refresh_action("gemini")
    report = build_jarvis_ai_refresh_response_intake(
        symbol="RELIANCE",
        provider="gemini",
        refresh_action=refresh_action,
        candidate_response=_v141_candidate(refresh_action["packet_hash"]),
    )
    assert report["intake_replay_version"] == "jarvis-ai-refresh-response-intake.v1.41"
    assert report["replay_status"] == "accepted_for_display"
    assert report["packet_hash_matches"] is True
    assert report["display_allowed"] is True
    assert report["review_record"]["display_allowed"] is True
    assert report["confidence_boost_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["can_export_to_openalgo"] is False


def test_v141_refresh_response_intake_blocks_missing_packet_hash():
    from app.behavior.jarvis_ai_refresh_response_intake import build_jarvis_ai_refresh_response_intake

    refresh_action = _v141_refresh_action("grok")
    candidate = _v141_candidate(refresh_action["packet_hash"])
    candidate.pop("packet_hash")
    report = build_jarvis_ai_refresh_response_intake(
        symbol="RELIANCE",
        provider="grok",
        refresh_action=refresh_action,
        candidate_response=candidate,
    )
    assert report["replay_status"] == "blocked"
    assert report["packet_hash_matches"] is False
    assert report["display_allowed"] is False
    assert any(gate["gate_id"] == "AIRI-002" and gate["passed"] is False for gate in report["gates"])
    assert report["trade_allowed"] is False


def test_v141_refresh_response_intake_rejects_hallucinated_evidence():
    from app.behavior.jarvis_ai_refresh_response_intake import build_jarvis_ai_refresh_response_intake

    refresh_action = _v141_refresh_action("gemini")
    report = build_jarvis_ai_refresh_response_intake(
        symbol="RELIANCE",
        provider="gemini",
        refresh_action=refresh_action,
        candidate_response=_v141_candidate(refresh_action["packet_hash"], cited=["indicator_snapshot", "invented_news"]),
    )
    assert report["replay_status"] == "rejected"
    assert report["packet_hash_matches"] is True
    assert report["validation"]["hallucination_detected"] is True
    assert "invented_news" in report["validation"]["hallucinated_evidence_keys"]
    assert report["display_allowed"] is False


def _v142_record(
    *,
    source: str = "gemini",
    status: str = "accepted_for_display",
    display_allowed: bool = True,
    evidence_hash: str = "current-hash",
    created_at: str | None = None,
    trade_allowed: bool = False,
) -> dict:
    return {
        "review_id": f"review-{source}-{status}",
        "symbol": "RELIANCE",
        "source": source,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "intake_status": status,
        "display_allowed": display_allowed,
        "safe_final_action": "TRADE_VISION_ONLY",
        "refresh_action_evidence_hash": evidence_hash,
        "refresh_packet_hash": "packet-hash",
        "response_packet_hash_matches": True,
        "validation": {
            "schema_validation_passed": display_allowed,
            "hallucination_detected": status == "rejected",
            "unsafe_override_attempted": False,
        },
        "trade_allowed": trade_allowed,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def test_v142_refresh_response_ledger_accepts_fresh_display_history():
    from app.behavior.jarvis_ai_refresh_response_ledger import build_jarvis_ai_refresh_response_ledger

    report = build_jarvis_ai_refresh_response_ledger(
        symbol="RELIANCE",
        records=[_v142_record()],
        current_evidence_packet_hash="current-hash",
        stale_after_seconds=900,
    )
    assert report["ledger_version"] == "jarvis-ai-refresh-response-ledger.v1.42"
    assert report["ledger_state"] == "fresh_display_history"
    assert report["accepted_count"] == 1
    assert report["latest_accepted_record"]["matches_current_evidence"] is True
    assert report["confidence_boost_allowed"] is False
    assert report["order_routing_enabled"] is False


def test_v142_refresh_response_ledger_marks_stale_mismatched_history_for_refresh():
    from app.behavior.jarvis_ai_refresh_response_ledger import build_jarvis_ai_refresh_response_ledger

    old_time = (datetime.now(timezone.utc) - timedelta(seconds=3600)).isoformat()
    report = build_jarvis_ai_refresh_response_ledger(
        symbol="RELIANCE",
        records=[_v142_record(source="grok", evidence_hash="old-hash", created_at=old_time)],
        current_evidence_packet_hash="current-hash",
        stale_after_seconds=900,
    )
    assert report["ledger_state"] == "needs_refresh"
    assert report["stale_count"] == 1
    assert report["hash_mismatch_count"] == 1
    assert report["latest_accepted_record"]["matches_current_evidence"] is False
    assert any(gate["gate_id"] == "AIRL-002" and gate["passed"] is False for gate in report["gates"])


def test_v142_refresh_response_ledger_blocks_unsafe_authority_record():
    from app.behavior.jarvis_ai_refresh_response_ledger import build_jarvis_ai_refresh_response_ledger

    report = build_jarvis_ai_refresh_response_ledger(
        symbol="RELIANCE",
        records=[_v142_record(trade_allowed=True)],
        current_evidence_packet_hash="current-hash",
        stale_after_seconds=900,
    )
    assert report["ledger_state"] == "unsafe_blocked"
    assert report["unsafe_authority_count"] == 1
    assert any(gate["gate_id"] == "AIRL-003" and gate["passed"] is False for gate in report["gates"])
    assert report["trade_allowed"] is False


def _v143_evidence(action: str = "NO_TRADE", blocking: bool = False) -> dict:
    return {
        "symbol": "RELIANCE",
        "timeframe": "1m",
        "trade_vision_decision": {
            "final_trade_decision": action,
            "entry_condition": "Wait for reclaim.",
        },
        "candle_structure": {"pattern": "range"},
        "indicator_snapshot": {"rsi14": 48.0, "vwap_position": "below", "ema_state": "flat"},
        "safety_summary": {"blocking_gates": ["risk"] if blocking else []},
        "final_action": action,
    }


def _v143_record(evidence_hash: str, final_action: str = "TRADE_VISION_ONLY", cited: list[str] | None = None) -> dict:
    return {
        "review_id": "review-v143",
        "symbol": "RELIANCE",
        "source": "gemini",
        "display_allowed": True,
        "intake_status": "accepted_for_display",
        "refresh_action_evidence_hash": evidence_hash,
        "sanitized_candidate_response": {
            "review_status": "valid",
            "agrees_with_trade_vision": True,
            "pattern_interpretation": "Range below VWAP.",
            "entry_guidance": "Wait for reclaim.",
            "risk_warning": "Respect safety risk and wait.",
            "best_indicator_for_pattern": ["rsi14", "vwap_position"],
            "avoid_if": ["risk block"],
            "confidence_comment": "No boost.",
            "final_action": final_action,
            "cited_evidence_keys": cited or ["trade_vision_decision", "indicator_snapshot", "vwap_position"],
        },
    }


def test_v143_ai_response_evidence_diff_supports_current_display_claims():
    from app.behavior.jarvis_ai_refresh_action_harness import _hash_packet
    from app.behavior.jarvis_ai_response_evidence_diff import build_jarvis_ai_response_evidence_diff

    evidence = _v143_evidence(action="NO_TRADE")
    evidence_hash = _hash_packet(evidence)
    report = build_jarvis_ai_response_evidence_diff(
        symbol="RELIANCE",
        evidence_packet=evidence,
        records=[_v143_record(evidence_hash)],
        current_evidence_packet_hash=evidence_hash,
    )
    assert report["diff_version"] == "jarvis-ai-response-evidence-diff.v1.43"
    assert report["diff_state"] == "supported_for_display"
    assert report["record_hash_matches_current"] is True
    assert report["supported_count"] >= 3
    assert report["confidence_boost_allowed"] is False


def test_v143_ai_response_evidence_diff_flags_missing_and_stale_claims():
    from app.behavior.jarvis_ai_refresh_action_harness import _hash_packet
    from app.behavior.jarvis_ai_response_evidence_diff import build_jarvis_ai_response_evidence_diff

    evidence = _v143_evidence(action="NO_TRADE")
    report = build_jarvis_ai_response_evidence_diff(
        symbol="RELIANCE",
        evidence_packet=evidence,
        records=[_v143_record("old-hash", cited=["indicator_snapshot", "invented_news"])],
        current_evidence_packet_hash=_hash_packet(evidence),
    )
    assert report["diff_state"] == "needs_review"
    assert report["record_hash_matches_current"] is False
    assert report["missing_count"] >= 1
    assert any(item["evidence_key"] == "invented_news" and item["status"] == "missing" for item in report["cited_key_diffs"])


def test_v143_ai_response_evidence_diff_blocks_action_conflict():
    from app.behavior.jarvis_ai_refresh_action_harness import _hash_packet
    from app.behavior.jarvis_ai_response_evidence_diff import build_jarvis_ai_response_evidence_diff

    evidence = _v143_evidence(action="NO_TRADE", blocking=True)
    evidence_hash = _hash_packet(evidence)
    report = build_jarvis_ai_response_evidence_diff(
        symbol="RELIANCE",
        evidence_packet=evidence,
        records=[_v143_record(evidence_hash, final_action="PAPER_CANDIDATE")],
        current_evidence_packet_hash=evidence_hash,
    )
    assert report["diff_state"] == "conflict_blocked"
    assert report["action_diff"]["status"] == "conflict"
    assert any(gate["gate_id"] == "AIRD-004" and gate["passed"] is False for gate in report["gates"])
    assert report["trade_allowed"] is False


def _v144_ai_comparison(gemini_action: str = "WAIT", grok_action: str = "TRADE_VISION_ONLY") -> dict:
    return {
        "gemini": {
            "safe_final_action": gemini_action,
            "status": "ready",
            "display_allowed": True,
            "candidate_response": {"pattern_interpretation": f"Gemini says {gemini_action}."},
        },
        "grok": {
            "safe_final_action": grok_action,
            "status": "ready",
            "display_allowed": True,
            "candidate_response": {"pattern_interpretation": f"Grok says {grok_action}."},
        },
    }


def test_v144_provider_disagreement_explorer_classifies_action_conflict():
    from app.behavior.jarvis_provider_disagreement_explorer import build_jarvis_provider_disagreement_explorer

    report = build_jarvis_provider_disagreement_explorer(
        symbol="RELIANCE",
        evidence_packet=_v143_evidence(action="BUY BREAKOUT"),
        ai_comparison=_v144_ai_comparison(gemini_action="NO_TRADE", grok_action="TRADE_VISION_ONLY"),
        evidence_diff={"record_hash_matches_current": True, "missing_count": 0, "action_diff": {"status": "supported"}},
        kronos_report={"forecast_path": {"trend_direction": "SHORT"}},
        openalgo_summary={"effect": "review_only", "report_available": True},
    )
    assert report["explorer_version"] == "jarvis-provider-disagreement-explorer.v1.44"
    assert report["explorer_state"] == "needs_review"
    assert "action" in report["categories"]
    assert any(reason["source"] == "kronos" for reason in report["reason_cards"])
    assert report["trade_allowed"] is False


def test_v144_provider_disagreement_explorer_blocks_risk_conflict():
    from app.behavior.jarvis_provider_disagreement_explorer import build_jarvis_provider_disagreement_explorer

    report = build_jarvis_provider_disagreement_explorer(
        symbol="RELIANCE",
        evidence_packet=_v143_evidence(action="NO_TRADE", blocking=True),
        ai_comparison=_v144_ai_comparison(gemini_action="WAIT", grok_action="TRADE_VISION_ONLY"),
        evidence_diff={"record_hash_matches_current": True, "missing_count": 0, "action_diff": {"status": "conflict"}},
        kronos_report={"forecast_path": {"trend_direction": "LONG"}},
        openalgo_summary={"effect": "review_only", "report_available": True},
    )
    assert report["explorer_state"] == "hard_conflict"
    assert "risk" in report["categories"]
    assert any(gate["gate_id"] == "PDR-004" and gate["passed"] is False for gate in report["gates"])
    assert report["order_routing_enabled"] is False


def test_v144_provider_disagreement_explorer_blocks_openalgo_execution_downgrade():
    from app.behavior.jarvis_provider_disagreement_explorer import build_jarvis_provider_disagreement_explorer

    report = build_jarvis_provider_disagreement_explorer(
        symbol="RELIANCE",
        evidence_packet=_v143_evidence(action="WATCH_ONLY"),
        ai_comparison=_v144_ai_comparison(gemini_action="TRADE_VISION_ONLY", grok_action="TRADE_VISION_ONLY"),
        evidence_diff={"record_hash_matches_current": True, "missing_count": 0, "action_diff": {"status": "supported"}},
        kronos_report={"forecast_path": {"trend_direction": "SIDEWAYS"}},
        openalgo_summary={"effect": "downgrade_execution_confidence", "report_available": True},
    )
    assert report["explorer_state"] == "hard_conflict"
    assert "execution" in report["categories"]
    assert any(reason["source"] == "openalgo" for reason in report["reason_cards"])
    assert report["can_export_to_openalgo"] is False


def _v145_status(provider: str = "gemini") -> dict:
    if provider == "gemini":
        return {
            "provider": "gemini",
            "status": "ready",
            "mode": "live_disabled_safe_stub",
            "selected_model": "gemini-test",
            "configured_key_slots": 1,
            "fallback_key_slots_supported": 5,
            "key_slots": [{"slot": 1, "configured": True, "fingerprint": "abc", "last4": "1234"}],
            "review_schema_version": "schema",
            "provider_version": "gemini-provider-test",
            "timeout_ms": 2000,
        }
    return {
        "provider": "grok",
        "status": "ready",
        "mode": "live_disabled_safe_stub",
        "selected_model": "grok-test",
        "api_key_configured": True,
        "api_url_preview": "https://api.x.ai/v1/chat/completions",
        "provider_version": "grok-provider-test",
        "timeout_ms": 6000,
    }


def _v145_bundle(provider: str, evidence: dict, request_extra: dict | None = None) -> dict:
    request = {
        "model": f"{provider}-test",
        "temperature": 0.0,
        "response_format": "strict_json",
        "evidence_packet": evidence,
        **(request_extra or {}),
    }
    return {
        "bundle_version": f"{provider}-bundle-test",
        "provider_version": f"{provider}-provider-test",
        "request_hash": f"{provider}-request-hash",
        "evidence_packet_hash": "evidence-hash",
        "selected_model": f"{provider}-test",
        "timeout_ms": 2000,
        "network_call_allowed": False,
        "outbound_request_preview": request,
    }


def test_v145_verified_review_packet_is_operator_review_only_and_hash_bound():
    from app.behavior.jarvis_verified_review_packet import build_jarvis_verified_review_packet

    evidence = _v143_evidence(action="NO_TRADE")
    report = build_jarvis_verified_review_packet(
        symbol="RELIANCE",
        evidence_packet=evidence,
        gemini_status=_v145_status("gemini"),
        grok_status=_v145_status("grok"),
        gemini_bundle=_v145_bundle("gemini", evidence),
        grok_bundle=_v145_bundle("grok", evidence),
        review_records=[_v142_record(source="gemini", evidence_hash="evidence-hash")],
        refresh_action={"packet_hash": "refresh-hash"},
    )
    assert report["verified_packet_version"] == "jarvis-verified-review-packet.v1.45"
    assert report["packet_state"] == "operator_review_ready"
    assert report["providers"]["gemini"]["latest_review_id"] is not None
    assert report["copy_safe_export_hash"]
    assert report["network_call_allowed"] is False
    assert report["trade_allowed"] is False


def test_v145_verified_review_packet_exposes_provider_metadata_without_secrets():
    from app.behavior.jarvis_verified_review_packet import build_jarvis_verified_review_packet

    evidence = _v143_evidence(action="WATCH_ONLY")
    report = build_jarvis_verified_review_packet(
        symbol="RELIANCE",
        evidence_packet=evidence,
        gemini_status=_v145_status("gemini"),
        grok_status=_v145_status("grok"),
        gemini_bundle=_v145_bundle("gemini", evidence),
        grok_bundle=_v145_bundle("grok", evidence),
        review_records=[],
        refresh_action=None,
    )
    assert report["providers"]["gemini"]["provider_status"]["active_slot"] == 1
    assert report["providers"]["gemini"]["provider_status"]["keys_exposed_to_frontend"] is False
    assert report["providers"]["grok"]["provider_status"]["api_key_exposed_to_frontend"] is False
    assert report["providers"]["grok"]["provider_status"]["passgrok_capture_allowed"] is False
    assert report["secret_scan"]["secret_like_value_detected"] is False


def test_v145_verified_review_packet_blocks_secret_like_request_preview():
    from app.behavior.jarvis_verified_review_packet import build_jarvis_verified_review_packet

    evidence = _v143_evidence(action="WATCH_ONLY")
    report = build_jarvis_verified_review_packet(
        symbol="RELIANCE",
        evidence_packet=evidence,
        gemini_status=_v145_status("gemini"),
        grok_status=_v145_status("grok"),
        gemini_bundle=_v145_bundle("gemini", evidence, request_extra={"api_key": "SECRET-KEY-SHOULD-NOT-LEAK"}),
        grok_bundle=_v145_bundle("grok", evidence),
        review_records=[],
        refresh_action=None,
    )
    assert report["packet_state"] == "unsafe_blocked"
    assert report["secret_scan"]["secret_like_value_detected"] is True
    assert any(gate["gate_id"] == "VRP-003" and gate["passed"] is False for gate in report["gates"])
    assert report["order_routing_enabled"] is False


def _v146_handoff(export_allowed: bool = False, state: str = "blocked_manual_review") -> dict:
    return {
        "handoff_state": state,
        "handoff_hash": "handoff-hash",
        "dry_run_handoff_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "intent_summary": {
            "intent_id": "intent-1",
            "intent_signature": "sig-1",
            "side": "NONE",
            "mode_permission": "mock",
            "valid_until": "2026-06-24T10:00:00+00:00",
            "expired": False,
            "duplicate_key": "dup-1",
            "export_allowed": export_allowed,
            "broker_order_created": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        "package_summary": {
            "package_hash": "package-hash",
            "dry_run_only": True,
            "broker_credentials_present": False,
            "broker_order_created": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
    }


def _v146_bridge(inspect: bool = True, execute: bool = False) -> dict:
    return {
        "bridge_state": "paper_review_ready" if inspect else "blocked",
        "openalgo_may_inspect": inspect,
        "openalgo_may_execute": execute,
        "paper_intent_allowed": inspect,
        "live_intent_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _v146_verified(blocking_count: int = 0) -> dict:
    return {
        "packet_state": "operator_review_ready" if blocking_count == 0 else "unsafe_blocked",
        "copy_safe_export_hash": "verified-hash",
        "secret_scan": {"secret_like_value_detected": False},
        "blocking_count": blocking_count,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _v146_disagreement(state: str = "needs_review", blocking_count: int = 0) -> dict:
    return {
        "explorer_state": state,
        "categories": ["availability"],
        "blocking_count": blocking_count,
        "warning_count": 1,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def test_v146_openalgo_safe_intent_binding_allows_inspection_only():
    from app.behavior.jarvis_openalgo_safe_intent_binding import build_openalgo_safe_intent_binding

    report = build_openalgo_safe_intent_binding(
        symbol="RELIANCE",
        jarvis_room={"symbol": "RELIANCE", "final_action": "WAIT", "trade_vision_decision": {"final_trade_decision": "WAIT"}, "safety_summary": {"blocking_gates": []}},
        verified_review_packet=_v146_verified(),
        disagreement_explorer=_v146_disagreement(),
        openalgo_handoff_gate=_v146_handoff(),
        openalgo_paper_bridge=_v146_bridge(inspect=True),
    )
    assert report["binding_version"] == "jarvis-openalgo-safe-intent-binding.v1.46"
    assert report["preview_state"] == "paper_review_preview_ready"
    assert report["openalgo_may_inspect"] is True
    assert report["openalgo_may_execute"] is False
    assert report["can_export_to_openalgo"] is False


def test_v146_openalgo_safe_intent_binding_blocks_hard_disagreement():
    from app.behavior.jarvis_openalgo_safe_intent_binding import build_openalgo_safe_intent_binding

    report = build_openalgo_safe_intent_binding(
        symbol="RELIANCE",
        jarvis_room={"symbol": "RELIANCE", "final_action": "NO_TRADE", "trade_vision_decision": {"final_trade_decision": "NO_TRADE"}, "safety_summary": {"blocking_gates": ["risk"]}},
        verified_review_packet=_v146_verified(),
        disagreement_explorer=_v146_disagreement(state="hard_conflict", blocking_count=1),
        openalgo_handoff_gate=_v146_handoff(),
        openalgo_paper_bridge=_v146_bridge(inspect=True),
    )
    assert report["preview_state"] == "blocked"
    assert any(gate["gate_id"] == "OASIB-003" and gate["passed"] is False for gate in report["gates"])
    assert report["openalgo_may_inspect"] is False


def test_v146_openalgo_safe_intent_binding_blocks_executable_intent_flag():
    from app.behavior.jarvis_openalgo_safe_intent_binding import build_openalgo_safe_intent_binding

    report = build_openalgo_safe_intent_binding(
        symbol="RELIANCE",
        jarvis_room={"symbol": "RELIANCE", "final_action": "WAIT", "trade_vision_decision": {"final_trade_decision": "WAIT"}, "safety_summary": {"blocking_gates": []}},
        verified_review_packet=_v146_verified(),
        disagreement_explorer=_v146_disagreement(),
        openalgo_handoff_gate=_v146_handoff(export_allowed=True),
        openalgo_paper_bridge=_v146_bridge(inspect=True),
    )
    assert report["preview_state"] == "blocked"
    assert any(gate["gate_id"] == "OASIB-006" and gate["passed"] is False for gate in report["gates"])
    assert report["intent_preview"]["export_allowed"] is False


def _v147_room() -> dict:
    return {
        "symbol": "RELIANCE",
        "final_action": "WAIT",
        "trade_vision_decision": {"final_trade_decision": "WAIT"},
        "safety_summary": {"blocking_gates": []},
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _v147_freshness(action: str = "WAIT") -> dict:
    return {
        "freshness_state": "fresh",
        "safe_display_action": action,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _v147_decision_quality() -> dict:
    return {
        "quality_state": "manual_review_required",
        "quality_hash": "quality-hash",
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
    }


def _v147_final_audit(live_ready: bool = False, live_blocked: bool = True) -> dict:
    return {
        "overall_state": "research_ready_live_blocked",
        "live_ready": live_ready,
        "live_trading_blocked": live_blocked,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "can_execute_orders": False,
    }


def test_v147_paper_ready_safety_audit_reports_paper_review_ready_live_blocked():
    from app.behavior.jarvis_paper_ready_safety_audit import build_jarvis_paper_ready_safety_audit

    report = build_jarvis_paper_ready_safety_audit(
        symbol="RELIANCE",
        jarvis_room=_v147_room(),
        realtime_freshness=_v147_freshness(),
        decision_quality=_v147_decision_quality(),
        verified_review_packet=_v146_verified(),
        provider_disagreement=_v146_disagreement(state="needs_review", blocking_count=0),
        openalgo_safe_binding={
            **build_v146_binding_fixture(),
            "preview_state": "paper_review_preview_ready",
            "openalgo_may_inspect": True,
        },
        final_production_audit=_v147_final_audit(),
    )
    assert report["paper_ready_audit_version"] == "jarvis-paper-ready-safety-audit.v1.47"
    assert report["final_state"] == "paper_review_ready_live_blocked"
    assert report["go_no_go"]["live_broker_trading"] == "NO_GO"
    assert report["trade_allowed"] is False
    assert report["can_export_to_openalgo"] is False


def build_v146_binding_fixture() -> dict:
    return {
        "preview_state": "paper_review_preview_ready",
        "binding_hash": "binding-hash",
        "openalgo_may_inspect": True,
        "openalgo_may_execute": False,
        "trading_bot_may_execute": False,
        "external_human_approval_required": True,
        "external_risk_check_required": True,
        "external_account_state_required": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
    }


def test_v147_paper_ready_safety_audit_blocks_hard_provider_disagreement():
    from app.behavior.jarvis_paper_ready_safety_audit import build_jarvis_paper_ready_safety_audit

    report = build_jarvis_paper_ready_safety_audit(
        symbol="RELIANCE",
        jarvis_room=_v147_room(),
        realtime_freshness=_v147_freshness(),
        decision_quality=_v147_decision_quality(),
        verified_review_packet=_v146_verified(),
        provider_disagreement=_v146_disagreement(state="hard_conflict", blocking_count=1),
        openalgo_safe_binding=build_v146_binding_fixture(),
        final_production_audit=_v147_final_audit(),
    )
    assert report["final_state"] == "blocked"
    assert any(gate["gate_id"] == "PAPER-AUDIT-005" and gate["passed"] is False for gate in report["gates"])
    assert report["paper_review_ready"] is False


def test_v147_paper_ready_safety_audit_blocks_live_ready_artifact():
    from app.behavior.jarvis_paper_ready_safety_audit import build_jarvis_paper_ready_safety_audit

    report = build_jarvis_paper_ready_safety_audit(
        symbol="RELIANCE",
        jarvis_room=_v147_room(),
        realtime_freshness=_v147_freshness(),
        decision_quality=_v147_decision_quality(),
        verified_review_packet=_v146_verified(),
        provider_disagreement=_v146_disagreement(state="needs_review", blocking_count=0),
        openalgo_safe_binding=build_v146_binding_fixture(),
        final_production_audit=_v147_final_audit(live_ready=True, live_blocked=False),
    )
    assert report["final_state"] == "blocked"
    assert any(gate["gate_id"] == "PAPER-AUDIT-007" and gate["passed"] is False for gate in report["gates"])
    assert report["live_ready"] is False


def test_ai_credentials_status_exposes_local_secret_key_path(monkeypatch, tmp_path):
    secret_file = tmp_path / "tradevision_secret_key.local.txt"
    monkeypatch.delenv("TRADEVISION_SECRET_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_SECRET_KEY_FILE", str(secret_file))
    result = client.get("/api/v1/ai/credentials/status").json()["data"]
    assert result["local_secret_key_path"] == str(secret_file)
    assert result["secret_key_source"] == "missing"
    assert result["vault_locked"] is True


def test_ai_credentials_can_use_local_secret_key_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "tradevision_secret_key.local.txt"
    vault_file = tmp_path / "ai_credentials.enc"
    secret_file.write_text("local-test-secret-key-for-vault", encoding="utf-8")
    monkeypatch.delenv("TRADEVISION_SECRET_KEY", raising=False)
    monkeypatch.setenv("TRADEVISION_SECRET_KEY_FILE", str(secret_file))
    monkeypatch.setenv("TRADEVISION_AI_CREDENTIAL_VAULT_PATH", str(vault_file))
    result = client.post("/api/v1/ai/credentials/gemini", json={"slot": 1, "api_key": "AIzaSyDemoLocalGeminiKey123456789"}).json()["data"]
    assert result["vault_locked"] is False
    assert result["secret_key_source"] == "TRADEVISION_SECRET_KEY_FILE"
    assert result["gemini"]["configured_slots"] == 1
    assert vault_file.exists()


def test_grok_gateway_status_is_localhost_only_and_safe(monkeypatch):
    monkeypatch.setenv("TRADEVISION_GROK_GATEWAY_URL", "http://127.0.0.1:3210")
    result = client.get("/api/v1/jarvis/grok-gateway/status").json()["data"]
    assert result["provider"] == "grok_gateway"
    assert result["url_valid"] is True
    assert result["localhost_only"] is True
    assert result["gateway_url_masked"] == "http://127.0.0.1:3210"
    assert result["single_box_paths"]["gateway_config_path"].endswith("grok_gateway.local.json")
    assert result["single_box_paths"]["official_api_key_vault_path"].endswith("ai_credentials.enc")
    assert result["single_box_paths"]["browser_username_password_supported"] is False
    assert result["single_box_paths"]["manual_edit_allowed_for_gateway_config"] is True
    assert result["security"]["frontend_username_password_form_allowed"] is False
    assert result["security"]["trade_vision_stores_grok_password"] is False
    assert result["security"]["cookie_capture_allowed"] is False
    assert result["security"]["passgrok_capture_code_vendored_into_core"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True


def test_grok_gateway_rejects_remote_gateway_url(monkeypatch):
    monkeypatch.setenv("TRADEVISION_GROK_GATEWAY_URL", "https://grok.example.com")
    result = client.get("/api/v1/jarvis/grok-gateway/status").json()["data"]
    assert result["url_valid"] is False
    assert result["gateway_state"] == "blocked_invalid_gateway_url"
    assert result["url_error"] in {"only_http_localhost_gateway_allowed", "gateway_must_be_localhost_or_127_0_0_1"}
    assert result["can_execute_orders"] is False


def test_grok_gateway_config_file_does_not_accept_browser_secrets(monkeypatch, tmp_path):
    config_path = tmp_path / "grok_gateway.local.json"
    config_path.write_text(
        json.dumps({
            "gateway_url": "http://127.0.0.1:8899",
            "model": "grok/grok-4-fast",
            "username": "user@example.com",
            "password": "secret",
            "cookie": "hidden",
        }),
        encoding="utf-8",
    )
    monkeypatch.delenv("TRADEVISION_GROK_GATEWAY_URL", raising=False)
    monkeypatch.setenv("TRADEVISION_GROK_GATEWAY_CONFIG_PATH", str(config_path))
    result = client.get("/api/v1/jarvis/grok-gateway/status").json()["data"]
    assert result["url_valid"] is True
    assert result["single_box_paths"]["gateway_config_file_exists"] is True
    assert result["single_box_paths"]["browser_username_password_supported"] is False
    assert result["single_box_paths"]["browser_session_cookie_supported"] is False
    assert result["single_box_paths"]["unsupported_secret_keys_detected"] == ["cookie", "password", "username"]


def test_grok_gateway_review_timeout_fails_safe(monkeypatch):
    import httpx
    from app.behavior import grok_gateway_provider

    async def fake_timeout(url, request):
        raise httpx.ReadTimeout("slow grok gateway")

    monkeypatch.setenv("TRADEVISION_GROK_GATEWAY_URL", "http://127.0.0.1:3210")
    monkeypatch.setattr(grok_gateway_provider, "_post_gateway_chat", fake_timeout)
    result = client.post("/api/v1/jarvis/grok-gateway/review/RELIANCE", json={"execute": True}).json()["data"]
    assert result["thinking_state"] == "timeout"
    assert result["safe_final_action"] == "TRADE_VISION_ONLY"
    assert result["display_allowed"] is False
    assert result["trade_allowed"] is False
    assert result["order_routing_enabled"] is False
    assert result["live_trading_blocked"] is True
    assert any(gate["gate_id"] == "GROK-GW-003" and gate["passed"] is False for gate in result["gates"])


def test_grok_gateway_redacts_sensitive_packet_fields():
    from app.behavior.grok_gateway_provider import _redact_sensitive

    packet = {
        "api_key": "secret",
        "cookie": "abc",
        "broker_credentials_present": False,
        "nested": {"session_token": "tok", "decision": "WAIT"},
    }
    redacted = _redact_sensitive(packet)
    assert redacted["api_key"] == "[REDACTED_BY_TRADE_VISION]"
    assert redacted["cookie"] == "[REDACTED_BY_TRADE_VISION]"
    assert redacted["broker_credentials_present"] is False
    assert redacted["nested"]["session_token"] == "[REDACTED_BY_TRADE_VISION]"
    assert redacted["nested"]["decision"] == "WAIT"
