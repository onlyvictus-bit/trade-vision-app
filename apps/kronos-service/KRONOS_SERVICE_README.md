# Kronos Service README

> **Filename:** `KRONOS_SERVICE_README.md` — isolated Kronos inference service (Trade Vision monorepo).  
> **Model cards:** `models/*/KRONOS_*_README.md`.

---

This folder contains the `v0.46-KR` isolated Kronos service boundary.

Current status: selectable real research-only inference:

- `NeoQuasar/Kronos-mini` + `NeoQuasar/Kronos-Tokenizer-2k`
- `NeoQuasar/Kronos-base` + `NeoQuasar/Kronos-Tokenizer-base`

## Purpose

- Keep model inference outside the main `apps/api` process.
- Run the real upstream model without adding heavy ML dependencies to `apps/api`.
- Let the main API fall back to deterministic mock output when this service is absent, slow, or unhealthy.
- Preserve the rule that Kronos is a forecast prior, never an execution authority.

## Safety Rules

- `apps/api` must not import PyTorch, Transformers, qlib, or Kronos.
- This service must not contain broker credentials.
- This service must not expose order-routing endpoints.
- Every forecast response must keep:
  - `research_only=true`
  - `trade_allowed=false`
  - `order_routing_enabled=false`
  - `live_trading_blocked=true`
  - `kronos_cannot_execute_orders=true`
  - `kronos_cannot_override_no_trade=true`
  - `kronos_cannot_override_risk=true`

## Run Locally

The dedicated Python 3.11 environment is:

```powershell
apps\kronos-service\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

Then start the main API with:

```powershell
$env:TRADEVISION_KRONOS_SERVICE_URL="http://127.0.0.1:8010"
$env:TRADEVISION_STATE_DB="C:\tmp\tradevision_runtime_kronos_v046.db"
D:\Projects\trading-platforms\stock-app\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Endpoints

- `GET /health`
- `POST /model/load?model_name=Kronos-mini`
- `POST /model/load?model_name=Kronos-base`
- `POST /forecast`

## Installed Artifacts

- Upstream source: `external/kronos`
- Model: `apps/kronos-service/models/Kronos-mini`
- Tokenizer: `apps/kronos-service/models/Kronos-Tokenizer-2k`
- Challenger model: `apps/kronos-service/models/Kronos-base`
- Challenger tokenizer: `apps/kronos-service/models/Kronos-Tokenizer-base`
- Runtime: `apps/kronos-service/kronos_runtime.py`

Model binaries and the virtual environment are ignored by Git and must be
installed on each inference host.
