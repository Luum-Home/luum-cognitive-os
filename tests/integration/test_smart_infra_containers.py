"""Integration tests for Smart Infrastructure using Testcontainers.

Tests real Docker container lifecycle: start, health check, stop, idle timeout.
Uses lightweight nginx containers as stand-ins for real services.
"""

import json
import os
import subprocess
import time
import tempfile
import textwrap
from pathlib import Path

import pytest

try:
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    tc_available = True
except ImportError:
    tc_available = False

from lib.smart_infra import SmartInfra, SERVICE_COMPOSE_MAP

pytestmark = [
    pytest.mark.docker,
    pytest.mark.slow,
    pytest.mark.skipif(not tc_available, reason="testcontainers not installed"),
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_SERVICE = "test-web"
_TEST_CONTAINER = "cos-test-nginx"
_TEST_PORT = 18080

_COMPOSE_YAML = textwrap.dedent(
    """\
    services:
      test-web:
        image: nginx:alpine
        container_name: cos-test-nginx
        healthcheck:
          test: ["CMD", "wget", "-q", "--spider", "http://localhost:80/"]
          interval: 3s
          timeout: 2s
          retries: 3
          start_period: 2s
        ports:
          - "18080:80"
    """
)

_CONFIG_YAML = textwrap.dedent(
    """\
    resources:
      infrastructure:
        smart_start: true
        services:
          test-web:
            mode: on_demand
            idle_timeout_minutes: 1
    """
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_compose_env(tmp_path, docker_available):
    """Create a minimal test environment with compose file, config, and SmartInfra."""

    # Write compose file.
    compose_file = tmp_path / "docker-compose.cognitive-os.yml"
    compose_file.write_text(_COMPOSE_YAML)

    # Write config.
    config_file = tmp_path / "cognitive-os.yaml"
    config_file.write_text(_CONFIG_YAML)

    # Create metrics directory.
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # Monkey-patch SERVICE_COMPOSE_MAP to include our test service.
    original_map = dict(SERVICE_COMPOSE_MAP)
    SERVICE_COMPOSE_MAP[_TEST_SERVICE] = {
        "compose_services": ["test-web"],
        "health_container": _TEST_CONTAINER,
        "profile": None,
    }

    # Build SmartInfra instance pointing at the temp env.
    infra = SmartInfra(
        project_dir=str(tmp_path),
        compose_file=str(compose_file),
        config_file=str(config_file),
    )

    yield infra

    # Teardown: stop containers and restore SERVICE_COMPOSE_MAP.
    try:
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "down",
                "-v",
                "--remove-orphans",
            ],
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass

    # Restore original map.
    SERVICE_COMPOSE_MAP.clear()
    SERVICE_COMPOSE_MAP.update(original_map)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSmartInfraContainers:
    """Integration tests validating SmartInfra with real Docker containers."""

    def test_ensure_starts_container(self, test_compose_env):
        """ensure_service should start a container and report it healthy."""
        infra = test_compose_env

        # Service should NOT be running initially.
        assert not infra.is_service_running(_TEST_SERVICE)

        # Start it.
        result = infra.ensure_service(_TEST_SERVICE, timeout_secs=60)
        assert result is True

        # Verify it is running and healthy.
        assert infra.is_service_running(_TEST_SERVICE)
        assert infra.is_service_healthy(_TEST_SERVICE)

    def test_ensure_idempotent(self, test_compose_env):
        """Calling ensure_service twice should succeed both times; second is faster."""
        infra = test_compose_env

        t0 = time.monotonic()
        first = infra.ensure_service(_TEST_SERVICE, timeout_secs=60)
        first_duration = time.monotonic() - t0

        t1 = time.monotonic()
        second = infra.ensure_service(_TEST_SERVICE, timeout_secs=60)
        second_duration = time.monotonic() - t1

        assert first is True
        assert second is True
        # The second call should be significantly faster (fast-path: already healthy).
        assert second_duration < first_duration

    def test_stop_service(self, test_compose_env):
        """stop_service should bring the container down."""
        infra = test_compose_env

        assert infra.ensure_service(_TEST_SERVICE, timeout_secs=60)
        assert infra.is_service_running(_TEST_SERVICE)

        result = infra.stop_service(_TEST_SERVICE)
        assert result is True

        # Give Docker a moment to tear down.
        time.sleep(2)
        assert not infra.is_service_running(_TEST_SERVICE)

    def test_is_service_running_reflects_state(self, test_compose_env):
        """is_service_running should accurately reflect container state transitions."""
        infra = test_compose_env

        # Before start.
        assert not infra.is_service_running(_TEST_SERVICE)

        # After start.
        infra.ensure_service(_TEST_SERVICE, timeout_secs=60)
        assert infra.is_service_running(_TEST_SERVICE)

        # After stop.
        infra.stop_service(_TEST_SERVICE)
        time.sleep(2)
        assert not infra.is_service_running(_TEST_SERVICE)

    def test_idle_timeout_stops_service(self, test_compose_env):
        """stop_idle_services should stop services whose last access exceeds the timeout."""
        infra = test_compose_env

        assert infra.ensure_service(_TEST_SERVICE, timeout_secs=60)

        # Manually set last access to 2 minutes ago (config idle timeout = 1 min).
        infra._last_access[_TEST_SERVICE] = time.time() - 120

        stopped = infra.stop_idle_services()

        assert _TEST_SERVICE in stopped
        time.sleep(2)
        assert not infra.is_service_running(_TEST_SERVICE)

    def test_metrics_logged(self, test_compose_env):
        """ensure_service should write a start event to infra-usage.jsonl."""
        infra = test_compose_env

        assert infra.ensure_service(_TEST_SERVICE, timeout_secs=60)

        log_path = Path(infra._project_dir) / ".cognitive-os" / "metrics" / "infra-usage.jsonl"
        assert log_path.exists(), "infra-usage.jsonl should exist after ensure_service"

        events = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
        start_events = [
            e for e in events if e.get("container") == _TEST_SERVICE and e.get("event") == "start"
        ]

        assert len(start_events) >= 1, f"Expected at least 1 start event, got {len(start_events)}"

    def test_status_reflects_running(self, test_compose_env):
        """status() should reflect whether the test service is running and healthy."""
        infra = test_compose_env

        # Before start: not running.
        status_before = infra.status()
        assert _TEST_SERVICE in status_before
        assert status_before[_TEST_SERVICE]["running"] is False
        assert status_before[_TEST_SERVICE]["healthy"] is False

        # After start: running and healthy.
        infra.ensure_service(_TEST_SERVICE, timeout_secs=60)
        status_after = infra.status()
        assert status_after[_TEST_SERVICE]["running"] is True
        assert status_after[_TEST_SERVICE]["healthy"] is True
