"""Test isolation for the retrieval test suite.

Tests in this package (following the task briefs exactly) call `get_session()`
directly and commit real rows to the shared local Postgres database rather
than using the rollback-based `db_session` fixture from the parent
`tests/conftest.py`. Several tests insert identical literal strings (e.g.
"The cat sat on the mat.") across different test functions and across
repeated test runs. Because embeddings are deterministic and `Chunk` has no
timestamp column to break ties, leftover rows from a previous test/run can
tie on cosine distance with the row a later test just inserted, making
`similarity_search` results nondeterministic.

This autouse fixture truncates the chunk and provenance tables before each
test so every test starts from a clean, isolated slate while still exercising
the real database end to end.
"""

import pytest
from sqlalchemy import delete

from app.db.base import engine
from app.db.models import Chunk, ProvenanceEdge


@pytest.fixture(autouse=True)
def _clean_retrieval_tables():
    with engine.begin() as connection:
        connection.execute(delete(ProvenanceEdge))
        connection.execute(delete(Chunk))
    yield
