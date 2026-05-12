# Cross-Harness Authoring Pattern

> Full spec: `docs/04-Concepts/architecture/cross-harness-authoring.md`

## Agent Self-Check (5 items, SO-only)

Before touching any SO path (`hooks/`, `scripts/`, `lib/`, `settings.json`), confirm:

1. **Driver scope**: does the change belong to the Claude driver (`.claude/`) or the OS kernel (`.cognitive-os/`)?
2. **Settings.json**: never edit directly — use `scripts/set-security-profile.sh` or `scripts/apply-efficiency-profile.sh`.
3. **Symlinks**: `lib/*.py` may be symlinks to `packages/*/lib/` — verify both sides.
4. **Hook registration**: new hooks must be added to a profile tier, not to settings.json directly.
5. **`cognitive-os.yaml`**: read current value before writing; do not duplicate sections.

## Contextual Trigger

OS-only. Fires when an agent is composing an edit to any SO path.
See also: `rules/orchestrator-prompt-compose.md` (ADR-032).
