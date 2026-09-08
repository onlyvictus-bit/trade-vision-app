# Next Build Target

Last reviewed: 2026-09-08

> **Canonical status source:** `docs/CANONICAL_BUILD_STATUS.md`
>
> Repository code/tests are the temporary truth when status documentation lags. Do not infer GREEN/LOCKED from implementation presence alone.

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
M3.2-A  Context source contract              IMPLEMENTED / CI-GATED
M3.2-B  Canonical Session Intelligence       IMPLEMENTED / VERIFICATION IN PROGRESS
M3.2-C  Canonical Index/Sector Context       NEXT ACTIVE SUB-MILESTONE
M3.2-D  Canonical Relative Strength          NOT STARTED
M3.2-E  Canonical Market Regime              NOT STARTED
M3.2-F  Context fusion / receipts / lock     NOT STARTED
M3.3    Canonical Memory Intelligence        DESIGN STAGED / RUNTIME NOT ACTIVE
M4      D6 orchestration redesign            NOT STARTED / D6 EXISTS
```

## M3.1 locked predecessor

M3.1 is already GREEN / LOCKED. Its exact pre-documentation verification remains:

```text
source head: a346ca62ddc960e0402b7df661bb3215cfa45a7b
workflow:    M3.1 Canonical Price Intelligence
run:         34254621808 — SUCCESS
```

M3.2 branch was created from the locked M3.1 final head:

```text
20d2d7b5889b09cd593401e8f70ec53cc299c51e
```

## Active branch

```text
m3-2-context-intelligence
```

M3.2-A production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_context_intelligence.py
apps/api/tests/decision_spine/test_m3_2_context_contract.py
```

M3.2-B production boundary:

```text
apps/api/app/behavior/decision_spine/canonical_session_intelligence.py
apps/api/tests/decision_spine/test_m3_2_session.py
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
no incomplete-bar authority
D1 outranks all specialists
all active evidence is causal to D2
FINAL_CONFLUENCE_ARBITER / D6 remains sole final-band authority
zero execution authority
```

M3.2 does not redesign D6. It creates a canonical context world with explicit source identity, session state, index/sector facts, relative strength, regime evidence, contradictions and provenance.

## NEXT ACTIVE BUILD — M3.2-C

After M3.2-B exact-head verification is green, build Canonical Index/Sector Context.

Required properties:

1. independently frozen index and sector snapshots;
2. exact provider/symbol/source-contract identity;
3. source close-time and `available_at` proof;
4. versioned freshness / clock-skew state;
5. versioned benchmark mapping (`stock -> sector -> broad index`);
6. explicit adjusted/raw lineage where comparative returns depend on it;
7. no missing source converted to `0`, `neutral`, `false` or `0.5`;
8. bounded deterministic receipt/hash;
9. contradictions preserved;
10. zero final-band and zero execution authority;
11. replay/adversarial/parity coverage;
12. locked M3.1/M2/M0/full-tree regressions remain green.

## Intelligence upgrade direction

The approved architecture reference adds these later requirements without prematurely activating them:

- versioned NSE calendar authority;
- benchmark mapping history;
- corporate-action lineage;
- real cross-market/breadth providers or explicit absent state;
- regime hysteresis + confidence;
- provider-specific freshness/skew SLOs;
- memory label migration, retention/decay and quarantine;
- multi-hypothesis reasoning with falsifiers;
- calibrated self-model / OOD uncertainty;
- offline information-value/curiosity queue;
- explanation receipts;
- failure-prediction receipts.

These are engineering goals for broad, adaptive, contradiction-aware intelligence. They do not constitute a claim of literal AGI, guaranteed prediction correctness, or trading edge.

## Current verification caveat

The local execution environment used during this continuation could not resolve `github.com`, so independent local pytest execution was not available. The repository workflow has been extended to compile and run M3.2-A/M3.2-B plus locked regressions at the exact pushed commit. Do not mark M3.2-B GREEN / LOCKED until that workflow result is actually verified.
