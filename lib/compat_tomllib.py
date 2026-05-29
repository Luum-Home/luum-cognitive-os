# SCOPE: both
"""Small tomllib compatibility layer for Python 3.9 test lanes.

Prefers stdlib tomllib/tomli/toml when available. The fallback intentionally
supports only the repository's needed pyproject shape: [project] scalar name,
[project] dependencies arrays, and [project.optional-dependencies] arrays.
"""
from __future__ import annotations

import ast
from typing import Any

try:  # pragma: no cover - depends on runtime
    import tomllib as _tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - depends on runtime
    try:
        import tomli as _tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        _tomllib = None


def loads(text: str) -> dict[str, Any]:
    """Parse TOML text with a narrow built-in fallback for Python 3.9."""
    if _tomllib is not None:
        return _tomllib.loads(text)
    return _loads_minimal_pyproject(text)


def _loads_minimal_pyproject(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    section: list[str] = []
    pending_key: str | None = None
    pending_value: list[str] = []

    def commit_value(key: str, value_lines: list[str]) -> None:
        value = _strip_inline_comment("\n".join(value_lines).strip())
        parsed = _parse_value(value)
        cursor = data
        for part in section[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor = cursor.setdefault(section[-1], {})
        cursor[key] = parsed

    for raw in text.splitlines():
        line = raw.strip()
        if pending_key is not None:
            pending_value.append(raw)
            if _balanced_brackets("\n".join(pending_value)):
                commit_value(pending_key, pending_value)
                pending_key = None
                pending_value = []
            continue
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = [part.strip() for part in line[1:-1].split(".") if part.strip()]
            cursor = data
            for part in section:
                cursor = cursor.setdefault(part, {})
            continue
        if "=" not in line or not section:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if value.startswith("[") and not _balanced_brackets(value):
            pending_key = key
            pending_value = [value]
            continue
        commit_value(key, [value])
    if pending_key is not None:
        commit_value(pending_key, pending_value)
    return data


def _strip_inline_comment(value: str) -> str:
    lines: list[str] = []
    for raw in value.splitlines():
        in_quote: str | None = None
        escaped = False
        out: list[str] = []
        for char in raw:
            if escaped:
                out.append(char)
                escaped = False
                continue
            if char == "\\" and in_quote:
                out.append(char)
                escaped = True
                continue
            if char in {"'", '"'}:
                in_quote = None if in_quote == char else char if in_quote is None else in_quote
            if char == "#" and in_quote is None:
                break
            out.append(char)
        lines.append("".join(out).rstrip())
    return "\n".join(lines).strip()


def _balanced_brackets(value: str) -> bool:
    in_quote: str | None = None
    escaped = False
    depth = 0
    for char in value:
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_quote:
            escaped = True
            continue
        if char in {"'", '"'}:
            in_quote = None if in_quote == char else char if in_quote is None else in_quote
            continue
        if in_quote:
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
    return depth <= 0


def _parse_value(value: str) -> Any:
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value.strip('"\'')
