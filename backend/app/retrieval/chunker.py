import tree_sitter_python
from tree_sitter import Language, Parser

from app.versioning.diff_engine import tokenize_paragraphs, tokenize_messages

_PYTHON_LANGUAGE = Language(tree_sitter_python.language())
_TOP_LEVEL_NODE_TYPES = ("function_definition", "class_definition")


def chunk_prose(text: str) -> list[str]:
    return tokenize_paragraphs(text)


def chunk_messages(content_json: str) -> list[str]:
    return tokenize_messages(content_json)


def _extract_python_chunks(filename: str, source: str) -> list[tuple[str, str]]:
    parser = Parser(_PYTHON_LANGUAGE)
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    chunks: list[tuple[str, str]] = []
    for node in tree.root_node.children:
        if node.type not in _TOP_LEVEL_NODE_TYPES:
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None:
            continue
        name = source_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
        text = source_bytes[node.start_byte : node.end_byte].decode("utf-8")
        chunks.append((f"{filename}::{name}", text))
    return chunks


def chunk_code(files: dict[str, str]) -> list[tuple[str, str]]:
    all_chunks: list[tuple[str, str]] = []
    for filename, source in files.items():
        if filename.endswith(".py"):
            all_chunks.extend(_extract_python_chunks(filename, source))
        else:
            all_chunks.append((filename, source))
    return all_chunks
