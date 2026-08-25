import json

from app.collab.merge_requests import create_merge_request
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_branch_head, get_commit
from app.versioning.diff_engine import tokenize_messages, tokenize_paragraphs
from app.db.models import Artifact, MergeRequest


def _insert_artifact(session, artifact_id, artifact_type="doc"):
    session.add(Artifact(id=artifact_id, workspace_id="ws-1", type=artifact_type, name="artifact"))
    session.commit()


def test_create_merge_request_records_base_commit_ref(db_session):
    artifact_id = "artifact-mr-1"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-a", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )

    mr_id = create_merge_request(db_session, artifact_id, "feature-a", "main", "user-1")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr is not None
    assert mr.artifact_id == artifact_id
    assert mr.source_branch == "feature-a"
    assert mr.target_branch == "main"
    assert mr.status == "open"
    assert mr.base_commit_ref == get_branch_head(db_session, artifact_id, "main")
    assert mr.opened_by == "user-1"


def test_get_merge_request_diff_reports_no_conflicts_for_disjoint_edits(db_session):
    from app.collab.merge_requests import create_merge_request, get_merge_request_diff
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-2"
    _insert_artifact(db_session, artifact_id)
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

    mr_id = create_merge_request(db_session, artifact_id, "feature-b", "main", "user-1")
    result = get_merge_request_diff(db_session, mr_id)

    assert result["conflicts"] == []


def test_merge_merge_request_advances_target_head_when_no_conflicts(db_session):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-3"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-c", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-c", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-c", "main", "user-1")
    old_head = get_branch_head(db_session, artifact_id, "main")

    result = merge_merge_request(db_session, mr_id, None, "user-1")

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
    _insert_artifact(db_session, artifact_id)
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

    mr_id = create_merge_request(db_session, artifact_id, "feature-d", "main", "user-1")

    diff_result = get_merge_request_diff(db_session, mr_id)
    assert len(diff_result["conflicts"]) == 1

    blocked = merge_merge_request(db_session, mr_id, None, "user-1")
    mr = db_session.get(MergeRequest, mr_id)
    assert blocked is False
    assert mr.status == "open"

    conflict_position = diff_result["conflicts"][0]["position"]
    resolved = merge_merge_request(db_session, mr_id, {conflict_position: "Resolved merged body."}, "user-1")
    mr = db_session.get(MergeRequest, mr_id)
    assert resolved is True
    assert mr.status == "merged"

    new_head = get_branch_head(db_session, artifact_id, "main")
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nResolved merged body."


def test_merge_merge_request_on_already_merged_mr_returns_false_and_does_not_move_head_again(db_session):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-5"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-e", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-e", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-e", "main", "user-1")

    first_result = merge_merge_request(db_session, mr_id, None, "user-1")
    assert first_result is True
    mr = db_session.get(MergeRequest, mr_id)
    assert mr.status == "merged"
    head_after_first_merge = get_branch_head(db_session, artifact_id, "main")

    # Replaying the merge on an already-"merged" MR must not re-run the merge
    # logic or advance the branch head a second time.
    second_result = merge_merge_request(db_session, mr_id, None, "user-1")

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
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-f", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-f", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-f", "main", "user-1")
    reject_merge_request(db_session, mr_id, "user-1")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr.status == "rejected"
    head_before = get_branch_head(db_session, artifact_id, "main")

    # A rejected MR must not be silently mergeable afterwards.
    result = merge_merge_request(db_session, mr_id, None, "user-1")

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
    _insert_artifact(db_session, artifact_id)
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

    mr_id = create_merge_request(db_session, artifact_id, "feature-g", "main", "user-1")
    diff_result = get_merge_request_diff(db_session, mr_id)
    conflict_position = diff_result["conflicts"][0]["position"]
    # position 0 is "Intro paragraph." — a real, non-conflicting list index —
    # not the actual conflict position.
    wrong_position = 0
    assert wrong_position != conflict_position

    result = merge_merge_request(db_session, mr_id, {wrong_position: "corrupted text"}, "user-1")

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
    _insert_artifact(db_session, artifact_id)
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

    mr_id = create_merge_request(db_session, artifact_id, "feature-h", "main", "user-1")

    # Must not raise IndexError, and must not merge.
    result = merge_merge_request(db_session, mr_id, {9999: "corrupted text"}, "user-1")

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
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Para A.\n\nPara B.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-i", root)

    main_commit = artifact.commit("Main A.\n\nMain B.", "user-1", "main edit", root)
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit("Feature A.\n\nFeature B.", "user-1", "feature edit", root)
    update_branch_head(db_session, artifact_id, "feature-i", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-i", "main", "user-1")
    diff_result = get_merge_request_diff(db_session, mr_id)
    assert len(diff_result["conflicts"]) == 2

    first_position = diff_result["conflicts"][0]["position"]
    # Only resolving one of the two required conflict positions.
    result = merge_merge_request(db_session, mr_id, {first_position: "Resolved A."}, "user-1")

    mr = db_session.get(MergeRequest, mr_id)
    head_after = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "open"
    assert head_after == main_commit


def test_merge_merge_request_returns_false_and_does_not_clobber_concurrent_head_move(db_session, monkeypatch):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-10"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-j", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-j", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-j", "main", "user-1")

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

    result = merge_merge_request(db_session, mr_id, None, "user-1")

    mr = db_session.get(MergeRequest, mr_id)
    final_head = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "open"
    # The concurrent writer's commit must still be reachable from "main" —
    # this finalizer must not silently overwrite/orphan it.
    assert final_head == concurrent_commit


def test_merge_merge_request_resolved_conflict_commit_has_both_parents(db_session):
    """Regression test for Finding C1.

    Before the fix, the conflict-resolution path built the resolved commit
    via `artifact.commit(merge_content, "user-1", "resolve merge conflicts",
    target_head)` -- DagVersionedArtifact.commit only accepts a single
    parent_ref, so the resulting commit's parent_ids was just [target_head]
    and the source branch was silently dropped from history. It must now
    carry BOTH branch heads as parents, the same way the clean-merge
    auto-commit path in dag_adapter.py already does.
    """
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-11"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-k", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-k", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-k", "main", "user-1")
    diff_result = get_merge_request_diff(db_session, mr_id)
    conflict_position = diff_result["conflicts"][0]["position"]

    resolved = merge_merge_request(db_session, mr_id, {conflict_position: "Resolved merged body."}, "user-1")
    assert resolved is True

    merge_commit_id = get_branch_head(db_session, artifact_id, "main")
    merge_commit = get_commit(db_session, merge_commit_id)

    # Both the pre-merge target head ("main") and the source branch head
    # ("feature-k") must be present as parents -- neither one silently
    # dropped.
    assert set(merge_commit.parent_ids) == {main_commit, feature_commit}


def test_merge_merge_request_resolved_conflict_source_reachable_via_all_parents(db_session):
    """Regression test for Finding C1.

    Proves the conflict-resolved merge commit is actually "stuck" in
    history: walking ALL of its parent edges (not just the first, as
    `_find_common_ancestor`'s simplified mainline-only walk does) reaches
    the source branch's own commit directly. Before the fix this commit was
    unreachable from the merge commit by any parent edge at all, because it
    was never recorded as a parent in the first place.
    """
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-12"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-l", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-l", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-l", "main", "user-1")
    diff_result = get_merge_request_diff(db_session, mr_id)
    conflict_position = diff_result["conflicts"][0]["position"]

    resolved = merge_merge_request(db_session, mr_id, {conflict_position: "Resolved merged body."}, "user-1")
    assert resolved is True

    merge_commit_id = get_branch_head(db_session, artifact_id, "main")

    # Full (all-parents, not just first-parent) BFS over ancestor edges from
    # the merge commit.
    seen = set()
    frontier = [merge_commit_id]
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        commit = get_commit(db_session, current)
        frontier.extend(commit.parent_ids)

    assert feature_commit in seen
    assert main_commit in seen
    assert root in seen


def test_merge_merge_request_accepts_string_keyed_resolutions(db_session):
    """Regression test for Finding C2.

    `resolutions` arrives with string keys whenever it round-trips through
    JSON (e.g. an HTTP request body) -- exactly how the frontend's
    `submitResolution` sends it (`JSON.stringify({resolutions})`). Before the
    fix, `set(resolutions.keys()) != conflict_positions` always mismatched
    (`{"2"} != {2}`), so every real resolution submitted through the UI was
    silently rejected.
    """
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-13"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-m", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-m", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-m", "main", "user-1")
    diff_result = get_merge_request_diff(db_session, mr_id)
    conflict_position = diff_result["conflicts"][0]["position"]

    # String key, exactly as it would arrive after a JSON round-trip.
    string_keyed_resolutions = {str(conflict_position): "Resolved merged body."}

    result = merge_merge_request(db_session, mr_id, string_keyed_resolutions, "user-1")

    mr = db_session.get(MergeRequest, mr_id)
    new_head = get_branch_head(db_session, artifact_id, "main")

    assert result is True
    assert mr.status == "merged"
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nResolved merged body."


def test_merge_merge_request_rejects_non_numeric_string_keyed_resolutions(db_session):
    """Regression test for Finding C2.

    A resolutions dict with a key that can't be coerced to int must be
    rejected cleanly (return False), not raise.
    """
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-14"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-n", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-n", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-n", "main", "user-1")

    result = merge_merge_request(db_session, mr_id, {"abc": "text"}, "user-1")

    mr = db_session.get(MergeRequest, mr_id)
    head_after = get_branch_head(db_session, artifact_id, "main")

    assert result is False
    assert mr.status == "open"
    assert head_after == main_commit


def test_get_merge_request_diff_uses_message_tokenizer_for_chat_artifacts(db_session):
    """Regression test for the chat merge-conflict bug.

    merge_requests.py used to hardcode the paragraph tokenizer for every
    artifact type regardless of `artifact.type`. Chat content is a single-line
    JSON blob with no blank lines, so `tokenize_paragraphs` collapsed it into
    ONE token -- meaning any two edits anywhere in the conversation, even to
    completely different messages, were reported as a single conflict
    spanning the whole chat. With the message tokenizer selected correctly,
    disjoint edits to different messages must not conflict.
    """
    from app.collab.merge_requests import create_merge_request, get_merge_request_diff
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-chat-1"
    _insert_artifact(db_session, artifact_id, artifact_type="chat")
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_messages)

    base_json = json.dumps(
        [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}]
    )
    root = artifact.commit(base_json, "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-chat", root)

    # main edits only the assistant's message.
    main_json = json.dumps(
        [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello there"}]
    )
    main_commit = artifact.commit(main_json, "user-1", "main edit", root)
    update_branch_head(db_session, artifact_id, "main", main_commit)

    # feature-chat edits only the user's message -- a disjoint edit.
    feature_json = json.dumps(
        [{"role": "user", "text": "hi you"}, {"role": "assistant", "text": "hello"}]
    )
    feature_commit = artifact.commit(feature_json, "user-1", "feature edit", root)
    update_branch_head(db_session, artifact_id, "feature-chat", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-chat", "main", "user-1")
    result = get_merge_request_diff(db_session, mr_id)

    assert result["conflicts"] == []


def test_merge_merge_request_chat_clean_merge_produces_valid_message_json(db_session):
    """Regression test for the chat merge-conflict bug.

    A clean (no-conflict) merge on a chat artifact must produce content that
    round-trips through `json.loads` back into the merged messages -- not
    "\\n\\n"-joined `"role: text"` strings, which isn't valid JSON at all.
    """
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-chat-2"
    _insert_artifact(db_session, artifact_id, artifact_type="chat")
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_messages)

    base_json = json.dumps(
        [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}]
    )
    root = artifact.commit(base_json, "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-chat-2", root)

    main_json = json.dumps(
        [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello there"}]
    )
    main_commit = artifact.commit(main_json, "user-1", "main edit", root)
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_json = json.dumps(
        [{"role": "user", "text": "hi you"}, {"role": "assistant", "text": "hello"}]
    )
    feature_commit = artifact.commit(feature_json, "user-1", "feature edit", root)
    update_branch_head(db_session, artifact_id, "feature-chat-2", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-chat-2", "main", "user-1")
    result = merge_merge_request(db_session, mr_id, None, "user-1")
    assert result is True

    new_head = get_branch_head(db_session, artifact_id, "main")
    merged_content = artifact.get_content(new_head)
    merged_messages = json.loads(merged_content)

    assert merged_messages == [
        {"role": "user", "text": "hi you"},
        {"role": "assistant", "text": "hello there"},
    ]

    merge_commit = get_commit(db_session, new_head)
    assert set(merge_commit.parent_ids) == {main_commit, feature_commit}


def test_merge_merge_request_records_merged_by_on_success(db_session):
    """Regression test for the missing-identity-tracking finding.

    routes_collab.py recorded no author at all for opening/merging/rejecting a
    merge request. merge_merge_request must record who actually performed the
    merge once it succeeds.
    """
    from app.collab.merge_requests import merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-15"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-o", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-o", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-o", "main", "alice")
    result = merge_merge_request(db_session, mr_id, None, "bob")

    mr = db_session.get(MergeRequest, mr_id)
    assert result is True
    assert mr.opened_by == "alice"
    assert mr.merged_by == "bob"


def test_merge_merge_request_does_not_record_merged_by_when_blocked(db_session):
    """A merge that's blocked (unresolved conflict) never actually merged --
    merged_by must stay unset, not attribute a merge that didn't happen.
    """
    from app.collab.merge_requests import merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-16"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-p", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-p", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-p", "main", "alice")
    result = merge_merge_request(db_session, mr_id, None, "bob")

    mr = db_session.get(MergeRequest, mr_id)
    assert result is False
    assert mr.merged_by is None


def test_reject_merge_request_records_rejected_by(db_session):
    from app.collab.merge_requests import reject_merge_request

    artifact_id = "artifact-mr-17"
    _insert_artifact(db_session, artifact_id)
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-q", root)

    mr_id = create_merge_request(db_session, artifact_id, "feature-q", "main", "alice")
    reject_merge_request(db_session, mr_id, "carol")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr.status == "rejected"
    assert mr.opened_by == "alice"
    assert mr.rejected_by == "carol"
