<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Agent Communication Bus Protocol

## Overview

The Agent Communication Bus provides bidirectional real-time communication between agents and the orchestrator using Valkey (Redis-compatible) pub/sub. It enables heartbeat monitoring, progress tracking, clarification flows, and control commands.

## Activation

The bus is **OFF by default**. Enable via environment variable:

```bash
export AGENT_BUS_ENABLED=true
```

When enabled, agents with an `agent_id` parameter automatically publish heartbeats and progress events. When disabled, all bus operations are silent no-ops.

## Channel Naming Convention

All channels use the prefix `cos:agent` (Cognitive OS Agent):

| Channel Pattern | Publisher | Subscriber | Purpose |
|----------------|-----------|------------|---------|
| `cos:agent:{id}:heartbeat` | Agent | Orchestrator | Alive signal every 5s |
| `cos:agent:{id}:progress` | Agent | Orchestrator | Tool use notifications |
| `cos:agent:{id}:question` | Agent | Orchestrator | Clarification requests |
| `cos:agent:{id}:answer` | Orchestrator | Agent | Answers to questions |
| `cos:agent:{id}:control` | Orchestrator | Agent | Commands (stop/pause/resume) |
| `cos:agent:*:heartbeat` | -- | Orchestrator | Pattern sub for all heartbeats |

Agent IDs are sanitized: only alphanumeric, hyphens, underscores, and dots are allowed. Other characters are replaced with underscores.

## Heartbeat Protocol

- **Interval**: Every 5 seconds
- **Timeout**: Agent considered dead after 15 seconds without heartbeat
- **Payload**: `{type, agent_id, phase, step, tokens_used, alive, timestamp}`
- **Final heartbeat**: On stop, agents publish `alive: false`
- **Background thread**: `start_heartbeat_thread()` runs automatically when `agent_id` is set

### Agent States

| State | Condition |
|-------|-----------|
| Active | Heartbeat received within last 15s, `alive: true` |
| Slow | Heartbeat received 10-15s ago |
| Lost | No heartbeat for 15s+ |
| Dead | `alive: false` in last heartbeat |

## Question/Answer Flow

When an agent needs clarification:

1. Agent publishes to `cos:agent:{id}:question` with `{questions: [...], round: N}`
2. Orchestrator (or dashboard) receives the question via callback
3. Orchestrator publishes answer to `cos:agent:{id}:answer` with `{answers: [...], round: N}`
4. Agent receives answer and continues

Timeout: 300 seconds by default. On timeout, agent receives empty answer list.

## Control Commands

The orchestrator can send commands to agents via `cos:agent:{id}:control`:

| Command | Effect |
|---------|--------|
| `stop` | Agent should terminate gracefully |
| `pause` | Agent should suspend work (future) |
| `resume` | Agent should resume work (future) |

## Graceful Degradation

When Valkey is unavailable, the bus falls back to file-based signaling:

- Events are written to `.cognitive-os/agent-bus/{agent_id}/{channel}.jsonl`
- One JSON object per line (JSONL format)
- File fallback supports publish and read operations
- All methods are no-ops when both Valkey and file I/O fail (log warning, no crash)
- On Valkey reconnection, the bus automatically switches back to pub/sub

## Message Size Limits

Messages are capped at 256KB. Larger messages have their `content` field truncated with a `...[truncated]` suffix.

## Integration Points

| Component | Integration |
|-----------|-------------|
| `ClaudeExecutor` | Accepts `agent_id` param; auto-starts heartbeat, publishes progress on tool use |
| `agent-bus-monitor.sh` | SessionStart hook; checks Valkey connectivity, reports active agents |
| `agent_dashboard.py` | Terminal UI subscribing to all events; shows agent status in real-time |
| `OrchestratorSubscriber` | Used by orchestrator to monitor agents, answer questions, send controls |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_BUS_ENABLED` | `false` | Enable/disable the bus |
| `VALKEY_HOST` | `localhost` | Valkey server host |
| `VALKEY_PORT` | `6379` | Valkey server port |

## Running the Dashboard

```bash
python lib/agent_dashboard.py
python lib/agent_dashboard.py --url redis://valkey:6379
python lib/agent_dashboard.py --refresh 2
```

## Contextual Trigger

This rule is loaded when: agent bus, heartbeat, agent monitoring, real-time communication, Valkey, pub/sub.
