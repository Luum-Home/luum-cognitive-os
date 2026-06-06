from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.audit
def test_mcp_registration_manifest_declares_hosts_and_otel_attrs() -> None:
    data = yaml.safe_load((PROJECT_ROOT / "manifests" / "mcp-server-registration.yaml").read_text())
    assert data["schema_version"] == "mcp-server-registration/v1"
    assert data["server"]["transport"] == "stdio"
    assert set(data["server"]["transports"]) == {"stdio", "streamable-http"}
    assert data["server"]["transports"]["streamable-http"]["trust_pin_required"] is True
    assert {"claude-code", "codex", "cursor", "devin"} <= set(data["hosts"])
    attrs = set(data["server"]["otel"]["attributes"])
    assert {"mcp.server.name", "mcp.tool.name", "mcp.transport", "mcp.response.error_code"} <= attrs
