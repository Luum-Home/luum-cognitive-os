# Dogfooding

> Using luum-agent-os to build luum-agent-os.

## What and Why

Dogfooding means using your own product as a primary user. For luum-agent-os, this means every substantial change to the OS itself goes through the SDD pipeline that the OS provides.

The analogy is PyPy: a Python interpreter written in Python. PyPy's self-hosting forces the compiler to be good enough to compile itself. Similarly, luum-agent-os must be good enough to orchestrate its own development. If the SDD pipeline cannot handle building a new skill or hook, that is a bug in the pipeline.

## How It Works in Practice

Every new feature follows the full SDD dependency chain:

```
explore -> propose -> spec -> design -> tasks -> apply -> verify -> archive
```

1. **Explore** the problem space and existing codebase
2. **Propose** the change with scope, risks, and approach
3. **Spec** the behavioral requirements and acceptance criteria
4. **Design** the technical architecture
5. **Tasks** break the work into ordered implementation steps
6. **Apply** implements the tasks via sub-agents
7. **Verify** checks the implementation against the spec
8. **Archive** captures lessons learned for future sessions

The verify-apply cycle retries up to 3 times on critical failures before escalating to a human.

## Benefits

- **Find bugs before users do.** Every feature exercises the full pipeline. If sub-agent delegation is broken, we discover it while building our own features.
- **Every feature tests the pipeline.** There is no separate test suite for SDD orchestration — real usage IS the test.
- **Improvements compound.** A fix to the spec phase produces better specs for the next feature, which produces better implementations, which surface fewer issues in verify.

## First Dogfooded Change: quinotospec-patterns

The first change developed entirely through the SDD pipeline was `quinotospec-patterns` — adding three new SDD capabilities (explore, propose, spec phases).

Pipeline executed: explore, propose, spec, design, apply, verify.

### What We Discovered

Three categories of issues surfaced during the dogfooding run:

1. **Sub-agent tool access.** Sub-agents launched by the orchestrator could not access Engram tools (`mem_save`, `mem_search`). The orchestrator needed to pass tool availability context explicitly.

2. **Permission issues with skill paths.** Agent-teams-lite skill paths referenced absolute paths that varied between environments. Sub-agents failed to load skills when paths did not match the current machine.

3. **Invalid JSON from shell arithmetic.** The `bc` utility used in hooks produced output with newlines and formatting that broke JSON parsing. Shell arithmetic or `awk` was required instead.

All three issues were fixed during the verify-apply retry loop, validating that the loop itself works as designed.

## Auto-Sync Mechanism

The `hooks/self-install.sh` hook runs as the first SessionStart hook and keeps the self-hosted development environment in sync automatically.

### What It Does

1. **Detects self-hosting** by checking if `hooks/self-install.sh` exists relative to the project root. If not present, it silently exits (safe for non-self-hosted projects).
2. **Syncs rule symlinks** from `rules/*.md` to `.claude/rules/`. Adds new rules, removes stale symlinks pointing to deleted files.
3. **Verifies infrastructure** exists: `.claude/settings.json`, `cognitive-os.yaml`, and `.cognitive-os/sessions/`.
4. **Reports status** in a single line: `Self-hosting: OK (55 rules, 57 hooks synced)` or `Self-hosting: FIXED (added 2 new rules, removed 1 stale)`.

### Why It Exists

Before auto-sync, adding a new rule required manually creating a symlink in `.claude/rules/`. This was easy to forget, causing the rule to exist in `rules/` but never load into Claude Code sessions. The hook eliminates this gap: every session starts with a guaranteed-consistent rule set.

### Design Constraints

- Runs in under 1 second (no network calls, no heavy computation)
- Fully idempotent (running twice produces the same result)
- Only activates inside the luum-agent-os repo itself
- Never modifies source files in `rules/` — only manages symlinks in `.claude/rules/`

## Reference

- Rule enforcement: `rules/dogfooding.md`
- Self-install hook: `hooks/self-install.sh`
- SDD workflow documentation: `CLAUDE.md` (SDD Workflow section)
- SDD phase skills: `skills/sdd-*/SKILL.md`
