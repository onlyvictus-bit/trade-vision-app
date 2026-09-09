from __future__ import annotations

from types import SimpleNamespace

from app.behavior.decision_spine import canonical_persisted_memory_adapter as adapter


NOW = 2_000_000_000


def _record(
    history_id: str,
    *,
    indicator_id: str,
    decision_time_ns: int = 1_000_000_000,
    signal_time_ns: int = 1_000_000_000,
    session_phase: str = "open",
    regime_id: str = "trend",
    snapshot_hash: str = "a" * 64,
    created_at: str = "1970-01-01T00:00:01+00:00",
    complete: bool = True,
    counted: bool = True,
    no_future_leakage: bool = True,
    missing_mask=(),
):
    return SimpleNamespace(
        history_id=history_id,
        symbol="RELIANCE",
        indicator_id=indicator_id,
        timeframe="5m",
        decision_time_ns=decision_time_ns,
        signal_time_ns=signal_time_ns,
        session_phase=session_phase,
        regime_id=regime_id,
        source_snapshot_hash=snapshot_hash,
        source_snapshot_id="snap-1",
        created_at=created_at,
        counted_in_reliability=counted,
        no_future_leakage=no_future_leakage,
        missing_mask=missing_mask,
        label=SimpleNamespace(label_status="complete" if complete else "pending"),
    )


def _install_fake_records(monkeypatch, records):
    by_id = {record.history_id: record for record in records}

    class FakeHistoryRecord:
        @staticmethod
        def model_validate_json(value):
            return by_id[value]

    monkeypatch.setattr(adapter, "IndicatorSignalHistoryRecord", FakeHistoryRecord)
    calls = {"count": 0}

    def fake_load_batch(**kwargs):
        calls["count"] += 1
        return [{"history_json": record.history_id} for record in records]

    monkeypatch.setattr(adapter, "_load_batch", fake_load_batch)
    return calls


def test_correlated_indicator_rows_collapse_to_one_independent_episode(monkeypatch):
    records = [
        _record("rsi", indicator_id="RSI_14"),
        _record("ema", indicator_id="EMA_20"),
        _record("vwap", indicator_id="VWAP"),
    ]
    calls = _install_fake_records(monkeypatch, records)
    evidence = adapter.build_persisted_memory_evidence(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=NOW,
        indicator_ids=["RSI_14", "EMA_20", "VWAP"],
        minimum_evidence_count=2,
    )
    assert calls["count"] == 1
    assert evidence.query_count == 1
    assert evidence.complete_record_count == 3
    assert evidence.independent_episode_count == 1
    assert evidence.summary["historical_match_count"] == 1
    assert evidence.summary["minimum_evidence_pass"] is False


def test_distinct_causal_snapshots_count_as_distinct_episodes(monkeypatch):
    records = [
        _record("a", indicator_id="RSI_14", snapshot_hash="a" * 64),
        _record(
            "b",
            indicator_id="RSI_14",
            decision_time_ns=1_500_000_000,
            signal_time_ns=1_500_000_000,
            snapshot_hash="b" * 64,
            created_at="1970-01-01T00:00:01.5+00:00",
        ),
    ]
    _install_fake_records(monkeypatch, records)
    evidence = adapter.build_persisted_memory_evidence(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=NOW,
        indicator_ids=["RSI_14"],
        minimum_evidence_count=2,
    )
    assert evidence.independent_episode_count == 2
    assert evidence.summary["minimum_evidence_pass"] is True


def test_noncausal_and_incomplete_records_are_excluded(monkeypatch):
    records = [
        _record("good", indicator_id="RSI_14"),
        _record("pending", indicator_id="RSI_14", complete=False, snapshot_hash="b" * 64),
        _record("leak", indicator_id="RSI_14", no_future_leakage=False, snapshot_hash="c" * 64),
        _record(
            "future-created",
            indicator_id="RSI_14",
            snapshot_hash="d" * 64,
            created_at="2100-01-01T00:00:00+00:00",
        ),
    ]
    _install_fake_records(monkeypatch, records)
    evidence = adapter.build_persisted_memory_evidence(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=NOW,
        indicator_ids=["RSI_14"],
        minimum_evidence_count=1,
    )
    assert evidence.complete_record_count == 1
    assert evidence.excluded_record_count == 3
    assert evidence.independent_episode_count == 1


def test_adapter_is_zero_authority_and_corpus_hash_is_deterministic(monkeypatch):
    records = [_record("a", indicator_id="RSI_14")]
    _install_fake_records(monkeypatch, records)
    one = adapter.build_persisted_memory_evidence(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=NOW,
        indicator_ids=["RSI_14"],
        minimum_evidence_count=1,
        caller_historical_match_count=999,
    )
    two = adapter.build_persisted_memory_evidence(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=NOW,
        indicator_ids=["RSI_14"],
        minimum_evidence_count=1,
        caller_historical_match_count=999,
    )
    assert one.corpus_hash == two.corpus_hash
    assert one.summary["caller_count_used_for_authority"] is False
    assert one.summary["used_for_probability"] is False
    assert one.summary["may_propose"] is False
    assert one.summary["may_veto"] is False
    assert one.summary["may_downgrade"] is False
    assert one.summary["may_set_final_band"] is False
    assert one.summary["may_execute"] is False
    assert one.summary["trade_allowed"] is False
    assert one.summary["order_routing_enabled"] is False
    assert one.summary["live_trading_blocked"] is True
    assert one.summary["human_approval_required"] is True
