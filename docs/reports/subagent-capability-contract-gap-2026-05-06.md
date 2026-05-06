# Subagent Capability Contract Gap — 2026-05-06

**Scope**: why read-only Explore agents were launched for tasks that required
writing markdown artifacts, and what contract prevents this from recurring.

## Short answer

The Explore agents did the safe thing: they did not write. The failure was that
the orchestrator selected a read-only agent type for prompts with durable file
artifact requirements.

This is an architecture bug, not only operator error. The subagent capability
contract existed as prose but not as a manifest/preflight.

## What happened

| Dimension | Selected / requested | Result |
|---|---|---|
| Task intent | research / exploration | Compatible with Explore |
| Output requirement | write `research/0X-*.md` | Requires write capability |
| Selected type | Explore | Cannot Write/Edit |
| Outcome | child returns `<result>`; parent persists manually | Work completes with serial recovery |

## Correct routing rule

```text
research + no file artifact required -> Explore
research + write artifact required -> general-purpose / worker
implementation -> worker / general-purpose
inspection only -> Explore
Explore + parent write -> valid only if explicitly declared
```

## Self-bite pattern

| Case | Missing executable contract |
|---|---|
| auto-pre-agent stashes | system-generated stale stashes need archive-first reaper |
| `/auto-rollback` | quoted/critiqued safety skills are not execution intent |
| private content portability | private content needs projection classes before harness/cloud sync |
| Explore agents | read-only agents cannot produce file artifacts |

## Implemented guard

ADR-203 adds:

- `manifests/subagent-capabilities.yaml`;
- `scripts/subagent_launch_preflight.py`;
- `scripts/cos subagent preflight`;
- unit coverage for blocking and parent-persistence exceptions.

## Remaining work

The preflight exists as a CLI/contract. It still needs to be wired into any
harness-native launch path that programmatically selects agent types.
