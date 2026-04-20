# cos-advisory-llm

Optional extension pack. Hosts the three Haiku-evaluated advisory gates that require Anthropic API access.

## What's here

- `hooks/prompt-quality-llm.sh` — UserPromptSubmit gate, Haiku scores prompt quality
- `hooks/completeness-check-llm.sh` — PreToolUse Agent, Haiku evaluates task-completeness rubric
- `hooks/confidence-gate-llm.sh` — PostToolUse Agent, Haiku cross-checks Trust Report claims

## Enabling

These gates activate automatically when `ANTHROPIC_API_KEY` is set AND the efficiency profile is `full`. Without the key they no-op silently (`skip_if_missing: true`).

## Wave 1 POC notes

This is the first extension extracted from monolithic `hooks/` per `docs/architecture/core-vs-extensions-migration-plan.md`. Source files remain importable at the old `hooks/*.sh` paths via backwards-compatibility symlinks; symlinks are scheduled for removal in v0.15.2.

## Migration debt

Tracked as row D43 in `docs/reports/debt-register-2026-04-20.md` (status: PARTIAL — advisory-llm extracted; other packs pending per migration plan).
