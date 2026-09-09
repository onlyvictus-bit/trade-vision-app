from __future__ import annotations

"""Versioned, deterministic and audit-preserving M3.3 retention policy.

Retention produces a view over a canonical corpus.  It never silently deletes
historical evidence: retired episodes keep deterministic tombstones, reason
codes and source hashes so replay/audit can prove what was excluded and why.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .memory_corpus import MemoryCorpus, MemoryRecord


MEMORY_RETENTION_VERSION = "canonical-memory-retention.v1"
MAX_RETENTION_TOMBSTONES = 10_000


class MemoryRetentionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    policy_id: str
    policy_version: str
    maximum_age_ns: int | None = None
    maximum_corpus_size: int | None = None
    minimum_independent_episodes: int = 0
    retain_quarantined: bool = True
    retain_unlabelled: bool = True


@dataclass(frozen=True, slots=True)
class RetentionTombstone:
    episode_hash: str
    retired_at_ns: int
    reason: str
    source_snapshot_hashes: tuple[str, ...]
    source_output_hashes: tuple[str, ...]
    tombstone_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_hash": self.episode_hash,
            "retired_at_ns": self.retired_at_ns,
            "reason": self.reason,
            "source_snapshot_hashes": list(self.source_snapshot_hashes),
            "source_output_hashes": list(self.source_output_hashes),
            "tombstone_hash": self.tombstone_hash,
        }


@dataclass(frozen=True, slots=True)
class RetentionView:
    calculation_version: str
    policy_id: str
    policy_version: str
    corpus_hash: str
    evaluated_at_ns: int
    original_episode_count: int
    retained_episode_count: int
    retired_episode_count: int
    retained_independent_episode_count: int
    retained_episode_hashes: tuple[str, ...]
    retired_episode_hashes: tuple[str, ...]
    tombstones: tuple[RetentionTombstone, ...]
    reason_codes: tuple[str, ...]
    output_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "calculation_version": self.calculation_version,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "corpus_hash": self.corpus_hash,
            "evaluated_at_ns": self.evaluated_at_ns,
            "original_episode_count": self.original_episode_count,
            "retained_episode_count": self.retained_episode_count,
            "retired_episode_count": self.retired_episode_count,
            "retained_independent_episode_count": self.retained_independent_episode_count,
            "retained_episode_hashes": list(self.retained_episode_hashes),
            "retired_episode_hashes": list(self.retired_episode_hashes),
            "tombstones": [item.as_dict() for item in self.tombstones],
            "reason_codes": list(self.reason_codes),
            "output_hash": self.output_hash,
        }


def apply_retention_policy(
    *,
    corpus: MemoryCorpus,
    policy: RetentionPolicy,
    evaluated_at_ns: int,
) -> RetentionView:
    if evaluated_at_ns <= 0 or evaluated_at_ns > corpus.corpus_cutoff_time_ns:
        raise MemoryRetentionError("INVALID_RETENTION_EVALUATION_TIME")
    _validate_policy(policy)

    records = tuple(sorted(corpus.records, key=lambda item: (item.episode.decision_time_ns, item.episode.episode_hash)))
    retained: dict[str, MemoryRecord] = {record.episode.episode_hash: record for record in records}
    retired_reason: dict[str, str] = {}

    def can_retire(record: MemoryRecord) -> bool:
        if record.quarantined and policy.retain_quarantined:
            return False
        if record.label is None and policy.retain_unlabelled:
            return False
        if record.quarantined:
            return True
        remaining_independent = sum(
            1
            for other in retained.values()
            if not other.quarantined and other.episode.episode_hash != record.episode.episode_hash
        )
        return remaining_independent >= policy.minimum_independent_episodes

    if policy.maximum_age_ns is not None:
        age_cutoff = evaluated_at_ns - policy.maximum_age_ns
        for record in records:
            episode_hash = record.episode.episode_hash
            if episode_hash not in retained:
                continue
            if record.episode.decision_time_ns < age_cutoff and can_retire(record):
                retained.pop(episode_hash)
                retired_reason[episode_hash] = "MAXIMUM_AGE"

    if policy.maximum_corpus_size is not None and len(retained) > policy.maximum_corpus_size:
        candidates = sorted(
            retained.values(),
            key=lambda item: (item.episode.decision_time_ns, item.episode.episode_hash),
        )
        for record in candidates:
            if len(retained) <= policy.maximum_corpus_size:
                break
            episode_hash = record.episode.episode_hash
            if episode_hash not in retained or not can_retire(record):
                continue
            retained.pop(episode_hash)
            retired_reason[episode_hash] = "MAXIMUM_CORPUS_SIZE"

    tombstones = []
    by_hash = {record.episode.episode_hash: record for record in records}
    for episode_hash in sorted(retired_reason):
        record = by_hash[episode_hash]
        seed = {
            "calculation_version": MEMORY_RETENTION_VERSION,
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
            "corpus_hash": corpus.corpus_hash,
            "episode_hash": episode_hash,
            "retired_at_ns": evaluated_at_ns,
            "reason": retired_reason[episode_hash],
            "source_snapshot_hashes": list(record.episode.source_snapshot_hashes),
            "source_output_hashes": list(record.episode.source_output_hashes),
        }
        tombstones.append(
            RetentionTombstone(
                episode_hash=episode_hash,
                retired_at_ns=evaluated_at_ns,
                reason=retired_reason[episode_hash],
                source_snapshot_hashes=record.episode.source_snapshot_hashes,
                source_output_hashes=record.episode.source_output_hashes,
                tombstone_hash=_stable_hash(seed),
            )
        )
    if len(tombstones) > MAX_RETENTION_TOMBSTONES:
        raise MemoryRetentionError("RETENTION_TOMBSTONE_LIMIT_EXCEEDED")

    retained_hashes = tuple(sorted(retained))
    retired_hashes = tuple(item.episode_hash for item in tombstones)
    retained_independent = sum(1 for record in retained.values() if not record.quarantined)
    reason_codes = []
    if retired_hashes:
        reason_codes.append("RETENTION_APPLIED")
    if policy.maximum_corpus_size is not None and len(retained) > policy.maximum_corpus_size:
        reason_codes.append("SIZE_LIMIT_BLOCKED_BY_RETENTION_FLOORS")
    if retained_independent < policy.minimum_independent_episodes:
        raise MemoryRetentionError("RETENTION_VIOLATED_MINIMUM_INDEPENDENT_EPISODES")

    seed = {
        "calculation_version": MEMORY_RETENTION_VERSION,
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "corpus_hash": corpus.corpus_hash,
        "evaluated_at_ns": evaluated_at_ns,
        "retained_episode_hashes": list(retained_hashes),
        "tombstone_hashes": [item.tombstone_hash for item in tombstones],
        "reason_codes": sorted(reason_codes),
    }
    return RetentionView(
        calculation_version=MEMORY_RETENTION_VERSION,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        corpus_hash=corpus.corpus_hash,
        evaluated_at_ns=evaluated_at_ns,
        original_episode_count=len(records),
        retained_episode_count=len(retained_hashes),
        retired_episode_count=len(retired_hashes),
        retained_independent_episode_count=retained_independent,
        retained_episode_hashes=retained_hashes,
        retired_episode_hashes=retired_hashes,
        tombstones=tuple(tombstones),
        reason_codes=tuple(sorted(reason_codes)),
        output_hash=_stable_hash(seed),
    )


def _validate_policy(policy: RetentionPolicy) -> None:
    if not isinstance(policy, RetentionPolicy):
        raise MemoryRetentionError("INVALID_RETENTION_POLICY")
    if not policy.policy_id.strip() or not policy.policy_version.strip():
        raise MemoryRetentionError("INVALID_RETENTION_POLICY_IDENTITY")
    if policy.maximum_age_ns is not None and policy.maximum_age_ns <= 0:
        raise MemoryRetentionError("INVALID_MAXIMUM_AGE")
    if policy.maximum_corpus_size is not None and policy.maximum_corpus_size <= 0:
        raise MemoryRetentionError("INVALID_MAXIMUM_CORPUS_SIZE")
    if policy.minimum_independent_episodes < 0:
        raise MemoryRetentionError("INVALID_MINIMUM_INDEPENDENT_EPISODES")
    if (
        policy.maximum_corpus_size is not None
        and policy.maximum_corpus_size < policy.minimum_independent_episodes
    ):
        raise MemoryRetentionError("SIZE_LIMIT_BELOW_MINIMUM_INDEPENDENT_EPISODES")


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
