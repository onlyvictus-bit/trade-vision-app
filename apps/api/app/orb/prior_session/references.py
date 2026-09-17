"""BUILD-3D reference identity + dual-source integrity (CTX-04 hardening).

close != settlement != adjusted close. A downstream gap calculation must
request the correct reference type; when settlement is required but
unavailable the answer is UNAVAILABLE, never close-substituted-as-settlement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from ..candidate_intake import AvailabilityState, canonical_sha256
from ..market_identity.contracts import DataBasis
from .contracts import (
    ORB_COMPARISON_RECEIPT_VERSION,
    ORB_REFERENCE_PRICE_VERSION,
    ComparisonOutcome,
    OrbCompletedSessionV1,
    OrbSessionReferencePriceV1,
    OrbSourceComparisonReceiptV1,
    ReferenceType,
)

_IDENTITY_CHECK_ORDER = (
    "instrument_key",
    "contract_key",
    "session_label",
    "reference_type",
    "data_basis",
    "currency",
    "adjustment_identity",
)


def build_reference_price(
    *,
    instrument_key: str,
    contract_key: str | None,
    session_label: str,
    reference_type: ReferenceType,
    value: float | None,
    currency: str,
    data_basis: DataBasis,
    adjustment_identity: str | None = None,
    market_effective_at: datetime | None = None,
    observed_at: datetime | None = None,
    published_at: datetime | None = None,
    available_at: datetime | None = None,
    source_id: str | None = None,
    source_version: str | None = None,
    source_hash: str | None = None,
    availability: AvailabilityState,
) -> OrbSessionReferencePriceV1:
    identity = {
        "instrument_key": instrument_key.strip(),
        "contract_key": contract_key,
        "session_label": session_label.strip(),
        "reference_type": reference_type.value,
        "data_basis": data_basis.value,
        "adjustment_identity": adjustment_identity,
    }
    reference_id = f"orb-ref:{canonical_sha256(identity)[:24]}"
    payload = {
        "schema_version": ORB_REFERENCE_PRICE_VERSION,
        "reference_id": reference_id,
        **identity,
        "value": value,
        "currency": currency.strip(),
        "market_effective_at": market_effective_at.isoformat() if market_effective_at else None,
        "observed_at": observed_at.isoformat() if observed_at else None,
        "published_at": published_at.isoformat() if published_at else None,
        "available_at": available_at.isoformat() if available_at else None,
        "source_id": source_id,
        "source_version": source_version,
        "source_hash": source_hash,
        "availability": availability.value,
    }
    return OrbSessionReferencePriceV1(
        schema_version=ORB_REFERENCE_PRICE_VERSION,
        reference_id=reference_id,
        record_hash=canonical_sha256(payload),
        instrument_key=instrument_key.strip(),
        contract_key=contract_key,
        session_label=session_label.strip(),
        reference_type=reference_type,
        value=value,
        currency=currency.strip(),
        data_basis=data_basis,
        adjustment_identity=adjustment_identity,
        market_effective_at=market_effective_at,
        observed_at=observed_at,
        published_at=published_at,
        available_at=available_at,
        source_id=source_id,
        source_version=source_version,
        source_hash=source_hash,
        availability=availability,
    )


def session_close_reference(
    completed: OrbCompletedSessionV1,
    *,
    currency: str,
    observed_at: datetime | None = None,
    available_at: datetime | None = None,
    source_id: str | None = None,
    source_version: str | None = None,
    source_hash: str | None = None,
) -> OrbSessionReferencePriceV1:
    """Typed SESSION_CLOSE derived only from a price-complete session."""
    if completed.price_availability is not AvailabilityState.AVAILABLE or completed.close is None:
        return build_reference_price(
            instrument_key=completed.instrument_key,
            contract_key=completed.contract_key,
            session_label=completed.session_label,
            reference_type=ReferenceType.SESSION_CLOSE,
            value=None,
            currency=currency,
            data_basis=completed.data_basis,
            availability=AvailabilityState.UNAVAILABLE,
        )
    return build_reference_price(
        instrument_key=completed.instrument_key,
        contract_key=completed.contract_key,
        session_label=completed.session_label,
        reference_type=ReferenceType.SESSION_CLOSE,
        value=float(completed.close),
        currency=currency,
        data_basis=completed.data_basis,
        market_effective_at=datetime.fromtimestamp(
            completed.session_market_end_ns / 1_000_000_000, tz=completed.knowledge_cutoff.tzinfo,
        ),
        observed_at=observed_at or completed.observed_at,
        available_at=available_at or completed.available_at,
        source_id=source_id or ",".join(completed.input_source_ids),
        source_version=source_version or completed.aggregation_algo_version,
        source_hash=source_hash or completed.input_content_hash,
        availability=AvailabilityState.AVAILABLE,
    )


def compare_references(
    left: OrbSessionReferencePriceV1,
    right: OrbSessionReferencePriceV1,
    *,
    tick: float | None = None,
    absolute_tolerance: float | None = None,
    knowledge_cutoff: datetime,
) -> OrbSourceComparisonReceiptV1:
    """Dual-source integrity gate. Identity comparability first; numbers last.

    A like-for-like disagreement beyond the registered tolerance is
    CONTEXT_SOURCE_CONFLICT (hard integrity error upstream). Anything that is
    not like-for-like is NOT_COMPARABLE (basis/session/contract/type mismatch),
    never a false conflict.
    """
    checks: list[str] = []
    comparable = True
    for field in _IDENTITY_CHECK_ORDER:
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        left_norm = left_value.value if isinstance(left_value, DataBasis) or hasattr(left_value, "value") else left_value
        right_norm = right_value.value if isinstance(right_value, DataBasis) or hasattr(right_value, "value") else right_value
        ok = left_norm == right_norm
        checks.append(f"{field}:{'LIKE_FOR_LIKE' if ok else 'BASIS_MISMATCH'}")
        comparable = comparable and ok

    if left.availability is not AvailabilityState.AVAILABLE or right.availability is not AvailabilityState.AVAILABLE:
        outcome = ComparisonOutcome.SECONDARY_SOURCE_UNAVAILABLE
        difference: float | None = None
        tolerance: float | None = None
    elif not comparable:
        outcome = ComparisonOutcome.NOT_COMPARABLE
        difference = None
        tolerance = None
    else:
        assert left.value is not None and right.value is not None
        difference = abs(float(left.value) - float(right.value))
        tolerance = 0.0
        if tick is not None:
            if tick <= 0:
                raise ValueError("tick must be positive when set")
            tolerance = max(tolerance, tick / 2.0)
        if absolute_tolerance is not None:
            if absolute_tolerance < 0:
                raise ValueError("absolute_tolerance cannot be negative")
            tolerance = max(tolerance, absolute_tolerance)
        if difference == 0.0:
            outcome = ComparisonOutcome.MATCH
        elif difference <= tolerance:
            outcome = ComparisonOutcome.MATCH_WITHIN_REGISTERED_TOLERANCE
        else:
            outcome = ComparisonOutcome.CONTEXT_SOURCE_CONFLICT

    receipt_id = f"orb-cmp:{canonical_sha256({'left': left.reference_id, 'right': right.reference_id, 'cutoff': knowledge_cutoff.isoformat()})[:24]}"
    payload = {
        "schema_version": ORB_COMPARISON_RECEIPT_VERSION,
        "receipt_id": receipt_id,
        "left": left.reference_id, "right": right.reference_id,
        "outcome": outcome.value, "checks": checks,
        "difference": difference, "tolerance": tolerance,
    }
    return OrbSourceComparisonReceiptV1(
        schema_version=ORB_COMPARISON_RECEIPT_VERSION,
        receipt_id=receipt_id,
        receipt_hash=canonical_sha256(payload),
        left_reference_id=left.reference_id,
        right_reference_id=right.reference_id,
        outcome=outcome,
        comparability_checks=tuple(checks),
        absolute_difference=difference,
        tolerance_used=tolerance,
        knowledge_cutoff=knowledge_cutoff,
    )


def coerce_basis(value: DataBasis | str) -> DataBasis:
    return value if isinstance(value, DataBasis) else DataBasis(value)
