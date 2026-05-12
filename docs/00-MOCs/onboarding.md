# MOC: Onboarding

You (human or agent) are new to this project. Start here.

## For humans

1. **Read first**: [`docs/00-MOCs/entrypoints/HOW-TO-USE-COS.md`](../HOW-TO-USE-COS.md) — single-page intro
2. **Then**: [`docs/05-Methodology/getting-started/`](../getting-started/) — guided setup
3. **Then**: [`docs/05-Methodology/onboarding/`](../onboarding/) — deeper orientation
4. **Reference**: [`docs/04-Concepts/architecture.md`](../architecture.md) + [`docs/00-MOCs/entrypoints/INDEX.md`](../INDEX.md) (the flat catalogue)

## For AI agents (Claude Code, Cursor, Aider, etc.)

1. **Read first**: [`docs/00-MOCs/entrypoints/AGENTS.md`](../AGENTS.md) — task-to-doc routing table, canonical glossary, what NOT to read
2. **Project rules**: [`rules/RULES-COMPACT.md`](../../rules/RULES-COMPACT.md) — compressed index of all governance rules
3. **Active phase**: check `cognitive-os.yaml` for current phase (e.g. `reconstruction` allows rewrites; `production` is stricter)
4. **Memory protocol**: see CLAUDE.md "Engram Persistent Memory Protocol" section — save decisions/bugs/discoveries proactively

## Vocabulary you'll need

| Term | Meaning |
|---|---|
| **COS** | Cognitive OS — this project |
| **ADR** | Architecture Decision Record (in `docs/02-Decisions/adrs/`) |
| **Primitive** | Atomic agentic capability (hook, rule, skill, lib, MCP). See [ADR-009](../adrs/ADR-009-package-architecture.md). |
| **Harness** | Claude Code, Cursor, Aider, etc. — the runtime executing the agent |
| **SDD** | Spec-Driven Development pipeline |
| **SCOPE** | A marker on artifacts: `os-only`, `project`, or `both`. `both` requires a portability test. |
| **MOC** | Map of Content — a curated entrypoint (you're reading one) |
| **Engram** | The persistent memory MCP system |

More terms in [`docs/00-MOCs/entrypoints/AGENTS.md`](../AGENTS.md).

## Project background

- [ADR-007 Cognitive OS rebrand](../adrs/ADR-007-cognitive-os-rebrand.md) — why "Cognitive OS"
- [ADR-008 Multi-tool support](../adrs/ADR-008-multi-tool-support.md) — why not Claude-only
- [`docs/08-References/business/`](../business/) — vision and roadmap
- [`docs/08-References/business/master-plan-checklist.md`](../business/master-plan-checklist.md) — current high-level plan

## Setup

- [`docs/05-Methodology/setup/`](../setup/) — local installation
- [`docs/08-References/integrations/`](../integrations/) — integrating with external services (Engram, MCP, etc.)
- Pre-commit hooks: enforced by `.claude/settings.json` (generated — edit `scripts/apply-efficiency-profile.sh`, not the JSON directly)

## Common first tasks

- **Read an ADR**: `docs/02-Decisions/adrs/ADR-NNN-slug.md` — start with the INDEX
- **Run tests**: `bash scripts/cos-test focused` (lane-scoped) or `pytest tests/audit/ -x`
- **Write an ADR**: copy structure from the most recent in `docs/02-Decisions/adrs/`, increment NNN
- **Add a skill**: see the `skill-creator` skill + [`docs/07-Capabilities/skills/`](../skills/)
- **Add a hook**: register it in `scripts/apply-efficiency-profile.sh` (lean/standard/full profiles)

## Related MOCs

- [decisions.md](decisions.md) — the ADRs that shape everything
- [workflow.md](workflow.md) — how multi-step processes work
- [architecture.md](architecture.md) — where things live in the tree

Last updated: 2026-05-12
