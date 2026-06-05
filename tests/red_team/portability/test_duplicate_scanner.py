# SCOPE: os-only
from __future__ import annotations

from pathlib import Path

from lib.duplicate_scanner import collect_text_files, generic_function_repeats, lexical_pairs


def test_duplicate_scanner_runs_without_repo_cwd_or_external_tools(tmp_path: Path) -> None:
    left = tmp_path / "src" / "a.py"
    right = tmp_path / "src" / "b.py"
    left.parent.mkdir()
    left.write_text("def alpha():\n    value = 1\n    return value + 1\n", encoding="utf-8")
    right.write_text("def beta():\n    value = 1\n    return value + 1\n", encoding="utf-8")

    files = collect_text_files(
        tmp_path,
        ["src"],
        text_suffixes={".py"},
        exclude_parts={".git", "node_modules"},
        special_names=set(),
    )

    assert files == [left, right]
    assert lexical_pairs(tmp_path, files, min_tokens=4, shingle_size=2, threshold=0.5)
    assert generic_function_repeats(tmp_path, files, min_tokens=4)
