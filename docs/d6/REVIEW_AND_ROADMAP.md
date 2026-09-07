# Proposed architecture review and implementation order

## Evidence status

The existing repository was inaccessible in this session. The rows below are
review targets and recommended design changes, NOT confirmed repository defects.
D6 and associated safeguards are implemented in the accompanying reference module.
The project completion estimate and actual engine arrangement remain unverified.

## Corrected application flow

```
User selects stock(s) and INTRADAY or SWING
  -> Instrument, calendar and eligibility resolution
  -> Fresh point-in-time data snapshot (immutable revision)
  -> Closed-bar/availability/integrity gates
  -> Shared feature DAG (one computation per feature/snapshot)
  -> Regime/context facts + independent setup detection
  -> Raw LONG evidence and raw SHORT evidence
  -> Historical/analogue evidence conditional on side/setup/regime
  -> Independent risk observations and explicit vetoes
  -> D6 preferred hypothesis, side-specific evaluation, economics and validation
  -> Bounded adversarial checks + audited WAIT / WATCH / PAPER-CANDIDATE
  -> Separate account-wide allocator and final state/expiry check
  -> Paper execution state machine, reconciliation and exit manager
  -> Outcome attribution and quarantined offline research
```

The feature DAG is a directed dependency graph, not an instruction to sequentially
run every indicator. Independent calculations may run in parallel, while consumers
wait for their actual dependencies. Optional analyses should not delay mandatory
safety gates. A timeout must retain the distinction between absent optional
information and failed mandatory information.

## Authority matrix

| Component | May contribute | Must not do |
|---|---|---|
| Data and point-in-time validator | Data availability, revision, hard veto | Infer direction or invent missing bars. |
| Feature/context engines | Causal features and regime/context facts | Issue orders or overwrite a safety veto. |
| Setup detector | Explicit side, invalidation, entry/stop/target hypothesis | Manufacture a setup from a negative risk-adjusted score. |
| Directional evidence engines | Independent LONG and SHORT support | Treat data/event/liquidity risk as bearish evidence. |
| Historical/9C-style analogue engine | Side-conditional outcomes, support size, uncertainty | Reauthorize a failed risk/economic gate or use future neighbors. |
| Risk/behavior/trap engines | Nonnegative risk severities and vetoes | Select an opposite side because danger increased. |
| Economics/validation | Cost/stress diagnostics and valid research evidence | Assume a profitable target/stop model or use demo statistics. |
| D6 final candidate authority | WAIT, WATCH or one paper candidate | Submit an order or fall back to the opposite blocked setup. |
| Account allocator | Final capacity veto and atomic reservation | Convert lack of capacity into higher directional conviction. |
| Paper execution/exit state machine | Idempotent simulated orders and lifecycle management | Treat every reevaluation as a new trade. |
| Language-model explanation | Explain recorded facts, rejection reasons and alternatives | Change policy, fabricate evidence, sign validation or override a veto. |

Names here describe roles, not verified classes or paths in the current project.

## Highest-priority review targets

| Priority | Review target | Required implementation/verification |
|---|---|---|
| P0 | Mixed direction/risk arithmetic | Map raw contributions; enforce D6 upstream through final response. |
| P0 | Multiple final-decision authorities | One candidate authority; explicit veto precedence; trace all legacy paths. |
| P0 | Lookahead and stale higher-timeframe features | Availability timestamps, closed HTF bars, revision-aware cache and replay tests. |
| P0 | Missing inputs becoming optimistic defaults | Required-source vetoes; missing risk is unknown, not safe. |
| P0 | Duplicate trades or shared-capital races | Account-wide reservations and order idempotency separate from evaluation logs. |
| P1 | Correlated indicator vote inflation | Fixed group budgets and fixed denominators; empirically evaluate families. |
| P1 | Historical match selection and overfitting | Point-in-time neighbor indexes, purging, held-out regimes and dependence-aware intervals. |
| P1 | Gross-only trade economics | Actual cost models, adverse execution scenarios, whole-lot sizing and gap-aware modeled risk. |
| P1 | Endless "reasoning" retries | Bounded scenarios and data-triggered reevaluation; never relax gates to force a trade. |
| P1 | Inefficient recomputation | Cache by symbol/horizon/bar-close/data-revision/feature-config; compute shared features once. |

## Autonomy with boundaries

An autonomous supervisor should ask checkable questions: Is this information
available now? Which explicit setup exists? What supports each side independently?
What invalidates it? Does it survive adverse modeled costs and gaps? Is the research
artifact applicable? Is capacity still available? Which new observation can change
WAIT/WATCH? Each answer should be a typed fact, calculation or reason code.

The supplied supervisor runs baseline plus six worsening-risk checks. The stress
scenario set is bounded to 16, source registry to 128 and setup count to two. It
does not hallucinate new probabilities or keep looping until it finds permission.
A new observation or explicit policy/research revision is needed for a new useful
evaluation. Repeated text reasoning on identical evidence is not new information.

Failure anticipation means checking a declared fault/scenario library, not predicting
all failures. Add actual feed outages, instrument restrictions, large gaps, spread
expansion, rejected fills, partial fills, stale positions and unavailable exits to
the paper simulator. Keep unexplained residual risk visible. Never equate a finite
scenario suite with exhaustive safety in real markets.

## Intraday and swing separation

Use different horizon-specific setup specifications, validation populations,
freshness limits, holding-period labels, gap/carry assumptions and exit rules.
An intraday permission does not authorize carrying a position overnight. A swing
signal does not inherit intraday short eligibility. Resolve actual product and
instrument permissions from authoritative current broker/exchange information.
Maintain one shared account-level risk budget across both horizons.

## Rollout

First, map existing producers and all final consumers. Second, integrate D6 behind
a read-only shadow adapter and collect discrepancies. Third, implement/verify the
validation producer and point-in-time replay. Fourth, enable only paper execution
after allocator, lifecycle and exit tests pass. Consider live use only as a separate
release decision with the necessary evidence and current regulatory review.

Research updates should be quarantined: candidate model -> chronological held-out
validation -> shadow/paper evaluation -> reviewed version promotion. Do not let a
recent loss automatically change thresholds, retrain a live model or reverse the
next trade. Keep failure labels distinct: bad data, false setup, execution failure,
ordinary losing trade, regime mismatch and model drift require different responses.

## Source notes

This architecture is original engineering advice and must be adapted to the real
checkout. The following primary documentation supports implementation mechanics:

- Python Decimal: https://docs.python.org/3/library/decimal.html
- Python HMAC and constant-time comparison: https://docs.python.org/3/library/hmac.html
- SQLite atomic commits and durability assumptions: https://www.sqlite.org/atomiccommit.html
- Chronological splitting and `gap`: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

These sources do not validate the strategy, the example thresholds, or the supplied
repository. The statistical validation producer is a required external component.
