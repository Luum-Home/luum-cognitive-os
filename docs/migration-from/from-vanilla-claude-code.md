# Migrating from Vanilla Claude Code

This guide is for users who already use stock Claude Code and want to add
Cognitive OS governance on top — without replacing anything you have today.

Cognitive OS does not change how Claude reasons or how you interact with it.
It adds hooks that fire at lifecycle points Claude Code already exposes:
session start, before tool calls, after tool calls, and session end.

---

## What changes after install

- `settings.json` is updated to register ~14 governance hooks.
- `.cognitive-os/` directory is created in your project with rules, skills,
  hooks, and metrics storage.
- A `cognitive-os.yaml` config file appears in `.cognitive-os/`.
- On the next Claude Code session, hooks fire automatically. No manual
  invocation required.

Nothing about the Claude Code UI, model selection, or your `.claude/CLAUDE.md`
instructions changes unless you opt in to project-specific rule generation
via `/cognitive-os-init`.

---

## Installation

**Prerequisites**: bash, git, Python 3.10+.

```bash
# Step 1: cd into YOUR project (not the Cognitive OS repo)
cd /path/to/your-project

# Step 2a: Remote install — nothing to clone
curl -sL https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/install.sh \
  | bash -s -- --harness=claude

# Step 2b: Local install — if you have the repo cloned already
/path/to/luum-agent-os/install.sh --harness=claude

# Step 3: Verify hooks are wired
COGNITIVE_OS_PROJECT_DIR="$PWD" bash /path/to/luum-agent-os/scripts/cos-status.sh
# Expected: PASS  active settings driver is valid
#           PASS  wired hooks exist

# Step 4 (optional): Generate project-specific rules and skills
claude
> /cognitive-os-init
```

`/cognitive-os-init` detects your stack (Node.js, Go, Python, etc.) and writes
project-specific rules into `.claude/rules/` and skills into `.claude/skills/`.
This step is optional — the governance layer works without it.

---

## Keeping Cognitive OS updated

Install git hooks once to auto-update all registered projects on `git pull`:

```bash
cd /path/to/luum-agent-os
bash scripts/setup-git-hooks.sh
```

After that, `git pull` in the Cognitive OS source repo triggers a re-run of the
installer for every project you have registered. Manual re-runs are also fine:

```bash
/path/to/luum-agent-os/install.sh --harness=claude   # re-run from your project dir
```

---

## Uninstalling

```bash
# Option A: Remove .cognitive-os/ and revert settings.json
bash /path/to/luum-agent-os/scripts/uninstall.sh

# Option B: Manual revert (if the uninstall script is unavailable)
# 1. Delete .cognitive-os/ from your project root
rm -rf .cognitive-os/

# 2. Remove COS hook entries from .claude/settings.json
# Each COS hook has a comment or a path containing ".cognitive-os/hooks/"
# Open settings.json and delete those entries from the hooks arrays.
```

> **Note**: `scripts/uninstall.sh` is the canonical path. If it does not exist
> in the version you installed, use Option B. This will be resolved in a future
> release (tracked in `.cognitive-os/plans/`).

---

## FAQ

**Does this change my Claude Code behavior?**

Claude's reasoning is unchanged. Cognitive OS adds hooks that can block, warn, or
log at lifecycle points. The most visible change is that some agent completions
will include a Trust Report at the end — this is the `trust-score-validator.sh`
hook requesting evidence before accepting a "done" claim.

**What is the cost overhead?**

Hooks are bash scripts that run locally. They add < 200 ms per tool call in
typical operation (see SLO 2 in [rules/so-slo.md](../../rules/so-slo.md)).
There is no external API call in the governance layer itself.

**How do I disable temporarily?**

Set the efficiency profile to minimal, which disables all non-critical hooks:

```bash
bash /path/to/luum-agent-os/scripts/apply-efficiency-profile.sh minimal
```

Or disable a specific hook by removing its entry from `.claude/settings.json`.

Restore the standard profile with:

```bash
bash /path/to/luum-agent-os/scripts/apply-efficiency-profile.sh standard
```

**Will it conflict with my existing `.claude/settings.json`?**

The installer merges hook entries; it does not overwrite your existing settings.
Run `git diff .claude/settings.json` after install to review exactly what changed.

**What if a hook fails?**

Each hook has an advisory mode (exit 0, log only) and a blocking mode (exit 2,
blocks the tool call). The default profile uses advisory mode for most hooks and
blocking mode only for security-critical paths (credential guard, license guard).
A failing hook that exits 1 is treated as advisory.
