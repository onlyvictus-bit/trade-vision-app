from __future__ import annotations
import math
from dataclasses import FrozenInstanceError
from time import perf_counter
import pytest
from app.behavior.decision_spine.canonical_market_structure_v2 import *
from app.behavior.decision_spine.canonical_chart_state_v2 import build_canonical_chart_state_v2
from app.behavior.decision_spine.market_primitive_kernel_v2 import build_market_primitive_kernel_v2
from app.behavior.decision_spine.snapshot_feature_kernel import build_snapshot_feature_kernel
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import CandleBar, ClosedCandleSnapshot
BASE=1_725_858_900_000_000_000

def snap(closes=None, missing=set(), hash="a"*64):
    closes=closes or [100+math.sin(i/2)*2+i*.03 for i in range(60)]; d=timeframe_duration_ns("5m"); rows=[]; prev=closes[0]
    for i,x in enumerate(closes):
        op=prev; rows.append(CandleBar(symbol="RELIANCE",timeframe="5m",timestamp_ns=BASE+i*d,open=op,high=max(op,x)+.2,low=min(op,x)-.2,close=x,volume=None if i in missing else 100000+i*100,source="user_csv",sequence_number=i+1)); prev=x
    end=rows[-1].timestamp_ns+d
    return ClosedCandleSnapshot(snapshot_version="closed-candle-snapshot.v1.87",snapshot_id="d-test",snapshot_hash=hash,symbol="RELIANCE",timeframe="5m",decision_time_ns=end,decision_time="2026-09-08T10:00:00+05:30",timezone_offset_minutes=330,bar_count=len(rows),first_bar_timestamp_ns=rows[0].timestamp_ns,last_bar_timestamp_ns=rows[-1].timestamp_ns,last_bar_close_time_ns=end,closed_ohlcv_bars=rows,source_schema_version="candles.v1",immutable=True,closed_candle_only=True,point_in_time_safe=True)

def build(s=None):
    o=build_snapshot_feature_kernel(s or snap()); p=build_market_primitive_kernel_v2(o); c=build_canonical_chart_state_v2(p,o); return build_canonical_market_structure_v2(p,o,c),p,o,c

def test_d001_zero_authority_and_honest_proxy_names():
    x,*_=build(); assert x.price_profile_proxy=="OHLC_RANGE_TPO_PROXY"; assert x.volume_profile_proxy=="BAR_TYPICAL_PRICE_VOLUME_PROFILE_PROXY"; assert not x.may_execute and not x.may_set_final_band and not x.trade_allowed and x.human_approval_required
    with pytest.raises(FrozenInstanceError): x.structural_state="x"

def test_d002_swing_hierarchy_and_lifecycle_vocabularies_are_canonical():
    x,*_=build(); assert tuple(k for k,_ in x.hierarchy_states)==HIERARCHIES; assert all(s.lifecycle in LIFECYCLES for s in x.swings)

def test_d003_bull_bear_mirror_does_not_turn_persistence_into_direction():
    up=[100+math.sin(i/2)*1.2+i*.12 for i in range(70)]; dn=[200-v for v in up]
    a,*_=build(snap(up,hash="b"*64)); b,*_=build(snap(dn,hash="c"*64)); assert {a.structural_direction,b.structural_direction}<={"BULLISH","BEARISH","CONFLICTED","UNAVAILABLE"}; assert a.structural_direction!=b.structural_direction or a.structural_direction in ("CONFLICTED","UNAVAILABLE")

def test_d004_missing_volume_is_unavailable_not_zero_evidence():
    x,*_=build(snap(missing={59})); assert x.volume_profile_availability=="UNAVAILABLE"; assert x.liquidity_sweep_rejection_signature.evidence_kind=="PRICE_ONLY"

def test_d005_intent_heavy_concepts_are_only_candidates_or_signatures():
    x,*_=build(); assert x.order_block_candidate.name=="order_block_candidate"; assert x.liquidity_sweep_rejection_signature.name=="liquidity_sweep_rejection_signature"; assert x.wyckoff_like_signature.name=="wyckoff_like_signature"

def test_d006_insufficient_history_is_explicit():
    x,*_=build(snap([100+i*.1 for i in range(8)])); assert x.structural_direction=="UNAVAILABLE" or x.structural_state=="INSUFFICIENT_HISTORY"

def test_d007_break_requires_close_beyond_prior_structure():
    xs=[100.0]*12+[101.5]; x,*_=build(snap(xs)); assert x.latest_break_state=="BULLISH_STRUCTURAL_BREAK"

def test_d008_deterministic_replay_hash():
    s=snap(); a,*_=build(s); b,*_=build(s); assert a==b and a.structure_hash==b.structure_hash

def test_d009_causal_snapshot_mismatch_rejected():
    x,p,o,c=build(); o2=build_snapshot_feature_kernel(snap(hash="f"*64));
    with pytest.raises(CanonicalMarketStructureV2Error): build_canonical_market_structure_v2(p,o2,c)

def test_d010_no_probability_or_final_decision_language_in_receipt():
    x,*_=build(); r=str(x.receipt_summary()).lower(); assert "probability" not in r; assert "final_band': true" not in r; assert x.scores_are_uncalibrated

def test_d011_runtime_is_bounded():
    _,p,o,c=build(); t=perf_counter();
    for _ in range(100): build_canonical_market_structure_v2(p,o,c)
    assert perf_counter()-t<2.0
