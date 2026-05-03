# Second Demotion Candidate Resolution — 2026-05-03

## Context

`scripts/cos-manifest-tier-claim-audit --json` identified nine projected
advisory primitives as candidates for a second ADR-126 demotion. The goal was not
mass deletion. The goal was to prove that candidate surfacing can drive one real
lifecycle transition while leaving safety/recovery hooks intact when their role
is still justified.

## Decision

Demote `hooks/context-watchdog.sh` from default runtime projection.

Why this one:

- It is a `PostToolUse` wildcard hook, so default projection adds per-tool-call
  runtime surface.
- It is advisory-only (`exit_0`) and does not block unsafe state.
- Hard compaction safety remains covered by `hooks/pre-compaction-flush.sh` and
  the explicit memory/session-summary protocol.
- It remains available on disk for opt-in maintainer sessions.

This is a **manifest-tier-audit-signed demotion**, not an ROI-signed demotion.
The ROI dashboard still has not signed a demotion decision.

## Candidate resolution table

| Candidate | Resolution | Rationale |
|---|---|---|
| `hooks/context-watchdog.sh` | **Demoted** | Advisory wildcard `PostToolUse` hook; shrinks default runtime surface without removing opt-in capability. |
| `hooks/destructive-rm-blocker.sh` | Keep, harden separately | Core runtime-safety primitive. It is advisory in operator context but blocks agent-context destructive file erasure. Better candidate for maturity/evidence clarification than demotion. |
| `hooks/engram-daemon-launcher.sh` | Keep maintainer/observe | Engram startup remains part of the maintainer memory lifecycle. Not externally adoptable; revisit during ADR-132 Shape B work. |
| `hooks/engram-reinforce-on-access.sh` | Keep maintainer/advisory | Supports memory lifecycle reinforcement. Revisit after Engram daemon reliability and usage metrics mature. |
| `hooks/rate-limit-precheck.sh` | Keep maintainer/advisory | Protects live sessions from provider/rate-limit friction; demote only if false-positive/no-use evidence appears. |
| `hooks/session-init.sh` | Keep projected | Core SessionStart marker used by the runtime/session lifecycle. Not a safe demotion target despite advisory maturity. |
| `hooks/session-resume.sh` | Keep projected | Session continuity/recovery primitive; the right action is evidence clarification, not demotion. |
| `hooks/session-start-stash-reapply.sh` | Keep projected | WIP recovery primitive directly tied to the stash-loss incident class. |
| `hooks/validation-lock-cleanup.sh` | Keep projected | Validation capsule recovery primitive tied to stale lock/worktree cleanup. |

## Verification

```bash
scripts/cos-manifest-tier-claim-audit --json
scripts/cos-demotion-loop-audit --json
python3 scripts/derived_artifact_gate.py --json
python3 scripts/cos_architecture_readiness.py --json
bash scripts/cos-ci-local.sh quick
```

Expected state after this change:

- `context-watchdog.sh` is absent from `.claude/settings.json` default projection.
- `hooks/context-watchdog.sh` remains in the repository for opt-in use.
- `demotion_count` becomes `2`.
- `roi_signed_demotion_count` remains `0`, so `demotion-loop-maturity` still
  warns until a future ROI-signed demotion lands.
