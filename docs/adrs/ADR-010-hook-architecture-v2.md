---
adr: 10
title: Hook Architecture v2 -- 10 Event Types, 3 Security Profiles
status: accepted
implementation_status: implemented
date: '2026-03-28'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'security profiles and hook profile scripts exist; ADR consequences describe the profile system as operational'
---

# ADR-010: Hook Architecture v2 -- 10 Event Types, 3 Security Profiles

**Date:** 2026-03-28 to 2026-04-13
**Status:** Accepted
**Commits:** e17b3ea, f0be80e, 329deb2, 86c419e
**Engram IDs:** 1789, 3191

## Context

Cognitive OS was using approximately 10% of Claude Code's hook capabilities. The initial hook architecture supported only 4 event types (PreToolUse, PostToolUse, SessionStart, Stop) with 13 hooks. All hooks were synchronous and blocking, which meant advisory hooks (that only observe and report) incurred the same latency penalty as enforcement hooks (that can block operations). There was no differentiation between security postures -- every user got the same set of hooks regardless of their risk tolerance.

## Decision

Expand the hook architecture from 4 events (13 hooks) to 10 event types with 3 security profiles:

**New event types added**:
- **SubagentStart**: Automatic preamble and sidecar injection into sub-agents, replacing manual orchestrator injection.
- **UserPromptSubmit**: Automatic prompt capture to Engram memory (async, never blocks the user).
- **PreCompact**: Automatic context save before Claude Code compaction (critical for session continuity).
- **TeammateIdle**: Triggered when a teammate agent becomes idle, enabling coordination between concurrent agents.
- **TaskCreated**: Fires when a new task is created, enabling automatic registration and tracking.
- **TaskCompleted**: Fires when a task completes, enabling post-completion actions like archiving and notifications.

**Async support**: ~23 advisory hooks marked with `async: true` to eliminate latency penalties. Only enforcement hooks (gates, blockers) remain synchronous.

> **Note:** While async execution was designed, the current settings.json does not use the `async: true` property — hooks achieve async behavior through background subprocesses (`&`) internally.

**Three security profiles**:
- **Minimal** (~11 hooks): Core enforcement only. For trusted environments or performance-sensitive workflows.
- **Standard** (~26-31 hooks): Default profile. Balances safety with usability.
- **Paranoid** (~47 hooks): Full security posture. For production, regulated, or high-risk environments.

Profiles are switched via `scripts/set-security-profile.sh` which rewrites `settings.json` from profile JSON templates.

## Alternatives Considered

- **Keep single profile, let users manually disable hooks**: Simpler implementation but poor UX. Users would need to understand each hook's purpose to make informed decisions.
- **Event-level granularity** (enable/disable events, not individual hooks): Too coarse. A user might want SubagentStart hooks but not all of them.
- **Plugin-style hook loading**: Hooks auto-discover and register themselves. Rejected because it makes the security profile non-deterministic -- you can't audit what's running without inspecting each hook file.

## Consequences

- Hook latency for standard operations dropped significantly due to async advisory hooks.
- Profile switching became a single-command operation, making it practical for users to change security posture per project.
- The profile system created a natural boundary for the rules-to-hooks migration (ADR-015) -- rules could be converted to hooks and placed in the appropriate profile tier.
- Maintaining three profile definitions (minimal, standard, paranoid) in sync with the generator script and the live settings.json proved to be an ongoing challenge, requiring multiple fix commits during stabilization.
