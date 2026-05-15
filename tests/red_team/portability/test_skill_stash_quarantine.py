from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_stash_quarantine_skill_has_behavioral_audit_handoff() -> None:
    result = subprocess.run(
        ["python3", "scripts/primitive_scope_classifier.py", "--project-dir", ".", "--paths", "skills/stash-quarantine/SKILL.md", "--fail-contradictions"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    text = (ROOT / "skills" / "stash-quarantine" / "SKILL.md").read_text(encoding="utf-8")
    assert "scripts/stash_quarantine_audit.py" in text
