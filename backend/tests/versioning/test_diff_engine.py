import json

from app.versioning.diff_engine import tokenize_messages, tokenize_paragraphs


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
