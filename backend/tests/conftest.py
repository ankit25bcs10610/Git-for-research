"""Shared pytest fixtures for the backend test suite.

`db_session` yields a SQLAlchemy Session bound to the real Postgres test
database (the same `DATABASE_URL` / `engine` used by the app in
app.db.base) and rolls back everything the test did once it finishes, so
tests don't leak rows into each other.

Some functions under test (e.g. app.versioning.dag_store.create_blob,
create_commit, create_branch, update_branch_head) call `session.commit()`
themselves. A plain "open a transaction, don't commit, roll back at the
end" fixture would not isolate those tests, because an inner
session.commit() would finalize the transaction early. Instead this binds
the Session to a Connection that already has an explicit outer transaction
started, with join_transaction_mode="create_savepoint" so the Session
always operates inside a SAVEPOINT: an inner session.commit() only
releases/re-creates the SAVEPOINT, while the outer transaction (and thus
full rollback of all test data) stays under this fixture's control.
"""

import pytest
from sqlalchemy.orm import Session

from app.db.base import engine


@pytest.fixture
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()
