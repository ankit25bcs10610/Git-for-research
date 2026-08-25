import os

import pygit2

_STATUS_MAP = {
    pygit2.GIT_DELTA_ADDED: "added",
    pygit2.GIT_DELTA_DELETED: "removed",
    pygit2.GIT_DELTA_MODIFIED: "modified",
}

ARTIFACT_STORE_PATH = os.environ.get("ARTIFACT_STORE_PATH", "/data/artifacts")


def repo_path_for_artifact(artifact_id: str) -> str:
    return os.path.join(ARTIFACT_STORE_PATH, artifact_id)


def init_repo_from_files(repo_path: str, files: dict, author: str = "system") -> None:
    os.makedirs(repo_path, exist_ok=True)
    repo = pygit2.init_repository(repo_path)
    for path, content in files.items():
        full_path = os.path.join(repo_path, path)
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    index = repo.index
    index.add_all()
    index.write()
    tree = index.write_tree()
    signature = pygit2.Signature(author, f"{author}@local")
    repo.create_commit("HEAD", signature, signature, "initial commit", tree, [])


def clone_repo(source_path_or_url: str, dest_path: str) -> None:
    pygit2.clone_repository(source_path_or_url, dest_path)


class GitVersionedArtifact:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo = pygit2.Repository(repo_path)

    def commit(self, files, author: str, message: str) -> str:
        if files is not None:
            for path, text in files.items():
                full_path = os.path.join(self.repo_path, path)
                if os.path.dirname(path):
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(text)
        index = self.repo.index
        index.add_all()
        index.write()
        tree = index.write_tree()
        signature = pygit2.Signature(author, f"{author}@local")
        parents = [] if self.repo.head_is_unborn else [self.repo.head.target]
        ref_name = "HEAD" if self.repo.head_is_unborn else self.repo.head.name
        new_commit_id = self.repo.create_commit(
            ref_name, signature, signature, message, tree, parents
        )
        return str(new_commit_id)

    def _resolve_commit(self, ref: str):
        branch = self.repo.branches.local.get(ref)
        if branch is not None:
            return self.repo[branch.target]
        return self.repo[pygit2.Oid(hex=ref)]

    def diff(self, ref_a: str, ref_b: str) -> list:
        commit_a = self._resolve_commit(ref_a)
        commit_b = self._resolve_commit(ref_b)
        tree_diff = self.repo.diff(commit_a.tree, commit_b.tree)
        results = []
        for patch in tree_diff.deltas:
            status = _STATUS_MAP.get(patch.status, "modified")
            path = patch.new_file.path if patch.new_file.path else patch.old_file.path
            results.append({"path": path, "status": status})
        return results

    def branch(self, name: str, from_ref: str) -> None:
        commit = self._resolve_commit(from_ref)
        self.repo.branches.local.create(name, commit)

    def branch_head(self, name: str) -> str:
        branch_ref = self.repo.branches.local[name]
        return str(branch_ref.target)

    def list_branches(self) -> list:
        return list(self.repo.branches.local)

    def merge_base(self, ref_a: str, ref_b: str) -> str:
        commit_a = self._resolve_commit(ref_a)
        commit_b = self._resolve_commit(ref_b)
        return str(self.repo.merge_base(commit_a.id, commit_b.id))

    def checkout_branch(self, name: str) -> None:
        branch_ref = self.repo.branches.local[name]
        self.repo.set_head(branch_ref.name)
        self.repo.checkout(branch_ref, strategy=pygit2.GIT_CHECKOUT_FORCE)

    def get_content(self, ref: str) -> dict:
        commit = self._resolve_commit(ref)
        result = {}

        def walk(tree, prefix=""):
            for entry in tree:
                full_path = prefix + entry.name
                obj = self.repo[entry.id]
                if isinstance(obj, pygit2.Tree):
                    walk(obj, full_path + "/")
                else:
                    result[full_path] = obj.data.decode("utf-8")

        walk(commit.tree)
        return result

    def _merge_index_and_conflicts(self, base_ref: str, ours_ref: str, theirs_ref: str):
        base_commit = self._resolve_commit(base_ref)
        ours_commit = self._resolve_commit(ours_ref)
        theirs_commit = self._resolve_commit(theirs_ref)

        merge_index = self.repo.merge_trees(base_commit.tree, ours_commit.tree, theirs_commit.tree)

        conflicts = []
        if merge_index.conflicts is not None:
            for ancestor, ours, theirs in merge_index.conflicts:
                path = None
                ours_text = None
                theirs_text = None
                base_text = None
                if ours is not None:
                    path = ours.path
                    ours_text = self.repo[ours.id].data.decode("utf-8")
                if theirs is not None:
                    path = path or theirs.path
                    theirs_text = self.repo[theirs.id].data.decode("utf-8")
                if ancestor is not None:
                    path = path or ancestor.path
                    base_text = self.repo[ancestor.id].data.decode("utf-8")
                conflicts.append(
                    {
                        "path": path,
                        "ours": ours_text,
                        "theirs": theirs_text,
                        "base": base_text,
                    }
                )
        return merge_index, ours_commit, theirs_commit, conflicts

    def preview_merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> dict:
        # Read-only: merge_trees() computes an in-memory index and never
        # touches the repo's refs/working tree, so this is safe to call
        # without committing or moving any branch.
        _, _, _, conflicts = self._merge_index_and_conflicts(base_ref, ours_ref, theirs_ref)
        return {"conflicts": conflicts}

    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str, resolutions: dict = None) -> dict:
        merge_index, ours_commit, theirs_commit, conflicts = self._merge_index_and_conflicts(
            base_ref, ours_ref, theirs_ref
        )

        if conflicts:
            conflict_paths = {c["path"] for c in conflicts}
            if resolutions is None or set(resolutions.keys()) != conflict_paths:
                return {"merged": False, "conflicts": conflicts}
            for path, resolved_text in resolutions.items():
                del merge_index.conflicts[path]
                blob_oid = self.repo.create_blob(resolved_text.encode("utf-8"))
                merge_index.add(pygit2.IndexEntry(path, blob_oid, pygit2.GIT_FILEMODE_BLOB))

        merge_tree_id = merge_index.write_tree(self.repo)
        signature = pygit2.Signature("system", "system@local")
        merge_commit_id = self.repo.create_commit(
            None,
            signature,
            signature,
            f"merge {theirs_ref} into {ours_ref}",
            merge_tree_id,
            [ours_commit.id, theirs_commit.id],
        )
        ours_branch = self.repo.branches.local.get(ours_ref)
        if ours_branch is not None:
            ours_branch.set_target(merge_commit_id)
            self.checkout_branch(ours_ref)
        return {"merged": True, "conflicts": []}
