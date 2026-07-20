# SCOPE: os-only
"""Portability proof for cos_lib/metric_event.py.

Pins that MetricEvent construction, JSONL round-tripping, and append_event()
work from an arbitrary working directory with no dependency on the OS repo
tree — the module only touches paths explicitly passed in by the caller.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/metric_event.py"


def test_metric_event_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_metric_event", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_append_event_round_trips_from_arbitrary_cwd(tmp_path: Path) -> None:
    """Falsification probe: append a real event to a tmp_path file, in a
    subprocess run from an arbitrary cwd, and read it back.

    Proves append_event() has no hidden dependency on running inside the
    Cognitive OS source repo (e.g. relative paths, sibling manifests).
    """
    consumer_cwd = tmp_path / "consumer_project"
    consumer_cwd.mkdir()
    events_path = tmp_path / "metrics" / "events.jsonl"

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.metric_event import MetricEvent, append_event\n"
        "event = MetricEvent(source='portability-test', event_type='probe.ran', "
        "payload={'ok': True})\n"
        "ok = append_event(%r, event)\n"
        "print('APPEND_OK' if ok else 'APPEND_FAILED')\n"
    ) % (str(REPO_ROOT), str(events_path))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=consumer_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "APPEND_OK" in result.stdout, result.stdout + result.stderr

    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["source"] == "portability-test"
    assert row["event_type"] == "probe.ran"
    assert row["payload"] == {"ok": True}
