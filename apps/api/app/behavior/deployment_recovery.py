from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from threading import RLock
from pathlib import Path
from uuid import uuid4

from .. import storage
from ..models import (
    DatabaseBackupArtifact,
    DatabaseRestoreDrillReport,
    DeploymentConfigurationFingerprint,
    DeploymentReadinessCheck,
    DeploymentReadinessReport,
    DeploymentSmokeReport,
    ExecutorTransportStatus,
    TransportSecurityPosture,
    now_iso,
)
from ..state import SYSTEM_MODE
from .openalgo_transport import _allowed_adapter_hosts, transport_status
from .transport_security import build_security_posture


FINGERPRINT_VERSION = "tradevision-deployment-config.v0.58"
BACKUP_VERSION = "tradevision-sqlite-backup.v0.58"
DRILL_VERSION = "tradevision-restore-drill.v0.58"
READINESS_VERSION = "tradevision-deployment-readiness.v0.58"
SMOKE_VERSION = "tradevision-deployment-smoke.v0.58"

_DB_INTEGRITY_LOCK = RLock()
_DB_INTEGRITY_CACHE: dict[tuple[object, ...], tuple[bool, int]] = {}


def configuration_fingerprint() -> DeploymentConfigurationFingerprint:
    adapter_url = os.environ.get("TRADEVISION_OPENALGO_ADAPTER_URL")
    config: dict[str, str | int | bool | None] = {
        "system_mode": SYSTEM_MODE.mode.value,
        "state_db_name": storage.DB_PATH.name,
        "adapter_url": adapter_url,
        "adapter_allowlist": ",".join(_allowed_adapter_hosts()),
        "adapter_active_key_configured": bool(os.environ.get("TRADEVISION_ADAPTER_SHARED_SECRET")),
        "adapter_previous_key_configured": bool(os.environ.get("TRADEVISION_ADAPTER_PREVIOUS_SECRET")),
        "transport_timeout_ms": 1200,
        "transport_circuit_threshold": 3,
        "live_orders_allowed": SYSTEM_MODE.allows_live_orders,
        "broker_credentials_allowed": SYSTEM_MODE.allows_broker_credentials,
    }
    fingerprint = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    expected = os.environ.get("TRADEVISION_EXPECTED_CONFIG_FINGERPRINT")
    return DeploymentConfigurationFingerprint(
        fingerprint_version=FINGERPRINT_VERSION,
        generated_at=now_iso(),
        fingerprint=fingerprint,
        expected_fingerprint=expected,
        drift_detected=bool(expected and expected != fingerprint),
        non_secret_configuration=config,
        secrets_included=False,
    )


def create_database_backup() -> DatabaseBackupArtifact:
    backup_id = str(uuid4())
    root = _backup_root()
    root.mkdir(parents=True, exist_ok=True)
    backup_path = root / f"tradevision-{backup_id}.db"
    with sqlite3.connect(storage.DB_PATH) as source, sqlite3.connect(backup_path) as destination:
        source.backup(destination)
    integrity, table_count = _database_integrity(backup_path)
    return DatabaseBackupArtifact(
        backup_version=BACKUP_VERSION,
        backup_id=backup_id,
        created_at=now_iso(),
        source_db=str(storage.DB_PATH),
        backup_path=str(backup_path),
        size_bytes=backup_path.stat().st_size,
        sha256=_sha256_file(backup_path),
        integrity_check="ok" if integrity else "failed",
        table_count=table_count,
    )


def restore_drill(artifact: DatabaseBackupArtifact) -> DatabaseRestoreDrillReport:
    backup_path = Path(artifact.backup_path).resolve()
    root = _backup_root().resolve()
    if root not in backup_path.parents:
        raise ValueError("Backup path is outside the configured backup directory.")
    if not backup_path.exists():
        raise FileNotFoundError(backup_path)
    actual_hash = _sha256_file(backup_path)
    drill_id = str(uuid4())
    restore_root = _restore_root()
    restore_root.mkdir(parents=True, exist_ok=True)
    restore_path = restore_root / f"restore-{drill_id}.db"
    shutil.copy2(backup_path, restore_path)
    integrity, restored_table_count = _database_integrity(restore_path)
    source_counts = _important_row_counts(backup_path)
    restored_counts = _important_row_counts(restore_path)
    row_checks = {
        table: {"source": count, "restored": restored_counts.get(table, -1)}
        for table, count in source_counts.items()
    }
    passed = (
        actual_hash == artifact.sha256
        and integrity
        and artifact.table_count == restored_table_count
        and all(item["source"] == item["restored"] for item in row_checks.values())
    )
    return DatabaseRestoreDrillReport(
        drill_version=DRILL_VERSION,
        drill_id=drill_id,
        executed_at=now_iso(),
        backup_id=artifact.backup_id,
        backup_sha256_matches=actual_hash == artifact.sha256,
        restore_path=str(restore_path),
        integrity_check="ok" if integrity else "failed",
        source_table_count=artifact.table_count,
        restored_table_count=restored_table_count,
        row_count_checks=row_checks,
        passed=passed,
    )


def deployment_readiness(
    *,
    transport: ExecutorTransportStatus | None = None,
    security: TransportSecurityPosture | None = None,
) -> DeploymentReadinessReport:
    config = configuration_fingerprint()
    db_ok, table_count = _database_integrity(storage.DB_PATH)
    transport = transport or transport_status(check_health=True)
    security = security or build_security_posture()
    checks = [
        _check("mode", "Research/mock mode", SYSTEM_MODE.mode.value == "MOCK", f"Mode={SYSTEM_MODE.mode.value}", True),
        _check("database", "State database integrity", db_ok, f"integrity={'ok' if db_ok else 'failed'}; tables={table_count}", True),
        _check("adapter_config", "Adapter configured", transport.configured, f"configured={transport.configured}", True),
        _check("adapter_auth", "Adapter service identity", transport.service_auth_configured, f"configured={transport.service_auth_configured}", True),
        _check("adapter_health", "Adapter authenticated health", transport.health_ok, f"checked={transport.health_checked}; ok={transport.health_ok}", True),
        _check("security", "Transport security posture", security.overall_status != "fail", f"status={security.overall_status}", True),
        _check("trace", "Transport trace integrity", security.trace_integrity.valid, f"verified={security.trace_integrity.verified_count}/{security.trace_integrity.trace_count}", True),
        _check("config_drift", "Configuration fingerprint", not config.drift_detected, "baseline unset" if config.expected_fingerprint is None else f"drift={config.drift_detected}", False, warn_if_missing=config.expected_fingerprint is None),
        _check("brokerless", "Brokerless deployment boundary", not transport.order_routing_enabled and transport.live_trading_blocked, "routing disabled; live blocked", True),
    ]
    fail_count = sum(item.status == "fail" for item in checks)
    warn_count = sum(item.status == "warn" for item in checks)
    return DeploymentReadinessReport(
        readiness_version=READINESS_VERSION,
        generated_at=now_iso(),
        target="research_mock_stack",
        configuration=config,
        checks=checks,
        pass_count=sum(item.status == "pass" for item in checks),
        warn_count=warn_count,
        fail_count=fail_count,
        ready=fail_count == 0,
    )


def deployment_smoke(readiness: DeploymentReadinessReport | None = None) -> DeploymentSmokeReport:
    readiness = readiness or deployment_readiness()
    checks = [
        _check("readiness", "Deployment readiness has no blockers", readiness.ready, f"failures={readiness.fail_count}", True),
        _check("api_db", "API database is readable", storage.storage_status().status == "ready", str(storage.DB_PATH), True),
        _check("transport", "Transport remains brokerless", not readiness.order_routing_enabled and readiness.live_trading_blocked, "routing disabled; live blocked", True),
        _check("security", "Security checks loaded", len(readiness.checks) >= 8, f"checks={len(readiness.checks)}", True),
    ]
    return DeploymentSmokeReport(
        smoke_version=SMOKE_VERSION,
        generated_at=now_iso(),
        checks=checks,
        passed_count=sum(item.status == "pass" for item in checks),
        check_count=len(checks),
        all_passed=all(item.status != "fail" for item in checks),
    )


def _backup_root() -> Path:
    configured = os.environ.get("TRADEVISION_BACKUP_DIR")
    return Path(configured) if configured else storage.DB_PATH.parent / "backups"


def _restore_root() -> Path:
    configured = os.environ.get("TRADEVISION_RESTORE_DRILL_DIR")
    return Path(configured) if configured else storage.DB_PATH.parent / "restore_drills"


def _database_integrity(path: Path) -> tuple[bool, int]:
    fingerprint = _database_integrity_fingerprint(path)
    with _DB_INTEGRITY_LOCK:
        cached = _DB_INTEGRITY_CACHE.get(fingerprint)
        if cached is not None:
            return cached

    try:
        connection = sqlite3.connect(path)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            table_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchone()[0]
            )
            result = (integrity, table_count)
        finally:
            connection.close()
    except sqlite3.DatabaseError:
        result = (False, 0)

    current_fingerprint = _database_integrity_fingerprint(path)
    with _DB_INTEGRITY_LOCK:
        _DB_INTEGRITY_CACHE[current_fingerprint] = result
    return result


def clear_database_integrity_cache() -> None:
    with _DB_INTEGRITY_LOCK:
        _DB_INTEGRITY_CACHE.clear()


def _database_integrity_fingerprint(path: Path) -> tuple[object, ...]:
    resolved = Path(path).resolve()
    wal = Path(str(resolved) + "-wal")
    shm = Path(str(resolved) + "-shm")
    return (
        str(resolved),
        *_file_stamp(resolved),
        "wal",
        *_file_stamp(wal),
        "shm",
        *_file_stamp(shm),
    )


def _file_stamp(path: Path) -> tuple[bool, int, int]:
    try:
        stat = path.stat()
        return True, int(stat.st_size), int(stat.st_mtime_ns)
    except OSError:
        return False, 0, 0


def _important_row_counts(path: Path) -> dict[str, int]:
    desired = {
        "audit_events",
        "executor_transport_outbox",
        "executor_transport_traces",
        "transport_health_samples",
        "transport_incidents",
    }
    counts: dict[str, int] = {}
    with sqlite3.connect(path) as connection:
        existing = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for table in sorted(desired & existing):
            counts[table] = int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    return counts


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check(
    check_id: str,
    name: str,
    passed: bool,
    evidence: str,
    blocks: bool,
    *,
    warn_if_missing: bool = False,
) -> DeploymentReadinessCheck:
    status = "pass" if passed and not warn_if_missing else "warn" if passed else "fail"
    return DeploymentReadinessCheck(
        check_id=check_id,
        name=name,
        status=status,
        evidence=evidence,
        blocks_deployment=blocks and status == "fail",
    )
