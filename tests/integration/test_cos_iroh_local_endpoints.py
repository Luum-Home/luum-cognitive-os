import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_cos_iroh_ping_two_local_endpoints_opt_in():
    if os.environ.get("COS_IROH_INTEGRATION") != "1":
        pytest.skip("set COS_IROH_INTEGRATION=1 to run local endpoint integration smoke")
    completed = subprocess.run(
        [str(ROOT / "scripts" / "cos-iroh-ping"), "--self-test", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["status"] == "pass"
    assert report["transport_backend"] == "local-loopback-contract"
    assert len(report["server_public_key"]) == 64
    assert len(report["client_public_key"]) == 64
