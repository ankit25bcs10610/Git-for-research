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


def test_diff3_merge_overlapping_changes_produce_conflict():
    base_tokens = [
        "Paragraph one original.",
        "Paragraph two original.",
        "Paragraph three original.",
    ]
    ours_tokens = [
        "Paragraph one original.",
        "Paragraph two changed by ours.",
        "Paragraph three original.",
    ]
    theirs_tokens = [
        "Paragraph one original.",
        "Paragraph two changed by theirs.",
        "Paragraph three original.",
    ]
    result = diff3_merge(base_tokens, ours_tokens, theirs_tokens)
    assert len(result["conflicts"]) == 1
    conflict = result["conflicts"][0]
    assert conflict["position"] == 1
    assert conflict["base"] == "Paragraph two original."
    assert conflict["ours"] == "Paragraph two changed by ours."
    assert conflict["theirs"] == "Paragraph two changed by theirs."
    # merged_tokens keeps a placeholder at the conflict's position so a caller
    # can resolve it later via merged_tokens[conflict["position"]] = resolved_text.
    assert result["merged_tokens"][conflict["position"]] == "Paragraph two original."
