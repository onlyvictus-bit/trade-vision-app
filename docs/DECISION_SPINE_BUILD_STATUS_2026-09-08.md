# Canonical Decision Spine Build Status — 2026-09-08

## Current status

```text
branch: decision-spine-orchestration-v1
base main: f26546047a28df7deb3916ed0b4467d67fd9bb7b
M0: COMPLETE / GREEN
M1: FOUNDATION BUILT
next: M2 CANONICAL DecisionContext
```

AFRE v4 is already merged. This work is isolated from the AFRE branch.

## Architecture decision

Trade Vision does not need another independent BUY/SELL brain. It needs one causal evidence spine and one final authority.

```text
D1 DATA/PIT SAFETY
 -> D2 IMMUTABLE CLOSED-CANDLE SNAPSHOT
 -> STAGE-2 ANALYSIS BRAINS
 -> STAGE-2 EVIDENCE INTEGRITY
 -> M2 DecisionContext
 -> Price / Context / Memory / Hypotheses / ORB / AFRE
 -> Derivatives / Events / Failure
 -> Risk / Execution
 -> FINAL CONFLUENCE / D6
 -> FinalDecision
 -> Jarvis display only
```

## Stage 1 verdict

Stage 1 is architecturally complete and should not be rebuilt. Preserve the D1-before-D2 ordering, closed-candle/PIT protection, deterministic D2 snapshot and snapshot hash, bad-data/unfinished-candle/kill-switch blocking, and same-snapshot downstream identity.

Future provider upgrades may improve inputs, but Stage 1 remains the causal root contract.

## M0 Stage-2 stabilization — COMPLETE

Tested M0 source commit:

`728d81d40ec8cdfe136e765ff0378118a8c1e759` — `decision-spine: stabilize Stage2 runtime contracts`

Committed-tree verification:

```text
workflow: M0 Stage2 Committed Verify
run:      34213835837
head:     9568ce951f44ea9e7c8d34b296a21b0bea0ab630
result:   SUCCESS
```

Exact verification results:

```text
compile affected M0 modules                 PASS
Stage-2 integrity suite                     15 passed
Paper Guidance v1.88 suite                  29 passed
full apps/api/tests/test_api.py             556 passed
sole-D6 / zero-execution authority checks   PASS
```

The verification workflow is read-only. Temporary patch/apply scripts and the self-applying stabilization workflow were removed after committed-tree verification succeeded.

## M0-C — `synthetic_fallback` contract drift — FIXED

`IndicatorFeatureBlock` now accepts the same explicit `synthetic_fallback` provenance already supported by `IndicatorSequenceRecord`.

The required safety semantics are preserved:

```text
synthetic_fallback != real
synthetic_fallback -> explanation_only = true
synthetic_fallback -> usable_for_probability = false
synthetic_fallback -> no proof authority
synthetic_fallback -> no trade authority
```

No test was changed to relabel synthetic data as real.

## M0-A — 9C runtime accounting — FIXED

The 9C audit now separates:

```text
real_runtime_computed_count
synthetic_fallback_computed_count
runtime_unavailable_count
runtime_failed_count
runtime_accounting_pass
```

The accounting reconciles promoted runtime indicators without counting synthetic fallback as real. Synthetic fallback can remain useful for explanation/runtime diagnostics while remaining non-authoritative.

## M0-B — PTA probe accounting — FIXED

PTA now exposes:

```text
selected_count
probe_count
computed_count
no_signal_count
dependency_unavailable_count
error_count
materialized_output_count
accounting_pass
```

A selected/probed PTA marker is not automatically counted as a successful output. Missing optional `research.signals.*` dependencies remain explicit availability failures/warnings rather than fabricated signals.

PTA remains explanation/availability evidence only:

```text
used_for_probability = false
trade_allowed = false
order_routing_enabled = false
```

## Stage-2 Evidence Integrity — BUILT AND WIRED

Files:

```text
apps/api/app/behavior/decision_spine/__init__.py
apps/api/app/behavior/decision_spine/authority_registry.py
apps/api/app/behavior/decision_spine/stage2_integrity.py
apps/api/tests/decision_spine/test_stage2_integrity.py
```

The gate enforces:

- registered engine identity;
- exact D2 snapshot hash agreement;
- identity consistency;
- future-leakage hard block;
- duplicate/unregistered engine hard block;
- unavailable evidence cannot be silently converted to neutral;
- synthetic/mock/masked/unknown evidence cannot gain probability authority;
- non-D6 engines cannot claim the product final band;
- exactly one final-band authority: `FINAL_CONFLUENCE_ARBITER`;
- zero execution-authorized engines;
- empty Stage-2 evidence fails closed;
- the integrity layer cannot grant paper promotion or execute.

## Real Paper Guidance wiring

The real Paper Guidance chain now evaluates Stage-2 integrity before D6.

```text
D2 Snapshot
   ↓
D2-native Stage-2 PaperGuidanceEngineReceipt[]
+ explicit migration observations
   ↓
Stage2IntegrityReport
   ↓
PASS / DEGRADED / BLOCK
   ↓
D6 only when no hard integrity blocker
```

Current migration-only observations:

```text
NINE_CANDLE_MEMORY  -> SKIPPED until D2-native Paper Guidance wiring
PTA_MARKER_RUNTIME  -> SKIPPED until D2-native Paper Guidance wiring
ORB_CORE            -> SKIPPED in this Paper Guidance path until canonical activation
AFRE                -> SKIPPED until canonical DecisionContext wiring
```

This is intentional. `SKIPPED/UNAVAILABLE` is safer and more truthful than silently substituting neutral values or independently fetching current state during arbitration.

If Stage-2 integrity hard-blocks, Paper Guidance stops before D6 and returns fail-closed `WAIT / DO_NOTHING` behavior with no paper authority.

## Engine Authority Registry — M1 FOUNDATION BUILT

The registry records engine ID, module, classification, propose/veto/downgrade/finalize/execute rights, rank, canonical consumer and migration lifecycle.

Current invariant:

```text
FINAL_CONFLUENCE_ARBITER = only may_set_final_band engine
all engines             = may_execute false
```

Registration is not activation. Specialist brains still need canonical evidence wiring through M2/M3.

## Milestone status

```text
M0  Stage-2 stabilization / evidence-integrity gate       COMPLETE / GREEN
M1  Engine Authority Registry                             FOUNDATION BUILT / GREEN
M2  Canonical DecisionContext                             NEXT / START NOW
M3  Route all specialist brains through DecisionContext  NOT STARTED
M4  D6 sole repository-wide final authority              PARTIAL; D6 EXISTS
M5  Canonical FinalDecision / PaperTradeGuidance          NOT STARTED
M6  Jarvis read-only presentation                         NOT STARTED
M7  Contradiction / veto / replay / safety integration    NOT STARTED
M8  Real providers + historical/paper proof               NOT STARTED
```

## M2 next build — Canonical DecisionContext

M2 builds an immutable deterministic shared evidence object, not another predictor and not another arbiter.

Target contract:

```text
DecisionContext
├─ identity
│  ├─ symbol
│  ├─ timeframe
│  ├─ decision_time
│  ├─ snapshot_hash
│  └─ universe_watermark
├─ input_integrity
│  ├─ data_quality
│  ├─ PIT_status
│  ├─ freshness
│  └─ quarantine_status
├─ price_structure
├─ candle_anatomy
├─ levels
├─ indicators
├─ market_regime
├─ session_context
├─ index_context
├─ sector_context
├─ relative_strength
├─ memory
├─ historical_analogs
├─ hypotheses
├─ strategy_candidates
├─ orb_variants
├─ afre_scenarios
├─ derivatives
├─ events
├─ failure_scenarios
├─ execution_quality
├─ portfolio_risk
├─ blockers
├─ warnings
├─ proof_status
├─ paper_authority
└─ provenance
   ├─ engines_run[]
   ├─ evidence_versions[]
   └─ capability_sources[]
```

M2 must enforce:

1. same symbol/timeframe/decision time/snapshot hash;
2. M0 Stage2IntegrityReport passed or degraded without hard blockers;
3. explicit availability for every material evidence block;
4. no missing-to-neutral conversion;
5. no hidden provider fetch during context construction;
6. deterministic serialization/context hash;
7. material evidence changes change the hash;
8. context assembly cannot grant proof/paper authority;
9. context assembly cannot trade or route orders;
10. D6 remains the only final-band authority.

Full specialist routing remains M3.

## Remaining non-M0 infrastructure issues

These were inherited and were not hidden by M0:

1. Linux CI/HSTRY fixture coverage including `RELIANCE_NSE_5m.csv`.
2. PowerShell parser verification on Ubuntu.

They are separate from the now-green M0 contract/runtime work.

## Safety invariants

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
missing != neutral
unknown != false
unavailable != safe
synthetic != real
external_ai != safety_authority
ORB_or_AFRE_confirmation != proof_authority
```
