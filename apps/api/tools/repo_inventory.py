"""Read-only Git-tracked file inventory and heuristic D6 locations; not a code audit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".toml",
                 ".md", ".sql", ".css", ".html", ".ini", ".cfg", ".txt"}
PATTERNS = {
    "direction_or_authority": re.compile(r"\b(long|short|buy|sell|final_decision|permission|PAPER.CANDIDATE|ENTER_PAPER)\b", re.I),
    "risk_or_uncertainty": re.compile(r"\b(risk|penalty|uncertainty|trap|slippage|liquidity)\b", re.I),
    "time_or_lookahead": re.compile(r"\b(resample|shift|ffill|bfill|lookahead|bar_close|available_at)\b", re.I),
    "execution": re.compile(r"\b(place_order|submit_order|execute_order|cancel_order|order_id)\b", re.I),
}


def git(root: Path, *arguments: str, required=True) -> str | None:
    result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, timeout=30)
    if result.returncode:
        if required:
            raise ValueError("Git repository cannot be inspected: " + result.stderr.decode("utf-8", errors="replace")[:300])
        return None
    return result.stdout.decode("utf-8", errors="strict")


def scan(root: Path) -> dict:
    root = Path(root).resolve(strict=True)
    top = Path(git(root, "rev-parse", "--show-toplevel").strip()).resolve()
    paths = git(top, "ls-files", "-z").split("\0")
    entries = []
    for relative in sorted(p for p in paths if p):
        path = top / relative
        item = {"path": relative}
        name = path.name.lower()
        if (name.startswith(".env") or path.suffix.lower() in {".key", ".pem", ".pfx", ".p12"}
                or any(token in name for token in ("credential", "secret", "token"))):
            item["skipped"] = "potential_sensitive_file"
        elif path.is_symlink() or not path.resolve().is_relative_to(top):
            item["skipped"] = "symlink_or_path_escape"
        elif not path.is_file():
            item["skipped"] = "missing_or_nonregular_worktree_entry"
        elif path.suffix.lower() not in TEXT_SUFFIXES:
            item["skipped"] = "nonselected_extension"
        elif path.stat().st_size > 2_000_000:
            item["skipped"] = "above_2MB_limit"
        else:
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8")
            except (OSError, UnicodeError):
                item["skipped"] = "unreadable_or_non_utf8"
            else:
                lines = text.splitlines()
                item.update(bytes=len(raw), lines=len(lines), sha256=hashlib.sha256(raw).hexdigest())
                # Never copy line contents into the report: matches are locations,
                # not confirmed bugs, and content could contain sensitive values.
                item["candidate_locations"] = [
                    {"line": i, "categories": categories}
                    for i, line in enumerate(lines, 1)
                    if (categories := [label for label, pattern in PATTERNS.items() if pattern.search(line)])
                ]
        entries.append(item)
    return {"scope": "tracked working-tree files; not a semantic or complete source audit",
            "commit": (git(top, "rev-parse", "--verify", "HEAD", required=False) or "UNCOMMITTED").strip(),
            "tracked_files": len(entries), "text_files_read": sum("sha256" in e for e in entries),
            "skipped_files": sum("skipped" in e for e in entries), "files": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = scan(args.root)
    args.out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(f"Inventoried {report['tracked_files']} tracked files; {report['skipped_files']} skipped. No project files executed.")


if __name__ == "__main__":
    main()
