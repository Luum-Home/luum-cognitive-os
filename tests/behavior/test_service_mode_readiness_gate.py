import json
import subprocess

import pytest


@pytest.mark.behavior
def test_cos_service_readiness_gate_route_reports_red_without_trace(project_root, tmp_path):
    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "service",
            "readiness",
            "--project-dir",
            str(tmp_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "service-mode-readiness/v1"
    assert payload["status"] == "red"
    gate_ids = {gate["id"] for gate in payload["gates"]}
    assert "private-content" in gate_ids
    assert "run-flight-recorder" in gate_ids
    assert "performance-ledger" in gate_ids
