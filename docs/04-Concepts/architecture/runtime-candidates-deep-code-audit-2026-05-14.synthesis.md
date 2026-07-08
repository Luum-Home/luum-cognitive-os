---
type: concept-synthesis
source: docs/04-Concepts/architecture/runtime-candidates-deep-code-audit-2026-05-14.md
provenance: "Compares four runtime candidates for improving Cognitive OS harnesses and/or backing a standalone cosd / agent-service runtime, based on fresh shallow clones with commit-pinned code inspection."
---

## What it is
Deep source-code audit (2026-05-14) comparing four runtime candidates — Pi/pi-mono (TypeScript), Gollem/Fugue (Go), Hermes Agent (Python), Goose (Rust) — for improving COS harnesses and/or backing a standalone `cosd`/agent-service runtime.

## Key mechanics
- Clone snapshot (commit-pinned): Pi @`0b54c87e` (837 files, 674 TS), Gollem @`354a9f89` (453/422 Go), Hermes @`cd64bed5` (3,409/1,681 Python), Goose @`401f8e86` (3,001 files, 421 Rust / 1,109 TS).
- Executive verdict / COS role: Pi = short-term lifecycle-mapping baseline and reference; Gollem/Fugue = best medium-term Go backend candidate for `cosd`/agent-service; Hermes = product/UX benchmark and pattern mine, not first runtime dependency (highest overlap risk with COS); Goose = safety/interoperability/MCP/ACP comparator and adapter target.
- Pi: `packages/agent/src/types.ts` defines `BeforeToolCallResult`(block, reason) / `AfterToolCallResult`(content, details, isError, terminate); `AgentLoopConfig` exposes `transformContext`, `getApiKey`, `shouldStopAfterTurn`, `prepareNextTurn`, tool-execution mode, `beforeToolCall`/`afterToolCall`; coding-agent layer adds extension runner, `session_before_compact` events, resource-loader for `skillPaths`; mature OAuth for Anthropic/OpenAI Codex/GitHub Copilot.
- Gollem/Fugue: `core/agent.go` `Agent[T]` + tool loop; `core/hooks.go` `OnRunStart/End`, `OnModelRequest/Response`, `OnToolStart/End`, `OnTurnStart/End`, `OnContextCompaction`; `core/tool.go` typed tools with approval/timeouts; `core/eventbus.go` typed pub/sub; `ext/temporal` durable workflows; `ext/mcp` stdio/SSE/HTTP.
- Hermes: a full product, not a library — native memory, self-improving skills, FTS5 session search, cron, multi-channel gateway (Telegram/Discord/Slack/WhatsApp/Signal/Email); `acp_adapter/` maps tools to ACP `ToolKind` + permission bridge (allow_once/session/permanent/deny); `agent/tool_guardrails.py` classifies idempotent vs. mutating vs. no-progress tool loops.
- Goose: `agents/agent.rs` `Agent`+`AgentConfig`+extension manager+hook manager; default inspectors: `SecurityInspector`, `EgressInspector`, LLM-based `AdversaryInspector`, `PermissionInspector`, `RepetitionInspector`; `tool_inspection.rs` gives `InspectionAction::{Allow,Deny,RequireApproval}`; permission outcomes `AlwaysAllow`/`AllowOnce`/`Cancel`/`DenyOnce`/`AlwaysDeny`; SQLite-backed session manager.
- Feature comparison matrix scores all 4 across pre/post-tool interception, event bus, streaming, sessions, compaction, MCP, ACP, provider/auth, tool approval UX, coding-tool suite, durable execution, embeddable-runtime fit, product completeness, risk-of-replacing-COS, public adoption.
- Recommended COS strategy: no single winner as source of truth — build a `RuntimeHarnessContract` backed by `manifests/primitive-contracts.yaml` (lifecycle/permissions/events/projection fields) and run 4 separate adapter proofs: Pi (extension blocking a destructive command), Gollem (Go worker: edit/test/block/stream/emit evidence), Goose (inspector/permission/hook adapter), Hermes (UX-benchmark port, not runtime dependency).

## Relations & where used
`manifests/primitive-contracts.yaml`; proposed `RuntimeHarnessContract`. Companion doc `standalone-agent-runtime-adapter-options.md` covers the same runtime candidates with deeper construction-mechanics comparison.

## Status / caveats
Working conclusion only — no migration decision made. Explicit stance: "do not choose one winner as the new source of truth"; treat each candidate as the benchmark for a different layer (Pi=lifecycle harness, Gollem=embedded Go backend, Goose=safety/interoperability harness, Hermes=product UX/skills/memory benchmark).
