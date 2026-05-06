<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Agent Communication Bus Protocol

## Overview

The Agent Communication Bus provides bidirectional communication between agents and the orchestrator. It has two transport tiers:

1. **Valkey pub/sub** when `AGENT_BUS_ENABLED=true`.
2. **Filesystem fallback** under `.cognitive-os/agent-bus/{agent_id}/` when Valkey is disabled or unavailable.

Agent-to-orchestrator telemetry is live through heartbeats, state snapshots, and event JSONL. Orchestrator-to-agent control is governed by the `/agent-control` skill, `scripts/orchestrator.py`, filesystem interrupt sentinels, and hook-boundary enforcement.

## Activation

Valkey is **OFF by default**. Enable it only for profiles that provision Valkey:

```bash
export AGENT_BUS_ENABLED=true
```

When Valkey is disabled, control and clarification paths still write durable fallback artifacts. They are not silent no-ops unless both Valkey and filesystem I/O fail.

## Channel and Artifact Naming

Valkey channels use the prefix `cos:agent`:

| Channel Pattern | Publisher | Subscriber | Purpose |
|----------------|-----------|------------|---------|
| `cos:agent:{id}:heartbeat` | Agent | Orchestrator | Alive signal every 5s |
| `cos:agent:{id}:progress` | Agent | Orchestrator | Tool use notifications |
| `cos:agent:{id}:question` | Agent | Orchestrator | Clarification requests |
| `cos:agent:{id}:answer` | Orchestrator | Agent | Answers to questions |
| `cos:agent:{id}:control` | Orchestrator | Agent | Commands: `stop`, `pause`, `resume` |
| `cos:agent:*:heartbeat` | -- | Orchestrator | Pattern subscription for all heartbeats |

Filesystem fallback uses matching local artifacts:

| Artifact | Writer | Reader | Purpose |
|----------|--------|--------|---------|
| `.cognitive-os/agent-bus/{id}/heartbeat.jsonl` | Agent | Orchestrator | Durable heartbeat stream |
| `.cognitive-os/agent-bus/{id}/events.jsonl` | Agent | Orchestrator | ADR-183 event stream |
| `.cognitive-os/agent-bus/{id}/control.jsonl` | Orchestrator | Agent/hooks | Control command queue |
| `.cognitive-os/agent-bus/{id}/answer.jsonl` | Orchestrator | Agent/adapters | Clarification answers |
| `.cognitive-os/agent-bus/{id}/interrupt` | Orchestrator | Hook/runtime | Latest hard control sentinel |

Agent IDs are sanitized: only alphanumeric characters, hyphens, underscores, and dots are allowed. Other characters are replaced with underscores.

## Heartbeat Protocol

- **Interval**: every 5 seconds when a heartbeat loop is active.
- **Timeout**: agent considered stale after the orchestrator's selected max age.
- **Payload**: `{type, agent_id, phase, step, tokens_used, alive, timestamp}`.
- **Final heartbeat**: agents publish `alive: false` on graceful stop when the harness supports it.
- **Snapshots**: `lib/state_heartbeat.py` and native heartbeat hooks persist current runtime state.

## Question/Answer Flow

When an agent needs clarification:

1. Agent publishes a question on Valkey or appends a question/event JSONL row.
2. Operator answers through the governed CLI:
   ```bash
   python3 scripts/orchestrator.py answer <agent_id> "answer text" --round <n>
   ```
3. The answer is published to `cos:agent:{id}:answer` or appended to `answer.jsonl`.
4. Harness adapters surface the answer as `inbound_signal`; runtime loops consume it as blocking or non-blocking clarification according to harness capability.

Timeouts remain harness-specific. On timeout, agents should proceed with an explicit empty-answer/default decision instead of fabricating operator intent.

## Control Commands

Use `/agent-control` or the CLI directly:

```bash
python3 scripts/orchestrator.py list-live --max-age 300
python3 scripts/orchestrator.py scan-stale --max-age 300
python3 scripts/orchestrator.py control <agent_id> stop
python3 scripts/orchestrator.py control <agent_id> pause
python3 scripts/orchestrator.py control <agent_id> resume
python3 scripts/orchestrator.py kill-hung <agent_id>
```

| Command | Required behavior |
|---------|-------------------|
| `stop` | Terminate gracefully when the runtime controls a child process; otherwise surface `inbound_signal` and block at hook boundaries. |
| `pause` | Suspend work when supported; otherwise persist/surface `inbound_signal` so the runtime loop can defer execution. |
| `resume` | Resume a paused process when supported; otherwise persist/surface `inbound_signal` so the runtime loop can clear a pause decision. |

`hooks/agent-control-inbound-guard.sh` is the hook-boundary enforcement primitive for harnesses without live child-process control. It consumes pending filesystem/Valkey control state and blocks unsafe tool use when an inbound stop/pause signal is active.

## Agent-to-Agent Messaging

`lib/agent_message_bus.py` and `scripts/cos-agent-message` remain the ADR-185 store-and-forward queue for peer messages such as `audit_finding`, `implementation_request`, `question`, `reply`, and `status`. This path is asynchronous JSONL with `flock`; it is not real-time peer-to-peer. Its lifecycle is pending sunset once `/agent-control` plus cosd directed queues cover equivalent acknowledgement, replay, and gate behavior.

## Graceful Degradation

When Valkey is unavailable:

- Control commands append `control.jsonl` and update the `interrupt` sentinel.
- Clarification answers append `answer.jsonl`.
- Harness adapters expose queued records as `inbound_signal`.
- Hook-boundary guards enforce stop/pause/resume for projected hooks.
- Failures to write fallback artifacts must be logged; commands must not claim delivery without evidence.

## Message Size Limits

Messages are capped at 256KB. Larger messages have their `content` field truncated with a `...[truncated]` suffix.

## Integration Points

| Agentic primitive | Integration |
|-------------------|-------------|
| `scripts/orchestrator.py` | Operator CLI for `list-live`, `scan-stale`, `kill-hung`, `control`, and `answer`. |
| `packages/agent-coordination/lib/agent_bus.py` | Valkey transport plus filesystem interrupt/control/answer fallback. |
| `hooks/agent-control-inbound-guard.sh` | PreToolUse boundary enforcement for inbound stop/pause/resume. |
| `packages/agent-lifecycle/lib/harness_adapter/base.py` | Surfaces pending controls and answers as `inbound_signal`. |
| `lib/state_heartbeat.py` | Publishes and reads heartbeat snapshots. |
| `agent-bus-monitor.sh` | SessionStart advisory check for Valkey connectivity and active agents. |
| `agent_dashboard.py` | Terminal UI for live and fallback status inspection. |
| `/agent-control` | Skill-routed operator workflow for natural-language control requests. |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_BUS_ENABLED` | `false` | Enable Valkey pub/sub transport. |
| `VALKEY_HOST` | `localhost` | Valkey server host. |
| `VALKEY_PORT` | `6379` | Valkey server port. |

## Running the Dashboard

```bash
python lib/agent_dashboard.py
python lib/agent_dashboard.py --url redis://valkey:6379
python lib/agent_dashboard.py --refresh 2
```

## Contextual Trigger

This rule is loaded when: agent bus, heartbeat, agent monitoring, bidirectional communication, Valkey, pub/sub, filesystem interrupt, inbound_signal, stop agent, pause agent, resume agent, answer agent, kill hung agent.
