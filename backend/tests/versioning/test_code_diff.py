from app.versioning.code_diff import structural_diff


def test_structural_diff_detects_added_function():
    old_code = "def foo():\n    return 1\n"
    new_code = "def foo():\n    return 1\n\n\ndef baz():\n    return 3\n"

    result = structural_diff(old_code, new_code, "python")

    assert result == [
        {"node_type": "function_definition", "name": "baz", "status": "added"}
    ]
