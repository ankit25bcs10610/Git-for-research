import os

import pygit2

_STATUS_MAP = {
    pygit2.GIT_DELTA_ADDED: "added",
    pygit2.GIT_DELTA_DELETED: "removed",
    pygit2.GIT_DELTA_MODIFIED: "modified",
}


def init_repo_from_files(repo_path: str, files: dict) -> None:
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
    signature = pygit2.Signature("system", "system@local")
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
