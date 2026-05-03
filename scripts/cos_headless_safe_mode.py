#!/usr/bin/env python3
"""Local headless safe-mode primitive for Cognitive OS task admission.

Safe mode is a repair-first kill switch for unattended headless workers: when
it is enabled, new task admission is denied while existing runtime evidence,
artifacts, ledgers, and workspaces remain untouched.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_RELATIVE_PATH = Path(".cognitive-os") / "runtime" / "headless-safe-mode.json"
DEFAULT_REASON = "operator requested headless safe mode"
DISABLE_REASON = "operator disabled headless safe mode"


@dataclass(frozen=True)
class SafeModeState:
    """Current headless safe-mode state."""

    enabled: bool
    reason: str | None
    updated_at: str | None
    updated_by: str | None
    state_path: Path

    @property
    def admits_new_tasks(self) -> bool:
        """Return whether a headless worker may admit a new task."""
        return not self.enabled

    def to_dict(self) -> dict[str, Any]:
        """Return a stable machine-readable representation."""
        return {
            "safe_mode": self.enabled,
            "admits_new_tasks": self.admits_new_tasks,
            "reason": self.reason,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "state_path": str(self.state_path),
        }


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp with seconds precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_project_dir(raw_project_dir: str | None) -> Path:
    """Resolve the project directory using CLI, environment, git, then cwd."""
    candidate = (
        raw_project_dir
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
    )
    if candidate:
        return Path(candidate).expanduser().resolve()

    try:
        git_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        git_root = ""

    if git_root:
        return Path(git_root).resolve()

    return Path.cwd().resolve()


def state_path_for(project_dir: Path) -> Path:
    """Return the file path used for local headless safe-mode state."""
    return project_dir / STATE_RELATIVE_PATH


def read_state(project_dir: Path) -> SafeModeState:
    """Read state; a missing or malformed file fails closed for admission."""
    state_path = state_path_for(project_dir)
    if not state_path.exists():
        return SafeModeState(
            enabled=False,
            reason=None,
            updated_at=None,
            updated_by=None,
            state_path=state_path,
        )

    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SafeModeState(
            enabled=True,
            reason=f"safe-mode state unreadable: {exc}",
            updated_at=None,
            updated_by=None,
            state_path=state_path,
        )

    return SafeModeState(
        enabled=bool(raw.get("safe_mode", False)),
        reason=raw.get("reason"),
        updated_at=raw.get("updated_at"),
        updated_by=raw.get("updated_by"),
        state_path=state_path,
    )


def write_state(project_dir: Path, *, enabled: bool, reason: str) -> SafeModeState:
    """Atomically write safe-mode state without touching runtime artifacts."""
    path = state_path_for(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "safe_mode": enabled,
        "admits_new_tasks": not enabled,
        "reason": reason,
        "updated_at": utc_now(),
        "updated_by": getpass.getuser(),
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp_file:
        json.dump(payload, tmp_file, indent=2, sort_keys=True)
        tmp_file.write("\n")
        tmp_name = tmp_file.name

    Path(tmp_name).replace(path)
    return read_state(project_dir)


def format_human(state: SafeModeState) -> str:
    """Render safe-mode state for operators."""
    mode = "ENABLED" if state.enabled else "disabled"
    admission = "blocked" if state.enabled else "allowed"
    lines = [
        f"Headless safe mode: {mode}",
        f"New task admission: {admission}",
        f"State file: {state.state_path}",
    ]
    if state.reason:
        lines.append(f"Reason: {state.reason}")
    if state.updated_at:
        lines.append(f"Updated at: {state.updated_at}")
    if state.updated_by:
        lines.append(f"Updated by: {state.updated_by}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Manage Cognitive OS headless safe mode for task admission.",
    )
    parser.add_argument(
        "command",
        choices=("status", "enable", "disable"),
        help="status queries admission, enable blocks new tasks, disable allows new tasks",
    )
    parser.add_argument(
        "--project-dir",
        help="project root containing .cognitive-os; defaults to COS/Codex/Claude env or cwd",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--reason", help="operator reason for enable/disable")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the safe-mode CLI."""
    args = build_parser().parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)

    if args.command == "enable":
        state = write_state(
            project_dir,
            enabled=True,
            reason=args.reason or DEFAULT_REASON,
        )
    elif args.command == "disable":
        state = write_state(
            project_dir,
            enabled=False,
            reason=args.reason or DISABLE_REASON,
        )
    else:
        state = read_state(project_dir)

    if args.json:
        print(json.dumps(state.to_dict(), sort_keys=True))
    else:
        print(format_human(state))

    return 0


if __name__ == "__main__":
    sys.exit(main())
