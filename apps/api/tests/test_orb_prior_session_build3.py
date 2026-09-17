"""ORB BUILD-3 previous-session reconstruction suite (M7 adversarial matrix).

Additive-only: this file plus app/orb/prior_session/ are the entire BUILD-3
surface. No legacy module is modified here. Every test is an executable
acceptance check for the plan's GREEN gate.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from dataclasses import replace

from app.models import CandleBar
from app.orb.candidate_intake import AvailabilityState
from app.orb.market_identity import contracts as C
from app.orb.prior_session import (
    ComparisonOutcome,
    GridUnavailable,
    OrbCalculationReceiptRefV1,
    ReferenceType,
    SessionCompleteness,
    SourceCadence,
    assign_session_label,
    build_completed_session,
    build_expected_grid,
    build_prior_snapshot,
    build_reference_price,
    build_snapshot_map,
    compare_references,
    reconstruct_history,
    select_prior_session,
    session_close_reference,
    slice_snapshots,
)
from app.orb.prior_session.contracts import (
    OrbCompletedSessionV1,
    OrbPriorSessionContextSnapshotV1,
    OrbSourceComparisonReceiptV1,
)

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc
NS5 = 5 * 60_000_000_000
NS1 = 60_000_000_000


def utc_ns(local_day: date, clock: str, tz: ZoneInfo = IST) -> int:
    hour, minute = int(clock[:2]), int(clock[3:])
    return int(datetime(local_day.year, local_day.month, local_day.day, hour, minute, tzinfo=tz).timestamp() * 1_000_000_000)


def nse_profile() -> C.SessionProfileV1:
    return C.session_record(
        profile_id="NSE-CASH-REGULAR-V1",
        venue_id="NSE",
        segment_scope="CASH",
        timezone_name="Asia/Kolkata",
        trading_date_convention="LABEL_EQUALS_LOCAL_DATE",
        session_type=C.SessionType.REGULAR,
        opening_anchor_local="09:15",
        tradable_intervals=[C.TradingIntervalV1(start_local="09:15", end_local="15:30")],
    )


def mcx_profile() -> C.SessionProfileV1:
    return C.session_record(
        profile_id="MCX-COMM-EVENING-V1",
        venue_id="MCX",
        segment_scope="COMMODITY",
        timezone_name="Asia/Kolkata",
        trading_date_convention="LABEL_EQUALS_START_DAY",
        session_type=C.SessionType.REGULAR,
        opening_anchor_local="09:00",
        tradable_intervals=[C.TradingIntervalV1(start_local="09:00", end_local="23:55")],
    )


def night_profile() -> C.SessionProfileV1:
    """True cross-midnight session: 18:00 -> 02:00 next civil day."""
    return C.session_record(
        profile_id="NIGHT-CROSS-MIDNIGHT-V1",
        venue_id="TESTEX",
        segment_scope="NIGHT",
        timezone_name="Asia/Kolkata",
        trading_date_convention="LABEL_EQUALS_START_DAY",
        session_type=C.SessionType.REGULAR,
        opening_anchor_local="18:00",
        tradable_intervals=[C.TradingIntervalV1(start_local="18:00", end_local="02:00")],
    )


def live_calendar(label: str, profile_id: str, session_type: C.SessionType = C.SessionType.REGULAR,
                  override=None) -> C.CalendarRecordV1:
    return C.calendar_record(
        record_id=f"CAL-{label}",
        effective_date=date.fromisoformat(label),
        venue_id="NSE",
        segment_scope="CASH",
        profile_id=profile_id,
        session_type=session_type,
        session_label=label,
        tradable_intervals_override=override,
        lifecycle=C.RegistryLifecycle.ACTIVE,
        available_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def cutoff_after(label: str, clock: str = "16:00") -> datetime:
    day = date.fromisoformat(label)
    return datetime(day.year, day.month, day.day, *map(int, clock.split(":"), ), tzinfo=IST).astimezone(UTC)


def grid_for(label: str, profile=None, calendar=None, timeframe="5m", duration=NS5,
             cadence=SourceCadence.FIXED_INTERVAL_BAR_CADENCE, basis=C.DataBasis.RAW_CASH,
             cutoff=None, contract_key=None):
    profile = profile or nse_profile()
    cutoff = cutoff or cutoff_after(label)
    return build_expected_grid(
        instrument_key="RELIANCE", contract_key=contract_key, session_label=label,
        profile=profile, calendar=calendar, timeframe=timeframe,
        timeframe_duration_ns=duration, data_basis=basis, source_cadence=cadence,
        market_as_of=cutoff, knowledge_cutoff=cutoff, source_id="test-stream",
    )


def session_bars(label: str, grid, start_price: float = 100.0, volume: float | None = 10.0,
                 symbol: str = "RELIANCE", missing: set[int] | None = None):
    bars = []
    for seq, ns in enumerate(grid.expected_slot_opens_ns, start=1):
        if ns in (missing or set()):
            continue
        o = start_price + seq * 0.01
        bars.append(CandleBar(symbol=symbol, timeframe="5m", timestamp_ns=ns,
                              open=o, high=o + 0.05, low=o - 0.05, close=o + 0.01,
                              volume=volume, source="mock", sequence_number=seq))
    return bars


def complete_session(label: str, **kwargs):
    grid = grid_for(label, **{k: v for k, v in kwargs.items() if k in
                              ("profile", "calendar", "timeframe", "duration", "cadence", "basis", "cutoff", "contract_key")})
    bars = session_bars(label, grid, **{k: v for k, v in kwargs.items() if k in ("start_price", "volume", "symbol")})
    return build_completed_session(grid, bars, symbol=kwargs.get("symbol", "RELIANCE"),
                                   venue_id="NSE", segment_id="CASH",
                                   instrument_type="NSE_EQUITY", currency="INR")


# ---------------------------------------------------------------- grid (3A)


class TestExpectedGrid:
    def test_nse_5m_slot_count(self):
        assert len(grid_for("2026-09-10").expected_slot_opens_ns) == 75

    def test_nse_1m_slot_count(self):
        assert len(grid_for("2026-09-10", timeframe="1m", duration=NS1).expected_slot_opens_ns) == 375

    def test_half_open_first_last(self):
        grid = grid_for("2026-09-10")
        assert grid.expected_slot_opens_ns[0] == utc_ns(date(2026, 9, 10), "09:15")
        assert grid.expected_slot_opens_ns[-1] == utc_ns(date(2026, 9, 10), "15:25")
        assert grid.session_market_start_ns == utc_ns(date(2026, 9, 10), "09:15")
        assert grid.session_market_end_ns == utc_ns(date(2026, 9, 10), "15:30")

    def test_break_excluded_from_grid(self):
        profile = C.session_record(
            profile_id="BRK-V1", venue_id="NSE", segment_scope="CASH", timezone_name="Asia/Kolkata",
            trading_date_convention="X", session_type=C.SessionType.REGULAR, opening_anchor_local="09:15",
            tradable_intervals=[C.TradingIntervalV1(start_local="09:15", end_local="15:30")],
            break_intervals=(C.TradingIntervalV1(start_local="12:00", end_local="12:30",
                                                 phase=C.SessionPhase.MID_SESSION_BREAK),),
        )
        grid = grid_for("2026-09-10", profile=profile)
        assert len(grid.expected_slot_opens_ns) == 75 - 6
        assert len(grid.break_windows_ns) == 1

    def test_cross_midnight_labels_by_start_day(self):
        profile = night_profile()
        grid = grid_for("2026-09-10", profile=profile, basis=C.DataBasis.RAW_CONTRACT,
                        contract_key="NIGHT-2026-09", timeframe="1H",
                        duration=60 * 60_000_000_000)
        assert len(grid.expected_slot_opens_ns) == 8  # 18:00 -> 02:00
        assert grid.session_market_start_ns == utc_ns(date(2026, 9, 10), "18:00")
        assert grid.session_market_end_ns == utc_ns(date(2026, 9, 11), "02:00")
        assert assign_session_label(bar_open_ns=utc_ns(date(2026, 9, 10), "19:00"),
                                    profile=profile, calendars_by_date={}) == "2026-09-10"
        assert assign_session_label(bar_open_ns=utc_ns(date(2026, 9, 11), "00:30"),
                                    profile=profile, calendars_by_date={}) == "2026-09-10"
        assert assign_session_label(bar_open_ns=utc_ns(date(2026, 9, 11), "02:00"),
                                    profile=profile, calendars_by_date={}) is None
        assert assign_session_label(bar_open_ns=utc_ns(date(2026, 9, 10), "17:59"),
                                    profile=profile, calendars_by_date={}) is None

    def test_partial_override_grid(self):
        muhurat = (C.TradingIntervalV1(start_local="13:45", end_local="14:45"),)
        cal = live_calendar("2026-10-21", "NSE-CASH-REGULAR-V1",
                            session_type=C.SessionType.SPECIAL, override=muhurat)
        grid = grid_for("2026-10-21", calendar=cal)
        assert len(grid.expected_slot_opens_ns) == 12
        assert grid.session_type is C.SessionType.SPECIAL

    def test_closed_holiday_unavailable(self):
        cal = live_calendar("2026-11-08", "NSE-CASH-REGULAR-V1", session_type=C.SessionType.CLOSED_HOLIDAY)
        with pytest.raises(GridUnavailable):
            grid_for("2026-11-08", calendar=cal)

    def test_non_live_calendar_rejected(self):
        cal = C.calendar_record(
            record_id="DRAFT-1", effective_date=date(2026, 9, 10), venue_id="NSE",
            segment_scope="CASH", profile_id="NSE-CASH-REGULAR-V1", session_type=C.SessionType.REGULAR,
            session_label="2026-09-10", lifecycle=C.RegistryLifecycle.DRAFT,
            available_at=datetime(2026, 1, 1, tzinfo=UTC))
        with pytest.raises(ValueError):
            grid_for("2026-09-10", calendar=cal)

    def test_untileable_timeframe_fails_explicitly(self):
        with pytest.raises(GridUnavailable):
            grid_for("2026-09-10", timeframe="daily", duration=24 * 60 * 60_000_000_000)

    def test_sparse_cadence_grid_not_required(self):
        grid = grid_for("2026-09-10", cadence=SourceCadence.SPARSE_EVENT_TRADE_CADENCE)
        assert grid.slots_are_required is False

    def test_unknown_cadence_grid_not_required(self):
        grid = grid_for("2026-09-10", cadence=SourceCadence.UNKNOWN_CADENCE)
        assert grid.slots_are_required is False

    def test_grid_hash_deterministic(self):
        assert grid_for("2026-09-10").grid_hash == grid_for("2026-09-10").grid_hash


# ------------------------------------------------------- reconstruction (3B)


class TestReconstruction:
    def test_exact_ohlc(self):
        grid = grid_for("2026-09-10")
        completed = build_completed_session(grid, session_bars("2026-09-10", grid),
                                            symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.COMPLETE_TRUSTED
        assert completed.open == pytest.approx(100.01)
        assert completed.close == pytest.approx(100.76)
        assert completed.high == pytest.approx(100.80)
        assert completed.low == pytest.approx(99.96)
        assert completed.session_volume == pytest.approx(750.0)
        assert completed.price_availability is AvailabilityState.AVAILABLE
        assert completed.volume_availability is AvailabilityState.AVAILABLE

    def test_missing_middle_bar_incomplete(self):
        grid = grid_for("2026-09-10")
        missing = {grid.expected_slot_opens_ns[37]}
        bars = session_bars("2026-09-10", grid, missing=missing)
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.INCOMPLETE
        assert completed.coverage.missing_slot_count == 1
        assert completed.coverage.missing_slot_opens_ns == (grid.expected_slot_opens_ns[37],)
        assert completed.price_availability is AvailabilityState.UNAVAILABLE

    def test_missing_first_and_last_bar(self):
        grid = grid_for("2026-09-10")
        missing = {grid.expected_slot_opens_ns[0], grid.expected_slot_opens_ns[-1]}
        completed = build_completed_session(grid, session_bars("2026-09-10", grid, missing=missing),
                                            symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.INCOMPLETE
        assert completed.coverage.missing_slot_count == 2

    def test_all_volume_missing_degraded_not_zero(self):
        grid = grid_for("2026-09-10")
        completed = build_completed_session(grid, session_bars("2026-09-10", grid, volume=None),
                                            symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.COMPLETE_DEGRADED
        assert completed.session_volume is None
        assert completed.volume_availability is AvailabilityState.UNAVAILABLE
        assert completed.price_availability is AvailabilityState.AVAILABLE

    def test_one_missing_volume_degraded(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        bars[10] = bars[10].model_copy(update={"volume": None})
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.COMPLETE_DEGRADED
        assert completed.session_volume is None
        assert completed.coverage.missing_volume_count == 1

    def test_observed_zero_volume_is_zero_not_missing(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        bars[0] = bars[0].model_copy(update={"volume": 0.0})
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.COMPLETE_TRUSTED
        assert completed.session_volume == pytest.approx(740.0)
        assert completed.coverage.missing_volume_count == 0

    def test_identical_duplicate_deduped(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        bars.append(bars[5])
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.COMPLETE_TRUSTED
        assert completed.coverage.duplicate_slot_count == 1

    def test_contradictory_duplicate_quarantined(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        # OHLC-valid but conflicting print at an already-observed slot.
        evil = bars[5].model_copy(update={"close": bars[5].close + 0.02})
        bars.append(evil)
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.QUARANTINED
        assert completed.coverage.conflicting_slot_count == 1

    def test_out_of_order_deterministic(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        forward = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                          segment_id="CASH", instrument_type="NSE_EQUITY")
        backward = build_completed_session(grid, list(reversed(bars)), symbol="RELIANCE",
                                           venue_id="NSE", segment_id="CASH",
                                           instrument_type="NSE_EQUITY")
        assert forward.session_hash == backward.session_hash
        assert forward.open == backward.open and forward.close == backward.close

    def test_future_bar_excluded(self):
        # A bar from the next civil day is outside this session once the
        # knowledge cutoff actually covers it (no PIT violation involved).
        grid = grid_for("2026-09-10", cutoff=cutoff_after("2026-09-11"))
        bars = session_bars("2026-09-10", grid)
        outsider = bars[-1].model_copy(update={"timestamp_ns": utc_ns(date(2026, 9, 11), "10:00"),
                                               "sequence_number": 999})
        bars.append(outsider)
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.COMPLETE_TRUSTED
        assert completed.coverage.outside_session_count == 1
        assert completed.coverage.future_bar_count == 0

    def test_bar_beyond_knowledge_cutoff_is_future(self):
        grid = grid_for("2026-09-10", cutoff=cutoff_after("2026-09-10", "10:00"))
        bars = session_bars("2026-09-10", grid)
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.PENDING
        assert completed.coverage.future_bar_count > 0

    def test_nan_bar_quarantined(self):
        grid = grid_for("2026-09-10")
        bad = SimpleNamespace(symbol="RELIANCE", timeframe="5m",
                              timestamp_ns=grid.expected_slot_opens_ns[3],
                              open=100.0, high=math.nan, low=99.0, close=99.5,
                              volume=10.0, sequence_number=77)
        # drop the valid bar at that slot so the NaN print is the observation
        bars = [b for b in session_bars("2026-09-10", grid)
                if b.timestamp_ns != bad.timestamp_ns] + [bad]
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.QUARANTINED
        assert completed.coverage.invalid_bar_count == 1

    def test_impossible_ohlc_quarantined(self):
        grid = grid_for("2026-09-10")
        bad = SimpleNamespace(symbol="RELIANCE", timeframe="5m",
                              timestamp_ns=grid.expected_slot_opens_ns[3],
                              open=100.0, high=99.0, low=98.0, close=98.5,
                              volume=10.0, sequence_number=78)
        bars = [b for b in session_bars("2026-09-10", grid)
                if b.timestamp_ns != bad.timestamp_ns] + [bad]
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.QUARANTINED

    def test_negative_volume_quarantined(self):
        grid = grid_for("2026-09-10")
        bad = SimpleNamespace(symbol="RELIANCE", timeframe="5m",
                              timestamp_ns=grid.expected_slot_opens_ns[3],
                              open=100.0, high=101.0, low=99.0, close=100.5,
                              volume=-3.0, sequence_number=79)
        bars = [b for b in session_bars("2026-09-10", grid)
                if b.timestamp_ns != bad.timestamp_ns] + [bad]
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.QUARANTINED

    def test_wrong_symbol_excluded(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        bars[0] = bars[0].model_copy(update={"symbol": "TCS"})
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.INCOMPLETE
        assert completed.coverage.wrong_identity_count == 1

    def test_wrong_contract_excluded(self):
        grid = grid_for("2026-09-10", contract_key="CRUDEOIL-2026-09",
                        basis=C.DataBasis.RAW_CONTRACT, profile=mcx_profile())
        assert grid is not None  # MCX 5m grid builds; contract check is per-bar
        nse_grid = grid_for("2026-09-10", contract_key="NIFTY-2026-09")
        bars = session_bars("2026-09-10", nse_grid)
        keys = ["NIFTY-2026-09"] * len(bars)
        keys[4] = "NIFTY-2026-10"
        completed = build_completed_session(nse_grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY",
                                            bar_contract_keys=keys)
        assert completed.completeness is SessionCompleteness.INCOMPLETE
        assert completed.coverage.wrong_identity_count == 1

    def test_break_bar_counted_not_silent(self):
        profile = C.session_record(
            profile_id="BRK-V1", venue_id="NSE", segment_scope="CASH", timezone_name="Asia/Kolkata",
            trading_date_convention="X", session_type=C.SessionType.REGULAR, opening_anchor_local="09:15",
            tradable_intervals=[C.TradingIntervalV1(start_local="09:15", end_local="15:30")],
            break_intervals=(C.TradingIntervalV1(start_local="12:00", end_local="12:30",
                                                 phase=C.SessionPhase.MID_SESSION_BREAK),),
        )
        grid = grid_for("2026-09-10", profile=profile)
        bars = session_bars("2026-09-10", grid)
        intruder = CandleBar(symbol="RELIANCE", timeframe="5m",
                             timestamp_ns=utc_ns(date(2026, 9, 10), "12:05"),
                             open=100.0, high=101.0, low=99.0, close=100.5,
                             volume=5.0, source="mock", sequence_number=999)
        bars.append(intruder)
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.coverage.break_overlap_count == 1
        assert completed.completeness is SessionCompleteness.COMPLETE_TRUSTED

    def test_empty_stream_incomplete(self):
        grid = grid_for("2026-09-10")
        completed = build_completed_session(grid, [], symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        assert completed.completeness is SessionCompleteness.INCOMPLETE
        assert completed.coverage.missing_slot_count == 75


# ------------------------------------------------------------- references (3C)


class TestReferences:
    def test_close_and_settlement_coexist_and_differ(self):
        completed = complete_session("2026-09-10")
        close_ref = session_close_reference(completed, currency="INR")
        settle_ref = build_reference_price(
            instrument_key="RELIANCE", contract_key=None, session_label="2026-09-10",
            reference_type=ReferenceType.OFFICIAL_DAILY_SETTLEMENT,
            value=float(completed.close) + 0.5, currency="INR",
            data_basis=C.DataBasis.RAW_CASH,
            market_effective_at=datetime(2026, 9, 10, 10, 30, tzinfo=UTC),
            observed_at=datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
            published_at=datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
            available_at=datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
            source_id="eod-bhavcopy", source_version="v1", source_hash="a" * 64,
            availability=AvailabilityState.AVAILABLE)
        assert close_ref.reference_type is ReferenceType.SESSION_CLOSE
        assert settle_ref.value != close_ref.value
        receipt = compare_references(close_ref, settle_ref, knowledge_cutoff=datetime(2026, 9, 11, tzinfo=UTC))
        assert receipt.outcome is ComparisonOutcome.NOT_COMPARABLE

    def test_exact_match(self):
        completed = complete_session("2026-09-10")
        ref = session_close_reference(completed, currency="INR")
        twin = session_close_reference(completed, currency="INR")
        receipt = compare_references(ref, twin, knowledge_cutoff=datetime(2026, 9, 11, tzinfo=UTC))
        assert receipt.outcome is ComparisonOutcome.MATCH
        assert receipt.absolute_difference == 0.0

    def test_within_tick_match(self):
        completed = complete_session("2026-09-10")
        ref = session_close_reference(completed, currency="INR")
        other = build_reference_price(
            instrument_key="RELIANCE", contract_key=None, session_label="2026-09-10",
            reference_type=ReferenceType.SESSION_CLOSE, value=float(completed.close) + 0.02,
            currency="INR", data_basis=C.DataBasis.RAW_CASH,
            market_effective_at=ref.market_effective_at, observed_at=ref.observed_at,
            published_at=ref.published_at, available_at=ref.available_at,
            source_id="eod", source_version="v1", source_hash="b" * 64,
            availability=AvailabilityState.AVAILABLE)
        receipt = compare_references(ref, other, tick=0.05, knowledge_cutoff=datetime(2026, 9, 11, tzinfo=UTC))
        assert receipt.outcome is ComparisonOutcome.MATCH_WITHIN_REGISTERED_TOLERANCE

    def test_true_disagreement_conflicts(self):
        completed = complete_session("2026-09-10")
        ref = session_close_reference(completed, currency="INR")
        other = build_reference_price(
            instrument_key="RELIANCE", contract_key=None, session_label="2026-09-10",
            reference_type=ReferenceType.SESSION_CLOSE, value=float(completed.close) + 2.0,
            currency="INR", data_basis=C.DataBasis.RAW_CASH,
            market_effective_at=ref.market_effective_at, observed_at=ref.observed_at,
            published_at=ref.published_at, available_at=ref.available_at,
            source_id="eod", source_version="v1", source_hash="c" * 64,
            availability=AvailabilityState.AVAILABLE)
        receipt = compare_references(ref, other, tick=0.05, knowledge_cutoff=datetime(2026, 9, 11, tzinfo=UTC))
        assert receipt.outcome is ComparisonOutcome.CONTEXT_SOURCE_CONFLICT
        assert receipt.absolute_difference == pytest.approx(2.0)

    def test_wrong_basis_not_comparable(self):
        completed = complete_session("2026-09-10")
        ref = session_close_reference(completed, currency="INR")
        adj = build_reference_price(
            instrument_key="RELIANCE", contract_key=None, session_label="2026-09-10",
            reference_type=ReferenceType.SESSION_CLOSE, value=float(completed.close),
            currency="INR", data_basis=C.DataBasis.CORPORATE_ACTION_ADJUSTED,
            adjustment_identity="SPLIT-2:1-2026-09-09",
            market_effective_at=ref.market_effective_at, observed_at=ref.observed_at,
            published_at=ref.published_at, available_at=ref.available_at,
            source_id="vendor", source_version="v1", source_hash="d" * 64,
            availability=AvailabilityState.AVAILABLE)
        receipt = compare_references(ref, adj, knowledge_cutoff=datetime(2026, 9, 11, tzinfo=UTC))
        assert receipt.outcome is ComparisonOutcome.NOT_COMPARABLE

    def test_wrong_session_not_comparable(self):
        first = complete_session("2026-09-10")
        second = complete_session("2026-09-11")
        receipt = compare_references(session_close_reference(first, currency="INR"),
                                     session_close_reference(second, currency="INR"),
                                     knowledge_cutoff=datetime(2026, 9, 12, tzinfo=UTC))
        assert receipt.outcome is ComparisonOutcome.NOT_COMPARABLE

    def test_unavailable_source_receipt(self):
        completed = complete_session("2026-09-10")
        ref = session_close_reference(completed, currency="INR")
        missing = build_reference_price(
            instrument_key="RELIANCE", contract_key=None, session_label="2026-09-10",
            reference_type=ReferenceType.OFFICIAL_DAILY_SETTLEMENT, value=None,
            currency="INR", data_basis=C.DataBasis.RAW_CASH,
            availability=AvailabilityState.UNAVAILABLE)
        receipt = compare_references(ref, missing, knowledge_cutoff=datetime(2026, 9, 11, tzinfo=UTC))
        assert receipt.outcome is ComparisonOutcome.SECONDARY_SOURCE_UNAVAILABLE

    def test_no_close_fallback_for_settlement(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid, missing={grid.expected_slot_opens_ns[0]})
        incomplete = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                             segment_id="CASH", instrument_type="NSE_EQUITY")
        ref = session_close_reference(incomplete, currency="INR")
        assert ref.availability is AvailabilityState.UNAVAILABLE
        assert ref.value is None


# ------------------------------------------------------- D-1 snapshot (3E)


class TestPriorSnapshot:
    def _two_day_map(self):
        first = complete_session("2026-09-10")
        second = complete_session("2026-09-11", start_price=200.0)
        return {"2026-09-10": first, "2026-09-11": second}

    def test_friday_to_monday(self):
        friday = complete_session("2026-09-11")
        monday = complete_session("2026-09-14", start_price=210.0)
        by_label = {"2026-09-11": friday, "2026-09-14": monday}
        prior, reason = select_prior_session(
            by_label, instrument_key="RELIANCE", contract_key=None,
            data_basis=C.DataBasis.RAW_CASH, current_session_label="2026-09-14",
            knowledge_cutoff=cutoff_after("2026-09-14"))
        assert reason is None and prior is not None
        assert prior.session_label == "2026-09-11"

    def test_holiday_chain_skipped(self):
        by_label = self._two_day_map()
        prior, _ = select_prior_session(
            by_label, instrument_key="RELIANCE", contract_key=None,
            data_basis=C.DataBasis.RAW_CASH, current_session_label="2026-09-14",
            knowledge_cutoff=cutoff_after("2026-09-14"))
        assert prior is not None and prior.session_label == "2026-09-11"

    def test_partial_session_eligible(self):
        muhurat = (C.TradingIntervalV1(start_local="13:45", end_local="14:45"),)
        cal = live_calendar("2026-10-21", "NSE-CASH-REGULAR-V1",
                            session_type=C.SessionType.SPECIAL, override=muhurat)
        grid = grid_for("2026-10-21", calendar=cal)
        special = build_completed_session(grid, session_bars("2026-10-21", grid),
                                          symbol="RELIANCE", venue_id="NSE",
                                          segment_id="CASH", instrument_type="NSE_EQUITY")
        assert special.completeness is SessionCompleteness.COMPLETE_TRUSTED
        nxt = complete_session("2026-10-22")
        prior, _ = select_prior_session(
            {"2026-10-21": special, "2026-10-22": nxt}, instrument_key="RELIANCE",
            contract_key=None, data_basis=C.DataBasis.RAW_CASH,
            current_session_label="2026-10-22", knowledge_cutoff=cutoff_after("2026-10-22"))
        assert prior is not None and prior.session_label == "2026-10-21"

    def test_mock_session_excluded(self):
        muhurat = (C.TradingIntervalV1(start_local="13:45", end_local="14:45"),)
        cal = live_calendar("2026-09-10", "NSE-CASH-REGULAR-V1",
                            session_type=C.SessionType.MOCK, override=muhurat)
        mock_grid = grid_for("2026-09-10", calendar=cal)
        mock_session = build_completed_session(mock_grid, session_bars("2026-09-10", mock_grid),
                                               symbol="RELIANCE", venue_id="NSE",
                                               segment_id="CASH", instrument_type="NSE_EQUITY")
        assert mock_session.session_type is C.SessionType.MOCK
        nxt = complete_session("2026-09-11")
        prior, _ = select_prior_session(
            {"2026-09-10": mock_session, "2026-09-11": nxt}, instrument_key="RELIANCE",
            contract_key=None, data_basis=C.DataBasis.RAW_CASH,
            current_session_label="2026-09-11", knowledge_cutoff=cutoff_after("2026-09-11"))
        assert prior is None or prior.session_label != "2026-09-10"

    def test_contract_isolation(self):
        front = complete_session("2026-09-10", contract_key="CRUDEOIL-2026-09",
                                 basis=C.DataBasis.RAW_CONTRACT, profile=mcx_profile())
        by_label = {"2026-09-10": front}
        prior, reason = select_prior_session(
            by_label, instrument_key="RELIANCE", contract_key="CRUDEOIL-2026-10",
            data_basis=C.DataBasis.RAW_CONTRACT, current_session_label="2026-09-11",
            knowledge_cutoff=cutoff_after("2026-09-11"))
        assert prior is None and reason == "NO_PRIOR_COMPLETED_SESSION_CAUSALLY_KNOWABLE"

    def test_new_contract_has_no_prior(self):
        listed = complete_session("2026-09-11", contract_key="CRUDEOIL-2026-10",
                                  basis=C.DataBasis.RAW_CONTRACT, profile=mcx_profile())
        snap = build_prior_snapshot(
            instrument_key="RELIANCE", contract_key="CRUDEOIL-2026-10",
            current_session_label="2026-09-11", data_basis=C.DataBasis.RAW_CONTRACT,
            knowledge_cutoff=cutoff_after("2026-09-11"), prior=None,
            unavailable_reason="NO_PRIOR_COMPLETED_SESSION_CAUSALLY_KNOWABLE")
        assert snap.prior_session_found is False
        assert snap.fact("PDH") is not None
        assert snap.fact("PDH").availability is AvailabilityState.UNAVAILABLE
        assert listed.contract_key == "CRUDEOIL-2026-10"

    def test_snapshot_field_availability_and_lineage(self):
        by_label = self._two_day_map()
        prior, _ = select_prior_session(
            by_label, instrument_key="RELIANCE", contract_key=None,
            data_basis=C.DataBasis.RAW_CASH, current_session_label="2026-09-11",
            knowledge_cutoff=cutoff_after("2026-09-11"))
        snap = build_prior_snapshot(
            instrument_key="RELIANCE", contract_key=None, current_session_label="2026-09-11",
            data_basis=C.DataBasis.RAW_CASH, knowledge_cutoff=cutoff_after("2026-09-11"),
            prior=prior, currency="INR")
        assert snap.prior_session_found is True
        assert snap.prior_session_label == "2026-09-10"
        pdh = snap.fact("PDH")
        assert pdh.availability is AvailabilityState.AVAILABLE
        assert pdh.value == pytest.approx(prior.high)
        assert pdh.source_hash == prior.input_content_hash
        assert snap.fact("SESSION_VOLUME").value == pytest.approx(750.0)
        assert snap.fact("DATA_BASIS").value == "RAW_CASH"
        kinds = {ref.reference_type for ref in snap.references}
        assert ReferenceType.SESSION_CLOSE in kinds
        assert ReferenceType.OFFICIAL_DAILY_SETTLEMENT in kinds
        settlement = next(r for r in snap.references
                          if r.reference_type is ReferenceType.OFFICIAL_DAILY_SETTLEMENT)
        assert settlement.availability is AvailabilityState.UNAVAILABLE
        assert snap.snapshot_hash == build_prior_snapshot(
            instrument_key="RELIANCE", contract_key=None, current_session_label="2026-09-11",
            data_basis=C.DataBasis.RAW_CASH, knowledge_cutoff=cutoff_after("2026-09-11"),
            prior=prior, currency="INR").snapshot_hash

    def test_cutoff_excludes_late_available_session(self):
        by_label = self._two_day_map()
        early_cutoff = datetime(2026, 9, 10, 10, 0, tzinfo=UTC)
        prior, reason = select_prior_session(
            by_label, instrument_key="RELIANCE", contract_key=None,
            data_basis=C.DataBasis.RAW_CASH, current_session_label="2026-09-11",
            knowledge_cutoff=early_cutoff)
        assert prior is None and reason is not None

    def test_calculation_receipt_refs_carried(self):
        by_label = self._two_day_map()
        prior, _ = select_prior_session(
            by_label, instrument_key="RELIANCE", contract_key=None,
            data_basis=C.DataBasis.RAW_CASH, current_session_label="2026-09-11",
            knowledge_cutoff=cutoff_after("2026-09-11"))
        ref = OrbCalculationReceiptRefV1(owner="canonical-context", receipt_id="cpr-1",
                                         receipt_hash="e" * 64,
                                         available_at=cutoff_after("2026-09-10"))
        snap = build_prior_snapshot(
            instrument_key="RELIANCE", contract_key=None, current_session_label="2026-09-11",
            data_basis=C.DataBasis.RAW_CASH, knowledge_cutoff=cutoff_after("2026-09-11"),
            prior=prior, calculation_receipt_refs=[ref])
        assert snap.calculation_receipt_refs[0].owner == "canonical-context"


# ------------------------------------------------- precompute / anti-leak (M6)


class TestPrecomputeAntiLeak:
    def _history(self):
        profile = nse_profile()
        labels = ["2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11", "2026-09-14"]
        bars = []
        for li, label in enumerate(labels):
            grid = grid_for(label)
            bars.extend(session_bars(label, grid, start_price=100.0 + li * 10.0))
        return labels, bars, profile

    def test_full_history_sessionize_once(self):
        labels, bars, profile = self._history()
        completed = reconstruct_history(
            bars, instrument_key="RELIANCE", contract_key=None, profile=profile,
            calendars_by_date={}, timeframe="5m", timeframe_duration_ns=NS5,
            data_basis=C.DataBasis.RAW_CASH, source_cadence=SourceCadence.FIXED_INTERVAL_BAR_CADENCE,
            market_as_of=cutoff_after("2026-09-14"), knowledge_cutoff=cutoff_after("2026-09-14"),
            source_id="test", venue_id="NSE", segment_id="CASH", instrument_type="NSE_EQUITY")
        assert sorted(completed) == labels
        assert all(s.completeness is SessionCompleteness.COMPLETE_TRUSTED for s in completed.values())

    def test_holdout_first_date_keeps_d1(self):
        labels, bars, profile = self._history()
        cutoff = cutoff_after("2026-09-14")
        completed = reconstruct_history(
            bars, instrument_key="RELIANCE", contract_key=None, profile=profile,
            calendars_by_date={}, timeframe="5m", timeframe_duration_ns=NS5,
            data_basis=C.DataBasis.RAW_CASH, source_cadence=SourceCadence.FIXED_INTERVAL_BAR_CADENCE,
            market_as_of=cutoff, knowledge_cutoff=cutoff,
            source_id="test", venue_id="NSE", segment_id="CASH", instrument_type="NSE_EQUITY")
        full_map = build_snapshot_map(
            completed, instrument_key="RELIANCE", contract_key=None,
            data_basis=C.DataBasis.RAW_CASH, knowledge_cutoff=cutoff)
        holdout = slice_snapshots(full_map, ["2026-09-11", "2026-09-14"])
        assert holdout["2026-09-11"].prior_session_label == "2026-09-10"
        assert holdout["2026-09-14"].prior_session_label == "2026-09-11"
        # slicing never mutates a frozen snapshot hash
        assert holdout["2026-09-11"].snapshot_hash == full_map["2026-09-11"].snapshot_hash

    def test_same_day_bars_never_enter_d1(self):
        labels, bars, profile = self._history()
        cutoff = cutoff_after("2026-09-14")
        completed = reconstruct_history(
            bars, instrument_key="RELIANCE", contract_key=None, profile=profile,
            calendars_by_date={}, timeframe="5m", timeframe_duration_ns=NS5,
            data_basis=C.DataBasis.RAW_CASH, source_cadence=SourceCadence.FIXED_INTERVAL_BAR_CADENCE,
            market_as_of=cutoff, knowledge_cutoff=cutoff,
            source_id="test", venue_id="NSE", segment_id="CASH", instrument_type="NSE_EQUITY")
        full_map = build_snapshot_map(
            completed, instrument_key="RELIANCE", contract_key=None,
            data_basis=C.DataBasis.RAW_CASH, knowledge_cutoff=cutoff)
        snap = full_map["2026-09-10"]
        assert snap.fact("SESSION_CLOSE").value == pytest.approx(completed["2026-09-09"].close)
        assert snap.prior_session_hash == completed["2026-09-09"].session_hash

    def test_mixed_symbol_stream_rejected(self):
        labels, bars, profile = self._history()
        bars = list(bars)
        bars[0] = bars[0].model_copy(update={"symbol": "TCS"})
        with pytest.raises(ValueError):
            reconstruct_history(
                bars, instrument_key="RELIANCE", contract_key=None, profile=profile,
                calendars_by_date={}, timeframe="5m", timeframe_duration_ns=NS5,
                data_basis=C.DataBasis.RAW_CASH, source_cadence=SourceCadence.FIXED_INTERVAL_BAR_CADENCE,
                market_as_of=cutoff_after("2026-09-14"), knowledge_cutoff=cutoff_after("2026-09-14"),
                source_id="test", venue_id="NSE", segment_id="CASH", instrument_type="NSE_EQUITY")


# ------------------------------------------------------- determinism (M8)


class TestDeterminism:
    def test_replay_stable_across_runs(self):
        first = complete_session("2026-09-10")
        second = complete_session("2026-09-10")
        assert first.session_hash == second.session_hash
        assert first.coverage == second.coverage

    def test_input_order_irrelevant(self):
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        shuffled = bars[::2] + bars[1::2]
        assert (build_completed_session(grid, shuffled, symbol="RELIANCE", venue_id="NSE",
                                        segment_id="CASH", instrument_type="NSE_EQUITY").session_hash
                == build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                           segment_id="CASH", instrument_type="NSE_EQUITY").session_hash)


# --------------------------------------------------------- authority (M8)


class TestAuthority:
    def test_completed_session_rejects_trading_flags(self):
        completed = complete_session("2026-09-10")
        with pytest.raises(ValueError):
            replace(completed, may_execute=True)

    def test_snapshot_rejects_trading_flags(self):
        snap = build_prior_snapshot(
            instrument_key="RELIANCE", contract_key=None, current_session_label="2026-09-10",
            data_basis=C.DataBasis.RAW_CASH, knowledge_cutoff=cutoff_after("2026-09-10"),
            prior=None, unavailable_reason="NO_PRIOR_COMPLETED_SESSION_CAUSALLY_KNOWABLE")
        with pytest.raises(ValueError):
            replace(snap, may_set_final_band=True)

    def test_comparison_receipt_rejects_trading_flags(self):
        completed = complete_session("2026-09-10")
        ref = session_close_reference(completed, currency="INR")
        receipt = compare_references(ref, ref, knowledge_cutoff=datetime(2026, 9, 11, tzinfo=UTC))
        with pytest.raises(ValueError):
            replace(receipt, trade_allowed=True)

    def test_no_signal_fields_on_contracts(self):
        completed = complete_session("2026-09-10")
        for forbidden in ("signal", "direction", "setup", "entry", "stop", "target",
                          "position_size", "bullish", "bearish"):
            assert forbidden not in OrbCompletedSessionV1.__dataclass_fields__


# ------------------------------------------------------------- parity (M7)


class TestParity:
    def test_nse_clean_session_matches_legacy_daily(self):
        pd = pytest.importorskip("pandas")
        from app.orb.context import daily_from_intraday
        grid = grid_for("2026-09-10")
        bars = session_bars("2026-09-10", grid)
        frame = pd.DataFrame(
            [{"open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume}
             for b in bars],
            index=pd.to_datetime([b.timestamp_ns for b in bars], utc=True).tz_convert(IST),
        )
        daily = daily_from_intraday(frame)
        completed = build_completed_session(grid, bars, symbol="RELIANCE", venue_id="NSE",
                                            segment_id="CASH", instrument_type="NSE_EQUITY")
        row = daily.iloc[0]
        assert completed.open == pytest.approx(row["open"])
        assert completed.high == pytest.approx(row["high"])
        assert completed.low == pytest.approx(row["low"])
        assert completed.close == pytest.approx(row["close"])

    def test_cross_midnight_mcX_session_kept_distinct(self):
        profile = mcx_profile()
        grid_a = grid_for("2026-09-10", profile=profile, basis=C.DataBasis.RAW_CONTRACT,
                          contract_key="GOLD-2026-10", timeframe="1H",
                          duration=60 * 60_000_000_000)
        grid_b = grid_for("2026-09-11", profile=profile, basis=C.DataBasis.RAW_CONTRACT,
                          contract_key="GOLD-2026-10", timeframe="1H",
                          duration=60 * 60_000_000_000)
        assert len(grid_a.expected_slot_opens_ns) == 14  # 09:00->23:55, 55m untiled tail
        assert grid_a.untiled_tail_minutes == 55
        evening_ns = utc_ns(date(2026, 9, 10), "22:00")
        assert evening_ns in grid_a.expected_slot_opens_ns
        assert evening_ns not in grid_b.expected_slot_opens_ns
        night = night_profile()
        night_a = grid_for("2026-09-10", profile=night, basis=C.DataBasis.RAW_CONTRACT,
                           contract_key="NIGHT-2026-09", timeframe="1H",
                           duration=60 * 60_000_000_000)
        night_b = grid_for("2026-09-11", profile=night, basis=C.DataBasis.RAW_CONTRACT,
                           contract_key="NIGHT-2026-09", timeframe="1H",
                           duration=60 * 60_000_000_000)
        past_midnight = utc_ns(date(2026, 9, 11), "00:00")
        assert past_midnight in night_a.expected_slot_opens_ns
        assert past_midnight not in night_b.expected_slot_opens_ns
