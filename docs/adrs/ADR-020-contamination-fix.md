---
adr: 20
title: Contamination Fix -- Remove Project-Specific Code from OS
status: accepted
implementation_status: partial
date: '2026-04-13'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
---

# ADR-020: Contamination Fix -- Remove Project-Specific Code from OS

**Date:** 2026-04-13
**Status:** Accepted
**Commits:** 57ed5cf
**Engram IDs:** 2298

## Context

During the rapid development of Cognitive OS, some agentic primitives accumulated project-specific references -- hardcoded project names, paths to specific client projects, business-specific terminology, and configuration values that assumed a particular deployment. This "contamination" violated the OS's core architectural principle: it should be a generic operating system layer that any project can adopt, not a tool tailored to one project. The contamination was discovered during stabilization (ADR-017) when agentic primitives were being audited for wiring and scope.

## Decision

Systematically remove all project-specific contamination from OS agentic primitives:

- Replace hardcoded project names with config references (`cognitive-os.yaml` lookups).
- Remove references to specific client projects, deployment environments, or business domains.
- Parameterize skills and hooks that assumed specific project context.
- Ensure all OS agentic primitives work generically across any project that installs the OS.

The three-model architecture for project consumption was documented:
- **Model A (Minimal)**: Works with any AI tool. Just rules and docs.
- **Model B (Standard)**: Requires Claude Code hooks + Engram. The standard installation.
- **Model C (Full Pipeline)**: Requires Claude CLI for subprocess invocation from Python. Most sophisticated, with per-agent MEMORY.md files to prevent cross-agent pattern contamination.

## Alternatives Considered

- **Keep project-specific code with feature flags**: Toggle per-project behavior. Rejected because it makes the OS codebase grow with each project, violating the separation principle.
- **Fork the OS per project**: Each project gets its own copy with customizations. Rejected because it prevents upstream updates and fragments maintenance.
- **Template-based customization**: Generate project-specific configurations from templates. Partially adopted -- `cognitive-os.yaml` serves as the customization surface, with templates providing defaults.

## Consequences

- All OS agentic primitives became truly generic and reusable across projects.
- The `cognitive-os.yaml` config file became the single customization surface, replacing scattered hardcoded values.
- The three consumption models provided clear documentation for how projects should integrate with the OS at different sophistication levels.
- 5 skills were parameterized (ADR-019 scope tagging commit) to read from config instead of assuming project context.
- Future contamination is prevented by the scope tagging system (ADR-019) and the agentic primitive registration hook, which validates that os-only agentic primitives do not reference project-specific paths.
