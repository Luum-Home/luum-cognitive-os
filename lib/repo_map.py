# SCOPE: both
"""W3-1 repo-map context selector.

Pattern-port of Aider's repo-map idea: build a compact, token-budgeted map of
relevant repository files/symbols, then overlay COS governance context. This is
first-party code; no Aider runtime dependency is required.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

CHARS_PER_TOKEN = 4
DEFAULT_BUDGET_TOKENS = 1200


@dataclass(frozen=True)
class RepoMapEntry:
    path: str
    symbols: list[str]
    score: float
    reason: str


@dataclass(frozen=True)
class RepoMapPacket:
    schema_version: str
    query: str
    code_symbols: list[RepoMapEntry]
    governance: dict[str, list[str]]
    tests: list[str]
    budget: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["code_symbols"] = [asdict(entry) for entry in self.code_symbols]
        return data


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) > 2}


def _git_files(root: Path) -> list[Path]:
    try:
        proc = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, check=False, timeout=10)
        if proc.returncode == 0:
            return [root / line for line in proc.stdout.splitlines() if line]
    except Exception:
        pass
    return [path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts]


def _symbols(path: Path) -> list[str]:
    if path.suffix != ".py":
        return []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.append(node.name)
    return sorted(found)[:20]


def _score(path: Path, rel: str, query_tokens: set[str], changed: set[str]) -> tuple[float, str]:
    path_tokens = _tokens(rel)
    symbols = _tokens(" ".join(_symbols(path)))
    overlap = len(query_tokens & (path_tokens | symbols))
    score = float(overlap)
    reason = "query_overlap" if overlap else "repository_prior"
    if rel in changed:
        score += 5.0
        reason = "changed_file"
    if any(part in {"hooks", "skills", "rules", "manifests"} for part in path.parts):
        score += 0.25
    return score, reason


def build_repo_map(root: str | Path, query: str, *, max_tokens: int = DEFAULT_BUDGET_TOKENS, changed_files: list[str] | None = None) -> RepoMapPacket:
    root_path = Path(root).resolve()
    query_tokens = _tokens(query)
    changed = {str(Path(item).as_posix()) for item in (changed_files or [])}
    candidates: list[RepoMapEntry] = []
    for path in _git_files(root_path):
        rel = path.relative_to(root_path).as_posix()
        if path.suffix not in {".py", ".sh", ".go", ".md", ".yaml", ".yml", ".json"}:
            continue
        if any(part.startswith(".") and part not in {".cognitive-os"} for part in Path(rel).parts):
            continue
        score, reason = _score(path, rel, query_tokens, changed)
        if score <= 0 and len(candidates) > 200:
            continue
        candidates.append(RepoMapEntry(rel, _symbols(path), score, reason))
    ranked = sorted(candidates, key=lambda row: (-row.score, row.path))
    selected: list[RepoMapEntry] = []
    used = 0
    for row in ranked:
        estimate = max(1, len(json.dumps(asdict(row), sort_keys=True)) // CHARS_PER_TOKEN)
        if selected and used + estimate > max_tokens:
            continue
        selected.append(row)
        used += estimate
        if used >= max_tokens:
            break
    governance = {
        "hooks": [entry.path for entry in selected if entry.path.startswith("hooks/")][:10],
        "skills": [entry.path for entry in selected if entry.path.startswith("skills/")][:10],
        "rules": [entry.path for entry in selected if entry.path.startswith("rules/")][:10],
        "manifests": [entry.path for entry in selected if entry.path.startswith("manifests/")][:10],
    }
    tests = [entry.path for entry in selected if entry.path.startswith("tests/")]
    return RepoMapPacket(
        schema_version="repo-map-context-selector/v1",
        query=query,
        code_symbols=selected,
        governance=governance,
        tests=tests,
        budget={"max_tokens": max_tokens, "estimated_tokens": used},
    )
