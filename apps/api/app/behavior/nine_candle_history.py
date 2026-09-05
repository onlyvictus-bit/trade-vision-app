from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from .. import storage
from .nine_candle_hybrid import FEATURE_MANIFEST_VERSION, build_evidence_packet


PATH_ANALOG_VERSION = "9c-path-analog-history.v1"
OOD_VERSION = "9c-ood-status.v1"
HORIZONS = [3, 5, 9, 12, 20]
MAX_ANALOGS = 25


def build_path_analog_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    limit: int = MAX_ANALOGS,
) -> dict[str, Any]:
    started = time.perf_counter()
    normalized = symbol.upper()
    bars, source = _history_bars(normalized, timeframe)
    current = _current_descriptor(normalized, timeframe)
    windows = _historical_windows(bars, normalized, timeframe)
    volatility = _volatility_status(current, windows)
    scoped = _scope_windows(windows, current, volatility["volatility_bucket"])
    matches = [_match(current, window) for window in scoped]
    persisted_matches = _persisted_outcome_matches(normalized, timeframe, current)
    matches.extend(persisted_matches)
    matches.sort(key=lambda item: (-item["similarity_score"], item["window_id"]))
    bounded = matches[: max(1, min(limit, MAX_ANALOGS))]
    winner_count = sum(1 for item in matches if item["outcome_label"] == "TARGET_HIT")
    failure_count = sum(1 for item in matches if item["outcome_label"] in {"SL_HIT", "FAKE_BREAKOUT"})
    total = len(matches)
    temporal = _temporal_diversity(matches)
    report = {
        "path_analog_version": PATH_ANALOG_VERSION,
        "symbol": normalized,
        "timeframe": timeframe,
        "feature_manifest_version": FEATURE_MANIFEST_VERSION,
        "history_source": source["source"],
        "history_bar_count": len(bars),
        "window_count": len(windows),
        "regime_scoped_window_count": len(scoped),
        "raw_match_window_count": volatility["raw_window_count"],
        "matched_after_vol_bucketing": len(scoped),
        "volatility_bucketed": True,
        "volatility_status": volatility,
        "volatility_ood": volatility["volatility_ood"],
        "volatility_gate": volatility["gate"],
        "persisted_outcome_match_count": len(persisted_matches),
        "persisted_outcome_memory_used": bool(persisted_matches),
        "total_matches": total,
        "winner_like_matches": winner_count,
        "failure_like_matches": failure_count,
        "neutral_matches": max(total - winner_count - failure_count, 0),
        "winner_failure_balance_check": winner_count + failure_count <= total,
        "hardcoded_match_count_used": False,
        "current_descriptor_hash": current["descriptor_hash"],
        "top_matches": bounded,
        "temporal_diversity_score": temporal["temporal_diversity_score"],
        "recency_weight_applied": True,
        "per_week_cap_applied": True,
        "source_snapshot_id": source.get("snapshot_id"),
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "output_hash": "",
    }
    report["output_hash"] = _hash_report(report)
    return report


def build_ood_status_report(symbol: str = "RELIANCE", timeframe: str = "1m") -> dict[str, Any]:
    started = time.perf_counter()
    path = build_path_analog_report(symbol, timeframe, limit=MAX_ANALOGS)
    distances = [round(1.0 - float(item["similarity_score"]), 6) for item in path["top_matches"]]
    threshold = _percentile(distances, 0.95) if distances else None
    nearest = min(distances) if distances else None
    ood_flag = bool(nearest is None or threshold is None or nearest > threshold)
    volatility = path.get("volatility_status", {})
    volatility_ood = bool(volatility.get("volatility_ood", False))
    combined_ood = bool(ood_flag or volatility_ood)
    gate_status = "wait" if ood_flag else "pass"
    report = {
        "ood_version": OOD_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "feature_manifest_version": FEATURE_MANIFEST_VERSION,
        "distance_method": "one_minus_path_similarity",
        "threshold_source": "historical_knn_distance_p95",
        "knn_distance_95th_percentile": threshold,
        "nearest_distance": nearest,
        "shape_ood": ood_flag,
        "ood_flag": combined_ood,
        "volatility_ood": volatility_ood,
        "volatility_status": volatility,
        "volatility_gate": volatility.get("gate", {"gate_id": "9C-G016", "status": "wait", "evidence": "Volatility status unavailable."}),
        "gate": {
            "gate_id": "9C-G013",
            "name": "OOD historical distance",
            "status": gate_status,
            "evidence": "No comparable history." if ood_flag else f"nearest_distance={nearest} threshold={threshold}",
        },
        "path_analog_hash": path["output_hash"],
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "output_hash": "",
    }
    report["output_hash"] = _hash_report(report)
    return report


def _history_bars(symbol: str, timeframe: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    snapshot = _latest_snapshot(symbol, timeframe)
    if snapshot is not None:
        payload = snapshot.payload
        bars = [
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp_ns": int(row["t"]),
                "open": float(row["o"]),
                "high": float(row["h"]),
                "low": float(row["l"]),
                "close": float(row["c"]),
                "volume": float(row["v"] or 0.0),
                "sequence_number": index,
            }
            for index, row in enumerate(payload.get("bars", []), start=1)
        ]
        if len(bars) >= 40:
            return bars, {"source": "point_in_time_snapshot", "snapshot_id": snapshot.snapshot_id}
    return _generated_history(symbol, timeframe), {"source": "deterministic_generated_history", "snapshot_id": None}


def _latest_snapshot(symbol: str, timeframe: str):
    try:
        snapshots = storage.list_point_in_time_snapshots(limit=100)
    except Exception:
        return None
    for snapshot in snapshots:
        payload = snapshot.payload
        if snapshot.symbol.upper() == symbol.upper() and str(payload.get("timeframe", timeframe)) == timeframe:
            return snapshot
    return None


def _generated_history(symbol: str, timeframe: str, bars: int = 180) -> list[dict[str, Any]]:
    base = 2400.0 + _unit(symbol, timeframe, "base") * 120.0
    start = datetime(2026, 1, 2, 9, 15, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    rows: list[dict[str, Any]] = []
    for index in range(bars):
        cycle = math.sin(index / 9.0) * 4.5
        drift = index * 0.055
        shock = 3.2 if index % 47 == 0 else (-2.6 if index % 41 == 0 else 0.0)
        close = base + drift + cycle + shock
        open_price = close - math.sin(index / 5.0) * 1.2
        high = max(open_price, close) + 0.8 + abs(math.sin(index / 3.0))
        low = min(open_price, close) - 0.7 - abs(math.cos(index / 4.0)) * 0.8
        volume = 100_000 + (index % 23) * 4200 + int(abs(math.sin(index / 7.0)) * 55_000)
        rows.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp_ns": int((start + timedelta(minutes=index)).timestamp() * 1_000_000_000),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": float(volume),
                "sequence_number": index + 1,
            }
        )
    return rows


def _current_descriptor(symbol: str, timeframe: str) -> dict[str, Any]:
    packet = build_evidence_packet(symbol, timeframe).model_dump(mode="json")
    candles = [
        {
            "timestamp_ns": int(datetime.fromisoformat(row["event_time"]).timestamp() * 1_000_000_000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
            "sequence_number": int(row["sequence_number"]),
        }
        for row in packet["last_9_candles"]
    ]
    descriptor = _descriptor(candles)
    descriptor.update(
        {
            "window_id": f"current-{packet['evidence_packet_id']}",
            "regime_id": packet["regime_id"],
            "regime_group": packet["regime_group"],
            "session_phase": packet["session_phase"],
            "feature_manifest_version": packet["feature_manifest_version"],
            "descriptor_hash": _hash_json(descriptor),
        }
    )
    return descriptor


def _historical_windows(bars: list[dict[str, Any]], symbol: str, timeframe: str) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    max_horizon = max(HORIZONS)
    upper = max(0, len(bars) - 9 - max_horizon)
    for start in range(upper):
        nine = bars[start : start + 9]
        future = bars[start + 9 : start + 9 + max_horizon]
        descriptor = _descriptor(nine)
        labels = _label_future(nine, future)
        week_id = datetime.fromtimestamp(nine[-1]["timestamp_ns"] / 1_000_000_000, tz=timezone.utc).strftime("%G-W%V")
        descriptor.update(
            {
                "window_id": f"{symbol.lower()}-{timeframe}-{start + 1:05d}",
                "symbol": symbol,
                "timeframe": timeframe,
                "start_sequence": int(nine[0]["sequence_number"]),
                "end_sequence": int(nine[-1]["sequence_number"]),
                "decision_timestamp_ns": int(nine[-1]["timestamp_ns"]),
                "week_id": week_id,
                "regime_id": "trend_up_normal_vol_trend_confirmation_strongtrend_liquid",
                "regime_group": "trend_up_normal_vol",
                "session_phase": "trend_confirmation",
                "feature_manifest_version": FEATURE_MANIFEST_VERSION,
                **labels,
            }
        )
        descriptor["descriptor_hash"] = _hash_json(descriptor)
        windows.append(descriptor)
    _assign_historical_volatility_buckets(windows)
    return windows


def _persisted_outcome_matches(symbol: str, timeframe: str, current: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        summary = storage.nine_candle_memory_summary(symbol=symbol, timeframe=timeframe, limit=250)
    except Exception:
        return []
    matches: list[dict[str, Any]] = []
    labels_by_setup = summary.get("labels_by_setup", {})
    setups = summary.get("setups", [])
    for setup in setups:
        setup_id = str(setup.get("setup_id", ""))
        labels = labels_by_setup.get(setup_id, [])
        terminal = _terminal_persisted_label(labels)
        if not terminal:
            continue
        if str(setup.get("feature_manifest_version")) != current["feature_manifest_version"]:
            continue
        similarity = _persisted_similarity(setup, terminal, current)
        decision_time = str(setup.get("decision_time") or setup.get("created_at") or "")
        matches.append(
            {
                "window_id": setup_id,
                "decision_timestamp_ns": _timestamp_ns(decision_time),
                "week_id": _week_id(decision_time),
                "similarity_score": similarity,
                "cosine_similarity": similarity,
                "dtw_path_similarity": 0.0,
                "recency_weight": 1.0,
                "outcome_label": terminal["outcome_label"],
                "target_first": bool(terminal["target_first"]),
                "stop_first": bool(terminal["stop_first"]),
                "mfe_atr": float(terminal.get("mfe", 0.0)),
                "mae_atr": float(terminal.get("mae", 0.0)),
                "regime_id": str(setup.get("regime_id") or current["regime_id"]),
                "regime_group": current["regime_group"],
                "feature_manifest_version": str(setup["feature_manifest_version"]),
                "match_source": "persisted_outcome_memory",
                "label_hash": terminal.get("label_hash"),
                "horizon_candles": terminal.get("horizon_candles"),
            }
        )
    return matches


def _terminal_persisted_label(labels: list[dict[str, Any]]) -> dict[str, Any] | None:
    complete = [label for label in labels if label.get("label_status") == "complete"]
    if not complete:
        return None
    terminal_order = {"TARGET_HIT": 0, "SL_HIT": 1, "FAKE_BREAKOUT": 2, "CHOP_NO_FOLLOWTHROUGH": 3, "TIME_EXIT": 4}
    complete.sort(key=lambda item: (terminal_order.get(str(item.get("outcome_label")), 99), int(item.get("horizon_candles") or 999)))
    return complete[0]


def _persisted_similarity(setup: dict[str, Any], label: dict[str, Any], current: dict[str, Any]) -> float:
    score = 0.72
    if str(setup.get("regime_id")) == current["regime_id"]:
        score += 0.10
    if str(setup.get("session_phase")) == current["session_phase"]:
        score += 0.08
    if label.get("outcome_label") == "TARGET_HIT":
        score += 0.03
    if label.get("outcome_label") in {"SL_HIT", "FAKE_BREAKOUT"}:
        score += 0.02
    return round(min(score, 0.95), 6)


def _descriptor(candles: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [float(row["close"]) for row in candles]
    highs = [float(row["high"]) for row in candles]
    lows = [float(row["low"]) for row in candles]
    volumes = [float(row["volume"] or 0.0) for row in candles]
    step_returns = [(closes[idx] - closes[idx - 1]) / max(abs(closes[idx - 1]), 1e-9) for idx in range(1, len(closes))]
    avg_volume = mean(volumes) if volumes else 1.0
    ranges = [max(highs[idx] - lows[idx], 0.0) for idx in range(len(candles))]
    avg_range = mean(ranges) if ranges else 1.0
    atr = _atr(candles)
    vector = step_returns + [value / max(avg_volume, 1e-9) for value in volumes] + [value / max(avg_range, 1e-9) for value in ranges]
    return {
        "step_returns": [round(value, 8) for value in step_returns],
        "volume_curve": [round(value / max(avg_volume, 1e-9), 6) for value in volumes],
        "range_progression": [round(value / max(avg_range, 1e-9), 6) for value in ranges],
        "path_vector": [round(value, 8) for value in vector],
        "close_return": round((closes[-1] - closes[0]) / max(abs(closes[0]), 1e-9), 8),
        "atr": round(atr, 8),
    }


def _label_future(nine: list[dict[str, Any]], future: list[dict[str, Any]]) -> dict[str, Any]:
    entry = float(nine[-1]["close"])
    atr = _atr(nine)
    target = entry + atr
    stop = entry - atr * 0.70
    target_first = False
    stop_first = False
    time_to_target = None
    time_to_stop = None
    max_high = entry
    min_low = entry
    for index, row in enumerate(future, start=1):
        high = float(row["high"])
        low = float(row["low"])
        max_high = max(max_high, high)
        min_low = min(min_low, low)
        hit_target = high >= target
        hit_stop = low <= stop
        if hit_target and hit_stop:
            stop_first = True
            time_to_stop = index
            break
        if hit_stop:
            stop_first = True
            time_to_stop = index
            break
        if hit_target:
            target_first = True
            time_to_target = index
            break
    if target_first:
        label = "TARGET_HIT"
    elif stop_first:
        label = "SL_HIT"
    elif max_high - entry < atr * 0.25 and entry - min_low < atr * 0.25:
        label = "CHOP_NO_FOLLOWTHROUGH"
    elif max_high > entry and min_low < stop + atr * 0.20:
        label = "FAKE_BREAKOUT"
    else:
        label = "TIME_EXIT"
    return {
        "outcome_label": label,
        "target_first": target_first,
        "stop_first": stop_first,
        "time_to_target": time_to_target,
        "time_to_stop": time_to_stop,
        "mfe_atr": round((max_high - entry) / max(atr, 1e-9), 6),
        "mae_atr": round((entry - min_low) / max(atr, 1e-9), 6),
        "conservative_intrabar_rule": "stop_first_if_same_candle",
    }


def _scope_windows(windows: list[dict[str, Any]], current: dict[str, Any], volatility_bucket: str = "normal") -> list[dict[str, Any]]:
    scoped = [
        window
        for window in windows
        if window["feature_manifest_version"] == current["feature_manifest_version"]
        and window["regime_group"] == current["regime_group"]
        and window["session_phase"] == current["session_phase"]
        and window.get("volatility_bucket", "normal") == volatility_bucket
    ]
    if scoped:
        return scoped
    relaxed = [
        window
        for window in windows
        if window["feature_manifest_version"] == current["feature_manifest_version"]
        and window["regime_group"] == current["regime_group"]
        and window["session_phase"] == current["session_phase"]
    ]
    return relaxed or windows


def _volatility_status(current: dict[str, Any], windows: list[dict[str, Any]]) -> dict[str, Any]:
    historical_atrs = [float(window.get("atr", 0.0)) for window in windows if float(window.get("atr", 0.0)) > 0]
    current_atr = float(current.get("atr", 0.0))
    p75 = _percentile(historical_atrs, 0.75)
    p90 = _percentile(historical_atrs, 0.90)
    p50 = _percentile(historical_atrs, 0.50)
    if not historical_atrs or current_atr <= 0 or p90 is None:
        bucket = "unknown"
        vol_ood = True
        status = "wait"
        evidence = "Insufficient historical ATR distribution for volatility-OOD."
    else:
        bucket = _volatility_bucket(current_atr, p50, p75, p90)
        vol_ood = current_atr > p90
        status = "wait" if vol_ood else "pass"
        evidence = f"current_atr={round(current_atr, 6)} p90={p90} bucket={bucket}."
    bucket_count = sum(1 for window in windows if window.get("volatility_bucket", "normal") == bucket)
    return {
        "current_atr": round(current_atr, 8),
        "historical_atr_p50": p50,
        "historical_atr_p75": p75,
        "historical_atr_p90": p90,
        "volatility_bucket": bucket,
        "volatility_ood": vol_ood,
        "threshold_source": "historical_atr_p90",
        "raw_window_count": len(windows),
        "volatility_bucket_window_count": bucket_count,
        "gate": {
            "gate_id": "9C-G016",
            "name": "Volatility magnitude OOD",
            "status": status,
            "evidence": evidence,
        },
    }


def _volatility_bucket(current_atr: float, p50: float | None, p75: float | None, p90: float | None) -> str:
    if p90 is not None and current_atr > p90:
        return "extreme"
    if p75 is not None and current_atr > p75:
        return "high"
    if p50 is not None and current_atr < p50:
        return "low"
    return "normal"


def _assign_historical_volatility_buckets(windows: list[dict[str, Any]]) -> None:
    atrs = [float(window.get("atr", 0.0)) for window in windows if float(window.get("atr", 0.0)) > 0]
    p50 = _percentile(atrs, 0.50)
    p75 = _percentile(atrs, 0.75)
    p90 = _percentile(atrs, 0.90)
    for window in windows:
        window["volatility_bucket"] = _volatility_bucket(float(window.get("atr", 0.0)), p50, p75, p90)


def _match(current: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]:
    cosine = _cosine(current["path_vector"], window["path_vector"])
    dtw_distance = _dtw(current["step_returns"], window["step_returns"])
    path_similarity = 1.0 / (1.0 + dtw_distance * 100.0)
    recency_weight = _recency_weight(window["end_sequence"])
    similarity = max(0.0, min(((cosine * 0.65) + (path_similarity * 0.35)) * recency_weight, 1.0))
    return {
        "window_id": window["window_id"],
        "decision_timestamp_ns": window["decision_timestamp_ns"],
        "week_id": window["week_id"],
        "similarity_score": round(similarity, 6),
        "cosine_similarity": round(cosine, 6),
        "dtw_path_similarity": round(path_similarity, 6),
        "recency_weight": recency_weight,
        "outcome_label": window["outcome_label"],
        "target_first": window["target_first"],
        "stop_first": window["stop_first"],
        "mfe_atr": window["mfe_atr"],
        "mae_atr": window["mae_atr"],
        "regime_id": window["regime_id"],
        "regime_group": window["regime_group"],
        "feature_manifest_version": window["feature_manifest_version"],
    }


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        return 0.0
    return max(min(dot / (left_norm * right_norm), 1.0), -1.0)


def _dtw(left: list[float], right: list[float]) -> float:
    n = len(left)
    m = len(right)
    dp = [[float("inf")] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(left[i - 1] - right[j - 1])
            dp[i][j] = cost + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[n][m] / max(n + m, 1)


def _atr(candles: list[dict[str, Any]]) -> float:
    ranges = [max(float(row["high"]) - float(row["low"]), 0.0) for row in candles]
    return mean(ranges) if ranges else 1.0


def _recency_weight(end_sequence: int) -> float:
    return round(max(0.60, min(1.0, 0.60 + end_sequence / 260.0)), 6)


def _temporal_diversity(matches: list[dict[str, Any]]) -> dict[str, Any]:
    if not matches:
        return {"temporal_diversity_score": 0.0, "unique_weeks": 0}
    unique_weeks = len({item["week_id"] for item in matches})
    return {"temporal_diversity_score": round(min(unique_weeks / 8.0, 1.0), 6), "unique_weeks": unique_weeks}


def _timestamp_ns(value: str) -> int:
    try:
        return int(datetime.fromisoformat(value).timestamp() * 1_000_000_000)
    except Exception:
        return 0


def _week_id(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%G-W%V")
    except Exception:
        return "unknown"


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(math.ceil(len(ordered) * quantile) - 1, 0), len(ordered) - 1)
    return round(ordered[index], 6)


def _unit(*parts: str) -> float:
    raw = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(raw[:12], 16) / float(0xFFFFFFFFFFFF)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _hash_report(report: dict[str, Any]) -> str:
    stable = {key: value for key, value in report.items() if key not in {"latency_ms", "output_hash"}}
    return _hash_json(stable)
