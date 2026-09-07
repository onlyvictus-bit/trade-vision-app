# D6 M2/M3 — Milestone Sheet (executable)

> **Approved:** user said "yes create sheet and start coding" (2026-09-07).
> Parent plan: `docs/plans/D6_TRADEVISION_INTEGRATION_PLAN.md` §4.
> Scope boundary: shadow adapter + evidence + tests. Paper enablement is NOT completable
> here (no validation producer, no account allocator exist) — M3 ends at shadow-readiness
> evidence plus an explicit NOT-DONE statement, never a paper decision.

## M2-A — Raw-contribution ledger (analysis, docs-only)- **Purpose:** every number entering `final_confluence_arbiter` classified once, so the
  adapter can never launder a risk penalty as directional evidence.
- **Surfaces:** read `behavior/final_confluence_arbiter.py` (`_votes`, `_conflicts` C001–C008,
  `_hard_block`, `_decision`, `_bounded_score`), `behavior/paper_guidance_spine.py`
  evidence builders, `behavior/orb_guidance.py` ticket inputs. Write ledger table below.
- **Ledger columns:** producer (file:line) | raw field | class (LONG / SHORT / QUALITY / RISK / GATE / COST / OPS) | D6 target (evidence group / risk dimension / required check / unmapped→WAIT) | notes.
- **Forbidden mapping:** `long=max(old,0)` / `short=max(-old,0)` splits of any mixed score;
  any risk value used as directional evidence; any silent default for missing required input.
- **Acceptance:** every arbiter vote + conflict code traced to ≥1 ledger row; unmapped rows
  listed explicitly with WAIT/WATCH fallback each. Verified by user review of this sheet.
- **Rollback:** docs-only; delete section.

## M2-B — Shadow adapter module (new file, dormant by default)

- **Purpose:** read-only comparator: live spine evidence → D6Engine → divergence record.
  D6 places no orders, changes no bands, writes no ledger.
- **Files:** NEW `apps/api/app/behavior/d6_shadow_adapter.py` only (+ imports of vendored
  `tradevision_d6` and host evidence types; no edits to existing files in this gate).
- **Intent:** `compare(spine_evidence) -> DivergenceRecord{input_hashes, arbiter_band, d6_decision, side_each, cause_of_difference}`; flag `TRADEVISION_D6_SHADOW` (default `off`; `off` → adapter returns None without constructing D6 objects); demo issuers/keys rejected; all exceptions → recorded divergence, never raised.
- **Acceptance:** adapter returns None with flag off; with flag on produces deterministic
  divergence records on fixture evidence; raises nothing on malformed input.
- **Rollback:** delete file (nothing references it yet).

## M2-C — Adapter tests (new file)

- **Files:** NEW `apps/api/tests/test_d6_shadow_adapter.py`.
- **Tests required:** determinism (same input → identical record); risk-increase sweep
  (each of 5 risks raised holding evidence fixed → D6 permission nonincreasing, evidence
  invariant); blocked-LONG stays WAIT (no SHORT fallback); missing required source → WAIT;
  demo-key/proof rejection; malformed input → recorded, not raised; flag-off → None.
- **Acceptance:** all green alongside untouched host suites.
- **Rollback:** delete file.

## M2-D — Spine wiring (flag-gated, dormant default)

- **Purpose:** call the adapter once per P1 guidance run, log divergence, discard result.
- **Files:** `behavior/paper_guidance_spine.py` (single call site post-arbiter) + test proving
  flag-off output is byte-identical to pre-wire output.
- **Intent:** `TRADEVISION_D6_SHADOW=off` default → zero behavior change (proven by test);
  `on` → divergence appended to guidance receipt metadata only (no band/ledger/order effect).
- **Acceptance:** flag-off byte-identity test; flag-on smoke on fixture evidence; full suite green.
- **Rollback:** revert the call-site hunk (adapter module stays dormant).

## M3-A — Endpoint traversal tests

- **Purpose:** prove adapter monotonicity through real entry points, not just unit calls.
- **Files:** extend `test_d6_shadow_adapter.py`.
- **Tests:** risk-increase sweep through POST paper-guidance route + v1.73 + Jarvis decision-room read path where feasible; positive/negative/conflict/absent setups; vetoed-preferred-never-fallback end-to-end.
- **Acceptance:** green; any endpoint that cannot carry the sweep is listed, not faked.

## M3-B — HTF/PIT audit on the adapter path

- **Purpose:** prove the adapter cannot be fed future or unclosed-bar evidence.
- **Tests:** future-timestamped evidence rejected; incomplete HTF bars excluded; revision change alters input hash (cache cannot serve stale).
- **Acceptance:** green.

## M3-C — Acceptance-gate evidence ledger (docs update)

- **Purpose:** honest scorecard against the author's 6 gates.
- **Content:** gates 1 (diff reviewed, paths accounted), 3 (PIT tests), 4 (chronological validation status), 6 (observability/kill-switch) with evidence links; gates 2 (validation producer) and 5 (account allocator) marked **NOT BUILT — paper decision blocked**, with what each would require.
- **Acceptance:** `docs/plans/D6_TRADEVISION_INTEGRATION_PLAN.md` §7 updated; no paper-enablement language anywhere.

## M2-A ledger (completed 2026-09-07; M2-B/C/D also complete — see below)

Host truth: `final_confluence_arbiter._votes` sums SIGNED layer votes + conflict
adjustments into one net score (`final_confluence_arbiter.py:29-31`); direction comes
from per-vote thresholds (`_direction`, `:199`) and the single `request.direction`.
No layer emits independent LONG/SHORT evidence — the pipeline is single-hypothesis.

| Producer (file:line) | Raw field | Class | D6 target |
|---|---|---|---|
| arbiter `:74` market_regime_score | signed direction measure | LONG/SHORT (agreed side only) | evidence `market_regime` |
| arbiter `:75` structure_score | signed direction measure | LONG/SHORT (agreed side only) | evidence `structure_levels` |
| arbiter `:76` volume_auction_score | signed direction measure | LONG/SHORT (agreed side only) | evidence `volume_auction` |
| arbiter `:77` relative_strength ×2-1 | signed direction measure | LONG/SHORT (agreed side only) | evidence `relative_strength` |
| arbiter `:78` indicator_signal_score | signed direction measure | LONG/SHORT (agreed side only) | evidence `indicators` |
| arbiter `:70` risk_safety vote | trap/event/liquidity/data penalty | RISK/GATE | risks + hard-gate mapping, never evidence |
| arbiter `:71-72` data/liquidity votes | quality/grade state | GATE | snapshot booleans + risk vector, never evidence |
| arbiter `:79` post_entry vote | thesis state | GATE | invalidated ⇒ no plans; else ignored (documented) |
| arbiter `:79` external_ai vote | reviewer opinion | OPS (excluded) | omitted; D6 has no reviewer channel |
| arbiter `:95-113` conflicts C001-C008 | block/downgrade rules | GATE | dominant hard-block ⇒ plans withheld; rest ⇒ divergence notes |
| spine `:185-203` v1.73 receipt | slippage_risk et al | RISK | execution risk (documented mapping) |
| spine `:236` event_risk_score | event risk 0..1 | RISK | event risk direct |
| spine `:235` trap_score | trap risk 0..1 | RISK | trap risk direct |
| spine `:227-228` data_quality/liquidity | quality state | RISK/GATE | data_uncertainty 0/1; liquidity via versioned table |
| ticket/entry plan | entry/stop/target + authority | QUALITY/setup | plan (quality = evidence-count ratio) or no plan |

Corroboration-only feeding proof: for asserted direction d with net layer value v of
agreeing sign, D6's checks reduce to `|v| >= minimum_evidence` (conservative: true
side-support >= |v| under bounded components) and margin exactly `|v|` (net math).
Disagreement is excluded from sums AND recorded as `D6_SHADOW_LAYER_DISAGREES`
conflict. No rescaling, no silent zeroing, no generic sign-splitter exists.
UNMAPPED (always WAIT/WATCH, never candidate): neutral/missing direction, missing
risks (`EXECUTION_RISK_UNAVAILABLE` only when spine receipt absent), no plans
(`NO_PLAN_NO_SETUP`), proof absent (D6 `proof_valid=False` path — a genuine standing
finding: host approves paper with no validation proofs).

## M2 build record (completed 2026-09-07)

- M2-B adapter ehavior/d6_shadow_adapter.py: flag-gated, output-neutral sidecar design; corroboration-only feeding with exactness argument in ledger.
- M2-C tests 	ests/test_d6_shadow_adapter.py: 14 green (determinism, monotonicity, no-fallback, abstains, neutrality, policy versioning).
- M2-D wiring: post-arbiter call site in paper_guidance_spine.py, bounded sidecar JSONL (500 lines), byte-neutral guidance proven both flag states.
- Full backend at commit: 1215 passed / 0 failed / 4 skipped. M3 gates + paper decision NOT started.
