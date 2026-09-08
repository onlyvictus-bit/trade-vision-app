# AFRE v4 Merge Status — 2026-09-08

## Status

AFRE v4 production hardening is merged into `main`.

```text
PR: #1
branch: afre-v4-production-hardening
final branch head: 83ff12c422d3426f51374e7155dabfda4f7503e8
main merge commit: 83070628bf153557ac6f5f54a025866bd484f76d
merged_at: 2026-09-08T08:06:47Z
```

This document is a dated implementation-status addendum. It does not replace
the historical ship log in `docs/IMPLEMENTATION_STATUS.md`.

## What is now on main

- deterministic A-G failure detection for all 30 registered source scenarios;
- 20 existing controller-risk contracts retained, preserving the 50-case
  scenario-status surface;
- explicit `OBSERVED`, `RISK_ARMED`, `NOT_OBSERVED`, `UNOBSERVABLE` semantics;
- deterministic derivatives calculations for VIX, IV, IV rank/crush, term
  structure, skew, PCR, max pain, futures OI state, basis, rollover, GEX,
  vanna/charm, GIFT gap, index gap and FII futures-short share;
- all 18 registered ORB variants assessed causally;
- strict large-gap rule `gap > 1.5 x prior ATR`;
- dealer-signed GEX only when dealer-position sign is supplied;
- raw `DerivativesSnapshot` and `RiskContextSnapshot` routed through the
  existing reducer into `Capability[]`;
- independent derivatives/risk refresh preserves the other valid capability
  family;
- outer runtime can no longer repaint a controller hard block into WATCH;
- legacy bar-only EventBatch idempotency shape preserved;
- recursive adaptive-engine proof fingerprint coverage;
- dynamic base-vs-PR CI regression comparison.

## Pre-merge verification

Latest pre-merge CI run:

```text
workflow: AFRE v4 CI
run: #18 / 34202290834
result: SUCCESS
```

Targeted adaptive suite:

```text
144 passed
4 skipped
0 failed
```

Full API differential gate:

```text
BASE main d5d7e8b1:
  5 failed, 887 passed, 4 skipped

PR candidate:
  5 failed, 899 passed, 4 skipped

new failure IDs introduced by PR: 0
result: PASS
```

Inherited baseline failures are unchanged:

1. `test_9c_033_real_indicator_payload_is_normalized_without_changing_default`
2. `test_9c_runtime_008_real_runtime_probes_pta_markers_without_probability_or_trading`
3. `test_9c_runtime_009_fmfm300_is_explanation_only_and_not_trade_authority`
4. `test_tv_v201_006_real_data_partition_invariant_and_coverage`
5. `test_research_stack_wrapper_powershell_parser_has_no_errors`

The first three are pre-existing 9C/PTA behavior issues; the fourth requires an
HSTRY fixture unavailable in Linux CI; the fifth invokes Windows PowerShell on
an Ubuntu runner. They must remain visible but are not AFRE regressions.

## Proof/fingerprint hardening

Before merge, `code_fingerprint()` was hardened from direct-directory hashing
to recursive hashing of decision-relevant adaptive source/config files:

```text
.py
.json
.toml
.yaml
.yml
```

Manifest keys use relative paths, so future nested decision modules and duplicate
filenames cannot silently escape or collide in proof binding.

Regression tests prove:

- nested decision-source changes change the fingerprint;
- unrelated `.txt` changes do not change it;
- the manifest includes AFRE v4 decision sources such as controller, runtime,
  derivatives, risk context, scenario detection and variants;
- changing the current fingerprint invalidates a previously signed review.

### Consequence

The merge is **not** evidence that an older proof remains valid.

```text
new adaptive source fingerprint
        -> prior reviewed fingerprint mismatch
        -> prior review cannot authorize current code
        -> fresh REAL_ATTESTED proof and explicit review required
```

Paper promotion remains intentionally fail-closed until that proof exists.

## Safety state after merge

The following remain architectural invariants:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
```

No broker credential path, broker order route, autonomous live execution, or
external-AI safety override was added.

`PAPER-CANDIDATE` still requires the exact current proof/authority state,
synchronized universe, current capabilities, no hard block and human approval.

## What AFRE v4 does NOT complete

AFRE v4 provides calculation contracts and same-reducer ingestion wiring. It
does not fabricate real external data.

Real providers still need to populate:

```text
DerivativesSnapshot
RiskContextSnapshot
```

from verified OpenAlgo/NSE/other approved sources with proper observation time,
receive time, freshness, completeness, expiry/session identity and provenance.
Missing facts remain unavailable/unobservable.

AFRE v4 also does not resolve the repository-wide duplicated decision-authority
problem. That is the next architecture milestone.

## Next engineering milestone

```text
Canonical Decision Spine / Brain Orchestration
```

Build it on a separate branch/PR. The goal is:

- authoritative engine-role registry;
- one canonical `DecisionContext`;
- one canonical `FinalDecision` / `PaperTradeGuidance`;
- Final Confluence / D6 as sole final-band authority;
- ORB/AFRE as strategy/scenario evidence, not a second product final;
- Twin/Kronos/Gemini/Grok as conflict/reviewer evidence only;
- Jarvis as read-only final presentation;
- real derivatives/risk providers feeding the same context;
- conflict/veto/PIT/freshness/determinism integration tests.

After that wiring is stable, run the gap-morning historical experiment, unseen
holdout, walk-forward proof, real paper observation, outcome feedback and
edge-decay monitoring.

See `docs/NEXT_BUILD_TARGET.md` for the current ordered build sequence.
