#!/usr/bin/env python3
"""Integration tests for all database and cache services from docker-compose.

Tests real containers for each data store used by the platform:
  - langfuse-pg:         PostgreSQL 17 (Langfuse metadata)
  - opik-mysql:          MySQL 8.4 (Opik metadata)
  - langfuse-valkey:     Valkey 8 (Redis-compatible cache for Langfuse)
  - langfuse-clickhouse: ClickHouse (Langfuse analytics/OLAP)

All containers are SESSION-scoped (started once, shared across all test
classes).  Individual test isolation is achieved via per-test ``connection``
fixtures that roll back transactions after each test.

Run:
    python -m pytest tests/integration/test_databases.py -v
    python -m pytest tests/integration/test_databases.py -v -m docker

Requires:
    pip install testcontainers pytest psycopg2-binary mysql-connector-python redis
"""
import shutil
import subprocess
import time
import os

import pytest

# ---------------------------------------------------------------------------
# Guard: skip everything if testcontainers is missing
# ---------------------------------------------------------------------------
tc_available = True
RUN_DATABASE_CONTAINERS = os.environ.get("COS_RUN_DATABASE_CONTAINERS") == "1"
try:
    import testcontainers.postgres  # noqa: F401
    import testcontainers.core.container  # noqa: F401
except ImportError:
    tc_available = False

pytestmark = [
    pytest.mark.docker,
    pytest.mark.slow,
    pytest.mark.skipif(not tc_available, reason="testcontainers not installed"),
    pytest.mark.skipif(
        not RUN_DATABASE_CONTAINERS,
        reason=(
            "optional database container lane; set "
            "COS_RUN_DATABASE_CONTAINERS=1 to run"
        ),
    ),
]


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


if RUN_DATABASE_CONTAINERS and not _docker_ok():
    pytest.skip("Docker not available", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _wait_for_port(container, port: int, timeout: float = 30.0) -> None:
    """Block until *port* inside the container is accepting TCP connections."""
    import socket

    host = container.get_container_host_ip()
    mapped = int(container.get_exposed_port(port))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, mapped), timeout=2):
                return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(
        f"Port {port} on {host}:{mapped} did not become reachable within {timeout}s"
    )


# ===================================================================
# 1. langfuse-pg  (PostgreSQL 17)
# ===================================================================
class TestLangfusePostgres:
    """Validate PostgreSQL for the Langfuse service.

    Mirrors the langfuse-pg service from docker-compose:
      image: postgres:17-alpine
      POSTGRES_USER=langfuse, POSTGRES_PASSWORD=langfuse_pass, POSTGRES_DB=langfuse

    Uses the session-scoped ``langfuse_pg_container`` fixture from conftest.py —
    the container is started once and shared across all test classes that use it.
    """

    @pytest.fixture()
    def connection(self, langfuse_pg_container):
        """Return a psycopg2 connection, rolled back after each test."""
        import psycopg2

        container = langfuse_pg_container
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        conn = psycopg2.connect(
            host=host, port=port,
            user="langfuse", password="langfuse_pass", dbname="langfuse",
        )
        conn.autocommit = False
        yield conn
        conn.rollback()
        conn.close()

    def test_container_starts(self, langfuse_pg_container):
        """Container must be running and exposing a mapped port."""
        assert langfuse_pg_container.get_container_host_ip() is not None
        assert langfuse_pg_container.get_exposed_port(5432) is not None

    def test_select_one(self, connection):
        """Basic SELECT 1 proves the wire protocol works."""
        cur = connection.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1

    def test_server_version(self, connection):
        """Server must report PostgreSQL 17.x."""
        cur = connection.cursor()
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
        assert version.startswith("17"), f"Expected PG 17, got {version}"

    def test_create_table_insert_query(self, connection):
        """Full DDL + DML cycle: CREATE TABLE, INSERT, SELECT, verify rows."""
        cur = connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS langfuse_test (
                id SERIAL PRIMARY KEY,
                trace_id TEXT NOT NULL,
                score REAL NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "INSERT INTO langfuse_test (trace_id, score) VALUES (%s, %s) RETURNING id",
            ("trace-001", 0.95),
        )
        row_id = cur.fetchone()[0]
        assert row_id is not None

        cur.execute("SELECT trace_id, score FROM langfuse_test WHERE id = %s", (row_id,))
        row = cur.fetchone()
        assert row[0] == "trace-001"
        assert abs(row[1] - 0.95) < 1e-5

    def test_database_name(self, connection):
        """Connected database must be 'langfuse'."""
        cur = connection.cursor()
        cur.execute("SELECT current_database()")
        assert cur.fetchone()[0] == "langfuse"

    def test_current_user(self, connection):
        """Connected user must be 'langfuse'."""
        cur = connection.cursor()
        cur.execute("SELECT current_user")
        assert cur.fetchone()[0] == "langfuse"


# ===================================================================
# 2. opik-mysql  (MySQL 8.4)
# ===================================================================
class TestOpikMySQL:
    """Validate MySQL for the Opik observability service.

    Mirrors the opik-mysql service from docker-compose:
      image: mysql:8.4
      MYSQL_ROOT_PASSWORD=opik_root_pass, MYSQL_DATABASE=opik,
      MYSQL_USER=opik, MYSQL_PASSWORD=opik_pass

    Uses the session-scoped ``mysql_container`` fixture from conftest.py.
    """

    @pytest.fixture()
    def connection(self, mysql_container):
        """Return a mysql-connector-python connection."""
        import mysql.connector

        conn = mysql.connector.connect(
            host=mysql_container.get_container_host_ip(),
            port=int(mysql_container.get_exposed_port(3306)),
            user="opik",
            password="opik_pass",
            database="opik",
        )
        yield conn
        conn.rollback()
        conn.close()

    def test_container_starts(self, mysql_container):
        """Container must be running and exposing a mapped port."""
        assert mysql_container.get_container_host_ip() is not None
        assert mysql_container.get_exposed_port(3306) is not None

    def test_select_one(self, connection):
        """Basic SELECT 1 proves the wire protocol works."""
        cur = connection.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1

    def test_server_version(self, connection):
        """Server must report MySQL 8.4.x."""
        cur = connection.cursor()
        cur.execute("SELECT VERSION()")
        version = cur.fetchone()[0]
        assert version.startswith("8.4"), f"Expected MySQL 8.4, got {version}"

    def test_create_table_insert_query(self, connection):
        """Full DDL + DML cycle: CREATE TABLE, INSERT, SELECT, verify rows."""
        cur = connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS opik_test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                experiment_name VARCHAR(255) NOT NULL,
                metric_value DOUBLE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            "INSERT INTO opik_test (experiment_name, metric_value) VALUES (%s, %s)",
            ("exp-hallucination-v1", 0.87),
        )
        connection.commit()
        row_id = cur.lastrowid
        assert row_id is not None

        cur.execute(
            "SELECT experiment_name, metric_value FROM opik_test WHERE id = %s",
            (row_id,),
        )
        row = cur.fetchone()
        assert row[0] == "exp-hallucination-v1"
        assert abs(row[1] - 0.87) < 1e-5

    def test_database_name(self, connection):
        """Connected database must be 'opik'."""
        cur = connection.cursor()
        cur.execute("SELECT DATABASE()")
        assert cur.fetchone()[0] == "opik"

    def test_current_user(self, connection):
        """Connected user must be 'opik'."""
        cur = connection.cursor()
        cur.execute("SELECT CURRENT_USER()")
        user = cur.fetchone()[0]
        assert user.startswith("opik@"), f"Expected opik@*, got {user}"


# ===================================================================
# 4. langfuse-valkey  (Valkey 8, Redis-compatible)
# ===================================================================
class TestLangfuseValkey:
    """Validate Valkey (Redis-compatible) cache for Langfuse.

    Mirrors the langfuse-valkey service from docker-compose:
      image: valkey/valkey:8-alpine
      Auth password: langfuse_redis

    Uses the session-scoped ``valkey_container`` fixture from conftest.py.
    Uses redis-py client since Valkey is wire-compatible with Redis.
    """

    @pytest.fixture()
    def redis_client(self, valkey_container):
        """Return a redis-py client connected to the shared Valkey container."""
        import redis

        client = redis.Redis(
            host=valkey_container.get_container_host_ip(),
            port=int(valkey_container.get_exposed_port(6379)),
            password="langfuse_redis",
            decode_responses=True,
            socket_connect_timeout=5,
        )
        yield client
        client.close()

    def test_container_starts(self, valkey_container):
        """Container must be running and exposing a mapped port."""
        assert valkey_container.get_container_host_ip() is not None
        assert valkey_container.get_exposed_port(6379) is not None

    def test_ping(self, redis_client):
        """PING must return True, proving auth and connectivity."""
        assert redis_client.ping() is True

    def test_set_get(self, redis_client):
        """SET then GET must round-trip a string value."""
        redis_client.set("langfuse:test:key", "hello-valkey")
        value = redis_client.get("langfuse:test:key")
        assert value == "hello-valkey"

    def test_set_with_ttl(self, redis_client):
        """SET with EX (TTL) must store and be retrievable before expiry."""
        redis_client.set("langfuse:test:ttl", "ephemeral", ex=60)
        assert redis_client.get("langfuse:test:ttl") == "ephemeral"
        ttl = redis_client.ttl("langfuse:test:ttl")
        assert 0 < ttl <= 60

    def test_incr(self, redis_client):
        """INCR on a key must atomically increment an integer value."""
        redis_client.set("langfuse:test:counter", 0)
        redis_client.incr("langfuse:test:counter")
        redis_client.incr("langfuse:test:counter")
        assert redis_client.get("langfuse:test:counter") == "2"

    def test_hash_operations(self, redis_client):
        """HSET/HGET must work for hash-based cache entries."""
        redis_client.hset("langfuse:test:hash", mapping={"field1": "val1", "field2": "val2"})
        assert redis_client.hget("langfuse:test:hash", "field1") == "val1"
        assert redis_client.hget("langfuse:test:hash", "field2") == "val2"

    def test_info_server(self, redis_client):
        """INFO server must return version info (Valkey identifies as redis-compatible)."""
        info = redis_client.info("server")
        # Valkey reports either 'redis_version' or 'valkey_version'
        assert "redis_version" in info or "valkey_version" in info


# ===================================================================
# 5. langfuse-clickhouse  (ClickHouse)
# ===================================================================
class TestLangfuseClickHouse:
    """Validate ClickHouse for Langfuse analytics/OLAP workloads.

    Mirrors the langfuse-clickhouse service from docker-compose:
      image: clickhouse/clickhouse-server
      Ports: 8123 (HTTP), 9000 (native)
      CLICKHOUSE_DB=default, CLICKHOUSE_USER=clickhouse,
      CLICKHOUSE_PASSWORD=clickhouse

    Uses the session-scoped ``clickhouse_container`` fixture from conftest.py.
    Each test drops and recreates its own table to avoid state leakage.
    """

    @pytest.fixture()
    def ch_http(self, clickhouse_container):
        """Return a helper to execute ClickHouse queries via HTTP interface."""
        from urllib.request import urlopen, Request
        from urllib.parse import urlencode

        host = clickhouse_container.get_container_host_ip()
        port = int(clickhouse_container.get_exposed_port(8123))
        base_url = f"http://{host}:{port}"

        def query(sql: str, *, fmt: str = "TabSeparated") -> str:
            """Execute a SQL query against the ClickHouse HTTP interface."""
            params = urlencode({
                "default_format": fmt,
                "user": "clickhouse",
                "password": "clickhouse",
            })
            url = f"{base_url}?{params}"
            req = Request(url, data=sql.encode("utf-8"), method="POST")
            with urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8").strip()

        return query

    def test_container_starts(self, clickhouse_container):
        """Container must be running and exposing mapped ports."""
        assert clickhouse_container.get_container_host_ip() is not None
        assert clickhouse_container.get_exposed_port(8123) is not None

    def test_select_one(self, ch_http):
        """SELECT 1 must return '1', proving HTTP interface works."""
        result = ch_http("SELECT 1")
        assert result == "1"

    def test_server_version(self, ch_http):
        """Server must report a ClickHouse version string."""
        version = ch_http("SELECT version()")
        assert len(version) > 0
        # ClickHouse versions look like "24.x.y.z"
        parts = version.split(".")
        assert len(parts) >= 2, f"Unexpected version format: {version}"

    def test_create_table_insert_query(self, ch_http):
        """Full DDL + DML cycle using MergeTree engine."""
        # Drop and recreate for a clean slate within the shared container.
        ch_http("DROP TABLE IF EXISTS langfuse_events")
        ch_http(
            """
            CREATE TABLE langfuse_events (
                event_id String,
                event_type String,
                value Float64,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (event_type, created_at)
            """
        )

        # Insert data
        ch_http(
            """
            INSERT INTO langfuse_events (event_id, event_type, value)
            VALUES ('evt-001', 'llm.completion', 0.42),
                   ('evt-002', 'llm.embedding', 0.78),
                   ('evt-003', 'llm.completion', 0.91)
            """
        )

        # Query and verify
        count = ch_http("SELECT count() FROM langfuse_events")
        assert int(count) == 3

        completion_count = ch_http(
            "SELECT count() FROM langfuse_events WHERE event_type = 'llm.completion'"
        )
        assert int(completion_count) == 2

        avg_value = ch_http(
            "SELECT round(avg(value), 2) FROM langfuse_events WHERE event_type = 'llm.completion'"
        )
        # (0.42 + 0.91) / 2 = 0.665; ClickHouse round() may yield 0.66 or 0.67
        assert abs(float(avg_value) - 0.665) < 0.02

        # Cleanup
        ch_http("DROP TABLE IF EXISTS langfuse_events")

    def test_system_databases(self, ch_http):
        """System databases must be present (system, default, information_schema)."""
        result = ch_http("SELECT name FROM system.databases ORDER BY name FORMAT TabSeparated")
        databases = result.split("\n")
        assert "default" in databases
        assert "system" in databases

    def test_user_exists(self, ch_http):
        """The 'clickhouse' user must exist."""
        result = ch_http("SELECT currentUser()")
        assert result == "clickhouse"
