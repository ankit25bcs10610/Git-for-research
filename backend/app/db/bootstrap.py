from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db.base import engine as default_engine
import app.db.models  # noqa: F401  registers all model tables on Base.metadata


def ensure_schema(engine: Engine = default_engine) -> None:
    """Create the `vector` extension and every model table if they don't already exist.

    Idempotent and non-destructive (never drops existing objects, never rewrites
    existing data) so it's safe to run on every app startup -- including against
    an already-migrated database. `Base.metadata.create_all` only creates missing
    *tables*, not missing *columns* on tables that already exist, so columns added
    to a model after its table was first created must also be added here.
    """
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        # Added when merge request identity tracking (open/merge/reject) was
        # introduced -- backfills pre-existing rows with 'unknown' rather than
        # leaving them unattributed.
        conn.execute(
            text(
                "ALTER TABLE merge_requests "
                "ADD COLUMN IF NOT EXISTS opened_by VARCHAR NOT NULL DEFAULT 'unknown'"
            )
        )
        conn.execute(text("ALTER TABLE merge_requests ADD COLUMN IF NOT EXISTS merged_by VARCHAR"))
        conn.execute(text("ALTER TABLE merge_requests ADD COLUMN IF NOT EXISTS rejected_by VARCHAR"))
