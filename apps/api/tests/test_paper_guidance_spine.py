from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.behavior.paper_guidance_config import PaperGuidanceConfig
from app.behavior.paper_guidance_spine import run_paper_guidance_p0
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.behavior.shared_snapshot import build_shared_snapshot
from app.main import app
from app.models import (
    CandleBar,
    CandleSeries,
    KillSwitchState,
    PaperGuidanceRequest,
    PaperTradeGuidance,
    SharedSnapshotRequest,
    SystemMode,
    SystemModeValue,
)


client = TestClient(app)
BASE_TIMESTAMP_NS = 1_714_815_600_000_000_000
REQUIRED_TIMEFRAMES = ("1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily")


def _research_mode() -> SystemMode:
    return SystemMode(
        mode=SystemModeValue.MOCK,
        display_label="Mock research",
        immutable=True,
        allows_live_orders=False,
        allows_broker_credentials=False,
        watermark_text="MOCK - NO REAL MONEY",
    )


def _armed_kill_switch() -> KillSwitchState:
    return KillSwitchState(
        state="armed",
        reason=None,
        source=None,
        actor_id=None,
        triggered_at=None,
        blocks_order_paths=False,
    )


def _series(
    timeframe: str = "5m",
    *,
    bars: int = 12,
    last_close_delta_ns: int = 0,
) -> CandleSeries:
    duration_ns = timeframe_duration_ns(timeframe)  # type: ignore[arg-type]
    rows: list[CandleBar] = []
    for index in range(bars):
        open_price = 100.0 + index * 0.2
        close_price = open_price + 0.1
        rows.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe=timeframe,
                timestamp_ns=BASE_TIMESTAMP_NS + index * duration_ns,
                open=open_price,
                high=close_price + 0.2,
                low=open_price - 0.2,
                close=close_price,
                volume=100_000.0 + index * 1_000.0,
                source="user_csv",
                sequence_number=index + 1,
            )
        )
    if last_close_delta_ns:
        rows[-1] = rows[-1].model_copy(
            update={"timestamp_ns": rows[-1].timestamp_ns + last_close_delta_ns}
        )
    return CandleSeries(
        symbol="RELIANCE",
        timeframe=timeframe,
        bars=rows,
        snapshot_id="fixture-reliance",
        schema_version="candles.v1",
    )


def _request(
    timeframe: str = "5m",
    *,
    series: CandleSeries | None = None,
    decision_time_ns: int | None = None,
    matches: int = 0,
) -> PaperGuidanceRequest:
    candle_series = series or _series(timeframe)
    return PaperGuidanceRequest(
        symbol="RELIANCE",
        timeframe=timeframe,
        series=candle_series,
        decision_time_ns=decision_time_ns,
        historical_match_count=matches,
    )


def _run(request: PaperGuidanceRequest) -> PaperTradeGuidance:
    return run_paper_guidance_p0(
        request,
        mode=_research_mode(),
        kill_switch=_armed_kill_switch(),
        config=PaperGuidanceConfig(),
    )


def test_tv_v187_001_same_input_is_fully_deterministic():
    request = _request(matches=42)

    first = _run(request)
    second = _run(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.snapshot_hash == second.snapshot_hash
    assert first.guidance_id == second.guidance_id
    assert first.snapshot is not None
    assert len(first.snapshot.snapshot_hash) == 64


def test_tv_v187_002_snapshot_hash_changes_when_closed_bar_changes():
    original = _series()
    changed_bars = list(original.bars)
    changed_bars[-1] = changed_bars[-1].model_copy(
        update={
            "high": changed_bars[-1].high + 0.5,
            "close": changed_bars[-1].close + 0.25,
        }
    )
    changed = original.model_copy(update={"bars": changed_bars})

    original_result = _run(_request(series=original, matches=42))
    changed_result = _run(_request(series=changed, matches=42))

    assert original_result.snapshot_hash != changed_result.snapshot_hash
    assert original_result.guidance_id != changed_result.guidance_id


def test_tv_v187_003_d1_failure_stops_before_snapshot_hash():
    series = _series()
    duration_ns = timeframe_duration_ns("5m")
    decision_time_ns = series.bars[-1].timestamp_ns + duration_ns - 1

    result = _run(_request(series=series, decision_time_ns=decision_time_ns))

    assert result.final_band == "WAIT"
    assert result.snapshot is None
    assert result.snapshot_hash is None
    assert result.safety_gate.stop_pipeline is True
    assert result.point_in_time.incomplete_candle_blocked == 1
    assert result.engines_run == ["D1_SAFETY_GATE"]
    assert result.engines_skipped[0] == "D2_CLOSED_CANDLE_SNAPSHOT"


def test_tv_v187_004_invalid_ohlc_blocks_guidance_before_d2():
    series = _series()
    broken_bars = list(series.bars)
    broken_bars[3] = broken_bars[3].model_copy(
        update={"high": broken_bars[3].open - 0.1}
    )
    broken = series.model_copy(update={"bars": broken_bars})

    result = _run(_request(series=broken))

    assert result.final_band == "WAIT"
    assert result.snapshot_hash is None
    assert result.data_quality.invalid_ohlc_count == 1
    assert result.data_quality.blocks_trade is True


def test_tv_v187_005_kill_switch_blocks_before_d2():
    triggered = KillSwitchState(
        state="triggered",
        reason="test",
        source="risk_engine",
        actor_id="qa",
        triggered_at="2026-07-23T00:00:00+00:00",
        blocks_order_paths=True,
    )

    result = run_paper_guidance_p0(
        _request(),
        mode=_research_mode(),
        kill_switch=triggered,
        config=PaperGuidanceConfig(),
    )

    assert result.final_band == "WAIT"
    assert result.snapshot_hash is None
    assert result.safety_gate.passed is False
    assert "Kill switch is armed" in result.blockers


def test_tv_v187_006_low_evidence_cannot_become_enter_paper():
    result = _run(_request(matches=29))

    assert result.final_band == "WATCH"
    assert result.final_band != "ENTER_PAPER"
    assert result.low_evidence_flag is True
    assert result.confidence_cap <= 0.55
    assert result.entry_plan is None
    assert result.next_action == "DO_NOTHING"


def test_tv_v187_007_high_evidence_is_still_watch_in_p0():
    result = _run(_request(matches=250))

    assert result.final_band == "WATCH"
    assert result.low_evidence_flag is False
    assert result.confidence_cap <= 0.60
    assert result.trade_allowed is False
    assert result.paper_execution_attempted is False
    assert result.auto_paper_fill_enabled is False
    assert result.broker_order_created is False
    assert result.order_routing_enabled is False
    assert result.live_trading_blocked is True


@pytest.mark.parametrize("timeframe", REQUIRED_TIMEFRAMES)
def test_tv_v187_008_required_mtf_close_semantics(timeframe: str):
    series = _series(timeframe, bars=3)
    duration_ns = timeframe_duration_ns(timeframe)  # type: ignore[arg-type]
    decision_time_ns = series.bars[-1].timestamp_ns + duration_ns

    result = _run(
        _request(
            timeframe,
            series=series,
            decision_time_ns=decision_time_ns,
            matches=30,
        )
    )

    assert result.safety_gate.passed is True
    assert result.snapshot is not None
    assert result.snapshot.bar_count == 3
    assert result.snapshot.last_bar_close_time_ns == decision_time_ns
    assert result.point_in_time.blocked_bars == 0


def test_tv_v187_009_contract_rejects_execution_flag_overrides():
    result = _run(_request(matches=100))
    unsafe = result.model_dump(mode="json")
    unsafe["trade_allowed"] = True
    unsafe["order_routing_enabled"] = True
    unsafe["broker_order_created"] = True

    with pytest.raises(ValidationError):
        PaperTradeGuidance.model_validate(unsafe)


def test_tv_v187_010_api_returns_research_only_envelope():
    payload = _request(matches=100).model_dump(mode="json")

    response = client.post("/api/v1/paper-guidance/run", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["capability_status"] == "mock"
    assert body["data"]["final_band"] in {"WAIT", "WATCH"}
    assert body["data"]["trade_allowed"] is False
    assert body["data"]["paper_execution_attempted"] is False
    assert body["data"]["auto_paper_fill_enabled"] is False
    assert body["data"]["broker_credentials_present"] is False
    assert body["data"]["broker_order_created"] is False
    assert body["data"]["order_routing_enabled"] is False
    assert body["data"]["live_trading_blocked"] is True


def test_tv_v187_011_openapi_and_manifest_publish_p0_contract():
    openapi = client.get("/openapi.json").json()
    assert "/api/v1/paper-guidance/run" in openapi["paths"]
    schemas = openapi["components"]["schemas"]
    assert "PaperGuidanceRequest" in schemas
    assert "PaperTradeGuidance" in schemas
    assert "ClosedCandleSnapshot" in schemas

    manifest = client.get("/api/system/features").json()["data"]["capabilities"]
    paper_guidance = next(
        capability
        for capability in manifest
        if capability["name"] == "Paper Guidance Spine P0"
    )
    assert paper_guidance["status"] == "mock"
    assert paper_guidance["required_for_startup"] is True


def test_tv_v187_012_spine_has_no_execution_or_broker_imports():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "behavior"
        / "paper_guidance_spine.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden_fragments = (
        "openalgo",
        "order_guard",
        "execution_sim",
        "paper_execution",
        "broker",
    )

    assert not any(
        fragment in module_name.lower()
        for module_name in imported_modules
        for fragment in forbidden_fragments
    )


def test_tv_v187_013_shared_snapshot_sibling_excludes_incomplete_candle():
    series = _series("5m", bars=16)
    duration_ns = timeframe_duration_ns("5m")
    decision_time_ns = series.bars[-1].timestamp_ns + duration_ns - 1

    snapshot, normalized = build_shared_snapshot(
        SharedSnapshotRequest(
            symbol="RELIANCE",
            timeframe="5m",
            lookback_candles=16,
            decision_time_ns=decision_time_ns,
            series=series,
        )
    )

    assert len(snapshot.closed_ohlcv_bars) == 15
    assert len(normalized.bars) == 15
    assert snapshot.last_bar_timestamp_ns == series.bars[-2].timestamp_ns
    assert all(
        bar.timestamp_ns + duration_ns <= decision_time_ns
        for bar in snapshot.closed_ohlcv_bars
    )
