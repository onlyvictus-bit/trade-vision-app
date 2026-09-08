# M2 audit verdict — canonical coding reference

Source: user-supplied `## M2 audit verdict.txt` on 2026-09-08. This document is the controlling implementation reference for the M2 Canonical DecisionContext milestone on branch `decision-spine-orchestration-v1`.

## Core verdict

M2 is **not another trading brain**. It is the system's **canonical world-state / evidence brain**:

> At this exact D2 snapshot, what facts do we actually know, what do we not know, which engine produced each fact, was that engine actually run, was its data causal, and can the entire state be reproduced exactly?

Trade Vision already has enough intelligence modules. M2 must not add another predictor, scoring model or LLM reasoning engine.

M2 requires **one new adapter/assembler module + targeted edits to existing Decision Spine code + new tests**.

## Existing M2 foundation

The existing `DecisionContext` contract is the correct foundation. It defines one immutable object containing 22 canonical evidence families:

1. `price_structure`
2. `candle_anatomy`
3. `levels`
4. `indicators`
5. `market_regime`
6. `session_context`
7. `index_context`
8. `sector_context`
9. `relative_strength`
10. `memory`
11. `historical_analogs`
12. `hypotheses`
13. `strategy_candidates`
14. `orb_variants`
15. `afre_scenarios`
16. `derivatives`
17. `events`
18. `failure_scenarios`
19. `execution_quality`
20. `portfolio_risk`
21. `proof_status`
22. `paper_authority`

The contract already provides immutable payloads, same-snapshot identity, future-evidence rejection, explicit missing evidence, no synthetic probability authority, no proof/paper/trade authority and no pre-D6 final-band authority, plus deterministic context hashing.

## Current runtime gap

Current Paper Guidance is approximately:

```text
PaperGuidanceRequest
        |
        v
D1 DATA QUALITY / PIT / MODE / KILL SWITCH
        |
        v
D2 CLOSED-CANDLE SNAPSHOT
        |
        +----------------------------------+
        |                                  |
        v                                  v
CHART_REASONING                     CANDLE_CONDITION
LEVEL_CONTEXT                       SNAPSHOT_INDICATORS
MTF_CONFIRMATION                    PERSISTED_MEMORY
MARKET_STRUCTURE                    EXECUTION_EVENT_OI_RISK
        |                                  |
        +----------------+-----------------+
                         |
                         v
                  Engine Receipts
                         |
                         +
                         |
              explicit SKIPPED:
              9C
              PTA
              ORB
              AFRE
                         |
                         v
              Stage2IntegrityReport
                         |
               +---------+---------+
               |                   |
             BLOCK               ELIGIBLE
               |                   |
               v                   v
       WAIT / DO NOTHING       legacy D6 request
       no D6                         |
                                     v
                              Final Confluence
```

`DecisionContext` is not yet in this runtime path. The missing M2 bridge is:

```text
Stage2IntegrityReport
        ↓
DecisionContext
```

## Critical causal inventory problem

DecisionContext requires 22 evidence fields, while the current Stage2 route contains only current active receipts plus four explicit skipped observations.

Current active identities are approximately:

```text
CHART_REASONING
CANDLE_CONDITION
LEVEL_CONTEXT
SNAPSHOT_INDICATOR_RUNTIME
MTF_CONFIRMATION
PERSISTED_INDICATOR_MEMORY
MARKET_STRUCTURE_LIQUIDITY
EXECUTION_EVENT_OI_RISK
```

Current explicit skipped identities:

```text
NINE_CANDLE_MEMORY
PTA_MARKER_RUNTIME
ORB_CORE
AFRE
```

Once M2 correctly requires every `EvidenceBlock.source_engine` to exist in the exact `Stage2IntegrityReport`, missing canonical evidence cannot simply be invented after Stage2. The owning source engine must already exist in Stage2 as explicit `UNAVAILABLE`, `SKIPPED`, or `ERROR` evidence.

Required causal flow:

```text
ACTIVE RECEIPTS
+
EXPLICIT INACTIVE / UNAVAILABLE OBSERVATIONS
        |
        v
COMPLETE Stage2 evidence inventory
        |
        v
Stage2IntegrityReport
        |
        v
DecisionContext
```

Stage2 must become a truthful inventory of what ran **and** what was expected but unavailable.

## File plan

| File | Action | Purpose |
|---|---|---|
| `apps/api/app/behavior/decision_spine/decision_context.py` | EDIT | Harden causal/integrity contract |
| `apps/api/app/behavior/decision_spine/stage2_integrity.py` | MINIMAL/NO CHANGE | M0 is locked; avoid reopening unless necessary |
| `apps/api/app/behavior/decision_spine/authority_registry.py` | NORMALLY NO CHANGE | M1 foundation remains locked |
| `apps/api/app/behavior/decision_spine/paper_guidance_decision_context_adapter.py` | NEW | Fast Paper Guidance → DecisionContext assembler |
| `apps/api/app/behavior/paper_guidance_spine.py` | EDIT | Insert adapter between Stage2 and legacy D6 |
| `apps/api/app/behavior/decision_spine/__init__.py` | SMALL EDIT | Export canonical adapter/contracts |
| `apps/api/tests/decision_spine/test_decision_context.py` | EDIT | Contract/adversarial hardening tests |
| `apps/api/tests/decision_spine/test_paper_guidance_decision_context_adapter.py` | NEW | Dedicated adapter unit tests |
| `apps/api/tests/test_paper_guidance_v188.py` | EDIT | End-to-end deterministic integration tests |
| `.github/workflows/m2-decision-context.yml` | EDIT | Compile/test new adapter and integration |
| `models.py` | PREFER NO CHANGE | Existing `risk_summary` can carry audit metadata |
| `final_confluence_arbiter.py` | NO CHANGE IN M2 | D6 behavior must remain identical |
| ORB/AFRE | NO CHANGE IN M2 | Canonical activation belongs to M3 |
| Jarvis | NO CHANGE IN M2 | Jarvis migration belongs to M6 |

## Adapter design

Create:

```text
apps/api/app/behavior/decision_spine/
    paper_guidance_decision_context_adapter.py
```

The adapter must be deliberately boring:

- no market calculations
- no fetching
- no database search
- no indicator recomputation
- no ORB execution
- no AFRE execution
- no AI calls
- no probability calculation
- no D6/final-band authority

Its entire job:

```text
already computed evidence
        ↓
validate identity
        ↓
normalize evidence
        ↓
represent missing evidence explicitly
        ↓
construct immutable DecisionContext
```

Conceptual API:

```python
build_paper_guidance_decision_context(
    snapshot,
    data_quality,
    point_in_time,
    receipts,
    stage2_integrity,
) -> DecisionContext
```

For efficiency build constant-time indexes once:

```python
receipt_by_engine = {receipt.engine_id: receipt for receipt in receipts}
stage2_by_engine = {state.engine_id: state for state in stage2_integrity.engine_states}
```

Mapping complexity should remain approximately O(number of engines + 22 evidence fields). No nested repeated receipt scans.

## Conservative current-runtime evidence mapping

M2 must represent truth, not aspirational availability.

| DecisionContext field | Current source | M2 state |
|---|---|---|
| `price_structure` | `MARKET_STRUCTURE_LIQUIDITY` | receipt status |
| `candle_anatomy` | `CANDLE_ANATOMY` | UNAVAILABLE |
| `levels` | `LEVEL_CONTEXT` | receipt status |
| `indicators` | `SNAPSHOT_INDICATOR_RUNTIME` | receipt status |
| `market_regime` | `MARKET_REGIME` | UNAVAILABLE |
| `session_context` | `SESSION_MEMORY` | UNAVAILABLE |
| `index_context` | `INDEX_CONTEXT` | UNAVAILABLE |
| `sector_context` | `SECTOR_CONTEXT` | UNAVAILABLE |
| `relative_strength` | `RELATIVE_STRENGTH` | UNAVAILABLE |
| `memory` | `PERSISTED_INDICATOR_MEMORY` | receipt status |
| `historical_analogs` | `ANALOG_MEMORY` | UNAVAILABLE |
| `hypotheses` | `HYPOTHESIS_ENGINE` | UNAVAILABLE |
| `strategy_candidates` | `ORB_CORE` | SKIPPED |
| `orb_variants` | `ORB_CORE` | SKIPPED |
| `afre_scenarios` | `AFRE` | SKIPPED |
| `derivatives` | `DERIVATIVES` | UNAVAILABLE |
| `events` | `EXECUTION_EVENT_OI_RISK` | receipt status/degraded when nested evidence is unavailable |
| `failure_scenarios` | `FAILURE_DETECTOR` | UNAVAILABLE |
| `execution_quality` | `EXECUTION_EVENT_OI_RISK` | receipt status |
| `portfolio_risk` | `BEHAVIOR_RISK` | UNAVAILABLE |
| `proof_status` | existing registered proof-related ownership until a dedicated canonical source is migrated | UNAVAILABLE |
| `paper_authority` | existing registered compatibility/paper-authority ownership until canonical migration | UNAVAILABLE |

The governing semantic rule is:

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
```

Example:

```text
sector_context = UNAVAILABLE
```

is correct when no sector evidence exists. `weak_sector = False` is not equivalent and must not be treated as real evidence.

## Legacy placeholders

Current D6 compatibility inputs include neutral placeholders such as:

```python
relative_strength_score = 0.5
indicator_signal_score = 0.0
external_ai_score = 0.0
weak_sector = False
```

Do **not** remove or reinterpret these in M2. That is an M3/M4 migration concern. M2 must preserve legacy D6 behavior exactly while independently recording truthful canonical evidence state.

## Required hardening: exact Stage2 membership

`decision_context.py` currently verifies that an evidence source is globally registered. M2 must also verify that it exists in **this exact Stage2 report**.

Required checks:

```text
EvidenceBlock
   +--> globally registered?
   +--> present in this Stage2 report?
   +--> same D2 snapshot?
   +--> compatible availability?
   +--> compatible source mode?
```

## Required hardening: monotonic authority / no status upgrade

DecisionContext may preserve or downgrade Stage2 evidence, but it must never upgrade it.

Allowed examples:

```text
AVAILABLE -> AVAILABLE
AVAILABLE -> DEGRADED
AVAILABLE -> UNAVAILABLE
DEGRADED -> DEGRADED
DEGRADED -> UNAVAILABLE
```

Forbidden examples:

```text
DEGRADED -> AVAILABLE
SKIPPED -> AVAILABLE
UNAVAILABLE -> AVAILABLE
ERROR -> AVAILABLE
```

Terminal `SKIPPED`, `UNAVAILABLE`, and `ERROR` states should normally remain exact terminal states.

Source-mode provenance must also be monotonic. A Stage2 `UNKNOWN`, `MOCK`, `MASKED`, or `SYNTHETIC_FALLBACK` source cannot become `REAL` or `VERIFIED_SNAPSHOT` inside DecisionContext.

## Required hardening: freshness

M2 must reject:

```text
freshness = BLOCK
        ↓
NO DecisionContext
```

PIT PASS does **not** imply freshness PASS. Until a D2-native canonical freshness assessor is wired, the adapter must not fabricate `PASS`. A safe state is:

```text
pit_status = PASS
freshness = UNKNOWN
reason = "No canonical D2-native freshness assessor is wired in this Paper Guidance path."
```

## Required hardening: explanations for non-PASS integrity

`DEGRADED`, `UNKNOWN`, or `BLOCK` input integrity must have an explicit reason. `PASS` may omit one.

This is required for replay, auditability, debugging and operator understanding.

## D2 remains unchanged

Do not rebuild D2. Its existing deterministic closed-candle snapshot and SHA-256 identity are the causal root.

Required invariants:

```text
same closed data -> same snapshot_hash
changed closed candle -> changed snapshot_hash
unfinished candle -> never admitted to D2
```

## Stronger provenance

High-value M2 enhancement: carry the exact receipt fingerprint into each canonical evidence block using a field such as:

```python
source_output_hash: str | None
```

Desired chain:

```text
D2 snapshot_hash
        ↓
engine receipt output_hash
        ↓
EvidenceBlock
        ↓
DecisionContext context_hash
```

This makes every canonical fact traceable back to its source receipt and D2 snapshot.

## Speed and efficiency requirements

M2 itself must be extremely fast because it should perform almost no market calculations.

Performance rule:

```text
CALCULATE ONCE
VALIDATE ONCE
MAP ONCE
HASH ONCE
```

Never:

```text
calculate indicator
    ↓
DecisionContext asks again
    ↓
recalculate indicator
    ↓
D6 calculates again
```

DecisionContext should contain bounded evidence summaries, not thousands of OHLCV bars, full dataframes, complete TA arrays, or entire historical ledgers.

Use compact evidence:

```text
indicator states/values
available_count
source_output_hash
historical sample_count
match_count
outcome distributions
quality
best-match IDs
memory version/hash
```

The existing deterministic JSON + SHA-256 hashing approach is acceptable unless measured profiling later proves otherwise.

## Compact Paper Guidance audit output

Do not change `PaperTradeGuidance` into another large schema during M2. Store a compact projection in `risk_summary`:

```text
decision_context:
    context_version
    context_hash
    snapshot_hash
    stage2_integrity_hash

    integrity:
        data_quality
        pit_status
        freshness
        quarantine_status

    evidence:
        available_count
        degraded_count
        unavailable_count
        skipped_count
        error_count

    safety:
        paper_promotion_eligible = false
        trade_allowed = false
        order_routing_enabled = false
        live_trading_blocked = true
```

Do not dump the complete DecisionContext into normal API responses.

## Determinism acceptance test

A completed M2 must prove:

```text
REQUEST A
    ↓
D2 hash = X
    ↓
Stage2 hash = Y
    ↓
DecisionContext hash = Z
    ↓
legacy D6 result = R
```

Replay of the same request must produce the same X/Y/Z/R.

Changing one legitimate **closed** candle must change D2 and DecisionContext hashes. An unfinished candle must never enter D2.

## Failure semantics

Every failure moves in one direction:

```text
uncertainty increases
      ↓
authority decreases
```

Never:

```text
missing evidence
      ↓
neutral assumption
      ↓
normal confidence
```

Expected outcomes include:

```text
future evidence -> BLOCK context
wrong snapshot -> BLOCK context
engine absent from exact Stage2 report -> BLOCK context
freshness BLOCK -> BLOCK context
engine SKIPPED -> explicit SKIPPED
sector unavailable -> UNAVAILABLE
derivatives feed missing -> UNAVAILABLE
synthetic evidence -> explanation only
unknown proof -> cannot grant paper authority
```

## Do not activate additional brains in M2

Repository existence is not runtime availability. Existing specialist modules must remain `UNAVAILABLE`/`SKIPPED` in the canonical context until they are properly migrated in M3.

Do not convert M2 into M2+M3+M4.

## Desired intelligence properties

Trade Vision is not declared AGI. The engineering target is a bounded multi-specialist decision-intelligence architecture with:

```text
ONE consistent world state
    +-- price specialist
    +-- candle specialist
    +-- regime specialist
    +-- context specialist
    +-- memory specialist
    +-- analog specialist
    +-- hypothesis specialist
    +-- ORB/AFRE specialist
    +-- derivatives specialist
    +-- failure specialist
    +-- risk specialist
    +-- execution specialist
    +-- external reviewers
        ↓
explicit disagreement
explicit uncertainty
explicit missing knowledge
causal provenance
memory
counterfactual/failure reasoning
replay
self-audit
single decision authority
```

The key intelligence property is not more brains. It is knowing what every brain knows, what it does not know, where its evidence came from, whether it is trustworthy, how it conflicts with other evidence, and which authority is allowed to act on it.

## M2 → M12 direction

```text
M2  Canonical world-state
 ↓
M3  Specialists all read/write canonical evidence
 ↓
M4  D6 reasons over one canonical world-state
 ↓
M5  One deterministic FinalDecision
 ↓
M6  Jarvis explains it
 ↓
M7  System attacks its own conclusions
 ↓
M8  Verified real providers
 ↓
M9  Historical/walk-forward proof
 ↓
M10 Paper-world learning
 ↓
M11 Operational hardening
 ↓
M12 Independent release gate
```

## Exact M2 implementation order

1. **Harden `InputIntegrity`.** Add `freshness=BLOCK` rejection and mandatory reasons for DEGRADED/UNKNOWN/BLOCK states.
2. **Harden EvidenceBlock ↔ Stage2 causality.** Every evidence source must exist in the exact report; enforce snapshot, availability and source-mode compatibility with no authority upgrade.
3. **Define the canonical M2 field binding table.** Explicitly specify which current engine owns each of the 22 fields and which fields are currently inactive.
4. **Expand the pre-Stage2 inventory.** Add explicit `SKIPPED/UNAVAILABLE` observations for canonical engines that are not currently active.
5. **Create `paper_guidance_decision_context_adapter.py`.** Pure deterministic mapping only; absolutely no I/O, refetch, re-run or trading computation.
6. **Add `source_output_hash` to `EvidenceBlock` if it can be done without weakening compatibility.** This gives exact receipt → evidence → context provenance.
7. **Wire the adapter immediately after an eligible `Stage2IntegrityReport`.** Stage2 BLOCK must continue returning before DecisionContext and before D6.
8. **Record compact DecisionContext audit metadata in Paper Guidance.** Include `context_hash`, Stage2 hash, snapshot hash and integrity/availability summary.
9. **Leave D6 inputs completely unchanged.** Keep legacy neutral compatibility values temporarily so M2 has exact behavior parity.
10. **Create adapter tests and strengthen DecisionContext tests.** Test membership, no-upgrade semantics, freshness, reasons, missing evidence and receipt provenance.
11. **Add end-to-end Paper Guidance replay tests.** Same D2 → same Stage2 → same context → same existing D6 guidance; changed closed candle → changed hashes; Stage2 BLOCK → no context.
12. **Run targeted + Paper Guidance + complete API regression + authority audit.** Only after all are green should documentation and commit state advance to M2 GREEN/LOCKED.

## Explicit M2 exclusions

Do not modify these unless an M2 test exposes a narrow causal defect:

```text
ORB strategy behavior
AFRE calculations
derivatives formulas
Kronos
Gemini
Grok
Jarvis arbitration
FinalDecision
paper promotion criteria
live providers
walk-forward proof
paper execution
broker routing
```

## M2 target architecture

```text
                         D1
              DATA / PIT / SAFETY
                         |
                         v
                         D2
               IMMUTABLE SNAPSHOT
                         |
                  snapshot_hash
                         |
                         v
              SPECIALISTS THAT ARE
              CURRENTLY D2-NATIVE
                         |
                         v
                    RECEIPTS
               output_hash each
                         |
              +----------+----------+
              |                     |
           ACTIVE              NOT ACTIVE
          evidence              explicit
                             unavailable/skipped
              |                     |
              +----------+----------+
                         |
                         v
             Stage2IntegrityReport
                         |
              stage2_integrity_hash
                         |
               exact membership
               exact availability
               exact source mode
                         |
                         v
              CANONICAL DecisionContext
                         |
                    context_hash
                         |
          +--------------+--------------+
          |                             |
      audit/replay                 future M3 consumers
          |
          v
        CURRENT
      LEGACY D6
       UNCHANGED
```

## Completion rule

M2 is not complete merely because the contract compiles. It is complete only when the real Paper Guidance path constructs a deterministic canonical DecisionContext from D2-linked Stage2 evidence, exposes compact provenance for replay/audit, leaves D6 behavior unchanged, passes the focused M2 suite, Stage2 regression, Paper Guidance regression, full API regression, and Decision Spine authority invariants.
