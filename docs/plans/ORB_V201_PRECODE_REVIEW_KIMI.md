# Kimi External Review — ORB v2.0 Pre-Code Review (first submission) — VERBATIM ARCHIVE

> **Provenance:** FIRST Kimi submission, received 2026-09-01 (the earliest ORB-plan review in this campaign). Integrated on 2026-09-01 as memorandum **v2.1** (see `ORB_V2_JUDGE_FINDINGS.md` §6 and `ORB_STRATEGY_MEMORANDUM.md` §12 v2.1 change log: blockers B1–B8, structural insights S-A/S-B, spec decisions S1–S10, policy corrections P1–P3, validation upgrades V1–V4, replacement Example 3) — but at that time no verbatim-archive instruction existed, so unlike submissions 2–4 it had no archive file. Archived retroactively 2026-09-03 during the "anything missed or skipped" audit, byte-exact, to complete the provenance chain. Source: `pasted-text-20260901-210209-75660c14.txt`.
> **Archive chain now complete:** submission 1 (this file) → submission 2 `ORB_V201_NSE_REVIEW_KIMI.md` → submission 3 `ORB_V201B_NSE_REVIEW_KIMI_PART2.md` → submission 4 `ORB_V201C_NSE_REVIEW_KIMI_PART3.md`.

---

## Submission (verbatim, byte-exact copy of source)

# Pre-Code Review: ORB V2 Plan + Memorandum + Judge Findings

**Verdict: UPDATE REQUIRED before any coding — but the architecture stands.** Candidate 2 (context-native core), the milestone sequence, and all judge corrections [J-E1/E2/E3, G1–G5] are sound and should not change. The problem is one level down: **the Strategy Memorandum — which §10 designates as the source of the reference test cases — contains 2 numerically wrong worked examples, 1 mathematically impossible scenario, non-exclusive zone definitions, a self-conflicting CPR classifier, and a precedence contradiction.** If M1 starts now, Examples 1A/1B get encoded as tests first (per §10) and the errors become executable truth.

All findings below are verifiable from the three documents alone — every number is recomputed from the memo's own stated formulas.

---

## 1. BLOCKERS — wrong math / broken logic in the memorandum

### B1 — Example 3's CPR width is arithmetically wrong; the example teaches the opposite of the truth

Memo states: PDH 1018 / PDL 986 / PDC 1000 → "CPR width ≈ 10.7 pts = 1.07% → WIDE".

Recompute with the memo's own §2 formula (CPRW = BC − TC):
- pivot = (1018+986+1000)/3 = **1001.33**, BC = (1018+986)/2 = **1002.00**, TC = 2×1001.33 − 1002 = **1000.67**
- **CPRW = 1.33 pts = 0.133% → NARROW** (width_pct < 0.25; width_atr = 1.33/12 = 0.11 < 0.5)

The 10.7 figure is (PDH−PDL)/3 = 32/3 — a formula that exists nowhere in the spec. Per the memo's own rules, Example 3's data is a **NARROW CPR day → breakouts ON, reversals OFF** — the exact opposite of the example's lesson. The 10.7 figure is (PDH−PDL)/3 — a formula that exists nowhere in the spec. Additionally its fade arithmetic is internally inconsistent: stop 1002.2 − fill 1000.8 = R 1.4 → T1 should be 999.4 (memo: 999.3), and T2 997.8 ≈ 2.1R, violating the 1.5R WIDE-CPR cap the same example cites. **Example 3 must be rewritten from scratch** (replacement provided in §6).

### B2 — The zone definitions overlap; Z2/Z3/Z4 are not mutually exclusive

> Z2 "between PDH and TC" · Z3 "inside CPR (TC–BC)" · Z4 "between BC and PDL"

Since TC < BC: any price inside CPR is simultaneously in Z2 (below PDH, above TC), Z3, and Z4 (below BC, above PDL). Three zones fire at once with contradictory actions (Z2: breakouts ON; Z3: breakouts OFF). Fix with explicit boundaries:

| Zone | Definition (exclusive) |
|---|---|
| Z1 | price ≥ PDH |
| Z2 | BC ≤ price < PDH (above CPR, below PDH) |
| Z3 | TC ≤ price < BC (inside CPR) |
| Z4 | PDL ≤ price < TC (below CPR, above PDL) |
| Z5 | price < PDL |

### B3 — The CPR class rule can classify one day as both NARROW and WIDE

NARROW if `width_atr < 0.5 **or** width_pct < 0.25`; WIDE if `width_atr > 1.0 **or** width_pct > 0.6`. Since `width_atr = width_pct ÷ ATR%`, take a volatile stock (ATR% = 2.0%) with CPR width 0.7% of price: `width_atr = 0.35 < 0.5` → **NARROW**, and `width_pct = 0.7 > 0.6` → **WIDE**. Both fire; the class is not a partition. This is not rare — Indian large-caps routinely run 1.5–3% ATR. Fix: classify on **one measure only** (recommend `width_atr` alone — it's scale-invariant and ATR is already computed), or define NARROW/WIDE/NORMAL as an explicit if/elif/else with stated precedence.

### B4 — The decision ladder's "first match wins" is contradicted by the trap overrides

Example 1B's bar *closes at 996.1 — above ORH 990*. That close is simultaneously:
- an **ORH breakout long** → vetoed by GAP_DOWN bias lock (ladder step 2), and
- a **PDL sweep-reclaim long** → allowed by the trap rule (zone layer, ladder step 4).

A lower ladder step overrides a higher one, so "evaluated top-down, first match wins" is false as written. You need an explicit precedence table, e.g.: `(1) large-gap trap protocol → (2) sweep/trap overrides (PDL-reclaim long, PDH-fail short) → (3) gap bias lock → (4) CPR family filter → (5) zone gates → (6) NO_TRADE`, with each override named as a rule ID.

### B5 — Example 2 has three errors

1. **OR-projection target is wrong:** ORW = 1018.5 − 1012 = **6.5**, so projection = 1018.7 + 6.5 = **1025.2**, not 1023.7 (the 5.0-pt width was carried over from Example 1A). Conclusion survives (take projection over 2R 1025.7) but the number is wrong.
2. **Mislabeled `dual_level_break`:** the tag requires PDH ≈ ORH within 0.2%. Here |1018.5 − 1010|/1010 = 0.84% — the tag must NOT fire. The example titled "dual-level break" doesn't meet the dual-level criterion. Either change PDH to ~1018 or retitle.
3. **R rounding:** R = 1018.7 − 1015.25 = **3.45** → size = 1000/3.45 = **289 shares**, T1 = 1022.15 — not 285 / 1022.2 (which use a rounded R = 3.5). Pick one convention: compute size off unrounded R.

### B6 — Example 1B has a broken premise chain and a convention violation

- **Undefined "sweep low":** price at lock is 986 (already below PDL 995). For a bar to "pierce to 994.0", price first rallied through ORH 990. So the day's true low is ~985, not 994 — "stop below the sweep low (993.8)" only works if "sweep low" is defined as *the low of the piercing bar / the local low since the last PDL cross*, not the day low. Define it.
- **T2 contradicts §2:** conventions say "T2 = 2R or structural, whichever is nearer" → nearer is 2R (1000.7), unconditionally. The example instead makes PDC (1002.0) primary with an undocumented "only if reached before 14:30" clause. Either adopt the nearer-target rule or promote the time-conditional structural-target rule into §2 conventions.
- **Redundant kill switch:** "close below 993.8 or below ORL 985" — 985 < 993.8, so the ORL clause can never bind first; and 993.8 *is* the stop. Delete or redefine (e.g., kill = close back below PDL 995 after entry).

### B7 — Example 4's T2 rule produces targets below entry on the shared data

Trap-protocol long fires "while price holds above PDC" → entry > 1002. T2 = TC of CPR = **1002.17**. Any entry above 1002.17 gets a target *below* entry; an entry at 1002.05 gets a +0.12 target against a multi-point stop — negative expectancy by construction. This isn't an edge case: on the shared data CPR sits exactly at PDC. Fix: `T2 = nearest structural level **above entry** among {TC, BC, PDH}, else 2R`.

### B8 — Stop doctrine is discontinuous at the LARGE-gap boundary

Gap −1.67% → stop = ORM (R ≈ 3.3 in 1A terms). Gap −1.69% → LARGE, trend-day branch → stop = PDC (R ≈ 18). A 0.02% gap difference triples the stop distance. Maybe intentional, but it's a cliff encoded silently. Make it a config key (`large_gap_stop: pdc | orm`) and let discovery decide — don't hardcode the discontinuity.

---

## 2. Two structural insights the plan misses (the "thinking" part)

### S-A — CPR width is not new information. Prove non-redundancy before building M3.

Algebraically: **CPRW = 2×|pivot − BC| = (2/3)×|PDC − midpoint(PDH,PDL)|**. CPR width is a pure reparametrization of *where the close sat inside yesterday's range*. "NARROW CPR" ⟺ "closed near mid-range." If your feature store or discovery already has any close-location-in-range feature, the CPR layer may add zero incremental signal. **Add to the cheapest pre-test:** compare CPR-class R-distributions against a raw close-location tercile split. If they carry the same information, keep whichever is cheaper and cut the other — this is exactly the falsifier discipline the plan preaches for gap/CPR vs nothing; apply it CPR-vs-close-location too.

### S-B — Z3 (inside CPR) is mathematically coupled to the gap layer; the memo treats the layers as independent

A clean derivation from the CPR formulas: **PDC is never strictly inside its own CPR** (PDC > mid ⟹ PDC above the band; PDC < mid ⟹ below it; the distance from PDC to the band edge = CPRW/2). Therefore:

> **Price opens inside CPR only if |gap%| > CPRW%/2.** For a WIDE CPR (≥0.6%), that requires a gap ≥ ~0.3% — i.e., **Z3-at-open is always a gap day** (modulo ultra-narrow CPR < 0.2%).

Consequences: (1) Example 3's premise — *flat open + WIDE CPR + inside CPR* — is **mathematically impossible**, a second independent reason B1 forces a rewrite; (2) the zone table and gap table are not orthogonal axes, so discovery should model them as an interaction, not independent filters; (3) state this as a derived rule in the memo so future rule-writers don't compose impossible scenarios.

---

## 3. Spec gaps that must be closed before code (currently "to be improvised")

| # | Gap | Required decision |
|---|---|---|
| S1 | **Zone evaluation timing** — memo says "zones at OR lock," but 1B's trigger depends on price-vs-PDL *after* lock | Evaluate zone at **signal-bar close** (and log zone at lock for audit). Say so. |
| S2 | **`gap_filled` granularity** — §4 bias release uses a 5m *close* beyond PDC; §6 trap protocol says "filled" (undefined) | Define both explicitly: trap protocol = any *trade* beyond PDC; bias release = 5m *close* beyond PDC. |
| S3 | **Large-gap third state** — what if price fills the gap then re-breaks within the first 30 min (whipsaw at PDC)? | Define: first touch of PDC = filled (trap regime) regardless of subsequent re-break, or a third `gap_whipsaw` state → NO_TRADE. Pick one. |
| S4 | **Vetoed signals and the one-signal-per-day rule** — in 1B, the ORH-breakout close is vetoed by bias before the trap long fires | **Vetoed/blocked signals must be logged, not consumed** — otherwise 1B can never fire after a vetoed breakout attempt. This changes `_signal_candidate` accounting; state it now. |
| S5 | **Intra-bar family precedence (M4)** — one bar can close above both ORH and PDH | Define precedence or merge (the `dual_level_break` tag implies merge). Also define: does a stopped-out 1A short followed by a 1B reclaim long consume the M6 re-entry slot? Direction-flip vs same-direction retry needs a state machine: `max_signals_per_day`, what consumes slots, what trap overrides consume. |
| S6 | **PDH/PDL family × context gates** — does `pdh_pdl_breakout` inherit gap bias and CPR filters? | Write the interaction matrix (e.g., PDH-break long on GAP_DOWN day = counter-bias → forbidden or half-size?). Also: entry cutoff 11:30 applies to the new family? State it. |
| S7 | **Dual-source context conflict** — M1 says core computes context "from bars itself" *and* `OrbBuildRequest` carries explicit `previous_day` fields | One source of truth + a validation rule: if both present and disagree beyond epsilon → hard error (that's a PIT/integrity bug, not a warning). |
| S8 | **Intrabar tie-break for split exits (M5)** — a bar containing both the 1R target and the stop | State the ordering rule (conservative: stop first) and that it inherits whatever `discovery._backtest_day` already does for single exits. Split exits make this materially worse — unresolved, it inflates backtested R. |
| S9 | **ATR(14d) on the live path** — judge finding G1 covers prev-day H/L/C, but ATR needs 14 daily bars | Same pipeline must carry daily ATR, or the gap classifier itself (which needs ATR%) degrades on the live path — G1 is broader than written. |
| S10 | **Corporate actions** — gap%, PDH/PDL, CPR are all computed on raw prices | State the data requirement: prev-day aggregates must come from the *adjusted* series, and add a sanity guard (|gap%| > ~20% → likely unadjusted corporate action → tag `context_suspect`, suppress gap rules). A 1:1 bonus otherwise reads as a −50% gap. |

---

## 4. Policy corrections

**P1 — Fail-open is right for live, wrong for research. Split the policy.** The judge doc applies fail-open to "any path (live or backtest)". In discovery/proof, a day with missing prev-day context under `gap_mode=bias_lock` silently trades as if `gap_mode=off` — **proof metrics then mix regimes and a context playbook can be promoted on trades its own filter would have banned** (the exact disease the whole plan exists to cure). Policy: **live = fail-open + `context_unknown` tag (as written); discovery/proof = fail-closed — exclude the day, count exclusions in proof metadata.**

**P2 — The E3 stop-semantics fix invalidates all historical reversal metrics — plan the migration.** Every v1.90–v1.97 promoted playbook was proved under the buggy stop convention. After the M4 prerequisite fix, existing playbooks must be **re-proved (or version-stamped and quarantined)** before v2.00, or the registry permanently mixes two metric universes. Add this as an explicit M4 task.

**P3 — Whitelist v0.15 list is incomplete.** The classification rules use `cpr_width_pct`, but it's not in the addition list. Also add: `cpr_width_pct`, `zone` (Z1–Z5), `gap_filled`, `or_width_atr` (needed by M6's regime filter), `pdh_fail` / `pdl_reclaim`. Registering them now avoids a v0.16 churn two milestones later.

---

## 5. Validation upgrades (cheap, do now)

- **V1 — Pre-register the cheapest test.** Current text: "if NARROW-CPR breakouts don't beat WIDE-CPR ones, stop." Add: hypotheses written down *before* looking (H1 narrow>wide for breakouts; H2 gap-aligned > counter-gap; H3 S-A's CPR-vs-close-location redundancy check); min cell n ≥ 30; Mann-Whitney + effect size with CI (R-distributions are skewed — don't compare means with a t-test); Holm correction across cells; **report base rates** (if 4% of days are Z3, the zone table barely matters); and a stated decision rule including the *reverse* outcome (if WIDE beats NARROW, does the filter flip or die?).
- **V2 — M2/M3 acceptance criteria are too weak.** "Trade counts shift as expected" proves mechanics, not edge. Counts = smoke test. Acceptance = pre-registered OOS expectancy delta on holdout.
- **V3 — Per-regime proof minimums (M6).** Raising `minimum_overall_trades` to 30 doesn't stop a context playbook from passing proof on 28 flat-day trades + 2 gap-day trades. Add `minimum_trades_per_regime` for context-gated playbooks, and state the target numbers now, not during M6.
- **V4 — Staged grid search.** Context modes as grid dimensions multiply combos ~3× per mode. Stage it: (1) context modes on/off over the existing best v1.97 configs; (2) joint search only over survivors. The "modes not continuous values" mitigation alone won't contain the explosion.

---

## 6. Replacement Example 3 (internally consistent, exercises more rules)

**Yesterday:** H 1018 / L 986 / **C 990** → pivot = 998.00, BC = 1002.00, TC = 994.00 → **CPRW = 8.0 = 0.81% → WIDE** (width_atr = 0.67).
**Today:** opens **998.5** → gap = +0.86% → **GAP_UP** (threshold 1.70%) → long-only bias. Open sits inside CPR (994 < 998.5 < 1002) → **Z3** — correctly demonstrating the S-B law (Z3 required a gap into the band).
**OR (3×5m):** ORH 1001, ORL 995.5, ORM 998.25.
**Rules:** WIDE CPR + Z3 → breakout families OFF; ORR only, half size. GAP_UP bias → shorts forbidden. Net: only a half-size ORR *long* is permitted.
**Trade:** bar pokes below ORL to 995.2, closes 996.4 → sweep-reclaim long, half size. Stop = sweep low 995.0 → R = 1.4 → size = 1000/(1.4×2) = **357 shares**. T1 = 997.8 (book half, stop → breakeven). T2 = 1.5R cap = **998.5** (nearer than BC 1002 — consistent with the WIDE cap). Kill: any close < 995.0.
**Veto path exercised:** a close above ORH 1001 is a breakout long → vetoed by Z3, logged as a vetoed signal, does not consume the daily slot (S4). If no sweep by 11:30 → **NO_TRADE recorded**.

This one example now tests: WIDE classification, bias lock, Z3 veto + veto accounting, ORR half-size, the 1.5R cap, and NO_TRADE logging — and every number reconciles.

Also fix: Example 2 → projection **1025.2**, size **289**, T1 **1022.15**, drop the `dual_level_break` label (or move PDH to ~1018); Example 4 → T2 = nearest structural **above entry** among {TC, BC, PDH} else 2R; Example 1B → define sweep-low, drop the redundant ORL kill clause, resolve the T2 convention.

---

## 7. Minor

- Example 2's "buffer 0, narrow CPR" misattributes the buffer rule — NARROW allows 0.02%; buffer 0 is the Z1 *dual-level* privilege (which this example doesn't qualify for).
- M1: session VWAP replacing range-VWAP — VWAP in the first 15 min ≈ price itself, so the confirmation check is near-vacuous at signal time; A/B it in discovery rather than hard-replacing.
- M5 circuit breaker fail-open on ledger-unavailable is acceptable for paper, but tag it loudly (a silently-disabled safety control is worse than none).
- Degenerate prev day (PDH = PDL, halted stock) → CPRW = 0 → NARROW; add a data-quality guard + `context_suspect` tag.
- Dependency direction: `behavior/context_engines.py` may import `orb/context.py`, never the reverse — state it to prevent a future circular import.
- Add rule IDs to the memo (GAP-01…, CPR-01…, ZONE-01…, TRAP-01…) so every test cites a rule — matches your TV-V convention and makes the audit trail 1:1.

---

## 8. What does NOT change

Candidate 2 architecture · M1→M6 sequence and effort estimates · the PIT pre-computation fix in `proof.py` · all judge corrections [J-E1/E2/E3, G1–G5] · fail-open *for the live path* · the cheapest-test-first discipline · the hard research-only boundary.

## Recommended order

1. **Memorandum v2.1** (~1 day, doc-only): fix B1–B8, S1–S10 decisions, P1–P3, replacement Example 3, rule IDs. Re-run the judge pass against the corrected memo only.
2. **Cheapest pre-test** with V1 statistics (including the S-A redundancy check) — go/no-go per layer (gap, CPR, PDH/PDL separately, not jointly).
3. **Then M1.** Everything in M1–M6 stays exactly as planned once the rule spec is true.

The plan's own verdict standard applies: the architecture was verified; the rule layer was not — and it's the rule layer that becomes test code on day one. Fix the memo first; it costs a day and saves encoding a wrong reference suite.