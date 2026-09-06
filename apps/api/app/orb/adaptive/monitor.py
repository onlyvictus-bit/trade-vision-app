"""Matured-outcome diagnostics and retrospective shadow-policy regret.

Never modifies active models, approval budgets, or a fixed trade's exits.
Warnings create review work, not automatically self-deployed strategies.
"""
from __future__ import annotations
from statistics import mean
from typing import Literal
from .contracts import Frozen, SafeOutput, digest
from .value import ActionOutcome,lower_mean_bound


class OutcomeEvidence(Frozen):
    outcome_id: str
    account_id: str
    session_date: str
    policy_hash: str
    available_ns: int
    net_budget_units: float | None
    origin: Literal["ATTESTED_REAL_PAPER", "SHADOW_REPLAY", "SYNTHETIC"]


class MonitoringReport(SafeOutput):
    policy_hash: str
    as_of_ns: int
    status: Literal["INSUFFICIENT_DATA","DATA_UNRESOLVED","REVIEW_DUE","NO_REVIEW_TRIGGER"]
    unique_dates: int
    unknown_dates: int
    recent_mean: float | None
    recent_lower_bound: float | None
    previous_mean: float | None
    reasons: tuple[str,...]
    model_changed: Literal[False] = False
    automatic_promotion: Literal[False] = False


def monitor(rows: tuple[OutcomeEvidence,...], *, policy_hash: str, as_of_ns: int,
            minimum_dates: int=30, window: int=30) -> MonitoringReport:
    if minimum_dates<2 or window<minimum_dates:
        raise ValueError("DECLARED_MONITORING_SAMPLE_WINDOW_INVALID")
    selected=[r for r in rows if r.policy_hash==policy_hash and r.available_ns<=as_of_ns and r.origin=='ATTESTED_REAL_PAPER']
    seen={}
    for r in selected:
        key=(r.account_id,r.session_date)
        if key in seen and seen[key]!=r:
            raise ValueError("DUPLICATE_ACCOUNT_DATE_OUTCOMES_CANNOT_INFLATE_RELIABILITY")
        seen[key]=r
    # Multiple accounts on one date are not asserted to be independent market dates.
    by_date={}
    for r in seen.values():
        by_date.setdefault(r.session_date,[]).append(r.net_budget_units)
    daily=[None if any(v is None for v in vals) else mean(vals) for _,vals in sorted(by_date.items())]
    unknown=sum(v is None for v in daily)
    known=[v for v in daily if v is not None]
    recent=known[-window:]
    previous=known[-2*window:-window]
    avg=mean(recent) if recent else None
    lower=lower_mean_bound(tuple(recent)) if len(recent)>=minimum_dates else None
    if unknown:
        status,reasons='DATA_UNRESOLVED',('Missing outcomes are not zero or deleted losses; reconcile before reliability claims.',)
    elif len(known)<minimum_dates:
        status,reasons='INSUFFICIENT_DATA',('Collect independent matured real-paper session outcomes.',)
    elif avg is not None and avg<0:
        status,reasons='REVIEW_DUE',('Recent net expectancy is negative; review/suspend through existing operator governance.',)
    elif lower is not None and lower<=0:
        status,reasons='REVIEW_DUE',('The declared lower mean bound does not exceed skip; uncertainty remains.',)
    else:
        status,reasons='NO_REVIEW_TRIGGER',('No declared trigger fired; this does not establish future performance.',)
    return MonitoringReport(policy_hash=policy_hash,as_of_ns=as_of_ns,status=status,unique_dates=len(daily),unknown_dates=unknown,
                            recent_mean=avg,recent_lower_bound=lower,previous_mean=mean(previous) if previous else None,reasons=reasons)


def shadow_regret(rows: tuple[ActionOutcome,...], selected_action: str, *, as_of_ns: int) -> dict:
    identities={(r.snapshot_hash,r.rules_hash,r.limits_hash,r.session_date,r.issued_ns) for r in rows}
    if not rows or len(identities)!=1 or len({r.action for r in rows})!=len(rows):
        raise ValueError("REGRET_REQUIRES_SAME_INFORMATION_BUDGET_AND_DISTINCT_ACTIONS")
    if any(r.label_available_ns>as_of_ns for r in rows):
        return {'status':'NOT_YET_MATURED','regret':None,'used_for_original_selection':False}
    if any(r.net_budget_units is None for r in rows):
        return {'status':'UNKNOWN_OUTCOME','regret':None,'used_for_original_selection':False}
    value=0.0 if selected_action=='SKIP' else next(r.net_budget_units for r in rows if r.action==selected_action)
    best=max([0.0,*[r.net_budget_units for r in rows]])
    return {'status':'RETROSPECTIVE_ONLY','selected_value':value,'best_shadow_or_skip':best,'regret':best-value,
            'used_for_original_selection':False,'causal_market_effect_claimed':False,
            'note':'Hindsight description of predeclared simulated policies, not a tradable oracle.'}
