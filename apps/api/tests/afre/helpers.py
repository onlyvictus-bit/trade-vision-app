"""Synthetic fixtures, deliberately not market evidence."""
from datetime import date, timedelta
from app.orb.adaptive.contracts import *
from app.orb.adaptive.controller import Controller
from app.orb.adaptive.runtime import *
from app.orb.adaptive.research import ResearchDay, ResearchMarket

DAY = '2026-09-04'
ROWS = [(102,102.6,101.8,102.2), (102.2,102.95,102.1,102.72),
        (102.72,102.8,102.3,102.42), (102.4,102.45,101.95,101.98)]
SAFE = SafetyState(mode='MOCK',kill_switch_armed=True,data_gate_passed=True)

def limits(account='fixture'):
    return AccountLimits(account_id=account,risk_budget=1000,maximum_notional=100000,maximum_quantity=500)

def policy(**kwargs):
    return Policy(range_minutes=5,reward_risk=1,**kwargs)

def prior(symbol='TEST', day=DAY, **kwargs):
    prev=(date.fromisoformat(day)-timedelta(days=1)).isoformat()
    fields=dict(symbol=symbol,session_date=prev,available_ns=clock_ns(prev,930),high=102,low=98,close=100,
                atr14=2,tick_size=.01,source_id='fixture',price_basis='basis',verified_prior_session=True,basis_verified=True)
    return PriorContext(**(fields|kwargs))

def bar(i,row=None,*,day=DAY,symbol='TEST',minutes=5,lag=0,**kwargs):
    row=ROWS[i] if row is None else row
    t=clock_ns(day,555)+i*minutes*MINUTE
    fields=dict(symbol=symbol,minutes=minutes,open_ns=t,close_ns=t+minutes*MINUTE,
                available_ns=t+minutes*MINUTE+lag*NS,open=row[0],high=row[1],low=row[2],close=row[3],
                volume=1000,source_id='fixture',price_basis='basis')
    return Bar(**(fields|kwargs))

def snapshot(rows=ROWS,*,day=DAY,symbol='TEST',**kwargs):
    bars=tuple(bar(i,r,day=day,symbol=symbol) for i,r in enumerate(rows))
    return MarketSnapshot(**(dict(session_date=day,as_of_ns=bars[-1].available_ns,prior=prior(symbol,day),bars=bars)|kwargs))

def controller(p=None, account='fixture'):
    return Controller(p or policy(),limits(account))

def state_to_fade(p=None):
    c=controller(p)
    state=new_session(DAY,(prior(),),c.policy,c.limits)
    for i,r in enumerate(ROWS):
        b=bar(i,r)
        state=advance_session(state,EventBatch(event_id=f'e{i}',available_ns=b.available_ns,feature_bars=(b,),execution_bars=(b,)),c,SAFE)
    return state,c

def plan(side=Side.LONG,entry=100.,stop=95.,rr=1,**kwargs):
    from app.orb.adaptive.execution import target_for
    base=dict(proposal_id='fixture-proposal',policy_hash='p'*64,snapshot_hash='s'*64,symbol='TEST',session_date=DAY,
              template=Template.FIRST_BREAK,side=side,created_ns=clock_ns(DAY,580),expires_ns=clock_ns(DAY,600),
              last_entry_ns=clock_ns(DAY,615),flat_ns=clock_ns(DAY,910),execution_minutes=5,tick_size=.01,
              price_basis='basis',reference_entry=entry,minimum_entry=entry-1,maximum_entry=entry+6,
              stop=stop,reward_risk=rr,reference_target=target_for(entry,stop,side,rr,.01),maximum_quantity=10,
              risk_budget=1000,maximum_notional=100000,cost_model=Costs(spread_bps=0,slippage_bps=0,impact_bps=0,fee_bps_per_side=0),
              pdc=90,requires_gap_unfilled=False,invalidation_level=99,invalidate_on='CLOSE_BACK_INSIDE',reason_codes=('FIXTURE',))
    if side==Side.SHORT:
        base['minimum_entry']=entry-6; base['maximum_entry']=entry+1
    return TradePlan(**(base|kwargs))

def synthetic_day(day=DAY, variant='fade', symbol='TEST'):
    rows=list(ROWS)
    # One independent fade, later fill at 09:40 (index5), never at signal close.
    rows += [(101.98,102.00,101.90,101.95),(101.95,102.,101.4,101.5)]
    rows += [(101.5,101.6,100.8,101.0)]
    while len(rows)<75:
        rows.append((101.,101.1,100.9,101.))
    if variant=='loss':
        rows[6]=(101.5,103.2,101.4,103.)
    if variant=='missing':
        bars=tuple(bar(i,r,day=day,symbol=symbol) for i,r in enumerate(rows) if i!=7)
    else:
        bars=tuple(bar(i,r,day=day,symbol=symbol) for i,r in enumerate(rows))
    return ResearchDay(session_date=day,markets=(ResearchMarket(prior=prior(symbol,day),feature_bars=bars,execution_bars=bars),),
                       source_origin='SYNTHETIC',source_manifest_hash='synthetic-fixture-manifest',completeness_attested=variant!='missing')
