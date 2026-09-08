# Canonical Decision Spine Build Status — 2026-09-08

## Current status

```text
branch: decision-spine-orchestration-v1
base main: f26546047a28df7deb3916ed0b4467d67fd9bb7b
state: IN PROGRESS
```

AFRE v4 is already merged. This work is isolated from the AFRE branch.

## Architecture decision

Trade Vision does not need another independent BUY/SELL brain. It needs one causal evidence spine and one final authority.

```text
D1 DATA/PIT SAFETY
 -> D2 IMMUTABLE CLOSED-CANDLE SNAPSHOT
 -> STAGE-2 ANALYSIS BRAINS
 -> STAGE-2 EVIDENCE INTEGRITY
 -> DecisionContext
 -> Price / Context / Memory / Hypotheses / ORB / AFRE
 -> Derivatives / Events / Failure
 -> Risk / Execution
 -> FINAL CONFLUENCE / D6
 -> FinalDecision
 -> Jarvis display only
```

## Stage 1 verdict

Stage 1 is architecturally complete and should not be rebuilt. Preserve the D1-before-D2 ordering, closed-candle/PIT protection, deterministic D2 snapshot and snapshot hash, bad-data/unfinished-candle/kill-switch blocking, and same-snapshot downstream identity.

Future provider upgrades may improve inputs, but Stage 1 remains the root contract.

## Stage 2 verdict

The existing Paper Guidance Stage-2 core is real and useful:

```text
D2 snapshot
 -> Chart Reasoning
 -> Candle Condition
 -> Level Context
 -> Snapshot Indicator Runtime
 -> MTF Confirmation
 -> Persisted Indicator Memory
 -> Market Structure / Liquidity
 -> Execution / Event / OI Risk
 -> Final Confluence / D6
```

The repository-wide gap is that not every existing specialist is forced through this same evidence contract.

## M0 first build — Stage-2 Evidence Integrity

New files:

```text
apps/api/app/behavior/decision_spine/__init__.py
apps/api/app/behavior/decision_spine/authority_registry.py
apps/api/app/behavior/decision_spine/stage2_integrity.py
apps/api/tests/decision_spine/test_stage2_integrity.py
```

The first gate enforces:

- registered engine identity before canonical-context entry;
- exact D2 snapshot hash agreement;
- engine identity match;
- future leakage hard block;
- duplicate/unregistered engine hard block;
- unavailable evidence cannot be silently converted to neutral;
- synthetic/mock/masked/unknown evidence cannot be probability authority;
- non-D6 engines cannot claim the product final band;
- exactly one final-band authority: `FINAL_CONFLUENCE_ARBITER`;
- no registered engine has execution authority;
- empty Stage-2 evidence fails closed;
- this gate cannot grant paper promotion or execute.

Focused local pre-commit verification: **14 passed, 0 failed**, plus compile/import safety smoke PASS.

Important: this foundation is **not yet wired into the production Paper Guidance call path**. That is intentional; the contract is being established and tested before behavior changes.

## Inherited Stage-2 defects assigned to M0

### M0-C — `synthetic_fallback` contract drift — FIRST

Sequence records accept it while `IndicatorFeatureBlock` does not. Align the model while forcing explanation-only, probability-disabled semantics. `synthetic_fallback` is explicit provenance and must never become real, probability authority, proof authority, or trade authority.

### M0-A — 9C runtime provenance/accounting — SECOND

Separate the runtime accounting into:

```text
real computed
synthetic fallback computed
unavailable
failed
```

Never count synthetic fallback as real. The accounting must reconcile to the promoted runtime indicator count and must preserve explicit unavailable/error states.

### M0-B — PTA probe accounting — THIRD

Replace misleading single-count interpretation with:

```text
selected_count
probe_count
computed_count
no_signal_count
dependency_unavailable_count
error_count
```

Never fabricate a PTA result merely because a marker was selected/probed. PTA remains explanation/availability evidence only, with no probability or trading authority.

## M0 real-pipeline wiring — FOURTH

After M0-C/A/B are stabilized, wire the Stage-2 Evidence Integrity Gate into the actual Paper Guidance path:

```text
D2 Snapshot
   ↓
Stage-2 engine receipts / explicit migration observations
   ↓
Stage2IntegrityReport
   ↓
canonical evidence allowed forward
   ↓
D6 only if no hard integrity blocker
```

9C, PTA, ORB and AFRE must be explicit `SKIPPED/UNAVAILABLE` observations until their own D2-snapshot-native wiring exists. They must not be represented as neutral defaults or silently fetched through independent current-state paths.

## Milestone status

```text
M0  Stage-2 stabilization / evidence-integrity gate       IN PROGRESS
M1  Engine Authority Registry                             FOUNDATION ADDED
M2  Canonical DecisionContext                             NOT STARTED
M3  Route all specialist brains through DecisionContext  NOT STARTED
M4  D6 sole repository-wide final authority              NOT STARTED
M5  Canonical FinalDecision / PaperTradeGuidance          NOT STARTED
M6  Jarvis read-only presentation                         NOT STARTED
M7  Contradiction / veto / replay / safety integration    NOT STARTED
M8  Real providers + historical/paper proof               NOT STARTED
```

## Required M0 regression gate

M0 is not complete until all affected tests are run and the result is recorded:

1. 9C runtime/contract tests.
2. PTA runtime/probe tests.
3. Paper Guidance v1.88 Stage-2 tests.
4. Decision Spine Stage-2 integrity tests.
5. Relevant API regressions.
6. Compile/import checks for every changed module.

Only after this gate is green may M2 `DecisionContext` begin.

## Next code steps

1. Repair M0-C `synthetic_fallback` model and authority semantics.
2. Repair M0-A 9C provenance accounting.
3. Repair M0-B PTA probe accounting.
4. Wire `Stage2IntegrityReport` after Stage-2 receipts and before D6/canonical-context promotion.
5. Run the full affected regression set and repair any new regression without weakening safety semantics.
6. Build `DecisionContext` only after M0 is green.
7. Replace neutral arbiter placeholders with availability-bearing evidence during M2/M3, not by inventing values in M0.

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

## CI note

A guarded M0 branch workflow has been added to apply exact-scoped stabilization patches, compile the affected modules, run the focused regression gate, and commit source changes only after those checks pass. A workflow run—not the presence of the workflow file—is the evidence required before marking M0 green.
