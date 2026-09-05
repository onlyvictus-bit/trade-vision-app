# Indicator Group and Use Map (generated core)

Vote rule: correlated family members share reduced weight (no independent full votes).

## Trend - 27 indicators

- pta_amat (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_aroon_sig (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_ebsw (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_hlc3 (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_long_run (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_short_run (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_ttm (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_vortex (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_adaptive_flow (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_bos (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_chandelier (PRIMARY, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_choch (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_ctz_gann (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_dual_ma_osc (PRIMARY, validated, lag_w=0.25): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_fmfm300 (PRIMARY, validated, lag_w=0.047619): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_ichi_trend_osc (PRIMARY, validated, lag_w=1.0): use=['explanation']; wait=['conflict_check']
- si_ichimoku (PRIMARY, validated, lag_w=0.333333): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_impulse (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_inside_candle_strategy (secondary, validated, lag_w=0.5): use=['explanation', 'early_context']; wait=['conflict_check']
- si_macd_ta (secondary, validated, lag_w=0.2): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_nbar (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sar_tapy (PRIMARY, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sbs (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_st_talipp (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_three_inside_filtered (secondary, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- si_trend_sig (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_twin_range (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: atr_trailing_flip, ichimoku_pair, ma_cross_generic, smc_structure

## Momentum - 13 indicators

- pta_dsp (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_fisher_sig (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_kdj (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_log_ret (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_mfi_sig (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_rsx (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_tsi (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_dual_ma_osc (secondary, validated, lag_w=0.25): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_ichi_trend_osc (secondary, validated, lag_w=1.0): use=['explanation']; wait=['conflict_check']
- si_macd_ta (PRIMARY, validated, lag_w=0.2): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_rsi_div (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_rsi_div_auto (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_rsi_ss (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- vote families touching this group: ichimoku_pair, ma_cross_generic, momentum_pta_cross, rsi_exhaustion, statistical_distribution

## Volatility - 5 indicators

- pta_chop (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- pta_entropy (PRIMARY, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_squeeze (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_bb_break (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_kc_pyti (PRIMARY, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- vote families touching this group: statistical_distribution, volatility_regime

## Volume and participation - 5 indicators

- pta_cmf (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_mfi_sig (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_delta_vp (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_mp_va (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_vol_exh (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: momentum_pta_cross

## Support/resistance and price levels - 18 indicators

- si_cm_strg_pivt (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_cpr (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_cpr_v4 (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_delta_vp (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_fib (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_fmfm300 (secondary, validated, lag_w=0.047619): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_fractal (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hourly_pvt (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hybrid_ml_cpr (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_inside_out (secondary, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- si_mp_va (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_ob (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sfp (secondary, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_strg_pivt (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_swing_break (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_swing_str (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_vwap_bb_ml_conf (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_wekly_pivot (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- vote families touching this group: inside_outside_bar, pivot_levels, smc_structure, vwap_confluence

## Reversal zone - 20 indicators

- pta_skew (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_zscore (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_bahai (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_curve (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_dark_cloud (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_dbl (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_har_zz (secondary, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_harmonic (secondary, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_hs (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hyb_opening_range_rev (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hybrid_ml (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_lrb (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_nbar (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_opening_range_rev (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_outside_rev (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_rev_radar (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_three_inside (secondary, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- si_three_inside_filtered (secondary, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- si_vwap_super (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_zz_swing (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: harmonic_zigzag, inside_outside_bar, orb_family, statistical_distribution, vwap_confluence

## Confirmation - 6 indicators

- pta_hlc3 (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_long_run (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_short_run (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_rev_radar (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_vwap_bb_ml_conf (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_vwap_conf (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- vote families touching this group: ma_cross_generic, vwap_confluence

## Pattern recognition - 7 indicators

- si_cdl (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_cdl_mb (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_curve (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_dbl (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_fractal (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hs (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_pta_cdl (secondary, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check']

## Candle structure - 12 indicators

- si_cdl (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_cdl_mb (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_dark_cloud (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_inside_candle_strategy (PRIMARY, validated, lag_w=0.5): use=['explanation', 'early_context']; wait=['conflict_check']
- si_inside_out (PRIMARY, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- si_mk_inside (PRIMARY, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- si_outside_rev (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_pta_cdl (PRIMARY, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sfb_hybrid (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sweep_inside_rr (secondary, validated, lag_w=0.5): use=['explanation', 'early_context']; wait=['conflict_check']
- si_three_inside (PRIMARY, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- si_three_inside_filtered (PRIMARY, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check']
- vote families touching this group: inside_outside_bar, smc_structure

## Breakout/fakeout/trap - 8 indicators

- si_bb_break (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_fvg (secondary, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_inside_candle_strategy (secondary, validated, lag_w=0.5): use=['explanation', 'early_context']; wait=['conflict_check']
- si_liq_intelg (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_liquidity_entry (secondary, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_sfp (PRIMARY, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_swing_break (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_trendln (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: smc_structure, volatility_regime

## Exhaustion/divergence - 5 indicators

- pta_drawdown (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_rsi_div (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_rsi_div_auto (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_rsi_ss (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_vol_exh (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: rsi_exhaustion

## VWAP/ORB/CPR/pivot - 14 indicators

- si_cm_strg_pivt (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_cpr (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_cpr_v4 (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_hourly_pvt (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hyb_opening_range_rev (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hybrid_ml (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_hybrid_ml_cpr (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_opening_range_rev (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_problty_grid (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_strg_pivt (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_vwap_bb_ml_conf (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_vwap_conf (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_vwap_super (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_wekly_pivot (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- vote families touching this group: orb_family, pivot_levels, vwap_confluence

## Trendline/curve - 3 indicators

- si_lrb (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_trendln (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_zz_swing (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: harmonic_zigzag

## Fibonacci/Elliott/Harmonic - 4 indicators

- si_ctz_gann (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_fib (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_har_zz (PRIMARY, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- si_harmonic (PRIMARY, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'zone_rejection_warning']
- vote families touching this group: harmonic_zigzag, smc_structure

## SMC/liquidity/structure - 12 indicators

- si_adaptive_flow (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_bos (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_choch (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_fmfm300 (secondary, validated, lag_w=0.047619): use=['explanation']; wait=['conflict_check', 'late_signal_warning']
- si_fvg (PRIMARY, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_impulse (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_liq_intelg (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_liquidity_entry (PRIMARY, validated, lag_w=1.0): use=['explanation', 'early_context']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_ob (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sfb_hybrid (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sweep_inside_rr (PRIMARY, validated, lag_w=0.5): use=['explanation', 'early_context']; wait=['conflict_check']
- si_swing_str (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: smc_structure

## Risk, stop, target and sizing - 5 indicators

- pta_drawdown (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_chandelier (secondary, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_liq_intelg (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- si_problty_grid (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_sweep_inside_rr (secondary, validated, lag_w=0.5): use=['explanation', 'early_context']; wait=['conflict_check']
- vote families touching this group: atr_trailing_flip, orb_family, smc_structure

## Explanation-only or display-only - 6 indicators

- pta_chop (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check', 'fakeout_or_chop_warning']
- pta_dsp (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_ebsw (secondary, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_entropy (secondary, proxy, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- pta_kurtosis (PRIMARY, validated, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- si_flowscope (PRIMARY, blocked, lag_w=0.5): use=['explanation']; wait=['conflict_check']
- vote families touching this group: statistical_distribution, volatility_regime
