"""v2.00-repair dedicated gates: reconstructed grok_provider + quality gate.

Hermetic by design: direct builder calls with synthetic inputs, no shared DB,
no network. Guards the 03-09 reconstruction against future regressions.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.behavior import grok_provider
from app.behavior.jarvis_decision_quality_gate import build_decision_quality_gate_report

EVIDENCE = {
    "trade_vision_decision": {"final_trade_decision": "WAIT"},
    "indicator_snapshot": {"rsi14": 44, "vwap_position": "below_vwap"},
    "safety_summary": {"blocking_gates": []},
}


def _clear_grok_env(monkeypatch):
    for name in (
        "TRADEVISION_GROK_ENABLE_LIVE",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "XAI_API_KEY_1",
        "GROK_API_KEY_1",
    ):
        monkeypatch.delenv(name, raising=False)


# ---------------- grok_provider (G1-G8) ----------------

def test_recon_g1_provider_status_shape(monkeypatch):
    _clear_grok_env(monkeypatch)
    status = grok_provider.build_grok_provider_status()
    assert status["provider"] == "grok"
    assert status["status"] == "unavailable"
    assert status["mode"] == "live_disabled_safe_stub"
    assert len(status["key_slots"]) == 5
    assert status["api_key_source"] is None
    assert status["security"]["browser_password_login_supported"] is False
    assert status["passgrok_boundary"]["capture_modules_imported"] is False
    assert status["can_execute_orders"] is False
    assert status["can_override_no_trade"] is False
    assert status["can_override_risk"] is False


def test_recon_g2_live_review_disabled_path(monkeypatch):
    _clear_grok_env(monkeypatch)
    report = asyncio.run(grok_provider.build_grok_live_review_report(evidence_packet=EVIDENCE, execute=True))
    assert report["live_review_version"] == "jarvis-grok-live-review.v1.36"
    assert report["live_call_allowed"] is False
    assert report["live_call_performed"] is False
    assert report["safe_final_action"] == "TRADE_VISION_ONLY"


def test_recon_g3_live_review_mocked_success(monkeypatch):
    monkeypatch.setenv("TRADEVISION_GROK_ENABLE_LIVE", "true")
    monkeypatch.setenv("XAI_API_KEY", "xai_unit_test_key_slot")

    async def fake_call(*, evidence_packet, provider_status, outbound_bundle):
        return {
            "performed": True,
            "success": True,
            "status_code": 200,
            "latency_ms": 5,
            "slot": 1,
            "candidate_response": {
                "review_status": "valid",
                "agrees_with_trade_vision": True,
                "pattern_interpretation": "Below-VWAP wait structure.",
                "entry_guidance": "Wait for VWAP reclaim.",
                "risk_warning": "Do not trade while below VWAP.",
                "best_indicator_for_pattern": ["vwap_position", "rsi14"],
                "avoid_if": ["price remains below VWAP"],
                "confidence_comment": "External AI cannot boost confidence.",
                "final_action": "WAIT",
                "cited_evidence_keys": ["indicator_snapshot", "vwap_position", "rsi14", "safety_summary"],
            },
            "raw_text_preview": '{"final_action":"WAIT"}',
        }

    monkeypatch.setattr(grok_provider, "_call_grok_api", fake_call)
    report = asyncio.run(grok_provider.build_grok_live_review_report(evidence_packet=EVIDENCE, execute=True))
    assert report["provider_status"]["status"] == "ready"
    assert report["provider_status"]["api_key_source"] == "XAI_API_KEY"
    assert report["live_call_performed"] is True
    assert report["display_allowed"] is True
    assert report["review_intake"]["validation"]["schema_validation_passed"] is True
    assert report["review_intake"]["validation"]["hallucination_detected"] is False
    assert report["safe_final_action"] == "WAIT"


def test_recon_g4_outbound_bundle_dry_run():
    bundle = grok_provider.build_grok_outbound_review_bundle(EVIDENCE, grok_provider.build_grok_provider_status())
    assert bundle["dry_run_only"] is True
    assert bundle["network_call_allowed"] is False
    assert bundle["live_call_performed"] is False
    assert bundle["sanitization"]["secrets_included"] is False
    assert bundle["trade_allowed"] is False
    assert bundle["live_trading_blocked"] is True


def test_recon_g5_decision_room_gates():
    status = grok_provider.build_grok_provider_status()
    bundle = grok_provider.build_grok_outbound_review_bundle(EVIDENCE, status)
    sample = grok_provider.build_sample_grok_review_for_display(EVIDENCE)
    report = grok_provider.build_grok_decision_room_report(
        symbol="RELIANCE",
        provider_status=status,
        outbound_bundle=bundle,
        sample_review=sample,
        realtime_freshness={"freshness_state": "fresh", "force_wait": False, "safe_display_action": "display"},
        decision_quality={"quality_state": "research_review_ready"},
        trading_decision_output={"output_state": "watch_or_no_trade", "trade_plan": {}},
    )
    assert report["symbol"] == "RELIANCE"
    assert report["dry_run_only"] is True
    assert report["network_call_allowed"] is False
    assert report["confidence_boost_allowed"] is False
    assert report["grok_can_execute_orders"] is False
    assert {g["gate_id"] for g in report["gates"]} == {f"GDR-00{i}" for i in range(1, 7)}


def test_recon_g6_disabled_candidate_and_prompt():
    candidate = grok_provider._disabled_candidate(status={"status": "x"}, live_allowed=False)
    assert candidate["final_action"] == "TRADE_VISION_ONLY"
    assert isinstance(grok_provider._grok_system_prompt(), str)
    assert "JSON" in grok_provider._grok_system_prompt()


def test_recon_g7_no_credential_leakage(monkeypatch):
    # Key MATERIAL must never appear; the variable NAME appears only as
    # api_key_source attribution (required by the mocked-key contract).
    monkeypatch.setenv("XAI_API_KEY", "xai_super_secret_value_12345")
    status = grok_provider.build_grok_provider_status()
    bundle = grok_provider.build_grok_outbound_review_bundle(EVIDENCE, status)
    blob = json.dumps({"status": status, "bundle": bundle})
    assert "xai_super_secret_value_12345" not in blob
    assert status["api_key_source"] == "XAI_API_KEY"


def test_recon_g8_review_stub_and_sample():
    stub = grok_provider.build_grok_review_stub(EVIDENCE)
    assert stub["safe_final_action"] == "TRADE_VISION_ONLY"
    assert stub["live_trading_blocked"] is True
    summary = grok_provider.grok_summary_for_jarvis()
    assert summary["can_execute_orders"] is False
    assert summary["can_override_no_trade"] is False


# ---------------- quality gate (G9-G14) ----------------

def _clean_inputs():
    return dict(
        symbol="TVR",
        jarvis_room={"symbol": "TVR", "trade_allowed": False},
        external_ai_reliability={
            "reliability_version": "jarvis-external-ai-consensus-reliability.v1.07",
            "disagreement_detected": False,
            "low_evidence_detected": False,
            "stale_review_history": False,
            "record_count": 3,
        },
        verified_evidence={
            "certificate_version": "jarvis-verified-evidence-certificate.v1.08",
            "certificate_state": "verified_display_only",
            "external_ai_blocked_claims": [],
            "external_ai_missed_items": [],
            "daily_data_authority": {"daily_claim_requires_citation": False},
        },
        daily_authority={
            "authority_version": "jarvis-daily-verified-authority.v1.15",
            "authority_state": "verified",
            "daily_available": True,
            "weekly_available": True,
        },
        paper_execution_loop={
            "paper_loop_version": "jarvis-paper-execution-loop-gate.v1.21",
            "external_executor_handoff_allowed": False,
        },
        openalgo_handoff_gate={
            "handoff_gate_version": "jarvis-openalgo-handoff-gate.v1.20",
            "automatic_delivery_allowed": False,
        },
    )


def test_recon_g9_clean_inputs_research_ready():
    report = build_decision_quality_gate_report(**_clean_inputs())
    assert report["quality_gate_version"] == "jarvis-decision-quality-gate.v1.22"
    assert report["quality_state"] == "research_review_ready"
    assert report["quality_flags"] == []
    assert all(g["passed"] for g in report["gates"])
    assert report["review_display_allowed"] is True


def test_recon_g10_blocked_fixture_display_blocked():
    inputs = _clean_inputs()
    inputs["external_ai_reliability"].update(
        {"disagreement_detected": True, "low_evidence_detected": True, "stale_review_history": True}
    )
    inputs["verified_evidence"].update(
        {
            "certificate_state": "blocked",
            "external_ai_blocked_claims": [{"claim_id": "X"}],
            "external_ai_missed_items": [{"item_id": "Y"}],
        }
    )
    inputs["daily_authority"].update({"authority_state": "blocked", "daily_available": False})
    inputs["paper_execution_loop"].update({"external_executor_handoff_allowed": True})
    inputs["openalgo_handoff_gate"].update({"automatic_delivery_allowed": True})
    report = build_decision_quality_gate_report(**inputs)
    assert report["quality_state"] == "display_blocked"
    flag_ids = {f["flag_id"] for f in report["quality_flags"]}
    assert {
        "disagreement", "low_evidence", "stale_review_history", "unverified_daily_claim",
        "paper_loop_handoff_unexpected", "openalgo_auto_delivery_unexpected",
        "daily_authority_not_verified",
    } <= flag_ids
    gates = {g["gate_id"]: g for g in report["gates"]}
    assert gates["QUAL-002"]["passed"] is False
    assert gates["QUAL-009"]["passed"] is False
    assert gates["QUAL-011"]["passed"] is False
    assert gates["QUAL-012"]["passed"] is False


@pytest.mark.parametrize(
    "mutation,flag_id",
    [
        ({"external_ai_reliability": {"disagreement_detected": True}}, "disagreement"),
        ({"external_ai_reliability": {"low_evidence_detected": True}}, "low_evidence"),
        ({"external_ai_reliability": {"stale_review_history": True}}, "stale_review_history"),
        ({"paper_execution_loop": {"external_executor_handoff_allowed": True}}, "paper_loop_handoff_unexpected"),
        ({"openalgo_handoff_gate": {"automatic_delivery_allowed": True}}, "openalgo_auto_delivery_unexpected"),
    ],
)
def test_recon_g11_each_flag_fires_alone(mutation, flag_id):
    import copy

    inputs = _clean_inputs()
    for key, patch in mutation.items():
        merged = copy.deepcopy(inputs[key])
        merged.update(patch)
        inputs[key] = merged
    report = build_decision_quality_gate_report(**inputs)
    assert flag_id in {f["flag_id"] for f in report["quality_flags"]}


def test_recon_g12_safety_invariants_hold():
    report = build_decision_quality_gate_report(**_clean_inputs())
    assert report["trade_allowed"] is False
    assert report["order_routing_enabled"] is False
    assert report["live_trading_blocked"] is True
    assert report["decision_trust_allowed"] is False
    assert report["confidence_boost_allowed"] is False
