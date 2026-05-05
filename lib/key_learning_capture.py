"""Capture assistant Key Learnings into self-improvement evidence."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECTION_RE = re.compile(r"^##\s+Key Learnings:?\s*$", re.IGNORECASE | re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)
ITEM_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+(.+?)\s*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def extract_key_learnings(markdown: str) -> list[str]:
    """Extract numbered/bulleted items from a Markdown Key Learnings section."""
    match = SECTION_RE.search(markdown)
    if not match:
        return []
    start = match.end()
    next_heading = NEXT_HEADING_RE.search(markdown, start)
    section = markdown[start : next_heading.start() if next_heading else len(markdown)]
    items: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("::"):
            continue
        item = ITEM_RE.match(line)
        if item:
            if current:
                items.append(" ".join(current).strip())
            current = [item.group(1).strip()]
        elif current and line.startswith((" ", "\t")):
            current.append(stripped)
    if current:
        items.append(" ".join(current).strip())
    return [item for item in items if item]


def classify_learning(text: str) -> dict[str, str]:
    lower = text.lower()
    if any(word in lower for word in ("adr", "decision", "deferred", "status")):
        artifact = "adr-or-plan"
    elif any(word in lower for word in ("test", "coverage", "pytest", "fixture")):
        artifact = "test"
    elif any(word in lower for word in ("script", "cli", "command", "hook")):
        artifact = "script-or-hook"
    elif any(word in lower for word in ("skill", "procedure", "workflow")):
        artifact = "skill"
    elif any(word in lower for word in ("manifest", "registry", "contract")):
        artifact = "manifest-or-contract"
    else:
        artifact = "documentation"

    if any(word in lower for word in ("must", "debe", "should", "conviene", "correcto", "evita", "avoid")):
        actionability = "candidate-improvement"
    elif any(word in lower for word in ("implemented", "quedó", "validated", "pusheado")):
        actionability = "evidence"
    else:
        actionability = "observation"
    return {"recommended_artifact": artifact, "actionability": actionability}


def learning_id(text: str, source: str) -> str:
    return hashlib.sha256(f"{source}\n{text}".encode("utf-8")).hexdigest()[:16]


def build_records(markdown: str, *, source: str, session_id: str = "unknown") -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    now = utc_now()
    for index, text in enumerate(extract_key_learnings(markdown), start=1):
        records.append(
            {
                "schema_version": "key-learning.v1",
                "id": learning_id(text, source),
                "timestamp": now,
                "session_id": session_id,
                "source": source,
                "ordinal": index,
                "text": text,
                **classify_learning(text),
            }
        )
    return records


def append_records(project_dir: Path, records: list[dict[str, Any]], *, path: Path | None = None) -> Path:
    out = path or project_dir / ".cognitive-os" / "metrics" / "key-learnings.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("id"):
                existing_ids.add(str(payload["id"]))
    with out.open("a", encoding="utf-8") as handle:
        for record in records:
            if record["id"] in existing_ids:
                continue
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return out
