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


def test_get_merge_request_diff_reports_no_conflicts_for_disjoint_edits(db_session):
    from app.collab.merge_requests import create_merge_request, get_merge_request_diff
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-2"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-b", root)

    # Committing alone does not move a branch head — DagVersionedArtifact.commit
    # only appends a commit object; the branch pointer must be advanced
    # explicitly so later branch-head lookups see this edit.
    feature_commit = artifact.commit(
        "Edited intro paragraph.\n\nBody paragraph.", "user-1", "edit intro", root
    )
    update_branch_head(db_session, artifact_id, "feature-b", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-b", "main")
    result = get_merge_request_diff(db_session, mr_id)

    assert result["conflicts"] == []


def test_merge_merge_request_advances_target_head_when_no_conflicts(db_session):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-3"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-c", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-c", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-c", "main")
    old_head = get_branch_head(db_session, artifact_id, "main")

    result = merge_merge_request(db_session, mr_id, None)

    new_head = get_branch_head(db_session, artifact_id, "main")
    mr = db_session.get(MergeRequest, mr_id)

    assert result is True
    assert new_head != old_head
    assert mr.status == "merged"
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nEdited body paragraph."


def test_merge_merge_request_blocks_on_conflict_until_resolved(db_session):
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-4"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-d", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-d", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-d", "main")

    diff_result = get_merge_request_diff(db_session, mr_id)
    assert len(diff_result["conflicts"]) == 1

    blocked = merge_merge_request(db_session, mr_id, None)
    mr = db_session.get(MergeRequest, mr_id)
    assert blocked is False
    assert mr.status == "open"

    conflict_position = diff_result["conflicts"][0]["position"]
    resolved = merge_merge_request(
        db_session, mr_id, {conflict_position: "Resolved merged body."}
    )
    mr = db_session.get(MergeRequest, mr_id)
    assert resolved is True
    assert mr.status == "merged"

    new_head = get_branch_head(db_session, artifact_id, "main")
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nResolved merged body."


def test_merge_merge_request_on_already_merged_mr_returns_false_and_does_not_move_head_again(db_session):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-5"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-e", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-e", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-e", "main")

    first_result = merge_merge_request(db_session, mr_id, None)
    assert first_result is True
    mr = db_session.get(MergeRequest, mr_id)
    assert mr.status == "merged"
    head_after_first_merge = get_branch_head(db_session, artifact_id, "main")

    # Replaying the merge on an already-"merged" MR must not re-run the merge
    # logic or advance the branch head a second time.
    second_result = merge_merge_request(db_session, mr_id, None)

    mr = db_session.get(MergeRequest, mr_id)
    head_after_second_call = get_branch_head(db_session, artifact_id, "main")

    assert second_result is False
    assert mr.status == "merged"
    assert head_after_second_call == head_after_first_merge


def test_merge_merge_request_on_rejected_mr_returns_false_and_does_not_flip_to_merged(db_session):
    from app.collab.merge_requests import (
        create_merge_request,
        merge_merge_request,
        reject_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-6"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-f", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-f", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-f", "main")
    reject_merge_request(db_session, mr_id)

    mr = db_session.get(MergeRequest, mr_id)
    assert mr.status == "rejected"
    head_before = get_branch_head(db_session, artifact_id, "main")

    # A rejected MR must not be silently mergeable afterwards.
    result = merge_merge_request(db_session, mr_id, None)

    mr = db_session.get(MergeRequest, mr_id)
    head_after = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "rejected"
    assert head_after == head_before


def test_merge_merge_request_rejects_resolution_at_wrong_in_range_position(db_session):
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-7"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-g", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-g", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-g", "main")
    diff_result = get_merge_request_diff(db_session, mr_id)
    conflict_position = diff_result["conflicts"][0]["position"]
    # position 0 is "Intro paragraph." — a real, non-conflicting list index —
    # not the actual conflict position.
    wrong_position = 0
    assert wrong_position != conflict_position

    result = merge_merge_request(db_session, mr_id, {wrong_position: "corrupted text"})

    mr = db_session.get(MergeRequest, mr_id)
    head_after = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "open"
    assert head_after == main_commit
    # The non-conflicting paragraph must not have been silently corrupted.
    assert artifact.get_content(head_after) == "Intro paragraph.\n\nMain-edited body."


def test_merge_merge_request_rejects_resolution_at_out_of_range_position(db_session):
    from app.collab.merge_requests import (
        create_merge_request,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-8"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-h", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-h", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-h", "main")

    # Must not raise IndexError, and must not merge.
    result = merge_merge_request(db_session, mr_id, {9999: "corrupted text"})

    mr = db_session.get(MergeRequest, mr_id)
    head_after = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "open"
    assert head_after == main_commit


def test_merge_merge_request_rejects_resolutions_missing_a_conflict_position(db_session):
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-9"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Para A.\n\nPara B.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-i", root)

    main_commit = artifact.commit("Main A.\n\nMain B.", "user-1", "main edit", root)
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit("Feature A.\n\nFeature B.", "user-1", "feature edit", root)
    update_branch_head(db_session, artifact_id, "feature-i", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-i", "main")
    diff_result = get_merge_request_diff(db_session, mr_id)
    assert len(diff_result["conflicts"]) == 2

    first_position = diff_result["conflicts"][0]["position"]
    # Only resolving one of the two required conflict positions.
    result = merge_merge_request(db_session, mr_id, {first_position: "Resolved A."})

    mr = db_session.get(MergeRequest, mr_id)
    head_after = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "open"
    assert head_after == main_commit


def test_merge_merge_request_returns_false_and_does_not_clobber_concurrent_head_move(db_session, monkeypatch):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-10"
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-j", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-j", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-j", "main")

    # A concurrent writer's commit that lands on "main" after this
    # finalizer has already read the target branch head (inside
    # merge_merge_request, captured as `target_head`) but before it writes
    # its own merge commit back.
    concurrent_commit = artifact.commit(
        "Intro paragraph.\n\nConcurrently-edited body.", "user-1", "concurrent edit", root
    )

    original_merge = DagVersionedArtifact.merge

    def merge_with_interleaved_concurrent_write(self, base_ref, ours_ref, theirs_ref):
        result = original_merge(self, base_ref, ours_ref, theirs_ref)
        update_branch_head(db_session, artifact_id, "main", concurrent_commit)
        return result

    monkeypatch.setattr(DagVersionedArtifact, "merge", merge_with_interleaved_concurrent_write)

    result = merge_merge_request(db_session, mr_id, None)

    mr = db_session.get(MergeRequest, mr_id)
    final_head = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "open"
    # The concurrent writer's commit must still be reachable from "main" —
    # this finalizer must not silently overwrite/orphan it.
    assert final_head == concurrent_commit
