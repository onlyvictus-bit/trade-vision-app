from __future__ import annotations

import json
import math
import time
from datetime import date

import httpx
import numpy as np
import pytest

from app.orb.derivatives.black76_extra import charm_black76_per_day, vanna_black76
from app.orb.derivatives.bridges import afre_capability_payloads, v173_payload_overlay
from app.orb.derivatives.calculators import (
    build_context, chain_arrays, dominant_oi_wall, max_pain, oi_change_arrays, pcr, skew_25d_pct,
)
from app.orb.derivatives.contracts import (
    DerivativesPolicy, EvidenceRelation, FuturesSnapshot, Greeks, OptionChainSnapshot, OptionQuote,
    OptionStrike, OptionType, PriceScenario, ScenarioKind, Side, digest,
)
from app.orb.derivatives.nse_rules import (
    TUESDAY, THURSDAY, current_index_future_tick, current_stock_option_tick, current_stock_future_tick,
    equity_derivative_expiry_weekday, expected_expiry_date,
)
from app.orb.derivatives.openalgo import OpenAlgoDataProvider
from app.orb.derivatives.reasoning import DerivativesScenarioController
from app.orb.derivatives.store import DerivativesStore

NOW = 1_800_000_000_000_000_000
EXP = date(2026, 9, 29)


def q(strike, kind, *, oi, vol=1000, ltp=10, lot=25, symbol=None):
    return OptionQuote(symbol=symbol or f"NIFTY29SEP26{int(strike)}{kind}", option_type=OptionType(kind), strike=strike,
                       ltp=ltp, bid=max(0, ltp-.1), ask=ltp+.1, volume=vol, oi=oi, lot_size=lot, tick_size=.05)


def chain(spot=100.0, ois=None, ns=NOW):
    strikes = [80, 90, 100, 110, 120]
    ois = ois or [(10, 50), (20, 80), (100, 100), (80, 20), (50, 10)]
    rows = tuple(OptionStrike(strike=s, ce=q(s, "CE", oi=co, ltp=max(1, 8-abs(s-100)*.2)), pe=q(s, "PE", oi=po, ltp=max(1, 8-abs(s-100)*.2)))
                 for s, (co, po) in zip(strikes, ois))
    return OptionChainSnapshot(underlying="NIFTY", underlying_exchange="NSE_INDEX", options_exchange="NFO", expiry_date=EXP,
                               underlying_ltp=spot, atm_strike=100, as_of_ns=ns, received_ns=ns, rows=rows,
                               provider_payload_hash=digest({"ns": ns, "ois": ois}))


def greeks():
    out=[]
    for s in [80,90,100,110,120]:
        cd={80:.90,90:.70,100:.50,110:.26,120:.10}[s]
        pd={80:-.10,90:-.24,100:-.50,110:-.72,120:-.90}[s]
        for kind,d,iv in [(OptionType.CE,cd,18+(s-100)*.02),(OptionType.PE,pd,20-(s-100)*.01)]:
            out.append(Greeks(symbol=f"NIFTY29SEP26{s}{kind.value}", strike=s, option_type=kind, days_to_expiry=22,
                              forward_price=100, option_price=8, implied_volatility_pct=iv, delta=d, gamma=.02 if s==100 else .01,
                              theta_per_day=-1, vega_per_vol_point=1.2, rho=.1))
    return tuple(out)


def fut(ltp=101, oi=1000, ns=NOW):
    return FuturesSnapshot(symbol="NIFTY29SEP26FUT", ltp=ltp, prev_close=100, oi=oi, volume=10000,
                           as_of_ns=ns, received_ns=ns, provider_payload_hash=digest({"ltp":ltp,"oi":oi,"ns":ns}))


def test_nse_expiry_transition_and_ticks():
    assert equity_derivative_expiry_weekday(date(2025,8,28)) == THURSDAY
    assert equity_derivative_expiry_weekday(date(2025,9,2)) == TUESDAY
    assert expected_expiry_date(date(2026,9,15), weekly=False).weekday() == TUESDAY
    assert current_index_future_tick(14999) == .05
    assert current_index_future_tick(20000) == .10
    assert current_index_future_tick(31000) == .20
    assert current_stock_option_tick(249.99) == .01
    assert current_stock_option_tick(250) == .05
    assert current_stock_future_tick(249) == .01
    assert current_stock_future_tick(800) == .05
    assert current_stock_future_tick(2000) == .10
    assert current_stock_future_tick(7000) == .50
    assert current_stock_future_tick(15000) == 1.00
    assert current_stock_future_tick(25000) == 5.00


def test_chain_contract_is_sorted_and_immutable():
    c=chain()
    assert c.rows[0].strike == 80
    with pytest.raises(Exception):
        c.underlying_ltp = 101


def test_pcr_exact():
    a=chain_arrays(chain())
    po, pv, co, put, cv, pvol = pcr(a)
    assert po == pytest.approx(260/260)
    assert pv == pytest.approx(1.0)


def test_true_max_pain_not_combined_oi_shortcut():
    a=chain_arrays(chain(ois=[(0,100),(0,0),(30,30),(100,0),(0,0)]))
    pain=max_pain(a.strikes,a.call_oi,a.put_oi)
    assert pain in set(a.strikes.tolist())
    # Verify against brute force definition.
    payouts=[]
    for settlement in a.strikes:
        call=float(np.sum(np.maximum(settlement-a.strikes,0)*a.call_oi))
        put=float(np.sum(np.maximum(a.strikes-settlement,0)*a.put_oi))
        payouts.append(call+put)
    assert pain == float(a.strikes[int(np.argmin(payouts))])


def test_oi_delta_alignment_handles_changed_universe():
    c1=chain()
    c2=chain(ois=[(11,55),(21,85),(110,90),(70,25),(45,9)], ns=NOW+1)
    dc,dp=oi_change_arrays(chain_arrays(c2),chain_arrays(c1))
    assert dc.tolist()==pytest.approx([1,1,10,-10,-5])
    assert dp.tolist()==pytest.approx([5,5,-10,5,-1])


def test_skew_25delta_uses_delta_not_fixed_strike():
    value=skew_25d_pct(greeks())
    # Call 110 ~= +0.26 IV 18.2; Put 90 ~= -0.24 IV 20.1.
    assert value == pytest.approx(1.9)


def test_higher_greeks_vectorized_finite():
    f=np.array([100.0,100.0]); k=np.array([95.0,105.0]); t=np.array([10/365,10/365]); s=np.array([.20,.25])
    va=vanna_black76(f,k,t,s)
    ch=charm_black76_per_day("CE",f,k,t,s)
    assert np.all(np.isfinite(va)) and np.all(np.isfinite(ch))


def test_context_builds_full_core_metrics():
    prev=chain(ns=NOW-5_000_000_000)
    cur=chain(ois=[(12,55),(22,90),(110,110),(90,22),(55,12)])
    ctx=build_context(cur,greeks(),previous_chain=prev,futures=fut(102,1200),previous_futures=fut(100,1000,NOW-5_000_000_000),
                      iv_history=tuple(10+i*.1 for i in range(40)),now_ns=NOW,horizon_minutes=30, policy=DerivativesPolicy(minimum_chain_rows=5))
    assert ctx.status == "AVAILABLE"
    assert ctx.max_pain is not None
    assert ctx.call_oi_wall and ctx.put_oi_wall
    assert ctx.call_gamma_wall and ctx.put_gamma_wall
    assert ctx.pcr_oi is not None and ctx.atm_iv_pct is not None
    assert ctx.futures_state == "LONG_BUILDUP"
    assert ctx.iv_percentile is not None
    assert ctx.trade_allowed is False and ctx.live_trading_blocked is True


def test_stale_chain_fail_closed():
    c=chain(ns=NOW-60_000_000_000)
    ctx=build_context(c,greeks(),now_ns=NOW,policy=DerivativesPolicy(max_chain_age_seconds=20))
    assert ctx.status == "STALE"
    s=PriceScenario(symbol="NIFTY",session_date=date(2026,9,7),as_of_ns=NOW,kind=ScenarioKind.CONTINUATION,side=Side.LONG,entry=100,target=105)
    a=DerivativesScenarioController().evaluate(s,ctx)
    assert a.relation == EvidenceRelation.BLOCK
    assert a.public_ticket_cap == "WAIT"


def test_near_wall_predicts_failure_and_caps_watch_wait():
    ctx=build_context(chain(),greeks(),now_ns=NOW)
    # Force a long entry just below whichever call wall calculator produced.
    wall=ctx.call_gamma_wall
    assert wall
    entry=wall.strike/1.005
    s=PriceScenario(symbol="NIFTY",session_date=date(2026,9,7),as_of_ns=NOW,kind=ScenarioKind.CONTINUATION,
                    side=Side.LONG,entry=entry,target=wall.strike*1.02,expiry_day=False)
    a=DerivativesScenarioController().evaluate(s,ctx)
    assert "GAMMA_WALL_AHEAD" in a.reason_codes
    assert any("stall/reject" in x or "reject" in x for x in a.predicted_failure_modes)
    assert a.relation in {EvidenceRelation.CONFLICT,EvidenceRelation.BLOCK}


def test_derivatives_never_create_trade():
    ctx=build_context(chain(),greeks(),futures=fut(102,1200),previous_futures=fut(100,1000,NOW-1),now_ns=NOW)
    s=PriceScenario(symbol="NIFTY",session_date=date(2026,9,7),as_of_ns=NOW,kind=ScenarioKind.RETEST,
                    side=Side.LONG,entry=100,target=100.2)
    a=DerivativesScenarioController().evaluate(s,ctx)
    assert a.trade_allowed is False
    assert a.public_ticket_cap in {"UNCHANGED","WATCH","WAIT"}


def test_v173_bridge_populates_existing_fields_without_none_overwrite():
    ctx=build_context(chain(),greeks(),now_ns=NOW,policy=DerivativesPolicy(minimum_chain_rows=5))
    out=v173_payload_overlay(ctx,{"symbol":"NIFTY","iv_skew":999},expiry_day=True)
    assert out["options_context_status"] == "available"
    assert out["max_pain"] == ctx.max_pain
    assert out["call_gamma_wall"] == ctx.call_gamma_wall.strike
    assert out["iv_skew"] == ctx.skew_25d_pct
    assert out["expiry_day"] is True


def test_afre_bridge_uses_capabilities_and_can_block():
    c=chain(ns=NOW-99_000_000_000)
    ctx=build_context(c,greeks(),now_ns=NOW)
    s=PriceScenario(symbol="NIFTY",session_date=date(2026,9,7),as_of_ns=NOW,kind=ScenarioKind.CONTINUATION,side=Side.LONG,entry=100)
    a=DerivativesScenarioController().evaluate(s,ctx)
    caps=afre_capability_payloads(ctx,a)
    assert caps[0]["name"] == "DERIVATIVES_CONTEXT_VALID"
    assert caps[0]["status"] == "BLOCKED"
    assert caps[0]["blocks_new_entry"] is True


def test_store_previous_snapshot_and_iv_history(tmp_path):
    st=DerivativesStore(tmp_path/"d.db")
    c1=chain(ns=NOW-10); c2=chain(ns=NOW)
    st.put_chain(c1); st.put_chain(c2)
    got=st.previous_chain("NIFTY",EXP.isoformat(),NOW)
    assert got and got.snapshot_hash==c1.snapshot_hash
    ctx=build_context(c1,greeks(),now_ns=c1.as_of_ns)
    st.put_context(ctx)
    assert st.iv_history("NIFTY",before_ns=NOW+1)==(ctx.atm_iv_pct,)


def test_openalgo_provider_parses_option_chain_and_batch_greeks():
    def handler(req: httpx.Request):
        body=json.loads(req.content)
        if req.url.path.endswith("/optionchain"):
            return httpx.Response(200,json={"status":"success","underlying":"NIFTY","underlying_ltp":100,"expiry_date":"29SEP26","atm_strike":100,"chain":[
                {"strike":100,"ce":{"symbol":"C100","label":"ATM","ltp":5,"bid":4.9,"ask":5.1,"volume":100,"oi":200,"lotsize":25,"tick_size":.05},
                              "pe":{"symbol":"P100","label":"ATM","ltp":6,"bid":5.9,"ask":6.1,"volume":110,"oi":220,"lotsize":25,"tick_size":.05}}
            ]})
        if req.url.path.endswith("/multioptiongreeks"):
            return httpx.Response(200,json={"status":"success","summary":{"total":2,"success":2,"failed":0},"data":[
                {"status":"success","symbol":"C100","strike":100,"option_type":"CE","days_to_expiry":22,"spot_price":100,"option_price":5,"implied_volatility":20,"greeks":{"delta":.5,"gamma":.02,"theta":-1,"vega":1,"rho":.1}},
                {"status":"success","symbol":"P100","strike":100,"option_type":"PE","days_to_expiry":22,"spot_price":100,"option_price":6,"implied_volatility":21,"greeks":{"delta":-.5,"gamma":.02,"theta":-1,"vega":1,"rho":-.1}}
            ]})
        return httpx.Response(404)
    client=httpx.Client(transport=httpx.MockTransport(handler))
    p=OpenAlgoDataProvider(base_url="http://openalgo.local",api_key="secret",client=client)
    c=p.option_chain(underlying="NIFTY",exchange="NSE_INDEX",expiry_date=EXP,strike_count=1,now_ns=NOW)
    g=p.greeks_for_chain(c)
    assert c.rows[0].ce.symbol=="C100" and len(g)==2
    assert "secret" not in repr(p)


def test_calculation_speed_401_strikes():
    strikes=np.arange(10000,10000+401*50,50,dtype=float)
    rng=np.random.default_rng(7)
    co=rng.integers(1,100000,size=401).astype(float)
    po=rng.integers(1,100000,size=401).astype(float)
    start=time.perf_counter()
    for _ in range(100):
        x=max_pain(strikes,co,po)
    elapsed=time.perf_counter()-start
    assert x is not None
    # Generous CI guard; algorithm should normally be orders of magnitude faster.
    assert elapsed < 1.0

from app.orb.derivatives.replay import ReplayPoint, evaluate_replay, expanding_folds, train_only_dates
from app.orb.derivatives.scenario_catalog import scenario_ids


def test_failure_catalog_is_broad_and_unique():
    ids=scenario_ids()
    assert len(ids) >= 20
    assert len(ids) == len(set(ids))
    assert {"WALL_REJECTION","MAX_PAIN_PIN","FUTURES_DIVERGENCE","STALE_CHAIN","UNKNOWN_DERIVATIVES_REGIME"}.issubset(set(ids))


def test_replay_rejects_future_context_and_preserves_pit():
    ctx=build_context(chain(ns=NOW),greeks(),now_ns=NOW,policy=DerivativesPolicy(minimum_chain_rows=5))
    s=PriceScenario(symbol="NIFTY",session_date=date(2026,9,7),as_of_ns=NOW,kind=ScenarioKind.CONTINUATION,side=Side.LONG,entry=100)
    good=ReplayPoint(date(2026,9,7),NOW, s, ctx)
    bad=ReplayPoint(date(2026,9,7),NOW-1, s, ctx)
    out=evaluate_replay([good,bad])
    assert len(out)==1 and out[0].pit_safe is True


def test_train_only_and_expanding_fold_helpers():
    dates=tuple(date(2026,1,d) for d in range(1,11))
    train,hold=train_only_dates(dates,.2)
    assert train==dates[:8] and hold==dates[8:]
    folds=expanding_folds(train,4)
    assert folds[0][0]==()
    for tr,val in folds[1:]:
        assert max(tr) < min(val)


def test_openalgo_resolves_future_from_master_search_not_symbol_guessing():
    def handler(req: httpx.Request):
        body=json.loads(req.content)
        if req.url.path.endswith('/expiry'):
            assert body['exchange']=='NFO' and body['instrumenttype']=='futures'
            return httpx.Response(200,json={'status':'success','data':['29-SEP-26','27-OCT-26']})
        if req.url.path.endswith('/search'):
            return httpx.Response(200,json={'status':'success','data':[
                {'symbol':'NIFTY29SEP26FUT','name':'NIFTY','exchange':'NFO','expiry':'29-SEP-26','instrumenttype':'FUTIDX','lotsize':65,'tick_size':.10},
                {'symbol':'NIFTY29SEP2610000CE','name':'NIFTY','exchange':'NFO','expiry':'29-SEP-26','instrumenttype':'OPTIDX','lotsize':65,'tick_size':.05},
            ]})
        return httpx.Response(404)
    p=OpenAlgoDataProvider(base_url='http://openalgo.local',api_key='secret',client=httpx.Client(transport=httpx.MockTransport(handler)))
    resolved=p.resolve_nearest_future('NIFTY','NFO',on_or_after=EXP)
    assert resolved==('NIFTY29SEP26FUT',EXP)


def test_assessment_availability_is_latest_input_not_earliest():
    ctx=build_context(chain(ns=NOW-5),greeks(),now_ns=NOW-5,policy=DerivativesPolicy(minimum_chain_rows=5))
    s=PriceScenario(symbol='NIFTY',session_date=date(2026,9,7),as_of_ns=NOW,kind=ScenarioKind.CONTINUATION,side=Side.LONG,entry=100)
    a=DerivativesScenarioController().evaluate(s,ctx)
    assert a.as_of_ns==NOW


def test_runtime_reasoning_exposes_counterfactual_branch_set():
    ctx=build_context(chain(),greeks(),futures=fut(98,1200),previous_futures=fut(100,1000,NOW-5_000_000_000),now_ns=NOW,
                      policy=DerivativesPolicy(minimum_chain_rows=5))
    s=PriceScenario(symbol="NIFTY",session_date=date(2026,9,7),as_of_ns=NOW,kind=ScenarioKind.CONTINUATION,
                    side=Side.LONG,entry=100,target=103,expiry_day=True,chop_risk=True)
    a=DerivativesScenarioController().evaluate(s,ctx)
    ids={b.branch_id for b in a.branches}
    required={
        "WALL_REJECTION_FAILURE","GAMMA_CONFINEMENT_CHOP","EXPIRY_PINNING_CHOP",
        "TARGET_STRETCH_FAILURE","FUTURES_DIVERGENCE_FAILURE","SKEW_TAIL_FAILURE",
        "TERM_STRUCTURE_EVENT_RISK","VOLATILITY_EXHAUSTION","PRICE_CHOP_DOUBLE_STOP",
        "DATA_QUALITY_FAILURE","UNKNOWN_DERIVATIVES_REGIME",
    }
    assert required <= ids
    assert len(a.branches) >= 12
    assert a.trade_allowed is False and a.order_routing_enabled is False
