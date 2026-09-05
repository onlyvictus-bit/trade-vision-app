# External AI Credentials Runbook

Last reviewed: 2026-07-02

Purpose: preserve the current Gemini and Grok credential design for future builds without exposing any secret values.

## Security Boundary

Trade Vision supports:

- Gemini API key saving through the frontend/backend vault.
- xAI/Grok API key saving through the frontend/backend vault.
- Local Grok gateway settings through a local JSON config file.
- Manual external AI review by copying evidence packets and pasting responses back.

Trade Vision does not support:

- Grok browser username/password storage.
- Browser cookie capture.
- Browser session token capture.
- Hidden web API replay from logged-in browser state.
- Broker credential storage inside Trade Vision.

External AI can only review evidence. It cannot approve trades, override WAIT/no-trade, bypass risk gates, or route orders.

## Gemini Key Saving - Easy Frontend Path

1. Start the backend and frontend.
2. Open Trade Vision frontend.
3. Go to `Jarvis`.
4. Open tab `Ops & Audit Vault`.
5. Find panel `AI Credential Vault`.
6. Select `Gemini Slot` from 1 to 5.
7. Paste the Gemini API key.
8. Click `Save Gemini Slot`.
9. Click `Test Gemini Slot`.
10. Refresh the page and confirm `Gemini Slots` shows the configured count and active slot.

The plaintext key is not returned to the frontend after saving. The UI shows only masked status/fingerprint.

## Backend Vault Files

Vault unlock key file:

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app\data\secrets\tradevision_secret.key
```

Encrypted API credential vault:

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app\data\secrets\ai_credentials.enc
```

`ai_credentials.enc` is encrypted. Do not manually edit it. Save Gemini/Grok API keys through the UI/backend only.

The backend can also use environment variables:

```text
TRADEVISION_SECRET_KEY
TRADEVISION_SECRET_KEY_FILE
TRADEVISION_AI_CREDENTIAL_VAULT_PATH
```

Default behavior uses `tradevision_secret.key` from `data\secrets` when `TRADEVISION_SECRET_KEY` is not set.

## Grok Local Gateway Config

Editable local config path:

```text
D:\Projects\trading-platforms\stock-app\trade-vision-app\data\secrets\grok_gateway.local.json
```

Allowed keys:

```json
{
  "enabled": true,
  "gateway_url": "http://127.0.0.1:8899",
  "model": "grok/grok-4-fast",
  "health_timeout_ms": 1500,
  "ask_timeout_ms": 45000
}
```

This file is only for local gateway settings. Do not put username, password, cookies, sessions, tokens, API keys, or broker credentials in this file.

## Current Implemented Files

Backend:

```text
apps/api/app/behavior/ai_credentials_vault.py
apps/api/app/behavior/gemini_provider.py
apps/api/app/behavior/grok_provider.py
apps/api/app/behavior/grok_gateway_provider.py
apps/api/app/main.py
```

Frontend:

```text
apps/web/src/components/aiCredentialsPanel.tsx
apps/web/src/api/client.ts
apps/web/src/App.tsx
```

Tests:

```text
apps/api/tests/test_api.py
```

## API Endpoints

Credential vault:

```text
GET    /api/v1/ai/credentials/status
POST   /api/v1/ai/credentials/gemini
POST   /api/v1/ai/credentials/grok
DELETE /api/v1/ai/credentials/gemini/{slot}
DELETE /api/v1/ai/credentials/grok
POST   /api/v1/ai/credentials/test-gemini
POST   /api/v1/ai/credentials/test-grok
```

Grok local gateway:

```text
GET  /api/v1/jarvis/grok-gateway/status
POST /api/v1/jarvis/grok-gateway/connect
POST /api/v1/jarvis/grok-gateway/review/{symbol}
```

## Verification Already Run

Focused credential tests:

```text
D:\Projects\trading-platforms\stock-app\.venv\Scripts\python.exe -m pytest apps\api\tests\test_api.py -k "ai_credentials or gemini_credential" -q
```

Result:

```text
2 passed
```

Focused Grok gateway tests:

```text
D:\Projects\trading-platforms\stock-app\.venv\Scripts\python.exe -m pytest apps\api\tests\test_api.py -k "grok_gateway" -q
```

Last known result:

```text
5 passed
```

Frontend verification:

```text
cmd /c npm run typecheck
cmd /c npm run build
```

Last known result: passed.

## Operational Notes

- If `AI Credential Vault` shows locked, confirm `tradevision_secret.key` exists and restart backend.
- If `ai_credentials.enc` is missing, save a Gemini key from the UI; the backend creates it.
- If `ai_credentials.enc` exists but cannot open, do not edit it manually. Clear/recreate through backend flow.
- If Grok gateway times out, Jarvis keeps `TRADE_VISION_ONLY` and does not boost confidence.
- External AI responses are display/review only and must pass schema validation before they influence comparison panels.
