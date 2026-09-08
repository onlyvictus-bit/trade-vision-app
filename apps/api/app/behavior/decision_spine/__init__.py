"""Canonical Decision Spine contracts.

The package contains authority, Stage-2 evidence-integrity, canonical
DecisionContext, deterministic Paper Guidance context-adapter contracts, and
M3.1's authority-free D2 feature substrate. It intentionally does not expose
execution authority or create a second final trading decision path.
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
from .paper_guidance_decision_context_adapter import (
    CANONICAL_FIELD_BINDINGS,
    PAPER_GUIDANCE_CONTEXT_ADAPTER_VERSION,
    CanonicalFieldBinding,
    build_canonical_stage2_observations,
    build_paper_guidance_decision_context,
    decision_context_audit_summary,
)
from .snapshot_feature_kernel import (
    DEFAULT_AVERAGE_RANGE_WINDOWS,
    DEFAULT_VOLUME_WINDOWS,
    SNAPSHOT_FEATURE_KERNEL_VERSION,
    AverageRangeWindow,
    KernelBuildAudit,
    KernelIdentity,
    KernelVectors,
    SnapshotFeatureKernel,
    SnapshotFeatureKernelError,
    VolumeWindow,
    build_snapshot_feature_kernel,
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
    "CANONICAL_FIELD_BINDINGS",
    "PAPER_GUIDANCE_CONTEXT_ADAPTER_VERSION",
    "CanonicalFieldBinding",
    "build_canonical_stage2_observations",
    "build_paper_guidance_decision_context",
    "decision_context_audit_summary",
    "DEFAULT_AVERAGE_RANGE_WINDOWS",
    "DEFAULT_VOLUME_WINDOWS",
    "SNAPSHOT_FEATURE_KERNEL_VERSION",
    "AverageRangeWindow",
    "KernelBuildAudit",
    "KernelIdentity",
    "KernelVectors",
    "SnapshotFeatureKernel",
    "SnapshotFeatureKernelError",
    "VolumeWindow",
    "build_snapshot_feature_kernel",
    "INTEGRITY_VERSION",
    "Availability",
    "EngineIntegrityState",
    "EvidenceObservation",
    "SourceMode",
    "Stage2IntegrityReport",
    "build_stage2_integrity_report",
]
