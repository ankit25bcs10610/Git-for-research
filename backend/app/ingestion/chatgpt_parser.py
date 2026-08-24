import json
from typing import List, Optional

from app.ingestion.base import ParsedArtifact


def _find_root_id(mapping: dict) -> Optional[str]:
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            return node_id
    return None


def _walk_current_path(mapping: dict) -> list:
    current_id = _find_root_id(mapping)
    messages = []

    while current_id is not None:
        node = mapping[current_id]
        message = node.get("message")
        if message is not None:
            role = message["author"]["role"]
            text = "".join(message["content"]["parts"])
            messages.append(
                {
                    "role": role,
                    "text": text,
                    "ts": message["create_time"],
                }
            )
        children = node.get("children") or []
        current_id = children[-1] if children else None

    messages.sort(key=lambda entry: entry["ts"])
    return messages


def parse_chatgpt_export(json_bytes: bytes) -> List[ParsedArtifact]:
    conversations = json.loads(json_bytes.decode("utf-8"))
    artifacts = []

    for conversation in conversations:
        messages = _walk_current_path(conversation["mapping"])
        content = json.dumps(messages)
        artifacts.append(
            ParsedArtifact(
                artifact_type="chat",
                name=conversation["title"],
                content=content,
            )
        )

    return artifacts
