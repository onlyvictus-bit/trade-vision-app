from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.behavior.final_confluence_arbiter import build_final_confluence_arbiter_report
from app.behavior.paper_guidance_config import PaperGuidanceConfig
from app.behavior.paper_guidance_spine import run_paper_guidance_p1
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.main import app
from app.models import (
    CandleBar,
    CandleSeries,
    FinalConfluenceArbiterRequest,
    IndicatorSignalHistoryRecord,
    IndicatorSignalOutcomeLabel,
    KillSwitchState,
    PaperGuidanceRequest,
    SystemMode,
    SystemModeValue,
)


client = TestClient(app)
BASE_NS = 1_714_815_600_000_000_000
ENGINE_ORDER = [
    "CANDLE_ANATOMY",
    "CHART_REASONING",
    "CANDLE_CONDITION",
    "LEVEL_CONTEXT",
    "SNAPSHOT_INDICATOR_RUNTIME",
    "MTF_CONFIRMATION",
    "PERSISTED_INDICATOR_MEMORY",
    "MARKET_STRUCTURE_LIQUIDITY",
    "EXECUTION_EVENT_OI_RISK",
    "FINAL_CONFLUENCE_ARBITER",
]


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


def _series(timeframe: str = "5m", bars: int = 40) -> CandleSeries:
    duration = timeframe_duration_ns(timeframe)  # type: ignore[arg-type]
    rows = []
    for index in range(bars):
        open_price = 100.0 + index * 0.08
        close = open_price + (0.06 if index % 4 else -0.02)
        rows.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe=timeframe,
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
        timeframe=timeframe,
        bars=rows,
        snapshot_id=f"fixture-{timeframe}",
        schema_version="candles.v1",
    )


def _request(
    *,
    primary: CandleSeries | None = None,
    decision_time_ns: int | None = None,
    higher: list[CandleSeries] | None = None,
    required: list[str] | None = None,
    matches: int = 0,
) -> PaperGuidanceRequest:
    series = primary or _series()
    return PaperGuidanceRequest(
        symbol="RELIANCE",
        timeframe=series.timeframe,
        series=series,
        decision_time_ns=decision_time_ns,
        higher_timeframe_series=higher or [],
        required_higher_timeframes=required or [],
        indicator_ids=["si_vwap_conf"],
        historical_match_count=matches,
    )


@pytest.fixture(autouse=True)
def _fast_indicator_runtime(monkeypatch):
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
                    "cache_version": "test",
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


def _history(
    history_id: str,
    *,
    status: str = "complete",
    decision_time_ns: int = BASE_NS,
    created_at_ns: int = BASE_NS,
) -> IndicatorSignalHistoryRecord:
    label = IndicatorSignalOutcomeLabel(
        label_version="test",
        label_id=f"label-{history_id}",
        indicator_id="si_vwap_conf",
        symbol="RELIANCE",
        timeframe="5m",
        signal_direction="bullish",
        signal_time_ns=decision_time_ns,
        horizon_candles=9,
        label_status=status,
        outcome_label="TARGET_HIT" if status == "complete" else "TIME_EXIT",
        target_first=status == "complete",
        stop_first=False,
        same_bar_ambiguous=False,
        conservative_stop_first_used=False,
        mfe=1.0,
        mae=0.2,
        counted_as_win=status == "complete",
        counted_as_failure=False,
        counted_in_reliability=status == "complete",
        reason="test",
    )
    return IndicatorSignalHistoryRecord(
        history_version="test",
        history_id=history_id,
        symbol="RELIANCE",
        indicator_id="si_vwap_conf",
        timeframe="5m",
        signal_direction="bullish",
        signal_time_ns=decision_time_ns,
        decision_time_ns=decision_time_ns,
        session_phase="establishment",
        regime_id="trend",
        feature_manifest_version="v1",
        indicator_registry_version="v1",
        signal_strength=0.7,
        missing_mask=False,
        label=label,
        counted_in_reliability=status == "complete",
        created_at=datetime.fromtimestamp(
            created_at_ns / 1_000_000_000, tz=timezone.utc
        ).isoformat(),
        no_future_leakage=True,
    )


def test_tv_v188_001_fixed_engine_order():
    result = _run(_request())
    assert [receipt.engine_id for receipt in result.engine_receipts] == ENGINE_ORDER


def test_tv_v188_002_every_receipt_matches_d2_snapshot():
    result = _run(_request())
    assert result.snapshot_hash
    assert all(
        receipt.source_snapshot_hash == result.snapshot_hash
        and receipt.identity_match
        for receipt in result.engine_receipts
    )


def test_tv_v188_003_output_hashes_and_guidance_are_deterministic():
    request = _request(matches=999)
    first = _run(request)
    second = _run(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [item.output_hash for item in first.engine_receipts] == [
        item.output_hash for item in second.engine_receipts
    ]


def test_tv_v188_004_incomplete_primary_candle_stops_before_d2():
    series = _series()
    decision = series.bars[-1].timestamp_ns + timeframe_duration_ns("5m") - 1
    result = _run(_request(primary=series, decision_time_ns=decision))
    assert result.final_band == "WAIT"
    assert result.snapshot is None
    assert result.point_in_time.incomplete_candle_blocked == 1


def test_tv_v188_005_incomplete_htf_candle_is_excluded():
    primary = _series()
    htf = _series("1H", bars=4)
    decision = htf.bars[-1].timestamp_ns + timeframe_duration_ns("1H") - 1
    result = _run(
        _request(
            primary=primary,
            decision_time_ns=decision,
            higher=[htf],
            required=["1H"],
        )
    )
    assert result.mtf_evidence
    assert result.mtf_evidence.usable_timeframes == ["1H"]
    assert result.mtf_evidence.indicator_runtime_by_timeframe["1H"]["source_bar_count"] == 3


@pytest.mark.parametrize("timeframe", ["1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily"])
def test_tv_v188_006_all_supported_mtf_identities_validate(timeframe: str):
    mtf = _series(timeframe, bars=3)
    primary = _series()
    decision = max(
        mtf.bars[-1].timestamp_ns + timeframe_duration_ns(timeframe),  # type: ignore[arg-type]
        primary.bars[-1].timestamp_ns + timeframe_duration_ns("5m"),
    )
    result = _run(
        _request(
            primary=primary,
            decision_time_ns=decision,
            higher=[mtf],
            required=[timeframe],
        )
    )
    assert result.mtf_evidence
    assert result.mtf_evidence.missing_required_timeframes == []
    assert timeframe in result.mtf_evidence.snapshot_hashes


def test_tv_v188_007_indicators_are_recalculated_for_supplied_timeframe():
    result = _run(
        _request(
            decision_time_ns=BASE_NS + 5 * timeframe_duration_ns("1H"),
            higher=[_series("1H", bars=3)],
            required=["1H"],
        )
    )
    runtime = result.mtf_evidence.indicator_runtime_by_timeframe["1H"]  # type: ignore[union-attr]
    assert runtime["indicator_ids"] == ["si_vwap_conf"]
    assert runtime["computed_count"] == 1
    assert runtime["source_bar_count"] == 3


def test_tv_v188_008_current_endpoint_substitution_is_forbidden():
    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "behavior"
        / "paper_guidance_spine.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("current" in item.lower() for item in imported)


def test_tv_v188_009_fixture_reliability_cannot_boost_confidence():
    result = _run(_request(matches=500))
    assert result.memory_summary["history_source"] == "persistent"
    assert result.memory_summary["fixture_fallback_used"] is False
    assert result.historical_match_count == 0
    assert result.low_evidence_flag is True


def test_tv_v188_010_only_completed_persisted_history_counts(monkeypatch):
    decision = BASE_NS + 40 * timeframe_duration_ns("5m")
    records = [
        _history("complete", decision_time_ns=BASE_NS, created_at_ns=BASE_NS),
        _history("pending", status="pending", decision_time_ns=BASE_NS, created_at_ns=BASE_NS),
    ]
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.list_indicator_signal_history_records",
        lambda **_: records,
    )
    result = _run(_request(decision_time_ns=decision))
    assert result.historical_match_count == 1


def test_tv_v188_011_history_created_after_decision_is_excluded(monkeypatch):
    decision = BASE_NS + 40 * timeframe_duration_ns("5m")
    records = [
        _history(
            "future-created",
            decision_time_ns=BASE_NS,
            created_at_ns=decision + 1_000_000_000,
        )
    ]
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.list_indicator_signal_history_records",
        lambda **_: records,
    )
    result = _run(_request(decision_time_ns=decision))
    assert result.historical_match_count == 0


def test_tv_v188_012_caller_match_count_cannot_bypass_memory():
    result = _run(_request(matches=999))
    assert result.memory_summary["caller_historical_match_count"] == 999
    assert result.memory_summary["caller_count_used_for_authority"] is False
    assert result.historical_match_count == 0


def test_tv_v188_013_low_evidence_caps_d6_after_aggregation():
    report = build_final_confluence_arbiter_report(
        FinalConfluenceArbiterRequest(
            liquidity_grade="A",
            market_regime_score=1.0,
            relative_strength_score=1.0,
            structure_score=1.0,
            volume_auction_score=1.0,
            indicator_signal_score=1.0,
            evidence_count=0,
            low_evidence_flag=True,
        )
    )
    assert report.final_decision == "WATCH"
    assert report.final_decision != "PAPER-CANDIDATE"


def test_tv_v188_014_missing_required_mtf_caps_watch():
    result = _run(_request(required=["1H"]))
    assert result.mtf_evidence
    assert result.mtf_evidence.missing_required_timeframes == ["1H"]
    assert result.final_band in {"WAIT", "WATCH", "AVOID"}
    assert result.final_band != "ENTER_PAPER"


def test_tv_v188_015_unavailable_event_oi_depth_cannot_look_clean():
    result = _run(_request())
    receipt = next(
        item
        for item in result.engine_receipts
        if item.engine_id == "EXECUTION_EVENT_OI_RISK"
    )
    assert receipt.output_summary["event_context_status"] == "unavailable"
    assert receipt.output_summary["options_context_status"] == "unavailable"
    assert receipt.output_summary["depth_context_status"] != "available"
    assert receipt.output_summary["unavailable_reasons"]


def test_tv_v188_016_conflicts_only_reduce_final_band():
    clean = build_final_confluence_arbiter_report(
        FinalConfluenceArbiterRequest(
            liquidity_grade="A",
            structure_score=0.8,
            indicator_signal_score=0.8,
            evidence_count=100,
        )
    )
    conflict = build_final_confluence_arbiter_report(
        FinalConfluenceArbiterRequest(
            liquidity_grade="A",
            structure_score=0.8,
            indicator_signal_score=0.8,
            evidence_count=100,
            daily_resistance_conflict=True,
        )
    )
    assert conflict.confluence_score <= clean.confluence_score


def test_tv_v188_017_d6_is_only_final_band_authority():
    result = _run(_request())
    assert result.arbiter_summary["final_decision"] in {"WAIT", "WATCH", "AVOID"}
    assert result.final_band == result.arbiter_summary["final_decision"]


def test_tv_v188_018_optional_engine_failure_degrades_safely(monkeypatch):
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.build_chart_reasoning_report",
        lambda *_: (_ for _ in ()).throw(RuntimeError("forced")),
    )
    result = _run(_request())
    receipt = next(
        item for item in result.engine_receipts if item.engine_id == "CHART_REASONING"
    )
    assert receipt.status == "degraded"
    assert result.final_band in {"WAIT", "WATCH", "AVOID"}


def test_tv_v188_019_no_execution_kronos_orb_openalgo_imports():
    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "behavior"
        / "paper_guidance_spine.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = ("openalgo", "kronos", "orb_", "paper_execution", "broker")
    assert not any(
        fragment in module.lower()
        for module in imported
        for fragment in forbidden
    )


def test_tv_v188_020_openapi_manifest_and_safety_literals():
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "PaperGuidanceEngineReceipt" in schemas
    assert "PaperGuidanceMtfEvidence" in schemas
    capabilities = client.get("/api/system/features").json()["data"]["capabilities"]
    p1 = next(item for item in capabilities if item["name"] == "Paper Guidance Spine P1")
    assert p1["status"] == "mock"
    result = _run(_request())
    assert result.trade_allowed is False
    assert result.paper_execution_attempted is False
    assert result.order_routing_enabled is False
    assert result.live_trading_blocked is True

def test_tv_v188_020_stage2_integrity_is_wired_before_d6():
    result = _run(_request())
    integrity = result.risk_summary["stage2_integrity"]
    assert integrity["canonical_snapshot_hash"] == result.snapshot_hash
    assert integrity["canonical_context_eligible"] is True
    assert integrity["paper_promotion_eligible"] is False
    assert integrity["trade_allowed"] is False
    assert integrity["order_routing_enabled"] is False
    assert integrity["live_trading_blocked"] is True
    assert "FINAL_CONFLUENCE_ARBITER" in result.engines_run
    states = {row["engine_id"]: row for row in integrity["engine_states"]}
    for engine_id in ("NINE_CANDLE_MEMORY", "PTA_MARKER_RUNTIME", "ORB_CORE", "AFRE"):
        assert states[engine_id]["availability"] == "SKIPPED"
        assert states[engine_id]["used_for_probability"] is False


def test_tv_v188_021_stage2_block_stops_before_d6(monkeypatch):
    class ForcedBlock:
        canonical_context_eligible = False
        hard_blockers = ("FORCED_STAGE2_BLOCK",)
        warnings = ("forced-stage2-warning",)
        output_hash = "f" * 64

        @staticmethod
        def as_dict():
            return {
                "status": "BLOCK",
                "canonical_context_eligible": False,
                "hard_blockers": ["FORCED_STAGE2_BLOCK"],
                "warnings": ["forced-stage2-warning"],
                "paper_promotion_eligible": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
            }

    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.build_stage2_integrity_report",
        lambda **_: ForcedBlock(),
    )
    result = _run(_request())
    assert result.final_band == "WAIT"
    assert "FINAL_CONFLUENCE_ARBITER" not in result.engines_run
    assert "D6_ARBITER:stage2_integrity_block" in result.engines_skipped
    assert result.arbiter_summary["arbiter_run"] is False
    assert result.arbiter_summary["blocked_before_d6"] is True
    assert any("FORCED_STAGE2_BLOCK" in blocker for blocker in result.blockers)
    assert result.risk_summary["stage2_integrity"]["canonical_context_eligible"] is False
