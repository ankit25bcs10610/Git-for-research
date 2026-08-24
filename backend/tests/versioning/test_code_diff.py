from app.versioning.code_diff import structural_diff


def test_structural_diff_detects_added_function():
    old_code = "def foo():\n    return 1\n"
    new_code = "def foo():\n    return 1\n\n\ndef baz():\n    return 3\n"

    result = structural_diff(old_code, new_code, "python")

    assert result == [
        {"node_type": "function_definition", "name": "baz", "status": "added"}
    ]


def test_structural_diff_detects_removed_function():
    old_code = "def foo():\n    return 1\n\n\ndef bar():\n    return 2\n"
    new_code = "def foo():\n    return 1\n"

    result = structural_diff(old_code, new_code, "python")

    assert result == [
        {"node_type": "function_definition", "name": "bar", "status": "removed"}
    ]


def test_structural_diff_detects_modified_removed_and_added_functions():
    old_code = "def foo():\n    return 1\n\n\ndef bar():\n    return 2\n"
    new_code = "def foo():\n    return 999\n\n\ndef baz():\n    return 3\n"

    result = structural_diff(old_code, new_code, "python")
    result_by_name = {entry["name"]: entry for entry in result}

    assert len(result) == 3
    assert result_by_name["foo"] == {
        "node_type": "function_definition",
        "name": "foo",
        "status": "modified",
    }
    assert result_by_name["bar"] == {
        "node_type": "function_definition",
        "name": "bar",
        "status": "removed",
    }
    assert result_by_name["baz"] == {
        "node_type": "function_definition",
        "name": "baz",
        "status": "added",
    }
