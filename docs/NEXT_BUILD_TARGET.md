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
M3.1-A  Snapshot Feature Kernel              GREEN / LOCKED
M3.1-B  Canonical Candle Intelligence        GREEN / LOCKED
M3.1-C  Canonical Level Intelligence         GREEN / LOCKED
M3.1-D  Canonical Indicator Intelligence     GREEN / LOCKED
M3.1-E  PIT-safe MTF Intelligence            GREEN / LOCKED
M3.1-F  Price Evidence Fusion / DAG / parity GREEN / LOCKED
M3.2    Canonical Context Intelligence       GREEN / LOCKED
M3.2-A  Context Source Contract              GREEN / LOCKED
M3.2-B  Canonical Session Intelligence       GREEN / LOCKED
M3.2-C  Canonical Index/Sector Context       GREEN / LOCKED
M3.2-D  Canonical Relative Strength          GREEN / LOCKED
M3.2-E  Canonical Market Regime              GREEN / LOCKED
M3.2-F  Context Fusion / Wiring / Parity     GREEN / LOCKED
M3.3    Canonical Memory Intelligence        NEXT / DESIGN STAGED / RUNTIME NOT ACTIVE
```

## Exact M3.2 lock evidence

```text
M3.2-B source: 5c944ac0f727767f5494af4c23b9334366860a8d
M3.2-B run:    34321289260 — SUCCESS

M3.2-C source: 64eaa47f5ecf02c18aa3b3422ef1e0cab9b489e6
M3.2-C run:    34323060143 — SUCCESS

M3.2-D source: 576ca58e5b4f62aeb4925a02e056680923cc4f22
M3.2-D run:    34325190554 — SUCCESS

M3.2-E source: 1a03a0888ea3fdd92593c358fa30ed50da789627
M3.2-E run:    34325585040 — SUCCESS

M3.2-F source: 4a98058357e6cddc8b3cb0aac225171933881479
M3.2-F run:    34326793497 — SUCCESS
workflow:      M3.2 Canonical Context Intelligence
```

The M3.2-F exact-head run passed the A-F targeted gates, compile checks, final-release cache isolation, locked M3.1/M2/M0 regressions, Paper Guidance regression, historical API regression, the complete API test tree and sole-D6/zero-execution authority audit.

## M3.2-F locked architecture

```text
SESSION
  + INDEX
  + SECTOR
  + RELATIVE STRENGTH
  + MARKET REGIME
        |
        v
CANONICAL CONTEXT WORLD
        |
        +--> bounded canonical component receipts
        +--> Stage2 identity / authority validation
        +--> DecisionContext context slots
        |
        v
CURRENT D6 (UNCHANGED AUTHORITY)
```

The composer preserves supporting facts, contradictions, missing/degraded evidence, failure risks, reason codes, warnings, component hashes and source hashes. It does not create a weighted trading score and has no probability/proposal/veto/downgrade/final-band/execution authority.

## Next build — M3.3 Canonical Memory Intelligence

Read before coding:

```text
docs/M3_3_CANONICAL_MEMORY_INTELLIGENCE_ANALYSIS_AND_BUILD_PLAN_2026-09-08.md
docs/M3_INTELLIGENCE_UPGRADE_REFERENCE_2026-09-08.md
docs/CANONICAL_BUILD_STATUS.md
docs/NEXT_BUILD_TARGET.md
```

Required M3.3 direction:

```text
M3.1 canonical price facts
        +
M3.2 canonical context facts
        |
        v
PIT-SAFE FEATURE / EPISODE FREEZER
        |
        v
VERSIONED MEMORY RECORD
        |
        +--> delayed labels only after outcome horizon
        +--> exact feature/corpus/label provenance
        +--> independent episode identity/count
        +--> reliability/session/pattern/9C/analog views
        +--> OOD + drift + decay + quarantine
        +--> replay-safe retrieval / forgetting / retention
        |
        v
CANONICAL MEMORY WORLD
```

Hard laws:

- 50 indicators from one event are not 50 independent observations;
- keep `raw_record_count` separate from `independent_episode_count`;
- no future label leakage;
- no mock analog generation or mock 9-candle histories in production authority paths;
- no fixture outcome production fallback;
- labels are delayed, versioned and provenance-bound;
- retrieval must be PIT-safe and deterministic under replay/restart;
- drift/OOD/decay/quarantine must be explicit and fail closed;
- memory remains evidence, never final-band or execution authority;
- D6 redesign remains deferred to M4.

## Hard boundary

M3.2 is locked. Do not modify its calculations merely to make M3.3 pass. M3.3 must consume the locked M3.1/M3.2 evidence contracts and preserve D6 compatibility until the authorized M4 redesign.
