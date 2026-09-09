from __future__ import annotations

"""M3.1.1-G full canonical evidence-graph wiring.

This layer converts already-calculated M3.1.1 specialist outputs into traceable
claims. It deliberately does *not* add scores or votes. The purpose is to make
reasoning scientifically auditable: provenance, dependency ancestry,
correlation, contradiction, missing evidence, confirmation and invalidation are
first-class data before later hypothesis/falsification engines reason over them.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from .canonical_indicator_contracts_v2 import CanonicalIndicatorContractsV2
from .evidence_graph import (
    EvidenceAvailability,
    EvidenceClaim,
    EvidenceGraph,
    EpistemicType,
    build_evidence_graph,
    make_evidence_claim,
)


CANONICAL_EVIDENCE_GRAPH_V2_VERSION = "canonical-evidence-graph.v2"


@dataclass(frozen=True, slots=True)
class SpecialistEvidenceInputV2:
    claim_id: str
    statement: str
    source_engine: str
    source_output_hash: str | None
    calculation_version: str
    dependency_family: str
    correlation_group: str
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE
    quality: str = "UNSPECIFIED"
    claim_type: EpistemicType = EpistemicType.DERIVED
    upstream_claim_ids: tuple[str, ...] = ()
    supporting_claim_ids: tuple[str, ...] = ()
    contradicting_claim_ids: tuple[str, ...] = ()
    confirmation_needed: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    calibration_id: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalEvidenceGraphV2:
    calculation_version: str
    source_snapshot_hash: str
    graph: EvidenceGraph
    independent_evidence_family_count: int
    available_claim_count: int
    unavailable_claim_count: int
    conflicted_claim_count: int
    contradiction_link_count: int
    missing_evidence_claim_ids: tuple[str, ...]
    correlation_cluster_sizes: tuple[tuple[str, int], ...]
    graph_hash: str
    epistemic_level: str = "INFERRED"
    research_only: bool = True
    scores_are_uncalibrated: bool = True
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    human_approval_required: bool = True

    def bounded_summary(self) -> dict[str, object]:
        return {
            "calculation_version": self.calculation_version,
            "source_snapshot_hash": self.source_snapshot_hash,
            "claim_count": len(self.graph.claims),
            "independent_evidence_family_count": self.independent_evidence_family_count,
            "raw_claim_count_is_independent_count": False,
            "available_claim_count": self.available_claim_count,
            "unavailable_claim_count": self.unavailable_claim_count,
            "conflicted_claim_count": self.conflicted_claim_count,
            "contradiction_link_count": self.contradiction_link_count,
            "missing_evidence_claim_ids": list(self.missing_evidence_claim_ids),
            "correlation_cluster_sizes": dict(self.correlation_cluster_sizes),
            "graph_hash": self.graph_hash,
            "authority": {
                "research_only": True,
                "scores_are_uncalibrated": True,
                "used_for_probability": False,
                "may_set_final_band": False,
                "may_execute": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
                "human_approval_required": True,
            },
        }


def build_canonical_evidence_graph_v2(
    *,
    source_snapshot_hash: str,
    specialist_inputs: Iterable[SpecialistEvidenceInputV2],
    indicator_contracts: CanonicalIndicatorContractsV2 | None = None,
) -> CanonicalEvidenceGraphV2:
    """Build one causal graph from specialist claims bound to one D2 snapshot.

    ``indicator_contracts`` is optional because G can wire price specialists
    before indicator runtime emits anything. When supplied it is used to add a
    contract-level claim that records how many registry outputs are actually
    canonicalized and how many independent ancestry families exist; individual
    indicator signals should be supplied as specialist inputs with their own
    source output hashes.
    """
    inputs = tuple(specialist_inputs)
    claims: list[EvidenceClaim] = []
    for item in inputs:
        claims.append(
            make_evidence_claim(
                claim_id=item.claim_id,
                claim_type=item.claim_type,
                statement=item.statement,
                source_engine=item.source_engine,
                source_snapshot_hash=source_snapshot_hash,
                source_output_hash=item.source_output_hash,
                calculation_version=item.calculation_version,
                dependency_family=item.dependency_family,
                correlation_group=item.correlation_group,
                availability=item.availability,
                quality=item.quality,
                upstream_claim_ids=item.upstream_claim_ids,
                supporting_claim_ids=item.supporting_claim_ids,
                contradicting_claim_ids=item.contradicting_claim_ids,
                confirmation_needed=item.confirmation_needed,
                invalidation_conditions=item.invalidation_conditions,
                calibration_id=item.calibration_id,
            )
        )

    if indicator_contracts is not None:
        claims.append(
            make_evidence_claim(
                claim_id="indicator-contract-dag",
                claim_type=EpistemicType.DERIVED,
                statement=(
                    f"Indicator registry exposes {indicator_contracts.registered_output_count} output contracts; "
                    f"{sum(n.canonicalized for n in indicator_contracts.nodes)} are currently canonicalized. "
                    "Raw indicator count is not treated as independent evidence."
                ),
                source_engine="CANONICAL_INDICATOR_CONTRACTS_V2",
                source_snapshot_hash=source_snapshot_hash,
                source_output_hash=indicator_contracts.dag_hash,
                calculation_version=indicator_contracts.calculation_version,
                dependency_family="INDICATOR_CONTRACT_METADATA",
                correlation_group="INDICATOR_DEPENDENCY_DAG",
                availability=EvidenceAvailability.AVAILABLE,
                quality="CONTRACT_ONLY",
                confirmation_needed=("Indicator signal claims require D2-bound runtime output before interpretation.",),
                invalidation_conditions=("Registry/DAG identity mismatch invalidates indicator contract interpretation.",),
            )
        )

    if not claims:
        raise ValueError("canonical evidence graph v2 requires at least one specialist claim")

    graph = build_evidence_graph(source_snapshot_hash, claims)
    correlation_counts: dict[str, int] = {}
    available = unavailable = conflicted = contradictions = 0
    missing: list[str] = []
    for claim in graph.claims:
        correlation_counts[claim.correlation_group] = correlation_counts.get(claim.correlation_group, 0) + 1
        contradictions += len(claim.contradicting_claim_ids)
        if claim.availability is EvidenceAvailability.AVAILABLE:
            available += 1
        elif claim.availability is EvidenceAvailability.CONFLICTED:
            conflicted += 1
        else:
            unavailable += 1
            missing.append(claim.claim_id)

    # Independence is intentionally coarser than claim count. Claims sharing a
    # dependency family or a correlation cluster are not counted repeatedly.
    independent_keys = {
        (claim.dependency_family, claim.correlation_group)
        for claim in graph.claims
        if claim.availability is EvidenceAvailability.AVAILABLE
    }
    deterministic = {
        "version": CANONICAL_EVIDENCE_GRAPH_V2_VERSION,
        "source_snapshot_hash": source_snapshot_hash,
        "base_graph_hash": graph.graph_hash,
        "independent_keys": sorted(independent_keys),
        "missing": sorted(missing),
        "correlation_counts": sorted(correlation_counts.items()),
    }
    return CanonicalEvidenceGraphV2(
        calculation_version=CANONICAL_EVIDENCE_GRAPH_V2_VERSION,
        source_snapshot_hash=source_snapshot_hash,
        graph=graph,
        independent_evidence_family_count=len(independent_keys),
        available_claim_count=available,
        unavailable_claim_count=unavailable,
        conflicted_claim_count=conflicted,
        contradiction_link_count=contradictions,
        missing_evidence_claim_ids=tuple(sorted(missing)),
        correlation_cluster_sizes=tuple(sorted(correlation_counts.items())),
        graph_hash=_stable_hash(deterministic),
    )


def specialist_input_from_output(
    *,
    claim_id: str,
    statement: str,
    source_engine: str,
    source_output: Any,
    calculation_version: str,
    dependency_family: str,
    correlation_group: str,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    quality: str = "AVAILABLE",
    claim_type: EpistemicType = EpistemicType.DERIVED,
    upstream_claim_ids: Iterable[str] = (),
    supporting_claim_ids: Iterable[str] = (),
    contradicting_claim_ids: Iterable[str] = (),
    confirmation_needed: Iterable[str] = (),
    invalidation_conditions: Iterable[str] = (),
    calibration_id: str | None = None,
) -> SpecialistEvidenceInputV2:
    """Hash a frozen/dataclass/mapping specialist output without recalculation."""
    output_hash = _extract_or_hash_output(source_output)
    return SpecialistEvidenceInputV2(
        claim_id=claim_id,
        statement=statement,
        source_engine=source_engine,
        source_output_hash=output_hash,
        calculation_version=calculation_version,
        dependency_family=dependency_family,
        correlation_group=correlation_group,
        availability=availability,
        quality=quality,
        claim_type=claim_type,
        upstream_claim_ids=tuple(upstream_claim_ids),
        supporting_claim_ids=tuple(supporting_claim_ids),
        contradicting_claim_ids=tuple(contradicting_claim_ids),
        confirmation_needed=tuple(confirmation_needed),
        invalidation_conditions=tuple(invalidation_conditions),
        calibration_id=calibration_id,
    )


def _extract_or_hash_output(value: Any) -> str:
    for name in ("evidence_hash", "graph_hash", "state_hash", "structure_hash", "level_graph_hash", "provenance_hash", "kernel_hash", "morphology_hash", "dag_hash"):
        candidate = getattr(value, name, None)
        if isinstance(candidate, str) and len(candidate) == 64:
            return candidate.lower()
    if isinstance(value, Mapping):
        for name in ("evidence_hash", "graph_hash", "state_hash", "structure_hash", "level_graph_hash", "provenance_hash", "kernel_hash", "morphology_hash", "dag_hash"):
            candidate = value.get(name)
            if isinstance(candidate, str) and len(candidate) == 64:
                return candidate.lower()
    return _stable_hash(_json_safe(value))


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {name: _json_safe(getattr(value, name)) for name in sorted(value.__dataclass_fields__)}
    return repr(value)


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
