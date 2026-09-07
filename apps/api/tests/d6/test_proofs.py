from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

import pytest

from tradevision_d6 import ContractError, D6Engine, ProofVerifier, Status, binding_digest, sign_proof
from tradevision_d6.demo import DEMO_KEY, DEMO_KEY_ID


def use_proof(req, proof):
    return replace(req, proofs=(proof, req.proofs[1]))


def test_signature_and_issuer(engine, proven):
    p = proven.proofs[0]
    for edited, reason in ((replace(p, signature="0"*64), "PROOF_BAD_SIGNATURE"),
                           (replace(p, key_id="untrusted"), "PROOF_UNKNOWN_ISSUER"),
                           (replace(p, target_probability_lower_bound=D(".99")), "PROOF_BAD_SIGNATURE")):
        out = engine.evaluate(use_proof(proven, edited))
        assert out.status is Status.WAIT and reason in out.reasons
    out = D6Engine(ProofVerifier({})).evaluate(proven)
    assert out.status is Status.WAIT


@pytest.mark.parametrize("kind,reason", [
    ("expired", "PROOF_NOT_CURRENT"), ("future", "PROOF_NOT_CURRENT"),
    ("long_lifetime", "PROOF_LIFETIME_INVALID"), ("reversed_lifetime", "PROOF_LIFETIME_INVALID"),
    ("future_data", "PROOF_DATA_AFTER_ISSUE"), ("embargo", "PROOF_LOOKAHEAD_OR_EMBARGO"),
    ("old_validation", "PROOF_VALIDATION_TOO_OLD"), ("small_sample", "PROOF_INSUFFICIENT_SAMPLES"),
    ("low_confidence", "PROOF_CONFIDENCE_TOO_LOW"), ("method", "PROOF_METHOD_MISMATCH"),
    ("missing_check", "PROOF_REQUIRED_CHECKS_MISSING"), ("binding", "PROOF_BINDING_MISMATCH"),
])
def test_validation_gates(engine, proven, kind, reason):
    p, now = proven.proofs[0], proven.evaluation_at
    updates = {
        "expired": {"expires_at": now}, "future": {"issued_at": now+timedelta(seconds=1)},
        "long_lifetime": {"expires_at": now+timedelta(days=1)},
        "reversed_lifetime": {"expires_at": p.issued_at-timedelta(seconds=1)},
        "future_data": {"validation_data_end_at": now+timedelta(seconds=1)},
        "embargo": {"validation_data_end_at": now-timedelta(hours=1)},
        "old_validation": {"validation_data_end_at": now-timedelta(days=100)},
        "small_sample": {"independent_samples": 99},
        "low_confidence": {"confidence_level": D(".90")}, "method": {"method": "wrong"},
        "missing_check": {"passed_checks": p.passed_checks[1:]}, "binding": {"binding_digest": "f"*64},
    }[kind]
    edited = sign_proof(replace(p, **updates), DEMO_KEY)
    out = engine.evaluate(use_proof(proven, edited))
    assert out.status is Status.WAIT and reason in out.reasons


def test_risk_not_in_statistical_binding_but_in_decision_id(engine, proven):
    changed = replace(proven, risks=replace(proven.risks, event=D(".1")))
    assert binding_digest(changed, changed.plans[0]) == binding_digest(proven, proven.plans[0])
    a, b = engine.evaluate(proven), engine.evaluate(changed)
    assert b.long.proof_valid
    assert a.decision_id != b.decision_id
    assert b.trade_permission < a.trade_permission


def test_portfolio_checked_live_not_frozen_into_validation(engine, proven):
    changed = replace(proven, portfolio=replace(proven.portfolio, kill_switch=True))
    assert binding_digest(changed, changed.plans[0]) == binding_digest(proven, proven.plans[0])
    out = engine.evaluate(changed)
    assert out.long.proof_valid and out.status is Status.WAIT


def test_snapshot_and_plan_mutations_invalidate_proof(engine, proven):
    for changed in (
        replace(proven, snapshot=replace(proven.snapshot, data_revision="revised")),
        replace(proven, snapshot=replace(proven.snapshot, feature_digest="e"*64)),
        replace(proven, plans=(replace(proven.plans[0], target=D("107")), proven.plans[1])),
        replace(proven, policy=replace(proven.policy, revision="changed")),
        replace(proven, evidence=(replace(proven.evidence[0], long=D(".9")),)+proven.evidence[1:]),
    ):
        out = engine.evaluate(changed)
        assert out.status is Status.WAIT and "PROOF_BINDING_MISMATCH" in out.reasons


def test_key_validation_and_registry_copy(proven):
    with pytest.raises(ContractError): ProofVerifier({"bad": b"short"})
    with pytest.raises(ContractError): sign_proof(proven.proofs[0], b"short")
    keys = {DEMO_KEY_ID: DEMO_KEY}
    verifier = ProofVerifier(keys)
    keys.clear()
    assert not verifier.verify(proven, proven.plans[0], proven.proofs[0])


def test_validation_contracts(proven):
    p = proven.proofs[0]
    for changes in ({"passed_checks": p.passed_checks + p.passed_checks[:1]},
                    {"passed_checks": ("made_up_check",)}, {"confidence_level": D("0")},
                    {"signature": "not-a-signature"}, {"report_digest": "invalid"}):
        with pytest.raises(ContractError): replace(p, **changes)


@pytest.mark.parametrize("risk", ["event", "trap", "data_uncertainty", "liquidity", "execution"])
def test_signed_risk_domain_is_downward_closed(engine, proven, risk):
    p = proven.proofs[0]
    envelope = replace(p.valid_risk_envelope, **{risk: D(".1")})
    edited = sign_proof(replace(p, valid_risk_envelope=envelope), DEMO_KEY)
    req = use_proof(proven, edited)
    assert engine.evaluate(req).status is Status.PAPER_CANDIDATE
    outside = replace(req, risks=replace(req.risks, **{risk: D(".2")}))
    result = engine.evaluate(outside)
    assert result.status is Status.WAIT and f"PROOF_RISK_DOMAIN_{risk.upper()}" in result.reasons
    assert result.long_evidence == engine.evaluate(req).long_evidence
    assert result.short_evidence == engine.evaluate(req).short_evidence


def test_bad_risk_envelope_type(proven):
    with pytest.raises(ContractError): replace(proven.proofs[0], valid_risk_envelope=None)
