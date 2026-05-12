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
    for raw in text.splitlines():
        line = raw.strip()
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
        value = value.split(" #", 1)[0].strip()
        parsed = _parse_value(value)
        cursor = data
        for part in section[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor = cursor.setdefault(section[-1], {})
        cursor[key] = parsed
    return data


def _parse_value(value: str) -> Any:
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value.strip('"\'')
