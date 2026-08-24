import re


def tokenize_paragraphs(text: str) -> list[str]:
    raw_tokens = re.split(r"\n\s*\n", text)
    return [token.strip() for token in raw_tokens if token.strip()]
