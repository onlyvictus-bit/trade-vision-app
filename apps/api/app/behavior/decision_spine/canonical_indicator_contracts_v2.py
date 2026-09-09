from __future__ import annotations

"""M3.1.1-F canonical indicator contracts + dependency DAG.

This module does not create a second indicator registry. ``indicator_registry``
remains the metadata authority. The v2 layer projects that locked registry into a
bounded dependency graph so shared transforms/correlation can be reasoned about
without pretending that 94 registered outputs are 94 independent observations.

It is a SHADOW / ZERO-AUTHORITY sensory contract. It never votes, predicts,
sets D6 bands, or executes.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

from ..indicator_registry import REGISTRY_VERSION, build_indicator_registry_report
from ..real_indicator_adapter import REAL_RUNTIME_PROMOTED_INDICATORS


CANONICAL_INDICATOR_CONTRACTS_V2_VERSION = "canonical-indicator-contracts.v2"
LOCKED_OUTPUT_COUNT = 94


class CanonicalIndicatorContractsV2Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IndicatorContractNodeV2:
    indicator_id: str
    registry_status: str
    registry_source: str
    family: str
    category: str
    formula_hash: str
    implementation_version: str
    warmup_bars: int
    lookback_bars: int
    confirmation_delay_bars: int
    input_columns: tuple[str, ...]
    output_columns: tuple[str, ...]
    closed_bar_only: bool
    point_in_time_safe: bool
    uses_future_pivots: bool
    pit_audit_state: str
    canonical_runtime_supported: bool
    canonicalized: bool
    availability: str
    dependency_roots: tuple[str, ...]
    dependency_ancestry: tuple[str, ...]
    correlation_families: tuple[str, ...]
    independence_family_key: str
    d6_eligible: bool = False
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False


@dataclass(frozen=True, slots=True)
class DependencyEdgeV2:
    parent: str
    child: str
    relation: str


@dataclass(frozen=True, slots=True)
class CanonicalIndicatorContractsV2:
    calculation_version: str
    registry_version: str
    registered_output_count: int
    nodes: tuple[IndicatorContractNodeV2, ...]
    edges: tuple[DependencyEdgeV2, ...]
    independent_family_keys: tuple[str, ...]
    unavailable_indicator_ids: tuple[str, ...]
    proxy_indicator_ids: tuple[str, ...]
    blocked_indicator_ids: tuple[str, ...]
    noncanonical_pta_indicator_ids: tuple[str, ...]
    dag_hash: str
    epistemic_level: str = "DERIVED"
    research_only: bool = True
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False
    trade_allowed: bool = False
    order_routing_enabled: bool = False
    live_trading_blocked: bool = True
    human_approval_required: bool = True

    def node(self, indicator_id: str) -> IndicatorContractNodeV2:
        for item in self.nodes:
            if item.indicator_id == indicator_id:
                return item
        raise KeyError(indicator_id)

    def bounded_summary(self) -> dict[str, object]:
        return {
            "calculation_version": self.calculation_version,
            "registry_version": self.registry_version,
            "registered_output_count": self.registered_output_count,
            "canonical_runtime_supported_count": sum(n.canonical_runtime_supported for n in self.nodes),
            "canonicalized_count": sum(n.canonicalized for n in self.nodes),
            "independent_family_count": len(self.independent_family_keys),
            "raw_indicator_count_is_independent_count": False,
            "proxy_count": len(self.proxy_indicator_ids),
            "blocked_count": len(self.blocked_indicator_ids),
            "pta_noncanonical_count": len(self.noncanonical_pta_indicator_ids),
            "dag_hash": self.dag_hash,
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


def build_canonical_indicator_contracts_v2() -> CanonicalIndicatorContractsV2:
    report = build_indicator_registry_report()
    if report.registry_version != REGISTRY_VERSION:
        raise CanonicalIndicatorContractsV2Error("indicator registry version mismatch")
    if report.total_output_groups != LOCKED_OUTPUT_COUNT or len(report.entries) != LOCKED_OUTPUT_COUNT:
        raise CanonicalIndicatorContractsV2Error(
            f"locked indicator registry coverage changed: expected {LOCKED_OUTPUT_COUNT}, "
            f"got {report.total_output_groups}/{len(report.entries)}"
        )

    nodes: list[IndicatorContractNodeV2] = []
    edges: set[DependencyEdgeV2] = set()
    proxy: list[str] = []
    blocked: list[str] = []
    pta: list[str] = []
    unavailable: list[str] = []

    # Shared primitive ancestry is explicit. These are dependency identities,
    # not newly calculated values and therefore do not violate calculate-once.
    shared_edges = (
        DependencyEdgeV2("RAW:OHLC", "DERIVED:PRICE_GEOMETRY", "DERIVES"),
        DependencyEdgeV2("RAW:OHLC", "DERIVED:EMA", "DERIVES"),
        DependencyEdgeV2("RAW:OHLC", "DERIVED:RSI", "DERIVES"),
        DependencyEdgeV2("RAW:OHLC", "DERIVED:TRUE_RANGE", "DERIVES"),
        DependencyEdgeV2("DERIVED:TRUE_RANGE", "DERIVED:ATR", "DERIVES"),
        DependencyEdgeV2("RAW:OHLC", "DERIVED:VOLATILITY", "DERIVES"),
        DependencyEdgeV2("RAW:OHLC", "DERIVED:LEVEL_GEOMETRY", "DERIVES"),
        DependencyEdgeV2("RAW:OHLC", "DERIVED:VWAP", "DERIVES"),
        DependencyEdgeV2("RAW:VOLUME", "DERIVED:VWAP", "DERIVES"),
        DependencyEdgeV2("RAW:VOLUME", "DERIVED:VOLUME_FLOW", "DERIVES"),
    )
    edges.update(shared_edges)

    for entry in sorted(report.entries, key=lambda item: item.indicator_id):
        roots, ancestry, correlations = _dependency_contract(entry)
        runtime_supported = (
            entry.source == "self_indc"
            and entry.indicator_id in REAL_RUNTIME_PROMOTED_INDICATORS
            and entry.status == "validated"
        )
        canonicalized = runtime_supported and bool(entry.point_in_time_safe) and bool(entry.closed_bar_only)
        if entry.status == "proxy":
            proxy.append(entry.indicator_id)
        if entry.status == "blocked":
            blocked.append(entry.indicator_id)
        if entry.source == "pta_signal_markers":
            pta.append(entry.indicator_id)
        if not canonicalized:
            unavailable.append(entry.indicator_id)

        family_key = _independence_family_key(entry.family, roots, correlations)
        node = IndicatorContractNodeV2(
            indicator_id=entry.indicator_id,
            registry_status=entry.status,
            registry_source=entry.source,
            family=entry.family,
            category=entry.category,
            formula_hash=entry.formula_hash,
            implementation_version=entry.implementation_version,
            warmup_bars=int(entry.warmup_bars_exact),
            lookback_bars=int(entry.lookback_bars),
            confirmation_delay_bars=int(entry.confirmation_delay_bars),
            input_columns=tuple(str(x).lower() for x in entry.input_columns),
            output_columns=tuple(str(x) for x in entry.output_columns),
            closed_bar_only=bool(entry.closed_bar_only),
            point_in_time_safe=bool(entry.point_in_time_safe),
            uses_future_pivots=bool(entry.uses_future_pivots),
            pit_audit_state=str(entry.internal_lookahead_audit_result),
            canonical_runtime_supported=runtime_supported,
            canonicalized=canonicalized,
            availability="AVAILABLE" if canonicalized else _availability(entry),
            dependency_roots=roots,
            dependency_ancestry=ancestry,
            correlation_families=correlations,
            independence_family_key=family_key,
        )
        nodes.append(node)
        for ancestor in ancestry:
            edges.add(DependencyEdgeV2(ancestor, f"INDICATOR:{entry.indicator_id}", "UPSTREAM"))

    ordered_edges = tuple(sorted(edges, key=lambda e: (e.parent, e.child, e.relation)))
    validate_indicator_dependency_dag(ordered_edges)
    independent = tuple(sorted({n.independence_family_key for n in nodes if n.canonicalized}))
    deterministic = {
        "version": CANONICAL_INDICATOR_CONTRACTS_V2_VERSION,
        "registry_version": report.registry_version,
        "nodes": [
            {
                "id": n.indicator_id,
                "status": n.registry_status,
                "source": n.registry_source,
                "family": n.family,
                "formula_hash": n.formula_hash,
                "implementation_version": n.implementation_version,
                "warmup": n.warmup_bars,
                "lookback": n.lookback_bars,
                "delay": n.confirmation_delay_bars,
                "pit": [n.closed_bar_only, n.point_in_time_safe, n.uses_future_pivots, n.pit_audit_state],
                "canonicalized": n.canonicalized,
                "roots": n.dependency_roots,
                "ancestry": n.dependency_ancestry,
                "correlation": n.correlation_families,
                "independence": n.independence_family_key,
            }
            for n in nodes
        ],
        "edges": [(e.parent, e.child, e.relation) for e in ordered_edges],
        "independent": independent,
    }
    return CanonicalIndicatorContractsV2(
        calculation_version=CANONICAL_INDICATOR_CONTRACTS_V2_VERSION,
        registry_version=report.registry_version,
        registered_output_count=len(nodes),
        nodes=tuple(nodes),
        edges=ordered_edges,
        independent_family_keys=independent,
        unavailable_indicator_ids=tuple(sorted(unavailable)),
        proxy_indicator_ids=tuple(sorted(proxy)),
        blocked_indicator_ids=tuple(sorted(blocked)),
        noncanonical_pta_indicator_ids=tuple(sorted(pta)),
        dag_hash=_stable_hash(deterministic),
    )


def validate_indicator_dependency_dag(edges: Iterable[DependencyEdgeV2]) -> None:
    adjacency: dict[str, set[str]] = {}
    nodes: set[str] = set()
    for edge in edges:
        if not edge.parent or not edge.child or edge.parent == edge.child:
            raise CanonicalIndicatorContractsV2Error("invalid dependency edge")
        adjacency.setdefault(edge.parent, set()).add(edge.child)
        nodes.add(edge.parent)
        nodes.add(edge.child)
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node: str) -> None:
        if node in permanent:
            return
        if node in temporary:
            raise CanonicalIndicatorContractsV2Error("cycle detected in indicator dependency DAG")
        temporary.add(node)
        for child in adjacency.get(node, ()):
            visit(child)
        temporary.remove(node)
        permanent.add(node)

    for node in sorted(nodes):
        visit(node)


def _dependency_contract(entry) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    iid = entry.indicator_id.lower()
    family = str(entry.family).lower()
    inputs = {str(x).lower() for x in entry.input_columns}
    roots: set[str] = {"RAW:OHLC"} if inputs & {"open", "high", "low", "close"} else set()
    if "volume" in inputs:
        roots.add("RAW:VOLUME")

    ancestry: set[str] = set()
    correlation: set[str] = {f"REGISTRY_FAMILY:{family}"}
    price_structure_tokens = ("bos", "choch", "fvg", "ob", "swing", "pivot", "cpr", "fib", "fractal", "inside", "outside", "trendln", "sfp", "nbar")
    if any(token in iid for token in price_structure_tokens) or family in {"market_structure", "support_resistance", "candlestick", "breakout_retest"}:
        ancestry.add("DERIVED:PRICE_GEOMETRY")
        correlation.add("PRICE_STRUCTURE")
    if any(token in iid for token in ("ema", "macd", "dual_ma", "trend_sig", "ichi")) or family == "trend":
        ancestry.add("DERIVED:EMA")
        correlation.add("MOVING_AVERAGE_TREND")
    if "rsi" in iid or family == "momentum":
        ancestry.add("DERIVED:RSI")
        correlation.add("MOMENTUM_OSCILLATOR")
    if any(token in iid for token in ("atr", "super", "fvg", "ob", "range", "bb", "kc")) or family == "volatility":
        ancestry.add("DERIVED:ATR")
        correlation.add("RANGE_VOLATILITY")
    if "vwap" in iid or family == "vwap_value_area":
        ancestry.add("DERIVED:VWAP")
        correlation.add("VWAP_FAMILY")
    if "volume" in inputs or family in {"volume_participation", "liquidity_order_flow_proxy"}:
        ancestry.add("DERIVED:VOLUME_FLOW")
        correlation.add("VOLUME_PARTICIPATION")
    if family == "statistical_distribution" or any(token in iid for token in ("chop", "vol")):
        ancestry.add("DERIVED:VOLATILITY")
        correlation.add("STATISTICAL_VOLATILITY")
    if family == "support_resistance" or any(token in iid for token in ("pivot", "cpr", "fib")):
        ancestry.add("DERIVED:LEVEL_GEOMETRY")
        correlation.add("LEVEL_GEOMETRY")
    if not ancestry and "RAW:OHLC" in roots:
        ancestry.add("DERIVED:PRICE_GEOMETRY")
        correlation.add("PRICE_PATH")
    if "RAW:VOLUME" in roots and not any(x in ancestry for x in ("DERIVED:VWAP", "DERIVED:VOLUME_FLOW")):
        ancestry.add("DERIVED:VOLUME_FLOW")
        correlation.add("VOLUME_PARTICIPATION")
    return tuple(sorted(roots)), tuple(sorted(ancestry)), tuple(sorted(correlation))


def _independence_family_key(family: str, roots: tuple[str, ...], correlations: tuple[str, ...]) -> str:
    payload = {"family": str(family), "roots": roots, "correlations": correlations}
    return f"family:{str(family).lower()}:{_stable_hash(payload)[:12]}"


def _availability(entry) -> str:
    if entry.status == "blocked":
        return "BLOCKED"
    if entry.status == "proxy":
        return "NONCANONICAL_PROXY"
    if entry.source == "pta_signal_markers":
        return "NONCANONICAL_PTA"
    if not entry.point_in_time_safe or not entry.closed_bar_only:
        return "PIT_UNVERIFIED"
    return "RUNTIME_UNAVAILABLE"


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
