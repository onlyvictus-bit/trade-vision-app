# Next Build Target

Last reviewed: 2026-09-08

> **Canonical status source:** `docs/CANONICAL_BUILD_STATUS.md`
>
> Do not infer milestone state from chat history or implementation presence. Advance only from verified repository lock evidence.

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
M3.2+   Later brain-family migration         NEXT / NOT STARTED
M4      D6 orchestration redesign            NOT STARTED / D6 EXISTS
```

## M3.1 lock evidence

Pre-documentation exact source head:

`a346ca62ddc960e0402b7df661bb3215cfa45a7b`

Workflow:

`M3.1 Canonical Price Intelligence`

Run:

`34254621808` — **SUCCESS**

Observed gate summary:

```text
A snapshot kernel                              15 passed
B candle pipeline                              13 passed
C level intelligence                           15 passed
D indicator intelligence                       12 passed
E PIT-safe MTF                                 11 passed
F price evidence                                5 passed
F replay/metamorphic                            4 passed
F adversarial DAG                               8 passed
M2 DecisionContext                             34 passed
M2 standalone adapter                         13 passed
M2 Paper Guidance / D6 parity                 10 passed
M0 Stage2                                      15 passed
v1.88                                          29 passed
historical API                                556 passed
entire API test tree                         1060 passed, 5 environment/resource skips
sole-D6 / zero-execution authority             PASS
exact triggering-commit checkout               PASS
```

Locked D6 parity remains zero for `snapshot_hash`, `final_band`, `confidence_cap`, `next_action`, and `arbiter_summary` against the preserved legacy route.

## M3.1 completion boundary

M3.1 established one D2-causal price world without creating another decision authority:

```text
D2
 -> calculate-once SnapshotFeatureKernel
 -> canonical Candle Intelligence
 -> canonical Level Intelligence
 -> canonical Indicator Intelligence
 -> closed-only PIT-safe MTF
 -> contradiction-preserving Price Structure Evidence / DAG
 -> Stage2IntegrityReport
 -> DecisionContext
 -> CURRENT D6 UNCHANGED
```

The following remain invariant:

```text
missing != neutral
unknown != false
unavailable != safe
error != zero
no_signal != unavailable
no_output != neutral
D1 outranks all
no incomplete-bar authority
FINAL_CONFLUENCE_ARBITER is sole final-band authority
zero execution authority
```

## NEXT — M3.2+ later brain-family migration

M3.2+ is now the next eligible program boundary, but it is **NOT STARTED** by the M3.1 lock.

Before any M3.2 implementation:

1. reread `docs/CANONICAL_BUILD_STATUS.md` and the controlling staged plan;
2. inventory the exact next specialist family and its current runtime authority/data dependencies;
3. preserve D1/D2 causality and explicit missingness;
4. migrate evidence into DecisionContext without changing D6 semantics unless a later milestone explicitly authorizes that change;
5. keep ORB redesign, derivatives migration, M4/D6 redesign and execution authority outside scope unless that next milestone specifically selects them;
6. retain full replay/parity/adversarial/authority gates.

Known M3.1 provider caveats stay explicit: official exchange calendar authority, corporate-action provenance and external feed freshness/clock-skew proof are not fabricated by the M3.1 lock.

Software verification is not market-edge proof. Walk-forward validation, costs/slippage, paper observation and promotion gates remain separate later work.
