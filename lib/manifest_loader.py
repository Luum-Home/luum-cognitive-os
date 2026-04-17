"""Manifest loader for manifests/dependencies.yaml.

Single source of truth for COS dependencies (Python, CLIs, MCP servers).
Validates schema manually (no jsonschema dep) and returns typed dataclasses.

Loader rejects unknown top-level keys, missing required fields, and bad
criticality values. Callers (scripts/manifest-check.sh, install.sh, doctor.sh)
get a parsed Manifest or a ManifestError describing exactly what is wrong.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1
VALID_CRITICALITIES = {"required", "recommended", "optional"}
VALID_PROFILES = {"default", "full"}
TOP_LEVEL_KEYS = {"schema_version", "python", "tools", "mcp_servers", "profiles"}
TOOL_KEYS = {
    "name", "criticality", "check", "install", "min_version",
    "degraded_behavior", "consumed_by", "enabled_when",
}
MCP_KEYS = {
    "name", "criticality", "transport", "command", "args",
    "register_to", "requires_tool", "consumed_by", "enabled_when",
}
PROFILE_KEYS = {
    "python_groups", "tools_required", "tools_recommended",
    "mcp_servers_recommended",
}


class ManifestError(ValueError):
    """Raised when the manifest fails validation."""


@dataclass(frozen=True)
class Tool:
    name: str
    criticality: str
    check: str
    install: dict[str, str]
    min_version: str | None = None
    degraded_behavior: str | None = None
    consumed_by: list[str] = field(default_factory=list)
    enabled_when: str | None = None


@dataclass(frozen=True)
class MCPServer:
    name: str
    criticality: str
    transport: str
    command: str
    args: list[str]
    register_to: str
    requires_tool: str | None = None
    consumed_by: list[str] = field(default_factory=list)
    enabled_when: str | None = None


@dataclass(frozen=True)
class Profile:
    name: str
    python_groups: list[str]
    tools_required: list[str]
    tools_recommended: list[str]
    mcp_servers_recommended: list[str]


@dataclass(frozen=True)
class Manifest:
    schema_version: int
    python_required: list[str]
    python_groups: dict[str, list[str]]
    tools: list[Tool]
    mcp_servers: list[MCPServer]
    profiles: dict[str, Profile]

    def tool(self, name: str) -> Tool | None:
        return next((t for t in self.tools if t.name == name), None)

    def mcp_server(self, name: str) -> MCPServer | None:
        return next((m for m in self.mcp_servers if m.name == name), None)

    def profile(self, name: str) -> Profile:
        if name not in self.profiles:
            raise ManifestError(f"Unknown profile: {name!r}. Valid: {sorted(self.profiles)}")
        return self.profiles[name]


def get_mcps_for_profile(profile: str, path: Path | str | None = None) -> list[dict]:
    """Return registrable MCP server dicts for a given profile name.

    Each dict contains: name, command, args, env (always {}), register_to.
    Only servers listed in profile.mcp_servers_recommended are returned.
    Raises ManifestError if the profile is unknown or the manifest is invalid.
    """
    manifest = load_manifest(path)
    prof = manifest.profile(profile)
    result: list[dict] = []
    for mcp_name in prof.mcp_servers_recommended:
        mcp = manifest.mcp_server(mcp_name)
        if mcp is None:
            # profile references are already validated in _build_manifest; this
            # should not happen in practice, but be defensive.
            raise ManifestError(f"MCP server {mcp_name!r} referenced by profile but not found")
        result.append({
            "name": mcp.name,
            "command": mcp.command,
            "args": list(mcp.args),
            "env": {},
            "register_to": mcp.register_to,
        })
    return result


def default_manifest_path() -> Path:
    """Return the on-disk path of manifests/dependencies.yaml.

    Resolves relative to this file (lib/) so importers don't need to know
    the repo root. Honors COS_MANIFEST_PATH env override for tests.
    """
    override = os.environ.get("COS_MANIFEST_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "manifests" / "dependencies.yaml"


def load_manifest(path: Path | str | None = None) -> Manifest:
    """Load and validate the manifest. Raises ManifestError on any problem."""
    p = Path(path) if path else default_manifest_path()
    if not p.exists():
        raise ManifestError(f"Manifest not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise ManifestError(f"Invalid YAML in {p}: {e}") from e
    if not isinstance(raw, dict):
        raise ManifestError(f"Manifest must be a mapping, got {type(raw).__name__}")
    return _build_manifest(raw, p)


def _build_manifest(raw: dict[str, Any], source: Path) -> Manifest:
    unknown = set(raw) - TOP_LEVEL_KEYS
    if unknown:
        raise ManifestError(f"Unknown top-level keys in {source}: {sorted(unknown)}")

    schema_version = raw.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ManifestError(
            f"Unsupported schema_version {schema_version!r}; loader expects {SCHEMA_VERSION}"
        )

    python = _require_mapping(raw, "python", source)
    python_required = _require_string_list(python, "required", f"{source}::python")
    groups_raw = python.get("groups", {}) or {}
    if not isinstance(groups_raw, dict):
        raise ManifestError(f"python.groups must be a mapping, got {type(groups_raw).__name__}")
    python_groups: dict[str, list[str]] = {}
    for gname, items in groups_raw.items():
        if not isinstance(items, list) or not all(isinstance(x, str) for x in items):
            raise ManifestError(f"python.groups.{gname} must be a list of strings")
        python_groups[gname] = list(items)

    tools_raw = raw.get("tools", []) or []
    if not isinstance(tools_raw, list):
        raise ManifestError("tools must be a list")
    tools = [_build_tool(t, i) for i, t in enumerate(tools_raw)]
    _check_unique([t.name for t in tools], "tools")

    mcp_raw = raw.get("mcp_servers", []) or []
    if not isinstance(mcp_raw, list):
        raise ManifestError("mcp_servers must be a list")
    mcp_servers = [_build_mcp(m, i) for i, m in enumerate(mcp_raw)]
    _check_unique([m.name for m in mcp_servers], "mcp_servers")

    profiles_raw = raw.get("profiles", {}) or {}
    if not isinstance(profiles_raw, dict):
        raise ManifestError("profiles must be a mapping")
    profiles: dict[str, Profile] = {}
    for pname, pdata in profiles_raw.items():
        if pname not in VALID_PROFILES:
            raise ManifestError(
                f"Unknown profile {pname!r}; valid: {sorted(VALID_PROFILES)}"
            )
        profiles[pname] = _build_profile(pname, pdata)

    tool_names = {t.name for t in tools}
    mcp_names = {m.name for m in mcp_servers}
    for prof in profiles.values():
        for ref in prof.tools_required + prof.tools_recommended:
            if ref not in tool_names:
                raise ManifestError(
                    f"Profile {prof.name!r} references unknown tool: {ref!r}"
                )
        for ref in prof.mcp_servers_recommended:
            if ref not in mcp_names:
                raise ManifestError(
                    f"Profile {prof.name!r} references unknown MCP server: {ref!r}"
                )
        for ref in prof.python_groups:
            if ref not in python_groups:
                raise ManifestError(
                    f"Profile {prof.name!r} references unknown python group: {ref!r}"
                )

    for mcp in mcp_servers:
        if mcp.requires_tool and mcp.requires_tool not in tool_names:
            raise ManifestError(
                f"MCP server {mcp.name!r} requires_tool {mcp.requires_tool!r} not in tools"
            )

    return Manifest(
        schema_version=schema_version,
        python_required=python_required,
        python_groups=python_groups,
        tools=tools,
        mcp_servers=mcp_servers,
        profiles=profiles,
    )


def _build_tool(raw: Any, index: int) -> Tool:
    if not isinstance(raw, dict):
        raise ManifestError(f"tools[{index}] must be a mapping")
    unknown = set(raw) - TOOL_KEYS
    if unknown:
        raise ManifestError(f"tools[{index}] has unknown keys: {sorted(unknown)}")
    for required in ("name", "criticality", "check", "install"):
        if required not in raw:
            raise ManifestError(f"tools[{index}] missing required field: {required!r}")
    crit = raw["criticality"]
    if crit not in VALID_CRITICALITIES:
        raise ManifestError(
            f"tools[{index}].criticality {crit!r} invalid; valid: {sorted(VALID_CRITICALITIES)}"
        )
    install = raw["install"]
    if not isinstance(install, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in install.items()
    ):
        raise ManifestError(f"tools[{index}].install must be a mapping of str→str")
    consumed_by = raw.get("consumed_by", []) or []
    if not isinstance(consumed_by, list) or not all(isinstance(x, str) for x in consumed_by):
        raise ManifestError(f"tools[{index}].consumed_by must be a list of strings")
    return Tool(
        name=raw["name"],
        criticality=crit,
        check=raw["check"],
        install=dict(install),
        min_version=raw.get("min_version"),
        degraded_behavior=raw.get("degraded_behavior"),
        consumed_by=list(consumed_by),
        enabled_when=raw.get("enabled_when"),
    )


def _build_mcp(raw: Any, index: int) -> MCPServer:
    if not isinstance(raw, dict):
        raise ManifestError(f"mcp_servers[{index}] must be a mapping")
    unknown = set(raw) - MCP_KEYS
    if unknown:
        raise ManifestError(f"mcp_servers[{index}] has unknown keys: {sorted(unknown)}")
    for required in ("name", "criticality", "transport", "command", "args", "register_to"):
        if required not in raw:
            raise ManifestError(
                f"mcp_servers[{index}] missing required field: {required!r}"
            )
    crit = raw["criticality"]
    if crit not in VALID_CRITICALITIES:
        raise ManifestError(
            f"mcp_servers[{index}].criticality {crit!r} invalid; valid: {sorted(VALID_CRITICALITIES)}"
        )
    args = raw["args"]
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ManifestError(f"mcp_servers[{index}].args must be a list of strings")
    consumed_by = raw.get("consumed_by", []) or []
    if not isinstance(consumed_by, list) or not all(isinstance(x, str) for x in consumed_by):
        raise ManifestError(f"mcp_servers[{index}].consumed_by must be a list of strings")
    return MCPServer(
        name=raw["name"],
        criticality=crit,
        transport=raw["transport"],
        command=raw["command"],
        args=list(args),
        register_to=raw["register_to"],
        requires_tool=raw.get("requires_tool"),
        consumed_by=list(consumed_by),
        enabled_when=raw.get("enabled_when"),
    )


def _build_profile(name: str, raw: Any) -> Profile:
    if not isinstance(raw, dict):
        raise ManifestError(f"profiles.{name} must be a mapping")
    unknown = set(raw) - PROFILE_KEYS
    if unknown:
        raise ManifestError(f"profiles.{name} has unknown keys: {sorted(unknown)}")
    return Profile(
        name=name,
        python_groups=_require_string_list(raw, "python_groups", f"profiles.{name}", allow_empty=True),
        tools_required=_require_string_list(raw, "tools_required", f"profiles.{name}", allow_empty=True),
        tools_recommended=_require_string_list(raw, "tools_recommended", f"profiles.{name}", allow_empty=True),
        mcp_servers_recommended=_require_string_list(raw, "mcp_servers_recommended", f"profiles.{name}", allow_empty=True),
    )


def _require_mapping(raw: dict[str, Any], key: str, source: Path) -> dict[str, Any]:
    if key not in raw:
        raise ManifestError(f"Missing required section {key!r} in {source}")
    val = raw[key]
    if not isinstance(val, dict):
        raise ManifestError(f"{key!r} must be a mapping, got {type(val).__name__}")
    return val


def _require_string_list(
    raw: dict[str, Any], key: str, ctx: str, *, allow_empty: bool = False
) -> list[str]:
    if key not in raw:
        if allow_empty:
            return []
        raise ManifestError(f"Missing required field {key!r} in {ctx}")
    val = raw[key]
    if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
        raise ManifestError(f"{ctx}.{key} must be a list of strings")
    return list(val)


def _check_unique(names: list[str], section: str) -> None:
    seen: set[str] = set()
    dupes: list[str] = []
    for n in names:
        if n in seen:
            dupes.append(n)
        seen.add(n)
    if dupes:
        raise ManifestError(f"Duplicate names in {section}: {dupes}")
