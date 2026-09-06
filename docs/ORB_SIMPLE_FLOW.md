# ORB Simple Flow Map — read this first

> Everything the system does, in 9 boxes. Each box: plain English, the exact
> Python file, the detail doc, and whether it is built. (The big design docs
> are linked, not repeated.)

```text
┌─ 1. DATA IN ──────────────────────────────┐
│ Read stock price files (CSV) → candles    │  ✅ BUILT
└──────────────┬────────────────────────────┘
               ▼
┌─ 2. DATA CHECK ───────────────────────────┐
│ 9 safety checks; bad data → WAIT          │  ✅ BUILT
└──────────────┬────────────────────────────┘
               ▼
┌─ 3. STUDY MARKET ─────────────────────────┐
│ 49 indicators + ORB + levels + trend      │  🟡 PARTIAL (49/94 live)
└──────────────┬────────────────────────────┘
               ▼
┌─ 4. CHECK MEMORY ─────────────────────────┐
│ Seen before? What happened last time?     │  🟡 PARTIAL (needs 30 outcomes)
└──────────────┬────────────────────────────┘
               ▼
┌─ 5. ASK OTHER BRAINS ─────────────────────┐
│ Kronos forecast + Gemini/Grok review      │  ✅ BUILT (advice only)
└──────────────┬────────────────────────────┘
               ▼
┌─ 6. FIND DISAGREEMENTS ───────────────────┐
│ Votes conflict? → reduce confidence       │  ✅ BUILT
└──────────────┬────────────────────────────┘
               ▼
┌─ 7. SAFETY CHECK ─────────────────────────┐
│ Entry/stop/target sensible? Enough proof? │  ✅ BUILT
└──────────────┬────────────────────────────┘
               ▼
┌─ 8. SHOW RESULT ──────────────────────────┐
│ WAIT / WATCH / PAPER-CANDIDATE on screen  │  ✅ BUILT
└──────────────┬────────────────────────────┘
               ▼
┌─ 9. HUMAN DECIDES ────────────────────────┐
│ You approve → paper trade recorded        │  ✅ BUILT (needs usage)
└───────────────────────────────────────────┘
```

## Box-by-box: Python file + detail doc + status

| # | Box (plain English) | Python file (exact) | Detail doc | Status |
|---|---|---|---|---|
| 1 | Load price files | `apps/api/app/orb/hstry_csv.py` → `load_hstry_series` | `docs/plans/ORB_TIMING_RESEARCH_V197.md` | ✅ 90 stocks × 7 timeframes load |
| 1 | Import any CSV | `apps/api/app/main.py` → `behavior_import_ohlcv` (:1105) | `docs/API_ENDPOINT_INDEX.md` | ✅ tested |
| 2 | 9 safety checks | `apps/api/app/behavior/paper_guidance_spine.py` → `run_paper_guidance_p1` (:57) | `docs/plans/FINAL_REQUIRED_FLOW.md` (D1) | ✅ 9/9 pass on real data |
| 2 | Quality scan (nights/weekends OK) | `apps/api/app/behavior/data_quality.py` → `scan_data_quality` | `docs/runbooks/flow-reaudit.md` | ✅ session-aware |
| 2 | Freeze data + fingerprint it | same spine file (D2 snapshot + hash) | `FINAL_REQUIRED_FLOW.md` (D2) | ✅ |
| 3 | Spot one ORB trade today | `apps/api/app/orb/core.py` → `build_orb_candidate` | `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` | ✅ breakout/reversal |
| 3 | Test 1000s of settings on history | `apps/api/app/orb/discovery.py` → `run_orb_discovery` | same as above | ✅ 72 combos/stock |
| 3 | Exam: luck or real edge? | `apps/api/app/orb/proof.py` → `run_orb_proof` | same as above | ✅ 4 walk-forward folds |
| 3 | Which opening time wins? | `apps/api/app/orb/timing_research.py` → `run_timing_research` | `docs/plans/ORB_TIMING_RESEARCH_V197.md` | ✅ 09:20/30/35/40 ranked |
| 3 | Classify the open (gap/CPR/zone) | `apps/api/app/orb/context.py` → `classify_opening` | `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md` §11 | ✅ standalone (not yet wired into core) |
| 3 | 49 indicators compute | `apps/api/app/behavior/real_indicator_adapter.py` | `docs/INDICATOR_INTELLIGENCE_CATALOG.md` | 🟡 49/94 live |
| 3 | Trend/structure/risk engines | `apps/api/app/behavior/` (v1.70–75 modules) | `ARCHITECTURE.md` F2 table | ✅ |
| 3 | Multi-timeframe check | `timeframe_feature_builder.py` | `ARCHITECTURE.md` | ✅ closed-bar only |
| 4 | Remember past outcomes | `behavior/indicator_reliability_memory.py`, `orb_paper_feedback.py` | `ARCHITECTURE.md` | 🟡 works; needs 30 outcomes to mature |
| 4 | Find similar past days | `behavior/nine_candle_hybrid.py` (real bars since v1.98) | `ARCHITECTURE.md` | ✅ real data now |
| 5 | Kronos forecast (advisor) | `apps/kronos-service/` (isolated) | `ARCHITECTURE.md` | ✅ prior-only, cannot override |
| 5 | Gemini/Grok review (advisors) | `behavior/gemini_provider.py`, `behavior/grok_provider.py` | `ARCHITECTURE.md` | ✅ display-only |
| 6 | Final judge of votes | `behavior/final_confluence_arbiter.py` | `FINAL_REQUIRED_FLOW.md` (D6) | ✅ reduce-only boss |
| 7 | Entry/stop/target sanity | `paper_guidance_spine.py` safety gate + `behavior/orb_guidance.py` | `FINAL_REQUIRED_FLOW.md` (D7) | ✅ |
| 8 | Show ticket on screen | `apps/web/src/App.tsx` (74 Jarvis panels) + `behavior/jarvis_decision_room.py` | `docs/FRONTEND_PANEL_MAP.md` | ✅ |
| 8 | Proven BEL recipe shown | playbook `a1c78a28` via `behavior/orb_guidance.py` | `data/orb_research/v197_m4_analysis.md` | ✅ live |
| 9 | Approve → record paper trade | `POST /api/v1/paper-guidance/*` + `behavior/simulated_paper_ledger.py` | `FINAL_REQUIRED_FLOW.md` (D8) | ✅ mechanism; needs your usage |

## How the boxes connect (function call chain)

```text
load_hstry_series()            [box 1: data in]
  → run_paper_guidance_p1()    [box 2: D1 gate → D2 snapshot]
    → build_orb_candidate()    [box 3: spot today's setup]
    → compute_real_indicator_outputs_with_telemetry()  [box 3: indicators]
    → reliability memory reads [box 4: what worked before]
    → kronos / gemini / grok   [box 5: advisors]
    → final_confluence_arbiter [box 6: judge]
    → safety gate + entry plan [box 7: sanity]
    → Jarvis ticket on screen  [box 8: WAIT/WATCH/PAPER-CANDIDATE]
    → human approves → ledger [box 9: recorded, outcomes feed box 4]
```

## Needed next (from the v2 plan, in order)

| # | Missing piece | Spec doc | Size |
|---|---|---|---|
| 1 | M0 data inventory + V1 gap/CPR pre-test | `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md` §11/§13 | research task, no engine change |
| 2 | Wire `orb/context.py` into `orb/core.py` (gap/CPR gates in the live engine) | same plan, M1 | 1 module + models + tests |
| 3 | PDH/PDL breakout family + fix reversal stop math (E3) + re-prove BEL | same plan, M4 | engine + migration |
| 4 | Exit simulator (book half at 1R, trails) + capital-risk sizing + daily loss cap | same plan, M5 | engine |
| 5 | External feeds (VIX, GIFT, OI, calendars) — only for rules the ledger earns | same plan, §12 G-rules | data plumbing, last |
| 6 | 30 paper outcomes (your usage, not code) | `docs/NEXT_BUILD_TARGET.md` ritual | operational |
