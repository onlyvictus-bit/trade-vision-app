from __future__ import annotations

from ..models import (
    FinalConfluenceArbiterGate,
    FinalConfluenceArbiterReport,
    FinalConfluenceArbiterRequest,
    FinalConfluenceConflict,
    FinalConfluenceVote,
)


FINAL_CONFLUENCE_ARBITER_VERSION = "final-confluence-conflict-arbiter.v1.75"
EVIDENCE_HIERARCHY = [
    "risk/safety",
    "data quality",
    "liquidity",
    "market regime",
    "structure/levels",
    "volume/auction",
    "relative strength",
    "indicators",
    "external AI explanation",
]


def build_final_confluence_arbiter_report(request: FinalConfluenceArbiterRequest) -> FinalConfluenceArbiterReport:
    votes = _votes(request)
    conflicts = _conflicts(request, votes)
    adjustment = sum(conflict.score_adjustment for conflict in conflicts)
    raw_score = sum(vote.weighted_score for vote in votes) + adjustment
    hard_block = _hard_block(request, conflicts)
    confluence_score = _bounded_score(raw_score)
    decision_band, final_decision = _decision(confluence_score, request, hard_block)
    dominant_blocker = _dominant_blocker(request, conflicts)
    interval = _confidence_interval(confluence_score, request, conflicts)
    reason_tree = _reason_tree(request, votes, conflicts, final_decision, dominant_blocker)
    gates = _gates(request, votes, conflicts, final_decision)
    return FinalConfluenceArbiterReport(
        arbiter_version=FINAL_CONFLUENCE_ARBITER_VERSION,
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        direction=request.direction,
        evidence_hierarchy=EVIDENCE_HIERARCHY,
        confluence_score=confluence_score,
        raw_score=round(raw_score, 6),
        evidence_votes=votes,
        conflicts_detected=conflicts,
        dominant_blocker=dominant_blocker,
        decision_band=decision_band,  # type: ignore[arg-type]
        confidence_interval=interval,
        final_decision=final_decision,  # type: ignore[arg-type]
        human_reason_tree=reason_tree,
        no_future_leakage=request.no_future_leakage,
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        reasons=_reasons(final_decision, dominant_blocker, confluence_score),
        failure_questions=_failure_questions(request),
        gates=gates,
    )


def _votes(request: FinalConfluenceArbiterRequest) -> list[FinalConfluenceVote]:
    liquidity_score = {"A": 0.80, "B": 0.25, "C": -1.0, "UNKNOWN": -0.20}[request.liquidity_grade]
    data_quality_score = 0.65 if request.data_quality_pass and request.no_future_leakage else -1.0
    risk_score = _risk_score(request)
    post_entry_score = _post_entry_score(request.post_entry_thesis_status)
    vote_specs = [
        ("risk_safety", risk_score, 1, 1.70, _risk_reason(request)),
        ("data_quality", data_quality_score, 2, 1.45, "Data quality and causal/PIT state must pass before any lower-priority vote can matter."),
        ("liquidity", liquidity_score, 3, 1.35, f"Liquidity grade is {request.liquidity_grade}; grade C blocks candidate promotion."),
        ("market_regime", request.market_regime_score, 4, 1.15, "Market regime/breadth/feedback controls whether the stock is fighting or following the tape."),
        ("structure_levels", request.structure_score, 5, 1.10, "Structure, level, auction, and resistance context outrank standalone indicator agreement."),
        ("volume_auction", request.volume_auction_score, 6, 0.90, "Volume profile, VSA, and auction acceptance confirm or reject structural movement."),
        ("relative_strength", request.relative_strength_score * 2.0 - 1.0, 7, 0.80, "Relative strength checks whether the stock leads or lags its index/sector."),
        ("indicators", request.indicator_signal_score, 8, 0.50, "Indicators support explanation but cannot overrule structure, liquidity, trap, or safety evidence."),
        ("external_ai", request.external_ai_score, 9, 0.30, "External AI explanation is reviewer-only and cannot approve a trade."),
        ("post_entry", post_entry_score, 1, 1.80, f"Post-entry thesis state is {request.post_entry_thesis_status}; thesis break overrides entry thesis."),
    ]
    return [
        FinalConfluenceVote(
            vote_id=f"V175-{idx:02d}-{layer}",
            evidence_layer=layer,  # type: ignore[arg-type]
            direction=_direction(raw),
            raw_score=round(raw, 6),
            weighted_score=round(raw * weight, 6),
            priority_rank=rank,
            reason=reason,
        )
        for idx, (layer, raw, rank, weight, reason) in enumerate(vote_specs, start=1)
    ]


def _conflicts(request: FinalConfluenceArbiterRequest, votes: list[FinalConfluenceVote]) -> list[FinalConfluenceConflict]:
    conflicts: list[FinalConfluenceConflict] = []
    if request.daily_resistance_conflict and request.indicator_signal_score > 0.20:
        conflicts.append(_conflict("ARB-C001", "structure/levels > indicator signal", "downgrade", ["V175-05-structure_levels", "V175-08-indicators"], -1.0, "Bullish indicators are downgraded because price is at daily resistance."))
    if request.weak_sector and request.direction == "long" and request.structure_score > 0.25:
        conflicts.append(_conflict("ARB-C002", "relative strength > isolated stock move", "reduce", ["V175-04-market_regime", "V175-07-relative_strength"], -0.8, "Long structure is reduced because sector or breadth context is weak."))
    if request.trap_score >= 0.70:
        conflicts.append(_conflict("ARB-C003", "price action/order-flow proxy > analog or indicator strength", "block", ["V175-01-risk_safety", "V175-05-structure_levels"], -2.5, f"Trap score {request.trap_score:.2f} is high enough to override continuation evidence."))
    if request.event_risk_score >= 0.65:
        conflicts.append(_conflict("ARB-C004", "event risk can downgrade all signals", "downgrade", ["V175-01-risk_safety", "V175-09-external_ai"], -1.25, f"Event risk score {request.event_risk_score:.2f} downgrades candidate confidence."))
    if request.liquidity_grade == "C":
        conflicts.append(_conflict("ARB-C005", "liquidity can block all signals", "block", ["V175-03-liquidity"], -2.5, "Liquidity grade C blocks PAPER-CANDIDATE even when other evidence agrees."))
    if request.post_entry_thesis_status == "invalidated":
        conflicts.append(_conflict("ARB-C006", "post-entry invalidation overrides entry thesis", "block", ["V175-10-post_entry"], -3.0, "Post-entry thesis is invalidated; original long/short thesis cannot remain active."))
    if request.indicator_signal_score > 0.45 and request.structure_score < -0.35:
        conflicts.append(_conflict("ARB-C007", "structure/levels > single indicator agreement", "downgrade", ["V175-05-structure_levels", "V175-08-indicators"], -1.0, "Indicator agreement conflicts with bearish/hostile structure."))
    if not request.data_quality_pass or not request.no_future_leakage:
        conflicts.append(_conflict("ARB-C008", "risk/safety > all evidence", "block", ["V175-02-data_quality"], -3.0, "Data quality or no-future-leakage gate failed."))
    return conflicts


def _decision(confluence_score: int, request: FinalConfluenceArbiterRequest, hard_block: bool) -> tuple[str, str]:
    if hard_block:
        return "AVOID", "AVOID"
    if (
        request.low_evidence_flag
        or request.evidence_count < request.minimum_evidence_count
        or not request.required_mtf_complete
        or not request.entry_plan_authority_present
    ):
        if confluence_score >= 2:
            return "WATCH", "WATCH"
        return "WAIT", "WAIT"
    if confluence_score >= 5:
        if request.event_risk_score >= 0.65:
            return "WATCH", "WATCH"
        return "PAPER_CANDIDATE", "PAPER-CANDIDATE"
    if confluence_score >= 2:
        return "WATCH", "WATCH"
    if confluence_score >= -1:
        return "WAIT", "WAIT"
    if confluence_score >= -4:
        return "AVOID", "AVOID"
    if request.direction == "short" and request.short_logic_enabled:
        return "SHORT_PAPER_CANDIDATE", "SHORT PAPER-CANDIDATE"
    return "AVOID", "AVOID"


def _hard_block(request: FinalConfluenceArbiterRequest, conflicts: list[FinalConfluenceConflict]) -> bool:
    if not request.data_quality_pass or not request.no_future_leakage:
        return True
    if request.liquidity_grade == "C":
        return True
    if request.post_entry_thesis_status == "invalidated":
        return True
    return any(conflict.severity == "block" for conflict in conflicts)


def _dominant_blocker(request: FinalConfluenceArbiterRequest, conflicts: list[FinalConfluenceConflict]) -> str | None:
    if not request.no_future_leakage:
        return "future_leakage_or_repaint_risk"
    if not request.data_quality_pass:
        return "data_quality_failed"
    if request.post_entry_thesis_status == "invalidated":
        return "post_entry_thesis_invalidated"
    if request.liquidity_grade == "C":
        return "liquidity_grade_c"
    for conflict in conflicts:
        if conflict.severity == "block":
            return conflict.rule
    if request.low_evidence_flag or request.evidence_count < request.minimum_evidence_count:
        return "low_evidence"
    if not request.required_mtf_complete:
        return "required_mtf_incomplete"
    if not request.entry_plan_authority_present:
        return "entry_plan_authority_missing"
    if conflicts:
        return conflicts[0].rule
    return None


def _risk_score(request: FinalConfluenceArbiterRequest) -> float:
    score = 0.35
    score -= request.trap_score * 0.85
    score -= request.event_risk_score * 0.55
    if request.liquidity_grade == "C":
        score -= 0.65
    if not request.data_quality_pass or not request.no_future_leakage:
        score = -1.0
    return _clamp(score, -1.0, 1.0)


def _post_entry_score(status: str) -> float:
    if status == "intact":
        return 0.25
    if status == "weakening":
        return -0.55
    if status == "invalidated":
        return -1.0
    if status == "exited":
        return -0.70
    return 0.0


def _direction(score: float) -> str:
    if score <= -0.85:
        return "block"
    if score > 0.15:
        return "long"
    if score < -0.15:
        return "short"
    return "neutral"


def _bounded_score(raw_score: float) -> int:
    return max(-7, min(7, int(round(raw_score))))


def _confidence_interval(score: int, request: FinalConfluenceArbiterRequest, conflicts: list[FinalConfluenceConflict]) -> list[float]:
    center = _clamp((score + 7.0) / 14.0, 0.0, 1.0)
    width = 0.18 + min(0.22, len(conflicts) * 0.035)
    if request.evidence_count < 5:
        width += 0.08
    return [round(_clamp(center - width, 0.0, 1.0), 4), round(_clamp(center + width, 0.0, 1.0), 4)]


def _reason_tree(
    request: FinalConfluenceArbiterRequest,
    votes: list[FinalConfluenceVote],
    conflicts: list[FinalConfluenceConflict],
    final_decision: str,
    dominant_blocker: str | None,
) -> list[str]:
    top_votes = sorted(votes, key=lambda vote: abs(vote.weighted_score), reverse=True)[:4]
    tree = [
        f"Final decision is {final_decision}.",
        f"Evidence hierarchy used: {', '.join(EVIDENCE_HIERARCHY)}.",
        f"Strongest votes: {'; '.join(f'{vote.evidence_layer}={vote.weighted_score:.2f}' for vote in top_votes)}.",
    ]
    if conflicts:
        tree.append(f"Conflicts detected: {'; '.join(conflict.rule for conflict in conflicts)}.")
    else:
        tree.append("No high-priority conflict was detected.")
    if dominant_blocker:
        tree.append(f"Dominant blocker: {dominant_blocker}.")
    if request.indicator_signal_score > 0 and request.daily_resistance_conflict:
        tree.append("Indicator agreement is treated as late/supportive evidence, not approval, because resistance context dominates.")
    if request.low_evidence_flag or request.evidence_count < request.minimum_evidence_count:
        tree.append(
            f"Post-aggregation evidence cap applied: {request.evidence_count} completed records "
            f"are below the required {request.minimum_evidence_count}."
        )
    if not request.required_mtf_complete:
        tree.append("Required higher-timeframe evidence is incomplete, so the final band cannot exceed WATCH.")
    if not request.entry_plan_authority_present:
        tree.append("No verified entry/stop/target authority is present, so the final band cannot exceed WATCH.")
    return tree


def _reasons(final_decision: str, dominant_blocker: str | None, score: int) -> list[str]:
    reasons = [
        f"Confluence score is {score}; final band is {final_decision}.",
        "The arbiter is display/research-only and cannot route orders.",
    ]
    if dominant_blocker:
        reasons.append(f"Dominant blocker is {dominant_blocker}.")
    return reasons


def _failure_questions(request: FinalConfluenceArbiterRequest) -> list[str]:
    return [
        "Did any higher-priority risk/safety gate fail after lower-priority indicators turned bullish?",
        "Is this setup being promoted by lagging indicators after structure already rejected?",
        "Is liquidity, event risk, trap score, or post-entry thesis state invalidating the candidate?",
        f"Is evidence count ({request.evidence_count}) enough to trust the score without overfitting?",
    ]


def _gates(
    request: FinalConfluenceArbiterRequest,
    votes: list[FinalConfluenceVote],
    conflicts: list[FinalConfluenceConflict],
    final_decision: str,
) -> list[FinalConfluenceArbiterGate]:
    score_sum = round(sum(vote.weighted_score for vote in votes), 6)
    hard_block = _hard_block(request, conflicts)
    return [
        _gate("ARB-001", "Bullish indicators at daily resistance are downgraded", not (request.daily_resistance_conflict and request.indicator_signal_score > 0.20) or any(conflict.conflict_id == "ARB-C001" for conflict in conflicts), "warn" if request.daily_resistance_conflict else "info", f"daily_resistance_conflict={request.daily_resistance_conflict}; indicator_score={request.indicator_signal_score:.2f}."),
        _gate("ARB-002", "Weak sector reduces long confidence", not (request.weak_sector and request.direction == "long") or any(conflict.conflict_id == "ARB-C002" for conflict in conflicts), "warn" if request.weak_sector else "info", f"weak_sector={request.weak_sector}."),
        _gate("ARB-003", "High trap score overrides analog or indicator strength", request.trap_score < 0.70 or any(conflict.conflict_id == "ARB-C003" for conflict in conflicts), "block" if request.trap_score >= 0.70 else "info", f"trap_score={request.trap_score:.2f}."),
        _gate("ARB-004", "Event risk downgrades candidate state", request.event_risk_score < 0.65 or any(conflict.conflict_id == "ARB-C004" for conflict in conflicts), "warn" if request.event_risk_score >= 0.65 else "info", f"event_risk_score={request.event_risk_score:.2f}."),
        _gate("ARB-005", "Liquidity C blocks PAPER-CANDIDATE", request.liquidity_grade != "C" or final_decision != "PAPER-CANDIDATE", "block" if request.liquidity_grade == "C" else "info", f"liquidity_grade={request.liquidity_grade}; final_decision={final_decision}."),
        _gate("ARB-006", "Post-entry thesis break overrides original plan", request.post_entry_thesis_status != "invalidated" or hard_block, "block" if request.post_entry_thesis_status == "invalidated" else "info", f"post_entry_thesis_status={request.post_entry_thesis_status}."),
        _gate("ARB-007", "Every final decision has a reason tree", True, "info", "human_reason_tree is generated deterministically."),
        _gate("ARB-008", "Evidence scores sum deterministically", True, "info", f"weighted_vote_sum={score_sum}; conflicts={len(conflicts)}."),
        _gate(
            "ARB-009",
            "Post-aggregation minimum evidence cap",
            request.evidence_count >= request.minimum_evidence_count and not request.low_evidence_flag
            or final_decision in {"WAIT", "WATCH", "AVOID"},
            "warn" if request.evidence_count < request.minimum_evidence_count or request.low_evidence_flag else "info",
            f"evidence_count={request.evidence_count}; minimum={request.minimum_evidence_count}; "
            f"low_evidence_flag={request.low_evidence_flag}; final_decision={final_decision}.",
        ),
        _gate(
            "ARB-010",
            "Required higher-timeframe evidence caps promotion",
            request.required_mtf_complete or final_decision in {"WAIT", "WATCH", "AVOID"},
            "warn" if not request.required_mtf_complete else "info",
            f"required_mtf_complete={request.required_mtf_complete}; final_decision={final_decision}.",
        ),
        _gate(
            "ARB-011",
            "Verified entry plan is required for paper candidacy",
            request.entry_plan_authority_present or final_decision in {"WAIT", "WATCH", "AVOID"},
            "warn" if not request.entry_plan_authority_present else "info",
            f"entry_plan_authority_present={request.entry_plan_authority_present}; final_decision={final_decision}.",
        ),
        _gate("V175-SAFE-001", "No live trading capability", True, "info", "trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true."),
    ]


def _risk_reason(request: FinalConfluenceArbiterRequest) -> str:
    return f"Risk score reflects trap={request.trap_score:.2f}, event={request.event_risk_score:.2f}, liquidity={request.liquidity_grade}, data_quality={request.data_quality_pass}."


def _conflict(
    conflict_id: str,
    rule: str,
    severity: str,
    affected_votes: list[str],
    score_adjustment: float,
    reason: str,
) -> FinalConfluenceConflict:
    return FinalConfluenceConflict(
        conflict_id=conflict_id,
        rule=rule,
        severity=severity,  # type: ignore[arg-type]
        affected_votes=affected_votes,
        score_adjustment=score_adjustment,
        reason=reason,
    )


def _gate(gate_id: str, name: str, passed: bool, severity: str, evidence: str, remediation: str | None = None) -> FinalConfluenceArbiterGate:
    return FinalConfluenceArbiterGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
        remediation=remediation,
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
