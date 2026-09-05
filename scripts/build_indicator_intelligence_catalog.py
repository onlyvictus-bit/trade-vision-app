"""Build the Indicator Intelligence Catalog artifacts (v1.96).

Deterministic, re-runnable generator. Sources:
  1. Live Trade Vision registry via build_indicator_registry_report() (94 entries).
  2. Audited code evidence embedded below (vendor copy is authoritative by decision
     of 2026-08-25 scope approval; drift vs shared/indicators originals is recorded,
     not fixed here).

Outputs (all paths relative to project root):
  data/indicator-intelligence/indicator_contracts.v1.json
  data/indicator-intelligence/indicator_coverage_report.json
  docs/INDICATOR_GROUP_AND_USE_MAP.md        (generated section)
  docs/generated/INDICATOR_CATALOG_TABLE.md  (human-readable grouped table)

Run:  .venv/Scripts/python.exe scripts/build_indicator_intelligence_catalog.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.behavior.indicator_registry import build_indicator_registry_report  # noqa: E402
from app.behavior.real_indicator_adapter import REAL_RUNTIME_PROMOTED_INDICATORS  # noqa: E402

# Single source of truth: the live adapter set. Never hardcode promotion membership.
PROMOTED_13 = sorted(REAL_RUNTIME_PROMOTED_INDICATORS)

VENDOR_SELF = "apps/api/app/vendor/stock_app/shared/indicators/self_indc.py"
VENDOR_PTA_WRAPPER = "apps/api/app/vendor/stock_app/shared/indicators/pta_signal_markers.py"
VENDOR_PTA_SIGNALS = "apps/api/app/vendor/stock_app/research/signals/pta_signals.py"
VENDOR_PTA_LIB = "apps/api/app/vendor/stock_app/shared/indicators/pta.py"

FUTURE_LEAK_IDS = {
    "si_delta_vp": "trades[].outcome computed over following hold_bars (self_indc.py:2110)",
    "si_hybrid_ml_cpr": "success_after_10 weight updates from close 10 bars later (self_indc.py:5225)",
    "si_sweep_inside_rr": "forward TP/SL fills in dashboard/trades (self_indc.py:6859)",
    "si_opening_range_rev": "forward TP/SL fill simulation (self_indc.py:4611)",
    "si_hyb_opening_range_rev": "forward TP/SL fill simulation (self_indc.py:4778)",
    "si_problty_grid": "hit probabilities calibrate from completed sessions only (sequentially causal per code); kept explanation-only as conservative in-sample-calibration guard (self_indc.py:2460-2528)",
}

CENTERED_PIVOT_IDS = {
    "si_swing_str", "si_sfp", "si_sfb_hybrid", "si_liq_intelg", "si_adaptive_flow",
    "si_liquidity_entry", "si_fmfm300", "si_ctz_gann", "si_swing_break", "si_hs",
}
ZIGZAG_REPAINT_IDS = {"si_zz_swing", "si_harmonic", "si_har_zz"}
LIB_SHIFT_RISK_IDS = {"si_bos", "si_choch"}
DISCLOSED_DELAY_IDS = {"si_rsi_div_auto": "signal emitted at pivot+right confirm bar", "si_fractal": "marker emitted at pivot+2", "si_hs": "fallback pattern markers backfilled onto 5th pivot bar, confirmable only 3 bars later (h[i-3:i+4])"}

REDUNDANCY_FAMILIES = {
    "harmonic_zigzag": ["si_harmonic", "si_har_zz", "si_zz_swing"],
    "inside_outside_bar": ["si_inside_out", "si_mk_inside"],
    "pivot_levels": ["si_cpr", "si_cpr_v4", "si_wekly_pivot", "si_hourly_pvt", "si_strg_pivt", "si_cm_strg_pivt"],
    "vwap_confluence": ["si_vwap_conf", "si_vwap_super", "si_vwap_bb_ml_conf", "si_hybrid_ml", "si_hybrid_ml_cpr"],
    "atr_trailing_flip": ["si_st_talipp", "si_trend_sig", "si_chandelier"],
    "rsi_exhaustion": ["si_rsi_div", "si_rsi_div_auto", "si_rsi_ss"],
    "smc_structure": ["si_bos", "si_choch", "si_ob", "si_fvg", "si_swing_str", "si_impulse",
                       "si_liq_intelg", "si_liquidity_entry", "si_sfb_hybrid", "si_sfp"],
    "orb_family": ["si_opening_range_rev", "si_hyb_opening_range_rev"],
    "ichimoku_pair": ["si_ichimoku", "si_ichi_trend_osc"],
    "ma_cross_generic": ["si_twin_range", "si_dual_ma_osc", "pta_hlc3", "pta_amat", "pta_ttm", "pta_long_run", "pta_short_run"],
    "momentum_pta_cross": ["pta_rsx", "pta_fisher_sig", "pta_kdj", "pta_tsi", "pta_mfi_sig"],
    "volatility_regime": ["pta_chop", "pta_squeeze", "si_bb_break", "si_kc_pyti"],
    "statistical_distribution": ["pta_zscore", "pta_skew", "pta_kurtosis", "pta_entropy", "pta_log_ret"],
}

# --- si_* enrichment -----------------------------------------------------------
# (fn, line, out_kind, inputs, nature, simple, bull, bear, neutral, primary, secondary, family)
SI_ENRICHMENT = {
    "si_adaptive_flow": ("adaptive_flow", 3638, "levels+markers", "OHLCV", "KAMA(ER) efficiency ratio plus ATR trailing stop plus BOS/CHoCH structure detection", "Adaptive moving-average flow with trailing stop and structure breaks.", "Price above KAMA/stop with bullish BOS", "Price below KAMA/stop with bearish BOS or CHoCH down", "Inside band, no confirmed break", "trend", ["smc_liquidity_structure"], "smc_structure"),
    "si_bahai": ("bahai_reversal_markers", 4253, "markers", "H,L", "Pine-port: count of lows/highs over 19 windows versus shift(lb=9)", "Counts window extremes to flag exhaustion reversals.", "Lows dominating count into support", "Highs dominating count into resistance", "Balanced counts", "reversal_zone", [], None),
    "si_bb_break": ("bb_breakout", 1101, "levels+markers", "C", "Bollinger Band(20,2) basis/upper/lower with close crossing events", "Close crossing Bollinger Bands.", "Close crosses above upper band", "Close crosses below lower band", "Close inside bands", "volatility", ["breakout_fakeout_trap"], "volatility_regime"),
    "si_bos": ("smc_bos_markers", 786, "markers", "OHLC", "Smart-money-concepts break-of-structure on swing_length=3 swings", "Break of prior swing high/low (SMC).", "Swing high broken upward", "Swing low broken downward", "No swing break", "smc_liquidity_structure", ["trend"], "smc_structure"),
    "si_cdl": ("cdl_patterns_adv", 260, "markers", "OHLCV", "External candlestick-pattern scanner module, priority-picked among 15 patterns", "Classic candlestick pattern scanner (external module).", "Bullish pattern detected", "Bearish pattern detected", "No pattern", "pattern_recognition", ["candle_structure"], None),
    "si_cdl_mb": ("cdl_multibar_markers", 1038, "markers", "OHLC", "Multi-bar candle patterns via external module (star fallback built in)", "Multi-bar candlestick patterns.", "Bullish multi-bar setup", "Bearish multi-bar setup", "None", "pattern_recognition", ["candle_structure"], None),
    "si_chandelier": ("finta_chandelier_markers", 3193, "markers", "OHLC", "Chandelier Exit (ATR from highest-high/lowest-low) crossover markers via finta library", "Chandelier-stop flip signals.", "Long stop crossed up", "Short stop crossed down", "No flip", "trend", ["risk_stop_target_sizing"], "atr_trailing_flip"),
    "si_choch": ("smc_choch_markers", 810, "markers", "OHLC", "Smart-money-concepts change-of-character on swing_length=3", "Trend character change (SMC).", "Bearish-to-bullish CHoCH", "Bullish-to-bearish CHoCH", "No character change", "smc_liquidity_structure", ["trend"], "smc_structure"),
    "si_cm_strg_pivt": ("cm_strg_pivt", 2761, "levels", "OHLCV", "ChrisMoody-filtered daily/weekly pivots plus cumulative VWAP bands plus hourly confirmation", "Filtered MTF pivots with VWAP confluence masks.", "Near filtered support pivot", "Near filtered resistance pivot", "Between levels", "vwap_orb_cpr_pivot", ["sr_price_levels"], "pivot_levels"),
    "si_cpr": ("cpr_levels", 645, "levels", "OHLC", "Previous-day central pivot range: pivot=(H+L+C)/3, BC/TC, stepped R1-R4/S1-S4 per day", "Classic previous-day CPR with resistances/supports.", "Price above TC / holding R as support", "Price below BC / rejecting R", "Inside CPR width", "vwap_orb_cpr_pivot", ["sr_price_levels"], "pivot_levels"),
    "si_cpr_v4": ("cpr_vedhaviyash4_levels", 3482, "snapshot_levels", "OHLC", "Daily CPR variant emitting last-row p/bc/tc/r1,s1,r2,s2 only", "Snapshot CPR variant (last row only).", "Above TC", "Below BC", "Inside range", "vwap_orb_cpr_pivot", ["sr_price_levels"], "pivot_levels"),
    "si_ctz_gann": ("ctz_gann_swing", 4457, "layers+markers", "OHLCV", "Fibonacci-length Gann swing layers F1..SF3 with MSB and RSI-divergence SMCD", "Gann-style swing layer engine.", "MSB up with layer support", "MSB down under layer resistance", "Layer mid", "fib_elliott_harmonic", ["trend"], "smc_structure"),
    "si_curve": ("curve_circle_markers", 3322, "markers", "OHLC", "Curve-shape pattern scan (U-bot/J-hook/arch/rollover) via external module", "Chart curve-shape recognizer.", "U-bot / J-hook base", "Arch rollover", "Flat", "pattern_recognition", ["reversal_zone"], None),
    "si_dark_cloud": ("dark_cloud_piercing", 452, "markers", "OHLC", "Body/midpoint-penetration dark-cloud-cover and piercing-line rules", "Dark cloud / piercing two-candle reversal.", "Piercing line up", "Dark cloud cover down", "None", "candle_structure", ["reversal_zone"], None),
    "si_dbl": ("double_top_bottom_markers", 1215, "markers", "OHLC", "Double top/bottom geometry detector with confirm/invalidation events (external)", "Double top and double bottom detector.", "Double bottom confirmed", "Double top confirmed", "Awaiting confirm", "pattern_recognition", ["reversal_zone"], None),
    "si_delta_vp": ("delta_vp", 2110, "markers+levels+sim", "OHLCV", "HTF breakout plus ATR risk-reward targets over rolling volume profile; includes simulated trade outcomes", "HTF breakout with volume-profile levels and simulated outcomes.", "Breakout with profile support", "Breakdown under profile", "Range", "volume_and_participation", ["sr_price_levels"], None),
    "si_dual_ma_osc": ("dual_ma_osc", 5763, "subpane", "C", "EMA fast/slow spread versus rolling sigma-band state machine", "Dual-EMA spread oscillator with sigma bands.", "Spread above upper band", "Spread below lower band", "Within band", "trend", ["momentum"], "ma_cross_generic"),
    "si_fib": ("fibonacci_markers", 2858, "markers", "OHLC", "Fibonacci retracement-level entry triggers (external)", "Fibonacci retracement entries.", "Long entry at fib support", "Short entry at fib resistance", "Between levels", "fib_elliott_harmonic", ["sr_price_levels"], None),
    "si_fmfm300": ("fmfm300_indicator", 6528, "canvas", "OHLCV", "SuperTrend plus MA braid plus demand/supply zones plus OB/FVG zones plus heatmap composite", "Composite trend/zones canvas (300-bar lookback).", "SuperTrend long in demand zone", "SuperTrend short in supply zone", "Mixed braid", "trend", ["smc_liquidity_structure", "sr_price_levels"], "smc_structure"),
    "si_flowscope": ("flowscope_markers", 3502, "marker", "OHLC", "Emits ONE constant neutral 'FlowScope Active' marker at bar 0 regardless of data", "Placeholder constant marker (near-stub).", "n/a - constant", "n/a - constant", "Always neutral active", "explanation_display_only", [], None),
    "si_fractal": ("si_fractal_markers", 1072, "markers", "H,L", "Williams fractals (2/2) emitted at pivot+2 via external module", "Williams fractal highs/lows.", "Fractal low hold", "Fractal high reject", "None", "sr_price_levels", ["pattern_recognition"], None),
    "si_fvg": ("smc_fvg_markers", 3090, "markers", "OHLC", "Three-candle fair value gap detection (SMC library)", "Fair value gaps (imbalance zones).", "Bullish FVG created/held", "Bearish FVG created/held", "Filled gap", "smc_liquidity_structure", ["breakout_fakeout_trap"], "smc_structure"),
    "si_har_zz": ("harmonic_patterns_zz_markers", 3470, "markers", "OHLC", "ZigZag-based Gartley/Bat/etc harmonic scanner (external) - DUPLICATE of si_harmonic module", "Harmonic patterns (duplicate wiring of si_harmonic).", "Bullish harmonic completion", "Bearish harmonic completion", "Pattern forming", "fib_elliott_harmonic", ["reversal_zone"], "harmonic_zigzag"),
    "si_harmonic": ("harmonic_pattern_markers", 3351, "markers", "OHLC", "ZigZag-based Gartley/Bat/butterfly/crab scanner (external)", "Harmonic pattern completion zones.", "Bullish PRZ complete", "Bearish PRZ complete", "Pattern forming", "fib_elliott_harmonic", ["reversal_zone"], "harmonic_zigzag"),
    "si_hourly_pvt": ("cm_hourly_pivots", 1483, "levels", "OHLC", "Previous-hour classic pivots (PP,R1-R3,S1-S3), forward-filled", "Hourly pivot levels from prior hour.", "Above hourly pivot", "Below hourly pivot", "At pivot", "vwap_orb_cpr_pivot", ["sr_price_levels"], "pivot_levels"),
    "si_hs": ("chart_hs_markers", 1173, "markers", "H,L", "Head-and-shoulders geometry scan (external; 5-pivot fallback whose symmetric +/-3 pivot window backfills markers onto the pivot bar)", "Head & shoulders detector.", "Inverse H&S complete", "H&S top complete", "Forming", "pattern_recognition", ["reversal_zone"], None),
    "si_hyb_opening_range_rev": ("hyb_opening_range_reversal", 4778, "markers+levels+sim", "OHLCV", "Opening-range reversal plus volume/ATR/VWAP/RSI/cooldown filters with quality score", "Filtered opening-range reversal.", "OR low reclaim with filters", "OR high reject with filters", "Outside window/cooldown", "vwap_orb_cpr_pivot", ["reversal_zone"], "orb_family"),
    "si_hybrid_ml": ("hybrid_ml_vwap_bb_markers", 3150, "markers", "OHLCV", "Online-weight 'ML' VWAP+BB hybrid Buy/Sell markers (external, tz-UTC handling)", "Hybrid VWAP-BB learning markers.", "Buy marker", "Sell marker", "None", "vwap_orb_cpr_pivot", ["reversal_zone"], "vwap_confluence"),
    "si_hybrid_ml_cpr": ("hybrid_ml_cpr", 5225, "markers+levels+dash", "OHLCV", "Hand-rolled online-weight learner over CPR/VWAP/BB extremes with confidence and success_after_10 feedback", "Self-weighting CPR/VWAP/BB confluence.", "Confident long confluence", "Confident short confluence", "Low confidence", "vwap_orb_cpr_pivot", ["sr_price_levels"], "vwap_confluence"),
    "si_ichi_trend_osc": ("ichimoku_trend_oscillator", 5860, "subpane+markers", "H,L,C", "Ichimoku Donchian-mid composite force oscillator with kumo state", "Ichimoku-composite trend oscillator.", "Force positive above kumo", "Force negative below kumo", "Neutral force", "trend", ["momentum"], "ichimoku_pair"),
    "si_ichimoku": ("tti_ichimoku_markers", 3166, "markers", "H,L", "Tenkan/Kijun Donchian-mid cross markers", "Tenkan-Kijun cross.", "Tenkan above Kijun", "Tenkan below Kijun", "Crossed flat", "trend", [], "ichimoku_pair"),
    "si_impulse": ("impulse_trend_markers", 1452, "markers", "OHLC", "Impulse/BOS-wave entries with retest logic (external)", "Impulse wave with retest entries.", "Impulse up retest hold", "Impulse down retest reject", "No impulse", "trend", ["smc_liquidity_structure"], "smc_structure"),
    "si_inside_out": ("inside_outside_bar", 861, "markers+levels+state", "OHLC", "Previous-candle inside/outside classification plus prior high/low/mid break states", "Inside/outside bar with prior H/L breaks.", "Outside bar bullish / prior-high break hold", "Outside bar bearish / prior-low break", "Inside bar", "candle_structure", ["sr_price_levels"], "inside_outside_bar"),
    "si_inside_candle_strategy": ("inside_candle_strategy", 6665, "markers+segments+levels", "OHLC", "Mother-candle breakout plus EMA9/21/200 plus custom SuperTrend segments", "Inside-bar breakout strategy.", "Mother bar high breakout", "Mother bar low breakdown", "Inside range", "candle_structure", ["breakout_fakeout_trap", "trend"], None),
    "si_kc_pyti": ("pyti_keltner_markers", 3425, "markers", "OHLC", "Keltner channel cross markers (pyti library)", "Keltner channel crosses.", "Close above upper KC", "Close below lower KC", "Inside channel", "volatility", [], "volatility_regime"),
    "si_liq_intelg": ("liquidity_intelligence", 3774, "markers+levels", "OHLCV", "Pivot-sweep plus rejection plus EMA/FVG/RSI scoring with quality/regime and entry/SL/TP1-3 levels", "Liquidity sweep intelligence with SL/TP plan.", "SSL sweep reclaimed with quality", "BSL sweep rejected with quality", "No qualified sweep", "smc_liquidity_structure", ["breakout_fakeout_trap", "risk_stop_target_sizing"], "smc_structure"),
    "si_liquidity_entry": ("liquidity_entry", 1906, "markers+levels", "OHLCV", "Sweep-reclaim wick model plus EMA filter plus TP/SL simulation", "Liquidity sweep entry model.", "Sweep-and-reclaim long", "Sweep-and-reject short", "No sweep", "smc_liquidity_structure", ["breakout_fakeout_trap"], "smc_structure"),
    "si_lrb": ("liquid_reversal_bands", 3545, "levels+markers", "C(H,L)", "EMA+ALMA fair-value band with deviation outer bands and reversal markers", "Fair-value deviation bands.", "Reversal up off lower band", "Rejection at upper band", "Mid fair value", "trendline_curve", ["reversal_zone"], None),
    "si_macd_ta": ("ta_macd_markers", 3410, "markers", "C", "MACD/signal-line cross markers (ta library)", "MACD signal crosses.", "MACD above signal", "MACD below signal", "Converged", "momentum", ["trend"], None),
    "si_mk_inside": ("inside_outside_mk_markers", 3518, "markers", "OHLC", "Inside/outside marker variant via external module - near-duplicate logic of si_inside_out", "Inside/outside markers (duplicate family).", "Outside bull", "Outside bear", "Inside neutral", "candle_structure", [], "inside_outside_bar"),
    "si_mp_va": ("mp_value_area_markers", 2993, "markers", "OHLCV", "Prior-session 24-bin volume profile with 70% value area break classification", "Market-profile value-area breaks.", "Acceptance above VAH", "Acceptance below VAL", "Inside value", "volume_and_participation", ["sr_price_levels"], None),
    "si_nbar": ("n_bar_reversal_markers", 1348, "markers", "OHLC", "N-bar high/low hold plus SuperTrend alignment with support/resistance annotation", "N-bar reversal with trend alignment.", "Bullish n-bar hold with ST up", "Bearish n-bar hold with ST down", "No hold", "reversal_zone", ["trend"], None),
    "si_ob": ("smc_ob_markers", 3113, "markers", "OHLC", "Order blocks detected off swing highs/lows (SMC library)", "Order block zones.", "Bullish OB reaction", "Bearish OB reaction", "Mitigated", "smc_liquidity_structure", ["sr_price_levels"], "smc_structure"),
    "si_opening_range_rev": ("opening_range_reversal", 4611, "markers+levels+sim", "OHLC", "Timed opening-range window with L1(1.272)-midpoint take-profit simulation", "Opening-range reversal play.", "OR low reversal long", "OR high reversal short", "Outside window", "vwap_orb_cpr_pivot", ["reversal_zone"], "orb_family"),
    "si_outside_rev": ("outside_reversal", 292, "markers", "OHLC", "Prior-bar engulfing outside-reversal rules", "Outside engulfing reversal.", "Bullish outside reversal", "Bearish outside reversal", "None", "candle_structure", ["reversal_zone"], "inside_outside_bar"),
    "si_problty_grid": ("problty_grid", 2572, "events+levels+dash", "OHLCV", "Session-open OR/ATR ladder with Laplace hit-probability statistics and boxes/dashboard", "Session probability ladder display.", "Up-ladder probability rising", "Down-ladder probability rising", "Mixed", "risk_stop_target_sizing", ["vwap_orb_cpr_pivot"], "orb_family"),
    "si_pta_cdl": ("pandas_ta_cdl_markers", 3530, "markers", "OHLC", "pandas-ta CDL engulfing markers", "Engulfing pattern via pandas-ta.", "Bullish engulfing", "Bearish engulfing", "None", "candle_structure", ["pattern_recognition"], None),
    "si_rev_radar": ("reversal_radar_markers", 1248, "markers", "OHLCV", "Multi-confluence reversal radar (RSI/wick/volume fallbacks)", "Reversal confluence radar.", "Bullish confluence cluster", "Bearish confluence cluster", "Below threshold", "reversal_zone", ["confirmation"], None),
    "si_rsi_div": ("rsi_divergence_sub", 527, "subpane", "C", "Dual-RSI divergence values (fast/slow) via external module", "RSI divergence sub-pane.", "Bullish divergence value", "Bearish divergence value", "Aligned", "exhaustion_divergence", ["momentum"], "rsi_exhaustion"),
    "si_rsi_div_auto": ("rsi_div_auto", 3982, "markers+series", "C,H,L", "RSI divergence on left/right-confirmed pivots, timeframe-auto right-window", "Auto RSI divergence with confirmed pivots.", "Higher-low price with higher RSI", "Lower-high price with lower RSI", "No divergence", "exhaustion_divergence", ["momentum"], "rsi_exhaustion"),
    "si_rsi_ss": ("stockstats_rsi_markers", 3455, "markers", "C", "RSI 30/70 cross markers (stockstats)", "RSI zone crosses.", "Cross up through 30", "Cross down through 70", "Mid-range", "momentum", ["exhaustion_divergence"], "rsi_exhaustion"),
    "si_sar_tapy": ("tapy_psar_markers", 3440, "markers", "C", "Parabolic SAR flip markers (ta-py)", "Parabolic SAR flips.", "SAR flipped below price", "SAR flipped above price", "n/a", "trend", [], None),
    "si_sbs": ("sbs_swing_markers", 3365, "markers", "OHLC", "SBS swing area/trade markers (external)", "SBS swing system.", "SBS long", "SBS short", "Flat", "trend", [], None),
    "si_sfb_hybrid": ("_sfb_hybrid_compute->sfp_hybrid_markers", 4317, "markers+levels", "OHLCV", "ICT swing sweep plus doji plus EMA/SMA/HMA/VWAP filter stack", "ICT-style sweep filter hybrid.", "Qualified sweep long", "Qualified sweep short", "Filtered out", "smc_liquidity_structure", ["candle_structure"], "smc_structure"),
    "si_sfp": ("sfp_markers", 936, "markers", "OHLC", "Centered-swing liquidity sweep plus doji confirmation with ATR annotation", "Swing failure pattern.", "Low sweep reclaimed", "High sweep rejected", "Clean break", "breakout_fakeout_trap", ["sr_price_levels"], "smc_structure"),
    "si_st_talipp": ("talipp_supertrend_markers", 3395, "markers", "C", "Incremental SuperTrend flip markers (talipp streaming library)", "Streaming SuperTrend flips.", "ST bullish flip", "ST bearish flip", "n/a", "trend", [], "atr_trailing_flip"),
    "si_strg_pivt": ("strg_pivt", 2665, "levels", "OHLCV", "Resampled daily/weekly pivots plus cumulative VWAP bands plus hourly confirmation masks", "MTF pivots with VWAP bands.", "Near daily/weekly support + VWAP lower", "Near daily/weekly resistance + VWAP upper", "Between", "vwap_orb_cpr_pivot", ["sr_price_levels"], "pivot_levels"),
    "si_swing_break": ("swing_breakout_sequence", 4069, "markers", "OHLC", "Confirmed 5-pivot consolidation plus breakout trigger with A-B-2-3-4 sequence points", "Consolidation breakout sequences.", "Sequence bullish trigger", "Sequence bearish trigger", "Still consolidating", "breakout_fakeout_trap", ["sr_price_levels"], "smc_structure"),
    "si_swing_str": ("swing_structure", 710, "markers", "H,L", "Centered pivot_len-window swing classification HH/LH/HL/LL with confirmed_index/price", "Swing structure labels.", "HH/HL sequence", "LH/LL sequence", "Mixed", "sr_price_levels", ["smc_liquidity_structure"], "smc_structure"),
    "si_sweep_inside_rr": ("sweep_inside_rr_strategy", 6859, "markers+trades+dash", "OHLC", "Sweep/inside patterns plus EMA plus fixed-risk-reward backtest dashboard", "Sweep-plus-inside RR strategy.", "Long setup triggered", "Short setup triggered", "No setup", "smc_liquidity_structure", ["candle_structure", "risk_stop_target_sizing"], None),
    "si_three_inside": ("three_inside", 386, "markers", "OHLC(V)", "Three-inside-up/down pattern with body-percentage ratios", "Three-inside reversal pattern.", "Three inside up", "Three inside down", "None", "candle_structure", ["reversal_zone"], None),
    "si_three_inside_filtered": ("three_inside_filtered", 416, "markers", "OHLCV", "Three-inside plus EMA20/50 trend plus volume filter", "Filtered three-inside.", "With uptrend filter", "With downtrend filter", "Filter blocks", "candle_structure", ["reversal_zone", "trend"], None),
    "si_trend_sig": ("trend_signals_markers", 2886, "markers", "OHLC", "ATR-chandelier trend-flip buy/sell and trend-begin markers (external)", "Chandelier trend signals.", "Trend begins up", "Trend begins down", "Continuation", "trend", [], "atr_trailing_flip"),
    "si_trendln": ("trendln_breakout_markers", 6092, "markers+segments", "C(log)", "Per-bar 72-bar log-price polynomial-fit S/R optimization with break markers and fitted segments", "Rolling polyfit trendline breaks.", "Log-close breaks fitted resistance up", "Breaks fitted support down", "Inside channel", "trendline_curve", ["breakout_fakeout_trap"], None),
    "si_twin_range": ("twin_range_filter_markers", 3137, "markers", "C", "Dual EMA-range filter cross markers (external)", "Twin range filter.", "Long filter cross", "Short filter cross", "No cross", "trend", [], "ma_cross_generic"),
    "si_vol_exh": ("vol_exhaustion_markers", 513, "markers", "OHLCV", "Volume-exhaustion flags (external module)", "Volume exhaustion flags.", "Seller exhaustion", "Buyer exhaustion", "None", "volume_and_participation", ["exhaustion_divergence"], None),
    "si_vwap_bb_ml_conf": ("vwap_bb_ml_conf", 5554, "markers+levels", "OHLCV", "VWAP k-sigma times BB confluence-meet with rule probability, regime and score", "VWAP-BB meet confluence scoring.", "Meet at lower confluence", "Meet at upper confluence", "No meet", "vwap_orb_cpr_pivot", ["sr_price_levels", "confirmation"], "vwap_confluence"),
    "si_vwap_conf": ("vwap_bb_confluence", 2917, "levels", "OHLCV", "VWAP plus Bollinger confluence overlay levels (upper_conf/lower_conf/+/-1) via external module", "VWAP-BB confluence levels.", "Price at lower conf support", "Price at upper conf resistance", "Mid", "vwap_orb_cpr_pivot", ["confirmation"], "vwap_confluence"),
    "si_vwap_super": ("vwap_bb_super_confluence", 2949, "levels+markers", "OHLCV", "VWAP+BB super-confluence overlays with upper/lower reversal markers (external)", "Super VWAP-BB reversal markers.", "Lower-band reversal up", "Upper-band rejection down", "None", "vwap_orb_cpr_pivot", ["reversal_zone"], "vwap_confluence"),
    "si_wekly_pivot": ("wekly_pivot", 1583, "levels", "OHLC", "Weekly/daily/hourly classic pivots shift(1) with tolerance confluence flags", "MTF classic pivots (prior period).", "Above weekly pivot", "Below weekly pivot", "At pivot", "vwap_orb_cpr_pivot", ["sr_price_levels"], "pivot_levels"),
    "si_zz_swing": ("zigzag_swing_markers", 3384, "markers", "OHLC", "ZigZag pivot-confirm Bull/Bear markers (external)", "ZigZag swing turns.", "ZZ bull turn", "ZZ bear turn", "n/a", "trendline_curve", ["reversal_zone"], "harmonic_zigzag"),
}

# --- pta_* enrichment: (lib_call, params, bull, bear, neutral, primary, secondary) ---
PTA_ENRICHMENT = {
    "pta_rsx": ("_pta.rsx(Close)", "len=14, thr=50", "RSX crosses up through 50", "RSX crosses down through 50", "Around 50", "momentum", []),
    "pta_fisher_sig": ("_pta.fisher(H,L)", "len=9", "Fisher crosses above signal", "Fisher crosses below signal", "Converged", "momentum", []),
    "pta_kdj": ("_pta.kdj(H,L,C)", "len=9", "K crosses above D", "K crosses below D", "Entangled", "momentum", []),
    "pta_mfi_sig": ("_pta.mfi(H,L,C,V)", "len=14", "MFI crosses up through 30", "MFI crosses down through 70", "Mid-range", "volume_and_participation", ["momentum"]),
    "pta_cmf": ("_pta.cmf(H,L,C,V)", "len=20", "CMF zero-cross up", "CMF zero-cross down", "Near zero", "volume_and_participation", []),
    "pta_vortex": ("_pta.vortex(H,L,C)", "len=14", "VI+ crosses above VI-", "VI- crosses above VI+", "Intertwined", "trend", []),
    "pta_aroon_sig": ("_pta.aroon(H,L)", "len=25", "UP crosses above DOWN", "DOWN crosses above UP", "Equal", "trend", []),
    "pta_tsi": ("_pta.tsi(Close)", "fast13/slow25/sig13", "TSI crosses above signal", "TSI crosses below signal", "Converged", "momentum", []),
    "pta_chop": ("_pta.chop(H,L,C)", "len=14, thr=38.2", "n/a (regime flag, neutral marker)", "n/a (regime flag, neutral marker)", "CHOP crosses below 38.2 => trending regime", "volatility", ["explanation_display_only"]),
    "pta_squeeze": ("_pta.squeeze(H,L,C)", "bb=20, kc=20", "Squeeze histogram crosses above 0 (fire)", "n/a", "In squeeze", "volatility", []),
    "pta_zscore": ("rolling z-score of Close (pure pandas)", "per=50, thr +/-2.0", "z crosses below -2 (mean-reversion long context)", "z crosses above +2 (mean-reversion short context)", "Within +/-2", "reversal_zone", ["statistical"]),
    "pta_kurtosis": ("rolling kurtosis of returns", "per=30, thr>5.0", "n/a (neutral fat-tail warning)", "n/a (neutral fat-tail warning)", "Spike above 5 flagged neutral", "explanation_display_only", ["statistical"]),
    "pta_skew": ("rolling skew of returns", "per=30, thr<-0.5", "Negative-skew drop (contrarian long context)", "n/a", "Above threshold", "reversal_zone", ["statistical"]),
    "pta_log_ret": ("rolling mean of log returns", "per=10, thr=0", "Mean log-return crosses above 0", "Crosses below 0", "Near zero", "momentum", ["statistical"]),
    "pta_drawdown": ("drawdown vs 50-bar rolling max", "thr=1%, recover=3 bars", "Deep drawdown then rising (DD Recovery)", "n/a", "No qualifying drawdown", "exhaustion_divergence", ["risk_stop_target_sizing"]),
    "pta_hlc3": ("SMA of HLC3", "fast=10/slow=30", "Fast SMA crosses above slow", "Fast crosses below slow", "Flat", "trend", ["confirmation"]),
    "pta_ebsw": ("pta.ebsw(Close)", "len=40, bars=15", "Sine wave crosses above 0", "Crosses below 0", "At zero", "trend", ["explanation_display_only"]),
    "pta_dsp": ("pta.dsp(Close)", "cutoff=0.15", "Cycle component crosses above 0 (bull-only emitter)", "n/a (no bear emitter)", "Below 0", "momentum", ["explanation_display_only"]),
    "pta_amat": ("pta.amat(Close)", "fast=8/slow=21", "AMAT long column > 0", "AMAT short column > 0", "Neither", "trend", []),
    "pta_ttm": ("pta.ttm_trend(H,L,C)", "len=6", "Trend state flips to >0", "n/a (bull-only emitter)", "State <= 0", "trend", []),
    "pta_long_run": ("custom EWMA(21/55)+ATR slope+confirm", "21/55, slope=8, conf=5", "All components aligned up after confirmation", "n/a", "Unconfirmed", "trend", ["confirmation"]),
    "pta_short_run": ("custom EWMA(21/55)+ATR slope+confirm (mirror)", "21/55, slope=8, conf=5", "n/a", "All components aligned down after confirmation", "Unconfirmed", "trend", ["confirmation"]),
    "pta_entropy": ("scipy entropy of 5-bin rolling histogram", "per=20, thr<0.4", "Low entropy compressing (pre-expansion long-neutral context)", "n/a", "Entropy above 0.4", "volatility", ["statistical", "explanation_display_only"]),
}

GROUP_LABELS = {
    "directional_signal": "Directional BUY/SELL signal",
    "trend": "Trend",
    "momentum": "Momentum",
    "volatility": "Volatility",
    "volume_and_participation": "Volume and participation",
    "sr_price_levels": "Support/resistance and price levels",
    "reversal_zone": "Reversal zone",
    "confirmation": "Confirmation",
    "pattern_recognition": "Pattern recognition",
    "candle_structure": "Candle structure",
    "breakout_fakeout_trap": "Breakout/fakeout/trap",
    "exhaustion_divergence": "Exhaustion/divergence",
    "vwap_orb_cpr_pivot": "VWAP/ORB/CPR/pivot",
    "trendline_curve": "Trendline/curve",
    "fib_elliott_harmonic": "Fibonacci/Elliott/Harmonic",
    "smc_liquidity_structure": "SMC/liquidity/structure",
    "risk_stop_target_sizing": "Risk, stop, target and sizing",
    "execution_liquidity": "Execution/liquidity",
    "explanation_display_only": "Explanation-only or display-only",
}


def lookahead_class(indicator_id: str) -> tuple[str, str]:
    if indicator_id in FUTURE_LEAK_IDS:
        return "future_outcome_leakage", "HIGH"
    if indicator_id in CENTERED_PIVOT_IDS:
        return "centered_pivot_confirmation", "MEDIUM"
    if indicator_id in ZIGZAG_REPAINT_IDS:
        return "zigzag_repaint", "HIGH"
    if indicator_id in LIB_SHIFT_RISK_IDS:
        return "library_label_shift_possible", "LOW"
    if indicator_id.startswith("pta_"):
        return "none_found_trailing_shift1", "NONE"
    return "none_found_past_only", "NONE"


def family_of(indicator_id: str) -> str | None:
    for fam, members in REDUNDANCY_FAMILIES.items():
        if indicator_id in members:
            return fam
    return None


def correlated_of(indicator_id: str) -> list[str]:
    fam = family_of(indicator_id)
    if not fam:
        return []
    return [m for m in REDUNDANCY_FAMILIES[fam] if m != indicator_id]


def build_contract(entry, enrich: dict) -> dict:
    iid = entry["indicator_id"] if isinstance(entry, dict) else entry.indicator_id
    d = entry if isinstance(entry, dict) else entry.model_dump()
    fn, line, out_kind, inputs, nature, simple, bull, bear, neutral, primary, secondary, family = enrich
    is_pta = iid.startswith("pta_")
    src_file = VENDOR_PTA_WRAPPER if is_pta else VENDOR_SELF
    impl_file = VENDOR_PTA_SIGNALS if is_pta else VENDOR_SELF
    delay = int(d.get("confirmation_delay_bars") or 0)
    lag_weight = round(1.0 / (1.0 + delay), 6)
    lk_class, lk_level = lookahead_class(iid)
    leaked = iid in FUTURE_LEAK_IDS
    status = str(d.get("status") or "unknown")
    promoted = iid in PROMOTED_13
    runtime_status = "promoted_runtime_computed" if promoted else (
        "registered_probe_only" if is_pta else "registered_not_promoted")
    if iid == "si_flowscope":
        runtime_status = "near_stub_constant_output"
    usable_prob = bool(d.get("used_for_probability")) and status == "validated" and not leaked
    usable_action = False if leaked else False  # research-only platform: never trade-actionable
    ev = [{"file": impl_file, "lines": f"L{line}", "what": f"compute function {fn}"},
          {"file": "apps/api/app/behavior/runtime_readiness.py", "lines": "L84-97,L99-123", "what": "group id registration"},
          {"file": "apps/api/app/behavior/indicator_registry.py", "lines": "L128+", "what": "registry metadata entry"}]
    if is_pta:
        ev.append({"file": VENDOR_PTA_LIB, "lines": "-", "what": "underlying pandas-ta-classic bindings"})
    test_ids = ["TV-V060-001", "TV-V060-002", "test_vendor_indicators"]
    test_ids.append("CAT-V196-001..008")
    return {
        "indicator_id": iid,
        "display_name": d.get("display_name"),
        "aliases": [],
        "source_registry": "tradevision_behavior_registry_v1",
        "source_file": src_file,
        "source_file_authoritative": "vendor_copy",
        "source_drift_note": (
            "Vendor self_indc.py is ahead of shared/indicators original (tz-safe weekly VWAP fix not backported)."
            if not is_pta else "Wrapper identical to source original."),
        "callable_name": fn,
        "callable_line": line,
        "implementation_status": status,
        "runtime_status": runtime_status,
        "purpose": d.get("purpose") or simple,
        "simple_explanation": simple,
        "primary_category": primary,
        "secondary_categories": secondary,
        "evidence_role": ("explanation_only_forced" if leaked else
                          ("display_context" if primary == "explanation_display_only" else
                           ("d3a_setup_candidate" if promoted else "evidence_reference"))),
        "required_input_columns": inputs.split(",") if isinstance(inputs, str) else inputs,
        "parameters_and_defaults": d.get("default_parameters_json") or {},
        "minimum_bars": d.get("minimum_bars"),
        "warmup_policy": f"warmup_bars_exact={d.get('warmup_bars_exact')}" + (" ; wrapper suppresses first 20 bars (_WARMUP_BARS)" if is_pta else ""),
        "supported_timeframes": d.get("timeframes_allowed"),
        "timeframes_note": "registry uses one flat ALL_TIMEFRAMES list; per-timeframe overrides not modeled yet",
        "formula_in_plain_english": nature,
        "mathematical_formula": "UNKNOWN_HEURISTIC_RULESET_SEE_CALCULATION_STEPS" if not is_pta else f"classic-library formula via {fn}: {nature}",
        "calculation_steps_source": "authored_from_code_reading_2026-08-25_audit",
        "output_columns": d.get("output_columns") or [],
        "output_kind": out_kind,
        "output_types": "discrete_marker_events" if "marker" in out_kind else "continuous_series_or_levels",
        "output_range": "UNKNOWN",
        "signal_values": {"bullish": bull, "bearish": bear, "neutral": neutral},
        "signal_purpose": simple,
        "direction_semantics": d.get("direction_semantics"),
        "direction_meaning": d.get("direction_meaning"),
        "bullish_meaning": bull,
        "bearish_meaning": bear,
        "neutral_meaning": neutral,
        "trade_usage": d.get("trade_usage") or "UNKNOWN_not_established",
        "entry_usage": d.get("trade_usage") or "UNKNOWN_not_established",
        "wait_usage": d.get("no_trade_usage") or "UNKNOWN_not_established",
        "no_trade_usage": d.get("no_trade_usage") or "UNKNOWN_not_established",
        "stop_usage": ("see linked SL/TP outputs" if "sl" in out_kind.lower() or iid in {"si_liq_intelg"} else "UNKNOWN_not_established"),
        "target_usage": ("see linked TP outputs" if "tp" in str(out_kind).lower() or iid in {"si_liq_intelg"} else "UNKNOWN_not_established"),
        "sizing_usage": "UNKNOWN_not_established",
        "exit_usage": d.get("risk_usage") or "UNKNOWN_not_established",
        "best_market_regime": d.get("best_market_regime"),
        "bad_market_regime": d.get("bad_market_regime"),
        "best_session_phase": ("opening_range_window" if "opening_range" in nature.lower() or "or ladder" in nature.lower() else "UNKNOWN_not_established"),
        "lag_behavior": d.get("lag_behavior"),
        "confirmation_delay_bars": delay,
        "lag_weight_formula": "lag_weight = 1 / (1 + confirmation_delay_bars)",
        "lag_weight": lag_weight,
        "sequential_signal_window": d.get("sequential_signal_window"),
        "normalization_method": d.get("normalization_method"),
        "missing_policy": d.get("missing_policy"),
        "false_positive_conditions": d.get("false_positive_conditions"),
        "confirmation_rules": d.get("confirmation_rules"),
        "conflict_rules": d.get("conflict_rules") or ("wrapper _sanitize_events drops same-candle bull+bear conflicts" if is_pta else "UNKNOWN_not_established"),
        "redundancy_family": family or "standalone",
        "correlated_indicators": correlated_of(iid),
        "vote_weight_rule": "correlated family members share reduced weight; no independent full votes within a family",
        "mtf_usage": "per-timeframe recompute via real_indicator_adapter with fully closed higher-timeframe candles only",
        "closed_candle_requirement": bool(d.get("closed_bar_only")),
        "lookahead_risk": lk_class,
        "lookahead_severity": lk_level,
        "repainting_risk": lk_level if lk_class != "none_found_trailing_shift1" else "NONE",
        "future_confirmation_delay": DISCLOSED_DELAY_IDS.get(iid, "n/a"),
        "future_leak_detail": FUTURE_LEAK_IDS.get(iid),
        "per_stock_reliability": d.get("per_stock_reliability"),
        "per_regime_reliability": "report-time rollup with Bayesian shrinkage (count+15)/(n+30); falls back to fabricated fixture labels when history DB empty (indicator_reliability_memory.py:314-360)",
        "historical_success_rate": d.get("historical_success_rate"),
        "historical_failure_rate": d.get("historical_failure_rate"),
        "rates_provenance": "fixture_fallback_until_real_labels_ingested",
        "usable_for_probability": usable_prob,
        "usable_for_explanation": True,
        "usable_for_trade_action": usable_action,
        "live_trading_blocked": True,
        "research_only": True,
        "capability_status_at_audit": "MOCK (app/state.py L208; all /behavior/indicators routes)",
        "safety_notes": [
            "compute functions fail silently to [] / {} when external modules or hardcoded paths are missing",
            "9C-DNA evidence path uses real HSTRY bars when available (v1.98); synthetic fallback is labelled source_mode=synthetic_fallback; paper-guidance snapshot path uses real bars",
        ] + ([f"FUTURE OUTCOME LEAKAGE: {FUTURE_LEAK_IDS[iid]}"] if leaked else []),
        "external_dependencies": (["hardcoded D:/Projects/test1/self indc exec-load", "smart-money-concepts smc.py", "talipp", "ta", "pyti", "ta-py", "stockstats", "pandas-ta-classic", "scipy (entropy)"] if not is_pta else ["pandas-ta-classic", "scipy (entropy only)"]),
        "source_evidence": ev,
        "test_ids": test_ids,
        "ontology_version": d.get("ontology_version"),
        "formula_hash": d.get("formula_hash"),
        "point_in_time_safe_flag_in_registry": d.get("point_in_time_safe"),
        "pit_audit_passed_date": d.get("pit_audit_passed_date"),
        "internal_lookahead_audit_result": d.get("internal_lookahead_audit_result"),
    }


def _pta_inputs(lib: str) -> list[str]:
    s = lib.upper()
    cols: list[str] = []
    if "O," in s or "(O" in s:
        cols.append("open")
    if "H," in s or "(H" in s or ",H" in s:
        cols.append("high")
    if "L," in s or "(L" in s or ",L" in s:
        cols.append("low")
    if "C)" in s or ",C" in s or "(CLOSE" in s or "CLOSE" in s:
        cols.append("close")
    if ",V)" in s or "(V" in s or " V" in s:
        cols.append("volume")
    return cols or ["close"]


def main() -> None:
    report = build_indicator_registry_report()
    raw_list: list = None
    for attr in ("entries", "indicators", "items"):
        if isinstance(report, dict) and attr in report:
            raw_list = report[attr]
            break
        if hasattr(report, attr):
            raw_list = getattr(report, attr)
            break
    if raw_list is None:
        raw_list = report if isinstance(report, (list, tuple)) else None
    if raw_list is None:
        raise SystemExit(f"cannot locate entry list on {type(report)!r}")
    raw_entries = [e.model_dump(by_alias=False) if hasattr(e, "model_dump") else dict(e)
                   for e in raw_list]
    ids_live = [e["indicator_id"] for e in raw_entries]

    contracts = []
    missing_enrichment, extra_enrichment = [], []
    for e in raw_entries:
        iid = e["indicator_id"]
        if iid.startswith("pta_"):
            lib, params, bull, bear, neutral, prim, sec = PTA_ENRICHMENT[iid]
            enrich = (lib, 0, "markers", _pta_inputs(lib),
                      f"{lib} with parameters {params}",
                      f"Marker generated from {lib}.",
                      bull, bear, neutral, prim, sec, family_of(iid))
        else:
            if iid not in SI_ENRICHMENT:
                missing_enrichment.append(iid)
                continue
            enrich = SI_ENRICHMENT[iid]
        contracts.append(build_contract(e, enrich))
    extra_enrichment = [k for k in SI_ENRICHMENT if k not in set(ids_live)]

    if missing_enrichment or extra_enrichment:
        print("MISSING enrichment:", missing_enrichment)
        print("EXTRA enrichment:", extra_enrichment)
        raise SystemExit(1)

    dupes = [k for k, v in Counter(c["indicator_id"] for c in contracts).items() if v > 1]
    if dupes or len(contracts) != 94:
        raise SystemExit(f"contract integrity failure: n={len(contracts)} dupes={dupes}")

    # Normalize registry-null metadata to explicit unknown markers (never invented).
    NORMALIZE_STR_FIELDS = [
        "purpose", "simple_explanation", "direction_semantics", "direction_meaning",
        "trade_usage", "entry_usage", "wait_usage", "no_trade_usage", "stop_usage",
        "target_usage", "exit_usage", "best_market_regime", "bad_market_regime",
        "lag_behavior", "sequential_signal_window", "normalization_method",
        "missing_policy", "false_positive_conditions", "confirmation_rules",
        "per_stock_reliability", "output_columns",
    ]
    for c in contracts:
        for k in NORMALIZE_STR_FIELDS:
            v = c.get(k)
            if v is None or (isinstance(v, str) and not v.strip()) or v == []:
                c[k] = "UNKNOWN_not_established"

    out_dir = PROJECT_ROOT / "data" / "indicator-intelligence"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "indicator_contracts.v1.json").write_text(
        json.dumps({"schema_version": "indicator-intelligence-contracts.v1",
                    "generated_by": "scripts/build_indicator_intelligence_catalog.py",
                    "authority_decision": "vendor_copy_authoritative_per_scope_approval_2026-08-25",
                    "count": len(contracts), "contracts": contracts}, indent=2, ensure_ascii=False),
        encoding="utf-8")

    # coverage report
    promoted = [c["indicator_id"] for c in contracts if c["runtime_status"] == "promoted_runtime_computed"]
    reg_only_self = [c["indicator_id"] for c in contracts if c["runtime_status"] == "registered_not_promoted"]
    probe_only = [c["indicator_id"] for c in contracts if c["runtime_status"] == "registered_probe_only"]
    proxy = [c["indicator_id"] for c in contracts if c["implementation_status"] == "proxy"]
    validated = [c["indicator_id"] for c in contracts if c["implementation_status"] == "validated"]
    cov = {
        "schema_version": "indicator-intelligence-coverage.v1",
        "totals": {"registry_entries": len(ids_live), "contracts_written": len(contracts),
                    "self_indc": sum(1 for i in ids_live if i.startswith("si_")),
                    "pta_markers": sum(1 for i in ids_live if i.startswith("pta_")),
                    "promoted_runtime_computed": len(promoted), "registered_not_promoted": len(reg_only_self),
                    "registered_probe_only_pta": len(probe_only),
                    "validated": len(validated), "proxy": len(proxy)},
        "promoted_runtime_computed": promoted,
        "registered_not_promoted": reg_only_self,
        "registered_probe_only_pta": probe_only,
        "near_stub_constant_output": [c["indicator_id"] for c in contracts if c["runtime_status"] == "near_stub_constant_output"],
        "bucket_reconciliation": "promoted_runtime_computed + registered_not_promoted + registered_probe_only_pta + near_stub_constant_output == registry_entries == 94",
        "proxy_reasons": {"empty_no_signal_on_sample": [i for i in proxy if not i.startswith("pta_")],
                           "pta_all_proxy_pending_pit_audit": [i for i in proxy if i.startswith("pta_")]},
        "future_outcome_leakage": {k: v for k, v in FUTURE_LEAK_IDS.items()},
        "duplicate_wiring": {"si_har_zz": "duplicate module wiring of si_harmonic", "si_mk_inside": "duplicate logic family of si_inside_out"},
        "shadowed_definitions_in_self_indc": [
            "dark_cloud_piercing L423->L452", "cpr_levels L545->L645", "swing_structure L588->L710",
            "inside_outside_bar L834->L861", "sfp_markers L923->L936", "bahai_reversal_markers L1140->L4253",
            "trendln_breakout_markers L3287->L6092"],
        "redundancy_families": REDUNDancy_FAMILIES_SAFE(),
        "category_unclassified_in_old_registry": 41,
        "unknown_field_policy": "fields that cannot be verified from code or registry are written UNKNOWN/not_established and never invented",
        "known_limitations": [
            "9C-DNA evidence path uses real HSTRY bars when available (v1.98); symbols without local history fall back to synthetic candles labelled source_mode=synthetic_fallback",
            "all indicator API routes report CapabilityStatus.MOCK",
            "~25 self_indc groups depend on exec-loaded external modules from hardcoded local paths",
            "EMPTY_NO_SIGNAL_ON_SAMPLE proxy labels are stale (single past sweep, never re-checked)",
            "vendor self_indc.py ahead of shared/indicators original (tz fix not backported)",
        ],
        "follow_up_proposals_out_of_catalog_scope": [
            "backport weekly-VWAP tz fix to shared/indicators/self_indc.py",
            "replace synthetic 9C candle source with real closed candles",
            "remove shadowed duplicate definitions in self_indc.py",
            "re-run EMPTY_NO_SIGNAL_ON_SAMPLE sweep against current sample data",
            "parameterize external module paths via env/config",
        ],
    }
    (out_dir / "indicator_coverage_report.json").write_text(json.dumps(cov, indent=2), encoding="utf-8")

    # generated human table grouped by primary category
    lines = ["# Indicator Catalog Table (generated - do not edit by hand)", "",
             f"Total: {len(contracts)} indicators. Runtime computed: {len(promoted)}. Proxy: {len(proxy)}. Future-leak (explanation-only forced): {len(FUTURE_LEAK_IDS)}.", ""]
    by_group = {}
    for c in contracts:
        by_group.setdefault(c["primary_category"], []).append(c)
    for g in sorted(by_group):
        lines += [f"## {GROUP_LABELS.get(g, g)} ({len(by_group[g])})", "",
                  "| id | name | status | runtime | lag_w | lookahead | family |", "|---|---|---|---|---|---|---|"]
        for c in sorted(by_group[g], key=lambda x: x["indicator_id"]):
            lines.append(f"| {c['indicator_id']} | {c['display_name']} | {c['implementation_status']} | "
                         f"{c['runtime_status']} | {c['lag_weight']} | {c['lookahead_risk']} | {c['redundancy_family']} |")
        lines.append("")
    gen_dir = PROJECT_ROOT / "docs" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "INDICATOR_CATALOG_TABLE.md").write_text("\n".join(lines), encoding="utf-8")

    # group & use map (generated core; hand narrative lives in the doc header)
    glines = ["# Indicator Group and Use Map (generated core)", "",
              "Vote rule: correlated family members share reduced weight (no independent full votes).", ""]
    for g in GROUP_LABELS:
        members = [c for c in contracts if c["primary_category"] == g or g in c["secondary_categories"]]
        if not members:
            continue
        glines += [f"## {GROUP_LABELS[g]} - {len(members)} indicators", ""]
        for c in sorted(members, key=lambda x: x["indicator_id"]):
            role = "PRIMARY" if c["primary_category"] == g else "secondary"
            glines.append(f"- {c['indicator_id']} ({role}, {c['implementation_status']}, lag_w={c['lag_weight']}): "
                          f"use={c['trade_usage']}; wait={c['wait_usage']}")
        fams = sorted({c["redundancy_family"] for c in members if c["redundancy_family"] != "standalone"})
        if fams:
            glines.append(f"- vote families touching this group: {', '.join(fams)}")
        glines.append("")
    (PROJECT_ROOT / "docs" / "INDICATOR_GROUP_AND_USE_MAP.md").write_text("\n".join(glines), encoding="utf-8")

    print(json.dumps(cov["totals"], indent=2))
    print("written:", out_dir / "indicator_contracts.v1.json")
    print("written:", out_dir / "indicator_coverage_report.json")
    print("written:", gen_dir / "INDICATOR_CATALOG_TABLE.md")
    print("written:", PROJECT_ROOT / "docs" / "INDICATOR_GROUP_AND_USE_MAP.md")


def REDUNDancy_FAMILIES_SAFE():
    clean = {k: [m for m in v if not m.endswith("_placeholder")] for k, v in REDUNDANCY_FAMILIES.items()}
    return {k: v for k, v in clean.items() if v}


if __name__ == "__main__":
    main()
