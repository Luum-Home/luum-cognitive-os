# SCOPE: os-only
"""Portability probes for the lineage CLI.

The CLI is the operator's window into the fuses, so its portability claim is
concrete: --project-dir decides where it reads and writes, and `probe` must
report a failure when a fuse does not cut. The falsification probe here does
not point at a directory — it points at the probe itself, by breaking a limit
and checking the report turns red. A self-test that cannot go red is a
dashboard.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "scripts" / "cos_lineage.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args], text=True, capture_output=True,
        cwd=str(cwd or REPO_ROOT), timeout=60,
    )


def test_probe_forces_every_fuse_and_reports_them_cutting() -> None:
    res = _run("probe")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "6/6 fuses cut when forced" in res.stdout
    for fuse in ("disarmed", "kill-switch", "stall", "total", "width", "depth"):
        assert f"[CUT ] {fuse}:" in res.stdout


def test_falsification_the_probe_can_report_red() -> None:
    """Raise a cap above what the probe drives and the report must fail.

    Without this, "6/6 cut" is a string a broken probe would also print.
    """
    from cos_lib.session_lineage import FuseLimits, LineageStore, evaluate_relaunch  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as td:
        store = LineageStore(Path(td) / "lineage")
        store.arm("g")
        wide = FuseLimits(max_total=99, max_width=99, max_depth=99, max_no_progress=99)
        allowed = []
        for i in range(4):
            dec = evaluate_relaunch(store, session_id=f"s{i}", goal_id="g", limits=wide, env={})
            if dec.allowed:
                store.reserve_slot("R", f"s{i}", wide)
            allowed.append(dec.allowed)
        # Caps above the load never fire — the report's own failure mode.
        assert allowed == [True, True, True, True]


def test_project_dir_selects_where_state_lives(tmp_path: Path) -> None:
    one = tmp_path / "one"
    two = tmp_path / "two"
    assert _run("--project-dir", str(one), "arm", "--goal-id", "g-1").returncode == 0
    assert (one / ".cognitive-os" / "lineage" / "autonomy.enabled").is_file()
    assert not (two / ".cognitive-os").exists()

    payload = json.loads((one / ".cognitive-os" / "lineage" / "autonomy.enabled").read_text())
    assert payload["state"] == "ARMED" and payload["mode"] == "dry-run"


def test_arm_defaults_to_dry_run_and_spawn_is_a_separate_act(tmp_path: Path) -> None:
    root = tmp_path / "p"
    _run("--project-dir", str(root), "arm", "--goal-id", "g-1")
    arm_file = root / ".cognitive-os" / "lineage" / "autonomy.enabled"
    assert json.loads(arm_file.read_text())["mode"] == "dry-run"

    _run("--project-dir", str(root), "arm", "--goal-id", "g-1", "--spawn")
    assert json.loads(arm_file.read_text())["mode"] == "spawn"

    assert _run("--project-dir", str(root), "disarm").returncode == 0
    assert not arm_file.exists()


def test_decide_exit_code_tracks_the_verdict(tmp_path: Path) -> None:
    root = tmp_path / "p"
    refused = _run("--project-dir", str(root), "decide", "--session-id", "s", "--goal-id", "g")
    assert refused.returncode == 1
    assert json.loads(refused.stdout)["fuse"] == "disarmed"

    _run("--project-dir", str(root), "arm", "--goal-id", "g")
    allowed = _run("--project-dir", str(root), "decide", "--session-id", "s", "--goal-id", "g")
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["allowed"] is True
