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
| ADR-226 | Event-Sourced Session Bus | 🟡 Slice A ✅ | Slice B: fan-out global index + measured latency budget | T2, T5, T6 |
| ADR-223 | Agent Lifecycle Reconstruction | 🟡 Slice A ✅ | Next: default-on policy + cleanup/reaper + cross-harness launch projection | T7, T8, T10 |
| ADR-227 | Shadow-Git Checkpoint Substrate | 🔲 | Draft/implement after ADR-226 Slice B, using per-session event envelope | T1, T2, T4, T7, T10 |
| ADR-228 | Retry Contract + Cost Budget | 🔲 | Implement retry classifier + pre-call session budget against ADR-226 events | T1, T2, T3, T4, T5, T6 |
| ADR-230 | Handoff Envelope + Cycle Deduplication | 🔲 | Implement envelope dataclass + cycle/depth checks before any team runtime | T1, T2, T3, T4, T5 |
| ADR-231 | MCP Server Surface | 🔲 | Wait until core governance read-only tools are stable; expose read-mostly tools first | T1, T2, T3, T4, T8, T9 |
| ADR-232 | Sandbox Adapter Tiers | 🔲 | OS-native adapter prototype only after worktree/lifecycle invariants are green | T1, T2, T4, T5, T7, T8, T10 |
| ADR-233 | Cross-Session Agent-Team File IPC | 🔲 | Wait for ADR-226 Slice B and ADR-230 envelope | T1, T2, T3, T4, T5, T7 |
| ADR-234 | Approval Policies as Code | 🔲 | Migrate pure-decision deny hooks to generated/native settings projection | T1, T3, T4, T5, T8 |
| ADR-235 | Detached Agent Daemon | 🔲 | Wait for worktree-per-write-agent/lifecycle reconstruction; opt-in only | T1, T2, T4, T5, T7, T10 |
| ADR-236 | Deferred Tool Loading + ToolSearch | 🔲 | Extend ADR-216 tool discovery; do not create parallel router loop | T1, T2, T3, T4, T8, T9 |

## Guardrail

Do **not** implement consumer ADRs against imagined event-store semantics. ADR-226 Slice B must land first with a real measured latency budget and fan-out index consistency tests.
