# OpenAlgo Transport Dead-Letter Runbook

1. Confirm the record contains no broker credentials and created no order.
2. Review its trace chain, package hash, last error, and adapter health.
3. Cancel stale or invalid research intent packages.
4. Retry only after an operator verifies the external fault is corrected.
5. Never reinterpret dead-letter recovery as trade approval.
