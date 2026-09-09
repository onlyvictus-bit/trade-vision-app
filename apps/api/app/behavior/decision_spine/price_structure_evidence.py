from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence


PRICE_STRUCTURE_EVIDENCE_VERSION = "price-structure-evidence.v1"
PRICE_STRUCTURE_DAG_VERSION = "price-structure-dag.v1"
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")

Availability = Literal["AVAILABLE", "DEGRADED", "UNAVAILABLE", "SKIPPED", "ERROR"]
Agreement = Literal["ALIGNED", "CONFLICTING", "UNAVAILABLE"]


class PriceStructureEvidenceError(ValueError):
    """Raised when the M3.1 price-evidence DAG is not causally valid."""


@dataclass(frozen=True, slots=True)
class PriceEvidenceNode:
    node_id: str
    source_snapshot_hash: str
    output_hash: str
    dependencies: tuple[str, ...]
    availability: Availability
    observed_at_ns: int | None = None


@dataclass(frozen=True, slots=True)
class PriceStructureEvidence:
    source_snapshot_hash: str
    local: Mapping[str, Any]
    mtf: Mapping[str, Any]
    agreement: Mapping[str, Any]
    upstream: Mapping[str, Any]
    epistemic: Mapping[str, Any]
    dag: Mapping[str, Any]
    structure_hash: str
    calculation_version: str = PRICE_STRUCTURE_EVIDENCE_VERSION
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
            "source_snapshot_hash": self.source_snapshot_hash,
            "local": dict(self.local),
            "mtf": dict(self.mtf),
            "agreement": dict(self.agreement),
            "upstream": dict(self.upstream),
            "epistemic": dict(self.epistemic),
            "dag": dict(self.dag),
            "structure_hash": self.structure_hash,
            "may_propose": False,
            "may_veto": False,
            "may_downgrade": False,
            "may_set_final_band": False,
            "may_execute": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }


def build_price_structure_evidence(
    *,
    snapshot_hash: str,
    decision_time_ns: int,
    local_receipts: Mapping[str, Mapping[str, Any]],
    mtf_receipt: Mapping[str, Any] | None,
) -> PriceStructureEvidence:
    """Compose already-calculated price facts without creating new authority.

    ``local_receipts`` and ``mtf_receipt`` are bounded receipt summaries. No
    candle series, DataFrame, specialist execution, score calculation or D6
    decision occurs here. The composer preserves contradictions and validates
    the causal DAG before producing an immutable hashable world-state.
    """

    snapshot_hash = _require_hash(snapshot_hash, "snapshot_hash")
    if decision_time_ns <= 0:
        raise PriceStructureEvidenceError("decision_time_ns must be positive")

    required_local = ("CANDLE_ANATOMY", "LEVEL_CONTEXT", "MARKET_STRUCTURE_LIQUIDITY")
    local_hashes: dict[str, str] = {}
    local_statuses: dict[str, Availability] = {}
    local_summaries: dict[str, Mapping[str, Any]] = {}
    warnings: list[str] = []
    nodes: list[PriceEvidenceNode] = [
        PriceEvidenceNode(
            node_id="D2",
            source_snapshot_hash=snapshot_hash,
            output_hash=snapshot_hash,
            dependencies=(),
            availability="AVAILABLE",
        )
    ]

    for engine_id in required_local:
        receipt = local_receipts.get(engine_id)
        if receipt is None:
            raise PriceStructureEvidenceError(f"UNKNOWN_OR_MISSING_UPSTREAM:{engine_id}")
        receipt_snapshot = _require_hash(str(receipt.get("source_snapshot_hash", "")), f"{engine_id}.snapshot")
        if receipt_snapshot != snapshot_hash:
            raise PriceStructureEvidenceError(f"SNAPSHOT_MISMATCH:{engine_id}")
        output_hash = _require_hash(str(receipt.get("output_hash", "")), f"{engine_id}.output_hash")
        status = _availability_from_receipt(receipt)
        summary = receipt.get("output_summary")
        if not isinstance(summary, Mapping):
            raise PriceStructureEvidenceError(f"INVALID_SUMMARY:{engine_id}")
        local_hashes[engine_id] = output_hash
        local_statuses[engine_id] = status
        local_summaries[engine_id] = summary
        if status != "AVAILABLE":
            warnings.append(f"{engine_id} availability is {status}.")
        nodes.append(
            PriceEvidenceNode(
                node_id=engine_id,
                source_snapshot_hash=snapshot_hash,
                output_hash=output_hash,
                dependencies=("D2",),
                availability=status,
            )
        )

    local_payload = {
        "structure_hash": _stable_hash(
            {
                "version": PRICE_STRUCTURE_EVIDENCE_VERSION,
                "snapshot_hash": snapshot_hash,
                "upstream_hashes": dict(sorted(local_hashes.items())),
            }
        ),
        "availability": _combine_availability(local_statuses.values()),
        "candle": _bounded_local_candle(local_summaries["CANDLE_ANATOMY"]),
        "levels": _bounded_local_levels(local_summaries["LEVEL_CONTEXT"]),
        "market_structure": _bounded_market_structure(local_summaries["MARKET_STRUCTURE_LIQUIDITY"]),
    }
    nodes.append(
        PriceEvidenceNode(
            node_id="LOCAL_PRICE_WORLD",
            source_snapshot_hash=snapshot_hash,
            output_hash=str(local_payload["structure_hash"]),
            dependencies=required_local,
            availability=local_payload["availability"],  # type: ignore[arg-type]
        )
    )

    if mtf_receipt is None:
        mtf_payload: dict[str, Any] = {
            "mtf_hash": None,
            "availability": "UNAVAILABLE",
            "records": [],
            "reason": "MTF receipt is unavailable.",
        }
        warnings.append("MTF evidence is unavailable.")
    else:
        receipt_snapshot = _require_hash(str(mtf_receipt.get("source_snapshot_hash", "")), "MTF_CONFIRMATION.snapshot")
        if receipt_snapshot != snapshot_hash:
            raise PriceStructureEvidenceError("SNAPSHOT_MISMATCH:MTF_CONFIRMATION")
        mtf_summary = mtf_receipt.get("output_summary")
        if not isinstance(mtf_summary, Mapping):
            raise PriceStructureEvidenceError("INVALID_SUMMARY:MTF_CONFIRMATION")
        canonical_hash = mtf_summary.get("mtf_hash")
        if canonical_hash is None:
            mtf_payload = {
                "mtf_hash": None,
                "availability": "UNAVAILABLE",
                "records": [],
                "reason": "Canonical MTF hash is unavailable.",
            }
            warnings.append("Canonical MTF hash is unavailable.")
        else:
            canonical_hash = _require_hash(str(canonical_hash), "MTF_CONFIRMATION.mtf_hash")
            records = mtf_summary.get("records", [])
            if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
                raise PriceStructureEvidenceError("INVALID_MTF_RECORDS")
            bounded_records = [_bounded_mtf_record(item) for item in records if isinstance(item, Mapping)]
            if int((mtf_summary.get("calculation_audit") or {}).get("future_or_incomplete_bar_authority_count", 0)) != 0:
                raise PriceStructureEvidenceError("FUTURE_OR_INCOMPLETE_BAR_AUTHORITY")
            mtf_availability = str(mtf_summary.get("canonical_status", "UNAVAILABLE")).upper()
            if mtf_availability not in {"AVAILABLE", "DEGRADED", "UNAVAILABLE"}:
                mtf_availability = "UNAVAILABLE"
            mtf_payload = {
                "mtf_hash": canonical_hash,
                "availability": mtf_availability,
                "records": bounded_records,
            }
            nodes.append(
                PriceEvidenceNode(
                    node_id="MTF_PRICE_WORLD",
                    source_snapshot_hash=snapshot_hash,
                    output_hash=canonical_hash,
                    dependencies=("D2",),
                    availability=mtf_availability,  # type: ignore[arg-type]
                )
            )
            if mtf_availability != "AVAILABLE":
                warnings.append(f"MTF availability is {mtf_availability}.")

    agreement_payload = _agreement(local_payload, mtf_payload)
    fusion_availability = _combine_availability(
        [str(local_payload["availability"]), str(mtf_payload["availability"])]
    )
    fusion_seed = {
        "version": PRICE_STRUCTURE_EVIDENCE_VERSION,
        "snapshot_hash": snapshot_hash,
        "local_structure_hash": local_payload["structure_hash"],
        "mtf_hash": mtf_payload.get("mtf_hash"),
        "agreement": agreement_payload,
    }
    structure_hash = _stable_hash(fusion_seed)
    fusion_dependencies = ["LOCAL_PRICE_WORLD"]
    if mtf_payload.get("mtf_hash"):
        fusion_dependencies.append("MTF_PRICE_WORLD")
    nodes.append(
        PriceEvidenceNode(
            node_id="PRICE_STRUCTURE_EVIDENCE",
            source_snapshot_hash=snapshot_hash,
            output_hash=structure_hash,
            dependencies=tuple(fusion_dependencies),
            availability=fusion_availability,  # type: ignore[arg-type]
        )
    )

    dag = _validate_dag(nodes, snapshot_hash=snapshot_hash, decision_time_ns=decision_time_ns)
    completeness = round(
        sum(node.availability == "AVAILABLE" for node in nodes if node.node_id != "D2")
        / max(1, len([node for node in nodes if node.node_id != "D2"])),
        6,
    )
    epistemic = {
        "availability": fusion_availability,
        "quality": "GOOD" if fusion_availability == "AVAILABLE" else "WARN",
        "completeness": completeness,
        "freshness": "UNKNOWN",
        "warmup": "NOT_APPLICABLE",
        "sample_size": len(nodes) - 1,
        "warnings": sorted(set(warnings + [
            "Fusion is provenance-only and has zero decision authority.",
            "External feed freshness is not inferred from price evidence.",
        ])),
    }
    upstream = {
        "snapshot_hash": snapshot_hash,
        "local_output_hashes": dict(sorted(local_hashes.items())),
        "local_structure_hash": local_payload["structure_hash"],
        "mtf_hash": mtf_payload.get("mtf_hash"),
    }

    result = PriceStructureEvidence(
        source_snapshot_hash=snapshot_hash,
        local=local_payload,
        mtf=mtf_payload,
        agreement=agreement_payload,
        upstream=upstream,
        epistemic=epistemic,
        dag=dag,
        structure_hash=structure_hash,
    )
    encoded = json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > 24_000:
        raise PriceStructureEvidenceError("BOUNDED_CONTEXT_EXCEEDED")
    return result


def _validate_dag(
    nodes: Sequence[PriceEvidenceNode],
    *,
    snapshot_hash: str,
    decision_time_ns: int,
) -> dict[str, Any]:
    ids = [node.node_id for node in nodes]
    if len(ids) != len(set(ids)):
        raise PriceStructureEvidenceError("DUPLICATE_DAG_NODE")
    index = {node.node_id: node for node in nodes}
    for node in nodes:
        if node.source_snapshot_hash != snapshot_hash:
            raise PriceStructureEvidenceError(f"DAG_SNAPSHOT_MISMATCH:{node.node_id}")
        _require_hash(node.output_hash, f"DAG.{node.node_id}.output_hash")
        if node.observed_at_ns is not None and node.observed_at_ns > decision_time_ns:
            raise PriceStructureEvidenceError(f"FUTURE_DAG_NODE:{node.node_id}")
        for dependency in node.dependencies:
            if dependency not in index:
                raise PriceStructureEvidenceError(f"UNKNOWN_DAG_DEPENDENCY:{node.node_id}:{dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise PriceStructureEvidenceError(f"DAG_CYCLE:{node_id}")
        if node_id in visited:
            return
        visiting.add(node_id)
        for dependency in index[node_id].dependencies:
            visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in ids:
        visit(node_id)

    return {
        "version": PRICE_STRUCTURE_DAG_VERSION,
        "valid": True,
        "node_count": len(nodes),
        "edge_count": sum(len(node.dependencies) for node in nodes),
        "node_ids": ids,
        "future_node_count": 0,
        "duplicate_node_count": 0,
        "unknown_dependency_count": 0,
        "cycle_count": 0,
    }


def _availability_from_receipt(receipt: Mapping[str, Any]) -> Availability:
    status = str(receipt.get("status", "")).lower()
    if status == "completed":
        return "AVAILABLE"
    if status == "degraded":
        return "DEGRADED"
    if status == "skipped":
        return "SKIPPED"
    if status == "error":
        return "ERROR"
    return "UNAVAILABLE"


def _combine_availability(values) -> Availability:
    states = [str(value).upper() for value in values]
    if not states:
        return "UNAVAILABLE"
    if "ERROR" in states:
        return "ERROR"
    if all(state == "UNAVAILABLE" for state in states):
        return "UNAVAILABLE"
    if any(state in {"UNAVAILABLE", "DEGRADED", "SKIPPED"} for state in states):
        return "DEGRADED"
    return "AVAILABLE"


def _agreement(local: Mapping[str, Any], mtf: Mapping[str, Any]) -> dict[str, Any]:
    if local.get("availability") not in {"AVAILABLE", "DEGRADED"} or mtf.get("availability") not in {"AVAILABLE", "DEGRADED"}:
        return {
            "state": "UNAVAILABLE",
            "aligned": False,
            "conflicting": False,
            "reason": "Local or MTF evidence is unavailable; agreement is not fabricated.",
            "contradictions": [],
        }

    mtf_records = [row for row in mtf.get("records", []) if isinstance(row, Mapping)]
    biases = [str(row.get("bias", "unavailable")) for row in mtf_records if str(row.get("bias", "unavailable")) in {"bullish", "bearish", "neutral"}]
    contradictions: list[dict[str, Any]] = []
    if "bullish" in biases and "bearish" in biases:
        contradictions.append({"type": "MTF_INTERNAL_CONFLICT", "biases": sorted(set(biases))})
    level_state = local.get("levels", {})
    if isinstance(level_state, Mapping):
        vwap_state = str(level_state.get("vwap_state", "unknown"))
        pdh_state = str(level_state.get("pdh_state", "unknown"))
        if vwap_state.startswith("above") and pdh_state in {"near", "below", "rejected"}:
            contradictions.append({
                "type": "LOCAL_LEVEL_TENSION",
                "facts": {"vwap_state": vwap_state, "pdh_state": pdh_state},
            })

    if contradictions:
        return {
            "state": "CONFLICTING",
            "aligned": False,
            "conflicting": True,
            "reason": "Contradictory price facts are preserved for D6; the composer does not resolve them.",
            "contradictions": contradictions,
        }
    if biases:
        return {
            "state": "ALIGNED",
            "aligned": True,
            "conflicting": False,
            "reason": "No contradictory canonical price facts were detected in the bounded evidence set.",
            "contradictions": [],
        }
    return {
        "state": "UNAVAILABLE",
        "aligned": False,
        "conflicting": False,
        "reason": "No canonical directional MTF facts are available; agreement is not inferred.",
        "contradictions": [],
    }


def _bounded_local_candle(summary: Mapping[str, Any]) -> dict[str, Any]:
    canonical = summary.get("canonical") if isinstance(summary.get("canonical"), Mapping) else summary
    return _pick(canonical, ("status", "shape", "body_ratio", "upper_wick_ratio", "lower_wick_ratio", "average_range", "calculation_version"))


def _bounded_local_levels(summary: Mapping[str, Any]) -> dict[str, Any]:
    return _pick(summary, ("canonical_status", "vwap_state", "opening_range_state", "pdh_state", "pdl_state", "level_respect_score", "canonical_level_hash", "calculation_version"))


def _bounded_market_structure(summary: Mapping[str, Any]) -> dict[str, Any]:
    return _pick(summary, ("auction_state", "profile_shape", "value_area_position", "trap_score", "vsa_downgrade_active", "confidence_cap"))


def _bounded_mtf_record(row: Mapping[str, Any]) -> dict[str, Any]:
    return _pick(row, ("timeframe", "source_snapshot_hash", "source_series_hash", "last_closed_ts", "last_closed_sequence", "bars_used", "availability", "bias", "confirmed", "quality", "reason_code"))


def _pick(mapping: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {key: mapping[key] for key in keys if key in mapping and _bounded_value(mapping[key])}


def _bounded_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, int, float)):
        return True
    if isinstance(value, str):
        return len(value) <= 256
    return False


def _require_hash(value: str, label: str) -> str:
    value = value.lower()
    if not _HASH_RE.fullmatch(value):
        raise PriceStructureEvidenceError(f"INVALID_HASH:{label}")
    return value


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
