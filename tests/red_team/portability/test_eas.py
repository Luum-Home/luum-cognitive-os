from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_eas_template_is_shared_and_contains_required_sections() -> None:
    text = (ROOT / "templates" / "eas.md").read_text(encoding="utf-8")

    assert "<!-- SCOPE: both -->" in text
    for heading in [
        "## Intent",
        "## Requirements",
        "## Non-goals",
        "## Executable Acceptance Criteria",
        "## Gap Matrix",
        "## Adversarial Personas",
        "## Detractor Mode",
        "## Detractor Objection Log",
        "## Verification Commands",
        "## Residual Risks",
    ]:
        assert heading in text


def test_eas_template_passes_scope_classifier() -> None:
    import subprocess

    result = subprocess.run(
        ["python3", "scripts/primitive_scope_classifier.py", "--project-dir", ".", "--paths", "templates/eas.md", "--fail-contradictions"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
