from __future__ import annotations

from ..models import (
    CausalFeatureDefinition,
    CausalFeatureValidationRequest,
    CausalFeatureValidationResult,
    CausalFeatureWhitelist,
)


WHITELIST_VERSION = "causal-feature-whitelist.v0.14"
ALLOWED_FEATURE_NAMES = [
    "rsi",
    "adx",
    "ema9",
    "ema21",
    "ema50",
    "ema200",
    "macd",
    "atr",
    "vwap",
    "volume_z",
    "previous_day_high",
    "previous_day_low",
    "previous_week_high",
    "previous_week_low",
    "cpr",
    "pivot",
    "orb_high",
    "orb_low",
    "supertrend",
    "candle_body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "close_location_value",
]
FORBIDDEN_FIELDS = [
    "future_high",
    "future_low",
    "future_close",
    "future_volume",
    "full_day_high",
    "full_day_low",
    "full_day_close",
    "full_day_volume",
    "current_day_high",
    "current_day_low",
    "current_day_close",
    "current_day_volume",
    "session_final_high",
    "session_final_low",
    "session_final_close",
    "target_hit_after_entry",
    "sl_hit_after_entry",
]
INVARIANT = (
    "Only features available before trade entry are allowed. No future high, future low, "
    "future close, future volume, full-day value, or incomplete higher-timeframe value can enter decision logic."
)


def causal_whitelist() -> CausalFeatureWhitelist:
    return CausalFeatureWhitelist(
        whitelist_version=WHITELIST_VERSION,
        allowed_feature_names=ALLOWED_FEATURE_NAMES,
        forbidden_fields=FORBIDDEN_FIELDS,
        invariant=INVARIANT,
    )


def validate_causal_features(request: CausalFeatureValidationRequest) -> CausalFeatureValidationResult:
    allowed: list[str] = []
    blocked: list[str] = []
    issues: list[str] = []
    alignment_by_timeframe = {}
    if request.timeframe_sync is not None:
        alignment_by_timeframe = {record.timeframe: record for record in request.timeframe_sync.records}

    for feature in request.features:
        feature_issues = _feature_issues(feature, request.decision_time_ns, alignment_by_timeframe)
        if feature_issues:
            blocked.append(feature.name)
            issues.extend([f"{feature.name}: {issue}" for issue in feature_issues])
        else:
            allowed.append(feature.name)

    passed = len(blocked) == 0
    return CausalFeatureValidationResult(
        whitelist_version=WHITELIST_VERSION,
        decision_time_ns=request.decision_time_ns,
        feature_count=len(request.features),
        allowed_features=allowed,
        blocked_features=blocked,
        issues=issues,
        passed=passed,
        blocks_trade=not passed,
    )


def default_safe_features(decision_time_ns: int) -> list[CausalFeatureDefinition]:
    return [
        CausalFeatureDefinition(
            name="rsi",
            source_timeframe="5m",
            required_fields=["open", "high", "low", "close"],
            available_after_ns=decision_time_ns,
            depends_on_full_candle=True,
            description="RSI from closed 5m candles only.",
        ),
        CausalFeatureDefinition(
            name="vwap",
            source_timeframe="1m",
            required_fields=["open", "high", "low", "close", "volume"],
            available_after_ns=decision_time_ns,
            depends_on_full_candle=True,
            description="VWAP from closed intraday candles only.",
        ),
        CausalFeatureDefinition(
            name="previous_day_high",
            source_timeframe="daily",
            required_fields=["previous_day_high"],
            available_after_ns=decision_time_ns,
            depends_on_full_candle=True,
            description="Previous completed daily high, never current full-day high.",
        ),
    ]


def _feature_issues(
    feature: CausalFeatureDefinition,
    decision_time_ns: int,
    alignment_by_timeframe: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    if feature.uses_future_data:
        issues.append("uses_future_data=true is forbidden.")

    lowered_fields = {field.lower() for field in feature.required_fields}
    forbidden = lowered_fields.intersection(FORBIDDEN_FIELDS)
    if forbidden:
        issues.append(f"forbidden fields present: {', '.join(sorted(forbidden))}.")

    if feature.available_after_ns is not None and feature.available_after_ns > decision_time_ns:
        issues.append("feature is not available at decision_time_ns.")

    record = alignment_by_timeframe.get(feature.source_timeframe)
    if record is not None:
        usable_bars = getattr(record, "usable_bars", 0)
        if feature.depends_on_full_candle and usable_bars <= 0:
            issues.append(f"source timeframe {feature.source_timeframe} has no closed candle available.")

    return issues
