from __future__ import annotations

"""Canonical M3.3 historical session memory.

M3.2 owns the *current* session state.  This module owns only historical,
PIT-safe outcome memory conditioned by the already-frozen M3.2 session identity.
No synthetic exact-time profile is generated when history is absent.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .canonical_memory_intelligence import CanonicalMemoryEpisode
from .memory_corpus import MemoryCorpus, MemoryRecord, retrieve_pit_records


CANONICAL_SESSION_MEMORY_VERSION = "canonical-session-memory.v1"
MAX_RECEIPT_BYTES = 48_000


class CanonicalSessionMemoryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalSessionMemory:
    calculation_version: str
    d2_snapshot_hash: str
    decision_time_ns: int
    corpus_hash: str
    current_session_id: str
    current_session_phase: str
    day_of_week: str | None
    calendar_class: str | None
    independent_phase_episode_count: int
    independent_day_episode_count: int
    independent_calendar_episode_count: int
    phase_outcome_distribution: dict[str, float]
    day_outcome_distribution: dict[str, float]
    calendar_outcome_distribution: dict[str, float]
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
            "current_session_id": self.current_session_id,
            "current_session_phase": self.current_session_phase,
            "day_of_week": self.day_of_week,
            "calendar_class": self.calendar_class,
            "independent_phase_episode_count": self.independent_phase_episode_count,
            "independent_day_episode_count": self.independent_day_episode_count,
            "independent_calendar_episode_count": self.independent_calendar_episode_count,
            "phase_outcome_distribution": self.phase_outcome_distribution,
            "day_outcome_distribution": self.day_outcome_distribution,
            "calendar_outcome_distribution": self.calendar_outcome_distribution,
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


def build_canonical_session_memory(
    *,
    query_episode: CanonicalMemoryEpisode,
    corpus: MemoryCorpus,
    minimum_sample_size: int = 30,
) -> CanonicalSessionMemory:
    if minimum_sample_size < 1:
        raise CanonicalSessionMemoryError("INVALID_MINIMUM_SAMPLE")
    if corpus.corpus_cutoff_time_ns < query_episode.decision_time_ns:
        raise CanonicalSessionMemoryError("CORPUS_CUTOFF_BEFORE_DECISION")

    query_session = _session_facts(query_episode)
    day_of_week = _text(query_session.get("day_of_week"))
    calendar_class = _text(query_session.get("calendar_class"))
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

    phase_records = _unique_episodes(
        record for record in records if record.episode.session_phase == query_episode.session_phase
    )
    day_records = _unique_episodes(
        record
        for record in phase_records
        if day_of_week is not None and _text(_session_facts(record.episode).get("day_of_week")) == day_of_week
    )
    calendar_records = _unique_episodes(
        record
        for record in phase_records
        if calendar_class is not None
        and _text(_session_facts(record.episode).get("calendar_class")) == calendar_class
    )

    phase_distribution = _outcome_distribution(phase_records)
    day_distribution = _outcome_distribution(day_records)
    calendar_distribution = _outcome_distribution(calendar_records)
    phase_count = len(phase_records)
    minimum_pass = phase_count >= minimum_sample_size
    reasons: list[str] = []
    warnings: list[str] = []

    if not phase_records:
        availability = "UNAVAILABLE"
        confidence = "INSUFFICIENT_EVIDENCE"
        reasons.append("NO_PIT_VALID_SESSION_HISTORY")
    elif not minimum_pass:
        availability = "DEGRADED"
        confidence = "INSUFFICIENT_EVIDENCE"
        reasons.append("LOW_INDEPENDENT_SESSION_SAMPLE")
    else:
        availability = "AVAILABLE"
        confidence = "MEDIUM"
    if day_of_week is None:
        reasons.append("DAY_OF_WEEK_NOT_PRESENT_IN_CANONICAL_SESSION_FACTS")
    elif not day_records:
        reasons.append("NO_MATCHING_DAY_OF_WEEK_HISTORY")
    if calendar_class is None:
        reasons.append("CALENDAR_CLASS_NOT_PRESENT_IN_CANONICAL_SESSION_FACTS")
    elif not calendar_records:
        reasons.append("NO_MATCHING_CALENDAR_CLASS_HISTORY")
    warnings.append("Historical session distributions are descriptive evidence and cannot choose a trade window autonomously.")

    source_hashes = tuple(record.episode.episode_hash for record in phase_records)
    seed = {
        "calculation_version": CANONICAL_SESSION_MEMORY_VERSION,
        "d2_snapshot_hash": query_episode.d2_snapshot_hash,
        "decision_time_ns": query_episode.decision_time_ns,
        "corpus_hash": corpus.corpus_hash,
        "current_session_phase": query_episode.session_phase,
        "day_of_week": day_of_week,
        "calendar_class": calendar_class,
        "source_episode_hashes": source_hashes,
        "phase_distribution": phase_distribution,
        "day_distribution": day_distribution,
        "calendar_distribution": calendar_distribution,
        "minimum_sample_size": minimum_sample_size,
        "availability": availability,
        "confidence": confidence,
        "reason_codes": sorted(set(reasons)),
    }
    output_hash = _stable_hash(seed)
    result = CanonicalSessionMemory(
        calculation_version=CANONICAL_SESSION_MEMORY_VERSION,
        d2_snapshot_hash=query_episode.d2_snapshot_hash,
        decision_time_ns=query_episode.decision_time_ns,
        corpus_hash=corpus.corpus_hash,
        current_session_id=query_episode.session_id,
        current_session_phase=query_episode.session_phase,
        day_of_week=day_of_week,
        calendar_class=calendar_class,
        independent_phase_episode_count=phase_count,
        independent_day_episode_count=len(day_records),
        independent_calendar_episode_count=len(calendar_records),
        phase_outcome_distribution=phase_distribution,
        day_outcome_distribution=day_distribution,
        calendar_outcome_distribution=calendar_distribution,
        minimum_sample_size=minimum_sample_size,
        minimum_sample_pass=minimum_pass,
        availability=availability,
        confidence=confidence,
        reason_codes=tuple(sorted(set(reasons))),
        warnings=tuple(sorted(set(warnings))),
        source_episode_hashes=source_hashes,
        output_hash=output_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_RECEIPT_BYTES:
        raise CanonicalSessionMemoryError("BOUNDED_SESSION_MEMORY_RECEIPT_EXCEEDED")
    return result


def _session_facts(episode: CanonicalMemoryEpisode) -> Mapping[str, Any]:
    payload = episode.fact_families.get("session")
    return payload if isinstance(payload, Mapping) else {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _unique_episodes(records) -> tuple[MemoryRecord, ...]:
    by_hash: dict[str, MemoryRecord] = {}
    for record in records:
        by_hash[record.episode.episode_hash] = record
    return tuple(sorted(by_hash.values(), key=lambda item: (item.episode.decision_time_ns, item.episode.episode_hash)))


def _outcome_distribution(records: tuple[MemoryRecord, ...]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for record in records:
        if record.label is None:
            continue
        outcome = record.label.outcome_class
        counts[outcome] = counts.get(outcome, 0) + 1
    total = sum(counts.values())
    if not total:
        return {}
    return {key: round(value / total, 12) for key, value in sorted(counts.items())}


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
