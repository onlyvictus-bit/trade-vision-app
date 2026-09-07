from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    CandleBar,
    CandleSeries,
    OrbDiscoveryRequest,
    OrbPlaybookPromotionRequest,
    OrbProofRequest,
    OrbProofThresholds,
)
from app.orb.proof import (
    list_orb_playbooks,
    load_orb_proof,
    promote_orb_playbook,
    run_orb_proof,
)


client = TestClient(app)
STEP_NS = 300_000_000_000
OPEN_NS = int(
    datetime(2025, 1, 1, 3, 45, tzinfo=timezone.utc).timestamp()
    * 1_000_000_000
)


def _day(day: int, outcome: str):
    start = OPEN_NS + day * 86_400_000_000_000
    rows = [
        (100.0, 100.6, 99.5, 100.2),
        (100.2, 101.0, 99.8, 100.7),
        (100.7, 100.9, 99.0, 100.1),
        (100.8, 101.7, 100.7, 101.4),
        (
            101.3,
            104.0 if outcome == "win" else 101.5,
            101.1 if outcome == "win" else 98.7,
            103.7 if outcome == "win" else 99.0,
        ),
        (103.7 if outcome == "win" else 99.0, 104.0, 98.9, 103.7 if outcome == "win" else 99.0),
    ]
    return [
        CandleBar(
            symbol="RELIANCE",
            timeframe="5m",
            timestamp_ns=start + index * STEP_NS,
            open=row[0],
            high=row[1],
            low=row[2],
            close=row[3],
            volume=1800.0 if index >= 3 else 1000.0,
            source="user_csv",
            sequence_number=day * 100 + index + 1,
        )
        for index, row in enumerate(rows)
    ]


def _series(outcomes: list[str]):
    return CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=[bar for day, outcome in enumerate(outcomes) for bar in _day(day, outcome)],
        snapshot_id="orb-proof-fixture",
        schema_version="candles.v1",
    )


def _proof_request(outcomes: list[str], *, rr: list[float] | None = None):
    discovery = OrbDiscoveryRequest(
        series=_series(outcomes),
        strategy_families=["orb_breakout"],
        orb_bar_counts=[3],
        reward_risk_grid=rr or [1.0],
        volume_confirmation_grid=[False],
        minimum_trades=1,
    )
    return OrbProofRequest(
        discovery_request=discovery,
        top_k=5,
        holdout_fraction=0.25,
        walk_forward_folds=4,
        thresholds=OrbProofThresholds(
            minimum_overall_trades=20,
            minimum_oos_trades=3,
            minimum_oos_profit_factor=1.0,
            minimum_oos_net_r=0.0,
            minimum_walk_forward_pass_rate=0.50,
        ),
    )


@pytest.fixture
def _stores(tmp_path, monkeypatch):
    proof_path = tmp_path / "orb_proofs.json"
    playbook_path = tmp_path / "orb_playbooks.json"
    monkeypatch.setattr("app.orb.proof.ORB_PROOF_STORE_PATH", proof_path)
    monkeypatch.setattr("app.orb.proof.ORB_PLAYBOOK_STORE_PATH", playbook_path)
    return proof_path, playbook_path


def test_tv_v191_001_proof_uses_chronological_train_holdout_split(_stores):
    report = run_orb_proof(_proof_request(["win"] * 32))
    assert len(report.train_dates) == 24
    assert len(report.holdout_dates) == 8
    assert max(report.train_dates) < min(report.holdout_dates)


def test_tv_v191_002_clean_repeated_winner_becomes_eligible(_stores):
    report = run_orb_proof(_proof_request(["win"] * 32))
    proof = report.combo_proofs[0]
    assert proof.oos_passed is True
    assert proof.repeated_success_passed is True
    assert proof.promotion_eligible is True
    assert report.eligible_combo_ids == [proof.combo_id]


def test_tv_v191_003_losing_holdout_blocks_promotion(_stores):
    report = run_orb_proof(
        _proof_request(["win"] * 24 + ["loss"] * 8)
    )
    proof = report.combo_proofs[0]
    assert proof.oos_passed is False
    assert proof.promotion_eligible is False
    assert report.eligible_combo_ids == []


def test_tv_v191_004_walk_forward_reports_real_fold_metrics(_stores):
    report = run_orb_proof(_proof_request(["win"] * 32))
    folds = report.combo_proofs[0].walk_forward_folds
    assert len(folds) == 4
    # Walk-forward discipline (repaired): folds validate equal chunks of the
    # 24 TRAIN days only (holdout days never appear in folds), so each fold
    # carries 6 trades, not the old 8 (which mixed holdout days into folds).
    assert all(fold.metrics and fold.metrics.trade_count == 6 for fold in folds)
    # No fold may touch holdout dates (train/holdout separation).
    assert all(fold.end_date in report.train_dates for fold in folds)
    # Fold 1 has no prior train history: metrics present, selection honestly
    # impossible -> passed=False with an explicit cold-start reason.
    assert folds[0].passed is False
    assert any("Insufficient train history" in reason for reason in folds[0].reasons)
    assert all(fold.passed is True for fold in folds[1:])
    assert report.combo_proofs[0].walk_forward_pass_rate == 0.75
    assert report.selection_scope == "train_only"
    assert report.fold_scheme == "expanding_train"
    assert report.thresholds_used["minimum_oos_profit_factor"] == 1.0


def test_tv_v191_005_proof_and_hash_are_deterministic(_stores):
    request = _proof_request(["win"] * 32)
    first = run_orb_proof(request)
    second = run_orb_proof(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.proof_hash == second.proof_hash


def test_tv_v191_006_proof_is_persisted_as_atomic_json(_stores):
    proof_path, _ = _stores
    report = run_orb_proof(_proof_request(["win"] * 32))
    payload = json.loads(proof_path.read_text(encoding="utf-8"))
    assert report.proof_id in payload
    assert load_orb_proof(report.proof_id) == report
    assert not proof_path.with_suffix(".json.tmp").exists()


def test_tv_v191_007_failed_combo_cannot_be_promoted(_stores):
    report = run_orb_proof(
        _proof_request(["win"] * 24 + ["loss"] * 8)
    )
    with pytest.raises(ValueError):
        promote_orb_playbook(
            OrbPlaybookPromotionRequest(
                proof_id=report.proof_id,
                combo_id=report.combo_proofs[0].combo_id,
                promoted_by="qa",
            )
        )


def test_tv_v191_008_only_server_stored_proof_can_promote(_stores):
    with pytest.raises(KeyError):
        promote_orb_playbook(
            OrbPlaybookPromotionRequest(
                proof_id="client-invented",
                combo_id="invented",
                promoted_by="qa",
            )
        )


def test_tv_v191_009_eligible_combo_promotes_to_active_playbook(_stores):
    report = run_orb_proof(_proof_request(["win"] * 32))
    playbook = promote_orb_playbook(
        OrbPlaybookPromotionRequest(
            proof_id=report.proof_id,
            combo_id=report.eligible_combo_ids[0],
            promoted_by="qa",
        )
    )
    assert playbook.status == "active"
    assert playbook.proof_hash == report.proof_hash
    assert playbook.storage_backend == "atomic_json"
    assert list_orb_playbooks(symbol="RELIANCE", timeframe="5m") == [playbook]


def test_tv_v191_010_playbook_store_contains_no_order_authority(_stores):
    _, playbook_path = _stores
    report = run_orb_proof(_proof_request(["win"] * 32))
    playbook = promote_orb_playbook(
        OrbPlaybookPromotionRequest(
            proof_id=report.proof_id,
            combo_id=report.eligible_combo_ids[0],
            promoted_by="qa",
        )
    )
    payload = json.loads(playbook_path.read_text(encoding="utf-8"))[playbook.playbook_id]
    assert payload["trade_allowed"] is False
    assert payload["order_routing_enabled"] is False
    assert payload["live_trading_blocked"] is True


def test_tv_v191_011_prove_and_promote_api_round_trip(_stores):
    prove_response = client.post(
        "/api/v1/orb/prove",
        json=_proof_request(["win"] * 32).model_dump(mode="json"),
    )
    assert prove_response.status_code == 200
    proof = prove_response.json()["data"]
    promote_response = client.post(
        "/api/v1/orb/playbooks/promote",
        json={
            "proof_id": proof["proof_id"],
            "combo_id": proof["eligible_combo_ids"][0],
            "promoted_by": "qa",
        },
    )
    assert promote_response.status_code == 200
    assert promote_response.json()["data"]["status"] == "active"
    listed = client.get(
        "/api/v1/orb/playbooks?symbol=RELIANCE&timeframe=5m"
    )
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1


def test_tv_v191_012_proof_and_playbook_are_research_only(_stores):
    report = run_orb_proof(_proof_request(["win"] * 32))
    playbook = promote_orb_playbook(
        OrbPlaybookPromotionRequest(
            proof_id=report.proof_id,
            combo_id=report.eligible_combo_ids[0],
            promoted_by="qa",
        )
    )
    assert report.trade_allowed is False
    assert report.order_routing_enabled is False
    assert report.live_trading_blocked is True
    assert playbook.trade_allowed is False
    assert playbook.order_routing_enabled is False
    assert playbook.live_trading_blocked is True

def test_tv_v191_013_train_only_selection_blocks_holdout_only_winner(_stores):
    """Selection-before-split is forbidden: a holdout-passing combo that was
    never selected on train data must not be eligible, regardless of its
    holdout metrics. Re-proves the winning combo with train_selected=False.
    """
    from app.orb.proof import _prove_combo, _run_subset

    request = _proof_request(["win"] * 32)
    report = run_orb_proof(request)
    proof = report.combo_proofs[0]
    assert proof.promotion_eligible is True
    holdout_result = _run_subset(request.discovery_request, report.holdout_dates)
    replayed = _prove_combo(
        proof.overall_metrics,
        holdout_result,
        [("WF-99", [], report.holdout_dates, set(), holdout_result)],
        request,
        train_selected=False,
    )
    assert replayed.promotion_eligible is False
    assert any("train-only" in reason for reason in replayed.reasons)


def test_tv_v191_014_all_proof_trades_stay_within_one_session(_stores):
    """Fold-boundary purge is structural: every backtest trade opens and
    exits inside a single session, so no outcome can leak across folds."""
    from app.orb.discovery import run_orb_discovery

    request = _proof_request(["win"] * 8).discovery_request
    result = run_orb_discovery(request)
    assert result.trades, "fixture must produce trades"
    for trade in result.trades:
        entry_day = datetime.fromtimestamp(
            trade.entry_timestamp_ns / 1_000_000_000, tz=timezone.utc
        ).date()
        exit_day = datetime.fromtimestamp(
            trade.exit_timestamp_ns / 1_000_000_000, tz=timezone.utc
        ).date()
        assert trade.local_session_date == str(entry_day) == str(exit_day)
