# M4-1 — Canonical Input and Evidence Contract

Baseline: `main@7a15bfb3717d34ea75d19a6584a3ef814fae8001`

## Purpose
Define the only data M4 may consume and prohibit raw recomputation of locked facts.

## Repository truth
`DecisionContext` is immutable, hash-bound to D2 identity, includes explicit `EvidenceBlock` status/provenance, and already carries price, context, memory, derivatives/events/failure/risk/proof/paper fields. M4 should extend orchestration around this contract rather than bypass it.

## Inputs
### D1 / Stage2 integrity
- canonical snapshot hash
- engine integrity states
- source mode / availability
- hard blockers / warnings
- output hash

### D2 identity
- symbol
- timeframe
- decision_time UTC
- snapshot_hash
- universe_watermark

### M3.1 Price world
Consumed only through canonical receipts/DecisionContext fields: price structure, levels, candle anatomy, MTF/indicator-derived canonical price evidence and their provenance.

### M3.2 Context world
Market regime, session, index, sector, relative strength, contextual quality/contradictions through canonical receipts.

### M3.3 Memory world
Analog, reliability, session, pattern, 9C, PTA, OOD, drift, sample sufficiency, quarantine/retention states through canonical memory receipts. Raw records must not be treated as independent episodes.

## Canonical M4 evidence envelope
Each decision-affecting evidence node must expose:
```text
node_id
source_engine
canonical_domain
claim_type
side: LONG|SHORT|BOTH|NONE
authority_class
epistemic_state
availability
observed_at
decision_time
freshness_state
quality_state
source_mode
payload_hash
source_snapshot_hash
source_output_hash
independence_group
regime_scope
sample_support
reasons
warnings
provenance
```

## Identity invariants
- Every decision-affecting node must bind to exactly the D2 snapshot hash.
- `observed_at <= decision_time` for causal evidence.
- Later labels/memory outcomes are unavailable until label-availability time.
- Identity mismatch is a hard validation failure, not degraded evidence.

## Epistemic transport
M4 must preserve, never collapse:
`KNOWN, UNKNOWN, UNAVAILABLE, MISSING, DEGRADED, STALE, CONTRADICTORY, OUT_OF_DISTRIBUTION, QUARANTINED, INSUFFICIENT`.

## Authority transport
Authority comes from registry/policy, not source self-claims. Any evidence claiming final-band or execution authority outside D6 is rejected/quarantined.

## Missingness rules
- Expected-but-absent receipt => MISSING.
- Source explicitly unavailable => UNAVAILABLE.
- Present but stale => STALE.
- Present but schema/quality degraded => DEGRADED.
- Conflicting trustworthy facts => CONTRADICTORY.
- No neutral numeric substitution is permitted.

## State transitions
```text
RAW CANONICAL RECEIPT
 -> identity validation
 -> provenance validation
 -> causality/PIT validation
 -> authority binding
 -> epistemic classification
 -> normalized M4 evidence node
```
Invalid identity, future evidence, forged authority, non-finite decision-critical payload, or corrupted hashes fail closed.

## Outputs
`M4CanonicalInputBundle` containing immutable ordered evidence nodes, input integrity summary, authority manifest version, context hash, and bundle hash.

## Long/short behavior
Every directional claim declares side relevance. `SHORT` is not derived by multiplying long evidence by -1. Side-neutral risks may veto both; side-specific conflicts only affect the relevant thesis.

## Performance
Normalization is O(N) over bounded canonical evidence nodes. No network I/O or historical scanning. Cache by `(context_hash, contract_version, authority_manifest_version)`.

## Determinism/replay
Stable sorted IDs, canonical serialization, UTC timestamps, no random values. Same DecisionContext and policy versions must yield byte-equivalent normalized bundle/hash.

## Observability / receipts
Receipt includes rejected nodes, rejection reasons, missing expected fields, authority binding, epistemic state and input bundle hash.

## Tests
- snapshot mismatch
- future timestamp
- forged final-band claim
- unavailable != neutral
- missing != zero
- non-finite values
- stale evidence
- contradictory sources
- OOD memory
- independent_episode_count preserved
- serialization/hash replay

## Acceptance criteria
M4 can be fully driven from canonical receipts with no raw calculator call, and every absence/quality/authority condition is explicit.

## Migration / rollback
Introduce adapter from current `DecisionContext`; leave legacy D6 request untouched until M4-G. Rollback is removal of M4 adapter/wiring only.

## Expected files
New: `m4_input_contract.py`, `m4_evidence.py`, tests. Possible backwards-compatible DecisionContext receipt extension only if proven necessary.

## Forbidden casual edits
D1/D2 identity and safety; M3.1/M3.2/M3.3 calculations; memory PIT/label timing.
