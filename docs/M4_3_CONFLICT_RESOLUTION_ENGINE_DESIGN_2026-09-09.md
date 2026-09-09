# M4-3 — Conflict Resolution Engine Design

## Purpose
Replace ad-hoc conflict deductions with a typed authority-aware conflict graph.

## Repository truth
Current D6 hardcodes a small set of conflicts and score adjustments. M4 must generalize conflict handling without restoring generic scoring.

## Conflict node
```text
conflict_id
class
participants[]
side
authority_order
resolution: RESOLVED|UNRESOLVED|VETO|DOWNGRADE|EXPLANATION_ONLY
severity
uncertainty_delta_class
final_band_cap
reason_codes[]
policy_version
```

## Taxonomy
1. SAFETY_VS_THESIS — D1/data integrity vs any thesis.
2. STRUCTURE_VS_INDICATOR — canonical price structure vs lagging/supportive indicator.
3. PRICE_VS_CONTEXT — stock setup vs index/sector/regime.
4. PRICE_VS_MEMORY — current price facts vs historical analog support.
5. CONTEXT_VS_MEMORY — present regime/context vs remembered historical regime.
6. LIQUIDITY_VS_SETUP — technically valid setup but poor tradability.
7. EVENT_VS_SETUP — event risk invalidates otherwise valid thesis.
8. DERIVATIVES_VS_DIRECTION — OI/positioning/expiry state hostile to direction.
9. INTERNAL_WORLD_CONTRADICTION — two canonical claims in same domain disagree.
10. LONG_VS_SHORT — simultaneously strong incompatible theses.
11. QUALITY_VS_CONTENT — high signal strength from degraded/stale evidence.
12. OOD_VS_MEMORY — analog support under material OOD/drift.
13. INDEPENDENCE_CONFLICT — apparently multiple confirmations share one causal source.

## Authority resolution
- Higher authority may veto/lower cap lower authority.
- Equal-authority contradiction cannot be averaged away. It becomes UNRESOLVED unless a deterministic domain-specific tie rule exists.
- Lower-authority opposition to higher-authority evidence can increase uncertainty or appear in explanation, but cannot reverse a proven higher-authority hard block.
- Memory/reviewer conflict with canonical current facts never overrides current causal fact.

## Deterministic tie handling
Tie policy order: canonical provenance quality -> freshness -> directness/causal proximity -> domain policy -> unresolved. Never random; never list-order dependent.

## Consequences
Each conflict maps to exactly one or more explicit consequences:
`VETO_DIRECTION`, `CAP_AT_WAIT`, `CAP_AT_WATCH`, `DOWNGRADE_CONFIDENCE`, `MARK_AMBIGUOUS`, `EXPLANATION_ONLY`.
No arbitrary numeric penalty.

## Long/short asymmetry
Conflict rules are side-aware. Weak sector may degrade long continuation while not automatically validating short reversal. Derivatives hostility to longs can be irrelevant to a short thesis only if its own short-side causal rule says so.

## State transitions
```text
EVIDENCE NODES -> PAIR/GROUP CONFLICT DETECTION -> AUTHORITY ORDER
-> RESOLUTION POLICY -> RESOLVED/UNRESOLVED/VETO/DOWNGRADE -> RECEIPT
```

## Failure behavior
Unknown conflict class or conflicting policy outcome fails closed to UNRESOLVED + uncertainty increase; it does not silently choose a side.

## Performance
Use indexed conflict predicates over bounded node classes. No O(N^2) unrestricted all-node comparison. Conflict detectors subscribe only to relevant evidence classes.

## Replay
Conflict IDs derive deterministically from participant IDs + policy class. Shuffled input order must yield same graph and hash.

## Tests
- price bullish/context bearish
- price strong/memory weak
- event risk extreme/setup strong
- D1 degraded/technical strong
- all canonical worlds disagree
- equal-authority contradictory sources
- duplicate correlated confirmations
- long and short simultaneously strong
- ordering invariance

## Acceptance
No decision-affecting contradiction is represented only as a score adjustment. Every conflict has participants, authority ordering, explicit resolution and downstream consequence.

## Expected files
`m4_conflict_graph.py`, `m4_conflict_policy.py`, tests.

## Forbidden casual edits
Locked source calculators and registry authority contracts.
