---
type: reference-synthesis
source: docs/08-References/integrations/cursor-cloud-agents.md
provenance: "Integration design (status: Design phase, last updated 2026-03-27) proposing how Cognitive OS's governance/memory/orchestration layer could pair with Cursor's cloud-agent execution VMs."
---

## What it is

A design document (not an implemented integration) proposing a layered architecture where Cognitive OS supplies governance, memory, cost tracking, and multi-agent coordination on top of Cursor's cloud/background agents (isolated VMs with terminal/browser/desktop access and video-proof PRs), positioning the pairing as a joint moat.

## Key mechanics

- **Architecture**: Human (decision layer, reviews video + Trust Report) → Cognitive OS (Layer 2: Engram memory, cost tracking/budget, quality gates, adaptive bypass, SDD pipeline, squad coordination) → multiple Cursor Agent VMs, each producing terminal/browser/desktop output, video proof, and a PR.
- **Four integration points**: (1) **Task dispatch** — COS classifies complexity (adaptive bypass), checks budget, selects trivial/single-agent/multi-agent-via-SDD workflow, prepares context (selective Engram retrieval, applicable rules, acceptance criteria, phase instructions), then triggers the Cursor agent via API/webhook. (2) **Result validation** — COS receives PR + video, runs acceptance criteria, validates claims against anti-hallucination checks (do files/tests actually exist/pass), computes a trust score, saves learnings to Engram, tracks cost, and presents the human with video + Trust Report + diff. (3) **Multi-agent coordination** — COS breaks large tasks via SDD (spec→design→tasks), dispatches each task to a separate Cursor agent, tracks progress via Agent Bus or polling, manages inter-task dependencies, aggregates and cross-verifies results, and re-dispatches with error context on failure. (4) **Memory sharing** — since Cursor agents start with no memory, COS injects relevant Engram context before dispatch, extracts and saves learnings after completion, and can share cross-project patterns via Engram namespaces.
- **Config shape** (`cognitive-os.yaml`): `integrations.cursor` block with `enabled` (default false, opt-in), `mode` (self-hosted|cloud), `worker_endpoint`, `api_key`, `max_parallel_agents` (COS-enforced), `dispatch_method` (api|webhook|slack), `video_review`, `cost_per_agent_minute`.
- **Prerequisites**: Cursor Business/Enterprise plan for the cloud agents API, a running `agent worker start` for self-hosted mode, COS installed with Engram configured, and a dispatch API key or webhook URL.
- **Three-phase rollout**: Phase 1 (manual — user triggers Cursor manually, COS provides context via copy-paste/CLAUDE.md, validates after the fact); Phase 2 (API — COS dispatches and receives completion webhooks, automated verification and cost tracking); Phase 3 (full orchestration — Singularity controller dispatches to Cursor, SDD phases execute as Cursor tasks, full squad coordination, Engram-bridged memory across all agents).
- **Competitive framing**: Cursor alone lacks governance/memory/coordination-at-scale; COS alone is governance-strong but execution-limited (relies on Claude Code sub-agents); combined, the claim is "governed execution at enterprise scale with persistent memory," asserted as unmatched by any other tool combination as of March 2026.

## Relations & where used

Ties into COS's existing SDD pipeline, adaptive-bypass complexity classification, rate-limiting/cost-governance rules, Engram memory, and (for Phase 3) the Singularity controller and squad coordination subsystems.

## Status / caveats

Explicitly marked **"Status: Design phase"**, last updated 2026-03-27 — this describes a proposed, not built, integration. Only "Phase 1: Manual Integration" is described as "now possible"; Phases 2 (API) and 3 (Full Orchestration) are prospective and depend on Cursor API availability and a "Singularity controller" that is itself DORMANT/aspirational per other repo audits. The "competitive moat" and "no other tool combination offers this today" claims are unverified positioning statements from the design doc itself, not audited claims — treat as aspirational marketing framing rather than a shipped-capability assertion.
