from __future__ import annotations

import hashlib
import re
from typing import Any

from app.behavior.orb_build0_requirement_catalog import AUDIT_BASE_SHA, MASTER, MASTER_SHA, _DELTA_ROWS, _R_ROWS


def _norm(value: str) -> str:
    return " ".join(value.strip().split())


def _hash(value: str) -> str:
    return hashlib.sha256(_norm(value).encode("utf-8")).hexdigest()


_SOURCE_ROWS = (
    ("SRC-MASTER", MASTER, MASTER_SHA, "canonical synthesized ORB build specification"),
    ("SRC-SCOPE", "docs/ORB_INTRADAY_STOCK_COMMODITY_SCOPE_AND_FLOW_HARDENING_2026-09-12.md", "851d13267805ee202f0c5d8fa3d9cd70bd364c81", "stock/commodity scope and flow hardening"),
    ("SRC-FUTURE", "docs/ORB_AFRE_CANONICAL_FUTURE_BUILD_PLAN_2026-09-10.md", "38fab7e95f0f00bc56d0368804f7717f24cc4941", "parent canonical ORB/AFRE plan"),
    ("SRC-SIMPLE", "docs/ORB_SIMPLE_FLOW.md", "594f155a8976f6a4ce1c4f16ddbae5d99026f7f3", "legacy simple flow regression source"),
    ("SRC-FLOW", "docs/plans/FINAL_REQUIRED_FLOW.md", "608b4dcff43f4119894cca93e6445c5f370d4997", "required product flow"),
    ("SRC-RESEARCH", "docs/plans/ORB_RESEARCH_ENGINE_PLAN.md", "0696ca63daff27788b625a604c6d084d2b1b0db8", "ORB research engine plan"),
    ("SRC-TIMING", "docs/plans/ORB_TIMING_RESEARCH_V197.md", "3dd0d56c3625c54f907d3e05381d632d735667f6", "v1.97 timing research provenance"),
    ("SRC-CONTEXT", "docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md", "efc06504ef0f67cbfb8a2f8d5e6494a65a6af0bf", "context-native ORB plan"),
    ("SRC-STRATEGY", "docs/plans/ORB_STRATEGY_MEMORANDUM.md", "0ab220591933795f53ffcef7f27a4b37891177a5", "strategy memorandum"),
    ("SRC-EXT", "docs/plans/ORB_EXTERNAL_REVIEW_BRIEF.md", "87129c8a727f883ce9f5aa0cdbdce30d426300b5", "external review brief"),
    ("SRC-GAP", "docs/plans/ORB_GAP_TRADING_EXTERNAL_REVIEW_BRIEF.md", "03c19115d418609307d6c9ed0177b702a25ce9dd", "gap trading review brief"),
    ("SRC-KIMI2", "docs/plans/ORB_V201B_NSE_REVIEW_KIMI_PART2.md", "90e6cc9a0895ce04a9fc135bf615462421e54ce4", "archived v2.01 review part 2"),
    ("SRC-KIMI3", "docs/plans/ORB_V201C_NSE_REVIEW_KIMI_PART3.md", "3acf58fe692b0a1707778e819863e82b142a63e6", "archived v2.01 review part 3"),
    ("SRC-M4-STATUS", "docs/CANONICAL_BUILD_STATUS.md", "bafcd7d081633e3f64f6ab8319226d2c09c69b82", "canonical build status"),
    ("SRC-M4-INDEX", "docs/M4_D6_ORCHESTRATION_MASTER_BUILD_INDEX_2026-09-09.md", "f089b18efa9c19da76974ecc5d20ddb8274f1a70", "M4/D6 orchestration index"),
    ("SRC-M4-CF", "docs/M4_4_SCENARIO_FAILURE_AND_COUNTERFACTUAL_REASONING_2026-09-09.md", "09c8d5dceb81bffa6b7b870adb62ca317529e251", "M4 scenario/failure/counterfactual design"),
    ("SRC-M4-HYP", "docs/M4_HYPOTHESIS_BOX_REFERENCE_2026-09-10.md", "e4ee56365ff4a4512783a83eac96708df6344ee6", "M4 hypothesis reference"),
    ("SRC-M4-HYP2", "docs/M4_HYPOTHESIS_BOX_V2_IMPLEMENTATION_PLAN_2026-09-10.md", "b974a1fea5f88079ade34942a26ad3173bb3055c", "M4 hypothesis v2 implementation plan"),
    ("SRC-M4-COG", "docs/M4_TRADING_COGNITIVE_ARCHITECTURE_REFERENCE_2026-09-10.md", "4f3aab032844b8ad1d27280589f2870941d43bd8", "M4 cognitive architecture reference"),
    ("SRC-D1", "apps/api/app/behavior/paper_guidance_spine_legacy.py", "085c6867cbbee13ee786b7557d35bbd69ebf8977", "current D1 code truth"),
    ("SRC-CONFIG", "apps/api/app/behavior/paper_guidance_config.py", "fe8db6103b7418cdf6345771cd06c4c4a03304f0", "current paper configuration truth"),
    ("SRC-AUTH", "apps/api/app/behavior/decision_spine/authority_registry.py", "6e77936112b0244c6951a593127a20b01435c9c4", "current authority registry truth"),
)


def _test_for(owner: str) -> str:
    if "authority" in owner.lower(): return "ORB-B0-AUTHORITY-LOCK"
    if owner.startswith("D6"): return "ORB-B11-D6-HANDOFF"
    match = re.search(r"B(\d+)", owner)
    if match: return f"ORB-B{match.group(1)}-REQUIREMENT-CONTRACT"
    if "calc" in owner.lower(): return "ORB-B4-CALCULATION-REGISTRY"
    if "migration" in owner.lower(): return "ORB-B14-STRANGLER-MIGRATION"
    if "architecture" in owner.lower(): return "ORB-GLOBAL-ARCHITECTURE-INVARIANTS"
    if owner == "all": return "ORB-B14-CROSSCUTTING-INVARIANTS"
    return "ORB-B0-TRACEABILITY"


def _row(rid: str, text: str, owner: str, section: str, line: str, disposition: str, *, requirement_class: str) -> dict[str, Any]:
    return {
        "requirement_id": rid, "source_doc_path": MASTER, "source_blob_sha": MASTER_SHA,
        "source_section": section, "source_line_range_or_text_hash": _hash(line),
        "requirement_text": text, "requirement_text_hash": _hash(text), "requirement_class": requirement_class,
        "stage_owner": owner, "target_section": section, "contract_ids": ["OrbRequirementManifestV1"],
        "calculation_ids": [], "test_ids": [], "fixture_ids": [], "disposition": disposition,
        "supersedes": [], "implementation_evidence": [], "status": "MAPPED", "notes": "",
        "source_locator": {"nearest_heading_path": [section], "source_block_kind": "TABLE_ROW", "normalized_text_hash": _hash(line), "optional_rule_id": rid},
    }


def build_manifest() -> dict[str, Any]:
    sources = []
    for sid, path, sha, role in _SOURCE_ROWS:
        item = {"source_id": sid, "path": path, "blob_sha": sha, "role": role, "requires_review_receipt": path != MASTER}
        if path != MASTER:
            item["review_receipt"] = {"canonical_master_doc": MASTER, "canonical_master_blob_sha": MASTER_SHA, "audit_base_sha": AUDIT_BASE_SHA, "coverage": "FULL_SOURCE_RECONCILED_BY_TWO_PASS_AUDIT", "drift_policy": "ANY_BLOB_CHANGE_REQUIRES_REAUDIT"}
        sources.append(item)

    requirements = []
    for number, text, owner in _R_ROWS:
        rid = f"R{number}"
        line = f"| {rid} | {text} | {owner} |"
        item = _row(rid, text, owner, "47. R1–R105 accumulated-requirement traceability matrix", line, "TARGET_REQUIRED", requirement_class="ACCUMULATED_REQUIREMENT")
        item["test_ids"] = [_test_for(owner)]
        item["notes"] = "Future implementation requirement; BUILD-0 verifies traceability, not completion."
        if rid in {"R19", "R102"}:
            item["allow_duplicate_text_hash"] = True
            item["semantic_equivalence_group"] = "DETERMINISTIC_REPLAY"
        requirements.append(item)

    fixtures = {"D020":"FIXTURE-MEMORY-30", "D021":"FIXTURE-PAPER-CONFIG-DEFAULTS", "D022":"FIXTURE-D1-GATE-INVENTORY"}
    for rid, anchor, text, owner, disposition, line in _DELTA_ROWS:
        item = _row(rid, text, owner, "52. Second line-by-line audit delta matrix — binding additions", line, disposition, requirement_class="SECOND_AUDIT_BINDING_CANARY")
        item["notes"] = anchor
        if disposition == "TARGET_REQUIRED": item["test_ids"] = [_test_for(owner)]
        elif disposition == "CURRENT_REGRESSION_BASELINE":
            item["test_ids"] = ["ORB-B0-REGRESSION-BASELINE"]; item["fixture_ids"] = [fixtures[rid]]
        elif disposition == "RESEARCH_CANDIDATE": item.update(authority=False, proof_before_activation=True)
        elif disposition == "SUPERSEDED":
            replacement = "explicit advisor availability/source-mode contract" if rid == "D013" else "unavailable-state law; missing risk control never creates permission"
            item.update(replacement=replacement, reason="Legacy sentinel/fail-open semantics violate explicit availability and safety laws.", authority=False)
        elif disposition == "OUT_OF_SCOPE_FOR_ORB": item.update(responsibility_note="Execution/broker actions belong outside ORB; ORB may emit only non-executing safety/risk evidence to D6/human paper workflow.", authority=False, may_execute=False)
        if rid == "D012": item.update(advisory_only=True, authority=False, may_set_final_band=False, may_execute=False)
        if rid == "D013": item["semantic_tags"] = ["NUMERIC_NEUTRAL_MISSINGNESS"]
        if rid == "D016": item["semantic_tags"] = ["FAIL_OPEN_UNAVAILABLE"]
        if rid == "D023": item["semantic_tags"] = ["BROKER_EXECUTION_COMMAND"]
        requirements.append(item)

    blocker_line = '- exact source of any previously referenced “12-dimension readiness matrix” not yet verified by this re-audit.'
    historical_name = "Historical 211-link activation contract: 12 assessment dimensions plus separate live proof."
    historical_text = (
        historical_name
        + " The 12 assessment dimensions are: Inventory ID and exact URL; Verified owner and source role; "
        "Duplicate/source-family mapping; Intended decision field or non-trading use; API/artifact, method and parameters; "
        "Headers, cookies, authentication and licensing; Content type, schema and units; Data date, publication time, frequency, revisions and valid-empty policy; "
        "Normalized table, primary key and point-in-time join; Gate effect and prohibited claims; Failure tests; Activation verdict. "
        "Live runtime proof is a separate 13th requirement."
    )
    historical = _row("BLOCKER-12D-001", historical_text, "BUILD-0", "50. Known blockers and unresolved uncertainties", blocker_line, "HISTORICAL_EVIDENCE", requirement_class="RESOLVED_SOURCE_AUDIT")
    historical["source_locator"]["source_block_kind"] = "BULLET"
    historical.update(
        verification_status="SOURCE_VERIFIED",
        corrected_name=historical_name,
        notes="Historical source recovered outside this repository; preserved as evidence only, not as the current runtime readiness schema.",
        historical_source_evidence={
            "activation_matrix_path":"D:/TrendForge/delete/source_link_api_merge_2026-07-14/ALL_211_LINK_ACTIVATION_MATRIX.csv",
            "activation_prompt_path":"D:/TrendForge/delete/source_link_api_merge_2026-07-14/ALL_211_LINK_ACTIVATION_PROMPT.md",
            "source_registry_path":"D:/TrendForge/TREND_FORGE_SOURCE_REGISTRY.md",
            "archive_status_path":"D:/TrendForge/docs/BUILD_STATUS.md",
            "matrix_sha256":"781069985bf029cb2ad6b4479ac5ff28141362aa6297d5f68601993d53ca0a28",
            "row_count":211,
            "unique_id_count":211,
            "matrix_column_count":12,
            "can_unlock_ready_now_no_count":211,
            "assessment_dimensions":[
                "Inventory ID and exact URL",
                "Verified owner and source role",
                "Duplicate/source-family mapping",
                "Intended decision field or non-trading use",
                "API/artifact, method and parameters",
                "Headers, cookies, authentication and licensing",
                "Content type, schema and units",
                "Data date, publication time, frequency, revisions and valid-empty policy",
                "Normalized table, primary key and point-in-time join",
                "Gate effect and prohibited claims",
                "Failure tests",
                "Activation verdict",
            ],
            "live_runtime_proof":"SEPARATE_13TH_REQUIREMENT",
            "current_matrix_distinction":"D:/TrendForge/backend/trendforge_api/source_cohort_r0b.py is newer and different: 8 declared dimensions and 9 evaluated dimensions; it is not the historical 12-dimension definition.",
            "provenance_note":"Original hash/provenance preserved in TREND_FORGE_SOURCE_REGISTRY.md; BUILD_STATUS.md records archival move rather than deletion.",
        },
    )
    requirements.append(historical)

    test_ids = {test_id for item in requirements for test_id in item.get("test_ids", [])}
    test_ids |= {"ORB-B0-MANIFEST-SCHEMA","ORB-B0-SOURCE-DRIFT","ORB-B0-CANARY-GUARD","ORB-B0-DETERMINISM","ORB-B0-D1-DRIFT","ORB-B0-CONFIG-DRIFT","ORB-B0-AUTHORITY-LOCK","ORB-B0-REGRESSION-BASELINE"}

    baseline = {
        "schema_version":"OrbBaselineManifestV1", "baseline_version":"ORB-BUILD0-BASELINE-V1", "audit_source_base_sha":AUDIT_BASE_SHA, "branch":"m4-d6-orchestration-redesign",
        "safety":{"research_only":True,"trade_allowed":False,"order_routing_enabled":False,"live_trading_blocked":True,"human_approval_required":True},
        "authority":{"enabled":True,"final_band_authority":"FINAL_CONFLUENCE_ARBITER","reviewer_ids":["KRONOS","GEMINI","GROK","TWIN_ARBITER"]},
        "d1_gate_inventory":{"enabled":True,"path":"apps/api/app/behavior/paper_guidance_spine_legacy.py","function":"build_d1_safety_gate","checks":[
            {"check_id":"PG-D1-001","name":"Research-only system mode"},{"check_id":"PG-D1-002","name":"Kill switch is armed"},{"check_id":"PG-D1-003","name":"Symbol identity matches candle series"},{"check_id":"PG-D1-004","name":"Timeframe identity matches candle series"},{"check_id":"PG-D1-005","name":"Input bar count is bounded"},{"check_id":"PG-D1-006","name":"OHLCV values are finite"},{"check_id":"PG-D1-007","name":"Data quality meets threshold"},{"check_id":"PG-D1-008","name":"All supplied candles are closed and point-in-time safe"},{"check_id":"PG-D1-009","name":"Broker credentials and routing are unavailable"}]},
        "config_defaults":{"enabled":True,"path":"apps/api/app/behavior/paper_guidance_config.py","classes":{"PaperGuidanceConfig":{"minimum_data_quality_score":0.85,"minimum_evidence_count":30,"low_evidence_confidence_cap":0.55,"p0_confidence_cap":0.60,"maximum_input_bars":5000},"PaperGuidanceStorageConfig":{"maximum_ticket_age_seconds":900,"retention_days":365,"maximum_observation_bars":500,"spread_bps":1.0,"slippage_bps":1.0,"impact_bps":0.5,"brokerage_bps":1.0,"feedback_minimum_samples":30,"feedback_quarantine_win_rate":0.35}}},
        "regression_test_paths":["apps/api/tests/test_orb_v189.py","apps/api/tests/test_orb_v190.py","apps/api/tests/test_orb_v191.py","apps/api/tests/test_orb_guidance_v192.py","apps/api/tests/test_orb_paper_ledger_v193.py","apps/api/tests/test_orb_feedback_hardening_v194.py","apps/api/tests/test_orb_timing_v197.py","apps/api/tests/test_reconstruction_v200.py","apps/api/tests/test_orb_opening_scenarios_v201.py","apps/api/tests/test_trendforge_bridge.py","apps/api/tests/decision_spine/test_stage2_integrity.py","apps/api/tests/decision_spine/test_m3_3_authority_complete.py","apps/api/tests/test_api.py"],
    }
    readiness = [
        {"capability_id":"LOCAL_OHLCV_DERIVED_FACTS","state":"COMPUTABLE_LOCAL","provenance":"Master plan Section 49: locally computable OHLCV-derived facts remain distinct from feed requirements."},
        {"capability_id":"EXCHANGE_CALENDAR_HISTORY","state":"NEEDS_VERSIONED_FILE","provenance":"Master plan Sections 49-50 require effective-date official calendar history."},
        {"capability_id":"COMMODITY_INSTRUMENT_MASTER","state":"UNAVAILABLE","provenance":"Master plan Section 50 lists generic commodity instrument master/provider mapping as unresolved."},
        {"capability_id":"SETTLEMENT_CONTEXT","state":"NEEDS_EXTERNAL_FEED","provenance":"Master plan Sections 49-50 require a settlement source contract before authority."},
        {"capability_id":"EVENT_NEWS_CONTEXT","state":"NEEDS_EXTERNAL_FEED","provenance":"Master plan Section 49 forbids authoritative event/news gates before a PIT-safe source contract."},
        {"capability_id":"DERIVATIVES_OI_CONTEXT","state":"NEEDS_EXTERNAL_FEED","provenance":"Master plan Section 49 forbids authoritative derivatives/OI gates before a PIT-safe source contract."},
        {"capability_id":"TRENDFORGE_HISTORICAL_SELECTOR","state":"UNAVAILABLE","provenance":"Master plan Section 50 lists historical Trendforge/premarket retention for candidate reconstruction as unresolved."},
    ]
    canaries = [
        {"canary_id":"CANARY-CLOCK-TF","terms":["CLOCK_TF_FIT","TIMING_V197_PROFILE","CLOCK_TF_LAYER_A_LEGACY_PROFILE"],"requirement_ids":["D001"]},
        {"canary_id":"CANARY-PRIOR-PATTERN","terms":["TREND_UP","TREND_DOWN","GAP_FILL","RANGE","UNKNOWN"],"requirement_ids":["D002"]},
        {"canary_id":"CANARY-ZONES","terms":["Z1","Z2","Z3","Z4","Z5"],"requirement_ids":["D003"]},
        {"canary_id":"CANARY-PDC","terms":["PDC_TOUCHED","PDC_CLOSED_BEYOND"],"requirement_ids":["D004"]},
        {"canary_id":"CANARY-HYPOTHESIS","terms":["expected_sequence","failure_sequence","anti_thesis"],"requirement_ids":["D010"]},
        {"canary_id":"CANARY-ADVISOR","terms":["OrbAdvisorObservationV1"],"requirement_ids":["D012"]},
        {"canary_id":"CANARY-E3","terms":["PRE_E3_FIX","POST_E3_FIX"],"requirement_ids":["D014"]},
        {"canary_id":"CANARY-D1-PRECOMPUTE","terms":["precompute D-1"],"requirement_ids":["D006"]},
        {"canary_id":"CANARY-DUAL-SOURCE","terms":["dual-source previous-session mismatch"],"requirement_ids":["D007"]},
        {"canary_id":"CANARY-COMMODITY","terms":["COMMODITY_FUTURE","price_precision"],"requirement_ids":["D008"]},
        {"canary_id":"CANARY-30-DEFAULTS","terms":["minimum_evidence_count","feedback_minimum_samples"],"requirement_ids":["D021"]},
    ]
    return {
        "schema_version":"OrbRequirementManifestV1", "manifest_version":"ORB-BUILD0-REQUIREMENTS-V1", "audit_tool_contract":"audit_orb_requirement_coverage",
        "baseline":baseline, "sources":sources,
        "registries":{"stages":[{"stage_id":f"BUILD-{i}"} for i in range(15)]+[{"stage_id":"D6"},{"stage_id":"GLOBAL"}],"contracts":[{"contract_id":"OrbBaselineManifestV1","owner":"BUILD-0"},{"contract_id":"OrbRequirementManifestV1","owner":"BUILD-0"},{"contract_id":"OrbRequirementCoverageReportV1","owner":"BUILD-0"},{"contract_id":"OrbSourceReadinessV1","owner":"BUILD-0"}],"calculations":[],"tests":[{"test_id":value,"owner":"BUILD-0" if value.startswith("ORB-B0") else "FUTURE_STAGE_CONTRACT"} for value in sorted(test_ids)],"fixtures":[{"fixture_id":"FIXTURE-MEMORY-30"},{"fixture_id":"FIXTURE-PAPER-CONFIG-DEFAULTS"},{"fixture_id":"FIXTURE-D1-GATE-INVENTORY"}]},
        "source_readiness":readiness, "canaries":canaries, "requirements":requirements,
        "coverage_policy":{"required_pct":100.0,"orphan_targets_allowed":0,"unexplained_source_drift_allowed":0,"hidden_conflicts_allowed":0,"missing_canaries_allowed":0,"research_priors_authoritative_without_proof":False,"deterministic_replay_required":True,"registered_blockers_prevent_lock":True,"require_r1_r105":True,"allowed_lock_blockers":[]},
    }
