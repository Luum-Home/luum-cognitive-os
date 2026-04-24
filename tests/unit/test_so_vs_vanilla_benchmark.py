"""Unit tests for scripts/so-vs-vanilla-benchmark.py.

Covers:
  - Task YAML loading + filtering
  - RunResult/TaskReport construction
  - Signal heuristics (check_signal)
  - Verdict logic (decide_verdict)
  - Dispatch env-var side-effect: COS_DISABLE_ALL_GOVERNANCE set in
    vanilla mode, unset in SO mode, and restored after the call
  - Markdown rendering contains required sections
  - Killswitch library early-exits on the master flag
  - CLI --dry-run short-circuits without touching dispatch
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "so-vs-vanilla-benchmark.py"
TASKS_YAML = PROJECT_ROOT / "docs" / "benchmarks" / "so-vs-vanilla-tasks.yaml"
KILLSWITCH = PROJECT_ROOT / "hooks" / "_lib" / "killswitch_check.sh"


def _load_harness():
    """Dynamic import — the script has a hyphenated name.

    Must register in sys.modules BEFORE exec so @dataclass can look up
    the module's __dict__ (Python 3.12+ dataclass.__module__ lookup).
    """
    if "so_vs_vanilla" in sys.modules:
        return sys.modules["so_vs_vanilla"]
    spec = importlib.util.spec_from_file_location("so_vs_vanilla", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.modules["so_vs_vanilla"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def harness():
    return _load_harness()


# -----------------------------------------------------------------------
# 1. Task loading
# -----------------------------------------------------------------------


def test_tasks_yaml_loads_and_has_min_five_tasks(harness):
    tasks = harness.load_tasks(TASKS_YAML)
    assert isinstance(tasks, list)
    assert len(tasks) >= 5, f"expected >=5 tasks, got {len(tasks)}"
    for t in tasks:
        assert "id" in t and "prompt" in t


def test_filter_tasks_single(harness):
    tasks = harness.load_tasks(TASKS_YAML)
    picked = harness.filter_tasks(tasks, "simple-fix")
    assert len(picked) == 1
    assert picked[0]["id"] == "simple-fix"


def test_filter_tasks_unknown_raises(harness):
    tasks = harness.load_tasks(TASKS_YAML)
    with pytest.raises(SystemExit):
        harness.filter_tasks(tasks, "does-not-exist")


# -----------------------------------------------------------------------
# 2. Signal heuristics
# -----------------------------------------------------------------------


def test_check_signal_trust_report_regex(harness):
    run = harness.RunResult(task_id="t", mode="so", trust_score=75)
    assert harness.check_signal("SO output matches regex '^TRUST_REPORT: SCORE='", run) is True


def test_check_signal_blocked(harness):
    run = harness.RunResult(task_id="t", mode="so", success=False, output_excerpt="BLOCKED by hook")
    assert harness.check_signal("SO run exit code non-zero OR output contains 'BLOCKED'", run) is True


def test_check_signal_unknown_returns_none(harness):
    run = harness.RunResult(task_id="t", mode="so")
    assert harness.check_signal("some signal we have never seen before xyz", run) is None


# -----------------------------------------------------------------------
# 3. Verdict logic
# -----------------------------------------------------------------------


def test_decide_verdict_so_win(harness):
    task = {
        "id": "x",
        "success_signal": "SO run exit code non-zero OR output contains 'BLOCKED'",
    }
    rep = harness.TaskReport(task_id="x", description="", hook_under_test="h")
    rep.vanilla = harness.RunResult(task_id="x", mode="vanilla", success=True, output_excerpt="done")
    rep.so = harness.RunResult(task_id="x", mode="so", success=False, output_excerpt="BLOCKED")
    harness.decide_verdict(task, rep)
    assert rep.verdict == "SO_WIN"


def test_decide_verdict_inconclusive_without_signal(harness):
    task = {"id": "x", "success_signal": "zzz unknown pattern zzz"}
    rep = harness.TaskReport(task_id="x", description="", hook_under_test="h")
    rep.vanilla = harness.RunResult(task_id="x", mode="vanilla", success=True)
    rep.so = harness.RunResult(task_id="x", mode="so", success=True)
    harness.decide_verdict(task, rep)
    assert rep.verdict == "INCONCLUSIVE"


# -----------------------------------------------------------------------
# 4. Dispatch env-var side-effects (mocked dispatch)
# -----------------------------------------------------------------------


def test_run_via_dispatch_sets_and_restores_env(harness, monkeypatch):
    """vanilla mode sets flag, SO mode unsets, prior value restored."""
    captured_envs: list[str | None] = []

    class FakeResult:
        success = True
        text = "hello"
        tokens_in = 10
        tokens_out = 20
        cost_usd = 0.001
        latency_ms = 42
        error = ""

    def fake_dispatch(**kwargs):
        captured_envs.append(os.environ.get("COS_DISABLE_ALL_GOVERNANCE"))
        return FakeResult()

    import lib.dispatch as dispatch_mod  # noqa: E402

    monkeypatch.setattr(dispatch_mod, "dispatch", fake_dispatch)

    # Set a prior value to verify restoration
    os.environ["COS_DISABLE_ALL_GOVERNANCE"] = "prior"
    try:
        v = harness.run_via_dispatch("p", mode="vanilla")
        s = harness.run_via_dispatch("p", mode="so")
    finally:
        prior = os.environ.pop("COS_DISABLE_ALL_GOVERNANCE", None)

    assert captured_envs == ["1", None]
    assert v.success and s.success
    assert v.tokens_in == 10 and s.cost_usd == 0.001
    # After both calls, prior value restored by the LAST finally block
    assert prior == "prior"


# -----------------------------------------------------------------------
# 5. Markdown report rendering
# -----------------------------------------------------------------------


def test_render_report_contains_required_sections(harness, tmp_path):
    rep = harness.TaskReport(task_id="demo", description="d", hook_under_test="h")
    rep.vanilla = harness.RunResult(
        task_id="demo", mode="vanilla", success=True, cost_usd=0.01, tokens_in=5, tokens_out=10
    )
    rep.so = harness.RunResult(
        task_id="demo",
        mode="so",
        success=True,
        cost_usd=0.02,
        tokens_in=6,
        tokens_out=11,
        trust_score=80,
        trust_status="MEDIUM",
    )
    rep.verdict = "TIE"
    rep.rationale = "test"
    out = tmp_path / "r.md"
    harness.render_report([rep], out)
    body = out.read_text(encoding="utf-8")
    assert "so-vs-vanilla benchmark" in body
    assert "Per-task results" in body
    assert "Aggregate verdict" in body
    assert "Per-task detail" in body
    assert "demo" in body
    assert "TIE" in body
    # overhead column should be 2.00×
    assert "2.00" in body


# -----------------------------------------------------------------------
# 6. Master kill-switch wiring in the bash library
# -----------------------------------------------------------------------


def test_killswitch_library_mentions_master_flag():
    body = KILLSWITCH.read_text(encoding="utf-8")
    assert "COS_DISABLE_ALL_GOVERNANCE" in body
    # And it must appear BEFORE the SO_KILLSWITCH env-var block so that
    # the master flag short-circuits first.
    master_idx = body.index("COS_DISABLE_ALL_GOVERNANCE")
    legacy_idx = body.index('"${SO_KILLSWITCH:-}"')
    assert master_idx < legacy_idx, "master flag must be checked before SO_KILLSWITCH"


def test_killswitch_library_master_flag_shortcircuits(tmp_path):
    """Source the library in a subshell with the flag set; expect exit 0."""
    probe = tmp_path / "probe.sh"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        "export COS_DISABLE_ALL_GOVERNANCE=1\n"
        "export HOOK_NAME=some-non-critical-hook.sh\n"
        f"source '{KILLSWITCH}'\n"
        "echo SHOULD_NEVER_PRINT\n",
        encoding="utf-8",
    )
    probe.chmod(0o755)
    res = subprocess.run(
        ["bash", str(probe)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env={**os.environ, "PROJECT_DIR": str(tmp_path)},
    )
    assert res.returncode == 0
    assert "SHOULD_NEVER_PRINT" not in res.stdout


# -----------------------------------------------------------------------
# 7. CLI --dry-run does NOT invoke dispatch
# -----------------------------------------------------------------------


def test_cli_dry_run_does_not_call_dispatch():
    # Use a subprocess so we can prove no network / dispatch happens.
    res = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0, res.stderr
    assert "Benchmark plan" in res.stdout
    assert "LLM calls per repeat" in res.stdout


def test_cli_dry_run_single_task():
    res = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--dry-run", "--task", "simple-fix"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0, res.stderr
    assert "simple-fix" in res.stdout
    # Only 1 task × 2 modes = 2 calls
    assert "2 LLM calls" in res.stdout
