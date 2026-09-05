from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.behavior.atomic_json_store import (
    AtomicJsonCorruptionError,
    load_record_map,
    replace_record_map,
    update_record_map,
)
from app.behavior.orb_guidance import _save_guidance_ticket
from app.behavior.orb_paper_feedback import (
    _hash as feedback_hash,
    build_orb_paper_reliability,
    build_paper_guidance_storage_monitor,
)
from app.behavior.orb_paper_lifecycle import (
    evaluate_simulated_paper_lifecycle,
    list_simulated_paper_outcomes,
)
from app.behavior.paper_guidance_config import (
    PaperGuidanceStorageConfig,
    load_paper_guidance_storage_config,
)
from app.behavior.simulated_paper_ledger import (
    list_simulated_paper_trades,
    record_simulated_paper_trade,
)
from app.main import app
from app.models import (
    CandleBar,
    CandleSeries,
    OrbComboMetrics,
    OrbGuidanceTicket,
    OrbSignalCandidate,
    PaperGuidanceEntryPlan,
    SimulatedPaperLifecycleObservationRequest,
    SimulatedPaperRecordApprovalRequest,
)


client = TestClient(app)
BASE_NS = 1_714_724_800_000_000_000
DURATION_NS = 5 * 60 * 1_000_000_000


@pytest.fixture(autouse=True)
def _stores(tmp_path, monkeypatch):
    guidance = tmp_path / "guidance.json"
    paper = tmp_path / "paper.json"
    outcomes = tmp_path / "outcomes.json"
    monkeypatch.setattr(
        "app.behavior.orb_guidance.ORB_GUIDANCE_STORE_PATH",
        guidance,
    )
    monkeypatch.setattr(
        "app.behavior.simulated_paper_ledger.SIMULATED_PAPER_STORE_PATH",
        paper,
    )
    monkeypatch.setattr(
        "app.behavior.orb_paper_lifecycle.ORB_PAPER_OUTCOME_STORE_PATH",
        outcomes,
    )
    monkeypatch.setattr(
        "app.behavior.orb_paper_feedback.ORB_GUIDANCE_STORE_PATH",
        guidance,
    )
    monkeypatch.setattr(
        "app.behavior.orb_paper_feedback.SIMULATED_PAPER_STORE_PATH",
        paper,
    )
    monkeypatch.setattr(
        "app.behavior.orb_paper_feedback.ORB_PAPER_OUTCOME_STORE_PATH",
        outcomes,
    )


def _storage_config(tmp_path: Path, **updates) -> PaperGuidanceStorageConfig:
    base = PaperGuidanceStorageConfig(
        guidance_store_path=tmp_path / "guidance.json",
        paper_store_path=tmp_path / "paper.json",
        outcome_store_path=tmp_path / "outcomes.json",
    )
    return replace(base, **updates)


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


def _ticket(guidance_id="guidance-v194", playbook_id="playbook-v194"):
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
        signal_timestamp_ns=BASE_NS - DURATION_NS,
        signal_close_time_ns=BASE_NS,
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
        decision_time_ns=BASE_NS,
        source_snapshot_hash="b" * 64,
        playbook_id=playbook_id,
        proof_id="proof-v194",
        proof_hash="a" * 64,
        strategy_family="orb_breakout",
        candidate_state="PAPER_CANDIDATE",
        final_band="ENTER_PAPER",
        signal=signal,
        entry_plan=entry,
        proof_metrics=_metrics(),
        historical_match_count=120,
        minimum_evidence_count=30,
        mtf_complete=True,
        liquidity_grade="A",
        trap_score=0.10,
        can_record_paper=True,
        reasons=["All research gates passed."],
        deterministic_hash="c" * 64,
    )


def _approval(guidance_id="guidance-v194"):
    return SimulatedPaperRecordApprovalRequest(
        guidance_id=guidance_id,
        source_snapshot_hash="b" * 64,
        approved_by="local-operator",
        approval_text="RECORD_SIMULATED_PAPER_TRADE",
        quantity=10,
        note="v1.94 replay test.",
    )


def _bar(
    index: int,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    timestamp_ns: int | None = None,
    sequence_number: int | None = None,
):
    return CandleBar(
        symbol="RELIANCE",
        timeframe="5m",
        timestamp_ns=(
            BASE_NS + index * DURATION_NS
            if timestamp_ns is None
            else timestamp_ns
        ),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
        source="replay",
        sequence_number=(
            index + 1 if sequence_number is None else sequence_number
        ),
    )


def _request(record_id: str, bars: list[CandleBar], max_holding=24):
    return SimulatedPaperLifecycleObservationRequest(
        paper_record_id=record_id,
        source_snapshot_hash="b" * 64,
        series=CandleSeries(
            symbol="RELIANCE",
            timeframe="5m",
            bars=bars,
            snapshot_id="v194-observation",
            schema_version="replay.v194",
        ),
        observation_time_ns=bars[-1].timestamp_ns + DURATION_NS,
        max_holding_bars=max_holding,
        observation_text="EVALUATE_SIMULATED_PAPER_OUTCOME",
    )


def _record():
    _save_guidance_ticket(_ticket())
    return record_simulated_paper_trade(_approval())


def test_tv_v194_001_configured_storage_paths_are_honored(tmp_path, monkeypatch):
    root = tmp_path / "configured"
    monkeypatch.setenv("TRADEVISION_PAPER_GUIDANCE_DATA_ROOT", str(root))
    config = load_paper_guidance_storage_config()
    assert config.guidance_store_path == root / "orb_guidance_tickets.json"
    assert config.paper_store_path == root / "orb_paper_records.json"
    assert config.outcome_store_path == root / "orb_paper_outcomes.json"


def test_tv_v194_002_corrupt_store_fails_closed_and_is_not_overwritten(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(AtomicJsonCorruptionError):
        update_record_map(path, lambda rows: ({**rows, "x": {}}, None))
    assert path.read_text(encoding="utf-8") == "{broken"


def test_tv_v194_003_valid_temporary_store_recovers_when_main_absent(tmp_path):
    path = tmp_path / "recover.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text('{"one": {"value": 1}}', encoding="utf-8")
    assert load_record_map(path) == {"one": {"value": 1}}
    assert path.exists()
    assert not temporary.exists()


def test_tv_v194_004_concurrent_writes_retain_every_record(tmp_path):
    path = tmp_path / "concurrent.json"

    def write(index: int):
        update_record_map(
            path,
            lambda rows: (
                {**rows, str(index): {"index": index}},
                index,
            ),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(30)))
    assert len(load_record_map(path)) == 30


def test_tv_v194_005_stale_guidance_ticket_is_rejected(monkeypatch):
    monkeypatch.setattr("app.behavior.orb_guidance.time.time_ns", lambda: 1)
    _save_guidance_ticket(_ticket())
    monkeypatch.setattr(
        "app.behavior.orb_guidance.time.time_ns",
        lambda: 10**18,
    )
    with pytest.raises(ValueError, match="expired"):
        record_simulated_paper_trade(_approval())


def test_tv_v194_006_historical_decision_time_does_not_make_fresh_ticket_stale(
    monkeypatch,
):
    now_ns = 2_000_000_000_000_000_000
    monkeypatch.setattr(
        "app.behavior.orb_guidance.time.time_ns",
        lambda: now_ns,
    )
    _save_guidance_ticket(_ticket())
    assert record_simulated_paper_trade(_approval()).status == "RECORDED"


def test_tv_v194_007_lifecycle_requires_human_approved_record():
    request = _request(
        "missing",
        [_bar(0, open_=100, high=102, low=100, close=101)],
    )
    with pytest.raises(KeyError):
        evaluate_simulated_paper_lifecycle(request)


def test_tv_v194_008_identity_chain_mismatch_is_rejected():
    record = _record()
    request = _request(
        record.paper_record_id,
        [_bar(0, open_=100, high=102, low=100, close=101)],
    ).model_copy(update={"source_snapshot_hash": "d" * 64})
    with pytest.raises(ValueError, match="identity mismatch"):
        evaluate_simulated_paper_lifecycle(request)


def test_tv_v194_009_duplicate_or_non_monotonic_candles_are_rejected():
    record = _record()
    bars = [
        _bar(0, open_=100, high=102, low=100, close=101),
        _bar(
            1,
            open_=101,
            high=102,
            low=100,
            close=101,
            timestamp_ns=BASE_NS,
        ),
    ]
    with pytest.raises(ValueError, match="chronological"):
        evaluate_simulated_paper_lifecycle(_request(record.paper_record_id, bars))


def test_tv_v194_010_incomplete_future_candle_is_rejected():
    record = _record()
    request = _request(
        record.paper_record_id,
        [_bar(0, open_=100, high=102, low=100, close=101)],
    ).model_copy(update={"observation_time_ns": BASE_NS})
    with pytest.raises(ValueError, match="incomplete or future"):
        evaluate_simulated_paper_lifecycle(request)


def test_tv_v194_011_pre_decision_candle_is_rejected():
    record = _record()
    bar = _bar(
        0,
        open_=100,
        high=102,
        low=100,
        close=101,
        timestamp_ns=BASE_NS - DURATION_NS,
    )
    with pytest.raises(ValueError, match="before the guidance decision"):
        evaluate_simulated_paper_lifecycle(_request(record.paper_record_id, [bar]))


def test_tv_v194_012_no_trigger_completes_as_no_fill():
    record = _record()
    bars = [
        _bar(0, open_=100, high=100.5, low=99.5, close=100),
        _bar(1, open_=100, high=100.8, low=99.8, close=100.2),
    ]
    result = evaluate_simulated_paper_lifecycle(
        _request(record.paper_record_id, bars, max_holding=2)
    )
    assert (result.outcome_label, result.completed) == ("NO_FILL", True)
    assert result.simulated_fill_price is None


def test_tv_v194_013_gap_through_entry_has_adverse_configured_fill(tmp_path):
    record = _record()
    result = evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [_bar(0, open_=102, high=103, low=101.5, close=102.5)],
        ),
        config=_storage_config(
            tmp_path,
            spread_bps=2,
            slippage_bps=2,
            impact_bps=1,
        ),
    )
    assert result.simulated_fill_price > 102
    assert result.costs.total_cost_r > 0


def test_tv_v194_014_target_first_records_target_hit():
    record = _record()
    bars = [
        _bar(0, open_=100, high=102, low=100, close=101.5),
        _bar(1, open_=102, high=105.5, low=101, close=105),
    ]
    result = evaluate_simulated_paper_lifecycle(
        _request(record.paper_record_id, bars)
    )
    assert result.outcome_label == "TARGET_HIT"
    assert result.bars_to_target == 2


def test_tv_v194_015_stop_first_records_stop_hit():
    record = _record()
    bars = [
        _bar(0, open_=100, high=102, low=100, close=101.5),
        _bar(1, open_=101, high=102, low=98.5, close=99),
    ]
    result = evaluate_simulated_paper_lifecycle(
        _request(record.paper_record_id, bars)
    )
    assert result.outcome_label == "STOP_HIT"
    assert result.bars_to_stop == 2


def test_tv_v194_016_same_bar_target_stop_is_conservative_stop_first():
    record = _record()
    result = evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [_bar(0, open_=100, high=106, low=98, close=103)],
        )
    )
    assert result.outcome_label == "STOP_HIT"
    assert result.same_bar_ambiguous is True
    assert result.conservative_stop_first_used is True


def test_tv_v194_017_open_lifecycle_waits_for_more_closed_bars():
    record = _record()
    result = evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [_bar(0, open_=100, high=102, low=100, close=101.5)],
            max_holding=3,
        )
    )
    assert result.lifecycle_status == "OPEN"
    assert result.outcome_label == "PENDING"
    assert result.completed is False


def test_tv_v194_018_completed_window_records_time_exit():
    record = _record()
    bars = [
        _bar(0, open_=100, high=102, low=100, close=101.5),
        _bar(1, open_=101.5, high=103, low=100, close=102),
    ]
    result = evaluate_simulated_paper_lifecycle(
        _request(record.paper_record_id, bars, max_holding=2)
    )
    assert result.outcome_label == "TIME_EXIT"
    assert result.completed is True


def test_tv_v194_019_mfe_mae_and_cost_adjusted_r_are_deterministic():
    record = _record()
    request = _request(
        record.paper_record_id,
        [
            _bar(0, open_=100, high=102, low=100, close=101.5),
            _bar(1, open_=101.5, high=105.5, low=100, close=105),
        ],
    )
    first = evaluate_simulated_paper_lifecycle(request)
    second = evaluate_simulated_paper_lifecycle(request)
    assert first == second
    assert first.mfe > 0
    assert first.mae > 0
    assert first.net_r < first.gross_r


def test_tv_v194_020_duplicate_observation_is_idempotent():
    record = _record()
    request = _request(
        record.paper_record_id,
        [
            _bar(0, open_=100, high=102, low=100, close=101.5),
            _bar(1, open_=101.5, high=105.5, low=100, close=105),
        ],
    )
    assert evaluate_simulated_paper_lifecycle(request) == (
        evaluate_simulated_paper_lifecycle(request)
    )
    assert len(list_simulated_paper_outcomes()) == 1


def test_tv_v194_021_only_completed_outcomes_enter_reliability():
    record = _record()
    evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [_bar(0, open_=100, high=102, low=100, close=101.5)],
            max_holding=3,
        )
    )
    report = build_orb_paper_reliability("playbook-v194")
    assert report.completed_sample_count == 0


def test_tv_v194_022_orphan_outcome_is_excluded_and_reported(tmp_path):
    record = _record()
    outcome = evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [
                _bar(0, open_=100, high=102, low=100, close=101.5),
                _bar(1, open_=101, high=106, low=100, close=105),
            ],
        )
    )
    assert outcome.completed is True
    paper_path = Path(
        build_paper_guidance_storage_monitor().stores[1]["path"]
    )
    replace_record_map(paper_path, {})
    report = build_paper_guidance_storage_monitor()
    assert report.orphan_outcome_count == 1


def test_tv_v194_023_low_sample_feedback_remains_low_evidence():
    record = _record()
    evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [
                _bar(0, open_=100, high=102, low=100, close=101.5),
                _bar(1, open_=101, high=106, low=100, close=105),
            ],
        )
    )
    report = build_orb_paper_reliability("playbook-v194")
    assert report.reliability_state == "LOW_EVIDENCE"
    assert report.can_boost_guidance is False


def test_tv_v194_024_poor_evidence_can_only_recommend_quarantine(tmp_path):
    record = _record()
    outcome = evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [
                _bar(0, open_=100, high=102, low=100, close=101.5),
                _bar(1, open_=101, high=102, low=98, close=99),
            ],
        )
    )
    paper_rows = {}
    outcome_rows = {}
    for index in range(30):
        paper_id = f"paper-{index}"
        paper = record.model_copy(
            update={
                "paper_record_id": paper_id,
                "guidance_id": f"guidance-{index}",
            }
        ).model_dump(mode="json")
        cloned = outcome.model_copy(
            update={
                "outcome_id": f"outcome-{index}",
                "paper_record_id": paper_id,
                "guidance_id": f"guidance-{index}",
            }
        )
        payload = cloned.model_dump(mode="json")
        payload.pop("integrity_hash")
        payload["integrity_hash"] = feedback_hash(payload)
        paper_rows[paper_id] = paper
        outcome_rows[f"outcome-{index}"] = payload
    replace_record_map(
        Path(
            build_paper_guidance_storage_monitor().stores[1]["path"]
        ),
        paper_rows,
    )
    replace_record_map(
        Path(
            build_paper_guidance_storage_monitor().stores[2]["path"]
        ),
        outcome_rows,
    )
    report = build_orb_paper_reliability(
        "playbook-v194",
        config=_storage_config(
            tmp_path,
            feedback_minimum_samples=30,
        ),
    )
    assert report.reliability_state == "QUARANTINE_RECOMMENDED"
    assert report.can_retire_playbook is False


def test_tv_v194_025_feedback_has_no_promotion_or_band_authority():
    report = build_orb_paper_reliability("playbook-v194")
    assert report.can_boost_guidance is False
    assert report.can_promote_playbook is False
    assert report.can_retire_playbook is False
    assert report.model_weights_updated is False


def test_tv_v194_026_monitor_reports_integrity_counts_and_stale_tickets():
    _record()
    report = build_paper_guidance_storage_monitor(now_ns=10**21)
    assert report.integrity_passed is True
    assert report.guidance_ticket_count == 1
    assert report.paper_record_count == 1
    assert report.stale_ticket_count == 1


def test_tv_v194_027_retention_is_preview_only_and_deletes_nothing():
    _record()
    before = len(list_simulated_paper_trades())
    report = build_paper_guidance_storage_monitor()
    after = len(list_simulated_paper_trades())
    assert report.retention_action == "PREVIEW_ONLY"
    assert report.automatic_deletion_enabled is False
    assert before == after


def test_tv_v194_028_safety_literals_block_every_execution_path():
    record = _record()
    outcome = evaluate_simulated_paper_lifecycle(
        _request(
            record.paper_record_id,
            [
                _bar(0, open_=100, high=102, low=100, close=101.5),
                _bar(1, open_=101, high=106, low=100, close=105),
            ],
        )
    )
    assert outcome.simulation_only is True
    assert outcome.automatic_fill_attempted is False
    assert outcome.external_execution_attempted is False
    assert outcome.broker_order_created is False
    assert outcome.order_routing_enabled is False
    assert outcome.live_trading_blocked is True


def test_tv_v194_029_openapi_and_capability_manifest_expose_v194():
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "SimulatedPaperLifecycleOutcome" in schemas
    assert "OrbPaperReliabilityReport" in schemas
    capabilities = client.get("/api/system/features").json()["data"]["capabilities"]
    assert "ORB Paper Lifecycle Feedback" in {
        item["name"] for item in capabilities
    }


def test_tv_v194_030_source_has_no_broker_openalgo_or_auto_fill_path():
    source = (
        Path(__file__).parents[1]
        / "app"
        / "behavior"
        / "orb_paper_lifecycle.py"
    ).read_text(encoding="utf-8").lower()
    assert "openalgo" not in source
    assert "broker_order_created\": false" in source
    assert "automatic_fill_attempted\": false" in source


def test_tv_v194_031_api_returns_lifecycle_and_reliability():
    record = _record()
    request = _request(
        record.paper_record_id,
        [
            _bar(0, open_=100, high=102, low=100, close=101.5),
            _bar(1, open_=101, high=106, low=100, close=105),
        ],
    )
    response = client.post(
        "/api/v1/paper-guidance/paper-records/observe",
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 200
    reliability = client.get(
        "/api/v1/paper-guidance/orb-reliability/playbook-v194"
    )
    assert reliability.status_code == 200
    assert reliability.json()["data"]["reliability_state"] == "LOW_EVIDENCE"


def test_tv_v194_032_monitor_fails_closed_on_corruption(tmp_path):
    _record()
    outcome_path = Path(
        build_paper_guidance_storage_monitor().stores[2]["path"]
    )
    outcome_path.write_text("{broken", encoding="utf-8")
    report = build_paper_guidance_storage_monitor()
    assert report.integrity_passed is False
    assert report.trade_allowed is False
    assert report.order_routing_enabled is False
    assert report.live_trading_blocked is True
