# SCOPE: os-only
"""Behavior proof for hooks/skill-drift-detector.sh (ADR-285).

The hook compares on-disk SHA-256 of every locked skill against
``skills/REGISTRY.lock`` and warns at SessionStart.  It has run 75 times in the
live plus rotated `hook-timing` ledgers and exited 0 every time — which is what
it does when it finds drift *and* what it does when the detector blows up, so
the exit code carries no information.  The only observable that separates
"checked and clean" from "never actually checked" is the warning text, and that
is what is asserted here.

Deliberately NOT asserted: the ``COS_SKILL_DRIFT_POLICY=block`` path.  The
wrapper ends in ``|| true`` followed by ``exit 0``, so the documented blocking
mode cannot block.  Pinning that in a test would freeze the defect; it is
reported for an operator decision instead.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "skill-drift-detector.sh"

LOCKED_BODY = "# Demo Skill\n\nOriginal, locked body.\n"
SKILL_REL = "skills/demo-skill/SKILL.md"


def _project(tmp_path: Path, *, on_disk: str) -> Path:
    """Project whose REGISTRY.lock pins the hash of LOCKED_BODY."""
    skill = tmp_path / SKILL_REL
    skill.parent.mkdir(parents=True)
    skill.write_text(on_disk, encoding="utf-8")
    locked_sha = hashlib.sha256(LOCKED_BODY.encode()).hexdigest()
    (tmp_path / "skills" / "REGISTRY.lock").write_text(
        "schema_version: 1\n"
        "generated_at: '2026-08-19T00:00:00+00:00'\n"
        "skills:\n"
        f"- path: {SKILL_REL}\n"
        f"  sha256: {locked_sha}\n",
        encoding="utf-8",
    )
    # The hook cds into the project and imports cos_lib from '.'.
    (tmp_path / "cos_lib").symlink_to(REPO / "cos_lib")
    return tmp_path


def _run(project: Path, **extra_env: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"COGNITIVE_OS_PROJECT_DIR": str(project), "CLAUDE_PROJECT_DIR": str(project)})
    env.pop("COS_DISABLE_SKILL_DRIFT_DETECTOR", None)
    env.pop("COS_SKILL_DRIFT_POLICY", None)
    env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input="",
        text=True,
        capture_output=True,
        cwd=project,
        env=env,
        timeout=60,
        check=False,
    )


def _output(result: subprocess.CompletedProcess[str]) -> str:
    # The wrapper folds stderr into stdout (`2>&1`); read both so the assertion
    # survives that detail rather than depending on it.
    return result.stdout + result.stderr


def test_a_mutated_skill_is_named_in_the_warning(tmp_path: Path) -> None:
    project = _project(tmp_path, on_disk="# Demo Skill\n\nSomeone edited this at runtime.\n")

    result = _run(project)

    out = _output(result)
    assert result.returncode == 0, out
    assert "drifted skill(s) detected" in out, f"drift went unreported: {out!r}"
    assert SKILL_REL in out, "the warning must name which skill drifted"
    audit = project / ".cognitive-os" / "metrics" / "skill-drift.jsonl"
    assert audit.is_file() and audit.read_text().strip(), "drift must leave an audit row"
    assert SKILL_REL in audit.read_text()


def test_an_unmodified_skill_produces_no_warning(tmp_path: Path) -> None:
    """The false-positive direction: a clean tree must be silent, or the warning
    becomes noise operators learn to skip."""
    project = _project(tmp_path, on_disk=LOCKED_BODY)

    result = _run(project)

    out = _output(result)
    assert result.returncode == 0, out
    assert "drifted" not in out, f"clean tree reported drift: {out!r}"
    assert SKILL_REL not in out


def test_killswitch_silences_a_real_drift(tmp_path: Path) -> None:
    project = _project(tmp_path, on_disk="# Demo Skill\n\nedited\n")

    result = _run(project, COS_DISABLE_SKILL_DRIFT_DETECTOR="1")

    out = _output(result)
    assert result.returncode == 0, out
    assert out.strip() == "", f"killswitch must be total, not partial: {out!r}"


def test_a_project_without_a_lock_file_is_a_silent_no_op(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()

    result = _run(tmp_path)

    assert result.returncode == 0
    assert _output(result).strip() == ""
