# Validation and release limits

See the bundle's final `evidence/verification.json`, `TEST_RESULTS.txt`, `junit.xml` and `coverage.json` for measured results. Test counts mean collected pytest cases; 300 seeded mirrored execution paths are additional property inputs inside a test, not 300 independent real-market observations.

## What has been exercised

Strict input validation; known-at and prefix invariance; complete opening-range intervals; failure/fade/reclaim transitions; untouched-PDC requirements; template-specific stops; actual-fill PnL; adverse stop gaps; no future fill shopping; same-bar ambiguity; fixed deadlines; quantity/cost limits; no post-exit excursion contamination; mirrored long/short paths; duplicate and conflicting events; restart and persisted audit integrity; concurrent approval attempts using both threads and spawned processes; proof identity/expiry; host-interface adapters; token/body constraints; timer cleanup; research selection isolation; forecast-label maturity; synthetic-data promotion rejection; and installer conflict/rollback checks.

The complete functional synthetic path examples include a target hit, a reclaim, a losing fade, and a no-entry day. None is a profitability result. Some governance tests intentionally construct a fictional `REAL_ATTESTED` fixture to test review signatures and gates; those fixtures use ephemeral test keys and are not shipped as eligible real-market proofs.

## Not executed or established

The entire original repository could not be cloned in the authoring environment. Its complete backend regression, frontend build, real browser interaction, full `app.main` import and real BEL data rerun were not executed. The host verifier is delivered for those checks; a passing bundle test suite does not imply that the original 734/740-test claim was reverified.

Only the environment recorded in `verification.json` was used. In particular, the installed pytest was 9.0.2, while the repository requires pytest >=8.3,<9. The supplied requirements preserve the repository constraint; run the host's actual dependency matrix before release. Windows commands are supplied but Windows execution, filesystem locking semantics and ACLs were not tested on a Windows machine here. Installer tests create a temporary synthetic Git repository and do not constitute installation into the real baseline checkout.

No real stock OHLCV, independently verified event feed, trained supported market model, signed deployment approval, real liquidity/depth proof, or winning controller backtest ships in this package.

## Coverage is not omniscience

The 30 source cases are preserved with observability/protection/opportunity contracts. The X01–X20 mapping identifies implemented guards and explicit unavailable behavior. It does not mean 50 predictive models exist. A news event, dealer gamma, VIX regime, ASM/GSM/T2T status or OI wall cannot be verified by naming it in a JSON registry. `Capability` is an upstream verified-input boundary, not an implemented exchange/data-provider connector.

Two structural forecast targets have executable labelers and frequency-model training. Four other action-dependent forecast questions remain unestimated contracts. Action-outcome training uses separate complete-policy replay; the supplied action dataset helper is restricted to one registered symbol. Multi-symbol deployment still needs the whole-universe controller study.

Calibration criteria, bootstrap block length, thresholds and minimum counts are experimental choices. Their mathematical implementation does not certify empirical calibration, tail coverage, stationarity or profitable selection. Grouped-date uncertainty is an estimate, not a market guarantee.

## Important operational limitations

This is a local, single-machine service. SQLite coordinates processes using the same database, not separate ledgers or applications. The trusted operator owns credentials and can modify files; HMAC authenticates local review, not the truth of an uploaded dataset or protection from a malicious machine owner. The sealed-date register discourages repeated holdout use within the same registry; deleting the database cannot make a previously examined test genuinely untouched.

The input boundary checks each stream's identity, intervals and price basis. It does not independently reconcile every finer execution stream against every aggregated feature candle or a second market vendor. Provide consistent streams and validate aggregation/source revisions before attesting real data. `completeness_attested` and `REAL_ATTESTED` require an actual reviewed dataset manifest; they are not magic verification flags.

Unknown exits remain unknown. There is no automatic reconciliation workflow that invents missing prices, no corporate-action correction feed, no automated security-master/trading-calendar verifier, and no release-grade live-feed service. Source revisions quarantine the existing analysis; repaired data should enter separately versioned research with originals retained.

Storage growth, backups, process isolation, clock synchronization, disk health, local network hardening, incident handling and manual recovery must be tested for the intended deployment. No latency guarantee or failover SLA is supplied. Default profile is off; paper is gated and requires new evidence.

## Promotion checklist

| Gate | This delivery |
|---|---|
| Executable AFRE code and focused tests | Implemented; see actual final results. |
| Reversible local overlay installer | Tested on temporary Git fixtures. |
| Full host backend/import/dependency compatibility | Required, not executed here. |
| Existing UI and verified feed connected | Required, not implemented as a frontend migration. |
| Real-data full-controller chronological proof | Required; no market dataset supplied. |
| Forecast calibration/support validation | Required for numerical forecast authority; no supported model supplied. |
| Account exclusivity and ledger reconciliation | Operator deployment requirement. |
| Sustained paper observations/operational recovery | Required prospective evidence. |
| Broker/live trading | Out of scope; permanently absent. |

Do not relabel this release candidate as production-certified until the applicable gates have evidence.
