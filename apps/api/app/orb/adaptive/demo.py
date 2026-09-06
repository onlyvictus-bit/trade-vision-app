"""Explicitly synthetic examples. Never accepted as real-data policy proof."""
from __future__ import annotations
from datetime import date,timedelta
from .contracts import PriorContext,Bar,Policy,AccountLimits,MINUTE,clock_ns
from .research import ResearchDay,ResearchMarket


def demo_day(day: str = "2026-09-04", *, path: str="fade") -> ResearchDay:
    previous=(date.fromisoformat(day)-timedelta(days=1)).isoformat()
    prior=PriorContext(symbol="SYNTH",session_date=previous,available_ns=clock_ns(previous,930),
                       high=102,low=98,close=100,atr14=2,tick_size=.01,source_id="synthetic-fixture",
                       price_basis="synthetic-comparable",verified_prior_session=True,basis_verified=True)
    rows=[(102,102.6,101.8,102.2),(102.2,102.95,102.1,102.72),(102.72,102.8,102.3,102.42)]
    if path=="reclaim":
        rows += [(102.42,103,102.35,102.78),(102.78,103.05,102.7,102.9),(102.9,103.1,102.8,103),
                 (102.9,105,102.8,104)]
    elif path=="gap-filled":
        rows += [(102.4,102.45,99.9,101.98),(101.98,102,101.90,101.95),(101.95,102,101.4,101.5)]
    else:
        rows += [(102.4,102.45,101.95,101.98),(101.98,102,101.90,101.95),(101.95,102,101.4,101.5),
                 (101.5,103.2,101.4,103) if path=="fade-fails" else (101.5,101.6,100.8,101)]
    close=rows[-1][-1]
    while len(rows)<75:
        rows.append((close,close+.1,close-.1,close))
    bars=[]
    for i,(o,h,l,c) in enumerate(rows):
        start=clock_ns(day,555)+i*5*MINUTE
        bars.append(Bar(symbol="SYNTH",minutes=5,open_ns=start,close_ns=start+5*MINUTE,available_ns=start+5*MINUTE,
                        open=o,high=h,low=l,close=c,volume=1000,source_id="synthetic-fixture",price_basis=prior.price_basis))
    market=ResearchMarket(prior=prior,feature_bars=tuple(bars),execution_bars=tuple(bars))
    return ResearchDay(session_date=day,markets=(market,),source_origin="SYNTHETIC",
                       source_manifest_hash="explicit-synthetic-teaching-fixture",completeness_attested=True)


def demo_policy() -> Policy:
    return Policy(policy_id="synthetic-demo-unproven",range_minutes=5,reward_risk=1)


def demo_limits() -> AccountLimits:
    return AccountLimits(account_id="synthetic-research",risk_budget=1000,maximum_notional=100000,maximum_quantity=500)
