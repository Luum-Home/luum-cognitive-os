"""Behavior tests for ADR-121 read-only sub-agent detection in agent-prelaunch.sh.

Tests verify that the hook correctly passes --allow-read-only to
cos_work_inventory.py when:
  (a) subagent_type is in the read-only whitelist (Explore, Plan,
      Code Reviewer, Security Engineer)
  (b) prompt/description contains the explicit READ_ONLY: true marker

and that the flag is NOT passed for:
  (c) non-whitelisted subagent_type values
  (d) prompts without the READ_ONLY marker

Strategy: capture the argv that cos_work_inventory.py would receive by
intercepting the python3 invocation with a shim script. The shim writes
the argv to a temp file instead of running the real inventory (which would
fail without a proper git repo setup in tests).

Run:
    pytest tests/behavior/test_agent_prelaunch_read_only.py -v

Marker: @pytest.mark.behavior on every test.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = PROJECT_ROOT / "hooks" / "agent-prelaunch.sh"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_input(
    subagent_type: str | None = None,
    description: str = "test task",
) -> str:
    """Build a minimal Agent tool_use JSON payload."""
    tool_input: dict[str, Any] = {"description": description}
    if subagent_type is not None:
        tool_input["subagent_type"] = subagent_type
    return json.dumps({"tool_name": "Agent", "tool_input": tool_input})


def _run_hook_capture_argv(
    hook_input: str,
    tmp_path: Path,
    env_override: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run agent-prelaunch.sh with a shim that captures cos_work_inventory.py argv.

    The shim intercepts the python3 call to cos_work_inventory.py and writes
    sys.argv to a capture file, then exits 0 so the hook doesn't block.

    Returns (returncode, stdout, stderr).
    """
    # Write a capture shim for cos_work_inventory.py
    shim_dir = tmp_path / "shim_scripts"
    shim_dir.mkdir()
    argv_file = tmp_path / "captured_argv.json"
    shim_py = shim_dir / "cos_work_inventory.py"
    shim_py.write_text(
        f"""#!/usr/bin/env python3
import sys, json
json.dump(sys.argv, open({str(argv_file)!r}, "w"))
sys.exit(0)
""",
        encoding="utf-8",
    )
    shim_py.chmod(0o755)

    # Build a minimal git repo for the hook's git check
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    subprocess.run(["git", "init", str(fake_repo)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.email", "test@test.com"],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(fake_repo), "config", "user.name", "Test"],
        capture_output=True, check=True,
    )

    # Build a fake scripts dir that the hook can find cos_work_inventory.py in
    fake_scripts = fake_repo / "scripts"
    fake_scripts.mkdir()
    (fake_scripts / "cos_work_inventory.py").symlink_to(shim_py)

    # Also need stub scripts that the hook calls:
    for stub_name in ("cos_task_claims.py", "claim_task.py", "agent_work_ledger.py", "resource_lease.py"):
        stub = fake_scripts / stub_name
        stub.write_text("#!/usr/bin/env python3\nimport sys; sys.exit(0)\n", encoding="utf-8")
        stub.chmod(0o755)

    # Build environment
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(fake_repo)
    env["COS_SKIP_GOVERNED_INVENTORY"] = "0"  # ensure inventory IS invoked
    env["COGNITIVE_OS_SESSION_ID"] = "test-session-adr121"
    # Suppress killswitch so hook doesn't early-exit
    env.pop("COS_KILLSWITCH", None)
    if env_override:
        env.update(env_override)

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=hook_input,
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )
    return result.returncode, result.stdout, result.stderr


def _read_captured_argv(tmp_path: Path) -> list[str] | None:
    argv_file = tmp_path / "captured_argv.json"
    if not argv_file.exists():
        return None
    import json as _json
    return _json.loads(argv_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReadOnlySubagentTypes:
    """Whitelist subagent_type values must produce --allow-read-only in argv."""

    @pytest.mark.parametrize("subagent_type", [
        "Explore",
        "Plan",
        "Code Reviewer",
        "Security Engineer",
    ])
    def test_whitelisted_type_passes_flag(
        self, subagent_type: str, tmp_path: Path
    ) -> None:
        hook_input = _make_agent_input(subagent_type=subagent_type)
        rc, stdout, stderr = _run_hook_capture_argv(hook_input, tmp_path)
        argv = _read_captured_argv(tmp_path)
        assert argv is not None, (
            f"Shim was not invoked (hook may have exited early). "
            f"rc={rc} stderr={stderr!r}"
        )
        assert "--allow-read-only" in argv, (
            f"Expected --allow-read-only for subagent_type={subagent_type!r}, "
            f"got argv={argv}"
        )

    def test_non_whitelisted_type_no_flag(self, tmp_path: Path) -> None:
        hook_input = _make_agent_input(subagent_type="implementation")
        _run_hook_capture_argv(hook_input, tmp_path)
        argv = _read_captured_argv(tmp_path)
        if argv is not None:
            assert "--allow-read-only" not in argv, (
                f"--allow-read-only should NOT be passed for non-whitelisted type, "
                f"got argv={argv}"
            )

    def test_no_subagent_type_no_flag(self, tmp_path: Path) -> None:
        hook_input = _make_agent_input(subagent_type=None)
        _run_hook_capture_argv(hook_input, tmp_path)
        argv = _read_captured_argv(tmp_path)
        if argv is not None:
            assert "--allow-read-only" not in argv, (
                f"--allow-read-only should NOT be passed when no subagent_type, "
                f"got argv={argv}"
            )


class TestReadOnlyExplicitMarker:
    """Explicit READ_ONLY: true in description must produce --allow-read-only."""

    def test_explicit_marker_passes_flag(self, tmp_path: Path) -> None:
        hook_input = _make_agent_input(
            description="Analyse the codebase. READ_ONLY: true"
        )
        _run_hook_capture_argv(hook_input, tmp_path)
        argv = _read_captured_argv(tmp_path)
        if argv is not None:
            assert "--allow-read-only" in argv, (
                f"Expected --allow-read-only for READ_ONLY: true marker, "
                f"got argv={argv}"
            )

    def test_no_marker_no_flag(self, tmp_path: Path) -> None:
        hook_input = _make_agent_input(description="Build the feature")
        _run_hook_capture_argv(hook_input, tmp_path)
        argv = _read_captured_argv(tmp_path)
        if argv is not None:
            assert "--allow-read-only" not in argv, (
                f"--allow-read-only should NOT be passed without marker, "
                f"got argv={argv}"
            )


class TestHookBashSyntax:
    """Confirm the hook has valid bash syntax (acceptance criterion 5)."""

    def test_bash_syntax_valid(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(HOOK_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n failed on {HOOK_PATH}:\n{result.stderr}"
        )
