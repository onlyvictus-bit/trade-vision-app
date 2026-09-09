from __future__ import annotations

from app.behavior.decision_spine.authority_registry import get_engine_authority


CANONICAL_M3_3_ENGINE_IDS = (
    "CANONICAL_RELIABILITY_MEMORY",
    "HISTORICAL_SESSION_MEMORY",
    "CANONICAL_PATTERN_MEMORY",
    "CANONICAL_NINE_CANDLE_MEMORY",
    "CANONICAL_PTA_MARKER_RUNTIME",
    "M33_MEMORY_WIRING",
)


def test_complete_m3_3_inventory_is_registered_with_zero_authority():
    for engine_id in CANONICAL_M3_3_ENGINE_IDS:
        authority = get_engine_authority(engine_id)
        assert authority is not None
        assert authority.authority_rank == 0
        assert authority.may_propose is False
        assert authority.may_veto is False
        assert authority.may_downgrade is False
        assert authority.may_set_final_band is False
        assert authority.may_execute is False
