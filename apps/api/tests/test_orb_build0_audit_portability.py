"""ORB BUILD-0 auditor portability suite (Milestone A).

Proves source identity is git-object identity, not worktree bytes: LF and
CRLF materializations of the same committed object validate identically,
while genuine committed/staged/unstaged changes, missing sources, non-UTF8
sources, and locator drift still fail closed.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

import pytest

from app.behavior.orb_requirement_audit import audit_manifest
from app.behavior.orb_requirement_audit_core import _git_blob_sha
from app.behavior.orb_build0_manifest import build_manifest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_check(*args: str, cwd: Path) -> str:
    completed = _git(*args, cwd=cwd)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return completed.stdout.decode("utf-8").strip()


def _make_git_repo(root: Path, files: dict[str, bytes]) -> Path:
    """Hermetic git repo mirroring the real checkout's text handling
    (autocrlf=true): committed blobs are LF, CRLF worktree materialization is
    git-clean, and only semantic edits read as dirty."""
    _git_check("init", cwd=root)
    _git_check("config", "user.email", "portability@test", cwd=root)
    _git_check("config", "user.name", "portability", cwd=root)
    _git_check("config", "core.autocrlf", "true", cwd=root)
    for name, data in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    _git_check("add", "-A", cwd=root)
    _git_check("commit", "-m", "fixture", cwd=root)
    return root


def _head(root: Path) -> str:
    return _git_check("rev-parse", "HEAD", cwd=root)


def _codes(report: dict) -> set[str]:
    return {row["code"] for row in report["findings"]}


def _fixture_manifest(paths: dict[str, bytes], **overrides) -> dict:
    manifest = {
        "schema_version": "OrbRequirementManifestV1",
        "manifest_version": "portability-v1",
        "baseline": {
            "schema_version": "OrbBaselineManifestV1",
            "baseline_version": "portability-baseline",
            "d1_gate_inventory": {"enabled": False},
            "config_defaults": {"enabled": False},
            "authority": {"enabled": False, "final_band_authority": "FINAL_CONFLUENCE_ARBITER"},
            "regression_test_paths": [],
        },
        "sources": [
            {"source_id": f"SRC-{index}", "path": name, "blob_sha": _git_blob_sha(data), "requires_review_receipt": False}
            for index, (name, data) in enumerate(paths.items())
        ],
        "registries": {"contracts": [], "calculations": [], "tests": [], "fixtures": []},
        "source_readiness": [],
        "canaries": [],
        "requirements": [],
        "coverage_policy": {"require_r1_r105": False},
    }
    manifest.update(overrides)
    return manifest


def _audit(root: Path, manifest: dict, sha: str) -> dict:
    return audit_manifest(root, manifest, exact_git_sha=sha, branch="unit")


# --- 10. SHA-1 git-object semantics stay pinned ------------------------------

def test_manifest_blob_shas_are_git_object_sha1() -> None:
    manifest = build_manifest()
    assert manifest["sources"], "manifest must declare sources"
    for row in manifest["sources"]:
        assert re.fullmatch(r"[0-9a-f]{40}", str(row["blob_sha"])), row["source_id"]
    assert _git_blob_sha(b"hello\n") == hashlib.sha1(b"blob 6\0hello\n").hexdigest()


# --- 1. LF checkout passes ----------------------------------------------------

def test_lf_git_checkout_validates_clean(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"# Source\n"})
    report = _audit(root, _fixture_manifest({"source.md": b"# Source\n"}), _head(root))
    assert "SOURCE_BLOB_SHA_MISMATCH" not in _codes(report)
    assert "SOURCE_MISSING" not in _codes(report)


# --- 2. CRLF worktree, unchanged object, still passes --------------------------

def test_crlf_materialization_is_not_drift(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"# Source\nline\n"})
    (root / "source.md").write_bytes(b"# Source\r\nline\r\n")
    manifest = _fixture_manifest({"source.md": b"# Source\nline\n"})
    report = _audit(root, manifest, _head(root))
    assert "SOURCE_BLOB_SHA_MISMATCH" not in _codes(report)
    # CRLF-only materialization is git-clean, so no dirty finding either.
    assert "LOCAL_DIRTY_SOURCE_UNSTAGED" not in _codes(report)
    assert "LOCAL_DIRTY_SOURCE_STAGED" not in _codes(report)


def test_real_repo_crlf_tree_has_no_blob_mismatch() -> None:
    """End-to-end proof on the real checkout: committed identity matches the
    manifest for all 22 rows even though the worktree is CRLF-materialized."""
    from app.behavior.orb_build0_manifest import _SOURCE_ROWS
    from app.behavior.orb_build0_requirement_catalog import MASTER, MASTER_SHA

    rows = [("SRC-MASTER", MASTER, MASTER_SHA)] + [(s, p, h) for s, p, h, _ in _SOURCE_ROWS[1:]]
    assert len(rows) == 22
    root = _repo_root()
    differ = 0
    for _, path, expected in rows:
        committed = _git("cat-file", "-p", f"HEAD:{path}", cwd=root).stdout
        assert _git_blob_sha(committed) == expected, path
        if (root / path).read_bytes() != committed:
            differ += 1
    if differ == 0:
        pytest.skip("no EOL materialization on this platform; CRLF path untested here")
    report = audit_manifest(root, build_manifest(), exact_git_sha=_git_check("rev-parse", "HEAD", cwd=root), branch="unit")
    assert "SOURCE_BLOB_SHA_MISMATCH" not in _codes(report)


# --- 3. changed committed source fails ----------------------------------------

def test_changed_committed_source_is_mismatch(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"v1\n"})
    first = _head(root)
    (root / "source.md").write_bytes(b"v2\n")
    _git_check("add", "-A", cwd=root)
    _git_check("commit", "-m", "v2", cwd=root)
    manifest = _fixture_manifest({"source.md": b"v1\n"})
    report = _audit(root, manifest, _head(root))
    assert "SOURCE_BLOB_SHA_MISMATCH" in _codes(report)
    # Sanity: the old commit still validates the old manifest (case 9 setup).
    old_report = _audit(root, manifest, first)
    assert "SOURCE_BLOB_SHA_MISMATCH" not in _codes(old_report)


# --- 4. unstaged modification is explicit dirt, not drift ----------------------

def test_unstaged_modification_is_dirty_not_drift(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"v1\n"})
    (root / "source.md").write_bytes(b"v1 semantic edit\n")
    report = _audit(root, _fixture_manifest({"source.md": b"v1\n"}), _head(root))
    assert "LOCAL_DIRTY_SOURCE_UNSTAGED" in _codes(report)
    assert "SOURCE_BLOB_SHA_MISMATCH" not in _codes(report)


# --- 5. staged modification is explicit dirt, not drift ------------------------

def test_staged_modification_is_dirty_not_drift(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"v1\n"})
    (root / "source.md").write_bytes(b"v1 staged edit\n")
    _git_check("add", "-A", cwd=root)
    report = _audit(root, _fixture_manifest({"source.md": b"v1\n"}), _head(root))
    assert "LOCAL_DIRTY_SOURCE_STAGED" in _codes(report)
    assert "SOURCE_BLOB_SHA_MISMATCH" not in _codes(report)


# --- 6. missing source fails ----------------------------------------------------

def test_never_committed_source_is_missing(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"other.md": b"x\n"})
    manifest = _fixture_manifest({"ghost.md": b"x\n"})
    report = _audit(root, manifest, _head(root))
    assert "SOURCE_MISSING" in _codes(report)


def test_worktree_deleted_source_is_dirty_not_missing(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"v1\n"})
    (root / "source.md").unlink()
    report = _audit(root, _fixture_manifest({"source.md": b"v1\n"}), _head(root))
    assert "SOURCE_MISSING" not in _codes(report)
    assert "LOCAL_DIRTY_SOURCE_UNSTAGED" in _codes(report)


# --- 7. non-UTF8 canonical source fails where UTF-8 required --------------------

def test_non_utf8_committed_source_fails(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": "café\n".encode("latin-1")})
    manifest = _fixture_manifest({"source.md": "café\n".encode("latin-1")})
    report = _audit(root, manifest, _head(root))
    assert "SOURCE_NOT_UTF8" in _codes(report)


# --- 8. locator validation uses canonical committed text --------------------------

def _norm_text(value: str) -> str:
    return " ".join(value.strip().split())


def test_locator_uses_committed_text_not_worktree(tmp_path: Path) -> None:
    committed_line = "| R9 | committed text | BUILD-0 |"
    root = _make_git_repo(tmp_path, {"source.md": (committed_line + "\n").encode()})
    # Worktree now says something else: only committed-text sourcing finds it.
    (root / "source.md").write_bytes(b"| R9 | worktree text | BUILD-0 |\n")
    manifest = _fixture_manifest({"source.md": (committed_line + "\n").encode()})
    manifest["requirements"] = [{
        "requirement_id": "RX", "source_doc_path": "source.md",
        "requirement_text": "committed text",
        "requirement_text_hash": hashlib.sha256("committed text".encode()).hexdigest(),
        "stage_owner": "BUILD-0", "disposition": "HISTORICAL_EVIDENCE", "status": "MAPPED",
        "source_locator": {
            "nearest_heading_path": [], "source_block_kind": "TABLE_ROW",
            "normalized_text_hash": hashlib.sha256(_norm_text(committed_line).encode()).hexdigest(),
            "optional_rule_id": "R9",
        },
    }]
    report = _audit(root, manifest, _head(root))
    assert "LOCATOR_TEXT_NOT_FOUND" not in _codes(report)
    assert "LOCAL_DIRTY_SOURCE_UNSTAGED" in _codes(report)


def test_locator_drift_fails(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"| R9 | some text | BUILD-0 |\n"})
    line = "| R9 | some text | BUILD-0 |"
    manifest = _fixture_manifest({"source.md": b"| R9 | some text | BUILD-0 |\n"})
    manifest["requirements"] = [{
        "requirement_id": "RX", "source_doc_path": "source.md",
        "requirement_text": "some text", "requirement_text_hash": hashlib.sha256("some text".encode()).hexdigest(),
        "stage_owner": "BUILD-0", "disposition": "HISTORICAL_EVIDENCE", "status": "MAPPED",
        "source_locator": {
            "nearest_heading_path": [], "source_block_kind": "TABLE_ROW",
            "normalized_text_hash": "f" * 64, "optional_rule_id": "R9",
        },
    }]
    assert line  # the true line exists; only the locator hash is wrong
    report = _audit(root, manifest, _head(root))
    assert "LOCATOR_TEXT_NOT_FOUND" in _codes(report)


# --- 9. exact_git_sha != HEAD reads the requested commit -------------------------

def test_audit_at_older_sha_reads_that_commit(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"v1\n"})
    first = _head(root)
    (root / "source.md").write_bytes(b"v2\n")
    _git_check("add", "-A", cwd=root)
    _git_check("commit", "-m", "v2", cwd=root)
    manifest = _fixture_manifest({"source.md": b"v1\n"})
    report = _audit(root, manifest, first)
    assert report["exact_git_sha"] == first
    assert "SOURCE_BLOB_SHA_MISMATCH" not in _codes(report)


# --- unresolvable commit fails closed --------------------------------------------

def test_unresolvable_commit_fails_closed(tmp_path: Path) -> None:
    root = _make_git_repo(tmp_path, {"source.md": b"v1\n"})
    report = _audit(root, _fixture_manifest({"source.md": b"v1\n"}), "0" * 40)
    assert "GIT_COMMIT_UNRESOLVABLE" in _codes(report)
