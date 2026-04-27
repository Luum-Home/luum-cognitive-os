"""Shared fixtures for integration tests.

SESSION-SCOPED CONTAINER STRATEGY
----------------------------------
All Docker containers are created at SESSION scope so they start once per
``pytest`` run and are shared across every test class that needs them.
This replaces the previous CLASS-scoped fixtures that spawned a new container
per test class, causing 10+ simultaneous containers (4 ClickHouse, 2 Postgres,
2 Valkey …) and up to 6 GB RAM / 78 % CPU.

Isolation within a shared container
------------------------------------
* PostgreSQL  – each test uses ``conn.rollback()`` after every test method and
  CREATE TABLE … IF NOT EXISTS for DDL; tables are namespaced per test class.
* Valkey/Redis – tests use unique key prefixes (``langfuse:test:``, etc.) that
  don't collide; redis_client.flushdb() is NOT called to keep fixtures cheap.
* ClickHouse  – each test drops and recreates its own table.
* MySQL        – transactions are rolled back after every test method.

Reuse of already-running compose containers
--------------------------------------------
Each fixture first inspects ``docker ps`` for the compose service container
(e.g. ``cognitive-os-langfuse-pg-1``).  If found it builds an
``_ExistingContainer`` shim that exposes the same interface as a
``testcontainers`` container, allowing zero-startup-time reuse.
"""
import signal
import shutil
import subprocess
import sys
import time
import socket
from typing import Optional

import pytest
import os

# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "docker: marks tests requiring Docker")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests spanning multiple services")


# ---------------------------------------------------------------------------
# Timeout override — all integration tests need 300 s
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _integration_test_timeout():
    """Override the global 30s timeout with 300s for integration tests.

    Docker containers need 60-120s to start. The global conftest.py sets 30s
    via SIGALRM which kills testcontainers fixtures during setup.
    """
    if sys.platform == "win32":
        yield
        return
    old_handler = signal.getsignal(signal.SIGALRM)
    signal.alarm(300)  # 5 minutes for container startup + test
    yield
    signal.alarm(0)
    if callable(old_handler):
        signal.signal(signal.SIGALRM, old_handler)


# ---------------------------------------------------------------------------
# Cognitive OS environment
# ---------------------------------------------------------------------------

@pytest.fixture
def cognitive_os_env(tmp_path, monkeypatch):
    """Set up Cognitive OS environment variables for testing."""
    project_dir = tmp_path / "cognitive-os-test"
    project_dir.mkdir()
    env = {
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_SESSION_ID": f"test-session-{os.getpid()}",
        "OPIK_API_URL": "http://localhost:5173/api",
        "OPIK_PROJECT_NAME": "cognitive-os-test",
        "COGNEE_GRAPH_BACKEND": "networkx",
        "COGNEE_VECTOR_STORE": "lancedb",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    yield env


# ---------------------------------------------------------------------------
# Docker availability check (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def docker_available():
    """Check if Docker is available — skip the entire session if not."""
    if not shutil.which("docker"):
        pytest.skip("Docker not installed")
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=10)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("Docker not running")
    return True


# ---------------------------------------------------------------------------
# Shim for reusing containers that are already running (e.g. compose stack)
# ---------------------------------------------------------------------------

class _ExistingContainer:
    """Minimal shim that satisfies the testcontainers container interface.

    Used when a compose container (e.g. ``cognitive-os-langfuse-pg-1``) is
    already running so we can skip the ``testcontainers`` startup overhead.
    """

    def __init__(self, host: str, port: int, *, extra_ports: Optional[dict] = None):
        self._host = host
        self._port = port
        self._extra_ports = extra_ports or {}

    def get_container_host_ip(self) -> str:
        return self._host

    def get_exposed_port(self, container_port: int) -> str:
        if container_port == list(self._extra_ports.keys())[0] if self._extra_ports else None:
            return str(self._extra_ports[container_port])
        return str(self._port)

    def get_connection_url(self) -> str:
        raise NotImplementedError("Use get_container_host_ip / get_exposed_port directly")

    class _WrappedContainer:
        status = "running"

    def get_wrapped_container(self):
        return self._WrappedContainer()


def _compose_container_port(container_name: str, internal_port: int) -> Optional[tuple]:
    """Return (host, mapped_port) if *container_name* is running, else None."""
    try:
        result = subprocess.run(
            ["docker", "port", container_name, str(internal_port)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Output format: "0.0.0.0:NNNNN" or "[::]:NNNNN"
            addr = result.stdout.strip().split("\n")[0]
            host_part, port_part = addr.rsplit(":", 1)
            host = "127.0.0.1" if host_part in ("0.0.0.0", "[::]", "") else host_part.strip("[]")
            return host, int(port_part)
    except Exception:
        pass
    return None


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    """Block until TCP port is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"Port {host}:{port} not reachable within {timeout}s")


# ===========================================================================
# SESSION-SCOPED SHARED CONTAINER FIXTURES
# ===========================================================================
# These start ONCE per ``pytest`` session and are shared across all test
# classes.  Individual tests inside each class are still isolated via
# per-test ``connection`` fixtures that roll back transactions.
# ===========================================================================

# ---------------------------------------------------------------------------
# PostgreSQL — langfuse credentials (langfuse / langfuse_pass / langfuse db)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def langfuse_pg_container(docker_available):
    """Session-scoped Postgres 17 container for Langfuse tests.

    Tries to reuse the running compose container first.
    Credential tests in TestLangfusePostgres rely on user=langfuse and db=langfuse.
    """
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    # Try reusing already-running compose container.
    compose_result = _compose_container_port("cognitive-os-langfuse-pg-1", 5432)
    if compose_result:
        host, port = compose_result
        try:
            _wait_for_port(host, port, timeout=5)
            yield _ExistingContainer(host, port)
            return
        except TimeoutError:
            pass  # fall through to testcontainers

    container = PostgresContainer(
        image="postgres:17-alpine",
        username="langfuse",
        password="langfuse_pass",
        dbname="langfuse",
    )
    with container:
        yield container


# ---------------------------------------------------------------------------
# PostgreSQL — paperclip credentials (paperclip / paperclip / paperclip db)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def paperclip_pg_container(docker_available):
    """Session-scoped Postgres 17 container for Paperclip tests."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    # Paperclip uses a different user/db — must be a separate container.
    container = PostgresContainer(
        image="postgres:17-alpine",
        username="paperclip",
        password="paperclip",
        dbname="paperclip",
    )
    with container:
        yield container


# ---------------------------------------------------------------------------
# Valkey (Redis-compatible) — shared, auth password langfuse_redis
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def valkey_container(docker_available):
    """Session-scoped Valkey 8 container shared across all tests.

    Tries to reuse the running compose container (langfuse-valkey) first.
    """
    try:
        from testcontainers.core.container import DockerContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    compose_result = _compose_container_port("cognitive-os-langfuse-valkey-1", 6379)
    if compose_result:
        host, port = compose_result
        try:
            _wait_for_port(host, port, timeout=5)
            yield _ExistingContainer(host, port)
            return
        except TimeoutError:
            pass

    container = (
        DockerContainer(image="valkey/valkey:8-alpine")
        .with_exposed_ports(6379)
        .with_command("valkey-server --requirepass langfuse_redis")
    )
    container.start()
    _wait_for_port(
        container.get_container_host_ip(),
        int(container.get_exposed_port(6379)),
        timeout=30,
    )
    yield container
    container.stop()


# ---------------------------------------------------------------------------
# ClickHouse — shared, auth clickhouse / clickhouse
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def clickhouse_container(docker_available):
    """Session-scoped ClickHouse container shared across all tests.

    Tries to reuse the running compose container first.
    """
    try:
        from testcontainers.core.container import DockerContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    from urllib.request import urlopen
    from urllib.error import URLError

    compose_result = _compose_container_port("cognitive-os-langfuse-clickhouse-1", 8123)
    if compose_result:
        host, port = compose_result
        try:
            _wait_for_port(host, port, timeout=5)
            yield _ExistingContainer(host, port)
            return
        except TimeoutError:
            pass

    container = (
        DockerContainer(image="clickhouse/clickhouse-server:latest")
        .with_exposed_ports(8123, 9000)
        .with_env("CLICKHOUSE_DB", "default")
        .with_env("CLICKHOUSE_USER", "clickhouse")
        .with_env("CLICKHOUSE_PASSWORD", "clickhouse")
    )
    container.start()
    _wait_for_port(
        container.get_container_host_ip(),
        int(container.get_exposed_port(8123)),
        timeout=60,
    )

    # Wait for ClickHouse HTTP interface to actually respond
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(8123))
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            url = f"http://{host}:{port}/?query=SELECT+1&user=clickhouse&password=clickhouse"
            with urlopen(url, timeout=5) as resp:
                if resp.read().decode().strip() == "1":
                    break
        except (URLError, OSError):
            time.sleep(1)
    else:
        container.stop()
        raise TimeoutError("ClickHouse HTTP interface did not become ready within 60s")

    yield container
    container.stop()


# ---------------------------------------------------------------------------
# MySQL — shared, opik credentials
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def mysql_container(docker_available):
    """Session-scoped MySQL 8.4 container for Opik tests."""
    try:
        from testcontainers.core.container import DockerContainer
        import mysql.connector
    except ImportError:
        pytest.skip("testcontainers or mysql-connector-python not installed")

    container = (
        DockerContainer(image="mysql:8.4")
        .with_exposed_ports(3306)
        .with_env("MYSQL_ROOT_PASSWORD", "opik_root_pass")
        .with_env("MYSQL_DATABASE", "opik")
        .with_env("MYSQL_USER", "opik")
        .with_env("MYSQL_PASSWORD", "opik_pass")
    )
    container.start()

    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(3306))
    _wait_for_port(host, port, timeout=90)

    # MySQL accepts TCP before user/db init completes — retry the handshake.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            conn = mysql.connector.connect(
                host=host, port=port,
                user="opik", password="opik_pass", database="opik",
                connection_timeout=5,
            )
            conn.close()
            break
        except mysql.connector.Error:
            time.sleep(2)
    else:
        container.stop()
        raise TimeoutError("MySQL did not become ready for user 'opik' within 60s")

    yield container
    container.stop()


# ---------------------------------------------------------------------------
# Langfuse app-layer infra — network + PG + Valkey + ClickHouse + SeaweedFS
# Shared by TestLangfuseWebService and TestLangfuseWorkerService so only ONE
# set of infrastructure containers is created for both test classes.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def langfuse_app_infra(docker_available):
    """Session-scoped Langfuse infrastructure stack (PG + Valkey + ClickHouse + SeaweedFS).

    Used by TestLangfuseWebService and TestLangfuseWorkerService.  Both app
    containers connect to these dependency containers via the shared Docker
    network using hostnames (langfuse-pg, langfuse-valkey, etc.).

    Yields a dict with keys: network, postgres, valkey, clickhouse, seaweedfs.
    """
    try:
        from testcontainers.core.container import DockerContainer
        from testcontainers.core.network import Network
        from testcontainers.core.waiting_utils import wait_for_logs
    except ImportError:
        pytest.skip("testcontainers not installed")

    network = Network()
    network.create()
    containers = {}

    try:
        # --- PostgreSQL ---
        postgres = (
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
        postgres.start()
        wait_for_logs(postgres, "database system is ready to accept connections", timeout=30)
        containers["postgres"] = postgres

        # --- Valkey (Redis-compatible) ---
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

        # --- ClickHouse ---
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
        wait_for_logs(clickhouse, "Ready for connections", timeout=60)
        containers["clickhouse"] = clickhouse

        # --- SeaweedFS (S3-compatible storage) ---
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

        yield {"network": network, **containers}

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
