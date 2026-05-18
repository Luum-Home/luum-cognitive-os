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

The adapter detects every harness that exposes a compatible Stop-event hook
surface. Claude Code and Codex registrations are currently probed directly;
harnesses without a compatible Stop analogue report status-only or unsupported.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

# Enforcement level literals — must match the strings used in cos_goal.py doctor.
EnforcementLevel = Literal["native-stop-hook", "status-only", "unsupported"]


def _check_stop_hooks_for_gate(stop_hooks: list) -> bool:
    """Return True if goal-stop-gate.sh appears in any Stop hook entry."""
    for entry in stop_hooks:
        if isinstance(entry, dict):
            # Group format: {"matcher": "...", "hooks": [...]}
            nested = entry.get("hooks", [])
            for hook in nested:
                cmd = hook if isinstance(hook, str) else hook.get("command", "")
                if "goal-stop-gate" in cmd:
                    return True
            # Also check flat command key on entry itself
            if "goal-stop-gate" in entry.get("command", ""):
                return True
        elif isinstance(entry, str) and "goal-stop-gate" in entry:
            return True
    return False


def detect_enforcement_level(project_dir: Path | None = None) -> dict[str, Any]:
    """Return a dict describing the current harness Stop-hook support level.

    Checks for ``goal-stop-gate.sh`` in Claude Code settings.json Stop hooks
    AND in Codex .codex/hooks.json Stop event registrations.

    Args:
        project_dir: Project root to resolve settings files. Defaults to cwd.

    Returns:
        Dict with at minimum:
          support_level: "native-stop-hook" | "status-only" | "unsupported"
          hook_registered: bool  (True if registered in ANY harness)
          enforcement: str (human-readable status)
          claude_code: bool  (True if registered in Claude Code settings.json)
          codex: bool  (True if registered in .codex/hooks.json)
          active_any: bool  (True if registered in at least one harness)
    """
    root = project_dir or Path(
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or Path.cwd()
    )

    claude_code_registered = False
    claude_code_settings_file: str | None = None

    # --- Claude Code: probe .claude/settings.json and .claude/settings.local.json ---
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
        stop_hooks = data.get("hooks", {}).get("Stop", [])
        if _check_stop_hooks_for_gate(stop_hooks):
            claude_code_registered = True
            claude_code_settings_file = str(path)
            break

    # --- Codex: probe .codex/hooks.json Stop event registrations ---
    codex_registered = False
    codex_hooks_file: str | None = None
    codex_hooks_path = root / ".codex" / "hooks.json"
    if codex_hooks_path.exists():
        try:
            data = json.loads(codex_hooks_path.read_text(encoding="utf-8"))
            stop_hooks = data.get("Stop", [])
            if _check_stop_hooks_for_gate(stop_hooks):
                codex_registered = True
                codex_hooks_file = str(codex_hooks_path)
        except (json.JSONDecodeError, OSError):
            pass

    active_any = claude_code_registered or codex_registered

    if active_any:
        harnesses = []
        if claude_code_registered:
            harnesses.append("claude-code")
        if codex_registered:
            harnesses.append("codex")
        return {
            "support_level": "native-stop-hook",
            "hook_registered": True,
            "enforcement": "active",
            "claude_code": claude_code_registered,
            "codex": codex_registered,
            "active_any": True,
            "harness": "+".join(harnesses),
            **({"settings_file": claude_code_settings_file} if claude_code_settings_file else {}),
            **({"codex_hooks_file": codex_hooks_file} if codex_hooks_file else {}),
        }

    # Hook file exists but not registered in any harness → status-only
    hook_path = root / "hooks" / "goal-stop-gate.sh"
    if hook_path.exists():
        return {
            "support_level": "status-only",
            "hook_registered": False,
            "enforcement": "unavailable — hook exists but not registered in settings.json or .codex/hooks.json",
            "hook_path": str(hook_path),
            "claude_code": False,
            "codex": False,
            "active_any": False,
            "harness": "none",
        }

    # No hook at all
    return {
        "support_level": "unsupported",
        "hook_registered": False,
        "enforcement": "unavailable — goal-stop-gate.sh not found",
        "claude_code": False,
        "codex": False,
        "active_any": False,
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
