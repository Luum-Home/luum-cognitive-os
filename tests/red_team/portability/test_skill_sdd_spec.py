from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_sdd_spec_skill_emits_eas_for_shared_sdd_workflow() -> None:
    text = (ROOT / "skills" / "sdd-spec" / "SKILL.md").read_text(encoding="utf-8")

    assert "<!-- SCOPE: both -->" in text
    assert "templates/eas.md" in text
    assert "Executable Acceptance Specification" in text
    assert "SDD_SPEC" in text


def test_sdd_spec_skill_passes_scope_classifier() -> None:
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/primitive_scope_classifier.py", "--project-dir", ".", "--paths", "skills/sdd-spec/SKILL.md", "--fail-contradictions"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
