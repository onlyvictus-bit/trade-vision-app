# Next Build Target

Last reviewed: 2026-09-03 (rev 2)

## Latest Completed Functional Build

```text
v1.99.2 - Flow Re-Audit on Real Data + Session-Aware Quality + Compute Window
```

Primary delivered purpose:

- the full D1-D8 flow is verified end-to-end on REAL HSTRY market data
  (RELIANCE 5000 bars: D1 9/9 -> snapshot -> 8/9 receipts -> WATCH);
- data quality is session-aware: overnight/weekend/holiday closures are
  info-level, only intraday gaps are warnings (real history can now pass D1);
- snapshot indicator evidence computes on a bounded 400-bar window
  (latency guard satisfied on any snapshot size, window disclosed);
- 49/94 indicators compute at runtime; registry 86 validated / 7 proxy /
  1 blocked; PTA marker stack fixed (was silently dead v1.86-v1.98).

## Verification Snapshot

```text
Full backend regression (2026-08-26): 734 passed, 0 failed
v1.96 catalog gates: 9 passed | v1.97 timing gates: 10 passed
v1.89-v1.94 ORB suites: 36 passed | spine+orb paper suites: 74 passed
Flow re-audit baseline: scripts/flow_reaudit.py (runbook: docs/runbooks/flow-reaudit.md)
Real-run artifacts: data/orb_research/ (BEL +60.2R @ 09:15-09:20, PF 1.30)
```

## Recommended Next Work

```text
BEL prove DONE (2026-08-26): VERDICT=ELIGIBLE, proof ab7b3163,
holdout PF 1.271 (+12.08R / 126 unseen trades), walk-forward 4/4 folds passed.
BEL PROMOTED (2026-08-26): playbook a1c78a28 active (BEL 5m, breakout,
09:15-09:20, RR 3.0, close confirmation); verified matched by the v1.92
guidance on real bars (orb_ticket present).

Candidate queue (in value order):

1. Daily ORB timing ritual on TrendForge picks (operational, no build)
   - paste symbols or use symbols_source=trendforge_latest
2. Accumulate 30 completed paper outcomes -> PERSISTED_INDICATOR_MEMORY
   receipt turns completed on its own (operational, no build)
3. v1.95 (still proposed, not built) - Active Evidence Loading And API Fast-Lane
4. pta_entropy latency fix (14.5s scipy rolling histogram) -> then validate
5. Latency optimization for si_curve / si_rev_radar / si_ctz_gann / si_sfb_hybrid
   -> then promote (runtime 49 -> 53)
6. 6 remaining self-proxy indicators: external-path hardening or trigger samples
7. v2.00 ORB Context-Native Upgrade (PROPOSED 2026-08-31; v2.1 2026-09-01;
   v2.2 2026-09-02 first Kimi review; v2.3 2026-09-02 second Kimi submission;
   v2.4 2026-09-03 third Kimi submission (consolidated): STOP-01 + REENTRY-01
   + ENTRY-04 + top-10 now TRIPLE-confirmed, 10 new rules (CHASE-01,
   ORPDC-01, EXIT-07, IDX-02...), VIX 5-band + ORW 1.0-skip majority priors -
   plan only, awaiting milestone approval, no code yet)
   - gap bias-lock (incl. large-gap trap protocol) + CPR wide/narrow filter +
     PDH/PDL breakout family + execution realism (1R-half/trail exits,
     capital-risk size_hint, daily circuit breaker) + raised proof thresholds
   - plan: docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md (milestones M1-M6 + §7/§8/
     §9/§10 addenda: policy split, migration, staged grid, review mappings)
   - rule spec: docs/plans/ORB_STRATEGY_MEMORANDUM.md v2.4 (rule IDs
     GAP/TRAP/CPR/ZONE/EXIT/CTX + EVENT/UNIV/IDX/VIX/DERIV/EXP/AFT/VWAP
     layers + §7A.7/§7A.9 calibration register; worked examples 1A/1B/2/3/4)
   - verification: docs/plans/ORB_V2_JUDGE_FINDINGS.md (five passes) +
     docs/plans/ORB_V201_VERIFIED_ANSWER.md (three submissions: 1 wrong/
     13 missed/11 right · 4 corrections/11 misses/13 conflicts · 0 contra/
     10 new/6 triple-confirmed)
   - reviews archived verbatim (all four submissions, byte-exact):
     docs/plans/ORB_V201_PRECODE_REVIEW_KIMI.md (sub 1, retro)
     + ORB_V201_NSE_REVIEW_KIMI.md (sub 2) +
     ORB_V201B_NSE_REVIEW_KIMI_PART2.md (sub 3) +
     ORB_V201C_NSE_REVIEW_KIMI_PART3.md (sub 4)
   - cheapest pre-test before any code: pre-registered (H1/H2/H3 incl.
     CPR-vs-close-location redundancy), per-layer go/no-go
```

## Standing Operational Ritual (no build required)

```text
Daily: send TrendForge picks -> ORB timing run (60-90s per stock, 5m)
       -> per-stock best-window table -> optionally 1m refine top-20
       per-stock full check: python scripts/stock_verify.py SYMBOL
Weekly: review data/orb_research/ leaderboards; promote nothing without
        walk-forward proof + explicit approval
Anytime flow looks wrong: python scripts/flow_reaudit.py (runbook first)
```
