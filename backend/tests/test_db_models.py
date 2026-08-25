import os

from sqlalchemy import create_engine, inspect

from app.db.base import Base
import app.db.models  # noqa: F401  registers all model tables on Base.metadata

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://research:research@localhost:5432/research"
)


def test_all_tables_are_created():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
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

    assert expected_tables.issubset(table_names)

    engine.dispose()
