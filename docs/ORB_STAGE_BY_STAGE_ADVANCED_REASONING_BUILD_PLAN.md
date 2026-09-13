# Trade Vision / Decision Spine / ORB — Stage-by-Stage Advanced Reasoning Build Plan

**Repository:** `onlyvictus-bit/trade-vision-app`  
**Planning branch:** `m4-d6-orchestration-redesign`  
**Original starting reference:** `9b950285b62046420bb1ad15d7c9f5b8a8f24f98`  
**Verified branch head before this re-audit:** `ae0b86d52b2f5282a3b266cbbe1c5f75568609df`  
**Re-audit date:** 2026-09-13  
**Document state:** `PLANNED / SOURCE-RECONCILED` — documentation and architecture only. This file does **not** implement ORB runtime behavior and does **not** make any BUILD stage GREEN.

> This revision exists because the first stage-by-stage document was architecturally sound but insufficiently source-complete. It summarized several older ORB requirements instead of preserving them explicitly. This revision performs a source-by-source, requirement-by-requirement reconciliation and makes omission itself a testable failure.

---

## 1. Status, scope and source-completeness rule

Continue the existing Trade Vision / Decision Spine / ORB project. Do not restart it and do not replace working ORB components simply because a cleaner rewrite is possible.

The implementation sequence remains `BUILD-0` through `BUILD-14`, but the plan now adds a mandatory **Requirement Coverage Manifest** so implementation cannot silently forget an older requirement, review rule, regression behavior, unresolved conflict or explicit rejection.

Every substantive source requirement must have exactly one disposition:

- `TARGET_REQUIRED` — must exist in the target architecture.
- `CURRENT_REGRESSION_BASELINE` — current/legacy behavior that must be preserved until an intentional, separately proven migration replaces it.
- `RESEARCH_CANDIDATE` — a hypothesis/threshold/variant that must be tested but must **not** become canonical truth without proof.
- `HISTORICAL_EVIDENCE` — old result/measurement retained for context; it is not current exact-head proof unless reverified.
- `EXAMPLE_ONLY` — explanatory example, never a hard-coded rule.
- `SUPERSEDED` — deliberately replaced by a safer/newer rule, with reason and replacement recorded.
- `CONFLICT_NEEDS_PROOF` — two retained sources disagree; preserve both priors and let registered research decide.
- `BLOCKED_NEEDS_AUDIT` — source intent is known but exact semantics/evidence are still not recoverable.

No substantive line may disappear merely because a later document is more abstract.

---

## 2. Source precedence and audited ORB source ledger

When sources disagree, use this precedence for **truth**, while still retaining lower-priority material as provenance or research candidates:

1. repository code + tests + exact-head artifacts for **current implementation truth**;
2. latest explicit scope/safety hardening document for **target boundaries**;
3. canonical future plan for **accumulated target requirements**;
4. older approved plans/memoranda for **regression behavior, rule provenance and research candidates**;
5. external-review archives for **candidate hypotheses/threshold priors only**, unless independently proven in repository research artifacts.

A lower-priority external review can never override D1/D2 causality, the authority registry, missingness semantics, or exact repository behavior.

### 2.1 Audited source set

| Source | Role in this plan | Required disposition |
|---|---|---|
| `docs/ORB_INTRADAY_STOCK_COMMODITY_SCOPE_AND_FLOW_HARDENING_2026-09-12.md` | latest stock/commodity/session hardening | target boundary |
| `docs/ORB_AFRE_CANONICAL_FUTURE_BUILD_PLAN_2026-09-10.md` | accumulated ORB/AFRE target; prior 105-requirement re-audit | target + provenance |
| `docs/ORB_SIMPLE_FLOW.md` | simplified current/legacy NSE behavior | regression baseline |
| `docs/CANONICAL_BUILD_STATUS.md` | Decision Spine status/authority truth | current truth |
| `docs/M4_D6_ORCHESTRATION_MASTER_BUILD_INDEX_2026-09-09.md` | future D6 integration boundary | target dependency |
| `docs/plans/ORB_RESEARCH_ENGINE_PLAN.md` | Discover/Prove/Playbook/Decide/Paper separation | target architecture + legacy plan |
| `docs/plans/ORB_TIMING_RESEARCH_V197.md` | approved historical timing sweep behavior | regression baseline + research provenance |
| `docs/plans/ORB_CONTEXT_NATIVE_PLAN_V2.md` | context-native milestones, PIT gaps, rollback rules | target provenance/research candidates |
| `docs/plans/ORB_STRATEGY_MEMORANDUM.md` | rule IDs, calibration conflicts, detailed ORB hypotheses | research candidate registry |
| `docs/plans/ORB_EXTERNAL_REVIEW_BRIEF.md` | historical external-review summary | historical evidence only |
| `docs/plans/ORB_GAP_TRADING_EXTERNAL_REVIEW_BRIEF.md` | deliberately narrow gap-morning experiment profile | historical experiment profile |
| `docs/plans/ORB_V201B_NSE_REVIEW_KIMI_PART2.md` | archived external review | research provenance only |
| `docs/plans/ORB_V201C_NSE_REVIEW_KIMI_PART3.md` | archived consolidated 18 variants, failures, derivatives, 50-row table, top-10 | research provenance only |
| relevant ORB/Decision Spine code/tests | implementation reality | highest current-truth authority |

BUILD-0 must expand this ledger if additional ORB source documents are found. A changed source blob/hash invalidates the previous requirement-coverage report until re-audited.

---

## 3. Executive objective

The target ORB is a causal, research-driven reasoning system, not `IF breakout: buy` and not one opaque confluence score.

It must ask:

```text
What is happening?
Which facts are actually known now?
Which exchange session and contract do those facts belong to?
Why might the move be happening?
Which alternative explanations remain plausible?
What supports continuation?
What supports failure/fade/reversal?
What evidence is missing, stale, suspect or not applicable?
What genuinely comparable historical situations exist?
How independent is that historical evidence?
What did registered unseen-data proof show?
What invalidates this thesis?
Has the setup become stale or extended?
What changes if the interpretation is wrong?
Should this stage emit evidence, abstain, or escalate uncertainty?
What should AFRE/D6 know FOR and AGAINST the setup?
```

Different brains answer different questions. Candidate intake does not decide direction. Session identity does not decide a setup. Context does not decide final guidance. Signal detection does not invent today’s optimal stop. Historical memory does not become authority. ML does not become authority. D6 remains the final permitted guidance-band authority.

---

## 4. Absolute authority and epistemic laws

Permanent system law:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true
```

Permanent epistemic law:

```text
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

Also:

1. D1 outranks every predictor/reviewer.
2. No incomplete candle has decision authority.
3. Every M2+ input must be causally available by the decision timestamp.
4. Important outputs carry provenance, version, availability, `observed_at`, `available_at`, identity and source/snapshot hashes.
5. Same complete valid replay identity => same canonical output.
6. `FINAL_CONFLUENCE_ARBITER` / D6 remains sole final-band authority.
7. No ORB, memory, ML, context or parameter module may execute or route orders.
8. Top-down policy can constrain use of facts; it cannot rewrite facts.
9. Desired D6 direction can never flow backward to modify ORB evidence.
10. Matured outcomes enter offline learning only after the original online decision is immutable.

---

## 5. Architecture law: calculate once, interpret many times

```text
RAW FACT CALCULATED ONCE
        ↓
CANONICAL VERSIONED FACT
        ↓
MANY SPECIALIST BRAINS INTERPRET
        ↓
EVERY INTERPRETATION TRACEABLE TO FACT IDS/HASHES
```

For every calculation record owner, formula, units, source fields, lookback, warm-up, availability timestamp, insufficient-history state, version, provenance and consumers. No ORB-private clone of a canonical M3 calculation is allowed merely because importing it is inconvenient.

Evidence combination records ancestry. Example:

```text
PRICE
 ├─ EMA
 │   └─ MACD
 └─ trend slope
```

EMA + MACD + trend slope are not automatically three independent votes.

---

## 6. Current repository truth and legacy behavior that must not vanish

Current/legacy facts below are regression facts, not automatically target universal rules.

### 6.1 Existing ORB engines to retain and strengthen

- `apps/api/app/orb/hstry_csv.py`
- `apps/api/app/orb/context.py`
- `apps/api/app/orb/timing_research.py`
- `apps/api/app/orb/core.py`
- `apps/api/app/orb/discovery.py`
- `apps/api/app/orb/proof.py`
- `apps/api/app/orb/adaptive/*`
- `apps/api/app/behavior/orb_guidance.py`
- simulated paper ledger / lifecycle / feedback
- D1/PIT guard and D2 closed snapshot
- M3.1 price/level/indicator/MTF systems
- M3.2 canonical context world
- M3.3 canonical memory/analog systems
- Stage-2 integrity and DecisionContext
- authority registry and final confluence arbiter

Migration philosophy:

```text
STRANGLE → WRAP → PROVE → SHADOW → MIGRATE
```

never `DELETE → REWRITE → HOPE`.

### 6.2 Legacy NSE behavior to lock in BUILD-0

The baseline fixture set must preserve, where current code/docs verify it:

- NSE regular-session behavior around `09:15–15:30` as a **legacy NSE profile**, not generic exchange truth;
- closed 5m-bar behavior;
- existing opening-range construction by configured bars/clock;
- ORH / ORL / midpoint / width / width% / range-volume / opening-range VWAP;
- existing `orb_breakout`, `orr_reversal`, `hybrid_orb` families;
- existing long/short/both settings;
- close confirmation, volume confirmation, opening-range-VWAP confirmation, cutoff, stop, target and R:R behavior;
- existing event outputs `BREAKOUT_LONG`, `BREAKDOWN_SHORT`, `REVERSAL_LONG`, `REVERSAL_SHORT`, `NO_SETUP`;
- the historical v1.97 timing windows `09:20`, `09:30`, `09:35`, `09:40` as regression/search provenance;
- historical proof shape: train-only selection, chronological walk-forward and frozen holdout;
- current playbook/guidance/paper identity chain and simulated outcome semantics;
- stop-first conservative same-bar handling;
- current no-order-routing/human-approval constraints.

Historical fixed thresholds such as `min_score=0.55`, `min_samples=20`, `min_wins=8`, `min_profit_factor=1.05`, `max_drawdown_pct=0.20`, old risk percentages, or old fixed clock cutoffs are `CURRENT_REGRESSION_BASELINE` or `RESEARCH_CANDIDATE`, **not new universal stock/commodity policy** unless re-proven.

### 6.3 Verified legacy hazards to remove from the canonical path

Canonical ORB must not preserve semantic bugs merely for numeric parity:

- `bar.volume or 0.0` when volume is missing;
- `relative_strength_score=0.5` when unavailable;
- indicator/external-AI default `0.0` when unavailable;
- `weak_sector=False` when sector truth is unknown;
- missing trap/event risk becoming `0.0` / “safe”;
- zero-valued features used when required source state is absent.

Required distinction:

```text
OBSERVED_ZERO
!= MISSING
!= UNKNOWN
!= UNAVAILABLE
!= STALE
!= SUSPECT
!= NOT_APPLICABLE
!= ERROR
!= INSUFFICIENT_HISTORY
```

---

## 7. Target lineage and runtime/offline separation

```text
USER / TRENDFORGE SHORTLIST               [runtime]
        ↓ evidence
CANDIDATE INTAKE + PIT PROVENANCE
        ↓
INSTRUMENT / CONTRACT / SESSION PROFILE
        ↓
D1 RAW FACTS
        ↓
D2 CLOSED-CANDLE CAUSAL SNAPSHOT
        ↓
PREVIOUS COMPLETED EXCHANGE SESSION
        ↓
CANONICAL ORB CONTEXT
        ↓
COMPETING MARKET HYPOTHESES
        ↓
ACTIVE PROVEN CLOCK/TF ARTIFACT  ← OR/CLOCK/TF RESEARCH [offline]
        ↓
BOUNDARY/LOCATION FACTS + EXPLICIT SIGNAL STATE MACHINE
        ↓
PROOF-BACKED FROZEN PARAMETER SET ← parameter research [offline]
        ↓
DISCOVERY / WALK-FORWARD / HOLDOUT PROOF               [offline]
        ↓
COMBINATION + HISTORICAL ANALOG MEMORY
        ↓
FROZEN VERSIONED PLAYBOOK
        ↓
CALIBRATED ML EVIDENCE WHEN PROVEN                      [optional]
        ↓
ORB EVIDENCE PACKAGE
  FOR + AGAINST + UNKNOWN + INVALIDATION + DEPENDENCIES
        ↓
AFRE MULTI-EVIDENCE REASONING
        ↓ authority
D6 FINAL GUIDANCE AUTHORITY
    ↓          ↓                 ↓
   WAIT       WATCH        PAPER-CANDIDATE
                               ↓
                     HUMAN PAPER APPROVAL
                               ↓
                     MATURED OUTCOME ONLY
                               ↓ feedback
                  OFFLINE LEARNING / DRIFT /
                    CHALLENGER RESEARCH
```

Morning runtime must not rerun years of discovery, tune parameters, train models or use unfinished same-day outcomes.

---

## 8. Stage dependency graph

```text
BUILD-0  truth + requirement/regression lock
   ↓
BUILD-1  candidate intake
   ↓
BUILD-2  instrument/session/contract identity
   ↓
BUILD-3  previous completed session
   ↓
BUILD-4  canonical context + hypotheses
   ↓
BUILD-5  OR duration / clock / confirmation-TF research
   ↓
BUILD-6  boundary facts + explicit signal state machine
   ↓
BUILD-7  parameter / invalidation / paper-risk research
   ↓
BUILD-8  discovery / backtest / WF / holdout proof
   ↓
BUILD-9  combination / analog / historical memory
   ↓
BUILD-10 playbook compiler / promotion
   ↓
BUILD-11 ORB evidence package + AFRE/D6 integration
   ↓
BUILD-12 calibrated ML / champion-challenger (only if useful)
   ↓
BUILD-13 paper outcome maturation / feedback
   ↓
BUILD-14 adversarial replay / CI / shadow lock
```

BUILD-12 is allowed to end `REJECTED_AS_NO_INCREMENTAL_VALUE`. Deterministic ORB quality does not require decorative ML.

---

# 9. BUILD-0 — Baseline / Invariant / Requirement / Regression Lock

### A. Stage purpose
Create the exact truth baseline and a machine-checkable guarantee that no old ORB requirement silently disappears.

### B. Problem being solved
ORB requirements are distributed across code, canonical plans, old approved plans, external-review archives and historical status docs. Architecture summaries alone can omit important details.

### C. Questions this brain must answer
What exists? What is wired? Which behavior is current? Which line is a target, legacy baseline, research candidate, superseded rule, conflict, example or unresolved item? Does every source requirement map somewhere?

### D. Questions forbidden
No market direction, setup quality, parameter optimization or final guidance.

### E. Current repository truth
The branch contains current ORB runtime modules plus multiple older ORB plan/review documents. The first version of this master file did not explicitly reconcile all of them.

### F. Upstream inputs
Git branch/SHA, source blob hashes, code/tests, source-document ledger, workflow inventory, stores/artifacts and exact-head CI evidence.

### G. Downstream consumers
Every later BUILD and every GREEN/LOCK decision.

### H. Failure propagation
A source blob changed, requirement is unmapped, disposition is contradictory, or exact current behavior is uncertain => coverage is not PASS. No “probably covered”.

### I. Canonical output contracts
`OrbBaselineManifestV1`, `OrbRequirementManifestV1`, `OrbRequirementCoverageReportV1`.

`OrbRequirementManifestV1` fields:

```text
requirement_id
source_doc_path
source_blob_sha
source_section
source_line_range_or_text_hash
requirement_text_hash
requirement_class
stage_owner
target_section
contract_ids
calculation_ids
test_ids
disposition
supersedes
implementation_evidence
status
notes
```

### J. State machine
`DISCOVERED → CLASSIFIED → MAPPED → VERIFIED → GOLDEN_CAPTURED → CI_VERIFIED → LOCKED`; source drift returns it to `DISCOVERED`.

### K. Calculations
SHA-256 of canonical JSON/text identities, golden semantic-output hashes and benchmark timings only.

### L. Reasoning architecture
Competing classifications are explicit. “Legacy defect” vs “required compatibility” cannot be decided without evidence.

### M. Decision/output semantics
Coverage `PASS` requires 100% mapped requirements and zero unresolved invariant/authority conflicts. `BLOCKED_NEEDS_AUDIT` is allowed but prevents claiming source-complete lock.

### N. Dynamic behavior
Source SHAs and implementation evidence change. Authority/epistemic laws do not.

### O. Failure modes
Wrong branch, stale doc copy, hidden source file, requirement merged into a vague sentence, current implementation mistaken for desired policy, external review mistaken for market truth, flaky golden fixture.

### P. False certainty prevention
Every source line has a disposition. Historical `740/740`, BEL statistics or old threshold claims remain historical until exact artifacts are reverified.

### Q. Code-change map
Later implementation may add a small repository-native requirement-audit utility and deterministic manifest/report fixtures. This documentation task does not implement it.

### R. Backward compatibility
Lock bullish ORB, bearish mirror, no setup, insufficient data, failed break/reversal, replay, NSE session grouping, playbook lookup, D6 authority, paper identity, v1.97 timing behavior and current safety gates.

### S. Tests
Manifest parser/validator, source-hash drift, duplicate/unmapped requirement, regression goldens, deterministic serialization, current ORB/Decision Spine suite, authority suite, performance baseline.

### T. GREEN acceptance gate
100% requirement disposition, golden baseline committed, source hashes fixed, regressions pass, authority passes, exact-head CI success, no unresolved invariant conflict.

### U. Rollback plan
Remove audit artifacts only; no runtime behavior changed.

### V. Observability
Source count, requirement count by class, unmapped IDs, conflicts, stale source hashes, golden diff reasons.

### W. Performance budget
Audit is offline O(source bytes + manifest rows); cache by source blob hash.

### X. Security/safety
No secret/environment content in manifests. Safety/authority flags explicitly asserted.

### Y. Unresolved uncertainties
A historical “multi-dimension readiness” concept is referenced indirectly in old planning context, but an exact canonical 12-dimension definition was not verified in this re-audit. It remains `BLOCKED_NEEDS_AUDIT`; do not invent dimensions.

### Z. Implementation checklist
Reverify head → enumerate source ledger → extract/classify requirements → generate manifest → lock legacy goldens → baseline performance → targeted/full/authority tests → exact-head CI → lock.

---

# 10. BUILD-1 — Candidate Intake + Provenance Brain

### A. Stage purpose
Convert user/Trendforge/manual morning selections into canonical PIT-safe research candidates.
### B. Problem
Current symbol intake does not fully encode why/when the instrument was selected or how to reproduce selection historically.
### C. Must answer
Instrument identity, selection reason, source, `observed_at`, `available_at`, freshness, supplied metrics, source quality, eligibility for study and historical reconstruction rule.
### D. Forbidden
LONG/SHORT, entry/stop/target, setup probability or final guidance.
### E. Current truth
`timing_research.resolve_symbols` supports explicit/Trendforge symbol sources, but not the full immutable candidate contract.
### F. Inputs
Manual/user record, Trendforge record, premarket/event source; typed units/version/hash; required vs optional fields.
### G. Consumers
BUILD-2,4,8,9,11.
### H. Failure propagation
Required identity missing => reject; optional metric missing => explicit unavailable; stale premarket metric never becomes normal/zero.
### I. Output
`OrbCandidateIntakeV1` with candidate ID/hash, reasons, source facts, selection-rule version, cutoff, provenance and historical reconstruction policy.
### J. States
`RECEIVED → IDENTITY_PENDING → VALIDATED → ELIGIBLE_FOR_STUDY`; or `REJECTED`, `QUARANTINED`, `UNAVAILABLE_REQUIRED_FACT`.
### K. Calculations
Selection-rule evaluation only. Gap/RVOL/etc reference canonical calculation IDs; no local formula clone.
### L. Reasoning
Validity/bias hypotheses only; candidate means “study”, never “trade”.
### M. Semantics
`ELIGIBLE_FOR_STUDY` has zero directional meaning.
### N. Dynamic behavior
Registered reasons vary; causal timestamps do not.
### O. Failure modes
Post-open selection leak, survivorship, alias collision, duplicate source, late-added manual reason, selection rule changed without version.
### P. False certainty
`TRUE/FALSE/UNKNOWN/NOT_APPLICABLE`, not boolean defaults.
### Q. Code map
Wrap existing symbol resolution; add typed intake/source adapters under repository conventions.
### R. Backward compatibility
Legacy list becomes explicit `MANUAL_RESEARCH_CANDIDATE` adapter.
### S. Tests
Trendforge/manual, timestamp leakage, stale/suspect, dedupe, historical reconstruction, deterministic hash, no direction implication.
### T. GREEN gate
All active intake paths shadow canonical output; historical reconstruction defined; exact-head CI success.
### U. Rollback
Route old symbol list unchanged.
### V. Observability
Candidate/source/reason/availability counts and latency.
### W. Performance
O(candidate facts), batch source reads.
### X. Safety
No paper ticket/execution/proof authority.
### Y. Uncertainties
Trendforge historical retention/schema must be frozen in BUILD-0.
### Z. Checklist
Contract → adapters → PIT validation → dedupe/hash → reconstruction → shadow → tests → CI → lock.

---

# 11. BUILD-2 — Instrument / Session / Contract Identity Brain

### A. Purpose
Remove NSE-stock-only assumptions from generic ORB logic.
### B. Problem
Current ORB/data-quality/session helpers embed NSE/IST clocks; commodity contracts need exchange, session, expiry, roll, settlement and economics.
### C. Must answer
Instrument, exchange/segment, contract, timezone, calendar, opening anchor, breaks, close/settlement, expiry, roll state, tick, multiplier/lot, raw vs continuous basis and applicable context families.
### D. Forbidden
Direction/setup quality/profitability.
### E. Current truth
NSE cash session implementation exists; generic MCX/commodity contract registry was not verified.
### F. Inputs
Versioned official exchange calendar/circular/spec records + instrument master/provider mapping.
### G. Consumers
BUILD-3 through 14.
### H. Failure propagation
Unknown/ambiguous/stale identity blocks identity-sensitive downstream use. No fallback to “09:15–15:30”.
### I. Outputs
`OrbInstrumentProfileV1`, `OrbSessionProfileV1`, `OrbContractProfileV1`, bound by `OrbMarketIdentityV1`.
### J. States
Registry `DRAFT→VERIFIED→ACTIVE→SUPERSEDED→RETIRED`; decision `RESOLVED/AMBIGUOUS/STALE/UNAVAILABLE/ERROR`.
### K. Calculations
Session-relative tradable minutes exclude registered breaks; expiry/settlement only from effective registry, never weekday memory.
### L. Reasoning
Identity candidates can compete; ambiguity is a blocker.
### M. Semantics
`RESOLVED` proves identity only.
### N. Dynamic behavior
Calendars/specs may change by effective version; replay pins historical version.
### O. Failures
DST-linked commodity close, special session, partial holiday, expired contract reuse, continuous/raw mismatch, tick-size change, roll mapping correction.
### P. False certainty
Never infer contract semantics from symbol text alone.
### Q. Code map
Versioned registry + NSE compatibility adapter + commodity fixtures; preserve current session engine as adapter until migration.
### R. Backward compatibility
Normal NSE profile must reproduce valid current NSE grouping.
### S. Tests
NSE parity, holiday/exception, cross-midnight commodity, breaks, raw/continuous, expiry/roll, stale registry, replay.
### T. GREEN gate
NSE exact parity + source-versioned generic fixtures + fail-closed ambiguity + CI success.
### U. Rollback
Legacy NSE selector remains available.
### V. Observability
Profile/version/effective rule/source hash/exception ID.
### W. Performance
Cached O(1)/O(log n) local registry lookup; no live network fetch in decision loop.
### X. Safety
External rule ingestion cannot self-activate without validation.
### Y. Uncertainties
Commodity universe/vendor symbol mapping/settlement source policy.
### Z. Checklist
Contracts → official-source fixtures → resolver → NSE parity → commodity fixtures → replay → shadow → CI → lock.

---

# 12. BUILD-3 — Previous Completed Session Reconstruction Brain

### A. Purpose
Produce exact prior completed exchange-session facts.
### B. Problem
Naive calendar-day `resample("D")` is unsafe for generic/overnight sessions; proof date slicing can also drop the D-1 context needed by the first test day.
### C. Must answer
Which bars belong to prior session? Complete? Correct price basis? Data gaps/bad ticks? Corporate action? Roll? Close vs settlement? Trust state?
### D. Forbidden
Bullish/bearish trade interpretation.
### E. Current truth
Legacy context aggregation exists; D2/kernel validation exists; generic session aggregation needs migration.
### F. Inputs
BUILD-2 identity; full causal history; data-quality; corporate-action/roll/settlement source.
### G. Consumers
BUILD-4,5,8,9.
### H. Failure propagation
Missing volume degrades volume facts but does not invent zero; incomplete prior session blocks complete-session facts.
### I. Output
`OrbCompletedSessionV1` with session ID/profile/contract, expected/observed grid, OHLC, volume state, close, separate settlement, adjustments, source hashes, quality and session hash.
### J. States
`PENDING`, `COMPLETE_TRUSTED`, `COMPLETE_DEGRADED`, `INCOMPLETE`, `QUARANTINED`, `UNAVAILABLE`, `ERROR`.
### K. Calculations
O/H/L/C exactly over registered session; sum volume only under declared complete-volume policy; no close→settlement substitution unless profile explicitly defines it.
### L. Reasoning
“Session complete” is a falsifiable hypothesis with coverage/anomaly evidence.
### M. Semantics
Complete/degraded controls which downstream fields can be consumed.
### N. Dynamic
Expected bars depend on profile/timeframe/breaks.
### O. Failures
Cross-date session, partial holiday, halt, split/bonus, late settlement, revision, roll jump, bad tick.
### P. False certainty
No silent interpolation/repair; raw and adjusted basis explicit.
### Q. Code map
New session-aware aggregator; legacy resample becomes compatibility only.
### R. Backward compatibility
Clean normal NSE session must match prior valid daily OHLC fixture.
### S. Tests
Friday/Monday, holiday, missing/duplicate, corporate action, cross-date, break, roll, settlement, deterministic hash.
### T. GREEN
No canonical calendar-day grouping; NSE parity; commodity fixtures; CI.
### U. Rollback
Legacy path remains isolated.
### V. Observability
Coverage, missing intervals, adjustment/roll IDs, source revisions.
### W. Performance
One pass O(n), cache by profile/session/source hash.
### X. Safety
Corrections produce new version/hash.
### Y. Uncertainties
Vendor settlement/corporate-action historical semantics.
### Z. Checklist
Expected-grid → aggregator → quality → adjustments/settlement → NSE parity → commodity → replay → CI.

---

# 13. BUILD-4 — Canonical ORB Context + Hypothesis Brain

### A. Purpose
Describe market situation on multiple axes without becoming final authority.
### B. Problem
Rich context capabilities exist, but current ORB consumes only a subset and legacy guidance has fake-neutral defaults.
### C. Must answer
Trend, volatility, compression, prior-session morphology/patterns, PDH/PDL/PDC, CPR, gap/open location, BB, session/daily/weekly VWAP and bands, ATR, volume/RVOL, structure, levels, sweeps/traps, benchmark, sector, relative strength, event, derivatives/OI, expiry/roll, data quality, support/contradiction/unknowns.
### D. Forbidden
One generic `context_score`, final guidance, ad-hoc parameters, uncalibrated probability.
### E. Current truth
Canonical M3 price/context/memory systems exist; ORB context is partial/unwired; some old formulas/defaults are unsafe.
### F. Inputs
BUILD-1..3, D2 feature kernel, canonical M3 receipts, optional event/derivatives feeds with causal availability.
### G. Consumers
BUILD-5,6,7,9,10,11,12.
### H. Failure propagation
Stock-only feature on commodity => `NOT_APPLICABLE`; missing benchmark/volume/event => explicit unavailable; optional experimental feed cannot veto if no valid source.
### I. Output
`OrbContextWorldV1` with axes, facts, epistemic level, FOR/AGAINST, dependencies/families, hypotheses, unknowns, blockers and invalidation.
### J. States
World `AVAILABLE/DEGRADED/CONFLICTED/INSUFFICIENT_EVIDENCE/UNAVAILABLE/ERROR`; hypotheses `POSSIBLE/SUPPORTED/WEAKENED/CONTRADICTED/INVALIDATED/UNOBSERVABLE`.
### K. Calculations
Consume Calculation Registry owners. CPR/gap/VWAP/BB/ATR/RVOL etc are calculated once, not reimplemented by hypothesis code.
### L. Reasoning
Default applicable hypothesis set: continuation, failed-break/reversal, gap fade, range/chop, event distortion, liquidity/roll distortion, insufficient evidence. Each has required/support/contradiction/invalidation fields.
### M. Semantics
`CONFLICTED` is not numerical neutral. Context axes are evidence, not permissions.
### N. Dynamic
Applicability by instrument/profile/playbook. Epistemic laws invariant.
### O. Failures
EMA/MACD/trend triple count; missing volume as zero; sector applied to commodity; future-confirmed pivot; stale level; event feed arriving after decision; continuous adjustment leak.
### P. False certainty
Separate data quality, evidence strength, sample support, contradiction, freshness, regime stability and calibration.
### Q. Code map
Compose canonical M3 outputs; retire duplicate ORB formulas only after parity.
### R. Backward compatibility
Shadow current context/guidance; no behavior switch yet.
### S. Tests
Missing/N-A/stale, pattern semantics, VWAP distinctions, dependencies, contradictory hypotheses, symmetry, replay, authority.
### T. GREEN
No fake neutral; all lineage traceable; correlation handled; CI.
### U. Rollback
Disable composer.
### V. Observability
Evidence/hypothesis/availability counts and reason codes.
### W. Performance
Consume each world once; cache by hashes.
### X. Safety
All context evidence-only/non-executing.
### Y. Uncertainties
Exact source contracts for event/derivatives and exact canonical owner for every requested level must be resolved.
### Z. Checklist
Adapters → axes → calculation ownership → patterns → hypotheses → dependencies → missingness → shadow → tests → CI.

### BUILD-4 mandatory legacy pattern registry

The following old candle-pattern outputs must be explicitly accounted for when previous **completed DAILY session** morphology is migrated:

`bullish_harami`, `bullish_engulfing`, `piercing_line`, `bullish_belt`, `bullish_kicker`, `morning_star`, `hammer`, `inverted_hammer`, `bearish_harami`, `bearish_engulfing`, `bearish_kicker`, `hanging_man`, `evening_star`, `shooting_star`, `doji`.

Historical priority ordering is a **legacy interpretation baseline**, not automatic future weighting:

`Morning/Evening Star 100`; `Kicker 96`; `Engulfing 90`; `Piercing 86`; `Hammer/Shooting Star 82`; `Inverted Hammer/Hanging Man 78`; `Harami 68`; `Bullish Belt 58`; `Doji 30`.

Also inventory `outside_reversal`, `three_inside`, `three_inside_filtered`, `dark_cloud_piercing`, `cdl_multibar_markers`, `sfp_markers`, N-bar reversals and chart/H&S pattern engines. Presence in the library is insufficient; ORB must receive the pattern from the correct completed-session/timeframe fact with PIT provenance.

### BUILD-4 context mathematical law retained from the strategy memorandum

CPR redundancy must be recognized rather than treated as independent votes:

```text
P = (PDH + PDL + PDC) / 3
BC = (PDH + PDL) / 2
TC = 2P - BC
CPRW = |TC - BC| = (2/3) * |PDC - BC|
```

Therefore CPR width and prior-close location share ancestry. Gap/zone/CPR combinations must not be assumed independent merely because they are separate columns.

---

# 14. BUILD-5 — OR Duration / Clock / Confirmation-Timeframe Research Brain

### A. Purpose
Discover when the opening range should lock and which confirmation timeframe is repeatably useful per instrument/context.
### B. Problem
Legacy v1.97 timing research is valuable but narrower than OR 5/10/15/20/30 × confirm 1/3/5/15.
### C. Must answer
Which OR/confirmation is stable, noisy, late, regime-dependent or statistically indistinguishable? Is there enough support to choose any winner?
### D. Forbidden
Tune today using later same-day future; force one winner; run holdout during selection.
### E. Current truth
Checkpoint/resume timing research and legacy `09:20/09:30/09:35/09:40` clocks exist as regression provenance.
### F. Inputs
PIT-reconstructed candidate universe, session profile, history, context strata, cost model and registered matrix.
### G. Consumers
BUILD-6,8,10.
### H. Failure propagation
Unavailable 1m source means corresponding 1m/3m reconstruction is unsupported, not fabricated.
### I. Outputs
`OrbClockTimeframeStateV1` for runtime facts and `OrbTimingResearchArtifactV1` for offline research.
### J. States
Research `REGISTERED→RUNNING→CHECKPOINTED→COMPLETE→PROOF_ELIGIBLE`; outcomes `SUPPORTED/MULTIPLE_VALID_WINDOWS/NO_SIGNIFICANT_DIFFERENCE/CONTEXT_DEPENDENT/INSUFFICIENT_DATA/REJECTED`.
### K. Calculations
Study OR 5/10/15/20/30 minutes when source supports exact reconstruction; confirmation 1/3/5/15. Metrics include sample, net expectancy, PF, drawdown, MAE/MFE, false-break rate, retest success, trigger delay, time-in-trade, sensitivity, regime/year/holdout stability and uncertainty.
### L. Reasoning
Timing configurations are competing hypotheses; top candidate gets active counter-evidence search.
### M. Semantics
Rank is not proof; `NO_SIGNIFICANT_DIFFERENCE` is valid.
### N. Dynamic
Matrix can vary by profile/source granularity; research policy versioned.
### O. Failures
Combinatorial mining, incomplete confirmation bars, same-day leakage, context-selection mismatch, repeated holdout tuning.
### P. False certainty
Expose independent dates/trades, intervals and practical-effect threshold.
### Q. Code map
Extend timing/discovery; preserve checkpointing and old v1.97 result compatibility.
### R. Backward compatibility
Legacy timing windows remain baseline candidates and must reproduce old fixture behavior.
### S. Tests
Clock mapping, TF availability, resume, no-diff, multiple-valid, insufficient, holdout isolation, performance.
### T. GREEN
Full target matrix supported where data permits; deterministic resume; regressions + CI.
### U. Rollback
Use legacy timing mode.
### V. Observability
Run/matrix/pruned-cell/cache/checkpoint metrics.
### W. Performance
Cache OR facts; prune impossible TF pairs; checkpoint immutable cells.
### X. Safety
Research artifacts cannot promote themselves.
### Y. Uncertainties
Multiplicity/practical-effect policy is a BUILD-5/8 research decision.
### Z. Checklist
Clock contract → matrix → source capability → cached facts → metrics → uncertainty → resume → tests → CI.

### BUILD-5 canonical clock/timeframe contract

`OrbClockTimeframeStateV1` must include:

```text
session_id
opening_anchor_ns
opening_range_minutes
opening_range_end_ns
confirmation_timeframe
confirmation_bar_close_ns
trigger_bar_close_ns
bars_since_or_lock
trigger_delay_minutes
session_elapsed_trading_minutes
entry_window_state
clock_state
source_profile_hash
source_snapshot_hash
calculation_version
```

For the NSE compatibility profile only, OR-5/10/15/20/30 from a 09:15 anchor correspond to nominal lock clocks 09:20/09:25/09:30/09:35/09:45. These are derived fixture expectations, not generic constants. The historical v1.97 09:40 endpoint remains a separate legacy search fixture.

---

# 15. BUILD-6 — Boundary / Location Facts + Explicit ORB Signal Brain

### A. Purpose
Separate what price did relative to OR boundaries from what a strategy concludes from it, then maintain a closed-candle event state machine.
### B. Problem
Current detection folds boundary crossing, confirmation and plan construction together; many requested states are not explicit.
### C. Must answer
Was the closed bar inside/outside/touching/straddling OR boundaries? Did it close beyond? Return inside? Retest? Accept/reject? Fail? Become stale? Which event state is supported?
### D. Forbidden
Invent unproven entry/stop/target, final guidance or authority.
### E. Current truth
Core supports basic breakout/breakdown/reversal; richer lifecycle must wrap/migrate it.
### F. Inputs
BUILD-2/4/5 + D2 closed bars + frozen signal-rule/playbook identity.
### G. Consumers
BUILD-7,8,9,11.
### H. Failure propagation
No locked range => pending; missing required confirmation evidence => unobservable/degraded, not false.
### I. Outputs
`OrbBoundaryLocationV1` and `OrbSignalEventV1`.
### J. States
`PENDING_RANGE→RANGE_LOCKED→WATCHING→TRIGGERED→CONFIRMED`; branches `REJECTED`, `RETEST_PENDING/HELD/FAILED`, `FAILED_BREAK`, `TRAP_STRENGTHENED`, `SECOND_CHANCE_ELIGIBLE/REENTRY_CONFIRMED`, `INVALIDATED`, `STALE`, `NO_SETUP`.
### K. Calculations
Boundary geometry is deterministic; close/accept/retest rules are frozen/playbook-versioned and use fully closed bars.
### L. Reasoning
Continuation and failed-break hypotheses may coexist until invalidation.
### M. Semantics
Cross/wick != close-beyond != acceptance. `NO_SETUP` != unavailable.
### N. Dynamic
Rule thresholds by proven playbook; transition/cause laws invariant.
### O. Failures
Wick as breakout, future bar as confirmation, stale revival, directional asymmetry, volume unavailable treated as failed confirm.
### P. False certainty
Record observation type separately from interpretation.
### Q. Code map
Extract/wrap core detection; event-source transitions; adapt legacy outputs.
### R. Backward compatibility
Legacy event fixture maps to semantically equivalent V1 event before switch.
### S. Tests
Every state/transition, wick-v-close, retest, stale, mirror, causality, missing confirm.
### T. GREEN
No illegal/future transition; parity; replay/authority/CI.
### U. Rollback
Legacy signal remains active.
### V. Observability
Event/transition IDs and reason codes.
### W. Performance
Incremental update per newly closed bar.
### X. Safety
No broker/order fields or execution method.
### Y. Uncertainties
Acceptance/retest thresholds require proof-backed playbook definitions.
### Z. Checklist
Boundary facts → transition table → event mapping → invalidation/freshness → legacy mapper → tests → shadow → CI.

### BUILD-6 boundary/location taxonomy

For each relevant fully closed post-OR bar, classify deterministic facts such as:

- `INSIDE_OR`
- `ABOVE_ORH`
- `BELOW_ORL`
- `TOUCH_ORH`
- `TOUCH_ORL`
- `STRADDLE_ORH`
- `STRADDLE_ORL`
- `STRADDLE_BOTH` when geometrically possible
- `RETURNED_INSIDE_AFTER_UP_BREAK`
- `RETURNED_INSIDE_AFTER_DOWN_BREAK`

Only a proof-backed acceptance rule may produce states such as `ABOVE_ORH_ACCEPTED` / `BELOW_ORL_ACCEPTED`.

Attach signed distances in bps/ATR/ticks where available to ORH, ORL, ORM, PDC, PDH, PDL, VWAP and relevant canonical structural levels. This layer is a fact layer, not a vote.

### BUILD-6 required signal families

Account explicitly for:

`NO_SETUP`, `BREAKOUT_LONG`, `BREAKDOWN_SHORT`, `RETEST_LONG`, `RETEST_SHORT`, `REVERSAL_LONG`, `REVERSAL_SHORT`, `FAILED_BREAK_LONG`, `FAILED_BREAK_SHORT`, `SECOND_CHANCE_REENTRY_LONG`, `SECOND_CHANCE_REENTRY_SHORT`, `TRAP_LONG`, `TRAP_SHORT`, `INVALIDATED`, `STALE`.

---

# 16. BUILD-7 — Parameter / Invalidation / Paper-Risk Research Brain

### A. Purpose
Research and freeze parameter sets before runtime.
### B. Problem
Legacy core couples signal and one stop/target convention; old documents contain conflicting stop/exit/sizing priors.
### C. Must answer
Which already researched entry/buffer/no-chase/stop/target/RR/cutoff/expiry/hold/reentry/cost/liquidity policy applies to the current proven event/context?
### D. Forbidden
Optimize today using later candles, account execution, live sizing, D6 guidance.
### E. Current truth
Strategy config, discovery, adaptive policy and paper lifecycle provide pieces; one canonical parameter artifact is missing.
### F. Inputs
BUILD-4/5/6 + registered parameter families + costs/liquidity history.
### G. Consumers
BUILD-8,10,11,13.
### H. Failure propagation
Unknown spread/tick/liquidity disables policies requiring them; zero-risk geometry is invalid, not epsilon-fixed permission.
### I. Outputs
`OrbParameterResearchArtifactV1`, frozen `OrbParameterSetV1`.
### J. States
`REGISTERED→RESEARCHED→PROOF_ELIGIBLE→FROZEN`; runtime `APPLICABLE/NO_SUPPORTED_SET/AMBIGUOUS/UNAVAILABLE_INPUT`.
### K. Calculations
Parameter formula owned by named model; initial risk strictly positive; costs versioned.
### L. Reasoning
Parameter candidates compete offline; runtime merely matches a frozen set.
### M. Semantics
`APPLICABLE` remains research/paper evidence, not permission.
### N. Dynamic
Different context may select different frozen set; set itself immutable.
### O. Failures
Hindsight stop/target, target from future excursion, hidden costs, reentry explosion, stop-rule drift between backtest/live.
### P. False certainty
No default RR/stop when proof absent.
### Q. Code map
Extract legacy parameter construction behind compatibility adapter; add registry/research selector.
### R. Backward compatibility
Legacy opposite-OR/fixed-R models become explicit named candidates for parity tests.
### S. Tests
Geometry, stop modes, targets, no-chase, cutoff, costs, gap-through, ambiguity, symmetry, reentry count.
### T. GREEN
Runtime no optimization; all active sets proof-referenced; backtest/runtime parity; CI.
### U. Rollback
Legacy parameter construction remains.
### V. Observability
Parameter hash/model/rejection/cost version.
### W. Performance
Small bounded runtime set; heavy search offline/checkpointed.
### X. Safety
Sizing outputs paper/research hints only.
### Y. Uncertainties
Empirical transaction-cost/liquidity sources.
### Z. Checklist
Registry → legacy candidates → stop/exit parity → offline research → selector → tests → CI.

### BUILD-7 preserved research-rule families

Old memorandum rules must remain visible as **research candidates / regression semantics**, including:

- `ENTRY-01` closed-bar trigger and candidate buffers;
- `ENTRY-02` historical morning cutoff 11:30;
- `ENTRY-03` time-to-target sufficiency concept;
- `ENTRY-04` late-window target truncation concept;
- `CHASE-01` no-chase after large extension;
- `STOP-01` explicit `stop_mode` rather than silent mixing of ORM/opposite OR/retest/swing/ATR/hybrid;
- `EXIT-01` partial 1R/breakeven research candidate;
- `EXIT-02` structural-vs-R target concept;
- `EXIT-03` historical 15:10 paper flat for NSE morning profile;
- `EXIT-06` exit precedence `safety > calendar caps > playbook targets > trails`;
- `EXIT-07` climax/no-follow-through and volume-dry-up management candidate;
- `REENTRY-01` one conditional retry candidate with explicit signal-slot accounting;
- `VETO-01` vetoed/blocked candidate is logged and does not silently consume a signal slot.

Numbers in these rules remain versioned priors until BUILD-8 proves them for an applicable playbook. No paper-risk hint acquires broker execution authority.

---

# 17. BUILD-8 — Discovery / Backtest / Walk-Forward / Holdout Proof Brain

### A. Purpose
Separate interesting patterns from robust unseen-data evidence.
### B. Problem
Large variant/threshold/context grids create selection bias and multiple-testing risk; old proof is strong but narrower.
### C. Must answer
Was candidate intake reconstructed? Did edge survive costs, chronological unseen data, periods/regimes, outliers and multiple-testing control? Is sample enough? Is edge decaying?
### D. Forbidden
Tune on final holdout, promote in-sample, treat synthetic as real proof.
### E. Current truth
Existing proof has train-only selection/expanding WF/holdout; adaptive proof adds unknown-outcome and lower-bound discipline.
### F. Inputs
Versioned dataset/candidate/profile/calendar/signal/parameter/search/cost manifests.
### G. Consumers
BUILD-9,10,11,12.
### H. Failure propagation
Unresolved selection/calendar/outcome => blocked/degraded proof. Unknown outcomes are not zeros.
### I. Output
`OrbProofReportV2` with hashes, splits, registered search, intervals, multiplicity, concentration, stability, drift, blockers and eligibility.
### J. States
`REGISTERED→TRAIN_SELECTION→WALK_FORWARD→FROZEN_SELECTION→HOLDOUT_EVAL→ELIGIBLE/REJECTED/BLOCKED`.
### K. Calculations
Net R, expectancy+interval, PF, drawdown, MAE/MFE, false-break/retest rates, block/date-aware uncertainty, concentration, multiplicity. Purge/embargo if label horizons cross split boundary.
### L. Reasoning
Main alternative explanation is “mining/selection artifact”; proof actively tests it.
### M. Semantics
`PROOF_ELIGIBLE` is necessary, not sufficient, for active playbook.
### N. Dynamic
Threshold/search policy changes require new version/re-proof.
### O. Failures
Data snooping, repeated holdout, row split instead of date split, correlated symbols as independent, context candidate mismatch, continuous-futures leakage.
### P. False certainty
Expose unique dates/trades, intervals, unknowns, tested hypothesis count and strata support.
### Q. Code map
Extend discovery/proof; selectively reuse adaptive research; optional CPCV/cost stress on finalists where justified.
### R. Backward compatibility
Old proof remains readable but is not silently relabeled V2.
### S. Tests
Holdout isolation, purge, candidate reconstruction, multiple-testing trap, outlier dominance, unstable years, no meaningful winner, synthetic blocker.
### T. GREEN
Selection cannot see holdout; proof gates causal/statistically explicit; regressions/CI.
### U. Rollback
Keep V2 inactive.
### V. Observability
Split/run/candidate/prune/blocker metrics.
### W. Performance
Cache session simulations; staged grid; deterministic parallel reduction.
### X. Safety
Proof cannot authorize execution.
### Y. Uncertainties
Minimum samples/effect size/multiplicity method are versioned research-policy decisions, not magic constants.
### Z. Checklist
V2 schema → causal dataset → registered grid → split/purge → metrics/intervals → multiplicity/outlier/drift → tests → CI.

### BUILD-8 mandatory variant-coverage rule

Every preserved ORB variant in Section 47 must end in one explicit state, never silently disappear:

`NOT_IMPLEMENTED`, `DATA_UNAVAILABLE`, `RESEARCH_CANDIDATE`, `REJECTED_BY_PROOF`, `CHALLENGER`, `PROOF_ELIGIBLE`, `PROMOTED`, `RETIRED`, `INVALIDATED`.

The exact 50-row review table in Section 50 is a **registered candidate-rule matrix**, not canonical execution logic. Each row must either be tested or explicitly rejected/unavailable with evidence.

---

# 18. BUILD-9 — Combination / Analog / Historical Memory Brain

### A. Purpose
Learn situations/combinations, not isolated indicators.
### B. Problem
Naive matching can create one-match certainty and correlated duplicate episodes.
### C. Must answer
Which past situations are comparable? Which features match/mismatch/unavailable? How many independent episodes? What outcomes/regimes/uncertainty/drift?
### D. Forbidden
Final guidance or probability without calibrated method.
### E. Current truth
Canonical analog memory already provides bounded, versioned distance, raw-v-independent counts and OOD.
### F. Inputs
Canonical memory corpus + candidate/context/timing/signal/parameter facts + matured labels.
### G. Consumers
BUILD-10,11,12.
### H. Failure propagation
Missing required feature can make query OOD; unmatured records never provide outcome evidence.
### I. Output
`OrbAnalogEvidenceV1` with feature/corpus hashes, raw/independent neighbors, match/mismatch, outcomes, interval, regimes, drift/OOD.
### J. States
`MATCHED/SPARSE/OOD/UNAVAILABLE/ERROR`.
### K. Calculations
Reuse canonical analog distance unless a new metric is separately proven; statistics on independent episodes.
### L. Reasoning
Hybrid deterministic bucket + nearest analog + regime statistics; contradictory outcomes remain visible.
### M. Semantics
Sparse/OOD = abstention, not neutral.
### N. Dynamic
Manifest/corpus version changes explicitly.
### O. Failures
Same session duplicates, overlap, future labels, scale instability, survivorship, feature availability mismatch.
### P. False certainty
Expose independent count/distance/mismatches/interval/OOD.
### Q. Code map
ORB feature view/adaptor over M3.3, not second memory engine.
### R. Backward compatibility
M3.3 memory unaffected.
### S. Tests
Sparse/OOD/overlap/source-sharing/missing features/determinism/replay/performance.
### T. GREEN
PIT corpus and independent counts correct; CI.
### U. Rollback
Disable ORB analog adapter.
### V. Observability
Corpus/query/manifest hashes + bounded matches.
### W. Performance
Pre-index/cache; bounded top-N; no unbounded D6 scan.
### X. Safety
Memory cannot set final band/execute.
### Y. Uncertainties
Feature manifest/scales are proof questions.
### Z. Checklist
Manifest → adapter → independence → stats → sparse/OOD → drift → tests → CI.

---

# 19. BUILD-10 — Per-Instrument Playbook Compiler / Promotion Brain

### A. Purpose
Turn only sufficiently proven research into immutable, versioned playbooks.
### B. Problem
Legacy playbook is narrower and cannot bind full profile/context/variant/rule/proof identity.
### C. Must answer
Which proven timing/signal/parameter/context/variant rules apply? Is identity current? Why promote/degrade/retire?
### D. Forbidden
Live mutation, proof waiver, auto-promotion from recent paper wins.
### E. Current truth
Existing proof-to-playbook promotion seam should be extended.
### F. Inputs
BUILD-2,5,6,7,8,9 + governance review.
### G. Consumers
BUILD-11,12,13.
### H. Failure propagation
Profile/proof/version mismatch => not active.
### I. Output
`OrbPlaybookV2`: instrument/contract/session, source TF, OR/clock/confirm, supported signal/variant IDs, context rules, candidate dependency, entry/invalidation/stop/target/RR/no-chase/cutoff/hold/reentry/cost, proof metrics/uncertainty/failures/drift and all hashes.
### J. States
`RESEARCH_ONLY→CHALLENGER→PROOF_ELIGIBLE→PROMOTED→ACTIVE→DEGRADED→RETIRED`; `INVALIDATED` terminal for broken identity.
### K. Calculations
Validation + canonical hash only.
### L. Reasoning
Promotion FOR/blockers recorded; deterministic governance.
### M. Semantics
ACTIVE = eligible evidence producer only.
### N. Dynamic
Lifecycle can change; playbook content under same hash cannot.
### O. Failures
Silent mutation, cross-contract reuse, stale profile, stale model, duplicate active incompatible playbooks.
### P. False certainty
Known failure modes/proof bounds preserved.
### Q. Code map
Versioned successor + compatibility reader + lifecycle events.
### R. Backward compatibility
V1 store never rewritten in place.
### S. Tests
Hash binding, active uniqueness, profile mismatch, lifecycle, immutability, migration, authority.
### T. GREEN
Only fully bound proof can activate; CI.
### U. Rollback
Disable V2 activation.
### V. Observability
Lifecycle/proof/profile/rule hashes and reasons.
### W. Performance
Offline compile; indexed runtime lookup.
### X. Safety
Playbook contains no broker credential/authority.
### Y. Uncertainties
Operator review/signature policy.
### Z. Checklist
Schema → compatibility → compiler → lifecycle → activation lookup → shadow → tests → CI.

---

# 20. BUILD-11 — ORB Evidence Package + AFRE/D6 Integration Brain

### A. Purpose
Translate ORB findings into rich evidence, not a buy/sell score.
### B. Problem
Legacy guidance contains placeholders and weighted-score adaptation that loses epistemic detail.
### C. Must answer
What did ORB find FOR/AGAINST? What is unknown/unavailable/stale/invalidated? What dependencies/correlation families exist? What proof/playbook/rule identity applies?
### D. Forbidden
Final WAIT/WATCH/PAPER-CANDIDATE, execution, D6 override.
### E. Current truth
DecisionContext, stage-2 integrity, ORB guidance and M4 receipt design are migration seams.
### F. Inputs
BUILD-1..10 + D1/D2/M3 canonical receipts + optional proven ML.
### G. Consumers
AFRE/M4/D6, paper guidance display, replay/audit.
### H. Failure propagation
Snapshot mismatch/integrity hard blocker blocks package; unavailable remains explicit; N/A separate.
### I. Output
`OrbEvidencePackageV1` including candidate, identity, clock/TF, boundary facts, prior session, context/hypotheses, variant/rule IDs, timing proof, signal, parameters, proof, analogs, playbook, optional ML, FOR/AGAINST/UNKNOWN/blockers/conflicts/invalidation/dependencies/freshness/uncertainty/provenance.
### J. States
`ASSEMBLING→VALIDATED→AVAILABLE`; or `DEGRADED/CONFLICTED/UNAVAILABLE/BLOCKED_INTEGRITY/ERROR`.
### K. Calculations
Only evidence identities/graph closure/freshness/package hash; no market recalculation.
### L. Reasoning
Dependency graph prevents vote inflation; contradiction remains visible.
### M. Semantics
ORB: “Here is what I found.” AFRE/D6: “What does it mean together?”
### N. Dynamic
Snapshot evidence changes; proof/playbook fixed.
### O. Failures
Neutral placeholders, cross-snapshot evidence, D6 side feeding backward, correlation inflation, ORB self-promotion.
### P. False certainty
Uncertainty vector, no generic `confidence=87%`.
### Q. Code map
Evidence package + DecisionContext/M4 adapter; shadow current guidance.
### R. Backward compatibility
Emit old and new adapters side-by-side until intentional differences are proven.
### S. Tests
Placeholder elimination, snapshot, conflicts, N/A, dependencies, D6 independence, symmetry, replay, size/performance.
### T. GREEN
No fake neutral; all facts traceable; D6 sole finalizer; CI.
### U. Rollback
Select legacy guidance adapter.
### V. Observability
Package hash, evidence counts/families/availability/blockers/conflicts.
### W. Performance
Bounded evidence graph; no historical scan.
### X. Safety
Reject `may_execute=true`, unauthorized final band or broker fields.
### Y. Uncertainties
Integrate to locked M4 schema when implemented, not stale planning assumptions.
### Z. Checklist
Schema → validator → dependency graph → adapter → shadow → placeholder removal → tests → CI.

---

# 21. BUILD-12 — Calibrated ML / Champion-Challenger Brain

### A. Purpose
Add predictive evidence only when a narrow causal label problem demonstrates stable unseen-data value.
### B. Problem
Opaque AI confidence would create false authority.
### C. Must answer
For a named event/horizon, does model beat simple baseline with acceptable calibration/OOD/drift behavior?
### D. Forbidden
Generic BUY/SELL, causal claims from correlation, online self-training, final band.
### E. Current truth
Adaptive forecasting already contains narrow chronological label/calibration patterns.
### F. Inputs
Mature labels + PIT feature manifest + frozen dataset/profile/playbook/code versions.
### G. Consumers
BUILD-11 and offline feedback.
### H. Failure propagation
Censored/unmatured excluded; OOD=>no probability; drift/calibration failure disables/downgrades.
### I. Output
`OrbPredictiveEvidenceV1` with event/horizon/probability or expected-R, interval, support, train/cal/test ranges, hashes, baseline comparison, calibration/OOD/drift.
### J. States
`REGISTERED→TRAINED→CALIBRATED→HELDOUT_TESTED→CHALLENGER→CHAMPION`; or `REJECTED/DEGRADED/RETIRED`.
### K. Calculations
Brier/log-loss/calibration curves/ECE, appropriate precision/recall/economic utility; chronological split + purge/embargo.
### L. Reasoning
ML is one predictive evidence family with explicit counter-evidence.
### M. Semantics
Probability always names event+horizon+basis.
### N. Dynamic
Champion changes only through revalidation.
### O. Failures
Leakage, repeated test reuse, random split, calibration overfit, sparse per-instrument model, distribution shift.
### P. False certainty
Reject complexity with no stable incremental value.
### Q. Code map
Adapt existing forecasting/governance; no LLM authority.
### R. Backward compatibility
Deterministic ORB works without ML.
### S. Tests
PIT features, label maturity, split, calibration, baseline, OOD, code hash, drift, authority.
### T. GREEN
A declared model adds stable test value or BUILD-12 is explicitly rejected/no-value.
### U. Rollback
Disable model artifact.
### V. Observability
Model/support/OOD/drift/calibration/latency.
### W. Performance
Offline train; bounded batch runtime inference.
### X. Safety
No self-modification, D1/AFRE/D6 bypass.
### Y. Uncertainties
Model family intentionally deferred.
### Z. Checklist
Target→labels→features→baseline→challenger→calibrate/test→review→adapter→tests→CI or reject.

---

# 22. BUILD-13 — Paper Guidance / Outcome Maturation / Feedback Brain

### A. Purpose
Connect immutable online evidence to later truth without contaminating the original decision.
### B. Problem
Existing lifecycle is strong but needs generic session/contract/label/drift semantics.
### C. Must answer
Fill? Stop/target/time outcome? Mature? Ambiguous/censored? Costs? Halt/roll/gap-through? Eligible for learning?
### D. Forbidden
Rewrite original evidence/playbook; auto-promote; route live order; pending=loss/win.
### E. Current truth
Lifecycle validates identity, closed observations, same-bar conservative behavior and MFE/MAE/R; feedback is reduce-only.
### F. Inputs
BUILD-11 ticket/package, human paper approval, ledger, future closed observations, profiles/cost metadata.
### G. Consumers
Offline BUILD-8/9/12 and playbook degradation review.
### H. Failure propagation
Missing future bars/halt/roll ambiguity => pending/censored/unknown, not zero.
### I. Output
`OrbMaturedOutcomeV2` with source IDs/hashes, label contract/horizon, fill/exit, ambiguity, MFE/MAE/gross/net R/cost, maturity and integrity.
### J. States
`ISSUED→HUMAN_APPROVED→PENDING_TRIGGER→OPEN→COMPLETED`; or `NO_FILL/CENSORED/UNKNOWN/INVALIDATED_DATA`.
### K. Calculations
Profile-aware fill/cost/MFE/MAE/R; explicit same-bar and session-flat rules.
### L. Reasoning
Outcome never changes what was knowable earlier.
### M. Semantics
PENDING != failure; NO_FILL != NO_SETUP.
### N. Dynamic
Label contract frozen per ticket.
### O. Failures
Future leak, duplicate, missing ticket, roll, halt, gap-through, late correction, cost omission.
### P. False certainty
Censored/ambiguous retained; independent completed episodes counted separately.
### Q. Code map
Versioned lifecycle/feedback extension; no destructive row rewrite.
### R. Backward compatibility
V1.94 rows immutable/readable.
### S. Tests
Pending/mature, no-fill, gap-through, same-bar, roll, session close, costs, orphan/hash, future, idempotency, reduce-only.
### T. GREEN
Online cannot see outcomes; matured labels bind identity; feedback no auto-upgrade; CI.
### U. Rollback
Use V1 lifecycle.
### V. Observability
Outcome/maturity/censored/orphan/integrity counts.
### W. Performance
Incremental/idempotent; bounded horizon.
### X. Safety
Human approval; simulation only; no broker order.
### Y. Uncertainties
Commodity settlement/roll label details depend on BUILD-2 policy.
### Z. Checklist
V2 schema→profile-aware lifecycle→compatibility→offline export→drift→tests→CI.

---

# 23. BUILD-14 — Adversarial System / Replay / CI / Shadow Lock

### A. Purpose
Prove the integrated system under normal, edge and hostile conditions.
### B. Problem
Happy-path tests do not prove causality, generic sessions, research honesty, source coverage or authority.
### C. Must answer
Can future data alter past outputs? Are mirrors symmetric? Are missing/corrupt/stale states truthful? Do all old requirements have a disposition? Is runtime bounded? Can authority escalate?
### D. Forbidden
Waive an invariant because performance is profitable; call GREEN without exact-head evidence.
### E. Current truth
Legacy ORB tests + AFRE/Decision Spine replay/authority tests form baseline.
### F. Inputs
Locked BUILD artifacts, source requirement manifest, representative stock/commodity fixtures, exact versions/hashes.
### G. Consumers
Activation/release/status docs.
### H. Failure propagation
Any causal/authority/source-coverage invariant failure blocks lock. Optional ML failure disables ML unless shared facts are corrupt.
### I. Output
`OrbSystemVerificationManifestV1` including exact SHA, stage hashes, requirement coverage hash, test categories/results, replay/shadow hashes, performance and CI run evidence.
### J. States
`PLANNED→IN_PROGRESS→AMBER/GREEN→LOCKED`; invariant violation=`BLOCKED`.
### K. Calculations
Semantic/hash equality and benchmark distributions only.
### L. Reasoning
Adversarial cases are counter-hypotheses against causal/safe/deterministic/statistically-honest claims.
### M. Semantics
Only evidence-backed exact-head GREEN/LOCK permits next migration seam.
### N. Dynamic
Hardware timings may vary; causal/authority requirements do not.
### O. Failures
Clock randomness, cache contamination, shadow data mismatch, skipped unknowns, prior-head CI, incomplete source manifest.
### P. False certainty
Publish skips/failures/fixture scope and CI SHA/run IDs.
### Q. Code map
Test/fixture/shadow/verification tooling; runtime defects return to owning stage.
### R. Backward compatibility
Legacy goldens remain until each intentional diff is approved/proven.
### S. Tests
Causality, symmetry, data failure, session, commodity, research, evidence, authority, replay, performance and requirement-coverage tests.
### T. GREEN
Stage tests + full regression + causal/replay/authority/performance + requirement coverage 100% + docs + exact-head CI success + zero invariant violation.
### U. Rollback
Rollback latest migration seam; preserve immutable audit/research history.
### V. Observability
One verification manifest per SHA.
### W. Performance
Morning path no historical grid; offline path checkpoint/cache; correctness never traded for speed.
### X. Safety
Permanent no-execution/no-routing/human-approval assertions.
### Y. Uncertainties
Hardware-specific SLO set by measured baseline.
### Z. Checklist
Master fixtures→coverage test→causal/symmetry/data/session/commodity/research/evidence→replay→shadow→performance→authority→full tree→exact-head CI→lock.

---

## 24. Cross-stage Calculation Registry

Any implementation must resolve canonical owner before adding code.

| Name | Canonical/target owner | Definition / units | Warm-up / PIT / missing rule | Main consumers |
|---|---|---|---|---|
| typical price | D2 feature kernel | `(H+L+C)/3`, price | closed bar; invalid OHLC=ERROR | VWAP/profile |
| gap | BUILD-4 from BUILD-3 | `(open-prior_reference)` and `%` | both causal; missing prior=UNAVAILABLE | context/analogs |
| true range | canonical price | `max(H-L,|H-Cprev|,|L-Cprev|)` | previous close required | ATR |
| Wilder ATR(n) | canonical price | Wilder recursive ATR, price | full seed; insufficient history explicit | context/buffers |
| CPR | canonical level/context | P/BC/TC from completed prior HLC | prior session complete | context |
| CPR width | canonical level/context | `|TC-BC|`, price / % / ATR | CPR + denominator available | context |
| PDH/PDL/PDC | BUILD-3 adapter | prior completed H/L/C | trusted/degraded fact state | context/signal |
| ORH/ORL | BUILD-6 | max/min fully closed bars inside exact OR interval | only after OR lock; missing interval=PENDING/INCOMPLETE | signal |
| ORM | BUILD-6 | `(ORH+ORL)/2` | range locked | signal/parameter |
| OR width | BUILD-6 | `ORH-ORL` | range locked | timing/context |
| OR width / ATR | BUILD-6 | `ORW/ATR` | ATR >0 and available | timing/context |
| opening-range VWAP | existing/core fact adapter | VWAP only over OR slice | missing volume=UNAVAILABLE | legacy/regression |
| session VWAP | canonical value calc | cumulative session TPV/volume | closed bars; missing required volume=UNAVAILABLE | context |
| PDC-anchored VWAP | research candidate | registered anchor semantics | only if proven/source valid | context candidate |
| daily/weekly VWAP | canonical indicator/value owner | registered daily/weekly trading anchors | no naive week/day grouping | context |
| VWAP ±1/2/3 deviation bands | canonical value owner | registered volume-weighted dispersion version | volume required | context/targets |
| Bollinger | indicator registry canonical output | versioned SMA/std bands | registry warm-up | context |
| Bollinger width | canonical indicator | band width/raw + normalized version | valid middle/owner semantics | compression |
| RVOL | BUILD-4 volume context | current/same-time historical baseline, versioned | minimum history; missing volume explicit | context/signal research |
| breakout buffer | BUILD-7 parameter model | frozen policy function | all required inputs available | signal/entry |
| distance bps | canonical level utility | signed `(price-level)/level*10000` | level>0 | context/analog |
| distance ATR | canonical level utility | signed `(price-level)/ATR` | ATR>0 | context/analog |
| boundary location | BUILD-6 | deterministic geometry relative OR/levels | closed bar | signal |
| MAE/MFE | BUILD-13/8 | side-aware max adverse/favorable excursion | matured horizon | proof/feedback |
| R multiple | BUILD-13/8 | net directional PnL / strictly positive initial risk | zero risk=INVALID | proof |
| expectancy | BUILD-8 | mean net R + interval separately | eligible independent outcomes only | proof |
| profit factor | BUILD-8 | gains/abs(losses) with no-loss state explicit | unknowns not zero; no fake `999` | proof |
| max drawdown | BUILD-8 | chronological peak-to-trough net-R equity | complete eligible series | proof |
| false-break rate | BUILD-8 | failed-break outcomes / eligible confirmed breaks under frozen horizon | matured events | timing/proof |
| retest success | BUILD-8 | successful frozen retest outcome / eligible retest attempts | matured events | timing/playbook |
| analog similarity | M3.3 owner | `1-weighted_normalized_distance` under manifest | PIT corpus/support | memory |
| uncertainty | BUILD-8/12 | method-specific vector/interval, never generic scalar | support required | proof/ML |
| drift | BUILD-8/12/13 | versioned performance/calibration/feature-shift vector | later offline only | lifecycle |

Old review thresholds tied to any calculation are stored in the Research Rule Registry, not hidden inside formulas.

---

## 25. Main Contract Matrix

| Contract | Producer | Consumers | Authority |
|---|---|---|---|
| `OrbRequirementManifestV1` | B0 | all/CI | audit only |
| `OrbBaselineManifestV1` | B0 | all/CI | audit only |
| `OrbCandidateIntakeV1` | B1 | 2,4,8,9,11 | evidence only |
| `OrbMarketIdentityV1` | B2 | 3-14 | identity gate only |
| `OrbCompletedSessionV1` | B3 | 4,5,8,9 | fact only |
| `OrbContextWorldV1` | B4 | 5,6,7,9-12 | evidence only |
| `OrbClockTimeframeStateV1` | B5/runtime | 6,11 | fact only |
| `OrbTimingResearchArtifactV1` | B5 | 6,8,10 | research only |
| `OrbBoundaryLocationV1` | B6 | 6,9,11 | derived fact only |
| `OrbSignalEventV1` | B6 | 7-11 | evidence only |
| `OrbParameterSetV1` | B7 | 8,10,11,13 | paper/research hint only |
| `OrbResearchRuleCandidateV1` | B0/8 registry | 4-8/10 | no authority until proof |
| `OrbProofReportV2` | B8 | 10-12 | proof gate only |
| `OrbAnalogEvidenceV1` | B9 | 10-12 | memory evidence |
| `OrbPlaybookV2` | B10 | 11-13 | evidence eligibility |
| `OrbEvidencePackageV1` | B11 | AFRE/D6 | evidence only |
| `OrbPredictiveEvidenceV1` | B12 | 11/D6 | predictive evidence only |
| `OrbMaturedOutcomeV2` | B13 | offline 8/9/12 | feedback only |
| `OrbSystemVerificationManifestV1` | B14 | release/lock | audit only |

---

## 26. Upstream / Downstream and top-down constraint matrix

| Stage | Hard upstream | Main downstream | Top-down constraint that may limit use but never rewrite fact |
|---|---|---|---|
| 0 | repo/source truth | all | safety/authority/source ledger |
| 1 | source records | 2/4/8/9/11 | selection policy |
| 2 | candidate identity + official registry | 3-14 | supported venue/product policy |
| 3 | 2 + D1/D2 bars | 4/5/8/9 | session/profile semantics |
| 4 | 1-3 + M3 | 5/6/7/9-12 | applicability/playbook evidence rules |
| 5 | histories 1-4 | 6/8/10 | registered search policy |
| 6 | 2/4/5 + closed bars | 7-11 | frozen signal definition |
| 7 | 4-6 histories | 8/10/11 | registered parameter families |
| 8 | 1-7 | 9/10/12 | proof/split/multiplicity policy |
| 9 | 1/2/4/6 + matured memory | 10-12 | feature manifest/corpus cutoff |
| 10 | 2/5-9 | 11-13 | promotion policy |
| 11 | 1-10 | AFRE/D6 | authority/epistemic contract |
| 12 | 8/10/13 | 11 | ML governance |
| 13 | 2/10/11 + human approval | offline | label contract/safety |
| 14 | 0-13 | release | GREEN/LOCK protocol |

D6 preference can never flow downward to change evidence.

---

## 27. Evidence dependency and correlation design

Evidence node fields:

`fact_id`, `producer`, `source_hash`, `dependencies`, `family`, `epistemic_level`, `availability`, `observed_at`, `available_at`, `version`.

Families: `price_action`, `trend`, `momentum`, `volatility`, `volume`, `market_structure`, `levels`, `value_vwap`, `benchmark`, `sector`, `derivatives_oi`, `event`, `candidate_selection`, `historical_analog`, `deterministic_proof`, `predictive_ml`, `data_quality`, `session_contract`.

Rules:

1. descendants do not create independent sample count;
2. CPR and previous-close location declare shared ancestry;
3. VWAP variants declare common volume/price ancestry and distinct anchors;
4. same-session or overlapping analog outcomes are not independent episodes;
5. contradiction is an edge, not a value averaged to zero;
6. unavailable/N-A evidence is excluded with its state, not treated as a vote.

---

## 28. Authority matrix

| Engine/stage | Observe | Calculate | Infer | Predict | Evidence | Local invalidate/veto own output | Final guidance | Execute |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | Y | audit | system only | N | audit | Y | N | N |
| B1 | Y | Y | validity | N | Y | candidate only | N | N |
| B2 | Y | Y | identity | N | Y | identity only | N | N |
| B3 | Y | Y | trust | N | Y | fact eligibility | N | N |
| B4 | Y | Y | Y | no by default | Y | hypothesis only | N | N |
| B5 | Y | Y | research | research stats | Y | research candidate | N | N |
| B6 | Y | Y | event state | N | Y | signal only | N | N |
| B7 | Y | Y | applicability | offline stats | Y | parameter set | N | N |
| B8 | Y | Y | proof | stats | Y | proof eligibility | N | N |
| B9 | Y | Y | analog | no unless calibrated | Y | analog/OOD | N | N |
| B10 | Y | Y | governance | N | Y | lifecycle | N | N |
| B11 | Y | graph/hash | synthesis | N | Y | ORB package only | N | N |
| B12 | Y | Y | Y | Y bounded | Y | model only | N | N |
| B13 | Y | Y | label eligibility | offline only | Y | label only | N | N |
| AFRE | Y | Y | Y | bounded | Y | registry-bounded | N | N |
| D6 | Y | Y | Y | consumes predictions | Y | Y | **Y** | N |

---

## 29. Availability / epistemic matrix

Canonical target states:

`AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `UNKNOWN`, `STALE`, `SUSPECT`, `ERROR`, `NOT_APPLICABLE`, `INSUFFICIENT_HISTORY`, `PENDING`.

| State | Can be converted to neutral numeric? | Can satisfy a required fact? | Default behavior |
|---|---:|---:|---|
| AVAILABLE | only if real measured value is neutral | Y | consume |
| DEGRADED | N | policy dependent | bounded use/downgrade |
| UNAVAILABLE | N | N | abstain/degrade |
| UNKNOWN | N | N | preserve uncertainty |
| STALE | N | normally N | reject freshness-sensitive use |
| SUSPECT | N | normally N | quarantine/review |
| ERROR | N | N | fail closed |
| NOT_APPLICABLE | N | not required by definition | exclude |
| INSUFFICIENT_HISTORY | N | N | warm-up/abstain |
| PENDING | N | N now | wait |

Epistemic levels: `OBSERVED`, `DERIVED`, `INFERRED`, `HYPOTHESIS`, `PREDICTIVE`. Downstream code cannot promote an epistemic level by relabeling it.

---

## 30. Stock vs Commodity matrix

| Capability | NSE equity | NSE derivative | Commodity raw contract | Continuous research series |
|---|---|---|---|---|
| sector | usually available | underlying-dependent | often N/A | often N/A |
| corporate action | applicable | underlying may matter | N/A | N/A |
| NSE CPR/cash prior | profile-defined | only if explicitly bound | N/A unless defined | N/A unless defined |
| contract expiry | N/A cash | important | critical | raw constituent metadata required |
| settlement vs close | profile-defined | profile-defined | critical | source basis explicit |
| roll/OI migration | N/A cash | applicable | critical | critical |
| continuous adjustment | N/A | optional | N/A raw | critical and versioned |
| benchmark | Nifty/sector | underlying/index | commodity/global/FX if registered | same |
| cross-date session | no regular cash | segment-specific | possible | inherits raw semantics |
| partial holiday | calendar | calendar | often important | same |
| tick/multiplier/lot | metadata | contract metadata | critical | source raw contract |
| inventory/macro event | optional | optional | often relevant | same |

Stock-only rules never silently bleed into commodity logic.

---

## 31. Research/runtime separation and efficiency

Runtime may bind identity, build canonical causal facts, load frozen artifacts, update signal state on newly closed bars, query bounded analog memory, assemble evidence and call AFRE/D6.

Runtime must not grid-search, refit models, mutate a playbook, use today’s future outcome, or scan an unbounded corpus.

Offline may run registered discovery, timing/parameter research, WF/holdout/CPCV stress where chosen, analog corpus building, model training/calibration, label maturation and challenger research.

Efficiency requirements:

- compute prior-session context once per session, not per combination;
- compute RVOL baselines once per symbol/time bucket/version, not per candidate;
- cache immutable features by content hashes, never mutable symbol-only keys;
- checkpoint long runs and resume by immutable cell/fold identity;
- stage search: cheap/prior proven dimensions first, joint expansion only for survivors;
- no O(N²) combination explosion without pruning/bounds;
- benchmark first, then set numeric SLO. Historical “<100 ms context/symbol-day” is retained as an old target to rebaseline, not promised as current hardware truth.

---

## 32. Historical memory / analog and ML governance

Memory:
- corpus cutoff must be causal;
- only matured labels count as outcomes;
- raw rows != independent episodes;
- sparse/OOD abstains;
- similarity != probability.

ML:
- deterministic label contract first;
- PIT features;
- chronological train/calibration/test;
- purge/embargo when overlap requires;
- untouched final test;
- simple baseline first;
- probability calibration + OOD/support + drift;
- immutable champion/challenger artifacts;
- disable model on binding/calibration/drift failure;
- never bypass D1/AFRE/D6.

---

## 33. Replay identity

A replay key must bind at least:

```text
input_data_snapshot_hash
candidate_intake_hash
instrument_profile_hash
session_profile_hash
contract_profile_hash
calendar_version/hash
previous_session_hash
calculation_versions
context_world_hash
clock/timeframe artifact version
boundary/signal rule version
parameter_set_hash
proof_hash
variant/rule-registry version
analog manifest + corpus cutoff/hash
playbook_hash
model_hash if used
configuration/policy hash
code fingerprint where decision-relevant
```

Historical replay uses historical effective registry rows, not latest rules.

---

## 34. Adversarial master test matrix

Mandatory classes include:

- future bar cannot alter past result;
- label cannot leak into feature;
- incomplete bar cannot transition signal;
- candidate intake reconstructs selection PIT-safe;
- bullish/bearish mirrors and symmetric reversal where intended;
- missing volume/prior session/benchmark/event;
- zero range, duplicates, out-of-order, bad ticks, stale/hash mismatch;
- holiday/special NSE, cross-date commodity, break, timezone;
- raw/continuous mismatch, expiry, roll, OI migration, settlement/close, illiquidity/limits;
- low sample, overfit, edge decay, year instability, multiple testing, one-outlier dominance, no meaningful winner;
- support + contradiction, correlated families, N/A, unavailable, invalidated/stale signal;
- every ORB/ML/memory engine `may_execute=false` and D6 sole final band;
- identical replay identity -> identical outputs;
- cache isolation/performance on realistic candidate/history volumes;
- requirement manifest source-hash drift/unmapped-line failure.

---

## 35. Migration map

| Existing component | Migration action |
|---|---|
| `orb/hstry_csv.py` | WRAP → generic data/session adapter; preserve NSE tests |
| `orb/context.py` | KEEP as starting point/reference; migrate calculations to canonical owners; no generic calendar-day resample |
| `orb/timing_research.py` | EXTEND; preserve checkpoint/legacy timing fixtures |
| `orb/core.py` | WRAP → SHADOW → migrate range facts/signal/parameters by seam |
| `orb/discovery.py` | EXTEND generic sessions/registered search/caches |
| `orb/proof.py` | EXTEND V2 causal/statistical proof; compatibility reader |
| `orb/adaptive/*` | REUSE selectively; generalize NSE clock assumptions before generic use |
| `behavior/orb_guidance.py` | WRAP → SHADOW → evidence package; eliminate fake-neutral defaults after proof |
| `final_confluence_arbiter.py` | DO NOT ORB-REWRITE; M4 owns D6 redesign |
| `authority_registry.py` | register new engines only with zero execution; preserve sole final authority |
| `stage2_integrity.py` / `decision_context.py` | reuse/versioned adapter for richer availability |
| `snapshot_feature_kernel.py` | reuse primitive substrate |
| `canonical_session_intelligence.py` | keep NSE adapter until generic profile migration |
| canonical price/context/level/indicator/memory | reuse; no duplicate ORB calculators |
| `data_quality.py` | wrap/generalize after session profile exists |
| `point_in_time_guard.py` | keep; extend explicit `available_at` semantics as needed |
| `market_structure_liquidity.py` | compatibility only where semantic defaults are unsafe; prefer canonical M3 successors |
| paper lifecycle/feedback | extend versioned; preserve existing rows/identity |
| ORB models/contracts | version; no silent serializer break |

---

## 36. GREEN / LOCK protocol

Allowed states: `PLANNED`, `IN_PROGRESS`, `BLOCKED`, `AMBER`, `GREEN`, `LOCKED`.

A BUILD becomes GREEN only if implementation, stage tests, causality, replay, relevant legacy regressions, authority, required performance, docs/status and exact-head CI all pass and no invariant violation remains.

Additionally after this re-audit:

```text
requirement_coverage == 100%
unmapped_target_requirements == 0
unexplained_source_hash_drift == 0
unresolved_authority_invariant_conflicts == 0
```

A `CONFLICT_NEEDS_PROOF` threshold is allowed if it is intentionally registered as a research grid candidate and cannot activate without proof. A hidden conflict is not allowed.

---

## 37. Exact implementation order

```text
0  requirement manifest + current baseline + golden fixtures
1  candidate intake/provenance
2  instrument/session/contract registry
3  prior completed session reconstruction
4  canonical context/hypotheses
5  clock/OR-duration/confirmation-TF research
6  boundary facts + explicit signal lifecycle
7  parameter/invalidation/paper-risk research
8  V2 discovery/WF/holdout proof + variant/rule coverage
9  ORB analog-memory view
10 playbook V2 compiler/lifecycle
11 ORB evidence package + shadow AFRE/D6 adapter
12 calibrated ML only if incremental value is proven
13 outcome V2/offline feedback
14 integrated adversarial/replay/performance/source-coverage lock
```

Every step: implement one stage → targeted/adversarial/replay → relevant legacy regression → full tree → authority audit → exact-head CI → GREEN/LOCK → next.

---

# 38. Source-reconciliation result: what the first master plan had missed or under-specified

The following items are now explicitly restored:

1. requirement-level traceability rather than topic-only coverage;
2. exact 18-variant registry plus ORB-10/20 timing additions;
3. exact A–G failure taxonomy and research measure vocabulary;
4. derivatives/OI overlay and threshold priors with PIT states;
5. exact 50-row external-review decision-table candidates;
6. complete ranked top-10 additions, including previously omitted #8–#10;
7. legacy NSE timing v1.97 windows and 72-combo research provenance;
8. legacy candle-pattern inventory and priority baseline;
9. explicit Clock/Timeframe fact contract;
10. explicit Inside/Outside/Touch/Straddle boundary fact classifier;
11. legacy current thresholds separated from future canonical formulas;
12. CPR algebraic dependency/non-independence law;
13. context D-1 proof-slicing leakage risk and precompute requirement;
14. dual-source context mismatch hard error;
15. data-gated-feed law: missing feed cannot create an authoritative veto/size/permission;
16. stop-rule/backtest-vs-runtime parity as a proof requirement;
17. signal-slot accounting before re-entry;
18. separate afternoon playbook/statistics and level-staleness rule;
19. historical narrow gap-morning review profile separated from the generic target;
20. Discover ≠ Prove ≠ Playbook ≠ Decide ≠ Paper architectural separation;
21. old 30/60 sample, VIX, OR-width and other threshold disagreements preserved as research conflicts rather than silently “resolved”;
22. source-hash invalidation and dynamic requirement audit design.

---

# 39. Legacy NSE regression profile and historical experiment profiles

### 39.1 `LEGACY_NSE_ORB_PROFILE`

This profile exists to prevent accidental regression while generic architecture is built. It contains current code/test behavior verified in BUILD-0; it is **not** the generic stock/commodity target.

### 39.2 `TIMING_V197_PROFILE`

Historical approved research provenance:

- default 5m sweep across requested symbols;
- 1m refinement historically targeted to top-20 composite symbols;
- clock endpoints 09:20/09:30/09:35/09:40;
- families breakout/reversal/hybrid;
- historical RR `[1,2,3]` × volume `[False,True]`, yielding 72 combinations per symbol for that plan;
- explicit/Trendforge-latest symbol source;
- checkpoint/resume and deterministic export requirements.

The target BUILD-5 expands beyond this; it must still preserve regression/replay compatibility with these old research artifacts.

### 39.3 `GAP_MORNING_REVIEW_PROFILE`

The old gap-morning external-review brief intentionally narrowed its game to gap-up/down NSE stocks, early session, max one position/day, CPR as confirming vote and no afternoon trades. That is a **historical experiment/review scope**, not the new generic architecture. Its useful constraints become research candidates; they do not forbid the separately proven AFT playbook or commodities.

### 39.4 historical evidence disclaimer

Old claims such as `740/740`, historical BEL performance, old gap/CPR NO-GO results and day-type predictor results are retained as `HISTORICAL_EVIDENCE`. They must be re-bound to exact dataset/code/proof artifacts before current promotion or CI claims use them.

---

# 40. Research Rule Candidate contract

All retained review/memorandum thresholds live in a typed research registry, not scattered `if` statements.

`OrbResearchRuleCandidateV1`:

```text
rule_id
source_document
source_blob_hash
source_section
rule_family
condition_definition
threshold_parameters
units
applicable_instrument_profiles
required_inputs
required_feed_ids
availability_policy
candidate_measure
counter_measure_or_no_action
causal_availability_rule
status
proof_id
playbook_ids
conflicts_with_rule_ids
supersedes_rule_ids
notes
```

Candidate statuses:

`ARCHIVED_PRIOR`, `DATA_UNAVAILABLE`, `REGISTERED_FOR_RESEARCH`, `REJECTED_BY_PROOF`, `CHALLENGER`, `PROOF_ELIGIBLE`, `PROMOTED`, `DEGRADED`, `RETIRED`, `INVALIDATED`.

No `ARCHIVED_PRIOR` or `DATA_UNAVAILABLE` rule can gate D6 or modify paper sizing.

---

# 41. Exact preserved ORB Variant Registry — 18 variants

All 18 must be accounted for in BUILD-8. Entry/stop/target notes below are **external-review research priors**, not canonical truths until proof.

| ID | Variant | Preserved candidate behavior / research question |
|---|---|---|
| V01 | Classic ORB-15 | closed-bar ORH/ORL breakout; study buffer, opposite-side/conditional stop, ~2R/time-flat candidates |
| V02 | ORB-5 micro | 5-minute range, early trigger; study noise/spread and shorter target |
| V03 | ORB-30 | 30-minute range; study post-event clarity vs late trigger |
| V04 | Volume-confirmed ORB | add same-time RVOL/volume confirmation; quantify trade-count/false-break tradeoff |
| V05 | VWAP-filtered ORB | test session-VWAP side filtering; distinguish early near-vacuous VWAP from later value acceptance |
| V06 | Index-aligned ORB | index/benchmark alignment as conditional evidence; stock-specific news exemption research |
| V07 | Narrow-OR expansion | compression/NR7/CPR/OR-width expansion hypothesis; correlated ancestry must be controlled |
| V08 | Wide-OR reduced | reduced-risk/target or skip policy on wide OR; threshold is research candidate |
| V09 | Gap-and-go | continuation gap/pullback-hold hypothesis |
| V10 | Gap-fade / ORR | extreme/exhaustion gap failing back toward PDC/value |
| V11 | False-breakout reversal / trap | failed break returning inside quickly; trap/reversal state |
| V12 | Pullback retest | first retest hold after confirmed break |
| V13 | Second-chance re-entry | max-one retry candidate after trap-like stop; signal-slot state required |
| V14 | Post-result ORB | delayed/longer OR after result; event calendar mandatory |
| V15 | PDH/PDL breakout | completed-prior-session level break/reclaim family |
| V16 | Expiry-day ORB | expiry-specific confirmation/target/pinning hypotheses; calendar file required |
| V17 | Afternoon range breakout | separate afternoon playbook/folds; never mix morning OR statistics or stale morning levels |
| V18 | Extension no-chase | abstain when price is already excessively extended without pullback |

Additional target timing research durations `ORB-10` and `ORB-20` are BUILD-5 matrix values, not replacements for V01–V18.

Archived review details such as buffers `0.05–0.1%`, RVOL `1.5×`, ORW/ATR thresholds, 1.5R/2R/2.5R/3R targets or exact event times remain candidate parameters in Section 50/Research Rule Registry until proof.

---

# 42. Exact preserved Failure Scenario Taxonomy

Every item must map to a fact/hypothesis/test/rule candidate or explicit unsupported state.

### A — Regime
- chop day;
- VIX coma `<11` prior;
- VIX spike `20–25` or intraday `ΔVIX +8%` prior;
- gap exhaustion `>1.5×ATR` prior;
- news shock.

### B — Signal
- false breakout;
- OR too wide `>1.0×ATR` prior;
- OR too narrow `<0.25×ATR` prior;
- first-bar contamination;
- setup/level staleness after the historical morning cutoff;
- double-stop whipsaw.

### C — Event
- result-day whipsaw;
- RBI MPC around announcement window;
- Budget/election event risk;
- ex-dividend mechanical gap misread.

### D — Instrument
- circuit lock;
- ASM/GSM/T2T restriction;
- illiquidity/slippage;
- F&O ban.

### E — Data / execution-simulation
- feed lag/bad ticks;
- simulated order rejection/broker square-off assumptions;
- PIT violation;
- backtest/runtime mismatch.

### F — Derivatives
- expiry pinning;
- gamma squeeze;
- OI wall rejection;
- rollover distortion.

### G — Statistical
- edge decay;
- overfit;
- small sample.

Preserved research-measure vocabulary:

`SKIP_DAY`, `DELAY_ENTRY`, `HALF_SIZE`, `TIGHTEN_TARGET`, `WIDEN_STOP`, `FLIP_BIAS`, `VETO_DIRECTION`, `ALERT_ONLY`.

These are **semantic research/guidance effects**, not order commands. `HALF_SIZE` is a paper-risk hint only and requires a promoted parameter/risk policy plus human approval.

---

# 43. Derivatives / OI Research-Prior Registry

Every metric below must carry source, observed/available timestamps, revision policy, applicability and PIT state. No source => `UNAVAILABLE` / experimental `ALERT_ONLY`, never zero/safe.

| Concept | Preserved prior / research state |
|---|---|
| India VIX bands | `<11`, `11–14`, `14–17`, `17–20`, `20–25`, `>25` research grid |
| ΔVIX | `+8%` intraday shock candidate |
| IV Rank | `>60` pre-result prior |
| IV term structure | near > next by `>5 vol pts` prior |
| 25Δ skew | optional index skew evidence |
| post-result IV crush | event-resolution evidence |
| PCR | `>1.3` / `<0.7` extremes prior |
| OI buildup | price↑OI↑ long buildup; price↓OI↑ short buildup; price↓OI↓ long unwind; price↑OI↓ short covering |
| max pain | spot within `≤0.5%` candidate proximity |
| GEX | model-dependent regime evidence only unless validated |
| charm/vanna | expiry-only experimental modifier |
| expiry | calendar-driven weekly/monthly/post-expiry context, never weekday constants |
| rollover | `>85% + positive basis` prior; alternative old thresholds stay conflict candidates |
| basis | `>+15 bps` / negative basis candidate, always dividend/contract adjusted |
| rollover contract | OI migration threshold candidate, versioned |
| GIFT implied gap | `>1.5×ATR` candidate; extreme index-gap `>2.5%` candidate |
| FII index-futures crowding | short `>80%` / `<30%` candidate states |

Old documents contained mutually different VIX/OR-width/rollover/IV/gap priors. Those differences are `CONFLICT_NEEDS_PROOF`, not silently collapsed into “truth”.

---

# 44. Exact 50-row Decision-Table Candidate Registry

This table is restored from the archived consolidated review. **It is not implementation truth.** Every row is an `OrbResearchRuleCandidateV1` and must pass source/data/PIT/proof gates before a playbook may activate it.

| # | Condition | Archived detection prior | Archived research measure |
|---:|---|---|---|
| 1 | VIX coma | VIX `<11` | tighten target `0.8R` / NR7-only candidate |
| 2 | VIX normal | `11–14` | no adjustment candidate |
| 3 | VIX elevated | `14–17` | buffer `×1.25` candidate |
| 4 | VIX high | `17–20` | buffer `×1.5` + half-size candidate |
| 5 | VIX kill zone | `20–25` | skip small/mid; large-cap volume condition candidate |
| 6 | VIX crisis | `>25` | skip-all candidate |
| 7 | vol shock | `ΔVIX +8%` intraday | cancel pending candidate |
| 8 | OR too wide | `ORW >1.0×ATR` | skip-day candidate |
| 9 | OR wide | `0.75–1.0×ATR` | half-size + ORM stop + `1.5R` candidate |
| 10 | OR normal | `0.25–0.75×ATR` | standard candidate |
| 11 | OR narrow | `<0.25×ATR` | volume-hammer + `3R` candidate |
| 12 | compression | NR7 + CPR `<0.2×ATR` | V07 priority candidate |
| 13 | first-bar anomaly | 09:15–09:20 volume z `>4` or range `>2×` median | re-base OR candidate |
| 14 | OR straddles PDC | PDC inside OR | half-size/contested-open candidate |
| 15 | gap extreme | `|gap| >1.5×ATR` | flip-bias/V10 candidate |
| 16 | gap moderate | `0.75–1.5×ATR` | no-chase/pullback-only candidate |
| 17 | flat open | gap `<0.25×ATR` | standard candidate |
| 18 | GIFT/open divergence | difference `>0.3%` | delay `5m` candidate |
| 19 | index gap extreme | GIFT implies `>2.5%` | skip small/mid candidate |
| 20 | ex-dividend | D-1 corporate-action source | adjusted gap = raw + dividend% candidate |
| 21 | Nifty aligned | same side of index OR/VWAP | full-size paper-risk candidate |
| 22 | Nifty conflict | opposite side | direction-veto candidate |
| 23 | Nifty mid-range | index inside own OR | half-size candidate |
| 24 | sector divergence | opposite `>0.5%` | half-size candidate |
| 25 | volume pass | RVOL `≥1.5×` | pass candidate |
| 26 | volume fail | RVOL `<1.0×` | delay until recovery else skip candidate |
| 27 | climax/no follow-through | breakout z `>4`, no progress in 3 bars | scratch/early-exit candidate |
| 28 | post-break dry-up | next 3 bars `<0.7×` OR average volume | tighten/scratch candidate |
| 29 | early signal | `<09:45` NSE historical profile | gap-day half-size else standard candidate |
| 30 | prime window | `09:45–10:45` historical profile | standard candidate |
| 31 | late window | `10:45–11:30` | target `1.5R` candidate |
| 32 | past morning cutoff | `>11:30` | no new morning entry candidate |
| 33 | time stop | `15:10` NSE historical profile | hard paper flat candidate |
| 34 | result day | event calendar | delay to 09:45; 30-min OR; `1.5R` candidate |
| 35 | result D-1 | calendar | tag next-day gap; no size-up candidate |
| 36 | RBI MPC | announcement calendar | 09:45–10:15 blackout + later buffer candidate |
| 37 | Budget/election | calendar | skip or 2× confirmation candidate |
| 38 | weekly expiry | effective calendar | +1 close-confirm candidate |
| 39 | monthly stock expiry | effective calendar | pain rules/no fresh late entries candidate |
| 40 | PCR extreme | `>1.3` or `<0.7` | contrarian soft-veto candidate |
| 41 | max-pain proximity | spot `≤0.5%` from pain | tighten/ORR-bias candidate |
| 42 | OI wall at target | target beyond wall | cap one tick before wall candidate |
| 43 | basis extreme | `>+15bps` or negative adjusted | directional-tilt candidate |
| 44 | FII crowding | short ratio `>80%` / `<30%` | squeeze/crowding tilt candidate |
| 45 | F&O ban | exchange list | skip candidate |
| 46 | ASM/GSM/T2T | exchange list | structural skip candidate |
| 47 | narrow circuit band | `≤10%` short-side prior | short skip candidate |
| 48 | illiquidity | turnover `<₹5cr` or spread `>0.1%` prior | skip candidate |
| 49 | chop signature | 2 failed breaks same side before 11:00 prior | skip remainder candidate |
| 50 | edge decay / sample | 60-day expectancy `<0` twice or `<60` OOS prior | alert-only/demotion candidate |

For commodity instruments, rows with NSE/VIX/Nifty/ASM/F&O semantics are `NOT_APPLICABLE` unless an explicitly registered analogous concept exists. Never transplant them by name.

---

# 45. Ranked Top-10 retained research additions

The repository archive resolves the old parent document’s missing items #8–#10. Preserve the complete ranked list as historical prioritization, not proof:

1. event-calendar gate;
2. universe hygiene filter;
3. session VWAP + side veto;
4. ex-dividend gap adjustment;
5. Nifty-alignment gate;
6. VIX-scaled buffers;
7. conditional re-entry;
8. OI-wall capping + expiry pinning;
9. RVOL filter;
10. expectancy monitor + multiple-testing hygiene.

Implementation order still follows BUILD dependencies, not external-review ranking.

---

# 46. Important old rule conflicts and their canonical disposition

| Old conflict | Correct disposition |
|---|---|
| live context “fail-open + unknown tag” vs target epistemic safety | `SUPERSEDED`: a required canonical fact that is unavailable must cause abstention/degrade according to the playbook; absence never creates permission. Optional context may be skipped explicitly but cannot become affirmative evidence. |
| hard-coded Tuesday/other expiry weekdays | `SUPERSEDED`: versioned exchange calendar/contract registry only. |
| gap-morning “no afternoon” vs later AFT variant | both preserved: narrow `GAP_MORNING_REVIEW_PROFILE` keeps its scope; generic target allows a separately proven afternoon playbook with separate statistics. |
| opening-range VWAP vs session/daily/weekly VWAP | distinct canonical facts/anchors; no substitution. |
| stop at opposite OR vs ORM vs retest/swing/ATR | `CONFLICT_NEEDS_PROOF`; stop mode is an explicit parameter/playbook field and backtest/runtime parity is mandatory. |
| sample `30`, per-regime `10`, OOS `60` | different historical purposes/priors; BUILD-8 policy version names each support gate and proves applicability. |
| VIX/ORW/rollover/IV threshold disagreements | preserve candidate grid/conflict register; no hidden resolution. |
| size/risk percentages from old docs | paper/research candidate only; not execution authority. |
| historical BEL/740-test claims | historical evidence until exact artifacts/SHA are reverified. |
| external-review “full size” / “flip bias” language | semantic evidence/paper-policy candidate; never broker action. |

---

# 47. R1–R105 accumulated-requirement traceability matrix

This restores the parent plan’s 105-requirement discipline. “Owner” indicates where implementation proof must live; cross-cutting requirements also appear in global matrices.

| ID | Requirement | Owner |
|---:|---|---|
| R1 | historical research | B8 |
| R2 | timing variants | B5 |
| R3 | candidate intake | B1 |
| R4 | multidimensional evidence | B4/B11 |
| R5 | long + short semantics | B6 |
| R6 | no-chase | B7 |
| R7 | playback/paper | B13 |
| R8 | proof-backed use | B8/B10 |
| R9 | features calculated once/reusable | architecture/B4 |
| R10 | raw facts first | B3/B4 |
| R11 | facts immutable by interpretation | architecture |
| R12 | canonical formulas | calculation registry |
| R13 | provenance | all |
| R14 | PIT | all |
| R15 | no incomplete bar authority | B6/all |
| R16 | missing != neutral | all |
| R17 | explicit availability | all |
| R18 | hash/identity | all |
| R19 | deterministic replay | all/B14 |
| R20 | correlation/independent evidence | B4/B9/B11 |
| R21 | candidate-scoped intake | B1 |
| R22 | raw→derived→interpretation one-way flow | architecture |
| R23 | per-stage bounded responsibility | B0-B14 |
| R24 | no authority creep | authority matrix |
| R25 | rich context | B4 |
| R26 | true previous exchange session | B3 |
| R27 | gap/open location | B4 |
| R28 | CPR | B4 |
| R29 | daily/weekly/banded VWAP | B4 |
| R30 | Bollinger | B4 |
| R31 | ATR | calc/B4 |
| R32 | volume/RVOL | B4 |
| R33 | candle patterns | B4 |
| R34 | levels | B4 |
| R35 | structure | B4 |
| R36 | liquidity/sweep/trap | B4/B6 |
| R37 | benchmark | B4 |
| R38 | sector | B4 |
| R39 | relative strength | B4 |
| R40 | events | B4 |
| R41 | derivatives/OI | B4 |
| R42 | expiry | B2/B4 |
| R43 | roll/settlement | B2/B3/B4 |
| R44 | commodity exchange session | B2 |
| R45 | OR 5/10/15/20/30 | B5 |
| R46 | confirmation TF 1/3/5/15 | B5 |
| R47 | no forced timing winner | B5 |
| R48 | explicit signal state machine | B6 |
| R49 | breakout long | B6 |
| R50 | breakdown short | B6 |
| R51 | retest long/short | B6 |
| R52 | reversal long/short | B6 |
| R53 | failed break | B6 |
| R54 | re-entry | B6/B7 |
| R55 | traps | B6 |
| R56 | stale/invalidated | B6 |
| R57 | parameter research | B7 |
| R58 | freeze params before runtime | B7/B10 |
| R59 | entry/buffer/chase | B7 |
| R60 | stop/invalidation | B7 |
| R61 | target | B7 |
| R62 | minimum RR | B7 |
| R63 | cutoff/setup expiry | B7 |
| R64 | max hold/flat | B7/B13 |
| R65 | costs/slippage/liquidity | B7/B8/B13 |
| R66 | chronological backtest | B8 |
| R67 | walk-forward | B8 |
| R68 | untouched holdout | B8 |
| R69 | selection-bias safe | B1/B8 |
| R70 | multiple-testing controls | B8 |
| R71 | sample/CI/uncertainty | B8 |
| R72 | regime stability | B8 |
| R73 | period/year stability | B8 |
| R74 | outlier/edge decay | B8/B13 |
| R75 | analog combinations | B9 |
| R76 | sparse analog abstention | B9 |
| R77 | analog evidence not authority | B9 |
| R78 | per-instrument versioned playbook | B10 |
| R79 | playbook lifecycle | B10 |
| R80 | no silent playbook mutation | B10 |
| R81 | rich ORB evidence package | B11 |
| R82 | FOR evidence | B11 |
| R83 | AGAINST evidence | B11 |
| R84 | unknowns | B11 |
| R85 | blockers | B11 |
| R86 | dependencies/correlation | B11 |
| R87 | D6 final authority | B11/authority |
| R88 | WAIT/WATCH/PAPER-CANDIDATE only | D6/B11 |
| R89 | ML only after deterministic labels | B12 |
| R90 | calibrated ML | B12 |
| R91 | champion/challenger | B12 |
| R92 | ML cannot bypass blockers | B12 |
| R93 | online/offline split | B13/global |
| R94 | matured outcomes only | B13 |
| R95 | paper identity/provenance | B13 |
| R96 | feedback reduce-only/no auto mutation | B13 |
| R97 | adversarial causality | B14 |
| R98 | symmetry | B14 |
| R99 | data failure | B14 |
| R100 | session edge cases | B14/B2/3 |
| R101 | commodity roll/expiry/settlement tests | B14/B2/3 |
| R102 | deterministic replay | B14/all |
| R103 | performance/caching | B5/B8/B9/B14 |
| R104 | GREEN/LOCK exact-head CI | B0/B14 |
| R105 | strangler migration | migration map |

BUILD-0 must convert this table into machine-readable rows with source hashes and test IDs; this Markdown table alone is not sufficient for GREEN.

---

# 48. Requirement-audit dynamic script design

Later implementation should add a repository-native audit utility only after checking current tooling conventions. The logical behavior is mandatory even if the final file path differs.

### 48.1 Inputs

- exact Git SHA;
- canonical source-document list and blob hashes;
- machine-readable requirement manifest;
- stage/contract/calculation/test registries;
- current status/implementation evidence.

### 48.2 Algorithm

```text
for each registered source:
    verify blob hash / load text
    verify every requirement source locator/text hash still resolves

for each requirement:
    require exactly one primary disposition
    require valid owner BUILD/section
    require target contract/calculation links where applicable
    if TARGET_REQUIRED:
        require at least one future/actual test class
    if CURRENT_REGRESSION_BASELINE:
        require a golden/regression fixture
    if RESEARCH_CANDIDATE:
        require authority=false and proof-before-activation gate
    if SUPERSEDED:
        require replacement + reason
    if CONFLICT_NEEDS_PROOF:
        require all competing priors and registered experiment

reject:
    orphan requirement
    duplicate requirement ID/hash collision
    changed source without review
    target marked complete with no test/implementation evidence
    external-review threshold marked canonical without proof
    missing/unknown state normalized to numeric neutral
    authority escalation

emit deterministic canonical JSON + Markdown coverage report
bind report hash to exact Git SHA and BUILD-0 baseline manifest
```

### 48.3 Lock conditions

- coverage = 100%;
- orphan target requirements = 0;
- unexplained source drift = 0;
- hidden conflicts = 0;
- all research priors non-authoritative unless proof/playbook binding exists;
- report deterministic on replay.

This mechanism is specifically intended to prevent another planning pass from “summarizing away” an important ORB line.

---

# 49. External rule/fact validation policy

Exchange sessions, holidays, expiry, settlement, contract specs, price limits and changing market-calendar rules come from versioned official exchange/SEBI sources. Do not encode volatile rule memory into scattered constants.

Historical review statements about expiry weekdays are preserved only as provenance; runtime and backtest reconstruction use the effective calendar registry for the exact date/instrument.

A rule requiring VIX/GIFT/OI/options/news/corporate-action/universe-restriction data cannot become an authoritative gate until a shipped, PIT-safe source contract exists. Until then it is `DATA_UNAVAILABLE`, `NOT_IMPLEMENTED` or `ALERT_ONLY` research evidence, never fabricated zero/safe evidence.

---

# 50. Known blockers and unresolved uncertainties

Implementation-stage blockers/unknowns include:

- generic commodity instrument master/provider mapping;
- versioned historical exchange calendar/exception/spec ingestion;
- settlement availability and continuous-series adjustment policy;
- historical Trendforge/premarket retention for candidate reconstruction;
- empirical cost/slippage/liquidity data sources;
- authoritative PIT event/derivatives/OI source contracts;
- exact final locked M4/D6 receipt schema;
- real source coverage for 1m/3m, commodity, OI, event and settlement fields;
- practical-effect, sample-support and multiple-testing policy versions;
- hardware-specific performance SLO;
- exact source of any previously referenced “12-dimension readiness matrix” not yet verified by this re-audit.

Unknowns remain unknown; they are not permission to invent.

---

# 51. Definition of a complete ORB build

The ORB upgrade is complete only when:

- required deterministic BUILD-0..14 stages are `GREEN / LOCKED` with exact-head evidence; BUILD-12 may be explicitly rejected if no incremental ML value;
- the requirement manifest proves no audited source requirement vanished;
- candidate selection is PIT reconstructable;
- instrument/session/contract identity is effective-date/versioned;
- previous sessions are true exchange sessions, not naive calendar days;
- raw facts have single canonical owners;
- context is multi-axis, hypothesis-driven and missingness-aware;
- clock/TF state is explicit;
- OR boundary facts are separate from signal interpretation;
- all 18 variants and all 50 review rows have explicit research dispositions;
- timing/confirmation choices can return no winner;
- signals are closed-candle explicit state transitions;
- runtime parameters are frozen from prior research;
- proof is chronological, cost-aware, anti-overfit and holdout-safe;
- historical analogs use independence/OOD/sparse abstention;
- playbooks are immutable/versioned/explainably promoted/degraded/retired;
- ORB sends FOR + AGAINST + UNKNOWN + INVALIDATION with dependency lineage;
- optional ML is calibrated, incremental evidence only;
- paper outcomes mature later and feed offline learning only;
- identical replay identity reproduces canonical output;
- valid legacy NSE behavior is retained until intentional migration is separately proven;
- commodity activation cannot occur without resolved session/contract/roll/settlement semantics;
- D6 remains final guidance authority;
- human paper approval remains mandatory;
- no ORB/ML/memory/context path gains live execution/order-routing authority.

Final target:

```text
SELECTED STOCK / COMMODITY CANDIDATE
        ↓
PIT CANDIDATE INTAKE
        ↓
INSTRUMENT / CONTRACT / SESSION IDENTITY
        ↓
D1 RAW FACTS → D2 CLOSED SNAPSHOT
        ↓
PREVIOUS COMPLETED EXCHANGE SESSION
        ↓
CANONICAL CONTEXT + COMPETING HYPOTHESES
        ↓
PROVEN CLOCK / OR DURATION / CONFIRMATION TF
        ↓
BOUNDARY FACTS → EXPLICIT SIGNAL STATE
        ↓
PROOF-BACKED FROZEN PARAMETER SET
        ↓
WALK-FORWARD / UNTOUCHED-HOLDOUT PROOF
        ↓
HISTORICAL ANALOG + MEMORY EVIDENCE
        ↓
VERSIONED PLAYBOOK
        ↓
OPTIONAL CALIBRATED ML EVIDENCE
        ↓
ORB EVIDENCE PACKAGE
FOR + AGAINST + UNKNOWN + INVALIDATION + DEPENDENCIES
        ↓
AFRE
        ↓
D6 FINAL GUIDANCE AUTHORITY
    ↓          ↓                 ↓
   WAIT       WATCH        PAPER-CANDIDATE
                               ↓
                    HUMAN PAPER APPROVAL
                               ↓
                    MATURED OUTCOME ONLY
                               ↓
                 OFFLINE LEARNING / DRIFT /
                    CHALLENGER RESEARCH
```

This document is the code-build specification. It implements none of the above by itself and makes no stage GREEN merely by existing.
