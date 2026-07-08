---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/adr-273-slice-c-staging/README.md
provenance: "Documents why ADR-273 Slice C's three anti-drift hooks are staged outside hooks/ rather than deployed, and gives the operator the exact review-and-activation procedure required because agents cannot write to the protected hook registry."
---

## What it is

A staging-directory README explaining why 3 designed-and-tested hook scripts for the pending-truth ledger (ADR-273 Slice C) live in `docs/05-Methodology/runbooks/adr-273-slice-c-staging/` instead of `hooks/`, and the exact steps an operator must take to activate them.

## Key mechanics

- **Why staged**: `hooks/protected-config-write-guard.sh` (a PreToolUse Write hook) blocks agents from creating new hooks without operator review — new hooks affect every session, so human sign-off is required before activation. The sub-agent that authored this batch lacks operator-level authorization to modify the hook registry (per ADR-273 §Slice C contract and `rules/agent-quality.md`, "no surfaces without operator review").
- **The 3 staged hooks**: `pending-truth-drift-detector.sh` (PostToolUse Edit/Write — non-blocking nudge when a commit touches a path referenced in a ledger item), `pending-truth-verify-weekly.sh` (Stop hook — async fire-and-forget verifier refresh if the ledger is >7 days stale or >50% items are stale), `pending-truth-staleness-gate.sh` (PreToolUse Bash — non-blocking warning on `git commit*` if `pending-truth-latest.json` is >30 days old).
- **Activation is a 6-step operator procedure**: review scripts for kill-switch sourcing / well-formed hookSpecificOutput / no destructive ops → copy into `hooks/` under `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` → register in `cognitive-os.yaml > harness.hooks` → project to harness settings via `scripts/apply-efficiency-profile.sh maintainer` (which drives `settings-driver-claude-code.sh` / `settings-driver-codex.sh`) → smoke-test with synthetic stdin → validate with `scripts/derived_artifact_gate.py`.
- **Portability tests already exist** at `tests/red_team/portability/test_pending-truth-hooks.py`, run directly against the staging scripts (no deployment required first).
- **Cross-harness projection**: per ADR-008 and ADR-064, once registered in `cognitive-os.yaml` the same hook definition projects to all three harness surfaces (`.claude/settings.json`, `.codex/hooks.json`, `.cognitive-os/cos-runner-hooks.json`) with no code change needed between them.

## Relations & where used

Depends on `hooks/protected-config-write-guard.sh` (the gate this staging pattern works around) and is one of three sibling staging directories using the identical discipline — see `adr-274-validator-extension-staging` and `adr-275-session-start-hook-staging` in the same runbooks directory.

## Status / caveats

Describes a point-in-time staged-but-not-deployed state; the README itself notes the hooks are "designed and tested logically" but "not yet wired into the hook registry" as of this writing — readers should check `hooks/` directly to confirm current deployment status rather than trusting this doc alone. No internal inconsistencies found.
