"""Environment-driven configuration for the agent runtime web service.

Reads four environment variables:

- ``COS_AGENT_SERVICE_TOKEN``: bearer token required on protected endpoints.
- ``COS_DISABLE_AGENT_SERVICE``: kill switch. If ``"1"``, ``create_app`` refuses
  to construct the application.
- ``COS_AGENT_SERVICE_VERSION``: optional override for the version surfaced at
  ``GET /api/v1/version``. Defaults to the package version.
- ``COS_AGENT_SERVICE_BUILD``: optional build identifier surfaced at the same
  endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


KILL_SWITCH_ENV = "COS_DISABLE_AGENT_SERVICE"
TOKEN_ENV = "COS_AGENT_SERVICE_TOKEN"
VERSION_ENV = "COS_AGENT_SERVICE_VERSION"
BUILD_ENV = "COS_AGENT_SERVICE_BUILD"


@dataclass(frozen=True)
class ServiceConfig:
    """Immutable runtime configuration resolved from environment variables."""

    bearer_token: str | None
    version: str
    build: str
    kill_switch_active: bool

    @classmethod
    def from_env(cls, *, default_version: str) -> "ServiceConfig":
        return cls(
            bearer_token=os.environ.get(TOKEN_ENV) or None,
            version=os.environ.get(VERSION_ENV, default_version),
            build=os.environ.get(BUILD_ENV, "dev"),
            kill_switch_active=os.environ.get(KILL_SWITCH_ENV) == "1",
        )


class ServiceDisabledError(RuntimeError):
    """Raised when the kill switch is active and ``create_app`` is called."""
