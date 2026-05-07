# SCOPE: both
"""ADR-236 deferred tool loading and ToolSearch planning helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "deferred-tool-loading/v1"
DEFAULT_MANIFEST = Path("manifests/deferred-tool-loading.yaml")


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    category: str
    description: str
    load_mode: str
    always_available: bool = False


@dataclass(frozen=True)
class ToolLoadingPlan:
    schema_version: str
    status: str
    visible_tools: list[str]
    deferred_tools: list[str]
    toolsearch_enabled: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "visible_tools": self.visible_tools,
            "deferred_tools": self.deferred_tools,
            "toolsearch_enabled": self.toolsearch_enabled,
            "reason": self.reason,
        }


def load_manifest(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir).resolve() / DEFAULT_MANIFEST
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "tools": [], "policy": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"tools": [], "policy": {}}


def descriptors(manifest: dict[str, Any]) -> list[ToolDescriptor]:
    result: list[ToolDescriptor] = []
    for row in manifest.get("tools", []) or []:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        result.append(
            ToolDescriptor(
                name=str(row["name"]),
                category=str(row.get("category") or "general"),
                description=str(row.get("description") or ""),
                load_mode=str(row.get("load_mode") or "deferred"),
                always_available=bool(row.get("always_available") or False),
            )
        )
    return result


def plan_tool_loading(
    project_dir: str | Path,
    *,
    estimated_tool_tokens: int = 0,
    threshold_tokens: int | None = None,
) -> ToolLoadingPlan:
    """Return the visible/deferred tool split for a session."""
    manifest = load_manifest(project_dir)
    policy = manifest.get("policy") or {}
    threshold = threshold_tokens if threshold_tokens is not None else int(policy.get("toolsearch_threshold_tokens") or 10_000)
    rows = descriptors(manifest)
    use_toolsearch = estimated_tool_tokens >= threshold or bool(policy.get("force_toolsearch") or False)
    visible: list[str] = []
    deferred: list[str] = []
    for tool in rows:
        if tool.always_available or tool.load_mode == "eager" or not use_toolsearch:
            visible.append(tool.name)
        else:
            deferred.append(tool.name)
    status = "deferred" if deferred else "eager"
    reason = "threshold_exceeded" if use_toolsearch else "below_threshold"
    return ToolLoadingPlan(SCHEMA_VERSION, status, visible, deferred, use_toolsearch, reason)


def toolsearch_index(project_dir: str | Path) -> dict[str, Any]:
    """Return compact searchable metadata for deferred tools."""
    manifest = load_manifest(project_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "tools": [tool.__dict__ for tool in descriptors(manifest)],
    }


def dumps_json(payload: Any) -> str:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()
    return json.dumps(payload, indent=2, sort_keys=True)
