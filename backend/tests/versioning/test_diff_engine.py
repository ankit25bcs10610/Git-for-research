from app.versioning.diff_engine import tokenize_paragraphs


def test_tokenize_paragraphs_splits_three_paragraphs():
    text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
    assert tokenize_paragraphs(text) == [
        "First paragraph here.",
        "Second paragraph here.",
        "Third paragraph here.",
    ]
