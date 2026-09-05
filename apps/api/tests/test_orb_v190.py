from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import CandleBar, CandleSeries, OrbCostModel, OrbDiscoveryRequest
from app.orb import (
    clear_orb_discovery_jobs,
    run_orb_discovery,
)


client = TestClient(app)
STEP_NS = 300_000_000_000
OPEN_NS = int(
    datetime(2026, 1, 5, 3, 45, tzinfo=timezone.utc).timestamp()
    * 1_000_000_000
)


def _day(day: int, *, outcome: str = "win", ambiguous: bool = False):
    start = OPEN_NS + day * 86_400_000_000_000
    rows = [
        (100.0, 100.6, 99.5, 100.2, 1000.0),
        (100.2, 101.0, 99.8, 100.7, 1100.0),
        (100.7, 100.9, 99.0, 100.1, 1000.0),
        (100.8, 101.7, 100.7, 101.4, 1800.0),
    ]
    if ambiguous:
        rows.extend([(101.3, 104.0, 98.5, 102.0, 1900.0)])
    elif outcome == "win":
        rows.extend([(101.3, 104.2, 101.1, 103.8, 1900.0)])
    elif outcome == "loss":
        rows.extend([(101.3, 101.5, 98.7, 99.0, 1900.0)])
    else:
        rows.extend([(101.3, 101.8, 100.8, 101.5, 1500.0)])
    rows.append((rows[-1][3], rows[-1][3] + 0.2, rows[-1][3] - 0.2, rows[-1][3], 1200.0))
    return [
        CandleBar(
            symbol="RELIANCE",
            timeframe="5m",
            timestamp_ns=start + index * STEP_NS,
            open=row[0],
            high=row[1],
            low=row[2],
            close=row[3],
            volume=row[4],
            source="user_csv",
            sequence_number=day * 100 + index + 1,
        )
        for index, row in enumerate(rows)
    ]


def _series(days: int = 8, *, outcomes: list[str] | None = None, ambiguous_day: int | None = None):
    outcomes = outcomes or ["win" if index % 3 else "loss" for index in range(days)]
    bars = []
    for index in range(days):
        bars.extend(
            _day(
                index,
                outcome=outcomes[index],
                ambiguous=index == ambiguous_day,
            )
        )
    return CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=bars,
        snapshot_id="orb-discovery-fixture",
        schema_version="candles.v1",
    )


def _request(**updates):
    payload = dict(
        series=_series(),
        strategy_families=["orb_breakout"],
        orb_bar_counts=[3],
        reward_risk_grid=[1.0],
        volume_confirmation_grid=[False],
        minimum_trades=5,
        maximum_combinations=20,
    )
    payload.update(updates)
    return OrbDiscoveryRequest(**payload)


def test_tv_v190_001_discovery_uses_real_counts_not_constants():
    result = run_orb_discovery(_request())
    assert result.combination_count == 1
    assert result.ranked_combinations[0].trade_count == 8
    assert len(result.trades) == 8


def test_tv_v190_002_entry_is_next_bar_open_after_confirmed_signal():
    result = run_orb_discovery(_request(series=_series(days=1), minimum_trades=1))
    trade = result.trades[0]
    assert trade.entry_timestamp_ns == trade.signal_timestamp_ns + STEP_NS
    assert trade.entry_price != 101.0


def test_tv_v190_003_costs_reduce_gross_result():
    no_cost = run_orb_discovery(
        _request(
            costs=OrbCostModel(
                commission_bps_per_side=0.0,
                slippage_bps_per_side=0.0,
            )
        )
    )
    with_cost = run_orb_discovery(
        _request(
            costs=OrbCostModel(
                commission_bps_per_side=10.0,
                slippage_bps_per_side=10.0,
            )
        )
    )
    assert with_cost.ranked_combinations[0].net_r < no_cost.ranked_combinations[0].net_r
    assert all(trade.cost_r >= 0 for trade in with_cost.trades)


def test_tv_v190_004_same_bar_target_stop_is_conservative_stop_first():
    result = run_orb_discovery(
        _request(
            series=_series(days=1, ambiguous_day=0),
            minimum_trades=1,
        )
    )
    trade = result.trades[0]
    assert trade.outcome == "STOP_HIT"
    assert trade.same_bar_ambiguous is True
    assert trade.conservative_stop_first_used is True


def test_tv_v190_005_combination_cap_is_enforced():
    result = run_orb_discovery(
        _request(
            strategy_families=["orb_breakout", "orr_reversal", "hybrid_orb"],
            orb_bar_counts=[1, 2, 3, 4],
            reward_risk_grid=[1.0, 1.5, 2.0],
            volume_confirmation_grid=[False, True],
            maximum_combinations=5,
        )
    )
    assert result.combination_count == 5
    assert result.combination_cap_applied is True


def test_tv_v190_006_minimum_trade_gate_controls_winner_eligibility():
    blocked = run_orb_discovery(_request(minimum_trades=20))
    assert blocked.best_composite is None
    assert all(not item.minimum_trades_pass for item in blocked.ranked_combinations)
    passed = run_orb_discovery(_request(minimum_trades=5))
    assert passed.best_composite is not None


def test_tv_v190_007_rankings_and_hash_are_deterministic():
    request = _request(
        reward_risk_grid=[1.0, 2.0],
        volume_confirmation_grid=[False, True],
    )
    first = run_orb_discovery(request)
    second = run_orb_discovery(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.deterministic_hash == second.deterministic_hash


def test_tv_v190_008_clock_window_combo_is_supported():
    request = _request(
        orb_bar_counts=[],
        clock_windows=[("09:15", "09:30")],
        minimum_trades=1,
    )
    result = run_orb_discovery(request)
    assert result.ranked_combinations[0].range_mode == "clock_window"
    assert result.ranked_combinations[0].clock_window == ("09:15", "09:30")


def test_tv_v190_009_no_next_bar_means_no_fabricated_trade():
    only_signal = CandleSeries(
        symbol="RELIANCE",
        timeframe="5m",
        bars=_day(0)[:4],
        snapshot_id="no-next-bar",
        schema_version="candles.v1",
    )
    result = run_orb_discovery(
        _request(series=only_signal, minimum_trades=1)
    )
    assert result.trades == []
    assert result.best_composite is None


def test_tv_v190_010_async_job_api_completes_and_returns_result():
    clear_orb_discovery_jobs()
    response = client.post(
        "/api/v1/orb/discover",
        json=_request().model_dump(mode="json"),
    )
    assert response.status_code == 200
    queued = response.json()["data"]
    assert queued["status"] == "queued"
    status = client.get(f"/api/v1/orb/discover/{queued['job_id']}")
    assert status.status_code == 200
    completed = status.json()["data"]
    assert completed["status"] == "completed"
    assert completed["result"]["combination_count"] == 1


def test_tv_v190_011_unknown_job_returns_404():
    assert client.get("/api/v1/orb/discover/not-found").status_code == 404


def test_tv_v190_012_discovery_is_research_only():
    result = run_orb_discovery(_request())
    assert result.no_future_leakage is True
    assert result.costs_applied is True
    assert result.trade_allowed is False
    assert result.paper_execution_attempted is False
    assert result.order_routing_enabled is False
    assert result.live_trading_blocked is True
