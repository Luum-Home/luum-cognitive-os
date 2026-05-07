from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.audit
def test_detached_agent_daemon_manifest_declares_opt_in_no_heavy_deps() -> None:
    data = yaml.safe_load((PROJECT_ROOT / "manifests" / "detached-agent-daemon.yaml").read_text())
    assert data["schema_version"] == "detached-agent-daemon-policy/v1"
    assert data["mode"] == "opt-in"
    rules = "\n".join(data["hard_rules"])
    assert "No Redis/Postgres/RabbitMQ/Docker".lower() in rules.lower()
    assert data["runtime"]["default"] == "tmux"
    assert data["runtime"]["bundled"] is False
