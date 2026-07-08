---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-adoption-gap/ux1-install-usability.md
provenance: "Fresh-install simulation on 2026-04-16 ran 'install.sh --standard' and got 'Unknown option: --standard', exit 1, zero files created — the documented profile flag did not exist at the install.sh entry point."
---

## What it is
UX-1 decision: rewrite `install.sh` argument handling into a 1-command, zero-decision contract with explicit `--lean`/`--standard`/`--full`/`--profile=NAME` flags, `COS_PROFILE` env override, auto-detection, and actionable errors — without touching `cos-init.sh`'s internal CLI surface.

## Key mechanics
- Profile resolution precedence: explicit flag > `COS_PROFILE` env var > auto-detection. Chosen profile and its source always printed first.
- Auto-detection heuristic (runs only with no flag/env set): `IF has_git AND src_count>=5 (from find . -maxdepth 3 for common source extensions) -> standard ELSE -> lean`. `full` is never auto-selected — opt-in only.
- Flag mapping to preserve `cos-init.sh` stability: user `--lean` → `cos-init.sh --minimal`; `--standard` → `--standard`; `--full` → `--full`. Renaming `cos-init.sh`'s surface was rejected because it would cascade into `auto-update-projects.sh`, `cos-update.sh`, `cos-bootstrap.sh`, `self-install.sh`.
- Post-install sanity check counts `Rules:`/`Hooks:`/`Skills:` in `.claude/rules/cos/`, `.cognitive-os/hooks/cos/`, `.claude/skills/`; warns and suggests `--full --force` if `standard`/`full` profile landed with 0 skills (suppressed for `lean`, which intentionally installs 0 skills).
- Errors now go to stderr, list valid options inline, exit 1; conflicting flags (`--lean --full`) rejected explicitly rather than "last wins".
- Verification: 4 acceptance scenarios + 6 additional scenarios all passed on fresh `/tmp/` dirs (e.g. `--full` → 14 rules, 124 skills; auto-detect with git+6 `.go` files → standard).

## Relations & where used
Depends on the ADR-001 fix (`.claude/skills/` becoming a real install target) to report skill counts correctly. Cross-references `harness-adoption-gap/ADR-001-harness-skills-sync-path.md` and `scripts-audit.md` (which flagged this as MEDIUM, later promoted to a blocker after the fresh-install simulation showed 0-file installs on the documented flag).

## Status / caveats
Scope: `install.sh` only; `scripts/cos-init.sh` CLI surface, `hooks/self-install.sh`, and `.claude/skills/` population logic were explicitly out of scope / left unchanged. Backwards compatible: `--from`, `--force`, and no-args invocation still work (no-args default changed from hardcoded `standard` to auto-detected, which may now yield `lean` in empty dirs — intentional).
