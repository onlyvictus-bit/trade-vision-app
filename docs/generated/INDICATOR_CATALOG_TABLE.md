# Indicator Catalog Table (generated - do not edit by hand)

Total: 94 indicators. Runtime computed: 49. Proxy: 7. Future-leak (explanation-only forced): 6.

## Breakout/fakeout/trap (2)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_sfp | SFP | validated | promoted_runtime_computed | 1.0 | centered_pivot_confirmation | smc_structure |
| si_swing_break | Swing Break | validated | promoted_runtime_computed | 0.5 | centered_pivot_confirmation | smc_structure |

## Candle structure (8)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_dark_cloud | Dark Cloud | validated | registered_not_promoted | 0.5 | none_found_past_only | standalone |
| si_inside_candle_strategy | Inside Candle Strategy | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_inside_out | Inside OUT | validated | promoted_runtime_computed | 1.0 | none_found_past_only | inside_outside_bar |
| si_mk_inside | MK Inside | validated | promoted_runtime_computed | 1.0 | none_found_past_only | inside_outside_bar |
| si_outside_rev | Outside REV | validated | promoted_runtime_computed | 0.5 | none_found_past_only | inside_outside_bar |
| si_pta_cdl | PTA CDL | proxy | registered_not_promoted | 0.5 | none_found_past_only | standalone |
| si_three_inside | Three Inside | validated | promoted_runtime_computed | 1.0 | none_found_past_only | standalone |
| si_three_inside_filtered | Three Inside Filtered | validated | registered_not_promoted | 1.0 | none_found_past_only | standalone |

## Exhaustion/divergence (3)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| pta_drawdown | Drawdown | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | standalone |
| si_rsi_div | RSI DIV | validated | promoted_runtime_computed | 0.5 | none_found_past_only | rsi_exhaustion |
| si_rsi_div_auto | RSI DIV Auto | validated | registered_not_promoted | 0.5 | none_found_past_only | rsi_exhaustion |

## Explanation-only or display-only (2)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| pta_kurtosis | Kurtosis | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | statistical_distribution |
| si_flowscope | Flowscope | blocked | near_stub_constant_output | 0.5 | none_found_past_only | standalone |

## Fibonacci/Elliott/Harmonic (4)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_ctz_gann | CTZ Gann | validated | registered_not_promoted | 0.5 | centered_pivot_confirmation | smc_structure |
| si_fib | FIB | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_har_zz | HAR ZZ | proxy | registered_not_promoted | 0.5 | zigzag_repaint | harmonic_zigzag |
| si_harmonic | Harmonic | proxy | registered_not_promoted | 0.5 | zigzag_repaint | harmonic_zigzag |

## Momentum (8)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| pta_dsp | DSP | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | standalone |
| pta_fisher_sig | Fisher SIG | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | momentum_pta_cross |
| pta_kdj | KDJ | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | momentum_pta_cross |
| pta_log_ret | LOG RET | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | statistical_distribution |
| pta_rsx | RSX | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | momentum_pta_cross |
| pta_tsi | TSI | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | momentum_pta_cross |
| si_macd_ta | Macd TA | validated | promoted_runtime_computed | 0.2 | none_found_past_only | standalone |
| si_rsi_ss | RSI SS | validated | promoted_runtime_computed | 0.5 | none_found_past_only | rsi_exhaustion |

## Pattern recognition (5)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_cdl | CDL | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_cdl_mb | CDL MB | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_curve | Curve | validated | registered_not_promoted | 0.5 | none_found_past_only | standalone |
| si_dbl | DBL | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_hs | HS | validated | promoted_runtime_computed | 0.5 | centered_pivot_confirmation | standalone |

## Reversal zone (5)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| pta_skew | Skew | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | statistical_distribution |
| pta_zscore | Zscore | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | statistical_distribution |
| si_bahai | Bahai | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_nbar | Nbar | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_rev_radar | REV Radar | validated | registered_not_promoted | 0.5 | none_found_past_only | standalone |

## Risk, stop, target and sizing (1)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_problty_grid | Problty Grid | validated | registered_not_promoted | 0.5 | future_outcome_leakage | orb_family |

## SMC/liquidity/structure (8)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_bos | BOS | validated | promoted_runtime_computed | 0.5 | library_label_shift_possible | smc_structure |
| si_choch | Choch | validated | promoted_runtime_computed | 0.5 | library_label_shift_possible | smc_structure |
| si_fvg | FVG | validated | promoted_runtime_computed | 1.0 | none_found_past_only | smc_structure |
| si_liq_intelg | LIQ Intelg | validated | promoted_runtime_computed | 0.5 | centered_pivot_confirmation | smc_structure |
| si_liquidity_entry | Liquidity Entry | validated | promoted_runtime_computed | 1.0 | centered_pivot_confirmation | smc_structure |
| si_ob | OB | validated | promoted_runtime_computed | 0.5 | none_found_past_only | smc_structure |
| si_sfb_hybrid | SFB Hybrid | validated | registered_not_promoted | 0.5 | centered_pivot_confirmation | smc_structure |
| si_sweep_inside_rr | SWEP+INSD | validated | promoted_runtime_computed | 0.5 | future_outcome_leakage | standalone |

## Support/resistance and price levels (2)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_fractal | Fractal | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_swing_str | Swing STR | validated | promoted_runtime_computed | 0.5 | centered_pivot_confirmation | smc_structure |

## Trend (20)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| pta_amat | Amat | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | ma_cross_generic |
| pta_aroon_sig | Aroon SIG | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | standalone |
| pta_ebsw | Ebsw | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | standalone |
| pta_hlc3 | Hlc3 | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | ma_cross_generic |
| pta_long_run | Long RUN | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | ma_cross_generic |
| pta_short_run | Short RUN | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | ma_cross_generic |
| pta_ttm | TTM | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | ma_cross_generic |
| pta_vortex | Vortex | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | standalone |
| si_adaptive_flow | Adaptive Flow | validated | promoted_runtime_computed | 0.5 | centered_pivot_confirmation | smc_structure |
| si_chandelier | Chandelier | proxy | registered_not_promoted | 0.5 | none_found_past_only | atr_trailing_flip |
| si_dual_ma_osc | Dual MA OSC | validated | promoted_runtime_computed | 0.25 | none_found_past_only | ma_cross_generic |
| si_fmfm300 | FMFM300 | validated | promoted_runtime_computed | 0.047619 | centered_pivot_confirmation | smc_structure |
| si_ichi_trend_osc | Ichimoku Trend Oscillator | validated | promoted_runtime_computed | 1.0 | none_found_past_only | ichimoku_pair |
| si_ichimoku | Ichimoku | validated | registered_not_promoted | 0.333333 | none_found_past_only | ichimoku_pair |
| si_impulse | Impulse | validated | promoted_runtime_computed | 0.5 | none_found_past_only | smc_structure |
| si_sar_tapy | SAR Tapy | proxy | registered_not_promoted | 0.5 | none_found_past_only | standalone |
| si_sbs | SBS | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_st_talipp | ST Talipp | validated | promoted_runtime_computed | 0.5 | none_found_past_only | atr_trailing_flip |
| si_trend_sig | Trend SIG | validated | promoted_runtime_computed | 0.5 | none_found_past_only | atr_trailing_flip |
| si_twin_range | Twin Range | validated | promoted_runtime_computed | 0.5 | none_found_past_only | ma_cross_generic |

## Trendline/curve (3)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_lrb | LRB | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_trendln | Trendln | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_zz_swing | ZZ Swing | validated | promoted_runtime_computed | 0.5 | zigzag_repaint | harmonic_zigzag |

## Volatility (5)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| pta_chop | Chop | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | volatility_regime |
| pta_entropy | Entropy | proxy | registered_probe_only | 0.5 | none_found_trailing_shift1 | statistical_distribution |
| pta_squeeze | Squeeze | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | volatility_regime |
| si_bb_break | BB Break | validated | promoted_runtime_computed | 0.5 | none_found_past_only | volatility_regime |
| si_kc_pyti | KC Pyti | proxy | registered_not_promoted | 0.5 | none_found_past_only | volatility_regime |

## Volume and participation (5)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| pta_cmf | CMF | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | standalone |
| pta_mfi_sig | MFI SIG | validated | registered_probe_only | 0.5 | none_found_trailing_shift1 | momentum_pta_cross |
| si_delta_vp | Delta VP | validated | registered_not_promoted | 0.5 | future_outcome_leakage | standalone |
| si_mp_va | MP VA | validated | promoted_runtime_computed | 0.5 | none_found_past_only | standalone |
| si_vol_exh | VOL EXH | validated | registered_not_promoted | 0.5 | none_found_past_only | standalone |

## VWAP/ORB/CPR/pivot (13)

| id | name | status | runtime | lag_w | lookahead | family |
|---|---|---|---|---|---|---|
| si_cm_strg_pivt | CM Strg Pivt | validated | promoted_runtime_computed | 0.5 | none_found_past_only | pivot_levels |
| si_cpr | CPR | validated | promoted_runtime_computed | 0.5 | none_found_past_only | pivot_levels |
| si_cpr_v4 | CPR V4 | validated | promoted_runtime_computed | 0.5 | none_found_past_only | pivot_levels |
| si_hourly_pvt | Hourly PVT | validated | promoted_runtime_computed | 0.5 | none_found_past_only | pivot_levels |
| si_hyb_opening_range_rev | HYB Opening Range REV | validated | registered_not_promoted | 0.5 | future_outcome_leakage | orb_family |
| si_hybrid_ml | Hybrid ML | validated | registered_not_promoted | 0.5 | none_found_past_only | vwap_confluence |
| si_hybrid_ml_cpr | Hybrid ML CPR | validated | registered_not_promoted | 0.5 | future_outcome_leakage | vwap_confluence |
| si_opening_range_rev | Opening Range REV | validated | registered_not_promoted | 0.5 | future_outcome_leakage | orb_family |
| si_strg_pivt | Strg Pivt | validated | promoted_runtime_computed | 0.5 | none_found_past_only | pivot_levels |
| si_vwap_bb_ml_conf | Vwap BB ML Conf | validated | promoted_runtime_computed | 0.5 | none_found_past_only | vwap_confluence |
| si_vwap_conf | Vwap Conf | validated | promoted_runtime_computed | 0.5 | none_found_past_only | vwap_confluence |
| si_vwap_super | Vwap Super | validated | promoted_runtime_computed | 0.5 | none_found_past_only | vwap_confluence |
| si_wekly_pivot | Wekly Pivot | validated | promoted_runtime_computed | 0.5 | none_found_past_only | pivot_levels |
