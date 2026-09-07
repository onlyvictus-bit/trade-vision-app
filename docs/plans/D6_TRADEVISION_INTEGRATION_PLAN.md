# D6 TradeVision Reference — Integration Plan

> **Status:** reference plan (evidence-backed, 2026-09-07). No repo behavior changed by this file.
> **Source:** `C:\Users\sakth\Downloads\tradevision_d6` (38 files; sandbox links unreachable).
> **Headline constraint:** our repo already mints PAPER-CANDIDATE in **three** places
> (spine arbiter, ORB guidance, AFRE runtime). Incoming `D6Engine` would be a fourth.
> Integration is **vendor-as-package + shadow adapter**, never overwrite, never direct swap.

## 1. What the bundle is (inventory)

- `tradevision-d6 0.1.0`, stdlib-only runtime (`requires-python>=3.11`, `dependencies=[]`).
- 8 src modules / 7 test files / 4 tools; claims 230 passed, 99.66% lib coverage, 15,533 synthetic risk comparisons, zero violations.

| File | Role |
|---|---|
| `src/tradevision_d6/models.py` | Frozen contracts: `Request/Snapshot/Portfolio/Policy/TradePlan/ValidationProof/RiskVector/Decision`; 5 risks (event, trap, data_uncertainty, liquidity, execution); 8 `REQUIRED_CHECKS` |
| `src/tradevision_d6/engine.py` | Pure kernel: `D6Engine.evaluate()` — separate LONG/SHORT scores, evidence-only preferred side (no fallback), monotone risk (`quality*∏(1-r)`), permission = quality iff all gates else 0 |
| `src/tradevision_d6/proofs.py` | HMAC proof auth + downward-closed risk envelope (`current ≤ signed max`); proves key possession, NOT statistical truth |
| `src/tradevision_d6/codec.py` | Canonical JSON, fingerprinting, strict boundary (1MB cap, dup/unknown-field reject, no float coercion) |
| `src/tradevision_d6/service.py` | Fail-closed boundary: trusted clock (5s lag), 7 evaluations (base + 5 single-risk + joint) with nonincreasing assertion, audit-before-return, demo-issuer rejection |
| `src/tradevision_d6/audit.py` | SQLite evaluation journal (idempotent replay, conflict rejection). NOT an order ledger |
| `src/tradevision_d6/demo.py` | Synthetic demo only (`SYNTHETIC-DEMO-DO-NOT-TRUST`); must never enter real validation |
| `tools/` | `property_audit` (seeded+exhaustive invariants), `benchmark`, `repo_inventory` (read-only `git ls-files` scan) |
| `docs/` | `TEST_REPORT.md` (honest limits) · `INTEGRATION_HANDOFF.md` (shadow-first spec) · `REVIEW_AND_ROADMAP.md` (P0/P1 targets — unverified, not confirmed defects) |

## 2. The 5-line D6 contract (do not weaken)

1. `survival=∏(1-r)`, `permission=quality iff all gates pass else 0` — a deterministic penalty, NOT a probability.
2. Preferred hypothesis from directional evidence ONLY; blocked LONG stays WAIT, never falls back to SHORT.
3. Sizing cannot rescue rejections (size independent of the 5 risks).
4. Risk envelope is downward-closed (`current ≤ signed max`); runtime risk excluded from HMAC binding.
5. Missing required source ⇒ hard WAIT; missing optional ⇒ contributes 0 without shrinking the denominator.

## 3. Collision map vs our HEAD (repair branch, AFRE-3.1 migrated)

| Risk | Fact |
|---|---|
| Triple authority today | `final_confluence_arbiter.py:26` (reduce-only bands) → spine `:264` downgrades to WATCH; `orb_guidance.py:158-164` promotes same output to ENTER_PAPER; `adaptive/runtime.py:248` mints PAPER-CANDIDATE independently |
| Vocabulary clash | Hyphen `PAPER-CANDIDATE` (arbiter/AFRE/D6) vs underscore `PAPER_CANDIDATE` (ticket) vs `ENTER_PAPER` (spine band); `TradePlan` ×3 (D6 setup-grade vs `tradeplan` execution contract vs `PaperGuidanceEntryPlan`); `permission` float (D6) vs permission matrix (host) |
| Proof stores disjoint | D6 HMAC binding+envelope vs host `snapshot_hash` + ORB `proof_hash` + ticket/ledger JSON bindings — never conflate |
| Hash lineage | D6 Decimal-`f` canonical + float-reject vs host `json.dumps(sort_keys)` + Pydantic dumps — keep both, bridge at boundary |
| Verdict | Vendor as NEW `tradevision_d6` package + thin shadow adapter; never overwrite `app/models.py`, `behavior/*`, `orb/tradeplan/*`, `orb/adaptive/*` |

## 4. Phased coding plan

```text
Q0  QUARANTINE (no repo touch): run 230 bundle tests with host venv. Gate: green.
M1  VENDOR-ADD (zero behavior change): src/* → apps/api/tradevision_d6/,
    tests/* → apps/api/tests/d6/, 3 docs → docs/d6/. Nothing imports them yet.
    Verify: vendored tests pass in repo; full suite green.
M2  SHADOW ADAPTER (the real work, separate approval): read-only comparator that
    feeds live spine evidence into D6Engine, logs old-vs-D6 divergence (input hashes,
    evidence, side, cause), D6 places NO orders, changes NO bands. Requires FIRST:
    raw-contribution mapping per producer (NEVER max(old,0) split — recover independent
    raws; risk never evidence for opposite side; unavailable ⇒ WAIT/WATCH).
M3  HOST TESTS + 6 acceptance gates (INTEGRATION_HANDOFF): baseline suite, adapter
    risk-increase tests through every endpoint, HTF/PIT audit, chronological validation,
    allocator + idempotency, observability/kill-switch. Then file-by-file ledger +
    explicit shadow→paper decision. Live trading is a separate release, never this task.
Rollback: M1 = delete vendored dirs. M2 = flag off (adapter dormant by default).
```

## 5. Explicitly NOT in this task

Overwriting host authority files; renaming bands; unifying hashes; validation producer/backtests; account allocator/exit engine; broker path; touching `main`; demo key anywhere near real validation; credentials in repo; weakening any test to fit.

## 6. Build record 2026-09-07 (Q0+M1 executed, uncommitted)

- Q0 quarantine: bundle 230/230 with host venv (matches author claim).
- M1 vendor-add (zero behavior change, nothing imports it yet): `src/*` (8) →
  `apps/api/tradevision_d6/`; `tests/*` (7) → `apps/api/tests/d6/`;
  `tools/{__init__,property_audit,repo_inventory}.py` → `apps/api/tools/`
  (`benchmark.py` intentionally not vendored — standalone CLI, runnable from bundle
  dir; no `tools` name collision in repo); 3 docs → `docs/d6/`.
- M1 verify: vendored 230/230 in repo.
- NEXT (separate approval): M2 shadow adapter — read-only comparator + mandatory
  raw-contribution mapping per producer (never `max(old,0)` split) before any wiring.
