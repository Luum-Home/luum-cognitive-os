from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_sdd_verify_skill_runs_eas_validator() -> None:
    text = (ROOT / "skills" / "sdd-verify" / "SKILL.md").read_text(encoding="utf-8")

    assert "<!-- SCOPE: both -->" in text
    assert "python3 scripts/eas_validate.py" in text
    assert "SDD_VERIFY" in text


def test_sdd_verify_skill_passes_scope_classifier() -> None:
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/primitive_scope_classifier.py", "--project-dir", ".", "--paths", "skills/sdd-verify/SKILL.md", "--fail-contradictions"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
