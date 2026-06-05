from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_init(project: Path, harness: str) -> None:
    project.mkdir()
    (project / "README.md").write_text("consumer\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cos_init.py"), "--default", "--harness", harness],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def hook_commands(settings: dict) -> list[str]:
    commands: list[str] = []
    for groups in settings.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command")
                if isinstance(command, str):
                    commands.append(command)
    return commands


def test_claude_projects_get_quality_duplicate_stop_hook(tmp_path: Path) -> None:
    project = tmp_path / "claude-consumer"
    run_init(project, "claude")

    settings = json.loads((project / ".claude" / "settings.json").read_text())
    assert any("quality-duplicates.sh" in command for command in hook_commands(settings))
    assert (project / ".cognitive-os" / "hooks" / "cos" / "quality-duplicates.sh").exists()
    assert (project / ".cognitive-os" / "bin" / "cos-quality-duplicates").exists()


def test_codex_projects_get_quality_duplicate_shutdown_hook(tmp_path: Path) -> None:
    project = tmp_path / "codex-consumer"
    run_init(project, "codex")

    hooks = json.loads((project / ".codex" / "hooks.json").read_text())
    shutdown = hooks.get("Stop") or hooks.get("shutdown") or hooks.get("SessionEnd") or []
    encoded = json.dumps(shutdown)
    assert "quality-duplicates.sh" in encoded
    assert (project / ".cognitive-os" / "hooks" / "cos" / "quality-duplicates.sh").exists()


def test_opencode_projects_get_quality_duplicate_idle_projection(tmp_path: Path) -> None:
    project = tmp_path / "opencode-consumer"
    run_init(project, "opencode")

    hooks = json.loads((project / ".opencode" / "cos-hooks.json").read_text())
    idle = hooks["events"].get("session.idle", [])
    assert any(item.get("script") == "hooks/quality-duplicates.sh" for item in idle)
    assert (project / ".cognitive-os" / "hooks" / "cos" / "quality-duplicates.sh").exists()


def test_shell_ci_projects_get_quality_duplicate_command_and_workflow(tmp_path: Path) -> None:
    project = tmp_path / "shell-consumer"
    run_init(project, "shell-ci")

    meta = json.loads((project / ".cognitive-os" / "shell-ci-projection.json").read_text())
    projected = {row["source"] for row in meta["projected"]}
    assert "scripts/cos-quality-duplicates" in projected
    assert "scripts/cos_quality_duplicates.py" in projected
    assert (project / "scripts" / "cos-quality-duplicates").exists()
    workflow = (project / ".github" / "workflows" / "cognitive-os-shell-ci.yml").read_text()
    assert "scripts/cos-quality-duplicates" in workflow
