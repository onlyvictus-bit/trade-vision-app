"""Append-only versioned registry for BUILD-2 identity records.

Bitemporal discipline: every material record carries market-time
effectiveness (effective_from/effective_to) and knowledge time
(published_at/available_at). Lookups answer two questions at once: what
rule applied at market timestamp T, and what was knowable to the system
at knowledge cutoff K. Default replay mode is AS_KNOWN_THEN.

Lifecycle: DRAFT -> VERIFIED -> ACTIVE -> SUPERSEDED -> RETIRED. Only
VERIFIED/ACTIVE records drive canonical resolution; ingestion never
self-activates. Corrections append a new record with supersedes_record_id;
history is never mutated. Two equally authoritative active rules with
incompatible answers is AMBIGUOUS and fails closed.

The registry object is explicitly constructed (no mutable module-global
default); lookups are pre-indexed with deterministic ordering, and a
bounded resolution cache is keyed to prevent cross-session leakage.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from .contracts import (
    AvailabilityState,
    CalendarRecordV1,
    ContractProfileV1,
    DataBasis,
    InstrumentProfileV1,
    InstrumentType,
    LotRuleV1,
    PriceRuleV1,
    RegistryLifecycle,
    SessionProfileV1,
    SessionType,
    VenueIdentityV1,
)

_LIVE_LIFECYCLES = frozenset({RegistryLifecycle.VERIFIED, RegistryLifecycle.ACTIVE})

_PROMOTIONS: dict[RegistryLifecycle, frozenset[RegistryLifecycle]] = {
    RegistryLifecycle.DRAFT: frozenset({RegistryLifecycle.VERIFIED, RegistryLifecycle.RETIRED}),
    RegistryLifecycle.VERIFIED: frozenset({RegistryLifecycle.ACTIVE, RegistryLifecycle.RETIRED}),
    RegistryLifecycle.ACTIVE: frozenset({RegistryLifecycle.SUPERSEDED, RegistryLifecycle.RETIRED}),
    RegistryLifecycle.SUPERSEDED: frozenset({RegistryLifecycle.RETIRED}),
    RegistryLifecycle.RETIRED: frozenset(),
}

_REPLAY_AS_KNOWN_THEN = "AS_KNOWN_THEN"
_REPLAY_AS_REVISED_NOW = "AS_REVISED_NOW"


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


class RegistryError(ValueError):
    """Machine-readable registry failure; the resolver maps these to reason codes."""


class MarketIdentityRegistry:
    """Explicitly constructed, append-only identity registry."""

    def __init__(self, *, registry_id: str, cache_size: int = 2048) -> None:
        clean = str(registry_id).strip()
        if not clean:
            raise ValueError("registry_id is required")
        if cache_size < 0:
            raise ValueError("cache_size cannot be negative")
        self._registry_id = clean
        self._cache_size = cache_size
        self._venues: dict[str, VenueIdentityV1] = {}
        self._instruments: dict[str, InstrumentProfileV1] = {}
        self._alias_index: dict[tuple[str, str], list[str]] = {}
        self._sessions: dict[str, SessionProfileV1] = {}
        self._contracts: dict[str, ContractProfileV1] = {}
        self._contract_alias_index: dict[str, list[str]] = {}
        self._price_rules: dict[str, list[PriceRuleV1]] = {}
        self._lot_rules: dict[str, list[LotRuleV1]] = {}
        self._calendars: dict[tuple[str, str, date], list[CalendarRecordV1]] = {}
        self._cache: OrderedDict[tuple[str, ...], Any] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def registry_id(self) -> str:
        return self._registry_id

    def registry_version_hash(self) -> str:
        from ..candidate_intake import canonical_sha256

        return canonical_sha256(
            {
                "venues": sorted(self._venues),
                "instruments": sorted(self._instruments),
                "sessions": sorted(self._sessions),
                "contracts": sorted(self._contracts),
                "price_rules": sorted(self._price_rules),
                "lot_rules": sorted(self._lot_rules),
                "calendars": sorted(f"{v}|{s}|{d.isoformat()}" for v, s, d in self._calendars),
            }
        )

    # -- ingestion ---------------------------------------------------------
    def add_venue(self, venue: VenueIdentityV1) -> None:
        if venue.venue_id in self._venues:
            raise RegistryError(f"duplicate venue: {venue.venue_id}")
        self._venues[venue.venue_id] = venue
        for alias in venue.provider_aliases:
            self._alias_index.setdefault((alias.provider, alias.alias), []).append(venue.venue_id)
        self._bump()

    def add_instrument(self, instrument: InstrumentProfileV1) -> None:
        if instrument.instrument_key in self._instruments:
            raise RegistryError(f"duplicate instrument: {instrument.instrument_key}")
        if instrument.venue_id not in self._venues:
            raise RegistryError(f"instrument venue unknown: {instrument.venue_id}")
        self._instruments[instrument.instrument_key] = instrument
        self._bump()

    def add_session_profile(self, profile: SessionProfileV1) -> None:
        if profile.profile_id in self._sessions:
            raise RegistryError(f"duplicate session profile: {profile.profile_id}")
        if profile.venue_id not in self._venues:
            raise RegistryError(f"session venue unknown: {profile.venue_id}")
        self._sessions[profile.profile_id] = profile
        self._bump()

    def add_contract(self, contract: ContractProfileV1) -> None:
        if contract.contract_key in self._contracts:
            raise RegistryError(f"duplicate contract: {contract.contract_key}")
        self._contracts[contract.contract_key] = contract
        for alias in list(contract.provider_contract_ids) + list(contract.provider_aliases):
            self._contract_alias_index.setdefault(alias, []).append(contract.contract_key)
        self._bump()

    def add_price_rule(self, rule: PriceRuleV1) -> None:
        bucket = self._price_rules.setdefault(rule.rule_id, [])
        if any(item.rule_version == rule.rule_version for item in bucket):
            raise RegistryError(f"duplicate price rule version: {rule.rule_id} {rule.rule_version}")
        bucket.append(rule)
        bucket.sort(key=lambda item: item.rule_version)
        self._bump()

    def add_lot_rule(self, rule: LotRuleV1) -> None:
        bucket = self._lot_rules.setdefault(rule.rule_id, [])
        if any(item.rule_version == rule.rule_version for item in bucket):
            raise RegistryError(f"duplicate lot rule version: {rule.rule_id} {rule.rule_version}")
        bucket.append(rule)
        bucket.sort(key=lambda item: item.rule_version)
        self._bump()

    def add_calendar_record(self, record: CalendarRecordV1) -> None:
        key = (record.venue_id, record.segment_scope, record.effective_date)
        bucket = self._calendars.setdefault(key, [])
        if any(item.record_id == record.record_id for item in bucket):
            raise RegistryError(f"duplicate calendar record: {record.record_id}")
        if record.supersedes_record_id is not None and not any(
            item.record_id == record.supersedes_record_id for item in bucket
        ):
            raise RegistryError(f"calendar supersedes unknown record: {record.supersedes_record_id}")
        bucket.append(record)
        self._bump()

    def set_calendar_lifecycle(self, record_id: str, venue_id: str, segment_scope: str, day: date, target: RegistryLifecycle) -> None:
        record = self._find_calendar(record_id, venue_id, segment_scope, day)
        if target not in _PROMOTIONS[record.lifecycle]:
            raise RegistryError(f"illegal calendar transition {record.lifecycle.value}->{target.value}")
        self._replace_calendar(record, record_id, venue_id, segment_scope, day, target)

    def _find_calendar(self, record_id: str, venue_id: str, segment_scope: str, day: date) -> CalendarRecordV1:
        for item in self._calendars.get((venue_id, segment_scope, day), []):
            if item.record_id == record_id:
                return item
        raise RegistryError(f"calendar record not found: {record_id}")

    def _replace_calendar(
        self,
        record: CalendarRecordV1,
        record_id: str,
        venue_id: str,
        segment_scope: str,
        day: date,
        target: RegistryLifecycle,
    ) -> None:
        from dataclasses import replace

        bucket = self._calendars[(venue_id, segment_scope, day)]
        updated = replace(record, lifecycle=target)
        self._calendars[(venue_id, segment_scope, day)] = [
            updated if item.record_id == record_id else item for item in bucket
        ]
        self._bump()

    def _bump(self) -> None:
        self._cache.clear()

    # -- bitemporal selection ----------------------------------------------
    @staticmethod
    def _knowable(record_available_at: datetime | None, cutoff: datetime) -> bool:
        return record_available_at is not None and record_available_at <= cutoff

    @staticmethod
    def _market_effective(
        effective_from: datetime | None,
        effective_to: datetime | None,
        moment: datetime,
    ) -> bool:
        if effective_from is not None and moment < effective_from:
            return False
        if effective_to is not None and moment >= effective_to:
            return False
        return True

    def _select_versions(
        self,
        versions: Sequence[Any],
        moment: datetime,
        knowledge_cutoff: datetime,
        *,
        replay_mode: str = _REPLAY_AS_KNOWN_THEN,
    ) -> list[Any]:
        eligible = []
        for item in versions:
            if not self._market_effective(item.effective_from, item.effective_to, moment):
                continue
            if replay_mode == _REPLAY_AS_KNOWN_THEN and not self._knowable(item.available_at, knowledge_cutoff):
                continue
            eligible.append(item)
        return eligible

    # -- lookups -------------------------------------------------------------
    def venue(self, venue_id: str) -> VenueIdentityV1:
        try:
            return self._venues[venue_id]
        except KeyError as exc:
            raise RegistryError(f"venue not found: {venue_id}") from exc

    def instrument(self, instrument_key: str) -> InstrumentProfileV1:
        try:
            return self._instruments[instrument_key]
        except KeyError as exc:
            raise RegistryError(f"instrument not found: {instrument_key}") from exc

    def venues_for_alias(self, provider: str, alias: str, moment: datetime) -> list[VenueIdentityV1]:
        moment = _require_aware(moment, field_name="moment")
        out = []
        for venue_id in sorted(set(self._alias_index.get((provider, alias), []))):
            venue = self._venues[venue_id]
            for mapping in venue.provider_aliases:
                if mapping.provider != provider or mapping.alias != alias:
                    continue
                if mapping.effective_from <= moment and (
                    mapping.effective_to is None or moment < mapping.effective_to
                ):
                    out.append(venue)
                    break
        return out

    def instruments_for_symbol(self, symbol: str) -> list[InstrumentProfileV1]:
        clean = str(symbol).strip().upper()
        return sorted(
            (
                item
                for item in self._instruments.values()
                if item.canonical_symbol == clean or clean in item.provider_aliases
            ),
            key=lambda item: item.instrument_key,
        )

    def session_profile(self, profile_id: str) -> SessionProfileV1:
        try:
            return self._sessions[profile_id]
        except KeyError as exc:
            raise RegistryError(f"session profile not found: {profile_id}") from exc

    def contracts_for_product(self, product_key: str, moment: datetime) -> list[ContractProfileV1]:
        moment = _require_aware(moment, field_name="moment")
        return sorted(
            (
                item
                for item in self._contracts.values()
                if item.product_key == product_key
                and self._market_effective(item.effective_from, item.effective_to, moment)
            ),
            key=lambda item: item.contract_key,
        )

    def contract(self, contract_key: str) -> ContractProfileV1:
        try:
            return self._contracts[contract_key]
        except KeyError as exc:
            raise RegistryError(f"contract not found: {contract_key}") from exc

    def contracts_for_alias(self, alias: str) -> list[ContractProfileV1]:
        return sorted(
            {self._contracts[key] for key in self._contract_alias_index.get(alias, [])},
            key=lambda item: item.contract_key,
        )

    def price_rule(
        self,
        rule_id: str,
        moment: datetime,
        knowledge_cutoff: datetime,
        *,
        replay_mode: str = _REPLAY_AS_KNOWN_THEN,
    ) -> PriceRuleV1 | None:
        versions = self._select_versions(
            self._price_rules.get(rule_id, []), moment, knowledge_cutoff, replay_mode=replay_mode
        )
        return versions[-1] if versions else None

    def lot_rule(
        self,
        rule_id: str,
        moment: datetime,
        knowledge_cutoff: datetime,
        *,
        replay_mode: str = _REPLAY_AS_KNOWN_THEN,
    ) -> LotRuleV1 | None:
        versions = self._select_versions(
            self._lot_rules.get(rule_id, []), moment, knowledge_cutoff, replay_mode=replay_mode
        )
        return versions[-1] if versions else None

    def calendar_records(
        self,
        venue_id: str,
        segment_scope: str,
        day: date,
        knowledge_cutoff: datetime,
        *,
        live_only: bool = True,
        replay_mode: str = _REPLAY_AS_KNOWN_THEN,
    ) -> list[CalendarRecordV1]:
        knowledge_cutoff = _require_aware(knowledge_cutoff, field_name="knowledge_cutoff")
        out = []
        for item in self._calendars.get((venue_id, segment_scope, day), []):
            if live_only and item.lifecycle not in _LIVE_LIFECYCLES:
                continue
            if replay_mode == _REPLAY_AS_KNOWN_THEN and not self._knowable(item.available_at, knowledge_cutoff):
                continue
            out.append(item)
        return sorted(out, key=lambda item: item.record_id)

    # -- bounded cache ---------------------------------------------------------
    def cache_get(self, key: tuple[str, ...]) -> Any:
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache_hits += 1
            return self._cache[key]
        self._cache_misses += 1
        return None

    def cache_put(self, key: tuple[str, ...], value: Any) -> None:
        if self._cache_size <= 0:
            return
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def cache_stats(self) -> Mapping[str, int]:
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "entries": len(self._cache),
            "capacity": self._cache_size,
        }
