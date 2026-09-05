from __future__ import annotations

from typing import Any


BEHAVIOR_CORE_PURPOSE = (
    "Find the hidden repeated behavior DNA of each stock using candle structure, "
    "session rhythm, indicator context, level memory, and historical outcome similarity."
)
NO_BLIND_PREDICTION_RULE = "Trade Vision must find repeated stock-specific behavior DNA, not blindly predict."
UNIVERSAL_AGREEMENT_RULE = (
    "A trade is allowed only when: signal strength + candle structure + level context + "
    "session rhythm + similar-history outcome + market regime + risk quality ALL agree. "
    "If they disagree, Trade Vision must say WAIT or NO TRADE."
)
LOW_EVIDENCE_MESSAGE = "Low evidence. Similar history is not enough."
INDICATOR_VALUE_SIMILARITY_EXAMPLE = (
    "This current setup matches old cases where RSI was 58-64, price above VWAP, "
    "MACD turning positive, ATR expanding, and volume 1.8x normal."
)
HTF_CONTEXT_EXAMPLE = (
    "1-minute candles look bullish, but the stock is rejecting from daily resistance, "
    "so breakout probability is weaker."
)
REPEATED_PATTERN_VALUES_EXAMPLE = (
    "Every time this stock opens above previous day high, RSI crosses 60, price stays above "
    "VWAP for 20 minutes, and volume is above 2x, it usually continues until 10:45."
)
DAY_OF_WEEK_SESSION_MEMORY_EXAMPLE = (
    "This stock often opens strong on Monday if Asian markets are positive, but fades after "
    "10:30 if previous US session closed weak."
)
NARRATIVE_EXPLANATION_ONLY_INVARIANT = "Narrative is EXPLANATION ONLY, not PRIMARY DECISION MAKER."


BEHAVIOR_LAYER_CONTRACTS = [
    "DataQualityResult",
    "LookaheadGuardResult",
    "SlippageBrokerageResult",
    "LiquidityFilterResult",
    "NewsEventFilterResult",
    "MarketRegimeResult",
    "CandleAnatomyResult",
    "PatternMemoryResult",
    "VwapOrbCprContextResult",
    "IndicatorSimilarityResult",
    "HTFConfirmationResult",
    "RelativeStrengthResult",
    "GapContextResult",
    "OrderFlowProxyResult",
    "MarketContextResult",
    "SupportResistanceMemoryResult",
    "SessionPersonalityResult",
    "TradeDecisionResult",
    "DynamicTargetResult",
    "RiskTargetResult",
    "ExplanationResult",
    "LearningTrustResult",
    "FailurePatternResult",
    "TradeLifecycleResult",
    "CalibrationResult",
    "WalkForwardResult",
    "OutOfSampleResult",
    "DriftResult",
    "NoTradeResult",
    "ReasonTreeResult",
    "RiskOfRuinResult",
    "SimilarDayReplayResult",
]


EXPECTED_74_COLUMNS = [
    "market_state",
    "session_phase",
    "candle_behavior",
    "pattern_family",
    "similarity_pattern",
    "similarity_score_pct",
    "historical_match_count",
    "similar_day_ids",
    "continuation_probability_pct",
    "reversal_probability_pct",
    "fakeout_probability_pct",
    "range_probability_pct",
    "learning_probability_pct",
    "trusting_percent",
    "expected_move_atr",
    "expected_time_window",
    "expected_MFE",
    "expected_MAE",
    "best_entry_zone",
    "invalidation_level",
    "target",
    "stop_loss",
    "risk_reward",
    "data_quality_score",
    "liquidity_score",
    "slippage_risk",
    "market_regime",
    "sector_strength",
    "relative_strength_score",
    "gap_type",
    "gap_fill_probability",
    "trap_probability",
    "absorption_score",
    "continuation_quality",
    "retest_quality",
    "level_respect_score",
    "model_drift_score",
    "uncertainty_score",
    "capital_risk_score",
    "past_failure_reason",
    "no_trade_reason",
    "rule_confidence_pct",
    "memory_confidence_pct",
    "final_trade_decision",
    "reason",
    "source_timeframe",
    "candle_close_time",
    "decision_time",
    "execution_time",
    "outcome_label",
    "bars_to_target",
    "bars_to_sl",
    "minimum_sample_pass",
    "evidence_quality",
    "position_size",
    "risk_per_trade_pct",
    "capital_to_use",
    "sector_exposure",
    "index_exposure",
    "correlation_risk",
    "portfolio_heat",
    "daily_pnl",
    "daily_loss_limit_hit",
    "cooldown_active",
    "trade_allowed",
    "trade_state",
    "entry_type",
    "fill_price",
    "fill_quality",
    "missed_trade_reason",
    "model_version",
    "rule_version",
    "backtest_id",
    "decision_audit_log",
]


BEHAVIOR_LAYER_NAMES = [
    "Data Quality Engine",
    "Lookahead-Bias Guard",
    "Slippage + Brokerage Model",
    "Liquidity Filter",
    "News/Event Filter",
    "Market Regime Detector",
    "Candle Structure Intelligence",
    "Intraday Pattern Memory",
    "VPD + ORB + CPR/Pivot + VWAP Context",
    "Indicator Similarity Engine",
    "Higher-Timeframe Confirmation",
    "Relative Strength Engine",
    "Gap Context Engine",
    "Order-Flow Proxy",
    "Index/Market Context",
    "Support/Resistance Memory",
    "Session Personality & Rhythm",
    "Trade Decision Engine",
    "Dynamic SL/Target Optimizer",
    "Risk/SL/Target Optimizer",
    "Explanation Engine",
    "Learning & Trust Table",
    "Failure Pattern Library",
    "Trade Lifecycle Tracking",
    "Confidence Calibration",
    "Walk-Forward Testing",
    "Out-of-Sample Validation",
    "Model Drift Detector",
    "No-Trade Intelligence",
    "Human-Readable Reason Tree",
    "Risk-of-Ruin / Capital Safety",
    "Similar-Day Replay Engine",
]


VERBATIM_REGISTRY = [
    {
        "constant_name": "BEHAVIOR_CORE_PURPOSE",
        "source_text": BEHAVIOR_CORE_PURPOSE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_behavior_core_purpose_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "NO_BLIND_PREDICTION_RULE",
        "source_text": NO_BLIND_PREDICTION_RULE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_no_blind_prediction_rule_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "UNIVERSAL_AGREEMENT_RULE",
        "source_text": UNIVERSAL_AGREEMENT_RULE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_universal_agreement_rule_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "LOW_EVIDENCE_MESSAGE",
        "source_text": LOW_EVIDENCE_MESSAGE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_low_evidence_message_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "INDICATOR_VALUE_SIMILARITY_EXAMPLE",
        "source_text": INDICATOR_VALUE_SIMILARITY_EXAMPLE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_indicator_value_similarity_example_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "HTF_CONTEXT_EXAMPLE",
        "source_text": HTF_CONTEXT_EXAMPLE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_htf_context_example_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "REPEATED_PATTERN_VALUES_EXAMPLE",
        "source_text": REPEATED_PATTERN_VALUES_EXAMPLE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_repeated_pattern_values_example_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "DAY_OF_WEEK_SESSION_MEMORY_EXAMPLE",
        "source_text": DAY_OF_WEEK_SESSION_MEMORY_EXAMPLE,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_day_of_week_session_memory_example_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "NARRATIVE_EXPLANATION_ONLY_INVARIANT",
        "source_text": NARRATIVE_EXPLANATION_ONLY_INVARIANT,
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_narrative_explanation_only_exact",
        "must_match_exactly": True,
    },
    {
        "constant_name": "EXPECTED_74_COLUMNS",
        "source_text": "EXPECTED_74_COLUMNS",
        "file_path": "apps/api/app/behavior/constants.py",
        "test_name": "test_expected_74_columns_exact_set",
        "must_match_exactly": True,
    },
]


def mock_behavior_result(*, symbol: str, timeframe: str, decision_time: str) -> dict[str, Any]:
    """Return a deterministic contract-lock result with the exact 74-column shape."""

    result: dict[str, Any] = {
        "market_state": "opening_drive_retest_watch",
        "session_phase": "09:30-10:15 real_trend_confirmation",
        "candle_behavior": "upper_wick_rejection_with_absorption_risk",
        "pattern_family": "open_drive_vwap_retest",
        "similarity_pattern": "prior_vwap_retest_fakeout_cluster",
        "similarity_score_pct": 78.0,
        "historical_match_count": 24,
        "similar_day_ids": ["mock-day-2024-03-11", "mock-day-2024-04-08", "mock-day-2024-05-22"],
        "continuation_probability_pct": 32.0,
        "reversal_probability_pct": 41.0,
        "fakeout_probability_pct": 57.0,
        "range_probability_pct": 27.0,
        "learning_probability_pct": 48.0,
        "trusting_percent": 54.0,
        "expected_move_atr": -0.34,
        "expected_time_window": "next 6-12 candles",
        "expected_MFE": 0.62,
        "expected_MAE": 0.78,
        "best_entry_zone": "wait for VWAP reclaim retest",
        "invalidation_level": "below VWAP and morning midpoint",
        "target": "3R only after retest confirmation",
        "stop_loss": "2 ATR beyond breakout/retest level",
        "risk_reward": 0.0,
        "data_quality_score": 0.98,
        "liquidity_score": 0.73,
        "slippage_risk": "medium",
        "market_regime": "mock_transition_70_bull_20_chop_10_panic",
        "sector_strength": "neutral",
        "relative_strength_score": 0.51,
        "gap_type": "small_gap_up_unconfirmed",
        "gap_fill_probability": 44.0,
        "trap_probability": 57.0,
        "absorption_score": 0.64,
        "continuation_quality": 0.42,
        "retest_quality": 0.55,
        "level_respect_score": 0.69,
        "model_drift_score": 0.12,
        "uncertainty_score": 0.71,
        "capital_risk_score": 0.18,
        "past_failure_reason": "upper wick near resistance with low follow-through",
        "no_trade_reason": LOW_EVIDENCE_MESSAGE,
        "rule_confidence_pct": 68.0,
        "memory_confidence_pct": 54.0,
        "final_trade_decision": "WATCH_ONLY",
        "reason": (
            "Rule signal is constructive, but similar history is below the strong evidence threshold "
            "and fakeout risk is elevated. Wait for VWAP reclaim or confirmed retest."
        ),
        "source_timeframe": timeframe,
        "candle_close_time": decision_time,
        "decision_time": decision_time,
        "execution_time": "not_scheduled_mock_only",
        "outcome_label": "UNLABELED_MOCK",
        "bars_to_target": None,
        "bars_to_sl": None,
        "minimum_sample_pass": False,
        "evidence_quality": "LOW",
        "position_size": 0,
        "risk_per_trade_pct": 0.0,
        "capital_to_use": 0.0,
        "sector_exposure": 0.0,
        "index_exposure": 0.0,
        "correlation_risk": "none_mock",
        "portfolio_heat": 0.0,
        "daily_pnl": 0.0,
        "daily_loss_limit_hit": False,
        "cooldown_active": False,
        "trade_allowed": False,
        "trade_state": "WAITING",
        "entry_type": "next_open_reserved",
        "fill_price": None,
        "fill_quality": "not_applicable_watch_only",
        "missed_trade_reason": "mock contract lock prevents execution",
        "model_version": "behavior-contract-lock.v0.11",
        "rule_version": "legacy-rule-stack.v1",
        "backtest_id": "mock-contract-lock",
        "decision_audit_log": "mock behavior contract lock result; no live route attempted",
    }
    missing = set(EXPECTED_74_COLUMNS) - set(result)
    extra = set(result) - set(EXPECTED_74_COLUMNS)
    if missing or extra:
        raise RuntimeError(f"Behavior result column mismatch missing={missing} extra={extra}")
    return result


assert len(BEHAVIOR_LAYER_CONTRACTS) == 32
assert len(BEHAVIOR_LAYER_NAMES) == 32
assert len(EXPECTED_74_COLUMNS) == 74

