# M4-7 — Reason Tree and Decision Receipt Design

## Purpose
Make every final judgment replayable, inspectable and attributable to canonical evidence and explicit policy rules.

## Repository truth
Current D6 emits human-readable reason strings and conflict/gate objects. M4 upgrades this into a structured receipt while preserving human explanation compatibility.

## Receipt schema
```text
decision_receipt_version
decision_id
decision_hash
context_hash
snapshot_hash
authority_manifest_version
policy_versions{}
input_bundle_hash
state_machine_trace[]
active_theses[]
rejected_theses[]
authority_nodes[]
epistemic_nodes[]
conflicts[]
failure_modes[]
scenarios[]
counterfactual_results[]
uncertainty_receipt
blockers[]
band_caps[]
final_band
final_rule_id
trade_allowed=false
order_routing_enabled=false
live_trading_blocked=true
human_approval_required=true
```

## Reason tree
Structured tree categories:
```text
DECISION
 +-- safety/integrity
 +-- price world
 +-- context world
 +-- memory world
 +-- side-specific thesis
 +-- conflicts
 +-- missing/degraded evidence
 +-- failure risks
 +-- scenarios
 +-- counterfactual robustness
 +-- uncertainty/confidence
 +-- applied vetoes/caps
 +-- final arbitration rule
```

## Evidence lineage
Every leaf references canonical `node_id`, source engine, source output hash, snapshot hash and decision time. No explanation may cite evidence not present in the normalized input bundle.

## Reason codes
Stable machine-readable namespaces:
- `M4.INPUT.*`
- `M4.AUTH.*`
- `M4.EPISTEMIC.*`
- `M4.CONFLICT.*`
- `M4.FAILURE.*`
- `M4.SCENARIO.*`
- `M4.CF.*`
- `M4.UNCERTAINTY.*`
- `M4.ARBITER.*`
- `M4.SAFETY.*`

Human text is presentation derived from reason codes; machine logic never parses prose.

## Decision hash
Canonical hash over decision-affecting receipt fields and versions, excluding presentation-only prose/order-insensitive formatting. Hash must change when policy version, evidence, conflict resolution, robustness result or final band changes.

## Replay receipt
Includes all input hashes and policy versions needed to reconstruct decision without refetching live data.

## Failure behavior
If receipt construction detects unreferenced evidence, duplicate node IDs, inconsistent final rule, noncanonical ordering or hash mismatch, final output fails closed and cannot be promoted.

## Long/short behavior
Reason tree keeps independent long and short thesis branches. Rejection of long is not evidence that short passed.

## Performance
Receipt generation is linear over already bounded artifacts. Human prose rendering is optional and downstream of machine receipt.

## Determinism
Canonical sort by stable IDs. No ambient timestamps except canonical decision metadata. Serialization round trip must preserve hash.

## Tests
- every reason leaf resolves to evidence
- no hidden evidence
- deterministic ordering
- hash changes on meaningful evidence/policy change
- prose changes do not alter decision hash
- serialization round trip
- long/short branches independent
- safety flags immutable

## Acceptance
An auditor can reproduce why the decision was WAIT/WATCH/PAPER-CANDIDATE from receipt alone and identify every blocker, cap, conflict and uncertainty source.

## Expected files
`m4_receipt.py`, `m4_reason_tree.py`, serializer/hash tests.

## Forbidden casual edits
Canonical source receipt internals, M3 calculations, authority law.
