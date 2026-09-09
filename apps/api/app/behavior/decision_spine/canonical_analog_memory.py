from __future__ import annotations

"""Deterministic M3.3 analog retrieval over the canonical memory corpus.

The retriever is intentionally evidence-only.  It uses an explicit versioned
feature manifest, never generated/mock history, and keeps raw nearest neighbors
separate from a conservative independent subset.  Same-session episodes and
records with overlapping labelled outcome horizons cannot both count as
independent confirmation.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal, Sequence

from .canonical_memory_intelligence import CanonicalMemoryEpisode
from .memory_corpus import MemoryCorpus, MemoryRecord, retrieve_pit_records


ANALOG_RETRIEVAL_VERSION = "canonical-analog-retrieval.v1"
MAX_FEATURE_SPECS = 128
MAX_ANALOGS = 100

FeatureKind = Literal["NUMERIC", "CATEGORICAL", "BOOLEAN"]


class CanonicalAnalogError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AnalogFeatureSpec:
    path: str
    kind: FeatureKind
    weight: float = 1.0
    scale: float = 1.0
    required: bool = True


@dataclass(frozen=True, slots=True)
class AnalogMatch:
    episode_hash: str
    symbol: str
    session_id: str
    decision_time_ns: int
    distance: float
    similarity: float
    outcome_class: str | None
    matched_features: tuple[str, ...]
    mismatched_features: tuple[str, ...]
    unavailable_features: tuple[str, ...]
    independent: bool
    independence_blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_hash": self.episode_hash,
            "symbol": self.symbol,
            "session_id": self.session_id,
            "decision_time_ns": self.decision_time_ns,
            "distance": self.distance,
            "similarity": self.similarity,
            "outcome_class": self.outcome_class,
            "matched_features": list(self.matched_features),
            "mismatched_features": list(self.mismatched_features),
            "unavailable_features": list(self.unavailable_features),
            "independent": self.independent,
            "independence_blockers": list(self.independence_blockers),
        }


@dataclass(frozen=True, slots=True)
class AnalogRetrievalResult:
    calculation_version: str
    feature_manifest_version: str
    feature_manifest_hash: str
    corpus_hash: str
    query_episode_hash: str
    decision_time_ns: int
    raw_nearest_neighbor_count: int
    independent_analog_count: int
    matches: tuple[AnalogMatch, ...]
    ood: bool
    ood_reasons: tuple[str, ...]
    supporting_facts: tuple[str, ...]
    contradictions: tuple[str, ...]
    warnings: tuple[str, ...]
    output_hash: str
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
            "calculation_version": self.calculation_version,
            "feature_manifest_version": self.feature_manifest_version,
            "feature_manifest_hash": self.feature_manifest_hash,
            "corpus_hash": self.corpus_hash,
            "query_episode_hash": self.query_episode_hash,
            "decision_time_ns": self.decision_time_ns,
            "raw_nearest_neighbor_count": self.raw_nearest_neighbor_count,
            "independent_analog_count": self.independent_analog_count,
            "matches": [match.as_dict() for match in self.matches],
            "ood": self.ood,
            "ood_reasons": list(self.ood_reasons),
            "supporting_facts": list(self.supporting_facts),
            "contradictions": list(self.contradictions),
            "warnings": list(self.warnings),
            "output_hash": self.output_hash,
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


def retrieve_analogs(
    *,
    query_episode: CanonicalMemoryEpisode,
    corpus: MemoryCorpus,
    decision_time_ns: int,
    feature_manifest_version: str,
    feature_specs: Sequence[AnalogFeatureSpec],
    max_analogs: int = 20,
    labelled_only: bool = True,
    maximum_distance: float = 0.65,
    minimum_independent_analogs: int = 5,
) -> AnalogRetrievalResult:
    if query_episode.decision_time_ns != decision_time_ns:
        raise CanonicalAnalogError("QUERY_DECISION_TIME_MISMATCH")
    if decision_time_ns > corpus.corpus_cutoff_time_ns:
        raise CanonicalAnalogError("QUERY_AFTER_CORPUS_CUTOFF")
    if not feature_manifest_version.strip():
        raise CanonicalAnalogError("EMPTY_FEATURE_MANIFEST_VERSION")
    specs = _validate_specs(feature_specs)
    if not 1 <= max_analogs <= MAX_ANALOGS:
        raise CanonicalAnalogError("INVALID_MAX_ANALOGS")
    if not 0.0 <= maximum_distance <= 1.0:
        raise CanonicalAnalogError("INVALID_MAXIMUM_DISTANCE")
    if minimum_independent_analogs < 1:
        raise CanonicalAnalogError("INVALID_MINIMUM_INDEPENDENT_ANALOGS")

    manifest_seed = [
        {"path": spec.path, "kind": spec.kind, "weight": spec.weight, "scale": spec.scale, "required": spec.required}
        for spec in specs
    ]
    manifest_hash = _stable_hash({"version": feature_manifest_version, "specs": manifest_seed})

    query_values = {spec.path: _read_path(query_episode, spec.path) for spec in specs}
    missing_required = tuple(sorted(spec.path for spec in specs if spec.required and query_values[spec.path] is None))
    ood_reasons = list(f"QUERY_REQUIRED_FEATURE_MISSING:{path}" for path in missing_required)

    eligible = retrieve_pit_records(
        corpus,
        decision_time_ns=decision_time_ns,
        labelled_only=labelled_only,
        include_quarantined=False,
    )
    scored: list[tuple[float, MemoryRecord, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []
    for record in eligible:
        if record.episode.episode_hash == query_episode.episode_hash:
            continue
        scored_item = _distance(query_values, record.episode, specs)
        if scored_item is None:
            continue
        distance, matched, mismatched, unavailable = scored_item
        if distance <= maximum_distance:
            scored.append((distance, record, matched, mismatched, unavailable))

    scored.sort(key=lambda item: (item[0], item[1].episode.episode_hash))
    scored = scored[:max_analogs]
    independent_records: list[MemoryRecord] = []
    matches: list[AnalogMatch] = []
    for distance, record, matched, mismatched, unavailable in scored:
        blockers = _independence_blockers(record, independent_records)
        independent = not blockers
        if independent:
            independent_records.append(record)
        matches.append(
            AnalogMatch(
                episode_hash=record.episode.episode_hash,
                symbol=record.episode.symbol,
                session_id=record.episode.session_id,
                decision_time_ns=record.episode.decision_time_ns,
                distance=round(distance, 12),
                similarity=round(1.0 - distance, 12),
                outcome_class=record.label.outcome_class if record.label else None,
                matched_features=matched,
                mismatched_features=mismatched,
                unavailable_features=unavailable,
                independent=independent,
                independence_blockers=blockers,
            )
        )

    if len(independent_records) < minimum_independent_analogs:
        ood_reasons.append(
            f"INSUFFICIENT_INDEPENDENT_ANALOGS:{len(independent_records)}<{minimum_independent_analogs}"
        )
    if not matches:
        ood_reasons.append("NO_ANALOG_WITHIN_DISTANCE_BOUND")

    outcome_counts: dict[str, int] = {}
    for match in matches:
        if match.independent and match.outcome_class:
            outcome_counts[match.outcome_class] = outcome_counts.get(match.outcome_class, 0) + 1
    supporting = tuple(
        f"{outcome}:{count}_independent_analogs"
        for outcome, count in sorted(outcome_counts.items(), key=lambda item: (-item[1], item[0]))
    )
    contradictions = tuple(
        f"MULTIPLE_OUTCOME_FAMILIES:{','.join(sorted(outcome_counts))}"
        for _ in [0]
        if len(outcome_counts) > 1
    )
    warnings = tuple(
        sorted(
            {
                *("Raw nearest-neighbor count exceeds independent analog count." for _ in [0] if len(matches) > len(independent_records)),
                *(f"Query missing required feature {path}." for path in missing_required),
            }
        )
    )
    output_seed = {
        "calculation_version": ANALOG_RETRIEVAL_VERSION,
        "feature_manifest_version": feature_manifest_version,
        "feature_manifest_hash": manifest_hash,
        "corpus_hash": corpus.corpus_hash,
        "query_episode_hash": query_episode.episode_hash,
        "decision_time_ns": decision_time_ns,
        "matches": [match.as_dict() for match in matches],
        "ood_reasons": sorted(set(ood_reasons)),
        "supporting_facts": supporting,
        "contradictions": contradictions,
    }
    return AnalogRetrievalResult(
        calculation_version=ANALOG_RETRIEVAL_VERSION,
        feature_manifest_version=feature_manifest_version,
        feature_manifest_hash=manifest_hash,
        corpus_hash=corpus.corpus_hash,
        query_episode_hash=query_episode.episode_hash,
        decision_time_ns=decision_time_ns,
        raw_nearest_neighbor_count=len(matches),
        independent_analog_count=len(independent_records),
        matches=tuple(matches),
        ood=bool(ood_reasons),
        ood_reasons=tuple(sorted(set(ood_reasons))),
        supporting_facts=supporting,
        contradictions=contradictions,
        warnings=warnings,
        output_hash=_stable_hash(output_seed),
    )


def _validate_specs(specs: Sequence[AnalogFeatureSpec]) -> tuple[AnalogFeatureSpec, ...]:
    if isinstance(specs, (str, bytes)) or not specs or len(specs) > MAX_FEATURE_SPECS:
        raise CanonicalAnalogError("INVALID_FEATURE_SPECS")
    normalized = tuple(sorted(specs, key=lambda spec: spec.path))
    if len({spec.path for spec in normalized}) != len(normalized):
        raise CanonicalAnalogError("DUPLICATE_FEATURE_PATH")
    for spec in normalized:
        if spec.kind not in {"NUMERIC", "CATEGORICAL", "BOOLEAN"}:
            raise CanonicalAnalogError(f"INVALID_FEATURE_KIND:{spec.path}")
        if not spec.path.strip() or "." not in spec.path:
            raise CanonicalAnalogError("INVALID_FEATURE_PATH")
        if not isinstance(spec.weight, (int, float)) or isinstance(spec.weight, bool) or spec.weight <= 0:
            raise CanonicalAnalogError(f"INVALID_FEATURE_WEIGHT:{spec.path}")
        if spec.kind == "NUMERIC" and (
            not isinstance(spec.scale, (int, float)) or isinstance(spec.scale, bool) or spec.scale <= 0
        ):
            raise CanonicalAnalogError(f"INVALID_FEATURE_SCALE:{spec.path}")
    return normalized


def _read_path(episode: CanonicalMemoryEpisode, path: str) -> Any:
    family, key = path.split(".", 1)
    facts = episode.fact_families.get(family)
    if facts is None:
        return None
    return facts.get(key)


def _distance(query_values: dict[str, Any], candidate: CanonicalMemoryEpisode, specs: Sequence[AnalogFeatureSpec]):
    weighted_distance = 0.0
    total_weight = 0.0
    matched: list[str] = []
    mismatched: list[str] = []
    unavailable: list[str] = []
    for spec in specs:
        query = query_values[spec.path]
        value = _read_path(candidate, spec.path)
        if query is None or value is None:
            unavailable.append(spec.path)
            if spec.required:
                return None
            continue
        if spec.kind == "NUMERIC":
            if isinstance(query, bool) or isinstance(value, bool):
                return None
            try:
                component = min(abs(float(query) - float(value)) / float(spec.scale), 1.0)
            except (TypeError, ValueError):
                return None
        elif spec.kind == "BOOLEAN":
            if not isinstance(query, bool) or not isinstance(value, bool):
                return None
            component = 0.0 if query is value else 1.0
        else:
            component = 0.0 if str(query) == str(value) else 1.0
        weighted_distance += component * float(spec.weight)
        total_weight += float(spec.weight)
        (matched if component <= 0.25 else mismatched).append(spec.path)
    if total_weight <= 0:
        return None
    return (
        weighted_distance / total_weight,
        tuple(sorted(matched)),
        tuple(sorted(mismatched)),
        tuple(sorted(unavailable)),
    )


def _independence_blockers(record: MemoryRecord, accepted: Sequence[MemoryRecord]) -> tuple[str, ...]:
    blockers: list[str] = []
    for other in accepted:
        if record.episode.session_id == other.episode.session_id:
            blockers.append(f"SAME_SESSION:{other.episode.episode_hash}")
        if _outcome_horizons_overlap(record, other):
            blockers.append(f"OVERLAPPING_OUTCOME_HORIZON:{other.episode.episode_hash}")
        if set(record.episode.source_snapshot_hashes) & set(other.episode.source_snapshot_hashes):
            blockers.append(f"SHARED_SOURCE_SNAPSHOT:{other.episode.episode_hash}")
    return tuple(sorted(set(blockers)))


def _outcome_horizons_overlap(a: MemoryRecord, b: MemoryRecord) -> bool:
    if a.label is None or b.label is None:
        return False
    a_start = a.episode.decision_time_ns
    a_end = a_start + a.label.outcome_horizon_ns
    b_start = b.episode.decision_time_ns
    b_end = b_start + b.label.outcome_horizon_ns
    return max(a_start, b_start) < min(a_end, b_end)


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
