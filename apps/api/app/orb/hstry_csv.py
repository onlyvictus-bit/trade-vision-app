"""HSTRY CSV loader for ORB timing research (v1.97).

Reads `{SYMBOL}_NSE_{tf}.csv` files (format: date,time,open,high,low,close,volume,oi)
with IST wall-clock timestamps and converts them into PIT-safe CandleSeries
(UTC epoch nanoseconds), filtered to the NSE session 09:15-15:30.

Read-only: never mutates the source files or the PIT snapshot store.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..models import CandleBar, CandleSeries, TimeframeValue

HSTRY_BASE_DIR = Path(r"C:\Users\sakth\Downloads\HSTRY")

# models.py TimeframeValue -> HSTRY filename token
_TIMEFRAME_FILE_TOKEN = {
    "1m": "1m",
    "3m": "03m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "4H": "4h",
}

_IST_OFFSET = pd.Timedelta(hours=5, minutes=30)
_SESSION_START = pd.Timedelta(hours=9, minutes=15)
_SESSION_END = pd.Timedelta(hours=15, minutes=30)


class HstryCsvNotFound(ValueError):
    """Raised when the requested symbol/timeframe CSV does not exist."""


def hstry_csv_path(symbol: str, timeframe: str = "5m", base_dir: Path | None = None) -> Path:
    token = _TIMEFRAME_FILE_TOKEN.get(timeframe)
    if token is None:
        raise ValueError(f"Unsupported HSTRY timeframe: {timeframe}")
    directory = base_dir if base_dir is not None else HSTRY_BASE_DIR
    return directory / f"{symbol}_NSE_{token}.csv"


def list_hstry_symbols(base_dir: Path | None = None) -> list[str]:
    directory = base_dir if base_dir is not None else HSTRY_BASE_DIR
    symbols = {
        path.name.split("_NSE_")[0]
        for path in directory.glob("*_NSE_*.csv")
        if path.name.count("_NSE_") == 1
    }
    return sorted(symbols)


def load_hstry_series(
    symbol: str,
    timeframe: str = "5m",
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    base_dir: Path | None = None,
    max_bars: int | None = None,
) -> CandleSeries:
    """Load one symbol's HSTRY csv as a closed-bar CandleSeries (UTC epoch ns).

    - Session filter keeps 09:15 <= time-of-day < 15:30 (IST).
    - start_date/end_date bound the research window (YYYY-MM-DD, inclusive).
    - max_bars keeps only the most recent N bars (memory guard for 1m files).
    - Duplicate timestamps are dropped (first occurrence wins), then sorted.
    """
    clean_symbol = symbol.strip().upper()
    path = hstry_csv_path(clean_symbol, timeframe, base_dir)
    if not path.exists():
        available = list_hstry_symbols(base_dir)
        raise HstryCsvNotFound(
            f"HSTRY csv not found: {path.name}; available symbols (sample): {available[:10]}"
        )

    frame = pd.read_csv(
        path,
        encoding="utf-8-sig",
        usecols=["date", "time", "open", "high", "low", "close", "volume"],
    )
    # normalize time to HH:MM:SS (some exports omit seconds)
    time_col = frame["time"].astype(str).str.strip()
    frame["time"] = time_col.where(time_col.str.len() > 5, time_col + ":00")
    stamp = pd.to_datetime(
        frame["date"].astype(str) + " " + frame["time"],
        format="%Y-%m-%d %H:%M:%S",
    )
    time_of_day = stamp - stamp.dt.normalize()
    session_mask = (time_of_day >= _SESSION_START) & (time_of_day < _SESSION_END)
    stamp = stamp[session_mask]
    frame = frame.loc[session_mask].reset_index(drop=True)
    stamp = stamp.reset_index(drop=True)

    if start_date:
        stamp = stamp[stamp >= pd.Timestamp(start_date)]
        frame = frame.loc[stamp.index].reset_index(drop=True)
        stamp = stamp.reset_index(drop=True)
    if end_date:
        stamp = stamp[stamp <= pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
        frame = frame.loc[stamp.index].reset_index(drop=True)
        stamp = stamp.reset_index(drop=True)

    utc_stamp = (stamp - _IST_OFFSET).dt.tz_localize("UTC")
    epoch_ns = utc_stamp.astype("int64")

    keep: dict[int, int] = {}
    for idx, ns in enumerate(epoch_ns):
        if int(ns) not in keep:
            keep[int(ns)] = idx

    ordered = sorted(keep.items())
    if max_bars is not None and len(ordered) > max_bars:
        ordered = ordered[-max_bars:]

    bars = [
        CandleBar(
            symbol=clean_symbol,
            timeframe=timeframe,  # type: ignore[arg-type]
            timestamp_ns=ns,
            open=float(frame.iloc[idx]["open"]),
            high=float(frame.iloc[idx]["high"]),
            low=float(frame.iloc[idx]["low"]),
            close=float(frame.iloc[idx]["close"]),
            volume=float(frame.iloc[idx]["volume"]),
            source="user_csv",
            sequence_number=seq,
        )
        for seq, (ns, idx) in enumerate(ordered, start=1)
    ]
    return CandleSeries(
        symbol=clean_symbol,
        timeframe=timeframe,  # type: ignore[arg-type]
        bars=bars,
        snapshot_id=f"hstry:{clean_symbol}:{timeframe}",
        schema_version="candles.v1",
    )
