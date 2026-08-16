# SCOPE: os-only
"""Portability proof for scripts/audit_hanging_processes.py.

Falsification probes for the two ways this census can lie:

1. ``etime`` misparsed — ``04:51`` is 4m51s, not 4h51m. A census that reads
   minutes as hours invents long-lived leaks out of short-lived children.
2. The daemon/orphan partition collapsed — both show ``ppid=1``. Calling a
   declared daemon an orphan invents a leak; calling an orphan a daemon hides
   one. The classifier must keep them apart on a synthetic tree with no live
   processes involved.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/audit_hanging_processes.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_hanging_processes", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(pid: int, ppid: int, command: str, etime_s: int = 10) -> dict:
    return {
        "pid": pid,
        "ppid": ppid,
        "etime_s": etime_s,
        "pcpu": 0.0,
        "stat": "S",
        "command": command,
    }


def test_etime_minutes_are_not_read_as_hours() -> None:
    mod = _load_module()
    assert mod.etime_seconds("04:51") == 291
    assert mod.etime_seconds("01:16:52") == 4612
    assert mod.etime_seconds("2-03:00:00") == 183600
    assert mod.etime_seconds("garbage") == 0


def test_daemon_and_orphan_are_not_conflated(tmp_path: Path) -> None:
    """Both have ppid=1; only the one without a daemon marker is a leak."""
    mod = _load_module()
    root = tmp_path / "myrepo"
    rows = [
        _row(100, 1, f"python3 {root}/scripts/watchdog.py --daemon --interval 60"),
        _row(200, 1, f"python3 {root}/scripts/leaky.py"),
        _row(201, 200, f"python3 {root}/scripts/child-of-leaky.py"),
        _row(300, 900, f"bash {root}/hooks/gate.sh"),
        _row(900, 800, "/usr/bin/some-harness --serve-nothing"),
    ]
    by_class = {r["pid"]: r["class"] for r in mod.classify(rows, root)}

    assert by_class[100] == "daemon", "declared daemon must not count as a leak"
    assert by_class[200] == "orphan-root"
    assert by_class[201] == "orphan-descendant", "an orphan's tree is not a live child"
    assert by_class[300] == "live-child", "a live non-repo ancestor means it has an owner"
    assert 900 not in by_class, "processes outside the repo root are out of scope"


def test_summary_counts_only_orphans_as_findings(tmp_path: Path) -> None:
    mod = _load_module()
    root = tmp_path / "myrepo"
    rows = [
        _row(100, 1, f"python3 {root}/scripts/watchdog.py --daemon"),
        _row(200, 1, f"python3 {root}/scripts/leaky.py", etime_s=330),
    ]
    report = mod.summarize(mod.classify(rows, root))
    assert report["orphan_pids"] == [200]
    assert report["oldest_orphan_seconds"] == 330
    assert report["by_class"]["daemon"] == 1


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: must not depend on the OS repo being the cwd."""
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--project-dir", str(tmp_path)],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert '"orphan_pids": []' in result.stdout
