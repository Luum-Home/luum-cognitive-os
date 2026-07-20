# SCOPE: os-only
"""Portability proof for cos_lib/state_heartbeat.py.

Pins that ``StateHeartbeat`` persists and reloads a real snapshot using only
paths relative to the caller-supplied ``session_dir`` — a directory layout
every consumer project has (``.cognitive-os/sessions/{id}/``), not one
specific to the Cognitive OS source repo — when the process cwd is an
unrelated arbitrary directory.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/state_heartbeat.py"


def _load_module(monkeypatch, cwd: Path):
    monkeypatch.chdir(cwd)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_state_heartbeat", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_state_heartbeat_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    _load_module(monkeypatch, tmp_path)


def test_state_heartbeat_saves_and_reloads_snapshot_from_arbitrary_cwd(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: save()/load() must round-trip a real snapshot
    using only the caller-supplied session_dir, from a cwd that shares no
    relationship with the OS repo or the session_dir itself.
    """
    # cwd is deliberately a sibling directory, not the session_dir and not
    # the OS repo checkout — proves no hidden reliance on process cwd.
    unrelated_cwd = tmp_path / "somewhere-else"
    unrelated_cwd.mkdir()
    session_dir = tmp_path / "consumer-project" / ".cognitive-os" / "sessions" / "abc123"

    module = _load_module(monkeypatch, unrelated_cwd)
    StateHeartbeat = module.StateHeartbeat

    heartbeat = StateHeartbeat(str(session_dir))
    heartbeat.register("custom_probe", lambda: {"value": 42})
    heartbeat.save()

    snapshot_path = session_dir / "state-snapshot.json"
    assert snapshot_path.exists()

    loaded = heartbeat.load()
    assert loaded is not None
    assert loaded["custom_probe"] == {"value": 42}
    assert loaded["session_dir"] == str(session_dir)
    # Built-in collectors must degrade gracefully rather than raising when
    # their expected project files are absent from this bare tmp project.
    assert loaded["active_tasks"]["status"] == "unavailable"
    assert loaded["pending_requests"] == {"pending": [], "total": 0}

    prompt = heartbeat.format_recovery_prompt()
    assert "PREVIOUS SESSION STATE" in prompt
