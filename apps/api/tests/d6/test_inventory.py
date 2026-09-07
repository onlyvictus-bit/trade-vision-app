import subprocess
import pytest
from tools.repo_inventory import scan


def test_read_only_inventory_has_locations_not_source_contents(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "engine.py").write_text("# private explanation\nrisk = 0.2\nfinal_decision = 'LONG'\n")
    (tmp_path / ".env").write_text("SECRET=do-not-output")
    (tmp_path / "asset.bin").write_bytes(b"\x00\x01")
    subprocess.run(["git", "-C", str(tmp_path), "add", "engine.py", ".env", "asset.bin"], check=True)
    before = (tmp_path / "engine.py").read_bytes()
    report = scan(tmp_path)
    assert report["tracked_files"] == 3 and report["text_files_read"] == 1 and report["skipped_files"] == 2
    engine = next(x for x in report["files"] if x["path"] == "engine.py")
    assert engine["lines"] == 3 and len(engine["candidate_locations"]) == 2
    assert "do-not-output" not in str(report) and "private explanation" not in str(report)
    assert before == (tmp_path / "engine.py").read_bytes()


def test_non_repository_is_reported(tmp_path):
    with pytest.raises(ValueError): scan(tmp_path)
