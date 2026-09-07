# Trade Vision Production Campaign

Last updated: 2026-09-07

## Current Phase

`v1.87-v1.94` paper-guidance + ORB campaign completed and verified. ORB research
continued through `v2.02-derivatives` (coded + finished, research-only):

- v1.96 Indicator Intelligence Catalog (94 contracts, 9 gates)
- v1.97 ORB Timing Research (09:20/30/35/40 windows, 10 gates; BEL 09:15-09:20
  ELIGIBLE, proof ab7b3163, playbook a1c78a28 ACTIVE)
- v2.01 ORB opening classifier `orb/context.py` (standalone, 8 gates, not wired
  into core)
- v2.02-derivatives ORB Derivatives Intelligence (OFF-by-default dormant,
  22/22 gates, ATR parity DONE)

Tip authority: `docs/IMPLEMENTATION_STATUS.md` (939 passed 2026-09-07 — 914 baseline
+ 26 repair gates; vendor half parked for G0 capture). v1.94
sections below are frozen history.

## Sequence

1. v1.87 D1/D2 and contract — completed.
2. v1.88 D3-D6 snapshot-bound orchestration and sole final-band authority - completed.
3. v1.89 ORB-0/1 contracts, NSE session lock, and strategy builders - completed.
4. v1.90 ORB-2 offline discovery and asynchronous job APIs - completed.
5. v1.91 ORB-3 OOS/WF proof and playbook promotion - completed.
6. v1.92 ORB-4/5 primary Jarvis setup action and guidance bridge - completed.
7. v1.93 human-approved simulated paper record and traceability - completed.
8. v1.94 outcome feedback, lifecycle evidence, and production hardening - completed.

## Campaign Risks

- Existing decision vocabulary is inconsistent.
- Existing shared snapshot candle-start filtering was fixed in v1.87.
- Local RELIANCE and some vendored indicator paths are hardcoded.
- Real downloaded MTF sources are not universally wired into Jarvis.
- Existing tests are extensive but concentrated in one large module.
- ORB must remain the primary setup candidate rather than replacing the D6
  arbiter or human approval.

## Current Evidence

- focused v1.88-v1.93 campaign: 85 passed;
- focused v1.94 lifecycle/hardening: 32 passed;
- focused v1.92-v1.94 UI/ledger/lifecycle: 54 passed;
- full backend: 715 passed;
- frontend typecheck/build: passed;
- browser RELIANCE ORB: WATCH/NO_PLAYBOOK with record and lifecycle disabled,
  MTF ALIGNED, and store integrity PASS;
- no Paper Guidance execution imports or live/broker route;
- frontend typecheck/build and desktop/mobile browser acceptance passed;
- docs, graph, pointers, API index, and test index refreshed.
