from __future__ import annotations

from typing import Any

from .contracts import DerivativesContext, EvidenceRelation, ScenarioAssessment, digest


def v173_payload_overlay(context: DerivativesContext, payload: dict[str, Any], *, expiry_day: bool | None = None) -> dict[str, Any]:
    """Pure adapter into existing ExecutionEventOiRiskRequest-shaped payload.

    It never overwrites caller fields with None and does not instantiate the
    repo model, keeping this module dependency-light and easy to unit test.
    """
    out = dict(payload)
    out["options_context_status"] = {
        "AVAILABLE": "available", "PARTIAL": "partial", "UNAVAILABLE": "unavailable", "STALE": "partial"
    }[context.status]
    mapping = {
        "expected_move_pct": context.iv_horizon_expected_move_pct or context.atm_straddle_expected_move_pct,
        "max_pain": context.max_pain,
        "call_gamma_wall": context.call_gamma_wall.strike if context.call_gamma_wall else None,
        "put_gamma_wall": context.put_gamma_wall.strike if context.put_gamma_wall else None,
        "oi_concentration_pct": context.oi_concentration_pct,
        "iv_percentile": context.iv_percentile,
        "iv_skew": context.skew_25d_pct,
    }
    for key, value in mapping.items():
        if value is not None:
            out[key] = value
    if expiry_day is not None:
        out["expiry_day"] = expiry_day
    return out


def afre_capability_payloads(context: DerivativesContext, assessment: ScenarioAssessment, *, ttl_seconds: int = 30) -> tuple[dict[str, Any], ...]:
    """Create AFRE Capability-compatible dicts without importing AFRE contracts."""
    expires_ns = context.as_of_ns + ttl_seconds * 1_000_000_000
    rows: list[dict[str, Any]] = []
    base_hash = digest({"context": context.context_hash, "assessment": assessment.model_dump(mode="json")})
    valid = context.status == "AVAILABLE"
    rows.append({
        "name": "DERIVATIVES_CONTEXT_VALID",
        "available_ns": context.as_of_ns,
        "expires_ns": expires_ns,
        "status": "VALID" if valid else "BLOCKED",
        "evidence_hash": base_hash,
        "blocks_new_entry": context.status in {"STALE", "UNAVAILABLE"},
        "reason": "fresh canonical derivatives context" if valid else f"derivatives status={context.status}",
    })
    if assessment.relation in {EvidenceRelation.CONFLICT, EvidenceRelation.BLOCK}:
        rows.append({
            "name": "DERIVATIVES_SCENARIO_CONFLICT",
            "available_ns": assessment.as_of_ns,
            "expires_ns": expires_ns,
            "status": "VALID",
            "evidence_hash": digest({"base": base_hash, "relation": assessment.relation.value}),
            "blocks_new_entry": assessment.relation == EvidenceRelation.BLOCK or assessment.public_ticket_cap == "WAIT",
            "reason": ";".join(assessment.reason_codes)[:300],
        })
    if assessment.relation == EvidenceRelation.SUPPORT:
        rows.append({
            "name": "DERIVATIVES_SCENARIO_SUPPORT",
            "available_ns": assessment.as_of_ns,
            "expires_ns": expires_ns,
            "status": "VALID",
            "evidence_hash": digest({"base": base_hash, "relation": "SUPPORT"}),
            "blocks_new_entry": False,
            "reason": ";".join(assessment.support_families)[:300],
        })
    return tuple(rows)


def typed_afre_capabilities(context: DerivativesContext, assessment: ScenarioAssessment, *, ttl_seconds: int = 30):
    """Optional strongly-typed bridge when loaded inside the Trade Vision repo."""
    from ..adaptive.contracts import Capability
    return tuple(Capability.model_validate(x) for x in afre_capability_payloads(context, assessment, ttl_seconds=ttl_seconds))
