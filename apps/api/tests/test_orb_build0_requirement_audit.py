from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from app.behavior.orb_requirement_audit import (
    AuditExitClass,
    _extract_d1_inventory,
    _extract_dataclass_defaults,
    _git_blob_sha,
    _sha256_text,
    audit_manifest,
    canonical_json_bytes,
)
from app.behavior.orb_build0_manifest import build_manifest


def _norm(value: str) -> str:
    return " ".join(value.strip().split())


def _hash(value: str) -> str:
    return hashlib.sha256(_norm(value).encode("utf-8")).hexdigest()


def _minimal_repo(tmp_path: Path, *, two_requirements: bool = False) -> tuple[Path, dict]:
    source = tmp_path / "source.md"
    lines = ["# Source", "| X1 | alpha requirement | BUILD-0 |"]
    if two_requirements:
        lines.append("| X2 | beta requirement | BUILD-0 |")
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")

    requirements = []
    for rid, text in [("X1", "alpha requirement"), ("X2", "beta requirement")]:
        if rid == "X2" and not two_requirements:
            continue
        line = f"| {rid} | {text} | BUILD-0 |"
        requirements.append({
            "requirement_id": rid, "source_doc_path": "source.md", "source_blob_sha": _git_blob_sha(source.read_bytes()),
            "source_section": "Source", "source_line_range_or_text_hash": _hash(line), "requirement_text": text,
            "requirement_text_hash": _hash(text), "requirement_class": "TEST", "stage_owner": "BUILD-0",
            "target_section": "unit", "contract_ids": ["OrbRequirementManifestV1"], "calculation_ids": [],
            "test_ids": ["UNIT-TEST"], "fixture_ids": [], "disposition": "TARGET_REQUIRED", "supersedes": [],
            "implementation_evidence": [], "status": "MAPPED", "notes": "",
            "source_locator": {"nearest_heading_path": ["Source"], "source_block_kind": "TABLE_ROW", "normalized_text_hash": _hash(line), "optional_rule_id": rid},
        })

    manifest = {
        "schema_version": "OrbRequirementManifestV1", "manifest_version": "unit-v1",
        "baseline": {"schema_version": "OrbBaselineManifestV1", "baseline_version": "unit-baseline", "d1_gate_inventory": {"enabled": False}, "config_defaults": {"enabled": False}, "authority": {"enabled": False, "final_band_authority": "FINAL_CONFLUENCE_ARBITER"}, "regression_test_paths": []},
        "sources": [{"source_id": "SRC", "path": "source.md", "blob_sha": _git_blob_sha(source.read_bytes()), "requires_review_receipt": False}],
        "registries": {"contracts": [{"contract_id": "OrbRequirementManifestV1"}], "calculations": [], "tests": [{"test_id": "UNIT-TEST"}], "fixtures": []},
        "source_readiness": [], "canaries": [], "requirements": requirements, "coverage_policy": {"require_r1_r105": False},
    }
    return tmp_path, manifest


def _audit(repo_root: Path, manifest: dict) -> dict:
    return audit_manifest(repo_root, manifest, exact_git_sha="a" * 40, branch="unit")


def _codes(report: dict) -> set[str]:
    return {row["code"] for row in report["findings"]}


def _classes(report: dict) -> set[str]:
    return {row["exit_class"] for row in report["findings"]}


def test_git_blob_sha_matches_git_object_format(tmp_path: Path) -> None:
    data = b"hello\n"
    assert _git_blob_sha(data) == hashlib.sha1(b"blob 6\0" + data).hexdigest()


def test_deterministic_report_ignores_requirement_row_order(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path, two_requirements=True)
    forward = _audit(root, manifest)
    reversed_manifest = copy.deepcopy(manifest)
    reversed_manifest["requirements"].reverse()
    backward = _audit(root, reversed_manifest)
    assert forward["report_hash"] == backward["report_hash"]
    assert canonical_json_bytes(forward) == canonical_json_bytes(backward)


def test_same_inputs_replay_byte_identically(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    assert canonical_json_bytes(_audit(root, manifest)) == canonical_json_bytes(_audit(root, copy.deepcopy(manifest)))


def test_source_blob_drift_fails_closed(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    (root / "source.md").write_text("changed\n", encoding="utf-8")
    report = _audit(root, manifest)
    assert AuditExitClass.SOURCE_DRIFT.value in _classes(report)
    assert "SOURCE_BLOB_SHA_MISMATCH" in _codes(report)


def test_duplicate_requirement_id_is_rejected(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    manifest["requirements"].append(copy.deepcopy(manifest["requirements"][0]))
    assert "DUPLICATE_REQUIREMENT_ID" in _codes(_audit(root, manifest))


def test_duplicate_requirement_text_hash_is_rejected(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path, two_requirements=True)
    second = manifest["requirements"][1]
    second["requirement_text"] = manifest["requirements"][0]["requirement_text"]
    second["requirement_text_hash"] = manifest["requirements"][0]["requirement_text_hash"]
    assert "DUPLICATE_REQUIREMENT_TEXT_HASH" in _codes(_audit(root, manifest))


def test_target_required_without_test_link_is_rejected(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    manifest["requirements"][0]["test_ids"] = []
    assert "TARGET_REQUIRED_MISSING_TEST" in _codes(_audit(root, manifest))


def test_research_candidate_cannot_hold_authority(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    manifest["requirements"][0].update({"disposition": "RESEARCH_CANDIDATE", "authority": True, "proof_before_activation": True, "test_ids": []})
    assert "RESEARCH_CANDIDATE_AUTHORITY_INVALID" in _codes(_audit(root, manifest))


def test_superseded_requires_replacement_and_reason(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    manifest["requirements"][0].update({"disposition": "SUPERSEDED", "test_ids": []})
    assert "SUPERSEDED_REPLACEMENT_OR_REASON_MISSING" in _codes(_audit(root, manifest))


def test_fail_open_semantic_cannot_be_reactivated(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    manifest["requirements"][0]["semantic_tags"] = ["FAIL_OPEN_UNAVAILABLE"]
    assert "UNSAFE_LEGACY_SEMANTIC_REACTIVATED" in _codes(_audit(root, manifest))


def test_advisory_contract_cannot_set_final_band(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    manifest["requirements"][0].update({"advisory_only": True, "authority": False, "may_set_final_band": True, "may_execute": False})
    report = _audit(root, manifest)
    assert "ADVISOR_AUTHORITY_ESCALATION" in _codes(report)
    assert "NON_D6_FINAL_BAND_AUTHORITY_FORBIDDEN" in _codes(report)


def test_canary_requires_linked_requirement_term(tmp_path: Path) -> None:
    root, manifest = _minimal_repo(tmp_path)
    manifest["canaries"] = [{"canary_id": "CLOCK", "terms": ["CLOCK_TF_FIT"], "requirement_ids": ["X1"], "require_source_presence": False}]
    assert "CANARY_TERM_NOT_MAPPED" in _codes(_audit(root, manifest))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _real_manifest() -> dict:
    return build_manifest()


def _real_audit(manifest: dict) -> dict:
    return audit_manifest(_repo_root(), manifest, exact_git_sha="b" * 40, branch="m4-d6-orchestration-redesign")


def test_real_build0_manifest_is_lock_eligible_after_12_dimension_source_verification() -> None:
    report = _real_audit(_real_manifest())
    assert report["status"] == "PASS"
    assert report["lock_eligible"] is True
    assert report["coverage"]["coverage_pct"] == 100.0
    assert report["coverage"]["requirement_count"] == 129
    assert report["coverage"]["blocked_count"] == 0
    assert report["coverage"]["hard_finding_count"] == 0
    assert report["findings"] == []


def test_historical_211_link_contract_is_exact_and_distinct_from_current_matrix() -> None:
    manifest = _real_manifest()
    row = next(item for item in manifest["requirements"] if item["requirement_id"] == "BLOCKER-12D-001")
    evidence = row["historical_source_evidence"]
    assert row["disposition"] == "HISTORICAL_EVIDENCE"
    assert row["verification_status"] == "SOURCE_VERIFIED"
    assert row["corrected_name"] == "Historical 211-link activation contract: 12 assessment dimensions plus separate live proof."
    assert evidence["matrix_sha256"] == "781069985bf029cb2ad6b4479ac5ff28141362aa6297d5f68601993d53ca0a28"
    assert evidence["row_count"] == evidence["unique_id_count"] == evidence["can_unlock_ready_now_no_count"] == 211
    assert evidence["matrix_column_count"] == len(evidence["assessment_dimensions"]) == 12
    assert evidence["live_runtime_proof"] == "SEPARATE_13TH_REQUIREMENT"
    assert "8 declared dimensions and 9 evaluated dimensions" in evidence["current_matrix_distinction"]


def test_real_d1_inventory_is_exact_and_not_prose_invented() -> None:
    root = _repo_root()
    expected = [
        ("PG-D1-001", "Research-only system mode"), ("PG-D1-002", "Kill switch is armed"),
        ("PG-D1-003", "Symbol identity matches candle series"), ("PG-D1-004", "Timeframe identity matches candle series"),
        ("PG-D1-005", "Input bar count is bounded"), ("PG-D1-006", "OHLCV values are finite"),
        ("PG-D1-007", "Data quality meets threshold"), ("PG-D1-008", "All supplied candles are closed and point-in-time safe"),
        ("PG-D1-009", "Broker credentials and routing are unavailable"),
    ]
    assert _extract_d1_inventory(root / "apps/api/app/behavior/paper_guidance_spine_legacy.py", "build_d1_safety_gate") == expected


def test_real_current_30_defaults_are_regression_truth() -> None:
    root = _repo_root()
    actual = _extract_dataclass_defaults(root / "apps/api/app/behavior/paper_guidance_config.py", ["PaperGuidanceConfig", "PaperGuidanceStorageConfig"])
    assert actual["PaperGuidanceConfig"]["minimum_evidence_count"] == 30
    assert actual["PaperGuidanceStorageConfig"]["feedback_minimum_samples"] == 30


@pytest.mark.parametrize(("requirement_id", "removed_term"), [("D001", "CLOCK_TF_FIT"), ("D002", "UNKNOWN"), ("D003", "Z5")])
def test_real_historically_missed_canaries_fail_if_mapping_is_removed(requirement_id: str, removed_term: str) -> None:
    manifest = _real_manifest()
    row = next(item for item in manifest["requirements"] if item["requirement_id"] == requirement_id)
    row["requirement_text"] = row["requirement_text"].replace(removed_term, "REMOVED")
    row["requirement_text_hash"] = _sha256_text(_norm(row["requirement_text"]))
    assert "CANARY_TERM_NOT_MAPPED" in _codes(_real_audit(manifest))


def test_real_source_sha_mutation_is_source_drift() -> None:
    manifest = _real_manifest()
    next(item for item in manifest["sources"] if item["source_id"] == "SRC-MASTER")["blob_sha"] = "0" * 40
    assert "SOURCE_BLOB_SHA_MISMATCH" in _codes(_real_audit(manifest))


def test_real_superseded_fail_open_cannot_be_marked_target_required() -> None:
    manifest = _real_manifest()
    row = next(item for item in manifest["requirements"] if item["requirement_id"] == "D016")
    row["disposition"] = "TARGET_REQUIRED"
    row["test_ids"] = ["ORB-B7-REQUIREMENT-CONTRACT"]
    assert "UNSAFE_LEGACY_SEMANTIC_REACTIVATED" in _codes(_real_audit(manifest))


def test_real_superseded_row_without_replacement_fails() -> None:
    manifest = _real_manifest()
    next(item for item in manifest["requirements"] if item["requirement_id"] == "D013").pop("replacement")
    assert "SUPERSEDED_REPLACEMENT_OR_REASON_MISSING" in _codes(_real_audit(manifest))


def test_real_advisor_cannot_escalate_to_final_band() -> None:
    manifest = _real_manifest()
    next(item for item in manifest["requirements"] if item["requirement_id"] == "D012")["may_set_final_band"] = True
    assert "ADVISOR_AUTHORITY_ESCALATION" in _codes(_real_audit(manifest))


def test_real_target_required_missing_test_link_fails() -> None:
    manifest = _real_manifest()
    next(item for item in manifest["requirements"] if item["requirement_id"] == "R1")["test_ids"] = []
    assert "TARGET_REQUIRED_MISSING_TEST" in _codes(_real_audit(manifest))


def test_real_manifest_reorder_keeps_report_hash_identical() -> None:
    manifest = _real_manifest()
    first = _real_audit(manifest)
    shuffled = copy.deepcopy(manifest)
    shuffled["requirements"] = list(reversed(shuffled["requirements"]))
    shuffled["sources"] = list(reversed(shuffled["sources"]))
    shuffled["canaries"] = list(reversed(shuffled["canaries"]))
    second = _real_audit(shuffled)
    assert first["report_hash"] == second["report_hash"]
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
