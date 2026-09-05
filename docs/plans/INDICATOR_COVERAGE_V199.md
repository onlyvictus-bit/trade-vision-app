# v1.99 — Complete Indicator Runtime Coverage (Waves 1b + 2 + 3)

> **Status:** Complete 2026-08-25. Full backend regression 734 passed / 0 failed.
> **Parent:** `TRADE_VISION_FULL_INDICATOR_MEMORY_PLAN.md` (§5 invariant + §18 acceptance) and the Wave roadmap from `INDICATOR_INTELLIGENCE_CATALOG.md`.
> **Outcome:** runtime coverage **22 → 49 of 94**; registry **86 validated / 7 proxy / 1 blocked**; the 6 future-leak indicators remain permanently explanation-only.

## What was done (evidence-based, audit-first)

### Wave 1b — 17 external-dependency promotions
Audit: each candidate computed via the real adapter on RELIANCE 5m ×500 HSTRY bars.
17 computed non-empty (`si_cdl, si_cdl_mb, si_dbl, si_fib, si_fractal, si_fvg, si_impulse, si_macd_ta, si_mk_inside, si_ob, si_rsi_ss, si_sbs, si_st_talipp, si_trend_sig, si_twin_range, si_vwap_bb_ml_conf, si_vwap_super`).
Excluded: `si_curve` (15.8 s latency, slow_blocked), `si_rev_radar` (1.2 s, slow_blocked).

### Wave 2 — 10 repaint-risk validated promotions (evidence-only)
`si_adaptive_flow, si_bos, si_choch, si_hs, si_liq_intelg, si_liquidity_entry, si_sfp, si_swing_break, si_swing_str, si_zz_swing` — all compute non-empty on real bars; `usable_for_probability` stays False (centered-pivot disclosure). Excluded: `si_ctz_gann`, `si_sfb_hybrid` (slow_blocked on real bars), and the 3 leak-classified ORR/CPR learners (never promotable).

### Wave 3 — proxy audits
- **Defect found and fixed**: the vendored `research/signals/__init__.py` imported six modules that were never vendored (`trend`, `momentum`, ...), raising an uncaught ImportError that **silently disabled all 23 PTA markers since v1.86** (every probe "passed" because empty lists are not errors). Fixed with guarded imports; **20/23 PTA markers now emit on real bars** (kdj 76, ebsw 170, fisher 83 events on RELIANCE ×500).
- **PTA statuses**: 22 → `validated` (wrapper audited: shift(1) crossings, 20-bar warmup, no centered windows); `pta_entropy` stays `proxy` (14.5 s scipy rolling-histogram latency exceeds runtime budget).
- **Self proxies**: 5 of 12 emit on real bars with past-only code (`si_dark_cloud, si_hybrid_ml, si_ichimoku, si_three_inside_filtered, si_vol_exh`) → `validated` via `REAL_DATA_VERIFIED_EMPTY_SAMPLE` (sample-empty label kept factual). 6 remain `proxy` (empty everywhere). `si_flowscope` → `blocked` (constant-output stub).

## Final state

| Measure | Value |
|---|---|
| Runtime promoted | **49 / 94** |
| Registry | 86 validated · 7 proxy · 1 blocked |
| Permanently explanation-only | 6 future-leak indicators |
| Verification | full backend 734/0 · catalog gates 9/9 · timing gates 10/10 · icache locks updated to 49 |

## Remaining (post-100%-of-safe-coverage)

- `pta_entropy` latency fix (vectorize rolling entropy) → then validate.
- `si_curve` / `si_rev_radar` / `si_ctz_gann` / `si_sfb_hybrid` latency optimization → then promote.
- 6 still-proxy self indicators: need external-module path hardening or sample data that triggers them.

*Safety unchanged: research_only everywhere; no probability authority added; live trading blocked.*
