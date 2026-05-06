---
related-adr: ADR-203
---

# Subagent Capability Contract and Launch Preflight Plan

## Goal

Prevent impossible subagent launches by comparing requested output requirements
against selected subagent type capabilities before fan-out.

## Phase 1 — Contract and local preflight

- [x] Add ADR-203.
- [x] Add `manifests/subagent-capabilities.yaml`.
- [x] Add `scripts/subagent_launch_preflight.py`.
- [x] Route `scripts/cos subagent preflight`.
- [x] Add unit tests for Explore blocking and explicit parent persistence.

## Phase 2 — Harness launch integration

- [ ] Identify every code path that launches subagents or composes Agent prompts.
- [ ] Run the preflight before any parallel fan-out where type and prompt are
      known.
- [ ] Emit `subagent_capability_mismatch` telemetry rows for blocked launches.
- [ ] Add a compact block message for operators.

## Phase 3 — Telemetry promotion

- [ ] Feed mismatch rows into ADR-201 `PromoteFromTelemetry`.
- [ ] Propose lowering Explore confidence for tasks containing artifact paths.
- [ ] Propose docs/catalog updates when new subagent types appear.

## Non-goals

- Do not remove Explore or make it writer-capable.
- Do not force all research through general-purpose agents.
- Do not auto-correct launch type silently; block or suggest unless a caller
      explicitly asks for suggestions-only output.

## Validation

```bash
python3 -m pytest tests/unit/test_subagent_launch_preflight.py -q
scripts/cos subagent preflight --type Explore --prompt 'write research/02-real-self-improvement.md' --json
scripts/cos subagent preflight --type Explore --prompt 'Explore read-only and return result only; parent will persist artifacts to research/02.md' --json
```
