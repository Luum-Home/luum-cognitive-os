---
type: methodology-synthesis
source: docs/05-Methodology/root/automation.md
provenance: "Documents how the session lifecycle, CI/CD workflows, scheduled tasks, and the experimental Agent Teams / SDD pipeline automate work end to end."
---

## What it is

An overview of automation surfaces in Cognitive OS: the automated session lifecycle (start/during/end), two GitHub Actions workflows (PR review, issue triage), scheduled-task support via `mcp__scheduled-tasks`, and the experimental Agent Teams orchestrator pattern including the SDD (Spec-Driven Development) pipeline.

## Key mechanics

- **Session lifecycle**: SessionStart runs `stack-detector.sh` (writes `.claude/detected-stack.json`), loads rules from `.claude/rules/`, loads Engram context (`mem_context`), and runs `skill-auto-loader` to flag missing skills. During the session, `block-prod-urls.sh` gates Bash, `auto-test-on-edit.sh` fires after Edit/Write, `skill-feedback-tracker.sh` fires after Agent/Skill use. Session end mandates `mem_session_summary`.
- **CI/CD**: `claude-pr-review.yml` (triggers on PR open/sync or `@claude` comment; runs claude-sonnet-4-6, max 10 turns; reviews architecture, mocks, security, quality; requires `ANTHROPIC_API_KEY` secret). `claude-issue-triage.yml` (triggers on issue open; runs claude-sonnet-4-6, max 5 turns; labels by service/type/priority).
- **Scheduled tasks**: `create_scheduled_task` tool supports `cronExpression` (recurring) or `fireAt` (one-time, ISO 8601). Example: `daily-health-check` skill scheduled `0 9 * * 1-5`.
- **Agent Teams (experimental)**: enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `settings.local.json`. Orchestrator never reads/writes code directly, delegates via async `delegate` (or sync `task` only when result is immediately needed), resolves skill paths once per session, and each sub-agent saves discoveries to Engram.
- **SDD workflow**: `/sdd-new` chains `sdd-explore -> sdd-propose -> sdd-spec -> sdd-tasks -> sdd-apply -> sdd-verify -> sdd-archive` (with `sdd-design` branching off `sdd-propose`). Each phase reads/writes Engram topic keys `planning/{change-name}/{phase}` and returns status/executive_summary/artifacts/next_recommended/risks.
- **Task scaling** (from control-manifest): trivial (direct) -> small (`/opsx:propose`) -> medium (`/opsx:propose` then `/opsx:apply`) -> large (`/sdd-new` -> `/sdd-ff` -> `/sdd-apply`) -> critical (`/sdd-new` with mandatory `/sdd-verify`).

## Relations & where used

- Overlaps heavily with `hooks.md` (hook names referenced here match the hook inventory there) and with `rules.md`/`rules-consolidation-plan.md` for the rules loaded at SessionStart.
- The SDD phase chain here matches the SDD workflow described in the global orchestrator instructions (propose→specs→tasks→apply/verify→archive, with design branching off proposal).
- CI workflow file paths (`claude-pr-review.yml`, `claude-issue-triage.yml`) are also referenced from `configurable-quality-gates.md` (Layer 3 GitHub Action enforcement).

## Status / caveats

- Describes Agent Teams as **experimental**, gated behind an explicit env var — not default behavior.
- Task-scaling terminology (`/opsx:propose`, `/opsx:apply`) differs from the `/sdd-*` command family used elsewhere in this same document and in the global orchestrator rules; the source does not reconcile these two command namespaces, so readers should treat `/opsx:*` as a separate/older scaling shorthand rather than a typo.
- CI service/label examples (`service:mobile-app`, `service:example-bff`, etc.) reference a specific downstream project's service topology, not a generic Cognitive OS default.
