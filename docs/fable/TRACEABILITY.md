# Trade Vision Campaign Traceability

Last updated: 2026-09-07 (tip: v2.02-derivatives + repair wave, 939 passed; authority:
`docs/IMPLEMENTATION_STATUS.md`)

| Requirement | Design | Milestone | Implementation | Verification | Status |
|---|---|---|---|---|---|
| TV-P0-001 D1 safety gate | TV-ADR-002 | v1.87 | `paper_guidance_spine.py` | TV-V187-003/004/005 | verified |
| TV-P0-002 D2 strict freeze | TV-ADR-002 | v1.87 | `freeze_d2_closed_candle_snapshot` | TV-V187-008/013 | verified |
| TV-P0-003 deterministic hash | D2 canonical snapshot | v1.87 | SHA-256 + UUID5 | TV-V187-001/002 | verified |
| TV-P0-004 typed guidance | Pydantic contracts | v1.87 | `models.py` + typed route | TV-V187-009/010/011 | verified |
| TV-P0-005 low evidence cap | TV-ADR-003 | v1.87 | config + P0 builder | TV-V187-006/007 | verified |
| TV-P0-006 no execution | literal safety envelope | v1.87 | contract + import boundary | TV-V187-009/010/012 | verified |
| TV-P0-007 docs current | campaign artifacts + project docs | v1.87 | pointers/indexes/graph/docs | graph/docs audit | verified |
| TV-P1-001 one snapshot-bound engine order | Paper Guidance D3-D6 | v1.88 | `paper_guidance_spine.py` | TV-V188-001..008 | verified |
| TV-P1-002 persisted-only memory authority | D3b memory gate | v1.88 | `paper_guidance_spine.py` | TV-V188-009..012 | verified |
| TV-P1-003 sole arbiter and low-evidence cap | D6 final authority | v1.88 | final confluence bridge | TV-V188-013..017 | verified |
| TV-ORB-001 session-safe ORB strategies | ORB-0/1 | v1.89 | `orb/core.py` | ORB core tests | verified |
| TV-ORB-002 offline combination discovery | ORB-2 | v1.90 | `orb/discovery.py` | job/determinism tests | verified |
| TV-ORB-003 prove before promotion | ORB-3 | v1.91 | `orb/proof.py` | OOS/WF/consistency tests | verified |
| TV-ORB-004 primary Jarvis setup, subordinate authority | ORB-4/5 | v1.92 | `orb_guidance.py` + Jarvis panel | 12 guidance tests + browser | verified |
| TV-PAPER-001 explicit approval creates simulation record | Paper record | v1.93 | `simulated_paper_ledger.py` | 10 approval/idempotency tests | verified |
| TV-PAPER-002 explicit replay lifecycle | Lifecycle observation | v1.94 | `orb_paper_lifecycle.py` | TV-V194-009..021 | verified |
| TV-PAPER-003 completed-only reduce-only reliability | Feedback boundary | v1.94 | `orb_paper_feedback.py` | TV-V194-022..025 | verified |
| TV-PAPER-004 atomic fail-closed local persistence | Storage boundary | v1.94 | `atomic_json_store.py` | TV-V194-002..008/026/027 | verified |
| TV-PAPER-005 Jarvis lifecycle visibility | Operator UI | v1.94 | `App.tsx` + `styles.css` | TV-V194-029 + browser | verified |
| TV-SAFE-001 no live route throughout campaign | hard invariant | v1.88-v1.94 | contracts/import boundaries | TV-V194-028/030/032 + regression | verified |
| TV-OPS-001 hidden surfaces issue no periodic evidence requests | active-surface loader manifest | proposed v1.95 | pending | TV-V195-001..004/013 | planned |
| TV-OPS-002 global safety remains current | safety fast lane | proposed v1.95 | pending | TV-V195-008/014 | planned |
| TV-OPS-003 stale responses cannot overwrite current evidence | generation-token merge | proposed v1.95 | pending | TV-V195-005/006/015 | planned |
| TV-OPS-004 all existing panels remain reachable | loader ownership manifest | proposed v1.95 | pending | TV-V195-011/012/018 | planned |
| TV-OPS-005 UI refresh does not change trading authority | request-scheduling-only boundary | proposed v1.95 | pending | TV-V195-016/020 | planned |
| TV-ORB-005 indicator catalog 94 contracts | ontology + lag vote | v1.96 | `behavior/indicator_registry.py` + `indicator_lag_voting.py` | CAT-V196-001..009 | verified |
| TV-ORB-006 per-stock timing windows | HSTRY batch research | v1.97 | `orb/timing_research.py` + `orb/hstry_csv.py` | ORB-T197-001..010 | verified |
| TV-ORB-007 BEL proof + promotion | OOS/WF + playbook | v1.91/v1.99 | `orb/proof.py` + `scripts/prove_bel.py` | TV-V191-001..014 + BEL ELIGIBLE ab7b3163/a1c78a28 | verified |
| TV-ORB-008 opening classifier standalone | gap/CPR/zone | v2.01 | `orb/context.py` (not wired to core) | TV-V201-001..008 | verified |
| TV-ORB-009 derivatives dormant subsystem | OFF-profile mount | v2.02-derivatives | `orb/derivatives/` (15 modules) | 22/22 bundle gates | verified |
| TV-RPR-001/002 provider+batch | PARKED for G0 capture | `openalgo.py` (no rewrite yet) | captured-contract tests | parked |
| TV-RPR-003 error boundary | G3 | `openalgo.py` + `api.py` handler | OPENALGO-003/004/005 + non-JSON guard | verified |
| TV-RPR-004 metadata fail-closed | G4-logic | `openalgo.py`, `fixtures.py` | OPENALGO-006 (names pending G1) | verified |
| TV-RPR-005 PIT/identity | G5 | `contracts.py`, `reasoning.py`, `service.py`, `replay.py` | PIT-001..004 | verified |
| TV-RPR-006 replay | G6 | `integration.py`, `fixtures.py` | REPLAY-001/002 | verified |
| TV-RPR-007 health | G7 | `api.py` | health matrix | verified |
| TV-RPR-008 storage | G8 | `store.py` | STORE-001 | verified |
| TV-RPR-009 v1.73 wiring | G9 | PARKED for G0 | BRIDGE-001/002 | parked |
| TV-RPR-010 AFRE wiring | G10 | PARKED for G0 | AFRE-001..004 | parked |
| TV-RPR-011 provenance | G11-mech | `contracts.py`, `service.py` | provenance tests (re-verify post-G1) | verified |
| TV-RPR-012 walls/policy | G12 | `calculators.py`, `contracts.py`, `reasoning.py` | wall + policy tests | verified |
| TV-RPR-013 repair wave | G3/G4-logic/G5/G6/G7/G8 | provider/store/api/reasoning/integration/fixtures | 26 repair tests + 939 full | verified |
