"""Canonical ORB BUILD-1 candidate intake and provenance contracts.

This module is research-only.  It converts a manual/user or validated TrendForge
selection into immutable, point-in-time candidate evidence.  A candidate means
"eligible to study" only; this module has no direction, setup, final-band,
paper-ticket, execution, or order-routing authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


ORB_CANDIDATE_INTAKE_VERSION = "orb-candidate-intake.v1"
MANUAL_SELECTOR_VERSION = "manual-research-candidate.v1"
TRENDFORGE_SELECTOR_VERSION = "trendforge-ready-priority-radar.v1"

_SYMBOL_RE = re.compile(r"^[A-Z0-9&._ -]{1,80}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class InstrumentType(str, Enum):
    NSE_EQUITY = "NSE_EQUITY"
    NSE_DERIVATIVE = "NSE_DERIVATIVE"
    COMMODITY_FUTURE = "COMMODITY_FUTURE"
    REGISTERED_OTHER = "REGISTERED_OTHER"


class ReferenceType(str, Enum):
    CLOSE = "CLOSE"
    SETTLEMENT = "SETTLEMENT"
    ADJUSTED_CLOSE = "ADJUSTED_CLOSE"
    OTHER_REGISTERED = "OTHER_REGISTERED"


class UniverseScope(str, Enum):
    ONLINE_SELECTED = "ONLINE_SELECTED"
    OFFLINE_RESEARCH_UNIVERSE = "OFFLINE_RESEARCH_UNIVERSE"
    HISTORICAL_RECONSTRUCTED_SELECTION = "HISTORICAL_RECONSTRUCTED_SELECTION"


class AvailabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    SUSPECT = "SUSPECT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


class TruthState(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CandidateState(str, Enum):
    RECEIVED = "RECEIVED"
    IDENTITY_PENDING = "IDENTITY_PENDING"
    VALIDATED = "VALIDATED"
    ELIGIBLE_FOR_STUDY = "ELIGIBLE_FOR_STUDY"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    UNAVAILABLE_REQUIRED_FACT = "UNAVAILABLE_REQUIRED_FACT"


def _utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _parse_utc(value: Any, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return _utc(value, field_name=field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} is invalid") from exc
    return _utc(parsed, field_name=field_name)


def _canonical(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return _utc(value, field_name="timestamp").isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: _canonical(val) for key, val in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _validate_sha256(value: str, *, field_name: str) -> str:
    clean = str(value).strip().lower()
    if not _SHA256_RE.fullmatch(clean):
        raise ValueError(f"{field_name} must be a lowercase 64-character SHA-256")
    return clean


def _clean_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ValueError("candidate symbol is invalid")
    return symbol


@dataclass(frozen=True, slots=True)
class OrbCandidateSourceFactV1:
    fact_id: str
    name: str
    availability: AvailabilityState
    value: Any = None
    units: str | None = None
    source_id: str | None = None
    source_hash: str | None = None
    observed_at: datetime | None = None
    available_at: datetime | None = None
    quality: str = "UNSPECIFIED"
    required_for_selection: bool = False

    def __post_init__(self) -> None:
        if not self.fact_id.strip() or not self.name.strip():
            raise ValueError("fact_id and name are required")
        if self.source_hash is not None:
            object.__setattr__(self, "source_hash", _validate_sha256(self.source_hash, field_name="source_hash"))
        if self.observed_at is not None:
            object.__setattr__(self, "observed_at", _utc(self.observed_at, field_name="observed_at"))
        if self.available_at is not None:
            object.__setattr__(self, "available_at", _utc(self.available_at, field_name="available_at"))
        if self.observed_at is not None and self.available_at is not None and self.observed_at > self.available_at:
            raise ValueError("fact observed_at cannot be after available_at")
        if self.availability is AvailabilityState.AVAILABLE:
            if self.value is None:
                raise ValueError("AVAILABLE fact must carry a value")
            if self.available_at is None or self.source_id is None or self.source_hash is None:
                raise ValueError("AVAILABLE fact requires available_at, source_id, and source_hash")
        elif self.value is not None:
            raise ValueError("non-AVAILABLE fact cannot carry a fabricated value")


@dataclass(frozen=True, slots=True)
class OrbCandidateReferencePriceV1:
    reference_type: ReferenceType
    reference_session_id: str
    price_basis: str
    value: float
    units: str
    source_id: str
    source_hash: str
    observed_at: datetime
    available_at: datetime

    def __post_init__(self) -> None:
        if not self.reference_session_id.strip() or not self.price_basis.strip():
            raise ValueError("reference session and price basis are required")
        if not self.units.strip() or not self.source_id.strip():
            raise ValueError("reference units and source_id are required")
        if not math.isfinite(float(self.value)) or float(self.value) <= 0.0:
            raise ValueError("reference price must be finite and positive")
        object.__setattr__(self, "value", float(self.value))
        object.__setattr__(self, "source_hash", _validate_sha256(self.source_hash, field_name="reference source_hash"))
        object.__setattr__(self, "observed_at", _utc(self.observed_at, field_name="reference observed_at"))
        object.__setattr__(self, "available_at", _utc(self.available_at, field_name="reference available_at"))
        if self.observed_at > self.available_at:
            raise ValueError("reference observed_at cannot be after available_at")


@dataclass(frozen=True, slots=True)
class OrbCandidateReasonV1:
    reason_id: str
    reason_code: str
    truth: TruthState
    requires_reference_price: bool = False
    evidence_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.reason_id.strip() or not self.reason_code.strip():
            raise ValueError("reason_id and reason_code are required")
        object.__setattr__(self, "evidence_fact_ids", tuple(sorted(set(self.evidence_fact_ids))))


@dataclass(frozen=True, slots=True)
class OrbHistoricalReconstructionPolicyV1:
    policy_id: str
    policy_version: str
    selector_version: str
    selection_cutoff_rule: str
    universe_rule: str
    comparable_performance_requires_reconstruction: bool = True

    def __post_init__(self) -> None:
        required = (
            self.policy_id,
            self.policy_version,
            self.selector_version,
            self.selection_cutoff_rule,
            self.universe_rule,
        )
        if any(not str(item).strip() for item in required):
            raise ValueError("historical reconstruction policy fields are required")


@dataclass(frozen=True, slots=True)
class OrbCandidateIntakeV1:
    schema_version: str
    candidate_id: str
    candidate_hash: str
    symbol: str
    instrument_type: InstrumentType
    state: CandidateState
    source_adapter: str
    source_record_id: str
    selection_rule_version: str
    selection_cutoff: datetime
    universe_scope: UniverseScope
    reasons: tuple[OrbCandidateReasonV1, ...]
    source_facts: tuple[OrbCandidateSourceFactV1, ...]
    reference_price_identity: OrbCandidateReferencePriceV1 | None
    reconstruction_policy: OrbHistoricalReconstructionPolicyV1
    rejection_reasons: tuple[str, ...] = ()
    research_only: bool = True
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    may_set_final_band: bool = False
    may_execute: bool = False


def _dedupe_facts(facts: Iterable[OrbCandidateSourceFactV1]) -> tuple[OrbCandidateSourceFactV1, ...]:
    by_id: dict[str, OrbCandidateSourceFactV1] = {}
    for fact in facts:
        existing = by_id.get(fact.fact_id)
        if existing is None:
            by_id[fact.fact_id] = fact
        elif canonical_json_bytes(existing) != canonical_json_bytes(fact):
            raise ValueError(f"conflicting duplicate source fact: {fact.fact_id}")
    return tuple(by_id[key] for key in sorted(by_id))


def _dedupe_reasons(reasons: Iterable[OrbCandidateReasonV1]) -> tuple[OrbCandidateReasonV1, ...]:
    by_id: dict[str, OrbCandidateReasonV1] = {}
    for reason in reasons:
        existing = by_id.get(reason.reason_id)
        if existing is None:
            by_id[reason.reason_id] = reason
        elif canonical_json_bytes(existing) != canonical_json_bytes(reason):
            raise ValueError(f"conflicting duplicate selection reason: {reason.reason_id}")
    return tuple(by_id[key] for key in sorted(by_id))


def build_candidate_intake(
    *,
    symbol: str,
    instrument_type: InstrumentType,
    source_adapter: str,
    source_record_id: str,
    selection_rule_version: str,
    selection_cutoff: datetime,
    universe_scope: UniverseScope,
    reasons: Sequence[OrbCandidateReasonV1],
    source_facts: Sequence[OrbCandidateSourceFactV1],
    reconstruction_policy: OrbHistoricalReconstructionPolicyV1,
    reference_price_identity: OrbCandidateReferencePriceV1 | None = None,
) -> OrbCandidateIntakeV1:
    clean_symbol = _clean_symbol(symbol)
    cutoff = _utc(selection_cutoff, field_name="selection_cutoff")
    if not source_adapter.strip() or not source_record_id.strip() or not selection_rule_version.strip():
        raise ValueError("candidate source identity and selector version are required")

    canonical_facts = _dedupe_facts(source_facts)
    canonical_reasons = _dedupe_reasons(reasons)
    fact_ids = {fact.fact_id for fact in canonical_facts}
    failures: list[str] = []
    quarantine = False

    for fact in canonical_facts:
        if fact.available_at is not None and fact.available_at > cutoff:
            quarantine = True
            failures.append(f"FUTURE_FACT:{fact.fact_id}")
        if fact.required_for_selection and fact.availability is not AvailabilityState.AVAILABLE:
            failures.append(f"REQUIRED_FACT_{fact.availability.value}:{fact.fact_id}")

    if reference_price_identity is not None and reference_price_identity.available_at > cutoff:
        quarantine = True
        failures.append("FUTURE_REFERENCE_PRICE")

    for reason in canonical_reasons:
        unknown_fact_ids = set(reason.evidence_fact_ids) - fact_ids
        if unknown_fact_ids:
            failures.append(f"UNKNOWN_REASON_FACT:{reason.reason_id}:{','.join(sorted(unknown_fact_ids))}")
        if reason.truth is TruthState.TRUE and reason.requires_reference_price and reference_price_identity is None:
            failures.append(f"REFERENCE_PRICE_REQUIRED:{reason.reason_id}")

    if universe_scope is UniverseScope.HISTORICAL_RECONSTRUCTED_SELECTION:
        if not reconstruction_policy.comparable_performance_requires_reconstruction:
            failures.append("HISTORICAL_RECONSTRUCTION_POLICY_WEAKENED")
        if reconstruction_policy.selector_version != selection_rule_version:
            failures.append("HISTORICAL_SELECTOR_VERSION_MISMATCH")

    if quarantine:
        state = CandidateState.QUARANTINED
    elif any(reason.startswith(("REQUIRED_FACT_", "REFERENCE_PRICE_REQUIRED", "UNKNOWN_REASON_FACT")) for reason in failures):
        state = CandidateState.UNAVAILABLE_REQUIRED_FACT
    elif failures:
        state = CandidateState.REJECTED
    else:
        state = CandidateState.ELIGIBLE_FOR_STUDY

    identity_payload = {
        "schema_version": ORB_CANDIDATE_INTAKE_VERSION,
        "symbol": clean_symbol,
        "instrument_type": instrument_type.value,
        "source_adapter": source_adapter,
        "source_record_id": source_record_id,
        "selection_rule_version": selection_rule_version,
        "selection_cutoff": cutoff,
        "universe_scope": universe_scope.value,
    }
    candidate_id = f"orb-candidate:{canonical_sha256(identity_payload)[:24]}"
    draft = OrbCandidateIntakeV1(
        schema_version=ORB_CANDIDATE_INTAKE_VERSION,
        candidate_id=candidate_id,
        candidate_hash="",
        symbol=clean_symbol,
        instrument_type=instrument_type,
        state=state,
        source_adapter=source_adapter,
        source_record_id=source_record_id,
        selection_rule_version=selection_rule_version,
        selection_cutoff=cutoff,
        universe_scope=universe_scope,
        reasons=canonical_reasons,
        source_facts=canonical_facts,
        reference_price_identity=reference_price_identity,
        reconstruction_policy=reconstruction_policy,
        rejection_reasons=tuple(sorted(set(failures))),
    )
    candidate_hash = canonical_sha256({key: value for key, value in _canonical(draft).items() if key != "candidate_hash"})
    return replace(draft, candidate_hash=candidate_hash)


def manual_candidate_intake(
    symbol: str,
    *,
    selected_at: datetime,
    instrument_type: InstrumentType = InstrumentType.NSE_EQUITY,
    universe_scope: UniverseScope = UniverseScope.ONLINE_SELECTED,
    source_record_id: str | None = None,
    reference_price_identity: OrbCandidateReferencePriceV1 | None = None,
) -> OrbCandidateIntakeV1:
    selected_at = _utc(selected_at, field_name="selected_at")
    clean_symbol = _clean_symbol(symbol)
    record_id = source_record_id or f"manual:{clean_symbol}:{selected_at.isoformat()}"
    policy = OrbHistoricalReconstructionPolicyV1(
        policy_id="manual-research-candidate-reconstruction",
        policy_version="v1",
        selector_version=MANUAL_SELECTOR_VERSION,
        selection_cutoff_rule="selected_at is the point-in-time cutoff; facts available later are forbidden",
        universe_rule="manual selections are comparable only to a stored historical manual-selection record; no hindsight recreation",
    )
    reason = OrbCandidateReasonV1(
        reason_id="manual-research-candidate",
        reason_code="MANUAL_RESEARCH_CANDIDATE",
        truth=TruthState.TRUE,
    )
    source_hash = canonical_sha256({"record_id": record_id, "symbol": clean_symbol, "selected_at": selected_at})
    fact = OrbCandidateSourceFactV1(
        fact_id="manual_selection",
        name="manual selection receipt",
        availability=AvailabilityState.AVAILABLE,
        value=True,
        units="boolean",
        source_id="manual-user-intake",
        source_hash=source_hash,
        observed_at=selected_at,
        available_at=selected_at,
        quality="USER_OBSERVED",
        required_for_selection=True,
    )
    return build_candidate_intake(
        symbol=clean_symbol,
        instrument_type=instrument_type,
        source_adapter="MANUAL_RESEARCH_CANDIDATE",
        source_record_id=record_id,
        selection_rule_version=MANUAL_SELECTOR_VERSION,
        selection_cutoff=selected_at,
        universe_scope=universe_scope,
        reasons=[reason],
        source_facts=[fact],
        reconstruction_policy=policy,
        reference_price_identity=reference_price_identity,
    )


def trendforge_candidate_intakes(
    validated_intake: Mapping[str, Any],
    *,
    instrument_type: InstrumentType = InstrumentType.NSE_EQUITY,
    universe_scope: UniverseScope = UniverseScope.ONLINE_SELECTED,
) -> list[OrbCandidateIntakeV1]:
    """Adapt one already-validated TrendForge bridge intake without inventing facts.

    The bridge has already authenticated and freshness-checked the packet.  This
    adapter still fails closed if the persisted receipt is stale/rejected or if a
    selected row lacks causal timestamp/hash identity.  The current TrendForge
    schema does not contain reference close/settlement identity, so no such value
    is fabricated here; reference-dependent reasons must remain unavailable until
    a later source adapter supplies that contract.
    """

    intake_state = str(validated_intake.get("intakeState") or "")
    if intake_state != "ACCEPTED_RESEARCH_ONLY":
        return []
    packet = validated_intake.get("packet")
    if not isinstance(packet, Mapping):
        raise ValueError("validated TrendForge intake packet is missing")
    evidence = packet.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("validated TrendForge evidence is missing")
    candidates = evidence.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("validated TrendForge candidates are missing")

    evidence_at = _parse_utc(validated_intake.get("evidenceAsOf") or packet.get("evidenceAsOf"), field_name="TrendForge evidenceAsOf")
    received_at = _parse_utc(validated_intake.get("receivedAt"), field_name="TrendForge receivedAt")
    payload_hash = _validate_sha256(str(validated_intake.get("payloadSha256") or packet.get("payloadSha256") or ""), field_name="TrendForge payloadSha256")
    intake_id = str(validated_intake.get("intakeId") or "")
    if not intake_id:
        raise ValueError("validated TrendForge intakeId is missing")

    policy = OrbHistoricalReconstructionPolicyV1(
        policy_id="trendforge-live-selector-reconstruction",
        policy_version="v1",
        selector_version=TRENDFORGE_SELECTOR_VERSION,
        selection_cutoff_rule="candidate must have been available in the accepted TrendForge packet by receivedAt",
        universe_rule="historical comparable performance must replay the same READY/PRIORITY_RADAR selector from retained PIT packets",
    )

    outputs: list[OrbCandidateIntakeV1] = []
    for index, raw in enumerate(candidates):
        if not isinstance(raw, Mapping):
            continue
        payload = raw.get("payload") if isinstance(raw.get("payload"), Mapping) else {}
        top_state = str(raw.get("state") or "")
        payload_state = str(payload.get("state") or "")
        state = top_state or payload_state
        status_group = str(payload.get("statusGroup") or "")
        if state not in {"READY", "PRIORITY_RADAR"}:
            continue
        if status_group and status_group != "ready":
            continue

        symbol = _clean_symbol(str(raw.get("symbol") or payload.get("symbol") or ""))
        row_created = _parse_utc(raw.get("createdAt") or evidence_at, field_name="TrendForge candidate createdAt")
        source_record_id = f"{intake_id}:candidate:{raw.get('recordId', index)}"
        reason = OrbCandidateReasonV1(
            reason_id="trendforge-ready-selector",
            reason_code=f"TRENDFORGE_{state}",
            truth=TruthState.TRUE,
            evidence_fact_ids=("trendforge_candidate_state",),
        )
        fact = OrbCandidateSourceFactV1(
            fact_id="trendforge_candidate_state",
            name="TrendForge candidate selector state",
            availability=AvailabilityState.AVAILABLE,
            value=state,
            units="enum",
            source_id=intake_id,
            source_hash=payload_hash,
            observed_at=row_created,
            available_at=received_at,
            quality="VALIDATED_BRIDGE_RECEIPT",
            required_for_selection=True,
        )
        outputs.append(
            build_candidate_intake(
                symbol=symbol,
                instrument_type=instrument_type,
                source_adapter="TRENDFORGE_VALIDATED_INTAKE",
                source_record_id=source_record_id,
                selection_rule_version=TRENDFORGE_SELECTOR_VERSION,
                selection_cutoff=received_at,
                universe_scope=universe_scope,
                reasons=[reason],
                source_facts=[fact],
                reconstruction_policy=policy,
                reference_price_identity=None,
            )
        )
    return outputs


def project_eligible_symbols(candidates: Sequence[OrbCandidateIntakeV1], *, limit: int = 50) -> list[str]:
    """Compatibility projection for shadow comparison with legacy symbol lists."""
    seen: set[str] = set()
    symbols: list[str] = []
    for candidate in candidates:
        if candidate.state is not CandidateState.ELIGIBLE_FOR_STUDY:
            continue
        if candidate.symbol not in seen:
            seen.add(candidate.symbol)
            symbols.append(candidate.symbol)
        if len(symbols) >= limit:
            break
    return symbols
