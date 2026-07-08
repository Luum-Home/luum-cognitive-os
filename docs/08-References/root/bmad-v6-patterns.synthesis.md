---
type: reference-synthesis
source: docs/08-References/root/bmad-v6-patterns.md
provenance: "Tracks which BMAD (Build Measure Analyze Decide) METHOD v6 patterns have been reconstructed and implemented inside Cognitive OS, patterns 1-12."
---

## What it is

An implementation-status tracker for 12 BMAD v6 patterns adopted into Cognitive OS, each with status, implementing file(s), and a short rationale. All 12 are marked "Implemented."

## Key mechanics

Patterns 7-12 (documented first, with most detail):
- **Pattern 7 — HALT-and-WAIT**: agents present a plan and wait before ambiguous/high-risk tasks (multi-service changes, migrations, API contract changes, auth/security). Phase-dependent: reconstruction only halts for data-destructive ops; production halts for all ambiguous tasks. `rules/closed-loop-prompts.md`.
- **Pattern 8 — Path Segregation in Engram**: structured topic-key prefixes (`planning/`, `implementation/`, `docs/`, `agent/`, `sre/`, `architecture/`, `sprint/`, `config/`, `bugfix/`) with a migration guide from legacy flat `sdd/` keys, migrated gradually (re-save on read). `rules/engram-organization.md`.
- **Pattern 9 — Agent Customization via Override Files**: per-agent YAML overrides in `customizations/{agent-name}.yaml` with deep-merge semantics covering model, temperature, max_tokens, tools, skills, budget, phase behavior, custom instructions; survives OS updates.
- **Pattern 10 — Sprint Tracking**: lightweight agent-managed sprints via `/sprint plan|status|retro|correct`, integrating Engram (goals/retros), Agent KPIs (completion rate), and resume-tasks (incomplete stories).
- **Pattern 11 — Dual-Search Protocol for Artifacts**: three-step lookup (complete file -> sharded index+sections -> Engram topic key -> legacy key -> keyword), respecting token budgets across small and large projects.
- **Pattern 12 — Schema Validation for Skills/Agents**: `/validate-config` checks `cognitive-os.yaml`, `squads/*.yaml`, `CATALOG.md`, `RULES-COMPACT.md`, skill frontmatter, hooks, and customizations; returns PASS/WARNINGS/ERRORS.

Patterns 1-6 (described as "reconstructed" — prior placeholder text replaced with real implementations):
- **1. Adversarial Review**: every review must produce >=1 finding; "looks good" is prohibited and triggers a HALT + re-launch; 4 severity tiers (BLOCKER/CONCERN/SUGGESTION/QUESTION).
- **2. Implementation Readiness Gate**: `/readiness-check`, a 6-dimension checklist (specs, design, tasks, dependencies, mocks, tests), mandatory gate between sdd-tasks and sdd-apply, verdicts PASS/CONCERNS/FAIL.
- **3. Project-Context Auto-Loading**: `hooks/inject-phase-context.sh` injects phase, architecture standards, all 7 constitutional gates, squad assignment, and project type into every sub-agent.
- **4. Per-Agent Sidecars via Engram**: topic key `agent/{agent-name}/sidecar` stores learnings/preferences/patterns/issues; orchestrator injects on launch, agents upsert after tasks.
- **5. Step-File Architecture**: for phases >30 min or >5 actions, `step-01-{desc}.md` ... `step-XX-complete.md` with objective/inputs/actions/outputs/success criteria and Engram-backed resumption.
- **6. Enhanced sdd-continue**: inspects 4 state sources (Engram SDD topic keys, plan files, workflow state, active-tasks.json) before recommending the next phase.

A separate finding documents that `.cognitive-os/` is not filtered by any IDE/gitignore/LLM tool, so the directory naming was kept (no rename to `_cognitive-os/`).

## Relations & where used

- Cross-referenced compactly in `rules/RULES-COMPACT.md` for most patterns.
- Feeds directly into `docs/08-References/root/patterns-adopted.md` (broader external-pattern catalog) and the SDD pipeline (`sdd-propose` -> `sdd-archive`).
- Sidecar pattern (4) and dual-search protocol (11) are load-bearing for how sub-agents receive and persist context across the whole OS.

## Status / caveats

- All 12 patterns are self-reported as "Implemented" with no verification evidence embedded in this document (no test IDs, no dates) — treat status claims as asserted, not independently verified here.
- No internal date/versioning on the document itself, so currency relative to the rest of the KB rollout (dated ~2026-04-08 in sibling docs) cannot be confirmed from this file alone.
