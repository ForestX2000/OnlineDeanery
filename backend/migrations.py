"""Small, transactional PostgreSQL schema migration registry.

``create_all`` is retained for first-time table creation. Changes to existing
tables belong in a numbered migration below and are recorded in
``schema_migrations`` so they run once per database.
"""

from collections.abc import Callable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


def _ensure_request_document_type(connection: Connection) -> None:
    columns = {
        column["name"]
        for column in inspect(connection).get_columns("requests")
    }
    if "document_type" not in columns:
        connection.execute(text(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS document_type VARCHAR(100)"
        ))


def _preserve_admin_audit(connection: Connection) -> None:
    columns = {
        column["name"]
        for column in inspect(connection).get_columns("audit_logs")
    }
    if "admin_email" not in columns:
        connection.execute(text("ALTER TABLE audit_logs ADD COLUMN admin_email VARCHAR(255)"))
    if "target_user_id" not in columns:
        connection.execute(text("ALTER TABLE audit_logs ADD COLUMN target_user_id INTEGER"))

    connection.execute(text(
        "UPDATE audit_logs AS audit SET admin_email = users.email "
        "FROM users WHERE audit.admin_id = users.user_id AND audit.admin_email IS NULL"
    ))

    # The old FK cascaded away an administrator's audit trail on account
    # deletion. Replace it with SET NULL; admin_email preserves attribution.
    for foreign_key in inspect(connection).get_foreign_keys("audit_logs"):
        if foreign_key.get("constrained_columns") == ["admin_id"]:
            name = foreign_key.get("name")
            if not name:
                raise RuntimeError("Cannot safely replace the audit_logs.admin_id foreign key")
            escaped_name = name.replace('"', '""')
            connection.execute(text(
                f'ALTER TABLE audit_logs DROP CONSTRAINT "{escaped_name}"'
            ))

    connection.execute(text("ALTER TABLE audit_logs ALTER COLUMN admin_id DROP NOT NULL"))
    connection.execute(text(
        "ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_admin_user "
        "FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE SET NULL"
    ))


MIGRATIONS: tuple[tuple[int, Callable[[Connection], None]], ...] = (
    (1, _ensure_request_document_type),
    (2, _preserve_admin_audit),
)


def apply_migrations(connection: Connection) -> None:
    """Apply pending migrations inside the caller's transaction."""
    # Serialize startup across workers/processes sharing this PostgreSQL DB.
    connection.execute(text("SELECT pg_advisory_xact_lock(731904221)"))
    connection.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, "
        "applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
    ))
    applied = {
        row[0]
        for row in connection.execute(text("SELECT version FROM schema_migrations"))
    }
    for version, migration in MIGRATIONS:
        if version in applied:
            continue
        migration(connection)
        connection.execute(
            text("INSERT INTO schema_migrations (version) VALUES (:version)"),
            {"version": version},
        )
