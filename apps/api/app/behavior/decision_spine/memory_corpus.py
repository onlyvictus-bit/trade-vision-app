from __future__ import annotations

"""M3.3 delayed labels, corpus identity, PIT retrieval, and quarantine.

The corpus is intentionally immutable-at-build-time and deterministic. Labels
become usable only at their causal availability timestamp; episode creation time
alone is never sufficient. Suspicious records are retained as quarantined
provenance rather than silently deleted. Quarantine state itself is also PIT:
a quarantine event may not leak backward into a corpus reconstructed before the
quarantine timestamp.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal, Sequence

from .canonical_memory_intelligence import CanonicalMemoryEpisode


MEMORY_LABEL_VERSION = "canonical-memory-label.v1"
MEMORY_CORPUS_VERSION = "canonical-memory-corpus.v1"
MAX_CORPUS_EPISODES = 10_000
MAX_CORPUS_RECEIPT_BYTES = 256_000
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")

OutcomeClass = Literal[
    "CONTINUATION",
    "BREAKOUT_FAILURE",
    "TRAP",
    "REVERSAL",
    "NO_EDGE",
    "EXHAUSTION",
]
_ALLOWED_OUTCOMES = {
    "CONTINUATION",
    "BREAKOUT_FAILURE",
    "TRAP",
    "REVERSAL",
    "NO_EDGE",
    "EXHAUSTION",
}


class MemoryCorpusError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DelayedOutcomeLabel:
    label_policy_id: str
    label_policy_version: str
    episode_hash: str
    decision_time_ns: int
    label_available_after_ns: int
    label_observed_at_ns: int
    outcome_horizon_ns: int
    future_price_source_hash: str
    future_snapshot_hash: str
    return_after_horizon: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    outcome_class: OutcomeClass
    future_candle_finished: bool = True
    source_identity_match: bool = True
    episode_identity_match: bool = True
    synthetic: bool = False
    label_version: str = MEMORY_LABEL_VERSION
    label_hash: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    episode: CanonicalMemoryEpisode
    label: DelayedOutcomeLabel | None = None
    memory_available_at_ns: int | None = None
    quarantined: bool = False
    quarantine_reason: str | None = None
    quarantine_version: str | None = None
    quarantined_at_ns: int | None = None

    def available_at(self) -> int:
        base = self.episode.decision_time_ns
        if self.label is not None:
            base = max(base, self.label.label_observed_at_ns)
        if self.memory_available_at_ns is not None:
            base = max(base, self.memory_available_at_ns)
        return base


@dataclass(frozen=True, slots=True)
class MemoryCorpus:
    corpus_version: str
    schema_version: str
    feature_version: str
    label_version: str
    corpus_cutoff_time_ns: int
    episode_count: int
    raw_record_count: int
    independent_episode_count: int
    independent_session_count: int
    independent_symbol_count: int
    labelled_count: int
    unlabelled_count: int
    quarantined_count: int
    episode_hashes: tuple[str, ...]
    labelled_episode_hashes: tuple[str, ...]
    quarantined_episode_hashes: tuple[str, ...]
    corpus_hash: str
    records: tuple[MemoryRecord, ...]

    def as_dict(self, *, include_records: bool = False) -> dict[str, Any]:
        payload = {
            "corpus_version": self.corpus_version,
            "schema_version": self.schema_version,
            "feature_version": self.feature_version,
            "label_version": self.label_version,
            "corpus_cutoff_time_ns": self.corpus_cutoff_time_ns,
            "episode_count": self.episode_count,
            "raw_record_count": self.raw_record_count,
            "independent_episode_count": self.independent_episode_count,
            "independent_session_count": self.independent_session_count,
            "independent_symbol_count": self.independent_symbol_count,
            "labelled_count": self.labelled_count,
            "unlabelled_count": self.unlabelled_count,
            "quarantined_count": self.quarantined_count,
            "episode_hashes": list(self.episode_hashes),
            "labelled_episode_hashes": list(self.labelled_episode_hashes),
            "quarantined_episode_hashes": list(self.quarantined_episode_hashes),
            "corpus_hash": self.corpus_hash,
        }
        if include_records:
            payload["records"] = [
                {
                    "episode_hash": record.episode.episode_hash,
                    "available_at_ns": record.available_at(),
                    "label_hash": record.label.label_hash if record.label else None,
                    "quarantined": record.quarantined,
                    "quarantine_reason": record.quarantine_reason,
                }
                for record in self.records
            ]
        return payload


def build_delayed_label(
    *,
    episode: CanonicalMemoryEpisode,
    label_policy_id: str,
    label_policy_version: str,
    label_available_after_ns: int,
    label_observed_at_ns: int,
    outcome_horizon_ns: int,
    future_price_source_hash: str,
    future_snapshot_hash: str,
    return_after_horizon: float,
    max_favorable_excursion: float,
    max_adverse_excursion: float,
    outcome_class: OutcomeClass,
    future_candle_finished: bool = True,
    source_identity_match: bool = True,
    episode_identity_match: bool = True,
    synthetic: bool = False,
) -> DelayedOutcomeLabel:
    if not isinstance(episode, CanonicalMemoryEpisode):
        raise MemoryCorpusError("INVALID_EPISODE")
    if not label_policy_id.strip() or not label_policy_version.strip():
        raise MemoryCorpusError("INVALID_LABEL_POLICY")
    if outcome_class not in _ALLOWED_OUTCOMES:
        raise MemoryCorpusError("INVALID_OUTCOME_CLASS")
    if outcome_horizon_ns <= 0:
        raise MemoryCorpusError("INVALID_OUTCOME_HORIZON")
    if label_available_after_ns < episode.decision_time_ns + outcome_horizon_ns:
        raise MemoryCorpusError("LABEL_AVAILABLE_BEFORE_HORIZON")
    if label_observed_at_ns < label_available_after_ns:
        raise MemoryCorpusError("LABEL_OBSERVED_BEFORE_AVAILABLE")
    if not future_candle_finished:
        raise MemoryCorpusError("FUTURE_CANDLE_UNFINISHED")
    if not source_identity_match:
        raise MemoryCorpusError("FUTURE_SOURCE_IDENTITY_MISMATCH")
    if not episode_identity_match:
        raise MemoryCorpusError("EPISODE_IDENTITY_MISMATCH")
    if synthetic:
        raise MemoryCorpusError("SYNTHETIC_LABEL_NOT_CANONICAL")
    future_price_source_hash = _require_hash(future_price_source_hash, "future_price_source_hash")
    future_snapshot_hash = _require_hash(future_snapshot_hash, "future_snapshot_hash")
    for name, value in (
        ("return_after_horizon", return_after_horizon),
        ("max_favorable_excursion", max_favorable_excursion),
        ("max_adverse_excursion", max_adverse_excursion),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not _finite(float(value)):
            raise MemoryCorpusError(f"INVALID_LABEL_NUMBER:{name}")

    seed = {
        "label_version": MEMORY_LABEL_VERSION,
        "label_policy_id": label_policy_id,
        "label_policy_version": label_policy_version,
        "episode_hash": episode.episode_hash,
        "decision_time_ns": episode.decision_time_ns,
        "label_available_after_ns": label_available_after_ns,
        "label_observed_at_ns": label_observed_at_ns,
        "outcome_horizon_ns": outcome_horizon_ns,
        "future_price_source_hash": future_price_source_hash,
        "future_snapshot_hash": future_snapshot_hash,
        "return_after_horizon": float(return_after_horizon),
        "max_favorable_excursion": float(max_favorable_excursion),
        "max_adverse_excursion": float(max_adverse_excursion),
        "outcome_class": outcome_class,
    }
    label_hash = _stable_hash(seed)
    return DelayedOutcomeLabel(
        label_policy_id=label_policy_id,
        label_policy_version=label_policy_version,
        episode_hash=episode.episode_hash,
        decision_time_ns=episode.decision_time_ns,
        label_available_after_ns=label_available_after_ns,
        label_observed_at_ns=label_observed_at_ns,
        outcome_horizon_ns=outcome_horizon_ns,
        future_price_source_hash=future_price_source_hash,
        future_snapshot_hash=future_snapshot_hash,
        return_after_horizon=float(return_after_horizon),
        max_favorable_excursion=float(max_favorable_excursion),
        max_adverse_excursion=float(max_adverse_excursion),
        outcome_class=outcome_class,
        label_hash=label_hash,
    )


def build_memory_corpus(*, records: Sequence[MemoryRecord], cutoff_time_ns: int) -> MemoryCorpus:
    if not isinstance(cutoff_time_ns, int) or isinstance(cutoff_time_ns, bool) or cutoff_time_ns <= 0:
        raise MemoryCorpusError("INVALID_CORPUS_CUTOFF")
    if isinstance(records, (str, bytes)):
        raise MemoryCorpusError("INVALID_RECORD_COLLECTION")
    if len(records) > MAX_CORPUS_EPISODES:
        raise MemoryCorpusError("CORPUS_TOO_LARGE")

    eligible: list[MemoryRecord] = []
    for record in records:
        if not isinstance(record, MemoryRecord):
            raise MemoryCorpusError("INVALID_MEMORY_RECORD")
        _validate_record(record)
        if record.available_at() > cutoff_time_ns:
            continue
        eligible.append(_project_record_at_cutoff(record, cutoff_time_ns=cutoff_time_ns))

    by_hash: dict[str, MemoryRecord] = {}
    for record in eligible:
        existing = by_hash.get(record.episode.episode_hash)
        if existing is None:
            by_hash[record.episode.episode_hash] = record
            continue
        if existing.label and record.label and existing.label.label_hash != record.label.label_hash:
            raise MemoryCorpusError("CONFLICTING_LABELS_FOR_EPISODE")
        if existing.label is None and record.label is not None:
            by_hash[record.episode.episode_hash] = record
        elif record.quarantined and not existing.quarantined:
            by_hash[record.episode.episode_hash] = record

    normalized = tuple(sorted(by_hash.values(), key=lambda item: item.episode.episode_hash))
    episode_hashes = tuple(record.episode.episode_hash for record in normalized)
    labelled_hashes = tuple(record.episode.episode_hash for record in normalized if record.label is not None)
    quarantined_hashes = tuple(record.episode.episode_hash for record in normalized if record.quarantined)
    session_ids = {record.episode.session_id for record in normalized if not record.quarantined}
    symbols = {record.episode.symbol for record in normalized if not record.quarantined}
    independent_hashes = {record.episode.episode_hash for record in normalized if not record.quarantined}
    raw_record_count = sum(record.episode.raw_record_count for record in normalized)

    schema_versions = {record.episode.schema_version for record in normalized}
    feature_versions = {record.episode.feature_version for record in normalized}
    if len(schema_versions) > 1:
        raise MemoryCorpusError("MIXED_SCHEMA_VERSIONS")
    if len(feature_versions) > 1:
        raise MemoryCorpusError("MIXED_FEATURE_VERSIONS")
    label_versions = {record.label.label_version for record in normalized if record.label is not None}
    if len(label_versions) > 1:
        raise MemoryCorpusError("MIXED_LABEL_VERSIONS")

    schema_version = next(iter(schema_versions), "none")
    feature_version = next(iter(feature_versions), "none")
    label_version = next(iter(label_versions), MEMORY_LABEL_VERSION)
    seed = {
        "corpus_version": MEMORY_CORPUS_VERSION,
        "schema_version": schema_version,
        "feature_version": feature_version,
        "label_version": label_version,
        "corpus_cutoff_time_ns": cutoff_time_ns,
        "records": [
            {
                "episode_hash": record.episode.episode_hash,
                "memory_available_at_ns": record.available_at(),
                "label_hash": record.label.label_hash if record.label else None,
                "quarantined": record.quarantined,
                "quarantine_reason": record.quarantine_reason,
                "quarantine_version": record.quarantine_version,
            }
            for record in normalized
        ],
    }
    corpus_hash = _stable_hash(seed)
    corpus = MemoryCorpus(
        corpus_version=MEMORY_CORPUS_VERSION,
        schema_version=schema_version,
        feature_version=feature_version,
        label_version=label_version,
        corpus_cutoff_time_ns=cutoff_time_ns,
        episode_count=len(normalized),
        raw_record_count=raw_record_count,
        independent_episode_count=len(independent_hashes),
        independent_session_count=len(session_ids),
        independent_symbol_count=len(symbols),
        labelled_count=len(labelled_hashes),
        unlabelled_count=len(normalized) - len(labelled_hashes),
        quarantined_count=len(quarantined_hashes),
        episode_hashes=episode_hashes,
        labelled_episode_hashes=labelled_hashes,
        quarantined_episode_hashes=quarantined_hashes,
        corpus_hash=corpus_hash,
        records=normalized,
    )
    encoded = json.dumps(corpus.as_dict(include_records=True), sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_CORPUS_RECEIPT_BYTES:
        raise MemoryCorpusError("BOUNDED_CORPUS_RECEIPT_EXCEEDED")
    return corpus


def retrieve_pit_records(
    corpus: MemoryCorpus,
    *,
    decision_time_ns: int,
    labelled_only: bool = False,
    include_quarantined: bool = False,
) -> tuple[MemoryRecord, ...]:
    if decision_time_ns > corpus.corpus_cutoff_time_ns:
        raise MemoryCorpusError("QUERY_AFTER_CORPUS_CUTOFF")
    result = []
    for record in corpus.records:
        if record.available_at() > decision_time_ns:
            continue
        if labelled_only and record.label is None:
            continue
        if record.quarantined and not include_quarantined:
            continue
        result.append(record)
    return tuple(result)


def quarantine_record(
    record: MemoryRecord,
    *,
    reason: str,
    quarantine_version: str,
    quarantined_at_ns: int,
) -> MemoryRecord:
    if not reason.strip() or not quarantine_version.strip():
        raise MemoryCorpusError("INVALID_QUARANTINE_METADATA")
    if quarantined_at_ns <= 0:
        raise MemoryCorpusError("INVALID_QUARANTINE_TIME")
    return MemoryRecord(
        episode=record.episode,
        label=record.label,
        memory_available_at_ns=record.memory_available_at_ns,
        quarantined=True,
        quarantine_reason=reason.strip(),
        quarantine_version=quarantine_version.strip(),
        quarantined_at_ns=quarantined_at_ns,
    )


def _project_record_at_cutoff(record: MemoryRecord, *, cutoff_time_ns: int) -> MemoryRecord:
    """Return the record state that was knowable at the requested corpus cutoff."""
    if not record.quarantined:
        return record
    assert record.quarantined_at_ns is not None
    if record.quarantined_at_ns <= cutoff_time_ns:
        return record
    return MemoryRecord(
        episode=record.episode,
        label=record.label,
        memory_available_at_ns=record.memory_available_at_ns,
        quarantined=False,
        quarantine_reason=None,
        quarantine_version=None,
        quarantined_at_ns=None,
    )


def _validate_record(record: MemoryRecord) -> None:
    if record.label is not None:
        if record.label.episode_hash != record.episode.episode_hash:
            raise MemoryCorpusError("LABEL_EPISODE_HASH_MISMATCH")
        if record.label.decision_time_ns != record.episode.decision_time_ns:
            raise MemoryCorpusError("LABEL_DECISION_TIME_MISMATCH")
        if not _HASH_RE.fullmatch(record.label.label_hash):
            raise MemoryCorpusError("INVALID_LABEL_HASH")
    if record.quarantined:
        if not record.quarantine_reason or not record.quarantine_version or not record.quarantined_at_ns:
            raise MemoryCorpusError("INCOMPLETE_QUARANTINE_METADATA")
        if record.quarantined_at_ns < record.available_at():
            raise MemoryCorpusError("QUARANTINE_BEFORE_MEMORY_AVAILABLE")


def _require_hash(value: str, field: str) -> str:
    if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
        raise MemoryCorpusError(f"INVALID_HASH:{field}")
    return value.lower()


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
