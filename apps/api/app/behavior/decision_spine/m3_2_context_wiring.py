from __future__ import annotations

"""M3.2-F wiring helpers for Stage2IntegrityReport -> DecisionContext.

These helpers only transport canonical context receipts. They do not execute D6
or alter final-band compatibility inputs.
"""

from typing import Any, Sequence

from .canonical_context_world import CanonicalContextWorld, build_context_receipts
from .stage2_integrity import Availability, EvidenceObservation, SourceMode

M32_CONTEXT_ENGINE_IDS = frozenset({"SESSION_MEMORY","INDEX_CONTEXT","SECTOR_CONTEXT","RELATIVE_STRENGTH","MARKET_REGIME"})


def build_m32_stage2_observations(world: CanonicalContextWorld) -> tuple[EvidenceObservation, ...]:
    observations=[]
    for receipt in build_context_receipts(world):
        summary=receipt.output_summary
        status={"completed":Availability.AVAILABLE,"degraded":Availability.DEGRADED}.get(receipt.status,Availability.DEGRADED)
        reasons=tuple(str(x) for x in summary.get("missing_facts",()) if str(x))
        if status is not Availability.AVAILABLE and not reasons:
            reasons=(f"{receipt.engine_id} canonical context availability is {summary.get('canonical_availability','DEGRADED')}.",)
        observations.append(EvidenceObservation(
            engine_id=receipt.engine_id,
            source_snapshot_hash=receipt.source_snapshot_hash,
            availability=status,
            source_mode=SourceMode.VERIFIED_SNAPSHOT,
            identity_match=True,
            used_for_probability=False,
            neutral_default_substituted=False,
            final_band_claimed=False,
            future_leakage_detected=False,
            explanation_only=True,
            unavailable_reasons=reasons,
            notes=tuple(receipt.warnings),
        ))
    return tuple(sorted(observations,key=lambda x:x.engine_id))


def merge_m32_context_receipts(existing: Sequence[Any], world: CanonicalContextWorld) -> tuple[Any, ...]:
    """Replace only the five deferred M3.2 context slots with canonical receipts.

    Duplicate non-M3.2 engines remain an error in Stage2. Existing M3.2 legacy
    receipts are removed rather than coexisting with canonical replacements.
    """
    retained=[x for x in existing if str(getattr(x,"engine_id","")).upper() not in M32_CONTEXT_ENGINE_IDS]
    merged=retained+list(build_context_receipts(world))
    return tuple(sorted(merged,key=lambda x:str(getattr(x,"engine_id","")).upper()))
