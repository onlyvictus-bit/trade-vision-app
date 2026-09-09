# Next Build Target

Last reviewed: 2026-09-09

> **Canonical status source:** `docs/CANONICAL_BUILD_STATUS.md`
>
> Repository code/tests are temporary truth when status documentation lags. GREEN / LOCKED requires exact-head CI evidence, locked regressions and authority/safety verification.

## Current truth

```text
M0      Stage-2 integrity                    GREEN / LOCKED
M1      Authority Registry                   FOUNDATION GREEN / SCOPE LOCKED
M2      Canonical DecisionContext            GREEN / LOCKED
M3      Brain migration                      IN BUILD
M3.1    Canonical Price Intelligence         GREEN / LOCKED
M3.1-A  Snapshot Feature Kernel              GREEN / LOCKED
M3.1-B  Canonical Candle Intelligence        GREEN / LOCKED
M3.1-C  Canonical Level Intelligence         GREEN / LOCKED
M3.1-D  Canonical Indicator Intelligence     GREEN / LOCKED
M3.1-E  PIT-safe MTF Intelligence            GREEN / LOCKED
M3.1-F  Price Evidence Fusion / DAG / parity GREEN / LOCKED
M3.2    Canonical Context Intelligence       IN BUILD
M3.2-A  Context source contract              GREEN / LOCKED
M3.2-B  Canonical Session Intelligence       GREEN / LOCKED
M3.2-C  Canonical Index/Sector Context       ACTIVE / IN BUILD
M3.2-D  Canonical Relative Strength          NOT STARTED
M3.2-E  Canonical Market Regime              NOT STARTED
M3.2-F  Context fusion / receipts / lock     NOT STARTED
M3.3    Canonical Memory Intelligence        DESIGN STAGED / RUNTIME NOT ACTIVE
M4      D6 orchestration redesign            NOT STARTED / D6 EXISTS
```

## M3.2-B lock evidence

```text
verified source head: 5c944ac0f727767f5494af4c23b9334366860a8d
workflow:             M3.2 Canonical Context Intelligence
run:                  34321289260 — SUCCESS
```

The exact-head workflow passed compile checks, M3.2-A, M3.2-B, the dedicated final-release-audit cache-isolation regression, locked M3.1/M2/M0 regressions, Paper Guidance, historical `tests/test_api.py`, the entire API test tree and the Decision Spine sole-D6/zero-execution authority audit.

The pre-lock full-tree transport-resilience failure was fixed at the production cache-identity boundary rather than by weakening tests or forcing a critical state. The cache now retains dependency object identity, and a dedicated transition regression proves cached healthy evidence cannot survive a changed critical resilience dependency.

## Locked M3.1 predecessor

```text
source head: a346ca62ddc960e0402b7df661bb3215cfa45a7b
workflow:    M3.1 Canonical Price Intelligence
run:         34254621808 — SUCCESS
```

M3.2 branch was created from locked M3.1 final head:

```text
20d2d7b5889b09cd593401e8f70ec53cc299c51e
```

## Active branch

```text
m3-2-context-intelligence
```

Locked M3.2-A/B production boundaries:

```text
apps/api/app/behavior/decision_spine/canonical_context_intelligence.py
apps/api/app/behavior/decision_spine/canonical_session_intelligence.py
apps/api/tests/decision_spine/test_m3_2_context_contract.py
apps/api/tests/decision_spine/test_m3_2_session.py
apps/api/app/behavior/final_release_audit.py
apps/api/tests/test_final_release_audit_cache_isolation.py
```

Controlling plans/reference:

```text
docs/M3_2_CANONICAL_CONTEXT_INTELLIGENCE_ANALYSIS_AND_BUILD_PLAN_2026-09-08.md
docs/M3_3_CANONICAL_MEMORY_INTELLIGENCE_ANALYSIS_AND_BUILD_PLAN_2026-09-08.md
docs/M3_INTELLIGENCE_UPGRADE_REFERENCE_2026-09-08.md
```

## M3.2 engineering law

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
unfinished != closed
future != causal
stale != fresh
ambiguous mapping != valid mapping
unknown adjustment basis != comparable adjusted series

D1 outranks all specialists
all active evidence is causal to D2
FINAL_CONFLUENCE_ARBITER / D6 remains sole final-band authority
zero execution authority
```

M3.2 does not redesign D6. It builds a canonical context world with explicit source identity, session state, index/sector facts, relative strength, regime evidence, contradictions, uncertainty and provenance.

# NEXT ACTIVE BUILD — M3.2-C Canonical Index + Sector Context

Build in this order:

1. **Versioned benchmark registry**
   - effective-dated `stock -> sector -> broad index` mapping;
   - source/mapping version and lineage;
   - reject missing, overlapping or ambiguous effective mappings;
   - deterministic resolution at D2 decision time.

2. **Provider/freshness policy contracts**
   - provider + contract + instrument/timeframe policy identity;
   - explicit maximum source age, availability lag and clock-skew tolerance;
   - policy version included in evidence lineage;
   - stale/skewed/unproven sources degrade or become unavailable, never neutral.

3. **Price-basis / corporate-action lineage**
   - explicit `RAW` / adjusted basis / `UNKNOWN` representation;
   - source adjustment policy/version;
   - comparative calculations must reject incompatible/unproven bases;
   - never fabricate corporate-action adjustments.

4. **Independent index and sector observations**
   - independently frozen source snapshots and source-series hashes;
   - exact provider/symbol/source-contract identity;
   - source close-time + `available_at` proof;
   - no unfinished/future authority.

5. **Canonical context composition**
   - preserve broad-index and sector facts independently;
   - preserve contradictions rather than majority-voting them away;
   - explicit missing/partial/ambiguous state;
   - bounded deterministic receipt and upstream hashes;
   - operational latency excluded from deterministic evidence identity unless causally required.

6. **Zero-authority boundary**
   - no trade proposal;
   - no veto/downgrade authority;
   - no final-band authority;
   - no execution authority;
   - D6 remains unchanged.

7. **Verification**
   - effective-date boundaries and mapping transitions;
   - missing/overlapping/ambiguous mappings;
   - stale/skewed/future/unfinished source observations;
   - wrong provider/symbol/source hash;
   - synthetic vs real;
   - incompatible price bases;
   - contradictory index/sector states;
   - duplicate observations;
   - replay and order independence;
   - deterministic/bounded receipts;
   - locked M3.1/M2/M0 regressions;
   - full API tree;
   - authority/safety audit.

## Intelligence direction

The approved architecture aims for adaptive, multi-hypothesis, falsifier-aware and uncertainty-aware reasoning. Later layers may use counterfactuals, calibrated self-model/OOD uncertainty, PIT-safe memory, failure-prediction receipts and offline information-value queues.

These are engineering capabilities, not claims of literal AGI, guaranteed prediction correctness or trading edge. Unknown or contradictory evidence must remain visible and reduce confidence rather than being converted into invented certainty.

## Hard stop boundary

Do not begin M3.2-D until M3.2-C itself is exact-head GREEN / LOCKED. Do not redesign D6 or activate live trading during M3.2.
