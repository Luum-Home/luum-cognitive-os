from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_eas_rule_is_shared_and_contextually_triggered() -> None:
    text = (ROOT / "rules" / "eas-evidence-artifact.md").read_text(encoding="utf-8")

    assert "<!-- SCOPE: both -->" in text
    assert "## Contextual Trigger" in text
    assert "Executable Acceptance Specification" in text
    assert "python3 scripts/eas_validate.py" in text


def test_eas_rule_passes_scope_classifier() -> None:
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/primitive_scope_classifier.py", "--project-dir", ".", "--paths", "rules/eas-evidence-artifact.md", "--fail-contradictions"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
