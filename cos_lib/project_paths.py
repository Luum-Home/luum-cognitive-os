"""Shared project path helpers for Cognitive OS scripts."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def project_dir_from_env(raw: str | None = None) -> Path:
    """Resolve the active project directory from explicit value, COS env, or cwd."""
    value = raw or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(value).expanduser().resolve()


def project_dir_from_args(args: Any) -> Path:
    """Resolve project directory from an argparse namespace with project_dir."""
    return project_dir_from_env(getattr(args, "project_dir", None))


def repo_root_from_file(file: str | Path) -> Path:
    """Return repository root for a file in scripts/ or tests/."""
    return Path(file).resolve().parents[1]


def relpath(root: Path, path: Path) -> str:
    """Return POSIX repo-relative path."""
    return path.relative_to(root).as_posix()


def safe_relpath(root: Path, path: Path) -> str:
    """Return relative path when possible, otherwise the original path string."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
