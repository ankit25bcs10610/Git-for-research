import uuid

import pytest
from sqlalchemy import text

from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.diff_engine import tokenize_paragraphs


@pytest.fixture
def artifact_id(db_session):
    new_id = str(uuid.uuid4())
    db_session.execute(
        text(
            "INSERT INTO artifacts (id, workspace_id, type, name) "
            "VALUES (:id, :workspace_id, :type, :name)"
        ),
        {
            "id": new_id,
            "workspace_id": str(uuid.uuid4()),
            "type": "doc",
            "name": "Adapter Test Artifact",
        },
    )
    db_session.commit()
    return new_id


def test_first_commit_is_readable_via_get_content(db_session, artifact_id):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    commit_id = artifact.commit(
        content="Paragraph one.\n\nParagraph two.",
        author="user-1",
        message="initial import",
        parent_ref=None,
    )
    assert isinstance(commit_id, str)
    assert artifact.get_content(commit_id) == "Paragraph one.\n\nParagraph two."


def test_branch_head_resolves_to_the_commit_it_was_created_from(db_session, artifact_id):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    commit_id = artifact.commit("Paragraph one.\n\nParagraph two.", "user-1", "init", None)
    artifact.branch("feature", commit_id)
    assert artifact.branch_head("feature") == commit_id
    assert artifact.get_content("feature") == "Paragraph one.\n\nParagraph two."
