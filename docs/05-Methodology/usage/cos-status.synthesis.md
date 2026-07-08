---
type: methodology-synthesis
source: docs/05-Methodology/usage/cos-status.md
provenance: "Usage reference for `cos status`, the single-command transparency check that reports active profile, exposed skills, wired hooks, rules, packages, and install health without requiring the operator to read source."
---

## What it is

Reference doc for `cos status` (`scripts/cos-status.sh`, or `bash scripts/cos status`), described as comparable to `git status`/`gh status` — one command giving a clear answer on whether the Cognitive OS installation is wired correctly.

## Key mechanics

- Flags: `--verbose` (expand each section to first 15-20 individual names), `--json` (machine-parseable, no color), `--help`.
- Output sections: **Profile** (active efficiency profile from `cognitive-os.yaml` `efficiency.profile`; values `default`/`full` per ADR-002), **Skills** (two counts — *exposed* under `.claude/skills/`, what Claude Code actually sees, vs. *installed* under `.cognitive-os/skills/cos/` or the flat self-hosting path), **Hooks** (total wired in `.claude/settings.json` plus a per-event breakdown: SessionStart, UserPromptSubmit, SubagentStart, PreCompact, PreToolUse, PostToolUse, Stop, TeammateIdle, TaskCreated, TaskCompleted), **Rules** (count of `*.md` in `rules/` excluding the compact index), **Packages** (subdirectory count under `packages/`), **Install** (root path, with a `(self-hosted)` marker when the repo ships its own installer), **Last session** (timestamp of the most recent session's `meta.json`).
- Three health checks run at the end: `.claude/skills/` non-empty, `.claude/settings.json` is valid JSON, every wired hook exists on disk. A failure switches the line to `FAIL N issue(s)` with an actionable fix per failure (e.g. missing hook → `bash hooks/self-install.sh`).
- The exit code is always `0` regardless of health-check outcome — deliberately, so the command is safe to call from pre-commit or session-start hooks without breaking them.
- JSON contract is documented with stable keys (`profile`, `skills.driver_exposed`/`skills.kernel_installed`, `hooks.total`/`hooks.by_event`, `rules.source_count`, `packages.count`, `install.source`, `session.last_end`, `health.checks`/`health.failures`); new keys may be added but existing key types won't change.
- Red-flag interpretation table: `Profile: unknown` → check `cognitive-os.yaml` / run `cos init`; `Skills: 0 exposed` → `bash hooks/self-install.sh`; `Hooks: 0 wired` → same fix; `Health: FAIL` → follow the printed `Fix:` hint.
- Recommended usage moments: session start, after install/update, when something feels broken, and in CI piping `--json` to a dashboard for drift alerts.

## Relations & where used

Complements `bin/cognitive-os.sh doctor` (deeper diagnostics) and `scripts/cos` (the subcommand wrapper routing `status`, `init`, `doctor`, `list`, etc. to `bin/cognitive-os.sh`).

## Status / caveats

The example output block (126 skills exposed, 150 installed, 56 hooks, 106 rules, 32 packages, "Last session: 2026-04-16") is illustrative sample data from a specific snapshot, not a live current-state claim — the doc itself frames it as an example of "what it shows," not a guarantee of present counts.
