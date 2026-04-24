#!/usr/bin/env python3
from __future__ import annotations
"""Integration tests for Cognitive OS application-layer services.

Tests that each application service starts correctly with its dependencies
and responds to health checks using real Docker containers via testcontainers.

Run:
    python -m pytest tests/integration/test_app_services.py -v
    python -m pytest tests/integration/test_app_services.py -v -k "litellm"   # Single service
    python -m pytest tests/integration/test_app_services.py -v -m "not slow"  # Skip slow tests

Requires:
    pip install testcontainers pytest
    Docker daemon running
"""
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from typing import Optional, Tuple, Union

import pytest

# ---------------------------------------------------------------------------
# Testcontainers imports — skip entire module if not installed
# ---------------------------------------------------------------------------
_tc_available = True
try:
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.network import Network
    from testcontainers.core.waiting_utils import wait_for_logs
except ImportError:
    _tc_available = False

pytestmark = [
    pytest.mark.docker,
    pytest.mark.slow,
    pytest.mark.skipif(not _tc_available, reason="testcontainers not installed"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for_http(url: str, *, timeout: int = 120, interval: int = 2, expected_status: int = 200) -> str:
    """Poll an HTTP endpoint until it returns the expected status or timeout expires.

    Returns the response body as a string on success.
    Raises ``TimeoutError`` if the endpoint is not reachable within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                if resp.status == expected_status:
                    return body
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ConnectionError) as exc:
            last_error = exc
        time.sleep(interval)
    raise TimeoutError(
        f"HTTP endpoint {url} did not return {expected_status} within {timeout}s. Last error: {last_error}"
    )


def _host_port(container: DockerContainer, container_port: Union[int, str]) -> Tuple[str, int]:
    """Return (host, mapped_port) for a running container."""
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(int(container_port)))
    return host, port


def _wait_for_clickhouse(container: DockerContainer, timeout: int = 90) -> None:
    """Wait until ClickHouse responds on its stable HTTP ping endpoint."""
    host, port = _host_port(container, 8123)
    body = wait_for_http(f"http://{host}:{port}/ping", timeout=timeout, interval=2)
    assert body.strip() == "Ok.", f"Unexpected ClickHouse ping response: {body!r}"


# ===========================================================================
# 1. Jupyter
# ===========================================================================

class TestJupyterService:
    """Verify jupyter/scipy-notebook starts and reports status."""

    @pytest.fixture(scope="class")
    def jupyter_container(self, docker_available):
        container = (
            DockerContainer("jupyter/scipy-notebook")
            .with_exposed_ports(8888)
            .with_env("JUPYTER_TOKEN", "test-token")
        )
        container.start()
        yield container
        container.stop()

    def test_jupyter_status_endpoint(self, jupyter_container):
        """GET /api/status should contain 'started'."""
        host, port = _host_port(jupyter_container, 8888)
        url = f"http://{host}:{port}/api/status?token=test-token"
        body = wait_for_http(url, timeout=60)
        assert "started" in body, f"Expected 'started' in response body, got: {body[:200]}"


# ===========================================================================
# 2. LiteLLM
# ===========================================================================

class TestLiteLLMService:
    """Verify LiteLLM proxy starts and responds to liveness checks."""

    @pytest.fixture(scope="class")
    def litellm_container(self, docker_available, tmp_path_factory):
        # Create a minimal config.yaml for LiteLLM
        config_dir = tmp_path_factory.mktemp("litellm_config")
        config_path = config_dir / "config.yaml"
        config_path.write_text(
            "model_list:\n"
            "  - model_name: fake-model\n"
            "    litellm_params:\n"
            "      model: openai/fake-model\n"
            "      api_key: sk-fake\n"
            "      api_base: http://localhost:9999\n"
        )

        container = (
            DockerContainer("ghcr.io/berriai/litellm:main-stable")
            .with_exposed_ports(4000)
            .with_env("LITELLM_MASTER_KEY", "sk-test-key")
            .with_volume_mapping(str(config_path), "/app/config.yaml", "ro")
            .with_command("--config /app/config.yaml --port 4000")
        )
        container.start()
        yield container
        container.stop()

    def test_litellm_liveliness(self, litellm_container):
        """GET /health/liveliness should return 200."""
        host, port = _host_port(litellm_container, 4000)
        url = f"http://{host}:{port}/health/liveliness"
        body = wait_for_http(url, timeout=90)
        assert body  # any 200 response is sufficient


# ===========================================================================
# 3. Opik Backend
# ===========================================================================

class TestOpikBackendService:
    """Verify Opik backend starts with MySQL + ClickHouse and is alive."""

    @pytest.fixture(scope="class")
    def opik_stack(self, docker_available):
        network = Network()
        network.create()

        # --- MySQL for Opik state ---
        mysql = (
            DockerContainer("mysql:8.4")
            .with_network(network)
            .with_network_aliases("opik-mysql")
            .with_exposed_ports(3306)
            .with_env("MYSQL_ROOT_PASSWORD", "root_pass")
            .with_env("MYSQL_DATABASE", "opik")
            .with_env("MYSQL_USER", "opik")
            .with_env("MYSQL_PASSWORD", "opik_pass")
        )
        mysql.start()
        wait_for_logs(mysql, "ready for connections", timeout=60)

        # --- Valkey for Opik runtime (Opik still expects REDIS_URL env name) ---
        valkey = (
            DockerContainer("valkey/valkey:8-alpine")
            .with_network(network)
            .with_network_aliases("langfuse-valkey")
            .with_exposed_ports(6379)
            .with_command("--requirepass langfuse_redis --maxmemory-policy noeviction")
        )
        valkey.start()
        wait_for_logs(valkey, "Ready to accept connections", timeout=30)

        # --- ClickHouse for analytics ---
        clickhouse = (
            DockerContainer("clickhouse/clickhouse-server")
            .with_network(network)
            .with_network_aliases("opik-clickhouse")
            .with_exposed_ports(8123)
            .with_env("CLICKHOUSE_DB", "opik")
            .with_env("CLICKHOUSE_USER", "clickhouse")
            .with_env("CLICKHOUSE_PASSWORD", "clickhouse")
        )
        clickhouse.start()
        _wait_for_clickhouse(clickhouse)

        # --- Opik backend ---
        opik = (
            DockerContainer("ghcr.io/comet-ml/opik/opik-backend:latest")
            .with_network(network)
            .with_exposed_ports(8080)
            .with_env("STATE_DB_PROTOCOL", "jdbc:mysql://")
            .with_env("STATE_DB_URL", "opik-mysql:3306/opik?createDatabaseIfNotExist=true")
            .with_env("STATE_DB_USER", "opik")
            .with_env("STATE_DB_PASS", "opik_pass")
            .with_env("STATE_DB_DATABASE_NAME", "opik")
            .with_env("ANALYTICS_DB_MIGRATIONS_URL", "jdbc:clickhouse://opik-clickhouse:8123/opik")
            .with_env("ANALYTICS_DB_MIGRATIONS_USER", "clickhouse")
            .with_env("ANALYTICS_DB_MIGRATIONS_PASS", "clickhouse")
            .with_env("ANALYTICS_DB_PROTOCOL", "HTTP")
            .with_env("ANALYTICS_DB_HOST", "opik-clickhouse")
            .with_env("ANALYTICS_DB_PORT", "8123")
            .with_env("ANALYTICS_DB_USERNAME", "clickhouse")
            .with_env("ANALYTICS_DB_PASS", "clickhouse")
            .with_env("ANALYTICS_DB_DATABASE_NAME", "opik")
            .with_env("REDIS_URL", "redis://:langfuse_redis@langfuse-valkey:6379/0")
            .with_env("JAVA_OPTS", "-Xms256m -Xmx512m")
        )
        opik.start()

        yield {
            "mysql": mysql,
            "valkey": valkey,
            "clickhouse": clickhouse,
            "opik": opik,
            "network": network,
        }

        opik.stop()
        valkey.stop()
        clickhouse.stop()
        mysql.stop()
        network.remove()

    def test_opik_is_alive(self, opik_stack):
        """GET /is-alive/ping should return a successful response."""
        host, port = _host_port(opik_stack["opik"], 8080)
        url = f"http://{host}:{port}/is-alive/ping"
        body = wait_for_http(url, timeout=120)
        assert body is not None


# ===========================================================================
# 4. Langfuse Web (most complex — 4 dependency containers)
# ===========================================================================

class TestLangfuseWebService:
    """Verify Langfuse web starts with all dependencies and passes health check.

    Infrastructure (PG + Valkey + ClickHouse + SeaweedFS) is provided by the
    session-scoped ``langfuse_app_infra`` fixture defined in conftest.py so
    it is shared with TestLangfuseWorkerService (4 fewer containers total).
    """

    # --- Langfuse common env vars (mirrors &langfuse-env YAML anchor) ---
    _LANGFUSE_ENV = {
        "DATABASE_URL": "postgresql://langfuse:langfuse_pass@langfuse-pg:5432/langfuse",
        "NEXTAUTH_URL": "http://localhost:3100",
        "NEXTAUTH_SECRET": "test_secret_32chars_minimum_length",
        "SALT": "test_salt_32chars_minimum_length_x",
        "ENCRYPTION_KEY": "0000000000000000000000000000000000000000000000000000000000000000",
        "TELEMETRY_ENABLED": "false",
        "LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES": "false",
        # ClickHouse
        "CLICKHOUSE_MIGRATION_URL": "clickhouse://langfuse-clickhouse:9000",
        "CLICKHOUSE_URL": "http://langfuse-clickhouse:8123",
        "CLICKHOUSE_USER": "clickhouse",
        "CLICKHOUSE_PASSWORD": "clickhouse",
        "CLICKHOUSE_CLUSTER_ENABLED": "false",
        # Valkey
        "REDIS_HOST": "langfuse-valkey",
        "REDIS_PORT": "6379",
        "REDIS_AUTH": "langfuse_redis",
        "REDIS_TLS_ENABLED": "false",
        # S3 — event upload
        "LANGFUSE_S3_EVENT_UPLOAD_BUCKET": "langfuse",
        "LANGFUSE_S3_EVENT_UPLOAD_REGION": "us-east-1",
        "LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID": "agentosadmin",
        "LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY": "agentossecret",
        "LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT": "http://langfuse-seaweedfs:8333",
        "LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE": "true",
        "LANGFUSE_S3_EVENT_UPLOAD_PREFIX": "events/",
        # S3 — media upload
        "LANGFUSE_S3_MEDIA_UPLOAD_BUCKET": "langfuse",
        "LANGFUSE_S3_MEDIA_UPLOAD_REGION": "us-east-1",
        "LANGFUSE_S3_MEDIA_UPLOAD_ACCESS_KEY_ID": "agentosadmin",
        "LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY": "agentossecret",
        "LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT": "http://langfuse-seaweedfs:8333",
        "LANGFUSE_S3_MEDIA_UPLOAD_FORCE_PATH_STYLE": "true",
        "LANGFUSE_S3_MEDIA_UPLOAD_PREFIX": "media/",
        # Batch export
        "LANGFUSE_S3_BATCH_EXPORT_ENABLED": "false",
        # Web-specific
        "HOSTNAME": "0.0.0.0",
    }

    @pytest.fixture(scope="class")
    def langfuse_stack(self, langfuse_app_infra):
        """Start only the Langfuse web container; infrastructure comes from the
        session-scoped ``langfuse_app_infra`` fixture (shared with worker tests)."""
        network = langfuse_app_infra["network"]

        langfuse_web = DockerContainer("langfuse/langfuse:3")
        langfuse_web.with_network(network)
        langfuse_web.with_network_aliases("langfuse-web")
        langfuse_web.with_exposed_ports(3000)
        for key, value in self._LANGFUSE_ENV.items():
            langfuse_web.with_env(key, value)
        langfuse_web.start()

        yield {
            **langfuse_app_infra,
            "langfuse_web": langfuse_web,
        }

        langfuse_web.stop()

    def test_langfuse_health(self, langfuse_stack):
        """GET /api/public/health should return 200."""
        host, port = _host_port(langfuse_stack["langfuse_web"], 3000)
        url = f"http://{host}:{port}/api/public/health"
        body = wait_for_http(url, timeout=120)
        assert body  # 200 response received

    def test_langfuse_dependencies_running(self, langfuse_stack):
        """All dependency containers should be in running state."""
        for name in ("postgres", "valkey", "clickhouse", "seaweedfs"):
            container = langfuse_stack[name]
            status = container.get_wrapped_container().status
            assert status == "running", f"{name} container is {status}, expected running"


# ===========================================================================
# 5. Langfuse Worker
# ===========================================================================

class TestLangfuseWorkerService:
    """Verify Langfuse worker starts with all dependencies and stays running.

    Infrastructure (PG + Valkey + ClickHouse + SeaweedFS) is provided by the
    session-scoped ``langfuse_app_infra`` fixture defined in conftest.py so
    it is shared with TestLangfuseWebService (4 fewer containers total).
    """

    @pytest.fixture(scope="class")
    def langfuse_worker_stack(self, langfuse_app_infra):
        """Start only the Langfuse worker container; infrastructure comes from the
        session-scoped ``langfuse_app_infra`` fixture (shared with web tests)."""
        network = langfuse_app_infra["network"]

        langfuse_env = {
            "DATABASE_URL": "postgresql://langfuse:langfuse_pass@langfuse-pg:5432/langfuse",
            "NEXTAUTH_URL": "http://localhost:3100",
            "NEXTAUTH_SECRET": "test_secret_32chars_minimum_length",
            "SALT": "test_salt_32chars_minimum_length_x",
            "ENCRYPTION_KEY": "0000000000000000000000000000000000000000000000000000000000000000",
            "TELEMETRY_ENABLED": "false",
            "LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES": "false",
            # ClickHouse
            "CLICKHOUSE_MIGRATION_URL": "clickhouse://langfuse-clickhouse:9000",
            "CLICKHOUSE_URL": "http://langfuse-clickhouse:8123",
            "CLICKHOUSE_USER": "clickhouse",
            "CLICKHOUSE_PASSWORD": "clickhouse",
            "CLICKHOUSE_CLUSTER_ENABLED": "false",
            # Valkey
            "REDIS_HOST": "langfuse-valkey",
            "REDIS_PORT": "6379",
            "REDIS_AUTH": "langfuse_redis",
            "REDIS_TLS_ENABLED": "false",
            # S3 — event upload
            "LANGFUSE_S3_EVENT_UPLOAD_BUCKET": "langfuse",
            "LANGFUSE_S3_EVENT_UPLOAD_REGION": "us-east-1",
            "LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID": "agentosadmin",
            "LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY": "agentossecret",
            "LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT": "http://langfuse-seaweedfs:8333",
            "LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE": "true",
            "LANGFUSE_S3_EVENT_UPLOAD_PREFIX": "events/",
            # S3 — media upload
            "LANGFUSE_S3_MEDIA_UPLOAD_BUCKET": "langfuse",
            "LANGFUSE_S3_MEDIA_UPLOAD_REGION": "us-east-1",
            "LANGFUSE_S3_MEDIA_UPLOAD_ACCESS_KEY_ID": "agentosadmin",
            "LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY": "agentossecret",
            "LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT": "http://langfuse-seaweedfs:8333",
            "LANGFUSE_S3_MEDIA_UPLOAD_FORCE_PATH_STYLE": "true",
            "LANGFUSE_S3_MEDIA_UPLOAD_PREFIX": "media/",
            # Batch export
            "LANGFUSE_S3_BATCH_EXPORT_ENABLED": "false",
            # Worker-specific
            "HOSTNAME": "0.0.0.0",
        }

        langfuse_worker = DockerContainer("langfuse/langfuse-worker:3")
        langfuse_worker.with_network(network)
        langfuse_worker.with_network_aliases("langfuse-worker")
        langfuse_worker.with_exposed_ports(3030)
        for key, value in langfuse_env.items():
            langfuse_worker.with_env(key, value)
        langfuse_worker.start()

        yield {
            **langfuse_app_infra,
            "langfuse_worker": langfuse_worker,
        }

        langfuse_worker.stop()

    def test_langfuse_worker_stays_running(self, langfuse_worker_stack):
        """Worker container should remain in running state for at least 10 seconds (no crash loop)."""
        worker = langfuse_worker_stack["langfuse_worker"]
        # Give the worker time to start and potentially crash
        time.sleep(10)
        status = worker.get_wrapped_container().reload() or worker.get_wrapped_container().status
        assert status == "running", f"langfuse-worker container is {status}, expected running"

    def test_langfuse_worker_port_reachable(self, langfuse_worker_stack):
        """Port 3030 should be reachable — attempt an HTTP GET (may not return 200)."""
        host, port = _host_port(langfuse_worker_stack["langfuse_worker"], 3030)
        url = f"http://{host}:{port}/"
        # The worker may not expose a standard health endpoint, so we accept
        # any HTTP response (including 404) as proof the process is listening.
        deadline = time.monotonic() + 60
        reachable = False
        while time.monotonic() < deadline:
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    reachable = True
                    break
            except urllib.error.HTTPError:
                # Any HTTP error (404, 500, etc.) still means the port is listening
                reachable = True
                break
            except (urllib.error.URLError, OSError, ConnectionError):
                time.sleep(2)
        assert reachable, f"langfuse-worker port 3030 not reachable at {url} within 60s"

    def test_langfuse_worker_dependencies_running(self, langfuse_worker_stack):
        """All dependency containers should be in running state."""
        for name in ("postgres", "valkey", "clickhouse", "seaweedfs"):
            container = langfuse_worker_stack[name]
            status = container.get_wrapped_container().status
            assert status == "running", f"{name} container is {status}, expected running"
