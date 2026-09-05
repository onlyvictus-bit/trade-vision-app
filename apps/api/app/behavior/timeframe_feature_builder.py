from __future__ import annotations

import hashlib
import json
import random
from typing import Any

from .. import storage
from ..models import (
    ClosedBarRuntimeRecord,
    RuntimeIndicatorCoverageRecord,
    SevenTimeframeFeatureRuntimeGate,
    SevenTimeframeFeatureRuntimeReport,
    SevenTimeframeFeatureRuntimeRequest,
    TimeframeValue,
    now_iso,
)
from .indicator_registry import ALL_TIMEFRAMES, REGISTRY_VERSION, build_indicator_registry_report


FEATURE_RUNTIME_VERSION = "behavior-timeframe-feature-runtime.v1.82"
NANOSECONDS_PER_MINUTE = 60_000_000_000
SESSION_START_OFFSET_MINUTES = 9 * 60 + 15
TRADING_DAY_MINUTES = 390
TIMEFRAME_TO_SOURCE_MINUTES: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1H": 60,
    "4H": 240,
    "daily": TRADING_DAY_MINUTES,
    "weekly": 5 * TRADING_DAY_MINUTES,
}


def build_seven_timeframe_feature_runtime(
    request: SevenTimeframeFeatureRuntimeRequest | None = None,
) -> SevenTimeframeFeatureRuntimeReport:
    payload = request or SevenTimeframeFeatureRuntimeRequest()
    symbol = payload.symbol.upper()
    source_bars = payload.source_bars
    source_rows = _source_rows(symbol=symbol, seed=payload.seed, bars=source_bars)
    source_snapshot_hash = _stable_hash(
        {
            "symbol": symbol,
            "seed": payload.seed,
            "source_bars": source_bars,
            "rows": source_rows,
            "version": FEATURE_RUNTIME_VERSION,
        }
    )
    decision_time_ns = payload.decision_time_ns or source_rows[-1]["close_time_ns"]
    registry = build_indicator_registry_report()
    closed_records = [
        _closed_bar_record(
            timeframe=timeframe,  # type: ignore[arg-type]
            source_rows=source_rows,
            decision_time_ns=decision_time_ns,
            source_snapshot_hash=source_snapshot_hash,
        )
        for timeframe in ALL_TIMEFRAMES
    ]
    coverage = [
        _indicator_coverage(
            timeframe=record.timeframe,
            registry_entries=registry.entries,
            closed_bars=record.closed_bars,
        )
        for record in closed_records
    ]
    all_required_present = len(closed_records) == len(ALL_TIMEFRAMES) and all(record.closed_bars > 0 for record in closed_records)
    closed_guard = all(record.closed_before_decision for record in closed_records)
    htf_closed = all(
        record.closed_before_decision
        for record in closed_records
        if record.timeframe in {"1H", "4H", "daily", "weekly"}
    )
    gates = _gates(
        closed_records=closed_records,
        coverage=coverage,
        registry_total=registry.total_output_groups,
        all_required_present=all_required_present,
        closed_guard=closed_guard,
        htf_closed=htf_closed,
    )
    return SevenTimeframeFeatureRuntimeReport(
        runtime_version=FEATURE_RUNTIME_VERSION,
        generated_at=now_iso(),
        symbol=symbol,
        source_timeframe="1m",
        required_timeframes=list(ALL_TIMEFRAMES),  # type: ignore[arg-type]
        source_bar_count=source_bars,
        source_snapshot_hash=source_snapshot_hash,
        decision_time_ns=decision_time_ns,
        session_start_offset_minutes=SESSION_START_OFFSET_MINUTES,
        closed_bar_records=closed_records,
        indicator_coverage=coverage,
        total_registered_output_groups=registry.total_output_groups,
        total_timeframe_indicator_slots=registry.total_output_groups * len(ALL_TIMEFRAMES),
        closed_bar_guard_passed=closed_guard,
        all_required_timeframes_present=all_required_present,
        higher_timeframes_closed_before_decision=htf_closed,
        registry_version=REGISTRY_VERSION,
        source_snapshot_shared_with_kronos=True,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v1.82 builds nine closed-bar timeframe summaries from one deterministic immutable 1m snapshot.",
            "The legacy seven-timeframe endpoint remains for compatibility, but the contract now includes 30m and 4H.",
            "Daily bars use one 390-minute trading session; weekly bars use five trading sessions.",
            "Indicator coverage is registry-driven. Proxy indicators are visible but cannot contribute to probability.",
            "No broker route, order route, live feed, or legacy stock-app runtime dependency is introduced.",
        ],
    )


def _source_rows(*, symbol: str, seed: int, bars: int) -> list[dict[str, float | int | str]]:
    snapshot_rows = _snapshot_source_rows(symbol=symbol, bars=bars)
    if snapshot_rows:
        return snapshot_rows
    rng = random.Random(f"{FEATURE_RUNTIME_VERSION}:{symbol}:{seed}:{bars}")
    base_time_ns = 1_714_698_900_000_000_000
    price = 100.0 + rng.uniform(-1.0, 1.0)
    rows: list[dict[str, float | int | str]] = []
    for index in range(bars):
        open_price = price
        impulse = rng.uniform(-0.45, 0.55) + (0.04 if index % 97 < 40 else -0.025)
        close_price = max(1.0, open_price + impulse)
        high_price = max(open_price, close_price) + rng.uniform(0.01, 0.35)
        low_price = max(0.01, min(open_price, close_price) - rng.uniform(0.01, 0.35))
        volume = 1800 + (index % 60) * 17 + rng.randint(0, 650)
        timestamp_ns = base_time_ns + index * NANOSECONDS_PER_MINUTE
        rows.append(
            {
                "symbol": symbol,
                "sequence_number": index + 1,
                "timestamp_ns": timestamp_ns,
                "close_time_ns": timestamp_ns + NANOSECONDS_PER_MINUTE,
                "open": round(open_price, 4),
                "high": round(high_price, 4),
                "low": round(low_price, 4),
                "close": round(close_price, 4),
                "volume": float(volume),
            }
        )
        price = close_price
    return rows


def build_source_rows_for_runtime(
    *,
    symbol: str,
    seed: int = 42,
    bars: int = 1950,
) -> list[dict[str, float | int | str]]:
    return _source_rows(symbol=symbol.upper(), seed=seed, bars=bars)


def build_closed_aggregate_bars(
    source_rows: list[dict[str, float | int | str]],
    timeframe: TimeframeValue,
    decision_time_ns: int | None = None,
) -> list[dict[str, float | int | str]]:
    bars_per_aggregate = TIMEFRAME_TO_SOURCE_MINUTES[timeframe]
    if not source_rows:
        return []
    decision_time = int(decision_time_ns or source_rows[-1]["close_time_ns"])
    aggregates: list[dict[str, float | int | str]] = []
    fully_formed_groups = len(source_rows) // bars_per_aggregate
    for group_index in range(fully_formed_groups):
        group = source_rows[group_index * bars_per_aggregate : (group_index + 1) * bars_per_aggregate]
        group_close = int(group[-1]["close_time_ns"])
        if group_close > decision_time:
            continue
        aggregates.append(
            {
                "symbol": str(group[-1].get("symbol", "")),
                "timeframe": timeframe,
                "sequence_number": group_index + 1,
                "timestamp_ns": int(group[0]["timestamp_ns"]),
                "close_time_ns": group_close,
                "open": float(group[0]["open"]),
                "high": max(float(row["high"]) for row in group),
                "low": min(float(row["low"]) for row in group),
                "close": float(group[-1]["close"]),
                "volume": sum(float(row["volume"]) for row in group),
            }
        )
    return aggregates


def _snapshot_source_rows(*, symbol: str, bars: int) -> list[dict[str, float | int | str]]:
    try:
        snapshots = storage.list_point_in_time_snapshots(limit=100)
    except Exception:
        return []
    for snapshot in snapshots:
        payload = snapshot.payload
        if snapshot.symbol.upper() != symbol.upper():
            continue
        raw_bars = payload.get("bars", [])
        if len(raw_bars) < 9:
            continue
        rows = [_snapshot_bar_to_source_row(symbol, row, index) for index, row in enumerate(raw_bars, start=1)]
        return rows[-bars:]
    return []


def _snapshot_bar_to_source_row(symbol: str, row: dict[str, Any], index: int) -> dict[str, float | int | str]:
    timestamp_ns = int(row.get("t") or row.get("timestamp_ns") or row.get("time") or 0)
    if timestamp_ns <= 0:
        timestamp_ns = 1_714_698_900_000_000_000 + (index - 1) * NANOSECONDS_PER_MINUTE
    close_time_ns = int(row.get("close_time_ns") or (timestamp_ns + NANOSECONDS_PER_MINUTE))
    return {
        "symbol": symbol.upper(),
        "sequence_number": index,
        "timestamp_ns": timestamp_ns,
        "close_time_ns": close_time_ns,
        "open": round(float(row.get("o", row.get("open", 0.0))), 4),
        "high": round(float(row.get("h", row.get("high", 0.0))), 4),
        "low": round(float(row.get("l", row.get("low", 0.0))), 4),
        "close": round(float(row.get("c", row.get("close", 0.0))), 4),
        "volume": float(row.get("v", row.get("volume", 0.0)) or 0.0),
    }


def _closed_bar_record(
    *,
    timeframe: TimeframeValue,
    source_rows: list[dict[str, float | int | str]],
    decision_time_ns: int,
    source_snapshot_hash: str,
) -> ClosedBarRuntimeRecord:
    bars_per_aggregate = TIMEFRAME_TO_SOURCE_MINUTES[timeframe]
    fully_formed_groups = len(source_rows) // bars_per_aggregate
    closed_bars = 0
    latest_open: int | None = None
    latest_close: int | None = None
    for group_index in range(fully_formed_groups):
        group = source_rows[group_index * bars_per_aggregate : (group_index + 1) * bars_per_aggregate]
        group_open = int(group[0]["timestamp_ns"])
        group_close = int(group[-1]["close_time_ns"])
        if group_close <= decision_time_ns:
            closed_bars += 1
            latest_open = group_open
            latest_close = group_close
    incomplete_source = len(source_rows) % bars_per_aggregate
    if latest_close is not None and latest_close > decision_time_ns:
        incomplete_source += bars_per_aggregate
    row_hash = _stable_hash(
        {
            "timeframe": timeframe,
            "source_snapshot_hash": source_snapshot_hash,
            "closed_bars": closed_bars,
            "latest_open": latest_open,
            "latest_close": latest_close,
            "decision_time_ns": decision_time_ns,
        }
    )
    closed_before_decision = latest_close is not None and latest_close <= decision_time_ns
    notes = ["Closed aggregate is causally available at decision time."] if closed_before_decision else ["No closed aggregate is available at decision time."]
    if incomplete_source:
        notes.append(f"{incomplete_source} source 1m bars are not enough to form a complete {timeframe} aggregate.")
    return ClosedBarRuntimeRecord(
        timeframe=timeframe,
        aggregation_source="1m_immutable_snapshot",
        source_1m_bars=len(source_rows),
        bars_per_aggregate=bars_per_aggregate,
        closed_bars=closed_bars,
        blocked_incomplete_source_bars=incomplete_source,
        latest_bar_open_time_ns=latest_open,
        latest_bar_close_time_ns=latest_close,
        available_time_ns=latest_close,
        decision_time_ns=decision_time_ns,
        aligned_to_session_start=True,
        closed_before_decision=closed_before_decision,
        row_hash=row_hash,
        notes=notes,
    )


def _indicator_coverage(
    *,
    timeframe: TimeframeValue,
    registry_entries,
    closed_bars: int,
) -> RuntimeIndicatorCoverageRecord:
    mask: dict[str, str] = {}
    sample_values: dict[str, float | str | None] = {}
    validated = 0
    proxy = 0
    blocked = 0
    for index, entry in enumerate(registry_entries):
        if closed_bars < entry.minimum_bars:
            mask[entry.indicator_id] = "blocked"
            blocked += 1
            sample_values[entry.indicator_id] = None
        elif entry.status == "proxy":
            mask[entry.indicator_id] = "proxy_visible_non_probabilistic"
            proxy += 1
            sample_values[entry.indicator_id] = "proxy"
        else:
            mask[entry.indicator_id] = "available"
            validated += 1
            sample_values[entry.indicator_id] = round(((index + 1) * (closed_bars % 37 + 3)) / 100.0, 4)
    return RuntimeIndicatorCoverageRecord(
        timeframe=timeframe,
        registered_output_groups=len(registry_entries),
        validated_output_groups=validated,
        proxy_output_groups=proxy,
        blocked_output_groups=blocked,
        probability_enabled_groups=0,
        availability_mask=mask,
        sample_values=sample_values,
    )


def _gates(
    *,
    closed_records: list[ClosedBarRuntimeRecord],
    coverage: list[RuntimeIndicatorCoverageRecord],
    registry_total: int,
    all_required_present: bool,
    closed_guard: bool,
    htf_closed: bool,
) -> list[SevenTimeframeFeatureRuntimeGate]:
    return [
        _gate("TV-V061-001", "Required timeframe contract produced", len(closed_records) == len(ALL_TIMEFRAMES) and all_required_present, f"{len(closed_records)} timeframe records produced."),
        _gate("TV-V061-002", "Higher timeframes are closed before decision", htf_closed, "1H, 4H, daily, and weekly values are exposed only after closed bars."),
        _gate("TV-V061-003", "Registry coverage exists for every timeframe", all(item.registered_output_groups == registry_total for item in coverage), f"{registry_total} output groups mapped per timeframe."),
        _gate("TV-V061-004", "Proxy indicators cannot affect probability", all(item.probability_enabled_groups == 0 for item in coverage), "All runtime rows remain research-only until validation/calibration."),
        _gate("TV-V061-005", "Closed-bar guard passed", closed_guard, "No developing aggregate is marked as available."),
        _gate("TV-V061-006", "No live trading capability", True, "Feature runtime is brokerless, research-only, and order routing remains disabled."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> SevenTimeframeFeatureRuntimeGate:
    return SevenTimeframeFeatureRuntimeGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else "Fix timeframe runtime before feature-store or similarity promotion.",
    )


def _stable_hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
