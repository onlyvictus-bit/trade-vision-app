"""ORB BUILD-2 official-source provenance gate.

Proves the ingestion machinery on real pinned artifacts: hash-bound source
receipts, verbatim NSE holiday-master rows, MCX per-session holiday splits,
Muhurat annotation without invented timings, and explicit missingness for
every unobserved fact (tick, expiry, settlement, NSE regular hours). The
synthetic adversarial set stays separate; this file asserts the official
examples only, and asserts the coverage boundary (listed dates only).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.orb.market_identity import contracts as C
from app.orb.market_identity.resolver import resolve_market_identity
from app.orb.market_identity.source_receipts import receipt_for_bytes, verify_content
from official_support import (
    MCX_SPEC_PDF_SHA,
    NSE_PDF_SHA,
    OFFICIAL_DIR,
    RETRIEVED_AT,
    build_official_registry,
    file_sha,
    official_receipts,
)

K = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)


def test_official_byte_artifacts_are_pinned() -> None:
    assert file_sha("nse_cmtr71775_2026_holidays.pdf") == NSE_PDF_SHA
    assert file_sha("mcx_crude_oil_jan2026_spec.pdf") == MCX_SPEC_PDF_SHA
    assert (OFFICIAL_DIR / "SOURCES.md").read_text(encoding="utf-8").count(NSE_PDF_SHA) >= 1
    assert (OFFICIAL_DIR / "SOURCES.md").read_text(encoding="utf-8").count(MCX_SPEC_PDF_SHA) >= 1


def test_receipt_binding_and_tamper_detection() -> None:
    receipts = official_receipts()
    assert set(receipts) == {"OF-NSE-API", "OF-NSE-CIRCULAR", "OF-MCX-PAGE", "OF-MCX-SPEC"}
    pdf_bytes = (OFFICIAL_DIR / "nse_cmtr71775_2026_holidays.pdf").read_bytes()
    assert verify_content(receipts["OF-NSE-CIRCULAR"], pdf_bytes) is True
    assert verify_content(receipts["OF-NSE-CIRCULAR"], pdf_bytes + b"tampered") is False
    api_bytes = (OFFICIAL_DIR / "nse_holiday_master_api_2026.json").read_bytes()
    assert verify_content(receipts["OF-NSE-API"], api_bytes) is True
    # Every receipt is knowledge-gated at retrieval: nothing was knowable before.
    for receipt in receipts.values():
        assert receipt.available_at == RETRIEVED_AT


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


def test_official_mcx_partial_session_splits_the_day() -> None:
    registry = build_official_registry()
    morning = resolve_market_identity(
        registry, instrument_key="OF-MCX-COMM:CRUDEOIL",
        contract_key="OF-MCX-COMM:CRUDEOIL-2026-01",
        as_of=datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert morning.state is C.ResolutionState.UNAVAILABLE
    assert "SESSION_NOT_RESOLVED" in morning.reason_codes
    evening = resolve_market_identity(
        registry, instrument_key="OF-MCX-COMM:CRUDEOIL",
        contract_key="OF-MCX-COMM:CRUDEOIL-2026-01",
        as_of=datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert evening.state is C.ResolutionState.RESOLVED
    assert evening.identity is not None
    assert evening.identity.calendar_record_id == "OF-MCX-2026-09-14"


def test_muhurat_annotated_but_timings_unknown() -> None:
    registry = build_official_registry()
    records = registry.calendar_records("NSE", "CASH", date(2026, 11, 8), K)
    assert len(records) == 1
    assert "MUHURAT_TRADING_ANNOUNCED_TIMINGS_PENDING_CIRCULAR" in records[0].contract_events
    assert records[0].tradable_intervals_override is None
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE


def test_official_crude_missingness_is_explicit() -> None:
    registry = build_official_registry()
    contract = registry.contract("OF-MCX-COMM:CRUDEOIL-2026-01")
    assert contract.contract_month == "2026-01"
    assert contract.trading_unit == "100 Barrels"
    assert contract.expiry_at is None
    assert contract.last_trade_at is None
    assert contract.tick_rule_id is None
    resolution = resolve_market_identity(
        registry, instrument_key="OF-MCX-COMM:CRUDEOIL",
        contract_key="OF-MCX-COMM:CRUDEOIL-2026-01",
        as_of=datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.RESOLVED
    assert "PRICE_RULE_UNAVAILABLE" in resolution.reason_codes
    assert "LOT_RULE_UNAVAILABLE" in resolution.reason_codes
    assert "SETTLEMENT_SEMANTICS_UNAVAILABLE" in resolution.reason_codes
    assert resolution.identity is not None
    assert resolution.identity.price_rule_id is None
    assert resolution.identity.contract_key == "OF-MCX-COMM:CRUDEOIL-2026-01"


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


def test_placeholder_profile_never_drives_membership() -> None:
    registry = build_official_registry()
    profile = registry.session_profile("OF-NSE-DAY-V1")
    assert profile.trading_date_convention.startswith("PLACEHOLDER")
    # Even with a full-day placeholder profile, the holiday record contributes
    # no intervals, so membership stays closed.
    resolution = resolve_market_identity(
        registry, instrument_key="OF-NSE-CASH:RELIANCE",
        as_of=datetime(2026, 12, 25, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE


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
