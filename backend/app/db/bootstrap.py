from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db.base import engine as default_engine
import app.db.models  # noqa: F401  registers all model tables on Base.metadata


def ensure_schema(engine: Engine = default_engine) -> None:
    """Create the `vector` extension and every model table if they don't already exist.

    Idempotent and non-destructive (never drops or alters existing objects) so it's
    safe to run on every app startup -- including against an already-migrated database.
    """
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
