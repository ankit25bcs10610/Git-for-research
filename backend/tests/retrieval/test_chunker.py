import json

from app.versioning.diff_engine import tokenize_paragraphs, tokenize_messages
from app.retrieval.chunker import chunk_prose, chunk_messages


def test_chunk_prose_reuses_paragraph_tokenizer_and_produces_expected_count():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunk_prose(text)
    assert chunks == tokenize_paragraphs(text)
    assert len(chunks) == 3


def test_chunk_messages_reuses_message_tokenizer_and_produces_expected_count():
    content_json = json.dumps(
        [
            {"role": "user", "text": "Hello there"},
            {"role": "assistant", "text": "Hi, how can I help?"},
        ]
    )
    chunks = chunk_messages(content_json)
    assert chunks == tokenize_messages(content_json)
    assert len(chunks) == 2


from app.retrieval.chunker import chunk_code


def test_chunk_code_extracts_named_top_level_functions():
    files = {
        "utils.py": (
            "def foo():\n"
            "    return 1\n"
            "\n"
            "\n"
            "def bar():\n"
            "    return 2\n"
        )
    }
    chunks = chunk_code(files)
    assert len(chunks) == 2
    names = [name for name, _ in chunks]
    assert names == ["utils.py::foo", "utils.py::bar"]
    assert "return 1" in chunks[0][1]
    assert "return 2" in chunks[1][1]
