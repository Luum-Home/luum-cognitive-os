---
adr: 231
title: MCP Server Surface for COS Primitives
status: accepted
implementation_status: implemented
date: '2026-05-07'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit accepted/implemented status
---

# ADR-231 — MCP Server Surface for COS Primitives

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–C implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-211 (service readiness), ADR-216 (tool discovery pre-use gate), ADR-226 (event-sourced session bus), ADR-233 (cross-session teams), ADR-236 (deferred tool loading)  
**Source**: [`docs/03-PoCs/research/orchestration-gaps/mcp-as-orchestration-bus.md`](../research/orchestration-gaps/mcp-as-orchestration-bus.md)

---

## Context

COS should expose governance/read-only state through a standard MCP server before adding heavier orchestration adapters. The repository already had a mature server at `mcp-server/cos_mcp.py` with eight tools and unit tests, while `packages/mcp-server/cos-package.yaml` advertised that server as a package export. The missing piece was making ADR-231 explicit in the orchestration slate and proving the packaged surface resolves to the implementation.

This is a consumer ADR: it does not introduce a daemon, database, queue, or network service by default. It is a stdio MCP publisher that a host may opt into.

## Decision

Adopt the existing `mcp-server/cos_mcp.py` as the canonical ADR-231 MCP server surface and package it through `packages/mcp-server/cos_mcp.py`.

Slice A exposes the existing eight tools:

1. `cos_search_memory`
2. `cos_get_tasks`
3. `cos_get_rules`
4. `cos_check_quality`
5. `cos_get_metrics`
6. `cos_suggest_skill`
7. `cos_save_memory`
8. `cos_status`

Write-capable operations remain constrained. `cos_save_memory` is allowed because it runs through the memory scanner / safe Engram path and is not a filesystem mutation. Additional write tools require a later ADR amendment and ADR-211 readiness gate.

## Implementation status (2026-05-07)

Implemented:

- `mcp-server/cos_mcp.py` remains the canonical implementation.
- `packages/mcp-server/cos_mcp.py` is a package-owned symlink to the canonical implementation, so package consumers have a stable path.
- `packages/mcp-server/cos-package.yaml` points at the package path.
- `tests/audit/test_mcp_server_package_surface.py` verifies manifest/tool parity and the package symlink.
- `tests/behavior/test_mcp_server_smoke.py` imports the package path in a subprocess and calls read-mostly tools without needing FastMCP installed.
- Existing `tests/unit/test_cos_mcp_server.py` continues to validate tool behavior.

Implemented Slice B:

- Optional OpenTelemetry spans around all eight MCP tools. Instrumentation is no-op when OTel is absent.
- `manifests/mcp-server-registration.yaml` declares stdio registration plans for Claude Code, Codex, Cursor, and Windsurf.
- `scripts/cos-mcp-registration-plan` plus `cos mcp registration-plan` emit host-specific registration plans without mutating user-global config.

Implemented Slice C:

- `mcp-server/cos_mcp.py` and package mirror accept `--transport streamable-http` while preserving stdio as the default.
- `manifests/mcp-server-registration.yaml` declares both stdio and Streamable HTTP transport shapes.
- `scripts/cos-mcp-registration-plan --transport streamable-http` emits URL-based host plans with `trust_pin_required: true` instead of command mutation.
- `scripts/mcp_tofu_audit.py` fingerprints URL/transport fields so external HTTP MCP consumption can be pinned before use.

Not implemented in Slice C:

- ToolSearch/deferred loading; tracked by ADR-236.

## Hard rules

- The MCP server must remain optional. Importing COS must not start a daemon.
- The package export path must resolve to the canonical implementation.
- The first public surface is read-mostly; new mutating MCP tools require an ADR/update and readiness gate.
- FastMCP absence must degrade gracefully for tests and direct tool imports.
- Streamable HTTP consumption must carry `trust_pin_required: true` and pass MCP TOFU audit before external servers are trusted.

## Test matrix

- T1 unit: `tests/unit/test_cos_mcp_server.py`
- T3 contract/audit: `tests/audit/test_mcp_server_package_surface.py`
- T4 smoke: `tests/behavior/test_mcp_server_smoke.py`
- T8 cross-harness: `tests/behavior/test_mcp_registration_plan_cli.py` verifies host registration plans for Claude Code, Codex, Cursor, and Windsurf
- T9 adoption-truth: package manifest must match importable tools

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_cos_mcp_server.py tests/unit/test_cos_mcp_otel.py tests/audit/test_mcp_server_package_surface.py tests/audit/test_mcp_registration_manifest.py tests/behavior/test_mcp_server_smoke.py tests/behavior/test_mcp_registration_plan_cli.py -q
```

The tests must prove:

- `packages/mcp-server/cos_mcp.py` exists and resolves to `mcp-server/cos_mcp.py`.
- `cos-package.yaml` lists exactly the exposed tool names.
- The package path can be imported in a clean subprocess.
- Read-mostly tools return JSON without requiring FastMCP transport startup.
- Streamable HTTP registration plans are URL-based and explicitly require trust pins.

## Consequences

Positive:

- ADR-231 becomes real without adding service footprint.
- ADR-233 and ADR-236 can target a stable MCP publisher surface.
- Package consumers no longer rely on a manifest pointing outside the package without a package-local file.

Negative / trade-offs:

- The implementation predates ADR-231 and still needs OTel instrumentation.
- `cos_save_memory` is not read-only; it remains allowed only because it uses the safe memory write path. Future write tools should not copy this exception casually.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
