"""Canonical ORB BUILD-2 market-identity contracts (venue / instrument /
session / contract / price-rule / economics / data-basis / receipts).

Research-only infrastructure. These contracts answer "what exact market
object is this, and under which version of the exchange rules does it
exist at this point in time". They carry no direction, setup, probability,
paper-ticket, execution, or order-routing authority: every identity object
is frozen with zero-authority flags enforced at construction.

Conventions follow BUILD-1 (`orb/candidate_intake.py`): frozen dataclasses
with slots, `__post_init__` validation, canonical-JSON SHA-256 record
hashes computed by small builder functions (`..._record()` + `replace`),
timezone-aware datetimes only, explicit missingness (no missing -> zero).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Sequence

from ..candidate_intake import (
    AvailabilityState,
    InstrumentType,
    canonical_json_bytes,
    canonical_sha256,
)

ORB_MARKET_IDENTITY_VERSION = "orb-market-identity.v1"
ORB_VENUE_VERSION = "orb-venue-identity.v1"
ORB_INSTRUMENT_VERSION = "orb-instrument-profile.v1"
ORB_SESSION_VERSION = "orb-session-profile.v1"
ORB_CONTRACT_VERSION = "orb-contract-profile.v1"
ORB_PRICE_RULE_VERSION = "orb-price-rule.v1"
ORB_LOT_RULE_VERSION = "orb-lot-rule.v1"
ORB_CALENDAR_VERSION = "orb-calendar-record.v1"
ORB_SOURCE_RECEIPT_VERSION = "orb-source-receipt.v1"


def _utc(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _utc_or_none(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    return _utc(value, field_name=field_name)


def _non_empty(value: str, *, field_name: str) -> str:
    clean = str(value).strip()
    if not clean:
        raise ValueError(f"{field_name} is required")
    return clean


def _decimal(value: Any, *, field_name: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field_name} must be an exact decimal amount")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be an exact decimal amount") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


def _sha256_text(value: str, *, field_name: str) -> str:
    from ..candidate_intake import _validate_sha256  # local import: same package family

    return _validate_sha256(value, field_name=field_name)


class RegistryLifecycle(str, Enum):
    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class SessionType(str, Enum):
    REGULAR = "REGULAR"
    PARTIAL = "PARTIAL"
    SPECIAL = "SPECIAL"
    MOCK = "MOCK"
    CLOSED_HOLIDAY = "CLOSED_HOLIDAY"


class SessionPhase(str, Enum):
    PRE_OPEN = "PRE_OPEN"
    OPENING_AUCTION = "OPENING_AUCTION"
    REGULAR = "REGULAR"
    MID_SESSION_BREAK = "MID_SESSION_BREAK"
    CLOSING_AUCTION = "CLOSING_AUCTION"
    POST_CLOSE = "POST_CLOSE"
    SETTLEMENT_WINDOW = "SETTLEMENT_WINDOW"
    SPECIAL_SESSION = "SPECIAL_SESSION"
    MOCK_SESSION = "MOCK_SESSION"
    CLOSED = "CLOSED"


class SettlementType(str, Enum):
    CASH = "CASH"
    PHYSICAL = "PHYSICAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class PriceRuleType(str, Enum):
    STATIC_TICK = "STATIC_TICK"
    PRICE_BANDED_TICK = "PRICE_BANDED_TICK"
    UNDERLYING_REFERENCED_TICK = "UNDERLYING_REFERENCED_TICK"
    VERSIONED_REGISTERED_RULE = "VERSIONED_REGISTERED_RULE"


class DataBasis(str, Enum):
    RAW_CONTRACT = "RAW_CONTRACT"
    RAW_CASH = "RAW_CASH"
    CORPORATE_ACTION_ADJUSTED = "CORPORATE_ACTION_ADJUSTED"
    BACK_ADJUSTED_CONTINUOUS = "BACK_ADJUSTED_CONTINUOUS"
    RATIO_ADJUSTED_CONTINUOUS = "RATIO_ADJUSTED_CONTINUOUS"
    UNADJUSTED_CONTINUOUS = "UNADJUSTED_CONTINUOUS"
    REGISTERED_OTHER = "REGISTERED_OTHER"
    UNKNOWN = "UNKNOWN"


class ResolutionState(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


def _check_authority_flags(obj: Any) -> None:
    if obj.research_only is not True:
        raise ValueError("market-identity contracts are research-only; research_only must be True")
    if obj.trade_allowed is not False:
        raise ValueError("market-identity contracts cannot allow trading; trade_allowed must be False")
    if obj.order_routing_enabled is not False:
        raise ValueError("market-identity contracts cannot route orders; order_routing_enabled must be False")
    if obj.live_trading_blocked is not True:
        raise ValueError("market-identity contracts must block live trading; live_trading_blocked must be True")
    if obj.may_set_final_band is not False:
        raise ValueError("market-identity contracts cannot set the final band; may_set_final_band must be False")
    if obj.may_execute is not False:
        raise ValueError("market-identity contracts cannot execute; may_execute must be False")


@dataclass(frozen=True, slots=True)
class VenueAliasV1:
    """One provider alias mapping, effective-dated. Aliases never become the
    canonical venue id; a mapping change retires the old record, never edits it."""

    alias: str
    provider: str
    effective_from: datetime
    effective_to: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "alias", _non_empty(self.alias, field_name="alias"))
        object.__setattr__(self, "provider", _non_empty(self.provider, field_name="provider"))
        effective_from = _utc(self.effective_from, field_name="alias effective_from")
        object.__setattr__(self, "effective_from", effective_from)
        effective_to = _utc_or_none(self.effective_to, field_name="alias effective_to")
        object.__setattr__(self, "effective_to", effective_to)
        if effective_to is not None and effective_to <= effective_from:
            raise ValueError("alias effective_to must be after effective_from")


@dataclass(frozen=True, slots=True)
class VenueIdentityV1:
    schema_version: str
    venue_id: str
    operating_venue_id: str
    mic_or_registered_venue_code: str | None
    exchange_code: str
    segment_code: str
    country_code: str
    venue_timezone: str
    provider_aliases: tuple[VenueAliasV1, ...] = ()
    source_receipt_ids: tuple[str, ...] = ()
    availability: AvailabilityState = AvailabilityState.AVAILABLE
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("venue_id", "operating_venue_id", "exchange_code", "segment_code", "country_code"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        object.__setattr__(self, "venue_timezone", _non_empty(self.venue_timezone, field_name="venue_timezone"))
        try:
            import zoneinfo

            zoneinfo.ZoneInfo(self.venue_timezone)
        except Exception as exc:
            raise ValueError(f"venue_timezone must be a valid IANA name: {self.venue_timezone!r}") from exc
        if self.mic_or_registered_venue_code is not None:
            object.__setattr__(
                self,
                "mic_or_registered_venue_code",
                _non_empty(self.mic_or_registered_venue_code, field_name="mic_or_registered_venue_code"),
            )
        object.__setattr__(self, "provider_aliases", tuple(self.provider_aliases))
        object.__setattr__(self, "source_receipt_ids", tuple(self.source_receipt_ids))
        object.__setattr__(self, "effective_from", _utc_or_none(self.effective_from, field_name="venue effective_from"))
        object.__setattr__(self, "effective_to", _utc_or_none(self.effective_to, field_name="venue effective_to"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="venue published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="venue available_at"))
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to <= self.effective_from
        ):
            raise ValueError("venue effective_to must be after effective_from")


@dataclass(frozen=True, slots=True)
class InstrumentProfileV1:
    """Canonical OrbInstrumentProfileV1. A ticker symbol alone is never
    sufficient identity; the key binds venue, segment, and type."""

    schema_version: str
    instrument_key: str
    instrument_type: InstrumentType
    venue_id: str
    segment_id: str
    canonical_symbol: str
    display_symbol: str
    provider_identifiers: tuple[str, ...] = ()
    provider_aliases: tuple[str, ...] = ()
    isin: str | None = None
    underlying_instrument_key: str | None = None
    asset_class: str = "UNSPECIFIED"
    currency: str = "UNSPECIFIED"
    quote_currency: str = "UNSPECIFIED"
    price_basis_family: str = "UNSPECIFIED"
    tick_rule_id: str | None = None
    price_precision: int | None = None
    lot_rule_id: str | None = None
    calendar_profile_id: str | None = None
    context_applicability: tuple[str, ...] = ()
    availability: AvailabilityState = AvailabilityState.AVAILABLE
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    source_receipt_ids: tuple[str, ...] = ()
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("instrument_key", "venue_id", "segment_id", "canonical_symbol", "display_symbol"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        object.__setattr__(
            self, "canonical_symbol", str(self.canonical_symbol).strip().upper()
        )
        if self.price_precision is not None and (not isinstance(self.price_precision, int) or self.price_precision < 0):
            raise ValueError("price_precision must be a non-negative integer when set")
        object.__setattr__(self, "provider_identifiers", tuple(self.provider_identifiers))
        object.__setattr__(self, "provider_aliases", tuple(self.provider_aliases))
        object.__setattr__(self, "context_applicability", tuple(self.context_applicability))
        object.__setattr__(self, "source_receipt_ids", tuple(self.source_receipt_ids))
        object.__setattr__(self, "effective_from", _utc_or_none(self.effective_from, field_name="instrument effective_from"))
        object.__setattr__(self, "effective_to", _utc_or_none(self.effective_to, field_name="instrument effective_to"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="instrument published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="instrument available_at"))


@dataclass(frozen=True, slots=True)
class TradingIntervalV1:
    """One half-open [start, end) local-time interval. An end at or before the
    start means the interval crosses midnight into the next civil day."""

    start_local: str
    end_local: str
    phase: SessionPhase = SessionPhase.REGULAR

    def __post_init__(self) -> None:
        import re

        for name in ("start_local", "end_local"):
            value = str(getattr(self, name)).strip()
            if not re.fullmatch(r"\d{2}:\d{2}", value):
                raise ValueError(f"{name} must be HH:MM, got {value!r}")
            hour, minute = int(value[:2]), int(value[3:])
            if hour > 23 or minute > 59:
                raise ValueError(f"{name} must be a valid clock time, got {value!r}")
            object.__setattr__(self, name, value)

    def crosses_midnight(self) -> bool:
        return self.end_local <= self.start_local


@dataclass(frozen=True, slots=True)
class SessionProfileV1:
    """Canonical OrbSessionProfileV1. Never a single timeless open/close pair:
    identity binds venue scope, phase set, explicit intervals, and effective
    version. Fixed numeric UTC offsets are not canonical; the IANA zone is."""

    schema_version: str
    profile_id: str
    venue_id: str
    segment_scope: str
    timezone_name: str
    trading_date_convention: str
    session_type: SessionType
    opening_anchor_local: str
    trading_phases: tuple[SessionPhase, ...] = (SessionPhase.REGULAR,)
    tradable_intervals: tuple[TradingIntervalV1, ...] = ()
    break_intervals: tuple[TradingIntervalV1, ...] = ()
    close_semantics: str = "UNSPECIFIED"
    settlement_semantics: str = "UNSPECIFIED"
    calendar_rule_id: str | None = None
    exception_rule_ids: tuple[str, ...] = ()
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    source_receipt_ids: tuple[str, ...] = ()
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("profile_id", "venue_id", "segment_scope", "trading_date_convention", "opening_anchor_local"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        object.__setattr__(self, "timezone_name", _non_empty(self.timezone_name, field_name="timezone_name"))
        try:
            import zoneinfo

            zoneinfo.ZoneInfo(self.timezone_name)
        except Exception as exc:
            raise ValueError(f"timezone_name must be a valid IANA name: {self.timezone_name!r}") from exc
        import re

        anchor = str(self.opening_anchor_local).strip()
        if not re.fullmatch(r"\d{2}:\d{2}", anchor):
            raise ValueError("opening_anchor_local must be HH:MM")
        object.__setattr__(self, "opening_anchor_local", anchor)
        if not self.tradable_intervals:
            raise ValueError("a session profile must declare at least one tradable interval")
        object.__setattr__(self, "trading_phases", tuple(self.trading_phases))
        object.__setattr__(self, "tradable_intervals", tuple(self.tradable_intervals))
        object.__setattr__(self, "break_intervals", tuple(self.break_intervals))
        object.__setattr__(self, "exception_rule_ids", tuple(self.exception_rule_ids))
        object.__setattr__(self, "source_receipt_ids", tuple(self.source_receipt_ids))
        object.__setattr__(self, "effective_from", _utc_or_none(self.effective_from, field_name="session effective_from"))
        object.__setattr__(self, "effective_to", _utc_or_none(self.effective_to, field_name="session effective_to"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="session published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="session available_at"))


@dataclass(frozen=True, slots=True)
class ContractProfileV1:
    """Canonical OrbContractProfileV1. Expiry identity comes from versioned
    records, never from weekday memory; expiry_date != last_trade_time in
    general; daily settlement != close != final settlement."""

    schema_version: str
    contract_key: str
    product_key: str
    venue_id: str
    segment_id: str
    provider_contract_ids: tuple[str, ...] = ()
    provider_aliases: tuple[str, ...] = ()
    contract_month: str | None = None
    listing_date: date | None = None
    first_trade_at: datetime | None = None
    last_trade_at: datetime | None = None
    expiry_at: datetime | None = None
    expiry_rule_id: str | None = None
    settlement_type: SettlementType = SettlementType.NOT_APPLICABLE
    daily_settlement_reference: str = "UNSPECIFIED"
    final_settlement_reference: str = "UNSPECIFIED"
    delivery_semantics: str = "UNSPECIFIED"
    trading_unit: str = "UNSPECIFIED"
    lot_size: int | None = None
    multiplier: Decimal | None = None
    quote_basis: str = "UNSPECIFIED"
    currency: str = "UNSPECIFIED"
    tick_rule_id: str | None = None
    price_precision: int | None = None
    eligible_data_bases: tuple[DataBasis, ...] = ()
    roll_map_id: str | None = None
    availability: AvailabilityState = AvailabilityState.AVAILABLE
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    source_receipt_ids: tuple[str, ...] = ()
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("contract_key", "product_key", "venue_id", "segment_id"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        if self.contract_month is not None:
            import re

            month = str(self.contract_month).strip()
            if not re.fullmatch(r"\d{4}-\d{2}", month) or not 1 <= int(month[5:]) <= 12:
                raise ValueError("contract_month must be YYYY-MM")
            object.__setattr__(self, "contract_month", month)
        if self.lot_size is not None and (not isinstance(self.lot_size, int) or self.lot_size <= 0):
            raise ValueError("lot_size must be a positive integer when set")
        if self.multiplier is not None:
            multiplier = _decimal(self.multiplier, field_name="multiplier")
            if multiplier <= 0:
                raise ValueError("multiplier must be positive when set")
            object.__setattr__(self, "multiplier", multiplier)
        if self.price_precision is not None and (not isinstance(self.price_precision, int) or self.price_precision < 0):
            raise ValueError("price_precision must be a non-negative integer when set")
        object.__setattr__(self, "provider_contract_ids", tuple(self.provider_contract_ids))
        object.__setattr__(self, "provider_aliases", tuple(self.provider_aliases))
        object.__setattr__(self, "eligible_data_bases", tuple(self.eligible_data_bases))
        object.__setattr__(self, "source_receipt_ids", tuple(self.source_receipt_ids))
        object.__setattr__(self, "first_trade_at", _utc_or_none(self.first_trade_at, field_name="first_trade_at"))
        object.__setattr__(self, "last_trade_at", _utc_or_none(self.last_trade_at, field_name="last_trade_at"))
        object.__setattr__(self, "expiry_at", _utc_or_none(self.expiry_at, field_name="expiry_at"))
        object.__setattr__(self, "effective_from", _utc_or_none(self.effective_from, field_name="contract effective_from"))
        object.__setattr__(self, "effective_to", _utc_or_none(self.effective_to, field_name="contract effective_to"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="contract published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="contract available_at"))


@dataclass(frozen=True, slots=True)
class PriceBandV1:
    """Upper price bound (inclusive) mapped to its tick. Bounds must ascend."""

    upper_bound_inclusive: Decimal
    tick: Decimal

    def __post_init__(self) -> None:
        upper = _decimal(self.upper_bound_inclusive, field_name="band upper_bound_inclusive")
        tick = _decimal(self.tick, field_name="band tick")
        if upper <= 0 or tick <= 0:
            raise ValueError("band bound and tick must be positive")
        object.__setattr__(self, "upper_bound_inclusive", upper)
        object.__setattr__(self, "tick", tick)


@dataclass(frozen=True, slots=True)
class PriceRuleV1:
    """Canonical OrbPriceRuleV1. Ticks are exact Decimals, never binary
    floats; a price is valid only against the rule causally effective for
    its instrument at its timestamp."""

    schema_version: str
    rule_id: str
    rule_version: str
    venue_id: str
    segment_scope: str
    instrument_scope: str
    rule_type: PriceRuleType
    tick: Decimal
    price_precision: int
    bands: tuple[PriceBandV1, ...] = ()
    rounding_semantics: str = "EXACT_GRID"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    source_document_id: str | None = None
    source_hash: str | None = None
    parser_version: str = "UNSPECIFIED"
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("rule_id", "rule_version", "venue_id", "segment_scope", "instrument_scope"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        tick = _decimal(self.tick, field_name="tick")
        if tick <= 0:
            raise ValueError("tick must be positive")
        object.__setattr__(self, "tick", tick)
        if not isinstance(self.price_precision, int) or self.price_precision < 0:
            raise ValueError("price_precision must be a non-negative integer")
        ordered = tuple(self.bands)
        for first, second in zip(ordered, ordered[1:]):
            if second.upper_bound_inclusive <= first.upper_bound_inclusive:
                raise ValueError("price bands must ascend by upper bound")
        object.__setattr__(self, "bands", ordered)
        if self.source_hash is not None:
            object.__setattr__(self, "source_hash", _sha256_text(self.source_hash, field_name="price-rule source_hash"))
        object.__setattr__(self, "effective_from", _utc_or_none(self.effective_from, field_name="price-rule effective_from"))
        object.__setattr__(self, "effective_to", _utc_or_none(self.effective_to, field_name="price-rule effective_to"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="price-rule published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="price-rule available_at"))


@dataclass(frozen=True, slots=True)
class LotRuleV1:
    """Canonical effective-dated contract economics. Old lot sizes are never
    overwritten: a change is a new rule version, so replay sees old values."""

    schema_version: str
    rule_id: str
    rule_version: str
    venue_id: str
    segment_scope: str
    instrument_scope: str
    trading_unit: str
    lot_size: int
    multiplier: Decimal
    quotation_unit: str = "UNSPECIFIED"
    currency: str = "UNSPECIFIED"
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    source_hash: str | None = None
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("rule_id", "rule_version", "venue_id", "segment_scope", "instrument_scope", "trading_unit"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        if not isinstance(self.lot_size, int) or self.lot_size <= 0:
            raise ValueError("lot_size must be a positive integer")
        multiplier = _decimal(self.multiplier, field_name="multiplier")
        if multiplier <= 0:
            raise ValueError("multiplier must be positive")
        object.__setattr__(self, "multiplier", multiplier)
        if self.source_hash is not None:
            object.__setattr__(self, "source_hash", _sha256_text(self.source_hash, field_name="lot-rule source_hash"))
        object.__setattr__(self, "effective_from", _utc_or_none(self.effective_from, field_name="lot-rule effective_from"))
        object.__setattr__(self, "effective_to", _utc_or_none(self.effective_to, field_name="lot-rule effective_to"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="lot-rule published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="lot-rule available_at"))


@dataclass(frozen=True, slots=True)
class CalendarRecordV1:
    """One append-only calendar fact for a venue/segment trading date.
    Corrections add a new record with supersedes_record_id; replay selects
    the record causally effective AND available for the decision."""

    schema_version: str
    record_id: str
    effective_date: date
    venue_id: str
    segment_scope: str
    profile_id: str
    session_type: SessionType
    session_label: str
    tradable_intervals_override: tuple[TradingIntervalV1, ...] | None = None
    contract_events: tuple[str, ...] = ()
    source_document_id: str = "UNSPECIFIED"
    source_hash: str | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    supersedes_record_id: str | None = None
    lifecycle: RegistryLifecycle = RegistryLifecycle.DRAFT
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("record_id", "venue_id", "segment_scope", "profile_id", "session_label"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        if not isinstance(self.effective_date, date) or isinstance(self.effective_date, datetime):
            raise ValueError("effective_date must be a plain date")
        if self.tradable_intervals_override is not None:
            object.__setattr__(self, "tradable_intervals_override", tuple(self.tradable_intervals_override))
        object.__setattr__(self, "contract_events", tuple(self.contract_events))
        if self.source_hash is not None:
            object.__setattr__(self, "source_hash", _sha256_text(self.source_hash, field_name="calendar source_hash"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="calendar published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="calendar available_at"))


@dataclass(frozen=True, slots=True)
class SourceReceiptV1:
    """Provenance for one external/reference-data rule. Never stores
    credentials or secrets; content is pinned by hash, never by prose."""

    schema_version: str
    source_id: str
    source_type: str
    provider: str
    document_id: str
    artifact_identity: str
    content_hash: str
    parser_version: str
    receipt_schema_version: str = ORB_SOURCE_RECEIPT_VERSION
    published_at: datetime | None = None
    available_at: datetime | None = None
    ingested_at: datetime | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    validation_state: str = "UNVALIDATED"
    supersedes_source_id: str | None = None
    record_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("source_id", "source_type", "provider", "document_id", "artifact_identity", "parser_version"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        object.__setattr__(self, "content_hash", _sha256_text(self.content_hash, field_name="content_hash"))
        object.__setattr__(self, "published_at", _utc_or_none(self.published_at, field_name="receipt published_at"))
        object.__setattr__(self, "available_at", _utc_or_none(self.available_at, field_name="receipt available_at"))
        object.__setattr__(self, "ingested_at", _utc_or_none(self.ingested_at, field_name="receipt ingested_at"))
        object.__setattr__(self, "effective_from", _utc_or_none(self.effective_from, field_name="receipt effective_from"))
        object.__setattr__(self, "effective_to", _utc_or_none(self.effective_to, field_name="receipt effective_to"))


@dataclass(frozen=True, slots=True)
class MarketIdentityV1:
    """Canonical OrbMarketIdentityV1: one immutable receipt binding every
    identity piece for a decision instant. RESOLVED proves identity only."""

    schema_version: str
    market_identity_id: str
    market_identity_hash: str
    venue_id: str
    venue_version: str
    venue_hash: str
    instrument_key: str
    instrument_version: str
    instrument_hash: str
    contract_key: str | None
    contract_version: str | None
    contract_hash: str | None
    session_profile_id: str
    session_version: str
    session_hash: str
    calendar_record_id: str
    calendar_version: str
    calendar_hash: str
    price_rule_id: str | None
    price_rule_version: str | None
    price_rule_hash: str | None
    lot_rule_id: str | None
    lot_rule_version: str | None
    lot_rule_hash: str | None
    data_basis: DataBasis
    as_of: datetime
    knowledge_cutoff: datetime
    source_receipt_ids: tuple[str, ...] = ()
    availability: AvailabilityState = AvailabilityState.AVAILABLE
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False

    def __post_init__(self) -> None:
        for name in (
            "market_identity_id",
            "venue_id",
            "instrument_key",
            "session_profile_id",
            "calendar_record_id",
        ):
            object.__setattr__(self, name, _non_empty(getattr(self, name), field_name=name))
        if self.market_identity_hash:
            from ..candidate_intake import _validate_sha256 as _check_sha

            object.__setattr__(self, "market_identity_hash", _check_sha(self.market_identity_hash, field_name="market_identity_hash"))
        object.__setattr__(self, "as_of", _utc(self.as_of, field_name="as_of"))
        object.__setattr__(self, "knowledge_cutoff", _utc(self.knowledge_cutoff, field_name="knowledge_cutoff"))
        object.__setattr__(self, "source_receipt_ids", tuple(self.source_receipt_ids))
        _check_authority_flags(self)


@dataclass(frozen=True, slots=True)
class MarketIdentityResolutionV1:
    """Outcome of resolve_market_identity(): state plus, when unique, the
    identity; when ambiguous, the competing candidates. Latency is measured
    outside and excluded from the output hash."""

    schema_version: str
    state: ResolutionState
    input_hash: str
    output_hash: str
    knowledge_cutoff: datetime
    as_of: datetime
    identity: MarketIdentityV1 | None = None
    candidate_identity_ids: tuple[str, ...] = ()
    source_receipt_ids: tuple[str, ...] = ()
    rule_versions: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    latency_ms: float = 0.0
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_hash", _sha256_text(self.input_hash, field_name="input_hash"))
        object.__setattr__(self, "output_hash", _sha256_text(self.output_hash, field_name="output_hash"))
        object.__setattr__(self, "as_of", _utc(self.as_of, field_name="as_of"))
        object.__setattr__(self, "knowledge_cutoff", _utc(self.knowledge_cutoff, field_name="knowledge_cutoff"))
        if self.state is ResolutionState.RESOLVED and self.identity is None:
            raise ValueError("RESOLVED requires an identity")
        if self.state is not ResolutionState.RESOLVED and self.identity is not None:
            raise ValueError("only RESOLVED may carry an identity")
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")
        object.__setattr__(self, "candidate_identity_ids", tuple(self.candidate_identity_ids))
        object.__setattr__(self, "source_receipt_ids", tuple(self.source_receipt_ids))
        object.__setattr__(self, "rule_versions", tuple(self.rule_versions))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        _check_authority_flags(self)


def _finalize_record(obj: Any, hash_names: Sequence[str] = ("record_hash",)) -> Any:
    payload = {
        key: value
        for key, value in _canonical_record(obj).items()
        if key not in set(hash_names)
    }
    digest = canonical_sha256(payload)
    updates = {name: digest for name in hash_names}
    return replace(obj, **updates)


def _canonical_record(obj: Any) -> dict[str, Any]:
    import dataclasses

    if not dataclasses.is_dataclass(obj):
        raise ValueError("canonical record must be a dataclass")
    out: dict[str, Any] = {}
    for f in dataclasses.fields(obj):
        out[f.name] = _canonical_field(getattr(obj, f.name))
    return out


def _canonical_field(value: Any) -> Any:
    from decimal import Decimal as _Decimal

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return _utc(value, field_name="timestamp").isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, _Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(k): _canonical_field(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical_field(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return _canonical_record(value)
    return value


def venue_record(
    *,
    venue_id: str,
    exchange_code: str,
    segment_code: str,
    country_code: str,
    venue_timezone: str,
    operating_venue_id: str | None = None,
    mic_or_registered_venue_code: str | None = None,
    provider_aliases: Sequence[VenueAliasV1] = (),
    source_receipt_ids: Sequence[str] = (),
    availability: AvailabilityState = AvailabilityState.AVAILABLE,
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
    published_at: datetime | None = None,
    available_at: datetime | None = None,
) -> VenueIdentityV1:
    draft = VenueIdentityV1(
        schema_version=ORB_VENUE_VERSION,
        venue_id=_non_empty(venue_id, field_name="venue_id"),
        operating_venue_id=(operating_venue_id or venue_id).strip(),
        mic_or_registered_venue_code=mic_or_registered_venue_code,
        exchange_code=exchange_code,
        segment_code=segment_code,
        country_code=country_code,
        venue_timezone=venue_timezone,
        provider_aliases=tuple(provider_aliases),
        source_receipt_ids=tuple(source_receipt_ids),
        availability=availability,
        effective_from=effective_from,
        effective_to=effective_to,
        published_at=published_at,
        available_at=available_at,
    )
    return _finalize_record(draft)


def instrument_record(
    *,
    instrument_key: str,
    instrument_type: InstrumentType,
    venue_id: str,
    segment_id: str,
    canonical_symbol: str,
    display_symbol: str | None = None,
    **kwargs: Any,
) -> InstrumentProfileV1:
    draft = InstrumentProfileV1(
        schema_version=ORB_INSTRUMENT_VERSION,
        instrument_key=instrument_key,
        instrument_type=instrument_type,
        venue_id=venue_id,
        segment_id=segment_id,
        canonical_symbol=canonical_symbol,
        display_symbol=display_symbol or canonical_symbol,
        **kwargs,
    )
    return _finalize_record(draft)


def session_record(
    *,
    profile_id: str,
    venue_id: str,
    segment_scope: str,
    timezone_name: str,
    trading_date_convention: str,
    session_type: SessionType,
    opening_anchor_local: str,
    tradable_intervals: Sequence[TradingIntervalV1],
    **kwargs: Any,
) -> SessionProfileV1:
    draft = SessionProfileV1(
        schema_version=ORB_SESSION_VERSION,
        profile_id=profile_id,
        venue_id=venue_id,
        segment_scope=segment_scope,
        timezone_name=timezone_name,
        trading_date_convention=trading_date_convention,
        session_type=session_type,
        opening_anchor_local=opening_anchor_local,
        tradable_intervals=tuple(tradable_intervals),
        **kwargs,
    )
    return _finalize_record(draft)


def contract_record(
    *,
    contract_key: str,
    product_key: str,
    venue_id: str,
    segment_id: str,
    **kwargs: Any,
) -> ContractProfileV1:
    draft = ContractProfileV1(
        schema_version=ORB_CONTRACT_VERSION,
        contract_key=contract_key,
        product_key=product_key,
        venue_id=venue_id,
        segment_id=segment_id,
        **kwargs,
    )
    return _finalize_record(draft)


def price_rule_record(
    *,
    rule_id: str,
    rule_version: str,
    venue_id: str,
    segment_scope: str,
    instrument_scope: str,
    rule_type: PriceRuleType,
    tick: Any,
    price_precision: int,
    **kwargs: Any,
) -> PriceRuleV1:
    draft = PriceRuleV1(
        schema_version=ORB_PRICE_RULE_VERSION,
        rule_id=rule_id,
        rule_version=rule_version,
        venue_id=venue_id,
        segment_scope=segment_scope,
        instrument_scope=instrument_scope,
        rule_type=rule_type,
        tick=tick,
        price_precision=price_precision,
        **kwargs,
    )
    return _finalize_record(draft)


def lot_rule_record(
    *,
    rule_id: str,
    rule_version: str,
    venue_id: str,
    segment_scope: str,
    instrument_scope: str,
    trading_unit: str,
    lot_size: int,
    multiplier: Any,
    **kwargs: Any,
) -> LotRuleV1:
    draft = LotRuleV1(
        schema_version=ORB_LOT_RULE_VERSION,
        rule_id=rule_id,
        rule_version=rule_version,
        venue_id=venue_id,
        segment_scope=segment_scope,
        instrument_scope=instrument_scope,
        trading_unit=trading_unit,
        lot_size=lot_size,
        multiplier=multiplier,
        **kwargs,
    )
    return _finalize_record(draft)


def calendar_record(
    *,
    record_id: str,
    effective_date: date,
    venue_id: str,
    segment_scope: str,
    profile_id: str,
    session_type: SessionType,
    session_label: str,
    lifecycle: RegistryLifecycle = RegistryLifecycle.DRAFT,
    **kwargs: Any,
) -> CalendarRecordV1:
    draft = CalendarRecordV1(
        schema_version=ORB_CALENDAR_VERSION,
        record_id=record_id,
        effective_date=effective_date,
        venue_id=venue_id,
        segment_scope=segment_scope,
        profile_id=profile_id,
        session_type=session_type,
        session_label=session_label,
        lifecycle=lifecycle,
        **kwargs,
    )
    return _finalize_record(draft)


def source_receipt(
    *,
    source_id: str,
    source_type: str,
    provider: str,
    document_id: str,
    artifact_identity: str,
    content_hash: str,
    parser_version: str,
    **kwargs: Any,
) -> SourceReceiptV1:
    draft = SourceReceiptV1(
        schema_version=ORB_SOURCE_RECEIPT_VERSION,
        source_id=source_id,
        source_type=source_type,
        provider=provider,
        document_id=document_id,
        artifact_identity=artifact_identity,
        content_hash=content_hash,
        parser_version=parser_version,
        **kwargs,
    )
    return _finalize_record(draft)


def describe_record(obj: Any) -> dict[str, Any]:
    """Deterministic dict view of a record (hashes included)."""
    return _canonical_record(obj)


def record_bytes(obj: Any) -> bytes:
    return canonical_json_bytes(_canonical_record(obj))
