# ORB Upgrade Plan — Adversarial Judge Findings (v2 corrections)

> **Status:** complete verification pass, 2026-08-31. Target: the v1 upgrade plan for the ORB engine, judged claim-by-claim against the codebase before plan approval.
> **Verdict:** **VERIFIED WITH CAVEATS** — the plan is directionally right, but it contained 2 factual errors, inherited 1 pre-existing code inconsistency, and missed 5 practical gaps. All are integrated into `ORB_CONTEXT_NATIVE_PLAN_V2.md` (marked **[J]** / **[RT]**).

---

## 1. Claims table (plan claim vs. what the code actually says)

| # | v1 plan claimed | Observed in code | Status |
|---|---|---|---|
| 1 | CPR math exists at `context_engines.py:284`, no width logic anywhere | Confirmed — `pivot=(H+L+C)/3`, `tc=pivot+(pivot−bc)`, returns BC/TC ordered (TC<BC); zero width/narrow/wide logic in repo | VERIFIED |
| 2 | Large gap ≈ "1% or 0.5×ATR" | `_gap_type` uses `large_threshold = max(1.0, atr_pct × 1.4)` — i.e. **1.4× ATR%, floor 1%**; flat < 0.1% | **REFUTED → corrected** |
| 3 | "Position sizing is missing" | `PaperGuidanceEntryPlan.size_hint` already exists (models.py:4345); paper approval takes explicit `quantity` (`SimulatedPaperRecordApprovalRequest`) | **REFUTED → M5 reframed as upgrade** |
| 4 | Gap/CPR/PDH-PDL are veto-only at guidance layer, blind in core/discovery | Confirmed — `FinalConfluenceArbiterRequest` (models.py:1261) takes only generic numeric scores; `build_orb_candidate` receives no prev-day data; whitelist already allows `previous_day_high/low`, `cpr`, `orb_high/low` | VERIFIED |
| 5 | Engine takes only the first signal per day, no re-entry | Confirmed — `_signal_candidate` returns on first match; `_backtest_day` produces one trade/day | VERIFIED |
| 6 | Prev-day leak trap in `proof._series_for_dates` | Confirmed — filters bars by date list; D−1 bars vanish for the first holdout day | VERIFIED |

## 2. Errors found and corrected

### E1 — Wrong gap threshold (fixed in M2)
The v1 plan invented a 0.5×ATR rule. The repo's own classifier (`context_engines.py::_gap_type`) is: FLAT < 0.1%, LARGE ≥ max(1.0%, 1.4 × ATR%). The core must reuse **this exact classifier** — otherwise the guidance-layer veto and the new core gates will disagree on the same day (one blocks, the other trades): a self-inflicted conflict.

### E2 — Sizing already half-exists (M5 reframed)
`PaperGuidanceEntryPlan.size_hint` (models.py:4345) exists as a raw float, and paper records take an explicit user-approved `quantity` with literal approval text `RECORD_SIMULATED_PAPER_TRADE`. M5 is therefore *upgrade `size_hint` to capital-risk sizing* (`capital × risk_pct ÷ |entry−stop|`), not build from zero. The daily circuit breaker must live inside that explicit-approval flow, not around it.

### E3 — Pre-existing stop inconsistency the plan would inherit (new M4 prerequisite)
`discovery.py:240-244` sets stop = opposite OR side for **every** signal type — but for REVERSAL signals the core sets stop = sweep extreme (bar high/low, `core.py::_trade_signal`). Backtested reversal R-multiples therefore never match the signaled trade. `_backtest_day` must honor the signal's own stop price **before** adding the `pdh_pdl_breakout` family; this also corrects historical reversal metrics.

## 3. Practical failures / gaps the plan missed

### G1 / [RT] — Realtime flow problem: live path has no previous-day source (M1 blocker)
`_series_from_guidance` (`behavior/orb_guidance.py:373`) builds the live series from `snapshot.closed_ohlcv_bars`. If the D2 snapshot carries only today's bars, the core **cannot** derive D−1 context on the live path — gap/CPR/PDH/PDL gates silently degrade exactly where it matters (live decisions). Fix in M1: source `previous_day` values from the same pipeline that feeds `BehaviorContextRequest.previous_day_high/low/close` and pass them explicitly into `OrbBuildRequest`.

### G2 — Causal whitelist registration
`behavior/causal_whitelist.py` (v0.14) already whitelists `previous_day_high/low`, `cpr`, `pivot`, `orb_high/low` — good. New features (`gap_pct`, `cpr_width`, `cpr_width_atr`, `pdh_break`, `session_vwap`, …) must be added and `WHITELIST_VERSION` bumped (v0.15). New model field names must **never** collide with `FORBIDDEN_FIELDS` (`current_day_*`, `full_day_*`, `future_*`, `target_hit_after_entry`, `sl_hit_after_entry`) or the audit layer flags them.

### G3 — Arbiter has no gap/CPR inputs
`FinalConfluenceArbiterRequest` scores direction from generic numeric fields only (`market_regime_score`, `structure_score`, `trap_score`, …). Surface context by extending the request with optional context fields (recommended, backward compatible) or mapping onto existing scores. Decide in M2, don't improvise.

### G4 — Registry and docs drift
Every ORB version is registered in `apps/api/app/state.py` as a `feature(...)` row with TV-V IDs, and `GATES.md` / `SPEC.md` / `TEST_PLAN.md` / `ARCHITECTURE.md` document them. Every new version (v1.98 / v1.99 / v2.00) needs its feature row + doc updates or the capability audit reports drift.

### G5 / [RT] — Performance rule
Discovery is O(combos × days) and timing research runs 1m data up to 400k bars. Prev-day context must be computed **once per day** and passed in — never recomputed per combination.

## 4. Unknown-context policy (specified because of G1)

When prev-day data is absent on any path (live or backtest):
- context-dependent gates are **skipped with a warning**; standard ORB still runs (fail-open, backward compatible with v1.89);
- context is **never fabricated**;
- every skipped gate is tagged `context_unknown` in warnings so audits can count how often decisions run blind;
- residual risk (accepted, documented): the large-gap veto cannot fire on unknown gap.

## 5. Council re-check after corrections

- **Independence:** the v1 verdict rested on code reading; this judge pass is a second, adversarial measurement of the same codebase (correlated family) plus one genuinely independent find (E3 — discovered only by cross-reading core vs. backtester). Confidence rises modestly: **P(success) ≈ 78% (CI 65–87%)** with the live-path gap (G1) and the unknown-context policy (§4) now closed in the plan.
- **Weak link unchanged:** whether gap/CPR/PDH-PDL filters actually add edge on our symbols — the cheapest test (offline labeling of existing backtest trades by gap type and CPR width) answers this before any engine code.
- **Standing correction adopted:** all thresholds cite the repo's own constants; any future threshold change goes through discovery, never hand-tuned in two places.

---

## 6. Second pass — external pre-code review verified and integrated (2026-09-01)

An independent pre-code review (Kimi) of the v2.0 documents was judged claim-by-claim: **every number recomputed before adoption.**

**Verdict on the review: VERIFIED** — all 8 blockers (B1–B8), both structural insights (S-A, S-B), and all policy/validation items were confirmed by recomputation. Highlights:

| Review claim | Recomputed result |
|---|---|
| B1: memo Example 3's CPR "10.7 pts WIDE" wrong | Confirmed — true CPRW = 1.333 pts (0.133%, width_atr 0.11) → **NARROW**; the 10.7 figure is (PDH−PDL)/3, a formula in no spec. Fade arithmetic also off (T1 999.4 not 999.3; T2 2.14R violated the 1.5R cap) |
| S-A: CPRW = (2/3)·\|PDC − BC\| | Confirmed exactly over random trials — CPR width is a reparametrization of close-location-in-range; redundancy check (H3) added to the pre-test |
| S-B: PDC never inside its own CPR; open-inside-CPR requires \|gap%\| > CPRW%/2 | Confirmed algebraically — old Example 3's premise (flat open + WIDE + inside CPR) was impossible; replaced wholesale by the review's Example 3, adopted with numbers re-verified (gap 0.86% > CPRW%/2 0.405% ✓) |
| B2: zones overlap | Confirmed — replaced with exclusive Z1–Z5 partition |
| B3: class rule can fire NARROW and WIDE on one day | Confirmed (ATR% 2.0, width 0.7% → both) — fixed with a precedence-ordered partition |
| B4: "first match wins" contradicted by trap overrides | Confirmed — replaced by an explicit 6-step precedence table with rule IDs |
| B5: Example 2 errors | Confirmed — ORW 6.5 → projection 1025.2; dual_level gap 0.84% → tag must not fire; R 3.45 → size 289, T1 1022.15 |
| B6: Example 1B premise chain | Confirmed — sweep-low now defined (signal-bar low), T2 repaired to 2R = 1000.7, kill switch reduced to one rule |
| B7: Example 4 T2 below entry | Confirmed (entry 1002.5 vs TC 1002.17) — T2 rule now "nearest structural strictly above entry, else 2R" |
| B8: stop cliff at the LARGE boundary | Confirmed — now config key `large_gap_stop: pdc \| orm` |
| P1/P2/P3, V1–V4, S1–S10 | All adopted into the plan (§7 addendum) and memo (§10) |

**One finding against the review itself:** its B3 fix (classify on `width_atr` alone) contradicts its own replacement Example 3, which is WIDE only under the `width_pct` criterion (width_atr 0.67 → NORMAL under width_atr-only). Resolution: precedence-ordered partition — NARROW first (`width_atr < 0.5`), then WIDE (`width_atr > 1.0 or width_pct > 0.6`), else NORMAL. Verified numerically: the B3 counterexample now classifies once (NARROW), and the replacement Example 3 stays WIDE. This is the only deviation from the review as written.

**What did not change:** candidate 2 architecture · M1→M6 sequence · PIT pre-computation fix · all first-pass corrections [J-E1/E2/E3, G1–G5] · fail-open for the live path · cheapest-test-first · research-only boundary.

**Result:** memorandum is now **v2.1** (rule IDs, repaired examples, exclusive zones, precedence ladder, closed spec decisions S1–S10); plan carries the v2.1 addendum (§7) with P1–P3 and V1–V4 landed in M1/M2/M4/M6 and the pre-test.

---

## 7. Third pass — second external review (ORB v2.01, NSE market structure) verified and integrated (2026-09-02)

Source archived verbatim: `ORB_V201_NSE_REVIEW_KIMI.md` (byte-identical, 0 diffs vs the delivered text). Full accounting: `ORB_V201_VERIFIED_ANSWER.md`. Headline: **1 wrong (W1 stop-doctrine mismatch: memo examples ORM vs engine opposite-OR-side vs reversal sweep-extremes), 13 missed (event/corporate-actions calendar gate — un-deferred; Tuesday expiry regime — SEBI-verified 01-Sep-2025; index-alignment gate; universe hygiene incl. the non-F&O circuit-lock tail; expected-move gate; VIX scaler; separate afternoon playbook; RVOL; VWAP drag/slope/bands; exit precedence; time-to-target; D-1 snapshot; 15 further variants), 11 already-right (EXIT-03, SIG-01/VETO-01, ENTRY-02, REENTRY-01, early-VWAP note, OR-width filter, PIT discipline, slippage stress, E1–E5 mappings, GEX caution, thresholds-as-priors).**

Fact-check performed: the review's headline calendar claim was verified against SEBI circular SEBI/HO/MRD/TPD-1/P/CIR/2025/76 (May 26, 2025) — NSE expiries Thursday → Tuesday effective 01-Sep-2025, BSE → Thursday. Lot-size 75→65 remains review-asserted (verify against the NSE circular before encoding).

All findings are integrated as memorandum **v2.2** (STOP-01, §7A layers EVENT/UNIV/IDX-VIX-DERIV/EXP/AFT, new conventions) and plan **§8 addendum** (milestone mapping; calendar gate removed from the deferred list). Pattern note for future reviews: this review's strongest finds were in the layer our plan had *deferred* (calendar) and in a cross-document convention mismatch (stops) — both classes the first two passes structurally under-weighted; keep cross-doc consistency sweeps and deferred-item re-tests in every future judge pass.

---

## 8. Fourth pass — second Kimi submission (Task 3/4 continuation + reasoning trace) verified and integrated (2026-09-02)

Archive: `ORB_V201B_NSE_REVIEW_KIMI_PART2.md` — Part A (deliverable) and Part B (reasoning trace, single line ending mid-sentence as delivered) embedded **byte-exact, CRLF preserved** (initial shell-archive attempt had LF-normalized the CRLF source — caught by byte-diff, rebuilt in binary mode; the check itself is part of this pass). Accounting: `ORB_V201_VERIFIED_ANSWER.md` §7.

**Verdict on the submission: VERIFIED with one supersession.** Content confirmed against our v2.2 docs: 4 corrections (W2 STOP-01 static → `or_width_conditional` default; W3 REENTRY-01 underspecified → trap-signature conditions; W4 AFT-01 missing level-staleness principle; W5 no calendar-file mandate → EXP-07), 11 misses (post-expiry quality tag, expiry confirm overlay, basis dividend/rollover mechanics, participant-OI contrarian tilts, first-bar high-volume contamination, second chop signature, late-entry truncation, n ≥ 60 OOS promotion bar, index skew, Task-4 sequencing, the banner itself), and — the pass's key structural finding — **13 parameters on which the two Kimi submissions disagree with each other** (VIX banding, ORW bounds, pain-check time, VWAP-start, rollover/IVR/term-structure cuts, GIFT gates, CPR quality tag, afternoon window, shorts universe, setup n). Resolution: memo **§7A.7 calibration conflict register** — every conflicting value becomes one config key with both priors recorded; discovery decides; where safety differs, the stricter rule is kept (UNIV-01 F&O-only shorts).

**Supersession:** the submission's expiry banner honestly states its live search returned no results and its expiry facts are training-data-based. Our independent verification (SEBI circular SEBI/HO/MRD/TPD-1/P/CIR/2025/76, §7 above) is the stronger evidence and stands; the banner's engineering conclusion — calendar file, not `dayofweek` constants — is adopted whole (EXP-07).

Integrated as memo **v2.3** + plan **§9**. Standing rule reinforced: **no threshold from any external review is ever hardcoded** — each enters the calibration register as a prior.

---

## 9. Fifth pass — third Kimi submission (consolidated Tasks 1–4) verified and integrated (2026-09-03)

Archive: `ORB_V201C_NSE_REVIEW_KIMI_PART3.md` (byte-exact, 16,269 source bytes embedded, line endings preserved). Accounting: `ORB_V201_VERIFIED_ANSWER.md` §8.

**Verdict: VERIFIED — a consolidation, not a contradiction.** Zero new conflicts with v2.3. Contribution: **10 new rules** (CHASE-01, ORPDC-01, GIFTDIV-01, IDX-02, EXIT-07, RVOL-01 fail path, EVENT-02 amend, EVENT-07, UNIV-03 amend, ORW-MID band) and **5 register updates** — most notably, VIX 5-banding and the ORW >1.0×ATR skip now hold **2-of-3 majorities** across submissions, and the top-10 ranking is reproduced identically. The submission's named pre-live must-fixes (stop-rule consistency, expiry-calendar cutover) are already our STOP-01/V5 and EXP-07 — cited as third-party confirmation rather than new work.

Judge-pass value of this round: it demonstrates the **majority-prior mechanism** working — when independent submissions converge on a threshold (VIX bands, ORW bounds, re-entry conditions), confidence rises without any single source being trusted; when they diverge (afternoon window, circuit bands, gap-moderate), the register holds both and discovery decides. Integrated as memo **v2.4** + plan **§10**.

---

## 10. Audit pass — "verify if anything was missed or skipped" (2026-09-03)

A full audit of the entire review-integration campaign (all four submissions, all archives, all docs). **Four findings, all repaired in the same pass:**

1. **Archive-provenance gap (FIXED):** the FIRST submission (2026-09-01 pre-code review — blockers B1–B8, S-A/S-B, S1–S10, P1–P3, V1–V4) was integrated as memo v2.1 (§6 above) but had **no verbatim archive file**, because the archive-everything instruction only arrived on 09-02. Retro-archived byte-exact as `ORB_V201_PRECODE_REVIEW_KIMI.md`. The initial audit script also mis-paired it against the 09-02 archive source; with the correct pairing all four archives verify byte-exact (containment checks PASS).
2. **Section-order defect (FIXED):** memo §7A subsections read 7A.6 → 7A.8 → 7A.9 → 7A.7 after the v2.4 insertion (an edit placed the new blocks before the register header). Reordered to 7A.1…7A.10; duplicate 7A.7 block removed.
3. **Archived-but-never-encoded rules (FIXED):** four submission-2 taxonomy rows (post-gap exhaustion B7, index circuit breaker C11, margin rejection F1, broker downtime F2) existed only inside the verbatim archive. Now memo rules §7A.10: **EXH-01, MKT-01, EXEC-01, EXEC-02**.
4. **Intentionally archived-only variants (documented, no action):** ORB variants not on the adopted list (open-drive, open-test-drive, open-rejection-reverse, gap-fill completion, 80% value-area rule, 5m scalp, second-close) stay archive-only by design — candidates for the discovery grid, never hand-promoted. Stated explicitly in the memo v2.4 audit addendum so future audits don't re-flag them.

Everything else re-verified clean: all four archives byte-exact vs their paste attachments; the 09-02 cover note fully present (all 19 distinctive lines); registration counts consistent (17 plan files after the retro-archive); no stale version headers.

### 10.1 Second audit wave — row-by-row coverage check (2026-09-04, user challenge accepted)

The first audit verified *structure* (archives, rule IDs, counts). This wave verified **content coverage**: every distinct rule/threshold/row across all four submissions checked for an encoding home (memo rule, register row, or documented archived-only status). **Six genuine gaps found — the user's disbelief was justified:**

| # | Missed item (source) | Now encoded |
|---|---|---|
| 1 | **Magnet-zone trap filter** (submission 2, decision row 7 + A1/A2): signal within 0.1% of PDH/PDL/OI wall + wick >60% of bar → delay/half-size | **TRAP-03** (§7A.11) — the most important miss: the pre-signal trap test that feeds TRAP-01/02 |
| 2 | **PDC-chop signature** (A8): ≥3 consecutive 5m bars overlapping PDC ±0.1% → skip remainder | UNIV-05 third signature |
| 3 | **Intraday shock detector** (submission 4 Task 2-A; submission 3 ΔVIX): 5m range >2×ATR or ΔVIX +8% → cancel pendings, tighten stops | **NEWS-01** + VIX-02 amend |
| 4 | **Stock-level OI buildup** (submission 2 Task 3): top-100 F&O, same-direction + gap → full size; opposing → half | DERIV-01 amend |
| 5 | **ΔPCR d/d confirmation** (submission 2): falling PCR + rising price = weak rally → one size step | DERIV-04 amend |
| 6 | **EOD reconciliation job** (D6): adjusted-vs-raw nightly compare; mismatch → skip until fixed | CTX-02 amend + plan M1 |

Also added: the **complete archived-only variant enumeration** (11 variants with disposition) so future audits have an explicit baseline. All landed as memo §7A.11 + change-log entry; plan §10 updated. Method note for future passes: structural audits (files, IDs, byte checks) do NOT catch content gaps — every campaign with pasted guidance needs at least one **row-by-row coverage audit** against the encoding spec.
