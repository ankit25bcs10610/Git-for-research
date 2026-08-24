import tree_sitter_python
from tree_sitter import Language, Node, Parser

_LANGUAGES = {
    "python": Language(tree_sitter_python.language()),
}

_DEFINITION_NODE_TYPES = ("function_definition", "class_definition")


def _get_parser(language: str) -> Parser:
    return Parser(_LANGUAGES[language])


def _extract_definitions(source: str, language: str) -> dict:
    parser = _get_parser(language)
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    definitions = {}

    def walk(node: Node) -> None:
        for child in node.children:
            if child.type in _DEFINITION_NODE_TYPES:
                name_node = child.child_by_field_name("name")
                if name_node is not None:
                    name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                    text = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                    definitions[name] = {"node_type": child.type, "text": text}
            walk(child)

    walk(tree.root_node)
    return definitions


def structural_diff(old_code: str, new_code: str, language: str) -> list:
    old_defs = _extract_definitions(old_code, language)
    new_defs = _extract_definitions(new_code, language)

    results = []
    for name, new_def in new_defs.items():
        if name not in old_defs:
            results.append(
                {"node_type": new_def["node_type"], "name": name, "status": "added"}
            )
        elif old_defs[name]["text"] != new_def["text"]:
            results.append(
                {"node_type": new_def["node_type"], "name": name, "status": "modified"}
            )

    for name, old_def in old_defs.items():
        if name not in new_defs:
            results.append(
                {"node_type": old_def["node_type"], "name": name, "status": "removed"}
            )

    return results
