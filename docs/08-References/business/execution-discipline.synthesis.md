---
type: reference-synthesis
source: docs/08-References/business/execution-discipline.md
provenance: "Makes explicit the three day-to-day execution rules needed to keep the durable-product master plan real across sessions: build what's real (not what sounds advanced), share logic instead of duplicating it, and preserve continuity through durable memory rather than recall."
---

## What it is

A short rules document operationalizing the master plan into concrete session-level execution discipline — the "how we actually work" companion to `durable-product-master-plan.md`'s "what we're building toward."

## Key mechanics

- **Rule 1 — Real over aspirational**: a change is "real" only if code behavior verifiably changes, a test locks the contract, an audit can observe the new state, or a doc reflects a real constraint. Named anti-patterns: describing untested portability, documenting a future subsystem as current, building wrapper layers with no real consumer, claiming harness "support" that secretly depends on another harness.
- **Rule 2 — Shared logic before duplicate logic**: prefer shared contract → shared resolver → shared helper → (only as a temporary, explicitly documented exception) duplicated logic. Named as especially important for runtime path resolution, settings projection, artifact discovery, installer target resolution, portability/release checks. The standard is explicitly *not* "no duplication ever" but "do not let the same rule silently fork across Bash, Python, Go, and docs without declaring the shared source of truth."
- **Rule 2.5 — Found bugs become work**: a broken-window discipline — small/safe bugs get fixed immediately; contract-changing bugs get documented then fixed; large/risky bugs get recorded in the active workplan before moving on. Explicitly: "a discovered bug is product work, not background noise."
- **Rule 3 — Durable memory hierarchy** (4 tiers, ranked by trust): (1) repository artifacts (docs, checklists, contracts, tests, workplans — primary durable memory), (2) compressed operator memory in `.codex/`, (3) Engram/MCP-backed memory *only when actually surfaced in the current session*, (4) conversation recall (lowest-trust, never the sole source of truth).
- **Rule 4 — Engram rule**: "memory claims must match actual available tooling" — if Engram isn't surfaced as an available MCP tool in the current session, don't pretend the memory was saved; fall back to repository artifacts and `.codex/` memory instead.
- **Rule 5 — Session handoff rule**: before ending a significant session, update the active workplan/checklist, document new analysis, record next-safe-step and still-dangerous-step, and prefer linking the exact preserving artifact — mirrored to MCP memory if available, otherwise repository artifacts remain authoritative.

## Relations & where used

Directly underlies the "Engram Persistent Memory Protocol" and "MANDATORY Self-Usage Protocol" sections of the orchestrator's own operating rules (this document's memory-hierarchy and "claims must match available tooling" stance is the project-level rationale for why those protocols exist and why they gate on tool availability). Its "shared logic before duplicate logic" rule is the stated justification behind `consumer-sdd-lane-surgical-review-plan.md`'s explicit refusal to build a duplicate workflow engine.

## Status / caveats

This is a timeless rules/discipline document with no point-in-time metrics or dated claims — lowest staleness risk in this batch. No internal inconsistencies found. It is prescriptive/normative (how work *should* proceed), not a report of actual compliance, so it should not be read as evidence that these rules are being followed in practice — only that they are the stated standard.
