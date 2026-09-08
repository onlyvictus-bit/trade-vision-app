from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .authority_registry import get_engine_authority
from .stage2_integrity import (
    Availability,
    EngineIntegrityState,
    SourceMode,
    Stage2IntegrityReport,
)


DECISION_CONTEXT_VERSION = "decision-context.v1"
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class DecisionContextError(ValueError):
    """Raised when evidence cannot safely enter the canonical DecisionContext."""


class IntegrityState(str, Enum):
    PASS = "PASS"
    DEGRADED = "DEGRADED"
    BLOCK = "BLOCK"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class DecisionIdentity:
    symbol: str
    timeframe: str
    decision_time: datetime
    snapshot_hash: str
    universe_watermark: str = ""

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        timeframe = self.timeframe.strip()
        if not symbol:
            raise DecisionContextError("symbol must be non-empty")
        if not timeframe:
            raise DecisionContextError("timeframe must be non-empty")
        if not _HASH_RE.fullmatch(self.snapshot_hash):
            raise DecisionContextError("snapshot_hash must be a 64-character SHA-256 hex digest")
        if not _is_timezone_aware(self.decision_time):
            raise DecisionContextError("decision_time must be timezone-aware")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "decision_time", self.decision_time.astimezone(timezone.utc))
        object.__setattr__(self, "snapshot_hash", self.snapshot_hash.lower())


@dataclass(frozen=True, slots=True)
class InputIntegrity:
    data_quality: float
    pit_status: IntegrityState
    freshness: IntegrityState
    quarantine_status: IntegrityState
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.data_quality) <= 1.0:
            raise DecisionContextError("data_quality must be within [0, 1]")
        reasons = tuple(sorted({str(item).strip() for item in self.reasons if str(item).strip()}))
        non_pass = (
            self.pit_status is not IntegrityState.PASS
            or self.freshness is not IntegrityState.PASS
            or self.quarantine_status is not IntegrityState.PASS
        )
        if non_pass and not reasons:
            raise DecisionContextError(
                "DEGRADED, UNKNOWN, or BLOCK input integrity requires an explicit reason"
            )
        object.__setattr__(self, "data_quality", float(self.data_quality))
        object.__setattr__(self, "reasons", reasons)


@dataclass(frozen=True, slots=True)
class EvidenceBlock:
    source_engine: str
    source_snapshot_hash: str
    status: Availability
    payload: Mapping[str, Any]
    observed_at: datetime | None = None
    source_mode: SourceMode = SourceMode.VERIFIED_SNAPSHOT
    evidence_version: str = "v1"
    capability_source: str = ""
    source_output_hash: str | None = None
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    used_for_probability: bool = False
    neutral_default_substituted: bool = False
    claims_proof_authority: bool = False
    claims_paper_authority: bool = False
    claims_trade_authority: bool = False
    final_band_claimed: bool = False

    def __post_init__(self) -> None:
        engine_id = self.source_engine.strip().upper()
        if not engine_id:
            raise DecisionContextError("source_engine must be non-empty")
        if not _HASH_RE.fullmatch(self.source_snapshot_hash):
            raise DecisionContextError(f"{engine_id}: source_snapshot_hash must be SHA-256 hex")
        if self.source_output_hash is not None and not _HASH_RE.fullmatch(self.source_output_hash):
            raise DecisionContextError(f"{engine_id}: source_output_hash must be SHA-256 hex when present")
        if self.observed_at is not None and not _is_timezone_aware(self.observed_at):
            raise DecisionContextError(f"{engine_id}: observed_at must be timezone-aware")
        reasons = tuple(sorted({str(item).strip() for item in self.reasons if str(item).strip()}))
        warnings = tuple(sorted({str(item).strip() for item in self.warnings if str(item).strip()}))
        if self.status in {
            Availability.DEGRADED,
            Availability.UNAVAILABLE,
            Availability.SKIPPED,
            Availability.ERROR,
        } and not reasons:
            raise DecisionContextError(f"{engine_id}: {self.status.value} evidence requires an explicit reason")
        object.__setattr__(self, "source_engine", engine_id)
        object.__setattr__(self, "source_snapshot_hash", self.source_snapshot_hash.lower())
        object.__setattr__(
            self,
            "source_output_hash",
            self.source_output_hash.lower() if self.source_output_hash is not None else None,
        )
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(timezone.utc) if self.observed_at else None)
        object.__setattr__(self, "evidence_version", self.evidence_version.strip() or "v1")
        object.__setattr__(self, "capability_source", self.capability_source.strip())
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "payload", _freeze_mapping(self.payload))

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_engine": self.source_engine,
            "source_snapshot_hash": self.source_snapshot_hash,
            "source_output_hash": self.source_output_hash,
            "status": self.status.value,
            "payload": _thaw(self.payload),
            "observed_at": _iso(self.observed_at),
            "source_mode": self.source_mode.value,
            "evidence_version": self.evidence_version,
            "capability_source": self.capability_source,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "used_for_probability": self.used_for_probability,
            "neutral_default_substituted": self.neutral_default_substituted,
            "claims_proof_authority": self.claims_proof_authority,
            "claims_paper_authority": self.claims_paper_authority,
            "claims_trade_authority": self.claims_trade_authority,
            "final_band_claimed": self.final_band_claimed,
        }


@dataclass(frozen=True, slots=True)
class DecisionProvenance:
    stage2_integrity_hash: str
    engines_run: tuple[str, ...]
    evidence_versions: tuple[str, ...]
    capability_sources: tuple[str, ...]
    source_output_hashes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage2_integrity_hash": self.stage2_integrity_hash,
            "engines_run": list(self.engines_run),
            "evidence_versions": list(self.evidence_versions),
            "capability_sources": list(self.capability_sources),
            "source_output_hashes": list(self.source_output_hashes),
        }


@dataclass(frozen=True, slots=True)
class DecisionContext:
    context_version: str
    identity: DecisionIdentity
    input_integrity: InputIntegrity
    price_structure: EvidenceBlock
    candle_anatomy: EvidenceBlock
    levels: EvidenceBlock
    indicators: EvidenceBlock
    market_regime: EvidenceBlock
    session_context: EvidenceBlock
    index_context: EvidenceBlock
    sector_context: EvidenceBlock
    relative_strength: EvidenceBlock
    memory: EvidenceBlock
    historical_analogs: EvidenceBlock
    hypotheses: EvidenceBlock
    strategy_candidates: EvidenceBlock
    orb_variants: EvidenceBlock
    afre_scenarios: EvidenceBlock
    derivatives: EvidenceBlock
    events: EvidenceBlock
    failure_scenarios: EvidenceBlock
    execution_quality: EvidenceBlock
    portfolio_risk: EvidenceBlock
    proof_status: EvidenceBlock
    paper_authority: EvidenceBlock
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    provenance: DecisionProvenance
    context_hash: str
    paper_promotion_eligible: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "context_version": self.context_version,
            "identity": {
                "symbol": self.identity.symbol,
                "timeframe": self.identity.timeframe,
                "decision_time": _iso(self.identity.decision_time),
                "snapshot_hash": self.identity.snapshot_hash,
                "universe_watermark": self.identity.universe_watermark,
            },
            "input_integrity": {
                "data_quality": self.input_integrity.data_quality,
                "pit_status": self.input_integrity.pit_status.value,
                "freshness": self.input_integrity.freshness.value,
                "quarantine_status": self.input_integrity.quarantine_status.value,
                "reasons": list(self.input_integrity.reasons),
            },
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "provenance": self.provenance.as_dict(),
            "paper_promotion_eligible": self.paper_promotion_eligible,
            "trade_allowed": self.trade_allowed,
            "order_routing_enabled": self.order_routing_enabled,
            "live_trading_blocked": self.live_trading_blocked,
        }
        for name in CANONICAL_EVIDENCE_FIELDS:
            result[name] = getattr(self, name).as_dict()
        if include_hash:
            result["context_hash"] = self.context_hash
        return result


CANONICAL_EVIDENCE_FIELDS: tuple[str, ...] = (
    "price_structure",
    "candle_anatomy",
    "levels",
    "indicators",
    "market_regime",
    "session_context",
    "index_context",
    "sector_context",
    "relative_strength",
    "memory",
    "historical_analogs",
    "hypotheses",
    "strategy_candidates",
    "orb_variants",
    "afre_scenarios",
    "derivatives",
    "events",
    "failure_scenarios",
    "execution_quality",
    "portfolio_risk",
    "proof_status",
    "paper_authority",
)

_NON_AUTHORITATIVE_PROBABILITY_MODES = {
    SourceMode.SYNTHETIC_FALLBACK,
    SourceMode.MOCK,
    SourceMode.MASKED,
    SourceMode.UNKNOWN,
}

_ALLOWED_STATUS_TRANSITIONS: dict[Availability, frozenset[Availability]] = {
    Availability.AVAILABLE: frozenset(Availability),
    Availability.DEGRADED: frozenset(
        {
            Availability.DEGRADED,
            Availability.UNAVAILABLE,
            Availability.SKIPPED,
            Availability.ERROR,
        }
    ),
    Availability.UNAVAILABLE: frozenset({Availability.UNAVAILABLE}),
    Availability.SKIPPED: frozenset({Availability.SKIPPED}),
    Availability.ERROR: frozenset({Availability.ERROR}),
}


def build_decision_context(
    *,
    identity: DecisionIdentity,
    input_integrity: InputIntegrity,
    stage2_integrity: Stage2IntegrityReport,
    evidence: Mapping[str, EvidenceBlock],
    blockers: Sequence[str] = (),
    warnings: Sequence[str] = (),
) -> DecisionContext:
    """Build the immutable canonical evidence object consumed by later D6 wiring.

    This function performs validation and deterministic assembly only. It does not
    fetch market data, run specialist engines, calculate a trade signal, grant
    proof/paper authority, or route orders.
    """

    if stage2_integrity.canonical_snapshot_hash.lower() != identity.snapshot_hash:
        raise DecisionContextError("Stage2IntegrityReport snapshot hash does not match DecisionIdentity")
    if not stage2_integrity.canonical_context_eligible or stage2_integrity.hard_blockers:
        raise DecisionContextError("Stage2IntegrityReport is not eligible for canonical context construction")
    if input_integrity.pit_status is not IntegrityState.PASS:
        raise DecisionContextError("PIT status must PASS before DecisionContext construction")
    if input_integrity.freshness is IntegrityState.BLOCK:
        raise DecisionContextError("blocked freshness cannot enter DecisionContext")
    if input_integrity.quarantine_status is IntegrityState.BLOCK:
        raise DecisionContextError("quarantined input cannot enter DecisionContext")

    supplied = set(evidence)
    required = set(CANONICAL_EVIDENCE_FIELDS)
    missing = sorted(required - supplied)
    extra = sorted(supplied - required)
    if missing:
        raise DecisionContextError(f"missing explicit evidence blocks: {', '.join(missing)}")
    if extra:
        raise DecisionContextError(f"unknown evidence blocks: {', '.join(extra)}")

    stage2_by_engine = _stage2_state_index(stage2_integrity)
    normalized: dict[str, EvidenceBlock] = {}
    provenance_engines: set[str] = set()
    evidence_versions: set[str] = set()
    capability_sources: set[str] = set()
    source_output_hashes: set[str] = set()

    for name in CANONICAL_EVIDENCE_FIELDS:
        block = evidence[name]
        _validate_evidence_block(
            name=name,
            block=block,
            identity=identity,
            stage2_by_engine=stage2_by_engine,
        )
        normalized[name] = block
        provenance_engines.add(block.source_engine)
        evidence_versions.add(f"{name}:{block.evidence_version}")
        if block.capability_source:
            capability_sources.add(f"{name}:{block.capability_source}")
        if block.source_output_hash:
            source_output_hashes.add(f"{name}:{block.source_engine}:{block.source_output_hash}")

    provenance = DecisionProvenance(
        stage2_integrity_hash=stage2_integrity.output_hash,
        engines_run=tuple(sorted(provenance_engines)),
        evidence_versions=tuple(sorted(evidence_versions)),
        capability_sources=tuple(sorted(capability_sources)),
        source_output_hashes=tuple(sorted(source_output_hashes)),
    )
    canonical_blockers = tuple(sorted({str(item).strip() for item in blockers if str(item).strip()}))
    canonical_warnings = tuple(sorted({str(item).strip() for item in warnings if str(item).strip()}))
    init_payload: dict[str, Any] = {
        "context_version": DECISION_CONTEXT_VERSION,
        "identity": identity,
        "input_integrity": input_integrity,
        **normalized,
        "blockers": canonical_blockers,
        "warnings": canonical_warnings,
        "provenance": provenance,
        "context_hash": "",
    }
    context = DecisionContext(**init_payload)
    context_hash = _digest(context.as_dict(include_hash=False))
    return DecisionContext(**{**init_payload, "context_hash": context_hash})


def unavailable_evidence(
    *,
    source_engine: str,
    snapshot_hash: str,
    reason: str,
    evidence_version: str = "v1",
    capability_source: str = "",
    status: Availability = Availability.UNAVAILABLE,
) -> EvidenceBlock:
    """Create an explicit missing-evidence block instead of a neutral default."""

    if status not in {Availability.UNAVAILABLE, Availability.SKIPPED, Availability.ERROR}:
        raise DecisionContextError("unavailable_evidence status must be UNAVAILABLE, SKIPPED, or ERROR")
    return EvidenceBlock(
        source_engine=source_engine,
        source_snapshot_hash=snapshot_hash,
        status=status,
        payload={},
        source_mode=SourceMode.UNKNOWN,
        evidence_version=evidence_version,
        capability_source=capability_source,
        reasons=(reason,),
        used_for_probability=False,
    )


def _stage2_state_index(stage2_integrity: Stage2IntegrityReport) -> dict[str, EngineIntegrityState]:
    index: dict[str, EngineIntegrityState] = {}
    for state in stage2_integrity.engine_states:
        engine_id = state.engine_id.upper()
        if engine_id in index:
            raise DecisionContextError(f"duplicate Stage2 engine state: {engine_id}")
        index[engine_id] = state
    return index


def _validate_evidence_block(
    *,
    name: str,
    block: EvidenceBlock,
    identity: DecisionIdentity,
    stage2_by_engine: Mapping[str, EngineIntegrityState],
) -> None:
    if block.source_snapshot_hash != identity.snapshot_hash:
        raise DecisionContextError(f"{name}: snapshot hash mismatch")
    if get_engine_authority(block.source_engine) is None:
        raise DecisionContextError(f"{name}: unregistered source engine {block.source_engine}")
    stage2_state = stage2_by_engine.get(block.source_engine)
    if stage2_state is None:
        raise DecisionContextError(
            f"{name}: source engine {block.source_engine} is absent from the exact Stage2IntegrityReport"
        )
    if not stage2_state.registered or not stage2_state.snapshot_match or not stage2_state.identity_match:
        raise DecisionContextError(f"{name}: Stage2 engine state is not causally valid")
    allowed_statuses = _ALLOWED_STATUS_TRANSITIONS[stage2_state.availability]
    if block.status not in allowed_statuses:
        raise DecisionContextError(
            f"{name}: evidence status {block.status.value} upgrades Stage2 status "
            f"{stage2_state.availability.value}"
        )
    if block.source_mode is not stage2_state.source_mode:
        raise DecisionContextError(
            f"{name}: source_mode {block.source_mode.value} does not match Stage2 source_mode "
            f"{stage2_state.source_mode.value}"
        )
    if block.observed_at is not None and block.observed_at > identity.decision_time:
        raise DecisionContextError(f"{name}: future evidence detected")
    if block.neutral_default_substituted:
        raise DecisionContextError(f"{name}: unavailable evidence was replaced with a neutral default")
    if block.source_mode in _NON_AUTHORITATIVE_PROBABILITY_MODES and block.used_for_probability:
        raise DecisionContextError(f"{name}: non-authoritative source mode cannot be probability evidence")
    if block.claims_proof_authority:
        raise DecisionContextError(f"{name}: DecisionContext evidence cannot grant proof authority")
    if block.claims_paper_authority:
        raise DecisionContextError(f"{name}: DecisionContext evidence cannot grant paper authority")
    if block.claims_trade_authority:
        raise DecisionContextError(f"{name}: DecisionContext evidence cannot grant trade authority")
    if block.final_band_claimed:
        raise DecisionContextError(f"{name}: pre-D6 DecisionContext evidence cannot claim a final band")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(
        {str(key): _freeze(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        if not _is_timezone_aware(value):
            raise DecisionContextError("datetime payload values must be timezone-aware")
        return value.astimezone(timezone.utc)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
