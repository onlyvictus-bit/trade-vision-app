from __future__ import annotations

"""Bounded D2-native PTA marker evidence for M3.3.

PTA markers are explanation/availability evidence only. Marker events are hashed
against the exact D2 candle window and source snapshot. Missing dependency,
warmup, no-signal and calculation errors remain distinct.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..real_indicator_adapter import compute_pta_marker_outputs_with_telemetry


CANONICAL_PTA_MARKER_VERSION = "canonical-pta-marker-evidence.v1"
MAX_EVENTS_PER_INDICATOR = 32
MAX_RECEIPT_BYTES = 48_000


class CanonicalPtaMarkerError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PtaMarkerObservation:
    indicator_id: str
    status: str
    event_count: int
    bounded_events: tuple[dict[str, Any], ...]
    event_hash: str
    reason_code: str | None
    source_window_hash: str
    source_snapshot_hash: str
    source_timeframe: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "indicator_id": self.indicator_id,
            "status": self.status,
            "event_count": self.event_count,
            "bounded_events": list(self.bounded_events),
            "event_hash": self.event_hash,
            "reason_code": self.reason_code,
            "source_window_hash": self.source_window_hash,
            "source_snapshot_hash": self.source_snapshot_hash,
            "source_timeframe": self.source_timeframe,
        }


@dataclass(frozen=True, slots=True)
class CanonicalPtaMarkerEvidence:
    calculation_version: str
    source_snapshot_hash: str
    source_timeframe: str
    source_window_hash: str
    requested_count: int
    computed_count: int
    no_signal_count: int
    dependency_unavailable_count: int
    error_count: int
    observations: tuple[PtaMarkerObservation, ...]
    availability: str
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
            "source_snapshot_hash": self.source_snapshot_hash,
            "source_timeframe": self.source_timeframe,
            "source_window_hash": self.source_window_hash,
            "requested_count": self.requested_count,
            "computed_count": self.computed_count,
            "no_signal_count": self.no_signal_count,
            "dependency_unavailable_count": self.dependency_unavailable_count,
            "error_count": self.error_count,
            "observations": [item.as_dict() for item in self.observations],
            "availability": self.availability,
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


def build_canonical_pta_marker_evidence(
    *,
    candles: Sequence[Mapping[str, Any]],
    indicator_ids: Sequence[str],
    source_snapshot_hash: str,
    source_timeframe: str,
) -> CanonicalPtaMarkerEvidence:
    if len(source_snapshot_hash) != 64:
        raise CanonicalPtaMarkerError("INVALID_SOURCE_SNAPSHOT_HASH")
    ids = tuple(sorted({str(item).strip() for item in indicator_ids if str(item).strip()}))
    if not ids:
        raise CanonicalPtaMarkerError("EMPTY_PTA_INDICATOR_SET")
    stable_candles = [
        {
            "event_time": row.get("event_time"),
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
            "volume": row.get("volume"),
        }
        for row in candles
    ]
    source_window_hash = _stable_hash(stable_candles)
    outputs, telemetry, dependency = compute_pta_marker_outputs_with_telemetry(stable_candles, list(ids))
    dependency_available = bool(dependency.get("dependency_available", False))

    observations: list[PtaMarkerObservation] = []
    warnings: list[str] = []
    for row in sorted(telemetry, key=lambda item: str(item.get("indicator_id", ""))):
        indicator_id = str(row.get("indicator_id", ""))
        status = str(row.get("status", "error"))
        raw_events = outputs.get(indicator_id)
        events = raw_events if isinstance(raw_events, list) else []
        bounded = tuple(_bounded_event(event) for event in events[-MAX_EVENTS_PER_INDICATOR:] if isinstance(event, Mapping))
        event_hash = _stable_hash(
            {
                "indicator_id": indicator_id,
                "source_window_hash": source_window_hash,
                "source_snapshot_hash": source_snapshot_hash.lower(),
                "source_timeframe": source_timeframe,
                "events": bounded,
                "status": status,
            }
        )
        if status == "dependency_unavailable":
            reason = "DEPENDENCY_UNAVAILABLE"
        elif status == "no_signal":
            reason = "NO_SIGNAL"
        elif status == "error":
            reason = "CALCULATION_ERROR"
        else:
            reason = None
        observations.append(
            PtaMarkerObservation(
                indicator_id=indicator_id,
                status=status,
                event_count=int(row.get("event_count", len(events)) or 0),
                bounded_events=bounded,
                event_hash=event_hash,
                reason_code=reason,
                source_window_hash=source_window_hash,
                source_snapshot_hash=source_snapshot_hash.lower(),
                source_timeframe=str(source_timeframe),
            )
        )

    computed = sum(item.status == "computed" for item in observations)
    no_signal = sum(item.status == "no_signal" for item in observations)
    dependency_unavailable = sum(item.status == "dependency_unavailable" for item in observations)
    errors = sum(item.status == "error" for item in observations)
    if not dependency_available or dependency_unavailable:
        availability = "DEGRADED"
        warnings.append("PTA dependency is unavailable for one or more marker calculations.")
    elif errors:
        availability = "DEGRADED"
        warnings.append("One or more PTA marker calculations failed; no neutral marker was substituted.")
    else:
        availability = "AVAILABLE"

    seed = {
        "calculation_version": CANONICAL_PTA_MARKER_VERSION,
        "source_snapshot_hash": source_snapshot_hash.lower(),
        "source_timeframe": str(source_timeframe),
        "source_window_hash": source_window_hash,
        "observations": [item.as_dict() for item in observations],
        "availability": availability,
    }
    output_hash = _stable_hash(seed)
    result = CanonicalPtaMarkerEvidence(
        calculation_version=CANONICAL_PTA_MARKER_VERSION,
        source_snapshot_hash=source_snapshot_hash.lower(),
        source_timeframe=str(source_timeframe),
        source_window_hash=source_window_hash,
        requested_count=len(ids),
        computed_count=computed,
        no_signal_count=no_signal,
        dependency_unavailable_count=dependency_unavailable,
        error_count=errors,
        observations=tuple(observations),
        availability=availability,
        warnings=tuple(sorted(set(warnings))),
        output_hash=output_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_RECEIPT_BYTES:
        raise CanonicalPtaMarkerError("BOUNDED_PTA_RECEIPT_EXCEEDED")
    return result


def _bounded_event(event: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(event):
        value = event[key]
        if value is None or isinstance(value, (bool, int, float)):
            result[str(key)] = value
        elif isinstance(value, str):
            result[str(key)] = value[:160]
        else:
            result[str(key)] = str(value)[:160]
    return result


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
