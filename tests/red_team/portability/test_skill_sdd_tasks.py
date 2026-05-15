from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_sdd_tasks_skill_consumes_eas_gap_matrix() -> None:
    text = (ROOT / "skills" / "sdd-tasks" / "SKILL.md").read_text(encoding="utf-8")

    assert "<!-- SCOPE: both -->" in text
    assert "gap-matrix" in text or "gap matrix" in text.lower()
    assert "REQ-*" in text
    assert "SDD_TASKS" in text


def test_sdd_tasks_skill_passes_scope_classifier() -> None:
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/primitive_scope_classifier.py", "--project-dir", ".", "--paths", "skills/sdd-tasks/SKILL.md", "--fail-contradictions"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
