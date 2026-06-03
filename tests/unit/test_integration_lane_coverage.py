import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_integration_lane_coverage.py"


def test_integration_lane_coverage_contract_passes_for_repo_registry():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "integration-lane-coverage/v1"
    assert payload["status"] == "pass"
    assert payload["unassigned_count"] == 0
    assert payload["duplicate_count"] == 0
    assert payload["total"] > 0
