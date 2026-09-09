# M4 D6 Orchestration — Master Build Index

Date: 2026-09-09  
Baseline: `main@7a15bfb3717d34ea75d19a6584a3ef814fae8001`  
Branch: `m4-d6-orchestration-redesign`

## Mission

Redesign D6 from a weighted-score finalizer into a deterministic, authority-aware, evidence/uncertainty/conflict/scenario reasoner that consumes canonical D1/D2/M3.1/M3.2/M3.3 receipts and remains the sole final-band authority. No production M4 implementation is included in this planning baseline.

## Non-negotiable laws

- D1 outranks every predictor, reviewer, strategy and memory system.
- `FINAL_CONFLUENCE_ARBITER` remains the sole final-band authority.
- `missing != neutral`, `unknown != false`, `unavailable != safe`, `stale != fresh`, `future != causal`.
- M4 consumes canonical receipts; it does not recompute locked M3 facts.
- No hidden weighted vote may overpower a higher-authority blocker.
- Long and short are independently reasoned.
- `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, `human_approval_required=true`.

## Target architecture

```text
D1 SAFETY / DATA INTEGRITY
        |
D2 CLOSED SNAPSHOT + IDENTITY
        |
        +----------------------+----------------------+
        |                      |                      |
 M3.1 PRICE WORLD       M3.2 CONTEXT WORLD     M3.3 MEMORY WORLD
        \                      |                      /
         \_____________________+_____________________/
                               |
                    CANONICAL DECISION CONTEXT
                               |
                 M4 INPUT/RECEIPT VALIDATOR
                               |
                 AUTHORITY + EPISTEMIC MODEL
                               |
                       CONFLICT GRAPH
                               |
                FAILURE / SCENARIO REASONER
                               |
                 COUNTERFACTUAL CHALLENGE
                               |
                  ADVERSARIAL SELF-REVIEW
                               |
             UNCERTAINTY / ROBUSTNESS SYNTHESIS
                               |
                  D6 FINAL ARBITRATION
                               |
                REASON TREE + DECISION RECEIPT
                               |
                       PAPER GUIDANCE
```

## Build dependency graph

```text
M4-0 CURRENT D6 AUDIT
        |
M4-1 INPUT + EVIDENCE CONTRACT
        |
M4-2 AUTHORITY + EPISTEMIC MODEL
        |
        +-------------------+
        |                   |
M4-3 CONFLICT GRAPH   M4-4 FAILURE/SCENARIO/COUNTERFACTUAL
        |                   |
        +---------+---------+
                  |
          M4-5 UNCERTAINTY
                  |
          M4-6 D6 ARBITRATION
                  |
          M4-7 REASON RECEIPTS
                  |
          M4-8 MIGRATION/WIRING
                  |
          M4-9 ADVERSARIAL TESTS
                  |
          M4-10 IMPLEMENTATION ROADMAP
                  |
             IMPLEMENTATION
                  |
           EXACT-HEAD CI + LOCK
```

## Ordered documents

1. `M4_0_D6_EXISTING_SYSTEM_AUDIT_2026-09-09.md`
2. `M4_1_CANONICAL_INPUT_AND_EVIDENCE_CONTRACT_2026-09-09.md`
3. `M4_2_AUTHORITY_AND_EPISTEMIC_REASONING_DESIGN_2026-09-09.md`
4. `M4_3_CONFLICT_RESOLUTION_ENGINE_DESIGN_2026-09-09.md`
5. `M4_4_SCENARIO_FAILURE_AND_COUNTERFACTUAL_REASONING_2026-09-09.md`
6. `M4_5_CONFIDENCE_UNCERTAINTY_AND_ROBUSTNESS_MODEL_2026-09-09.md`
7. `M4_6_FINAL_CONFLUENCE_ARBITER_DESIGN_2026-09-09.md`
8. `M4_7_REASON_TREE_AND_DECISION_RECEIPT_DESIGN_2026-09-09.md`
9. `M4_8_MIGRATION_AND_COMPATIBILITY_PLAN_2026-09-09.md`
10. `M4_9_ADVERSARIAL_REPLAY_AND_SAFETY_TEST_PLAN_2026-09-09.md`
11. `M4_10_IMPLEMENTATION_STAGE_ROADMAP_2026-09-09.md`

## Common implementation contract for every order

Each order defines: purpose; repository truth; problem; scope/non-scope; inputs/outputs; data model; authority; state transitions; algorithms; fail behavior; fail-closed behavior; missing-data behavior; long/short behavior; edge cases; performance; determinism; replay; observability; receipts; unit/adversarial/regression tests; acceptance/lock criteria; migration impact; rollback; dependencies; expected changed files; forbidden casual edits.

## Stage lock law

No stage becomes GREEN because targeted tests pass alone. Required sequence:

`implementation -> targeted tests -> adversarial/replay -> locked regressions -> full API tree -> authority audit -> exact-head CI -> GREEN -> lock`

## Performance budget principles

- Bounded loops only; no recursive self-reasoning.
- Consume each canonical world once per DecisionContext.
- Deterministic stable ordering for evidence, conflicts, scenarios and receipts.
- Fixed maximum scenario and counterfactual counts.
- Hash/replay equivalence for identical inputs.
- Cache keys include context hash + M4 policy/version.
- No unbounded historical analog scan in D6.

## Frozen non-scope

- Broker execution or order routing.
- Autonomous trade placement.
- Rewriting locked M3 calculators.
- Hidden LLM reasoning as decision authority.
- Universal win-probability claims.

## Recommended implementation sequence

M4-A receipt validator -> M4-B authority/epistemic -> M4-C conflicts -> M4-D failure risk -> M4-E scenarios/counterfactual -> M4-F uncertainty -> M4-G D6 arbitration -> M4-H receipts -> M4-I compatibility -> M4-J adversarial replay -> M4-K regression/performance -> M4-L authority audit/exact-head lock.
