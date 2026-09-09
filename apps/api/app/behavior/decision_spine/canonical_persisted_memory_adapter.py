from __future__ import annotations

"""M3.3 adapter for the legacy persisted-indicator memory seam.

The adapter replaces N-per-indicator reads with one bounded query and collapses
correlated indicator rows into independent market episodes.  It deliberately
returns data only; the Paper Guidance migration facade mints the historical
receipt shape so locked D6/public contracts remain unchanged.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from ...models import IndicatorSignalHistoryRecord
from ... import storage


PERSISTED_MEMORY_ADAPTER_VERSION = "canonical-persisted-memory-adapter.v1"
MAX_BATCH_ROWS = 10_000
MAX_INDICATORS = 256


class CanonicalPersistedMemoryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PersistedMemoryEvidence:
    raw_record_count: int
    independent_episode_count: int
    independent_session_count: int
    independent_symbol_count: int
    complete_record_count: int
    excluded_record_count: int
    source_episode_hashes: tuple[str, ...]
    source_snapshot_hashes: tuple[str, ...]
    corpus_hash: str
    query_count: int
    summary: dict[str, Any]


def build_persisted_memory_evidence(
    *,
    symbol: str,
    timeframe: str,
    decision_time_ns: int,
    indicator_ids: Sequence[str],
    minimum_evidence_count: int,
    caller_historical_match_count: int = 0,
) -> PersistedMemoryEvidence:
    symbol = str(symbol).strip().upper()
    timeframe = str(timeframe).strip()
    indicators = tuple(sorted({str(item).strip() for item in indicator_ids if str(item).strip()}))
    if not symbol or not timeframe:
        raise CanonicalPersistedMemoryError("INVALID_MEMORY_IDENTITY")
    if not isinstance(decision_time_ns, int) or isinstance(decision_time_ns, bool) or decision_time_ns <= 0:
        raise CanonicalPersistedMemoryError("INVALID_DECISION_TIME")
    if not indicators or len(indicators) > MAX_INDICATORS:
        raise CanonicalPersistedMemoryError("INVALID_INDICATOR_SET")
    if minimum_evidence_count < 1:
        raise CanonicalPersistedMemoryError("INVALID_MINIMUM_EVIDENCE_COUNT")

    cutoff_iso = _iso_from_ns(decision_time_ns)
    rows = _load_batch(
        symbol=symbol,
        timeframe=timeframe,
        indicator_ids=indicators,
        decision_time_ns=decision_time_ns,
        cutoff_iso=cutoff_iso,
    )
    records: list[IndicatorSignalHistoryRecord] = []
    excluded = 0
    for row in rows:
        try:
            record = IndicatorSignalHistoryRecord.model_validate_json(row["history_json"])
        except Exception:
            excluded += 1
            continue
        if not _record_is_causal(record, decision_time_ns=decision_time_ns):
            excluded += 1
            continue
        records.append(record)

    # A single market snapshot/session may produce many indicator observations.
    # Collapse those correlated rows into one episode identity.  When a source
    # snapshot hash is absent, use the bounded causal tuple rather than merging
    # unrelated sessions or pretending the observation is independent.
    episode_groups: dict[str, list[IndicatorSignalHistoryRecord]] = {}
    for record in records:
        episode_key = _episode_key(record)
        episode_groups.setdefault(episode_key, []).append(record)

    source_episode_hashes = tuple(sorted(episode_groups))
    source_snapshot_hashes = tuple(
        sorted(
            {
                str(record.source_snapshot_hash)
                for record in records
                if record.source_snapshot_hash
            }
        )
    )
    session_keys = {
        (record.symbol.upper(), record.timeframe, record.session_phase, record.decision_time_ns)
        for record in records
    }
    symbol_keys = {record.symbol.upper() for record in records}
    independent_episode_count = len(source_episode_hashes)
    low_evidence = independent_episode_count < minimum_evidence_count

    corpus_seed = {
        "adapter_version": PERSISTED_MEMORY_ADAPTER_VERSION,
        "symbol": symbol,
        "timeframe": timeframe,
        "decision_time_ns": decision_time_ns,
        "indicator_ids": list(indicators),
        "source_episode_hashes": list(source_episode_hashes),
        "source_snapshot_hashes": list(source_snapshot_hashes),
        "complete_history_ids": sorted(record.history_id for record in records),
    }
    corpus_hash = _stable_hash(corpus_seed)
    summary = {
        # Compatibility field now reflects statistically honest independent
        # evidence rather than correlated indicator-row count.
        "historical_match_count": independent_episode_count,
        "raw_record_count": len(rows),
        "complete_record_count": len(records),
        "excluded_record_count": excluded,
        "independent_episode_count": independent_episode_count,
        "independent_session_count": len(session_keys),
        "independent_symbol_count": len(symbol_keys),
        "minimum_evidence_count": minimum_evidence_count,
        "minimum_evidence_pass": not low_evidence,
        "low_evidence_flag": low_evidence,
        "history_source": "persistent",
        "fixture_fallback_used": False,
        "indicator_count": len(indicators),
        "caller_historical_match_count": int(caller_historical_match_count or 0),
        "caller_count_used_for_authority": False,
        "decision_time_cutoff": cutoff_iso,
        "canonical_memory_intelligence": True,
        "calculation_version": PERSISTED_MEMORY_ADAPTER_VERSION,
        "corpus_hash": corpus_hash,
        "source_episode_hashes": list(source_episode_hashes),
        "source_snapshot_hashes": list(source_snapshot_hashes),
        "storage_query_count": 1,
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
    return PersistedMemoryEvidence(
        raw_record_count=len(rows),
        independent_episode_count=independent_episode_count,
        independent_session_count=len(session_keys),
        independent_symbol_count=len(symbol_keys),
        complete_record_count=len(records),
        excluded_record_count=excluded,
        source_episode_hashes=source_episode_hashes,
        source_snapshot_hashes=source_snapshot_hashes,
        corpus_hash=corpus_hash,
        query_count=1,
        summary=summary,
    )


def _load_batch(
    *,
    symbol: str,
    timeframe: str,
    indicator_ids: tuple[str, ...],
    decision_time_ns: int,
    cutoff_iso: str,
) -> list[dict[str, Any]]:
    storage.init_db()
    placeholders = ",".join("?" for _ in indicator_ids)
    # Match the old per-indicator upper bound while also imposing one global
    # anti-pathology ceiling.
    row_limit = min(MAX_BATCH_ROWS, max(500, 500 * len(indicator_ids)))
    params: list[Any] = [symbol, timeframe, *indicator_ids, decision_time_ns, decision_time_ns, cutoff_iso, row_limit]
    sql = f"""
        SELECT history_json
        FROM indicator_signal_history
        WHERE symbol = ?
          AND timeframe = ?
          AND indicator_id IN ({placeholders})
          AND counted_in_reliability = 1
          AND decision_time_ns <= ?
          AND signal_time_ns <= ?
          AND created_at <= ?
        ORDER BY signal_time_ns DESC, created_at DESC, history_id ASC
        LIMIT ?
    """
    with storage.connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def _record_is_causal(record: IndicatorSignalHistoryRecord, *, decision_time_ns: int) -> bool:
    return bool(
        record.label.label_status == "complete"
        and record.counted_in_reliability
        and record.no_future_leakage
        and not record.missing_mask
        and record.decision_time_ns <= decision_time_ns
        and record.signal_time_ns <= decision_time_ns
        and _iso_to_ns(record.created_at) <= decision_time_ns
    )


def _episode_key(record: IndicatorSignalHistoryRecord) -> str:
    identity = {
        "symbol": record.symbol.upper(),
        "timeframe": record.timeframe,
        "decision_time_ns": record.decision_time_ns,
        "session_phase": record.session_phase,
        "regime_id": record.regime_id,
        "source_snapshot_hash": record.source_snapshot_hash or "MISSING",
        "source_snapshot_id": record.source_snapshot_id or "MISSING",
    }
    return _stable_hash(identity)


def _iso_from_ns(timestamp_ns: int) -> str:
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).isoformat()


def _iso_to_ns(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1_000_000_000)
    except (TypeError, ValueError, OverflowError):
        return 2**63 - 1


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
