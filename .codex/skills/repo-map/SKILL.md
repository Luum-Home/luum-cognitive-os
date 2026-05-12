---
name: repo-map
description: Compact map of the Cognitive OS codebase. Use when a task needs quick orientation without re-reading the whole repository.
version: 1.0.0
audience: both
tags: [navigation, architecture, orientation]
---

# Repo Map

## Trigger

Use when work starts in an unfamiliar area of the repository and fast orientation matters more than exhaustive exploration.

## Core Map

- `hooks/` — lifecycle enforcement and runtime hook behavior
- `hooks/_lib/` — shared shell runtime helpers
- `lib/` — Python runtime, routing, portability, metrics, config loading
- `pkg/hook/` — canonical Go hook context model
- `internal/provider/` — provider adapters and normalization
- `cmd/cos/` — Go package manager, installer, wizard
- `scripts/` — bootstrap, projection, migration, validation
- `docs/08-References/business/` — product, wedge, messaging, master plan
- `docs/04-Concepts/architecture/` — portability, boundaries, audits, ADR-adjacent implementation docs

## Stable Decision Anchors

- `docs/08-References/business/durable-product-master-plan.md`
- `docs/08-References/business/feature-reality-audit.md`
- `docs/04-Concepts/architecture/bootstrap-portability.md`
- `docs/04-Concepts/root/model-evolution-resilience.md`
- `docs/04-Concepts/root/kernel-contract.md`

## Working Rule

Read only the smallest set of files needed to answer:

1. Is this core runtime, driver projection, optional package, or future architecture?
2. Which one or two files actually enforce the behavior?
3. Which tests verify that slice?
