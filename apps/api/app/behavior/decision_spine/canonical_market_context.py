from __future__ import annotations

"""M3.2-C canonical index + sector context foundations.

This module deliberately creates *facts*, not a trading score.  It owns the
versioned benchmark relationship, provider freshness policy, price-basis
lineage and the deterministic composition of independently frozen INDEX and
SECTOR observations admitted by the M3.2-A context-source contract.

Hard boundary: no proposal, veto, downgrade, final-band or execution authority.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal, Sequence

from .canonical_context_intelligence import (
    CanonicalContextError,
    ContextAvailability,
    ContextSourceObservation,
)


BENCHMARK_REGISTRY_VERSION = "benchmark-registry.v1"
PROVIDER_FRESHNESS_POLICY_VERSION = "context-provider-freshness-policy.v1"
PRICE_BASIS_LINEAGE_VERSION = "price-basis-lineage.v1"
CANONICAL_MARKET_CONTEXT_VERSION = "canonical-market-context.v1"
MAX_MARKET_CONTEXT_BYTES = 16_000

PriceBasis = Literal["RAW", "SPLIT_ADJUSTED", "TOTAL_RETURN_ADJUSTED", "UNKNOWN"]
ContextRelation = Literal["ALIGNED", "CONTRADICTORY", "PARTIAL", "UNKNOWN"]


class CanonicalMarketContextError(CanonicalContextError):
    """Raised when M3.2-C benchmark/context evidence cannot be proven."""


@dataclass(frozen=True, slots=True)
class BenchmarkMapping:
    stock_symbol: str
    sector_symbol: str
    broad_index_symbol: str
    effective_from_ns: int
    effective_to_ns: int | None
    mapping_source: str
    mapping_version: str
    lineage_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BenchmarkRegistry:
    entries: tuple[BenchmarkMapping, ...]
    registry_version: str = BENCHMARK_REGISTRY_VERSION

    def resolve(self, *, stock_symbol: str, decision_time_ns: int) -> BenchmarkMapping:
        stock = _symbol(stock_symbol, "stock_symbol")
        if decision_time_ns <= 0:
            raise CanonicalMarketContextError("INVALID_DECISION_TIME")
        matches = [
            item
            for item in self.entries
            if _symbol(item.stock_symbol, "stock_symbol") == stock
            and item.effective_from_ns <= decision_time_ns
            and (item.effective_to_ns is None or decision_time_ns < item.effective_to_ns)
        ]
        if not matches:
            raise CanonicalMarketContextError(f"BENCHMARK_MAPPING_MISSING:{stock}")
        if len(matches) != 1:
            raise CanonicalMarketContextError(f"BENCHMARK_MAPPING_AMBIGUOUS:{stock}")
        return matches[0]


@dataclass(frozen=True, slots=True)
class ProviderFreshnessPolicy:
    provider_id: str
    provider_contract_version: str
    source_kind: Literal["INDEX", "SECTOR"]
    timeframe: str
    max_source_age_ns: int
    max_availability_lag_ns: int
    max_clock_skew_ns: int
    policy_version: str = PROVIDER_FRESHNESS_POLICY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PriceBasisLineage:
    basis: PriceBasis
    adjustment_policy_id: str
    adjustment_policy_version: str
    corporate_action_source_id: str | None
    corporate_action_snapshot_hash: str | None
    lineage_version: str = PRICE_BASIS_LINEAGE_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanonicalBenchmarkObservation:
    role: Literal["INDEX", "SECTOR"]
    source: ContextSourceObservation
    freshness_policy: ProviderFreshnessPolicy
    price_basis: PriceBasisLineage
    observation_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "source": self.source.as_dict(),
            "freshness_policy": self.freshness_policy.as_dict(),
            "price_basis": self.price_basis.as_dict(),
            "observation_hash": self.observation_hash,
        }


@dataclass(frozen=True, slots=True)
class CanonicalIndexSectorContext:
    d2_snapshot_hash: str
    decision_time_ns: int
    stock_symbol: str
    benchmark_mapping: BenchmarkMapping
    index: CanonicalBenchmarkObservation | None
    sector: CanonicalBenchmarkObservation | None
    availability: ContextAvailability
    relation: ContextRelation
    contradictions: tuple[str, ...]
    reason_codes: tuple[str, ...]
    upstream_hashes: tuple[str, ...]
    output_hash: str
    calculation_version: str = CANONICAL_MARKET_CONTEXT_VERSION
    used_for_probability: bool = False
    may_propose: bool = False
    may_veto: bool = False
    may_downgrade: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "calculation_version": self.calculation_version,
            "d2_snapshot_hash": self.d2_snapshot_hash,
            "decision_time_ns": self.decision_time_ns,
            "stock_symbol": self.stock_symbol,
            "benchmark_mapping": self.benchmark_mapping.as_dict(),
            "index": self.index.as_dict() if self.index else None,
            "sector": self.sector.as_dict() if self.sector else None,
            "availability": self.availability,
            "relation": self.relation,
            "contradictions": list(self.contradictions),
            "reason_codes": list(self.reason_codes),
            "upstream_hashes": list(self.upstream_hashes),
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
        }


def build_benchmark_registry(entries: Sequence[BenchmarkMapping]) -> BenchmarkRegistry:
    if isinstance(entries, (str, bytes)):
        raise CanonicalMarketContextError("INVALID_BENCHMARK_COLLECTION")
    normalized = tuple(sorted(entries, key=lambda x: (_symbol(x.stock_symbol, "stock_symbol"), x.effective_from_ns)))
    seen: dict[str, list[BenchmarkMapping]] = {}
    for item in normalized:
        _validate_mapping(item)
        seen.setdefault(_symbol(item.stock_symbol, "stock_symbol"), []).append(item)
    for stock, mappings in seen.items():
        for previous, current in zip(mappings, mappings[1:]):
            previous_end = previous.effective_to_ns
            if previous_end is None or current.effective_from_ns < previous_end:
                raise CanonicalMarketContextError(f"BENCHMARK_MAPPING_OVERLAP:{stock}")
    return BenchmarkRegistry(entries=normalized)


def evaluate_freshness(
    *,
    source: ContextSourceObservation,
    policy: ProviderFreshnessPolicy,
) -> tuple[ContextAvailability, tuple[str, ...]]:
    _validate_policy(policy)
    if source.source_kind != policy.source_kind:
        raise CanonicalMarketContextError(f"FRESHNESS_POLICY_KIND_MISMATCH:{source.source_id}")
    if source.provider_id != policy.provider_id or source.provider_contract_version != policy.provider_contract_version:
        raise CanonicalMarketContextError(f"FRESHNESS_POLICY_PROVIDER_MISMATCH:{source.source_id}")
    if source.source_timeframe != policy.timeframe:
        raise CanonicalMarketContextError(f"FRESHNESS_POLICY_TIMEFRAME_MISMATCH:{source.source_id}")
    if source.availability not in {"AVAILABLE", "DEGRADED"}:
        return source.availability, tuple(sorted(set(source.reason_codes)))
    if source.source_bar_close_time_ns is None or source.available_at_ns is None:
        raise CanonicalMarketContextError(f"FRESHNESS_SOURCE_TIME_MISSING:{source.source_id}")

    reasons: list[str] = []
    source_age = source.d2_decision_time_ns - source.source_bar_close_time_ns
    availability_lag = source.available_at_ns - source.source_bar_close_time_ns
    if source_age > policy.max_source_age_ns:
        reasons.append("SOURCE_STALE_BY_POLICY")
    if availability_lag < 0 or availability_lag > policy.max_availability_lag_ns:
        reasons.append("SOURCE_AVAILABILITY_LAG_EXCEEDED")
    if source.clock_skew_state == "SKEWED":
        reasons.append("SOURCE_CLOCK_SKEWED")
    elif source.clock_skew_state == "UNKNOWN":
        reasons.append("SOURCE_CLOCK_SKEW_UNKNOWN")
    if source.freshness_state == "STALE":
        reasons.append("SOURCE_MARKED_STALE")
    elif source.freshness_state == "UNKNOWN":
        reasons.append("SOURCE_FRESHNESS_UNKNOWN")
    return ("DEGRADED" if reasons else source.availability), tuple(sorted(set((*source.reason_codes, *reasons))))


def build_benchmark_observation(
    *,
    role: Literal["INDEX", "SECTOR"],
    source: ContextSourceObservation,
    policy: ProviderFreshnessPolicy,
    price_basis: PriceBasisLineage,
) -> CanonicalBenchmarkObservation:
    if source.source_kind != role:
        raise CanonicalMarketContextError(f"BENCHMARK_ROLE_MISMATCH:{source.source_id}")
    _validate_price_basis(price_basis)
    evaluated, reasons = evaluate_freshness(source=source, policy=policy)
    if evaluated != source.availability or reasons != tuple(sorted(set(source.reason_codes))):
        source = ContextSourceObservation(**{
            **source.as_dict(),
            "availability": evaluated,
            "reason_codes": reasons,
        })
    seed = {
        "version": CANONICAL_MARKET_CONTEXT_VERSION,
        "role": role,
        "source": _source_identity(source),
        "freshness_policy": policy.as_dict(),
        "price_basis": price_basis.as_dict(),
    }
    return CanonicalBenchmarkObservation(
        role=role,
        source=source,
        freshness_policy=policy,
        price_basis=price_basis,
        observation_hash=_stable_hash(seed),
    )


def build_canonical_index_sector_context(
    *,
    d2_snapshot_hash: str,
    decision_time_ns: int,
    stock_symbol: str,
    registry: BenchmarkRegistry,
    index: CanonicalBenchmarkObservation | None,
    sector: CanonicalBenchmarkObservation | None,
) -> CanonicalIndexSectorContext:
    _require_hash(d2_snapshot_hash, "d2_snapshot_hash")
    mapping = registry.resolve(stock_symbol=stock_symbol, decision_time_ns=decision_time_ns)
    stock = _symbol(stock_symbol, "stock_symbol")
    reasons: list[str] = []
    contradictions: list[str] = []

    for role, observation, expected in (
        ("INDEX", index, mapping.broad_index_symbol),
        ("SECTOR", sector, mapping.sector_symbol),
    ):
        if observation is None:
            reasons.append(f"{role}_OBSERVATION_MISSING")
            continue
        if observation.role != role:
            raise CanonicalMarketContextError(f"{role}_ROLE_MISMATCH")
        if observation.source.d2_decision_time_ns != decision_time_ns:
            raise CanonicalMarketContextError(f"{role}_DECISION_TIME_MISMATCH")
        if _symbol(observation.source.symbol_or_universe, "symbol_or_universe") != _symbol(expected, "benchmark_symbol"):
            raise CanonicalMarketContextError(f"{role}_BENCHMARK_IDENTITY_MISMATCH")
        if observation.source.availability != "AVAILABLE":
            reasons.append(f"{role}_{observation.source.availability}")

    if index is None and sector is None:
        availability: ContextAvailability = "UNAVAILABLE"
        relation: ContextRelation = "UNKNOWN"
    elif index is None or sector is None:
        availability = "DEGRADED"
        relation = "PARTIAL"
    elif index.source.availability == "AVAILABLE" and sector.source.availability == "AVAILABLE":
        availability = "AVAILABLE"
        relation = "ALIGNED"
        if index.price_basis.basis != sector.price_basis.basis:
            contradictions.append("INDEX_SECTOR_PRICE_BASIS_MISMATCH")
            relation = "CONTRADICTORY"
            availability = "DEGRADED"
    else:
        availability = "DEGRADED"
        relation = "PARTIAL"

    if index and sector and index.source.source_snapshot_hash == sector.source.source_snapshot_hash:
        contradictions.append("INDEX_SECTOR_SOURCE_HASH_COLLISION")
        relation = "CONTRADICTORY"
        availability = "DEGRADED"

    upstream = tuple(sorted({
        item
        for item in (
            mapping.lineage_hash,
            index.observation_hash if index else None,
            sector.observation_hash if sector else None,
        )
        if item is not None
    }))
    seed = {
        "version": CANONICAL_MARKET_CONTEXT_VERSION,
        "d2_snapshot_hash": d2_snapshot_hash.lower(),
        "decision_time_ns": decision_time_ns,
        "stock_symbol": stock,
        "mapping": mapping.as_dict(),
        "index_hash": index.observation_hash if index else None,
        "sector_hash": sector.observation_hash if sector else None,
        "availability": availability,
        "relation": relation,
        "contradictions": sorted(set(contradictions)),
        "reason_codes": sorted(set(reasons)),
        "upstream_hashes": upstream,
    }
    result = CanonicalIndexSectorContext(
        d2_snapshot_hash=d2_snapshot_hash.lower(),
        decision_time_ns=decision_time_ns,
        stock_symbol=stock,
        benchmark_mapping=mapping,
        index=index,
        sector=sector,
        availability=availability,
        relation=relation,
        contradictions=tuple(sorted(set(contradictions))),
        reason_codes=tuple(sorted(set(reasons))),
        upstream_hashes=upstream,
        output_hash=_stable_hash(seed),
    )
    if len(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")) > MAX_MARKET_CONTEXT_BYTES:
        raise CanonicalMarketContextError("BOUNDED_MARKET_CONTEXT_EXCEEDED")
    return result


def _validate_mapping(item: BenchmarkMapping) -> None:
    _symbol(item.stock_symbol, "stock_symbol")
    _symbol(item.sector_symbol, "sector_symbol")
    _symbol(item.broad_index_symbol, "broad_index_symbol")
    if item.effective_from_ns <= 0:
        raise CanonicalMarketContextError("INVALID_MAPPING_EFFECTIVE_FROM")
    if item.effective_to_ns is not None and item.effective_to_ns <= item.effective_from_ns:
        raise CanonicalMarketContextError("INVALID_MAPPING_EFFECTIVE_RANGE")
    if not item.mapping_source.strip() or not item.mapping_version.strip():
        raise CanonicalMarketContextError("MAPPING_LINEAGE_MISSING")
    _require_hash(item.lineage_hash, "mapping.lineage_hash")


def _validate_policy(policy: ProviderFreshnessPolicy) -> None:
    if not policy.provider_id.strip() or not policy.provider_contract_version.strip() or not policy.timeframe.strip():
        raise CanonicalMarketContextError("FRESHNESS_POLICY_IDENTITY_MISSING")
    if policy.source_kind not in {"INDEX", "SECTOR"}:
        raise CanonicalMarketContextError("INVALID_FRESHNESS_POLICY_KIND")
    for name, value in (
        ("max_source_age_ns", policy.max_source_age_ns),
        ("max_availability_lag_ns", policy.max_availability_lag_ns),
        ("max_clock_skew_ns", policy.max_clock_skew_ns),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CanonicalMarketContextError(f"INVALID_{name.upper()}")


def _validate_price_basis(lineage: PriceBasisLineage) -> None:
    if lineage.basis not in {"RAW", "SPLIT_ADJUSTED", "TOTAL_RETURN_ADJUSTED", "UNKNOWN"}:
        raise CanonicalMarketContextError("INVALID_PRICE_BASIS")
    if not lineage.adjustment_policy_id.strip() or not lineage.adjustment_policy_version.strip():
        raise CanonicalMarketContextError("PRICE_BASIS_POLICY_MISSING")
    if lineage.corporate_action_snapshot_hash is not None:
        _require_hash(lineage.corporate_action_snapshot_hash, "corporate_action_snapshot_hash")
    if lineage.basis != "RAW" and lineage.basis != "UNKNOWN":
        if not lineage.corporate_action_source_id or not lineage.corporate_action_snapshot_hash:
            raise CanonicalMarketContextError("ADJUSTED_BASIS_LINEAGE_UNPROVEN")


def _source_identity(source: ContextSourceObservation) -> dict[str, Any]:
    payload = source.as_dict()
    payload["reason_codes"] = sorted(set(payload["reason_codes"]))
    return payload


def _symbol(value: str, field: str) -> str:
    normalized = str(value).strip().upper()
    if not normalized:
        raise CanonicalMarketContextError(f"EMPTY_{field.upper()}")
    if len(normalized) > 160:
        raise CanonicalMarketContextError(f"{field.upper()}_TOO_LONG")
    return normalized


def _require_hash(value: str, field: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise CanonicalMarketContextError(f"INVALID_SHA256:{field}")
    return normalized


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
