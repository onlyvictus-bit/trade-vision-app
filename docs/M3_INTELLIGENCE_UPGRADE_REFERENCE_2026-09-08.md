# Trade Vision — Intelligence Upgrade Reference

**Date:** 2026-09-08  
**Applies to:** M3.2 Context Intelligence, M3.3 Memory Intelligence, later M3.x specialist migration  
**Source:** user-supplied continuation/reference note reviewed against repository state on `m3-2-context-intelligence`  
**Status:** architectural reference; does not grant runtime authority by itself

---

## 1. Purpose

This document records the next intelligence upgrades requested for Trade Vision / TrendForge Decision Spine. The target is not to claim literal AGI or guaranteed market correctness. The engineering target is a production-grade, generalizable research-intelligence architecture that is:

- causal and point-in-time safe;
- provenance-first;
- contradiction-aware;
- explicit about uncertainty and missingness;
- adaptive only through auditable/versioned learning loops;
- able to generate and falsify multiple hypotheses;
- failure-aware before producing stronger guidance;
- deterministic where determinism is required;
- bounded for latency, memory and payload size;
- incapable of silently converting missing, stale, synthetic or future data into neutral evidence;
- zero-execution-authority until a separately authorized milestone changes that boundary.

The existing locked laws remain mandatory:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no incomplete-bar authority
D1 outranks every predictor/reviewer
all active evidence is causal to the D2 decision time
FINAL_CONFLUENCE_ARBITER / D6 remains sole final-band authority
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
```

---

## 2. Repository-verified baseline

At review time the active branch is:

```text
m3-2-context-intelligence
```

Verified branch head before this reference was added:

```text
a97382ca133a1e72a9d7b410d3b555acc9381e32
```

M3.2-A already exists as a canonical source/evidence boundary in:

```text
apps/api/app/behavior/decision_spine/canonical_context_intelligence.py
```

It already protects:

- D2 decision-time binding;
- immutable source snapshot identity;
- source/provider contract identity;
- close-time and availability-time causality;
- source watermark/sequence;
- explicit freshness and clock-skew states;
- synthetic-source rejection for canonical available evidence;
- identity mismatch rejection;
- explicit AVAILABLE / DEGRADED / UNAVAILABLE / PENDING / ERROR;
- future source rejection;
- duplicate source rejection;
- deterministic order-independent context hashing;
- bounded context envelope;
- zero probability/final-band/execution authority.

Repository documentation was inconsistent at this point: M3.2 code and plan were present, but `CANONICAL_BUILD_STATUS.md` and `NEXT_BUILD_TARGET.md` still described M3.2 as `NEXT / NOT STARTED`. That status must be corrected whenever M3.2 changes are committed.

---

## 3. P0 — correctness gaps that must be solved before stronger intelligence

### 3.1 Versioned exchange calendar authority

Add a canonical NSE calendar artifact/provider contract covering:

- holidays;
- special trading sessions;
- half-days/modified sessions;
- session open/close changes;
- version and source identity;
- available-at time;
- effective date range;
- deterministic artifact hash;
- explicit unavailable state when authority cannot be proven.

Static `09:15-15:30` semantics are useful as a regular-session fallback description, not sufficient exchange-calendar proof.

### 3.2 Versioned benchmark mapping registry

Add a PIT-safe registry:

```text
stock -> sector benchmark -> broad-market benchmark
```

The registry must record:

- mapping version;
- effective-from/effective-to;
- source identity;
- symbol changes;
- index rebalance history where relevant;
- mapping hash;
- explicit `MAPPING_UNAVAILABLE` rather than guessing a sector.

### 3.3 Corporate-action lineage

Every stock/index source snapshot used for comparative calculations should be able to declare:

```text
adjustment_basis
corporate_action_version
```

Raw and adjusted series must never be mixed silently in relative-strength, memory or regime calculations.

### 3.4 Real providers or explicit absence

Cross-market/breadth/global context currently represented by mock/synthetic research paths must remain noncanonical until a real provider satisfies the M3.2 source contract. If there is no real provider, the canonical state is explicit `UNAVAILABLE / NOT_MIGRATED`, not a fixture-derived neutral value.

---

## 4. P1 — robustness upgrades

### 4.1 Regime hysteresis and confidence

A regime label should not flicker on one noisy bar. Canonical regime output should support:

```text
regime_id
candidate_regime_id
regime_confidence
change_evidence_count
minimum_persistence_bars
hysteresis_state
last_confirmed_change_time
```

A regime transition must require versioned evidence and must preserve contradictory facts.

### 4.2 Versioned freshness and skew SLOs

`FRESH`, `STALE`, `SKEWED` need provider-specific numeric policies. Add a versioned policy contract rather than hard-coded universal values.

Example shape:

```text
provider_id
source_kind
policy_version
fresh_max_age_ns
degraded_max_age_ns
max_clock_skew_ns
on_violation = DEGRADED | UNAVAILABLE
```

The exact values must come from provider/data-contract validation, not arbitrary defaults.

### 4.3 Memory label migration

M3.3 memory records must carry at least:

```text
feature_version
label_version
outcome_rule_version
strategy_semantics_version
```

Changing stop/target/outcome rules requires stratification or an explicit migration job. Old and new labels must not silently mix.

### 4.4 Retention, decay and poisoning recovery

Memory needs bounded lifecycle rules:

- per-family/per-symbol capacity;
- time decay;
- regime-conditioned decay;
- quarantine;
- purge eligibility;
- source-retraction handling;
- rollback to a previous corpus version;
- no online request-path self-modification.

---

## 5. P2 — general reasoning upgrades

### 5.1 Multi-hypothesis evidence layer

Add a zero-authority hypothesis layer after canonical facts exist. It may produce 2-3 bounded plausible next-state hypotheses such as continuation, failed-break/reversal, or compression/no-resolution.

Each hypothesis must include:

```text
hypothesis_id
statement
supporting_fact_hashes
contradicting_fact_hashes
required_observations
falsifiers
unknowns
confidence_band_or_ordinal
expires_at_or_bar_count
status = ACTIVE | CONFIRMED | FALSIFIED | EXPIRED | INDETERMINATE
```

This layer may organize evidence; it must not become a hidden second D6.

### 5.2 Calibrated self-model / uncertainty

Every intelligence family should be able to expose calibration metadata derived only from validated historical corpora:

```text
calibration_version
brier_score
expected_calibration_error
sample_count
independent_episode_count
ood_state
reliability_state
```

When OOD, calibration-poor or low-sample, allowed behavior can only become more conservative. Uncertainty must never increase trade authority.

### 5.3 Curiosity / information-value queue

Offline-only research may prioritize what should be stored, relabeled or investigated next:

- low-sample regimes;
- high specialist disagreement;
- recurrent failure clusters;
- distribution shifts;
- newly observed setup combinations;
- calibration failures.

This queue has zero request-path authority and zero execution authority.

### 5.4 Explanation receipts

Every canonical specialist family should emit top supporting and contradicting evidence with hashes. A reviewer must be able to understand why a state was emitted without re-running the entire system.

### 5.5 Counterfactual / falsification reasoning

For every material hypothesis, record what observation would invalidate it. This prevents one-direction narrative lock-in and supports adaptive WAIT behavior.

### 5.6 Failure-prediction layer

Before stronger guidance is emitted, aggregate known failure precursors from canonical evidence only. Examples:

- stale/misaligned context;
- session transition instability;
- regime disagreement;
- benchmark divergence;
- extreme volatility state;
- weak independent episode count;
- memory OOD/drift;
- repeated recent analog failure;
- event/calendar uncertainty;
- data-provider degradation.

The output should be a bounded failure-risk receipt with reason codes, not a magic probability unless calibrated evidence exists.

---

## 6. Intelligence control loop

Target research-intelligence flow:

```text
D1 SAFETY / PIT / KILL SWITCH
        |
        v
D2 IMMUTABLE PRIMARY SNAPSHOT
        |
        v
M3.1 CANONICAL PRICE WORLD
        |
        +----------------------------+
        |                            |
        v                            v
M3.2 CONTEXT WORLD              M3.3 MEMORY WORLD
session/index/sector/RS/regime   PIT corpus/labels/analogs/OOD
        |                            |
        +-------------+--------------+
                      |
                      v
            CONTRADICTION GRAPH
                      |
                      v
          MULTI-HYPOTHESIS ENGINE
        support / oppose / falsify
                      |
                      v
             SELF-MODEL / OOD
       calibration / uncertainty
                      |
                      v
          FAILURE-PREDICTION RECEIPT
                      |
                      v
               EXPLANATION RECEIPT
                      |
                      v
              DecisionContext
                      |
                      v
              EXISTING D6 ONLY
                [unchanged]
```

No new node above may set a final band unless a later milestone explicitly changes the authority registry.

---

## 7. Production-readiness invariants for future code

Every new canonical intelligence module should satisfy applicable rules below:

1. deterministic output from deterministic causal inputs;
2. explicit calculation/version identity;
3. exact upstream hashes;
4. explicit availability/missingness;
5. no hidden synthetic fallback;
6. no caller-supplied historical counts trusted as authority;
7. independent episode count where historical evidence is involved;
8. bounded payload and bounded request-path work;
9. no full histories/DataFrames inside DecisionContext receipts;
10. no future or incomplete bar authority;
11. no stale source silently used as fresh;
12. no benchmark identity guess;
13. no raw/adjusted series mixing;
14. no regime change without hysteresis/versioned evidence;
15. OOD/uncertainty can only reduce confidence/authority;
16. support and contradiction both remain visible;
17. every state has reason codes;
18. replay produces identical evidence hashes;
19. source completion order cannot change deterministic identity;
20. malformed provenance fails closed;
21. existing locked D6 parity remains zero-diff until D6 migration is authorized;
22. zero execution authority remains enforced by registry and tests.

---

## 8. Build order

Continue in this order:

```text
M3.2-A  Context Source Contract             STARTED
M3.2-B  Canonical Session Intelligence      NEXT ACTIVE CODE
M3.2-C  Canonical Index/Sector Context
M3.2-D  Canonical Relative Strength
M3.2-E  Canonical Market Regime + hysteresis
M3.2-F  Context fusion / receipts / replay / parity / lock
M3.3-A  PIT-safe batched memory corpus
M3.3-B  versioned delayed labels + migration
M3.3-C  independent episode grouping
M3.3-D  reliability/session/pattern memory views
M3.3-E  real analog engine
M3.3-F  real 9-candle memory
M3.3-G  OOD / drift / decay / quarantine
M3.3-H  memory fusion / receipts / replay / lock
M3.4    hypothesis + self-model + failure-prediction proposal
```

P0 work that is required by a specific M3.2 sub-milestone must be solved or explicitly represented as unavailable; it must not be fabricated merely to keep the build moving.

---

## 9. What “production ready” means here

Production ready in this project means the software is robust, causal, testable, auditable, deterministic where required, and safe against malformed/missing/synthetic/future evidence. It does **not** mean:

- guaranteed profitable trading;
- guaranteed correct predictions;
- literal AGI;
- authority to place orders;
- permission to bypass paper/live promotion gates.

Market-edge validation remains a separate empirical program using walk-forward tests, realistic costs/slippage, paper observation, calibration, and release gates.
