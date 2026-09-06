# Trade Vision AFRE v3 — executable release candidate

**Version:** `AFRE-3.0.0rc1`  
**Repository baseline:** `onlyvictus-bit/trade-vision-app`, commit `33184ea811e97173cdc920f563cdd728ceda9833`  
**Release scope:** executable autonomous analysis, historical simulation, and strictly human-approved local paper research. **Not production-certified, not live execution, and not a claim of profitable or failure-free trading.**

This is code, not a prompt pack. It contains a deterministic scenario controller, six registered setup templates, common fill/exit accounting, a durable event loop, authenticated FastAPI routes, chronological policy research, structural-label and statistical-model training code, a reversible repository installer, and executable tests. There is no runtime language-model dependency.

The original AFRE-2.0 proposal and explanation are retained under `specs/`. All 30 original failure records are preserved unchanged in `source_scenarios.json`. Their unverified thresholds and claimed mechanisms are source material, not automatically executed rules. The additional X01–X20 cases have an explicit implementation/limitation mapping.

## 1. Start here

You can run the package independently before changing your repository. Use an isolated Python environment; the code requires Python 3.11 or newer. The actual tested versions, test output, coverage, and limits are in `evidence/verification.json` and `evidence/TEST_RESULTS.txt`.

### Windows PowerShell: run the bundle's tests and demos

After extracting this ZIP, open PowerShell **in its top-level directory**, which contains `install_afre.py` and `overlay`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-afre.txt
$env:PYTHONPATH = (Resolve-Path .\overlay\apps\api).Path
python -m pytest .\overlay\apps\api\tests\afre -q
python -m app.orb.adaptive.cli demo --path fade --out .\output\fade
python -m app.orb.adaptive.cli demo --path reclaim --out .\output\reclaim
python -m app.orb.adaptive.cli demo --path fade-fails --out .\output\fade-fails
python -m app.orb.adaptive.cli demo --path gap-filled --out .\output\gap-filled
```

Each demo writes its exact synthetic input, policy, account assumptions, result, and JSONL/Markdown/HTML decision trace. Open `output/fade/trace.html` in a browser. A losing alternative and a no-entry day are intentional tests, not errors. These fixtures are not historical stock data and cannot earn paper permission.

On Linux/macOS, set `PYTHONPATH=overlay/apps/api` before the same Python commands. There is no installation-time download of market data or model weights.

### Install into the real repository

Stop your local application first. Keep your existing working changes committed or backed up. The installer refuses a changed baseline or conflicting local files; it never resets Git or pushes a commit.

```powershell
$repo = 'D:\Projects\trading-platforms\stock-app\trade-vision-app'
python .\install_afre.py --repo $repo
# Review the dry-run file list, then apply this explicit local change:
python .\install_afre.py --repo $repo --apply
Set-Location $repo
$env:PYTHONPATH = (Resolve-Path .\apps\api).Path
python .\scripts\verify_afre_host.py --full-backend
```

The installer adds `app/orb/adaptive`, tests, config examples and documentation; it appends narrow opt-in exports to `orb/core.py`, `orb/discovery.py`, `orb/proof.py`, `behavior/orb_guidance.py`, and mounts the opt-in router in `main.py`. **The profile defaults to `off`.** Legacy formulas, control results and BEL playbooks are not overwritten or silently relabeled. AFRE is a versioned migration path, not a second post-proof voting overlay.

**The full host verification command above was not run in the authoring environment.** The GitHub connector could read the repository, but direct clone/download DNS was unavailable. The bundle was tested using its real implementation and a synthetic Git fixture for the installer, not a complete host checkout. Do not skip that host verification step or interpret bundle tests as the original application's full regression.

### Roll back source changes safely

The install output names a `.afre-backups/<timestamp>` directory. From the extracted bundle, with the application stopped:

```powershell
python .\rollback_afre.py --repo $repo --backup "$repo\.afre-backups\<timestamp>"
python .\rollback_afre.py --repo $repo --backup "$repo\.afre-backups\<timestamp>" --apply
```

Rollback refuses to overwrite subsequent edits. It restores original source bytes and removes unchanged additions from that installation. It does **not** delete paper observations, undo a database transaction, remove backups, or reset Git. Back up the SQLite database separately.

## 2. The implemented observation loop

```text
New available bar / reference update / timer
  -> validate clock, identity, price basis and known-at time
  -> account for an already approved/filled paper plan FIRST
  -> validate shared D1 and the complete causal feature prefix
  -> update eight simultaneous market branches
  -> produce exact failure questions and supported forecast or UNESTIMATED
  -> generate up to six registered setup/action templates
  -> evaluate actual price envelope, structural stop, target room and costs
  -> challenge each candidate once; keep evidence lineage
  -> choose by frozen priority or supported action-value model
  -> apply exact policy proof, current safety and account/day permission
  -> persist checkpoint + decision + idempotent audit receipt atomically
  -> WAIT / WATCH / PAPER-CANDIDATE
  -> stop until new information or a real deadline arrives
```

A close back inside the opening range can invalidate an unapproved continuation. A **later independent rejection** can qualify a gap fade. A reclaim can refute the fade and qualify a separately registered continuation. Both alternatives can fail. A touched PDC remains touched; an original-gap fade cannot be resurrected. No trade is a legitimate result.

The public explanation is structured evidence: facts, supporting/contradicting observations, conditions, uncertainty and reasons. It is not hidden model chain-of-thought and not repeated conversational self-agreement.

## 3. Implemented setup templates

| Template | What triggers an investigation or candidate |
|---|---|
| `FIRST_BREAK` | First completed buffered gap-direction break; opt-in, not default. |
| `ACCEPTANCE` | Required consecutive completed outside closes, with registered confirmation settings. |
| `RETEST_HOLD` | Causal retest of a known OR boundary followed by a qualifying hold; own structural stop. |
| `GAP_FADE` | Previously observed gap-direction failure plus a later independent rejection, untouched PDC, and enough room for the frozen target. |
| `RECLAIM` | A failed acceptance episode followed by a new qualifying reclaim/acceptance sequence. |
| `PD_LEVEL_BREAK` | Registered previous-day level confirmation combined with a valid OR continuation. |

Default priority is `RECLAIM`, `RETEST_HOLD`, `ACCEPTANCE`, `GAP_FADE`. It is a **declared deterministic research policy**, not a learned optimal ranking. FIRST_BREAK and PD_LEVEL_BREAK are separately selectable. The entire priority/waiting/switching controller is hashed and must be evaluated, not just its individual leaves.

## 4. Fixed policy boundary

The current uploaded specification is used over the older August proposal: gap days only; no actual entry later than **10:15 IST**; fixed initial stop; fixed full **1R or 2R** target calculated once from actual simulated fill; no re-entry or exit rewriting; one filled entry account/session-wide. This initial release also enforces **one accepted approval attempt** per session, even if unfilled. Observing or rejecting a hypothesis does not consume that attempt.

Native 3m features are supported with verified 1m execution for a 15:10 flat. An explicitly distinct native-3m execution policy uses 15:09 flat. A 15:10 price is not fabricated from a candle straddling that time. Five-minute bars cannot manufacture native 3m evidence.

Price-risk and cost thresholds in the example configs are **unproven experimental choices**, not market constants or recommendations for your capital.

## 5. Forecasting: implemented code versus absent evidence

The runtime emits six exact forecast-question contracts. Two currently have end-to-end structural label generation and conditional-frequency training: **return inside OR within the specified feature-bar horizon**, and **PDC touch within that horizon**. Training/calibration/test dates are chronological; repeated same-date/context observations are not treated as independent market dates; known-at maturity and out-of-support checks are enforced.

The other questions describe retest fill by expiry, missing all eligible entries through waiting, entry-economics invalidation, and stop before target for an exact plan. Their records expose `UNESTIMATED`; this release does **not** ship calibrated numerical estimators for those four questions. Complete action-policy replay and an empirical action-value training path are supplied separately.

**No trained real-market model, signed paper permission, or claimed calibration result is included.** Consequently, the default numerical probabilities are `null`, not invented 50% guesses. The statistical code and its tests are real; empirical validation still requires real, correctly timestamped observations.

## 6. Run in shadow mode inside Trade Vision

Bind the existing repository's D1 source and effective settings **before conducting a new study**, so research and paper use the same data checks:

```powershell
python -m app.orb.adaptive.cli bind-host-d1 --policy configs/afre/policy.example.json --out data/afre/policy.host-bound.json
python -m app.orb.adaptive.cli generate-local-secrets --out D:\TradeVisionSecrets\afre
$env:TRADEVISION_AFRE_PROFILE = 'shadow'
$env:TRADEVISION_AFRE_POLICY = "$repo\data\afre\policy.host-bound.json"
$env:TRADEVISION_AFRE_LIMITS = "$repo\configs\afre\account.example.json"
$env:TRADEVISION_AFRE_DB = "$repo\data\afre\runtime.sqlite3"
$env:TRADEVISION_AFRE_TOKEN = (Get-Content D:\TradeVisionSecrets\afre\api-token.txt -Raw).Trim()
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep secrets out of the repository. On Windows, restrict the directory's ACL to the intended local account; Python's POSIX-style chmod is not a complete Windows ACL policy. Shadow does not automatically approve anything. Your existing verified loader must send actual available bars and reference metadata through the authenticated event route; no live feed connector is fabricated.

Inspect the API status:

```powershell
$headers = @{ Authorization = "Bearer $env:TRADEVISION_AFRE_TOKEN" }
Invoke-RestMethod -Headers $headers -Uri http://127.0.0.1:8000/api/v1/orb/adaptive/status
```

The lifespan timer handles genuine deadlines even without another candle. It does not poll a broker, invent prices or repeatedly re-score identical evidence.

## 7. Before enabling paper eligibility

Read `overlay/docs/afre/POLICY_AND_PROOF.md` (installed as `docs/afre/POLICY_AND_PROOF.md`). Replay real complete sessions, preserve the trial register, select only on development dates, and evaluate the frozen controller on the final holdout. Existing BEL evidence does not prove this controller.

`exclusive-paper` requires a current locally signed review for the exact code, controller/models, D1 binding, account budget and universe. There is no API promotion bypass. It also requires explicit confirmation that **no other process or paper ledger can use this account**, and refuses today's legacy paper activity until reconciled. Old mutating HTTP routes are locked in that profile; old reads remain available. This is deliberately restrictive during migration. It is not protection against an independently running application or manual edits by the trusted machine owner.

## 8. What is not established by this delivery

- Full original-repository regression, old/new UI integration, real-time provider integration, Windows execution and a real BEL rerun remain unverified here.
- All 50 named cases have contracts/coverage status, not 50 calibrated predictors. News, VIX, OI, bands, surveillance, dealer positioning, verified market breadth and tradeable depth are not derived from stock candles.
- This is a single-machine SQLite research service, not a distributed account/broker platform. External feed reconciliation, access hardening beyond the local token, storage capacity, incident recovery and deployment review remain operator responsibilities.
- The new path corrects its own simulator and selection semantics. The old path and its previously audited deficiencies remain preserved as legacy; adding AFRE does not silently repair or re-prove old results.
- No engine can certify every future market path. Unfamiliar states, incomplete observations and absent model support are explicit unknowns, not forced trades.

The release candidate is useful now for executable scenario analysis, repeatable testing and controlled research. Production readiness requires the remaining host/data/operational gates to pass, not a stronger label on the ZIP.
