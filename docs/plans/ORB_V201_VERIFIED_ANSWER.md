# Verified Answer — Kimi ORB v2.01 Review vs Our Saved Docs (v2.1)

> **Date:** 2026-09-02 · **Question answered:** "which did we give wrong and which did we miss?"
> **Method:** every claim below checked against the saved documents (`ORB_STRATEGY_MEMORANDUM.md` v2.1, `ORB_CONTEXT_NATIVE_PLAN_V2.md` §7, `ORB_V2_JUDGE_FINDINGS.md` §6) and the engine code. The review itself is archived verbatim in `ORB_V201_NSE_REVIEW_KIMI.md` (byte-identical, 0 diffs).
> **Result summary:** **1 thing we got wrong · 13 things we missed · 11 things we already had right (review-confirmed).** All findings are integrated as memorandum **v2.2** and plan **§8 addendum**.

---

## 1. What we got WRONG (inconsistency inside our own saved docs)

### W1 — Stop doctrine mismatch (review §D.1 + cover-note sharp edge) — CONFIRMED
Our engine (`orb/core.py::_trade_signal`) stops breakouts at the **opposite OR side**; the plan describes exactly that; but memorandum v2.1's worked examples and zone table stop at **ORM** — and E3 already proved reversal signals stop at the **sweep extreme**. Three stop conventions coexist across code/spec/examples, and the memo never declared which one it was using. On wide-OR days the ORM-vs-OR-side choice doubles R and halves size — so the memo's example R-multiples are not the engine's R-multiples.
**Fix (v2.2):** rule **STOP-01** — `stop_mode: orm | or_opposite | retest_low` is a per-playbook config key declared in the playbook spec; examples now state `stop_mode: orm`; the backtester must implement exactly the playbook's stop_mode, verified by a parity test folded into the E3/P2 migration (review calls this V5; treat with E3-class paranoia).

## 2. What we MISSED entirely (absent from memo v2.1 + plan)

| # | Missed item (review ref) | Why it matters | Where it lands now |
|---|---|---|---|
| M1 | **Event & corporate-actions calendar gate** (C1–C7, C12; top-10 **#1**) | We had deferred it to "Future" — the review un-defers it as the biggest known hole: results-day ORs 2–3× normal, ex-dividend false gaps, Budget/RBI/muhurat days | **Un-deferred** → memo §7.5 EVENT-01..06; plan M2 scope; data = published calendars (EOD-OK) |
| M2 | **Tuesday expiry regime** (Task 3.B, C2/C3; top-10 #9) | Verified SEBI change: NSE expiries Thu→**Tue** effective 01-Sep-2025 (circular SEBI/HO/MRD/TPD-1/P/CIR/2025/76). Pinning/gamma now Fri→Tue; last-Tuesday = monthly stock expiry; Wed–Thu OI walls least reliable. We had **zero** expiry logic | memo §7.8 EXP-01..04 |
| M3 | **Index-alignment gate** (variant 14, B5, top-10 **#2**) | Removes the biggest class of single-stock fake-outs; Nifty futures vs its VWAP/15-min OR at signal → `VETO_DIRECTION` / `HALF_SIZE` | memo §7.7 IDX-01; plan M2 |
| M4 | **Universe hygiene** (C8/C9/C10, top-10 **#3**) | Locked-circuit short in a non-F&O name = forced auction/delivery — **the only failure class exceeding a day's risk budget**. Shorts F&O-only; ASM/GSM/T2T/ban exclusions; ₹5cr/day liquidity floor | memo §7.6 UNIV-01..04; plan M1/M6 |
| M5 | **Expected-move gate** (Task 3.A EM; top-10 **#4**) | ORW/EM >0.45 → range mostly spent (tighten, no runner); <0.20 → expansion room (runner-eligible). Replaces ad-hoc width heuristics | memo §7.7 DERIV-05; plan M6+ (needs D-1 chain snapshots) |
| M6 | **VIX regime scaler** (B1–B3, top-10 **#8**) | VIX buckets 11/17/22/25 scale buffer/size/targets; our buffer was CPR-adjusted but **not volatility-scaled** (review §D.3 confirmed) | memo §7.7 VIX-01..03; ENTRY-01 amended |
| M7 | **Afternoon playbook as separate validated strategy** (variant 17, top-10 **#7**) | Hard 11:30 cutoff discards the 13:45–15:00 second trend window (Tuesday expiries, Europe-open). Never merge into morning walk-forward stats | memo §7.9 AFT-01; plan M6 separate track |
| M8 | **RVOL proper definition** (A1; top-10 **#5**) | RVOL = signal-bar volume ÷ **20-day same-time-bucket** average; our volume confirm was same-day range-mean — far weaker than the best-documented ORB edge filter | memo RVOL-01 (replaces volume-confirm definition) |
| M9 | **VWAP gap-day drag + slope + 1σ bands** (verdict 3b/3c) | On gap days session VWAP is dragged toward the gap origin; add PDC-anchored VWAP; slope+bands strictly beat binary position | memo VWAP-01..03 (extends the v2.1 A/B note) |
| M10 | **Exit precedence order** (review §D.2) | `trail_after_1r` vs `TIGHTEN_TARGET` vs pinning-cap can fire on the same trade; we never defined exit precedence | memo EXIT-06: safety exits > calendar caps > playbook targets > trails |
| M11 | **Time-to-target rule** (decision row 23, A10) | A signal at 11:25 with no room to reach 1R is a wasted bullet: skip if (15:10 − T) < 1.5× playbook median time-to-1R | memo ENTRY-03 |
| M12 | **D-1 EOD context snapshot pattern** (review §D.4, extends our S9) | Persist one D-1 snapshot (ATR, CPR, PDH/L, VA, buildup cell, IV/EM, event flags) as the **only** input the morning pipeline reads — makes PIT structural, not aspirational | memo CTX-05; plan M1 |
| M13 | **The other 15 ORB variants** (Task 1: 18 total) | We spec'd only classic ORB + ORR + PDH/PDL + gap splits. Review tabulates 18 with entry/stop/target/best/worst regime; near-free wins: **#14 index-coupled, #6 inside-day/NR7 levels**, then #4 retest (better R, −40% trades); #3/#5 only after 200+ logged trades | archived verbatim (Task 1); adopted per rank into plan §8 |

**Sub-finding under M1 (C12):** our CTX-02 guard (|gap%| > 20 → `context_suspect`) only catches gross misadjustment. The review's sharper case — **ex-dividend false gaps** (price drops by the dividend amount, faking GAP_DOWN) — must be fixed **on the gap classifier itself**: effective gap% = raw gap% + dividend% before GAP-01 classification. Memo CTX-02 amended.

## 3. What we already had right (review confirms, mapped to our rule IDs)

| Review says | Our rule (confirmed) |
|---|---|
| 15:10 time stop "correctly placed", keep ≥10-min MIS buffer | EXIT-03 (memo §3) |
| One trade/day: right as chop brake; vetoed signals don't consume the day | SIG-01 + VETO-01 |
| Fix for trap stop-outs = one **conditional** re-entry (trap signature + re-close + index aligned) | REENTRY-01 (sharpened: conditions now explicit, memo §3) |
| 11:30 cutoff = "right rule" — don't extend, ship afternoon separately | ENTRY-02 (afternoon now M7/AFT-01) |
| Session-VWAP near-vacuous before ~09:45 | already adopted in v2.1 (M1 A/B note); now extended by M9 |
| OR-width regime filter | M6 regime filter present; thresholds sharpened to review's (skip < max(0.2×ATR, 0.15%); veto breakout > 1.2×ATR) — memo §7.7 |
| PIT tagging discipline (@0915 / @SIG / EOD-OK / PARTIAL) | matches CTX design + causal-whitelist v0.15 plan; review's E4 (EOD-derivatives lookahead) extends it — every derivative feature gets an availability timestamp |
| Stop-slippage stress (D5) | M5 `slippage_overrides` + new stress rule (fills at stop + max(0.1%, 0.5× signal-bar range)) |
| Small-n (E1), edge decay (E2), multiple testing (E3), survivorship (E5) | map to V1/V3 pre-registration, v1.94 ledger reliability reports, walk-forward gates, P2 migration |
| GEX/charm/PCR caution — never size without OOS proof | matches our exclusion; adopted as staged ALERT_ONLY protocol (§7.7) |
| All thresholds are priors — calibrate before gating | matches plan §2 weak-link + V1 discipline |

## 4. Fact-check of the review's market-structure claims

- **VERIFIED:** NSE expiries Thursday → **Tuesday effective 01-Sep-2025**; monthly = last Tuesday; BSE → Thursday; only Nifty keeps a weekly; stock F&O monthly-only, physically settled. Source: SEBI circular [SEBI/HO/MRD/TPD-1/P/CIR/2025/76](https://www.sebi.gov.in/legal/circulars/may-2025/final-settlement-day-expiry-day-for-equity-derivatives-contracts_94189.html) (May 26, 2025); corroborated by [Kotak Neo](https://www.kotakneo.com/news/market-news/sebi-to-end-thursday-expiry/) and [Groww](https://groww.in/blog/sebi-nod-nse-to-shift-weekly-f-and-o-expiry-to-tuesday-bse-gets-thursday).
- **REVIEW-ASSERTED (verify against the NSE circular before encoding):** Nifty lot 75→65 from Jan-2026 expiries; broker MIS auto-square-off window 15:15–15:20 (broker-dependent); pre-open imbalance feed quality (PARTIAL).
- **Consistent with known NSE structure (not independently re-verified here):** closing price = VWAP 15:00–15:30; non-F&O bands 2/5/10/20% vs no fixed bands for F&O; T2T/ASM/GSM mechanics; index circuit breakers 10/15/20%.

## 5. Honest limits (adopted from the review, consistent with ours)

Trend days are ~20–25% of sessions — every filter trades frequency for expectancy; judge on expectancy × opportunity, not hit rate, n ≥ 30 OOS per regime cell. GEX/charm/participant-flow gates stay experimental (`ALERT_ONLY`) until our own ledger proves them. All thresholds (VIX 11/17/22/25, ORW 0.25/1.2×ATR, ORW/EM 0.20/0.45, PCR 0.7/1.3, pain-distance 0.5%) are priors — calibrate against our 5m archive before promoting from ALERT_ONLY to gating (same rule as memo §11).

## 6. Adoption map (where each finding landed)

| Document | Change |
|---|---|
| `ORB_STRATEGY_MEMORANDUM.md` → **v2.2** | STOP-01 stop_mode; §7A.1 EVENT-01..06; §7A.2 UNIV-01..04; §7A.3 IDX/VIX/DERIV overlays (staged); §7A.4 EXP-01..04; §7A.5 AFT-01; §7A.6 VWAP-01..03; ENTRY-01 (vol-scaled buffer) / ENTRY-03 (time-to-target); RVOL-01; EXIT-06 precedence; CTX-02 amendment (dividend-adjusted gap on the classifier) + CTX-05 (D-1 snapshot); §12 change log |
| `ORB_CONTEXT_NATIVE_PLAN_V2.md` → **§8 addendum** | calendar-gate data ingestion promoted into M1/M2; universe hygiene in M1/M6; index gate in M2; variant adoption per rank (14, 6, 4 → M2/M4; 3/5 deferred to 200-trade ledger); afternoon playbook as separate M6 track; derivatives overlay staged experimental; stop-parity folded into E3/P2/V5 |
| `ORB_V2_JUDGE_FINDINGS.md` → **§7** | third-pass verification record |
| `ORB_V201_NSE_REVIEW_KIMI.md` | verbatim archive (Part 1 cover note + Part 2 full review, byte-identical) |

---

## 7. Continuation submission (same day, second Kimi message) — verified answer (2026-09-02)

> Source archived **byte-exact** (CRLF preserved; reasoning trace included as delivered, single line ending mid-sentence): `ORB_V201B_NSE_REVIEW_KIMI_PART2.md`. Result vs our v2.2 docs: **4 corrections · 11 misses · 13 mutual threshold conflicts between the two Kimi submissions themselves** (all now in a calibration register — memo §7A.7). Integrated as memo **v2.3** + plan **§9**.

### 7.1 What we got wrong (in v2.2), per this continuation

| # | Finding | Resolution |
|---|---|---|
| W2 | **STOP-01 offered only static modes.** The continuation supplies the missing deterministic default: stop = opposite OR side if ORW ≤ 0.6×ATR; else ORM; else skip — wide-OR days made opposite-side stops absurd (R inflated, size starved) and ORM stops whipsaw-prone on chop | STOP-01 gains `or_width_conditional` (recommended default); parity test extended |
| W3 | **REENTRY-01 was underspecified** — "one re-entry after a stop" lacked the trap signature | Sharpened: stopped **within 20 min** + price **re-closes beyond the OR level with RVOL ≥ 1.5** + **never after 11:30**; direction flip still consumes the slot |
| W4 | **AFT-01 never stated the level-staleness principle** — afternoon trades must use day H/L + PDH/PDL or a fresh 13:00–13:45 range, never morning-OR levels (level staleness after ~90 min is real degradation); window edges also differ between submissions | Principle added; variants registered in §7A.7 |
| W5 | **No expiry-calendar engineering mandate.** Facts were encoded (EXP-01..04) but nothing forbade `dayofweek == Thursday` constants — which silently misfire after any cutover. Kimi's own banner (its live search failed; facts from training data) makes the point: its uncertainty is exactly why the code must read a calendar file | **EXP-07**: expiry logic driven by an exchange holiday/expiry calendar file, never weekday constants. Our SEBI-circular verification supersedes Kimi's unverified banner |

### 7.2 What we missed (M14–M24)

| # | Missed item | Where it lands |
|---|---|---|
| M14 | Post-expiry session = high-quality ORB day (gamma unclenched) — expectancy tag | EXP-05 |
| M15 | Weekly-expiry overlay for cash stocks: +1 extra 5m close confirm; no fresh entries 14:00+; trail (not fixed-target) runners after 14:00 (charm acceleration) | EXP-06 |
| M16 | Basis mechanics: dividend adjustment near ex-date (mechanical discount ≠ bearish); >30% OI rolled → use next-month basis (false-backwardation guard); rollover >85% + positive basis → long-conviction tilt | DERIV-02 amendment |
| M17 | FII participant-OI contrarian tilts: index-futures short ratio >80% → crowded shorts → bullish squeeze tilt; <30% bearish; weekly tag only | DERIV-08 (new) |
| M18 | First-bar **high-volume** contamination guard (pre-open match print: volume z > 4 or range > 2× median) — complements the low-volume single-print guard we had | UNIV-04 amendment |
| M19 | Second chop signature: two failed breakouts **same side** before 11:00 → done for day / switch to ORR (complements the both-sides-broken rule) | UNIV-05 (new) |
| M20 | Late-entry target truncation: entries after 10:45 get `TIGHTEN_TARGET` (achievable R shrinks with time-to-close) | ENTRY-04 (new) |
| M21 | Setup qualification bar: < 60 OOS occurrences → `ALERT_ONLY` — stricter than our V3 pre-test minimum (30/cell); different purposes (pre-test vs promotion), both kept | plan §9 / M6 |
| M22 | Index skew (25Δ put−call IV spread) — optional, index-only, noisy | Future/experimental list |
| M23 | Task-4 sequencing: items 1–4 immediately (LOW effort), 5 & 9 next, 7 after, 8/10 as hygiene | plan §9 |
| M24 | Kimi's verification banner itself (honest uncertainty about expiry facts) — our independent SEBI verification is the stronger evidence and stands | documented here + EXP-07 |

### 7.3 Calibration conflict register — the two Kimi submissions disagree with each other

13 parameters (VIX banding 11/17/22/25 vs 11/14/17/20/25 · ORW narrow 0.2×ATR-skip vs 0.25×ATR-escalate · ORW wide 1.2×ATR-veto vs 1.0×ATR-skip · pain-check 10:00 vs 09:30 · VWAP-start 09:45 vs 10:00 · rollover 80% vs 85% · IVR 70 vs 60 · term-structure 3 vs 5 vol pts · GIFT gates · CPR high-quality 0.2×ATR tag · afternoon window edges · shorts universe F&O-only vs band≥20% · setup n 30 vs 60). **None is hardcoded** — full table in memo §7A.7; every value becomes a config prior; discovery decides. Where safety differs (shorts universe), the stricter rule (UNIV-01 F&O-only) is kept.

### 7.4 Confirmed already-right by this continuation

15:10 time stop (endorsed, MIS buffer) · VETO-01 · one-trade/day as chop brake + conditional-re-entry fix · session-VWAP direction + PDC-anchored gap-day VWAP + ORM-confirm before the VWAP window · event-calendar gate as #1 (already un-deferred) · ex-dividend gap adjustment (already CTX-02) · PIT wiring = D-1 snapshot (already CTX-05) · NSE public chain 15-min delay → broker-API-or-D-1 (already staged DERIV) · GEX research-grade (already DERIV-07 ALERT_ONLY) · measure-code legend (already adopted) · stop parity as E3-class paranoia (already STOP-01/V5) · gap touch-vs-close dual definitions acceptable **if synchronized backtest↔live** (parity note added to GAP-03).

### 7.5 Adoption map for this submission

| Document | Change |
|---|---|
| `ORB_V201B_NSE_REVIEW_KIMI_PART2.md` | **NEW** — byte-exact archive (Part A deliverable + Part B reasoning trace, CRLF preserved) |
| `ORB_STRATEGY_MEMORANDUM.md` → **v2.3** | STOP-01 conditional default · REENTRY-01 sharpened · ENTRY-04 · UNIV-04 amend + UNIV-05 · DERIV-02 amend + DERIV-08 · EXP-05/06/07 · AFT-01 staleness principle · §7A.7 calibration register · §12 change log |
| `ORB_CONTEXT_NATIVE_PLAN_V2.md` → **§9** | milestone mapping + n≥60 promotion bar + Task-4 sequencing |
| `ORB_V2_JUDGE_FINDINGS.md` → **§8** | fourth-pass record |

---

## 8. Third submission (consolidated Tasks 1–4 deliverable) — verified answer (2026-09-03)

> Source archived **byte-exact** (16,269 bytes, line endings preserved): `ORB_V201C_NSE_REVIEW_KIMI_PART3.md`. Result vs our v2.3 docs: **0 new contradictions · 10 new rules adopted · 6 third independent confirmations · 5 calibration-register updates.** Integrated as memo **v2.4** + plan **§10**.

### 8.1 What this submission changes

- **Wrong:** nothing new — v2.2/v2.3 already fixed everything it flags (the two pre-live must-fixes it names — stop-rule inconsistency and expiry-calendar cutover — are exactly our STOP-01/V5 and EXP-07).
- **New rules adopted (memo §7A.8):** CHASE-01 (no entry when price is >1×ATR extended from the OR by 11:00 — a discipline layer we lacked), ORPDC-01 (PDC inside the OR → HALF_SIZE, contested open), GIFTDIV-01 (open vs GIFT-implied gap >0.3% → delay 5 min), IDX-02 (sector divergence >0.5% → HALF_SIZE — submission 1's B6, never encoded until now), EXIT-07 (climax bar + no progress → scratch; post-breakout volume dry-up → tighten), RVOL-01 fail path (<1.0 → delay until recovery), EVENT-02 post-MPC buffer ×1.5 for the session, EVENT-07 result D-1 tag, UNIV-03 concrete spread >0.1% + dual-source tick halt, ORW-MID band (0.75–1.0×ATR → HALF_SIZE + ORM + 1.5R).
- **Third independent confirmations:** STOP-01's `or_width_conditional` (submission 3's variant-1 stop is literally "opposite OR side, ORM if ORW > 0.6×ATR"), all four REENTRY-01 conditions, ENTRY-04's 10:45 threshold, 15:10 hard flat, the ranked top-10, and the calendar-file conclusion. Two reviews agreeing by accident is unlikely — these rules are now evidence-backed priors, not one model's opinion.
- **Register updates (memo §7A.9):** VIX 5-band and ORW >1.0×ATR-skip now have 2-of-3 majorities; the afternoon window has **three** variants (all share the staleness principle); circuit-band-for-shorts has three versions (strictest, UNIV-01, stays); new gap-moderate conflict row.
- **Fact-check:** the submission again says "Tuesday — verify" without successful web verification of its own. Our SEBI-circular verification (§4 above) stands and supersedes; EXP-07 already mandates the calendar-file approach it recommends.

### 8.2 Adoption map for this submission

| Document | Change |
|---|---|
| `ORB_V201C_NSE_REVIEW_KIMI_PART3.md` | **NEW** — byte-exact archive |
| `ORB_STRATEGY_MEMORANDUM.md` → **v2.4** | §7A.8 new rules + amendments; §7A.9 register updates; §12 change log |
| `ORB_CONTEXT_NATIVE_PLAN_V2.md` → **§10** | milestone mapping for the new rules + majority-prior notes |
| `ORB_V2_JUDGE_FINDINGS.md` → **§9** | fifth-pass record |

---

## 10. Coverage-audit verdict (2026-09-04, second audit wave)

Question: "did you really review everything we pasted, and was anything important missed?" Answer after a **row-by-row coverage check** of all four submissions against the memo (not just the structural checks of the first audit): the archives were complete, but **six rules were archived yet never encoded** — the most important being the **TRAP-03 magnet-zone filter** (signal within 0.1% of PDH/PDL/OI wall + wick >60% of the bar → delay/half-size), a core pre-signal trap test. All six are now memo §7A.11 (plus the CTX-02 reconciliation job, DERIV-01/04 and VIX-02 amendments, the UNIV-05 PDC-chop signature, and the complete 11-variant archived-only enumeration). Full table: `ORB_V2_JUDGE_FINDINGS.md` §10.1.

---

## 9. Provenance note (2026-09-03 audit)

The complete submission chain, now fully archived in submission order: **submission 1** = 2026-09-01 pre-code review → `ORB_V201_PRECODE_REVIEW_KIMI.md` (retro-archived 09-03; findings were already integrated as memo v2.1 / findings §6) · **submission 2** = 2026-09-02 full ORB v2.01 review → `ORB_V201_NSE_REVIEW_KIMI.md` (§1–§6 above) · **submission 3** = 2026-09-02 continuation → `ORB_V201B_NSE_REVIEW_KIMI_PART2.md` (§7) · **submission 4** = 2026-09-03 consolidated deliverable → `ORB_V201C_NSE_REVIEW_KIMI_PART3.md` (§8). All four verified byte-exact against their delivered sources. Sections §7/§8 call submissions 2–4 "second/third" counting within their arrival days; the canonical numbering is this list. Full audit record: `ORB_V2_JUDGE_FINDINGS.md` §10.
