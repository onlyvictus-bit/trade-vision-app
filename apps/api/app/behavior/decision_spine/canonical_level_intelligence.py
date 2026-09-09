from __future__ import annotations

"""Canonical M3.1-C level intelligence.

This module is a deterministic sensory/world-state calculator, not a trading
predictor. It consumes one already-approved D2 SnapshotFeatureKernel and one
legacy-compatible level request. Canonical facts are session-aware and
point-in-time bounded; a separate compatibility projection preserves the
pre-M3.1 D6 inputs until D6 migration is explicitly authorized.
"""

from datetime import date, datetime, time, timezone
import hashlib
import json
import math
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from ...models import CandleBar, VwapOrbCprContextRequest
from ..point_in_time_guard import timeframe_duration_ns
from .snapshot_feature_kernel import SnapshotFeatureKernel


LEVEL_INTELLIGENCE_VERSION = "canonical-level-intelligence.v1"
SESSION_SEMANTICS_VERSION = "nse-cash-regular-session.v1"
NSE_TIMEZONE_NAME = "Asia/Kolkata"
NSE_TIMEZONE = ZoneInfo(NSE_TIMEZONE_NAME)
NSE_SESSION_OPEN = time(9, 15)
NSE_SESSION_CLOSE = time(15, 30)
OR_WINDOWS_MINUTES: tuple[int, ...] = (5, 15, 30)

Availability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE", "PENDING"]
LevelState = Literal[
    "above",
    "below",
    "inside",
    "reclaiming",
    "rejecting",
    "breaking_up",
    "breaking_down",
    "unknown",
]


class CanonicalLevelIntelligenceError(ValueError):
    """Raised when canonical level identity or causality cannot be established."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SessionIdentity(_FrozenModel):
    semantics_version: str = SESSION_SEMANTICS_VERSION
    exchange: str = "NSE"
    timezone: str = NSE_TIMEZONE_NAME
    session_id: str
    session_date: str
    open_time_local: str = "09:15:00"
    close_time_local: str = "15:30:00"
    open_time_ns: int
    close_time_ns: int
    first_bar_timestamp_ns: int
    last_bar_timestamp_ns: int
    source_bar_count: int = Field(ge=1)
    starts_at_session_open: bool
    contiguous_from_session_open: bool


class CanonicalVwap(_FrozenModel):
    status: Availability
    value: float | None
    state: LevelState
    band_1_upper: float | None
    band_1_lower: float | None
    band_2_upper: float | None
    band_2_lower: float | None
    band_3_upper: float | None
    band_3_lower: float | None
    weighted_stddev: float | None
    source_bar_count: int
    missing_volume_count: int
    reason: str | None = None


class OpeningRange(_FrozenModel):
    name: Literal["OR5", "OR15", "OR30"]
    minutes: Literal[5, 15, 30]
    status: Availability
    high: float | None
    low: float | None
    state: LevelState
    window_start_ns: int
    window_end_ns: int
    required_bar_count: int | None
    source_bar_count: int
    reason: str | None = None


class PreviousSessionLevels(_FrozenModel):
    status: Availability
    session_id: str | None
    high: float | None
    low: float | None
    close: float | None
    source_bar_count: int
    first_bar_timestamp_ns: int | None
    last_bar_timestamp_ns: int | None
    source_hash: str | None
    reason: str | None = None


class CanonicalCpr(_FrozenModel):
    status: Availability
    pivot: float | None
    bc: float | None
    tc: float | None
    state: LevelState
    source_session_id: str | None
    source_hash: str | None
    reason: str | None = None


class CanonicalLevelProvenance(_FrozenModel):
    source_snapshot_hash: str
    source_feature_kernel_hash: str
    source_feature_kernel_version: str
    session_semantics_version: str = SESSION_SEMANTICS_VERSION
    canonical_level_hash: str


class CanonicalLevelCalculationAudit(_FrozenModel):
    canonical_level_compute_count: int = 1
    feature_kernel_reused: bool = True
    session_partition_pass_count: int = 1
    canonical_vwap_compute_count: int = 1
    opening_range_compute_count: int = 3
    previous_session_compute_count: int = 1
    compatibility_projection_compute_count: int = 1


class CanonicalLevelIntelligenceResult(_FrozenModel):
    # Canonical M3.1-C evidence.
    context_version: str = LEVEL_INTELLIGENCE_VERSION
    calculation_version: str = LEVEL_INTELLIGENCE_VERSION
    symbol: str
    timeframe: str
    latest_close: float | None
    session: SessionIdentity
    session_vwap: CanonicalVwap
    opening_ranges: tuple[OpeningRange, OpeningRange, OpeningRange]
    previous_session: PreviousSessionLevels
    cpr: CanonicalCpr
    canonical_pdh_state: LevelState
    canonical_pdl_state: LevelState
    canonical_support_resistance_flags: tuple[str, ...]
    canonical_level_respect_score: float = Field(ge=0.0, le=1.0)
    canonical_blocks_trade: bool
    missing_reasons: tuple[str, ...]
    provenance: CanonicalLevelProvenance
    calculation_audit: CanonicalLevelCalculationAudit

    # Compatibility projection consumed by the unchanged legacy D6 helpers.
    # These fields intentionally preserve the pre-M3.1 contract until M4.
    calculated_vwap: float | None
    price_vs_vwap_pct: float | None
    vwap_state: LevelState
    opening_range_high: float | None
    opening_range_low: float | None
    opening_range_state: LevelState
    cpr_pivot: float | None
    cpr_bc: float | None
    cpr_tc: float | None
    cpr_state: LevelState
    pdh_state: LevelState
    pdl_state: LevelState
    vpd_state: str
    support_resistance_flags: list[str]
    level_respect_score: float = Field(ge=0.0, le=1.0)
    blocks_trade: bool
    reasons: list[str]

    def opening_range(self, minutes: int) -> OpeningRange:
        for item in self.opening_ranges:
            if item.minutes == minutes:
                return item
        raise KeyError(minutes)

    def receipt_summary(self) -> dict[str, object]:
        """Bounded canonical evidence suitable for DecisionContext/receipt payloads."""

        return {
            "latest": {
                "close": self.latest_close,
                "vwap_state": self.session_vwap.state,
                "or15_state": self.opening_range(15).state,
                "pdh_state": self.canonical_pdh_state,
                "pdl_state": self.canonical_pdl_state,
                "cpr_state": self.cpr.state,
            },
            "session": self.session.model_dump(mode="json"),
            "vwap": self.session_vwap.model_dump(mode="json"),
            "opening_ranges": {
                item.name: item.model_dump(mode="json") for item in self.opening_ranges
            },
            "previous_session": self.previous_session.model_dump(mode="json"),
            "cpr": self.cpr.model_dump(mode="json"),
            "quality": {
                "available": True,
                "missing_reasons": list(self.missing_reasons),
                "canonical_level_respect_score": self.canonical_level_respect_score,
                "canonical_blocks_trade": self.canonical_blocks_trade,
                "support_resistance_flags": list(self.canonical_support_resistance_flags),
                "calculation_version": self.calculation_version,
            },
            "provenance": self.provenance.model_dump(mode="json"),
            "calculation_audit": self.calculation_audit.model_dump(mode="json"),
            "compatibility": {
                "legacy_d6_projection_preserved": True,
                "legacy_opening_range_semantics": "first-three-closed-bars",
                "legacy_vwap_semantics": "all-supplied-closed-bars-skip-missing-volume",
            },
            "used_for_probability": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }


def build_canonical_level_intelligence(
    request: VwapOrbCprContextRequest,
    *,
    feature_kernel: SnapshotFeatureKernel,
) -> CanonicalLevelIntelligenceResult:
    """Build one canonical, session-aware level world-state from the D2 kernel."""

    _validate_identity(request, feature_kernel)
    duration_ns = timeframe_duration_ns(request.series.timeframe)
    decision_time_ns = int(request.decision_time_ns or feature_kernel.identity.decision_time_ns)
    if decision_time_ns != feature_kernel.identity.decision_time_ns:
        raise CanonicalLevelIntelligenceError("level request decision_time_ns must equal D2 kernel decision_time_ns")

    sessions = _partition_regular_sessions(feature_kernel, duration_ns, decision_time_ns)
    if not sessions:
        raise CanonicalLevelIntelligenceError("no regular NSE session bars are present in the D2 snapshot")

    session_id = sorted(sessions)[-1]
    current_indices = sessions[session_id]
    session = _session_identity(session_id, current_indices, feature_kernel, duration_ns)
    latest_index = current_indices[-1]
    latest_bar = request.series.bars[latest_index]

    session_vwap = _canonical_vwap(feature_kernel, current_indices, session, duration_ns)
    opening_ranges = tuple(
        _opening_range(feature_kernel, current_indices, session, duration_ns, decision_time_ns, minutes)
        for minutes in OR_WINDOWS_MINUTES
    )
    previous_session = _previous_session_levels(
        feature_kernel,
        sessions,
        current_session_id=session_id,
        duration_ns=duration_ns,
    )
    cpr = _canonical_cpr(previous_session, latest_bar.close)
    canonical_pdh_state = _state_against_level(
        latest_bar,
        _previous_bar(request.series.bars, latest_index),
        previous_session.high,
    )
    canonical_pdl_state = _state_against_level(
        latest_bar,
        _previous_bar(request.series.bars, latest_index),
        previous_session.low,
    )
    or15 = next(item for item in opening_ranges if item.minutes == 15)
    canonical_flags = _canonical_flags(
        latest=latest_bar,
        vwap=session_vwap.value,
        or_high=or15.high if or15.status == "AVAILABLE" else None,
        or_low=or15.low if or15.status == "AVAILABLE" else None,
        pdh=previous_session.high,
        pdl=previous_session.low,
        cpr=cpr,
    )
    canonical_score = _level_respect_score(
        session_vwap.state,
        or15.state,
        cpr.state,
        canonical_pdh_state,
        canonical_pdl_state,
        list(canonical_flags),
    )
    canonical_blocks = any(
        flag in canonical_flags
        for flag in ("rejecting_pdh", "failed_or15_breakout", "below_session_vwap")
    )

    missing_reasons = _missing_reasons(session_vwap, opening_ranges, previous_session, cpr)
    compatibility = _legacy_projection(request, feature_kernel)

    canonical_without_hash = {
        "version": LEVEL_INTELLIGENCE_VERSION,
        "symbol": feature_kernel.identity.symbol,
        "timeframe": feature_kernel.identity.timeframe,
        "decision_time_ns": decision_time_ns,
        "session": session.model_dump(mode="json"),
        "session_vwap": session_vwap.model_dump(mode="json"),
        "opening_ranges": [item.model_dump(mode="json") for item in opening_ranges],
        "previous_session": previous_session.model_dump(mode="json"),
        "cpr": cpr.model_dump(mode="json"),
        "canonical_pdh_state": canonical_pdh_state,
        "canonical_pdl_state": canonical_pdl_state,
        "canonical_flags": list(canonical_flags),
        "canonical_level_respect_score": round(canonical_score, 4),
        "canonical_blocks_trade": canonical_blocks,
        "missing_reasons": list(missing_reasons),
        "source_snapshot_hash": feature_kernel.source_snapshot_hash,
        "source_feature_kernel_hash": feature_kernel.feature_hash,
    }
    level_hash = _hash_payload(canonical_without_hash)

    return CanonicalLevelIntelligenceResult(
        symbol=feature_kernel.identity.symbol,
        timeframe=feature_kernel.identity.timeframe,
        latest_close=float(latest_bar.close),
        session=session,
        session_vwap=session_vwap,
        opening_ranges=opening_ranges,  # type: ignore[arg-type]
        previous_session=previous_session,
        cpr=cpr,
        canonical_pdh_state=canonical_pdh_state,
        canonical_pdl_state=canonical_pdl_state,
        canonical_support_resistance_flags=canonical_flags,
        canonical_level_respect_score=round(canonical_score, 4),
        canonical_blocks_trade=canonical_blocks,
        missing_reasons=missing_reasons,
        provenance=CanonicalLevelProvenance(
            source_snapshot_hash=feature_kernel.source_snapshot_hash,
            source_feature_kernel_hash=feature_kernel.feature_hash,
            source_feature_kernel_version=feature_kernel.kernel_version,
            canonical_level_hash=level_hash,
        ),
        calculation_audit=CanonicalLevelCalculationAudit(),
        **compatibility,
    )


def _validate_identity(request: VwapOrbCprContextRequest, kernel: SnapshotFeatureKernel) -> None:
    if request.series.symbol.upper() != kernel.identity.symbol:
        raise CanonicalLevelIntelligenceError("level request symbol differs from D2 feature kernel")
    if str(request.series.timeframe) != kernel.identity.timeframe:
        raise CanonicalLevelIntelligenceError("level request timeframe differs from D2 feature kernel")
    if len(request.series.bars) != kernel.closed_bar_count:
        raise CanonicalLevelIntelligenceError("level request bar count differs from D2 feature kernel")
    if tuple(bar.timestamp_ns for bar in request.series.bars) != kernel.vectors.timestamps_ns:
        raise CanonicalLevelIntelligenceError("level request timestamps differ from D2 feature kernel")
    if tuple(bar.sequence_number for bar in request.series.bars) != kernel.vectors.sequence_numbers:
        raise CanonicalLevelIntelligenceError("level request sequence identity differs from D2 feature kernel")


def _partition_regular_sessions(
    kernel: SnapshotFeatureKernel,
    duration_ns: int,
    decision_time_ns: int,
) -> dict[str, list[int]]:
    sessions: dict[str, list[int]] = {}
    for index, timestamp_ns in enumerate(kernel.vectors.timestamps_ns):
        close_ns = timestamp_ns + duration_ns
        if close_ns > decision_time_ns:
            raise CanonicalLevelIntelligenceError("D2 kernel contains a bar closing after decision time")
        local_open = _local_datetime(timestamp_ns)
        local_close = _local_datetime(close_ns)
        if local_open.date() != local_close.date():
            continue
        if local_open.time() < NSE_SESSION_OPEN or local_close.time() > NSE_SESSION_CLOSE:
            continue
        session_id = local_open.date().isoformat()
        sessions.setdefault(session_id, []).append(index)
    return sessions


def _session_identity(
    session_id: str,
    indices: list[int],
    kernel: SnapshotFeatureKernel,
    duration_ns: int,
) -> SessionIdentity:
    session_date = date.fromisoformat(session_id)
    open_ns, close_ns = _session_bounds_ns(session_date)
    if indices != list(range(indices[0], indices[-1] + 1)):
        raise CanonicalLevelIntelligenceError("current-session bars are not contiguous in D2 ordering")
    starts_at_open = kernel.vectors.timestamps_ns[indices[0]] == open_ns
    contiguous = starts_at_open and all(
        kernel.vectors.timestamps_ns[index] == open_ns + offset * duration_ns
        for offset, index in enumerate(indices)
    )
    return SessionIdentity(
        session_id=session_id,
        session_date=session_id,
        open_time_ns=open_ns,
        close_time_ns=close_ns,
        first_bar_timestamp_ns=kernel.vectors.timestamps_ns[indices[0]],
        last_bar_timestamp_ns=kernel.vectors.timestamps_ns[indices[-1]],
        source_bar_count=len(indices),
        starts_at_session_open=starts_at_open,
        contiguous_from_session_open=contiguous,
    )


def _canonical_vwap(
    kernel: SnapshotFeatureKernel,
    indices: list[int],
    session: SessionIdentity,
    duration_ns: int,
) -> CanonicalVwap:
    missing_volume = sum(kernel.vectors.volumes[index] is None for index in indices)
    latest = _kernel_bar(kernel, indices[-1])
    if not session.starts_at_session_open:
        return CanonicalVwap(
            status="UNAVAILABLE",
            value=None,
            state="unknown",
            band_1_upper=None,
            band_1_lower=None,
            band_2_upper=None,
            band_2_lower=None,
            band_3_upper=None,
            band_3_lower=None,
            weighted_stddev=None,
            source_bar_count=len(indices),
            missing_volume_count=missing_volume,
            reason="Current-session history does not begin at the explicit 09:15 NSE session open.",
        )
    if not session.contiguous_from_session_open:
        return CanonicalVwap(
            status="UNAVAILABLE",
            value=None,
            state="unknown",
            band_1_upper=None,
            band_1_lower=None,
            band_2_upper=None,
            band_2_lower=None,
            band_3_upper=None,
            band_3_lower=None,
            weighted_stddev=None,
            source_bar_count=len(indices),
            missing_volume_count=missing_volume,
            reason="Current-session history has a timestamp gap; session VWAP would be incomplete.",
        )
    if missing_volume:
        return CanonicalVwap(
            status="UNAVAILABLE",
            value=None,
            state="unknown",
            band_1_upper=None,
            band_1_lower=None,
            band_2_upper=None,
            band_2_lower=None,
            band_3_upper=None,
            band_3_lower=None,
            weighted_stddev=None,
            source_bar_count=len(indices),
            missing_volume_count=missing_volume,
            reason="At least one current-session bar has missing volume; missing volume is not treated as zero.",
        )

    start = indices[0]
    end = indices[-1] + 1
    value = kernel.anchored_vwap(start, end)
    if value is None:
        return CanonicalVwap(
            status="UNAVAILABLE",
            value=None,
            state="unknown",
            band_1_upper=None,
            band_1_lower=None,
            band_2_upper=None,
            band_2_lower=None,
            band_3_upper=None,
            band_3_lower=None,
            weighted_stddev=None,
            source_bar_count=len(indices),
            missing_volume_count=missing_volume,
            reason="Session VWAP denominator is zero or unavailable.",
        )
    deviation = _weighted_stddev(kernel, indices, value)
    rounded = round(value, 4)
    rounded_dev = round(deviation, 4)
    return CanonicalVwap(
        status="AVAILABLE",
        value=rounded,
        state=_state_against_level(latest, _kernel_bar(kernel, indices[-2]) if len(indices) > 1 else None, rounded),
        band_1_upper=round(value + deviation, 4),
        band_1_lower=round(value - deviation, 4),
        band_2_upper=round(value + 2.0 * deviation, 4),
        band_2_lower=round(value - 2.0 * deviation, 4),
        band_3_upper=round(value + 3.0 * deviation, 4),
        band_3_lower=round(value - 3.0 * deviation, 4),
        weighted_stddev=rounded_dev,
        source_bar_count=len(indices),
        missing_volume_count=0,
    )


def _weighted_stddev(kernel: SnapshotFeatureKernel, indices: list[int], vwap: float) -> float:
    total_volume = sum(float(kernel.vectors.volumes[index] or 0.0) for index in indices)
    if total_volume <= 0.0:
        return 0.0
    variance = sum(
        float(kernel.vectors.volumes[index] or 0.0)
        * (float(kernel.vectors.typical_prices[index]) - vwap) ** 2
        for index in indices
    ) / total_volume
    return math.sqrt(max(variance, 0.0))


def _opening_range(
    kernel: SnapshotFeatureKernel,
    current_indices: list[int],
    session: SessionIdentity,
    duration_ns: int,
    decision_time_ns: int,
    minutes: int,
) -> OpeningRange:
    window_ns = minutes * 60 * 1_000_000_000
    window_end = session.open_time_ns + window_ns
    name = f"OR{minutes}"
    if duration_ns > window_ns or window_ns % duration_ns:
        return OpeningRange(
            name=name,  # type: ignore[arg-type]
            minutes=minutes,  # type: ignore[arg-type]
            status="UNAVAILABLE",
            high=None,
            low=None,
            state="unknown",
            window_start_ns=session.open_time_ns,
            window_end_ns=window_end,
            required_bar_count=None,
            source_bar_count=0,
            reason=f"{kernel.identity.timeframe} bars cannot exactly tile a {minutes}-minute opening range.",
        )

    required = window_ns // duration_ns
    if decision_time_ns < window_end:
        return OpeningRange(
            name=name,  # type: ignore[arg-type]
            minutes=minutes,  # type: ignore[arg-type]
            status="PENDING",
            high=None,
            low=None,
            state="unknown",
            window_start_ns=session.open_time_ns,
            window_end_ns=window_end,
            required_bar_count=int(required),
            source_bar_count=0,
            reason=f"{name} is not authoritative until the complete window has closed.",
        )

    by_timestamp = {kernel.vectors.timestamps_ns[index]: index for index in current_indices}
    expected = [session.open_time_ns + offset * duration_ns for offset in range(int(required))]
    resolved = [by_timestamp.get(timestamp) for timestamp in expected]
    if any(index is None for index in resolved):
        present = sum(index is not None for index in resolved)
        return OpeningRange(
            name=name,  # type: ignore[arg-type]
            minutes=minutes,  # type: ignore[arg-type]
            status="UNAVAILABLE",
            high=None,
            low=None,
            state="unknown",
            window_start_ns=session.open_time_ns,
            window_end_ns=window_end,
            required_bar_count=int(required),
            source_bar_count=present,
            reason=f"{name} has missing closed bars; partial opening ranges have no authority.",
        )

    indices = [int(index) for index in resolved if index is not None]
    high, low = kernel.high_low(indices[0], indices[-1] + 1)
    latest = _kernel_bar(kernel, current_indices[-1])
    return OpeningRange(
        name=name,  # type: ignore[arg-type]
        minutes=minutes,  # type: ignore[arg-type]
        status="AVAILABLE",
        high=round(high, 4),
        low=round(low, 4),
        state=_opening_range_state(latest, high, low),
        window_start_ns=session.open_time_ns,
        window_end_ns=window_end,
        required_bar_count=int(required),
        source_bar_count=len(indices),
    )


def _previous_session_levels(
    kernel: SnapshotFeatureKernel,
    sessions: dict[str, list[int]],
    *,
    current_session_id: str,
    duration_ns: int,
) -> PreviousSessionLevels:
    previous_ids = [item for item in sorted(sessions) if item < current_session_id]
    if not previous_ids:
        return PreviousSessionLevels(
            status="UNAVAILABLE",
            session_id=None,
            high=None,
            low=None,
            close=None,
            source_bar_count=0,
            first_bar_timestamp_ns=None,
            last_bar_timestamp_ns=None,
            source_hash=None,
            reason="No earlier observed regular session is present in the D2 snapshot.",
        )

    previous_id = previous_ids[-1]
    indices = sessions[previous_id]
    session_date = date.fromisoformat(previous_id)
    open_ns, close_ns = _session_bounds_ns(session_date)
    session_length = close_ns - open_ns
    if session_length % duration_ns:
        return PreviousSessionLevels(
            status="UNAVAILABLE",
            session_id=previous_id,
            high=None,
            low=None,
            close=None,
            source_bar_count=len(indices),
            first_bar_timestamp_ns=kernel.vectors.timestamps_ns[indices[0]],
            last_bar_timestamp_ns=kernel.vectors.timestamps_ns[indices[-1]],
            source_hash=None,
            reason=f"{kernel.identity.timeframe} bars cannot exactly tile the full NSE regular session; PDH/PDL completeness is unproven.",
        )

    expected_count = session_length // duration_ns
    expected = [open_ns + offset * duration_ns for offset in range(int(expected_count))]
    actual = [kernel.vectors.timestamps_ns[index] for index in indices]
    if actual != expected:
        return PreviousSessionLevels(
            status="UNAVAILABLE",
            session_id=previous_id,
            high=None,
            low=None,
            close=None,
            source_bar_count=len(indices),
            first_bar_timestamp_ns=actual[0],
            last_bar_timestamp_ns=actual[-1],
            source_hash=None,
            reason="Previous observed session is incomplete or has timestamp gaps; PDH/PDL/CPR are withheld.",
        )

    high, low = kernel.high_low(indices[0], indices[-1] + 1)
    close = kernel.vectors.closes[indices[-1]]
    source_hash = _hash_payload(
        [
            {
                "timestamp_ns": kernel.vectors.timestamps_ns[index],
                "high": kernel.vectors.highs[index],
                "low": kernel.vectors.lows[index],
                "close": kernel.vectors.closes[index],
                "sequence_number": kernel.vectors.sequence_numbers[index],
            }
            for index in indices
        ]
    )
    return PreviousSessionLevels(
        status="AVAILABLE",
        session_id=previous_id,
        high=round(high, 4),
        low=round(low, 4),
        close=round(close, 4),
        source_bar_count=len(indices),
        first_bar_timestamp_ns=actual[0],
        last_bar_timestamp_ns=actual[-1],
        source_hash=source_hash,
    )


def _canonical_cpr(previous: PreviousSessionLevels, latest_close: float) -> CanonicalCpr:
    if previous.status != "AVAILABLE" or previous.high is None or previous.low is None or previous.close is None:
        return CanonicalCpr(
            status="UNAVAILABLE",
            pivot=None,
            bc=None,
            tc=None,
            state="unknown",
            source_session_id=previous.session_id,
            source_hash=previous.source_hash,
            reason="CPR requires a complete PIT-safe previous session with high, low and close.",
        )
    pivot, bc, tc = _calculate_cpr(previous.high, previous.low, previous.close)
    return CanonicalCpr(
        status="AVAILABLE",
        pivot=pivot,
        bc=bc,
        tc=tc,
        state=_cpr_state(latest_close, bc, tc),
        source_session_id=previous.session_id,
        source_hash=previous.source_hash,
    )


def _canonical_flags(
    *,
    latest: CandleBar,
    vwap: float | None,
    or_high: float | None,
    or_low: float | None,
    pdh: float | None,
    pdl: float | None,
    cpr: CanonicalCpr,
) -> tuple[str, ...]:
    flags: list[str] = []
    if vwap is not None and latest.close < vwap:
        flags.append("below_session_vwap")
    if vwap is not None and latest.low <= vwap <= latest.close:
        flags.append("session_vwap_held")
    if pdh is not None and latest.high >= pdh and latest.close < pdh:
        flags.append("rejecting_pdh")
    if pdh is not None and latest.close > pdh:
        flags.append("breaking_pdh")
    if pdl is not None and latest.low <= pdl and latest.close > pdl:
        flags.append("reclaiming_pdl")
    if or_high is not None and latest.high > or_high and latest.close <= or_high:
        flags.append("failed_or15_breakout")
    if or_high is not None and latest.close > or_high:
        flags.append("or15_breakout")
    if cpr.pivot is not None and latest.close >= cpr.pivot:
        flags.append("above_cpr_pivot")
    if cpr.bc is not None and cpr.tc is not None and cpr.bc <= latest.close <= cpr.tc:
        flags.append("inside_cpr")
    return tuple(flags or ["no_key_level_interaction"])


def _missing_reasons(
    vwap: CanonicalVwap,
    opening_ranges: tuple[OpeningRange, ...],
    previous: PreviousSessionLevels,
    cpr: CanonicalCpr,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if vwap.status != "AVAILABLE" and vwap.reason:
        reasons.append(f"VWAP: {vwap.reason}")
    for item in opening_ranges:
        if item.status != "AVAILABLE" and item.reason:
            reasons.append(f"{item.name}: {item.reason}")
    if previous.status != "AVAILABLE" and previous.reason:
        reasons.append(f"previous_session: {previous.reason}")
    if cpr.status != "AVAILABLE" and cpr.reason:
        reasons.append(f"CPR: {cpr.reason}")
    return tuple(reasons)


def _legacy_projection(request: VwapOrbCprContextRequest, kernel: SnapshotFeatureKernel) -> dict[str, object]:
    """Reproduce pre-M3.1 level outputs from the shared raw kernel facts.

    This is intentionally isolated compatibility debt. It does not populate the
    canonical receipt summary and can be deleted when D6 is migrated in M4.
    """

    bars = list(request.series.bars)
    latest = bars[-1] if bars else None
    previous = bars[-2] if len(bars) >= 2 else None
    latest_close = latest.close if latest else None
    calculated_vwap = request.vwap if request.vwap is not None else _legacy_vwap(kernel)
    if request.opening_range_high is not None:
        opening_high = request.opening_range_high
    else:
        opening_high = max(kernel.vectors.highs[: min(3, kernel.closed_bar_count)]) if bars else None
    if request.opening_range_low is not None:
        opening_low = request.opening_range_low
    else:
        opening_low = min(kernel.vectors.lows[: min(3, kernel.closed_bar_count)]) if bars else None
    pivot, bc, tc = _calculate_cpr(request.previous_day_high, request.previous_day_low, request.previous_close)

    vwap_state = _state_against_level(latest, previous, calculated_vwap)
    orb_state = _opening_range_state(latest, opening_high, opening_low)
    cpr_state = _cpr_state(latest_close, bc, tc)
    pdh_state = _state_against_level(latest, previous, request.previous_day_high)
    pdl_state = _state_against_level(latest, previous, request.previous_day_low)
    vpd_state = _vpd_state(latest_close, request.volume_profile_hvn, request.volume_profile_lvn)
    flags = _legacy_flags(latest, request, calculated_vwap, opening_high, pivot, bc, tc)
    score = _level_respect_score(vwap_state, orb_state, cpr_state, pdh_state, pdl_state, flags)
    blocks_trade = any(
        flag in flags
        for flag in ("rejecting_pdh", "failed_orb_breakout", "below_vwap", "near_lvn_instability")
    )
    reasons = [
        f"VWAP state is {vwap_state}.",
        f"Opening range state is {orb_state}.",
        f"CPR state is {cpr_state}.",
        f"PDH state is {pdh_state}; PDL state is {pdl_state}.",
        f"Volume profile state is {vpd_state}.",
        f"Level flags: {', '.join(flags)}.",
    ]
    return {
        "calculated_vwap": calculated_vwap,
        "price_vs_vwap_pct": _pct_diff(latest_close, calculated_vwap),
        "vwap_state": vwap_state,
        "opening_range_high": opening_high,
        "opening_range_low": opening_low,
        "opening_range_state": orb_state,
        "cpr_pivot": pivot,
        "cpr_bc": bc,
        "cpr_tc": tc,
        "cpr_state": cpr_state,
        "pdh_state": pdh_state,
        "pdl_state": pdl_state,
        "vpd_state": vpd_state,
        "support_resistance_flags": flags,
        "level_respect_score": round(score, 4),
        "blocks_trade": blocks_trade,
        "reasons": reasons,
    }


def _legacy_vwap(kernel: SnapshotFeatureKernel) -> float | None:
    weighted = 0.0
    total = 0.0
    for typical, volume in zip(kernel.vectors.typical_prices, kernel.vectors.volumes):
        if volume is None:
            continue
        weighted += typical * volume
        total += volume
    if total <= 0.0:
        return None
    return round(weighted / total, 4)


def _legacy_flags(latest, request, vwap, orb_high, pivot, bc, tc) -> list[str]:
    if latest is None:
        return ["no_candles"]
    flags: list[str] = []
    if vwap is not None and latest.close < vwap:
        flags.append("below_vwap")
    if vwap is not None and latest.low <= vwap <= latest.close:
        flags.append("vwap_held")
    if request.previous_day_high is not None and latest.high >= request.previous_day_high and latest.close < request.previous_day_high:
        flags.append("rejecting_pdh")
    if request.previous_day_high is not None and latest.close > request.previous_day_high:
        flags.append("breaking_pdh")
    if request.previous_day_low is not None and latest.low <= request.previous_day_low and latest.close > request.previous_day_low:
        flags.append("reclaiming_pdl")
    if orb_high is not None and latest.high > orb_high and latest.close <= orb_high:
        flags.append("failed_orb_breakout")
    if orb_high is not None and latest.close > orb_high:
        flags.append("orb_breakout")
    if pivot is not None and latest.close >= pivot:
        flags.append("above_pivot")
    if bc is not None and tc is not None and bc <= latest.close <= tc:
        flags.append("inside_cpr")
    if request.volume_profile_lvn is not None and abs(_pct_diff(latest.close, request.volume_profile_lvn) or 0.0) <= 0.12:
        flags.append("near_lvn_instability")
    return flags or ["no_key_level_interaction"]


def _state_against_level(latest: CandleBar | None, previous: CandleBar | None, level: float | None) -> LevelState:
    if latest is None or level is None:
        return "unknown"
    tolerance = max(level * 0.001, 0.01)
    if latest.high >= level and latest.close < level and _has_upper_wick_rejection(latest):
        return "rejecting"
    if previous and previous.close < level <= latest.close:
        return "reclaiming"
    if latest.close > level + tolerance:
        return "above"
    if latest.close < level - tolerance:
        return "below"
    return "inside"


def _opening_range_state(latest: CandleBar | None, high: float | None, low: float | None) -> LevelState:
    if latest is None or high is None or low is None:
        return "unknown"
    if latest.high > high and latest.close <= high:
        return "rejecting"
    if latest.low < low and latest.close >= low:
        return "reclaiming"
    if latest.close > high:
        return "breaking_up"
    if latest.close < low:
        return "breaking_down"
    return "inside"


def _cpr_state(close: float | None, bc: float | None, tc: float | None) -> LevelState:
    if close is None or bc is None or tc is None:
        return "unknown"
    if close > tc:
        return "above"
    if close < bc:
        return "below"
    return "inside"


def _vpd_state(close: float | None, hvn: float | None, lvn: float | None) -> str:
    if close is None or (hvn is None and lvn is None):
        return "unknown"
    if hvn is not None and abs(_pct_diff(close, hvn) or 0.0) <= 0.12:
        return "at_hvn"
    if lvn is not None and abs(_pct_diff(close, lvn) or 0.0) <= 0.12:
        return "at_lvn"
    if hvn is not None and close > hvn:
        return "above_hvn"
    if lvn is not None and close < lvn:
        return "below_lvn"
    return "between_nodes"


def _level_respect_score(*states_and_flags) -> float:
    score = 0.5
    flat: list[str] = []
    for item in states_and_flags:
        if isinstance(item, list):
            flat.extend(item)
        elif isinstance(item, tuple):
            flat.extend(item)
        else:
            flat.append(str(item))
    for item in flat:
        if item in {
            "above",
            "breaking_up",
            "reclaiming",
            "vwap_held",
            "session_vwap_held",
            "orb_breakout",
            "or15_breakout",
            "above_pivot",
            "above_cpr_pivot",
            "breaking_pdh",
        }:
            score += 0.06
        if item in {
            "rejecting",
            "below",
            "breaking_down",
            "failed_orb_breakout",
            "failed_or15_breakout",
            "below_vwap",
            "below_session_vwap",
            "near_lvn_instability",
        }:
            score -= 0.08
    return min(max(score, 0.0), 1.0)


def _calculate_cpr(
    pdh: float | None,
    pdl: float | None,
    previous_close: float | None,
) -> tuple[float | None, float | None, float | None]:
    if pdh is None or pdl is None or previous_close is None:
        return None, None, None
    pivot = (pdh + pdl + previous_close) / 3.0
    bc = (pdh + pdl) / 2.0
    tc = pivot + (pivot - bc)
    return round(pivot, 4), round(min(bc, tc), 4), round(max(bc, tc), 4)


def _pct_diff(value: float | None, reference: float | None) -> float | None:
    if value is None or reference is None or reference == 0:
        return None
    return round(((value - reference) / reference) * 100.0, 4)


def _has_upper_wick_rejection(bar: CandleBar) -> bool:
    candle_range = max(bar.high - bar.low, 1e-9)
    upper_wick = max(0.0, bar.high - max(bar.open, bar.close))
    return upper_wick / candle_range >= 0.3


def _previous_bar(bars: list[CandleBar], index: int) -> CandleBar | None:
    return bars[index - 1] if index > 0 else None


def _kernel_bar(kernel: SnapshotFeatureKernel, index: int) -> CandleBar:
    # A compact immutable projection used only by state classifiers. The source
    # identity remains the kernel/D2 hash; no new market facts are introduced.
    return CandleBar(
        symbol=kernel.identity.symbol,
        timeframe=kernel.identity.timeframe,  # type: ignore[arg-type]
        timestamp_ns=kernel.vectors.timestamps_ns[index],
        open=kernel.vectors.opens[index],
        high=kernel.vectors.highs[index],
        low=kernel.vectors.lows[index],
        close=kernel.vectors.closes[index],
        volume=kernel.vectors.volumes[index],
        source="snapshot",
        sequence_number=kernel.vectors.sequence_numbers[index],
    )


def _local_datetime(timestamp_ns: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).astimezone(NSE_TIMEZONE)


def _session_bounds_ns(session_date: date) -> tuple[int, int]:
    start = datetime.combine(session_date, NSE_SESSION_OPEN, tzinfo=NSE_TIMEZONE)
    end = datetime.combine(session_date, NSE_SESSION_CLOSE, tzinfo=NSE_TIMEZONE)
    return int(start.timestamp() * 1_000_000_000), int(end.timestamp() * 1_000_000_000)


def _hash_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
