---
name: docs-to-artifact
description: Convert important reasoning into durable repository artifacts. Use when an analysis, diagnosis, tradeoff, or decision should outlive the conversation.
version: 1.0.0
audience: both
tags: [documentation, decisions, process]
---

# Docs To Artifact

## Trigger

Use when a conversation produces any of the following:

- a product diagnosis
- a portability conclusion
- a focus or wedge decision
- a taxonomy
- a checklist
- a testing or verification doctrine

## Placement Rules

- `docs/08-References/business/` — product strategy, wedge, risk, messaging, feature audits
- `docs/04-Concepts/architecture/` — technical boundaries, portability, driver layers, runtime decisions
- `docs/02-Decisions/adrs/` — durable architectural decisions with alternatives and consequences
- `docs/09-Quality/manual-tests/` — explicit human verification flows
- tests/contracts — when the document should become enforceable

## Operating Rule

Every significant analysis should become at least one of:

- a document
- a checklist
- a contract
- a test

Prefer adding the document first, then adding enforcement when the behavior is expected to remain stable.

Durable memory should follow this order:

1. repository artifact
2. checklist or contract
3. `.codex/` compressed memory
4. MCP memory such as Engram when the tool is actually available

Never claim that memory was persisted to an MCP tool unless that tool is surfaced in the current environment.

## Completion Step

When a new artifact is created, link it from:

- `docs/00-MOCs/entrypoints/README.md`
- and, if it advances execution, `docs/08-References/business/master-plan-checklist.md`
