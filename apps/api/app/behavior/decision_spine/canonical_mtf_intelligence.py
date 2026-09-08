from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from ...models import (
    CandleSeries,
    ClosedCandleSnapshot,
    HTFConfirmationRequest,
    PaperGuidanceMtfEvidence,
    PaperGuidanceRequest,
    TimeframeValue,
)
from ..context_engines import analyze_htf_confirmation
from ..point_in_time_guard import timeframe_duration_ns


MTF_CONFIRMATION_VERSION = "mtf-confirmation.v2"
MTF_SERIES_HASH_VERSION = "mtf-closed-series-hash.v1"

MtfAvailability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE"]
MtfQuality = Literal["GOOD", "WARN", "UNAVAILABLE"]
MtfBias = Literal["bullish", "bearish", "neutral", "unavailable"]


class CanonicalMtfRecord(BaseModel):
    timeframe: TimeframeValue
    source_snapshot_hash: str | None = None
    source_series_hash: str | None = None
    last_closed_ts: int | None = None
    last_closed_sequence: int | None = None
    bars_used: int = Field(ge=0)
    availability: MtfAvailability
    bias: MtfBias = "unavailable"
    confirmed: bool = False
    quality: MtfQuality
    reason_code: str
    reason: str
    # Audit-only. These fields describe rejected caller input and are excluded
    # from mtf_hash, so a future/incomplete bar can never become a causal fact.
    excluded_incomplete_bars: int = Field(default=0, ge=0)
    future_bar_blocked: bool = False
    duplicate_timeframe: bool = False
    symbol_identity_match: bool = True
    timeframe_identity_match: bool = True
    source_clock_monotonic: bool = True
    volume_quality: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE"] = "UNAVAILABLE"
    official_exchange_calendar_verified: bool = False
    corporate_action_adjustment_verified: bool = False
    freshness_verified: bool = False
    calculation_version: str = MTF_CONFIRMATION_VERSION
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False


class CanonicalMtfIntelligence(PaperGuidanceMtfEvidence):
    calculation_version: str = MTF_CONFIRMATION_VERSION
    source_snapshot_hash: str
    records: list[CanonicalMtfRecord] = Field(default_factory=list)
    mtf_hash: str
    canonical_mtf_intelligence: bool = True
    canonical_status: Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE"]
    calculation_audit: dict[str, int | bool]
    epistemic: dict[str, Any]
    used_for_probability: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False


FreezeSnapshot = Callable[[PaperGuidanceRequest], ClosedCandleSnapshot]
IndicatorRuntime = Callable[..., tuple[dict[str, object], list[dict[str, object]]]]


def build_canonical_mtf_intelligence(
    request: PaperGuidanceRequest,
    primary_snapshot: ClosedCandleSnapshot,
    *,
    freeze_snapshot: FreezeSnapshot,
    indicator_runtime: IndicatorRuntime | None = None,
    default_indicator_ids: list[str] | None = None,
) -> CanonicalMtfIntelligence:
    """Build one bounded, PIT-safe MTF world-state from D2-closed bars only.

    The compatibility fields inherited from ``PaperGuidanceMtfEvidence`` keep
    locked D6 semantics stable. Canonical records add explicit causality and
    missingness; the composer does not vote or set a band.
    """

    supplied_timeframes = sorted({series.timeframe for series in request.higher_timeframe_series})
    duplicate_counts = Counter(series.timeframe for series in request.higher_timeframe_series)
    duplicate_timeframes = {tf for tf, count in duplicate_counts.items() if count > 1}

    records: list[CanonicalMtfRecord] = []
    snapshots: dict[str, ClosedCandleSnapshot] = {}
    closed_series: dict[str, CandleSeries] = {}
    reasons: list[str] = []

    for series in sorted(
        request.higher_timeframe_series,
        key=lambda item: (item.timeframe, item.symbol.upper(), item.snapshot_id or ""),
    ):
        timeframe = series.timeframe
        if timeframe in duplicate_timeframes:
            continue
        record, snapshot, safe_series = _build_record(
            request,
            primary_snapshot,
            series,
            freeze_snapshot=freeze_snapshot,
        )
        records.append(record)
        if snapshot is not None and safe_series is not None:
            snapshots[timeframe] = snapshot
            closed_series[timeframe] = safe_series
        if record.availability != "AVAILABLE":
            reasons.append(f"{timeframe}: {record.reason}")

    for timeframe in sorted(duplicate_timeframes):
        records.append(
            CanonicalMtfRecord(
                timeframe=timeframe,
                availability="UNAVAILABLE",
                quality="UNAVAILABLE",
                reason_code="DUPLICATE_TIMEFRAME",
                reason=(
                    f"Multiple higher-timeframe series were supplied for {timeframe}; "
                    "no arbitrary series was selected."
                ),
                duplicate_timeframe=True,
            )
        )
        reasons.append(
            f"{timeframe}: duplicate higher-timeframe inputs were withheld instead of overwriting one another."
        )

    usable_timeframes = sorted(snapshots)
    missing_required = sorted(set(request.required_higher_timeframes) - set(usable_timeframes))

    confirmation = analyze_htf_confirmation(
        HTFConfirmationRequest(
            symbol=primary_snapshot.symbol,
            decision_time_ns=primary_snapshot.decision_time_ns,
            direction=request.direction,
            higher_timeframe_series=[closed_series[tf] for tf in usable_timeframes],
        )
    )
    confirmation_by_tf = {record.timeframe: record for record in confirmation.records}
    canonical_records: list[CanonicalMtfRecord] = []
    for record in records:
        compatible = confirmation_by_tf.get(record.timeframe)
        if compatible is None or record.availability != "AVAILABLE":
            canonical_records.append(record)
            continue
        canonical_records.append(
            record.model_copy(
                update={
                    "bias": compatible.bias,
                    "confirmed": compatible.confirmed,
                    "reason": _join_reason(record.reason, compatible.reason),
                }
            )
        )
    records = sorted(canonical_records, key=lambda item: item.timeframe)

    reasons.extend(confirmation.reasons)
    if missing_required:
        reasons.append(
            f"Required higher-timeframe evidence is missing: {', '.join(missing_required)}."
        )

    indicator_runtime_by_timeframe: dict[str, dict[str, Any]] = {}
    if indicator_runtime is not None:
        selected = (
            sorted(set(request.indicator_ids))
            if request.indicator_ids
            else sorted(set(default_indicator_ids or []))
        )
        for timeframe in usable_timeframes:
            snapshot = snapshots[timeframe]
            candles = [
                {
                    "event_time": _iso_from_ns(bar.timestamp_ns),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in snapshot.closed_ohlcv_bars
            ]
            try:
                outputs, telemetry = indicator_runtime(
                    candles,
                    selected,
                    source_snapshot_hash=snapshot.snapshot_hash,
                    source_timeframe=timeframe,
                )
                indicator_runtime_by_timeframe[timeframe] = {
                    "source_snapshot_hash": snapshot.snapshot_hash,
                    "source_series_hash": _closed_series_hash(closed_series[timeframe]),
                    "source_bar_count": snapshot.bar_count,
                    "indicator_ids": selected,
                    "computed_count": len(outputs),
                    "telemetry": telemetry,
                    "used_for_final_vote": False,
                }
            except Exception as exc:
                indicator_runtime_by_timeframe[timeframe] = {
                    "source_snapshot_hash": snapshot.snapshot_hash,
                    "source_series_hash": _closed_series_hash(closed_series[timeframe]),
                    "source_bar_count": snapshot.bar_count,
                    "indicator_ids": selected,
                    "computed_count": 0,
                    "telemetry": [],
                    "used_for_final_vote": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                reasons.append(
                    f"{timeframe} indicator runtime degraded safely: {type(exc).__name__}: {exc}"
                )

    deterministic = {
        "calculation_version": MTF_CONFIRMATION_VERSION,
        "source_snapshot_hash": primary_snapshot.snapshot_hash,
        "decision_time_ns": primary_snapshot.decision_time_ns,
        "required_timeframes": sorted(request.required_higher_timeframes),
        # Only D2-causal fields participate. Rejected future/incomplete caller
        # bars remain auditable on the record but cannot perturb this hash.
        "records": [_causal_record_payload(record) for record in records],
    }
    mtf_hash = _stable_hash(deterministic)

    unavailable_count = sum(record.availability == "UNAVAILABLE" for record in records)
    degraded_count = sum(record.availability == "DEGRADED" for record in records)
    canonical_status: Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE"]
    if records and unavailable_count == len(records):
        canonical_status = "UNAVAILABLE"
    elif missing_required or unavailable_count or degraded_count:
        canonical_status = "DEGRADED"
    else:
        canonical_status = "AVAILABLE"

    epistemic = {
        "availability": canonical_status,
        "quality": "GOOD" if canonical_status == "AVAILABLE" else "WARN",
        "closed_candle_only": True,
        "official_exchange_calendar_verified": False,
        "corporate_action_adjustment_verified": False,
        "freshness_verified": False,
        "warnings": [
            "Official exchange holiday/special-session calendar provenance is not wired into M3.1-E.",
            "Corporate-action adjustment provenance is not wired into M3.1-E.",
            "External provider freshness/clock-skew proof is not wired into M3.1-E.",
        ],
    }

    return CanonicalMtfIntelligence(
        required_timeframes=request.required_higher_timeframes,
        supplied_timeframes=supplied_timeframes,
        usable_timeframes=usable_timeframes,
        missing_required_timeframes=missing_required,
        snapshot_hashes={tf: snapshots[tf].snapshot_hash for tf in usable_timeframes},
        indicator_runtime_by_timeframe=indicator_runtime_by_timeframe,
        confirmed=confirmation.confirmed,
        blocks_promotion=bool(missing_required) or confirmation.blocks_trade,
        reasons=_unique(reasons),
        source_snapshot_hash=primary_snapshot.snapshot_hash,
        records=records,
        mtf_hash=mtf_hash,
        canonical_status=canonical_status,
        calculation_audit={
            "mtf_builder_count": 1,
            "series_partition_count": len(request.higher_timeframe_series),
            "confirmation_compute_count": 1,
            "duplicate_timeframe_count": len(duplicate_timeframes),
            "future_or_incomplete_bar_authority_count": 0,
        },
        epistemic=epistemic,
    )


def _build_record(
    request: PaperGuidanceRequest,
    primary_snapshot: ClosedCandleSnapshot,
    series: CandleSeries,
    *,
    freeze_snapshot: FreezeSnapshot,
) -> tuple[CanonicalMtfRecord, ClosedCandleSnapshot | None, CandleSeries | None]:
    if series.symbol.upper() != primary_snapshot.symbol.upper():
        return (
            CanonicalMtfRecord(
                timeframe=series.timeframe,
                availability="UNAVAILABLE",
                quality="UNAVAILABLE",
                reason_code="SYMBOL_IDENTITY_MISMATCH",
                reason=(
                    f"Series symbol {series.symbol.upper()} does not match primary D2 symbol "
                    f"{primary_snapshot.symbol.upper()}."
                ),
                symbol_identity_match=False,
            ),
            None,
            None,
        )

    duration_ns = timeframe_duration_ns(series.timeframe)
    eligible = [
        bar
        for bar in series.bars
        if bar.timestamp_ns + duration_ns <= primary_snapshot.decision_time_ns
    ]
    excluded = len(series.bars) - len(eligible)
    future_blocked = any(
        bar.timestamp_ns > primary_snapshot.decision_time_ns for bar in series.bars
    )

    if not eligible:
        code = "HTF_NOT_CLOSED" if series.bars else "NO_HTF_BARS"
        return (
            CanonicalMtfRecord(
                timeframe=series.timeframe,
                availability="UNAVAILABLE",
                quality="UNAVAILABLE",
                reason_code=code,
                reason=(
                    f"No {series.timeframe} bar is fully closed at decision_time_ns="
                    f"{primary_snapshot.decision_time_ns}."
                ),
                excluded_incomplete_bars=excluded,
                future_bar_blocked=future_blocked,
                source_clock_monotonic=_bars_strictly_increasing(series.bars),
                volume_quality="UNAVAILABLE",
            ),
            None,
            None,
        )

    # Only eligible closed bars may decide source validity. A malformed future
    # bar is audit input, never authority over the already-known closed state.
    if not _bars_strictly_increasing(eligible):
        return (
            CanonicalMtfRecord(
                timeframe=series.timeframe,
                availability="UNAVAILABLE",
                quality="UNAVAILABLE",
                reason_code="NON_MONOTONIC_SOURCE_CLOCK",
                reason="Closed higher-timeframe timestamps/sequence numbers are not strictly increasing.",
                excluded_incomplete_bars=excluded,
                future_bar_blocked=future_blocked,
                source_clock_monotonic=False,
                volume_quality=_volume_quality(eligible),
            ),
            None,
            None,
        )

    safe_series = CandleSeries(
        symbol=series.symbol,
        timeframe=series.timeframe,
        bars=eligible,
        snapshot_id=series.snapshot_id,
        schema_version=series.schema_version,
    )
    try:
        mtf_request = PaperGuidanceRequest(
            symbol=primary_snapshot.symbol,
            timeframe=series.timeframe,
            series=safe_series,
            decision_time_ns=primary_snapshot.decision_time_ns,
            direction=request.direction,
        )
        snapshot = freeze_snapshot(mtf_request)
    except Exception as exc:
        return (
            CanonicalMtfRecord(
                timeframe=series.timeframe,
                availability="UNAVAILABLE",
                quality="UNAVAILABLE",
                reason_code="D2_FREEZE_FAILED",
                reason=f"Closed-candle snapshot freeze failed: {type(exc).__name__}: {exc}",
                excluded_incomplete_bars=excluded,
                future_bar_blocked=future_blocked,
                source_clock_monotonic=True,
                volume_quality=_volume_quality(eligible),
            ),
            None,
            None,
        )

    last = snapshot.closed_ohlcv_bars[-1]
    return (
        CanonicalMtfRecord(
            timeframe=series.timeframe,
            source_snapshot_hash=snapshot.snapshot_hash,
            source_series_hash=_closed_series_hash(safe_series),
            last_closed_ts=last.timestamp_ns,
            last_closed_sequence=last.sequence_number,
            bars_used=snapshot.bar_count,
            availability="AVAILABLE",
            bias="unavailable",
            confirmed=False,
            quality="GOOD",
            reason_code="AVAILABLE_CLOSED_ONLY",
            reason=(
                f"{snapshot.bar_count} fully closed {series.timeframe} bars are D2-safe; "
                "incomplete/future supplied bars have zero authority."
            ),
            excluded_incomplete_bars=excluded,
            future_bar_blocked=future_blocked,
            source_clock_monotonic=True,
            volume_quality=_volume_quality(snapshot.closed_ohlcv_bars),
        ),
        snapshot,
        safe_series,
    )


def _bars_strictly_increasing(bars) -> bool:
    return all(
        current.timestamp_ns > previous.timestamp_ns
        and current.sequence_number > previous.sequence_number
        for previous, current in zip(bars, bars[1:])
    )


def _volume_quality(bars) -> Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE"]:
    if not bars:
        return "UNAVAILABLE"
    valid = sum(bar.volume is not None and float(bar.volume) > 0.0 for bar in bars)
    if valid == len(bars):
        return "AVAILABLE"
    if valid:
        return "PARTIAL"
    return "UNAVAILABLE"


def _closed_series_hash(series: CandleSeries) -> str:
    return _stable_hash(
        {
            "version": MTF_SERIES_HASH_VERSION,
            "symbol": series.symbol.upper(),
            "timeframe": series.timeframe,
            "schema_version": series.schema_version,
            "bars": [bar.model_dump(mode="json") for bar in series.bars],
        }
    )


def _causal_record_payload(record: CanonicalMtfRecord) -> dict[str, object]:
    return {
        "timeframe": record.timeframe,
        "source_snapshot_hash": record.source_snapshot_hash,
        "source_series_hash": record.source_series_hash,
        "last_closed_ts": record.last_closed_ts,
        "last_closed_sequence": record.last_closed_sequence,
        "bars_used": record.bars_used,
        "availability": record.availability,
        "bias": record.bias,
        "confirmed": record.confirmed,
        "quality": record.quality,
        "reason_code": record.reason_code,
        "duplicate_timeframe": record.duplicate_timeframe,
        "symbol_identity_match": record.symbol_identity_match,
        "timeframe_identity_match": record.timeframe_identity_match,
        "source_clock_monotonic": record.source_clock_monotonic,
        "volume_quality": record.volume_quality,
        "calculation_version": record.calculation_version,
        "used_for_probability": False,
        "may_set_final_band": False,
        "may_execute": False,
    }


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _iso_from_ns(value: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc).isoformat()


def _join_reason(left: str, right: str) -> str:
    if not right or right in left:
        return left
    return f"{left} {right}"


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
