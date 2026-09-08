from __future__ import annotations

from pathlib import Path
import re

ROOT = Path.cwd()


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = _read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}: {old[:100]!r}")
    _write(path, text.replace(old, new, 1))


def regex_once(path: str, pattern: str, replacement: str) -> None:
    text = _read(path)
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{path}: expected one regex match, found {count}: {pattern[:120]!r}")
    _write(path, updated)


def append_once(path: str, marker: str, addition: str) -> None:
    text = _read(path)
    if marker in text:
        raise RuntimeError(f"{path}: marker already present: {marker}")
    _write(path, text.rstrip() + "\n\n" + addition.strip() + "\n")


def patch_stage2_integrity() -> None:
    path = "apps/api/app/behavior/decision_spine/stage2_integrity.py"
    replace_once(
        path,
        "if item.availability in {Availability.UNAVAILABLE, Availability.ERROR] and not item.unavailable_reasons:",
        "if item.availability in {Availability.UNAVAILABLE, Availability.ERROR} and not item.unavailable_reasons:",
    )


def patch_models() -> None:
    path = "apps/api/app/models.py"
    regex_once(
        path,
        r'(class IndicatorFeatureBlock\(BaseModel\):.*?source_mode: Literal\[)"mock", "real", "masked"(\] = "mock")',
        r'\1"mock", "real", "masked", "synthetic_fallback"\2',
    )
    replace_once(
        path,
        '    real_runtime_computed_count: int = Field(default=0, ge=0)\n    real_runtime_masked_count: int = Field(default=0, ge=0)',
        '    real_runtime_computed_count: int = Field(default=0, ge=0)\n'
        '    synthetic_fallback_computed_count: int = Field(default=0, ge=0)\n'
        '    runtime_unavailable_count: int = Field(default=0, ge=0)\n'
        '    runtime_failed_count: int = Field(default=0, ge=0)\n'
        '    runtime_accounting_pass: bool = True\n'
        '    real_runtime_masked_count: int = Field(default=0, ge=0)',
    )


def patch_nine_candle_hybrid() -> None:
    path = "apps/api/app/behavior/nine_candle_hybrid.py"
    replace_once(
        path,
        '                source_mode="real" if candle_source == "hstry_real" else "synthetic_fallback",\n'
        '                runtime_status=runtime_status,\n'
        '                normalized_from=normalized_from,\n'
        '                raw_output_present=True,\n'
        '                explanation_only=not bool(item.used_for_probability),\n'
        '                usable_for_probability=bool(item.used_for_probability and not any(mask)),',
        '                source_mode="real" if candle_source == "hstry_real" else "synthetic_fallback",\n'
        '                runtime_status=runtime_status,\n'
        '                normalized_from=normalized_from,\n'
        '                raw_output_present=True,\n'
        '                # Synthetic candles may be useful for explanation/runtime diagnostics,\n'
        '                # but they can never become calibrated probability evidence.\n'
        '                explanation_only=bool(candle_source != "hstry_real" or not item.used_for_probability),\n'
        '                usable_for_probability=bool(\n'
        '                    candle_source == "hstry_real"\n'
        '                    and item.used_for_probability\n'
        '                    and not any(mask)\n'
        '                ),',
    )

    replace_once(
        path,
        '    real_runtime_computed_count = sum(\n'
        '        1 for sequence in sequences if sequence.source_mode == "real" and sequence.runtime_status in {"computed", "slow_warn"}\n'
        '    )\n'
        '    real_runtime_masked_count = sum(\n'
        '        1 for sequence in sequences if sequence.source_mode == "masked" and sequence.runtime_status != "not_promoted"\n'
        '    )\n'
        '    non_promoted_masked_count = sum(\n'
        '        1 for sequence in sequences if sequence.source_mode == "masked" and sequence.runtime_status == "not_promoted"\n'
        '    )',
        '    computed_statuses = {"computed", "slow_warn"}\n'
        '    real_runtime_computed_count = sum(\n'
        '        1\n'
        '        for sequence in sequences\n'
        '        if sequence.source_mode == "real" and sequence.runtime_status in computed_statuses\n'
        '    )\n'
        '    synthetic_fallback_computed_count = sum(\n'
        '        1\n'
        '        for sequence in sequences\n'
        '        if sequence.source_mode == "synthetic_fallback" and sequence.runtime_status in computed_statuses\n'
        '    )\n'
        '    runtime_failed_count = sum(\n'
        '        1\n'
        '        for sequence in sequences\n'
        '        if sequence.runtime_status == "error" and sequence.runtime_status != "not_promoted"\n'
        '    )\n'
        '    runtime_unavailable_count = max(\n'
        '        0,\n'
        '        promoted_runtime_indicator_count\n'
        '        - real_runtime_computed_count\n'
        '        - synthetic_fallback_computed_count\n'
        '        - runtime_failed_count,\n'
        '    )\n'
        '    runtime_accounting_pass = (\n'
        '        real_runtime_computed_count\n'
        '        + synthetic_fallback_computed_count\n'
        '        + runtime_unavailable_count\n'
        '        + runtime_failed_count\n'
        '        == promoted_runtime_indicator_count\n'
        '    )\n'
        '    real_runtime_masked_count = sum(\n'
        '        1 for sequence in sequences if sequence.source_mode == "masked" and sequence.runtime_status != "not_promoted"\n'
        '    )\n'
        '    non_promoted_masked_count = sum(\n'
        '        1 for sequence in sequences if sequence.source_mode == "masked" and sequence.runtime_status == "not_promoted"\n'
        '    )',
    )

    replace_once(
        path,
        '    if use_real_indicators and non_promoted_masked_count:\n'
        '        warnings.append(\n'
        '            f"{non_promoted_masked_count} registry indicators are not promoted for the local real-runtime bridge and remain masked"\n'
        '        )\n'
        '    if missing_mask_count:',
        '    if use_real_indicators and non_promoted_masked_count:\n'
        '        warnings.append(\n'
        '            f"{non_promoted_masked_count} registry indicators are not promoted for the local real-runtime bridge and remain masked"\n'
        '        )\n'
        '    if use_real_indicators and synthetic_fallback_computed_count:\n'
        '        warnings.append(\n'
        '            f"{synthetic_fallback_computed_count} promoted indicators were computed from synthetic fallback candles; "\n'
        '            "they are explanation-only and excluded from probability authority"\n'
        '        )\n'
        '    if use_real_indicators and not runtime_accounting_pass:\n'
        '        failures.append("runtime_provenance_accounting_mismatch")\n'
        '    if missing_mask_count:',
    )

    replace_once(
        path,
        '        real_runtime_computed_count=real_runtime_computed_count,\n'
        '        real_runtime_masked_count=real_runtime_masked_count,',
        '        real_runtime_computed_count=real_runtime_computed_count,\n'
        '        synthetic_fallback_computed_count=synthetic_fallback_computed_count,\n'
        '        runtime_unavailable_count=runtime_unavailable_count,\n'
        '        runtime_failed_count=runtime_failed_count,\n'
        '        runtime_accounting_pass=runtime_accounting_pass,\n'
        '        real_runtime_masked_count=real_runtime_masked_count,',
    )


def patch_pta_accounting() -> None:
    path = "apps/api/app/behavior/indicator_runtime_bridge.py"
    replace_once(
        path,
        '    slow_indicator_ids = [\n'
        '        str(row.get("indicator_id"))\n'
        '        for row in telemetry\n'
        '        if str(row.get("status")) in {"slow_warn", "slow_blocked"}\n'
        '    ]\n'
        '    report = {',
        '    slow_indicator_ids = [\n'
        '        str(row.get("indicator_id"))\n'
        '        for row in telemetry\n'
        '        if str(row.get("status")) in {"slow_warn", "slow_blocked"}\n'
        '    ]\n'
        '    pta_accounting = _pta_accounting(\n'
        '        selected_count=len(pta_selected),\n'
        '        telemetry=pta_telemetry,\n'
        '        materialized_output_count=len(pta_outputs),\n'
        '        requested=use_real_indicators,\n'
        '    )\n'
        '    report = {',
    )

    replace_once(
        path,
        '        "pta_marker_selected_count": len(pta_selected),\n'
        '        "pta_marker_output_count": len(pta_outputs),\n'
        '        "pta_marker_telemetry": pta_telemetry,\n'
        '        "pta_marker_telemetry_counts": _telemetry_counts(pta_telemetry),',
        '        "pta_marker_selected_count": len(pta_selected),\n'
        '        "pta_marker_probe_count": pta_accounting["probe_count"],\n'
        '        "pta_marker_computed_count": pta_accounting["computed_count"],\n'
        '        "pta_marker_no_signal_count": pta_accounting["no_signal_count"],\n'
        '        "pta_marker_dependency_unavailable_count": pta_accounting["dependency_unavailable_count"],\n'
        '        "pta_marker_error_count": pta_accounting["error_count"],\n'
        '        # Legacy field retained as materialized outputs only (computed + no-signal).\n'
        '        # It must never be interpreted as probe completeness.\n'
        '        "pta_marker_output_count": len(pta_outputs),\n'
        '        "pta_marker_accounting": pta_accounting,\n'
        '        "pta_marker_telemetry": pta_telemetry,\n'
        '        "pta_marker_telemetry_counts": _telemetry_counts(pta_telemetry),',
    )

    replace_once(
        path,
        '\ndef _telemetry_counts(telemetry: list[dict[str, object]]) -> dict[str, int]:\n',
        '\ndef _pta_accounting(\n'
        '    *,\n'
        '    selected_count: int,\n'
        '    telemetry: list[dict[str, object]],\n'
        '    materialized_output_count: int,\n'
        '    requested: bool,\n'
        ') -> dict[str, object]:\n'
        '    counts = _telemetry_counts(telemetry)\n'
        '    probe_count = len(telemetry)\n'
        '    computed_count = int(counts.get("computed", 0))\n'
        '    no_signal_count = int(counts.get("no_signal", 0))\n'
        '    dependency_unavailable_count = int(counts.get("dependency_unavailable", 0))\n'
        '    error_count = int(counts.get("error", 0))\n'
        '    classified_count = computed_count + no_signal_count + dependency_unavailable_count + error_count\n'
        '    expected_materialized_count = computed_count + no_signal_count\n'
        '    accounting_pass = (\n'
        '        probe_count == classified_count\n'
        '        and materialized_output_count == expected_materialized_count\n'
        '        and ((not requested and probe_count == 0) or (requested and probe_count == selected_count))\n'
        '    )\n'
        '    return {\n'
        '        "selected_count": selected_count,\n'
        '        "probe_count": probe_count,\n'
        '        "computed_count": computed_count,\n'
        '        "no_signal_count": no_signal_count,\n'
        '        "dependency_unavailable_count": dependency_unavailable_count,\n'
        '        "error_count": error_count,\n'
        '        "materialized_output_count": materialized_output_count,\n'
        '        "accounting_pass": accounting_pass,\n'
        '    }\n'
        '\n\ndef _telemetry_counts(telemetry: list[dict[str, object]]) -> dict[str, int]:\n',
    )


def patch_authority_registry() -> None:
    path = "apps/api/app/behavior/decision_spine/authority_registry.py"
    replace_once(
        path,
        '    _engine("NINE_CANDLE_MEMORY", "app.behavior.nine_candle_hybrid", EngineClassification.MEMORY, downgrade=True, rank=25, lifecycle="migration", notes="9C/PTA runtime contract stabilization required before canonical authority use."),\n'
        '    _engine("HYPOTHESIS_ENGINE",',
        '    _engine("NINE_CANDLE_MEMORY", "app.behavior.nine_candle_hybrid", EngineClassification.MEMORY, downgrade=True, rank=25, lifecycle="migration", notes="9C/PTA runtime contract stabilization required before canonical authority use."),\n'
        '    _engine("PTA_MARKER_RUNTIME", "app.behavior.real_indicator_adapter", EngineClassification.EVIDENCE, rank=10, lifecycle="migration", notes="PTA marker probes are availability/explanation evidence only; never probability or trade authority."),\n'
        '    _engine("HYPOTHESIS_ENGINE",',
    )


def patch_paper_guidance_wiring() -> None:
    path = "apps/api/app/behavior/paper_guidance_spine.py"
    replace_once(
        path,
        'from .data_quality import scan_data_quality\n',
        'from .data_quality import scan_data_quality\n'
        'from .decision_spine.stage2_integrity import (\n'
        '    Availability,\n'
        '    EvidenceObservation,\n'
        '    SourceMode,\n'
        '    build_stage2_integrity_report,\n'
        ')\n',
    )

    replace_once(
        path,
        '    authoritative_count = int(memory_summary["historical_match_count"])\n'
        '    low_evidence = authoritative_count < settings.minimum_evidence_count\n'
        '    required_mtf_complete = not mtf_evidence.missing_required_timeframes\n'
        '    arbiter_request = FinalConfluenceArbiterRequest(',
        '    authoritative_count = int(memory_summary["historical_match_count"])\n'
        '    low_evidence = authoritative_count < settings.minimum_evidence_count\n'
        '    required_mtf_complete = not mtf_evidence.missing_required_timeframes\n'
        '\n'
        '    # M0 Decision-Spine stabilization: only D2-native receipts are admitted as\n'
        '    # active evidence. Legacy/current 9C, PTA, ORB and AFRE paths are recorded\n'
        '    # explicitly as skipped instead of being silently substituted with neutral\n'
        '    # values or independently re-fetching/recomputing outside the D2 snapshot.\n'
        '    stage2_observations = [\n'
        '        EvidenceObservation(\n'
        '            engine_id="NINE_CANDLE_MEMORY",\n'
        '            source_snapshot_hash=snapshot.snapshot_hash,\n'
        '            availability=Availability.SKIPPED,\n'
        '            source_mode=SourceMode.UNKNOWN,\n'
        '            unavailable_reasons=("9C current runtime is not yet D2-snapshot-native in paper guidance",),\n'
        '            notes=("M0 preserves 9C as explicit non-authoritative skipped evidence until canonical wiring",),\n'
        '        ),\n'
        '        EvidenceObservation(\n'
        '            engine_id="PTA_MARKER_RUNTIME",\n'
        '            source_snapshot_hash=snapshot.snapshot_hash,\n'
        '            availability=Availability.SKIPPED,\n'
        '            source_mode=SourceMode.UNKNOWN,\n'
        '            unavailable_reasons=("PTA marker probes are not yet D2-snapshot-native in paper guidance",),\n'
        '            notes=("PTA remains explanation/availability evidence only",),\n'
        '        ),\n'
        '        EvidenceObservation(\n'
        '            engine_id="ORB_CORE",\n'
        '            source_snapshot_hash=snapshot.snapshot_hash,\n'
        '            availability=Availability.SKIPPED,\n'
        '            source_mode=SourceMode.UNKNOWN,\n'
        '            unavailable_reasons=("ORB is intentionally not activated in v1.88 paper guidance",),\n'
        '        ),\n'
        '        EvidenceObservation(\n'
        '            engine_id="AFRE",\n'
        '            source_snapshot_hash=snapshot.snapshot_hash,\n'
        '            availability=Availability.SKIPPED,\n'
        '            source_mode=SourceMode.UNKNOWN,\n'
        '            unavailable_reasons=("AFRE canonical DecisionContext wiring is deferred until after M0",),\n'
        '        ),\n'
        '    ]\n'
        '    stage2_integrity = build_stage2_integrity_report(\n'
        '        canonical_snapshot_hash=snapshot.snapshot_hash,\n'
        '        engine_receipts=receipts,\n'
        '        evidence_observations=stage2_observations,\n'
        '    )\n'
        '    if not stage2_integrity.canonical_context_eligible:\n'
        '        stage2_blockers = [f"Stage-2 integrity: {item}" for item in stage2_integrity.hard_blockers]\n'
        '        blocked_guidance_id = str(\n'
        '            uuid5(\n'
        '                NAMESPACE_URL,\n'
        '                "tradevision:paper-guidance:stage2-block:"\n'
        '                + snapshot.snapshot_hash\n'
        '                + ":"\n'
        '                + stage2_integrity.output_hash,\n'
        '            )\n'
        '        )\n'
        '        return base.model_copy(\n'
        '            update={\n'
        '                "guidance_version": PAPER_GUIDANCE_P1_VERSION,\n'
        '                "guidance_id": blocked_guidance_id,\n'
        '                "final_band": "WAIT",\n'
        '                "confidence_cap": min(base.confidence_cap, settings.p0_confidence_cap),\n'
        '                "next_action": "DO_NOTHING",\n'
        '                "blockers": _unique(list(base.blockers) + stage2_blockers),\n'
        '                "warnings": _unique(warnings + list(stage2_integrity.warnings)),\n'
        '                "reason_for": _unique(list(base.reason_for) + ["D1 safety and D2 immutable snapshot checks passed."]),\n'
        '                "reason_against": _unique(\n'
        '                    list(base.reason_against)\n'
        '                    + ["Stage-2 evidence integrity blocked canonical evidence before D6 arbitration."]\n'
        '                ),\n'
        '                "entry_plan": None,\n'
        '                "evidence_votes": [],\n'
        '                "engine_receipts": receipts,\n'
        '                "mtf_evidence": mtf_evidence,\n'
        '                "arbiter_summary": {\n'
        '                    "arbiter_run": False,\n'
        '                    "blocked_before_d6": True,\n'
        '                    "stage2_integrity_hash": stage2_integrity.output_hash,\n'
        '                },\n'
        '                "engines_run": _unique(engines_run),\n'
        '                "engines_skipped": _unique(engines_skipped + ["D6_ARBITER:stage2_integrity_block"]),\n'
        '                "memory_summary": memory_summary,\n'
        '                "risk_summary": {\n'
        '                    **base.risk_summary,\n'
        '                    "paper_entry_authority": False,\n'
        '                    "stage2_integrity": stage2_integrity.as_dict(),\n'
        '                },\n'
        '                "low_evidence_flag": low_evidence,\n'
        '                "historical_match_count": authoritative_count,\n'
        '                "minimum_evidence_count": settings.minimum_evidence_count,\n'
        '            }\n'
        '        )\n'
        '\n'
        '    arbiter_request = FinalConfluenceArbiterRequest(',
    )

    replace_once(
        path,
        '            "paper_entry_authority": False,\n'
        '        },\n'
        '        data_quality=base.data_quality,',
        '            "paper_entry_authority": False,\n'
        '            "stage2_integrity": stage2_integrity.as_dict(),\n'
        '        },\n'
        '        data_quality=base.data_quality,',
    )


def patch_api_tests() -> None:
    path = "apps/api/tests/test_api.py"
    replace_once(
        path,
        '    monkeypatch.setattr(hybrid, "compute_real_indicator_outputs_with_telemetry", fake_outputs)\n'
        '    default_result = client.get("/api/v1/behavior/9c-dna/current/RELIANCE?timeframe=1m").json()["data"]',
        '    monkeypatch.setattr(hybrid, "compute_real_indicator_outputs_with_telemetry", fake_outputs)\n'
        '    monkeypatch.setattr(hybrid, "_real_closed_candles", lambda *_: [])\n'
        '    default_result = client.get("/api/v1/behavior/9c-dna/current/RELIANCE?timeframe=1m").json()["data"]',
    )
    replace_once(
        path,
        '    assert audit["real_runtime_computed_count"] == 2\n'
        '    assert audit["real_runtime_masked_count"] == len(promoted_ids) - 2\n'
        '    assert audit["non_promoted_masked_count"] == len(entries) - len(promoted_ids)',
        '    assert audit["real_runtime_computed_count"] == 0\n'
        '    assert audit["synthetic_fallback_computed_count"] == 2\n'
        '    assert audit["runtime_unavailable_count"] == len(promoted_ids) - 2\n'
        '    assert audit["runtime_failed_count"] == 0\n'
        '    assert audit["runtime_accounting_pass"] is True\n'
        '    assert audit["real_runtime_masked_count"] == len(promoted_ids) - 2\n'
        '    assert audit["non_promoted_masked_count"] == len(entries) - len(promoted_ids)',
    )
    replace_once(
        path,
        '    assert result["pta_marker_selected_count"] == 23\n'
        '    assert result["pta_marker_output_count"] == 23\n'
        '    assert len(result["pta_marker_telemetry"]) == 23',
        '    assert result["pta_marker_selected_count"] == 23\n'
        '    accounting = result["pta_marker_accounting"]\n'
        '    assert accounting["selected_count"] == 23\n'
        '    assert accounting["probe_count"] == 23\n'
        '    assert len(result["pta_marker_telemetry"]) == 23\n'
        '    assert (\n'
        '        accounting["computed_count"]\n'
        '        + accounting["no_signal_count"]\n'
        '        + accounting["dependency_unavailable_count"]\n'
        '        + accounting["error_count"]\n'
        '        == accounting["probe_count"]\n'
        '    )\n'
        '    assert result["pta_marker_output_count"] == accounting["computed_count"] + accounting["no_signal_count"]\n'
        '    assert accounting["accounting_pass"] is True',
    )
    replace_once(
        path,
        '    else:\n'
        '        assert fmfm_alignment["source_mode"] == "real"\n'
        '        assert fmfm_alignment["raw_output_present"] is True\n'
        '        assert fmfm_alignment["explanation_only"] is True\n'
        '    assert fmfm_alignment["usable_for_probability"] is False',
        '    else:\n'
        '        assert fmfm_alignment["source_mode"] in {"real", "synthetic_fallback"}\n'
        '        assert fmfm_alignment["raw_output_present"] is True\n'
        '        assert fmfm_alignment["explanation_only"] is True\n'
        '        if fmfm_alignment["source_mode"] == "synthetic_fallback":\n'
        '            assert fmfm_alignment["usable_for_probability"] is False\n'
        '    assert fmfm_alignment["usable_for_probability"] is False',
    )


def patch_paper_guidance_tests() -> None:
    path = "apps/api/tests/test_paper_guidance_v188.py"
    append_once(
        path,
        "test_tv_v188_020_stage2_integrity_is_wired_before_d6",
        '''

def test_tv_v188_020_stage2_integrity_is_wired_before_d6():
    result = _run(_request())
    integrity = result.risk_summary["stage2_integrity"]
    assert integrity["canonical_snapshot_hash"] == result.snapshot_hash
    assert integrity["canonical_context_eligible"] is True
    assert integrity["paper_promotion_eligible"] is False
    assert integrity["trade_allowed"] is False
    assert integrity["order_routing_enabled"] is False
    assert integrity["live_trading_blocked"] is True
    assert "FINAL_CONFLUENCE_ARBITER" in result.engines_run
    states = {row["engine_id"]: row for row in integrity["engine_states"]}
    for engine_id in ("NINE_CANDLE_MEMORY", "PTA_MARKER_RUNTIME", "ORB_CORE", "AFRE"):
        assert states[engine_id]["availability"] == "SKIPPED"
        assert states[engine_id]["used_for_probability"] is False


def test_tv_v188_021_stage2_block_stops_before_d6(monkeypatch):
    class ForcedBlock:
        canonical_context_eligible = False
        hard_blockers = ("FORCED_STAGE2_BLOCK",)
        warnings = ("forced-stage2-warning",)
        output_hash = "f" * 64

        @staticmethod
        def as_dict():
            return {
                "status": "BLOCK",
                "canonical_context_eligible": False,
                "hard_blockers": ["FORCED_STAGE2_BLOCK"],
                "warnings": ["forced-stage2-warning"],
                "paper_promotion_eligible": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
            }

    monkeypatch.setattr(
        "app.behavior.paper_guidance_spine.build_stage2_integrity_report",
        lambda **_: ForcedBlock(),
    )
    result = _run(_request())
    assert result.final_band == "WAIT"
    assert "FINAL_CONFLUENCE_ARBITER" not in result.engines_run
    assert "D6_ARBITER:stage2_integrity_block" in result.engines_skipped
    assert result.arbiter_summary["arbiter_run"] is False
    assert result.arbiter_summary["blocked_before_d6"] is True
    assert any("FORCED_STAGE2_BLOCK" in blocker for blocker in result.blockers)
    assert result.risk_summary["stage2_integrity"]["canonical_context_eligible"] is False
''',
    )


def patch_stage2_tests() -> None:
    path = "apps/api/tests/decision_spine/test_stage2_integrity.py"
    append_once(
        path,
        "test_ds_s2_015_explicit_skipped_migration_evidence_degrades_without_authority",
        '''

def test_ds_s2_015_explicit_skipped_migration_evidence_degrades_without_authority():
    observation = EvidenceObservation(
        engine_id="PTA_MARKER_RUNTIME",
        source_snapshot_hash=SNAPSHOT,
        availability=Availability.SKIPPED,
        source_mode=SourceMode.UNKNOWN,
        used_for_probability=False,
        final_band_claimed=False,
        unavailable_reasons=("not D2-native yet",),
    )
    report = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        evidence_observations=[observation],
    )
    assert report.status == "DEGRADED"
    assert report.canonical_context_eligible is True
    assert report.paper_promotion_eligible is False
    assert report.trade_allowed is False
    assert report.order_routing_enabled is False
    assert report.live_trading_blocked is True
''',
    )


def main() -> None:
    expected = [
        "apps/api/app/models.py",
        "apps/api/app/behavior/nine_candle_hybrid.py",
        "apps/api/app/behavior/indicator_runtime_bridge.py",
        "apps/api/app/behavior/paper_guidance_spine.py",
        "apps/api/app/behavior/decision_spine/stage2_integrity.py",
        "apps/api/tests/test_api.py",
        "apps/api/tests/test_paper_guidance_v188.py",
    ]
    missing = [path for path in expected if not (ROOT / path).exists()]
    if missing:
        raise RuntimeError(f"Run from repository root; missing: {missing}")

    patch_stage2_integrity()
    patch_models()
    patch_nine_candle_hybrid()
    patch_pta_accounting()
    patch_authority_registry()
    patch_paper_guidance_wiring()
    patch_api_tests()
    patch_paper_guidance_tests()
    patch_stage2_tests()
    print("M0 Stage-2 stabilization patch applied with all scoped replacement assertions satisfied.")


if __name__ == "__main__":
    main()
