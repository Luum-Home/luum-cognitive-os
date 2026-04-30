"""Behavioral contracts for canonical-first artifact projection.

These tests intentionally go beyond structural checks such as "SKILL.md exists".
They install Cognitive OS into throwaway projects and verify that artifacts are
usable from the canonical `.cognitive-os/` contract and projected into harness
drivers without becoming the runtime source of truth.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.paths import preferred_rules_dirs
from lib.skill_routing import find_skill_md


pytestmark = [pytest.mark.contract, pytest.mark.timeout(120)]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COS_INIT = PROJECT_ROOT / "scripts" / "cos-init.sh"
SOURCE_SKILLS = PROJECT_ROOT / "skills"
SOURCE_RULES = PROJECT_ROOT / "rules"


def _run_cos_init(project: Path, mode: str = "--full", harness: str = "claude") -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COS_SOURCE_DIR"] = str(PROJECT_ROOT)
    env["COS_REGISTRY_FILE"] = str(project / ".cos-test-registry.json")
    env["HOME"] = str(project)
    return subprocess.run(
        ["bash", str(COS_INIT), mode, f"--harness={harness}"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _source_skill_names() -> list[str]:
    return sorted(
        p.name
        for p in SOURCE_SKILLS.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file() and _skill_audience_allows(p / "SKILL.md")
    )


def _scope_allows(path: Path) -> bool:
    first_lines = "\n".join(path.read_text(errors="replace").splitlines()[:3])
    return "SCOPE: os-only" not in first_lines


def _skill_audience_allows(path: Path) -> bool:
    lines = path.read_text(errors="replace").splitlines()
    in_frontmatter = False
    saw_frontmatter = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            if not saw_frontmatter:
                in_frontmatter = True
                saw_frontmatter = True
                continue
            break
        if saw_frontmatter and not in_frontmatter:
            break
        if stripped.startswith(("audience:", "scope:")):
            value = stripped.split(":", 1)[1].strip().strip("'\"")
            return value not in {"os", "os-dev", "os-only"}
    return True


def _source_rule_names() -> list[str]:
    return sorted(p.name for p in SOURCE_RULES.glob("*.md") if _scope_allows(p))


def _hook_commands(settings: dict) -> list[str]:
    commands: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            command = value.get("command")
            if isinstance(command, str):
                commands.append(command)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(settings.get("hooks", settings))
    return commands


def _shell_script_paths(command: str) -> list[str]:
    """Return every absolute-ish .sh path embedded in a hook command.

    Commands may invoke instrumentation first and pass the real hook as a later
    argument, e.g. `bash .../_lib/hook-timing-wrapper.sh Event .../hook.sh`.
    The projection contract is stronger than "the last hook exists": every COS
    script referenced by the driver must be installed in canonical storage.
    """
    return re.findall(r"((?:\$?\{[^}]+}|\$?[A-Za-z_][A-Za-z0-9_]*|/|[A-Za-z0-9_.:-])+[^\"'\s]*\.sh)(?:\"|'|\s|$)", command)


def test_full_install_projects_all_skills_to_canonical_and_runtime_discovery(tmp_path: Path) -> None:
    """Every source skill must install to canonical storage and be discoverable."""
    project = tmp_path / "client"
    project.mkdir()
    (project / "package.json").write_text('{"name": "client"}\n')

    result = _run_cos_init(project, "--full", "claude")
    assert result.returncode == 0, result.stderr

    canonical = project / ".cognitive-os" / "skills" / "cos"
    driver = project / ".claude" / "skills"
    source_names = _source_skill_names()
    assert source_names, "source skills/ must contain at least one installable skill"

    missing_canonical = [
        name for name in source_names if not (canonical / name / "SKILL.md").is_file()
    ]
    missing_driver = [
        name for name in source_names if not (driver / name / "SKILL.md").is_file()
    ]
    assert not missing_canonical, f"skills missing from canonical projection: {missing_canonical}"
    assert not missing_driver, f"skills missing from Claude driver projection: {missing_driver}"

    shutil.rmtree(driver)
    undiscoverable = [
        name
        for name in source_names
        if find_skill_md(name, project) != canonical / name / "SKILL.md"
    ]
    assert not undiscoverable, (
        "runtime discovery must work from canonical skills without .claude/skills: "
        f"{undiscoverable}"
    )


def test_full_install_projects_all_rules_to_canonical_and_driver(tmp_path: Path) -> None:
    """Rules are policy artifacts: install must write canonical truth plus driver view."""
    project = tmp_path / "client"
    project.mkdir()
    (project / "package.json").write_text('{"name": "client"}\n')

    result = _run_cos_init(project, "--full", "claude")
    assert result.returncode == 0, result.stderr

    canonical = project / ".cognitive-os" / "rules" / "cos"
    driver = project / ".claude" / "rules" / "cos"
    source_rules = _source_rule_names()
    assert source_rules, "source rules/ must contain at least one rule"

    missing_canonical = [name for name in source_rules if not (canonical / name).is_file()]
    missing_driver = [name for name in source_rules if not (driver / name).is_file()]
    assert not missing_canonical, f"rules missing from canonical projection: {missing_canonical}"
    assert not missing_driver, f"rules missing from Claude driver projection: {missing_driver}"

    shutil.rmtree(project / ".claude" / "rules")
    preferred = preferred_rules_dirs(project)
    assert preferred[0] == canonical
    assert (preferred[0] / "RULES-COMPACT.md").is_file()


def test_codex_projection_commands_point_to_installed_hooks(tmp_path: Path) -> None:
    """Codex hooks.json must point at installed canonical hook files, not source paths."""
    project = tmp_path / "codex-client"
    project.mkdir()
    (project / "package.json").write_text('{"name": "codex-client"}\n')

    result = _run_cos_init(project, "--full", "codex")
    assert result.returncode == 0, result.stderr

    hooks_path = project / ".codex" / "hooks.json"
    assert hooks_path.is_file(), "Codex driver projection must write .codex/hooks.json"
    settings = json.loads(hooks_path.read_text())
    commands = _hook_commands(settings)
    assert commands, "Codex projection must register executable hooks"
    assert all("CODEX_PROJECT_DIR" in command for command in commands), commands
    assert all("$CLAUDE_PROJECT_DIR/hooks/" not in command for command in commands), commands

    missing: list[str] = []
    not_executable: list[str] = []
    for command in commands:
        for script_path in _shell_script_paths(command):
            filename = Path(script_path).name
            if filename == "hook-timing-wrapper.sh":
                installed = project / ".cognitive-os" / "hooks" / "cos" / "_lib" / filename
            else:
                installed = project / ".cognitive-os" / "hooks" / "cos" / filename
            if not installed.is_file():
                missing.append(str(installed.relative_to(project)))
            elif not os.access(installed, os.X_OK):
                not_executable.append(str(installed.relative_to(project)))

    assert not missing, f"Codex projection references hooks not installed in canonical storage: {missing}"
    assert not not_executable, f"Codex projection references non-executable hooks: {not_executable}"


def test_codex_install_keeps_rules_and_skills_out_of_claude_driver(tmp_path: Path) -> None:
    """Codex installs canonical artifacts without making `.claude/` a center of gravity."""
    project = tmp_path / "codex-client"
    project.mkdir()
    (project / "package.json").write_text('{"name": "codex-client"}\n')

    result = _run_cos_init(project, "--full", "codex")
    assert result.returncode == 0, result.stderr

    canonical_rules = project / ".cognitive-os" / "rules" / "cos"
    canonical_skills = project / ".cognitive-os" / "skills" / "cos"

    assert (project / ".codex" / "hooks.json").is_file()
    assert (canonical_rules / "RULES-COMPACT.md").is_file()
    assert (canonical_skills / "CATALOG.md").is_file()
    assert any((canonical_skills / name / "SKILL.md").is_file() for name in _source_skill_names())

    assert not (project / ".claude" / "rules" / "cos").exists()
    assert not (project / ".claude" / "skills").exists()
