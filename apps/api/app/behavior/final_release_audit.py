from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from threading import RLock
from uuid import uuid4

from ..models import (
    FinalProductionReadinessAudit,
    FinalReleaseGate,
    ReleaseArtifactEntry,
    ReleaseCandidateManifest,
    StaticSafetyScanFinding,
    StaticSafetyScanReport,
    now_iso,
)
from ..state import CAPABILITIES
from .deployment_recovery import deployment_readiness, deployment_smoke
from .red_team_final_gate import build_tv_prod_red_001_report
from .transport_resilience import build_resilience_report
from .transport_security import build_security_posture, build_threat_report


AUDIT_VERSION = "tradevision-final-release-audit.v1.68"
SCAN_VERSION = "tradevision-static-safety-scan.v0.59"
MANIFEST_VERSION = "tradevision-release-candidate-manifest.v0.59"
RELEASE_SCOPE = (
    "Production-ready brokerless research, replay, simulation, evidence, and guarded "
    "external-review stack. Live broker execution and autonomous trading remain excluded."
)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
FINAL_AUDIT_CACHE_TTL_SECONDS = 2.0
_FINAL_AUDIT_CACHE_LOCK = RLock()
_FINAL_AUDIT_CACHE: tuple[tuple[object, ...], float, FinalProductionReadinessAudit] | None = None

SCANNED_SOURCE_ROOTS = (
    "apps/api/app",
    "apps/web/src",
    "apps/openalgo-adapter/adapter_app",
)
SCANNED_SUFFIXES = {".py", ".ts", ".tsx"}
SCAN_EXCLUSIONS = {
    "behavior/final_release_audit.py",
}
FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("direct_place_order_call", re.compile(r"\bplace_order\s*\(", re.IGNORECASE)),
    ("direct_submit_order_call", re.compile(r"\bsubmit_order\s*\(", re.IGNORECASE)),
    ("direct_broker_order_call", re.compile(r"\bbroker\.(?:buy|sell|order)\s*\(", re.IGNORECASE)),
    ("broker_secret_assignment", re.compile(r"\bbroker_(?:api_)?(?:key|secret|token)\s*=", re.IGNORECASE)),
    ("live_order_route", re.compile(r"@[a-zA-Z_]+\.post\(\s*[\"']/api/(?:v\d+/)?(?:live/)?orders", re.IGNORECASE)),
)
REQUIRED_CAPABILITIES = {
    "Behavior Chart Replay Workbench",
    "Behavior Indicator Expansion Workbench",
    "Behavior Stock Memory Profile",
    "Behavior Golden Replay Fixtures",
    "Behavior Decision Engine",
    "Behavior No-Trade Intelligence",
    "Behavior Risk Sizing Engine",
    "Behavior Execution Simulation Engine",
    "Kronos Forecast Engine",
    "Twin Machine Arbiter",
    "OpenAlgo SignalIntent Export",
    "OpenAlgo Adapter Simulator",
    "Research Stack Deployment Recovery",
}
RELEASE_ARTIFACT_PATHS: tuple[tuple[str, bool], ...] = (
    ("apps/api/app/main.py", True),
    ("apps/api/app/models.py", True),
    ("apps/api/app/behavior/constants.py", True),
    ("apps/api/app/behavior/deployment_recovery.py", True),
    ("apps/api/app/behavior/final_release_audit.py", True),
    ("apps/api/app/behavior/release_readiness_evidence.py", True),
    ("apps/api/app/behavior/red_team_final_gate.py", True),
    ("apps/api/app/behavior/openalgo_transport.py", True),
    ("apps/api/app/behavior/transport_security.py", True),
    ("apps/api/app/behavior/transport_resilience.py", True),
    ("apps/openalgo-adapter/adapter_app/main.py", True),
    ("apps/web/src/App.tsx", True),
    ("apps/web/src/api/client.ts", True),
    ("apps/web/src/api/schemas.ts", True),
    ("docs/IMPLEMENTATION_STATUS.md", True),
    ("docs/runbooks/deployment-backup-restore.md", True),
    (".env.research.example", True),
    ("scripts/start-research-stack.ps1", True),
    ("scripts/stop-research-stack.ps1", True),
)


def scan_for_unsafe_live_paths(
    roots: list[Path] | None = None,
    *,
    project_root: Path | None = None,
) -> StaticSafetyScanReport:
    base = (project_root or PROJECT_ROOT).resolve()
    scan_roots = [path.resolve() for path in roots] if roots is not None else [
        (base / relative).resolve() for relative in SCANNED_SOURCE_ROOTS
    ]
    findings: list[StaticSafetyScanFinding] = []
    scanned_files = 0
    for root in scan_roots:
        candidates = [root] if root.is_file() else sorted(root.rglob("*")) if root.exists() else []
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
                continue
            relative = _display_path(path, base)
            if any(relative.replace("\\", "/").endswith(item) for item in SCAN_EXCLUSIONS):
                continue
            scanned_files += 1
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for line_number, line in enumerate(lines, start=1):
                for pattern_id, pattern in FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        findings.append(
                            StaticSafetyScanFinding(
                                finding_id=f"{pattern_id}:{relative}:{line_number}",
                                file_path=relative,
                                line_number=line_number,
                                pattern_id=pattern_id,
                                excerpt=line.strip()[:240],
                            )
                        )
    return StaticSafetyScanReport(
        scan_version=SCAN_VERSION,
        generated_at=now_iso(),
        scanned_file_count=scanned_files,
        scanned_roots=[_display_path(root, base) for root in scan_roots],
        forbidden_pattern_count=len(FORBIDDEN_PATTERNS),
        findings=findings,
        passed=not findings,
    )


def build_release_manifest(*, write_to_disk: bool = False) -> ReleaseCandidateManifest:
    entries: list[ReleaseArtifactEntry] = []
    for relative_path, required in RELEASE_ARTIFACT_PATHS:
        path = PROJECT_ROOT / relative_path
        present = path.is_file()
        entries.append(
            ReleaseArtifactEntry(
                artifact_id=relative_path.replace("/", ":"),
                relative_path=relative_path,
                sha256=_sha256_file(path) if present else "",
                size_bytes=path.stat().st_size if present else 0,
                required=required,
                present=present,
            )
        )
    canonical = [
        entry.model_dump(mode="json")
        for entry in sorted(entries, key=lambda item: item.relative_path)
    ]
    manifest_sha = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    release_id = f"tv-v059-{manifest_sha[:16]}"
    manifest_path: str | None = None
    manifest = ReleaseCandidateManifest(
        manifest_version=MANIFEST_VERSION,
        release_id=release_id,
        generated_at=now_iso(),
        target="research_mock_stack",
        artifact_count=len(entries),
        artifacts=entries,
        manifest_sha256=manifest_sha,
    )
    if write_to_disk:
        output_root = Path(
            os.environ.get(
                "TRADEVISION_RELEASE_DIR",
                str(PROJECT_ROOT / "data" / "release_candidates"),
            )
        )
        output_root.mkdir(parents=True, exist_ok=True)
        output_path = output_root / f"{release_id}.json"
        exported = manifest.model_copy(update={"manifest_path": str(output_path.resolve())})
        output_path.write_text(
            exported.model_dump_json(indent=2),
            encoding="utf-8",
        )
        manifest = exported
    return manifest


def build_final_release_audit(*, force_refresh: bool = False) -> FinalProductionReadinessAudit:
    global _FINAL_AUDIT_CACHE
    cache_key = _final_audit_cache_key()
    now = time.monotonic()
    if not force_refresh:
        with _FINAL_AUDIT_CACHE_LOCK:
            if _FINAL_AUDIT_CACHE is not None:
                cached_key, cached_at, cached_audit = _FINAL_AUDIT_CACHE
                if cached_key == cache_key and now - cached_at <= FINAL_AUDIT_CACHE_TTL_SECONDS:
                    return cached_audit.model_copy(deep=True)

    audit = _build_final_release_audit_uncached()
    with _FINAL_AUDIT_CACHE_LOCK:
        _FINAL_AUDIT_CACHE = (cache_key, time.monotonic(), audit.model_copy(deep=True))
    return audit


def clear_final_release_audit_cache() -> None:
    with _FINAL_AUDIT_CACHE_LOCK:
        global _FINAL_AUDIT_CACHE
        _FINAL_AUDIT_CACHE = None


def _build_final_release_audit_uncached() -> FinalProductionReadinessAudit:
    security = build_security_posture()
    deployment = deployment_readiness(security=security)
    smoke = deployment_smoke(readiness=deployment)
    threat_report = build_threat_report()
    resilience = build_resilience_report()
    red_team = build_tv_prod_red_001_report()
    safety_scan = scan_for_unsafe_live_paths()
    manifest = build_release_manifest()
    names = {capability.name for capability in CAPABILITIES}
    missing_capabilities = sorted(REQUIRED_CAPABILITIES - names)
    required_artifacts_missing = [
        entry.relative_path
        for entry in manifest.artifacts
        if entry.required and not entry.present
    ]
    gates = [
        _gate(
            "deployment",
            "Deployment readiness",
            deployment.ready,
            f"{deployment.pass_count} pass, {deployment.warn_count} warn, {deployment.fail_count} fail",
        ),
        _gate(
            "smoke",
            "End-to-end deployment smoke",
            smoke.all_passed,
            f"{smoke.passed_count}/{smoke.check_count} checks passed",
        ),
        _gate(
            "security",
            "Transport security posture",
            security.overall_status != "fail",
            f"status={security.overall_status}; trace_valid={security.trace_integrity.valid}",
        ),
        _gate(
            "threat_controls",
            "Threat-control verification",
            threat_report.all_passed,
            f"{threat_report.passed_count}/{threat_report.threat_count} controls passed",
        ),
        FinalReleaseGate(
            gate_id="transport_resilience",
            name="Transport resilience evidence",
            status=(
                "pass"
                if resilience.overall_status == "healthy"
                else "warn"
                if resilience.overall_status == "low_evidence"
                else "fail"
            ),
            evidence=(
                f"status={resilience.overall_status}; attempts={resilience.delivery_attempts}; "
                f"alerts={len(resilience.alerts)}; backlog={resilience.backlog_count}"
            ),
            blocks_release=resilience.overall_status in {"degraded", "critical"},
        ),
        FinalReleaseGate(
            gate_id="tv_prod_red_001",
            name="TV-PROD-RED-001 manipulated-wick red-team gate",
            status="pass" if _red_team_passes_release(red_team) else "fail",
            evidence=_red_team_evidence(red_team),
            blocks_release=True,
        ),
        _gate(
            "static_safety",
            "No executable live broker/order path",
            safety_scan.passed,
            f"{safety_scan.scanned_file_count} files scanned; {len(safety_scan.findings)} findings",
        ),
        _gate(
            "capability_coverage",
            "Required capability preservation",
            not missing_capabilities,
            "all required capabilities present" if not missing_capabilities else f"missing: {', '.join(missing_capabilities)}",
        ),
        _gate(
            "artifact_integrity",
            "Release artifact integrity",
            not required_artifacts_missing,
            f"{manifest.artifact_count} artifacts hashed"
            if not required_artifacts_missing
            else f"missing: {', '.join(required_artifacts_missing)}",
        ),
        _gate(
            "brokerless_boundary",
            "Brokerless research boundary",
            (
                deployment.live_trading_blocked
                and not deployment.order_routing_enabled
                and not deployment.broker_credentials_present
                and not deployment.broker_order_created
            ),
            "live blocked; routing disabled; no broker credentials or orders",
        ),
        FinalReleaseGate(
            gate_id="operator_signoff",
            name="Operator release sign-off",
            status="warn",
            evidence="Manual sign-off is required outside this automated audit before deployment.",
            blocks_release=False,
        ),
    ]
    fail_count = sum(gate.status == "fail" for gate in gates)
    warn_count = sum(gate.status == "warn" for gate in gates)
    ready = fail_count == 0
    return FinalProductionReadinessAudit(
        audit_version=AUDIT_VERSION,
        generated_at=now_iso(),
        target="research_mock_stack",
        release_scope=RELEASE_SCOPE,
        gates=gates,
        pass_count=sum(gate.status == "pass" for gate in gates),
        warn_count=warn_count,
        fail_count=fail_count,
        research_stack_ready=ready,
        production_research_release_candidate=ready,
        static_safety_scan=safety_scan,
        release_manifest=manifest,
        deployment_readiness_version=deployment.readiness_version,
        deployment_smoke_version=smoke.smoke_version,
        transport_resilience_version=resilience.resilience_version,
        transport_resilience_status=resilience.overall_status,
        capability_count=len(CAPABILITIES),
        required_capability_count=len(REQUIRED_CAPABILITIES),
        required_capabilities_covered=not missing_capabilities,
        notes=[
            "This audit proves the brokerless research/mock stack only.",
            "TV-PROD-RED-001 is a blocking release gate for manipulated-wick, volatility-OOD, and cache-quarantine behavior.",
            "It does not approve live trading, broker credentials, autonomous execution, or investment use.",
            "A future OpenAlgo integration must pass a separate execution-production review.",
        ],
    )


def _final_audit_cache_key() -> tuple[object, ...]:
    # Keep strong references to each callable in the cache key. Using id(callable)
    # is unsafe because monkeypatch/reload teardown can release the callable while
    # the integer id remains cached; CPython may then reuse that address for a
    # different callable, causing a stale audit to be returned for new evidence.
    return (
        AUDIT_VERSION,
        deployment_readiness,
        deployment_smoke,
        build_security_posture,
        build_threat_report,
        build_resilience_report,
        build_tv_prod_red_001_report,
        scan_for_unsafe_live_paths,
        build_release_manifest,
        os.environ.get("TRADEVISION_OPENALGO_ADAPTER_URL", ""),
        os.environ.get("TRADEVISION_EXPECTED_CONFIG_FINGERPRINT", ""),
        bool(os.environ.get("TRADEVISION_ADAPTER_SHARED_SECRET")),
        bool(os.environ.get("TRADEVISION_ADAPTER_PREVIOUS_SECRET")),
    )


def export_release_candidate() -> ReleaseCandidateManifest:
    audit = build_final_release_audit()
    if not audit.production_research_release_candidate:
        raise ValueError("Final release audit has blocking failures.")
    return build_release_manifest(write_to_disk=True)


def _red_team_passes_release(report: dict) -> bool:
    return (
        report.get("red_team_id") == "TV-PROD-RED-001"
        and report.get("passed") is True
        and report.get("release_blocking") is False
        and report.get("paper_candidate_allowed") is False
        and report.get("trade_allowed") is False
        and report.get("order_routing_enabled") is False
        and report.get("live_trading_blocked") is True
    )


def _red_team_evidence(report: dict) -> str:
    checks = report.get("checks") or []
    passed_count = sum(1 for item in checks if item.get("passed") is True)
    total_count = len(checks)
    failed = [str(item.get("check_id")) for item in checks if item.get("passed") is not True]
    if failed:
        return (
            f"id={report.get('red_team_id', 'unknown')}; passed={report.get('passed')}; "
            f"checks={passed_count}/{total_count}; failed={', '.join(failed[:4])}; "
            f"decision={report.get('decision')}; cache={report.get('cache_status')}"
        )
    return (
        f"id={report.get('red_team_id', 'unknown')}; passed={report.get('passed')}; "
        f"checks={passed_count}/{total_count}; decision={report.get('decision')}; "
        f"paper_candidate={report.get('paper_candidate_allowed')}; cache={report.get('cache_status')}"
    )


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> FinalReleaseGate:
    return FinalReleaseGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "fail",
        evidence=evidence,
        blocks_release=not passed,
    )


def _display_path(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base).as_posix()
    except ValueError:
        return str(path.resolve())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
