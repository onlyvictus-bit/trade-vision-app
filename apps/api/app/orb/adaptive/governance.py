"""Local offline review attestations. No API route can create approval keys.

HMAC authenticates a local operator's review; it does NOT prove data provenance
or profitability. The data manifest and research procedure still need review.
Any source-code, selector, model, budget or universe change invalidates binding.
"""
from __future__ import annotations
import hashlib
import hmac
from pathlib import Path
from typing import Literal
from .contracts import Frozen, Policy, AccountLimits, canonical, digest
from .research import ProofReport


def code_fingerprint() -> str:
    root = Path(__file__).resolve().parent
    files = sorted([*root.glob("*.py"), *root.glob("*.json")])
    return digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


class ReviewedProof(Frozen):
    report: ProofReport
    reviewer: str
    reviewed_ns: int
    expires_ns: int
    review_phrase: Literal["I_REVIEWED_REAL_DATA_POLICY_AND_HOLDOUT"]
    signature: str


def validate_report(report: ProofReport) -> None:
    if digest(report.model_dump(mode="json", exclude={"proof_hash"})) != report.proof_hash:
        raise ValueError("PROOF_CONTENT_HASH_MISMATCH")
    if report.selected_policy.policy_hash != report.selected_policy_hash:
        raise ValueError("PROOF_SELECTED_POLICY_MISMATCH")
    if not report.development_dates or not report.holdout_dates or max(report.development_dates) >= min(report.holdout_dates):
        raise ValueError("INVALID_PROOF_DATE_PARTITION")
    if report.source_origin != "REAL_ATTESTED" or not report.promotion_eligible or report.blockers:
        raise ValueError("PROOF_NOT_ELIGIBLE_FOR_REVIEW")
    t, m = report.thresholds, report.holdout_metrics
    if len(report.development_dates) < t.minimum_development_dates or len(report.holdout_dates) < t.minimum_holdout_dates:
        raise ValueError("PROOF_DATE_SUPPORT_GATE_FAILED")
    if m.get("unknown_dates") != 0 or m.get("filled_entries", 0) < t.minimum_holdout_fills:
        raise ValueError("PROOF_OUTCOME_SUPPORT_GATE_FAILED")
    if m.get("lower_mean_bound") is None or m["lower_mean_bound"] <= t.minimum_lower_mean_budget_units:
        raise ValueError("PROOF_HOLDOUT_EDGE_GATE_FAILED")
    if not report.walk_forward:
        raise ValueError("MISSING_CHRONOLOGICAL_FOLDS")
    for fold in report.walk_forward:
        if not fold["train_dates"] or not fold["test_dates"] or max(fold["train_dates"]) >= min(fold["test_dates"]):
            raise ValueError("INVALID_WALK_FORWARD_FOLD")
        if set(fold["test_dates"]) & set(report.holdout_dates):
            raise ValueError("FINAL_HOLDOUT_USED_IN_DEVELOPMENT")
    if sum(bool(f["passed"]) for f in report.walk_forward)/len(report.walk_forward) < t.minimum_walk_forward_pass_rate:
        raise ValueError("PROOF_WALK_FORWARD_GATE_FAILED")


def sign_review(report: ProofReport, key: bytes, reviewer: str, reviewed_ns: int, expires_ns: int,
                phrase: str) -> ReviewedProof:
    validate_report(report)
    if report.code_hash != code_fingerprint():
        raise ValueError("CODE_CHANGED_SINCE_PROOF")
    if len(key) < 32 or not reviewer.strip() or expires_ns <= reviewed_ns:
        raise ValueError("INVALID_OPERATOR_REVIEW_CONFIGURATION")
    from .contracts import clock_ns
    if reviewed_ns <= clock_ns(max(report.holdout_dates), 930):
        raise ValueError("REVIEW_PRECEDES_HOLDOUT_COMPLETION")
    if phrase != "I_REVIEWED_REAL_DATA_POLICY_AND_HOLDOUT":
        raise ValueError("EXPLICIT_REVIEW_PHRASE_REQUIRED")
    payload = dict(report=report.model_dump(mode="json"), reviewer=reviewer.strip(),
                   reviewed_ns=reviewed_ns, expires_ns=expires_ns, review_phrase=phrase)
    signature = hmac.new(key, canonical(payload).encode(), hashlib.sha256).hexdigest()
    return ReviewedProof(**payload, signature=signature)


def verify_review(review: ReviewedProof, key: bytes, policy: Policy, limits: AccountLimits,
                  universe: tuple[str, ...], now_ns: int, session_date: str) -> str:
    validate_report(review.report)
    payload = review.model_dump(mode="json", exclude={"signature"})
    wanted = hmac.new(key, canonical(payload).encode(), hashlib.sha256).hexdigest()
    if len(key) < 32 or not hmac.compare_digest(wanted, review.signature):
        raise ValueError("PROOF_REVIEW_SIGNATURE_INVALID")
    if not review.reviewed_ns <= now_ns < review.expires_ns:
        raise ValueError("PROOF_REVIEW_NOT_CURRENT")
    report = review.report
    if report.code_hash != code_fingerprint() or report.selected_policy_hash != policy.policy_hash:
        raise ValueError("EXACT_CONTROLLER_CODE_OR_MODEL_PROOF_MISMATCH")
    if report.limits_hash != digest(limits) or report.universe != tuple(sorted(universe)):
        raise ValueError("PROOF_ACCOUNT_BUDGET_OR_UNIVERSE_MISMATCH")
    if max(report.holdout_dates) >= session_date:
        raise ValueError("PROOF_NOT_AVAILABLE_BEFORE_RESEARCH_SESSION")
    return report.proof_hash
