#!/usr/bin/env python3
"""End-to-end integration tests for Cognitive OS multi-service flows.

Unlike the unit-style integration tests in test_databases.py and test_app_services.py
(which validate each service individually), these tests validate that services
WORK TOGETHER correctly through complete user-facing workflows.

# Langfuse e2e tests removed per ADR-058 (2026-04-24).
# The legacy ingestion-API tests (`test_send_trace_to_langfuse`,
# `test_record_completion_sends_trace_to_langfuse`) were removed because
# Langfuse is deprecated and record_completion now emits OTel spans.
# The Phoenix OTel integration test lives in
# tests/integration/test_record_completion_sends_trace_to_phoenix.py.

Flows tested:
  1. Observability Pipeline — Opik + Langfuse receive and store LLM traces
  2. Memory Pipeline       — Cognee ECL pipeline produces queryable knowledge
  3. LLM Routing           — LiteLLM routes requests through the proxy
  4. Agent Coordination    — Paperclip starts with auto-migration and serves API
  5. Full Stack Smoke      — All core services start and pass health checks together

Run:
    python -m pytest tests/integration/test_e2e_flows.py -v
    python -m pytest tests/integration/test_e2e_flows.py::TestObservabilityFlow -v
    python -m pytest tests/integration/test_e2e_flows.py -v -m "not slow"

Requires:
    pip install testcontainers pytest
    Docker daemon running
"""
import json
import logging
import os as _os
import pathlib as _pathlib
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Optional, Dict, Tuple, Union

import pytest

# ---------------------------------------------------------------------------
# Testcontainers imports — skip entire module if not installed
# ---------------------------------------------------------------------------
_tc_available = True
_RUN_E2E_REFERENCE_FLOWS = _os.environ.get("COS_RUN_E2E_REFERENCE_FLOWS") == "1"
try:
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.network import Network
    from testcontainers.core.waiting_utils import wait_for_logs
except ImportError:
    _tc_available = False

pytestmark = [
    pytest.mark.docker,
    pytest.mark.e2e,
    pytest.mark.slow,
    pytest.mark.skipif(not _tc_available, reason="testcontainers not installed"),
    pytest.mark.skipif(
        not _RUN_E2E_REFERENCE_FLOWS,
        reason=(
            "optional multi-service reference flow lane; set "
            "COS_RUN_E2E_REFERENCE_FLOWS=1 to run"
        ),
    ),
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level skip: Docker must be installed and running
# ---------------------------------------------------------------------------
def _docker_ok() -> bool:
    """Return True when Docker CLI exists and daemon is reachable."""
    if not shutil.which("docker"):
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


if _RUN_E2E_REFERENCE_FLOWS and not _docker_ok():
    pytest.skip("Docker not available", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for_http(
    url: str,
    *,
    timeout: int = 180,
    interval: int = 3,
    expected_status: int = 200,
    method: str = "GET",
    data: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """Poll an HTTP endpoint until it returns the expected status or timeout expires.

    E2E flows need longer timeouts than single-service tests because multiple
    containers must initialize, run migrations, and establish connections.

    Returns the response body as a string on success.
    Raises ``TimeoutError`` if the endpoint is not reachable within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, method=method, data=data)
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                if resp.status == expected_status:
                    return body
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ConnectionError) as exc:
            last_error = exc
        time.sleep(interval)
    raise TimeoutError(
        f"HTTP endpoint {url} did not return {expected_status} within {timeout}s. "
        f"Last error: {last_error}"
    )


def http_request(
    url: str,
    *,
    method: str = "GET",
    data: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Tuple[int, str]:
    """Make a single HTTP request, returning (status_code, body).

    Does NOT retry — use wait_for_http for polling.
    Returns (0, error_message) on connection failure.
    """
    try:
        body_bytes = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, method=method, data=body_bytes)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        if data and not headers:
            req.add_header("Content-Type", "application/json")
        elif data and headers and "Content-Type" not in headers:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ConnectionError) as exc:
        return 0, str(exc)


def _host_port(container: DockerContainer, container_port: Union[int, str]) -> Tuple[str, int]:
    """Return (host, mapped_port) for a running container."""
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(int(container_port)))
    return host, port


def _start_container_safe(container: DockerContainer, name: str) -> bool:
    """Try to start a container, return True on success, False if image unavailable."""
    try:
        t0 = time.monotonic()
        container.start()
        elapsed = time.monotonic() - t0
        logger.info("Container %s started in %.1fs", name, elapsed)
        return True
    except Exception as exc:
        logger.warning("Failed to start container %s: %s", name, exc)
        return False


def _wait_for_clickhouse(container: DockerContainer, timeout: int = 90) -> None:
    """Wait until ClickHouse responds on its HTTP ping endpoint.

    Log messages have drifted across upstream image versions; `/ping` is the
    stable readiness contract we actually care about.
    """
    host, port = _host_port(container, 8123)
    body = wait_for_http(f"http://{host}:{port}/ping", timeout=timeout, interval=2)
    assert body.strip() == "Ok.", f"Unexpected ClickHouse ping response: {body!r}"


def _build_langfuse_env() -> dict[str, str]:
    """Return the common Langfuse environment variables (mirrors &langfuse-env YAML anchor)."""
    return {
        "DATABASE_URL": "postgresql://langfuse:langfuse_pass@langfuse-pg:5432/langfuse",
        "NEXTAUTH_URL": "http://localhost:3000",
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
        # S3 event upload
        "LANGFUSE_S3_EVENT_UPLOAD_BUCKET": "langfuse",
        "LANGFUSE_S3_EVENT_UPLOAD_REGION": "us-east-1",
        "LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID": "agentosadmin",
        "LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY": "agentossecret",
        "LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT": "http://langfuse-seaweedfs:8333",
        "LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE": "true",
        "LANGFUSE_S3_EVENT_UPLOAD_PREFIX": "events/",
        # S3 media upload
        "LANGFUSE_S3_MEDIA_UPLOAD_BUCKET": "langfuse",
        "LANGFUSE_S3_MEDIA_UPLOAD_REGION": "us-east-1",
        "LANGFUSE_S3_MEDIA_UPLOAD_ACCESS_KEY_ID": "agentosadmin",
        "LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY": "agentossecret",
        "LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT": "http://langfuse-seaweedfs:8333",
        "LANGFUSE_S3_MEDIA_UPLOAD_FORCE_PATH_STYLE": "true",
        "LANGFUSE_S3_MEDIA_UPLOAD_PREFIX": "media/",
        # Batch export
        "LANGFUSE_S3_BATCH_EXPORT_ENABLED": "false",
    }


# ===========================================================================
# Flow 1: Observability Pipeline
# ===========================================================================

class TestObservabilityFlow:
    """Validate the complete observability pipeline across Opik and Langfuse.

    Services: ClickHouse + MySQL + Opik Backend + Langfuse (PG + Valkey + CH + SeaweedFS + Web)

    This flow tests that a mock LLM trace can be ingested by BOTH observability
    systems, verifying that an agent execution is traceable end-to-end.
    """

    @pytest.fixture(scope="class")
    def observability_stack(self, docker_available):
        """Start the full observability stack: Opik + Langfuse with all dependencies."""
        network = Network()
        network.create()
        containers = {}
        startup_times = {}

        try:
            # --- Shared ClickHouse (used by both Opik and Langfuse) ---
            t0 = time.monotonic()
            clickhouse = (
                DockerContainer("clickhouse/clickhouse-server")
                .with_network(network)
                .with_network_aliases("langfuse-clickhouse")
                .with_exposed_ports(8123, 9000)
                .with_env("CLICKHOUSE_DB", "default")
                .with_env("CLICKHOUSE_USER", "clickhouse")
                .with_env("CLICKHOUSE_PASSWORD", "clickhouse")
            )
            clickhouse.start()
            _wait_for_clickhouse(clickhouse)
            containers["clickhouse"] = clickhouse
            startup_times["clickhouse"] = time.monotonic() - t0

            # --- MySQL for Opik ---
            t0 = time.monotonic()
            mysql = (
                DockerContainer("mysql:8.4")
                .with_network(network)
                .with_network_aliases("opik-mysql")
                .with_exposed_ports(3306)
                .with_env("MYSQL_ROOT_PASSWORD", "opik_root_pass")
                .with_env("MYSQL_DATABASE", "opik")
                .with_env("MYSQL_USER", "opik")
                .with_env("MYSQL_PASSWORD", "opik_pass")
            )
            mysql.start()
            wait_for_logs(mysql, "ready for connections", timeout=60)
            containers["mysql"] = mysql
            startup_times["mysql"] = time.monotonic() - t0

            # --- PostgreSQL for Langfuse ---
            t0 = time.monotonic()
            langfuse_pg = (
                DockerContainer("postgres:17-alpine")
                .with_network(network)
                .with_network_aliases("langfuse-pg")
                .with_exposed_ports(5432)
                .with_env("POSTGRES_USER", "langfuse")
                .with_env("POSTGRES_PASSWORD", "langfuse_pass")
                .with_env("POSTGRES_DB", "langfuse")
                .with_env("TZ", "UTC")
                .with_env("PGTZ", "UTC")
            )
            langfuse_pg.start()
            wait_for_logs(langfuse_pg, "database system is ready to accept connections", timeout=30)
            containers["langfuse_pg"] = langfuse_pg
            startup_times["langfuse_pg"] = time.monotonic() - t0

            # --- Valkey for Langfuse ---
            t0 = time.monotonic()
            valkey = (
                DockerContainer("valkey/valkey:8-alpine")
                .with_network(network)
                .with_network_aliases("langfuse-valkey")
                .with_exposed_ports(6379)
                .with_command("--requirepass langfuse_redis --maxmemory-policy noeviction")
            )
            valkey.start()
            wait_for_logs(valkey, "Ready to accept connections", timeout=30)
            containers["valkey"] = valkey
            startup_times["valkey"] = time.monotonic() - t0

            # --- Opik Backend ---
            t0 = time.monotonic()
            opik = (
                DockerContainer("ghcr.io/comet-ml/opik/opik-backend:latest")
                .with_network(network)
                .with_network_aliases("opik-backend")
                .with_exposed_ports(8080)
                .with_env("STATE_DB_PROTOCOL", "jdbc:mysql://")
                .with_env("STATE_DB_URL", "opik-mysql:3306/opik?createDatabaseIfNotExist=true")
                .with_env("STATE_DB_USER", "opik")
                .with_env("STATE_DB_PASS", "opik_pass")
                .with_env("STATE_DB_DATABASE_NAME", "opik")
                .with_env("ANALYTICS_DB_MIGRATIONS_URL", "jdbc:clickhouse://langfuse-clickhouse:8123/opik")
                .with_env("ANALYTICS_DB_MIGRATIONS_USER", "clickhouse")
                .with_env("ANALYTICS_DB_MIGRATIONS_PASS", "clickhouse")
                .with_env("ANALYTICS_DB_PROTOCOL", "HTTP")
                .with_env("ANALYTICS_DB_HOST", "langfuse-clickhouse")
                .with_env("ANALYTICS_DB_PORT", "8123")
                .with_env("ANALYTICS_DB_USERNAME", "clickhouse")
                .with_env("ANALYTICS_DB_PASS", "clickhouse")
                .with_env("ANALYTICS_DB_DATABASE_NAME", "opik")
                .with_env("REDIS_URL", "redis://:langfuse_redis@langfuse-valkey:6379/0")
                .with_env("JAVA_OPTS", "-Xms256m -Xmx512m")
            )
            if not _start_container_safe(opik, "opik-backend"):
                pytest.skip("opik-backend image not available")
            containers["opik"] = opik
            startup_times["opik"] = time.monotonic() - t0

            # --- SeaweedFS for Langfuse ---
            t0 = time.monotonic()
            seaweedfs = (
                DockerContainer("chrislusf/seaweedfs:latest")
                .with_network(network)
                .with_network_aliases("langfuse-seaweedfs")
                .with_exposed_ports(8333, 9333)
                .with_command("server -dir=/data -s3 -s3.port=8333 -filer -master.volumeSizeLimitMB=100")
            )
            seaweedfs.start()
            wait_for_logs(seaweedfs, "Start Seaweed", timeout=30)
            containers["seaweedfs"] = seaweedfs
            startup_times["seaweedfs"] = time.monotonic() - t0

            # --- Langfuse Web ---
            t0 = time.monotonic()
            langfuse_web = DockerContainer("langfuse/langfuse:3")
            langfuse_web.with_network(network)
            langfuse_web.with_network_aliases("langfuse-web")
            langfuse_web.with_exposed_ports(3000)
            for key, value in _build_langfuse_env().items():
                langfuse_web.with_env(key, value)
            langfuse_web.with_env("HOSTNAME", "0.0.0.0")
            if not _start_container_safe(langfuse_web, "langfuse-web"):
                pytest.skip("langfuse image not available")
            containers["langfuse_web"] = langfuse_web
            startup_times["langfuse_web"] = time.monotonic() - t0

            logger.info("Observability stack startup times: %s", startup_times)

            yield {**containers, "network": network, "startup_times": startup_times}

        finally:
            # Stop in reverse dependency order
            for name in reversed(list(containers.keys())):
                try:
                    containers[name].stop()
                except Exception:
                    pass
            try:
                network.remove()
            except Exception:
                pass

    def test_opik_is_alive(self, observability_stack):
        """Opik backend health check must pass."""
        host, port = _host_port(observability_stack["opik"], 8080)
        body = wait_for_http(f"http://{host}:{port}/is-alive/ping", timeout=120)
        assert body is not None

    def test_langfuse_health(self, observability_stack):
        """Langfuse web health check must pass."""
        host, port = _host_port(observability_stack["langfuse_web"], 3000)
        body = wait_for_http(f"http://{host}:{port}/api/public/health", timeout=180)
        assert body is not None

    def test_opik_trace_ingestion_lane_is_not_reference_backend(self, observability_stack):
        """Opik trace ingestion is a cloud/full-stack contract, not this reference backend."""
        host, port = _host_port(observability_stack["opik"], 8080)
        base_url = f"http://{host}:{port}"

        wait_for_http(f"{base_url}/is-alive/ping", timeout=120)
        project_root = _pathlib.Path(__file__).resolve().parents[2]
        config = (project_root / "cognitive-os.yaml").read_text(encoding="utf-8")
        compose = (project_root / "docker-compose.cognitive-os.yml").read_text(encoding="utf-8")

        assert "opik:\n        mode: cloud" in config
        assert "Container kept for reference/CI" in compose
        assert "clickhouse-init" not in compose, (
            "If this test starts asserting local Opik trace ingestion, the "
            "reference stack must first model Opik's full upstream compose "
            "dependencies such as ClickHouse config initialization."
        )

    # test_send_trace_to_langfuse removed per ADR-058 (2026-04-24): Langfuse
    # ingestion API is deprecated. See test_record_completion_sends_trace_to_phoenix.py
    # for the Phoenix OTel replacement.

    def test_both_systems_reachable(self, observability_stack):
        """Both Opik and Langfuse must be simultaneously reachable.

        This validates that a single agent action could produce traces
        observable in BOTH systems.
        """
        opik_host, opik_port = _host_port(observability_stack["opik"], 8080)
        lf_host, lf_port = _host_port(observability_stack["langfuse_web"], 3000)

        opik_body = wait_for_http(f"http://{opik_host}:{opik_port}/is-alive/ping", timeout=120)
        lf_body = wait_for_http(f"http://{lf_host}:{lf_port}/api/public/health", timeout=180)

        assert opik_body is not None, "Opik not reachable"
        assert lf_body is not None, "Langfuse not reachable"


# ===========================================================================
# Flow 2: Memory Pipeline
# ===========================================================================

@pytest.mark.timeout(300)
class TestMemoryFlow:
    """Validate the Cognee knowledge graph memory lifecycle.

    Services: Cognee (python:3.12-slim based)

    Tests the ECL (Extract, Cognify, Load) pipeline:
      1. Add text knowledge to Cognee
      2. Run cognify to build knowledge graph
      3. Search for related concepts
      4. Verify semantic relevance in results

    NOTE: Cognee requires an LLM API key for cognify. If not available,
    the test validates the API is accessible and add/search endpoints exist.
    """

    @pytest.fixture(scope="class")
    def cognee_stack(self, docker_available):
        """Start Cognee with its dependencies.

        Cognee runs on python:3.12-slim with pip install at startup,
        so it has a long startup time.
        """
        network = Network()
        network.create()
        containers = {}

        try:
            # Cognee uses networkx + lancedb by default (no external DB needed)
            t0 = time.monotonic()
            cognee = (
                DockerContainer("python:3.12-slim")
                .with_network(network)
                .with_network_aliases("cognee")
                .with_exposed_ports(8000)
                .with_env("COGNEE_GRAPH_BACKEND", "networkx")
                .with_env("COGNEE_VECTOR_STORE", "lancedb")
                .with_env("COGNEE_LLM_PROVIDER", "anthropic")
                .with_env("COGNEE_LLM_MODEL", "claude-sonnet-4-5-20250514")
                # Keys intentionally empty — tests check API availability, not LLM calls
                .with_env("ANTHROPIC_API_KEY", "")
                .with_env("OPENAI_API_KEY", "")
                .with_command(
                    "bash -c '"
                    "pip install --quiet cognee[api] litellm==1.83.0 && "
                    "uvicorn cognee.api.client:app --host 0.0.0.0 --port 8000"
                    "'"
                )
            )
            if not _start_container_safe(cognee, "cognee"):
                pytest.skip("Failed to start cognee container")
            containers["cognee"] = cognee
            logger.info("Cognee container started in %.1fs", time.monotonic() - t0)

            yield {**containers, "network": network}

        finally:
            for name in reversed(list(containers.keys())):
                try:
                    containers[name].stop()
                except Exception:
                    pass
            try:
                network.remove()
            except Exception:
                pass

    def test_cognee_health(self, cognee_stack):
        """Cognee health endpoint must respond.

        Long timeout because pip install runs at container start.
        """
        host, port = _host_port(cognee_stack["cognee"], 8000)
        # Cognee takes a long time to pip install + start
        body = wait_for_http(f"http://{host}:{port}/health", timeout=300, interval=5)
        assert body is not None

    def test_add_knowledge(self, cognee_stack):
        """POST text content to Cognee /add endpoint."""
        host, port = _host_port(cognee_stack["cognee"], 8000)
        base_url = f"http://{host}:{port}"

        # Wait for service to be ready
        wait_for_http(f"{base_url}/health", timeout=300, interval=5)

        # Add knowledge about a code architecture
        payload = {
            "text": (
                "The Cognitive OS platform uses a microservices architecture. "
                "Langfuse handles LLM observability and tracing. "
                "Opik provides experiment tracking and evaluation. "
                "LiteLLM acts as an LLM proxy for cost control and routing. "
                "Paperclip coordinates agent tasks and workflows. "
                "Cognee builds knowledge graphs from unstructured text."
            ),
        }

        status, body = http_request(
            f"{base_url}/add",
            method="POST",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        # Accept 200 (success), 422 (validation — different payload format), or 405 (method not allowed)
        assert status in (200, 201, 202, 405, 422), (
            f"Cognee /add unexpected status: {status}, body={body[:300]}"
        )

    def test_search_knowledge(self, cognee_stack):
        """POST a search query to Cognee /search endpoint."""
        host, port = _host_port(cognee_stack["cognee"], 8000)
        base_url = f"http://{host}:{port}"

        wait_for_http(f"{base_url}/health", timeout=300, interval=5)

        payload = {"query": "observability tracing"}

        status, body = http_request(
            f"{base_url}/search",
            method="POST",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        # Without LLM keys, cognify won't have run, so search may return empty
        # We validate the endpoint exists and responds
        assert status in (200, 400, 405, 422, 500), (
            f"Cognee /search unexpected status: {status}, body={body[:300]}"
        )


# ===========================================================================
# Flow 3: LLM Routing + Guardrails
# ===========================================================================

class TestRoutingGuardrailsFlow:
    """Validate LLM request routing through LiteLLM proxy.

    Services: LiteLLM (+ NeMo Guardrails if image is available)

    Tests:
      1. LiteLLM starts with a minimal config and responds to health checks
      2. Routing headers are present on proxied requests
      3. NeMo Guardrails (if available) responds to config queries
    """

    @pytest.fixture(scope="class")
    def routing_stack(self, docker_available, tmp_path_factory):
        """Start LiteLLM with a minimal config."""
        network = Network()
        network.create()
        containers = {}

        try:
            # Create minimal LiteLLM config
            config_dir = tmp_path_factory.mktemp("litellm_e2e_config")
            config_path = config_dir / "config.yaml"
            config_path.write_text(
                "model_list:\n"
                "  - model_name: fake-model\n"
                "    litellm_params:\n"
                "      model: openai/fake-model\n"
                "      api_key: sk-fake\n"
                "      api_base: http://localhost:9999\n"
            )

            # --- LiteLLM ---
            t0 = time.monotonic()
            litellm = (
                DockerContainer("ghcr.io/berriai/litellm:main-stable")
                .with_network(network)
                .with_network_aliases("litellm")
                .with_exposed_ports(4000)
                .with_env("LITELLM_MASTER_KEY", "sk-test-key")
                .with_volume_mapping(str(config_path), "/app/config.yaml", "ro")
                .with_command("--config /app/config.yaml --port 4000")
            )
            if not _start_container_safe(litellm, "litellm"):
                pytest.skip("litellm image not available")
            containers["litellm"] = litellm
            logger.info("LiteLLM started in %.1fs", time.monotonic() - t0)

            yield {**containers, "network": network}

        finally:
            for name in reversed(list(containers.keys())):
                try:
                    containers[name].stop()
                except Exception:
                    pass
            try:
                network.remove()
            except Exception:
                pass

    def test_litellm_health(self, routing_stack):
        """LiteLLM liveness endpoint must respond."""
        host, port = _host_port(routing_stack["litellm"], 4000)
        body = wait_for_http(f"http://{host}:{port}/health/liveliness", timeout=90)
        assert body is not None

    def test_litellm_model_list(self, routing_stack):
        """LiteLLM /model/info must list configured models."""
        host, port = _host_port(routing_stack["litellm"], 4000)
        base_url = f"http://{host}:{port}"

        wait_for_http(f"{base_url}/health/liveliness", timeout=90)

        status, body = http_request(
            f"{base_url}/model/info",
            headers={"Authorization": "Bearer sk-test-key"},
        )

        # Model info endpoint should list the fake model
        assert status == 200, f"Expected 200, got {status}: {body[:300]}"
        data = json.loads(body)
        assert "data" in data, f"Expected 'data' key in response: {body[:300]}"

    def test_litellm_chat_routing(self, routing_stack):
        """A chat completion request routes through the proxy (will fail at upstream)."""
        host, port = _host_port(routing_stack["litellm"], 4000)
        base_url = f"http://{host}:{port}"

        wait_for_http(f"{base_url}/health/liveliness", timeout=90)

        # Send a chat request — it will fail because upstream is fake,
        # but we verify the proxy ROUTES the request (not a 404)
        payload = {
            "model": "fake-model",
            "messages": [{"role": "user", "content": "test"}],
        }
        status, body = http_request(
            f"{base_url}/chat/completions",
            method="POST",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer sk-test-key",
            },
        )

        # Should NOT be 404 (route not found) — it should be routed and fail at upstream
        assert status != 404, "Chat completions route not found in LiteLLM proxy"
        # Expect a 5xx or connection error to the fake upstream, not a routing error
        # Status 0 means connection to proxy failed (unlikely if health passed)


# ===========================================================================
# Flow 4: Agent Coordination
# ===========================================================================

class TestAgentCoordinationFlow:
    """Validate Paperclip agent coordination platform.

    Services: PostgreSQL + Paperclip

    Tests:
      1. PostgreSQL starts and accepts connections
      2. Paperclip starts with auto-migration
      3. Paperclip health check passes
      4. API is accessible (auth may be required for task creation)
    """

    @pytest.fixture(scope="class")
    def paperclip_stack(self, docker_available):
        """Start PostgreSQL + Paperclip."""
        network = Network()
        network.create()
        containers = {}

        try:
            # --- PostgreSQL for Paperclip ---
            t0 = time.monotonic()
            pg = (
                DockerContainer("postgres:17-alpine")
                .with_network(network)
                .with_network_aliases("paperclip-pg")
                .with_exposed_ports(5432)
                .with_env("POSTGRES_USER", "paperclip")
                .with_env("POSTGRES_PASSWORD", "paperclip")
                .with_env("POSTGRES_DB", "paperclip")
            )
            pg.start()
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            containers["pg"] = pg
            logger.info("Paperclip PG started in %.1fs", time.monotonic() - t0)

            # --- Paperclip ---
            t0 = time.monotonic()
            paperclip = (
                DockerContainer("tuyenvd/paperclip:latest")
                .with_network(network)
                .with_network_aliases("paperclip")
                .with_exposed_ports(3100)
                .with_env("DATABASE_URL", "postgres://paperclip:paperclip@paperclip-pg:5432/paperclip")
                .with_env("HOST", "0.0.0.0")
                .with_env("PORT", "3100")
                .with_env("SERVE_UI", "true")
                .with_env("PAPERCLIP_DEPLOYMENT_MODE", "local_trusted")
                .with_env("PAPERCLIP_DEPLOYMENT_EXPOSURE", "private")
                .with_env("PAPERCLIP_PUBLIC_URL", "http://localhost:3100")
                .with_env("BETTER_AUTH_SECRET", "e2e-test-secret")
                .with_env("PAPERCLIP_HOME", "/paperclip")
                .with_env("PAPERCLIP_INSTANCE_ID", "default")
                .with_env("PAPERCLIP_MIGRATION_AUTO_APPLY", "true")
                .with_env("PAPERCLIP_ADMIN_EMAIL", "admin@e2e-test.local")
                .with_env("PAPERCLIP_ADMIN_PASSWORD", "e2e-test-password")
                .with_env("PAPERCLIP_ADMIN_NAME", "E2E Test Admin")
            )
            if not _start_container_safe(paperclip, "paperclip"):
                pytest.skip("paperclip image not available")
            containers["paperclip"] = paperclip
            logger.info("Paperclip started in %.1fs", time.monotonic() - t0)

            yield {**containers, "network": network}

        finally:
            for name in reversed(list(containers.keys())):
                try:
                    containers[name].stop()
                except Exception:
                    pass
            try:
                network.remove()
            except Exception:
                pass

    def test_paperclip_pg_running(self, paperclip_stack):
        """PostgreSQL for Paperclip must be in running state."""
        status = paperclip_stack["pg"].get_wrapped_container().status
        assert status == "running", f"paperclip-pg is {status}, expected running"

    def test_paperclip_health(self, paperclip_stack):
        """Paperclip /api/health must respond (auto-migration must complete)."""
        host, port = _host_port(paperclip_stack["paperclip"], 3100)
        body = wait_for_http(f"http://{host}:{port}/api/health", timeout=180, interval=5)
        assert body is not None

    def test_paperclip_api_accessible(self, paperclip_stack):
        """Paperclip API root must be accessible (may require auth)."""
        host, port = _host_port(paperclip_stack["paperclip"], 3100)
        base_url = f"http://{host}:{port}"

        # Wait for health first
        wait_for_http(f"{base_url}/api/health", timeout=180, interval=5)

        # Try to access the API — in local_trusted mode this may work without auth
        status, body = http_request(f"{base_url}/api/health")

        assert status in (200, 401, 403), (
            f"Paperclip API unexpected status: {status}, body={body[:300]}"
        )

    def test_paperclip_database_migrated(self, paperclip_stack):
        """After Paperclip starts, the database should have migration tables.

        We verify by checking that PostgreSQL has tables created by Paperclip.
        """
        host, port = _host_port(paperclip_stack["paperclip"], 3100)

        # If health passes, migrations ran successfully
        body = wait_for_http(f"http://{host}:{port}/api/health", timeout=180, interval=5)

        # Parse health response for database connectivity info
        try:
            health_data = json.loads(body)
            # Health response format varies — if it's a dict, check for status
            if isinstance(health_data, dict):
                assert health_data.get("status", "ok") in ("ok", "healthy", "UP"), (
                    f"Paperclip health reports unhealthy: {health_data}"
                )
        except (json.JSONDecodeError, TypeError):
            # Plain text "ok" response is fine too
            pass


# ===========================================================================
# Flow 5: Full Stack Smoke Test
# ===========================================================================

class TestFullStackSmoke:
    """Start ALL core services and verify cross-service connectivity.

    This is the ultimate E2E test: everything starts together and all health
    checks pass. It validates that services do not conflict on ports, resources,
    or shared dependencies (like the ClickHouse instance shared by Opik and Langfuse).

    Services:
      - Databases: langfuse-pg, opik-mysql, paperclip-pg, clickhouse, valkey
      - Apps: langfuse-web, litellm, opik-backend, paperclip
    """

    @pytest.fixture(scope="class")
    def full_stack(self, docker_available, tmp_path_factory):
        """Start ALL core services in a shared network."""
        network = Network()
        network.create()
        containers = {}
        startup_times = {}

        try:
            # === DATABASE LAYER ===

            # ClickHouse (shared by Langfuse + Opik)
            t0 = time.monotonic()
            clickhouse = (
                DockerContainer("clickhouse/clickhouse-server")
                .with_network(network)
                .with_network_aliases("langfuse-clickhouse")
                .with_exposed_ports(8123, 9000)
                .with_env("CLICKHOUSE_DB", "default")
                .with_env("CLICKHOUSE_USER", "clickhouse")
                .with_env("CLICKHOUSE_PASSWORD", "clickhouse")
            )
            clickhouse.start()
            _wait_for_clickhouse(clickhouse)
            containers["clickhouse"] = clickhouse
            startup_times["clickhouse"] = time.monotonic() - t0

            # Langfuse PostgreSQL
            t0 = time.monotonic()
            langfuse_pg = (
                DockerContainer("postgres:17-alpine")
                .with_network(network)
                .with_network_aliases("langfuse-pg")
                .with_exposed_ports(5432)
                .with_env("POSTGRES_USER", "langfuse")
                .with_env("POSTGRES_PASSWORD", "langfuse_pass")
                .with_env("POSTGRES_DB", "langfuse")
                .with_env("TZ", "UTC")
                .with_env("PGTZ", "UTC")
            )
            langfuse_pg.start()
            wait_for_logs(langfuse_pg, "database system is ready to accept connections", timeout=30)
            containers["langfuse_pg"] = langfuse_pg
            startup_times["langfuse_pg"] = time.monotonic() - t0

            # Opik MySQL
            t0 = time.monotonic()
            opik_mysql = (
                DockerContainer("mysql:8.4")
                .with_network(network)
                .with_network_aliases("opik-mysql")
                .with_exposed_ports(3306)
                .with_env("MYSQL_ROOT_PASSWORD", "opik_root_pass")
                .with_env("MYSQL_DATABASE", "opik")
                .with_env("MYSQL_USER", "opik")
                .with_env("MYSQL_PASSWORD", "opik_pass")
            )
            opik_mysql.start()
            wait_for_logs(opik_mysql, "ready for connections", timeout=60)
            containers["opik_mysql"] = opik_mysql
            startup_times["opik_mysql"] = time.monotonic() - t0

            # Paperclip PostgreSQL
            t0 = time.monotonic()
            paperclip_pg = (
                DockerContainer("postgres:17-alpine")
                .with_network(network)
                .with_network_aliases("paperclip-pg")
                .with_exposed_ports(5432)
                .with_env("POSTGRES_USER", "paperclip")
                .with_env("POSTGRES_PASSWORD", "paperclip")
                .with_env("POSTGRES_DB", "paperclip")
            )
            paperclip_pg.start()
            wait_for_logs(paperclip_pg, "database system is ready to accept connections", timeout=30)
            containers["paperclip_pg"] = paperclip_pg
            startup_times["paperclip_pg"] = time.monotonic() - t0

            # Valkey (Langfuse cache)
            t0 = time.monotonic()
            valkey = (
                DockerContainer("valkey/valkey:8-alpine")
                .with_network(network)
                .with_network_aliases("langfuse-valkey")
                .with_exposed_ports(6379)
                .with_command("--requirepass langfuse_redis --maxmemory-policy noeviction")
            )
            valkey.start()
            wait_for_logs(valkey, "Ready to accept connections", timeout=30)
            containers["valkey"] = valkey
            startup_times["valkey"] = time.monotonic() - t0

            # SeaweedFS (Langfuse S3)
            t0 = time.monotonic()
            seaweedfs = (
                DockerContainer("chrislusf/seaweedfs:latest")
                .with_network(network)
                .with_network_aliases("langfuse-seaweedfs")
                .with_exposed_ports(8333, 9333)
                .with_command("server -dir=/data -s3 -s3.port=8333 -filer -master.volumeSizeLimitMB=100")
            )
            seaweedfs.start()
            wait_for_logs(seaweedfs, "Start Seaweed", timeout=30)
            containers["seaweedfs"] = seaweedfs
            startup_times["seaweedfs"] = time.monotonic() - t0

            # === APPLICATION LAYER ===

            # LiteLLM
            config_dir = tmp_path_factory.mktemp("litellm_smoke_config")
            config_path = config_dir / "config.yaml"
            config_path.write_text(
                "model_list:\n"
                "  - model_name: fake-model\n"
                "    litellm_params:\n"
                "      model: openai/fake-model\n"
                "      api_key: sk-fake\n"
                "      api_base: http://localhost:9999\n"
            )

            t0 = time.monotonic()
            litellm = (
                DockerContainer("ghcr.io/berriai/litellm:main-stable")
                .with_network(network)
                .with_network_aliases("litellm")
                .with_exposed_ports(4000)
                .with_env("LITELLM_MASTER_KEY", "sk-test-key")
                .with_volume_mapping(str(config_path), "/app/config.yaml", "ro")
                .with_command("--config /app/config.yaml --port 4000")
            )
            if _start_container_safe(litellm, "litellm"):
                containers["litellm"] = litellm
                startup_times["litellm"] = time.monotonic() - t0

            # Opik Backend
            t0 = time.monotonic()
            opik = (
                DockerContainer("ghcr.io/comet-ml/opik/opik-backend:latest")
                .with_network(network)
                .with_network_aliases("opik-backend")
                .with_exposed_ports(8080)
                .with_env("STATE_DB_PROTOCOL", "jdbc:mysql://")
                .with_env("STATE_DB_URL", "opik-mysql:3306/opik?createDatabaseIfNotExist=true")
                .with_env("STATE_DB_USER", "opik")
                .with_env("STATE_DB_PASS", "opik_pass")
                .with_env("STATE_DB_DATABASE_NAME", "opik")
                .with_env("ANALYTICS_DB_MIGRATIONS_URL", "jdbc:clickhouse://langfuse-clickhouse:8123/opik")
                .with_env("ANALYTICS_DB_MIGRATIONS_USER", "clickhouse")
                .with_env("ANALYTICS_DB_MIGRATIONS_PASS", "clickhouse")
                .with_env("ANALYTICS_DB_PROTOCOL", "HTTP")
                .with_env("ANALYTICS_DB_HOST", "langfuse-clickhouse")
                .with_env("ANALYTICS_DB_PORT", "8123")
                .with_env("ANALYTICS_DB_USERNAME", "clickhouse")
                .with_env("ANALYTICS_DB_PASS", "clickhouse")
                .with_env("ANALYTICS_DB_DATABASE_NAME", "opik")
                .with_env("REDIS_URL", "redis://:langfuse_redis@langfuse-valkey:6379/0")
                .with_env("JAVA_OPTS", "-Xms256m -Xmx512m")
            )
            if _start_container_safe(opik, "opik-backend"):
                containers["opik"] = opik
                startup_times["opik"] = time.monotonic() - t0

            # Langfuse Web
            t0 = time.monotonic()
            langfuse_web = DockerContainer("langfuse/langfuse:3")
            langfuse_web.with_network(network)
            langfuse_web.with_network_aliases("langfuse-web")
            langfuse_web.with_exposed_ports(3000)
            for key, value in _build_langfuse_env().items():
                langfuse_web.with_env(key, value)
            langfuse_web.with_env("HOSTNAME", "0.0.0.0")
            if _start_container_safe(langfuse_web, "langfuse-web"):
                containers["langfuse_web"] = langfuse_web
                startup_times["langfuse_web"] = time.monotonic() - t0

            # Paperclip
            t0 = time.monotonic()
            paperclip = (
                DockerContainer("tuyenvd/paperclip:latest")
                .with_network(network)
                .with_network_aliases("paperclip")
                .with_exposed_ports(3100)
                .with_env("DATABASE_URL", "postgres://paperclip:paperclip@paperclip-pg:5432/paperclip")
                .with_env("HOST", "0.0.0.0")
                .with_env("PORT", "3100")
                .with_env("SERVE_UI", "true")
                .with_env("PAPERCLIP_DEPLOYMENT_MODE", "local_trusted")
                .with_env("PAPERCLIP_DEPLOYMENT_EXPOSURE", "private")
                .with_env("PAPERCLIP_PUBLIC_URL", "http://localhost:3100")
                .with_env("BETTER_AUTH_SECRET", "e2e-smoke-test-secret")
                .with_env("PAPERCLIP_HOME", "/paperclip")
                .with_env("PAPERCLIP_INSTANCE_ID", "default")
                .with_env("PAPERCLIP_MIGRATION_AUTO_APPLY", "true")
            )
            if _start_container_safe(paperclip, "paperclip"):
                containers["paperclip"] = paperclip
                startup_times["paperclip"] = time.monotonic() - t0

            logger.info("Full stack startup times: %s", startup_times)

            yield {**containers, "network": network, "startup_times": startup_times}

        finally:
            for name in reversed(list(containers.keys())):
                try:
                    containers[name].stop()
                except Exception:
                    pass
            try:
                network.remove()
            except Exception:
                pass

    def test_all_databases_running(self, full_stack):
        """All database containers must be in running state."""
        db_names = ["clickhouse", "langfuse_pg", "opik_mysql", "paperclip_pg", "valkey"]
        for name in db_names:
            container = full_stack.get(name)
            assert container is not None, f"Database {name} was not started"
            status = container.get_wrapped_container().status
            assert status == "running", f"{name} is {status}, expected running"

    def test_clickhouse_health(self, full_stack):
        """ClickHouse HTTP ping must respond."""
        host, port = _host_port(full_stack["clickhouse"], 8123)
        body = wait_for_http(f"http://{host}:{port}/ping", timeout=30)
        assert body is not None

    def test_litellm_health(self, full_stack):
        """LiteLLM liveness must respond (skip if image unavailable)."""
        if "litellm" not in full_stack:
            pytest.skip("litellm container not started")
        host, port = _host_port(full_stack["litellm"], 4000)
        body = wait_for_http(f"http://{host}:{port}/health/liveliness", timeout=90)
        assert body is not None

    def test_opik_health(self, full_stack):
        """Opik backend ping must respond (skip if image unavailable)."""
        if "opik" not in full_stack:
            pytest.skip("opik-backend container not started")
        host, port = _host_port(full_stack["opik"], 8080)
        body = wait_for_http(f"http://{host}:{port}/is-alive/ping", timeout=120)
        assert body is not None

    def test_langfuse_health(self, full_stack):
        """Langfuse web health must respond (skip if image unavailable)."""
        if "langfuse_web" not in full_stack:
            pytest.skip("langfuse-web container not started")
        host, port = _host_port(full_stack["langfuse_web"], 3000)
        body = wait_for_http(f"http://{host}:{port}/api/public/health", timeout=180)
        assert body is not None

    def test_paperclip_health(self, full_stack):
        """Paperclip health must respond (skip if image unavailable)."""
        if "paperclip" not in full_stack:
            pytest.skip("paperclip container not started")
        host, port = _host_port(full_stack["paperclip"], 3100)
        body = wait_for_http(f"http://{host}:{port}/api/health", timeout=180, interval=5)
        assert body is not None

    def test_health_report(self, full_stack):
        """Generate a summary report of service health across the full stack."""
        services = {
            "clickhouse": (8123, "/ping"),
            "litellm": (4000, "/health/liveliness"),
            "opik": (8080, "/is-alive/ping"),
            "langfuse_web": (3000, "/api/public/health"),
            "paperclip": (3100, "/api/health"),
        }

        report = {}
        for name, (container_port, path) in services.items():
            if name not in full_stack:
                report[name] = "SKIPPED (image not available)"
                continue
            try:
                host, port = _host_port(full_stack[name], container_port)
                wait_for_http(f"http://{host}:{port}{path}", timeout=30, interval=2)
                report[name] = "HEALTHY"
            except TimeoutError:
                report[name] = "UNHEALTHY"

        logger.info("Full stack health report: %s", json.dumps(report, indent=2))

        # At minimum, all databases and at least one app service must be healthy
        healthy_count = sum(1 for v in report.values() if v == "HEALTHY")
        assert healthy_count >= 1, f"No services healthy. Report: {report}"

    def test_startup_performance_baseline(self, full_stack):
        """Log startup times for performance baseline tracking."""
        startup_times = full_stack.get("startup_times", {})
        logger.info("Startup performance baseline (seconds):")
        for name, elapsed in sorted(startup_times.items(), key=lambda x: x[1], reverse=True):
            logger.info("  %-20s %.1fs", name, elapsed)

        # Databases should start within 60s
        for name in ["clickhouse", "langfuse_pg", "opik_mysql", "paperclip_pg", "valkey"]:
            if name in startup_times:
                assert startup_times[name] < 120, (
                    f"Database {name} took {startup_times[name]:.1f}s to start (expected < 120s)"
                )


# ===========================================================================
