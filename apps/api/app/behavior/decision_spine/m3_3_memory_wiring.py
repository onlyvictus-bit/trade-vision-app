from __future__ import annotations

"""M3.3 production wiring primitives.

This module converts already-computed canonical memory specialists into bounded
Paper-Guidance-compatible receipts and Stage2 observations. It never executes
D6, never manufactures unavailable memory, and never grants proposal/veto/final
or execution authority.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .canonical_memory_world import CanonicalMemoryWorld
from .canonical_nine_candle_memory import CanonicalNineCandleMemory
from .canonical_pattern_memory import CanonicalPatternMemory
from .canonical_pta_marker_runtime import CanonicalPtaMarkerEvidence
from .canonical_reliability_memory import CanonicalReliabilityMemory
from .canonical_session_memory import CanonicalSessionMemory
from .stage2_integrity import Availability, EvidenceObservation, SourceMode


M33_MEMORY_WIRING_VERSION = "m3.3-memory-wiring.v1"
M33_CANONICAL_ENGINE_IDS = frozenset(
    {
        "PERSISTED_INDICATOR_MEMORY",
        "CANONICAL_RELIABILITY_MEMORY",
        "HISTORICAL_SESSION_MEMORY",
        "PATTERN_MEMORY",
        "ANALOG_MEMORY",
        "NINE_CANDLE_MEMORY",
        "PTA_MARKER_RUNTIME",
    }
)
MAX_RECEIPT_BYTES = 64_000


class M33MemoryWiringError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalMemoryReceipt:
    engine_id: str
    source_snapshot_hash: str
    output_hash: str
    status: str
    engine_version: str
    output_summary: Mapping[str, Any]
    warnings: tuple[str, ...] = ()
    used_for_probability: bool = False


def build_memory_receipts(
    *,
    memory_world: CanonicalMemoryWorld,
    reliability: CanonicalReliabilityMemory | None = None,
    session_memory: CanonicalSessionMemory | None = None,
    pattern_memory: CanonicalPatternMemory | None = None,
    nine_candle_memory: CanonicalNineCandleMemory | None = None,
    pta_markers: CanonicalPtaMarkerEvidence | None = None,
) -> tuple[CanonicalMemoryReceipt, ...]:
    root = memory_world.d2_snapshot_hash
    decision_time = memory_world.decision_time_ns
    views = [reliability, session_memory, pattern_memory, nine_candle_memory]
    for view in views:
        if view is None:
            continue
        if getattr(view, "d2_snapshot_hash", root) != root:
            raise M33MemoryWiringError(f"SNAPSHOT_MISMATCH:{type(view).__name__}")
        if int(getattr(view, "decision_time_ns", decision_time)) != decision_time:
            raise M33MemoryWiringError(f"DECISION_TIME_MISMATCH:{type(view).__name__}")
        if str(getattr(view, "corpus_hash", memory_world.corpus_hash)) != memory_world.corpus_hash:
            raise M33MemoryWiringError(f"CORPUS_HASH_MISMATCH:{type(view).__name__}")
    if pta_markers is not None and pta_markers.source_snapshot_hash != root:
        raise M33MemoryWiringError("SNAPSHOT_MISMATCH:PTA_MARKER_RUNTIME")

    receipts: list[CanonicalMemoryReceipt] = []
    receipts.append(
        _receipt(
            engine_id="ANALOG_MEMORY",
            root=root,
            version=memory_world.calculation_version,
            output_hash=memory_world.output_hash,
            availability=memory_world.availability,
            payload={
                **memory_world.as_dict(),
                "canonical_memory_world": True,
                "canonical_memory_wiring_version": M33_MEMORY_WIRING_VERSION,
            },
            warnings=memory_world.warnings,
        )
    )
    if reliability is not None:
        receipts.append(
            _receipt(
                engine_id="CANONICAL_RELIABILITY_MEMORY",
                root=root,
                version=reliability.calculation_version,
                output_hash=reliability.output_hash,
                availability=reliability.availability,
                payload=reliability.as_dict(),
                warnings=reliability.warnings,
            )
        )
    if session_memory is not None:
        receipts.append(
            _receipt(
                engine_id="HISTORICAL_SESSION_MEMORY",
                root=root,
                version=session_memory.calculation_version,
                output_hash=session_memory.output_hash,
                availability=session_memory.availability,
                payload=session_memory.as_dict(),
                warnings=session_memory.warnings,
            )
        )
    if pattern_memory is not None:
        receipts.append(
            _receipt(
                engine_id="PATTERN_MEMORY",
                root=root,
                version=pattern_memory.calculation_version,
                output_hash=pattern_memory.output_hash,
                availability=pattern_memory.availability,
                payload=pattern_memory.as_dict(),
            )
        )
    if nine_candle_memory is not None:
        receipts.append(
            _receipt(
                engine_id="NINE_CANDLE_MEMORY",
                root=root,
                version=nine_candle_memory.calculation_version,
                output_hash=nine_candle_memory.output_hash,
                availability=nine_candle_memory.availability,
                payload=nine_candle_memory.as_dict(),
                warnings=nine_candle_memory.warnings,
            )
        )
    if pta_markers is not None:
        receipts.append(
            _receipt(
                engine_id="PTA_MARKER_RUNTIME",
                root=root,
                version=pta_markers.calculation_version,
                output_hash=pta_markers.output_hash,
                availability=pta_markers.availability,
                payload=pta_markers.as_dict(),
                warnings=pta_markers.warnings,
            )
        )
    return tuple(sorted(receipts, key=lambda item: item.engine_id))


def build_m33_stage2_observations(receipts: Sequence[CanonicalMemoryReceipt]) -> tuple[EvidenceObservation, ...]:
    observations: list[EvidenceObservation] = []
    seen: set[str] = set()
    for receipt in sorted(receipts, key=lambda item: item.engine_id):
        engine = receipt.engine_id.upper()
        if engine in seen:
            raise M33MemoryWiringError(f"DUPLICATE_MEMORY_RECEIPT:{engine}")
        seen.add(engine)
        availability = Availability.AVAILABLE if receipt.status == "completed" else Availability.DEGRADED
        reasons: tuple[str, ...] = ()
        if availability is not Availability.AVAILABLE:
            summary = dict(receipt.output_summary)
            reason_values = summary.get("reason_codes") or summary.get("ood_reasons") or ()
            reasons = tuple(sorted({str(item) for item in reason_values if str(item)}))
            if not reasons:
                reasons = (f"{engine} canonical memory is degraded or unavailable.",)
        observations.append(
            EvidenceObservation(
                engine_id=engine,
                source_snapshot_hash=receipt.source_snapshot_hash,
                availability=availability,
                source_mode=SourceMode.VERIFIED_SNAPSHOT,
                identity_match=True,
                used_for_probability=False,
                neutral_default_substituted=False,
                final_band_claimed=False,
                future_leakage_detected=False,
                explanation_only=True,
                unavailable_reasons=reasons,
                notes=tuple(receipt.warnings),
            )
        )
    return tuple(observations)


def merge_m33_memory_receipts(existing: Sequence[Any], canonical: Sequence[CanonicalMemoryReceipt]) -> tuple[Any, ...]:
    """Replace only matching M3.3 memory engine slots; never duplicate them."""
    replacements = {item.engine_id.upper(): item for item in canonical}
    if len(replacements) != len(tuple(canonical)):
        raise M33MemoryWiringError("DUPLICATE_CANONICAL_MEMORY_ENGINE")
    retained = [
        item
        for item in existing
        if str(getattr(item, "engine_id", "")).upper() not in replacements
    ]
    merged = retained + list(replacements.values())
    ids = [str(getattr(item, "engine_id", "")).upper() for item in merged]
    if len(ids) != len(set(ids)):
        raise M33MemoryWiringError("DUPLICATE_ENGINE_AFTER_MEMORY_MERGE")
    return tuple(sorted(merged, key=lambda item: str(getattr(item, "engine_id", "")).upper()))


def unavailable_memory_receipt(
    *,
    engine_id: str,
    source_snapshot_hash: str,
    engine_version: str,
    reason: str,
) -> CanonicalMemoryReceipt:
    """Explicitly represent a real canonical family whose corpus is unavailable."""
    if not reason.strip():
        raise M33MemoryWiringError("UNAVAILABLE_MEMORY_REQUIRES_REASON")
    payload = {
        "canonical_memory_intelligence": True,
        "availability": "UNAVAILABLE",
        "reason_codes": [reason.strip()],
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
    return _receipt(
        engine_id=engine_id,
        root=source_snapshot_hash,
        version=engine_version,
        output_hash=_stable_hash({"engine_id": engine_id, "root": source_snapshot_hash, "payload": payload}),
        availability="UNAVAILABLE",
        payload=payload,
        warnings=(reason.strip(),),
    )


def _receipt(
    *,
    engine_id: str,
    root: str,
    version: str,
    output_hash: str,
    availability: str,
    payload: Mapping[str, Any],
    warnings: Sequence[str] = (),
) -> CanonicalMemoryReceipt:
    if len(root) != 64 or len(output_hash) != 64:
        raise M33MemoryWiringError(f"INVALID_HASH:{engine_id}")
    summary = json.loads(json.dumps(dict(payload), sort_keys=True, default=str))
    summary.update(
        {
            "canonical_memory_intelligence": True,
            "canonical_memory_wiring_version": M33_MEMORY_WIRING_VERSION,
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
    )
    if len(json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")) > MAX_RECEIPT_BYTES:
        raise M33MemoryWiringError(f"BOUNDED_MEMORY_RECEIPT_EXCEEDED:{engine_id}")
    status = "completed" if str(availability).upper() == "AVAILABLE" else "degraded"
    return CanonicalMemoryReceipt(
        engine_id=engine_id.upper(),
        source_snapshot_hash=root.lower(),
        output_hash=output_hash.lower(),
        status=status,
        engine_version=version,
        output_summary=summary,
        warnings=tuple(sorted({str(item) for item in warnings if str(item)})),
    )


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
