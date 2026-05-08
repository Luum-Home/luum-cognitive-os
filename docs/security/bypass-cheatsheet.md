# COS Bypass Cheatsheet

ADR-241 consolidates emergency bypasses under one session-scoped allowlist:

```bash
export COS_BYPASS=destructive_git,push_collision
```

PreToolUse hooks can also read `.cognitive-os/runtime/bypass.env`:

```bash
mkdir -p .cognitive-os/runtime
printf 'COS_BYPASS=direct_push\n' > .cognitive-os/runtime/bypass.env
```

Bypasses are emergency controls. Prefer fixing the underlying finding or using a
higher-level COS command. Legacy env vars remain as aliases for one release, but
new hooks should call `cos_bypass_allows <key>` from `hooks/_lib/bypass-resolver.sh`.

| Stable key | Legacy alias | Scope | Notes |
|---|---|---|---|
| `destructive_git` | `COS_ALLOW_DESTRUCTIVE_GIT`, `COS_GIT_BYPASS` | destructive git operations | Does not replace explicit `--allow-*` command tokens. |
| `main_branch_write` | `COS_ALLOW_MAIN_BRANCH_WRITE`, `COS_ALLOW_DIRECT_MAIN` | protected branch writes | Requires a reason in direct-main flows. |
| `branch_switch` | `COS_ALLOW_BRANCH_SWITCH` | branch context switches | Use only when operator explicitly accepts commit destination change. |
| `reset_over_wip` | `COS_ALLOW_RESET_OVER_WIP` | reset/stash WIP guard | Logs WIP bypass evidence. |
| `commit_guard` | `COS_BYPASS_COMMIT_GUARD` | commit scope guard | Use for emergency commits only. |
| `branch_ownership` | `COS_ALLOW_BRANCH_OWNERSHIP_OVERRIDE` | branch lock | Use only after checking liveness. |
| `claim_gate` | `COS_ORCHESTRATOR_CLAIM_GATE_MODE=warn` | orchestrator claim gate | Prefer fixing claim evidence. |
| `push_collision` | `DISABLE_HOOK_PUSH_COLLISION_CHECK` | push collision detector | Prefer ADR-243 post-rewrite marker. |
| `direct_push` | `COS_ALLOW_DIRECT_PUSH` | direct push to protected branch | Requires reason. |
| `direct_main` | `COS_ALLOW_DIRECT_MAIN` | direct commit to protected branch | Requires reason. |
| `unproven_scope_both` | `COS_ALLOW_UNPROVEN_SCOPE_BOTH` | portability scope marker | Requires paired portability proof later. |

Examples:

```bash
COS_BYPASS=branch_switch bash -lc 'git switch release/prepare'
COS_BYPASS=push_collision git push --force-with-lease
COS_BYPASS=commit_guard git commit -m 'fix: emergency scoped change'
```
