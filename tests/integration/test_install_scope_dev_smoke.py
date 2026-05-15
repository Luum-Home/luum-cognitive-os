"""Integration coverage for dev-like primitive install-scope smoke.

This test intentionally validates the evidence contract, not a marketing claim:
if named scopes collapse or a full-scope hook probe fails, the smoke must say so.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
SMOKE = PROJ_ROOT / "scripts" / "cos-install-scope-dev-smoke"


@pytest.mark.timeout(360)
def test_install_scope_dev_smoke_exercises_all_named_scopes_like_a_dev():
    result = subprocess.run(
        [str(SMOKE), "--json"],
        cwd=str(PROJ_ROOT),
        capture_output=True,
        text=True,
        timeout=330,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    payload = json.loads(result.stdout)
    by_scope = {entry["scope"]: entry for entry in payload["results"]}
    assert set(by_scope) == {"project", "both", "all"}

    for scope in ("project", "both"):
        entry = by_scope[scope]
        checks = entry["dev_like_checks"]
        assert entry["install_ok"] is True
        assert checks["normal_project_tests_pass"] is True
        assert checks["cos_status_json_available"] is True
        assert checks["destructive_git_blocked"] is True
        assert checks["secret_probe_nonfatal_or_blocked"] is True
        assert sum(entry["primitive_os_only_counts"].values()) == 0

    assert by_scope["all"]["total_files"] > by_scope["project"]["total_files"]
    assert sum(by_scope["all"]["primitive_os_only_counts"].values()) > 0

    findings = payload["findings"]
    if findings["project_vs_both_equivalent"]:
        assert "Do not claim three distinct" in findings["recommendation"]
    if not findings["all_extra_hooks_pass_when_present"]:
        assert findings["status"] == "fail"
