# Indicator Intelligence Catalog

- **Version**: v1.96 (catalog build)
- **Generated**: 2026-08-25 by `scripts/build_indicator_intelligence_catalog.py` (deterministic, re-runnable)
- **Scope approval**: 2026-08-25 — vendor copy authoritative; leakage forced to explanation-only; all 94 covered; catalog+tests only

## 1. What this is

One structured contract per discovered indicator available to Trade Vision: what it
calculates, from what data, with what formula evidence, what its signal means, when it
helps, when it fails, and how Trade Vision may use it safely. Machine-readable truth:

| Artifact | Path |
|---|---|
| Contracts (94 records) | `data/indicator-intelligence/indicator_contracts.v1.json` |
| Coverage report | `data/indicator-intelligence/indicator_coverage_report.json` |
| Group & use map | `docs/INDICATOR_GROUP_AND_USE_MAP.md` |
| Human table (generated) | `docs/generated/INDICATOR_CATALOG_TABLE.md` |
| Generator | `scripts/build_indicator_intelligence_catalog.py` |

## 2. Discovery result (first audit, code-verified)

- Registry entries: **94** (`build_indicator_registry_report()`, lock gates TV-V060-001/002)
  - self_indc (`si_*`): **71** ≡ `SELF_INDC_REGISTRY` in vendor copy (exact match both directions)
  - PTA markers (`pta_*`): **23** ≡ `PTA_SIGNAL_METADATA`
- Actually computed at runtime: **49** (`REAL_RUNTIME_PROMOTED_INDICATORS` — read live from the adapter at generation time; v1.99 Waves 1b+2 added 27)
- Registry status: **86 validated / 7 proxy / 1 blocked** (v1.99 Wave 3 audits; proxy = PIT or latency pending; blocked = constant-output stub; never probability-enabled)
- Runtime buckets reconcile exactly:
  `49 promoted + 21 registered_not_promoted + 23 pta_probe_only + 1 near_stub (si_flowscope) = 94`

## 3. Authority decision

The runtime imports the **vendor copy** (`apps/api/app/vendor/stock_app/shared/indicators/`),
which has drifted *ahead* of `shared/indicators/self_indc.py` (tz-safe weekly-VWAP fix never
backported). Per scope approval this catalog documents the vendor copy as authoritative;
the drift is recorded in every `si_*` record's `source_drift_note` and listed as a
follow-up proposal.

## 4. Safety model baked into contracts

1. **A BUY/SELL marker is evidence, not permission.** Every record carries
   `usable_for_trade_action=false` and `research_only=true`; the platform remains
   paper-guidance only.
2. **Missing stays missing**: `missing_policy` comes from the registry; nothing converts
   absent output into a zero signal.
3. **Six indicators leak future outcomes** and are forced to
   `evidence_role=explanation_only_forced`, `usable_for_probability=false`,
   `lookahead_risk=future_outcome_leakage` with the exact mechanism cited:
   si_delta_vp, si_hybrid_ml_cpr, si_sweep_inside_rr, si_opening_range_rev,
   si_hyb_opening_range_rev, si_problty_grid.
4. **Centered-pivot / ZigZag repainting** is classified per indicator
   (`centered_pivot_confirmation` MEDIUM, `zigzag_repaint` HIGH) with disclosed
   confirmation delay where one exists (e.g., si_rsi_div_auto emits at pivot+right,
   si_fractal at pivot+2).
5. **lag_weight = 1 / (1 + confirmation_delay_bars)**, computed at generation time,
   matching `indicator_lag_voting.py:15-16`.
6. **Redundancy families** (13 documented) mark correlated members; correlated
   indicators must not receive independent full votes.
7. **MTF** uses only fully closed higher-timeframe candles via the adapter path.
8. **No verified formula ⇒ UNKNOWN**: heuristic/rule-based engines carry
   `mathematical_formula=UNKNOWN_HEURISTIC_RULESET_SEE_CALCULATION_STEPS`; classic
   library wrappers cite the library call + parameters instead of invented math.
9. **Proxy/mock visibly labelled**: implementation_status, runtime_status,
   capability_status_at_audit are on every record.

## 5. Known platform limitations (documented, not fixed here)

1. 9C-DNA evidence path uses **real HSTRY bars when available** (v1.98); symbols
   without local history fall back to synthetic candles labelled
   `source_mode=synthetic_fallback`. Paper-guidance snapshots always use real bars.
2. All `/behavior/indicators*` routes report `CapabilityStatus.MOCK`
   (`app/state.py:208`).
3. ~25 `si_*` groups depend on exec-loaded external modules from hardcoded local paths
   (`self_indc.py:29-30,3290-3533`); a missing path degrades silently to empty output.
4. `EMPTY_NO_SIGNAL_ON_SAMPLE` proxy labels are a stale single-sweep snapshot.
5. Reliability memory falls back to fabricated fixture labels when the history DB is
   empty (`indicator_reliability_memory.py:314-360`) — rates are marked
   `rates_provenance=fixture_fallback_until_real_labels_ingested`.
6. Seven shadowed duplicate function definitions inside `self_indc.py` (registry binds
   the last def); two duplicate wirings (si_har_zz≡si_harmonic module, si_mk_inside≈si_inside_out).

## 6. Follow-up proposals (out of catalog scope)

See `follow_up_proposals_out_of_catalog_scope` in the coverage report JSON.

## 7. Frontend / API integration plan (concise)

- **API**: serve the artifact read-only —
  `GET /api/v1/behavior/indicators/intelligence` (list: id, name, group, status,
  lag_weight, lookahead) and `GET /api/v1/behavior/indicators/intelligence/{indicator_id}`
  (full contract). Implementation: load JSON at startup, expose via existing router
  style, keep `capability_status=research_only`; cache-bust on `ontology_version`.
- **Frontend**: one Research-tab panel ("Indicator Intelligence") rendering the list +
  detail view display-only. No new write paths; no trading surfaces; panel must show
  proxy/future-leak badges from the contract flags.
- **Decision spine**: contracts are documentation-of-record for D3a setup candidates;
  arbiter consumption continues to flow through existing promoted-indicator paths with
  family vote-weight rules applied upstream (this catalog does not wire votes).

## 8. Verification matrix pointer

Final matrix (indicator → formula → output → purpose → group → action → failure mode →
runtime status → source → test) is realized by joining the contracts JSON with the
generated table; per-record `source_evidence` and `test_ids` close the loop.
