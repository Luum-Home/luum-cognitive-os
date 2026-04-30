#!/usr/bin/env python3
"""Add COS provenance trailers to commit messages.

Used by `.githooks/prepare-commit-msg`. The hook is intentionally local-only:
it records session/harness/kind metadata in the commit message so future audits
can distinguish manual, agent, hook, cron, and subagent commits.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

TRAILER_KEYS = ("X-COS-Origin", "X-COS-Session", "X-COS-Harness")


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def resolve_repo() -> Path:
    top = _run_git(["rev-parse", "--show-toplevel"])
    return Path(top) if top else Path.cwd()


def read_current_session(repo: Path) -> str:
    env_session = (
        os.environ.get("COS_COMMIT_SESSION_ID")
        or os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or ""
    )
    if env_session:
        return env_session
    sessions_dir = repo / ".cognitive-os" / "sessions"
    for marker in sorted(sessions_dir.glob(".current-session-*"), key=lambda path: path.stat().st_mtime, reverse=True):
        value = marker.read_text(errors="ignore").strip()
        if value:
            return value
    return "unknown"


def infer_harness() -> str:
    explicit = os.environ.get("COS_COMMIT_HARNESS") or os.environ.get("COGNITIVE_OS_HARNESS")
    if explicit:
        return explicit
    if os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_PROJECT_DIR"):
        return "codex"
    if os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude"
    return "unknown"


def infer_kind() -> str:
    explicit = os.environ.get("COS_COMMIT_KIND")
    if explicit:
        return explicit
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "cron"
    if os.environ.get("COS_HOOK_NAME"):
        return "hook"
    if os.environ.get("COS_SUBAGENT_ID") or os.environ.get("CLAUDE_SUBAGENT_ID"):
        return "subagent"
    if os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID"):
        return "orchestrator"
    return "manual"


def has_provenance(message: str) -> bool:
    return any(line.startswith(f"{key}:") for key in TRAILER_KEYS for line in message.splitlines())


def append_provenance(message: str, *, session: str, kind: str, harness: str) -> str:
    if has_provenance(message):
        return message
    cleaned = message.rstrip()
    origin = f"kind={kind} session={session} harness={harness}"
    trailers = [
        f"X-COS-Origin: {origin}",
        f"X-COS-Session: {session}",
        f"X-COS-Harness: {harness}",
    ]
    return cleaned + "\n\n" + "\n".join(trailers) + "\n"


def apply_to_file(message_file: Path, *, repo: Path | None = None) -> None:
    repo = repo or resolve_repo()
    message = message_file.read_text(encoding="utf-8", errors="ignore")
    updated = append_provenance(
        message,
        session=read_current_session(repo),
        kind=infer_kind(),
        harness=infer_harness(),
    )
    if updated != message:
        message_file.write_text(updated, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add COS provenance trailers to a commit message file")
    parser.add_argument("message_file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apply_to_file(Path(args.message_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
