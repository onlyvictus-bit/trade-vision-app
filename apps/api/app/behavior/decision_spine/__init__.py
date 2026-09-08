"""Canonical Decision Spine foundations.

This package starts with authority and Stage-2 evidence-integrity contracts.
It intentionally does not expose execution authority or create a second final
trading decision path.
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
    "INTEGRITY_VERSION",
    "Availability",
    "EngineIntegrityState",
    "EvidenceObservation",
    "SourceMode",
    "Stage2IntegrityReport",
    "build_stage2_integrity_report",
]
