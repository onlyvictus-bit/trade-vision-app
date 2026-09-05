# Trade Vision SPEC

## Current Release Scope: v1.94

Trade Vision is a research and explicitly human-controlled local paper-guidance
system. Its current normative pipeline is D1 safety, D2 immutable closed-candle
snapshot, snapshot-bound D3-D5 evidence, D6 sole final-band authority, Jarvis
ORB guidance, explicit simulated-paper recording, and explicit replay outcome
evaluation.

Current invariants:

1. No broker order, OpenAlgo route, live trade, or automatic paper fill is
   created.
2. Every decision receipt is bound to a deterministic D2 `snapshot_hash`.
3. Low evidence, missing required MTF, unavailable proof, adverse liquidity or
   risk, and engine conflict can only preserve or reduce the decision band.
4. Simulated records require an eligible server-stored ticket and explicit
   human approval.
5. Lifecycle outcomes require later closed replay/downloaded candles and use
   conservative stop-first ordering when one OHLCV bar touches stop and target.
6. Outcome reliability is completed-only and reduce-only; it cannot promote a
   playbook or increase trading permission.
7. Local ticket, ledger, and outcome persistence fails closed on corruption or
   lock contention.

Current operational requirement:

8. Periodic frontend refresh must eventually load only the global safety fast
   lane plus the active workspace/subtab. Hidden workspaces must not generate a
   full evidence request wave every 30 seconds.

## Scope: v1.87 Paper Guidance Spine P0

Trade Vision must expose one reproducible, research-only Paper Guidance
contract before connecting setup, memory, structure, Kronos, or arbiter
decisions.

### Requirements

1. D1 validates system mode, kill switch, symbol/timeframe identity, bounded
   input, finite OHLCV, data quality, point-in-time safety, and the absence of
   broker/routing authority.
2. D1 failure returns `WAIT`, stops the pipeline, and does not mint a D2
   snapshot or `snapshot_hash`.
3. D2 includes only candles whose `timestamp_ns + timeframe_duration_ns` is
   less than or equal to `decision_time_ns`.
4. D2 hashes canonical JSON with SHA-256; identical input and decision time
   must produce identical guidance data, snapshot id, and snapshot hash.
5. Support strict close-time validation for 1m, 3m, 5m, 15m, 30m, 1H, 4H,
   and Daily inputs.
6. `PaperTradeGuidance` is typed and locks the safety envelope:
   `research_only=true`, `trade_allowed=false`,
   `paper_execution_attempted=false`, `auto_paper_fill_enabled=false`,
   `broker_credentials_present=false`, `broker_order_created=false`,
   `order_routing_enabled=false`, and `live_trading_blocked=true`.
7. P0 may return only `WAIT` or `WATCH`; even high evidence cannot produce
   `ENTER_PAPER` before downstream spine stages exist.
8. Low evidence remains explicitly flagged and capped at 0.55 or the lower
   configured limit.
9. `POST /api/v1/paper-guidance/run` publishes typed request and response
   schemas through OpenAPI.
10. The older Kronos/Twin shared snapshot must use the same close-time rule so
    an incomplete candle cannot enter sibling research comparison.

### Acceptance Criteria

- `apps/api/tests/test_paper_guidance_spine.py`: 20 passed.
- Existing v0.66/v0.67 Kronos/Twin snapshot tests: 9 passed.
- Full backend regression: 598 passed, 0 failed (2026-07-23).
- No Paper Guidance module import creates broker, OpenAlgo, order, or paper-fill
  authority.

## Scope: v0.72 Real Closed-Candle MTF Pullback

Trade Vision must replace seed/hash-based multi-timeframe direction logic with real closed-candle OHLCV aggregation when point-in-time candle data is available. The feature remains research-only and cannot route orders.

## Requirements

1. Build 3m, 5m, 15m, 1H, daily, and weekly bars from the same immutable 1m source series.
2. Aggregate OHLCV with `open=first`, `high=max`, `low=min`, `close=last`, and `volume=sum`.
3. Drop incomplete/developing aggregate bars from decision logic.
4. Mark developing bars visible only when incomplete source bars exist; they must never be decision-safe.
5. Determine timeframe direction from real closed aggregate close slope, not seed arithmetic.
6. Treat lower-timeframe counter-move inside intact higher-timeframe trend as `lower_timeframe_pullback_inside_higher_timeframe_trend`, recommended action `WAIT`, not hard conflict.
7. Treat higher-timeframe opposition to primary direction as block-level conflict.
8. Preserve research-only safety: `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true`.
9. Preserve deterministic output for identical source data and decision time.
10. Do not remove mock/generated fallback paths; if no point-in-time source exists, fallback must be explicit and deterministic.

## Acceptance Criteria

1. A scenario with 15m long trend and 3m short pullback is classified as a pullback/watch condition, not `NO_TRADE`.
2. Direction records are derived from real aggregate close slope.
3. Incomplete 1H/daily/weekly aggregates are excluded from decision-safe evidence.
4. Every MTF endpoint/report includes no-future-leakage safety flags through the existing envelope/path checks.
5. Existing 9C, indicator cache, and frontend build checks remain green.

## Assumptions

ASSUMPTION: If no imported point-in-time data exists for a symbol, deterministic generated data remains allowed for mock/research screens, but the report notes that it is not real market evidence.

ASSUMPTION: Daily bars use the existing 390-minute NSE-style session approximation until a full exchange-calendar engine is wired into this route.

## Scope: v0.73 Volatility-OOD Before Analogs

Trade Vision must detect abnormal ATR magnitude before 9-candle analog confidence is trusted. A high-similarity shape match is not enough when the current volatility regime is outside the historical distribution.

## Requirements

1. Compute current 9-candle ATR from closed candles only.
2. Compute historical 9-candle ATR values from historical closed windows only.
3. Derive volatility thresholds from historical distribution, not hardcoded constants.
4. Mark `volatility_ood=true` when current ATR is above the historical 90th percentile.
5. Expose `volatility_ood`, `current_atr`, `historical_atr_p90`, `volatility_bucket`, and a gate `9C-G016`.
6. Run volatility-OOD before analog confidence promotion; if volatility-OOD is active, decision must remain `WAIT`.
7. Preserve existing shape-OOD reporting and path analog reporting for normal volatility.
8. Preserve research-only safety fields on all reports.

## Acceptance Criteria

1. Synthetic current ATR above historical p90 returns `volatility_ood=true`.
2. OOD status contains both shape-OOD and volatility-OOD evidence.
3. Decision gate `9C-G016` returns `wait` when volatility-OOD is active.
4. Normal RELIANCE mock/replay data preserves existing analog count behavior.
5. No live trading or paper routing becomes possible.

## Scope: v0.74 Reasoning Arbiter, Audit, and Drift Gate

Trade Vision must add a deterministic reasoning arbiter above the 9C analog/model layer. The arbiter exists to detect dangerous disagreement and abnormal setup flags before any research confidence can be promoted.

## Requirements

1. Detect hard safety flags including `manipulated_looking`, `fake_breakout`, `volatility_ood`, and `shape_ood`.
2. If any hard safety flag is present, force the 9C decision path to `WAIT`.
3. Detect subsystem disagreement across analog, OOD, risk, and HTF votes.
4. Hard conflict must force `WAIT`; soft conflict must cap confidence and avoid `PAPER-CANDIDATE`.
5. Add a deterministic decision audit record that stores subsystem votes, arbiter override state, safety gates, and a stable hash.
6. Add calibration drift monitoring for prediction drift, label drift, latency drift, feature drift, and execution-cost drift.
7. Add gates `9C-G018` and `9C-G019` to the hybrid decision safety gate list.
8. Preserve research-only output: `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true`.

## Acceptance Criteria

1. A manipulated-looking setup with strong analog evidence still returns arbiter override to `WAIT`.
2. A LONG/SHORT subsystem conflict returns hard conflict and confidence action `force_wait`.
3. Decision audit hash is deterministic for identical inputs.
4. Active calibration drift returns gate `9C-G018=wait` and action `demote_to_rule_only`.
5. Hybrid decision output includes gates `9C-G018` and `9C-G019`, plus final reason audit evidence.

## Scope: v0.75B Indicator Cache Integrity and Quarantine

Trade Vision must harden the indicator result cache so it remains a speed/audit layer only. A cache row or artifact must never become probability authority, trading authority, or a silent source of stale indicator values.

## Requirements

1. Cache reuse is allowed only when source snapshot hash, timeframe, indicator registry version, feature manifest version, promoted indicator hash, and artifact SHA all match exactly.
2. Artifact SHA mismatch must return `cache_integrity_status=failed`, must not reuse the artifact, and must recompute if real runtime is requested.
3. Feature manifest or registry mismatch must return a stale status and must not count as reusable evidence.
4. An anomalous snapshot request must return `cache_status=anomalous_snapshot_quarantined`, save no artifact rows, and stay reference-only.
5. Every artifact safety block must include `reference_only=true`, `used_for_probability=false`, `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true`.
6. Disk/write failure must degrade to failed telemetry and must not crash the API.
7. Cache force-recompute must bypass reuse and create fresh artifacts only for clean snapshots.

## Acceptance Criteria

1. Corrupting a saved artifact makes status/results report failed integrity.
2. A row with mismatched feature manifest version is marked stale and is not reused.
3. `anomalous_snapshot=true` saves zero rows and returns quarantine status.
4. All returned rows and artifacts remain reference-only and trading-blocked.
5. Disk write failure returns failed cache rows and does not crash.
6. Same identity cache artifacts are reproducible by cache ID and artifact SHA.
7. Stored volatility context mismatch returns stale status.
8. Force-recompute cannot override anomalous snapshot quarantine.

## Scope: TV-PROD-RED-001 Final Manipulated-Wick Red-Team Gate

Trade Vision must expose one deterministic final red-team proof for the required manipulated-wick failure mode. This report is a release-blocking safety proof, not a trading signal.

## Requirements

1. Simulate a `2.4x ATR` manipulated-wick day.
2. Prove volatility-OOD fires before analog confidence.
3. Prove `manipulated_looking` appears in arbiter consulted flags.
4. Prove strict volatility bucketing reduces matched windows: `matched_after_vol_bucketing < raw_match_count`.
5. Prove continuation boost is `<= 0.0`.
6. Prove decision is only `WAIT` or `WATCH`.
7. Prove `paper_candidate_allowed=false`.
8. Prove cache status is `anomalous_snapshot_quarantined`.
9. Prove `live_trading_blocked=true`, `trade_allowed=false`, and `order_routing_enabled=false`.
10. Expose the report through an API endpoint so frontend/Jarvis can display the safety proof.
11. Jarvis must show the red-team proof as a dedicated panel with pass/fail state, volatility-OOD state, arbiter consulted flags, strict volatility-bucket match reduction, continuation boost, cache quarantine, decision, and trading-safety locks.
12. If the red-team report is still loading or unavailable, Jarvis must display a fail-closed pending state: no trade authority, order routing blocked, live trading blocked, and release status pending/blocked. It must not show `unsafe` because of missing frontend data.

## Acceptance Criteria

1. Endpoint `/api/v1/behavior/red-team/tv-prod-red-001` returns `red_team_id=TV-PROD-RED-001`.
2. All required red-team assertions return `passed=true`.
3. Any failure in volatility, arbiter, cache, decision, or trading-safety checks marks the report as failed.
4. Jarvis renders the same backend report without local recomputation and keeps `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true` visible.
5. Jarvis pending-state fallbacks are conservative and never imply live trading is enabled or unsafe due only to missing data.

## Scope: Jarvis Evidence Loader Concurrency Guard

Jarvis loads a large evidence surface. The frontend must not start every endpoint request at once because browser and dev-server resource limits can cause `ERR_INSUFFICIENT_RESOURCES`, leaving critical safety panels stuck in pending state.

## Requirements

1. The frontend evidence loader must use bounded concurrency for API calls.
2. Request order must remain deterministic so destructured `AppData` fields still map to the intended endpoint result.
3. Endpoint contracts, response envelopes, and backend routes must not change.
4. If an individual request fails, only the affected panel remains unavailable; healthy evidence panels must still hydrate.
5. Any unavailable panel remains fail-closed and no trade route is enabled.
6. Jarvis red-team proof must remain visible as pending/blocked while hydration is in progress.
7. Critical release-safety evidence, including TV-PROD-RED-001, must be fetched before bulk evidence hydration and rendered as soon as it arrives.
8. Scheduled refreshes must not overlap; if a refresh is already running, the next timer tick must skip instead of starting a second request storm.

## Acceptance Criteria

1. Frontend typecheck/build passes.
2. Browser snapshot no longer shows bulk `ERR_INSUFFICIENT_RESOURCES` during Jarvis load under normal local verification.
3. The red-team panel remains present and fail-closed during loading.
4. A single endpoint failure produces a partial-evidence warning instead of forcing the whole workspace into an offline shell.
5. TV-PROD-RED-001 can hydrate even while slower non-critical evidence endpoints are still pending.

## Scope: SQLite State Startup And Lock Contention Guard

Trade Vision stores local audit, replay, capability, indicator-cache, and Jarvis evidence state in SQLite during local/research operation. The API must start with the default configured DB path and must tolerate short-lived lock contention from another local process without immediately failing request handling. This guard is for reliability only; it must not weaken audit, storage integrity, or trading-safety blocks.

## Requirements

1. The default DB path must remain `trade-vision-app/data/trade_vision_state.db` unless `TRADEVISION_STATE_DB` explicitly overrides it.
2. SQLite connections must use a bounded busy timeout so transient local locks wait before failing.
3. The same timeout behavior must apply to shared in-memory test DB connections and file-backed DB connections.
4. Storage initialization must create the schema at a newly configured DB path.
5. Storage status must report the configured DB path and table counts after initialization.
6. This change must not create broker routes, live order routes, or hidden execution paths.

## Acceptance Criteria

1. A storage startup regression can point `storage.DB_PATH` to a fresh temp file, call `init_db()`, and read `/api/storage/status`-equivalent counts through `storage.storage_status()`.
2. `connect()` applies `PRAGMA busy_timeout` on every connection.
3. Existing storage, red-team, indicator-cache, and 9C arbiter tests still pass.

## Scope: Indicator Cache Test Continuity Guard

The official v0.71-v0.77 roadmap requires indicator-cache tests `ICACHE-001` through `ICACHE-020`. The implementation must not leave numeric gaps in that contract because gaps hide unverified behavior in cache identity, artifact integrity, force recompute, stale reads, and safety envelopes.

## Requirements

1. `ICACHE-005` through `ICACHE-012` must exist as executable backend tests.
2. The tests must prove cache IDs are deterministic and derived from the exact source identity fields.
3. The tests must prove artifact payloads contain canonical identity, context, telemetry, and safety sections.
4. The tests must prove force recompute writes the same deterministic identity instead of creating duplicate authority.
5. The tests must prove missing or invalid artifacts are treated as failed/stale and never reused.
6. The tests must prove cache rows can never enable probability, paper-candidate promotion, or order routing.
7. The tests must keep default behavior research-only and live blocked.

## Acceptance Criteria

1. Focused indicator-cache test selection passes for `icache`.
2. `ICACHE-001` through `ICACHE-020` are present with no numeric gaps.
3. Safety fields remain `used_for_probability=false`, `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true` for cache save, status, results, and delete paths.

## Scope: Transport Trace Integrity Window Guard

OpenAlgo transport trace integrity verification may run against a bounded result window. A bounded query can return the tail of a delivery trace chain without the first/root trace. The verifier must not falsely report a `previous hash mismatch` only because the predecessor is outside the query window. It must still detect real tampering when the predecessor exists and does not match, or when a full delivery chain is explicitly verified.

## Requirements

1. Global trace verification must support bounded windows without false previous-hash failures.
2. If the first returned trace for a delivery references a predecessor outside the current window, the verifier must fetch the immediate predecessor and compare the stored hash.
3. If no predecessor exists and the first returned trace has a non-null previous hash, verification must fail.
4. Trace hash verification must remain unchanged for every returned trace.
5. Explicit tampering tests must still fail while the trace is modified and pass after restore.
6. Release readiness and final audit must remain brokerless and live-blocked.

## Acceptance Criteria

1. A new regression proves truncated-window trace integrity remains valid when the predecessor hash matches the omitted predecessor.
2. Existing tamper detection still detects modified trace JSON.
3. Full backend regression passes with the default local DB.

## Scope: Pytest Cache Hygiene Guard

The local test runner must not emit recurring cache warnings caused by a malformed or inaccessible generated `.pytest_cache` path. Pytest cache is generated state, ignored by git, and must be safe to delete/recreate without changing application behavior or test outcomes.

## Requirements

1. The fix may remove only the generated project-local `.pytest_cache` path if removal is permitted.
2. If `.pytest_cache` is inaccessible or cannot be safely removed, pytest must use `.test_cache/pytest` as the project-local writable cache directory instead.
3. The fix must not remove source files, test files, databases, logs, artifacts, or user data.
4. Test configuration must continue to discover `apps/api/tests` through `trade-vision-app/pytest.ini`.
5. The backend test suite must use a usable writable cache path without cache warnings.
6. Trading safety behavior must remain unchanged.

## Acceptance Criteria

1. Pytest cache writes go to a normal generated cache directory after the next test run.
2. A focused backend test run no longer emits `PytestCacheWarning`.
3. Full backend regression remains green.

## Scope: Research Stack Local Verification Tool

Operators need a deterministic local smoke verifier for the brokerless research stack after starting the API and OpenAlgo adapter simulator. The verifier must prove API health, signed adapter health, deployment readiness, security posture, and final release audit state without creating broker credentials, live orders, or order-routing authority.

## Requirements

1. Add a standalone script under `scripts/` that uses only Python standard library modules.
2. The script must accept API base URL, adapter URL, service identity, and timeout as arguments or environment defaults.
3. The script must sign the adapter `/health` request with the same HMAC service identity protocol used by the transport layer.
4. The script must check these API endpoints:
   - `/health`
   - `/api/v1/openalgo/security/posture`
   - `/api/v1/deployment/readiness`
   - `/api/v1/release/final-audit`
5. The script must treat any unsafe flag as failure:
   - `broker_credentials_present=true`
   - `broker_order_created=true`
   - `order_routing_enabled=true`
   - `live_trading_blocked=false`
6. The script must output machine-readable JSON and exit `0` only when all checks pass.
7. Missing adapter secret must fail clearly; it must never use broker credentials as a substitute.
8. Unit tests must cover success, adapter auth failure/missing secret, unsafe payload detection, and endpoint failure handling.

## Acceptance Criteria

1. Unit tests for the verifier pass without starting network services.
2. Running the verifier against an unavailable stack fails closed with clear JSON.
3. Existing backend regression remains green.

## Scope: One-Command Local Research Stack Verification Wrapper

Operators need a single local command that starts the existing research stack, waits for readiness through the brokerless verifier, emits the final JSON verifier report, and stops only the processes it started. This wrapper must make local readiness reproducible without adding new runtime services or bypassing the existing safety gates.

## Requirements

1. Add a PowerShell wrapper under `scripts/` that calls the existing `start-research-stack.ps1`, `verify_research_stack.py`, and `stop-research-stack.ps1`.
2. The wrapper must require `TRADEVISION_ADAPTER_SHARED_SECRET` from the environment or an explicit parameter; it must never accept broker credentials.
3. The wrapper must retry verification until the timeout expires because API and adapter startup are asynchronous.
4. The wrapper must stop the stack in a `finally` block if and only if it successfully started the stack.
5. The wrapper must preserve all safety semantics from `verify_research_stack.py`; it must not transform failed verification into success.
6. The wrapper must output the final verifier JSON so operators can inspect exact failing checks.
7. Static tests must prove the wrapper calls start, verify, and stop scripts, uses `finally`, and does not contain live-order/broker execution commands.

## Acceptance Criteria

1. The wrapper passes PowerShell parser validation.
2. Static tests verify the wrapper’s safety structure.
3. Existing backend and frontend checks remain green.
## Scope: Idempotent Storage Initialization Runtime Guard

Repeated read/write helpers call `storage.init_db()` defensively. That reliability pattern must stay, but schema creation and audit hash backfill must not rerun on every storage operation in the same process because large external-AI/Jarvis audit regressions become slow enough to exceed local command timeouts. Initialization must become idempotent per active database target without weakening fresh database startup, migration safety, or audit-chain integrity.

## Requirements

1. `storage.init_db()` must run schema creation, migration guards, and audit backfill once per active `DB_PATH` target in a process.
2. If `DB_PATH` changes, the new target must be initialized independently.
3. If a file-backed `DB_PATH` was initialized but the file disappears, `init_db()` must initialize it again instead of trusting stale process memory.
4. `:memory:` mode must remain supported and must keep the shared in-memory connection behavior.
5. Audit hash backfill must still run during the first initialization for each target and during explicit audit integrity verification.
6. The optimization must not skip schema/migration work for a fresh configured database path.
7. The optimization must not change broker/order routing behavior or any trading safety gates.

## Acceptance Criteria

1. A focused test proves repeated `init_db()` calls for the same target do not rerun audit backfill.
2. A focused test proves changing `DB_PATH` to a fresh file still initializes that database.
3. Existing storage startup tests remain green.
4. Slow external-AI/Jarvis tests remain semantically green after the optimization.

## Scope: Bounded Deployment Database Integrity Cache

Deployment readiness and final-release audit paths must verify database integrity, but repeated `PRAGMA integrity_check` calls inside the same Jarvis/external-AI request must not make review-only endpoints too slow to operate. Integrity results may be cached only when the database file fingerprint proves the checked state has not changed.

## Requirements

1. Cache database integrity results by resolved database path plus file size and modification time.
2. Include SQLite sidecar WAL/SHM file size and modification time in the fingerprint when those files exist.
3. Never reuse an integrity result when the database or sidecar fingerprint changes.
4. Keep the cache in process memory only; do not persist readiness cache state to disk.
5. Preserve fail-closed behavior: unreadable or invalid databases must still return failed integrity.
6. Preserve release safety: cached readiness cannot enable broker credentials, broker orders, order routing, OpenAlgo export, or live trading.

## Acceptance Criteria

1. A focused test proves two integrity checks against an unchanged database open SQLite once.
2. A focused test proves a database write changes the fingerprint and forces a fresh integrity check.
3. Existing deployment/readiness/final-audit tests remain green.
4. External-AI/Jarvis review packet tests remain green and materially faster.

## Scope: Review-Only Preflight Fast Path For External AI Correction Packets

External AI correction-review packets are display/review-only artifacts. They must include verified evidence, reliability status, and explicit safety gates, but they must not run full final-release audit or deployment smoke checks on every packet build because those checks are reserved for readiness/final-audit endpoints and are too expensive for interactive review packet generation.

## Requirements

1. Correction-review packet generation must use a lightweight review-only preflight evidence object.
2. The lightweight preflight object must keep `preflight_version = jarvis-preflight-evidence.v1.01` so the existing review preflight contract remains stable.
3. The lightweight preflight object must set `paper_review_allowed=false`, `openalgo_dry_run_allowed=false`, and `live_trading_allowed=false`.
4. The lightweight preflight object must explicitly report `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true`.
5. Full deployment readiness, final release audit, release export, and deployment smoke endpoints must remain unchanged.
6. No correction-review packet may gain OpenAlgo export, broker credential, broker order, or live trading authority.

## Acceptance Criteria

1. Correction-review packet tests still return ready-for-correction-review when verified evidence exists.
2. Correction-review packet tests prove OpenAlgo and live trading remain blocked.
3. A focused test proves correction packet generation does not call `build_final_release_audit()`.
4. Final release audit tests remain green.

## Scope: Timezone-Safe VWAP Band Grouping

The stock-app vendor indicator bridge must not drop timezone information while grouping intraday candles into daily or weekly VWAP-band sessions. Pandas `DatetimeIndex.to_period("W")` emits a warning and discards timezone information, which is unacceptable for intraday trading evidence because session boundaries depend on the exchange timezone.

## Requirements

1. VWAP band grouping must avoid `DatetimeIndex.to_period()` on timezone-aware indexes.
2. Daily grouping must use timezone-aware normalized calendar dates when the index is a `DatetimeIndex`.
3. Weekly grouping must derive a timezone-aware week-start key from normalized timestamps and weekday offsets.
4. Output values for daily/weekly VWAP bands must remain aligned to the original candle index.
5. The fix must preserve non-DatetimeIndex fallback behavior.
6. Indicator outputs must remain explanation/research-only unless already promoted by existing safety gates.

## Acceptance Criteria

1. A focused test proves weekly `_vwap_bands()` on an IST timezone-aware index emits no timezone-dropping warning.
2. The returned VWAP-band frame preserves the original index and row count.
3. Existing FMFM300 and indicator-cache tests remain green.

## Scope: Frontend Production Bundle Split

The frontend production build must split stable third-party framework code from Trade Vision application code. This must reduce browser download and parse pressure without changing the Jarvis workspace, chart panels, safety banners, API contract validation, or route behavior.

## Requirements

1. Configure deterministic vendor chunking in Vite.
2. Split React runtime code into a `react-vendor` chunk.
3. Split Zod validation code into a `validation-vendor` chunk.
4. Do not raise `chunkSizeWarningLimit` as a substitute for real chunking.
5. Do not change application routing, workspace layout, chart rendering, safety gates, API endpoints, or contracts.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. Production build output contains separate vendor chunks.
4. Production build output emits no large-chunk warning.

## Scope: Shared Frontend UI Primitive Extraction

`App.tsx` contains workspace logic, Jarvis evidence panels, chart rendering, API loading, and shared UI primitives in one large file. The first safe modularization step is to extract dependency-light shared primitives while preserving all workspace behavior.

## Requirements

1. Move reusable primitive components and display formatters out of `App.tsx`.
2. Preserve the exact rendered class names and markup shape for `Panel`, `Card`, `Metric`, and `Status`.
3. Preserve formatter behavior for `pct()` and `money()`.
4. Do not change API loading, Jarvis room logic, chart rendering, credentials UI, safety banners, workspace navigation, or backend contracts.
5. Keep the new module typed and dependency-light.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. Full backend regression remains green.
4. Source search proves the primitives live in the shared module and are imported by `App.tsx`.

## Scope: Reference Workspace Component Extraction

The `Knowledge` and `Implementation` workspaces are display-only reference surfaces. They show the documentation graph and capability manifest but do not own trading decisions, chart calculations, credentials, external-AI calls, or order-like behavior. They are the safest workspace-level extraction target after primitive extraction.

## Requirements

1. Move `Knowledge` and `Implementation` workspace components out of `App.tsx`.
2. Preserve the rendered workspace structure, panel titles, badges, metric labels, and capability-table layout.
3. Keep the extracted module display-only: no API calls, no side effects, no direct trading state mutation.
4. Keep `App.tsx` responsible for routing active workspaces and passing loaded data into extracted workspaces.
5. Do not change Jarvis, chart, research, behavior, replay, system, safety, credential, or external-AI logic.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. Full backend regression remains green.
4. Source search proves `Knowledge` and `Implementation` definitions live outside `App.tsx` and are imported by `App.tsx`.

## Scope: Safety Display Panel Extraction

`RiskPanel`, `OrderPathPanel`, and `IntegrityPanel` are safety-facing display panels used across the cockpit, market DNA, research, and replay views. They are small enough to extract safely, but their wording and fail-closed labels must be preserved exactly because users rely on them to distinguish mock/simulation-only state from unsafe live behavior.

## Requirements

1. Move `RiskPanel`, `OrderPathPanel`, and `IntegrityPanel` out of `App.tsx`.
2. Preserve existing panel titles, badges, metric labels, fallback values, and text rendering.
3. Keep the extracted module display-only: no API calls, no `fetch`, no state mutation, no credential handling, no broker/OpenAlgo/Gemini/Grok calls, and no kill-switch control.
4. Preserve all existing call sites and data ownership in `App.tsx`.
5. Do not change Jarvis, chart, research, behavior, replay, system, credentials, external-AI, or order-path semantics.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. Full backend regression remains green.
4. Source search proves the extracted module contains the panel definitions and `App.tsx` imports them.
5. Source search proves the extracted module has no direct API/fetch/broker/OpenAlgo/Gemini/Grok/credential/kill-switch control calls.

## Scope: AI Credential Vault Panel Extraction

`AiCredentialsPanel` is a sensitive UI because it accepts Gemini and Grok API keys. It is not display-only, but its authority is intentionally narrow: save, test, and clear API keys through the backend credential-vault endpoints. It must never handle browser sessions, usernames, passwords, cookies, broker credentials, OpenAlgo credentials, order routing, live trading, or external-AI review execution.

## Requirements

1. Move `AiCredentialsPanel` out of `App.tsx`.
2. Preserve all visible labels, button text, password inputs, disabled states, status messages, and local input clearing behavior.
3. The extracted module may call only these API client methods:
   - `saveGeminiCredential`
   - `testGeminiCredential`
   - `clearGeminiCredential`
   - `saveGrokCredential`
   - `testGrokCredential`
   - `clearGrokCredential`
4. The extracted module must not call external-AI review endpoints, OpenAlgo endpoints, broker/order endpoints, kill-switch endpoints, or raw `fetch`.
5. The extracted module must keep `autoComplete="off"` and `type="password"` on secret inputs.
6. The extracted module must continue clearing local secret input state after successful save/test/clear actions.
7. `App.tsx` remains responsible for loading masked credential status from the backend.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. Full backend regression remains green.
4. Source search proves `AiCredentialsPanel` lives outside `App.tsx` and is imported by `App.tsx`.
5. Source search proves the extracted module has no browser-session capture, username/password form, cookie, broker, OpenAlgo, order-routing, kill-switch, live-review, or raw `fetch` calls.
6. Source search proves password inputs remain `type="password"` and `autoComplete="off"`.
7. Displaying backend-reported `browser_password_login_supported` status is allowed only as read-only status text.

## Scope: System Workspace Extraction

The `System` workspace renders already-loaded operational evidence: AI credential vault, pipeline status, persistent storage counts, observability counters, workspace layout, audit integrity, and audit events. It must be separated from `App.tsx` without changing data loading, routing, credential-vault behavior, safety labels, or audit display.

## Requirements

1. Move the `System` workspace component out of `App.tsx`.
2. Preserve all panel titles, badges, metric labels, fallback values, audit rows, and storage path display.
3. Keep `App.tsx` responsible for active workspace routing, refresh behavior, and all API loading.
4. The extracted `System` workspace may render `AiCredentialsPanel`, but must not directly call credential APIs.
5. The extracted `System` workspace must not call raw `fetch`, broker/OpenAlgo/order APIs, external-AI review APIs, kill-switch actions, or live-trading paths.
6. Do not change Jarvis, chart, research, behavior, replay, credentials, or external-AI semantics.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. Full backend regression remains green.
4. Source search proves `System` lives outside `App.tsx` and is imported by `App.tsx`.
5. Source search proves the extracted System workspace has no direct `api.`, `fetch`, OpenAlgo, broker/order, external-AI review, live-trading, or kill-switch action calls.

## Scope: Replay Evidence Panel Extraction

The `Replay` workspace contains replay control actions and display-only evidence panels. Replay controls are stateful and must remain in `App.tsx` for this milestone. Only the display-only evidence panels can be extracted safely: execution simulation, replay archive, point-in-time snapshots, feature version registry, and simulation integrity.

## Requirements

1. Move replay evidence panels out of `App.tsx` into a dedicated display-only component.
2. Preserve panel titles, badges, metric labels, fallback values, archive rows, snapshot rows, feature rows, and integrity rendering.
3. Keep replay seed/session state and `start`, `play`, `pause`, `step`, and `seek` handlers in `App.tsx`.
4. The extracted component must not call the API client, raw `fetch`, replay control APIs, broker/OpenAlgo/order APIs, external-AI review APIs, kill-switch actions, or live-trading paths.
5. Do not change deterministic replay behavior, execution-simulation display values, archive display values, PIT snapshot display values, or feature registry display values.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. Full backend regression remains green.
4. Source search proves replay evidence panel definitions live outside `App.tsx` and are imported by `App.tsx`.
5. Source search proves the extracted replay evidence component has no direct `api.`, `fetch`, replay control, OpenAlgo, broker/order, external-AI review, live-trading, or kill-switch action calls.

## Scope: Replay Evidence Simple-English Clarification

The Replay workspace has two different user-facing concepts that must remain clear. The replay controls in `App.tsx` let the user start, play, pause, step, and seek a deterministic event session. The extracted replay evidence panels explain why that replay is safe, reproducible, and audit-friendly. They do not replace the chart replay workbench in the Research tab and they do not show real broker trade history.

## Requirements

1. Add simple-English explanatory copy to the replay evidence panels.
2. Explain that execution simulation is simulated fill/risk evidence, not a real order.
3. Explain that replay archive sessions are repeatable test sessions, not broker trade history.
4. Explain that point-in-time snapshots are exact data packets used for audit/replay.
5. Explain that feature version rows show which feature definitions were used.
6. Preserve display-only ownership: no API client, raw `fetch`, replay control API, broker/order, OpenAlgo, external-AI review, live-trading, or kill-switch action calls may be added to the extracted component.

## Acceptance Criteria

1. `npm run typecheck` passes.
2. `npm run build` passes.
3. The Replay evidence component contains plain-English distinction text for evidence versus chart replay.
4. The extracted component remains display-only and has no direct action/API calls.

## Scope: Context Maintenance, Graph Refresh, And Handoff Compression

Trade Vision is now large enough that a new AI/chat can waste significant context reading large files before understanding the project. The project needs compact handoff and index files that reduce token use and prevent stale assumptions.

## Requirements

1. Maintain `docs/context.md` as the Fable domain/invariant file (preferred first-read with graph.md).
2. Maintain `TRADE_VISION_README.md` § AI / New-Chat Handoff as the compact handoff (must stay aligned with context.md and IMPLEMENTATION_STATUS tip).
3. Maintain `docs/FILE_DOCUMENT_INDEX.md` §0.6 as the token-saving routing table (merged CONTEXT_INDEX).
4. Maintain `docs/IMPLEMENTATION_STATUS.md` with the latest completed version.
5. Maintain `docs/NEXT_BUILD_TARGET.md` with the next planned version and immediate build target.
6. Maintain `docs/SAFETY_INVARIANTS.md` with non-negotiable safety rules.
7. Maintain `docs/FILE_DOCUMENT_INDEX.md` §7.4 ownership, `docs/FRONTEND_PANEL_MAP.md`, `docs/API_ENDPOINT_INDEX.md`, and `docs/TEST_ID_INDEX.md` as compact indexes.
8. Maintain `docs/graph.md` (includes how-to/update rule at §0) and `docs/graph/project_graph.json` as human + machine graphs.
9. Maintain `TRADE_VISION_README.md` § AI Handoff → Fast continuation + context maintenance so future agents know when docs must be refreshed.
10. Keep `TRADE_VISION_README.md` and `docs/MILESTONE_EASY_EXPLANATION.md` aligned with the latest project status.
11. Do not delete older project content during context maintenance. Merge aligned content or mark stale files for future cleanup.

## Acceptance Criteria

1. `docs/graph/project_graph.json` parses as valid JSON.
2. Graph node and edge counts match actual arrays.
3. Every graph edge references an existing node.
4. `ARCHITECTURE.md`, `SPEC.md`, and `TEST_PLAN.md` mention the v1.62 context layer.
5. `TRADE_VISION_README.md` no longer points to the stale `v0.31` milestone as current.
6. `docs/MILESTONE_EASY_EXPLANATION.md` no longer claims `18 passed` as the current verification state.
7. New AI handoff files clearly identify:
   - latest completed version
   - next target
   - safety invariants
   - files to read first
   - files not to open first because they are large

## Scope: v1.75 Final Confluence Conflict Arbiter

Trade Vision must resolve mixed evidence into one final research-only decision packet. The arbiter must not generate a new signal blindly. It consumes upstream evidence and applies an explicit hierarchy:

```text
risk/safety > data quality > liquidity > market regime > structure/levels > volume/auction > relative strength > indicators > external AI explanation
```

## Requirements

1. Produce a deterministic `FinalConfluenceArbiterReport`.
2. Include `confluence_score`, `evidence_votes`, `conflicts_detected`, `dominant_blocker`, `decision_band`, `confidence_interval`, `final_decision`, and `human_reason_tree`.
3. Downgrade bullish indicators when price is at daily resistance.
4. Reduce long confidence when sector/relative-strength context is weak.
5. Let high trap score override indicator or analog strength.
6. Let event risk cap otherwise strong evidence to `WATCH`.
7. Let liquidity grade C block `PAPER-CANDIDATE`.
8. Let post-entry thesis invalidation override the original entry thesis.
9. Preserve research-only safety: `used_for_probability=false`, `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true`.

## Acceptance Criteria

1. `POST /api/v1/behavior/final-confluence/arbiter/analyze` returns a valid envelope.
2. `GET /api/v1/behavior/final-confluence/arbiter/current` synthesizes current evidence from existing v1.70-v1.74 reports.
3. Tests `test_v175_*` pass.
4. Full backend regression passes with the v1.75 test count.
5. Project graph and context files list v1.75 as the latest verified version.

## Scope: v1.80 Indicator Intelligence Contract + Ontology + Lag-Aware Voting

Trade Vision must understand indicators, not merely list or compute them. Every indicator contract must describe what the indicator is for, when it is misleading, how late it confirms, and whether it is safe for explanation only or eligible for future reliability learning.

## Requirements

1. Extend each locked registry entry with ontology metadata:
   - `purpose`
   - `category`
   - `best_market_regime`
   - `bad_market_regime`
   - `best_timeframe`
   - `signal_type`
   - `direction_meaning`
   - `lag_behavior`
   - `sequential_signal_window`
   - `missing_policy`
   - `false_positive_conditions`
   - `confirmation_rules`
   - `conflict_rules`
   - `trade_usage`
   - `risk_usage`
   - `no_trade_usage`
   - `usable_for_explanation`
   - `ontology_version`
2. Preserve the exact 94-output registry count.
3. Consume existing `confirmation_delay_bars` with:

```text
lag_weight = 1 / (1 + confirmation_delay_bars)
```

4. Ensure lagging/stale indicators cannot promote `WATCH` to `PAPER-CANDIDATE` alone.
5. Ensure unknown/unclassified indicators stay explanation-only.
6. Wire ontology metadata into redundancy and false-agreement checks without rebuilding those engines.
7. Preserve research-only safety: `used_for_probability=false`, `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, and `no_future_leakage=true`.

## Acceptance Criteria

1. `GET /api/v1/behavior/indicators/{indicator_id}/ontology` returns an ontology-enriched registry entry.
2. `POST /api/v1/behavior/indicators/lag-vote` returns delay-adjusted vote evidence.
3. `GET /api/v1/behavior/indicators/intelligence-summary/{symbol}` returns compact ontology/vote coverage.
4. Tests `test_v180_*` pass.
5. Focused backend verification passes for v1.80, v0.60, and envelope routes.
6. Full backend regression passes before v1.80 is marked full-regression verified.

## Scope: v1.81 Per-Indicator Reliability Memory + Outcome Labeling Bridge

Trade Vision must learn whether each indicator actually worked historically for a symbol, timeframe, regime, and session. Reliability must be based on completed outcome labels, not on live guesses or same-candle optimism.

## Requirements

1. Add a label bridge from an indicator signal to future 3/5/9/12/20-candle outcomes.
2. Do not count unresolved/pending horizons as wins.
3. Use conservative stop-first handling when target and stop touch inside the same OHLC candle without lower-timeframe proof.
4. Compute reliability rollups:
   - per-stock reliability
   - per-regime reliability
   - per-session reliability
   - reciprocal signal ratio
5. Apply Bayesian shrinkage when `sample_count < 30`.
6. Quarantine reliability under OOD or regime-shift conditions.
7. Feed reliability into the v1.80 lag-vote preview only as research context.
8. Preserve research-only safety: `used_for_probability=false`, `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, and `no_future_leakage=true`.

## Acceptance Criteria

1. `POST /api/v1/behavior/indicators/reliability/label-signal` labels completed horizons and leaves incomplete horizons pending.
2. `GET /api/v1/behavior/indicators/{indicator_id}/reliability/{symbol}` returns a reliability report with gates and safety flags.
3. `GET /api/v1/behavior/indicators/intelligence-summary/{symbol}` includes a reliability preview.
4. Tests `test_v181_*` pass.
5. Focused backend verification passes for v1.81, v1.80, v0.60, and envelope routes.
6. Full backend regression passes before v1.81 is marked full-regression verified.

## Scope: v1.82 Full Timeframe Contract Expansion + Indicator Reliability UI Drilldown

Trade Vision must treat `30m` and `4H` as first-class closed-candle research timeframes, not frontend-only labels. The indicator reliability drilldown must expose enough information for a trader to see why an indicator is useful, late, low-sample, quarantined, or historically reciprocal.

## Requirements

1. Expand shared backend timeframe contracts to exactly:
   - `1m`
   - `3m`
   - `5m`
   - `15m`
   - `30m`
   - `1H`
   - `4H`
   - `daily`
   - `weekly`
2. Every registry indicator must advertise the same timeframe list.
3. Closed-bar runtime, point-in-time guard, MTF conflict, pattern-by-timeframe memory, shared snapshots, walk-forward weighting, and feature-store writes must understand `30m` and `4H`.
4. Existing endpoint paths must remain backward-compatible where already published.
5. `IndicatorReliabilityReport` must expose UI drilldown fields: purpose, category, confirmation delay, lag weight, sample count, reliability state, reciprocal warning, and quarantine reason.
6. The frontend panel map must include an indicator reliability drilldown panel.
7. Preserve research-only safety: `used_for_probability=false`, `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, and `no_future_leakage=true`.

## Acceptance Criteria

1. `GET /api/v1/behavior/indicators/registry` returns nine allowed timeframes for every indicator.
2. `GET /api/v1/behavior/features/seven-timeframe/current` emits nine closed-bar records while preserving the legacy route name.
3. `POST /api/v1/behavior/guards/point-in-time` accepts `30m` and `4H` and blocks incomplete/future bars correctly.
4. `GET /api/v1/behavior/timeframes/conflict/current` and `GET /api/v1/behavior/patterns/by-timeframe` include `30m` and `4H`.
5. `GET /api/v1/behavior/frontend/panel-map` includes `indicator_reliability_drilldown_v182`.
6. Tests `test_v182_*` pass.
7. Full backend regression passes before v1.82 is marked full-regression verified.

## Scope: v1.83 Persistent Indicator Signal History Store + Reliability Drilldown Frontend Rendering

Trade Vision must persist indicator signal outcomes so reliability can be read from real stored history instead of deterministic fixture labels. Persisted history remains research-only and can only reduce confidence.

## Requirements

1. Add a persistent `indicator_signal_history` store with symbol, indicator, timeframe, signal time, decision time, session, regime, snapshot, manifest, registry, label, and safety fields.
2. Store pending labels for audit, but exclude them from reliability counts.
3. Make `IndicatorReliabilityReport` prefer persisted completed labels when available.
4. Keep deterministic fixture fallback only when no persisted counted labels exist.
5. Add a trader-facing frontend reliability drilldown card.
6. Preserve research-only safety: `used_for_probability=false`, `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`, and `no_future_leakage=true`.

## Acceptance Criteria

1. `POST /api/v1/behavior/indicators/reliability/save-history` persists a signal history record.
2. `GET /api/v1/behavior/indicators/{indicator_id}/signal-history/{symbol}` reads stored signal history.
3. `GET /api/v1/behavior/indicators/{indicator_id}/reliability-drilldown/{symbol}` returns reliability plus history plus trader summary.
4. Persisted completed labels override fixture fallback in reliability reports.
5. Pending labels are visible but not counted.
6. Tests `test_v183_*` pass.
7. Frontend typecheck/build passes before v1.83 is marked UI-verified.

## Scope: v1.84 Current Closed-Candle Indicator Signal History Ingestion

Requirement:

- Provide a safe bridge from current closed-candle 9C indicator evidence into the persistent indicator signal history table.
- The bridge must never label a future outcome at decision time.
- The bridge must be explicit user action, not an automatic hidden write on page load.

Contract additions:

- `IndicatorSignalHistoryIngestCurrentRequest`
- `IndicatorSignalHistoryIngestCurrentReport`

Endpoint:

```text
POST /api/v1/behavior/indicators/reliability/ingest-current
```

Acceptance criteria:

1. Current ingestion reads a closed-candle evidence packet.
2. Current ingestion saves only pending labels.
3. Pending rows are not counted in reliability.
4. Repeating ingestion for the same symbol/timeframe/snapshot/horizon is idempotent.
5. The Jarvis reliability card exposes a manual `Ingest Current Signals` action.
6. The feature remains research-only: no probability authority, no order routing, no live trading.

## Scope: v1.85 Pending Indicator History Outcome Completion

Requirement:

- Convert pending indicator history rows into completed outcome labels only after future-bar evidence is explicitly supplied.
- Preserve the same history id for the same indicator, stock, timeframe, signal time, and horizon.
- Do not complete rows when the supplied future bars do not cover the stored horizon.
- Use the existing conservative intrabar ambiguity rule.

Contract additions:

- `IndicatorSignalHistoryCompletePendingRequest`
- `IndicatorSignalHistoryCompletePendingReport`

Endpoint:

```text
POST /api/v1/behavior/indicators/reliability/complete-pending
```

Acceptance criteria:

1. Completed future horizons update pending rows to complete labels.
2. Incomplete future horizons remain pending and uncounted.
3. Same-bar target/stop collisions are labeled conservatively as stop-first.
4. Completed rows may feed research reliability but cannot approve trades.
5. The feature remains research-only: no probability authority, no order routing, no live trading.

## Scope: Context Files Fable Layer (docs/context.md + docs/graph.md)

In addition to the v1.62 context set, maintain human Fable docs:

1. `docs/context.md` — domain invariants, policies, known unknowns, measured bounds.
2. `docs/graph.md` — Mermaid/authority maps twin of `docs/graph/project_graph.json`.
3. Prefer these with `ARCHITECTURE.md` for new-agent onboarding (see `docs/FILE_DOCUMENT_INDEX.md §0.6`).

## Scope: v1.86 Signed TrendForge Research Intake

Trade Vision must accept scanner evidence from TrendForge only as **signed, research-only** intake. Packets must not enable broker orders, order routing, or OpenAlgo live handoff.

## Requirements

1. Validate HMAC signature with a dedicated secret distinct from the OpenAlgo adapter secret.
2. Require safety envelope fields proving research-only posture (`researchOnly`, `tradeAllowed=false`, `orderRoutingEnabled=false`, `brokerOrderCreated=false`, `liveTradingBlocked=true`).
3. Default source host policy is **loopback-only** (`127.0.0.1`, `localhost`, `::1`); remote URLs rejected unless a future host-policy ADR allows them.
4. Persist immutable intakes with packet/content/payload hashes (`trendforge_intakes`).
5. Expose operator/API surfaces:
   - `POST /api/v1/integrations/trendforge/pull-latest`
   - `GET /api/v1/integrations/trendforge/intakes`
6. Stale or non-promotable evidence remains WAIT / research storage — no forced OpenAlgo handoff.
7. Preserve global safety: no live trading, no broker credentials, no hidden routing.

## Scope: v1.88-v1.93 ORB Paper Guidance

Trade Vision shall make ORB the primary paper-research setup candidate without
making ORB, Jarvis, or the simulated ledger an execution authority.

Requirements:

1. Build ORB only from fully closed candles aligned to the NSE 09:15 session.
2. Use the same immutable snapshot for ORB, MTF, memory, risk, and arbiter
   evidence.
3. Require a proof-backed server-side promoted playbook before an ORB entry
   ticket may become eligible.
4. Require at least 30 historical evidence records and complete required MTF
   evidence before `ENTER_PAPER` is possible.
5. Keep D6 as the sole final-band producer.
6. Show ORH/ORL, setup side, entry trigger, stop, target, invalidation, MTF,
   proof, liquidity, and blockers in Jarvis.
7. Record a simulated paper item only after literal human approval and exact
   snapshot binding.
8. Treat the record as a local research ledger entry, not a fill or broker
   order.
9. Reject client-supplied entry/stop/target changes.
10. Keep `broker_order_created=false`, `order_routing_enabled=false`, and
    `live_trading_blocked=true` on every route and stored record.

Observed offline RELIANCE acceptance result:

```text
WATCH / NO_PLAYBOOK / MTF ALIGNED / evidence 0 of 30 / record disabled
```

## Scope: v1.94 ORB Paper Lifecycle Feedback

Trade Vision shall turn an eligible, human-approved simulated ORB paper intent
into an explicit replay observation without creating an automatic fill, broker
order, or live route.

Requirements:

1. Require an existing server-stored paper record and its exact guidance,
   playbook proof, snapshot, symbol, and timeframe identity.
2. Accept only unique, monotonic, consecutive, fully closed post-decision bars.
3. Compute deterministic simulated fill, MFE, MAE, costs, net R, and one of
   `PENDING`, `NO_FILL`, `TARGET_HIT`, `STOP_HIT`, or `TIME_EXIT`.
4. Resolve target/stop collisions in one OHLC bar conservatively as
   `STOP_HIT` unless lower-timeframe ordering evidence exists.
5. Freeze a completed outcome and preserve a deterministic integrity hash.
6. Build ORB reliability only from completed, non-orphaned, identity-valid,
   hash-valid outcomes.
7. Keep low evidence below 30 completed outcomes at `LOW_EVIDENCE`.
8. Permit feedback only to reduce/quarantine trust; it cannot promote a
   playbook, change weights, or approve a trade.
9. Persist tickets, records, and outcomes through lock-protected atomic JSON
   replacement and expose a read-only storage monitor.
10. Make retention report-only and configurable through environment-backed
    paths and thresholds.
11. Show explicit replay horizon controls, lifecycle result, reliability, and
    store integrity in the Jarvis ORB panel.
12. Preserve `trade_allowed=false`, `order_routing_enabled=false`,
    `broker_order_created=false`, and `live_trading_blocked=true`.

Observed downloaded RELIANCE acceptance result remains correctly fail-closed:

```text
WATCH / NO_PLAYBOOK / MTF ALIGNED / evidence 0 of 30
record disabled / lifecycle evaluation disabled
```

## Acceptance Criteria

1. `apps/api/tests/test_trendforge_bridge.py` passes (6 tests).
2. Tampered or unsigned packets are rejected.
3. Remote non-loopback pull is blocked by default.
4. Safety envelope violations are rejected.
5. Idempotent storage does not duplicate the same packet identity incorrectly.
6. `docs/IMPLEMENTATION_STATUS.md`, `docs/graph/project_graph.json`, `ARCHITECTURE.md`, `docs/context.md`, and `docs/graph.md` list v1.86 as latest completed functional version after context maintenance.
7. No route sets `order_routing_enabled=true` or creates broker orders from TrendForge candidates.
