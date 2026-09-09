from __future__ import annotations

"""M3.2-F canonical context fusion.

This module composes already-canonical M3.2 facts into one bounded context world.
It never converts context into a trade score, never executes specialists, and
never claims proposal/final-band/execution authority.

The composer is deliberately loss-averse: supporting facts, contradictions,
missing/degraded facts and failure risks remain independently addressable so
later hypothesis/counterfactual reasoning can withdraw only the conclusions
whose upstream evidence actually changed.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping, Sequence

from .canonical_market_regime import CanonicalMarketRegime
from .canonical_relative_strength import CanonicalRelativeStrength


CANONICAL_CONTEXT_WORLD_VERSION = "canonical-context-world.v1"
CONTEXT_WORLD_RECEIPT_VERSION = "canonical-context-world-receipt.v1"
MAX_CONTEXT_WORLD_BYTES = 24_000
MAX_COMPONENT_SUMMARY_BYTES = 8_000

ContextWorldAvailability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE", "ERROR", "PENDING"]
ContextWorldConfidence = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN", "CONFLICTING", "OOD", "INSUFFICIENT_EVIDENCE"]


class CanonicalContextWorldError(ValueError):
    """Raised when M3.2-F composition cannot prove one causal context world."""


@dataclass(frozen=True, slots=True)
class ContextWorldComponent:
    engine_id: str
    d2_snapshot_hash: str
    decision_time_ns: int
    output_hash: str
    availability: str
    calculation_version: str
    summary: Mapping[str, Any]
    source_snapshot_hashes: tuple[str, ...] = ()
    source_output_hashes: tuple[str, ...] = ()
    supporting_facts: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    missing_facts: tuple[str, ...] = ()
    degraded_facts: tuple[str, ...] = ()
    failure_risks: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["summary"] = dict(self.summary)
        for key in (
            "source_snapshot_hashes",
            "source_output_hashes",
            "supporting_facts",
            "contradictions",
            "missing_facts",
            "degraded_facts",
            "failure_risks",
            "reason_codes",
            "warnings",
        ):
            payload[key] = list(payload[key])
        return payload


@dataclass(frozen=True, slots=True)
class CanonicalContextWorld:
    d2_snapshot_hash: str
    decision_time_ns: int
    availability: ContextWorldAvailability
    quality: str
    confidence: ContextWorldConfidence
    session_hash: str
    index_sector_hash: str
    relative_strength_hash: str
    regime_hash: str
    source_snapshot_hashes: tuple[str, ...]
    source_output_hashes: tuple[str, ...]
    supporting_facts: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_facts: tuple[str, ...]
    degraded_facts: tuple[str, ...]
    failure_risks: tuple[str, ...]
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    components: tuple[ContextWorldComponent, ...]
    output_hash: str
    calculation_version: str = CANONICAL_CONTEXT_WORLD_VERSION
    used_for_probability: bool = False
    may_propose: bool = False
    may_veto: bool = False
    may_downgrade: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    human_approval_required: bool = True

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["components"] = [item.as_dict() for item in self.components]
        for key in (
            "source_snapshot_hashes",
            "source_output_hashes",
            "supporting_facts",
            "contradictions",
            "missing_facts",
            "degraded_facts",
            "failure_risks",
            "reason_codes",
            "warnings",
        ):
            payload[key] = list(payload[key])
        return payload


@dataclass(frozen=True, slots=True)
class CanonicalContextReceipt:
    engine_id: str
    source_snapshot_hash: str
    output_hash: str
    status: str
    engine_version: str
    output_summary: Mapping[str, Any]
    warnings: tuple[str, ...] = ()
    used_for_probability: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "source_snapshot_hash": self.source_snapshot_hash,
            "output_hash": self.output_hash,
            "status": self.status,
            "engine_version": self.engine_version,
            "output_summary": dict(self.output_summary),
            "warnings": list(self.warnings),
            "used_for_probability": False,
        }


def component_from_result(
    *,
    engine_id: str,
    result: Any,
    summary: Mapping[str, Any],
    source_snapshot_hashes: Sequence[str] = (),
    source_output_hashes: Sequence[str] = (),
    supporting_facts: Sequence[str] = (),
    contradictions: Sequence[str] = (),
    missing_facts: Sequence[str] = (),
    degraded_facts: Sequence[str] = (),
    failure_risks: Sequence[str] = (),
    reason_codes: Sequence[str] = (),
    warnings: Sequence[str] = (),
) -> ContextWorldComponent:
    """Freeze one already-computed M3.2 specialist output for composition."""

    normalized_engine = str(engine_id).strip().upper()
    if normalized_engine not in {
        "SESSION_MEMORY",
        "INDEX_CONTEXT",
        "SECTOR_CONTEXT",
        "RELATIVE_STRENGTH",
        "MARKET_REGIME",
    }:
        raise CanonicalContextWorldError(f"UNSUPPORTED_CONTEXT_ENGINE:{normalized_engine}")

    d2_snapshot_hash = str(_get(result, "d2_snapshot_hash", "")).lower()
    decision_time_ns = int(_get(result, "decision_time_ns", 0))
    output_hash = str(_get(result, "output_hash", "")).lower()
    availability = str(_get(result, "availability", "UNAVAILABLE")).upper()
    calculation_version = str(_get(result, "calculation_version", "unknown"))

    _hash(d2_snapshot_hash, "d2_snapshot_hash")
    _hash(output_hash, "output_hash")
    if decision_time_ns <= 0:
        raise CanonicalContextWorldError(f"INVALID_DECISION_TIME:{normalized_engine}")
    if availability not in {"AVAILABLE", "DEGRADED", "UNAVAILABLE", "ERROR", "PENDING"}:
        raise CanonicalContextWorldError(f"INVALID_AVAILABILITY:{normalized_engine}")
    if not calculation_version.strip():
        raise CanonicalContextWorldError(f"MISSING_CALCULATION_VERSION:{normalized_engine}")
    _bounded_mapping(summary, f"{normalized_engine}.summary")

    source_snapshot_tuple = _hash_tuple(source_snapshot_hashes, "source_snapshot_hash")
    source_output_tuple = _hash_tuple(source_output_hashes, "source_output_hash")

    return ContextWorldComponent(
        engine_id=normalized_engine,
        d2_snapshot_hash=d2_snapshot_hash,
        decision_time_ns=decision_time_ns,
        output_hash=output_hash,
        availability=availability,
        calculation_version=calculation_version,
        summary=_canonical_mapping(summary),
        source_snapshot_hashes=source_snapshot_tuple,
        source_output_hashes=source_output_tuple,
        supporting_facts=_strings(supporting_facts),
        contradictions=_strings(contradictions),
        missing_facts=_strings(missing_facts),
        degraded_facts=_strings(degraded_facts),
        failure_risks=_strings(failure_risks),
        reason_codes=_strings(reason_codes),
        warnings=_strings(warnings),
    )


def build_canonical_context_world(
    *,
    d2_snapshot_hash: str,
    decision_time_ns: int,
    session: ContextWorldComponent,
    index_context: ContextWorldComponent,
    sector_context: ContextWorldComponent,
    relative_strength: ContextWorldComponent,
    market_regime: ContextWorldComponent,
) -> CanonicalContextWorld:
    """Compose canonical session/index/sector/RS/regime facts without scoring them."""

    root = str(d2_snapshot_hash).lower()
    _hash(root, "d2_snapshot_hash")
    if decision_time_ns <= 0:
        raise CanonicalContextWorldError("INVALID_DECISION_TIME")

    components = tuple(
        sorted(
            (session, index_context, sector_context, relative_strength, market_regime),
            key=lambda item: item.engine_id,
        )
    )
    expected = {
        "SESSION_MEMORY",
        "INDEX_CONTEXT",
        "SECTOR_CONTEXT",
        "RELATIVE_STRENGTH",
        "MARKET_REGIME",
    }
    actual = {item.engine_id for item in components}
    if actual != expected or len(components) != len(expected):
        raise CanonicalContextWorldError("CONTEXT_COMPONENT_SET_INVALID")

    for item in components:
        if item.d2_snapshot_hash != root:
            raise CanonicalContextWorldError(f"SNAPSHOT_MISMATCH:{item.engine_id}")
        if item.decision_time_ns != decision_time_ns:
            raise CanonicalContextWorldError(f"DECISION_TIME_MISMATCH:{item.engine_id}")

    supporting = _union(item.supporting_facts for item in components)
    contradictions = _union(item.contradictions for item in components)
    missing = _union(item.missing_facts for item in components)
    degraded = _union(item.degraded_facts for item in components)
    failure_risks = _union(item.failure_risks for item in components)
    reasons = _union(item.reason_codes for item in components)
    warnings = _union(item.warnings for item in components)

    source_snapshot_hashes = _union_hashes(item.source_snapshot_hashes for item in components)
    source_output_hashes = tuple(sorted({item.output_hash for item in components} | {
        value for item in components for value in item.source_output_hashes
    }))

    availability = _availability(item.availability for item in components)
    regime_confidence = str(market_regime.summary.get("confidence", "UNKNOWN")).upper()
    if regime_confidence not in {
        "HIGH", "MEDIUM", "LOW", "UNKNOWN", "CONFLICTING", "OOD", "INSUFFICIENT_EVIDENCE"
    }:
        regime_confidence = "UNKNOWN"

    if "OOD" == regime_confidence:
        confidence: ContextWorldConfidence = "OOD"
    elif contradictions:
        confidence = "CONFLICTING"
    elif availability == "UNAVAILABLE":
        confidence = "INSUFFICIENT_EVIDENCE"
    elif availability in {"DEGRADED", "PENDING", "ERROR"}:
        confidence = "LOW" if regime_confidence not in {"OOD", "CONFLICTING"} else regime_confidence  # type: ignore[assignment]
    else:
        confidence = regime_confidence  # type: ignore[assignment]

    available_count = sum(item.availability == "AVAILABLE" for item in components)
    degraded_count = sum(item.availability == "DEGRADED" for item in components)
    if availability == "AVAILABLE" and available_count == len(components):
        quality = "COMPLETE"
    elif available_count >= 3 and availability == "DEGRADED":
        quality = "PARTIAL_HIGH_COVERAGE"
    elif available_count:
        quality = "PARTIAL"
    else:
        quality = "INSUFFICIENT"

    seed = {
        "version": CANONICAL_CONTEXT_WORLD_VERSION,
        "d2_snapshot_hash": root,
        "decision_time_ns": decision_time_ns,
        "component_hashes": {item.engine_id: item.output_hash for item in components},
        "source_snapshot_hashes": source_snapshot_hashes,
        "source_output_hashes": source_output_hashes,
        "availability": availability,
        "quality": quality,
        "confidence": confidence,
        "supporting_facts": supporting,
        "contradictions": contradictions,
        "missing_facts": missing,
        "degraded_facts": degraded,
        "failure_risks": failure_risks,
        "reason_codes": reasons,
    }
    world = CanonicalContextWorld(
        d2_snapshot_hash=root,
        decision_time_ns=decision_time_ns,
        availability=availability,
        quality=quality,
        confidence=confidence,
        session_hash=session.output_hash,
        index_sector_hash=_stable_hash({
            "index": index_context.output_hash,
            "sector": sector_context.output_hash,
        }),
        relative_strength_hash=relative_strength.output_hash,
        regime_hash=market_regime.output_hash,
        source_snapshot_hashes=source_snapshot_hashes,
        source_output_hashes=source_output_hashes,
        supporting_facts=supporting,
        contradictions=contradictions,
        missing_facts=missing,
        degraded_facts=degraded,
        failure_risks=failure_risks,
        reason_codes=reasons,
        warnings=warnings,
        components=components,
        output_hash=_stable_hash(seed),
    )
    if len(json.dumps(world.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")) > MAX_CONTEXT_WORLD_BYTES:
        raise CanonicalContextWorldError("BOUNDED_CONTEXT_WORLD_EXCEEDED")
    return world


def build_context_receipts(world: CanonicalContextWorld) -> tuple[CanonicalContextReceipt, ...]:
    """Project canonical M3.2 components into the existing DecisionContext receipt contract.

    This is wiring, not authority migration. The current D6 compatibility inputs
    remain untouched; these receipts populate canonical evidence fields only.
    """

    status_map = {
        "AVAILABLE": "completed",
        "DEGRADED": "degraded",
        "UNAVAILABLE": "degraded",
        "ERROR": "degraded",
        "PENDING": "degraded",
    }
    receipts: list[CanonicalContextReceipt] = []
    for item in world.components:
        summary = dict(item.summary)
        summary.update({
            "canonical_context_world": True,
            "canonical_context_world_version": world.calculation_version,
            "canonical_context_world_hash": world.output_hash,
            "canonical_availability": item.availability,
            "component_output_hash": item.output_hash,
            "source_snapshot_hashes": list(item.source_snapshot_hashes),
            "source_output_hashes": list(item.source_output_hashes),
            "supporting_facts": list(item.supporting_facts),
            "contradictions": list(item.contradictions),
            "missing_facts": list(item.missing_facts),
            "degraded_facts": list(item.degraded_facts),
            "failure_risks": list(item.failure_risks),
            "reason_codes": list(item.reason_codes),
            "used_for_probability": False,
            "may_propose": False,
            "may_veto": False,
            "may_downgrade": False,
            "may_set_final_band": False,
            "may_execute": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "human_approval_required": True,
        })
        _bounded_mapping(summary, f"{item.engine_id}.receipt_summary")
        receipts.append(CanonicalContextReceipt(
            engine_id=item.engine_id,
            source_snapshot_hash=world.d2_snapshot_hash,
            output_hash=item.output_hash,
            status=status_map[item.availability],
            engine_version=item.calculation_version,
            output_summary=_canonical_mapping(summary),
            warnings=item.warnings,
        ))
    return tuple(sorted(receipts, key=lambda item: item.engine_id))


def components_from_m32_results(
    *,
    session: Any,
    index_sector: Any,
    relative_strength: CanonicalRelativeStrength,
    market_regime: CanonicalMarketRegime,
) -> tuple[ContextWorldComponent, ContextWorldComponent, ContextWorldComponent, ContextWorldComponent, ContextWorldComponent]:
    """Build the five F components from locked B/C/D/E results.

    Index and sector stay as separate DecisionContext evidence fields even though
    M3.2-C computes them in one canonical relationship object.
    """

    session_component = component_from_result(
        engine_id="SESSION_MEMORY",
        result=session,
        summary={
            "current_phase": _get(session, "current_phase", None),
            "session_id": _get(session, "session_id", None),
            "session_date": _get(session, "session_date", None),
            "availability": _get(session, "availability", "UNAVAILABLE"),
            "session_return_pct": _get(session, "session_return_pct", None),
            "observed_progress": _get(session, "observed_progress", None),
        },
        source_output_hashes=(_get(session, "source_feature_kernel_hash", ""),),
        missing_facts=_session_missing(session),
        reason_codes=_get(session, "reason_codes", ()) or (),
        warnings=_get(session, "warnings", ()) or (),
    )

    c_availability = str(_get(index_sector, "availability", "UNAVAILABLE")).upper()
    c_contradictions = tuple(_get(index_sector, "contradictions", ()) or ())
    c_reasons = tuple(_get(index_sector, "reason_codes", ()) or ())
    index_obj = _get(index_sector, "index", None)
    sector_obj = _get(index_sector, "sector", None)
    index_missing = ("INDEX_CONTEXT_MISSING",) if index_obj is None else ()
    sector_missing = ("SECTOR_CONTEXT_MISSING",) if sector_obj is None else ()

    index_component = component_from_result(
        engine_id="INDEX_CONTEXT",
        result=index_sector,
        summary={
            "stock_symbol": _get(index_sector, "stock_symbol", None),
            "benchmark_symbol": _nested(index_obj, "source", "symbol_or_universe"),
            "availability": c_availability if index_obj is not None else "UNAVAILABLE",
            "relation": _get(index_sector, "relation", "UNKNOWN"),
            "price_basis": _nested(index_obj, "price_basis", "basis"),
        },
        source_snapshot_hashes=_maybe_hash(_nested(index_obj, "source", "source_snapshot_hash")),
        source_output_hashes=_maybe_hash(_get(index_obj, "observation_hash", None)),
        contradictions=c_contradictions,
        missing_facts=index_missing,
        degraded_facts=("INDEX_CONTEXT_DEGRADED",) if c_availability == "DEGRADED" and index_obj is not None else (),
        reason_codes=c_reasons,
    )
    sector_component = component_from_result(
        engine_id="SECTOR_CONTEXT",
        result=index_sector,
        summary={
            "stock_symbol": _get(index_sector, "stock_symbol", None),
            "benchmark_symbol": _nested(sector_obj, "source", "symbol_or_universe"),
            "availability": c_availability if sector_obj is not None else "UNAVAILABLE",
            "relation": _get(index_sector, "relation", "UNKNOWN"),
            "price_basis": _nested(sector_obj, "price_basis", "basis"),
        },
        source_snapshot_hashes=_maybe_hash(_nested(sector_obj, "source", "source_snapshot_hash")),
        source_output_hashes=_maybe_hash(_get(sector_obj, "observation_hash", None)),
        contradictions=c_contradictions,
        missing_facts=sector_missing,
        degraded_facts=("SECTOR_CONTEXT_DEGRADED",) if c_availability == "DEGRADED" and sector_obj is not None else (),
        reason_codes=c_reasons,
    )

    rs_component = component_from_result(
        engine_id="RELATIVE_STRENGTH",
        result=relative_strength,
        summary={
            "availability": relative_strength.availability,
            "state": relative_strength.state,
            "window": relative_strength.window.as_dict(),
            "stock_return": relative_strength.stock_return,
            "sector_return": relative_strength.sector_return,
            "index_return": relative_strength.index_return,
            "stock_vs_sector": relative_strength.stock_vs_sector,
            "stock_vs_index": relative_strength.stock_vs_index,
            "sector_vs_index": relative_strength.sector_vs_index,
        },
        source_snapshot_hashes=relative_strength.source_hashes,
        supporting_facts=relative_strength.supporting_facts,
        contradictions=relative_strength.contradictions,
        missing_facts=relative_strength.missing_facts,
        reason_codes=relative_strength.reason_codes,
    )

    regime_component = component_from_result(
        engine_id="MARKET_REGIME",
        result=market_regime,
        summary={
            "availability": market_regime.availability,
            "stable_regime": market_regime.stable_regime,
            "transition_candidate": market_regime.transition_candidate,
            "persistence_count": market_regime.persistence_count,
            "minimum_confirmation": market_regime.minimum_confirmation,
            "confidence": market_regime.confidence,
            "ood": market_regime.ood,
            "novelty_reasons": list(market_regime.novelty_reasons),
        },
        source_snapshot_hashes=market_regime.source_hashes,
        supporting_facts=market_regime.supporting_facts,
        contradictions=market_regime.contradictions,
        missing_facts=market_regime.missing_facts,
        degraded_facts=market_regime.degraded_facts,
        failure_risks=market_regime.failure_risks,
    )
    return session_component, index_component, sector_component, rs_component, regime_component


def _session_missing(session: Any) -> tuple[str, ...]:
    availability = str(_get(session, "availability", "UNAVAILABLE")).upper()
    if availability == "AVAILABLE":
        return ()
    return (f"SESSION_{availability}",)


def _availability(states: Sequence[str] | Any) -> ContextWorldAvailability:
    values = [str(item).upper() for item in states]
    if not values:
        return "UNAVAILABLE"
    if "ERROR" in values:
        return "ERROR"
    if all(value == "UNAVAILABLE" for value in values):
        return "UNAVAILABLE"
    if "PENDING" in values and all(value in {"PENDING", "UNAVAILABLE"} for value in values):
        return "PENDING"
    if any(value in {"DEGRADED", "UNAVAILABLE", "PENDING"} for value in values):
        return "DEGRADED"
    return "AVAILABLE"


def _union(groups: Sequence[Sequence[str]] | Any) -> tuple[str, ...]:
    return tuple(sorted({str(item) for group in groups for item in group if str(item)}))


def _union_hashes(groups: Sequence[Sequence[str]] | Any) -> tuple[str, ...]:
    values = tuple(sorted({str(item).lower() for group in groups for item in group if str(item)}))
    for value in values:
        _hash(value, "source_hash")
    return values


def _hash_tuple(values: Sequence[str], field: str) -> tuple[str, ...]:
    normalized = tuple(sorted({str(value).lower() for value in values if str(value)}))
    for value in normalized:
        _hash(value, field)
    return normalized


def _maybe_hash(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    text = str(value).lower()
    _hash(text, "optional_hash")
    return (text,)


def _strings(values: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    if any(len(value) > 240 for value in normalized):
        raise CanonicalContextWorldError("CONTEXT_FACT_TOO_LONG")
    return normalized


def _bounded_mapping(value: Mapping[str, Any], field: str) -> None:
    encoded = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    if len(encoded) > MAX_COMPONENT_SUMMARY_BYTES:
        raise CanonicalContextWorldError(f"BOUNDED_COMPONENT_SUMMARY_EXCEEDED:{field}")


def _canonical_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), default=str)
    return json.loads(encoded)


def _hash(value: str, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise CanonicalContextWorldError(f"INVALID_HASH:{field}")


def _stable(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _nested(value: Any, first: str, second: str) -> Any:
    if value is None:
        return None
    return _get(_get(value, first, None), second, None)
