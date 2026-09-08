from __future__ import annotations

"""Zero-authority epistemic evidence graph for M3.1.1 shadow reasoning.

The graph does not decide, predict, vote or execute. It records what a claim is,
where it came from, what it depends on and whether it is fact, inference,
hypothesis or calibrated predictive evidence.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable


EVIDENCE_GRAPH_VERSION = "epistemic-evidence-graph.v1"
MAX_TEXT = 500
MAX_LINKS = 64
MAX_CLAIMS = 512


class EpistemicType(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    HYPOTHESIS = "HYPOTHESIS"
    PREDICTIVE = "PREDICTIVE"


class EvidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    CONFLICTED = "CONFLICTED"
    OOD = "OOD"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    claim_id: str
    claim_type: EpistemicType
    statement: str
    source_engine: str
    source_snapshot_hash: str
    source_output_hash: str | None
    calculation_version: str
    dependency_family: str
    correlation_group: str
    availability: EvidenceAvailability
    quality: str
    upstream_claim_ids: tuple[str, ...] = ()
    supporting_claim_ids: tuple[str, ...] = ()
    contradicting_claim_ids: tuple[str, ...] = ()
    confirmation_needed: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    calibration_id: str | None = None
    claim_hash: str = ""
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceGraph:
    graph_version: str
    source_snapshot_hash: str
    claims: tuple[EvidenceClaim, ...]
    independent_dependency_families: tuple[str, ...]
    correlation_groups: tuple[str, ...]
    graph_hash: str
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True

    def claim(self, claim_id: str) -> EvidenceClaim:
        for item in self.claims:
            if item.claim_id == claim_id:
                return item
        raise KeyError(claim_id)

    def bounded_summary(self) -> dict[str, object]:
        type_counts: dict[str, int] = {}
        availability_counts: dict[str, int] = {}
        for item in self.claims:
            type_counts[item.claim_type.value] = type_counts.get(item.claim_type.value, 0) + 1
            availability_counts[item.availability.value] = availability_counts.get(item.availability.value, 0) + 1
        return {
            "graph_version": self.graph_version,
            "source_snapshot_hash": self.source_snapshot_hash,
            "claim_count": len(self.claims),
            "type_counts": dict(sorted(type_counts.items())),
            "availability_counts": dict(sorted(availability_counts.items())),
            "independent_dependency_families": list(self.independent_dependency_families),
            "correlation_groups": list(self.correlation_groups),
            "graph_hash": self.graph_hash,
            "authority": {
                "used_for_probability": False,
                "may_set_final_band": False,
                "may_execute": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
            },
        }


def make_evidence_claim(
    *,
    claim_id: str,
    claim_type: EpistemicType,
    statement: str,
    source_engine: str,
    source_snapshot_hash: str,
    source_output_hash: str | None,
    calculation_version: str,
    dependency_family: str,
    correlation_group: str,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    quality: str = "UNSPECIFIED",
    upstream_claim_ids: Iterable[str] = (),
    supporting_claim_ids: Iterable[str] = (),
    contradicting_claim_ids: Iterable[str] = (),
    confirmation_needed: Iterable[str] = (),
    invalidation_conditions: Iterable[str] = (),
    calibration_id: str | None = None,
) -> EvidenceClaim:
    claim_id_n = _bounded_token(claim_id, "claim_id", 160)
    statement_n = _bounded_text(statement, "statement")
    source_engine_n = _bounded_token(source_engine, "source_engine", 160)
    calc_n = _bounded_token(calculation_version, "calculation_version", 160)
    dependency_n = _bounded_token(dependency_family, "dependency_family", 160)
    correlation_n = _bounded_token(correlation_group, "correlation_group", 160)
    quality_n = _bounded_token(quality, "quality", 160)
    snapshot_hash_n = _sha256(source_snapshot_hash, "source_snapshot_hash")
    output_hash_n = None if source_output_hash is None else _sha256(source_output_hash, "source_output_hash")
    upstream_n = _links(upstream_claim_ids, "upstream_claim_ids")
    support_n = _links(supporting_claim_ids, "supporting_claim_ids")
    contradict_n = _links(contradicting_claim_ids, "contradicting_claim_ids")
    confirmation_n = tuple(_bounded_text(item, "confirmation_needed") for item in confirmation_needed)
    invalidation_n = tuple(_bounded_text(item, "invalidation_conditions") for item in invalidation_conditions)
    if len(confirmation_n) > MAX_LINKS or len(invalidation_n) > MAX_LINKS:
        raise ValueError("confirmation/invalidation lists exceed bounded evidence contract")

    if claim_type is EpistemicType.PREDICTIVE and not calibration_id:
        raise ValueError("PREDICTIVE claims require an explicit calibration_id")
    if claim_type is not EpistemicType.PREDICTIVE and calibration_id is not None:
        raise ValueError("calibration_id is reserved for PREDICTIVE claims")

    deterministic = {
        "claim_id": claim_id_n,
        "claim_type": claim_type.value,
        "statement": statement_n,
        "source_engine": source_engine_n,
        "source_snapshot_hash": snapshot_hash_n,
        "source_output_hash": output_hash_n,
        "calculation_version": calc_n,
        "dependency_family": dependency_n,
        "correlation_group": correlation_n,
        "availability": availability.value,
        "quality": quality_n,
        "upstream_claim_ids": upstream_n,
        "supporting_claim_ids": support_n,
        "contradicting_claim_ids": contradict_n,
        "confirmation_needed": confirmation_n,
        "invalidation_conditions": invalidation_n,
        "calibration_id": calibration_id,
    }
    return EvidenceClaim(
        claim_id=claim_id_n,
        claim_type=claim_type,
        statement=statement_n,
        source_engine=source_engine_n,
        source_snapshot_hash=snapshot_hash_n,
        source_output_hash=output_hash_n,
        calculation_version=calc_n,
        dependency_family=dependency_n,
        correlation_group=correlation_n,
        availability=availability,
        quality=quality_n,
        upstream_claim_ids=upstream_n,
        supporting_claim_ids=support_n,
        contradicting_claim_ids=contradict_n,
        confirmation_needed=confirmation_n,
        invalidation_conditions=invalidation_n,
        calibration_id=calibration_id,
        claim_hash=_stable_hash(deterministic),
    )


def build_evidence_graph(
    source_snapshot_hash: str,
    claims: Iterable[EvidenceClaim],
) -> EvidenceGraph:
    snapshot_hash = _sha256(source_snapshot_hash, "source_snapshot_hash")
    items = tuple(sorted(claims, key=lambda item: item.claim_id))
    if not items:
        raise ValueError("evidence graph requires at least one claim")
    if len(items) > MAX_CLAIMS:
        raise ValueError(f"evidence graph exceeds {MAX_CLAIMS} claims")
    ids = [item.claim_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate claim_id in evidence graph")
    id_set = set(ids)
    for item in items:
        if item.source_snapshot_hash != snapshot_hash:
            raise ValueError("claim snapshot hash differs from graph snapshot hash")
        for linked in (*item.upstream_claim_ids, *item.supporting_claim_ids, *item.contradicting_claim_ids):
            if linked not in id_set:
                raise ValueError(f"claim {item.claim_id} references unknown claim {linked}")
        if item.claim_id in item.upstream_claim_ids:
            raise ValueError("claim cannot depend on itself")
        if item.used_for_probability or item.may_set_final_band or item.may_execute:
            raise ValueError("shadow evidence claims must have zero authority")

    _assert_acyclic(items)
    dependency_families = tuple(sorted({item.dependency_family for item in items}))
    correlation_groups = tuple(sorted({item.correlation_group for item in items}))
    deterministic = {
        "graph_version": EVIDENCE_GRAPH_VERSION,
        "source_snapshot_hash": snapshot_hash,
        "claims": [
            {
                "claim_id": item.claim_id,
                "claim_hash": item.claim_hash,
            }
            for item in items
        ],
        "independent_dependency_families": dependency_families,
        "correlation_groups": correlation_groups,
    }
    return EvidenceGraph(
        graph_version=EVIDENCE_GRAPH_VERSION,
        source_snapshot_hash=snapshot_hash,
        claims=items,
        independent_dependency_families=dependency_families,
        correlation_groups=correlation_groups,
        graph_hash=_stable_hash(deterministic),
    )


def _assert_acyclic(items: tuple[EvidenceClaim, ...]) -> None:
    dependencies = {item.claim_id: set(item.upstream_claim_ids) for item in items}
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node: str) -> None:
        if node in permanent:
            return
        if node in temporary:
            raise ValueError("cycle detected in evidence graph")
        temporary.add(node)
        for dependency in dependencies[node]:
            visit(dependency)
        temporary.remove(node)
        permanent.add(node)

    for claim_id in dependencies:
        visit(claim_id)


def _links(values: Iterable[str], name: str) -> tuple[str, ...]:
    normalized = tuple(sorted(set(_bounded_token(item, name, 160) for item in values)))
    if len(normalized) > MAX_LINKS:
        raise ValueError(f"{name} exceeds {MAX_LINKS} links")
    return normalized


def _bounded_text(value: str, name: str) -> str:
    text = str(value).strip()
    if not text or len(text) > MAX_TEXT:
        raise ValueError(f"{name} must contain 1..{MAX_TEXT} characters")
    return text


def _bounded_token(value: str, name: str, limit: int) -> str:
    text = str(value).strip()
    if not text or len(text) > limit:
        raise ValueError(f"{name} must contain 1..{limit} characters")
    return text


def _sha256(value: str, name: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64:
        raise ValueError(f"{name} must be a 64-character SHA-256 value")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return text


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
