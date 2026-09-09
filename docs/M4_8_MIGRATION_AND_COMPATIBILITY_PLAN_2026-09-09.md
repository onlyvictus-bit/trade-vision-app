# M4-8 — Migration and Compatibility Plan

## Purpose
Migrate current D6 to M4 without breaking Paper Guidance, APIs, locked tests, canonical M3 worlds or existing clients.

## Repository truth
Current system has a legacy `FinalConfluenceArbiterRequest/Report` path and a canonical `DecisionContext` path assembled in Paper Guidance. M4 should converge these through adapters, not by rewriting locked engines.

## Migration principles
1. Add M4 beside current D6 first.
2. Build canonical `DecisionContext -> M4CanonicalInputBundle` adapter.
3. Add legacy request compatibility adapter only for fields that can be proven equivalent.
4. Shadow-run M4 against v1.75 fixtures before switching authority path.
5. Preserve output fields/labels required by clients.
6. Never grant authority to compatibility layers.
7. Do not modify M3 calculations to simplify M4.

## Compatibility seams
### Input seam
`DecisionContext` is preferred source. Legacy scalar request is accepted only through a versioned adapter that marks information loss/missingness explicitly.

### Output seam
Map new structured decision receipt to current `FinalConfluenceArbiterReport` fields:
- final decision/band
- dominant blocker
- human reason tree
- conflicts
- confidence representation (clearly semantic, not probability)
- gates/reasons
- hard safety flags

### Paper Guidance seam
Paper Guidance continues to receive research-only final guidance. It must not bypass D6 or create alternate final band.

## Locked regressions
M0, M2, M3.1, M3.2, M3.3 and Paper Guidance regressions remain mandatory. Any expected semantic change in D6 gets explicit fixture migration notes, never silent test weakening.

## Migration stages
1. Add types/validators only.
2. Normalize canonical context.
3. Shadow authority/epistemic/conflict artifacts.
4. Shadow failure/scenario/uncertainty artifacts.
5. Shadow M4 final arbitration, compare with v1.75.
6. Classify differences as intentional safety improvement, parity, or bug.
7. Switch final authority implementation behind same registry identity.
8. Retain rollback feature seam until exact-head lock.

## Backwards-compatible receipt extension rule
Only extend locked receipts if M4 requires information that is not already present and cannot be safely derived at orchestration level. Any extension must be additive, versioned, default-safe and independently regression-tested.

## Rollback
Single configuration/import seam returns finalization to locked v1.75 implementation. No rollback requires reverting M3 worlds or data contracts.

## Failure behavior
If adapter loses critical epistemic/authority information, M4 caps to WAIT rather than inventing equivalence. Legacy missing scalar cannot be interpreted as neutral.

## Long/short
Legacy symmetry assumptions are not carried forward. Adapter must identify when old request cannot express an independent short thesis; such case cannot produce new short promotion.

## Performance
Shadow mode may double arbitration cost but must not rerun canonical calculators. Once cut over, only one M4 arbitration pass remains.

## Tests
- old request adapter parity
- missing legacy field fail-closed
- Paper Guidance response compatibility
- API serialization
- locked regression suite
- semantic diff fixtures
- rollback seam
- authority registry unchanged

## Acceptance
M4 can be enabled/disabled at one orchestration seam, public safety/output contracts remain compatible, and locked M3 code remains untouched except separately approved additive receipts.

## Expected files
Adapters around `final_confluence_arbiter.py`, `paper_guidance_decision_context_adapter.py`, possibly response model serializers, new M4 compatibility module/tests.

## Forbidden casual edits
M3 locked calculators, D1/D2 safety/identity, memory PIT, registry final-authority identity.
