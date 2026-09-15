"""Shared BUILD-2 fixture loader: JSON fixtures -> versioned registry.

Load order respects dependencies (venues -> sessions -> instruments ->
contracts/rules -> calendars). Calendar lifecycles load as declared; the
append-only correction pair (NSE-2026-09-21 V1 SUPERSEDED / V2 ACTIVE)
loads in declared state.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from app.orb.candidate_intake import AvailabilityState, InstrumentType
from app.orb.market_identity import contracts as C
from app.orb.market_identity.registry import MarketIdentityRegistry

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "market_identity"


def _dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"fixture datetimes must be aware: {value!r}")
    return parsed


def _d(value: str) -> date:
    return date.fromisoformat(value)


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def build_fixture_registry(*, registry_id: str = "test-market-identity-v1") -> MarketIdentityRegistry:
    registry = MarketIdentityRegistry(registry_id=registry_id)
    venues = _load("venues.json")
    assert venues["provenance"].startswith("TEST_")
    for row in venues["venues"]:
        aliases = [
            C.VenueAliasV1(
                alias=item["alias"],
                provider=item["provider"],
                effective_from=_dt(item["effective_from"]),
                effective_to=_dt(item["effective_to"]),
            )
            for item in row.get("provider_aliases", [])
        ]
        registry.add_venue(
            C.venue_record(
                venue_id=row["venue_id"],
                exchange_code=row["exchange_code"],
                segment_code=row["segment_code"],
                country_code=row["country_code"],
                venue_timezone=row["venue_timezone"],
                operating_venue_id=row.get("operating_venue_id"),
                mic_or_registered_venue_code=row.get("mic_or_registered_venue_code"),
                provider_aliases=aliases,
                source_receipt_ids=row.get("source_receipt_ids", []),
                availability=AvailabilityState(row.get("availability", "AVAILABLE")),
                effective_from=_dt(row.get("effective_from")),
                effective_to=_dt(row.get("effective_to")),
                published_at=_dt(row.get("published_at")),
                available_at=_dt(row.get("available_at")),
            )
        )
    sessions = _load("sessions.json")
    assert sessions["provenance"].startswith("TEST_")
    for row in sessions["sessions"]:
        registry.add_session_profile(
            C.session_record(
                profile_id=row["profile_id"],
                venue_id=row["venue_id"],
                segment_scope=row["segment_scope"],
                timezone_name=row["timezone_name"],
                trading_date_convention=row["trading_date_convention"],
                session_type=C.SessionType(row["session_type"]),
                opening_anchor_local=row["opening_anchor_local"],
                tradable_intervals=[
                    C.TradingIntervalV1(
                        start_local=item["start_local"],
                        end_local=item["end_local"],
                        phase=C.SessionPhase(item.get("phase", "REGULAR")),
                    )
                    for item in row["tradable_intervals"]
                ],
                trading_phases=tuple(C.SessionPhase(item) for item in row.get("trading_phases", ["REGULAR"])),
                break_intervals=tuple(
                    C.TradingIntervalV1(
                        start_local=item["start_local"],
                        end_local=item["end_local"],
                        phase=C.SessionPhase(item.get("phase", "MID_SESSION_BREAK")),
                    )
                    for item in row.get("break_intervals", [])
                ),
                close_semantics=row.get("close_semantics", "UNSPECIFIED"),
                settlement_semantics=row.get("settlement_semantics", "UNSPECIFIED"),
                calendar_rule_id=row.get("calendar_rule_id"),
                exception_rule_ids=row.get("exception_rule_ids", []),
                effective_from=_dt(row.get("effective_from")),
                effective_to=_dt(row.get("effective_to")),
                published_at=_dt(row.get("published_at")),
                available_at=_dt(row.get("available_at")),
                source_receipt_ids=row.get("source_receipt_ids", []),
            )
        )
    instruments = _load("instruments.json")
    assert instruments["provenance"].startswith("TEST_")
    for row in instruments["instruments"]:
        registry.add_instrument(
            C.instrument_record(
                instrument_key=row["instrument_key"],
                instrument_type=InstrumentType(row["instrument_type"]),
                venue_id=row["venue_id"],
                segment_id=row["segment_id"],
                canonical_symbol=row["canonical_symbol"],
                display_symbol=row.get("display_symbol"),
                provider_identifiers=row.get("provider_identifiers", []),
                provider_aliases=row.get("provider_aliases", []),
                isin=row.get("isin"),
                underlying_instrument_key=row.get("underlying_instrument_key"),
                asset_class=row.get("asset_class", "UNSPECIFIED"),
                currency=row.get("currency", "UNSPECIFIED"),
                quote_currency=row.get("quote_currency", "UNSPECIFIED"),
                price_basis_family=row.get("price_basis_family", "UNSPECIFIED"),
                tick_rule_id=row.get("tick_rule_id"),
                price_precision=row.get("price_precision"),
                lot_rule_id=row.get("lot_rule_id"),
                calendar_profile_id=row.get("calendar_profile_id"),
                context_applicability=row.get("context_applicability", []),
                availability=AvailabilityState(row.get("availability", "AVAILABLE")),
                effective_from=_dt(row.get("effective_from")),
                effective_to=_dt(row.get("effective_to")),
                published_at=_dt(row.get("published_at")),
                available_at=_dt(row.get("available_at")),
                source_receipt_ids=row.get("source_receipt_ids", []),
            )
        )
    contracts = _load("contracts.json")
    assert contracts["provenance"].startswith("TEST_")
    for row in contracts["contracts"]:
        registry.add_contract(
            C.contract_record(
                contract_key=row["contract_key"],
                product_key=row["product_key"],
                venue_id=row["venue_id"],
                segment_id=row["segment_id"],
                provider_contract_ids=row.get("provider_contract_ids", []),
                provider_aliases=row.get("provider_aliases", []),
                contract_month=row.get("contract_month"),
                listing_date=_d(row["listing_date"]) if row.get("listing_date") else None,
                first_trade_at=_dt(row.get("first_trade_at")),
                last_trade_at=_dt(row.get("last_trade_at")),
                expiry_at=_dt(row.get("expiry_at")),
                expiry_rule_id=row.get("expiry_rule_id"),
                settlement_type=C.SettlementType(row.get("settlement_type", "NOT_APPLICABLE")),
                daily_settlement_reference=row.get("daily_settlement_reference", "UNSPECIFIED"),
                final_settlement_reference=row.get("final_settlement_reference", "UNSPECIFIED"),
                delivery_semantics=row.get("delivery_semantics", "UNSPECIFIED"),
                trading_unit=row.get("trading_unit", "UNSPECIFIED"),
                lot_size=row.get("lot_size"),
                multiplier=row.get("multiplier"),
                quote_basis=row.get("quote_basis", "UNSPECIFIED"),
                currency=row.get("currency", "UNSPECIFIED"),
                tick_rule_id=row.get("tick_rule_id"),
                price_precision=row.get("price_precision"),
                eligible_data_bases=tuple(C.DataBasis(item) for item in row.get("eligible_data_bases", [])),
                roll_map_id=row.get("roll_map_id"),
                availability=AvailabilityState(row.get("availability", "AVAILABLE")),
                effective_from=_dt(row.get("effective_from")),
                effective_to=_dt(row.get("effective_to")),
                published_at=_dt(row.get("published_at")),
                available_at=_dt(row.get("available_at")),
                source_receipt_ids=row.get("source_receipt_ids", []),
            )
        )
    for row in contracts["price_rules"]:
        registry.add_price_rule(
            C.price_rule_record(
                rule_id=row["rule_id"],
                rule_version=row["rule_version"],
                venue_id=row["venue_id"],
                segment_scope=row["segment_scope"],
                instrument_scope=row["instrument_scope"],
                rule_type=C.PriceRuleType(row["rule_type"]),
                tick=row["tick"],
                price_precision=row["price_precision"],
                bands=tuple(
                    C.PriceBandV1(upper_bound_inclusive=item["upper_bound_inclusive"], tick=item["tick"])
                    for item in row.get("bands", [])
                ),
                rounding_semantics=row.get("rounding_semantics", "EXACT_GRID"),
                effective_from=_dt(row.get("effective_from")),
                effective_to=_dt(row.get("effective_to")),
                published_at=_dt(row.get("published_at")),
                available_at=_dt(row.get("available_at")),
                source_document_id=row.get("source_document_id"),
                source_hash=row.get("source_hash"),
                parser_version=row.get("parser_version", "TEST-FIXTURE-V1"),
            )
        )
    for row in contracts["lot_rules"]:
        registry.add_lot_rule(
            C.lot_rule_record(
                rule_id=row["rule_id"],
                rule_version=row["rule_version"],
                venue_id=row["venue_id"],
                segment_scope=row["segment_scope"],
                instrument_scope=row["instrument_scope"],
                trading_unit=row["trading_unit"],
                lot_size=row["lot_size"],
                multiplier=row["multiplier"],
                quotation_unit=row.get("quotation_unit", "UNSPECIFIED"),
                currency=row.get("currency", "UNSPECIFIED"),
                effective_from=_dt(row.get("effective_from")),
                effective_to=_dt(row.get("effective_to")),
                published_at=_dt(row.get("published_at")),
                available_at=_dt(row.get("available_at")),
                source_hash=row.get("source_hash"),
            )
        )
    calendars = _load("calendars.json")
    assert calendars["provenance"].startswith("TEST_")
    for row in calendars["calendars"]:
        override = row.get("tradable_intervals_override")
        registry.add_calendar_record(
            C.calendar_record(
                record_id=row["record_id"],
                effective_date=_d(row["effective_date"]),
                venue_id=row["venue_id"],
                segment_scope=row["segment_scope"],
                profile_id=row["profile_id"],
                session_type=C.SessionType(row["session_type"]),
                session_label=row["session_label"],
                tradable_intervals_override=(
                    tuple(
                        C.TradingIntervalV1(
                            start_local=item["start_local"],
                            end_local=item["end_local"],
                            phase=C.SessionPhase(item.get("phase", "REGULAR")),
                        )
                        for item in override
                    )
                    if override is not None
                    else None
                ),
                contract_events=row.get("contract_events", []),
                source_document_id=row.get("source_document_id", "UNSPECIFIED"),
                source_hash=row.get("source_hash"),
                published_at=_dt(row.get("published_at")),
                available_at=_dt(row.get("available_at")),
                supersedes_record_id=row.get("supersedes_record_id"),
                lifecycle=C.RegistryLifecycle(row.get("lifecycle", "DRAFT")),
            )
        )
    return registry
