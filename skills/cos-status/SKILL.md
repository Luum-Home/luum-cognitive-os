---
name: cos-status
description: Display current Cognitive OS state — active profile, skills exposed, hooks wired, rules loaded, packages installed, and health checks. Use when a user asks about OS state, installation verification, or troubleshooting.
triggers: ["/cos-status", "/status", "cos status"]
audience: both
version: 1.0.0
---

# /cos-status — Cognitive OS State Transparency

Show the current state of the Cognitive OS installation: what is active, what is wired, what is healthy.

## When to use

- A user asks "what COS components are active in this project?"
- After installation to verify everything landed correctly
- When something feels broken and you need to diagnose
- Before tagging a release (sanity check)

## How it works

This skill wraps the `scripts/cos-status.sh` script (installed to the project by the installer). Invoke it via the underlying command:

```bash
bash scripts/cos-status.sh             # human-readable table
bash scripts/cos-status.sh --verbose   # expanded per-component listings
bash scripts/cos-status.sh --json      # machine-parseable state
bash scripts/cos-status.sh --help      # usage
```

Alternatively via the `cos` wrapper if installed:

```bash
cos status
cos status --json
```

## Output example

```
COS Status
══════════

Profile:    default (cognitive-os.yaml)
Skills:     9 exposed → .claude/skills/  ✅
            150 installed → .cognitive-os/skills/
Hooks:      18 wired
  PreToolUse:    5
  PostToolUse:   4
  SessionStart:  2
  ...
Rules:      107 total — 21 enforced, 52 auto-injected, 34 docs
Packages:   32 installed
Install:    /Users/.../luum-agent-os (self-hosted)

Health:     ✅ all checks pass
```

If any health check fails (empty skills dir, missing wired hook, invalid settings.json), the skill outputs actionable guidance:

```
Health:     ❌ 2 issues
  - .claude/skills/ is empty (expected >0)
    Fix: bash hooks/self-install.sh
  - hook 'auto-verify.sh' wired but missing on disk
    Fix: bash hooks/self-install.sh
```

## Integration

- **Sprint 4 canary** (`scripts/cos-release-check.sh`) uses `cos status` to verify each install scenario landed correctly.
- **Sprint 5 observability** (`scripts/cos-usage-report.sh`) complements this with usage-over-time metrics.
- **Health check at SessionStart** (`hooks/session-sanity.sh`) invokes a subset of these checks automatically.

## References

- Script source: `scripts/cos-status.sh`
- JSON contract documented: `docs/usage/cos-status.md`
- Part of the 10 core adoption skills listed in ADR-002

## Prerequisites

- Project must be COS-installed (`bash hooks/self-install.sh` or `bash install.sh` ran successfully)
- `.claude/settings.json` must exist and be valid JSON
