from __future__ import annotations

"""M3.2-E deterministic market-regime evidence. Facts only; zero trade authority."""
import hashlib, json
from dataclasses import asdict, dataclass
from typing import Any, Literal, Sequence

REGIME_VERSION = "canonical-market-regime.v1"
HYSTERESIS_VERSION = "regime-hysteresis.v1"
MAX_REGIME_BYTES = 16000
Trend = Literal["UP","DOWN","RANGE","TRANSITION","UNKNOWN"]
Volatility = Literal["COMPRESSED","NORMAL","EXPANDING","EXTREME","UNKNOWN"]
Liquidity = Literal["HEALTHY","THIN","STRESSED","UNKNOWN"]
Breadth = Literal["BROAD_RISK_ON","NARROW_RISK_ON","MIXED","RISK_OFF","UNKNOWN"]
Confidence = Literal["HIGH","MEDIUM","LOW","UNKNOWN","CONFLICTING","OOD","INSUFFICIENT_EVIDENCE"]
Availability = Literal["AVAILABLE","DEGRADED","UNAVAILABLE"]

class CanonicalMarketRegimeError(ValueError): pass

@dataclass(frozen=True, slots=True)
class RegimeDimensions:
    trend: Trend; volatility: Volatility; liquidity: Liquidity; breadth: Breadth
    index_alignment: str; sector_alignment: str; relative_strength_state: str; session_phase: str
    source_hashes: tuple[str,...]; missing_facts: tuple[str,...]=(); degraded_facts: tuple[str,...]=()
    ood: bool=False; novelty_reasons: tuple[str,...]=()
    def as_dict(self)->dict[str,Any]:
        d=asdict(self)
        for k in ("source_hashes","missing_facts","degraded_facts","novelty_reasons"): d[k]=list(d[k])
        return d

@dataclass(frozen=True, slots=True)
class RegimeHistory:
    stable_regime: str
    candidate_regime: str|None
    persistence_count: int
    minimum_confirmation: int
    history_hash: str
    hysteresis_version: str=HYSTERESIS_VERSION

@dataclass(frozen=True, slots=True)
class CanonicalMarketRegime:
    d2_snapshot_hash:str; decision_time_ns:int; availability:Availability; stable_regime:str
    transition_candidate:str|None; persistence_count:int; minimum_confirmation:int
    confidence:Confidence; contradictions:tuple[str,...]; supporting_facts:tuple[str,...]
    missing_facts:tuple[str,...]; degraded_facts:tuple[str,...]; failure_risks:tuple[str,...]
    ood:bool; novelty_reasons:tuple[str,...]; source_hashes:tuple[str,...]; output_hash:str
    calculation_version:str=REGIME_VERSION; used_for_probability:bool=False; may_propose:bool=False
    may_veto:bool=False; may_downgrade:bool=False; may_set_final_band:bool=False; may_execute:bool=False
    trade_allowed:bool=False; order_routing_enabled:bool=False; live_trading_blocked:bool=True
    human_approval_required:bool=True
    def as_dict(self)->dict[str,Any]:
        d=asdict(self)
        for k in ("contradictions","supporting_facts","missing_facts","degraded_facts","failure_risks","novelty_reasons","source_hashes"): d[k]=list(d[k])
        return d

def build_canonical_market_regime(*, d2_snapshot_hash:str, decision_time_ns:int, dimensions:RegimeDimensions,
                                  history:RegimeHistory|None=None, minimum_confirmation:int=3)->CanonicalMarketRegime:
    _hash(d2_snapshot_hash); 
    if decision_time_ns<=0: raise CanonicalMarketRegimeError("INVALID_DECISION_TIME")
    if minimum_confirmation<1: raise CanonicalMarketRegimeError("INVALID_CONFIRMATION")
    hashes=tuple(sorted(set(dimensions.source_hashes)))
    for h in hashes: _hash(h)
    contradictions=[]; support=[]; risks=[]
    if dimensions.index_alignment=="UP" and dimensions.sector_alignment=="DOWN": contradictions.append("INDEX_SECTOR_DIVERGENCE")
    if dimensions.index_alignment=="DOWN" and dimensions.sector_alignment=="UP": contradictions.append("INDEX_SECTOR_DIVERGENCE")
    if dimensions.breadth=="MIXED": contradictions.append("BREADTH_DIVERGENCE")
    if dimensions.trend in {"UP","DOWN"} and dimensions.volatility=="COMPRESSED": risks.append("TREND_EXHAUSTION_RISK")
    if dimensions.volatility in {"EXPANDING","EXTREME"}: risks.append("VOLATILITY_SHOCK_RISK")
    if dimensions.liquidity in {"THIN","STRESSED"}: risks.append("LIQUIDITY_FAILURE_RISK")
    if "INDEX_SECTOR_DIVERGENCE" in contradictions: risks.append("INDEX_SECTOR_DIVERGENCE")
    if "BREADTH_DIVERGENCE" in contradictions: risks.append("BREADTH_DIVERGENCE")
    if dimensions.session_phase in {"OPENING_TRANSITION","CLOSING_TRANSITION","UNKNOWN"}: risks.append("SESSION_TRANSITION_RISK")
    candidate=_candidate(dimensions, contradictions)
    stable=candidate; persistence=minimum_confirmation
    if history is not None:
        _hash(history.history_hash)
        if history.minimum_confirmation<1 or history.persistence_count<0: raise CanonicalMarketRegimeError("INVALID_HISTORY")
        if candidate==history.stable_regime:
            stable=history.stable_regime; persistence=0
        elif candidate==history.candidate_regime:
            persistence=history.persistence_count+1
            stable=candidate if persistence>=minimum_confirmation else history.stable_regime
        else:
            persistence=1; stable=history.stable_regime
    missing=tuple(sorted(set(dimensions.missing_facts))); degraded=tuple(sorted(set(dimensions.degraded_facts)))
    coverage=8-len(missing)-len(degraded)
    if dimensions.ood: confidence:Confidence="OOD"
    elif not hashes or coverage<=2: confidence="INSUFFICIENT_EVIDENCE"
    elif contradictions: confidence="CONFLICTING"
    elif missing or degraded: confidence="LOW"
    elif candidate in {"UNKNOWN","CONFLICTING"}: confidence="UNKNOWN"
    elif coverage>=8: confidence="HIGH"
    else: confidence="MEDIUM"
    availability:Availability="AVAILABLE"
    if not hashes or confidence=="INSUFFICIENT_EVIDENCE": availability="UNAVAILABLE"
    elif missing or degraded or contradictions or dimensions.ood: availability="DEGRADED"
    support.extend(_support(dimensions))
    seed={"v":REGIME_VERSION,"d2":d2_snapshot_hash.lower(),"t":decision_time_ns,"dimensions":dimensions.as_dict(),"stable":stable,"candidate":candidate,"persistence":persistence,"min":minimum_confirmation,"confidence":confidence,"contradictions":sorted(set(contradictions)),"risks":sorted(set(risks)),"history":history.history_hash if history else None}
    r=CanonicalMarketRegime(d2_snapshot_hash.lower(),decision_time_ns,availability,stable,candidate if stable!=candidate else None,persistence,minimum_confirmation,confidence,tuple(sorted(set(contradictions))),tuple(sorted(set(support))),missing,degraded,tuple(sorted(set(risks))),dimensions.ood,tuple(sorted(set(dimensions.novelty_reasons))),hashes,_stable(seed))
    if len(json.dumps(r.as_dict(),sort_keys=True,separators=(",",":")).encode())>MAX_REGIME_BYTES: raise CanonicalMarketRegimeError("BOUNDED_REGIME_EXCEEDED")
    return r

def _candidate(d:RegimeDimensions,c:Sequence[str])->str:
    if d.ood: return "OOD"
    if c: return "CONFLICTING"
    if d.trend=="UP" and d.index_alignment=="UP" and d.sector_alignment=="UP": return "TREND_UP"
    if d.trend=="DOWN" and d.index_alignment=="DOWN" and d.sector_alignment=="DOWN": return "TREND_DOWN"
    if d.trend=="RANGE" or (d.volatility=="COMPRESSED" and d.breadth in {"MIXED","UNKNOWN"}): return "CHOP"
    if d.trend=="TRANSITION": return "TRANSITION"
    return "UNKNOWN"

def _support(d:RegimeDimensions)->list[str]:
    out=[]
    if d.trend!="UNKNOWN": out.append("TREND_OBSERVED")
    if d.volatility!="UNKNOWN": out.append("VOLATILITY_OBSERVED")
    if d.liquidity!="UNKNOWN": out.append("LIQUIDITY_OBSERVED")
    if d.breadth!="UNKNOWN": out.append("BREADTH_OBSERVED")
    if d.relative_strength_state not in {"UNKNOWN","INSUFFICIENT_EVIDENCE"}: out.append("RELATIVE_STRENGTH_OBSERVED")
    return out

def _hash(v:str)->None:
    if not isinstance(v,str) or len(v)!=64 or any(c not in "0123456789abcdefABCDEF" for c in v): raise CanonicalMarketRegimeError("INVALID_HASH")
def _stable(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
