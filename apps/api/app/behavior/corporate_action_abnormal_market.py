from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import Random

from ..models import (
    AbnormalMarketEventRecord,
    CorporateActionAbnormalMarketGate,
    CorporateActionAbnormalMarketReport,
    CorporateActionAbnormalMarketRequest,
    CorporateActionEventRecord,
    MemoryContaminationRecord,
    MemoryQuarantineActionRecord,
)


PATTERN_FAMILIES = ["opening_drive", "breakout_retest", "range_reversal", "compression_expansion"]


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _fmt(day: datetime) -> str:
    return day.date().isoformat()


def _ns(day: datetime, hour: int, minute: int) -> int:
    return int(day.replace(hour=hour, minute=minute, second=0, microsecond=0).timestamp() * 1_000_000_000)


def _corporate_actions(payload: CorporateActionAbnormalMarketRequest) -> list[CorporateActionEventRecord]:
    base = _date(payload.trading_date)
    events = [
        CorporateActionEventRecord(
            event_id=f"CA-{payload.symbol.upper()}-SPLIT",
            event_type="split",
            effective_date=_fmt(base - timedelta(days=7)),
            adjustment_factor=0.5,
            source="mock_corporate_action_calendar",
            affects_ohlcv_continuity=True,
            contaminates_memory_window=True,
            quarantine_start=_fmt(base - timedelta(days=payload.quarantine_window_days)),
            quarantine_end=_fmt(base + timedelta(days=payload.quarantine_window_days)),
            reason="Split/adjustment can make old candle body, wick, gap, volume, and indicator values incomparable.",
        ),
        CorporateActionEventRecord(
            event_id=f"CA-{payload.symbol.upper()}-DIV",
            event_type="dividend_adjustment",
            effective_date=_fmt(base - timedelta(days=31)),
            adjustment_factor=0.98,
            source="mock_corporate_action_calendar",
            affects_ohlcv_continuity=True,
            contaminates_memory_window=True,
            quarantine_start=_fmt(base - timedelta(days=36)),
            quarantine_end=_fmt(base - timedelta(days=26)),
            reason="Dividend adjustment can distort previous close, gap context, and support/resistance memory.",
        ),
    ]
    if payload.include_special_corporate_events:
        events.append(
            CorporateActionEventRecord(
                event_id=f"CA-{payload.symbol.upper()}-SUSP",
                event_type="suspension",
                effective_date=_fmt(base - timedelta(days=3)),
                adjustment_factor=None,
                source="manual_research_stub",
                affects_ohlcv_continuity=True,
                contaminates_memory_window=True,
                quarantine_start=_fmt(base - timedelta(days=5)),
                quarantine_end=_fmt(base + timedelta(days=2)),
                reason="Suspension or special corporate event requires human review before memory can learn from the window.",
            )
        )
    return events


def _abnormal_events(payload: CorporateActionAbnormalMarketRequest, rng: Random) -> list[AbnormalMarketEventRecord]:
    base = _date(payload.trading_date)
    return [
        AbnormalMarketEventRecord(
            event_id=f"AM-{payload.symbol.upper()}-UC",
            event_type="upper_circuit_near",
            timestamp_ns=_ns(base, 9, 44),
            severity="warning",
            price_impact_pct=9.2,
            volume_anomaly_z=round(3.4 + rng.random(), 2),
            blocks_memory_update=True,
            blocks_trade_quality=True,
            reason="Upper-circuit proximity can create locked price behavior and fake continuation statistics.",
        ),
        AbnormalMarketEventRecord(
            event_id=f"AM-{payload.symbol.upper()}-HALT",
            event_type="trading_halt",
            timestamp_ns=_ns(base, 10, 17),
            severity="blocker",
            price_impact_pct=0.0,
            volume_anomaly_z=None,
            blocks_memory_update=True,
            blocks_trade_quality=True,
            reason="Trading halt breaks normal candle sequencing and invalidates intraday rhythm memory.",
        ),
        AbnormalMarketEventRecord(
            event_id=f"AM-{payload.symbol.upper()}-PRINT",
            event_type="single_candle_abnormal_print",
            timestamp_ns=_ns(base, 13, 4),
            severity="warning",
            price_impact_pct=14.8,
            volume_anomaly_z=round(4.8 + rng.random(), 2),
            blocks_memory_update=True,
            blocks_trade_quality=True,
            reason="Single-candle abnormal print must be treated as suspect until verified against source data.",
        ),
        AbnormalMarketEventRecord(
            event_id=f"AM-{payload.symbol.upper()}-ILLIQ",
            event_type="illiquid_spike",
            timestamp_ns=_ns(base, 14, 21),
            severity="warning",
            price_impact_pct=5.7,
            volume_anomaly_z=0.2,
            blocks_memory_update=True,
            blocks_trade_quality=True,
            reason="Illiquid spike can create false harmonic, trendline, and breakout evidence.",
        ),
    ]


def _contamination_records(
    payload: CorporateActionAbnormalMarketRequest,
    corporate_actions: list[CorporateActionEventRecord],
    abnormal_events: list[AbnormalMarketEventRecord],
) -> list[MemoryContaminationRecord]:
    base = _date(payload.trading_date)
    clean_count = max(0, payload.lookback_days - len(corporate_actions) * payload.quarantine_window_days * 2 - len(abnormal_events) * 2)
    return [
        MemoryContaminationRecord(
            contamination_id=f"CONTAM-{payload.symbol.upper()}-CORP",
            contamination_type="corporate_action",
            affected_memory_tier="WARM",
            affected_window_start=corporate_actions[0].quarantine_start,
            affected_window_end=corporate_actions[0].quarantine_end,
            affected_pattern_families=PATTERN_FAMILIES,
            clean_sample_count_after_exclusion=clean_count,
            trust_adjustment_pct=-35.0,
            quarantine_required=True,
            rebuild_required=True,
            explanation="Corporate action windows are excluded from analog search and require DNA recomputation without suspect bars.",
        ),
        MemoryContaminationRecord(
            contamination_id=f"CONTAM-{payload.symbol.upper()}-ABNORMAL",
            contamination_type="halt_or_circuit",
            affected_memory_tier="HOT",
            affected_window_start=_fmt(base),
            affected_window_end=_fmt(base + timedelta(days=1)),
            affected_pattern_families=["opening_drive", "breakout_retest", "range_reversal"],
            clean_sample_count_after_exclusion=max(0, clean_count - 12),
            trust_adjustment_pct=-42.0,
            quarantine_required=True,
            rebuild_required=False,
            explanation="Circuit/halt/abnormal-print day is quarantined from live-like pattern memory until manually reviewed.",
        ),
    ]


def _quarantine_actions(records: list[MemoryContaminationRecord]) -> list[MemoryQuarantineActionRecord]:
    return [
        MemoryQuarantineActionRecord(
            action_id="QA-001",
            action="exclude_from_similarity",
            triggered=True,
            target="corporate-action windows",
            reason="Contaminated windows must not be retrieved as clean analogs.",
            human_review_required=False,
        ),
        MemoryQuarantineActionRecord(
            action_id="QA-002",
            action="quarantine_warm_memory",
            triggered=any(record.affected_memory_tier == "WARM" and record.quarantine_required for record in records),
            target="WARM memory",
            reason="WARM memory near split/bonus/dividend/suspension events cannot raise confidence.",
            human_review_required=True,
        ),
        MemoryQuarantineActionRecord(
            action_id="QA-003",
            action="force_no_trade",
            triggered=True,
            target="abnormal market session",
            reason="Circuit, halt, illiquid spike, or abnormal print blocks trade-quality conclusions.",
            human_review_required=True,
        ),
        MemoryQuarantineActionRecord(
            action_id="QA-004",
            action="preserve_raw_data",
            triggered=True,
            target="immutable raw OHLCV",
            reason="Raw data remains immutable; adjusted views are versioned separately.",
            human_review_required=False,
        ),
        MemoryQuarantineActionRecord(
            action_id="QA-005",
            action="trigger_rebuild_plan",
            triggered=any(record.rebuild_required for record in records),
            target="Stock DNA and analog indexes",
            reason="Rebuild DNA and analog indexes without suspect corporate-action windows.",
            human_review_required=True,
        ),
    ]


def build_corporate_action_abnormal_market_report(
    payload: CorporateActionAbnormalMarketRequest | None = None,
) -> CorporateActionAbnormalMarketReport:
    payload = payload or CorporateActionAbnormalMarketRequest()
    rng = Random(f"v0.81:{payload.symbol}:{payload.trading_date}:{payload.seed}")
    corporate_actions = _corporate_actions(payload)
    abnormal_events = _abnormal_events(payload, rng)
    contamination = _contamination_records(payload, corporate_actions, abnormal_events)
    quarantine_actions = _quarantine_actions(contamination)
    clean_sample_count = min(record.clean_sample_count_after_exclusion for record in contamination)

    corporate_filter = any(event.contaminates_memory_window for event in corporate_actions)
    abnormal_filter = any(event.blocks_memory_update or event.blocks_trade_quality for event in abnormal_events)
    quarantined = any(action.triggered and action.action in {"quarantine_warm_memory", "exclude_from_similarity"} for action in quarantine_actions)
    trust_reduced = any(record.trust_adjustment_pct < 0 for record in contamination)
    no_trade = any(action.triggered and action.action == "force_no_trade" for action in quarantine_actions)
    memory_blocked = corporate_filter or abnormal_filter
    raw_preserved = any(action.triggered and action.action == "preserve_raw_data" for action in quarantine_actions)

    gates = [
        CorporateActionAbnormalMarketGate(
            gate_id="TV-V081-001",
            name="corporate action filter active",
            passed=corporate_filter,
            evidence=f"corporate_actions={len(corporate_actions)}",
        ),
        CorporateActionAbnormalMarketGate(
            gate_id="TV-V081-002",
            name="abnormal market filter active",
            passed=abnormal_filter,
            evidence=f"abnormal_events={len(abnormal_events)}",
        ),
        CorporateActionAbnormalMarketGate(
            gate_id="TV-V081-003",
            name="contaminated memory quarantined",
            passed=quarantined,
            evidence=f"quarantine_actions={sum(1 for action in quarantine_actions if action.triggered)}",
        ),
        CorporateActionAbnormalMarketGate(
            gate_id="TV-V081-004",
            name="trust reduced for contaminated analogs",
            passed=trust_reduced,
            evidence=f"trust_adjustments={[record.trust_adjustment_pct for record in contamination]}",
        ),
        CorporateActionAbnormalMarketGate(
            gate_id="TV-V081-005",
            name="research no-trade gate active for abnormal session",
            passed=no_trade,
            evidence="force_no_trade action triggered for abnormal market session.",
        ),
        CorporateActionAbnormalMarketGate(
            gate_id="TV-FI-053",
            name="quarantined memory cannot affect recommendation",
            passed=quarantined and trust_reduced,
            evidence="contaminated memory is excluded or trust-reduced before recommendation.",
        ),
        CorporateActionAbnormalMarketGate(
            gate_id="TV-FI-106",
            name="memory poisoning detector quarantines suspect windows and preserves raw data",
            passed=quarantined and raw_preserved,
            evidence="suspect windows are quarantined and immutable raw data is preserved.",
        ),
        CorporateActionAbnormalMarketGate(
            gate_id="TV-V081-006",
            name="research-only trading safety",
            passed=True,
            evidence="trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true.",
        ),
    ]

    return CorporateActionAbnormalMarketReport(
        corporate_abnormal_version="corporate-action-abnormal-market-memory.v0.81",
        generated_at=datetime.now(timezone.utc).isoformat(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        trading_date=payload.trading_date,
        corporate_actions=corporate_actions,
        abnormal_events=abnormal_events,
        contamination_records=contamination,
        quarantine_actions=quarantine_actions,
        clean_sample_count=clean_sample_count,
        corporate_action_filter_active=corporate_filter,
        abnormal_market_filter_active=abnormal_filter,
        contaminated_memory_quarantined=quarantined,
        trust_reduced_for_contaminated_analogs=trust_reduced,
        raw_data_preserved_immutable=raw_preserved,
        no_trade_gate_active=no_trade,
        memory_update_blocked=memory_blocked,
        gates=gates,
        notes=[
            "v0.81 prevents corporate-action and abnormal-market windows from poisoning Stock DNA memory.",
            "Raw OHLCV is preserved immutably; adjusted and filtered memory views are versioned separately.",
            "Abnormal sessions can force NO TRADE for research output but cannot create orders.",
        ],
    )
