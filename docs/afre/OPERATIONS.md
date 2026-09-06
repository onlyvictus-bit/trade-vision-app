# AFRE local operations

## Profiles and configuration

| Environment variable | Purpose |
|---|---|
| `TRADEVISION_AFRE_PROFILE` | `off` (default), `shadow`, or `exclusive-paper`. |
| `TRADEVISION_AFRE_POLICY` | Absolute path to server-owned validated Policy JSON. |
| `TRADEVISION_AFRE_LIMITS` | Absolute path to server-owned AccountLimits JSON. |
| `TRADEVISION_AFRE_DB` | Local SQLite runtime ledger, not the old JSON ledger. |
| `TRADEVISION_AFRE_TOKEN` | Private local API token, at least 32 characters. |
| `TRADEVISION_AFRE_FORECAST_MODEL` | Optional model artifact matching the policy's exact forecast hash. |
| `TRADEVISION_AFRE_VALUE_MODEL` | Optional action-value artifact matching policy/rules/budget hashes. |
| `TRADEVISION_AFRE_REVIEW` | Current offline-reviewed proof artifact; required for paper. |
| `TRADEVISION_AFRE_REVIEW_KEY_FILE` | Secret local HMAC review-key file, at least 32 bytes; required for paper. |
| `TRADEVISION_AFRE_ACCOUNT_EXCLUSIVE_CONFIRMED` | Must be `1` for exclusive-paper, only after actually isolating this account. |

Policy, budgets, model artifacts and paper permission are not accepted from event HTTP requests. Restart under a new versioned session/policy after approved changes. An existing day's persisted policy or account limits cannot be silently replaced.

Use the existing application entry point with loopback binding. Do not expose this release directly to the public Internet. The local token is not a complete organizational identity, per-user RBAC, TLS, rate-limiting or remote deployment system. Use separate secrets for development and deployment; no credentials or supported model are bundled.

## Route contract

All new routes require `Authorization: Bearer <local-token>` and live under `/api/v1/orb/adaptive`.

| Method/path | Function |
|---|---|
| GET `/status` | Version/safety/policy/account capability status. |
| GET `/scenario-registry` | Exact original 30 source records, identified as unverified source claims. |
| POST `/sessions/{YYYY-MM-DD}` | Start an immutable account/day with explicit verified prior references. |
| POST `/sessions/{day}/events` | Ingest newly available feature/execution/reference evidence at one watermark. |
| POST `/sessions/{day}/timer` | Server-owned clock expiry event; cannot supply a client clock override. |
| GET `/sessions/{day}` | Inspect current state and permission. |
| GET `/sessions/{day}/audit` | Inspect the persisted hash-chain receipts. |
| POST `/sessions/{day}/approve` | Approve only the exact current server-owned proposal/hash/quantity and explicit phrase. |
| POST `/safety/kill` | Integrated host: trigger persistent kill switch; never resets/enables live trading. |

The standalone API constructor omits the integrated host kill route; `integration.mount` adds it. Strict request schemas and example shapes are exported under `docs/afre/schemas/`. Successful research or shadow decisions do not auto-approve a user paper trade.

## Feeding existing candles

Use `adapters.from_candle_series` with a real per-timestamp availability map, source ID and price-basis identifier. The old `CandleSeries` timestamp alone does not establish when a bar was actually available. Unknown volume is rejected rather than changed to zero. Required prior references must be from a strictly earlier verified trading session with compatible adjustments. A previous date string by itself does not verify an exchange calendar.

Send complete native 3m or 5m feature prefixes incrementally through `EventBatch`; execution bars must nest into that feature resolution and use the declared source/basis conventions. Batch simultaneous symbol observations at the same availability watermark. The selector waits for aligned closes across the declared universe; silently missing symbols do not become neutral market breadth.

The source must deliver the closing execution observations even after the new-entry cutoff. A timer can expire an entry or mark a missing outcome unknown, but cannot supply a missing market price. Validate finer-to-feature aggregation outside the service before attesting a real dataset. Five-minute OHLCV cannot be converted into authentic three-minute candles.

`REFERENCE_VERSION_AVAILABLE` is represented through timestamped capability updates. The current runtime does not hot-swap earlier-session price references inside an existing session; conflicting corrections are quarantined and investigated. Preserve original as-of records and use a new explicitly versioned research run for corrected history.

## Approval and account isolation

Each accepted proposal freezes direction, structural stop, reward multiple, entry envelope and quantity ceiling. The target is deterministically instantiated once from actual modeled fill. A stale screen cannot approve a superseding proposal. Only a later eligible whole execution-bar opening price can fill; there is no retrospective fill at the earlier signal price.

The same SQLite database enforces account/day approval and fill constraints across worker processes. Default policy permits one accepted attempt even if it later cancels. After a fill the allowance stays consumed. A failure diagnosis does not authorize a revenge trade. Shadow alternatives are diagnostics, not new human trades.

For exclusive-paper, stop other writers and reconcile old records first. The profile locks non-AFRE mutating HTTP routes and refuses legacy approvals detected today. This will also block old mutation-dependent UI actions; the new authenticated kill route remains available. Do not run the old simulator, Stock App ledger, another database or a manual process against the same account concurrently and expect cross-ledger locking. There is no silent migration.

## Persistence, backup and recovery

Use a local filesystem, not a shared network filesystem for the runtime SQLite database. The store uses WAL, full synchronization, parameterized queries, explicit write transactions, a busy timeout and append-only audit receipts. Storage failures do not grant permission. Changes to checkpoint/audit hashes are detected. Physical loss or a privileged operator deleting the database is outside hash-chain protection.

Use `Store.backup(destination)` from the Python interface for a consistent SQLite backup to a new file. Do not copy only the main `.sqlite3` file while writers are active and omit its WAL. Test restore into a separate stopped instance, validate its account/day and audit state, and verify no other writer remains before resuming. Preserve model/policy/review artifacts alongside backups. Backups contain research data; apply local access controls.

The source installer and rollback helper never delete the database. Rolling back source is not rolling back a trade. A new software version changes the proof binding. Retain historical outputs and revalidate new code rather than forcing old signatures to pass.

Monitor disk usage and audit size. This release does not automatically prune old sessions, silently purge evidence or guarantee a retention capacity. The host verifier reports import/test failures, not deployment health. Exercise recovery from process termination, full disk, database corruption, source lag and host-clock faults in your real environment.

## Incident behavior

Invalid required data blocks affected new entries. Existing approved/filled accounting is processed first; missing required execution intervals produce UNKNOWN rather than a fictional liquidation. A triggered kill switch cancels or blocks new entries, while fixed open-position accounting continues when valid prices arrive. A data revision preserves the old forecast and quarantines the session. Do not simply clear the ledger to regain a daily allowance.

The timer task is created and canceled through the application's lifespan, preserving an existing yielded lifespan state. It journals only due transitions. The server clock must be trustworthy; the event API does not accept future prices by changing a request clock. A provider outage is not remedied by repeated engine calls.
