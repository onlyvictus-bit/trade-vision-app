# Trade Vision — Canonical Build Status

> Durable source of truth. Repository code + tests + exact-head CI override stale prose.
>
> Program law: implement -> targeted/adversarial/replay tests -> locked regressions -> full tree -> authority audit -> exact-head CI -> GREEN -> lock.

**Last audited:** 2026-09-09  
**Active branch:** `m3-2-context-intelligence`  
**Controlling M3.3 spec:** `docs/M3_3_CANONICAL_MEMORY_INTELLIGENCE_ANALYSIS_AND_BUILD_PLAN_2026-09-08.md`

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
all M3.3 canonical memory specialists may_execute = false
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
| M3 | Brain migration | **IN BUILD** |
| M3.1 | Canonical Price Intelligence | **GREEN / LOCKED** |
| M3.2 | Canonical Context Intelligence | **GREEN / LOCKED** |
| M3.3 | Canonical Memory Intelligence | **GREEN / LOCKED** |
| M3.3-A | Memory episode contract / freezer | **GREEN / LOCKED** |
| M3.3-B | Delayed labels + PIT corpus | **GREEN / LOCKED** |
| M3.3-C | Canonical analog retrieval | **GREEN / LOCKED** |
| M3.3-D | Canonical memory world / health | **GREEN / LOCKED** |
| M3.3-E | Auditable retention / tombstones | **GREEN / LOCKED** |
| M3.3-F | Canonical persisted-memory adapter | **GREEN / LOCKED** |
| M3.3-G | Zero-authority isolation | **GREEN / LOCKED** |
| M3.3-H | Real-data reliability + historical session memory | **GREEN / LOCKED** |
| M3.3-I | Day-shape v2 / pattern memory | **GREEN / LOCKED** |
| M3.3-J | Snapshot-native Nine-Candle memory | **GREEN / LOCKED** |
| M3.3-K | Canonical PTA marker evidence | **GREEN / LOCKED** |
| M3.3-L | Production wiring + replay/adversarial lock | **GREEN / LOCKED** |
| M4 | D6 orchestration redesign | **NEXT / NOT STARTED** |

## M3.3 lock candidate and CI

Implementation lock candidate before this documentation commit:

```text
c336e33065ce3fc00e71798f53c3fb4a5ae3b074
workflow: M3.3 Canonical Memory Intelligence
run:      34334397084
```

That exact implementation-head run verified M3.3-A through M3.3-L and the locked M3.2, M3.1, M2, M0 and Paper Guidance regressions before this documentation-only lock update. The documentation-head M3.3 workflow is the final exact-head lock arbiter and must remain green before the branch advances to M4.

## Locked M3.3 architecture

```text
M3.1 CANONICAL PRICE WORLD
            +
M3.2 CANONICAL CONTEXT WORLD
            |
            v
CANONICAL MEMORY EPISODE FREEZER
            |
            +--> deterministic episode identity
            +--> D2 / price / context / source hashes
            +--> explicit missing / degraded / contradiction state
            +--> raw facts != independent episode count
            |
            v
DELAYED LABEL + PIT CORPUS
            |
            +--> label_available_at gate
            +--> duplicate collapse / conflict fail-closed
            +--> quarantine provenance
            +--> auditable retention / tombstones
            |
            v
CANONICAL MEMORY VIEWS
            |
            +--> analog retrieval
            +--> reliability memory (real labelled history only)
            +--> historical session memory
            +--> day-shape v2 / pattern memory
            +--> snapshot-native Nine-Candle memory
            +--> canonical PTA marker evidence
            +--> OOD / drift / sample sufficiency / quarantine health
            |
            v
CANONICAL MEMORY WORLD / BOUNDED RECEIPTS
            |
            v
CURRENT DECISION SPINE COMPATIBILITY SEAM
            |
            v
D6 FINAL_CONFLUENCE_ARBITER (UNCHANGED SOLE FINAL AUTHORITY)
```

## M3.3 invariants now locked

- one market episode cannot become dozens of independent samples because many indicators fired;
- labels are unavailable until their causal outcome horizon has completed;
- future/synthetic/identity-mismatched/non-finite evidence fails closed;
- no fixture outcome fallback is allowed in canonical reliability memory;
- no mock analog generation is allowed in canonical retrieval;
- day-shape v2 uses candle close-time windows and preserves missing previous-close state;
- large pattern/9C corpora require bounded retrieval rather than unbounded decision-path scans;
- Nine-Candle current state is D2 snapshot-native and cannot manufacture current candles or model probabilities;
- PTA marker evidence is D2-bound, bounded, explanation-only evidence;
- OOD, drift, sample insufficiency and quarantine remain explicit states rather than neutral defaults;
- retention is auditable and cannot prune below configured independent-history floors;
- public Paper Guidance compatibility hooks remain preserved, while unmodified production persisted memory uses the canonical one-query adapter;
- canonical memory specialists have no final-band or execution authority;
- D6 redesign remains deferred to M4.

## What is intentionally not claimed

M3.3 does **not** claim that memory produces a universal trade-win probability. Outcome distributions remain descriptive unless a future policy-specific calibrated target contract explicitly defines such a probability. It also does not activate live execution, broker routing, autonomous position sizing, or a competing final decision.

## Next authorized build

M4 is the next architectural milestone: redesign D6 orchestration to consume the now-locked canonical price, context and memory worlds without restoring duplicate calculators, neutralizing missing evidence, or granting hidden authority to specialist engines.
