from app.versioning.merge_engine import diff3_merge


def test_diff3_merge_non_overlapping_changes():
    base_tokens = [
        "Paragraph one original.",
        "Paragraph two original.",
        "Paragraph three original.",
    ]
    ours_tokens = [
        "Paragraph one changed by ours.",
        "Paragraph two original.",
        "Paragraph three original.",
    ]
    theirs_tokens = [
        "Paragraph one original.",
        "Paragraph two original.",
        "Paragraph three changed by theirs.",
    ]
    result = diff3_merge(base_tokens, ours_tokens, theirs_tokens)
    assert result["merged_tokens"] == [
        "Paragraph one changed by ours.",
        "Paragraph two original.",
        "Paragraph three changed by theirs.",
    ]
    assert result["conflicts"] == []
