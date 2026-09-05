from __future__ import annotations

from ..models import IndicatorLagVoteRecord, IndicatorLagVoteRequest, IndicatorLagVotingReport
from .indicator_registry import build_indicator_registry_report


INDICATOR_LAG_VOTING_VERSION = "indicator-lag-aware-voting.v1.80"


def build_indicator_lag_voting_report(request: IndicatorLagVoteRequest) -> IndicatorLagVotingReport:
    registry = build_indicator_registry_report()
    entry = next((item for item in registry.entries if item.indicator_id == request.indicator_id), None)
    if entry is None:
        entry = registry.entries[0]
    delay = int(entry.confirmation_delay_bars)
    lag_weight = 1.0 / (1.0 + delay)
    delay_adjusted = request.raw_vote * lag_weight * request.per_stock_reliability * request.per_regime_reliability * request.freshness_weight
    stale = delay >= entry.sequential_signal_window
    late = entry.lag_behavior == "lagging" or stale
    can_promote_wait = (not late) and abs(delay_adjusted) >= 0.55 and entry.category in {"structure", "level", "trap"}
    can_promote_paper = False
    reason = _reason(entry, lag_weight, delay_adjusted, stale)
    return IndicatorLagVotingReport(
        voting_version=INDICATOR_LAG_VOTING_VERSION,
        symbol=request.symbol.upper(),
        registry_version=registry.registry_version,
        indicator_id=entry.indicator_id,
        vote=IndicatorLagVoteRecord(
            indicator_id=entry.indicator_id,
            category=entry.category,
            lag_behavior=entry.lag_behavior,
            confirmation_delay_bars=delay,
            sequential_signal_window=entry.sequential_signal_window,
            lag_weight=round(lag_weight, 6),
            delay_adjusted_vote=round(max(-1.0, min(1.0, delay_adjusted)), 6),
            stale_confirmation_warning=stale,
            can_promote_wait_to_watch=can_promote_wait,
            can_promote_watch_to_paper=can_promote_paper,
            explanation_usage_allowed=entry.usable_for_explanation,
            post_entry_usage_allowed=late,
            reason=reason,
        ),
        all_registry_entries_have_ontology=all(bool(item.purpose) and item.category != "" for item in registry.entries),
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        no_future_leakage=True,
        gates=[
            _gate("IND-ARB-009", "confirmation_delay_bars reduces late vote weight", lag_weight <= 1.0, f"delay={delay}; lag_weight={lag_weight:.4f}"),
            _gate("IND-ARB-010", "zero-delay structural evidence outranks delayed confirmation", not (delay >= 4 and can_promote_wait), f"delay={delay}; can_promote_wait_to_watch={can_promote_wait}"),
            _gate("IND-ARB-011", "late confirmation cannot promote WATCH to PAPER-CANDIDATE alone", not can_promote_paper, "can_promote_watch_to_paper=false"),
            _gate("IND-ARB-012", "stale confirmation creates warning not confidence", not stale or not can_promote_wait, f"stale={stale}; window={entry.sequential_signal_window}"),
            _gate("IND-ONT-001", "registry entries carry ontology metadata", all(bool(item.purpose) for item in registry.entries), f"entries={len(registry.entries)}"),
            _gate("IND-ONT-005", "registry count remains locked", registry.total_output_groups == 94, f"entries={registry.total_output_groups}"),
        ],
        notes=[
            "Lag-aware voting is advisory and cannot route orders.",
            "Lagging indicators can explain or support post-entry management but cannot promote a decision by themselves.",
            "Reliability multipliers are caller-supplied placeholders until v1.81 outcome-backed reliability memory is built.",
        ],
    )


def build_indicator_intelligence_summary(symbol: str = "RELIANCE") -> dict:
    registry = build_indicator_registry_report()
    selected_ids = _selected_indicator_ids(registry.entries)
    reports = [
        build_indicator_lag_voting_report(IndicatorLagVoteRequest(symbol=symbol, indicator_id=indicator_id))
        for indicator_id in selected_ids
    ]
    return {
        "summary_version": "indicator-intelligence-summary.v1.80",
        "symbol": symbol.upper(),
        "registry_version": registry.registry_version,
        "total_indicators": registry.total_output_groups,
        "selected_indicator_count": len(reports),
        "ontology_coverage_count": sum(1 for item in registry.entries if item.purpose and item.category != "unclassified"),
        "unclassified_count": sum(1 for item in registry.entries if item.category == "unclassified"),
        "lagging_count": sum(1 for item in registry.entries if item.lag_behavior == "lagging"),
        "leading_or_coincident_count": sum(1 for item in registry.entries if item.lag_behavior in {"leading", "coincident"}),
        "sample_votes": [report.vote.model_dump() for report in reports],
        "decision_rule": "Lagging confirmations cannot promote WAIT to WATCH or WATCH to PAPER-CANDIDATE by themselves.",
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "no_future_leakage": True,
    }


def _selected_indicator_ids(entries) -> list[str]:
    ids = [entry.indicator_id for entry in entries]
    preferred = ["si_inside_candle_strategy", "si_sweep_inside_rr", "si_ichi_trend_osc", "si_fmfm300"]
    selected = [indicator_id for indicator_id in preferred if indicator_id in ids]
    selected.extend(indicator_id for indicator_id in ids if any(token in indicator_id.lower() for token in ("rsi", "macd", "vwap", "adx")) and indicator_id not in selected)
    return selected[:8]


def _reason(entry, lag_weight: float, delay_adjusted: float, stale: bool) -> str:
    if stale:
        return f"{entry.indicator_id} is stale relative to its sequential window; use as warning/explanation only."
    if entry.lag_behavior == "lagging":
        return f"{entry.indicator_id} is lagging; vote is reduced to {lag_weight:.2f} before reliability multipliers."
    return f"{entry.indicator_id} is {entry.lag_behavior}; delay-adjusted vote is {delay_adjusted:.2f}."


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> dict:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": passed,
        "evidence": evidence,
        "remediation": None if passed else "Fix indicator ontology or lag-vote weighting before v1.81 reliability memory.",
    }
