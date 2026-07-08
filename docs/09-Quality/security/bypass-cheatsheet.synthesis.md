---
type: quality-synthesis
source: docs/09-Quality/security/bypass-cheatsheet.md
provenance: "Quick-reference cheatsheet for ADR-241's consolidated emergency-bypass allowlist, listing every stable bypass key, its legacy env-var aliases, and scope."
---

## What it is

A compact operational cheatsheet documenting `COS_BYPASS`, the ADR-241 session-scoped allowlist that consolidates emergency hook bypasses under one mechanism, with a table mapping each stable bypass key to its legacy env-var alias(es) and scope.

## Key mechanics

- Set via `export COS_BYPASS=destructive_git,push_collision` (comma-separated keys), or persisted per-repo at `.cognitive-os/runtime/bypass.env` (e.g. `COS_BYPASS=direct_push`), read by PreToolUse hooks.
- Bypasses are framed as emergency controls — the doc explicitly prefers fixing the underlying finding or using a higher-level COS command first.
- Legacy per-feature env vars remain as aliases for one release; new hooks should call `cos_bypass_allows <key>` from `hooks/_lib/bypass-resolver.sh` instead of checking legacy vars directly.
- Ten stable keys are documented, each mapped to its scope and a usage note: `destructive_git` (git safety, does not replace explicit `--allow-*` tokens), `main_branch_write` (protected-branch writes, requires a reason), `branch_switch` (branch context changes, operator must explicitly accept), `reset_over_wip` (reset/stash WIP guard, logs bypass evidence), `commit_guard` (commit scope guard, emergency-only), `branch_ownership` (branch lock override, only after checking liveness), `claim_gate` (orchestrator claim gate, prefer fixing evidence), `push_collision` (push collision detector, prefer the ADR-243 post-rewrite marker instead), `direct_push` / `direct_main` (direct writes to protected branches, both require a reason), `unproven_scope_both` (portability scope marker, requires a paired portability proof later).

## Relations & where used

- `hooks/_lib/bypass-resolver.sh` (the `cos_bypass_allows` function), `.cognitive-os/runtime/bypass.env`.
- References ADR-241 (the consolidation decision) and ADR-243 (preferred alternative to the push-collision bypass).

## Status / caveats

No dates or version markers; presented as current operational reference. No internal inconsistencies found.
