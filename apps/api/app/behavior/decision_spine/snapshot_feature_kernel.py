from __future__ import annotations

"""Deterministic D2-derived price feature substrate for M3.1.

The kernel is deliberately not a trading brain. It consumes one already-approved
``ClosedCandleSnapshot`` and computes reusable Level-0/Level-1 price facts once.
It performs no I/O, no provider fetch, no persistence access, no prediction,
no scoring, no strategy selection and no final-decision work.

Important compatibility note:
``candle_anatomy.v0.15`` currently uses rolling *mean candle range* for its
``range_atr`` feature rather than Wilder true range. This module preserves that
existing fact under the explicit name ``average_range``. A future canonical ATR
implementation must be separately versioned and parity-tested rather than
silently changing trading mathematics here.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from statistics import mean, pstdev
from typing import Iterable

from ...models import CandleBar, ClosedCandleSnapshot


SNAPSHOT_FEATURE_KERNEL_VERSION = "snapshot-feature-kernel.v1"
DEFAULT_AVERAGE_RANGE_WINDOWS: tuple[int, ...] = (14,)
DEFAULT_VOLUME_WINDOWS: tuple[int, ...] = (20,)
MAX_WINDOW = 10_000


class SnapshotFeatureKernelError(ValueError):
    """Raised when an approved D2 snapshot cannot safely form the feature substrate."""


@dataclass(frozen=True, slots=True)
class KernelIdentity:
    symbol: str
    timeframe: str
    decision_time_ns: int
    snapshot_hash: str
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class KernelVectors:
    timestamps_ns: tuple[int, ...]
    sequence_numbers: tuple[int, ...]
    opens: tuple[float, ...]
    highs: tuple[float, ...]
    lows: tuple[float, ...]
    closes: tuple[float, ...]
    volumes: tuple[float | None, ...]
    ranges: tuple[float, ...]
    bodies: tuple[float, ...]
    typical_prices: tuple[float, ...]
    returns: tuple[float | None, ...]


@dataclass(frozen=True, slots=True)
class AverageRangeWindow:
    window: int
    values: tuple[float, ...]

    @property
    def latest(self) -> float:
        return self.values[-1]


@dataclass(frozen=True, slots=True)
class VolumeWindow:
    window: int
    means: tuple[float | None, ...]
    population_stddevs: tuple[float | None, ...]
    zscores: tuple[float | None, ...]

    @property
    def latest_zscore(self) -> float | None:
        return self.zscores[-1]


@dataclass(frozen=True, slots=True)
class KernelBuildAudit:
    feature_kernel_build_count: int
    bar_sort_pass_count: int
    bar_validation_count: int
    derived_vector_pass_count: int


@dataclass(frozen=True, slots=True)
class SnapshotFeatureKernel:
    kernel_version: str
    identity: KernelIdentity
    closed_bar_count: int
    first_timestamp_ns: int
    last_timestamp_ns: int
    latest_sequence: int
    vectors: KernelVectors
    average_range_windows: tuple[AverageRangeWindow, ...]
    volume_windows: tuple[VolumeWindow, ...]
    cumulative_volume: tuple[float, ...]
    cumulative_typical_price_volume: tuple[float, ...]
    cumulative_missing_volume: tuple[int, ...]
    source_snapshot_hash: str
    bar_content_hash: str
    feature_hash: str
    audit: KernelBuildAudit

    def average_range(self, window: int) -> AverageRangeWindow:
        for item in self.average_range_windows:
            if item.window == window:
                return item
        raise SnapshotFeatureKernelError(f"average-range window {window} was not materialized")

    def volume_stats(self, window: int) -> VolumeWindow:
        for item in self.volume_windows:
            if item.window == window:
                return item
        raise SnapshotFeatureKernelError(f"volume window {window} was not materialized")

    def anchored_vwap(self, start_index: int, end_index: int | None = None) -> float | None:
        """Return VWAP for an explicit caller-selected inclusive/exclusive slice.

        M3.1-A intentionally does not choose exchange/session semantics. M3.1-C
        will map a verified NSE session/time window to indices and call this
        primitive. Missing volume anywhere in the requested slice returns None
        rather than a fabricated value.
        """

        start, end = self._normalize_slice(start_index, end_index)
        missing = self.cumulative_missing_volume[end] - self.cumulative_missing_volume[start]
        if missing:
            return None
        volume = self.cumulative_volume[end] - self.cumulative_volume[start]
        if volume <= 0.0:
            return None
        numerator = (
            self.cumulative_typical_price_volume[end]
            - self.cumulative_typical_price_volume[start]
        )
        return numerator / volume

    def high_low(self, start_index: int, end_index: int | None = None) -> tuple[float, float]:
        """Return caller-selected high/low without assigning opening-range semantics."""

        start, end = self._normalize_slice(start_index, end_index)
        return max(self.vectors.highs[start:end]), min(self.vectors.lows[start:end])

    def compact_audit(self) -> dict[str, object]:
        return {
            "kernel_version": self.kernel_version,
            "source_snapshot_hash": self.source_snapshot_hash,
            "bar_content_hash": self.bar_content_hash,
            "feature_hash": self.feature_hash,
            "closed_bar_count": self.closed_bar_count,
            "first_timestamp_ns": self.first_timestamp_ns,
            "last_timestamp_ns": self.last_timestamp_ns,
            "latest_sequence": self.latest_sequence,
            "average_range_windows": [item.window for item in self.average_range_windows],
            "volume_windows": [item.window for item in self.volume_windows],
            "audit": {
                "feature_kernel_build_count": self.audit.feature_kernel_build_count,
                "bar_sort_pass_count": self.audit.bar_sort_pass_count,
                "bar_validation_count": self.audit.bar_validation_count,
                "derived_vector_pass_count": self.audit.derived_vector_pass_count,
            },
        }

    def _normalize_slice(self, start_index: int, end_index: int | None) -> tuple[int, int]:
        end = self.closed_bar_count if end_index is None else end_index
        if start_index < 0 or end < 0 or start_index >= end or end > self.closed_bar_count:
            raise SnapshotFeatureKernelError(
                f"invalid kernel slice [{start_index}:{end}] for {self.closed_bar_count} bars"
            )
        return start_index, end


def build_snapshot_feature_kernel(
    snapshot: ClosedCandleSnapshot,
    *,
    average_range_windows: Iterable[int] = DEFAULT_AVERAGE_RANGE_WINDOWS,
    volume_windows: Iterable[int] = DEFAULT_VOLUME_WINDOWS,
) -> SnapshotFeatureKernel:
    """Build one immutable reusable feature substrate from an approved D2 snapshot."""

    normalized_range_windows = _normalize_windows(average_range_windows, "average_range_windows")
    normalized_volume_windows = _normalize_windows(volume_windows, "volume_windows")
    snapshot_hash = _validate_snapshot_root(snapshot)

    input_bars = tuple(snapshot.closed_ohlcv_bars)
    # One deterministic order pass. D2 is expected to already be canonical. We
    # refuse to silently repair ordering drift because that would hide a broken
    # causal root behind a seemingly valid feature substrate.
    ordered_bars = tuple(sorted(input_bars, key=lambda bar: (bar.timestamp_ns, bar.sequence_number)))
    if ordered_bars != input_bars:
        raise SnapshotFeatureKernelError("D2 closed_ohlcv_bars are not in canonical timestamp/sequence order")

    _validate_bars(snapshot, ordered_bars)
    vectors = _build_vectors(ordered_bars)
    range_series = tuple(
        AverageRangeWindow(
            window=window,
            values=_rolling_average_ranges(vectors.ranges, window),
        )
        for window in normalized_range_windows
    )
    volume_series = tuple(
        _rolling_volume_window(vectors.volumes, window)
        for window in normalized_volume_windows
    )
    cumulative_volume, cumulative_tpv, cumulative_missing = _build_vwap_prefixes(
        vectors.typical_prices,
        vectors.volumes,
    )

    bar_content_hash = _hash_bar_content(ordered_bars)
    feature_hash = _hash_feature_identity(
        snapshot=snapshot,
        snapshot_hash=snapshot_hash,
        bar_content_hash=bar_content_hash,
        average_range_windows=normalized_range_windows,
        volume_windows=normalized_volume_windows,
    )

    return SnapshotFeatureKernel(
        kernel_version=SNAPSHOT_FEATURE_KERNEL_VERSION,
        identity=KernelIdentity(
            symbol=str(snapshot.symbol).upper(),
            timeframe=str(snapshot.timeframe),
            decision_time_ns=int(snapshot.decision_time_ns),
            snapshot_hash=snapshot_hash,
            snapshot_id=str(snapshot.snapshot_id),
        ),
        closed_bar_count=len(ordered_bars),
        first_timestamp_ns=ordered_bars[0].timestamp_ns,
        last_timestamp_ns=ordered_bars[-1].timestamp_ns,
        latest_sequence=ordered_bars[-1].sequence_number,
        vectors=vectors,
        average_range_windows=range_series,
        volume_windows=volume_series,
        cumulative_volume=cumulative_volume,
        cumulative_typical_price_volume=cumulative_tpv,
        cumulative_missing_volume=cumulative_missing,
        source_snapshot_hash=snapshot_hash,
        bar_content_hash=bar_content_hash,
        feature_hash=feature_hash,
        audit=KernelBuildAudit(
            feature_kernel_build_count=1,
            bar_sort_pass_count=1,
            bar_validation_count=len(ordered_bars),
            derived_vector_pass_count=1,
        ),
    )


def _validate_snapshot_root(snapshot: ClosedCandleSnapshot) -> str:
    snapshot_hash = str(snapshot.snapshot_hash).strip().lower()
    if len(snapshot_hash) != 64:
        raise SnapshotFeatureKernelError("D2 snapshot_hash must be a 64-character SHA-256 value")
    try:
        int(snapshot_hash, 16)
    except ValueError as exc:
        raise SnapshotFeatureKernelError("D2 snapshot_hash must be hexadecimal") from exc

    if getattr(snapshot, "stage", None) != "D2_CLOSED_CANDLE_SNAPSHOT":
        raise SnapshotFeatureKernelError("feature kernel accepts only D2 closed-candle snapshots")
    if not bool(getattr(snapshot, "immutable", False)):
        raise SnapshotFeatureKernelError("D2 snapshot must be immutable")
    if not bool(getattr(snapshot, "closed_candle_only", False)):
        raise SnapshotFeatureKernelError("D2 snapshot must be closed-candle-only")
    if not bool(getattr(snapshot, "point_in_time_safe", False)):
        raise SnapshotFeatureKernelError("D2 snapshot must be point-in-time safe")
    if int(snapshot.bar_count) <= 0:
        raise SnapshotFeatureKernelError("D2 snapshot must contain at least one closed bar")
    if int(snapshot.last_bar_close_time_ns) > int(snapshot.decision_time_ns):
        raise SnapshotFeatureKernelError("D2 snapshot contains a bar closing after decision_time_ns")
    return snapshot_hash


def _validate_bars(snapshot: ClosedCandleSnapshot, bars: tuple[CandleBar, ...]) -> None:
    if len(bars) != int(snapshot.bar_count):
        raise SnapshotFeatureKernelError(
            f"D2 bar_count={snapshot.bar_count} does not match closed_ohlcv_bars={len(bars)}"
        )
    if bars[0].timestamp_ns != int(snapshot.first_bar_timestamp_ns):
        raise SnapshotFeatureKernelError("D2 first_bar_timestamp_ns does not match first closed bar")
    if bars[-1].timestamp_ns != int(snapshot.last_bar_timestamp_ns):
        raise SnapshotFeatureKernelError("D2 last_bar_timestamp_ns does not match last closed bar")

    expected_symbol = str(snapshot.symbol).upper()
    expected_timeframe = str(snapshot.timeframe)
    previous_timestamp: int | None = None
    previous_sequence: int | None = None

    for bar in bars:
        if bar.symbol.upper() != expected_symbol:
            raise SnapshotFeatureKernelError("closed bar symbol differs from D2 snapshot symbol")
        if str(bar.timeframe) != expected_timeframe:
            raise SnapshotFeatureKernelError("closed bar timeframe differs from D2 snapshot timeframe")
        if previous_timestamp is not None and bar.timestamp_ns <= previous_timestamp:
            raise SnapshotFeatureKernelError("closed bar timestamps must be strictly increasing")
        if previous_sequence is not None and bar.sequence_number <= previous_sequence:
            raise SnapshotFeatureKernelError("closed bar sequence numbers must be strictly increasing")
        previous_timestamp = bar.timestamp_ns
        previous_sequence = bar.sequence_number

        values = (bar.open, bar.high, bar.low, bar.close)
        if any(not math.isfinite(float(value)) for value in values):
            raise SnapshotFeatureKernelError("closed bar OHLC values must be finite")
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close) or bar.high < bar.low:
            raise SnapshotFeatureKernelError("closed bar violates OHLC geometry")
        if bar.volume is not None:
            if not math.isfinite(float(bar.volume)) or float(bar.volume) < 0.0:
                raise SnapshotFeatureKernelError("closed bar volume must be finite and non-negative")


def _build_vectors(bars: tuple[CandleBar, ...]) -> KernelVectors:
    timestamps: list[int] = []
    sequences: list[int] = []
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[float | None] = []
    ranges: list[float] = []
    bodies: list[float] = []
    typical_prices: list[float] = []
    returns: list[float | None] = []

    previous_close: float | None = None
    for bar in bars:
        open_price = float(bar.open)
        high = float(bar.high)
        low = float(bar.low)
        close = float(bar.close)
        volume = None if bar.volume is None else float(bar.volume)

        timestamps.append(int(bar.timestamp_ns))
        sequences.append(int(bar.sequence_number))
        opens.append(open_price)
        highs.append(high)
        lows.append(low)
        closes.append(close)
        volumes.append(volume)
        ranges.append(max(high - low, 0.0))
        bodies.append(abs(close - open_price))
        typical_prices.append((high + low + close) / 3.0)
        returns.append(None if previous_close is None else (close - previous_close) / previous_close)
        previous_close = close

    return KernelVectors(
        timestamps_ns=tuple(timestamps),
        sequence_numbers=tuple(sequences),
        opens=tuple(opens),
        highs=tuple(highs),
        lows=tuple(lows),
        closes=tuple(closes),
        volumes=tuple(volumes),
        ranges=tuple(ranges),
        bodies=tuple(bodies),
        typical_prices=tuple(typical_prices),
        returns=tuple(returns),
    )


def _rolling_average_ranges(ranges: tuple[float, ...], window: int) -> tuple[float, ...]:
    # Preserve candle-anatomy.v0.15 math exactly: arithmetic mean of candle
    # ranges over an expanding/rolling window, clamped to 1e-9.
    values: list[float] = []
    for index in range(len(ranges)):
        start = max(0, index - window + 1)
        values.append(max(mean(ranges[start : index + 1]), 1e-9))
    return tuple(values)


def _rolling_volume_window(volumes: tuple[float | None, ...], window: int) -> VolumeWindow:
    means: list[float | None] = []
    deviations: list[float | None] = []
    zscores: list[float | None] = []

    for index, current in enumerate(volumes):
        start = max(0, index - window + 1)
        sample = volumes[start : index + 1]
        if current is None or any(item is None for item in sample):
            means.append(None)
            deviations.append(None)
            zscores.append(None)
            continue

        numeric = [float(item) for item in sample if item is not None]
        sample_mean = mean(numeric)
        deviation = pstdev(numeric) if len(numeric) >= 2 else 0.0
        means.append(sample_mean)
        deviations.append(deviation)
        if len(numeric) < 2 or deviation == 0.0:
            zscores.append(0.0)
        else:
            zscores.append((float(current) - sample_mean) / deviation)

    return VolumeWindow(
        window=window,
        means=tuple(means),
        population_stddevs=tuple(deviations),
        zscores=tuple(zscores),
    )


def _build_vwap_prefixes(
    typical_prices: tuple[float, ...],
    volumes: tuple[float | None, ...],
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[int, ...]]:
    cumulative_volume = [0.0]
    cumulative_tpv = [0.0]
    cumulative_missing = [0]

    for typical_price, volume in zip(typical_prices, volumes, strict=True):
        if volume is None:
            cumulative_volume.append(cumulative_volume[-1])
            cumulative_tpv.append(cumulative_tpv[-1])
            cumulative_missing.append(cumulative_missing[-1] + 1)
        else:
            cumulative_volume.append(cumulative_volume[-1] + volume)
            cumulative_tpv.append(cumulative_tpv[-1] + typical_price * volume)
            cumulative_missing.append(cumulative_missing[-1])

    return tuple(cumulative_volume), tuple(cumulative_tpv), tuple(cumulative_missing)


def _hash_bar_content(bars: tuple[CandleBar, ...]) -> str:
    payload = [
        {
            "symbol": bar.symbol.upper(),
            "timeframe": str(bar.timeframe),
            "timestamp_ns": int(bar.timestamp_ns),
            "sequence_number": int(bar.sequence_number),
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": None if bar.volume is None else float(bar.volume),
            "source": str(bar.source),
        }
        for bar in bars
    ]
    return _sha256_json(payload)


def _hash_feature_identity(
    *,
    snapshot: ClosedCandleSnapshot,
    snapshot_hash: str,
    bar_content_hash: str,
    average_range_windows: tuple[int, ...],
    volume_windows: tuple[int, ...],
) -> str:
    return _sha256_json(
        {
            "kernel_version": SNAPSHOT_FEATURE_KERNEL_VERSION,
            "source_snapshot_hash": snapshot_hash,
            "bar_content_hash": bar_content_hash,
            "symbol": str(snapshot.symbol).upper(),
            "timeframe": str(snapshot.timeframe),
            "decision_time_ns": int(snapshot.decision_time_ns),
            "average_range_windows": list(average_range_windows),
            "volume_windows": list(volume_windows),
        }
    )


def _normalize_windows(values: Iterable[int], name: str) -> tuple[int, ...]:
    normalized: set[int] = set()
    for value in values:
        if isinstance(value, bool):
            raise SnapshotFeatureKernelError(f"{name} must contain integer window sizes")
        try:
            window = int(value)
        except (TypeError, ValueError) as exc:
            raise SnapshotFeatureKernelError(f"{name} must contain integer window sizes") from exc
        if window <= 0 or window > MAX_WINDOW:
            raise SnapshotFeatureKernelError(f"{name} window must be between 1 and {MAX_WINDOW}")
        normalized.add(window)
    if not normalized:
        raise SnapshotFeatureKernelError(f"{name} must contain at least one window")
    return tuple(sorted(normalized))


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
