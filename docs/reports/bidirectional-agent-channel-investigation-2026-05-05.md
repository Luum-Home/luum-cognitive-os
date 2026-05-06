# Bidirectional Agent Communication Channel — Investigation

**Date**: 2026-05-05
**Status**: research-only; no state modified
**Trigger**: Operator recalls prior discussion of a bidirectional channel; wants the current architectural state surfaced before deciding whether ADR-183/185 (just drafted) overlap, complement, or supersede.

---

## TL;DR

- The **bidirectional channel is fully designed and partially implemented**: `packages/agent-coordination/lib/agent_bus.py` provides a Valkey pub/sub channel with 5 directional lanes (heartbeat, progress, question, answer, control). The **question/answer** pair is the explicit bidirectional contract.
- The bus is **dormant by default**: `AGENT_BUS_ENABLED=false`, Valkey is `mode: on_demand` in `cognitive-os.yaml`. File-based fallback runs automatically when Valkey is absent.
- A second communication layer (**hcom**) was researched (2026-03-28, engram #1666) and assessed as complementary — cross-terminal, not intra-session. It was never integrated.
- ADR-116 (2026-05-02) independently proposed `lib/session_bus.py` (P1.3) as an **append-only cross-session event file** — a simpler, no-daemon sibling for multi-session visibility. Also not yet implemented.
- **ADR-183** (cross-session event log) and **ADR-185** (audit findings queue) are the newest layer. They **complement** the prior design at a different scope (cross-session, file-only) rather than superseding it (intra-session, Valkey/pub-sub).
- The recommendation is to **move forward with ADR-183/185** for tonight's needs. The Valkey bus question/answer flow remains a separate, dormant, higher-fidelity channel that could be activated later.
- Uncertainty: the prior discussion that seeded the operator's memory likely lives in chat transcript, not in engram or any commit — engram has no direct match for "bidirectional agent communication channel" as a standalone design session.

---

## What Was Proposed (per surviving artifacts)

### 1. Valkey Agent Bus (primary design — fully documented)

**Source**: `packages/agent-coordination/lib/agent_bus.py` + `packages/agent-coordination/rules/agent-communication.md`

The bus defines five channel lanes per agent:

| Channel | Direction | Purpose |
|---|---|---|
| `cos:agent:{id}:heartbeat` | Agent → Orchestrator | Alive signal every 5 s |
| `cos:agent:{id}:progress` | Agent → Orchestrator | Tool-use notifications |
| `cos:agent:{id}:question` | Agent → Orchestrator | Clarification requests |
| `cos:agent:{id}:answer` | Orchestrator → Agent | Replies to questions |
| `cos:agent:{id}:control` | Orchestrator → Agent | stop/pause/resume |

The `question/answer` pair is the explicit **bidirectional** contract: an agent can block waiting for an orchestrator answer (timeout: 300 s). This is the most direct match for what the operator recalls.

**ADR**: ADR-042 (`docs/adrs/ADR-042-valkey-local-daemon.md`) governs Valkey's runtime model — local daemon via `scripts/cos-valkey-local.sh`, demoted from Docker to `profiles: [legacy]`, with file-based fallback chain in `agent_bus.py`.

### 2. hcom — Cross-Terminal Agent Communication

**Source**: engram observation #1666 (2026-03-28, topic: `architecture/hcom-integration-research`)

Research into `hcom` (github.com/aannoo/claude-hook-comms, MIT, Rust+Python) as a **cross-terminal** bidirectional layer. Key finding: complementary to Valkey bus, not a replacement. hcom covers multi-terminal / multi-tool scope; Valkey covers intra-session orchestrator↔sub-agent scope. Integration plan was drafted (3 phases, 5–7 days total) but never executed.

### 3. ADR-116 P1.3 — Inter-Session Pub/Sub Bus

**Source**: `docs/adrs/ADR-116-multi-session-coordination-primitives.md`, lines 75–83

Proposed `lib/session_bus.py` + `scripts/session_event_watcher.py`: an append-only `.cognitive-os/sessions/events.jsonl` fanned to in-session listeners via a tail watcher. Listed artifacts "to create" — design-only as of 2026-05-02.

### 4. ADR-024 — Task Panel Bridge (first "bidirectional adapter")

**Source**: `docs/adrs/ADR-024-task-panel-bridge.md` line 17

Describes itself as "the first full bidirectional adapter." Scope is narrower: correlates COS task_id with Claude Code's native `tool_use_id` via `hooks/_lib/task_bridge.py`. Status: Accepted and implemented. This is a UI/metadata bridge, not a general-purpose messaging bus.

---

## What Was Implemented

| Component | File(s) | Status |
|---|---|---|
| `AgentBus` (Valkey pub/sub) | `packages/agent-coordination/lib/agent_bus.py` | **Live code, dormant at runtime** (`AGENT_BUS_ENABLED=false`) |
| `AgentPublisher` | same | Live code |
| `OrchestratorSubscriber` | same | Live code |
| `FallbackBus` (file-based) | same | **Active fallback** — writes to `.cognitive-os/agent-bus/` |
| `AgentBusMetrics` adapter | `lib/agent_bus_metrics.py` | Live code; bridges to MetricEvent JSONL |
| `AgentOutputBridge` | `lib/agent_output_to_bus.py` | Live code; bridges JSONL output files → Valkey |
| `agent-bus-monitor.sh` | `packages/skill-governance/hooks/agent-bus-monitor.sh` | Hook; checks Valkey connectivity on SessionStart |
| Valkey local daemon | `scripts/cos-valkey-local.sh` | Script exists; daemon **not currently running** |
| Task Panel Bridge | `hooks/_lib/task_bridge.py`, `hooks/agent-prelaunch.sh` | **Implemented and active** |
| hcom integration | `lib/hcom_bridge.py` (proposed) | **Design-only; never executed** |
| `lib/session_bus.py` (ADR-116 P1.3) | `lib/session_bus.py` (proposed) | **Design-only; never executed** |
| ADR-183 cross-session event log | `lib/cross_session_events.py` (proposed) | **Proposed today; not implemented** |
| ADR-185 audit findings queue | `lib/audit_findings.py` (proposed) | **Proposed today; not implemented** |

---

## Cross-Reference with Tonight's ADRs

| Concern | Prior design (Valkey Bus) | ADR-116 P1.3 | ADR-183 | ADR-185 | Gap |
|---|---|---|---|---|---|
| **Intra-session agent↔orchestrator** | Full Q/A + control channel | Not in scope | Not in scope | Not in scope | Covered by Valkey bus (dormant) |
| **Cross-session peer visibility** | Not in scope | File-based events.jsonl (design) | File-based cross-session-events.jsonl (proposed) | Not primary focus | ADR-183 supersedes ADR-116 P1.3 with a cleaner schema |
| **Directive / audit findings flow** | Not in scope | Not in scope | Generic events only, no severity | Typed findings + gate | ADR-185 fills a gap not covered by any prior design |
| **Bidirectional Q/A** | Full (question/answer channels) | Not in scope | Not in scope | Not in scope | Valkey bus is the only design covering real Q/A; ADR-183/185 are unidirectional (append-only) |
| **Persistence across crashes** | Ephemeral (Redis); file fallback | JSONL (durable) | JSONL (durable) | JSONL (durable) | JSONL designs are more durable than Valkey |
| **Activation cost** | Requires Valkey daemon | Zero (file only) | Zero (file only) | Zero (file only) | ADR-183/185 are lower friction to activate |

---

## Recommendation

**Move forward with ADR-183 and ADR-185.** They address tonight's concrete problem (cross-session blind spots, auditor→implementer directive gap) at zero infrastructure cost. They are file-only, append-only, and do not depend on Valkey or any daemon.

The prior Valkey bus design is **not superseded** — it operates at a different layer (intra-session, real-time, Q/A flow) and remains valuable if/when the orchestrator needs to steer a running sub-agent in real time. That activation path is: set `AGENT_BUS_ENABLED=true` + run `scripts/cos-valkey-local.sh`. No code changes needed; the implementation is complete.

The hcom integration and ADR-116 P1.3 (`lib/session_bus.py`) should be considered **superseded by ADR-183** for the cross-session layer. ADR-183's schema is a strict improvement over both.

**Hybrid summary**:
- Cross-session awareness + directive flow → ADR-183 + ADR-185 (new, implement now)
- Intra-session real-time agent steering → Valkey bus (existing, activate when needed)
- Cross-terminal multi-tool coordination → hcom (research done, integrate later if needed)

---

## Uncertainty (Trust Report)

- The operator's original recall of a "bidirectional agent communication channel" conversation may have occurred entirely in a chat session not captured in engram — engram returned no direct hit for that exact phrase. The Valkey bus design is the most likely artifact of that conversation, but confirmation requires session transcript search.
- Valkey presence is read from code and config, not runtime state. The daemon was not running at investigation time (`ps aux` returned no valkey/redis process), but this investigation cannot determine whether it was ever run in production or only existed in design.
- ADR-183 and ADR-185 were drafted today and have no implementation yet; the cross-reference table is based on their proposed schemas, not on running code.

---

## Sources

| Source | Reference |
|---|---|
| Engram #1666 | `architecture/hcom-integration-research` — hcom deep analysis, 2026-03-28 |
| `packages/agent-coordination/lib/agent_bus.py` | Primary bidirectional bus implementation |
| `packages/agent-coordination/rules/agent-communication.md` | Channel protocol documentation |
| `lib/agent_bus_metrics.py` | Metrics adapter |
| `lib/agent_output_to_bus.py` | Output bridge |
| `packages/skill-governance/hooks/agent-bus-monitor.sh` | SessionStart hook |
| `scripts/cos-valkey-local.sh` | Valkey local daemon script |
| `cognitive-os.yaml` lines 449–474 | Valkey `on_demand` config, env vars |
| `docs/adrs/ADR-042-valkey-local-daemon.md` | Valkey extraction from Docker |
| `docs/adrs/ADR-024-task-panel-bridge.md` | First "bidirectional adapter" (UI scope) |
| `docs/adrs/ADR-116-multi-session-coordination-primitives.md` lines 75–96 | P1.3 inter-session pub/sub (design-only) |
| `docs/adrs/ADR-183-cross-session-event-log.md` | Tonight's cross-session event log proposal |
| `docs/adrs/ADR-185-cross-agent-audit-findings.md` | Tonight's audit findings queue proposal |
