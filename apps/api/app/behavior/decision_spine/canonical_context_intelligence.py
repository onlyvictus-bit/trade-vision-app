from __future__ import annotations

"""Canonical M3.2 context-source identity and causal envelope.

M3.2-A deliberately does not calculate market regime, relative strength,
sector strength, session probabilities, trade bands, or any execution action.
It freezes and validates the independently sourced observations that later
M3.2 specialists are allowed to interpret.

The envelope is strict by design:
- future/not-yet-available observations are rejected;
- synthetic observations cannot masquerade as canonical available evidence;
- unavailable sources remain unavailable and are never converted to neutral;
- deterministic evidence identity excludes operational timing/cache metadata;
- every source is bound to the same D2 decision time;
- the output has zero decision/execution authority.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal, Sequence


CONTEXT_SOURCE_OBSERVATION_VERSION = "context-source-observation.v1"
CANONICAL_CONTEXT_ENVELOPE_VERSION = "canonical-context-envelope.v1"
MAX_CONTEXT_ENVELOPE_BYTES = 32_000
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")

ContextSourceKind = Literal[
    "STOCK",
    "INDEX",
    "SECTOR",
    "BREADTH",
    "CALENDAR",
    "CROSS_MARKET",
]
ContextAvailability = Literal[
    "AVAILABLE",
    "DEGRADED",
    "UNAVAILABLE",
    "PENDING",
    "ERROR",
]
FreshnessState = Literal["FRESH", "STALE", "UNKNOWN"]
ClockSkewState = Literal["ALIGNED", "SKEWED", "UNKNOWN"]

_ALLOWED_SOURCE_KINDS = {
    "STOCK",
    "INDEX",
    "SECTOR",
    "BREADTH",
    "CALENDAR",
    "CROSS_MARKET",
}
_ALLOWED_AVAILABILITY = {"AVAILABLE", "DEGRADED", "UNAVAILABLE", "PENDING", "ERROR"}
_ALLOWED_FRESHNESS = {"FRESH", "STALE", "UNKNOWN"}
_ALLOWED_CLOCK_SKEW = {"ALIGNED", "SKEWED", "UNKNOWN"}


class CanonicalContextError(ValueError):
    """Raised when an M3.2 context source cannot be admitted causally."""


@dataclass(frozen=True, slots=True)
class ContextSourceObservation:
    """Identity of one independently frozen contextual source.

    ``source_snapshot_hash`` may be ``None`` only when the source is not
    available. An AVAILABLE/DEGRADED source must identify the immutable source
    state that was actually observed.
    """

    source_id: str
    source_kind: ContextSourceKind
    symbol_or_universe: str
    provider_id: str
    provider_contract_version: str
    source_snapshot_hash: str | None
    source_timeframe: str | None
    source_bar_close_time_ns: int | None
    available_at_ns: int | None
    d2_decision_time_ns: int
    sequence_or_watermark: str | None = None
    freshness_state: FreshnessState = "UNKNOWN"
    clock_skew_state: ClockSkewState = "UNKNOWN"
    identity_match: bool = True
    synthetic: bool = False
    availability: ContextAvailability = "AVAILABLE"
    reason_codes: tuple[str, ...] = ()
    calculation_version: str = CONTEXT_SOURCE_OBSERVATION_VERSION

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


@dataclass(frozen=True, slots=True)
class CanonicalContextEnvelope:
    """Bounded immutable source world for later M3.2 specialist brains."""

    d2_snapshot_hash: str
    decision_time_ns: int
    sources: tuple[ContextSourceObservation, ...]
    availability: ContextAvailability
    source_hashes: dict[str, str]
    source_counts: dict[str, int]
    warnings: tuple[str, ...]
    context_hash: str
    calculation_version: str = CANONICAL_CONTEXT_ENVELOPE_VERSION
    used_for_probability: bool = False
    may_propose: bool = False
    may_veto: bool = False
    may_downgrade: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "calculation_version": self.calculation_version,
            "d2_snapshot_hash": self.d2_snapshot_hash,
            "decision_time_ns": self.decision_time_ns,
            "sources": [item.as_dict() for item in self.sources],
            "availability": self.availability,
            "source_hashes": dict(self.source_hashes),
            "source_counts": dict(self.source_counts),
            "warnings": list(self.warnings),
            "context_hash": self.context_hash,
            "used_for_probability": False,
            "may_propose": False,
            "may_veto": False,
            "may_downgrade": False,
            "may_set_final_band": False,
            "may_execute": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }


def build_canonical_context_envelope(
    *,
    d2_snapshot_hash: str,
    decision_time_ns: int,
    sources: Sequence[ContextSourceObservation],
) -> CanonicalContextEnvelope:
    """Validate and freeze M3.2 contextual source identities.

    Source order is intentionally normalized by ``source_id`` so callers that
    receive independent provider results in a different completion order still
    produce the same canonical context hash.
    """

    d2_snapshot_hash = _require_hash(d2_snapshot_hash, "d2_snapshot_hash")
    if not isinstance(decision_time_ns, int) or isinstance(decision_time_ns, bool) or decision_time_ns <= 0:
        raise CanonicalContextError("INVALID_DECISION_TIME")
    if isinstance(sources, (str, bytes)):
        raise CanonicalContextError("INVALID_SOURCE_COLLECTION")

    normalized = tuple(sorted(sources, key=lambda item: item.source_id))
    if len({item.source_id for item in normalized}) != len(normalized):
        raise CanonicalContextError("DUPLICATE_SOURCE_ID")

    warnings: list[str] = []
    source_hashes: dict[str, str] = {}
    source_counts = {state: 0 for state in sorted(_ALLOWED_AVAILABILITY)}

    for source in normalized:
        _validate_source(source, decision_time_ns=decision_time_ns)
        source_counts[source.availability] += 1
        if source.source_snapshot_hash is not None:
            source_hashes[source.source_id] = source.source_snapshot_hash.lower()
        if source.availability != "AVAILABLE":
            warnings.append(f"{source.source_id} availability is {source.availability}.")
        if source.freshness_state == "STALE":
            warnings.append(f"{source.source_id} is stale.")
        if source.clock_skew_state == "SKEWED":
            warnings.append(f"{source.source_id} has clock skew.")

    availability = _combine_availability(item.availability for item in normalized)
    deterministic_sources = [_deterministic_source_dict(item) for item in normalized]
    context_seed = {
        "calculation_version": CANONICAL_CONTEXT_ENVELOPE_VERSION,
        "source_observation_version": CONTEXT_SOURCE_OBSERVATION_VERSION,
        "d2_snapshot_hash": d2_snapshot_hash,
        "decision_time_ns": decision_time_ns,
        "sources": deterministic_sources,
        "availability": availability,
    }
    context_hash = _stable_hash(context_seed)

    result = CanonicalContextEnvelope(
        d2_snapshot_hash=d2_snapshot_hash,
        decision_time_ns=decision_time_ns,
        sources=normalized,
        availability=availability,
        source_hashes=dict(sorted(source_hashes.items())),
        source_counts=source_counts,
        warnings=tuple(sorted(set(warnings))),
        context_hash=context_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_CONTEXT_ENVELOPE_BYTES:
        raise CanonicalContextError("BOUNDED_CONTEXT_EXCEEDED")
    return result


def _validate_source(source: ContextSourceObservation, *, decision_time_ns: int) -> None:
    if not isinstance(source, ContextSourceObservation):
        raise CanonicalContextError("INVALID_SOURCE_RECORD")
    if not source.source_id.strip():
        raise CanonicalContextError("EMPTY_SOURCE_ID")
    if len(source.source_id) > 160:
        raise CanonicalContextError(f"SOURCE_ID_TOO_LONG:{source.source_id[:40]}")
    if source.source_kind not in _ALLOWED_SOURCE_KINDS:
        raise CanonicalContextError(f"INVALID_SOURCE_KIND:{source.source_id}")
    if source.availability not in _ALLOWED_AVAILABILITY:
        raise CanonicalContextError(f"INVALID_AVAILABILITY:{source.source_id}")
    if source.freshness_state not in _ALLOWED_FRESHNESS:
        raise CanonicalContextError(f"INVALID_FRESHNESS:{source.source_id}")
    if source.clock_skew_state not in _ALLOWED_CLOCK_SKEW:
        raise CanonicalContextError(f"INVALID_CLOCK_SKEW:{source.source_id}")
    if not source.symbol_or_universe.strip():
        raise CanonicalContextError(f"EMPTY_SYMBOL_OR_UNIVERSE:{source.source_id}")
    if not source.provider_id.strip():
        raise CanonicalContextError(f"EMPTY_PROVIDER_ID:{source.source_id}")
    if not source.provider_contract_version.strip():
        raise CanonicalContextError(f"EMPTY_PROVIDER_CONTRACT_VERSION:{source.source_id}")
    if source.d2_decision_time_ns != decision_time_ns:
        raise CanonicalContextError(f"DECISION_TIME_MISMATCH:{source.source_id}")
    if source.d2_decision_time_ns <= 0:
        raise CanonicalContextError(f"INVALID_SOURCE_DECISION_TIME:{source.source_id}")

    requires_snapshot = source.availability in {"AVAILABLE", "DEGRADED"}
    if requires_snapshot:
        if source.source_snapshot_hash is None:
            raise CanonicalContextError(f"MISSING_SOURCE_SNAPSHOT_HASH:{source.source_id}")
        _require_hash(source.source_snapshot_hash, f"{source.source_id}.source_snapshot_hash")
    elif source.source_snapshot_hash is not None:
        _require_hash(source.source_snapshot_hash, f"{source.source_id}.source_snapshot_hash")

    if source.synthetic and source.availability in {"AVAILABLE", "DEGRADED"}:
        raise CanonicalContextError(f"SYNTHETIC_SOURCE_NOT_CANONICAL:{source.source_id}")
    if not source.identity_match and source.availability in {"AVAILABLE", "DEGRADED"}:
        raise CanonicalContextError(f"SOURCE_IDENTITY_MISMATCH:{source.source_id}")

    if source.source_bar_close_time_ns is not None:
        if source.source_bar_close_time_ns <= 0:
            raise CanonicalContextError(f"INVALID_SOURCE_BAR_CLOSE_TIME:{source.source_id}")
        if source.source_bar_close_time_ns > decision_time_ns:
            raise CanonicalContextError(f"FUTURE_SOURCE_BAR:{source.source_id}")
    if source.available_at_ns is not None:
        if source.available_at_ns <= 0:
            raise CanonicalContextError(f"INVALID_SOURCE_AVAILABLE_AT:{source.source_id}")
        if source.available_at_ns > decision_time_ns:
            raise CanonicalContextError(f"FUTURE_SOURCE_AVAILABILITY:{source.source_id}")

    if source.availability in {"AVAILABLE", "DEGRADED"}:
        if source.source_bar_close_time_ns is None and source.source_kind not in {"CALENDAR", "BREADTH"}:
            raise CanonicalContextError(f"MISSING_SOURCE_BAR_CLOSE_TIME:{source.source_id}")
        if source.available_at_ns is None:
            raise CanonicalContextError(f"MISSING_SOURCE_AVAILABLE_AT:{source.source_id}")

    for reason in source.reason_codes:
        if not isinstance(reason, str) or not reason.strip():
            raise CanonicalContextError(f"INVALID_REASON_CODE:{source.source_id}")
        if len(reason) > 160:
            raise CanonicalContextError(f"REASON_CODE_TOO_LONG:{source.source_id}")


def _deterministic_source_dict(source: ContextSourceObservation) -> dict[str, Any]:
    # This list is intentionally explicit. Future operational-only telemetry
    # (latency/cache-hit/retry count) must never be added to canonical identity.
    return {
        "calculation_version": source.calculation_version,
        "source_id": source.source_id,
        "source_kind": source.source_kind,
        "symbol_or_universe": source.symbol_or_universe,
        "provider_id": source.provider_id,
        "provider_contract_version": source.provider_contract_version,
        "source_snapshot_hash": source.source_snapshot_hash.lower() if source.source_snapshot_hash else None,
        "source_timeframe": source.source_timeframe,
        "source_bar_close_time_ns": source.source_bar_close_time_ns,
        "available_at_ns": source.available_at_ns,
        "d2_decision_time_ns": source.d2_decision_time_ns,
        "sequence_or_watermark": source.sequence_or_watermark,
        "freshness_state": source.freshness_state,
        "clock_skew_state": source.clock_skew_state,
        "identity_match": source.identity_match,
        "synthetic": source.synthetic,
        "availability": source.availability,
        "reason_codes": sorted(set(source.reason_codes)),
    }


def _combine_availability(values) -> ContextAvailability:
    states = [str(value).upper() for value in values]
    if not states:
        return "UNAVAILABLE"
    if "ERROR" in states:
        return "ERROR"
    if all(state == "UNAVAILABLE" for state in states):
        return "UNAVAILABLE"
    if "PENDING" in states and all(state in {"PENDING", "UNAVAILABLE"} for state in states):
        return "PENDING"
    if any(state in {"DEGRADED", "UNAVAILABLE", "PENDING"} for state in states):
        return "DEGRADED"
    return "AVAILABLE"


def _require_hash(value: str, field: str) -> str:
    normalized = str(value).strip().lower()
    if not _HASH_RE.fullmatch(normalized):
        raise CanonicalContextError(f"INVALID_SHA256:{field}")
    return normalized


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
