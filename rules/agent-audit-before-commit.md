# Agent Audit Before Commit

## Rule (Always Active)

The orchestrator MUST NOT commit agent work without reviewing the diff.

### Mandatory Pre-Commit Audit

After every agent completion, BEFORE `git add` + `git commit`:

1. **`git diff` the changed files** — read what was actually modified
2. **Verify against plan** — does the change match what was requested?
3. **Check for content loss** — did the agent delete content without migrating it?
4. **Check for hardcoded values** — did the agent introduce fragile counts, paths, or assumptions?
5. **Run affected tests** — not just "tests pass" but the SPECIFIC tests for the changed files

### Red Flags to Catch

| Red Flag | Example | Action |
|----------|---------|--------|
| File replaced with stub | Doc → "Run /skill to use it" | Verify skill has ALL the doc's content |
| Hardcoded count | `assert count == 40` | Replace with dynamic invariant |
| Settings overwritten | settings.json replaced entirely | Restore from backup |
| Content deleted | Rule removed from COMPACT | Verify hook covers it |
| API changed | Class attribute removed | Check all callers updated |

### Enforcement

- `hooks/agent-output-verifier.sh` (PostToolUse Agent) — verifies files exist
- `hooks/completion-gate.sh` (PostToolUse Agent) — verifies criteria + DoD
- This rule — orchestrator behavioral mandate for design-level review

### Why This Matters

Agents optimize for "tests pass", not "decision is correct". Tests verify behavior,
not design intent. The orchestrator is the design reviewer — hooks can't do this.
