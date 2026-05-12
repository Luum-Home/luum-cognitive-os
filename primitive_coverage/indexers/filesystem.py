from __future__ import annotations

from pathlib import Path
from typing import Iterable

IGNORED_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
IGNORED_PREFIXES = ("docs/06-Daily/reports/", "archive/")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def repo_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    rows: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file() and not path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            if any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
                continue
            if any(rel.startswith(prefix) for prefix in IGNORED_PREFIXES):
                continue
            rows[rel] = path
    return [rows[key] for key in sorted(rows)]
