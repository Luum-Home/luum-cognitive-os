---
date: 2026-05-06
repo: agentgateway/agentgateway
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: agentgateway/agentgateway

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 Go gateway. Same category as litellm; ADR-049 covers routing.

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 2606
- **Archived:** False
- **Last push:** 2026-05-05T23:49:05Z (active (<30d))
- **Primary language:** Rust
- **Open issues:** 205
- **Description:** Next Generation Agentic Proxy for AI Agents and MCP servers
- **Top-level entries (first 3):** .cargo, .devcontainer.json, .dockerignore

### Deep Finding
Apache-2.0, Rust/Go gateway, active, ~3k stars. Performance-optimized but COS volume doesn't justify externalizing dispatch.

### Peer Overlap with COS
Externalized gateway service; lib/dispatch.py is in-process and sufficient for current scale.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** large (would require ops infra)
- **License gate:** pass
- **Archived gate:** pass
