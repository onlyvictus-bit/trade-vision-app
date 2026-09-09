from __future__ import annotations

"""Canonical M3.3 memory episode contract and PIT-safe feature freezer.

This module is deliberately evidence-only.  It freezes bounded summaries of the
already-canonical M3.1 price world and M3.2 context world into a deterministic
memory episode.  It does not label outcomes, retrieve analogs, calculate a
trading score, or acquire any decision/execution authority.

Hard laws enforced here:
- future/unavailable facts never become causal evidence;
- synthetic production evidence cannot masquerade as real memory;
- missing/degraded/contradictory evidence stays explicit;
- raw fact count is distinct from independent episode count;
- source order and fact order cannot change episode identity;
- payloads are bounded and replay/restart deterministic;
- hashes bind the episode to D2, price world, context world and source outputs.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping, Sequence


MEMORY_EPISODE_SCHEMA_VERSION = "canonical-memory-episode.v1"
MEMORY_FEATURE_VERSION = "canonical-memory-features.v1"
MAX_MEMORY_EPISODE_BYTES = 48_000
MAX_FACTS_PER_FAMILY = 256
MAX_TEXT_ITEMS = 128
MAX_TEXT_LENGTH = 512
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")

MemoryAvailability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE", "ERROR"]
_ALLOWED_AVAILABILITY = {"AVAILABLE", "DEGRADED", "UNAVAILABLE", "ERROR"}


class CanonicalMemoryError(ValueError):
    """Raised when an M3.3 memory episode cannot be frozen causally."""


@dataclass(frozen=True, slots=True)
class MemorySourceRef:
    """Immutable identity for one source contributing to an episode."""

    source_id: str
    source_snapshot_hash: str
    source_output_hash: str
    available_at_ns: int
    synthetic: bool = False
    identity_match: bool = True
    availability: MemoryAvailability = "AVAILABLE"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanonicalMemoryEpisode:
    episode_id: str
    schema_version: str
    feature_version: str
    symbol: str
    timeframe: str
    decision_time_ns: int
    d2_snapshot_hash: str
    price_world_hash: str
    context_world_hash: str
    source_snapshot_hashes: tuple[str, ...]
    source_output_hashes: tuple[str, ...]
    session_id: str
    session_phase: str
    fact_families: dict[str, dict[str, Any]]
    missing_facts: tuple[str, ...]
    degraded_facts: tuple[str, ...]
    contradictions: tuple[str, ...]
    failure_risks: tuple[str, ...]
    warnings: tuple[str, ...]
    raw_record_count: int
    independent_episode_count: int
    independent_session_count: int
    independent_symbol_count: int
    feature_hash: str
    episode_hash: str
    availability: MemoryAvailability
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
        return {
            "episode_id": self.episode_id,
            "schema_version": self.schema_version,
            "feature_version": self.feature_version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "decision_time_ns": self.decision_time_ns,
            "d2_snapshot_hash": self.d2_snapshot_hash,
            "price_world_hash": self.price_world_hash,
            "context_world_hash": self.context_world_hash,
            "source_snapshot_hashes": list(self.source_snapshot_hashes),
            "source_output_hashes": list(self.source_output_hashes),
            "session_id": self.session_id,
            "session_phase": self.session_phase,
            "fact_families": self.fact_families,
            "missing_facts": list(self.missing_facts),
            "degraded_facts": list(self.degraded_facts),
            "contradictions": list(self.contradictions),
            "failure_risks": list(self.failure_risks),
            "warnings": list(self.warnings),
            "raw_record_count": self.raw_record_count,
            "independent_episode_count": self.independent_episode_count,
            "independent_session_count": self.independent_session_count,
            "independent_symbol_count": self.independent_symbol_count,
            "feature_hash": self.feature_hash,
            "episode_hash": self.episode_hash,
            "availability": self.availability,
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
        }


def freeze_memory_episode(
    *,
    symbol: str,
    timeframe: str,
    decision_time_ns: int,
    d2_snapshot_hash: str,
    price_world_hash: str,
    context_world_hash: str,
    session_id: str,
    session_phase: str,
    fact_families: Mapping[str, Mapping[str, Any]],
    sources: Sequence[MemorySourceRef],
    missing_facts: Sequence[str] = (),
    degraded_facts: Sequence[str] = (),
    contradictions: Sequence[str] = (),
    failure_risks: Sequence[str] = (),
    warnings: Sequence[str] = (),
) -> CanonicalMemoryEpisode:
    """Freeze a deterministic unlabeled episode from canonical causal evidence.

    One call creates exactly one independent market episode even if hundreds of
    derived facts/indicators are present.  This prevents correlated facts from
    inflating statistical sample size at the memory boundary.
    """

    symbol = _require_text(symbol, "symbol", max_length=64).upper()
    timeframe = _require_text(timeframe, "timeframe", max_length=32)
    session_id = _require_text(session_id, "session_id", max_length=160)
    session_phase = _require_text(session_phase, "session_phase", max_length=80)
    if not isinstance(decision_time_ns, int) or isinstance(decision_time_ns, bool) or decision_time_ns <= 0:
        raise CanonicalMemoryError("INVALID_DECISION_TIME")

    d2_snapshot_hash = _require_hash(d2_snapshot_hash, "d2_snapshot_hash")
    price_world_hash = _require_hash(price_world_hash, "price_world_hash")
    context_world_hash = _require_hash(context_world_hash, "context_world_hash")

    normalized_sources = _normalize_sources(sources, decision_time_ns=decision_time_ns)
    normalized_families = _normalize_fact_families(fact_families)
    normalized_missing = _normalize_text_items(missing_facts, "missing_facts")
    normalized_degraded = _normalize_text_items(degraded_facts, "degraded_facts")
    normalized_contradictions = _normalize_text_items(contradictions, "contradictions")
    normalized_failure_risks = _normalize_text_items(failure_risks, "failure_risks")
    normalized_warnings = _normalize_text_items(warnings, "warnings")

    raw_record_count = sum(len(facts) for facts in normalized_families.values())
    # Critical M3.3 statistical law: one frozen decision episode is one
    # independent episode, regardless of how many derived indicators/facts it
    # contains.  Independence across episodes is handled later by corpus logic.
    independent_episode_count = 1
    independent_session_count = 1
    independent_symbol_count = 1

    if not normalized_sources or not normalized_families:
        availability: MemoryAvailability = "UNAVAILABLE"
    elif any(source.availability == "ERROR" for source in normalized_sources):
        availability = "ERROR"
    elif (
        normalized_missing
        or normalized_degraded
        or normalized_contradictions
        or any(source.availability != "AVAILABLE" for source in normalized_sources)
    ):
        availability = "DEGRADED"
    else:
        availability = "AVAILABLE"

    source_snapshot_hashes = tuple(sorted({source.source_snapshot_hash for source in normalized_sources}))
    source_output_hashes = tuple(sorted({source.source_output_hash for source in normalized_sources}))

    feature_seed = {
        "feature_version": MEMORY_FEATURE_VERSION,
        "symbol": symbol,
        "timeframe": timeframe,
        "decision_time_ns": decision_time_ns,
        "d2_snapshot_hash": d2_snapshot_hash,
        "price_world_hash": price_world_hash,
        "context_world_hash": context_world_hash,
        "session_id": session_id,
        "session_phase": session_phase,
        "fact_families": normalized_families,
        "missing_facts": normalized_missing,
        "degraded_facts": normalized_degraded,
        "contradictions": normalized_contradictions,
        "failure_risks": normalized_failure_risks,
    }
    feature_hash = _stable_hash(feature_seed)
    episode_seed = {
        "schema_version": MEMORY_EPISODE_SCHEMA_VERSION,
        "feature_hash": feature_hash,
        "sources": [_deterministic_source_dict(source) for source in normalized_sources],
        "availability": availability,
    }
    episode_hash = _stable_hash(episode_seed)
    episode_id = f"mem-{episode_hash[:32]}"

    episode = CanonicalMemoryEpisode(
        episode_id=episode_id,
        schema_version=MEMORY_EPISODE_SCHEMA_VERSION,
        feature_version=MEMORY_FEATURE_VERSION,
        symbol=symbol,
        timeframe=timeframe,
        decision_time_ns=decision_time_ns,
        d2_snapshot_hash=d2_snapshot_hash,
        price_world_hash=price_world_hash,
        context_world_hash=context_world_hash,
        source_snapshot_hashes=source_snapshot_hashes,
        source_output_hashes=source_output_hashes,
        session_id=session_id,
        session_phase=session_phase,
        fact_families=normalized_families,
        missing_facts=normalized_missing,
        degraded_facts=normalized_degraded,
        contradictions=normalized_contradictions,
        failure_risks=normalized_failure_risks,
        warnings=normalized_warnings,
        raw_record_count=raw_record_count,
        independent_episode_count=independent_episode_count,
        independent_session_count=independent_session_count,
        independent_symbol_count=independent_symbol_count,
        feature_hash=feature_hash,
        episode_hash=episode_hash,
        availability=availability,
    )
    encoded = json.dumps(episode.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_MEMORY_EPISODE_BYTES:
        raise CanonicalMemoryError("BOUNDED_MEMORY_EPISODE_EXCEEDED")
    return episode


def _normalize_sources(sources: Sequence[MemorySourceRef], *, decision_time_ns: int) -> tuple[MemorySourceRef, ...]:
    if isinstance(sources, (str, bytes)):
        raise CanonicalMemoryError("INVALID_SOURCE_COLLECTION")
    normalized = tuple(sorted(sources, key=lambda item: item.source_id))
    if len({source.source_id for source in normalized}) != len(normalized):
        raise CanonicalMemoryError("DUPLICATE_SOURCE_ID")
    for source in normalized:
        if not isinstance(source, MemorySourceRef):
            raise CanonicalMemoryError("INVALID_SOURCE_RECORD")
        _require_text(source.source_id, "source_id", max_length=160)
        _require_hash(source.source_snapshot_hash, f"{source.source_id}.source_snapshot_hash")
        _require_hash(source.source_output_hash, f"{source.source_id}.source_output_hash")
        if source.availability not in _ALLOWED_AVAILABILITY:
            raise CanonicalMemoryError(f"INVALID_SOURCE_AVAILABILITY:{source.source_id}")
        if not isinstance(source.available_at_ns, int) or isinstance(source.available_at_ns, bool) or source.available_at_ns <= 0:
            raise CanonicalMemoryError(f"INVALID_SOURCE_AVAILABLE_AT:{source.source_id}")
        if source.available_at_ns > decision_time_ns:
            raise CanonicalMemoryError(f"FUTURE_SOURCE:{source.source_id}")
        if source.synthetic and source.availability in {"AVAILABLE", "DEGRADED"}:
            raise CanonicalMemoryError(f"SYNTHETIC_SOURCE_NOT_CANONICAL:{source.source_id}")
        if not source.identity_match and source.availability in {"AVAILABLE", "DEGRADED"}:
            raise CanonicalMemoryError(f"SOURCE_IDENTITY_MISMATCH:{source.source_id}")
    return normalized


def _normalize_fact_families(fact_families: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    if not isinstance(fact_families, Mapping):
        raise CanonicalMemoryError("INVALID_FACT_FAMILIES")
    normalized: dict[str, dict[str, Any]] = {}
    for family_name in sorted(fact_families):
        name = _require_text(str(family_name), "fact_family", max_length=80)
        facts = fact_families[family_name]
        if not isinstance(facts, Mapping):
            raise CanonicalMemoryError(f"INVALID_FACT_FAMILY:{name}")
        if len(facts) > MAX_FACTS_PER_FAMILY:
            raise CanonicalMemoryError(f"FACT_FAMILY_TOO_LARGE:{name}")
        normalized[name] = {str(key): _json_safe(facts[key]) for key in sorted(facts, key=lambda value: str(value))}
    return normalized


def _normalize_text_items(values: Sequence[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise CanonicalMemoryError(f"INVALID_{field.upper()}")
    if len(values) > MAX_TEXT_ITEMS:
        raise CanonicalMemoryError(f"TOO_MANY_{field.upper()}")
    normalized = {
        _require_text(str(value), field, max_length=MAX_TEXT_LENGTH)
        for value in values
    }
    return tuple(sorted(normalized))


def _deterministic_source_dict(source: MemorySourceRef) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_snapshot_hash": source.source_snapshot_hash.lower(),
        "source_output_hash": source.source_output_hash.lower(),
        "available_at_ns": source.available_at_ns,
        "synthetic": source.synthetic,
        "identity_match": source.identity_match,
        "availability": source.availability,
    }


def _require_hash(value: str, field: str) -> str:
    if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
        raise CanonicalMemoryError(f"INVALID_HASH:{field}")
    return value.lower()


def _require_text(value: str, field: str, *, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalMemoryError(f"EMPTY_TEXT:{field}")
    value = value.strip()
    if len(value) > max_length:
        raise CanonicalMemoryError(f"TEXT_TOO_LONG:{field}")
    return value


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalMemoryError("NON_FINITE_FACT")
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    if hasattr(value, "as_dict"):
        return _json_safe(value.as_dict())
    raise CanonicalMemoryError(f"UNSUPPORTED_FACT_TYPE:{type(value).__name__}")


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
