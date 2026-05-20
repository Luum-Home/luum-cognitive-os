"""Behavioral tests for the SO-only /os-session-wrapup addendum trigger."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "session-wrapup-trigger.sh"
SKILL = REPO_ROOT / "skills" / "os-session-wrapup" / "SKILL.md"


def run_hook(prompt: str, project_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "CODEX_PROJECT_DIR": str(project_dir),
            "CLAUDE_PROJECT_DIR": str(project_dir),
        }
    )
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"user_prompt": prompt}),
        text=True,
        capture_output=True,
        cwd=project_dir,
        env=env,
        timeout=10,
        check=False,
    )


def parse_output(result: subprocess.CompletedProcess) -> dict | None:
    stdout = result.stdout.strip()
    return json.loads(stdout) if stdout else None


def make_consumer_project(tmp_path: Path) -> Path:
    (tmp_path / ".cognitive-os").mkdir()
    (tmp_path / "hooks").mkdir()
    return tmp_path


def test_os_reality_prompt_suggests_os_session_wrapup_addendum() -> None:
    result = run_hook("¿todas las primitivas están controladas o quedó aspirational?", REPO_ROOT)

    assert result.returncode == 0, result.stderr
    payload = parse_output(result)
    assert payload is not None
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "/os-session-wrapup" in context
    assert "aspirational_audit.py --dry-run --json --project-root ." in context


def test_consumer_project_closure_does_not_get_os_addendum(tmp_path: Path) -> None:
    project = make_consumer_project(tmp_path)

    result = run_hook("close session", project)

    assert result.returncode == 0, result.stderr
    payload = parse_output(result)
    assert payload is not None
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "/session-wrapup" in context
    assert "/os-session-wrapup" not in context
    assert "aspirational_audit.py" not in context


def test_os_session_wrapup_skill_is_os_only_and_keeps_session_wrapup_generic() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "<!-- SCOPE: os-only -->" in text
    assert "python3 scripts/aspirational_audit.py --dry-run --json --project-root ." in text
    assert "Invoke `/session-wrapup`" in text

    frontmatter = text.split("---", 2)[1]
    data = yaml.safe_load(frontmatter)
    assert data["name"] == "os-session-wrapup"
    assert data["audience"] == "os-dev"
    assert {"claude-code", "codex", "generic-cli"}.issubset(set(data["platforms"]))
