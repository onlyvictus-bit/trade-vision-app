from __future__ import annotations

import json

from app.behavior.decision_spine.price_structure_evidence import (
    PRICE_STRUCTURE_EVIDENCE_VERSION,
    build_price_structure_evidence,
)


SNAPSHOT = "a" * 64


def _receipt(engine: str, hash_char: str, summary: dict, status: str = "completed"):
    return {
        "engine_id": engine,
        "source_snapshot_hash": SNAPSHOT,
        "output_hash": hash_char * 64,
        "status": status,
        "output_summary": summary,
    }


def _locals():
    return {
        "CANDLE_ANATOMY": _receipt(
            "CANDLE_ANATOMY", "b", {"status": "AVAILABLE", "body_ratio": 0.62}
        ),
        "LEVEL_CONTEXT": _receipt(
            "LEVEL_CONTEXT",
            "c",
            {
                "canonical_status": "AVAILABLE",
                "vwap_state": "above",
                "pdh_state": "above",
                "opening_range_state": "above",
            },
        ),
        "MARKET_STRUCTURE_LIQUIDITY": _receipt(
            "MARKET_STRUCTURE_LIQUIDITY",
            "d",
            {"auction_state": "trend", "trap_score": 0.2, "vsa_downgrade_active": False},
        ),
    }


def _mtf(records=None, status="AVAILABLE"):
    return _receipt(
        "MTF_CONFIRMATION",
        "e",
        {
            "canonical_mtf_intelligence": True,
            "canonical_status": status,
            "mtf_hash": "f" * 64,
            "records": records or [],
            "calculation_audit": {"future_or_incomplete_bar_authority_count": 0},
        },
    )


def test_m31f_001_builds_bounded_zero_authority_price_world():
    result = build_price_structure_evidence(
        snapshot_hash=SNAPSHOT,
        decision_time_ns=1_800_000_000_000_000_000,
        local_receipts=_locals(),
        mtf_receipt=_mtf([{"timeframe": "15m", "availability": "AVAILABLE", "bias": "bullish", "confirmed": True}]),
    )
    payload = result.as_dict()
    assert result.calculation_version == PRICE_STRUCTURE_EVIDENCE_VERSION
    assert len(result.structure_hash) == 64
    assert payload["source_snapshot_hash"] == SNAPSHOT
    assert payload["local"]["structure_hash"]
    assert payload["mtf"]["mtf_hash"] == "f" * 64
    assert payload["may_propose"] is False
    assert payload["may_veto"] is False
    assert payload["may_downgrade"] is False
    assert payload["may_set_final_band"] is False
    assert payload["may_execute"] is False
    assert payload["trade_allowed"] is False
    assert payload["order_routing_enabled"] is False
    assert payload["live_trading_blocked"] is True
    assert len(json.dumps(payload).encode("utf-8")) < 24_000


def test_m31f_002_preserves_mtf_internal_contradiction_instead_of_scoring_it():
    result = build_price_structure_evidence(
        snapshot_hash=SNAPSHOT,
        decision_time_ns=1_800_000_000_000_000_000,
        local_receipts=_locals(),
        mtf_receipt=_mtf(
            [
                {"timeframe": "15m", "availability": "AVAILABLE", "bias": "bullish", "confirmed": True},
                {"timeframe": "1h", "availability": "AVAILABLE", "bias": "bearish", "confirmed": False},
            ]
        ),
    )
    assert result.agreement["state"] == "CONFLICTING"
    assert result.agreement["conflicting"] is True
    assert result.agreement["contradictions"][0]["type"] == "MTF_INTERNAL_CONFLICT"
    assert "score" not in result.as_dict()


def test_m31f_003_unavailable_mtf_never_becomes_neutral_alignment():
    mtf = _mtf([], status="UNAVAILABLE")
    result = build_price_structure_evidence(
        snapshot_hash=SNAPSHOT,
        decision_time_ns=1_800_000_000_000_000_000,
        local_receipts=_locals(),
        mtf_receipt=mtf,
    )
    assert result.mtf["availability"] == "UNAVAILABLE"
    assert result.agreement["state"] == "UNAVAILABLE"
    assert result.epistemic["availability"] == "DEGRADED"


def test_m31f_004_upstream_hashes_are_explicit_and_traceable():
    result = build_price_structure_evidence(
        snapshot_hash=SNAPSHOT,
        decision_time_ns=1_800_000_000_000_000_000,
        local_receipts=_locals(),
        mtf_receipt=_mtf(),
    )
    assert result.upstream["snapshot_hash"] == SNAPSHOT
    assert result.upstream["local_output_hashes"] == {
        "CANDLE_ANATOMY": "b" * 64,
        "LEVEL_CONTEXT": "c" * 64,
        "MARKET_STRUCTURE_LIQUIDITY": "d" * 64,
    }
    assert result.upstream["mtf_hash"] == "f" * 64
    assert result.dag["valid"] is True
    assert result.dag["cycle_count"] == 0
    assert result.dag["future_node_count"] == 0
