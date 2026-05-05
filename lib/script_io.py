"""Shared filesystem and JSON helpers for Cognitive OS scripts."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    """Read UTF-8-ish text and return an empty string when unavailable."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from path."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_or_empty(path: Path) -> dict[str, Any]:
    """Read a JSON object, returning an empty mapping on any read/parse error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable pretty JSON, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write stable pretty JSON beside the target file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_name = tmp.name
    Path(tmp_name).replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL records, preserving corrupt lines as explicit events."""
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"event": "corrupt-line", "raw": line})
    return events


def print_json_status(payload: dict[str, Any]) -> int:
    """Print stable JSON and return failure for payload status=fail."""
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") not in {"fail"} else 1


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML mapping from path."""
    import yaml

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded
