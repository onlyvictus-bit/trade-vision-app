"""ORB v2.00 cheapest pre-test (pre-registered H1/H2/H3) — research only.

Runs the EXISTING v1.90 discovery engine on ~2 years of 5m HSTRY data for five
liquid symbols, then labels every backtested trade with the day's gap class and
CPR class (memo CPR-01) and tests the plan's pre-registered hypotheses:

  H1  breakout trades: NARROW-CPR days outperform WIDE-CPR days (net_r)
  H2  gap-aligned trades outperform counter-gap trades
  H3  redundancy: CPR class vs raw close-location-in-range — if the cheap
      close-location split carries the same effect, the CPR layer is CUT

Statistics per plan V1: min cell n>=30, Mann-Whitney U, Cliff's delta effect
size, Holm correction within the test family, base rates reported.

No trading authority: research output only.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from scipy import stats

TV_API = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(TV_API))

from app.models import OrbDiscoveryRequest  # noqa: E402
from app.orb import run_orb_discovery  # noqa: E402
from app.orb.hstry_csv import load_hstry_series  # noqa: E402

SYMBOLS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "SBIN"]
START = "2024-04-01"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "orb_research" / "pretest"
MIN_CELL = 30


def daily_context(series_bars: list) -> pd.DataFrame:
    rows = [
        {
            "ts": pd.Timestamp(b.timestamp_ns, unit="ns") + pd.Timedelta(minutes=330),
            "open": b.open, "high": b.high, "low": b.low, "close": b.close,
        }
        for b in series_bars
    ]
    df = pd.DataFrame(rows).set_index("ts")
    daily = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    daily["prev_high"] = daily["high"].shift(1)
    daily["prev_low"] = daily["low"].shift(1)
    daily["prev_close"] = daily["close"].shift(1)
    daily["tr"] = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - daily["close"].shift(1)).abs(),
        (daily["low"] - daily["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    daily["atr14"] = daily["tr"].rolling(14).mean().shift(1)  # PIT: D-1 close only
    daily = daily.dropna(subset=["prev_close", "atr14"])
    daily["gap_pct"] = (daily["open"] - daily["prev_close"]) / daily["prev_close"] * 100.0
    daily["atr_pct"] = daily["atr14"] / daily["prev_close"] * 100.0
    large_thr = pd.concat([pd.Series(1.0, index=daily.index), daily["atr_pct"] * 1.4], axis=1).max(axis=1)
    daily["gap_class"] = "flat"
    daily.loc[daily["gap_pct"] > 0.1, "gap_class"] = "gap_up"
    daily.loc[daily["gap_pct"] < -0.1, "gap_class"] = "gap_down"
    daily.loc[daily["gap_pct"] >= large_thr, "gap_class"] = "large_up"
    daily.loc[daily["gap_pct"] <= -large_thr, "gap_class"] = "large_down"
    pivot = (daily["prev_high"] + daily["prev_low"] + daily["prev_close"]) / 3.0
    bc = (daily["prev_high"] + daily["prev_low"]) / 2.0
    tc = 2 * pivot - bc
    width = (bc - tc).abs()
    daily["cpr_width"] = width
    daily["width_atr"] = width / daily["atr14"]
    daily["width_pct"] = width / daily["prev_close"] * 100.0
    # CPR-01 precedence partition (memo v2.2): NARROW first by width_atr
    daily["cpr_class"] = "NORMAL"
    daily.loc[daily["width_atr"] < 0.5, "cpr_class"] = "NARROW"
    daily.loc[(daily["width_atr"] >= 0.5) & ((daily["width_atr"] > 1.0) | (daily["width_pct"] > 0.6)), "cpr_class"] = "WIDE"
    # H3 comparator: raw close-location-in-range (PDC inside yesterday's range)
    rng = (daily["prev_high"] - daily["prev_low"]).replace(0, pd.NA)
    daily["close_loc"] = ((daily["prev_close"] - daily["prev_low"]) / rng).astype(float)
    daily["clo_near_mid"] = (daily["close_loc"] - 0.5).abs() < 1.0 / 6.0  # middle tercile
    return daily


def cliffs_delta(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adj, running = {}, 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adj[name] = running
    return adj


def mw(a: list[float], b: list[float]) -> tuple[float, float, float]:
    if len(a) < 2 or len(b) < 2:
        return 0.0, 1.0, 0.0
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return float(u), float(p), cliffs_delta(a, b)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_trades: list[dict] = []
    day_base_rates: dict[str, dict] = {}
    for sym in SYMBOLS:
        series = load_hstry_series(sym, "5m", start_date=START)
        result = run_orb_discovery(OrbDiscoveryRequest(series=series))
        ctx = daily_context(series.bars)
        base = ctx["cpr_class"].value_counts(normalize=True).round(4).to_dict()
        gaps = ctx["gap_class"].value_counts(normalize=True).round(4).to_dict()
        day_base_rates[sym] = {"cpr_days": base, "gap_days": gaps, "session_days": int(len(ctx))}
        for t in result.trades:
            d = t.local_session_date
            if d not in ctx.index.strftime("%Y-%m-%d").values:
                continue
            row = ctx.loc[d]
            aligned = (t.side == "LONG" and row["gap_pct"] > 0.1) or (t.side == "SHORT" and row["gap_pct"] < -0.1)
            all_trades.append({
                "symbol": sym, "date": d, "combo_id": t.combo_id,
                "signal_type": t.signal_type, "side": t.side, "net_r": t.net_r,
                "gross_r": t.gross_r, "outcome": t.outcome,
                "gap_class": row["gap_class"], "cpr_class": row["cpr_class"],
                "width_atr": round(float(row["width_atr"]), 4),
                "close_loc": round(float(row["close_loc"]), 4) if pd.notna(row["close_loc"]) else None,
                "clo_near_mid": bool(row["clo_near_mid"]),
                "gap_aligned": bool(aligned),
            })
        print(f"{sym}: {len(result.trades)} trades over {len(ctx)} session days", flush=True)

    df = pd.DataFrame(all_trades)
    df.to_csv(OUT_DIR / "pretest_trades.csv", index=False)
    breakout = df[df["signal_type"].isin(["BREAKOUT_LONG", "BREAKDOWN_SHORT"])]

    tests: dict[str, dict] = {}

    def add_test(name: str, a: list[float], b: list[float], na: int, nb: int) -> None:
        u, p, delta = mw(a, b)
        tests[name] = {
            "n_a": len(a), "n_b": len(b), "mean_a": round(sum(a) / len(a), 4) if a else None,
            "mean_b": round(sum(b) / len(b), 4) if b else None,
            "mw_u": u, "p_value": p, "cliffs_delta": round(delta, 4),
            "min_cell_pass": len(a) >= MIN_CELL and len(b) >= MIN_CELL,
            "n_days_a": na, "n_days_b": nb,
        }

    # H1: breakout trades, NARROW vs WIDE CPR days (pooled across symbols)
    h1a = breakout[breakout["cpr_class"] == "NARROW"]["net_r"].tolist()
    h1b = breakout[breakout["cpr_class"] == "WIDE"]["net_r"].tolist()
    add_test("H1_narrow_vs_wide_breakout", h1a, h1b,
             breakout[breakout["cpr_class"] == "NARROW"]["date"].nunique(),
             breakout[breakout["cpr_class"] == "WIDE"]["date"].nunique())

    # H2: gap-aligned vs counter-gap (all non-flat trades)
    h2a = df[df["gap_aligned"]]["net_r"].tolist()
    h2b = df[~df["gap_aligned"] & (df["gap_class"] != "flat")]["net_r"].tolist()
    add_test("H2_aligned_vs_counter", h2a, h2b,
             df[df["gap_aligned"]]["date"].nunique(),
             df[~df["gap_aligned"] & (df["gap_class"] != "flat")]["date"].nunique())

    # H3: redundancy — same semantic split via raw close-location (no CPR math)
    h3a = breakout[breakout["clo_near_mid"]]["net_r"].tolist()   # near mid ⟺ NARROW
    h3b = breakout[~breakout["clo_near_mid"]]["net_r"].tolist()  # far from mid ⟺ WIDE-ish
    add_test("H3_closeloc_nearmid_vs_far", h3a, h3b,
             breakout[breakout["clo_near_mid"]]["date"].nunique(),
             breakout[~breakout["clo_near_mid"]]["date"].nunique())

    adj = holm({k: v["p_value"] for k, v in tests.items() if k != "H3_closeloc_nearmid_vs_far"})
    for k in tests:
        tests[k]["p_holm"] = adj.get(k)
        tests[k]["significant_holm"] = bool(adj.get(k, 1.0) < 0.05)

    # H3 verdict: CPR effect vs close-location effect (same direction semantics)
    d_cpr = tests["H1_narrow_vs_wide_breakout"]["cliffs_delta"]
    d_clo = tests["H3_closeloc_nearmid_vs_far"]["cliffs_delta"]
    h3_verdict = "REDUNDANT (keep close-location, cut CPR layer)" if abs(d_clo) >= abs(d_cpr) - 0.02 else "CPR adds signal beyond close-location"

    verdicts = {
        "H1_gap_layer_cpr": {
            "go": tests["H1_narrow_vs_wide_breakout"]["significant_holm"] and tests["H1_narrow_vs_wide_breakout"]["min_cell_pass"],
            "detail": tests["H1_narrow_vs_wide_breakout"],
        },
        "H2_gap_layer_bias": {
            "go": tests["H2_aligned_vs_counter"]["significant_holm"] and tests["H2_aligned_vs_counter"]["min_cell_pass"],
            "detail": tests["H2_aligned_vs_counter"],
        },
        "H3_cpr_redundancy": {"verdict": h3_verdict, "delta_cpr": d_cpr, "delta_closeloc": d_clo, "detail": tests["H3_closeloc_nearmid_vs_far"]},
    }

    payload = {
        "pretest_version": "orb-pretest-v1",
        "pre_registered": {
            "H1": "breakout net_r: NARROW > WIDE CPR days",
            "H2": "net_r: gap-aligned > counter-gap",
            "H3": "CPR class redundant with close-location tercile (CPRW=(2/3)|PDC-BC|)",
            "decision_rule": "GO per layer if Holm p<0.05 AND both cells n>=30 trades; H3 redundant if |delta_closeloc| >= |delta_cpr| - 0.02",
            "symbols": SYMBOLS, "start": START, "min_cell": MIN_CELL,
        },
        "day_base_rates": day_base_rates,
        "trades_total": len(df),
        "tests": tests,
        "verdicts": verdicts,
    }
    (OUT_DIR / "pretest_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(verdicts, indent=2))
    print(f"\nSaved: {OUT_DIR/'pretest_results.json'} and pretest_trades.csv")


if __name__ == "__main__":
    main()
