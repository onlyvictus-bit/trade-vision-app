# ORB Context-Native Upgrade Plan V2 (Gap + CPR + PDH/PDL + Execution Realism)

> **Status:** PROPOSED — awaiting user approval of milestones M0–M6. Not built.
> **v2.01-track amendment (2026-09-04, build audit):** milestone versions renumbered (v1.98–v2.00 collided with shipped work: v1.98 real 9C candles, v1.99 indicator coverage + BEL) — see §11. M0 added (data inventory + V1 pre-test + BEL decision). Adoption staged 4→2→1.
> **Date:** 2026-08-31 · **v2.1 addendum (2026-09-01):** external pre-code review (Kimi) integrated — see §7; **v2.2 addendum (2026-09-02):** second external review (NSE market structure) integrated — see §8; **v2.3 addendum (2026-09-02):** second Kimi submission (Task 3/4 continuation) integrated — see §9. Rule spec is `ORB_STRATEGY_MEMORANDUM.md` **v2.3** (rule IDs incl. EVENT/UNIV/IDX/VIX/DERIV/EXP/AFT layers + §7A.7 calibration register).
> **Companion docs:**
> - Rule-level trade spec (entry/stop/target, worked examples): `docs/plans/ORB_STRATEGY_MEMORANDUM.md` (v2.3)
> - Adversarial verification (four passes): `docs/plans/ORB_V2_JUDGE_FINDINGS.md` · verified answers: `docs/plans/ORB_V201_VERIFIED_ANSWER.md` · verbatim archives: `docs/plans/ORB_V201_NSE_REVIEW_KIMI.md` + `docs/plans/ORB_V201B_NSE_REVIEW_KIMI_PART2.md`
> - Prior ORB plans: `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` (v1.90 lab), `docs/plans/ORB_TIMING_RESEARCH_V197.md` (v1.97)
> **Version targets:** orb-core v2.01 (context + gap + CPR), v2.02 (PDH/PDL family + realism), v2.03 (regime + proof hardening)
> **Hard boundary unchanged:** research-only. Every new output stays `research_only=true / trade_allowed=false / live_trading_blocked=true` (`models.py` Literal enforcement). No order routing is added by this plan.

---

## 1. Where the code stands (evidence, verified 2026-08-31)

| Capability | Today | Gap |
|---|---|---|
| ORB core signal | `apps/api/app/orb/core.py` v1.89 — breakout/reversal, volume+VWAP confirm, first-signal-per-day | VWAP is range-VWAP only (not session VWAP), no gap/CPR/PDH/PDL awareness, no re-entry, no partial booking |
| Gap up/down | `apps/api/app/behavior/context_engines.py:101` `analyze_gap_context` — gap %, `gap_type` (flat <0.1%, large ≥ max(1.0%, 1.4×ATR%)), fill probability, trap risk | **Veto-only at guidance layer**; `build_orb_candidate` / discovery / proof never see it; not a strategy input |
| CPR | `context_engines.py:284` `_calculate_cpr` (pivot=(PDH+PDL+PDC)/3, BC=(PDH+PDL)/2, TC=pivot+(pivot−BC), ordered TC<BC) | **No width classification (wide/narrow) anywhere in the repo**; veto-only |
| PDH/PDL | behavior flags `breaking_pdh` / `rejecting_pdh` / `reclaiming_pdl` (`context_engines.py:346-368`) | No **PDH/PDL-breakout strategy family** in the engine |
| Causal whitelist | `behavior/causal_whitelist.py` v0.14 — already allows `previous_day_high`, `previous_day_low`, `cpr`, `pivot`, `orb_high`, `orb_low` | New features (`gap_pct`, `cpr_width`, `cpr_width_atr`, `pdh_break`, …) must be registered (bump to v0.15); field names must never collide with `FORBIDDEN_FIELDS` (`current_day_*`, `full_day_*`, `future_*`) |
| Discovery/proof | `orb/discovery.py` v1.90, `orb/proof.py` v1.91 | Rank combos on a **context-blind world** → playbooks can be promoted on trades the guidance layer would have banned |

## 2. Design decision (deep-plan council, condensed)

**Three candidate mechanisms for wiring context into ORB:**

| # | Approach | Mechanism | Kill risk | P(success) |
|---|---|---|---|---|
| 1 | Guidance-layer filters only | Keep core blind; veto gap/CPR at `orb_guidance.py` | Cheapest, but **discovery/proof stay context-blind** — playbooks get promoted on data that includes trades the filter would have banned. Fake proof. | ~45% |
| 2 | **Context-native core (RECOMMENDED)** | Add previous-day context as a first-class input to `OrbBuildRequest`; core computes gap/CPR/PDH-PDL from bars itself; add `pdh_pdl_breakout` as a new strategy family | Grid explosion in discovery; must guard PIT on prev-day data | ~78% (after v2 corrections) |
| 3 | Separate meta-strategy engine | New parallel engine for PDH/PDL + gap strategies alongside ORB | Duplicates the whole proof/playbook stack; two sources of truth to maintain | ~50% |

**RECOMMENDATION:** Candidate 2 — one PIT-safe core that knows the context, so every downstream layer (discovery, proof, timing research, playbooks, guidance) inherits it for free.

**CONFIDENCE:** P(success) ≈ 78% (CI 65–87%), from independent evidence families: code verification (modules and formulas already exist to reuse), domain fit (gap-day and CPR-width ORB rules are established practice), forecaster base rate on strategy-filter upgrades.

**WEAK LINK:** whether gap/CPR/PDH-PDL filters actually add edge on our symbols. Cheapest test (do BEFORE engine code, pre-registered per V1): run existing discovery on ~1 year of 5m data for 3–5 liquid symbols and label each trade offline (pandas notebook) with gap type and CPR width. **Pre-register before looking:** H1 narrow>wide for breakouts; H2 gap-aligned>counter-gap; H3 redundancy — CPR-class vs raw close-location-in-range tercile (memo rule CPR-04: CPRW = (2/3)|PDC − BC|, so CPR width may carry no information beyond close location; if H3 shows equivalence, keep the cheaper feature and cut the other). Min cell n ≥ 30; Mann-Whitney + effect size with CI (R-distributions are skewed — no t-tests on means); Holm correction across cells; report base rates (a zone covering 4% of days barely matters); state the decision rule including the reverse outcome (if WIDE beats NARROW, flip or die — pick now). Go/no-go per layer (gap, CPR, PDH/PDL separately, not jointly).

## 3. Milestones (v2 — judge corrections already integrated)

Corrections from the judge pass are marked **[J]**; realtime-flow items marked **[RT]**. Full findings in `ORB_V2_JUDGE_FINDINGS.md`.

### M1 — Context-native core foundation (v2.01) — dependency for everything

**What:** A new `OrbConfluenceContext` computed inside the ORB engine: previous session High/Low/Close, gap % and class, CPR (pivot/BC/TC/width/width_atr/class), PDH/PDL, session VWAP, ATR(14 daily).

**Where:**
- `apps/api/app/orb/context.py` — **NEW FILE**: gap/CPR/PDH-PDL/VWAP/ATR computation, PIT-guarded. Port `_calculate_cpr`, `_gap_type`, `_gap_fill_probability`, `_gap_trap_risk` logic from `context_engines.py` so the core does not depend on the behavior layer (behavior layer later refactors to call this module — single source of truth).
- `apps/api/app/models.py` — new `OrbConfluenceContext` model; `OrbBuildRequest` gains explicit optional `previous_day` fields (`previous_day_high/low/close`, PIT-validated: must come from a session strictly before the current one).
- `apps/api/app/orb/core.py` — `build_orb_candidate` computes context before `_opening_range`/`_signal_candidate`; result carries `context` + new gate `ORB-006 "Previous-day data is from a prior session"`.

**How (formulas, reuse repo constants):**
- Gap: `gap_pct = (today_open − prev_close) / prev_close × 100`; class = repo's own `_gap_type`: FLAT < 0.1% · GAP_UP/GAP_DOWN · LARGE ≥ max(1.0%, 1.4 × ATR% of prev close). **[J-E1]** Do NOT invent a different threshold (v1 plan wrongly said 0.5×ATR); core and guidance must share one classifier or they will contradict each other on the same day.
- CPR: pivot=(PDH+PDL+PDC)/3, BC=(PDH+PDL)/2, TC=pivot+(pivot−BC); width=BC−TC; `width_pct` = width/close×100; `width_atr` = width/ATR(14 daily). Class: NARROW if width_atr < 0.5 or width_pct < 0.25 · WIDE if width_atr > 1.0 or width_pct > 0.6 · NORMAL between. Thresholds are config keys (discoverable), never hardcoded forever.
- Session VWAP: running VWAP from session open — **replaces the range-VWAP check in `_signal_candidate`** (fixes audit gap).

**PIT rule (the weak link):** previous-day values must come only from bars strictly before the current session date. In `orb/proof.py`, `_series_for_dates` slices bars **by date** — the day before the first holdout day would be dropped, silently corrupting every gap/CPR/PDH/PDL feature. Fix: compute/store per-date prev-day aggregates from the **full** series *before* subsetting, and add a leak-proof test (no D−1 bar timestamp ≥ any D bar timestamp is ever used).

**[RT] Realtime/live-path flow problem (must be solved in M1):** `_series_from_guidance` (`behavior/orb_guidance.py:373`) builds the live series from `snapshot.closed_ohlcv_bars`. If the D2 snapshot carries only today's bars, the core **cannot** derive D−1 context on the live path. Wiring: source `previous_day` values from the same pipeline that feeds `BehaviorContextRequest.previous_day_high/low/close` (the behavior context engine already receives them) and pass them explicitly into `OrbBuildRequest`.

**[RT] Unknown-context policy (P1 — split per path, v2.1):** **live = fail-open + `context_unknown` tag** (backward compatible; context never fabricated; skipped gates tagged so audits count blind decisions). **discovery/proof = fail-closed:** a day with missing prev-day context under `gap_mode=bias_lock` is **excluded from the backtest day-set and counted** in proof metadata (`context_excluded_days`) — otherwise proof metrics mix regimes and a context playbook can be promoted on trades its own filter would have banned (the exact disease this plan exists to cure).

**[RT] Performance rule:** discovery is O(combos × days); timing research runs 1m data up to 400k bars. Prev-day context must be computed **once per day** and passed in — never recomputed per combination.

**[v2.1 / S7] Dual-source integrity:** if core-computed context and explicit `previous_day` fields both exist and disagree beyond epsilon → **hard error** (PIT/integrity bug), never a warning (memo CTX-04).

**[v2.1 / S9] Live ATR:** the live pipeline must carry daily ATR(14) too, not just prev-day H/L/C — the gap classifier itself needs ATR%, so G1 is broader than prev-day H/L/C. Unavailable → `context_unknown` (live fail-open applies).

**[v2.1 / S10] Corporate actions:** prev-day aggregates from the *adjusted* series; guard |gap%| > 20 → tag `context_suspect`, suppress gap rules (memo CTX-02); degenerate prev day (PDH=PDL) → `context_suspect`, suppress CPR rules (CTX-03).

**[v2.1 / dependency direction]** `behavior/context_engines.py` may import `orb/context.py`; never the reverse (prevents circular imports — state it in the module docstring).

**[J-G2] Causal whitelist (expanded per v2.1 P3):** add `gap_pct`, `gap_type`, `gap_filled`, `cpr_width`, `cpr_width_atr`, `cpr_width_pct`, `cpr_class`, `zone`, `or_width_atr`, `pdh_break`, `pdl_break`, `pdh_fail`, `pdl_reclaim`, `session_vwap` to `ALLOWED_FEATURE_NAMES` in `behavior/causal_whitelist.py`, bump `WHITELIST_VERSION` to v0.15. New model field names must never match `FORBIDDEN_FIELDS` (`current_day_*`, `full_day_*`, `future_*`). Registering the full set now avoids a v0.16 churn two milestones later.

**[J-G4] Registry + docs:** add `feature(...)` rows in `apps/api/app/state.py` (pattern: `feature("ORB Context Core", CapabilityStatus.MOCK, "Research", ["orb.context"], [...], "v2_01_...", False, [f"TV-V201-{i:03d}" ...])`) and update `GATES.md` / `SPEC.md` / `TEST_PLAN.md` / `ARCHITECTURE.md` for each shipped version.

**Verify:** `apps/api/tests/test_orb_v201_context.py` — CPR math vs known values (TC<BC ordering), gap classification (0.1% / large thresholds), width classes **per memo CPR-01 precedence partition**, leak-proof test, session-VWAP regression, fail-open live path + fail-closed discovery path, CTX-02/03/04 guards.

**[v2.1 / session VWAP A/B]:** VWAP in the first 15 minutes ≈ price itself, so the confirmation check is near-vacuous at signal time — A/B session-VWAP vs range-VWAP in discovery rather than hard-replacing.

### M2 — Gap-up / Gap-down ORB (v2.01, same release)

**What:** the engine adapts to the gap instead of trading every day identically. Full rule table with worked examples: `ORB_STRATEGY_MEMORANDUM.md` §4 + Examples 1A/1B/4.

**Where:** `orb/core.py` (`_signal_candidate` + new `_gap_gates`), config fields on `OrbStrategyConfig` (`gap_mode: off | bias_lock | full`, `gap_min_gap_pct`, `large_gap_handling`), tests.

**How (decision rules, all config-switchable, thresholds = repo classifier [J-E1]):**

| Gap state | Allowed | Forbidden | Notes |
|---|---|---|---|
| FLAT (<0.1%) | Both directions | — | Standard ORB, unchanged |
| GAP_UP (≥ +0.1%) | LONG only | shorts until a close below ORL **and** below PDC | Short = gap-fail trade, half size |
| GAP_DOWN (≤ −0.1%) | SHORT only | longs until a close above PDC (gap filled) | Long = gap-fill trade, half size |
| LARGE either (≥ max(1.0%, 1.4×ATR%)) | Gap-trap protocol (§6 of memorandum) | blind breakouts | Gap-and-go vs gap-fill trap decided by first-30-min behavior vs PDC |

**[J-G3] Arbiter wiring:** `FinalConfluenceArbiterRequest` (models.py:1261) takes only generic numeric scores — no gap/CPR inputs. Extend it with optional context fields (backward compatible, recommended) or map gap regime onto `market_regime_score`. Decide in M2 code review, do not improvise.

**Verify:** unit tests per gap scenario keyed to memo rule IDs (GAP-01..04, TRAP-01/02, VETO-01). **Acceptance (V2, v2.1):** trade-count shifts are only a smoke test — the real acceptance is a pre-registered OOS expectancy delta on holdout. Spec decisions S2/S3/S4 are closed in the memo (§10); vetoed signals are logged, never consumed.

### M3 — CPR wide/narrow filter (v2.01, same release)

**What:** CPR width as a day-type predictor driving which ORB families are allowed.

**Where:** `orb/core.py` gates; `OrbStrategyConfig` gains `cpr_filter_mode: off | narrow_trend | full`.

**How (decision rules):**

| CPR class + price state | Meaning | ORB action |
|---|---|---|
| NARROW + open above TC | Yesterday was tight balance → trend day likely | Breakout family ON, **reversal family OFF** (reversals die on trend days); buffer may drop to 0.02% |
| WIDE | Yesterday was wide range → mean reversion likely | Small-range breakouts require buffer 0.15% + 1.5× volume; reversal family ON (fade back into CPR); targets capped 1.5R |
| Price inside CPR at lock | No man's land | Veto breakouts (esp. WIDE CPR) or require volume confirmation; ORR only, half size |

**Verify:** tests for the three states; offline validation notebook comparing R-distribution of trades with vs without CPR filter (the "cheapest test" made permanent).

### M4 — Previous-day High/Low break ORB (v2.02) — new strategy family

**What:** `pdh_pdl_breakout` as a new `OrbStrategyFamily` (currently `Literal["orb_breakout", "orr_reversal", "hybrid_orb"]`, models.py:4428).

**Where:** `models.py` literal, `orb/core.py` (`_signal_candidate` third block), `orb/discovery.py` (family grid is generic — picks up the new family automatically).

**How (rules; full zone table in memorandum §6):**
- **PDH break long:** post-range bar **closes above PDH** (close confirmation + volume ≥ range mean) → long; stop = min(PDH, ORH) or retest low; target = risk × R:R. Confluence: when PDH ≈ ORH (within 0.2%), the breakout crosses two resistance layers → tag `dual_level_break`.
- **PDL break short:** mirror.
- **Failed break → reversal:** bar pokes above PDH but closes back below → `PDH_FAIL_SHORT` (reuse ORR sweep skeleton / `_trade_signal`).
- **Edge cases:** if PDH lies *inside* today's opening range, PDH breakout is meaningless → skip, tag `pdh_inside_range`.

**[J-E3] PREREQUISITE — unify backtest stop semantics:** `discovery.py:240-244` sets stop = opposite OR side for **every** signal type, but for REVERSAL signals the core sets stop = sweep extreme (bar high/low). Backtested reversal R-multiples therefore never match the signaled trade. Fix `_backtest_day` to honor the signal's own stop price before adding the new family (also corrects all historical reversal metrics).

**[v2.1 / P2] Historical metric migration:** the E3 fix invalidates every v1.90–v1.97 reversal metric — including the promoted playbook (BEL a1c78a28). After the fix, existing playbooks must be **re-proved or version-stamped and quarantined** before v2.00 ships, or the registry permanently mixes two metric universes. Explicit M4 task: re-run proof for all active playbooks; annotate `metric_universe: pre_e3_fix | post_e3_fix`.

**[v2.1 / S5+S6] Signal accounting & family interactions:** define `max_signals_per_day`, what consumes slots (trap overrides don't; direction-flip after stop does), intra-bar family precedence (a bar closing above both ORH and PDH → merged with `dual_level_break` tag when within 0.2%), and the PDH/PDL × gap/CPR interaction matrix (memo §7 S6) before encoding the family.

**Verify:** `tests/test_orb_v202_pdh_pdl.py` — synthetic series with known PDH: break long fires, fail-reversal fires, inside-range skips; stop-unification regression test for reversal family.

### M5 — Execution realism & decision completeness (v2.02, same release)

**[J-E2] Reframed:** sizing already half-exists — `PaperGuidanceEntryPlan.size_hint` (models.py:4345) and paper approval takes explicit `quantity` (`SimulatedPaperRecordApprovalRequest`). Upgrade, don't build from zero:
- **Capital-risk sizing:** upgrade `size_hint` computation to `capital × risk_pct / |entry − stop|`, liquidity-capped (needs capital/risk_pct on `PaperGuidanceRequest` or guidance config).
- **Partial booking + trailing:** config `exit_plan: full_target | split_1r_half | trail_after_1r`; backtest loop in `discovery._backtest_day` simulates half-exit at 1R (stop → breakeven), remainder trailed by OR-side step; time stop 15:10, breakeven move at 14:30.
- **Daily circuit breaker:** inside the **explicit-approval paper flow** (`RECORD_SIMULATED_PAPER_TRADE` gate) — after N same-day stop-hits in the ledger, guidance returns WAIT with reason `daily_loss_limit_reached`. Fail-open default (no limit) if ledger unavailable, **tagged loudly in warnings** — a silently-disabled safety control is worse than none (v2.1).
- **[v2.1 / S8] Split-exit tie-break:** a bar containing both the 1R target and the stop resolves **stop first** (conservative), inheriting `_backtest_day`'s single-exit convention — split exits make the unresolved tie materially worse (inflates backtested R).
- **Slippage by liquidity:** `OrbCostModel` gains optional per-symbol-tier `slippage_overrides`.

**Verify:** split-exit backtest tests (extends `test_orb_v190.py` style); sizing math unit tests; breaker integration test (mirrors `test_orb_paper_ledger_v193.py`).

### M6 — Regime filter + discovery/proof hardening (v2.03)

**What:**
- OR-width-vs-ATR day-type filter (narrow OR < 0.5×ATR → breakout-favorable; wide OR > 1.2×ATR → fade regime).
- Re-entry rule: one retry after a stopped-out first breakout, config-gated, with the S5 state machine (direction-flip consumes the slot).
- **Proof hardening (V3, v2.1):** raise `OrbProofThresholds` — `minimum_overall_trades` ≥ 30, higher `minimum_oos_trades` — **and add `minimum_trades_per_regime` for context-gated playbooks** (target ≥ 10 per active regime initially): 30 overall trades can otherwise be 28 flat-day + 2 gap-day trades, and the context playbook passes proof on a regime it will trade differently.
- **Staged grid search (V4, v2.1):** context modes as grid dimensions multiply combos ~3× per mode. Stage 1: context modes on/off over the best v1.97 configs only. Stage 2: joint search over stage-1 survivors. "Modes not continuous values" alone does not contain the explosion.

**Where:** `orb/core.py`, `models.py` (`OrbProofThresholds`, `OrbStrategyConfig`), `orb/proof.py`.

**Verify:** proof rejection test (combo with 5 trades must fail promotion), re-entry lifecycle test.

### Deferred / rejected

- **Rejected (stays as designed):** live order routing, broker integration.
- **Future:** event-calendar veto (budget/results/RBI days), news sentiment gate, market-profile HVN/LVN refinement, Fintel-style datasets (short volume/ownership — noted as possible future confluence inputs; India coverage via Fintel is limited).

## 4. File touch summary

| File | Change |
|---|---|
| `apps/api/app/orb/context.py` | **NEW** — gap/CPR/PDH-PDL/VWAP/ATR computation (PIT-guarded) |
| `apps/api/app/orb/core.py` | consume context; gap gates; CPR gates; `pdh_pdl_breakout` family; session VWAP; re-entry |
| `apps/api/app/orb/discovery.py` | per-day prev-context plumbing (precomputed once per day); stop-semantics unification; split/trailing exit simulation |
| `apps/api/app/orb/proof.py` | prev-day aggregate pre-computation before date-subsetting (leak fix); raised thresholds |
| `apps/api/app/models.py` | `OrbConfluenceContext`, `OrbStrategyConfig` fields, `OrbStrategyFamily` literal, `OrbProofThresholds`, arbiter context fields |
| `apps/api/app/behavior/orb_guidance.py` | pass `previous_day` into `OrbBuildRequest` (live flow fix); sizing suggestion; circuit breaker; surface context tags in tickets |
| `apps/api/app/behavior/context_engines.py` | refactor to call `orb/context.py` (single source of truth, no duplicate CPR/gap math) |
| `apps/api/app/behavior/causal_whitelist.py` | v0.15: add gap/CPR/PDH/PDL feature names |
| `apps/api/app/behavior/final_confluence_arbiter.py` | optional context inputs (G3) |
| `apps/api/app/state.py` | feature() rows for v2.01 / v2.02 / v2.03 |
| `GATES.md` / `SPEC.md` / `TEST_PLAN.md` / `ARCHITECTURE.md` / `docs/IMPLEMENTATION_STATUS.md` / `docs/NEXT_BUILD_TARGET.md` | per-version updates |
| `apps/api/tests/test_orb_v201_*.py`, `test_orb_v202_*.py`, `test_orb_v203_*.py` | new tests, existing naming convention |

## 5. Sequence, effort, risks

**Sequence:** M1 → (M2+M3) → M4 → M5 → M6. Rough effort: M1 ~2 days · M2+M3 ~2 days · M4 ~1–2 days · M5 ~2 days · M6 ~1–2 days (excluding the cheapest pre-test).

**Top risks:**
1. Overfitting via bigger grids → combination cap + raised proof thresholds + cheapest pre-test.
2. Prev-day leakage → M1 leak-proof test.
3. Grid explosion → context filters enter the grid as *modes* (off/narrow/full), not continuous values.
4. **[RT]** Live snapshot may lack prev-day bars → explicit `previous_day` wiring + fail-open policy (M1).
5. Two threshold sets drifting (core vs guidance) → one classifier module, both layers call it.

## 6. Changelog vs v1 plan (2026-08-31)

- **[J-E1]** large-gap threshold corrected to repo classifier (max(1.0%, 1.4×ATR%)); was wrongly "0.5×ATR".
- **[J-E2]** M5 reframed: `size_hint` already exists → upgrade path, not greenfield.
- **[J-E3]** added M4 prerequisite: unify `_backtest_day` stop semantics with signal stop (pre-existing reversal-family inconsistency).
- **[J-G1/RT]** added live-path prev-day wiring + unknown-context policy.
- **[J-G2]** added causal whitelist v0.15 registration + forbidden-name constraints.
- **[J-G3]** added arbiter wiring decision point.
- **[J-G4]** added state.py feature rows + doc updates per milestone.
- **[J-G5/RT]** added per-day context precompute performance rule.

## 7. v2.1 addendum — external pre-code review integrated (2026-09-01)

An independent pre-code review (Kimi) of the v2.0 plan + memorandum + judge findings was recomputed claim-by-claim and **confirmed in full** (8 blockers, 2 structural insights, 10 spec gaps, 3 policy corrections, 4 validation upgrades — details and verification in `ORB_V2_JUDGE_FINDINGS.md` §6). Architecture, milestone sequence, and all [J] corrections stand unchanged. What changed:

1. **Rule spec is now memo v2.1** — the source of the reference test cases had wrong worked-example math (old Example 3 replaced), overlapping zones, a self-contradictory CPR classifier, and a precedence contradiction. All fixed with rule IDs (`ORB_STRATEGY_MEMORANDUM.md` §12 change log).
2. **P1 — context policy split by path:** live = fail-open + tag; **discovery/proof = fail-closed** (day excluded + counted) — M1 updated.
3. **P2 — E3 migration:** existing playbooks (incl. BEL a1c78a28) must be re-proved or quarantined after the stop-semantics fix — M4 updated.
4. **P3 — whitelist v0.15 list expanded** (cpr_width_pct, zone, gap_filled, or_width_atr, pdh_fail, pdl_reclaim added) — M1 updated.
5. **V1 — pre-registered cheapest test** (H1/H2/H3 incl. the CPR-vs-close-location redundancy check; n ≥ 30/cell; Mann-Whitney + effect size; Holm; base rates; reverse-outcome rule) — §2 updated. Go/no-go per layer, not jointly.
6. **V2 — M2/M3 acceptance = pre-registered OOS expectancy delta**, trade-count shifts demoted to smoke test.
7. **V3 — per-regime proof minimums** (`minimum_trades_per_regime`, target ≥ 10/active regime) — M6 updated.
8. **V4 — staged grid search** (stage 1: context modes over best v1.97 configs; stage 2: joint over survivors) — M6 updated.
9. **S1–S10 spec decisions closed** in memo §10 (zone timing, gap-fill granularity, whipsaw, veto accounting, family precedence, interaction matrix, dual-source hard error, split-exit tie-break, live ATR, corporate actions).
10. **One refinement to the review itself:** its B3 fix (classify on width_atr alone) contradicts its own replacement Example 3 (width_atr 0.67 → NORMAL). Adopted instead: precedence-ordered partition (NARROW first by width_atr; WIDE by either measure) — satisfies both, verified numerically.

**Revised order (unchanged from the review):** memo v2.1 (done) → cheapest pre-test with V1 statistics → M1.

## 8. v2.2 addendum — second external review (NSE market structure + failure taxonomy) integrated (2026-09-02)

Source: `ORB_V201_NSE_REVIEW_KIMI.md` (verbatim archive) · verification: `ORB_V201_VERIFIED_ANSWER.md` (1 wrong, 13 missed, 11 already-right) · rule spec: memorandum **v2.2**. Verified headline: SEBI circular SEBI/HO/MRD/TPD-1/P/CIR/2025/76 moved all NSE expiries Thursday → **Tuesday effective 01-Sep-2025** (BSE → Thursday) — the plan previously had zero expiry logic.

**Milestone mapping (plan changes only; rule content lives in memo v2.2 §7A):**

- **M1 gains:** D-1 EOD context snapshot as the only morning input (CTX-05, extends S9); universe-hygiene data at symbol intake (F&O flag, ASM/GSM/T2T/ban lists, ₹5cr liquidity floor — UNIV-01..04); **calendar-gate data ingestion promoted out of "Future"** (results/RBI/Budget/holiday/ex-dividend calendars — EVENT-01..06, review top-10 #1).
- **M2 gains:** index-alignment gate (IDX-01 — Nifty futures vs its VWAP/15-min OR at signal → VETO_DIRECTION/HALF_SIZE); event gates wired to the calendar module; RVOL-01 replaces the same-day volume confirm (20-day same-time-bucket average, ≥1.5); VIX regime scaler hooks (VIX-01..03, thresholds 11/17/22/25 as ALERT_ONLY priors).
- **M4 gains:** near-free-win variant adoption — **#14 index-coupled ORB** and **#6 inside-day/NR7 level substitution**; #4 first-retest as a config variant (better R, −40% trade count); #3/#5 (5m scalp, second-close) deferred until the ledger holds 200+ disciplined trades.
- **M5 gains:** **STOP-01 stop-doctrine parity** — `stop_mode: orm | or_opposite | retest_low` per playbook, backtester proven identical by test (folded into the E3/P2 migration, review's V5; this closes W1: memo examples used ORM while engine code uses opposite-OR-side and reversals use sweep extremes); stop-slippage stress (fills at stop + max(0.1%, 0.5× signal-bar range)); EXIT-06 exit precedence (safety > calendar caps > playbook targets > trails).
- **M6 gains:** **afternoon playbook (AFT-01) as a separate validated track** (13:00–13:45 range, entries 13:45–14:30, own folds — never merged into morning stats); Tuesday expiry protocol EXP-01..04 (pinning detector, post-13:30 breakout lockout, last-Tuesday trend exception); ORW/EM expected-move gate once D-1 chain snapshots exist (DERIV-05).
- **Deferred-list change:** event/corporate-actions calendar gate **removed from Future** (now M1/M2 scope — the review's #1). GEX/charm/participant-flow stay **Future + experimental** (`ALERT_ONLY` forever until the ledger proves them). Lot-size 75→65 (Jan-2026): review-asserted — verify against the NSE circular before encoding.

**Engine-layer note:** measure codes (`SKIP_DAY / DELAY_ENTRY / HALF_SIZE / WIDEN_STOP / TIGHTEN_TARGET / VETO_DIRECTION / FLIP_BIAS / REDUCE_FREQUENCY / ALERT_ONLY`) become the gate-enum vocabulary shared by `orb/context.py` outputs and guidance blockers, so every review row maps to one gate output.

## 9. v2.3 addendum — second Kimi submission (Task 3/4 continuation) integrated (2026-09-02)

Source: `ORB_V201B_NSE_REVIEW_KIMI_PART2.md` (byte-exact archive incl. the reasoning trace, CRLF preserved) · accounting: `ORB_V201_VERIFIED_ANSWER.md` §7 (4 corrections W2–W5 · 11 misses M14–M24 · 13 mutual threshold conflicts) · rules: memo **v2.3**. The submission's own expiry banner could not web-verify (its search returned nothing; facts from training data) — our SEBI-circular verification stands and supersedes it; its engineering conclusion became memo EXP-07.

**Milestone mapping:**
- **M5:** STOP-01 gains `or_width_conditional` (opposite OR side if ORW ≤ 0.6×ATR; else ORM; else skip) as the recommended default; the backtest↔live parity test extends to the conditional mode.
- **M6:** REENTRY-01 conditions (20-min trap signature + RVOL ≥ 1.5 re-close + 11:30 bound); **setup promotion bar raised to n ≥ 60 OOS** (`ALERT_ONLY` below it — the pre-test's 30/cell minimum is a different purpose and stands); AFT-01 level-staleness principle; the memo §7A.7 calibration register becomes an explicit discovery calibration task (every conflicting threshold = one config key with both priors recorded).
- **M1/M2:** UNIV-04 both-direction first-bar guards; UNIV-05 chop guards; ENTRY-04 late-entry truncation; EXP-05/06/07 (post-expiry quality tag, expiry confirm overlay, **calendar-file implementation — no weekday constants**).
- **Derivatives (staged):** DERIV-02 dividend/rollover amendments; DERIV-08 participant-OI weekly tag; index skew (25Δ put−call IV spread) added to the Future/experimental list.
- **Sequencing guidance (submission Task 4):** top-10 items 1–4 immediately (LOW effort: event calendar, universe hygiene, session VWAP + side veto, ex-dividend adjustment), 5 & 9 next (index-alignment gate, RVOL), 7 after (conditional re-entry), 8/10 as hygiene infrastructure (OI-wall capping, expectancy monitor + multiple-testing guard).

## 10. v2.4 addendum — third Kimi submission (consolidated Tasks 1–4) integrated (2026-09-03)

Source: `ORB_V201C_NSE_REVIEW_KIMI_PART3.md` (byte-exact archive) · accounting: `ORB_V201_VERIFIED_ANSWER.md` §8 · rules: memo **v2.4** §7A.8/§7A.9. No new contradictions; the submission consolidates and confirms.

- **M1/M2:** UNIV-03 concrete spread threshold (>0.1%) + dual-source tick cross-check (halt on mismatch); EVENT-02 MPC post-buffer ×1.5; EVENT-07 result D-1 tag; ORPDC-01 contested open; GIFTDIV-01 open-vs-GIFT divergence.
- **M2/M4:** IDX-02 sector divergence; CHASE-01 no-chase discipline; ORW-MID intermediate band (0.75–1.0×ATR → HALF_SIZE + ORM + 1.5R) enters the discovery grid as a mode.
- **M5/M6:** EXIT-07 post-breakout management (climax scratch, volume dry-up tighten) added to the exit simulator; RVOL-01 fail path; VIX 5-band and ORW 1.0-skip become **majority priors** (2-of-3 submissions) — still config keys, discovery calibrates; afternoon-window three-variant comparison added to M6's separate-track validation.
- **Confirmation value:** STOP-01 `or_width_conditional`, REENTRY-01, ENTRY-04, EXIT-03, and the top-10 ranking are now triple-confirmed across independent submissions — their priority in the build order rises accordingly.
- **2026-09-03 audit additions:** EXH-01/MKT-01 (M2/M6 gates — gap-exhaustion and index-circuit flatten), EXEC-01/EXEC-02 (M5 execution realism — margin pre-check at 1.2× VaR+ELM sizing ≤80%, broker-heartbeat kill switch with 15:05 reconciliation); first submission retro-archived (`ORB_V201_PRECODE_REVIEW_KIMI.md`); unadopted variants stay archive-only as discovery-grid candidates.
- **2026-09-04 coverage-audit additions (second audit wave):** TRAP-03 magnet-zone filter (M2/M4 — pre-signal trap test near PDH/PDL/OI walls); UNIV-05 PDC-chop signature (M2); NEWS-01 intraday shock detector + VIX-02 cancel-pendings (M2); DERIV-01 stock-level buildup + DERIV-04 ΔPCR confirmation (M6 derivatives staging); CTX-02 **EOD reconciliation job** (M1 nightly compare, mismatch → skip until fixed); complete archived-only variant enumeration (M4/M6 discovery-grid candidates).

## 11. v2.01-track amendment — staged adoption (2026-09-04 build audit)

Audit verdict on this plan: code citations verified true; 4 issues fixed here
(version collision, missing data pipelines, S5 sequencing, BEL fate). Adoption
follows staged 4→2→1: pre-test first, HSTRY-computable filters next, full M1
core only for ledger-proven layers, external feeds only for rules the ledger earns.

### M0 — data inventory + V1 pre-test + BEL decision (no engine code)

1. **Version map (binding):** M1/M2/M3 → v2.01 · M4/M5 → v2.02 · M6 → v2.03.
   Tests `test_orb_v201/v202/v203_*`. Never reuse v1.98–v2.00 labels.
2. **Data-inventory audit:** every memo rule classified HSTRY-computable
   (gap/CPR/zones/RVOL/session-VWAP/first-bar/chop/afternoon/time-to-target),
   needs-file (holiday/expiry calendar CSV, corporate-action list), or
   needs-feed (VIX, GIFT, futures, sector, OI/PCR/GEX, IV, participant OI, news).
   Rules in the last two classes stay `ALERT_ONLY`/unbuilt until their source ships.
3. **V1 pre-test (H1/H2/H3) on existing timing rows** before any engine code.
   Go/no-go per layer (gap, CPR, PDH/PDL separately).
4. **BEL playbook P2 decision (default: re-prove):** after the E3 stop-semantics
   fix, re-run proof for playbook a1c78a28 (its winner row is breakout-family,
   E3-immune) instead of quarantining live paper testing. One-word confirmation
   required before the E3 migration touches it.

### Staged adoption order

- **Stage 4 (first):** V1 pre-test only — measurement without construction.
- **Stage 2 (next):** HSTRY-computable rules as guidance-layer filters/vetoes
  (no core change; single shared classifier per E1).
- **Stage 1 (then):** full M1 core (`orb/context.py`, models, leak tests) only
  for layers the pre-test proves.
- **Feeds (last):** external pipelines only for rules the OOS ledger earns.

### S5 sequencing fix

The signal-slot accounting state machine (ladder M2, direction-flip M4/S6,
REENTRY M6) is implemented in **M2**, not M6. No milestone may encode slot
rules on undefined accounting.

### Data-gated feeds rule

No rule whose inputs lack a shipped source may gate, veto, or size a trade.
Such rules stay `ALERT_ONLY` (or unbuilt) until their feed milestone ships and
the ledger proves them — this is what keeps the engine from going permanently
`context_unknown` on ~40 rules.
