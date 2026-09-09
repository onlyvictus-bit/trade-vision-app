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
M3.2    Canonical Context Intelligence       IN BUILD
M3.2-A  Context Source Contract              GREEN / LOCKED
M3.2-B  Canonical Session Intelligence       GREEN / LOCKED
M3.2-C  Canonical Index/Sector Context       GREEN / LOCKED
M3.2-D  Canonical Relative Strength          ACTIVE / IN BUILD
M3.2-E  Canonical Market Regime              NOT STARTED
M3.2-F  Context Fusion / Wiring / Parity     NOT STARTED
M3.3    Canonical Memory Intelligence        DESIGN STAGED / RUNTIME NOT ACTIVE
```

## Exact lock evidence

```text
M3.2-B source: 5c944ac0f727767f5494af4c23b9334366860a8d
M3.2-B run:    34321289260 — SUCCESS

M3.2-C source: 64eaa47f5ecf02c18aa3b3422ef1e0cab9b489e6
M3.2-C run:    34323060143 — SUCCESS
workflow:      M3.2 Canonical Context Intelligence
```

M3.2-C passed its dedicated canonical market-context gate, compile checks, locked M3.1/M2/M0 regressions, Paper Guidance, historical API regression, full API tree and final authority/safety audit.

## Active build — M3.2-D Canonical Relative Strength

Implement a causal, versioned relationship layer over the canonical stock/index/sector world.

Required facts:

```text
stock_return
sector_return
index_return
stock_vs_sector
stock_vs_index
sector_vs_index
```

Required laws:

- no arbitrary caller scalar becomes canonical truth;
- each measurement carries window id/version/start/end and exact source hashes;
- only closed/causal observations may contribute;
- compare only compatible proven price bases;
- missing index/sector remains missing, never zero/neutral;
- preserve absolute direction separately from relative leadership;
- preserve index/sector contradictions and idiosyncratic stock behavior;
- deterministic, bounded, replay-safe receipts;
- no probability/proposal/veto/downgrade/final-band/execution authority;
- D6 semantics unchanged.

Required tests include normal leadership/lagging, negative absolute relative-outperformance, conflicts, missing sources, future/unfinished/stale inputs, wrong mapping, mapping transition, basis mismatch, duplicates, source-order independence, replay/restart determinism, bounded payload, performance anti-pathology and zero authority.

## Engineering direction

The later M3.2-E/F layers will consume these facts without flattening them into one trading score. Context must remain suitable for multi-hypothesis reasoning, falsifiers, counterfactual withdrawal, OOD/novelty awareness and explicit insufficient-evidence states.

## Hard boundary

Do not redesign D6 or activate M3.3 runtime before M3.2 is fully locked. After D exact-head GREEN, lock it and proceed automatically to E.
