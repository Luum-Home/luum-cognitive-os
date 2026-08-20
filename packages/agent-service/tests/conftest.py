"""Shared pytest fixtures for the agent service test suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Make the package importable without `pip install -e .`.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent_service.app import create_app  # noqa: E402
from agent_service.config import ServiceConfig  # noqa: E402


TEST_TOKEN = "test-bearer-token-do-not-use-in-prod"


@pytest.fixture
def service_config(tmp_path) -> ServiceConfig:
    return ServiceConfig(
        bearer_token=TEST_TOKEN,
        version="0.1.0-test",
        build="test",
        kill_switch_active=False,
        session_store_path=tmp_path / "sessions.json",
    )


@pytest.fixture
def app(service_config: ServiceConfig):
    # Ensure no stray env overrides interfere with kill-switch tests in this app.
    os.environ.pop("COS_DISABLE_AGENT_SERVICE", None)
    return create_app(config=service_config)


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}"}
