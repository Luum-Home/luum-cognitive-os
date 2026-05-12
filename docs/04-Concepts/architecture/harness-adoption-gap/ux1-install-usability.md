# UX-1: `install.sh` — 1-Command, Zero-Decision Install

Date: 2026-04-16
Author: cos-reconstruction (sub-agent)
Phase: reconstruction — rewrite allowed
Scope: `install.sh` only (delegation target `scripts/cos-init.sh` untouched)

## Problem (empirical)

Fresh-install simulation on 2026-04-16 ran:

```
$ bash /path/to/luum-agent-os/install.sh --standard
Unknown option: --standard
Run 'install.sh --help' for usage.
```

Exit code: 1. Zero files created in the target directory.

The install entry point did NOT accept the `--standard` flag (nor `--lean`,
`--full`, `--profile=...`). It silently required either `--from`, `--force`,
or no arguments, and internally hardcoded `--standard` when delegating to
`cos-init.sh`. Users who followed the intuitive "pick a profile" pattern
(documented in several COS skills + the `cos-init.sh --help` output) hit a
dead-end error with no valid next step.

Additionally, `--help` made no mention of profiles — the 3-profile selector
was a `cos-init.sh` concept that had never been surfaced at the `install.sh`
level. A new user had to read source code to discover the installer's own
contract.

## Decision

Rewrite `install.sh` argument handling to implement a **1-command, zero-decision**
contract aligned with the production-ready vanilla vision:

| Invocation                                    | Behaviour                                      |
| --------------------------------------------- | ---------------------------------------------- |
| `bash install.sh`                             | Auto-detect profile; install; confirm counts  |
| `bash install.sh --lean`                      | Explicit lean (5 rules, no skills)            |
| `bash install.sh --standard`                  | Explicit standard (~25 rules, ~10 skills)     |
| `bash install.sh --full`                      | Explicit full (all rules, all skills)         |
| `bash install.sh --profile=standard`          | Long-form equivalent                           |
| `COS_PROFILE=full bash install.sh`            | Env-var override (picked up when no flag)     |
| `bash install.sh --help`                      | Lists 3 profiles with descriptions            |
| `bash install.sh --bogus`                     | Actionable error listing valid options; exit 1 |

Profile resolution precedence (highest wins): explicit flag > `COS_PROFILE`
env var > auto-detection. The chosen profile is always printed on the first
line of install output, together with its source (`flag`, `env COS_PROFILE`,
or `auto-detected`).

### Auto-detection heuristic

The heuristic runs only when no flag and no env var are set. It optimises
for "least surprise" — do the smallest reasonable install in unfamiliar
contexts, and promote to `standard` only when there is evidence the user
is working in a real code project.

```
has_git:     [ -d .git ]
src_count:   find . -maxdepth 3 -type f \( *.go *.py *.ts *.tsx *.js *.jsx
             *.rs *.java *.rb *.kt *.swift *.cs \) | head -6 | wc -l

IF has_git AND src_count >= 5   -> standard
ELSE                            -> lean
```

`full` is never auto-selected — it is opt-in only, via `--full` or
`COS_PROFILE=full`. This protects users from accidentally installing the
heaviest profile into small projects.

### Flag → `cos-init.sh` mapping

`cos-init.sh` pre-dates this change and uses `--minimal` as its internal
name for what we now expose as `--lean` to the user. Rather than renaming
the `cos-init.sh` CLI surface (which would break self-hosting callers like
`auto-update-projects.sh`), `install.sh` performs the mapping at delegation
time:

```
user-facing --lean     -> cos-init.sh --minimal
user-facing --standard -> cos-init.sh --standard
user-facing --full     -> cos-init.sh --full
```

This keeps the `cos-init.sh` surface stable while giving users a coherent
`lean / standard / full` vocabulary at the top level. The term "minimal"
no longer leaks into user-facing help text.

### Post-install sanity check

After delegation completes, `install.sh` now counts what actually landed:

```
Rules:  N in .claude/rules/cos/
Hooks:  N in .cognitive-os/hooks/cos/
Skills: N in .claude/skills/
```

If the profile is `standard` or `full` but `N skills == 0`, the installer
prints an actionable warning suggesting `bash install.sh --full --force`.
The `lean` profile intentionally installs zero skills, so the warning is
suppressed in that case.

### Error handling

All error paths now:
- Print to `stderr` (previously mixed with stdout).
- List valid options in the error message itself.
- Exit 1 (non-zero).

Example:
```
$ bash install.sh --bogus
Unknown option: --bogus
Valid options: --lean, --standard, --full, --profile=NAME, --from PATH, --force, --help
Run 'install.sh --help' for details.
$ echo $?
1
```

Conflicting profile flags (e.g. `--lean --full`) are rejected with a clear
message rather than silently using "last flag wins".

## Before / After

### Before

```
$ bash install.sh --standard
Unknown option: --standard
Run 'install.sh --help' for usage.     # --help itself never mentioned profiles

$ bash install.sh
=== Cognitive OS Installer ===
...
Running cos-init.sh...                  # always --standard, no user choice
```

### After

```
$ bash install.sh
=== Cognitive OS Installer ===

Profile: lean (auto-detected)
  (override with --lean / --standard / --full, or COS_PROFILE=...)
...
Running cos-init.sh --minimal...
...
Cognitive OS installed successfully! (profile: lean)
  Rules:  6 in .claude/rules/cos/
  Hooks:  5 in .cognitive-os/hooks/cos/
  Skills: 0 in .claude/skills/
```

```
$ bash install.sh --standard
=== Cognitive OS Installer ===

Profile: standard (flag)
...
Running cos-init.sh --standard...
...
Cognitive OS installed successfully! (profile: standard)
  Rules:  10 in .claude/rules/cos/
  Hooks:  28 in .cognitive-os/hooks/cos/
  Skills: 4 in .claude/skills/
```

## Verification

All four acceptance scenarios pass on a fresh `/tmp/` directory:

| # | Command                                      | Expected                              | Observed                              |
| - | -------------------------------------------- | ------------------------------------- | ------------------------------------- |
| 1 | `bash install.sh` (empty dir)                | exit 0, auto-detect, install          | exit 0, profile=lean, 6 rules        |
| 2 | `bash install.sh --standard`                 | exit 0, install                       | exit 0, profile=standard, 10 rules, 4 skills |
| 3 | `bash install.sh --bogus`                    | exit 1, "Unknown option" on stderr    | exit 1, lists 7 valid options        |
| 4 | `bash install.sh --help`                     | lists lean/standard/full              | lists all 3 with sizes + descriptions |

Additional scenarios verified:

| Command                                     | Observed                              |
| ------------------------------------------- | ------------------------------------- |
| `bash install.sh --lean`                    | Profile: lean (flag), exit 0          |
| `bash install.sh --full`                    | Profile: full (flag), 14 rules, 124 skills, exit 0 |
| `bash install.sh --profile=standard`        | Profile: standard (flag), exit 0      |
| `COS_PROFILE=full bash install.sh`          | Profile: full (env COS_PROFILE), exit 0 |
| `bash install.sh --lean --full`             | exit 1, "conflicting profile flags"   |
| git-init + 6 `.go` files, then `install.sh` | Profile: standard (auto-detected)     |

## Backwards compatibility

Pre-existing invocations remain supported:
- `bash install.sh --from PATH` — unchanged
- `bash install.sh --force`     — unchanged
- `bash install.sh` (no args)   — still works, now auto-detects instead of
  hardcoding `--standard`; the default may differ in truly-empty directories
  (now `lean` instead of `standard`). This is intentional: an empty dir
  installing 10 rules + 4 skills was overkill and wasted the user's quota
  on paths they could not yet use.

The `--from` flag composes with profile flags:
```
bash install.sh --from /path/to/repo --standard --force
```

## Out of scope

- `scripts/cos-init.sh` CLI surface unchanged (still uses `--minimal`,
  `--standard`, `--full`). Renaming it would cascade into
  `auto-update-projects.sh`, `cos-update.sh`, `cos-bootstrap.sh`, and
  `self-install.sh`, breaking the self-hosting path. The mapping layer in
  `install.sh` is a cheaper, fully-contained fix.
- `hooks/self-install.sh` unchanged (self-hosting path, different usage).
- `.claude/skills/` population — already fixed by ADR-001; this change
  relies on that fix to deliver skills correctly under `standard`/`full`.

## Cross-references

- `docs/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md`
  — prerequisite fix that made `.claude/skills/` a real install target.
- `docs/architecture/harness-adoption-gap/scripts-audit.md` — full audit of
  the install chain; this change addresses the public `install.sh` UX gap
  that the audit flagged as MEDIUM but which fresh-install simulation
  subsequently promoted to effectively a blocker (0-file installs on the
  documented flag).
