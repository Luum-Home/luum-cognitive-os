"""Tests for scripts/check_mcp_servers.py"""
from __future__ import annotations

import json
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
# scripts/ uses snake_case (rules/python-naming.md) so direct import works.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import check_mcp_servers as cms  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_claude_dir(tmp_path: Path):
    """Create a minimal ~/.claude layout under tmp_path."""
    mcp_dir = tmp_path / "mcp"
    mcp_dir.mkdir()
    plugins_cache = tmp_path / "plugins" / "cache"
    plugins_cache.mkdir(parents=True)
    return tmp_path


def _write_mcp_config(mcp_dir: Path, name: str, config: dict) -> Path:
    path = mcp_dir / f"{name}.json"
    path.write_text(json.dumps(config))
    return path


# ---------------------------------------------------------------------------
# Test 1: Config parsing — standalone mcp/*.json files
# ---------------------------------------------------------------------------

def test_find_mcp_configs_parses_standalone_file(tmp_claude_dir: Path):
    """find_mcp_configs reads ~/.claude/mcp/<name>.json (single-server format)."""
    mcp_dir = tmp_claude_dir / "mcp"
    _write_mcp_config(mcp_dir, "engram", {"command": "engram", "args": ["mcp"]})

    with patch.object(cms, "MCP_DIR", mcp_dir), \
         patch.object(cms, "PLUGINS_CACHE", tmp_claude_dir / "plugins" / "cache"):
        configs = cms.find_mcp_configs()

    assert "engram" in configs
    assert configs["engram"]["command"] == "engram"
    assert configs["engram"]["args"] == ["mcp"]


def test_find_mcp_configs_parses_mcp_servers_format(tmp_claude_dir: Path):
    """find_mcp_configs handles the {'mcpServers': {...}} multi-server format."""
    mcp_dir = tmp_claude_dir / "mcp"
    payload = {
        "mcpServers": {
            "my-tool": {"command": "my-tool", "args": ["serve"]},
            "other-tool": {"command": "other-tool"},
        }
    }
    _write_mcp_config(mcp_dir, "multi", payload)

    with patch.object(cms, "MCP_DIR", mcp_dir), \
         patch.object(cms, "PLUGINS_CACHE", tmp_claude_dir / "plugins" / "cache"):
        configs = cms.find_mcp_configs()

    assert "my-tool" in configs
    assert "other-tool" in configs


def test_find_mcp_configs_reads_plugin_bundled_mcp_json(tmp_claude_dir: Path):
    """find_mcp_configs reads plugin-bundled .mcp.json files under plugins/cache."""
    plugins_cache = tmp_claude_dir / "plugins" / "cache"
    plugin_dir = plugins_cache / "engram" / "engram" / "0.1.0"
    plugin_dir.mkdir(parents=True)
    mcp_json = plugin_dir / ".mcp.json"
    mcp_json.write_text(json.dumps({
        "mcpServers": {
            "engram": {"command": "engram", "args": ["mcp", "--tools=agent"]}
        }
    }))

    with patch.object(cms, "MCP_DIR", tmp_claude_dir / "mcp"), \
         patch.object(cms, "PLUGINS_CACHE", plugins_cache):
        configs = cms.find_mcp_configs()

    assert "engram" in configs
    assert configs["engram"]["args"] == ["mcp", "--tools=agent"]


# ---------------------------------------------------------------------------
# Test 2: Multi-path conflict detection
# ---------------------------------------------------------------------------

def test_check_server_detects_multi_path_conflict():
    """check_server flags multi_path_conflict when which -a returns >1 result."""
    config = {"command": "engram", "args": ["mcp"]}

    with patch.object(cms, "which_all", return_value=[
        "/opt/homebrew/bin/engram",
        "/Users/user/go/bin/engram",
        "/Users/user/.local/bin/engram",
    ]), patch("shutil.which", return_value="/opt/homebrew/bin/engram"), \
       patch.object(cms, "get_binary_version", return_value="1.14.5"), \
       patch.object(cms, "is_process_running", return_value=True):

        result = cms.check_server("engram", config)

    assert result["multi_path_conflict"] is True
    assert len(result["binary_paths_all"]) == 3
    assert any("Multi-path conflict" in issue for issue in result["issues"])
    # Status is WARN (conflict) not ERROR (binary found, process running)
    assert result["status"] == "WARN"


def test_check_server_no_conflict_single_path():
    """check_server does not flag conflict when only one binary location exists."""
    config = {"command": "engram", "args": ["mcp"]}

    with patch.object(cms, "which_all", return_value=["/opt/homebrew/bin/engram"]), \
         patch("shutil.which", return_value="/opt/homebrew/bin/engram"), \
         patch.object(cms, "get_binary_version", return_value="1.14.5"), \
         patch.object(cms, "is_process_running", return_value=True):

        result = cms.check_server("engram", config)

    assert result["multi_path_conflict"] is False
    assert result["status"] == "OK"
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# Test 3: Missing process detection
# ---------------------------------------------------------------------------

def test_check_server_warns_when_process_not_running():
    """check_server emits an issue and WARN status when pgrep finds no process."""
    config = {"command": "engram", "args": ["mcp"]}

    with patch.object(cms, "which_all", return_value=["/opt/homebrew/bin/engram"]), \
         patch("shutil.which", return_value="/opt/homebrew/bin/engram"), \
         patch.object(cms, "get_binary_version", return_value="1.14.5"), \
         patch.object(cms, "is_process_running", return_value=False):

        result = cms.check_server("engram", config)

    assert result["process_running"] is False
    assert result["status"] == "WARN"
    assert any("restart Claude Code" in issue for issue in result["issues"])


def test_check_server_error_when_binary_missing():
    """check_server returns ERROR status when the binary is not in PATH."""
    config = {"command": "nonexistent-tool", "args": []}

    with patch.object(cms, "which_all", return_value=[]), \
         patch("shutil.which", return_value=None):

        result = cms.check_server("nonexistent-tool", config)

    assert result["binary_found"] is False
    assert result["status"] == "ERROR"
    assert any("not found in PATH" in issue for issue in result["issues"])


# ---------------------------------------------------------------------------
# Test 4: JSON output format
# ---------------------------------------------------------------------------

def test_main_json_output_is_valid_json(tmp_claude_dir, capsys):
    """--json flag produces machine-parseable JSON with expected top-level key."""
    mcp_dir = tmp_claude_dir / "mcp"
    _write_mcp_config(mcp_dir, "engram", {"command": "engram", "args": ["mcp"]})

    with patch.object(cms, "MCP_DIR", mcp_dir), \
         patch.object(cms, "PLUGINS_CACHE", tmp_claude_dir / "plugins" / "cache"), \
         patch.object(cms, "which_all", return_value=["/opt/homebrew/bin/engram"]), \
         patch("shutil.which", return_value="/opt/homebrew/bin/engram"), \
         patch.object(cms, "get_binary_version", return_value="1.14.5"), \
         patch.object(cms, "is_process_running", return_value=True), \
         patch("sys.argv", ["check_mcp_servers.py", "--json"]):

        exit_code = cms.main()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "mcp_servers" in data
    assert isinstance(data["mcp_servers"], list)
    assert exit_code == 0
