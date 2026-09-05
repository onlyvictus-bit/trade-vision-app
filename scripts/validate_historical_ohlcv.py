from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.behavior.candle_anatomy import analyze_candles
from app.behavior.condition_classifier import classify_conditions
from app.behavior.data_quality import scan_data_quality
from app.behavior.point_in_time_guard import run_point_in_time_guard
from app.behavior.replay_indicator_validation import _chart_points, _indicator_points
from app.behavior.session_memory import analyze_session_rhythm, session_phase_for_timestamp
from app.models import (
    CandleAnatomyRequest,
    CandleBar,
    CandleSeries,
    ConditionClassifierRequest,
    PointInTimeGuardRequest,
    SessionRhythmRequest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a large historical OHLCV CSV without loading it all into memory.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--symbol", default="RELIANCE")
    parser.add_argument("--timeframe", default="1m", choices=["1m"])
    parser.add_argument("--timezone-offset-minutes", type=int, default=330)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "validation" / "historical_ohlcv_report.json")
    args = parser.parse_args()

    started = perf_counter()
    stream = stream_validate(args.csv_path, args.symbol, args.timezone_offset_minutes)
    latest_bars = stream.pop("latest_session_bars")
    series = CandleSeries(
        symbol=args.symbol.upper(),
        timeframe="1m",
        bars=latest_bars,
        snapshot_id=f"historical-{args.symbol.lower()}-{stream['latest_session_date']}",
        schema_version="candles.historical-validation.v1",
    )
    quality = scan_data_quality(series)
    decision_time_ns = latest_bars[-1].timestamp_ns + 60_000_000_000
    pit = run_point_in_time_guard(
        PointInTimeGuardRequest(
            series=series,
            decision_time_ns=decision_time_ns,
            execution_time_ns=decision_time_ns,
            source_timeframe="1m",
        )
    )
    indicators = _indicator_points(series.bars)
    chart_points = _chart_points(series.bars, indicators)
    vwap = _vwap(latest_bars)
    opening_bars = latest_bars[:15]
    reference_bars = latest_bars[:-1] or latest_bars
    anatomy = analyze_candles(
        CandleAnatomyRequest(
            series=series,
            breakout_reference_high=max(bar.high for bar in reference_bars),
            breakout_reference_low=min(bar.low for bar in reference_bars),
        )
    )
    phase = session_phase_for_timestamp(latest_bars[-1].timestamp_ns, args.timezone_offset_minutes)
    conditions = classify_conditions(
        ConditionClassifierRequest(
            series=series,
            anatomy=anatomy,
            vwap=vwap,
            opening_range_high=max(bar.high for bar in opening_bars),
            opening_range_low=min(bar.low for bar in opening_bars),
            support_level=min(bar.low for bar in reference_bars),
            resistance_level=max(bar.high for bar in reference_bars),
            session_phase=phase,
        )
    )
    rhythm = analyze_session_rhythm(
        SessionRhythmRequest(
            series=series,
            timezone_offset_minutes=args.timezone_offset_minutes,
            minimum_bars_per_segment=3,
        )
    )
    latest_indicator = indicators[-1]
    result = {
        "validation_version": "tradevision-historical-ohlcv-validation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(args.csv_path.resolve()),
        "symbol": args.symbol.upper(),
        "timeframe": "1m",
        "full_history": stream,
        "latest_session": {
            "date": stream["latest_session_date"],
            "bar_count": len(latest_bars),
            "first_timestamp_ns": latest_bars[0].timestamp_ns,
            "last_timestamp_ns": latest_bars[-1].timestamp_ns,
            "open": latest_bars[0].open,
            "high": max(bar.high for bar in latest_bars),
            "low": min(bar.low for bar in latest_bars),
            "close": latest_bars[-1].close,
            "volume": sum(float(bar.volume or 0) for bar in latest_bars),
            "vwap": round(vwap, 4),
            "quality": quality.model_dump(mode="json"),
            "point_in_time": pit.model_dump(mode="json"),
            "indicator_count": 6,
            "latest_indicators": latest_indicator.model_dump(mode="json"),
            "chart_point_count": len(chart_points),
            "chart_output_hash": _hash([point.model_dump(mode="json") for point in chart_points]),
            "candle_anatomy_summary": anatomy.summary,
            "latest_candle_anatomy": anatomy.latest.model_dump(mode="json") if anatomy.latest else None,
            "condition": conditions.model_dump(mode="json"),
            "session_rhythm": rhythm.model_dump(mode="json"),
        },
        "system_verdict": {
            "full_file_stream_read_passed": True,
            "latest_session_quality_passed": not quality.blocks_trade,
            "point_in_time_guard_passed": not pit.blocks_trade,
            "indicator_output_produced": len(indicators) == len(latest_bars),
            "chart_output_produced": len(chart_points) == len(latest_bars),
            "behavior_output_produced": conditions.latest is not None,
            "session_output_produced": rhythm.trading_date is not None,
            "stock_dna_memory_trained": False,
            "stock_dna_note": "This validation reads and analyzes the data, but bulk historical outcome labeling and Stock DNA training are not yet wired to this CLI.",
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), **result["system_verdict"], "elapsed_seconds": result["elapsed_seconds"]}, indent=2))
    return 0


def stream_validate(path: Path, symbol: str, offset_minutes: int) -> dict[str, object]:
    required = {"date", "time", "open", "high", "low", "close", "volume"}
    row_count = 0
    invalid_ohlc = 0
    missing_volume = 0
    duplicate_timestamps = 0
    non_monotonic = 0
    intraday_gap_count = 0
    abnormal_prints = 0
    split_suspects = 0
    parse_errors = 0
    date_counts: Counter[str] = Counter()
    seen: set[int] = set()
    previous_timestamp: int | None = None
    previous_close: float | None = None
    previous_date: str | None = None
    first_date: str | None = None
    last_date: str | None = None
    latest_session_bars: list[CandleBar] = []
    tz = timezone(timedelta(minutes=offset_minutes))

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        available = set(reader.fieldnames or [])
        missing = sorted(required - available)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        for raw in reader:
            row_count += 1
            try:
                trade_date = raw["date"].strip()
                timestamp = datetime.fromisoformat(f"{trade_date}T{raw['time'].strip()}").replace(tzinfo=tz)
                timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
                open_price = float(raw["open"])
                high = float(raw["high"])
                low = float(raw["low"])
                close = float(raw["close"])
                volume_text = raw.get("volume", "").strip()
                volume = float(volume_text) if volume_text else None
            except (KeyError, TypeError, ValueError):
                parse_errors += 1
                continue
            first_date = first_date or trade_date
            last_date = trade_date
            date_counts[trade_date] += 1
            if trade_date != previous_date:
                latest_session_bars = []
            latest_session_bars.append(
                CandleBar(
                    symbol=symbol.upper(),
                    timeframe="1m",
                    timestamp_ns=timestamp_ns,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    source="user_csv",
                    sequence_number=len(latest_session_bars) + 1,
                )
            )
            if low > high or high < max(open_price, close) or low > min(open_price, close):
                invalid_ohlc += 1
            if volume is None:
                missing_volume += 1
            if timestamp_ns in seen:
                duplicate_timestamps += 1
            seen.add(timestamp_ns)
            if previous_timestamp is not None:
                if timestamp_ns <= previous_timestamp:
                    non_monotonic += 1
                elif trade_date == previous_date and timestamp_ns - previous_timestamp > 90_000_000_000:
                    intraday_gap_count += 1
            if close > 0 and (high - low) / close > 0.25:
                abnormal_prints += 1
            if previous_close and previous_close > 0 and trade_date == previous_date:
                ratio = close / previous_close
                if ratio >= 2 or ratio <= 0.5:
                    split_suspects += 1
            previous_timestamp = timestamp_ns
            previous_close = close
            previous_date = trade_date

    if not latest_session_bars:
        raise ValueError("No valid candles found.")
    return {
        "row_count": row_count,
        "valid_parsed_rows": row_count - parse_errors,
        "parse_error_count": parse_errors,
        "first_date": first_date,
        "last_date": last_date,
        "trading_day_count": len(date_counts),
        "latest_session_date": last_date,
        "latest_session_bar_count": len(latest_session_bars),
        "minimum_bars_per_day": min(date_counts.values()) if date_counts else 0,
        "maximum_bars_per_day": max(date_counts.values()) if date_counts else 0,
        "invalid_ohlc_count": invalid_ohlc,
        "missing_volume_count": missing_volume,
        "duplicate_timestamp_count": duplicate_timestamps,
        "non_monotonic_count": non_monotonic,
        "intraday_gap_count": intraday_gap_count,
        "abnormal_print_count": abnormal_prints,
        "split_suspect_count": split_suspects,
        "latest_session_bars": latest_session_bars,
    }


def _vwap(bars: list[CandleBar]) -> float:
    total_volume = sum(float(bar.volume or 0.0) for bar in bars)
    if total_volume <= 0:
        return bars[-1].close
    return sum(((bar.high + bar.low + bar.close) / 3) * float(bar.volume or 0.0) for bar in bars) / total_volume


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
