from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "mcp-server"))
sys.path.insert(0, str(PROJECT_ROOT))

import cos_mcp  # noqa: E402


@pytest.mark.unit
def test_mcp_tool_span_noops_when_otel_missing_or_unconfigured() -> None:
    with cos_mcp._mcp_tool_span("cos_status"):
        pass


@pytest.mark.unit
def test_mcp_tools_are_wrapped_but_keep_valid_json() -> None:
    assert cos_mcp.cos_status.__name__ == "cos_status"
    payload = json.loads(cos_mcp.cos_status())
    assert isinstance(payload, dict)
