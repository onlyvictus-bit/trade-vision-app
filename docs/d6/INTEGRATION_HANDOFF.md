# Handoff to a coding agent with repository access

This is an integration specification, not a claim that the target files were read.
Target: `https://github.com/onlyvictus-bit/trade-vision-app`.

## Required first action: establish the actual checkout

Record branch, commit, working-tree changes, dependency versions and test commands.
Do not overwrite existing uncommitted work. Do not infer completion from a stated
"75%" estimate. Do not assume file paths or engine classes from this reference.
Do not run live-trading entrypoints or provide this package with broker credentials.

Run the inventory helper against the checkout, then actually inspect the sources:

```powershell
python tools/repo_inventory.py --root "D:\path\to\trade-vision-app" --out repo_inventory.json
```

The inventory records tracked text-file hashes, line counts and heuristic D6 match
locations; it does not read meaning, prove defects, or complete a line-by-line
review. Record every skipped file and why. Never include `.env` or credential data.

## Reconstruct authority and dependency order before editing

For every engine, record its real file/class/function, input producers, output
consumers, horizon, timestamp/availability assumptions, failure behavior, whether
it can veto, and whether it can cause an order or overwrite a decision. Trace the
UI request through data, features, setup detection, historical matching, risks,
costs, allocation, final response and any execution consumer. Record alternate,
legacy and fallback paths, not just the intended main path.

Find all signed-score arithmetic, direction choices, max/min/normalization,
missing-input defaults, post-decision overrides and `WAIT` fallbacks. Classify raw
contributions as LONG evidence, SHORT evidence, setup quality, risk penalty,
hard permission gate, cost, or operational state. Cite actual source lines.

## D6 migration rules

Never convert an already mixed signed score using:

```
long = max(old_score, 0)
short = max(-old_score, 0)
```

That preserves the contamination. Recover the independent raw directional
contributions. Risk penalties must never be evidence for the opposite side.
Unavailable raw contributions must cause WATCH/WAIT while the producer is fixed.

Introduce the reference contracts behind an adapter using actual project types.
Keep the public `WAIT / WATCH / PAPER-CANDIDATE` contract or deliberately version
any existing alias. Do not silently replace it with broker actions. Give one
component final candidate authority; all other engines emit typed facts/evidence
or vetoes. Higher evidence cannot override safety, cost or account rejection.

Run the reference in shadow mode first: the existing output and D6 output may be
compared, but D6 must not place orders. The proposed shadow flag is a new design
concept, not a verified flag already present in this repository. Save input hashes,
old/new evidence and reasons, selected side and the cause of each difference.

Map missing, timed-out, malformed and stale risk output to a veto, not zero risk.
Do not fabricate validation samples, probabilities, costs, boolean checks or
eligibility. Keep the demo key and demo issuer out of real validation. Do not let
a language model rewrite policy or sign its own approval.

## Required tests in the real application

Run the existing baseline suite before changes. Add adapter-level tests that
increase each raw upstream risk input while preserving actual market evidence;
assert both evidence invariance and nonincreasing final permission. Run these
through every endpoint and postprocessor, not only the new kernel. Test positive
and negative directional cases, conflicts and absent setups. A vetoed preferred
side must not fall back to the opposite setup.

Audit all higher-timeframe joins and feature availability. Historical bar labels
must not imply availability before close. Training, fitting, scaling, selection
and neighbor indexing must not use later observations. Purge overlapping outcome
windows between training/validation and apply an embargo appropriate to the actual
holding period. Verify point-in-time constituents, corporate actions and joins.

Validate separately for intraday and swing, across chronological held-out periods,
symbols, market regimes and a realistic cost/size model. Use dependence-aware
uncertainty and account for strategy/parameter search. Treat `TimeSeriesSplit`
with a gap as a tool, not proof that event-label overlap is correctly purged.

Test new snapshots arriving during evaluation, stale results, changed account
versions, concurrent symbols, duplicated events, reconnects, partial fills,
rejections, cancel/replace races, halts and late data. The reference only tests
local audit concurrency, not broker or shared-account execution races.

## Acceptance gates before enabling paper execution

1. Actual repository diff reviewed; original and new tests passing; every final
   decision path accounted for, with no direct legacy bypass.
2. Real validation artifact producer and key management implemented; no demo
   values or silent evidence defaults.
3. Data/timeframe and point-in-time tests passed on actual provider data.
4. Independent, chronological economic validation and held-out paper replay passed
   against predeclared acceptance criteria; thresholds are not selected post hoc.
5. One account-wide allocator reserves risk/capital atomically across symbols and
   both horizons, checks expiry and enforces order idempotency.
6. Observability, rejection reason tracking, rollback and human kill switch tested.

Deliver the actual file-by-file coverage ledger, ranked findings with file/line
citations, one corrected flow, one authority matrix, minimal code diff, executed
test logs, remaining limitations and an explicit shadow-to-paper rollout decision.
No "all scenarios solved" or "production ready" claim without that evidence.
