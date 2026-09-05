from __future__ import annotations

import math
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from .. import storage
from ..models import (
    TransportAlert,
    TransportFaultHarnessReport,
    TransportFaultHarnessRequest,
    TransportFaultScenarioResult,
    TransportHealthSample,
    TransportIncident,
    TransportIncidentAction,
    TransportResilienceReport,
    TransportSloObjective,
    now_iso,
)
from .openalgo_transport import transport_status


RESILIENCE_VERSION = "openalgo-transport-resilience.v0.56"
HARNESS_VERSION = "openalgo-transport-fault-harness.v0.56"
MINIMUM_SLO_SAMPLES = 5
AVAILABILITY_TARGET_PCT = 99.0
P95_LATENCY_TARGET_MS = 1200.0
MAX_RETRY_RATE_PCT = 10.0
MAX_BACKLOG = 20


def record_health_sample() -> TransportHealthSample:
    started = perf_counter()
    status = transport_status(check_health=True)
    latency_ms = round((perf_counter() - started) * 1000, 3) if status.health_checked else None
    sample = TransportHealthSample(
        sample_id=str(uuid4()),
        sampled_at=now_iso(),
        configured=status.configured,
        authenticated=status.service_auth_configured,
        health_ok=status.health_ok,
        circuit_state=status.circuit_state,
        latency_ms=latency_ms,
        pending_count=status.pending_count,
        retry_wait_count=status.retry_wait_count,
        dead_letter_count=status.dead_letter_count,
        order_routing_enabled=False,
        live_trading_blocked=True,
    )
    storage.save_transport_health_sample(sample)
    return sample


def build_resilience_report(*, evidence_window: int = 100, record_health: bool = False) -> TransportResilienceReport:
    if record_health:
        record_health_sample()
    traces = storage.list_executor_transport_traces(limit=evidence_window * 4)
    health = storage.list_transport_health_samples(limit=evidence_window)
    counts = storage.executor_transport_counts()
    started = [trace for trace in traces if trace.event_type == "delivery_started"]
    successes = [trace for trace in traces if trace.event_type == "acknowledged"]
    failures = [
        trace
        for trace in traces
        if trace.event_type in {"retry_scheduled", "dead_lettered", "manual_review", "circuit_blocked"}
    ]
    retries = [trace for trace in traces if trace.event_type == "retry_scheduled"]
    latencies = [trace.latency_ms for trace in successes if trace.latency_ms is not None]
    attempts = len(started)
    availability = (len(successes) / attempts * 100.0) if attempts else 0.0
    retry_rate = (len(retries) / attempts * 100.0) if attempts else 0.0
    p95 = _percentile(latencies, 0.95)
    backlog = counts["pending"] + counts["delivering"] + counts["retry_wait"]
    latest_health = health[0] if health else None
    objectives, alerts, overall = evaluate_transport_metrics(
        attempts=attempts,
        successes=len(successes),
        failures=len(failures),
        availability_pct=availability,
        p95_latency_ms=p95,
        retry_rate_pct=retry_rate,
        backlog_count=backlog,
        dead_letter_count=counts["dead_letter"],
        circuit_state=latest_health.circuit_state if latest_health else "closed",
        health_ok=latest_health.health_ok if latest_health else None,
    )
    evidence_times = [sample.sampled_at for sample in health]
    evidence_times.extend(trace.event_time for trace in traces)
    incident = _reconcile_incident(
        alerts,
        latest_evidence_at=max(evidence_times) if evidence_times else None,
    )
    return TransportResilienceReport(
        resilience_version=RESILIENCE_VERSION,
        generated_at=now_iso(),
        evidence_window=evidence_window,
        health_samples=len(health),
        delivery_attempts=attempts,
        successful_deliveries=len(successes),
        failed_deliveries=len(failures),
        availability_pct=round(availability, 4),
        p95_delivery_latency_ms=round(p95, 3),
        retry_rate_pct=round(retry_rate, 4),
        backlog_count=backlog,
        dead_letter_count=counts["dead_letter"],
        objectives=objectives,
        alerts=alerts,
        incident=incident,
        overall_status=overall,
    )


def evaluate_transport_metrics(
    *,
    attempts: int,
    successes: int,
    failures: int,
    availability_pct: float,
    p95_latency_ms: float,
    retry_rate_pct: float,
    backlog_count: int,
    dead_letter_count: int,
    circuit_state: str,
    health_ok: bool | None,
) -> tuple[list[TransportSloObjective], list[TransportAlert], str]:
    enough = attempts >= MINIMUM_SLO_SAMPLES
    objectives = [
        _objective(
            "availability",
            "Delivery availability",
            AVAILABILITY_TARGET_PCT,
            availability_pct,
            "%",
            enough,
            availability_pct >= AVAILABILITY_TARGET_PCT,
            attempts,
        ),
        _objective(
            "latency",
            "P95 delivery latency",
            P95_LATENCY_TARGET_MS,
            p95_latency_ms,
            "ms",
            enough,
            p95_latency_ms <= P95_LATENCY_TARGET_MS,
            attempts,
            lower_is_better=True,
        ),
        _objective(
            "retry_rate",
            "Retry rate",
            MAX_RETRY_RATE_PCT,
            retry_rate_pct,
            "%",
            enough,
            retry_rate_pct <= MAX_RETRY_RATE_PCT,
            attempts,
            lower_is_better=True,
        ),
        TransportSloObjective(
            objective_id="backlog",
            name="Delivery backlog",
            target=float(MAX_BACKLOG),
            observed=float(backlog_count),
            unit="records",
            status="pass" if backlog_count <= MAX_BACKLOG else "fail",
            sample_count=attempts,
            minimum_sample_count=0,
            blocks_promotion=backlog_count > MAX_BACKLOG,
            reason=f"Backlog {backlog_count}; maximum {MAX_BACKLOG}.",
        ),
    ]
    alerts: list[TransportAlert] = []
    if circuit_state == "open":
        alerts.append(_alert("TRANSPORT_CIRCUIT_OPEN", "critical", "Transport circuit breaker is open.", "runbooks/openalgo-transport-circuit.md"))
    if dead_letter_count > 0:
        alerts.append(_alert("TRANSPORT_DEAD_LETTER", "critical", f"{dead_letter_count} delivery records require dead-letter review.", "runbooks/openalgo-transport-dead-letter.md"))
    if health_ok is False:
        alerts.append(_alert("ADAPTER_HEALTH_FAILED", "warning", "Authenticated adapter health check failed.", "runbooks/openalgo-adapter-health.md"))
    if backlog_count > MAX_BACKLOG:
        alerts.append(_alert("TRANSPORT_BACKLOG_HIGH", "warning", f"Backlog {backlog_count} exceeds {MAX_BACKLOG}.", "runbooks/openalgo-transport-backlog.md"))
    if enough and availability_pct < AVAILABILITY_TARGET_PCT:
        alerts.append(_alert("TRANSPORT_AVAILABILITY_SLO", "warning", f"Availability {availability_pct:.2f}% is below {AVAILABILITY_TARGET_PCT:.2f}%.", "runbooks/openalgo-transport-slo.md"))
    if enough and p95_latency_ms > P95_LATENCY_TARGET_MS:
        alerts.append(_alert("TRANSPORT_LATENCY_SLO", "warning", f"P95 latency {p95_latency_ms:.1f} ms exceeds {P95_LATENCY_TARGET_MS:.1f} ms.", "runbooks/openalgo-transport-slo.md"))
    if enough and retry_rate_pct > MAX_RETRY_RATE_PCT:
        alerts.append(_alert("TRANSPORT_RETRY_RATE_SLO", "warning", f"Retry rate {retry_rate_pct:.2f}% exceeds {MAX_RETRY_RATE_PCT:.2f}%.", "runbooks/openalgo-transport-slo.md"))
    if any(alert.severity == "critical" for alert in alerts):
        overall = "critical"
    elif alerts:
        overall = "degraded"
    elif not enough:
        overall = "low_evidence"
    else:
        overall = "healthy"
    return objectives, alerts, overall


def acknowledge_incident(incident_id: str, action: TransportIncidentAction) -> TransportIncident:
    incident = storage.load_active_transport_incident()
    if incident is None or incident.incident_id != incident_id:
        raise KeyError(incident_id)
    if incident.status == "resolved":
        raise ValueError("Resolved incident cannot be acknowledged.")
    updated = incident.model_copy(
        update={
            "status": "acknowledged",
            "updated_at": now_iso(),
            "acknowledged_by": action.actor_id,
            "acknowledged_at": now_iso(),
            "resolution_note": action.note,
        }
    )
    storage.save_transport_incident(updated)
    return updated


def run_fault_harness(request: TransportFaultHarnessRequest) -> TransportFaultHarnessReport:
    scenarios = [
        ("healthy", "healthy", None, 100.0, 40.0, 0.0, 0, 0, "closed", True),
        ("latency_breach", "degraded", "TRANSPORT_LATENCY_SLO", 100.0, 1800.0, 0.0, 0, 0, "closed", True),
        ("availability_breach", "degraded", "TRANSPORT_AVAILABILITY_SLO", 90.0, 40.0, 10.0, 0, 0, "closed", True),
        ("backlog_breach", "degraded", "TRANSPORT_BACKLOG_HIGH", 100.0, 40.0, 0.0, 25, 0, "closed", True),
        ("dead_letter", "critical", "TRANSPORT_DEAD_LETTER", 99.0, 40.0, 1.0, 0, 1, "closed", True),
        ("circuit_open", "critical", "TRANSPORT_CIRCUIT_OPEN", 99.0, 40.0, 1.0, 0, 0, "open", False),
    ]
    results: list[TransportFaultScenarioResult] = []
    for scenario, expected, code, availability, latency, retry_rate, backlog, dead, circuit, health in scenarios:
        _, alerts, observed = evaluate_transport_metrics(
            attempts=request.sample_count,
            successes=round(request.sample_count * availability / 100),
            failures=request.sample_count - round(request.sample_count * availability / 100),
            availability_pct=availability,
            p95_latency_ms=latency,
            retry_rate_pct=retry_rate,
            backlog_count=backlog,
            dead_letter_count=dead,
            circuit_state=circuit,
            health_ok=health,
        )
        codes = [alert.code for alert in alerts]
        results.append(
            TransportFaultScenarioResult(
                scenario=scenario,  # type: ignore[arg-type]
                expected_status=expected,  # type: ignore[arg-type]
                observed_status=observed,  # type: ignore[arg-type]
                expected_alert_code=code,
                observed_alert_codes=codes,
                passed=observed == expected and (code is None or code in codes),
            )
        )
    return TransportFaultHarnessReport(
        harness_version=HARNESS_VERSION,
        generated_at=now_iso(),
        sample_count=request.sample_count,
        deterministic=True,
        passed_count=sum(item.passed for item in results),
        scenario_count=len(results),
        all_passed=all(item.passed for item in results),
        scenarios=results,
    )


def _objective(
    objective_id: str,
    name: str,
    target: float,
    observed: float,
    unit: str,
    enough: bool,
    passed: bool,
    samples: int,
    *,
    lower_is_better: bool = False,
) -> TransportSloObjective:
    status = "pass" if enough and passed else "fail" if enough else "low_evidence"
    comparison = "maximum" if lower_is_better else "minimum"
    return TransportSloObjective(
        objective_id=objective_id,
        name=name,
        target=target,
        observed=round(observed, 4),
        unit=unit,
        status=status,
        sample_count=samples,
        minimum_sample_count=MINIMUM_SLO_SAMPLES,
        blocks_promotion=status == "fail",
        reason=f"Observed {observed:.3f} {unit}; {comparison} target {target:.3f} {unit}; samples {samples}/{MINIMUM_SLO_SAMPLES}.",
    )


def _alert(code: str, severity: str, message: str, runbook: str) -> TransportAlert:
    return TransportAlert(
        alert_id=f"{code.lower()}-{datetime.now(timezone.utc).date().isoformat()}",
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
        active=True,
        runbook=runbook,
    )


def _reconcile_incident(
    alerts: list[TransportAlert],
    *,
    latest_evidence_at: str | None = None,
) -> TransportIncident | None:
    active_alerts = [alert for alert in alerts if alert.severity in {"warning", "critical"}]
    existing = storage.load_active_transport_incident()
    if not active_alerts:
        if existing:
            resolved = existing.model_copy(
                update={
                    "status": "resolved",
                    "updated_at": now_iso(),
                    "resolution_note": "All transport resilience alerts cleared.",
                }
            )
            storage.save_transport_incident(resolved)
        return None
    severity = "critical" if any(alert.severity == "critical" for alert in active_alerts) else "warning"
    codes = sorted(alert.code for alert in active_alerts)
    if existing:
        reopened = (
            existing.status == "acknowledged"
            and latest_evidence_at is not None
            and existing.acknowledged_at is not None
            and latest_evidence_at > existing.acknowledged_at
        )
        incident = existing.model_copy(
            update={
                "updated_at": now_iso(),
                "status": "open" if reopened else existing.status,
                "severity": severity,
                "title": f"OpenAlgo transport {severity} incident",
                "alert_codes": codes,
                "acknowledged_by": None if reopened else existing.acknowledged_by,
                "acknowledged_at": None if reopened else existing.acknowledged_at,
                "resolution_note": "Reopened by new resilience evidence." if reopened else existing.resolution_note,
            }
        )
    else:
        incident = TransportIncident(
            incident_id=str(uuid4()),
            opened_at=now_iso(),
            updated_at=now_iso(),
            status="open",
            severity=severity,
            title=f"OpenAlgo transport {severity} incident",
            alert_codes=codes,
        )
    storage.save_transport_incident(incident)
    return incident


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return float(ordered[index])
