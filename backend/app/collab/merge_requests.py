import uuid

from app.artifacts import get_artifact
from app.db.models import MergeRequest
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import (
    create_blob,
    create_commit,
    get_branch_head,
    get_commit,
    update_branch_head,
)
from app.versioning.diff_engine import join_tokens_for_type, tokenizer_for_type
from app.versioning.merge_engine import diff3_merge


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
    a = get_artifact(session, mr.artifact_id)
    tokenizer = tokenizer_for_type(a.type)
    artifact = DagVersionedArtifact(session, mr.artifact_id, tokenizer)

    base_content = artifact.get_content(mr.base_commit_ref)
    target_head = artifact.branch_head(mr.target_branch)
    source_head = artifact.branch_head(mr.source_branch)
    target_content = artifact.get_content(target_head)
    source_content = artifact.get_content(source_head)

    base_tokens = tokenizer(base_content)
    ours_tokens = tokenizer(target_content)
    theirs_tokens = tokenizer(source_content)

    return diff3_merge(base_tokens, ours_tokens, theirs_tokens)


def merge_merge_request(session, mr_id: str, resolutions=None) -> bool:
    mr = session.get(MergeRequest, mr_id)
    if mr.status != "open":
        return False

    a = get_artifact(session, mr.artifact_id)
    tokenizer = tokenizer_for_type(a.type)
    artifact = DagVersionedArtifact(session, mr.artifact_id, tokenizer)

    diff_result = get_merge_request_diff(session, mr_id)
    conflicts = diff_result["conflicts"]

    if conflicts and resolutions is None:
        return False

    target_head = artifact.branch_head(mr.target_branch)
    source_head = artifact.branch_head(mr.source_branch)

    if not conflicts:
        merge_result = artifact.merge(mr.base_commit_ref, target_head, source_head)
        if "merge_commit_id" in merge_result:
            merge_commit_id = merge_result["merge_commit_id"]
        else:
            # DagVersionedArtifact.merge() only auto-commits when its tokenizer
            # is tokenize_paragraphs (see dag_adapter.py) -- for a chat
            # artifact's message tokenizer it stops after diff3_merge, so the
            # commit must be built here instead, mirroring the resolved-
            # conflict path below (both branch heads as parents).
            merge_content = join_tokens_for_type(a.type, merge_result["merged_tokens"])
            blob_hash = create_blob(session, merge_content)
            merge_commit_id = create_commit(
                session,
                mr.artifact_id,
                blob_hash,
                [target_head, source_head],
                "merge-bot",
                f"Merge {mr.source_branch} into {mr.target_branch}",
            )
    else:
        # `resolutions` arrives with string keys whenever it has been
        # round-tripped through JSON (e.g. an HTTP request body deserialized
        # by the route layer), while `conflicts[*]["position"]` is always a
        # plain int. Coerce keys to int defensively before comparing against
        # conflict_positions, so a real resolution submitted through the UI
        # isn't silently rejected just because its keys are strings on the
        # wire. Non-coercible keys are treated the same as any other invalid
        # resolution: reject, don't raise.
        try:
            resolutions = {int(k): v for k, v in resolutions.items()}
        except (ValueError, TypeError):
            return False

        conflict_positions = {c["position"] for c in conflicts}
        if set(resolutions.keys()) != conflict_positions:
            return False
        merged_tokens = list(diff_result["merged_tokens"])
        for position, resolved_text in resolutions.items():
            merged_tokens[position] = resolved_text
        merge_content = join_tokens_for_type(a.type, merged_tokens)
        # A resolved-conflict commit must record BOTH branches as parents,
        # the same way DagVersionedArtifact.merge()'s clean-merge auto-commit
        # path does (see dag_adapter.py's `create_commit(..., [ours_commit_id,
        # theirs_commit_id], ...)` call) -- artifact.commit() only accepts a
        # single parent_ref, which would silently drop the source branch out
        # of history. Build the commit directly via create_blob/create_commit
        # instead, exactly like that clean-merge path does, with target_head
        # (ours) first and source_head (theirs) second.
        blob_hash = create_blob(session, merge_content)
        merge_commit_id = create_commit(
            session,
            mr.artifact_id,
            blob_hash,
            [target_head, source_head],
            "merge-bot",
            "resolve merge conflicts",
        )

    if not update_branch_head(
        session, mr.artifact_id, mr.target_branch, merge_commit_id, expected_commit_id=target_head
    ):
        return False
    mr.status = "merged"
    session.commit()
    return True


def reject_merge_request(session, mr_id: str) -> None:
    mr = session.get(MergeRequest, mr_id)
    if mr.status != "open":
        return
    mr.status = "rejected"
    session.commit()
