from __future__ import annotations

from ..models import (
    FinalProductionReadinessAudit,
    ReleaseReadinessEvidenceGate,
    ReleaseReadinessEvidenceReport,
    now_iso,
)
from . import final_release_audit


RELEASE_READINESS_EVIDENCE_VERSION = "tradevision-release-readiness-evidence.v1.69"


def build_release_readiness_evidence_report(
    *,
    audit: FinalProductionReadinessAudit | None = None,
    force_refresh: bool = False,
) -> ReleaseReadinessEvidenceReport:
    """Summarize final release evidence without adding release or trading authority."""
    final_audit = audit or final_release_audit.build_final_release_audit(force_refresh=force_refresh)
    safety_scan = final_audit.static_safety_scan
    manifest = final_audit.release_manifest
    missing_required_artifacts = [
        artifact.relative_path
        for artifact in manifest.artifacts
        if artifact.required and not artifact.present
    ]
    unsafe_release_flags = (
        final_audit.broker_credentials_present
        or final_audit.broker_order_created
        or final_audit.order_routing_enabled
        or not final_audit.live_trading_blocked
        or final_audit.live_trading_ready
        or manifest.contains_broker_credentials
        or manifest.contains_live_orders
        or manifest.order_routing_enabled
        or not manifest.live_trading_blocked
        or safety_scan.broker_credentials_present
        or safety_scan.broker_order_created
        or safety_scan.order_routing_enabled
        or not safety_scan.live_trading_blocked
    )
    gates = [
        _gate(
            "REL-EVID-001",
            "Final release audit is internally ready",
            final_audit.production_research_release_candidate and final_audit.fail_count == 0,
            (
                f"version={final_audit.audit_version}; pass={final_audit.pass_count}; "
                f"warn={final_audit.warn_count}; fail={final_audit.fail_count}"
            ),
        ),
        _gate(
            "REL-EVID-002",
            "Static safety scan is clean",
            safety_scan.passed and not safety_scan.findings,
            (
                f"version={safety_scan.scan_version}; scanned={safety_scan.scanned_file_count}; "
                f"findings={len(safety_scan.findings)}"
            ),
        ),
        _gate(
            "REL-EVID-003",
            "Release manifest is complete and secret-free",
            (
                not missing_required_artifacts
                and manifest.artifact_count == len(manifest.artifacts)
                and not manifest.contains_secrets
                and not manifest.contains_broker_credentials
                and not manifest.contains_live_orders
            ),
            (
                f"version={manifest.manifest_version}; release_id={manifest.release_id}; "
                f"artifacts={manifest.artifact_count}; missing={len(missing_required_artifacts)}"
            ),
        ),
        _gate(
            "REL-EVID-004",
            "Final audit evidence sources are aligned",
            (
                final_audit.release_manifest.release_id == manifest.release_id
                and final_audit.release_manifest.manifest_sha256 == manifest.manifest_sha256
                and final_audit.static_safety_scan.scan_version == safety_scan.scan_version
            ),
            "final audit, safety scan, and manifest are taken from one evidence snapshot",
        ),
        _gate(
            "REL-EVID-005",
            "Brokerless boundary is preserved",
            not unsafe_release_flags,
            "live blocked; routing disabled; no broker credentials; no broker orders",
        ),
        ReleaseReadinessEvidenceGate(
            gate_id="REL-EVID-006",
            name="Operator sign-off remains external and explicit",
            status="pass" if final_audit.operator_signoff_present else "warn",
            evidence=(
                "operator sign-off present"
                if final_audit.operator_signoff_present
                else "operator sign-off is required before deployment outside this automated report"
            ),
            blocks_evidence_ready=False,
        ),
        _gate(
            "REL-EVID-007",
            "Final audit cache policy is visible",
            final_release_audit.FINAL_AUDIT_CACHE_TTL_SECONDS >= 0,
            f"ttl_seconds={final_release_audit.FINAL_AUDIT_CACHE_TTL_SECONDS}",
            blocks=False,
        ),
    ]
    blocking_gate_ids = [
        gate.gate_id
        for gate in gates
        if gate.status == "fail" and gate.blocks_evidence_ready
    ]
    blocking_gate_ids.extend(
        gate.gate_id
        for gate in final_audit.gates
        if gate.status == "fail" and gate.blocks_release
    )
    blocking_gate_ids = sorted(set(blocking_gate_ids))
    ready = (
        final_audit.production_research_release_candidate
        and not blocking_gate_ids
        and safety_scan.passed
        and not missing_required_artifacts
        and not unsafe_release_flags
    )
    return ReleaseReadinessEvidenceReport(
        evidence_version=RELEASE_READINESS_EVIDENCE_VERSION,
        generated_at=now_iso(),
        target=final_audit.target,
        evidence_state="research_release_evidence_ready" if ready else "blocked",
        final_audit_version=final_audit.audit_version,
        final_audit_ready=final_audit.production_research_release_candidate,
        final_audit_fail_count=final_audit.fail_count,
        final_audit_warn_count=final_audit.warn_count,
        safety_scan_version=safety_scan.scan_version,
        safety_scan_passed=safety_scan.passed,
        safety_scan_finding_count=len(safety_scan.findings),
        manifest_version=manifest.manifest_version,
        release_id=manifest.release_id,
        manifest_sha256=manifest.manifest_sha256,
        manifest_artifact_count=manifest.artifact_count,
        required_artifacts_missing=missing_required_artifacts,
        blocking_gate_ids=blocking_gate_ids,
        gates=gates,
        cache_policy="final audit is cached briefly for repeated dashboard reads; force_refresh bypasses the cache",
        final_audit_cache_ttl_seconds=final_release_audit.FINAL_AUDIT_CACHE_TTL_SECONDS,
        evidence_sources=[
            "/api/v1/release/final-audit",
            "/api/v1/release/safety-scan",
            "/api/v1/release/candidate/current",
        ],
        operator_message=_operator_message(ready, blocking_gate_ids),
        research_release_candidate=ready,
        broker_credentials_present=False,
        broker_order_created=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        trade_allowed=False,
        can_execute_orders=False,
        can_export_to_openalgo=False,
        notes=[
            "This report refreshes release-readiness evidence only.",
            "It does not approve live broker trading, autonomous execution, or OpenAlgo order export.",
            "Operator deployment sign-off remains outside this automated report.",
        ],
    )


def _gate(
    gate_id: str,
    name: str,
    passed: bool,
    evidence: str,
    *,
    blocks: bool = True,
) -> ReleaseReadinessEvidenceGate:
    return ReleaseReadinessEvidenceGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "fail",
        evidence=evidence,
        blocks_evidence_ready=blocks and not passed,
    )


def _operator_message(ready: bool, blocking_gate_ids: list[str]) -> str:
    if ready:
        return "Research release evidence is aligned. Live trading remains blocked and still requires separate human deployment approval."
    return f"Release readiness evidence is blocked by: {', '.join(blocking_gate_ids) or 'unknown'}."
