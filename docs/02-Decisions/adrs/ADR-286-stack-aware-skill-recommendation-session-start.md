---
adr: 286
title: Stack-Aware Skill Recommendation at Session Start
status: accepted
implementation_status: implemented
classification_basis: 'implemented: ADR-286 ships session-start-stack-recommend.sh hook writing stack-recommendations.json, unit tests against a fixture project, and hook registration.'
date: 2026-05-13
supersedes: []
superseded_by: null
extends: []
implementation_files:
  - hooks/session-start-stack-recommend.sh
  - tests/unit/test_session_start_stack_recommend.py
tier: maintainer
tags: [skills, stack-detection, session-start, recommendation, ux]
---
# ADR-286: Stack-Aware Skill Recommendation at Session Start

## Status

Accepted and implemented — 2026-05-13.

<!-- SCOPE: OS -->

**Date**: 2026-05-13

## Context

`lib/stack_skill_recommender.py` implements project-level technology detection
from standard manifests (`package.json`, `go.mod`, `pyproject.toml`,
`Cargo.toml`, Gradle build files, and config files like `next.config.*`,
`tailwind.config.*`, `Dockerfile`). It maps detected technology stacks to
relevant skills with a priority ordering (recommended > optional > suggested)
and handles combo patterns such as React + TypeScript or Next.js + Supabase.

The module is fully implemented and tested in isolation but is never invoked
during normal operation. It has no wiring to any session lifecycle hook, so its
recommendations are never surfaced to operators or agents.

### Relationship to skill_router

The existing `skill_router` answers the question: *"given this user request,
which skill best handles it?"* It resolves intent from the user message at
prompt time. `StackSkillRecommender` answers a different question: *"given this
project's technology fingerprint, which skills are worth having installed?"*
It operates on filesystem evidence at session start, not on user intent.

The two are complementary:

- `skill_router` provides runtime routing for explicit requests.
- `StackSkillRecommender` provides ambient session context about skills that
  are structurally relevant to the current project before any user prompt.

There is no overlap in their resolution space. Activating both creates a richer
skill-awareness layer: agents can consult the stack recommendations file to
understand what the project needs, independent of the specific task being
requested.

### Why session start?

Stack detection is I/O bound (file stat and JSON parsing) and produces stable
output for the duration of a session — the project's package manifests do not
change while the session is running. Running at `SessionStart` once per session
amortises the cost across all subsequent tool calls and stores the result as a
state file that any hook or agent can read without repeating the scan.

## Decision

Add a `session-start-stack-recommend.sh` hook that:

1. Runs `StackSkillRecommender().recommend(project_path)` against the current
   project directory.
2. Serialises the result to `.cognitive-os/state/stack-recommendations.json`
   including a `generated_at` timestamp and the detected project path.
3. Runs asynchronously so that I/O latency (typically <50 ms; up to 200 ms on
   very large repos) does not block the session start sequence.
4. Never emits to stdout (the hook output is a side-effect file, not
   additionalContext). Errors are emitted to stderr only.
5. Is advisory only — exits 0 unconditionally, never blocks session start.

### Output schema

```json
{
  "generated_at": "2026-05-13T10:00:00+00:00",
  "project_path": "/absolute/path/to/project",
  "recommendations": [
    {
      "skill_name": "go-testing",
      "reason": "Go project detected",
      "source": "cos-builtin",
      "install_command": "/go-testing",
      "priority": "recommended"
    }
  ]
}
```

The file is written atomically (write to `.tmp` then `rename`) to avoid
partial reads by concurrent hooks.

### Consumption

The state file is not consumed by the hook framework automatically. It is
available for:

- Agents that query `.cognitive-os/state/stack-recommendations.json` to
  suggest skills to the operator.
- Future `UserPromptSubmit` hooks that surface recommendations when the user's
  first message arrives.
- CI primitives that validate expected skills are installed for the detected
  stack.

## Consequences

- **Positive**: Stack-relevant skills are surfaced automatically without
  operator effort. An agent working on a Go + Docker project will find the
  recommendations pre-computed before any prompt.
- **Positive**: The detection is purely additive — it does not modify skill
  installation state, does not block session start, and does not emit
  disruptive output.
- **Positive**: The `StackSkillRecommender` class goes from orphaned (consumed
  only by its own test) to actively producing value on every session.
- **Negative**: An additional Python subprocess is launched at session start.
  The `COS_DISABLE_STACK_RECOMMEND=1` killswitch allows opt-out.
- **Negative**: The state file can become stale if the project's manifests
  change during a long session. This is acceptable for the current use case
  (advisory only). A future iteration could trigger a refresh on
  `package.json` writes.

## Alternatives rejected

1. **UserPromptSubmit hook.** Running at first prompt is too late for agents
   that need to know the stack before the first tool call. SessionStart
   guarantees the file is available from the beginning.
2. **Inline in session-startup-protocol.sh.** That hook has a strict 500 ms
   budget and must be synchronous. Stack detection is I/O-bound and should
   run async.
3. **Trigger on demand only.** Requires every consumer to invoke the recommender
   independently, duplicating I/O and defeating the purpose of the cache file.

## Implementation

```
hooks/session-start-stack-recommend.sh   — async SessionStart wrapper
tests/unit/test_session_start_stack_recommend.py — tests against fixture project
```

Profiles that include this hook: `maintainer`, `full` (not `core`).

## Verification

```bash
python3 -m pytest tests/unit/test_session_start_stack_recommend.py -v
bash -n hooks/session-start-stack-recommend.sh
```
