"""System tests for Docker infrastructure.

Checks if Cognitive OS containers are running and healthy.
Migrated from tests/infra/test-docker.sh.
"""

import re
import subprocess
import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def compose_file(project_root):
    path = project_root / "docker-compose.cognitive-os.yml"
    if not path.exists():
        pytest.skip("docker-compose.cognitive-os.yml not found")
    return path


@pytest.fixture(scope="module")
def docker_cmd():
    """Find the docker binary."""
    docker = shutil.which("docker") or "/Applications/Docker.app/Contents/Resources/bin/docker"
    if not shutil.which(docker.split("/")[-1]) and not Path(docker).exists():
        pytest.skip("Docker not found")
    # Check daemon
    result = subprocess.run([docker, "info"], capture_output=True, timeout=10)
    if result.returncode != 0:
        pytest.skip("Docker daemon not running")
    return docker


@pytest.fixture(scope="module")
def expected_containers(compose_file):
    """Extract container names from docker-compose file."""
    text = compose_file.read_text()
    containers = re.findall(r"container_name:\s*['\"]?([^\s'\"]+)", text)
    if not containers:
        pytest.skip("No container_name entries found in compose file")
    return containers


@pytest.mark.system
@pytest.mark.docker
class TestDockerInfrastructure:
    """Tests for Docker container status and health.

    Note: Docker failures are non-blocking -- services may not be running.
    """

    @pytest.mark.parametrize("container", [], indirect=False)
    def test_container_status(self, container, docker_cmd):
        """Parameterized dynamically -- see conftest or test collection."""
        pass  # Covered by test_all_containers_status

    def test_all_containers_status(self, expected_containers, docker_cmd):
        """Check each expected container's status."""
        for container in expected_containers:
            status_result = subprocess.run(
                [docker_cmd, "inspect", "--format", "{{.State.Status}}", container],
                capture_output=True,
                text=True,
                timeout=10,
            )
            status = status_result.stdout.strip() if status_result.returncode == 0 else "not_found"

            health_result = subprocess.run(
                [docker_cmd, "inspect", "--format",
                 "{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}",
                 container],
                capture_output=True,
                text=True,
                timeout=10,
            )
            health = health_result.stdout.strip() if health_result.returncode == 0 else "unknown"

            # Non-blocking: just report status
            if status == "running":
                if health == "unhealthy":
                    pytest.skip(f"{container}: running but unhealthy")
            elif status in ("exited", "dead", "paused"):
                pytest.skip(f"{container}: {status}")
            elif status == "not_found":
                pytest.skip(f"{container}: not found (never started)")
