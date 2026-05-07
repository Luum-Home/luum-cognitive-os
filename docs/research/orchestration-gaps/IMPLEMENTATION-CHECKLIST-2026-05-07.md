# Orchestration ADR Implementation Checklist — 2026-05-07

**Scope**: ADRs derived from `docs/research/orchestration-gaps/` after the C1–C4 evaluation contract.

## Status legend

- ✅ implemented and tested
- 🟡 partially implemented / next slice needed
- 🔲 not started
- ⏸ intentionally deferred

## Load-bearing order

1. ADR-226 Event-Sourced Session Bus
2. ADR-227 Shadow-Git Checkpoint Substrate
3. ADR-228 Retry Contract + Cost Budget
4. ADR-230 Handoff Envelope + Cycle Deduplication
5. ADR-231+ distribution/adapters after substrate consumers stabilize

## Checklist

| ADR | Topic | Status | Next implementation slice | Required tests |
|---|---|---:|---|---|
| ADR-222 | Pre-Agent Snapshot Two-Phase Capture | ✅ | Implemented tactical mitigation: plan-only pre-agent hook + launch-confirmed stash commit + plan cleanup + ordering tests. Deprecates once ADR-223 fully replaces operator-worktree stash lane. | T1, T3, T4 done |
| ADR-226 | Event-Sourced Session Bus | ✅ Slices A–E implemented | Monitor perf/concurrency; consumers may now build on stable envelope | T6/T7 follow-ups |
| ADR-223 | Agent Lifecycle Reconstruction | 🟡 Slice A ✅ | Next: default-on policy + cleanup/reaper + cross-harness launch projection | T7, T8, T10 |
| ADR-227 | Shadow-Git Checkpoint Substrate | 🟡 Slice A ✅ | Next: conversation truncation + combined atomic restore + event-envelope wiring | T4, T7, T10 |
| ADR-224 | Shadow-State Snapshots Off-Repo | 🟡 Slice A ✅ | Next: operator runbook + retention/reaper integration | T3, T4, T10 |
| ADR-228 | Retry Contract + Cost Budget | 🟡 Slices A–F+retry ✅ | Real `lib/dispatch.py` budget pre-call gate + actual cost recording + provider circuit breaker + class-based retry attempt loop. Remaining: cost predictor estimates, T6 baseline budget, deeper chaos hardening. | T2/T3 done; T6/T7 pending |
| ADR-230 | Handoff Envelope + Cycle Deduplication | 🟢 Runtime receiver closed | File-IPC inbox transport, explicit receiver execution, external hook runner via `--hook-command`, timeout/failure receipts, and chaos test for kill-mid-receiver idempotency. Remaining only future daemon-spawned receiver runtime. | T1, T2, T3, T4, T5, T7-lite, T8 done |
| ADR-225 | Branch-Per-Task Mode | 🟡 Slices A–B ✅ | Canonical task branch policy + conditional prelaunch enforcement for explicit write/cloud/detached launches. Remaining: branch migration and ADR-235 auto-branching. | T1, T3, T4 done |
| ADR-231 | MCP Server Surface | 🟡 Slices A–B ✅ | Existing 8-tool FastMCP server formalized, optional OTel spans, and cross-harness stdio registration plans for Claude Code/Codex/Cursor/Windsurf. Remaining: Streamable HTTP and external trust-pinning consumption. | T1, T3, T4, T8 done |
| ADR-232 | Sandbox Adapter Tiers | 🟡 Slices A–D ✅ | Command wrapper, dispatch preflight, Claude CLI sandbox wrapping, in-process provider subprocess boundary, and microVM/ConTree adapter contracts. Remaining: actual optional microVM/ConTree runner integrations. | T1, T2, T3, T4 done; T7/T8/T10 partial |
| ADR-233 | Cross-Session Agent-Team File IPC | 🟡 Slices A–D ✅ | File-backed AgentTeam substrate, `cos team ...`, TaskCreated/TaskCompleted/TeammateIdle consumers, ADR-230 receiver flow, chaos claim race, cross-harness inbox contract, and machine-readable file/NATS/A2A transport-plan. Remaining: actual NATS/A2A adapter implementation is opt-in future. | T1, T3, T4, T7, T8 done |
| ADR-234 | Approval Policies as Code | 🟡 Slice A ✅ | YAML policy evaluator + CLI + sample destructive-bash policy. Remaining: hook migration/settings projection/external engines. | T1, T3, T4 done; T5/T8 pending |
| ADR-235 | Detached Agent Daemon | 🟡 Slices A–E ✅ | Queue/state + tmux launcher + sentinels + watchdog + budget gate + TeamTask enqueue + service-plan + opt-in launchd/systemd file installer + kill escalation. Remaining: activation helper/process-tree kill beyond tmux. | T1, T3, T4, T5, T7 done; T10 pending |
| ADR-236 | Deferred Tool Loading + ToolSearch | 🟡 Slices A–C ✅ | Manifest-backed planning + ToolSearch index + dispatch insertion/metrics + local `list_changed` state + truthful provider-native payload when APIs are unavailable. Remaining: true provider-native `defer_loading` once provider APIs exist. | T1, T2, T3, T4, T8-lite done; T9 pending |

## Guardrail

Do **not** implement consumer ADRs against imagined event-store semantics. ADR-226 Slice B must land first with a real measured latency budget and fan-out index consistency tests.
