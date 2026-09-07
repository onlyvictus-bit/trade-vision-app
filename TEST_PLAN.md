# Trade Vision TEST_PLAN

## Current Release Verification: v2.02-derivatives

Verified 2026-09-07:

```text
python -m pytest apps/api/tests -q
-> 914 passed / 0 failed (chunked: 358 + 556)

focused v2.02 derivatives bundle: 22 passed
focused v2.01 opening scenarios: 8 passed
focused v1.96 catalog: 9 passed | v1.97 timing: 10 passed
focused v1.89-v1.94 ORB suites: 36 passed | spine+orb paper: 74 passed

npm.cmd run typecheck
npm.cmd run build
-> passed (v1.97; no frontend change since)
```

Tip authority: `docs/IMPLEMENTATION_STATUS.md`. v1.94 section below is frozen
history (715 passed 2026-07-24).

Observed browser result:

```text
RELIANCE 5m
WATCH / NO_PLAYBOOK
MTF ALIGNED
evidence 0/30
record and lifecycle controls disabled
storage integrity PASS
```

The next proposed operational test family is `TV-V195-*`: it must prove that
the 30-second timer loads only global safety state and visible workspace/subtab
evidence, while explicit refresh can reload the active surface without dropping
previously loaded inactive data.

## v1.87 Paper Guidance Spine P0 Tests

Run:

```text
python -m pytest apps/api/tests/test_paper_guidance_spine.py -q
python -m pytest apps/api/tests/test_api.py -q -k "v066 or v067"
python -m pytest apps/api/tests -q
```

Required cases:

1. Identical input produces byte-equivalent guidance data, guidance id, and
   snapshot hash.
2. A closed-bar value change changes the hash.
3. D1 failure stops before D2 and leaves `snapshot_hash=null`.
4. Invalid OHLC and triggered kill switch fail closed.
5. Low evidence cannot produce `ENTER_PAPER`.
6. High evidence is still capped at `WATCH` in P0.
7. Close-time semantics pass independently for 1m, 3m, 5m, 15m, 30m, 1H,
   4H, and Daily.
8. Typed safety literals reject execution-flag overrides.
9. API response is a research-only envelope.
10. OpenAPI and capability manifest publish the P0 contract.
11. The Paper Guidance module imports no broker/OpenAlgo/execution module.
12. The sibling Kronos/Twin shared snapshot excludes an incomplete candle.

Verified 2026-07-23:

```text
focused Paper Guidance: 20 passed
existing Kronos/Twin snapshot subset: 9 passed, 547 deselected
full backend: 598 passed in 325.15s
```

## v0.72 Real Closed-Candle MTF Pullback Tests

Run:

```text
python -m pytest apps/api/tests/test_api.py -q -k "mtf or timeframe or 9c_pit_level_memory"
npm run build
```

## Required Cases

1. `test_mtf_001_real_aggregation_uses_ohlcv_rules`
   - Input: synthetic monotonic 1m bars.
   - Expected: 3m/5m/15m aggregate count and OHLCV values follow open-first, high-max, low-min, close-last, volume-sum.

2. `test_mtf_002_incomplete_aggregate_is_not_decision_safe`
   - Input: source rows that do not complete a 15m aggregate.
   - Expected: incomplete bars are blocked from decision logic.

3. `test_mtf_003_direction_comes_from_closed_bar_slope_not_seed`
   - Input: same seed, opposite source data slope.
   - Expected: direction follows source data slope, not seed.

4. `test_mtf_004_lower_timeframe_pullback_inside_higher_uptrend_is_watch_not_block`
   - Input: 15m uptrend with 3m short pullback.
   - Expected: conflict explanation is `lower_timeframe_pullback_inside_higher_timeframe_trend` with `WAIT`.

5. `test_mtf_005_higher_timeframe_opposition_blocks_confidence`
   - Input: primary long, higher timeframe short.
   - Expected: block severity and `blocks_trade=true`.

6. `test_mtf_006_research_safety_never_changes`
   - Expected: `trade_allowed=false`, `order_routing_enabled=false`, `live_trading_blocked=true`.

7. `test_mtf_007_output_is_deterministic`
   - Input: same request twice.
   - Expected: same state matrix and explanations.

8. Regression:
   - Existing ICACHE tests still pass.
   - Existing 9C safety tests still pass.
   - Frontend typecheck/build passes.

## v0.73 Volatility-OOD Before Analogs Tests

1. `test_9c_vol_001_current_atr_above_historical_p90_sets_volatility_ood`
   - Input: low-volatility historical windows and high-volatility current descriptor.
   - Expected: `volatility_ood=true`, bucket `extreme`.

2. `test_9c_vol_002_ood_status_exposes_shape_and_volatility_gates`
   - Input: normal RELIANCE 1m report.
   - Expected: output includes `shape_ood`, `volatility_ood`, `volatility_gate`, and research safety fields.

3. `test_9c_vol_003_decision_gate_9c_g016_uses_volatility_before_analogs`
   - Input: monkeypatched OOD report with volatility wait.
   - Expected: hybrid decision stays `WAIT`.

4. `test_9c_vol_004_path_analogs_preserve_real_counts_not_hardcoded`
   - Input: normal RELIANCE 1m path analog endpoint.
   - Expected: `hardcoded_match_count_used=false`; volatility fields are present.

5. Regression:
   - Existing 9C tests remain green.
   - Frontend build remains green.

## v0.74 Reasoning Arbiter, Audit, and Drift Tests

1. `test_9c_arbiter_001_manipulated_flag_overrides_to_wait`
   - Input: strong winner analog evidence plus `manipulated_looking`.
   - Expected: arbiter override is active, continuation boost is zero, and routing remains blocked.

2. `test_9c_disagree_001_hard_conflict_forces_confidence_penalty`
   - Input: subsystem votes `LONG`, `SHORT`, and `WAIT`.
   - Expected: hard conflict, confidence penalty `1.0`, action `force_wait`.

3. `test_9c_audit_001_decision_audit_hash_is_deterministic`
   - Input: identical arbiter and gate payloads twice.
   - Expected: identical audit hash and safety fields remain false/blocked.

4. `test_9c_drift_001_active_drift_demotes_calibrator_to_rule_only`
   - Input: realized error rate far above predicted error rate.
   - Expected: gate `9C-G018=wait` and action `demote_to_rule_only`.

5. `test_9c_decision_includes_arbiter_audit_and_drift_gates`
   - Input: normal RELIANCE 1m decision panel.
   - Expected: gates `9C-G018` and `9C-G019` exist, decision remains `WAIT` or `WATCH`, and final reason includes arbiter/audit evidence.

6. Regression:
   - Existing v0.72 MTF tests remain green.
   - Existing v0.73 volatility-OOD tests remain green.
   - Existing ICACHE tests remain green.
   - Frontend typecheck/build passes.

## v0.75B Indicator Cache Integrity and Quarantine Tests

1. `test_icache_013_anomalous_snapshot_is_quarantined_and_not_persisted`
   - Input: save request with `anomalous_snapshot=true`.
   - Expected: `cache_status=anomalous_snapshot_quarantined`, `saved_count=0`, reference-only, trading blocked.

2. `test_icache_014_artifacts_are_reference_only_and_never_probability_authority`
   - Input: normal save and results read.
   - Expected: artifact safety block includes reference-only and all trading/probability flags false/blocked.

3. `test_icache_015_sha_mismatch_is_failed_and_not_reused`
   - Input: save cache, corrupt artifact JSON, read status/results.
   - Expected: failed integrity is reported and artifact is not loaded as usable evidence.

4. `test_icache_016_feature_manifest_mismatch_is_stale_and_not_reused`
   - Input: saved row copied with mismatched feature manifest version.
   - Expected: stale version status and reuse path ignores the stale row.

5. `test_icache_017_disk_write_failure_degrades_without_crashing`
   - Input: artifact writer raises an `OSError`.
   - Expected: failed rows are returned, API logic does not crash, and trading remains blocked.

6. `test_icache_018_same_identity_artifact_is_reproducible`
   - Input: same symbol/timeframe/snapshot/manifest saved twice.
   - Expected: cache IDs and artifact hashes remain identical.

7. `test_icache_019_wrong_volatility_context_is_stale`
   - Input: valid artifact SHA with stale stored volatility bucket.
   - Expected: integrity status `stale_volatility_bucket`.

8. `test_icache_020_force_recompute_anomalous_snapshot_remains_quarantined`
   - Input: prior clean cache exists, then force-recompute with anomalous snapshot.
   - Expected: no new rows are saved or reused; quarantine status wins.

9. Continuity guard:
   - `test_icache_005_cache_id_matches_exact_identity_formula`
     - Expected: `cache_id` equals SHA-256 of the exact symbol, timeframe, source hash, indicator id, registry version, feature manifest version, and promoted-indicator hash.
   - `test_icache_006_artifact_payload_identity_context_telemetry_and_safety_are_present`
     - Expected: verified artifact carries identity, context, telemetry, and research-only safety sections.
   - `test_icache_007_force_recompute_refreshes_same_deterministic_cache_identity`
     - Expected: force recompute refreshes existing deterministic rows and does not create duplicate authority.
   - `test_icache_008_missing_artifact_is_failed_and_not_reused`
     - Expected: missing artifact is marked failed and cannot be reused.
   - `test_icache_009_api_paths_share_live_blocked_safety_envelope`
     - Expected: save, status, results, and delete paths all preserve no-probability and live-blocked fields.
   - `test_icache_010_limit_parameter_is_bounded`
     - Expected: oversized result limits are bounded by storage protection.
   - `test_icache_011_stale_registry_version_is_not_verified`
     - Expected: stale registry version fails verification and is not reused.
   - `test_icache_012_cache_save_keeps_mock_default_reference_only`
     - Expected: default cache save is reference-only, mock-safe, and cannot enable trading.

10. Regression:
   - ICACHE-001 through ICACHE-020 remain green with no numeric gaps.
   - Relevant 9C safety gates remain green.

## TV-PROD-RED-001 Final Red-Team Test

1. `test_tv_prod_red_001_manipulated_wick_final_gate_blocks_confidence_and_quarantines_cache`
   - Input: deterministic manipulated-wick fixture with `2.4x ATR` shock.
   - Expected:
     - `volatility_ood=true`
     - `manipulated_looking` in arbiter consulted flags
     - `matched_after_vol_bucketing < raw_match_count`
     - `continuation_boost <= 0.0`
     - decision in `{WAIT, WATCH}`
     - `paper_candidate_allowed=false`
     - `cache_status=anomalous_snapshot_quarantined`
     - `live_trading_blocked=true`

2. Regression:
   - Relevant 9C/MTF/cache tests remain green.
   - Frontend build remains green.
   - Jarvis frontend loads `/api/v1/behavior/red-team/tv-prod-red-001` through the typed client and renders the report without enabling any trade route.
   - Browser snapshot confirms the panel exists and pending fallbacks are fail-closed (`blocked`/`pending`), not misleading `unsafe` labels caused by absent data.

## Jarvis Evidence Loader Concurrency Test

1. Frontend production build:
   - Command: `npm.cmd run build`
   - Expected: TypeScript and Vite build pass.
2. Static UI contract verification:
   - Command: `npm.cmd run verify:jarvis-redteam`
   - Expected: Jarvis red-team endpoint, priority fetch, no-overlap refresh guard, bounded loader, fail-closed pending labels, and safety metric labels are present.
3. Browser verification:
   - Open `http://127.0.0.1:5173/?v=verify-redteam#jarvis`.
   - Expected: Jarvis renders without bulk `ERR_INSUFFICIENT_RESOURCES`.
   - Expected: `TV-PROD-RED-001 Manipulated-Wick Safety Proof` is present and fail-closed while loading.
   - Expected: If one evidence endpoint fails, the UI shows a partial-evidence warning and unaffected panels still hydrate.
   - Expected: TV-PROD-RED-001 hydrates before slower non-critical evidence panels and scheduled refreshes do not overlap.

## SQLite State Startup And Lock Test

1. Storage startup regression:
   - Command: `.venv\Scripts\python.exe -m pytest trade-vision-app\apps\api\tests\test_storage_startup.py -q`
   - Expected: a fresh configured DB path initializes schema, reports `status=ready`, and records the configured path.
2. Connection policy regression:
   - Expected: every SQLite connection applies `PRAGMA busy_timeout` with the project timeout.
3. Safety regression:
   - Expected: storage reliability changes do not create live-order routes and do not alter the TV-PROD-RED-001 `WAIT`/blocked behavior.

## Transport Trace Integrity Window Test

1. `test_v057_trace_integrity_window_fetches_omitted_predecessor_before_mismatch`
   - Input: a delivery with multiple traces, verified through a bounded window that starts after the root trace.
   - Expected: global/windowed verification succeeds when the omitted predecessor hash matches.
2. Existing tamper regression:
   - `test_v057_trace_integrity_detects_tampering_and_recovers_after_restore`
   - Expected: modified trace JSON fails integrity, restored trace passes.
3. Full release/security regression:
   - Command: `.venv\Scripts\python.exe -m pytest trade-vision-app\apps\api\tests -q`
   - Expected: security posture, deployment readiness, final audit, and release export pass with the default local DB while remaining brokerless and live-blocked.

## Pytest Cache Hygiene Test

1. Cache cleanup verification:
   - Command: remove only `trade-vision-app/.pytest_cache` if it is malformed or inaccessible and the filesystem permits removal.
   - Expected: no source, test, data, artifact, or DB path is removed.
2. Focused pytest recreation:
   - Command: `.venv\Scripts\python.exe -m pytest trade-vision-app\apps\api\tests\test_storage_startup.py -q`
   - Expected: tests pass and pytest writes to the configured generated cache directory without `PytestCacheWarning`.
3. Full regression:
   - Command: `.venv\Scripts\python.exe -m pytest trade-vision-app\apps\api\tests -q`
   - Expected: full backend regression remains green and warning-free except third-party library warnings that are unrelated to cache writes.

## Research Stack Local Verification Tool Tests

1. Unit tests:
   - Command: `.venv\Scripts\python.exe -m pytest trade-vision-app\apps\api\tests\test_research_stack_verifier.py -q`
   - Expected: verifier success, missing secret, unsafe payload, and endpoint failure paths are covered without live network services.
2. Fail-closed unavailable-stack smoke:
   - Command: `.venv\Scripts\python.exe trade-vision-app\scripts\verify_research_stack.py --api-base http://127.0.0.1:9 --adapter-url http://127.0.0.1:9`
   - Expected: JSON report has `passed=false` and exits non-zero.
3. Safety invariant:
   - Expected: verifier never sends broker credentials, never creates orders, and fails any payload where `order_routing_enabled=true` or `live_trading_blocked=false`.

## One-Command Local Research Stack Verification Wrapper Tests

1. Static wrapper contract:
   - Command: `.venv\Scripts\python.exe -m pytest trade-vision-app\apps\api\tests\test_research_stack_verifier.py -q`
   - Expected: the wrapper references `start-research-stack.ps1`, `verify_research_stack.py`, `stop-research-stack.ps1`, uses `finally`, and contains no broker/order execution calls.
2. PowerShell parser validation:
   - Command: parse `scripts/verify-local-research-stack.ps1` with `System.Management.Automation.Language.Parser`.
   - Expected: zero parser errors.
3. Existing safety regression:
   - Expected: backend regression, Jarvis verifier, and frontend build remain green.

## Idempotent Storage Initialization Runtime Guard Tests

1. Same-target idempotency:
   - Configure a fresh file database.
   - Patch `_backfill_audit_hashes` to count calls.
   - Call `storage.init_db()` twice.
   - Expected: schema exists, database is ready, and audit backfill runs once.
2. Target switch initialization:
   - Configure `DB_PATH` to one fresh file, initialize it, then configure `DB_PATH` to a second fresh file.
   - Expected: both databases are initialized independently and report ready status.
3. Disappearing file recovery:
   - Initialize a file database, remove only that generated database file, and call `storage.init_db()` again.
   - Expected: the file is recreated and schema is present.
4. Audit integrity preservation:
   - Existing audit integrity tests still validate the hash chain.
   - Explicit audit integrity verification still invokes backfill before checking the chain.
5. Trading safety preservation:
   - No storage initialization path can set `trade_allowed=true`, `order_routing_enabled=true`, or `live_trading_blocked=false`.
   - External-AI/Jarvis audit reports remain display-only.

## Bounded Deployment Database Integrity Cache Tests

1. Same-fingerprint reuse:
   - Create a fresh SQLite database.
   - Patch `sqlite3.connect` in the deployment readiness module to count opens.
   - Call `_database_integrity(path)` twice without modifying the DB.
   - Expected: both calls return the same result and SQLite is opened once.
2. Fingerprint invalidation:
   - Create a fresh SQLite database and run `_database_integrity(path)`.
   - Write a new table or row to the same database.
   - Run `_database_integrity(path)` again.
   - Expected: SQLite is opened again and the new table count is reflected.
3. Failure behavior:
   - Point `_database_integrity(path)` at an invalid database file.
   - Expected: returns `(False, 0)` and does not raise.
4. Release safety:
   - Final release audit, deployment readiness, and Jarvis review packet tests remain brokerless and live-blocked.

## Review-Only Preflight Fast Path Tests

1. Correction packet does not run final audit:
   - Patch `build_final_release_audit` in the API module to raise if called.
   - Request `/api/v1/jarvis/correction-review-packet/{symbol}`.
   - Expected: response succeeds and final audit is not called.
2. Correction packet remains display-only:
   - Expected: `ready_for_correction_review=true` can be returned, but `ready_for_decision_trust=false`, `ready_for_openalgo=false`, `trade_allowed=false`, `order_routing_enabled=false`, and `live_trading_blocked=true`.
3. Full audit endpoints unchanged:
   - Existing final release audit and deployment readiness tests remain green.

## Timezone-Safe VWAP Band Grouping Tests

1. Weekly timezone-aware VWAP:
   - Build an IST timezone-aware 1-minute OHLCV DataFrame.
   - Call vendor `_vwap_bands(work, "W")` under `warnings.catch_warnings`.
   - Expected: no warning containing `drop timezone information`.
2. Output alignment:
   - Expected: returned frame index equals the input index and length.
3. Existing indicator safety:
   - Existing FMFM300 explanation-only test remains green.
   - Existing indicator-cache tests remain green.

## Frontend Production Bundle Split Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: contracts and web app compile with no TypeScript errors.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite build succeeds.
3. Chunk warning regression:
   - Inspect build output.
   - Expected: separate `react-vendor` and `validation-vendor` chunks are emitted.
   - Expected: no Vite warning that chunks are larger than 500 kB.
4. Behavior preservation:
   - No API client, route, workspace, chart, or safety-gate source file is changed by this milestone.

## Shared Frontend UI Primitive Extraction Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: extracted primitive exports are typed and imported correctly.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite production build succeeds.
3. Backend regression:
   - Run the full backend API test suite.
   - Expected: backend behavior remains unchanged.
4. Source ownership:
   - Search source for `function Panel`, `function Card`, `function Metric`, `function Status`, `function pct`, and `function money`.
   - Expected: definitions exist in `src/components/primitives.tsx`; `App.tsx` imports them.

## Reference Workspace Component Extraction Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: extracted `Knowledge` and `Implementation` components import and compile correctly.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite production build succeeds and existing chunk split remains valid.
3. Backend regression:
   - Run the full backend API test suite.
   - Expected: backend behavior remains unchanged.
4. Source ownership:
   - Search source for `function Knowledge` and `function Implementation`.
   - Expected: definitions exist in `src/components/workspaces/referenceWorkspaces.tsx`; `App.tsx` imports them.
5. Safety preservation:
   - Confirm extracted components contain no direct `api.` calls and no order-routing, credential, broker, OpenAlgo, Gemini, Grok, or kill-switch calls.

## Safety Display Panel Extraction Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: extracted `RiskPanel`, `OrderPathPanel`, and `IntegrityPanel` compile correctly.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite production build succeeds and existing chunk split remains valid.
3. Backend regression:
   - Run the full backend API test suite.
   - Expected: backend behavior remains unchanged.
4. Source ownership:
   - Search source for `function RiskPanel`, `function OrderPathPanel`, and `function IntegrityPanel`.
   - Expected: definitions exist in `src/components/safetyPanels.tsx`; `App.tsx` imports them.
5. Safety preservation:
   - Search `src/components/safetyPanels.tsx`.
   - Expected: no direct `api.`, `fetch`, broker-control, OpenAlgo, Gemini, Grok, credential-handling, or kill-switch control calls.
   - Expected: safety display labels such as `Broker Credentials` are allowed because they render already-loaded backend evidence.
   - Expected: the module may display `kill_switch_state` from loaded data only.

## AI Credential Vault Panel Extraction Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: extracted `AiCredentialsPanel` compiles correctly.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite production build succeeds and existing chunk split remains valid.
3. Backend regression:
   - Run the full backend API test suite.
   - Expected: backend behavior remains unchanged.
4. Source ownership:
   - Search source for `function AiCredentialsPanel`.
   - Expected: definition exists in `src/components/aiCredentialsPanel.tsx`; `App.tsx` imports it.
5. Credential API boundary:
   - Search `src/components/aiCredentialsPanel.tsx`.
   - Expected: allowed API calls are limited to `saveGeminiCredential`, `testGeminiCredential`, `clearGeminiCredential`, `saveGrokCredential`, `testGrokCredential`, and `clearGrokCredential`.
   - Expected: no raw `fetch`, browser-login implementation, username/password form, cookie/session capture, OpenAlgo, broker, order-routing, live-review, or kill-switch action calls.
   - Expected: read-only display of backend `browser_password_login_supported` status is allowed.
6. Secret-input safety:
   - Search `src/components/aiCredentialsPanel.tsx`.
   - Expected: Gemini and Grok secret inputs remain `type="password"` and `autoComplete="off"`.

## System Workspace Extraction Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: extracted `System` workspace compiles correctly.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite production build succeeds and existing chunk split remains valid.
3. Backend regression:
   - Run the full backend API test suite.
   - Expected: backend behavior remains unchanged.
4. Source ownership:
   - Search source for `function System`.
   - Expected: definition exists in `src/components/workspaces/systemWorkspace.tsx`; `App.tsx` imports it.
5. Data ownership:
   - Search `src/components/workspaces/systemWorkspace.tsx`.
   - Expected: no direct `api.`, `fetch`, external-AI review, OpenAlgo, broker/order, live-trading, or kill-switch action calls.
   - Expected: the workspace may render `AiCredentialsPanel` using already-loaded masked status.

## Replay Evidence Panel Extraction Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: extracted replay evidence component compiles correctly.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite production build succeeds and existing chunk split remains valid.
3. Backend regression:
   - Run the full backend API test suite.
   - Expected: backend behavior remains unchanged.
4. Source ownership:
   - Search source for `ReplayEvidencePanels`.
   - Expected: definition exists in `src/components/workspaces/replayEvidencePanels.tsx`; `App.tsx` imports it.
5. Replay control ownership:
   - Search `src/components/workspaces/replayEvidencePanels.tsx`.
   - Expected: no direct `api.`, `fetch`, `startReplay`, `playReplay`, `pauseReplay`, `stepReplay`, `seekReplay`, OpenAlgo, broker/order, live-trading, external-AI review, or kill-switch action calls.
   - Expected: replay seed/session state and replay control handlers remain in `App.tsx`.

## Replay Evidence Simple-English Clarification Tests

1. TypeScript contract safety:
   - Run `npm run typecheck`.
   - Expected: the updated replay evidence component compiles correctly.
2. Production build:
   - Run `npm run build`.
   - Expected: Vite production build succeeds.
3. Plain-English evidence labels:
   - Search `src/components/workspaces/replayEvidencePanels.tsx`.
   - Expected: the module explains that replay archive sessions are repeatable test sessions, execution simulation is not a real order, point-in-time snapshots are exact data packets, and the chart replay workbench remains separate.
4. Display-only boundary:
   - Search `src/components/workspaces/replayEvidencePanels.tsx`.
   - Expected: no direct `api.`, `fetch`, replay control, broker/order, OpenAlgo, external-AI review, live-trading, or kill-switch action calls.

## v1.62 Context Maintenance And Graph Refresh Tests

1. Graph JSON validity:
   - Parse `docs/graph/project_graph.json`.
   - Expected: valid JSON.
2. Graph count consistency:
   - Compare `summary.nodes` with `len(nodes)`.
   - Compare `summary.edges` with `len(edges)`.
   - Expected: counts match.
3. Graph reference integrity:
   - Collect all node IDs.
   - Check every edge `from` and `to`.
   - Expected: no missing references.
4. Handoff file presence:
   - Confirm these files exist:
     - `docs/context.md`
     - `docs/graph.md`
     - `TRADE_VISION_README.md § AI / New-Chat Handoff`
     - `docs/FILE_DOCUMENT_INDEX.md §0.6`
     - `docs/IMPLEMENTATION_STATUS.md`
     - `docs/NEXT_BUILD_TARGET.md`
     - `docs/SAFETY_INVARIANTS.md`
     - `docs/FILE_DOCUMENT_INDEX.md §7.4`
     - `docs/FRONTEND_PANEL_MAP.md`
     - `docs/API_ENDPOINT_INDEX.md`
     - `docs/TEST_ID_INDEX.md`
     - `TRADE_VISION_README.md § AI Handoff → Fast continuation + context maintenance`
     - `docs/graph/project_graph.json`
5. Current version pointer:
   - Read `docs/IMPLEMENTATION_STATUS.md`.
   - Expected: latest completed version is listed and does not conflict with `docs/IMPLEMENTATION_STATUS.md`.
6. Safety invariant preservation:
   - Read `docs/SAFETY_INVARIANTS.md`.
   - Expected: live routing, broker credential creation, hidden session capture, and external-AI override authority remain blocked.
7. README freshness:
   - Read `TRADE_VISION_README.md`.
   - Expected: current milestone is not stale `v0.31`.
8. Easy explanation freshness:
   - Read `docs/MILESTONE_EASY_EXPLANATION.md`.
   - Expected: current explanation references the modern safety/research state and does not claim old `18 passed` verification as current.

## v1.75 Final Confluence Conflict Arbiter Tests

Run:

```text
python -m pytest apps/api/tests/test_api.py -q -k "v175 or enveloped"
python -m pytest apps/api/tests/test_api.py
```

Required cases:

1. `test_v175_arb_001_bullish_indicators_at_daily_resistance_are_downgraded`
   - Expected: resistance conflict exists and final decision is not blindly promoted.
2. `test_v175_arb_002_strong_breakout_with_weak_sector_reduces_confidence`
   - Expected: weak-sector conflict exists.
3. `test_v175_arb_003_high_trap_score_overrides_analog_strength`
   - Expected: final decision is `AVOID`.
4. `test_v175_arb_004_event_risk_downgrades_paper_to_watch`
   - Expected: otherwise strong evidence is capped to `WATCH`.
5. `test_v175_arb_005_liquidity_c_blocks_paper_candidate`
   - Expected: liquidity grade C blocks candidate promotion.
6. `test_v175_arb_006_post_entry_thesis_break_overrides_original_long_plan`
   - Expected: post-entry invalidation dominates the original thesis.
7. `test_v175_arb_007_every_final_decision_has_reason_tree_and_safety_flags`
   - Expected: reason tree exists and all routing flags remain blocked.
8. `test_v175_arb_008_evidence_scores_sum_deterministically_and_manifest_is_present`
   - Expected: identical input returns identical score and decision; capability manifest includes v1.75.

Current verification:

```text
Focused v1.75/envelope subset: 9 passed, 501 deselected
Full backend regression: 510 passed, 1 warning
```

## v1.80 Indicator Intelligence Contract + Ontology Tests

Run:

```text
python -m pytest apps/api/tests/test_api.py -q -k "v180 or v060 or enveloped"
python -m pytest apps/api/tests/test_api.py
```

Required cases:

1. `test_v180_ind_ont_001_every_registry_indicator_carries_ontology_metadata`
   - Expected: all 94 registry entries carry ontology metadata and safe defaults.
2. `test_v180_ind_ont_002_rsi_is_exhaustion_not_breakout_strength`
   - Expected: RSI is classified as exhaustion context, not breakout strength.
3. `test_v180_ind_ont_003_category_and_family_can_differ_without_breaking_redundancy`
   - Expected: category-aware redundancy keeps RSI exhaustion distinct from generic momentum family.
4. `test_v180_ind_ont_004_list_defaults_are_not_shared_mutable_defaults`
   - Expected: list fields use isolated defaults and cannot leak mutations.
5. `test_v180_ind_ont_005_registry_count_and_growth_gate_remain_green`
   - Expected: 94-entry registry lock remains green.
6. `test_v180_ind_ont_006_unclassified_indicator_is_safe_explanation_only`
   - Expected: unclassified indicators cannot affect probability.
7. `test_v180_ind_arb_009_confirmation_delay_reduces_late_indicator_vote_weight`
   - Expected: four-bar MACD confirmation receives `lag_weight=0.2`.
8. `test_v180_ind_arb_010_zero_delay_structural_signal_outranks_four_bar_macd`
   - Expected: zero-delay structural evidence has stronger adjusted vote than delayed MACD.
9. `test_v180_ind_arb_011_late_confirmation_cannot_promote_watch_to_paper_alone`
   - Expected: late confirmation cannot produce `PAPER-CANDIDATE`.
10. `test_v180_ind_arb_012_stale_confirmation_creates_warning_not_confidence`
   - Expected: stale confirmation creates warning and no promotion.

Current verification:

```text
Focused v1.80/v0.60/envelope subset: 12 passed, 508 deselected
Full backend regression: 520 passed, 1 warning
```

## v1.81 Per-Indicator Reliability Memory Tests

Run:

```text
python -m pytest apps/api/tests/test_api.py -q -k "v181 or v180 or v060 or enveloped"
python -m pytest apps/api/tests/test_api.py
```

Required cases:

1. `test_v181_ind_rel_001_signal_label_waits_until_future_horizon_completes`
   - Expected: incomplete future horizon remains pending and is not counted as a win.
2. `test_v181_ind_rel_002_same_bar_target_stop_collision_uses_conservative_stop_first`
   - Expected: same-bar target/stop collision labels as `SL_HIT` without lower-timeframe proof.
3. `test_v181_ind_rel_003_low_sample_bayesian_shrinkage_blocks_probability`
   - Expected: low sample count sets `low_evidence`, neutral multiplier, and no probability authority.
4. `test_v181_ind_rel_004_per_stock_reliability_differs_by_symbol`
   - Expected: symbol-specific reliability can differ.
5. `test_v181_ind_rel_005_reliability_feeds_lag_vote_multiplier_research_only`
   - Expected: reliability reduces lag-vote preview and keeps trading blocked.
6. `test_v181_ind_rel_006_quarantine_on_ood_or_regime_shift_blocks_reliability`
   - Expected: OOD/regime shift quarantines reliability.
7. `test_v181_ind_rel_007_reciprocal_warning_surfaces_reliably_wrong_indicator`
   - Expected: high reciprocal ratio produces warning and failed gate.
8. `test_v181_ind_rel_008_intelligence_summary_includes_reliability_preview`
   - Expected: existing intelligence summary includes safe reliability preview.

Current verification:

```text
Focused v1.81/v1.80/v0.60/envelope subset: 20 passed, 508 deselected
Full backend regression: 528 passed, 1 warning
```

## v1.82 Full Timeframe Contract + Reliability Drilldown Tests

Run:

```text
python -m pytest apps/api/tests/test_api.py -q -k "v182 or v181 or v180 or v061 or v062 or v072 or v078 or v060"
python -m pytest apps/api/tests/test_api.py
```

Required cases:

1. `test_v182_timeframe_contract_includes_30m_and_4h_across_registry_runtime_and_mtf`
   - Expected: registry, runtime, and MTF conflict all expose `30m` and `4H`.
2. `test_v182_timeframe_duration_guard_accepts_30m_and_4h_without_leakage`
   - Expected: `30m` and `4H` durations pass point-in-time guard when bars are closed.
3. `test_v182_indicator_reliability_drilldown_accepts_30m_and_4h_research_only`
   - Expected: reliability report works for `30m` and `4H` and remains non-routing.
4. `test_v182_frontend_panel_map_exposes_indicator_reliability_drilldown`
   - Expected: panel map exposes `indicator_reliability_drilldown_v182`.
5. `test_v182_capability_manifest_tracks_full_timeframe_expansion`
   - Expected: capability manifest tracks the v1.82 contracts and promotion gates.

Current verification:

```text
Focused v1.82/v1.81/v1.80/v0.60/v0.61/v0.62/v0.72/v0.78 subset: 36 passed, 497 deselected
Full backend regression: 533 passed, 1 warning
```

## v1.83 Persistent Indicator Signal History Tests

Run:

```text
python -m pytest apps/api/tests/test_api.py -q -k "v183 or v182 or v181 or v180 or v061 or v062 or v072 or v078 or v060"
npm run typecheck
npm run build
python -m pytest apps/api/tests/test_api.py
```

Required cases:

1. `test_v183_persistent_indicator_signal_history_save_and_readback`
   - Expected: history record is persisted, readable, counted when complete, and research-only.
2. `test_v183_reliability_prefers_persisted_history_over_fixture_fallback`
   - Expected: reliability uses persistent history and reports `fixture_fallback_used=false`.
3. `test_v183_pending_indicator_history_is_stored_but_not_counted`
   - Expected: pending labels are stored but not counted in reliability.
4. `test_v183_reliability_drilldown_returns_trader_summary_and_history_packet`
   - Expected: drilldown returns reliability, history, trader summary, and blocked routing.
5. `test_v183_persistent_history_accepts_30m_and_4h_without_routing`
   - Expected: `30m` and `4H` persisted history works and remains non-routing.
6. `test_v183_panel_map_and_capability_manifest_track_persistent_indicator_history`
   - Expected: panel map and capability manifest expose v1.83.

Current verification:

```text
Focused v1.83/v1.82/v1.81/v1.80/v0.60/v0.61/v0.62/v0.72/v0.78 subset: 42 passed, 497 deselected
Frontend typecheck/build: passed
Full backend regression: 539 passed, 1 pytest cache warning
```

## v1.84 Current Indicator Signal History Ingestion Tests

1. `test_v184_current_indicator_signal_ingestion_writes_pending_history_only`
   - Expected: current ingestion writes pending records only; no counted reliability rows.
2. `test_v184_current_ingestion_is_idempotent_for_same_snapshot_signal_time_and_horizon`
   - Expected: repeated ingestion returns the same history ids and does not duplicate the selected row.
3. `test_v184_reliability_keeps_fixture_fallback_when_only_pending_ingested_rows_exist`
   - Expected: pending rows are visible in persisted history but reliability still uses fixture fallback until completed labels exist.
4. `test_v184_panel_map_and_capability_manifest_track_current_signal_ingestion`
   - Expected: panel map and capability manifest expose the v1.84 ingestion contract.

Verification:

```text
Focused v1.84/v1.83/v1.82/v1.81/v1.80 subset: 33 passed, 510 deselected
Frontend typecheck/build: passed
Full backend regression: 543 passed, 1 pytest cache warning
```

## v1.85 Pending Indicator Outcome Completion Tests

1. `test_v185_complete_pending_indicator_history_counts_completed_future_horizon`
   - Expected: supplied future bars complete a pending row, preserve history id, and make it reliability-countable.
2. `test_v185_incomplete_future_horizon_stays_pending_and_uncounted`
   - Expected: insufficient future bars keep the row pending and uncounted.
3. `test_v185_same_bar_target_stop_collision_uses_conservative_stop_first`
   - Expected: same-bar target/stop collision is labeled `SL_HIT` with conservative stop-first evidence.
4. `test_v185_panel_map_and_capability_manifest_track_pending_completion`
   - Expected: panel map and capability manifest expose the v1.85 completion contract.

Verification:

```text
Focused v1.85/v1.84/v1.83/v1.82/v1.81/v1.80 subset: 37 passed, 510 deselected
Frontend typecheck/build: passed
```

## v1.86 Signed TrendForge Research Intake Tests

Run:

```text
python -m pytest apps/api/tests/test_trendforge_bridge.py -q
```

Required cases (module `test_trendforge_bridge.py`):

1. Valid packet validation succeeds with correct HMAC and safety envelope.
2. Tampered packet / wrong secret is rejected.
3. Stale / age-gated packet handling keeps research-only posture.
4. Loopback pull path can use TrendForge export endpoint (mocked HTTP).
5. Remote TrendForge URL is blocked by default.
6. Intake persistence is idempotent for repeated save of the same validated record.

Cross-doc checks:

1. `docs/IMPLEMENTATION_STATUS.md` latest completed version is `v1.86`.
2. `docs/graph/project_graph.json` `summary.latest_completed_version` is `v1.86`.
3. `SPEC.md` contains Scope v1.86.
4. Graph edge integrity: every edge `from`/`to` exists in `nodes`; `summary.nodes`/`summary.edges` match array lengths.
5. No casual frontend TrendForge execute button is required (API/integration surface only).

Verification snapshot (implementation date):

```text
TrendForge intake focused tests: 6 passed
OpenAlgo adapter focused tests: 6 passed
OpenAlgo handoff allowed: false
Broker order created: false
```

## v1.88-v1.93 ORB Paper Guidance Tests

Focused coverage includes:

- fixed snapshot-bound engine order and deterministic receipts;
- strict primary/HTF closed-candle filtering;
- no fixture or future-created reliability evidence boosting confidence;
- low-evidence and missing-MTF caps;
- NSE ORB session locking and deterministic setup builders;
- asynchronous discovery determinism and trading-cost handling;
- OOS/walk-forward/consistency proof and promotion rules;
- no-playbook, mismatch, low-evidence, and positive eligible-ticket paths;
- no discovery/proof imports in the runtime guidance path;
- exact snapshot binding and server-owned trade levels;
- explicit approval, idempotency, tamper rejection, and filtering;
- OpenAPI/capability exposure and no route/execution imports.

Verification snapshot:

```text
v1.88-v1.93 focused backend: 85 passed
v1.92/v1.93 focused backend: 22 passed
full backend: 683 passed in 418.12s
frontend typecheck: passed
frontend build: passed
browser: RELIANCE 5m returns WATCH/NO_PLAYBOOK and disables record action
```

Production-readiness caveat:

- v1.93 proves guidance and local record safety, not profitable edge.
- v1.94 adds the outcome feedback, lifecycle monitoring, recovery/retention
  tests, configuration hardening, and operational evidence listed below.

## v1.94 ORB Paper Lifecycle Feedback Tests

File: `apps/api/tests/test_orb_feedback_hardening_v194.py`

Required cases `TV-V194-001` through `TV-V194-032` cover:

- environment-backed store, TTL, retention, cost, and evidence configuration;
- corruption fail-close, temporary-file recovery, concurrent atomic writes,
  idempotency, and stale-ticket rejection;
- exact guidance/playbook/proof/snapshot/symbol/timeframe identity;
- post-decision, closed, unique, consecutive, finite OHLC validation;
- deterministic long/short fill logic and no-fill behavior;
- conservative same-bar target/stop handling;
- MFE, MAE, cost breakdown, gross R, and net R;
- completed-outcome freezing and integrity hashing;
- completed-only reliability, Bayesian low-evidence handling, quarantine-only
  feedback, orphan exclusion, and storage monitoring;
- retention preview without deletion;
- OpenAPI/capability publication;
- no OpenAlgo, broker, order-routing, or live-trading path.

Browser acceptance:

```text
downloaded RELIANCE 1m
  -> closed 5m guidance with +6 replay holdout
  -> WATCH / NO_PLAYBOOK / MTF ALIGNED / evidence 0 of 30
  -> record and lifecycle buttons disabled
  -> store integrity PASS
```

Verification snapshot:

```text
v1.94 focused: 32 passed in 9.07s
v1.92-v1.94 focused: 54 passed
full backend: 715 passed in 542.50s
frontend workspace typecheck: passed
frontend production build: passed
desktop/mobile browser acceptance: passed with no horizontal overflow
```

## v2.01 ORB Opening Scenarios Tests (coded + finished)

File: `apps/api/tests/test_orb_opening_scenarios_v201.py` — 8 gates
`TV-V201-001..008` (gap/CPR/zone/parity/guards/coverage + predict_day_type
branches + label_day_outcome boundaries). Proves `orb/context.py` standalone
classifier; live `orb/core.py` wiring explicitly out of scope. Research-only,
live blocked.

## v2.02-derivatives ORB Derivatives Tests (coded + finished, OFF-by-default)

File: `apps/api/tests/test_orb_derivatives_v202.py` — 22/22 passed in host.
Proves NSE expiry/ticks, chain/Greeks calc, reasoning/store/bridges, OFF-profile
mount, shadow-gate on `OPENALGO_*`, ATR parity (SMA-seeded Wilder canonical),
research-only envelopes. Full backend tip: 914 passed 2026-09-07.
