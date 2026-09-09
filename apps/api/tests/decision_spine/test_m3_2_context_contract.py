from __future__ import annotations

import json
import time

import pytest

from app.behavior.decision_spine.canonical_context_intelligence import (
    CANONICAL_CONTEXT_ENVELOPE_VERSION,
    MAX_CONTEXT_ENVELOPE_BYTES,
    CanonicalContextError,
    ContextSourceObservation,
    build_canonical_context_envelope,
)


D2_HASH = "a" * 64
DECISION = 1_800_000_000_000_000_000


def _source(
    source_id: str = "NIFTY50:5m",
    *,
    source_kind: str = "INDEX",
    source_hash: str | None = "b" * 64,
    close_time: int | None = DECISION - 300_000_000_000,
    available_at: int | None = DECISION - 1,
    availability: str = "AVAILABLE",
    synthetic: bool = False,
    identity_match: bool = True,
    d2_decision_time_ns: int = DECISION,
    freshness_state: str = "FRESH",
    clock_skew_state: str = "ALIGNED",
    reason_codes: tuple[str, ...] = (),
) -> ContextSourceObservation:
    return ContextSourceObservation(
        source_id=source_id,
        source_kind=source_kind,  # type: ignore[arg-type]
        symbol_or_universe="NIFTY 50",
        provider_id="fixture-provider",
        provider_contract_version="fixture-provider.v1",
        source_snapshot_hash=source_hash,
        source_timeframe="5m",
        source_bar_close_time_ns=close_time,
        available_at_ns=available_at,
        d2_decision_time_ns=d2_decision_time_ns,
        sequence_or_watermark="seq-42",
        freshness_state=freshness_state,  # type: ignore[arg-type]
        clock_skew_state=clock_skew_state,  # type: ignore[arg-type]
        identity_match=identity_match,
        synthetic=synthetic,
        availability=availability,  # type: ignore[arg-type]
        reason_codes=reason_codes,
    )


def test_m32a_001_builds_deterministic_bounded_zero_authority_envelope():
    result = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[_source()],
    )
    payload = result.as_dict()
    assert payload["calculation_version"] == CANONICAL_CONTEXT_ENVELOPE_VERSION
    assert payload["d2_snapshot_hash"] == D2_HASH
    assert payload["availability"] == "AVAILABLE"
    assert payload["source_hashes"] == {"NIFTY50:5m": "b" * 64}
    assert len(payload["context_hash"]) == 64
    assert payload["used_for_probability"] is False
    assert payload["may_propose"] is False
    assert payload["may_veto"] is False
    assert payload["may_downgrade"] is False
    assert payload["may_set_final_band"] is False
    assert payload["may_execute"] is False
    assert payload["trade_allowed"] is False
    assert payload["order_routing_enabled"] is False
    assert payload["live_trading_blocked"] is True
    assert len(json.dumps(payload, sort_keys=True).encode("utf-8")) < MAX_CONTEXT_ENVELOPE_BYTES


def test_m32a_002_source_completion_order_does_not_change_context_hash():
    index = _source("INDEX:NIFTY50", source_hash="b" * 64)
    sector = _source(
        "SECTOR:NIFTY-IT",
        source_kind="SECTOR",
        source_hash="c" * 64,
    )
    first = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[index, sector],
    )
    second = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[sector, index],
    )
    assert first.context_hash == second.context_hash
    assert [item.source_id for item in first.sources] == ["INDEX:NIFTY50", "SECTOR:NIFTY-IT"]


def test_m32a_003_unavailable_source_stays_unavailable_and_never_gets_fake_hash():
    unavailable = _source(
        "SECTOR:UNKNOWN",
        source_kind="SECTOR",
        source_hash=None,
        close_time=None,
        available_at=None,
        availability="UNAVAILABLE",
        freshness_state="UNKNOWN",
        clock_skew_state="UNKNOWN",
        reason_codes=("SECTOR_SOURCE_MISSING",),
    )
    result = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[unavailable],
    )
    payload = result.as_dict()
    assert payload["availability"] == "UNAVAILABLE"
    assert payload["source_hashes"] == {}
    assert payload["sources"][0]["source_snapshot_hash"] is None
    assert payload["sources"][0]["availability"] == "UNAVAILABLE"
    assert "return" not in payload["sources"][0]
    assert "score" not in payload["sources"][0]


def test_m32a_004_mixed_available_and_missing_sources_degrade_instead_of_neutralizing():
    result = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[
            _source("INDEX:NIFTY50"),
            _source(
                "SECTOR:MISSING",
                source_kind="SECTOR",
                source_hash=None,
                close_time=None,
                available_at=None,
                availability="UNAVAILABLE",
                freshness_state="UNKNOWN",
                clock_skew_state="UNKNOWN",
                reason_codes=("MISSING",),
            ),
        ],
    )
    assert result.availability == "DEGRADED"
    assert result.source_counts["AVAILABLE"] == 1
    assert result.source_counts["UNAVAILABLE"] == 1


def test_m32a_005_rejects_synthetic_available_source():
    with pytest.raises(CanonicalContextError, match="SYNTHETIC_SOURCE_NOT_CANONICAL"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source(synthetic=True)],
        )


def test_m32a_006_rejects_source_bar_that_is_not_closed_by_decision_time():
    with pytest.raises(CanonicalContextError, match="FUTURE_SOURCE_BAR"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source(close_time=DECISION + 1)],
        )


def test_m32a_007_rejects_source_not_available_at_decision_time():
    with pytest.raises(CanonicalContextError, match="FUTURE_SOURCE_AVAILABILITY"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source(available_at=DECISION + 1)],
        )


def test_m32a_008_rejects_decision_time_mismatch():
    with pytest.raises(CanonicalContextError, match="DECISION_TIME_MISMATCH"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source(d2_decision_time_ns=DECISION - 1)],
        )


def test_m32a_009_rejects_available_identity_mismatch():
    with pytest.raises(CanonicalContextError, match="SOURCE_IDENTITY_MISMATCH"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source(identity_match=False)],
        )


def test_m32a_010_rejects_malformed_source_hash():
    with pytest.raises(CanonicalContextError, match="INVALID_SHA256"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source(source_hash="not-a-hash")],
        )


def test_m32a_011_rejects_duplicate_source_id():
    with pytest.raises(CanonicalContextError, match="DUPLICATE_SOURCE_ID"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source("INDEX:NIFTY50"), _source("INDEX:NIFTY50", source_hash="c" * 64)],
        )


def test_m32a_012_rejects_available_market_source_without_close_time():
    with pytest.raises(CanonicalContextError, match="MISSING_SOURCE_BAR_CLOSE_TIME"):
        build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=[_source(close_time=None)],
        )


def test_m32a_013_calendar_source_can_be_non_bar_observation_when_availability_is_proven():
    calendar = ContextSourceObservation(
        source_id="CALENDAR:NSE:2026-09-08",
        source_kind="CALENDAR",
        symbol_or_universe="NSE",
        provider_id="calendar-fixture",
        provider_contract_version="calendar.v1",
        source_snapshot_hash="d" * 64,
        source_timeframe=None,
        source_bar_close_time_ns=None,
        available_at_ns=DECISION - 1,
        d2_decision_time_ns=DECISION,
        sequence_or_watermark="calendar-2026-09-08",
        freshness_state="FRESH",
        clock_skew_state="ALIGNED",
        availability="AVAILABLE",
    )
    result = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[calendar],
    )
    assert result.availability == "AVAILABLE"
    assert result.sources[0].source_bar_close_time_ns is None


def test_m32a_014_stale_source_is_visible_and_deterministically_hashed():
    stale = _source(
        freshness_state="STALE",
        reason_codes=("PROVIDER_STALE",),
    )
    result = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[stale],
    )
    assert any("stale" in warning.lower() for warning in result.warnings)
    again = build_canonical_context_envelope(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        sources=[stale],
    )
    assert result.context_hash == again.context_hash


def test_m32a_015_context_envelope_latency_is_bounded_for_small_source_bundle():
    sources = [
        _source("INDEX:NIFTY50", source_hash="b" * 64),
        _source("SECTOR:NIFTY-IT", source_kind="SECTOR", source_hash="c" * 64),
        _source("BREADTH:NSE", source_kind="BREADTH", source_hash="d" * 64, close_time=None),
    ]
    started = time.perf_counter()
    result = None
    for _ in range(200):
        result = build_canonical_context_envelope(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            sources=sources,
        )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    assert result is not None
    # Anti-pathology guard only; not a market-latency SLA or edge claim.
    assert elapsed_ms < 2000.0
    assert len(json.dumps(result.as_dict(), sort_keys=True).encode("utf-8")) < MAX_CONTEXT_ENVELOPE_BYTES
