import json
import re


def tokenize_paragraphs(text: str) -> list[str]:
    raw_tokens = re.split(r"\n\s*\n", text)
    return [token.strip() for token in raw_tokens if token.strip()]


def tokenize_messages(content_json: str) -> list[str]:
    messages = json.loads(content_json)
    return [f"{message['role']}: {message['text']}" for message in messages]
