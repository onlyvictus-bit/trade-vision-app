from __future__ import annotations
import json
from app.behavior.decision_spine.canonical_market_regime import *
H="a"*64

def dims(**kw):
    base=dict(trend="UP",volatility="NORMAL",liquidity="HEALTHY",breadth="BROAD_RISK_ON",index_alignment="UP",sector_alignment="UP",relative_strength_state="STOCK_LEADER",session_phase="MORNING",source_hashes=("b"*64,))
    base.update(kw); return RegimeDimensions(**base)

def build(d,history=None): return build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,d2_snapshot_hash=H,dimensions=d,history=history)

def test_clear_trend():
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims())
    assert r.stable_regime=="TREND_UP" and r.confidence=="HIGH"
def test_clear_chop():
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims(trend="RANGE",volatility="COMPRESSED",breadth="MIXED",index_alignment="FLAT",sector_alignment="FLAT"))
    assert r.stable_regime in {"CHOP","CONFLICTING"}
def test_conflict_preserved():
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims(sector_alignment="DOWN"))
    assert r.confidence=="CONFLICTING" and "INDEX_SECTOR_DIVERGENCE" in r.contradictions
def test_missing_breadth_reduces_confidence():
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims(breadth="UNKNOWN",missing_facts=("BREADTH",)))
    assert r.availability=="DEGRADED" and r.confidence=="LOW"
def test_ood_reduces_authority():
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims(ood=True,novelty_reasons=("UNSUPPORTED_VOLATILITY",)))
    assert r.confidence=="OOD" and r.availability=="DEGRADED"
def test_hysteresis_requires_persistence():
    hist=RegimeHistory("TREND_UP","CHOP",1,3,"c"*64)
    d=dims(trend="RANGE",volatility="COMPRESSED",breadth="BROAD_RISK_ON",index_alignment="FLAT",sector_alignment="FLAT")
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=d,history=hist)
    assert r.stable_regime=="TREND_UP" and r.persistence_count==2
    hist2=RegimeHistory("TREND_UP","CHOP",2,3,"d"*64)
    r2=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=d,history=hist2)
    assert r2.stable_regime=="CHOP"
def test_replay_restart_determinism():
    a=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims())
    b=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims())
    assert a.as_dict()==b.as_dict()
def test_failure_risks():
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims(volatility="EXTREME",liquidity="STRESSED"))
    assert "VOLATILITY_SHOCK_RISK" in r.failure_risks and "LIQUIDITY_FAILURE_RISK" in r.failure_risks
def test_zero_authority_bounded():
    r=build_canonical_market_regime(d2_snapshot_hash=H,decision_time_ns=100,dimensions=dims())
    p=r.as_dict(); assert len(json.dumps(p).encode())<MAX_REGIME_BYTES
    assert not p["may_propose"] and not p["may_veto"] and not p["may_set_final_band"] and not p["may_execute"]
    assert not p["trade_allowed"] and not p["order_routing_enabled"] and p["live_trading_blocked"] and p["human_approval_required"]
