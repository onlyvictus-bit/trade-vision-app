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

### M0-A — 9C real-runtime provenance/count ambiguity

Current failure expected `real_runtime_computed_count=2`, observed 0. Runtime computation and real-market-data provenance are conflated. Fix the contract; never rename synthetic fallback as real to make the counter green.

### M0-B — PTA 23-selected versus actual-output ambiguity

The registry has 23 marker slots, but optional dependency availability affects output. Track selected, probed, computed/no-signal, dependency-unavailable and errors separately. Never fabricate outputs. PTA remains non-authoritative for trade/probability.

### M0-C — `synthetic_fallback` contract drift

Sequence records accept it while `IndicatorFeatureBlock` does not. Align the model while forcing explanation-only, probability-disabled semantics.

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

## Next code steps

1. Wire `Stage2IntegrityReport` after Stage-2 receipts and before canonical context promotion.
2. Add integration tests using real `PaperGuidanceEngineReceipt` objects.
3. Repair M0-A/B/C without converting synthetic/unavailable evidence into fake real/clean evidence.
4. Run existing Paper Guidance tests plus new Decision Spine tests.
5. Build `DecisionContext` only after M0 contracts are stable.
6. Replace neutral arbiter placeholders with availability-bearing evidence.

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
