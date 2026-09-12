# TRADE VISION — ORB Intraday Stock + Commodity Scope and Flow Hardening

**Repository:** `onlyvictus-bit/trade-vision-app`  
**Planning branch:** `m4-d6-orchestration-redesign`  
**Document date:** 2026-09-12  
**Status:** CANONICAL SCOPE ADDENDUM / FUTURE BUILD REQUIREMENT  
**Parent specification:** `docs/ORB_AFRE_CANONICAL_FUTURE_BUILD_PLAN_2026-09-10.md`

---

## 1. Scope decision

The ORB upgrade is **not** intended to run blindly across every stock in the market at runtime.

The target runtime universe is deliberately narrow:

1. **Selected intraday NSE equity candidates** supplied by the user or an approved pre-market/Trendforge intake after point-in-time-safe screening such as major gap-up, major gap-down, abnormal/high pre-market participation, unusual volume, event relevance, or other explicit candidate reason.
2. **Selected commodity futures/contracts** supplied by the user or an approved candidate-intake process.
3. Historical research may run over a wider stored universe to build and re-prove playbooks, but daily runtime guidance should operate only on the current approved candidate set.

The candidate shortlist is an **upstream attention filter**, not a trade signal and not final direction authority. A gap-up candidate may become continuation, fade/reversal, or `WAIT`; a gap-down candidate may do the same. Candidate selection must never mean “high chance therefore trade.”

---

## 2. Candidate Intake Contract — add before ORB

Create a first-class `ORB_CANDIDATE_INTAKE` contract before the context brain.

Minimum fields:

- instrument identity / symbol;
- instrument type: `NSE_EQUITY`, `NSE_DERIVATIVE`, `COMMODITY_FUTURE`, or future registered type;
- exchange / venue;
- contract identity when applicable;
- session date / session identity;
- `as_of` timestamp;
- source: user shortlist, Trendforge, approved scanner, or other registered source;
- selection reasons, for example `GAP_UP`, `GAP_DOWN`, `HIGH_PREMARKET_VOLUME`, `ABNORMAL_VOLUME`, `EVENT`, `MANUAL_RESEARCH_CANDIDATE`;
- observed pre-market/pre-session metrics only when actually available;
- reference close/settlement identity;
- data-quality/availability states;
- provenance;
- snapshot hash;
- intake version.

Rules:

1. A user-supplied symbol is enough to include an instrument in the analysis queue; it is not enough to create bullish/bearish evidence.
2. If numeric pre-market gap/volume metrics are supplied, they must have timestamp/provenance and must be available before the ORB decision.
3. Missing pre-market volume must remain `UNAVAILABLE`, not zero.
4. Candidate selection itself must not leak future-session performance into research.
5. When evaluating a strategy specifically conditioned on “pre-market selected candidates,” historical backtests must reconstruct the same selection rule point-in-time. Backtesting every historical day and then claiming results for a pre-market-screened strategy is selection-bias leakage.
6. Manual/user candidate intake and Trendforge intake must use the same downstream canonical ORB contracts after ingestion.

---

## 3. Instrument and Session Profile Contract — required for stocks + commodities

The current ORB research implementation is NSE-session-shaped. Before commodity support, create a canonical `ORB_INSTRUMENT_PROFILE` / `ORB_SESSION_PROFILE`.

Minimum fields:

- instrument type;
- exchange;
- symbol / contract code;
- timezone;
- exchange session calendar identity/version;
- session open;
- session close;
- session breaks if any;
- session anchor used for ORB timing;
- tick size;
- price precision;
- lot/contract metadata where research needs it;
- expiry/roll metadata when applicable;
- prior-session reference-price semantics: close vs official settlement vs another registered source;
- applicable benchmark/context family;
- applicable event-calendar family;
- corporate-action applicability;
- derivatives/OI applicability;
- data-source/provenance requirements.

### 3.1 NSE equity semantics

For NSE equities, “previous-day candle” remains exactly the **completed previous NSE trading session DAILY candle**. Never use yesterday's last 5m/10m/15m candle as the previous-day candle.

### 3.2 Commodity semantics

For commodities, “previous day” must mean the **previous completed exchange session**, not a naive midnight-to-midnight calendar resample. If a commodity session crosses calendar boundaries or uses exchange-specific trading hours, sessionization must follow the exchange calendar.

Therefore commodity support must not reuse `DataFrame.resample("D")` as the canonical session boundary without an exchange-session proof.

The prior-session commodity candle must be built from the exact registered session and carry the session/calendar version used to construct it.

---

## 4. Commodity-specific hardening that the stock-only plan did not fully capture

Commodity futures introduce failure modes that must be first-class before promotion:

1. **Contract identity:** front/next/other contract must be explicit. Never silently mix contracts.
2. **Rollover:** roll date/method and active-contract rule must be versioned and PIT-safe.
3. **Continuous series:** back-adjusted continuous futures may alter historical prices and create/remove apparent gaps. Raw contract prices and adjustment provenance must be preserved. Gap research cannot use an adjusted series as if it were an unmodified traded contract.
4. **Settlement vs close:** gap calculations must state whether previous reference is last trade, official settlement, or another canonical value.
5. **Expiry effects:** expiry/roll proximity, open interest migration and liquidity changes must be available to AFRE when data exists.
6. **Volume/OI distortion:** abnormal volume around roll must not be mistaken for ordinary participation without roll context.
7. **Tick/contract economics:** stop, target, slippage and cost research must use instrument metadata and normalized R/ATR/tick measures rather than stock-only assumptions.
8. **Price limits / halts / illiquidity:** market-specific constraints must be represented explicitly.
9. **Benchmark context:** Nifty/sector context is not automatically applicable to commodities. Use an approved commodity/underlying/FX/global context only when available and proven useful; otherwise mark it `NOT_APPLICABLE` or `UNAVAILABLE`.
10. **Corporate actions:** equity corporate-action logic must not be applied to commodities. `NOT_APPLICABLE` is distinct from missing.
11. **Event context:** commodity-specific inventory, macro, central-bank, FX, global-market or supply/event context may be added only through registered PIT-safe sources.
12. **Session-specific timing:** commodity ORB windows are measured from the registered commodity session anchor or another explicitly researched event anchor, not from hard-coded 09:15 IST.

---

## 5. Strengthened Canonical ORB Context Brain

Create one canonical context package per candidate and decision snapshot.

### Common evidence for all supported instruments

- previous completed exchange-session OHLCV candle;
- prior-session candle anatomy and validated pattern evidence;
- previous-session high/low/close or settlement references;
- opening/pre-session gap state using explicitly defined reference semantics;
- BB state: basis, bands, width, compression/expansion, slope, location, transition;
- session/daily and weekly VWAP with deviation bands ±1/±2/±3 when canonically available;
- ATR/volatility regime;
- current and prior volume/participation evidence;
- market structure, levels, liquidity, trap/sweep evidence;
- relevant event/derivatives/OI context where applicable;
- quality/freshness/availability/provenance/snapshot hashes;
- reasons FOR and AGAINST.

### Equity-only or equity-default context

- CPR Pivot/BC/TC and width class;
- PDH/PDL/PDC;
- Nifty/benchmark alignment;
- sector alignment/relative strength;
- corporate-action checks;
- equity/F&O expiry/event context when applicable.

### Commodity context

- previous-session high/low/close/settlement identity;
- CPR only if calculated canonically and research proves utility for that commodity; existence of the formula alone does not make it an authoritative rule;
- contract/roll/expiry context;
- OI migration and volume context where available;
- relevant underlying/benchmark/currency/global context only when source and PIT semantics are valid;
- commodity-specific event context where available.

No unavailable context is converted into neutral/safe evidence.

---

## 6. Timing / Timeframe Research — change “per-stock” to “per-instrument”

The existing target remains ORB-5/10/15/20/30 plus confirmation-TF research, but the canonical abstraction is **per instrument**, not stock-only.

Research matrix should support:

- OR duration: 5 / 10 / 15 / 20 / 30 minutes at minimum when exact source data supports reconstruction;
- OR-end clock / session-relative cutoff as a configurable dimension;
- confirmation timeframe: 1m / 3m / 5m / 15m where exact bars are available;
- signal family: breakout, breakdown, retest, reversal, trap, constrained re-entry and other preserved variants;
- context/regime bucket;
- candidate-intake reason when studying a pre-market-selected strategy.

Measure at minimum:

- sample count;
- win/loss rate;
- expectancy in R;
- after-cost expectancy;
- profit factor where appropriate;
- maximum drawdown;
- MAE/MFE;
- false-break rate;
- retest success rate;
- trigger timing;
- no-chase sensitivity;
- stop/target sensitivity;
- regime/context dependence;
- stability by year/period;
- holdout/unseen performance;
- uncertainty/confidence interval;
- edge decay/drift;
- roll/expiry stability for commodities.

For NSE equities, OR timing is relative to the NSE session. For commodities, timing is relative to that instrument's registered session profile. Hard-coded stock-market clock assumptions are forbidden in the generic research engine.

---

## 7. Combination Research — include candidate-selection context

Do not research isolated indicators. Research **situations**.

Examples for equities:

```text
USER/TRENDFORGE CANDIDATE: major gap-up + high pre-market volume
+
previous completed DAILY = bullish engulfing
+
narrow CPR
+
above/accepted daily VWAP
+
BB expansion
+
Nifty + sector aligned
+
ORB-15 BREAKOUT_LONG with 5m confirmation
        ↓
What happened historically on equivalent PIT-safe selected days?
```

Opposite/conflicted examples must be researched too.

Examples for commodities:

```text
COMMODITY CANDIDATE: abnormal pre-session activity
+
previous completed exchange-session trend candle
+
volatility expansion
+
contract not in roll distortion
+
relevant benchmark/context aligned
+
ORB signal confirmed on the proven session-relative window
        ↓
How did this contract/instrument behave historically after costs?
```

Minimum-sample, multiple-testing, sparse-bucket, walk-forward and untouched-holdout controls remain mandatory.

---

## 8. Per-Instrument ORB Playbook

Rename the conceptual scope from only `per-stock playbook` to **per-instrument ORB playbook** while retaining stock-specific behavior for equities.

Minimum contents:

- instrument/symbol/contract identity;
- instrument type and exchange;
- session-profile version;
- eligible source timeframes;
- preferred OR duration(s);
- preferred OR-end/session-relative clock;
- preferred confirmation timeframe(s);
- supported signal families;
- best contexts and bad/no-trade contexts;
- candidate-intake conditions when the proof depends on a pre-market filter;
- direction bias only when evidence supports it;
- breakout vs retest preference;
- false-break/trap behavior;
- volume requirements;
- VWAP/3-band rules;
- CPR rules where applicable/proven;
- previous-session candle/pattern rules;
- BB/volatility-state rules;
- benchmark/sector/context rules where applicable;
- event/expiry/roll/OI/liquidity vetoes;
- entry, stop, target, RR and no-chase rules;
- cutoff/setup expiry/hold-flat/re-entry rules;
- costs/slippage assumptions;
- sample count;
- train/validation/holdout ranges;
- deterministic proof statistics;
- uncertainty;
- known failure modes;
- drift/edge-decay state;
- data/feature/model/session versions;
- promotion status.

Nothing is promoted from in-sample performance alone.

---

## 9. AFRE / D6 reasoning contract

ORB remains an evidence producer.

AFRE/D6 must ask:

1. Why is this instrument in today's candidate list?
2. Is the candidate-intake evidence itself valid/PIT-safe or merely a manual attention flag?
3. Which OR duration/clock/confirmation TF has proof for this instrument?
4. Does the previous completed exchange session support or contradict the current signal?
5. Does current regime/volatility/structure support it?
6. Does VWAP/value context support it?
7. Is volume genuine or explained by expiry/roll/auction distortion?
8. Is the breakout likely a trap/failed break?
9. Is the relevant benchmark/sector/underlying context aligned, contradictory, unavailable, or not applicable?
10. Is event/expiry/roll/OI risk elevated?
11. What happened in comparable historical candidate-selected situations?
12. Are deterministic proof, analog evidence and calibrated ML evidence consistent?
13. Is any hard blocker present?

D6 remains the only final-band authority and may return only permitted research/paper guidance such as `WAIT`, `WATCH`, or `PAPER-CANDIDATE`.

---

## 10. Current verified designed flow — keep and extend, do not rewrite from zero

### Current research path already present

```text
Historical local data
  -> hstry_csv
  -> timing_research
  -> discovery
  -> proof / walk-forward / holdout
  -> promoted ORB playbook
```

### Current guidance path already present

```text
D1/D2 paper-guidance snapshot
  -> active playbook lookup
  -> ORB core candidate on the same immutable snapshot
  -> MTF / liquidity / trap / regime / structure / volume / event evidence
  -> final confluence arbiter
  -> WAIT / WATCH / PAPER-CANDIDATE-equivalent paper guidance
  -> human approval before paper recording
```

### Important current gap

The repository already has `orb/context.py`, but the simple-flow audit records it as standalone/not yet fully wired into `orb/core.py`. The canonical future plan also records that detailed prior-session candle patterns, BB, daily/weekly VWAP ±1/±2/±3 and several context signals exist elsewhere but are not yet fully wired into the ORB decision package.

Commodity support is an additional gap because current discovery session grouping is NSE 09:15–15:30 shaped.

---

## 11. Strengthened target flow for the user's actual operating method

```text
USER / TRENDFORGE PRE-MARKET SHORTLIST
(gap-up / gap-down / abnormal-volume / event candidate)
                |
                v
ORB_CANDIDATE_INTAKE
(identity + reason + as_of + provenance + snapshot hash)
                |
                v
INSTRUMENT / SESSION PROFILE
(NSE equity or commodity contract; correct exchange calendar)
                |
                v
D1 / D2 DATA + CLOSED-CANDLE CAUSAL SNAPSHOT
                |
                v
PREVIOUS COMPLETED EXCHANGE SESSION
(full DAILY/session candle, never previous intraday bar)
                |
                v
CANONICAL ORB CONTEXT BRAIN
(candle/pattern + CPR where applicable + levels + gap + BB + VWAP ±1/2/3
 + ATR + volume + structure + benchmark/sector/underlying + event/OI/expiry/roll)
                |
                +-------------------------------+
                |                               |
                v                               v
OFFLINE RESEARCH                         TODAY RUNTIME
Timing/TF/clock matrix                   Active proven playbook
Combination research                    Build/lock today's OR
Discovery + proof                       Closed-candle signal
Walk-forward + holdout                  Pattern / context classification
Costs + uncertainty                     Proven parameter selection
                |                               |
                v                               v
PROVEN PER-INSTRUMENT PLAYBOOK ------> ORB_EVIDENCE_PACKAGE
                                                |
                                                v
                                           AFRE / D6
                                                |
                                      +---------+---------+
                                      |         |         |
                                     WAIT      WATCH   PAPER-CANDIDATE
                                                |
                                                v
                                      HUMAN PAPER APPROVAL ONLY
                                                |
                                                v
                                      LATER MATURED OUTCOME
                                                |
                                                v
                                calibration / drift / challenger research
```

---

## 12. Build order from the current repository

Do not start over. Upgrade the existing stack in this order:

### S0 — exact-head baseline lock

- reverify branch head;
- record current ORB tests/workflows;
- map existing model contracts and APIs;
- preserve passing behavior.

### S1 — candidate intake contract

- add typed candidate-intake schema and provenance;
- support explicit user list and existing Trendforge candidate intake;
- add candidate-selection-bias tests.

### S2 — instrument/session profile abstraction

- remove generic research dependence on hard-coded NSE clocks;
- keep an NSE profile that reproduces existing behavior exactly;
- add commodity session/contract profile support;
- replace naive calendar-day aggregation where session boundaries differ.

### S3 — canonical context brain

- reuse/migrate `orb/context.py`;
- wire prior completed session candle/pattern, CPR/levels where applicable, BB, VWAP ±1/2/3, ATR, volume, structure, benchmark/context, events and availability semantics;
- eliminate fake-neutral defaults.

### S4 — timing/TF/clock research

- extend `timing_research.py` rather than create a parallel engine;
- support per-instrument duration × session-relative clock × confirmation-TF matrix;
- retain deterministic checkpoint/replay semantics.

### S5 — discovery/proof hardening

- make `discovery.py` session-profile aware;
- preserve costs, deterministic ranking and no-future-leakage;
- extend `proof.py` with candidate-selection-conditioned proof and commodity expiry/roll stability checks;
- keep train-only selection, walk-forward and holdout discipline.

### S6 — combination/analog research

- join context + candidate-intake reason + signal + matured outcomes;
- research supportive and conflicting situations;
- sparse samples must abstain.

### S7 — per-instrument playbook v2

- freeze session profile, timing/TF/clock fit, contexts, parameters, proof, uncertainty and commodity metadata when applicable.

### S8 — ORB evidence package into AFRE/D6

- replace current neutral placeholders with real canonical evidence or explicit unavailability;
- carry reasons FOR/AGAINST;
- D6 may veto;
- no live-trading authority.

### S9 — adversarial/replay/CI lock

- exact-head tests and CI before GREEN;
- shadow/paper validation only.

---

## 13. Mandatory new adversarial tests

In addition to the parent plan, add:

1. User-shortlisted symbol enters the queue without becoming bullish/bearish evidence by itself.
2. Historical candidate-filter backtest cannot use future gap/volume information.
3. Missing pre-market volume remains unavailable.
4. Equity NSE profile reproduces legacy 09:15–15:30 behavior before migration is accepted.
5. Generic discovery has no hard-coded 09:15–15:30 dependency after session-profile migration.
6. Commodity session crossing a calendar boundary forms exactly one intended exchange session.
7. Commodity previous-session candle never becomes midnight-to-midnight by accident.
8. Commodity gap uses the declared reference close/settlement semantics.
9. Raw contract and back-adjusted continuous-series prices cannot be silently mixed.
10. Roll/expiry does not create a fake gap edge.
11. Roll-driven volume spike is distinguishable from ordinary participation when roll data exists.
12. Missing benchmark/sector/underlying context remains unavailable/not-applicable, never neutral.
13. Corporate-action checks are `NOT_APPLICABLE` for commodities, not false/safe.
14. CPR for commodities cannot become a promoted rule without instrument-specific proof.
15. OR duration and clock are relative to the registered session profile.
16. Confirmation uses only fully closed bars.
17. Same immutable snapshot reproduces context, signal, parameters and evidence-package hashes.
18. Playbook for one instrument/session profile cannot be silently copied to another instrument.
19. Expired/rolled commodity contract playbook cannot apply to a different contract identity without an explicit migration rule.
20. D6 remains sole final-band authority for equities and commodities.
21. `research_only=true`, `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, `human_approval_required=true` remain invariant.

---

## 14. Final scope statement

The canonical target is now:

> **Selected intraday stock/commodity candidate → candidate-intake proof → correct instrument/session profile → previous completed exchange session → canonical ORB context → per-instrument OR duration/clock/confirmation research → discovery + unseen-data proof → combination/analog research → frozen per-instrument playbook → today's closed-candle ORB signal + proof-backed parameters → ORB evidence package → AFRE support/contradiction reasoning → D6 WAIT/WATCH/PAPER-CANDIDATE → human-approved paper record only → later matured outcome feeds controlled research.**

This addendum strengthens the parent ORB/AFRE plan. It does not weaken or replace the existing safety, causality, epistemic, replay, proof, or authority requirements.