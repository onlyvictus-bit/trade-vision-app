# Next Build Target

Last reviewed: 2026-09-08

> **Canonical status source:** `docs/CANONICAL_BUILD_STATUS.md`
>
> Do not advance milestone state in this file. Every coding/audit session must start from the canonical status document and update milestone truth there after verified commits/tests.

## Current milestone

**M2 — Canonical DecisionContext real-pipeline construction**

Active branch: `decision-spine-orchestration-v1`

M0 is GREEN/LOCKED. M1 authority-registry foundation is GREEN/scope-locked. M2 contract foundation is green, but the M2 milestone is still **IN BUILD**.

## Immediate scope

```text
D2 approved snapshot
        ↓
Stage-2 engine receipts
        ↓
Stage2IntegrityReport
        ↓
Canonical DecisionContext
        ↓
context_hash / provenance
        ↓
existing D6 unchanged
```

Before M2 may be marked GREEN, close every gate in `docs/CANONICAL_BUILD_STATUS.md` §5, including:

- exact `EvidenceBlock.source_engine` membership in the supplied `Stage2IntegrityReport`;
- Stage2 availability/source-mode compatibility;
- `freshness == BLOCK` rejection;
- explicit reasons for degraded/unknown/blocking input-integrity state;
- real Paper Guidance -> DecisionContext adapter with no refetch or neutral substitution;
- inactive ORB/AFRE/9C/PTA kept explicit `SKIPPED/UNAVAILABLE`;
- deterministic D2 -> Stage2 -> DecisionContext replay identity;
- changed closed candle -> changed snapshot/context hash;
- Stage2 BLOCK -> no DecisionContext;
- `context_hash` and provenance recorded without changing D6 behavior;
- targeted + Paper Guidance + full API regression + safety/authority checks;
- commit and audit before changing M2 to `GREEN / LOCKED`.

## Do not start M3 yet

M3 specialist migration starts only after M2 is fully GREEN/LOCKED in the canonical tracker.

Do not remove legacy D6 neutral placeholders inside M2 in a way that changes current D6 behavior. M2 first makes missing evidence explicit in the canonical context; M3 migrates the real specialist evidence and removes corresponding legacy placeholders with replay parity.

## Core rule

> **One milestone -> implement -> test -> audit -> commit -> GREEN -> lock.**

And:

> **Many brains may disagree internally. Only one decision may leave the brain.**

Full M0-M12 roadmap, exit gates, safety/proof separation, current code-audit findings and future-session procedure are in `docs/CANONICAL_BUILD_STATUS.md`.
