# ADR-273 Slice C — Anti-Drift Hooks (staging)

This directory holds the **3 hook scripts** designed for ADR-273 Slice C
(anti-drift hooks for the pending-truth ledger). They live here as staging
because `hooks/` is a protected control-plane path that requires explicit
operator authorization (`COS_ALLOW_PROTECTED_CONFIG_WRITE=1`).

## Why staging instead of hooks/

`hooks/protected-config-write-guard.sh` (PreToolUse Write) blocks agents
from creating new hooks without operator review. This is correct
governance — new hooks affect every session and need human sign-off
before activation.

Slice C is **designed and tested logically** but **not yet wired into the
hook registry**. To activate, the operator must perform the steps below.

## Files

- `pending-truth-drift-detector.sh` — PostToolUse Edit/Write hook. When
  a commit touches a path mentioned in any ledger item's `next_action` or
  `evidence`, emit `additionalContext` suggesting the operator/agent mark
  the source plan as done. Non-blocking nudge.
- `pending-truth-verify-weekly.sh` — Stop hook. Async: if the ledger
  hasn't been verified in 7 days OR >50% of items have stale
  `last_verified`, fire-and-forget `scripts/cos-pending-truth-verify
  --max-age-days 7` in background.
- `pending-truth-staleness-gate.sh` — PreToolUse Bash hook. When the
  command being run is `git commit*` and `pending-truth-latest.json` is
  older than 30 days, emit a non-blocking warning suggesting an
  aggregator + verifier refresh.

## Activation steps (operator-only)

```bash
# 1) Review each script. They are small (~50 LOC each). Check that:
#    - kill-switch and disable-env hooks are sourced
#    - hookSpecificOutput JSON is well-formed
#    - no destructive operations are performed

# 2) Move to hooks/ with explicit authorization
export COS_ALLOW_PROTECTED_CONFIG_WRITE=1
cp docs/runbooks/adr-273-slice-c-staging/pending-truth-drift-detector.sh hooks/
cp docs/runbooks/adr-273-slice-c-staging/pending-truth-verify-weekly.sh hooks/
cp docs/runbooks/adr-273-slice-c-staging/pending-truth-staleness-gate.sh hooks/
chmod +x hooks/pending-truth-*.sh

# 3) Register in cognitive-os.yaml > harness.hooks (operator edit):
#    - pending-truth-drift-detector: event=PostToolUse, matcher="Edit|Write", scope=both
#    - pending-truth-verify-weekly: event=Stop, async=true, scope=both
#    - pending-truth-staleness-gate: event=PreToolUse, matcher=Bash, scope=both

# 4) Project to harness settings via canonical pipeline:
bash scripts/apply-efficiency-profile.sh maintainer
# This updates .claude/settings.json and .codex/hooks.json via:
#   scripts/_lib/settings-driver-claude-code.sh
#   scripts/_lib/settings-driver-codex.sh

# 5) Smoke-test each hook with synthetic stdin (see ADR-273 §Slice C verification)

# 6) Validate audit pass:
python3 scripts/derived_artifact_gate.py
```

## Portability tests

Tests at `tests/red_team/portability/test_pending-truth-hooks.py` (sibling
file in this staging dir) provide bilateral + falsification probes for
each hook. They run AGAINST the staging scripts directly (they don't
require the hooks to be deployed to `hooks/` first).

## Cross-harness story

Per ADR-008 (Multi-Tool Support — Not Claude Code-Only) and ADR-064
(Hook Architecture v2), once registered in `cognitive-os.yaml`, the hooks
project to:
- `.claude/settings.json` (Claude Code)
- `.codex/hooks.json` (Codex CLI)
- `.cognitive-os/cos-runner-hooks.json` (bare-cli)

Same hook, three harness surfaces. No code change required between them.

## Why not wire immediately

The author of this commit (a sub-agent) does not have operator-level
authorization to modify the hook registry. Per ADR-273 §Slice C contract
+ rules/agent-quality.md ("no surfaces without operator review"), Slice C
is staged here for explicit human review before activation.
