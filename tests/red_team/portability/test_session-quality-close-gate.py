"""Portability proof for hooks/session-quality-close-gate.sh."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "hooks" / "session-quality-close-gate.sh"


def _portable_project(tmp_path: Path) -> Path:
    project = tmp_path / "portable-consumer"
    project.mkdir()
    hooks = project / "hooks"
    hooks.mkdir()
    shutil.copy(ARTIFACT, hooks / "session-quality-close-gate.sh")
    lib = hooks / "_lib"
    lib.mkdir()
    (lib / "killswitch_check.sh").write_text("# portable test stub\n", encoding="utf-8")
    return project


def _run(project: Path, session_id: str = "portable-session") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CODEX_PROJECT_DIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project),
            "COGNITIVE_OS_SESSION_ID": session_id,
            "PATH": os.environ.get("PATH", ""),
        }
    )
    return subprocess.run(
        ["bash", str(project / "hooks" / "session-quality-close-gate.sh")],
        input="{}",
        text=True,
        capture_output=True,
        cwd=project,
        env=env,
        timeout=20,
        check=False,
    )


def test_session_quality_close_gate_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: hook must not depend on the OS repo cwd."""
    project = _portable_project(tmp_path)

    result = _run(project)

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_session_quality_close_gate_blocks_portable_session_metrics(tmp_path: Path) -> None:
    """Falsification probe: session-scoped metrics resolve under consumer root."""
    project = _portable_project(tmp_path)
    metrics = project / ".cognitive-os" / "sessions" / "portable-session" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "completion-gate.jsonl").write_text(
        json.dumps({"decision": "block", "reason": "portable acceptance evidence missing"}) + "\n",
        encoding="utf-8",
    )

    result = _run(project)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["decision"] == "block"
    assert "portable acceptance evidence missing" in payload["reason"]
