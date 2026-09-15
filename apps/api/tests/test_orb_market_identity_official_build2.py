"""ORB BUILD-2 official-source provenance gate.

Proves the ingestion machinery on real pinned artifacts: hash-bound source
receipts, verbatim NSE holiday-master rows, MCX per-session holiday splits,
Muhurat annotation without invented timings, and explicit missingness for
every unobserved fact (tick, expiry, settlement, NSE regular hours). The
synthetic adversarial set stays separate; this file asserts the official
examples only, and asserts the coverage boundary (listed dates only).

Source-truth posture (BUILD-2 review-hold remediation, blockers 1-8):
OBSERVED means observed; UNKNOWN stays unknown; no source inherits facts
from another source silently; no fixture masquerades as exchange fact; no
partial observation becomes a complete market rule.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path

from app.orb.market_identity import contracts as C
from app.orb.market_identity import session as session_math
from app.orb.market_identity.registry import RegistryError
from app.orb.market_identity.resolver import resolve_market_identity
from app.orb.market_identity.source_receipts import receipt_for_bytes, verify_content
from official_support import (
    LEGACY_INSTRUMENTS_FIXTURE,
    MCX_SPEC_PDF_SHA,
    MCX_TXT_SHA,
    NSE_API_SHA,
    NSE_CIRCULAR_PUBLISHED_AT,
    NSE_PDF_SHA,
    OFFICIAL_DIR,
    RETRIEVED_AT,
    build_official_registry,
    file_sha,
    official_receipts,
)

K = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)
CIRCULAR_DATE = datetime(2025, 12, 12, 0, 0, tzinfo=timezone.utc)
LEGACY_RECEIPT_ID = "LEGACY-MARKET-IDENTITY-INSTRUMENT-FIXTURE"
GUESSED_CRUDE_CONTRACT = "OF-MCX-COMM:CRUDEOIL-2026-01"


def test_official_byte_artifacts_are_pinned() -> None:
    assert file_sha("nse_cmtr71775_2026_holidays.pdf") == NSE_PDF_SHA
    assert file_sha("mcx_crude_oil_jan2026_spec.pdf") == MCX_SPEC_PDF_SHA
    assert file_sha("nse_holiday_master_api_2026.json") == NSE_API_SHA
    assert file_sha("mcx_observed_2026.txt") == MCX_TXT_SHA
    sources = (OFFICIAL_DIR / "SOURCES.md").read_text(encoding="utf-8")
    assert sources.count(NSE_PDF_SHA) >= 1
    assert sources.count(MCX_SPEC_PDF_SHA) >= 1
    assert sources.count(NSE_API_SHA) >= 1
    assert sources.count(MCX_TXT_SHA) >= 1


def test_receipt_binding_and_tamper_detection() -> None:
    receipts = official_receipts()
    assert set(receipts) == {
        "OF-NSE-API",
        "OF-NSE-CIRCULAR",
        "OF-MCX-PAGE",
        "OF-MCX-SPEC",
        LEGACY_RECEIPT_ID,
    }
    pdf_bytes = (OFFICIAL_DIR / "nse_cmtr71775_2026_holidays.pdf").read_bytes()
    assert verify_content(receipts["OF-NSE-CIRCULAR"], pdf_bytes) is True
    assert verify_content(receipts["OF-NSE-CIRCULAR"], pdf_bytes + b"tampered") is False
    api_bytes = (OFFICIAL_DIR / "nse_holiday_master_api_2026.json").read_bytes()
    assert verify_content(receipts["OF-NSE-API"], api_bytes) is True
    assert verify_content(receipts["OF-NSE-API"], api_bytes + b"tampered") is False
    page_bytes = (OFFICIAL_DIR / "mcx_observed_2026.txt").read_bytes()
    assert verify_content(receipts["OF-MCX-PAGE"], page_bytes) is True
    assert verify_content(receipts["OF-MCX-PAGE"], page_bytes + b"tampered") is False
    legacy_bytes = LEGACY_INSTRUMENTS_FIXTURE.read_bytes()
    assert verify_content(receipts[LEGACY_RECEIPT_ID], legacy_bytes) is True
    # Every receipt is knowledge-gated at retrieval: nothing was knowable before.
    for receipt in receipts.values():
        assert receipt.available_at == RETRIEVED_AT


def test_api_vs_circular_published_at_separation() -> None:
    """Blocker 1: the circular date never leaks onto API-backed facts."""
    receipts = official_receipts()
    assert receipts["OF-NSE-API"].published_at is None
    assert receipts["OF-NSE-CIRCULAR"].published_at == CIRCULAR_DATE
    assert receipts["OF-NSE-CIRCULAR"].published_at == NSE_CIRCULAR_PUBLISHED_AT
    assert receipts["OF-MCX-PAGE"].published_at is None
    assert receipts["OF-MCX-SPEC"].published_at is None
    assert receipts[LEGACY_RECEIPT_ID].published_at is None
    registry = build_official_registry()
    for venue in registry._venues.values():
        assert venue.published_at is None, venue.venue_id
        assert venue.available_at == RETRIEVED_AT
    for profile in registry._sessions.values():
        assert profile.published_at is None, profile.profile_id
    for instrument in registry._instruments.values():
        assert instrument.published_at is None, instrument.instrument_key
    for (_venue, _seg, _day), bucket in registry._calendars.items():
        for record in bucket:
            assert record.published_at is None, record.record_id
            assert record.available_at == RETRIEVED_AT
    # Retrieval-time availability remains causal: nothing knowable before.
    early = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    for receipt in receipts.values():
        assert receipt.available_at is not None and receipt.available_at > early


def test_no_fabricated_official_effective_from() -> None:
    """Blocker 2: no invented effective start in the official registry."""
    registry = build_official_registry()
    for venue in registry._venues.values():
        assert venue.effective_from is None, venue.venue_id
    for profile in registry._sessions.values():
        assert profile.effective_from is None, profile.profile_id
    for instrument in registry._instruments.values():
        assert instrument.effective_from is None, instrument.instrument_key
    for contract in registry._contracts.values():
        assert contract.effective_from is None, contract.contract_key
    # Anti-regression: the loader source must not reintroduce a magic date.
    loader_text = (Path(__file__).resolve().parent / "official_support.py").read_text(encoding="utf-8")
    assert "2020-01-01" not in loader_text
    assert "2020, 1, 1" not in loader_text


def test_official_nse_holiday_blocks_cash_session() -> None:
    registry = build_official_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "SESSION_NOT_RESOLVED" in resolution.reason_codes


def test_official_nse_fo_mirrors_cash_holiday() -> None:
    registry = build_official_registry()
    # FO lists the same Ganesh holiday (segment mirror at the source level).
    fo_rows = registry.calendar_records("NSE", "DERIVATIVES", date(2026, 9, 14), K)
    assert [row.record_id for row in fo_rows] == ["OF-NSE-DERIV-2026-09-14"]
    assert fo_rows[0].session_type is C.SessionType.CLOSED_HOLIDAY
    # No official NIFTY contract exists, so derivative resolution stops at
    # the contract gate before session logic — also fail-closed.
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-DERIV:NIFTY",
        as_of=datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "CONTRACT_NOT_FOUND" in resolution.reason_codes


def test_official_mcx_ambiguous_close_fails_closed() -> None:
    """Blocker 3: the unresolved 23:30/23:55 close never becomes exact."""
    registry = build_official_registry()
    profile = registry.session_profile("OF-MCX-DAY-V1")
    assert profile.trading_date_convention.startswith("PLACEHOLDER")
    assert "AMBIGUOUS" in profile.trading_date_convention
    # No exact evening boundary anywhere in the constructed official facts.
    for interval in profile.tradable_intervals:
        assert (interval.start_local, interval.end_local) != ("17:00", "23:55")
        assert (interval.start_local, interval.end_local) != ("17:00", "23:30")
    for target_day in (date(2026, 9, 14), date(2026, 10, 20)):
        rows = registry.calendar_records("MCX", "COMMODITY", target_day, K)
        assert len(rows) == 1
        row = rows[0]
        assert row.session_type is C.SessionType.PARTIAL
        # Ganesh/Dassera rows preserve MORNING_CLOSED / EVENING_OPEN as
        # source evidence plus the raw close-ambiguity marker — never as
        # exact session intervals.
        assert any("MORNING-CLOSED-EVENING-OPEN" in event for event in row.contract_events)
        assert "MCX_EVENING_CLOSE_AMBIGUOUS_2330_2355_RULE_UNRESOLVED" in row.contract_events
        assert row.tradable_intervals_override is None
    # Session math proves fail-closed directly: neither the closed morning
    # nor the open-but-unbounded evening resolves to in-session membership.
    ganesh = registry.calendar_records("MCX", "COMMODITY", date(2026, 9, 14), K)[0]
    morning = session_math.locate_timestamp(
        profile, datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc), ganesh
    )
    evening = session_math.locate_timestamp(
        profile, datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc), ganesh
    )
    assert morning["in_session"] is False
    assert evening["in_session"] is False
    # End to end: no MCX resolution reports OPEN/CLOSED from a guessed clock.
    for as_of in (
        datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc),
    ):
        resolution = resolve_market_identity(
            registry, instrument_key="OF-MCX-COMM:CRUDEOIL",
            contract_key=GUESSED_CRUDE_CONTRACT,
            as_of=as_of, knowledge_cutoff=K,
            data_basis=C.DataBasis.RAW_CONTRACT,
        )
        assert resolution.state is C.ResolutionState.UNAVAILABLE
        assert resolution.identity is None


def test_mcx_close_and_settlement_semantics_unspecified() -> None:
    """Blocker 4: unobserved settlement/close semantics stay UNSPECIFIED."""
    registry = build_official_registry()
    profile = registry.session_profile("OF-MCX-DAY-V1")
    assert profile.close_semantics == "UNSPECIFIED"
    assert profile.settlement_semantics == "UNSPECIFIED"
    for session_profile in registry._sessions.values():
        assert session_profile.close_semantics == "UNSPECIFIED", session_profile.profile_id
        assert session_profile.settlement_semantics == "UNSPECIFIED", session_profile.profile_id
    # Settlement-sensitive resolution stays explicitly unavailable.
    resolution = resolve_market_identity(
        registry, instrument_key="OF-MCX-COMM:CRUDEOIL",
        contract_key=GUESSED_CRUDE_CONTRACT,
        as_of=datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    loader_text = (Path(__file__).resolve().parent / "official_support.py").read_text(encoding="utf-8")
    assert "LAST_TRADED_PRICE_AT_SESSION_END" not in loader_text
    assert "CASH_SETTLED_AGAINST_DAILY_SETTLEMENT_REFERENCE" not in loader_text


def test_official_crude_series_does_not_become_exact_contract() -> None:
    """Blocker 5: series-existence text never becomes exact contract identity."""
    registry = build_official_registry()
    # The guessed exact contract does not exist in the official set.
    assert GUESSED_CRUDE_CONTRACT not in registry._contracts
    assert registry._contracts == {}
    for contract in registry._contracts.values():
        assert contract.contract_month != "2026-01"
        assert contract.trading_unit != "100 Barrels"
    # Asking for the guessed contract fails closed at the contract gate.
    resolution = resolve_market_identity(
        registry, instrument_key="OF-MCX-COMM:CRUDEOIL",
        contract_key=GUESSED_CRUDE_CONTRACT,
        as_of=datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "CONTRACT_NOT_FOUND" in resolution.reason_codes
    # Product/underlying identity that IS observed remains available.
    product = registry.instrument("OF-MCX-COMM:CRUDEOIL")
    assert product.underlying_instrument_key == "CME-NYMEX:WTI"
    assert product.tick_rule_id is None
    assert product.lot_rule_id is None
    assert product.price_precision is None
    # The raw series evidence is preserved as source text, not as identity.
    raw = (OFFICIAL_DIR / "mcx_observed_2026.txt").read_text(encoding="utf-8")
    assert "January 2026 Contract Onwards" in raw
    assert "100 Barrels" in raw  # options-title context only
    try:
        registry.contract(GUESSED_CRUDE_CONTRACT)
    except RegistryError as exc:
        assert "contract not found" in str(exc)
    else:  # pragma: no cover - must fail closed
        raise AssertionError("guessed crude contract must not resolve")


def test_muhurat_annotated_but_timings_unknown() -> None:
    """Blocker 6 (NSE): regular-closed and special-unknown stay distinct."""
    registry = build_official_registry()
    records = registry.calendar_records("NSE", "CASH", date(2026, 11, 8), K)
    assert len(records) == 1
    assert "MUHURAT_TRADING_ANNOUNCED_TIMINGS_PENDING_CIRCULAR" in records[0].contract_events
    assert any("DIWALI" in event for event in records[0].contract_events)
    assert records[0].tradable_intervals_override is None
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE


def test_muhurat_unknown_timing_never_becomes_closed_mcx() -> None:
    """Blocker 6 (MCX): unknown special-session timing is not CLOSED."""
    registry = build_official_registry()
    # No ACTIVE record converts the unknown timing into CLOSED_HOLIDAY truth.
    live = registry.calendar_records("MCX", "COMMODITY", date(2026, 11, 8), K)
    assert live == []
    evidence = registry.calendar_records(
        "MCX", "COMMODITY", date(2026, 11, 8), K, live_only=False
    )
    assert len(evidence) == 1
    row = evidence[0]
    assert row.lifecycle is C.RegistryLifecycle.DRAFT
    assert row.session_type is not C.SessionType.CLOSED_HOLIDAY
    assert "MUHURAT_TRADING_ANNOUNCED_TIMINGS_PENDING_CIRCULAR" in row.contract_events
    assert "MCX-2026-NO-TABLE-ROW-FOR-DATE" in row.contract_events
    assert "CLOSED_PENDING_PUBLISHED_TIMINGS" not in row.contract_events
    # Exact membership stays unavailable — never whole-day CLOSED.
    resolution = resolve_market_identity(
        registry, instrument_key="OF-MCX-COMM:CRUDEOIL",
        contract_key=GUESSED_CRUDE_CONTRACT,
        as_of=datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert resolution.identity is None


def test_calendar_rows_hash_bound_to_raw_source() -> None:
    """Blocker 7: every active calendar fact carries its raw-source hash."""
    receipts = official_receipts()
    raw_by_receipt = {
        "OF-NSE-API": (OFFICIAL_DIR / "nse_holiday_master_api_2026.json").read_bytes(),
        "OF-MCX-PAGE": (OFFICIAL_DIR / "mcx_observed_2026.txt").read_bytes(),
    }
    payload = __import__("json").loads(
        (OFFICIAL_DIR / "official_calendars.json").read_text(encoding="utf-8")
    )
    row_receipt = {row["record_id"]: row["source_receipt_id"] for row in payload["calendars"]}
    assert set(row_receipt.values()) <= set(receipts)
    registry = build_official_registry()
    seen = 0
    for (_venue, _seg, _day), bucket in registry._calendars.items():
        for record in bucket:
            if record.lifecycle not in (C.RegistryLifecycle.VERIFIED, C.RegistryLifecycle.ACTIVE):
                continue
            receipt = receipts[row_receipt[record.record_id]]
            raw = raw_by_receipt[row_receipt[record.record_id]]
            assert receipt.content_hash == hashlib.sha256(raw).hexdigest()
            assert record.source_hash == receipt.content_hash, record.record_id
            assert record.available_at == receipt.available_at
            assert record.published_at == receipt.published_at
            seen += 1
    assert seen >= 14  # all ACTIVE rows bound; DRAFT Muhurat evidence excluded


def test_tampered_source_hash_fails_closed() -> None:
    """Blocker 7: a mismatched derived hash is detectable and unusable."""
    receipts = official_receipts()
    registry = build_official_registry()
    record = registry.calendar_records("NSE", "CASH", date(2026, 9, 14), K)[0]
    receipt = receipts["OF-NSE-API"]
    raw = (OFFICIAL_DIR / "nse_holiday_master_api_2026.json").read_bytes()
    assert record.source_hash == receipt.content_hash == hashlib.sha256(raw).hexdigest()
    assert verify_content(receipt, raw + b"tampered") is False
    tampered_hash = hashlib.sha256(raw + b"tampered").hexdigest()
    assert tampered_hash != record.source_hash
    # A derived fact carrying the tampered hash no longer matches its receipt.
    from dataclasses import replace

    forged = replace(record, record_hash=record.record_hash, source_hash=tampered_hash)
    assert forged.source_hash != receipt.content_hash
    # And a receipt built from tampered bytes binds a different hash.
    forged_receipt = receipt_for_bytes(
        source_id="OF-NSE-API",
        source_type="EXCHANGE_HOLIDAY_MASTER_API",
        provider="NSE",
        document_id="holiday-master?type=trading",
        artifact_identity="official/nse_holiday_master_api_2026.json",
        content=raw + b"tampered",
        parser_version="official-extract.v1",
        available_at=RETRIEVED_AT,
    )
    assert forged_receipt.content_hash != record.source_hash


def test_legacy_instrument_provenance_is_explicit() -> None:
    """Blocker 8: repository fixture symbols never claim exchange provenance."""
    receipts = official_receipts()
    legacy = receipts[LEGACY_RECEIPT_ID]
    assert legacy.source_type == "LEGACY_TEST_FIXTURE"
    assert legacy.provider == "TRADE_VISION_REPOSITORY"
    assert legacy.artifact_identity == "tests/fixtures/market_identity/instruments.json"
    assert legacy.content_hash == hashlib.sha256(LEGACY_INSTRUMENTS_FIXTURE.read_bytes()).hexdigest()
    assert legacy.published_at is None
    registry = build_official_registry()
    reliance = registry.instrument("OF-NSE-CASH:RELIANCE")
    nifty = registry.instrument("OF-NSE-DERIV:NIFTY")
    assert tuple(reliance.source_receipt_ids) == (LEGACY_RECEIPT_ID,)
    assert tuple(nifty.source_receipt_ids) == (LEGACY_RECEIPT_ID,)
    for instrument in registry._instruments.values():
        if instrument.instrument_key in ("OF-NSE-CASH:RELIANCE", "OF-NSE-DERIV:NIFTY"):
            assert "OF-NSE-API" not in instrument.source_receipt_ids
    crude = registry.instrument("OF-MCX-COMM:CRUDEOIL")
    assert "OF-NSE-API" not in crude.source_receipt_ids


def test_pre_retrieval_cutoff_sees_no_official_facts() -> None:
    registry = build_official_registry()
    early = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=early,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    # Knowledge gating applies end to end: the instrument itself (and hence
    # everything downstream) is invisible before retrieval.
    assert set(resolution.reason_codes) <= {"IDENTITY_NOT_FOUND", "CALENDAR_UNAVAILABLE"}


def test_no_regular_day_assumption_in_official_set() -> None:
    registry = build_official_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "CALENDAR_UNAVAILABLE" in resolution.reason_codes


def test_placeholder_profiles_never_drive_membership() -> None:
    registry = build_official_registry()
    nse = registry.session_profile("OF-NSE-DAY-V1")
    assert nse.trading_date_convention.startswith("PLACEHOLDER")
    # Even with a full-day placeholder profile, the holiday record contributes
    # no intervals, so membership stays closed.
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 12, 25, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    mcx = registry.session_profile("OF-MCX-DAY-V1")
    assert mcx.trading_date_convention.startswith("PLACEHOLDER")
    assert mcx.close_semantics == "UNSPECIFIED"
    assert mcx.settlement_semantics == "UNSPECIFIED"


def test_official_set_covers_only_listed_dates() -> None:
    registry = build_official_registry()
    cash = [key for key in registry._calendars if key[0] == "NSE" and key[1] == "CASH"]
    deriv = [key for key in registry._calendars if key[0] == "NSE" and key[1] == "DERIVATIVES"]
    comm = [key for key in registry._calendars if key[0] == "MCX"]
    assert len(cash) == 6 and len(deriv) == 4 and len(comm) == 5
    for (_venue, _seg, _day), bucket in registry._calendars.items():
        for record in bucket:
            assert record.record_id.startswith("OF-")
            assert record.available_at == RETRIEVED_AT


def test_receipt_ids_referenced_by_official_records_exist() -> None:
    receipts = official_receipts()
    registry = build_official_registry()
    for instrument in registry._instruments.values():
        for receipt_id in instrument.source_receipt_ids:
            assert receipt_id in receipts, receipt_id
    for (_venue, _seg, _day), bucket in registry._calendars.items():
        for record in bucket:
            assert record.source_document_id in {
                "OF-NSE-API-CM", "OF-NSE-API-FO", "OF-MCX-HOLIDAYS-PAGE",
            }
            assert record.source_hash in {receipt.content_hash for receipt in receipts.values()}


def test_source_readiness_remains_unchanged() -> None:
    from app.behavior.orb_build0_manifest import build_manifest

    readiness = {
        row["capability_id"]: row["state"] for row in build_manifest()["source_readiness"]
    }
    assert readiness["EXCHANGE_CALENDAR_HISTORY"] == "NEEDS_VERSIONED_FILE"
    assert readiness["COMMODITY_INSTRUMENT_MASTER"] == "UNAVAILABLE"
    assert readiness["SETTLEMENT_CONTEXT"] == "NEEDS_EXTERNAL_FEED"


def test_zero_authority_invariants_hold() -> None:
    from app.behavior.decision_spine.authority_registry import (
        FINAL_BAND_AUTHORITY,
        all_engine_authorities,
        validate_authority_registry,
    )

    assert validate_authority_registry() == ()
    assert [e.engine_id for e in all_engine_authorities() if e.may_set_final_band] == [
        FINAL_BAND_AUTHORITY
    ]
    assert all(not e.may_execute for e in all_engine_authorities())
    registry = build_official_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.research_only is True
    assert resolution.trade_allowed is False
    assert resolution.may_execute is False
    assert resolution.may_set_final_band is False


def test_deterministic_replay_hash_stable() -> None:
    first = build_official_registry()
    second = build_official_registry()
    assert first.registry_version_hash() == second.registry_version_hash()
    assert (
        first.session_profile("OF-MCX-DAY-V1").record_hash
        == second.session_profile("OF-MCX-DAY-V1").record_hash
    )
    kwargs = dict(
        instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc),
        knowledge_cutoff=K,
    )
    one = resolve_market_identity(first, **kwargs)
    two = resolve_market_identity(second, **kwargs)
    assert one.input_hash == two.input_hash
    assert one.output_hash == two.output_hash
    assert one.reason_codes == two.reason_codes
