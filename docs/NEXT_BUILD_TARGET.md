# Next Build Target

Last reviewed: 2026-09-08

> **Canonical status source:** `docs/CANONICAL_BUILD_STATUS.md`
>
> Do not advance milestone state in this file independently. Every coding/audit session starts from the canonical status document.

## Current truth

**M2 — Canonical DecisionContext: GREEN / LOCKED**

Verified source head:
`105561fc4908db6c18c32f9fd1a81ae5570f680f`

Verification workflow:
`M2 DecisionContext` run `34233061074` — **SUCCESS**

```text
DecisionContext contract                    34 passed
Paper Guidance DecisionContext adapter      13 passed
M2 real-pipeline integration + D6 parity    10 passed
M0 Stage2 integrity regression              15 passed
Paper Guidance v1.88 regression             29 passed
full apps/api/tests/test_api.py             556 passed
authority / sole-D6 / zero-execution        PASS
```

M2 now constructs a deterministic D2-causal DecisionContext inside the real Paper Guidance route before the unchanged D6 request. Missing specialists remain explicit `UNAVAILABLE/SKIPPED`; no neutral substitution, paper authority, trade authority or parallel final decision was introduced.

## Next eligible milestone

**M3 — Brain migration**

State: **NOT STARTED**

Do not begin M3 in the M2 lock/docs patch. The next coding session should start by re-reading `docs/CANONICAL_BUILD_STATUS.md`, verifying the branch/head, and opening M3 deliberately.

Recorded M3 order:

```text
M3.1 price / candle / levels / indicators / MTF
M3.2 regime / session / index / sector / relative strength
M3.3 memory / historical analogs / 9C / PTA
M3.4 hypotheses / strategy candidates / ORB / AFRE
M3.5 derivatives / events / failure scenarios
M3.6 execution quality / behavior risk / portfolio/cooldown
M3.7 reviewer evidence: Kronos / Gemini / Grok / OpenAlgo / Twin
```

For every migrated family:
- use the same D2-causal DecisionContext identity;
- emit explicit availability/provenance;
- remove only the matching legacy placeholder after replay parity;
- add contradiction/adversarial tests;
- never create another public final decision;
- preserve D6 as sole final-band authority.

## Still intentionally deferred

Legacy D6 compatibility placeholders remain for M3 migration:

```python
relative_strength_score = 0.5
indicator_signal_score  = 0.0
external_ai_score       = 0.0
weak_sector             = False
```

Real canonical freshness/quarantine assessors are also not fabricated; M2 reports them as `UNKNOWN` with reasons until verified providers/assessors are wired.

## Core rules

> **One milestone -> implement -> test -> audit -> commit -> GREEN -> lock.**

> **Many brains may disagree internally. Only one decision may leave the brain.**
