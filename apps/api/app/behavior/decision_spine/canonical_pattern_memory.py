from __future__ import annotations

"""Canonical M3.3 day-shape v2 and pattern-memory retrieval.

The feature builder uses candle *close* time and explicit wall-clock windows.
Unknown previous close remains missing; it is never converted into a flat gap.
Historical vectors must carry the exact schema/scaling version and an explicit
missing mask. Large corpora require a verified external shortlist rather than a
surprise full-history scan on the decision path.
"""

import hashlib
import json
import math
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Mapping, Sequence

from .canonical_memory_intelligence import CanonicalMemoryEpisode
from .memory_corpus import MemoryCorpus, MemoryRecord, retrieve_pit_records


DAY_SHAPE_VERSION = "canonical-day-shape.v2"
PATTERN_MEMORY_VERSION = "canonical-pattern-memory.v1"
SCALING_VERSION = "canonical-day-shape-scales.v1"
MAX_PATTERN_CANDIDATES = 512
MAX_PATTERN_MATCHES = 32
MAX_RECEIPT_BYTES = 64_000

FEATURE_NAMES = (
    "gap_pct",
    "first15_return_pct",
    "first15_range_pct",
    "first15_close_location",
    "first30_return_pct",
    "first30_range_pct",
    "first30_close_location",
    "session_return_pct",
    "session_range_pct",
    "realized_step_volatility",
    "trend_efficiency",
    "volume_impulse_ratio",
)
FEATURE_SCALES = (2.0, 1.5, 2.0, 1.0, 2.5, 3.0, 1.0, 4.0, 5.0, 1.0, 1.0, 2.0)


class CanonicalPatternMemoryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalDayShape:
    shape_version: str
    scaling_version: str
    symbol: str
    timeframe: str
    decision_time_ns: int
    session_open_ns: int
    source_snapshot_hash: str
    feature_names: tuple[str, ...]
    vector: tuple[float | None, ...]
    missing_mask: tuple[bool, ...]
    closed_bar_count: int
    first15_bar_count: int
    first30_bar_count: int
    vector_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "shape_version": self.shape_version,
            "scaling_version": self.scaling_version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "decision_time_ns": self.decision_time_ns,
            "session_open_ns": self.session_open_ns,
            "source_snapshot_hash": self.source_snapshot_hash,
            "feature_names": list(self.feature_names),
            "vector": list(self.vector),
            "missing_mask": list(self.missing_mask),
            "closed_bar_count": self.closed_bar_count,
            "first15_bar_count": self.first15_bar_count,
            "first30_bar_count": self.first30_bar_count,
            "vector_hash": self.vector_hash,
        }

    def as_fact(self) -> dict[str, Any]:
        return {"day_shape_v2": self.as_dict()}


@dataclass(frozen=True, slots=True)
class PatternMatch:
    episode_hash: str
    session_id: str
    distance: float
    outcome_class: str
    matched_features: tuple[str, ...]
    mismatched_features: tuple[str, ...]
    unavailable_features: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_hash": self.episode_hash,
            "session_id": self.session_id,
            "distance": self.distance,
            "outcome_class": self.outcome_class,
            "matched_features": list(self.matched_features),
            "mismatched_features": list(self.mismatched_features),
            "unavailable_features": list(self.unavailable_features),
        }


@dataclass(frozen=True, slots=True)
class CanonicalPatternMemory:
    calculation_version: str
    d2_snapshot_hash: str
    decision_time_ns: int
    corpus_hash: str
    current_vector_hash: str
    candidate_count: int
    independent_match_count: int
    index_shortlist_used: bool
    index_manifest_hash: str | None
    ood: bool
    ood_reasons: tuple[str, ...]
    matches: tuple[PatternMatch, ...]
    availability: str
    confidence: str
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
            "current_vector_hash": self.current_vector_hash,
            "candidate_count": self.candidate_count,
            "independent_match_count": self.independent_match_count,
            "index_shortlist_used": self.index_shortlist_used,
            "index_manifest_hash": self.index_manifest_hash,
            "ood": self.ood,
            "ood_reasons": list(self.ood_reasons),
            "matches": [match.as_dict() for match in self.matches],
            "availability": self.availability,
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


def build_day_shape_v2(
    *,
    symbol: str,
    timeframe: str,
    decision_time_ns: int,
    session_open_ns: int,
    timeframe_duration_ns: int,
    source_snapshot_hash: str,
    bars: Sequence[Mapping[str, Any]],
    previous_close: float | None,
) -> CanonicalDayShape:
    if decision_time_ns <= 0 or session_open_ns <= 0 or timeframe_duration_ns <= 0:
        raise CanonicalPatternMemoryError("INVALID_TIME_IDENTITY")
    if session_open_ns >= decision_time_ns:
        raise CanonicalPatternMemoryError("SESSION_OPEN_NOT_BEFORE_DECISION")
    if len(source_snapshot_hash) != 64:
        raise CanonicalPatternMemoryError("INVALID_SOURCE_SNAPSHOT_HASH")

    closed = []
    for raw in bars:
        row = _bar(raw)
        close_ns = row["timestamp_ns"] + timeframe_duration_ns
        if close_ns > decision_time_ns:
            continue
        if row["timestamp_ns"] < session_open_ns:
            continue
        closed.append(row)
    closed.sort(key=lambda row: row["timestamp_ns"])
    first15 = [row for row in closed if row["timestamp_ns"] + timeframe_duration_ns <= session_open_ns + 15 * 60 * 1_000_000_000]
    first30 = [row for row in closed if row["timestamp_ns"] + timeframe_duration_ns <= session_open_ns + 30 * 60 * 1_000_000_000]

    values = (
        _gap_pct(closed, previous_close),
        _return_pct(first15),
        _range_pct(first15),
        _close_location(first15),
        _return_pct(first30),
        _range_pct(first30),
        _close_location(first30),
        _return_pct(closed),
        _range_pct(closed),
        _realized_volatility(closed),
        _trend_efficiency(closed),
        _volume_impulse(closed),
    )
    normalized = tuple(round(float(value), 10) if value is not None else None for value in values)
    missing = tuple(value is None for value in normalized)
    seed = {
        "shape_version": DAY_SHAPE_VERSION,
        "scaling_version": SCALING_VERSION,
        "symbol": str(symbol).strip().upper(),
        "timeframe": str(timeframe).strip(),
        "decision_time_ns": decision_time_ns,
        "session_open_ns": session_open_ns,
        "source_snapshot_hash": source_snapshot_hash.lower(),
        "feature_names": FEATURE_NAMES,
        "vector": normalized,
        "missing_mask": missing,
    }
    vector_hash = _stable_hash(seed)
    return CanonicalDayShape(
        shape_version=DAY_SHAPE_VERSION,
        scaling_version=SCALING_VERSION,
        symbol=str(symbol).strip().upper(),
        timeframe=str(timeframe).strip(),
        decision_time_ns=decision_time_ns,
        session_open_ns=session_open_ns,
        source_snapshot_hash=source_snapshot_hash.lower(),
        feature_names=FEATURE_NAMES,
        vector=normalized,
        missing_mask=missing,
        closed_bar_count=len(closed),
        first15_bar_count=len(first15),
        first30_bar_count=len(first30),
        vector_hash=vector_hash,
    )


def build_canonical_pattern_memory(
    *,
    query_episode: CanonicalMemoryEpisode,
    current_shape: CanonicalDayShape,
    corpus: MemoryCorpus,
    candidate_episode_hashes: Sequence[str] | None = None,
    index_manifest_hash: str | None = None,
    max_matches: int = 20,
    minimum_overlap_features: int = 6,
    ood_distance_threshold: float = 0.75,
) -> CanonicalPatternMemory:
    if current_shape.source_snapshot_hash != query_episode.d2_snapshot_hash:
        raise CanonicalPatternMemoryError("CURRENT_SHAPE_SNAPSHOT_MISMATCH")
    if current_shape.decision_time_ns != query_episode.decision_time_ns:
        raise CanonicalPatternMemoryError("CURRENT_SHAPE_DECISION_TIME_MISMATCH")
    if corpus.corpus_cutoff_time_ns < query_episode.decision_time_ns:
        raise CanonicalPatternMemoryError("CORPUS_CUTOFF_BEFORE_DECISION")
    if not 1 <= max_matches <= MAX_PATTERN_MATCHES:
        raise CanonicalPatternMemoryError("INVALID_MAX_MATCHES")
    if not 1 <= minimum_overlap_features <= len(FEATURE_NAMES):
        raise CanonicalPatternMemoryError("INVALID_MINIMUM_OVERLAP")

    all_candidates = [
        record
        for record in retrieve_pit_records(corpus, decision_time_ns=query_episode.decision_time_ns, labelled_only=True)
        if record.episode.symbol == query_episode.symbol
        and record.episode.timeframe == query_episode.timeframe
        and record.episode.episode_hash != query_episode.episode_hash
        and _shape_from_episode(record.episode) is not None
    ]
    shortlist_used = candidate_episode_hashes is not None
    if candidate_episode_hashes is None:
        if len(all_candidates) > MAX_PATTERN_CANDIDATES:
            raise CanonicalPatternMemoryError("VERIFIED_INDEX_SHORTLIST_REQUIRED")
        candidates = all_candidates
    else:
        if not index_manifest_hash or len(index_manifest_hash) != 64:
            raise CanonicalPatternMemoryError("INVALID_INDEX_MANIFEST_HASH")
        allowed = set(candidate_episode_hashes)
        if len(allowed) > MAX_PATTERN_CANDIDATES:
            raise CanonicalPatternMemoryError("INDEX_SHORTLIST_TOO_LARGE")
        candidates = [record for record in all_candidates if record.episode.episode_hash in allowed]

    scored: list[tuple[float, MemoryRecord, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []
    for record in candidates:
        shape = _shape_from_episode(record.episode)
        assert shape is not None
        distance, matched, mismatched, unavailable = _distance(
            current_shape,
            shape,
            minimum_overlap_features=minimum_overlap_features,
        )
        if distance is None:
            continue
        scored.append((distance, record, matched, mismatched, unavailable))
    scored.sort(key=lambda item: (item[0], item[1].episode.episode_hash))

    selected: list[PatternMatch] = []
    seen_sessions: set[str] = set()
    for distance, record, matched, mismatched, unavailable in scored:
        if record.episode.session_id in seen_sessions:
            continue
        seen_sessions.add(record.episode.session_id)
        assert record.label is not None
        selected.append(
            PatternMatch(
                episode_hash=record.episode.episode_hash,
                session_id=record.episode.session_id,
                distance=round(distance, 12),
                outcome_class=record.label.outcome_class,
                matched_features=matched,
                mismatched_features=mismatched,
                unavailable_features=unavailable,
            )
        )
        if len(selected) >= max_matches:
            break

    nearest = selected[0].distance if selected else None
    ood_reasons: list[str] = []
    if nearest is None:
        ood_reasons.append("NO_COMPARABLE_CANONICAL_DAY_SHAPES")
    elif nearest > ood_distance_threshold:
        ood_reasons.append("NEAREST_DAY_SHAPE_OUTSIDE_SUPPORT")
    ood = bool(ood_reasons)
    if not selected:
        availability = "UNAVAILABLE"
        confidence = "INSUFFICIENT_EVIDENCE"
    elif ood:
        availability = "DEGRADED"
        confidence = "OOD"
    elif len(selected) < 5:
        availability = "DEGRADED"
        confidence = "INSUFFICIENT_EVIDENCE"
    else:
        availability = "AVAILABLE"
        confidence = "MEDIUM"

    seed = {
        "calculation_version": PATTERN_MEMORY_VERSION,
        "d2_snapshot_hash": query_episode.d2_snapshot_hash,
        "decision_time_ns": query_episode.decision_time_ns,
        "corpus_hash": corpus.corpus_hash,
        "current_vector_hash": current_shape.vector_hash,
        "candidate_count": len(candidates),
        "index_shortlist_used": shortlist_used,
        "index_manifest_hash": index_manifest_hash,
        "matches": [match.as_dict() for match in selected],
        "ood_reasons": ood_reasons,
        "availability": availability,
        "confidence": confidence,
    }
    output_hash = _stable_hash(seed)
    result = CanonicalPatternMemory(
        calculation_version=PATTERN_MEMORY_VERSION,
        d2_snapshot_hash=query_episode.d2_snapshot_hash,
        decision_time_ns=query_episode.decision_time_ns,
        corpus_hash=corpus.corpus_hash,
        current_vector_hash=current_shape.vector_hash,
        candidate_count=len(candidates),
        independent_match_count=len(selected),
        index_shortlist_used=shortlist_used,
        index_manifest_hash=index_manifest_hash.lower() if index_manifest_hash else None,
        ood=ood,
        ood_reasons=tuple(sorted(set(ood_reasons))),
        matches=tuple(selected),
        availability=availability,
        confidence=confidence,
        output_hash=output_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_RECEIPT_BYTES:
        raise CanonicalPatternMemoryError("BOUNDED_PATTERN_MEMORY_RECEIPT_EXCEEDED")
    return result


def _bar(raw: Mapping[str, Any]) -> dict[str, float | int | None]:
    try:
        timestamp_ns = int(raw["timestamp_ns"])
        open_price = float(raw["open"])
        high = float(raw["high"])
        low = float(raw["low"])
        close = float(raw["close"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CanonicalPatternMemoryError("INVALID_BAR") from exc
    if timestamp_ns < 0 or not all(math.isfinite(value) for value in (open_price, high, low, close)):
        raise CanonicalPatternMemoryError("INVALID_BAR")
    if low > min(open_price, close) or high < max(open_price, close) or high < low:
        raise CanonicalPatternMemoryError("INVALID_OHLC")
    volume = raw.get("volume")
    if volume is not None:
        try:
            volume = float(volume)
        except (TypeError, ValueError):
            volume = None
        if volume is not None and (not math.isfinite(volume) or volume < 0):
            volume = None
    return {"timestamp_ns": timestamp_ns, "open": open_price, "high": high, "low": low, "close": close, "volume": volume}


def _gap_pct(rows, previous_close):
    if not rows or previous_close is None:
        return None
    previous_close = float(previous_close)
    if not math.isfinite(previous_close) or previous_close <= 0:
        return None
    return (float(rows[0]["open"]) - previous_close) / previous_close * 100.0


def _return_pct(rows):
    if not rows:
        return None
    first = float(rows[0]["open"])
    return (float(rows[-1]["close"]) - first) / max(abs(first), 1e-12) * 100.0


def _range_pct(rows):
    if not rows:
        return None
    base = float(rows[0]["open"])
    return (max(float(row["high"]) for row in rows) - min(float(row["low"]) for row in rows)) / max(abs(base), 1e-12) * 100.0


def _close_location(rows):
    if not rows:
        return None
    high = max(float(row["high"]) for row in rows)
    low = min(float(row["low"]) for row in rows)
    if high <= low:
        return 0.5
    return (float(rows[-1]["close"]) - low) / (high - low)


def _realized_volatility(rows):
    if len(rows) < 3:
        return None
    closes = [float(row["close"]) for row in rows]
    returns = [(closes[i] - closes[i - 1]) / max(abs(closes[i - 1]), 1e-12) * 100.0 for i in range(1, len(closes))]
    return pstdev(returns) if len(returns) >= 2 else None


def _trend_efficiency(rows):
    if len(rows) < 2:
        return None
    closes = [float(row["close"]) for row in rows]
    net = abs(closes[-1] - closes[0])
    path = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
    return net / path if path > 1e-12 else 0.0


def _volume_impulse(rows):
    volumes = [float(row["volume"]) for row in rows if row.get("volume") is not None and float(row["volume"]) > 0]
    if len(volumes) < 4:
        return None
    baseline = mean(volumes[:-1])
    return volumes[-1] / baseline if baseline > 0 else None


def _shape_from_episode(episode: CanonicalMemoryEpisode) -> CanonicalDayShape | None:
    family = episode.fact_families.get("pattern")
    if not isinstance(family, Mapping):
        return None
    payload = family.get("day_shape_v2")
    if not isinstance(payload, Mapping):
        return None
    if payload.get("shape_version") != DAY_SHAPE_VERSION or payload.get("scaling_version") != SCALING_VERSION:
        return None
    try:
        names = tuple(str(item) for item in payload["feature_names"])
        vector = tuple(float(item) if item is not None else None for item in payload["vector"])
        missing = tuple(bool(item) for item in payload["missing_mask"])
        if names != FEATURE_NAMES or len(vector) != len(FEATURE_NAMES) or len(missing) != len(FEATURE_NAMES):
            return None
        if any((value is not None and not math.isfinite(value)) for value in vector):
            return None
        return CanonicalDayShape(
            shape_version=DAY_SHAPE_VERSION,
            scaling_version=SCALING_VERSION,
            symbol=str(payload.get("symbol", episode.symbol)),
            timeframe=str(payload.get("timeframe", episode.timeframe)),
            decision_time_ns=int(payload.get("decision_time_ns", episode.decision_time_ns)),
            session_open_ns=int(payload["session_open_ns"]),
            source_snapshot_hash=str(payload.get("source_snapshot_hash", episode.d2_snapshot_hash)).lower(),
            feature_names=names,
            vector=vector,
            missing_mask=missing,
            closed_bar_count=int(payload.get("closed_bar_count", 0)),
            first15_bar_count=int(payload.get("first15_bar_count", 0)),
            first30_bar_count=int(payload.get("first30_bar_count", 0)),
            vector_hash=str(payload["vector_hash"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _distance(current: CanonicalDayShape, historical: CanonicalDayShape, *, minimum_overlap_features: int):
    matched: list[str] = []
    mismatched: list[str] = []
    unavailable: list[str] = []
    components: list[float] = []
    for index, name in enumerate(FEATURE_NAMES):
        a = current.vector[index]
        b = historical.vector[index]
        if current.missing_mask[index] or historical.missing_mask[index] or a is None or b is None:
            unavailable.append(name)
            continue
        component = min(abs(float(a) - float(b)) / FEATURE_SCALES[index], 2.0) / 2.0
        components.append(component)
        if component <= 0.20:
            matched.append(name)
        elif component >= 0.55:
            mismatched.append(name)
    if len(components) < minimum_overlap_features:
        return None, tuple(matched), tuple(mismatched), tuple(unavailable)
    return mean(components), tuple(matched), tuple(mismatched), tuple(unavailable)


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
