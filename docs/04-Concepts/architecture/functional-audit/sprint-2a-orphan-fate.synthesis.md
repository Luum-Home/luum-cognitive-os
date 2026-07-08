---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/sprint-2a-orphan-fate.md
provenance: "Follow-up sprint deciding and executing the fate of orphan squads, agents, and aspirational rules identified by the Capa-3 scorecards (scorecard-rules.md, scorecard-packages-squads-agents.md)."
---

## What it is

Executed cleanup sprint (not just a proposal) that archives orphan squad YAMLs and agent MDs, relocates declarative-only rules out of `rules/`, and extends the sub-agent mandatory-rules template — reducing the "aspirational rules" pool.

## Key mechanics

- Squads: kept `organization.yaml` (used as the `/cognitive-os-init` template, preserves the `>=1 squad` test invariant); archived `infra-team.yaml`, `mobile-team.yaml`, `payments-team.yaml`, `platform-team.yaml` to `packages/_archived/squads/` (broken `testing-patterns` skill ref + broken agentRefs). Removed their now-stale `.cognitive-os/squads/*.yaml` symlinks.
- Agents: kept `test-coverage-enforcer.md` (most structured frontmatter, referenced by squad templates); archived `service-health-checker.md` and `stack-validator.md` to `.claude/agents/_archived/`.
- Rules: moved 7 declarative-only rules to `docs/04-Concepts/patterns/` — `plan-first.md`, `dogfooding.md`, `os-vs-project.md`, `ecosystem-tools.md`, `component-classification.md`, `cognitive-os-changes.md`, `library-selection.md`. Added `rules/ROADMAP.md` tracking the 8 hook-enforced-BROKEN rules + 2 remaining code-dead refs. Extended `templates/agent-mandatory-rules.md` with a new section naming 9 critical agent-instruction rules by name: `acceptance-criteria.md`, `trust-score.md`, `adversarial-review.md`, `definition-of-done.md`, `phase-aware-agents.md`, `agent-quality.md`, `responsiveness.md`, `agent-output-reading.md`, `model-directive.md`.
- Aspirational-rules delta: dropped from 33 (8 broken + 19 declarative + 6 code-dead) to 22 (8 tracked-in-ROADMAP + 12 declarative + 2 code-dead) — a 33% reduction via relocation/tracking alone, without touching hook registration.
- Active `rules/` file count: 107 -> 102 (106 behavioral minus 7 moved, plus `ROADMAP.md` and the pre-existing `RULES-COMPACT.md`).
- Explicitly out of scope (deferred to future sprints): registering the 8 broken hooks, cleaning stale `EXCLUDED_RULES` entries in `hooks/self-install.sh`, building the 2 remaining missing hooks (`response-length-check.sh`, `context-budget.sh`), untangling the 52 agent-instruction-only rules.

## Relations & where used

Built directly on findings from `scorecard-rules.md` and `scorecard-packages-squads-agents.md`. Produces `rules/ROADMAP.md` and `docs/04-Concepts/patterns/`.

## Status / caveats

Executed (file inventory of created/moved/modified files included in the source doc). Baseline test run before the sprint: 55 failed / 216 passed / 54 skipped; sprint goal was no new failures, but the actual post-sprint re-run number was not captured in this doc.
