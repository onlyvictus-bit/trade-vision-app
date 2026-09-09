# Next Build Target

Last reviewed: 2026-09-09

> `docs/CANONICAL_BUILD_STATUS.md` is the durable status source. Code/tests/exact-head CI override stale prose.

## Current truth

```text
M0      Stage-2 integrity                    GREEN / LOCKED
M1      Authority Registry                   FOUNDATION GREEN / SCOPE LOCKED
M2      Canonical DecisionContext            GREEN / LOCKED
M3      Brain migration                      IN BUILD
M3.1    Canonical Price Intelligence         GREEN / LOCKED
M3.2    Canonical Context Intelligence       GREEN / LOCKED
M3.3    Canonical Memory Intelligence        GREEN / LOCKED
M4      D6 orchestration redesign            NEXT / NOT STARTED
```

## M3.3 lock summary

Canonical Memory Intelligence now provides:

- deterministic D2-bound memory episode identity;
- delayed labels with explicit `label_available_at` causality;
- PIT-safe corpus retrieval, duplicate collapse and conflicting-label fail-closed behavior;
- separate raw-record and independent-episode/session counts;
- analog retrieval with independence controls;
- real-labelled reliability memory with no fixture fallback;
- historical session memory without synthetic exact-time histories;
- canonical day-shape v2 pattern memory with explicit missingness and bounded retrieval;
- snapshot-native Nine-Candle memory without mock packet generation;
- D2-bound PTA marker explanation evidence;
- OOD, drift, sample-sufficiency, quarantine and auditable retention state;
- one-query production persisted-memory compatibility wiring;
- replay/adversarial tests and complete authority registration;
- zero final-band and zero execution authority for canonical M3.3 specialists.

The current implementation lock candidate is `c336e33065ce3fc00e71798f53c3fb4a5ae3b074`; its M3.3 workflow run is `34334397084`. Documentation-only commits after that implementation head must also pass the exact-head M3.3 workflow before M4 begins.

## Next build — M4 D6 orchestration redesign

M4 must redesign the final orchestration around the three locked canonical worlds rather than adding another independent trading score.

```text
D1 SAFETY / DATA INTEGRITY
        |
        v
D2 CLOSED-CANDLE SNAPSHOT
        |
        +--------------------+
        |                    |
        v                    v
M3.1 PRICE WORLD       M3.2 CONTEXT WORLD
        \                    /
         \                  /
          +--> M3.3 MEMORY WORLD
                    |
                    v
          CANONICAL DECISION CONTEXT
                    |
                    v
             M4 D6 ORCHESTRATOR
                    |
                    +--> conflict resolution
                    +--> explicit missing/degraded handling
                    +--> authority-ranked evidence
                    +--> reason tree / uncertainty
                    +--> conservative final band
                    |
                    v
          PAPER GUIDANCE ONLY
```

## M4 non-negotiable design laws

1. `FINAL_CONFLUENCE_ARBITER / D6` remains the sole final-band authority unless a separately approved migration explicitly replaces that identity.
2. D1 hard blockers outrank every predictor, memory view, reviewer and strategy.
3. Missing, degraded, stale, OOD, quarantined or contradictory evidence may not be silently converted to neutral/zero.
4. M4 consumes canonical M3.1/M3.2/M3.3 receipts; it must not recompute their raw facts independently.
5. Memory sample size must use independent evidence, not correlated indicator-row count.
6. Reviewers/LLMs may explain or downgrade but cannot upgrade a hard safety block or create execution authority.
7. Conflict resolution must be deterministic, replay-stable and auditable.
8. No hidden weighted average may allow many weak votes to overwhelm one higher-authority blocker.
9. Confidence must reflect evidence quality, independence, contradiction, OOD/drift and missingness; it cannot be a cosmetic score.
10. Short-side logic remains explicit and separately validated; do not infer symmetry from long-side behavior.
11. Paper Guidance public contracts and locked regressions remain compatibility constraints during migration.
12. `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, `human_approval_required=true` remain hard product boundaries.

## Required M4 first action

Before coding M4, create a repository-grounded D6 analysis/build plan that inventories every current vote, blocker, downgrade path, duplicated calculation, authority conflict, missing-evidence default, and compatibility dependency. The plan must define the canonical input contract and migration sequence before changing final arbitration behavior.

## Hard boundary

Do not modify locked M3.1, M3.2 or M3.3 calculations merely to make M4 pass. M4 must consume their canonical outputs and fix orchestration at the orchestration layer.
