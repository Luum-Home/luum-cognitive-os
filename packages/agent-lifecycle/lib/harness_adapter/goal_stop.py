# SCOPE: os-only
"""Goal Stop harness adapter (ADR-064 + cos-native-goal-loop Phase 3).

Implements REQ-004 and REQ-012: provides a harness-agnostic abstraction for
Stop-hook enforcement of the COS-native goal loop.

Three enforcement levels are declared:
  native-stop-hook  — Stop hook is registered and can block continuation.
  status-only       — Goal state is inspectable; harness cannot block Stop.
  unsupported       — No runtime enforcement is possible or claimed.

This module is the canonical authority for determining enforcement level.
``scripts/cos_goal.py doctor`` and the stop-gate hook both delegate here.

The adapter is Claude Code-only in MVP. Stop hook registration is only
possible when the harness provides a Stop event, so other harnesses
(Codex, Bare-CLI) report status-only until they wire their own Stop analogue.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

# Enforcement level literals — must match the strings used in cos_goal.py doctor.
EnforcementLevel = Literal["native-stop-hook", "status-only", "unsupported"]


def detect_enforcement_level(project_dir: Path | None = None) -> dict[str, Any]:
    """Return a dict describing the current harness Stop-hook support level.

    Checks for ``goal-stop-gate.sh`` in Claude Code settings.json Stop hooks.
    Falls back gracefully when files are missing or unreadable.

    Args:
        project_dir: Project root to resolve settings.json. Defaults to cwd.

    Returns:
        Dict with at minimum:
          support_level: "native-stop-hook" | "status-only" | "unsupported"
          hook_registered: bool
          enforcement: str (human-readable status)
    """
    root = project_dir or Path(
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or Path.cwd()
    )

    settings_paths = [
        root / ".claude" / "settings.json",
        root / ".claude" / "settings.local.json",
    ]

    for path in settings_paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        hooks: dict = data.get("hooks", {})
        stop_hooks = hooks.get("Stop", [])

        for entry in stop_hooks:
            # Each entry can be a group dict with nested "hooks" list, or a
            # raw string/dict from older formats.
            if isinstance(entry, dict):
                # Group format: {"matcher": "...", "hooks": [...]}
                nested = entry.get("hooks", [])
                for hook in nested:
                    cmd = hook if isinstance(hook, str) else hook.get("command", "")
                    if "goal-stop-gate" in cmd:
                        return {
                            "support_level": "native-stop-hook",
                            "hook_registered": True,
                            "enforcement": "active",
                            "settings_file": str(path),
                            "harness": "claude-code",
                        }
                # Also check if entry itself has a command key (flat format)
                cmd = entry.get("command", "")
                if "goal-stop-gate" in cmd:
                    return {
                        "support_level": "native-stop-hook",
                        "hook_registered": True,
                        "enforcement": "active",
                        "settings_file": str(path),
                        "harness": "claude-code",
                    }
            elif isinstance(entry, str) and "goal-stop-gate" in entry:
                return {
                    "support_level": "native-stop-hook",
                    "hook_registered": True,
                    "enforcement": "active",
                    "settings_file": str(path),
                    "harness": "claude-code",
                }

    # Hook file exists but not registered → status-only
    hook_path = root / "hooks" / "goal-stop-gate.sh"
    if hook_path.exists():
        return {
            "support_level": "status-only",
            "hook_registered": False,
            "enforcement": "unavailable — hook exists but not registered in settings.json",
            "hook_path": str(hook_path),
            "harness": "claude-code",
        }

    # No hook at all
    return {
        "support_level": "unsupported",
        "hook_registered": False,
        "enforcement": "unavailable — goal-stop-gate.sh not found",
        "harness": "unknown",
    }


def parse_stop_event(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse a Claude Code Stop hook event payload.

    Claude Code Stop events have a minimal schema; the hook receives stdin JSON.
    Returns a normalised dict with at minimum:
      hook_event_name: str  (always "Stop")
      session_id: str | None
      stop_reason: str | None

    Args:
        raw: Parsed JSON dict from stdin.

    Returns:
        Normalised stop event dict.
    """
    return {
        "hook_event_name": raw.get("hook_event_name", "Stop"),
        "session_id": raw.get("session_id") or raw.get("CLAUDE_SESSION_ID"),
        "stop_reason": raw.get("stop_reason") or raw.get("reason"),
    }
