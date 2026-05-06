---
date: 2026-05-06
repo: maximhq/bifrost
mode: monitor-followup-light-deep
phase: 2
---

# Monitor Follow-up: maximhq/bifrost

## Phase 1 (Shallow) Verdict
- **Verdict:** monitor
- **Rationale:** Apache-2.0 Go gateway (claims 50x faster than litellm).

## Phase 2 (Light-Deep) Verification

### Repository Facts (gh api)
- **License (SPDX):** `Apache-2.0`
- **Stars:** 4637
- **Archived:** False
- **Last push:** 2026-05-06T07:41:55Z (active (<30d))
- **Primary language:** Go
- **Open issues:** 370
- **Description:** Fastest enterprise AI gateway (50x faster than LiteLLM) with adaptive load balancer, cluster mode, guardrails, 1000+ models support & <100 µs overhead at 5k RPS.
- **Top-level entries (first 3):** .claude, .dockerignore, .editorconfig

### Deep Finding
Apache-2.0, Go, ~4.6k stars. Performance gateway; same category as agentgateway.

### Peer Overlap with COS
Sub-100us overhead at 5k RPS — interesting if we externalize dispatch but unnecessary at COS scale.

## Revised Verdict

**REVISED_VERDICT:** `MONITOR_CONFIRMED`

- **Integration effort if any:** large
- **License gate:** pass
- **Archived gate:** pass
