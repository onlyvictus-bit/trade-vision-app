from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd


VERSION = "tradevision-multitimeframe-research.v1"
TIMEFRAMES = {
    "1m": {"rule": None, "horizon": 15, "lookback": 30, "level_window": 30},
    "3m": {"rule": "3min", "horizon": 10, "lookback": 25, "level_window": 25},
    "5m": {"rule": "5min", "horizon": 8, "lookback": 24, "level_window": 24},
    "15m": {"rule": "15min", "horizon": 6, "lookback": 20, "level_window": 20},
    "1H": {"rule": "60min", "horizon": 4, "lookback": 20, "level_window": 20},
    "daily": {"rule": "1D", "horizon": 5, "lookback": 20, "level_window": 20},
    "weekly": {"rule": "W-FRI", "horizon": 4, "lookback": 16, "level_window": 16},
}
FEATURE_COLUMNS = [
    "return_1",
    "return_3",
    "ema_spread_atr",
    "ema9_slope_atr",
    "rsi14_scaled",
    "adx14_scaled",
    "macd_atr",
    "volume_z20_scaled",
    "body_pct_scaled",
    "upper_wick_scaled",
    "lower_wick_scaled",
    "clv_scaled",
    "range_atr_scaled",
    "bb_width_atr",
    "distance_high_atr",
    "distance_low_atr",
]


@dataclass(frozen=True)
class Plan:
    action: str
    preferred_side: str
    trigger: str
    entry_low: float
    entry_high: float
    stop_loss: float
    invalidation: str
    target_1r: float
    target_2r: float
    target_3r: float
    risk_per_share: float
    risk_reward_to_3r: float


def main() -> int:
    parser = argparse.ArgumentParser(description="Build point-in-time multi-timeframe research plans and historical analogs.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--symbol", default="RELIANCE")
    parser.add_argument("--as-of", default=None, help="Optional ISO timestamp/date no later than the source data.")
    parser.add_argument("--top-analogs", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("data/validation/RELIANCE_multitimeframe_research.json"))
    parser.add_argument("--markdown", type=Path, default=Path("docs/test-reports/RELIANCE_MULTITIMEFRAME_RESEARCH.md"))
    args = parser.parse_args()

    started = perf_counter()
    minute = load_source(args.csv_path)
    if args.as_of:
        cutoff = pd.Timestamp(args.as_of, tz="Asia/Kolkata") if "T" in args.as_of else pd.Timestamp(f"{args.as_of} 23:59:59", tz="Asia/Kolkata")
        minute = minute[minute.index <= cutoff]
    if minute.empty:
        raise ValueError("No source candles are available at the requested as-of time.")

    frames = {name: enrich(aggregate(minute, name, config["rule"])) for name, config in TIMEFRAMES.items()}
    reports: dict[str, dict[str, object]] = {}
    for name, config in TIMEFRAMES.items():
        frame = frames[name]
        reports[name] = analyze_timeframe(
            name=name,
            frame=frame,
            horizon=int(config["horizon"]),
            lookback=int(config["lookback"]),
            level_window=int(config["level_window"]),
            top_analogs=args.top_analogs,
        )

    apply_higher_timeframe_veto(reports)
    output = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(args.csv_path.resolve()),
        "symbol": args.symbol.upper(),
        "source_last_timestamp": minute.index[-1].isoformat(),
        "data_freshness_warning": (
            f"Source ends {minute.index[-1].date().isoformat()}; this is a historical point-in-time research report, "
            "not a current June 2026 market recommendation."
        ),
        "methodology": {
            "timeframes": list(TIMEFRAMES),
            "features": FEATURE_COLUMNS,
            "similarity": "robust-scaled Euclidean distance converted to 0-100 similarity",
            "analog_outcome": "future bars strictly after each historical candidate timestamp",
            "entry_policy": "conditional break/retest zone; no market order",
            "stop_policy": "2 ATR beyond the structural breakout/breakdown reference",
            "target_policy": "1R, 2R and 3R from the conditional entry midpoint",
            "minimum_analog_count": 30,
            "live_execution": False,
        },
        "timeframes": reports,
        "consensus": build_consensus(reports),
        "safety": {
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "note": "Levels are historical research outputs requiring fresh-market confirmation and human review.",
        },
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, default=json_default), encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(output), encoding="utf-8")
    print(json.dumps({"json": str(args.output.resolve()), "markdown": str(args.markdown.resolve()), "consensus": output["consensus"], "elapsed_seconds": output["elapsed_seconds"]}, indent=2))
    return 0


def load_source(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        usecols=["date", "time", "open", "high", "low", "close", "volume"],
        dtype={"date": "string", "time": "string", "open": "float64", "high": "float64", "low": "float64", "close": "float64", "volume": "float64"},
    )
    index = pd.to_datetime(df["date"] + " " + df["time"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    valid = index.notna()
    df = df.loc[valid, ["open", "high", "low", "close", "volume"]].copy()
    df.index = pd.DatetimeIndex(index[valid]).tz_localize("Asia/Kolkata")
    return df.sort_index()


def aggregate(minute: pd.DataFrame, name: str, rule: str | None) -> pd.DataFrame:
    if rule is None:
        return minute.copy()
    if name in {"3m", "5m", "15m", "1H"}:
        minutes = int(rule.replace("min", ""))
        session_minute = (minute.index.hour * 60 + minute.index.minute) - 555
        bucket = np.floor_divide(session_minute, minutes)
        keys = [minute.index.normalize(), bucket]
        grouped = minute.groupby(keys, sort=True)
        result = grouped.agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        )
        result.index = pd.DatetimeIndex(grouped.apply(lambda group: group.index[-1], include_groups=False).to_numpy())
        return result.sort_index()
    if name == "daily":
        grouped = minute.groupby(minute.index.normalize(), sort=True)
    else:
        grouped = minute.groupby(minute.index.tz_localize(None).to_period("W-FRI"), sort=True)
    result = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    result.index = pd.DatetimeIndex(grouped.apply(lambda group: group.index[-1], include_groups=False).to_numpy())
    return result.sort_index()


def enrich(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    previous_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["rsi14"] = rsi(df["close"], 14)
    df["adx14"] = adx(df, 14)
    vol_mean = df["volume"].rolling(20).mean()
    vol_std = df["volume"].rolling(20).std(ddof=0).replace(0, np.nan)
    df["volume_z20"] = ((df["volume"] - vol_mean) / vol_std).fillna(0)
    middle = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std(ddof=0)
    df["bb_width"] = (4 * std) / middle.replace(0, np.nan)
    candle_range = (df["high"] - df["low"]).replace(0, np.nan)
    df["body_pct"] = (df["close"] - df["open"]).abs() / candle_range
    df["upper_wick_pct"] = (df["high"] - df[["open", "close"]].max(axis=1)) / candle_range
    df["lower_wick_pct"] = (df[["open", "close"]].min(axis=1) - df["low"]) / candle_range
    df["clv"] = (df["close"] - df["low"]) / candle_range
    df["inside_bar"] = (df["high"] <= df["high"].shift(1)) & (df["low"] >= df["low"].shift(1))
    df["outside_bar"] = (df["high"] >= df["high"].shift(1)) & (df["low"] <= df["low"].shift(1))
    df["prior_high20"] = df["high"].shift(1).rolling(20).max()
    df["prior_low20"] = df["low"].shift(1).rolling(20).min()
    df["return_1"] = df["close"].pct_change()
    df["return_3"] = df["close"].pct_change(3)
    atr = df["atr14"].replace(0, np.nan)
    df["ema_spread_atr"] = (df["ema9"] - df["ema21"]) / atr
    df["ema9_slope_atr"] = df["ema9"].diff(3) / atr
    df["rsi14_scaled"] = (df["rsi14"] - 50) / 50
    df["adx14_scaled"] = df["adx14"] / 100
    df["macd_atr"] = df["macd"] / atr
    df["volume_z20_scaled"] = df["volume_z20"] / 3
    df["body_pct_scaled"] = df["body_pct"] * np.sign(df["close"] - df["open"])
    df["upper_wick_scaled"] = df["upper_wick_pct"]
    df["lower_wick_scaled"] = df["lower_wick_pct"]
    df["clv_scaled"] = (df["clv"] - 0.5) * 2
    df["range_atr_scaled"] = candle_range / atr
    df["bb_width_atr"] = df["bb_width"] * df["close"] / atr
    df["distance_high_atr"] = (df["close"] - df["prior_high20"]) / atr
    df["distance_low_atr"] = (df["close"] - df["prior_low20"]) / atr
    return df.replace([np.inf, -np.inf], np.nan)


def analyze_timeframe(
    *,
    name: str,
    frame: pd.DataFrame,
    horizon: int,
    lookback: int,
    level_window: int,
    top_analogs: int,
) -> dict[str, object]:
    usable = frame.dropna(subset=["atr14", "rsi14", "adx14", "ema9", "ema21", *FEATURE_COLUMNS]).copy()
    if len(usable) < 100:
        raise ValueError(f"{name}: insufficient enriched history ({len(usable)} bars)")
    current = usable.iloc[-1]
    current_time = usable.index[-1]
    recent = usable.iloc[-lookback:]
    support = float(recent["low"].min())
    resistance = float(recent["high"].max())
    patterns = detect_patterns(usable, current)
    score, raw_action, reasons = directional_score(current, patterns)
    analysis_direction = raw_action if raw_action in {"LONG", "SHORT"} else "LONG" if score > 0 else "SHORT"
    analog_pool = find_analogs(usable, current_time, horizon, max(30, top_analogs), analysis_direction, name)
    analogs = analog_pool[:top_analogs]
    analog_summary = summarize_analogs(analog_pool, analysis_direction, displayed_count=len(analogs))
    action = decide_action(raw_action, score, current, analog_summary, patterns)
    plan = build_plan(action, analysis_direction, current, support, resistance)
    return {
        "timeframe": name,
        "as_of": current_time.isoformat(),
        "bar_count": int(len(frame)),
        "close": round(float(current["close"]), 4),
        "atr14": round(float(current["atr14"]), 4),
        "rsi14": round(float(current["rsi14"]), 2),
        "adx14": round(float(current["adx14"]), 2),
        "ema9": round(float(current["ema9"]), 4),
        "ema21": round(float(current["ema21"]), 4),
        "macd": round(float(current["macd"]), 4),
        "volume_z20": round(float(current["volume_z20"]), 3),
        "support": round(support, 4),
        "resistance": round(resistance, 4),
        "patterns": patterns,
        "directional_score": round(score, 4),
        "raw_action": raw_action,
        "analysis_direction": analysis_direction,
        "recommendation": action,
        "recommendation_reasons": reasons,
        "plan": plan.__dict__,
        "analog_summary": analog_summary,
        "similar_patterns": analogs,
        "minimum_evidence_pass": len(analog_pool) >= 30,
        "higher_timeframe_veto": False,
        "trade_allowed": False,
        "live_trading_blocked": True,
    }


def detect_patterns(df: pd.DataFrame, row: pd.Series) -> list[str]:
    patterns: list[str] = []
    if row["ema9"] > row["ema21"] and row["ema9_slope_atr"] > 0:
        patterns.append("bullish_ema_structure")
    elif row["ema9"] < row["ema21"] and row["ema9_slope_atr"] < 0:
        patterns.append("bearish_ema_structure")
    if row["adx14"] >= 30:
        patterns.append("strong_trend_strength")
    elif row["adx14"] < 20:
        patterns.append("weak_or_range_strength")
    if row["close"] > row["prior_high20"]:
        patterns.append("rolling_20_bar_breakout")
    if row["close"] < row["prior_low20"]:
        patterns.append("rolling_20_bar_breakdown")
    if bool(row["inside_bar"]):
        patterns.append("inside_bar_compression")
    if bool(row["outside_bar"]):
        patterns.append("outside_bar_expansion")
    if row["upper_wick_pct"] >= 0.45:
        patterns.append("upper_wick_rejection")
    if row["lower_wick_pct"] >= 0.45:
        patterns.append("lower_wick_rejection")
    width_history = df["bb_width"].dropna().iloc[-252:]
    if len(width_history) >= 20 and row["bb_width"] <= width_history.quantile(0.2):
        patterns.append("volatility_compression")
    if row["range_atr_scaled"] >= 1.4:
        patterns.append("range_expansion")
    if row["volume_z20"] >= 1 and row["body_pct"] <= 0.3:
        patterns.append("absorption_proxy")
    if row["rsi14"] >= 65:
        patterns.append("bullish_momentum")
    elif row["rsi14"] <= 35:
        patterns.append("bearish_momentum")
    else:
        patterns.append("neutral_momentum")
    return patterns


def directional_score(row: pd.Series, patterns: list[str]) -> tuple[float, str, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if row["ema9"] > row["ema21"]:
        score += 0.22
        reasons.append("EMA9 is above EMA21.")
    else:
        score -= 0.22
        reasons.append("EMA9 is below EMA21.")
    slope = float(np.clip(row["ema9_slope_atr"], -1, 1))
    score += 0.18 * slope
    reasons.append(f"EMA9 slope contributes {slope:+.2f} ATR-normalized direction.")
    momentum = float(np.clip((row["rsi14"] - 50) / 20, -1, 1))
    score += 0.18 * momentum
    reasons.append(f"RSI14 is {row['rsi14']:.1f}.")
    macd = float(np.clip(row["macd_atr"], -1, 1))
    score += 0.14 * macd
    if "rolling_20_bar_breakout" in patterns:
        score += 0.18
    if "rolling_20_bar_breakdown" in patterns:
        score -= 0.18
    if "upper_wick_rejection" in patterns:
        score -= 0.08
    if "lower_wick_rejection" in patterns:
        score += 0.08
    if row["adx14"] < 20:
        score *= 0.7
        reasons.append("ADX below 20 reduces directional confidence.")
    raw = "LONG" if score >= 0.22 else "SHORT" if score <= -0.22 else "WAIT"
    return float(np.clip(score, -1, 1)), raw, reasons


def find_analogs(
    df: pd.DataFrame,
    current_time: pd.Timestamp,
    horizon: int,
    top_n: int,
    direction: str,
    timeframe: str,
) -> list[dict[str, object]]:
    candidates = df.iloc[:-horizon].dropna(subset=FEATURE_COLUMNS).copy()
    if timeframe in {"1m", "3m", "5m", "15m", "1H"}:
        current_minutes = current_time.hour * 60 + current_time.minute
        candidate_minutes = candidates.index.hour * 60 + candidates.index.minute
        tolerance = 15 if timeframe != "1H" else 60
        candidates = candidates[np.abs(candidate_minutes - current_minutes) <= tolerance]
    if len(candidates) < top_n:
        return []
    sample = candidates[FEATURE_COLUMNS].tail(250_000).apply(pd.to_numeric, errors="coerce")
    center = sample.median()
    scale = (sample.quantile(0.75) - sample.quantile(0.25)).replace(0, 1).fillna(1)
    current_features = pd.to_numeric(df.loc[current_time, FEATURE_COLUMNS], errors="coerce")
    current_vector = ((current_features - center) / scale).clip(-8, 8).fillna(0).to_numpy(float)
    matrix = ((sample - center) / scale).clip(-8, 8).fillna(0).to_numpy(float)
    distances = np.sqrt(np.mean((matrix - current_vector) ** 2, axis=1))
    order = np.argsort(distances)
    chosen: list[int] = []
    used_dates: set[str] = set()
    for idx in order:
        timestamp = sample.index[idx]
        date_key = timestamp.date().isoformat()
        if date_key in used_dates:
            continue
        used_dates.add(date_key)
        chosen.append(int(idx))
        if len(chosen) >= top_n:
            break
    results: list[dict[str, object]] = []
    full_positions = {timestamp: position for position, timestamp in enumerate(df.index)}
    for idx in chosen:
        timestamp = sample.index[idx]
        position = full_positions[timestamp]
        future = df.iloc[position + 1 : position + 1 + horizon]
        base_close = float(df.iloc[position]["close"])
        atr_value = max(float(df.iloc[position]["atr14"]), 1e-9)
        future_return = ((float(future.iloc[-1]["close"]) / base_close) - 1) * 100 if not future.empty else 0.0
        mfe_long = max(0.0, (float(future["high"].max()) - base_close) / atr_value) if not future.empty else 0.0
        mae_long = max(0.0, (base_close - float(future["low"].min())) / atr_value) if not future.empty else 0.0
        if direction == "SHORT":
            favorable_mfe = mae_long
            adverse_mae = mfe_long
        else:
            favorable_mfe = mfe_long
            adverse_mae = mae_long
        favorable = future_return > 0 if direction == "LONG" else future_return < 0 if direction == "SHORT" else abs(future_return) < 0.5
        results.append(
            {
                "date": timestamp.date().isoformat(),
                "timestamp": timestamp.isoformat(),
                "similarity_pct": round(100 / (1 + float(distances[idx])), 2),
                "close_then": round(base_close, 4),
                "rsi14_then": round(float(df.iloc[position]["rsi14"]), 2),
                "adx14_then": round(float(df.iloc[position]["adx14"]), 2),
                "future_horizon_bars": horizon,
                "future_return_pct": round(future_return, 4),
                "future_mfe_atr_long": round(mfe_long, 4),
                "future_mae_atr_long": round(mae_long, 4),
                "favorable_mfe_atr": round(favorable_mfe, 4),
                "adverse_mae_atr": round(adverse_mae, 4),
                "direction_supported": bool(favorable),
            }
        )
    return results


def summarize_analogs(analogs: list[dict[str, object]], direction: str, *, displayed_count: int) -> dict[str, object]:
    if not analogs:
        return {"match_count": 0, "direction_support_pct": 0.0, "average_future_return_pct": 0.0, "evidence": "LOW"}
    support = sum(bool(item["direction_supported"]) for item in analogs) / len(analogs) * 100
    average = float(np.mean([float(item["future_return_pct"]) for item in analogs]))
    return {
        "match_count": len(analogs),
        "displayed_match_count": displayed_count,
        "direction": direction,
        "direction_support_pct": round(support, 2),
        "average_future_return_pct": round(average, 4),
        "evidence": "LOW" if len(analogs) < 30 else "MEDIUM",
        "warning": "Top analog display is descriptive; calibrated probability requires at least 30 non-overlapping matches.",
    }


def decide_action(raw: str, score: float, row: pd.Series, analog: dict[str, object], patterns: list[str]) -> str:
    if raw == "WAIT":
        return "WAIT"
    if row["adx14"] < 20 and "rolling_20_bar_breakout" not in patterns and "rolling_20_bar_breakdown" not in patterns:
        return "WAIT"
    if float(analog.get("direction_support_pct", 0)) < 60:
        return "WAIT"
    if abs(score) < 0.3:
        return "WAIT"
    return raw


def build_plan(action: str, raw_action: str, row: pd.Series, support: float, resistance: float) -> Plan:
    atr_value = max(float(row["atr14"]), 0.01)
    preferred_side = action if action in {"LONG", "SHORT"} else raw_action if raw_action in {"LONG", "SHORT"} else "LONG"
    if preferred_side == "SHORT":
        reference = min(float(row["low"]), support)
        entry_mid = reference - 0.05 * atr_value
        entry_low, entry_high = entry_mid - 0.05 * atr_value, entry_mid + 0.05 * atr_value
        stop = reference + 2 * atr_value
        risk = max(stop - entry_mid, 0.01)
        targets = [max(0.01, entry_mid - risk * multiple) for multiple in (1, 2, 3)]
        trigger = (
            "WAIT: conditional short plan activates only after a closed candle below support and a non-failing retest."
            if action == "WAIT"
            else "Closed candle below support/breakdown reference, followed by non-failing retest."
        )
        return Plan(action, preferred_side, trigger, round(entry_low, 4), round(entry_high, 4), round(stop, 4), "Close back above breakdown level or structural resistance.", *[round(x, 4) for x in targets], round(risk, 4), 3.0)
    reference = max(float(row["high"]), resistance)
    entry_mid = reference + 0.05 * atr_value
    entry_low, entry_high = entry_mid - 0.05 * atr_value, entry_mid + 0.05 * atr_value
    stop = max(0.01, reference - 2 * atr_value)
    risk = max(entry_mid - stop, 0.01)
    targets = [entry_mid + risk * multiple for multiple in (1, 2, 3)]
    trigger = (
        "WAIT: conditional long plan activates only after a closed candle above resistance and a valid retest."
        if action == "WAIT"
        else "Closed candle above resistance/breakout reference, followed by holding retest."
    )
    return Plan(action, preferred_side, trigger, round(entry_low, 4), round(entry_high, 4), round(stop, 4), "Close below breakout level or structural support.", *[round(x, 4) for x in targets], round(risk, 4), 3.0)


def apply_higher_timeframe_veto(reports: dict[str, dict[str, object]]) -> None:
    higher = [reports["weekly"]["recommendation"], reports["daily"]["recommendation"], reports["1H"]["recommendation"]]
    bearish = sum(item == "SHORT" for item in higher)
    bullish = sum(item == "LONG" for item in higher)
    for name in ["1m", "3m", "5m", "15m"]:
        report = reports[name]
        action = report["recommendation"]
        veto = (action == "LONG" and bearish >= 2) or (action == "SHORT" and bullish >= 2)
        if veto:
            report["higher_timeframe_veto"] = True
            report["recommendation"] = "WAIT"
            report["recommendation_reasons"].append("Higher-timeframe majority vetoed the lower-timeframe direction.")
            report["plan"] = build_plan("WAIT", str(report["analysis_direction"]), pd.Series({
                "atr14": report["atr14"],
                "close": report["close"],
                "high": report["resistance"],
                "low": report["support"],
            }), float(report["support"]), float(report["resistance"])).__dict__


def build_consensus(reports: dict[str, dict[str, object]]) -> dict[str, object]:
    actions = {name: str(report["recommendation"]) for name, report in reports.items()}
    long_count = sum(action == "LONG" for action in actions.values())
    short_count = sum(action == "SHORT" for action in actions.values())
    wait_count = sum(action == "WAIT" for action in actions.values())
    higher = [actions["1H"], actions["daily"], actions["weekly"]]
    if higher.count("LONG") >= 2 and short_count == 0:
        consensus = "LONG_BIAS_RESEARCH_ONLY"
    elif higher.count("SHORT") >= 2 and long_count == 0:
        consensus = "SHORT_BIAS_RESEARCH_ONLY"
    else:
        consensus = "NO_TRADE_MIXED_OR_LOW_EVIDENCE"
    return {
        "result": consensus,
        "actions": actions,
        "long_count": long_count,
        "short_count": short_count,
        "wait_count": wait_count,
        "reason": "Consensus requires higher-timeframe agreement and no opposing timeframe candidate.",
        "trade_allowed": False,
    }


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def adx(df: pd.DataFrame, period: int) -> pd.Series:
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    previous_close = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]), (df["high"] - previous_close).abs(), (df["low"] - previous_close).abs()], axis=1).max(axis=1)
    atr_value = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr_value
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr_value
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().fillna(0)


def render_markdown(output: dict[str, object]) -> str:
    lines = [
        f"# {output['symbol']} Multi-Timeframe Research Report",
        "",
        f"**Point-in-time:** {output['source_last_timestamp']}",
        "",
        f"> {output['data_freshness_warning']}",
        "",
        "## Decision Matrix",
        "",
        "| Timeframe | Pattern / State | Action | Entry Zone | SL | T1 | T2 | T3 | Analog Support |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, report in output["timeframes"].items():
        plan = report["plan"]
        patterns = ", ".join(report["patterns"][:3])
        analog = report["analog_summary"]
        lines.append(
            f"| {name} | {patterns} | **{report['recommendation']}** | "
            f"{plan['entry_low']:.2f}-{plan['entry_high']:.2f} | {plan['stop_loss']:.2f} | "
            f"{plan['target_1r']:.2f} | {plan['target_2r']:.2f} | {plan['target_3r']:.2f} | "
            f"{analog['direction_support_pct']:.0f}% ({analog['match_count']} sampled) |"
        )
    lines.extend(["", "## Historical Analogs", ""])
    for name, report in output["timeframes"].items():
        lines.extend([f"### {name}", "", f"- Current action: **{report['recommendation']}**", f"- Trigger: {report['plan']['trigger']}", f"- Invalidation: {report['plan']['invalidation']}", ""])
        for analog in report["similar_patterns"]:
            lines.append(
                f"- `{analog['timestamp']}`: similarity {analog['similarity_pct']}%, "
                f"next {analog['future_horizon_bars']} bars return {analog['future_return_pct']}%, "
                f"favorable MFE {analog['favorable_mfe_atr']} ATR, adverse MAE {analog['adverse_mae_atr']} ATR."
            )
        lines.append("")
    consensus = output["consensus"]
    lines.extend(
        [
            "## Consensus",
            "",
            f"- Result: **{consensus['result']}**",
            f"- Actions: `{json.dumps(consensus['actions'], sort_keys=True)}`",
            "- Trade permission remains false. Use the dates to inspect charts; do not treat five displayed analogs as a calibrated probability.",
        ]
    )
    return "\n".join(lines) + "\n"


def json_default(value: object) -> object:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value)!r}")


if __name__ == "__main__":
    raise SystemExit(main())
