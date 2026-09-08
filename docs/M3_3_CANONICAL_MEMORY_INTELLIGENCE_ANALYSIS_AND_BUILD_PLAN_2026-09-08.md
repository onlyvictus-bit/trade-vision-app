# M3.3 — Canonical Memory Intelligence

**Date:** 2026-09-08  
**Branch:** `m3-2-context-intelligence` (analysis staged while M3.2 is the active implementation milestone)  
**Base / locked predecessor:** M3.1 final head `20d2d7b5889b09cd593401e8f70ec53cc299c51e`  
**State at creation:** ANALYSIS COMPLETE / ACTIVE RUNTIME MIGRATION DEFERRED UNTIL M3.2 LOCK  
**Scope:** persisted indicator memory, session memory corpus, pattern/day-shape memory, analog memory, nine-candle memory, reliability/feedback memory, OOD/quarantine and memory provenance.  
**Out of scope:** activating synthetic fixtures as real evidence, ORB/AFRE strategy migration, risk/D6 redesign, execution.

---

## 1. Mission

M3.3 turns Trade Vision's existing historical/reliability/analog subsystems into a canonical **memory world** that can answer:

- What did this stock do in genuinely comparable past states?
- How many independent, point-in-time-valid examples exist?
- Were those examples labeled only after their outcome horizons completed?
- Which memory facts are real persisted observations versus fixtures/generated research scaffolds?
- Is the current state in-distribution or unlike the stored corpus?
- Is recent performance degrading, regime-shifting, or quarantined?
- What historical evidence is strong enough to be visible to later reasoning without becoming a final decision authority?

The target is not “learn live and mutate itself.” The target is **safe adaptive memory**:

```text
OBSERVE CLOSED FACTS
        ↓
STORE VERSIONED FEATURE/OUTCOME RECORDS
        ↓
LABEL ONLY AFTER OUTCOME HORIZON COMPLETES
        ↓
BUILD CUT-OFF-SAFE MEMORY CORPUS
        ↓
QUERY / MATCH / CALIBRATE
        ↓
EXPOSE BOUNDED EVIDENCE + UNCERTAINTY
        ↓
D6 REMAINS SOLE FINAL-BAND AUTHORITY
```

M3.3 must preserve:

```text
future outcomes cannot influence past decisions
fixture/generated history cannot become real evidence
missing memory != failure
empty memory != zero probability
similarity != causality
correlation != independent confirmation
overlapping episodes cannot inflate sample size
model/live weights cannot silently mutate
D6 remains sole final-band authority
no execution authority
```

"AGI-level" is interpreted here as durable episodic memory, provenance, contradiction awareness, self-audit, OOD detection, calibration, and modular future learning. It does not mean the system can guarantee correct market decisions or autonomous general intelligence.

---

## 2. Current M3.3 brain inventory — repository truth

### 2.1 `PERSISTED_INDICATOR_MEMORY` — strongest current real-memory path

Current production path:

`apps/api/app/behavior/paper_guidance_spine_legacy.py::_build_persisted_memory_evidence()`

Current storage:

- SQLite table `indicator_signal_history`
- indexes by symbol/timeframe/indicator/signal time, regime/session, manifest, and label.

Current good properties:

1. Paper Guidance already uses persisted indicator history rather than caller-supplied `historical_match_count` for authority.
2. Records are queried with a decision-time cutoff.
3. Only complete labels are counted.
4. `counted_in_reliability`, `no_future_leakage`, `missing_mask`, `decision_time_ns`, `signal_time_ns`, and `created_at` are checked.
5. Caller historical counts are preserved only as non-authoritative diagnostics.
6. Low evidence is explicit.
7. The receipt is already D2-bound to the current snapshot.

Main weaknesses:

1. **N-query hot path:** one storage query is executed per indicator. With dozens of promoted indicators, this is unnecessary SQLite overhead.
2. Each query can fetch up to 500 records, then Python deduplicates by `history_id`.
3. The memory receipt reports a count but not a deterministic corpus hash/watermark describing exactly which records were considered.
4. No single query proves/returns the max included `created_at`, decision cutoff, manifest versions, or outcome-label versions as a corpus identity.
5. Current evidence count mixes many indicators; correlated indicator families can inflate the impression of independent historical evidence unless M3.3 separates record count from independent-episode count.
6. There is no canonical memory envelope shared with pattern/analog/9C memory.

**Decision:** preserve semantics, replace the N-query implementation with a batched indexed PIT query, and add a deterministic memory-corpus identity. This is the first M3.3 production candidate after M3.2 locks.

---

### 2.2 Indicator reliability memory

Existing file:

`apps/api/app/behavior/indicator_reliability_memory.py`

Useful existing behavior:

- outcome labels distinguish complete vs pending horizons;
- same-bar target/stop ambiguity is conservatively stop-first without lower-TF proof;
- MFE/MAE and target/stop ordering are calculated;
- minimum sample size and Bayesian shrinkage exist;
- per-stock, per-regime, per-session buckets exist;
- OOD/regime-shift quarantine concepts exist;
- reliability can reduce lag-vote confidence but is research-only.

Critical migration issue:

When no persisted labels exist, the current report falls back to deterministic **fixture labels**. That is acceptable for testing/demo output but cannot become canonical M3.3 real evidence.

Canonical rule:

```text
persistent real labels available -> evaluate real corpus
no persistent real labels         -> UNAVAILABLE / LOW_EVIDENCE
fixture fallback                  -> test/research-only, never canonical authority
```

A canonical reliability receipt must expose:

```text
history_source
fixture_fallback_used
sample_count
independent_episode_count
minimum_sample_pass
posterior/shrinkage method version
quarantine status
corpus hash
label schema/version
feature/indicator registry versions
```

---

### 2.3 `SESSION_MEMORY`

Existing file:

`apps/api/app/behavior/session_memory.py`

This overlaps M3.2 and M3.3:

- **M3.2 owns current session context** derived from D2-closed observations.
- **M3.3 owns historical session memory** derived from stored past outcomes.

Useful historical concepts:

- phase-specific continuation/fakeout rates;
- day-of-week memory;
- minimum/strong sample thresholds;
- stock personality / session profiles.

Migration risks:

- profile timestamps must be cutoff-safe;
- profiles generated after the decision time cannot be injected into a past replay;
- overlapping records must not inflate independent evidence counts;
- “best trade window” is a research summary, not trade authority;
- static time windows need the M3.2 session/calendar identity.

**Decision:** split current-session interpretation from historical session corpus. The canonical M3.3 session-memory record consumes the M3.2 session ID as a conditioning key.

---

### 2.4 `PATTERN_MEMORY`

Existing file:

`apps/api/app/behavior/pattern_memory.py`

Useful existing behavior:

- 13-field day-shape vector;
- cosine + DTW + time-decay matching;
- continuation/reversal/fakeout/range outcomes;
- minimum sample guards;
- replay concepts;
- visible failure reason and feature-match summaries.

Critical issues before canonical use:

1. `_available_bars()` filters by bar start timestamp rather than close timestamp; this needs the same D2 closed-bar correction as M3.2.
2. `calculate_day_shape_vector()` uses fixed bar counts for “first 15m/30m” rather than explicitly tiling wall-clock windows by source timeframe. M3.1 already demonstrated why `bars[:3]` is unsafe.
3. Missing `previous_close` becomes numeric `gap_pct=0.0`, which can masquerade as a true flat gap.
4. Fallback day-shape vectors are synthesized from a handful of other fields when the real vector is missing. Those should be marked imputed/synthetic and not treated as equal to observed vectors.
5. `similar_day_id` uses a `mock-day-` label even for memory-backed records.
6. Similarity search iterates/scales in Python and will not be efficient for a large historical corpus.
7. Independent episode/non-overlap accounting is not strong enough for probability claims.

**Decision:** preserve current research API; create canonical day-shape schema v2 using M3.1/M3.2 facts, explicit missing masks, real window semantics, and an indexed corpus.

---

### 2.5 `ANALOG_MEMORY`

Existing files:

- `apps/api/app/behavior/analog_research.py`
- `apps/api/app/behavior/combination_similarity.py`
- `apps/api/app/behavior/nine_candle_history.py`
- feature-store / redundancy / analog index manifests.

The architectural ideas are strong:

- hard-context prefilter before exact refinement;
- mixed distance rather than naive cosine for heterogeneous fields;
- non-overlap guards;
- false-discovery control;
- holdout/generalization checks;
- matched and mismatched feature explanations;
- OOD detection;
- index manifests already have active pointers, version, artifact hash, record count and vector dimension.

But much of the current runtime is explicitly research scaffolding:

- `combination_similarity.py` generates matches using `random.Random` and labels its distance `mock_mixed_distance`;
- value bands and conditional rules in `analog_research.py` are hard-coded research candidates;
- `nine_candle_history.py` can fall back to deterministic generated history;
- current 9C current descriptor can come from the mock evidence packet;
- generated history and mock analogs cannot be activated as real historical proof.

**Decision:** do not throw away these modules. Their contracts/tests are useful prototypes. M3.3 must replace the data plane beneath them:

```text
real feature snapshots
+ real labeled episodes
+ real index artifact
+ PIT cutoff
+ non-overlap groups
+ versioned exact distance
= canonical analog memory
```

---

### 2.6 `NINE_CANDLE_MEMORY`

Registered engine:

`NINE_CANDLE_MEMORY` -> `app.behavior.nine_candle_hybrid`

Current registry notes already say runtime contract stabilization is required before canonical authority use.

Useful existing architecture:

- stable feature manifest and order hash;
- explicit missing mask;
- source mode / runtime status;
- probability-enabled mask;
- promoted real indicator bridge;
- analog index manifest/version concepts;
- multiple future horizons;
- outcome label storage;
- OOD and winner/failure analog concepts.

Critical current limitations:

1. `build_evidence_packet()` currently uses mock last-9 candles, mock levels, a fixed decision time, and a current 9C packet not sourced from the Paper Guidance D2 snapshot.
2. If real HSTRY candles are unavailable, real-indicator mode can use synthetic fallback candles. The current code correctly describes these as explanation-only in some audit paths, but canonical M3.3 must hard-exclude them.
3. `MODEL_VERSION = "mock"`.
4. Several 9C/analog reports still use deterministic generated history or mock index data.
5. `build_evidence_packet()` is `lru_cache`d by symbol/timeframe/use_real_indicators—not by D2 snapshot hash—so it is not a valid canonical cache identity for changing market state.

**Decision:** M3.3 should create a snapshot-native 9C adapter over the already canonical M3.1 indicator evidence and primary D2 series. It should never call the legacy mock evidence packet on the active Paper Guidance route.

---

### 2.7 `PTA_MARKER_RUNTIME`

Current implementation:

`apps/api/app/behavior/real_indicator_adapter.py::compute_pta_marker_outputs_with_telemetry()`

Good:

- marker events are treated as availability/explanation evidence;
- no probability/trade authority flags;
- dependency availability is visible.

Needs for canonical M3.3/9C integration:

- same canonical `IndicatorEvidence`-style provenance envelope as M3.1-D;
- source snapshot hash/timeframe/window hash;
- deterministic event hash;
- warmup/dependency/no-signal distinction;
- bounded event summary rather than arbitrary marker arrays;
- D2 snapshot-native candle input;
- no standalone probability or final-band authority.

---

## 3. What is currently wired?

### Active real memory in Paper Guidance

```text
PERSISTED_INDICATOR_MEMORY -> yes
```

It influences `authoritative_count` / low-evidence gating, while D6 remains final authority.

### Registered but not canonical/active in current Paper Guidance

```text
SESSION_MEMORY
PATTERN_MEMORY
ANALOG_MEMORY
NINE_CANDLE_MEMORY
PTA_MARKER_RUNTIME
```

M0 deliberately represented 9C/PTA as skipped until they become D2-snapshot-native. That guard remains correct.

### DecisionContext destination fields already exist

M2 created:

```text
session_memory
pattern_memory
analog_memory
nine_candle_memory
```

These should remain unavailable until canonical M3.3 receipts are real and causal.

---

## 4. New files vs editing old files

### 4.1 New canonical production files are required

Recommended:

```text
apps/api/app/behavior/decision_spine/canonical_memory_intelligence.py
apps/api/app/behavior/decision_spine/memory_corpus.py
apps/api/app/behavior/decision_spine/canonical_nine_candle_memory.py
apps/api/app/behavior/decision_spine/canonical_analog_memory.py
apps/api/app/behavior/paper_guidance_spine_m3_3_impl.py
apps/api/tests/decision_spine/test_m3_3_memory_contract.py
apps/api/tests/decision_spine/test_m3_3_persisted_indicator_memory.py
apps/api/tests/decision_spine/test_m3_3_session_memory.py
apps/api/tests/decision_spine/test_m3_3_pattern_memory.py
apps/api/tests/decision_spine/test_m3_3_nine_candle_memory.py
apps/api/tests/decision_spine/test_m3_3_analog_memory.py
apps/api/tests/decision_spine/test_m3_3_replay.py
apps/api/tests/decision_spine/test_m3_3_adversarial.py
.github/workflows/m3-3-memory-intelligence.yml
```

### 4.2 Existing files need surgical edits

Likely:

```text
apps/api/app/storage.py
apps/api/app/behavior/paper_guidance_spine.py
apps/api/app/behavior/decision_spine/paper_guidance_decision_context_adapter.py
apps/api/app/behavior/real_indicator_adapter.py
```

Optional compatibility fixes after parity tests:

```text
apps/api/app/behavior/session_memory.py
apps/api/app/behavior/pattern_memory.py
apps/api/app/behavior/indicator_reliability_memory.py
```

### 4.3 Do not “upgrade” mock modules by merely renaming them

The following current paths cannot become canonical just by changing labels/version strings:

```text
exact_time_session_memory synthetic profiles
cross_market_influence mock provider values
combination_similarity generated analog matches
analog_research hard-coded value bands/rules
nine_candle_history deterministic generated history fallback
nine_candle_hybrid mock evidence packet/current candles
indicator reliability fixture fallback
```

They need real persisted inputs or must remain explicitly research-only.

---

## 5. Target architecture

```text
                   CANONICAL D2 + M3.1 + M3.2 FACTS
                              |
                              v
                    FEATURE/EPISODE FREEZER
                              |
            +-----------------+-------------------+
            |                 |                   |
            v                 v                   v
    INDICATOR SIGNALS   SESSION/DAY SHAPE      9C STATE
            |                 |                   |
            +-----------------+-------------------+
                              |
                              v
                  VERSIONED MEMORY RECORDS
           signal-time / decision-time / source hashes
                              |
                              v
                 DELAYED OUTCOME LABELER
             outcome only after horizon completes
                              |
                              v
                   PIT MEMORY CORPUS
          available_at <= current decision time
                              |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
 RELIABILITY MEMORY      PATTERN MEMORY        ANALOG INDEX
       |                      |                      |
       +-------------+--------+----------------------+
                     |
                     v
           OOD / DRIFT / QUARANTINE
                     |
                     v
          CANONICAL MEMORY RECEIPTS
                     |
                     v
               DecisionContext
                     |
                     v
                  D6
             SEMANTICS LOCKED
```

---

## 6. Canonical memory-corpus identity

Every active memory query must identify **the exact historical corpus knowable at the decision time**.

Required fields:

```text
memory_engine_id
corpus_version
query_version
symbol
timeframe
conditioning_keys
current_d2_snapshot_hash
current_decision_time_ns
max_record_available_at_ns
record_count
independent_episode_count
complete_label_count
pending_label_count_excluded
quarantined_count_excluded
synthetic_count_excluded
feature_manifest_versions
indicator_registry_versions
label_versions
record_ids_hash
corpus_hash
storage_watermark
```

The corpus hash must change if a legitimate historical record becomes newly available before a later decision, but replaying an older decision must select the old cutoff and reproduce the old corpus hash.

---

## 7. Independent evidence and overlap control

Raw record count is not enough.

Examples of duplicate/non-independent evidence:

- 40 indicators firing on the same 5-minute episode;
- the same breakout stored at 1m/3m/5m;
- overlapping 9C windows shifted by one candle;
- multiple horizons for the same setup;
- repeated copies after an index rebuild.

M3.3 must define a versioned `episode_id` / `non_overlap_group_id` derived from:

```text
symbol
market session/trading date
causal event window
setup/feature identity
source snapshot family
```

Canonical outputs expose both:

```text
raw_record_count
independent_episode_count
```

Probability/calibration eligibility must use the independent count, not the inflated raw count.

---

## 8. M3.3 sub-milestones

### M3.3-A — Memory Corpus + Batched Persisted Indicator Memory

First production candidate.

Deliverables:

- one batched storage query for a set of indicator IDs;
- SQL/Python PIT cutoff parity with current behavior;
- deterministic record/corpus hash;
- independent episode accounting;
- explicit version/watermark metadata;
- zero fixture fallback on canonical route;
- exact parity of current low-evidence behavior before any D6 semantic change.

Performance goal: replace O(number_of_indicators) DB round trips with O(1) query per primary memory corpus.

### M3.3-B — Canonical Reliability Memory

Use only persisted complete real labels.

- Bayesian shrinkage/calibration versioned;
- no fixture fallback;
- stock/regime/session conditioning keys from M3.2;
- OOD/regime-shift quarantine;
- recent-vs-old drift stats;
- family/correlation-aware aggregation;
- no direct final-band authority.

### M3.3-C — Canonical Historical Session Memory

- conditioning key = M3.2 canonical session identity;
- cutoff-safe persisted records;
- phase/day/calendar class sample counts;
- continuation/reversal/fakeout distributions;
- no synthetic exact-time profiles;
- minimum independent sample guard.

### M3.3-D — Canonical Pattern / Day-Shape Memory

Build day-shape v2 from canonical facts:

- exact session windows, not `bars[:3]` / `bars[:6]`;
- explicit missing mask;
- no unknown previous-close -> zero gap substitution;
- source snapshot hash;
- deterministic vector hash;
- robust scaling/normalization version;
- indexed top-k retrieval;
- non-overlap groups;
- visible match + mismatch explanations.

### M3.3-E — Snapshot-native Nine-Candle Memory

Current 9C architecture is preserved but the data plane changes:

```text
current last 9 CLOSED bars -> current D2 snapshot
indicator values           -> M3.1-D canonical evidence / snapshot-native history
levels                      -> M3.1-C canonical levels
session/regime              -> M3.2 canonical context
historical outcomes         -> real persisted 9C labels
index                       -> verified artifact manifest
```

Hard exclusions:

```text
mock current candles
fixed decision time
synthetic fallback candles
mock model probability
mock analog index
```

### M3.3-F — Canonical Analog Memory

Pipeline:

```text
hard causal/context filters
-> ANN/index shortlist
-> exact mixed-distance refinement
-> non-overlap enforcement
-> outcome distribution
-> holdout/calibration/OOD checks
-> bounded analog receipt
```

The existing research modules provide useful candidate contracts, but the canonical implementation must retrieve real records.

### M3.3-G — Drift / OOD / Quarantine

Memory should become less trusted when the world changes.

Detect:

- current feature vector far from historical support;
- volatility/regime distribution shift;
- recent reliability decay;
- corporate-action/version contamination;
- stale index artifact;
- feature manifest mismatch;
- provider/data schema transition;
- too-small recent sample.

Quarantine reduces/withholds memory evidence; it cannot create a trade signal.

### M3.3-H — Production wiring / lock

Activate canonical receipts into existing DecisionContext fields:

```text
PERSISTED_INDICATOR_MEMORY
SESSION_MEMORY
PATTERN_MEMORY
ANALOG_MEMORY
NINE_CANDLE_MEMORY
PTA_MARKER_RUNTIME (bounded availability/explanation only)
```

D6 remains unchanged until the explicit later orchestration milestone.

---

## 9. Storage optimization

### Current issue

The production persisted-memory loop effectively does:

```python
for indicator_id in indicator_ids:
    SELECT ... WHERE symbol=? AND timeframe=? AND indicator_id=? ... LIMIT 500
```

For ~50 indicators this creates dozens of DB round trips and can materialize tens of thousands of records before deduplication.

### Target SQL shape

One indexed query:

```text
WHERE symbol = ?
  AND timeframe = ?
  AND indicator_id IN (...)
  AND counted_in_reliability = 1
  AND label_status = 'complete'
  AND signal_time_ns <= ?
  AND decision_time_ns <= ?
  AND created_at <= ?
ORDER BY signal_time_ns DESC
```

Then apply an overall safe bound and group/partition as needed.

Recommended new/adjusted indexes after EXPLAIN verification:

```text
(symbol, timeframe, counted_in_reliability, label_status, decision_time_ns, signal_time_ns)
(symbol, timeframe, indicator_id, decision_time_ns DESC)
```

Do not add indexes blindly; verify SQLite query plan in tests/benchmark before final lock.

### Larger future corpus

As history grows:

- SQLite remains metadata/index of record identity;
- feature vectors/large arrays stay in Parquet/artifact files;
- analog ANN artifacts remain versioned immutable files;
- active index pointer swap is atomic;
- background/offline index rebuild is allowed only as an artifact creation process; the decision path reads a fixed verified active manifest;
- no live model-weight mutation.

---

## 10. Real-time efficiency design

1. No full-history scans inside Paper Guidance.
2. One PIT corpus query per memory family, not per feature.
3. Current feature vectors calculated once from M3.1/M3.2 facts.
4. ANN shortlist before exact distance.
5. Exact distance only on bounded `top_k` candidates.
6. Corpus/index cache keyed by corpus hash + feature manifest + algorithm version.
7. Request-local memoization for repeated specialist views.
8. Storage watermark lets later requests know whether the memory corpus changed.
9. Incremental index build consumes only new completed labeled episodes.
10. Pending outcomes remain separate and never contaminate success/failure stats.

Initial engineering guardrails to benchmark and refine:

```text
batched primary memory query          < 10 ms warm local SQLite for bounded corpus
corpus hash build                     < 3 ms for selected IDs
canonical reliability aggregation     < 5 ms per bounded family batch
ANN shortlist                         < 5 ms for target corpus sizes after index load
exact refinement                      bounded top-k only
canonical memory payload              < 32 KiB per memory engine receipt
```

These are starting anti-pathology thresholds, not guaranteed market latency.

---

## 11. Failure radar — M3.3

M3.3 must explicitly detect or guard:

1. Outcome label not complete yet.
2. Label record created after current replay decision.
3. Signal timestamp after decision time.
4. Historical record source snapshot missing.
5. Historical record snapshot hash malformed/mismatched.
6. Feature manifest version mismatch.
7. Indicator registry version mismatch.
8. Corporate-action adjusted vs raw history mismatch.
9. Duplicate labels for one setup/horizon.
10. Same-bar target/stop ambiguity.
11. Overlapping episodes inflating sample count.
12. Multi-timeframe duplicates.
13. Many correlated indicators inflating evidence.
14. Fixture fallback activated accidentally.
15. Deterministic generated history activated accidentally.
16. Mock 9C evidence packet activated accidentally.
17. Mock analog index activated accidentally.
18. Empty corpus becomes 0% success probability.
19. Low sample produces overconfident probability.
20. OOD current state still uses historical calibration.
21. Stale analog index after feature-manifest update.
22. ANN artifact hash mismatch.
23. Active-pointer swap not atomic.
24. Corpus query uses current database state when replaying old decisions without cutoff.
25. Clock/timezone mismatch in stored created-at values.
26. Historical session calendar identity differs from current mapping.
27. Deleted/corrected labels are not versioned/audited.
28. Memory poisoning from malformed provider data.
29. Outcome rules changed but old labels are mixed without label-version stratification.
30. Strategy entry/stop/target definitions changed but historical outcomes are treated as comparable.
31. Similarity metric/config changes without index rebuild.
32. Cache key omits corpus hash/manifest/version.
33. Memory query/ANN latency explodes with corpus growth.
34. One corrupted record crashes the entire memory family.
35. Memory layer tries to set final band or execution action.

---

## 12. Testing plan

### Storage/PIT tests

- batched query result set equals legacy N-query set for fixed fixtures;
- created-after-decision excluded;
- pending label excluded;
- future signal excluded;
- uncounted/missing-mask excluded;
- exact record/corpus hash deterministic;
- older replay sees same old corpus after newer records are added.

### Fixture/synthetic isolation

- indicator reliability fixture fallback cannot create canonical receipt;
- generated 9C history cannot create canonical receipt;
- mock 9C current packet cannot create canonical receipt;
- mock analog matches cannot create canonical receipt;
- synthetic PTA/indicator fallback cannot become probability evidence.

### Independent evidence

- 50 indicators same episode -> raw_count=50, independent_episode_count=1 (or defined grouped count);
- overlapping 9C windows deduplicate/non-overlap correctly;
- multi-horizon labels do not become independent episodes.

### Replay/metamorphic

- appending a record created after decision -> old corpus hash unchanged;
- adding a valid older record available before later decision -> later corpus hash changes;
- cache hit/latency changes -> evidence hash unchanged;
- changing feature manifest -> old index rejected/quarantined;
- same query/source corpus -> byte-stable receipt hash.

### Performance

- compare N-query vs batched query count/latency;
- verify query plan uses intended index;
- bounded top-k analog refinement;
- no full database scan in request path.

### Integration

- M0/M1/M2/M3.1/M3.2 remain green;
- DecisionContext builds once;
- Stage2 blocks malformed/future memory receipts;
- D6 parity zero during migration;
- exactly one final-band authority;
- zero execution authority;
- full API tree.

---

## 13. Pre-mortem — five likely production failures

### Failure 1 — future outcome leakage

**Break:** an old decision replay reads a label that was only known hours/days later.  
**Prevention:** corpus `available_at` cutoff, record-created cutoff, complete-label horizon proof, replay metamorphic tests.

### Failure 2 — fake intelligence from fixtures

**Break:** deterministic mock analogs/fixture labels make memory appear rich when no real history exists.  
**Prevention:** canonical source-mode allowlist and hard fixture/synthetic exclusion.

### Failure 3 — evidence inflation

**Break:** dozens of correlated indicators or overlapping windows count as dozens of independent examples.  
**Prevention:** independent episode IDs, correlation-family accounting, non-overlap groups.

### Failure 4 — real-time latency collapse

**Break:** 50 indicator queries + full-history analog scans run on every decision.  
**Prevention:** batched PIT queries, immutable corpus hashes, ANN shortlist, bounded exact refinement, incremental indexes.

### Failure 5 — stale model/index after schema change

**Break:** new feature vector is compared against an index built with an old feature manifest.  
**Prevention:** manifest/index hash coupling, artifact verification, quarantine on mismatch, atomic active-pointer swap.

---

## 14. Build sequence and dependency on M3.2

M3.3 analysis can be completed now, but active runtime integration should follow this order:

```text
M3.2 GREEN / LOCKED
        ↓
M3.3-A batched corpus + persisted indicator memory
        ↓
M3.3-B reliability memory
        ↓
M3.3-C historical session memory
        ↓
M3.3-D pattern/day-shape memory
        ↓
M3.3-E snapshot-native 9C
        ↓
M3.3-F real analog memory
        ↓
M3.3-G OOD/drift/quarantine
        ↓
M3.3-H production wiring/parity/performance/full regression
        ↓
M3.3 GREEN / LOCKED
```

Reason: session/regime/index/sector conditioning keys must be canonical before memory can reliably stratify historical evidence by those contexts.

---

## 15. Definition of done

M3.3 is complete only when:

- every active memory fact comes from real persisted records or verified immutable artifacts;
- fixtures/generated/mock evidence cannot enter canonical receipts;
- all historical records are cutoff-safe to the current D2 decision time;
- pending outcomes never count as completed evidence;
- corpus identity/hash/watermark is deterministic and replayable;
- independent episode count is separated from raw record count;
- batched storage replaces the current N-query persisted-memory hot path;
- 9C current evidence is D2 snapshot-native;
- analog retrieval uses a verified real index + exact refinement, not generated matches;
- OOD/drift/quarantine can withhold stale/non-generalizing memory;
- DecisionContext fields are populated only from canonical receipts;
- D6 parity remains locked until later orchestration redesign;
- full regressions, authority audit and zero-execution audit pass;
- exact-head workflow succeeds;
- docs are updated only after observed proof.

Until then M3.3 remains NOT STARTED / ANALYZED, not GREEN.
