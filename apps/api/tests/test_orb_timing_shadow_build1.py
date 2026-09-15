"""ORB BUILD-1 shadow parity: legacy resolve_symbols() vs canonical intake projection.

Research-only. run_timing_research() resolves symbols through
resolve_symbols_with_shadow(): legacy symbols still drive the run, the canonical
shadow observes every resolution, and a trendforge_latest divergence fails the
run closed. This suite proves parity on valid inputs and explicit recorded
mismatches (never silent substitution) on safety-related divergences.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models import OrbTimingResearchRequest
from app.orb import timing_research as tr
from app.orb.candidate_intake import (
    MANUAL_SELECTOR_VERSION,
    TRENDFORGE_SELECTOR_VERSION,
    CandidateState,
)
from app.orb.timing_research import (
    ORB_SYMBOL_SHADOW_VERSION,
    compare_symbol_shadow,
    resolve_symbols,
    resolve_symbols_with_shadow,
)

T0 = datetime(2026, 9, 13, 3, 30, tzinfo=timezone.utc)
SHA_A = "a" * 64


def _trendforge_intake(
    rows: list[dict],
    *,
    intake_state: str = "ACCEPTED_RESEARCH_ONLY",
    received_at: datetime = T0,
) -> dict:
    evidence_at = received_at - timedelta(seconds=5)
    return {
        "intakeId": "trendforge-intake:shadow-1",
        "intakeState": intake_state,
        "evidenceAsOf": evidence_at.isoformat(),
        "receivedAt": received_at.isoformat(),
        "payloadSha256": SHA_A,
        "packet": {
            "evidenceAsOf": evidence_at.isoformat(),
            "payloadSha256": SHA_A,
            "evidence": {"candidates": rows},
        },
    }


def _row(symbol: str, state: str, *, record_id: int = 1, status_group: str = "ready") -> dict:
    created = (T0 - timedelta(seconds=5)).isoformat()
    return {
        "recordId": record_id,
        "symbol": symbol,
        "state": state,
        "createdAt": created,
        "payload": {"symbol": symbol, "state": state, "statusGroup": status_group},
    }


def _assert_zero_authority(candidates) -> None:
    assert candidates, "shadow must materialize candidates for valid inputs"
    for candidate in candidates:
        assert candidate.research_only is True
        assert candidate.trade_allowed is False
        assert candidate.order_routing_enabled is False
        assert candidate.live_trading_blocked is True
        assert candidate.may_set_final_band is False
        assert candidate.may_execute is False


# 1. manual parity -----------------------------------------------------------
def test_manual_parity_exact_with_dedup_case_and_whitespace() -> None:
    request = OrbTimingResearchRequest(
        symbols_source="explicit",
        symbols=[" reliance ", "RELIANCE", "TCS", "", "  "],
    )
    legacy, candidates, receipt = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    assert legacy == ["RELIANCE", "TCS"]
    assert receipt.shadow_version == ORB_SYMBOL_SHADOW_VERSION
    assert receipt.symbols_source == "explicit"
    assert receipt.provenance == "manual"
    assert receipt.selection_cutoff == T0.isoformat()
    assert receipt.parity is True
    assert receipt.mismatches == ()
    assert receipt.shadow_error is None
    assert len(candidates) == 2
    assert all(c.state is CandidateState.ELIGIBLE_FOR_STUDY for c in candidates)
    assert all(c.selection_cutoff == T0 for c in candidates)
    assert all(c.selection_rule_version == MANUAL_SELECTOR_VERSION for c in candidates)
    _assert_zero_authority(candidates)


# 2. TrendForge parity --------------------------------------------------------
def test_trendforge_parity_ready_and_priority_radar() -> None:
    intake = _trendforge_intake(
        [_row("RELIANCE", "READY"), _row("TCS", "PRIORITY_RADAR", record_id=2)],
    )
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    legacy, candidates, receipt = resolve_symbols_with_shadow(request, intakes=[intake])
    assert legacy == ["RELIANCE", "TCS"]
    assert receipt.parity is True
    assert receipt.mismatches == ()
    assert receipt.provenance == "trendforge-intake:shadow-1"
    assert receipt.selection_cutoff == T0.isoformat()
    assert [c.symbol for c in candidates] == ["RELIANCE", "TCS"]
    assert all(c.selection_rule_version == TRENDFORGE_SELECTOR_VERSION for c in candidates)
    assert all(c.source_adapter == "TRENDFORGE_VALIDATED_INTAKE" for c in candidates)
    _assert_zero_authority(candidates)


# 3. stale / rejected TrendForge ----------------------------------------------
def test_stale_trendforge_receipt_yields_no_candidates_and_recorded_mismatch() -> None:
    intake = _trendforge_intake(
        [_row("RELIANCE", "READY")],
        intake_state="WAIT_STALE_TRENDFORGE_EVIDENCE",
    )
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    # Legacy scan ignores receipt state and still projects the READY row;
    # the canonical adapter refuses the stale receipt. The divergence must be
    # recorded, never silently substituted.
    legacy, candidates, receipt = resolve_symbols_with_shadow(request, intakes=[intake])
    assert legacy == ["RELIANCE"]
    assert candidates == []
    assert receipt.parity is False
    assert receipt.mismatches == ("LEGACY_ONLY:RELIANCE",)


def test_rejected_trendforge_state_yields_no_candidates_both_paths() -> None:
    intake = _trendforge_intake([_row("RELIANCE", "WAIT_DATA_WEAK")])
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    with pytest.raises(ValueError, match="no READY/PRIORITY_RADAR"):
        resolve_symbols_with_shadow(request, intakes=[intake])


# 4. deterministic replay ------------------------------------------------------
def test_deterministic_replay_with_identical_cutoff() -> None:
    request = OrbTimingResearchRequest(
        symbols_source="explicit", symbols=["RELIANCE", "TCS"]
    )
    first = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    second = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    assert [c.candidate_hash for c in first[1]] == [c.candidate_hash for c in second[1]]
    assert first[2].receipt_hash == second[2].receipt_hash
    assert first[2].candidate_hashes == second[2].candidate_hashes


def test_distinct_cutoffs_diverge() -> None:
    request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE"])
    early = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    late = resolve_symbols_with_shadow(request, selection_cutoff=T0 + timedelta(hours=1))
    assert early[1][0].candidate_hash != late[1][0].candidate_hash


# 5. provenance preservation ----------------------------------------------------
def test_manual_provenance_preserves_cutoff_selector_and_identity() -> None:
    request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE"])
    _, candidates, _ = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    candidate = candidates[0]
    assert candidate.source_adapter == "MANUAL_RESEARCH_CANDIDATE"
    assert candidate.selection_cutoff == T0
    assert candidate.source_record_id == f"manual:RELIANCE:{T0.isoformat()}"
    assert candidate.reconstruction_policy.selector_version == MANUAL_SELECTOR_VERSION


def test_trendforge_provenance_preserves_intake_timestamps_and_hash() -> None:
    intake = _trendforge_intake([_row("RELIANCE", "READY")])
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    _, candidates, _ = resolve_symbols_with_shadow(request, intakes=[intake])
    candidate = candidates[0]
    assert candidate.selection_cutoff == T0
    assert candidate.source_record_id.startswith("trendforge-intake:shadow-1:candidate:")
    fact = candidate.source_facts[0]
    assert fact.source_id == "trendforge-intake:shadow-1"
    assert fact.source_hash == SHA_A
    assert fact.observed_at == T0 - timedelta(seconds=5)
    assert fact.available_at == T0


# 6. duplicate handling ----------------------------------------------------------
def test_duplicate_rows_collapse_to_single_canonical_symbol() -> None:
    intake = _trendforge_intake(
        [_row("RELIANCE", "READY"), _row("reliance ", "READY", record_id=2)],
    )
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    legacy, candidates, receipt = resolve_symbols_with_shadow(request, intakes=[intake])
    # Each intake row keeps its own receipt (distinct recordIds), while the
    # compatibility projection collapses to one symbol exactly like legacy.
    assert legacy == ["RELIANCE"]
    assert len(candidates) == 2
    assert receipt.canonical_symbols == ("RELIANCE",)
    assert receipt.parity is True


# 7. missing / reference identity --------------------------------------------------
def test_shadow_fabricates_no_reference_price_identity() -> None:
    intake = _trendforge_intake(
        [_row("RELIANCE", "READY"), _row("TCS", "PRIORITY_RADAR", record_id=2)],
    )
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    _, candidates, _ = resolve_symbols_with_shadow(request, intakes=[intake])
    assert all(c.reference_price_identity is None for c in candidates)
    assert all(c.state is CandidateState.ELIGIBLE_FOR_STUDY for c in candidates)


def test_explicit_shadow_fabricates_no_reference_price_identity() -> None:
    request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE"])
    _, candidates, _ = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    assert candidates[0].reference_price_identity is None


# 8. zero execution / final-band authority -------------------------------------------
def test_shadow_candidates_carry_zero_authority_manual_and_trendforge() -> None:
    manual_request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE"])
    _, manual_candidates, _ = resolve_symbols_with_shadow(manual_request, selection_cutoff=T0)
    _assert_zero_authority(manual_candidates)

    intake = _trendforge_intake([_row("RELIANCE", "READY")])
    tf_request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    _, tf_candidates, _ = resolve_symbols_with_shadow(tf_request, intakes=[intake])
    _assert_zero_authority(tf_candidates)


# 9. expected legacy-vs-canonical safety divergence -------------------------------------
def test_non_ready_status_group_is_recorded_not_substituted() -> None:
    intake = _trendforge_intake([_row("RELIANCE", "READY", status_group="weak")])
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    legacy, candidates, receipt = resolve_symbols_with_shadow(request, intakes=[intake])
    # Legacy projection keeps the row; canonical skips non-ready status groups.
    assert legacy == ["RELIANCE"]
    assert candidates == []
    assert receipt.parity is False
    assert "LEGACY_ONLY:RELIANCE" in receipt.mismatches
    # The canonical side never feeds the run: legacy output is returned as-is.
    assert legacy == ["RELIANCE"]
    assert candidates == []


def test_compare_symbol_shadow_order_divergence_is_explicit() -> None:
    parity, mismatches = compare_symbol_shadow(["A", "B"], ["B", "A"])
    assert parity is False
    assert mismatches == ["ORDER_DIVERGENCE"]


def test_canonical_build_failure_is_recorded_and_legacy_untouched(monkeypatch) -> None:
    import app.orb.timing_research as shadow_module

    def _boom(candidates, **kwargs):
        raise RuntimeError("projection exploded")

    monkeypatch.setattr(shadow_module, "project_eligible_symbols", _boom)
    request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE"])
    legacy, candidates, receipt = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    assert legacy == ["RELIANCE"]
    assert candidates == []
    assert receipt.parity is False
    assert receipt.shadow_error == "RuntimeError: projection exploded"
    assert "LEGACY_ONLY:RELIANCE" in receipt.mismatches
    assert any(m.startswith("SHADOW_ERROR:") for m in receipt.mismatches)


# legacy-unchanged guard -----------------------------------------------------------------
def test_legacy_resolve_symbols_unchanged_by_shadow() -> None:
    explicit = OrbTimingResearchRequest(
        symbols_source="explicit", symbols=[" reliance ", "TCS", "TCS"]
    )
    assert resolve_symbols(explicit) == ["RELIANCE", "TCS"]
    legacy, _, _ = resolve_symbols_with_shadow(explicit, selection_cutoff=T0)
    assert legacy == resolve_symbols(explicit)

    intake = _trendforge_intake(
        [{"recordId": 1, "symbol": "RELIANCE", "state": "READY"}],
    )
    trendforge = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    legacy_tf, _, receipt = resolve_symbols_with_shadow(trendforge, intakes=[intake])
    assert legacy_tf == ["RELIANCE"]
    assert receipt.parity is True


# Gap-fill: shadow on the active runtime path -----------------------------------
class _StubDiscovery:
    def model_dump(self, mode: str = "json") -> dict:
        return {"ranked_combinations": [], "trades": [], "no_future_leakage": True}


def test_active_run_resolves_through_shadow_and_attaches_receipt(tmp_path, monkeypatch) -> None:
    # Discovery internals are covered by the v197 suite; here only the intake
    # seam is under test, so both seams are stubbed past validation.
    monkeypatch.setattr(tr, "run_orb_discovery", lambda request_model: _StubDiscovery())
    monkeypatch.setattr(tr, "load_hstry_series", lambda *args, **kwargs: object())
    monkeypatch.setattr(tr, "OrbDiscoveryRequest", lambda **kwargs: object())
    monkeypatch.setattr(tr, "_checkpoint_path", lambda request_hash: tmp_path / f"cp_{request_hash[:16]}.json")
    request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE"])
    result = tr.run_timing_research(request, base_dir=tmp_path)
    assert result.symbols_requested == ["RELIANCE"]
    assert result.symbols_completed == ["RELIANCE"]
    shadow = result.symbol_shadow
    assert shadow is not None
    assert shadow["parity"] is True
    assert shadow["mismatches"] == []
    assert shadow["provenance"] == "manual"
    assert shadow["counts"]["candidate_count"] == 1
    assert shadow["counts"]["eligible_count"] == 1


def test_active_run_fails_closed_on_stale_trendforge_intake(monkeypatch) -> None:
    intake = _trendforge_intake(
        [_row("RELIANCE", "READY")],
        intake_state="WAIT_STALE_TRENDFORGE_EVIDENCE",
    )
    monkeypatch.setattr(tr, "_load_recent_intakes", lambda: [intake])
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    with pytest.raises(ValueError, match="failed closed"):
        tr.run_timing_research(request)


def test_active_run_fails_closed_on_shadow_error_for_trendforge(monkeypatch) -> None:
    intake = _trendforge_intake([_row("RELIANCE", "READY")])
    monkeypatch.setattr(tr, "_load_recent_intakes", lambda: [intake])
    monkeypatch.setattr(
        tr, "project_eligible_symbols", lambda candidates, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    with pytest.raises(ValueError, match="failed closed"):
        tr.run_timing_research(request)


# Gap-fill: cutoff preserved on empty canonical sets ------------------------------
def test_stale_receipt_preserves_pit_cutoff() -> None:
    intake = _trendforge_intake(
        [_row("RELIANCE", "READY")],
        intake_state="WAIT_STALE_TRENDFORGE_EVIDENCE",
    )
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    _, candidates, receipt = resolve_symbols_with_shadow(request, intakes=[intake])
    assert candidates == []
    assert receipt.selection_cutoff == T0.isoformat()


# Gap-fill: observability counters and latency --------------------------------------
def test_receipt_carries_observability_counts_and_latency() -> None:
    intake = _trendforge_intake(
        [_row("RELIANCE", "READY"), _row("TCS", "PRIORITY_RADAR", record_id=2)],
    )
    request = OrbTimingResearchRequest(symbols_source="trendforge_latest")
    _, candidates, receipt = resolve_symbols_with_shadow(request, intakes=[intake])
    assert receipt.candidate_count == 2
    assert receipt.eligible_count == 2
    assert receipt.source_count == 2
    assert receipt.reason_count == 2
    assert receipt.instrument_type_counts == (("NSE_EQUITY", 2),)
    assert receipt.universe_scope_counts == (("ONLINE_SELECTED", 2),)
    assert receipt.availability_counts == (("AVAILABLE", 2),)
    assert receipt.latency_ms >= 0.0
    # Latency is wall-clock: it must not enter the deterministic receipt hash.
    assert len(candidates) == 2


def test_receipt_hash_is_stable_across_runs_with_identical_cutoff() -> None:
    request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE"])
    first = resolve_symbols_with_shadow(request, selection_cutoff=T0)[2]
    second = resolve_symbols_with_shadow(request, selection_cutoff=T0)[2]
    assert first.receipt_hash == second.receipt_hash
