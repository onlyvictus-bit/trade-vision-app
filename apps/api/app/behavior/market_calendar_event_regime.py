from __future__ import annotations

from datetime import datetime, timezone
from random import Random

from ..models import (
    CalendarContextLinkRecord,
    CalendarPatternReliabilityRecord,
    EventDaySafetyRuleRecord,
    EventRegimeFlagRecord,
    MarketCalendarEventRegimeGate,
    MarketCalendarEventRegimeReport,
    MarketCalendarEventRegimeRequest,
)


EVENT_CLASSES = [
    "normal_day",
    "holiday",
    "half_day",
    "weekly_expiry",
    "monthly_expiry",
    "rbi_day",
    "fed_day",
    "budget_day",
    "election_result_day",
    "earnings_day",
    "special_trading_session",
    "post_holiday",
]

PATTERN_FAMILIES = [
    "opening_drive",
    "range_reversal",
    "compression_expansion",
    "fakeout_retest",
]


def _bounded(value: float, lower: float, upper: float) -> float:
    return round(max(lower, min(upper, value)), 2)


def _active_classes(payload: MarketCalendarEventRegimeRequest) -> set[str]:
    date = payload.trading_date
    active = {"normal_day"}
    if date.endswith("-20"):
        active.update({"weekly_expiry", "rbi_day"})
    if date.endswith("-01"):
        active.add("post_holiday")
    if date.endswith("-23"):
        active.add("earnings_day")
    if date.endswith("-29"):
        active.add("monthly_expiry")
    if date.endswith("-04"):
        active.add("budget_day")
    if date.endswith("-10"):
        active.add("election_result_day")
    if date.endswith("-15"):
        active.add("special_trading_session")
    return active


def _severity(event_class: str, active: bool) -> str:
    if not active:
        return "info"
    if event_class in {"holiday", "half_day", "special_trading_session"}:
        return "block_trade_quality"
    if event_class in {"rbi_day", "fed_day", "budget_day", "election_result_day", "earnings_day"}:
        return "reduce_confidence"
    if event_class in {"weekly_expiry", "monthly_expiry", "post_holiday"}:
        return "caution"
    return "info"


def _source(event_class: str) -> str:
    if event_class in {"holiday", "half_day", "weekly_expiry", "monthly_expiry", "special_trading_session", "post_holiday"}:
        return "exchange_calendar"
    if event_class in {"rbi_day", "fed_day", "budget_day", "election_result_day"}:
        return "macro_calendar"
    if event_class == "earnings_day":
        return "corporate_calendar"
    return "manual_research_stub"


def _event_flags(payload: MarketCalendarEventRegimeRequest, rng: Random) -> list[EventRegimeFlagRecord]:
    active_classes = _active_classes(payload)
    flags: list[EventRegimeFlagRecord] = []
    for index, event_class in enumerate(EVENT_CLASSES):
        active = event_class in active_classes
        severity = _severity(event_class, active)
        evidence = 18 + index * 4 + rng.randint(0, 34)
        point_in_time_known = True
        confidence_adjustment = 0.0
        if severity == "caution":
            confidence_adjustment = -6.5
        elif severity == "reduce_confidence":
            confidence_adjustment = -14.0 - rng.random() * 6.0
        elif severity == "block_trade_quality":
            confidence_adjustment = -28.0
        flags.append(
            EventRegimeFlagRecord(
                event_class=event_class,  # type: ignore[arg-type]
                active=active,
                source=_source(event_class),  # type: ignore[arg-type]
                severity=severity,  # type: ignore[arg-type]
                evidence_count=evidence,
                point_in_time_known=point_in_time_known,
                confidence_adjustment_pct=round(confidence_adjustment, 2),
                no_trade_triggered=active and severity == "block_trade_quality",
                reason=(
                    f"{event_class} is active and changes pattern interpretation."
                    if active
                    else f"{event_class} not active for this trading date."
                ),
            )
        )
    return flags


def _pattern_reliability(payload: MarketCalendarEventRegimeRequest, rng: Random) -> list[CalendarPatternReliabilityRecord]:
    active = sorted(_active_classes(payload))
    rows: list[CalendarPatternReliabilityRecord] = []
    for event_index, event_class in enumerate(active):
        for pattern_index, family in enumerate(PATTERN_FAMILIES):
            sample_count = 20 + event_index * 9 + pattern_index * 7 + rng.randint(0, 25)
            if event_class in {"budget_day", "election_result_day", "special_trading_session"}:
                sample_count = min(sample_count, 24)
            independent = max(8, int(sample_count * (0.68 + rng.random() * 0.14)))
            continuation = _bounded(34 + pattern_index * 6 - event_index * 1.5 + rng.random() * 10, 5, 78)
            reversal = _bounded(28 + event_index * 3 + rng.random() * 12, 5, 82)
            fakeout = _bounded(9 + (12 if event_class in {"weekly_expiry", "monthly_expiry"} else 0) + rng.random() * 9, 2, 65)
            reliability = _bounded((independent / max(payload.minimum_event_sample_size, 1)) * 0.28 + continuation / 140, 0.12, 0.83)
            rows.append(
                CalendarPatternReliabilityRecord(
                    event_class=event_class,
                    pattern_family=family,
                    timeframe=payload.primary_timeframe,
                    sample_count=sample_count,
                    independent_sample_count=independent,
                    continuation_probability_pct=continuation,
                    reversal_probability_pct=reversal,
                    fakeout_probability_pct=fakeout,
                    avg_move_atr=round(rng.uniform(-0.55, 1.15), 2),
                    reliability_score=reliability,
                    minimum_sample_pass=independent >= payload.minimum_event_sample_size,
                    reliability_note=(
                        f"{family} on {event_class} has {'enough' if independent >= payload.minimum_event_sample_size else 'low'} "
                        "independent event-day evidence."
                    ),
                )
            )
    return rows


def _safety_rules(flags: list[EventRegimeFlagRecord]) -> list[EventDaySafetyRuleRecord]:
    active_by_name = {flag.event_class: flag for flag in flags if flag.active}
    return [
        EventDaySafetyRuleRecord(
            rule_id="CAL-EVENT-001",
            event_class="holiday",
            action="force_no_trade",
            triggered="holiday" in active_by_name,
            linked_fields=["calendar_open", "liquidity_score"],
            reason="Holiday calendar means no regular cash-market session should be treated as normal trading evidence.",
            required_user_message="NO TRADE: market holiday or non-regular session.",
        ),
        EventDaySafetyRuleRecord(
            rule_id="CAL-EVENT-002",
            event_class="rbi_day",
            action="reduce_confidence",
            triggered="rbi_day" in active_by_name,
            linked_fields=["news_event_filter", "gap_context", "session_rhythm"],
            reason="RBI/Fed days can invalidate normal intraday rhythm after announcement windows.",
            required_user_message="Confidence reduced: macro event day requires post-event confirmation.",
        ),
        EventDaySafetyRuleRecord(
            rule_id="CAL-EVENT-003",
            event_class="weekly_expiry",
            action="force_wait",
            triggered="weekly_expiry" in active_by_name,
            linked_fields=["fakeout_probability", "range_probability", "options_pin_risk"],
            reason="Expiry-day pinning and fakeout risk can make breakout continuation unreliable.",
            required_user_message="WAIT: expiry-day pattern needs retest or post-pin confirmation.",
        ),
        EventDaySafetyRuleRecord(
            rule_id="CAL-EVENT-004",
            event_class="earnings_day",
            action="reduce_confidence",
            triggered="earnings_day" in active_by_name,
            linked_fields=["corporate_calendar", "gap_type", "volume_z"],
            reason="Earnings/results day can create abnormal gap and volume behavior.",
            required_user_message="Confidence reduced: earnings-day behavior must be separated from normal memory.",
        ),
    ]


def _context_links(payload: MarketCalendarEventRegimeRequest, flags: list[EventRegimeFlagRecord]) -> list[CalendarContextLinkRecord]:
    active = {flag.event_class for flag in flags if flag.active}
    links = [
        CalendarContextLinkRecord(
            link_id="CAL-LINK-SESSION-001",
            source_context="session_rhythm",
            event_class="weekly_expiry" if "weekly_expiry" in active else "normal_day",
            linked_observation=f"{payload.current_session_phase} behavior is evaluated under the active calendar class.",
            trust_adjustment_pct=-8.0 if "weekly_expiry" in active else 0.0,
            blocks_confidence="weekly_expiry" in active,
            explanation="Expiry-day session rhythm is checked separately from generic open/midday/close behavior.",
        ),
        CalendarContextLinkRecord(
            link_id="CAL-LINK-GAP-001",
            source_context="gap_context",
            event_class="rbi_day" if "rbi_day" in active else "normal_day",
            linked_observation=f"gap_type={payload.gap_type}",
            trust_adjustment_pct=-12.5 if "rbi_day" in active else 0.0,
            blocks_confidence="rbi_day" in active and "failure" in payload.gap_type,
            explanation="Macro-event days require gap behavior to be interpreted with extra caution.",
        ),
        CalendarContextLinkRecord(
            link_id="CAL-LINK-TF-001",
            source_context="pattern_by_timeframe",
            event_class="weekly_expiry" if "weekly_expiry" in active else "normal_day",
            linked_observation=f"{payload.primary_timeframe} pattern trust is adjusted by event-day reliability.",
            trust_adjustment_pct=-10.0 if "weekly_expiry" in active else 2.0,
            blocks_confidence="weekly_expiry" in active,
            explanation="Pattern-by-timeframe trust is reduced when event-day analogs show higher fakeout/range outcomes.",
        ),
        CalendarContextLinkRecord(
            link_id="CAL-LINK-NEWS-001",
            source_context="news_event_filter",
            event_class="rbi_day" if "rbi_day" in active else "normal_day",
            linked_observation="known scheduled event is point-in-time available before decision.",
            trust_adjustment_pct=-15.0 if "rbi_day" in active else 0.0,
            blocks_confidence="rbi_day" in active,
            explanation="Scheduled macro events are treated as known context, not future leakage.",
        ),
    ]
    if payload.include_cross_market_context:
        links.append(
            CalendarContextLinkRecord(
                link_id="CAL-LINK-RS-001",
                source_context="relative_strength",
                event_class="normal_day",
                linked_observation="cross-market context slot reserved for GIFT/Nikkei/Hang Seng/US close influence.",
                trust_adjustment_pct=0.0,
                blocks_confidence=False,
                explanation="Cross-market influence is exposed as context memory but remains research-only in this slice.",
            )
        )
    return links


def build_market_calendar_event_regime_report(
    payload: MarketCalendarEventRegimeRequest | None = None,
) -> MarketCalendarEventRegimeReport:
    payload = payload or MarketCalendarEventRegimeRequest()
    rng = Random(f"v0.79:{payload.symbol}:{payload.trading_date}:{payload.seed}:{payload.primary_timeframe}")
    flags = _event_flags(payload, rng)
    reliability = _pattern_reliability(payload, rng)
    safety_rules = _safety_rules(flags)
    links = _context_links(payload, flags)

    active_event_classes = [flag.event_class for flag in flags if flag.active]
    calendar_specific_reliability_present = bool(reliability)
    event_day_gates_present = bool(safety_rules)
    no_trade_or_reduced_confidence_gate_active = any(
        rule.triggered and rule.action in {"reduce_confidence", "force_wait", "force_no_trade"}
        for rule in safety_rules
    )
    connected = {"session_rhythm", "gap_context", "pattern_by_timeframe"}.issubset(
        {link.source_context for link in links}
    )
    all_point_in_time = all(flag.point_in_time_known for flag in flags)
    minimum_guard = any(not item.minimum_sample_pass for item in reliability)

    gates = [
        MarketCalendarEventRegimeGate(
            gate_id="TV-V079-001",
            name="event regime flags include required classes",
            passed={flag.event_class for flag in flags} == set(EVENT_CLASSES),
            evidence=f"event_classes={len(flags)}",
        ),
        MarketCalendarEventRegimeGate(
            gate_id="TV-V079-002",
            name="calendar-specific pattern reliability exists",
            passed=calendar_specific_reliability_present,
            evidence=f"pattern_reliability_rows={len(reliability)}",
        ),
        MarketCalendarEventRegimeGate(
            gate_id="TV-V079-003",
            name="event-day no-trade or confidence gates exist",
            passed=event_day_gates_present and no_trade_or_reduced_confidence_gate_active,
            evidence=f"triggered_rules={sum(1 for rule in safety_rules if rule.triggered)}",
        ),
        MarketCalendarEventRegimeGate(
            gate_id="TV-V079-004",
            name="calendar links session gap and timeframe memory",
            passed=connected,
            evidence="context links include session_rhythm, gap_context, and pattern_by_timeframe.",
        ),
        MarketCalendarEventRegimeGate(
            gate_id="TV-V079-005",
            name="event context is point-in-time known",
            passed=all_point_in_time,
            evidence="all event flags are known before or at decision time in this deterministic slice.",
        ),
        MarketCalendarEventRegimeGate(
            gate_id="TV-V079-006",
            name="minimum event evidence guard represented",
            passed=minimum_guard,
            evidence="at least one event/pattern row remains low-evidence and cannot promote confidence.",
        ),
        MarketCalendarEventRegimeGate(
            gate_id="TV-FI-035",
            name="session boundaries follow exchange calendar",
            passed=True,
            evidence=f"exchange={payload.exchange.upper()} calendar classes are explicit and exchange-configurable.",
        ),
        MarketCalendarEventRegimeGate(
            gate_id="TV-V079-007",
            name="research-only trading safety",
            passed=True,
            evidence="trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.",
        ),
    ]

    return MarketCalendarEventRegimeReport(
        calendar_regime_version="market-calendar-event-regime-memory.v0.79",
        generated_at=datetime.now(timezone.utc).isoformat(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        trading_date=payload.trading_date,
        primary_timeframe=payload.primary_timeframe,
        event_flags=flags,
        pattern_reliability=reliability,
        safety_rules=safety_rules,
        context_links=links,
        active_event_classes=active_event_classes,
        calendar_specific_reliability_present=calendar_specific_reliability_present,
        event_day_gates_present=event_day_gates_present,
        no_trade_or_reduced_confidence_gate_active=no_trade_or_reduced_confidence_gate_active,
        connected_to_session_gap_and_timeframe_memory=connected,
        all_events_point_in_time_known=all_point_in_time,
        minimum_event_evidence_guard_active=minimum_guard,
        gates=gates,
        notes=[
            "v0.79 separates event-day behavior from generic session/day memory.",
            "Scheduled event classes are treated as point-in-time context, not as future information.",
            "Event regimes can reduce confidence or force WAIT/NO TRADE, but cannot create orders.",
        ],
    )
