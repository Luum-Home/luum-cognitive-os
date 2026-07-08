---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md
provenance: "Audit date 2026-04-16, reconstruction phase: whether packages/squads/agents are actually runtime-wired or merely cataloged."
---

## What it is

Capa-3 audit of `packages/`, `squads/`, and `agents/` classifying each as integrated / standalone / orphan based on whether any runtime code actually parses or dispatches them.

## Key mechanics

- Packages: 32 total. 10 integrated via `lib/` symlinks (42 symlinks total into `packages/*/lib/*.py`, matching the project-gotchas `>40` claim). 21 standalone — self-contained skills/rules/hooks installed via `hooks/self-install.sh`'s `SYNC_DIRS`, not Python imports; there's no `pyproject.toml`/`setup.py` per package. 1 orphan: `mcp-server/` has only a `cos-package.yaml` manifest, no README/SKILL.md/skills-rules-hooks. `lib/_wiring-allowlist.txt` lists 18 modules intentionally not-yet-wired (e.g. `batch_runner`, `cognee_client`, `dynamic_tool_creator`, `webhook_trigger`) — integrated-but-dormant.
- Squads: 5 YAML files (`organization.yaml` + 4 team templates). **Zero** runtime loader/parser exists anywhere (only a string-literal "Squad Protocol" mention in `lib/repo_analyzer.py`). All 4 team YAMLs reference a `testing-patterns` skill that does not exist on disk, and agentRefs (`backend-architect`, `security-engineer`, `sre-agent`, `devops-agent`, `engineering-manager-agent`) with no physical MD file. All 4 carry template comments (`repos: []  # Add your ... repos here`) — they're intentionally per-project customization templates, not active runtime squads, consistent with `docs/04-Concepts/root/plug-and-play.md`.
- Agents: 3 MD files (`service-health-checker.md`, `stack-validator.md`, `test-coverage-enforcer.md`). Zero runtime dispatcher. `test-coverage-enforcer.md`'s `triggers:` frontmatter (glob patterns) is never parsed by any hook. Only 1 of the 6 agents named in `organization.yaml` has a physical file; conversely 2 physical agent files aren't listed in `organization.yaml` at all.
- Scoring: Integrated/runtime-wired = 10/32 packages (31%), 0/5 squads (0%), 0/3 agents (0%).

## Relations & where used

`docs/04-Concepts/root/plug-and-play.md`, `hooks/self-install.sh`, `hooks/inject-phase-context.sh`, `hooks/cognitive-os-health.sh`, `packages/cos-index/index/packages.yaml`.

## Status / caveats

Read-only audit, no fixes applied. Verdict: the "5 squads, 3 agents wired" claim in the self-hosting-check is nominal (file presence), not functional. See `sprint-2a-orphan-fate.md` for the follow-up disposition (4 squads and 2 agents archived).
