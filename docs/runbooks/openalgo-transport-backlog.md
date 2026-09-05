# OpenAlgo Transport Backlog Runbook

1. Inspect pending, retry-wait, dead-letter, and cancelled counts separately.
2. Confirm the adapter is healthy and the circuit is closed.
3. Run bounded due-worker batches; do not increase concurrency beyond configured limits.
4. Cancel expired research packages and review repeated failures.
5. Keep live trading blocked throughout recovery.
