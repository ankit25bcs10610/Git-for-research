import pytest

from app.versioning.interface import VersionedArtifact


def test_versioned_artifact_protocol_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        VersionedArtifact()


def test_object_implementing_all_methods_satisfies_the_protocol():
    class CompleteArtifact:
        def commit(self, content, author, message, parent_ref):
            return "commit-1"

        def diff(self, ref_a, ref_b):
            return []

        def branch(self, name, from_ref):
            return None

        def merge(self, base_ref, ours_ref, theirs_ref):
            return {"conflicts": [], "merged": []}

        def get_content(self, ref):
            return "content"

        def branch_head(self, name):
            return "commit-1"

    assert isinstance(CompleteArtifact(), VersionedArtifact)


def test_object_missing_a_method_does_not_satisfy_the_protocol():
    class IncompleteArtifact:
        def commit(self, content, author, message, parent_ref):
            return "commit-1"

    assert not isinstance(IncompleteArtifact(), VersionedArtifact)
