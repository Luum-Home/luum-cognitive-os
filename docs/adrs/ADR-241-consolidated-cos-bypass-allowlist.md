---

adr: 241
title: Consolidate Hook-Bypass Envs into a Single COS_BYPASS Allowlist
status: accepted
implementation_status: partial
classification_basis: 'Slice A resolver/hook integration is active; broad ecosystem bypass consolidation remains future expansion'
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-094, ADR-105, ADR-182]
implementation_files:
  - hooks/_lib/bypass-resolver.sh
  - docs/security/bypass-cheatsheet.md
  - hooks/destructive-git-blocker.sh
  - hooks/commit-guard.sh
  - hooks/branch-ownership-lock.sh
  - hooks/orchestrator-claim-gate.sh
  - hooks/push-collision-check.sh
  - tests/behavior/test_bypass_resolver.py
tier: maintainer
tags: [governance, hooks, dx, postmortem-2026-05-08]
---
# ADR-241: Consolidate Hook-Bypass Envs into a Single COS_BYPASS Allowlist

## Status

Accepted — Slice A implemented. Shared resolver, cheatsheet, target hook integration, and behavior tests are active; broad ecosystem bypass consolidation remains future expansion.

## Context

Seven distinct environment variables currently gate different hook bypasses:

- `COS_ALLOW_DESTRUCTIVE_GIT`
- `COS_BYPASS_COMMIT_GUARD`
- `COS_ALLOW_MAIN_BRANCH_WRITE`
- `COS_ALLOW_UNPROVEN_SCOPE_BOTH`
- `COS_ORCHESTRATOR_CLAIM_GATE_MODE`
- `DISABLE_HOOK_PUSH_COLLISION_CHECK`
- `COS_ALLOW_DIRECT_PUSH`

Each has a different scope, naming convention, and resolution semantics. There
is no central cheatsheet that names them, describes when they are appropriate,
and shows the correct invocation form.

Observed symptoms on 2026-05-08:

- The operator and orchestrator pasted bypass envs eight or more times by
  trial and error during a single session, because the right name was not
  discoverable from any single document.
- Inline-set forms such as `VAR=val cmd` did not reach `PreToolUse` hooks,
  because those hooks run before the bash invocation populates its own env.
  The operator was forced to fall back to `--no-verify`, which discarded
  unrelated protections at the same time.
- Two hooks named the same bypass concept differently
  (`COS_ALLOW_DESTRUCTIVE_GIT` vs `COS_BYPASS_COMMIT_GUARD`), so honoring one
  did not honor the other and the operator had to set both.

The anti-pattern is **per-hook bypass naming with no shared resolver**. The
governance value of any individual gate is undermined by the cumulative
friction of the bypass surface.

## Decision

Introduce a single allowlist environment variable and a shared resolver:

```text
COS_BYPASS=key1,key2,...
```

Semantics:

1. A new helper `hooks/_lib/bypass-resolver.sh` exposes a single function,
   `cos_bypass_allows <key>`, that returns 0 when `<key>` is present in
   `COS_BYPASS` (comma-separated, whitespace-tolerant) **or** when the
   corresponding back-compat env var is set to a truthy value.
2. The resolver also reads `.cognitive-os/runtime/bypass.env` if present, so
   `PreToolUse` hooks see the same allowlist that the operator set on the
   shell. This is the layer that fixes the inline-`VAR=val cmd` invisibility
   problem.
3. Every gate hook listed in `implementation_files` switches its bypass
   check to call `cos_bypass_allows <stable-key>`. Existing envs continue
   to work for one release as aliases.
4. A canonical cheatsheet at `docs/security/bypass-cheatsheet.md` lists every
   key, what it disables, the audit-trail entry it produces, and an example
   invocation.

Stable keys are short, hook-aligned, and lower_snake_case, e.g.
`destructive_git`, `commit_guard`, `main_branch_write`, `claim_gate`,
`push_collision`, `direct_push`.

## Operational Guide

### What changes for the operator

Before this ADR: seven separately named bypass environment variables, each with a different naming convention and scope. There was no single reference document listing them all.

After this ADR: one allowlist variable (`COS_BYPASS`) and one resolver (`hooks/_lib/bypass-resolver.sh`) cover all gate bypasses. The canonical reference is `docs/security/bypass-cheatsheet.md`.

**Stable key mapping (legacy env → new key):**

| Legacy env var | New `COS_BYPASS` key | Gate hook |
|---|---|---|
| `COS_ALLOW_DESTRUCTIVE_GIT` | `destructive_git` | `hooks/destructive-git-blocker.sh` |
| `COS_BYPASS_COMMIT_GUARD` | `commit_guard` | `hooks/commit-guard.sh` |
| `COS_ALLOW_MAIN_BRANCH_WRITE` | `main_branch_write` | `hooks/branch-ownership-lock.sh` |
| `COS_ALLOW_UNPROVEN_SCOPE_BOTH` | `unproven_scope_both` | `hooks/orchestrator-claim-gate.sh` |
| `COS_ORCHESTRATOR_CLAIM_GATE_MODE` | `claim_gate` | `hooks/orchestrator-claim-gate.sh` |
| `DISABLE_HOOK_PUSH_COLLISION_CHECK` | `push_collision` | `hooks/push-collision-check.sh` |
| `COS_ALLOW_DIRECT_PUSH` | `direct_push` | `hooks/push-collision-check.sh` |

Legacy env vars remain as back-compat aliases for one release. Both forms resolve via the shared `cos_bypass_allows <key>` function.

### Daily operational pattern

**To bypass a single gate for one command:**
```bash
COS_BYPASS=destructive_git git filter-repo --execute ...
# Comma-separate for multiple keys:
COS_BYPASS=destructive_git,push_collision git push --force-with-lease
```

**When inline `VAR=val cmd` does not reach `PreToolUse` hooks** (the original incident failure mode), use the runtime file instead:
```bash
echo "destructive_git,commit_guard" > .cognitive-os/runtime/bypass.env
# hooks/_lib/bypass-resolver.sh reads this file; PreToolUse hooks see it
# Clear after session:
rm .cognitive-os/runtime/bypass.env
```

**To discover which key to use:** consult `docs/security/bypass-cheatsheet.md` — it lists every key, what it disables, the audit-trail entry produced, and an example invocation.

**To verify the resolver is wired correctly:**
```bash
python3 -m pytest tests/behavior/test_bypass_resolver.py -q
grep -RIn "cos_bypass_allows" hooks/
```

### Reading guide for cold readers

If you encounter this ADR without session context:

1. Read `docs/security/bypass-cheatsheet.md` for the complete and current key list — this is the single document to consult during an incident.
2. Read `hooks/_lib/bypass-resolver.sh` for the resolution logic: it checks `COS_BYPASS`, then back-compat env vars, then `.cognitive-os/runtime/bypass.env`.
3. The original incident (2026-05-08) had the operator pasting bypass envs 8+ times by trial and error — the cheatsheet and resolver exist to eliminate that friction without removing the governance value of the individual gates.
4. The runtime file (`.cognitive-os/runtime/bypass.env`) is the mechanism that makes `PreToolUse` hooks see the same bypass scope as bash hooks — use it whenever inline env-var form fails.

## Alternatives rejected

- **Keep per-hook envs and document them centrally** — rejected because the
  documentation drift caused this incident in the first place. Without a
  shared resolver, every new gate adds a new env name, and the cheatsheet
  becomes stale on the next merge.
- **Single boolean `COS_BYPASS_ALL=1`** — rejected because it removes the
  governance value of fine-grained gates entirely. A single flag is exactly
  the `--no-verify` failure mode that ADR-094 was created to avoid.
- **Bypass via per-command CLI flag only (no env var)** — rejected because
  many gates fire from `PreToolUse` hooks that the operator never invokes
  directly. There is no command line on which to put a flag.
- **Move bypass to a YAML config under `cognitive-os.yaml`** — rejected as a
  default because YAML edits are persistent across sessions, while bypass
  scope should be ephemeral. The runtime `bypass.env` file is session-scoped
  and cleared on session close.

## Consequences

### Positive

- One name (`COS_BYPASS`) to learn and one document
  (`docs/security/bypass-cheatsheet.md`) to consult.
- `PreToolUse` hooks see the same bypass scope as bash hooks because the
  resolver reads from a runtime file, not just process env.
- Audit-trail entries cite a stable key, so `agent-heartbeat.jsonl` analysis
  can attribute bypass usage to a single namespace.

### Negative

- Back-compat aliases mean two code paths to maintain for one release.
- The runtime file is one more piece of state to clean up at session end.
- Operators who relied on muscle memory for the old env names need to relearn.

## Acceptance criteria

1. `hooks/_lib/bypass-resolver.sh` exists, exports `cos_bypass_allows`, and
   resolves both `COS_BYPASS` and back-compat envs.
2. Every hook in `implementation_files` calls the resolver instead of reading
   its bypass env directly.
3. `docs/security/bypass-cheatsheet.md` lists at least the seven stable keys
   replacing the legacy envs and shows example invocations for each.
4. `tests/behavior/test_bypass_resolver.py` covers: allowlist hit, allowlist
   miss, back-compat alias hit, runtime-file precedence, whitespace tolerance.
5. Audit-trail entries from gate hooks include the stable key when bypass is
   honored.

## Verification

```bash
python3 -m pytest tests/behavior/test_bypass_resolver.py -q
grep -RIn "COS_BYPASS" hooks/ docs/security/bypass-cheatsheet.md
```
