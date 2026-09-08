# M3.1 — Canonical Price Intelligence Migration Plan

> Source: user-supplied `# M3.1 — Canonical Price Intelligen.txt` on 2026-09-08.
> Uploaded source SHA-256: `5c17d996f5e598de81a07e419ea011d4034234f6d0c35d8a793f5734c9f17241`.
> This repository copy is the controlling M3.1 coding reference. Whitespace is normalized to Markdown; no intentional semantic changes were made.

M3.1 should become the **sensory cortex of Trade Vision**: one closed-candle reality, calculated once, interpreted by multiple specialists, with every interpretation carrying causal identity, uncertainty, provenance, and contradiction information.

The goal is **not to add another prediction brain**. It is to make the existing price/candle/level/indicator/MTF intelligence behave like one coherent intelligence system.

The repository already gives us a strong starting point. M2 is locked and produces a deterministic DecisionContext before unchanged D6. Current active receipts include Chart Reasoning, Candle Condition, Levels, Indicators, MTF, Market Structure, etc.; however only `price_structure`, `levels`, and `indicators` are currently canonical M2 fields, while `candle_anatomy` is still unavailable.

A particularly important inefficiency exists today: `classify_conditions()` calls `analyze_candles()` when anatomy is not supplied, while Chart Reasoning independently calls `analyze_candles()` again.

That duplication should disappear in M3.1.

---

## 1. M3.1 target

```text
                         D1
                DATA / PIT / SAFETY
                         |
                         v
                         D2
             CLOSED-CANDLE SNAPSHOT
                         |
                  snapshot_hash
                         |
                         v
            SNAPSHOT FEATURE KERNEL
               CALCULATE ONCE
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
   CANDLE ANATOMY      LEVELS         INDICATORS
        |                |                |
        v                |                |
 CANDLE CONDITION        |                |
        |                |                |
        +--------+-------+----------------+
                 |
                 v
           CHART REASONING
                 |
                 +
                 |
           LOCAL STRUCTURE
                 |
                 +
                 |
             MTF CONTEXT
                 |
                 v
       PRICE EVIDENCE COMPOSER
            NO DECISION POWER
                 |
                 v
       Stage2IntegrityReport
                 |
                 v
       Canonical DecisionContext
                 |
                 v
        LEGACY D6 DURING M3.1
                 |
             UNCHANGED
```

Central rule:

```text
RAW FACT CALCULATED ONCE
        ↓
MANY SPECIALISTS MAY INTERPRET IT
        ↓
EVERY INTERPRETATION IS TRACEABLE
        ↓
NO SPECIALIST GETS FINAL AUTHORITY
```

---

## 2. Build M3.1 as six locked sub-milestones

| Substep | Purpose | Exit condition |
|---|---|---|
| M3.1-A | Canonical snapshot feature kernel | one D2-derived price substrate |
| M3.1-B | Candle intelligence migration | anatomy computed once and canonical |
| M3.1-C | Level intelligence migration | all level facts D2-native and explicit |
| M3.1-D | Indicator intelligence migration | bounded, provenance-rich real indicator evidence |
| M3.1-E | MTF intelligence migration | all HTF evidence PIT-safe and canonical |
| M3.1-F | Price evidence fusion + parity | one coherent price-family world-state, D6 unchanged |

Do not begin M3.2 until all six are green.

---

## 3. M3.1-A — Snapshot Feature Kernel

Create:

```text
apps/api/app/behavior/decision_spine/snapshot_feature_kernel.py
```

This is **not a trading brain**. It is a deterministic computation substrate.

Conceptual contract:

```text
SnapshotFeatureKernel
    identity
        symbol
        timeframe
        decision_time
        snapshot_hash

    bars
        closed_bar_count
        first_timestamp
        last_timestamp
        latest_sequence

    vectors
        open
        high
        low
        close
        volume

    reusable facts
        ranges
        bodies
        typical_price
        returns

    shared calculations
        ATR windows
        VWAP
        ORH
        ORL
        basic rolling volume statistics

    provenance
        kernel_version
        source_snapshot_hash
        feature_hash
```

### Critical invariant

It must consume **only the already-approved D2 snapshot**.

Never:

```text
DecisionContext -> fetch candles again
```

Never independently sort/reconstruct the same price data in multiple specialists.

Instead:

```text
D2
 ↓
normalize/sort once
 ↓
shared immutable feature substrate
```

---

## 4. Separate facts from interpretations

```text
LEVEL 0 — OBSERVATIONS
OHLCV / timestamps / volume / timeframe

LEVEL 1 — DERIVED FACTS
ATR / VWAP / ORH / ORL / EMA / wick % / body % / range % /
volume z-score / distance from level

LEVEL 2 — INTERPRETATION
rejection / compression / expansion / trend health / failed breakout /
absorption-looking / MTF conflict

LEVEL 3 — DECISION RELEVANCE
propose / veto / downgrade

LEVEL 4 — FINAL DECISION
D6 ONLY
```

M3.1 owns Levels 0–2. It must not jump to Level 4.

---

## 5. M3.1-B — compute Candle Anatomy exactly once

Current Candle Anatomy calculates direction, range, body%, upper/lower wick%, close location, range/ATR, volume z-score, body/volume efficiency, effort/result, wick clusters, inside/outside bars, gaps, follow-through, failed follow-through and structure types.

Current duplicate path:

```python
anatomy = request.anatomy or analyze_candles(...)
```

while Chart Reasoning independently calls `analyze_candles(...)`.

Target:

```text
D2
 ↓
CANDLE_ANATOMY
 ↓
CandleAnatomyResult
 ↓
CANDLE_ANATOMY receipt
 ↓
     ├─────────────> CANDLE_CONDITION
     |
     └─────────────> CHART_REASONING
```

No second Anatomy calculation.

Activate canonical evidence:

```text
DecisionContext.candle_anatomy
    source_engine = CANDLE_ANATOMY
    status = AVAILABLE/DEGRADED/ERROR
    source_snapshot_hash = D2
    source_output_hash = anatomy receipt
```

---

## 6. Keep canonical Candle Anatomy bounded

Do not copy every candle/per-bar feature into DecisionContext. Use a bounded summary such as:

```text
candle_anatomy:
    latest:
        direction
        body_pct
        upper_wick_pct
        lower_wick_pct
        close_location
        range_atr
        volume_z
        follow_through_count
        failed_follow_through
        structure_types

    recent_window:
        bullish_count
        bearish_count
        doji_count
        rejection_count
        compression_count
        expansion_count
        inside_count
        outside_count

    quality:
        available
        source_bar_count
        calculation_version

    provenance:
        source_output_hash
```

Full detail remains internal.

---

## 7. Candle Condition becomes interpretation-only

Normal Paper Guidance route:

```text
CANDLE_ANATOMY
      ↓
CANDLE_CONDITION
```

Condition consumes anatomy and classifies facts into opening drive, fake breakout, VWAP rejection, accumulation, distribution, absorption, compression, choppy avoid, manipulated-looking structure, etc. Anatomy remains the causal fact source.

---

## 8. M3.1-C — Level intelligence

Current `analyze_level_context()` already calculates VWAP, opening range, CPR, PDH/PDL relationship, volume-profile context, support/resistance flags, level-respect score and trade blocks.

Target:

```text
D2 Feature Kernel
       ↓
LEVEL_CONTEXT
       ↓
canonical levels evidence
```

Canonical payload should keep separate VWAP, opening range, prior-day levels, CPR, interactions and quality/missing inputs. Missing PDH/CPR/volume profile must be `null` plus explicit unavailable/partial reason, never zero.

---

## 9. Correct session semantics in levels

VWAP must carry explicit session identity:

```text
anchor_session
session_start
bars_used
```

Do not accidentally combine previous-day and current-day candles for a session VWAP.

Opening range must mean configured exchange/session time, e.g. 09:15 to configured OR end, not blindly `bars[:3]`.

Examples for OR15:

```text
5m: 09:15, 09:20, 09:25
3m: 09:15, 09:18, 09:21, 09:24, 09:27
```

Do not assume three bars always means the same opening range.

---

## 10. M3.1-D — Indicator intelligence

The existing real indicator adapter has good foundations: promoted allowlist, per-indicator latency telemetry, LRU cache, one dataframe per call, slow warning/block thresholds and deterministic candle hashing. Do not replace it; improve orchestration.

Normalize vendor outputs into a canonical `IndicatorEvidence` contract:

```text
indicator_id
family
value/state
direction
strength
quality
warmup_complete
output_present
status
latency_ms
cache_hit
calculation_version
```

Aggregate requested/computed/unavailable/no-output/failed/slow counts, family summaries, bounded normalized observations and accounting correctness.

---

## 11. Indicator missingness must be typed

Distinguish:

```text
COMPUTED
NO_SIGNAL
NO_OUTPUT
INSUFFICIENT_WARMUP
DEPENDENCY_UNAVAILABLE
SLOW_BLOCKED
ERROR
UNSUPPORTED
```

Never collapse all of these into `indicator_score = 0`, because neutral and unknown/error are different facts.

---

## 12. Indicator family diversity awareness

Attach:

```text
indicator_family
dependency_family
correlation_group
```

so later reasoning can count independent evidence families instead of treating many correlated moving-average derivatives as independent confirmations. M3.1 exposes metadata; later milestones own decision weighting.

---

## 13. Indicator performance architecture

```text
D2 hash
 ↓
feature kernel
 ↓
one dataframe construction
 ↓
batch compute selected indicators
 ↓
normalize once
 ↓
receipt once
 ↓
context once
```

No recalculation inside context assembly and no unnecessary base-timeframe reruns from MTF.

---

## 14. M3.1-E — MTF intelligence

Each higher timeframe is evaluated at `decision_time_ns` and may explicitly be unavailable.

Example at 10:37:

```text
15m: only bars closed by 10:37
30m: only bars closed by 10:37
1H:  only bars closed by 10:37
Daily: only prior completed daily bar
```

Never use the 10:30–10:45 15m candle at 10:37.

---

## 15. MTF independent identity

Every timeframe record should carry:

```text
timeframe
source_snapshot_hash
source_series_hash
last_closed_bar_timestamp
last_closed_sequence
bars_used
availability
bias
confirmed
quality
reason
```

---

## 16. Price Structure Evidence Composer

M2's 22 canonical fields do not include standalone `mtf_confirmation`. Do not silently stuff MTF into another field with false provenance.

Build deterministic zero-authority `PRICE_STRUCTURE_EVIDENCE`:

```text
MARKET_STRUCTURE_LIQUIDITY
          +
MTF_CONFIRMATION
          ↓
PRICE_STRUCTURE_EVIDENCE
```

Payload:

```text
price_structure:
    local: ...
    multi_timeframe: ...
    agreement:
        aligned
        conflicting
        unavailable
    upstream:
        market_structure_output_hash
        mtf_output_hash
```

Its receipt becomes the source of `DecisionContext.price_structure`. Prefer this over reopening M2 for a 23rd field.

---

## 17. Composer has zero authority

```text
may_propose = false
may_veto = false
may_downgrade = false
may_set_final_band = false
may_execute = false
```

It is a deterministic evidence composer/database view, not a trading brain.

---

## 18. M3.1-F — one price-family causal graph

```text
D2
 |
 +--> FEATURE_KERNEL
 |
 +--> CANDLE_ANATOMY
 |        |
 |        +--> CANDLE_CONDITION
 |        |
 |        +--> CHART_REASONING
 |
 +--> LEVEL_CONTEXT
 |
 +--> SNAPSHOT_INDICATOR_RUNTIME
 |
 +--> MARKET_STRUCTURE_LIQUIDITY
 |
 +--> MTF_CONFIRMATION
          |
          v
   PRICE_STRUCTURE_EVIDENCE
```

Then all receipts feed Stage2IntegrityReport, then DecisionContext.

---

## 19. Explicit upstream dependency hashes

Derived receipts must record upstream hashes.

```text
CANDLE_ANATOMY: D2 X -> output A
CANDLE_CONDITION: D2 X + upstream A -> output B
CHART_REASONING: D2 X + upstream A -> output C
PRICE_STRUCTURE_EVIDENCE: D2 X + structure hash + MTF hash -> output P
DecisionContext -> Z
```

This gives a replayable causal chain.

---

## 20. Dependency DAG validation

Before DecisionContext, validate:

```text
all upstream hashes exist
all parents use same D2
no cycles
no future evidence
no duplicate engine identity
no unknown source
no missing mandatory dependency
```

If a claimed upstream hash does not equal the actual parent receipt hash: **BLOCK**, not warning.

---

## 21. Preserve contradictions

Tests must include cases such as bullish candle + bearish MTF, bullish indicator + failed breakout candle, price above VWAP + PDH rejection, 5m expansion + 15m chop, local breakout + HTF resistance, and high-volume breakout + immediate failed follow-through.

M3.1 does not have to resolve all contradictions. It must preserve both sides faithfully for later D6 reasoning.

---

## 22. No silent evidence compression

Do not replace rich evidence with one `price_score = 0.63`. Retain price structure, candle anatomy, candle condition, levels, indicator families and MTF evidence.

---

## 23. Epistemic quality on every evidence family

Expose equivalents of:

```text
availability
quality
completeness
freshness
warmup
sample_size
source_mode
warnings
limitations
```

so later reasoning can distinguish bullish-but-low-quality evidence from strong evidence.

---

## 24. Typed unavailable states

Use the common availability taxonomy:

```text
AVAILABLE
DEGRADED
UNAVAILABLE
SKIPPED
ERROR
```

and structured reason codes such as:

```text
INSUFFICIENT_BARS
HTF_NOT_CLOSED
MISSING_VOLUME
MISSING_PREVIOUS_DAY
MISSING_SESSION_ANCHOR
DEPENDENCY_UNAVAILABLE
CALCULATION_ERROR
LATENCY_BLOCK
NOT_MIGRATED
```

Structured reason code + human explanation is preferred over arbitrary strings alone.

---

## 25. Performance budget

Initial engineering targets, not market-edge claims:

```text
Feature kernel             < 2 ms typical
Candle Anatomy             < 5 ms / 400 bars
Candle Condition           < 3 ms after anatomy
Level Context              < 2 ms
MTF summarization          < 5 ms per HTF set
DecisionContext assembly   < 2 ms

Indicator runtime:
    cached                 < 1 ms each
    normal                 preserve existing <250 ms warning
    slow warning           250–800 ms
    blocked                >800 ms
```

Profile first. Do not optimize by invisibly changing trading mathematics.

---

## 26. Calculation counters

Expose debug counters such as:

```text
bars_sorted_count = 1
feature_kernel_build_count = 1
candle_anatomy_compute_count = 1
indicator_dataframe_build_count = 1
decision_context_build_count = 1
```

Tests must prove Anatomy compute count equals one.

---

## 27. Deterministic caching

Cache identity must include enough causal information:

```text
engine_version
snapshot_hash / relevant window hash
parameters
timeframe
```

Conceptually:

```text
SHA256(engine_version + snapshot_hash + normalized_parameters)
```

Never cache only by symbol or symbol+timeframe.

---

## 28. Parameter identity

Different parameters must generate different evidence fingerprints. ATR(14) != ATR(20), and later ORB15 != ORB5. Engine output hashes must reflect configuration.

---

## 29. M3.1 does not migrate D6

During M3.1:

```text
new canonical evidence -> audit/replay
legacy D6 inputs -> unchanged
```

Only after parity may later milestones replace corresponding D6 compatibility inputs. Broad D6 consumption belongs mainly to M4.

---

## 30. Legacy debt boundary

Do not remove `indicator_signal_score = 0.0` during M3.1 unless the roadmap explicitly assigns that consumer migration. Preferred sequence:

```text
M3.1: real canonical indicator evidence exists
M4:   D6 begins consuming canonical indicator evidence
```

---

## 31. Mandatory test matrix

1. Causal identity: same D2 hash, valid upstream hashes, changed closed candle propagates.
2. No future leakage: unfinished base candle rejected; unfinished HTF excluded; future HTF rejected.
3. Calculate once: Anatomy once; indicator dataframe once; context once.
4. Candle correctness: doji, trend, rejection, inside/outside, expansion, compression, failed follow-through, zero-range, missing volume.
5. Levels: session VWAP, OR5/OR15/OR30 geometry, CPR, PDH/PDL, missing prior day, multi-session input.
6. Indicators: valid output, no signal, warmup, dependency error, latency warning/block, cache replay, deterministic payload.
7. MTF: aligned, partial, conflict, no HTF, unfinished HTF, duplicate timeframe, wrong symbol, wrong time boundary.
8. Contradictions: bullish 5m/bearish 15m, bullish indicator/rejection candle, breakout/PDH rejection.
9. Failure injection: Anatomy, Levels, Indicator, MTF, composer failure.
10. Authority: no M3.1 finalizer/executor; D6 sole final-band authority.

---

## 32. Property/invariant testing

For generated valid candle sequences, verify:

```text
high >= max(open, close)
low <= min(open, close)
0 <= body_pct <= 100
0 <= upper_wick_pct <= 100
0 <= lower_wick_pct <= 100
body_pct + upper_wick_pct + lower_wick_pct ~= 100 for non-zero range
0 <= close_location <= 1
same inputs -> same hashes
```

---

## 33. Metamorphic tests

- Price scaling: multiply OHLC by 10; ratio features remain equivalent.
- Volume scaling: multiply volume by a constant; relative z-scores remain approximately invariant.
- Duplicate replay: same D2 state in different request objects -> same output hashes.
- Ordering: equivalent uniquely ordered candles normalize to the same canonical result if D1/D2 permits normalization.

---

## 34. Session/timeframe adversarial tests

Explicitly test boundaries around 09:15, 09:16, 09:20, 09:30, 10:00, 11:30, 15:10, 15:30 and timeframes 1m, 3m, 5m, 15m, 30m, 1H, 4H, daily.

Example: 10:29:59 must not see a 30m candle ending at 10:30:00.

---

## 35. Evidence-size budget

DecisionContext summaries must remain bounded. Never put 400 bars, 50 full indicator arrays, pandas DataFrames, or entire historical signal history inside DecisionContext.

---

## 36. Suggested M3.1 files

```text
decision_spine/
    snapshot_feature_kernel.py                 NEW
    price_structure_evidence.py                NEW
    decision_context.py                        MINIMAL / preferably unchanged
    paper_guidance_decision_context_adapter.py EDIT

behavior/
    candle_anatomy.py                          EDIT
    condition_classifier.py                    EDIT
    chart_reasoning_volatility.py              EDIT
    context_engines.py                         EDIT
    real_indicator_adapter.py                  TARGETED EDIT
    paper_guidance_spine_m3_1_impl.py          NEW

tests/decision_spine/
    test_snapshot_feature_kernel.py            NEW
    test_m3_1_candle_pipeline.py               NEW
    test_m3_1_levels.py                        NEW
    test_m3_1_indicator_pipeline.py            NEW
    test_m3_1_mtf_pipeline.py                  NEW
    test_m3_1_price_evidence.py                NEW
    test_m3_1_replay.py                        NEW
    test_m3_1_adversarial.py                   NEW
```

Keep `paper_guidance_spine_legacy.py` and `paper_guidance_spine_m2_impl.py` as parity references until M3.1 locks.

---

## 37. Version everything

```text
snapshot-feature-kernel.v1
candle-anatomy.v0.16
condition-classifier.v0.16
level-context.v0.17
indicator-evidence.v1
mtf-confirmation.v2
price-structure-evidence.v1
paper-guidance-m3.1.v1
```

A semantic version change must affect output identity.

---

## 38. Runtime failure philosophy

```text
KNOWLEDGE ↓
AUTHORITY ↓
```

Never `ENGINE ERROR -> 0.0 -> normal scoring`.

Use `ENGINE ERROR -> EvidenceBlock.ERROR -> explicit reason -> reduced epistemic confidence`.

Causal integrity violation -> BLOCK before DecisionContext/D6. Optional evidence failure -> DEGRADED/UNAVAILABLE according to contract.

---

## 39. No arbitrary ML/LLM in M3.1

M3.1 needs deterministic sensory truth. First establish correct observations, causal identity, missingness, provenance and contradiction preservation. Later intelligence layers can reason over them.

---

## 40. Useful meaning of “AGI-level” here

Do not claim the application is AGI. The useful engineering target is:

```text
SELF-CONSISTENT WORLD MODEL
+
SPECIALIST PERCEPTION
+
EXPLICIT UNCERTAINTY
+
CAUSAL MEMORY
+
MULTIPLE HYPOTHESES
+
CONTRADICTION AWARENESS
+
COUNTERFACTUAL FAILURE THINKING
+
REPLAY
+
SELF-AUDIT
+
STRICT AUTHORITY
```

M3.1 establishes world model, specialist perception and explicit uncertainty. M3.3 deepens memory; M3.4 adds hypotheses/ORB/AFRE; M7 attacks conclusions.

---

## 41. Exact recommended build order

```text
M3.1-A0
Record M3.1 start in canonical tracker
freeze M2 verified baseline 105561fc...

M3.1-A1
Build immutable SnapshotFeatureKernel
test deterministic D2 identity
benchmark it

M3.1-B1
Expose real CANDLE_ANATOMY receipt

M3.1-B2
Pass same Anatomy object to CANDLE_CONDITION + CHART_REASONING

M3.1-B3
Prove Anatomy calculate_count == 1

M3.1-C1
Make Level Context use explicit session/timeframe semantics

M3.1-C2
Fix opening-range definition away from blindly bars[:3]

M3.1-C3
Make VWAP explicitly session anchored

M3.1-D1
Normalize real indicator outputs

M3.1-D2
Add family/dependency metadata and typed missing/error states

M3.1-D3
Preserve/better exploit existing cache

M3.1-E1
Strengthen MTF PIT identity

M3.1-E2
Explicit HTF closed-bar hashes and missing timeframe states

M3.1-F1
Build PRICE_STRUCTURE_EVIDENCE composer

M3.1-F2
Add upstream receipt hashes / DAG audit

M3.1-F3
Populate canonical price_structure / candle_anatomy / levels / indicators

M3.1-F4
Run contradiction/adversarial matrix

M3.1-F5
Prove M2 -> M3.1 D6 parity

FULL API REGRESSION
AUTHORITY AUDIT
PERFORMANCE AUDIT
COMMIT
M3.1 GREEN / LOCKED
```

---

## 42. M3.1 mandatory GREEN gate

```text
CANDLE ANATOMY
✓ real canonical evidence
✓ computed only once
✓ same object feeds dependent specialists
✓ deterministic

LEVELS
✓ session-aware VWAP
✓ timeframe-aware opening range
✓ explicit unavailable inputs
✓ D2 causal

INDICATORS
✓ real normalized evidence
✓ complete accounting
✓ family/dependency identity
✓ deterministic cache
✓ no error->neutral conversion

MTF
✓ closed-candle only
✓ each timeframe independently identified
✓ incomplete HTF excluded
✓ explicit unavailable/conflict

PRICE STRUCTURE
✓ local + MTF provenance
✓ upstream hashes preserved
✓ no new decision authority

DECISION CONTEXT
✓ exact Stage2 membership
✓ all migrated evidence D2 causal
✓ deterministic context hash

D6
✓ identical behavior to locked M2 baseline
✓ still sole final-band authority

SAFETY
✓ trade_allowed = false
✓ order_routing_enabled = false
✓ live_trading_blocked = true

TESTS
✓ targeted
✓ integration
✓ adversarial
✓ replay
✓ full API
✓ authority

PERFORMANCE
✓ no duplicate major calculations
✓ bounded context payload
✓ latency measured
```

---

## Final architecture after M3.1

```text
                    VERIFIED D2
                        |
                        v
               FEATURE KERNEL
                 CALCULATE ONCE
                        |
       +----------------+----------------+
       |                |                |
       v                v                v
 CANDLE ANATOMY       LEVELS         INDICATORS
       |
       +------------+
       |            |
       v            v
 CONDITION         CHART
       |            |
       +------+-----+
              |
       MARKET STRUCTURE
              |
              +---------+
                        |
                    MTF CONTEXT
                        |
                        v
              PRICE STRUCTURE EVIDENCE
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

M3.1 is **not more intelligence modules, but a much more intelligent way of computing, sharing, validating, remembering and trusting price evidence.**

The first coding move is **M3.1-A: build the immutable D2 Snapshot Feature Kernel and eliminate duplicate Candle Anatomy computation** so every later M3.1 specialist has a fast, deterministic, shared sensory foundation.
