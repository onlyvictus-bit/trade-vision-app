# ORB Strategy Memorandum — Context-Native ORB Playbook (Rule-Level) — v2.4

> **Status:** SPEC for the v1.98–v2.00 ORB upgrade (`docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md`). PROPOSED, not built.
> **v2.4 (2026-09-03):** third Kimi submission (consolidated Tasks 1–4, archived byte-exact in `ORB_V201C_NSE_REVIEW_KIMI_PART3.md`; accounting `ORB_V201_VERIFIED_ANSWER.md` §8) integrated — **third independent confirmations** of STOP-01 `or_width_conditional`, REENTRY-01, ENTRY-04 (10:45), EXIT-03 (15:10), and the top-10 ranking; **10 new rules** (§7A.8): CHASE-01 no-chase discipline, ORPDC-01 contested open, GIFTDIV-01 open-vs-GIFT divergence, IDX-02 sector divergence, EXIT-07 post-breakout management, RVOL-01 fail path, EVENT-02 MPC post-buffer, EVENT-07 result D-1 tag, UNIV-03 concrete spread threshold + dual-source tick check, and the ORW 0.75–1.0×ATR intermediate band; **§7A.7 register updated** (VIX and ORW-wide now 2-of-3 majorities; third afternoon variant; third circuit-band version; gap-moderate conflict).
> **v2.3 (2026-09-02):** second Kimi submission (Task 3/4 continuation + reasoning trace, archived byte-exact in `ORB_V201B_NSE_REVIEW_KIMI_PART2.md`; accounting `ORB_V201_VERIFIED_ANSWER.md` §7) integrated — STOP-01 gains the `or_width_conditional` deterministic default, REENTRY-01 trap-signature conditions, ENTRY-04 late-entry truncation, UNIV-04 both-direction first-bar guards + UNIV-05 chop guards, DERIV-02 dividend/rollover amendments + DERIV-08 participant-OI tilts, EXP-05/06/07 (post-expiry tag, expiry confirm overlay, **calendar-file mandate**), AFT-01 level-staleness principle, and §7A.7 **calibration conflict register** (13 thresholds on which the two reviews disagree — config priors, discovery decides).
> **v2.2 (2026-09-02):** second external review (`ORB_V201_NSE_REVIEW_KIMI.md`, verified in `ORB_V201_VERIFIED_ANSWER.md`) integrated — STOP-01 stop-doctrine fix (W1: memo examples used ORM while the engine/spec uses opposite-OR-side and reversals use sweep extremes), event/corporate-actions calendar layer **un-deferred** (§7A), universe hygiene (§7A), index & derivatives overlay staged experimental (§7A), **Tuesday expiry protocol** (verified SEBI change, §7A), separate afternoon playbook (§7A), RVOL-01, ENTRY-01 vol-scaled buffer, ENTRY-03 time-to-target, EXIT-06 precedence, VWAP-01..03, CTX-02 amendment + CTX-05. Change log §12.
> **v2.1 (2026-09-01):** external pre-code review (Kimi) integrated — wrong worked-example math fixed (old Example 3 replaced), exclusive zone definitions, precedence-ordered CPR classifier, explicit decision-ladder precedence, rule IDs (every test cites a rule), spec decisions S1–S10 closed, conventions repaired (T2 rule, sweep-low definition, veto accounting).
> **Purpose:** the exact trade rules the upgraded engine must encode — entry trigger, stop, targets, size, and worked numeric examples for every context combination (including narrow CPR + gap-down + inside previous-day low).
> **Threshold provenance:** all gap thresholds reuse the repo's own classifier (`behavior/context_engines.py::_gap_type`); all formulas reuse `_calculate_cpr`. Nothing here is hand-tuned in a second place.

---

## 1. Background

The existing ORB engine (`apps/api/app/orb/core.py` v1.89) trades the same five rules every day and returns entry/stop/target only for breakout/reversal families. What's missing is the conditional layer: *given gap state, CPR width, and where price sits against previous-day levels, which trade is allowed, what is the entry trigger, where is the stop, and where are the targets.* This memo defines that layer completely, with worked examples, so it can be encoded 1:1 in v1.98+.

## 2. Definitions (all PIT-safe)

| Symbol | Meaning | Source |
|---|---|---|
| ORH / ORL / ORM | Opening-range high / low / mid = (ORH+ORL)/2 | `orb/core.py` (existing) |
| ORW | OR width = ORH − ORL | existing |
| PDC / PDH / PDL | Previous day close / high / low | new `orb/context.py` (M1) |
| CPR: TC / Pivot / BC | TC = pivot+(pivot−BC), Pivot=(PDH+PDL+PDC)/3, BC=(PDH+PDL)/2, ordered so TC<BC | `_calculate_cpr` (verified) |
| CPRW | CPR width = BC − TC; `width_atr` = CPRW ÷ ATR(14 daily); `width_pct` = CPRW ÷ PDC × 100 | **new** |
| Gap% | (Today open − PDC) ÷ PDC × 100 | `_gap_type` (verified) |
| ATR% | ATR(14 daily) ÷ PDC × 100 | new `orb/context.py` |

**Rule CPR-01 — CPR class (precedence-ordered partition; v2.1 fixes the v2.0 both-fire bug):**

```python
if   width_atr < 0.5:                     class = NARROW   # checked FIRST
elif width_atr > 1.0 or width_pct > 0.6:  class = WIDE
else:                                     class = NORMAL
```

Rationale: NARROW must mean tight *relative to the stock's own volatility* (scale-invariant). WIDE fires by either measure. Precedence makes the class a true partition — one day, one class. (v2.0's two independent OR-conditions could label the same day NARROW and WIDE.)

**Rule CPR-04 — derived law (state it so impossible scenarios are never composed again):**
`CPRW = 2·|pivot − BC| = (2/3)·|PDC − BC|`. Therefore PDC always sits exactly **CPRW/2 outside** its own CPR band, and:
- **"NARROW CPR" ⟺ yesterday closed near mid-range.** CPR width carries no information beyond close-location-in-range — non-redundancy must be proven by the pre-test (H3, plan §3 V1) before M3 is built.
- **Price can open inside CPR only if |gap%| > CPRW%/2.** A flat open + WIDE CPR + inside-CPR scenario is mathematically impossible. Zone-at-open and gap state are coupled axes, not independent filters.

**Exclusive price zones (v2.1 replaces the overlapping v2.0 zones; evaluate at signal-bar close per S1, log zone-at-lock for audit):**

| Zone | Definition (exclusive) |
|---|---|
| Z1 | price ≥ PDH |
| Z2 | BC ≤ price < PDH (above CPR, below PDH) |
| Z3 | TC ≤ price < BC (inside CPR) |
| Z4 | PDL ≤ price < TC (below CPR, above PDL) |
| Z5 | price < PDL |

**Rule CTX-02 — corporate-action guard (amended v2.2):** prev-day aggregates must come from the *adjusted* series, **and the gap classifier itself must be dividend-aware**: on an ex-dividend session, effective gap% = raw gap% + dividend% before GAP-01 classification (a ₹12 dividend on a ₹500 stock must not fake a −2.4% GAP_DOWN). Sanity guard retained: |effective gap%| > 20 → likely unadjusted bonus/split → tag `context_suspect`, suppress all gap rules.
**Rule CTX-03 — degenerate prev day:** PDH = PDL (halted/one-print day) → CPRW = 0 → forced NARROW is meaningless → tag `context_suspect`, suppress CPR rules.
**Rule CTX-04 — dual-source conflict:** if core-computed context and explicit `previous_day` fields both exist and disagree beyond epsilon → **hard error** (PIT/integrity bug), never a warning.
**Rule CTX-05 — D-1 EOD context snapshot (v2.2):** the morning pipeline reads **one persisted D-1 snapshot only** — ATR(14), CPR levels, PDH/PDL/PDC, value area, futures buildup cell, IV/expected-move, event flags — each field stamped with its availability timestamp. Makes PIT discipline structural instead of aspirational.

**Rule TRAP-01 definition — "sweep low":** the low of the signal bar itself (the bar that swept below PDL and closed back above it), not the day low. Stop = sweep low − 0.2 epsilon.

## 3. Conventions (used in every rule below)

- **ENTRY-01:** entry trigger = a 5m candle **closes** beyond the level (wick pierces don't count — existing `require_close_confirmation`), buffer `b` (default 0.05%; NARROW CPR may use 0.02%; WIDE CPR small-range breakouts need 0.15% + 1.5× volume; buffer 0 is the Z1 dual-level privilege only); **volatility-scaled (v2.2):** when VIX ≥ 17, b = max(base, 0.3 × median 5m true range of the first 30 min) — a flat 0.05% sits inside the 5m noise floor for high-beta names; fill at next bar open ± slippage.
- **ENTRY-03 (v2.2):** skip any signal where (15:10 − signal time) < 1.5 × that playbook's median time-to-1R (from the ledger) — a late signal with no room to reach 1R is a wasted bullet.
- **RVOL-01 (v2.2, replaces the volume-confirm definition):** RVOL = signal-bar volume ÷ 20-day **same-time-bucket** average; default gate RVOL ≥ 1.5 (2.0 for 5m scalp and post-result variants).
- **EXIT-01:** R = |entry − stop|. T1 = 1R → book 50%, stop → breakeven. **EXIT-04:** breakeven move at 14:30 if T1 not reached. **EXIT-03:** time stop — flat by 15:10 (≥10-min buffer ahead of broker MIS auto-square-off 15:15–15:20 and the 15:00–15:30 closing-VWAP print). **EXIT-06 (v2.2 — exit precedence):** when multiple exit rules fire on the same trade: **safety exits (kill switch, circuit/feed failure) > calendar caps (max-pain, OI wall, event) > playbook targets (T1/T2) > trails** — strict order, no same-trade ambiguity.
- **EXIT-02 (T2 rule, repaired in v2.1):** T2 = the nearer of (a) 2R and (b) the nearest structural level **strictly above entry** (long; mirrored for short) among {TC, BC, PDH} / {TC, BC, PDL}. Structural levels below entry are never targets. No undocumented time conditions.
- **EXIT-05 / STOP-01 (stop doctrine, v2.2; v2.3 adds the conditional default):** the large-gap branch stop is a **config key** (`large_gap_stop: pdc | orm`) — no silent cliff at the LARGE boundary. More broadly, **`stop_mode: orm | or_opposite | retest_low | or_width_conditional` is a per-playbook config key declared in the playbook spec**: the engine's current code stops breakouts at the opposite OR side, reversals at the sweep extreme, and v2.1's examples used ORM — three conventions that must never be mixed silently. **v2.3 recommended default — `or_width_conditional`:** stop = opposite OR side if ORW ≤ 0.6×ATR; else ORM; else skip (wide-OR days make opposite-side stops absurd — R inflated, size starved — while ORM on chop doubles whipsaw; the width-conditional rule removes both failure modes). The backtester implements exactly the playbook's `stop_mode`, proven by a parity test folded into the E3/P2 migration (review's V5). **All worked examples in §8 declare `stop_mode: orm`.**
- **SIZE-01:** size = capital × 1% ÷ R, liquidity-capped. Counter-trend and Z3 trades: **half size**.
- **SIG-01:** max 1 position signal per day (default). **VETO-01:** vetoed/blocked candidates are **logged, never consumed** — a vetoed breakout close does not burn the daily slot (otherwise trap overrides could never fire after a veto).
- **REENTRY-01 (sharpened v2.3):** one conditional re-entry per day, allowed only when the first stop has the **trap signature** — (a) stopped out **within 20 minutes** of entry, (b) price **re-closes beyond the OR level with RVOL ≥ 1.5**, (c) **never after 11:30**; a direction flip after a stop consumes the same slot (state machine decided in M6).
- **ENTRY-04 (v2.3):** late-entry target truncation — entries after **10:45** get `TIGHTEN_TARGET` (achievable R shrinks with time-to-close; the simple complement to ENTRY-03's median-time rule).
- **ENTRY-02:** entry cutoff 11:30 applies to all families including `pdh_pdl_breakout`.

## 4. Decision ladder — explicit precedence (v2.1 replaces "first match wins")

The v2.0 ladder claimed top-down first-match-wins, but the trap overrides must beat the gap bias lock (Example 1B's reclaim-long fires on a bar whose close also reads as a vetoed ORH breakout). Precedence is therefore explicit; each step name is a rule ID cited by tests:

| Order | Step | Rule IDs |
|---|---|---|
| 1 | Large-gap trap protocol | GAP-02 |
| 2 | Sweep/trap overrides (PDL-reclaim long, PDH-fail short) | TRAP-01, TRAP-02 |
| 3 | Gap bias lock | GAP-01 |
| 4 | CPR family filter | CPR-02, CPR-03 |
| 5 | Zone gates | ZONE-01..05 |
| 6 | Nothing fired → NO_TRADE (recorded as a decision) | SIG-01 |

## 5. Gap layer (bias lock)

| Gap state (GAP-01) | Allowed | Forbidden | Notes |
|---|---|---|---|
| FLAT (<0.1%) | Both | — | Standard ORB, no modification |
| GAP_UP (≥ +0.1%) | LONG only | shorts until a 5m **close** below ORL *and* below PDC | Short = gap-fail trade, half size |
| GAP_DOWN (≤ −0.1%) | SHORT only | longs until a 5m **close** above PDC (gap filled) | Long = gap-fill trade, half size |
| LARGE either (≥ max(1.0%, 1.4 × ATR%)) | GAP-02 protocol | blind breakouts | |

**Rule GAP-03 (granularity, per S2):** "gap filled" means **any trade touches PDC** inside the trap protocol; the bias *release* requires a 5m **close** beyond PDC. Two distinct definitions, both named — and both must be **identical in backtest and live** (E3-class parity, v2.3 note).
**Rule GAP-04 (whipsaw, per S3):** first touch of PDC = filled → trap regime, regardless of any subsequent re-break. No third state (decided; simpler and auditable).

## 6. CPR layer (family filter)

| CPR class (CPR-02) | Meaning | Effect |
|---|---|---|
| NARROW | Yesterday closed near mid-range → trend day more likely | **Breakout families ON, reversal family OFF**, buffer may drop to 0.02%. Do not fade the first move. |
| NORMAL | No strong edge | All families per gap layer. |
| WIDE | Wide CPR → mean reversion likely | **Reversal family ON, small-range breakouts need b = 0.15% + 1.5× volume**, targets capped 1.5R. |

**Rule CPR-03:** buffer adjustments per ENTRY-01.
**Caveat (S-A, carried into the plan's pre-test):** CPR width is algebraically close-location-in-range (CPR-04). If the H3 redundancy check shows the close-location tercile carries the same R-distribution information, keep the cheaper feature and cut the CPR layer.

## 7. Zone table (exclusive definitions from §2; evaluated at signal-bar close, S1)

| Zone | Long rules (entry / stop / T1 / T2) | Short rules |
|---|---|---|
| Z1 above PDH | Buy close > ORH (PDH≈ORH within 0.2% ⇒ `dual_level_break`, buffer 0) / stop = ORM / T1 = 1R / T2 = EXIT-02 | Short only on PDH-fail (TRAP-02): close back < PDH after piercing / stop = day high / T2 = ORM |
| Z2 BC–PDH | Same as Z1; PDH is the *later* level, so ORH break is primary | Mirror: close < ORL, stop = ORM, T2 = PDL |
| Z3 TC–BC (inside CPR) | Breakout trades OFF (CPR-02); ORR only, half size / stop = OR extreme / T2 = other OR side | Same mirrored |
| Z4 PDL–TC | Long only if close > ORH **and** > TC (reclaimed CPR) / stop = ORL / T2 = PDH | Sell close < ORL / stop = ORM / T2 = PDL first, then 2R |
| Z5 < PDL | **Counter-trend only** (TRAP-01): reclaim long, half size | Sell close < ORL / stop = ORM / T2 = 2R, OR-projection entry−ORW if nearer |

**GAP-02 — large-gap trap protocol (ladder step 1):**
- Large gap + first 30 min **holds beyond the gap zone** (gap-down: no trade at/above PDC) → trend day → normal directional ORB of §5, stop per EXIT-05 config (`large_gap_stop`).
- Large gap + **gap filled in the first 30 min** (GAP-03: any trade touches PDC) → trap regime: breakout shorts (gap-down case) OFF; reversal long allowed **half size** while price holds above PDC; stop below the retest low; T1 = 1R; T2 = EXIT-02 (nearest structural **above entry** among {TC, BC, PDH}, else 2R — v2.1 fix: TC may sit below entry on these days).

**Rule S6 interaction matrix (PDH/PDL family × context gates):** `pdh_pdl_breakout` inherits GAP-01 and CPR-02. A PDH-break long on a GAP_DOWN day is counter-bias → forbidden (only TRAP-02 PDH-fail short is allowed). Entry cutoff 11:30 applies.

## 7A. v2.2 layers — event calendar, universe hygiene, index & derivatives overlay, expiry protocol, afternoon playbook

**Provenance:** second external review (`ORB_V201_NSE_REVIEW_KIMI.md`, verified answer `ORB_V201_VERIFIED_ANSWER.md`). The review's full 18-variant table and ~40-row failure taxonomy are archived verbatim; the rules below are what the engine encodes.

### 7A.1 Event & corporate-actions calendar layer (EVENT-01..06 — un-deferred; review top-10 #1)

| Rule | Condition (PIT: published calendars, EOD-OK) | Measure |
|---|---|---|
| EVENT-01 | Results day for the symbol | `SKIP_DAY`, or route to the post-result protocol (OR 09:15–09:45, buffer 0.15%, RVOL ≥ 2, HALF_SIZE, target 1.5R, no runner; skip entirely if first 45 min > 1.5×ATR) |
| EVENT-02 | RBI MPC day, rate-sensitive symbol | No fresh entries 09:45–10:15 (policy at 10:00 IST); else HALF_SIZE |
| EVENT-03 | Budget day (incl. Saturday special session) | `SKIP_DAY` |
| EVENT-04 | Election-count/geopolitical event day and \|GIFT Nifty gap\| > 2% at 08:45–09:00 | `SKIP_DAY` or index-coupled-only at quarter size |
| EVENT-05 | Muhurat / special / half / DR-drill sessions | `SKIP_DAY` config flag |
| EVENT-06 | Ex-dividend session | CTX-02: dividend-adjusted gap on the classifier — never let a payout fake a GAP_DOWN |

### 7A.2 Universe hygiene (UNIV-01..04 — the catastrophic-tail filter)

| Rule | Condition | Measure |
|---|---|---|
| UNIV-01 | Non-F&O stock + short signal | `VETO_DIRECTION` — an intraday short into an upper-circuit lock = forced auction/delivery; the one tail that exceeds a day's risk budget. Non-F&O with band ≤5% + gap already >60% of band: exclude entirely |
| UNIV-02 | Symbol on ASM/GSM/T2T list, or in F&O ban (MWPL breach) | Universe exclusion / `SKIP_DAY`; derivatives gates off; never short a banned name |
| UNIV-03 | 20-day median daily value < ₹5 cr, or elevated spread proxy | Universe exclusion; slippage stress ×2 in backtest for that tier |
| UNIV-04 | First-bar anomalies, **both directions (v2.3)**: single-print LOW volume (volume <0.5× 20-day median AND range >1.5× median) **or pre-open-print contamination** (first-bar volume z > 4 or range > 2× median) → re-base OR to 09:20–09:35; auction imbalance >2% ADV; missing/zero-volume bars; feed stale >5 s | Re-base OR window / `DELAY_ENTRY` / `SKIP_DAY` — never impute |
| UNIV-05 | **Chop guards (v2.3, both signatures):** (a) both ORH and ORL broken within 60 min; (b) two failed breakouts on the **same side** before 11:00 | `REDUCE_FREQUENCY` — done for the day, or switch to ORR levels for the remainder |

### 7A.3 Index & derivatives overlay (staged: ALERT_ONLY → gating only after the ledger proves each gate, n ≥ 30 OOS)

| Rule | Condition | Measure |
|---|---|---|
| IDX-01 (**index-alignment gate — top-10 #2**) | Nifty futures on the opposite side of *its* VWAP and 15-min OR at signal | `VETO_DIRECTION`; Nifty mid-range → `HALF_SIZE` |
| VIX-01 | India VIX ≥ 17 at 09:15 | Buffer ×1.5 per ENTRY-01, `HALF_SIZE`, top-liquidity names only |
| VIX-02 | VIX ≥ 22 (or ΔVIX ≥ +8% d/d) | Top-liquidity F&O only; VIX ≥ 25 → `SKIP_DAY` |
| VIX-03 | VIX < 11 + gap < 0.1% + NORMAL/WIDE CPR | `TIGHTEN_TARGET` 0.8R or `SKIP_DAY` |
| DERIV-01 | Index futures buildup 4-cell (D-1, EOD-OK) | Short buildup → `HALF_SIZE` longs / favour shorts; short covering → `TIGHTEN_TARGET` longs; long unwinding → `TIGHTEN_TARGET` shorts |
| DERIV-02 | Futures basis — **dividend-adjusted near ex-dates (v2.3)**: futures trade mechanically below spot by the dividend amount, a discount that is NOT bearish; **if >30% of OI has rolled to next month, read basis off next month** (false-backwardation guard); next-month series in expiry week | Discount >0.15% → `HALF_SIZE` longs; premium >0.25% → `TIGHTEN_TARGET` longs; rollover >85% + positive basis → long-conviction tilt (prior) |
| DERIV-03 | OI walls (D-1 chain, top-100 F&O only) | Call wall above → `TIGHTEN_TARGET` at wall; breakout through wall needs 2 closes + RVOL ≥ 2; put wall mirror |
| DERIV-04 | PCR (OI) | Size modulator **only, never VETO**: extremes (<0.5 / >1.6) → `HALF_SIZE` in the crowded direction |
| DERIV-05 (**expected-move gate — top-10 #4**) | ORW ÷ IV-implied expected move at 09:30 | >0.45 → `TIGHTEN_TARGET` 1R, no runner; <0.20 → runner-eligible |
| DERIV-06 | Max pain | Expiry day only (spot within 0.5% of pain at 10:00 → pin regime); non-expiry days: weak in India, **do not gate** |
| DERIV-07 | GEX / gamma flip, charm, participant-wise OI | **Experimental — `ALERT_ONLY`**, never size, until our own OOS ledger proves them (dealer positioning is assumed, not published, in India) |
| DERIV-08 | **Participant-wise OI contrarian tilts (v2.3):** FII index-futures short ratio >80% → crowded shorts → bullish squeeze tilt; <30% → crowded longs → bearish tilt | Weekly regime tag only — never a daily gate |

### 7A.4 Tuesday expiry protocol (EXP-01..04 — verified SEBI regime, effective 01-Sep-2025)

| Rule | Content |
|---|---|
| EXP-01 | Calendar facts: NSE **weekly (Nifty) = every Tuesday**; **monthly (all F&O stocks) = last Tuesday**, physically settled; only Nifty has a weekly; BSE = Thursday (media "expiry day" chatter is split Tue/Thu). Any Thursday-keyed logic is stale |
| EXP-02 | Tuesday index-expiry on Nifty-heavy names: pinning distorts 13:30–15:00 → afternoon breakouts `TIGHTEN_TARGET`; new entries after 13:30 only via AFT-01/expiry rules |
| EXP-03 | Last-Tuesday monthly + spot within 0.5% of max pain at 10:00 → pin regime: cap targets at pain, post-13:30 breakouts `SKIP`, fade-only (variant 18) |
| EXP-04 | Last-Tuesday **trend exception**: morning range > 1×ATR by 12:00 → charm/delta-hedging accelerates trends — runner-eligible afternoon protocol, **fades vetoed**. OI walls are least reliable Wed–Thu (fresh OI), most reliable Mon–Tue |
| EXP-05 | **Post-expiry session quality tag (v2.3):** the day after expiry = gamma unclenched → ORB reliability up; tag as a high-quality day in expectancy aggregation |
| EXP-06 | **Weekly-expiry confirm overlay (v2.3):** on expiry days, cash-stock signals need **+1 extra 5m close confirm**; no fresh entries after 14:00; runners **trailed** (not fixed-target) after 14:00 — charm/delta-hedge unwind accelerates trends into the close |
| EXP-07 | **Calendar-file mandate (v2.3):** expiry-day logic is driven by an exchange holiday/expiry **calendar file**, never `dayofweek` constants — hard-coded weekday logic silently misfires after regime cutovers (the SEBI 01-Sep-2025 Tue cutover is the live example; Kimi's own banner uncertainty is the argument) |

### 7A.5 Afternoon playbook (AFT-01 — separate validation track, never merged into morning stats)

- Range = 13:00–13:45 H/L; entry on 5m close beyond it, entry window 13:45–14:30; stop = other side of the afternoon range; target 1R into the 15:10 time stop; runner only on expiry trend days (EXP-04) / Europe-open resumption.
- Its own playbook record, its own walk-forward folds, its own median time-to-1R — shipping it inside the morning playbook would contaminate both statistics (review verdict on the 11:30 cutoff).
- **Level-staleness principle (v2.3):** afternoon trades use the day's H/L, PDH/PDL, or a fresh 13:00–13:45 range — **never the morning OR levels** (level staleness after ~90 min is real degradation). Submission-2's variant window (entries 13:45–14:15, hard exit 15:00) is registered in §7A.7 as the alternate to calibrate.

### 7A.6 VWAP rules (VWAP-01..03 — v2.2, completing the session-VWAP migration)

| Rule | Content |
|---|---|
| VWAP-01 | Session-VWAP confirm is near-vacuous on few prints: active only after **6 completed bars (09:45+)**; before that use **VWAP slope from bar 3** or skip the confirm and pay with `HALF_SIZE` |
| VWAP-02 | On gap days (\|gap\| ≥ 0.75×ATR%) session VWAP is dragged toward the gap origin — anchor a second **PDC-anchored VWAP** and require agreement, or fall back to the open-drive/ORM confirm family |
| VWAP-03 | **Slope + 1σ bands** beat binary position-vs-VWAP at zero extra data cost; bands double as targets on `TIGHTEN_TARGET` days |

### 7A.7 Calibration conflict register (v2.3; v2.4 updates in §7A.9 below — the two Kimi submissions disagree; both are priors, discovery decides, nothing is hardcoded)

| Parameter | Submission 1 (v2.01 full review) | Submission 2 (continuation) | Encoding |
|---|---|---|---|
| VIX bands | 11 / 17 / 22 / 25 | 11 / 14 / 17 / 20 / 25 (5-band) | encode the 5-band grid (superset of the coarse one); calibrate |
| ORW narrow | < max(0.2×ATR, 0.15%) → skip-able without confluence | < 0.25×ATR → escalate: free edge, require volume hammer | config `orw_narrow_atr` + action mode |
| ORW wide | > 1.2×ATR → veto breakout family | > 1.0×ATR → `SKIP_DAY` | config `orw_wide_atr` + action mode |
| Max-pain check time | 10:00 (fade window from 13:00/13:30) | 09:30 | config `pain_check_time` |
| VWAP confirm start | after 6 completed bars (09:45) | from 10:00; 09:30–10:00 use ORM | config `vwap_after_bar` (6–9) |
| Rollover conviction | > 80% | > 85% | config |
| IVR event flag | > 70 | > 60 | config |
| IV term-structure spread | weekly vs monthly > 3 vol pts | near vs next month > 5 vol pts | config |
| GIFT gap gates | >1.5% → gap regime; >2% on event days → kill | >1.5×ATR% → `FLIP_BIAS`; >2.5% index gap → skip small/mid | two separate config keys, both priors |
| CPR high-quality tag | — | width_atr < 0.2 → high-quality expansion day | **CPR-05** tag (informational, no veto either way) |
| Afternoon window | range 13:00–13:45, entries 13:45–14:30, exit 15:10 | entries 13:45–14:15 on day H/L + PDH/PDL, exit 15:00 | AFT-01 encodes variant 1; variant 2 registered as alternate |
| Shorts universe | non-F&O shorts vetoed | band ≥ 20% allows shorts | **keep UNIV-01 (stricter, safer)**; revisit only with ledger evidence |
| Setup qualification | n ≥ 30/cell (pre-test, V1/V3) | < 60 OOS → `ALERT_ONLY` | pre-test 30 stands; **promotion bar = 60 OOS** (plan §9) |

### 7A.8 Consolidated-submission additions (v2.4 — third Kimi submission; new rules + amendments)

| Rule | Content |
|---|---|
| CHASE-01 | **No-chase discipline:** price extended > 1.0×ATR from the OR with no pullback by 11:00 → no entry (missed trend accepted; never chase mid-extension) |
| ORPDC-01 | **Contested open:** PDC lies inside today's opening range → `HALF_SIZE` (price magnetised to PDC, chop risk) |
| GIFTDIV-01 | **Open-vs-GIFT divergence:** actual open differs from the GIFT-implied gap by > 0.3% → `DELAY_ENTRY` 5 min (opening print unreliable) |
| IDX-02 | **Sector divergence:** sector index on the opposite side by > 0.5% → `HALF_SIZE`; hard veto only if index AND sector both conflict |
| EXIT-07 | **Post-breakout management:** climax signal bar (volume z > 4) with no price progress in 3 bars → scratch/exit early; next 3 bars volume < 0.7× the OR average → `TIGHTEN_TARGET`/scratch |
| RVOL-01 (amend) | fail path added: RVOL < 1.0 → `DELAY_ENTRY` until volume recovers, else skip (pass remains ≥ 1.5) |
| EVENT-02 (amend) | RBI MPC: after the 09:45–10:15 blackout, buffer ×1.5 applies **for the rest of the session** on rate-sensitives |
| EVENT-07 | **Result D-1 tag:** day before a result → tag next-day gap regime, no size-up |
| UNIV-03 (amend) | concrete thresholds: 60-day turnover < ₹5 cr **or spread > 0.1%** → `SKIP_DAY`; feed integrity via **dual-source tick cross-check — halt on mismatch** (extends UNIV-04) |
| ORW-MID | **Intermediate width band 0.75–1.0×ATR:** `HALF_SIZE` + ORM stop + 1.5R target (between the standard band and the > 1.0 skip) |

### 7A.9 Calibration register — v2.4 updates (submission 3 vs the register)

- **VIX banding: majority reached** — submissions 2 and 3 agree on the 5-band grid (<11 / 11–14 / 14–17 ×1.25 / 17–20 ×1.5+HALF / 20–25 skip small-mid / >25 skip all); submission 1's coarse 4-band is retired to the minority record. Still a prior — discovery calibrates.
- **ORW wide: majority reached** — submissions 2 and 3 agree on `> 1.0×ATR → SKIP_DAY`; submission 1's 1.2×ATR veto is the minority record. The new ORW-MID band (0.75–1.0) sits between the standard band and the skip.
- **Afternoon window: now three variants** — (1) 13:00–13:45 range, entries 13:45–14:30; (2) day H/L + PDH/PDL levels, entries 13:45–14:15, flat 15:00; (3) day range 09:15–13:30 as the "OR", entries 13:45–14:15, flat 15:00. All three share the AFT-01 staleness principle (never morning-OR levels); discovery decides.
- **Circuit band for shorts: three versions** — F&O-only (ours, strictest), band ≥ 20%, band ≤ 10% → skip shorts. UNIV-01 stays until the ledger proves a loosening.
- **Gap-moderate handling (new conflict):** 0.75–1.5×ATR → submission 2: standard bias split; submission 3: no chase, pullback entry only. Both priors; config key `gap_moderate_mode`.

### 7A.10 Execution-tail & market-halt rules (added in the 2026-09-03 audit — submission-2 taxonomy rows that were archived but never encoded)

| Rule | Content |
|---|---|
| EXH-01 | **Post-gap exhaustion:** gap in the same direction as a 3-day cumulative move > 2×ATR → `TIGHTEN_TARGET`, no runner, `HALF_SIZE` (the second leg rarely comes after an extended run) |
| MKT-01 | **Index circuit breaker:** Nifty moves > 7% intraday (the 10/15/20% halt regime) → flatten everything, `ALERT_ONLY` for the remainder; on binary-event days pre-empted by EVENT-04 |
| EXEC-01 | **Margin pre-check:** pre-trade margin check with a 1.2× VaR+ELM buffer; size to ≤ 80% of available margin; a rejection → `ALERT_ONLY`, never a half-on position |
| EXEC-02 | **Broker/API downtime:** heartbeat loss → default state `ALERT_ONLY`; kill switch = market-square-off-all; position reconciliation at 15:05 so any residual is caught before the 15:10 flat |

### 7A.11 Coverage-audit additions (2026-09-04 second audit wave — rows archived across submissions but never encoded; found by row-by-row coverage check)

| Rule | Content |
|---|---|
| TRAP-03 | **Magnet-zone filter** (submission 2 decision row 7 + A1/A2 detection — the pre-signal trap test our TRAP-01/02 lacked): signal level within **0.1% of PDH/PDL or an OI wall** AND signal-bar **wick > 60%** of its range → `DELAY_ENTRY` (2 closes) or `HALF_SIZE`; if the OR is also narrow and RVOL low → `SKIP_DAY` |
| UNIV-05 (amend) | **Third chop signature (A8):** ≥ 3 consecutive 5m bars overlapping **PDC ± 0.1%** → `SKIP_DAY` remainder (post-fill magnetisation chop) |
| NEWS-01 | **Intraday shock detector** (submission 4 Task 2-A + submission 3 ΔVIX row): 5m bar range **> 2×ATR** mid-session, or ΔVIX ≥ +8% intraday → **cancel pending entries**, tighten stops on open positions (regime shift, not a sizing tweak) |
| DERIV-01 (amend) | **Stock-level buildup added** (top-100 F&O, D-1 EOD): same-direction buildup + gap → gap-and-go probability up (full size); opposing buildup → `HALF_SIZE` |
| DERIV-04 (amend) | **ΔPCR d/d confirmation:** rising PCR + rising price = healthy longs; falling PCR + rising price = weak rally → shift one size step |
| VIX-02 (amend) | ΔVIX ≥ +8% intraday → **cancel pending entries** (regime shift), in addition to the existing size/skip effects |
| CTX-02 (amend) | **EOD reconciliation job:** corporate-action-adjusted levels vs raw series compared nightly; mismatched symbol → `SKIP_DAY` until fixed (submission 2 D6) |
| Variant register | **Complete enumeration of archived-only variants** (deliberate, discovery-grid candidates): ORB-30 (09:15–09:45, 2.5R) · ORB-5 micro · VWAP-filtered ORB · gap-and-go pullback refinement · gap-fill completion · 80% value-area rule · open-drive · open-test-drive · open-rejection-reverse · first-retest (config variant, M4) · second-close confirmation. Adoption only via the discovery grid with V1/V3 statistics — never hand-promoted |

## 8. Worked examples (all numbers recomputed and reconciled in v2.1; stop doctrine declared in v2.2)

**Shared data:** PDC 1002.00, PDH 1010, PDL 995, ATR(14d) 12 → ATR% = 1.197% → large-gap threshold = max(1.0, 1.4×1.197%) = **1.68%**. Capital ₹1,00,000, risk 1% = ₹1000. **All examples assume `stop_mode: orm` (STOP-01)** — the engine's current opposite-OR-side default is a different playbook configuration and must never be mixed silently (V5 parity test).

### Example 1A — GAP-01 + NARROW + Z5 continuation → SHORT the ORL breakdown

- Yesterday: H 1010 / L 995 / C 1002 → CPR: pivot 1002.33, TC 1002.17, BC 1002.50, CPRW = 0.33 pts; width_atr = 0.028 < 0.5 → **NARROW** (CPR-01).
- Today opens **988** → gap% = −1.40% → GAP_DOWN (< 1.68%) → **SHORT-only bias** (GAP-01).
- OR (3×5m): ORH 990, ORL 985, ORM 987.5, ORW 5. Zone at lock: 986 → Z5 (below PDL 995); CPR levels ~1002 are overhead resistance, not targets.
- **Entry (ENTRY-01):** trigger = 985 × (1 − 0.0002) = **984.80** → 5m close 984.4 → fill 984.2.
- **Stop:** ORM = **987.5** → R = 3.3. (Conservative variant: ORH 990, R = 5.8, size scales down.)
- **Size (SIZE-01):** 1000 ÷ 3.3 = **303 shares** (liquidity-capped).
- **T1 (EXIT-01)** = 980.9 → book 50%, stop → 984.2. **T2 (EXIT-02):** 2R = 977.6 vs OR-projection 984.2 − 5 = 979.2 → nearer = **979.2**. Time stop 15:10 (EXIT-03).
- Blocked automatically: any long (GAP-01), any reversal short (CPR-02 NARROW), no gap-fill target exists below (PDC 1002 is overhead).

### Example 1B — GAP-01 + NARROW + TRAP-01 (sweep below PDL, reclaim close) → HALF-SIZE reversal LONG

- Same CPR/gap as 1A. A 5m bar pierces to 994.0 (below PDL 995) and **closes 996.1** — failed breakdown.
- **Precedence demo (LADDER-01..05):** the same close (996.1 > ORH 990) is also an ORH-breakout candidate → vetoed by GAP-01 and **logged, not consumed (VETO-01)**; then TRAP-01 (ladder step 2) fires the reclaim long. "First match wins" as v2.0 wrote it would have made this trade impossible.
- **Entry:** close 996.1. **Stop (TRAP-01 definition):** sweep low 994.0 − 0.2 = **993.8** (sweep low = the signal bar's low, not the day low) → R = 2.3.
- **Size:** half → 1000 ÷ (2.3×2) = **217 shares**.
- **T1** = 998.4 (book half). **T2 (EXIT-02, repaired):** 2R = 1000.7 vs structural PDC 1002.0 → nearer wins → **1000.7**. (v2.0's undocumented "14:30" clause is deleted; if a time-conditional structural target is ever wanted, it must be added to §3 conventions first.)
- **Kill switch (single rule):** any 5m close back below PDL 995 after entry → exit (trap failed). The old "below 993.8 or below ORL 985" wording was redundant — 993.8 *is* the stop.

### Example 2 — GAP-01 + NARROW + Z1 → LONG the ORH new-high break

- Opens 1016 → gap% = +1.40% → GAP_UP, LONG-only. ORH 1018.5, ORL 1012, ORM 1015.25, **ORW 6.5**. Zone at lock: 1017 ≥ PDH 1010 → **Z1**.
- **No `dual_level_break`:** |ORH − PDH| / PDH = 8.5/1010 = **0.84%** > 0.2% → tag must not fire (v2.1 fix; v2.0 titled this example wrongly). Buffer = NARROW 0.02% (CPR-03), not 0 — buffer 0 is the dual-level privilege only.
- **Entry (ENTRY-01):** trigger = 1018.5 × 1.0002 ≈ **1018.70** → fill 1018.7. **Stop:** ORM 1015.25 → R = 3.45.
- **Size:** 1000 ÷ 3.45 = **289 shares** (v2.1: unrounded R, not 285). **T1** = **1022.15**. **T2 (EXIT-02):** 2R = 1025.6 vs OR-projection 1018.7 + 6.5 = **1025.2** → take **1025.2** (v2.1 fixes the v2.0 carry-over of ORW 5).

### Example 3 — GAP-01 + WIDE + Z3 → breakouts OFF; half-size ORR long only (v2.1 replacement — the old Example 3 was arithmetically wrong and Premise-impossible)

- Yesterday: H 1018 / L 986 / **C 990** → pivot = 998.00, BC = 1002.00, TC = 994.00 → **CPRW = 8.0 = 0.81% → WIDE** (width_atr 0.67 → not NARROW; width_pct 0.81 > 0.6 → WIDE under CPR-01 precedence).
- Today opens **998.5** → gap = +0.86% → **GAP_UP** (threshold 1.70%: ATR% = 12/990). Open sits inside CPR (994 < 998.5 < 1002) → **Z3** — legal only because of CPR-04's law: gap 0.86% > CPRW%/2 = 0.405%. (v2.0's Example 3 claimed flat-open + WIDE + inside-CPR, which CPR-04 makes impossible.)
- **Rules:** WIDE CPR + Z3 → breakout families OFF (CPR-02); ORR only, half size (SIZE-01). GAP_UP bias → shorts forbidden. Net: only a half-size ORR **long** is permitted.
- **Trade:** bar pokes below ORL to 995.2, closes 996.4 → sweep-reclaim long, half size. Stop = sweep low 995.0 → R = 1.4 → size = 1000/(1.4×2) = **357 shares**. **T1** = 997.8 (book half, stop → breakeven). **T2 (EXIT-02 + WIDE 1.5R cap):** 1.5R = **998.5** (nearer than BC 1002 — cap respected). **Kill:** any close < 995.0.
- **Veto path exercised (VETO-01):** a close above ORH 1001 is a breakout long → vetoed by Z3, logged, does not consume the daily slot (SIG-01). If no sweep by 11:30 → **NO_TRADE recorded**.

### Example 4 — GAP-02 + gap filled early → breakout shorts blocked; fill-fade long with repaired T2

- PDC 1002, ATR 12 → threshold 1.68%. Opens 985 → gap% = −1.70% → **LARGE_GAP_DOWN**. First 30 min rallies through PDC (GAP-03: touched = filled → GAP-04: no third state on re-break).
- **Protocol:** gap-fill after a large gap-down = trap regime for shorts → all breakout shorts OFF; ORR long allowed **half size** while price holds above PDC.
- **Trade:** price retests PDC and holds — entry 1002.5 on the reclaim close; stop below retest low 1001.6 → stop 1001.4 → R = 1.1.
- **T1** = 1003.6. **T2 (EXIT-02, v2.1 fix for B7):** structural candidates **above entry**: TC 1002.17 (below entry — never a target), BC 1002.50 (= entry — skip), PDH 1010 (6.8R — farther than 2R) → none qualifies → **T2 = 2R = 1004.7**. (v2.0's "T2 = TC" produced targets below entry on this data.)
- Stop-doctrine note (EXIT-05): had the day taken the *trend* branch instead of the fill branch, stop = PDC per `large_gap_stop` config — the v2.0 silent cliff at the 1.68% boundary is now a config key discovery decides on.

## 9. Config-key mapping (engine encoding)

| Rule of this memo | Engine home |
|---|---|
| GAP-01 bias lock | `OrbStrategyConfig.gap_mode: off \| bias_lock \| full` (v1.98) |
| GAP-02/03/04 + EXIT-05 | `gap_mode=full` branch + `large_gap_stop: pdc \| orm` |
| CPR-01/02/03 | `OrbStrategyConfig.cpr_filter_mode: off \| narrow_trend \| full` |
| ZONE-01..05 | new `_zone_gates()` in `orb/core.py`, driven by `OrbConfluenceContext` |
| TRAP-01/02, S6 matrix | `pdh_pdl_breakout` family block (v1.99) |
| EXIT-01..04 | `OrbStrategyConfig.exit_plan` (v1.99, simulated in `discovery._backtest_day`) |
| SIZE-01 | `PaperGuidanceEntryPlan.size_hint` upgrade (v1.99) |
| SIG-01 / VETO-01 / REENTRY-01 | `_signal_candidate` accounting rework (v1.98/2.00) |
| CTX-01..05 | `orb/context.py` guards + D-1 snapshot store |
| ENTRY-01 / ENTRY-03 | `buffer_pct` (vol-scaled per VIX-01) + `min_time_to_target_mult` on the playbook spec |
| RVOL-01 | replaces volume-confirm: `rvol_min` (default 1.5) with 20-day same-time-bucket baseline |
| VWAP-01..03 | VWAP confirm config: `vwap_after_bar` (6), `pdc_anchored_on_gap: bool`, `vwap_bands_1σ: bool` |
| STOP-01 / EXIT-05 | `OrbStrategyConfig.stop_mode: orm \| or_opposite \| retest_low`, `large_gap_stop: pdc \| orm` |
| EVENT-01..06 | calendar gate module (published NSE/BSE/RBI calendars, EOD-OK) — plan M1/M2 |
| UNIV-01..04 | universe filter at symbol intake (F&O flag, surveillance lists, liquidity floor) |
| IDX-01 / VIX-01..03 / DERIV-01..07 | derivatives overlay module — staged `ALERT_ONLY` → gating after ledger proof |
| EXP-01..04 | expiry-calendar protocol (Tuesday regime) |
| AFT-01 | separate afternoon playbook record (own validation) |

## 10. Spec decisions closed in v2.1 (S1–S10)

| # | Decision |
|---|---|
| S1 | Zones evaluated at **signal-bar close**; zone-at-lock logged for audit |
| S2 | GAP-03: trap protocol = any trade touches PDC; bias release = 5m close beyond PDC |
| S3 | GAP-04: first PDC touch = filled (trap regime); no whipsaw state |
| S4 | VETO-01: vetoed signals logged, never consumed |
| S5 | SIG-01 max 1/day; trap overrides don't consume slots; direction-flip consumes re-entry slot (state machine in M6) |
| S6 | §7 interaction matrix: pdh_pdl_breakout inherits GAP-01 + CPR-02; cutoff 11:30 applies |
| S7 | CTX-04: dual-source context disagreement = hard error |
| S8 | Split-exit intrabar tie → **stop first** (conservative), inheriting `_backtest_day`'s single-exit convention |
| S9 | Live path needs daily ATR(14) too, not just prev-day H/L/C; unavailable → `context_unknown` (gap class degrades, GAP rules skipped) |
| S10 | CTX-02: adjusted series + |gap%| > 20 guard → `context_suspect` |

## 11. Risks

- **Edge decay:** thresholds are priors until M6's raised-proof validation; the pre-test (now with H1/H2/H3 pre-registered statistics) is the falsifier — including the S-A redundancy check that may kill the CPR layer entirely.
- **Double-filter conflict:** every threshold is the repo's own constant or one config key.
- **Trap cases are counter-trend:** 1B / Example-4 longs are the most likely losers; half-size and kill-switched.
- **Sample shrink:** context filters cut trade counts; M6 raises proof thresholds and adds per-regime minimums in the same release.

## 12. Encoding order + change log

**Encoding order:** Examples 1A/1B first as reference test cases, then 3 (widest rule coverage: WIDE class, Z3 veto + veto accounting, 1.5R cap, NO_TRADE logging), then the matrix. Milestone mapping in `ORB_CONTEXT_NATIVE_PLAN_V2.md` (§3 + §8 addendum).

**v2.4 change log (third Kimi submission — consolidated Tasks 1–4, archived byte-exact in `ORB_V201C_NSE_REVIEW_KIMI_PART3.md`; accounting `ORB_V201_VERIFIED_ANSWER.md` §8):**
- **Audit addendum (2026-09-03, "anything missed or skipped" pass):** §7A section order repaired (7A.7 register now precedes 7A.8/7A.9); the first submission (2026-09-01 pre-code review) retro-archived verbatim as `ORB_V201_PRECODE_REVIEW_KIMI.md` (its findings were already integrated as v2.1, but no archive existed); four submission-2 taxonomy rows that were archived yet never encoded are now rules — **EXH-01** post-gap exhaustion, **MKT-01** index circuit breaker flatten, **EXEC-01** margin pre-check, **EXEC-02** broker-down kill switch (§7A.10). Variants not on the adopted list (e.g., open-drive, open-test-drive, gap-fill completion, 80% rule) remain intentionally archived-only — candidates for the discovery grid, not hand-promoted.
- **Second audit wave (2026-09-04, row-by-row coverage check of all four submissions):** six more archived-but-unencoded items found and added as **§7A.11** — TRAP-03 magnet-zone filter (the most important: the pre-signal trap test near PDH/PDL/OI walls), UNIV-05 PDC-chop signature, NEWS-01 intraday shock detector, DERIV-01 stock-level buildup, DERIV-04 ΔPCR confirmation, VIX-02 cancel-pendings, CTX-02 EOD reconciliation job, and the complete archived-only variant enumeration.
- **Third independent confirmations** (no rule change, confidence upgrade): STOP-01 `or_width_conditional` (variant 1's stop is literally "opposite OR side, ORM if ORW > 0.6×ATR"), REENTRY-01's four conditions, ENTRY-04's 10:45 late-window tighten, EXIT-03's 15:10 hard flat, the top-10 ranking, and the calendar-file conclusion.
- **New rules (§7A.8):** CHASE-01 no-chase · ORPDC-01 contested open · GIFTDIV-01 open-vs-GIFT divergence · IDX-02 sector divergence · EXIT-07 post-breakout climax/dry-up management · RVOL-01 fail path · EVENT-02 MPC post-buffer · EVENT-07 result D-1 tag · UNIV-03 concrete spread >0.1% + dual-source tick halt · ORW-MID intermediate band.
- **Register updates (§7A.9):** VIX 5-band and ORW 1.0×ATR-skip reach 2-of-3 majorities; afternoon window now three variants; circuit-band shorts three versions (strictest kept); new gap-moderate conflict row.

**v2.3 change log (second Kimi submission — Task 3/4 continuation + reasoning trace, archived byte-exact in `ORB_V201B_NSE_REVIEW_KIMI_PART2.md`; accounting in `ORB_V201_VERIFIED_ANSWER.md` §7):**
- STOP-01: added **`or_width_conditional`** deterministic default (opposite OR side if ORW ≤ 0.6×ATR; else ORM; else skip) — fixes wide-OR stop absurdity and chop whipsaw in one rule.
- REENTRY-01 sharpened: trap signature (stopped within 20 min) + re-close beyond OR with RVOL ≥ 1.5 + never after 11:30.
- ENTRY-04: late-entry target truncation after 10:45.
- UNIV-04 both-direction first-bar guards (low-volume single print **and** high-volume pre-open contamination); UNIV-05 chop guards (both signatures).
- DERIV-02 dividend-adjusted basis + rollover next-month switch + rollover-conviction tilt; DERIV-08 participant-OI contrarian tilts (weekly tag only).
- EXP-05 post-expiry quality tag · EXP-06 weekly-expiry +1 close confirm / no fresh entries 14:00+ / trail runners after 14:00 · **EXP-07 calendar-file mandate (no `dayofweek` constants)**.
- AFT-01 level-staleness principle (afternoon never uses morning-OR levels).
- §7A.7 **calibration conflict register**: 13 parameters on which the two submissions disagree — every value a config prior, discovery decides; stricter safety rule kept for shorts (UNIV-01).

**v2.2 change log (second external review — `ORB_V201_VERIFIED_ANSWER.md` has the full wrong/missed/right accounting):**
- **W1 / STOP-01:** stop doctrine made an explicit per-playbook config key (`orm | or_opposite | retest_low`) — the memo's ORM examples, the engine's opposite-OR-side code, and the reversal sweep-extreme stops were three un-reconciled conventions; parity test folded into E3/P2 (V5).
- **M1:** event & corporate-actions calendar layer **un-deferred** → EVENT-01..06 (§7A.1), incl. CTX-02 amendment: dividend-adjusted gap on the classifier itself.
- **M2:** Tuesday expiry protocol EXP-01..04 (§7A.4) — SEBI-verified regime change (01-Sep-2025), absent from all prior versions.
- **M3/M4:** index-alignment gate IDX-01 + universe hygiene UNIV-01..04 (§7A.2/7A.3) — the catastrophic-tail filter (non-F&O circuit-lock shorts).
- **M5/M6/M8:** derivatives overlay staged experimental — VIX-01..03, DERIV-01..07 (expected-move gate), PCR size-only, GEX/charm `ALERT_ONLY`; RVOL-01 replaces the weak same-day volume confirm.
- **M7:** afternoon playbook AFT-01 as a separate validated track (§7A.5).
- **M9–M13:** VWAP-01..03 (PDC-anchored on gap days, slope + 1σ bands), ENTRY-01 vol-scaled buffer, ENTRY-03 time-to-target, EXIT-06 exit precedence, CTX-05 D-1 snapshot; remaining ORB variants archived verbatim and adopted per rank.

**v2.1 change log (first external pre-code review, all findings recomputed before adoption):**
- B1: old Example 3 replaced (old CPRW "10.7 pts WIDE" was arithmetically wrong — true CPRW 1.33 pts = NARROW — and its premise violated CPR-04).
- B2: zones made exclusive (v2.0's Z2/Z3/Z4 overlapped).
- B3: CPR-01 precedence partition (v2.0 could label one day both NARROW and WIDE).
- B4: ladder precedence table with rule IDs (v2.0's "first match wins" was contradicted by trap overrides).
- B5: Example 2 — ORW 6.5, projection 1025.2, R 3.45, size 289, T1 1022.15, `dual_level_break` tag removed (0.84% ≠ dual-level), buffer attribution fixed.
- B6: Example 1B — sweep-low defined, T2 convention repaired (2R = 1000.7), kill switch reduced to one rule.
- B7: Example 4 — T2 = nearest structural **above entry** else 2R (v2.0's TC target could sit below entry).
- B8: EXIT-05 `large_gap_stop` config key replaces the silent LARGE-gap stop cliff.
- S-A/S-B adopted as CPR-04 derived law + pre-test H3.
- S1–S10 decisions closed (§10); P1–P3 and V1–V4 landed in the plan doc.
