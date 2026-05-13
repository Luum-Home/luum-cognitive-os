"""Behavioral tests for hooks/tool-loop-detector.sh.

Verifies:
- Repeating the same tool+args 3 times in a row triggers a TOOL LOOP warning
- Calling different tools does not trigger a warning
- A corrupt / missing history file is handled gracefully (state resets)
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "tool-loop-detector.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stdin(tool_name: str, tool_input: "dict | None" = None) -> str:
    """Build a PostToolUse event JSON string."""
    payload = {
        "tool_name": tool_name,
        "tool_input": tool_input or {},
        "tool_response": {"exit_code": 0, "stdout": "", "stderr": ""},
    }
    return json.dumps(payload)


def _run_hook(
    stdin: str,
    history_file: "str | None" = None,
    extra_env: "dict | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    env["PRIVATE_MODE"] = "false"
    # Capability level: do not disable tool-loop-detector
    env["COGNITIVE_OS_CAPABILITY_LEVEL"] = "3"
    if history_file is not None:
        # Trick: override PPID-based filename by patching it via env var or
        # by pre-writing the file.  The hook uses PPID which we cannot control
        # from Python.  Instead, we pre-populate the history file at the
        # expected path for the current PID-based path.
        # We expose the HISTORY_FILE path so the test can seed it.
        env["_TEST_HISTORY_FILE"] = history_file
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToolLoopDetector:
    def test_repeated_tool_triggers_warning(self, tmp_path):
        """Same tool+args called 3+ times should produce a TOOL LOOP warning.

        We cannot seed the history file directly because the hook derives its
        path from PPID.  Instead, we run the hook 3 times sequentially from the
        same Python process (same PPID) with an identical stdin payload, which
        causes the hook to build up 3 identical lines in its history file.
        """
        stdin = _make_stdin("Read", {"file_path": "/tmp/test.go"})

        # Run 3 times in the same process (same PPID → same history file)
        results = []
        for _ in range(3):
            r = _run_hook(stdin)
            results.append(r)

        # At least the last run should warn
        combined_output = " ".join(r.stdout + r.stderr for r in results)
        assert "TOOL LOOP DETECTED" in combined_output, (
            "Expected 'TOOL LOOP DETECTED' after 3 identical tool calls\n"
            f"Combined output: {combined_output!r}"
        )

    def test_different_tools_no_warning(self, tmp_path):
        """Calling different tools should not trigger a loop warning."""
        tools = ["Read", "Grep", "Bash", "Edit", "Write"]
        outputs = []
        for tool in tools:
            stdin = _make_stdin(tool, {"path": f"/tmp/{tool.lower()}.go"})
            r = _run_hook(stdin)
            outputs.append(r.stdout + r.stderr)

        combined = " ".join(outputs)
        # A simple alternating variety of 5 different tools should NOT trigger
        # the generic_repeat or ping_pong patterns
        assert "TOOL LOOP DETECTED" not in combined, (
            f"Unexpected loop warning for diverse tools\nOutput: {combined!r}"
        )

    def test_corrupt_state_resets(self, tmp_path):
        """A corrupt or truncated history file should not crash the hook.

        The hook uses set -euo pipefail; a corrupt file might cause awk/wc to
        fail.  We verify that the hook still exits 0 (gracefully).
        """
        # The hook writes its history to /tmp/claude-tool-history-${PPID}.log
        # We can corrupt the expected file for the current PPID
        ppid = os.getppid()
        history_path = Path(f"/tmp/claude-tool-history-{ppid}.log")
        original = None
        try:
            if history_path.exists():
                original = history_path.read_bytes()
            # Write binary garbage
            history_path.write_bytes(b"\x00\x01\x02\x03\xff\xfe invalid json")

            stdin = _make_stdin("Bash", {"command": "ls"})
            r = _run_hook(stdin)

            assert r.returncode == 0, (
                f"Hook crashed after corrupt history (exit {r.returncode})\n"
                f"stderr: {r.stderr}"
            )
        finally:
            if original is not None:
                history_path.write_bytes(original)
            elif history_path.exists():
                history_path.unlink()
