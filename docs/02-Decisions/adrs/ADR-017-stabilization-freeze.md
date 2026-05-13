---
adr: 17
title: Stabilization Freeze -- No New Features Until Wiring Complete
status: accepted
implementation_status: not-applicable
date: '2026-04-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: temporal freeze expired; preserved as historical governance record
partial_remaining: null
partial_remaining_basis: temporal freeze expired
---

# ADR-017: Stabilization Freeze -- No New Features Until Wiring Complete

**Date:** 2026-04-11
**Status:** Accepted
**Commits:** f49731d, abccc8f
**Engram IDs:** 5319, 5889

## Context

After 18 days of rapid development, the OS had accumulated 375+ agentic primitives but many were not wired into the running system. A reality audit revealed: 82 unwired libs, 17 unregistered hooks, 14 phantom skills (referenced but not present), and 292 failing tests. Each session added new agentic primitives but the wiring rate was declining. Dead code accumulated. The user declared the OS "unmanageable" -- agentic primitives were built but could not be trusted to work because there was no automated enforcement preventing unwired agentic primitives from accumulating.

## Decision

Declare a stabilization freeze: no new features until the existing system is fully wired, tested, and validated. The phase transition was from "reconstruction" to "stabilization."

**Mega plan**: 6 phases across ~10 sessions, targeting 43% wiring to 90%:
1. **Foundation**: Pre-commit hooks (ruff, vulture), automated enforcement gates.
2. **Catalog cleanup**: Remove phantom skills, dead references, orphaned configs.
3. **Critical wiring**: Connect the 82 unwired libs to their consumers.
4. **Lib triage**: Evaluate each unwired lib -- wire, archive, or delete.
5. **CI pipeline**: Automated validation on every commit.
6. **Runtime validation**: Health checks confirming agentic primitives work at runtime, not just at import time.

**Enforcement mechanisms added**:
- Wiring validator hook: detects unregistered agentic primitives at commit time.
- Registration check: BLOCKS commits with unregistered hooks (upgraded from warning to enforcement).
- Primitive usage tracker: identifies dead-weight agentic primitives.

## Alternatives Considered

- **Continue feature development with parallel stabilization**: Keeps momentum but the wiring gap widens faster than it closes. Each new feature adds agentic primitives that need wiring. Rejected as unsustainable.
- **Archive everything unwired and start clean**: Drastic but eliminates the debt. Rejected because many unwired agentic primitives are valuable -- they just need connection points.
- **Hire/assign someone to stabilization while features continue**: Not applicable to a solo developer project.


## Current Status

This ADR is obsolete-by-context as an operational freeze. It governed the April
2026 stabilization window and is preserved as historical rationale. New feature
work is no longer globally blocked by ADR-017; current work is governed by
`project.phase`, current ADRs, readiness gates, lifecycle ledgers, and narrower
freezes such as release, adoption, and compliance freezes.

ADR-017 was correct for the original growth crisis. The expired part is using it
today as a global anti-feature limit. The surviving principle is narrower: do
not add agentic primitives without lifecycle/wiring evidence, do not expand in
ways that break readiness, do not accumulate dead code, and do not bypass active
gates.

## Consequences

- Feature development stopped for multiple sessions, allowing focused stabilization work.
- Test failures dropped from 292 to single digits through systematic fix sessions.
- The enforcement gates (pre-commit, registration check) created a ratchet effect: once wired, agentic primitives cannot silently become unwired.
- The stabilization process itself generated valuable patterns: the Docker-to-pip migration (ADR-018), scope tagging (ADR-019), and contamination fix (ADR-020) all emerged as stabilization work items.
- The fundamental lesson was documented: building agentic primitives is easy, wiring them into a working system is the hard part.

> **Note:** Commits after the freeze date include `feat:` prefixes for stabilization work (scope tagging, Docker-to-pip Phase 2, audit enforcement). These are stabilization/wiring tasks, not new user-facing features. The freeze was followed in spirit — test failures dropped from 292 to 6 (commit `a06b7ef`).
