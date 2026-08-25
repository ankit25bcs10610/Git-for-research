from app.collab.agent_editor import agent_edit
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.diff_engine import tokenize_paragraphs
from app.db.models import MergeRequest


def _fake_llm_call(instruction: str, current_content: str) -> str:
    return current_content + "\n\nAppended by agent."


def test_agent_edit_creates_branch_commit_and_open_merge_request(db_session):
    artifact_id = "artifact-agent-1"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)

    mr_id = agent_edit(
        db_session, artifact_id, "main", "Append a closing remark.", _fake_llm_call, "user-1"
    )

    mr = db_session.get(MergeRequest, mr_id)
    assert mr is not None
    assert mr.status == "open"
    assert mr.target_branch == "main"
    assert mr.source_branch.startswith("agent-edit-")

    source_head = artifact.branch_head(mr.source_branch)
    source_content = artifact.get_content(source_head)
    assert source_content == "Intro paragraph.\n\nBody paragraph.\n\nAppended by agent."


def test_agent_edit_produces_distinct_branches_on_repeated_calls(db_session):
    artifact_id = "artifact-agent-2"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)

    mr_id_one = agent_edit(
        db_session, artifact_id, "main", "First instruction.", _fake_llm_call, "user-1"
    )
    mr_id_two = agent_edit(
        db_session, artifact_id, "main", "Second instruction.", _fake_llm_call, "user-1"
    )

    mr_one = db_session.get(MergeRequest, mr_id_one)
    mr_two = db_session.get(MergeRequest, mr_id_two)

    assert mr_one.source_branch != mr_two.source_branch
    assert mr_one.status == "open"
    assert mr_two.status == "open"
