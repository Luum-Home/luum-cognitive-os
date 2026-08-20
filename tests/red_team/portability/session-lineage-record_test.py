# SCOPE: os-only
"""Portability probes for the SessionStart lineage recorder.

The hook is declared os-only, which is a claim about where it is INSTALLED,
not a licence to hardcode this checkout. Each probe points the hook at a
project root that is not this repository and checks the effect landed there.
The falsification probe is the one that gives the others meaning: it asserts
the destination actually follows the environment, so a hook that wrote to a
fixed path would fail rather than quietly pass.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "session-lineage-record.sh"


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
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.update(extra)
    return env


def _run(project: Path, session_id: str, **extra: str) -> subprocess.CompletedProcess:
    payload = json.dumps({
        "hook_event_name": "SessionStart", "session_id": session_id,
        "timestamp": "2026-08-19T00:00:00Z", "source": "startup",
    })
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, text=True, capture_output=True,
        cwd=str(project), env=_env(project, **extra), timeout=30,
    )


def test_writes_into_the_project_it_was_pointed_at(tmp_path: Path) -> None:
    project = _project(tmp_path)
    res = _run(project, "sess-a")
    assert res.returncode == 0, res.stderr
    ledger = project / ".cognitive-os" / "lineage" / "lineage.jsonl"
    assert ledger.is_file()
    assert json.loads(ledger.read_text().splitlines()[0])["session_id"] == "sess-a"


def test_falsification_two_project_roots_do_not_share_a_ledger(tmp_path: Path) -> None:
    """The probe that makes the others meaningful.

    If the destination were hardcoded, both runs would land in one file and
    this assertion would fail. It is the only way to tell "respects the
    environment" from "happened to work once".
    """
    one = _project(tmp_path, "one")
    two = _project(tmp_path, "two")
    _run(one, "sess-one")
    _run(two, "sess-two")

    read = lambda p: (p / ".cognitive-os" / "lineage" / "lineage.jsonl").read_text()  # noqa: E731
    assert "sess-one" in read(one) and "sess-two" not in read(one)
    assert "sess-two" in read(two) and "sess-one" not in read(two)


def test_missing_session_id_writes_nothing(tmp_path: Path) -> None:
    project = _project(tmp_path)
    env = _env(project)
    env.pop("CLAUDE_SESSION_ID", None)
    res = subprocess.run(
        ["bash", str(HOOK)], input=json.dumps({"hook_event_name": "SessionStart"}),
        text=True, capture_output=True, cwd=str(project), env=env, timeout=30,
    )
    assert res.returncode == 0
    assert not (project / ".cognitive-os" / "lineage").exists()


def test_runtime_disable_switch_is_honoured(tmp_path: Path) -> None:
    project = _project(tmp_path)
    res = _run(project, "sess-a", DISABLE_HOOK_SESSION_LINEAGE_RECORD="true")
    assert res.returncode == 0
    assert not (project / ".cognitive-os" / "lineage").exists()
