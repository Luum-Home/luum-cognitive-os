import json
import subprocess

import pytest


@pytest.mark.behavior
def test_reward_signal_audit_cli_reports_quarantined_rows(project_root):
    result = subprocess.run(
        [str(project_root / "scripts" / "cos-reward-signal-audit"), "--stream", "skill-feedback", "--limit", "5", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "reward-signal-audit/v1"
    assert payload["summary"]["total"] <= 5
    assert "skill-feedback" in payload["streams"]
    assert payload["streams"]["skill-feedback"]["summary"]["corrupt"] >= 1


@pytest.mark.behavior
def test_cos_reward_signal_audit_route_smoke(project_root):
    result = subprocess.run(
        [str(project_root / "scripts" / "cos"), "reward-signal", "audit", "--stream", "skill-feedback", "--limit", "1", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "reward-signal-audit/v1"
