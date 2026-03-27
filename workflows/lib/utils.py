"""Utility functions for backend workflows."""

import os
import random
import string
import subprocess
from typing import Dict, List, Optional

import yaml

from .data_types import ServiceConfig, ServiceLanguage


def check_env_vars(required: list) -> bool:
    """Check that required environment variables are set."""
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        return False
    return True


def make_workflow_id() -> str:
    """Generate a short unique workflow ID."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=8))


def get_project_root() -> str:
    """Get the project monorepo root.

    Walks up from this file's directory until it finds a directory containing
    docker-compose.yml or .claude/. Falls back to git rev-parse.
    """
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isfile(os.path.join(current, "docker-compose.yml")):
            return current
        if os.path.isdir(os.path.join(current, ".claude")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # Fallback: git root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    raise RuntimeError("Could not determine project root")


def get_services_config() -> List[ServiceConfig]:
    """Load service configurations from config/services.yaml."""
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "config",
        "services.yaml",
    )
    config_path = os.path.normpath(config_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Services config not found: {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    services = []
    for svc in data.get("services", []):
        services.append(ServiceConfig(**svc))

    return services


def get_service_config(service_name: str) -> Optional[ServiceConfig]:
    """Get configuration for a specific service by name."""
    for svc in get_services_config():
        if svc.name == service_name:
            return svc
    return None


def get_service_abs_path(service: ServiceConfig) -> str:
    """Get the absolute path for a service."""
    return os.path.join(get_project_root(), service.path)


def detect_service_language(service_path: str) -> ServiceLanguage:
    """Auto-detect the language of a service by examining its files."""
    abs_path = os.path.join(get_project_root(), service_path)

    if os.path.exists(os.path.join(abs_path, "go.mod")):
        return ServiceLanguage.GO
    if os.path.exists(os.path.join(abs_path, "build.gradle")):
        return ServiceLanguage.SPRING_BOOT
    if os.path.exists(os.path.join(abs_path, "build.gradle.kts")):
        return ServiceLanguage.SPRING_BOOT
    if os.path.exists(os.path.join(abs_path, "nest-cli.json")):
        return ServiceLanguage.NESTJS

    # Check package.json for NestJS vs Express
    pkg_path = os.path.join(abs_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            import json

            with open(pkg_path) as f:
                pkg = json.load(f)
            deps = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
            }
            if "@nestjs/core" in deps:
                return ServiceLanguage.NESTJS
            return ServiceLanguage.EXPRESS
        except Exception:
            return ServiceLanguage.EXPRESS

    return ServiceLanguage.EXPRESS  # default fallback


def get_allowed_tools_for_language(language: ServiceLanguage) -> List[str]:
    """Get the appropriate Claude Code allowed tools for a service language."""
    base_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
    return base_tools


def get_environments_config() -> Dict:
    """Load environment configurations from config/environments.yaml."""
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "config",
        "environments.yaml",
    )
    config_path = os.path.normpath(config_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Environments config not found: {config_path}"
        )

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    return data.get("environments", {})
