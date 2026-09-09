from __future__ import annotations

"""Canonical M3.3 memory-world composition and conservative health analysis.

The world preserves corpus/retrieval provenance and exposes OOD, drift,
quarantine, sample insufficiency and unknown decay explicitly.  It never
flattens memory into a trading score and never gains decision authority.
"""

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Literal, Sequence

from .canonical_analog_memory import AnalogRetrievalResult
from .canonical_memory_intelligence import CanonicalMemoryEpisode
from .memory_corpus import MemoryCorpus, MemoryRecord


CANONICAL_MEMORY_WORLD_VERSION = "canonical-memory-world.v1"
MAX_MEMORY_WORLD_BYTES = 64_000

State = Literal["CLEAR", "WATCH", "ALERT", "UNKNOWN"]
Confidence = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN", "OOD", "CONFLICTING", "INSUFFICIENT_EVIDENCE"]


class CanonicalMemoryWorldError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MemoryHealth:
    ood: bool
    drift_state: State
    decay_state: State
    quarantine_state: State
    small_sample: bool
    outcome_distribution_divergence: float | None
    recent_independent_count: int
    baseline_independent_count: int
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ood": self.ood,
            "drift_state": self.drift_state,
            "decay_state": self.decay_state,
            "quarantine_state": self.quarantine_state,
            "small_sample": self.small_sample,
            "outcome_distribution_divergence": self.outcome_distribution_divergence,
            "recent_independent_count": self.recent_independent_count,
            "baseline_independent_count": self.baseline_independent_count,
            "reason_codes": list(self.reason_codes),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CanonicalMemoryWorld:
    engine_id: str
    calculation_version: str
    d2_snapshot_hash: str
    decision_time_ns: int
    corpus_hash: str
    feature_version: str
    label_version: str
    raw_record_count: int
    independent_episode_count: int
    retrieved_episode_count: int
    independent_retrieved_episode_count: int
    supporting_facts: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_facts: tuple[str, ...]
    degraded_facts: tuple[str, ...]
    failure_risks: tuple[str, ...]
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    ood: bool
    drift_state: State
    decay_state: State
    quarantine_state: State
    source_episode_hashes: tuple[str, ...]
    source_snapshot_hashes: tuple[str, ...]
    source_output_hashes: tuple[str, ...]
    availability: str
    quality: str
    confidence: Confidence
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
            "engine_id": self.engine_id,
            "calculation_version": self.calculation_version,
            "d2_snapshot_hash": self.d2_snapshot_hash,
            "decision_time_ns": self.decision_time_ns,
            "corpus_hash": self.corpus_hash,
            "feature_version": self.feature_version,
            "label_version": self.label_version,
            "raw_record_count": self.raw_record_count,
            "independent_episode_count": self.independent_episode_count,
            "retrieved_episode_count": self.retrieved_episode_count,
            "independent_retrieved_episode_count": self.independent_retrieved_episode_count,
            "supporting_facts": list(self.supporting_facts),
            "contradictions": list(self.contradictions),
            "missing_facts": list(self.missing_facts),
            "degraded_facts": list(self.degraded_facts),
            "failure_risks": list(self.failure_risks),
            "reason_codes": list(self.reason_codes),
            "warnings": list(self.warnings),
            "ood": self.ood,
            "drift_state": self.drift_state,
            "decay_state": self.decay_state,
            "quarantine_state": self.quarantine_state,
            "source_episode_hashes": list(self.source_episode_hashes),
            "source_snapshot_hashes": list(self.source_snapshot_hashes),
            "source_output_hashes": list(self.source_output_hashes),
            "availability": self.availability,
            "quality": self.quality,
            "confidence": self.confidence,
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


def analyze_memory_health(
    *,
    corpus: MemoryCorpus,
    analogs: AnalogRetrievalResult,
    recent_episode_count: int = 50,
    minimum_window_count: int = 10,
    drift_watch_threshold: float = 0.15,
    drift_alert_threshold: float = 0.30,
) -> MemoryHealth:
    if analogs.corpus_hash != corpus.corpus_hash:
        raise CanonicalMemoryWorldError("ANALOG_CORPUS_HASH_MISMATCH")
    if recent_episode_count < 1 or minimum_window_count < 1:
        raise CanonicalMemoryWorldError("INVALID_HEALTH_WINDOW")
    if not 0 <= drift_watch_threshold <= drift_alert_threshold <= 1:
        raise CanonicalMemoryWorldError("INVALID_DRIFT_THRESHOLDS")

    usable = [record for record in corpus.records if not record.quarantined and record.label is not None]
    usable.sort(key=lambda record: (record.episode.decision_time_ns, record.episode.episode_hash))
    recent = usable[-recent_episode_count:]
    baseline = usable[:-recent_episode_count]
    reason_codes: list[str] = []
    warnings: list[str] = []

    divergence: float | None = None
    if len(recent) >= minimum_window_count and len(baseline) >= minimum_window_count:
        divergence = _total_variation(_outcome_distribution(recent), _outcome_distribution(baseline))
        if divergence >= drift_alert_threshold:
            drift_state: State = "ALERT"
            reason_codes.append("OUTCOME_DISTRIBUTION_DRIFT_ALERT")
        elif divergence >= drift_watch_threshold:
            drift_state = "WATCH"
            reason_codes.append("OUTCOME_DISTRIBUTION_DRIFT_WATCH")
        else:
            drift_state = "CLEAR"
    else:
        drift_state = "UNKNOWN"
        reason_codes.append("INSUFFICIENT_INDEPENDENT_WINDOWS_FOR_DRIFT")

    quarantine_fraction = (corpus.quarantined_count / corpus.episode_count) if corpus.episode_count else 0.0
    if corpus.quarantined_count == 0:
        quarantine_state: State = "CLEAR"
    elif quarantine_fraction >= 0.20:
        quarantine_state = "ALERT"
        reason_codes.append("HIGH_QUARANTINE_FRACTION")
    else:
        quarantine_state = "WATCH"
        reason_codes.append("QUARANTINED_MEMORY_PRESENT")

    # Outcome labels are multi-class market behavior labels, not a universal
    # strategy success label.  Therefore an edge-decay assertion would be
    # fabricated here.  Keep decay unknown until a policy-specific calibration
    # specialist supplies a valid success/utility definition.
    decay_state: State = "UNKNOWN"
    reason_codes.append("EDGE_DECAY_REQUIRES_POLICY_SPECIFIC_UTILITY_LABEL")

    small_sample = corpus.independent_episode_count < minimum_window_count
    if small_sample:
        reason_codes.append("SMALL_INDEPENDENT_SAMPLE")
    if analogs.ood:
        warnings.extend(analogs.ood_reasons)

    return MemoryHealth(
        ood=analogs.ood,
        drift_state=drift_state,
        decay_state=decay_state,
        quarantine_state=quarantine_state,
        small_sample=small_sample,
        outcome_distribution_divergence=round(divergence, 12) if divergence is not None else None,
        recent_independent_count=len(recent),
        baseline_independent_count=len(baseline),
        reason_codes=tuple(sorted(set(reason_codes))),
        warnings=tuple(sorted(set(warnings))),
    )


def build_canonical_memory_world(
    *,
    query_episode: CanonicalMemoryEpisode,
    corpus: MemoryCorpus,
    analogs: AnalogRetrievalResult,
    health: MemoryHealth,
) -> CanonicalMemoryWorld:
    if query_episode.decision_time_ns != analogs.decision_time_ns:
        raise CanonicalMemoryWorldError("DECISION_TIME_MISMATCH")
    if corpus.corpus_hash != analogs.corpus_hash:
        raise CanonicalMemoryWorldError("CORPUS_HASH_MISMATCH")
    if corpus.corpus_cutoff_time_ns < query_episode.decision_time_ns:
        raise CanonicalMemoryWorldError("CORPUS_CUTOFF_BEFORE_DECISION")

    supporting = tuple(sorted(set(analogs.supporting_facts)))
    contradictions = tuple(sorted(set(analogs.contradictions) | set(query_episode.contradictions)))
    missing = tuple(sorted(set(query_episode.missing_facts)))
    degraded = tuple(sorted(set(query_episode.degraded_facts)))
    failure_risks = set(query_episode.failure_risks)
    if health.ood:
        failure_risks.add("MEMORY_OOD")
    if health.drift_state in {"WATCH", "ALERT"}:
        failure_risks.add("MEMORY_DRIFT")
    if health.quarantine_state in {"WATCH", "ALERT"}:
        failure_risks.add("MEMORY_QUARANTINE")
    if health.small_sample:
        failure_risks.add("MEMORY_SMALL_SAMPLE")

    reasons = tuple(sorted(set(health.reason_codes) | set(analogs.ood_reasons)))
    warnings = tuple(sorted(set(query_episode.warnings) | set(analogs.warnings) | set(health.warnings)))
    source_episode_hashes = tuple(match.episode_hash for match in analogs.matches)
    source_snapshot_hashes = tuple(
        sorted(
            {
                source_hash
                for match in analogs.matches
                for record in corpus.records
                if record.episode.episode_hash == match.episode_hash
                for source_hash in record.episode.source_snapshot_hashes
            }
        )
    )
    source_output_hashes = tuple(
        sorted(
            {
                source_hash
                for match in analogs.matches
                for record in corpus.records
                if record.episode.episode_hash == match.episode_hash
                for source_hash in record.episode.source_output_hashes
            }
        )
    )

    if corpus.episode_count == 0:
        availability = "UNAVAILABLE"
        quality = "NO_MEMORY"
        confidence: Confidence = "INSUFFICIENT_EVIDENCE"
    elif health.ood:
        availability = "DEGRADED"
        quality = "OOD"
        confidence = "OOD"
    elif contradictions:
        availability = "DEGRADED"
        quality = "CONFLICTING"
        confidence = "CONFLICTING"
    elif health.drift_state == "ALERT" or health.quarantine_state == "ALERT":
        availability = "DEGRADED"
        quality = "DEGRADED"
        confidence = "LOW"
    elif health.small_sample or analogs.independent_analog_count == 0:
        availability = "DEGRADED"
        quality = "LOW_EVIDENCE"
        confidence = "INSUFFICIENT_EVIDENCE"
    else:
        availability = "AVAILABLE"
        quality = "CAUSAL_MEMORY"
        confidence = "MEDIUM"

    seed = {
        "calculation_version": CANONICAL_MEMORY_WORLD_VERSION,
        "d2_snapshot_hash": query_episode.d2_snapshot_hash,
        "decision_time_ns": query_episode.decision_time_ns,
        "corpus_hash": corpus.corpus_hash,
        "feature_version": corpus.feature_version,
        "label_version": corpus.label_version,
        "analog_output_hash": analogs.output_hash,
        "health": health.as_dict(),
        "supporting_facts": supporting,
        "contradictions": contradictions,
        "missing_facts": missing,
        "degraded_facts": degraded,
        "failure_risks": sorted(failure_risks),
        "reason_codes": reasons,
        "availability": availability,
        "quality": quality,
        "confidence": confidence,
    }
    output_hash = _stable_hash(seed)
    world = CanonicalMemoryWorld(
        engine_id="CANONICAL_MEMORY_WORLD",
        calculation_version=CANONICAL_MEMORY_WORLD_VERSION,
        d2_snapshot_hash=query_episode.d2_snapshot_hash,
        decision_time_ns=query_episode.decision_time_ns,
        corpus_hash=corpus.corpus_hash,
        feature_version=corpus.feature_version,
        label_version=corpus.label_version,
        raw_record_count=corpus.raw_record_count,
        independent_episode_count=corpus.independent_episode_count,
        retrieved_episode_count=analogs.raw_nearest_neighbor_count,
        independent_retrieved_episode_count=analogs.independent_analog_count,
        supporting_facts=supporting,
        contradictions=contradictions,
        missing_facts=missing,
        degraded_facts=degraded,
        failure_risks=tuple(sorted(failure_risks)),
        reason_codes=reasons,
        warnings=warnings,
        ood=health.ood,
        drift_state=health.drift_state,
        decay_state=health.decay_state,
        quarantine_state=health.quarantine_state,
        source_episode_hashes=source_episode_hashes,
        source_snapshot_hashes=source_snapshot_hashes,
        source_output_hashes=source_output_hashes,
        availability=availability,
        quality=quality,
        confidence=confidence,
        output_hash=output_hash,
    )
    encoded = json.dumps(world.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_MEMORY_WORLD_BYTES:
        raise CanonicalMemoryWorldError("BOUNDED_MEMORY_WORLD_EXCEEDED")
    return world


def _outcome_distribution(records: Sequence[MemoryRecord]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for record in records:
        if record.label is None:
            continue
        counts[record.label.outcome_class] = counts.get(record.label.outcome_class, 0) + 1
    total = sum(counts.values())
    return {key: value / total for key, value in counts.items()} if total else {}


def _total_variation(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return 0.5 * sum(abs(a.get(key, 0.0) - b.get(key, 0.0)) for key in keys)


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
