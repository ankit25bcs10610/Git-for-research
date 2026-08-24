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


def test_structural_diff_does_not_conflate_same_named_methods_in_different_classes():
    old_code = (
        "class A:\n"
        "    def __init__(self):\n"
        "        self.x = 1\n"
        "\n"
        "\n"
        "class B:\n"
        "    def __init__(self):\n"
        "        self.y = 2\n"
    )
    new_code = (
        "class A:\n"
        "    def __init__(self):\n"
        "        self.x = 999\n"
        "\n"
        "\n"
        "class B:\n"
        "    def __init__(self):\n"
        "        self.y = 2\n"
    )

    result = structural_diff(old_code, new_code, "python")

    # Only the top-level class A actually changed (its nested __init__ body
    # differs); class B is untouched. A buggy implementation that recurses
    # into class bodies would key both classes' __init__ methods under the
    # same "__init__" name and could report a spurious/ambiguous entry for
    # it, or silently drop which class actually changed.
    assert result == [
        {"node_type": "class_definition", "name": "A", "status": "modified"}
    ]


def test_structural_diff_reports_both_classes_when_both_same_named_methods_change():
    old_code = (
        "class A:\n"
        "    def __init__(self):\n"
        "        self.x = 1\n"
        "\n"
        "\n"
        "class B:\n"
        "    def __init__(self):\n"
        "        self.y = 2\n"
    )
    new_code = (
        "class A:\n"
        "    def __init__(self):\n"
        "        self.x = 999\n"
        "\n"
        "\n"
        "class B:\n"
        "    def __init__(self):\n"
        "        self.y = 999\n"
    )

    result = structural_diff(old_code, new_code, "python")
    result_by_name = {entry["name"]: entry for entry in result}

    # Both classes changed independently and must be reported as two
    # distinct entries, keyed by their own (module-level) class names -
    # never collapsed into a single ambiguous "__init__" entry.
    assert len(result) == 2
    assert "__init__" not in result_by_name
    assert result_by_name["A"] == {
        "node_type": "class_definition",
        "name": "A",
        "status": "modified",
    }
    assert result_by_name["B"] == {
        "node_type": "class_definition",
        "name": "B",
        "status": "modified",
    }
