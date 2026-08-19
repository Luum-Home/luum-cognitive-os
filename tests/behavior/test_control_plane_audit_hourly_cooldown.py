# SCOPE: os-only
"""Behavior proof for hooks/control-plane-audit-hourly.sh (ADR-248).

The hook is a cooldown wrapper: it decides, on every Stop, whether the
expensive control-plane sweep runs at all.  That sweep peaked at 174s in
`.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz`, so a regression that
drops the cooldown turns every session end into a multi-minute stall, and a
regression that never clears it silently retires the sweep.  Neither failure
changes the exit code (always 0), so telemetry cannot see it.

What is asserted here is the decision, observed through a stub sweep that
records its own invocation and environment.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "control-plane-audit-hourly.sh"
STAMP_REL = ".cognitive-os/runtime/control-plane-audit/hourly.last"


def _project(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal project dir whose control-plane-audit.sh is a recording stub."""
    hooks = tmp_path / "hooks"
    hooks.mkdir(parents=True)
    sentinel = tmp_path / "sweep-ran.txt"
    (hooks / "control-plane-audit.sh").write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s|%s\\n" "${{COS_CONTROL_PLANE_AUDIT_LANE:-}}" '
        f'"${{COS_CONTROL_PLANE_AUDIT_MODE:-}}" >> "{sentinel}"\n',
        encoding="utf-8",
    )
    return tmp_path, sentinel


def _run(project: Path, cooldown: str = "3600") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project),
            "COS_CONTROL_PLANE_HOURLY_COOLDOWN_SECONDS": cooldown,
        }
    )
    return subprocess.run(
        ["bash", str(HOOK)],
        input="",
        text=True,
        capture_output=True,
        cwd=project,
        env=env,
        timeout=30,
        check=False,
    )


def test_first_stop_ever_runs_the_sweep_and_stamps_the_clock(tmp_path: Path) -> None:
    project, sentinel = _project(tmp_path)
    before = int(time.time())

    result = _run(project)

    assert result.returncode == 0, result.stderr
    assert sentinel.exists(), "no stamp yet, so the sweep must run: it did not"
    assert sentinel.read_text().strip() == "hourly|warn", (
        "the sweep must be told which lane and mode it is running under"
    )
    stamp = project / STAMP_REL
    assert stamp.is_file(), "the wrapper must record when it last swept"
    assert int(stamp.read_text().strip()) >= before


def test_second_stop_inside_the_window_does_not_re_sweep(tmp_path: Path) -> None:
    project, sentinel = _project(tmp_path)
    _run(project)
    assert sentinel.read_text().count("\n") == 1
    stamp = project / STAMP_REL
    first = stamp.read_text()

    result = _run(project)

    assert result.returncode == 0, result.stderr
    assert sentinel.read_text().count("\n") == 1, (
        "the cooldown must suppress the second sweep, not merely delay it"
    )
    assert stamp.read_text() == first, "a suppressed run must not push the clock forward"


def test_stop_after_the_window_sweeps_again(tmp_path: Path) -> None:
    project, sentinel = _project(tmp_path)
    stamp = project / STAMP_REL
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stale = int(time.time()) - 7200
    stamp.write_text(f"{stale}\n", encoding="utf-8")

    result = _run(project)

    assert result.returncode == 0, result.stderr
    assert sentinel.exists() and sentinel.read_text().count("\n") == 1, (
        "a stamp older than the cooldown must not keep the sweep retired"
    )
    assert int(stamp.read_text().strip()) > stale


def test_unreadable_stamp_is_treated_as_never_swept(tmp_path: Path) -> None:
    """A corrupt stamp must fail toward running the sweep, not toward silence."""
    project, sentinel = _project(tmp_path)
    stamp = project / STAMP_REL
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text("", encoding="utf-8")

    result = _run(project)

    assert result.returncode == 0, result.stderr
    assert sentinel.exists(), "an empty stamp must not be read as 'swept just now'"
