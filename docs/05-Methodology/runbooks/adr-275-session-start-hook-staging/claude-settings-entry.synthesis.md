---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/adr-275-session-start-hook-staging/claude-settings-entry.md
provenance: "Gives the operator the exact JSON snippet and placement instructions to append the ADR-275 session-start projector to .claude/settings.json."
---

## What it is

A short, single-purpose instruction sheet: the exact JSON entry to append to `.claude/settings.json`'s `hooks.SessionStart[0].hooks[]` array to wire in the session-start projector.

## Key mechanics

- The entry is a `command` type hook invoking `python3 "$CLAUDE_PROJECT_DIR/scripts/cos-session-start-projector"`.
- Placement matters: it must go AFTER the existing `session-init.sh` entry so the projection surfaces only after project state has finished loading.
- The projector always exits 0 and writes to stderr, so it is non-blocking and cannot fail the SessionStart chain.
- Optional disable: `export COS_PROJECTOR_DISABLED=1` — but the doc notes this only works "if you wrap the command in a check," i.e. it's not automatically honored by the raw command shown.
- Rollback is simply removing the appended entry.

## Relations & where used

One of three per-harness sibling instruction files referenced by `adr-275-session-start-hook-staging/README.md` (the other two being `codex-hooks-entry.md` and a `.cognitive-os/cos-runner-hooks.json` entry not in this batch). Both this file and `README.md` describe `.claude/settings.json` as protected by `protected-config-write-guard`, requiring operator authorization to edit.

## Status / caveats

Very short, single-purpose instruction file — synthesized in full above rather than abbreviated. Worth flagging: the `COS_PROJECTOR_DISABLED=1` disable note is conditional ("if you wrap the command in a check") but the JSON snippet shown does not include such a wrapper, so as written the disable env var has no effect unless the operator adds the check themselves — a latent gap between the instructions and the literal snippet.
