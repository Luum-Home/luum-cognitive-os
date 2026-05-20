"""ADR-329 audit tests for skill platform support levels."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "skill_platform_support_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("skill_platform_support_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_skill(root: Path, name: str, body: str) -> Path:
    path = root / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_repo_generic_cli_skills_declare_support_metadata() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(REPO), "--strict"],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"blockers": 0' in result.stdout


def test_missing_generic_cli_support_is_blocker(tmp_path: Path) -> None:
    audit = _load_module()
    skill = _write_skill(
        tmp_path,
        "bad",
        """---
name: bad
platforms:
- generic-cli
---
<!-- SCOPE: both -->
# Bad
""",
    )

    findings = audit.audit_skill(skill, tmp_path)

    assert [finding.code for finding in findings] == ["missing-platform-support"]


def test_invalid_support_level_and_missing_evidence_are_blockers(tmp_path: Path) -> None:
    audit = _load_module()
    skill = _write_skill(
        tmp_path,
        "bad-level",
        """---
name: bad-level
platforms:
- generic-cli
platform_support:
  generic-cli:
    support_level: magic
    evidence: []
---
<!-- SCOPE: both -->
# Bad Level
""",
    )

    findings = audit.audit_skill(skill, tmp_path)

    assert {finding.code for finding in findings} == {
        "invalid-support-level",
        "missing-platform-evidence",
    }


def test_documented_only_with_evidence_passes(tmp_path: Path) -> None:
    audit = _load_module()
    skill = _write_skill(
        tmp_path,
        "ok",
        """---
name: ok
platforms:
- generic-cli
platform_support:
  generic-cli:
    support_level: documented-only
    evidence:
    - skills/ok/SKILL.md
---
<!-- SCOPE: both -->
# OK
""",
    )

    assert audit.audit_skill(skill, tmp_path) == []
