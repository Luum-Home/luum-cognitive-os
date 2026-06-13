# SCOPE: os-only
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, **(env or {})},
        timeout=60,
    )


def test_so_impact_eval_trigger_runs_from_installed_consumer_projection(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    (project / "README.md").write_text("consumer\n", encoding="utf-8")
    init = _run([sys.executable, str(ROOT / "scripts" / "cos_init.py"), "--default", "--harness", "codex"], project)
    assert init.returncode == 0, init.stderr + init.stdout

    _run(["git", "init"], project)
    _run(["git", "config", "user.email", "test@example.invalid"], project)
    _run(["git", "config", "user.name", "Test"], project)
    _run(["git", "add", "."], project)
    commit = _run(["git", "commit", "-m", "initial"], project)
    assert commit.returncode == 0, commit.stderr + commit.stdout

    engine = project / ".cognitive-os" / "bin" / "cos_so_impact_eval.py"
    engine.write_text(engine.read_text(encoding="utf-8") + "\n# portability marker\n", encoding="utf-8")
    hook = project / ".cognitive-os" / "hooks" / "cos" / "so-impact-eval-trigger.sh"
    result = _run(
        ["bash", str(hook)],
        project,
        env={"COGNITIVE_OS_PROJECT_DIR": str(project), "CODEX_PROJECT_DIR": str(project)},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "ran SO impact smoke" in result.stderr
    metric = project / ".cognitive-os" / "metrics" / "so-impact-eval-trigger.jsonl"
    entry = json.loads(metric.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["status"] == "pass"
    assert (project / entry["report_path"]).exists()
