<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Hcom -- Cross-Terminal Agent Communication

## Overview
Hcom (claude-hook-comms) is an optional cross-terminal messaging layer for coordinating multiple Claude Code sessions working on the same project. Uses SQLite + TCP for instant message delivery with file collision detection.

## Installation
```bash
pip install hcom
# or
cargo install hcom
```

## Configuration
Enable in `cognitive-os.yaml`:
```yaml
agent_communication:
  hcom:
    enabled: false  # Set to true after installing hcom
    collision_detection: true
    collision_window_seconds: 30
```

## Usage
When enabled, wrap Claude Code with hcom for cross-terminal features:
```bash
hcom claude  # Instead of just: claude
```

## How It Complements the Valkey Bus
| Scope | Tool |
|---|---|
| Intra-session (sub-agents) | Valkey pub/sub (existing) |
| Cross-terminal (multiple sessions) | hcom (new) |
| Cross-device (remote) | hcom MQTT relay (optional) |

## Graceful Degradation
If hcom is not installed, the system operates normally. Cross-terminal features are simply unavailable. The Valkey bus handles all intra-session communication regardless.

## Integration with Session Concurrency

Hcom complements the existing session concurrency system (`rules/session-concurrency.md`):

| Feature | Session Concurrency | Hcom |
|---------|---------------------|------|
| File locking | Advisory locks via lock files | Real-time collision detection |
| Communication | None (isolated sessions) | Cross-terminal messaging |
| Coordination | Manual (check active-sessions.json) | Automatic (instant notifications) |

## Contextual Trigger

This rule is loaded when: hcom, cross-terminal, terminal communication, collision detection, claude-hook-comms.
