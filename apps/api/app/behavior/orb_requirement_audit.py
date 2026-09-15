from __future__ import annotations

import argparse
import ast
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from app.behavior.orb_requirement_audit_core import (
    AUDIT_TOOL_VERSION, DEFAULT_MANIFEST_PATH, AuditExitClass, AuditFinding, ERROR_EXIT_CODES,
    SourceReadiness, canonical_json_bytes, load_default_manifest, load_manifest, _finding, _git_blob_sha, _sha256_text,
    _resolve_repo_root, _git_identity, _validate_sources, _validate_requirements, _validate_canaries,
    _validate_source_completeness, _validate_golden_baseline,
    _requirement_manifest_hash, _baseline_manifest_hash,
)

def _extract_d1_inventory(path: Path, function_name: str) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            target = node
            break
    if target is None:
        return []
    rows: list[tuple[str, str]] = []
    for node in ast.walk(target):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "_check" or len(node.args) < 2:
            continue
        try:
            check_id = ast.literal_eval(node.args[0])
            name = ast.literal_eval(node.args[1])
        except (ValueError, TypeError):
            continue
        if isinstance(check_id, str) and isinstance(name, str):
            rows.append((check_id, name))
    return sorted(rows, key=lambda row: row[0])


def _extract_dataclass_defaults(path: Path, class_names: Iterable[str]) -> dict[str, dict[str, Any]]:
    wanted = set(class_names)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name not in wanted:
            continue
        fields: dict[str, Any] = {}
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name) and child.value is not None:
                try:
                    fields[child.target.id] = ast.literal_eval(child.value)
                except (ValueError, TypeError):
                    continue
        out[node.name] = fields
    return out


def _validate_code_baselines(repo_root: Path, manifest: Mapping[str, Any], findings: list[AuditFinding]) -> None:
    baseline = manifest.get("baseline", {})
    d1 = baseline.get("d1_gate_inventory", {})
    if d1.get("enabled", True):
        path = repo_root / str(d1.get("path", ""))
        actual = _extract_d1_inventory(path, str(d1.get("function", "build_d1_safety_gate"))) if path.is_file() else []
        expected = [(str(row.get("check_id")), str(row.get("name"))) for row in d1.get("checks", [])]
        if actual != expected:
            _finding(findings, AuditExitClass.BASELINE_DRIFT, "D1_GATE_INVENTORY_DRIFT", source_path=str(d1.get("path", "")), detail=f"expected={expected};actual={actual}")

    cfg = baseline.get("config_defaults", {})
    if cfg.get("enabled", True):
        path = repo_root / str(cfg.get("path", ""))
        classes = cfg.get("classes", {})
        actual = _extract_dataclass_defaults(path, classes.keys()) if path.is_file() else {}
        for class_name, expected_fields in classes.items():
            for field_name, expected_value in expected_fields.items():
                actual_value = actual.get(class_name, {}).get(field_name, object())
                if actual_value != expected_value:
                    _finding(findings, AuditExitClass.BASELINE_DRIFT, "CONFIG_DEFAULT_DRIFT", source_path=str(cfg.get("path", "")), detail=f"{class_name}.{field_name}:expected={expected_value!r};actual={actual_value!r}")

    auth = baseline.get("authority", {})
    if auth.get("enabled", True):
        try:
            from app.behavior.decision_spine.authority_registry import (
                FINAL_BAND_AUTHORITY,
                all_engine_authorities,
                validate_authority_registry,
            )
        except Exception as exc:
            _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "AUTHORITY_REGISTRY_IMPORT_FAILED", detail=repr(exc))
        else:
            errors = validate_authority_registry()
            if errors:
                _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "AUTHORITY_REGISTRY_INVALID", detail=",".join(errors))
            expected_final = str(auth.get("final_band_authority", "FINAL_CONFLUENCE_ARBITER"))
            if FINAL_BAND_AUTHORITY != expected_final:
                _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "FINAL_BAND_AUTHORITY_DRIFT", detail=f"expected={expected_final};actual={FINAL_BAND_AUTHORITY}")
            rows = tuple(all_engine_authorities())
            finalizers = [row.engine_id for row in rows if row.may_set_final_band]
            if finalizers != [expected_final]:
                _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "FINAL_BAND_NOT_D6_ONLY", detail=repr(finalizers))
            if any(row.may_execute for row in rows):
                _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "EXECUTION_AUTHORITY_FORBIDDEN")
            for engine_id in auth.get("reviewer_ids", []):
                matching = [row for row in rows if row.engine_id == engine_id]
                if len(matching) != 1 or matching[0].may_set_final_band or matching[0].may_execute:
                    _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "REVIEWER_AUTHORITY_ESCALATION", detail=str(engine_id))


def _validate_readiness(manifest: Mapping[str, Any], findings: list[AuditFinding]) -> None:
    seen: set[str] = set()
    for row in manifest.get("source_readiness", []):
        capability_id = str(row.get("capability_id", ""))
        if not capability_id or capability_id in seen:
            _finding(findings, AuditExitClass.REGISTRY_ERROR, "SOURCE_READINESS_ID_INVALID_OR_DUPLICATE", detail=capability_id)
            continue
        seen.add(capability_id)
        try:
            SourceReadiness(str(row.get("state", "")))
        except ValueError:
            _finding(findings, AuditExitClass.REGISTRY_ERROR, "SOURCE_READINESS_STATE_INVALID", detail=capability_id)
        if not row.get("provenance"):
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "SOURCE_READINESS_PROVENANCE_MISSING", detail=capability_id)


def _validate_regression_paths(repo_root: Path, manifest: Mapping[str, Any], findings: list[AuditFinding]) -> None:
    for relative in manifest.get("baseline", {}).get("regression_test_paths", []):
        path = repo_root / str(relative)
        if not path.is_file():
            _finding(findings, AuditExitClass.BASELINE_DRIFT, "REGRESSION_TEST_PATH_MISSING", source_path=str(relative))


def _summarize_findings(findings: Sequence[AuditFinding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.exit_class] = counts.get(finding.exit_class, 0) + 1
    return dict(sorted(counts.items()))


def audit_manifest(
    repo_root: Path,
    manifest: Mapping[str, Any],
    *,
    exact_git_sha: str,
    branch: str,
) -> dict[str, Any]:
    findings: list[AuditFinding] = []
    if manifest.get("schema_version") != "OrbRequirementManifestV1":
        _finding(findings, AuditExitClass.REGISTRY_ERROR, "MANIFEST_SCHEMA_INVALID", detail=repr(manifest.get("schema_version")))
    if manifest.get("baseline", {}).get("schema_version") != "OrbBaselineManifestV1":
        _finding(findings, AuditExitClass.REGISTRY_ERROR, "BASELINE_SCHEMA_INVALID")

    source_texts = _validate_sources(repo_root, manifest, findings)
    total, mapped = _validate_requirements(manifest, source_texts, findings)
    _validate_canaries(manifest, source_texts, findings)
    _validate_source_completeness(manifest, source_texts, findings)
    _validate_code_baselines(repo_root, manifest, findings)
    _validate_readiness(manifest, findings)
    _validate_regression_paths(repo_root, manifest, findings)
    _validate_golden_baseline(repo_root, manifest, findings)

    findings_sorted = sorted(set(findings))
    hard_findings = [f for f in findings_sorted if f.exit_class != AuditExitClass.BLOCKED_NEEDS_AUDIT.value]
    blockers = [f for f in findings_sorted if f.exit_class == AuditExitClass.BLOCKED_NEEDS_AUDIT.value]
    if hard_findings:
        status = "FAIL"
        lock_eligible = False
    elif blockers:
        status = "BLOCKED"
        lock_eligible = False
    else:
        status = "PASS"
        lock_eligible = total > 0 and mapped == total

    coverage_pct = round((mapped / total * 100.0), 6) if total else 0.0
    body: dict[str, Any] = {
        "schema_version": "OrbRequirementCoverageReportV1",
        "audit_tool_version": AUDIT_TOOL_VERSION,
        "manifest_version": manifest.get("manifest_version"),
        "baseline_version": manifest.get("baseline", {}).get("baseline_version"),
        "baseline_manifest_hash": _baseline_manifest_hash(manifest),
        "requirement_manifest_hash": _requirement_manifest_hash(manifest),
        "exact_git_sha": exact_git_sha,
        "branch": branch,
        "status": status,
        "lock_eligible": lock_eligible,
        "coverage": {
            "requirement_count": total,
            "mapped_requirement_count": mapped,
            "coverage_pct": coverage_pct,
            "source_count": len(manifest.get("sources", [])),
            "canary_count": len(manifest.get("canaries", [])),
            "blocked_count": len(blockers),
            "hard_finding_count": len(hard_findings),
        },
        "finding_counts": _summarize_findings(findings_sorted),
        "findings": [asdict(finding) for finding in findings_sorted],
        "safety": {
            "research_only": True,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
            "human_approval_required": True,
            "final_band_authority": manifest.get("baseline", {}).get("authority", {}).get("final_band_authority"),
        },
    }
    body["report_hash"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body


def render_markdown(report: Mapping[str, Any]) -> str:
    coverage = report["coverage"]
    lines = [
        "# ORB BUILD-0 Requirement Coverage Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Lock eligible: `{str(bool(report['lock_eligible'])).lower()}`",
        f"- Exact Git SHA: `{report['exact_git_sha']}`",
        f"- Branch: `{report['branch']}`",
        f"- Tool: `{report['audit_tool_version']}`",
        f"- Requirements mapped: `{coverage['mapped_requirement_count']}/{coverage['requirement_count']}` ({coverage['coverage_pct']}%)",
        f"- Sources locked: `{coverage['source_count']}`",
        f"- Canaries: `{coverage['canary_count']}`",
        f"- Registered blockers: `{coverage['blocked_count']}`",
        f"- Hard findings: `{coverage['hard_finding_count']}`",
        f"- Report hash: `{report['report_hash']}`",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No findings.")
    else:
        lines.append("| Class | Code | Requirement | Source | Detail |")
        lines.append("|---|---|---|---|---|")
        for row in report["findings"]:
            detail = str(row["detail"]).replace("|", "\\|")
            lines.append(f"| {row['exit_class']} | {row['code']} | {row['requirement_id']} | {row['source_path']} | {detail} |")
    lines.extend([
        "",
        "## Authority lock",
        "",
        "This report is audit/governance evidence only. It does not create trading authority, order-routing authority, or an additional final guidance-band authority.",
        "",
    ])
    return "\n".join(lines)


def _write_if_requested(path_text: str | None, data: bytes) -> None:
    if not path_text:
        return
    path = Path(path_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _exit_code(report: Mapping[str, Any], *, require_lock: bool) -> int:
    if require_lock and not report.get("lock_eligible", False):
        return 30
    hard = [row for row in report.get("findings", []) if row.get("exit_class") != AuditExitClass.BLOCKED_NEEDS_AUDIT.value]
    if not hard:
        return 0
    classes = [AuditExitClass(str(row["exit_class"])) for row in hard if str(row.get("exit_class")) in AuditExitClass._value2member_map_]
    return max((ERROR_EXIT_CODES.get(item, 20) for item in classes), default=20)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic ORB BUILD-0 requirement/source/authority auditor")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST_PATH, help="Optional JSON manifest override; default uses committed orb_build0_manifest.py")
    parser.add_argument("--repo-root")
    parser.add_argument("--exact-git-sha")
    parser.add_argument("--branch")
    parser.add_argument("--report-json")
    parser.add_argument("--report-md")
    parser.add_argument("--dump-manifest-json", help="Write the expanded OrbRequirementManifestV1 JSON artifact")
    parser.add_argument("--require-lock", action="store_true", help="Return non-zero unless BUILD-0 is fully lock eligible")
    args = parser.parse_args(argv)

    repo_root = _resolve_repo_root(args.repo_root)
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = repo_root / manifest_path
        manifest = load_manifest(manifest_path)
    else:
        manifest = load_default_manifest()
    if args.dump_manifest_json:
        _write_if_requested(args.dump_manifest_json, canonical_json_bytes(manifest))
    exact_git_sha, branch = _git_identity(repo_root, args.exact_git_sha, args.branch)
    report = audit_manifest(repo_root, manifest, exact_git_sha=exact_git_sha, branch=branch)

    json_bytes = canonical_json_bytes(report)
    markdown = render_markdown(report).encode("utf-8")
    _write_if_requested(args.report_json, json_bytes)
    _write_if_requested(args.report_md, markdown)
    print(json_bytes.decode("utf-8"), end="")
    return _exit_code(report, require_lock=args.require_lock)


if __name__ == "__main__":
    raise SystemExit(main())
