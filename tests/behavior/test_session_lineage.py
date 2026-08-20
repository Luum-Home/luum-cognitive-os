# SCOPE: os-only
"""Behaviour tests for the cross-session recursion fuses.

These do not assert that a fuse EXISTS. Each one forces the condition and
checks the effect on disk: a decision row, a counter value, a directory that
was never created. A fuse nobody has watched cut is a promise, and across the
~50 sources surveyed for the harness report nobody was found exercising their
own.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cos_lib.session_lineage import (  # noqa: E402
    ENV_DEPTH,
    ENV_DISABLE,
    ENV_PARENT,
    ENV_ROOT,
    FuseLimits,
    LineageRecord,
    LineageStore,
    MODE_SPAWN,
    child_env,
    current_depth,
    evaluate_relaunch,
    resolve_parent,
)

PY = sys.executable
STOP_HOOK = REPO / "hooks" / "lineage-relaunch-gate.sh"
START_HOOK = REPO / "hooks" / "session-lineage-record.sh"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A throwaway project root that borrows the repo's code but not its state."""
    root = tmp_path / "proj"
    root.mkdir()
    for name in ("scripts", "cos_lib", "hooks"):
        (root / name).symlink_to(REPO / name)
    return root


def _hook_env(project: Path, **extra: str) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("COS_PARENT", "COS_SESSION_DEPTH", "COS_LINEAGE"))
    }
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.pop(ENV_DISABLE, None)
    env.update(extra)
    return env


def _run_stop_hook(project: Path, session_id: str, **extra: str) -> subprocess.CompletedProcess:
    payload = json.dumps({
        "hook_event_name": "Stop", "session_id": session_id,
        "timestamp": "2026-08-19T00:00:00Z", "stop_reason": "end_turn",
    })
    return subprocess.run(
        ["/bin/bash", str(STOP_HOOK)], input=payload, text=True,
        capture_output=True, env=_hook_env(project, **extra), cwd=str(project),
    )


# ── Proof 1: no goal file, no launch — and it shows ─────────────────────────

def test_stop_hook_disarmed_creates_nothing(project: Path):
    """Without the arm file the hook must not merely decline: it must not act.

    Asserted on effect, not on exit code — the directory the launcher would
    write into is never created, so nothing downstream can mistake an empty
    ledger for a ledger of refusals it never wrote.
    """
    res = _run_stop_hook(project, "sess-root")
    lineage_dir = project / ".cognitive-os" / "lineage"
    assert res.returncode == 0
    assert not lineage_dir.exists(), "disarmed hook touched the lineage directory"
    assert res.stdout.strip() == "", f"disarmed hook produced output: {res.stdout!r}"


def test_stop_hook_disarmed_even_with_an_active_goal(project: Path):
    """An unfinished goal is not consent. Only the arm file is."""
    goals = project / ".cognitive-os" / "goals"
    goals.mkdir(parents=True)
    (goals / "default.json").write_text(json.dumps({
        "goal_id": "g-1", "objective": "x", "status": "active",
        "acceptance_checks": ["c1"],
    }))
    _run_stop_hook(project, "sess-root")
    assert not (project / ".cognitive-os" / "lineage").exists()


# ── Proof 2: armed, under the caps — it decides, and disk shows it ─────────

def test_armed_under_cap_decides_and_reserves_a_slot(project: Path):
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")  # default mode: dry-run

    res = subprocess.run(
        [PY, str(REPO / "scripts" / "cos_relaunch.py"),
         "--project-dir", str(project), "--session-id", "sess-root", "--goal-id", "g-1"],
        capture_output=True, text=True, env=_hook_env(project), cwd=str(REPO),
    )
    assert res.returncode == 0, res.stderr

    decisions = store.decisions()
    assert len(decisions) == 1
    assert decisions[0]["allowed"] is True
    assert decisions[0]["child_depth"] == 1
    assert "mode=dry-run" in decisions[0]["reason"]

    counters = store.read_counters("sess-root")
    assert counters["total"] == 1
    assert counters["children"]["sess-root"] == 1


def test_arm_file_mode_outranks_the_caller(project: Path):
    """A caller that forgets --dry-run cannot spawn on a dry-run arm file."""
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    sys.path.insert(0, str(REPO))
    from scripts.cos_relaunch import relaunch  # noqa: PLC0415

    dec = relaunch(project, session_id="s", goal_id="g-1", prompt="x", dry_run=False)
    assert dec.allowed is True
    assert "mode=dry-run" in dec.reason
    assert not (store.base_dir / "child-logs").exists()


# ── Proof 3: at the cap — it refuses, and says why ─────────────────────────

def test_depth_at_cap_refuses_and_records_why(project: Path):
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1", mode=MODE_SPAWN)  # even fully armed, the fuse holds

    res = subprocess.run(
        [PY, str(REPO / "scripts" / "cos_relaunch.py"),
         "--project-dir", str(project), "--session-id", "sess-gen3", "--goal-id", "g-1"],
        capture_output=True, text=True,
        env=_hook_env(project, **{ENV_DEPTH: "3", ENV_ROOT: "sess-root"}), cwd=str(REPO),
    )
    assert res.returncode == 1

    decisions = store.decisions()
    assert len(decisions) == 1
    assert decisions[0]["allowed"] is False
    assert decisions[0]["fuse"] == "depth"
    assert "generation 4" in decisions[0]["reason"]
    # Refusing must not consume a slot.
    assert store.read_counters("sess-root")["total"] == 0
    assert not (store.base_dir / "child-logs").exists()


def test_total_cap_binds_across_sessions_and_does_not_reset(project: Path):
    """The tree cap lives on disk, so a fresh session inherits the count.

    A counter that starts over each session is decoration; this asserts the
    third session is refused using only what the first two wrote down.
    """
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    lim = FuseLimits(max_total=2, max_width=99)
    env = {ENV_ROOT: "R"}

    allowed = []
    for i in range(4):
        dec = evaluate_relaunch(store, session_id=f"s{i}", goal_id="g-1", limits=lim, env=env)
        if dec.allowed:
            store.reserve_slot("R", f"s{i}", lim)
        allowed.append(dec.allowed)

    assert allowed == [True, True, False, False]
    # A brand-new store object over the same directory sees the same count.
    assert LineageStore(store.base_dir).read_counters("R")["total"] == 2


def test_width_cap_binds_what_depth_cannot(project: Path):
    """Depth is a path property; width is not. Same depth, still refused."""
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    lim = FuseLimits(max_total=99, max_width=2)
    env = {ENV_ROOT: "R"}

    allowed = []
    for _ in range(4):
        dec = evaluate_relaunch(store, session_id="P", goal_id="g-1", limits=lim, env=env)
        if dec.allowed:
            store.reserve_slot("R", "P", lim)
        allowed.append(dec.allowed)
    assert allowed == [True, True, False, False]

    # Depth alone would have waved every one of these through.
    assert current_depth(env) == 0


def test_stall_fuse_cuts_before_the_budget_does(project: Path):
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    dec = evaluate_relaunch(store, session_id="s", goal_id="g-1", consecutive_no_progress=2, env={})
    assert dec.allowed is False and dec.fuse == "stall"


def test_killswitch_env_var_cuts(project: Path):
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    dec = evaluate_relaunch(store, session_id="s", goal_id="g-1", env={ENV_DISABLE: "1"})
    assert dec.allowed is False and dec.fuse == "kill-switch"


def test_arm_file_is_scoped_to_one_goal(project: Path):
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.arm("g-1")
    dec = evaluate_relaunch(store, session_id="s", goal_id="g-2", env={})
    assert dec.allowed is False and dec.fuse == "disarmed"


def test_unparseable_depth_is_treated_as_deep(project: Path):
    assert current_depth({ENV_DEPTH: "banana"}) >= FuseLimits().max_depth
    assert current_depth({ENV_DEPTH: "-4"}) >= FuseLimits().max_depth


# ── Proof 4: lineage — a child writes its parent, the chain rebuilds ───────

def _run_start_hook(project: Path, session_id: str, **extra: str) -> None:
    payload = json.dumps({
        "hook_event_name": "SessionStart", "session_id": session_id,
        "timestamp": "2026-08-19T00:00:00Z", "source": "startup",
    })
    subprocess.run(
        ["/bin/bash", str(START_HOOK)], input=payload, text=True,
        capture_output=True, env=_hook_env(project, **extra), cwd=str(project), check=False,
    )


def test_child_writes_parent_and_the_chain_reconstructs(project: Path):
    _run_start_hook(project, "A")  # root: no launcher, no parent
    env_b = child_env(parent_session_id="A", root_id="A", parent_depth=0)
    _run_start_hook(project, "B", **env_b)
    env_c = child_env(parent_session_id="B", root_id="A", parent_depth=1)
    _run_start_hook(project, "C", **env_c)

    store = LineageStore(project / ".cognitive-os" / "lineage")
    chain = store.chain("C")
    assert [r.session_id for r in chain] == ["A", "B", "C"]
    assert [r.depth for r in chain] == [0, 1, 2]
    assert [r.parent_session_id for r in chain] == [None, "A", "B"]
    assert [r.source for r in chain] == ["startup", "relaunch", "relaunch"]


def test_unknown_parent_is_absent_not_invented(project: Path):
    _run_start_hook(project, "solo")
    store = LineageStore(project / ".cognitive-os" / "lineage")
    rec = store.records()[0]
    assert rec.parent_session_id is None
    assert rec.session_id == "solo"
    assert resolve_parent({}) is None


def test_chain_survives_a_cycle_in_the_ledger(project: Path):
    store = LineageStore(project / ".cognitive-os" / "lineage")
    store.record_session(LineageRecord("X", "Y", 1, "X", "t"))
    store.record_session(LineageRecord("Y", "X", 1, "X", "t"))
    assert len(store.chain("X")) == 2  # terminates instead of looping


# ── The probe itself is part of the contract ───────────────────────────────

def test_probe_reports_every_fuse_cutting():
    res = subprocess.run(
        [PY, str(REPO / "scripts" / "cos_lineage.py"), "probe"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "6/6 fuses cut when forced" in res.stdout
    assert "FAIL" not in res.stdout
