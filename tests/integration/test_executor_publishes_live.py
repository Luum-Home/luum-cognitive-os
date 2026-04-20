"""Integration — ADR-034 cos-executor republishes FallbackBus events.

This test exercises the *fallback* path (no Valkey required): we drop a
JSONL event in ``.cognitive-os/agent-bus/<id>/progress.jsonl`` and assert
the executor re-publishes it to the canonical live stream
(``.cognitive-os/metrics/canonical-live.jsonl``).

Running Valkey is NOT a CI prerequisite — the executor detects its
absence and engages the file-tail loop.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest


def _load_executor(project_dir: Path):
    """Load scripts/cos-executor.py into a named module with patched cwd."""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "scripts" / "cos-executor.py"
    assert path.exists(), f"missing {path}"

    # cos-executor uses CLAUDE_PROJECT_DIR / COGNITIVE_OS_PROJECT_DIR.
    os.environ["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)

    mod_name = "cos_executor_under_test"
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    # Force the executor down the fallback path by pointing VALKEY_URL at a
    # dead port.
    monkeypatch.setenv("VALKEY_URL", "redis://127.0.0.1:1")
    monkeypatch.setenv("COS_VALKEY_URL", "redis://127.0.0.1:1")
    yield tmp_path


def test_executor_republishes_fallback_events(isolated_project):
    project = isolated_project
    module = _load_executor(project)

    # Prepare an agent-bus file before starting the executor loop.
    bus_dir = project / ".cognitive-os" / "agent-bus" / "agent-abc"
    bus_dir.mkdir(parents=True)
    progress_file = bus_dir / "progress.jsonl"

    sample = {
        "event_type": "progress_marker",
        "agent_id": "agent-abc",
        "ts": time.time(),
        "step_current": 3,
        "step_total": 7,
        "message": "pytest green",
    }
    progress_file.write_text(json.dumps(sample) + "\n")

    executor = module.CosExecutor(valkey_url="redis://127.0.0.1:1")
    t = threading.Thread(target=executor.run, daemon=True)
    t.start()

    canonical = project / ".cognitive-os" / "metrics" / "canonical-live.jsonl"
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if canonical.exists() and canonical.read_text().strip():
            break
        time.sleep(0.1)

    executor.stop()
    t.join(timeout=3.0)

    assert canonical.exists(), "executor did not create canonical-live.jsonl"
    lines = [json.loads(l) for l in canonical.read_text().splitlines() if l.strip()]
    assert lines, "no events were republished"
    assert any(l.get("agent_id") == "agent-abc" for l in lines)


def test_executor_pid_file_guard(isolated_project):
    module = _load_executor(isolated_project)

    # Write a pid file pointing to a definitely-alive pid (this process).
    pf = module._pid_file()
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(str(os.getpid()))

    # _cmd_daemon should early-return 0 and NOT fork.
    rc = module._cmd_daemon()
    assert rc == 0


def test_executor_status_cli(isolated_project):
    module = _load_executor(isolated_project)
    rc = module._cmd_status()
    # DEAD before we start anything.
    assert rc == 1

    # Write a live pid file manually.
    pf = module._pid_file()
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(str(os.getpid()))
    rc = module._cmd_status()
    assert rc == 0
