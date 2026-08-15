"""Acceptance-criteria verification must not depend on GNU `timeout` existing.

Regression guard: on a stock macOS there is no `timeout` (and no `gtimeout`).
`auto-verify.sh` and `completion-gate.sh` used to run every criterion through
`timeout "$MAX_VERIFY_TIME" bash -c ...`, which returns 127 when the binary is
absent. Every criterion — including trivially true ones — was then reported as
FAILED, turning both verifiers into false-negative generators.

Both hooks now resolve `timeout`/`gtimeout` when present and otherwise enforce
the wall clock from shell. `COS_FORCE_SHELL_TIMEOUT=1` pins the shell watchdog
so both branches are exercised on any platform.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.behavior]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"

# Kept small so the hanging-command case does not dominate the lane runtime.
VERIFY_BUDGET = "2"


def _payload(criteria: list[str]) -> dict:
    body = "\n".join(f"{i}. {item}" for i, item in enumerate(criteria, start=1))
    return {
        "tool_name": "Agent",
        "tool_input": {"prompt": f"Do the thing.\n\nACCEPTANCE CRITERIA:\n{body}\n"},
        "tool_response": "Done. Implemented and fixed.",
    }


def _run(hook: str, criteria: list[str], project_dir: Path, force_shell: str) -> str:
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "COS_MAX_VERIFY_TIME": VERIFY_BUDGET,
            "COS_FORCE_SHELL_TIMEOUT": force_shell,
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    proc = subprocess.run(
        ["bash", str(HOOKS_DIR / hook)],
        input=json.dumps(_payload(criteria)),
        capture_output=True,
        text=True,
        env=env,
        timeout=90,
    )
    return proc.stdout + proc.stderr


@pytest.fixture
def verify_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    (project / "README.md").write_text("# fixture\n", encoding="utf-8")
    return project


@pytest.mark.parametrize("force_shell", ["0", "1"])
@pytest.mark.parametrize("hook", ["auto-verify.sh", "completion-gate.sh"])
def test_true_criterion_passes_without_gnu_timeout(hook, force_shell, verify_project):
    """A criterion that is actually true must report PASS on both code paths."""
    out = _run(hook, ["`test -f README.md` exits 0"], verify_project, force_shell)
    # completion-gate collapses an all-green run into a single summary line,
    # auto-verify lists each check; both must agree the criterion held.
    assert ("VERIFICATION PASSED" in out) or ("AUTO-VERIFY: PASS" in out), out
    assert "FAIL:" not in out, out


@pytest.mark.parametrize("force_shell", ["0", "1"])
@pytest.mark.parametrize("hook", ["auto-verify.sh", "completion-gate.sh"])
def test_false_criterion_reports_the_real_exit_code(hook, force_shell, verify_project):
    """A genuinely failing criterion still fails, and reports the command's code."""
    out = _run(hook, ["`test -f absent-fixture-file.txt` exits 0"], verify_project, force_shell)
    assert "FAIL: `test -f absent-fixture-file.txt` exits 0" in out
    # 1 is `test` failing; 127 would mean the runner itself could not execute.
    assert "exit code 1" in out
    assert "exit code 127" not in out


@pytest.mark.parametrize("hook", ["auto-verify.sh", "completion-gate.sh"])
def test_hanging_command_is_bounded_and_labelled_as_a_timeout(hook, verify_project):
    """The shell watchdog enforces a real wall clock and says so in the report."""
    out = _run(hook, ["`sleep 60` exits 0"], verify_project, force_shell="1")
    assert "timed out after" in out
    assert "PASS: `sleep 60`" not in out


def test_no_hook_reintroduces_a_bare_gnu_timeout_call():
    """Both verifiers must route every criterion through the portable runner."""
    for hook in ("auto-verify.sh", "completion-gate.sh"):
        text = (HOOKS_DIR / hook).read_text(encoding="utf-8")
        assert 'timeout "$MAX_VERIFY_TIME"' not in text, f"{hook} calls GNU timeout directly"
        assert "_bounded_bash()" in text, f"{hook} lost the portable bounded runner"
