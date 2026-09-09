# Decision Spine Build Status — 2026-09-08

## Status

```text
M0 Stage-2 stabilization / integrity             GREEN / LOCKED
M1 Engine Authority Registry foundation          GREEN / SCOPE LOCKED
M2 Canonical DecisionContext                     GREEN / LOCKED
M3 Specialist brain migration                    NOT STARTED
M4 D6 repository-wide canonical consumer         NOT STARTED / D6 EXISTS
M5 Canonical FinalDecision                       NOT STARTED
M6 Jarvis read-only presentation                 NOT STARTED
M7 Contradiction / replay / safety attack matrix NOT STARTED
M8 Verified real providers                       NOT STARTED
M9 Historical / walk-forward validation          NOT STARTED
M10 Controlled paper validation                  NOT STARTED
M11 Operational hardening                        NOT STARTED
M12 Independent release gate                     NOT STARTED
```

Canonical status source:
`docs/CANONICAL_BUILD_STATUS.md`

M2 coding reference:
`docs/M2_AUDIT_VERDICT_CODING_REFERENCE_2026-09-08.md`

---

## M2 verified implementation

Verified source head:
`105561fc4908db6c18c32f9fd1a81ae5570f680f`

Workflow:
`M2 DecisionContext`

Run:
`34233061074`

Result:
**SUCCESS**

```text
compile affected M2 modules                    PASS
DecisionContext contract                       34 passed
Paper Guidance DecisionContext adapter         13 passed
M2 real-pipeline integration + D6 parity       10 passed
M0 Stage2 integrity regression                 15 passed
Paper Guidance v1.88 regression                29 passed
full apps/api/tests/test_api.py                556 passed
authority registry / sole-D6 / zero-execution PASS
```

## What M2 now does

```text
D1 safety / PIT
      ↓
D2 immutable closed-candle snapshot
      ↓
current D2-native Stage2 engines
      ↓
engine receipts
      +
explicit inactive / unavailable canonical inventory
      +
locked M0 9C / PTA / ORB / AFRE skipped inventory
      ↓
Stage2IntegrityReport
      ↓
if BLOCK -> WAIT / DO_NOTHING / no context / no D6
      ↓
Canonical DecisionContext
      ↓
context_hash + receipt provenance + compact audit
      ↓
existing D6 request unchanged
      ↓
FINAL_CONFLUENCE_ARBITER
```

### DecisionContext hardening

M2 now enforces:
- exact Stage2 membership for each evidence source;
- exact D2 snapshot identity;
- monotonic availability: context may preserve/downgrade, never upgrade Stage2 evidence;
- exact Stage2 source-mode provenance;
- `freshness == BLOCK` rejection;
- explicit reasons for non-PASS PIT/freshness/quarantine states;
- future evidence rejection;
- neutral-default substitution rejection;
- non-authoritative probability rejection;
- no proof/paper/trade/final-band authority inside context;
- immutable deterministic payloads/hashes;
- optional receipt `source_output_hash` provenance.

### New adapter

`apps/api/app/behavior/decision_spine/paper_guidance_decision_context_adapter.py`

The adapter performs deterministic validation/mapping only. It does **not** fetch data, read storage, rerun specialists, calculate indicators, execute ORB/AFRE, call AI, calculate probability, or arbitrate D6.

It builds O(1) receipt/Stage2 indexes and maps the current route into 22 canonical evidence fields. Missing brains remain explicit `UNAVAILABLE` or `SKIPPED` with reasons.

### Paper Guidance compatibility architecture

For low-risk migration and exact parity:

```text
paper_guidance_spine.py
    public compatibility facade

paper_guidance_spine_m2_impl.py
    M2 orchestration layer

paper_guidance_spine_legacy.py
    byte-preserved pre-M2 implementation
```

The public facade retains historical monkeypatch/fault-injection hooks so existing tests and consumers keep the same import surface.

### D6 parity

M2 deliberately leaves legacy D6 compatibility inputs unchanged. Direct integration comparison against the byte-preserved pre-M2 path verifies equality of:
- snapshot hash;
- guidance ID;
- final band;
- confidence cap;
- next action;
- arbiter summary;
- engine receipts.

Therefore M2 introduces canonical evidence truth and replayability without changing the current D6 decision.

### Determinism

Verified:

```text
same request
  -> same D2 snapshot hash
  -> same Stage2 integrity hash
  -> same DecisionContext hash
  -> same existing guidance result

changed legitimate closed candle
  -> changed D2 snapshot hash
  -> changed DecisionContext hash
```

Typed context-contract failures and Stage2 hard blocks stop before D6.

### Compact audit

Normal Paper Guidance output carries only a compact `risk_summary["decision_context"]` projection containing:
- adapter/context versions;
- context hash;
- D2 snapshot hash;
- Stage2 integrity hash;
- PIT/freshness/quarantine/data-quality status and reasons;
- counts of available/degraded/unavailable/skipped/error fields;
- hard safety flags.

The complete canonical world-state is not duplicated into the normal API response and is not exposed as a second product decision.

---

## M2 safety truth

Still enforced:

```text
research_only = true
trade_allowed = false
order_routing_enabled = false
live_trading_blocked = true
human_approval_required = true

missing != neutral
unknown != false
unavailable != safe
synthetic != real
```

M2 GREEN means the software architecture for canonical context is verified. It does **not** mean historical edge is proven, paper authority is granted, or the project is production-ready for live trading.

---

## Next eligible work — M3, not started

Recorded sequence:

```text
M3.1 price / candle / levels / indicators / MTF
M3.2 regime / session / index / sector / relative strength
M3.3 memory / historical analogs / 9C / PTA
M3.4 hypotheses / strategy candidates / ORB / AFRE
M3.5 derivatives / events / failure scenarios
M3.6 execution quality / behavior risk / portfolio/cooldown
M3.7 reviewer evidence: Kronos / Gemini / Grok / OpenAlgo / Twin
```

Legacy D6 neutral compatibility values remain intentionally untouched until the corresponding M3 specialist migration has causal evidence and replay parity.
