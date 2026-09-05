from __future__ import annotations

import hashlib
import json
from typing import Any

from .nine_candle_hybrid import build_feature_manifest


INTEGRITY_VERSION = "9c-feature-manifest-integrity.v1"
ALLOWED_NORMALIZATION_METHODS = {
    "bounded_minmax",
    "event_strength_and_recency",
    "point_in_time_level_distance_atr",
    "rolling_zscore_clipped",
}


def build_feature_manifest_integrity_report() -> dict[str, Any]:
    manifest = build_feature_manifest()
    rows = [_row(entry) for entry in manifest.entries]
    failures = _failures(manifest, rows)
    warnings = _warnings(rows)
    report = {
        "integrity_version": INTEGRITY_VERSION,
        "feature_manifest_version": manifest.feature_manifest_version,
        "source_registry_version": manifest.source_registry_version,
        "feature_count": manifest.feature_count,
        "vector_dimension": manifest.vector_dimension,
        "stable_order_hash": manifest.stable_order_hash,
        "policy_hash": _policy_hash(rows),
        "normalization_methods": sorted({row["normalization_method"] for row in rows}),
        "missing_policy_counts": _count(rows, "missing_policy"),
        "similarity_policy_counts": _count(rows, "similarity_policy"),
        "probability_enabled_count": sum(1 for row in rows if row["probability_enabled"]),
        "missing_mask_enabled_count": sum(1 for row in rows if row["missing_mask_enabled"]),
        "active_feature_count": sum(1 for row in rows if row["is_active"]),
        "rows": rows,
        "checks": {
            "feature_count_matches_vector_dimension": manifest.feature_count == manifest.vector_dimension == len(rows),
            "feature_indices_contiguous": [row["feature_index"] for row in rows] == list(range(len(rows))),
            "feature_ids_unique": len({row["feature_id"] for row in rows}) == len(rows),
            "normalization_methods_allowed": all(row["normalization_method"] in ALLOWED_NORMALIZATION_METHODS for row in rows),
            "bounded_indicators_not_zscore": all(not row["bounded_indicator"] or row["normalization_method"] == "bounded_minmax" for row in rows),
            "missing_masks_enabled": all(row["missing_mask_enabled"] for row in rows),
            "missing_defaults_are_not_zero_signals": all(row["missing_default"] is None for row in rows),
            "low_variance_is_not_missing": all(row["low_variance_policy"] == "low_variance_flag_not_missing" for row in rows),
            "masked_cosine_required": all(row["similarity_policy"] == "masked_cosine_min_overlap_0_70" for row in rows),
            "probability_disabled_until_promotion": all(not row["probability_enabled"] for row in rows),
        },
        "failure_reasons": failures,
        "warnings": warnings,
        "wait_required": bool(failures),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    report["integrity_hash"] = _hash(
        json.dumps(
            {key: value for key, value in report.items() if key != "integrity_hash"},
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
    )
    return report


def _row(entry: Any) -> dict[str, Any]:
    feature_id = str(entry.feature_id)
    method = str(entry.normalization_method)
    bounded = any(token in feature_id.lower() for token in ("rsi", "mfi", "cmf", "percent", "pct", "stoch"))
    return {
        "feature_id": feature_id,
        "feature_index": int(entry.feature_index),
        "feature_type": str(entry.feature_type),
        "feature_block": str(entry.feature_block),
        "normalization_method": method,
        "normalization_formula": entry.normalization_formula,
        "bounded_indicator": bounded,
        "missing_default": entry.missing_default,
        "missing_mask_enabled": bool(entry.missing_mask_enabled),
        "missing_policy": str(entry.missing_policy),
        "low_variance_policy": str(entry.low_variance_policy),
        "similarity_policy": str(entry.similarity_policy),
        "is_active": bool(entry.is_active),
        "probability_enabled": bool(entry.probability_enabled),
    }


def _failures(manifest: Any, rows: list[dict[str, Any]]) -> list[str]:
    checks = {
        "feature_count_vector_dimension_mismatch": not (manifest.feature_count == manifest.vector_dimension == len(rows)),
        "feature_indices_not_contiguous": [row["feature_index"] for row in rows] != list(range(len(rows))),
        "duplicate_feature_id": len({row["feature_id"] for row in rows}) != len(rows),
        "normalization_method_not_allowed": any(row["normalization_method"] not in ALLOWED_NORMALIZATION_METHODS for row in rows),
        "bounded_indicator_uses_non_minmax": any(row["bounded_indicator"] and row["normalization_method"] != "bounded_minmax" for row in rows),
        "missing_mask_disabled": any(not row["missing_mask_enabled"] for row in rows),
        "missing_default_zero_signal_risk": any(row["missing_default"] is not None for row in rows),
        "low_variance_marked_as_missing_risk": any(row["low_variance_policy"] != "low_variance_flag_not_missing" for row in rows),
        "masked_cosine_not_required": any(row["similarity_policy"] != "masked_cosine_min_overlap_0_70" for row in rows),
        "probability_enabled_without_promotion": any(row["probability_enabled"] for row in rows),
    }
    return [name for name, failed in checks.items() if failed]


def _warnings(rows: list[dict[str, Any]]) -> list[str]:
    warnings = []
    if all(not row["probability_enabled"] for row in rows):
        warnings.append("all feature slots remain probability-disabled until promotion gates and evidence pass")
    warnings.append("missing values require masked cosine; two missing zeros cannot create similarity")
    warnings.append("low variance is represented as low_variance_flag, not missing_mask")
    return warnings


def _count(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _policy_hash(rows: list[dict[str, Any]]) -> str:
    payload = [
        {
            "feature_id": row["feature_id"],
            "feature_index": row["feature_index"],
            "normalization_method": row["normalization_method"],
            "missing_policy": row["missing_policy"],
            "low_variance_policy": row["low_variance_policy"],
            "similarity_policy": row["similarity_policy"],
            "probability_enabled": row["probability_enabled"],
        }
        for row in rows
    ]
    return _hash(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
