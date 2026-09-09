from __future__ import annotations

from app.behavior.decision_spine.authority_registry import (
    FINAL_BAND_AUTHORITY,
    all_engine_authorities,
    get_engine_authority,
    validate_authority_registry,
)


M3_3_ENGINE_IDS = (
    "CANONICAL_MEMORY_EPISODE_FREEZER",
    "CANONICAL_MEMORY_CORPUS",
    "CANONICAL_ANALOG_RETRIEVAL",
    "CANONICAL_MEMORY_WORLD",
    "CANONICAL_MEMORY_RETENTION",
    "CANONICAL_PERSISTED_MEMORY_ADAPTER",
)


def test_m3_3_canonical_memory_engines_have_zero_decision_authority():
    for engine_id in M3_3_ENGINE_IDS:
        authority = get_engine_authority(engine_id)
        assert authority is not None
        assert authority.may_propose is False
        assert authority.may_veto is False
        assert authority.may_downgrade is False
        assert authority.may_set_final_band is False
        assert authority.may_execute is False
        assert authority.authority_rank == 0


def test_d6_remains_the_only_final_band_authority():
    assert validate_authority_registry() == ()
    assert [item.engine_id for item in all_engine_authorities() if item.may_set_final_band] == [FINAL_BAND_AUTHORITY]
