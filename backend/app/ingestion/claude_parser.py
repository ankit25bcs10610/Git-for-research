import json
from typing import List

from app.ingestion.base import ParsedArtifact

_SENDER_TO_ROLE = {
    "human": "user",
    "assistant": "assistant",
}


def parse_claude_export(json_bytes: bytes) -> List[ParsedArtifact]:
    conversations = json.loads(json_bytes.decode("utf-8"))
    artifacts = []

    for conversation in conversations:
        messages = []
        for chat_message in conversation["chat_messages"]:
            role = _SENDER_TO_ROLE[chat_message["sender"]]
            messages.append(
                {
                    "role": role,
                    "text": chat_message["text"],
                    "ts": chat_message["created_at"],
                }
            )
        content = json.dumps(messages)
        artifacts.append(
            ParsedArtifact(
                artifact_type="chat",
                name=conversation["name"],
                content=content,
            )
        )

    return artifacts
