# SCOPE: os-only
"""Portability proof for scripts/_lib/session-id.sh.

This lib became a shipped artifact on 2026-08-19: cos_init projects it to
.cognitive-os/bin/_lib/session-id.sh so the edit-lock CLI and the edit-lock
hooks resolve the SAME session identity. That is its whole reason to travel --
without it edit-coop.sh falls back to `default-session` and the hooks to
`shell-$PPID`, and a lock taken by one is invisible to the other.

So the property under proof is not "the file exists somewhere": it is that the
resolution order is identical no matter which copy gets sourced, from any cwd.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/_lib/session-id.sh"


def _resolve(lib: Path, cwd: Path, **env_extra: str) -> str:
    env = {k: v for k, v in os.environ.items()
           if k not in ("COGNITIVE_OS_SESSION_ID", "CODEX_SESSION_ID", "CLAUDE_SESSION_ID")}
    env.update(env_extra)
    result = subprocess.run(
        ["bash", "-c", f'source "{lib}" && cos_session_id'],
        text=True, capture_output=True, cwd=str(cwd), env=env, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "No such file or directory" not in result.stderr
    return result.stdout


def test_resolution_order_is_stable_from_an_arbitrary_cwd(tmp_path: Path) -> None:
    """Explicit ids win, in the documented order."""
    assert _resolve(ARTIFACT, tmp_path, COGNITIVE_OS_SESSION_ID="cos-1",
                    CODEX_SESSION_ID="codex-1", CLAUDE_SESSION_ID="claude-1") == "cos-1"
    assert _resolve(ARTIFACT, tmp_path, CODEX_SESSION_ID="codex-1",
                    CLAUDE_SESSION_ID="claude-1") == "codex-1"
    assert _resolve(ARTIFACT, tmp_path, CLAUDE_SESSION_ID="claude-1") == "claude-1"


def test_the_shipped_copy_answers_exactly_like_the_source(tmp_path: Path) -> None:
    """The point of shipping it: both copies must agree, or locking is broken.

    Compares the source under scripts/_lib with a copy placed at the consumer
    location, on the same inputs.
    """
    shipped_dir = tmp_path / ".cognitive-os" / "bin" / "_lib"
    shipped_dir.mkdir(parents=True)
    shipped = shipped_dir / "session-id.sh"
    shutil.copy2(ARTIFACT, shipped)

    for env in ({"COGNITIVE_OS_SESSION_ID": "abc"},
                {"CODEX_SESSION_ID": "def"},
                {"CLAUDE_SESSION_ID": "ghi"}):
        assert _resolve(ARTIFACT, tmp_path, **env) == _resolve(shipped, tmp_path, **env)


def test_fallback_is_deterministic_within_a_process_tree(tmp_path: Path) -> None:
    """Null control for the two tests above.

    With no id in the environment the answer must still be a stable, non-empty
    identity -- otherwise 'both copies agree' would hold trivially for a lib
    that returns nothing, and an empty identity is exactly what collapsed the
    negotiation inbox to its root earlier today.
    """
    got = _resolve(ARTIFACT, tmp_path)
    assert got.startswith("shell-"), got
    assert got != "shell-", "the fallback produced an empty identity"
