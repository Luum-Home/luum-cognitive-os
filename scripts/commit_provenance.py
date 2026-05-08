#!/usr/bin/env python3
"""Add COS provenance trailers to commit messages.

Used by `.githooks/prepare-commit-msg`. The hook is intentionally local-only:
it records session/harness/kind metadata in the commit message so future audits
can distinguish manual, agent, hook, cron, and subagent commits.

Attribution algorithm (priority order):
  1. PPID-chain walk: look for .context-<pid>.json up the process tree.
  2. Environment variables (COS_COMMIT_* / COGNITIVE_OS_* / CLAUDE_* / CODEX_*).
  3. Most-recently-modified .context-<pid>.json (last resort — may be wrong session).
  4. Backwards compat: most-recent .current-session-<pid> plain-text files.
  5. "manual" / "unknown" defaults.

See ADR-088 for the full rationale and known limitations.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

TRAILER_KEYS = ("X-COS-Origin", "X-COS-Session", "X-COS-Harness")
MAX_PARENT_DEPTH = 10


# ─── Process tree helpers ─────────────────────────────────────────────────────


def walk_parents(pid: int, max_depth: int = MAX_PARENT_DEPTH) -> list[int]:
    """Walk PPID chain from *pid* upward. Returns [pid, ppid, ppid-of-ppid, ...].

    Uses ``ps -o ppid= -p <pid>`` which works on macOS and most Linux distros.
    Falls back gracefully on any subprocess error.
    """
    chain: list[int] = []
    current = pid
    for _ in range(max_depth):
        chain.append(current)
        try:
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(current)],
                capture_output=True,
                text=True,
                timeout=2,
            )
            ppid_str = result.stdout.strip()
            if not ppid_str:
                break
            ppid = int(ppid_str)
            if ppid <= 1 or ppid == current:
                break
            current = ppid
        except (subprocess.SubprocessError, ValueError, OSError):
            break
    return chain


def _load_json_marker(path: Path) -> dict | None:
    """Load a JSON context marker; return None on parse failure."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def _load_legacy_marker(path: Path) -> dict | None:
    """Load a legacy plain-text .current-session-<pid> marker.

    These files contain just a session ID string. Returned as a minimal context
    dict with kind=unknown so callers can still extract the session ID.
    DEPRECATED: new code writes JSON markers via write_context_marker.py.
    """
    try:
        value = path.read_text(encoding="utf-8", errors="ignore").strip()
        if value:
            return {"session": value, "kind": "unknown", "harness": "unknown", "_legacy": True}
    except Exception:
        pass
    return None


# ─── Core lookup ─────────────────────────────────────────────────────────────


def find_owning_context(repo: Path) -> dict | None:
    """Find the COS context that owns the current git commit process.

    Priority:
      1. PPID-chain walk through .context-<pid>.json files.
      2. Environment variables.
      3. Most-recently-modified .context-<pid>.json (mtime fallback).
      4. Most-recently-modified .current-session-<pid> (legacy fallback).
      5. Return None (callers apply their own defaults).
    """
    sessions_dir = repo / ".cognitive-os" / "sessions"

    # ── Step 1: PPID-chain walk ───────────────────────────────────────────────
    try:
        pid_chain = walk_parents(os.getpid())
        for pid in pid_chain:
            json_marker = sessions_dir / f".context-{pid}.json"
            if json_marker.exists():
                ctx = _load_json_marker(json_marker)
                if ctx:
                    return ctx
    except Exception:
        pass

    # ── Step 2: Environment variables ────────────────────────────────────────
    env_session = (
        os.environ.get("COS_COMMIT_SESSION_ID")
        or os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
    )
    env_harness = _env_harness()
    env_kind = _env_kind()

    # A harness-only environment such as CODEX_PROJECT_DIR is useful as
    # enrichment, but it is not enough to identify the owning session. Keep
    # searching so legacy/current context markers can provide the session ID.
    if env_session or env_kind != "manual":
        return {
            "session": env_session or "unknown",
            "kind": env_kind,
            "harness": env_harness,
            "_source": "env",
        }

    # ── Step 3: Most-recent JSON context marker (mtime fallback) ─────────────
    try:
        json_markers = sorted(
            sessions_dir.glob(".context-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for marker in json_markers:
            ctx = _load_json_marker(marker)
            if ctx:
                ctx["_source"] = "mtime-json-fallback"
                return ctx
    except Exception:
        pass

    # ── Step 4: Legacy .current-session-<pid> (backwards compat) ─────────────
    try:
        legacy_markers = sorted(
            sessions_dir.glob(".current-session-*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for marker in legacy_markers:
            ctx = _load_legacy_marker(marker)
            if ctx:
                ctx["_source"] = "legacy-fallback"
                return ctx
    except Exception:
        pass

    return None


# ─── Env-based helpers (fallbacks when no context file) ──────────────────────


def _env_harness() -> str:
    explicit = os.environ.get("COS_COMMIT_HARNESS") or os.environ.get("COGNITIVE_OS_HARNESS")
    if explicit:
        return explicit
    if os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_PROJECT_DIR"):
        return "codex"
    if os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude"
    return "unknown"


def _env_kind() -> str:
    explicit = os.environ.get("COS_COMMIT_KIND")
    if explicit:
        return explicit
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "cron"
    if os.environ.get("COS_HOOK_NAME"):
        return "hook"
    if os.environ.get("COS_SUBAGENT_ID") or os.environ.get("CLAUDE_SUBAGENT_ID"):
        return "subagent"
    if (
        os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
    ):
        return "orchestrator"
    return "manual"


# ─── Public API (kept for external callers; delegate to find_owning_context) ──


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def resolve_repo() -> Path:
    top = _run_git(["rev-parse", "--show-toplevel"])
    return Path(top) if top else Path.cwd()


def read_current_session(repo: Path) -> str:
    """Return the session ID for this commit.

    Single source of truth: delegates to find_owning_context().
    Backwards compat: legacy .current-session-<pid> files are still read
    inside find_owning_context() as step 4, so existing repos without JSON
    markers continue to work.
    """
    ctx = find_owning_context(repo)
    if ctx:
        return ctx.get("session") or "unknown"
    return "unknown"


def infer_kind(repo: Path | None = None) -> str:
    """Return the commit kind. Delegates to find_owning_context() first."""
    if repo is None:
        repo = resolve_repo()
    ctx = find_owning_context(repo)
    if ctx:
        return ctx.get("kind") or "manual"
    return _env_kind()


def infer_harness(repo: Path | None = None) -> str:
    """Return the harness that owns this commit. Delegates to find_owning_context() first."""
    if repo is None:
        repo = resolve_repo()
    ctx = find_owning_context(repo)
    if ctx:
        return ctx.get("harness") or "unknown"
    return _env_harness()


def has_provenance(message: str) -> bool:
    return any(
        line.startswith(f"{key}:")
        for key in TRAILER_KEYS
        for line in message.splitlines()
    )


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
    if os.environ.get("COS_DISABLE_COMMIT_PROVENANCE") == "1":
        return
    repo = repo or resolve_repo()
    # Single find_owning_context() call; results fed to all three fields so
    # there is no risk of different lookup results per field.
    ctx = find_owning_context(repo)

    if ctx:
        session = ctx.get("session") or "unknown"
        kind = ctx.get("kind") or "manual"
        harness = ctx.get("harness") or "unknown"
        if harness == "unknown":
            harness = _env_harness()
    else:
        session = "unknown"
        kind = _env_kind()
        harness = _env_harness()

    message = message_file.read_text(encoding="utf-8", errors="ignore")
    updated = append_provenance(message, session=session, kind=kind, harness=harness)
    if updated != message:
        message_file.write_text(updated, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add COS provenance trailers to a commit message file"
    )
    parser.add_argument("message_file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apply_to_file(Path(args.message_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
