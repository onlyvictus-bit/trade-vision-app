from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.behavior.decision_spine.canonical_context_world import (
    MAX_CONTEXT_WORLD_BYTES,
    CanonicalContextWorldError,
    build_canonical_context_world,
    build_context_receipts,
    component_from_result,
)

H="a"*64
T=1_780_000_000_000_000_000

@dataclass(frozen=True)
class R:
    d2_snapshot_hash: str=H
    decision_time_ns: int=T
    output_hash: str="b"*64
    availability: str="AVAILABLE"
    calculation_version: str="test.v1"

def c(engine: str, *, result: R|None=None, **kw):
    return component_from_result(engine_id=engine,result=result or R(),summary={"confidence":"HIGH","fact":engine},**kw)

def world(**overrides):
    parts={"session":c("SESSION_MEMORY"),"index_context":c("INDEX_CONTEXT"),"sector_context":c("SECTOR_CONTEXT"),"relative_strength":c("RELATIVE_STRENGTH"),"market_regime":c("MARKET_REGIME")}; parts.update(overrides)
    return build_canonical_context_world(d2_snapshot_hash=H,decision_time_ns=T,**parts)

def test_complete_world_is_deterministic_bounded_and_zero_authority():
    a=world(); b=world()
    assert a.output_hash==b.output_hash and a.availability=="AVAILABLE" and a.quality=="COMPLETE"
    assert not any((a.used_for_probability,a.may_propose,a.may_veto,a.may_downgrade,a.may_set_final_band,a.may_execute,a.trade_allowed,a.order_routing_enabled))
    assert a.live_trading_blocked and a.human_approval_required
    import json
    assert len(json.dumps(a.as_dict(),sort_keys=True,default=str).encode()) <= MAX_CONTEXT_WORLD_BYTES

def test_order_independent_fact_sets_and_source_hashes():
    x=c("INDEX_CONTEXT",supporting_facts=("B","A","A"),source_snapshot_hashes=("2"*64,"1"*64))
    y=c("INDEX_CONTEXT",supporting_facts=("A","B"),source_snapshot_hashes=("1"*64,"2"*64))
    assert world(index_context=x).output_hash==world(index_context=y).output_hash

def test_snapshot_mismatch_fails_closed():
    bad=c("SECTOR_CONTEXT",result=R(d2_snapshot_hash="c"*64))
    with pytest.raises(CanonicalContextWorldError,match="SNAPSHOT_MISMATCH"):
        world(sector_context=bad)

def test_decision_time_mismatch_fails_closed():
    bad=c("INDEX_CONTEXT",result=R(decision_time_ns=T+1))
    with pytest.raises(CanonicalContextWorldError,match="DECISION_TIME_MISMATCH"):
        world(index_context=bad)

def test_missing_and_degraded_are_not_neutralized():
    missing=c("SECTOR_CONTEXT",result=R(availability="UNAVAILABLE"),missing_facts=("SECTOR_MISSING",))
    w=world(sector_context=missing)
    assert w.availability=="DEGRADED" and w.quality!="COMPLETE" and w.confidence=="LOW"
    assert "SECTOR_MISSING" in w.missing_facts

def test_contradictions_are_preserved_and_dominate_confidence():
    x=c("INDEX_CONTEXT",contradictions=("INDEX_SECTOR_DIVERGENCE",),supporting_facts=("INDEX_UP",))
    w=world(index_context=x)
    assert w.confidence=="CONFLICTING" and "INDEX_SECTOR_DIVERGENCE" in w.contradictions and "INDEX_UP" in w.supporting_facts

def test_ood_regime_is_preserved_without_weighted_score():
    r=component_from_result(engine_id="MARKET_REGIME",result=R(),summary={"confidence":"OOD","stable_regime":"OOD"},failure_risks=("NOVEL_CONTEXT",))
    w=world(market_regime=r)
    assert w.confidence=="OOD" and "NOVEL_CONTEXT" in w.failure_risks
    assert "score" not in w.as_dict() and "weighted_score" not in w.as_dict()

def test_duplicate_engine_identity_fails_closed():
    with pytest.raises(CanonicalContextWorldError,match="CONTEXT_COMPONENT_SET_INVALID"):
        build_canonical_context_world(d2_snapshot_hash=H,decision_time_ns=T,session=c("SESSION_MEMORY"),index_context=c("INDEX_CONTEXT"),sector_context=c("INDEX_CONTEXT"),relative_strength=c("RELATIVE_STRENGTH"),market_regime=c("MARKET_REGIME"))

def test_receipts_preserve_safety_and_canonical_lineage():
    w=world(); receipts=build_context_receipts(w)
    assert [r.engine_id for r in receipts]==sorted(r.engine_id for r in receipts)
    for r in receipts:
        s=r.output_summary
        assert s["canonical_context_world_hash"]==w.output_hash and s["used_for_probability"] is False
        assert s["may_set_final_band"] is False and s["may_execute"] is False
        assert s["trade_allowed"] is False and s["order_routing_enabled"] is False
        assert s["live_trading_blocked"] is True and s["human_approval_required"] is True

def test_invalid_hash_and_oversized_fact_fail_closed():
    with pytest.raises(CanonicalContextWorldError,match="INVALID_HASH"):
        c("INDEX_CONTEXT",source_snapshot_hashes=("bad",))
    with pytest.raises(CanonicalContextWorldError,match="CONTEXT_FACT_TOO_LONG"):
        c("INDEX_CONTEXT",warnings=("x"*241,))
