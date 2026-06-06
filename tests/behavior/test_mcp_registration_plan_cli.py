from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS = PROJECT_ROOT / "scripts" / "cos"


@pytest.mark.behavior
def test_mcp_registration_plan_lists_cross_harness_hosts(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(COS), "mcp", "registration-plan", "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    hosts = {plan["host"] for plan in payload["plans"]}
    assert {"claude-code", "codex", "cursor", "devin"} <= hosts
    for plan in payload["plans"]:
        assert plan["server"]["transport"] == "stdio"
        assert plan["server"]["args"][0].endswith("mcp-server/cos_mcp.py")


@pytest.mark.behavior
def test_mcp_registration_plan_can_filter_one_host() -> None:
    result = subprocess.run(
        [str(COS), "mcp", "registration-plan", "--host", "codex", "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [plan["host"] for plan in payload["plans"]] == ["codex"]


@pytest.mark.behavior
def test_mcp_registration_plan_streamable_http_requires_trust_pin() -> None:
    result = subprocess.run(
        [str(COS), "mcp", "registration-plan", "--transport", "streamable-http", "--host", "cursor", "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [plan["host"] for plan in payload["plans"]] == ["cursor"]
    server = payload["plans"][0]["server"]
    assert server["transport"] == "streamable-http"
    assert server["url"].startswith("http://127.0.0.1:")
    assert server["trust_pin_required"] is True
    assert "command" not in server
