from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "indicator_audit"
INFY_1M = Path(r"C:\Users\sakth\Downloads\HSTRY\INFY_NSE_1m.csv")
MIN_FULL_TRADES = 100
MIN_SPLIT_TRADES = 20


def load_infy_5m() -> pd.DataFrame:
    raw = pd.read_csv(INFY_1M)
    raw["datetime"] = pd.to_datetime(raw["date"].astype(str) + " " + raw["time"].astype(str), errors="coerce")
    raw = raw.dropna(subset=["datetime"]).sort_values("datetime").set_index("datetime")
    for col in ["open", "high", "low", "close", "volume"]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw.dropna(subset=["open", "high", "low", "close"])
    df = raw.resample("5min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })
    return df.dropna(subset=["open", "high", "low", "close"]).query("volume > 0").copy()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]

    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    df["rsi_14"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    df["ema_fast_21"] = c.ewm(span=21, adjust=False, min_periods=21).mean()
    df["ema_slow_55"] = c.ewm(span=55, adjust=False, min_periods=55).mean()
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal_line"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal_line"]
    df["macd_bull"] = (df["macd"] > df["macd_signal_line"]) & (df["macd"].shift(1) <= df["macd_signal_line"].shift(1))
    df["macd_bear"] = (df["macd"] < df["macd_signal_line"]) & (df["macd"].shift(1) >= df["macd_signal_line"].shift(1))

    prev_close = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    df["atr_14_sma"] = tr.rolling(14, min_periods=14).mean()

    fast = df["ema_fast_21"]
    slow = df["ema_slow_55"]
    long_state = (
        (fast > slow) & (c > fast) & (fast > fast.shift(8)) & (slow > slow.shift(8))
        & ((fast - slow) > df["atr_14_sma"] * 0.15)
    )
    short_state = (
        (fast < slow) & (c < fast) & (fast < fast.shift(8)) & (slow < slow.shift(8))
        & ((slow - fast) > df["atr_14_sma"] * 0.15)
    )
    long_conf = long_state.rolling(5, min_periods=5).sum().eq(5)
    short_conf = short_state.rolling(5, min_periods=5).sum().eq(5)
    df["long_run_bull"] = long_conf & ~long_conf.shift(1, fill_value=False)
    df["short_run_bear"] = short_conf & ~short_conf.shift(1, fill_value=False)

    rolling_max = c.rolling(50, min_periods=10).max()
    df["drawdown_pct"] = (c - rolling_max) / rolling_max.replace(0, np.nan)
    df["drawdown_recovery"] = (
        (df["drawdown_pct"].rolling(3, min_periods=1).min() < -0.01)
        & (df["drawdown_pct"] > df["drawdown_pct"].shift(1))
        & (df["drawdown_pct"] > -0.005)
    )

    n = 14
    up = h.diff()
    down = -l.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    atr = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    df["plus_di_14"] = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr.replace(0, np.nan)
    df["minus_di_14"] = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr.replace(0, np.nan)
    dx = 100 * (df["plus_di_14"] - df["minus_di_14"]).abs() / (df["plus_di_14"] + df["minus_di_14"]).replace(0, np.nan)
    df["adx_14"] = dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()

    hh = h.rolling(14, min_periods=14).max()
    ll = l.rolling(14, min_periods=14).min()
    df["williams_r_14"] = -100 * (hh - c) / (hh - ll).replace(0, np.nan)
    df["willr_bull"] = (df["williams_r_14"] > -80) & (df["williams_r_14"].shift(1) <= -80)
    df["willr_bear"] = (df["williams_r_14"] < -20) & (df["williams_r_14"].shift(1) >= -20)

    tp = (h + l + c) / 3
    sma = tp.rolling(20, min_periods=20).mean()
    mad = (tp - sma).abs().rolling(20, min_periods=20).mean()
    df["cci_20"] = (tp - sma) / (0.015 * mad.replace(0, np.nan))
    df["cci_bull"] = (df["cci_20"] > -100) & (df["cci_20"].shift(1) <= -100)
    df["cci_bear"] = (df["cci_20"] < 100) & (df["cci_20"].shift(1) >= 100)

    raw_mf = tp * v
    pos = raw_mf.where(tp > tp.shift(1), 0.0)
    neg = raw_mf.where(tp < tp.shift(1), 0.0)
    pmf = pos.rolling(14, min_periods=14).sum()
    nmf = neg.rolling(14, min_periods=14).sum()
    df["mfi_14"] = 100 - (100 / (1 + pmf / nmf.replace(0, np.nan)))
    df["mfi_bull"] = (df["mfi_14"] > 30) & (df["mfi_14"].shift(1) <= 30)
    df["mfi_bear"] = (df["mfi_14"] < 70) & (df["mfi_14"].shift(1) >= 70)

    ar_n = 25

    def aroon_up(x):
        return 100 * (ar_n - 1 - np.argmax(x[::-1])) / (ar_n - 1) if len(x) == ar_n else np.nan

    def aroon_down(x):
        return 100 * (ar_n - 1 - np.argmin(x[::-1])) / (ar_n - 1) if len(x) == ar_n else np.nan

    df["aroon_up_25"] = h.rolling(ar_n, min_periods=ar_n).apply(aroon_up, raw=True)
    df["aroon_down_25"] = l.rolling(ar_n, min_periods=ar_n).apply(aroon_down, raw=True)
    return df


def backtest(df: pd.DataFrame, signal: pd.Series, direction: str, start_i: int, end_i: int,
             tp: float = 0.01, sl: float = 0.005, max_hold: int = 24, cost_side: float = 0.0015) -> pd.DataFrame:
    sig = signal.fillna(False).to_numpy()
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    idx = df.index
    trades = []
    i = max(1, start_i)
    while i < end_i - 1:
        if not sig[i - 1]:
            i += 1
            continue
        entry_i = i
        entry = o[entry_i]
        if not np.isfinite(entry) or entry <= 0:
            i += 1
            continue
        exit_i = min(entry_i + max_hold, end_i - 1)
        exit_price = c[exit_i]
        reason = "timeout"
        for j in range(entry_i, min(entry_i + max_hold + 1, end_i)):
            if direction == "long":
                tp_price = entry * (1 + tp)
                sl_price = entry * (1 - sl)
                hit_sl = l[j] <= sl_price
                hit_tp = h[j] >= tp_price
                if hit_sl:
                    exit_i, exit_price, reason = j, sl_price, "sl"
                    break
                if hit_tp:
                    exit_i, exit_price, reason = j, tp_price, "tp"
                    break
            else:
                tp_price = entry * (1 - tp)
                sl_price = entry * (1 + sl)
                hit_sl = h[j] >= sl_price
                hit_tp = l[j] <= tp_price
                if hit_sl:
                    exit_i, exit_price, reason = j, sl_price, "sl"
                    break
                if hit_tp:
                    exit_i, exit_price, reason = j, tp_price, "tp"
                    break
        gross = (exit_price - entry) / entry if direction == "long" else (entry - exit_price) / entry
        trades.append({
            "entry_i": entry_i,
            "exit_i": exit_i,
            "entry_time": str(idx[entry_i]),
            "exit_time": str(idx[exit_i]),
            "return": gross - (2 * cost_side),
            "reason": reason,
        })
        i = exit_i + 1
    return pd.DataFrame(trades)


def metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "trades": 0,
            "win_rate": 0,
            "return_pct": 0,
            "pf": 0,
            "sharpe": 0,
            "maxdd_pct": 0,
            "avg_ret_pct": 0,
            "reliable": False,
        }
    r = trades["return"].astype(float)
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    wins = r[r > 0].sum()
    losses = -r[r < 0].sum()
    return {
        "trades": int(len(r)),
        "win_rate": round(float((r > 0).mean() * 100), 2),
        "return_pct": round(float((eq.iloc[-1] - 1) * 100), 2),
        "pf": round(float(wins / losses), 3) if losses > 0 else (999.0 if wins > 0 else 0),
        "sharpe": round(float(r.mean() / r.std() * math.sqrt(252 * 75)), 3) if r.std() and len(r) > 1 else 0,
        "maxdd_pct": round(float(dd.min() * 100), 2),
        "avg_ret_pct": round(float(r.mean() * 100), 4),
        "reliable": bool(len(r) >= MIN_SPLIT_TRADES),
    }


def fail_reasons(full: dict, val: dict, hold: dict) -> list[str]:
    reasons = []
    if full["trades"] < MIN_FULL_TRADES:
        reasons.append(f"full trades {full['trades']} < {MIN_FULL_TRADES}")
    if val["trades"] < MIN_SPLIT_TRADES:
        reasons.append(f"validation trades {val['trades']} < {MIN_SPLIT_TRADES}")
    if hold["trades"] < MIN_SPLIT_TRADES:
        reasons.append(f"holdout trades {hold['trades']} < {MIN_SPLIT_TRADES}")
    if full["pf"] < 1.15:
        reasons.append(f"full PF {full['pf']} < 1.15")
    if val["trades"] >= MIN_SPLIT_TRADES and val["pf"] < 1.0:
        reasons.append(f"validation PF {val['pf']} < 1.0")
    if hold["trades"] >= MIN_SPLIT_TRADES and hold["pf"] < 1.0:
        reasons.append(f"holdout PF {hold['pf']} < 1.0")
    if full["maxdd_pct"] <= -25:
        reasons.append(f"full maxDD {full['maxdd_pct']}% <= -25%")
    if val["trades"] >= MIN_SPLIT_TRADES and val["return_pct"] <= -10:
        reasons.append(f"validation return {val['return_pct']}% <= -10%")
    if hold["trades"] >= MIN_SPLIT_TRADES and hold["return_pct"] <= -10:
        reasons.append(f"holdout return {hold['return_pct']}% <= -10%")
    return reasons


def build_candidate_signals(df: pd.DataFrame) -> dict[str, tuple[str, pd.Series]]:
    long_trend = (df["ema_fast_21"] > df["ema_slow_55"]) & (df["close"] > df["ema_fast_21"]) & (df["adx_14"].fillna(0) > 18)
    short_trend = (df["ema_fast_21"] < df["ema_slow_55"]) & (df["close"] < df["ema_fast_21"]) & (df["adx_14"].fillna(0) > 18)
    rsi_ok_long = df["rsi_14"].between(35, 68)
    rsi_ok_short = df["rsi_14"].between(32, 65)
    mfi_long = df["mfi_bull"] | (df["mfi_14"] > 50)
    mfi_short = df["mfi_bear"] | (df["mfi_14"] < 50)
    aroon_long = df["aroon_up_25"] > df["aroon_down_25"]
    aroon_short = df["aroon_down_25"] > df["aroon_up_25"]
    candidates = {
        "L_trend_macd_rsi_mfi": ("long", long_trend & df["macd_bull"] & rsi_ok_long & mfi_long),
        "L_trend_macd_aroon": ("long", long_trend & df["macd_bull"] & aroon_long),
        "L_trend_pullback_willr": ("long", long_trend & df["willr_bull"] & mfi_long),
        "L_trend_pullback_cci": ("long", long_trend & df["cci_bull"] & mfi_long),
        "L_trend_dd_recovery": ("long", long_trend & df["drawdown_recovery"] & mfi_long),
        "L_strict_long_run": ("long", df["long_run_bull"] & (df["adx_14"] > 20)),
        "S_trend_macd_rsi_mfi": ("short", short_trend & df["macd_bear"] & rsi_ok_short & mfi_short),
        "S_trend_macd_aroon": ("short", short_trend & df["macd_bear"] & aroon_short),
        "S_trend_pullback_willr": ("short", short_trend & df["willr_bear"] & mfi_short),
        "S_trend_pullback_cci": ("short", short_trend & df["cci_bear"] & mfi_short),
        "S_strict_short_run": ("short", df["short_run_bear"] & (df["adx_14"] > 20)),
    }
    return candidates


def evaluate_candidates(df: pd.DataFrame, candidates: dict[str, tuple[str, pd.Series]]) -> tuple[pd.DataFrame, dict]:
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    rows = []
    details = {}
    for name, (direction, signal) in candidates.items():
        full = backtest(df, signal, direction, 0, n)
        train = backtest(df, signal, direction, 0, train_end)
        val = backtest(df, signal, direction, train_end, val_end)
        hold = backtest(df, signal, direction, val_end, n)
        mf, mt, mv, mh = metrics(full), metrics(train), metrics(val), metrics(hold)
        reasons = fail_reasons(mf, mv, mh)
        passed = (
            mf["trades"] >= MIN_FULL_TRADES and mv["trades"] >= MIN_SPLIT_TRADES and mh["trades"] >= MIN_SPLIT_TRADES
            and mf["pf"] >= 1.15 and mv["pf"] >= 1.0 and mh["pf"] >= 1.0
            and mf["maxdd_pct"] > -25 and mv["return_pct"] > -10 and mh["return_pct"] > -10
        )
        rows.append({
            "strategy": name,
            "direction": direction,
            "passed": passed,
            "display_verdict": "PAPER_TEST_CANDIDATE" if passed else "REJECT",
            "fail_reasons": "; ".join(reasons) if reasons else "",
            "warning": "Do not trust split metrics with less than 20 trades." if (mv["trades"] < MIN_SPLIT_TRADES or mh["trades"] < MIN_SPLIT_TRADES) else "",
            **{f"full_{k}": v for k, v in mf.items()},
            **{f"train_{k}": v for k, v in mt.items()},
            **{f"val_{k}": v for k, v in mv.items()},
            **{f"hold_{k}": v for k, v in mh.items()},
        })
        details[name] = full.head(50).to_dict(orient="records")
    results = pd.DataFrame(rows).sort_values(["passed", "full_pf", "full_return_pct"], ascending=[False, False, False])
    return results, details


def verified_trade_snapshot(symbol: str = "INFY", interval: str = "5m") -> dict:
    """Return strict trader-facing signal state. TRADE is allowed only after gates pass."""
    if symbol.upper() != "INFY" or interval.lower() not in {"5m", "5min"}:
        return {
            "symbol": symbol.upper(),
            "tf": interval,
            "status": "NO_VERIFIED_DATA",
            "verdict": "NO TRADE",
            "reason": "Only INFY 5m has local 10-year verified data right now.",
            "ready_to_trade": False,
        }
    df = add_indicators(load_infy_5m())
    candidates = build_candidate_signals(df)
    results, _details = evaluate_candidates(df, candidates)
    passed = results[results["passed"] == True]  # noqa: E712
    latest_i = len(df) - 1
    latest_bar = df.iloc[-1]
    active = []
    for name, (direction, signal) in candidates.items():
        confirm_i = latest_i - 1
        if confirm_i >= 0 and bool(signal.iloc[confirm_i]):
            active.append({
                "strategy": name,
                "direction": direction,
                "confirm_time": str(df.index[confirm_i]),
                "entry_time": str(df.index[latest_i]),
                "entry_price": round(float(latest_bar["open"]), 4),
                "sl_pct": 0.5,
                "tp_pct": 1.0,
                "sl_price": round(float(latest_bar["open"]) * (0.995 if direction == "long" else 1.005), 4),
                "tp_price": round(float(latest_bar["open"]) * (1.01 if direction == "long" else 0.99), 4),
            })
    best = results.iloc[0].to_dict()
    ready_active = [a for a in active if a["strategy"] in set(passed["strategy"])]
    return {
        "symbol": "INFY",
        "tf": "5m_from_1m",
        "data_rows": int(len(df)),
        "data_start": str(df.index[0]),
        "data_end": str(df.index[-1]),
        "last_bar": {
            "time": str(df.index[-1]),
            "open": round(float(latest_bar["open"]), 4),
            "high": round(float(latest_bar["high"]), 4),
            "low": round(float(latest_bar["low"]), 4),
            "close": round(float(latest_bar["close"]), 4),
            "volume": int(latest_bar["volume"]),
        },
        "status": "VERIFIED",
        "verdict": "TRADE" if ready_active else "NO TRADE",
        "ready_to_trade": bool(ready_active),
        "active_signals": ready_active,
        "raw_active_signals": active,
        "strategies_tested": int(len(results)),
        "passed_strategies": int(results["passed"].sum()),
        "best_strategy": best,
        "proof": {
            "rule": "next candle execution only; TP 1%; SL 0.5%; cost 0.15% per side; 70/15/15 split",
            "report": str((OUT_DIR / "INFY_5m_10_indicator_production_readiness.md").resolve()),
            "csv": str((OUT_DIR / "INFY_5m_10_indicator_strategy_readiness.csv").resolve()),
        },
    }


def main() -> None:
    df = add_indicators(load_infy_5m())
    candidates = build_candidate_signals(df)
    results, details = evaluate_candidates(df, candidates)
    n = len(df)

    out_csv = OUT_DIR / "INFY_5m_10_indicator_strategy_readiness.csv"
    out_md = OUT_DIR / "INFY_5m_10_indicator_production_readiness.md"
    out_json = OUT_DIR / "INFY_5m_10_indicator_production_readiness.json"
    results.to_csv(out_csv, index=False)
    summary = {
        "symbol": "INFY",
        "tf": "5m_from_1m",
        "rows": n,
        "start": str(df.index[0]),
        "end": str(df.index[-1]),
        "strategies_tested": int(len(results)),
        "passed": int(results["passed"].sum()),
        "best": results.iloc[0].to_dict(),
    }
    out_json.write_text(json.dumps({"summary": summary, "strategies": results.to_dict(orient="records"), "sample_trades": details}, indent=2, default=str), encoding="utf-8")
    lines = [
        "# INFY 10-Year 5m 10-Indicator Production Readiness",
        "",
        f"Rows: {n}",
        f"Range: {summary['start']} to {summary['end']}",
        "",
        "## Verdict",
        f"{'CONDITIONAL PAPER-TEST READY' if summary['passed'] else 'NOT LIVE READY'}: {summary['passed']} / {len(results)} candidates passed gates.",
        "",
        "No green result is allowed unless full, validation, and holdout gates pass.",
        "Any split with less than 20 trades is marked unreliable.",
        "",
        "## Results",
    ]
    for _, r in results.iterrows():
        lines.append(
            f"- {r.strategy}: verdict={r.display_verdict} pass={r.passed} trades={r.full_trades} "
            f"ret={r.full_return_pct}% pf={r.full_pf} sharpe={r.full_sharpe} maxDD={r.full_maxdd_pct}% "
            f"valTrades={r.val_trades} holdTrades={r.hold_trades} fail=`{r.fail_reasons}`"
        )
    lines += [
        "",
        "## Gates",
        "- full trades >=100",
        "- validation trades >=20",
        "- holdout trades >=20",
        "- full PF >=1.15",
        "- validation PF >=1.0",
        "- holdout PF >=1.0",
        "- full maxDD > -25%",
        "- val/hold return > -10%",
        "- next candle execution",
        "- 0.15% cost per side",
        "",
        f"CSV: `{out_csv.resolve()}`",
        f"JSON: `{out_json.resolve()}`",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    print(f"csv={out_csv.resolve()}")
    print(f"md={out_md.resolve()}")


if __name__ == "__main__":
    main()
