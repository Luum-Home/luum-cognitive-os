---
type: methodology-synthesis
source: docs/05-Methodology/root/skills.md
provenance: "Documents the skill system's organization, current project skills, auto-detection/auto-improvement flows, and how to create a new skill."
---

## What it is

An overview of Skills — structured `SKILL.md` markdown files providing domain-specific knowledge/conventions, living project-level (`.claude/skills/`, highest priority) or globally (`~/.claude/skills/`, cross-project). Covers organization, the current roster of project skills, the two feedback flows (auto-detection of gaps, auto-improvement from failures), and skill-creation procedure.

## Key mechanics

- **Priority order** (from `skill-registry-protocol.md`): project skills > global skills > auto-generated skills (lowest priority, safely regenerable).
- **Directory layout example**: project skills (typescript-patterns, nestjs-patterns, clean-arch-patterns, testing-patterns, daily-health-check); global skills (the full `sdd-*` family, skill-creator, openspec, go-testing) plus a `_shared/` convention directory (engram-convention, persistence-contract, openspec-convention).
- **7 current project skills documented**: typescript-patterns (strict mode, Zod/class-validator, no `any`, `as const` over enums), nestjs-patterns (module-per-domain, conditional providers, global AuthGuard with `@Public()`), clean-arch-patterns (Domain never imports Infrastructure/Presentation, use cases return DTOs), testing-patterns (per-stack conventions: Jest for NestJS/Express, WireMock+TestContainers for Spring, table-driven+testify for Go), daily-health-check (Docker + HTTP health + infra probes, schedulable), repair-status (auto-repair health/stats), metrics-calibrator (KPI-driven threshold auto-calibration), conversation-memory (semantic search over past sessions), tool-discovery (GitHub tool scanning + license-compatibility evaluation).
- **Auto-Detection Flow**: SessionStart -> `stack-detector.sh` writes `.claude/detected-stack.json` -> `skill-auto-loader` rule maps each detected tech to an expected skill -> if missing, prompts the user (Spanish example: "Detecte {tech} pero no hay skill. Queres que lo genere?") -> on approval, `skill-creator` uses Context7 for current library docs and registers the new skill in Engram.
- **Auto-Improvement Flow**: skill fails -> `skill-feedback-tracker.sh` hook detects failure (exit code or error keywords) -> saves to Engram under `skill-feedback/{skill-name}` -> next run, `skill-adaptation` rule reads past failures and adapts execution -> after 3+ failures, `skill-adaptation` announces the pattern and invokes `/skill-creator` to rewrite the `SKILL.md`.
- **Skill creation**: via `/skill-creator` (recommended, auto-generates frontmatter + registry update) or manually (create `.claude/skills/{name}/SKILL.md` with `name`/`description`/`version`/`last-updated`/`auto-generated`/`tech` frontmatter, add tech mapping to `skill-auto-loader.md` if applicable, run `/skill-registry`). Skills should stay under 100 lines for context efficiency.

## Relations & where used

- Directly mirrors `rules.md`'s Skill Adaptation (#4), Skill Auto-Loader (#5), and Skill Registry Protocol (#6) rule summaries — same layer diagram (Registry -> Engram -> Hooks -> skill-creator), same 3-failure threshold, same priority order.
- The Auto-Improvement Flow's `skill-feedback-tracker.sh` step matches the hook deep-dive in `hooks.md` (same Engram topic-key format `skill-feedback/{skill-name}`, same failure-keyword detection logic, same `localhost:7437` Engram port).
- `stack-detector.sh` detection logic referenced here (package.json, tsconfig.json, build.gradle, go.mod) matches the detailed detection table in `hooks.md`'s Stack Detector deep-dive.

## Status / caveats

- Technology-to-skill mapping table lists spring_boot, express, react_native, golang, solidity, docker as "Pending" (not yet built) alongside typescript/nestjs/clean_architecture/jest as "Exists" — a point-in-time snapshot of skill coverage that will drift as more are generated.
- No internal inconsistencies found; consistent with `hooks.md` and `rules.md` on shared mechanisms (skill-feedback-tracker, skill-adaptation, stack-detector).
