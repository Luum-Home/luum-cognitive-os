---
type: reference-synthesis
source: docs/08-References/business/roadmap.md
provenance: "Public-facing living roadmap describing current state and the four-phase forward plan, so contributors and adopters share one source of truth for what exists versus what is planned."
---

## What it is

The public roadmap document for Cognitive OS: a snapshot of current capabilities plus a four-phase forward plan (open-sourcing the core, web dashboard, team features, enterprise), a risk assessment, and contribution guidance.

## Key mechanics

- **Current state table**: 176 SKILL.md files, 244 hook scripts (minimal profile requires 3), 120 rule files, 16+ agent personas, 326 ADRs, 20+ canonical manifests, a native MCP server (8 tools) plus Engram + Context7, one fintech case study (~300x acceleration claimed).
- **What works end-to-end today** (per this doc): persistent cross-session memory (Engram), multi-agent orchestration with cycle dedup and worktree isolation, replay timeline/restore-by-checkpoint via shadow-git, sync cost + retry gate, DORMANT/propose-only self-improvement loop, profile-projected quality/security gates, cost tracking with budget enforcement, DORMANT/advisory SRE repair guardrails, native MCP server, ratcheted (not universal) manifest-driven governance, and an 8-core-phase SDD workflow.
- **Phase 1 (in progress)**: extract core from project-specific code, publish under FSL-1.1-MIT, ship `cognitive-os init`/`cognitive-os.yaml`, npm/brew distribution, community infra (Discord, GitHub Discussions), and an explicit commercial-use boundary (hosted COS / managed agent runtime / orchestration SaaS reserved pre-Change-Date).
- **Phase 2 (Web Dashboard)**: agent execution dashboard, Memory Explorer, KPI dashboard, visual config editor, session history, plus a Go backend API layer.
- **Phase 3 (Team Features)**: multi-tenant cloud Engram, skill marketplace, team analytics, SSO/SAML, webhooks.
- **Phase 4 (Enterprise)**: self-hosted Docker/Helm deployment, air-gapped install, SOC 2/HIPAA compliance mode, exportable audit trails, RBAC, SLA tiers.
- **Risk table**: AI market consolidation (high severity, mitigated by proof-level portability), competitor replication (medium, mitigated by integration depth + case study), open-source sustainability (medium, SaaS-model precedent), community adoption speed (low), MCP protocol changes (low).

## Relations & where used

Cross-references `features.md` (full feature matrix), `case-study.md` (the ~300x acceleration case), `open-source-design.md` (framework/plugin architecture), and `portability-plan.md` (multi-IDE plan) as companion documents.

## Status / caveats

This is a **forward-looking planning document**, not an audit — phases 2 through 4 describe unbuilt/planned features (dashboard, cloud Engram, marketplace, enterprise compliance tooling) presented alongside a "Current State" table that mixes shipped, profile-gated, and DORMANT capabilities. Readers should not infer that everything under "What works end-to-end today" is default-on or fully proven; the companion `promise-compliance-audit-2026-05-15.md` finds several of these same claims (multi-IDE portability, manifest-driven governance "every primitive" wording, self-improvement autonomy) needed correction around the same period. Static counts (skills/hooks/rules/ADRs) are a point-in-time snapshot and will drift.
