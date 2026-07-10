# SCOPE: os-only
"""Shared helpers for repository maintenance scripts."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso_utc_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def naive_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_yaml_required(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_or(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_root(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return start.resolve()


def resolve_project_dir(arg: str | None) -> Path:
    import os

    if arg:
        return Path(arg).resolve()
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if env_var in os.environ:
            return Path(os.environ[env_var]).resolve()
    return Path.cwd().resolve()


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def emit_result(args: Any, payload: dict[str, object], human: str, ok: bool = True) -> int:
    if args.json:
        print(json.dumps({"ok": ok, **payload}, indent=2, sort_keys=True))
    else:
        print(human)
    return 0 if ok else 2


def object_map(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def object_maps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def run_git(repo: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, timeout=60)


def run_git_ls_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    return [p for p in proc.stdout.decode("utf-8", errors="ignore").split("\0") if p]


def is_probably_text(path: Path, suffixes: set[str]) -> bool:
    if path.suffix.lower() not in suffixes:
        return False
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\0" not in chunk


def shingles(tokens: list[str], n: int) -> set[str]:
    if len(tokens) < n:
        return set(tokens)
    return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def script_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
