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

---

# code build ready plan

This section converts the scope and architecture above into the concrete implementation plan to start coding from the current repository. It is intentionally written as an **upgrade plan**, not a rewrite plan.

## A. Build-readiness verdict

**YES — coding can start now.**

The repository already contains enough working ORB infrastructure to begin implementation safely:

```text
apps/api/app/orb/hstry_csv.py
apps/api/app/orb/context.py
apps/api/app/orb/core.py
apps/api/app/orb/timing_research.py
apps/api/app/orb/discovery.py
apps/api/app/orb/proof.py
apps/api/app/orb/adaptive/
apps/api/app/behavior/orb_guidance.py
apps/api/app/behavior/final_confluence_arbiter.py
apps/api/app/behavior/indicator_registry.py
```

The build therefore starts by extending these seams and their models/tests. Do **not** create a second independent ORB implementation.

Coding readiness does not mean all future data feeds are already available. The correct approach is:

1. implement deterministic contracts and session logic first;
2. represent missing feeds as `UNAVAILABLE`/`NOT_APPLICABLE` rather than fake neutral values;
3. add external/event/commodity feeds later behind the same contracts;
4. never delay the safe core build merely because every enrichment source is not connected yet.

## B. Non-negotiable implementation laws

Every code stage must preserve:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

Epistemic laws:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no_signal != unavailable
no_output != neutral
NOT_APPLICABLE != UNAVAILABLE
```

Causality/authority laws:

1. fully closed candles only;
2. no future data in research features or runtime decisions;
3. previous-day/session means the previous **completed exchange session**;
4. snapshot-hash lineage must survive every handoff;
5. canonical facts are calculated once and reused;
6. ORB, context, ML, research and reviewers gain zero execution authority;
7. AFRE/D6 may contradict or veto ORB evidence;
8. D6 remains sole final-band authority;
9. no stage is GREEN without exact-head tests/CI evidence.

## C. Exact coding sequence

### BUILD-0 — baseline and contract inventory

Before modifying behavior:

- re-read the exact current branch head;
- inventory current ORB models in `apps/api/app/models.py` or their current canonical location;
- inventory ORB API routes and call chains;
- inventory existing ORB tests and workflow coverage;
- snapshot current deterministic outputs for representative NSE fixtures;
- record current playbook/proof storage schemas;
- record all current neutral/default hazards in `orb_guidance.py`, `core.py`, context adapters and arbiter inputs.

**GREEN gate:** existing ORB regression suite passes unchanged and baseline hashes are recorded.

### BUILD-1 — `ORB_CANDIDATE_INTAKE`

Implement the typed upstream attention contract.

Primary code changes should include the canonical models plus the smallest intake adapter needed to normalize:

- explicit user symbol list;
- Trendforge `READY` / `PRIORITY_RADAR` candidates;
- later scanner sources through the same schema.

Required states include source, reason, `as_of`, session identity, provenance, observed premarket metrics, availability and deterministic hash.

Do not infer bullish/short direction from the shortlist.

**Tests:** manual symbol, Trendforge symbol, duplicate symbol, stale intake, missing premarket volume, provenance mismatch, deterministic replay, candidate-selection bias.

### BUILD-2 — `ORB_INSTRUMENT_PROFILE` + `ORB_SESSION_PROFILE`

Create the canonical abstraction that removes exchange/session assumptions from generic ORB research.

NSE profile must initially reproduce current behavior exactly:

```text
timezone = Asia/Kolkata
session anchor = NSE cash-session open
legacy ORB session semantics preserved
```

Then add commodity-capable fields without pretending unsupported calendars are known.

Refactor hard-coded session filtering in `orb/discovery.py` and any equivalent ORB path so session grouping comes from the profile.

Refactor previous-session aggregation in `orb/context.py` so canonical session bars are produced by exchange-session identity, not a generic `resample("D")` when the instrument profile says otherwise.

**GREEN gate:** legacy NSE fixtures produce equivalent results; generic ORB sessionization no longer depends directly on `09:15`/`15:30` constants outside the NSE profile.

### BUILD-3 — canonical previous-session object

Create an immutable, hashable previous-session structure containing:

- session id/calendar version;
- open/high/low/close/volume availability;
- settlement reference where applicable;
- PDH/PDL/PDC semantics for equities;
- candle anatomy;
- corporate-action/roll adjustment identity;
- data quality and provenance.

The builder must prove that a previous 5m/10m/15m bar can never be substituted for the completed session candle.

**GREEN gate:** explicit regression that last intraday bar != prior DAILY/session candle.

### BUILD-4 — Canonical ORB Context Brain v2

Extend/reconcile `apps/api/app/orb/context.py`; do not build an unrelated context stack.

Wire canonical facts/evidence for:

- previous-session candle anatomy;
- detailed registered candlestick patterns;
- CPR/Pivot/BC/TC where applicable;
- previous-session high/low/close/settlement;
- gap and opening zone;
- BB state/compression/expansion;
- daily/session and weekly VWAP ±1/±2/±3;
- ATR/volatility;
- volume/RVOL/participation;
- canonical structure/levels/liquidity/trap evidence;
- benchmark/index/sector/underlying context;
- event/derivatives/OI/expiry/roll context;
- availability, freshness, provenance and hashes.

Required contract rule:

```text
OBSERVED_ZERO
MISSING
UNKNOWN
UNAVAILABLE
NOT_APPLICABLE
ERROR
```

must remain distinguishable.

No evidence source may silently become `0.0`, `False`, or neutral merely because it is missing.

**GREEN gate:** context replay hash deterministic; incomplete context is explicit; no fake-neutral regression failures.

### BUILD-5 — ORB Timing / Clock / Confirmation-TF Research v2

Upgrade `timing_research.py` rather than replace it.

Research matrix:

```text
instrument
× ORB duration (5/10/15/20/30)
× session-relative OR-end clock
× confirmation TF (1m/3m/5m/15m where exact data exists)
× signal family
× regime/context bucket
× candidate-intake condition when required
```

Required metrics:

- sample count;
- win/loss;
- expectancy R and after-cost expectancy;
- profit factor;
- maximum drawdown;
- MAE/MFE;
- false-break rate;
- retest success;
- trigger time;
- no-chase sensitivity;
- stop/target sensitivity;
- context/regime dependence;
- year/period stability;
- holdout performance;
- uncertainty;
- drift/edge decay;
- commodity expiry/roll stability when applicable.

Retain deterministic checkpoints and resumability.

**GREEN gate:** the engine can legitimately conclude `INSUFFICIENT_DATA` or no significant timing difference instead of inventing a winner.

### BUILD-6 — explicit ORB signal contract v2

Reconcile `core.py` with the parent future plan so ORB signals are first-class, versioned and hashable.

Signal families must explicitly represent, as implemented/proven:

- `NO_SETUP`;
- breakout long;
- breakdown short;
- retest long/short;
- reversal/failed-break long/short;
- trap evidence;
- constrained second-chance re-entry;
- invalidated/stale.

Every signal must carry ORH/ORL, OR timing, confirmation TF, closed-bar confirmation timestamp, direction, buffer, volume/VWAP evidence, retest/trap state, freshness, provenance, source snapshot, reasons FOR/AGAINST and deterministic hash.

**GREEN gate:** no signal can gain authority from an incomplete bar.

### BUILD-7 — discovery engine hardening

Extend `discovery.py` to consume the session profile, canonical context and expanded research dimensions.

Research must preserve costs and no-future-leakage while expanding beyond the current limited combination grid.

A candidate-selected strategy must use historical selection rules reconstructed from information known at each historical `as_of`; it cannot tag winning historical days after seeing the future.

**GREEN gate:** same input/version produces same ranked combinations and trade ledger.

### BUILD-8 — proof / promotion engine v2

Extend `proof.py`; preserve its current good properties:

- train-only candidate selection;
- chronological holdout;
- expanding walk-forward validation;
- minimum-sample gates;
- deterministic proof IDs/hashes.

Add:

- duration/clock/confirmation-TF proof;
- context/combination proof;
- candidate-intake-conditioned proof;
- transaction-cost sensitivity;
- uncertainty intervals;
- edge-decay/stability checks;
- commodity contract/roll/expiry stability where applicable;
- explicit rejected/insufficient-data reasons.

No playbook promotion from in-sample results alone.

### BUILD-9 — combination + historical analog research

Create the research layer that answers situations rather than isolated indicator questions.

Minimum join key is:

```text
candidate intake
+ immutable ORB context snapshot
+ ORB signal
+ parameter set
+ later matured outcome
```

Research support, contradiction and conflict cases.

Examples include:

```text
bullish engulfing + narrow CPR + VWAP acceptance + BB expansion
+ aligned benchmark + strong breakout volume
```

and the mirrored/conflicting cases.

Sparse combinations must pool/abstain rather than become confident rules.

Historical analog output must contain comparable-case definition, sample count, wins/failures/mixed, expectancy, similarity/uncertainty and PIT proof.

### BUILD-10 — trade-parameter research v2

Research and freeze per-instrument/per-signal/per-context parameters only when proof supports them:

- entry style/zone;
- breakout buffer;
- confirmation rule;
- required volume;
- VWAP/3-band acceptance/veto;
- stop methodology;
- target methodology;
- minimum RR;
- maximum chase;
- entry cutoff;
- setup expiry;
- retest window;
- maximum re-entry;
- maximum hold/paper-flat rules;
- slippage/cost/liquidity assumptions.

Runtime selects from frozen promoted parameter sets; it must not optimize using later movement from the current session.

### BUILD-11 — per-instrument playbook v2

Promote one immutable playbook contract containing:

```text
instrument identity
instrument/session profile version
candidate-selection scope if relevant
preferred OR duration
preferred OR-end clock
confirmation TF
supported signal families
best/bad contexts
volume/VWAP/CPR/candle/BB rules
benchmark/event/expiry/roll rules
entry/stop/target/no-chase/cutoff
sample count
train/validation/holdout periods
proof hashes
uncertainty
failure modes
drift state
promotion state
```

A stock playbook remains stock-specific. A commodity contract/instrument playbook cannot silently inherit a stock session profile.

### BUILD-12 — ORB Evidence Package

Build one immutable package before AFRE/D6 containing:

- candidate-intake identity;
- instrument/session identity;
- canonical context;
- active playbook/proof;
- ORB signal;
- selected promoted parameters;
- deterministic research statistics;
- historical analog evidence;
- combination evidence;
- ML evidence when later promoted;
- reasons FOR;
- reasons AGAINST;
- blockers;
- unavailable/not-applicable evidence;
- PIT/causality proof;
- package hash.

ORB evidence remains advisory/evidentiary, never final authority.

### BUILD-13 — AFRE / D6 integration hardening

Upgrade `orb_guidance.py` and the canonical D6 ingestion seam.

Replace current placeholder/default semantics such as artificial neutral indicator/relative-strength/external-AI/sector/event/trap values with either:

1. real canonical evidence; or
2. explicit `UNAVAILABLE`/`NOT_APPLICABLE` state.

D6 must deliberate over support and contradiction and retain the ability to reject a strong ORB setup because of stronger structure, resistance, event, liquidity, trap, data-quality or uncertainty evidence.

Permitted user-facing outputs remain:

```text
WAIT
WATCH
PAPER-CANDIDATE
```

### BUILD-14 — ML feature/label store only after deterministic contracts stabilize

Do not start ML first.

Once context, signal, parameters and playbook contracts are stable:

- freeze immutable decision-time feature rows;
- create outcome labels only after the outcome horizon matures;
- never mutate past decision snapshots;
- use chronological train/validation/test;
- add purging/embargo where trade horizons overlap;
- preserve untouched final holdout;
- compare against simple deterministic/statistical baselines;
- calibrate probabilities;
- maintain champion/challenger/rollback/drift states.

ML may rank/evaluate proven configurations but cannot invent execution authority or bypass hard blockers.

### BUILD-15 — full adversarial + deterministic replay suite

In addition to all earlier tests, full-build acceptance must cover:

- future-bar mutation cannot alter an earlier decision;
- incomplete-bar authority blocked;
- prior session truly completed;
- wrong timezone/session rejected;
- DST/calendar/session-boundary cases where applicable;
- missing volume not zero;
- missing indicator not neutral;
- missing event/trap not safe;
- `NOT_APPLICABLE` distinct from `UNAVAILABLE`;
- raw commodity contract not silently mixed with adjusted continuous data;
- expiry/roll fake-gap prevention;
- candidate-selection leakage prevention;
- deterministic context/signal/parameter/evidence hashes;
- train/validation/holdout separation;
- multiple-testing/sparse-sample controls;
- playbook/version mismatch fail-closed;
- D6 sole final-band authority;
- zero live execution authority.

## D. Stage progression rule

The build progresses serially:

```text
BUILD-0 GREEN
   ↓
BUILD-1 GREEN
   ↓
BUILD-2 GREEN
   ↓
BUILD-3 GREEN
   ↓
BUILD-4 GREEN
   ↓
BUILD-5 GREEN
   ↓
...
   ↓
ORB/AFRE integration GREEN
```

For every stage:

1. inspect exact current implementation;
2. state assumptions and canonical source of truth;
3. change the smallest safe seam;
4. add unit + integration + adversarial tests;
5. run affected regressions;
6. run full required workflow/CI;
7. verify exact-head result;
8. record unresolved limitations;
9. lock the stage before moving on.

Never mark a stage GREEN from documentation alone.

## E. Files expected to be extended first

The first coding passes are expected to touch, subject to exact-head re-verification:

```text
apps/api/app/models.py                     # typed candidate/session/context contracts
apps/api/app/orb/context.py                # canonical session/context brain
apps/api/app/orb/discovery.py              # session-aware historical discovery
apps/api/app/orb/timing_research.py        # duration/clock/confirmation-TF research
apps/api/app/orb/proof.py                  # expanded OOS/promotion proof
apps/api/app/orb/core.py                   # signal contract and context consumption
apps/api/app/behavior/orb_guidance.py      # ORB evidence -> AFRE/D6
apps/api/app/behavior/indicator_registry.py# reuse canonical registered indicators
```

Tests should be added beside the repository's existing ORB/behavior test structure rather than creating a disconnected test harness.

## F. Current system → target system summary

Current useful foundation:

```text
history
 -> timing research
 -> discovery
 -> proof
 -> playbook
 -> ORB core
 -> ORB guidance
 -> final arbiter
```

Target strengthened system:

```text
selected premarket/intraday candidate
 -> canonical candidate intake
 -> instrument/session profile
 -> completed previous exchange session
 -> canonical ORB context
 -> per-instrument OR/clock/TF research
 -> signal-family + parameter research
 -> combination + analog research
 -> discovery + OOS/walk-forward proof
 -> frozen playbook
 -> today's closed-candle ORB signal
 -> proof-backed parameter selection
 -> ORB evidence package with FOR/AGAINST
 -> AFRE reasoning
 -> D6 final deliberation
 -> WAIT / WATCH / PAPER-CANDIDATE
 -> human paper approval only
 -> later matured outcome
 -> controlled calibration/challenger research
```

## G. Coding start point

The correct first implementation target is:

> **BUILD-0 baseline lock → BUILD-1 candidate intake → BUILD-2 instrument/session profile → BUILD-3 previous-session contract → BUILD-4 Canonical ORB Context Brain.**

These stages create the safe foundation for everything that follows. Timing research, combination research, playbook v2, AFRE integration and ML should build on those contracts rather than being implemented ahead of them.

Therefore the ORB build is **code-ready now**, with the condition that implementation starts by verifying the exact branch head and current tests, then proceeds stage by stage without breaking the already-working ORB research/proof/guidance path.