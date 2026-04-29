from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-profile-bootstrap.py"


def _session(project: Path, session_id: str) -> None:
    session_dir = project / ".cognitive-os" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "meta.json").write_text(
        json.dumps({"session_id": session_id, "start_time": "2026-04-29T00:00:00Z", "working_directory": str(project)})
    )


def test_profile_bootstrap_cli_generate_inspect_and_wipe(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo'\n")
    _session(project, "s1")

    generate = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), "generate"],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert generate.returncode == 0, generate.stderr
    draft_path = project / ".cognitive-os" / "project-profile" / "draft.json"
    assert str(draft_path) in generate.stdout
    assert draft_path.exists()

    inspect = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), "inspect"],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert inspect.returncode == 0, inspect.stderr
    data = json.loads(inspect.stdout)
    assert any(entry["value"] == "python" for entry in data["entries"])
    assert str(project) not in inspect.stdout

    wipe = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(project), "wipe"],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert wipe.returncode == 0, wipe.stderr
    assert not draft_path.exists()
