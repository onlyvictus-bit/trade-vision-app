# M3.2 — Canonical Context Intelligence

**Date:** 2026-09-08  
**Branch:** `m3-2-context-intelligence`  
**Base / locked predecessor:** M3.1 final head `20d2d7b5889b09cd593401e8f70ec53cc299c51e`  
**State at creation:** DESIGN STARTED / RUNTIME MIGRATION NOT YET LOCKED  
**Scope:** market regime, session context, index context, sector context, relative strength  
**Out of scope:** M3.3 memory activation, ORB/AFRE redesign, derivatives, final D6 redesign, execution authority.

---

## 1. Mission

M3.2 converts the existing context brains into one deterministic, D2-causal, bounded context evidence layer without creating another final decision brain.

The target is not to invent another score. The target is to answer, with explicit provenance:

- What session are we actually in?
- What is the market/index doing at the same causal decision time?
- What is the correct sector doing?
- Is the stock leading or lagging those benchmarks?
- What market regime can be supported by the available facts?
- Which facts are unavailable, stale, incomplete, synthetic, misaligned, or contradictory?

M3.2 must preserve the program law:

```text
RAW FACT CALCULATED ONCE
        ↓
MANY SPECIALISTS MAY INTERPRET IT
        ↓
EVERY INTERPRETATION IS TRACEABLE
        ↓
NO SPECIALIST GETS FINAL AUTHORITY
```

Safety and epistemic rules remain locked:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no incomplete-bar authority
D1 outranks every predictor/reviewer
all active evidence must be causal to the D2 decision time
FINAL_CONFLUENCE_ARBITER / D6 remains sole final-band authority
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
```

"AGI-level" is treated as an architecture aspiration: broad context, contradiction awareness, adaptation, provenance, failure detection, and future extensibility. No software design can guarantee correct decisions in every market situation or guarantee AGI. M3.2 therefore optimizes for robust evidence and bounded uncertainty rather than pretending omniscience.

---

## 2. Current M3.2 brain inventory — repository truth

### 2.1 `MARKET_REGIME`

**Registered engine:** `MARKET_REGIME`  
**Authority registry source:** `app.behavior.regime_gate`  
**Current lifecycle:** migration  
**Current allowed authority:** evidence/downgrade only; no final band and no execution.

Existing files:

- `apps/api/app/behavior/regime_gate.py`
- `apps/api/app/behavior/market_regime_feedback.py`
- `apps/api/app/behavior/market_calendar_event_regime.py`
- `apps/api/app/behavior/condition_classifier.py`
- `apps/api/app/behavior/chart_reasoning_volatility.py`

What is already useful:

- deterministic regime labels and regime IDs exist;
- trend/volatility/session/liquidity dimensions are already represented;
- the market-regime feedback layer includes breadth, correlation, relative-strength, Bayesian shrinkage, failure penalty, and live-update restrictions;
- research-only safety flags already exist in these reports.

What is not acceptable as canonical M3.2 evidence yet:

1. `regime_gate.py` calls the 9C `build_evidence_packet()` path. That packet currently contains mock/hard-coded current evidence paths and can construct CandleBars with `source="mock"`. A report cannot become canonical merely because it later sets `no_future_leakage=True`.
2. `market_regime_feedback.py` mixes M3.2 context facts with M3.3 historical feedback and later risk/cooldown concepts. M3.2 must separate sensory context from historical learning and risk authority.
3. Missing index/breadth/sector inputs are sometimes substituted internally with neutral-looking numeric defaults (`0.0` or `1.0`) for downstream calculations. The report exposes partial status, but canonical evidence must not calculate a directional fact from a fabricated neutral substitute.
4. No independent source snapshot/watermark is attached to index, sector, or breadth inputs.
5. No freshness, clock-skew, provider identity, source sequence, or source close-time contract is proven.
6. Current production Paper Guidance does not emit a canonical `MARKET_REGIME` receipt.

**Decision:** do not rewrite or delete the legacy regime files. Create a new canonical M3.2 layer that consumes verified already-computed facts. Reuse only pure formulas after provenance and missingness are made explicit.

---

### 2.2 `SESSION_MEMORY`

**Registered engine:** `SESSION_MEMORY`  
**Authority source:** `app.behavior.session_memory`  
**Classification:** memory  
**Current lifecycle:** migration.

Existing files:

- `apps/api/app/behavior/session_memory.py`
- `apps/api/app/behavior/exact_time_session_memory.py`
- related session models and persisted session profiles in storage.

What is already useful:

- explicit NSE-style intraday phase windows exist;
- segment-level return/range/volume-curve/trend/fakeout/quality calculations exist;
- sample-size guards exist for persisted session memory;
- day-of-week and stock-DNA summaries already exist;
- exact-time/session-transition/calendar-class concepts have already been explored.

Critical defects before canonical activation:

1. `session_memory._available_bars()` admits bars using `bar.timestamp_ns <= decision_time_ns`. For a timestamp that represents bar open/start, an in-progress bar can enter authority even though its close is after the decision time. M3.2 must use `bar.timestamp_ns + timeframe_duration_ns(timeframe) <= decision_time_ns` or the already-frozen D2 closed series.
2. The current exact-time module is deterministic only because it uses seeded `random.Random`; its rates and evidence counts are synthetic. It also defaults to a fixed 2024 decision time when none is supplied. This is fixture/research scaffolding, not real session memory.
3. `follows_exchange_calendar=True` is asserted from static regular-session windows rather than proved against an official exchange calendar identity.
4. `Asia/Calcutta` / fixed offset handling should be replaced by a versioned timezone/calendar contract. India does not currently use DST, but the architecture should not encode the assumption that all future providers/exchanges have fixed offsets.
5. Persisted profile `updated_at` and corpus availability must be cutoff-safe. A profile computed after the decision time cannot be allowed to describe what was knowable at that decision time.
6. No canonical `SESSION_MEMORY` receipt is active in the current Paper Guidance DecisionContext.

**Decision:** preserve legacy session-memory functions for compatibility and historical research. Create a new canonical session evaluator over D2-closed bars and a versioned calendar/session identity. Synthetic exact-time profiles remain explicitly noncanonical until replaced by real persisted observations.

---

### 2.3 `INDEX_CONTEXT`, `SECTOR_CONTEXT`, `RELATIVE_STRENGTH`

**Registered engines:**

- `INDEX_CONTEXT`
- `SECTOR_CONTEXT`
- `RELATIVE_STRENGTH`

**Current authority source:** `app.behavior.context_engines`  
**Lifecycle:** migration.

Current implementation anchor:

`apps/api/app/behavior/context_engines.py::analyze_market_context()`

Useful existing behavior:

- index direction classification exists;
- sector strength classification exists;
- stock-vs-index-vs-sector relative-strength calculation exists;
- market alignment/conflict rules exist;
- long/short conflict examples already produce a blocking context result.

Current limitations:

1. Inputs are scalar request values rather than independently frozen source snapshots.
2. There is no provider/symbol identity for the benchmark.
3. There is no proof that index/sector values correspond to the same or earlier decision time.
4. There is no source close-time/freshness proof.
5. There is no benchmark mapping provenance proving that the stock is compared with the correct sector index.
6. No breadth identity or index constituent/universe watermark is attached.
7. Relative strength has no explicit lookback/window version in the simple context engine.
8. Correlation/lead-lag logic in `market_regime_feedback.py` is richer, but that file mixes historical/Bayesian/risk concerns and also uses fallback defaults for missing facts.
9. The current canonical DecisionContext fields for index, sector and RS remain explicitly `UNAVAILABLE`.

**Decision:** keep the legacy scalar API stable, but do not make it the canonical truth. Build a new M3.2 context-source contract and calculate index, sector and relative-strength facts once from explicit benchmark snapshots.

---

### 2.4 Optional cross-market context

Existing file:

`apps/api/app/behavior/cross_market_influence.py`

The design already understands an important rule: unavailable global context should reduce coverage instead of becoming neutral.

However, the current implementation generates provider values through deterministic random fixtures and uses `source="mock_provider"`. Therefore:

- it is useful as a failure-mode/test scaffold;
- it is not canonical M3.2 evidence;
- it must never be silently wired as real GIFT Nifty, US, DXY, USD/INR, yields, or crude data.

Future real cross-market adapters should plug into the M3.2 context-source contract after they have provider identity, timestamps, freshness, and snapshot hashes.

---

## 3. What is currently wired into production Paper Guidance?

### 3.1 DecisionContext already has the destination fields

M2 created canonical fields for:

```text
market_regime
session_context
index_context
sector_context
relative_strength
```

The current binding table maps them to:

```text
market_regime      -> MARKET_REGIME
session_context    -> SESSION_MEMORY
index_context      -> INDEX_CONTEXT
sector_context     -> SECTOR_CONTEXT
relative_strength  -> RELATIVE_STRENGTH
```

But these fields are still intentionally represented as unavailable when no M3.2 receipt exists. This is correct and must not be bypassed.

### 3.2 Current D6 compatibility values are not M3.2 activation

Current locked D6 construction still uses compatibility values:

```text
market_regime_score       = legacy chart-derived compatibility score
relative_strength_score   = 0.5
weak_sector               = false
```

Those values are preserved for parity. M3.2 must first create causal canonical evidence. It must **not** silently replace D6 inputs during this milestone. D6 semantic redesign belongs to the later authorized orchestration stage.

### 3.3 Current M3.2 receipts are absent

Production Paper Guidance currently emits M3.1 price receipts plus persisted indicator memory, structure and execution-risk evidence. It does not yet run canonical:

```text
MARKET_REGIME
SESSION_MEMORY
INDEX_CONTEXT
SECTOR_CONTEXT
RELATIVE_STRENGTH
```

Therefore M3.2 is a real migration, not just documentation cleanup.

---

## 4. New files vs editing old files

### 4.1 New files are required

Recommended production additions:

```text
apps/api/app/behavior/decision_spine/canonical_context_intelligence.py
apps/api/app/behavior/decision_spine/context_source_snapshot.py          # if source ingestion grows beyond the first contract
apps/api/app/behavior/paper_guidance_spine_m3_2_impl.py
apps/api/tests/decision_spine/test_m3_2_context_contract.py
apps/api/tests/decision_spine/test_m3_2_session.py
apps/api/tests/decision_spine/test_m3_2_market_context.py
apps/api/tests/decision_spine/test_m3_2_regime.py
apps/api/tests/decision_spine/test_m3_2_replay.py
apps/api/tests/decision_spine/test_m3_2_adversarial.py
.github/workflows/m3-2-context-intelligence.yml
```

Why new canonical files instead of rewriting everything:

- old modules have public/test compatibility contracts;
- several old modules mix unrelated milestones;
- some old paths contain synthetic or fixture data;
- large rewrites increase regression risk;
- a canonical adapter allows precise provenance and parity comparison against legacy behavior.

### 4.2 Existing files should be edited only at controlled integration points

Expected surgical edits later in M3.2:

```text
apps/api/app/behavior/paper_guidance_spine.py
apps/api/app/behavior/decision_spine/paper_guidance_decision_context_adapter.py
apps/api/app/behavior/decision_spine/__init__.py
.github/workflows/m3-2-context-intelligence.yml
docs/CANONICAL_BUILD_STATUS.md
docs/NEXT_BUILD_TARGET.md
```

Possible optimization edits after parity proof:

```text
apps/api/app/behavior/session_memory.py
apps/api/app/behavior/context_engines.py
apps/api/app/behavior/market_regime_feedback.py
```

But the first canonical implementation should wrap/reuse rather than mutate their semantics.

### 4.3 Files that must remain noncanonical unless their data source changes

```text
apps/api/app/behavior/exact_time_session_memory.py
apps/api/app/behavior/cross_market_influence.py
```

Their current seeded/synthetic outputs are valuable for tests and UI research but must be tagged fixture/synthetic and excluded from real decision evidence.

---

## 5. Target architecture

```text
                              D1 SAFETY / PIT
                                    |
                                    v
                         PRIMARY D2 STOCK SNAPSHOT
                                    |
                                    v
                         M3.1 PRICE WORLD (LOCKED)
                                    |
                                    +-------------------------+
                                    |                         |
                                    |                         v
                                    |               SESSION/CALENDAR IDENTITY
                                    |                         |
                                    |                         v
                                    |                 SESSION INTELLIGENCE
                                    |
             +----------------------+------------------------------+
             |                      |                              |
             v                      v                              v
      INDEX SOURCE SNAPSHOT   SECTOR SOURCE SNAPSHOT          BREADTH SOURCE
      timestamp/hash/provider timestamp/hash/provider         optional/typed
             |                      |                              |
             +-----------+----------+------------------------------+
                         |
                         v
              CONTEXT SOURCE VALIDATION
         identity / close-time / freshness / skew
                         |
          +--------------+-------------------+
          |              |                   |
          v              v                   v
     INDEX CONTEXT   SECTOR CONTEXT     RELATIVE STRENGTH
          \              |                   /
           \             |                  /
            +------------+-----------------+
                         |
                         v
                   MARKET REGIME
            facts + contradictions only
                         |
                         v
              CANONICAL CONTEXT WORLD
        bounded hashes / reasons / availability
                         |
                         v
                  engine receipts
                         |
                         v
               Stage2IntegrityReport
                         |
                         v
                  DecisionContext
                         |
                         v
                   CURRENT D6
                    UNCHANGED
```

---

## 6. Canonical context-source contract

Every external or contextual input must have an independently auditable identity.

Minimum source identity:

```text
source_id
source_kind                    stock | index | sector | breadth | calendar | cross_market
symbol_or_universe
provider_id
provider_contract_version
source_snapshot_hash
source_timeframe
source_bar_close_time_ns
available_at_ns
d2_decision_time_ns
sequence_or_watermark
freshness_state
clock_skew_state
identity_match
synthetic
```

Hard rules:

1. `available_at_ns <= d2_decision_time_ns`.
2. A bar may contribute only if its close time is `<= d2_decision_time_ns`.
3. `synthetic=true` cannot become real canonical evidence.
4. A missing source gets an explicit unavailable record; it does not get a zero return.
5. Stale and clock-skewed sources are degraded/unavailable according to versioned thresholds.
6. Benchmark mapping must be explicit (`stock -> sector benchmark`, `stock -> broad index benchmark`).
7. Every downstream context hash must list its upstream source hashes.
8. Operational latency/cache fields must not change the deterministic evidence hash.

---

## 7. Canonical M3.2 evidence model

Recommended top-level record per engine:

```text
engine_id
calculation_version
source_snapshot_hash(es)
source_output_hash(es)
d2_snapshot_hash
decision_time_ns
availability                 AVAILABLE | DEGRADED | UNAVAILABLE | ERROR | PENDING
quality
freshness
warmup_complete
sample_size
facts                        bounded typed scalar facts
contradictions               explicit list
reason_codes
warnings
output_hash
used_for_probability=false
may_propose=false
may_set_final_band=false
may_execute=false
```

No canonical context payload should contain:

- full CandleSeries;
- DataFrames;
- full index/sector histories;
- complete provider responses;
- giant arrays;
- hidden model state;
- synthetic fallback values pretending to be real observations.

---

## 8. M3.2 sub-milestones

### M3.2-A — Context Source Contract + Canonical Context Envelope

Build first.

Deliverables:

- immutable typed source observation contract;
- exact D2 binding;
- independent source hash support;
- explicit unavailable/degraded/error states;
- deterministic hash;
- bounded payload guard;
- future/source-time rejection;
- synthetic-source rejection for authoritative evidence;
- zero-authority invariants.

No production activation yet.

### M3.2-B — Canonical Session Intelligence

Input:

- primary D2 closed bars;
- canonical level session identity from M3.1-C;
- optional real persisted session-memory corpus with cutoff-safe `available_at`.

Upgrade requirements:

- closed-bar rule by bar close, not bar start;
- official/session-calendar identity field;
- special session/holiday/half-day state explicit;
- no fixed-date fallback;
- no random profile rates;
- session phase and transition computed once;
- current phase availability independent from historical session-memory availability;
- session memory evidence may downgrade only after sufficient real samples.

### M3.2-C — Canonical Index + Sector Context

Input:

- independently frozen index and sector snapshots;
- benchmark mapping registry;
- provider freshness metadata.

Facts:

- benchmark return over versioned windows;
- direction/state;
- distance to benchmark VWAP/levels where available;
- breadth when actually supplied;
- alignment/contradiction with stock context;
- source age and data coverage.

No missing benchmark may become flat/neutral.

### M3.2-D — Canonical Relative Strength

Calculate once from aligned stock/index/sector observations.

Recommended facts:

```text
stock_return
index_return
sector_return
stock_minus_index
stock_minus_sector
relative_strength_state
rolling_rs_percentile        only with sufficient PIT history
rolling_correlation          explicit insufficient-sample state
lead_lag_state               only when inputs support it
lookback/window version
```

Do not transform missing index/sector data into a 0.5 RS score.

### M3.2-E — Canonical Market Regime

Regime must consume the canonical facts produced by B-D plus M3.1, not refetch/recompute them.

Recommended dimensions:

```text
trend regime
volatility regime
breadth regime
liquidity regime
session regime
index/sector alignment regime
relative-strength regime
gap/opening regime reference
regime confidence/quality
contradictions
```

The result is a regime description, not a final decision.

M3.3 historical feedback, Bayesian priors and failure-memory cooldowns remain separate inputs and must not be hidden inside the M3.2 regime calculation.

### M3.2-F — Production Wiring / Parity / Performance / Lock

Activate receipts:

```text
SESSION_MEMORY
INDEX_CONTEXT
SECTOR_CONTEXT
RELATIVE_STRENGTH
MARKET_REGIME
```

Then populate the existing DecisionContext fields.

D6 inputs remain compatibility-preserved for this milestone unless a later explicit gate authorizes semantic migration.

---

## 9. Calculate-once and performance design

### 9.1 Shared raw context facts

Do not let five engines each rebuild the same returns and session partitions.

Request-local/context-run cache should calculate once:

```text
primary stock returns/window facts
session partition/current phase
index returns/window facts
sector returns/window facts
stock-index aligned return pairs
stock-sector aligned return pairs
breadth aggregate
source freshness/age/skew
benchmark mapping
```

Specialists interpret immutable facts.

### 9.2 No network calls inside DecisionContext assembly

Provider ingestion must happen before deterministic context construction:

```text
provider -> validated source snapshot -> canonical context engine -> receipt -> DecisionContext
```

DecisionContext assembly must never initiate HTTP, database-wide scans, or provider retries.

### 9.3 Real-time optimization

- bounded rolling windows rather than full-history DataFrames;
- vectorized/pure-array calculation for returns/correlation;
- request-local immutable source bundle;
- cache key includes source hashes + algorithm version + parameters;
- concurrent prefetch of independent index/sector/breadth providers outside the deterministic spine;
- one benchmark mapping lookup per symbol, cached by mapping version;
- one session partition per primary D2 snapshot;
- incremental provider snapshots rather than repeated full payload parsing;
- source watermark/sequence allows O(delta) updates later;
- no cross-request mutable calculator state.

Performance targets for the canonical layer should be measured, not guessed. Initial anti-pathology gates:

```text
context envelope build                 < 2 ms for bounded precomputed facts
session canonical interpretation       < 5 ms excluding provider/storage I/O
index+sector+RS interpretation          < 5 ms excluding provider I/O
regime composition                     < 3 ms
bounded canonical context payload      < 32 KiB
DecisionContext build count            == 1
external source parse/freeze count     == 1 per source snapshot
```

These are engineering guardrails, not market-latency guarantees; measured CI/perf evidence will determine final thresholds.

---

## 10. Failure radar — M3.2

M3.2 must explicitly handle:

1. NSE holiday / special session / half day.
2. Timezone/provider timestamp disagreement.
3. Provider clock skew.
4. Stock snapshot is fresh but index snapshot is stale.
5. Sector source missing while index exists.
6. Wrong sector mapping after index reclassification.
7. Index symbol changed/provider renamed instrument.
8. Breadth universe changes mid-session.
9. Breadth value exists but constituent set/watermark is unknown.
10. Benchmark bar is incomplete.
11. Primary stock bar closed but benchmark close has not arrived.
12. Duplicate source snapshots with conflicting values.
13. Out-of-order provider sequence.
14. Zero/NaN/inf returns.
15. Corporate action distorts stock relative strength.
16. Index rebalance distorts sector/RS comparisons.
17. Extremely low volume or halted stock.
18. Circuit/auction state creates non-comparable returns.
19. Regime inputs contradict each other.
20. No history for correlation/RS percentile.
21. Provider failure after a previously cached value.
22. Synthetic/mock provider accidentally enabled.
23. Runtime exception in one context brain.
24. Context payload exceeds bound.
25. Cache key omits source hash or parameters.
26. A later timestamp changes an earlier replay result.

All cases must resolve to explicit typed state/reason codes. None may be silently converted to flat/neutral context.

---

## 11. Testing plan

### Unit / contract

- exact source identity validation;
- deterministic hashing;
- bounded payload;
- unavailable != zero;
- synthetic rejection;
- future source rejection;
- duplicate source rejection;
- benchmark mapping identity.

### Session adversarial

- 09:15 boundary;
- 15:30 boundary;
- incomplete 5m/15m bar;
- holiday/special-session unknown;
- missing first bar;
- timestamp gap;
- stale session-memory corpus;
- synthetic exact-time profile cannot activate.

### Index/sector/RS adversarial

- stock/index/sector timestamps misaligned;
- wrong symbol/sector;
- stale index;
- missing sector;
- missing breadth;
- short source history;
- zero variance correlation;
- NaN/inf source values;
- corporate-action verification unknown.

### Metamorphic/replay

- same source hashes -> same canonical hashes;
- appending future/incomplete source bar -> no causal hash change;
- changing only index snapshot -> index/RS/regime change, session hash does not;
- changing only sector snapshot -> sector/RS/regime change, index hash does not;
- changing only operational latency/cache hit -> no evidence hash change;
- changed legitimate closed source -> only causal downstream hashes change.

### Integration/parity

- M0/M1/M2/M3.1 regressions remain green;
- existing D6 final-band parity diff remains zero;
- Stage2 blocks identity mismatch/future evidence before D6;
- exactly one final-band authority remains D6;
- zero execution authority;
- full API tree.

---

## 12. Pre-mortem — five likely production failures

### Failure 1 — asynchronous benchmark timestamps masquerade as one market state

**Break:** stock 10:00 close is compared with index/sector data from 09:55 or an unfinished 10:00 bar.  
**Prevention:** independent source close-time identity, freshness/skew state, causal cutoff, explicit degraded context.

### Failure 2 — session brain learns from synthetic/fixture memory

**Break:** seeded exact-time rates influence real guidance.  
**Prevention:** `synthetic` source flag, canonical-source allowlist, hard rejection of synthetic evidence from authoritative receipts.

### Failure 3 — missing benchmark becomes neutral

**Break:** unavailable sector/index is coerced to zero return/0.5 RS and looks safe.  
**Prevention:** nullable typed facts, no calculation when required inputs are missing, explicit unavailable reason codes.

### Failure 4 — duplicated context calculation creates latency and disagreement

**Break:** regime, RS, sector and index modules each rebuild arrays/DataFrames with slightly different windows.  
**Prevention:** one immutable context fact kernel/source bundle, downstream interpretation only.

### Failure 5 — M3.2 accidentally becomes a second arbiter

**Break:** market-regime/session layer sets PAPER-CANDIDATE/final band or silently changes D6 inputs.  
**Prevention:** zero-authority contract, authority audit, compatibility-preserved D6 until explicit later milestone.

---

## 13. Build sequence and lock gates

```text
M3.2-A context-source contract
  -> targeted + adversarial + hash/replay tests
  -> GREEN / lock

M3.2-B canonical session
  -> session boundary + incomplete-bar + calendar tests
  -> GREEN / lock

M3.2-C index/sector
  -> source identity/freshness/mapping tests
  -> GREEN / lock

M3.2-D relative strength
  -> aligned-window/correlation/insufficient-history tests
  -> GREEN / lock

M3.2-E market regime
  -> contradiction/missingness/regime replay tests
  -> GREEN / lock

M3.2-F production receipts + DecisionContext integration
  -> D6 parity zero
  -> performance audit
  -> full API tree
  -> authority audit
  -> exact-head workflow
  -> M3.2 GREEN / LOCKED
```

M3.3 may be analyzed and its non-wired contracts may be staged, but its active DecisionContext/runtime migration must not outrun the M3.2 lock.

---

## 14. Definition of done

M3.2 is complete only when:

- all five target engines emit bounded canonical receipts;
- every active fact is causally bound to the D2 decision time;
- independent context sources have snapshot/provider/watermark identity;
- incomplete/future/stale/synthetic evidence is explicitly blocked/degraded;
- session calculation uses closed-bar semantics;
- index/sector benchmark identity is explicit;
- RS does not use neutral defaults for missing data;
- regime consumes canonical facts rather than refetching/recomputing;
- DecisionContext fields are populated from receipts;
- D6 parity remains zero for the locked compatibility comparison;
- M0/M1/M2/M3.1 regressions pass;
- full API tree passes;
- sole-D6 and zero-execution authority audits pass;
- exact-head GitHub Actions run is SUCCESS;
- canonical docs are updated only after observed proof.

Until then M3.2 remains IN BUILD.
