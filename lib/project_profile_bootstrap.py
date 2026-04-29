# SCOPE: both
"""Project profile bootstrap for early Cognitive OS sessions.

This module creates a local, editable project profile draft during the first
sessions of a project. It intentionally writes only to `.cognitive-os/` and does
not call Engram or any MCP tool from hooks. The artifact is source-linked,
sanitzed, and draft-only so memory/profile bootstrap improves future sessions
without silently changing runtime behavior.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.memory_scanner import MemoryScanner

PROFILE_DIR = Path(".cognitive-os") / "project-profile"
DRAFT_JSON = "draft.json"
DRAFT_MD = "draft.md"
MAX_BOOTSTRAP_SESSIONS = 3
BLOCKED_PATH_PARTS = {".env", "secrets", ".git"}
BLOCKED_SUFFIXES = {".key", ".pem"}

POSIX_HOME_RE = re.compile(r"/(?:Users|home)/[^/\s`'\"<>)]*(?:/[^\s`'\"<>)]*)?")
WINDOWS_HOME_RE = re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\\\s]+(?:\\\\[^\s`'\"<>)]*)?")


@dataclass(frozen=True)
class ProfileSource:
    type: str
    path: str
    session_id: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class ProfileEntry:
    id: str
    kind: str
    key: str
    value: str
    confidence: float
    status: str
    source: ProfileSource


@dataclass(frozen=True)
class ProfileConflict:
    key: str
    values: list[str]
    entry_ids: list[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sanitize_text(value: str, project_dir: Path) -> str:
    """Remove developer-specific absolute paths from persisted profile text."""
    text = str(value)
    try:
        root = str(project_dir.resolve())
        text = text.replace(root, "<project-root>")
    except OSError:
        pass
    home = os.path.expanduser("~")
    if home and home != "~":
        text = text.replace(home, "<developer-home>")
    text = POSIX_HOME_RE.sub("<developer-home>", text)
    text = WINDOWS_HOME_RE.sub("<developer-home>", text)
    return text


def _relative_path(path: Path, project_dir: Path) -> str:
    try:
        return path.resolve().relative_to(project_dir.resolve()).as_posix()
    except (OSError, ValueError):
        return sanitize_text(str(path), project_dir)


def _blocked_source(path: Path) -> bool:
    parts = set(path.parts)
    if parts.intersection(BLOCKED_PATH_PARTS):
        return True
    return path.suffix.lower() in BLOCKED_SUFFIXES


def _safe_entry(entry: ProfileEntry, project_dir: Path) -> ProfileEntry | None:
    if _blocked_source(Path(entry.source.path)):
        return None
    scanner = MemoryScanner()
    value = sanitize_text(entry.value, project_dir)
    source = ProfileSource(
        type=entry.source.type,
        path=sanitize_text(entry.source.path, project_dir),
        session_id=sanitize_text(entry.source.session_id, project_dir)
        if entry.source.session_id
        else None,
        line=entry.source.line,
    )
    candidate = ProfileEntry(
        id=entry.id,
        kind=entry.kind,
        key=entry.key,
        value=value,
        confidence=entry.confidence,
        status=entry.status,
        source=source,
    )
    scan_payload = json.dumps(asdict(candidate), sort_keys=True)
    if scanner.scan(scan_payload).blocked:
        return None
    return candidate


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def discover_sessions(project_dir: Path) -> list[dict[str, Any]]:
    """Return valid local session metadata records sorted by start time."""
    sessions_dir = project_dir / ".cognitive-os" / "sessions"
    records: list[dict[str, Any]] = []
    if not sessions_dir.is_dir():
        return records
    for meta_path in sessions_dir.glob("*/meta.json"):
        data = _read_json(meta_path)
        if not data or not data.get("session_id"):
            continue
        data["_meta_path"] = meta_path
        records.append(data)
    return sorted(records, key=lambda item: str(item.get("start_time", "")))


def _stack_entries(project_dir: Path) -> list[ProfileEntry]:
    probes = [
        ("go", "go.mod", 0.9),
        ("python", "pyproject.toml", 0.85),
        ("python", "requirements.txt", 0.75),
        ("node", "package.json", 0.85),
        ("container", "docker-compose.yml", 0.8),
        ("container", "docker-compose.yaml", 0.8),
        ("container", "Dockerfile", 0.75),
    ]
    entries: list[ProfileEntry] = []
    seen: set[str] = set()
    for value, rel, confidence in probes:
        path = project_dir / rel
        if not path.exists() or value in seen:
            continue
        seen.add(value)
        entries.append(
            ProfileEntry(
                id=f"stack-{value}",
                kind="stack",
                key=f"runtime.{value}",
                value=value,
                confidence=confidence,
                status="draft",
                source=ProfileSource(type="file", path=rel),
            )
        )
    return entries


def _session_entries(project_dir: Path, sessions: list[dict[str, Any]]) -> list[ProfileEntry]:
    if not sessions:
        return []
    latest = sessions[-1]
    meta_path = latest.get("_meta_path")
    rel = _relative_path(meta_path, project_dir) if isinstance(meta_path, Path) else ""
    return [
        ProfileEntry(
            id="workflow-session-bootstrap-count",
            kind="workflow",
            key="bootstrap_sessions_seen",
            value=str(len(sessions)),
            confidence=0.7,
            status="draft",
            source=ProfileSource(
                type="session",
                path=rel,
                session_id=str(latest.get("session_id", "")),
            ),
        )
    ]


def _prompt_metric_entries(project_dir: Path) -> list[ProfileEntry]:
    path = project_dir / ".cognitive-os" / "metrics" / "prompt-captures.jsonl"
    if not path.is_file():
        return []
    counts: dict[str, int] = {}
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    for line in lines[-50:]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        category = row.get("category") or row.get("prompt_category")
        if isinstance(category, str) and category:
            counts[category] = counts.get(category, 0) + 1
    entries: list[ProfileEntry] = []
    rel = _relative_path(path, project_dir)
    for category, count in sorted(counts.items()):
        entries.append(
            ProfileEntry(
                id=f"workflow-prompt-category-{re.sub(r'[^a-z0-9]+', '-', category.lower()).strip('-')}",
                kind="workflow",
                key=f"prompt_category.{re.sub(r'[^a-z0-9]+', '-', category.lower()).strip('-')}",
                value=f"{category} ({count})",
                confidence=0.55,
                status="draft",
                source=ProfileSource(type="metrics", path=rel),
            )
        )
    return entries


def detect_conflicts(entries: list[ProfileEntry]) -> list[ProfileConflict]:
    grouped: dict[str, dict[str, list[str]]] = {}
    for entry in entries:
        key = f"{entry.kind}:{entry.key}"
        grouped.setdefault(key, {}).setdefault(entry.value, []).append(entry.id)
    conflicts: list[ProfileConflict] = []
    for key, values in grouped.items():
        if len(values) <= 1:
            continue
        conflicts.append(
            ProfileConflict(
                key=key,
                values=sorted(values),
                entry_ids=sorted(entry_id for ids in values.values() for entry_id in ids),
            )
        )
    return conflicts


def build_project_profile_draft(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    sessions = discover_sessions(project_dir)
    raw_entries = [
        *_stack_entries(project_dir),
        *_session_entries(project_dir, sessions),
        *_prompt_metric_entries(project_dir),
    ]
    entries = [entry for entry in (_safe_entry(e, project_dir) for e in raw_entries) if entry]
    return {
        "schema_version": 1,
        "status": "draft",
        "generated_at": _utc_now(),
        "session_count": len(sessions),
        "bootstrap_window": {
            "max_sessions": MAX_BOOTSTRAP_SESSIONS,
            "active": len(sessions) <= MAX_BOOTSTRAP_SESSIONS,
        },
        "entries": [asdict(entry) for entry in entries],
        "conflicts": [asdict(conflict) for conflict in detect_conflicts(entries)],
        "notes": [
            "Draft-only artifact; review before turning entries into durable memory.",
            "Developer-specific absolute paths and blocked secret paths are sanitized or skipped.",
        ],
    }


def write_project_profile_draft(project_dir: Path, force: bool = False) -> Path | None:
    """Write `.cognitive-os/project-profile/draft.json` when bootstrap should run.

    Returns the draft path when written or already present, otherwise None.
    """
    project_dir = project_dir.resolve()
    draft_dir = project_dir / PROFILE_DIR
    draft_json = draft_dir / DRAFT_JSON
    sessions = discover_sessions(project_dir)
    if draft_json.exists() and len(sessions) > MAX_BOOTSTRAP_SESSIONS and not force:
        return draft_json
    if len(sessions) > MAX_BOOTSTRAP_SESSIONS and not force and draft_json.exists():
        return draft_json
    if len(sessions) > MAX_BOOTSTRAP_SESSIONS and not force:
        return None

    draft = build_project_profile_draft(project_dir)
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_json.write_text(json.dumps(draft, indent=2, sort_keys=True) + "\n")
    (draft_dir / DRAFT_MD).write_text(render_project_profile_markdown(draft))
    return draft_json


def render_project_profile_markdown(draft: dict[str, Any]) -> str:
    lines = [
        "# Project Profile Draft",
        "",
        "This draft is generated locally by Cognitive OS during early sessions.",
        "Review it before promoting any entry into durable memory.",
        "",
        f"- Status: `{draft.get('status', 'draft')}`",
        f"- Session count: `{draft.get('session_count', 0)}`",
        "",
        "## Entries",
        "",
    ]
    for entry in draft.get("entries", []):
        source = entry.get("source", {})
        lines.append(
            f"- `{entry.get('kind')}:{entry.get('key')}` = "
            f"{entry.get('value')} "
            f"(confidence {entry.get('confidence')}, source `{source.get('path')}`)"
        )
    if not draft.get("entries"):
        lines.append("- No profile signals detected yet.")
    lines.extend(["", "## Conflicts", ""])
    for conflict in draft.get("conflicts", []):
        lines.append(f"- `{conflict.get('key')}` has values: {', '.join(conflict.get('values', []))}")
    if not draft.get("conflicts"):
        lines.append("- None detected.")
    lines.append("")
    return "\n".join(lines)


def wipe_project_profile(project_dir: Path) -> None:
    shutil.rmtree(project_dir / PROFILE_DIR, ignore_errors=True)
