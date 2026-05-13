"""Behavioral tests for lib.targeted_test_resolver.

Mutation-safe: each test exercises return values, not just file existence.
"""
from __future__ import annotations


import pytest

from lib.targeted_test_resolver import resolve_tests_for_changes


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Create a minimal project structure under tmp_path."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # Create some source + test files
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "foo.py").write_text("x=1\n")
    (tmp_path / "lib" / "unused.py").write_text("x=1\n")  # no tests

    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "bar.sh").write_text("#!/bin/bash\n")

    (tmp_path / "packages" / "p1" / "lib").mkdir(parents=True)
    (tmp_path / "packages" / "p1" / "lib" / "baz.py").write_text("x=1\n")

    tests_unit = tmp_path / "tests" / "unit"
    tests_unit.mkdir(parents=True)
    (tests_unit / "test_foo.py").write_text("def test_x(): pass\n")
    (tests_unit / "test_baz.py").write_text("def test_x(): pass\n")

    tests_hooks = tmp_path / "tests" / "hooks"
    tests_hooks.mkdir(parents=True)
    (tests_hooks / "test_bar.py").write_text("def test_x(): pass\n")

    return tmp_path


def test_lib_py_resolves_to_unit_test(tmp_project):
    result = resolve_tests_for_changes(["lib/foo.py"])
    assert "tests/unit/test_foo.py" in result


def test_package_lib_py_resolves_to_unit_test(tmp_project):
    result = resolve_tests_for_changes(["packages/p1/lib/baz.py"])
    assert "tests/unit/test_baz.py" in result


def test_hook_sh_resolves_to_hook_test(tmp_project):
    result = resolve_tests_for_changes(["hooks/bar.sh"])
    assert "tests/hooks/test_bar.py" in result


def test_missing_test_file_is_dropped(tmp_project):
    # lib/unused.py has no test — should produce empty result
    result = resolve_tests_for_changes(["lib/unused.py"])
    assert result == []


def test_test_file_itself_is_returned(tmp_project):
    result = resolve_tests_for_changes(["tests/unit/test_foo.py"])
    assert result == ["tests/unit/test_foo.py"]


def test_docs_changes_resolve_to_empty(tmp_project):
    (tmp_project / "docs").mkdir()
    (tmp_project / "docs" / "x.md").write_text("# x\n")
    result = resolve_tests_for_changes(["docs/x.md", "rules/y.md"])
    assert result == []


def test_deduplicates_multiple_changes_mapping_to_same_test(tmp_project):
    # If two source files map to the same test, it appears once
    result = resolve_tests_for_changes(["lib/foo.py", "lib/foo.py"])
    assert result.count("tests/unit/test_foo.py") == 1


def test_empty_input_returns_empty_list(tmp_project):
    assert resolve_tests_for_changes([]) == []
    assert resolve_tests_for_changes(["", "  ", None]) == []  # type: ignore[list-item]


def test_mixed_inputs_return_sorted_list(tmp_project):
    result = resolve_tests_for_changes(
        ["packages/p1/lib/baz.py", "lib/foo.py", "hooks/bar.sh"]
    )
    assert result == sorted(result)
    # All three real tests exist, so all three should resolve
    assert len(result) == 3


def test_returns_strings_relative_to_project_root(tmp_project):
    result = resolve_tests_for_changes(["lib/foo.py"])
    for p in result:
        assert not p.startswith("/"), f"expected relative path, got {p}"
        assert p.endswith(".py")
