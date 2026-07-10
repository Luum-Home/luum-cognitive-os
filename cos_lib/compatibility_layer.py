# SCOPE: both
"""Explicit compatibility layer inventory.

The purpose of this module is to make ecosystem churn visible and contained.
Provider payloads, gateway behavior, and schema adaptation belong here as
explicit compatibility surfaces rather than implicit knowledge spread across
the codebase.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ProviderAdapterContract:
    name: str
    adapter_path: str
    normalized_into: str
    compatibility_surface: str


@dataclass(frozen=True)
class GatewayAdapterContract:
    name: str
    adapter_path: str
    concern: str


@dataclass(frozen=True)
class ToolSchemaAdapterContract:
    name: str
    adapter_path: str
    concern: str


@dataclass(frozen=True)
class HarnessAdapterContract:
    name: str
    adapter_path: str
    normalized_into: str
    compatibility_surface: str


@dataclass(frozen=True)
class DocumentedCompatibilityTarget:
    name: str
    evidence_path: str
    delivery_mode: str
    current_coverage: str
    compatibility_surface: str


PROVIDER_ADAPTERS: tuple[ProviderAdapterContract, ...] = (
    ProviderAdapterContract(
        name="claude",
        adapter_path="internal/provider/claude.go",
        normalized_into="pkg/hook/context.go",
        compatibility_surface="Hook payload parsing, canonical event mapping, response shape.",
    ),
    ProviderAdapterContract(
        name="codex",
        adapter_path="internal/provider/codex.go",
        normalized_into="pkg/hook/context.go",
        compatibility_surface="Hook payload parsing, canonical event mapping, response shape.",
    ),
    ProviderAdapterContract(
        name="gemini",
        adapter_path="internal/provider/gemini.go",
        normalized_into="pkg/hook/context.go",
        compatibility_surface="Hook payload parsing, canonical event mapping, response shape.",
    ),
    ProviderAdapterContract(
        name="cursor",
        adapter_path="internal/provider/cursor.go",
        normalized_into="pkg/hook/context.go",
        compatibility_surface="Editor event payload parsing and canonical tool mapping.",
    ),
    ProviderAdapterContract(
        name="devin",
        adapter_path="internal/provider/devin.go",
        normalized_into="pkg/hook/context.go",
        compatibility_surface="Editor event payload parsing and canonical tool mapping.",
    ),
)


HARNESS_ADAPTERS: tuple[HarnessAdapterContract, ...] = (
    HarnessAdapterContract(
        name="claude_code",
        adapter_path="lib/harness_adapter/claude_code.py",
        normalized_into="lib/harness_adapter/base.py",
        compatibility_surface="Canonical event emission for agent lifecycle, tool use, heartbeat, and token usage.",
    ),
    HarnessAdapterContract(
        name="aider",
        adapter_path="lib/harness_adapter/aider.py",
        normalized_into="lib/harness_adapter/base.py",
        compatibility_surface="Passive transcript parsing into canonical events with version-aware dispatch and parse errors.",
    ),
)


DOCUMENTED_COMPATIBILITY_TARGETS: tuple[DocumentedCompatibilityTarget, ...] = (
    DocumentedCompatibilityTarget(
        name="opencode",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="AGENTS.md + MCP + adapter/documentation strategy",
        current_coverage="documented_target",
        compatibility_surface="Native AGENTS.md compatibility and MCP portability; no native hook adapter implemented in this repo yet.",
    ),
    DocumentedCompatibilityTarget(
        name="continue",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="MCP + rules portability",
        current_coverage="documented_target",
        compatibility_surface="Rules and MCP portability target without a repo-local hook adapter implementation.",
    ),
    DocumentedCompatibilityTarget(
        name="cline",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="MCP + rules portability",
        current_coverage="documented_target",
        compatibility_surface="Rules portability target without native hook lifecycle support in this repo.",
    ),
    DocumentedCompatibilityTarget(
        name="roo_code",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="MCP + rules portability",
        current_coverage="documented_target",
        compatibility_surface="Rules and MCP compatibility target documented as a portability tier, not an implemented adapter.",
    ),
    DocumentedCompatibilityTarget(
        name="copilot_cli",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="hooks + rules portability",
        current_coverage="documented_target",
        compatibility_surface="Hook-compatible target documented in the tool matrix; no dedicated adapter module implemented here yet.",
    ),
    DocumentedCompatibilityTarget(
        name="kiro",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="hooks + rules portability",
        current_coverage="documented_target",
        compatibility_surface="Tool-specific hook and rules target documented in portability tiers without a local adapter implementation.",
    ),
    DocumentedCompatibilityTarget(
        name="zed",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="rules + MCP portability",
        current_coverage="documented_target",
        compatibility_surface="Rules and MCP compatibility target documented in the landscape matrix.",
    ),
    DocumentedCompatibilityTarget(
        name="warp",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="rules + MCP portability",
        current_coverage="documented_target",
        compatibility_surface="Portability target documented through AGENTS.md and MCP support rather than a local adapter.",
    ),
    DocumentedCompatibilityTarget(
        name="augment",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="rules + MCP portability",
        current_coverage="documented_target",
        compatibility_surface="Documented cross-tool portability target without a first-party adapter in the repo.",
    ),
    DocumentedCompatibilityTarget(
        name="trae",
        evidence_path="docs/04-Concepts/architecture/cross-tool-landscape.md",
        delivery_mode="rules + MCP portability",
        current_coverage="documented_target",
        compatibility_surface="Documented portability target in tiered coverage, separate from implemented provider adapters.",
    ),
)


GATEWAY_ADAPTERS: tuple[GatewayAdapterContract, ...] = (
    GatewayAdapterContract(
        name="bifrost",
        adapter_path="lib/gateway_selector.py",
        concern="Fast-path gateway health and selection.",
    ),
    GatewayAdapterContract(
        name="litellm",
        adapter_path="lib/gateway_selector.py",
        concern="Feature-rich fallback gateway and broad provider coverage.",
    ),
    GatewayAdapterContract(
        name="claude_direct",
        adapter_path="lib/gateway_selector.py",
        concern="Direct CLI execution when no proxy should be involved.",
    ),
)


TOOL_SCHEMA_ADAPTERS: tuple[ToolSchemaAdapterContract, ...] = (
    ToolSchemaAdapterContract(
        name="canonical_hook_context",
        adapter_path="pkg/hook/context.go",
        concern="Canonical provider-agnostic tool and event schema.",
    ),
    ToolSchemaAdapterContract(
        name="manifest_exports",
        adapter_path="cmd/cos/internal/manifest/types.go",
        concern="Portable package export schema for skills, rules, hooks, and templates.",
    ),
)


def compatibility_inventory() -> Dict[str, List[dict]]:
    """Return the explicit compatibility inventory as plain dicts."""
    return {
        "providers": [asdict(item) for item in PROVIDER_ADAPTERS],
        "harness_adapters": [asdict(item) for item in HARNESS_ADAPTERS],
        "documented_targets": [asdict(item) for item in DOCUMENTED_COMPATIBILITY_TARGETS],
        "gateways": [asdict(item) for item in GATEWAY_ADAPTERS],
        "tool_schemas": [asdict(item) for item in TOOL_SCHEMA_ADAPTERS],
    }


def compatibility_summary() -> str:
    """Return a compact human-readable summary."""
    parts = [
        "Compatibility Layer",
        "=" * 20,
        f"Providers: {', '.join(item.name for item in PROVIDER_ADAPTERS)}",
        f"Harness adapters: {', '.join(item.name for item in HARNESS_ADAPTERS)}",
        f"Documented targets: {', '.join(item.name for item in DOCUMENTED_COMPATIBILITY_TARGETS)}",
        f"Gateways: {', '.join(item.name for item in GATEWAY_ADAPTERS)}",
        f"Tool schemas: {', '.join(item.name for item in TOOL_SCHEMA_ADAPTERS)}",
    ]
    return "\n".join(parts)
