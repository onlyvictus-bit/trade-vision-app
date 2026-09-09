from __future__ import annotations

"""Canonical M3.3 reliability view over PIT-safe real memory records.

The view deliberately models *historical outcome distribution*, not a universal
"win probability". A market-behaviour label only becomes strategy success after
a policy-specific utility definition exists. This prevents the memory layer from
inventing trade authority while still exposing calibrated, shrinkage-aware
historical evidence to later reasoning.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .canonical_memory_intelligence import CanonicalMemoryEpisode
from .memory_corpus import MemoryCorpus, MemoryRecord, retrieve_pit_records


CANONICAL_RELIABILITY_MEMORY_VERSION = "canonical-reliability-memory.v1"
OUTCOME_CLASSES = (
    "BREAKOUT_FAILURE",
    "CONTINUATION",
    "EXHAUSTION",
    "NO_EDGE",
    "REVERSAL",
    "TRAP",
)
MAX_RECEIPT_BYTES = 48_000


class CanonicalReliabilityMemoryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalReliabilityMemory:
    calculation_version: str
    d2_snapshot_hash: str
    decision_time_ns: int
    corpus_hash: str
    conditioning_keys: tuple[str, ...]
    raw_labelled_record_count: int
    independent_episode_count: int
    independent_session_count: int
    matched_session_phase_count: int
    matched_regime_count: int
    outcome_counts: dict[str, int]
    posterior_outcome_distribution: dict[str, float]
    recent_outcome_distribution: dict[str, float]
    baseline_outcome_distribution: dict[str, float]
    recent_baseline_divergence: float | None
    minimum_sample_size: int
    minimum_sample_pass: bool
    availability: str
    confidence: str
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    source_episode_hashes: tuple[str, ...]
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
            "d2_snapshot_hash": self.d2_snapshot_hash,
            "decision_time_ns": self.decision_time_ns,
            "corpus_hash": self.corpus_hash,
            "conditioning_keys": list(self.conditioning_keys),
            "raw_labelled_record_count": self.raw_labelled_record_count,
            "independent_episode_count": self.independent_episode_count,
            "independent_session_count": self.independent_session_count,
            "matched_session_phase_count": self.matched_session_phase_count,
            "matched_regime_count": self.matched_regime_count,
            "outcome_counts": self.outcome_counts,
            "posterior_outcome_distribution": self.posterior_outcome_distribution,
            "recent_outcome_distribution": self.recent_outcome_distribution,
            "baseline_outcome_distribution": self.baseline_outcome_distribution,
            "recent_baseline_divergence": self.recent_baseline_divergence,
            "minimum_sample_size": self.minimum_sample_size,
            "minimum_sample_pass": self.minimum_sample_pass,
            "availability": self.availability,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "warnings": list(self.warnings),
            "source_episode_hashes": list(self.source_episode_hashes),
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


def build_canonical_reliability_memory(
    *,
    query_episode: CanonicalMemoryEpisode,
    corpus: MemoryCorpus,
    minimum_sample_size: int = 30,
    recent_window: int = 30,
    prior_strength: float = 1.0,
) -> CanonicalReliabilityMemory:
    if minimum_sample_size < 1 or recent_window < 1:
        raise CanonicalReliabilityMemoryError("INVALID_SAMPLE_POLICY")
    if not isinstance(prior_strength, (int, float)) or isinstance(prior_strength, bool) or prior_strength <= 0:
        raise CanonicalReliabilityMemoryError("INVALID_PRIOR_STRENGTH")
    if corpus.corpus_cutoff_time_ns < query_episode.decision_time_ns:
        raise CanonicalReliabilityMemoryError("CORPUS_CUTOFF_BEFORE_DECISION")

    records = [
        record
        for record in retrieve_pit_records(
            corpus,
            decision_time_ns=query_episode.decision_time_ns,
            labelled_only=True,
            include_quarantined=False,
        )
        if record.episode.symbol == query_episode.symbol
        and record.episode.timeframe == query_episode.timeframe
        and record.label is not None
    ]
    records.sort(key=lambda item: (item.episode.decision_time_ns, item.episode.episode_hash))

    regime_id = _regime_id(query_episode)
    matched_session = [record for record in records if record.episode.session_phase == query_episode.session_phase]
    matched_regime = [record for record in records if regime_id and _regime_id(record.episode) == regime_id]
    conditioned = records
    conditioning = ["symbol", "timeframe"]
    if matched_session:
        conditioned = matched_session
        conditioning.append("session_phase")
    if regime_id:
        intersection = [record for record in conditioned if _regime_id(record.episode) == regime_id]
        if intersection:
            conditioned = intersection
            conditioning.append("regime_id")

    # One canonical episode contributes at most one label to this view.
    by_episode: dict[str, MemoryRecord] = {}
    for record in conditioned:
        by_episode[record.episode.episode_hash] = record
    independent = tuple(sorted(by_episode.values(), key=lambda item: (item.episode.decision_time_ns, item.episode.episode_hash)))
    counts = {outcome: 0 for outcome in OUTCOME_CLASSES}
    for record in independent:
        assert record.label is not None
        outcome = record.label.outcome_class
        counts[outcome] = counts.get(outcome, 0) + 1

    n = len(independent)
    denominator = n + float(prior_strength) * len(OUTCOME_CLASSES)
    posterior = {
        outcome: round((counts.get(outcome, 0) + float(prior_strength)) / denominator, 12)
        for outcome in OUTCOME_CLASSES
    }

    recent = independent[-recent_window:]
    baseline = independent[:-recent_window]
    recent_distribution = _distribution(recent)
    baseline_distribution = _distribution(baseline)
    divergence = (
        _total_variation(recent_distribution, baseline_distribution)
        if recent and baseline
        else None
    )

    reason_codes: list[str] = []
    warnings: list[str] = []
    minimum_pass = n >= minimum_sample_size
    if not independent:
        availability = "UNAVAILABLE"
        confidence = "INSUFFICIENT_EVIDENCE"
        reason_codes.append("NO_PIT_VALID_LABELLED_MEMORY")
    elif not minimum_pass:
        availability = "DEGRADED"
        confidence = "INSUFFICIENT_EVIDENCE"
        reason_codes.append("LOW_INDEPENDENT_SAMPLE")
    else:
        availability = "AVAILABLE"
        confidence = "MEDIUM"
    if divergence is None:
        reason_codes.append("RECENT_BASELINE_DRIFT_UNAVAILABLE")
    elif divergence >= 0.30:
        availability = "DEGRADED"
        confidence = "LOW"
        reason_codes.append("RECENT_OUTCOME_DISTRIBUTION_DRIFT_ALERT")
    elif divergence >= 0.15:
        reason_codes.append("RECENT_OUTCOME_DISTRIBUTION_DRIFT_WATCH")
    warnings.append("Outcome-class posterior is descriptive historical memory, not a strategy win probability.")

    source_hashes = tuple(record.episode.episode_hash for record in independent)
    seed = {
        "calculation_version": CANONICAL_RELIABILITY_MEMORY_VERSION,
        "d2_snapshot_hash": query_episode.d2_snapshot_hash,
        "decision_time_ns": query_episode.decision_time_ns,
        "corpus_hash": corpus.corpus_hash,
        "conditioning_keys": conditioning,
        "source_episode_hashes": source_hashes,
        "outcome_counts": counts,
        "posterior": posterior,
        "recent": recent_distribution,
        "baseline": baseline_distribution,
        "divergence": divergence,
        "minimum_sample_size": minimum_sample_size,
        "availability": availability,
        "confidence": confidence,
        "reason_codes": sorted(set(reason_codes)),
    }
    output_hash = _stable_hash(seed)
    result = CanonicalReliabilityMemory(
        calculation_version=CANONICAL_RELIABILITY_MEMORY_VERSION,
        d2_snapshot_hash=query_episode.d2_snapshot_hash,
        decision_time_ns=query_episode.decision_time_ns,
        corpus_hash=corpus.corpus_hash,
        conditioning_keys=tuple(conditioning),
        raw_labelled_record_count=len(records),
        independent_episode_count=n,
        independent_session_count=len({record.episode.session_id for record in independent}),
        matched_session_phase_count=len(matched_session),
        matched_regime_count=len(matched_regime),
        outcome_counts=dict(sorted(counts.items())),
        posterior_outcome_distribution=dict(sorted(posterior.items())),
        recent_outcome_distribution=dict(sorted(recent_distribution.items())),
        baseline_outcome_distribution=dict(sorted(baseline_distribution.items())),
        recent_baseline_divergence=round(divergence, 12) if divergence is not None else None,
        minimum_sample_size=minimum_sample_size,
        minimum_sample_pass=minimum_pass,
        availability=availability,
        confidence=confidence,
        reason_codes=tuple(sorted(set(reason_codes))),
        warnings=tuple(sorted(set(warnings))),
        source_episode_hashes=source_hashes,
        output_hash=output_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_RECEIPT_BYTES:
        raise CanonicalReliabilityMemoryError("BOUNDED_RELIABILITY_RECEIPT_EXCEEDED")
    return result


def _regime_id(episode: CanonicalMemoryEpisode) -> str | None:
    for family in ("regime", "context", "market_regime"):
        payload = episode.fact_families.get(family)
        if isinstance(payload, Mapping):
            value = payload.get("regime_id") or payload.get("regime")
            if value is not None and str(value).strip():
                return str(value).strip()
    return None


def _distribution(records: Sequence[MemoryRecord]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for record in records:
        if record.label is None:
            continue
        key = record.label.outcome_class
        counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return {}
    return {key: round(value / total, 12) for key, value in sorted(counts.items())}


def _total_variation(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    keys = set(a) | set(b)
    return round(0.5 * sum(abs(float(a.get(key, 0.0)) - float(b.get(key, 0.0))) for key in keys), 12)


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
