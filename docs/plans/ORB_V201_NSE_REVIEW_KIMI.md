# Kimi External Review — ORB v2.01, NSE India Equities (VERBATIM ARCHIVE)

> **Provenance:** external pre-code review received 2026-09-02 (Kimi). Saved verbatim, line-per-line, per explicit user instruction — no edits, no omissions, no paraphrase.
> **Part 1** = the submission cover note exactly as delivered in chat (verbatim, including UI status lines).
> **Part 2** = the full review document `orb-v201-review.md` (verbatim byte-copy of paste attachment `pasted-text-20260902-133308-3b0c0a29.txt`).
> **Verification + adoption of this review:** `docs/plans/ORB_V201_VERIFIED_ANSWER.md` (what our v2.1 docs got wrong, missed, already had right) · memorandum **v2.2** · plan **§8 addendum** · findings **§7 third pass**.
> **Independent fact-check (2026-09-02):** headline calendar claim VERIFIED — SEBI circular SEBI/HO/MRD/TPD-1/P/CIR/2025/76 (May 26, 2025): all NSE equity-derivative expiries moved Thursday → **Tuesday effective 01-Sep-2025**; BSE → Thursday. Lot-size 75→65 (Jan-2026): review-asserted — verify against the NSE circular before encoding.

---

## Part 1 — Submission cover note (verbatim)

Expiry regime confirmed — major change in 2025 that your system's calendar logic must encode. Now I'll build the full memo.

Worked for 7s
▶
ORB v2.01 Review — NSE India
Markdown

Worked for 12s
▶
The full review is in the preview — 
orb-v201-review.md

. The headline findings:

Verified first (it changes your calendar logic): NSE expiries moved from Thursday to Tuesday effective 01-Sep-2025 (SEBI standardisation). Nifty weekly = every Tuesday; single-stock futures/options = monthly, last Tuesday, physically settled. Only Nifty retains a weekly (Bank Nifty etc. killed Nov-2024). Pinning/gamma now concentrates Fri→Tue; any Thursday-keyed expiry logic is stale.

The four tasks, compressed:

18 ORB variants tabulated (entry/stop/target/best/worst regime) — from 30-min OR and first-retest entries to open-test-drive, NR7/inside-day level substitution, VWAP-reclaim, a separate 13:45–14:30 afternoon playbook, and a last-Tuesday expiry-pinning fade.
~40 failure scenarios in six groups (price action, regime, calendar/structural, microstructure/data, statistical, execution tail), each with pre-entry detection tagged by point-in-time legitimacy and a measure code. The densest avoidable-loss cluster: results days, ex-dividend false gaps, and locked-circuit shorts in non-F&O names (an intraday short into an upper circuit = forced auction/delivery — the one tail that exceeds a day's risk budget).
Derivatives overlay with thresholds and PIT status per metric: VIX buckets (11/17/22/25), futures buildup 4-cell, PCR 0.7/1.3 as size modulator (never VETO), OI walls as target caps, max pain (expiry-day only — weak in India otherwise), and the single best addition: ORW ÷ IV-implied expected move as your target/runner gate. GEX is flagged experimental — dealer positioning is assumed, not published, in India.
25-row decision table + ranked top 10. #1 is the event/corporate-actions calendar gate your memo deferred — un-defer it, it's the biggest known hole for a single-stock system.
Your three flagged questions:

One trade/day: right as a chop brake, wrong in that a trap stop-out on a trend day gets treated like a real loss. Fix = one conditional re-entry (trap signature + re-close + index aligned), not more trades.
11:30 cutoff: keep it for the morning playbook, but don't extend it — ship the 13:45–14:30 window as a separately validated playbook so you don't contaminate walk-forward stats.
VWAP: session-VWAP is the right move, but it's near-vacuous before ~09:45 (use slope or half-size early), gets dragged on gap days (add a PDC-anchored VWAP), and slope + 1σ bands beat binary position at zero data cost.
One more sharp edge: your spec says breakout stop = opposite OR side, but your memo examples use ORM stops — on wide-OR days that mismatch silently corrupts every R-multiple in the ledger until the backtester and production rule are unified.

---

## Part 2 — Full review (verbatim, byte-copy of source)

# ORB v2.01 Review — NSE India Equities
**Senior intraday derivatives strategist & quant review** · Prepared 02 Sep 2026 · Research-only system

---

## 0. Ground rules & verified market structure (read first)

**Point-in-time (PIT) discipline used throughout:** every gate below is tagged with what data it needs and whether that data is legitimately available at decision time:
- **@0915** = available before the opening bell (D-1 EOD data, calendars, GIFT Nifty).
- **@SIG** = available at signal time intraday (completed 5m bars, live quotes, broker-fed chain data).
- **EOD-OK** = fine from exchange EOD files for next-day use.
- **PARTIAL** = available but delayed/degraded in public feeds — usable only via broker API or with a lag caveat.

**Verified NSE structure as of 2026 (checked against NSE contract specs & circulars):**

| Item | Current state |
|---|---|
| Nifty **weekly** expiry | **Tuesday** (moved from Thursday, effective 01-Sep-2025, per SEBI standardisation). Holiday → previous trading day. |
| Nifty **monthly/quarterly** expiry | **Last Tuesday** of the month (was last Thursday). |
| **Single-stock** futures & options | **Monthly only** (stocks never had weeklies on NSE). Expire **last Tuesday** of month, physically settled. |
| Bank Nifty / FinNifty / Midcap weeklies | **Discontinued Nov-2024** (SEBI one-weekly-per-exchange rule). Only **Nifty** has a weekly. |
| BSE (Sensex) expiry | Thursday — irrelevant to you, but note financial media "expiry day" chatter is now split Tue/Thu. |
| Nifty lot size | 75 → **65** from Jan-2026 expiries. |
| Equity session | 09:15–15:30; pre-open auction 09:00–09:08 (match ~09:08–09:12); closing price = **VWAP of 15:00–15:30**; post-close session 15:40–16:00. |
| Index circuit breakers | 10% / 15% / 20% Nifty move → market-wide timed halts. |
| Stock price bands | Non-F&O stocks: fixed bands 2/5/10/20%. **F&O stocks: no fixed daily bands** (dynamic operating ranges only) → gap-through-stop risk is higher in exactly the names you should trade. |
| T2T (trade-to-trade) | No intraday netting; delivery compulsory; brokers block MIS/CO. |
| ASM/GSM | 100% margin, no intraday leverage; brokers typically block intraday product types. |
| Margin | Peak margin 100% upfront; effective intraday leverage ≤ ~5× (VaR+ELM). |
| Broker MIS auto square-off | Typically 15:15–15:20 → your 15:10 time stop is correctly placed; keep ≥10 min buffer. |
| Special sessions | Muhurat (Diwali, ~1h), Budget-day Saturday sessions, DR drill sessions — all ORB-poisonous. |

> **Why this matters to your ORB:** the entire Indian options microstructure (pinning, gamma, charm, PCR flips) now concentrates on **Tuesday**, not Thursday. Any expiry logic keyed to Thursday in your code, notebooks, or head is stale. Expiry-week gamma effects now run Fri→Tue; Wednesday–Friday are post-expiry rebuild days.

---

## TASK 1 — ORB variants & alternative strategies

Format: Entry / Stop / Target / Best regime / Worst regime. "R" = initial risk per trade. OR = opening range; ORH/ORL/ORM = high/low/mid; ID = inside day; RVOL = signal-bar volume ÷ 20-day same-time-bucket average.

### A. Structure & timeframe variants

| # | Variant | Entry | Stop | Target | Best regime | Worst regime |
|---|---|---|---|---|---|---|
| 1 | **Classic 15-min ORB (your base)** | 5m close beyond ORH/L + buffer + RVOL ≥1.5 + VWAP side | Opposite OR side | 2R or 1R+runner | Normal-VIX (11–17), moderate OR width (0.25–0.8×ATR) | Chop, wide-OR mean-reversion days |
| 2 | **30-min OR (09:15–09:45)** | 5m close beyond 30-min OR + VWAP | ORM | 1.5–2R | News-digestion days, trend days; lets the auction finish | V-reversal days (entry is late, stop wide) |
| 3 | **5-min OR (scalp)** | Break of first 5m bar + RVOL ≥2 | Other side of that 5m bar | 1R flat, no runner | Gap-and-go, high-conviction event mornings | Everything else; retail noise machine |
| 4 | **First-retest entry** | After clean break, limit order at ORH (long) on first pullback that holds | Below retest low / ORM | 2R+, runner-eligible | Trend days with shallow pullbacks; improves R by 30–50% | Vertical trend days (no fill — opportunity cost only); trap days |
| 5 | **Second-close confirmation** | Requires 2 consecutive 5m closes beyond level | Opposite OR side | 2R | High-VIX whipsaw (17–22), sweep-prone names | Fast trend days (~0.2–0.3R worse entry) |
| 6 | **Inside-day / NR7 expansion** | Levels = **IDH/IDL, not ORH/ORL**; break + RVOL ≥1.5 | Opposite ID side (wide) or ORM (tight, half size) | 2R + runner | Post-compression; NR7 + narrow-CPR confluence is the single best ORB day-type | Continued compression: raise buffer ×1.5 or skip |
| 7 | **PDH/PDL break** | 5m close beyond PDH/L + RVOL; OR used only as trigger timing | ORM or breakout-bar low, whichever tighter | 1.5R then trail | Trend continuation after balanced day | Inside days (PDH/L too far — R broken) |

### B. Open-type & gap variants (Market Profile logic, 5m-implementable)

| # | Variant | Entry | Stop | Target | Best regime | Worst regime |
|---|---|---|---|---|---|---|
| 8 | **Open-drive ORB** | ORB long only if price never traded below open in first 15 min (mirror for short) + ORH break | ORM | 2R + trail; add-on eligible | Trend days; strongest open signature | Open-auction days (rarely triggers — acceptable) |
| 9 | **Open-test-drive long** | Open < PDL/value low, auction reclaims open within 20 min, then ORH break | Day low | PDC first, then 2R | Failed gap-downs; squeeze of early shorts | True gap-and-go down (you simply don't get the reclaim — safe) |
| 10 | **Open-rejection-reverse short** | Gap ≥0.5×ATR% up, first drive takes price below open, then 5m close < ORL | Above ORH / gap-day high | VWAP, then PDC (fill) | Exhaustion gaps after multi-day run-up | Gap-and-go (big trend up — this is the loser; keep to 1 attempt) |
| 11 | **Gap-and-go** | Gap ≥0.75×ATR% + first 15 min never closes back through open + ORH break | Below first 5m bar low | 2R + trail to 14:45 | Result/news-driven repricing | Gap-fill days — your GAP-04 split must route these away |
| 12 | **Gap-fill completion** | Gap + failure to extend by 09:45 → enter toward PDC on first lower-high | Beyond gap-day extreme | PDC touch (not close); optional flip on 5m close beyond PDC | Wide-CPR / mean-reversion days | Gap-and-go — never average into it |
| 13 | **80% rule (value-area re-entry)** | Open outside prior day value area; enter on 5m close back inside VA | Outside the opening extreme | Opposite edge of VA | Balance days after a failed auction | Trend days that open outside VA and keep going — VA data must be EOD-OK |

### C. Context-coupled variants

| # | Variant | Entry | Stop | Target | Best regime | Worst regime |
|---|---|---|---|---|---|---|
| 14 | **Index-coupled ORB** | Base entry + condition: Nifty futures on same side of *its* VWAP and 15-min OR at @SIG; else DELAY_ENTRY up to 15 min or HALF_SIZE | Unchanged | Unchanged | All regimes; removes the single biggest class of single-stock fake-outs | Idiosyncratic news days (stock decouples) — you miss some winners; accept it |
| 15 | **VWAP-reclaim (gap-down longs)** | Gap-down ≥1×ATR%: trigger = 5m close above **session VWAP** (after 10:00 only), ORH ignored | Day low | PDC / 1.5R | Gap-fill days | Continuation down (second leg) |
| 16 | **Post-result ORB** | Results-day variant: OR window extended to 09:15–09:45, buffer 0.15%, RVOL ≥2, HALF_SIZE | ORM | 1.5R; no runner | Post-earnings drift days | Conflicting-guidance whipsaw; if first 45 min > 1.5×ATR, skip entirely |
| 17 | **Afternoon range breakout (separate playbook)** | Range = 13:00–13:45 H/L; entry on 5m close beyond it, window 13:45–14:30 | Other side of AR range | 1R into 15:10; runner only on expiry trend days | Europe-open trend resumption; Tuesday expiry trend days | Quiet pinning days (see Task 3) — gate it with the pinning detector |
| 18 | **Expiry pinning fade (monthly expiry, F&O stocks)** | Last Tuesday: if spot within 0.5% of max pain at 13:00, fade extensions toward pain, 13:30–14:45 | Beyond nearest OI wall strike | Max pain strike; hard flat 14:50 | High-OI large-caps on monthly expiry | Expiry *trend* days (morning range already >1×ATR → charm acceleration; do not fade) |

**Ranking by expected value for your system:** 14 (index-coupled) and 6 (inside-day levels) are near-free wins. 4 (retest) improves R but cuts trade count ~40%. 17 and 18 add day-count in regimes your morning system is flat in. 3 and 5 are for after you have 200+ logged trades of discipline.

---

## TASK 2 — Failure scenario taxonomy

Each row: why ORB breaks → **pre-entry detection** (PIT-tagged) → measure. Codes: `SKIP_DAY`, `DELAY_ENTRY`, `HALF_SIZE`, `WIDEN_STOP`, `TIGHTEN_TARGET`, `VETO_DIRECTION`, `FLIP_BIAS`, `REDUCE_FREQUENCY`, `ALERT_ONLY`.

### A. Price-action failures

| # | Failure | Why ORB dies | Pre-entry detection (PIT) | Measure |
|---|---|---|---|---|
| A1 | Failed breakout / trap | Break bar lacks participation; algos fade the level | Signal-bar RVOL <1.5 (@SIG); ORW <0.25×ATR (@0915); signal within 0.1% of PDH/PDL (magnet + trap zone) | `DELAY_ENTRY` (2 closes) or `SKIP_DAY` if both narrow-OR and low RVOL |
| A2 | Sweep-and-reclaim (stop hunt) | ORH set by opening print; liquidity grab above it | Wick >60% of signal-bar range (@SIG); ORH within 0.1% of PDH or a round strike | `DELAY_ENTRY`, `HALF_SIZE` |
| A3 | Double-break chop | Both ORH and ORL trigger within 60 min → no range edge | Count of ORM crosses ≥3 in first 45 min post-lock (@SIG) | `REDUCE_FREQUENCY`: one-and-done for the day after 1 stopped trade |
| A4 | OR too narrow | Range is noise; every tick is a "breakout" | ORW < max(0.2×ATR, 0.15%) (@0915) | Trade only with NR7/narrow-CPR/gap confluence, buffer ×1.5; else `SKIP_DAY` |
| A5 | OR too wide | R economics destroyed; day already spent its range | ORW >1.2×ATR (@0915) | `VETO` breakout family; ORR-only with ORM stop; `TIGHTEN_TARGET` 1R |
| A6 | Midday V-reversal | Morning trend reverses on news/lunch flows | Hard to detect pre-entry; proxies: event day flag (@0915), gap filled within 30 min (@SIG) | `TIGHTEN_TARGET` (book 1R, no runner) on event days |
| A7 | Inside-day level confusion | OR breaks but IDH/IDL (the real level) holds | Today OR fully inside yesterday's range (@0915) | Substitute levels → IDH/IDL (variant 6); else `DELAY_ENTRY` |
| A8 | PDC chop (gap days) | Post-fill price magnetises to PDC, chops ±0.1% | ≥3 consecutive 5m bars overlapping PDC ±0.1% (@SIG) | `SKIP_DAY` remainder |
| A9 | Trend day, no retest | Retest variants never fill | n/a — opportunity cost, not a loss | Accept; never chase with market orders mid-extension |
| A10 | Signal too late | Entry at 11:25 leaves <100 min to target; afternoon lunch chop eats it | Signal time vs playbook median time-to-1R (your ledger, @SIG) | Skip if (15:10 − T) < 1.5× median time-to-1R for that playbook |

### B. Regime failures

| # | Failure | Why ORB dies | Pre-entry detection (PIT) | Measure |
|---|---|---|---|---|
| B1 | High-VIX whipsaw | 5m noise doubles; fixed 0.05% buffer is inside the noise floor | India VIX ≥17 at 09:15 (@0915, realtime) | Buffer = max(0.05%, 0.3× median 5m TR of first 30 min) ×1.5; `HALF_SIZE` |
| B2 | Vol storm | Stops gapped; slippage 3–5× | VIX ≥22 (@0915); ΔVIX ≥ +8% d/d | ORB only in top-liquidity F&O names; VIX ≥25 → `SKIP_DAY` |
| B3 | Low-VIX coma | Range never extends; targets never hit | VIX <11 + gap <0.1% + normal/wide CPR (@0915) | `TIGHTEN_TARGET` 0.8R or `SKIP_DAY` |
| B4 | Gap misclassification | Gap-and-go treated as fill (or vice versa) | Gap ≥1.5×ATR% → fill probability rises; ≥2.5×ATR% → exhaustion likely (@0915, GIFT Nifty pre-confirms) | >2.5×ATR% gap → `FLIP_BIAS` toward fill/fade; 0.75–1.5× → standard split |
| B5 | Index divergence | Stock long fires while Nifty breaks *its* OR down; beta drags it back | Nifty futures vs its 15-min OR and VWAP at @SIG (realtime, YES) | Conflict → `VETO_DIRECTION`; Nifty mid-range → `HALF_SIZE` |
| B6 | Sector divergence | Stock fires against its sector index | Sector index vs its VWAP at @SIG | `HALF_SIZE`; hard veto only if index AND sector both conflict |
| B7 | Post-gap exhaustion | Second leg never comes after 3+ day move + gap | Gap direction = same as 3-day trend AND cumulative 3-day move >2×ATR (@0915) | `TIGHTEN_TARGET`, no runner, `HALF_SIZE` |
| B8 | Regime misclassification base rate | Narrow-CPR predicts trend but trend days are only ~20–25% of sessions | n/a — statistical | Accept lower trade count; judge filter on expectancy, not hit rate |

### C. Calendar & structural failures (NSE-specific — highest density of avoidable losses)

| # | Failure | Why ORB dies | Pre-entry detection (PIT) | Measure |
|---|---|---|---|---|
| C1 | **Results day** | OR width 2–3× normal; guidance whipsaw at 12:00+ calls | Results calendar (@0915, NSE/BSE announcements — publishable, EOD-OK) | `SKIP_DAY` or route to variant 16 with its rules. **Your deferral of this is the biggest known hole in v2.01.** |
| C2 | **Tuesday index expiry** | Pinning flows distort large-caps 13:30–15:00 | Calendar (@0915) | Afternoon breakouts on Nifty-50 names: `TIGHTEN_TARGET`; new entries after 13:30 only via variant 17/18 |
| C3 | **Monthly stock expiry (last Tuesday)** | High-OI strikes pin F&O stocks | Calendar + D-1 chain (@0915, EOD-OK) | If spot opens within 0.5% of max pain: breakout targets capped at pain; post-13:30 `SKIP` breakouts, fade-only |
| C4 | RBI MPC day | Policy at **10:00 IST** — mid-window whipsaw | RBI calendar (@0915) | No fresh entries 09:45–10:15 in banks/NBFCs; else `HALF_SIZE` |
| C5 | Budget day (Feb 1, incl. Saturday session) | Speech-driven 1%-in-minutes moves | Calendar | `SKIP_DAY` (or dedicated event playbook with 3× buffer) |
| C6 | Election counting / geopolitical gap | Index circuit risk; GIFT gap >3% | Calendar + GIFT Nifty at 08:50 (@0915) | \|GIFT gap\| >2% on event day → `SKIP_DAY` or index-coupled-only at quarter size |
| C7 | Muhurat / special / half sessions | 1-hour symbolic session; OR = whole session | Exchange holiday/session calendar (@0915) | `SKIP_DAY` config flag |
| C8 | **Locked circuit (non-F&O)** | Short entry → upper circuit lock → **cannot square off → auction/delivery catastrophe**; long → lower circuit → forced carry | Universe: price band ≤5% + gap already >60% of band (@0915) | Short side restricted to **F&O stocks only** (no fixed bands); non-F&O shorts `VETO`; band ≤5% names excluded entirely |
| C9 | ASM / GSM / T2T | No intraday leverage, broker blocks, manipulated opens | Exchange surveillance lists (published EOD, @0915 YES) | Universe exclusion, `SKIP_DAY` |
| C10 | F&O ban period (MWPL breach) | No fresh F&O positions; OI signals distorted; odd squeezes | NSE ban list (EOD, @0915 YES) | Derivatives gates off for that name; `HALF_SIZE`; never short |
| C11 | Index circuit breaker | 10/15/20% Nifty halt; all stops theoretical | GIFT + event calendar (@0915); intraday: Nifty move >7% (@SIG) | Pre-emptive `SKIP_DAY` on binary-event days; intraday → flatten everything, `ALERT_ONLY` |
| C12 | Ex-dividend false gap | Price drops by dividend amount — **not a real gap**; triggers fake GAP_DOWN | Corporate-action calendar (@0915, EOD-OK) | Effective gap% = raw gap% + dividend% (longs) before classification; bonus/split → rescale all prior-day levels. **Verify CTX-02 actually does this on the gap classifier, not just the price series.** |

### D. Microstructure & data failures

| # | Failure | Why ORB dies | Pre-entry detection (PIT) | Measure |
|---|---|---|---|---|
| D1 | Single-print first bar | 09:15–09:20 bar contains pre-open match print; ORH/L set by one illiquid trade | First bar volume <0.5× its 20-day median AND range >1.5× median (@SIG) | Shift OR window to 09:20–09:35 (dynamic OR) or `SKIP_DAY` |
| D2 | Opening auction imbalance | One-sided auction → immediate mean reversion through the OR | Pre-open indicative imbalance @09:07 (@0915, PARTIAL — broker feed) | Imbalance >2% of ADV → `DELAY_ENTRY` 15 min, require 2 closes |
| D3 | Missing/zero-volume bars | OR built on fabricated or partial data | Data-quality check on first 3 bars (@SIG) | Never impute → `SKIP_DAY` for that symbol |
| D4 | Wide spreads / thin books | Slippage eats 0.3–0.5R before you start | 20-day median daily value < ₹5 cr, or median spread proxy (bar range / volume z) elevated (@0915 from EOD) | Universe exclusion; slippage stress ×2 in backtest for that tier |
| D5 | Stop slippage | Backtest fills at stop price; reality gaps 0.2–0.5% in fast moves | n/a — backtest assumption | Stress-test: fills at stop + max(0.1%, 0.5× signal-bar range); kill any playbook whose edge survives only at zero slippage |
| D6 | Corporate-action misadjustment | Levels/gaps computed on unadjusted prices | CTX-02 audit; \|gap\| >20% guard you already have | EOD reconciliation job; mismatched symbol → `SKIP_DAY` until fixed |
| D7 | Feed lag at 09:30–09:35 | First minutes are the most lag-prone on retail APIs | Heartbeat/timestamp check (@SIG) | Stale >5s → `DELAY_ENTRY`; stale >60s → `ALERT_ONLY` |

### E. Statistical & research-process failures

| # | Failure | Why ORB dies | Detection | Measure |
|---|---|---|---|---|
| E1 | Small-n overfit | n<30/cell → noise promoted to playbook | Your V3 minimums | `ALERT_ONLY` until n≥30 OOS; no exceptions |
| E2 | Edge decay | Playbook's regime ended; expectancy silently negative | Rolling 60-trade expectancy per playbook <0 for 2 consecutive months (your ledger, PIT-clean) | Demote → `REDUCE_FREQUENCY` → retire |
| E3 | Multiple testing | Grid search + Holm is good but discovery bias remains across strategy *families* | Deflated Sharpe / White reality check on the full research history | Require 2 walk-forward folds + holdout for anything new (you have this — keep it as a hard gate) |
| E4 | EOD-derivatives lookahead | Using same-day chain/bhavcopy stats for same-day 09:15 decisions (published only that evening) | Data-lineage audit per feature | Every derivative feature stamped with availability timestamp; D-1 only at @0915 |
| E5 | Survivorship in promotion | Playbooks promoted before the core/backtester parity fix | Your P2/V5 | Re-validate all legacy playbooks through the fixed backtester before capital |

### F. Execution & tail failures

| # | Failure | Why ORB dies | Detection | Measure |
|---|---|---|---|---|
| F1 | Margin/peak-margin rejection | Order rejected at 09:31; position half-on | Pre-trade margin check vs VaR+ELM buffer 1.2× | Size to 80% of available margin; rejection → `ALERT_ONLY` |
| F2 | API/broker downtime | No exits possible | Heartbeat | Default state `ALERT_ONLY`; kill switch = market-square-off-all |
| F3 | Liquidity evaporation on news | Spreads 10× for minutes | Event calendar + D1 proxy | `DELAY_ENTRY` 15 min post-event |
| F4 | Forced carry (MIS failure) | Auto-square-off missed → overnight risk you never sized | Position reconciliation 15:05 | Hard flatten 15:10; any residual → alert + manual |

---

## TASK 3 — Derivatives overlay

**Reality check first:** your instrument is cash equity. Stock-level option chains are only statistically meaningful for the ~top 50–100 F&O names by option turnover; below that, OI is sparse and signals are noise. For everything else, use **index-level** derivatives as a regime overlay only. Nothing here should be a hard VETO except where marked — these are size/target modulators.

### A. Metric table

| Metric | Source & PIT availability | Computation | Thresholds (calibrate, don't worship) | Gate mapping |
|---|---|---|---|---|
| **India VIX level** | Realtime, @0915 YES | Exchange-published | <11 coma · 11–17 green · 17–22 whipsaw · ≥22 storm · ≥25 kill | VIX bucket scales buffer/size/targets (B1–B3) |
| **ΔVIX d/d** | EOD-OK | VIX(D-1)/VIX(D-2) −1 | ≥ +8% risk-off open | `HALF_SIZE` longs at open; favour shorts on ORL breaks |
| **GIFT Nifty gap** | 06:30 IST session; read 08:45–09:00, @0915 YES | GIFT last vs Nifty D-1 close | \|gap\| >1.5% → treat all large-caps as gap-day regime | Pre-loads GAP playbook before 09:15; C6 kill at >2% on event days |
| **Nifty futures basis** | Realtime futures vs spot, @SIG YES | Fut − spot (use **next-month** in expiry week; near-month basis → 0 into expiry and lies) | Discount >0.15% = aggressive hedging/shorting; premium >0.25% = crowded longs | Discount → `HALF_SIZE` longs, shorts full; extreme premium → `TIGHTEN_TARGET` longs (squeeze-fade risk) |
| **Index futures OI buildup** | EOD D-1, @0915 YES | Price/OI 4-cell: P↑OI↑ long buildup · P↓OI↑ short buildup · P↑OI↓ short covering · P↓OI↓ long unwinding | — | Long buildup → full-size longs. Short buildup → `HALF_SIZE` longs / favour shorts. **Short covering → `TIGHTEN_TARGET` longs (rallies fade)**. Long unwinding → `TIGHTEN_TARGET` shorts (bounces fade) |
| **Stock futures OI buildup** | EOD D-1, @0915 YES; top-100 F&O only | Same 4-cell per stock | — | Same-direction buildup + gap → gap-and-go probability up (full size); opposing buildup → `HALF_SIZE` |
| **PCR (OI), Nifty** | D-1 chain @0915 YES; live via broker @SIG YES (NSE public chain ~15-min delayed = PARTIAL) | ΣPut OI / ΣCall OI | <0.7 fear · 0.7–1.3 neutral · >1.3 complacency · >1.6 or <0.5 extreme | Size modulator only, **never VETO**: extremes → `HALF_SIZE` in the crowded direction + favour `FLIP_BIAS` reversals |
| **ΔPCR d/d** | EOD-OK | PCR(D-1)−PCR(D-2) with price direction | Rising PCR + rising price = healthy longs; falling PCR + rising price = weak rally | Confirms/undermines buildup cell; shift one size step |
| **PCR (volume)** | Intraday only, PARTIAL | Put vol / Call vol | Spikes on expiry; noisy | Ignore for gating; diagnostic only |
| **OI walls (strike OI)** | D-1 chain @0915 YES; live refresh PARTIAL | Strike with OI ≥1.5× adjacent strikes, within 1% of spot | — | Call wall above → `TIGHTEN_TARGET` at wall; breakout *through* wall requires 2 closes + RVOL ≥2; put wall below → mirror |
| **Max pain** | Computable from D-1 chain @0915 YES; decays intraday as OI shifts (PARTIAL after lunch) | Strike minimising option-holder payoff | Expiry day: spot within 0.5% of pain at 10:00 → pin regime; >2% away → drift-toward-pain after 13:30 | Pin: cap targets at pain, `SKIP` post-13:30 breakouts (variant 18). Non-expiry days: **weak signal in India — do not gate** |
| **ATM IV / expected move (EM)** | D-1 chain @0915 YES; live broker @SIG PARTIAL | EM = spot × IV × √(1/252) (or weekly ATM straddle/spot on expiry week) | **ORW/EM >0.45 by 09:30 → range mostly spent → `TIGHTEN_TARGET` 1R, no runner. ORW/EM <0.20 → expansion room → runner-eligible** | The single most honest target-setting variable you can add; replaces several ad-hoc width rules |
| **IV rank / percentile (IVR)** | EOD 1-yr history, @0915 YES | Percentile of IV vs trailing 252d | IVR >70 → event premium elevated; IVR <20 → complacency | IVR >70 without a known event → find the event or `HALF_SIZE`; IVR >70 pre-result → variant 16 only |
| **IV term structure** | Weekly vs monthly IV, @0915 YES (D-1) | Weekly IV > monthly IV by >3 vol pts = event priced in near leg | — | Confirms event-week caution; expiry-week breakouts get `TIGHTEN_TARGET` (crush tailwind fades moves less than expected — actually helps cash; use for sizing only) |
| **GEX / gamma flip** | Computed: Σ(Call OI×Γ) − Σ(Put OI×Γ), dealer-short assumption. @SIG PARTIAL (needs live chain; public data 15-min delayed); EOD YES for backtests | Per-strike gamma × OI; flip = strike where net GEX crosses 0 | Spot above flip (positive GEX) → dealers dampen → mean reversion. Below flip (negative) → dealers amplify → trend | Positive GEX: `HALF_SIZE` breakouts + `TIGHTEN_TARGET`. Negative GEX: full size, runner-eligible, `WIDEN` trail. **Reliability: LOW-MEDIUM in India** — dealer positioning is assumed, not published; treat as experimental until your own OOS ledger proves it (n≥30) |
| **Charm / vanna flows** | Derived, expiry-adjacent only | Delta-decay hedging into close | Last 2 sessions before expiry | Directional drift into 13:45–15:00 with the day's dominant side; inform trail tightness only. Second-order — do not gate |
| **Rollover %** | EOD during expiry week, @0915 YES | OI carried to next series / total OI | >80% strong conviction carry; <60% uncertainty | High rollover + trend-aligned → runner-eligible expiry week; low rollover → `HALF_SIZE` |
| **Participant-wise OI (FII/DII/Pro/Client)** | EOD, @0915 YES | FII index-fut long/short ratio | Extremes (>2.5 or <0.7) | Slow regime tag only; weekly, not daily. No trade gates |
| **F&O ban list / MWPL utilisation** | EOD, @0915 YES | NSE published | Ban = name in ban; MWPL >85% = approaching | C10 gates |

### B. Expiry dynamics under the Tuesday regime (2026)

1. **Weekly (Nifty) = every Tuesday.** Pinning of index heavyweights (Reliance, HDFC Bank, ICICI Bank etc. — the names that dominate Nifty option hedging) concentrates Monday close → Tuesday 15:30. If you trade index-heavyweight cash ORB, Tuesday afternoon is structurally mean-reverting when spot is near pain.
2. **Monthly (all F&O stocks) = last Tuesday.** The stock-level pinning day and the index weekly now *coincide* on month-ends → compounded pinning on last Tuesdays; also the highest OI-wall reliability day of the month.
3. **Gamma build runs Fri → Tue; Wed–Fri is post-expiry OI rebuild** — OI walls are least reliable Wednesday/Thursday (fresh, shifting OI), most reliable Monday/Tuesday.
4. **Expiry-trend exception:** if the morning range on expiry day already exceeds 1×ATR by 12:00, charm/delta-hedge flows *accelerate* the trend into the close — that is the day to run variant 17 with a runner, and the worst day to fade (variant 18 veto condition).
5. **Basis and IV near expiry:** near-month basis → 0 and weekly IV → crush; always read basis/term-structure off the *next* series in expiry week or you'll gate on arithmetic artefacts.

### C. What is NOT reliably available point-in-time (be honest in the ledger)

- Public NSE option-chain web data: ~15-min delayed and rate-limited → **not valid for 09:30 decisions**; broker API chain snapshots only.
- True dealer positioning: not published at strike granularity → GEX is a model, not a measurement.
- Participant-wise OI: EOD only → regime tag, never an intraday trigger.
- Stock option OI outside top-100 names: too sparse — treat as absent.

---

## TASK 4 — Protective measures, decision table, and verdicts on your design

### A. Consolidated decision table (condition → measure)

| # | Condition (all PIT-timed) | Measure |
|---|---|---|
| 1 | VIX ≥25, or event day with \|GIFT gap\| >2% | `SKIP_DAY` |
| 2 | VIX 17–22 | Buffer ×1.5, `HALF_SIZE`, top-liquidity names only |
| 3 | VIX <11 + gap <0.1% | `TIGHTEN_TARGET` 0.8R or skip |
| 4 | ORW <0.25×ATR without NR7/narrow-CPR/gap confluence | `SKIP_DAY` |
| 5 | ORW >1.2×ATR | Breakout family `VETO`; ORR-only, ORM stop, 1R target |
| 6 | Signal-bar RVOL <1.5 | `DELAY_ENTRY` (2 closes) |
| 7 | Signal within 0.1% of PDH/PDL or OI wall + wick >60% of bar | `DELAY_ENTRY`, `HALF_SIZE` |
| 8 | Nifty futures on opposite side of its VWAP/15-min OR at signal | `VETO_DIRECTION` |
| 9 | Nifty mid-range (no side) at signal | `HALF_SIZE` |
| 10 | Index futures short buildup (D-1) + long signal | `HALF_SIZE`; short-covering rally + long → `TIGHTEN_TARGET` |
| 11 | Results day for the symbol | `SKIP_DAY` (or variant 16 protocol) |
| 12 | RBI MPC day, rate-sensitive symbol, 09:45–10:15 | `DELAY_ENTRY` post-10:15 |
| 13 | Tuesday expiry + spot within 0.5% of max pain at 10:00 (index-heavy names) | `TIGHTEN_TARGET` to pain; no new breakouts after 13:30 |
| 14 | Last-Tuesday monthly expiry + morning range >1×ATR by 12:00 | Runner-eligible trend protocol (variant 17); **veto fades** |
| 15 | ORW/EM >0.45 at 09:30 | `TIGHTEN_TARGET` 1R, no runner |
| 16 | ORW/EM <0.20 at 09:30 + trend confluence | Runner-eligible, trail after 1R |
| 17 | Spot below GEX flip (negative GEX) | Full size, wider trail; above flip → `HALF_SIZE` + tight targets *(experimental until OOS-proven)* |
| 18 | Non-F&O stock, short signal | `VETO_DIRECTION` (circuit-lock tail) |
| 19 | Symbol on ASM/GSM/T2T/F&O-ban list | Universe exclusion / `SKIP_DAY` |
| 20 | Ex-dividend date | Gap% adjusted by dividend% before GAP classification |
| 21 | Both ORH and ORL broken within 60 min | `REDUCE_FREQUENCY` — done for the day |
| 22 | First stopped trade was a trap (stop within 15 min) + price re-closes beyond level + index aligned | One conditional re-entry allowed (REENTRY-01) |
| 23 | Signal time leaves < 1.5× playbook median time-to-1R before 15:10 | `SKIP` signal |
| 24 | Missing/stale/zero-volume data in first 3 bars or at signal | `SKIP_DAY` / `ALERT_ONLY` — never impute |
| 25 | Rolling 60-trade expectancy <0 for 2 months (per playbook) | Demote playbook → `REDUCE_FREQUENCY` → retire |

### B. Top 10 additions, ranked by (expected impact ÷ effort)

| Rank | Addition | Why this rank |
|---|---|---|
| 1 | **Event & corporate-actions calendar gate** (results, RBI, Budget, ex-dividend gap adjustment, special sessions) | Kills the single largest loss cluster in single-stock ORB (C1, C12). Pure calendar data, EOD-OK, a weekend of work. Your memo deferred this — **un-defer it.** |
| 2 | **Index-alignment gate** (Nifty futures vs its VWAP + 15-min OR at signal) | Removes the biggest class of single-stock fake-outs (B5). Realtime, PIT-clean, ~20 lines of code. |
| 3 | **Universe hygiene** (exclude T2T/ASM/GSM; shorts F&O-only; liquidity floor ₹5 cr/day; band check) | Eliminates the catastrophic tail (C8, C9) — the only failure class that can cost more than a day's risk budget. |
| 4 | **Expected-move gate** (ORW/EM from D-1 ATM IV) | Replaces ad-hoc width/target rules with the market's own range forecast (rows 15–16). Moderate effort: needs historical chain snapshots. |
| 5 | **RVOL upgrade of volume confirm** (20-day same-time-bucket average) | You already store 5m volume; this is the best-documented ORB edge filter in the literature. |
| 6 | **Conditional re-entry (REENTRY-01)** — 1 re-entry/day, only on trap-signature + re-close + index alignment | Recovers trend-day P&L that "one trade per day" throws away, without opening the overtrading floodgates. |
| 7 | **Afternoon playbook as a *separate* validated strategy** (13:00–13:45 range, entries 13:45–14:30) | Captures the second Indian trend window and Tuesday-expiry moves your 11:30 cutoff discards — without contaminating morning-playbook statistics. |
| 8 | **VIX regime scaler** (buffer/size/target multipliers per VIX bucket) | One mechanism that robustifies every other gate across regimes (B1–B3). |
| 9 | **Tuesday expiry protocol** (pinning detector, post-13:30 breakout lockout, last-Tuesday trend exception) | Cheap calendar + D-1 chain logic; protects you on the 4–5 most distorted sessions per month. |
| 10 | **OI-wall target capping** (top-100 F&O names) | Improves exits, which is where ORB systems bleed quietly. EOD-OK data. |

*Deliberately NOT in the top 10:* GEX/gamma-flip gating (assumption-stacked in India — paper-trade it first), participant-wise OI (too slow), charm/vanna (second-order), PCR as anything beyond a size modulator.

### C. Verdicts on your three flagged design choices

**1. "One trade per day" — mostly right, slightly wrong.** As a risk brake it's correct: ORB's death spiral is chop-day overtrading, and A3/#21 already handles the chop signature. Where it's wrong: it treats a *trap stop-out on a trend day* identically to a *legitimate loss on a chop day*. The first 30 minutes produce frequent shakeout-then-go sequences; your system watches the trend leave after being right about direction. Fix is not "more trades" — it's **one conditional re-entry** (#22) plus your already-correct v2.01 rule that vetoed signals don't consume the day. Also add #23 (minimum time-to-target) — a signal consumed at 11:25 with no room to reach 1R is a wasted bullet.

**2. 11:30 entry cutoff — right rule, wrong implementation.** The cutoff correctly protects you from 11:30–13:30 lunch chop (the genuinely dead window in India). But a *hard* cutoff throws away the second trend window (13:45–15:00), which on Tuesday expiries and Europe-open days is often the *best* window. Don't extend the window — that mixes two regimes into one playbook and contaminates your walk-forward stats. Ship variant 17 as a **separate playbook with its own validation**, and let each playbook carry its own session window.

**3. Range-VWAP → session-VWAP — directionally correct, three caveats.**
- (a) Session VWAP before ~09:45 is barely more informative than price itself (few prints); requiring "price above VWAP" at a 09:31 signal is close to vacuous. Fix: VWAP confirm active only after 6 completed bars (09:45+); before that, use *VWAP slope* from bar 3 onward or skip the confirm and pay for it with HALF_SIZE.
- (b) On gap days, session VWAP is dragged toward the gap origin — price can sit "above VWAP" all day while fading the entire move. Fix: on gap days (|gap| ≥0.75×ATR%), anchor a second VWAP to PDC and require agreement, or use the opening-drive/ORM family of confirms instead.
- (c) Position-vs-VWAP is binary and weak; **VWAP slope + 1σ bands** are strictly more informative at zero extra data cost — bands double as targets on TIGHTEN_TARGET days.

### D. Other things wrong / risky in the current spec

1. **Stop inconsistency:** the system description says breakout stop = opposite OR side, but your memo examples use ORM stops. On 0.8–1.2×ATR wide-OR days, opposite-side stops double R and halve size — and if the backtester doesn't match the production rule exactly, every R-multiple in your ledger for those playbooks is fiction. Pick one per playbook, encode it in the playbook spec, and re-run V5 parity. This is your E3 bug class; treat it with the same paranoia.
2. **Precedence ambiguity:** trail_after_1r vs TIGHTEN_TARGET vs pinning-cap can all fire on the same trade. Define a strict precedence order in the approval flow (safety exits > calendar caps > playbook targets > trails).
3. **Buffer not volatility-scaled:** a flat 0.05% buffer is inside the 5m noise floor for high-beta names and for everything when VIX >17 (B1). Scale it.
4. **ATR availability (your S9):** correct catch. Persist a D-1 EOD context snapshot (ATR, CPR, PDH/L/VA, buildup cell, IV/EM, event flags) as the *only* input the morning pipeline reads — that single pattern makes PIT discipline structural instead of aspirational.
5. **15:10 time stop:** correct; keep the ≥10-minute buffer ahead of broker MIS auto-square-off (15:15–15:20) and the 15:00–15:30 closing-VWAP games.

### E. Honest limits

- Trend days are ~20–25% of NSE sessions; every filter above trades *frequency* for *per-trade expectancy* — judge them on expectancy × opportunity, not hit rate, and only after n≥30 OOS per regime cell (your own V3 rule).
- GEX, charm, and participant-flow gates are the weakest links here (assumption-stacked, EOD or delayed in India). They're marked experimental; don't let them touch size until your ledger proves them.
- All thresholds (VIX 17/22/25, ORW 0.25/1.2×ATR, ORW/EM 0.20/0.45, PCR 0.7/1.3, pain-distance 0.5%) are priors from Indian microstructure conventions — calibrate each against your own 5m archive before promoting from `ALERT_ONLY` to gating.
