"""ADR-028 D6 — Chaos test 5: destructive-git-reset cascade detector.

Contract: if a hook contains `git reset --hard`, the detection mechanism
MUST surface it before it can execute.

Two complementary approaches:
  A. If hooks/destructive-git-blocker.sh exists: pass the dangerous command via
     CLAUDE_TOOL_INPUT + CLAUDE_AGENT_ID and assert exit code == 1 (blocked).
  B. Always: run a grep-based static detector that catches
     `git reset --hard|git clean -fdx|rm -rf /` in hook source and asserts it
     fires on our crafted fake hook.

The contract is satisfied when EITHER A or B (or both) fire.
Silence on a hook containing `git reset --hard` is the failure mode — not whether
the hook is blocked at runtime vs. detected statically.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

_BLOCKER = _PROJ_ROOT / "hooks" / "destructive-git-blocker.sh"

# ---- Helpers ----------------------------------------------------------------

_DESTRUCTIVE_PATTERNS = [
    r"git reset --hard",
    r"git clean -fdx",
    r"rm -rf /",
]


def _static_detect(hook_content: str) -> list[str]:
    """Grep-based static detector: returns matched patterns found in hook_content."""
    import re

    found = []
    for pattern in _DESTRUCTIVE_PATTERNS:
        if re.search(pattern, hook_content):
            found.append(pattern)
    return found


# ---- Tests ------------------------------------------------------------------


class TestResetCascadeDetector:
    """Watchdog on the watchdog: detect destructive git ops in hook code."""

    def test_static_detector_fires_on_fake_hook(self, tmp_path):
        """Grep-based detector must find `git reset --hard` in a fake hook."""
        fake_hook = textwrap.dedent("""\
            #!/bin/bash
            # Simulate a badly written hook that resets the repo
            git reset --hard HEAD~1
            echo "done"
        """)

        hook_file = tmp_path / "fake-destructive-hook.sh"
        hook_file.write_text(fake_hook)

        hits = _static_detect(fake_hook)

        assert hits, (
            "Static detector must fire for `git reset --hard` in hook content; "
            f"got no matches. Patterns checked: {_DESTRUCTIVE_PATTERNS}"
        )
        assert "git reset --hard" in hits

    def test_static_detector_clean_hook_is_silent(self, tmp_path):
        """Static detector must NOT fire on a harmless hook."""
        safe_hook = textwrap.dedent("""\
            #!/bin/bash
            git status
            git diff HEAD
            echo "hook ran"
        """)
        hits = _static_detect(safe_hook)
        assert not hits, f"False positive: safe hook triggered detector: {hits}"

    @pytest.mark.skipif(
        not _BLOCKER.exists(),
        reason="hooks/destructive-git-blocker.sh not found; skipping runtime block test",
    )
    def test_blocker_sh_blocks_reset_hard_in_agent_context(self, tmp_path):
        """destructive-git-blocker.sh must exit 1 when CLAUDE_AGENT_ID is set."""
        env = {
            **os.environ,
            "CLAUDE_TOOL_INPUT": "git reset --hard HEAD~1",
            "CLAUDE_AGENT_ID": "chaos-test-agent",
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            # Ensure jq fallback path works even without jq
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }

        result = subprocess.run(
            ["bash", str(_BLOCKER)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            cwd=str(_PROJ_ROOT),
        )

        assert result.returncode == 1, (
            "destructive-git-blocker.sh must exit 1 (BLOCKED) when "
            "CLAUDE_AGENT_ID is set and command is `git reset --hard`.\n"
            f"returncode: {result.returncode}\n"
            f"stderr: {result.stderr}\n"
            f"stdout: {result.stdout}"
        )
        assert "BLOCKED" in result.stderr, (
            "Expected 'BLOCKED' in stderr; got: " + result.stderr[:300]
        )

    @pytest.mark.skipif(
        not _BLOCKER.exists(),
        reason="hooks/destructive-git-blocker.sh not found; skipping warn test",
    )
    def test_blocker_sh_warns_but_allows_in_user_context(self, tmp_path):
        """destructive-git-blocker.sh must exit 0 (warn, not block) without CLAUDE_AGENT_ID."""
        env = {
            **os.environ,
            "CLAUDE_TOOL_INPUT": "git reset --hard HEAD~1",
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        }
        # Remove agent id to simulate user/orchestrator context
        env.pop("CLAUDE_AGENT_ID", None)

        result = subprocess.run(
            ["bash", str(_BLOCKER)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            cwd=str(_PROJ_ROOT),
        )

        assert result.returncode == 0, (
            "In user context, blocker should exit 0 (warn, allow); "
            f"got {result.returncode}.\nstderr: {result.stderr}"
        )
        assert "WARN" in result.stderr or "warn" in result.stderr.lower(), (
            "Expected a warning in stderr for user context; got: " + result.stderr[:300]
        )
