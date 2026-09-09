# M4-9 — Adversarial, Replay and Safety Test Plan

## Purpose
Prove M4 cannot be tricked by authority inversion, temporal leakage, data corruption, correlated evidence, conflicting worlds, unstable serialization or performance stress.

## Test classes
### Authority attacks
- 100 low-authority bullish supports vs one D1 block -> safe band.
- specialist sets `final_band_claimed=true` -> reject/quarantine.
- reviewer attempts upgrade from WAIT -> rejected.
- presenter mutates decision -> impossible.
- any engine `may_execute=true` -> registry/receipt failure.

### Temporal attacks
- future `observed_at`.
- label available after decision time.
- later quarantine applied to replay corpus.
- stale snapshot.
- mismatched decision time/timezone.
- replay using different snapshot hash.

### Data attacks
- required block missing.
- UNAVAILABLE vs MISSING preserved.
- NaN/Inf.
- invalid schema/version.
- degraded source.
- conflicting trustworthy source.
- forged source output hash.
- duplicate evidence node ID.

### Market conflicts
- price bullish/context bearish.
- price bullish/memory bearish.
- context bullish/memory OOD.
- all three canonical worlds disagree.
- liquidity poor/setup strong.
- event risk extreme/setup strong.
- derivatives hostile/price strong.

### Statistical attacks
- tiny sample.
- 100 correlated indicator rows from one episode.
- OOD severe.
- drift severe.
- regime mismatch.
- overfit/edge-decay flag.
- memory unavailable but price/context strong.

### Strategy attacks
- long strong and short strong simultaneously.
- false breakout.
- whipsaw/chop.
- result/event shock.
- expiry pinning/gamma distortion.
- exhausted >1.5x ATR gap as supplied by canonical evidence.
- stale/late breakout.
- first-bar contamination.

### Counterfactual attacks
- remove strongest support.
- remove memory.
- remove index alignment.
- resolve conflict against thesis.
- degrade volume evidence.
- remove blocker.
- single-factor dependency detection.

### Determinism/replay
- shuffled input ordering.
- Python hash-seed changes.
- repeated replay 1000x.
- JSON/msgpack or supported serialization round trip.
- stable conflict/scenario IDs.
- stable decision hash.
- policy version change changes hash.

### Performance
- large symbol batch.
- maximum allowed evidence nodes.
- maximum conflict count.
- maximum 12 scenarios and 8 counterfactuals/thesis.
- no recursive/unbounded loops.
- no canonical world recomputation.
- memory footprint bounded.

## Golden invariants
```text
missing != neutral
unknown != false
unavailable != safe
synthetic != real
error != zero
future != causal
unfinished != closed
stale != fresh
correlated facts != independent episodes
label observed later != label available now
```
Every invariant must have at least one direct adversarial test.

## Safety assertions on every final report
- sole finalizer identity is D6.
- trade_allowed is false.
- order_routing_enabled is false.
- live_trading_blocked is true.
- human approval is required.
- no specialist/reviewer receipt can contain effective final authority.

## Test levels
1. pure unit tests for policies/classifiers.
2. component tests for conflict/scenario/uncertainty.
3. integration tests from DecisionContext to receipt.
4. Paper Guidance compatibility.
5. replay/golden fixtures.
6. full API regression.
7. performance benchmark.
8. authority audit.
9. exact-head CI.

## Acceptance
No critical adversarial fixture may merely lower a numeric score; it must produce the correct explicit epistemic/conflict/veto/cap result. Replays are deterministic and safety flags immutable.

## Lock criteria
All targeted/adversarial/replay suites green, existing locked regressions green, full tree green, performance budget met, authority audit green, exact-head CI successful.

## Expected files
`tests/behavior/decision_spine/test_m4_*`, adversarial fixtures, replay fixtures, performance tests, CI workflow extension.

## Forbidden casual edits
Do not weaken existing tests or safety checks to make M4 pass.
