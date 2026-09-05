# OpenAlgo Transport SLO Runbook

1. Confirm the report has at least five delivery attempts before interpreting availability or latency.
2. Inspect P95 latency, retry rate, availability, and backlog together.
3. Use the fault harness to confirm alert logic before changing thresholds.
4. Acknowledge incidents with an operator note; acknowledgement does not clear the alert.
5. Resolve the underlying transport condition and verify the report returns healthy.
