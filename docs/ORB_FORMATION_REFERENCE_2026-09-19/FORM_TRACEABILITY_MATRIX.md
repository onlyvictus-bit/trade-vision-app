# ORB Intraday Formation Intelligence Traceability Matrix

Source basis: repository source snapshot `docs/ORB_FORMATION_REFERENCE_2026-09-19/SOURCE_INTRADAY_FORMATION_PLAN_2026-09-19.md` (originally supplied as `Pasted markdown(20260919-070133).md`) plus the already-verified ORB/B4 ownership map from the prior reconciliation bundle. This matrix separates source-backed requirements from design placement decisions. It does not claim runtime implementation.

| ID | Source lines | Source-backed requirement | Design placement | Primary docs | Verification idea | Status |
|---|---:|---|---|---|---|---|
| FORM-001 | 100-115 | arbitrary-`as_of`; bind decision/knowledge/source/formation hashes; no future information | B4-F view identity; B14 replay | master, B4, context, M4 | append future data; earlier receipt unchanged | TARGET_REQUIRED |
| FORM-002 | 119-148 | deterministic causal anchors; `anchor_known_at <= decision_as_of` | B4 composition over canonical event owners; B14 attack | master, B4, scope, cognitive | hindsight-anchor attack | TARGET_REQUIRED |
| FORM-003 | 152-183 | source TF / formation TF / scope / horizon / anchor; multi-scale coexistence | B4-F/B6 identity | master, B4, scope, M4, cognitive | time-scale conflict fixture | TARGET_REQUIRED |
| FORM-004 | 188-224 | explicit lifecycle: seed/developing/testing/confirmed/failed/expired/ambiguous | B6 owns state; B4 composes | master, B4, strategy, cognitive | lifecycle transition tests | TARGET_REQUIRED |
| FORM-005 | 228-287 | support/opposition/unknown/expected/failure + next discriminator/confirm/weaken/invalidate/expiry | B4 hypotheses / M4 receipt | master, B4, AFRE, M4 | discriminator completeness test | TARGET_REQUIRED |
| FORM-006 | 291-332 | historical matching uses prefix only; freeze IDs before outcomes | M3.3 baseline / B9 research / B14 attack | master, B4, research, cognitive | outcome-reveal retrieval invariance | TARGET_REQUIRED |
| FORM-007 | 336-419 | facts→relationships→behaviour→structure→optional alias | B4/B6 grammar, versioned | master, B4, strategy, cognitive | alias lineage + grammar version tests | TARGET_REQUIRED |
| FORM-008 | 424-468 | transition history with previous/current state, evidence changes, reason, snapshot hash | B6 transition diary; M3.3 may consume | master, B4, cognitive | deterministic replay of transition sequence | TARGET_REQUIRED |
| FORM-009 | 472-510 | source event IDs / dependency family / derived_from; correlated aliases not independent | B11 evidence lineage / D6 consumption | master, B4, AFRE, M4, cognitive | alias-independence attack | TARGET_REQUIRED |
| FORM-010 | 515-550 | versioned tolerance/geometry policy | B7 parameters; B8 proof; B10 freeze | master, B4, strategy, research | parameter-version and holdout-freeze tests | TARGET_REQUIRED |

## Safety requirements traced separately

| Safety ID | Source lines | Requirement | Placement |
|---|---:|---|---|
| FORM-SAFE-001 | 554-573 | `NO_STABLE_FORMATION` / unresolved is legal | B6/B4/M4 contract |
| FORM-SAFE-002 | 577-615 | incomplete higher-timeframe interpretation can be provisional only, zero authority | B4/B6/B14 |
| FORM-SAFE-003 | 617-648 | screenshots are examples, not canonical market data | research/test-data governance |
| FORM-SAFE-004 | 652-679 | pattern fishing controlled by pre-frozen grammar/search/train/walk-forward/holdout | B8 research proof |

## Adversarial tests

| Test | Source lines | Required invariant |
|---|---:|---|
| T1 future append invariance | 882-907 | fixed-`as_of` hash unchanged |
| T2 hindsight-anchor attack | 912-924 | same anchor after future append |
| T3 historical analogue outcome attack | 928-945 | episode IDs unchanged after outcomes revealed |
| T4 time-scale conflict | 950-963 | 3m/15m/session states coexist without false contradiction |
| T5 alias independence | 968-983 | correlated aliases become one dependency family |
| T6 incomplete-candle | 986-999 | provisional allowed, confirmed forbidden until close |
| T7 pattern-search leakage | 1004-1017 | future changes cannot alter earlier anchor/window/candidates/aliases/parameter version |

## Design placement decisions that are not direct repository facts

These placements are deliberate architecture decisions made to preserve previously verified ownership boundaries; they are **not claims that the runtime already implements them**:

- `OrbIntradayFormationViewV1` is placed as a B4-F composition seam because the existing B4 reconciliation already owns ORB-specific composition and prohibits duplicate calculation ownership.
- B6 is kept as lifecycle/state owner; B7 as geometry/tolerance parameter owner; B8 as proof owner; B9/M3.3 as analogue research; B11 as dependency-aware evidence packaging; B14 as release/adversarial lock.
- Candidate anchor names from the source are treated as registry candidates. A candidate is unavailable unless a canonical owner/provenance exists. This prevents hallucinating a producer for `VWAP_RECLAIM`, `CAUSAL_PIVOT`, or any other candidate.
- Exact thresholds, minimum touch counts, slope rules, compression definitions, retracement limits, timeframe sets and anchor precedence are **not frozen here**. They remain research parameters until the proper stage proves/promotes them.

## Nine-document abstraction map

- **Master plan:** FORM traceability, causal law, stage ownership, safety invariants.
- **B4 full plan:** detailed `OrbIntradayFormationViewV1` identity/receipt, FORM-001…010, B14 attack set.
- **Scope hardening:** exact session/instrument/contract/timeframe/anchor/reference applicability.
- **AFRE future plan:** end-to-end evidence placement and zero-authority integration.
- **Strategy memorandum:** mechanism-before-alias, lifecycle, parameter humility, no hindsight/probability/execution.
- **Context Native V2:** arbitrary-`as_of` context availability and no duplicate calculator.
- **Research Engine:** prefix-safe retrieval, pattern-fishing controls, frozen manifests, A0-A9 progression.
- **M4 Hypothesis Box:** discriminator-complete hypotheses, multi-scale reasoning, dependency-aware confluence.
- **M4 Cognitive:** continuous causal story, transition diary, no-stable-formation, memory and authority discipline.