"""Integration coverage for dev-real primitive install-scope smoke."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
SMOKE = PROJ_ROOT / "scripts" / "cos-install-scope-dev-smoke"


@pytest.mark.timeout(120)
def test_install_scope_dev_smoke_exercises_named_scopes_like_a_real_dev():
    result = subprocess.run(
        [str(SMOKE), "--json", "--stacks", "python"],
        cwd=str(PROJ_ROOT),
        capture_output=True,
        text=True,
        timeout=110,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cos-install-scope-dev-smoke/v2"

    active = [entry for entry in payload["results"] if not entry.get("skipped")]
    assert {entry["scope"] for entry in active} == {"project", "both", "all"}
    assert {entry["stack"] for entry in active} == {"python"}

    for entry in active:
        checks = entry["dev_like_checks"]
        assert entry["install_ok"] is True
        assert checks["baseline_tests_pass"] is True
        assert checks["intentional_bug_failed"] is True
        assert checks["fixed_tests_pass"] is True
        assert checks["task_failed_then_fixed"] is True
        assert checks["eas_or_skill_contract_valid"] is True
        assert checks["cos_status_json_available"] is True
        assert checks["destructive_git_blocked"] is True
        assert checks["secret_probe_nonfatal_or_blocked"] is True
        assert checks["safe_git_not_blocked"] is True
        assert entry["friction_steps"] >= 5

    for entry in active:
        if entry["scope"] in {"project", "both"}:
            assert sum(entry["primitive_os_only_counts"].values()) == 0

    project = next(entry for entry in active if entry["scope"] == "project")
    both = next(entry for entry in active if entry["scope"] == "both")
    all_scope = next(entry for entry in active if entry["scope"] == "all")
    assert all_scope["total_files"] > project["total_files"]
    assert all_scope["total_files"] > both["total_files"]
    assert sum(all_scope["primitive_os_only_counts"].values()) > 0

    findings = payload["findings"]
    if findings["project_vs_both_equivalent"]:
        assert "Do not claim three distinct" in findings["recommendation"]
    if not findings["all_default_justified"]:
        assert findings["product_verdict"] != "all-cos-default"
    if findings["protected_config_guard_gap"]:
        assert findings["status"] in {"fail-product-safety-gap", "fail"}
