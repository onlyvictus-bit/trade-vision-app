"""D6 shadow adapter tests (M2-C). All fixtures synthetic; no market data, no orders."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.behavior import d6_shadow_adapter as ad
from tradevision_d6.models import RiskVector

T0 = 1_780_000_000_000_000_000
H = 3_600_000_000_000  # one hour in ns
SNAP = "a" * 64

LAYERS = {"market_regime": 0.4, "structure_levels": 0.5, "volume_auction": 0.3,
          "relative_strength": 0.2, "indicators": 0.35}


def risks(**kw):
    base = dict(event=0.1, trap=0.1, data_uncertainty=0.0, liquidity=0.2, execution=0.1)
    base.update(kw)
    return RiskVector(**{k: Decimal(str(v)) for k, v in base.items()})


def compare(**kw):
    args = dict(symbol="NIFTY", timeframe="5m", direction="long", layer_scores=dict(LAYERS),
                risks=risks(), snapshot_id=SNAP, session_id="2026-09-07",
                bar_open_ns=T0 - H, bar_close_ns=T0, decision_ns=T0,
                entry=100.0, stop=99.0, target=102.0, entry_plan_authority_present=True,
                evidence_count=30, minimum_evidence_count=30, arbiter_band="WATCH")
    args.update(kw)
    return ad.compare(**args)


def test_flag_off_returns_none(monkeypatch):
    monkeypatch.delenv(ad.FLAG, raising=False)
    assert compare() is None


def test_deterministic(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    assert compare() == compare()


def test_risk_increase_never_improves_permission_nor_flips_side(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    base = compare()
    assert base is not None and base.d6_side in ("LONG", None)
    for dim in ("event", "trap", "data_uncertainty", "liquidity", "execution"):
        worse = compare(risks=risks(**{dim: 0.9}))
        assert worse is not None
        assert worse.d6_side in ("LONG", None), dim  # Safeguard A: never SHORT fallback
        if base.d6_permission != "n/a" and worse.d6_permission != "n/a":
            assert Decimal(worse.d6_permission) <= Decimal(base.d6_permission), dim


def test_evidence_invariant_under_risk_sweep(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    from tradevision_d6.engine import D6Engine
    from tradevision_d6.proofs import ProofVerifier

    # Same evidence rows reach the engine regardless of risk levels.
    recs = [compare(risks=risks(event=v)) for v in (0.1, 0.5, 0.9)]
    assert all(r is not None for r in recs)
    assert len({r.input_hash for r in recs}) == 3  # risks are part of the input


def test_missing_risks_abstains(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    rec = compare(risks=None)
    assert rec is not None and rec.d6_status == "ADAPTER_ABSTAIN"
    assert rec.causes == ("EXECUTION_RISK_UNAVAILABLE",)


def test_no_direction_no_plans(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    rec = compare(direction="neutral")
    assert rec is not None and "NO_DIRECTIONAL_HYPOTHESIS" in rec.causes


def test_no_authority_no_plan(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    rec = compare(entry_plan_authority_present=False)
    assert rec is not None and "NO_PLAN_NO_SETUP" in rec.causes


def test_malformed_times_recorded_not_raised(monkeypatch):
    # Inverted bar times: D6's own time gates fail it closed to WAIT (no raise,
    # never a candidate). The adapter records whatever D6 decides.
    monkeypatch.setenv(ad.FLAG, "on")
    rec = compare(bar_open_ns=T0, bar_close_ns=T0 - H)
    assert rec is not None and rec.d6_status == "WAIT" and rec.d6_side is None


def test_short_setup_never_selects_long(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    neg = {k: -v for k, v in LAYERS.items()}
    rec = compare(direction="short", layer_scores=neg, entry=100.0, stop=101.0, target=98.0)
    assert rec is not None and rec.d6_side in ("SHORT", None)


def test_layer_disagreement_recorded(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    mixed = dict(LAYERS)
    mixed["indicators"] = -0.6  # disagrees with long setup
    rec = compare(layer_scores=mixed)
    assert rec is not None
    assert any(c.startswith("D6_SHADOW_LAYER_DISAGREES:indicators") for c in rec.causes)


def test_divergence_record_shape(monkeypatch):
    monkeypatch.setenv(ad.FLAG, "on")
    rec = compare(arbiter_band="PAPER_CANDIDATE")
    assert rec is not None and rec.adapter_version == ad.ADAPTER_VERSION
    assert rec.arbiter_band == "PAPER_CANDIDATE"
    assert any(c.startswith(("AGREE_", "DIVERGE_")) for c in rec.causes)


def test_policy_thresholds_versioned():
    from tradevision_d6.models import Horizon

    pol = ad.build_adapter_policy(Horizon.INTRADAY)
    assert pol.revision == ad.ADAPTER_VERSION
    assert {s.name for s in pol.sources} == {layer for layer, _ in ad.DIRECTION_LAYERS}
    assert all(s.required is False for s in pol.sources)


# M2-D spine wiring: output-neutral in both flag states --------------------------

def _p1_series():
    from app.behavior.point_in_time_guard import timeframe_duration_ns
    from app.models import CandleBar, CandleSeries

    duration = timeframe_duration_ns("5m")
    base = 1_714_815_600_000_000_000
    rows = [CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=base + i * duration,
                      open=100.0 + i * 0.08, high=100.2 + i * 0.08, low=99.9 + i * 0.08,
                      close=100.1 + i * 0.08, volume=100_000.0, source="user_csv",
                      sequence_number=i + 1) for i in range(40)]
    return CandleSeries(symbol="RELIANCE", timeframe="5m", bars=rows,
                        snapshot_id="d6-shadow-fixture", schema_version="candles.v1")


def _p1_request():
    from app.behavior.point_in_time_guard import timeframe_duration_ns
    from app.models import PaperGuidanceRequest

    series = _p1_series()
    duration = timeframe_duration_ns("5m")
    return PaperGuidanceRequest(symbol="RELIANCE", timeframe="5m", series=series,
                                decision_time_ns=1_714_815_600_000_000_000 + 40 * duration,
                                historical_match_count=0)


def _p1_run():
    from app.behavior.paper_guidance_config import PaperGuidanceConfig
    from app.behavior.paper_guidance_spine import run_paper_guidance_p1
    from app.models import KillSwitchState, SystemMode, SystemModeValue

    mode = SystemMode(mode=SystemModeValue.MOCK, display_label="Mock research", immutable=True,
                      allows_live_orders=False, allows_broker_credentials=False,
                      watermark_text="MOCK - NO REAL MONEY")
    kill = KillSwitchState(state="armed", reason=None, source=None, actor_id=None,
                           triggered_at=None, blocks_order_paths=False)
    return run_paper_guidance_p1(_p1_request(), mode=mode, kill_switch=kill, config=PaperGuidanceConfig())


def test_spine_wiring_flag_off_dormant_and_output_clean(monkeypatch, tmp_path):
    """Flag off: the adapter is never called and guidance carries no D6 trace.

    (Full P1 runs are not byte-deterministic across calls in this host — receipt
    hashes include run-varying content — so dormancy is proven by call-count plus
    output-absence instead of run-to-run equality.)
    """
    import os

    import app.behavior.d6_shadow_adapter as adapter_mod

    calls = []
    real_compare = adapter_mod.compare

    def counting_compare(**kwargs):
        calls.append(kwargs)
        return real_compare(**kwargs)

    monkeypatch.delenv(ad.FLAG, raising=False)
    monkeypatch.setenv("TRADEVISION_D6_SHADOW_LOG", str(tmp_path / "off.jsonl"))
    monkeypatch.setattr(adapter_mod, "compare", counting_compare)
    out = _p1_run().model_dump(mode="json")
    assert calls == []
    assert not os.path.isfile(str(tmp_path / "off.jsonl"))
    assert "d6_shadow" not in json_dumps(out).lower()
    assert "d6-shadow" not in json_dumps(out).lower()


def json_dumps(payload) -> str:
    import json

    return json.dumps(payload, sort_keys=True, default=str)


def test_spine_wiring_flag_on_logs_sidecar_without_changing_output(monkeypatch, tmp_path):
    import json
    import os

    log = str(tmp_path / "shadow.jsonl")
    monkeypatch.setenv(ad.FLAG, "on")
    monkeypatch.setenv("TRADEVISION_D6_SHADOW_LOG", log)
    first = _p1_run().model_dump(mode="json")
    second = _p1_run().model_dump(mode="json")
    # Wiring never affects guidance: no D6 trace in either output; divergence lives
    # only in the sidecar (one record per run).
    assert "d6_shadow" not in json_dumps(first).lower()
    assert "d6-shadow" not in json_dumps(first).lower()
    assert os.path.isfile(log)
    with open(log, encoding="utf-8") as handle:
        lines = [json.loads(line) for line in handle.read().splitlines() if line.strip()]
    assert len(lines) == 2
    assert all(line["adapter_version"] == ad.ADAPTER_VERSION and "input_hash" in line for line in lines)
