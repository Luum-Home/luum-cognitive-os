# `cos status` — See what is active

`cos status` is the transparency command for Cognitive OS. It tells you which
profile is loaded, how many skills are exposed to the driver, which hooks are
wired into Claude Code, and whether the installation is healthy — all without
reading source.

Comparable to `git status` or `gh status`: one short command, one clear answer.

## Usage

```bash
# From the repo root
bash scripts/cos-status.sh

# Or via the wrapper (auto-dispatches to cos-status.sh):
bash scripts/cos status
```

Flags:

| Flag | Effect |
|------|--------|
| `--verbose` | Expand each section with individual names (first 15-20 per section). |
| `--json`    | Machine-parseable JSON output. No color. |
| `--help`    | Show usage and exit 0. |

## What it shows

```
COS Status
══════════

Profile:         default (cognitive-os.yaml)
Skills:          126 exposed -> .claude/skills/  OK
                 150 installed -> .cognitive-os/skills/
Hooks:           56 wired
  SessionStart:  7
  UserPromptSubmit: 1
  SubagentStart: 1
  PreCompact:    1
  PreToolUse:    14
  PostToolUse:   24
  Stop:          5
  TeammateIdle:  1
  TaskCreated:   1
  TaskCompleted: 1
Rules:           106 total
Packages:        32 installed
Install:         <repo-root> (self-hosted)
Last session:    2026-04-16 20:44:21

Health:          OK all checks pass
```

### Sections

- **Profile** — the active efficiency profile, read from `cognitive-os.yaml`
  (`efficiency.profile`). Values: `default`, `full` (ADR-002).
- **Skills** — two counts:
  - *exposed*: number of entries under `.claude/skills/` (what Claude Code
    actually sees).
  - *installed*: number of entries under `.cognitive-os/skills/cos/` (kernel
    path used by the dispatcher) or `.cognitive-os/skills/` (self-hosting flat
    install).
- **Hooks** — total hooks wired across all events in `.claude/settings.json`,
  then a breakdown per event (`SessionStart`, `PreToolUse`, `PostToolUse`, ...).
- **Rules** — count of `*.md` files in `rules/`, excluding the `RULES-COMPACT.md`
  index.
- **Packages** — count of subdirectories under `packages/`.
- **Install** — the root path, with a `(self-hosted)` marker when the repo
  ships its own `install.sh`/`hooks/self-install.sh`.
- **Last session** — timestamp of the most recent `.cognitive-os/sessions/*/meta.json`.

### Health checks

Three quick asserts run at the end:

1. `.claude/skills/` is non-empty.
2. `.claude/settings.json` is valid JSON.
3. Every wired hook exists on disk.

If any check fails, the line switches to `FAIL N issue(s)` and each failure is
listed with an actionable fix:

```
Health:          FAIL 1 issue(s)
  - 1 wired hook(s) missing: auto-verify.sh
    Fix: bash hooks/self-install.sh
```

The exit code is always `0` — health issues are reported in the output, not
through the exit code, so the command is safe to call from pre-commit or session
start hooks.

## When to run it

- **Session start** — confirm COS is wired correctly before doing real work.
- **After install/update** — verify the new state matches expectation.
- **When something feels broken** — compare expected counts vs actual.
- **In CI** — pipe `--json` output to your dashboard for drift alerts.

## JSON contract (for tooling)

```json
{
  "profile": "default",
  "skills": {
    "driver_exposed": 126,
    "kernel_installed": 150,
    "kernel_path": ".cognitive-os/skills/"
  },
  "hooks": {
    "total": 56,
    "by_event": { "PreToolUse": 14, "PostToolUse": 24, ... }
  },
  "rules": { "source_count": 106 },
  "packages": { "count": 32 },
  "install": { "source": "/path/to/repo (self-hosted)" },
  "session": { "last_end": "2026-04-16 20:44:21" },
  "health": {
    "checks": [
      {"status": "OK", "message": "...", "hint": ""}
    ],
    "failures": 0
  }
}
```

Keys are stable; new keys may be added in future minor versions, but existing
keys will not change type.

## Interpreting red flags

| Output | Meaning | Action |
|--------|---------|--------|
| `Profile: unknown` | `cognitive-os.yaml` missing or `efficiency.profile` not set. | Check `cognitive-os.yaml`; run `cos init` if missing. |
| `Skills: 0 exposed` | Driver path `.claude/skills/` is empty — Claude sees nothing. | `bash hooks/self-install.sh` |
| `Hooks: 0 wired` | `.claude/settings.json` missing or has no hooks block. | `bash hooks/self-install.sh` |
| `Health: FAIL` | One or more asserts failed. | Follow the `Fix:` hint printed under each failure. |

## Related

- `bin/cognitive-os.sh doctor` — more extensive installation diagnostics.
- `scripts/cos` — the subcommand wrapper that routes `status` here and
  everything else (`init`, `doctor`, `list`, ...) to `bin/cognitive-os.sh`.
