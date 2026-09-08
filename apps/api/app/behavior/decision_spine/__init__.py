"""Canonical Decision Spine contracts.

The package contains authority, Stage-2 evidence-integrity and canonical
DecisionContext contracts. It intentionally does not expose execution authority
or create a second final trading decision path.
"""

from .authority_registry import (
    ENGINE_AUTHORITIES,
    FINAL_BAND_AUTHORITY,
    REGISTRY_VERSION,
    EngineAuthority,
    EngineClassification,
    all_engine_authorities,
    authority_manifest,
    get_engine_authority,
    validate_authority_registry,
)
from .decision_context import (
    CANONICAL_EVIDENCE_FIELDS,
    DECISION_CONTEXT_VERSION,
    DecisionContext,
    DecisionContextError,
    DecisionIdentity,
    DecisionProvenance,
    EvidenceBlock,
    InputIntegrity,
    IntegrityState,
    build_decision_context,
    unavailable_evidence,
)
from .stage2_integrity import (
    INTEGRITY_VERSION,
    Availability,
    EngineIntegrityState,
    EvidenceObservation,
    SourceMode,
    Stage2IntegrityReport,
    build_stage2_integrity_report,
)

__all__ = [
    "ENGINE_AUTHORITIES",
    "FINAL_BAND_AUTHORITY",
    "REGISTRY_VERSION",
    "EngineAuthority",
    "EngineClassification",
    "all_engine_authorities",
    "authority_manifest",
    "get_engine_authority",
    "validate_authority_registry",
    "CANONICAL_EVIDENCE_FIELDS",
    "DECISION_CONTEXT_VERSION",
    "DecisionContext",
    "DecisionContextError",
    "DecisionIdentity",
    "DecisionProvenance",
    "EvidenceBlock",
    "InputIntegrity",
    "IntegrityState",
    "build_decision_context",
    "unavailable_evidence",
    "INTEGRITY_VERSION",
    "Availability",
    "EngineIntegrityState",
    "EvidenceObservation",
    "SourceMode",
    "Stage2IntegrityReport",
    "build_stage2_integrity_report",
]
