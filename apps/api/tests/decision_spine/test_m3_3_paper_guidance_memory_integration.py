from __future__ import annotations

from types import SimpleNamespace

from app.behavior import paper_guidance_spine as spine


H1 = "1" * 64


def _snapshot():
    return SimpleNamespace(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=2_000_000_000,
        snapshot_hash=H1,
    )


def test_public_facade_mints_canonical_persisted_memory_receipt(monkeypatch):
    summary = {
        "historical_match_count": 3,
        "raw_record_count": 9,
        "complete_record_count": 9,
        "excluded_record_count": 0,
        "independent_episode_count": 3,
        "independent_session_count": 3,
        "independent_symbol_count": 1,
        "minimum_evidence_count": 2,
        "minimum_evidence_pass": True,
        "low_evidence_flag": False,
        "history_source": "persistent",
        "fixture_fallback_used": False,
        "indicator_count": 3,
        "caller_historical_match_count": 999,
        "caller_count_used_for_authority": False,
        "decision_time_cutoff": "1970-01-01T00:00:02+00:00",
        "canonical_memory_intelligence": True,
        "calculation_version": "canonical-persisted-memory-adapter.v1",
        "corpus_hash": "2" * 64,
        "source_episode_hashes": ["3" * 64],
        "source_snapshot_hashes": ["4" * 64],
        "storage_query_count": 1,
        "used_for_probability": False,
        "may_propose": False,
        "may_veto": False,
        "may_downgrade": False,
        "may_set_final_band": False,
        "may_execute": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "human_approval_required": True,
    }
    fake = SimpleNamespace(summary=summary)
    calls = {"count": 0}

    def fake_build(**kwargs):
        calls["count"] += 1
        assert kwargs["caller_historical_match_count"] == 999
        return fake

    monkeypatch.setattr(spine, "build_persisted_memory_evidence", fake_build)
    request = SimpleNamespace(historical_match_count=999)
    result, receipt = spine._canonical_build_persisted_memory_evidence(
        request,
        _snapshot(),
        ["RSI", "EMA", "VWAP"],
        2,
    )
    assert calls["count"] == 1
    assert result["historical_match_count"] == 3
    assert receipt.engine_id == "PERSISTED_INDICATOR_MEMORY"
    assert receipt.status == "completed"
    assert receipt.output_summary["storage_query_count"] == 1
    assert receipt.output_summary["caller_count_used_for_authority"] is False


def test_adapter_failure_does_not_fall_back_to_legacy_loop(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(spine, "build_persisted_memory_evidence", fail)
    summary, receipt = spine._canonical_build_persisted_memory_evidence(
        SimpleNamespace(historical_match_count=50),
        _snapshot(),
        ["RSI"],
        30,
    )
    assert summary["canonical_memory_intelligence"] is False
    assert summary["historical_match_count"] == 0
    assert summary["storage_query_count"] == 0
    assert summary["fixture_fallback_used"] is False
    assert receipt.status == "degraded"
    assert any("failed closed" in warning for warning in receipt.warnings)
