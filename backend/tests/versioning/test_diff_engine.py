import json

from app.versioning.diff_engine import diff_tokens, diff_words, tokenize_messages, tokenize_paragraphs


def test_tokenize_paragraphs_splits_three_paragraphs():
    text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
    assert tokenize_paragraphs(text) == [
        "First paragraph here.",
        "Second paragraph here.",
        "Third paragraph here.",
    ]


def test_tokenize_messages_formats_role_and_text():
    content_json = json.dumps([
        {"role": "user", "text": "hello there", "ts": 1},
        {"role": "assistant", "text": "hi back", "ts": 2},
    ])
    assert tokenize_messages(content_json) == [
        "user: hello there",
        "assistant: hi back",
    ]


def test_diff_tokens_added_removed_and_changed():
    tokens_a = [
        "Intro paragraph.",
        "Middle paragraph one.",
        "Middle paragraph two.",
        "Closing paragraph.",
    ]
    tokens_b = [
        "Intro paragraph.",
        "Middle paragraph one changed.",
        "Closing paragraph.",
        "New appended paragraph.",
    ]
    result = diff_tokens(tokens_a, tokens_b)
    kinds = [entry["kind"] for entry in result]
    assert kinds == ["unchanged", "changed", "removed", "unchanged", "added"]


def test_diff_words_shows_added_and_removed_words():
    text_a = "the quick brown fox jumps over the lazy dog"
    text_b = "the quick brown fox jumps swiftly over the dog"
    result = diff_words(text_a, text_b)
    kinds = [entry["kind"] for entry in result]
    assert "added" in kinds
    assert "removed" in kinds
