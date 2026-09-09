from __future__ import annotations

from types import SimpleNamespace

from app.behavior.decision_spine.m3_3_memory_wiring import (
    build_m33_stage2_observations,
    build_memory_receipts,
    merge_m33_memory_receipts,
    unavailable_memory_receipt,
)


H1 = "1" * 64
H2 = "2" * 64


class FakeWorld(SimpleNamespace):
    def as_dict(self):
        return dict(self.payload)


def _world():
    payload = {
        "calculation_version": "canonical-memory-world.v1",
        "d2_snapshot_hash": H1,
        "decision_time_ns": 10_000,
        "corpus_hash": H2,
        "availability": "AVAILABLE",
        "warnings": [],
        "output_hash": "3" * 64,
        "used_for_probability": False,
        "may_set_final_band": False,
        "may_execute": False,
    }
    return FakeWorld(
        calculation_version=payload["calculation_version"],
        d2_snapshot_hash=H1,
        decision_time_ns=10_000,
        corpus_hash=H2,
        availability="AVAILABLE",
        warnings=(),
        output_hash="3" * 64,
        payload=payload,
    )


def test_memory_world_wires_as_analog_receipt_with_zero_authority():
    receipts = build_memory_receipts(memory_world=_world())
    assert [receipt.engine_id for receipt in receipts] == ["ANALOG_MEMORY"]
    receipt = receipts[0]
    assert receipt.source_snapshot_hash == H1
    assert receipt.output_summary["canonical_memory_intelligence"] is True
    assert receipt.output_summary["used_for_probability"] is False
    assert receipt.output_summary["may_set_final_band"] is False
    assert receipt.output_summary["may_execute"] is False
    observations = build_m33_stage2_observations(receipts)
    assert observations[0].engine_id == "ANALOG_MEMORY"
    assert observations[0].used_for_probability is False
    assert observations[0].final_band_claimed is False


def test_merge_replaces_matching_legacy_memory_without_duplicate():
    legacy = SimpleNamespace(engine_id="ANALOG_MEMORY", output_hash="9" * 64)
    unrelated = SimpleNamespace(engine_id="CANDLE_ANATOMY", output_hash="8" * 64)
    canonical = build_memory_receipts(memory_world=_world())
    merged = merge_m33_memory_receipts((legacy, unrelated), canonical)
    ids = [item.engine_id for item in merged]
    assert ids.count("ANALOG_MEMORY") == 1
    assert ids.count("CANDLE_ANATOMY") == 1
    analog = next(item for item in merged if item.engine_id == "ANALOG_MEMORY")
    assert analog.output_hash == "3" * 64


def test_unavailable_memory_is_explicit_not_neutral():
    receipt = unavailable_memory_receipt(
        engine_id="NINE_CANDLE_MEMORY",
        source_snapshot_hash=H1,
        engine_version="canonical-nine-candle-memory.v1",
        reason="NO_PERSISTED_CANONICAL_9C_CORPUS",
    )
    assert receipt.status == "degraded"
    assert receipt.output_summary["availability"] == "UNAVAILABLE"
    assert receipt.output_summary["reason_codes"] == ["NO_PERSISTED_CANONICAL_9C_CORPUS"]
    assert receipt.output_summary["trade_allowed"] is False
    assert receipt.output_summary["order_routing_enabled"] is False
