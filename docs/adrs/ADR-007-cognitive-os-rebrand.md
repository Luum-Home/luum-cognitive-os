---
adr: 7
title: Rebrand from Agent OS to Cognitive OS
status: accepted
implementation_status: not-applicable
date: '2026-03-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted decision/policy record with no explicit implementation
  surface
---

# ADR-007: Rebrand from Agent OS to Cognitive OS

**Date:** 2026-03-24
**Status:** Accepted
**Commits:** 1a7e421 (v0.1.0 already branded as Cognitive OS)
**Engram IDs:** 1597, 1598

## Context

The project was originally called "Agent OS." As the architecture matured, it became clear that the system manages cognition (tokens, context, decisions, memory) rather than hardware or agents themselves. The name "Agent OS" positioned the product alongside coding assistants (Aider, Cursor, Codex), which are not true competitors. The system needed a name that accurately reflected its architectural role: an operating system layer for AI cognition.

## Decision

Rename the product from "Agent OS" to "Cognitive OS" (two words, capital C capital O). The rebrand applied only to prose and documentation -- all 264 references across 64 .md files were updated. Technical identifiers were intentionally NOT renamed:

- Directory paths: `.agent-os/`, `.cognitive-os/` (Note: `.agent-os/` was later renamed to `.cognitive-os/` in subsequent commits.)
- Config files: `agent-os.yaml` (later `cognitive-os.yaml`)
- Hook names and internal APIs: unchanged
- License: Apache 2.0 (unchanged)

An OS analogy table was added mapping traditional OS concepts (kernel, scheduler, memory, filesystem, drivers, syscalls, networking, self-healing, package manager, init system) to their Cognitive OS equivalents, establishing the conceptual framework.

## Alternatives Considered

- **Keep "Agent OS"**: Simpler, no migration effort. Rejected because it conflated the OS layer with the agents it manages, and invited unfair comparisons with coding tools.
- **"AI OS" or "LLM OS"**: Too generic, no differentiation. Multiple projects already use these terms.
- **Full technical rename** (directories, configs, hooks): Would break all existing installations and integrations. The prose-only approach avoided this cost entirely.

## Consequences

- The product positioning shifted from "another AI coding tool" to "an operating system for AI cognition," which is architecturally accurate and differentiating.
- Business documentation was simultaneously rewritten for open-source publication (removing pricing, revenue targets, and proprietary provider names).
- The dual naming (Cognitive OS in prose, agent-os in code) occasionally causes confusion for new contributors, but avoids breaking changes.
- All subsequent documentation, evaluations, and competitive analysis use the Cognitive OS framing.
