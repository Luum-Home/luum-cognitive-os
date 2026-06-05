# SCOPE: os-only
"""Shared inventory of agentic primitive source files."""
from __future__ import annotations

from pathlib import Path

from lib.project_paths import relpath

SOURCE_ROOTS = ("hooks", "skills", "rules", "scripts", "templates", "packages")
IGNORED_PARTS = {".git", "__pycache__", ".venv", "node_modules"}


def is_text_file(path: Path) -> bool:
    if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
        return False
    try:
        path.read_text(encoding="utf-8", errors="ignore")[:128]
        return True
    except OSError:
        return False


def primitive_files(root: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for root_name in SOURCE_ROOTS:
        base = root / root_name
        if not base.exists():
            continue
        if root_name == "skills":
            for path in base.rglob("SKILL.md"):
                if is_text_file(path):
                    found[relpath(root, path)] = path
            continue
        if root_name == "packages":
            for path in base.glob("*/skills/*/SKILL.md"):
                if is_text_file(path):
                    found[relpath(root, path)] = path
            continue
        for path in base.rglob("*"):
            if is_text_file(path):
                found[relpath(root, path)] = path
    return [found[key] for key in sorted(found)]
