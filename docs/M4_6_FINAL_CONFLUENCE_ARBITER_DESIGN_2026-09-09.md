# M4-6 — Final Confluence Arbiter Design

## Purpose
Define D6 as the sole deterministic final-band authority after canonical evidence, authority, epistemic state, conflicts, failures, scenarios, counterfactuals and uncertainty have been resolved.

## Repository truth
`FINAL_CONFLUENCE_ARBITER` is already the only registry entry with `may_set_final_band=True`. M4 preserves that identity and removes weighted-vote dependence from final arbitration.

## State machine
```text
INGEST
 -> VALIDATE
 -> AUTHORITY_CLASSIFY
 -> EPISTEMIC_CLASSIFY
 -> CONFLICT_DETECT
 -> FAILURE_SCAN
 -> SCENARIO_ANALYZE
 -> COUNTERFACTUAL_CHALLENGE
 -> UNCERTAINTY_SYNTHESIS
 -> THESIS_ARBITRATION
 -> FINAL_BAND_ASSIGN
 -> RECEIPT
```

## Final bands
Canonical public behavior remains conservative:
- WAIT
- WATCH
- PAPER-CANDIDATE
- AVOID / NO-TRADE compatible state where required by current clients
- SHORT PAPER-CANDIDATE only when independently validated short thesis meets policy

No band implies execution authority.

## Arbitration policy
1. D1 hard block terminates promotion and forces safe output.
2. Structural vetoes are applied before directional support.
3. Invalid/incomplete canonical context cannot promote.
4. Each active thesis is evaluated independently.
5. Unresolved high-authority conflict caps or vetoes according to policy.
6. Failure modes can veto/cap when their canonical conditions are proven.
7. Counterfactual fragility caps promotion.
8. Confidence/uncertainty provides a band ceiling, not an approval vote.
9. PAPER-CANDIDATE requires all mandatory gates, adequate evidence coverage, no unresolved critical conflict, acceptable robustness and policy-defined minimum confidence.
10. No-trade/WAIT is an intelligent valid result.

## No weighted final score
M4 may expose diagnostic ordinal summaries, but final band must not be derived from `sum(weights)` or a hidden average. Decision is a policy-lattice result over authority, vetoes, caps, thesis validity and robustness.

## Thesis arbitration
Supported thesis modes:
- BULLISH_CONTINUATION
- BULLISH_REVERSAL
- BEARISH_CONTINUATION
- BEARISH_REVERSAL
- NO_TRADE
- AMBIGUOUS_CHOP

If incompatible long and short theses both remain strong, D6 returns ambiguity/WAIT unless a deterministic higher-authority rule resolves the conflict. It does not choose based on marginal score difference.

## Invalid/incomplete context
- identity/hash failure -> fail closed
- critical MISSING/UNAVAILABLE evidence -> policy cap or WAIT
- stale critical context -> WAIT/AVOID depending authority
- severe OOD -> historical support disabled/capped
- contradictory critical evidence -> unresolved conflict cap

## Blocker precedence
```text
D1 safety / PIT / identity
> structural impossibility / severe tradability risk
> critical event/execution veto
> canonical current facts
> strategy thesis
> memory/reliability support
> reviewers/explanation
```

## Upgrade restrictions
Only D6 assigns band. No reviewer, memory engine, strategy, compatibility adapter or presenter can promote. D6 itself cannot ignore higher-authority blocker rules.

## Performance
Pure bounded in-memory policy evaluation. No I/O. Target complexity linear in normalized evidence + bounded conflicts/scenarios/counterfactual receipts.

## Determinism/replay
Version all policies. Same normalized bundle and policy versions produce identical final band, reason codes and receipt hash.

## Observability
Emit state entered/exited, applied vetoes, caps, surviving thesis, rejected theses, uncertainty ceiling, final rule ID and decision hash.

## Tests
- hard safety vs 100 bullish supports
- strong setup but missing critical evidence
- strong setup + event veto
- fragile thesis capped
- robust long candidate
- independently robust short candidate
- simultaneous long/short ambiguity
- reviewer attempts upgrade
- memory-only support cannot promote
- ordering/replay invariance

## Acceptance
There is exactly one code path that assigns final band, and its output can be reconstructed from explicit deterministic rule applications without hidden score arithmetic.

## Migration
Keep current v1.75 arbiter behind compatibility adapter until M4-I. Preserve public response fields where possible while replacing internal authority semantics.

## Expected files
`m4_arbiter.py`, `m4_policy.py`, `m4_thesis_arbitration.py`, compatibility changes in `final_confluence_arbiter.py`.

## Forbidden casual edits
Authority registry sole-finalizer law; D1/D2/M3 calculations; execution boundaries.
