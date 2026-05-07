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
| ADR-223 | Agent Lifecycle Reconstruction | 🟢 Slices A–D ✅ | Default-on worktree lifecycle, manifest-scoped cleanup/reaper, cross-harness projection, and branch-prefix support implemented. Remaining future: deeper shadow-state retention integration. | T1, T3, T4, T8-lite, T10-lite done |
| ADR-227 | Shadow-Git Checkpoint Substrate | 🟢 Slices A–F ✅ | Off-repo snapshots, preview-gated files restore, conversation truncation, atomic files+conversation restore, and event-envelope `file_tree_sha` wiring implemented. Remaining runbook/reaper belongs to ADR-224. | T1, T3, T4 done; T7/T10 partial |
| ADR-224 | Shadow-State Snapshots Off-Repo | 🟢 Slices A–C ✅ | Off-repo shadow-git safety net, operator rollback runbook, and manual retention/reaper via `cos rollback --prune`. | T1, T3, T4, T10 done |
| ADR-228 | Retry Contract + Cost Budget | 🟢 Runtime closed | Dispatch budget gate, actual accounting, provider circuit breaker, class-based retry loop, provider-aware cost predictor, T6 perf baseline, and T7 circuit recovery chaos. Remaining future only: operator runbook polish. | T2/T3/T6/T7 done |
| ADR-230 | Handoff Envelope + Cycle Deduplication | 🟢 Runtime receiver closed | File-IPC inbox transport, explicit receiver execution, external hook runner via `--hook-command`, timeout/failure receipts, SIGKILL/timeout chaos receipts, and idempotent skip after failure. | T1, T2, T3, T4, T5, T7, T8 done |
| ADR-225 | Branch-Per-Task Mode | 🟢 Slices A–C ✅ | Canonical task branch policy, conditional prelaunch enforcement, and ADR-235 auto-branching via `--prepare-worktree` default `codex/task/*` prefix. | T1, T3, T4 done |
| ADR-231 | MCP Server Surface | 🟢 Slices A–C ✅ | Existing 8-tool FastMCP server formalized, optional OTel spans, stdio + Streamable HTTP registration plans, and trust-pin-required URL consumption fingerprints. | T1, T3, T4, T8 done |
| ADR-232 | Sandbox Adapter Tiers | 🟢 Slices A–E ✅ | Command wrapper, dispatch preflight, Claude CLI/provider subprocess wrapping, microVM/ConTree adapter contracts, and opt-in runner-backed CLI execution. | T1, T2, T3, T4 done; T7/T8/T10 partial |
| ADR-233 | Cross-Session Agent-Team File IPC | 🟢 Transport adapters closed | File-backed AgentTeam substrate, `cos team ...`, hooks, ADR-230 receiver flow, chaos claim race, cross-harness inbox contract, real opt-in NATS publish adapter, real A2A HTTP JSON adapter, and CLI `transport-send`. | T1, T3, T4, T7, T8 done |
| ADR-234 | Approval Policies as Code | 🟢 Slices A–C ✅ | YAML evaluator, CLI, destructive/protected-config policies, two real hook migrations, and plan-only Claude/Codex settings projection. External engines intentionally deferred. | T1, T3, T4 done; T5/T8 partial |
| ADR-235 | Detached Agent Daemon | 🟢 Slices A–F ✅ | Queue/state + tmux launcher + sentinels + watchdog + budget gate + TeamTask enqueue + service-plan/install + activation helper + tmux/process-tree kill escalation. | T1, T3, T4, T5, T7 done; T10 partial |
| ADR-236 | Deferred Tool Loading + ToolSearch | 🟢 Slices A–D ✅ | Manifest-backed planning + ToolSearch index + dispatch insertion/metrics + local `list_changed` state + truthful provider-native payloads with operator-enabled native API switch. | T1, T2, T3, T4, T8-lite done; T9 pending |

## Guardrail

Do **not** implement consumer ADRs against imagined event-store semantics. ADR-226 Slice B must land first with a real measured latency budget and fan-out index consistency tests.
