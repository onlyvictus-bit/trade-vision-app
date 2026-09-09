from __future__ import annotations

from copy import deepcopy

import pytest

from app.behavior.decision_spine.price_structure_evidence import (
    PriceEvidenceNode,
    PriceStructureEvidenceError,
    _validate_dag,
    build_price_structure_evidence,
)


SNAPSHOT = "9" * 64
DECISION = 1_800_000_000_000_000_000


def _receipt(engine, char, summary, status="completed"):
    return {
        "engine_id": engine,
        "source_snapshot_hash": SNAPSHOT,
        "output_hash": char * 64,
        "status": status,
        "output_summary": summary,
    }


def _inputs():
    local = {
        "CANDLE_ANATOMY": _receipt("CANDLE_ANATOMY", "a", {"status": "AVAILABLE"}),
        "LEVEL_CONTEXT": _receipt("LEVEL_CONTEXT", "b", {"canonical_status": "AVAILABLE", "vwap_state": "above"}),
        "MARKET_STRUCTURE_LIQUIDITY": _receipt("MARKET_STRUCTURE_LIQUIDITY", "c", {"auction_state": "trend"}),
    }
    mtf = _receipt(
        "MTF_CONFIRMATION",
        "d",
        {
            "canonical_status": "AVAILABLE",
            "mtf_hash": "e" * 64,
            "records": [],
            "calculation_audit": {"future_or_incomplete_bar_authority_count": 0},
        },
    )
    return local, mtf


def test_m31f_adv_001_snapshot_mismatch_blocks():
    local, mtf = _inputs()
    local["LEVEL_CONTEXT"]["source_snapshot_hash"] = "f" * 64
    with pytest.raises(PriceStructureEvidenceError, match="SNAPSHOT_MISMATCH:LEVEL_CONTEXT"):
        build_price_structure_evidence(snapshot_hash=SNAPSHOT, decision_time_ns=DECISION, local_receipts=local, mtf_receipt=mtf)


def test_m31f_adv_002_missing_upstream_blocks():
    local, mtf = _inputs()
    del local["CANDLE_ANATOMY"]
    with pytest.raises(PriceStructureEvidenceError, match="UNKNOWN_OR_MISSING_UPSTREAM:CANDLE_ANATOMY"):
        build_price_structure_evidence(snapshot_hash=SNAPSHOT, decision_time_ns=DECISION, local_receipts=local, mtf_receipt=mtf)


def test_m31f_adv_003_future_or_incomplete_mtf_authority_blocks():
    local, mtf = _inputs()
    mtf["output_summary"]["calculation_audit"]["future_or_incomplete_bar_authority_count"] = 1
    with pytest.raises(PriceStructureEvidenceError, match="FUTURE_OR_INCOMPLETE_BAR_AUTHORITY"):
        build_price_structure_evidence(snapshot_hash=SNAPSHOT, decision_time_ns=DECISION, local_receipts=local, mtf_receipt=mtf)


def test_m31f_adv_004_duplicate_dag_node_blocks():
    nodes = [
        PriceEvidenceNode("D2", SNAPSHOT, SNAPSHOT, (), "AVAILABLE"),
        PriceEvidenceNode("D2", SNAPSHOT, SNAPSHOT, (), "AVAILABLE"),
    ]
    with pytest.raises(PriceStructureEvidenceError, match="DUPLICATE_DAG_NODE"):
        _validate_dag(nodes, snapshot_hash=SNAPSHOT, decision_time_ns=DECISION)


def test_m31f_adv_005_unknown_dependency_blocks():
    nodes = [
        PriceEvidenceNode("D2", SNAPSHOT, SNAPSHOT, (), "AVAILABLE"),
        PriceEvidenceNode("FUSION", SNAPSHOT, "a" * 64, ("MISSING",), "AVAILABLE"),
    ]
    with pytest.raises(PriceStructureEvidenceError, match="UNKNOWN_DAG_DEPENDENCY"):
        _validate_dag(nodes, snapshot_hash=SNAPSHOT, decision_time_ns=DECISION)


def test_m31f_adv_006_cycle_blocks():
    nodes = [
        PriceEvidenceNode("A", SNAPSHOT, "a" * 64, ("B",), "AVAILABLE"),
        PriceEvidenceNode("B", SNAPSHOT, "b" * 64, ("A",), "AVAILABLE"),
    ]
    with pytest.raises(PriceStructureEvidenceError, match="DAG_CYCLE"):
        _validate_dag(nodes, snapshot_hash=SNAPSHOT, decision_time_ns=DECISION)


def test_m31f_adv_007_future_node_blocks():
    nodes = [
        PriceEvidenceNode("D2", SNAPSHOT, SNAPSHOT, (), "AVAILABLE"),
        PriceEvidenceNode("LOCAL", SNAPSHOT, "a" * 64, ("D2",), "AVAILABLE", observed_at_ns=DECISION + 1),
    ]
    with pytest.raises(PriceStructureEvidenceError, match="FUTURE_DAG_NODE"):
        _validate_dag(nodes, snapshot_hash=SNAPSHOT, decision_time_ns=DECISION)


def test_m31f_adv_008_degraded_local_stays_degraded_not_neutral():
    local, mtf = _inputs()
    local["LEVEL_CONTEXT"]["status"] = "degraded"
    result = build_price_structure_evidence(snapshot_hash=SNAPSHOT, decision_time_ns=DECISION, local_receipts=local, mtf_receipt=mtf)
    assert result.local["availability"] == "DEGRADED"
    assert result.epistemic["availability"] == "DEGRADED"
    assert any("LEVEL_CONTEXT availability is DEGRADED" in item for item in result.epistemic["warnings"])
