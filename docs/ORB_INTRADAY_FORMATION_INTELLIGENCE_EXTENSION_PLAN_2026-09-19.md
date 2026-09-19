# ORB Intraday Formation Intelligence Extension Plan

Date: 2026-09-19  
Status: **PROPOSED DOCUMENTATION CONTRACT — NOT IMPLEMENTED / NOT GREEN**  
Scope: extend the existing ORB opening-sequence architecture without changing B0-B3 runtime ownership, M3 ownership, D6 authority, execution permissions, dependencies, feeds, or live trading behavior.

## 1. Mission

The ORB engine must be able to answer, at any causal intraday decision time:

> What market behaviour is forming now, what competing explanations remain viable, what evidence supports or attacks each explanation, and what next observation would strengthen, confirm, weaken, invalidate, or expire each one — using only information genuinely available at that decision time.

This is not a chart-pattern naming project. It is a causal market-sequence reasoning contract for research-only ORB guidance.

## 2. Architecture law

Preserve the existing source-of-truth hierarchy:

```text
canonical market data
        ↓
D2 closed-candle facts + snapshot lineage
        ↓
M3.1 morphology / structure / levels
        +
M3.2 context when available
        +
BUILD-1 candidate identity / provenance
BUILD-2 market/session/contract identity
BUILD-3 prior-session typed references
        ↓
ORB deterministic event grammar
        ↓
OrbOpeningSequenceViewV1
        +
OrbIntradayFormationViewV1
        ↓
B6 formation lifecycle / state
        ↓
competing hypotheses
        ↓
M3.3 prefix-safe memory / analogues
        ↓
B8 proof / B9 challenger research
        ↓
B11 FOR / AGAINST / UNKNOWN evidence package
        ↓
M4 / AFRE
        ↓
D6 FINAL_CONFLUENCE_ARBITER
        ↓
WAIT / WATCH / PAPER-CANDIDATE only
```

`OrbIntradayFormationViewV1` is a **VIEW / COMPOSER**. It does not become a new candle calculator, structure calculator, level calculator, session owner, market-identity owner, memory database, probability model, final arbiter, or execution engine.

## 3. Frozen contracts: FORM-001…FORM-010

### FORM-001 — arbitrary-`as_of` causal formation reasoning

Every formation result is bound to at least:

```text
decision_as_of
knowledge_cutoff
source_snapshot_hash
formation_snapshot_hash
composition_version
availability
```

Hard invariant:

```text
information_used_at <= knowledge_cutoff <= decision_as_of
```

Appending later market data must not change an earlier fixed-`as_of` result.

### FORM-002 — deterministic formation anchors

Every active formation has an explicit anchor chosen only from information known by `decision_as_of`.

Candidate anchor families may include:

```text
SESSION_OPEN
OR_LOCK
CAUSAL_PIVOT
PDH_INTERACTION
PDL_INTERACTION
ORH_INTERACTION
ORL_INTERACTION
VWAP_RECLAIM
STRUCTURE_BREAK
EXPANSION_START
```

These are **registry candidates**, not proof that every candidate already has a canonical producer. A candidate may be used only when its underlying event has a canonical owner, valid provenance, and `anchor_known_at <= decision_as_of`; otherwise it is unavailable.

Required anchor identity:

```text
anchor_type
anchor_event_id
anchor_owner
anchor_market_time
anchor_known_at
anchor_source_snapshot_hash
anchor_policy_version
```

No hindsight anchor selection from the completed day is permitted.

### FORM-003 — multi-scale formation identity

Simultaneous interpretations on different scales may coexist. They are not automatically contradictory.

Every formation/hypothesis records:

```text
source_timeframe
formation_timeframe
scope
horizon
anchor
```

Initial scope vocabulary:

```text
MICRO
LOCAL_SWING
OPENING_SEQUENCE
INTRADAY
SESSION
```

A 3-minute bearish pullback may coexist with a 15-minute bullish continuation and a bullish session expansion if all are causally supported on their own scale.

### FORM-004 — formation lifecycle

A formation is not a static label. B6 owns lifecycle/state semantics.

Required states:

```text
SEED
DEVELOPING
TESTING_BOUNDARY
CONFIRMED
FAILED
EXPIRED
AMBIGUOUS
```

`CONFIRMED` must be earned by registered evidence. `FAILED` and `EXPIRED` are distinct. `AMBIGUOUS` is valid and must not be coerced into a directional formation.

### FORM-005 — explicit discriminator contract

Every active hypothesis must expose:

```text
support[]
opposition[]
unknown[]
expected_sequence[]
failure_sequence[]
next_discriminating_observation
confirmation_condition
weakening_condition
invalidation_condition
expiry_condition
```

The next discriminator must reference an observable future event definition, not a vague statement such as “looks stronger”. Conditions are deterministic predicates or registered research rules with version identity.

### FORM-006 — prefix-safe historical analogue retrieval

Historical matching at a current `decision_as_of` may use only the historical prefix that would have been available at the equivalent historical cutoff.

Required order:

```text
build current prefix at decision_as_of
        ↓
retrieve historical prefixes using only pre-outcome information
        ↓
freeze matched episode IDs + retrieval version + feature manifest
        ↓
only then reveal matured future outcomes
```

Historical outcome fields must not participate in candidate retrieval, ranking, anchor selection, feature construction, or tie-breaking.

### FORM-007 — versioned behavioural grammar

Pattern aliases are derived interpretation, not primary evidence.

Required hierarchy:

```text
CANDLE FACTS
    ↓
RELATIONSHIPS
    ↓
SEQUENCE BEHAVIOUR
    ↓
STRUCTURAL FORMATION
    ↓
OPTIONAL HUMAN ALIAS
```

Example vocabulary may include:

```text
relationships:
  HIGHER_HIGH / HIGHER_LOW / LOWER_HIGH / LOWER_LOW
  INSIDE / OUTSIDE / OVERLAP

behaviour:
  IMPULSE / PULLBACK / COMPRESSION / EXPANSION
  RETEST / RECLAIM / REJECTION / FAILURE / BALANCE

structural interpretation:
  TREND / RANGE / REVERSAL / SWEEP / FAILED_BREAKOUT
  BREAKOUT_ACCEPTANCE / PULLBACK_CONTINUATION

optional aliases:
  FLAG / TRIANGLE / VCP / DOUBLE_TOP / DOUBLE_BOTTOM / WEDGE / ...
```

Aliases may summarize already-existing evidence but may not fabricate new independent evidence.

### FORM-008 — formation identity and transition history

The engine records how an interpretation evolves through time.

Each transition records:

```text
formation_id
previous_state
current_state
changed_at
evidence_added[]
evidence_removed[]
reason
source_snapshot_hash
formation_snapshot_hash
transition_version
```

Transition identity must be deterministic and replayable. Corrections use replacement/supersession lineage; history is not silently mutated.

### FORM-009 — dependency lineage and anti-double-counting

Every alias, formation, and hypothesis records:

```text
source_event_ids[]
dependency_family
derived_from[]
```

If `BULL_FLAG`, `BULLISH_PULLBACK`, `HIGHER_LOW_CONTINUATION`, and `ASCENDING_MICRO_CHANNEL` all derive from the same candles/structure events, B11/D6 must not treat them as four independent votes.

Rule:

```text
correlated evidence != independent evidence
```

### FORM-010 — versioned geometry / tolerance policy

Vague geometry is forbidden in canonical or research claims.

B7 owns versioned parameter policies such as:

```text
boundary_tolerance_basis
pivot_prominence_basis
minimum_touch_count
slope_policy
compression_policy
overlap_policy
retracement_policy
normalization_basis
parameter_version
```

B4/B6 consume registered policy identity. B8 proves it. B10 freezes only evidence-supported configurations. Exact thresholds remain research parameters until promoted by the approved proof path.

## 4. Four hard safety rules

### 4.1 `NO_STABLE_FORMATION` is a valid result

The system may return:

```text
current_state = UNRESOLVED
possible = [ ... ]
no hypothesis has enough discriminating evidence
```

The engine must never invent a pattern merely because a caller expects one.

### 4.2 incomplete higher-timeframe candle cannot confirm a formation

Closed lower-timeframe sub-bars may support a provisional interpretation for an incomplete higher-timeframe bar, but:

```text
status = PROVISIONAL
authority = NONE
```

and the incomplete higher-timeframe formation cannot become `CONFIRMED` until the required candle is closed under the registered contract.

### 4.3 screenshots are examples, not canonical market data

Screenshots may define test scenarios or human-readable examples. Production/research canonical reasoning uses timestamped numerical market data, source identity, revision identity, level identity, volume/context availability, and hashes. Pixel recognition is a separate future challenger, never the primary truth source in this plan.

### 4.4 pattern fishing is controlled

Before holdout evaluation, B8 freezes at least:

```text
pattern_grammar_version
candidate_families
anchor_policy_version
parameter_search_space
train_period
walk_forward_periods
untouched_holdout
feature_manifest_version
```

No post-hoc expansion of searched patterns/anchors/windows/thresholds may be reported as if it were untouched confirmation.

## 5. `OrbIntradayFormationViewV1` composition contract

Minimum identity:

```text
symbol / instrument identity
session_id
contract identity where applicable
decision_as_of
knowledge_cutoff
source_timeframe
formation_timeframe
scope
horizon
anchor identity
grammar_version
parameter_version
source_snapshot_hash
formation_snapshot_hash
composition_version
availability
```

Minimum content:

```text
observed_behaviour[]
active_formations[]
competing_hypotheses[]
transition_history_ref
historical_prefix_analogue_ref
missing_or_unknown_evidence[]
dependency_lineage[]
```

Mandatory authority fields:

```text
authority = NONE
may_execute = false
may_set_final_band = false
```

## 6. Hypothesis receipt requirements

For each hypothesis:

```text
hypothesis_id
scope
horizon
anchor
state
support[]
opposition[]
unknown[]
expected_sequence[]
failure_sequence[]
next_discriminating_observation
confirmation_condition
weakening_condition
invalidation_condition
expiry_condition
source_event_ids[]
dependency_family
derived_from[]
```

No field named `probability`, `confidence_probability`, `win_probability`, or equivalent is introduced here. Any calibrated event/horizon probability remains a later BUILD-12 concern and must be evidence-backed.

## 7. Research ownership versus canonical ownership

| Concern | Owner / stage | B4 formation treatment |
|---|---|---|
| closed candles / snapshot lineage | D2 | consume only |
| candidate identity / provenance | BUILD-1 | consume only |
| market/session/contract identity | BUILD-2 | consume only |
| prior-session reference facts | BUILD-3 | consume only |
| candle morphology / structure / levels | M3.1 | consume only |
| context | M3.2 when available | consume only; missing stays missing |
| memory / analogues | M3.3 | prefix-safe baseline retrieval first |
| opening/intraday composition view | B4-F | compose only |
| timing / timeframe / N / OR-window search | B5 | research only until promoted |
| formation lifecycle/state | B6 | state owner |
| geometry/tolerance parameters | B7 | parameter owner |
| proof / ablation / OOS / holdout | B8 | proof owner |
| analogue challengers | B9 after M3.3 limitation proof | optional research |
| configuration freeze | B10 | only proven config |
| dependency-aware evidence package | B11 | FOR / AGAINST / UNKNOWN |
| calibrated probabilities | B12 | only after calibration proof |
| matured outcomes | B13 | outcome owner |
| adversarial/replay/release lock | B14 | final proof gate |
| final guidance band | D6 | unchanged final authority |

## 8. Historical similarity order

Preserve the evidence ladder:

```text
A0 legacy ORB
A1 + canonical candle anatomy
A2 + level interaction
A3 + sequence transitions
A4 + valid participation / RVOL
A5 + context
A6 + formation state
A7 + M3.3 prefix-safe analogues
A8 + STUMPY only if A7 limitation is proven
A9 + bounded DTW reranking only if A8 leaves incremental value
```

STUMPY/DTW remain challengers. This plan does not install them and does not treat their availability as evidence of value.

## 9. Mandatory B14 adversarial tests

### T1 — future append invariance

Freeze `decision_as_of=T`. Append later market data. Reconstruct `T`.

Required unchanged fields include:

```text
formation_snapshot_hash
anchor
window/feature manifest
candidate hypotheses
aliases
parameter_version
```

Any change caused only by future data fails with a future-dependency error.

### T2 — hindsight-anchor attack

Compute anchor at `T`; append future data; reconstruct `T`; anchor must remain identical.

### T3 — historical-analogue outcome attack

Retrieve and freeze episode IDs before outcome reveal. Revealing outcomes must not change retrieval IDs/rank at the same historical cutoff.

### T4 — time-scale coexistence

A test fixture may intentionally produce different valid states on 3m, 15m, and session scales. All remain representable without false contradiction.

### T5 — alias independence attack

Multiple aliases derived from one event family must remain one dependency family for confluence purposes.

### T6 — incomplete-candle attack

Incomplete higher-timeframe structure may be `PROVISIONAL` only; it must not become `CONFIRMED` until the close contract is satisfied.

### T7 — pattern-search leakage attack

Changing post-`T` data must not change at `T`:

```text
anchor
candidate window
candidate formations
aliases
parameter_version
grammar_version
```

### T8 — no-stable-formation case

Messy overlapping evidence with no discriminator satisfied must produce `NO_STABLE_FORMATION` / `UNRESOLVED`, not a forced label.

### T9 — missingness case

Unavailable volume/RVOL/context remains `UNKNOWN`/`UNAVAILABLE`; it may not be coerced to zero, false, or neutral.

### T10 — dependency family case

Two independent evidence families and four correlated aliases must be represented as two families, not six votes.

## 10. Completion criteria for documentation stage

Documentation reconciliation is complete only when:

1. all nine target ORB/M4 Markdown plans bind FORM-001…FORM-010 without creating conflicting owners;
2. the detailed B4 plan contains the full `OrbIntradayFormationViewV1` contract and B14 attack set;
3. master/stage maps preserve B4→B14 ownership boundaries;
4. M3.3-first analogue discipline remains intact;
5. D6 remains sole final guidance-band authority;
6. `NO_STABLE_FORMATION` and `PROVISIONAL` are explicit legal outcomes;
7. no runtime implementation, dependency install, feed activation, execution authority, commit, push, merge, or PR is implied by the documentation update.

Implementation and GREEN status require a later, separately authorized runtime build plus exact-head tests/CI. Documentation text alone is not proof.

## Repository reference artifacts

The source and verification records for this documentation contract are saved with the same documentation update under:

- `docs/ORB_FORMATION_REFERENCE_2026-09-19/SOURCE_INTRADAY_FORMATION_PLAN_2026-09-19.md`;
- `docs/ORB_FORMATION_REFERENCE_2026-09-19/FORM_TRACEABILITY_MATRIX.md`;
- `docs/ORB_FORMATION_REFERENCE_2026-09-19/DESIGN_EVIDENCE_LEDGER.md`;
- `docs/ORB_FORMATION_REFERENCE_2026-09-19/JUDGE_REPORT.md`;
- `docs/ORB_FORMATION_REFERENCE_2026-09-19/ORB_FORMATION_FUTURE_BUILD_REFERENCE_2026-09-19.md`;
- `docs/ORB_FORMATION_REFERENCE_2026-09-19/B4_OS_TRACEABILITY_MATRIX_PREVIOUS_VERIFIED.md`;
- `docs/ORB_FORMATION_REFERENCE_2026-09-19/SOURCE_OF_TRUTH_MAP_PREVIOUS_VERIFIED.md`.

These references preserve design provenance; they do not claim runtime implementation, BUILD-0 source-lock completion, or exact-head CI GREEN.
