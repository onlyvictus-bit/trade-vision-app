# Trade Vision / Decision Spine / ORB — Stage-by-Stage Advanced Reasoning Build Plan

**Repository:** `onlyvictus-bit/trade-vision-app`  
**Planning branch:** `m4-d6-orchestration-redesign`  
**Verified planning-head before this document:** `9b950285b62046420bb1ad15d7c9f5b8a8f24f98`  
**Date:** 2026-09-12  
**Document state:** `PLANNED` — architecture/build specification only; no runtime ORB behavior is implemented by this document.

Primary parents:

- `docs/ORB_INTRADAY_STOCK_COMMODITY_SCOPE_AND_FLOW_HARDENING_2026-09-12.md`
- `docs/ORB_AFRE_CANONICAL_FUTURE_BUILD_PLAN_2026-09-10.md`
- `docs/ORB_SIMPLE_FLOW.md`
- `docs/CANONICAL_BUILD_STATUS.md`
- `docs/M4_D6_ORCHESTRATION_MASTER_BUILD_INDEX_2026-09-09.md`

---

## 1. Status and scope

This file is the canonical implementation plan for upgrading the existing ORB system without starting over. It does not authorize implementation out of sequence, does not change the active ORB equations, does not change paper guidance, does not change AFRE/D6 authority, and does not claim any BUILD stage is GREEN.

The target is not a one-score breakout script. It is a causal, replayable, uncertainty-aware research system in which specialized brains answer bounded questions, preserve competing hypotheses, produce auditable evidence, and abstain when facts are unavailable or proof is weak.

The required implementation sequence is `BUILD-0` through `BUILD-14`. Each stage must be implemented, tested, exact-head-CI verified, and locked before the next foundational stage is allowed to depend on it.

---

## 2. Executive objective

Build an ORB research architecture that can answer, with explicit evidence and uncertainty:

- what was known at the decision timestamp;
- what exchange session and contract semantics apply;
- what the previous completed exchange session actually was;
- what observed facts and derived context exist;
- which continuation, reversal, trap, range, event or distortion hypotheses remain plausible;
- which OR duration / confirmation scheme has repeatable unseen-data support;
- what explicit ORB event occurred on closed candles;
- which already-proven parameter set is applicable;
- whether an apparent edge survives costs, walk-forward testing and untouched holdout;
- which historical analogs are genuinely comparable and independent;
- whether a playbook deserves promotion, degradation or retirement;
- what evidence AFRE/D6 should receive **FOR**, **AGAINST**, **UNKNOWN**, **UNAVAILABLE** and **INVALIDATED**;
- whether calibrated ML adds stable unseen-data value;
- how matured paper outcomes feed offline learning without leaking into online reasoning.

The architecture must optimize for correctness first, then deterministic replay, then bounded runtime. Morning runtime must consume frozen research artifacts instead of rerunning multi-year research.

---

## 3. Repository audit method and truth-status vocabulary

Repository truth was inspected on `m4-d6-orchestration-redesign` before this document was written. Claims below use these labels:

- `EXISTS_AND_WIRED` — code exists and is on an active route relevant to the stated capability.
- `EXISTS_BUT_NOT_WIRED` — code exists but is not consumed by the active ORB route being described.
- `PARTIALLY_IMPLEMENTED` — meaningful code exists but does not satisfy the target contract.
- `LEGACY` — behavior is active/preserved for compatibility but must not become the new canonical abstraction.
- `PLANNED_ONLY` — described by documents but not verified as a runtime implementation.
- `MISSING` — no repository implementation was found for the target capability.
- `UNCERTAIN_NEEDS_AUDIT` — evidence is insufficient; BUILD-0 must resolve it before code depends on it.

Planned prose never upgrades a status. A standalone helper never becomes `EXISTS_AND_WIRED` merely because it can be imported.

### 3.1 Current repository truth

| Capability | Truth | Repository evidence | Design consequence |
|---|---|---|---|
| Legacy ORB candidate builder | `EXISTS_AND_WIRED` / `LEGACY` | `apps/api/app/orb/core.py::build_orb_candidate` | Wrap, parity-test, then migrate seams; do not rewrite at once. |
| Closed-candle filtering in legacy ORB | `EXISTS_AND_WIRED` | `orb/core.py::_closed_unique_bars` | Preserve causality behavior in golden regression. |
| NSE-only ORB session contract | `EXISTS_AND_WIRED` / `LEGACY` | `OrbSessionDefinition`; `orb/core.py::_gates`; `hstry_csv.py` | BUILD-2 must generalize session identity without changing current NSE behavior during shadow. |
| Generic commodity session/contract registry | `MISSING` | no verified MCX/generic settlement runtime found | New canonical registry/adapters required before commodity activation. |
| ORB opening context foundation | `EXISTS_BUT_NOT_WIRED` / `PARTIALLY_IMPLEMENTED` | `apps/api/app/orb/context.py` | Reuse formulas only after ownership/parity audit; replace naive day grouping. |
| Prior-session construction in ORB context | `PARTIALLY_IMPLEMENTED` / unsafe for generic commodity | `orb/context.py::daily_from_intraday` uses calendar-day resampling | BUILD-3 owns session-based aggregation. |
| ORB discovery | `EXISTS_AND_WIRED` | `orb/discovery.py::run_orb_discovery` | Extend rather than replace; remove embedded NSE day grouping after session registry exists. |
| ORB proof / train-only selection / holdout / expanding folds | `EXISTS_AND_WIRED` | `orb/proof.py::run_orb_proof` | Strong baseline; harden statistics, candidate reconstruction, embargo and instrument/session identity. |
| Timing research / checkpoints | `EXISTS_AND_WIRED` / narrow target | `orb/timing_research.py` | Expand OR duration × clock × confirmation-TF research; preserve resume/checkpoint pattern. |
| Trendforge-symbol intake into timing research | `EXISTS_AND_WIRED` / not canonical provenance contract | `orb/timing_research.py::resolve_symbols` | BUILD-1 introduces immutable PIT candidate-intake record and reconstruction policy. |
| Adaptive AFRE contracts/controller | `PARTIALLY_IMPLEMENTED`; opt-in/research | `orb/adaptive/contracts.py`, `controller.py` | Reuse bounded hypotheses, evidence IDs and explicit availability ideas; first remove NSE/clock coupling. |
| Adaptive chronological proof | `EXISTS_AND_WIRED` in adaptive research path | `orb/adaptive/research.py::prove_policies` | Reuse lower-bound, unknown-outcome, frozen-universe and chronological proof discipline. |
| Adaptive calibrated frequency model | `PARTIALLY_IMPLEMENTED` / narrow labels | `orb/adaptive/forecasting.py` | Reuse governance pattern only for validated ORB prediction questions in BUILD-12. |
| Adaptive code/proof binding | `EXISTS_AND_WIRED` in adaptive review path | `orb/adaptive/governance.py` | Reuse model/policy/code fingerprint concepts for frozen artifacts. |
| D2 reusable raw-price feature substrate | `EXISTS_AND_WIRED` | `decision_spine/snapshot_feature_kernel.py` | Prefer canonical raw-fact reuse; do not duplicate VWAP/range/volume primitives. |
| M3.2 NSE session intelligence | `EXISTS_AND_WIRED` / NSE-specific | `decision_spine/canonical_session_intelligence.py` | Preserve as NSE adapter/compatibility baseline; generic ORB session registry must sit below/around it. |
| M3.2 canonical context world | `EXISTS_AND_WIRED` | `canonical_context_world.py` | ORB BUILD-4 consumes canonical context receipts, support/contradiction/missingness. |
| M3.3 canonical analog memory | `EXISTS_AND_WIRED` | `canonical_analog_memory.py` | BUILD-9 should adapt/extend rather than invent a second nearest-neighbor framework. |
| Canonical DecisionContext | `EXISTS_AND_WIRED` | `decision_spine/decision_context.py` | ORB evidence should be representable as explicit evidence blocks; no fake-neutral compatibility fields. |
| Stage-2 integrity / neutral-default detection | `EXISTS_AND_WIRED` | `decision_spine/stage2_integrity.py` | Reuse/extend integrity law for ORB receipts. |
| Authority registry | `EXISTS_AND_WIRED` | `decision_spine/authority_registry.py` | `FINAL_CONFLUENCE_ARBITER` remains sole final-band authority; all ORB stages `may_execute=False`. |
| Current ORB paper guidance | `EXISTS_AND_WIRED` | `behavior/orb_guidance.py::run_paper_guidance_with_orb` | Shadow/migrate; current neutral/default placeholders are a known debt. |
| Current D6/final confluence | `EXISTS_AND_WIRED` / M4 redesign planned | `behavior/final_confluence_arbiter.py`; M4 docs | ORB must emit evidence independent of desired final band and align with M4 contracts. |
| Paper lifecycle maturation | `EXISTS_AND_WIRED` | `behavior/orb_paper_lifecycle.py` | Extend outcome contract rather than replace; preserve immutable identity chain and conservative same-bar rule. |
| Paper feedback/reliability | `EXISTS_AND_WIRED` | `behavior/orb_paper_feedback.py` | Keep reduce-only/no-auto-mutation law; extend drift/calibration offline. |
| Generic exchange-aware data-quality calendar | `PARTIALLY_IMPLEMENTED` / NSE-shaped | `behavior/data_quality.py` | Generalize only after BUILD-2; do not copy current 09:15/15:30 constants. |
| D1/PIT guard | `EXISTS_AND_WIRED` | `behavior/point_in_time_guard.py` | Preserve closed-bar invariant; add explicit `available_at` where timestamp+duration is insufficient. |
| Market-structure/liquidity engine | `EXISTS_AND_WIRED` but has legacy missing-volume fallbacks | `behavior/market_structure_liquidity.py` | Consume canonical M3.1 replacements where available; never copy `volume or 0` semantics. |
| 94-output indicator registry | `EXISTS_AND_WIRED` | `behavior/indicator_registry.py` | Reuse canonical registry/output versions and PIT policies; no ORB-private indicator formulas. |
| Exact-head checks at audited planning head | `MISSING evidence` | GitHub check-runs for `9b950...` = 0 | Planning head is not declared GREEN. |

### 3.2 Verified known problems

The audit confirms the following concerns and converts them to mandatory migration requirements:

1. `orb/core.py`, `orb/discovery.py`, `orb/hstry_csv.py`, data-quality helpers and canonical session intelligence contain NSE-shaped clock/session assumptions.
2. No generic commodity exchange/session/contract registry was verified.
3. `orb/context.py::daily_from_intraday` uses calendar-day resampling and cannot define a generic prior commodity session.
4. `orb/context.py` is not the authoritative context package consumed by `build_orb_candidate`/guidance.
5. Rich canonical M3 context exists but current ORB core does not consume the full canonical world.
6. `orb/core.py` and `orb_guidance.py` contain zero/false/0.5-style placeholders, including missing-volume coercions and guidance placeholder evidence.
7. Candidate selection has a live Trendforge symbol seam but no frozen, reconstructable candidate-intake contract proving what was knowable historically.
8. Timing research is narrower than OR-duration × clock × confirmation-TF × regime research.
9. Current signal logic supports basic breakout/reversal but does not model all requested event states as an explicit lifecycle/state machine.
10. Existing proof correctly selects on train before holdout, but needs stronger statistical uncertainty, multiple-testing, candidate-intake reconstruction and optional purge/embargo.
11. Commodity raw-contract/continuous-series/roll/settlement semantics are not verified as implemented.
12. Canonical Decision Spine has stronger missingness/provenance semantics than current ORB guidance and should be reused.
13. D6 final authority is explicit in the authority registry and must remain unchanged.
14. Paper-only safety is explicit throughout current adaptive/guidance/lifecycle code and must never weaken.

---

## 4. External exchange-fact validation policy

Volatile exchange facts are data, not code constants. BUILD-2 must create a versioned source registry whose records include `source_url`, `source_document_id/circular`, `effective_from`, `effective_to`, `retrieved_at`, `content_hash`, `review_status`, and explicit override/exception records.

Authoritative source families verified during this audit:

- NSE Market Timings & Holidays: `https://www.nseindia.com/resources/exchange-communication-holidays`
- NSE consolidated/master circulars: `https://www.nseindia.com/static/resources/consolidated-master-circulars`
- MCX market operations/trade timings: `https://www.mcxindia.com/faq/market-operations`
- MCX trading holidays: `https://www.mcxindia.com/market-operations/trading-surveillance/trading-holidays`
- MCX product pages/contract specifications: product-specific pages under `https://www.mcxindia.com/products/`

Why a registry is mandatory: official MCX material distinguishes commodity categories, session endings, daylight-saving-dependent closing times, and morning/evening holiday treatment. Contract-specification pages are versioned by contract effective period. NSE also publishes holidays, exceptional sessions and circular-driven changes. Therefore no BUILD may scatter current hours, expiry weekdays, settlement rules or contract economics as timeless constants.

---

## 5. Non-negotiable invariants

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true

missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
no_signal != unavailable
no_output != neutral
NOT_APPLICABLE != AVAILABLE
weak evidence != contradictory evidence
conflicting evidence != neutral evidence
future != causal
unfinished != closed
stale != fresh
correlated facts != independent episodes
label observed later != label available now
```

Additional immutable laws:

1. D1 safety/data facts outrank every downstream predictor/reviewer.
2. No incomplete candle has decision authority.
3. Every M2+ fact used at time `t` must be available at or before `t`.
4. Important outputs carry source identity, version, availability, decision/availability timestamps, provenance and snapshot/hash lineage.
5. Same valid data snapshot + calendar/profile/playbook/feature/model/config versions must replay identically.
6. `FINAL_CONFLUENCE_ARBITER` / D6 remains the sole final-band authority.
7. No ORB brain may route an order or silently convert uncertainty to permission.
8. Top-down policy can bound interpretation but may never rewrite bottom-up historical facts.
9. ORB evidence must be independent of the final decision desired by AFRE/D6.
10. Historical labels and paper outcomes enter `OFFLINE_LEARNING` only after maturation.

---

## 6. Architecture principles

### 6.1 Raw fact ownership law

```text
RAW FACT CALCULATED ONCE
        ↓
CANONICAL VERSIONED FACT
        ↓
MANY SPECIALIST BRAINS INTERPRET
        ↓
EVERY INTERPRETATION REFERENCES THE FACT HASH/ID
```

Every canonical calculation has one owner. A consumer may transform a fact into evidence, but may not silently reimplement a near-equivalent formula.

### 6.2 Reasoning modes

- **Deterministic reasoning:** identity, calendars, OHLC aggregation, closed-bar gates, state transitions, hashes, invariants.
- **Statistical reasoning:** sample sufficiency, expectancy distributions, confidence intervals, drift, calibration, regime stability.
- **Historical analog reasoning:** bounded comparable situations with explicit similarity and independence.
- **Evidence-graph reasoning:** support, contradiction, dependency ancestry, correlation families and invalidation.
- **Hypothesis competition:** continuation/fade/trap/range/event/roll/insufficient-evidence can coexist.
- **Counter-evidence search:** every thesis declares observations that would weaken/refute it.
- **Abstention:** `UNKNOWN`, `UNAVAILABLE`, `INSUFFICIENT_HISTORY`, `CONFLICTED`, `NO_SETUP` are valid outputs.
- **Calibrated ML:** optional evidence after deterministic labels/proof are stable; never authority.

### 6.3 Structured self-critique artifact

Persist bounded auditable fields, never private reasoning transcripts:

```text
observations
assumptions
hypotheses
supporting_evidence
contradicting_evidence
alternative_explanations
unknowns
uncertainty_dimensions
invalidation_conditions
output_state
reason_codes
unresolved_questions
```

### 6.4 Core engineering decisions

| Problem | Evidence | Options considered | Chosen design | Trade-off / failure protection |
|---|---|---|---|---|
| Existing ORB works but is NSE-shaped | core/discovery/HSTRY hard-code session | rewrite; fork; strangler | `WRAP → PROVE → SHADOW → MIGRATE` | temporarily more adapters, but rollback is safe. |
| Commodity rules change | official exchange calendars/specs | constants; config file; versioned registry | source-dated versioned registry | registry operations required, but replay becomes truthful. |
| Missing values become neutral in legacy seams | `volume or 0`, guidance 0/0.5/False | tolerate; patch locally; canonical availability | typed epistemic state | larger contracts, lower false certainty. |
| Evidence correlation inflates conviction | indicator descendants share price/volume ancestry | flat vote; manual weights; dependency graph | ancestry + family-aware aggregation | extra metadata, prevents pseudo-confirmation. |
| Research can overfit timing/parameters | combinatorial search | choose best score; unrestricted ML; registered bounded search | train-only selection + WF + untouched holdout + multiplicity controls | may yield no winner, which is intended. |
| Historical similarity can be sparse | one-neighbor confidence | nearest neighbor only; global average; hybrid | deterministic buckets + canonical analog memory + sparse abstention | less frequent conclusions, more honest uncertainty. |
| Morning runtime must be fast | research matrix can be large | recompute; cache everything; frozen artifacts | precompute proof/playbooks, runtime reads only active artifacts | requires artifact lifecycle/versioning. |

---

## 7. Existing ORB system map

### 7.1 Current research path

```text
HSTRY CSV / supplied CandleSeries
        ↓
orb/hstry_csv.py
        ↓
orb/timing_research.py
        ↓
orb/discovery.py
        ↓
orb/core.py
        ↓
orb/proof.py
        ↓
orb_playbooks.json / promoted playbook
```

### 7.2 Current guidance path

```text
PaperGuidance request
        ↓
D1 checks + D2 closed snapshot
        ↓
active ORB playbook lookup
        ↓
orb/core.py
        ↓
legacy/current context receipts
        ↓
final_confluence_arbiter.py
        ↓
WAIT / WATCH / PAPER-CANDIDATE-compatible paper guidance
        ↓
human paper approval
        ↓
simulated_paper_ledger
        ↓
orb_paper_lifecycle
        ↓
orb_paper_feedback
```

### 7.3 Existing engines to preserve and evolve

`hstry_csv`, `context`, `timing_research`, `core`, `discovery`, `proof`, `adaptive/*`, `orb_guidance`, `simulated_paper_ledger`, `orb_paper_lifecycle`, `orb_paper_feedback`, canonical M3 price/context/memory systems, stage-2 integrity, DecisionContext, authority registry and D6.

---

## 8. Target ORB system map and full data lineage

Legend: `[R]` runtime, `[O]` offline research, `[F]` feedback, `[A]` authority edge, `[E]` evidence-only.

```text
USER / TRENDFORGE SHORTLIST [R]
        ↓ E
CANDIDATE INTAKE + PIT PROVENANCE [R]
        ↓ E
INSTRUMENT / CONTRACT / SESSION PROFILE [R]
        ↓ E
D1 RAW FACTS [R]
        ↓ E
D2 CLOSED-CANDLE CAUSAL SNAPSHOT [R]
        ↓ E
PREVIOUS COMPLETED EXCHANGE SESSION [R]
        ↓ E
CANONICAL ORB CONTEXT + HYPOTHESES [R]
        ↓ E
ACTIVE PROVEN TIMING / TF ARTIFACT [R] ← OR TIMING RESEARCH [O]
        ↓ E
EXPLICIT ORB SIGNAL STATE MACHINE [R]
        ↓ E
PROOF-BACKED PARAMETER SELECTION [R] ← PARAMETER RESEARCH [O]
        ↓ E
DISCOVERY / WALK-FORWARD / HOLDOUT PROOF [O]
        ↓ E
COMBINATION + HISTORICAL ANALOG MEMORY [R/O]
        ↓ E
FROZEN VERSIONED PLAYBOOK [R] ← PROMOTION [O]
        ↓ E
CALIBRATED ML EVIDENCE WHEN PROVEN [R] ← MODEL TRAIN/CALIBRATE/TEST [O]
        ↓ E
ORB EVIDENCE PACKAGE: FOR + AGAINST + UNKNOWN + INVALIDATION [R]
        ↓ E
AFRE MULTI-EVIDENCE REASONING [R]
        ↓ A
D6 FINAL GUIDANCE AUTHORITY [R]
        ↓ A
WAIT / WATCH / PAPER-CANDIDATE
        ↓ A
HUMAN PAPER APPROVAL
        ↓ F
MATURED OUTCOME ONLY
        ↓ F
OFFLINE LEARNING / DRIFT / CHALLENGER RESEARCH [O]
```

No feedback edge is allowed to reach the immutable evidence package that caused the original decision.

---

## 9. Stage dependency graph

```text
BUILD-0 Baseline Lock
   ↓
BUILD-1 Candidate Intake
   ↓
BUILD-2 Instrument / Session / Contract Identity
   ↓
BUILD-3 Previous Completed Session
   ↓
BUILD-4 Canonical ORB Context
   ↓
BUILD-5 OR Duration / Clock / Confirmation Research
   ↓
BUILD-6 Explicit Signal State Machine
   ↓
BUILD-7 Parameter / Invalidation / Paper-Risk Research
   ↓
BUILD-8 Discovery / WF / Holdout Proof
   ↓
BUILD-9 Combination / Analog / Historical Memory
   ↓
BUILD-10 Playbook Compiler / Promotion
   ↓
BUILD-11 ORB Evidence Package + AFRE/D6 Integration
   ↓
BUILD-12 Calibrated ML / Champion-Challenger
   ↓
BUILD-13 Paper Outcome / Feedback
   ↓
BUILD-14 Adversarial Replay / CI / Shadow Lock
```

BUILD-12 may remain `PLANNED` or `REJECTED_AS_NO_INCREMENTAL_VALUE` without blocking a deterministic production-quality ORB evidence system. It must never be implemented merely to satisfy a feature checklist.

---

# 10. BUILD-0 — Baseline / Invariant / Regression Lock

### A. Stage purpose
Freeze exact repository/runtime truth so every later migration can prove `NEW_CAPABILITY_ADDED` without silently breaking valid behavior.

### B. Problem being solved
Current ORB behavior spans legacy core, adaptive modules, Decision Spine adapters, proof stores and paper feedback; without a machine-readable baseline, later refactors can confuse intentional behavior with legacy accidents.

### C. Questions this reasoning engine must answer
What exists? Which branch/SHA? Which public contracts, stores, routes and tests are active? Which behaviors are safety invariants? Which behaviors are legacy compatibility? Which outputs must match exactly during shadow migration?

### D. Questions it is forbidden to answer
It must not classify a market setup, select a side, rank a playbook, infer profitability or change a runtime parameter.

### E. Current repository truth
Reuse `orb/core.py`, `discovery.py`, `proof.py`, `timing_research.py`, `orb_guidance.py`, paper lifecycle/feedback tests, `decision_spine/*`, authority registry and existing workflows. Current planning head has no attached check-run evidence; therefore BUILD-0 begins `PLANNED`, never GREEN by inference.

### F. Upstream inputs
Repository commit graph; source files; schema/model definitions; persisted fixture formats; workflows; test inventory. Inputs are immutable Git blobs/SHA identities. Missing source/test evidence => `UNCERTAIN_NEEDS_AUDIT`, not “pass”.

### G. Downstream consumers
Every BUILD stage, migration parity tests, rollback decisions, CI gates and release documentation.

### H. Upstream/downstream failure propagation
Missing file/test/workflow evidence blocks a claim about baseline coverage. Stale docs are evidence only; source + tests + exact-head CI outrank prose.

### I. Canonical output contract
`OrbBaselineManifestV1`: repository SHA, file hashes, public function/schema inventory, safety flags, golden-scenario hashes, active playbook fixture identities, store schema versions, test/workflow inventory, performance observations, unresolved classifications.

### J. State machine
`DISCOVERED → VERIFIED → GOLDEN_CAPTURED → CI_VERIFIED → LOCKED`; any source drift returns to `DISCOVERED`. No direct `DISCOVERED → LOCKED`.

### K. Calculations
Only content hashes, deterministic fixture hashes, elapsed runtime measurements and output diffs. Hash owner: baseline module/test utility; SHA-256 canonical JSON with sorted keys and `allow_nan=False`.

### L. Reasoning architecture
Facts = repository/source/test evidence. Hypotheses = “intentional compatibility” vs “legacy defect”. Every claimed defect must cite code/test evidence; ambiguous behavior remains unresolved.

### M. Decision/output semantics
`MATCH`, `INTENTIONAL_CHANGE`, `REGRESSION`, `UNCLASSIFIED`. A future stage cannot suppress a `REGRESSION` by relabeling it `MATCH`.

### N. Dynamic behavior
Manifest SHA/file hashes change with repository changes. Safety/authority laws do not.

### O. Failure modes
Wrong branch, stale checkout, fixtures generated from future code, nondeterministic IDs/timestamps, hidden local config, omitted stores, performance measurement on unrealistic toy data.

### P. False certainty prevention
Record absent CI as absent; record uninspected surfaces as `UNCERTAIN_NEEDS_AUDIT`; distinguish “test exists” from “test passed at exact head”.

### Q. Code-change map
Expected later: a small test/manifest utility under existing ORB/test conventions, golden fixtures under current fixture conventions, documentation update. Do not create a new framework merely for the manifest.

### R. Backward compatibility
Capture normal bullish, bearish mirror, no setup, insufficient data, failed break/trap-compatible fixture, deterministic replay, NSE grouping, active-playbook lookup and D6 authority before changing any logic.

### S. Tests
Unit manifest hashing; deterministic serialization; golden replay; branch/SHA binding; authority manifest; current ORB test suite; full API regression; performance baseline.

### T. GREEN acceptance gate
Exact head recorded; baseline manifest committed; all golden fixtures deterministic; targeted + existing ORB + Decision Spine + authority tests pass; exact-head CI succeeds; no unexplained golden diff.

### U. Rollback plan
Delete baseline additions only; runtime is untouched.

### V. Observability
Structured baseline report with SHA, test counts, file hashes and diff reasons. No credentials/environment secrets.

### W. Performance budget
Baseline capture should be O(number of selected files + fixtures); expensive performance fixtures are separately benchmarked and cached by SHA.

### X. Security/safety
Manifest must prove all execution flags false and D6 sole final authority.

### Y. Unresolved uncertainties
Exact current CI workflow expected for docs-only planning head; persisted local datasets unavailable to repository audit; BUILD-0 must resolve environment-specific fixtures before GREEN.

### Z. Implementation checklist
1. Re-verify branch/head. 2. Enumerate runtime/public contracts/stores. 3. Enumerate tests/workflows. 4. Classify capabilities. 5. Capture safety/authority snapshot. 6. Build golden fixtures. 7. Capture performance baseline. 8. Run targeted/full/authority tests. 9. Run exact-head CI. 10. Lock manifest.

---

# 11. BUILD-1 — Candidate Intake + Provenance Brain

### A. Stage purpose
Turn user/Trendforge/manual morning selections into immutable, reconstructable, PIT-safe research candidates.

### B. Problem being solved
`timing_research.resolve_symbols` can consume Trendforge-ready symbols, but symbol presence alone does not encode why/when/how the candidate became eligible or whether historical reconstruction used the same selection rule.

### C. Questions this reasoning engine must answer
What instrument was selected? By whom/source? Why? Which observed metrics supported selection? When did each metric become available? Is identity resolvable? Is selection data suspect/stale? Does historical testing require candidate-filter reconstruction?

### D. Questions it is forbidden to answer
Candidate direction, trade side, ORB success probability, entry/stop/target, final guidance.

### E. Current repository truth
`timing_research.py::resolve_symbols` is a useful existing seam; candidate reasons/provenance contract is not canonical. Trendforge integration is therefore `PARTIALLY_IMPLEMENTED` for this target.

### F. Upstream inputs
User selection, Trendforge intake record, registered premarket feed/event source. Each input: source ID/version, instrument key, observed value+units, observation time, `available_at`, freshness, source hash, selection-rule version, required/optional flag. Missing required identity => reject; missing optional metric => explicit unavailable.

### G. Downstream consumers
BUILD-2 identity, BUILD-4 context (candidate reason as context only), BUILD-8 historical selection reconstruction, BUILD-9 analog feature, BUILD-11 provenance.

### H. Upstream/downstream failure propagation
`MISSING/UNKNOWN/UNAVAILABLE/STALE/SUSPECT/ERROR` remain states. A stale premarket-volume metric cannot become “normal volume”. `NOT_APPLICABLE` is valid only if the selection rule does not require that field.

### I. Canonical output contract
`OrbCandidateIntakeV1`: `candidate_id`, `instrument_key`, `selection_reason[]`, `source_type`, `source_record_id`, `selection_rule_version`, `observed_facts[]`, `selected_at`, `decision_cutoff`, `available_at_max`, `availability`, `quality`, `provenance[]`, `source_hashes[]`, `candidate_hash`, `historical_reconstruction_policy_id`.

### J. State machine
`RECEIVED → IDENTITY_PENDING → VALIDATED → ELIGIBLE_FOR_STUDY`; alternatives `REJECTED_INVALID_IDENTITY`, `QUARANTINED_SUSPECT`, `UNAVAILABLE_REQUIRED_FACT`. No candidate state equals LONG/SHORT.

### K. Calculations
Only selection-rule evaluation owned by candidate intake; canonical gap/volume calculations are referenced by calculation IDs, not recomputed. Boolean rule truth must support `TRUE/FALSE/UNKNOWN/NOT_APPLICABLE`, not Python false defaults.

### L. Reasoning architecture
Hypotheses concern input validity/selection bias, not market direction. For = facts proving the selection condition existed. Against = stale/suspect/missing source. Invalidation = source correction, late timestamp, identity mismatch.

### M. Decision/output semantics
`ELIGIBLE_FOR_STUDY` means “ORB may analyze this instrument”; it never means favorable or tradeable.

### N. Dynamic behavior
Registered reasons may vary by instrument/source/time; provenance and PIT laws never change.

### O. Failure modes
Look-ahead premarket metrics, manual labels added later, symbol alias collision, duplicate candidate from multiple sources, unversioned selection rule, historical universe survivorship, post-open fact used to explain pre-open selection.

### P. False certainty prevention
Persist every unknown and source timestamp; historical study must either reconstruct the intake rule or mark results `SELECTION_BIAS_UNRESOLVED`.

### Q. Code-change map
Extend existing models/contracts; add candidate-intake module near ORB contracts; wrap `resolve_symbols`; adapters for Trendforge/manual sources; tests. Do not duplicate Trendforge storage.

### R. Backward compatibility
Legacy symbol-list requests are wrapped as `MANUAL_RESEARCH_CANDIDATE` with explicit source/time; current behavior stays shadowed until parity.

### S. Tests
Reason enums, duplicate merge, timestamp causality, stale/suspect source, missing metric, manual candidate, Trendforge adapter, historical reconstruction, deterministic hash, no direction implication, authority test.

### T. GREEN acceptance gate
All current candidate paths emit canonical intake in shadow; historical selection reconstruction policy exists; no post-cutoff fact enters intake; old symbol list parity passes; exact-head CI GREEN.

### U. Rollback plan
Disable canonical intake adapter and route legacy symbol list unchanged; no store migration destructive step.

### V. Observability
Candidate ID, source, reason codes, availability counts, latency, reconstruction status; never raw secrets.

### W. Performance budget
O(candidate facts); deduplicate by `(instrument_key, selection_cutoff, selection_rule_version)`; batch source reads.

### X. Security/safety
Candidate intake cannot create paper tickets, proof authority or execution capability.

### Y. Unresolved uncertainties
Exact Trendforge schema/version and historical retention depth must be frozen in BUILD-0 before implementation.

### Z. Implementation checklist
Contract/enums → source adapters → PIT validation → dedupe/hash → historical reconstruction contract → shadow wrapper → unit/adversarial tests → regression → exact-head CI → lock.

---

# 12. BUILD-2 — Instrument / Session / Contract Identity Brain

### A. Stage purpose
Provide authoritative, versioned instrument/session/contract semantics before any generic ORB calculation groups bars.

### B. Problem being solved
Current ORB, HSTRY, data-quality and canonical session code embed NSE/IST/current cash-session assumptions. Commodity contracts require category/session, expiry, roll, settlement and economics that cannot be inferred from symbol text.

### C. Questions this reasoning engine must answer
What instrument/venue/contract is this? Which timezone/calendar/session/anchor/breaks apply? Which tick/lot/economics and price basis apply? Is this raw contract or continuous series? What expiry/roll/settlement metadata was effective at the decision time? Which benchmark/context families are applicable?

### D. Questions it is forbidden to answer
Whether price should rise/fall, which OR timing wins, signal quality or final guidance.

### E. Current repository truth
`OrbSessionDefinition`, `hstry_csv`, `canonical_session_intelligence`, adaptive `clock_ns/day_of` are NSE-shaped. A generic MCX/session/settlement registry was not verified.

### F. Upstream inputs
Instrument master, official exchange calendar/circular/specification records, source series metadata. Required fields have source/effective dates/hash and `available_at`. Unknown contract identity is a blocker for commodity research.

### G. Downstream consumers
BUILD-3 through BUILD-14; D1/data-quality; D2 snapshot construction adapters; playbook eligibility; replay keys.

### H. Upstream/downstream failure propagation
Unknown calendar/profile => `UNAVAILABLE` or fail closed. Stale profile cannot silently reuse last year. `NOT_APPLICABLE` is explicit for stock-only/commodity-only fields.

### I. Canonical output contract
`OrbInstrumentProfileV1`, `OrbSessionProfileV1`, `OrbContractProfileV1`, plus immutable `OrbMarketIdentityV1` that binds profile hashes to decision time.

Required profile fields: venue, market segment, timezone, calendar ID/version, session ID family, open anchor, intervals/breaks, close/settlement semantics, tick size schedule, currency, multiplier/lot, expiry identity, roll policy ID, continuous-series policy, price-limit/halts metadata where available, applicable context families, source citations/hashes/effective interval.

### J. State machine
Registry record: `DRAFT → VERIFIED → ACTIVE → SUPERSEDED → RETIRED`; decision binding: `RESOLVED`, `UNAVAILABLE`, `AMBIGUOUS`, `STALE`, `ERROR`.

### K. Calculations
Session-relative offset = elapsed tradable time from registered opening anchor, excluding registered breaks. Contract days-to-expiry = calendar/session-count according to registered rule. No expiry weekday is hard-coded outside the registry. Time conversions use timezone-aware datetimes/zoneinfo.

### L. Reasoning architecture
Competing identity candidates are allowed only during resolution; ambiguity blocks downstream signal authority. Provenance includes official rule source.

### M. Decision/output semantics
`RESOLVED` means one effective profile set applies to this decision timestamp; it does not imply market data quality or setup validity.

### N. Dynamic behavior
Sessions, holidays, DST-linked hours, contract specs, expiry/settlement can change by effective version. Safety and replay binding remain invariant.

### O. Failure modes
Wrong symbol alias, expired contract reused, continuous series mistaken for raw, DST close drift, partial holiday/session, emergency exchange circular, wrong timezone, roll mapping after the fact, tick-size change.

### P. False certainty prevention
No fallback `NSE 09:15-15:30` for unknown instruments; no symbol-name guess for contract metadata; ambiguous identity blocks.

### Q. Code-change map
New registry/profile contracts under repository-native ORB/market metadata conventions; adapters around current `OrbSessionDefinition` and `canonical_session_intelligence`; calendar provider fixtures; no runtime behavior switch until shadow parity.

### R. Backward compatibility
Create an `NSE_CASH_REGULAR_V1` profile whose normal-session output reproduces current valid NSE grouping exactly. Legacy session object remains adapter input until migration.

### S. Tests
NSE parity, holidays, special/shortened session fixture, MCX category profile fixtures, DST-linked timing change fixture, cross-date session, break, contract mismatch, raw vs continuous, expiry/roll, stale registry, replay hash, authority.

### T. GREEN acceptance gate
NSE golden parity exact; official-source registry fixtures versioned; commodity test profiles resolve without code constants; ambiguity fails closed; exact-head CI GREEN.

### U. Rollback plan
Keep legacy session adapter as active selector; canonical profiles remain shadow artifacts.

### V. Observability
Resolved profile/version/source/effective date, lookup latency, exception/override ID; no noisy per-bar clock logs.

### W. Performance budget
Registry lookup O(log n) or keyed O(1); cache immutable records by `(venue, product, effective_date, contract)`; no external network fetch in morning decision loop.

### X. Security/safety
Registry ingestion requires review/content hash; remote rule changes cannot self-activate without validation.

### Y. Unresolved uncertainties
Exact commodity universe, data vendor symbol mapping, settlement fields and continuous-series adjustment policy must be chosen before commodity activation.

### Z. Implementation checklist
Schema → official-source fixtures → registry validator → NSE adapter/parity → commodity fixture adapters → session-relative clock → replay hash → shadow binding → tests → CI → lock.

---

# 13. BUILD-3 — Previous Completed Session Reconstruction Brain

### A. Stage purpose
Construct the exact prior completed exchange session used by every downstream ORB calculation.

### B. Problem being solved
Calendar-day resampling is unsafe for generic sessions; the current context helper can turn midnight grouping into a false prior session.

### C. Questions this reasoning engine must answer
Which bars belong to the prior registered session? Was the session complete? Which close/settlement basis is required? Are bars missing/duplicated/bad? Was a corporate action/roll adjustment relevant? Can OHLCV be trusted?

### D. Questions it is forbidden to answer
Whether prior candle is bullish/bearish evidence for a trade; BUILD-4 interprets it.

### E. Current repository truth
`orb/context.py::daily_from_intraday` is reusable only as a legacy equity reference, not generic ownership. D2 feature kernel already validates raw bar order/geometry and preserves missing volume.

### F. Upstream inputs
Resolved BUILD-2 identity, historical D1/D2-approved bars, data-quality receipt, corporate-action source where applicable, contract/roll/settlement source where applicable. Every bar must have event timestamp, close/availability timestamp, source/revision and price basis.

### G. Downstream consumers
BUILD-4 context, gap/CPR/PDH/PDL/PDC calculations, timing research stratification, analog memory, playbook eligibility.

### H. Upstream/downstream failure propagation
Incomplete prior session => `INCOMPLETE`; missing volume makes volume-derived fields unavailable but not price OHLC; suspect corporate action/roll can quarantine normalized-return/gap calculations without deleting raw OHLC.

### I. Canonical output contract
`OrbCompletedSessionV1`: session/profile/contract IDs, start/end, expected/observed coverage, OHLC, volume availability/aggregate, close and settlement with separate availability, source bar hashes, action/roll adjustments, quality state, reason codes, session hash.

### J. State machine
`PENDING → COMPLETE_TRUSTED`; alternatives `COMPLETE_DEGRADED`, `INCOMPLETE`, `QUARANTINED`, `UNAVAILABLE`, `ERROR`. Completed session never becomes “complete” merely because a day boundary passed.

### K. Calculations
OHLC = first open/max high/min low/last close over exactly registered session bars; volume = sum only if required volume observations are available according to volume policy, else unavailable; coverage = observed expected grid intervals / expected intervals excluding registered breaks; settlement remains separate, never substituted by close without explicit profile rule.

### L. Reasoning architecture
Facts only: coverage support, anomaly contradictions, missing/suspect flags. Hypothesis “session complete” has explicit required evidence and invalidation.

### M. Decision/output semantics
`COMPLETE_TRUSTED` allows price-derived downstream facts; `COMPLETE_DEGRADED` carries permitted subset; `INCOMPLETE/QUARANTINED` blocks facts requiring full session.

### N. Dynamic behavior
Expected bars depend on session profile/timeframe/breaks; settlement/corporate-action/roll applicability depends on instrument. Aggregation law remains invariant.

### O. Failure modes
Cross-midnight grouping, wrong contract, duplicate revision, missing open/close bars, partial holiday, halt, split/bonus, roll jump, settlement arriving later than close, bad tick dominating high/low.

### P. False certainty prevention
Keep raw vs adjusted basis explicit; do not “repair” missing bars silently; maintain `expected_bar_count`, `observed_bar_count`, missing intervals and quality reason codes.

### Q. Code-change map
New session aggregator using BUILD-2 profiles; adapters from D2/kernel; deprecate `daily_from_intraday` for canonical use only after parity tests; add corporate-action/roll hooks, not embedded provider fetches.

### R. Backward compatibility
For normal NSE sessions and clean data, previous OHLC must equal legacy expected prior-day candle fixtures.

### S. Tests
Previous Friday/Monday, holiday, missing bar, duplicate, bad OHLC, missing volume, split suspect, cross-date commodity session, break, raw/continuous mismatch, settlement late, roll, deterministic hash.

### T. GREEN acceptance gate
No canonical prior-session path uses naive calendar resampling; NSE parity passes; commodity session fixtures pass; missingness preserved; replay/authority/CI GREEN.

### U. Rollback plan
Legacy context retains old aggregator behind compatibility route while canonical consumer is disabled.

### V. Observability
Session ID/hash, coverage counts, source revisions, adjustment/roll IDs, degraded reasons.

### W. Performance budget
Single ordered pass O(n) per session; cache by `(session_profile_hash, contract_id, source_snapshot_hash)`.

### X. Security/safety
No provider correction can rewrite persisted prior-session artifact without new revision/hash.

### Y. Unresolved uncertainties
Vendor settlement timestamps and historical corporate-action adjustment policy require explicit source contracts.

### Z. Implementation checklist
Aggregator contract → expected-grid builder → quality gates → raw/adjusted basis → settlement/roll hooks → NSE parity → commodity fixtures → hash/replay → shadow → CI → lock.

---

# 14. BUILD-4 — Canonical ORB Context Reasoning Brain

### A. Stage purpose
Describe the opening market situation on multiple explicit axes without collapsing context into a trade score.

### B. Problem being solved
Rich canonical price/context/memory capabilities exist, but current ORB uses only a narrow subset and guidance still contains neutral/default placeholders.

### C. Questions this reasoning engine must answer
What is trend/volatility/value/volume/structure/location/benchmark/sector/event/derivatives/roll/data-quality context? Which continuation/fade/trap/range/event hypotheses are supported, contradicted or unknown? What would invalidate each interpretation?

### D. Questions it is forbidden to answer
Final trade/guidance band, execution, ad-hoc entry/stop/target, or probability without calibrated proof.

### E. Current repository truth
Reuse D2 feature kernel, canonical M3.1/M3.2 worlds, indicator registry, level/structure intelligence, DecisionContext and stage-2 integrity. `orb/context.py` is partial/standalone and must not become a second canonical calculator library.

### F. Upstream inputs
BUILD-1 candidate, BUILD-2 profiles, BUILD-3 prior session, D2 kernel, canonical M3 price/context receipts, event/derivatives sources with availability, freshness and provenance. Each input declares required/optional/applicability.

### G. Downstream consumers
BUILD-5 stratification, BUILD-6 signal interpretation, BUILD-7 parameters, BUILD-9 analogs, BUILD-10 playbook rules, BUILD-11 evidence package, optional BUILD-12 features.

### H. Upstream/downstream failure propagation
Unavailable sector for commodity => `NOT_APPLICABLE`; missing benchmark => `UNAVAILABLE`, not neutral alignment; missing volume disables RVOL/VWAP volume-dependent facts while price-only facts remain usable.

### I. Canonical output contract
`OrbContextWorldV1`: identity/hash; axis states (`trend_support`, `trend_conflict`, `volatility_state`, `compression_expansion`, `location_state`, `value_acceptance`, `volume_quality`, `structure_quality`, `trap_risk`, `event_risk`, `benchmark_alignment`, `sector_alignment`, `roll_distortion`, `data_quality`); typed facts/evidence; hypotheses; reasons_for/against; unknowns; blockers; invalidations; dependency IDs; context hash.

### J. State machine
Context world availability: `AVAILABLE`, `DEGRADED`, `CONFLICTED`, `INSUFFICIENT_EVIDENCE`, `UNAVAILABLE`, `ERROR`; individual hypotheses: `POSSIBLE`, `SUPPORTED`, `WEAKENED`, `CONTRADICTED`, `INVALIDATED`, `UNOBSERVABLE`.

### K. Calculations
Consume Calculation Registry owners: prior levels, gap, ATR, CPR, VWAP/bands, BB, RVOL, canonical structure/levels. Any new calculation is registered once with formula/units/warm-up/PIT. No hidden `context_score`.

### L. Reasoning architecture
Default hypothesis set where applicable: H1 continuation, H2 failed-break/reversal, H3 gap fade, H4 range/chop, H5 event distortion, H6 liquidity/roll distortion, H7 insufficient evidence. Evidence ancestry and correlation families are mandatory.

### M. Decision/output semantics
Axis states are descriptive, not permissions. `CONFLICTED` means material support exists for incompatible hypotheses; it is not numerical neutral.

### N. Dynamic behavior
Applicable axes vary by instrument/session; thresholds may come from frozen playbook/proof; epistemic rules and raw facts remain invariant.

### O. Failure modes
Double counting EMA/MACD/trend, missing volume coerced to zero, sector context applied to commodity, event feed late, stale levels, forward-confirmed pivot used early, continuous-futures adjustment leak.

### P. False certainty prevention
Confidence is a vector: data quality, evidence strength, sample support, contradiction, freshness and regime stability. No free-form 0–100 confidence.

### Q. Code-change map
New ORB context adapter/composer consuming canonical M3 outputs; reuse `snapshot_feature_kernel`, canonical context/level/indicator/memory contracts; deprecate duplicate `orb/context.py` calculations only after parity.

### R. Backward compatibility
Shadow current ORB context and guidance; current NSE signal remains unchanged until BUILD-11 migration gate.

### S. Tests
Axis semantics, missing volume, missing benchmark, N/A sector, contradictions, evidence ancestry, stale facts, hypothesis invalidation, symmetry, replay, snapshot mismatch, performance, zero authority.

### T. GREEN acceptance gate
No fake-neutral fallback in canonical ORB context; every fact lineage traceable; correlated evidence identified; required M3 parity/regressions and exact-head CI pass.

### U. Rollback plan
Disable composer; retain current ORB core/guidance route.

### V. Observability
Counts by availability/family/hypothesis, dependency IDs, contradiction/invalidation reason codes; bounded receipt size.

### W. Performance budget
Consume each canonical world once; no repeated indicator computation; memoize by D2/context-world hashes.

### X. Security/safety
All context components remain evidence-only/non-executing; external AI explanations cannot create facts.

### Y. Unresolved uncertainties
Which event/derivatives feeds qualify as authoritative and which canonical M3 level calculations already cover every requested ORB level must be finalized before implementation.

### Z. Implementation checklist
Input adapters → axis contracts → dependency map → hypotheses → counter-evidence/invalidation → explicit missingness → shadow composer → tests → regression/CI → lock.

---

# 15. BUILD-5 — OR Duration / Clock / Confirmation-TF Research Brain

### A. Stage purpose
Discover stable opening-range and confirmation timing per instrument/session/context instead of imposing ORB-15 globally.

### B. Problem being solved
Current timing research evaluates a narrower set of clock windows and does not model the full OR-duration × confirmation-TF target.

### C. Questions this reasoning engine must answer
Which OR duration/confirmation TF is stable? Does shorter OR add false breaks? Does longer OR delay too much? Is improvement statistically meaningful? Does choice vary by regime/instrument/roll state? Is evidence sufficient to choose any winner?

### D. Questions it is forbidden to answer
Today’s live best parameter by peeking at later bars; final guidance; model fitting on holdout.

### E. Current repository truth
`timing_research.py` has checkpoint/resume and `INSUFFICIENT_DATA` / `NO_SIGNIFICANT_DIFFERENCE`; `discovery.py` explores bars/windows. Preserve these strengths.

### F. Upstream inputs
PIT-reconstructed BUILD-1 universe, BUILD-2 session profiles, BUILD-3 completed histories, BUILD-4 context buckets, source granularity, cost model, registered candidate matrix. Every research run binds dataset/calendar/profile/code versions.

### G. Downstream consumers
BUILD-6 signal definition, BUILD-8 proof, BUILD-10 playbook compiler.

### H. Upstream/downstream failure propagation
Insufficient 1m history => unsupported 1m/3m confirmation candidates, not resampled fiction. Incomplete session => excluded/unknown according to declared policy. Roll-distorted commodity periods are explicit strata.

### I. Canonical output contract
`OrbTimingResearchArtifactV1`: registered matrix; per-cell metrics; context strata; selection procedure; multiplicity metadata; confidence intervals; stability; train/validation/holdout identities; statuses `SUPPORTED`, `MULTIPLE_VALID_WINDOWS`, `NO_SIGNIFICANT_DIFFERENCE`, `CONTEXT_DEPENDENT`, `INSUFFICIENT_DATA`, `REJECTED`.

### J. State machine
`REGISTERED → RUNNING → CHECKPOINTED → COMPLETE → PROOF_ELIGIBLE`; failures `PARTIAL`, `INVALID_DATASET`, `CANCELLED`; artifact is immutable after completion.

### K. Calculations
OR candidates at minimum 5/10/15/20/30 minutes when source supports; confirmation 1m/3m/5m/15m. Metrics: sample, net-R expectancy, PF, drawdown, MAE/MFE, false-break, retest success, trigger delay, time-in-trade, no-chase/stop/target sensitivity, regime/period/holdout stability and interval estimates. Definitions come from Calculation Registry.

### L. Reasoning architecture
Timing candidates are competing hypotheses. Selection uses statistically defensible comparison and can preserve multiple candidates. Search actively records evidence against the top-ranked choice.

### M. Decision/output semantics
Ranking is not proof. `NO_SIGNIFICANT_DIFFERENCE` prevents cosmetic score differences from becoming permanent policy.

### N. Dynamic behavior
Registered matrix may differ by source granularity/profile; selection thresholds are versioned research policy, never daily mutable knobs.

### O. Failure modes
Combinatorial mining, same-day leakage, confirmation TF built from incomplete bars, candidate selection mismatch, one regime dominating, continuous-series roll leak, test set reused for tuning.

### P. False certainty prevention
Report uncertainty and pairwise practical difference; require minimum independent dates/trades; preserve unknown outcomes.

### Q. Code-change map
Extend `timing_research.py`/`discovery.py`; use session profile grouping; add confirmation-TF adapter and registered search manifest; preserve checkpoint mechanism.

### R. Backward compatibility
Existing timing windows remain a baseline matrix subset; current outputs remain readable via compatibility adapter.

### S. Tests
Matrix generation, session-relative clocks, source-TF capability, checkpoint resume determinism, multiple-valid/no-difference/insufficient outcomes, holdout isolation, symmetry, costs, performance.

### T. GREEN acceptance gate
Full requested matrix supported where data permits; no held-out selection leakage; deterministic resume; current timing regression preserved; exact-head CI GREEN.

### U. Rollback plan
Use current timing-research mode and ignore advanced artifact; no active playbook mutation.

### V. Observability
Run ID, matrix-cell counts, pruned combinations/reasons, cache hits, stage timings, dataset hash.

### W. Performance budget
Vectorize/cache reusable OR facts; prune impossible TF/profile pairs; checkpoint by immutable cell key; avoid O(N²) pair analysis unless bounded.

### X. Security/safety
Research artifacts cannot auto-promote playbooks or guidance.

### Y. Unresolved uncertainties
Practical-effect thresholds and multiplicity correction method require calibration on actual dataset scale in BUILD-5 implementation review.

### Z. Implementation checklist
Registered matrix → session grouping → confirmation bars → cached facts → metrics/intervals → multiplicity/stability → checkpoint/resume → shadow compare → tests/CI → lock.

---

# 16. BUILD-6 — Explicit ORB Signal / Market-Event Brain

### A. Stage purpose
Convert closed-candle behavior into explicit, versioned market-event states separate from parameter selection and final guidance.

### B. Problem being solved
Current core conflates detection, confirmation and entry/stop/target construction and does not expose full retest/failed-break/reentry/staleness lifecycle.

### C. Questions this reasoning engine must answer
Did price cross, close beyond, accept, reject, retest, hold/fail, become stale or invalidate? Which OR boundary/event family? What supports/contradicts the event?

### D. Questions it is forbidden to answer
Unproven entry/stop/target optimization, sizing, final guidance, broker action.

### E. Current repository truth
`orb/core.py::_signal_candidate` supports breakout/breakdown and reversal on closed bars; adaptive controller has richer branch concepts. Both are reusable references, not the final generic state machine.

### F. Upstream inputs
Resolved session/OR window, closed confirmation bars, canonical OR levels, context evidence, active timing artifact/playbook rules, explicit availability/provenance.

### G. Downstream consumers
BUILD-7 parameter selector, BUILD-8 backtest/proof, BUILD-9 analog memory, BUILD-11 evidence package.

### H. Upstream/downstream failure propagation
No range lock => `PENDING_RANGE`; missing required confirmation volume => state may be `UNOBSERVABLE_VOLUME_CONFIRMATION`, not failed volume; stale snapshot => no new authoritative transition.

### I. Canonical output contract
`OrbSignalEventV1`: event ID/type/side, state, ORH/ORL/ORM/width, normalized width, trigger/buffer, crossed/closed/accepted/retested facts, volume/VWAP/trap evidence refs, freshness, transition history, invalidation, reasons FOR/AGAINST, unknowns, D2 hash, signal hash.

### J. State machine
Core legal sequence: `NO_RANGE/PENDING_RANGE → RANGE_LOCKED → WATCHING → TRIGGERED → CONFIRMED`; branches `REJECTED`, `RETEST_PENDING → RETEST_HELD/RETEST_FAILED`, `FAILED_BREAK`, `TRAP_STRENGTHENED`, `SECOND_CHANCE_ELIGIBLE → REENTRY_CONFIRMED`, `INVALIDATED`, `STALE`, `NO_SETUP`. Transitions are event-sourced and deterministic.

### K. Calculations
Cross = intrabar high/low geometry; close-beyond = fully closed confirmation close past boundary+registered buffer; acceptance = registered consecutive-close/hold rule; retest = registered touch zone then close/accept rule; freshness = session-relative bars/time since confirmation. Every rule comes from frozen playbook/timing artifact.

### L. Reasoning architecture
Signal is a market-event hypothesis, not a trade instruction. Maintain continuation and failed-break hypotheses concurrently until evidence invalidates one.

### M. Decision/output semantics
`BREAKOUT_LONG` means a configured market event has occurred; `NO_SETUP` means no qualifying event, not evidence unavailable. `UNAVAILABLE` is separate.

### N. Dynamic behavior
Signal definitions may vary by proven playbook; transition law, causality and closed-bar requirement do not.

### O. Failure modes
Wick treated as close, same bar used as both trigger and future confirmation, stale setup resurrected, mirror asymmetry, missed session break, volume missing converted to false, late correction rewriting event ID.

### P. False certainty prevention
Record observation type and required evidence separately; do not infer acceptance from price crossing alone.

### Q. Code-change map
New signal state module wrapping/extracting current core detection; adapt adaptive branches; keep legacy `build_orb_candidate` facade until migration.

### R. Backward compatibility
Golden legacy breakout/reversal fixtures must map to semantically equivalent new events before current signal path is replaced.

### S. Tests
All requested event families, state-transition legality, closed-bar causality, wick-vs-close, retest hold/fail, stale, reentry limit, volume unavailable, bullish/bearish mirrors, deterministic event history.

### T. GREEN acceptance gate
No future/incomplete transition possible; legacy parity mapped; event states typed/versioned; full adversarial/replay/authority/CI pass.

### U. Rollback plan
Legacy core continues creating signal/plan; advanced event engine remains shadow-only.

### V. Observability
Transition event IDs, reason codes, rule/playbook version and latency; no hidden traces.

### W. Performance budget
One incremental pass over new closed bars; persist state by `(candidate, session, playbook, snapshot)` to avoid rescans.

### X. Security/safety
Signal object contains no execution method or broker identifier.

### Y. Unresolved uncertainties
Exact acceptance/retest rules must be sourced from proof-backed playbooks, not invented globally during implementation.

### Z. Implementation checklist
Event enum → transition table → fact evaluators → invalidation/freshness → legacy mapper → property/mirror tests → shadow → regression/CI → lock.

---

# 17. BUILD-7 — Trade-Parameter / Invalidation / Paper-Risk Research Brain

### A. Stage purpose
Research and freeze what parameter set is appropriate **if** a valid evidence/event state exists; never optimize today using today’s future.

### B. Problem being solved
Legacy core directly derives stop/target from OR boundary and fixed RR, coupling event detection to one parameter model.

### C. Questions this reasoning engine must answer
Which pre-researched entry/buffer/no-chase/stop/target/hold/reentry/cost/liquidity policy survives proof for this event/context? What invalidates it? Is no parameter set supported?

### D. Questions it is forbidden to answer
Ad-hoc parameter optimization from today’s later candles, account/broker execution sizing, final D6 guidance.

### E. Current repository truth
`OrbStrategyConfig`, discovery, paper lifecycle and adaptive policy contain parameter ideas; target parameter-research artifact is `PARTIALLY_IMPLEMENTED`.

### F. Upstream inputs
BUILD-4 context, BUILD-5 timing artifacts, BUILD-6 events, registered parameter families, realistic cost/slippage/liquidity model, historical session data.

### G. Downstream consumers
BUILD-8 proof, BUILD-10 playbook, BUILD-11 paper-risk hints, BUILD-13 outcome evaluation.

### H. Upstream/downstream failure propagation
Unknown tick/spread/liquidity disables parameter models requiring them. Zero/negative risk distance is `INVALID_PARAMETER_GEOMETRY`, not epsilon-adjusted permission.

### I. Canonical output contract
`OrbParameterResearchArtifactV1` and frozen `OrbParameterSetV1`: entry method/zone, buffer, chase ceiling, confirmation, volume/VWAP rules, stop model, invalidation, target model, min RR, cutoff, setup expiry, max hold/flat, reentry, cost model, liquidity constraints, applicable context/event profiles, proof IDs/hashes.

### J. State machine
Parameter candidate `REGISTERED → RESEARCHED → PROOF_ELIGIBLE → FROZEN`; alternatives `REJECTED`, `UNSUPPORTED`, `RETIRED`. Runtime selector returns `APPLICABLE`, `NO_SUPPORTED_SET`, `AMBIGUOUS`, `UNAVAILABLE_INPUT`.

### K. Calculations
Entry/stop/target formulas are parameter-model specific and registered; initial risk = absolute entry-stop with strict positive check; target R uses frozen model; costs use versioned bps/fees/impact model; no `max(risk,1e-9)` for semantic invalidity.

### L. Reasoning architecture
Competing parameter hypotheses are tested offline. Runtime only matches current state to already-proven applicability; contradictions can disqualify a set.

### M. Decision/output semantics
`APPLICABLE` means parameter artifact matches evidence/profile and proof; it remains paper/research guidance subordinate to D6/human approval.

### N. Dynamic behavior
Different instruments/regimes may map to different frozen sets; the set itself is immutable for a given version/hash.

### O. Failure modes
Parameter mining, hindsight stop placement, target chosen after seeing excursion, unrealistic fills, ignoring gap-through stop, hidden fees, reentry explosion, illiquid commodity contract.

### P. False certainty prevention
Report unsupported/ambiguous sets explicitly; no default fixed RR if required proof is absent.

### Q. Code-change map
Extract parameter construction from legacy core behind compatibility adapter; add research artifact/selector; reuse paper cost/lifecycle semantics and adaptive policy concepts.

### R. Backward compatibility
Legacy opposite-OR stop/fixed-RR model becomes an explicit `LEGACY_OR_BOUNDARY_RR_V1` candidate and must prove parity before deprecation.

### S. Tests
Geometry, no-chase, cutoffs, stop/target models, gap fills, ambiguity, costs, liquidity unavailable, no set, one-reentry limit, symmetry, PIT/replay.

### T. GREEN acceptance gate
Runtime never optimizes; all active sets are frozen/proof-referenced; legacy parity and authority tests pass; exact-head CI GREEN.

### U. Rollback plan
Continue legacy core parameter construction while advanced selector is shadow.

### V. Observability
Parameter-set hash, match rules, rejection reasons, cost model version; no broker secrets.

### W. Performance budget
Runtime O(number of active proven sets), bounded small; expensive grid search offline and checkpointed.

### X. Security/safety
Sizing remains descriptive paper-risk hint only; no account/order API.

### Y. Unresolved uncertainties
Exact cost sources and commodity liquidity model need data-contract review.

### Z. Implementation checklist
Parameter registry → legacy model adapter → offline search manifest → selector → cost/fill parity → tests → shadow → CI → lock.

---

# 18. BUILD-8 — Discovery / Backtest / Walk-Forward / Proof Brain

### A. Stage purpose
Separate attractive in-sample patterns from repeatable, causal, after-cost evidence.

### B. Problem being solved
Existing proof is a strong base but advanced search needs candidate-selection reconstruction, statistical uncertainty, multiplicity controls, richer outcomes and generic sessions.

### C. Questions this reasoning engine must answer
Was selection PIT-safe? Does edge survive chronological unseen data, costs, periods/regimes and holdout? Is sample sufficient? Are results outlier-dominated? Is edge decaying? Did multiple testing inflate the apparent winner?

### D. Questions it is forbidden to answer
Promote from full-sample/in-sample alone; tune on untouched holdout; convert synthetic proof to paper authority.

### E. Current repository truth
`proof.py` already performs train-only top-k selection, expanding folds and holdout; adaptive `prove_policies` adds unknown-outcome blocking, frozen universe and lower-bound statistics.

### F. Upstream inputs
Versioned dataset manifest, candidate reconstruction, profiles/calendars, timing/signal/parameter artifacts, cost model, labels/outcomes and registered search space.

### G. Downstream consumers
BUILD-9 memory eligibility, BUILD-10 promotion, BUILD-11 proof status, BUILD-12 model governance.

### H. Upstream/downstream failure propagation
Unresolved outcome/candidate selection/calendar identity => proof degraded/blocked. Synthetic data can test software but not authorize promotion.

### I. Canonical output contract
`OrbProofReportV2`: code/data/calendar/profile/search hashes; train/validation/fold/holdout date sets; selected-on-train IDs; metrics+intervals; multiplicity method; stability/drift/outlier analysis; candidate-selection reconstruction status; blockers; proof hash; promotion eligibility false unless all gates pass.

### J. State machine
`REGISTERED → TRAIN_SELECTION → WALK_FORWARD → FROZEN_SELECTION → HOLDOUT_EVAL → ELIGIBLE/REJECTED/BLOCKED`; holdout can execute once per proof version.

### K. Calculations
Net-R metrics, PF with explicit no-loss semantics, drawdown, block-bootstrap uncertainty, minimum sample, fold pass rate, concentration/outlier contribution, multiple-testing correction/false-discovery policy chosen and versioned. Purge/embargo applied when outcome/label horizons overlap split boundaries.

### L. Reasoning architecture
Evidence FOR = robust unseen performance. AGAINST = instability, costs, drift, concentration, missing/biased selection. Alternative explanation “selection/mining artifact” is first-class.

### M. Decision/output semantics
`PROOF_ELIGIBLE` is necessary but not sufficient for ACTIVE playbook; promotion is BUILD-10.

### N. Dynamic behavior
Thresholds/search policy can evolve only by version and re-proof; historical proof artifact is immutable.

### O. Failure modes
Selection before split, label overlap, survivorship, candidate-filter mismatch, repeated holdout peeking, split by rows not dates, correlated symbols counted as independent dates, unknown outcome dropped as zero/no-trade, data snooping.

### P. False certainty prevention
Always expose sample/unique dates, interval width, unknown counts, strata support and number of tested hypotheses.

### Q. Code-change map
Extend `orb/proof.py`/`discovery.py`; borrow adaptive proof utilities where compatible; add generic session/date keys, artifact manifests, no-loss PF semantics, statistical helpers under existing conventions.

### R. Backward compatibility
Read current v1.91 proofs/playbooks through migration adapter; never silently reclassify old proof as V2 eligible.

### S. Tests
Train-only selection, holdout immutability, purge boundary, candidate reconstruction, synthetic blocker, unknown outcomes, multiple-testing trap, one-outlier dominance, unstable years, no meaningful winner, replay/performance.

### T. GREEN acceptance gate
All proof eligibility paths are causally isolated; held-out data cannot influence selection; statistical gates tested; old proof regression maintained; exact-head CI GREEN.

### U. Rollback plan
V2 proof not used for activation; current proof store remains readable/active under legacy route.

### V. Observability
Proof stage timings, evaluated/pruned candidates, dataset/code hashes, split dates, blockers.

### W. Performance budget
Cache per-session event/outcome simulations; bounded registered configurations; parallelizable offline folds with deterministic reduction order.

### X. Security/safety
Proof cannot route orders or bypass human review; review signatures/code hashes remain local governance artifacts.

### Y. Unresolved uncertainties
Multiplicity method and minimum support thresholds require research-policy approval; no universal magic number is specified here.

### Z. Implementation checklist
V2 schema → causal dataset manifest → split/purge → richer metrics → multiplicity/outlier/drift → compatibility reader → adversarial tests → full regression/CI → lock.

---

# 19. BUILD-9 — Combination / Analog / Historical Memory Reasoning Brain

### A. Stage purpose
Learn conditional situations and failure patterns without treating one historical match as certainty.

### B. Problem being solved
Indicator-by-indicator memory misses interactions; naive nearest neighbors can double-count same-session/overlapping outcomes and sparse buckets.

### C. Questions this reasoning engine must answer
Which historical situations are genuinely comparable? Which features match/mismatch/unavailable? How many independent episodes exist? What outcomes occurred? Is the query OOD? Is evidence drifting?

### D. Questions it is forbidden to answer
Final guidance, trade authority, 100% probability from sparse matches, outcome labels before maturation.

### E. Current repository truth
`canonical_analog_memory.py` already has versioned feature specs, bounded distance, raw vs independent counts, overlap/session/source independence blockers and OOD. Reuse it.

### F. Upstream inputs
Canonical memory corpus, BUILD-1 reason, BUILD-2 identity, BUILD-4 context facts, BUILD-5 timing, BUILD-6 signal, BUILD-7 parameter ID, matured labels only. Features include value + availability + version.

### G. Downstream consumers
BUILD-10 playbook known contexts/failures, BUILD-11 historical evidence, optional BUILD-12 features.

### H. Upstream/downstream failure propagation
Missing required feature can make analog query OOD; optional unavailable fields reduce comparable dimensions; unlabelled/unmatured episodes cannot count as outcome evidence.

### I. Canonical output contract
`OrbAnalogEvidenceV1`: feature-manifest/hash, corpus/cutoff hash, raw neighbors, independent neighbors, similarity/distance, matched/mismatched/unavailable features, outcome distribution, net-R distribution, uncertainty, regimes/time range, recency/drift, OOD reasons, support/contradiction.

### J. State machine
`QUERY_VALID → MATCHED`; alternatives `SPARSE`, `OOD`, `UNAVAILABLE`, `ERROR`. Analog set versions are immutable by corpus cutoff.

### K. Calculations
Use canonical analog weighted normalized distance unless research proves a new metric; similarity = `1-distance`; outcome statistics count independent episodes; conditional expectancy intervals use block/date-aware resampling, not raw alert count.

### L. Reasoning architecture
Hybrid deterministic bucket + nearest analog + regime statistics. Evidence descendants do not become extra independent episodes. Contradictory outcomes remain visible.

### M. Decision/output semantics
`SPARSE/OOD` means abstain from analog conclusion, not neutral. Historical memory is evidence only.

### N. Dynamic behavior
Feature manifest/context may evolve by version; corpus cutoff advances only with matured records.

### O. Failure modes
One-match certainty, duplicate same day/symbol, overlapping outcome horizon, post-event features, regime leakage, unstable scale, survivorship, feature availability mismatch, future corpus cutoff.

### P. False certainty prevention
Expose raw vs independent count, maximum distance, mismatch features, interval and OOD; never emit probability without calibrated basis.

### Q. Code-change map
Adapter/feature manifest around `canonical_analog_memory` and memory corpus; add ORB-specific fact-family mappings, not duplicate engine.

### R. Backward compatibility
Existing memory remains unchanged; ORB adds a new feature manifest/query view.

### S. Tests
Sparse/OOD, same-session independence, overlapping labels, source hash overlap, missing features, deterministic ranking, regime mismatch, bullish/bearish symmetry where feature semantics are directional-normalized, replay/performance.

### T. GREEN acceptance gate
ORB analog view uses canonical corpus, no future label, independent counts correct, bounded runtime, exact-head CI GREEN.

### U. Rollback plan
Disable ORB analog adapter; canonical M3.3 memory unaffected.

### V. Observability
Query/corpus/manifest hashes, raw/independent counts, OOD reasons, bounded top matches.

### W. Performance budget
Pre-index/cache normalized features; bounded `MAX_ANALOGS`; no unbounded daily full-corpus scan in D6 path.

### X. Security/safety
Memory cannot propose final band or execute; personal/account data not stored in feature corpus.

### Y. Unresolved uncertainties
Optimal ORB feature manifest and scaling are proof questions; start interpretable and bounded.

### Z. Implementation checklist
ORB feature manifest → canonical memory adapter → independence/outcome stats → sparse/OOD policy → drift fields → tests → shadow → CI → lock.

---

# 20. BUILD-10 — Per-Instrument Playbook Compiler / Promotion Brain

### A. Stage purpose
Compile only proven, reproducible research into immutable versioned playbooks with explainable lifecycle.

### B. Problem being solved
Current `OrbPlaybook` captures a relatively small config/proof bundle and status is mainly active/retired; target playbook must bind the entire causal/research identity.

### C. Questions this reasoning engine must answer
Did proof pass? Which profile/timing/signal/parameter/context conditions were proven? Is artifact compatible with current instrument/session/contract versions? Is it promoted, degraded or retired, and why?

### D. Questions it is forbidden to answer
Live optimize/mutate parameters, waive proof, self-promote from paper wins, execute.

### E. Current repository truth
`proof.py::promote_orb_playbook` is a valid promotion seam with proof binding and retirement of previous active symbol/timeframe playbook; extend it.

### F. Upstream inputs
BUILD-2 profiles, BUILD-5 timing artifact, BUILD-6 signal rules, BUILD-7 parameter set, BUILD-8 proof, BUILD-9 context/analog summaries, governance review metadata.

### G. Downstream consumers
BUILD-11 runtime evidence package, BUILD-12 model eligibility, BUILD-13 feedback/drift.

### H. Upstream/downstream failure propagation
Superseded session/contract/profile or invalid proof => not ACTIVE. Unknown compatibility => `DEGRADED/BLOCKED`, never silent fallback to previous compatible-looking playbook.

### I. Canonical output contract
`OrbPlaybookV2`: instrument/contract/session applicability; source TF; OR/clock/confirmation choices; supported signal families; good/bad/conflicted contexts; candidate-intake dependency; volume/VWAP/CPR/prior-session/BB/benchmark/event/expiry/roll rules; entry/invalidation/stop/target/RR/no-chase/cutoff/hold/reentry/cost; sample/splits/proof metrics/uncertainty/failures/drift; every version/hash; lifecycle/reason.

### J. State machine
`RESEARCH_ONLY → CHALLENGER → PROOF_ELIGIBLE → PROMOTED → ACTIVE → DEGRADED → RETIRED`; `INVALIDATED` terminal for broken identity/proof. Re-activation requires a new version/proof, not mutation.

### K. Calculations
Compiler does no new market math; it validates referenced artifact hashes/compatibility and computes canonical playbook hash.

### L. Reasoning architecture
Promotion criteria are deterministic governance gates plus proof evidence; reasons FOR promotion and blockers AGAINST are retained.

### M. Decision/output semantics
`ACTIVE` means eligible to produce ORB evidence for matching identity, not permission to paper trade.

### N. Dynamic behavior
Lifecycle can change by new evidence/drift review; playbook content never mutates under same ID/hash.

### O. Failure modes
Silent parameter mutation, cross-contract use, outdated calendar/profile, stale model attached, proof hash mismatch, two active conflicting playbooks, retirement losing audit history.

### P. False certainty prevention
Promotion record exposes proof limits and known failure modes; no “best strategy” wording without scope.

### Q. Code-change map
Versioned successor/adapter around current playbook store; compiler/validator; lifecycle events; migration reader for v1.91.

### R. Backward compatibility
V1 playbook remains usable through compatibility route until V2 shadow parity and explicit migration. Never rewrite stored V1 rows in place.

### S. Tests
Promotion gates, hash binding, active uniqueness, profile mismatch, stale contract, lifecycle transitions, immutable versions, migration adapter, authority, replay.

### T. GREEN acceptance gate
Only fully proof-bound V2 artifacts can become ACTIVE; no silent mutation; current V1 route regression passes; exact-head CI GREEN.

### U. Rollback plan
Disable V2 activation; V1 store remains untouched/readable.

### V. Observability
Lifecycle event, playbook/proof/profile hashes, activation/degradation reason and age.

### W. Performance budget
Compile offline; runtime lookup indexed by instrument/session/contract/profile IDs, O(1)/small bounded set.

### X. Security/safety
Promotion rights do not equal paper approval; no credentials/broker configuration in playbook.

### Y. Unresolved uncertainties
Operator review/signature policy for V2 promotion must align with existing adaptive governance and deployment process.

### Z. Implementation checklist
V2 schema → compatibility reader → compiler/validator → lifecycle event store → activation lookup → shadow migration → tests/CI → lock.

---

# 21. BUILD-11 — ORB Evidence Package + AFRE/D6 Integration Brain

### A. Stage purpose
Translate ORB findings into a rich canonical evidence receipt so AFRE/D6 can reason with support, contradiction, missingness and vetoes without ORB becoming final authority.

### B. Problem being solved
Current guidance adapts ORB into a weighted arbiter request and includes fake-neutral placeholder fields such as fixed relative-strength/indicator/external-AI scores and `weak_sector=False`.

### C. Questions this reasoning engine must answer
What did ORB observe/prove? What supports/contradicts each hypothesis? What is unavailable? What is stale/invalidated? Which dependencies/correlation families exist? What proof/playbook/model identity applies?

### D. Questions it is forbidden to answer
Final WAIT/WATCH/PAPER-CANDIDATE, trade execution, broker route, overriding higher-authority blockers.

### E. Current repository truth
`orb_guidance.py`, `DecisionContext`, stage-2 integrity and M4 D6 design are the migration seams. Authority registry already makes D6 sole final-band authority.

### F. Upstream inputs
BUILD-1 through BUILD-10 outputs, D1/D2 integrity, canonical M3 worlds, active playbook, optional calibrated model receipt. Every input binds to same decision identity or declares independent external source with causal availability.

### G. Downstream consumers
DecisionContext/AFRE/M4 receipt validator/D6, paper guidance presenter, audit/replay.

### H. Upstream/downstream failure propagation
Unavailable input remains an explicit evidence block. Snapshot mismatch/hard integrity failure blocks package eligibility. `NOT_APPLICABLE` is preserved separately from `UNAVAILABLE`.

### I. Canonical output contract
`OrbEvidencePackageV1`: candidate intake, market identity, data quality, prior session, context/hypotheses, timing proof, signal state, parameter set, proof, analogs, playbook, optional ML; `FOR`, `AGAINST`, `UNKNOWN`, `HARD_BLOCKER`, `SOFT_CONFLICT`, `INVALIDATION`; dependencies/correlation families; freshness; uncertainty vector; provenance/source hashes/versions; `may_set_final_band=false`, `may_execute=false`.

### J. State machine
Package `ASSEMBLING → VALIDATED → AVAILABLE`; alternatives `DEGRADED`, `CONFLICTED`, `UNAVAILABLE`, `BLOCKED_INTEGRITY`, `ERROR`. Package lifecycle never transitions to final guidance.

### K. Calculations
No duplicate market calculation. Package computes only deterministic evidence identities, dependency graph closure, freshness comparison and canonical package hash.

### L. Reasoning architecture
Evidence graph records ancestry and support/contradiction/invalidation. Correlation families prevent descendants becoming independent votes. Contradiction remains explicit; no averaging to zero.

### M. Decision/output semantics
ORB says “here is what I found”; AFRE/D6 determine meaning together. Package can locally veto an ORB setup due to its own invalidation, but cannot set final product band.

### N. Dynamic behavior
Evidence availability changes with snapshot; proof/playbook/model content remains frozen by hash.

### O. Failure modes
Placeholder neutral values, cross-snapshot evidence, ORB self-promoting signal, correlation inflation, evidence package changing when D6 desired side changes, recursive AFRE→ORB feedback.

### P. False certainty prevention
Explicit uncertainty dimensions and unavailable blocks; no synthetic/mocked source in probability/final-band inputs; no generic “confidence=87%”.

### Q. Code-change map
Add ORB evidence package/DecisionContext adapter; modify `orb_guidance.py` behind feature/shadow seam to consume it; coordinate with M4 contracts; remove placeholders only after parity and D6 migration proof.

### R. Backward compatibility
Legacy guidance remains active while new package and legacy arbiter request are emitted side-by-side; compare outputs/reasons, never silently swap.

### S. Tests
Placeholder elimination, snapshot identity, correlation graph, conflicting strong evidence, unavailable/N/A, invalidation, D6 independence, long/short symmetry, authority, replay, receipt size/performance.

### T. GREEN acceptance gate
No fake-neutral substitution; every ORB evidence fact traceable; D6 remains only finalizer; shadow comparisons explain differences; exact-head CI GREEN.

### U. Rollback plan
Feature flag/adapter selects legacy guidance request; evidence package generation can be disabled without data migration.

### V. Observability
Package hash, evidence counts by epistemic/family/availability, blockers/conflicts, D6 receipt linkage; bounded diagnostics.

### W. Performance budget
O(number of bounded evidence nodes/edges); reuse canonical hashes; no historical scan in runtime package assembly.

### X. Security/safety
Authority validator must reject `may_execute=true`, unauthorized final-band claim or broker fields.

### Y. Unresolved uncertainties
Final M4 D6 receipt schema may evolve; integration adapter must target the locked M4 contract when available rather than hard-coding planning prose.

### Z. Implementation checklist
Package schema → integrity validator → dependency graph → DecisionContext/M4 adapter → shadow guidance → placeholder removal tests → authority/replay/performance → CI → lock.

---

# 22. BUILD-12 — Calibrated ML / Champion-Challenger Brain

### A. Stage purpose
Add predictive evidence only for narrowly defined ORB questions where deterministic labels and unseen-data tests prove incremental value.

### B. Problem being solved
Opaque “AI confidence” would create false authority; current adaptive forecasting demonstrates a safer narrow label/calibration pattern but does not cover the complete target.

### C. Questions this reasoning engine must answer
For a declared event/horizon, does a model improve calibrated unseen-data prediction/economic utility over simple baselines? Is it in support/OOD? Is calibration/drift acceptable?

### D. Questions it is forbidden to answer
Generic BUY/SELL, causal explanation from correlation, final D6 band, model self-training online, use immature labels.

### E. Current repository truth
`adaptive/forecasting.py` has structural labels, chronological train/calibration/test, Brier/log-loss/ECE, support cells and source-origin checks. No universal ORB ML authority exists; that is correct.

### F. Upstream inputs
Matured labelled dataset with BUILD-1..11 feature versions, frozen feature manifest, profile/playbook identity, chronological split, model code version.

### G. Downstream consumers
BUILD-11 package as `PREDICTIVE` evidence; BUILD-13 calibration/drift feedback. No direct D6 final-band shortcut.

### H. Upstream/downstream failure propagation
Censored/unmatured label excluded with reason; OOD feature support => no probability; drift/calibration failure downgrades challenger or disables model.

### I. Canonical output contract
`OrbPredictiveEvidenceV1`: target event, horizon, issue time, probability/expected-R if applicable, calibrated interval, model/dataset/feature hashes, train/calibration/test ranges, support count, baseline comparison, calibration metrics, OOD/drift state, uncertainty, provenance.

### J. State machine
Model `REGISTERED → TRAINED → CALIBRATED → HELDOUT_TESTED → CHALLENGER → CHAMPION`; alternatives `REJECTED`, `DEGRADED`, `RETIRED`. Prediction `ESTIMATED` or explicit `UNSUPPORTED/OOD/UNAVAILABLE`.

### K. Calculations
Metrics: Brier, log loss, calibration curve/ECE, precision/recall where target warrants, economic/decision-curve utility, probability intervals; splits chronological with purge/embargo for overlapping labels. Compare against deterministic/base-rate/simple model.

### L. Reasoning architecture
ML is one evidence family; feature dependencies remain recorded. Counter-evidence includes calibration failure, OOD, drift and baseline non-improvement.

### M. Decision/output semantics
A probability must state event+horizon+basis. No unnamed `confidence` field.

### N. Dynamic behavior
Champion may be replaced only after challenger revalidation; runtime model immutable/versioned.

### O. Failure modes
Label leakage, post-event feature, repeated test reuse, class imbalance hidden, calibration-only overfit, distribution shift, sparse per-instrument model, random split, continuous-futures leakage.

### P. False certainty prevention
Reject complexity without stable incremental value; expose interval/support/OOD; probability unavailable outside support.

### Q. Code-change map
Extend/adapt adaptive forecasting/governance; model registry/artifact loader; ORB feature/label pipelines. Do not add LLM decision authority.

### R. Backward compatibility
No model is required for current ORB; deterministic path remains complete and active when ML unavailable.

### S. Tests
Feature PIT, label maturity, split isolation, calibration metrics, baseline comparison, OOD, model/code hash mismatch, drift, champion/challenger, replay, authority.

### T. GREEN acceptance gate
At least one declared model question beats baseline on untouched test and passes calibration/support/drift gates, or BUILD-12 is explicitly recorded `REJECTED_AS_NO_INCREMENTAL_VALUE`. No model is activated merely because code exists.

### U. Rollback plan
Disable model artifact; package emits `UNAVAILABLE/NOT_PROMOTED` predictive evidence; deterministic ORB unchanged.

### V. Observability
Model/hash, support, OOD/drift, calibration summary, inference latency; no feature values containing secrets.

### W. Performance budget
Morning inference bounded and batchable; training offline; model size/latency budget set from BUILD-0 runtime benchmark.

### X. Security/safety
No online self-modification; signed/reviewed artifacts; ML cannot bypass D1, hard blockers, AFRE or D6.

### Y. Unresolved uncertainties
Model family is intentionally unspecified until deterministic target/data audit demonstrates need.

### Z. Implementation checklist
Target/label contract → feature manifest → chronological dataset → simple baseline → challenger → calibration/test → governance review → package adapter → tests/CI → lock or reject.

---

# 23. BUILD-13 — Paper Guidance / Outcome Maturation / Feedback Brain

### A. Stage purpose
Connect immutable online evidence to later outcomes for offline learning without temporal contamination.

### B. Problem being solved
Existing paper lifecycle is strong but target needs richer label horizons, halt/roll/event semantics, drift/calibration datasets and explicit online/offline boundary.

### C. Questions this reasoning engine must answer
Has outcome matured? Was entry filled? Did target/stop/time/invalidity occur under declared replay rules? Is outcome ambiguous/censored? What cost/slippage applied? Is record eligible for calibration/drift research?

### D. Questions it is forbidden to answer
Rewrite the original evidence/playbook, auto-promote based on today, route live orders, treat pending as loss/win.

### E. Current repository truth
`orb_paper_lifecycle.py` validates identity/closed bars, marks pending, handles same-bar stop/target conservatively, computes MFE/MAE/R/costs; `orb_paper_feedback.py` is reduce-only and no-auto-mutation.

### F. Upstream inputs
Immutable BUILD-11 package/guidance ticket, human paper approval, paper ledger, future closed observations, BUILD-2 session/contract profile, cost/roll/event metadata.

### G. Downstream consumers
Offline research datasets, BUILD-8 re-proof, BUILD-9 corpus, BUILD-12 calibration/drift, BUILD-10 degradation/retirement review.

### H. Upstream/downstream failure propagation
Missing future bars/halt/ambiguous contract roll => pending/censored/unknown according to label contract; never zero PnL by default.

### I. Canonical output contract
`OrbMaturedOutcomeV2`: immutable source IDs/hashes, label contract/horizon, fill/exit state, target/stop/time/halt/roll/gap ambiguity, MFE/MAE/gross/net R, costs, observation snapshot, maturity time, eligibility flags and integrity hash.

### J. State machine
`ISSUED → HUMAN_APPROVED → PENDING_TRIGGER → OPEN → COMPLETED`; alternatives `NO_FILL`, `CENSORED`, `UNKNOWN`, `INVALIDATED_DATA`. Completed immutable.

### K. Calculations
Reuse lifecycle calculation registry for fill/cost/MFE/MAE/R; add profile-aware close/flat/halt/roll rules. Same-bar ambiguity policy stays explicit/versioned.

### L. Reasoning architecture
Outcome facts do not reinterpret the original thesis; offline analyses compare predicted/evidence states with matured truth.

### M. Decision/output semantics
`PENDING` is not failure; `NO_FILL` distinct from `NO_SETUP`; `CENSORED` excluded from ordinary binary labels unless method explicitly models censoring.

### N. Dynamic behavior
Label contract can vary by playbook/instrument but is frozen per ticket/outcome.

### O. Failure modes
Future bar in online context, duplicate outcome, missing ticket, contract roll mid-horizon, halt, gap-through target/stop, late correction, premature label, ignoring costs.

### P. False certainty prevention
Maintain ambiguous/censored states and audit eligibility; feedback sample count uses independent completed episodes, not raw alerts.

### Q. Code-change map
Versioned extension of `orb_paper_lifecycle.py`/feedback; profile-aware outcome adapter; offline dataset exporter; no destructive store rewrite.

### R. Backward compatibility
V1.94 lifecycle rows stay readable and immutable; V2 adapter can map fields with explicit unknowns.

### S. Tests
Pending/matured, no-fill, halt/missing bars, gap-through, same-bar, roll, session close, costs, orphan/hash mismatch, future leak, duplicate idempotency, feedback reduce-only.

### T. GREEN acceptance gate
Online evidence cannot observe outcome fields; all matured labels bind identity and profile; feedback never upgrades automatically; exact-head CI GREEN.

### U. Rollback plan
Continue V1 lifecycle/feedback; V2 exporter disabled.

### V. Observability
Outcome state counts, maturity lag, censored/unknown reasons, orphan/integrity issues, drift summaries offline.

### W. Performance budget
Incremental/idempotent evaluation; stop scanning after terminal outcome; bounded bars per label horizon.

### X. Security/safety
Human approval remains required; simulation only; explicit `external_execution_attempted=false` and no broker order fields.

### Y. Unresolved uncertainties
Commodity settlement/roll label treatment depends on final BUILD-2 product policies.

### Z. Implementation checklist
V2 label/outcome schema → profile-aware lifecycle → migration reader → offline exporter → reliability/drift → adversarial tests → regression/CI → lock.

---

# 24. BUILD-14 — Adversarial System / Replay / CI / Shadow Lock

### A. Stage purpose
Prove the integrated upgraded ORB behaves correctly under normal, edge, hostile and distribution-shifted conditions before migration becomes authoritative evidence.

### B. Problem being solved
Passing happy-path unit tests cannot prove causality, replay, generic sessions, authority or research integrity across a multi-stage system.

### C. Questions this reasoning engine must answer
Can future data change past output? Does symmetry hold? Do missing/corrupt/stale inputs fail honestly? Do contract/session changes replay? Can any ORB/ML/memory stage escalate authority? Is runtime bounded?

### D. Questions it is forbidden to answer
It cannot waive a failing invariant because average performance is good; cannot label stage GREEN without exact-head CI evidence.

### E. Current repository truth
Existing ORB v189/v190/timing/guidance/paper-feedback tests, adaptive AFRE test tree, Decision Spine M3.1/M3.2/M3.3/replay/authority tests and workflows form the regression base.

### F. Upstream inputs
Locked BUILD-0..13 contracts/artifacts/tests; representative stock/commodity fixture datasets; exact versions/hashes; CI workflows.

### G. Downstream consumers
Migration/activation decision, canonical status docs, release audit.

### H. Upstream/downstream failure propagation
Any invariant failure blocks lock. Performance failure is AMBER until fixed. Optional ML failure disables ML, not deterministic ORB, unless corrupted shared facts caused it.

### I. Canonical output contract
`OrbSystemVerificationManifestV1`: exact SHA; per-stage lock hashes; test classes/counts/results; golden/shadow diffs; replay hashes; performance stats; authority manifest; unresolved blockers; CI run ID/conclusion.

### J. State machine
`PLANNED → IN_PROGRESS → AMBER/GREEN → LOCKED`; `BLOCKED` for invariant violation. GREEN requires all declared evidence; LOCKED records immutable exact-head proof.

### K. Calculations
Replay equality compares canonical hashes/semantic outputs; performance percentiles collected on declared fixtures; no correctness relaxation for latency.

### L. Reasoning architecture
Adversarial tests are counter-hypotheses against system claims: causal, symmetric, complete, deterministic, safe, statistically honest and bounded.

### M. Decision/output semantics
Only `GREEN / LOCKED` with exact evidence authorizes next migration seam. Documentation-only existence is `PLANNED`.

### N. Dynamic behavior
Performance baselines may scale with hardware/fixture; causality/authority/hash identity laws do not.

### O. Failure modes
Flaky clock/random IDs, test ordering dependency, shadow comparison using different data, skipped unknowns, CI not exact head, partial test suite labeled full, cache contamination.

### P. False certainty prevention
Publish failures/skips/fixture scope; store run IDs/SHA; do not infer success from prior head.

### Q. Code-change map
Test/fixture/workflow additions, shadow comparison harness, verification manifest generator; runtime changes only to fix discovered defects and must return to owning BUILD stage.

### R. Backward compatibility
Run all preserved legacy goldens until intentional migration diff is separately approved/proven.

### S. Tests
Master classes:
- causality: future bars/labels/incomplete candles/candidate reconstruction;
- symmetry: bull/bear and symmetric reversal;
- data: missing volume/prior session/zero range/duplicates/order/bad ticks/stale/hash mismatch/missing benchmark/event;
- session: NSE/holiday/exception/commodity cross-date/break/timezone;
- commodity: contract mismatch/expiry/roll/OI migration/continuous vs raw/settlement/limits/liquidity;
- research: low sample/overfit/decay/year instability/multiplicity/outlier/no winner;
- evidence: support+contradiction/correlation/N-A/unavailable/invalidation/staleness;
- authority: all execution flags false, D6 sole final band;
- replay: identical complete identity tuple => identical outputs;
- performance: candidate/runtime/research/replay datasets.

### T. GREEN acceptance gate
All implementation complete; stage-specific + full regressions + causality + replay + authority + required performance pass; docs updated; exact-head CI SUCCESS; no unresolved invariant violation.

### U. Rollback plan
Rollback the latest migration seam to previous locked stage/playbook/adapter; preserve immutable research/proof/audit artifacts.

### V. Observability
One bounded verification report per SHA, test-category summaries, replay diff path and performance distributions.

### W. Performance budget
Morning path must avoid historical scan/research grids; offline jobs checkpoint/resume/cache; benchmark targets are set from BUILD-0 and tightened only after measurement.

### X. Security/safety
Permanent assertions:
`research_only=true`, `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, `human_approval_required=true`; ORB/ML/memory cannot execute; AFRE cannot route; D6 only final band.

### Y. Unresolved uncertainties
Production hardware/data-volume SLO must be measured; do not fabricate millisecond numbers before BUILD-0 baseline.

### Z. Implementation checklist
Assemble master fixtures → causality/symmetry/data/session/commodity/research/evidence tests → replay harness → shadow diffs → performance → authority audit → full tree → exact-head CI → verification manifest → lock.

---

## 25. Cross-stage Calculation Registry

**Rule:** no implementation may create a second formula under a similar name. BUILD-0 must map each owner to existing code; BUILD owners below are target ownership. Existing canonical M3 implementations win when semantic parity is confirmed.

| Calculation | Owner / target module | Formula / definition | Units | Source inputs | Lookback / warm-up | Availability timestamp / PIT | Missing-data rule | Consumers | Version target / test vectors |
|---|---|---|---|---|---|---|---|---|---|
| Typical price | D2 feature kernel | `(H+L+C)/3` | price | closed OHLC | 1 bar | bar close/available_at | OHLC invalid => ERROR | VWAP/profile | existing kernel v1; flat/zero-range vectors |
| Gap | BUILD-4 using BUILD-3 | `open_current - prior_reference`; normalized `% = delta/prior_reference*100` | price, % | session open + prior close/settlement per profile | prior completed session | current open and prior ref causally available | prior ref <=0/missing => UNAVAILABLE/ERROR | context/analogs | `orb-gap.v1`; ±gap/flat/split-suspect |
| True range | canonical price calc | `max(H-L, abs(H-Cprev), abs(L-Cprev))` | price | closed OHLC + previous close | 2 bars | current bar close | missing previous close => warm-up unavailable | ATR | `orb-tr.v1`; gap-up/down/zero range |
| Wilder ATR(n) | canonical price calc, not legacy average-range | seed=`mean(TR_1..TR_n)` then `(ATRprev*(n-1)+TR)/n` | price | TR | default n=14 by registry; n complete TRs | last included bar close | insufficient => `INSUFFICIENT_HISTORY`; no epsilon fabrication | context/OR width/buffers | `orb-atr-wilder.v1`; monotonic/flat/gap vectors |
| CPR | BUILD-4 canonical level adapter | `P=(H+L+C)/3`, `BC=(H+L)/2`, `TC=2P-BC`; canonicalize top=max(BC,TC), bottom=min | price | prior completed HLC | 1 complete prior session | prior session completion | missing prior => UNAVAILABLE | context/playbook | `orb-cpr.v1`; bullish/bearish/flat candles |
| CPR width | BUILD-4 | `top-bottom`; `% = width/P*100` when P>0 | price,% | CPR | same | CPR availability | P<=0 => ERROR | compression context | `orb-cpr-width.v1` |
| PDH/PDL/PDC | BUILD-3/4 level adapter | prior completed session high/low/close | price | CompletedSession | 1 session | session complete | incomplete => unavailable/degraded per fact | context/signal/targets | `orb-prior-levels.v1` |
| ORH/ORL | BUILD-6 fact owner using BUILD-2 profile | max high / min low of fully closed bars in exact OR interval | price | D2 bars + OR window | chosen OR duration | after final OR bar is closed/available | missing required interval => PENDING/INCOMPLETE | signal/parameters | `orb-opening-range.v2`; 5/10/15/20/30 fixtures |
| ORM | BUILD-6 | `(ORH+ORL)/2` | price | ORH/ORL | range locked | OR lock | unavailable if OR unavailable | context/signal | same version |
| OR width | BUILD-6 | `ORH-ORL` | price | ORH/ORL | range locked | OR lock | negative impossible=>ERROR | timing/parameters | same |
| OR width / ATR | BUILD-6 | `OR_width / ATR` | ATR units | OR width + canonical ATR matching declared timeframe/horizon | ATR warm-up | max availability of both | ATR<=0/unavailable => UNAVAILABLE, not 0 | context/timing | `orb-or-width-atr.v1` |
| VWAP | D2/kernel or canonical indicator owner | `Σ(TP*V)/ΣV` over explicit anchor slice | price | TP, volume | anchor-to-now | all included closed bars | any required missing volume or ΣV<=0 => UNAVAILABLE | context | reuse `anchored_vwap` semantics; missing-volume test |
| VWAP deviation bands | canonical value calc | VWAP ± k× weighted std of TP around VWAP, k∈registered {1,2,3}; weighting/variance convention frozen in version | price | TP,V | session/week anchor | current closed bar | missing volume => UNAVAILABLE | context/targets | `orb-vwap-bands.v1`; constant-price std=0 valid |
| Weekly VWAP | canonical value calc | same VWAP across registered trading week/session slices, not naive 7-day bars | price | session bars | week-to-date | latest closed bar | missing required volume => degraded/unavailable | context | `orb-weekly-vwap.v1` |
| Bollinger bands | canonical indicator registry implementation; ORB consumes | target parity: SMA(n) ± k×std(close,n), parameters/version from registry | price | closes | registry n/k | last closed bar | insufficient history=>UNAVAILABLE | context | reuse registry output; parity fixture before ownership claim |
| Bollinger width | canonical indicator | `(upper-lower)/middle` when middle valid; preserve raw width too | ratio,price | BB | BB warm-up | BB availability | invalid middle=>UNAVAILABLE | compression | version tied to BB |
| RVOL | BUILD-4 volume context | cumulative/current interval volume divided by expected volume from same session-relative bucket over registered prior completed sessions; estimator and N versioned | ratio | volume + session relative time | configured prior sessions | current closed bar + historical cut-off | missing current/history or insufficient sessions => UNAVAILABLE/INSUFFICIENT_HISTORY | context/signal | `orb-rvol.v1`; constant/2x/missing/session-break |
| Breakout buffer | BUILD-7 parameter set | frozen policy function, e.g. `max(tick*k_tick, spread*k_spread if available, ATR*k_atr)` only when that policy is proof-backed | price | tick/spread/ATR | parameter proof | all required inputs available | required component missing=>set not applicable | signal/entry | per parameter-set version; no global magic |
| Distance bps | canonical level utility | `(price-level)/level*10000` signed | bps | price,level | none | both available | level<=0=>ERROR | context/analogs | `distance-bps.v1` |
| Distance ATR | canonical level utility | `(price-level)/ATR` signed | ATR | price,level,ATR | ATR warm-up | max availability | ATR<=0/unavailable=>UNAVAILABLE | context/analogs | `distance-atr.v1` |
| MAE/MFE | BUILD-8/13 outcome owner | side-aware maximum adverse/favorable excursion from fill over declared horizon | price and R | future matured bars + fill | outcome horizon | label maturity only | incomplete horizon=>PENDING/CENSORED | proof/feedback | preserve lifecycle semantics; bull/bear mirrors |
| R multiple | BUILD-8/13 | side-aware net PnL / initial risk, initial risk=`abs(fill-stop)>0` | R | fill/stop/exit/cost | outcome | maturity | zero risk=>INVALID, not epsilon | proof/feedback | `orb-r.v2` |
| Expectancy | BUILD-8 | arithmetic mean of **net** R over eligible independent outcomes; interval separately | R/trade | net R | minimum support policy | proof cutoff | unknown/censored not coerced to 0 | proof/playbook | `orb-expectancy.v2`; known/unknown samples |
| Profit factor | BUILD-8 | `sum(positive net R)/abs(sum(negative net R))` | ratio | net R | support policy | proof cutoff | no losses => state `NO_LOSS_SAMPLE` + PF mathematically unbounded/undefined for finite comparison; never cap to 999 for proof | proof | `orb-pf.v2` |
| Max drawdown | BUILD-8 | max peak-to-trough decline of cumulative net R in chronological order | R | ordered net R | full split | proof cutoff | unknown outcome blocks declared-complete series | proof | `orb-dd.v2` |
| False-break rate | BUILD-8 | count of versioned failed-break outcomes / eligible confirmed breakout events within declared horizon | proportion | signal lifecycle + matured horizon | support policy | maturity | ambiguous/unmatured excluded with counts | timing/proof | `orb-false-break.v1` |
| Retest success | BUILD-8 | eligible retest-held outcomes / eligible retest attempts under frozen retest definition | proportion | signal lifecycle/outcome | support policy | maturity | sparse=>insufficient | timing/playbook | `orb-retest-success.v1` |
| Analog similarity | canonical M3.3 analog owner | `1 - weighted_normalized_distance` with versioned feature manifest/scales | [0,1] descriptive similarity | canonical episode features | corpus cutoff | only records PIT-eligible at query time | required missing feature can make no match/OOD | BUILD-9/11 | reuse `canonical-analog-retrieval.v1` unless superseded by proof |
| Statistical uncertainty | BUILD-8/12 | not one scalar: interval method + sample/independent dates + calibration/stability fields | method-specific | proof/model samples | declared | cutoff | insufficient support => explicit state | proof/ML | versioned methods; bootstrap/calibration vectors |
| Drift | BUILD-8/12/13 | vector of performance/calibration/feature-distribution change against frozen reference; method/threshold per artifact | method-specific | matured periods | minimum windows | later offline only | sparse=>INSUFFICIENT_EVIDENCE | playbook/model lifecycle | `orb-drift.v1` after empirical threshold review |

---

## 26. Main Contract Matrix

| Contract | Producer | Primary consumers | Authority |
|---|---|---|---|
| `OrbBaselineManifestV1` | BUILD-0 | all stages/CI | audit only |
| `OrbCandidateIntakeV1` | BUILD-1 | 2,4,8,9,11 | evidence only |
| `OrbMarketIdentityV1` | BUILD-2 | 3-14 | identity/gating only |
| `OrbCompletedSessionV1` | BUILD-3 | 4,5,8,9 | fact only |
| `OrbContextWorldV1` | BUILD-4 | 5,6,7,9,10,11,12 | evidence only |
| `OrbTimingResearchArtifactV1` | BUILD-5 | 6,8,10 | research evidence |
| `OrbSignalEventV1` | BUILD-6 | 7,8,9,11 | event evidence |
| `OrbParameterSetV1` | BUILD-7 | 8,10,11,13 | research/paper hint only |
| `OrbProofReportV2` | BUILD-8 | 10,11,12 | proof gate; no final band |
| `OrbAnalogEvidenceV1` | BUILD-9 | 10,11,12 | memory evidence only |
| `OrbPlaybookV2` | BUILD-10 | 11,12,13 | evidence eligibility only |
| `OrbEvidencePackageV1` | BUILD-11 | AFRE/M4/D6 | evidence only; no final band |
| `OrbPredictiveEvidenceV1` | BUILD-12 | 11/D6 via evidence | predictive evidence only |
| `OrbMaturedOutcomeV2` | BUILD-13 | 8,9,12/offline governance | offline feedback only |
| `OrbSystemVerificationManifestV1` | BUILD-14 | release/lock | audit only |

---

## 27. Upstream / Downstream Dependency Matrix

| Stage | Hard upstream | Soft/optional upstream | Main downstream | Top-down constraints received |
|---|---|---|---|---|
| 0 | repo truth | CI metadata | 1-14 | safety/authority laws |
| 1 | baseline/source records | Trendforge/manual source | 2,4,8,9,11 | selection policy |
| 2 | baseline + candidate identity | official rule registry | 3-14 | supported venue/product policy |
| 3 | 2 + D1/D2 bars | action/settlement/roll | 4,5,8,9 | profile semantics |
| 4 | 1-3 + canonical M3 | event/derivatives sources | 5,6,7,9-12 | applicability + playbook evidence rules |
| 5 | 1-4 histories | context strata | 6,8,10 | pre-registered search policy |
| 6 | 2,4,5 + closed bars | volume/value evidence | 7-11 | frozen signal rule |
| 7 | 4-6 histories | cost/liquidity | 8,10,11 | registered parameter families |
| 8 | 1-7 | adaptive proof utilities | 9,10,12 | proof thresholds/split policy |
| 9 | 1,2,4,6 + matured memory | 5/7 features | 10-12 | feature manifest/corpus cutoff |
| 10 | 2,5-9 | governance review | 11-13 | promotion policy |
| 11 | 1-10 | 12 if proven | AFRE/D6 | DecisionContext/M4 authority/epistemic contract |
| 12 | 8,10,13 matured labels | model family | 11 | ML governance |
| 13 | 2,10,11 + human approval | 12 target definitions | 8,9,12/offline | label contract/safety |
| 14 | locked 0-13 | hardware fixture | activation | GREEN/LOCK protocol |

Bottom-up facts never accept a top-down desired side. D6 can veto/downgrade final guidance but cannot rewrite ORB facts or historical labels.

---

## 28. Evidence Dependency and Double-Counting Map

Canonical evidence nodes carry `fact_id`, `producer`, `source_hash`, `dependencies[]`, `family`, `epistemic_level`, `availability`, `observed_at`, `available_at`, `version`.

Example ancestry:

```text
PRICE
 ├─ returns
 ├─ EMA
 │   └─ MACD
 ├─ true range
 │   └─ ATR
 │       ├─ OR_width_ATR
 │       └─ ATR buffer
 └─ swing geometry
     └─ structure break

VOLUME
 ├─ VWAP
 │   └─ VWAP distance
 └─ RVOL

SESSION PROFILE
 ├─ prior-session aggregation
 │   ├─ PDH/PDL/PDC
 │   └─ CPR
 └─ opening-range bounds
     └─ ORH/ORL/ORM
```

Evidence families:

`price_action`, `trend`, `momentum`, `volatility`, `volume`, `market_structure`, `levels`, `value_vwap`, `benchmark`, `sector`, `derivatives_oi`, `event`, `candidate_selection`, `historical_analog`, `deterministic_proof`, `predictive_ml`, `data_quality`, `session_contract`.

Rules:

1. Descendants can add interpretation but not independent sample count.
2. EMA + MACD + trend slope cannot automatically equal three independent confirmations.
3. Same-session/overlapping-outcome analogs remain correlated and are counted separately from independent episodes.
4. Contradiction is represented as an edge, never erased by averaging.
5. D6/M4 may apply authority/conflict policy but must preserve original evidence direction and provenance.

---

## 29. Authority Matrix

`Y` = permitted within bounded contract; `N` = forbidden.

| Stage/engine | Observe | Calculate | Infer | Predict | Produce evidence | Local veto/invalidate own output | Final guidance | Execute |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BUILD-0 | Y | Y | Y(system only) | N | Y(audit) | Y(regression gate) | N | N |
| BUILD-1 | Y | Y | Y(input validity) | N | Y | Y(candidate eligibility) | N | N |
| BUILD-2 | Y | Y | Y(identity) | N | Y | Y(identity ambiguity) | N | N |
| BUILD-3 | Y | Y | Y(session trust) | N | Y | Y(session fact eligibility) | N | N |
| BUILD-4 | Y | Y | Y | N by default | Y | Y(context hypothesis) | N | N |
| BUILD-5 | Y | Y | Y | statistical research only | Y | Y(research candidate) | N | N |
| BUILD-6 | Y | Y | Y(event state) | N | Y | Y(signal invalidation) | N | N |
| BUILD-7 | Y | Y | Y(applicability) | offline research | Y | Y(parameter set) | N | N |
| BUILD-8 | Y | Y | Y | statistical proof | Y | Y(proof eligibility) | N | N |
| BUILD-9 | Y | Y | Y | N unless separately calibrated | Y | Y(analog/OOD) | N | N |
| BUILD-10 | Y | Y | Y(governance) | N | Y | Y(playbook lifecycle) | N | N |
| BUILD-11 | Y | Y(hash/graph) | Y(package synthesis) | N | Y | Y(ORB package only) | N | N |
| BUILD-12 | Y | Y | Y | Y, calibrated/bounded | Y | Y(model output) | N | N |
| BUILD-13 | Y | Y | Y(outcome eligibility) | N online | Y offline | Y(label eligibility) | N | N |
| AFRE | Y | Y | Y | bounded | Y | Y/downgrade per registry | N | N |
| D6 / FINAL_CONFLUENCE_ARBITER | Y | Y | Y | consumes predictive evidence | Y | Y | **Y** | N |
| human paper approval | Y | N | human | N | approval record | Y | accepts/rejects paper action | no live execution |

Permanent system flags remain false/blocked as defined in Section 5.

---

## 30. Availability / Epistemic Matrix

Target canonical availability superset:

`AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `UNKNOWN`, `STALE`, `SUSPECT`, `ERROR`, `NOT_APPLICABLE`, `INSUFFICIENT_HISTORY`, `PENDING`.

Existing Decision Spine enums may require a versioned extension/adapter; do not silently collapse the superset into `DEGRADED` when semantics matter.

| State | Meaning | Can be converted to neutral numeric? | Can satisfy required fact? | Typical action |
|---|---|---:|---:|---|
| AVAILABLE | causally available and valid for declared use | only if the actual measured value is neutral | Y | consume |
| DEGRADED | usable subset with explicit deficiency | N | policy-dependent | consume bounded / downgrade |
| UNAVAILABLE | source/fact cannot be obtained | N | N | abstain/degrade |
| UNKNOWN | truth not established | N | N | preserve uncertainty |
| STALE | existed but freshness expired | N | usually N | refuse freshness-sensitive use |
| SUSPECT | quality anomaly unresolved | N | usually N | quarantine/soft block |
| ERROR | calculation/source failed | N | N | fail closed/log |
| NOT_APPLICABLE | concept does not apply | N | not required by definition | exclude from denominator/vote |
| INSUFFICIENT_HISTORY | formula needs more valid history | N | N | warm-up/abstain |
| PENDING | fact may become available later | N | N now | wait |

Epistemic levels: `OBSERVED`, `DERIVED`, `INFERRED`, `HYPOTHESIS`, `PREDICTIVE`. A downstream stage cannot relabel `HYPOTHESIS` as `OBSERVED`.

---

## 31. Stock vs Commodity Applicability Matrix

| Capability | NSE equity | NSE derivative | Commodity raw contract | Commodity continuous research series |
|---|---|---|---|---|
| sector context | usually AVAILABLE | underlying-dependent | often NOT_APPLICABLE | often NOT_APPLICABLE |
| corporate action | applicable to equity | underlying may matter | NOT_APPLICABLE | NOT_APPLICABLE |
| NSE CPR/prior cash session | applicable by profile | only if playbook explicitly binds underlying/cash context | NOT_APPLICABLE unless defined | NOT_APPLICABLE unless defined |
| contract expiry | N/A cash | AVAILABLE | AVAILABLE | metadata required for constituent raw contracts |
| settlement vs close | profile-defined | profile-defined | critical/profile-defined | must preserve source basis |
| roll/OI migration | N/A cash | applicable | critical | critical to construction metadata |
| continuous adjustment | N/A | optional research series | N/A raw | critical; never hidden |
| benchmark | Nifty/sector registered | underlying/index registered | commodity/global/FX benchmark if registered | same, versioned |
| overnight/cross-date session | no regular cash | segment-specific | possible/profile-defined | inherits raw-session semantics |
| exchange holiday partial session | profile/calendar | profile/calendar | important morning/evening distinction | same |
| tick/multiplier/lot | instrument metadata | contract metadata | critical contract economics | source raw contract metadata |
| inventory/macro event | optional | optional | often relevant by commodity | same |

`NOT_APPLICABLE` is not a negative vote.

---

## 32. Research / Runtime Separation

### Morning runtime may do

- bind candidate/profile/D1/D2 identity;
- build prior-session/context facts from already available data;
- load active frozen timing/playbook/parameter/model artifacts;
- update explicit signal state from newly closed bars;
- query bounded pre-indexed analog memory;
- assemble ORB evidence package;
- hand evidence to AFRE/D6.

### Morning runtime must not do

- grid-search years of timing/parameters;
- refit/calibrate models;
- alter playbook parameters;
- use today’s future outcome;
- query unbounded historical corpus;
- activate a challenger automatically.

### Offline research may do

registered timing/parameter search, backtest, walk-forward, holdout, analog corpus construction, label maturation, model training/calibration, drift analysis, challenger proof and playbook compilation.

Artifacts are immutable and addressed by content/version hashes so interrupted jobs can resume safely.

---

## 33. ML Governance

1. Deterministic label contract first.
2. Mature labels only.
3. Versioned PIT feature manifest.
4. Chronological train/calibration/test; purge/embargo for overlap.
5. Untouched final test.
6. Simple baseline first.
7. Probability calibration and uncertainty.
8. OOD/support detection.
9. Economic/decision utility in addition to generic classification metrics.
10. Champion/challenger; no in-place mutation.
11. Model/data/code/feature hashes on every prediction.
12. Disable model when code binding, calibration, support or drift fails.
13. Predictive evidence never bypasses D1/AFRE/D6.

---

## 34. Historical Memory / Analog Governance

- Corpus cutoff must be before/at query decision time.
- Outcome label must have matured before inclusion as labelled evidence.
- Raw rows and independent episodes are separate counts.
- Same session, overlapping outcome horizon and shared source snapshot are correlation blockers unless a stricter future method is proven.
- Feature manifest/scales are versioned.
- Sparse/OOD query abstains.
- Similarity is descriptive; probability requires separate calibrated methodology.
- Corpus retention may compact views but cannot rewrite audit history.

---

## 35. Replay / Determinism Requirements

Replay identity tuple:

```text
input_data_snapshot_hash
candidate_intake_hash
instrument_profile_hash
session_profile_hash
contract_profile_hash
calendar_version/hash
prior_session_hash
feature/calculation_versions
context_world_hash
signal_rule_version
parameter_set_hash
proof_hash
analog_feature_manifest_hash + corpus_cutoff/hash
playbook_hash
model_hash (if any)
configuration/policy hash
code version/fingerprint where decision-relevant
```

Same complete tuple => same canonical outputs/hashes. If an external rule changes, replay uses the historical effective registry version, not the latest registry row.

---

## 36. Performance Architecture

1. Calculate primitive vectors once from D2 feature kernel.
2. Cache immutable prior-session/context facts by source/profile hash.
3. Batch historical calculations by instrument/profile/session.
4. Precompute research matrices and outcome paths where safe.
5. Cache by content hash, never mutable symbol-only keys.
6. Checkpoint timing/parameter/proof jobs by registered cell/fold.
7. Prune unsupported source-TF/profile combinations before simulation.
8. Keep analog retrieval bounded/pre-indexed.
9. Runtime loads one active playbook and small bounded challengers, not entire research store.
10. Deterministic stable ordering permits parallel offline work with stable reduction.
11. Set numeric latency/memory SLO only after BUILD-0 measures realistic fixtures; no invented performance target in this planning document.

---

## 37. Adversarial Test Master Matrix

| Invariant/failure | Owning stage(s) | Mandatory test |
|---|---|---|
| branch/SHA truth | 0,14 | manifest rejects drift |
| future candle | 3,4,6,14 | append future bars; prior output hash unchanged |
| incomplete candle | 4,6,14 | no authoritative transition before close |
| candidate selection leakage | 1,8,14 | post-cutoff ranking cannot enter historical candidate set |
| mirror semantics | 4,6,7,14 | price-reflected bull/bear fixtures |
| missing volume | 3,4,6,14 | volume facts unavailable; price facts preserved |
| missing prior session | 3,4 | gap/CPR unavailable, no zero defaults |
| zero-range | 3,4,6 | valid zero range where mathematically valid; no divide-by-zero fiction |
| duplicate/out-of-order | 3,14 | reject/quarantine deterministically |
| stale/hash mismatch | 1-14 | fail integrity/availability |
| NSE holiday/exception | 2,3,14 | registry effective session used |
| commodity cross-date | 2,3,14 | one registered session despite date boundary |
| session break | 2,3 | expected grid excludes break |
| contract mismatch | 2,10,14 | playbook not applicable |
| raw vs continuous | 2,3,8,14 | basis mismatch blocks proof/runtime reuse |
| settlement vs close | 2,3 | distinct fields/availability |
| expiry/roll/OI migration | 2,4,8,14 | context/proof strata preserve distortion |
| low sample | 5,8,9,12 | insufficient result, not winner |
| multiple testing | 5,7,8 | mined winner fails correction/gate |
| one outlier dominates | 8 | concentration blocker |
| edge decay | 8,10,13 | degrade/retire review, no auto-upgrade |
| support + contradiction | 4,11,14 | `CONFLICTED`, not neutral |
| correlated descendants | 4,9,11 | independent family count not inflated |
| N/A evidence | 4,11 | excluded, not vote=0 |
| stale signal | 6,11 | transition to STALE, cannot revive without new event |
| D6 authority | 0,11,14 | only FINAL_CONFLUENCE_ARBITER may final-band |
| execution authority | all,14 | every ORB/ML/memory `may_execute=false` |
| deterministic replay | every stage | same identity tuple same output hash |
| performance/cache isolation | 0,5,8,9,14 | realistic fixtures + content-key isolation |

---

## 38. Migration Map of Existing ORB/Related Files

| Existing file/component | Action | Target evolution |
|---|---|---|
| `apps/api/app/orb/hstry_csv.py` | `WRAP → MIGRATE → DEPRECATE_LATER` | source adapter into generic dataset/session profile; preserve current NSE loader tests. |
| `apps/api/app/orb/context.py` | `KEEP as legacy reference → EXTEND via canonical adapters → REMOVE_ONLY_AFTER_PROOF from authority path` | calculations move to canonical owners; no generic `resample("D")`. |
| `apps/api/app/orb/timing_research.py` | `EXTEND` | profile-relative OR/clock/confirmation matrix, richer stats, preserved checkpoints. |
| `apps/api/app/orb/core.py` | `WRAP → SHADOW → MIGRATE` | split range facts, explicit event state, parameter selection; facade remains until parity. |
| `apps/api/app/orb/discovery.py` | `EXTEND` | generic sessions, registered search, richer outcomes/caches. |
| `apps/api/app/orb/proof.py` | `EXTEND` | V2 proof with reconstruction, uncertainty, multiplicity, purge/embargo, compatibility reader. |
| `apps/api/app/orb/adaptive/contracts.py` | `KEEP / GENERALIZE where reused` | remove implicit NSE clock assumptions before generic use; preserve safe-output invariants. |
| `orb/adaptive/controller.py` | `KEEP as bounded hypothesis/research source; ADAPT` | reuse branches/evidence, not a new final authority. |
| `orb/adaptive/research.py` | `REUSE / EXTEND selectively` | lower-bound/unknown/frozen-universe proof patterns. |
| `orb/adaptive/forecasting.py` | `REUSE selectively` | narrow calibrated targets under BUILD-12. |
| `orb/adaptive/governance.py` | `REUSE` | artifact/code/proof review binding. |
| `behavior/orb_guidance.py` | `WRAP → SHADOW → MIGRATE` | consume `OrbEvidencePackage`; remove fake-neutral placeholders after compatibility proof. |
| `behavior/final_confluence_arbiter.py` | `DO NOT ORB-REWRITE` | M4 owns D6 redesign; ORB only supplies canonical evidence. |
| `decision_spine/authority_registry.py` | `EXTEND registrations if needed; preserve law` | all new ORB engines zero execution; D6 only final. |
| `decision_spine/stage2_integrity.py` | `REUSE / versioned extension` | recognize richer ORB availability without neutral collapse. |
| `decision_spine/decision_context.py` | `REUSE / adapter` | canonical ORB evidence block/receipt. |
| `decision_spine/snapshot_feature_kernel.py` | `REUSE` | raw fact substrate; add new facts only via versioned canonical ownership. |
| `decision_spine/canonical_session_intelligence.py` | `KEEP NSE adapter` | consume generic BUILD-2 identity or remain compatibility implementation. |
| canonical context/level/MTF/indicator systems | `REUSE` | ORB interprets; no duplicated calculators. |
| canonical memory/analog systems | `REUSE / ORB feature view` | BUILD-9. |
| `behavior/data_quality.py` | `WRAP / GENERALIZE` | session-aware provider/profile semantics; preserve existing NSE behavior until proof. |
| `behavior/point_in_time_guard.py` | `KEEP / EXTEND contracts` | explicit available-at support where duration inference insufficient. |
| `behavior/market_structure_liquidity.py` | `LEGACY/compatibility; prefer canonical M3 replacement` | eliminate missing-volume-to-zero semantics before ORB reliance. |
| `behavior/orb_paper_lifecycle.py` | `EXTEND V2` | generic session/contract outcomes, preserve V1 rows. |
| `behavior/orb_paper_feedback.py` | `EXTEND` | calibration/drift offline; preserve reduce-only law. |
| `behavior/simulated_paper_ledger.py` | `KEEP` | human-approved simulated record seam. |
| `models.py` ORB contracts | `EXTEND/version` | avoid breaking V1 serializers; add V2 typed objects/enums. |

Migration philosophy is permanently:

```text
STRANGLE / WRAP / PROVE / SHADOW / MIGRATE
```

not `DELETE / REWRITE / HOPE`.

---

## 39. CI / GREEN / LOCK Protocol

Allowed statuses: `PLANNED`, `IN_PROGRESS`, `BLOCKED`, `AMBER`, `GREEN`, `LOCKED`.

A stage is GREEN only when all apply:

1. implementation is complete for declared scope;
2. stage-specific unit/integration/property/metamorphic tests pass;
3. causality and replay tests pass;
4. relevant legacy regressions pass;
5. authority/safety tests pass;
6. required performance tests pass;
7. documentation/status manifest updated;
8. exact-head CI succeeds;
9. no unresolved invariant violation remains.

`GREEN / LOCKED` additionally records exact commit SHA, workflow/run ID, test/manifest hashes and lock evidence. Prior-head CI never locks a later SHA.

---

## 40. Exact Implementation Order

```text
0. baseline manifest/goldens
1. candidate intake/provenance
2. instrument/session/contract registry + NSE compatibility profile
3. completed-session aggregator
4. canonical ORB context/hypotheses
5. timing/clock/confirmation research
6. explicit signal state machine
7. parameter/invalidation research
8. V2 proof
9. ORB analog-memory adapter
10. playbook V2 compiler/lifecycle
11. ORB evidence package + shadow AFRE/D6 adapter
12. optional calibrated ML if and only if incremental proof succeeds
13. outcome V2/offline feedback
14. integrated adversarial/replay/performance/shadow lock
```

For each number: implement only that stage → targeted tests → adversarial/replay relevant to stage → locked regressions → full API tree → authority audit → exact-head CI → GREEN → lock → begin next stage.

---

## 41. Expected Files to Modify/Create During Later Implementation

Paths below are **expected design locations**, not implementation claims. Before each BUILD, re-check repository conventions and current head.

Likely new ORB-native modules:

- candidate intake/provenance contract;
- market identity/session/contract profile registry and adapters;
- completed-session reconstruction;
- canonical ORB context composer/hypothesis contracts;
- explicit signal state module;
- parameter research/selector;
- V2 research/proof/playbook contracts;
- ORB evidence package/DecisionContext adapter;
- optional predictive artifact registry;
- V2 outcome/offline dataset adapter;
- verification manifest/shadow harness.

Likely existing files to extend/wrap:

- `apps/api/app/models.py`
- `apps/api/app/orb/hstry_csv.py`
- `apps/api/app/orb/context.py`
- `apps/api/app/orb/timing_research.py`
- `apps/api/app/orb/core.py`
- `apps/api/app/orb/discovery.py`
- `apps/api/app/orb/proof.py`
- selected `apps/api/app/orb/adaptive/*`
- `apps/api/app/behavior/orb_guidance.py`
- `apps/api/app/behavior/orb_paper_lifecycle.py`
- `apps/api/app/behavior/orb_paper_feedback.py`
- Decision Spine authority/integrity/context adapters only as required by locked M4/M3 contracts.

Tests should follow existing `apps/api/tests/test_orb_*`, `apps/api/tests/afre/*`, and `apps/api/tests/decision_spine/*` conventions rather than introducing an unrelated test framework.

---

## 42. Known Blockers / Required Decisions Before Relevant Activation

These are not blockers to this plan; they are implementation-stage blockers if unresolved:

1. Generic commodity instrument master/provider mapping is not implemented/verified.
2. Historical official calendar/exception/contract-spec ingestion and retention source must be chosen.
3. Commodity settlement availability and continuous-series adjustment policies require explicit vendor/exchange contracts.
4. Candidate-selection historical reconstruction depends on retained Trendforge/premarket source history.
5. Cost/slippage/liquidity assumptions require versioned empirical source/policy.
6. M4 final D6 schema is still a planning program on this branch; BUILD-11 must integrate to the locked M4 contract, not assume current weighted arbiter remains final architecture.
7. Current planning head had no check-runs; BUILD-0 must establish exact-head verification for implementation work.
8. Real dataset coverage for 1m/3m/commodity/OI/event/settlement fields must be audited before research combinations are declared supported.

---

## 43. Unresolved Uncertainties

- Exact selected commodity universe and venue/product categories.
- Whether each desired VWAP/BB/structure calculation already has a canonical M3 owner with identical required semantics; BUILD-0/4 must map exact versions before coding.
- Event calendar provider and point-in-time revision history.
- Derivatives/OI source availability and revision semantics.
- Corporate-action normalization policy for historical candidate/gap studies.
- Practical-effect and multiplicity thresholds for timing/parameter search.
- Final model family, if any; BUILD-12 intentionally defers this to evidence.
- Hardware-specific daily/research performance SLO.
- Retention/versioning strategy for official rule documents and provider data snapshots.

Unknowns are expected engineering inputs. None may be replaced by model memory or convenient neutral constants.

---

## 44. Definition of Complete ORB Build

The ORB upgrade is complete only when the following are simultaneously true:

- BUILD-0 through BUILD-14 required deterministic stages are `GREEN / LOCKED` with exact-head evidence; BUILD-12 is either legitimately locked or explicitly rejected/no-value without weakening deterministic ORB.
- Candidate intake is reconstructable PIT-safe.
- Instrument/session/contract identity is versioned and exchange-source grounded.
- Previous sessions are exchange-session based, not naive calendar days.
- Raw facts are calculated once by canonical owners.
- Context is multi-axis, hypothesis-driven, contradiction-aware and explicit about missing/N/A states.
- OR duration/confirmation choices are proof-backed and can abstain/no-difference.
- Signal events use closed-candle state transitions.
- Runtime parameters are frozen from offline research.
- Discovery/proof uses chronological train selection, walk-forward, untouched holdout, costs, uncertainty and anti-overfit controls.
- Analog memory uses independent episodes and OOD/sparse abstention.
- Playbooks are immutable, versioned, explainably promoted/degraded/retired.
- ORB sends a rich evidence package, not a buy/sell score.
- Calibrated ML, if present, is merely evidence and demonstrably adds unseen-data value.
- Paper outcomes mature later and only feed offline learning.
- Same complete identity tuple replays deterministically.
- Legacy valid NSE behavior remains preserved until each intentional change is separately proven.
- Commodity support cannot activate without resolved contract/session/settlement/roll semantics.
- D6 remains sole final guidance-band authority.
- Human paper approval remains mandatory.
- No code path gains live execution/order-routing authority.

Final target flow:

```text
SELECTED STOCK / COMMODITY CANDIDATE
        ↓
CANDIDATE INTAKE + PIT PROVENANCE
        ↓
INSTRUMENT / CONTRACT / SESSION BRAIN
        ↓
D1 RAW FACTS
        ↓
D2 CLOSED-CANDLE CAUSAL SNAPSHOT
        ↓
PREVIOUS COMPLETED EXCHANGE SESSION
        ↓
CANONICAL ORB CONTEXT BRAIN
        ↓
COMPETING MARKET HYPOTHESES
        ↓
PER-INSTRUMENT OR / CLOCK / CONFIRMATION RESEARCH
        ↓
EXPLICIT ORB SIGNAL STATE MACHINE
        ↓
PROOF-BACKED PARAMETER SELECTION
        ↓
DISCOVERY / WALK-FORWARD / HOLDOUT PROOF
        ↓
COMBINATION + HISTORICAL ANALOG REASONING
        ↓
FROZEN VERSIONED PLAYBOOK
        ↓
CALIBRATED ML EVIDENCE WHEN PROVEN
        ↓
ORB EVIDENCE PACKAGE
FOR + AGAINST + UNKNOWN + INVALIDATION
        ↓
AFRE MULTI-EVIDENCE REASONING
        ↓
D6 FINAL GUIDANCE AUTHORITY
    ↓           ↓              ↓
  WAIT        WATCH       PAPER-CANDIDATE
                              ↓
                    HUMAN PAPER APPROVAL
                              ↓
                    MATURED OUTCOME ONLY
                              ↓
                 OFFLINE LEARNING / DRIFT /
                    CHALLENGER RESEARCH
```

This document is a build plan. It does not implement the flow, does not change runtime behavior, and does not make any BUILD stage GREEN by itself.
