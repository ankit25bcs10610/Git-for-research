"""Common interface unifying the custom DAG and git-backed versioning engines.

Both DagVersionedArtifact (docs, chat exports, PDFs) and a future
GitVersionedArtifact (codebase artifacts) implement this same interface so
ingestion, retrieval, provenance, multi-agent PRs, and the UI can call
commit(), diff(), branch(), merge(), get_content(), and branch_head() without
knowing which backend a given artifact uses.

This is defined as a typing.Protocol rather than an abc.ABC on purpose: a
Protocol is structural (isinstance checks work off matching method names, not
explicit inheritance) and, unlike an ABC with @abstractmethod, subclassing it
directly does not block instantiation of a class that only implements some of
the methods so far. That property is relied on while DagVersionedArtifact is
built up incrementally, method by method, in the tests below.
"""

from typing import Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class VersionedArtifact(Protocol):
    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        ...

    def diff(self, ref_a: str, ref_b: str) -> List[Dict]:
        ...

    def branch(self, name: str, from_ref: str) -> None:
        ...

    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> Dict:
        ...

    def get_content(self, ref: str) -> str:
        ...

    def branch_head(self, name: str) -> str:
        ...
