import json
import uuid

import pytest
from sqlalchemy import text

from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import update_branch_head
from app.versioning.diff_engine import tokenize_messages, tokenize_paragraphs


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


def test_diff_of_a_changed_paragraph_includes_word_diff(db_session, artifact_id):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    c1 = artifact.commit("Paragraph one.\n\nParagraph two.", "user-1", "init", None)
    c2 = artifact.commit(
        "Paragraph one.\n\nParagraph two updated.", "user-1", "edit", c1
    )
    entries = artifact.diff(c1, c2)
    # diff_tokens (app.versioning.diff_engine) tags entries with a "kind" key
    # whose value is "changed" for a replaced token, not "type"/"change".
    changed = [entry for entry in entries if entry["kind"] == "changed"]
    assert len(changed) == 1
    assert changed[0]["old_text"] == "Paragraph two."
    assert changed[0]["text"] == "Paragraph two updated."
    assert "word_diff" in changed[0]
    assert changed[0]["word_diff"]


def test_merge_with_no_conflicts_creates_a_merge_commit_with_both_changes(
    db_session, artifact_id
):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    base_commit = artifact.commit(
        "Paragraph one.\n\nParagraph two.", "user-1", "init", None
    )
    artifact.branch("feature", base_commit)

    branch_commit = artifact.commit(
        "Paragraph one.\n\nParagraph two changed on branch.",
        "user-1",
        "branch edit",
        base_commit,
    )
    update_branch_head(db_session, artifact_id, "feature", branch_commit)

    main_commit = artifact.commit(
        "Paragraph one changed on main.\n\nParagraph two.",
        "user-1",
        "main edit",
        base_commit,
    )

    result = artifact.merge(
        base_ref=base_commit,
        ours_ref=main_commit,
        theirs_ref=artifact.branch_head("feature"),
    )

    assert result["conflicts"] == []
    assert "merge_commit_id" in result
    merged_content = artifact.get_content(result["merge_commit_id"])
    assert "Paragraph one changed on main." in merged_content
    assert "Paragraph two changed on branch." in merged_content


def test_merge_with_message_tokenizer_does_not_auto_commit(db_session, artifact_id):
    # tokenize_messages already does json.loads(content_json) internally
    # (see app/versioning/diff_engine.py), so it is passed straight through
    # as the tokenizer rather than wrapped in something that parses JSON a
    # second time.
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_messages)
    base_json = [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}]
    ours_json = [
        {"role": "user", "text": "hi there"},
        {"role": "assistant", "text": "hello"},
    ]
    theirs_json = [
        {"role": "user", "text": "hi"},
        {"role": "assistant", "text": "hello friend"},
    ]
    base_commit = artifact.commit(json.dumps(base_json), "user-1", "init", None)
    ours_commit = artifact.commit(json.dumps(ours_json), "user-1", "ours", base_commit)
    theirs_commit = artifact.commit(
        json.dumps(theirs_json), "user-1", "theirs", base_commit
    )

    result = artifact.merge(base_commit, ours_commit, theirs_commit)

    assert result["conflicts"] == []
    assert "merge_commit_id" not in result
