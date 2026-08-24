import os

import pygit2


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
