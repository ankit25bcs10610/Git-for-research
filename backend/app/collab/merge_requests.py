import uuid

from app.db.models import MergeRequest
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_branch_head, get_commit, update_branch_head
from app.versioning.diff_engine import tokenize_paragraphs
from app.versioning.merge_engine import diff3_merge

# `DagVersionedArtifact.merge()` only auto-commits a clean (no-conflict) merge
# when `self.tokenizer is tokenize_paragraphs` -- an identity check against
# the exact function object imported from app.versioning.diff_engine, not a
# structural/behavioral check. Re-implementing an equivalent
# `text.split("\n\n")` tokenizer locally (as an earlier draft of this module
# did) would make that identity check always fail, silently dropping
# "merge_commit_id" from `artifact.merge(...)`'s return value and causing a
# KeyError in merge_merge_request's no-conflict path. Using the real
# tokenize_paragraphs here keeps identity intact.
_paragraph_tokenizer = tokenize_paragraphs


def _ancestor_chain(session, ref: str) -> list:
    chain = []
    current_ref = ref
    while current_ref is not None:
        chain.append(current_ref)
        commit = get_commit(session, current_ref)
        current_ref = commit.parent_ids[0] if commit.parent_ids else None
    return chain


def _find_common_ancestor(session, ref_a: str, ref_b: str) -> str:
    chain_a = _ancestor_chain(session, ref_a)
    chain_b_set = set(_ancestor_chain(session, ref_b))
    for commit_id in chain_a:
        if commit_id in chain_b_set:
            return commit_id
    return None


def create_merge_request(session, artifact_id: str, source_branch: str, target_branch: str) -> str:
    target_head = get_branch_head(session, artifact_id, target_branch)
    source_head = get_branch_head(session, artifact_id, source_branch)
    base_commit_ref = _find_common_ancestor(session, target_head, source_head)
    mr_id = str(uuid.uuid4())
    mr = MergeRequest(
        id=mr_id,
        artifact_id=artifact_id,
        source_branch=source_branch,
        target_branch=target_branch,
        status="open",
        base_commit_ref=base_commit_ref,
    )
    session.add(mr)
    session.commit()
    return mr_id


def get_merge_request_diff(session, mr_id: str) -> dict:
    mr = session.get(MergeRequest, mr_id)
    artifact = DagVersionedArtifact(session, mr.artifact_id, _paragraph_tokenizer)

    base_content = artifact.get_content(mr.base_commit_ref)
    target_head = artifact.branch_head(mr.target_branch)
    source_head = artifact.branch_head(mr.source_branch)
    target_content = artifact.get_content(target_head)
    source_content = artifact.get_content(source_head)

    base_tokens = _paragraph_tokenizer(base_content)
    ours_tokens = _paragraph_tokenizer(target_content)
    theirs_tokens = _paragraph_tokenizer(source_content)

    return diff3_merge(base_tokens, ours_tokens, theirs_tokens)
