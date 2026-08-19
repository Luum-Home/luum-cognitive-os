"""Behavior tests for hooks/skill-feedback-tracker.sh: the `skill` field.

Guards the regression that produced 198/198 rows naming a skill that does not
exist in .cognitive-os/metrics/skill-feedback.jsonl -- the operator home path
the operator home path was recorded as the skill named after the username, and
`/private/tmp/...` as the skill "private". Those rows are read back as skill identifiers by
cos_lib/skill_failure_repair.py and cos_lib/consumer_improvement_proposals.py,
which emitted "Review degraded skill matias".

The contract these tests pin: the hook writes a row ONLY when the prompt names
a skill that resolves to a SKILL.md on disk, and the value written is that
skill's directory name.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "skill-feedback-tracker.sh"

# Built at runtime, never written as a literal: rules/local-privacy-hygiene.md
# blocks committing a home path, and the whole point of this file is that such a
# path used to become a skill name.
_HOME_DIR = Path.home()
_HOME_LIKE = "/".join(["", _HOME_DIR.parent.name, "someoperator", "Projects", "demo"])
_OPERATOR_USER = _HOME_DIR.name

# Prompts that must never yield a row: none of them names a real skill.
NON_SKILL_PROMPTS = [
    f"Repo: {_HOME_LIKE}/luum-agent-os. Auditar la telemetria.",
    "Usa /private/tmp/claude-501/scratchpad/ag-x/ como scratchpad exclusivo.",
    "Leer docs/06-Daily/reports/ y /runbooks/deploy y despues commitear.",
    "Revisar skills/definitely-not-a-real-skill/SKILL.md por favor.",
    "El hook /research-compliance-guard fallo con exit-2.",
    "Sin ninguna ruta ni referencia: hace el trabajo y listo.",
]


def _run_hook(project_dir: Path, prompt: str, response: str = "done") -> None:
    payload = {
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
        "tool_response": {"content": response},
    }
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env.pop("COGNITIVE_OS_SESSION_ID", None)
    env.pop("SO_KILLSWITCH", None)
    subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(project_dir),
        check=False,
    )


def _rows(project_dir: Path) -> list[dict]:
    log = project_dir / ".cognitive-os" / "metrics" / "skill-feedback.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    if Path("/tmp/claude-private-mode-active").exists():
        pytest.skip("private mode active: the hook exits before writing")
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    for name in ("real-fixture-skill", "another-real-skill"):
        skill_dir = tmp_path / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n")
    return tmp_path


@pytest.mark.parametrize("prompt", NON_SKILL_PROMPTS)
def test_prompt_without_a_real_skill_writes_no_row(project: Path, prompt: str) -> None:
    _run_hook(project, prompt)
    assert _rows(project) == [], (
        "the hook invented a skill name out of free text / a filesystem path: "
        f"{_rows(project)}"
    )


def test_operator_username_never_reaches_telemetry(project: Path) -> None:
    _run_hook(project, f"Repo en {_HOME_DIR}/Projects/x - analizar eso.")
    log = project / ".cognitive-os" / "metrics" / "skill-feedback.jsonl"
    body = log.read_text() if log.exists() else ""
    assert _OPERATOR_USER not in body, (
        "operator username leaked into skill-feedback.jsonl"
    )


def test_skill_load_directive_is_recorded(project: Path) -> None:
    _run_hook(project, "SKILL: Load `skills/real-fixture-skill/SKILL.md` and work.")
    rows = _rows(project)
    assert len(rows) == 1, f"expected exactly one row, got {rows}"
    assert rows[0]["skill"] == "real-fixture-skill"
    assert rows[0]["success"] is True


def test_bare_skills_reference_is_recorded(project: Path) -> None:
    _run_hook(project, "Segui lo que dice skills/another-real-skill para esto.")
    rows = _rows(project)
    assert len(rows) == 1, f"expected exactly one row, got {rows}"
    assert rows[0]["skill"] == "another-real-skill"


def test_failure_is_still_detected_for_a_real_skill(project: Path) -> None:
    _run_hook(
        project,
        "SKILL: Load `skills/real-fixture-skill/SKILL.md`",
        response="ESCALATION: build failed",
    )
    rows = _rows(project)
    assert len(rows) == 1
    assert rows[0]["skill"] == "real-fixture-skill"
    assert rows[0]["success"] is False


def test_every_written_skill_resolves_on_disk(project: Path) -> None:
    """Property over the whole battery: no row may name a non-existent skill."""
    prompts = NON_SKILL_PROMPTS + [
        "SKILL: Load `skills/real-fixture-skill/SKILL.md`",
        "mira skills/another-real-skill/SKILL.md",
    ]
    for prompt in prompts:
        _run_hook(project, prompt)
    rows = _rows(project)
    assert rows, "battery produced no rows at all — the hook stopped recording"
    for row in rows:
        skill_md = project / "skills" / row["skill"] / "SKILL.md"
        assert skill_md.is_file(), f"row names a skill that does not exist: {row}"
