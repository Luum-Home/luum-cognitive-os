"""Unit tests for lib/manifest_loader.py.

Covers:
- Happy path: real manifest loads, structure exposed correctly
- Schema validation: every error path raises ManifestError with a useful message
- Cross-references: profiles can't point at undefined tools/MCPs/groups
- Helpers: tool() / mcp_server() / profile() lookups

All tests use synthetic manifests written to tmp_path so the production
manifest at manifests/dependencies.yaml stays untouched.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lib.manifest_loader import (
    SCHEMA_VERSION,
    Manifest,
    ManifestError,
    MCPServer,
    default_manifest_path,
    load_manifest,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, payload: dict | str) -> Path:
    p = tmp_path / "dependencies.yaml"
    if isinstance(payload, str):
        p.write_text(payload)
    else:
        p.write_text(yaml.safe_dump(payload, sort_keys=False))
    return p


def _minimal_manifest() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "python": {
            "required": ["pyyaml>=6.0"],
            "groups": {"testing": ["pytest>=8.0"]},
        },
        "tools": [
            {
                "name": "jq",
                "criticality": "required",
                "check": "jq --version",
                "install": {"any": "brew install jq"},
            },
            {
                "name": "engram",
                "criticality": "recommended",
                "check": "engram --version",
                "install": {"any": "npx -y @anthropic/engram"},
            },
        ],
        "mcp_servers": [
            {
                "name": "engram",
                "criticality": "recommended",
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@anthropic/engram"],
                "register_to": "~/.claude/settings.json",
                "requires_tool": "engram",
            }
        ],
        "profiles": {
            "default": {
                "python_groups": [],
                "tools_required": ["jq"],
                "tools_recommended": ["engram"],
                "mcp_servers_recommended": ["engram"],
            },
            "full": {
                "python_groups": ["testing"],
                "tools_required": ["jq"],
                "tools_recommended": ["engram"],
                "mcp_servers_recommended": ["engram"],
            },
        },
    }


# ── Happy path ──────────────────────────────────────────────────────────


def test_real_manifest_loads():
    manifest = load_manifest()
    assert isinstance(manifest, Manifest)
    assert manifest.schema_version == SCHEMA_VERSION
    assert "pyyaml>=6.0" in manifest.python_required
    assert manifest.tool("jq") is not None
    assert manifest.tool("jq").criticality == "required"
    default = manifest.profile("default")
    assert "jq" in default.tools_required
    assert "engram" in default.tools_recommended


def test_real_manifest_default_profile_has_engram_mcp():
    manifest = load_manifest()
    default = manifest.profile("default")
    assert "engram" in default.mcp_servers_recommended
    engram = manifest.mcp_server("engram")
    assert engram is not None
    assert engram.requires_tool == "engram"


def test_synthetic_minimal_manifest_loads(tmp_path):
    p = _write(tmp_path, _minimal_manifest())
    manifest = load_manifest(p)
    assert len(manifest.tools) == 2
    assert len(manifest.mcp_servers) == 1
    assert manifest.profile("default").tools_required == ["jq"]


def test_default_path_honors_env_override(tmp_path, monkeypatch):
    p = _write(tmp_path, _minimal_manifest())
    monkeypatch.setenv("COS_MANIFEST_PATH", str(p))
    assert default_manifest_path() == p
    manifest = load_manifest()
    assert manifest.tool("jq") is not None


# ── Helpers ─────────────────────────────────────────────────────────────


def test_tool_lookup_returns_none_for_missing(tmp_path):
    p = _write(tmp_path, _minimal_manifest())
    manifest = load_manifest(p)
    assert manifest.tool("does-not-exist") is None


def test_profile_lookup_raises_for_unknown(tmp_path):
    p = _write(tmp_path, _minimal_manifest())
    manifest = load_manifest(p)
    with pytest.raises(ManifestError, match="Unknown profile"):
        manifest.profile("nonexistent")


def test_mcp_server_lookup(tmp_path):
    p = _write(tmp_path, _minimal_manifest())
    manifest = load_manifest(p)
    mcp = manifest.mcp_server("engram")
    assert isinstance(mcp, MCPServer)
    assert mcp.command == "npx"
    assert mcp.args == ["-y", "@anthropic/engram"]


# ── Schema validation: file-level ───────────────────────────────────────


def test_missing_file_raises():
    with pytest.raises(ManifestError, match="not found"):
        load_manifest("/tmp/definitely-does-not-exist.yaml")


def test_invalid_yaml_raises(tmp_path):
    p = tmp_path / "broken.yaml"
    p.write_text("not: valid: yaml: [")
    with pytest.raises(ManifestError, match="Invalid YAML"):
        load_manifest(p)


def test_non_mapping_root_raises(tmp_path):
    p = tmp_path / "list.yaml"
    p.write_text("- just a list\n- not a mapping\n")
    with pytest.raises(ManifestError, match="must be a mapping"):
        load_manifest(p)


def test_unknown_top_level_key_raises(tmp_path):
    payload = _minimal_manifest()
    payload["whatever"] = "extra"
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="Unknown top-level keys"):
        load_manifest(p)


def test_wrong_schema_version_raises(tmp_path):
    payload = _minimal_manifest()
    payload["schema_version"] = 99
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="Unsupported schema_version"):
        load_manifest(p)


# ── Schema validation: python section ───────────────────────────────────


def test_missing_python_section_raises(tmp_path):
    payload = _minimal_manifest()
    del payload["python"]
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="Missing required section 'python'"):
        load_manifest(p)


def test_python_required_must_be_list_of_strings(tmp_path):
    payload = _minimal_manifest()
    payload["python"]["required"] = [123, "ok"]
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="must be a list of strings"):
        load_manifest(p)


def test_python_groups_bad_type_raises(tmp_path):
    payload = _minimal_manifest()
    payload["python"]["groups"] = ["not", "a", "mapping"]
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="python.groups must be a mapping"):
        load_manifest(p)


# ── Schema validation: tools ────────────────────────────────────────────


def test_tool_missing_required_field_raises(tmp_path):
    payload = _minimal_manifest()
    del payload["tools"][0]["check"]
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="missing required field: 'check'"):
        load_manifest(p)


def test_tool_unknown_field_raises(tmp_path):
    payload = _minimal_manifest()
    payload["tools"][0]["frobnicate"] = True
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="unknown keys"):
        load_manifest(p)


def test_tool_invalid_criticality_raises(tmp_path):
    payload = _minimal_manifest()
    payload["tools"][0]["criticality"] = "kinda-important"
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="criticality 'kinda-important' invalid"):
        load_manifest(p)


def test_tool_install_must_be_str_str_mapping(tmp_path):
    payload = _minimal_manifest()
    payload["tools"][0]["install"] = ["not", "a", "mapping"]
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="install must be a mapping"):
        load_manifest(p)


def test_duplicate_tool_names_raise(tmp_path):
    payload = _minimal_manifest()
    payload["tools"].append(dict(payload["tools"][0]))
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="Duplicate names in tools"):
        load_manifest(p)


# ── Schema validation: mcp_servers ──────────────────────────────────────


def test_mcp_missing_required_field_raises(tmp_path):
    payload = _minimal_manifest()
    del payload["mcp_servers"][0]["transport"]
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="missing required field: 'transport'"):
        load_manifest(p)


def test_mcp_args_must_be_list_of_strings(tmp_path):
    payload = _minimal_manifest()
    payload["mcp_servers"][0]["args"] = "not-a-list"
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="args must be a list of strings"):
        load_manifest(p)


def test_mcp_requires_tool_must_exist_in_tools(tmp_path):
    payload = _minimal_manifest()
    payload["mcp_servers"][0]["requires_tool"] = "nonexistent-cli"
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="requires_tool 'nonexistent-cli' not in tools"):
        load_manifest(p)


# ── Schema validation: profiles ─────────────────────────────────────────


def test_profile_unknown_name_raises(tmp_path):
    payload = _minimal_manifest()
    payload["profiles"]["legacy"] = payload["profiles"]["default"]
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="Unknown profile 'legacy'"):
        load_manifest(p)


def test_profile_references_unknown_tool_raises(tmp_path):
    payload = _minimal_manifest()
    payload["profiles"]["default"]["tools_required"].append("nonexistent")
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="references unknown tool: 'nonexistent'"):
        load_manifest(p)


def test_profile_references_unknown_mcp_raises(tmp_path):
    payload = _minimal_manifest()
    payload["profiles"]["default"]["mcp_servers_recommended"].append("nonexistent")
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="references unknown MCP server: 'nonexistent'"):
        load_manifest(p)


def test_profile_references_unknown_python_group_raises(tmp_path):
    payload = _minimal_manifest()
    payload["profiles"]["full"]["python_groups"].append("nonexistent")
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError, match="references unknown python group: 'nonexistent'"):
        load_manifest(p)


# ── Real-world invariants on the production manifest ───────────────────


def test_real_manifest_default_profile_python_groups_empty():
    """The default profile should not pull in heavy optional Python groups."""
    manifest = load_manifest()
    assert manifest.profile("default").python_groups == []


def test_real_manifest_full_profile_has_testing_group():
    manifest = load_manifest()
    assert "testing" in manifest.profile("full").python_groups


def test_real_manifest_every_required_tool_has_install_recipe():
    manifest = load_manifest()
    required = [t for t in manifest.tools if t.criticality == "required"]
    assert required, "manifest must have at least one required tool"
    for tool in required:
        assert tool.install, f"{tool.name} has no install recipe"


def test_real_manifest_all_dataclasses_immutable():
    """Tool/MCPServer/Profile are frozen dataclasses — guards against mutation bugs."""
    manifest = load_manifest()
    with pytest.raises((AttributeError, Exception)):
        manifest.tools[0].name = "tampered"  # type: ignore[misc]
