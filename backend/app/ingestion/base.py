from dataclasses import dataclass
from typing import Union


@dataclass
class ParsedArtifact:
    artifact_type: str
    name: str
    content: Union[str, dict]
