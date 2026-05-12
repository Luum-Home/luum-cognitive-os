# Infrastructure Intent Detector

## Overview

The Infrastructure Intent Detector is a PreToolUse hook that runs before Agent/task/delegate tool calls. It scans the agent's prompt for infrastructure-related keywords and suggests matching components from the project stack.

## How It Works

1. The hook intercepts Agent tool calls via the PreToolUse hook mechanism
2. It extracts the prompt/task description from the tool input JSON
3. It scans against 7 keyword categories (database, auth, real-time, storage, queue, cache, search)
4. If matches are found, it outputs advisory suggestions to stderr
5. All detections are logged to `.cognitive-os/metrics/infra-detections.jsonl`

## Hook Location

```
hooks/infra-intent-detector.sh
```

Registered in `.claude/settings.json` under `PreToolUse` with matcher `Agent`.

## Keyword Categories

See `.cognitive-os/rules/infra-intent.md` for the complete keyword-to-infrastructure mapping table.

### Summary

| Category | Existing in Stack? | Primary Component |
|----------|-------------------|-------------------|
| Database | Yes | MySQL (3306), MongoDB (27017, 27018) |
| Auth | Yes | auth-provider (8070), example-auth (8090) |
| Real-time | No | Suggest Socket.IO + Redis |
| Storage | Partial | GCS in prod, no local mock |
| Queue | Yes | RabbitMQ (5672), Bull (Redis) |
| Cache | Yes | Redis (6379) |
| Search | No | Suggest MongoDB text indexes or dedicated engine |

## Metrics

Detections are logged in JSONL format:

```json
{
  "timestamp": "2026-03-22T10:30:00Z",
  "intents": ["database", "auth"],
  "prompt_preview": "create a user registration flow that stores..."
}
```

File: `.cognitive-os/metrics/infra-detections.jsonl`

## Configuration

The hook requires no configuration. It reads from stdin (Claude hook protocol) and uses `jq` for JSON parsing.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_PROJECT_DIR` | Auto-detected from script location | Project root directory |

## Extending

To add new infrastructure categories, follow the instructions in `.cognitive-os/rules/infra-intent.md` under "Adding New Categories".
