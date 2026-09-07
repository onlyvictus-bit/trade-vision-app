# ORB v2.02 Repair & Integration — Campaign Plan (Candidate 2: capture-first hybrid)

> **Status:** APPROVED for planning; implementation NOT started. No source file is
> changed by this document.
> **Approval:** user approved Candidate 2 + 12 gates + release gate (conversation,
> 2026-09-07). Pivot condition mandatory. Candidate 3 (isolate-and-defer) is the
> fallback if G0 capture proves impossible.
> **Objective:** make staged v2.02 derivatives truthful, contract-correct, PIT-safe,
> replayable, and genuinely wired `OpenAlgo → canonical snapshots →
> DerivativesContext → v1.73 + AFRE capabilities → ORB SHADOW → proof`.
> **Hard scope:** the 12 gates below only. FORBIDDEN in this campaign: new Greeks,
> new strategy variants, new expiry intelligence, new scoring, new UI, live
> execution, derivatives trade-generation, unrelated ORB improvements. A P0 needing
> architecture outside this boundary returns as a scope-change proposal — it is not
> silently absorbed.
> **SHADOW invariants (whole campaign):** AFRE default OFF · derivatives default OFF ·
> no live profile · no live/broker/paper-promotion authority · derivatives may
> SUPPORT/CONFLICT/BLOCK/DELAY/CAP/REQUIRE-RETEST/REQUIRE-ACCEPTANCE/MARK-UNKNOWN,
> never originate a setup. Calculators stay untouched unless a test proves otherwise
> (anti-corruption boundary: vendor knowledge lives in the provider edge only).
> **Ordering rule:** G9/G10 do not begin until G0–G8 green. No wiring untrusted
> evidence deeper into the decision engine.

## Gate ordering

```text
G0  Capture + contract oracle (BLOCKING, gates everything)
 ↓
G1  Provider contract correction
G2  Batching / response mapping
G3  HTTP/error boundary
G4  Contract metadata fail-closed
 ↓
G5  PIT + identity hardening (campaign-critical)
 ↓
G6  Replay provider
G7  Truthful health/readiness
G8  SQLite/storage repair
 ↓
G9  v1.73 runtime wiring
G10 AFRE EventBatch wiring
 ↓
G11 Complete provenance chain
G12 Wall persistence decision
 ↓
Contract/PIT/replay/bridge/E2E test wave → full regression → SHADOW acceptance
```

## Re-sequence addendum (authorized 2026-09-07: "build remaining, paste creds later")

G0 capture is pending operator credentials. Until they arrive, the vendor-dependent
gates are PARKED (G1, G2, G4 field-name confirmation, G9, G10, OPENALGO-001/002,
BRIDGE-*, AFRE-*, E2E-001, captured-contract tests) and the vendor-independent
gates build in this order: G8 → G7 → G3 → G5 → G6 → G4-logic → G12 → G11-mechanism.
Rules for the interim: no rewrite against the unwitnessed vendor schema; G4 removes
fabricated defaults but real field-name mapping stays deferred to G1; G11 builds the
hash-chain mechanism on the current input set and is re-verified post-G1; synthetic
fixtures used below are canonical-domain (in-code), never vendor-JSON shaped.

## Build status 2026-09-07 (vendor-independent half DONE)

Implemented + verified: G8 (`:memory:` shared-cache + keepalive), G7 (truthful
health matrix), G3 (typed HTTP boundary: Auth/Unavailable + bounded retry),
G5 (admission gate + `DerivativesIdentityError` + 422 mapping + PIT-001..004),
G6 (`FixtureDerivativesProvider` + creds-free replay + REPLAY-001/002),
G4-logic (no fabricated lot/tick in either parser; field names pending G1),
G12 (top_k bounding + 1-step persistence + REQUIRED/OPTIONAL policy),
G11-mechanism (per-input hash fields + service computation; re-verify post-G1).
Parked: G0, G1, G2, G4-names, G9, G10 + captured/AFRE/bridge/E2E tests.
Evidence: `apps/api/tests/test_orb_derivatives_repair_v202r.py` 25 passed;
bundle `test_orb_derivatives_v202.py` 22 preserved; full backend **939 passed /
0 failed / 4 skipped** (997s). Deferred honestly: session-date-vs-exchange-
calendar validation (no calendar in scope); vendor-auth failures stay 503
(fail-closed; SHADOW-only).

---

## G0 — Capture + contract oracle (BLOCKING)

**Purpose:** replace the single-witness vendor model with immutable captured reality;
every later gate tests against it. Expected first result is failure of the current
parser — that failure is the oracle working.

**Files/surfaces allowed:** NEW ONLY — `apps/api/tests/fixtures/openalgo_captured/`
(raw responses + `manifest.json`), `scripts/capture_openalgo_contract.py` (capture
helper; API key from env, never written to disk), NEW
`apps/api/tests/test_orb_openalgo_contract_v202g0.py` (oracle tests: current parser
vs captured fixtures, expected to FAIL on mismatch). NO `app/` source changes.

**Preconditions:** live OpenAlgo credentials + reachable endpoint provided by the
operator for one capture session (NIFTY/NFO, one current expiry); approval to make
read-only vendor calls. If unavailable → pivot to Candidate 3, do not synthesize.

**Implementation intent:** capture 1× `OptionChain(with_greeks=true)`, 1×
`MultiOptionGreeks`, 1× expiry, 1× futures-search response. Manifest per fixture:
capture timestamp, endpoint, request shape (key redacted), HTTP status,
content-type, underlying, exchange, expiry, redactions applied. Raw fixtures
immutable afterwards; derived/normalized copies allowed with documented transform.

**Tests required:** oracle tests assert current `multi_option_greeks()` /
`option_chain()` output against captured fixtures field-by-field (expect mismatch
exposed, not hidden); manifest completeness test (every fixture has all manifest
fields; no `apikey|secret|token|cookie` bytes anywhere in the fixture dir).

**Acceptance:** 4+ fixtures captured with complete manifests; secret-scan clean;
oracle run demonstrates at least the P0-1/2/3 mismatches (or contradicts the judge
schema → trigger pivot instead).

**Failure/rollback:** capture impossible → STOP, propose Candidate 3. Fixtures are
additive; rollback = delete fixture dir + oracle test (no source touched).

**Evidence artifact:** fixture dir + manifest + oracle run transcript.

**Next-gate dependency:** G1–G4 rewrite targets the captured schema, never memory.

## G1 — Provider contract correction

**Purpose:** make the provider speak the captured API: correct endpoints, per-symbol
vs top-level fields (`expiry_time` top-level; drop `forward_price` per-item unless
captured), correct Greeks mapping (strike/CE-PE/DTE/spot/price joined by `symbol`
from the chain leg, never expected from the batch response).

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/openalgo.py`
(request builders + `multi_option_greeks()` + `option_chain()` parsers only);
`apps/api/tests/test_orb_derivatives_v202.py` (fix the mocked hybrid response to
captured shape); NEW/EXTENDED captured-contract tests. NOT calculators, reasoning,
bridges, AFRE, v1.73.

**Preconditions:** G0 green (or pivot-resolution re-plan).

**Implementation intent:** prefer `OptionChain(with_greeks=true)` as primary
chain+Greeks source; keep `MultiOptionGreeks` for Rho/validation. Remove
`row["strike"]` / `row["option_type"]` hard requirements on batch rows; join by
`symbol` to the canonical chain leg.

**Tests required:** OPENALGO-001 (captured batch response parses to exact expected
`Greeks`; 0 silently dropped on captured input).

**Acceptance:** captured fixtures parse with zero silent drops; previously-passing
synthetic tests updated to captured shape, still green; full-file `compileall` clean.

**Failure/rollback:** revert `openalgo.py` to staged state (git); oracle still fails
as before (no worse).

**Evidence artifact:** parser diff + OPENALGO-001 transcript.

**Next-gate dependency:** G2 builds on corrected field mapping.

## G2 — Batching / response mapping

**Purpose:** enforce the real batch constraint end-to-end (chunk 50/50+remainder at
the call site, not just validation).

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/openalgo.py`
(`multi_option_greeks()`, `greeks_for_chain()` defaults + chunking).

**Preconditions:** G1 green.

**Implementation intent:** default batch 50, hard range 1..50; chunk inside the
provider so callers cannot emit an illegal request; preserve ordering across chunks.

**Tests required:** OPENALGO-002 (51 symbols → 50+1 wire calls, order preserved;
52nd-leg results mapped to correct legs).

**Acceptance:** no code path can emit >50 symbols/request (test constructs the
60-leg case from the judge repro and observes 50+10).

**Failure/rollback:** revert `openalgo.py`.

**Evidence artifact:** OPENALGO-002 transcript + wire-call capture.

**Next-gate dependency:** G3 hardens what G1/G2 now correctly send.

## G3 — HTTP/error boundary

**Purpose:** every transport/HTTP failure becomes a sanitized typed error; nothing
raw escapes the provider, and the FastAPI route's `except OpenAlgoError` boundary
holds.

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/openalgo.py` (`_post()`
retry/except mapping); error classes in same file (`OpenAlgoError` subclasses);
route handler in `apps/api/app/orb/derivatives/api.py` ONLY to widen/narrow its
except clause to the new taxonomy (no logic changes).

**Preconditions:** G1 green.

**Implementation intent:** catch `httpx.HTTPStatusError` explicitly: 400/401/403 →
protocol/auth errors (message sanitized, key redacted as today); 429/transient 5xx
→ bounded retry then `OpenAlgoUnavailable`; final 5xx → unavailable. No API key,
no raw provider payload in any message.

**Tests required:** OPENALGO-003 (400/401 → controlled typed error, key absent from
message); OPENALGO-004 (429 → bounded retries then clean failure); OPENALGO-005
(5xx → bounded retries then `OpenAlgoUnavailable`).

**Acceptance:** fault-injection matrix green; route returns controlled application
responses for all injected statuses (no raw 500 from the derivatives router).

**Failure/rollback:** revert the two files.

**Evidence artifact:** fault matrix transcript.

**Next-gate dependency:** G6/G7 build on a truthful error taxonomy.

## G4 — Contract metadata fail-closed

**Purpose:** missing exchange contract metadata (`lotsize`, `tick_size`) becomes
PARTIAL/BLOCKED evidence, never fabricated constants — fabricated lot size
corrupts GEX/wall math multiplicatively.

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/openalgo.py` (chain
parser), `apps/api/app/orb/derivatives/fixtures.py` (CSV fixture parsing),
`apps/api/app/orb/derivatives/contracts.py` (metadata-missing status, if a new
literal is needed), affected tests.

**Preconditions:** G1 green.

**Implementation intent:** delete `or 1` / `or 0.05` defaults; missing metadata →
explicit `CONTRACT_METADATA_MISSING` with PARTIAL/BLOCKED propagation; fixtures
with blank leg columns exercise the path.

**Tests required:** OPENALGO-006 (chain missing lotsize/tick → PARTIAL/BLOCKED, no
wall/GEX emitted from fabricated values).

**Acceptance:** grep proves no `or 1)` / `or 0.05` numeric defaults remain on the
metadata path; OPENALGO-006 green.

**Failure/rollback:** revert touched files.

**Evidence artifact:** OPENALGO-006 transcript + defaults-grep output.

**Next-gate dependency:** G5 identity gates assume untrusted-input discipline from
G3/G4.

## G5 — PIT + identity hardening (campaign-critical)

**Purpose:** make the causal contract structural: wrong-symbol, future-dated, or
wrong-expiry/session derivatives evidence can never reach a scenario assessment
while claiming `no_future_leakage=True`. No code may repair causality by advancing
the decision timestamp (`max(...)` forbidden).

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/contracts.py`
(`ScenarioAssessment` + identity fields), `apps/api/app/orb/derivatives/service.py`
and `reasoning.py` (admission gate before assessment), tests. NOT calculators.

**Preconditions:** G1–G4 green.

**Implementation intent:** mandatory admission check —
`scenario.symbol == context.symbol`, `context.as_of_ns <= scenario.as_of_ns`,
expiry/session identity belongs to the requested instrument, every contributing
input available by decision time — else `DERIVATIVES_SYMBOL_IDENTITY_MISMATCH` /
`DERIVATIVES_CONTEXT_FROM_FUTURE` hard rejection. Add the approved extra test:
same symbol, wrong expiry/session rejected. Identity contract:
`scenario.symbol == derivatives.symbol`, `derivatives.as_of_ns <= decision.as_of_ns`.

**Tests required:** PIT-001 (BANKNIFTY scenario + NIFTY context rejected);
PIT-002 (context `as_of` T+10s vs scenario T rejected, incl. the judge's exact
repro); PIT-003 (stale/expired evidence cannot authorize a candidate); NEW
PIT-004 (same symbol, wrong expiry/session rejected).

**Acceptance:** all four red; judge's P0-7 repro now rejects instead of
`accepted=True`; `no_future_leakage` remains a `Literal[True]` the type system
cannot lie about (rejection happens before the flag is minted).

**Failure/rollback:** revert touched files; subsystem stays OFF so nothing
untrusted flows meanwhile.

**Evidence artifact:** PIT transcripts incl. P0-7 repro reversal.

**Next-gate dependency:** G9/G10 wiring is only safe behind this gate.

## G6 — Replay provider

**Purpose:** `profile=replay` runs with zero OpenAlgo credentials on fixture/PIT
data only; also fix the READY-while-crashing lie structurally (health reflects
provider readiness — completed in G7, founded here).

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/integration.py`
(`build_service` profile switch), `service.py` (provider selection),
`fixtures.py` (fixture-backed provider if missing — check first, reuse helpers),
tests.

**Preconditions:** G3 green (error taxonomy), G1 green (parser).

**Implementation intent:** `shadow → OpenAlgoDataProvider`; `replay →`
fixture-backed provider (fail closed if fixture absent); `off → nothing loaded`.
`build_service()` must not touch `OPENALGO_*` env on the replay path.

**Tests required:** REPLAY-001 (replay profile, creds absent → analyze works);
REPLAY-002 (replay output equals fixture/PIT-derived expectation byte-for-byte;
no network client constructed — assert via injected failing transport).

**Acceptance:** judge's P0-8 repro (`replay` + no creds + POST /analyze) succeeds
on fixtures instead of `KeyError: OPENALGO_BASE_URL`.

**Failure/rollback:** revert integration/service; profile stays OFF.

**Evidence artifact:** REPLAY transcripts with creds provably absent (env scrubbed
in test).

**Next-gate dependency:** G7 health semantics + E2E-002 determinism build on this.

## G7 — Truthful health/readiness

**Purpose:** `/health` reports `mounted/profile/provider_ready/store_ready` truth;
never unconditional `ready`.

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/api.py` (`health`
handler only) + tests.

**Preconditions:** G6 green.

**Implementation intent:** health reflects actual provider/store state per profile
(off → dormant truthfully; replay → fixture readiness; shadow → credential +
reachability state without leaking secrets).

**Tests required:** health matrix (off/replay-unconfigured/replay-ready/shadow
states each report distinct truthful payloads).

**Acceptance:** no profile returns `ready` while its analyze path would crash.

**Failure/rollback:** revert `api.py` handler.

**Evidence artifact:** health matrix transcript.

**Next-gate dependency:** SHADOW acceptance reads this endpoint.

## G8 — SQLite/storage repair

**Purpose:** `:memory:` works (shared-cache URI or persistent connection) or is
explicitly rejected with a clear error — no more vanishing-schema
`OperationalError`.

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/store.py`
(`__init__`/connection handling) + tests.

**Preconditions:** none (independent; scheduled here to keep storage work together).

**Implementation intent:** prefer shared-cache-memory URI or single persistent
connection; if rejected instead, raise at construction with message naming the
supported alternative. Keep `timeout=5.0` behavior and disk path untouched.

**Tests required:** STORE-001 (`:memory:` round-trip works, or construction raises
the explicit error — assert whichever is implemented, plus disk regression).

**Acceptance:** judge's P0-10 repro resolved either way; disk-path tests green.

**Failure/rollback:** revert `store.py`.

**Evidence artifact:** STORE-001 transcript.

**Next-gate dependency:** provenance (G11) persists through this store.

## G9 — v1.73 runtime wiring

**Purpose:** `v173_payload_overlay` stops being an island: the live
`execution-event-oi/risk/analyze` path automatically consumes computed
`DerivativesContext` from the same causal snapshot.

**Files/surfaces allowed:** `apps/api/app/behavior/execution_event_oi_risk.py`
(context lookup + overlay call inside `build_execution_event_oi_risk_report`),
`apps/api/app/orb/derivatives/bridges.py` (adapter hardening only if tests demand),
wiring tests. GATED: only after G0–G8 green.

**Preconditions:** G0–G8 green (enforced — no wiring untrusted evidence deeper).

**Implementation intent:** endpoint resolves derivatives context for the request's
symbol/expiry/session (same snapshot identity), overlays via the existing helper,
falls back to caller-provided fields with explicit UNKNOWN marking when context
unavailable (per the BLOCK/UNKNOWN policy below).

**Tests required:** BRIDGE-001 (context → real `ExecutionEventOiRiskRequest`
populated automatically); BRIDGE-002 (existing endpoint returns computed — not
caller-typed — values on a captured fixture).

**Acceptance:** captured-fixture request produces context-derived v1.73 fields
without manual payload construction; unavailable-context case marks UNKNOWN
(never CLEAN).

**Failure/rollback:** revert behavior file; helper remains (harmless island).

**Evidence artifact:** BRIDGE transcripts with request/response pairs.

**Next-gate dependency:** E2E-001 traverses this bridge.

## G10 — AFRE EventBatch wiring

**Purpose:** derivative capabilities flow `ScenarioAssessment → typed Capability →
EventBatch.capabilities[symbol] → advance_session() → MarketSnapshot.capabilities
→ Controller.evaluate()` automatically. A unit test calling
`afre_capability_payloads()` alone is NOT acceptance.

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/bridges.py`
(typed-capability constructor), a THIN injection point on the AFRE session path
(`apps/api/app/orb/adaptive/runtime.py` `advance_session` input construction or
`service.py` batch assembly — whichever the code proves owns batch creation; no
controller/policy logic changes), tests.

**Preconditions:** G0–G8 green; G5 green (capabilities carry PIT-valid context).

**Implementation intent:** convert `ScenarioAssessment` to AFRE `Capability`
objects (reuse `afre_capability_payloads` output shape), insert into
`EventBatch.capabilities[symbol]`; existing `advance_session` merge
(`runtime.py:174-175`) and required-capability enforcement carry them (already
built). AFRE policy requires nothing new.

**Tests required:** AFRE-001 (capability present in EventBatch); AFRE-002
(reaches `MarketSnapshot` via `advance_session`); AFRE-003 (BLOCK capability
blocks candidate); AFRE-004 (SUPPORT alone cannot create a candidate).

**Acceptance:** full chain green on captured fixtures; AFRE default remains OFF;
no controller/policy file modified (verify via diff).

**Failure/rollback:** revert bridge + injection point; AFRE untouched.

**Evidence artifact:** AFRE-001..004 transcripts.

**Next-gate dependency:** E2E-001 traverses this chain.

## G11 — Complete provenance chain

**Purpose:** every input that shapes a `DerivativesContext` is hash-pinned:
chain, Greeks, futures, previous chain/futures, IV history, next-expiry snapshot,
policy.

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/contracts.py`
(hash fields), `service.py` (hash computation at build), `store.py` (persist new
hashes if schema allows without migration pain — else document; no unapproved
migration), tests.

**Preconditions:** G1 green (know all inputs), G8 green (know store limits).

**Implementation intent:** extend `source_hash` into per-input hashes
(`chain_snapshot_hash`, `greeks_snapshot_hash`, `futures_snapshot_hash`,
`previous_*`, `iv_history_hash`, `next_expiry_snapshot_hash`, `policy_hash`);
replay can re-derive and compare each.

**Tests required:** provenance test (mutate one Greeks input → exactly the Greeks
hash + context hash change; all others stable); replay re-derivation equality.

**Acceptance:** proof-grade replay: identical raw inputs → identical full hash
chain (feeds E2E-002).

**Failure/rollback:** revert contracts/service; prior single-hash behavior intact.

**Evidence artifact:** provenance mutation transcript.

**Next-gate dependency:** E2E-002 asserts on this chain.

## G12 — Wall persistence decision

**Purpose:** close the unfinished piece honestly: implement multi-snapshot wall
persistence (`FORMING/STABLE/STRENGTHENING/WEAKENING/UNWINDING` + `persistence`)
or remove/flag the unsupported field. Also resolve the UNAVAILABLE inconsistency
(scenario controller says WATCH vs AFRE capability says BLOCK) via the explicit
policy below — decided here, tested here, not drifted into during G9/G10.

**Files/surfaces allowed:** `apps/api/app/orb/derivatives/calculators.py`
(`dominant_oi_wall` `top_k` use + persistence), `contracts.py` (Wall fields),
`reasoning.py` (UNAVAILABLE mapping), tests.

**Preconditions:** G1 green (wall inputs correct).

**Implementation intent:** either wire `top_k` + persistence from ΔOI across
snapshots, or delete/flag the field with a documented NOT-SUPPORTED marker.
Policy (approved, implement exactly):
`REQUIRED-BY-PROVED-POLICY + unavailable/stale/invalid → BLOCK/WAIT`;
`OPTIONAL-SHADOW + unavailable → UNKNOWN, price-only continues, zero derivative
contribution`; and `UNKNOWN ≠ BULLISH/BEARISH/CLEAN` asserted in tests.

**Tests required:** wall test (persistence transitions on a 3-snapshot captured
sequence, or NOT-SUPPORTED marker test); policy tests for both branches +
`UNKNOWN`-is-not-clean assertion.

**Acceptance:** no dead `top_k` parameter; no unmarked `persistence = 0`; policy
branches green.

**Failure/rollback:** revert calculators/contracts/reasoning.

**Evidence artifact:** wall/policy transcripts.

**Next-gate dependency:** none (terminal gate before test wave).

---

## Test wave + release gate (after G12)

Run in order: new OPENALGO/PIT/REPLAY/STORE/BRIDGE/AFRE/E2E suites → full backend
`pytest` → `compileall` → `git diff --check` → secret scan
(`apikey|api_key|authorization|bearer|secret|password|token` — review every hit) →
SHADOW acceptance (health truthful, OFF defaults, no live authority). Final report
uses the approved format with real counts (`X passed / 0 failed / Y skipped /
Z xfailed / duration`); never promote `collected` into `passed`.

## Rollback criterion (campaign-wide)

Any unresolved P0 · any PIT violation · nondeterministic replay · legacy ORB
regression · external-contract ambiguity affecting calculations · new order
authority · proof bypass → derivatives profile stays OFF, no policy promotion.
Per-gate reverts listed above; cross-gate state never depends on reverted work
because G9/G10 wait for G0–G8.

## Traceability seed (stable IDs)

| Req | Gate | Implementation surface | Verification | Status |
|---|---|---|---|---|
| TV-RPR-000 capture oracle | G0 | fixtures + oracle test | manifests + mismatch demo | planned |
| TV-RPR-001/002 provider+batch | G1/G2 | `openalgo.py` | OPENALGO-001/002 | planned |
| TV-RPR-003 error boundary | G3 | `openalgo.py` + `api.py` handler | OPENALGO-003/004/005 | planned |
| TV-RPR-004 metadata fail-closed | G4 | `openalgo.py`, `fixtures.py`, `contracts.py` | OPENALGO-006 | planned |
| TV-RPR-005 PIT/identity | G5 | `contracts.py`, `service.py`, `reasoning.py` | PIT-001..004 | planned |
| TV-RPR-006 replay | G6 | `integration.py`, `service.py`, `fixtures.py` | REPLAY-001/002 | planned |
| TV-RPR-007 health | G7 | `api.py` | health matrix | planned |
| TV-RPR-008 storage | G8 | `store.py` | STORE-001 | planned |
| TV-RPR-009 v1.73 wiring | G9 | `execution_event_oi_risk.py`, `bridges.py` | BRIDGE-001/002 | planned |
| TV-RPR-010 AFRE wiring | G10 | `bridges.py` + thin injection | AFRE-001..004 | planned |
| TV-RPR-011 provenance | G11 | `contracts.py`, `service.py`, `store.py` | provenance tests | planned |
| TV-RPR-012 walls/policy | G12 | `calculators.py`, `contracts.py`, `reasoning.py` | wall + policy tests | planned |
| TV-RPR-013 release | wave | all | full regression 0-failed + SHADOW | planned |

## After OpenAlgo credentials arrive (G0 unblock checklist)

Paste `OPENALGO_BASE_URL` + `OPENALGO_API_KEY` (session env only — never written
to files, fixtures, or manifests). Then code the parked half in this order:

```text
G0  Capture (BLOCKING): 1x OptionChain(with_greeks=true) + 1x MultiOptionGreeks
    + 1x expiry + 1x futures-search (NIFTY/NFO, one current expiry) via
    scripts/capture_openalgo_contract.py (to be written at G0; key from env).
    Manifest per fixture: timestamp, endpoint, redacted request, HTTP status,
    content-type, underlying/exchange/expiry. Raw fixtures immutable under
    apps/api/tests/fixtures/openalgo_captured/. Then run the current parser over
    them: expected result is FAILURE exposing the real mismatch (oracle working).
    Pivot rule: capture contradicts the provisional model (different endpoints,
    batching, nesting, auth, no with_greeks) -> STOP G1, return with the observed
    contract, revise plan. No creds -> Candidate 3 (isolate-and-defer), no fakes.
```

```text
G1  Provider correction (openalgo.py): remap chain/Greeks parsing field-by-field
    to captured truth; replace PROVISIONAL_* block; keep strict join + report.
    Tests: OPENALGO-001 rewritten against captured fixtures (must use captured or
    byte-identical-derived-with-redactions — never memory-written vendor JSON).
G2  Batching (openalgo.py): confirm/adjust OPENALGO_MULTI_GREEKS_MAX_BATCH from
    capture; keep auto-chunking. Test: OPENALGO-002 with captured limit.
G4  Field names: point CONTRACT_METADATA_MISSING at confirmed lotsize/tick fields;
    re-run OPENALGO-006 + full suite.
G9  Flip the switch: set TRADEVISION_V173_DERIVATIVES=on in shadow env; POST
    /risk/analyze now auto-consumes context (code already wired). Prove with a
    live replay-backed BRIDGE run; any failure -> flag back off, report.
G10 Enable derivatives_source in the live AFRE session path (research.py seam is
    built; production caller passes it). Prove AFRE-001..004 against a captured
    session; SUPPORT-still-creates-nothing re-proven on live-shaped data.
Wave Release gate: captured-contract tests + PIT adversarial + replay determinism
    + full backend 0-failed with REAL counts (X passed / 0 failed / Y skipped) +
    SHADOW acceptance (health truthful, OFF defaults, no live authority). Only
    then discuss main; the NO-GO-for-main stands until this checklist is green.
```
