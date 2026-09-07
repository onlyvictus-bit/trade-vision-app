"""Authentication and point-in-time checks for externally produced validation.

HMAC proves issuer possession of a key, not correctness of statistical assertions.
Never expose signing keys or the signing helper to a browser/untrusted signal model.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import hashlib
import hmac
from types import MappingProxyType
from typing import Mapping

from .codec import canonical_json, fingerprint
from .models import ContractError, REQUIRED_CHECKS, RISK_NAMES, Request, TradePlan, ValidationProof


def binding_digest(request: Request, plan: TradePlan) -> str:
    # Intentionally excludes runtime RiskVector and account state. These are
    # checked live and bound into the final request/decision digest. Binding to
    # exact risk equality can make proof validity NONMONOTONE in risk.
    return fingerprint({
        "binding_schema": "tradevision-d6-proof-v1",
        "snapshot": request.snapshot,
        "policy": request.policy,
        "evidence": request.evidence,
        "plan": plan,
    })


def sign_proof(proof: ValidationProof, secret: bytes) -> ValidationProof:
    """Trusted validator helper, not a mechanism for generating research evidence."""
    if type(secret) is not bytes or len(secret) < 32:
        raise ContractError("validation signing secret must contain at least 32 bytes")
    unsigned = replace(proof, signature="")
    sig = hmac.new(secret, canonical_json(unsigned).encode("utf-8"), hashlib.sha256).hexdigest()
    return replace(unsigned, signature=sig)


class ProofVerifier:
    def __init__(self, trusted_keys: Mapping[str, bytes]) -> None:
        keys = dict(trusted_keys)
        if not all(isinstance(k, str) and type(v) is bytes and len(v) >= 32 for k, v in keys.items()):
            raise ContractError("invalid trusted key registry")
        self._keys = MappingProxyType(keys)

    def verify(self, request: Request, plan: TradePlan,
               proof: ValidationProof) -> tuple[str, ...]:
        reasons: list[str] = []
        key = self._keys.get(proof.key_id)
        if key is None:
            reasons.append("PROOF_UNKNOWN_ISSUER")
        else:
            expected = sign_proof(proof, key).signature
            if not hmac.compare_digest(expected, proof.signature):
                reasons.append("PROOF_BAD_SIGNATURE")
        if proof.side is not plan.side or proof.binding_digest != binding_digest(request, plan):
            reasons.append("PROOF_BINDING_MISMATCH")
        now, policy = request.evaluation_at, request.policy
        if not proof.issued_at <= now < proof.expires_at:
            reasons.append("PROOF_NOT_CURRENT")
        if proof.expires_at <= proof.issued_at or (proof.expires_at - proof.issued_at) > timedelta(seconds=policy.max_proof_lifetime_seconds):
            reasons.append("PROOF_LIFETIME_INVALID")
        if proof.validation_data_end_at > proof.issued_at:
            reasons.append("PROOF_DATA_AFTER_ISSUE")
        if proof.validation_data_end_at > request.snapshot.bar_opened_at - timedelta(seconds=policy.validation_embargo_seconds):
            reasons.append("PROOF_LOOKAHEAD_OR_EMBARGO")
        if now - proof.validation_data_end_at > timedelta(seconds=policy.max_validation_age_seconds):
            reasons.append("PROOF_VALIDATION_TOO_OLD")
        if proof.independent_samples < policy.minimum_validation_samples:
            reasons.append("PROOF_INSUFFICIENT_SAMPLES")
        # A downward-closed validated domain preserves monotonicity. Exact
        # equality to a previous runtime risk vector would not. The trusted
        # issuer must validate its probability assertion across this envelope.
        for name in RISK_NAMES:
            if getattr(request.risks, name) > getattr(proof.valid_risk_envelope, name):
                reasons.append(f"PROOF_RISK_DOMAIN_{name.upper()}")
        if proof.confidence_level < policy.minimum_validation_confidence:
            reasons.append("PROOF_CONFIDENCE_TOO_LOW")
        if proof.method != policy.validation_method:
            reasons.append("PROOF_METHOD_MISMATCH")
        if set(REQUIRED_CHECKS) - set(proof.passed_checks):
            reasons.append("PROOF_REQUIRED_CHECKS_MISSING")
        return tuple(reasons)
