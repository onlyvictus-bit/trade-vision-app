"""ORB BUILD-2 market identity: resolution, session, contract, economics.

Research-only. Proves canonical identity machinery on versioned fixtures:
NSE clean-session parity with the legacy engine, generic cross-midnight and
break math, contract/expiry/settlement semantics, Decimal tick/lot rules,
data-basis guards, and fail-closed ambiguity. Legacy ORB behavior is
unchanged by these tests.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.orb.candidate_intake import InstrumentType
from app.orb.market_identity import compatibility as compat
from app.orb.market_identity import price_rules as pr
from app.orb.market_identity import session as sm
from app.orb.market_identity import contracts as C
from app.orb.market_identity.resolver import availability_summary, resolve_market_identity
from market_identity_support import build_fixture_registry

K = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)
NSE_MORNING = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)  # 11:30 IST
MCX_EVENING = datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc)  # 22:30 IST


def _ns(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp() * 1_000_000_000)


# identity ---------------------------------------------------------------
def test_nse_equity_resolves_with_full_provenance() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert resolution.state is C.ResolutionState.RESOLVED
    identity = resolution.identity
    assert identity is not None
    assert identity.venue_id == "NSE"
    assert identity.instrument_key == "NSE-CASH:RELIANCE"
    assert identity.contract_key is None
    assert identity.session_profile_id == "NSE-CASH-REGULAR-V1"
    assert identity.calendar_record_id == "NSE-2026-09-14-R1"
    assert identity.price_rule_id == "NSE-CASH-TICK"
    assert identity.data_basis is C.DataBasis.RAW_CASH
    assert identity.market_identity_hash
    assert resolution.reason_codes == ()


def test_symbol_normalization_and_alias_hit() -> None:
    registry = build_fixture_registry()
    first = resolve_market_identity(
        registry, provider_alias=" reliance ", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    second = resolve_market_identity(
        registry, provider_alias="RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert first.state is C.ResolutionState.RESOLVED
    assert first.identity is not None and second.identity is not None
    assert first.identity.market_identity_hash == second.identity.market_identity_hash


def test_unknown_and_empty_identity_fail_closed() -> None:
    registry = build_fixture_registry()
    for kwargs in ({"instrument_key": "NOPE:NOTHING"}, {"provider_alias": "NOPE"}, {"provider_alias": "  "}):
        resolution = resolve_market_identity(registry, as_of=NSE_MORNING, knowledge_cutoff=K, **kwargs)
        assert resolution.state is C.ResolutionState.UNAVAILABLE
        assert "IDENTITY_NOT_FOUND" in resolution.reason_codes
        assert resolution.identity is None


def test_same_ticker_two_venues_is_ambiguous_until_hinted() -> None:
    registry = build_fixture_registry()
    registry.add_instrument(
        C.instrument_record(
            instrument_key="MCX-COMM:RELIANCE",
            instrument_type=InstrumentType.REGISTERED_OTHER,
            venue_id="MCX",
            segment_id="COMMODITY",
            canonical_symbol="RELIANCE",
            calendar_profile_id="MCX-COMM-LONG-V1",
            tick_rule_id="MCX-AGRI-TICK",
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            available_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    ambiguous = resolve_market_identity(registry, provider_alias="RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K)
    assert ambiguous.state is C.ResolutionState.AMBIGUOUS
    assert "IDENTITY_AMBIGUOUS" in ambiguous.reason_codes
    assert len(ambiguous.candidate_identity_ids) == 2
    hinted = resolve_market_identity(
        registry, provider_alias="RELIANCE", venue_id="NSE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert hinted.state is C.ResolutionState.RESOLVED
    assert hinted.identity is not None and hinted.identity.instrument_key == "NSE-CASH:RELIANCE"


def test_expired_instrument_identity_is_unavailable() -> None:
    registry = build_fixture_registry()
    registry.add_instrument(
        C.instrument_record(
            instrument_key="NSE-CASH:DELISTED",
            instrument_type=InstrumentType.NSE_EQUITY,
            venue_id="NSE",
            segment_id="CASH",
            canonical_symbol="DELISTED",
            calendar_profile_id="NSE-CASH-REGULAR-V1",
            tick_rule_id="NSE-CASH-TICK",
            effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            effective_to=datetime(2026, 1, 1, tzinfo=timezone.utc),
            published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            available_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:DELISTED", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE


# session ------------------------------------------------------------------
def test_nse_clean_session_parity_with_legacy() -> None:
    registry = build_fixture_registry()
    profile = registry.session_profile("NSE-CASH-REGULAR-V1")
    stamps = [_ns(2026, 9, 14, h, m) for h in range(3, 11) for m in (0, 15, 30, 45)]
    receipt = compat.shadow_compare_nse(stamps, profile)
    assert receipt["parity"] is True
    assert receipt["divergences"] == []
    assert receipt["compared"] == len(stamps)


def test_session_boundaries_are_half_open() -> None:
    profile = compat.nse_canonical_profile()
    at_open = sm.locate_timestamp(profile, datetime(2026, 9, 14, 3, 45, tzinfo=timezone.utc))
    at_close = sm.locate_timestamp(profile, datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc))
    before_open = sm.locate_timestamp(profile, datetime(2026, 9, 14, 3, 44, tzinfo=timezone.utc))
    assert at_open["in_session"] is True and at_open["session_label"] == "2026-09-14"
    assert at_close["in_session"] is False
    assert before_open["in_session"] is False


def test_holiday_divergence_is_recorded_not_substituted() -> None:
    registry = build_fixture_registry()
    profile = registry.session_profile("NSE-CASH-REGULAR-V1")
    holiday = next(
        item
        for item in registry.calendar_records("NSE", "CASH", date(2026, 9, 16), K)
        if item.record_id == "NSE-2026-09-16-HOLIDAY"
    )
    stamps = [_ns(2026, 9, 16, 6, 0)]
    receipt = compat.shadow_compare_nse(stamps, profile, holiday)
    assert receipt["parity"] is False
    assert receipt["divergences"][0]["kind"] == "LEGACY_ONLY"
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 16, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "SESSION_NOT_RESOLVED" in resolution.reason_codes


def test_special_session_uses_override_and_is_flagged() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 17, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.RESOLVED
    assert "SPECIAL_SESSION" in resolution.reason_codes
    assert resolution.identity is not None
    assert resolution.identity.calendar_record_id == "NSE-2026-09-17-SPECIAL"


def test_mock_session_resolves_but_is_flagged() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 19, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.RESOLVED
    assert "MOCK_SESSION" in resolution.reason_codes


def test_cross_midnight_session_labels_by_start_day() -> None:
    profile = C.session_record(
        profile_id="TESTX-OVERNIGHT-V1",
        venue_id="TESTX",
        segment_scope="TEST",
        timezone_name="Asia/Kolkata",
        trading_date_convention="LABEL_BY_START_DAY",
        session_type=C.SessionType.REGULAR,
        opening_anchor_local="21:00",
        tradable_intervals=[C.TradingIntervalV1(start_local="21:00", end_local="02:00")],
    )
    evening = sm.locate_timestamp(profile, datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc))
    after_midnight = sm.locate_timestamp(profile, datetime(2026, 9, 14, 20, 29, tzinfo=timezone.utc))
    assert evening["in_session"] is True and evening["session_label"] == "2026-09-14"
    assert after_midnight["in_session"] is True and after_midnight["session_label"] == "2026-09-14"


def test_break_excluded_from_elapsed_minutes_and_phase() -> None:
    registry = build_fixture_registry()
    profile = registry.session_profile("MCX-AGRI-SHORT-V1")
    in_break = sm.locate_timestamp(profile, datetime(2026, 9, 14, 7, 45, tzinfo=timezone.utc))
    assert in_break["in_session"] is True
    assert in_break["in_break"] is True
    assert in_break["phase"] is C.SessionPhase.MID_SESSION_BREAK
    elapsed = sm.elapsed_tradable_minutes(profile, datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc))
    assert elapsed == 5 * 60


def test_seasonal_close_rule_selects_effective_profile() -> None:
    registry = build_fixture_registry()
    summer = registry.session_profile("MCX-COMM-LONG-V1")
    winter = registry.session_profile("MCX-COMM-LONG-WINTER-V1")
    late = datetime(2026, 11, 15, 18, 10, tzinfo=timezone.utc)  # 23:40 IST
    assert sm.locate_timestamp(summer, late)["in_session"] is True
    assert sm.locate_timestamp(winter, late)["in_session"] is False


def test_naive_datetimes_rejected_at_boundaries() -> None:
    profile = compat.nse_canonical_profile()
    with pytest.raises(ValueError, match="timezone-aware"):
        sm.locate_timestamp(profile, datetime(2026, 9, 14, 6, 0))


# contract -------------------------------------------------------------------
def test_commodity_contract_resolves_with_distinct_last_trade_and_expiry() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="MCX-COMM:CRUDEOIL",
        contract_key="MCX-COMM:CRUDEOIL-2026-09", as_of=MCX_EVENING, knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.RESOLVED
    identity = resolution.identity
    assert identity is not None and identity.contract_key == "MCX-COMM:CRUDEOIL-2026-09"
    assert identity.calendar_record_id == "MCX-2026-09-14-R1"
    contract = registry.contract("MCX-COMM:CRUDEOIL-2026-09")
    assert contract.last_trade_at is not None and contract.expiry_at is not None
    assert contract.last_trade_at < contract.expiry_at


def test_unique_live_contract_is_selected_without_guessing() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-DERIV:NIFTY", as_of=NSE_MORNING, knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.RESOLVED
    assert resolution.identity is not None
    assert resolution.identity.contract_key == "NSE-DERIV:NIFTY-2026-09"


def test_reusing_expired_contract_fails_closed() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="MCX-COMM:CRUDEOIL",
        contract_key="MCX-COMM:CRUDEOIL-2026-09",
        as_of=datetime(2026, 9, 19, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "CONTRACT_EXPIRED" in resolution.reason_codes


def test_unlisted_contract_fails_closed() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="MCX-COMM:CRUDEOIL",
        contract_key="MCX-COMM:CRUDEOIL-2026-09",
        as_of=datetime(2026, 5, 1, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "CONTRACT_NOT_EFFECTIVE" in resolution.reason_codes


def test_wrong_product_contract_key_fails_closed() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-DERIV:NIFTY",
        contract_key="MCX-COMM:CRUDEOIL-2026-09", as_of=NSE_MORNING, knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.AMBIGUOUS
    assert "CONTRACT_AMBIGUOUS" in resolution.reason_codes


def test_cash_vs_physical_and_close_vs_settlement_are_distinct() -> None:
    registry = build_fixture_registry()
    contract = registry.contract("MCX-COMM:CRUDEOIL-2026-09")
    assert contract.settlement_type is C.SettlementType.CASH
    assert contract.daily_settlement_reference != contract.final_settlement_reference
    assert contract.daily_settlement_reference != "LAST_TRADED_PRICE_AT_SESSION_END"


def test_missing_settlement_semantics_is_explicit_not_fatal() -> None:
    registry = build_fixture_registry()
    registry.add_contract(
        C.contract_record(
            contract_key="MCX-COMM:COTTON-2026-09",
            product_key="MCX-COMM:COTTON",
            venue_id="MCX",
            segment_id="COMMODITY",
            first_trade_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            last_trade_at=datetime(2026, 9, 25, tzinfo=timezone.utc),
            expiry_at=datetime(2026, 9, 25, tzinfo=timezone.utc),
            settlement_type=C.SettlementType.NOT_APPLICABLE,
            tick_rule_id="MCX-AGRI-TICK",
            eligible_data_bases=(C.DataBasis.RAW_CONTRACT,),
            effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
            published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            available_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    resolution = resolve_market_identity(
        registry, instrument_key="MCX-COMM:COTTON",
        contract_key="MCX-COMM:COTTON-2026-09",
        as_of=datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    assert resolution.state is C.ResolutionState.RESOLVED
    assert "SETTLEMENT_SEMANTICS_UNAVAILABLE" in resolution.reason_codes


# tick / precision / lot -------------------------------------------------------
def test_static_tick_grid_and_precision() -> None:
    registry = build_fixture_registry()
    rule = registry.price_rule("NSE-CASH-TICK", NSE_MORNING, K)
    assert rule is not None
    assert pr.is_on_tick_grid(rule, "1500.25") is True
    assert pr.is_on_tick_grid(rule, "1500.27") is False
    assert pr.quantize_to_precision(rule, "1500.256") == Decimal("1500.26")
    pr.check_precision_consistency(rule)


def test_banded_tick_boundaries() -> None:
    registry = build_fixture_registry()
    rule = registry.price_rule("MCX-ENERGY-TICK", MCX_EVENING, K)
    assert rule is not None
    assert pr.tick_for_price(rule, Decimal("1000.00")) == Decimal("0.50")
    assert pr.tick_for_price(rule, Decimal("1000.01")) == Decimal("1.00")
    assert pr.is_on_tick_grid(rule, "1000.50") is False
    assert pr.is_on_tick_grid(rule, "1001.00") is True


def test_tick_revision_is_versioned_and_replayable() -> None:
    registry = build_fixture_registry()
    old = registry.price_rule("NSE-DERIV-TICK", NSE_MORNING, K)
    new = registry.price_rule(
        "NSE-DERIV-TICK", datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc), K
    )
    assert old is not None and new is not None
    assert old.tick == Decimal("0.05") and new.tick == Decimal("0.10")
    assert old.record_hash != new.record_hash


def test_invalid_tick_definitions_rejected() -> None:
    base = {
        "rule_id": "BAD", "rule_version": "v1", "venue_id": "NSE",
        "segment_scope": "CASH", "instrument_scope": "X",
        "rule_type": C.PriceRuleType.STATIC_TICK, "price_precision": 2,
    }
    with pytest.raises(ValueError):
        C.price_rule_record(tick="0", **base)
    with pytest.raises(ValueError):
        C.price_rule_record(tick="-0.05", **base)
    with pytest.raises(ValueError):
        C.price_rule_record(tick=float("nan"), **base)
    with pytest.raises(ValueError):
        C.price_rule_record(tick="0.05", **{**base, "price_precision": -1})
    rule = C.price_rule_record(tick="0.05", **base)
    with pytest.raises(ValueError, match="precision"):
        pr.check_precision_consistency(
            C.price_rule_record(tick="0.05", price_precision=1, **{k: v for k, v in base.items() if k != "price_precision"})
        )
    assert rule.tick == Decimal("0.05")


def test_lot_revision_replay_uses_old_rule() -> None:
    registry = build_fixture_registry()
    old = registry.lot_rule("NSE-NIFTY-LOT", NSE_MORNING, K)
    new = registry.lot_rule("NSE-NIFTY-LOT", datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc), K)
    assert old is not None and new is not None
    assert old.lot_size == 75 and new.lot_size == 50
    assert pr.check_lot_quantity(old, 150) is True
    assert pr.check_lot_quantity(old, 100) is False
    assert pr.notional_value(old, "100.00") == Decimal("7500.00")


# data basis ---------------------------------------------------------------------
def test_continuous_without_roll_map_cannot_masquerade_as_raw() -> None:
    registry = build_fixture_registry()
    for basis in (
        C.DataBasis.BACK_ADJUSTED_CONTINUOUS,
        C.DataBasis.RATIO_ADJUSTED_CONTINUOUS,
        C.DataBasis.UNADJUSTED_CONTINUOUS,
        C.DataBasis.UNKNOWN,
    ):
        resolution = resolve_market_identity(
            registry, instrument_key="MCX-COMM:CRUDEOIL",
            contract_key="MCX-COMM:CRUDEOIL-2026-09",
            as_of=MCX_EVENING, knowledge_cutoff=K, data_basis=basis,
        )
        assert resolution.state is C.ResolutionState.UNAVAILABLE
        assert "DATA_BASIS_CONFLICT" in resolution.reason_codes


def test_cash_basis_rules() -> None:
    registry = build_fixture_registry()
    ok_cash = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=NSE_MORNING, knowledge_cutoff=K, data_basis=C.DataBasis.RAW_CASH,
    )
    assert ok_cash.state is C.ResolutionState.RESOLVED
    ok_adj = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=NSE_MORNING, knowledge_cutoff=K, data_basis=C.DataBasis.CORPORATE_ACTION_ADJUSTED,
    )
    assert ok_adj.state is C.ResolutionState.RESOLVED
    bad = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=NSE_MORNING, knowledge_cutoff=K, data_basis=C.DataBasis.BACK_ADJUSTED_CONTINUOUS,
    )
    assert bad.state is C.ResolutionState.UNAVAILABLE


# observability --------------------------------------------------------------------
def test_availability_summary_is_bounded() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="MCX-COMM:CRUDEOIL",
        contract_key="MCX-COMM:CRUDEOIL-2026-09", as_of=MCX_EVENING, knowledge_cutoff=K,
        data_basis=C.DataBasis.RAW_CONTRACT,
    )
    summary = availability_summary(resolution)
    assert summary["state"] == "RESOLVED"
    assert summary["contract_state"] == "BOUND"
    assert summary["calendar_record"] == "MCX-2026-09-14-R1"
    assert summary["latency_ms"] >= 0.0
