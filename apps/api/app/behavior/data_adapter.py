from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

from ..models import (
    BehaviorDataAdapterManifest,
    BehaviorDataAdapterResult,
    BehaviorOhlcvImportRequest,
    BehaviorOhlcvImportResult,
    CandleBar,
    CandleSeries,
    PointInTimeSnapshot,
    PointInTimeGuardRequest,
    SystemModeValue,
    TimeframeValue,
    now_iso,
)
from .data_quality import scan_data_quality
from .point_in_time_guard import run_point_in_time_guard


ADAPTER_VERSION = "behavior-data-adapter.v0.13"
IMPORT_VERSION = "behavior-real-ohlcv-import.v0.40"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
LEGACY_STOCK_APP_SNAPSHOT = PROJECT_ROOT / "legacy" / "stock_app"
LOCAL_DATA_DIR = PROJECT_ROOT / "data"


SUPPORTED_TIMEFRAMES: list[TimeframeValue] = ["1m", "3m", "5m", "15m", "1H", "daily", "weekly"]


def adapter_manifest() -> BehaviorDataAdapterManifest:
    return BehaviorDataAdapterManifest(
        adapter_version=ADAPTER_VERSION,
        source_roots=[
            str(LEGACY_STOCK_APP_SNAPSHOT),
            str(LOCAL_DATA_DIR),
        ],
        supported_inputs=[
            "PointInTimeSnapshot.payload.bars[{t,o,h,l,c,v}]",
            "User supplied OHLCV CSV with timestamp/open/high/low/close/volume columns",
            "Vendored stock-app chart/indicator/backtest references after explicit porting",
        ],
        supported_timeframes=SUPPORTED_TIMEFRAMES,
        output_contract="CandleSeries",
        production_rules=[
            "No runtime import from legacy.stock_app is allowed.",
            "No live feed is allowed in v0.13.",
            "Every adapted candle must keep timestamp_ns and sequence_number.",
            "Aggregation is not performed in v0.13; timeframe sync is handled by the guard layer.",
            "Data quality and point-in-time guard must pass before behavior analysis promotion.",
            "User CSV import is research-only in v0.40 and never enables broker/live routing.",
        ],
        runtime_dependency_on_legacy_stock_app=False,
    )


def adapt_snapshot(snapshot: PointInTimeSnapshot, requested_timeframe: TimeframeValue | None = None) -> BehaviorDataAdapterResult:
    payload = snapshot.payload
    source_timeframe = payload.get("timeframe", requested_timeframe or "1m")
    timeframe: TimeframeValue = source_timeframe if source_timeframe in SUPPORTED_TIMEFRAMES else "1m"  # type: ignore[assignment]
    warnings: list[str] = []
    if requested_timeframe and requested_timeframe != timeframe:
        warnings.append(
            f"Requested timeframe {requested_timeframe} differs from source timeframe {timeframe}; v0.13 does not aggregate candles."
        )

    bars = [
        CandleBar(
            symbol=str(payload.get("symbol", snapshot.symbol)).upper(),
            timeframe=timeframe,
            timestamp_ns=int(row["t"]),
            open=float(row["o"]),
            high=float(row["h"]),
            low=float(row["l"]),
            close=float(row["c"]),
            volume=float(row["v"]) if row.get("v") is not None else None,
            source="snapshot",
            sequence_number=idx,
        )
        for idx, row in enumerate(payload.get("bars", []), start=1)
    ]
    return BehaviorDataAdapterResult(
        adapter_version=ADAPTER_VERSION,
        source_snapshot_id=snapshot.snapshot_id,
        source_payload_hash=snapshot.payload_hash,
        series=CandleSeries(
            symbol=snapshot.symbol.upper(),
            timeframe=timeframe,
            bars=bars,
            snapshot_id=snapshot.snapshot_id,
            schema_version="candles.v1",
        ),
        warnings=warnings,
        runtime_dependency_on_legacy_stock_app=False,
    )


def import_ohlcv_csv(payload: BehaviorOhlcvImportRequest) -> BehaviorOhlcvImportResult:
    rows = list(csv.DictReader(payload.csv_text.splitlines()))
    warnings: list[str] = []
    timestamp_columns = (
        {payload.date_column, payload.time_column}
        if payload.date_column and payload.time_column
        else {payload.timestamp_column}
    )
    required_columns = {
        *timestamp_columns,
        payload.open_column,
        payload.high_column,
        payload.low_column,
        payload.close_column,
    }
    available_columns = set(rows[0].keys()) if rows else set()
    missing_columns = sorted(required_columns - available_columns)
    if missing_columns:
        raise ValueError(f"Missing required OHLCV CSV columns: {', '.join(missing_columns)}")

    bars: list[CandleBar] = []
    parse_errors: list[str] = []
    normalized_symbol = payload.symbol.upper()
    for idx, row in enumerate(rows, start=1):
        try:
            volume_value = row.get(payload.volume_column)
            bars.append(
                CandleBar(
                    symbol=normalized_symbol,
                    timeframe=payload.timeframe,
                    timestamp_ns=_parse_timestamp_ns(
                        _timestamp_text(row, payload),
                        payload.timezone_offset_minutes,
                    ),
                    open=_parse_float(row[payload.open_column], "open", idx),
                    high=_parse_float(row[payload.high_column], "high", idx),
                    low=_parse_float(row[payload.low_column], "low", idx),
                    close=_parse_float(row[payload.close_column], "close", idx),
                    volume=_parse_optional_float(volume_value, "volume", idx),
                    source="user_csv",
                    sequence_number=len(bars) + 1,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            parse_errors.append(f"row {idx}: {exc}")

    if parse_errors:
        warnings.extend(parse_errors[:10])
    if len(parse_errors) > 10:
        warnings.append(f"{len(parse_errors) - 10} additional row parse errors omitted.")

    bars.sort(key=lambda item: (item.timestamp_ns, item.sequence_number))
    bars = [bar.model_copy(update={"sequence_number": idx}) for idx, bar in enumerate(bars, start=1)]
    series = CandleSeries(
        symbol=normalized_symbol,
        timeframe=payload.timeframe,
        bars=bars,
        snapshot_id=None,
        schema_version="candles.v1",
    )
    snapshot_payload = {
        "symbol": normalized_symbol,
        "timeframe": payload.timeframe,
        "bars": [
            {
                "t": bar.timestamp_ns,
                "o": bar.open,
                "h": bar.high,
                "l": bar.low,
                "c": bar.close,
                "v": bar.volume,
            }
            for bar in bars
        ],
        "source": "user_csv",
        "leakage_policy": "point_in_time_only",
        "import_version": IMPORT_VERSION,
    }
    payload_json = json.dumps(snapshot_payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    snapshot_id = f"user-csv-{normalized_symbol.lower()}-{payload.timeframe.lower()}-{payload_hash[:16]}"
    if bars:
        series = series.model_copy(update={"snapshot_id": snapshot_id})
    quality = scan_data_quality(series)
    decision_time_ns = payload.decision_time_ns if payload.decision_time_ns is not None else (bars[-1].timestamp_ns + _timeframe_duration_ns(payload.timeframe) if bars else 0)
    point_in_time = run_point_in_time_guard(
        PointInTimeGuardRequest(
            series=series,
            decision_time_ns=decision_time_ns,
            execution_time_ns=decision_time_ns,
            source_timeframe=payload.timeframe,
        )
    )
    safe_for_research = bool(bars) and not quality.blocks_trade and not point_in_time.blocks_trade
    if not bars:
        warnings.append("No valid OHLCV bars were parsed from the CSV payload.")
    return BehaviorOhlcvImportResult(
        import_version=IMPORT_VERSION,
        symbol=normalized_symbol,
        timeframe=payload.timeframe,
        row_count=len(rows),
        parsed_bar_count=len(bars),
        persisted_snapshot_id=snapshot_id if payload.persist_snapshot and bars else None,
        payload_hash=payload_hash,
        series=series,
        quality=quality,
        point_in_time=point_in_time,
        warnings=warnings,
        safe_for_research=safe_for_research,
    )


def build_import_snapshot(result: BehaviorOhlcvImportResult) -> PointInTimeSnapshot:
    payload = {
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "bars": [
            {
                "t": bar.timestamp_ns,
                "o": bar.open,
                "h": bar.high,
                "l": bar.low,
                "c": bar.close,
                "v": bar.volume,
            }
            for bar in result.series.bars
        ],
        "source": "user_csv",
        "leakage_policy": "point_in_time_only",
        "import_version": result.import_version,
    }
    return PointInTimeSnapshot(
        snapshot_id=result.persisted_snapshot_id or f"user-csv-{result.symbol.lower()}-{result.timeframe.lower()}-{result.payload_hash[:16]}",
        symbol=result.symbol,
        source_mode=SystemModeValue.MOCK,
        seed=0,
        as_of_timestamp_ns=result.series.bars[-1].timestamp_ns if result.series.bars else 0,
        created_at=now_iso(),
        schema_version="ohlcv.user_csv.v1",
        payload_hash=result.payload_hash,
        payload=payload,
        immutable=True,
    )


def _parse_float(value: object, field_name: str, row_number: int) -> float:
    parsed = float(str(value).strip())
    if parsed <= 0:
        raise ValueError(f"{field_name} must be positive at row {row_number}")
    return parsed


def _parse_optional_float(value: object, field_name: str, row_number: int) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    parsed = float(str(value).strip())
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative at row {row_number}")
    return parsed


def _timestamp_text(row: dict[str, str], payload: BehaviorOhlcvImportRequest) -> str:
    if payload.date_column and payload.time_column:
        return f"{str(row[payload.date_column]).strip()}T{str(row[payload.time_column]).strip()}"
    return str(row[payload.timestamp_column]).strip()


def _parse_timestamp_ns(raw: str, timezone_offset_minutes: int = 0) -> int:
    if raw.isdigit():
        value = int(raw)
        if value >= 10_000_000_000_000_000_000:
            return value
        if value >= 10_000_000_000_000_000:
            return value * 1_000
        if value >= 10_000_000_000_000:
            return value * 1_000_000
        if value >= 10_000_000_000:
            return value * 1_000_000
        return value * 1_000_000_000
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(minutes=timezone_offset_minutes)))
    return int(parsed.timestamp() * 1_000_000_000)


def _timeframe_duration_ns(timeframe: TimeframeValue) -> int:
    minutes = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "1H": 60,
        "daily": 390,
        "weekly": 390 * 5,
    }[timeframe]
    return minutes * 60_000_000_000
