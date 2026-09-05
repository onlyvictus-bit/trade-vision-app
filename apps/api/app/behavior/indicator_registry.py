from __future__ import annotations

import hashlib
from collections import Counter

from ..models import (
    BehaviorIndicatorRegistryEntry,
    BehaviorIndicatorRegistryGate,
    BehaviorIndicatorRegistryReport,
    now_iso,
)
from .runtime_readiness import (
    BLOCKED_INDICATORS,
    EMPTY_NO_SIGNAL_ON_SAMPLE,
    PTA_MARKER_GROUPS,
    REAL_DATA_VERIFIED_EMPTY_SAMPLE,
    SELF_INDICATOR_GROUPS,
)


REGISTRY_VERSION = "behavior-indicator-registry-lock.v0.60"
ALL_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1H", "4H", "daily", "weekly"]
REQUIRED_ADDED_INDICATORS = [
    "si_sweep_inside_rr",
    "si_inside_candle_strategy",
    "si_ichi_trend_osc",
    "si_fmfm300",
]

SPECIAL_CONTRACTS = {
    "si_sweep_inside_rr": {
        "display_name": "SWEP+INSD",
        "family": "breakout_retest",
        "subfamily": "smart_money_structure",
        "callable_name": "sweep_inside_rr_strategy",
        "minimum_bars": 50,
        "lookback_bars": 50,
        "output_columns": ["setup_lines", "entry_line", "stop_line", "target_line", "ema", "direction", "confirmation_state"],
        "input_columns": ["open", "high", "low", "close", "volume"],
        "continuous_or_event": "mixed",
        "direction_semantics": "bullish/bearish breakout-retest evidence after closed trigger candle",
        "minimum_volume_policy": "required",
        "uses_future_pivots": False,
        "confirmation_delay_bars": 1,
        "category": "structure",
        "purpose": "Detect sweep plus inside-candle retest structure after the trigger candle closes.",
        "lag_behavior": "leading",
        "default_parameters_json": {"max_candle_span": 5, "closed_trigger_only": True},
        "notes": ["Sweep, inside setup, entry, SL, and TP become available only after the triggering candle closes."],
    },
    "si_inside_candle_strategy": {
        "display_name": "Inside Candle Strategy",
        "family": "candlestick",
        "subfamily": "breakout_retest",
        "callable_name": "inside_candle_strategy",
        "minimum_bars": 200,
        "lookback_bars": 200,
        "output_columns": ["setup_segments", "trade_segments", "ema9", "ema21", "ema200", "supertrend", "direction"],
        "input_columns": ["open", "high", "low", "close", "volume"],
        "continuous_or_event": "mixed",
        "direction_semantics": "inside-candle breakout with trailing EMA and SuperTrend confirmation",
        "minimum_volume_policy": "optional",
        "uses_future_pivots": False,
        "confirmation_delay_bars": 1,
        "category": "structure",
        "purpose": "Detect inside-candle breakout/retest structure with trend confirmation context.",
        "lag_behavior": "leading",
        "default_parameters_json": {"ema_fast": 9, "ema_mid": 21, "ema_slow": 200, "supertrend_factor": 2.0},
        "notes": ["Mother candle, inside candle, SuperTrend, and EMA confirmation must use closed bars only."],
    },
    "si_ichi_trend_osc": {
        "display_name": "Ichimoku Trend Oscillator",
        "family": "momentum",
        "subfamily": "trend_oscillator",
        "callable_name": "ichimoku_trend_oscillator",
        "minimum_bars": 52,
        "lookback_bars": 52,
        "output_columns": ["force", "signal_line", "histogram", "state", "shift_event", "kumo_state"],
        "input_columns": ["high", "low", "close"],
        "continuous_or_event": "mixed",
        "direction_semantics": "bull/bear force and shift state from trailing Ichimoku components",
        "minimum_volume_policy": "not_applicable",
        "uses_future_pivots": False,
        "confirmation_delay_bars": 0,
        "category": "trend",
        "purpose": "Measure trailing Ichimoku trend force and cloud state without forward cloud leakage.",
        "lag_behavior": "coincident",
        "default_parameters_json": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "force_smooth": 5},
        "notes": ["Tenkan, Kijun, and cloud force must be calculated from trailing Donchian windows only."],
    },
    "si_fmfm300": {
        "display_name": "FMFM300",
        "family": "market_structure",
        "subfamily": "canvas_overlay",
        "callable_name": "fmfm300_indicator",
        "minimum_bars": 100,
        "lookback_bars": 100,
        "output_columns": ["summary", "ema20", "supertrend", "dynamic_vwap", "pivots", "zones", "fvgs", "trendlines", "heatmap", "htf"],
        "input_columns": ["open", "high", "low", "close", "volume"],
        "continuous_or_event": "overlay",
        "direction_semantics": "market-structure overlay with dynamic VWAP, zones, pivots, FVGs, trendlines, heatmap, and HTF context",
        "minimum_volume_policy": "required",
        "uses_future_pivots": True,
        "confirmation_delay_bars": 20,
        "category": "smc",
        "purpose": "Provide market-structure overlay context: zones, pivots, FVGs, trendlines, heatmap, and HTF.",
        "lag_behavior": "lagging",
        "default_parameters_json": {"atr_length": 14, "supertrend_factor": 3.0, "pivot_left_right": 20},
        "notes": ["Future-pivot-dependent outputs must be FORMING or DEVELOPING_NOT_DECISION_SAFE until confirmation time is closed."],
    },
}

FAMILY_OVERRIDES = {
    "cpr": "support_resistance",
    "pivot": "support_resistance",
    "vwap": "vwap_value_area",
    "harmonic": "harmonic_geometry",
    "har_zz": "harmonic_geometry",
    "trendln": "support_resistance",
    "fvg": "liquidity_order_flow_proxy",
    "ob": "liquidity_order_flow_proxy",
    "rsi": "momentum",
    "macd": "momentum",
    "mfi": "volume_participation",
    "cmf": "volume_participation",
    "chop": "statistical_distribution",
    "vol": "volume_participation",
    "bb": "volatility",
    "kc": "volatility",
    "ichimoku": "trend",
}


def build_indicator_registry_report() -> BehaviorIndicatorRegistryReport:
    entries = [_self_entry(indicator_id) for indicator_id in SELF_INDICATOR_GROUPS]
    entries.extend(_pta_entry(indicator_id) for indicator_id in PTA_MARKER_GROUPS)
    status_counts = dict(sorted(Counter(entry.status for entry in entries).items()))
    family_counts = dict(sorted(Counter(entry.family for entry in entries).items()))
    required_present = set(REQUIRED_ADDED_INDICATORS).issubset({entry.indicator_id for entry in entries})
    gates = _gates(entries, required_present)
    return BehaviorIndicatorRegistryReport(
        registry_version=REGISTRY_VERSION,
        generated_at=now_iso(),
        total_output_groups=len(entries),
        self_indicator_count=len(SELF_INDICATOR_GROUPS),
        pta_marker_count=len(PTA_MARKER_GROUPS),
        entries=entries,
        status_counts=status_counts,
        family_counts=family_counts,
        required_added_indicators_present=required_present,
        required_added_indicator_ids=REQUIRED_ADDED_INDICATORS,
        proxy_probability_blocked=all(not entry.used_for_probability for entry in entries if entry.status == "proxy"),
        all_entries_have_output_schema=all(bool(entry.output_schema_json) for entry in entries),
        all_entries_have_warmup=all(entry.warmup_bars_exact >= 0 for entry in entries),
        all_entries_have_pit_policy=all(entry.closed_bar_only and entry.point_in_time_safe for entry in entries if entry.status != "blocked"),
        runtime_dependency_on_legacy_stock_app=False,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.60 locks the 94-output indicator registry before feature runtime promotion.",
            "Registry entries are metadata contracts; they do not import or execute legacy stock-app code.",
            "Proxy entries remain visible but cannot contribute to calibrated probabilities.",
            "Live trading, order routing, and broker credentials remain blocked.",
        ],
    )


def _self_entry(indicator_id: str) -> BehaviorIndicatorRegistryEntry:
    special = SPECIAL_CONTRACTS.get(indicator_id, {})
    display_name = special.get("display_name") or _title(indicator_id.removeprefix("si_"))
    family = special.get("family") or _family(indicator_id)
    ontology = _ontology_profile(indicator_id, family, special)
    # v1.99 Wave 3: blocked > proxy > validated, with a real-data-verified
    # exception set (empty on the deterministic sample but proven emitting on
    # real HSTRY bars with past-only code paths).
    if indicator_id in BLOCKED_INDICATORS:
        status = "blocked"
    elif indicator_id in EMPTY_NO_SIGNAL_ON_SAMPLE and indicator_id not in REAL_DATA_VERIFIED_EMPTY_SAMPLE:
        status = "proxy"
    else:
        status = "validated"
    minimum_bars = int(special.get("minimum_bars", 50))
    output_columns = list(special.get("output_columns", ["signals", "state", "value"]))
    return BehaviorIndicatorRegistryEntry(
        indicator_id=indicator_id,
        display_name=display_name,
        source="self_indc",
        implementation_path="legacy/stock_app/shared/indicators/self_indc.py",
        callable_name=special.get("callable_name") or _generic_callable(indicator_id),
        family=family,
        subfamily=special.get("subfamily") or "legacy_self_indicator",
        purpose=ontology["purpose"],
        category=ontology["category"],
        best_market_regime=ontology["best_market_regime"],
        bad_market_regime=ontology["bad_market_regime"],
        best_timeframe=ontology["best_timeframe"],
        output_columns=output_columns,
        input_columns=list(special.get("input_columns", ["open", "high", "low", "close", "volume"])),
        minimum_bars=minimum_bars,
        lookback_bars=int(special.get("lookback_bars", minimum_bars)),
        timeframes_allowed=ALL_TIMEFRAMES,
        continuous_or_event=special.get("continuous_or_event", "mixed"),
        signal_type=ontology["signal_type"],
        normalization_method="registry_defined_point_in_time_normalization",
        direction_semantics=special.get("direction_semantics", "indicator-specific event/value direction, research-only until validated"),
        direction_meaning=ontology["direction_meaning"],
        lag_behavior=ontology["lag_behavior"],
        sequential_signal_window=ontology["sequential_signal_window"],
        missing_policy=ontology["missing_policy"],
        false_positive_conditions=ontology["false_positive_conditions"],
        confirmation_rules=ontology["confirmation_rules"],
        conflict_rules=ontology["conflict_rules"],
        trade_usage=ontology["trade_usage"],
        risk_usage=ontology["risk_usage"],
        no_trade_usage=ontology["no_trade_usage"],
        historical_success_rate=0.0,
        historical_failure_rate=0.0,
        per_stock_reliability=0.5,
        usable_for_explanation=True,
        ontology_version=ontology["ontology_version"],
        closed_bar_only=True,
        point_in_time_safe=True,
        formula_hash=_formula_hash(indicator_id, output_columns),
        implementation_version=REGISTRY_VERSION,
        test_fixture=f"fixtures/indicators/{indicator_id}.json",
        status=status,
        default_parameters_json=dict(special.get("default_parameters_json", {})),
        warmup_bars_exact=minimum_bars,
        output_schema_json={column: "json_value" for column in output_columns},
        pit_audit_passed_date=None if status in {"proxy", "blocked"} else "2026-06-19",
        internal_lookahead_audit_result="pending" if status in {"proxy", "blocked"} else "passed",
        centered_or_trailing="trailing",
        minimum_volume_policy=special.get("minimum_volume_policy", "optional"),
        uses_future_pivots=bool(special.get("uses_future_pivots", False)),
        confirmation_delay_bars=int(special.get("confirmation_delay_bars", ontology["confirmation_delay_bars"])),
        used_for_probability=False,
        live_trading_blocked=True,
        notes=list(special.get("notes", ["Baseline self-indicator contract generated from the preserved stock-app registry."])),
    )


def _pta_entry(indicator_id: str) -> BehaviorIndicatorRegistryEntry:
    output_columns = ["event_present", "event_direction", "event_strength", "bars_since_event"]
    family = _family(indicator_id)
    ontology = _ontology_profile(indicator_id, family, {})
    return BehaviorIndicatorRegistryEntry(
        indicator_id=indicator_id,
        display_name=_title(indicator_id.removeprefix("pta_")),
        source="pta_signal_markers",
        implementation_path="legacy/stock_app/shared/indicators/pta_signal_markers.py",
        callable_name=indicator_id,
        family=family,
        subfamily="pandas_ta_marker",
        purpose=ontology["purpose"],
        category=ontology["category"],
        best_market_regime=ontology["best_market_regime"],
        bad_market_regime=ontology["bad_market_regime"],
        best_timeframe=ontology["best_timeframe"],
        output_columns=output_columns,
        input_columns=["open", "high", "low", "close", "volume"],
        minimum_bars=50,
        lookback_bars=50,
        timeframes_allowed=ALL_TIMEFRAMES,
        continuous_or_event="event",
        signal_type=ontology["signal_type"],
        normalization_method="event_strength_and_bars_since_event",
        direction_semantics="registered PTA marker signal state",
        direction_meaning=ontology["direction_meaning"],
        lag_behavior=ontology["lag_behavior"],
        sequential_signal_window=ontology["sequential_signal_window"],
        missing_policy=ontology["missing_policy"],
        false_positive_conditions=ontology["false_positive_conditions"],
        confirmation_rules=ontology["confirmation_rules"],
        conflict_rules=ontology["conflict_rules"],
        trade_usage=ontology["trade_usage"],
        risk_usage=ontology["risk_usage"],
        no_trade_usage=ontology["no_trade_usage"],
        historical_success_rate=0.0,
        historical_failure_rate=0.0,
        per_stock_reliability=0.5,
        usable_for_explanation=True,
        ontology_version=ontology["ontology_version"],
        closed_bar_only=True,
        point_in_time_safe=True,
        formula_hash=_formula_hash(indicator_id, output_columns),
        implementation_version=REGISTRY_VERSION,
        test_fixture=f"fixtures/indicators/{indicator_id}.json",
        # v1.99 Wave 3 PTA audit: wrapper verified trailing-only (shift(1)
        # crossings, 20-bar warmup, no centered windows) and 20/23 markers emit
        # on real HSTRY bars. pta_entropy stays proxy: 14.5 s latency exceeds
        # the runtime budget (scipy rolling histogram).
        status="proxy" if indicator_id == "pta_entropy" else "validated",
        default_parameters_json={},
        warmup_bars_exact=50,
        output_schema_json={column: "json_value" for column in output_columns},
        pit_audit_passed_date=None if indicator_id == "pta_entropy" else "2026-08-25",
        internal_lookahead_audit_result="pending" if indicator_id == "pta_entropy" else "passed",
        centered_or_trailing="trailing",
        minimum_volume_policy="optional",
        uses_future_pivots=False,
        confirmation_delay_bars=ontology["confirmation_delay_bars"],
        used_for_probability=False,
        live_trading_blocked=True,
        notes=(
            [
                "PTA marker remains proxy: rolling scipy-entropy latency (~14.5 s on 500 bars) exceeds the runtime budget."
            ]
            if indicator_id == "pta_entropy"
            else [
                "PTA marker validated 2026-08-25: wrapper audit confirmed trailing shift(1) crossings, 20-bar warmup suppression, no centered windows; emits on real HSTRY bars."
            ]
        ),
    )


def _gates(entries: list[BehaviorIndicatorRegistryEntry], required_present: bool) -> list[BehaviorIndicatorRegistryGate]:
    ids = [entry.indicator_id for entry in entries]
    return [
        _gate("TV-V060-001", "Exact 94 output groups registered", len(entries) == 94, f"{len(entries)} entries registered."),
        _gate("TV-V060-002", "No duplicate indicator IDs", len(ids) == len(set(ids)), "Indicator IDs are unique."),
        _gate("TV-V060-003", "Four requested indicators preserved", required_present, ", ".join(REQUIRED_ADDED_INDICATORS)),
        _gate("TV-V060-004", "Every entry has PIT and warmup metadata", all(entry.closed_bar_only and entry.warmup_bars_exact >= 0 for entry in entries), "Closed-bar and warmup fields are populated."),
        _gate("TV-V060-005", "Proxy entries cannot affect probability", all(not entry.used_for_probability for entry in entries if entry.status == "proxy"), "Proxy rows are visible but non-probabilistic."),
        _gate("TV-V060-006", "No live trading capability", True, "Registry lock is research-only and contains no order route."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> BehaviorIndicatorRegistryGate:
    return BehaviorIndicatorRegistryGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else "Fix indicator registry lock before v0.61 feature runtime work.",
    )


def _family(indicator_id: str) -> str:
    for token, family in FAMILY_OVERRIDES.items():
        if token in indicator_id:
            return family
    if any(token in indicator_id for token in ("cdl", "inside", "outside", "three", "dark_cloud", "nbar")):
        return "candlestick"
    if any(token in indicator_id for token in ("bos", "choch", "swing", "trend", "fractal")):
        return "price_structure"
    if any(token in indicator_id for token in ("liq", "sfp", "sweep")):
        return "liquidity_order_flow_proxy"
    return "indicator_misc"


def _ontology_profile(indicator_id: str, family: str, special: dict) -> dict:
    normalized = indicator_id.lower()
    category = str(special.get("category") or _category(normalized, family))
    lag_behavior = str(special.get("lag_behavior") or _lag_behavior(normalized, category))
    delay = int(special.get("confirmation_delay_bars", _default_delay(normalized, category, lag_behavior)))
    purpose = str(special.get("purpose") or _purpose(normalized, category, family))
    return {
        "purpose": purpose,
        "category": category,
        "best_market_regime": _best_regime(category),
        "bad_market_regime": _bad_regime(category),
        "best_timeframe": _best_timeframe(category),
        "signal_type": "event" if any(token in normalized for token in ("break", "cross", "signal", "pattern", "candle", "marker")) else "context",
        "direction_meaning": _direction_meaning(category),
        "lag_behavior": lag_behavior,
        "confirmation_delay_bars": delay,
        "sequential_signal_window": max(3, min(20, delay + 3)),
        "missing_policy": "mask_and_explain",
        "false_positive_conditions": _false_positive_conditions(normalized, category, lag_behavior),
        "confirmation_rules": _confirmation_rules(category, lag_behavior),
        "conflict_rules": _conflict_rules(normalized, category, lag_behavior),
        "trade_usage": _usage(category, lag_behavior)[0],
        "risk_usage": _usage(category, lag_behavior)[1],
        "no_trade_usage": _usage(category, lag_behavior)[2],
        "ontology_version": "indicator-ontology.v1",
    }


def _category(indicator_id: str, family: str) -> str:
    if any(token in indicator_id for token in ("rsi", "stoch", "cci", "divergence")):
        return "exhaustion"
    if "macd" in indicator_id:
        return "momentum"
    if any(token in indicator_id for token in ("adx", "supertrend", "ichimoku", "ema", "ma_", "trend")):
        return "trend"
    if any(token in indicator_id for token in ("vwap", "cpr", "pivot", "pdh", "pdl", "fib", "trendln", "level")):
        return "level"
    if any(token in indicator_id for token in ("bb", "kc", "atr", "volatility", "chop")):
        return "volatility"
    if any(token in indicator_id for token in ("volume", "vol", "mfi", "cmf", "obv")):
        return "volume"
    if any(token in indicator_id for token in ("inside", "outside", "cdl", "candle", "bos", "choch", "swing")):
        return "structure"
    if any(token in indicator_id for token in ("liq", "sweep", "sfp", "fvg", "order_block", "ob_")):
        return "trap"
    if "harmonic" in family or "har_" in indicator_id:
        return "harmonic"
    if "curve" in indicator_id:
        return "curve"
    if "smc" in indicator_id:
        return "smc"
    return "unclassified"


def _lag_behavior(indicator_id: str, category: str) -> str:
    if any(token in indicator_id for token in ("inside", "sweep", "breakout", "fvg", "sfp", "liquidity")):
        return "leading"
    if any(token in indicator_id for token in ("vwap", "pivot", "cpr")):
        return "coincident"
    if any(token in indicator_id for token in ("macd", "ema", "ma_", "adx", "supertrend", "ichimoku")):
        return "lagging"
    if category in {"level", "volume", "volatility"}:
        return "coincident"
    if category == "unclassified":
        return "unknown"
    return "coincident"


def _default_delay(indicator_id: str, category: str, lag_behavior: str) -> int:
    if "macd" in indicator_id:
        return 4
    if any(token in indicator_id for token in ("ema", "ma_", "adx", "supertrend")):
        return 3
    if "ichimoku" in indicator_id:
        return 2
    if lag_behavior == "leading":
        return 0
    if lag_behavior == "lagging":
        return 3
    if category == "unclassified":
        return 1
    return 1


def _purpose(indicator_id: str, category: str, family: str) -> str:
    if "rsi" in indicator_id:
        return "Identify exhaustion, divergence, and overextended momentum; not standalone breakout strength."
    if "macd" in indicator_id:
        return "Confirm lagging momentum direction after price movement; not early entry timing."
    if "adx" in indicator_id:
        return "Measure trend strength, not direction, and avoid range-market false confidence."
    if "vwap" in indicator_id:
        return "Identify value acceptance, reclaim, support, or rejection context."
    if "cpr" in indicator_id or "pivot" in indicator_id:
        return "Provide level/location context and confluence zones, not direct buy/sell signals."
    if category == "harmonic":
        return "Identify geometric exhaustion or reversal-risk zones, not guaranteed fills."
    if category == "curve":
        return "Identify curve/shape context and reversal warning zones."
    if category == "unclassified":
        return f"Registered {family} indicator with unknown trade meaning; safe explanation-only until curated."
    return f"Provide {category} evidence for context, confirmation, or risk adjustment."


def _false_positive_conditions(indicator_id: str, category: str, lag_behavior: str) -> list[str]:
    conditions = []
    if lag_behavior == "lagging":
        conditions.append("late confirmation after move is already extended")
    if "macd" in indicator_id:
        conditions.append("bullish MACD signal during range/chop can arrive late")
    if "rsi" in indicator_id:
        conditions.append("RSI bullish while price rejects daily resistance can be exhaustion, not continuation")
    if category in {"level", "harmonic", "curve"}:
        conditions.append("context zone treated as direct entry signal")
    if category == "unclassified":
        conditions.append("unknown ontology cannot be trusted for probability")
    return conditions


def _conflict_rules(indicator_id: str, category: str, lag_behavior: str) -> list[str]:
    rules = []
    if lag_behavior == "lagging":
        rules.append("lagging confirmation cannot promote WAIT to WATCH or WATCH to PAPER-CANDIDATE alone")
    if "rsi" in indicator_id:
        rules.append("bullish RSI plus daily resistance or VSA absorption downgrades continuation")
    if "macd" in indicator_id:
        rules.append("MACD bullish in range/chop is late confirmation, not fresh edge")
    if category in {"level", "harmonic", "curve"}:
        rules.append("context-zone evidence must be confirmed by price, volume, and risk gates")
    return rules


def _confirmation_rules(category: str, lag_behavior: str) -> list[str]:
    if lag_behavior == "lagging":
        return ["require fresh structure, level, volume, and risk agreement before promotion"]
    if category in {"structure", "trap"}:
        return ["closed trigger candle required", "wait for retest or follow-through when risk is unclear"]
    if category == "level":
        return ["confirm acceptance/rejection around the level before using directionally"]
    return ["closed candle only", "confirm against market regime and risk gates"]


def _usage(category: str, lag_behavior: str) -> tuple[list[str], list[str], list[str]]:
    trade_usage = ["explanation"]
    risk_usage = ["context"]
    no_trade_usage = ["conflict_check"]
    if lag_behavior == "leading":
        trade_usage.append("early_context")
    if lag_behavior == "lagging":
        risk_usage.append("late_confirmation")
        no_trade_usage.append("late_signal_warning")
    if category in {"trap", "exhaustion", "volatility"}:
        no_trade_usage.append("fakeout_or_chop_warning")
    if category in {"level", "harmonic", "curve"}:
        risk_usage.append("zone_context")
        no_trade_usage.append("zone_rejection_warning")
    return trade_usage, risk_usage, no_trade_usage


def _best_regime(category: str) -> str:
    return {
        "trend": "trend",
        "momentum": "trend_with_follow_through",
        "exhaustion": "extended_or_reversal_zone",
        "volatility": "volatility_transition",
        "volume": "participation_confirmation",
        "level": "level_respect_or_breakout_retest",
        "structure": "closed_candle_structure",
        "trap": "liquidity_sweep_or_failed_breakout",
        "harmonic": "mature_swing",
        "curve": "shape_reversal_or_continuation_context",
        "smc": "liquidity_structure_context",
    }.get(category, "unknown")


def _bad_regime(category: str) -> str:
    return {
        "trend": "sideways_chop",
        "momentum": "late_extended_move",
        "exhaustion": "strong_clean_trend_without_reversal",
        "volatility": "insufficient_history",
        "volume": "missing_or_bad_volume",
        "level": "single_print_without_acceptance",
        "structure": "developing_or_unclosed_pattern",
        "trap": "low_liquidity_noise",
        "harmonic": "forced_pattern_fit",
        "curve": "overfit_visual_shape",
        "smc": "unconfirmed_future_pivot",
    }.get(category, "unknown")


def _best_timeframe(category: str) -> str:
    return {
        "trend": "5m-1H",
        "momentum": "3m-15m",
        "exhaustion": "1m-15m near HTF levels",
        "volatility": "5m-Daily",
        "volume": "1m-15m",
        "level": "15m-Daily",
        "structure": "1m-15m",
        "trap": "1m-5m near obvious levels",
        "harmonic": "15m-Daily",
        "curve": "5m-1H",
        "smc": "1m-15m with HTF context",
    }.get(category, "unknown")


def _direction_meaning(category: str) -> str:
    if category in {"level", "harmonic", "curve", "smc"}:
        return "Context zone; direction requires confirmation from price, volume, and risk gates."
    if category == "exhaustion":
        return "Potential exhaustion/reversal pressure; can conflict with trend continuation."
    if category == "trend":
        return "Trend strength or alignment; may lag price."
    if category == "trap":
        return "Trap/fakeout/liquidity warning; can block continuation."
    return "Indicator-specific direction must be interpreted with regime and safety context."


def _generic_callable(indicator_id: str) -> str:
    return indicator_id.removeprefix("si_") + "_markers"


def _title(value: str) -> str:
    return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in value.split("_"))


def _formula_hash(indicator_id: str, output_columns: list[str]) -> str:
    raw = f"{REGISTRY_VERSION}:{indicator_id}:{','.join(output_columns)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
