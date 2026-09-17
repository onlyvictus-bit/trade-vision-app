"""BUILD-3B/C reconstruction kernel + BUILD-3D completed-session assembly.

Maps bars to exact BUILD-2 session identity and computes only raw session
facts. No silent repair: no interpolation, no forward/back fill, no gap
repair, no volume fabrication (missing volume stays missing; an observed
zero stays zero).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence

from ..candidate_intake import AvailabilityState, canonical_sha256
from ..market_identity.contracts import DataBasis
from .contracts import (
    ORB_COMPLETED_SESSION_VERSION,
    ORB_RECONSTRUCTION_ALGO_VERSION,
    ORB_SESSION_COVERAGE_VERSION,
    OrbCompletedSessionV1,
    OrbExpectedSessionGridV1,
    OrbSessionCoverageV1,
    SessionCompleteness,
)


class SessionBar(Protocol):
    symbol: str
    timeframe: str
    timestamp_ns: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    sequence_number: int


def _is_valid_bar(bar: SessionBar) -> str | None:
    """Return None when valid, else a machine-readable defect code."""
    for name in ("open", "high", "low", "close"):
        value = float(getattr(bar, name))
        if not math.isfinite(value) or value <= 0.0:
            return "INVALID_PRICE_NON_POSITIVE_OR_NON_FINITE"
    if bar.high < max(bar.open, bar.close, bar.low):
        return "INVALID_OHLC_HIGH_BELOW_RANGE"
    if bar.low > min(bar.open, bar.close, bar.high):
        return "INVALID_OHLC_LOW_ABOVE_RANGE"
    volume = getattr(bar, "volume", None)
    if volume is not None:
        volume = float(volume)
        if not math.isfinite(volume) or volume < 0.0:
            return "INVALID_VOLUME_NEGATIVE_OR_NON_FINITE"
    if bar.timestamp_ns < 0:
        return "INVALID_TIMESTAMP"
    return None


def _json_safe(value: Any) -> Any:
    """Deterministic JSON-safe projection: non-finite floats become explicit
    tokens instead of crashing canonical hashing or silently vanishing."""
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _same_ohlcv(first: SessionBar, second: SessionBar) -> bool:
    return (
        float(first.open) == float(second.open)
        and float(first.high) == float(second.high)
        and float(first.low) == float(second.low)
        and float(first.close) == float(second.close)
        and (first.volume is None) == (second.volume is None)
        and (first.volume is None or float(first.volume) == float(second.volume))
    )


def reconstruct_session(
    grid: OrbExpectedSessionGridV1,
    bars: Sequence[SessionBar],
    *,
    symbol: str,
    timeframe: str,
    bar_contract_keys: Sequence[str | None] | None = None,
    bar_data_bases: Sequence[DataBasis | str | None] | None = None,
) -> tuple[OrbSessionCoverageV1, dict[str, Any]]:
    """Map bars to the grid and compute raw facts.

    Returns (coverage, facts) where facts carries open/high/low/close,
    session_volume (None when any valid bar lacks volume), valid bars in
    timestamp order, quarantine flag, and state-reason codes. Pure function.
    """
    clean_symbol = symbol.strip().upper()
    duration = grid.timeframe_duration_ns
    cutoff_ns = int(grid.knowledge_cutoff.timestamp() * 1_000_000_000)
    expected = set(grid.expected_slot_opens_ns)

    if bar_contract_keys is not None and len(bar_contract_keys) != len(bars):
        raise ValueError("bar_contract_keys length must match bars length")
    if bar_data_bases is not None and len(bar_data_bases) != len(bars):
        raise ValueError("bar_data_bases length must match bars length")

    ordered = sorted(bars, key=lambda b: (b.timestamp_ns, b.sequence_number))
    by_slot: dict[int, SessionBar] = {}
    counters = {
        "observed_slot_count": 0, "duplicate_slot_count": 0, "conflicting_slot_count": 0,
        "outside_session_count": 0, "break_overlap_count": 0, "future_bar_count": 0,
        "missing_volume_count": 0, "invalid_bar_count": 0, "wrong_identity_count": 0,
        "unexpected_slot_count": 0,
    }
    anomaly_codes: list[str] = []
    quarantined = False

    def note(code: str, counter: str | None = None, quarantine: bool = False) -> None:
        nonlocal quarantined
        anomaly_codes.append(code)
        if counter is not None:
            counters[counter] += 1
        if quarantine:
            quarantined = True

    for index, bar in enumerate(ordered):
        if str(bar.symbol).strip().upper() != clean_symbol or str(bar.timeframe) != timeframe:
            note("WRONG_SYMBOL_OR_TIMEFRAME", "wrong_identity_count")
            continue
        if bar_contract_keys is not None and bar_contract_keys[index] != grid.contract_key:
            note("WRONG_CONTRACT", "wrong_identity_count")
            continue
        if bar_data_bases is not None:
            declared = bar_data_bases[index]
            declared_value = declared.value if isinstance(declared, DataBasis) else declared
            if declared_value != grid.data_basis.value:
                note("WRONG_DATA_BASIS", "wrong_identity_count")
                continue
        close_ns = bar.timestamp_ns + duration
        if bar.timestamp_ns > cutoff_ns or close_ns > cutoff_ns:
            note("FUTURE_BAR_BEYOND_KNOWLEDGE_CUTOFF", "future_bar_count")
            continue
        defect = _is_valid_bar(bar)
        if defect is not None:
            note(defect, "invalid_bar_count", quarantine=True)
            continue
        if not (grid.session_market_start_ns <= bar.timestamp_ns < grid.session_market_end_ns):
            note("BAR_OUTSIDE_SESSION", "outside_session_count")
            continue
        counters["observed_slot_count"] += 1
        if close_ns > grid.session_market_end_ns:
            note("BAR_STRADDLES_SESSION_END", "unexpected_slot_count")
            continue
        if any(bstart <= bar.timestamp_ns and close_ns <= bend for bstart, bend in grid.break_windows_ns):
            note("BAR_INSIDE_BREAK", "break_overlap_count")
            continue
        if any(bar.timestamp_ns < bend and bstart < close_ns
               for bstart, bend in grid.break_windows_ns):
            note("BAR_STRADDLES_BREAK", "break_overlap_count")
            continue
        if bar.timestamp_ns not in expected:
            note("OFF_GRID_TIMESTAMP", "unexpected_slot_count")
            continue
        existing = by_slot.get(bar.timestamp_ns)
        if existing is None:
            by_slot[bar.timestamp_ns] = bar
        elif _same_ohlcv(existing, bar):
            note("IDENTICAL_DUPLICATE", "duplicate_slot_count")
        else:
            note("CONFLICTING_DUPLICATE", "conflicting_slot_count", quarantine=True)

    valid = [by_slot[slot] for slot in sorted(by_slot)]
    valid_opens = set(by_slot)
    missing = [slot for slot in grid.expected_slot_opens_ns if slot not in valid_opens]
    missing_volume = sum(1 for bar in valid if getattr(bar, "volume", None) is None)

    counters["missing_volume_count"] = missing_volume
    if valid:
        session_open = float(valid[0].open)
        session_close = float(valid[-1].close)
        session_high = max(float(bar.high) for bar in valid)
        session_low = min(float(bar.low) for bar in valid)
        session_volume: float | None = (
            sum(float(getattr(bar, "volume")) for bar in valid) if missing_volume == 0 else None
        )
    else:
        session_open = session_close = session_high = session_low = session_volume = None

    coverage = OrbSessionCoverageV1(
        schema_version=ORB_SESSION_COVERAGE_VERSION,
        expected_slot_count=len(grid.expected_slot_opens_ns),
        observed_slot_count=counters["observed_slot_count"],
        valid_slot_count=len(valid),
        missing_slot_count=len(missing),
        duplicate_slot_count=counters["duplicate_slot_count"],
        conflicting_slot_count=counters["conflicting_slot_count"],
        outside_session_count=counters["outside_session_count"],
        break_overlap_count=counters["break_overlap_count"],
        future_bar_count=counters["future_bar_count"],
        missing_volume_count=missing_volume,
        invalid_bar_count=counters["invalid_bar_count"],
        wrong_identity_count=counters["wrong_identity_count"],
        unexpected_slot_count=counters["unexpected_slot_count"],
        missing_slot_opens_ns=tuple(missing),
        anomaly_codes=tuple(anomaly_codes),
    )
    facts = {
        "open": session_open,
        "high": session_high,
        "low": session_low,
        "close": session_close,
        "session_volume": session_volume,
        "valid_bars": valid,
        "quarantined": quarantined,
    }
    return coverage, facts


def decide_completeness(
    *,
    grid: OrbExpectedSessionGridV1,
    coverage: OrbSessionCoverageV1,
    quarantined: bool,
    has_valid_prices: bool,
) -> tuple[SessionCompleteness, tuple[str, ...]]:
    """Map coverage evidence to a falsifiable completeness claim."""
    reasons: list[str] = []
    if quarantined:
        reasons.append("QUARANTINED_ON_CONTRADICTORY_OR_INVALID_OBSERVATION")
        return SessionCompleteness.QUARANTINED, tuple(reasons)
    end_utc = datetime.fromtimestamp(grid.session_market_end_ns / 1_000_000_000, tz=timezone.utc)
    if grid.knowledge_cutoff < end_utc:
        reasons.append("PENDING_SESSION_END_BEYOND_KNOWLEDGE_CUTOFF")
        return SessionCompleteness.PENDING, tuple(reasons)
    if not grid.slots_are_required:
        reasons.append("CADENCE_NOT_FIXED_ABSENCE_IS_NO_OBSERVATION")
    if coverage.missing_slot_count > 0 or not has_valid_prices:
        reasons.append("INCOMPLETE_REQUIRED_PRICE_COVERAGE_UNPROVEN")
        return SessionCompleteness.INCOMPLETE, tuple(reasons)
    if coverage.missing_volume_count > 0:
        reasons.append("PRICE_COMPLETE_VOLUME_UNAVAILABLE")
        return SessionCompleteness.COMPLETE_DEGRADED, tuple(reasons)
    reasons.append("FULL_PRICE_AND_VOLUME_COVERAGE_PROVEN")
    return SessionCompleteness.COMPLETE_TRUSTED, tuple(reasons)


def build_completed_session(
    grid: OrbExpectedSessionGridV1,
    bars: Sequence[SessionBar],
    *,
    symbol: str,
    venue_id: str,
    segment_id: str,
    instrument_type: str,
    currency: str = "UNSPECIFIED",
    bar_contract_keys: Sequence[str | None] | None = None,
    bar_data_bases: Sequence[DataBasis | str | None] | None = None,
) -> OrbCompletedSessionV1:
    """Assemble the immutable OrbCompletedSessionV1 fact for one session."""
    coverage, facts = reconstruct_session(
        grid, bars, symbol=symbol, timeframe=grid.timeframe,
        bar_contract_keys=bar_contract_keys, bar_data_bases=bar_data_bases,
    )
    has_prices = all(v is not None for v in (facts["open"], facts["high"], facts["low"], facts["close"]))
    completeness, reasons = decide_completeness(
        grid=grid, coverage=coverage, quarantined=facts["quarantined"], has_valid_prices=has_prices,
    )
    if grid.source_cadence.value != "FIXED_INTERVAL_BAR_CADENCE" and completeness is SessionCompleteness.COMPLETE_TRUSTED:
        reasons = tuple(sorted(set(reasons) | {"CADENCE_NOT_FIXED_COVERAGE_OBSERVED_NOT_GUARANTEED"}))

    # An unfinished/partial/contradicted session has no session OHLC: partial
    # bars must never be published as the completed-session fact (they would
    # corrupt e.g. PDH). Only price-complete states carry OHLC; only TRUSTED
    # carries a volume total (a partial sum is never a session total).
    if completeness in (SessionCompleteness.COMPLETE_TRUSTED, SessionCompleteness.COMPLETE_DEGRADED):
        ohlc = (facts["open"], facts["high"], facts["low"], facts["close"])
        price_availability = AvailabilityState.AVAILABLE
    else:
        ohlc = (None, None, None, None)
        price_availability = AvailabilityState.UNAVAILABLE
    if completeness is SessionCompleteness.COMPLETE_TRUSTED:
        session_volume = facts["session_volume"]
        volume_availability = AvailabilityState.AVAILABLE
    else:
        session_volume = None
        volume_availability = AvailabilityState.UNAVAILABLE

    end_utc = datetime.fromtimestamp(grid.session_market_end_ns / 1_000_000_000, tz=timezone.utc)
    observed_at = end_utc if grid.knowledge_cutoff >= end_utc else grid.knowledge_cutoff
    available_at = max(observed_at, grid.knowledge_cutoff)

    content = {
        "grid_hash": grid.grid_hash,
        "symbol": symbol.strip().upper(),
        "timeframe": grid.timeframe,
        "bars": [
            {
                "timestamp_ns": bar.timestamp_ns,
                "sequence_number": bar.sequence_number,
                "open": float(bar.open), "high": float(bar.high),
                "low": float(bar.low), "close": float(bar.close),
                "volume": None if getattr(bar, "volume", None) is None else float(getattr(bar, "volume")),
            }
            for bar in sorted(bars, key=lambda b: (b.timestamp_ns, b.sequence_number))
        ],
    }
    input_content_hash = canonical_sha256(_json_safe(content))
    session_id = (
        f"orb-session:{symbol.strip().upper()}:{grid.contract_key or '-'}:"
        f"{grid.session_label}:{grid.timeframe}:{grid.data_basis.value}"
    )
    payload = {
        "schema_version": ORB_COMPLETED_SESSION_VERSION,
        "session_id": session_id,
        "grid_hash": grid.grid_hash,
        "instrument_key": grid.instrument_key,
        "contract_key": grid.contract_key,
        "session_label": grid.session_label,
        "open": ohlc[0], "high": ohlc[1],
        "low": ohlc[2], "close": ohlc[3],
        "session_volume": session_volume,
        "completeness": completeness.value,
        "coverage": {
            "expected": coverage.expected_slot_count, "valid": coverage.valid_slot_count,
            "missing": coverage.missing_slot_count, "anomalies": list(coverage.anomaly_codes),
        },
        "input_content_hash": input_content_hash,
        "algo": ORB_RECONSTRUCTION_ALGO_VERSION,
        "knowledge_cutoff": grid.knowledge_cutoff.isoformat(),
    }
    session_hash = canonical_sha256(payload)
    dependency_ids = tuple(item for item in (
        grid.grid_id, grid.session_profile_hash, grid.calendar_hash,
        grid.session_profile_id, grid.calendar_record_id,
    ) if item)

    return OrbCompletedSessionV1(
        schema_version=ORB_COMPLETED_SESSION_VERSION,
        session_hash=session_hash,
        instrument_key=grid.instrument_key,
        contract_key=grid.contract_key,
        venue_id=venue_id.strip(),
        segment_id=segment_id.strip(),
        instrument_type=instrument_type.strip(),
        session_label=grid.session_label,
        session_type=grid.session_type,
        session_profile_id=grid.session_profile_id,
        session_profile_hash=grid.session_profile_hash,
        calendar_record_id=grid.calendar_record_id,
        calendar_hash=grid.calendar_hash,
        timezone_name=grid.timezone_name,
        timeframe=grid.timeframe,
        data_basis=grid.data_basis,
        session_market_start_ns=grid.session_market_start_ns,
        session_market_end_ns=grid.session_market_end_ns,
        completeness=completeness,
        state_reasons=reasons,
        open=ohlc[0], high=ohlc[1], low=ohlc[2], close=ohlc[3],
        price_availability=price_availability,
        session_volume=session_volume,
        volume_availability=volume_availability,
        open_interest=None,
        open_interest_availability=AvailabilityState.NOT_APPLICABLE,
        coverage=coverage,
        observed_at=observed_at,
        available_at=available_at,
        knowledge_cutoff=grid.knowledge_cutoff,
        input_source_ids=(grid.source_id,),
        input_content_hash=input_content_hash,
        aggregation_algo_version=ORB_RECONSTRUCTION_ALGO_VERSION,
        dependency_ids=dependency_ids,
    )
