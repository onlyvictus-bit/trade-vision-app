# Executed verification report

Date: 2026-09-06. Scope: the newly authored `tradevision_d6` reference package only.

## Repository access and provenance

- Supplied repository: `onlyvictus-bit/trade-vision-app`.
- Public repository fetch: HTTP 404. This does not establish whether it is private, renamed or unavailable.
- Authenticated repository access: not available in this session.
- Git clone/network attempt: host resolution failed in the execution environment.
- Actual repository files reviewed: **0**.
- Actual repository tests executed: **0**.
- Actual repository changes or commits: **0**.
- Actual market-data backtests, paper trades or broker tests: **0**.
- The user's approximately 75% completion estimate was not independently verified.

## Tests actually executed on the new package

| Check | Actual result |
|---|---|
| Pytest suite | **230 passed**, no failures; 15.42 seconds under coverage instrumentation. |
| Combined statement/branch coverage | **99.66%** for the library, excluding the synthetic demo. |
| Statements | 850 covered / 852 total. |
| Branch exits | 336 covered / 338 total. |
| Randomized monotonicity comparisons | 7,500 across LONG, SHORT, conflict, absent proof and no-capital cases. |
| Exhaustive coarse-grid ordered risk pairs | 7,533 distinct componentwise-comparable pairs. |
| Ordered single-risk grid comparisons | 500 across all five risk dimensions. |
| Total reported risk comparisons | **15,533**, zero violations found, seed 640206. |
| Concurrent audit writes | 32 identical writes across 8 worker threads produced one stored evaluation. |
| Compilation | `compileall` passed for source, tools, examples and tests. |
| Distribution build | Standard Python wheel built successfully without third-party runtime dependencies. |
| Isolated wheel installation | Installed into a separate directory; WATCH and synthetic candidate smoke tests passed. |

The coverage denominator excludes `demo.py`, tests and tooling. Two defensive codec
branches (unsupported internal schema and excessive decoder nesting) were not
executed by the suite. Coverage is not proof of complete behavioral correctness.

Assertions include evidence independence, nonincreasing quality and permission,
nonincreasing permitted quantities, no risk-created candidate and no opposite-side
fallback. The counterfactual service also detects injected invariant violations.
The tests cover invalid/NaN inputs, unknown/duplicate fields, missing sources,
future/stale/unclosed data, proof tampering and scope, insufficient validation,
clock backdating, candidate expiry, signed risk-domain restrictions, invalid ticks, costs, modeled expectancy,
whole-lot budgets, cost-size scope, account vetoes, audit conflicts and storage
failures. These are software tests with synthetic fixtures, not trading outcomes.

## Runtime environment

Python 3.13.5, pytest 9.0.2, coverage 7.13.3, setuptools 82.0.1.
Platform: `Linux-6.18.35-x86_64-with-glibc2.41`. No Windows execution was performed. The package
uses Python 3.11+ syntax/APIs but only Python 3.13.5 was executed here.

## Local synthetic performance

| Measurement | Samples | Median | 95th percentile |
|---|---:|---:|---:|
| Pure kernel, two plans/four sources/three stresses | 2,000 | 0.5549 ms | 0.6980 ms |
| Supervisor, seven evaluations plus a unique SQLite audit insert | 150 | 5.2214 ms | 5.8111 ms |

These are local warm-process synthetic measurements. They exclude market-data
retrieval, indicators, historical matching, real validation production, account
allocation and broker execution. They do not measure or predict the user's app
performance. No improvement percentage against the existing project is claimed.

## Statistical and deployment limitations

No real conditional probability, independence/effective sample size, calibration,
validation report, fee model, instrument eligibility or strategy profitability was
established. Synthetic validation uses deliberately fictional evidence. The normal
PAPER service rejects the synthetic issuer; the demo explicitly uses REPLAY mode.

The proof checker authenticates assertions; it does not validate their scientific
truth. The signed risk envelope must be genuinely supported by the validator; it
is checked as a downward-closed applicability domain, not exact risk equality. The module cannot detect causal leakage hidden inside an upstream producer
that supplies false timestamps. Per-unit costs must be valid for the explicitly
stated quantity range; real schedules and impact models remain external.

No shared-account reservations, order lifecycle, reconciliation, market calendar,
exit engine or live broker path is implemented. SQLite idempotency applies to
evaluation events only, not orders. Repository integration, security review,
real-data replay and market validation are release blockers.

**Readiness conclusion: tested standalone reference implementation, not a certified
production system or a verified repository patch.**

## Reproduce

```text
python -m coverage run -m pytest -q
python -m coverage report -m
python -m tools.property_audit
python -m tools.benchmark
```

Raw outputs accompany this report in `pytest_output.txt`, `coverage.txt`,
`coverage.json`, `property_audit.json`, `benchmark.json` and
`synthetic_risk_example.json`.
