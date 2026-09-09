# Trade Vision — Canonical Build Status

> Durable source of truth. Repository code + tests + exact-head CI override stale prose.
>
> Program law: implement -> targeted/adversarial/replay tests -> locked regressions -> full tree -> authority audit -> exact-head CI -> GREEN -> lock.

**Last audited:** 2026-09-09  
**Production baseline:** `main@7a15bfb3717d34ea75d19a6584a3ef814fae8001` (PR #2 merge)  
**Merged verified feature parent:** `761ea5c0935d3f5e6b9ee2156dee1aa96eddb654`  
**Active planning branch:** `m4-d6-orchestration-redesign`  
**M4 design index:** `docs/M4_D6_ORCHESTRATION_MASTER_BUILD_INDEX_2026-09-09.md`

## Locked authority and safety law

```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
future != causal
unfinished != closed
stale != fresh
correlated facts != independent episodes
label observed later != label available now

D1 outranks every predictor/reviewer
all active M2+ evidence is causal to D2
FINAL_CONFLUENCE_ARBITER / D6 is sole final-band authority
all M3 canonical specialists remain bounded and non-executing
raw_record_count remains separate from independent_episode_count

trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

## Milestone truth

| Step | Milestone | State |
|---|---|---|
| M0 | Stage-2 integrity | **GREEN / LOCKED** |
| M1 | Authority Registry | **FOUNDATION GREEN / SCOPE LOCKED** |
| M2 | Canonical DecisionContext | **GREEN / LOCKED** |
| M3 | Brain migration | **BASELINE COMPLETE THROUGH M3.3** |
| M3.1 | Canonical Price Intelligence | **GREEN / LOCKED** |
| M3.2 | Canonical Context Intelligence | **GREEN / LOCKED** |
| M3.3 | Canonical Memory Intelligence | **GREEN / LOCKED** |
| M4 | D6 orchestration redesign | **DESIGN BASELINE IN PROGRESS / NO PRODUCTION CODE** |

## M0-M3.3 production baseline

PR #2 merged the verified Decision Spine M0 through M3.3 feature line into `main` at:

```text
7a15bfb3717d34ea75d19a6584a3ef814fae8001
```

The merge commit includes verified feature parent:

```text
761ea5c0935d3f5e6b9ee2156dee1aa96eddb654
```

The merge records the exact-head CI, PIT/replay-safety fixes, full API regression, and authority/safety verification completed before production merge. No commits were present on `main` after that merge at the start of M4 planning.

## Locked M3 architecture

```text
D1 SAFETY / DATA INTEGRITY
        |
D2 CLOSED SNAPSHOT / IDENTITY
        |
        +----------------------+----------------------+
        |                      |                      |
M3.1 CANONICAL PRICE    M3.2 CANONICAL CONTEXT  M3.3 CANONICAL MEMORY
        \                      |                      /
         \_____________________+_____________________/
                               |
                     CANONICAL DECISION CONTEXT
                               |
                   CURRENT D6 COMPATIBILITY SEAM
                               |
                  FINAL_CONFLUENCE_ARBITER
                               |
                       PAPER GUIDANCE ONLY
```

## Current D6 truth entering M4

Current production D6 (`final-confluence-conflict-arbiter.v1.75`) preserves hard safety/data/liquidity/post-entry blockers and sole final-band authority, but its final decision still centers on a weighted vote sum plus conflict score adjustments. Its confidence interval is mainly derived from bounded score position, conflict count and evidence count. It does not yet use the full canonical price/context/memory worlds as a typed authority/epistemic/conflict/scenario/counterfactual reasoning state machine.

M4 is authorized specifically to replace that orchestration weakness while retaining all locked authority and safety laws.

## M4 planning boundary

The `m4-d6-orchestration-redesign` branch is documentation/design only until the complete M4 design baseline is reviewed and locked. It must not contain production M4 implementation during this phase.

M4 design must define:
- canonical input/receipt contract;
- explicit authority graph;
- explicit epistemic states;
- deterministic conflict graph;
- failure/scenario reasoning;
- bounded counterfactual robustness;
- semantic confidence/uncertainty;
- deterministic D6 final arbitration;
- structured reason tree/decision receipt;
- compatibility migration;
- adversarial/replay/performance verification;
- stage-by-stage implementation and lock roadmap.

## Next authorized build

After the M4 documentation baseline is committed, reread and internally verified from GitHub, the first implementation stage is **M4-A — Canonical Input Contract + Receipt Validator**. No later stage may bypass that contract or recompute locked M3 facts.
