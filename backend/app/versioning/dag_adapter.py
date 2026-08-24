from typing import Callable, Dict, List, Optional

from app.versioning.dag_store import (
    create_blob,
    create_branch,
    create_commit,
    get_blob_content,
    get_branch_head,
    get_commit,
)
from app.versioning.interface import VersionedArtifact


class DagVersionedArtifact(VersionedArtifact):
    def __init__(self, session, artifact_id: str, tokenizer: Callable[[str], List[str]]):
        self.session = session
        self.artifact_id = artifact_id
        self.tokenizer = tokenizer

    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        blob_hash = create_blob(self.session, content)
        parent_ids = [parent_ref] if parent_ref else []
        # dag_store.create_commit already returns the new commit's id as a
        # plain str (not a Commit object), so it's used directly here rather
        # than accessed via a `.id` attribute.
        commit_id = create_commit(
            self.session, self.artifact_id, blob_hash, parent_ids, author, message
        )
        return commit_id

    def branch(self, name: str, from_ref: str) -> None:
        commit_id = self._resolve_commit_id(from_ref)
        create_branch(self.session, self.artifact_id, name, commit_id)

    def get_content(self, ref: str) -> str:
        commit_id = self._resolve_commit_id(ref)
        commit = get_commit(self.session, commit_id)
        return get_blob_content(self.session, commit.blob_hash)

    def branch_head(self, name: str) -> str:
        return get_branch_head(self.session, self.artifact_id, name)

    def _resolve_commit_id(self, ref: str) -> str:
        # `ref` may be a branch name or a direct commit id. Try it as a
        # branch name first; if no such branch exists on this artifact, fall
        # back to treating it as a commit id directly.
        branch_head_id = get_branch_head(self.session, self.artifact_id, ref)
        if branch_head_id is not None:
            return branch_head_id
        return ref
