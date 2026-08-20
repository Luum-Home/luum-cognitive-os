# SCOPE: os-only
"""Portability probes for the Stop-event relaunch gate.

Two claims are under test here, and the second one is the one that matters:
the hook follows the project root it is given, and it starts nothing in a
project that was never armed. The falsification probe arms one of two
otherwise identical roots — a gate that ignored the arm file would leave
identical evidence in both, and the assertion would fail.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "lineage-relaunch-gate.sh"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cos_lib.session_lineage import LineageStore  # noqa: E402


def _project(tmp_path: Path, name: str = "elsewhere") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    for part in ("scripts", "cos_lib", "hooks"):
        target = root / part
        if not target.exists():
            target.symlink_to(REPO_ROOT / part)
    return root


def _env(project: Path, **extra: str) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("COS_PARENT", "COS_SESSION_DEPTH", "COS_LINEAGE"))
    }
    env.pop("COS_DISABLE_AUTONOMOUS_RELAUNCH", None)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.update(extra)
    return env


def _run(project: Path, session_id: str, **extra: str) -> subprocess.CompletedProcess:
    payload = json.dumps({
        "hook_event_name": "Stop", "session_id": session_id,
        "timestamp": "2026-08-19T00:00:00Z", "stop_reason": "end_turn",
    })
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, text=True, capture_output=True,
        cwd=str(project), env=_env(project, **extra), timeout=30,
    )


def _seed_goal(project: Path, goal_id: str = "g-1") -> None:
    from cos_lib.goal_state import GoalState, GoalStateStore  # noqa: PLC0415

    store = GoalStateStore(
        base_dir=project / ".cognitive-os" / "goals", workspace_thread_id="default"
    )
    goal = GoalState.create(
        objective="probe", acceptance_checks=["c1"], workspace_thread_id="default"
    )
    goal.goal_id = goal_id
    store.save(goal)


def test_unarmed_project_is_left_untouched(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _seed_goal(project)
    res = _run(project, "S-root")
    assert res.returncode == 0
    assert res.stdout.strip() == ""
    assert not (project / ".cognitive-os" / "lineage").exists()


def test_falsification_arming_one_root_changes_only_that_root(tmp_path: Path) -> None:
    armed = _project(tmp_path, "armed")
    bare = _project(tmp_path, "bare")
    for root in (armed, bare):
        _seed_goal(root)
    LineageStore(armed / ".cognitive-os" / "lineage").arm("g-1")

    _run(armed, "S-armed")
    _run(bare, "S-bare")

    decisions = LineageStore(armed / ".cognitive-os" / "lineage").decisions()
    assert len(decisions) == 1 and decisions[0]["allowed"] is True
    assert not (bare / ".cognitive-os" / "lineage").exists()


def test_armed_but_no_active_goal_decides_nothing(tmp_path: Path) -> None:
    project = _project(tmp_path)
    LineageStore(project / ".cognitive-os" / "lineage").arm("g-1")
    res = _run(project, "S-root")
    assert res.returncode == 0
    assert LineageStore(project / ".cognitive-os" / "lineage").decisions() == []


def test_env_killswitch_stops_it_even_when_armed(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _seed_goal(project)
    LineageStore(project / ".cognitive-os" / "lineage").arm("g-1")
    res = _run(project, "S-root", COS_DISABLE_AUTONOMOUS_RELAUNCH="1")
    assert res.returncode == 0
    assert LineageStore(project / ".cognitive-os" / "lineage").decisions() == []


def test_dry_run_arming_never_creates_a_child_log(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _seed_goal(project)
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    _run(project, "S-root")
    assert not (store.base_dir / "child-logs").exists()


def test_runtime_bypass_file_stops_it_mid_session(tmp_path: Path) -> None:
    """The only switch that works without restarting the harness (ADR-241).

    Written as a differential: the same armed project, same payload, run twice
    -- once with the runtime file and once without. One decision row, not two,
    is what proves the bypass matched. Asserting only the first run would pass
    for a bypass that never fires, which is how the first draft of this hook
    looked correct while keying on the wrong variable name.
    """
    project = _project(tmp_path)
    _seed_goal(project)
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")

    runtime = project / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    bypass = runtime / "bypass.env"
    bypass.write_text("COS_BYPASS=autonomous_relaunch\n")
    _run(project, "S-root")
    assert store.decisions() == [], "runtime bypass did not stop the gate"

    bypass.unlink()
    _run(project, "S-root")
    assert len(store.decisions()) == 1, "gate stayed silent even without the bypass"
