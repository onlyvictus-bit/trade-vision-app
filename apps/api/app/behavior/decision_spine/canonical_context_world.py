from __future__ import annotations

"""M3.2-F deterministic context fusion. Facts only; zero trade authority."""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping, Sequence

CANONICAL_CONTEXT_WORLD_VERSION = "canonical-context-world.v1"
MAX_CONTEXT_WORLD_BYTES = 24_000
MAX_COMPONENT_BYTES = 8_000
Availability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE", "ERROR", "PENDING"]
Confidence = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN", "CONFLICTING", "OOD", "INSUFFICIENT_EVIDENCE"]

class CanonicalContextWorldError(ValueError): pass

@dataclass(frozen=True, slots=True)
class ContextWorldComponent:
    engine_id: str; d2_snapshot_hash: str; decision_time_ns: int; output_hash: str
    availability: Availability; calculation_version: str; summary: Mapping[str, Any]
    source_snapshot_hashes: tuple[str, ...] = (); source_output_hashes: tuple[str, ...] = ()
    supporting_facts: tuple[str, ...] = (); contradictions: tuple[str, ...] = ()
    missing_facts: tuple[str, ...] = (); degraded_facts: tuple[str, ...] = ()
    failure_risks: tuple[str, ...] = (); reason_codes: tuple[str, ...] = (); warnings: tuple[str, ...] = ()
    def as_dict(self) -> dict[str, Any]:
        d=asdict(self); d["summary"]=dict(self.summary); return d

@dataclass(frozen=True, slots=True)
class CanonicalContextWorld:
    engine_id: str; calculation_version: str; d2_snapshot_hash: str; decision_time_ns: int
    session_hash: str; index_hash: str; sector_hash: str; relative_strength_hash: str; regime_hash: str
    source_snapshot_hashes: tuple[str, ...]; source_output_hashes: tuple[str, ...]
    availability: Availability; quality: str; confidence: Confidence
    supporting_facts: tuple[str, ...]; contradictions: tuple[str, ...]; missing_facts: tuple[str, ...]
    degraded_facts: tuple[str, ...]; failure_risks: tuple[str, ...]; reason_codes: tuple[str, ...]; warnings: tuple[str, ...]
    components: tuple[ContextWorldComponent, ...]; output_hash: str
    used_for_probability: bool=False; may_propose: bool=False; may_veto: bool=False; may_downgrade: bool=False
    may_set_final_band: bool=False; may_execute: bool=False; trade_allowed: bool=False; order_routing_enabled: bool=False
    live_trading_blocked: bool=True; human_approval_required: bool=True
    def as_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True, slots=True)
class CanonicalContextReceipt:
    engine_id: str; source_snapshot_hash: str; output_hash: str; status: str; engine_version: str
    output_summary: Mapping[str, Any]; warnings: tuple[str, ...]=(); used_for_probability: bool=False


def component_from_result(*, engine_id: str, result: Any, summary: Mapping[str, Any], source_snapshot_hashes: Sequence[str]=(), source_output_hashes: Sequence[str]=(), supporting_facts: Sequence[str]=(), contradictions: Sequence[str]=(), missing_facts: Sequence[str]=(), degraded_facts: Sequence[str]=(), failure_risks: Sequence[str]=(), reason_codes: Sequence[str]=(), warnings: Sequence[str]=()) -> ContextWorldComponent:
    engine=str(engine_id).strip().upper()
    if engine not in {"SESSION_MEMORY","INDEX_CONTEXT","SECTOR_CONTEXT","RELATIVE_STRENGTH","MARKET_REGIME"}: raise CanonicalContextWorldError(f"UNSUPPORTED_CONTEXT_ENGINE:{engine}")
    root=str(_get(result,"d2_snapshot_hash","")).lower(); out=str(_get(result,"output_hash","")).lower(); _hash(root,"d2_snapshot_hash"); _hash(out,"output_hash")
    when=int(_get(result,"decision_time_ns",0)); availability=str(_get(result,"availability","UNAVAILABLE")).upper(); version=str(_get(result,"calculation_version","")).strip()
    if when<=0: raise CanonicalContextWorldError(f"INVALID_DECISION_TIME:{engine}")
    if availability not in {"AVAILABLE","DEGRADED","UNAVAILABLE","ERROR","PENDING"}: raise CanonicalContextWorldError(f"INVALID_AVAILABILITY:{engine}")
    if not version: raise CanonicalContextWorldError(f"MISSING_CALCULATION_VERSION:{engine}")
    sm=_mapping(summary)
    if len(_json(sm))>MAX_COMPONENT_BYTES: raise CanonicalContextWorldError(f"BOUNDED_COMPONENT_EXCEEDED:{engine}")
    return ContextWorldComponent(engine,root,when,out,availability,version,sm,_hashes(source_snapshot_hashes),_hashes(source_output_hashes),_strings(supporting_facts),_strings(contradictions),_strings(missing_facts),_strings(degraded_facts),_strings(failure_risks),_strings(reason_codes),_strings(warnings))


def build_canonical_context_world(*, d2_snapshot_hash: str, decision_time_ns: int, session: ContextWorldComponent, index_context: ContextWorldComponent, sector_context: ContextWorldComponent, relative_strength: ContextWorldComponent, market_regime: ContextWorldComponent) -> CanonicalContextWorld:
    root=str(d2_snapshot_hash).lower(); _hash(root,"d2_snapshot_hash")
    if decision_time_ns<=0: raise CanonicalContextWorldError("INVALID_DECISION_TIME")
    items=(session,index_context,sector_context,relative_strength,market_regime); by_id={x.engine_id:x for x in items}
    if set(by_id)!={"SESSION_MEMORY","INDEX_CONTEXT","SECTOR_CONTEXT","RELATIVE_STRENGTH","MARKET_REGIME"} or len(by_id)!=5: raise CanonicalContextWorldError("CONTEXT_COMPONENT_SET_INVALID")
    components=tuple(by_id[k] for k in sorted(by_id))
    for x in components:
        if x.d2_snapshot_hash!=root: raise CanonicalContextWorldError(f"SNAPSHOT_MISMATCH:{x.engine_id}")
        if x.decision_time_ns!=decision_time_ns: raise CanonicalContextWorldError(f"DECISION_TIME_MISMATCH:{x.engine_id}")
    support=_union(x.supporting_facts for x in components); contradictions=_union(x.contradictions for x in components); missing=_union(x.missing_facts for x in components); degraded=_union(x.degraded_facts for x in components); risks=_union(x.failure_risks for x in components); reasons=_union(x.reason_codes for x in components); warnings=_union(x.warnings for x in components)
    snapshots=_hashes(v for x in components for v in x.source_snapshot_hashes); outputs=_hashes([x.output_hash for x in components]+[v for x in components for v in x.source_output_hashes])
    availability=_availability([x.availability for x in components]); rc=str(market_regime.summary.get("confidence","UNKNOWN")).upper(); allowed={"HIGH","MEDIUM","LOW","UNKNOWN","CONFLICTING","OOD","INSUFFICIENT_EVIDENCE"}; rc=rc if rc in allowed else "UNKNOWN"
    confidence: Confidence = "OOD" if rc=="OOD" else "CONFLICTING" if contradictions else "INSUFFICIENT_EVIDENCE" if availability=="UNAVAILABLE" else "LOW" if availability!="AVAILABLE" else rc  # type: ignore[assignment]
    n=sum(x.availability=="AVAILABLE" for x in components); quality="COMPLETE" if n==5 else "PARTIAL_HIGH_COVERAGE" if n>=3 else "PARTIAL" if n else "INSUFFICIENT"
    hashes={x.engine_id:x.output_hash for x in components}; seed={"version":CANONICAL_CONTEXT_WORLD_VERSION,"d2":root,"t":decision_time_ns,"components":hashes,"source_snapshot_hashes":snapshots,"source_output_hashes":outputs,"availability":availability,"quality":quality,"confidence":confidence,"support":support,"contradictions":contradictions,"missing":missing,"degraded":degraded,"risks":risks,"reasons":reasons,"warnings":warnings}
    world=CanonicalContextWorld("CONTEXT_WORLD",CANONICAL_CONTEXT_WORLD_VERSION,root,decision_time_ns,hashes["SESSION_MEMORY"],hashes["INDEX_CONTEXT"],hashes["SECTOR_CONTEXT"],hashes["RELATIVE_STRENGTH"],hashes["MARKET_REGIME"],snapshots,outputs,availability,quality,confidence,support,contradictions,missing,degraded,risks,reasons,warnings,components,_stable(seed))
    if len(_json(world.as_dict()))>MAX_CONTEXT_WORLD_BYTES: raise CanonicalContextWorldError("BOUNDED_CONTEXT_WORLD_EXCEEDED")
    return world


def build_context_receipts(world: CanonicalContextWorld) -> tuple[CanonicalContextReceipt,...]:
    status={"AVAILABLE":"completed","DEGRADED":"degraded","UNAVAILABLE":"degraded","ERROR":"degraded","PENDING":"degraded"}; out=[]
    for x in world.components:
        sm=dict(x.summary); sm.update({"canonical_context_world":True,"canonical_context_world_hash":world.output_hash,"canonical_availability":x.availability,"component_output_hash":x.output_hash,"supporting_facts":list(x.supporting_facts),"contradictions":list(x.contradictions),"missing_facts":list(x.missing_facts),"degraded_facts":list(x.degraded_facts),"failure_risks":list(x.failure_risks),"reason_codes":list(x.reason_codes),"used_for_probability":False,"may_propose":False,"may_veto":False,"may_downgrade":False,"may_set_final_band":False,"may_execute":False,"trade_allowed":False,"order_routing_enabled":False,"live_trading_blocked":True,"human_approval_required":True})
        if len(_json(sm))>MAX_COMPONENT_BYTES: raise CanonicalContextWorldError(f"BOUNDED_RECEIPT_EXCEEDED:{x.engine_id}")
        out.append(CanonicalContextReceipt(x.engine_id,world.d2_snapshot_hash,x.output_hash,status[x.availability],x.calculation_version,_mapping(sm),x.warnings))
    return tuple(sorted(out,key=lambda x:x.engine_id))


def _availability(states: Sequence[str]) -> Availability:
    s=[str(v).upper() for v in states]
    if "ERROR" in s:return "ERROR"
    if all(v=="UNAVAILABLE" for v in s):return "UNAVAILABLE"
    if "PENDING" in s and all(v in {"PENDING","UNAVAILABLE"} for v in s):return "PENDING"
    if any(v in {"DEGRADED","UNAVAILABLE","PENDING"} for v in s):return "DEGRADED"
    return "AVAILABLE"
def _strings(values: Sequence[str])->tuple[str,...]:
    out=tuple(sorted({str(v).strip() for v in values if str(v).strip()}))
    if any(len(v)>240 for v in out):raise CanonicalContextWorldError("CONTEXT_FACT_TOO_LONG")
    return out
def _union(groups: Any)->tuple[str,...]:return tuple(sorted({str(v) for g in groups for v in g if str(v)}))
def _hashes(values: Any)->tuple[str,...]:
    out=tuple(sorted({str(v).lower() for v in values if str(v)}))
    for v in out:_hash(v,"source_hash")
    return out
def _hash(v:str,field:str)->None:
    if len(v)!=64 or any(c not in "0123456789abcdefABCDEF" for c in v):raise CanonicalContextWorldError(f"INVALID_HASH:{field}")
def _mapping(v:Mapping[str,Any])->dict[str,Any]:return json.loads(json.dumps(dict(v),sort_keys=True,default=str))
def _json(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()
def _stable(v:Any)->str:return hashlib.sha256(_json(v)).hexdigest()
def _get(v:Any,k:str,d:Any=None)->Any:return v.get(k,d) if isinstance(v,Mapping) else getattr(v,k,d)
