# SCOPE: both
"""P5.1 — Engram-backed task claims: source-of-truth for task ownership.

Claim lifecycle
---------------
1. ``claim_task``   — session declares intent to work on a task.
2. ``find_claim``   — any session checks whether a task is already claimed.
3. ``complete_task``— session marks work done (upserts the same topic key).
4. ``release_claim``— session cancels without completing (e.g. on error/abort).

All writes use topic key ``claims/<task-id>`` so the claim is discoverable
by topic_key across all sessions.

Injection pattern for unit tests
---------------------------------
The module exposes ``_save_fn`` and ``_search_fn`` module-level variables that
default to the real engram binary wrappers.  Tests replace them::

    import engram_claims
    engram_claims._save_fn  = my_mock_save
    engram_claims._search_fn = my_mock_search

This keeps the public API free of DI boilerplate while remaining fully
testable without a live engram daemon.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Low-level engram wrappers (replaced in unit tests via module-level patching)
# ---------------------------------------------------------------------------

_ENGRAM_BIN = os.environ.get("ENGRAM_BIN", "engram")
_PROJECT = "luum-cognitive-os"


def _default_save_fn(
    title: str,
    content: str,
    *,
    type_: str = "architecture",
    topic_key: str = "",
    project: str = _PROJECT,
) -> dict[str, Any] | None:
    """Thin subprocess wrapper around current positional ``engram save``."""
    cmd = [_ENGRAM_BIN, "save", title, content, "--type", type_]
    if topic_key:
        cmd.extend(["--topic", topic_key])
    if project:
        cmd.extend(["--project", project])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return None
        output = proc.stdout.strip()
        if not output:
            return None
        match = re.search(r"Memory saved:\s+#(?P<id>\d+)", output)
        return {
            "id": int(match.group("id")) if match else None,
            "title": title,
            "content": content,
            "type": type_,
            "topic_key": topic_key,
            "project": project,
        }
    except Exception:
        return None


def _default_search_fn(
    query: str,
    *,
    limit: int = 5,
    project: str = _PROJECT,
) -> list[dict[str, Any]]:
    """Structured search via the Engram HTTP API when the daemon is available."""
    try:
        from lib import engram_http_client

        return engram_http_client.search_observations(query, limit=limit, project=project)[:limit]
    except Exception:
        return []


# Module-level function references — replace in tests to inject mocks.
_save_fn = _default_save_fn
_search_fn = _default_search_fn


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _topic_key(task_id: str) -> str:
    return f"claims/{task_id}"


def _title_for(task_id: str) -> str:
    return f"claim:{task_id}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def claim_task(
    task_id: str,
    session_id: str,
    *,
    expected_files: list[str] | None = None,
    fingerprint: str | None = None,
) -> dict[str, Any]:
    """Declare that *session_id* will work on *task_id*.

    If the task is already claimed by another *live* session the existing
    claim is returned unchanged.  If claimed by the same session the claim
    is refreshed (idempotent re-claim).

    Returns the claim record dict::

        {
            "task_id": str,
            "session_id": str,
            "claimed_at": ISO-8601,
            "expected_files": list[str] | None,
            "fingerprint": str | None,
            "status": "claimed",
        }
    """
    existing = find_claim(task_id)
    if existing and existing.get("session_id") != session_id:
        # Already owned by a different session — return it as-is so caller
        # can decide whether to wait or abort.
        return existing

    record: dict[str, Any] = {
        "task_id": task_id,
        "session_id": session_id,
        "claimed_at": _now_iso(),
        "expected_files": expected_files,
        "fingerprint": fingerprint,
        "status": "claimed",
    }
    _save_fn(
        _title_for(task_id),
        json.dumps(record),
        type_="architecture",
        topic_key=_topic_key(task_id),
        project=_PROJECT,
    )
    return record


def find_claim(task_id: str) -> dict[str, Any] | None:
    """Return the current claim for *task_id*, or ``None`` if unclaimed.

    Searches engram by topic key ``claims/<task_id>``.  Returns ``None`` when
    no observation exists or when engram is unavailable.
    """
    results = _search_fn(_topic_key(task_id), limit=3, project=_PROJECT)
    for obs in results:
        # Match on topic_key or content that parses to the right task_id.
        topic = obs.get("topic_key", "")
        if topic == _topic_key(task_id):
            content = obs.get("content", "")
            try:
                record = json.loads(content)
                if isinstance(record, dict) and record.get("task_id") == task_id:
                    return record
            except (json.JSONDecodeError, ValueError):
                continue
    # Fallback: parse content from any hit
    for obs in results:
        content = obs.get("content", "")
        try:
            record = json.loads(content)
            if isinstance(record, dict) and record.get("task_id") == task_id:
                return record
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def complete_task(
    task_id: str,
    session_id: str,
    evidence: str | dict[str, Any],
) -> dict[str, Any]:
    """Mark *task_id* as complete, upsertng the same topic key.

    *evidence* can be a string description or a dict of structured evidence
    (e.g. ``{"tests_passed": 12, "commit": "abc123"}``).

    Returns the updated claim record.
    """
    existing = find_claim(task_id) or {}
    record: dict[str, Any] = {
        **existing,
        "task_id": task_id,
        "completed_at": _now_iso(),
        "completed_by_session": session_id,
        "completion_evidence": evidence if isinstance(evidence, dict) else {"description": evidence},
        "status": "completed",
    }
    _save_fn(
        _title_for(task_id),
        json.dumps(record),
        type_="architecture",
        topic_key=_topic_key(task_id),
        project=_PROJECT,
    )
    return record


def release_claim(task_id: str, session_id: str) -> None:
    """Cancel a claim without completing the task.

    Only the owning session may release.  If the claim belongs to a different
    session (or does not exist) this is a silent no-op — the function never
    raises.
    """
    existing = find_claim(task_id)
    if not existing:
        return
    if existing.get("session_id") != session_id:
        return

    record: dict[str, Any] = {
        **existing,
        "task_id": task_id,
        "released_at": _now_iso(),
        "released_by_session": session_id,
        "status": "released",
    }
    _save_fn(
        _title_for(task_id),
        json.dumps(record),
        type_="architecture",
        topic_key=_topic_key(task_id),
        project=_PROJECT,
    )
