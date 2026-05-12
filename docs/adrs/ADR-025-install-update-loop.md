---
adr: 25
title: Install/Update Loop — Closing the Advisory-Only Gap
status: accepted
implementation_status: partial
date: '2026-04-17'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-025: Install/Update Loop — Closing the Advisory-Only Gap

**Date:** 2026-04-17
**Status:** Accepted
**Related:** ADR-018 (Docker-to-pip), commit 6de320c (Lote 1 order fix), PRs #6 (16f5e1a) and #10 (1540ef4 / v0.10.0)

## Context

Until v0.10.0 the install/update pipeline was advisory-only: `install.sh` and
`cos-update.sh` would **report** missing Python deps and MCPs but never install
them.  PR #6 ("install.sh runs manifest-check post-install") promised
installation in its title but delivered only reporting — a BLOCKER documented in
the Q1 audit (2026-04-17).

Two related problems surfaced simultaneously:

1. **First-time setup gap** — a developer who cloned the repo and ran
   `bash install.sh` still needed to manually run `uv sync` and
   `bash scripts/register-mcps.sh` to get a working environment.

2. **Drift bug in register-mcps.sh** — the SHA cache gate (lines ~327-330,
   pre-fix) caused declared-vs-actual state drift:
   - Manifest declares A, B, C.  First run installs all.  SHA saved.
   - User manually removes B (`claude mcp remove B` or edits `settings.json`).
   - `git pull` with **no manifest change** → SHA unchanged → early-exit fires →
     B is never reinstalled.

Both problems share the same root cause: the pipeline trusted a cached signal
(manifest SHA) as a correctness gate rather than as a performance hint.

## Decision

Three coordinated decisions made on 2026-04-17 across v0.10.0 and follow-up
commits:

### 1. cos-update.sh as the auto-update spine

`cos-update.sh` runs `uv sync` and `register-mcps.sh` automatically on every
update.  Phase order:

```
pull-images → uv sync → register-mcps → self-install → verify
```

`uv` runs **before** `self-install` because hooks written by `self-install` may
import newly-added Python deps; installing deps first ensures hooks are
functional immediately.  Failures in this phase are WARN-only (non-fatal) so
partial or offline environments can still apply whatever they can.

### 2. install.sh as opt-in installer

By default `install.sh` remains advisory (preserving PR #6 behavior).  A new
`--install-deps` flag triggers actual installation.  Rationale: first-time users
expect a clean install without surprises; explicit opt-in protects against
unintended writes to `~/.claude/settings.json` during CI or paired-session
workflows.

### 3. Two-layer idempotence

Both `uv sync` and `register-mcps.sh` implement two layers of idempotence:

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| SHA cache | `.cognitive-os/state/{pyproject,mcps}.sha` | Fast-path — detect manifest changes without expensive per-item checks |
| Per-item check | `uv sync` is internally idempotent; `register-mcps.sh` queries `claude mcp list` before each add | Correctness — handle local state drift when declared ≠ actual |

The SHA cache is a **performance hint**, not a correctness gate.  The per-item
check is always authoritative.

## MCP Registration Strategy

Priority order (unchanged from v0.9.x):

1. `claude` CLI on PATH: `claude mcp add <name> <command> [args…]`
2. `claude` absent: deep-merge `mcpServers` into `~/.claude/settings.json` via
   Python (atomic tempfile + rename).  Non-destructive — preserves all other
   keys.
3. Neither available: WARN and exit 0.

## Drift Handling

The SHA cache records whether the manifest file has changed since the last run.
Using it as an early-exit caused the drift bug described above.  The fix removes
the early-exit block (was lines 327-330) and adds an explanatory comment:

```bash
# The SHA cache is a PERFORMANCE HINT, NOT a correctness gate.
# Per-item checks (via `claude mcp list`) always run because the declared
# state (manifest) can desync from actual state (user removals, partial
# installs, crashed installs).
```

The SHA is still written at end-of-run for telemetry and change-detection
logging.  A `--force` flag (`bash scripts/cos-update.sh --force`) triggers a
full re-run regardless of SHA, useful for manual drift recovery.

## Consequences

### Positive

- Cold-clone `bash install.sh --install-deps` produces a fully working
  environment in a single command.
- Subsequent `git pull` invokes `cos-update.sh` via the post-merge hook and
  keeps Python deps and MCPs current automatically.
- Drift recovery is automatic — any `cos-update.sh` run (including the
  post-merge hook) will reinstall removed MCPs even when the manifest is
  unchanged.

### Negative

- Every update run pays a `claude mcp list` call plus a per-MCP compare.
  Amortized overhead is <100ms total.
- `install.sh` without `--install-deps` still produces a half-working state.
  Users who expect auto-install may be confused.  This is documented in
  `--help` output and in the manifest-check report.

## Alternatives Considered

### Always-install in install.sh
Simpler UX.  Rejected because it is destructive by default with no opt-in,
which breaks CI workflows and paired-session setups where `install.sh` is run
for inspection only.

### SHA-cache as sole gate
Simpler implementation.  Rejected because it causes the drift bug (BLOCKER in
Q1 audit).  The cached SHA only reflects whether the *declared* state changed,
not whether the *actual* registered state matches declaration.

### Separate `claude-mcp-check` lint that never writes
Keeps installation fully manual.  Rejected because it forces developers to read
reports and act on them manually — it does not close the loop.  The same gap
that existed before PR #6 would persist.

## References

- PR #6 (16f5e1a) — install.sh manifest-check (advisory-only, the gap)
- PR #10 (1540ef4, v0.10.0) — uv sync and register-mcps in cos-update.sh
- Commit 6de320c — Lote 1: uv sync order fix (uv before self-install)
- Commit [0db8c14](https://github.com/Luum-Home/luum-cognitive-os/commit/0db8c14) — Lote 2: register-mcps loop + drift fix (this ADR)
- Q1 audit 2026-04-17 — documented BLOCKER: install pipeline advisory-only
- `scripts/register-mcps.sh` — implementation
- `scripts/cos-update.sh` — auto-update spine
- `tests/behavior/test_register_mcps.py` — regression test including
  `test_reregisters_when_mcp_missing_despite_unchanged_manifest`
