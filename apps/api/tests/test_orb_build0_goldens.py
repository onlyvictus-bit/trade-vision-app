"""ORB BUILD-0 golden semantic-output and benchmark baselines (G001/G002).

The goldens pin the deterministic meaning of the BUILD-1 intake contracts and
the requirement manifest hash. Any contract or manifest change without a golden
re-capture fails here and in the BUILD-0 auditor's golden drift check.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.behavior.orb_build0_manifest import build_manifest
from app.behavior.orb_requirement_audit_core import (
    _baseline_manifest_hash,
    _requirement_manifest_hash,
)
from app.models import OrbTimingResearchRequest
from app.orb.candidate_intake import (
    manual_candidate_intake,
    trendforge_candidate_intakes,
)
from app.orb.timing_research import resolve_symbols_with_shadow

T0 = datetime(2026, 9, 13, 3, 30, tzinfo=timezone.utc)
SHA_A = "a" * 64

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GOLDENS_PATH = FIXTURES_DIR / "orb_build0_goldens.json"
BENCHMARKS_PATH = FIXTURES_DIR / "orb_build0_benchmarks.json"


def _golden_intake() -> dict:
    return {
        "intakeId": "trendforge-intake:golden-1",
        "intakeState": "ACCEPTED_RESEARCH_ONLY",
        "evidenceAsOf": T0.isoformat(),
        "receivedAt": T0.isoformat(),
        "payloadSha256": SHA_A,
        "packet": {
            "evidenceAsOf": T0.isoformat(),
            "payloadSha256": SHA_A,
            "evidence": {
                "candidates": [
                    {
                        "recordId": 1,
                        "symbol": "RELIANCE",
                        "state": "READY",
                        "createdAt": T0.isoformat(),
                        "payload": {"symbol": "RELIANCE", "state": "READY", "statusGroup": "ready"},
                    },
                    {
                        "recordId": 2,
                        "symbol": "TCS",
                        "state": "PRIORITY_RADAR",
                        "createdAt": T0.isoformat(),
                        "payload": {"symbol": "TCS", "state": "PRIORITY_RADAR", "statusGroup": "ready"},
                    },
                ]
            },
        },
    }


def _recompute_fixtures() -> dict:
    manual = manual_candidate_intake("RELIANCE", selected_at=T0)
    trendforge = trendforge_candidate_intakes(_golden_intake())
    request = OrbTimingResearchRequest(symbols_source="explicit", symbols=["RELIANCE", "TCS"])
    _, _, receipt = resolve_symbols_with_shadow(request, selection_cutoff=T0)
    return {
        "manual_candidate_hash": manual.candidate_hash,
        "trendforge_candidate_hashes": [candidate.candidate_hash for candidate in trendforge],
        "shadow_receipt_hash_explicit": receipt.receipt_hash,
        "shadow_receipt_counts": {
            "candidate_count": receipt.candidate_count,
            "eligible_count": receipt.eligible_count,
            "source_count": receipt.source_count,
            "reason_count": receipt.reason_count,
        },
    }


def test_golden_semantic_outputs_are_byte_stable() -> None:
    goldens = json.loads(GOLDENS_PATH.read_text(encoding="utf-8"))
    assert goldens["schema_version"] == "OrbBuild0GoldensV1"
    assert goldens["fixtures"] == _recompute_fixtures()


def test_golden_manifest_hashes_match_current_manifest() -> None:
    goldens = json.loads(GOLDENS_PATH.read_text(encoding="utf-8"))
    manifest = build_manifest()
    assert goldens["requirement_manifest_hash"] == _requirement_manifest_hash(manifest)
    assert goldens["baseline_manifest_hash"] == _baseline_manifest_hash(manifest)


def test_benchmark_baselines_are_sane_and_fast_op_holds_ceiling() -> None:
    benchmarks = json.loads(BENCHMARKS_PATH.read_text(encoding="utf-8"))
    assert benchmarks["schema_version"] == "OrbBuild0BenchmarksV1"
    assert isinstance(benchmarks["suites"], dict) and benchmarks["suites"]
    for suite, row in benchmarks["suites"].items():
        assert 0 < row["ceiling_s"] <= 3600, suite
        assert 0 <= row["observed_s"] <= row["ceiling_s"], suite
    unit_ceiling_ms = benchmarks["unit_op_ceiling_ms"]
    assert 0 < unit_ceiling_ms <= 60000
    started = time.perf_counter()
    manual_candidate_intake("RELIANCE", selected_at=T0)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    assert elapsed_ms < unit_ceiling_ms
