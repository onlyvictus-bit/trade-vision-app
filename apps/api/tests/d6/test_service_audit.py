from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import sqlite3

import pytest

from tradevision_d6 import (
    AuditConflict, AuditJournal, D6Engine, DecisionService, ProofVerifier, Status,
    canonical_json, decode_request, sign_proof,
)
from tradevision_d6.demo import DEMO_KEY
from tradevision_d6.service import SafetyViolation


def test_audit_idempotency_and_replay(engine, proven, tmp_path):
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    result = engine.evaluate(proven)
    assert journal.record(proven, result)
    assert not journal.record(proven, result)
    assert journal.count() == 1
    raw_input, raw_output = journal.read(result.decision_id)
    assert engine.evaluate(decode_request(raw_input)) == result
    assert raw_output == canonical_json(result)
    assert journal.read("absent") is None


def test_concurrent_identical_audit_writes(engine, proven, tmp_path):
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    decision = engine.evaluate(proven)
    with ThreadPoolExecutor(max_workers=8) as pool:
        inserts = list(pool.map(lambda _: journal.record(proven, decision), range(32)))
    assert sum(inserts) == 1 and journal.count() == 1


def test_conflicting_output_does_not_overwrite(engine, proven, tmp_path):
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    decision = engine.evaluate(proven)
    journal.record(proven, decision)
    tampered = replace(decision, reasons=("different",))
    with pytest.raises(AuditConflict): journal.record(proven, tampered)
    assert journal.read(decision.decision_id)[1] == canonical_json(decision)
    wrong_id = replace(decision, decision_id="f"*64)
    with pytest.raises(AuditConflict): journal.record(proven, wrong_id)
    with pytest.raises(ValueError): AuditJournal(":memory:")


def test_risk_updates_get_distinct_audit_events(engine, proven, tmp_path):
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    changed = replace(proven, risks=replace(proven.risks, event=D(".5")))
    journal.record(proven, engine.evaluate(proven))
    journal.record(changed, engine.evaluate(changed))
    assert journal.count() == 2


def test_service_runs_bounded_checks_and_audits(engine, proven, tmp_path):
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    service = DecisionService(engine, journal, replay_mode=True)
    a = service.evaluate(proven)
    b = service.evaluate_json(canonical_json(proven))
    assert a == b
    assert a.status is Status.PAPER_CANDIDATE
    assert a.audit_written and a.counterfactual_checks == 6 and a.evaluation_mode == "REPLAY"
    assert journal.count() == 1


def test_bad_json_and_bad_object_never_candidate(engine, tmp_path):
    service = DecisionService(engine, AuditJournal(tmp_path / "audit.sqlite3"), replay_mode=True)
    for result in (service.evaluate_json('{}'), service.evaluate({})):
        assert result.status is Status.WAIT and result.decision is None
        assert result.error_code == "INPUT_CONTRACT_INVALID"


def test_journal_failure_prevents_returning_candidate(engine, proven):
    class BrokenJournal:
        def record(self, *args): raise sqlite3.OperationalError("disk full")
    result = DecisionService(engine, BrokenJournal(), replay_mode=True).evaluate(proven)
    assert result.status is Status.WAIT and result.decision is None
    assert not result.audit_written and result.error_code == "EVALUATION_OR_AUDIT_FAILED"


def test_engine_failure_prevents_stale_approval(engine, proven, tmp_path):
    class BrokenEngine:
        def evaluate(self, request): raise RuntimeError("engine failed")
    result = DecisionService(BrokenEngine(), AuditJournal(tmp_path / "audit.sqlite3"), replay_mode=True).evaluate(proven)
    assert result.status is Status.WAIT and result.decision is None


def test_online_invariant_check_catches_risk_contaminating_direction(engine, proven, tmp_path):
    class BadEngine:
        def evaluate(self, request):
            out = engine.evaluate(request)
            return replace(out, long_evidence=D(".99")) if request.risks.event == 1 else out
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    result = DecisionService(BadEngine(), journal, replay_mode=True).evaluate(proven)
    assert result.status is Status.WAIT and result.error_code == "SAFETY_INVARIANT_FAILED"
    assert journal.count() == 0


def test_default_paper_service_rejects_backdating_and_demo_key(engine, proven, tmp_path):
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    for seconds in (-1, 6, 86400):
        service = DecisionService(engine, journal, clock=lambda: proven.evaluation_at+timedelta(seconds=seconds))
        result = service.evaluate(proven)
        assert result.error_code == "EVALUATION_TIME_UNTRUSTED" and result.status is Status.WAIT
    service = DecisionService(engine, journal, clock=lambda: proven.evaluation_at)
    assert service.evaluate(proven).error_code == "DEMO_PROOF_NOT_ALLOWED"
    assert journal.count() == 0


def test_paper_service_with_test_issuer_and_trusted_clock(proven, tmp_path):
    # The issuer here is a test double, not evidence about any market.
    secret = b"test-only-validator-key-with-no-real-research"
    proofs = tuple(sign_proof(replace(p, key_id="test-validator"), secret) for p in proven.proofs)
    req = replace(proven, proofs=proofs)
    engine = D6Engine(ProofVerifier({"test-validator": secret}))
    service = DecisionService(engine, AuditJournal(tmp_path / "audit.sqlite3"), clock=lambda: req.evaluation_at)
    result = service.evaluate(req)
    assert result.status is Status.PAPER_CANDIDATE and result.evaluation_mode == "PAPER"


def test_naive_clock_and_invalid_service_config(engine, proven, tmp_path):
    journal = AuditJournal(tmp_path / "audit.sqlite3")
    with pytest.raises(ValueError): DecisionService(engine, journal, replay_mode="false")
    service = DecisionService(engine, journal, clock=lambda: proven.evaluation_at.replace(tzinfo=None))
    assert service.evaluate(proven).error_code == "INPUT_CONTRACT_INVALID"


def test_every_safety_checker_branch(engine, proven):
    base = engine.evaluate(proven)
    denied = engine.evaluate(replace(proven, risks=replace(proven.risks, event=D("1"))))
    check = DecisionService._assert_nonincreasing
    variants = (
        replace(base, trade_permission=base.trade_permission+D(".01")),
        replace(base, long=replace(base.long, quality=D("1"))),
        replace(base, short=replace(base.short, eligible=True)),
        replace(base, selected_side=base.short.side),
    )
    for worse in variants:
        with pytest.raises(SafetyViolation): check(base, worse)
    fabricated = replace(denied, status=Status.PAPER_CANDIDATE)
    with pytest.raises(SafetyViolation): check(denied, fabricated)


@pytest.mark.parametrize("offset,code", [(5, "CANDIDATE_EXPIRED_BEFORE_DELIVERY"), (-1, "CLOCK_MOVED_BACKWARDS")])
def test_delivery_rechecks_clock_and_expiry(proven, tmp_path, offset, code):
    secret = b"test-only-validator-key-with-no-real-research"
    proofs = tuple(sign_proof(replace(p, key_id="test-validator"), secret) for p in proven.proofs)
    req = replace(proven, proofs=proofs)
    engine = D6Engine(ProofVerifier({"test-validator": secret}))
    times = iter((req.evaluation_at, req.evaluation_at+timedelta(seconds=offset)))
    service = DecisionService(engine, AuditJournal(tmp_path / "audit.sqlite3"), clock=lambda: next(times))
    result = service.evaluate(req)
    assert result.status is Status.WAIT and result.decision is None and result.error_code == code
    assert result.audit_written  # Audit records evaluation, not delivery or an order.
