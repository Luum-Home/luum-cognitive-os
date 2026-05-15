from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_sdd_apply_skill_records_eas_evidence() -> None:
    text = (ROOT / "skills" / "sdd-apply" / "SKILL.md").read_text(encoding="utf-8")

    assert "<!-- SCOPE: both -->" in text
    assert "REQ-*" in text
    assert "AC-*" in text
    assert "SDD_APPLY" in text


def test_sdd_apply_skill_passes_scope_classifier() -> None:
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/primitive_scope_classifier.py", "--project-dir", ".", "--paths", "skills/sdd-apply/SKILL.md", "--fail-contradictions"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
