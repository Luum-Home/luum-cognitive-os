---
name: agent-control
version: 1.0.0
description: 'Use when you need this Cognitive OS skill: Send governed bidirectional
  control and clarification signals between the orchestrator and live agents.; do
  not use when a narrower skill directly matches the task.'
audience: os
scope: os
platforms:
- claude-code
- codex
- shell
prerequisites:
- Agent ID from heartbeat, list-live, scan-stale, or .cognitive-os/agent-bus.
triggers:
- stop agent
- pause agent
- resume agent
- answer agent
- kill hung agent
- list live agents
- scan stale agents
routing_patterns:
- pattern: \\b(stop|pause|resume)\\s+(the\\s+)?agent\\b
  confidence: 0.95
- pattern: \\banswer\\s+(the\\s+)?agent\\b
  confidence: 0.95
- pattern: \\bkill\\s+(-| )?hung\\s+(agent|worker)\\b
  confidence: 0.9
- pattern: \\b(list[- ]live|live agents?|scan[- ]stale|stale agents?)\\b
  confidence: 0.88
summary_line: Send governed bidirectional control and clarification signals between
  the orchestrator and live agents.
routing_intents:
- intent: agent_control_request
  description: User asks to send governed bidirectional control and clarification
    signals between the orchestrator and live agents.
  confidence: 0.85
---
<!-- SCOPE: both -->
# Agent Control

Use this skill when an operator asks to stop, pause, resume, answer, inspect, or kill a live agent. The governed entrypoint is `scripts/orchestrator.py`; it uses Valkey pub/sub when `AGENT_BUS_ENABLED=true` and writes filesystem fallback artifacts under `.cognitive-os/agent-bus/{agent_id}/` otherwise.

## 1. Identify the target agent

Prefer a live heartbeat source before sending a mutating command:

```bash
python3 scripts/orchestrator.py list-live --max-age 300
python3 scripts/orchestrator.py scan-stale --max-age 300
```

If the operator already supplied an agent ID, still check `.cognitive-os/agent-bus/{agent_id}/heartbeat.jsonl` when the command is destructive or ambiguous.

## 2. Send control signals

Use explicit verbs and echo the target in your operator response:

```bash
python3 scripts/orchestrator.py control <agent_id> stop
python3 scripts/orchestrator.py control <agent_id> pause
python3 scripts/orchestrator.py control <agent_id> resume
```

For hung agents, use the higher-level verb so the stale-agent state and stop signal stay coupled:

```bash
python3 scripts/orchestrator.py kill-hung <agent_id>
```

## 3. Send clarification answers

When an agent is waiting for clarification, preserve answer order and round number when known:

```bash
python3 scripts/orchestrator.py answer <agent_id> "use port 8080" "ship it" --round 2
```

If the round is unknown, use the default and state that the answer was sent as a best-effort fallback.

## 4. Verify delivery evidence

A successful command should leave at least one governed evidence trail:

- Valkey channel: `cos:agent:{id}:control` or `cos:agent:{id}:answer`.
- Filesystem fallback: `.cognitive-os/agent-bus/{id}/control.jsonl`, `answer.jsonl`, or `interrupt`.
- Hook-boundary enforcement: `hooks/agent-control-inbound-guard.sh` blocks or surfaces pending inbound stop/pause/resume signals between tool calls.
- Harness context: adapters expose pending controls as `inbound_signal` for runtime loops that cannot directly control a child process.

## 5. Apply harness semantics

- Child-process harnesses may apply `stop`, `pause`, and `resume` immediately.
- Harnesses without child-process control must surface `inbound_signal`; their runtime loop decides whether to block, defer, or ask the operator.
- `answer` signals are clarification data, not a process-control interrupt.
- Do not delete evidence artifacts unless the operator explicitly asks to clear a stale signal after review.

## Contextual Trigger

Load this skill when the operator says: stop agent, pause agent, resume agent, answer agent, kill hung agent, list live agents, scan stale agents, inbound signal, agent interrupt, bidirectional agent communication.
