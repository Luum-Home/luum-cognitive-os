# SCOPE: both
"""Smart Infrastructure — Lazy Docker service lifecycle management.

Manages on-demand startup, health polling, and idle shutdown of Docker
services used by Cognitive OS skills and hooks. Services are started only
when a skill that requires them is invoked, and stopped after an
idle timeout.

Usage:
    from lib.smart_infra import ensure_service, ensure_for_skill, stop_idle_services

    # Ensure a single service is running
    ok = ensure_service("langfuse")

    # Ensure all services required by a skill
    results = ensure_for_skill("agent-kpis")  # {"langfuse": True}

    # Stop services that have been idle past their timeout
    stopped = stop_idle_services()

    # Decorator for functions that need a service
    from lib.smart_infra import requires_service

    @requires_service("langfuse", "litellm")
    def my_function():
        ...

Python 3.9+ compatible. stdlib + PyYAML only. Author: luum.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skill-to-service mapping
# ---------------------------------------------------------------------------

SKILL_SERVICE_MAP: Dict[str, List[str]] = {
    "agent-kpis": ["langfuse"],
    "observability": ["langfuse"],
    "observability-trace": ["langfuse"],
    "sdd-pipeline": ["litellm"],
    "sdd-apply": ["litellm"],
    "sdd-verify": ["litellm"],
    "multi-model": ["litellm"],
    "model-routing": ["litellm"],
    "content-filtering": ["nemo-guardrails"],
    "guardrails": ["nemo-guardrails"],
    "pii-detection": ["nemo-guardrails"],
    "squad-report": ["paperclip"],
    "governance": ["paperclip"],
    "paperclip-sync": ["paperclip"],
    "memory-sync": ["memu"],
    "knowledge-graph": ["cognee"],
    "cognee-search": ["cognee"],
    "jupyter": ["jupyter"],
    "opik": ["opik"],
    "automaker": ["automaker"],
    "webhook-trigger": ["webhook-trigger"],
    "agent-bus": ["valkey"],
    "agent-communication": ["valkey"],
}


# ---------------------------------------------------------------------------
# Service-to-compose mapping
# ---------------------------------------------------------------------------

SERVICE_COMPOSE_MAP: Dict[str, Dict[str, Any]] = {
    "langfuse": {
        "compose_services": ["langfuse-web"],
        "health_container": "cognitive-os-langfuse",
        "profile": None,
    },
    "litellm": {
        "compose_services": ["litellm"],
        "health_container": "cognitive-os-litellm",
        "profile": None,
    },
    "nemo-guardrails": {
        "compose_services": ["nemo-guardrails"],
        "health_container": "cognitive-os-nemo-guardrails",
        "profile": None,
    },
    "paperclip": {
        "compose_services": ["paperclip"],
        "health_container": "cognitive-os-paperclip",
        "profile": None,
    },
    "memu": {
        "compose_services": ["memu"],
        "health_container": "cognitive-os-memu",
        "profile": "memory",
    },
    "cognee": {
        "compose_services": ["cognee"],
        "health_container": "cognitive-os-cognee",
        "profile": "memory",
    },
    "jupyter": {
        "compose_services": ["jupyter"],
        "health_container": "cognitive-os-jupyter",
        "profile": None,
    },
    "opik": {
        "compose_services": ["opik-backend"],
        "health_container": "cognitive-os-opik-backend",
        "profile": "observability",
    },
    "automaker": {
        "compose_services": ["automaker"],
        "health_container": "cognitive-os-automaker",
        "profile": "ui",
    },
    "webhook-trigger": {
        "compose_services": ["webhook-trigger"],
        "health_container": "cognitive-os-webhook-trigger",
        "profile": "automation",
    },
    "valkey": {
        "compose_services": ["valkey"],
        "health_container": "cognitive-os-valkey",
        "profile": None,
    },
}


# Default idle timeout when not specified in config (minutes).
_DEFAULT_IDLE_TIMEOUT_MINUTES = 30

# Default service mode when not specified in config.
_DEFAULT_SERVICE_MODE = "on_demand"


# ---------------------------------------------------------------------------
# SmartInfra class
# ---------------------------------------------------------------------------


class SmartInfra:
    """Manages lazy Docker service lifecycle.

    Services are started on demand when a skill or hook requires them,
    health-checked before use, and stopped after an idle timeout.
    """

    def __init__(
        self,
        project_dir: Optional[str] = None,
        compose_file: Optional[str] = None,
        config_file: Optional[str] = None,
    ) -> None:
        self._project_dir = project_dir or os.environ.get(
            "COGNITIVE_OS_PROJECT_DIR", os.getcwd()
        )
        self._compose_file = compose_file
        self._config_file = config_file
        self._config: Optional[Dict[str, Any]] = None
        self._last_access: Dict[str, float] = {}
        self._docker_available: Optional[bool] = None

    # -- Docker availability ------------------------------------------------

    def _is_docker_available(self) -> bool:
        """Check whether Docker CLI is installed and the daemon is reachable.

        The result is cached for the lifetime of this instance.
        """
        if self._docker_available is not None:
            return self._docker_available

        if shutil.which("docker") is None:
            logger.info("Docker CLI not found in PATH")
            self._docker_available = False
            return False

        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10,
            )
            self._docker_available = result.returncode == 0
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.info("Docker daemon not reachable: %s", exc)
            self._docker_available = False

        return self._docker_available

    # -- Configuration ------------------------------------------------------

    def _load_config(self) -> Dict[str, Any]:
        """Load the ``resources.infrastructure`` section from cognitive-os.yaml.

        Returns an empty dict on any failure (file missing, parse error, etc.).
        """
        if self._config is not None:
            return self._config

        config_path = self._config_file or os.path.join(
            self._project_dir, "cognitive-os.yaml"
        )

        try:
            import yaml  # type: ignore[import-untyped]

            with open(config_path, "r") as fh:
                data = yaml.safe_load(fh) or {}
            self._config = (
                data.get("resources", {}).get("infrastructure", {})
            )
        except FileNotFoundError:
            logger.debug("cognitive-os.yaml not found at %s", config_path)
            self._config = {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse cognitive-os.yaml: %s", exc)
            self._config = {}

        return self._config

    def _get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Return per-service config with defaults applied.

        Keys returned: ``mode``, ``idle_timeout_minutes``.
        """
        cfg = self._load_config()
        services = cfg.get("services", {})

        # Config may use underscores (nemo_guardrails) while maps use hyphens.
        svc_cfg = services.get(service_name) or services.get(
            service_name.replace("-", "_"), {}
        )

        if svc_cfg is None:
            svc_cfg = {}

        return {
            "mode": svc_cfg.get("mode", _DEFAULT_SERVICE_MODE),
            "idle_timeout_minutes": svc_cfg.get(
                "idle_timeout_minutes", _DEFAULT_IDLE_TIMEOUT_MINUTES
            ),
        }

    def _get_compose_file_path(self) -> str:
        """Return the absolute path to docker-compose.cognitive-os.yml."""
        if self._compose_file:
            return self._compose_file
        return os.path.join(self._project_dir, "docker-compose.cognitive-os.yml")

    # -- Service status -----------------------------------------------------

    def is_service_running(self, service_name: str) -> bool:
        """Return True if the service container reports status ``running``."""
        compose_info = SERVICE_COMPOSE_MAP.get(service_name)
        if not compose_info:
            return False

        container = compose_info["health_container"]

        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Status}}",
                    container,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and result.stdout.strip() == "running"
        except (subprocess.TimeoutExpired, OSError):
            return False

    def is_service_healthy(self, service_name: str) -> bool:
        """Return True if the service container is healthy.

        If the container has no healthcheck configured, being in ``running``
        state is considered healthy.
        """
        compose_info = SERVICE_COMPOSE_MAP.get(service_name)
        if not compose_info:
            return False

        container = compose_info["health_container"]

        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
                    container,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return False

            health = result.stdout.strip()
            if health == "none":
                # No healthcheck defined — fall back to running check.
                return self.is_service_running(service_name)
            return health == "healthy"
        except (subprocess.TimeoutExpired, OSError):
            return False

    # -- Service lifecycle --------------------------------------------------

    def ensure_service(
        self, service_name: str, timeout_secs: int = 120
    ) -> bool:
        """Ensure that *service_name* is running and healthy.

        Starts the service via ``docker compose up -d`` if it is not already
        running, then polls for health up to *timeout_secs*.

        Returns True on success, False on failure.  Never raises.
        """
        if not self._is_docker_available():
            logger.warning(
                "Docker not available — cannot ensure service %s", service_name
            )
            return False

        if service_name not in SERVICE_COMPOSE_MAP:
            logger.warning("Unknown service: %s", service_name)
            return False

        # Already running and healthy — fast path.
        if self.is_service_running(service_name) and self.is_service_healthy(
            service_name
        ):
            self._last_access[service_name] = time.time()
            return True

        compose_info = SERVICE_COMPOSE_MAP[service_name]
        compose_file = self._get_compose_file_path()

        if not os.path.isfile(compose_file):
            logger.warning("Compose file not found: %s", compose_file)
            return False

        # Build the docker compose command.
        cmd: List[str] = [
            "docker",
            "compose",
            "-f",
            compose_file,
        ]

        profile = compose_info.get("profile")
        if profile:
            cmd.extend(["--profile", profile])

        cmd.extend(["up", "-d"])
        cmd.extend(compose_info["compose_services"])

        logger.info("Starting service %s: %s", service_name, " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning(
                    "docker compose up failed for %s: %s",
                    service_name,
                    result.stderr.strip(),
                )
                self._log_event("start_failed", service_name, error=result.stderr.strip())
                return False
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Failed to start service %s: %s", service_name, exc)
            self._log_event("start_failed", service_name, error=str(exc))
            return False

        # Poll for health.
        poll_interval = 3
        elapsed = 0.0
        while elapsed < timeout_secs:
            if self.is_service_healthy(service_name):
                self._last_access[service_name] = time.time()
                self._log_event("start", service_name, reason="on_demand")
                logger.info("Service %s is healthy", service_name)
                return True
            time.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(
            "Service %s did not become healthy within %ds",
            service_name,
            timeout_secs,
        )
        self._log_event(
            "start_timeout",
            service_name,
            timeout_secs=timeout_secs,
        )
        return False

    def stop_service(self, service_name: str) -> bool:
        """Stop *service_name* via ``docker compose stop``.

        Returns True if the stop command succeeded.
        """
        if not self._is_docker_available():
            return False

        compose_info = SERVICE_COMPOSE_MAP.get(service_name)
        if not compose_info:
            logger.warning("Unknown service: %s", service_name)
            return False

        compose_file = self._get_compose_file_path()
        if not os.path.isfile(compose_file):
            return False

        cmd: List[str] = [
            "docker",
            "compose",
            "-f",
            compose_file,
        ]

        profile = compose_info.get("profile")
        if profile:
            cmd.extend(["--profile", profile])

        cmd.extend(["stop"])
        cmd.extend(compose_info["compose_services"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                self._last_access.pop(service_name, None)
                self._log_event("stop", service_name, reason="explicit")
                logger.info("Stopped service %s", service_name)
                return True
            logger.warning(
                "docker compose stop failed for %s: %s",
                service_name,
                result.stderr.strip(),
            )
            return False
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Failed to stop service %s: %s", service_name, exc)
            return False

    def stop_idle_services(self) -> List[str]:
        """Stop services that have been idle past their configured timeout.

        Services with ``mode: always`` are never stopped.

        Returns a list of service names that were stopped.
        """
        stopped: List[str] = []
        now = time.time()

        for service_name, last_ts in list(self._last_access.items()):
            svc_cfg = self._get_service_config(service_name)

            # Never auto-stop services marked as "always".
            if svc_cfg["mode"] == "always":
                continue

            idle_timeout_secs = svc_cfg["idle_timeout_minutes"] * 60
            if now - last_ts >= idle_timeout_secs:
                if self.stop_service(service_name):
                    self._log_event(
                        "stop",
                        service_name,
                        reason="idle_timeout",
                        idle_minutes=round((now - last_ts) / 60, 1),
                    )
                    stopped.append(service_name)

        return stopped

    # -- Skill integration --------------------------------------------------

    def get_required_services(self, skill_name: str) -> List[str]:
        """Return the list of Docker services required by *skill_name*.

        Checks the ``resources.infrastructure.skill_service_map`` config key
        first, then falls back to the built-in ``SKILL_SERVICE_MAP``.
        """
        cfg = self._load_config()
        config_map = cfg.get("skill_service_map", {})

        if skill_name in config_map:
            val = config_map[skill_name]
            if isinstance(val, list):
                return val
            return [val]

        return list(SKILL_SERVICE_MAP.get(skill_name, []))

    def ensure_for_skill(
        self, skill_name: str, timeout_secs: int = 120
    ) -> Dict[str, bool]:
        """Ensure all Docker services required by *skill_name* are running.

        Returns a dict mapping each required service to its start result.
        An empty dict is returned when the skill has no service requirements.
        """
        services = self.get_required_services(skill_name)
        results: Dict[str, bool] = {}
        for svc in services:
            results[svc] = self.ensure_service(svc, timeout_secs=timeout_secs)
        return results

    # -- Metrics logging ----------------------------------------------------

    def _log_event(self, event: str, service: str, **details: Any) -> None:
        """Append a JSONL entry to ``.cognitive-os/metrics/infra-usage.jsonl``."""
        metrics_dir = os.path.join(self._project_dir, ".cognitive-os", "metrics")
        log_path = os.path.join(metrics_dir, "infra-usage.jsonl")

        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "container": service,
            "event": event,
        }
        entry.update(details)

        try:
            os.makedirs(metrics_dir, exist_ok=True)
            with open(log_path, "a") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # Best effort — never crash on I/O failure.

    # -- Status report ------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return a status dict for all configured services.

        Each service entry contains: ``running``, ``healthy``,
        ``last_access`` (ISO timestamp or None), ``idle_remaining_minutes``
        (minutes until idle timeout, or None).
        """
        now = time.time()
        result: Dict[str, Any] = {}

        for service_name in SERVICE_COMPOSE_MAP:
            svc_cfg = self._get_service_config(service_name)
            running = self.is_service_running(service_name) if self._is_docker_available() else False
            healthy = self.is_service_healthy(service_name) if self._is_docker_available() else False

            last_access_ts = self._last_access.get(service_name)
            last_access_iso: Optional[str] = None
            idle_remaining: Optional[float] = None

            if last_access_ts is not None:
                last_access_iso = datetime.fromtimestamp(
                    last_access_ts, tz=timezone.utc
                ).isoformat()

                if svc_cfg["mode"] != "always":
                    timeout_secs = svc_cfg["idle_timeout_minutes"] * 60
                    remaining = timeout_secs - (now - last_access_ts)
                    idle_remaining = round(max(0.0, remaining) / 60, 1)

            result[service_name] = {
                "running": running,
                "healthy": healthy,
                "mode": svc_cfg["mode"],
                "last_access": last_access_iso,
                "idle_remaining_minutes": idle_remaining,
            }

        return result

    def format_status(self) -> str:
        """Return a human-readable status summary."""
        st = self.status()
        lines = ["Smart Infrastructure Status:", "=" * 60]

        for svc_name, info in sorted(st.items()):
            state = "healthy" if info["healthy"] else ("running" if info["running"] else "stopped")
            mode = info["mode"]
            idle = info.get("idle_remaining_minutes")
            idle_str = f", idle timeout in {idle}m" if idle is not None else ""
            lines.append(f"  {svc_name:<20} {state:<10} mode={mode}{idle_str}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level singleton and convenience functions
# ---------------------------------------------------------------------------

_instance: Optional[SmartInfra] = None


def _get_instance() -> SmartInfra:
    """Return (and lazily create) the module-level SmartInfra singleton."""
    global _instance
    if _instance is None:
        _instance = SmartInfra()
    return _instance


def ensure_service(name: str, timeout_secs: int = 120) -> bool:
    """Ensure a Docker service is running. See :meth:`SmartInfra.ensure_service`."""
    return _get_instance().ensure_service(name, timeout_secs=timeout_secs)


def stop_idle_services() -> List[str]:
    """Stop services past their idle timeout. See :meth:`SmartInfra.stop_idle_services`."""
    return _get_instance().stop_idle_services()


def ensure_for_skill(skill_name: str) -> Dict[str, bool]:
    """Ensure services for a skill. See :meth:`SmartInfra.ensure_for_skill`."""
    return _get_instance().ensure_for_skill(skill_name)


def is_docker_available() -> bool:
    """Check if Docker is available. See :meth:`SmartInfra._is_docker_available`."""
    return _get_instance()._is_docker_available()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def requires_service(*service_names: str):
    """Decorator: ensure Docker services are running before the function call.

    Graceful degradation -- the decorated function still executes even if a
    service fails to start.  A warning is logged for each failure.

    Example::

        @requires_service("langfuse", "litellm")
        def run_observability():
            ...
    """

    def decorator(func):  # type: ignore[type-arg]
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for svc in service_names:
                try:
                    ensure_service(svc)
                except Exception:  # noqa: BLE001
                    logger.warning("Failed to ensure service %s for %s", svc, func.__name__)
            return func(*args, **kwargs)

        return wrapper

    return decorator
