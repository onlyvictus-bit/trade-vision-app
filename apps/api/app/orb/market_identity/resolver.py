"""Deterministic BUILD-2 identity resolver: resolve_market_identity().

Given PIT identity context (instrument key or provider alias, optional
venue/segment/contract hints, decision instant, knowledge cutoff, requested
data basis), return a canonical OrbMarketIdentityV1 when uniquely proven,
or an explicit AMBIGUOUS / STALE / UNAVAILABLE / ERROR receipt with
machine-readable reason codes. Never returns the first of conflicting
matches; never falls back to NSE; never invents identity.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from ..candidate_intake import AvailabilityState, InstrumentType, canonical_sha256
from . import session as session_math
from .contracts import (
    ORB_MARKET_IDENTITY_VERSION,
    CalendarRecordV1,
    ContractProfileV1,
    DataBasis,
    InstrumentProfileV1,
    MarketIdentityResolutionV1,
    MarketIdentityV1,
    ResolutionState,
    SessionProfileV1,
    SessionType,
    SettlementType,
    _canonical_record,
    _finalize_record,
)
from .registry import MarketIdentityRegistry, RegistryError, _REPLAY_AS_KNOWN_THEN

_DERIVATIVE_TYPES = frozenset({InstrumentType.NSE_DERIVATIVE, InstrumentType.COMMODITY_FUTURE})

_CASH_OK_BASES = frozenset({DataBasis.RAW_CASH, DataBasis.CORPORATE_ACTION_ADJUSTED})


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def resolve_market_identity(
    registry: MarketIdentityRegistry,
    *,
    instrument_key: str | None = None,
    provider: str | None = None,
    provider_alias: str | None = None,
    venue_id: str | None = None,
    segment_id: str | None = None,
    contract_key: str | None = None,
    as_of: datetime,
    knowledge_cutoff: datetime,
    data_basis: DataBasis = DataBasis.RAW_CASH,
    replay_mode: str = _REPLAY_AS_KNOWN_THEN,
) -> MarketIdentityResolutionV1:
    """Single canonical resolver. All inputs are hashed into input_hash; the
    output hash covers semantic content only (latency excluded)."""
    started = time.perf_counter()
    as_of = _require_aware(as_of, field_name="as_of")
    knowledge_cutoff = _require_aware(knowledge_cutoff, field_name="knowledge_cutoff")
    # Normalize textual identity inputs before hashing: " reliance " and
    # "RELIANCE" are the same claim and must replay to the same receipt.
    instrument_key = instrument_key.strip() if instrument_key else None
    provider = provider.strip() if provider else None
    provider_alias = provider_alias.strip().upper() if provider_alias else None
    venue_id = venue_id.strip() if venue_id else None
    segment_id = segment_id.strip() if segment_id else None
    contract_key = contract_key.strip() if contract_key else None
    cache_key = (
        registry.registry_id,
        registry.registry_version_hash(),
        instrument_key or "",
        provider or "",
        provider_alias or "",
        venue_id or "",
        segment_id or "",
        contract_key or "",
        as_of.isoformat(),
        knowledge_cutoff.isoformat(),
        data_basis.value,
        replay_mode,
    )
    cached = registry.cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        resolution = _resolve(
            registry,
            instrument_key=instrument_key,
            provider=provider,
            provider_alias=provider_alias,
            venue_id=venue_id,
            segment_id=segment_id,
            contract_key=contract_key,
            as_of=as_of,
            knowledge_cutoff=knowledge_cutoff,
            data_basis=data_basis,
            replay_mode=replay_mode,
            cache_key=cache_key,
        )
    except RegistryError as exc:
        resolution = _unresolved_from_registry_error(
            exc, as_of=as_of, knowledge_cutoff=knowledge_cutoff, cache_key=cache_key
        )
    except Exception:  # noqa: BLE001 - resolver boundary must stay machine-readable
        resolution = _unresolved(
            state=ResolutionState.ERROR,
            as_of=as_of,
            knowledge_cutoff=knowledge_cutoff,
            cache_key=cache_key,
            reason_codes=("RESOLUTION_ERROR",),
        )
    latency_ms = (time.perf_counter() - started) * 1000.0
    resolved = replace(resolution, latency_ms=latency_ms)
    registry.cache_put(cache_key, resolved)
    return resolved


def _input_hash(cache_key: tuple[str, ...]) -> str:
    return canonical_sha256({"resolver": "resolve_market_identity.v1", "inputs": list(cache_key)})


def _state_for_reason(reason: str) -> ResolutionState:
    if "STALE" in reason:
        return ResolutionState.STALE
    if "AMBIGUOUS" in reason or "CONFLICT" in reason:
        return ResolutionState.AMBIGUOUS
    return ResolutionState.UNAVAILABLE


def _unresolved_from_registry_error(
    exc: RegistryError,
    *,
    as_of: datetime,
    knowledge_cutoff: datetime,
    cache_key: tuple[str, ...],
) -> MarketIdentityResolutionV1:
    reason = str(exc)
    return _unresolved(
        state=_state_for_reason(reason),
        as_of=as_of,
        knowledge_cutoff=knowledge_cutoff,
        cache_key=cache_key,
        reason_codes=(reason,),
    )


def _unresolved(
    *,
    state: ResolutionState,
    as_of: datetime,
    knowledge_cutoff: datetime,
    cache_key: tuple[str, ...],
    reason_codes: Sequence[str],
    candidates: Sequence[str] = (),
    receipts: Sequence[str] = (),
    rules: Sequence[str] = (),
) -> MarketIdentityResolutionV1:
    body = {
        "state": state.value,
        "reasons": sorted(set(reason_codes)),
        "candidates": sorted(set(candidates)),
    }
    return MarketIdentityResolutionV1(
        schema_version=ORB_MARKET_IDENTITY_VERSION,
        state=state,
        input_hash=_input_hash(cache_key),
        output_hash=canonical_sha256(body),
        knowledge_cutoff=knowledge_cutoff,
        as_of=as_of,
        identity=None,
        candidate_identity_ids=tuple(sorted(set(candidates))),
        source_receipt_ids=tuple(sorted(set(receipts))),
        rule_versions=tuple(sorted(set(rules))),
        reason_codes=tuple(sorted(set(reason_codes))),
    )


def _resolve(
    registry: MarketIdentityRegistry,
    *,
    instrument_key: str | None,
    provider: str | None,
    provider_alias: str | None,
    venue_id: str | None,
    segment_id: str | None,
    contract_key: str | None,
    as_of: datetime,
    knowledge_cutoff: datetime,
    data_basis: DataBasis,
    replay_mode: str,
    cache_key: tuple[str, ...],
) -> MarketIdentityResolutionV1:
    reasons: list[str] = []
    receipts: list[str] = []
    rules: list[str] = []

    instrument = _resolve_instrument(
        registry, instrument_key, provider, provider_alias, venue_id, segment_id, as_of, knowledge_cutoff, cache_key
    )
    if isinstance(instrument, MarketIdentityResolutionV1):
        return instrument
    venue = registry.venue(instrument.venue_id, instrument.segment_id)
    receipts.extend(venue.source_receipt_ids)
    receipts.extend(instrument.source_receipt_ids)

    contract = _resolve_contract(
        registry, instrument, contract_key, as_of, knowledge_cutoff, replay_mode, reasons, receipts, rules
    )
    if isinstance(contract, MarketIdentityResolutionV1):
        return contract

    located = _resolve_session(
        registry, venue, instrument, as_of, knowledge_cutoff, replay_mode, reasons, receipts, rules
    )
    if isinstance(located, MarketIdentityResolutionV1):
        return located
    profile, calendar = located

    price_rule, lot_rule = _resolve_economics(
        registry, instrument, contract, as_of, knowledge_cutoff, replay_mode, reasons, receipts, rules
    )

    basis_reason = _check_data_basis(instrument, contract, data_basis)
    if basis_reason is not None:
        return _unresolved(
            state=ResolutionState.UNAVAILABLE,
            as_of=as_of,
            knowledge_cutoff=knowledge_cutoff,
            cache_key=cache_key,
            reason_codes=(basis_reason,),
            receipts=receipts,
            rules=rules,
        )

    if contract is not None and contract.settlement_type is SettlementType.NOT_APPLICABLE:
        reasons.append("SETTLEMENT_SEMANTICS_UNAVAILABLE")
    if calendar.session_type is SessionType.MOCK:
        reasons.append("MOCK_SESSION")
    if calendar.session_type is SessionType.SPECIAL:
        reasons.append("SPECIAL_SESSION")

    identity = _bind_identity(
        registry=registry,
        venue=venue,
        instrument=instrument,
        contract=contract,
        profile=profile,
        calendar=calendar,
        price_rule=price_rule,
        lot_rule=lot_rule,
        data_basis=data_basis,
        as_of=as_of,
        knowledge_cutoff=knowledge_cutoff,
        receipts=receipts,
        rules=rules,
        cache_key=cache_key,
    )
    body = {"state": ResolutionState.RESOLVED.value, "identity_hash": identity.market_identity_hash}
    return MarketIdentityResolutionV1(
        schema_version=ORB_MARKET_IDENTITY_VERSION,
        state=ResolutionState.RESOLVED,
        input_hash=_input_hash(cache_key),
        output_hash=canonical_sha256(body),
        knowledge_cutoff=knowledge_cutoff,
        as_of=as_of,
        identity=identity,
        candidate_identity_ids=(),
        source_receipt_ids=tuple(sorted(set(receipts))),
        rule_versions=tuple(sorted(set(rules))),
        reason_codes=tuple(sorted(set(reasons))),
    )


def _resolve_instrument(
    registry: MarketIdentityRegistry,
    instrument_key: str | None,
    provider: str | None,
    provider_alias: str | None,
    venue_id: str | None,
    segment_id: str | None,
    as_of: datetime,
    knowledge_cutoff: datetime,
    cache_key: tuple[str, ...],
) -> InstrumentProfileV1 | MarketIdentityResolutionV1:
    if instrument_key is not None:
        try:
            candidate = registry.instrument(instrument_key.strip())
        except RegistryError:
            return _unresolved(
                state=ResolutionState.UNAVAILABLE,
                as_of=as_of,
                knowledge_cutoff=knowledge_cutoff,
                cache_key=cache_key,
                reason_codes=("IDENTITY_NOT_FOUND",),
            )
        if not MarketIdentityRegistry._market_effective(
            candidate.effective_from, candidate.effective_to, as_of
        ) or not MarketIdentityRegistry._knowable(candidate.available_at, knowledge_cutoff):
            return _unresolved(
                state=ResolutionState.UNAVAILABLE,
                as_of=as_of,
                knowledge_cutoff=knowledge_cutoff,
                cache_key=cache_key,
                reason_codes=("IDENTITY_NOT_FOUND",),
            )
        if venue_id is not None and candidate.venue_id != venue_id:
            return _unresolved(
                state=ResolutionState.AMBIGUOUS,
                as_of=as_of,
                knowledge_cutoff=knowledge_cutoff,
                cache_key=cache_key,
                reason_codes=("VENUE_CONFLICT",),
                candidates=(candidate.instrument_key,),
            )
        if segment_id is not None and candidate.segment_id != segment_id:
            return _unresolved(
                state=ResolutionState.AMBIGUOUS,
                as_of=as_of,
                knowledge_cutoff=knowledge_cutoff,
                cache_key=cache_key,
                reason_codes=("SEGMENT_CONFLICT",),
                candidates=(candidate.instrument_key,),
            )
        return candidate
    if provider_alias is None:
        return _unresolved(
            state=ResolutionState.UNAVAILABLE,
            as_of=as_of,
            knowledge_cutoff=knowledge_cutoff,
            cache_key=cache_key,
            reason_codes=("IDENTITY_NOT_FOUND",),
        )
    matches = registry.instruments_for_symbol(provider_alias)
    matches = [
        item
        for item in matches
        if MarketIdentityRegistry._market_effective(item.effective_from, item.effective_to, as_of)
        and MarketIdentityRegistry._knowable(item.available_at, knowledge_cutoff)
    ]
    if provider is not None:
        # Provider namespace disambiguation: the alias must be claimed under
        # this provider's identifiers (e.g. "hstry:NSE:RELIANCE"). An alias
        # claimed by two instruments under the same provider stays ambiguous.
        matches = [
            item
            for item in matches
            if any(pid == provider or pid.startswith(provider + ":") for pid in item.provider_identifiers)
        ]
    if venue_id is not None:
        matches = [item for item in matches if item.venue_id == venue_id]
    if segment_id is not None:
        matches = [item for item in matches if item.segment_id == segment_id]
    if not matches:
        return _unresolved(
            state=ResolutionState.UNAVAILABLE,
            as_of=as_of,
            knowledge_cutoff=knowledge_cutoff,
            cache_key=cache_key,
            reason_codes=("IDENTITY_NOT_FOUND",),
        )
    if len(matches) > 1:
        return _unresolved(
            state=ResolutionState.AMBIGUOUS,
            as_of=as_of,
            knowledge_cutoff=knowledge_cutoff,
            cache_key=cache_key,
            reason_codes=("IDENTITY_AMBIGUOUS",),
            candidates=[item.instrument_key for item in matches],
        )
    return matches[0]


def _resolve_contract(
    registry: MarketIdentityRegistry,
    instrument: InstrumentProfileV1,
    contract_key: str | None,
    as_of: datetime,
    knowledge_cutoff: datetime,
    replay_mode: str,
    reasons: list[str],
    receipts: list[str],
    rules: list[str],
) -> ContractProfileV1 | None | MarketIdentityResolutionV1:
    needs_contract = instrument.instrument_type in _DERIVATIVE_TYPES
    if not needs_contract:
        return None
    if contract_key is not None:
        try:
            candidate = registry.contract(contract_key.strip())
        except RegistryError:
            raise RegistryError("CONTRACT_NOT_FOUND")
        if candidate.product_key != instrument.instrument_key:
            raise RegistryError("CONTRACT_AMBIGUOUS")
        if not MarketIdentityRegistry._market_effective(candidate.effective_from, candidate.effective_to, as_of):
            raise RegistryError("CONTRACT_NOT_EFFECTIVE")
        if not MarketIdentityRegistry._knowable(candidate.available_at, knowledge_cutoff):
            raise RegistryError("SOURCE_NOT_CAUSAL")
        if candidate.last_trade_at is not None and as_of > candidate.last_trade_at:
            raise RegistryError("CONTRACT_EXPIRED")
        if candidate.first_trade_at is not None and as_of < candidate.first_trade_at:
            raise RegistryError("CONTRACT_NOT_EFFECTIVE")
        receipts.extend(candidate.source_receipt_ids)
        return candidate
    live = [
        item
        for item in registry.contracts_for_product(instrument.instrument_key, as_of)
        if MarketIdentityRegistry._knowable(item.available_at, knowledge_cutoff)
    ]
    if not live:
        raise RegistryError("CONTRACT_NOT_FOUND")
    if len(live) > 1:
        raise RegistryError("CONTRACT_AMBIGUOUS")
    receipts.extend(live[0].source_receipt_ids)
    return live[0]


def _resolve_session(
    registry: MarketIdentityRegistry,
    venue: Any,
    instrument: InstrumentProfileV1,
    as_of: datetime,
    knowledge_cutoff: datetime,
    replay_mode: str,
    reasons: list[str],
    receipts: list[str],
    rules: list[str],
) -> tuple[SessionProfileV1, CalendarRecordV1] | MarketIdentityResolutionV1:
    if instrument.calendar_profile_id is None:
        raise RegistryError("SESSION_NOT_RESOLVED")
    try:
        profile = registry.session_profile(instrument.calendar_profile_id)
    except RegistryError:
        raise RegistryError("SESSION_NOT_RESOLVED")
    rules.append(f"{profile.profile_id}:{profile.schema_version}")
    zone = ZoneInfo(profile.timezone_name)
    local = as_of.astimezone(zone)
    candidate_days = sorted({local.date(), local.date() - timedelta(days=1)})
    dated: list[CalendarRecordV1] = []
    for day in candidate_days:
        dated.extend(
            registry.calendar_records(
                venue.venue_id, instrument.segment_id, day, knowledge_cutoff, replay_mode=replay_mode
            )
        )
    if not dated:
        superseded = []
        for day in candidate_days:
            superseded.extend(
                registry.calendar_records(
                    venue.venue_id,
                    instrument.segment_id,
                    day,
                    knowledge_cutoff,
                    live_only=False,
                    replay_mode=replay_mode,
                )
            )
        if superseded:
            raise RegistryError("CALENDAR_STALE")
        raise RegistryError("CALENDAR_UNAVAILABLE")
    groups: dict[str, list[CalendarRecordV1]] = {}
    for record in dated:
        located = session_math.locate_timestamp(profile, as_of, record)
        if not located["in_session"]:
            continue
        # Date consistency: a record governs only the session on its own
        # effective date. Without this, yesterday's record would also match
        # today's time-of-day and every date would be a conflict.
        if str(located["session_label"] or "") != record.effective_date.isoformat():
            continue
        key = canonical_sha256(
            {
                "session_type": record.session_type.value,
                "profile": record.profile_id,
                "intervals": [
                    [i.start_local, i.end_local, i.phase.value]
                    for i in session_math.effective_intervals(profile, record)
                ],
            }
        )
        groups.setdefault(key, []).append(record)
    if not groups:
        raise RegistryError("SESSION_NOT_RESOLVED")
    if len(groups) > 1:
        raise RegistryError("CALENDAR_CONFLICT")
    chosen = sorted(list(groups.values())[0], key=lambda item: item.record_id)[0]
    receipts.extend([chosen.source_document_id] if chosen.source_document_id != "UNSPECIFIED" else [])
    rules.append(f"{chosen.record_id}:{chosen.schema_version}")
    return profile, chosen


def _resolve_economics(
    registry: MarketIdentityRegistry,
    instrument: InstrumentProfileV1,
    contract: ContractProfileV1 | None,
    as_of: datetime,
    knowledge_cutoff: datetime,
    replay_mode: str,
    reasons: list[str],
    receipts: list[str],
    rules: list[str],
) -> tuple[Any, Any]:
    price_rule = None
    lot_rule = None
    rule_id = (contract.tick_rule_id if contract is not None else None) or instrument.tick_rule_id
    if rule_id is not None:
        price_rule = registry.price_rule(rule_id, as_of, knowledge_cutoff, replay_mode=replay_mode)
        if price_rule is None:
            raise RegistryError("PRICE_RULE_UNAVAILABLE")
        rules.append(f"{price_rule.rule_id}:{price_rule.rule_version}")
    else:
        reasons.append("PRICE_RULE_UNAVAILABLE")
    lot_id = instrument.lot_rule_id
    if lot_id is not None:
        lot_rule = registry.lot_rule(lot_id, as_of, knowledge_cutoff, replay_mode=replay_mode)
        if lot_rule is None:
            raise RegistryError("LOT_RULE_UNAVAILABLE")
        rules.append(f"{lot_rule.rule_id}:{lot_rule.rule_version}")
    elif instrument.instrument_type in _DERIVATIVE_TYPES:
        reasons.append("LOT_RULE_UNAVAILABLE")
    return price_rule, lot_rule


def _check_data_basis(
    instrument: InstrumentProfileV1,
    contract: ContractProfileV1 | None,
    data_basis: DataBasis,
) -> str | None:
    if data_basis is DataBasis.UNKNOWN:
        return "DATA_BASIS_CONFLICT"
    if contract is None:
        if data_basis in _CASH_OK_BASES or data_basis is DataBasis.REGISTERED_OTHER:
            return None
        return "DATA_BASIS_CONFLICT"
    eligible = set(contract.eligible_data_bases)
    if data_basis not in eligible:
        return "DATA_BASIS_CONFLICT"
    if data_basis in {
        DataBasis.BACK_ADJUSTED_CONTINUOUS,
        DataBasis.RATIO_ADJUSTED_CONTINUOUS,
        DataBasis.UNADJUSTED_CONTINUOUS,
    } and not contract.roll_map_id:
        return "DATA_BASIS_CONFLICT"
    return None


def _bind_identity(
    *,
    registry: MarketIdentityRegistry,
    venue: Any,
    instrument: InstrumentProfileV1,
    contract: ContractProfileV1 | None,
    profile: SessionProfileV1,
    calendar: CalendarRecordV1,
    price_rule: Any,
    lot_rule: Any,
    data_basis: DataBasis,
    as_of: datetime,
    knowledge_cutoff: datetime,
    receipts: Sequence[str],
    rules: Sequence[str],
    cache_key: tuple[str, ...],
) -> MarketIdentityV1:
    payload = {
        "schema_version": ORB_MARKET_IDENTITY_VERSION,
        "venue_id": venue.venue_id,
        "instrument_key": instrument.instrument_key,
        "contract_key": contract.contract_key if contract else None,
        "session_profile_id": profile.profile_id,
        "calendar_record_id": calendar.record_id,
        "price_rule_id": price_rule.rule_id if price_rule else None,
        "lot_rule_id": lot_rule.rule_id if lot_rule else None,
        "data_basis": data_basis.value,
        "as_of": as_of.isoformat(),
        "knowledge_cutoff": knowledge_cutoff.isoformat(),
        "registry": registry.registry_id,
        "inputs": list(cache_key),
    }
    identity_id = f"orb-market-identity:{canonical_sha256(payload)[:24]}"
    draft = MarketIdentityV1(
        schema_version=ORB_MARKET_IDENTITY_VERSION,
        market_identity_id=identity_id,
        market_identity_hash="",
        venue_id=venue.venue_id,
        venue_version=venue.schema_version,
        venue_hash=venue.record_hash,
        instrument_key=instrument.instrument_key,
        instrument_version=instrument.schema_version,
        instrument_hash=instrument.record_hash,
        contract_key=contract.contract_key if contract else None,
        contract_version=contract.schema_version if contract else None,
        contract_hash=contract.record_hash if contract else None,
        session_profile_id=profile.profile_id,
        session_version=profile.schema_version,
        session_hash=profile.record_hash,
        calendar_record_id=calendar.record_id,
        calendar_version=calendar.schema_version,
        calendar_hash=calendar.record_hash,
        price_rule_id=price_rule.rule_id if price_rule else None,
        price_rule_version=price_rule.rule_version if price_rule else None,
        price_rule_hash=price_rule.record_hash if price_rule else None,
        lot_rule_id=lot_rule.rule_id if lot_rule else None,
        lot_rule_version=lot_rule.rule_version if lot_rule else None,
        lot_rule_hash=lot_rule.record_hash if lot_rule else None,
        data_basis=data_basis,
        as_of=as_of,
        knowledge_cutoff=knowledge_cutoff,
        source_receipt_ids=tuple(sorted(set(receipts))),
        availability=AvailabilityState.AVAILABLE,
    )
    finalized = _finalize_record(draft, ("market_identity_hash",))
    return finalized


def availability_summary(resolution: MarketIdentityResolutionV1) -> Mapping[str, Any]:
    """Bounded operational receipt for logging/monitoring (no reasoning)."""
    identity = resolution.identity
    return {
        "state": resolution.state.value,
        "contract_state": "NOT_APPLICABLE" if identity is None or identity.contract_key is None else "BOUND",
        "session_profile": identity.session_profile_id if identity else None,
        "calendar_record": identity.calendar_record_id if identity else None,
        "price_rule": identity.price_rule_id if identity else None,
        "lot_rule": identity.lot_rule_id if identity else None,
        "data_basis": identity.data_basis.value if identity else None,
        "ambiguity_count": len(resolution.candidate_identity_ids),
        "reason_codes": list(resolution.reason_codes),
        "latency_ms": resolution.latency_ms,
    }
