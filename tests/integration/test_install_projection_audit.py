"""Integration guardrails for install projection consistency."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "cos-install-projection-audit"


def _cos_init_default_hooks() -> set[str]:
    source = (ROOT / "scripts" / "cos_init.py").read_text(encoding="utf-8")
    match = re.search(r"DEFAULT_HOOKS = \(\n(.*?)\n\)\.split\(\)", source, re.S)
    assert match is not None
    names = " ".join(re.findall(r'"([^"]*)"', match.group(1))).split()
    return {f"{name}.sh" for name in names}


def _generated_settings_default_hooks() -> set[str]:
    source = (ROOT / "scripts" / "generate-project-settings.sh").read_text(encoding="utf-8")
    match = re.search(r'DEFAULT_HOOKS="(.*?)"', source, re.S)
    assert match is not None
    return set(match.group(1).split())


@pytest.mark.integration
def test_default_project_settings_hook_allowlist_matches_default_installer_copy_set() -> None:
    assert _generated_settings_default_hooks() == _cos_init_default_hooks()


@pytest.mark.integration
def test_install_projection_audit_rejects_dangling_or_scope_excluded_hook_projection() -> None:
    result = subprocess.run(
        [str(AUDIT), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["summary"]["findings"] == 0
    assert payload["summary"]["runs"] == 12
