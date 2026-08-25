import uuid

from app.db.models import MergeRequest
from app.versioning.git_adapter import GitVersionedArtifact


def create_merge_request(
    session,
    artifact: GitVersionedArtifact,
    artifact_id: str,
    source_branch: str,
    target_branch: str,
    opened_by: str,
) -> str:
    target_head = artifact.branch_head(target_branch)
    source_head = artifact.branch_head(source_branch)
    base_commit_ref = artifact.merge_base(target_head, source_head)
    mr_id = str(uuid.uuid4())
    mr = MergeRequest(
        id=mr_id,
        artifact_id=artifact_id,
        source_branch=source_branch,
        target_branch=target_branch,
        status="open",
        base_commit_ref=base_commit_ref,
        opened_by=opened_by,
    )
    session.add(mr)
    session.commit()
    return mr_id


def get_merge_request_diff(session, artifact: GitVersionedArtifact, mr_id: str) -> dict:
    mr = session.get(MergeRequest, mr_id)
    target_head = artifact.branch_head(mr.target_branch)
    source_head = artifact.branch_head(mr.source_branch)
    return artifact.preview_merge(mr.base_commit_ref, target_head, source_head)


def merge_merge_request(
    session, artifact: GitVersionedArtifact, mr_id: str, resolutions, merged_by: str
) -> bool:
    mr = session.get(MergeRequest, mr_id)
    if mr.status != "open":
        return False

    preview = get_merge_request_diff(session, artifact, mr_id)
    if preview["conflicts"] and resolutions is None:
        return False

    # Pass branch names (not the resolved head commit ids) for ours/theirs --
    # GitVersionedArtifact.merge() advances and checks out that branch by
    # name once the merge commit is written.
    result = artifact.merge(
        mr.base_commit_ref, mr.target_branch, mr.source_branch, resolutions=resolutions
    )
    if not result["merged"]:
        return False

    mr.status = "merged"
    mr.merged_by = merged_by
    session.commit()
    return True


def reject_merge_request(session, mr_id: str, rejected_by: str) -> None:
    mr = session.get(MergeRequest, mr_id)
    if mr.status != "open":
        return
    mr.status = "rejected"
    mr.rejected_by = rejected_by
    session.commit()
