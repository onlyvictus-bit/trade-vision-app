"""Official-source BUILD-2 registry builder (parser: official-extract.v1).

Builds an isolated registry ONLY from the pinned official artifacts under
fixtures/market_identity/official/. Symbol spellings come from repository
legacy fixtures (labeled as such); venue domicile timezones record the
official Indian-exchange sites (session times in these documents are IST).
No regular-session hours are asserted for NSE because none were observed in
the official artifacts: OF-NSE-DAY-V1 is a full-day placeholder whose
intervals are never consulted (CLOSED_HOLIDAY records contribute no
intervals — proven by test).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.orb.candidate_intake import AvailabilityState, InstrumentType
from app.orb.market_identity import contracts as C
from app.orb.market_identity.registry import MarketIdentityRegistry
from app.orb.market_identity.source_receipts import receipt_for_bytes

OFFICIAL_DIR = Path(__file__).resolve().parent / "fixtures" / "market_identity" / "official"
RETRIEVED_AT = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
NSE_PUBLISHED_AT = datetime(2025, 12, 12, 0, 0, tzinfo=timezone.utc)

NSE_PDF_SHA = "1466db29f0b18d8b66524c6e47a8798f6dc8cdef4cf641e01b607e5925579274"
MCX_SPEC_PDF_SHA = "347d6512f5c296b7eef128fd8b65dcf91e1fda54a64e6f832b0209315ecaa7cb"


def file_sha(name: str) -> str:
    return hashlib.sha256((OFFICIAL_DIR / name).read_bytes()).hexdigest()


def official_receipts() -> dict[str, C.SourceReceiptV1]:
    api_bytes = (OFFICIAL_DIR / "nse_holiday_master_api_2026.json").read_bytes()
    page_bytes = (OFFICIAL_DIR / "mcx_observed_2026.txt").read_bytes()
    nse_pdf = (OFFICIAL_DIR / "nse_cmtr71775_2026_holidays.pdf").read_bytes()
    mcx_pdf = (OFFICIAL_DIR / "mcx_crude_oil_jan2026_spec.pdf").read_bytes()
    assert hashlib.sha256(nse_pdf).hexdigest() == NSE_PDF_SHA
    assert hashlib.sha256(mcx_pdf).hexdigest() == MCX_SPEC_PDF_SHA
    return {
        "OF-NSE-API": receipt_for_bytes(
            source_id="OF-NSE-API",
            source_type="EXCHANGE_HOLIDAY_MASTER_API",
            provider="NSE",
            document_id="holiday-master?type=trading",
            artifact_identity="official/nse_holiday_master_api_2026.json",
            content=api_bytes,
            parser_version="official-extract.v1",
            published_at=NSE_PUBLISHED_AT,
            available_at=RETRIEVED_AT,
        ),
        "OF-NSE-CIRCULAR": receipt_for_bytes(
            source_id="OF-NSE-CIRCULAR",
            source_type="EXCHANGE_CIRCULAR_PDF",
            provider="NSE",
            document_id="NSE/CMTR/71775",
            artifact_identity="official/nse_cmtr71775_2026_holidays.pdf",
            content=nse_pdf,
            parser_version="official-extract.v1",
            published_at=NSE_PUBLISHED_AT,
            available_at=RETRIEVED_AT,
        ),
        "OF-MCX-PAGE": receipt_for_bytes(
            source_id="OF-MCX-PAGE",
            source_type="EXCHANGE_PRODUCT_AND_HOLIDAY_PAGE_TEXT",
            provider="MCX",
            document_id="trading-holidays+crude-oil-product-page",
            artifact_identity="official/mcx_observed_2026.txt",
            content=page_bytes,
            parser_version="official-extract.v1",
            available_at=RETRIEVED_AT,
        ),
        "OF-MCX-SPEC": receipt_for_bytes(
            source_id="OF-MCX-SPEC",
            source_type="EXCHANGE_CONTRACT_SPEC_PDF",
            provider="MCX",
            document_id="crude-oil-january-2026-contract-onwards",
            artifact_identity="official/mcx_crude_oil_jan2026_spec.pdf",
            content=mcx_pdf,
            parser_version="official-extract.v1",
            available_at=RETRIEVED_AT,
        ),
    }


def build_official_registry(*, registry_id: str = "official-market-identity-v1") -> MarketIdentityRegistry:
    receipts = official_receipts()
    registry = MarketIdentityRegistry(registry_id=registry_id)
    for venue_id, segment in (("NSE", "CASH"), ("NSE", "DERIVATIVES"), ("MCX", "COMMODITY")):
        registry.add_venue(
            C.venue_record(
                venue_id=venue_id,
                exchange_code=venue_id,
                segment_code=segment,
                country_code="IN",
                venue_timezone="Asia/Kolkata",
                mic_or_registered_venue_code=None,
                source_receipt_ids=["OF-NSE-API"] if venue_id == "NSE" else ["OF-MCX-PAGE"],
                effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
                published_at=NSE_PUBLISHED_AT if venue_id == "NSE" else None,
                available_at=RETRIEVED_AT,
            )
        )
    # Placeholder NSE day profile: official NSE session hours were not
    # observed, so this profile exists only to satisfy the non-empty invariant
    # and is never consulted (holiday records contribute no intervals).
    registry.add_session_profile(
        C.session_record(
            profile_id="OF-NSE-DAY-V1",
            venue_id="NSE",
            segment_scope="CASH",
            timezone_name="Asia/Kolkata",
            trading_date_convention="PLACEHOLDER_FULL_DAY_NEVER_CONSULTED_FOR_HOLIDAYS",
            session_type=C.SessionType.REGULAR,
            opening_anchor_local="00:00",
            tradable_intervals=[C.TradingIntervalV1(start_local="00:00", end_local="23:59")],
            source_receipt_ids=["OF-NSE-API"],
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            published_at=NSE_PUBLISHED_AT,
            available_at=RETRIEVED_AT,
        )
    )
    registry.add_session_profile(
        C.session_record(
            profile_id="OF-MCX-DAY-V1",
            venue_id="MCX",
            segment_scope="COMMODITY",
            timezone_name="Asia/Kolkata",
            trading_date_convention="SESSION_LABEL_EQUALS_LOCAL_DATE_OF_SESSION_START",
            session_type=C.SessionType.REGULAR,
            opening_anchor_local="09:00",
            tradable_intervals=[
                C.TradingIntervalV1(start_local="09:00", end_local="17:00"),
                C.TradingIntervalV1(start_local="17:00", end_local="23:55"),
            ],
            close_semantics="LAST_TRADED_PRICE_AT_SESSION_END",
            settlement_semantics="CASH_SETTLED_AGAINST_DAILY_SETTLEMENT_REFERENCE",
            source_receipt_ids=["OF-MCX-PAGE"],
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            available_at=RETRIEVED_AT,
        )
    )
    # Symbol spellings from repository legacy fixtures (not official docs).
    registry.add_instrument(
        C.instrument_record(
            instrument_key="OF-NSE-CASH:RELIANCE",
            instrument_type=InstrumentType.NSE_EQUITY,
            venue_id="NSE",
            segment_id="CASH",
            canonical_symbol="RELIANCE",
            calendar_profile_id="OF-NSE-DAY-V1",
            source_receipt_ids=["OF-NSE-API"],
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            published_at=NSE_PUBLISHED_AT,
            available_at=RETRIEVED_AT,
        )
    )
    registry.add_instrument(
        C.instrument_record(
            instrument_key="OF-NSE-DERIV:NIFTY",
            instrument_type=InstrumentType.NSE_DERIVATIVE,
            venue_id="NSE",
            segment_id="DERIVATIVES",
            canonical_symbol="NIFTY",
            calendar_profile_id="OF-NSE-DAY-V1",
            source_receipt_ids=["OF-NSE-API"],
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            published_at=NSE_PUBLISHED_AT,
            available_at=RETRIEVED_AT,
        )
    )
    registry.add_instrument(
        C.instrument_record(
            instrument_key="OF-MCX-COMM:CRUDEOIL",
            instrument_type=InstrumentType.COMMODITY_FUTURE,
            venue_id="MCX",
            segment_id="COMMODITY",
            canonical_symbol="CRUDEOIL",
            underlying_instrument_key="CME-NYMEX:WTI",
            calendar_profile_id="OF-MCX-DAY-V1",
            source_receipt_ids=["OF-MCX-PAGE", "OF-MCX-SPEC"],
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            available_at=RETRIEVED_AT,
        )
    )
    # Observed futures series only: month label + 100-Barrel unit (the latter
    # observed on the options-series titles). No expiry, tick, lot,
    # settlement, or listing facts were observed: all stay missing.
    registry.add_contract(
        C.contract_record(
            contract_key="OF-MCX-COMM:CRUDEOIL-2026-01",
            product_key="OF-MCX-COMM:CRUDEOIL",
            venue_id="MCX",
            segment_id="COMMODITY",
            contract_month="2026-01",
            trading_unit="100 Barrels",
            eligible_data_bases=(C.DataBasis.RAW_CONTRACT,),
            source_receipt_ids=["OF-MCX-PAGE", "OF-MCX-SPEC"],
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            available_at=RETRIEVED_AT,
        )
    )
    payload = json.loads((OFFICIAL_DIR / "official_calendars.json").read_text(encoding="utf-8"))
    assert payload["parser_version"] == "official-extract.v1"
    for row in payload["calendars"]:
        override = row.get("tradable_intervals_override")
        registry.add_calendar_record(
            C.calendar_record(
                record_id=row["record_id"],
                effective_date=date.fromisoformat(row["effective_date"]),
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
                published_at=NSE_PUBLISHED_AT if row["venue_id"] == "NSE" else None,
                available_at=RETRIEVED_AT,
                supersedes_record_id=row.get("supersedes_record_id"),
                lifecycle=C.RegistryLifecycle(row.get("lifecycle", "DRAFT")),
            )
        )
    return registry
