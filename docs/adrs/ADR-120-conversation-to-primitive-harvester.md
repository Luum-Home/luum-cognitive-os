# ADR-120: Conversation-to-Primitive Harvester

## Status

Accepted — 2026-05-02

## Context

Several high-value Cognitive OS improvements began as conversation recipes: a
safe preserved-WIP cleanup sequence, staged-blob commit gate hardening, plugin
submodule observation, and session filesystem reaping. The risk is that these
recipes remain in chat history instead of becoming durable, portable, tested
agentic primitives.

At the same time, not every conversation should become code. Some conversations
are ordinary preference notes, some are documentation-only decisions, and some
already map to existing skills or scripts. Creating duplicate primitives would
increase maintenance cost and confuse agents.

## Decision

Add an advisory **Conversation-to-Primitive Harvester** that classifies a
conversation into one of five outcomes:

1. `CREATE_PRIMITIVE` — create a new skill/script/hook/docs/tests bundle.
2. `IMPROVE_EXISTING` — extend a matching existing primitive instead of creating
   a duplicate.
3. `USE_EXISTING` — invoke an existing primitive without new artifacts.
4. `DOCUMENT_ONLY` — write ADR/docs but no executable primitive.
5. `DISCARD` — keep as ordinary conversation or memory learning.

The harvester must be deterministic, local, and non-mutating. It emits a JSON
plan with candidate name, primitive type, existing match, risks, artifact plan,
validation plan, and next action. It does not create files by itself.

## Promotion Rule

A conversation may be promoted only when it is:

```text
repeatable + risky/valuable + verifiable + portable
```

If a matching primitive already exists, the default is to use or improve it.

## Consequences

- Agents get a repeatable way to decide whether conversation content should
  become durable infrastructure.
- Duplicate primitive creation is reduced by matching against existing skills,
  scripts, and hooks.
- Documentation-only decisions remain documentation-only.
- Low-signal conversations are explicitly discarded.
- Future automation can wrap the harvester, but repository mutation remains
  governed by normal review, tests, and merge queue.

## Alternatives Considered

- **Manual judgment only**: rejected because recent cleanup work proved manual
  recipes are easy to lose and hard to audit later.
- **Always generate a skill**: rejected because it would create duplicate or
  low-value skills from ordinary chat.
- **Fully autonomous generation and commit**: rejected for now because primitive
  creation can affect hooks, Git state, or cleanup behavior and must stay behind
  validation and governed landing.

## Validation

- Behavior tests cover create, improve-existing, use-existing, documentation-only,
  and discard decisions.
- Discard tests cover low-signal and ambiguous-preference conversations.
- Portability tests cover use in a consumer-style repo and malformed invocation.
