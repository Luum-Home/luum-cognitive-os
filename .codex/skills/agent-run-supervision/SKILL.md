---
name: agent-run-supervision
version: 1.0.0
description: Use when the user asks how a background agent is doing, whether it is stuck/dead, to keep monitoring it, or to produce a handoff from live git/process/WIP evidence.
audience: both
platforms:
  - codex
  - claude-code
  - opencode
  - generic-cli
platform_support:
  generic-cli:
    support_level: executable
    evidence:
      - scripts/cos-agent-run-status
      - scripts/cos-agent-watch
      - scripts/cos-progress-metric
      - scripts/cos-handoff-if-dead
      - tests/red_team/portability/test_cos_agent_supervision_primitives.py
routing_patterns:
  - pattern: (/agent-run-status|/agent-watch|\b(como venimos|status del agente|segui monitoreando|murio el agente|esta trabado|dejalo correr|how are we doing|agent status|keep monitoring|is it stuck|did the agent die|deixa rodar|como estamos|agente travado)\b)
    confidence: 0.94
routing_intents:
  - intent: agent_run_supervision_request
    description: User asks for multilingual background-agent progress/status supervision, stuck/dead detection, monitoring, or handoff evidence.
    confidence: 0.92
triggers:
  - /agent-run-status
  - /agent-watch
  - como venimos
  - cómo venimos
  - status del agente
  - seguí monitoreando
  - murió el agente?
  - está trabado?
  - dejalo correr
  - how are we doing
  - agent status
  - keep monitoring
  - is it stuck?
  - did the agent die?
  - como estamos
  - agente travado
---
<!-- SCOPE: both -->
# Agent Run Supervision

Use this skill to answer background-agent status questions with evidence instead
of vibes. It is multilingual and model-agnostic: Spanish, English, and Portuguese
triggers should route here.

## Quick commands

```bash
scripts/cos-agent-run-status --process-id <id> --json
scripts/cos-agent-watch --process-id <id> --interval 60 --max-cycles 5 --json
scripts/cos-progress-metric --process-id <id> --contract progress.yaml --json
scripts/cos-handoff-if-dead --process-id <id> --json
```

## Status states

- `active-progress`: process is alive and dirty WIP changed recently.
- `idle-but-safe`: process is alive but no fresh WIP signal is present.
- `probably-stuck`: same status repeated past the no-progress threshold.
- `dead-with-wip`: process is gone while dirty WIP remains.
- `ready-for-handoff`: no live process and no dirty WIP blocker.

## Multilingual conversational mapping

| User phrase | Action |
|---|---|
| `como venimos`, `cómo venimos`, `status del agente` | Run `cos-agent-run-status --language es`. |
| `seguí monitoreando`, `dejalo correr` | Run `cos-agent-watch --language es`. |
| `murió el agente?`, `está trabado?` | Run status; if dead/stuck, run handoff. |
| `how are we doing`, `agent status` | Run `cos-agent-run-status --language en`. |
| `keep monitoring`, `let it run` | Run `cos-agent-watch --language en`. |
| `como estamos`, `agente travado`, `deixa rodar` | Run with `--language pt`. |

## Progress metric contract

```yaml
progress:
  metric: hir_residual_diff
  command: cargo run -- check-hir-parity --json
  improves_when: decreases
  stuck_after: 3
```

The metric command should be read-only or validation-only. If it emits JSON, the
metric can be selected by key; otherwise the last numeric value in stdout is used.

## Rules

- Do not say an agent is stuck only because it has not committed yet.
- Check process liveness, dirty WIP age, branch/ahead/behind, validation receipts,
  and progress metric before making a status claim.
- If the process is dead with WIP, produce a handoff instead of editing blindly.
- If there is recent dirty WIP and a live process, do not overwrite it.
- Keep answers evidence-backed and mention uncertainty when process detection is by pattern.

## Contextual Trigger

Use when the user asks: como venimos, cómo venimos, status del agente, seguí
monitoreando, murió el agente, está trabado, dejalo correr, how are we doing,
agent status, keep monitoring, is it stuck, did the agent die, como estamos, or
agente travado.
