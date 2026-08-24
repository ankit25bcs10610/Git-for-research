import uuid

from app.collab.merge_requests import create_merge_request
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import update_branch_head
from app.versioning.diff_engine import tokenize_paragraphs

# Kept as the same object as app.versioning.diff_engine.tokenize_paragraphs
# (see the comment in app/collab/merge_requests.py) rather than a locally
# reimplemented tokenizer. agent_edit itself never calls artifact.diff() or
# artifact.merge(), so this identity doesn't change behavior here, but using
# the same tokenizer as the rest of app.collab keeps DagVersionedArtifact
# instances constructed across this package consistent.
_paragraph_tokenizer = tokenize_paragraphs


def agent_edit(session, artifact_id: str, base_branch: str, instruction: str, llm_call) -> str:
    artifact = DagVersionedArtifact(session, artifact_id, _paragraph_tokenizer)

    base_head = artifact.branch_head(base_branch)
    current_content = artifact.get_content(base_head)

    proposed_content = llm_call(instruction, current_content)

    suffix = uuid.uuid4().hex[:8]
    new_branch_name = f"agent-edit-{suffix}"
    artifact.branch(new_branch_name, base_head)

    new_commit_id = artifact.commit(proposed_content, "agent", instruction, base_head)
    update_branch_head(session, artifact_id, new_branch_name, new_commit_id)

    mr_id = create_merge_request(session, artifact_id, new_branch_name, base_branch)
    return mr_id
