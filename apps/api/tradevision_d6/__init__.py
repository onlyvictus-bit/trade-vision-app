"""Paper-only D6 reference engine. Start with README.md and ARCHITECTURE.md."""
from .audit import AuditConflict, AuditJournal
from .codec import canonical_json, decode_request, fingerprint
from .engine import D6Engine
from .models import (
    ContractError, Costs, Decision, DirectionalEvidence, GroupSpec, Horizon,
    Policy, Portfolio, Request, RiskVector, Side, Snapshot, SourceSpec, Status,
    StressScenario, TradePlan, ValidationProof,
)
from .proofs import ProofVerifier, binding_digest, sign_proof
from .service import DecisionService, ServiceResult

__all__ = [
    "AuditConflict", "AuditJournal", "ContractError", "Costs", "D6Engine",
    "Decision", "DecisionService", "DirectionalEvidence", "GroupSpec", "Horizon",
    "Policy", "Portfolio", "ProofVerifier", "Request", "RiskVector", "ServiceResult",
    "Side", "Snapshot", "SourceSpec", "Status", "StressScenario", "TradePlan",
    "ValidationProof", "binding_digest", "canonical_json", "decode_request",
    "fingerprint", "sign_proof",
]
