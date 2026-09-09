from __future__ import annotations

"""Snapshot-native canonical Nine-Candle memory for M3.3.

This adapter never calls the legacy mock evidence packet. Current candles come
only from the D2 closed-candle snapshot, current indicator evidence comes from
already-computed M3.1 telemetry, and historical outcomes come only from PIT-safe
persisted canonical memory records. Missing history remains unavailable.
"""

import hashlib
import json
import math
from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping, Sequence

from .canonical_memory_intelligence import CanonicalMemoryEpisode
from .memory_corpus import MemoryCorpus, MemoryRecord, retrieve_pit_records


CANONICAL_NINE_CANDLE_VERSION = "canonical-nine-candle-memory.v1"
NINE_CANDLE_FEATURE_VERSION = "canonical-nine-candle-features.v1"
MAX_MATCHES = 24
MAX_RECEIPT_BYTES = 64_000


class CanonicalNineCandleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NineCandleState:
    feature_version: str
    symbol: str
    timeframe: str
    decision_time_ns: int
    source_snapshot_hash: str
    candle_count: int
    candle_window_hash: str
    close_return_pct: float
    path_efficiency: float
    range_expansion_ratio: float | None
    volume_impulse_ratio: float | None
    bullish_candle_fraction: float
    bearish_candle_fraction: float
    indicator_facts: dict[str, dict[str, Any]]
    missing_indicators: tuple[str, ...]
    state_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_version": self.feature_version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "decision_time_ns": self.decision_time_ns,
            "source_snapshot_hash": self.source_snapshot_hash,
            "candle_count": self.candle_count,
            "candle_window_hash": self.candle_window_hash,
            "close_return_pct": self.close_return_pct,
            "path_efficiency": self.path_efficiency,
            "range_expansion_ratio": self.range_expansion_ratio,
            "volume_impulse_ratio": self.volume_impulse_ratio,
            "bullish_candle_fraction": self.bullish_candle_fraction,
            "bearish_candle_fraction": self.bearish_candle_fraction,
            "indicator_facts": self.indicator_facts,
            "missing_indicators": list(self.missing_indicators),
            "state_hash": self.state_hash,
        }

    def as_fact(self) -> dict[str, Any]:
        return {"nine_candle_state": self.as_dict()}


@dataclass(frozen=True, slots=True)
class NineCandleMatch:
    episode_hash: str
    session_id: str
    distance: float
    outcome_class: str
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_hash": self.episode_hash,
            "session_id": self.session_id,
            "distance": self.distance,
            "outcome_class": self.outcome_class,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class CanonicalNineCandleMemory:
    calculation_version: str
    d2_snapshot_hash: str
    decision_time_ns: int
    corpus_hash: str
    current_state_hash: str
    raw_candidate_count: int
    independent_match_count: int
    ood: bool
    ood_reasons: tuple[str, ...]
    outcome_distribution: dict[str, float]
    matches: tuple[NineCandleMatch, ...]
    availability: str
    confidence: str
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
            "d2_snapshot_hash": self.d2_snapshot_hash,
            "decision_time_ns": self.decision_time_ns,
            "corpus_hash": self.corpus_hash,
            "current_state_hash": self.current_state_hash,
            "raw_candidate_count": self.raw_candidate_count,
            "independent_match_count": self.independent_match_count,
            "ood": self.ood,
            "ood_reasons": list(self.ood_reasons),
            "outcome_distribution": self.outcome_distribution,
            "matches": [match.as_dict() for match in self.matches],
            "availability": self.availability,
            "confidence": self.confidence,
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


def build_nine_candle_state(
    *,
    symbol: str,
    timeframe: str,
    decision_time_ns: int,
    source_snapshot_hash: str,
    closed_bars: Sequence[Mapping[str, Any]],
    indicator_telemetry: Sequence[Mapping[str, Any]],
) -> NineCandleState:
    if decision_time_ns <= 0:
        raise CanonicalNineCandleError("INVALID_DECISION_TIME")
    if len(source_snapshot_hash) != 64:
        raise CanonicalNineCandleError("INVALID_SOURCE_SNAPSHOT_HASH")
    if len(closed_bars) < 9:
        raise CanonicalNineCandleError("INSUFFICIENT_CLOSED_BARS")

    bars = [_bar(row) for row in closed_bars[-9:]]
    if any(int(row["timestamp_ns"]) >= decision_time_ns for row in bars):
        raise CanonicalNineCandleError("FUTURE_OR_UNFINISHED_BAR_IN_9C")
    candle_seed = [
        {
            "timestamp_ns": row["timestamp_ns"],
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
        }
        for row in bars
    ]
    candle_window_hash = _stable_hash(candle_seed)

    closes = [float(row["close"]) for row in bars]
    opens = [float(row["open"]) for row in bars]
    ranges = [float(row["high"]) - float(row["low"]) for row in bars]
    return_pct = (closes[-1] - closes[0]) / max(abs(closes[0]), 1e-12) * 100.0
    path = sum(abs(closes[index] - closes[index - 1]) for index in range(1, len(closes)))
    efficiency = abs(closes[-1] - closes[0]) / path if path > 1e-12 else 0.0
    baseline_range = mean(ranges[:6]) if ranges[:6] else 0.0
    range_expansion = mean(ranges[6:]) / baseline_range if baseline_range > 1e-12 else None
    volumes = [float(row["volume"]) for row in bars if row["volume"] is not None and float(row["volume"]) > 0]
    volume_impulse = None
    if len(volumes) == 9:
        base_volume = mean(volumes[:6])
        volume_impulse = mean(volumes[6:]) / base_volume if base_volume > 0 else None

    indicator_facts: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for raw in indicator_telemetry:
        indicator_id = str(raw.get("indicator_id", "")).strip()
        evidence = raw.get("evidence")
        if not indicator_id or not isinstance(evidence, Mapping):
            continue
        if str(evidence.get("source_snapshot_hash") or "").lower() != source_snapshot_hash.lower():
            missing.append(indicator_id)
            continue
        status = str(evidence.get("status", "ERROR"))
        if status != "COMPUTED" or not bool(evidence.get("output_present", False)):
            missing.append(indicator_id)
            continue
        indicator_facts[indicator_id] = {
            "family": evidence.get("family"),
            "correlation_group": evidence.get("correlation_group"),
            "direction": evidence.get("direction"),
            "strength": evidence.get("strength"),
            "value": evidence.get("value"),
            "evidence_hash": evidence.get("evidence_hash"),
        }

    seed = {
        "feature_version": NINE_CANDLE_FEATURE_VERSION,
        "symbol": str(symbol).strip().upper(),
        "timeframe": str(timeframe).strip(),
        "decision_time_ns": decision_time_ns,
        "source_snapshot_hash": source_snapshot_hash.lower(),
        "candle_window_hash": candle_window_hash,
        "close_return_pct": round(return_pct, 12),
        "path_efficiency": round(efficiency, 12),
        "range_expansion_ratio": round(range_expansion, 12) if range_expansion is not None else None,
        "volume_impulse_ratio": round(volume_impulse, 12) if volume_impulse is not None else None,
        "bullish_candle_fraction": round(sum(close > open_ for close, open_ in zip(closes, opens)) / 9.0, 12),
        "bearish_candle_fraction": round(sum(close < open_ for close, open_ in zip(closes, opens)) / 9.0, 12),
        "indicator_facts": {key: indicator_facts[key] for key in sorted(indicator_facts)},
        "missing_indicators": sorted(set(missing)),
    }
    state_hash = _stable_hash(seed)
    return NineCandleState(
        feature_version=NINE_CANDLE_FEATURE_VERSION,
        symbol=str(symbol).strip().upper(),
        timeframe=str(timeframe).strip(),
        decision_time_ns=decision_time_ns,
        source_snapshot_hash=source_snapshot_hash.lower(),
        candle_count=9,
        candle_window_hash=candle_window_hash,
        close_return_pct=round(return_pct, 12),
        path_efficiency=round(efficiency, 12),
        range_expansion_ratio=round(range_expansion, 12) if range_expansion is not None else None,
        volume_impulse_ratio=round(volume_impulse, 12) if volume_impulse is not None else None,
        bullish_candle_fraction=round(sum(close > open_ for close, open_ in zip(closes, opens)) / 9.0, 12),
        bearish_candle_fraction=round(sum(close < open_ for close, open_ in zip(closes, opens)) / 9.0, 12),
        indicator_facts={key: indicator_facts[key] for key in sorted(indicator_facts)},
        missing_indicators=tuple(sorted(set(missing))),
        state_hash=state_hash,
    )


def build_canonical_nine_candle_memory(
    *,
    query_episode: CanonicalMemoryEpisode,
    current_state: NineCandleState,
    corpus: MemoryCorpus,
    max_matches: int = 12,
    minimum_independent_matches: int = 5,
    maximum_distance: float = 0.65,
) -> CanonicalNineCandleMemory:
    if current_state.source_snapshot_hash != query_episode.d2_snapshot_hash:
        raise CanonicalNineCandleError("CURRENT_9C_SNAPSHOT_MISMATCH")
    if current_state.decision_time_ns != query_episode.decision_time_ns:
        raise CanonicalNineCandleError("CURRENT_9C_DECISION_TIME_MISMATCH")
    if not 1 <= max_matches <= MAX_MATCHES:
        raise CanonicalNineCandleError("INVALID_MAX_MATCHES")
    if minimum_independent_matches < 1:
        raise CanonicalNineCandleError("INVALID_MINIMUM_MATCHES")
    if not 0.0 <= maximum_distance <= 1.0:
        raise CanonicalNineCandleError("INVALID_MAXIMUM_DISTANCE")

    candidates = [
        record
        for record in retrieve_pit_records(corpus, decision_time_ns=query_episode.decision_time_ns, labelled_only=True)
        if record.episode.symbol == query_episode.symbol
        and record.episode.timeframe == query_episode.timeframe
        and record.episode.episode_hash != query_episode.episode_hash
        and _state_from_episode(record.episode) is not None
    ]
    scored: list[tuple[float, MemoryRecord, tuple[str, ...]]] = []
    for record in candidates:
        historical = _state_from_episode(record.episode)
        assert historical is not None
        distance, blockers = _distance(current_state, historical)
        if distance is None or distance > maximum_distance:
            continue
        scored.append((distance, record, blockers))
    scored.sort(key=lambda item: (item[0], item[1].episode.episode_hash))

    selected: list[NineCandleMatch] = []
    seen_sessions: set[str] = set()
    for distance, record, blockers in scored:
        if record.episode.session_id in seen_sessions:
            continue
        seen_sessions.add(record.episode.session_id)
        assert record.label is not None
        selected.append(
            NineCandleMatch(
                episode_hash=record.episode.episode_hash,
                session_id=record.episode.session_id,
                distance=round(distance, 12),
                outcome_class=record.label.outcome_class,
                blockers=blockers,
            )
        )
        if len(selected) >= max_matches:
            break

    counts: dict[str, int] = {}
    for match in selected:
        counts[match.outcome_class] = counts.get(match.outcome_class, 0) + 1
    total = sum(counts.values())
    distribution = {key: round(value / total, 12) for key, value in sorted(counts.items())} if total else {}

    ood_reasons: list[str] = []
    if not selected:
        ood_reasons.append("NO_COMPARABLE_PERSISTED_9C_HISTORY")
    if len(selected) < minimum_independent_matches:
        ood_reasons.append(f"INSUFFICIENT_INDEPENDENT_9C_ANALOGS:{len(selected)}<{minimum_independent_matches}")
    ood = bool(ood_reasons)
    warnings = []
    if current_state.missing_indicators:
        warnings.append("Some canonical indicators were unavailable; 9C distance used only available evidence.")

    if not selected:
        availability = "UNAVAILABLE"
        confidence = "INSUFFICIENT_EVIDENCE"
    elif ood:
        availability = "DEGRADED"
        confidence = "OOD"
    else:
        availability = "AVAILABLE"
        confidence = "MEDIUM"

    seed = {
        "calculation_version": CANONICAL_NINE_CANDLE_VERSION,
        "d2_snapshot_hash": query_episode.d2_snapshot_hash,
        "decision_time_ns": query_episode.decision_time_ns,
        "corpus_hash": corpus.corpus_hash,
        "current_state_hash": current_state.state_hash,
        "raw_candidate_count": len(candidates),
        "matches": [match.as_dict() for match in selected],
        "outcome_distribution": distribution,
        "ood_reasons": ood_reasons,
        "availability": availability,
        "confidence": confidence,
    }
    output_hash = _stable_hash(seed)
    result = CanonicalNineCandleMemory(
        calculation_version=CANONICAL_NINE_CANDLE_VERSION,
        d2_snapshot_hash=query_episode.d2_snapshot_hash,
        decision_time_ns=query_episode.decision_time_ns,
        corpus_hash=corpus.corpus_hash,
        current_state_hash=current_state.state_hash,
        raw_candidate_count=len(candidates),
        independent_match_count=len(selected),
        ood=ood,
        ood_reasons=tuple(sorted(set(ood_reasons))),
        outcome_distribution=distribution,
        matches=tuple(selected),
        availability=availability,
        confidence=confidence,
        warnings=tuple(sorted(set(warnings))),
        output_hash=output_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_RECEIPT_BYTES:
        raise CanonicalNineCandleError("BOUNDED_9C_MEMORY_RECEIPT_EXCEEDED")
    return result


def _bar(raw: Mapping[str, Any]) -> dict[str, Any]:
    try:
        timestamp_ns = int(raw["timestamp_ns"])
        open_price = float(raw["open"])
        high = float(raw["high"])
        low = float(raw["low"])
        close = float(raw["close"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CanonicalNineCandleError("INVALID_9C_BAR") from exc
    if not all(math.isfinite(value) for value in (open_price, high, low, close)):
        raise CanonicalNineCandleError("INVALID_9C_BAR")
    if high < max(open_price, close) or low > min(open_price, close) or high < low:
        raise CanonicalNineCandleError("INVALID_9C_OHLC")
    volume = raw.get("volume")
    if volume is not None:
        try:
            volume = float(volume)
        except (TypeError, ValueError):
            volume = None
        if volume is not None and (not math.isfinite(volume) or volume < 0):
            volume = None
    return {
        "timestamp_ns": timestamp_ns,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def _state_from_episode(episode: CanonicalMemoryEpisode) -> NineCandleState | None:
    family = episode.fact_families.get("nine_candle")
    if not isinstance(family, Mapping):
        return None
    payload = family.get("nine_candle_state")
    if not isinstance(payload, Mapping) or payload.get("feature_version") != NINE_CANDLE_FEATURE_VERSION:
        return None
    try:
        indicator_facts = payload.get("indicator_facts", {})
        if not isinstance(indicator_facts, Mapping):
            return None
        return NineCandleState(
            feature_version=NINE_CANDLE_FEATURE_VERSION,
            symbol=str(payload.get("symbol", episode.symbol)),
            timeframe=str(payload.get("timeframe", episode.timeframe)),
            decision_time_ns=int(payload.get("decision_time_ns", episode.decision_time_ns)),
            source_snapshot_hash=str(payload.get("source_snapshot_hash", episode.d2_snapshot_hash)).lower(),
            candle_count=int(payload.get("candle_count", 9)),
            candle_window_hash=str(payload["candle_window_hash"]),
            close_return_pct=float(payload["close_return_pct"]),
            path_efficiency=float(payload["path_efficiency"]),
            range_expansion_ratio=float(payload["range_expansion_ratio"]) if payload.get("range_expansion_ratio") is not None else None,
            volume_impulse_ratio=float(payload["volume_impulse_ratio"]) if payload.get("volume_impulse_ratio") is not None else None,
            bullish_candle_fraction=float(payload["bullish_candle_fraction"]),
            bearish_candle_fraction=float(payload["bearish_candle_fraction"]),
            indicator_facts={str(key): dict(value) for key, value in indicator_facts.items() if isinstance(value, Mapping)},
            missing_indicators=tuple(str(item) for item in payload.get("missing_indicators", ())),
            state_hash=str(payload["state_hash"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _distance(current: NineCandleState, historical: NineCandleState) -> tuple[float | None, tuple[str, ...]]:
    numeric = [
        (current.close_return_pct, historical.close_return_pct, 3.0),
        (current.path_efficiency, historical.path_efficiency, 1.0),
        (current.range_expansion_ratio, historical.range_expansion_ratio, 2.0),
        (current.volume_impulse_ratio, historical.volume_impulse_ratio, 2.0),
        (current.bullish_candle_fraction, historical.bullish_candle_fraction, 1.0),
        (current.bearish_candle_fraction, historical.bearish_candle_fraction, 1.0),
    ]
    parts: list[float] = []
    blockers: list[str] = []
    for a, b, scale in numeric:
        if a is None or b is None:
            continue
        parts.append(min(abs(float(a) - float(b)) / scale, 1.0))
    common_indicators = sorted(set(current.indicator_facts) & set(historical.indicator_facts))
    for indicator_id in common_indicators:
        a = current.indicator_facts[indicator_id]
        b = historical.indicator_facts[indicator_id]
        if str(a.get("direction")) != str(b.get("direction")):
            parts.append(0.75)
        else:
            parts.append(0.0)
    if len(parts) < 4:
        blockers.append("INSUFFICIENT_OVERLAPPING_9C_FEATURES")
        return None, tuple(blockers)
    return mean(parts), tuple(blockers)


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
