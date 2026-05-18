---
name: install-hook
description: 'Use when you need this Cognitive OS skill: Install an extension hook
  from a local path or packages/cos-* into the active harness and register it in
  cognitive-os.yaml; do not use when authoring a new hook from scratch.'
routing_intents:
  - "Install a Cognitive OS extension hook by name from the extension registry"
  - "Enable an opt-in hook from packages/cos-* without a full wave migration"
  - "Wire a hook into the active harness settings surface"
  - "Register an extension hook in cognitive-os.yaml harness.hooks"
  - "Make a dormant or packaged hook active in the current harness"
version: 0.1.0
audience: os
tags:
  - install
  - extension
  - hooks
  - plugin
platforms:
  - claude-code
prerequisites: []
routing_patterns:
  - pattern: \binstall[- ]?hook\b
    confidence: 0.95
  - pattern: /install-hook\b
    confidence: 0.97
  - pattern: \benable\s+hook\b
    confidence: 0.75
  - pattern: \bactivate\s+extension\s+hook\b
    confidence: 0.78
summary_line: Install an extension hook from packages/cos-* into the active harness registration.
triggers:
  - install-hook
  - /install-hook
  - enable extension hook
  - activate hook

---
<!-- SCOPE: os-only -->
# /install-hook

> Install an extension hook from the COS extension registry into the active harness.

## Scope note

This skill is `os-only` because it modifies the COS hook projection surface
(`cognitive-os.yaml` > `harness.hooks`) and re-runs
`scripts/apply-efficiency-profile.sh` to project the change into
`.claude/settings.json` (or the active harness equivalent). For creating a
brand-new hook from scratch, use `/add-hook`.

## Trigger

When you want to activate an existing but unregistered extension hook — one
that lives in `packages/cos-*/hooks/` or `hooks/` with an `@on-demand` or
`@manual-trigger` marker — without running a full wave migration.

## Inputs

- **`<name>`**: kebab-case hook filename without `.sh` (e.g., `semgrep-scan`,
  `guardrails-validator`)
- **`--event <EventType>`** (optional): `PreToolUse`, `PostToolUse`,
  `SessionStart`, or `Stop` — required when the hook header does not declare
  `# EVENT:`
- **`--matcher <pattern>`** (optional): tool matcher pattern (e.g., `Bash`,
  `Edit|Write`) — required when the hook header does not declare a clear matcher
- **`--source <path>`** (optional): explicit path to the `.sh` file if not in
  standard search paths
- **`--dry-run`** (optional): show what would happen without writing anything

## API Signature

```
/install-hook <name> [--event <EventType>] [--matcher <pattern>] [--source <path>] [--dry-run]
```

## When to use

- A feature plan asks you to ship an on-demand hook without executing a full
  wave migration.
- A hook exists in `packages/cos-*/hooks/` but is not yet wired into
  `cognitive-os.yaml`.
- A hook in `hooks/` carries `@on-demand` or `@manual-trigger` and the
  operator now wants it active.

## When NOT to use

- The hook is already listed in `.claude/settings.json` — it is already active.
- You want to create a new hook from scratch — use `/add-hook`.
- The hook requires an external service (Docker, Valkey, API key) that is not
  configured — document the dependency first.

## Steps

### 1. Resolve the hook source

Run the backing script in dry-run mode:

```bash
scripts/cos-install-hook <name> --dry-run
```

The script searches in this priority order:
1. `--source <path>` if provided
2. `packages/cos-*/hooks/<name>.sh`
3. `hooks/<name>.sh` (present but unregistered / marked @on-demand)

### 2. Validate the hook script

The script verifies:
- File exists and is executable (`chmod +x` if missing)
- Line 1 is `#!/usr/bin/env bash`
- `# SCOPE:` header present
- `# EVENT:` header present or `--event` flag provided
- `set -euo pipefail` within first 20 lines

### 3. Determine registration metadata

Extract from hook headers or CLI flags:
- `EVENT`: `PreToolUse` / `PostToolUse` / `SessionStart` / `Stop`
- `MATCHER`: tool pattern string
- `COMMAND`: `bash "$CLAUDE_PROJECT_DIR/hooks/<name>.sh"`

### 4. Register in cognitive-os.yaml

Append the hook entry under `harness.hooks.<EventType>` in `cognitive-os.yaml`.
If the `harness.hooks` key is absent, create it. Use Python YAML round-trip
(via `scripts/cos-install-hook`) to preserve comments and ordering.

NEVER edit `.claude/settings.json` directly. The projection step (Step 5) does that.

### 5. Project to harness surface

```bash
bash scripts/apply-efficiency-profile.sh
```

This re-generates `.claude/settings.json` (and other harness surfaces) from
`cognitive-os.yaml`. The new hook appears in the settings after this step.

### 6. Verify

```bash
grep -c '"<name>.sh"' .claude/settings.json
# Expect: 1
```

### 7. Inform the user

Report:
- Source path resolved
- Hook registered in `cognitive-os.yaml` under `harness.hooks.<EventType>`
- Harness surface re-projected (`apply-efficiency-profile.sh` exit 0)
- Effective immediately in the active session

## Edge cases

| Situation | Behaviour |
|---|---|
| Hook already in `cognitive-os.yaml` | Error: "already registered — edit `cognitive-os.yaml` directly to change matcher/event" |
| Missing `# EVENT:` and no `--event` flag | Error: "cannot determine event type; pass `--event`" |
| Hook requires external service | Warning printed; installation proceeds; operator must verify service is up |
| `apply-efficiency-profile.sh` fails | Rollback the `cognitive-os.yaml` change; report failure with script stderr |
| `--dry-run` | Prints plan; writes nothing; does not invoke `apply-efficiency-profile.sh` |
| Source is outside project root | Error: "source must be within project root (scope violation)" |
| Hook file not executable | Script runs `chmod +x` automatically and logs the action |

## Cross-references

- `/add-hook` — author a new hook from scratch
- `/install-skill` — install an extension skill the same way
- `scripts/cos-install-hook` — backing executable
- `scripts/apply-efficiency-profile.sh` — canonical harness projection entry point
- `scripts/_lib/settings-driver-claude-code.sh` — Claude Code projection driver
- `docs/04-Concepts/architecture/core-vs-extensions-audit-2026-04-20.md` — extension pack taxonomy
- `docs/02-Decisions/adrs/ADR-064-harness-hook-registry.md` — hook registry design (if present)
- `.cognitive-os/plans/features/so-existential-validation-2026-04-24.md` Phase 3 — origin requirement
