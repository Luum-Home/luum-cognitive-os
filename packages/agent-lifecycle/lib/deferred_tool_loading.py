# SCOPE: both
"""ADR-236 deferred tool loading and ToolSearch planning helpers."""
from __future__ import annotations

import hashlib
import json
import os
import time
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



def _native_defer_supported(provider: str) -> bool:
    configured = os.environ.get("COS_NATIVE_DEFER_LOADING_PROVIDERS", "")
    allowed = {item.strip().lower() for item in configured.split(",") if item.strip()}
    return "*" in allowed or provider.strip().lower() in allowed


def provider_native_defer_payload(project_dir: str | Path, *, provider: str) -> dict[str, Any]:
    """Return provider-native defer/list_changed payload when supported.

    COS is truthful by default: no current provider path in this repo exposes a
    stable native API. Operators can opt in per provider with
    ``COS_NATIVE_DEFER_LOADING_PROVIDERS=provider`` once a host API appears; the
    payload shape is then generated and still carries the local ToolSearch index.
    """
    index = toolsearch_index(project_dir)
    supported = _native_defer_supported(provider)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider,
        "native_defer_loading_supported": supported,
        "toolsearch_index": index,
    }
    if supported:
        payload["reason"] = "provider_api_enabled_by_operator"
        payload["provider_payload"] = {
            "defer_loading": True,
            "list_changed": True,
            "toolsearch_index": index,
        }
    else:
        payload["reason"] = "provider_api_not_available"
    return payload


def _index_hash(index: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(index, sort_keys=True).encode("utf-8")).hexdigest()


def list_changed(project_dir: str | Path, *, state_path: str | Path | None = None, update_state: bool = False) -> dict[str, Any]:
    """Compare current ToolSearch index against the last saved index hash."""
    root = Path(project_dir).resolve()
    path = Path(state_path).resolve() if state_path else root / ".cognitive-os" / "metrics" / "deferred-tool-loading-state.json"
    index = toolsearch_index(root)
    current_hash = _index_hash(index)
    previous: dict[str, Any] = {}
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
    previous_tools = {row.get("name") for row in previous.get("tools", []) if isinstance(row, dict)}
    current_tools = {row.get("name") for row in index.get("tools", []) if isinstance(row, dict)}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "changed": current_hash != previous.get("index_hash"),
        "index_hash": current_hash,
        "previous_hash": previous.get("index_hash"),
        "added_tools": sorted(str(x) for x in current_tools - previous_tools if x),
        "removed_tools": sorted(str(x) for x in previous_tools - current_tools if x),
        "tool_count": len(current_tools),
    }
    if update_state:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"index_hash": current_hash, "tools": index.get("tools", []), "updated_at": time.time()}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def dumps_json(payload: Any) -> str:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()
    return json.dumps(payload, indent=2, sort_keys=True)
