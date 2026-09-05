# OpenAlgo Adapter Health Runbook

1. Verify the isolated adapter process is reachable.
2. Verify HMAC service identity configuration without exposing the secret.
3. Inspect timestamp skew, payload hash, and signature failures.
4. Keep delivery in WAIT while health is unavailable.
5. Record a fresh health sample after correction.
