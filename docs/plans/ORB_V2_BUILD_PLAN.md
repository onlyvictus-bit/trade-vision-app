# ORB v2 Build Plan (v2.01 track) — approved design, staged 4→2→1

> Status: APPROVED DESIGN, not started. Council verdict: staged candidate 2,
> P ≈ 0.72 (CI 0.60–0.83). Parent spec: ORB_STRATEGY_MEMORANDUM.md v2.4.
> Plan: ORB_CONTEXT_NATIVE_PLAN_V2.md (§11–§13). Rule: no milestone starts
> without its gate green; every milestone reversible via its config key.

## Council verdict (summary)

- #1 Full M1–M6 as specified — rejected as first move (V1-NO_GO layers would ship dead; feed-less rules rot).
- #2 SLICE-SCOPED BUILD (chosen) — M1 foundation, then only V1-unrejected slices as filters first, core gates only on OOS proof, feeds only for ledger-earned rules.
- #3 Feeds first — rejected (months of plumbing, feed rot).
- Weak link: whether LARGE-gap/NARROW+RVOL slices show edge (V1-slice re-run answers before any engine code).

## M1: context foundation (v2.01)

Files: `orb/context.py` (extend) · `models.py` (+`OrbConfluenceContext`,
`OrbBuildRequest.previous_day_*`, `gap_mode`/`cpr_filter_mode`/`stop_mode`
keys defaulting to current behavior) · `state.py` TV-V202 rows ·
`tests/test_orb_v201_context.py` (new).

Work: session-VWAP · previous_day explicit fields (PIT strictly-prior session;
dual-source mismatch = hard error CTX-04) · per-day precompute helper (never
per-combo) · leak-proof test (no D−1 bar timestamp ≥ any D bar timestamp) ·
causal whitelist v0.15 · live path wiring + `context_unknown` fail-open.

Verify: new tests + full suite green + `flow_reaudit.py` clean.
Rollback: `context_enabled` flag (default off) — zero behavior change when off.

## M2: gap gates (ONLY if V1-slice passes for LARGE-gap)

`core.py::_gap_gates`, `gap_mode: off | bias_lock | full` (default off),
S5 slot accounting implemented HERE (not M6), arbiter wiring decision
(optional context fields vs regime-score mapping), tests per
GAP-01..04 / TRAP-01 / TRAP-02 / VETO-01 rule ID.

## M3: CPR filter (ONLY if V1-slice passes for NARROW)

`cpr_filter_mode: off | narrow_trend | full` (default off), NARROW-first
precedence partition, targets capped 1.5R on WIDE.

## M4: PDH/PDL family + E3 (dangerous — shadow first)

`pdh_pdl_breakout` family, `_backtest_day` honors the signal's own stop,
BEL shadow-run parallel proof over the identical request, switch the active
playbook only on a passing shadow proof, `metric_universe` stamps
(pre/post-e3-fix), timing rows recomputed, S5/S6 accounting, stop-unification
regression test.

## M5: exits + sizing

`exit_plan` (full / split-1R-half / trail), split-exit stop-first tie-break,
capital-risk `size_hint`, slippage overrides, daily breaker inside the
explicit-approval paper flow (fail-open + loud tag when ledger absent),
`stop_mode` + backtest↔live parity test.

## M6: regime + hardening

OR-width-vs-ATR filter, REENTRY-01 state machine, thresholds raised
(overall ≥30, per-regime ≥10, promotion bar 60 OOS), staged grid (Stage 1:
context modes over best v1.97 configs; Stage 2: joint over survivors),
AFT-01 separate track with its own folds — never merged into morning stats.

## Verification after EVERY milestone

New tests green + full suite green + `flow_reaudit.py` clean + catalog regen
if registry touched + docs: IMPLEMENTATION_STATUS, TEST_ID_INDEX,
ARCHITECTURE F2, graph JSON (zero dangling), FILE_DOCUMENT_INDEX.
