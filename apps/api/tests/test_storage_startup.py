import sqlite3

from app import storage
from app.behavior import deployment_recovery


def test_storage_startup_initializes_fresh_configured_db_path(tmp_path):
    original_path = storage.DB_PATH
    fresh_path = tmp_path / "trade_vision_state.db"
    storage.DB_PATH = fresh_path
    try:
        storage.init_db()
        status = storage.storage_status()
    finally:
        storage.DB_PATH = original_path

    assert fresh_path.exists()
    assert status.status == "ready"
    assert status.db_path == str(fresh_path)
    assert status.audit_events == 0
    assert status.replay_sessions == 0


def test_storage_init_db_is_idempotent_for_same_target(tmp_path, monkeypatch):
    original_path = storage.DB_PATH
    fresh_path = tmp_path / "idempotent_state.db"
    calls = {"backfill": 0}
    original_backfill = storage._backfill_audit_hashes

    def counted_backfill(connection):
        calls["backfill"] += 1
        return original_backfill(connection)

    storage.DB_PATH = fresh_path
    monkeypatch.setattr(storage, "_backfill_audit_hashes", counted_backfill)
    try:
        storage.init_db()
        storage.init_db()
        status = storage.storage_status()
    finally:
        storage.DB_PATH = original_path

    assert fresh_path.exists()
    assert status.status == "ready"
    assert calls["backfill"] == 1


def test_storage_init_db_initializes_each_configured_target(tmp_path):
    original_path = storage.DB_PATH
    first_path = tmp_path / "first_state.db"
    second_path = tmp_path / "second_state.db"
    try:
        storage.DB_PATH = first_path
        storage.init_db()
        first_status = storage.storage_status()

        storage.DB_PATH = second_path
        storage.init_db()
        second_status = storage.storage_status()
    finally:
        storage.DB_PATH = original_path

    assert first_path.exists()
    assert second_path.exists()
    assert first_status.status == "ready"
    assert second_status.status == "ready"
    assert first_status.db_path == str(first_path)
    assert second_status.db_path == str(second_path)


def test_storage_init_db_recreates_deleted_initialized_file(tmp_path):
    original_path = storage.DB_PATH
    fresh_path = tmp_path / "deleted_state.db"
    storage.DB_PATH = fresh_path
    try:
        storage.init_db()
        assert fresh_path.exists()
        fresh_path.unlink()

        storage.init_db()
        status = storage.storage_status()
    finally:
        storage.DB_PATH = original_path

    assert fresh_path.exists()
    assert status.status == "ready"
    assert status.db_path == str(fresh_path)


def test_sqlite_connections_apply_project_busy_timeout(tmp_path):
    original_path = storage.DB_PATH
    storage.DB_PATH = tmp_path / "busy_timeout_state.db"
    try:
        with storage.connect() as connection:
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        storage.DB_PATH = original_path

    assert busy_timeout == storage.SQLITE_BUSY_TIMEOUT_MS
    assert foreign_keys == 1


def test_memory_connections_apply_project_busy_timeout():
    original_path = storage.DB_PATH
    storage.DB_PATH = ":memory:"
    try:
        with storage.connect() as connection:
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        storage.DB_PATH = original_path

    assert busy_timeout == storage.SQLITE_BUSY_TIMEOUT_MS
    assert foreign_keys == 1


def test_database_integrity_cache_reuses_same_fingerprint(tmp_path, monkeypatch):
    db_path = tmp_path / "integrity_cache.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")

    deployment_recovery.clear_database_integrity_cache()
    original_connect = deployment_recovery.sqlite3.connect
    calls = {"connect": 0}

    def counted_connect(*args, **kwargs):
        calls["connect"] += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(deployment_recovery.sqlite3, "connect", counted_connect)

    first = deployment_recovery._database_integrity(db_path)
    second = deployment_recovery._database_integrity(db_path)

    assert first == (True, 1)
    assert second == first
    assert calls["connect"] == 1


def test_database_integrity_cache_invalidates_after_database_write(tmp_path, monkeypatch):
    db_path = tmp_path / "integrity_invalidation.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE first_table (id INTEGER PRIMARY KEY)")

    deployment_recovery.clear_database_integrity_cache()
    original_connect = deployment_recovery.sqlite3.connect
    calls = {"connect": 0}

    def counted_connect(*args, **kwargs):
        calls["connect"] += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(deployment_recovery.sqlite3, "connect", counted_connect)

    first = deployment_recovery._database_integrity(db_path)
    with original_connect(db_path) as connection:
        connection.execute("CREATE TABLE second_table (id INTEGER PRIMARY KEY)")
    db_path.touch()
    second = deployment_recovery._database_integrity(db_path)

    assert first == (True, 1)
    assert second == (True, 2)
    assert calls["connect"] == 2


def test_database_integrity_cache_invalid_database_fails_closed(tmp_path):
    db_path = tmp_path / "invalid.db"
    db_path.write_text("not sqlite", encoding="utf-8")

    deployment_recovery.clear_database_integrity_cache()

    assert deployment_recovery._database_integrity(db_path) == (False, 0)
