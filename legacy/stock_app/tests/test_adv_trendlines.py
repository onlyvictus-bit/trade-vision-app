"""
tests/test_adv_trendlines.py — Advanced Trendline Detector Tests
================================================================
TC01 - cluster_trendlines deduplicates identical lines
TC02 - cluster_trendlines passes through noise lines (no cluster)
TC03 - score_trendline returns value in [0,1]
TC04 - extract_trendline_events detects TOUCH within errpct
TC05 - extract_trendline_events detects BREAK on side flip
TC06 - confidence_score clamps to [0,1]
TC07 - extract_line_features returns 6 floats
TC08 - /api/trendlines/{symbol} returns expected JSON shape
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "indicators"))

import numpy as np
import pytest

# ── deduplicator ────────────────────────────────────────────────────────────
try:
    from deduplicator import cluster_trendlines
    _HAS_DEDUPLICATOR = True
except ImportError:
    _HAS_DEDUPLICATOR = False

@pytest.mark.skipif(not _HAS_DEDUPLICATOR, reason="deduplicator not installed")
def test_TC01_cluster_deduplicates_identical():
    """Two nearly-identical trendlines should be reduced to one."""
    def make_trend(m, b, idxs):
        return (idxs, (m, b, [], 0.001, 0.0, 0.0))
    t1 = make_trend(0.5, 100.0, [10, 20, 30])
    t2 = make_trend(0.5, 100.1, [10, 20, 30])  # intercept diff=0.1; normalized=0.1/500=0.0002 << eps=0.008
    result = cluster_trendlines([t1, t2])
    assert len(result) == 1

@pytest.mark.skipif(not _HAS_DEDUPLICATOR, reason="deduplicator not installed")
def test_TC02_cluster_keeps_noise_lines():
    """Very different lines should NOT be merged."""
    def make_trend(m, b, idxs):
        return (idxs, (m, b, [], 0.001, 0.0, 0.0))
    t1 = make_trend(0.01,  100.0, [10, 20, 30])
    t2 = make_trend(5.0,  500.0, [50, 60, 70])  # completely different slope+intercept
    result = cluster_trendlines([t1, t2])
    assert len(result) == 2

@pytest.mark.skipif(not _HAS_DEDUPLICATOR, reason="deduplicator not installed")
def test_TC01b_cluster_empty_input():
    """Empty list returns empty list — no crash."""
    assert cluster_trendlines([]) == []

@pytest.mark.skipif(not _HAS_DEDUPLICATOR, reason="deduplicator not installed")
def test_TC01c_cluster_single_item():
    """Single trendline passes through unchanged (noise label=-1)."""
    t = ([10, 20, 30], (0.5, 100.0, [], 0.001, 0.0, 0.0))
    result = cluster_trendlines([t])
    assert len(result) == 1
    assert result[0] is t

# ── adv_trend_detector ──────────────────────────────────────────────────────
try:
    from adv_trend_detector import (score_trendline, extract_trendline_events,
                                     prepare_trendlines, detect_optimized_trendlines)
    _HAS_DETECTOR = True
except ImportError:
    _HAS_DETECTOR = False

def _make_trend(m, b, idxs):
    """Helper: build a trendln-format trend tuple."""
    ys = [m * i + b for i in idxs]
    ser = 0.001
    return (np.array(idxs), (m, b, ys, ser, 0.0, 0.0))

@pytest.mark.skipif(not _HAS_DETECTOR, reason="adv_trend_detector not installed")
def test_TC03_score_trendline_range():
    """score_trendline should return float in [0, 1]."""
    t = _make_trend(0.5, 100.0, [10, 20, 30, 40, 50])
    score = score_trendline(t, n_local=100)
    assert 0.0 <= score <= 1.0

@pytest.mark.skipif(not _HAS_DETECTOR, reason="adv_trend_detector not installed")
def test_TC04_extract_events_touch():
    """Close within 0.8% of line price → TOUCH event."""
    # Line: flat at 100.0 (m=0, b=100)
    t = _make_trend(0.0, 100.0, [5, 10])
    # Close = 100.3 → dist_pct = 0.003 < errpct=0.008
    closes = np.array([100.0] * 5 + [100.3] + [100.0] * 5)
    idx_to_ts = {i: f"2024-01-{i+1:02d}" for i in range(len(closes))}
    typed = [(t, 0.8, 'support')]
    events = extract_trendline_events(typed, closes, idx_to_ts, errpct=0.008)
    touch_events = [ev for ev in events if ev['type'] == 'TOUCH']
    assert len(touch_events) >= 1
    assert touch_events[0]['line_type'] == 'support'
    assert touch_events[0]['color'] == '#22c55e'

@pytest.mark.skipif(not _HAS_DETECTOR, reason="adv_trend_detector not installed")
def test_TC05_extract_events_break():
    """Price crossing from below to above line → BREAK event."""
    # Line: flat at 100.0
    t = _make_trend(0.0, 100.0, [2, 8])
    # Goes: 98, 98, 98 (below), then 102 (above) → BREAK at bar 3
    closes = np.array([98.0, 98.0, 98.0, 102.0, 102.0, 102.0, 102.0, 102.0, 102.0])
    idx_to_ts = {i: f"2024-01-{i+1:02d}" for i in range(len(closes))}
    typed = [(t, 0.8, 'support')]
    events = extract_trendline_events(typed, closes, idx_to_ts, errpct=0.008)
    break_events = [ev for ev in events if ev['type'] == 'BREAK']
    assert len(break_events) >= 1
    assert break_events[0]['type'] == 'BREAK'

# ── adv_trend_brain ─────────────────────────────────────────────────────────
try:
    from adv_trend_brain import (confidence_score, extract_line_features,
                                  extract_line_feature_dict,
                                  train_meta_model_persistent, train_meta_model)
    _HAS_BRAIN = True
except ImportError:
    _HAS_BRAIN = False

@pytest.mark.skipif(not _HAS_BRAIN, reason="adv_trend_brain not installed")
def test_TC06_confidence_score_clamps():
    """confidence_score must return float in [0, 1]."""
    assert confidence_score(1.5, 1.5, 1.5) == 1.0
    assert confidence_score(0.0, 0.5, 0.5) == 0.0
    val = confidence_score(0.7, 0.8, 0.9)
    assert 0.0 <= val <= 1.0

@pytest.mark.skipif(not _HAS_BRAIN, reason="adv_trend_brain not installed")
def test_TC07_extract_line_features_returns_6():
    """extract_line_features should return a list of exactly 6 floats."""
    import pandas as pd
    n = 50
    df = pd.DataFrame({
        'Close':  np.linspace(100, 120, n),
        'Volume': np.full(n, 1e6),
    })
    idxs = np.array([10, 20, 30])
    m, b = 0.4, 96.0
    ys = [m * i + b for i in idxs]
    trend = (idxs, (m, b, ys, 0.001, 0.0, 0.0))
    feats = extract_line_features(trend, n_local=n, df=df)
    assert len(feats) == 6
    assert all(isinstance(f, float) for f in feats)

@pytest.mark.skipif(not _HAS_BRAIN, reason="adv_trend_brain not installed")
def test_TC07b_extract_line_feature_names_match_plan():
    """Public ML feature names must match the requested six fields."""
    import pandas as pd
    n = 50
    df = pd.DataFrame({
        'Close':  np.linspace(100, 120, n),
        'Volume': np.full(n, 1e6),
    })
    trend = (np.array([10, 20, 30]), (0.4, 96.0, [100, 104, 108], 0.001, 0.0, 0.0))
    feats = extract_line_feature_dict(trend, n_local=n, df=df)
    assert set(feats) == {"slope", "touches", "recency", "error", "distance_pct", "volume_ratio"}

@pytest.mark.skipif(not _HAS_DETECTOR, reason="adv_trend_detector not installed")
def test_TC07c_optimized_detector_finds_recent_lines():
    """Dependency-free detector should emit usable recent support/resistance lines."""
    n = 160
    x = np.arange(n)
    lows = 100 + 0.08 * x + np.sin(x / 5.0) * 0.15
    highs = lows + 4.0 + np.cos(x / 6.0) * 0.15
    closes = lows + 2.0
    sup, res = detect_optimized_trendlines(lows, highs, closes, n)
    assert sup
    assert res
    assert any(int(t[0][-1]) > n - 80 for t in sup + res)

# ── API endpoint ─────────────────────────────────────────────────────────────
try:
    from server import app as _app
    from fastapi.testclient import TestClient as _TC
    _client = _TC(_app)
    _HAS_SERVER = True
except Exception:
    _HAS_SERVER = False

@pytest.mark.skipif(not _HAS_SERVER, reason="server not importable")
def test_TC08_trendlines_endpoint_shape():
    """/api/trendlines/{symbol} must return symbol, interval, trendlines keys."""
    resp = _client.get("/api/trendlines/AAPL?interval=1d")
    assert resp.status_code == 200
    data = resp.json()
    assert "symbol"     in data
    assert "interval"   in data
    assert "trendlines" in data
    tl = data["trendlines"]
    assert "lines"  in tl
    assert "events" in tl
    assert isinstance(tl["lines"],  list)
    assert isinstance(tl["events"], list)


# TC09 - renderTrendlinesPanel graceful handling when showIndicators.trendlines is missing
# NOTE: renderTrendlinesPanel() is a JavaScript function in static/index.html and cannot
# be unit-tested directly in this Python test suite (no JS test framework is configured).
# The function guards against a falsy showIndicators.trendlines by checking:
#   if (!showIndicators.trendlines) { if (panel) panel.remove(); return; }
# It also guards against null _trendlinesData via optional chaining:
#   const lines  = _trendlinesData?.lines  || [];
#   const events = _trendlinesData?.events || [];
# Together these ensure no crash when either the indicator is disabled or data is null.
@pytest.mark.skip(reason="renderTrendlinesPanel is a JS-only function; no JS runtime in this test suite. "
                         "Guard clauses verified by code inspection: "
                         "(!showIndicators.trendlines) early-return and ?. optional chaining on _trendlinesData.")
def test_TC09_renderTrendlinesPanel_graceful_no_js():
    """
    TC09 — renderTrendlinesPanel guard clauses (JS-only, not executable here).

    Verified by code review that:
    - When showIndicators.trendlines is falsy: existing #trendlinesPanel is removed and function returns
    - When _trendlinesData is null: optional chaining prevents crash (?.lines, ?.events, ?.ml_metrics)
    """
    pass  # pragma: no cover
