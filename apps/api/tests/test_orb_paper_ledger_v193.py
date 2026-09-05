from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.behavior.orb_guidance import _save_guidance_ticket
from app.behavior.simulated_paper_ledger import (
    list_simulated_paper_trades,
    record_simulated_paper_trade,
)
from app.main import app
from app.models import (
    OrbComboMetrics,
    OrbGuidanceTicket,
    OrbSignalCandidate,
    PaperGuidanceEntryPlan,
    SimulatedPaperRecordApprovalRequest,
)


client = TestClient(app)


def _metrics():
    return OrbComboMetrics(
        combo_id="combo",
        strategy_family="orb_breakout",
        range_mode="bar_count",
        orb_bar_count=3,
        reward_risk_ratio=2.0,
        require_volume_confirmation=False,
        trade_count=120,
        win_count=70,
        loss_count=50,
        win_rate=0.583333,
        gross_r=90.0,
        net_r=80.0,
        profit_factor=1.6,
        max_drawdown_r=7.0,
        profitable_period_rate=0.70,
        composite_score=1.0,
        minimum_trades_pass=True,
        no_future_leakage=True,
    )


def _ticket(*, can_record=True, guidance_id="guidance-eligible"):
    entry = PaperGuidanceEntryPlan(
        side="LONG",
        entry=101.0,
        stop=99.0,
        target=105.0,
        invalidation="Close below ORL.",
        size_hint=0.0,
        r_ratio=2.0,
    )
    signal = OrbSignalCandidate(
        signal_type="BREAKOUT_LONG",
        side="LONG",
        signal_timestamp_ns=1_000,
        signal_close_time_ns=2_000,
        trigger_price=101.0,
        entry_price=101.0,
        stop_price=99.0,
        target_price=105.0,
        invalidation="Close below ORL.",
        reward_risk_ratio=2.0,
        volume_confirmed=True,
        vwap_confirmed=True,
        close_confirmed=True,
        reason="Proof-backed ORB breakout.",
    )
    return OrbGuidanceTicket(
        ticket_version="orb-jarvis-guidance.v1.92",
        guidance_id=guidance_id,
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=2_000,
        source_snapshot_hash="b" * 64,
        playbook_id="playbook",
        proof_id="proof",
        proof_hash="a" * 64,
        strategy_family="orb_breakout",
        candidate_state="PAPER_CANDIDATE" if can_record else "WATCH",
        final_band="ENTER_PAPER" if can_record else "WATCH",
        signal=signal,
        entry_plan=entry,
        proof_metrics=_metrics(),
        historical_match_count=120,
        minimum_evidence_count=30,
        mtf_complete=True,
        liquidity_grade="A",
        trap_score=0.10,
        can_record_paper=can_record,
        blockers=[] if can_record else ["Low evidence."],
        reasons=["All research gates passed."],
        deterministic_hash="c" * 64,
    )


def _approval(guidance_id="guidance-eligible", snapshot_hash="b" * 64):
    return SimulatedPaperRecordApprovalRequest(
        guidance_id=guidance_id,
        source_snapshot_hash=snapshot_hash,
        approved_by="local-operator",
        approval_text="RECORD_SIMULATED_PAPER_TRADE",
        quantity=10,
        note="Manual replay test.",
    )


@pytest.fixture(autouse=True)
def _stores(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.behavior.orb_guidance.ORB_GUIDANCE_STORE_PATH",
        tmp_path / "guidance.json",
    )
    monkeypatch.setattr(
        "app.behavior.simulated_paper_ledger.SIMULATED_PAPER_STORE_PATH",
        tmp_path / "paper.json",
    )


def test_tv_v193_001_explicit_eligible_ticket_records():
    _save_guidance_ticket(_ticket())
    record = record_simulated_paper_trade(_approval())
    assert record.status == "RECORDED"
    assert record.human_approved is True
    assert record.simulation_only is True


def test_tv_v193_002_server_ticket_is_required():
    with pytest.raises(KeyError):
        record_simulated_paper_trade(_approval())


def test_tv_v193_003_snapshot_tampering_is_rejected():
    _save_guidance_ticket(_ticket())
    with pytest.raises(ValueError):
        record_simulated_paper_trade(_approval(snapshot_hash="d" * 64))


def test_tv_v193_004_watch_ticket_cannot_record():
    _save_guidance_ticket(_ticket(can_record=False))
    with pytest.raises(ValueError):
        record_simulated_paper_trade(_approval())


def test_tv_v193_005_duplicate_approval_is_idempotent():
    _save_guidance_ticket(_ticket())
    first = record_simulated_paper_trade(_approval())
    second = record_simulated_paper_trade(_approval())
    assert first == second
    assert len(list_simulated_paper_trades()) == 1


def test_tv_v193_006_atomic_json_contains_no_execution_authority(tmp_path):
    _save_guidance_ticket(_ticket())
    record = record_simulated_paper_trade(_approval())
    rows = list_simulated_paper_trades()
    assert rows == [record]
    assert record.trade_allowed is False
    assert record.execution_attempted is False
    assert record.broker_order_created is False
    assert record.order_routing_enabled is False
    assert record.live_trading_blocked is True


def test_tv_v193_007_record_copies_server_entry_plan_not_client_prices():
    _save_guidance_ticket(_ticket())
    record = record_simulated_paper_trade(_approval())
    assert (record.entry, record.stop, record.target) == (101.0, 99.0, 105.0)
    assert record.risk_reward_ratio == 2.0


def test_tv_v193_008_list_filters_symbol_and_timeframe():
    _save_guidance_ticket(_ticket())
    record_simulated_paper_trade(_approval())
    assert len(list_simulated_paper_trades(symbol="RELIANCE", timeframe="5m")) == 1
    assert list_simulated_paper_trades(symbol="INFY") == []


def test_tv_v193_009_api_rejects_unrecordable_ticket():
    _save_guidance_ticket(_ticket(can_record=False))
    response = client.post(
        "/api/v1/paper-guidance/record-simulated",
        json=_approval().model_dump(mode="json"),
    )
    assert response.status_code == 409


def test_tv_v193_010_openapi_and_capability_are_exposed():
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "OrbGuidanceTicket" in schemas
    assert "SimulatedPaperTradeRecord" in schemas
    capabilities = client.get("/api/system/features").json()["data"]["capabilities"]
    names = {item["name"] for item in capabilities}
    assert "ORB Jarvis Guidance" in names
    assert "ORB Simulated Paper Ledger" in names
