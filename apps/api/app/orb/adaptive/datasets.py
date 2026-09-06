"""Outcome-side research datasets. Never imported by the decision controller."""
from __future__ import annotations
from collections import defaultdict
from .contracts import MarketSnapshot, Policy, Template, NS, MINUTE, clock_ns, digest, evolve
from .controller import Controller
from .features import extract, validate_prefix
from .forecasting import Label, label_structural, context_key
from .research import ResearchDay, ResearchMarket, _complete_intervals
from .runtime import new_session, EventBatch, advance_session, accept_proposal, select_global
from .execution import mark_unknown
from .value import ActionOutcome
from .contracts import SafetyState


def structural_dataset(days: tuple[ResearchDay,...], controller: Controller) -> tuple[Label,...]:
    """Issue from causal prefixes; attach future labels only after evaluation."""
    labels=[]
    p=controller.policy
    for day in days:
        for market in day.markets:
            for i,b in enumerate(market.feature_bars):
                if b.available_ns >= clock_ns(day.session_date,p.last_entry_minute): break
                s=MarketSnapshot(session_date=day.session_date,as_of_ns=b.available_ns,prior=market.prior,
                                 bars=market.feature_bars[:i+1],
                                 capabilities=tuple(c for c in market.capabilities if c.available_ns<=b.available_ns<c.expires_ns))
                d=controller.evaluate(s)
                for forecast in d.forecasts:
                    if forecast.event in {"RETURN_INSIDE_OR","PDC_TOUCH"}:
                        labels.append(label_structural(forecast,s,market.feature_bars[i+1:],d.features,
                                                       rules_hash=p.rules_hash,source_origin=day.source_origin))
    return tuple(labels)


def shadow_wait_action(snapshot: MarketSnapshot, market: ResearchMarket, controller: Controller,
                       template: Template, *, source_origin: str, completeness_attested: bool) -> ActionOutcome:
    """Evaluate a fixed wait/entry policy from the SAME current information.

    At most one accepted research attempt. No best-future-retest selection.
    This is a one-symbol conditional counterfactual, not market-impact causality
    and not an independent additional market date. Parent selector still needs
    its own whole-universe proof before paper use.
    """
    parent=controller.policy
    if snapshot.prior != market.prior or template not in parent.templates:
        raise ValueError("COUNTERFACTUAL_IDENTITY_OR_TEMPLATE_MISMATCH")
    known=tuple(b for b in market.feature_bars if b.available_ns<=snapshot.as_of_ns)
    if known!=snapshot.bars or validate_prefix(snapshot,parent):
        raise ValueError("COUNTERFACTUAL_MUST_START_FROM_IDENTICAL_VALID_PREFIX")
    leaf=evolve(parent,templates=(template,),forecast_model_hash=None,value_model_hash=None)
    c=Controller(leaf,controller.limits,data_guard=controller.data_guard)
    state=new_session(snapshot.session_date,(snapshot.prior,),leaf,c.limits)
    decision=c.evaluate(snapshot)
    state=evolve(state,feature_prefixes={snapshot.prior.symbol:snapshot.bars},
                 capabilities={snapshot.prior.symbol:snapshot.capabilities},watermark_ns=snapshot.as_of_ns,
                 decisions={snapshot.prior.symbol:decision},active_proposal=decision.selected_plan)
    safety=SafetyState(mode="RESEARCH",kill_switch_armed=True,data_gate_passed=True)
    def maybe_approve(state):
        if state.active_proposal and not state.approval_accepted:
            plan=state.active_proposal
            try:
                return accept_proposal(state,c,plan.proposal_id,digest(plan),plan.maximum_quantity,
                                       state.watermark_ns+leaf.replay_approval_delay_seconds*NS,"SHADOW_WAIT_POLICY",research=True)
            except ValueError: return state
        return state
    state=maybe_approve(state)
    groups=defaultdict(lambda:{"feature":[],"execution":[]})
    for b in market.feature_bars:
        if snapshot.as_of_ns<b.available_ns<=clock_ns(snapshot.session_date,leaf.flat_minute):
            groups[b.available_ns]["feature"].append(b)
    for b in market.execution_bars:
        if snapshot.as_of_ns<b.available_ns<=clock_ns(snapshot.session_date,leaf.flat_minute):
            groups[b.available_ns]["execution"].append(b)
    for stamp,group in sorted(groups.items()):
        state=advance_session(state,EventBatch(event_id=digest([snapshot.snapshot_hash,template.value,stamp]),
                              available_ns=stamp,feature_bars=tuple(group['feature']),execution_bars=tuple(group['execution'])),c,safety)
        state=maybe_approve(state)
    complete=completeness_attested and not state.quarantine and _complete_intervals(market.feature_bars,
             clock_ns(snapshot.session_date,555),clock_ns(snapshot.session_date,leaf.last_entry_minute),leaf.feature_minutes)
    value=None
    if complete and state.position is None: value=0.0
    elif complete and state.position and state.position.status in {"CLOSED","NO_FILL"}: value=state.position.net_budget_units
    # Conservatively mature all these labels after the full fixed-exit window.
    mature=max([clock_ns(snapshot.session_date,leaf.flat_minute),*[b.available_ns for b in market.execution_bars if b.close_ns<=clock_ns(snapshot.session_date,leaf.flat_minute)]])
    return ActionOutcome(symbol=snapshot.prior.symbol,limits_hash=digest(c.limits),snapshot_hash=snapshot.snapshot_hash,
                         action_policy_hash=leaf.policy_hash,row_id=digest([snapshot.snapshot_hash,leaf.policy_hash,digest(c.limits)]),
                         session_date=snapshot.session_date,action=template,context_key=context_key(extract(snapshot,parent)),
                         issued_ns=snapshot.as_of_ns,label_available_ns=mature,net_budget_units=value,
                         source_origin=source_origin,rules_hash=parent.rules_hash)


def action_dataset(days: tuple[ResearchDay,...], controller: Controller, *, anchor_minute: int) -> tuple[ActionOutcome,...]:
    if not 555<anchor_minute<615:
        raise ValueError("ANCHOR_MUST_PRECEDE_ENTRY_CUTOFF")
    if any(len(d.markets)!=1 for d in days):
        raise ValueError("CONDITIONAL_ACTION_DATASET_REQUIRES_ONE_REGISTERED_SYMBOL")
    rows=[]
    for day in days:
        market=day.markets[0]
        anchor=clock_ns(day.session_date,anchor_minute)
        prefix=tuple(b for b in market.feature_bars if b.available_ns<=anchor)
        s=MarketSnapshot(session_date=day.session_date,as_of_ns=anchor,prior=market.prior,bars=prefix,
                         capabilities=tuple(c for c in market.capabilities if c.available_ns<=anchor<c.expires_ns))
        for template in controller.policy.templates:
            rows.append(shadow_wait_action(s,market,controller,template,source_origin=day.source_origin,
                                           completeness_attested=day.completeness_attested))
    return tuple(rows)
