"""
tests/test_research_engine.py — Core Research Engine Unit Tests
=================================================================
"""
from __future__ import annotations

import pandas as pd
import pytest
from pathlib import Path
from research.signals import registry
from research.engine.combinator import generate_combos, is_valid_combo
from research.engine.scorer import compute_composite_score
from research.engine.backtester import BacktestResult, run_vectorbt_backtest
from research.data.mtf_loader import align_mtf_data, fetch_mtf_data
from research.validation.gates import mark_with_gates, rankable_only
from research.engine.runner import run_discovery

# ── Combinator Tests ──────────────────────────────────────────────────────

def test_is_valid_combo_rules():
    """Verify pruning rules for signal combinations."""
    # Mock SignalDefinition-like objects
    class MockSignal:
        def __init__(self, name, category, direction="bullish", tags=None):
            self.name = name
            self.category = category
            self.direction = direction
            self.tags = tags or []

    s1 = MockSignal("s1", "trend", tags=["ema", "trend-following"])
    s2 = MockSignal("s2", "trend", tags=["sma", "trend-following"]) # Different tags except 'trend-following'
    s3 = MockSignal("s3", "momentum")
    s4 = MockSignal("s4", "trend", tags=["ema", "trend-following", "cross"]) # Overlaps s1 by 2 tags
    
    # Rule 1: Max 2 from same category
    assert is_valid_combo([s1, s2, s3]) is True
    assert is_valid_combo([s1, s2, s4]) is False # All trend
    
    # Rule 2: 3+ signals MUST include at least 1 trend
    m1 = MockSignal("m1", "momentum")
    m2 = MockSignal("m2", "momentum")
    m3 = MockSignal("m3", "volatility")
    assert is_valid_combo([m1, m2, m3]) is False
    
    # Rule 5: No redundant combos (overlapping tags)
    assert is_valid_combo([s1, s4]) is False # Both trend, both have 'ema' and 'trend-following' tags

def test_generate_combos_filtering():
    """Verify generate_combos respects direction and category filters."""
    combos = generate_combos(registry, max_signals=1, direction="long", categories=["trend"])
    for c in combos:
        sig = registry.get(c[0])
        assert sig.direction == "bullish"
        assert sig.category == "trend"

# ── Scorer Tests ──────────────────────────────────────────────────────────

def test_composite_score_logic():
    """Verify scoring logic penalizes high drawdown and rewards Sharpe."""
    res_good = BacktestResult(trades=50, win_rate=0.6, total_return=0.2, sharpe=2.0, max_drawdown=0.05)
    res_bad = BacktestResult(trades=50, win_rate=0.4, total_return=0.05, sharpe=0.5, max_drawdown=0.20)
    
    score_good = compute_composite_score(res_good)
    score_bad = compute_composite_score(res_bad)
    
    assert score_good > score_bad
    assert 0 <= score_good <= 100
    assert 0 <= score_bad <= 100

# ── MTF Alignment Tests ──────────────────────────────────────────────────

def test_mtf_alignment_correctness():
    """Verify merge_asof alignment in MTF loader."""
    # 1H index
    h1_idx = pd.date_range("2024-01-01", periods=5, freq="1H")
    h1_df = pd.DataFrame({"close": [100, 101, 102, 103, 104]}, index=h1_idx)
    
    # 1D index (starts at 00:00)
    d1_idx = pd.date_range("2024-01-01", periods=2, freq="1D")
    d1_df = pd.DataFrame({"close": [1000, 1100]}, index=d1_idx)
    
    df_map = {"1h": h1_df, "1d": d1_df}
    aligned = align_mtf_data(df_map, "1h")
    
    aligned_d1 = aligned["1d"]
    assert len(aligned_d1) == 5
    # All 5 hours of Jan 1st should have Jan 1st's Daily close (1000)
    assert (aligned_d1["close"] == 1000).all()


def test_mtf_local_resample_cache(monkeypatch):
    """Local 1m data should resample to higher TFs and write Parquet cache."""
    import research.data.mtf_cache as mtf_cache

    work = Path("cache") / "test_mtf_cache"
    work.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mtf_cache, "CACHE_ROOT", work)

    idx = pd.date_range("2024-01-01 09:15", periods=30, freq="1min")
    df = pd.DataFrame({
        "datetime": idx,
        "open": range(30),
        "high": [x + 1 for x in range(30)],
        "low": range(30),
        "close": [x + 0.5 for x in range(30)],
        "volume": [100] * 30,
    })
    src = work / "one_min.csv"
    df.to_csv(src, index=False)

    result = fetch_mtf_data("TEST", ["1m", "5m"], "2024-01-01", "2024-01-02", data_path=str(src))

    assert len(result["1m"]) == 30
    assert len(result["5m"]) > 1
    assert list(work.rglob("*.parquet"))


def test_fail_closed_pipeline_rejects_before_ranking():
    """Rejected strategies must never enter rankable output."""
    good = {"name": "good", "result": BacktestResult(trades=30), "composite_score": 10}
    bad = {"name": "bad", "result": BacktestResult(trades=30), "composite_score": 99}

    gated_good = mark_with_gates(good, {"WF": lambda c: True, "MC": lambda c: True})
    gated_bad = mark_with_gates(bad, {"WF": lambda c: False, "MC": lambda c: True})
    rankable = rankable_only([gated_bad, gated_good])

    assert gated_bad["passed"] is False
    assert gated_bad["rejected_by"] == "WF"
    assert [r["name"] for r in rankable] == ["good"]


def test_runner_validation_gates_can_reject_all():
    """Impossible validation score should reject candidates before ranking."""
    idx = pd.date_range("2024-01-01 09:15", periods=220, freq="1min")
    close = list(range(100, 320))
    df = pd.DataFrame({
        "datetime": idx,
        "open": close,
        "high": [x + 1 for x in close],
        "low": [x - 1 for x in close],
        "close": close,
        "volume": [1000] * len(close),
    })
    work = Path("cache") / "test_runner_gates"
    work.mkdir(parents=True, exist_ok=True)
    src = work / "one_min.csv"
    df.to_csv(src, index=False)

    results = run_discovery(
        "TEST",
        "2024-01-01",
        "2024-01-02",
        interval="1m",
        data_path=str(src),
        max_signals=1,
        categories=["trend"],
        fixed_sl_grid=[0.005],
        fixed_tp_grid=[0.01],
        min_trades=1,
        min_validation_trades=1,
        min_holdout_trades=1,
        min_validation_score=999.0,
        min_holdout_score=999.0,
        mc_runs=10,
        max_workers=1,
        use_processes=False,
        max_param_combos=2,
    )

    assert results == []

# ── Backtester Tests ─────────────────────────────────────────────────────

@pytest.mark.skipif(True, reason="VectorBT might not be available or too slow for unit tests")
def test_vectorbt_run_smoke():
    """Smoke test for VectorBT wrapper."""
    idx = pd.date_range("2024-01-01", periods=100, freq="1D")
    df = pd.DataFrame({"close": range(100, 200)}, index=idx)
    entries = pd.Series(False, index=idx)
    entries.iloc[10] = True
    exits = pd.Series(False, index=idx)
    
    res = run_vectorbt_backtest(df, entries, exits, interval="1d")
    assert isinstance(res, BacktestResult)
    assert res.trades == 1
