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
| ADR-230 | Handoff Envelope + Cycle Deduplication | 🟡 Slices F–H ✅ | File-IPC inbox transport plus explicit receiver execution via `cos team handoff receive`; external hook runner via `--hook-command`; timeout receipt covers kill-mid-receiver failure. Remaining: process-kill chaos for daemon-spawned receivers. | T1, T2, T3, T4, T5, T7-lite, T8 done |
| ADR-225 | Branch-Per-Task Mode | 🟡 Slices A–B ✅ | Canonical task branch policy + conditional prelaunch enforcement for explicit write/cloud/detached launches. Remaining: branch migration and ADR-235 auto-branching. | T1, T3, T4 done |
| ADR-231 | MCP Server Surface | 🟡 Slices A–B ✅ | Existing 8-tool FastMCP server formalized, optional OTel spans, and cross-harness stdio registration plans for Claude Code/Codex/Cursor/Windsurf. Remaining: Streamable HTTP and external trust-pinning consumption. | T1, T3, T4, T8 done |
| ADR-232 | Sandbox Adapter Tiers | 🟡 Slices A–C ✅ | Command wrapper, dispatch `require_sandbox` preflight, and Claude CLI subprocess sandbox wrapping. Remaining: in-process provider isolation, microVM/ConTree adapters, hook integration. | T1, T2, T3, T4 done; T7/T8/T10 pending |
| ADR-233 | Cross-Session Agent-Team File IPC | 🟡 Slices A–D ✅ | File-backed AgentTeam substrate, `cos team ...`, TaskCreated/TaskCompleted/TeammateIdle consumers, ADR-230 receiver flow, chaos claim race, cross-harness inbox contract, and machine-readable file/NATS/A2A transport-plan. Remaining: actual NATS/A2A adapter implementation is opt-in future. | T1, T3, T4, T7, T8 done |
| ADR-234 | Approval Policies as Code | 🟡 Slice A ✅ | YAML policy evaluator + CLI + sample destructive-bash policy. Remaining: hook migration/settings projection/external engines. | T1, T3, T4 done; T5/T8 pending |
| ADR-235 | Detached Agent Daemon | 🟡 Slices A–D ✅ | Queue/state + tmux launcher + done/heartbeat sentinels + watchdog reap + budget gate + TeamTask auto-enqueue + launchd/systemd service-plan output. Remaining: actual installer and process kill escalation. | T1, T3, T4, T5, T7 done; T10 pending |
| ADR-236 | Deferred Tool Loading + ToolSearch | 🟡 Slices A–B ✅ | Manifest-backed planning + ToolSearch-like metadata index + dispatch prompt insertion/metrics when requested. Remaining: provider-native `defer_loading` API and list_changed handling. | T1, T2, T3, T4 done; T8/T9 pending |

## Guardrail

Do **not** implement consumer ADRs against imagined event-store semantics. ADR-226 Slice B must land first with a real measured latency budget and fan-out index consistency tests.
