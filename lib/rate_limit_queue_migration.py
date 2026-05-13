# SCOPE: os-only
"""Migration helper: legacy rate-limit-queue.json → JSONL append-only format.

This module exposes the on-boot migration logic that ``RateLimitQueue.__init__``
calls automatically.  It is also importable as a standalone utility for scripts
and tests that need to drive the migration explicitly.

Migration semantics
-------------------
1. If ``<state_path>`` (the old ``.json`` file) does NOT exist → no-op.
2. If ``<jsonl_path>`` (the new ``.jsonl`` file) already exists → no-op
   (migration already ran; we must not duplicate events).
3. Otherwise: read the JSON array, emit one ``queued`` event per item to the
   JSONL file, rename the old JSON file to ``<state_path>.deprecated``, and
   append a ``migration`` audit event.

The function is idempotent: calling it twice on the same paths is safe because
condition (2) prevents any work on the second call.

Usage
-----
    from lib.rate_limit_queue_migration import migrate_queue_on_boot

    migrated = migrate_queue_on_boot(
        json_path=".cognitive-os/rate-limit-queue.json",
        jsonl_path=".cognitive-os/rate-limit-queue.jsonl",
    )
    # migrated == number of entries ported to JSONL (0 if nothing to migrate)

Python 3.9+ compatible. Author: luum.
"""

from __future__ import annotations

import os
from typing import Optional

# Re-export the canonical implementation from rate_limiter so callers have
# a single import target.
from lib.rate_limiter import _migrate_legacy_json, _derive_jsonl_path  # noqa: F401


def migrate_queue_on_boot(
    json_path: Optional[str] = None,
    jsonl_path: Optional[str] = None,
) -> int:
    """Run the legacy JSON → JSONL migration for the default queue paths.

    Args:
        json_path:  Path to the legacy ``.json`` queue file.
                    Defaults to ``.cognitive-os/rate-limit-queue.json``.
        jsonl_path: Destination ``.jsonl`` event-log path.
                    Defaults to the path derived from ``json_path`` via
                    ``_derive_jsonl_path()``.

    Returns:
        Number of entries migrated (0 if migration was not needed or had
        nothing to migrate).
    """
    if json_path is None:
        json_path = ".cognitive-os/rate-limit-queue.json"
    if jsonl_path is None:
        jsonl_path = _derive_jsonl_path(json_path)
    return _migrate_legacy_json(json_path, jsonl_path)


def migration_status(
    json_path: Optional[str] = None,
    jsonl_path: Optional[str] = None,
) -> dict:
    """Return a dict describing the current migration state.

    Keys:
        ``json_exists``      — whether the legacy JSON file is present
        ``jsonl_exists``     — whether the new JSONL event log exists
        ``deprecated_exists``— whether the deprecated backup exists
        ``needs_migration``  — True if json exists but jsonl does not
        ``already_migrated`` — True if both json.deprecated and jsonl exist
    """
    if json_path is None:
        json_path = ".cognitive-os/rate-limit-queue.json"
    if jsonl_path is None:
        jsonl_path = _derive_jsonl_path(json_path)
    deprecated_path = json_path + ".deprecated"
    return {
        "json_exists": os.path.exists(json_path),
        "jsonl_exists": os.path.exists(jsonl_path),
        "deprecated_exists": os.path.exists(deprecated_path),
        "needs_migration": os.path.exists(json_path) and not os.path.exists(jsonl_path),
        "already_migrated": os.path.exists(deprecated_path) and os.path.exists(jsonl_path),
    }
