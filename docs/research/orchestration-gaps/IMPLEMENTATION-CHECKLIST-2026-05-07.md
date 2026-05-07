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
| ADR-228 | Retry Contract + Cost Budget | 🟡 Slices A–E ✅ | Next: wire into lib/dispatch.py + provider circuit breaker + cost predictor | T2, T4, T6, T7 |
| ADR-230 | Handoff Envelope + Cycle Deduplication | 🟡 Slice F partial ✅ | Envelope/dispatcher substrate plus ADR-233 inbox transport via `cos team handoff send`. Remaining: receiver execution, external hook runner, chaos/cross-harness lanes. | T1, T3, T4, T5 done; T2/T7/T8 pending |
| ADR-225 | Branch-Per-Task Mode | 🟡 Slice A ✅ | Observe/check substrate implemented: canonical task branch policy, manifest, CLI strict mode. Remaining: default prelaunch enforcement + ADR-233/235 integration. | T1, T3, T4 done |
| ADR-231 | MCP Server Surface | 🟡 Slice A ✅ | Existing 8-tool FastMCP server formalized, package export path added, manifest/audit/smoke tests. Remaining: OTel, HTTP transport, cross-harness registration. | T1, T3, T4 done; T8 pending |
| ADR-232 | Sandbox Adapter Tiers | 🟡 Slice A ✅ | Opt-in sandbox command wrapper implemented for Bubblewrap/Seatbelt with explicit fallback. Remaining: microVM/ConTree adapters + hook/dispatch integration. | T1, T3, T4 done; T7/T8/T10 pending |
| ADR-233 | Cross-Session Agent-Team File IPC | 🟡 Slices A–B ✅ | File-backed AgentTeam substrate plus `cos team ...`, TaskCreated/TeammateIdle consumers, and ADR-230 inbox handoff transport. Remaining: TaskCompleted mirror, chaos/cross-harness. | T1, T3, T4 done; T7/T8 pending |
| ADR-234 | Approval Policies as Code | 🟡 Slice A ✅ | YAML policy evaluator + CLI + sample destructive-bash policy. Remaining: hook migration/settings projection/external engines. | T1, T3, T4 done; T5/T8 pending |
| ADR-235 | Detached Agent Daemon | 🟡 Slice A ✅ | Opt-in file-backed queue/state + tmux launcher + done/heartbeat sentinels + CLI. Remaining: launchd/systemd installer, watchdog, ADR-228 budget gate, ADR-233 auto-enqueue. | T1, T3, T4 done; T5/T7/T10 pending |
| ADR-236 | Deferred Tool Loading + ToolSearch | 🟡 Slice A ✅ | Manifest-backed eager/deferred planning + ToolSearch-like metadata index implemented. Remaining: provider defer_loading + dispatch ToolSearch insertion + list_changed handling. | T1, T3, T4 done; T8/T9 pending |

## Guardrail

Do **not** implement consumer ADRs against imagined event-store semantics. ADR-226 Slice B must land first with a real measured latency budget and fan-out index consistency tests.
