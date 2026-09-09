from __future__ import annotations

from copy import deepcopy

from app.behavior.decision_spine.price_structure_evidence import build_price_structure_evidence


SNAPSHOT = "1" * 64
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
        "CANDLE_ANATOMY": _receipt("CANDLE_ANATOMY", "2", {"status": "AVAILABLE", "body_ratio": 0.5}),
        "LEVEL_CONTEXT": _receipt("LEVEL_CONTEXT", "3", {"canonical_status": "AVAILABLE", "vwap_state": "above", "pdh_state": "above"}),
        "MARKET_STRUCTURE_LIQUIDITY": _receipt("MARKET_STRUCTURE_LIQUIDITY", "4", {"auction_state": "trend", "trap_score": 0.1}),
    }
    mtf = _receipt(
        "MTF_CONFIRMATION",
        "5",
        {
            "canonical_status": "AVAILABLE",
            "mtf_hash": "6" * 64,
            "records": [{"timeframe": "15m", "availability": "AVAILABLE", "bias": "bullish", "confirmed": True}],
            "calculation_audit": {"future_or_incomplete_bar_authority_count": 0},
        },
    )
    return local, mtf


def _build(local, mtf):
    return build_price_structure_evidence(
        snapshot_hash=SNAPSHOT,
        decision_time_ns=DECISION,
        local_receipts=local,
        mtf_receipt=mtf,
    )


def test_m31f_replay_001_same_facts_same_structure_hash():
    local, mtf = _inputs()
    first = _build(deepcopy(local), deepcopy(mtf))
    second = _build(deepcopy(local), deepcopy(mtf))
    assert first.structure_hash == second.structure_hash
    assert first.as_dict() == second.as_dict()


def test_m31f_replay_002_changed_legitimate_upstream_hash_changes_structure_hash():
    local, mtf = _inputs()
    first = _build(local, mtf)
    changed = deepcopy(local)
    changed["LEVEL_CONTEXT"]["output_hash"] = "7" * 64
    second = _build(changed, deepcopy(mtf))
    assert first.local["structure_hash"] != second.local["structure_hash"]
    assert first.structure_hash != second.structure_hash


def test_m31f_replay_003_noncausal_receipt_warning_does_not_change_structure_hash():
    local, mtf = _inputs()
    first = _build(local, mtf)
    changed = deepcopy(local)
    changed["LEVEL_CONTEXT"]["warnings"] = ["operational-only-warning"]
    second = _build(changed, deepcopy(mtf))
    assert first.structure_hash == second.structure_hash


def test_m31f_replay_004_mtf_hash_change_changes_only_mtf_and_fusion_identity():
    local, mtf = _inputs()
    first = _build(local, mtf)
    changed = deepcopy(mtf)
    changed["output_summary"]["mtf_hash"] = "8" * 64
    second = _build(deepcopy(local), changed)
    assert first.local["structure_hash"] == second.local["structure_hash"]
    assert first.mtf["mtf_hash"] != second.mtf["mtf_hash"]
    assert first.structure_hash != second.structure_hash
