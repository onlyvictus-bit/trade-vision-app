from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.behavior.orb_guidance import run_paper_guidance_with_orb
from app.behavior.paper_guidance_config import PaperGuidanceConfig
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import (
    CandleBar,
    CandleSeries,
    IndicatorSignalHistoryRecord,
    IndicatorSignalOutcomeLabel,
    KillSwitchState,
    OrbComboMetrics,
    OrbPlaybook,
    OrbStrategyConfig,
    PaperGuidanceRequest,
    SystemMode,
    SystemModeValue,
)


OPEN_NS = int(
    datetime(2025, 1, 2, 3, 45, tzinfo=timezone.utc).timestamp()
    * 1_000_000_000
)
STEP_NS = timeframe_duration_ns("5m")


def _series(*, breakout: bool = True) -> CandleSeries:
    bars = []
    for index in range(40):
        if index < 3:
            open_price = 100.0 + index * 0.05
            close = open_price + 0.02
            high = 100.30
            low = 99.70
        elif breakout:
            open_price = 100.25 + index * 0.12
            close = open_price + 0.09
            high = close + 0.08
            low = open_price - 0.04
        else:
            open_price = 100.0 + (index % 2) * 0.03
            close = 100.01 - (index % 2) * 0.02
            high = 100.22
            low = 99.78
        bars.append(
            CandleBar(
                symbol="RELIANCE",
                timeframe="5m",
                timestamp_ns=OPEN_NS + index * STEP_NS,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=150_000.0 + index * 2_000.0,
                source="user_csv",
                sequence_number=index + 1,
            )
        )
    return CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=bars,
        snapshot_id="orb-guidance-fixture",
        schema_version="candles.v1",
    )


def _request(*, breakout: bool = True, required: list[str] | None = None):
    series = _series(breakout=breakout)
    return PaperGuidanceRequest(
        symbol=series.symbol,
        timeframe=series.timeframe,
        series=series,
        decision_time_ns=series.bars[-1].timestamp_ns + STEP_NS,
        indicator_ids=["si_vwap_conf"],
        required_higher_timeframes=required or [],
    )


def _mode():
    return SystemMode(
        mode=SystemModeValue.MOCK,
        display_label="Mock research",
        immutable=True,
        allows_live_orders=False,
        allows_broker_credentials=False,
        watermark_text="MOCK - NO REAL MONEY",
    )


def _kill_switch():
    return KillSwitchState(
        state="armed",
        reason=None,
        source=None,
        actor_id=None,
        triggered_at=None,
        blocks_order_paths=False,
    )


def _metrics():
    return OrbComboMetrics(
        combo_id="combo-proof-backed",
        strategy_family="orb_breakout",
        range_mode="bar_count",
        orb_bar_count=3,
        reward_risk_ratio=2.0,
        require_volume_confirmation=False,
        trade_count=120,
        win_count=72,
        loss_count=48,
        win_rate=0.60,
        gross_r=96.0,
        net_r=84.0,
        profit_factor=1.75,
        max_drawdown_r=6.0,
        profitable_period_rate=0.72,
        composite_score=1.2,
        minimum_trades_pass=True,
        no_future_leakage=True,
    )


def _playbook():
    return OrbPlaybook(
        playbook_version="orb-playbook.v1.91",
        playbook_id="playbook-reliance-5m",
        symbol="RELIANCE",
        timeframe="5m",
        combo_id="combo-proof-backed",
        config=OrbStrategyConfig(
            strategy_family="orb_breakout",
            range_mode="bar_count",
            orb_bar_count=3,
            direction="long",
            reward_risk_ratio=2.0,
        ),
        proof_id="proof-reliance",
        proof_hash="a" * 64,
        metrics=_metrics(),
        promoted_by="qa",
        promoted_at="2025-01-01T00:00:00+00:00",
    )


def _history():
    label = IndicatorSignalOutcomeLabel(
        label_version="test",
        label_id="label-orb-guidance",
        indicator_id="si_vwap_conf",
        symbol="RELIANCE",
        timeframe="5m",
        signal_direction="bullish",
        signal_time_ns=OPEN_NS,
        horizon_candles=9,
        label_status="complete",
        outcome_label="TARGET_HIT",
        target_first=True,
        stop_first=False,
        same_bar_ambiguous=False,
        conservative_stop_first_used=False,
        mfe=1.2,
        mae=0.2,
        counted_as_win=True,
        counted_as_failure=False,
        counted_in_reliability=True,
        reason="fixture",
    )
    return IndicatorSignalHistoryRecord(
        history_version="test",
        history_id="history-orb-guidance",
        symbol="RELIANCE",
        indicator_id="si_vwap_conf",
        timeframe="5m",
        signal_direction="bullish",
        signal_time_ns=OPEN_NS,
        decision_time_ns=OPEN_NS,
        session_phase="establishment",
        regime_id="trend",
        feature_manifest_version="v1",
        indicator_registry_version="v1",
        signal_strength=0.8,
        missing_mask=False,
        label=label,
        counted_in_reliability=True,
        created_at=datetime.fromtimestamp(
            OPEN_NS / 1_000_000_000, tz=timezone.utc
        ).isoformat(),
        no_future_leakage=True,
    )


@pytest.fixture(autouse=True)
def _runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.behavior.orb_guidance.ORB_GUIDANCE_STORE_PATH",
        tmp_path / "guidance.json",
    )
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.compute_real_indicator_outputs_with_telemetry",
        lambda candles, indicator_ids: (
            {item: {"last": len(candles)} for item in indicator_ids},
            [
                {
                    "indicator_id": item,
                    "status": "computed",
                    "latency_ms": 0.1,
                    "source_latency_ms": 0.1,
                    "output_present": True,
                    "used_for_9c_vector": True,
                    "cache_hit": False,
                    "cache_version": "test",
                    "error": None,
                }
                for item in indicator_ids
            ],
        ),
    )
    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.list_indicator_signal_history_records",
        lambda **_: [_history()],
    )


def _run(request, monkeypatch, playbooks=None, *, minimum=1):
    monkeypatch.setattr(
        "app.behavior.orb_guidance.list_orb_playbooks",
        lambda **_: [] if playbooks is None else playbooks,
    )
    return run_paper_guidance_with_orb(
        request,
        mode=_mode(),
        kill_switch=_kill_switch(),
        config=PaperGuidanceConfig(minimum_evidence_count=minimum),
    )


def test_tv_v192_001_no_playbook_fails_closed(monkeypatch):
    result = _run(_request(), monkeypatch)
    assert result.orb_ticket
    assert result.orb_ticket.candidate_state == "NO_PLAYBOOK"
    assert result.final_band in {"WAIT", "WATCH", "AVOID"}
    assert result.next_action == "DO_NOTHING"


def test_tv_v192_002_active_playbook_builds_same_snapshot_candidate(monkeypatch):
    result = _run(_request(), monkeypatch, [_playbook()])
    assert result.orb_ticket
    assert result.orb_ticket.playbook_id == "playbook-reliance-5m"
    assert result.orb_ticket.source_snapshot_hash == result.snapshot_hash
    receipt = next(
        row for row in result.engine_receipts if row.engine_id == "ORB_PLAYBOOK_GUIDANCE"
    )
    assert receipt.source_snapshot_hash == result.snapshot_hash
    assert receipt.identity_match is True


def test_tv_v192_003_orb_supplies_entry_stop_target_only_after_setup(monkeypatch):
    result = _run(_request(), monkeypatch, [_playbook()])
    assert result.entry_plan
    assert result.entry_plan.entry > result.entry_plan.stop
    assert result.entry_plan.target > result.entry_plan.entry
    assert result.entry_plan.r_ratio == 2.0


def test_tv_v192_004_no_setup_has_no_entry_authority(monkeypatch):
    result = _run(_request(breakout=False), monkeypatch, [_playbook()])
    assert result.entry_plan is None
    assert result.orb_ticket
    assert result.orb_ticket.candidate_state == "NO_SETUP"
    assert result.orb_ticket.can_record_paper is False


def test_tv_v192_005_low_evidence_blocks_enter_paper(monkeypatch):
    result = _run(_request(), monkeypatch, [_playbook()], minimum=30)
    assert result.low_evidence_flag is True
    assert result.final_band != "ENTER_PAPER"
    assert result.next_action == "DO_NOTHING"


def test_tv_v192_006_missing_required_mtf_blocks_enter_paper(monkeypatch):
    result = _run(
        _request(required=["15m"]),
        monkeypatch,
        [_playbook()],
        minimum=1,
    )
    assert result.mtf_evidence
    assert result.mtf_evidence.missing_required_timeframes == ["15m"]
    assert result.orb_ticket
    assert result.orb_ticket.mtf_complete is False
    assert result.final_band != "ENTER_PAPER"


def test_tv_v192_007_playbook_proof_metrics_are_visible(monkeypatch):
    from app.behavior.final_confluence_arbiter import (
        build_final_confluence_arbiter_report as real_arbiter,
    )

    monkeypatch.setattr(
        "app.behavior.orb_guidance.build_final_confluence_arbiter_report",
        lambda request: real_arbiter(
            request.model_copy(
                update={
                    "market_regime_score": 1.0,
                    "structure_score": 1.0,
                    "volume_auction_score": 1.0,
                }
            )
        ),
    )
    result = _run(_request(), monkeypatch, [_playbook()])
    assert result.orb_ticket
    assert result.orb_ticket.proof_metrics
    assert result.orb_ticket.proof_metrics.trade_count == 120
    assert result.orb_ticket.proof_metrics.profit_factor == 1.75
    assert result.final_band == "ENTER_PAPER"
    assert result.next_action == "OFFER_PAPER_TICKET"
    assert result.orb_ticket.can_record_paper is True


def test_tv_v192_008_guidance_is_deterministic(monkeypatch):
    first = _run(_request(), monkeypatch, [_playbook()])
    second = _run(_request(), monkeypatch, [_playbook()])
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.orb_ticket.deterministic_hash == second.orb_ticket.deterministic_hash  # type: ignore[union-attr]


def test_tv_v192_009_orb_cannot_route_or_execute(monkeypatch):
    result = _run(_request(), monkeypatch, [_playbook()])
    assert result.trade_allowed is False
    assert result.paper_execution_attempted is False
    assert result.broker_order_created is False
    assert result.order_routing_enabled is False
    assert result.live_trading_blocked is True


def test_tv_v192_010_discovery_and_proof_are_not_in_guidance_path():
    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "behavior"
        / "orb_guidance.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("discovery" in item or "proof" in item for item in imports)


def test_tv_v192_011_existing_p1_remains_orb_import_free():
    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "behavior"
        / "paper_guidance_spine.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("orb" in item.lower() for item in imports)


def test_tv_v192_012_orb_never_removes_existing_safety_gate(monkeypatch):
    result = _run(_request(), monkeypatch, [_playbook()])
    assert result.safety_gate.passed is True
    assert result.point_in_time.passed is True
    assert result.data_quality.blocks_trade is False
    assert result.arbiter_summary["gates"]
