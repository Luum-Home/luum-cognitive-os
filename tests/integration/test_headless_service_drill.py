from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
@pytest.mark.docker
def test_headless_service_drill_runs_opt_in() -> None:
    """Run the Docker headless service proof only when explicitly requested."""
    if os.environ.get("COS_RUN_HEADLESS_SERVICE_DOCKER") != "1":
        pytest.skip("set COS_RUN_HEADLESS_SERVICE_DOCKER=1 to run the Docker headless service drill")
    if not shutil.which("docker"):
        pytest.skip("docker not available")

    result = subprocess.run(
        [str(PROJECT_ROOT / "scripts" / "cos-headless-service-drill"), "--json"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout.splitlines()[-1])
    assert payload["ok"] is True
    assert payload["local_task_status"] == "completed"
    assert payload["container_codex_status"] in {"unsupported", "auth_required", "ready"}
    assert payload["container_claude_status"] in {"unsupported", "auth_required", "ready"}
