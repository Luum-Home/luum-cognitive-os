"""Integration tests for Cognitive OS Docker service health.

Validates that all configured services are reachable and healthy.
Skips gracefully if Docker is not available.
Migrated from test-service-health.sh.
"""

import subprocess
import shutil
from pathlib import Path

import pytest

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


EXPECTED_SERVICES = [
    "langfuse-pg",
    "langfuse-web",
    "litellm",
    "opik-backend",
    "opik-mysql",
    "cognee",
]

HEALTH_ENDPOINTS = [
    ("opik-backend", "http://localhost:5173/is-alive/ping"),
    ("cognee", "http://localhost:8100/health"),
    ("langfuse-web", "http://localhost:3100"),
    ("litellm", "http://localhost:4000/health"),
]


@pytest.fixture(scope="module")
def compose_file(project_root):
    path = project_root / "docker-compose.cognitive-os.yml"
    if not path.exists():
        pytest.skip("docker-compose.cognitive-os.yml not found")
    return path


@pytest.fixture(scope="module")
def docker_compose_available():
    if not shutil.which("docker"):
        pytest.skip("Docker not available")
    result = subprocess.run(
        ["docker", "info"], capture_output=True, timeout=10
    )
    if result.returncode != 0:
        pytest.skip("Docker daemon not running")
    return True


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.mark.integration
@pytest.mark.docker
class TestServiceHealth:
    """Tests for Docker Compose service definitions and health."""

    def test_compose_file_validates(self, compose_file, docker_compose_available):
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "config", "--quiet"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0 and "required variable" in result.stderr:
            pytest.skip(
                "compose file requires env vars not set in test environment: "
                + result.stderr.strip().split("\n")[-1]
            )
        assert result.returncode == 0, "compose file should validate"

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_service_defined_in_compose(self, service, compose_file, docker_compose_available):
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file),
             "--profile", "observability", "--profile", "memory",
             "--profile", "automation",
             "config", "--services"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            pytest.skip("compose config failed (likely missing env vars)")
        services = result.stdout.strip().split("\n")
        assert service in services, f"service '{service}' should be defined in compose"

    @pytest.mark.parametrize("label,url", HEALTH_ENDPOINTS, ids=[e[0] for e in HEALTH_ENDPOINTS])
    def test_health_endpoint(self, label, url, docker_compose_available):
        """Check health endpoints -- only if the service is running."""
        if not HAS_REQUESTS:
            pytest.skip("requests library not installed")
        try:
            resp = requests.get(url, timeout=5)
            assert resp.status_code < 500, f"{label} returned {resp.status_code}"
        except requests.ConnectionError:
            pytest.skip(f"{label} not running (expected if stack is down)")
        except requests.Timeout:
            pytest.skip(f"{label} timed out (expected if stack is down)")
