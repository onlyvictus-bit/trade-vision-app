"""V1 cheapest pre-test (ORB v2 plan §2): do gap/CPR layers earn their keep?

H1: breakout trades on NARROW days beat WIDE days (net-R distributions).
H2: gap-aligned trades beat counter-gap trades.
H3: CPR-class split vs close-location-tercile split carry the same
    information (memo CPR-04 redundancy) -> keep the cheaper feature.

Method: run the EXISTING v1.90 discovery on ~1yr 5m data for liquid symbols,
label each trade day with gap/CPR/tercile via orb/context.py, compare with
Mann-Whitney U + rank-biserial effect + Holm correction. Min cell n = 30.
Reverse-outcome rule: if WIDE beats NARROW (or counter beats aligned),
the layer flips or dies - picked before looking.

Outputs: delete/orb_pretest_v1.json + delete/orb_pretest_v1.md
"""

import json
import sys
from datetime import datetime

sys.path.insert(0, r"D:\Projects\trading-platforms\stock-app\trade-vision-app\apps\api")

import pandas as pd
from scipy.stats import mannwhitneyu

from app.models import OrbDiscoveryRequest
from app.orb import context as C
from app.orb.discovery import run_orb_discovery
from app.orb.hstry_csv import load_hstry_series

SYMBOLS = ["RELIANCE", "BEL", "TCS", "INFY", "HDFCBANK"]
START = "2025-01-01"
MIN_CELL_N = 30
ALPHA = 0.05


def day_labels(symbol: str):
    """session_date -> (gap_state, cpr_class, close_tercile)."""
    series = load_hstry_series(symbol, "5m", start_date=START)
    frame = pd.DataFrame(
        [
            {"open": b.open, "high": b.high, "low": b.low, "close": b.close,
             "volume": b.volume or 0.0}
            for b in series.bars
        ],
        index=pd.to_datetime([b.timestamp_ns for b in series.bars]),
    )
    frame.index = frame.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
    daily = C.daily_from_intraday(frame)
    session_dates = sorted({ts.strftime("%Y-%m-%d") for ts in frame.index})
    opens = {}
    for d in session_dates:
        day_bars = frame[frame.index.strftime("%Y-%m-%d") == d]
        if len(day_bars):
            opens[d] = float(day_bars.iloc[0]["open"])
    labels = {}
    for rec in C.classify_history(symbol, daily, opens):
        if rec["context_suspect"]:
            continue
        prev = daily.loc[: rec["session_date"]].iloc[-2]
        loc = (prev["close"] - prev["low"]) / (prev["high"] - prev["low"]) if prev["high"] > prev["low"] else 0.5
        tercile = "low" if loc < 1 / 3 else ("high" if loc > 2 / 3 else "mid")
        labels[rec["session_date"]] = {
            "gap": rec["gap_state"], "cpr": rec["cpr_class"], "tercile": tercile,
        }
    return labels


def collect_trades():
    """(symbol, date, side, family, net_r) for every backtest trade."""
    rows = []
    for symbol in SYMBOLS:
        try:
            series = load_hstry_series(symbol, "5m", start_date=START)
        except Exception as exc:
            print(f"  {symbol}: skipped ({exc})")
            continue
        req = OrbDiscoveryRequest(
            series=series,
            strategy_families=["orb_breakout", "orr_reversal"],
            orb_bar_counts=[3],
            clock_windows=[("09:15", "09:20"), ("09:15", "09:30"),
                           ("09:15", "09:35"), ("09:15", "09:40")],
            reward_risk_grid=[2.0],
            volume_confirmation_grid=[False],
            maximum_combinations=250,
            minimum_trades=1,
        )
        result = run_orb_discovery(req)
        combo_family = {m.combo_id: m.strategy_family for m in result.ranked_combinations}
        for t in result.trades:
            rows.append({
                "symbol": symbol, "date": t.local_session_date, "side": t.side,
                "family": combo_family.get(t.combo_id, "?"), "net_r": t.net_r,
            })
        print(f"  {symbol}: {len(result.trades)} trades")
    return rows


def mw(x, y):
    """Mann-Whitney U + rank-biserial r. Returns (p, r, med_x, med_y)."""
    res = mannwhitneyu(x, y, alternative="two-sided")
    n1, n2 = len(x), len(y)
    r = 1.0 - 2.0 * res.statistic / (n1 * n2)
    return float(res.pvalue), float(r), float(pd.Series(x).median()), float(pd.Series(y).median())


def main() -> None:
    print("V1 pre-test: labeling days...")
    labels = {}
    for symbol in SYMBOLS:
        try:
            labels[symbol] = day_labels(symbol)
            print(f"  {symbol}: {len(labels[symbol])} labeled sessions")
        except Exception as exc:
            print(f"  {symbol}: label failed ({exc})")
    print("collecting discovery trades...")
    trades = collect_trades()

    def labeled():
        for t in trades:
            lab = labels.get(t["symbol"], {}).get(t["date"])
            if lab:
                yield {**t, **lab}

    rows = list(labeled())
    print(f"labeled trades: {len(rows)}")
    df = pd.DataFrame(rows)

    tests = {}
    # H1: breakout net_r on NARROW vs WIDE days
    br = df[df["family"] == "orb_breakout"]
    narrow = br[br["cpr"] == "NARROW"]["net_r"].tolist()
    wide = br[br["cpr"] == "WIDE"]["net_r"].tolist()
    # H2: gap-aligned vs counter-gap (FLAT counts aligned either side)
    def aligned(r):
        if r["gap"] == "FLAT":
            return True
        if r["gap"] in ("GAP_UP", "LARGE_GAP_UP"):
            return r["side"] == "LONG"
        return r["side"] == "SHORT"
    al = [r["net_r"] for r in rows if aligned(r)]
    co = [r["net_r"] for r in rows if not aligned(r)]
    # H3: CPR split vs tercile split (breakout trades): compare separation strength
    ter_hi = br[br["tercile"] == "high"]["net_r"].tolist()
    ter_lo = br[br["tercile"] == "low"]["net_r"].tolist()

    results = {}
    for hid, x, y, desc in [
        ("H1_narrow_vs_wide", narrow, wide, "breakout NARROW-day R vs WIDE-day R"),
        ("H2_aligned_vs_counter", al, co, "gap-aligned R vs counter-gap R"),
        ("H3_cpr_split", narrow, wide, "CPR-class separation (same as H1 by construction)"),
        ("H3_tercile_split", ter_hi, ter_lo, "close-tercile high vs low separation"),
    ]:
        if len(x) >= MIN_CELL_N and len(y) >= MIN_CELL_N:
            p, r, mx, my = mw(x, y)
            results[hid] = {"n1": len(x), "n2": len(y), "p": p, "r": r,
                            "med1": mx, "med2": my, "desc": desc, "verdict": None}
        else:
            results[hid] = {"n1": len(x), "n2": len(y), "p": None, "r": None,
                            "med1": None, "med2": None, "desc": desc,
                            "verdict": "INSUFFICIENT_N"}

    # Holm correction over testable hypotheses
    testable = sorted(
        [(hid, r) for hid, r in results.items() if r["p"] is not None],
        key=lambda kv: kv[1]["p"],
    )
    m = len(testable)
    for rank, (hid, r) in enumerate(testable):
        thresh = ALPHA / (m - rank)
        sig = r["p"] <= thresh
        direction_ok = (r["med1"] or 0) > (r["med2"] or 0)
        if hid.startswith("H3"):
            r["verdict"] = "REDUNDANT_CHECK" if sig else "NO_SEPARATION"
        else:
            r["verdict"] = "GO" if (sig and direction_ok) else ("REVERSE" if (sig and not direction_ok) else "NO_GO")
        r["holm_threshold"] = thresh

    out = {
        "generated_at": datetime.now().isoformat(),
        "symbols": SYMBOLS, "start": START, "min_cell_n": MIN_CELL_N,
        "total_trades": len(rows), "results": results,
    }
    with open(r"D:\Projects\trading-platforms\stock-app\trade-vision-app\delete\orb_pretest_v1.json", "w") as f:
        json.dump(out, f, indent=1)
    lines = ["# V1 pre-test results (H1/H2/H3)", "",
             f"symbols={SYMBOLS} start={START} labeled_trades={len(rows)}", ""]
    for hid, r in results.items():
        lines.append(f"## {hid}: {r['desc']}")
        if r["p"] is None:
            lines.append(f"n1={r['n1']} n2={r['n2']} -> **{r['verdict']}** (need n>={MIN_CELL_N})")
        else:
            lines.append(f"n1={r['n1']} n2={r['n2']} p={r['p']:.4f} (Holm<={r['holm_threshold']:.4f}) "
                         f"r={r['r']:+.3f} med1={r['med1']:.3f} med2={r['med2']:.3f} -> **{r['verdict']}**")
        lines.append("")
    with open(r"D:\Projects\trading-platforms\stock-app\trade-vision-app\delete\orb_pretest_v1.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("saved to delete/orb_pretest_v1.json + .md")


if __name__ == "__main__":
    main()
