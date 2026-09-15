"""ORB BUILD-2 hardening: bitemporal replay, determinism, authority,
anti-regression scans, cache isolation, and source receipts.

Research-only. Every test pins a refusal-to-guess behavior or a
byte-stability property; nothing here grants execution authority.
"""

from __future__ import annotations

from dataclasses import fields, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.orb.candidate_intake import InstrumentType
from app.orb.market_identity import contracts as C
from app.orb.market_identity import price_rules as pr
from app.orb.market_identity import source_receipts as sr
from app.orb.market_identity.registry import MarketIdentityRegistry, RegistryError
from app.orb.market_identity.resolver import resolve_market_identity
from market_identity_support import FIXTURES_DIR, build_fixture_registry

K = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)
NSE_MORNING = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)

REASON_CODES = {
    "IDENTITY_NOT_FOUND",
    "IDENTITY_AMBIGUOUS",
    "VENUE_CONFLICT",
    "SEGMENT_CONFLICT",
    "CONTRACT_NOT_FOUND",
    "CONTRACT_AMBIGUOUS",
    "CONTRACT_NOT_EFFECTIVE",
    "CONTRACT_EXPIRED",
    "CALENDAR_UNAVAILABLE",
    "CALENDAR_STALE",
    "CALENDAR_CONFLICT",
    "SESSION_NOT_RESOLVED",
    "SOURCE_NOT_CAUSAL",
    "FUTURE_RULE",
    "PRICE_RULE_UNAVAILABLE",
    "LOT_RULE_UNAVAILABLE",
    "SETTLEMENT_SEMANTICS_UNAVAILABLE",
    "DATA_BASIS_CONFLICT",
    "PROVIDER_ALIAS_AMBIGUOUS",
    "SOURCE_HASH_MISMATCH",
    "MOCK_SESSION",
    "SPECIAL_SESSION",
    "RESOLUTION_ERROR",
}


# bitemporal replay ------------------------------------------------------------
def test_correction_is_visible_only_after_publication() -> None:
    registry = build_fixture_registry()
    as_of = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
    early_cutoff = datetime(2026, 9, 11, 0, 0, tzinfo=timezone.utc)
    stale = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=as_of, knowledge_cutoff=early_cutoff
    )
    assert stale.state is C.ResolutionState.STALE
    assert "CALENDAR_STALE" in stale.reason_codes
    late = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=as_of, knowledge_cutoff=K
    )
    assert late.state is C.ResolutionState.UNAVAILABLE
    assert "SESSION_NOT_RESOLVED" in late.reason_codes
    assert late.identity is None


def test_future_published_rule_is_forbidden_to_history() -> None:
    registry = build_fixture_registry()
    before = registry.price_rule("NSE-DERIV-TICK", NSE_MORNING, datetime(2026, 9, 19, tzinfo=timezone.utc))
    assert before is not None and before.rule_version == "2020-01"
    after = registry.price_rule("NSE-DERIV-TICK", NSE_MORNING, K)
    assert after is not None and after.rule_version == "2020-01"


def test_effective_earlier_but_published_later_rule_applies() -> None:
    registry = build_fixture_registry()
    rule = registry.lot_rule("NSE-NIFTY-LOT", datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc), K)
    assert rule is not None and rule.lot_size == 50
    # Published 2026-09-20, so a cutoff before publication cannot see it even
    # though the decision instant is later — and the expired rule does not
    # linger either. Fail closed: no applicable rule, no silent substitution.
    blind = registry.lot_rule(
        "NSE-NIFTY-LOT",
        datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 19, tzinfo=timezone.utc),
    )
    assert blind is None


def test_append_only_supersession_keeps_history() -> None:
    registry = build_fixture_registry()
    bucket = registry._calendars[("NSE", "CASH", date(2026, 9, 21))]
    assert sorted(item.record_id for item in bucket) == ["NSE-2026-09-21-V1", "NSE-2026-09-21-V2"]
    assert {item.lifecycle for item in bucket} == {C.RegistryLifecycle.SUPERSEDED, C.RegistryLifecycle.ACTIVE}


def test_illegal_lifecycle_transition_rejected() -> None:
    registry = build_fixture_registry()
    with pytest.raises(RegistryError):
        registry.set_calendar_lifecycle("NSE-2026-09-14-R1", "NSE", "CASH", date(2026, 9, 14), C.RegistryLifecycle.DRAFT)
    registry.set_calendar_lifecycle("NSE-2026-09-14-R1", "NSE", "CASH", date(2026, 9, 14), C.RegistryLifecycle.SUPERSEDED)
    with pytest.raises(RegistryError):
        registry.set_calendar_lifecycle("NSE-2026-09-14-R1", "NSE", "CASH", date(2026, 9, 14), C.RegistryLifecycle.ACTIVE)


def test_unavailable_date_is_not_a_holiday() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 23, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "CALENDAR_UNAVAILABLE" in resolution.reason_codes


def test_conflicting_live_records_fail_closed() -> None:
    registry = build_fixture_registry()
    registry.add_calendar_record(
        C.calendar_record(
            record_id="NSE-2026-09-14-RX",
            effective_date=date(2026, 9, 14),
            venue_id="NSE",
            segment_scope="CASH",
            profile_id="NSE-CASH-REGULAR-V1",
            session_type=C.SessionType.PARTIAL,
            session_label="2026-09-14",
            tradable_intervals_override=(
                C.TradingIntervalV1(start_local="09:15", end_local="12:00", phase=C.SessionPhase.REGULAR),
            ),
            lifecycle=C.RegistryLifecycle.ACTIVE,
            published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            available_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert resolution.state is C.ResolutionState.AMBIGUOUS
    assert "CALENDAR_CONFLICT" in resolution.reason_codes


# determinism --------------------------------------------------------------------
def test_identical_inputs_replay_identical_hashes() -> None:
    registry = build_fixture_registry()
    first = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    second = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert first.identity is not None and second.identity is not None
    assert first.identity.market_identity_hash == second.identity.market_identity_hash
    assert first.output_hash == second.output_hash
    assert first.input_hash == second.input_hash


def test_registry_load_order_does_not_change_hashes() -> None:
    first = build_fixture_registry(registry_id="same")
    second = build_fixture_registry(registry_id="same")
    assert first.registry_version_hash() == second.registry_version_hash()
    one = resolve_market_identity(
        first, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    two = resolve_market_identity(
        second, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert one.output_hash == two.output_hash


def test_timezone_representation_replays_stably() -> None:
    from zoneinfo import ZoneInfo

    registry = build_fixture_registry()
    utc = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    kolkata = NSE_MORNING.astimezone(ZoneInfo("Asia/Kolkata"))
    local = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=kolkata, knowledge_cutoff=K
    )
    assert local.state is C.ResolutionState.RESOLVED
    assert utc.identity is not None and local.identity is not None
    assert utc.identity.market_identity_hash == local.identity.market_identity_hash
    assert utc.output_hash == local.output_hash


def test_conflicting_duplicates_fail_identically() -> None:
    def _conflicted() -> MarketIdentityRegistry:
        registry = build_fixture_registry()
        registry.add_calendar_record(
            C.calendar_record(
                record_id="NSE-2026-09-14-RX",
                effective_date=date(2026, 9, 14),
                venue_id="NSE",
                segment_scope="CASH",
                profile_id="NSE-CASH-REGULAR-V1",
                session_type=C.SessionType.PARTIAL,
                session_label="2026-09-14",
                tradable_intervals_override=(
                    C.TradingIntervalV1(start_local="09:15", end_local="12:00", phase=C.SessionPhase.REGULAR),
                ),
                lifecycle=C.RegistryLifecycle.ACTIVE,
                published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                available_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            )
        )
        return registry

    one = resolve_market_identity(
        _conflicted(), instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    two = resolve_market_identity(
        _conflicted(), instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert one.state is two.state is C.ResolutionState.AMBIGUOUS
    assert one.output_hash == two.output_hash


def test_record_hashes_change_with_rule_version() -> None:
    registry = build_fixture_registry()
    old = registry.price_rule("NSE-DERIV-TICK", NSE_MORNING, K)
    new = registry.price_rule("NSE-DERIV-TICK", datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc), K)
    assert old is not None and new is not None
    assert old.record_hash != new.record_hash


# authority ------------------------------------------------------------------------
def test_identity_carries_no_direction_or_execution_fields() -> None:
    names = {item.name for item in fields(C.MarketIdentityV1)}
    assert names.isdisjoint({"direction", "entry", "stop", "target", "probability", "final_band", "setup"})
    resolution_names = {item.name for item in fields(C.MarketIdentityResolutionV1)}
    assert resolution_names.isdisjoint({"direction", "entry", "stop", "target", "probability", "final_band"})


def test_zero_authority_on_identity_and_resolution() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert resolution.identity is not None
    for obj in (resolution.identity, resolution):
        assert obj.research_only is True
        assert obj.trade_allowed is False
        assert obj.order_routing_enabled is False
        assert obj.live_trading_blocked is True
        assert obj.may_set_final_band is False
        assert obj.may_execute is False


def test_hostile_direct_construction_cannot_gain_authority() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert resolution.identity is not None
    hostile = {
        "research_only": False,
        "trade_allowed": True,
        "order_routing_enabled": True,
        "live_trading_blocked": False,
        "may_set_final_band": True,
        "may_execute": True,
    }
    for field_name, bad_value in hostile.items():
        with pytest.raises(ValueError):
            replace(resolution.identity, **{field_name: bad_value})
        with pytest.raises(ValueError):
            replace(resolution, **{field_name: bad_value})


def test_reason_codes_come_from_registered_set() -> None:
    registry = build_fixture_registry()
    cases = [
        resolve_market_identity(registry, instrument_key="NOPE", as_of=NSE_MORNING, knowledge_cutoff=K),
        resolve_market_identity(
            registry, instrument_key="MCX-COMM:CRUDEOIL",
            contract_key="MCX-COMM:CRUDEOIL-2026-09", as_of=NSE_MORNING, knowledge_cutoff=K,
            data_basis=C.DataBasis.BACK_ADJUSTED_CONTINUOUS,
        ),
        resolve_market_identity(
            registry, instrument_key="NSE-CASH:RELIANCE",
            as_of=datetime(2026, 9, 19, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
        ),
    ]
    for resolution in cases:
        assert resolution.reason_codes
        assert set(resolution.reason_codes) <= REASON_CODES


# anti-regression scans --------------------------------------------------------------
_PACKAGE = Path(__file__).resolve().parent / "app" / "orb" / "market_identity"


def _package_sources() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(_PACKAGE.glob("*.py"))}


def test_no_weekday_expiry_inference_in_canonical_code() -> None:
    for name, text in _package_sources().items():
        assert "weekday" not in text, name
        assert "dayofweek" not in text, name
        assert "last Thursday" not in text and "last Tuesday" not in text, name


def test_no_calendar_day_grouping_in_canonical_code() -> None:
    for name, text in _package_sources().items():
        assert 'resample(' not in text, name


def test_no_hardcoded_session_clock_outside_legacy_adapter() -> None:
    for name, text in _package_sources().items():
        if name == "compatibility.py":
            assert "LEGACY_NSE_OPEN" in text and "LEGACY_NSE_CLOSE" in text
            continue
        assert "09:15" not in text, name
        assert "15:30" not in text, name


def test_no_fixed_offset_session_math_outside_legacy_adapter() -> None:
    for name, text in _package_sources().items():
        if name == "compatibility.py":
            continue
        assert "timezone(timedelta" not in text, name


def test_date_usage_is_inventoried() -> None:
    # .date() appears only in session.py label/convention math (exchange-local
    # trading-date derivation with cross-midnight adjustment) and registry.py
    # calendar-day keys. Naive `.date() == session` grouping is forbidden.
    for name, text in _package_sources().items():
        if name in {"session.py", "registry.py", "contracts.py"}:
            continue
        assert ".date()" not in text, name


# cache -------------------------------------------------------------------------------
def test_cache_hit_replays_without_recompute() -> None:
    registry = build_fixture_registry()
    kwargs = {"instrument_key": "NSE-CASH:RELIANCE", "as_of": NSE_MORNING, "knowledge_cutoff": K}
    first = resolve_market_identity(registry, **kwargs)
    stats_before = dict(registry.cache_stats())
    second = resolve_market_identity(registry, **kwargs)
    stats_after = dict(registry.cache_stats())
    assert second.output_hash == first.output_hash
    assert stats_after["hits"] == stats_before["hits"] + 1


def test_cache_is_isolated_across_sessions_and_cutoffs() -> None:
    registry = build_fixture_registry()
    resolve_market_identity(registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K)
    other = resolve_market_identity(
        registry, instrument_key="NSE-CASH:RELIANCE",
        as_of=datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc), knowledge_cutoff=K,
    )
    assert other.identity is not None
    assert other.identity.calendar_record_id == "NSE-2026-09-15-R1"
    stats = registry.cache_stats()
    assert stats["misses"] >= 2


def test_registry_mutation_clears_cache() -> None:
    registry = build_fixture_registry()
    resolve_market_identity(registry, instrument_key="NSE-CASH:RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K)
    assert registry.cache_stats()["entries"] >= 1
    registry.add_calendar_record(
        C.calendar_record(
            record_id="NSE-2026-09-22-R1",
            effective_date=date(2026, 9, 22),
            venue_id="NSE",
            segment_scope="CASH",
            profile_id="NSE-CASH-REGULAR-V1",
            session_type=C.SessionType.REGULAR,
            session_label="2026-09-22",
            lifecycle=C.RegistryLifecycle.ACTIVE,
            published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            available_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    assert registry.cache_stats()["entries"] == 0


def test_batch_resolution_has_no_superlinear_blowup() -> None:
    import time

    registry = build_fixture_registry()
    keys = ["NSE-CASH:RELIANCE", "NSE-DERIV:NIFTY", "MCX-COMM:CRUDEOIL", "MCX-COMM:COTTON"]
    as_ofs = [datetime(2026, 9, 14, h, 0, tzinfo=timezone.utc) for h in range(0, 20)]
    started = time.perf_counter()
    count = 0
    for key in keys:
        for moment in as_ofs:
            resolve_market_identity(registry, instrument_key=key, as_of=moment, knowledge_cutoff=K)
            count += 1
    elapsed = time.perf_counter() - started
    assert count == 80
    assert elapsed < 60.0


# source receipts --------------------------------------------------------------------------
def test_receipt_round_trip_and_cutoff() -> None:
    content = b'{"exchange": "TEST", "rule": "session 09:00-17:00"}'
    receipt = sr.receipt_for_bytes(
        source_id="TEST-SRC-1",
        source_type="EXCHANGE_CIRCULAR",
        provider="TEST-EXCHANGE",
        document_id="CIR-1",
        artifact_identity="fixtures/cir-1.json",
        content=content,
        parser_version="TEST-PARSER-V1",
        published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    assert sr.verify_content(receipt, content) is True
    assert sr.verify_content(receipt, b"tampered") is False
    assert sr.receipt_age_ok(receipt, K) is True
    assert sr.receipt_age_ok(receipt, datetime(2026, 8, 1, tzinfo=timezone.utc)) is False


def test_fixture_provenance_is_explicit_test_data() -> None:
    import json

    for name in ("venues.json", "instruments.json", "sessions.json", "calendars.json", "contracts.json"):
        payload = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
        assert payload["provenance"].startswith("TEST_"), name


def test_provider_alias_change_is_effective_dated() -> None:
    registry = build_fixture_registry()
    early = datetime(2019, 6, 1, tzinfo=timezone.utc)
    assert registry.venues_for_alias("hstry", "NSE", early) == []
    assert [v.segment_code for v in registry.venues_for_alias("hstry", "NSE", NSE_MORNING)] == ["CASH"]


def test_unavailable_identity_never_falls_back_to_nse() -> None:
    registry = build_fixture_registry()
    resolution = resolve_market_identity(
        registry, provider_alias="XYZUNKNOWN", venue_id="NSE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    assert resolution.state is C.ResolutionState.UNAVAILABLE
    assert "IDENTITY_NOT_FOUND" in resolution.reason_codes
    assert resolution.identity is None


def test_venue_conflict_requires_segment() -> None:
    registry = build_fixture_registry()
    with pytest.raises(RegistryError, match="VENUE_CONFLICT"):
        registry.venue("NSE")
    venue = registry.venue("NSE", "CASH")
    assert venue.segment_code == "CASH"


def test_provider_alias_collision_is_visible() -> None:
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
    resolution = resolve_market_identity(registry, provider_alias="RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K)
    assert resolution.state is C.ResolutionState.AMBIGUOUS
    provider_hit = resolve_market_identity(
        registry, provider="hstry", provider_alias="RELIANCE", as_of=NSE_MORNING, knowledge_cutoff=K
    )
    # The hstry namespace claims only NSE-CASH:RELIANCE, so the provider
    # scope disambiguates deterministically instead of guessing.
    assert provider_hit.state is C.ResolutionState.RESOLVED
    assert provider_hit.identity is not None
    assert provider_hit.identity.instrument_key == "NSE-CASH:RELIANCE"
