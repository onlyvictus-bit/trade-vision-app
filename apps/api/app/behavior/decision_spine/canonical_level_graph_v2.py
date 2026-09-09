from __future__ import annotations

"""M3.1.1-E zero-authority canonical level graph.

Consumes the locked canonical M3.1-C level result plus the exact causal primitive
and feature kernels. It never recomputes VWAP, opening ranges, prior-session
levels or CPR. Static level interactions are measured from already-observed bars;
dynamic levels (VWAP/bands) deliberately do not receive fabricated historical
touch counts because their value changes through time.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

from .canonical_level_intelligence import CanonicalLevelIntelligenceResult
from .market_primitive_kernel_v2 import MarketPrimitiveKernelV2
from .snapshot_feature_kernel import SnapshotFeatureKernel


CANONICAL_LEVEL_GRAPH_V2_VERSION = "canonical-level-graph.v2"
DEFAULT_ATR_PERIOD = 14
DEFAULT_ATR_TOLERANCE = 0.10
DEFAULT_NOISE_TOLERANCE = 1.50


class CanonicalLevelGraphV2Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LevelGraphNodeV2:
    node_id: str
    source: str
    source_family: str
    correlation_group: str
    price: float
    zone_low: float
    zone_high: float
    created_at_ns: int
    timeframe: str
    hierarchy: str
    dynamic: bool
    availability: str
    freshness: str
    age_bars: int | None
    touch_count: int | None
    rejection_count: int | None
    break_count: int | None
    reclaim_count: int | None
    role_flip: bool | None
    lifecycle: str
    distance_bps: float
    distance_atr: float | None
    distance_ticks: float | None
    directional_support: str
    directional_conflict: str
    quality: str
    source_snapshot_hash: str
    source_level_hash: str


@dataclass(frozen=True, slots=True)
class LevelClusterV2:
    cluster_id: str
    zone_low: float
    zone_high: float
    center: float
    node_ids: tuple[str, ...]
    source_families: tuple[str, ...]
    correlation_groups: tuple[str, ...]
    independent_family_count: int
    raw_node_count: int
    tolerance_price: float


@dataclass(frozen=True, slots=True)
class CanonicalLevelGraphV2:
    calculation_version: str
    symbol: str
    timeframe: str
    decision_time_ns: int
    source_snapshot_hash: str
    source_feature_kernel_hash: str
    source_primitive_hash: str
    source_level_hash: str
    latest_close: float
    tolerance_price: float
    tolerance_sources: tuple[str, ...]
    tick_size: float | None
    spread: float | None
    nodes: tuple[LevelGraphNodeV2, ...]
    clusters: tuple[LevelClusterV2, ...]
    unavailable_sources: tuple[str, ...]
    graph_hash: str
    epistemic_level: str = "DERIVED"
    research_only: bool = True
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    human_approval_required: bool = True

    def receipt_summary(self) -> dict[str, object]:
        return {
            "calculation_version": self.calculation_version,
            "latest_close": self.latest_close,
            "node_count": len(self.nodes),
            "cluster_count": len(self.clusters),
            "unavailable_sources": list(self.unavailable_sources),
            "tolerance": {
                "price": self.tolerance_price,
                "sources": list(self.tolerance_sources),
                "tick_size": self.tick_size,
                "spread": self.spread,
                "invented_tick_or_spread": False,
            },
            "provenance": {
                "snapshot_hash": self.source_snapshot_hash,
                "feature_kernel_hash": self.source_feature_kernel_hash,
                "primitive_hash": self.source_primitive_hash,
                "level_hash": self.source_level_hash,
                "graph_hash": self.graph_hash,
            },
            "quality": {
                "dynamic_level_interaction_counts_fabricated": False,
                "clusters_use_independent_source_families": True,
                "missing_is_neutral": False,
            },
            "authority": {
                "research_only": True,
                "used_for_probability": False,
                "may_set_final_band": False,
                "may_execute": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
                "human_approval_required": True,
            },
        }


def build_canonical_level_graph_v2(
    levels: CanonicalLevelIntelligenceResult,
    primitive: MarketPrimitiveKernelV2,
    observed: SnapshotFeatureKernel,
    *,
    tick_size: float | None = None,
    spread: float | None = None,
    atr_period: int = DEFAULT_ATR_PERIOD,
) -> CanonicalLevelGraphV2:
    _validate(levels, primitive, observed, tick_size=tick_size, spread=spread, atr_period=atr_period)
    latest_close = float(observed.vectors.closes[-1])
    atr = primitive.wilder_atr(atr_period).latest
    noise = primitive.realized_volatility(20).latest
    tolerance_price, tolerance_sources = _tolerance(
        latest_close, atr=atr, noise_per_bar=noise, tick_size=tick_size, spread=spread
    )

    specs, unavailable = _canonical_specs(levels)
    nodes: list[LevelGraphNodeV2] = []
    for spec in specs:
        nodes.append(
            _node(
                spec=spec,
                levels=levels,
                observed=observed,
                latest_close=latest_close,
                atr=atr,
                tick_size=tick_size,
                tolerance=tolerance_price,
            )
        )
    clusters = _clusters(tuple(nodes), tolerance_price)
    payload = {
        "version": CANONICAL_LEVEL_GRAPH_V2_VERSION,
        "snapshot": primitive.source_snapshot_hash,
        "level_hash": levels.provenance.canonical_level_hash,
        "tolerance": tolerance_price,
        "tolerance_sources": tolerance_sources,
        "tick_size": tick_size,
        "spread": spread,
        "nodes": [
            {
                "id": n.node_id,
                "price": n.price,
                "zone": [n.zone_low, n.zone_high],
                "source": n.source,
                "family": n.source_family,
                "correlation": n.correlation_group,
                "lifecycle": n.lifecycle,
                "touch": n.touch_count,
                "reject": n.rejection_count,
                "break": n.break_count,
                "reclaim": n.reclaim_count,
                "role_flip": n.role_flip,
            }
            for n in nodes
        ],
        "clusters": [
            {
                "id": c.cluster_id,
                "nodes": c.node_ids,
                "families": c.source_families,
                "independent": c.independent_family_count,
            }
            for c in clusters
        ],
        "unavailable": sorted(unavailable),
    }
    digest = _hash(payload)
    return CanonicalLevelGraphV2(
        calculation_version=CANONICAL_LEVEL_GRAPH_V2_VERSION,
        symbol=primitive.identity.symbol,
        timeframe=primitive.identity.timeframe,
        decision_time_ns=primitive.identity.decision_time_ns,
        source_snapshot_hash=primitive.source_snapshot_hash,
        source_feature_kernel_hash=primitive.source_feature_kernel_hash,
        source_primitive_hash=primitive.primitive_hash,
        source_level_hash=levels.provenance.canonical_level_hash,
        latest_close=latest_close,
        tolerance_price=tolerance_price,
        tolerance_sources=tolerance_sources,
        tick_size=tick_size,
        spread=spread,
        nodes=tuple(nodes),
        clusters=clusters,
        unavailable_sources=tuple(sorted(unavailable)),
        graph_hash=digest,
    )


def _validate(levels, primitive, observed, *, tick_size, spread, atr_period):
    if primitive.source_snapshot_hash != observed.source_snapshot_hash:
        raise CanonicalLevelGraphV2Error("primitive/observed snapshot hash mismatch")
    if primitive.source_feature_kernel_hash != observed.feature_hash:
        raise CanonicalLevelGraphV2Error("primitive/observed feature hash mismatch")
    if levels.provenance.source_snapshot_hash != primitive.source_snapshot_hash:
        raise CanonicalLevelGraphV2Error("level/primitive snapshot hash mismatch")
    if levels.provenance.source_feature_kernel_hash != primitive.source_feature_kernel_hash:
        raise CanonicalLevelGraphV2Error("level/primitive feature hash mismatch")
    if levels.symbol != primitive.identity.symbol or levels.timeframe != primitive.identity.timeframe:
        raise CanonicalLevelGraphV2Error("level/primitive identity mismatch")
    if levels.latest_close is None:
        raise CanonicalLevelGraphV2Error("canonical levels require an observed latest close")
    if not isinstance(atr_period, int) or isinstance(atr_period, bool) or atr_period <= 0:
        raise CanonicalLevelGraphV2Error("atr_period must be a positive integer")
    try:
        primitive.wilder_atr(atr_period)
        primitive.realized_volatility(20)
    except ValueError as exc:
        raise CanonicalLevelGraphV2Error("required primitive series was not materialized") from exc
    for name, value in (("tick_size", tick_size), ("spread", spread)):
        if value is not None and (not math.isfinite(float(value)) or float(value) <= 0.0):
            raise CanonicalLevelGraphV2Error(f"{name} must be positive finite when supplied")


def _tolerance(price, *, atr, noise_per_bar, tick_size, spread):
    candidates: list[tuple[str, float]] = []
    if atr is not None and atr > 0:
        candidates.append(("WILDER_ATR", DEFAULT_ATR_TOLERANCE * float(atr)))
    if noise_per_bar is not None and noise_per_bar > 0:
        candidates.append(("REALIZED_NOISE", DEFAULT_NOISE_TOLERANCE * float(noise_per_bar) * price))
    if tick_size is not None:
        candidates.append(("TICK_SIZE", 2.0 * float(tick_size)))
    if spread is not None:
        candidates.append(("SPREAD", 1.5 * float(spread)))
    if not candidates:
        # Price bps is not an invented market microstructure input; it is a
        # deterministic fallback geometry tolerance and is labeled explicitly.
        candidates.append(("PRICE_BPS_FALLBACK", price * 0.0005))
    maximum = max(value for _, value in candidates)
    sources = tuple(name for name, value in candidates if value == maximum)
    return maximum, sources


def _canonical_specs(levels):
    specs: list[dict[str, object]] = []
    unavailable: set[str] = set()
    v = levels.session_vwap
    if v.status == "AVAILABLE" and v.value is not None:
        for source, value in (
            ("SESSION_VWAP", v.value),
            ("VWAP_BAND_1_UPPER", v.band_1_upper), ("VWAP_BAND_1_LOWER", v.band_1_lower),
            ("VWAP_BAND_2_UPPER", v.band_2_upper), ("VWAP_BAND_2_LOWER", v.band_2_lower),
            ("VWAP_BAND_3_UPPER", v.band_3_upper), ("VWAP_BAND_3_LOWER", v.band_3_lower),
        ):
            if value is not None:
                specs.append(_spec(source, value, "VWAP", "VWAP_DERIVATIVES", levels.session.open_time_ns, "SESSION", True))
    else:
        unavailable.add("VWAP")

    for opening in levels.opening_ranges:
        family = opening.name
        if opening.status == "AVAILABLE" and opening.high is not None and opening.low is not None:
            specs.append(_spec(f"{opening.name}_HIGH", opening.high, family, family, opening.window_end_ns, "INTRADAY", False))
            specs.append(_spec(f"{opening.name}_LOW", opening.low, family, family, opening.window_end_ns, "INTRADAY", False))
        else:
            unavailable.add(opening.name)

    ps = levels.previous_session
    if ps.status == "AVAILABLE":
        created = ps.last_bar_timestamp_ns or levels.session.open_time_ns
        for source, value in (("PDH", ps.high), ("PDL", ps.low), ("PDC", ps.close)):
            if value is not None:
                specs.append(_spec(source, value, "PREVIOUS_SESSION", "PREVIOUS_SESSION", created, "SESSION", False))
    else:
        unavailable.add("PREVIOUS_SESSION")

    cpr = levels.cpr
    if cpr.status == "AVAILABLE":
        for source, value in (("CPR_PIVOT", cpr.pivot), ("CPR_BC", cpr.bc), ("CPR_TC", cpr.tc)):
            if value is not None:
                specs.append(_spec(source, value, "CPR", "CPR", levels.session.open_time_ns, "SESSION", False))
    else:
        unavailable.add("CPR")
    return specs, unavailable


def _spec(source, price, family, correlation, created, hierarchy, dynamic):
    return {"source": source, "price": float(price), "family": family, "correlation": correlation,
            "created": int(created), "hierarchy": hierarchy, "dynamic": bool(dynamic)}


def _node(*, spec, levels, observed, latest_close, atr, tick_size, tolerance):
    price = float(spec["price"])
    dynamic = bool(spec["dynamic"])
    zone_low, zone_high = price - tolerance, price + tolerance
    created = int(spec["created"])
    start = 0
    while start < observed.closed_bar_count and observed.vectors.timestamps_ns[start] < created:
        start += 1
    if dynamic:
        touch = reject = breaks = reclaims = None
        role_flip = None
        lifecycle = "FRESH"
        age = None
        freshness = "DYNAMIC_CURRENT_VALUE"
    else:
        touch, reject, breaks, reclaims = _interactions(observed, start, zone_low, zone_high)
        role_flip = breaks > 0 and reclaims > 0
        lifecycle = "BROKEN" if breaks and not reclaims else ("TOUCHED" if touch else "FRESH")
        age = max(0, observed.closed_bar_count - max(start, 0))
        freshness = "FRESH" if touch == 0 else "INTERACTED"
    distance = latest_close - price
    distance_bps = distance / price * 10_000.0
    distance_atr = None if atr is None or atr <= 0 else distance / atr
    distance_ticks = None if tick_size is None else distance / float(tick_size)
    if latest_close > zone_high:
        support, conflict = "LONG", "SHORT"
    elif latest_close < zone_low:
        support, conflict = "SHORT", "LONG"
    else:
        support = conflict = "CONFLICTED_AT_LEVEL"
    quality = "AVAILABLE_DYNAMIC" if dynamic else "AVAILABLE_STATIC"
    node_id = f"{str(spec['source']).lower()}:{price:.8f}"
    return LevelGraphNodeV2(
        node_id=node_id, source=str(spec["source"]), source_family=str(spec["family"]),
        correlation_group=str(spec["correlation"]), price=price, zone_low=zone_low, zone_high=zone_high,
        created_at_ns=created, timeframe=levels.timeframe, hierarchy=str(spec["hierarchy"]), dynamic=dynamic,
        availability="AVAILABLE", freshness=freshness, age_bars=age, touch_count=touch,
        rejection_count=reject, break_count=breaks, reclaim_count=reclaims, role_flip=role_flip,
        lifecycle=lifecycle, distance_bps=distance_bps, distance_atr=distance_atr,
        distance_ticks=distance_ticks, directional_support=support, directional_conflict=conflict,
        quality=quality, source_snapshot_hash=levels.provenance.source_snapshot_hash,
        source_level_hash=levels.provenance.canonical_level_hash,
    )


def _interactions(observed, start, zone_low, zone_high):
    touch = reject = breaks = reclaims = 0
    prior_side: int | None = None
    for i in range(max(0, start), observed.closed_bar_count):
        high, low, close = observed.vectors.highs[i], observed.vectors.lows[i], observed.vectors.closes[i]
        touched = high >= zone_low and low <= zone_high
        if touched:
            touch += 1
            if close > zone_high or close < zone_low:
                reject += 1
        side = 1 if close > zone_high else (-1 if close < zone_low else 0)
        if prior_side is not None and side and prior_side and side != prior_side:
            breaks += 1
        if prior_side is not None and side == prior_side and touched:
            reclaims += 1
        if side:
            prior_side = side
    return touch, reject, breaks, reclaims


def _clusters(nodes: tuple[LevelGraphNodeV2, ...], tolerance: float) -> tuple[LevelClusterV2, ...]:
    if not nodes:
        return ()
    ordered = sorted(nodes, key=lambda n: (n.price, n.node_id))
    groups: list[list[LevelGraphNodeV2]] = []
    current: list[LevelGraphNodeV2] = [ordered[0]]
    for node in ordered[1:]:
        center = sum(item.price for item in current) / len(current)
        if abs(node.price - center) <= tolerance:
            current.append(node)
        else:
            groups.append(current)
            current = [node]
    groups.append(current)
    out: list[LevelClusterV2] = []
    for index, group in enumerate(groups):
        families = tuple(sorted({n.source_family for n in group}))
        correlations = tuple(sorted({n.correlation_group for n in group}))
        low = min(n.zone_low for n in group); high = max(n.zone_high for n in group)
        node_ids = tuple(sorted(n.node_id for n in group))
        out.append(LevelClusterV2(
            cluster_id=f"cluster-{index:03d}", zone_low=low, zone_high=high,
            center=sum(n.price for n in group)/len(group), node_ids=node_ids,
            source_families=families, correlation_groups=correlations,
            independent_family_count=len(families), raw_node_count=len(group), tolerance_price=tolerance,
        ))
    return tuple(out)


def _hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
