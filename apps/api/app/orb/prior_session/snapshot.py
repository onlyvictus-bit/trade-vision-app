"""BUILD-3E D-1 snapshot + full-series precompute (anti-leak law).

FULL CAUSAL HISTORY -> SESSIONIZE ONCE -> RECONSTRUCT ONCE -> SNAPSHOTS ->
FREEZE/HASH -> slice into train/validation/walk-forward/holdout. The first
holdout date keeps its D-1 snapshot even when that session belongs to the
training period; the snapshot only ever contains causally available facts.

BUILD-3 owns raw prior-session facts (PDH/PDL/session close/settlement
reference/volume availability/session identity/quality/basis). Derived
quantities (ATR/CPR/patterns/bands) stay with their canonical owners and may
only appear here as versioned calculation-receipt references.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Mapping, Sequence

from ..candidate_intake import AvailabilityState, canonical_sha256
from ..market_identity.contracts import (
    CalendarRecordV1,
    DataBasis,
    SessionProfileV1,
    SessionType,
)
from .contracts import (
    ORB_PRIOR_SNAPSHOT_VERSION,
    OrbCalculationReceiptRefV1,
    OrbCompletedSessionV1,
    OrbExpectedSessionGridV1,
    OrbPriorSessionContextSnapshotV1,
    OrbPriorSessionFactV1,
    OrbSessionReferencePriceV1,
    ReferenceType,
    SessionCompleteness,
)
from .grid import GridUnavailable, assign_session_label, build_expected_grid
from .kernel import build_completed_session
from .references import coerce_basis, session_close_reference

_ELIGIBLE_COMPLETENESS = frozenset({
    SessionCompleteness.COMPLETE_TRUSTED,
    SessionCompleteness.COMPLETE_DEGRADED,
})
_ELIGIBLE_SESSION_TYPES = frozenset({
    SessionType.REGULAR,
    SessionType.PARTIAL,
    SessionType.SPECIAL,
})

_RAW_FACT_FIELDS = ("PDH", "PDL", "SESSION_CLOSE", "SESSION_VOLUME", "SESSION_IDENTITY", "SESSION_QUALITY", "DATA_BASIS")


def _fact(
    field_name: str,
    availability: AvailabilityState,
    completed: OrbCompletedSessionV1,
    *,
    value=None,
    units: str | None = None,
) -> OrbPriorSessionFactV1:
    if availability is AvailabilityState.AVAILABLE:
        return OrbPriorSessionFactV1(
            field_name=field_name,
            availability=availability,
            value=value,
            units=units,
            observed_at=completed.observed_at,
            available_at=completed.available_at,
            source_id=",".join(completed.input_source_ids),
            source_hash=completed.input_content_hash,
            dependency_ids=completed.dependency_ids,
        )
    return OrbPriorSessionFactV1(field_name=field_name, availability=availability)


def select_prior_session(
    completed_by_label: Mapping[str, OrbCompletedSessionV1],
    *,
    instrument_key: str,
    contract_key: str | None,
    data_basis: DataBasis | str,
    current_session_label: str,
    knowledge_cutoff: datetime,
) -> tuple[OrbCompletedSessionV1 | None, str | None]:
    """Return (prior, None) or (None, unavailable_reason).

    Skips holidays/non-trading records (absent), MOCK sessions, unknown or
    incomplete sessions, wrong-contract/basis sessions, and anything whose
    availability postdates the knowledge cutoff (AS_KNOWN_THEN).
    """
    basis = coerce_basis(data_basis)
    current = current_session_label.strip()
    candidates: list[OrbCompletedSessionV1] = []
    for label in sorted(completed_by_label):
        if label >= current:
            continue
        session = completed_by_label[label]
        if session.instrument_key != instrument_key.strip():
            continue
        if session.contract_key != contract_key:
            continue
        if session.data_basis is not basis:
            continue
        if session.session_type not in _ELIGIBLE_SESSION_TYPES:
            continue
        if session.completeness not in _ELIGIBLE_COMPLETENESS:
            continue
        if session.available_at > knowledge_cutoff:
            continue
        candidates.append(session)
    if not candidates:
        return None, "NO_PRIOR_COMPLETED_SESSION_CAUSALLY_KNOWABLE"
    return candidates[-1], None


def build_prior_snapshot(
    *,
    instrument_key: str,
    contract_key: str | None,
    current_session_label: str,
    data_basis: DataBasis | str,
    knowledge_cutoff: datetime,
    prior: OrbCompletedSessionV1 | None,
    unavailable_reason: str | None = None,
    settlement: OrbSessionReferencePriceV1 | None = None,
    adjusted_close: OrbSessionReferencePriceV1 | None = None,
    currency: str = "UNSPECIFIED",
    calculation_receipt_refs: Sequence[OrbCalculationReceiptRefV1] = (),
) -> OrbPriorSessionContextSnapshotV1:
    """Freeze one D-1 snapshot. Every field carries availability + lineage."""
    basis = coerce_basis(data_basis)
    current = current_session_label.strip()
    if prior is None:
        facts = tuple(_fact(name, AvailabilityState.UNAVAILABLE, None) for name in _RAW_FACT_FIELDS)  # type: ignore[arg-type]
        payload = {
            "instrument": instrument_key, "contract": contract_key,
            "current": current, "prior": None,
            "basis": basis.value, "cutoff": knowledge_cutoff.isoformat(),
        }
        digest = canonical_sha256(payload)
        return OrbPriorSessionContextSnapshotV1(
            schema_version=ORB_PRIOR_SNAPSHOT_VERSION,
            snapshot_id=f"orb-d1:{digest[:24]}",
            snapshot_hash=digest,
            instrument_key=instrument_key.strip(),
            contract_key=contract_key,
            current_session_label=current,
            prior_session_label=None,
            prior_session_found=False,
            unavailable_reason=unavailable_reason or "NO_PRIOR_COMPLETED_SESSION_CAUSALLY_KNOWABLE",
            data_basis=basis,
            knowledge_cutoff=knowledge_cutoff,
            facts=facts,
            references=tuple(item for item in (settlement, adjusted_close) if item is not None),
            calculation_receipt_refs=tuple(calculation_receipt_refs),
            prior_session_hash=None,
            source_hashes=(),
        )

    price_ok = prior.price_availability is AvailabilityState.AVAILABLE
    volume_ok = prior.volume_availability is AvailabilityState.AVAILABLE
    facts = (
        _fact("PDH", AvailabilityState.AVAILABLE if price_ok else AvailabilityState.UNAVAILABLE,
              prior, value=prior.high, units=currency),
        _fact("PDL", AvailabilityState.AVAILABLE if price_ok else AvailabilityState.UNAVAILABLE,
              prior, value=prior.low, units=currency),
        _fact("SESSION_CLOSE", AvailabilityState.AVAILABLE if price_ok else AvailabilityState.UNAVAILABLE,
              prior, value=prior.close, units=currency),
        _fact("SESSION_VOLUME", AvailabilityState.AVAILABLE if volume_ok else AvailabilityState.UNAVAILABLE,
              prior, value=prior.session_volume, units="contracts_or_shares"),
        _fact("SESSION_IDENTITY", AvailabilityState.AVAILABLE, prior,
              value={"session_label": prior.session_label, "session_type": prior.session_type.value,
                     "timeframe": prior.timeframe, "session_hash": prior.session_hash}),
        _fact("SESSION_QUALITY", AvailabilityState.AVAILABLE, prior,
              value={"completeness": prior.completeness.value, "reasons": list(prior.state_reasons)}),
        _fact("DATA_BASIS", AvailabilityState.AVAILABLE, prior, value=prior.data_basis.value),
    )
    references: list[OrbSessionReferencePriceV1] = [
        session_close_reference(prior, currency=currency)
    ]
    for extra, expected_type in ((settlement, ReferenceType.OFFICIAL_DAILY_SETTLEMENT),
                                 (adjusted_close, ReferenceType.ADJUSTED_CLOSE)):
        if extra is None:
            references.append(_unavailable_reference(
                instrument_key, contract_key, prior.session_label, expected_type, currency, basis))
        else:
            if extra.reference_type is not expected_type:
                raise ValueError(f"wrong reference_type supplied for {expected_type.value}")
            if extra.session_label != prior.session_label or extra.instrument_key != prior.instrument_key:
                raise ValueError("supplied reference does not belong to the prior session")
            references.append(extra)

    source_hashes = {prior.input_content_hash, prior.session_hash}
    source_hashes.update(ref.source_hash for ref in references
                         if ref.availability is AvailabilityState.AVAILABLE and ref.source_hash)
    payload = {
        "instrument": instrument_key.strip(), "contract": contract_key,
        "current": current, "prior": prior.session_label,
        "prior_hash": prior.session_hash, "basis": basis.value,
        "cutoff": knowledge_cutoff.isoformat(),
        "facts": [(f.field_name, f.availability.value, f.value) for f in facts],
    }
    digest = canonical_sha256(payload)
    return OrbPriorSessionContextSnapshotV1(
        schema_version=ORB_PRIOR_SNAPSHOT_VERSION,
        snapshot_id=f"orb-d1:{digest[:24]}",
        snapshot_hash=digest,
        instrument_key=instrument_key.strip(),
        contract_key=contract_key,
        current_session_label=current,
        prior_session_label=prior.session_label,
        prior_session_found=True,
        unavailable_reason=None,
        data_basis=basis,
        knowledge_cutoff=knowledge_cutoff,
        facts=facts,
        references=tuple(references),
        calculation_receipt_refs=tuple(calculation_receipt_refs),
        prior_session_hash=prior.session_hash,
        source_hashes=tuple(sorted(source_hashes)),
    )


def _unavailable_reference(
    instrument_key: str,
    contract_key: str | None,
    session_label: str,
    reference_type: ReferenceType,
    currency: str,
    basis: DataBasis,
) -> OrbSessionReferencePriceV1:
    from .references import build_reference_price
    return build_reference_price(
        instrument_key=instrument_key,
        contract_key=contract_key,
        session_label=session_label,
        reference_type=reference_type,
        value=None,
        currency=currency,
        data_basis=basis,
        availability=AvailabilityState.UNAVAILABLE,
    )


def reconstruct_history(
    bars,
    *,
    instrument_key: str,
    contract_key: str | None,
    profile: SessionProfileV1,
    calendars_by_date: Mapping[date, CalendarRecordV1 | None],
    timeframe: str,
    timeframe_duration_ns: int,
    data_basis: DataBasis | str,
    source_cadence,
    market_as_of: datetime,
    knowledge_cutoff: datetime,
    source_id: str,
    venue_id: str,
    segment_id: str,
    instrument_type: str,
    currency: str = "UNSPECIFIED",
    symbol: str | None = None,
) -> dict[str, OrbCompletedSessionV1]:
    """One causal pass over the full bar history.

    Bars are grouped by BUILD-2 session label ONCE, each session is
    reconstructed ONCE, and the map is keyed by session label. Callers slice
    the frozen map afterwards; they must never re-derive D-1 inside a split.
    Sessions whose grid cannot be built (holidays, unknown timing) are absent
    from the map: an unfinished or non-trading day is not a completed session.

    The stream must be single-symbol/single-contract/single-basis; mixing
    contracts in one stream raises. Pre-split mixed streams before calling.
    """
    from .contracts import SourceCadence
    basis = coerce_basis(data_basis)
    indexed = list(enumerate(sorted(bars, key=lambda b: (b.timestamp_ns, b.sequence_number))))
    groups: dict[str, list] = {}
    for _, bar in indexed:
        label = assign_session_label(
            bar_open_ns=bar.timestamp_ns, profile=profile, calendars_by_date=calendars_by_date,
        )
        if label is None:
            continue
        groups.setdefault(label, []).append(bar)

    completed: dict[str, OrbCompletedSessionV1] = {}
    for label in sorted(groups):
        label_day = date.fromisoformat(label)
        calendar = calendars_by_date.get(label_day)
        try:
            grid = build_expected_grid(
                instrument_key=instrument_key,
                contract_key=contract_key,
                session_label=label,
                profile=profile,
                calendar=calendar,
                timeframe=timeframe,
                timeframe_duration_ns=timeframe_duration_ns,
                data_basis=basis,
                source_cadence=source_cadence,
                market_as_of=market_as_of,
                knowledge_cutoff=knowledge_cutoff,
                source_id=source_id,
            )
        except GridUnavailable:
            continue
        stream_symbols = {str(bar.symbol).strip().upper() for bar in groups[label]}
        if len(stream_symbols) != 1:
            raise ValueError("a single-contract stream must carry one symbol per session")
        resolved_symbol = symbol.strip().upper() if symbol else next(iter(stream_symbols))
        if any(str(bar.symbol).strip().upper() != resolved_symbol for bar in groups[label]):
            raise ValueError("mixed symbols in one reconstruction stream")
        completed[label] = build_completed_session(
            grid, groups[label],
            symbol=resolved_symbol,
            venue_id=venue_id, segment_id=segment_id, instrument_type=instrument_type,
            currency=currency,
        )
    return completed


def build_snapshot_map(
    completed_by_label: Mapping[str, OrbCompletedSessionV1],
    *,
    instrument_key: str,
    contract_key: str | None,
    data_basis: DataBasis | str,
    knowledge_cutoff: datetime,
    currency: str = "UNSPECIFIED",
) -> dict[str, OrbPriorSessionContextSnapshotV1]:
    """Freeze the full current_session -> D-1 snapshot map (hash-stable)."""
    snapshots: dict[str, OrbPriorSessionContextSnapshotV1] = {}
    for current in sorted(completed_by_label):
        prior, reason = select_prior_session(
            completed_by_label,
            instrument_key=instrument_key,
            contract_key=contract_key,
            data_basis=data_basis,
            current_session_label=current,
            knowledge_cutoff=knowledge_cutoff,
        )
        snapshots[current] = build_prior_snapshot(
            instrument_key=instrument_key,
            contract_key=contract_key,
            current_session_label=current,
            data_basis=data_basis,
            knowledge_cutoff=knowledge_cutoff,
            prior=prior,
            unavailable_reason=reason,
            currency=currency,
        )
    return snapshots


def slice_snapshots(
    snapshots: Mapping[str, OrbPriorSessionContextSnapshotV1],
    dates: Sequence[str],
) -> dict[str, OrbPriorSessionContextSnapshotV1]:
    """Split-safe slicing: subset the frozen map without recomputation.

    The first holdout/validation date keeps the D-1 snapshot reconstructed
    from the full causal history (correct lagged-feature semantics, not
    leakage). Slicing must never change a snapshot hash.
    """
    wanted = set(dates)
    return {label: snapshots[label] for label in sorted(snapshots) if label in wanted}
