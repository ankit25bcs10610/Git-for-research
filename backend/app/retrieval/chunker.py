from app.versioning.diff_engine import tokenize_paragraphs, tokenize_messages


def chunk_prose(text: str) -> list[str]:
    return tokenize_paragraphs(text)


def chunk_messages(content_json: str) -> list[str]:
    return tokenize_messages(content_json)
