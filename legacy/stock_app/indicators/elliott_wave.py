"""
Elliott Wave Hybrid Detector
============================
Combines three open-source approaches:

1. Structural rule validation  (btcorgtfo/ElliottWaveAnalyzer)
   - W2 < 100% retrace of W1
   - W3 top exceeds W1 top (bull) / W3 bottom below W1 bottom (bear)
   - W4 does not overlap W1 price territory
   - W3 is never the shortest impulse wave
   - W2/W4 alternation: not both deep (>61.8%) or both shallow (<38.2%)

2. Fibonacci scoring bonus  (DrEdwardPCB/python-taew)
   - W2 near 50 / 61.8 / 78.6 % retracement of W1      → +1 point
   - W3 near 161.8 / 200 / 261.8 % extension of W1      → +1 point
   - W4 near 23.6 / 38.2 / 50 % retracement of W3       → +1 point
   - W5 near 61.8 / 100 % of W1 length                  → +1 point
   fib_score = 0-4  (shown in panel as quality metric)

3. Entry / Stop / Target  (ESJavadex/elliot-waves-auto)
   Bullish W5 setup:  entry = W4_high * 1.01
                      stop  = W2_low  * 0.99
                      T1    = entry + risk * 1.618
                      T2    = entry + risk * 2.618
   Bearish W5 setup:  entry = W4_low  * 0.99
                      stop  = W2_high * 1.01
                      T1    = entry - risk * 1.618
                      T2    = entry - risk * 2.618
"""
from __future__ import annotations
import numpy as np
from typing import List, Tuple

# ── Fibonacci tolerance ─────────────────────────────────────────────────────
_FIB_TOL = 0.10   # 10% tolerance around each Fibonacci level

def _near_fib(ratio: float, levels: List[float], tol: float = _FIB_TOL) -> bool:
    return any(abs(ratio - lvl) / lvl <= tol for lvl in levels if lvl > 0)


# ── Pivot detection ──────────────────────────────────────────────────────────
def find_pivots(high: np.ndarray, low: np.ndarray,
                left: int = 3, right: int = 3) -> List[dict]:
    """
    Find alternating swing highs/lows with a left+right bar confirmation window.
    Returns [{bar, price, type}] strictly alternating, sorted by bar index.
    """
    n = len(high)
    raw: List[dict] = []

    for i in range(left, n - right):
        win_hi = high[i - left: i + right + 1]
        win_lo = low[i  - left: i + right + 1]
        if high[i] >= max(win_hi):
            raw.append({'bar': i, 'price': float(high[i]), 'type': 'high'})
        elif low[i] <= min(win_lo):
            raw.append({'bar': i, 'price': float(low[i]),  'type': 'low'})

    # Enforce strict alternation, keep the more extreme of consecutive same-type
    alt: List[dict] = []
    for pv in raw:
        if not alt:
            alt.append(pv)
        elif alt[-1]['type'] == pv['type']:
            prev = alt[-1]
            if pv['type'] == 'high' and pv['price'] >= prev['price']:
                alt[-1] = pv
            elif pv['type'] == 'low'  and pv['price'] <= prev['price']:
                alt[-1] = pv
        else:
            alt.append(pv)
    return alt


# ── Structural rule validation ───────────────────────────────────────────────
def _impulse_rules_bullish(p: List[float]) -> bool:
    """p = [p0..p5] prices for 6 alternating pivots starting at a low."""
    # type guard (even indices = lows, odd = highs)
    w1 = p[1] - p[0]   # length Wave 1 (up)
    w2 = p[1] - p[2]   # Wave 2 retrace (should be < w1)
    w3 = p[3] - p[2]   # Wave 3 (up)
    w4 = p[3] - p[4]   # Wave 4 retrace
    w5 = p[5] - p[4]   # Wave 5 (up)

    if w1 <= 0 or w3 <= 0 or w5 <= 0: return False
    if w2 >= w1:          return False   # W2 ≤ 100% of W1
    if p[2] <= p[0]:      return False   # W2 bottom > W1 bottom
    if p[3] <= p[1]:      return False   # W3 top > W1 top
    if w4 >= w3:          return False   # W4 ≤ 100% of W3
    if p[4] <= p[2]:      return False   # W4 bottom > W2 bottom (no W1 overlap)
    if w3 <= w1 and w3 <= w5: return False  # W3 never shortest
    return True


def _impulse_rules_bearish(p: List[float]) -> bool:
    """p = [p0..p5] starting at a high."""
    w1 = p[0] - p[1]
    w2 = p[2] - p[1]
    w3 = p[2] - p[3]
    w4 = p[4] - p[3]
    w5 = p[4] - p[5]

    if w1 <= 0 or w3 <= 0 or w5 <= 0: return False
    if w2 >= w1:          return False
    if p[2] >= p[0]:      return False
    if p[3] >= p[1]:      return False
    if w4 >= w3:          return False
    if p[4] >= p[2]:      return False
    if w3 <= w1 and w3 <= w5: return False
    return True


def _alternation_ok(retrace2: float, retrace4: float) -> bool:
    """W2 and W4 should not both be deep (>61.8%) or both shallow (<38.2%)."""
    deep2  = retrace2 > 0.618
    deep4  = retrace4 > 0.618
    shal2  = retrace2 < 0.382
    shal4  = retrace4 < 0.382
    if deep2 and deep4: return False
    if shal2 and shal4: return False
    return True


# ── Fibonacci scoring (taew-style) ──────────────────────────────────────────
def _fib_score_bullish(p: List[float]) -> int:
    """Score 0-4 for how many waves land near classic Fibonacci levels."""
    score = 0
    w1 = p[1] - p[0]
    w3 = p[3] - p[2]

    # W2 retracement of W1
    r2 = (p[1] - p[2]) / w1 if w1 > 0 else 0
    if _near_fib(r2, [0.50, 0.618, 0.786]): score += 1

    # W3 extension of W1
    e3 = (p[3] - p[2]) / w1 if w1 > 0 else 0
    if _near_fib(e3, [1.618, 2.0, 2.618]): score += 1

    # W4 retracement of W3
    r4 = (p[3] - p[4]) / w3 if w3 > 0 else 0
    if _near_fib(r4, [0.236, 0.382, 0.50]): score += 1

    # W5 relative to W1
    e5 = (p[5] - p[4]) / w1 if w1 > 0 else 0
    if _near_fib(e5, [0.618, 1.0]): score += 1

    # Alternation bonus check
    if not _alternation_ok(r2, r4): score = max(0, score - 1)
    return score


def _fib_score_bearish(p: List[float]) -> int:
    score = 0
    w1 = p[0] - p[1]
    w3 = p[2] - p[3]

    r2 = (p[2] - p[1]) / w1 if w1 > 0 else 0
    if _near_fib(r2, [0.50, 0.618, 0.786]): score += 1

    e3 = (p[2] - p[3]) / w1 if w1 > 0 else 0
    if _near_fib(e3, [1.618, 2.0, 2.618]): score += 1

    r4 = (p[4] - p[3]) / w3 if w3 > 0 else 0
    if _near_fib(r4, [0.236, 0.382, 0.50]): score += 1

    e5 = (p[4] - p[5]) / w1 if w1 > 0 else 0
    if _near_fib(e5, [0.618, 1.0]): score += 1

    if not _alternation_ok(r2, r4): score = max(0, score - 1)
    return score


# ── ABC corrective validation ────────────────────────────────────────────────
def _abc_bullish(p: List[float]) -> Tuple[bool, int]:
    """p = [p0..p3] starting at a low (low-high-low-high)."""
    wA = p[1] - p[0]
    wB = p[1] - p[2]
    wC = p[3] - p[2]
    if wA <= 0 or wC <= 0: return False, 0
    if wB >= wA: return False, 0
    score = 0
    rB = wB / wA
    eC = wC / wA
    if _near_fib(rB, [0.382, 0.50, 0.618]): score += 1
    if _near_fib(eC, [1.0, 1.618, 2.618]):  score += 1
    return True, score


def _abc_bearish(p: List[float]) -> Tuple[bool, int]:
    """p = [p0..p3] starting at a high."""
    wA = p[0] - p[1]
    wB = p[2] - p[1]
    wC = p[2] - p[3]
    if wA <= 0 or wC <= 0: return False, 0
    if wB >= wA: return False, 0
    score = 0
    rB = wB / wA
    eC = wC / wA
    if _near_fib(rB, [0.382, 0.50, 0.618]): score += 1
    if _near_fib(eC, [1.0, 1.618, 2.618]):  score += 1
    return True, score


# ── Trade setup (ESJavadex-style) ────────────────────────────────────────────
def _trade_setup_impulse_bullish(p: List[float]) -> dict:
    """Entry above W4 high; stop below W2 low; targets at 1.618 / 2.618 × risk."""
    entry = round(p[4] * 1.005, 2)
    stop  = round(p[2] * 0.990, 2)
    risk  = abs(entry - stop)
    return {
        'entry':   entry,
        'stop':    stop,
        'target1': round(entry + risk * 1.618, 2),
        'target2': round(entry + risk * 2.618, 2),
    }

def _trade_setup_impulse_bearish(p: List[float]) -> dict:
    entry = round(p[4] * 0.995, 2)
    stop  = round(p[2] * 1.010, 2)
    risk  = abs(stop - entry)
    return {
        'entry':   entry,
        'stop':    stop,
        'target1': round(entry - risk * 1.618, 2),
        'target2': round(entry - risk * 2.618, 2),
    }

def _trade_setup_abc_bullish(p: List[float]) -> dict:
    """Enter on break above C; stop below C; targets 1.0 / 1.618 × wA."""
    wA = p[1] - p[0]
    entry = round(p[3] * 1.005, 2)
    stop  = round(p[2] * 0.990, 2)
    risk  = abs(entry - stop)
    return {
        'entry':   entry,
        'stop':    stop,
        'target1': round(entry + risk * 1.0, 2),
        'target2': round(entry + risk * 1.618, 2),
    }

def _trade_setup_abc_bearish(p: List[float]) -> dict:
    entry = round(p[3] * 0.995, 2)
    stop  = round(p[2] * 1.010, 2)
    risk  = abs(stop - entry)
    return {
        'entry':   entry,
        'stop':    stop,
        'target1': round(entry - risk * 1.0, 2),
        'target2': round(entry - risk * 1.618, 2),
    }


# ── Main detection ───────────────────────────────────────────────────────────
def detect_elliott_waves(
    high: np.ndarray, low: np.ndarray,
    left: int = 3, right: int = 3,
    max_patterns: int = 5,
) -> List[dict]:
    """
    Scan zigzag pivots for 5-wave impulse and 3-wave corrective Elliott patterns.

    Returns up to max_patterns most-recent valid patterns sorted by end_bar desc.
    Each pattern includes entry/stop/target1/target2 and fib_score (0-4).
    """
    pivots = find_pivots(high, low, left=left, right=right)
    patterns: List[dict] = []

    # ── 5-wave impulse scan (need 6 pivots) ──────────────────────────────────
    for i in range(len(pivots) - 5):
        pts = pivots[i: i + 6]
        types = [pv['type'] for pv in pts]
        p = [pv['price'] for pv in pts]

        if types == ['low','high','low','high','low','high']:
            if _impulse_rules_bullish(p):
                fib = _fib_score_bullish(p)
                setup = _trade_setup_impulse_bullish(p)
                patterns.append(_build(pts, 'impulse', 'bullish', fib, setup))

        elif types == ['high','low','high','low','high','low']:
            if _impulse_rules_bearish(p):
                fib = _fib_score_bearish(p)
                setup = _trade_setup_impulse_bearish(p)
                patterns.append(_build(pts, 'impulse', 'bearish', fib, setup))

    # ── 3-wave corrective scan (need 4 pivots) ───────────────────────────────
    for i in range(len(pivots) - 3):
        pts = pivots[i: i + 4]
        types = [pv['type'] for pv in pts]
        p = [pv['price'] for pv in pts]

        if types == ['low','high','low','high']:
            ok, fib = _abc_bullish(p)
            if ok:
                setup = _trade_setup_abc_bullish(p)
                patterns.append(_build(pts, 'corrective', 'bullish', fib, setup))

        elif types == ['high','low','high','low']:
            ok, fib = _abc_bearish(p)
            if ok:
                setup = _trade_setup_abc_bearish(p)
                patterns.append(_build(pts, 'corrective', 'bearish', fib, setup))

    # Sort by end_bar desc, deduplicate by end_bar, cap at max_patterns
    patterns.sort(key=lambda x: x['end_bar'], reverse=True)
    seen, result = set(), []
    for pat in patterns:
        if pat['end_bar'] not in seen:
            seen.add(pat['end_bar'])
            result.append(pat)
        if len(result) >= max_patterns:
            break
    return result


def _build(pts: List[dict], wave_type: str, direction: str,
           fib_score: int, setup: dict) -> dict:
    """Serialize pattern to a JSON-ready dict."""
    if wave_type == 'impulse':
        labels = ['0','1','2','3','4','5']
    else:
        labels = ['0','A','B','C']

    color = '#22c55e' if direction == 'bullish' else '#ef4444'

    return {
        'type':       wave_type,
        'direction':  direction,
        'color':      color,
        'fib_score':  fib_score,
        'start_bar':  pts[0]['bar'],
        'end_bar':    pts[-1]['bar'],
        'points': [
            {'bar': pv['bar'], 'price': pv['price'], 'label': labels[j]}
            for j, pv in enumerate(pts)
        ],
        **setup,   # entry, stop, target1, target2
    }
