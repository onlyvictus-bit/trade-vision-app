# Kimi External Review — ORB v2.01 Consolidated Deliverable (Tasks 1–4) — VERBATIM ARCHIVE

> **Provenance:** third Kimi submission, 2026-09-03 — the consolidated complete deliverable (18 variants, ~35-row failure taxonomy, full derivatives overlay, 50-row decision table, ranked top 10, two pre-live must-fixes). Saved verbatim, byte-exact (line endings preserved), per explicit user instruction — no edits, no omissions, no paraphrase. Source: `pasted-text-20260903-111252-515023ec.txt`.
> **Verification + adoption:** `ORB_V201_VERIFIED_ANSWER.md` §8 (what is new vs the two prior submissions, what is a third independent confirmation, what changed in the calibration register) · memorandum **v2.4** · plan **§10 addendum** · findings **§9 fifth pass**.
> **Fact-check note:** this submission again carries the "Tuesday — verify" expiry caveat with no successful web verification of its own. Our independent verification (SEBI circular SEBI/HO/MRD/TPD-1/P/CIR/2025/76 — NSE expiries Tuesday effective 01-Sep-2025) stands and supersedes; the calendar-file mandate (memo EXP-07) already covers its engineering conclusion.

---

## Submission (verbatim, byte-exact copy of source)

# ORB System Review — Complete Deliverable (Tasks 1–4)

**Legend (used throughout):** OR = opening range (09:15–09:30); ORH/ORL/ORM = OR high/low/mid; ORW = OR width; ATR = ATR(14) from D-1 close; PDC = previous day close; PDH/PDL = previous day high/low; RVOL = volume vs 20-day same-time average; CPR = central pivot range; PIT = point-in-time availability. **Measure codes:** SKIP_DAY, DELAY_ENTRY, HALF_SIZE, TIGHTEN_TARGET, WIDEN_STOP, FLIP_BIAS, VETO_DIRECTION, ALERT_ONLY.

⚠️ **Expiry-day caveat:** NSE expiry is now **Tuesday** (weekly Nifty; monthly stock F&O = last Tuesday), BSE Thursday — from training data; my web verification failed, so confirm against the live NFO calendar. Drive expiry logic from a calendar file, never `dayofweek` constants.

---

## TASK 1 — ORB Variants

| # | Variant | Entry | Stop | Target | Best regime | Worst regime |
|---|---|---|---|---|---|---|
| 1 | **Classic ORB-15** | 5m close beyond ORH/ORL + 0.05–0.1% buffer | Opposite OR side (ORM if ORW > 0.6×ATR) | 2R or 15:10 | VIX 11–17, index-aligned | Chop, VIX <11 |
| 2 | **ORB-5 (micro)** | 5-min OR break, entry from 09:20 | ORM | 1.5R | High-vol trend days, expiry | Noisy open, wide spreads |
| 3 | **ORB-30** | 30-min OR break | Opposite OR side | 2.5R | Post-event clarity, swing days | Fast V-reversals |
| 4 | **Volume-confirmed ORB** | Variant 1 + breakout-bar RVOL ≥ 1.5× | Same as 1 | 2R | All regimes (filter) | Low-float runners (volume lags price) |
| 5 | **VWAP-filtered ORB** | Longs only above session VWAP (post-10:00); pre-10:00 use ORM | Same as 1 | 2R | Trend days | Gap days pre-10:00 (VWAP contaminated) |
| 6 | **Index-aligned ORB** | Only in direction of Nifty vs its OR/VWAP | Same as 1 | 2R | All (raises hit rate) | Stock-specific news days (blocks good trades — allow exemption) |
| 7 | **Narrow-OR expansion** | ORW < 0.25×ATR + NR7 + CPR < 0.2×ATR; buffer entry | ORM | 3R | VIX coma 11–13, post-consolidation | Event days (false compression) |
| 8 | **Wide-OR reduced** | ORW 0.75–1.0×ATR | ORM | 1.5R, HALF_SIZE | Defensive only | VIX >20 (skip instead) |
| 9 | **Gap-and-go** | Gap 0.25–0.75×ATR with catalyst; first pullback holds ORH, then break | Below ORH/ORM | 2R | Continuation gaps on news | Gaps >1.5×ATR (exhaustion) |
| 10 | **Gap-fade (ORR)** | Gap >1.5×ATR; enter on failure back inside OR toward PDC | Beyond opening extreme | PDC, then session VWAP | VIX >17 overreaction opens | Genuine news trend days |
| 11 | **False-breakout reversal (ORB trap)** | Breakout fails ≤10 min, 5m close back inside OR; enter opposite on reclaim | Beyond failed extreme | Opposite OR side + 1R extension | Chop, range days | Trend days (trap → continuation) |
| 12 | **Pullback entry (retest)** | After breakout, first retest of ORH/ORL that holds on 5m close | Below retest low | 2R | Orderly trends | V-moves (never retest — missed trade) |
| 13 | **Second-chance re-entry** | Stopped ≤20 min, price re-closes beyond OR with ≥1.5× volume; max 1, before 11:30 | Same as original | 2R | Shakeout-then-trend days | Chop (donates twice) |
| 14 | **Post-result ORB** | Result day: OR = 09:15–09:45, entry ≥09:45 | ORM | 1.5R | Post-result drift (PEAD) | Pre-result gambling; ambiguous results |
| 15 | **PDH/PDL breakout** | 5m close beyond PDH/PDL + buffer | Day-OR mid | 2R | Trend continuation days | Inside days |
| 16 | **Expiry-day ORB** | Variant 1 + one extra close confirm; no entries after 14:00 | Same as 1 | Capped at max pain / OI wall | Expiry trend days (runners post-14:00) | Pinning days |
| 17 | **Afternoon range breakout** | Day range 09:15–13:30 as new "OR"; entry 13:45–14:15 only | Mid-range | 1–1.5R, hard flat 15:00 | Europe-open resumption, expiry days | Lunch-chop continuation |
| 18 | **Extension no-chase rule** | Price >1.0×ATR from OR by 11:00 with no pullback → no entry | — | — | Discipline layer | Fading strong trends (don't) |

---

## TASK 2 — Failure Scenario Taxonomy

| Cat | Failure mode | Mechanism | Detection (threshold) | Measure |
|---|---|---|---|---|
| **A. Regime** | Chop day | Overlapping 5m bars, no displacement | 2 failed breakouts same side <11:00 | SKIP_DAY remainder |
| A | VIX coma | No range expansion fuel | VIX <11 | TIGHTEN_TARGET 0.8R / NR7-only |
| A | VIX spike | Whipsaw both directions | VIX 20–25, or ΔVIX +8% intraday | SKIP_DAY small/mid; cancel pendings |
| A | Gap exhaustion | Gap >1.5×ATR fades into OR | Gap % vs ATR at 09:15 | FLIP_BIAS |
| A | News shock | Headline mid-trade | ΔVIX +8% or 5m range >2× ATR | Cancel pendings, tighten stops |
| **B. Signal** | False breakout (trap) | Liquidity grab beyond ORH | Close back inside OR ≤10 min | Reverse via variant 11, or stand down |
| B | OR too wide | Risk/reward broken | ORW >1.0×ATR | SKIP_DAY |
| B | OR too narrow | Noise breakouts | ORW <0.25×ATR | Require volume hammer; 3R target |
| B | First-bar contamination | Pre-open match print in 09:15–09:20 bar | Bar volume z >4 or range >2× median | Re-base OR to 09:20–09:35 |
| B | Level staleness | OR levels used too late | Signal after 11:30 | No entry (morning system) |
| B | Double-stop whipsaw | ORM stop in chop | Stop-out then re-close ≤20 min | Max 1 re-entry (variant 13) |
| **C. Event** | Result-day whipsaw | Spread blowout, both-side sweeps | Event calendar | DELAY_ENTRY 09:45, 30-min OR |
| C | RBI MPC ~10:00 | Announcement inside entry window | Calendar | No entries 09:45–10:15 |
| C | Budget/election | Multi-% swings, circuit risk | Calendar | SKIP_DAY or 2× confirms |
| C | Ex-dividend misread | Mechanical gap read as signal | Corp-actions feed D-1 | Adjusted gap = raw + div% |
| **D. Instrument** | Circuit lock | Locked band → auction/delivery penalty on shorts | Band ≤10% for shorts | Structural exclusion |
| D | ASM/GSM/T2T | Margin/trade restrictions, manipulation risk | Exchange lists (weekly) | Structural exclusion |
| D | Illiquidity/slippage | Slippage >0.15% vs signal | 60-day turnover <₹5cr, spread >0.1% | SKIP_DAY |
| D | F&O ban | No hedge capacity, distorted flows | NSE ban list EOD | SKIP_DAY |
| **E. Data/Exec** | Feed lag / bad ticks | Phantom breakout | Cross-check 2 sources; tick vs 1m close | Halt on mismatch |
| E | Order rejection / broker square-off | MIS auto-square ~15:15–15:20 | Broker clock | Hard flat 15:10 |
| E | PIT violation (lookahead) | Using EOD data intraday | Audit: every input timestamped | Pipeline fix |
| E | Backtest/live mismatch (E3) | Different stop/gap-fill logic | Reconciliation diff ≠ 0 | Single shared rule engine |
| **F. Derivatives** | Expiry pinning | Dealer hedging glues spot to pain | Spot ≤0.5% of pain on expiry | TIGHTEN_TARGET / ORR bias |
| F | Gamma squeeze | Dealer chase amplifies move | Negative GEX + breakout | Let runners run (trail) |
| F | OI wall rejection | Call/put wall caps move | Target beyond wall | Cap target 1 tick below wall |
| F | Rollover distortion | Basis flips sign mechanically | >30% OI moved to next month | Use next-month basis |
| **G. Statistical** | Edge decay | Regime change kills setup | 60-day rolling expectancy <0 ×2 months | ALERT_ONLY demotion |
| G | Overfit | 9-strategy grid, multiple testing | Holm / deflated Sharpe fail | Demote variant |
| G | Small sample | n <60 OOS occurrences | Trade log | ALERT_ONLY until qualified |

---

## TASK 3 — Derivatives Overlay (complete)

| Module | Metric | Threshold / rule | Action | PIT |
|---|---|---|---|---|
| Vol regime | India VIX | <11 / 11–14 / 14–17 / 17–20 / 20–25 / >25 | 0.8R target · none · buffer ×1.25 · ×1.5+HALF · SKIP small/mid · SKIP all | YES (realtime) |
| Vol regime | ΔVIX | +8% intraday vs D-1 close | Cancel pendings | YES |
| IV | IV Rank (stock, monthly) | IVR >60 pre-result → crush expected | Post-result variant only, from 09:45 | YES (D-1 chain) |
| IV | Term structure | Near-month IV > next-month by >5 vol pts, no earnings | Hidden event → HALF_SIZE/skip | YES (D-1) |
| IV | Skew (index 25Δ) | Put–call spread spiking | Soft veto on longs; index only (stock skew too noisy) | Computed, optional |
| IV | IV crush post-result | Uncertainty resolved | Post-result variant safe after 09:45 | YES |
| PCR | Index PCR (OI) | >1.3 or <0.7 | Contrarian soft veto | YES D-1; intraday PARTIAL (NSE ~15-min delay) |
| OI | Buildup classification | Price↑+OI↑ long buildup; Price↓+OI↑ short buildup; Price↓+OI↓ long unwind; Price↑+OI↓ short cover | Directional tilt; opposite buildup → VETO_DIRECTION | PARTIAL (broker API OK) |
| Max pain | Stock pain | Spot ≤0.5% of pain on expiry day | TIGHTEN_TARGET to pain; ORR bias | Computed D-1; intraday PARTIAL |
| GEX | Dealer gamma | Positive → damped moves (fade OK); negative → amplified (ORB OK) | Regime tag only — model-dependent, not a hard gate | Computed/PARTIAL |
| Greeks | Charm/vanna | Expiry-day delta decay | Expiry-only modifier: after 14:00 trail runners; no fresh entries | Calendar |
| Expiry | Weekly expiry (Nifty only; **Tuesday — verify**) | Expiry day | +1 close confirm on all signals | YES (calendar) |
| Expiry | Monthly stock F&O expiry (**last Tuesday — verify**) | Expiry day | Pain rules; breakouts need ≥1.5× volume; no 14:00+ entries | YES |
| Expiry | Post-expiry session | Day after expiry | Tag as high-quality ORB day (gamma unclenched) | YES |
| Expiry | Rollover % | >85% + positive basis | Longs carried with conviction → bullish tilt | YES (EOD) |
| Basis | Stock futures basis | >+15 bps near-month = leveraged long buildup; negative = short buildup **or dividend** | Directional tilt; **always dividend-adjust** | YES (fut+spot ticks) |
| Basis | Contract selection at rollover | >30% OI in next month | Use next-month basis | YES (D-1 OI) |
| Pre-open | GIFT Nifty | Implied gap >1.5×ATR → fade risk; >2.5% index gap | FLIP_BIAS / SKIP_DAY small-mid | YES (trades from ~06:45 IST) |
| Flows | FII index-futures L/S ratio | Short ratio >80% → squeeze risk; <30% → crowded longs | Bullish tilt / bearish tilt | YES (NSE EOD) |

---

## TASK 4a — 50-Row Decision Table

| # | Condition | Detection (threshold) | PIT | Measure |
|---|---|---|---|---|
| 1 | VIX coma | VIX <11 | YES | TIGHTEN_TARGET 0.8R / NR7-only |
| 2 | VIX normal | 11–14 | YES | No adjustment |
| 3 | VIX elevated | 14–17 | YES | Buffer ×1.25 |
| 4 | VIX high | 17–20 | YES | Buffer ×1.5 + HALF_SIZE |
| 5 | VIX kill zone | 20–25 | YES | SKIP_DAY small/mid; large-cap needs 2× volume |
| 6 | VIX crisis | >25 | YES | SKIP_DAY all |
| 7 | Vol shock | ΔVIX +8% intraday | YES | Cancel pendings |
| 8 | OR too wide | ORW >1.0×ATR | YES | SKIP_DAY |
| 9 | OR wide | ORW 0.75–1.0×ATR | YES | HALF_SIZE + ORM stop + 1.5R |
| 10 | OR normal | ORW 0.25–0.75×ATR | YES | Standard |
| 11 | OR narrow | ORW <0.25×ATR | YES | Volume hammer required; target 3R |
| 12 | Compression setup | NR7 + CPR <0.2×ATR | YES | Priority day (variant 7) |
| 13 | First-bar anomaly | 09:15–09:20 volume z>4 or range >2× median | YES | Re-base OR to 09:20–09:35 |
| 14 | OR straddles PDC | PDC inside OR | YES | HALF_SIZE (contested open) |
| 15 | Gap extreme | \|gap\| >1.5×ATR | YES | FLIP_BIAS (variant 10) |
| 16 | Gap moderate | 0.75–1.5×ATR | YES | No chase; pullback entry only (variant 12) |
| 17 | Flat open | Gap <0.25×ATR | YES | Standard |
| 18 | GIFT/open divergence | >0.3% vs actual open | YES | DELAY_ENTRY 5 min |
| 19 | Index gap extreme | GIFT implies >2.5% | YES | SKIP_DAY small/mid |
| 20 | Ex-dividend day | Corp-actions feed D-1 | YES | Adjusted gap = raw + div% |
| 21 | Nifty aligned | Same side of index OR/VWAP | YES | Full size |
| 22 | Nifty conflict | Opposite side | YES | VETO_DIRECTION |
| 23 | Nifty mid-range | Index inside its OR | YES | HALF_SIZE |
| 24 | Sector divergence | Sector index opposite >0.5% | YES | HALF_SIZE |
| 25 | Volume pass | RVOL ≥1.5× | YES | Pass |
| 26 | Volume fail | RVOL <1.0× | YES | DELAY_ENTRY until recovery, else skip |
| 27 | Climax, no follow-through | Breakout bar z>4, no progress in 3 bars | Intraday | Scratch/exit early |
| 28 | Post-breakout dry-up | Next 3 bars <0.7× OR avg volume | Intraday | TIGHTEN_TARGET / scratch |
| 29 | Early signal | <09:45 | YES | HALF_SIZE on gap days; else standard |
| 30 | Prime window | 09:45–10:45 | YES | Standard |
| 31 | Late window | 10:45–11:30 | YES | TIGHTEN_TARGET 1.5R (time-to-close) |
| 32 | Past cutoff | >11:30 | YES | No new entries |
| 33 | Time stop | 15:10 | YES | Hard flat |
| 34 | Result day | Calendar | YES | DELAY_ENTRY 09:45; 30-min OR; 1.5R |
| 35 | Result D-1 | Calendar | YES | Tag next-day gap regime; no size-up |
| 36 | RBI MPC day | Calendar (announcement ~10:00) | YES | No entries 09:45–10:15; buffer ×1.5 after |
| 37 | Budget/election day | Calendar | YES | SKIP_DAY or 2× confirms |
| 38 | Weekly expiry | Calendar (**Tue — verify**) | YES | +1 close confirm |
| 39 | Monthly stock expiry | Calendar (**last Tue — verify**) | YES | Pain rules; no 14:00+ entries |
| 40 | PCR extreme | Index PCR >1.3 or <0.7 | YES (D-1) | Contrarian soft veto |
| 41 | Max pain proximity | Spot ≤0.5% of pain on expiry | Computed | TIGHTEN_TARGET / ORR bias |
| 42 | OI wall at target | Target beyond call/put wall | PARTIAL | Cap target 1 tick below wall |
| 43 | Basis extreme | >+15 bps or negative (div-adjusted) | YES | Directional tilt |
| 44 | FII crowding | Index-fut short ratio >80% / <30% | YES (EOD) | Squeeze tilt long / crowding tilt short |
| 45 | F&O ban | NSE ban list | YES | SKIP_DAY |
| 46 | ASM/GSM/T2T | Exchange lists | YES | SKIP_DAY (structural) |
| 47 | Narrow circuit band | Band ≤10% for shorts | YES | SKIP_DAY shorts |
| 48 | Illiquidity | Turnover <₹5cr (60d) or spread >0.1% | YES | SKIP_DAY |
| 49 | Chop signature | 2 failed breakouts same side <11:00 | Intraday | SKIP_DAY remainder |
| 50 | Edge decay / small sample | 60-day expectancy <0 ×2 months, or n<60 OOS | YES (own log) | ALERT_ONLY |

## TASK 4b — Ranked Top 10 Additions

| Rank | Addition | Rule | Effort | Impact | Why |
|---|---|---|---|---|---|
| 1 | Event-calendar gate | Results/MPC/Budget/elections → SKIP or DELAY 09:45 | LOW | HIGH | Kills fattest whipsaw tails; MPC lands ~10:00 inside your window |
| 2 | Universe hygiene filter | Exclude ASM/GSM/T2T/F&O-ban; shorts need ≥20% band; ₹5cr turnover min | LOW | HIGH | Removes locked-circuit catastrophic carry |
| 3 | Session VWAP + side veto | Full-session VWAP; post-10:00 require close on VWAP side; pre-10:00 use ORM | LOW | HIGH | Range-VWAP confirm is vacuous |
| 4 | Ex-dividend gap adjustment | effective_gap = raw + div% | LOW | MED | Kills false gap-regime tags |
| 5 | Nifty-alignment gate | Index vs its OR/VWAP → VETO_DIRECTION / HALF_SIZE | LOW-MED | HIGH | Largest single filter in ORB literature |
| 6 | VIX-scaled buffers | Buffer = max(0.05%, k × VIX-scaled 5m σ) | MED | MED-HIGH | One parameterized rule replaces ad-hoc widening |
| 7 | Conditional re-entry | ≤1 re-entry: stopped ≤20 min + re-close beyond OR with ≥1.5× volume; never after 11:30 | MED | MED-HIGH | Fixes one-trade/day flaw without opening floodgates |
| 8 | OI-wall capping + expiry pinning | Target ≤1 tick below wall; expiry ±0.5% of pain → fade bias post-13:30 | MED | MED | Reliable target discipline for F&O universe |
| 9 | RVOL filter | Signal needs ≥1.5× 20-day same-time volume | LOW-MED | HIGH | Kills drift breakouts; classic ORB edge filter |
| 10 | Expectancy monitor + discovery hygiene | 60-day expectancy <0 ×2 months → ALERT_ONLY; Holm/deflated-Sharpe on grid | MED | MED | Guards edge decay + multiple-testing overfit |

**Execution order:** #1–4 this week (all LOW effort) → #5, #9 next sprint (raw-edge filters) → #6–8 → #10 as standing infrastructure. Two pre-live must-fixes remain from the flags: the **stop-rule inconsistency** (opposite-side vs ORM — one deterministic rule in both backtester and live path) and the **expiry-calendar cutover** (Tuesday — verify, calendar-file driven).