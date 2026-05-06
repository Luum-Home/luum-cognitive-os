"""Regression test for removing the rejected coordination surface."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_first_party_tree_has_no_rejected_surface_references() -> None:
    root = Path(__file__).resolve().parents[2]
    token = "paper" + "clip"
    skipped_prefixes = (
        ".claude/plugins/",
        "dashboard/node_modules/",
    )
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    offenders: list[str] = []

    for relative_text in result.stdout.splitlines():
        if not relative_text or relative_text.startswith(skipped_prefixes):
            continue
        path = root / relative_text
        if not path.exists():
            continue
        if token in relative_text.lower():
            offenders.append(relative_text)
            continue
        if not path.is_file():
            continue
        try:
            content = path.read_text(errors="ignore")
        except OSError:
            continue
        if token in content.lower():
            offenders.append(relative_text)

    assert offenders == []
