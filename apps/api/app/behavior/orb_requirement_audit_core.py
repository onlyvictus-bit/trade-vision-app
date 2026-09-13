from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


AUDIT_TOOL_VERSION = "orb-requirement-audit.v1"
DEFAULT_MANIFEST_PATH = None


class RequirementDisposition(str, Enum):
    TARGET_REQUIRED = "TARGET_REQUIRED"
    CURRENT_REGRESSION_BASELINE = "CURRENT_REGRESSION_BASELINE"
    RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
    HISTORICAL_EVIDENCE = "HISTORICAL_EVIDENCE"
    EXAMPLE_ONLY = "EXAMPLE_ONLY"
    SUPERSEDED = "SUPERSEDED"
    CONFLICT_NEEDS_PROOF = "CONFLICT_NEEDS_PROOF"
    BLOCKED_NEEDS_AUDIT = "BLOCKED_NEEDS_AUDIT"
    OUT_OF_SCOPE_FOR_ORB = "OUT_OF_SCOPE_FOR_ORB"


class SourceReadiness(str, Enum):
    COMPUTABLE_LOCAL = "COMPUTABLE_LOCAL"
    NEEDS_VERSIONED_FILE = "NEEDS_VERSIONED_FILE"
    NEEDS_EXTERNAL_FEED = "NEEDS_EXTERNAL_FEED"
    AVAILABLE_REAL_PIT = "AVAILABLE_REAL_PIT"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


class SourceBlockKind(str, Enum):
    PARAGRAPH = "PARAGRAPH"
    BULLET = "BULLET"
    NUMBERED_ITEM = "NUMBERED_ITEM"
    TABLE_ROW = "TABLE_ROW"
    CODE_CONTRACT = "CODE_CONTRACT"
    RULE_ID = "RULE_ID"


class AuditExitClass(str, Enum):
    PASS = "PASS"
    BLOCKED_NEEDS_AUDIT = "BLOCKED_NEEDS_AUDIT"
    SOURCE_DRIFT = "SOURCE_DRIFT"
    UNMAPPED_REQUIREMENT = "UNMAPPED_REQUIREMENT"
    INVALID_DISPOSITION = "INVALID_DISPOSITION"
    MISSING_TEST_LINK = "MISSING_TEST_LINK"
    AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"
    CANARY_MISSING = "CANARY_MISSING"
    BASELINE_DRIFT = "BASELINE_DRIFT"
    REGISTRY_ERROR = "REGISTRY_ERROR"
    LOCATOR_DRIFT = "LOCATOR_DRIFT"
    DUPLICATE_REQUIREMENT = "DUPLICATE_REQUIREMENT"
    NONDETERMINISTIC_OUTPUT = "NONDETERMINISTIC_OUTPUT"


ERROR_EXIT_CODES: Mapping[AuditExitClass, int] = {
    AuditExitClass.PASS: 0,
    AuditExitClass.BLOCKED_NEEDS_AUDIT: 0,
    AuditExitClass.SOURCE_DRIFT: 10,
    AuditExitClass.UNMAPPED_REQUIREMENT: 11,
    AuditExitClass.INVALID_DISPOSITION: 12,
    AuditExitClass.MISSING_TEST_LINK: 13,
    AuditExitClass.AUTHORITY_CONFLICT: 14,
    AuditExitClass.CANARY_MISSING: 15,
    AuditExitClass.BASELINE_DRIFT: 16,
    AuditExitClass.REGISTRY_ERROR: 17,
    AuditExitClass.LOCATOR_DRIFT: 18,
    AuditExitClass.DUPLICATE_REQUIREMENT: 19,
    AuditExitClass.NONDETERMINISTIC_OUTPUT: 20,
}


@dataclass(frozen=True, slots=True, order=True)
class AuditFinding:
    exit_class: str
    code: str
    requirement_id: str = ""
    source_path: str = ""
    detail: str = ""


def _norm(value: str) -> str:
    return " ".join(str(value).strip().split())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            _canonicalize(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        items = [_canonicalize(v) for v in value]
        if all(isinstance(v, dict) for v in items):
            key_order = ("requirement_id", "source_id", "canary_id", "test_id", "contract_id", "calculation_id", "capability_id", "code")
            for key in key_order:
                if items and all(key in v for v in items):
                    return sorted(items, key=lambda row: str(row[key]))
        if all(isinstance(v, str) for v in items):
            return sorted(items)
        return items
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be an object")
    return payload


def load_default_manifest() -> dict[str, Any]:
    from app.behavior.orb_build0_manifest import build_manifest
    payload = build_manifest()
    if not isinstance(payload, dict):
        raise ValueError("default manifest builder must return an object")
    return payload


def _resolve_repo_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path(__file__).resolve()
    for candidate in (Path.cwd(), *here.parents):
        if (candidate / ".git").exists() and (candidate / "apps" / "api").exists():
            return candidate
    raise RuntimeError("repository root not found; pass --repo-root")


def _git_identity(repo_root: Path, exact_git_sha: str | None, branch: str | None) -> tuple[str, str]:
    sha = exact_git_sha or _run_git(repo_root, "rev-parse", "HEAD")
    if branch:
        branch_name = branch
    else:
        branch_name = os.getenv("GITHUB_REF_NAME") or _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    return sha.strip(), branch_name.strip()


def _run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _finding(
    findings: list[AuditFinding],
    exit_class: AuditExitClass,
    code: str,
    *,
    requirement_id: str = "",
    source_path: str = "",
    detail: str = "",
) -> None:
    findings.append(AuditFinding(exit_class.value, code, requirement_id, source_path, detail))


def _validate_sources(repo_root: Path, manifest: Mapping[str, Any], findings: list[AuditFinding]) -> dict[str, str]:
    texts: dict[str, str] = {}
    seen_ids: set[str] = set()
    for row in manifest.get("sources", []):
        source_id = str(row.get("source_id", ""))
        path_text = str(row.get("path", ""))
        expected_sha = str(row.get("blob_sha", ""))
        if not source_id or source_id in seen_ids:
            _finding(findings, AuditExitClass.REGISTRY_ERROR, "SOURCE_ID_INVALID_OR_DUPLICATE", source_path=path_text, detail=source_id)
            continue
        seen_ids.add(source_id)
        path = repo_root / path_text
        if not path.is_file():
            _finding(findings, AuditExitClass.SOURCE_DRIFT, "SOURCE_MISSING", source_path=path_text)
            continue
        data = path.read_bytes()
        actual_sha = _git_blob_sha(data)
        if actual_sha != expected_sha:
            _finding(
                findings,
                AuditExitClass.SOURCE_DRIFT,
                "SOURCE_BLOB_SHA_MISMATCH",
                source_path=path_text,
                detail=f"expected={expected_sha};actual={actual_sha}",
            )
        try:
            texts[path_text] = data.decode("utf-8")
        except UnicodeDecodeError:
            _finding(findings, AuditExitClass.SOURCE_DRIFT, "SOURCE_NOT_UTF8", source_path=path_text)

        receipt = row.get("review_receipt")
        if row.get("requires_review_receipt", False):
            if not isinstance(receipt, dict) or not receipt.get("canonical_master_doc") or not receipt.get("audit_base_sha"):
                _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "SOURCE_REVIEW_RECEIPT_MISSING", source_path=path_text)
    return texts


def _line_hashes(text: str) -> set[str]:
    return {_sha256_text(_norm(line)) for line in text.splitlines() if _norm(line)}


def _validate_locator(req: Mapping[str, Any], source_text: str | None, findings: list[AuditFinding]) -> None:
    requirement_id = str(req.get("requirement_id", ""))
    path = str(req.get("source_doc_path", ""))
    locator = req.get("source_locator")
    if not isinstance(locator, dict):
        _finding(findings, AuditExitClass.LOCATOR_DRIFT, "LOCATOR_MISSING", requirement_id=requirement_id, source_path=path)
        return
    try:
        SourceBlockKind(str(locator.get("source_block_kind", "")))
    except ValueError:
        _finding(findings, AuditExitClass.LOCATOR_DRIFT, "LOCATOR_BLOCK_KIND_INVALID", requirement_id=requirement_id, source_path=path)
        return
    expected_hash = str(locator.get("normalized_text_hash", ""))
    if len(expected_hash) != 64:
        _finding(findings, AuditExitClass.LOCATOR_DRIFT, "LOCATOR_HASH_INVALID", requirement_id=requirement_id, source_path=path)
        return
    if source_text is None:
        return
    if expected_hash not in _line_hashes(source_text):
        _finding(findings, AuditExitClass.LOCATOR_DRIFT, "LOCATOR_TEXT_NOT_FOUND", requirement_id=requirement_id, source_path=path)


def _validate_requirements(
    manifest: Mapping[str, Any],
    source_texts: Mapping[str, str],
    findings: list[AuditFinding],
) -> tuple[int, int]:
    requirements = manifest.get("requirements", [])
    if not isinstance(requirements, list):
        _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "REQUIREMENTS_NOT_LIST")
        return 0, 0

    registry_tests = {str(row.get("test_id")) for row in manifest.get("registries", {}).get("tests", [])}
    registry_contracts = {str(row.get("contract_id")) for row in manifest.get("registries", {}).get("contracts", [])}
    registry_calcs = {str(row.get("calculation_id")) for row in manifest.get("registries", {}).get("calculations", [])}
    registry_fixtures = {str(row.get("fixture_id")) for row in manifest.get("registries", {}).get("fixtures", [])}

    seen_ids: set[str] = set()
    seen_hashes: dict[str, str] = {}
    mapped = 0
    accumulated_ids: set[str] = set()

    for req in requirements:
        if not isinstance(req, dict):
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "REQUIREMENT_NOT_OBJECT")
            continue
        requirement_id = str(req.get("requirement_id", ""))
        source_path = str(req.get("source_doc_path", ""))
        if not requirement_id:
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "REQUIREMENT_ID_MISSING", source_path=source_path)
            continue
        if requirement_id in seen_ids:
            _finding(findings, AuditExitClass.DUPLICATE_REQUIREMENT, "DUPLICATE_REQUIREMENT_ID", requirement_id=requirement_id, source_path=source_path)
            continue
        seen_ids.add(requirement_id)

        text = str(req.get("requirement_text", ""))
        expected_text_hash = str(req.get("requirement_text_hash", ""))
        actual_text_hash = _sha256_text(_norm(text)) if text else ""
        if not text or expected_text_hash != actual_text_hash:
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "REQUIREMENT_TEXT_HASH_MISMATCH", requirement_id=requirement_id, source_path=source_path)
        elif expected_text_hash in seen_hashes and not req.get("allow_duplicate_text_hash", False):
            _finding(
                findings,
                AuditExitClass.DUPLICATE_REQUIREMENT,
                "DUPLICATE_REQUIREMENT_TEXT_HASH",
                requirement_id=requirement_id,
                source_path=source_path,
                detail=f"same_as={seen_hashes[expected_text_hash]}",
            )
        else:
            seen_hashes[expected_text_hash] = requirement_id

        disposition_text = str(req.get("disposition", ""))
        try:
            disposition = RequirementDisposition(disposition_text)
            mapped += 1
        except ValueError:
            _finding(findings, AuditExitClass.INVALID_DISPOSITION, "DISPOSITION_INVALID", requirement_id=requirement_id, source_path=source_path, detail=disposition_text)
            continue

        if not str(req.get("stage_owner", "")):
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "STAGE_OWNER_MISSING", requirement_id=requirement_id, source_path=source_path)

        for test_id in req.get("test_ids", []):
            if str(test_id) not in registry_tests:
                _finding(findings, AuditExitClass.REGISTRY_ERROR, "UNKNOWN_TEST_ID", requirement_id=requirement_id, detail=str(test_id))
        for contract_id in req.get("contract_ids", []):
            if str(contract_id) not in registry_contracts:
                _finding(findings, AuditExitClass.REGISTRY_ERROR, "UNKNOWN_CONTRACT_ID", requirement_id=requirement_id, detail=str(contract_id))
        for calculation_id in req.get("calculation_ids", []):
            if str(calculation_id) not in registry_calcs:
                _finding(findings, AuditExitClass.REGISTRY_ERROR, "UNKNOWN_CALCULATION_ID", requirement_id=requirement_id, detail=str(calculation_id))
        for fixture_id in req.get("fixture_ids", []):
            if str(fixture_id) not in registry_fixtures:
                _finding(findings, AuditExitClass.REGISTRY_ERROR, "UNKNOWN_FIXTURE_ID", requirement_id=requirement_id, detail=str(fixture_id))

        status = str(req.get("status", ""))
        if status in {"VERIFIED", "GOLDEN_CAPTURED", "CI_VERIFIED", "LOCKED", "COMPLETE"} and not req.get("implementation_evidence"):
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "COMPLETION_WITHOUT_IMPLEMENTATION_EVIDENCE", requirement_id=requirement_id)

        if disposition is RequirementDisposition.TARGET_REQUIRED and not req.get("test_ids"):
            _finding(findings, AuditExitClass.MISSING_TEST_LINK, "TARGET_REQUIRED_MISSING_TEST", requirement_id=requirement_id, source_path=source_path)
        elif disposition is RequirementDisposition.CURRENT_REGRESSION_BASELINE and not req.get("fixture_ids"):
            _finding(findings, AuditExitClass.MISSING_TEST_LINK, "REGRESSION_BASELINE_MISSING_FIXTURE", requirement_id=requirement_id, source_path=source_path)
        elif disposition is RequirementDisposition.RESEARCH_CANDIDATE:
            if req.get("authority", True) is not False or req.get("proof_before_activation", False) is not True:
                _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "RESEARCH_CANDIDATE_AUTHORITY_INVALID", requirement_id=requirement_id)
        elif disposition is RequirementDisposition.SUPERSEDED:
            if not req.get("replacement") or not req.get("reason"):
                _finding(findings, AuditExitClass.INVALID_DISPOSITION, "SUPERSEDED_REPLACEMENT_OR_REASON_MISSING", requirement_id=requirement_id)
        elif disposition is RequirementDisposition.OUT_OF_SCOPE_FOR_ORB:
            if not req.get("responsibility_note") or req.get("authority", True) is not False or req.get("may_execute", True) is not False:
                _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "OUT_OF_SCOPE_AUTHORITY_INVALID", requirement_id=requirement_id)
        elif disposition is RequirementDisposition.CONFLICT_NEEDS_PROOF:
            if len(req.get("competing_priors", [])) < 2 or not req.get("experiment_id"):
                _finding(findings, AuditExitClass.INVALID_DISPOSITION, "CONFLICT_PROOF_REGISTRATION_MISSING", requirement_id=requirement_id)
        elif disposition is RequirementDisposition.BLOCKED_NEEDS_AUDIT:
            allowed_blockers = {str(value) for value in manifest.get("coverage_policy", {}).get("allowed_lock_blockers", [])}
            if requirement_id not in allowed_blockers:
                _finding(findings, AuditExitClass.INVALID_DISPOSITION, "UNREGISTERED_AUDIT_BLOCKER", requirement_id=requirement_id, source_path=source_path)
            _finding(findings, AuditExitClass.BLOCKED_NEEDS_AUDIT, "REGISTERED_AUDIT_BLOCKER", requirement_id=requirement_id, source_path=source_path, detail=str(req.get("notes", "")))

        if req.get("may_execute") is True:
            _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "ORB_EXECUTION_AUTHORITY_FORBIDDEN", requirement_id=requirement_id)
        if req.get("may_set_final_band") is True and str(req.get("stage_owner", "")) not in {"D6", "FINAL_CONFLUENCE_ARBITER"}:
            _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "NON_D6_FINAL_BAND_AUTHORITY_FORBIDDEN", requirement_id=requirement_id)
        if req.get("advisory_only") is True and (req.get("authority") is not False or req.get("may_set_final_band") is not False or req.get("may_execute") is not False):
            _finding(findings, AuditExitClass.AUTHORITY_CONFLICT, "ADVISOR_AUTHORITY_ESCALATION", requirement_id=requirement_id)
        semantic_tags = {str(value) for value in req.get("semantic_tags", [])}
        forbidden_legacy_tags = {"FAIL_OPEN_UNAVAILABLE", "NUMERIC_NEUTRAL_MISSINGNESS", "BROKER_EXECUTION_COMMAND"}
        if semantic_tags & forbidden_legacy_tags and disposition not in {RequirementDisposition.SUPERSEDED, RequirementDisposition.OUT_OF_SCOPE_FOR_ORB, RequirementDisposition.HISTORICAL_EVIDENCE}:
            _finding(findings, AuditExitClass.INVALID_DISPOSITION, "UNSAFE_LEGACY_SEMANTIC_REACTIVATED", requirement_id=requirement_id, detail=",".join(sorted(semantic_tags & forbidden_legacy_tags)))

        _validate_locator(req, source_texts.get(source_path), findings)
        rule_id = str(req.get("source_locator", {}).get("optional_rule_id", "")) if isinstance(req.get("source_locator"), dict) else ""
        if re.fullmatch(r"R(?:[1-9]|[1-9][0-9]|10[0-5])", rule_id):
            accumulated_ids.add(rule_id)

    if manifest.get("coverage_policy", {}).get("require_r1_r105", True):
        expected_accumulated = {f"R{i}" for i in range(1, 106)}
        missing_accumulated = sorted(expected_accumulated - accumulated_ids, key=lambda value: int(value[1:]))
        extra_accumulated = sorted(accumulated_ids - expected_accumulated)
        if missing_accumulated:
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "R1_R105_MISSING", detail=",".join(missing_accumulated))
        if extra_accumulated:
            _finding(findings, AuditExitClass.UNMAPPED_REQUIREMENT, "R1_R105_EXTRA", detail=",".join(extra_accumulated))

    return len(requirements), mapped


def _validate_canaries(manifest: Mapping[str, Any], source_texts: Mapping[str, str], findings: list[AuditFinding]) -> None:
    requirements = {str(row.get("requirement_id")): row for row in manifest.get("requirements", []) if isinstance(row, dict)}
    baseline_text = json.dumps(manifest.get("baseline", {}), sort_keys=True)
    source_joined = "\n".join(source_texts.values())
    seen: set[str] = set()
    for canary in manifest.get("canaries", []):
        canary_id = str(canary.get("canary_id", ""))
        if not canary_id or canary_id in seen:
            _finding(findings, AuditExitClass.CANARY_MISSING, "CANARY_ID_INVALID_OR_DUPLICATE", detail=canary_id)
            continue
        seen.add(canary_id)
        linked = [str(value) for value in canary.get("requirement_ids", [])]
        if not linked or any(value not in requirements for value in linked):
            _finding(findings, AuditExitClass.CANARY_MISSING, "CANARY_REQUIREMENT_LINK_MISSING", detail=canary_id)
            continue
        linked_text = "\n".join(json.dumps(requirements[value], sort_keys=True) for value in linked) + "\n" + baseline_text
        for term in canary.get("terms", []):
            text = str(term)
            if text not in linked_text:
                _finding(findings, AuditExitClass.CANARY_MISSING, "CANARY_TERM_NOT_MAPPED", detail=f"{canary_id}:{text}")
            if canary.get("require_source_presence", True) and text not in source_joined and text not in baseline_text:
                _finding(findings, AuditExitClass.CANARY_MISSING, "CANARY_TERM_NOT_IN_SOURCE", detail=f"{canary_id}:{text}")
