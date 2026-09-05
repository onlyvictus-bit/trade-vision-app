# OpenAlgo Transport Circuit Runbook

1. Confirm `order_routing_enabled=false` and `live_trading_blocked=true`.
2. Inspect `/api/v1/openalgo/transport/status` and recent transport traces.
3. Verify adapter health and service identity configuration.
4. Do not bypass the circuit. Correct the adapter/network fault and wait for cooldown.
5. Run one controlled health sample, then one operator-triggered due-worker batch.
6. Escalate repeated failures to dead-letter review.
