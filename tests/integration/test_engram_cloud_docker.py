from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

try:
    from testcontainers.core.container import DockerContainer
except ImportError:  # pragma: no cover - optional lane
    DockerContainer = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[2]
RUN_ENGRAM_CLOUD_CONTAINERS = os.environ.get("COS_RUN_ENGRAM_CLOUD_CONTAINERS") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.skipif(DockerContainer is None, reason="testcontainers not installed"),
    pytest.mark.skipif(not RUN_ENGRAM_CLOUD_CONTAINERS, reason="optional Engram Cloud docker lane; set COS_RUN_ENGRAM_CLOUD_CONTAINERS=1"),
]


def test_engram_cloud_enroll_dry_run_inside_container() -> None:
    assert DockerContainer is not None
    with DockerContainer("python:3.11-slim").with_volume_mapping(str(ROOT), "/workspace", mode="rw").with_command(
        "sh -lc 'cd /workspace && scripts/cos-engram-cloud-enroll --project docker-smoke --dry-run --json'"
    ) as container:
        wait_result = container.get_wrapped_container().wait()
        exit_code = wait_result.get("StatusCode", wait_result) if isinstance(wait_result, dict) else wait_result
        raw_logs = container.get_logs()
        if isinstance(raw_logs, tuple):
            logs = b"".join(part for part in raw_logs if part).decode("utf-8", errors="replace")
        else:
            logs = raw_logs.decode("utf-8", errors="replace")
    assert exit_code == 0
    assert '"project_scope": "docker-smoke"' in logs


def test_engram_cloud_compose_profile_renders() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", str(ROOT / "docker" / "cos-worker" / "docker-compose.yml"), "--profile", "engram-cloud", "config"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "cos-engram-cloud" in result.stdout
    assert "ENGRAM_DATABASE_URL" in result.stdout
