# ADR-236 — Deferred Tool Loading + ToolSearch Adoption

<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–C implemented (2026-05-07)  
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

Implemented Slice B:

- `lib/dispatch.py` can inject a compact `[TOOLSEARCH_INDEX]` into the prompt and emit tool-loading metadata when `skill_requirements.enable_toolsearch` / `estimated_tool_tokens` requests it.

Implemented Slice C:

- `list_changed()` compares the current ToolSearch index with a persisted state hash and reports added/removed tools; `scripts/cos-deferred-tool-plan --list-changed [--update-state]` exposes it.
- `provider_native_defer_payload()` emits a truthful provider payload: native `defer_loading` is marked unsupported until a provider API exists, while still carrying the local ToolSearch index.

Not implemented yet:

- Actual provider API `defer_loading` flags. No current provider path in this repo exposes that API, so COS must not pretend native support exists.
- Real MCP `notifications/tools/list_changed` transport emission; local detection is implemented and ready to feed it.

## Hard rules

- ADR-236 extends ADR-216; it must not create a parallel tool router loop.
- Deferred tools remain discoverable by metadata.
- Eager surface must stay small and governance-oriented.
- Runtime loading changes require separate dispatch integration tests.
