# COS Bypass Cheatsheet

ADR-241 consolidates emergency bypasses under one session-scoped allowlist. There
are exactly two ways to hand a key to a hook, and which one you need depends on
whether you are blocked **right now**.

## Mid-session: the runtime file

A PreToolUse hook is a child of the harness, not of the shell that runs your
command. It cannot see anything you set after the harness started — except this
file, which the ADR-241 resolver re-reads on **every** invocation:

```bash
mkdir -p .cognitive-os/runtime
printf 'COS_BYPASS=direct_push\n' > .cognitive-os/runtime/bypass.env
```

Write it, retry the blocked command, and the next hook invocation sees the key.
This is the only route that works without relaunching.

## Next session: the environment

```bash
export COS_BYPASS=destructive_git,push_collision   # in the shell that LAUNCHES the harness
claude
```

The harness inherits the environment of the shell that started it, so an `export`
that happens **before** the launch reaches every hook. An `export` typed inside an
already-running session does not: it lives in a shell the hooks never touch.

## What does NOT work

```bash
COS_BYPASS=commit_guard git commit -m 'fix: emergency scoped change'   # ← inert
```

The prefix form sets the variable for `git`, which does not read it, and never for
the hook, which decided before that shell existed. Until 2026-08-19 this page
offered exactly that form in three examples; they are gone because they were
inert, not because the style changed. Proof that they stay gone:
`.venv/bin/python3 -m pytest tests/contracts/test_killswitch_activation_is_executable.py
-k prefijo`.

A handful of hooks additionally honour a **token inside the command**
(`--allow-destructive`, `--allow-branch-switch` in `destructive-git-blocker.sh`).
That works because the hook greps the command text for the literal — it is a
per-hook feature, not a general route, and each block message names the token when
its hook has one.

## Keys

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
| `direct_push` | `COS_ALLOW_DIRECT_PUSH` | direct push to protected branch | Requires reason. **No mid-session route**: the reason is read from the environment only, and `bypass.env` carries `COS_BYPASS` alone. |
| `direct_main` | `COS_ALLOW_DIRECT_MAIN` | direct commit to protected branch | Requires reason. Same caveat as `direct_push`. |
| `unproven_scope_both` | `COS_ALLOW_UNPROVEN_SCOPE_BOTH` | portability scope marker | Requires paired portability proof later. |

Keys whose bypass also demands a companion `*_REASON` variable can only be
activated at launch: the runtime file transports `COS_BYPASS` and nothing else.
