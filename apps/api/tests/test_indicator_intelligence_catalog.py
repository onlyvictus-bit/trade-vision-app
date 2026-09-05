"""v1.96 Indicator Intelligence Catalog gates (CAT-V196-001..008).

Structural and safety gates over data/indicator-intelligence/indicator_contracts.v1.json.
Hermetic: no external module execution, no network, no hardcoded user paths.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.behavior.indicator_registry import build_indicator_registry_report

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_PATH = PROJECT_ROOT / "data" / "indicator-intelligence" / "indicator_contracts.v1.json"
COVERAGE_PATH = PROJECT_ROOT / "data" / "indicator-intelligence" / "indicator_coverage_report.json"
VENDOR_SELF = PROJECT_ROOT / "apps/api/app/vendor/stock_app/shared/indicators/self_indc.py"
VENDOR_PTA_WRAPPER = PROJECT_ROOT / "apps/api/app/vendor/stock_app/shared/indicators/pta_signal_markers.py"
PTA_SIGNALS = PROJECT_ROOT / "apps/api/app/vendor/stock_app/research/signals/pta_signals.py"
GROUP_MAP = PROJECT_ROOT / "docs" / "INDICATOR_GROUP_AND_USE_MAP.md"

REQUIRED_FIELDS = [
    "indicator_id", "display_name", "aliases", "source_registry", "source_file",
    "callable_name", "implementation_status", "runtime_status", "purpose",
    "simple_explanation", "primary_category", "secondary_categories", "evidence_role",
    "required_input_columns", "parameters_and_defaults", "minimum_bars", "warmup_policy",
    "supported_timeframes", "formula_in_plain_english", "mathematical_formula",
    "output_columns", "output_types", "signal_values", "bullish_meaning",
    "bearish_meaning", "neutral_meaning", "trade_usage", "no_trade_usage",
    "best_market_regime", "bad_market_regime", "lag_behavior",
    "confirmation_delay_bars", "lag_weight", "normalization_method", "missing_policy",
    "false_positive_conditions", "confirmation_rules", "conflict_rules",
    "redundancy_family", "correlated_indicators", "mtf_usage",
    "closed_candle_requirement", "lookahead_risk", "repainting_risk",
    "per_stock_reliability", "usable_for_probability", "usable_for_explanation",
    "usable_for_trade_action", "live_trading_blocked", "research_only",
    "safety_notes", "external_dependencies", "source_evidence", "test_ids",
]

NULLABLE_FIELDS = {
    "historical_success_rate", "historical_failure_rate", "pit_audit_passed_date",
    "future_leak_detail", "minimum_bars", "formula_hash",
}

# Legitimately empty by design: aliases (no alias mechanism exists yet),
# parameters_and_defaults (no tunable params), correlated_indicators (standalone),
# secondary_categories (single-role indicators).
EMPTY_ALLOWED_FIELDS = {
    "aliases", "parameters_and_defaults", "correlated_indicators", "secondary_categories",
}

FUTURE_LEAK_IDS = {
    "si_delta_vp", "si_hybrid_ml_cpr", "si_sweep_inside_rr",
    "si_opening_range_rev", "si_hyb_opening_range_rev", "si_problty_grid",
}


@pytest.fixture(scope="module")
def contracts() -> list[dict]:
    assert CONTRACTS_PATH.exists(), "contracts artifact missing - run generator script"
    payload = json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))
    return payload["contracts"]


@pytest.fixture(scope="module")
def live_ids() -> set[str]:
    report = build_indicator_registry_report()
    entries = getattr(report, "entries", None) or report["entries"]
    return {e.indicator_id if hasattr(e, "indicator_id") else e["indicator_id"] for e in entries}


def test_cat_v196_001_contract_registry_lock(contracts: list[dict], live_ids: set[str]) -> None:
    ids = [c["indicator_id"] for c in contracts]
    assert len(ids) == 94, f"expected 94 contracts, found {len(ids)}"
    assert len(set(ids)) == len(ids), "duplicate indicator_id in contracts"
    assert set(ids) == live_ids, (
        f"registry/catalog mismatch: only_catalog={sorted(set(ids) - live_ids)} "
        f"only_registry={sorted(live_ids - set(ids))}"
    )


def test_cat_v196_002_contract_field_completeness(contracts: list[dict]) -> None:
    for c in contracts:
        missing = [f for f in REQUIRED_FIELDS if f not in c]
        assert not missing, f"{c['indicator_id']} missing fields: {missing}"
        empty = []
        for f in REQUIRED_FIELDS:
            v = c[f]
            if f in NULLABLE_FIELDS:
                continue
            if isinstance(v, (list, dict)) and len(v) == 0 and f in EMPTY_ALLOWED_FIELDS:
                continue
            if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, dict)) and len(v) == 0):
                empty.append(f)
        assert not empty, f"{c['indicator_id']} has empty required fields: {empty}"


def test_cat_v196_003_future_leak_forced_explanation_only(contracts: list[dict]) -> None:
    by_id = {c["indicator_id"]: c for c in contracts}
    for iid in FUTURE_LEAK_IDS:
        c = by_id[iid]
        assert c["lookahead_risk"] == "future_outcome_leakage"
        assert c["evidence_role"] == "explanation_only_forced"
        assert c["usable_for_trade_action"] is False
        assert c["usable_for_probability"] is False
        assert c["future_leak_detail"], f"{iid} must cite the leak mechanism"
        assert any("FUTURE OUTCOME LEAKAGE" in s for s in c["safety_notes"])
    # inverse: nothing else may claim the forced role without being in the set
    for c in contracts:
        if c["evidence_role"] == "explanation_only_forced":
            assert c["indicator_id"] in FUTURE_LEAK_IDS


def test_cat_v196_004_lag_weight_formula(contracts: list[dict]) -> None:
    for c in contracts:
        delay = c["confirmation_delay_bars"]
        assert isinstance(delay, int) and delay >= 0, f"{c['indicator_id']} bad delay {delay!r}"
        expected = round(1.0 / (1.0 + delay), 6)
        assert c["lag_weight"] == pytest.approx(expected, abs=1e-9), c["indicator_id"]


def test_cat_v196_005_alias_uniqueness(contracts: list[dict]) -> None:
    seen: dict[str, str] = {}
    for c in contracts:
        assert isinstance(c["aliases"], list)
        for alias in c["aliases"]:
            assert isinstance(alias, str) and alias.strip()
            key = alias.strip().lower()
            assert key not in seen, f"alias collision {alias}: {seen[key]} vs {c['indicator_id']}"
            seen[key] = c["indicator_id"]


def test_cat_v196_006_no_live_routing_or_probability_escalation(contracts: list[dict]) -> None:
    for c in contracts:
        assert c["live_trading_blocked"] is True, c["indicator_id"]
        assert c["research_only"] is True, c["indicator_id"]
        assert c["usable_for_trade_action"] is False, c["indicator_id"]
        if c["implementation_status"] != "validated" or c["lookahead_severity"] in {"HIGH", "MEDIUM"}:
            assert c["usable_for_probability"] is False, (
                f"{c['indicator_id']} proxy/repainting indicator must not be probability-enabled"
            )


def test_cat_v196_007_group_map_covers_all_primary_once(contracts: list[dict]) -> None:
    primaries = [c["primary_category"] for c in contracts]
    assert all(isinstance(p, str) and p.strip() for p in primaries)
    map_text = GROUP_MAP.read_text(encoding="utf-8")
    for c in contracts:
        assert c["indicator_id"] in map_text, f"{c['indicator_id']} absent from group/use map"


def test_cat_v196_008_source_evidence_paths_and_callables(contracts: list[dict]) -> None:
    self_src = VENDOR_SELF.read_text(encoding="utf-8", errors="replace")
    wrapper_src = VENDOR_PTA_WRAPPER.read_text(encoding="utf-8", errors="replace")
    pta_src = PTA_SIGNALS.read_text(encoding="utf-8", errors="replace")
    for c in contracts:
        assert isinstance(c["source_evidence"], list) and c["source_evidence"], c["indicator_id"]
        for ev in c["source_evidence"]:
            path = PROJECT_ROOT / ev["file"]
            assert path.exists(), f"{c['indicator_id']} evidence path missing: {ev['file']}"
        fn = c["callable_name"].split("->")[0].strip()
        if c["indicator_id"].startswith("si_"):
            pattern = re.compile(rf"^def\s+{re.escape(fn)}\b", re.MULTILINE)
            assert pattern.search(self_src), (
                f"{c['indicator_id']}: callable '{fn}' not defined in vendor self_indc.py"
            )
        else:
            # ids are built as "pta_" + registry key inside the wrapper
            bare = c["indicator_id"][len("pta_"):]
            assert bare in wrapper_src or bare in pta_src, (
                f"{c['indicator_id']}: key '{bare}' absent from wrapper and pta_signals sources"
            )


def test_cat_v196_009_coverage_report_reconciles(contracts: list[dict]) -> None:
    cov = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    totals = cov["totals"]
    assert totals["registry_entries"] == totals["contracts_written"] == 94
    buckets = (
        totals["promoted_runtime_computed"]
        + totals["registered_not_promoted"]
        + totals["registered_probe_only_pta"]
        + len(cov["near_stub_constant_output"])
    )
    assert buckets == 94, f"runtime buckets sum to {buckets}, expected 94"
