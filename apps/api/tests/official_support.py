"""Official-source BUILD-2 registry builder (parser: official-extract.v1).

Builds an isolated registry ONLY from the pinned official artifacts under
fixtures/market_identity/official/. Symbol spellings come from repository
legacy fixtures (provenance LEGACY-MARKET-IDENTITY-INSTRUMENT-FIXTURE, never
an exchange API); venue domicile timezones record the official
Indian-exchange sites (session times in these documents are IST).

Source-truth posture (BUILD-2 review-hold remediation):
- OF-NSE-API.published_at is None (API artifact states no publication
  timestamp). The 2025-12-12 date belongs ONLY to OF-NSE-CIRCULAR
  (NSE/CMTR/71775). API-backed facts never inherit the circular date.
- No official object carries an effective_from: none is observed, so all
  stay None (explicit missingness, never an invented effective start).
- OF-MCX-DAY-V1 is a placeholder that asserts NO exact evening close: the
  pinned MCX text gives "5:00pm - 11:30 / 11:55pm" with no rule selecting
  which close applies, so the official set models no resolvable evening
  boundary. Observed morning/evening OPEN facts survive only as calendar
  contract_events + raw text, never as exact intervals. Exact
  cross-midnight/session machinery is proven by the synthetic fixtures.
- MCX close/settlement semantics stay UNSPECIFIED (settlement references
  were explicitly NOT observed).
- No exact crude futures ContractProfileV1 is built: the January-2026 row
  proves series existence only, and the barrel-quantity text was observed on
  options titles, not as a futures trading_unit. Product/underlying facts that are
  observed (MCX crude-oil product, CME/NYMEX WTI underlying) are kept on
  the instrument.
- MCX 2026-11-08 (Muhurat) has no holiday-table row proving closure, so it
  is a non-active SPECIAL evidence record (lifecycle DRAFT): the
  MUHURAT_TRADING_ANNOUNCED_TIMINGS_PENDING_CIRCULAR announcement is
  preserved, exact membership stays unavailable, and unknown timing never
  becomes CLOSED_HOLIDAY.
- Every official CalendarRecordV1 is hash-bound: source_hash equals the
  exact SourceReceiptV1.content_hash of the raw pinned bytes named by the
  row's source_receipt_id (never the generated mapping file).

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
# Synthetic architecture fixture that supplies RELIANCE/NIFTY spellings only
# (never exchange identity). Hashed at load so the legacy receipt binds the
# exact repository bytes used by this test set.
LEGACY_INSTRUMENTS_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "market_identity" / "instruments.json"
)
RETRIEVED_AT = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
# 2025-12-12 belongs ONLY to NSE circular NSE/CMTR/71775. It must never be
# applied to API-backed facts.
NSE_CIRCULAR_PUBLISHED_AT = datetime(2025, 12, 12, 0, 0, tzinfo=timezone.utc)

NSE_PDF_SHA = "1466db29f0b18d8b66524c6e47a8798f6dc8cdef4cf641e01b607e5925579274"
MCX_SPEC_PDF_SHA = "347d6512f5c296b7eef128fd8b65dcf91e1fda54a64e6f832b0209315ecaa7cb"
NSE_API_SHA = "5d228002284d150478553dffd34fdd0d3a0a10196f42aabd49846f57952e84fb"
MCX_TXT_SHA = "fde9f8f4707b5e23732bb0a4e680c82a06a43a51de8e84f8a47c223c286d64da"


def file_sha(name: str) -> str:
    return hashlib.sha256((OFFICIAL_DIR / name).read_bytes()).hexdigest()


def official_receipts() -> dict[str, C.SourceReceiptV1]:
    api_bytes = (OFFICIAL_DIR / "nse_holiday_master_api_2026.json").read_bytes()
    page_bytes = (OFFICIAL_DIR / "mcx_observed_2026.txt").read_bytes()
    nse_pdf = (OFFICIAL_DIR / "nse_cmtr71775_2026_holidays.pdf").read_bytes()
    mcx_pdf = (OFFICIAL_DIR / "mcx_crude_oil_jan2026_spec.pdf").read_bytes()
    assert hashlib.sha256(nse_pdf).hexdigest() == NSE_PDF_SHA
    assert hashlib.sha256(mcx_pdf).hexdigest() == MCX_SPEC_PDF_SHA
    assert hashlib.sha256(api_bytes).hexdigest() == NSE_API_SHA
    assert hashlib.sha256(page_bytes).hexdigest() == MCX_TXT_SHA
    legacy_bytes = LEGACY_INSTRUMENTS_FIXTURE.read_bytes()
    return {
        "OF-NSE-API": receipt_for_bytes(
            source_id="OF-NSE-API",
            source_type="EXCHANGE_HOLIDAY_MASTER_API",
            provider="NSE",
            document_id="holiday-master?type=trading",
            artifact_identity="official/nse_holiday_master_api_2026.json",
            content=api_bytes,
            parser_version="official-extract.v1",
            # The API artifact itself states no publication timestamp:
            # unknown stays unknown (never inherit the circular date).
            published_at=None,
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
            published_at=NSE_CIRCULAR_PUBLISHED_AT,
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
        "LEGACY-MARKET-IDENTITY-INSTRUMENT-FIXTURE": receipt_for_bytes(
            source_id="LEGACY-MARKET-IDENTITY-INSTRUMENT-FIXTURE",
            source_type="LEGACY_TEST_FIXTURE",
            provider="TRADE_VISION_REPOSITORY",
            document_id="repository-legacy-instrument-spellings",
            artifact_identity="tests/fixtures/market_identity/instruments.json",
            content=legacy_bytes,
            parser_version="official-extract.v1",
            published_at=None,
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
                # No effective start observed: explicit missingness.
                effective_from=None,
                # API/page artifacts state no publication time.
                published_at=None,
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
            effective_from=None,
            published_at=None,
            available_at=RETRIEVED_AT,
        )
    )
    # Placeholder MCX day profile: the pinned MCX text observes morning
    # 09:00-17:00 but leaves the evening close ambiguous (dual close with
    # no product/date selection rule), so the official set asserts NO exact
    # evening boundary. This midnight-minute placeholder never matches real
    # trading times; PARTIAL rows carry the OPEN facts as contract_events and
    # resolve exact membership fail-closed. Close/settlement semantics stay
    # UNSPECIFIED (settlement references were NOT observed).
    registry.add_session_profile(
        C.session_record(
            profile_id="OF-MCX-DAY-V1",
            venue_id="MCX",
            segment_scope="COMMODITY",
            timezone_name="Asia/Kolkata",
            trading_date_convention="PLACEHOLDER_NO_EXACT_CLOSE_AMBIGUOUS_2330_2355_NEVER_CONSULTED",
            session_type=C.SessionType.REGULAR,
            opening_anchor_local="00:00",
            tradable_intervals=[
                C.TradingIntervalV1(start_local="00:00", end_local="00:01"),
            ],
            source_receipt_ids=["OF-MCX-PAGE"],
            effective_from=None,
            published_at=None,
            available_at=RETRIEVED_AT,
        )
    )
    # Symbol spellings from the repository legacy fixture receipt above —
    # never the exchange holiday API.
    registry.add_instrument(
        C.instrument_record(
            instrument_key="OF-NSE-CASH:RELIANCE",
            instrument_type=InstrumentType.NSE_EQUITY,
            venue_id="NSE",
            segment_id="CASH",
            canonical_symbol="RELIANCE",
            calendar_profile_id="OF-NSE-DAY-V1",
            source_receipt_ids=["LEGACY-MARKET-IDENTITY-INSTRUMENT-FIXTURE"],
            effective_from=None,
            published_at=None,
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
            source_receipt_ids=["LEGACY-MARKET-IDENTITY-INSTRUMENT-FIXTURE"],
            effective_from=None,
            published_at=None,
            available_at=RETRIEVED_AT,
        )
    )
    # Product-level crude facts that really are observed: the MCX crude-oil
    # product exists and its underlying is the CME/NYMEX benchmark WTI (per
    # the pinned product page). No exact futures contract is built here: the
    # January-2026 series row proves series existence only (not
    # contract_month/expiry/listing), and the barrel-quantity text was
    # observed on options titles, never as a futures trading_unit.
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
            effective_from=None,
            published_at=None,
            available_at=RETRIEVED_AT,
        )
    )
    payload = json.loads((OFFICIAL_DIR / "official_calendars.json").read_text(encoding="utf-8"))
    assert payload["parser_version"] == "official-extract.v1"
    for row in payload["calendars"]:
        # Every official calendar fact is hash-bound to its exact raw source
        # receipt — never inferred from the venue, never borrowed across
        # sources, never hashed from this mapping file.
        receipt = receipts[row["source_receipt_id"]]
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
                source_hash=receipt.content_hash,
                published_at=receipt.published_at,
                available_at=receipt.available_at,
                supersedes_record_id=row.get("supersedes_record_id"),
                lifecycle=C.RegistryLifecycle(row.get("lifecycle", "DRAFT")),
            )
        )
    return registry
