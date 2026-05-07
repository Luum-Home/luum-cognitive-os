# ADR-236 — Deferred Tool Loading + ToolSearch Adoption

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-044 (context payload slimming), ADR-216 (tool discovery pre-use gate), ADR-231 (MCP server surface)

---

## Context

The orchestration research recommended adopting the ToolSearch/deferred-loading pattern instead of loading every tool schema into every session. This is not a second router. It extends ADR-216: use the existing primitive-first discovery discipline, but keep heavyweight tool surfaces searchable and deferred until needed.

## Decision

Add a manifest-backed deferred tool loading substrate:

- Small eager surface stays visible.
- Heavy/optional surfaces are represented by compact metadata.
- A ToolSearch-like index can be generated from the manifest.
- Runtime dispatch integration is deferred to a later slice.

## Implementation status (2026-05-07)

Implemented Slice A:

- `packages/agent-lifecycle/lib/deferred_tool_loading.py` plans eager/deferred splits and emits a searchable index.
- `lib/deferred_tool_loading.py` package symlink.
- `manifests/deferred-tool-loading.yaml` declares policy and compact metadata.
- `scripts/cos-deferred-tool-plan` exposes plan/index output.
- Unit/audit/behavior tests validate threshold behavior, ADR-216 extension invariant, and CLI smoke.

Not implemented yet:

- Actual provider API `defer_loading` flags.
- Runtime insertion of ToolSearch into `lib/dispatch.py`.
- MCP `notifications/tools/list_changed` handling.

## Hard rules

- ADR-236 extends ADR-216; it must not create a parallel tool router loop.
- Deferred tools remain discoverable by metadata.
- Eager surface must stay small and governance-oriented.
- Runtime loading changes require separate dispatch integration tests.
