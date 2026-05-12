---
adr: 13
title: Security Stack -- 8 Layers, 32 Tools
status: accepted
implementation_status: partial
date: '2026-03-29'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Audit exact remaining implementation scope; current ADR metadata only records a generic partial/phase signal.
partial_remaining_basis: generic audit fallback
---

# ADR-013: Security Stack -- 8 Layers, 32 Tools

**Date:** 2026-03-29
**Status:** Accepted
**Commits:** e565687, c778e49, 3916f64, d3016b5
**Engram IDs:** 1776, 1777, 1778, 1781

## Context

The existing safety-mesh.md documented a 12-layer hook pipeline for internal safety checks, but it was incomplete. It covered only the internal hook chain and missed external security tools (Aguara, Semgrep AI rules), MCP security scanning, supply chain defense, and red team capabilities. The security posture needed a single source of truth that encompassed all defense layers.

## Decision

Build a comprehensive security stack organized into 8 defense layers with 32 tools total (19 active, 8 optional, 5 planned):

1. **Code Analysis**: Semgrep with AI Best Practices ruleset (58 rules for hardcoded keys, injection, MCP hooks), plus Semgrep `--config auto`.
2. **Prompt Security**: Parry (ML prompt injection scanner, MIT), Promptfoo red team (13 adversarial test cases covering injection, jailbreak, exfiltration, tool abuse, permission escalation).
3. **MCP Security**: MCP-Scan (Invariant Labs) as a SessionStart hook scanning `.claude/settings.json` MCP configs for tool poisoning and injection. Advisory only.
4. **Supply Chain**: SHA256 digest pinning on all Docker images, commit hash pinning in the cos package manager, per-file integrity checks.
5. **Runtime Safety Mesh**: Internal hook pipeline (clarification-gate, blast-radius, assumption-tracker, confidence-gate, content-policy, secret-detector).
6. **Agent Governance**: Scope-creep detector, capability levels with auto-disable, agent escalation protocol.
7. **External Tools**: Aguara + mcp-aguara integration, Trail of Bits skills (62 professional audit skills as git submodule), Garak, tero, mantis packages.
8. **Observability**: Cost tracking, error learning pipeline, metrics auto-calibration.

P0 integrations (Semgrep AI, MCP-Scan, Promptfoo) were implemented immediately. P1/P2 tools (Garak, tero, mantis) were packaged for optional installation.

## Alternatives Considered

- **Rely on a single security platform**: Tools like Snyk or SonarQube cover multiple concerns. Rejected because AI agent security has unique requirements (prompt injection, MCP poisoning, tool abuse) that no single platform addresses.
- **Build custom security tools**: Maximum integration but enormous development cost. Rejected in favor of composing best-of-breed open-source tools with thin integration hooks.
- **Security as optional add-on**: Make security opt-in. Rejected because the safety mesh hooks are the OS's core value proposition -- without them, it is just a configuration manager.

## Consequences

- `docs/04-Concepts/root/security-stack.md` became the master security document, superseding the partial safety-mesh.md.
- 72 behavior tests were created to validate security tool integrations.
- The 8-layer model provides clear responsibility boundaries, making it easy to identify gaps when new threat vectors emerge.
- The security stack influenced the hook profile system (ADR-010): the paranoid profile enables all security hooks, while minimal disables advisory-only ones.
- Every new tool evaluation now includes a security layer classification step.
