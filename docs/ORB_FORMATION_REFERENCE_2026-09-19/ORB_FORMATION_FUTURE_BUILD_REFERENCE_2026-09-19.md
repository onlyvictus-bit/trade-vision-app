# ORB Formation Intelligence — Future Build Reference

Date: 2026-09-19
Status: SAVED REFERENCE — DOCUMENTATION RECONCILED / RUNTIME NOT IMPLEMENTED / NOT GREEN
Repository: onlyvictus-bit/trade-vision-app
Verified documentation base: plan/orb-build4-d0-lock-full-plan@9ca03ef6a988e0c16a6d8260c169ba144894f87b

## 1. Why this file exists

This file records the result of a read-only verification of the ORB opening-sequence + continuous intraday formation documentation work.

It preserves the pre-application verification and the final placement decisions. At the verified base below, the nine important ORB/M4 Markdown files were unchanged; the documentation commit containing this reference applies the reconciliation while leaving runtime implementation and GREEN status unresolved.

## 2. Current repository truth

At the pre-application base `9ca03ef6a988e0c16a6d8260c169ba144894f87b`, all nine target Markdown files lacked the new opening-sequence / intraday-formation markers such as:

- `OrbOpeningSequenceViewV1`
- `OrbIntradayFormationViewV1`
- `FORM-001`
- `FORM-010`
- `NO_STABLE_FORMATION`

Therefore:

**Repository state = NOT UPDATED.**

At that pre-application base this was not an "edited but uncommitted" state; the prepared changes existed only in the local reconciliation artifacts/bundle. The documentation commit containing this reference converts that plan into committed documentation.

## 3. Prepared bundle truth

The V2 bundle contains:

- nine combined reconciliation blocks, one for each target Markdown document;
- the new `ORB_INTRADAY_FORMATION_INTELLIGENCE_EXTENSION_PLAN_2026-09-19.md`;
- `FORM_TRACEABILITY_MATRIX.md`;
- `DESIGN_EVIDENCE_LEDGER.md`;
- `JUDGE_REPORT.md`;
- a fail-closed local apply helper.

The master and detailed BUILD-4 blocks contain all `FORM-001` through `FORM-010` contracts. The remaining seven documents receive the subset appropriate to their ownership and purpose rather than duplicating every field everywhere.

## 4. Source-backed design that must not be lost

The future build must preserve these requirements:

1. `OrbIntradayFormationViewV1` is a read-only VIEW / COMPOSER, never a second market-fact calculator.
2. Arbitrary fixed-`as_of` reasoning with `decision_as_of`, `knowledge_cutoff`, source snapshot hash and formation snapshot hash.
3. Deterministic causal anchors with `anchor_known_at <= decision_as_of`.
4. Multi-scale identity: source timeframe, formation timeframe, scope, horizon and anchor.
5. Lifecycle: `SEED`, `DEVELOPING`, `TESTING_BOUNDARY`, `CONFIRMED`, `FAILED`, `EXPIRED`, `AMBIGUOUS`.
6. Discriminator-complete hypotheses: support, opposition, unknown, expected/failure sequences, next discriminator, confirmation, weakening, invalidation and expiry.
7. Prefix-safe historical analogues: freeze historical episode IDs before future outcomes are revealed.
8. Behavioural grammar order: facts -> relationships -> sequence behaviour -> structural formation -> optional human alias.
9. Formation transition diary with deterministic lineage.
10. Dependency-family lineage so multiple aliases from one candle sequence are not counted as independent votes.
11. Versioned geometry/tolerance policies owned by the correct research stages.
12. `NO_STABLE_FORMATION` is a legal answer.
13. Incomplete higher-timeframe formations may be `PROVISIONAL`, never `CONFIRMED` before the required close.
14. Screenshots are examples/test fixtures, not canonical market data.
15. Pattern-search space, grammar, parameters, train/WF periods and untouched holdout must be frozen before holdout evaluation.
16. B14 must attack future append leakage, hindsight anchors, analogue outcome leakage, scale conflicts, alias dependence, incomplete candles and pattern-search leakage.

## 5. Placement review by document

### 5.1 Master plan

Target: `docs/ORB_STAGE_BY_STAGE_ADVANCED_REASONING_BUILD_PLAN.md`

Prepared placement: insert the reconciliation between Section 52 and Section 53 (`Definition of a complete ORB build`).

Verdict: **CORRECT / PREFERRED.**

Reason: the new binding requirements become part of the requirement/audit body before the document defines completion. This is better than appending them after the completion definition.

### 5.2 Detailed BUILD-4 plan

Target: `docs/ORB_BUILD4_CONTEXT_DERIVATIVES_HYPOTHESIS_FULL_BUILD_PLAN_2026-09-17.md`

Prepared placement: append Sections 64 and 65 after existing Section 63 (`Final design principle`).

Verdict: **CONTENT CORRECT; PLACEMENT ACCEPTABLE AS A DATED BINDING EXTENSION.**

Hardening recommended before final commit:

- retain the additive history-preserving placement;
- add an explicit sentence at the start of Section 64/65 saying these later dated sections are the current binding extension when they are more specific than Section 63;
- optionally add a small cross-reference near Section 63 so a reader who stops at "Final design principle" cannot miss Sections 64/65.

Do not rewrite the historical Section 63 just to make the numbering look cleaner.

### 5.3 Stock/commodity scope hardening

Target: `docs/ORB_INTRADAY_STOCK_COMMODITY_SCOPE_AND_FLOW_HARDENING_2026-09-12.md`

Prepared placement: dated scope/identity addendum at the end.

Verdict: **CORRECT.**

It correctly focuses on session/instrument/contract/reference identity, multi-scale applicability, causal anchors, provisional higher-timeframe handling and stock-vs-futures basis.

Traceability hardening recommended:

- use exact contract field spellings `source_timeframe` and `formation_timeframe` in addition to prose forms "source timeframe" / "formation timeframe".

This is a readability/implementation traceability improvement, not a missing design concept.

### 5.4 AFRE canonical future plan

Target: `docs/ORB_AFRE_CANONICAL_FUTURE_BUILD_PLAN_2026-09-10.md`

Prepared placement: dated current-architecture integration note at the end.

Verdict: **CORRECT.**

It belongs here as an evidence-flow/authority integration note, not as a new calculator specification.

### 5.5 Strategy memorandum

Target: `docs/plans/ORB_STRATEGY_MEMORANDUM.md`

Prepared placement: current-architecture reconciliation after the historical strategy/change-log material.

Verdict: **CORRECT.**

It appropriately records mechanism-before-alias, lifecycle, parameter humility, no fake probability, no hindsight and research-only authority without pretending old historical strategy thresholds are newly canonical.

### 5.6 Context Native V2

Target: `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md`

Prepared placement: dated supersession/reconciliation note after the existing standing exclusions.

Verdict: **CORRECT, WITH ONE TRACEABILITY HARDENING.**

The design already enforces context known no later than `decision_as_of` and preserves UNKNOWN/UNAVAILABLE. Before final application, explicitly name the field `knowledge_cutoff` in this block rather than only saying "availability/knowledge timing".

This avoids two future implementations using different timestamp vocabulary for the same contract.

### 5.7 Research Engine plan

Target: `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md`

Prepared placement: current-architecture research addendum after the historical bottom line.

Verdict: **CORRECT, WITH ONE OWNERSHIP HARDENING.**

The addendum correctly covers prefix-safe analogue retrieval, frozen search spaces, walk-forward/untouched holdout, A0-A9 adjacency, missingness and adversarial checks.

Before future coding, add one explicit sentence:

> Research features are derived from the versioned `OrbIntradayFormationViewV1` / B6 transition receipts and canonical M3.3 lineage; the research engine must not rebuild raw-bar market facts or create a second formation truth owner.

This is consistent with the existing architecture and prevents research code from becoming a hidden duplicate calculator.

### 5.8 M4 Hypothesis Box

Target: `docs/M4_HYPOTHESIS_BOX_V2_IMPLEMENTATION_PLAN_2026-09-10.md`

Prepared placement: dated integration note after the historical final implementation target.

Verdict: **CONTENT CORRECT; DATED ADDENDUM PLACEMENT ACCEPTABLE.**

It correctly maps formation receipts into discriminator-complete hypotheses, multi-scale reasoning, dependency-aware confluence, replay/provisional guards, zero raw-probability claims and zero authority.

Hardening recommended:

- add a cross-reference from the historical final-target section to the newer dated integration note so future readers do not stop too early.

### 5.9 M4 Trading Cognitive Architecture

Target: `docs/M4_TRADING_COGNITIVE_ARCHITECTURE_REFERENCE_2026-09-10.md`

Prepared placement: dated cognitive mapping after the historical final merged design principle.

Verdict: **CONTENT CORRECT; DATED ADDENDUM PLACEMENT ACCEPTABLE.**

It correctly describes continuous causal story evolution, transition diary, multi-scale coexistence, behaviour-before-alias, prefix-safe memory, dependency de-duplication and D6 authority.

Hardening recommended:

- add a cross-reference near the historical final merged design principle to the 2026-09-19 extension.

## 6. What is correctly NOT duplicated into every document

Do not copy all FORM-001..010 fields into all nine files.

The correct approach is:

- master = requirement / stage / safety registry;
- BUILD-4 = detailed composition contract and adversarial lock requirements;
- scope = market/timeframe/reference identity;
- AFRE = evidence flow and authority;
- strategy = doctrine and research discipline;
- context = context availability / missingness / no duplicate calculation;
- research = prefix-safe evaluation and anti-pattern-fishing;
- M4 Hypothesis = competing hypothesis semantics;
- M4 Cognitive = continuous reasoning story and memory/authority integration.

Full duplication would create drift and conflicting truth owners.

## 7. Repository work still required before any GREEN claim

1. Apply the prepared reconciliation to a clean checkout at `9ca03ef6...`.
2. Apply the traceability hardenings in Section 5 of this reference before freezing the doc diff.
3. Review the complete ten-document diff.
4. Reconcile BUILD-0 source registration/catalog/manifest/goldens for the new document set.
5. Run documentation/source-lock tests and protected ORB/Decision Spine regressions.
6. Commit only with explicit authorization.
7. Require exact-head CI before declaring source-lock GREEN.
8. Runtime FORM/B4 implementation remains a later build and must pass the fixed-prefix B14 adversarial tests before any implementation-complete claim.

## 8. Non-hallucination / ownership guard

Future builders must not invent:

- a winning timeframe;
- anchor precedence;
- pivot, touch, slope, compression or retracement thresholds;
- pattern acceptance scores;
- STUMPY/DTW adoption;
- probability of success;
- profitability claims;
- missing data as zero/neutral;
- new market-data owners;
- BUY/SELL authority;
- execution authority;
- final-band authority.

Where a candidate anchor or evidence producer has no verified canonical owner, use explicit UNAVAILABLE / NOT_PROVEN semantics until the proper build establishes it.

## 9. Final verification verdict

### Prepared documentation architecture

**VERIFIED WITH MINOR PLACEMENT/TRACEABILITY HARDENINGS.**

The core design is present, stage ownership is coherent, and no major FORM contract is missing from the master/detailed BUILD-4 documentation set.

### Current GitHub repository

**NOT UPDATED.**

The pre-application base did not contain the new B4-OS / intraday-formation reconciliation. The documentation commit containing this reference applies those document changes. BUILD-0 source-lock reconciliation, runtime implementation, and exact-head CI remain future gates.