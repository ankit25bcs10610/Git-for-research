import difflib
import json
import re


def tokenize_paragraphs(text: str) -> list[str]:
    raw_tokens = re.split(r"\n\s*\n", text)
    return [token.strip() for token in raw_tokens if token.strip()]


def tokenize_messages(content_json: str) -> list[str]:
    messages = json.loads(content_json)
    return [f"{message['role']}: {message['text']}" for message in messages]


def diff_tokens(tokens_a: list[str], tokens_b: list[str]) -> list[dict]:
    matcher = difflib.SequenceMatcher(a=tokens_a, b=tokens_b, autojunk=False)
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for token in tokens_a[i1:i2]:
                result.append({"kind": "unchanged", "text": token, "old_text": None})
        elif tag == "delete":
            for token in tokens_a[i1:i2]:
                result.append({"kind": "removed", "text": token, "old_text": None})
        elif tag == "insert":
            for token in tokens_b[j1:j2]:
                result.append({"kind": "added", "text": token, "old_text": None})
        elif tag == "replace":
            old_tokens = tokens_a[i1:i2]
            new_tokens = tokens_b[j1:j2]
            pair_count = min(len(old_tokens), len(new_tokens))
            for index in range(pair_count):
                result.append({
                    "kind": "changed",
                    "text": new_tokens[index],
                    "old_text": old_tokens[index],
                })
            for token in old_tokens[pair_count:]:
                result.append({"kind": "removed", "text": token, "old_text": None})
            for token in new_tokens[pair_count:]:
                result.append({"kind": "added", "text": token, "old_text": None})
    return result


def diff_words(text_a: str, text_b: str) -> list[dict]:
    words_a = text_a.split()
    words_b = text_b.split()
    return diff_tokens(words_a, words_b)
