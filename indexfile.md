# Trade Vision — ORB / AFRE Canonical Plan Index

## Current verified Git baseline

- Repository: `onlyvictus-bit/trade-vision-app`
- Branch: `m4-d6-orchestration-redesign`
- Verified HEAD: `4819ddaee72540c1bbbe605f5411b28089333898` (`4819dda`)
- Parent: `42feaf77fb45f1f73999da6c975082d8e66c5c86` (`42feaf7`)
- Commit message: `docs: add Layer A clock/TF fit and Layer B inside-outside pattern plus 14-layer flowchart (§46)`
- Canonical plan: `docs/ORB_AFRE_CANONICAL_FUTURE_BUILD_PLAN_2026-09-10.md`
- Canonical plan blob at `4819dda`: `38fab7e95f0f00bc56d0368804f7717f24cc4941`
- Verified canonical-plan size at this revision: 102,570 bytes / 2,754 lines.
- The update from `42feaf7` to `4819dda` was a pure 104-line append to the canonical ORB/AFRE plan; no new plan file was created and no other file was changed by that commit.

## Section 46 added at this baseline

Section 46 adds:

1. **Layer A — clock/timeframe fit**: determine the appropriate OR clock/duration and confirmation timeframe from proof-backed research rather than assuming one fixed OR configuration for every stock/context.
2. **Layer B — inside/outside pattern state**: classify the post-OR market structure into explicit states such as `TREND_UP`, `TREND_DOWN`, `GAP_FILL`, or `RANGE` from closed-candle evidence.
3. **14-layer end-to-end flowchart** connecting data, context, OR construction, signal generation, pattern interpretation, trade parameters, research, ML, playbook promotion, runtime evidence, AFRE/D6 deliberation, and later outcome learning.

## 14-layer canonical flow

```text
1. RAW / PIT-SAFE CLOSED-CANDLE DATA
                         |
                         v
2. PREVIOUS COMPLETED DAILY SESSION + CURRENT MARKET CONTEXT
                         |
                         v
3. LAYER A: CLOCK / TF FIT
                         |
                         v
4. BUILD AND LOCK TODAY'S OPENING RANGE
                         |
                         v
5. SIGNAL ENGINE -> ORB_SIGNAL (closed-candle confirmation)
                         |
                         v
6. LAYER B: INSIDE/OUTSIDE -> TREND_UP / TREND_DOWN / GAP_FILL / RANGE
                         |
                         v
7. TRADE PARAMS (pattern-split entry/stop/target/no-chase/cutoff)
                         |
                         v
8. COMBINATION RESEARCH (pattern-conditioned situations)
                         |
                         v
9. ML DATASET (frozen decision-time photo + separately matured label)
                         |
                         v
10. ML ENGINE (calibrated P(win), expected R, uncertainty)
                         |
                         v
11. PLAYBOOK (clock/TF fit + pattern stats + params + ML proof, frozen)
                         |
                         v
12. MORNING RUNTIME -> ORB_EVIDENCE_PACKAGE (signal + pattern + FOR/AGAINST)
                         |
                         v
13. AFRE + D6 -> WAIT / WATCH / PAPER-CANDIDATE (D6 sole final authority)
                         |
                         v
14. AFTER THE DAY (outcome -> calibration -> challenger -> rollback if worse)
```

## Section 46 invariant

Layers A and B inherit the project safety and causality invariants:

- D2 / point-in-time causality is mandatory.
- Only closed-candle evidence can gain decision authority.
- Missing information remains missing/unknown/unavailable; it is never silently converted to neutral, safe, false, or zero.
- Identical inputs and versions must support deterministic replay.
- ORB, Layer A, Layer B, ML, AFRE subcomponents, and trade-parameter logic have zero live-trading/order-routing authority.
- Human approval remains required for paper actions.
- D6 remains the sole final-band authority unless a separately approved architecture migration changes that rule.

## Baseline rule for future work

For future ORB/AFRE work, treat commit `4819ddaee72540c1bbbe605f5411b28089333898` as the verified documentation baseline until the branch advances and is reverified. The canonical source remains `docs/ORB_AFRE_CANONICAL_FUTURE_BUILD_PLAN_2026-09-10.md`; this index is only a navigation/baseline record and must not become a competing specification.
