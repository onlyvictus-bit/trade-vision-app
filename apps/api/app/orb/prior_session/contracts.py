"""Canonical ORB BUILD-3 prior-session reconstruction contracts.

Research-only fact layer. BUILD-3 answers "what facts were observed in the
completed exchange session?" It owns raw session facts (OHLC, volume
availability, coverage, reference-price identity); interpretation (CPR, ATR,
patterns, context meaning) belongs to the canonical calculation owners.

Every identity object is frozen with zero trading authority enforced at
construction. Same conventions as BUILD-1/BUILD-2: frozen dataclasses with
slots, ``__post_init__`` validation, canonical-JSON SHA-256 record hashes,
timezone-aware datetimes only, explicit missingness (missing != zero,
unknown != closed, close != settlement, raw contract != continuous series).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence

from ..candidate_intake import (
    AvailabilityState,
    _validate_sha256,
    canonical_sha256,
)
from ..market_identity.contracts import DataBasis, SessionType

ORB_PRIOR_SESSION_VERSION = "orb-prior-session.v1"
ORB_EXPECTED_GRID_VERSION = "orb-expected-session-grid.v1"
ORB_SESSION_COVERAGE_VERSION = "orb-session-coverage.v1"
ORB_REFERENCE_PRICE_VERSION = "orb-session-reference-price.v1"
ORB_COMPLETED_SESSION_VERSION = "orb-completed-session.v1"
ORB_PRIOR_FACT_VERSION = "orb-prior-session-fact.v1"
ORB_PRIOR_SNAPSHOT_VERSION = "orb-prior-session-context-snapshot.v1"
ORB_COMPARISON_RECEIPT_VERSION = "orb-source-comparison-receipt.v1"
ORB_RECONSTRUCTION_ALGO_VERSION = "orb-session-reconstruction.v1"


class SessionCompleteness(str, Enum):
    PENDING = "PENDING"
    COMPLETE_TRUSTED = "COMPLETE_TRUSTED"
    COMPLETE_DEGRADED = "COMPLETE_DEGRADED"
    INCOMPLETE = "INCOMPLETE"
    QUARANTINED = "QUARANTINED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class ReferenceType(str, Enum):
    SESSION_CLOSE = "SESSION_CLOSE"
    OFFICIAL_DAILY_SETTLEMENT = "OFFICIAL_DAILY_SETTLEMENT"
    ADJUSTED_CLOSE = "ADJUSTED_CLOSE"
    LAST_COMPLETED_BAR_CLOSE = "LAST_COMPLETED_BAR_CLOSE"
    REGISTERED_OTHER = "REGISTERED_OTHER"


class SourceCadence(str, Enum):
    FIXED_INTERVAL_BAR_CADENCE = "FIXED_INTERVAL_BAR_CADENCE"
    SPARSE_EVENT_TRADE_CADENCE = "SPARSE_EVENT_TRADE_CADENCE"
    UNKNOWN_CADENCE = "UNKNOWN_CADENCE"


class ComparisonOutcome(str, Enum):
    MATCH = "MATCH"
    MATCH_WITHIN_REGISTERED_TOLERANCE = "MATCH_WITHIN_REGISTERED_TOLERANCE"
    CONTEXT_SOURCE_CONFLICT = "CONTEXT_SOURCE_CONFLICT"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    SECONDARY_SOURCE_UNAVAILABLE = "SECONDARY_SOURCE_UNAVAILABLE"


def _utc(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _non_empty(value: str, *, field_name: str) -> str:
    clean = str(value).strip()
    if not clean:
        raise ValueError(f"{field_name} is required")
    return clean


def _check_authority_flags(obj: Any) -> None:
    if obj.research_only is not True:
        raise ValueError("BUILD-3 contracts are research-only; research_only must be True")
    if obj.trade_allowed is not False:
        raise ValueError("BUILD-3 contracts cannot allow trading; trade_allowed must be False")
    if obj.order_routing_enabled is not False:
        raise ValueError("BUILD-3 contracts cannot route orders; order_routing_enabled must be False")
    if obj.live_trading_blocked is not True:
        raise ValueError("BUILD-3 contracts must block live trading; live_trading_blocked must be True")
    if obj.may_set_final_band is not False:
        raise ValueError("BUILD-3 contracts cannot set the final band; may_set_final_band must be False")
    if obj.may_execute is not False:
        raise ValueError("BUILD-3 contracts cannot execute; may_execute must be False")


@dataclass(frozen=True, slots=True)
class OrbExpectedSessionGridV1:
    """BUILD-3A: what bars SHOULD exist. No price interpretation.

    ``expected_slot_opens_ns`` are bar-OPEN timestamps (UTC epoch ns) tiling
    the effective tradable intervals with half-open [start, end) semantics,
    excluding registered breaks. ``slots_are_required`` is True only for
    FIXED_INTERVAL_BAR_CADENCE sources; otherwise absence means NO
    OBSERVATION, not DATA LOSS.
    """

    schema_version: str
    grid_id: str
    grid_hash: str
    instrument_key: str
    contract_key: str | None
    session_label: str
    session_type: SessionType
    session_profile_id: str
    session_profile_hash: str
    calendar_record_id: str | None
    calendar_hash: str | None
    timezone_name: str
    timeframe: str
    timeframe_duration_ns: int
    data_basis: DataBasis
    source_cadence: SourceCadence
    slots_are_required: bool
    expected_slot_opens_ns: tuple[int, ...]
    session_market_start_ns: int
    session_market_end_ns: int
    break_windows_ns: tuple[tuple[int, int], ...]
    untiled_tail_minutes: int
    market_as_of: datetime
    knowledge_cutoff: datetime
    source_id: str
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_key", _non_empty(self.instrument_key, field_name="instrument_key"))
        object.__setattr__(self, "session_label", _non_empty(self.session_label, field_name="session_label"))
        object.__setattr__(self, "session_profile_id", _non_empty(self.session_profile_id, field_name="session_profile_id"))
        object.__setattr__(self, "timezone_name", _non_empty(self.timezone_name, field_name="timezone_name"))
        object.__setattr__(self, "timeframe", _non_empty(self.timeframe, field_name="timeframe"))
        object.__setattr__(self, "source_id", _non_empty(self.source_id, field_name="source_id"))
        if self.timeframe_duration_ns <= 0:
            raise ValueError("timeframe_duration_ns must be positive")
        if self.session_market_end_ns <= self.session_market_start_ns:
            raise ValueError("session_market_end_ns must be after session_market_start_ns")
        if self.untiled_tail_minutes < 0:
            raise ValueError("untiled_tail_minutes cannot be negative")
        if tuple(sorted(self.expected_slot_opens_ns)) != tuple(self.expected_slot_opens_ns):
            raise ValueError("expected_slot_opens_ns must be sorted ascending")
        if len(set(self.expected_slot_opens_ns)) != len(self.expected_slot_opens_ns):
            raise ValueError("expected_slot_opens_ns must not contain duplicates")
        object.__setattr__(self, "expected_slot_opens_ns", tuple(self.expected_slot_opens_ns))
        object.__setattr__(self, "break_windows_ns", tuple(self.break_windows_ns))
        object.__setattr__(self, "market_as_of", _utc(self.market_as_of, field_name="market_as_of"))
        object.__setattr__(self, "knowledge_cutoff", _utc(self.knowledge_cutoff, field_name="knowledge_cutoff"))
        object.__setattr__(self, "session_profile_hash", _validate_sha256(self.session_profile_hash, field_name="session_profile_hash"))
        if self.calendar_hash is not None:
            object.__setattr__(self, "calendar_hash", _validate_sha256(self.calendar_hash, field_name="calendar_hash"))
        object.__setattr__(self, "grid_hash", _validate_sha256(self.grid_hash, field_name="grid_hash"))
        _check_authority_flags(self)


@dataclass(frozen=True, slots=True)
class OrbSessionCoverageV1:
    """BUILD-3B/C: falsifiable completeness evidence. A scalar score must
    never replace these dimensions."""

    schema_version: str
    expected_slot_count: int
    observed_slot_count: int
    valid_slot_count: int
    missing_slot_count: int
    duplicate_slot_count: int
    conflicting_slot_count: int
    outside_session_count: int
    break_overlap_count: int
    future_bar_count: int
    missing_volume_count: int
    invalid_bar_count: int
    wrong_identity_count: int
    unexpected_slot_count: int
    missing_slot_opens_ns: tuple[int, ...] = ()
    anomaly_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "expected_slot_count", "observed_slot_count", "valid_slot_count",
            "missing_slot_count", "duplicate_slot_count", "conflicting_slot_count",
            "outside_session_count", "break_overlap_count", "future_bar_count",
            "missing_volume_count", "invalid_bar_count", "wrong_identity_count",
            "unexpected_slot_count",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.valid_slot_count > self.expected_slot_count:
            raise ValueError("valid_slot_count cannot exceed expected_slot_count")
        if self.missing_slot_count != self.expected_slot_count - self.valid_slot_count:
            raise ValueError("missing_slot_count must equal expected minus valid")
        if len(self.missing_slot_opens_ns) != self.missing_slot_count:
            raise ValueError("missing_slot_opens_ns length must equal missing_slot_count")
        object.__setattr__(self, "missing_slot_opens_ns", tuple(sorted(self.missing_slot_opens_ns)))
        object.__setattr__(self, "anomaly_codes", tuple(sorted(set(self.anomaly_codes))))


@dataclass(frozen=True, slots=True)
class OrbSessionReferencePriceV1:
    """BUILD-3D: one typed reference. SESSION_CLOSE != SETTLEMENT; a value of
    one type must never be substituted for another."""

    schema_version: str
    reference_id: str
    record_hash: str
    instrument_key: str
    contract_key: str | None
    session_label: str
    reference_type: ReferenceType
    value: float | None
    currency: str
    data_basis: DataBasis
    adjustment_identity: str | None
    market_effective_at: datetime | None
    observed_at: datetime | None
    published_at: datetime | None
    available_at: datetime | None
    source_id: str | None
    source_version: str | None
    source_hash: str | None
    availability: AvailabilityState
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_id", _non_empty(self.reference_id, field_name="reference_id"))
        object.__setattr__(self, "instrument_key", _non_empty(self.instrument_key, field_name="instrument_key"))
        object.__setattr__(self, "session_label", _non_empty(self.session_label, field_name="session_label"))
        object.__setattr__(self, "currency", _non_empty(self.currency, field_name="currency"))
        for name in ("market_effective_at", "observed_at", "published_at", "available_at"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _utc(value, field_name=name))
        if self.availability is AvailabilityState.AVAILABLE:
            if self.value is None or not math.isfinite(float(self.value)) or float(self.value) <= 0.0:
                raise ValueError("AVAILABLE reference must carry a finite positive value")
            object.__setattr__(self, "value", float(self.value))
            for name in ("source_id", "source_version", "source_hash"):
                if not (getattr(self, name) or "").strip():
                    raise ValueError(f"AVAILABLE reference requires {name}")
            if self.available_at is None or self.observed_at is None:
                raise ValueError("AVAILABLE reference requires observed_at and available_at")
            if self.observed_at > self.available_at:
                raise ValueError("reference observed_at cannot be after available_at")
            object.__setattr__(self, "source_hash", _validate_sha256(str(self.source_hash), field_name="reference source_hash"))
        elif self.value is not None:
            raise ValueError("non-AVAILABLE reference cannot carry a fabricated value")
        object.__setattr__(self, "record_hash", _validate_sha256(self.record_hash, field_name="record_hash"))
        _check_authority_flags(self)


@dataclass(frozen=True, slots=True)
class OrbCompletedSessionV1:
    """BUILD-3D: immutable completed-session fact. No direction, setup,
    confidence-to-trade, or signal fields exist on this contract."""

    schema_version: str
    session_hash: str
    instrument_key: str
    contract_key: str | None
    venue_id: str
    segment_id: str
    instrument_type: str
    session_label: str
    session_type: SessionType
    session_profile_id: str
    session_profile_hash: str
    calendar_record_id: str | None
    calendar_hash: str | None
    timezone_name: str
    timeframe: str
    data_basis: DataBasis
    session_market_start_ns: int
    session_market_end_ns: int
    completeness: SessionCompleteness
    state_reasons: tuple[str, ...]
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    price_availability: AvailabilityState
    session_volume: float | None
    volume_availability: AvailabilityState
    open_interest: float | None
    open_interest_availability: AvailabilityState
    coverage: OrbSessionCoverageV1
    observed_at: datetime
    available_at: datetime
    knowledge_cutoff: datetime
    input_source_ids: tuple[str, ...]
    input_content_hash: str
    aggregation_algo_version: str
    dependency_ids: tuple[str, ...]
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False

    def __post_init__(self) -> None:
        for name in ("instrument_key", "venue_id", "segment_id", "instrument_type",
                     "session_label", "session_profile_id", "timezone_name", "timeframe"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        if self.session_market_end_ns <= self.session_market_start_ns:
            raise ValueError("session_market_end_ns must be after session_market_start_ns")
        price_fields = (self.open, self.high, self.low, self.close)
        if self.price_availability is AvailabilityState.AVAILABLE:
            if any(v is None or not math.isfinite(float(v)) for v in price_fields):
                raise ValueError("AVAILABLE price facts must all be finite")
            if not (self.low <= min(self.open, self.close) and max(self.open, self.close) <= self.high):  # type: ignore[operator]
                raise ValueError("completed-session OHLC geometry is impossible")
        elif any(v is not None for v in price_fields):
            raise ValueError("non-AVAILABLE price facts cannot carry fabricated values")
        if self.volume_availability is AvailabilityState.AVAILABLE:
            if self.session_volume is None or not math.isfinite(self.session_volume) or self.session_volume < 0:
                raise ValueError("AVAILABLE session_volume must be finite and non-negative")
        elif self.session_volume is not None:
            raise ValueError("non-AVAILABLE session_volume cannot carry a fabricated value")
        if self.open_interest_availability is AvailabilityState.AVAILABLE:
            if self.open_interest is None or not math.isfinite(self.open_interest):
                raise ValueError("AVAILABLE open_interest must be finite")
        elif self.open_interest is not None:
            raise ValueError("non-AVAILABLE open_interest cannot carry a fabricated value")
        object.__setattr__(self, "state_reasons", tuple(sorted(set(self.state_reasons))))
        object.__setattr__(self, "input_source_ids", tuple(sorted(set(self.input_source_ids))))
        object.__setattr__(self, "dependency_ids", tuple(self.dependency_ids))
        for name in ("observed_at", "available_at", "knowledge_cutoff"):
            object.__setattr__(self, name, _utc(getattr(self, name), field_name=name))
        if self.observed_at > self.available_at:
            raise ValueError("observed_at cannot be after available_at")
        object.__setattr__(self, "session_profile_hash", _validate_sha256(self.session_profile_hash, field_name="session_profile_hash"))
        if self.calendar_hash is not None:
            object.__setattr__(self, "calendar_hash", _validate_sha256(self.calendar_hash, field_name="calendar_hash"))
        object.__setattr__(self, "input_content_hash", _validate_sha256(self.input_content_hash, field_name="input_content_hash"))
        object.__setattr__(self, "session_hash", _validate_sha256(self.session_hash, field_name="session_hash"))
        _check_authority_flags(self)


@dataclass(frozen=True, slots=True)
class OrbPriorSessionFactV1:
    """One field of the D-1 snapshot with field-level availability + lineage."""

    field_name: str
    availability: AvailabilityState
    value: Any = None
    units: str | None = None
    observed_at: datetime | None = None
    available_at: datetime | None = None
    source_id: str | None = None
    source_hash: str | None = None
    dependency_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_name", _non_empty(self.field_name, field_name="field_name"))
        if self.observed_at is not None:
            object.__setattr__(self, "observed_at", _utc(self.observed_at, field_name="observed_at"))
        if self.available_at is not None:
            object.__setattr__(self, "available_at", _utc(self.available_at, field_name="available_at"))
        if self.observed_at is not None and self.available_at is not None and self.observed_at > self.available_at:
            raise ValueError("fact observed_at cannot be after available_at")
        if self.source_hash is not None:
            object.__setattr__(self, "source_hash", _validate_sha256(self.source_hash, field_name="source_hash"))
        object.__setattr__(self, "dependency_ids", tuple(self.dependency_ids))
        if self.availability is AvailabilityState.AVAILABLE:
            if self.value is None:
                raise ValueError("AVAILABLE fact must carry a value")
            if self.available_at is None or self.source_id is None or self.source_hash is None:
                raise ValueError("AVAILABLE fact requires available_at, source_id, and source_hash")
        elif self.value is not None:
            raise ValueError("non-AVAILABLE fact cannot carry a fabricated value")


@dataclass(frozen=True, slots=True)
class OrbCalculationReceiptRefV1:
    """Versioned projection pointer to another canonical owner's output
    (e.g. ATR/CPR/pattern). BUILD-3 stores the receipt, never the formula."""

    owner: str
    receipt_id: str
    receipt_hash: str
    available_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "owner", _non_empty(self.owner, field_name="owner"))
        object.__setattr__(self, "receipt_id", _non_empty(self.receipt_id, field_name="receipt_id"))
        object.__setattr__(self, "receipt_hash", _validate_sha256(self.receipt_hash, field_name="receipt_hash"))
        object.__setattr__(self, "available_at", _utc(self.available_at, field_name="available_at"))


@dataclass(frozen=True, slots=True)
class OrbPriorSessionContextSnapshotV1:
    """BUILD-3E: immutable answer to 'for current session S, what was the most
    recent prior COMPLETED exchange session that was causally knowable, and
    which facts from it were valid?'"""

    schema_version: str
    snapshot_id: str
    snapshot_hash: str
    instrument_key: str
    contract_key: str | None
    current_session_label: str
    prior_session_label: str | None
    prior_session_found: bool
    unavailable_reason: str | None
    data_basis: DataBasis
    knowledge_cutoff: datetime
    facts: tuple[OrbPriorSessionFactV1, ...]
    references: tuple[OrbSessionReferencePriceV1, ...]
    calculation_receipt_refs: tuple[OrbCalculationReceiptRefV1, ...]
    prior_session_hash: str | None
    source_hashes: tuple[str, ...]
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_id", _non_empty(self.snapshot_id, field_name="snapshot_id"))
        object.__setattr__(self, "instrument_key", _non_empty(self.instrument_key, field_name="instrument_key"))
        object.__setattr__(self, "current_session_label", _non_empty(self.current_session_label, field_name="current_session_label"))
        if self.prior_session_found and self.prior_session_label is None:
            raise ValueError("a found prior session must carry its label")
        if not self.prior_session_found and not (self.unavailable_reason or "").strip():
            raise ValueError("a missing prior session must carry an unavailable_reason")
        if self.prior_session_found and self.prior_session_hash is None:
            raise ValueError("a found prior session must carry its session hash")
        names = [fact.field_name for fact in self.facts]
        if len(set(names)) != len(names):
            raise ValueError("snapshot facts must have unique field names")
        object.__setattr__(self, "facts", tuple(sorted(self.facts, key=lambda item: item.field_name)))
        object.__setattr__(self, "references", tuple(self.references))
        object.__setattr__(self, "calculation_receipt_refs", tuple(self.calculation_receipt_refs))
        if self.prior_session_hash is not None:
            object.__setattr__(self, "prior_session_hash", _validate_sha256(self.prior_session_hash, field_name="prior_session_hash"))
        for digest in self.source_hashes:
            _validate_sha256(digest, field_name="source_hashes entry")
        object.__setattr__(self, "source_hashes", tuple(sorted(set(self.source_hashes))))
        object.__setattr__(self, "knowledge_cutoff", _utc(self.knowledge_cutoff, field_name="knowledge_cutoff"))
        object.__setattr__(self, "snapshot_hash", _validate_sha256(self.snapshot_hash, field_name="snapshot_hash"))
        _check_authority_flags(self)

    def fact(self, field_name: str) -> OrbPriorSessionFactV1 | None:
        for item in self.facts:
            if item.field_name == field_name:
                return item
        return None


@dataclass(frozen=True, slots=True)
class OrbSourceComparisonReceiptV1:
    """BUILD-3 dual-source integrity receipt. Identity comparability is proven
    before any number is compared; non-like-for-like is NOT_COMPARABLE, never
    a false numeric conflict."""

    schema_version: str
    receipt_id: str
    receipt_hash: str
    left_reference_id: str
    right_reference_id: str
    outcome: ComparisonOutcome
    comparability_checks: tuple[str, ...]
    absolute_difference: float | None
    tolerance_used: float | None
    knowledge_cutoff: datetime
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _non_empty(self.receipt_id, field_name="receipt_id"))
        object.__setattr__(self, "left_reference_id", _non_empty(self.left_reference_id, field_name="left_reference_id"))
        object.__setattr__(self, "right_reference_id", _non_empty(self.right_reference_id, field_name="right_reference_id"))
        if self.absolute_difference is not None and (not math.isfinite(self.absolute_difference) or self.absolute_difference < 0):
            raise ValueError("absolute_difference must be finite and non-negative when set")
        if self.tolerance_used is not None and (not math.isfinite(self.tolerance_used) or self.tolerance_used < 0):
            raise ValueError("tolerance_used must be finite and non-negative when set")
        if self.outcome is ComparisonOutcome.CONTEXT_SOURCE_CONFLICT and self.absolute_difference is None:
            raise ValueError("a conflict receipt must carry the absolute_difference")
        object.__setattr__(self, "comparability_checks", tuple(self.comparability_checks))
        object.__setattr__(self, "knowledge_cutoff", _utc(self.knowledge_cutoff, field_name="knowledge_cutoff"))
        object.__setattr__(self, "receipt_hash", _validate_sha256(self.receipt_hash, field_name="receipt_hash"))
        _check_authority_flags(self)


def hash_record(payload: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(payload))
