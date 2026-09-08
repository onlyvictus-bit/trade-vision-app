from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .authority_registry import FINAL_BAND_AUTHORITY, REGISTRY_VERSION, get_engine_authority


INTEGRITY_VERSION = "decision-spine-stage2-integrity.v1"
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class SourceMode(str, Enum):
    VERIFIED_SNAPSHOT = "VERIFIED_SNAPSHOT"
    REAL = "REAL"
    SYNTHETIC_FALLBACK = "SYNTHETIC_FALLBACK"
    MOCK = "MOCK"
    MASKED = "MASKED"
    UNKNOWN = "UNKNOWN"


_NON_AUTHORITATIVE_SOURCE_MODES = {
    SourceMode.SYNTHETIC_FALLBACK,
    SourceMode.MOCK,
    SourceMode.MASKED,
    SourceMode.UNKNOWN,
}


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    engine_id: str
    source_snapshot_hash: str
    availability: Availability = Availability.AVAILABLE
    source_mode: SourceMode = SourceMode.VERIFIED_SNAPSHOT
    identity_match: bool = True
    used_for_probability: bool = False
    neutral_default_substituted: bool = False
    final_band_claimed: bool = False
    future_leakage_detected: bool = False
    explanation_only: bool = True
    unavailable_reasons: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EngineIntegrityState:
    engine_id: str
    availability: Availability
    source_mode: SourceMode
    registered: bool
    snapshot_match: bool
    identity_match: bool
    used_for_probability: bool
    final_band_claimed: bool
    unavailable_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["availability"] = self.availability.value
        payload["source_mode"] = self.source_mode.value
        return payload


@dataclass(frozen=True, slots=True)
class Stage2IntegrityReport:
    integrity_version: str
    registry_version: str
    canonical_snapshot_hash: str
    status: str
    canonical_context_eligible: bool
    paper_promotion_eligible: bool
    final_band_authority: str
    engine_count: int
    available_count: int
    degraded_count: int
    unavailable_count: int
    hard_blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    engine_states: tuple[EngineIntegrityState, ...] = ()
    output_hash: str = ""
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["engine_states"] = [item.as_dict() for item in self.engine_states]
        return payload


def build_stage2_integrity_report(
    *,
    canonical_snapshot_hash: str,
    engine_receipts: Sequence[Any] = (),
    evidence_observations: Sequence[EvidenceObservation | Mapping[str, Any]] = (),
) -> Stage2IntegrityReport:
    """Validate Stage-2 evidence before it is allowed into DecisionContext.

    This gate is intentionally not a trading decision engine.  It cannot grant
    paper authority and it cannot execute.  Its only authority is to reject or
    degrade evidence that violates snapshot identity, provenance, availability,
    or final-authority rules.
    """

    blockers: list[str] = []
    warnings: list[str] = []
    states: list[EngineIntegrityState] = []

    if not _HASH_RE.fullmatch(str(canonical_snapshot_hash)):
        blockers.append("INVALID_CANONICAL_SNAPSHOT_HASH")

    normalized: list[EvidenceObservation] = []
    for receipt in engine_receipts:
        normalized.append(_observation_from_receipt(receipt))
    for observation in evidence_observations:
        normalized.append(_coerce_observation(observation))

    # A valid D2 hash with no Stage-2 evidence is not a clean decision context.
    # Fail closed so an empty/miswired analysis chain can never be interpreted
    # as neutral or safe.
    if not normalized:
        blockers.append("NO_STAGE2_EVIDENCE")

    seen: set[str] = set()
    for item in normalized:
        engine_id = item.engine_id.upper()
        registered = get_engine_authority(engine_id) is not None
        snapshot_match = item.source_snapshot_hash == canonical_snapshot_hash
        local_warnings: list[str] = []

        if engine_id in seen:
            blockers.append(f"DUPLICATE_ENGINE_RECEIPT:{engine_id}")
        seen.add(engine_id)

        if not registered:
            blockers.append(f"UNREGISTERED_ENGINE:{engine_id}")
        if not _HASH_RE.fullmatch(str(item.source_snapshot_hash)):
            blockers.append(f"INVALID_ENGINE_SNAPSHOT_HASH:{engine_id}")
        elif not snapshot_match:
            blockers.append(f"SNAPSHOT_HASH_MISMATCH:{engine_id}")
        if not item.identity_match:
            blockers.append(f"ENGINE_IDENTITY_MISMATCH:{engine_id}")
        if item.future_leakage_detected:
            blockers.append(f"FUTURE_LEAKAGE_DETECTED:{engine_id}")
        if item.neutral_default_substituted:
            blockers.append(f"UNAVAILABLE_EVIDENCE_REPLACED_WITH_NEUTRAL:{engine_id}")

        authority = get_engine_authority(engine_id)
        if item.final_band_claimed and (authority is None or not authority.may_set_final_band):
            blockers.append(f"UNAUTHORIZED_FINAL_BAND_CLAIM:{engine_id}")
        if item.final_band_claimed and engine_id == FINAL_BAND_AUTHORITY:
            local_warnings.append("D6 final-band output present; Stage-2 gate records it but does not re-decide it")

        if item.source_mode in _NON_AUTHORITATIVE_SOURCE_MODES:
            local_warnings.append(f"non-authoritative source_mode={item.source_mode.value}")
            if item.used_for_probability:
                blockers.append(f"NON_AUTHORITATIVE_SOURCE_USED_FOR_PROBABILITY:{engine_id}")
            if item.final_band_claimed:
                blockers.append(f"NON_AUTHORITATIVE_SOURCE_USED_FOR_FINAL_BAND:{engine_id}")

        if item.availability in {Availability.DEGRADED, Availability.UNAVAILABLE, Availability.SKIPPED, Availability.ERROR}:
            local_warnings.append(f"availability={item.availability.value}")
        if item.availability in {Availability.UNAVAILABLE, Availability.ERROR} and not item.unavailable_reasons:
            local_warnings.append("unavailable/error evidence has no reason")

        states.append(
            EngineIntegrityState(
                engine_id=engine_id,
                availability=item.availability,
                source_mode=item.source_mode,
                registered=registered,
                snapshot_match=snapshot_match,
                identity_match=item.identity_match,
                used_for_probability=item.used_for_probability,
                final_band_claimed=item.final_band_claimed,
                unavailable_reasons=item.unavailable_reasons,
                warnings=tuple(sorted(set(local_warnings + list(item.notes)))),
            )
        )
        warnings.extend(f"{engine_id}:{text}" for text in local_warnings)

    states.sort(key=lambda row: row.engine_id)
    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))

    available_count = sum(item.availability is Availability.AVAILABLE for item in states)
    degraded_count = sum(item.availability is Availability.DEGRADED for item in states)
    unavailable_count = sum(
        item.availability in {Availability.UNAVAILABLE, Availability.SKIPPED, Availability.ERROR}
        for item in states
    )

    if blockers:
        status = "BLOCK"
    elif warnings or degraded_count or unavailable_count:
        status = "DEGRADED"
    else:
        status = "PASS"

    core = {
        "integrity_version": INTEGRITY_VERSION,
        "registry_version": REGISTRY_VERSION,
        "canonical_snapshot_hash": canonical_snapshot_hash,
        "status": status,
        "canonical_context_eligible": not blockers,
        # This layer can never grant promotion.  Promotion remains a later D6 +
        # proof + paper-authority + human-approval responsibility.
        "paper_promotion_eligible": False,
        "final_band_authority": FINAL_BAND_AUTHORITY,
        "engine_count": len(states),
        "available_count": available_count,
        "degraded_count": degraded_count,
        "unavailable_count": unavailable_count,
        "hard_blockers": blockers,
        "warnings": warnings,
        "engine_states": [item.as_dict() for item in states],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    output_hash = _digest(core)
    return Stage2IntegrityReport(
        integrity_version=INTEGRITY_VERSION,
        registry_version=REGISTRY_VERSION,
        canonical_snapshot_hash=canonical_snapshot_hash,
        status=status,
        canonical_context_eligible=not blockers,
        paper_promotion_eligible=False,
        final_band_authority=FINAL_BAND_AUTHORITY,
        engine_count=len(states),
        available_count=available_count,
        degraded_count=degraded_count,
        unavailable_count=unavailable_count,
        hard_blockers=tuple(blockers),
        warnings=tuple(warnings),
        engine_states=tuple(states),
        output_hash=output_hash,
    )


def _observation_from_receipt(receipt: Any) -> EvidenceObservation:
    engine_id = str(_get(receipt, "engine_id", "UNKNOWN"))
    snapshot_hash = str(_get(receipt, "source_snapshot_hash", ""))
    status = str(_get(receipt, "status", "degraded")).lower()
    summary = _get(receipt, "output_summary", {})
    summary = summary if isinstance(summary, Mapping) else {}
    warnings = _get(receipt, "warnings", ())
    warnings_tuple = tuple(str(item) for item in (warnings or ()))
    availability = {
        "completed": Availability.AVAILABLE,
        "degraded": Availability.DEGRADED,
        "skipped": Availability.SKIPPED,
        "error": Availability.ERROR,
        "failed": Availability.ERROR,
        "unavailable": Availability.UNAVAILABLE,
    }.get(status, Availability.DEGRADED)

    unavailable_reasons = tuple(sorted(set(_collect_unavailable_reasons(summary))))
    if unavailable_reasons and availability is Availability.AVAILABLE:
        # An engine can complete successfully while some evidence families are
        # unavailable.  That completion is not equivalent to a clean market.
        availability = Availability.DEGRADED

    source_mode = _coerce_source_mode(summary.get("source_mode", SourceMode.VERIFIED_SNAPSHOT.value))
    final_band_claimed = engine_id.upper() == FINAL_BAND_AUTHORITY and any(
        key in summary for key in ("final_decision", "decision_band")
    )
    return EvidenceObservation(
        engine_id=engine_id,
        source_snapshot_hash=snapshot_hash,
        availability=availability,
        source_mode=source_mode,
        identity_match=bool(_get(receipt, "identity_match", False)),
        used_for_probability=bool(_get(receipt, "used_for_probability", False)),
        neutral_default_substituted=bool(summary.get("neutral_default_substituted", False)),
        final_band_claimed=final_band_claimed,
        future_leakage_detected=bool(summary.get("future_leakage_detected", False)),
        explanation_only=bool(summary.get("explanation_only", True)),
        unavailable_reasons=unavailable_reasons,
        notes=warnings_tuple,
    )


def _coerce_observation(value: EvidenceObservation | Mapping[str, Any]) -> EvidenceObservation:
    if isinstance(value, EvidenceObservation):
        return value
    return EvidenceObservation(
        engine_id=str(value.get("engine_id", "UNKNOWN")),
        source_snapshot_hash=str(value.get("source_snapshot_hash", "")),
        availability=_coerce_availability(value.get("availability", Availability.AVAILABLE.value)),
        source_mode=_coerce_source_mode(value.get("source_mode", SourceMode.VERIFIED_SNAPSHOT.value)),
        identity_match=bool(value.get("identity_match", True)),
        used_for_probability=bool(value.get("used_for_probability", False)),
        neutral_default_substituted=bool(value.get("neutral_default_substituted", False)),
        final_band_claimed=bool(value.get("final_band_claimed", False)),
        future_leakage_detected=bool(value.get("future_leakage_detected", False)),
        explanation_only=bool(value.get("explanation_only", True)),
        unavailable_reasons=tuple(str(item) for item in value.get("unavailable_reasons", ()) or ()),
        notes=tuple(str(item) for item in value.get("notes", ()) or ()),
    )


def _coerce_availability(value: Any) -> Availability:
    text = str(getattr(value, "value", value)).upper()
    try:
        return Availability(text)
    except ValueError:
        return Availability.DEGRADED


def _coerce_source_mode(value: Any) -> SourceMode:
    text = str(getattr(value, "value", value)).upper()
    aliases = {
        "VERIFIED": SourceMode.VERIFIED_SNAPSHOT,
        "VERIFIED_SNAPSHOT": SourceMode.VERIFIED_SNAPSHOT,
        "REAL": SourceMode.REAL,
        "SYNTHETIC_FALLBACK": SourceMode.SYNTHETIC_FALLBACK,
        "MOCK": SourceMode.MOCK,
        "MASKED": SourceMode.MASKED,
    }
    return aliases.get(text, SourceMode.UNKNOWN)


def _collect_unavailable_reasons(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    reasons: list[str] = []
    if isinstance(value, Mapping):
        explicit = value.get("unavailable_reasons")
        if isinstance(explicit, (list, tuple, set)):
            reasons.extend(str(item) for item in explicit if item)
        for key, child in value.items():
            key_text = str(key)
            if key_text.endswith("_status") and str(child).lower() in {"unavailable", "unknown", "missing", "error"}:
                reasons.append(".".join(path + (key_text,)) + f"={child}")
            elif key_text != "unavailable_reasons":
                reasons.extend(_collect_unavailable_reasons(child, path + (key_text,)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reasons.extend(_collect_unavailable_reasons(child, path + (str(index),)))
    return reasons


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
