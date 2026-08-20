# SCOPE: os-only
"""Portability probes for the launcher — the one file that can start a session.

Every probe below asks the same question from a different angle: can this
file be made to spawn something it was not armed for? The falsification probe
is the inverse: it confirms that a fully armed, in-budget call DOES reserve a
slot, so the refusals above are refusals and not a script that never runs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = REPO_ROOT / "scripts" / "cos_relaunch.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cos_lib.session_lineage import MODE_SPAWN, LineageStore  # noqa: E402


def _env(**extra: str) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("COS_PARENT", "COS_SESSION_DEPTH", "COS_LINEAGE"))
    }
    env.pop("COS_DISABLE_AUTONOMOUS_RELAUNCH", None)
    # A launcher that ever did reach a spawn under test must fail loudly
    # instead of starting a real session on the operator's account.
    env["CLAUDE_CODE_PATH"] = "/nonexistent/claude-must-not-run"
    env.update(extra)
    return env


def _run(project: Path, session: str, goal: str = "g-1", **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LAUNCHER), "--project-dir", str(project),
         "--session-id", session, "--goal-id", goal],
        text=True, capture_output=True, cwd=str(REPO_ROOT), env=_env(**extra), timeout=60,
    )


def test_unarmed_project_refuses_and_reserves_nothing(tmp_path: Path) -> None:
    project = tmp_path / "p"
    res = _run(project, "s0")
    assert res.returncode == 1
    assert json.loads(res.stdout)["fuse"] == "disarmed"
    assert not (project / ".cognitive-os" / "lineage" / "counters.json").exists()


def test_falsification_an_armed_in_budget_call_does_reserve(tmp_path: Path) -> None:
    """Without this the refusals above could be a script that always exits 1."""
    project = tmp_path / "p"
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    res = _run(project, "s0")
    assert res.returncode == 0, res.stderr
    assert store.read_counters("s0")["total"] == 1


def test_spawn_mode_does_not_bypass_the_depth_fuse(tmp_path: Path) -> None:
    project = tmp_path / "p"
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1", mode=MODE_SPAWN)
    res = _run(project, "s-deep", COS_SESSION_DEPTH="3", COS_LINEAGE_ROOT_ID="R")
    assert res.returncode == 1
    assert json.loads(res.stdout)["fuse"] == "depth"
    assert not (store.base_dir / "child-logs").exists()


def test_a_refused_call_never_consumes_a_slot(tmp_path: Path) -> None:
    project = tmp_path / "p"
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1", mode=MODE_SPAWN)
    for _ in range(3):
        _run(project, "s-deep", COS_SESSION_DEPTH="9", COS_LINEAGE_ROOT_ID="R")
    assert store.read_counters("R")["total"] == 0
    assert len(store.decisions()) == 3


def test_project_dir_is_honoured_for_state(tmp_path: Path) -> None:
    one, two = tmp_path / "one", tmp_path / "two"
    LineageStore(one / ".cognitive-os" / "lineage").arm("g-1")
    _run(one, "s0")
    assert (one / ".cognitive-os" / "lineage" / "counters.json").is_file()
    assert not (two / ".cognitive-os").exists()
