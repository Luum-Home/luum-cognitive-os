# ADR-028 D1.B — Process Registry Clients: Deferred Sites

Created: 2026-04-20
Status: Non-migrated sites from initial D1.B wiring sprint.

## Summary

Initial sprint wired the top 5 highest-value background-spawn sites.
This document tracks all remaining sites for follow-up.

## Already Migrated (this sprint)

| Site | File | Line | owner_label | ttl | kind |
|---|---|---|---|---|---|
| skill-usage-tracker | `hooks/skill-usage-tracker.sh` | 93 | skill-usage-tracker | 30 | short_lived |

The `_register_bg` helper in `hooks/_lib/register-bg.sh` is also available for
future bash sites.

## Deferred Sites

### P1 — Wrap when safe (manual PID consumed downstream)

| Site | File:Line | Pattern | Spawn Kind | Reason Deferred |
|---|---|---|---|---|
| execute-repair apply | `hooks/_lib/execute-repair.sh:336` | `( _repair_apply_fix ... ) &` then `local apply_pid=$!` | short_lived | **AMBIGUOUS** — `apply_pid` is immediately captured and used in a `kill -0` wait-loop. Wrapping with `_register_bg` would interpose and the registration subshell PID would overwrite `$!`. Cannot wrap without refactoring the wait loop. Safe approach: extract the fix subprocess, assign PID before registration call, then register separately. |

### P2 — Investigate before wiring

| Site | File:Line | Pattern | Spawn Kind | Reason Deferred |
|---|---|---|---|---|
| git post-push hook | `scripts/setup-git-hooks.sh:146` | `( sleep 2 && auto-update-projects.sh ) &` | short_lived | This is a git hook template embedded in a setup script, not a Claude hook. Git hooks are NOT registered in Claude settings.json. Per `rules/ROADMAP.md` §1.8 pattern, git hooks are "intentionally out of scope" for Claude hook wiring. If the subprocess becomes long-lived, register inside `auto-update-projects.sh` itself. |
| _archived auto-repair-dispatcher | `hooks/_archived/auto-repair-dispatcher.sh.bak:320` | `nohup bash -c "..." &` | detached_daemon | **ARCHIVED** — file is `.bak`, not active. Skip unless the hook is un-archived. |

### P3 — Python `subprocess.Popen` sites

| Site | File:Line | Pattern | Spawn Kind | Reason Deferred |
|---|---|---|---|---|
| claude_executor.py | `lib/claude_executor.py:432` | `subprocess.Popen([...], start_new_session=True)` | detached_daemon | The executor `wait()`s on the process (blocking, with timeout). It is NOT fire-and-forget. The PID is fully managed by the executor — no orphan risk. Register only if we want reaper visibility for very long-running agent invocations. Owner would be `"claude-executor"`, kind `"detached_daemon"`, ttl = `default_timeout`. Medium-effort change. |

## Fix Plan for execute-repair (P1)

The wait-loop pattern:

```bash
( _repair_apply_fix ... ) &
local apply_pid=$!
while kill -0 "$apply_pid" 2>/dev/null; do ... done
```

Safe wrap without changing semantics:

```bash
( _repair_apply_fix ... ) &
local apply_pid=$!
# Register separately — does NOT change apply_pid
(
  COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" python3 - "$apply_pid" <<'PYEOF' >/dev/null 2>&1
import sys, os; root = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd(); sys.path.insert(0, root)
try:
    import lib.process_registry as process_registry
    process_registry.register(int(sys.argv[1]), "execute-repair-apply", 120, "short_lived")
except Exception: pass
PYEOF
) &
# Original wait-loop unchanged
while kill -0 "$apply_pid" 2>/dev/null; do ...
```

This does not change `apply_pid` because the registration happens in a separate subshell whose `$!` is never captured by the caller.
