"""Unit tests for Smart Infrastructure — lazy Docker service loading."""

import json
import os
import time
from unittest.mock import MagicMock, patch, call
import pytest

from lib.smart_infra import (
    SmartInfra,
    SKILL_SERVICE_MAP,
    SERVICE_COMPOSE_MAP,
    NON_DOCKER_SERVICE_NAMES,
    requires_service,
)

# Mark all tests as unit
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def smart_infra(tmp_path):
    """Create SmartInfra with mocked Docker and temp directories."""
    config = tmp_path / "cognitive-os.yaml"
    config.write_text(
        "resources:\n"
        "  infrastructure:\n"
        "    services:\n"
        "      litellm:\n"
        "        mode: always\n"
        "      paperclip:\n"
        "        mode: on_demand\n"
        "        idle_timeout_minutes: 30\n"
        "      mlflow:\n"
        "        mode: pip\n"
    )

    cos_dir = tmp_path / ".cognitive-os" / "metrics"
    cos_dir.mkdir(parents=True)

    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3'\nservices: {}\n")

    with patch.object(SmartInfra, "_is_docker_available", return_value=True):
        si = SmartInfra(
            project_dir=str(tmp_path),
            compose_file=str(compose_file),
            config_file=str(config),
        )
    return si


# ---------------------------------------------------------------------------
# TestSkillServiceMap
# ---------------------------------------------------------------------------


class TestSkillServiceMap:
    """Tests for SKILL_SERVICE_MAP constants."""

    def test_known_skill_returns_services(self):
        assert SKILL_SERVICE_MAP["agent-kpis"] == ["mlflow"]

    def test_unknown_skill_returns_empty(self):
        assert SKILL_SERVICE_MAP.get("nonexistent", []) == []

    def test_sdd_skills_need_litellm(self):
        assert "litellm" in SKILL_SERVICE_MAP["sdd-apply"]
        assert "litellm" in SKILL_SERVICE_MAP["sdd-verify"]

    def test_all_mapped_services_exist_in_compose_map(self):
        """Every mapped service must be a Docker service or an explicit non-Docker service."""
        for skill, services in SKILL_SERVICE_MAP.items():
            for svc in services:
                assert svc in SERVICE_COMPOSE_MAP or svc in NON_DOCKER_SERVICE_NAMES, (
                    f"Skill '{skill}' references service '{svc}' "
                    "not found in SERVICE_COMPOSE_MAP or NON_DOCKER_SERVICE_NAMES"
                )


# ---------------------------------------------------------------------------
# TestServiceComposeMap
# ---------------------------------------------------------------------------


class TestServiceComposeMap:
    """Tests for SERVICE_COMPOSE_MAP constants."""

    def test_all_services_have_required_keys(self):
        required_keys = {"compose_services", "health_container", "profile"}
        for svc_name, info in SERVICE_COMPOSE_MAP.items():
            for key in required_keys:
                assert key in info, f"Service '{svc_name}' missing key '{key}'"

    def test_profiled_services(self):
        # ADR-060 (2026-04-24): opik removed per local-only policy
        # (was mode:cloud; Phoenix covers observability locally via pip).
        assert SERVICE_COMPOSE_MAP["memu"]["profile"] == "memory"
        assert SERVICE_COMPOSE_MAP["cognee"]["profile"] == "memory"

    def test_default_profile_services(self):
        assert SERVICE_COMPOSE_MAP["litellm"]["profile"] is None
        # ADR-058: the former observability trace-UI entry was removed from the
        # service map; paperclip is a representative default-profile service.
        assert SERVICE_COMPOSE_MAP["paperclip"]["profile"] is None


# ---------------------------------------------------------------------------
# TestDockerAvailability
# ---------------------------------------------------------------------------


class TestDockerAvailability:
    """Tests for SmartInfra._is_docker_available()."""

    def test_docker_not_installed(self):
        si = SmartInfra()
        with patch("shutil.which", return_value=None):
            assert si._is_docker_available() is False

    def test_docker_daemon_not_running(self):
        si = SmartInfra()
        with patch("shutil.which", return_value="/usr/bin/docker"):
            mock_result = MagicMock()
            mock_result.returncode = 1
            with patch("subprocess.run", return_value=mock_result):
                assert si._is_docker_available() is False

    def test_docker_available(self):
        si = SmartInfra()
        with patch("shutil.which", return_value="/usr/bin/docker"):
            mock_result = MagicMock()
            mock_result.returncode = 0
            with patch("subprocess.run", return_value=mock_result):
                assert si._is_docker_available() is True

    def test_docker_check_cached(self):
        si = SmartInfra()
        with patch("shutil.which", return_value="/usr/bin/docker"):
            mock_result = MagicMock()
            mock_result.returncode = 0
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                si._is_docker_available()
                si._is_docker_available()
                # subprocess.run should only be called once (cached)
                assert mock_run.call_count == 1


# ---------------------------------------------------------------------------
# TestServiceConfig
# ---------------------------------------------------------------------------


class TestServiceConfig:
    """Tests for SmartInfra._get_service_config()."""

    def test_loads_config_from_yaml(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "resources:\n"
            "  infrastructure:\n"
            "    services:\n"
            "      paperclip:\n"
            "        mode: on_demand\n"
            "        idle_timeout_minutes: 45\n"
        )
        si = SmartInfra(project_dir=str(tmp_path), config_file=str(config))
        cfg = si._get_service_config("paperclip")
        assert cfg["mode"] == "on_demand"
        assert cfg["idle_timeout_minutes"] == 45

    def test_default_config_when_missing(self, tmp_path):
        si = SmartInfra(
            project_dir=str(tmp_path),
            config_file=str(tmp_path / "nonexistent.yaml"),
        )
        cfg = si._get_service_config("paperclip")
        assert cfg["mode"] == "on_demand"
        assert cfg["idle_timeout_minutes"] == 30

    def test_underscore_hyphen_normalization(self, tmp_path):
        config = tmp_path / "cognitive-os.yaml"
        config.write_text(
            "resources:\n"
            "  infrastructure:\n"
            "    services:\n"
            "      nemo_guardrails:\n"
            "        mode: on_demand\n"
            "        idle_timeout_minutes: 15\n"
        )
        si = SmartInfra(project_dir=str(tmp_path), config_file=str(config))
        cfg = si._get_service_config("nemo-guardrails")
        assert cfg["mode"] == "on_demand"
        assert cfg["idle_timeout_minutes"] == 15


# ---------------------------------------------------------------------------
# TestIsServiceRunning
# ---------------------------------------------------------------------------


class TestIsServiceRunning:
    """Tests for SmartInfra.is_service_running() with mocked subprocess."""

    def test_running_returns_true(self, smart_infra):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "running\n"
        with patch("subprocess.run", return_value=mock_result):
            assert smart_infra.is_service_running("paperclip") is True

    def test_exited_returns_false(self, smart_infra):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "exited\n"
        with patch("subprocess.run", return_value=mock_result):
            assert smart_infra.is_service_running("paperclip") is False

    def test_missing_container_returns_false(self, smart_infra):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            assert smart_infra.is_service_running("paperclip") is False


# ---------------------------------------------------------------------------
# TestIsServiceHealthy
# ---------------------------------------------------------------------------


class TestIsServiceHealthy:
    """Tests for SmartInfra.is_service_healthy() with mocked subprocess."""

    def test_healthy_returns_true(self, smart_infra):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "healthy\n"
        with patch("subprocess.run", return_value=mock_result):
            assert smart_infra.is_service_healthy("paperclip") is True

    def test_unhealthy_returns_false(self, smart_infra):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "unhealthy\n"
        with patch("subprocess.run", return_value=mock_result):
            assert smart_infra.is_service_healthy("paperclip") is False

    def test_no_healthcheck_returns_true(self, smart_infra):
        """When container has no healthcheck, falls back to running check."""
        # First call returns "none" (no healthcheck), second checks running state.
        health_result = MagicMock()
        health_result.returncode = 0
        health_result.stdout = "none\n"

        running_result = MagicMock()
        running_result.returncode = 0
        running_result.stdout = "running\n"

        with patch("subprocess.run", side_effect=[health_result, running_result]):
            assert smart_infra.is_service_healthy("paperclip") is True


# ---------------------------------------------------------------------------
# TestEnsureService
# ---------------------------------------------------------------------------


class TestEnsureService:
    """Tests for SmartInfra.ensure_service() with mocked subprocess."""

    def test_already_running_skips_compose_up(self, smart_infra):
        with patch.object(smart_infra, "_is_docker_available", return_value=True), \
             patch.object(smart_infra, "is_service_running", return_value=True), \
             patch.object(smart_infra, "is_service_healthy", return_value=True), \
             patch("subprocess.run") as mock_run:
            result = smart_infra.ensure_service("paperclip")
            assert result is True
            mock_run.assert_not_called()

    def test_starts_when_not_running(self, smart_infra):
        compose_result = MagicMock()
        compose_result.returncode = 0
        compose_result.stderr = ""

        with patch.object(smart_infra, "_is_docker_available", return_value=True), \
             patch.object(smart_infra, "is_service_running", return_value=False), \
             patch.object(smart_infra, "is_service_healthy", side_effect=[False, True]), \
             patch("subprocess.run", return_value=compose_result), \
             patch("time.sleep"):
            result = smart_infra.ensure_service("paperclip", timeout_secs=10)
            assert result is True

    def test_includes_profile_for_memu(self, smart_infra):
        compose_result = MagicMock()
        compose_result.returncode = 0
        compose_result.stderr = ""

        with patch.object(smart_infra, "_is_docker_available", return_value=True), \
             patch.object(smart_infra, "is_service_running", return_value=False), \
             patch.object(smart_infra, "is_service_healthy", side_effect=[False, True]), \
             patch("subprocess.run", return_value=compose_result) as mock_run, \
             patch("time.sleep"):
            smart_infra.ensure_service("memu", timeout_secs=10)
            # Verify the compose command includes --profile memory
            cmd = mock_run.call_args[0][0]
            assert "--profile" in cmd
            assert "memory" in cmd

    def test_timeout_returns_false(self, smart_infra):
        compose_result = MagicMock()
        compose_result.returncode = 0
        compose_result.stderr = ""

        with patch.object(smart_infra, "_is_docker_available", return_value=True), \
             patch.object(smart_infra, "is_service_running", return_value=False), \
             patch.object(smart_infra, "is_service_healthy", return_value=False), \
             patch("subprocess.run", return_value=compose_result), \
             patch("time.sleep"):
            result = smart_infra.ensure_service("paperclip", timeout_secs=1)
            assert result is False

    def test_no_docker_returns_false(self, smart_infra):
        with patch.object(smart_infra, "_is_docker_available", return_value=False):
            result = smart_infra.ensure_service("paperclip")
            assert result is False

    def test_pip_service_does_not_start_docker(self, smart_infra):
        with patch("subprocess.run") as mock_run:
            result = smart_infra.ensure_service("mlflow")
            assert result is True
            assert "mlflow" in smart_infra._last_access
            mock_run.assert_not_called()

    def test_unknown_service_returns_false(self, smart_infra):
        with patch.object(smart_infra, "_is_docker_available", return_value=True):
            result = smart_infra.ensure_service("nonexistent")
            assert result is False

    def test_updates_last_access(self, smart_infra):
        with patch.object(smart_infra, "_is_docker_available", return_value=True), \
             patch.object(smart_infra, "is_service_running", return_value=True), \
             patch.object(smart_infra, "is_service_healthy", return_value=True):
            smart_infra.ensure_service("paperclip")
            assert "paperclip" in smart_infra._last_access
            assert smart_infra._last_access["paperclip"] > 0

    def test_logs_event_to_metrics(self, smart_infra, tmp_path):
        compose_result = MagicMock()
        compose_result.returncode = 0
        compose_result.stderr = ""

        with patch.object(smart_infra, "_is_docker_available", return_value=True), \
             patch.object(smart_infra, "is_service_running", return_value=False), \
             patch.object(smart_infra, "is_service_healthy", side_effect=[False, True]), \
             patch("subprocess.run", return_value=compose_result), \
             patch("time.sleep"):
            smart_infra.ensure_service("paperclip", timeout_secs=10)

        log_path = tmp_path / ".cognitive-os" / "metrics" / "infra-usage.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert entry["container"] == "paperclip"
        assert entry["event"] == "start"


# ---------------------------------------------------------------------------
# TestStopIdleServices
# ---------------------------------------------------------------------------


class TestStopIdleServices:
    """Tests for SmartInfra.stop_idle_services()."""

    def test_stops_past_timeout(self, smart_infra):
        # Set last access 31 minutes ago (timeout is 30 min for paperclip).
        smart_infra._last_access["paperclip"] = time.time() - 31 * 60

        with patch.object(smart_infra, "stop_service", return_value=True) as mock_stop:
            stopped = smart_infra.stop_idle_services()
            assert "paperclip" in stopped
            mock_stop.assert_called_with("paperclip")

    def test_keeps_within_timeout(self, smart_infra):
        # Set last access 5 minutes ago.
        smart_infra._last_access["paperclip"] = time.time() - 5 * 60

        with patch.object(smart_infra, "stop_service") as mock_stop:
            stopped = smart_infra.stop_idle_services()
            assert stopped == []
            mock_stop.assert_not_called()

    def test_always_mode_never_stopped(self, smart_infra):
        # litellm has mode=always in the test config.
        smart_infra._last_access["litellm"] = time.time() - 120 * 60

        with patch.object(smart_infra, "stop_service") as mock_stop:
            stopped = smart_infra.stop_idle_services()
            assert "litellm" not in stopped
            mock_stop.assert_not_called()

    def test_returns_stopped_list(self, smart_infra):
        smart_infra._last_access["paperclip"] = time.time() - 31 * 60

        with patch.object(smart_infra, "stop_service", return_value=True):
            stopped = smart_infra.stop_idle_services()
            assert stopped == ["paperclip"]


# ---------------------------------------------------------------------------
# TestRequiresServiceDecorator
# ---------------------------------------------------------------------------


class TestRequiresServiceDecorator:
    """Tests for the @requires_service decorator."""

    def test_calls_ensure_service(self):
        with patch("lib.smart_infra.ensure_service") as mock_ensure:

            @requires_service("paperclip")
            def my_func():
                return "ok"

            result = my_func()
            assert result == "ok"
            mock_ensure.assert_called_once_with("paperclip")

    def test_function_runs_on_ensure_failure(self):
        with patch("lib.smart_infra.ensure_service", side_effect=Exception("boom")):

            @requires_service("paperclip")
            def my_func():
                return "still ok"

            result = my_func()
            assert result == "still ok"

    def test_multiple_services(self):
        with patch("lib.smart_infra.ensure_service") as mock_ensure:

            @requires_service("paperclip", "litellm")
            def my_func():
                return "ok"

            my_func()
            assert mock_ensure.call_count == 2
            mock_ensure.assert_any_call("paperclip")
            mock_ensure.assert_any_call("litellm")


# ---------------------------------------------------------------------------
# TestEnsureForSkill
# ---------------------------------------------------------------------------


class TestEnsureForSkill:
    """Tests for SmartInfra.ensure_for_skill()."""

    def test_maps_skill_to_services(self, smart_infra):
        with patch.object(smart_infra, "ensure_service", return_value=True) as mock_ensure:
            results = smart_infra.ensure_for_skill("agent-kpis")
            assert results == {"mlflow": True}
            mock_ensure.assert_called_once_with("mlflow", timeout_secs=120)

    def test_unknown_skill_returns_empty(self, smart_infra):
        results = smart_infra.ensure_for_skill("nonexistent-skill")
        assert results == {}


# ---------------------------------------------------------------------------
# TestFormatStatus
# ---------------------------------------------------------------------------


class TestValkeyServiceMapping:
    """Tests for Valkey service in smart_infra maps."""

    def test_valkey_in_compose_map(self):
        """Valkey service must be registered in SERVICE_COMPOSE_MAP."""
        assert "valkey" in SERVICE_COMPOSE_MAP
        info = SERVICE_COMPOSE_MAP["valkey"]
        assert info["compose_services"] == ["valkey"]
        assert info["health_container"] == "cognitive-os-valkey"
        assert info["profile"] is None

    def test_agent_bus_maps_to_valkey(self):
        """agent-bus skill must map to valkey service."""
        assert "agent-bus" in SKILL_SERVICE_MAP
        assert SKILL_SERVICE_MAP["agent-bus"] == ["valkey"]

    def test_agent_communication_maps_to_valkey(self):
        """agent-communication skill must map to valkey service."""
        assert "agent-communication" in SKILL_SERVICE_MAP
        assert SKILL_SERVICE_MAP["agent-communication"] == ["valkey"]

    def test_ensure_for_skill_agent_bus(self, smart_infra):
        """ensure_for_skill('agent-bus') triggers valkey service."""
        with patch.object(smart_infra, "ensure_service", return_value=True) as mock_es:
            results = smart_infra.ensure_for_skill("agent-bus")
            mock_es.assert_called_once_with("valkey", timeout_secs=120)
            assert results == {"valkey": True}


class TestFormatStatus:
    """Tests for SmartInfra.format_status()."""

    def test_format_includes_all_services(self, smart_infra):
        with patch.object(smart_infra, "_is_docker_available", return_value=False):
            output = smart_infra.format_status()
            for svc_name in SERVICE_COMPOSE_MAP:
                assert svc_name in output
