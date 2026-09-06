# AFRE v3: implemented architecture and ownership

## One versioned adaptive path

`Controller.evaluate` is the pure evaluator. `advance_session` owns the event-driven account/session state machine. `Service` wraps that reducer with trusted clocks, current safety, exact reviewed proof, durable transactions and human approval. `replay_day` calls the same reducer, evaluator and execution engine, with a separately identified research approval-delay policy. Research never writes a human-approved user trade.

The existing loader is retained through `adapters.from_candle_series`. Its caller must provide real availability metadata and compatible price basis. `RepositoryDataGuard` reuses the host's existing D1 models and `run_paper_guidance_p0` under an exact source/config hash. The live kill switch is checked separately from those deterministic data checks. The data guard belongs inside the shared evaluator, not in a paper-only post-proof veto.

The narrow installed exports are opt-in entry points. Old ORB results stay old; AFRE results carry a new whole-policy identity. Once host verification succeeds, update the existing Research and Guidance callers to select this versioned path. There is no automatic UI rewrite in this bundle and no claim that every existing screen now invokes AFRE.

## State and event ordering

1. Validate the account/day, policy hash, event watermark and idempotency identity.
2. Resolve an already accepted paper plan with available execution bars. Entry-analysis vetoes do not stop exit accounting.
3. Record causal feature/reference changes. An identical event yields its original receipt; a reused ID with a different payload conflicts. Revised observed prices preserve old state and quarantine instead of rewriting old forecasts.
4. Validate complete OR intervals, identity, source, price basis and availability. Data invalidity does not become bearish evidence.
5. Evaluate the bounded market branches, immutable evidence references, exact forecast questions and registered candidate templates.
6. Validate economic feasibility at every permitted fill boundary. Apply the frozen priority or validated value provider. Wait and skip remain allowed.
7. Select only aligned, same-watermark universe proposals. Freeze the account/day proposal. Superseded proposal IDs cannot approve replacements.
8. In paper mode, recheck proof, safety, quantity, expiry and account allowance in the approval transaction. A new market thesis cannot change the accepted plan.
9. Atomically persist state, event result and a hash-chained audit receipt. Stop until another event or deadline.

## Modules

| File | Authority |
|---|---|
| `contracts.py` | Validated, frozen domain models, UTC nanoseconds, policy/account hashing, permanent safety flags. |
| `features.py` | Causal session features, exact OR, session VWAP, gap/CPR annotations, observed break/failure/reclaim episodes. |
| `registry.py` | Preserved 30-case taxonomy and 20 controller-risk coverage states; source prose is not executed. |
| `controller.py` | Eight branches, up to six action templates, independent fade/reclaim rules, bounded challenge, deterministic decision trace. |
| `execution.py` | Common paper/research entry, protective stop geometry, target construction, friction, exits and realized PnL. |
| `runtime.py` | Shared account/session reducer, synchronized universe selection, approval/fill tokens, revisions and timers. |
| `store.py` | SQLite transactions, durable restart, checkpoints, idempotent receipts, backup and sealed research-date register. |
| `service.py` | Trusted clock/safety/proof checks and separate explicit human approval. |
| `api.py` | Token-authenticated local routes, strict request models, two-megabyte request limit. |
| `wake.py` | Lifecycle-managed deadline checks; no price generation or provider polling. |
| `research.py` | Exact universe replay, train-only selection, chronological development folds and untouched final holdout. |
| `forecasting.py` | Two structural labelers, regularized frequency models, chronological validation, support checks and forecast scoring. |
| `datasets.py` | Outcome-side label building and fixed one-symbol shadow wait-policy experiments; never imported as future features. |
| `value.py` | Common-budget action outcomes, date-based uncertainty, later validation, abstention against zero-trade comparator. |
| `monitor.py` | Matured-real-outcome review alerts and descriptive regret; no automatic retraining/deployment. |
| `governance.py` | Exact code/config/data-study identities and offline authenticated operator review. |
| `adapters.py` | Existing CandleSeries boundary, explicit known-at metadata, valid finer aggregation and host D1 binding. |
| `integration.py` | Off/shadow/exclusive-paper deployment profiles and persistent host kill-switch wiring. |
| `explain.py` | Escaped HTML and structured JSON/Markdown explanations; no trading authority. |
| `demo.py`, `cli.py` | Executable synthetic examples and explicit local research commands. |

## Decision branches versus probabilities

Several branches can be plausible simultaneously. Acceptance and extension risk can both be true. A structural failure detector means an event has already occurred; a prospective forecast records when it was issued and its exact target/horizon. Correlated candle tags share price evidence, rather than multiplying independent likelihoods. Numeric values are null when no validated provider covers that context.

## Accounting invariants

No backward fill at an earlier trigger. The next permitted whole execution-bar open must occur after the declared approval time. The first eligible opening price is checked against the frozen envelope; an invalid price is not rescued by shopping through later bars. Stops stay at their structural anchor. Long stop must be below actual fill and short stop above it. A gap beyond a stop can lose more than one initial risk unit. Stop/target ambiguity is reported with conservative stop-first handling. Time exits require an observable boundary. MFE/MAE exclude later bars after exit and expose intrabar bounds. Cash PnL uses actual modeled entry/exit fills, with explicit fees applied once.

## Remaining integration work

The selected host signatures were inspected through GitHub; a full host import, source-bound end-to-end comparison, existing frontend controls and provider adapters must still be exercised in the real checkout. The old JSON paper ledger is not silently migrated to this transactional ledger. Exclusive-account mode is a guarded migration option, not a claim that parallel independent processes are coordinated automatically.
