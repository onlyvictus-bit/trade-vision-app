"""NSE legacy compatibility adapter + shadow parity (BUILD-2E).

The legacy NSE engine (`orb/core.py`, `OrbSessionDefinition`) is a valid
NSE-only fact: fixed +330 offset, 09:15 <= HH:MM < 15:30 membership, civil
local-date session label. This module preserves that behavior behind named
LEGACY_* constants (approved legacy exception, see the anti-regression
inventory) and proves canonical equivalence for clean normal sessions via
shadow comparison. Intentional divergences are recorded with legacy and
canonical values, never silently substituted. Active ORB behavior is
unchanged by this module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from . import session as session_math
from .contracts import (
    ORB_SESSION_VERSION,
    AvailabilityState,
    CalendarRecordV1,
    SessionPhase,
    SessionProfileV1,
    SessionType,
    TradingIntervalV1,
    session_record,
)

# Approved legacy exception (BUILD-2 anti-regression inventory): exact
# replication of orb/core.py fixed-offset NSE session semantics.
LEGACY_NSE_OFFSET_MINUTES = 330
LEGACY_NSE_OPEN = "09:15"
LEGACY_NSE_CLOSE = "15:30"
LEGACY_NSE_TIMEZONE = "Asia/Kolkata"
LEGACY_NSE_VENUE_ID = "NSE"
LEGACY_NSE_SEGMENT = "CASH"


def legacy_nse_local(timestamp_ns: int) -> datetime:
    """core.py _local_datetime: UTC plus fixed offset (naive arithmetic)."""
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc) + timedelta(
        minutes=LEGACY_NSE_OFFSET_MINUTES
    )


def legacy_nse_in_session(timestamp_ns: int) -> bool:
    """core.py _in_session: start <= HH:MM < end string comparison."""
    hhmm = legacy_nse_local(timestamp_ns).strftime("%H:%M")
    return LEGACY_NSE_OPEN <= hhmm < LEGACY_NSE_CLOSE


def legacy_nse_session_label(timestamp_ns: int) -> str:
    """core.py local_session_date: civil local date of the bar."""
    return str(legacy_nse_local(timestamp_ns).date())


def nse_canonical_profile(
    *,
    profile_id: str = "NSE-CASH-REGULAR-V1",
    source_receipt_ids: Sequence[str] = (),
) -> SessionProfileV1:
    """Canonical session profile reproducing valid legacy NSE grouping."""
    return session_record(
        profile_id=profile_id,
        venue_id=LEGACY_NSE_VENUE_ID,
        segment_scope=LEGACY_NSE_SEGMENT,
        timezone_name=LEGACY_NSE_TIMEZONE,
        trading_date_convention="EXCHANGE_SESSION_LABEL_EQUALS_LOCAL_DATE_FOR_SAME_DAY_SESSIONS",
        session_type=SessionType.REGULAR,
        opening_anchor_local=LEGACY_NSE_OPEN,
        tradable_intervals=[
            TradingIntervalV1(start_local=LEGACY_NSE_OPEN, end_local=LEGACY_NSE_CLOSE, phase=SessionPhase.REGULAR)
        ],
        trading_phases=(SessionPhase.PRE_OPEN, SessionPhase.REGULAR, SessionPhase.POST_CLOSE, SessionPhase.CLOSED),
        close_semantics="LAST_TRADED_PRICE_AT_15_30_IST",
        settlement_semantics="UNSPECIFIED_FOR_EQUITY_CASH",
        source_receipt_ids=tuple(source_receipt_ids),
    )


def canonical_nse_membership(
    timestamp_ns: int,
    profile: SessionProfileV1,
    calendar: CalendarRecordV1 | None = None,
) -> Mapping[str, Any]:
    moment = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc)
    return session_math.locate_timestamp(profile, moment, calendar)


def shadow_compare_nse(
    timestamps_ns: Sequence[int],
    profile: SessionProfileV1,
    calendar: CalendarRecordV1 | None = None,
) -> Mapping[str, Any]:
    """Compare legacy vs canonical NSE session grouping over timestamps.

    Returns a receipt: parity flag plus per-timestamp divergence records
    with LEGACY_VALUE / CANONICAL_VALUE / difference reason / safety
    implication / migration state. Never alters active behavior.
    """
    divergences: list[dict[str, Any]] = []
    for timestamp_ns in timestamps_ns:
        legacy_member = legacy_nse_in_session(timestamp_ns)
        legacy_label = legacy_nse_session_label(timestamp_ns) if legacy_member else ""
        located = canonical_nse_membership(timestamp_ns, profile, calendar)
        canonical_member = bool(located["in_session"])
        canonical_label = str(located["session_label"] or "")
        if legacy_member != canonical_member:
            divergences.append(
                {
                    "timestamp_ns": timestamp_ns,
                    "kind": "LEGACY_ONLY" if legacy_member else "CANONICAL_ONLY",
                    "legacy_value": {"in_session": legacy_member, "label": legacy_label},
                    "canonical_value": {"in_session": canonical_member, "label": canonical_label},
                    "difference_reason": "calendar override or mock/holiday session" if calendar else "unexpected",
                    "safety_implication": "canonical uncertainty preserved; legacy output drives active runs",
                    "migration_state": "SHADOW",
                }
            )
        elif legacy_member and legacy_label != canonical_label:
            divergences.append(
                {
                    "timestamp_ns": timestamp_ns,
                    "kind": "SEMANTIC_DIVERGENCE",
                    "legacy_value": {"label": legacy_label},
                    "canonical_value": {"label": canonical_label},
                    "difference_reason": "session-label convention differs",
                    "safety_implication": "downstream session grouping could shift; kept on legacy",
                    "migration_state": "SHADOW",
                }
            )
    return {
        "shadow_version": "orb-nse-shadow.v1",
        "compared": len(list(timestamps_ns)),
        "parity": not divergences,
        "divergences": divergences,
        "migration_state": "SHADOW",
    }
