"""Shared event reducer for synchronized research and human-paper sessions.

This module has no wall clock, storage, network, or permission bypass. The
service supplies trusted time and proof status; research uses the same reducer
but records simulated approvals with RESEARCH_REPLAY origin only.
"""
from __future__ import annotations

from typing import Annotated
from pydantic import Field, model_validator
from .contracts import (
    Frozen, SafeOutput, Identifier, PriorContext, Bar, Capability, Decision,
    Position, TradePlan, Policy, AccountLimits, SafetyState, MarketSnapshot,
    MINUTE, NS, clock_ns, digest, evolve, Side,
)
from .controller import Controller
from .execution import advance_position, cancel_pending, mark_unknown, start_position


class EventBatch(Frozen):
    event_id: Identifier
    available_ns: Annotated[int, Field(strict=True, gt=0)]
    feature_bars: Annotated[tuple[Bar, ...], Field(max_length=100)] = ()
    execution_bars: Annotated[tuple[Bar, ...], Field(max_length=500)] = ()
    capabilities: dict[str, tuple[Capability, ...]] = Field(default_factory=dict)
    integrity_faults: tuple[str, ...] = ()

    @model_validator(mode="after")
    def valid(self):
        if any(b.available_ns != self.available_ns for b in self.feature_bars):
            raise ValueError("FEATURE_BATCH_REQUIRES_ONE_AVAILABILITY_WATERMARK")
        if any(b.available_ns > self.available_ns for b in self.execution_bars):
            raise ValueError("EXECUTION_FROM_FUTURE")
        if len({b.symbol for b in self.feature_bars}) != len(self.feature_bars):
            raise ValueError("ONE_NEW_FEATURE_BAR_PER_SYMBOL_PER_BATCH")
        if any(c.available_ns > self.available_ns for cs in self.capabilities.values() for c in cs):
            raise ValueError("REFERENCE_FROM_FUTURE")
        return self


class SessionState(SafeOutput):
    session_date: str
    account_id: str
    policy_hash: str
    limits_hash: str
    universe: tuple[str, ...]
    prior: dict[str, PriorContext]
    feature_prefixes: dict[str, tuple[Bar, ...]]
    capabilities: dict[str, tuple[Capability, ...]] = Field(default_factory=dict)
    execution_seen: dict[str, str] = Field(default_factory=dict)
    watermark_ns: int
    decisions: dict[str, Decision] = Field(default_factory=dict)
    active_proposal: TradePlan | None = None
    position: Position | None = None
    approval_accepted: bool = False
    filled_entry_used: bool = False
    quarantine: tuple[str, ...] = ()
    sequence: int = 0
    last_action: str = "WAIT_FOR_NEW_INFORMATION"


def new_session(day: str, priors: tuple[PriorContext, ...], policy: Policy, limits: AccountLimits) -> SessionState:
    if not 1 <= len(priors) <= 100 or len({x.symbol for x in priors}) != len(priors):
        raise ValueError("UNIVERSE_REQUIRES_1_TO_100_DISTINCT_SYMBOLS")
    opening = clock_ns(day, policy.open_minute)
    for prior in priors:
        if prior.session_date >= day or prior.available_ns > opening:
            raise ValueError("PRIOR_CONTEXT_NOT_AVAILABLE_BEFORE_CURRENT_SESSION")
    return SessionState(session_date=day, account_id=limits.account_id,
                        policy_hash=policy.policy_hash, limits_hash=digest(limits),
                        universe=tuple(sorted(x.symbol for x in priors)),
                        prior={x.symbol: x for x in priors},
                        feature_prefixes={x.symbol: () for x in priors}, watermark_ns=opening)


def select_global(decisions: dict[str, Decision], policy: Policy, watermark: int) -> TradePlan | None:
    """Fixed rule priority then symbol, or supported LCB then same tie-break.

    Only proposals generated at this exact watermark compete. Same-date
    symbols are one account decision, not independent budget allocations.
    """
    eligible = []
    for symbol, decision in decisions.items():
        plan = decision.selected_plan
        if plan is None or decision.as_of_ns != watermark:
            continue
        c = next(x for x in decision.candidates if x.plan and x.plan.proposal_id == plan.proposal_id)
        value_key = -(c.lower_bound or 0.0) if policy.value_model_hash else 0.0
        eligible.append((value_key, policy.templates.index(plan.template), symbol, plan))
    return min(eligible, key=lambda x: x[:3])[-1] if eligible else None


def pending_invalidation(position: Position, decision: Decision) -> str | None:
    if position.status != "PENDING":
        return None
    f, plan = decision.features, position.plan
    if decision.internal_action == "HALT_AFFECTED_DECISIONS_FOR_DATA":
        return "DATA_INVALIDATES_APPROVED_UNFILLED_PLAN"
    if plan.requires_gap_unfilled and decision.gap_ever_touched_pdc:
        return "ORIGINAL_GAP_FILLED_BEFORE_ENTRY"
    if not f or "latest_close" not in f:
        return None
    close = float(f["latest_close"])
    if plan.invalidate_on == "CLOSE_BACK_INSIDE":
        if (close - plan.invalidation_level) * plan.side.sign <= 0:
            return "APPROVED_CONTINUATION_INVALIDATED"
    else:
        gap_sign = -plan.side.sign
        if (close - plan.invalidation_level) * gap_sign > 0:
            return "APPROVED_FADE_INVALIDATED_BY_RECLAIM"
    return None


def advance_session(state: SessionState, event: EventBatch, controller: Controller,
                    safety: SafetyState, *, paper_authority: bool = False,
                    proof_hash: str | None = None) -> SessionState:
    p = controller.policy
    if state.policy_hash != p.policy_hash or state.limits_hash != digest(controller.limits):
        raise ValueError("SESSION_POLICY_OR_ACCOUNT_LIMITS_CHANGED")
    if event.available_ns < state.watermark_ns:
        raise ValueError("OUT_OF_ORDER_EVENT_REQUIRES_SEPARATE_RECONCILIATION")
    opening = clock_ns(state.session_date, p.open_minute)
    closing = clock_ns(state.session_date, 15 * 60 + 30)
    if not opening <= event.available_ns <= closing + 30 * MINUTE:
        raise ValueError("EVENT_OUTSIDE_CONFIGURED_SESSION")
    quarantine = list(state.quarantine) + list(event.integrity_faults)
    seen = dict(state.execution_seen)
    position = state.position
    # Exit accounting always runs FIRST, even under a triggered kill switch.
    for b in sorted(event.execution_bars, key=lambda x: (x.available_ns, x.open_ns, x.symbol)):
        if b.symbol not in state.universe or b.minutes != p.execution_minutes:
            quarantine.append("EXECUTION_IDENTITY_OUTSIDE_FROZEN_UNIVERSE")
            continue
        key = f"{b.symbol}:{b.open_ns}:{b.minutes}"
        if key in seen and seen[key] != b.event_id:
            quarantine.append("EXECUTION_REVISION_CONFLICT")
            if position and position.plan.symbol == b.symbol:
                position = mark_unknown(position, "EXECUTION_REVISION_CONFLICT")
            continue
        if key in seen:
            continue
        seen[key] = b.event_id
        if b.revision != 0:
            quarantine.append("EXECUTION_REVISION_REQUIRES_OFFLINE_RECONCILIATION")
            if position and position.plan.symbol == b.symbol:
                position = mark_unknown(position, "EXECUTION_REVISION_REQUIRES_OFFLINE_RECONCILIATION")
            continue
        if position and position.plan.symbol == b.symbol:
            if position.status == "PENDING" and position.origin == "HUMAN_APPROVED_PAPER" and not paper_authority:
                position = cancel_pending(position, "PROOF_REVOKED_BEFORE_FILL")
            if position.status == "PENDING" and not safety.allows_analysis:
                position = cancel_pending(position, "SAFETY_REVOKED_BEFORE_FILL")
            position = advance_position(position, b, as_of_ns=event.available_ns)
    prefixes = dict(state.feature_prefixes)
    changed = False
    for b in event.feature_bars:
        if b.symbol not in state.universe:
            quarantine.append("FEATURE_SYMBOL_OUTSIDE_FROZEN_UNIVERSE")
            continue
        old = prefixes[b.symbol]
        same = next((x for x in old if x.open_ns == b.open_ns), None)
        if same:
            if same.event_id != b.event_id:
                quarantine.append("FEATURE_REVISION_CONFLICT")
            continue
        if old and b.open_ns <= old[-1].open_ns:
            quarantine.append("FEATURE_OUT_OF_ORDER")
            continue
        if len(old) >= 400:
            quarantine.append("FEATURE_BOUND_EXCEEDED")
            continue
        prefixes[b.symbol] = old + (b,)
        changed = True
    caps = dict(state.capabilities)
    for symbol, records in event.capabilities.items():
        if symbol not in state.universe:
            quarantine.append("CAPABILITY_SYMBOL_OUTSIDE_UNIVERSE")
            continue
        if len({x.name for x in records}) != len(records):
            quarantine.append("DUPLICATE_CAPABILITY_NAME")
            continue
        if caps.get(symbol) != records:
            caps[symbol] = records
            changed = True
    decisions = dict(state.decisions)
    proposal = state.active_proposal
    # References and new bars wake evaluation once. Timer-only events cannot
    # refresh a proposal's TTL or create fictitious new evidence.
    if changed or quarantine != list(state.quarantine):
        for symbol in state.universe:
            try:
                snapshot = MarketSnapshot(session_date=state.session_date, as_of_ns=event.available_ns,
                                          prior=state.prior[symbol], bars=prefixes[symbol],
                                          capabilities=caps.get(symbol, ()), data_blockers=tuple(dict.fromkeys(quarantine)))
                decisions[symbol] = controller.evaluate(snapshot)
                if state.decisions.get(symbol) and state.decisions[symbol].gap_ever_touched_pdc:
                    decisions[symbol] = evolve(decisions[symbol], gap_ever_touched_pdc=True)
            except ValueError:
                quarantine.append("SNAPSHOT_VALIDATION_FAILED:" + symbol)
        # All declared symbols must have equally closed prefixes. This avoids
        # falsely calling a partial local watchlist a synchronized universe.
        last_closes = {xs[-1].close_ns if xs else None for xs in prefixes.values()}
        aligned = len(last_closes) == 1 and None not in last_closes
        proposal = select_global(decisions, p, event.available_ns) if aligned else None
        if not aligned:
            decisions = {s: evolve(d, public_ticket="WATCH", internal_action="WAIT_FOR_UNIVERSE_WATERMARK",
                                    reason_codes=d.reason_codes + ("UNIVERSE_NOT_SYNCHRONIZED",))
                         for s, d in decisions.items()}
    if position and position.status == "PENDING" and (not safety.allows_analysis or (position.origin == "HUMAN_APPROVED_PAPER" and not paper_authority)):
        position = cancel_pending(position, "AUTHORITY_REVOKED_BEFORE_FILL")
    if position and position.status == "PENDING" and position.plan.symbol in decisions:
        reason = pending_invalidation(position, decisions[position.plan.symbol])
        if reason:
            position = cancel_pending(position, reason)
    # Once an interval should have been available, missing prices do not become
    # a benign no-fill. UNKNOWN keeps the consumed attempt reserved.
    if position and position.status in {"PENDING", "OPEN"}:
        due = position.expected_open_ns + p.execution_minutes * MINUTE + p.max_feature_lag_seconds * NS
        if event.available_ns > due:
            position = mark_unknown(position, "EXECUTION_FEED_DEADLINE_MISSED")
    if quarantine and position:
        if position.status == "PENDING":
            position = cancel_pending(position, "DATA_QUARANTINE_BEFORE_FILL")
        elif position.status == "OPEN":
            position = mark_unknown(position, "DATA_QUARANTINE_WITH_OPEN_POSITION")
    filled = state.filled_entry_used or bool(position and position.fill_ns is not None)
    if proposal and event.available_ns >= proposal.expires_ns:
        proposal = None
    blocked = (bool(quarantine) or not safety.allows_analysis or state.approval_accepted
               or filled or event.available_ns >= clock_ns(state.session_date, p.last_entry_minute))
    if blocked:
        proposal = None
    for symbol, decision in list(decisions.items()):
        can_offer = bool(proposal and decision.selected_plan and
                         decision.selected_plan.proposal_id == proposal.proposal_id and paper_authority and proof_hash)
        action = "REQUEST_PAPER_APPROVAL" if can_offer else decision.internal_action
        if filled:
            action = "MAINTAIN_EXISTING_FIXED_EXIT_POLICY_SHADOW_ONLY"
        elif state.approval_accepted:
            action = "APPROVAL_ATTEMPT_CONSUMED"
        elif not safety.allows_analysis:
            action = "SAFETY_BLOCKED_NEW_ENTRIES"
        elif event.available_ns >= clock_ns(state.session_date, p.last_entry_minute):
            action = "SKIP_SESSION_ENTRY_WINDOW_EXPIRED"
        elif quarantine:
            action = "HALT_AFFECTED_DECISIONS_FOR_DATA"
        # Never leave an earlier PAPER-CANDIDATE badge alive after revocation.
        decisions[symbol] = evolve(decision, public_ticket="PAPER-CANDIDATE" if can_offer else
                                   "WAIT" if blocked else "WATCH", internal_action=action,
                                   proof_hash=proof_hash if can_offer else None)
    return evolve(state, feature_prefixes=prefixes, execution_seen=seen, capabilities=caps,
                  decisions=decisions, active_proposal=proposal, position=position,
                  filled_entry_used=filled, quarantine=tuple(dict.fromkeys(quarantine)),
                  watermark_ns=event.available_ns, sequence=state.sequence + 1,
                  last_action="PAPER_CANDIDATE" if proposal and paper_authority else "SHADOW_CANDIDATE" if proposal else "WAIT_FOR_NEW_INFORMATION")


def accept_proposal(state: SessionState, controller: Controller, proposal_id: str,
                    proposal_hash: str, quantity: int, now_ns: int, actor: str, *, research=False) -> SessionState:
    if state.approval_accepted or state.filled_entry_used or state.quarantine:
        raise ValueError("ACCOUNT_SESSION_ALLOWANCE_UNAVAILABLE")
    plan = state.active_proposal
    if plan is None or plan.proposal_id != proposal_id or digest(plan) != proposal_hash:
        raise ValueError("STALE_OR_TAMPERED_PROPOSAL")
    position = start_position(plan, controller.limits, now_ns, quantity, actor, research=research)
    decisions = {s: evolve(d, public_ticket="WATCH", internal_action="APPROVED_FIXED_PLAN_NO_SWITCHING")
                 for s, d in state.decisions.items()}
    return evolve(state, approval_accepted=True, active_proposal=None, position=position,
                  decisions=decisions, last_action="AWAITING_FIRST_PERMITTED_EXECUTION_OPEN")
