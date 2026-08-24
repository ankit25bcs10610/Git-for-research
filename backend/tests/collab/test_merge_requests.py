from app.collab.merge_requests import create_merge_request
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_branch_head
from app.versioning.diff_engine import tokenize_paragraphs
from app.db.models import MergeRequest


def test_create_merge_request_records_base_commit_ref(db_session):
    artifact_id = "artifact-mr-1"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-a", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )

    mr_id = create_merge_request(db_session, artifact_id, "feature-a", "main")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr is not None
    assert mr.artifact_id == artifact_id
    assert mr.source_branch == "feature-a"
    assert mr.target_branch == "main"
    assert mr.status == "open"
    assert mr.base_commit_ref == get_branch_head(db_session, artifact_id, "main")
