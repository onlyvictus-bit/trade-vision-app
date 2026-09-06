# Research, model fitting and exact paper permission

## First establish real input provenance

The executable synthetic demo is a shape example, not a market fixture. Real `ResearchDay` input must carry a reviewed manifest, correctly ordered and complete intervals, per-bar availability, earlier-session reference data, compatible price bases, an actual trading-date calendar and an independently reviewed origin attestation. Do not replace the string `SYNTHETIC` with `REAL_ATTESTED` to make a gate pass. The latter is a trusted upstream assertion, not independent verification by this code.

Keep original raw inputs, adjustment/calendar versions, loader version, symbol universe and all source corrections. Keep both no-entry and unknown dates. A corrupted or censored day must not be coded as profitable abstention. All symbols on one date share that date's split and account allowance.

## Frozen configuration

The entire selector is a policy: templates, priority, waiting/confirmation rules, cutoffs, price/volume filters, costs, execution resolution, reward multiple, capability requirements and model identities. Changes produce a new hash. The account budget and universe are separately bound. A leaf recipe's previous proof cannot authorize a new adaptive selector, and the BEL control cannot be inherited automatically.

Within the real repository, bind the existing D1 source and effective settings first:

```text
python -m app.orb.adaptive.cli bind-host-d1 --policy configs/afre/policy.example.json --out data/afre/policy.host-bound.json
```

This hash covers the inspected host models, D1 spine, data-quality guard, point-in-time guard and paper-guidance config plus effective data settings. If those change, the new study must use the new binding. `RepositoryDataGuard` is shared by replay and guidance; no new price filter is inserted only after proof.

## Exact replay and registered policy study

From the repository root with `PYTHONPATH=apps/api`:

```text
python -m app.orb.adaptive.cli replay --data data/afre/research-days.json --policy data/afre/policy.host-bound.json --limits configs/afre/account.example.json --out data/afre/replay.json
python -m app.orb.adaptive.cli prove --data data/afre/research-days.json --policies data/afre/registered-policies.json --limits configs/afre/account.example.json --holdout-start YYYY-MM-DD --study-id unique-registered-study --registry-db data/afre/trials.sqlite3 --out data/afre/proof.json
```

`registered-policies.json` is a JSON array of the full registered Policy objects, not a list of previous backtest winners. Pick the holdout date and policies before reading its outcomes. Register all experiments, including failures. The CLI's study register makes a final study immutable and seals final dates against reuse by a new study ID in the same database. It is a governance aid, not a defense against an operator deleting their research history.

The engine selects only from development data. Each walk-forward fold selects on its own earlier training prefix and scores the chosen policy on a later development block. Final-holdout prices are evaluated only after freezing the development-selected policy. The test suite changes only holdout paths to verify that the earlier selected recipe does not change.

The default declared support/edge thresholds are visible in `ProofThresholds` and the schema. They are review criteria, not universal statistical proof. Outcomes use common account-risk-budget units, include no-entry/no-fill, preserve UNKNOWN, and use a declared date-block bootstrap for mean uncertainty. Rare gaps and discontinuities can exceed the initial risk estimate. A confidence bound does not certify future tail safety.

## Failure dataset and frequency models

```text
python -m app.orb.adaptive.cli label-structural --data data/afre/research-days.json --policy data/afre/policy.host-bound.json --limits configs/afre/account.example.json --out data/afre/structural-labels.json
python -m app.orb.adaptive.cli fit-frequency --labels data/afre/structural-labels.json --train-end YYYY-MM-DD --calibration-end YYYY-MM-DD --event RETURN_INSIDE_OR --out data/afre/frequency-model.json
```

Training precedes calibration, which precedes evaluation. The label's full horizon must have become available before its split boundary. One event/horizon/context is not repeated as many independent same-date observations. Status is unsupported for missing support or synthetic data. A fitted table is not automatically a calibrated or deployed model. Inspect test metrics, cell/date coverage and errors; no fitted real model is bundled.

Model code/policy/universe/time identities are checked at prediction. Unseen cells or unsupported symbols return UNESTIMATED. The default probability remains null. Structural return-inside probability is not stop-out probability, and its complement is not the chance a fade wins.

The runtime defines four additional action-specific forecast questions but does not implement numerical estimators or full dedicated maturity-label pipelines for those four. Their explicit unestimated output prevents accidental use as made-up confidence.

## Complete wait/action-policy comparisons

```text
python -m app.orb.adaptive.cli label-actions --data data/afre/one-symbol-research-days.json --policy data/afre/policy.host-bound.json --limits configs/afre/account.example.json --anchor-minute 565 --out data/afre/action-labels.json
python -m app.orb.adaptive.cli fit-value --labels data/afre/action-labels.json --train-end YYYY-MM-DD --out data/afre/value-model.json
```

565 is 09:25 IST and is an example registered anchor, not a recommendation. Every counterplan starts from the same information and follows its frozen later trigger; it is not a hindsight-perfect retest. The helper deliberately rejects multi-symbol action datasets: these are one-symbol conditional experiments. Their estimates do not replace the whole-universe study or independent market dates. Synthetic alternatives do not create new observations.

A supported value provider compares common-budget net outcomes with abstention, using a declared lower-bound criterion. Without one, the priority selector is a frozen deterministic baseline, not a numerical expected-value claim. Code exports `monitor.shadow_regret` only for retrospective diagnostics; the future winner never chooses the earlier real decision.

For model-bound whole-policy studies, use the Python `prove_policies` interface with fully loaded and verified providers. The CLI refuses to silently discard model bindings. Train/calibrate/test the models on dates earlier than the later controller study; changing the model alters the deployment policy hash. Freeze the model during a session. No automatic online deployment exists.

## Offline reviewed proof

Only after a genuinely eligible real-data report and independent review:

```text
python -m app.orb.adaptive.cli review --proof data/afre/proof.json --key-file D:/TradeVisionSecrets/afre/review-key.bin --reviewer local-operator --phrase I_REVIEWED_REAL_DATA_POLICY_AND_HOLDOUT --out data/afre/reviewed-proof.json
```

The local review binds the full report and expires. Signing refuses synthetic or ineligible reports, changed code and malformed date partitions. At runtime, permission also checks policy, model, source-code, universe and account-budget equality, current clock/kill switch, day allowance and plan feasibility. An HMAC signature authenticates who held your local review key; it cannot verify that a human honestly described the dataset.

`TRADEVISION_AFRE_PROFILE=exclusive-paper` additionally requires the host-bound D1 path, account isolation confirmation, no unreconciled legacy activity today, a review artifact and its secret key. No bundled signed review grants this release paper permission. Do not weaken gates to make the example light up.

A user paper trade still requires `RECORD_SIMULATED_PAPER_TRADE` for its exact current proposal. Reviewed policy eligibility is not human approval of every subsequent trade.
