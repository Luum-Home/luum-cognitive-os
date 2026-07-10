"""Harness environment detection helpers."""
from __future__ import annotations

import os


def is_claude_code() -> bool:
    """Detect if the current process is running under Claude Code."""
    env = os.environ
    return bool(
        env.get("CLAUDE_PROJECT_DIR")
        or env.get("CLAUDE_SESSION_ID")
        or "claude" in env.get("USER_AGENT", "").lower()
    )
