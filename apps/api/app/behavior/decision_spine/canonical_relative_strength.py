from __future__ import annotations

"""M3.2-D canonical relative-strength intelligence.

Relative strength is a relationship between independently frozen causal market
observations.  This module preserves absolute and relative facts separately;
it never turns them into a trade score or action.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Literal, Sequence

from .canonical_context_intelligence import ContextSourceObservation
from .canonical_market_context import BenchmarkMapping, PriceBasisLineage


CANONICAL_RELATIVE_STRENGTH_VERSION = "canonical-relative-strength.v1"
RELATIVE_STRENGTH_WINDOW_VERSION = "relative-strength-window.v1"
MAX_RELATIVE_STRENGTH_BYTES = 16_000

RSAvailability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE"]
RSState = Literal[
    "STOCK_LEADER", "STOCK_LAGGARD", "SECTOR_LEADER", "SECTOR_LAGGARD",
    "INDEX_DOMINATED", "STOCK_IDIOSYNCRATIC", "ALIGNED_UP", "ALIGNED_DOWN",
    "DIVERGENT", "CONFLICTING", "UNKNOWN", "INSUFFICIENT_EVIDENCE",
]


class CanonicalRelativeStrengthError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RelativeStrengthWindow:
    window_id: str
    start_time_ns: int
    end_time_ns: int
    window_version: str = RELATIVE_STRENGTH_WINDOW_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanonicalReturnObservation:
    role: Literal["STOCK", "SECTOR", "INDEX"]
    source: ContextSourceObservation
    window: RelativeStrengthWindow
    start_price: str
    end_price: str
    price_basis: PriceBasisLineage
    series_hash: str
    observation_hash: str

    @property
    def return_fraction(self) -> Decimal:
        start = _decimal(self.start_price, "start_price")
        end = _decimal(self.end_price, "end_price")
        return (end / start) - Decimal(1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "source": self.source.as_dict(),
            "window": self.window.as_dict(),
            "start_price": self.start_price,
            "end_price": self.end_price,
            "price_basis": self.price_basis.as_dict(),
            "series_hash": self.series_hash,
            "observation_hash": self.observation_hash,
        }


@dataclass(frozen=True, slots=True)
class CanonicalRelativeStrength:
    d2_snapshot_hash: str
    decision_time_ns: int
    stock_symbol: str
    benchmark_mapping_hash: str
    window: RelativeStrengthWindow
    availability: RSAvailability
    state: RSState
    stock_return: str | None
    sector_return: str | None
    index_return: str | None
    stock_vs_sector: str | None
    stock_vs_index: str | None
    sector_vs_index: str | None
    supporting_facts: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_facts: tuple[str, ...]
    reason_codes: tuple[str, ...]
    source_hashes: tuple[str, ...]
    output_hash: str
    calculation_version: str = CANONICAL_RELATIVE_STRENGTH_VERSION
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
        payload = asdict(self)
        for key in ("supporting_facts", "contradictions", "missing_facts", "reason_codes", "source_hashes"):
            payload[key] = list(payload[key])
        return payload


def build_return_observation(
    *, role: Literal["STOCK", "SECTOR", "INDEX"], source: ContextSourceObservation,
    window: RelativeStrengthWindow, start_price: str, end_price: str,
    price_basis: PriceBasisLineage, series_hash: str,
) -> CanonicalReturnObservation:
    _validate_window(window, source.d2_decision_time_ns)
    if source.source_kind != role:
        raise CanonicalRelativeStrengthError(f"ROLE_SOURCE_MISMATCH:{role}")
    if source.availability != "AVAILABLE":
        raise CanonicalRelativeStrengthError(f"SOURCE_NOT_AVAILABLE:{role}")
    if source.synthetic or not source.identity_match:
        raise CanonicalRelativeStrengthError(f"SOURCE_IDENTITY_UNPROVEN:{role}")
    if source.source_bar_close_time_ns is None or source.source_bar_close_time_ns > source.d2_decision_time_ns:
        raise CanonicalRelativeStrengthError(f"SOURCE_BAR_NOT_CAUSAL:{role}")
    if source.available_at_ns is None or source.available_at_ns > source.d2_decision_time_ns:
        raise CanonicalRelativeStrengthError(f"SOURCE_NOT_CAUSAL:{role}")
    if source.freshness_state != "FRESH" or source.clock_skew_state != "ALIGNED":
        raise CanonicalRelativeStrengthError(f"SOURCE_NOT_FRESH_ALIGNED:{role}")
    if source.source_snapshot_hash is None:
        raise CanonicalRelativeStrengthError(f"SOURCE_HASH_MISSING:{role}")
    _hash(source.source_snapshot_hash, "source_snapshot_hash")
    _hash(series_hash, "series_hash")
    start = _decimal(start_price, "start_price")
    end = _decimal(end_price, "end_price")
    if start <= 0 or end <= 0:
        raise CanonicalRelativeStrengthError("NON_POSITIVE_PRICE")
    _validate_basis(price_basis)
    seed = {
        "version": CANONICAL_RELATIVE_STRENGTH_VERSION, "role": role,
        "source_hash": source.source_snapshot_hash.lower(), "series_hash": series_hash.lower(),
        "window": window.as_dict(), "start_price": _fmt(start), "end_price": _fmt(end),
        "price_basis": price_basis.as_dict(),
    }
    return CanonicalReturnObservation(
        role=role, source=source, window=window, start_price=_fmt(start), end_price=_fmt(end),
        price_basis=price_basis, series_hash=series_hash.lower(), observation_hash=_stable_hash(seed),
    )


def build_canonical_relative_strength(
    *, d2_snapshot_hash: str, decision_time_ns: int, stock_symbol: str,
    mapping: BenchmarkMapping, stock: CanonicalReturnObservation,
    sector: CanonicalReturnObservation | None, index: CanonicalReturnObservation | None,
    leadership_threshold: str = "0.005",
) -> CanonicalRelativeStrength:
    _hash(d2_snapshot_hash, "d2_snapshot_hash")
    _hash(mapping.lineage_hash, "mapping.lineage_hash")
    if decision_time_ns <= 0 or stock.source.d2_decision_time_ns != decision_time_ns:
        raise CanonicalRelativeStrengthError("DECISION_TIME_MISMATCH")
    if stock.role != "STOCK" or _sym(stock.source.symbol_or_universe) != _sym(stock_symbol):
        raise CanonicalRelativeStrengthError("STOCK_IDENTITY_MISMATCH")
    if _sym(mapping.stock_symbol) != _sym(stock_symbol):
        raise CanonicalRelativeStrengthError("BENCHMARK_STOCK_MISMATCH")
    observations = [stock] + [x for x in (sector, index) if x is not None]
    if len({x.role for x in observations}) != len(observations):
        raise CanonicalRelativeStrengthError("DUPLICATE_OBSERVATION_ROLE")
    for item in observations:
        if item.source.d2_decision_time_ns != decision_time_ns:
            raise CanonicalRelativeStrengthError("DECISION_TIME_MISMATCH")
        if item.window != stock.window:
            raise CanonicalRelativeStrengthError("WINDOW_MISMATCH")
    if sector and _sym(sector.source.symbol_or_universe) != _sym(mapping.sector_symbol):
        raise CanonicalRelativeStrengthError("SECTOR_BENCHMARK_MISMATCH")
    if index and _sym(index.source.symbol_or_universe) != _sym(mapping.broad_index_symbol):
        raise CanonicalRelativeStrengthError("INDEX_BENCHMARK_MISMATCH")

    missing: list[str] = []
    reasons: list[str] = []
    contradictions: list[str] = []
    support: list[str] = []
    for role, item in (("SECTOR", sector), ("INDEX", index)):
        if item is None:
            missing.append(f"{role}_RETURN_UNAVAILABLE")
    for item in observations[1:]:
        if not _basis_compatible(stock.price_basis, item.price_basis):
            contradictions.append(f"PRICE_BASIS_MISMATCH:STOCK:{item.role}")
            reasons.append("PRICE_BASIS_MISMATCH")

    sr = stock.return_fraction
    rr_sector = sector.return_fraction if sector and _basis_compatible(stock.price_basis, sector.price_basis) else None
    rr_index = index.return_fraction if index and _basis_compatible(stock.price_basis, index.price_basis) else None
    svs = sr - rr_sector if rr_sector is not None else None
    svi = sr - rr_index if rr_index is not None else None
    svi_sector = rr_sector - rr_index if rr_sector is not None and rr_index is not None and _basis_compatible(sector.price_basis, index.price_basis) else None
    threshold = _decimal(leadership_threshold, "leadership_threshold")
    if threshold < 0:
        raise CanonicalRelativeStrengthError("NEGATIVE_LEADERSHIP_THRESHOLD")

    if svs is not None and svi is not None:
        # Preserve directional contradictions before relative-performance labels.
        # A stock can be the strongest leg numerically while the surrounding
        # market context is still internally contradictory.  M3.2 must expose
        # that contradiction rather than flatten it into STOCK_LEADER/LAGGARD.
        if sr > 0 and rr_sector < 0 and rr_index > 0:
            state: RSState = "CONFLICTING"
            contradictions.append("STOCK_UP_SECTOR_DOWN_INDEX_UP")
            if svs >= threshold and svi >= threshold:
                support.extend(("STOCK_OUTPERFORMS_SECTOR", "STOCK_OUTPERFORMS_INDEX"))
        elif sr < 0 and rr_sector > 0 and rr_index < 0:
            state = "CONFLICTING"
            contradictions.append("STOCK_DOWN_SECTOR_UP_INDEX_DOWN")
            if svs <= -threshold and svi <= -threshold:
                support.extend(("STOCK_LAGS_SECTOR", "STOCK_LAGS_INDEX"))
        elif svs >= threshold and svi >= threshold:
            state = "STOCK_LEADER"
            support.extend(("STOCK_OUTPERFORMS_SECTOR", "STOCK_OUTPERFORMS_INDEX"))
        elif svs <= -threshold and svi <= -threshold:
            state = "STOCK_LAGGARD"
            support.extend(("STOCK_LAGS_SECTOR", "STOCK_LAGS_INDEX"))
        elif (sr > 0 > rr_sector and rr_index) or (sr < 0 < rr_sector and rr_index):
            state = "STOCK_IDIOSYNCRATIC"
            support.append("STOCK_DIRECTION_DIFFERS_FROM_BENCHMARKS")
        elif sr > 0 and rr_sector > 0 and rr_index > 0:
            state = "ALIGNED_UP"
        elif sr < 0 and rr_sector < 0 and rr_index < 0:
            state = "ALIGNED_DOWN"
        else:
            state = "DIVERGENT"
            contradictions.append("ABSOLUTE_DIRECTIONS_DIVERGE")
    else:
        state = "INSUFFICIENT_EVIDENCE"

    availability: RSAvailability = "AVAILABLE"
    if missing or contradictions:
        availability = "DEGRADED"
    if sector is None and index is None:
        availability = "UNAVAILABLE"
    source_hashes = tuple(sorted({x.source.source_snapshot_hash.lower() for x in observations if x.source.source_snapshot_hash}))
    seed = {
        "version": CANONICAL_RELATIVE_STRENGTH_VERSION, "d2_snapshot_hash": d2_snapshot_hash.lower(),
        "decision_time_ns": decision_time_ns, "stock_symbol": _sym(stock_symbol),
        "mapping_hash": mapping.lineage_hash.lower(), "window": stock.window.as_dict(),
        "stock_return": _fmt(sr), "sector_return": _fmt(rr_sector) if rr_sector is not None else None,
        "index_return": _fmt(rr_index) if rr_index is not None else None,
        "stock_vs_sector": _fmt(svs) if svs is not None else None,
        "stock_vs_index": _fmt(svi) if svi is not None else None,
        "sector_vs_index": _fmt(svi_sector) if svi_sector is not None else None,
        "state": state, "availability": availability, "supporting_facts": sorted(set(support)),
        "contradictions": sorted(set(contradictions)), "missing_facts": sorted(set(missing)),
        "reason_codes": sorted(set(reasons)), "source_hashes": source_hashes,
    }
    result = CanonicalRelativeStrength(
        d2_snapshot_hash=d2_snapshot_hash.lower(), decision_time_ns=decision_time_ns,
        stock_symbol=_sym(stock_symbol), benchmark_mapping_hash=mapping.lineage_hash.lower(), window=stock.window,
        availability=availability, state=state, stock_return=_fmt(sr),
        sector_return=_fmt(rr_sector) if rr_sector is not None else None,
        index_return=_fmt(rr_index) if rr_index is not None else None,
        stock_vs_sector=_fmt(svs) if svs is not None else None,
        stock_vs_index=_fmt(svi) if svi is not None else None,
        sector_vs_index=_fmt(svi_sector) if svi_sector is not None else None,
        supporting_facts=tuple(sorted(set(support))), contradictions=tuple(sorted(set(contradictions))),
        missing_facts=tuple(sorted(set(missing))), reason_codes=tuple(sorted(set(reasons))),
        source_hashes=source_hashes, output_hash=_stable_hash(seed),
    )
    if len(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")).encode()) > MAX_RELATIVE_STRENGTH_BYTES:
        raise CanonicalRelativeStrengthError("BOUNDED_RELATIVE_STRENGTH_EXCEEDED")
    return result


def _validate_window(window: RelativeStrengthWindow, decision_time_ns: int) -> None:
    if not window.window_id.strip() or not window.window_version.strip():
        raise CanonicalRelativeStrengthError("WINDOW_IDENTITY_MISSING")
    if window.start_time_ns <= 0 or window.end_time_ns <= window.start_time_ns:
        raise CanonicalRelativeStrengthError("INVALID_WINDOW_RANGE")
    if window.end_time_ns > decision_time_ns:
        raise CanonicalRelativeStrengthError("FUTURE_WINDOW")


def _validate_basis(basis: PriceBasisLineage) -> None:
    if basis.basis == "UNKNOWN":
        raise CanonicalRelativeStrengthError("PRICE_BASIS_UNKNOWN")
    if not basis.adjustment_policy_id.strip() or not basis.adjustment_policy_version.strip():
        raise CanonicalRelativeStrengthError("PRICE_BASIS_POLICY_MISSING")
    if basis.basis != "RAW" and (not basis.corporate_action_source_id or not basis.corporate_action_snapshot_hash):
        raise CanonicalRelativeStrengthError("ADJUSTMENT_LINEAGE_UNPROVEN")
    if basis.corporate_action_snapshot_hash:
        _hash(basis.corporate_action_snapshot_hash, "corporate_action_snapshot_hash")


def _basis_compatible(a: PriceBasisLineage, b: PriceBasisLineage) -> bool:
    return (
        a.basis == b.basis != "UNKNOWN"
        and a.adjustment_policy_id == b.adjustment_policy_id
        and a.adjustment_policy_version == b.adjustment_policy_version
        and a.corporate_action_source_id == b.corporate_action_source_id
        and a.corporate_action_snapshot_hash == b.corporate_action_snapshot_hash
    )


def _decimal(value: str | Decimal, field: str) -> Decimal:
    try:
        with localcontext() as ctx:
            ctx.prec = 34
            result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise CanonicalRelativeStrengthError(f"INVALID_DECIMAL:{field}") from None
    if not result.is_finite():
        raise CanonicalRelativeStrengthError(f"NON_FINITE_DECIMAL:{field}")
    return result


def _fmt(value: Decimal) -> str:
    with localcontext() as ctx:
        ctx.prec = 34
        text = format(value.normalize(), "f")
    return "0" if text in {"-0", ""} else text


def _hash(value: str, field: str) -> str:
    text = str(value).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise CanonicalRelativeStrengthError(f"INVALID_SHA256:{field}")
    return text


def _sym(value: str) -> str:
    text = " ".join(str(value).strip().upper().split())
    if not text:
        raise CanonicalRelativeStrengthError("EMPTY_SYMBOL")
    return text


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
