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

try:
    import yaml
except ImportError:  # PyYAML is optional for stdlib-only CLI smoke tests.
    yaml = None  # type: ignore[assignment]

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
    token_delta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "status": self.status,
            "visible_tools": self.visible_tools,
            "deferred_tools": self.deferred_tools,
            "toolsearch_enabled": self.toolsearch_enabled,
            "reason": self.reason,
        }
        if self.token_delta is not None:
            payload["token_delta"] = self.token_delta
        return payload


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.isdigit():
        return int(value)
    return value.strip("\"'")


def _load_manifest_fallback(text: str) -> dict[str, Any]:
    manifest: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "tools": [], "policy": {}}
    section: str | None = None
    current_tool: dict[str, Any] | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            current_tool = None
            if stripped.endswith(":"):
                section = stripped[:-1]
                if section == "tools":
                    manifest.setdefault("tools", [])
                elif section == "policy":
                    manifest.setdefault("policy", {})
            elif ":" in stripped:
                key, value = stripped.split(":", 1)
                manifest[key.strip()] = _parse_scalar(value.strip())
            continue
        if section == "policy" and indent == 2 and ":" in stripped:
            key, value = stripped.split(":", 1)
            manifest.setdefault("policy", {})[key.strip()] = _parse_scalar(value.strip())
            continue
        if section == "tools":
            if stripped.startswith("- "):
                current_tool = {}
                manifest.setdefault("tools", []).append(current_tool)
                item = stripped[2:]
                if ":" in item:
                    key, value = item.split(":", 1)
                    current_tool[key.strip()] = _parse_scalar(value.strip())
                continue
            if current_tool is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                current_tool[key.strip()] = _parse_scalar(value.strip())
    return manifest


def load_manifest(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir).resolve() / DEFAULT_MANIFEST
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "tools": [], "policy": {}}
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        return _load_manifest_fallback(text)
    return yaml.safe_load(text) or {"tools": [], "policy": {}}


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
    token_delta = estimate_toolsearch_token_delta(
        project_dir,
        estimated_tool_tokens=estimated_tool_tokens,
        toolsearch_enabled=use_toolsearch,
        visible_tools=visible,
        deferred_tools=deferred,
    )
    return ToolLoadingPlan(SCHEMA_VERSION, status, visible, deferred, use_toolsearch, reason, token_delta)


def toolsearch_index(project_dir: str | Path) -> dict[str, Any]:
    """Return compact searchable metadata for deferred tools."""
    manifest = load_manifest(project_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "tools": [tool.__dict__ for tool in descriptors(manifest)],
    }


def _estimate_tokens(payload: Any) -> int:
    text = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return max(1, (len(text) + 3) // 4)


def estimate_toolsearch_token_delta(
    project_dir: str | Path,
    *,
    estimated_tool_tokens: int = 0,
    toolsearch_enabled: bool,
    visible_tools: list[str],
    deferred_tools: list[str],
) -> dict[str, Any]:
    """Estimate local token delta for ToolSearch vs eager tool loading.

    The baseline is the caller-provided full tool token estimate when present,
    otherwise a deterministic local proxy derived from the manifest metadata.
    No tool content or credentials are recorded.
    """
    index = toolsearch_index(project_dir)
    index_by_name = {str(row.get("name")): row for row in index.get("tools", []) if isinstance(row, dict)}
    manifest_proxy_tokens = _estimate_tokens(index)
    baseline_tokens = int(estimated_tool_tokens) if int(estimated_tool_tokens or 0) > 0 else manifest_proxy_tokens
    if not toolsearch_enabled:
        prompt_tokens = baseline_tokens
    else:
        visible_index = {"schema_version": SCHEMA_VERSION, "tools": [index_by_name[name] for name in visible_tools if name in index_by_name]}
        deferred_index = {"schema_version": SCHEMA_VERSION, "tools": [index_by_name[name] for name in deferred_tools if name in index_by_name]}
        prompt_tokens = _estimate_tokens(visible_index) + _estimate_tokens(deferred_index)
    delta = baseline_tokens - prompt_tokens
    reduction_pct = round((delta / baseline_tokens) * 100.0, 2) if baseline_tokens > 0 else 0.0
    return {
        "schema_version": "toolsearch-token-delta/v1",
        "baseline_tool_tokens": baseline_tokens,
        "toolsearch_prompt_tokens": prompt_tokens,
        "estimated_delta_tokens": delta,
        "estimated_reduction_pct": reduction_pct,
        "measurement": "local_estimate",
    }


def record_toolsearch_token_delta(
    project_dir: str | Path,
    *,
    plan: ToolLoadingPlan,
    estimated_tool_tokens: int = 0,
    session_id: str = "",
    metrics_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append a content-free ToolSearch token delta metric."""
    root = Path(project_dir).resolve()
    delta = plan.token_delta or estimate_toolsearch_token_delta(
        root,
        estimated_tool_tokens=estimated_tool_tokens,
        toolsearch_enabled=plan.toolsearch_enabled,
        visible_tools=plan.visible_tools,
        deferred_tools=plan.deferred_tools,
    )
    payload = {
        **delta,
        "timestamp": time.time(),
        "session_id": session_id,
        "status": plan.status,
        "toolsearch_enabled": plan.toolsearch_enabled,
        "visible_tool_count": len(plan.visible_tools),
        "deferred_tool_count": len(plan.deferred_tools),
    }
    path = Path(metrics_path) if metrics_path else root / ".cognitive-os" / "metrics" / "toolsearch-token-delta.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return payload



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
