---
adr: 236
title: Deferred Tool Loading + ToolSearch Adoption
status: accepted
implementation_status: partial
date: '2026-05-07'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'Slices A-D are implemented; real MCP list_changed transport emission remains explicitly not implemented'
partial_remaining: Slices A-D are implemented; real MCP list_changed transport emission remains explicitly not implemented
partial_remaining_basis: specific classification_basis
---

# ADR-236 — Deferred Tool Loading + ToolSearch Adoption

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–D implemented (2026-05-07)  
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

Implemented Slice D:

- `provider_native_defer_payload()` remains truthful by default, but can emit a provider-native `defer_loading`/`list_changed` payload when an operator enables a known provider via `COS_NATIVE_DEFER_LOADING_PROVIDERS`.
- `lib/dispatch.py` attaches provider-native payload candidates to tool-loading metadata when `skill_requirements.native_defer_loading` is explicit.

Not implemented yet:

- Real MCP `notifications/tools/list_changed` transport emission; local detection is implemented and ready to feed it when host APIs expose the hook.

## Hard rules

- ADR-236 extends ADR-216; it must not create a parallel tool router loop.
- Deferred tools remain discoverable by metadata.
- Eager surface must stay small and governance-oriented.
- Runtime loading changes require separate dispatch integration tests.

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on conversation history.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
