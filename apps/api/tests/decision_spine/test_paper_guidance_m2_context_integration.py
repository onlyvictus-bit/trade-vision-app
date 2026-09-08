from __future__ import annotations

from copy import deepcopy

import pytest

from app.behavior import paper_guidance_spine_legacy as legacy_spine
from app.behavior.paper_guidance_config import PaperGuidanceConfig
from app.behavior.paper_guidance_spine import run_paper_guidance_p1
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import (
    CandleBar,
    CandleSeries,
    KillSwitchState,
    PaperGuidanceRequest,
    SystemMode,
    SystemModeValue,
)


BASE_NS = 1_714_815_600_000_000_000


def _mode() -> SystemMode:
    return SystemMode(
        mode=SystemModeValue.MOCK,
        display_label="Mock research",
        immutable=True,
        allows_live_orders=False,
        allows_broker_credentials=False,
        watermark_text="MOCK - NO REAL MONEY",
    )


def _kill_switch() -> KillSwitchState:
    return KillSwitchState(
        state="armed",
        reason=None,
        source=None,
        actor_id=None,
        triggered_at=None,
        blocks_order_paths=False,
    )


def _series(*, last_close_delta: float = 0.0) -> CandleSeries:
    duration = timeframe_duration_ns("5m")
    rows = []
    for index in range(40):
        open_price = 100.0 + index * 0.08
        close = open_price + (0.06 if index % 4 else -0.02)
        if index == 39:
            close += last_close_delta
        rows.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe="5m",
                timestamp_ns=BASE_NS + index * duration,
                open=open_price,
                high=max(open_price, close) + 0.10,
                low=min(open_price, close) - 0.08,
                close=close,
                volume=100_000.0 + index * 700.0,
                source="user_csv",
                sequence_number=index + 1,
            )
        )
    return CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=rows,
        snapshot_id="m2-integration",
        schema_version="candles.v1",
    )


def _request(series: CandleSeries | None = None) -> PaperGuidanceRequest:
    series = series or _series()
    decision = series.bars[-1].timestamp_ns + timeframe_duration_ns("5m")
    return PaperGuidanceRequest(
        symbol="RELIANCE",
        timeframe="5m",
        series=series,
        decision_time_ns=decision,
        higher_timeframe_series=[],
        required_higher_timeframes=[],
        indicator_ids=["si_vwap_conf"],
        historical_match_count=999,
    )


@pytest.fixture(autouse=True)
def _fast_pure_dependencies(monkeypatch):
    def fake_runtime(candles, indicator_ids):
        return (
            {indicator_id: {"last": len(candles)} for indicator_id in indicator_ids},
            [
                {
                    "indicator_id": indicator_id,
                    "status": "computed",
                    "latency_ms": 0.1,
                    "source_latency_ms": 0.1,
                    "output_present": True,
                    "used_for_9c_vector": True,
                    "cache_hit": False,
                    "cache_version": "m2-test",
                    "error": None,
                }
                for indicator_id in indicator_ids
            ],
        )

    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.compute_real_indicator_outputs_with_telemetry",
        fake_runtime,
    )
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.list_indicator_signal_history_records",
        lambda **_: [],
    )


def _run(request: PaperGuidanceRequest):
    return run_paper_guidance_p1(
        request,
        mode=_mode(),
        kill_switch=_kill_switch(),
        config=PaperGuidanceConfig(),
    )


def test_m2_pg_001_real_pipeline_emits_compact_canonical_context_audit():
    result = _run(_request())
    context = result.risk_summary["decision_context"]
    stage2 = result.risk_summary["stage2_integrity"]
    assert context is not None
    assert context["snapshot_hash"] == result.snapshot_hash
    assert context["stage2_integrity_hash"] == stage2["output_hash"]
    assert len(context["context_hash"]) == 64
    assert context["evidence"]["field_count"] == 22
    assert context["safety"]["paper_promotion_eligible"] is False
    assert context["safety"]["trade_allowed"] is False
    assert context["safety"]["order_routing_enabled"] is False
    assert context["safety"]["live_trading_blocked"] is True


def test_m2_pg_002_same_request_replays_same_d2_stage2_context_and_guidance():
    request = _request()
    first = _run(request)
    second = _run(request)
    assert first.snapshot_hash == second.snapshot_hash
    assert first.risk_summary["stage2_integrity"]["output_hash"] == second.risk_summary["stage2_integrity"]["output_hash"]
    assert first.risk_summary["decision_context"]["context_hash"] == second.risk_summary["decision_context"]["context_hash"]
    assert first.guidance_id == second.guidance_id
    assert first.final_band == second.final_band
    assert first.arbiter_summary == second.arbiter_summary


def test_m2_pg_003_changed_closed_candle_changes_d2_and_context_hash():
    first = _run(_request(_series(last_close_delta=0.0)))
    second = _run(_request(_series(last_close_delta=0.03)))
    assert first.snapshot_hash != second.snapshot_hash
    assert first.risk_summary["decision_context"]["context_hash"] != second.risk_summary["decision_context"]["context_hash"]


def test_m2_pg_004_stage2_inventory_activates_m31_candle_anatomy_only():
    result = _run(_request())
    states = {
        item["engine_id"]: item
        for item in result.risk_summary["stage2_integrity"]["engine_states"]
    }
    assert states["CANDLE_ANATOMY"]["availability"] == "AVAILABLE"
    assert states["CANDLE_ANATOMY"]["source_mode"] == "VERIFIED_SNAPSHOT"
    assert states["CANDLE_ANATOMY"]["used_for_probability"] is False
    assert states["SECTOR_CONTEXT"]["availability"] == "UNAVAILABLE"
    assert states["RELATIVE_STRENGTH"]["availability"] == "UNAVAILABLE"
    assert states["DERIVATIVES"]["availability"] == "UNAVAILABLE"
    assert states["FAILURE_DETECTOR"]["availability"] == "UNAVAILABLE"
    assert states["ORB_CORE"]["availability"] == "SKIPPED"
    assert states["AFRE"]["availability"] == "SKIPPED"
    for engine_id in (
        "SECTOR_CONTEXT",
        "RELATIVE_STRENGTH",
        "DERIVATIVES",
        "FAILURE_DETECTOR",
        "ORB_CORE",
        "AFRE",
    ):
        assert states[engine_id]["unavailable_reasons"]
        assert states[engine_id]["used_for_probability"] is False


def test_m2_pg_005_unknown_freshness_is_visible_not_neutralized():
    result = _run(_request())
    integrity = result.risk_summary["decision_context"]["integrity"]
    assert integrity["pit_status"] == "PASS"
    assert integrity["freshness"] == "UNKNOWN"
    assert integrity["quarantine_status"] == "UNKNOWN"
    joined = " ".join(integrity["reasons"]).lower()
    assert "freshness" in joined
    assert "quarantine" in joined


def test_m2_pg_006_context_failure_stops_before_d6(monkeypatch):
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.build_paper_guidance_decision_context",
        lambda **_: (_ for _ in ()).throw(RuntimeError("forced-context-failure")),
    )
    with pytest.raises(RuntimeError, match="forced-context-failure"):
        _run(_request())


def test_m2_pg_007_contract_context_failure_returns_wait_before_d6(monkeypatch):
    from app.behavior.decision_spine.decision_context import DecisionContextError

    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.build_paper_guidance_decision_context",
        lambda **_: (_ for _ in ()).throw(DecisionContextError("forced-contract-block")),
    )
    result = _run(_request())
    assert result.final_band == "WAIT"
    assert result.next_action == "DO_NOTHING"
    assert "FINAL_CONFLUENCE_ARBITER" not in result.engines_run
    assert "D6_ARBITER:decision_context_block" in result.engines_skipped
    assert result.arbiter_summary["arbiter_run"] is False
    assert result.risk_summary["decision_context"] is None
    assert any("forced-contract-block" in blocker for blocker in result.blockers)


def test_m2_pg_008_d6_remains_the_only_final_band_engine():
    result = _run(_request())
    assert result.engine_receipts[-1].engine_id == "FINAL_CONFLUENCE_ARBITER"
    assert result.final_band == result.arbiter_summary["final_decision"]
    assert result.risk_summary["decision_context"]["safety"]["trade_allowed"] is False


def test_m2_pg_009_context_audit_stays_bounded_during_m31_migration():
    result = _run(_request())
    audit = deepcopy(result.risk_summary["decision_context"])
    assert "price_structure" not in audit
    assert "indicators" not in audit
    assert "derivatives" not in audit
    assert set(audit) == {
        "adapter_version",
        "context_version",
        "context_hash",
        "snapshot_hash",
        "stage2_integrity_hash",
        "integrity",
        "evidence",
        "safety",
        "calculation_audit",
    }
    assert audit["calculation_audit"] == {
        "feature_kernel_build_count": 1,
        "candle_anatomy_compute_count": 1,
        "decision_context_build_count": 1,
    }


def test_m2_pg_010_d6_semantics_match_preserved_pre_m2_route():
    request = _request()

    # M3.1 adds receipts/provenance, so guidance identity and receipt lists are
    # expected to change. The locked parity requirement is D6 input/output
    # behavior: no migration-stage candle plumbing may change the final arbiter.
    migrated_result = _run(request)
    legacy_result = legacy_spine.run_paper_guidance_p1(
        request,
        mode=_mode(),
        kill_switch=_kill_switch(),
        config=PaperGuidanceConfig(),
    )

    assert migrated_result.snapshot_hash == legacy_result.snapshot_hash
    assert migrated_result.final_band == legacy_result.final_band
    assert migrated_result.confidence_cap == legacy_result.confidence_cap
    assert migrated_result.next_action == legacy_result.next_action
    assert migrated_result.arbiter_summary == legacy_result.arbiter_summary

    migrated_receipts = {item.engine_id: item for item in migrated_result.engine_receipts}
    legacy_receipts = {item.engine_id: item for item in legacy_result.engine_receipts}
    for engine_id in (
        "CHART_REASONING",
        "CANDLE_CONDITION",
        "LEVEL_CONTEXT",
        "SNAPSHOT_INDICATOR_RUNTIME",
        "MTF_CONFIRMATION",
        "PERSISTED_INDICATOR_MEMORY",
        "MARKET_STRUCTURE_LIQUIDITY",
        "EXECUTION_EVENT_OI_RISK",
        "FINAL_CONFLUENCE_ARBITER",
    ):
        assert migrated_receipts[engine_id].status == legacy_receipts[engine_id].status
