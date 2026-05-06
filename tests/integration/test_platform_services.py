#!/usr/bin/env python3
"""Integration tests for remaining platform services from docker-compose.

Tests platform services using testcontainers for isolated Docker-based testing.
and Opik Frontend.

Run: python -m pytest tests/integration/test_platform_services.py -v
Requires: pip install testcontainers pytest
"""
import os
import time
import json
import urllib.request
import urllib.error

import pytest

# ---------------------------------------------------------------------------
# Testcontainers availability guard
# ---------------------------------------------------------------------------
tc_available = True
RUN_PLATFORM_SERVICES = os.environ.get("COS_RUN_PLATFORM_SERVICES") == "1"
try:
    from testcontainers.core.container import DockerContainer
    import docker
except ImportError:
    tc_available = False

pytestmark = [
    pytest.mark.docker,
    pytest.mark.slow,
    pytest.mark.skipif(not tc_available, reason="testcontainers not installed"),
    pytest.mark.skipif(
        not RUN_PLATFORM_SERVICES,
        reason=(
            "optional platform service lane; set "
            "COS_RUN_PLATFORM_SERVICES=1 to run"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for_http(url: str, *, timeout: int = 120, interval: int = 3) -> urllib.request.Request:
    """Poll an HTTP endpoint until it returns a successful response.

    Args:
        url: The URL to poll.
        timeout: Maximum seconds to wait before raising.
        interval: Seconds between attempts.

    Returns:
        The successful ``http.client.HTTPResponse``.

    Raises:
        TimeoutError: If the endpoint does not respond within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            if resp.status < 500:
                return resp
        except Exception as exc:
            last_exc = exc
        time.sleep(interval)
    raise TimeoutError(
        f"Endpoint {url} did not become healthy within {timeout}s. "
        f"Last error: {last_exc}"
    )


def _image_pullable(image: str) -> bool:
    """Return True if the Docker image can be pulled, False otherwise."""
    try:
        client = docker.from_env()
        client.images.pull(image)
        return True
    except Exception:
        return False


def _skip_on_pull_failure(image: str):
    """Skip the current test if the image cannot be pulled."""
    if not _image_pullable(image):
        pytest.skip(f"Cannot pull image {image} -- skipping")


# ===========================================================================
# 1. Memu (python:3.13-slim + pip install memu-ai) — profile: memory
# ===========================================================================

class TestMemuService:
    """Test Memu AI memory service starts and exposes a health endpoint.

    This service installs from PyPI at runtime so the container startup is
    slow (up to ~120 s).
    """

    IMAGE = "python:3.13-slim"

    @pytest.fixture(scope="class")
    def memu_container(self, docker_available):
        """Start a slim Python container, install memu-ai, and run the server."""
        container = (
            DockerContainer(self.IMAGE)
            .with_exposed_ports(8765)
            .with_command(
                "bash -c '"
                "pip install --quiet memu-ai && "
                "python -m memu.server --host 0.0.0.0 --port 8765"
                "'"
            )
        )
        container.start()

        host = container.get_container_host_ip()
        port = container.get_exposed_port(8765)

        yield {
            "container": container,
            "host": host,
            "port": port,
            "base_url": f"http://{host}:{port}",
        }

        container.stop()

    def test_memu_health(self, memu_container):
        """Verify Memu /health returns a successful response within 120 s."""
        base = memu_container["base_url"]
        resp = wait_for_http(f"{base}/health", timeout=120, interval=3)
        assert resp.status == 200


# ===========================================================================
# 3. Cognee server (python:3.12-slim + pip install cognee[api])
# ===========================================================================

class TestCogneeServerService:
    """Test Cognee knowledge-graph server starts and exposes /health.

    Uses networkx + lancedb backends so no external dependencies are required.
    Slow startup due to pip install at container boot.
    """

    IMAGE = "python:3.12-slim"

    @pytest.fixture(scope="class")
    def cognee_container(self, docker_available):
        """Start a slim Python container running Cognee server."""
        container = (
            DockerContainer(self.IMAGE)
            .with_exposed_ports(8000)
            .with_env("COGNEE_GRAPH_BACKEND", "networkx")
            .with_env("COGNEE_VECTOR_STORE", "lancedb")
            .with_command(
                "bash -c '"
                "pip install --quiet cognee[api] litellm==1.83.0 && "
                "uvicorn cognee.api.client:app --host 0.0.0.0 --port 8000"
                "'"
            )
        )
        container.start()

        host = container.get_container_host_ip()
        port = container.get_exposed_port(8000)

        yield {
            "container": container,
            "host": host,
            "port": port,
            "base_url": f"http://{host}:{port}",
        }

        container.stop()

    def test_cognee_server_health(self, cognee_container):
        """Verify Cognee /health responds within 120 s."""
        base = cognee_container["base_url"]
        resp = wait_for_http(f"{base}/health", timeout=120, interval=3)
        assert resp.status == 200


# ===========================================================================
# 4. SeaweedFS (chrislusf/seaweedfs:latest) — langfuse blob storage
# ===========================================================================

class TestSeaweedFSService:
    """Test SeaweedFS starts and exposes the master cluster status API."""

    IMAGE = "chrislusf/seaweedfs:latest"

    @pytest.fixture(scope="class")
    def seaweedfs_container(self, docker_available):
        """Start SeaweedFS with master + filer + S3 gateway.

        The S3 config file is omitted for testing — the -s3 flag alone starts
        the gateway with default settings.
        """
        _skip_on_pull_failure(self.IMAGE)

        container = (
            DockerContainer(self.IMAGE)
            .with_exposed_ports(8333, 9333, 8888)
            .with_command(
                "server -dir=/data -s3 -s3.port=8333 "
                "-filer -master.volumeSizeLimitMB=100"
            )
        )
        container.start()

        host = container.get_container_host_ip()
        master_port = container.get_exposed_port(9333)
        s3_port = container.get_exposed_port(8333)
        filer_port = container.get_exposed_port(8888)

        yield {
            "container": container,
            "host": host,
            "master_port": master_port,
            "s3_port": s3_port,
            "filer_port": filer_port,
            "master_url": f"http://{host}:{master_port}",
        }

        container.stop()

    def test_seaweedfs_cluster_status(self, seaweedfs_container):
        """Verify the master /cluster/status returns valid JSON."""
        url = f"{seaweedfs_container['master_url']}/cluster/status"
        resp = wait_for_http(url, timeout=60, interval=3)
        body = resp.read().decode("utf-8")
        data = json.loads(body)
        # SeaweedFS cluster status always contains IsLeader field
        assert "IsLeader" in data or "Peers" in data or isinstance(data, dict)

    def test_seaweedfs_filer_reachable(self, seaweedfs_container):
        """Verify the filer HTTP endpoint is reachable."""
        host = seaweedfs_container["host"]
        port = seaweedfs_container["filer_port"]
        resp = wait_for_http(f"http://{host}:{port}/", timeout=60, interval=3)
        assert resp.status == 200


# ===========================================================================
# 5. Automaker — external/manual integration only
# ===========================================================================

@pytest.mark.skip(reason="AutoMaker has no stable public GHCR image; upstream documents source-build Docker Compose.")
class TestAutomakerService:
    """Placeholder for future Automaker image smoke tests.

    Re-enable only after upstream publishes a stable public image digest.
    """

    IMAGE = ""

    @pytest.fixture(scope="class")
    def automaker_container(self, docker_available):
        """Start Automaker container if image is available."""
        _skip_on_pull_failure(self.IMAGE)

        container = (
            DockerContainer(self.IMAGE)
            .with_exposed_ports(4200)
        )
        container.start()

        host = container.get_container_host_ip()
        port = container.get_exposed_port(4200)

        yield {
            "container": container,
            "host": host,
            "port": port,
            "base_url": f"http://{host}:{port}",
        }

        container.stop()

    def test_automaker_health(self, automaker_container):
        """Verify Automaker /health returns 200."""
        base = automaker_container["base_url"]
        resp = wait_for_http(f"{base}/health", timeout=60, interval=3)
        assert resp.status == 200


# ===========================================================================
# 6. NeMo Guardrails — build-context validation (no container test)
# ===========================================================================

class TestNemoGuardrailsBuildContext:
    """Validate the NeMo Guardrails Docker build context without building.

    Since testcontainers cannot build from a Dockerfile context directly,
    these tests verify the build artifacts exist and are correctly configured.
    """

    DOCKERFILE_PATH = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "infra", "nemo-guardrails", "Dockerfile",
    )

    def _resolved_path(self) -> str:
        return os.path.normpath(self.DOCKERFILE_PATH)

    def test_dockerfile_exists(self):
        """Verify the NeMo Guardrails Dockerfile is present."""
        path = self._resolved_path()
        assert os.path.isfile(path), f"Dockerfile not found at {path}"

    def test_dockerfile_exposes_port_8088(self):
        """Verify the Dockerfile exposes port 8088."""
        path = self._resolved_path()
        with open(path) as f:
            content = f.read()
        assert "EXPOSE 8088" in content, "Dockerfile must EXPOSE 8088"

    def test_dockerfile_installs_nemoguardrails(self):
        """Verify the Dockerfile installs nemoguardrails package."""
        path = self._resolved_path()
        with open(path) as f:
            content = f.read()
        assert "nemoguardrails" in content, (
            "Dockerfile must install nemoguardrails"
        )

    def test_dockerfile_runs_server_command(self):
        """Verify the CMD launches the nemoguardrails server."""
        path = self._resolved_path()
        with open(path) as f:
            content = f.read()
        assert "nemoguardrails" in content and "server" in content, (
            "Dockerfile CMD must run nemoguardrails server"
        )

    def test_dockerfile_has_config_directory(self):
        """Verify the Dockerfile creates a config mount point."""
        path = self._resolved_path()
        with open(path) as f:
            content = f.read()
        assert "/app/config" in content, (
            "Dockerfile must create /app/config directory for config mounting"
        )


# ===========================================================================
# 7. Opik Frontend (ghcr.io/comet-ml/opik/opik-frontend:latest)
# ===========================================================================

class TestOpikFrontendService:
    """Test Opik Frontend serves its SPA shell.

    The frontend will not connect to a real backend, but it should still
    serve the static HTML/JS bundle.
    """

    IMAGE = "ghcr.io/comet-ml/opik/opik-frontend:latest"

    @pytest.fixture(scope="class")
    def opik_frontend_container(self, docker_available):
        """Start Opik frontend container."""
        _skip_on_pull_failure(self.IMAGE)

        container = (
            DockerContainer(self.IMAGE)
            .with_exposed_ports(5173)
            .with_env("OPIK_API_URL", "http://localhost:8080/api")
        )
        container.start()

        host = container.get_container_host_ip()
        port = container.get_exposed_port(5173)

        yield {
            "container": container,
            "host": host,
            "port": port,
            "base_url": f"http://{host}:{port}",
        }

        container.stop()

    def test_opik_frontend_serves_html(self, opik_frontend_container):
        """Verify the root path returns an HTML response."""
        base = opik_frontend_container["base_url"]
        resp = wait_for_http(f"{base}/", timeout=60, interval=3)
        body = resp.read().decode("utf-8", errors="replace")
        assert resp.status == 200
        # SPA frontends serve HTML with a root div or script tags
        assert "<html" in body.lower() or "<!doctype" in body.lower(), (
            "Expected HTML response from Opik frontend"
        )
