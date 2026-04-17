# Archived Squad Templates

These squad YAMLs are **archived template examples** — preserved for historical and
documentation value. They are NOT runtime-loaded; no Python/Go code parses them.

## Why archived (Sprint 2A, 2026-04-16)

The Capa-3 functional audit (`docs/architecture/functional-audit/scorecard-packages-squads-agents.md`)
found:

- **0% runtime integration** — no loader, no parser, no dispatcher.
- **Broken `skills:` references** — every YAML references `testing-patterns`, a skill
  that does not exist under `skills/` or `packages/*/skills/`.
- **Broken `agentRef:` references** — `backend-architect`, `security-engineer`,
  `sre-agent`, `devops-agent`, `engineering-manager-agent` have no matching MD file
  under `agents/`.

They were copied (symlinked) into `.cognitive-os/squads/` and counted in health
reports, but functioned only as ornamental examples.

## What remains active

One squad file remains in the project root `squads/` directory
(`squads/organization.yaml`) as an example for users initializing their own projects.
It is wired for template-copy by `/cognitive-os-init` but still has no runtime loader.

## When to un-archive

A squad YAML should be un-archived **only after** a runtime loader has been
implemented that:

1. Deserializes the YAML (Pydantic or equivalent)
2. Resolves `agentRef:` entries against `agents/*.md` or a dispatch registry
3. Resolves `skills:` entries against `skills/*/SKILL.md`
4. Wires `governance.constitutionalGates` into a policy engine

Until then, these files are reference only. See `docs/plug-and-play.md` for the
intended design.
