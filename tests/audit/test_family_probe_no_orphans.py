# SCOPE: os-only
"""The family probe must not leak a candidate's subprocess tree onto init.

Regression test for the orphan leak found on 2026-08-15: 28 live
``cos_primitive_closure_check.py`` processes with ``ppid=1``, each still
driving the real ACC pipeline minutes after the probe that spawned them was
gone. ``subprocess.run(timeout=...)`` kills only the direct child, so every
candidate that had itself forked a subprocess left that subtree running.

This test executes the real ``run_candidate`` against a candidate that forks a
long-lived grandchild, then asserts the grandchild is dead once the probe's
timeout has fired. It fails on the pre-fix code and passes on the fixed code.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROBE_PATH = REPO / "scripts" / "family_conformance_probe.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("family_conformance_probe", PROBE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["family_conformance_probe"] = module
    spec.loader.exec_module(module)
    return module


# A candidate that forks a grandchild and then hangs, exactly the shape that
# leaked: the probe's timeout reaches the parent, the grandchild survives it.
LEAKY_CANDIDATE = """\
import subprocess, sys, time

pidfile = sys.argv[1]
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(120)"]
)
with open(pidfile, "w") as handle:
    handle.write(str(child.pid))
time.sleep(120)
"""


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@pytest.mark.skipif(os.name == "nt", reason="process groups are POSIX-only here")
def test_run_candidate_kills_the_whole_candidate_tree(tmp_path, monkeypatch):
    probe = _load_probe()
    monkeypatch.setattr(probe, "TIMEOUT_S", 3)

    candidate = tmp_path / "leaky_candidate.py"
    candidate.write_text(LEAKY_CANDIDATE)

    sandbox = tmp_path / "sbx"
    (sandbox / "home").mkdir(parents=True)
    pidfile = tmp_path / "grandchild.pid"

    outcome, detail = probe.run_candidate(
        candidate,
        candidate,  # source: .py suffix selects the python3 interpreter
        [str(pidfile)],
        sandbox,
        "fixture.md",
        "",
    )

    assert outcome == probe.UNMEASURABLE, f"expected a timeout verdict, got {outcome}/{detail}"
    assert detail == "timeout"

    assert pidfile.exists(), "candidate never forked its grandchild; test is not exercising the leak"
    grandchild = int(pidfile.read_text().strip())

    # Give the group kill a moment to be reaped by the kernel.
    for _ in range(20):
        if not _pid_alive(grandchild):
            break
        time.sleep(0.1)

    assert not _pid_alive(grandchild), (
        f"grandchild pid {grandchild} survived the probe timeout: "
        "the candidate's subprocess tree is leaking onto init"
    )


@pytest.mark.skipif(os.name == "nt", reason="process groups are POSIX-only here")
def test_run_candidate_still_classifies_a_normal_candidate(tmp_path):
    """The group-kill change must not disturb the ordinary verdicts."""
    probe = _load_probe()

    sandbox = tmp_path / "sbx"
    (sandbox / "home").mkdir(parents=True)

    silent = tmp_path / "silent.py"
    silent.write_text("import sys; sys.exit(0)\n")
    assert probe.run_candidate(silent, silent, [], sandbox, "fixture.md", "")[0] == probe.SILENT

    blocking = tmp_path / "blocking.py"
    blocking.write_text("import sys; sys.exit(2)\n")
    assert probe.run_candidate(blocking, blocking, [], sandbox, "fixture.md", "")[0] == probe.BLOCKED

    reads_stdin = tmp_path / "echoes.py"
    reads_stdin.write_text("import sys; sys.stdout.write(sys.stdin.read()); sys.exit(0)\n")
    outcome, detail = probe.run_candidate(
        reads_stdin, reads_stdin, [], sandbox, "fixture.md", "payload-from-stdin"
    )
    assert outcome == probe.SILENT
    assert "out=18b" in detail, f"stdin was not delivered to the candidate: {detail}"
