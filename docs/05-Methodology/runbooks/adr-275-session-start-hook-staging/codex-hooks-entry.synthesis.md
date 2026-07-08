---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/adr-275-session-start-hook-staging/codex-hooks-entry.md
provenance: "Gives the operator the exact JSON snippet and file-creation fallback to wire the ADR-275 session-start projector into Codex's .codex/hooks.json."
---

## What it is

A short, single-purpose instruction sheet: the JSON entry to append to (or the full file to create for) `.codex/hooks.json`'s `hooks.SessionStart` array, mirroring the Claude Code entry for the Codex harness.

## Key mechanics

- If `.codex/hooks.json` already exists, append an entry with `command: ["python3", "scripts/cos-session-start-projector"]` and `description: "ADR-275 session-start projector"`.
- If the file does not exist yet, create it with the full `{"hooks": {"SessionStart": [...]}}` wrapper shown in the doc.
- Key portability detail: Codex resolves commands relative to the project root, so no `$CLAUDE_PROJECT_DIR` substitution is needed (unlike the Claude Code entry, which does require that substitution).

## Relations & where used

Sibling to `claude-settings-entry.md` in the same staging directory — both implement the same underlying projector script (`scripts/cos-session-start-projector`) for different harnesses, per the cross-harness pattern described in `adr-275-session-start-hook-staging/README.md`.

## Status / caveats

Very short, single-purpose instruction file — synthesized in full above rather than abbreviated. No internal inconsistencies found.
