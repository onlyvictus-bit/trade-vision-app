from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..models import NineCandleModelPrediction, ProbabilityCalibrationBin


CALIBRATION_VERSION = "9c-evidence-calibration.v1"
MODEL_VERSION = "mock"
PRIOR_TARGETS = 2.0
PRIOR_STOPS = 2.0
PRIOR_TOTAL = 6.0


def build_evidence_calibration_bins(symbol: str = "RELIANCE", timeframe: str = "1m") -> list[ProbabilityCalibrationBin]:
    from .nine_candle_history import build_path_analog_report

    report = build_path_analog_report(symbol, timeframe, limit=25)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for match in report["top_matches"]:
        buckets[_bucket_name(float(match["similarity_score"]))].append(match)
    rows: list[ProbabilityCalibrationBin] = []
    for bucket in ["0.40-0.50", "0.50-0.60", "0.60-0.70", "0.70-0.80", "0.80-0.90", "0.90-1.00"]:
        matches = buckets.get(bucket, [])
        if not matches:
            continue
        target_count = sum(1 for item in matches if item["outcome_label"] == "TARGET_HIT")
        stop_count = sum(1 for item in matches if item["outcome_label"] in {"SL_HIT", "FAKE_BREAKOUT"})
        total = len(matches)
        target_rate = _shrink(target_count, total)
        stop_rate = _shrink(stop_count, total)
        expected_midpoint = _bucket_midpoint(bucket)
        rows.append(
            ProbabilityCalibrationBin(
                predicted_bucket=bucket,
                actual_target_rate=target_rate,
                actual_stop_rate=stop_rate,
                calibration_error=round(abs(target_rate - expected_midpoint), 6),
                sample_count=total,
            )
        )
    return rows or [
        ProbabilityCalibrationBin(
            predicted_bucket="insufficient-history",
            actual_target_rate=0.0,
            actual_stop_rate=0.0,
            calibration_error=1.0,
            sample_count=0,
        )
    ]


def build_evidence_model_status(symbol: str = "RELIANCE", timeframe: str = "1m") -> NineCandleModelPrediction:
    from .nine_candle_history import build_path_analog_report

    report = build_path_analog_report(symbol, timeframe, limit=25)
    total = int(report["total_matches"])
    target_count = int(report["winner_like_matches"])
    stop_count = int(report["failure_like_matches"])
    fakeout_count = sum(1 for item in report["top_matches"] if item["outcome_label"] == "FAKE_BREAKOUT")
    target_prob = _shrink(target_count, total)
    stop_prob = _shrink(stop_count, total)
    fakeout_prob = _shrink(fakeout_count, max(len(report["top_matches"]), 1), prior_successes=1.0, prior_total=4.0)
    expected_r_after_cost = round((target_prob * 1.0) - (stop_prob * 0.70) - (fakeout_prob * 0.20) - 0.03, 6)
    return NineCandleModelPrediction(
        model_version=MODEL_VERSION,
        usable_for_probability=False,
        calibrated_target_prob=target_prob,
        calibrated_stop_prob=stop_prob,
        calibrated_fakeout_prob=fakeout_prob,
        expected_r_after_cost=expected_r_after_cost,
        model_edge=round(target_prob - stop_prob, 6),
        weights_mutated_live=False,
        live_retraining_enabled=False,
        paper_candidate_allowed=False,
    )


def build_model_promotion_guard(symbol: str = "RELIANCE", timeframe: str = "1m") -> dict[str, Any]:
    model = build_evidence_model_status(symbol, timeframe)
    bins = build_evidence_calibration_bins(symbol, timeframe)
    calibration_sample_count = sum(row.sample_count for row in bins)
    max_error = max((row.calibration_error for row in bins), default=1.0)
    return {
        "promotion_guard_version": "9c-model-promotion-guard.v1",
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "model_version": model.model_version,
        "usable_for_probability": model.usable_for_probability,
        "paper_candidate_allowed": model.paper_candidate_allowed,
        "weights_mutated_live": model.weights_mutated_live,
        "live_retraining_enabled": model.live_retraining_enabled,
        "calibration_sample_count": calibration_sample_count,
        "max_calibration_error": round(max_error, 6),
        "promotion_allowed": False,
        "block_reasons": [
            "model_version=mock",
            "usable_for_probability=false",
            "LightGBM batch model has not been trained/promoted",
            "live route remains blocked",
        ],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _bucket_name(score: float) -> str:
    bounded = max(0.0, min(score, 0.999999))
    lower = int(bounded * 10) / 10
    upper = lower + 0.1
    if lower < 0.4:
        lower, upper = 0.4, 0.5
    return f"{lower:.2f}-{upper:.2f}"


def _bucket_midpoint(bucket: str) -> float:
    left, right = bucket.split("-")
    return round((float(left) + float(right)) / 2.0, 6)


def _shrink(successes: int, total: int, prior_successes: float = PRIOR_TARGETS, prior_total: float = PRIOR_TOTAL) -> float:
    return round((float(successes) + prior_successes) / (float(total) + prior_total), 6)
