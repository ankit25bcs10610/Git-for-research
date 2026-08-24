from typing import Callable, Dict, List, Optional

from app.versioning.dag_store import (
    create_blob,
    create_branch,
    create_commit,
    get_blob_content,
    get_branch_head,
    get_commit,
)
from app.versioning.diff_engine import diff_tokens, diff_words, tokenize_paragraphs
from app.versioning.interface import VersionedArtifact
from app.versioning.merge_engine import diff3_merge


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

    def diff(self, ref_a: str, ref_b: str) -> List[Dict]:
        content_a = self.get_content(ref_a)
        content_b = self.get_content(ref_b)
        tokens_a = self.tokenizer(content_a)
        tokens_b = self.tokenizer(content_b)
        entries = diff_tokens(tokens_a, tokens_b)
        for entry in entries:
            # diff_tokens tags a replaced token's entry with kind="changed"
            # (not "type"/"change"); nest a word_diff on those entries only.
            if entry.get("kind") == "changed":
                entry["word_diff"] = diff_words(entry["old_text"], entry["text"])
        return entries

    def branch(self, name: str, from_ref: str) -> None:
        commit_id = self._resolve_commit_id(from_ref)
        create_branch(self.session, self.artifact_id, name, commit_id)

    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> Dict:
        base_content = self.get_content(base_ref)
        ours_content = self.get_content(ours_ref)
        theirs_content = self.get_content(theirs_ref)
        base_tokens = self.tokenizer(base_content)
        ours_tokens = self.tokenizer(ours_content)
        theirs_tokens = self.tokenizer(theirs_content)
        result = diff3_merge(base_tokens, ours_tokens, theirs_tokens)
        # Auto-committing the merge result is only supported when this
        # adapter tokenizes on paragraphs, because the paragraph tokenizer's
        # join separator ("\n\n") round-trips cleanly back into the original
        # text shape. When this adapter is wired up with the message
        # tokenizer instead, this method intentionally stops after
        # diff3_merge and hands the raw result back to the caller, which
        # resolves message merges through the merge_request UI rather than
        # an automatic commit.
        if len(result["conflicts"]) == 0 and self.tokenizer is tokenize_paragraphs:
            ours_commit_id = self._resolve_commit_id(ours_ref)
            theirs_commit_id = self._resolve_commit_id(theirs_ref)
            merged_content = "\n\n".join(result["merged_tokens"])
            blob_hash = create_blob(self.session, merged_content)
            # dag_store.create_commit returns the new commit's id directly as
            # a str, not an object with a `.id` attribute.
            merge_commit_id = create_commit(
                self.session,
                self.artifact_id,
                blob_hash,
                [ours_commit_id, theirs_commit_id],
                "merge-bot",
                f"Merge {theirs_ref} into {ours_ref}",
            )
            result["merge_commit_id"] = merge_commit_id
        return result

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
