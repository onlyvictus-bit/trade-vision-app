from __future__ import annotations

"""M3.1.1-D shadow market-structure geometry; zero authority.

Consumes canonical observed/primitive/chart-state contracts. Intent-heavy labels
are deliberately signatures/candidates, never claims about participant intent.
"""
from dataclasses import dataclass
import hashlib, json
from .snapshot_feature_kernel import SnapshotFeatureKernel
from .market_primitive_kernel_v2 import MarketPrimitiveKernelV2
from .canonical_chart_state_v2 import CanonicalChartStateV2

VERSION = "canonical-market-structure.v2"
PRICE_PROFILE_PROXY = "OHLC_RANGE_TPO_PROXY"
VOLUME_PROFILE_PROXY = "BAR_TYPICAL_PRICE_VOLUME_PROFILE_PROXY"
HIERARCHIES = ("MICRO", "LOCAL_SWING", "INTRADAY", "HTF", "SESSION")
LIFECYCLES = ("CREATED", "FORMING", "CONFIRMED", "FRESH", "TOUCHED", "PARTIALLY_MITIGATED", "MITIGATED", "BROKEN", "INVALIDATED", "EXPIRED")

class CanonicalMarketStructureV2Error(ValueError): pass

@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int; timestamp_ns: int; price: float; kind: str; hierarchy: str; lifecycle: str

@dataclass(frozen=True, slots=True)
class StructureSignature:
    name: str; direction: str; availability: str; strength: float | None; lifecycle: str; evidence_kind: str

@dataclass(frozen=True, slots=True)
class CanonicalMarketStructureV2:
    calculation_version: str
    symbol: str; timeframe: str; decision_time_ns: int; source_snapshot_hash: str
    source_feature_kernel_hash: str; source_primitive_hash: str; source_chart_state_hash: str
    swings: tuple[SwingPoint, ...]
    hierarchy_states: tuple[tuple[str, str], ...]
    structural_state: str; structural_direction: str
    latest_break_state: str; range_state: str
    order_block_candidate: StructureSignature
    liquidity_sweep_rejection_signature: StructureSignature
    wyckoff_like_signature: StructureSignature
    price_profile_proxy: str; volume_profile_proxy: str; volume_profile_availability: str
    structure_hash: str
    epistemic_level: str = "INFERRED"; scores_are_uncalibrated: bool = True
    research_only: bool = True; used_for_probability: bool = False; may_set_final_band: bool = False
    may_execute: bool = False; trade_allowed: bool = False; order_routing_enabled: bool = False
    live_trading_blocked: bool = True; human_approval_required: bool = True

    def receipt_summary(self) -> dict[str, object]:
        return {"version": self.calculation_version, "state": self.structural_state,
                "direction": self.structural_direction, "break": self.latest_break_state,
                "profiles": {"price": self.price_profile_proxy, "volume": self.volume_profile_proxy,
                "volume_availability": self.volume_profile_availability},
                "provenance": {"snapshot_hash": self.source_snapshot_hash, "structure_hash": self.structure_hash},
                "authority": {"research_only": True, "may_set_final_band": False, "may_execute": False,
                "trade_allowed": False, "order_routing_enabled": False, "live_trading_blocked": True,
                "human_approval_required": True}}

def build_canonical_market_structure_v2(primitive: MarketPrimitiveKernelV2, observed: SnapshotFeatureKernel,
                                        chart: CanonicalChartStateV2) -> CanonicalMarketStructureV2:
    _validate(primitive, observed, chart)
    h, l, c = observed.vectors.highs, observed.vectors.lows, observed.vectors.closes
    ts = observed.vectors.timestamps_ns
    swings = _swings(h, l, ts)
    direction = _swing_direction(swings)
    state = _state(swings, direction, chart.chop_balance_state)
    break_state = _break_state(h, l, c)
    range_state = "BALANCE" if chart.chop_balance_state in ("balanced", "choppy") else chart.compression_expansion_state.upper()
    atr = primitive.wilder_atr(14).latest
    order = _order_candidate(observed, atr)
    sweep = _sweep_signature(observed, atr)
    wyckoff = _wyckoff_like(sweep, chart)
    volume_availability = "UNAVAILABLE" if primitive.missing_volume_count else "AVAILABLE"
    hierarchy = (("MICRO", direction), ("LOCAL_SWING", direction), ("INTRADAY", state),
                 ("HTF", "UNAVAILABLE_REQUIRES_HTF_CONTEXT"), ("SESSION", "UNAVAILABLE_REQUIRES_SESSION_CONTEXT"))
    payload = {"v": VERSION, "snapshot": primitive.source_snapshot_hash, "swings": [(x.index,x.price,x.kind) for x in swings],
               "direction": direction, "state": state, "break": break_state, "range": range_state,
               "order": (order.direction,order.availability,order.strength), "sweep": (sweep.direction,sweep.availability,sweep.strength),
               "wyckoff": (wyckoff.direction,wyckoff.availability,wyckoff.strength), "volume": volume_availability}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",",":"), allow_nan=False).encode()).hexdigest()
    return CanonicalMarketStructureV2(VERSION, primitive.identity.symbol, primitive.identity.timeframe,
        primitive.identity.decision_time_ns, primitive.source_snapshot_hash, primitive.source_feature_kernel_hash,
        primitive.primitive_hash, chart.chart_state_hash, swings, hierarchy, state, direction, break_state, range_state,
        order, sweep, wyckoff, PRICE_PROFILE_PROXY, VOLUME_PROFILE_PROXY, volume_availability, digest)

def _validate(p,o,ch):
    if p.source_snapshot_hash != o.source_snapshot_hash or p.source_snapshot_hash != ch.source_snapshot_hash: raise CanonicalMarketStructureV2Error("snapshot hash mismatch")
    if p.source_feature_kernel_hash != o.feature_hash or ch.source_feature_kernel_hash != o.feature_hash: raise CanonicalMarketStructureV2Error("feature hash mismatch")
    if ch.source_primitive_hash != p.primitive_hash: raise CanonicalMarketStructureV2Error("primitive hash mismatch")
    if (p.identity.symbol,p.identity.timeframe,p.identity.decision_time_ns)!=(o.identity.symbol,o.identity.timeframe,o.identity.decision_time_ns): raise CanonicalMarketStructureV2Error("causal identity mismatch")

def _swings(h,l,ts):
    out=[]
    for i in range(2,len(h)-2):
        if h[i] > max(h[i-2:i]) and h[i] >= max(h[i+1:i+3]): out.append(SwingPoint(i,ts[i],h[i],"HIGH","LOCAL_SWING","CONFIRMED"))
        if l[i] < min(l[i-2:i]) and l[i] <= min(l[i+1:i+3]): out.append(SwingPoint(i,ts[i],l[i],"LOW","LOCAL_SWING","CONFIRMED"))
    return tuple(out)

def _swing_direction(s):
    hi=[x.price for x in s if x.kind=="HIGH"][-2:]; lo=[x.price for x in s if x.kind=="LOW"][-2:]
    if len(hi)<2 or len(lo)<2: return "UNAVAILABLE"
    if hi[-1]>hi[-2] and lo[-1]>lo[-2]: return "BULLISH"
    if hi[-1]<hi[-2] and lo[-1]<lo[-2]: return "BEARISH"
    return "CONFLICTED"

def _state(s,d,chop):
    if len(s)<4: return "INSUFFICIENT_HISTORY"
    if chop in ("balanced","choppy"): return "BALANCE"
    return "STRUCTURAL_CONTINUATION" if d in ("BULLISH","BEARISH") else "STRUCTURAL_TRANSITION"

def _break_state(h,l,c):
    if len(c)<8: return "INSUFFICIENT_HISTORY"
    ph=max(h[-8:-1]); pl=min(l[-8:-1]); last=c[-1]
    if last>ph: return "BULLISH_STRUCTURAL_BREAK"
    if last<pl: return "BEARISH_STRUCTURAL_BREAK"
    return "NO_CONFIRMED_BREAK"

def _order_candidate(o,atr):
    if len(o.vectors.closes)<4 or atr is None or atr<=0: return StructureSignature("order_block_candidate","NONE","INSUFFICIENT_HISTORY",None,"FORMING","PRICE_ONLY")
    op,cl=o.vectors.opens,o.vectors.closes
    for i in range(len(cl)-2,max(0,len(cl)-12),-1):
        impulse=abs(cl[i+1]-op[i+1])/atr
        if impulse>=.6 and cl[i]<op[i] and cl[i+1]>op[i+1]: return StructureSignature("order_block_candidate","BULLISH","AVAILABLE",min(1.,impulse),"CONFIRMED","PRICE_ONLY")
        if impulse>=.6 and cl[i]>op[i] and cl[i+1]<op[i+1]: return StructureSignature("order_block_candidate","BEARISH","AVAILABLE",min(1.,impulse),"CONFIRMED","PRICE_ONLY")
    return StructureSignature("order_block_candidate","NONE","AVAILABLE",0.,"FORMING","PRICE_ONLY")

def _sweep_signature(o,atr):
    if len(o.vectors.closes)<8 or atr is None or atr<=0: return StructureSignature("liquidity_sweep_rejection_signature","NONE","INSUFFICIENT_HISTORY",None,"FORMING","PRICE_ONLY")
    h,l,c=o.vectors.highs,o.vectors.lows,o.vectors.closes; ph=max(h[-8:-1]); pl=min(l[-8:-1]); tol=.08*atr
    if h[-1]>ph+tol and c[-1]<ph: return StructureSignature("liquidity_sweep_rejection_signature","BEARISH","AVAILABLE",min(1.,(h[-1]-ph)/atr),"CONFIRMED","PRICE_ONLY")
    if l[-1]<pl-tol and c[-1]>pl: return StructureSignature("liquidity_sweep_rejection_signature","BULLISH","AVAILABLE",min(1.,(pl-l[-1])/atr),"CONFIRMED","PRICE_ONLY")
    return StructureSignature("liquidity_sweep_rejection_signature","NONE","AVAILABLE",0.,"FORMING","PRICE_ONLY")

def _wyckoff_like(sweep,chart):
    if sweep.availability!="AVAILABLE": return StructureSignature("wyckoff_like_signature","NONE",sweep.availability,None,"FORMING","PRICE_ONLY")
    if sweep.direction in ("BULLISH","BEARISH") and chart.chop_balance_state in ("balanced","choppy"):
        return StructureSignature("wyckoff_like_signature",sweep.direction,"AVAILABLE",sweep.strength,"CONFIRMED","PRICE_ONLY")
    return StructureSignature("wyckoff_like_signature","NONE","AVAILABLE",0.,"FORMING","PRICE_ONLY")
