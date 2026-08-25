import os
import uuid

from sqlalchemy import create_engine, inspect, text

from app.db.bootstrap import ensure_schema

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://research:research@localhost:5432/research"
)

EXPECTED_TABLES = {
    "blobs",
    "artifacts",
    "commits",
    "branches",
    "chunks",
    "provenance_edges",
    "merge_requests",
    "last_seen",
    "users",
}


def test_ensure_schema_creates_every_table_on_a_fresh_empty_schema():
    """Regression test for the "docker compose up --build can't boot" finding.

    On a genuinely fresh database volume, nothing but the `vector` extension
    exists (see app/db/init.sql) -- there is no migration step that creates
    the actual tables. Simulates that exact starting point with a brand-new,
    empty Postgres schema (not the shared `public` schema the rest of the
    suite runs against) and proves `ensure_schema` alone -- with no other
    setup -- creates every table the app needs.
    """
    schema_name = f"test_bootstrap_{uuid.uuid4().hex[:8]}"
    admin_engine = create_engine(DATABASE_URL)
    with admin_engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema_name}"))

    try:
        scoped_engine = create_engine(
            DATABASE_URL,
            connect_args={"options": f"-c search_path={schema_name},public"},
        ).execution_options(schema_translate_map={None: schema_name})
        try:
            ensure_schema(scoped_engine)

            inspector = inspect(scoped_engine)
            table_names = set(inspector.get_table_names(schema=schema_name))
            assert EXPECTED_TABLES.issubset(table_names)
        finally:
            scoped_engine.dispose()
    finally:
        with admin_engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {schema_name} CASCADE"))
        admin_engine.dispose()


def test_ensure_schema_is_idempotent_against_an_already_migrated_database(db_session):
    """Must be safe to run on every app startup, not just the first one --
    it must never drop or wipe a database that already has real data.
    """
    from app.db.base import engine as shared_engine

    ensure_schema(shared_engine)
    ensure_schema(shared_engine)

    inspector = inspect(shared_engine)
    table_names = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(table_names)
