# Incident: Session-Startup Multi-Spawn Hang (2026-05-01)

**Severity**: High — operator-blocking 5+ minute hang on every fresh session in `luum-agent-os`.
**Status**: Hardened 2026-05-01. Initial mitigation shipped two structural fixes; follow-up hardening now gates subagent SessionStart fan-out and serializes self-install git config repair.
**Detected**: 2026-05-01 by operator report (chat UI showed duplicate prompts and a "5m 0s" timer).
**Engram**: `incident/2026-05-01-session-3-spawn-hang`.

## TL;DR

Two issues compounded into a 5-minute startup hang:

1. **Cross-filesystem `mv` in `scripts/_lib/settings-driver-claude-code.sh`** — `mktemp` defaulted to `$TMPDIR` (often `/var/folders/...` on macOS), which is on a different filesystem from the project's `.claude/` directory. Cross-filesystem `mv` degrades from a single atomic `rename(2)` to copy + unlink. During the copy window, the IDE file-watcher could observe a half-written `settings.json` and trigger a session re-spawn.

2. **No mutex in `hooks/profile-drift-autoapply.sh`** — when N parallel sessions all detected a stale hash, all N concurrently called `apply-efficiency-profile.sh`, racing to write `settings.json`. Each partial write triggered another re-spawn.

The two together created a positive-feedback loop: re-spawn → more concurrent F8 → more partial writes → more re-spawns.

## Timeline (2026-05-01 13:36 UTC)

```
13:36:26.x   Operator launches a fresh session in luum-agent-os.
             dispatch-gate / clarification-gate / blast-radius / agent-prelaunch
             fire on PID set A → confirms a parallel-Agent invocation in flight
             from a previous chat turn (orchestrator-mode session).

13:36:27.x   First session-init (PID 90471) fires SessionStart hooks (17 of them).
             profile-drift-autoapply.sh detects hash drift (last applied
             2026-04-30T20:35Z, >17h prior).
             apply-efficiency-profile.sh starts writing settings.json via
             mktemp (in /tmp) + mv → cross-FS, slow.

13:36:27.x   IDE watcher observes settings.json mid-rename → spawns Session 2.
             Session 2 also runs F8, also detects drift (hash file not yet
             written by Session 1 because apply hasn't finished), also calls
             apply-efficiency-profile.sh.

13:36:28.x   Sessions 3 and 4 spawn (same path).
             Net: PIDs 95214, 95642, 95912, 96549 all run 17 SessionStart
             hooks each. self-install.sh in each session attempts git config
             writes → race on .git/index.lock.

13:36:28-45  10x session-init invocations recorded in hook-timing.jsonl;
             10x self-knowledge-refresh; 4 distinct session dirs created.
             Wall-clock from operator perspective: ≥5 minutes blocked.
```

## Root cause

**Two independent bugs that interact destructively.** Either alone is annoying; together they form a feedback loop.

### Bug A: Non-atomic settings.json write

`scripts/_lib/settings-driver-claude-code.sh` previously did:

```bash
TMP_OUT="$(mktemp)"               # → $TMPDIR (often a different FS)
trap 'rm -f "$TMP_OUT"' EXIT
cc_driver_emit > "$TMP_OUT"
mv "$TMP_OUT" "$SETTINGS_FILE"    # cross-FS → copy + unlink, NOT atomic
```

Atomicity guarantees from `rename(2)` only hold within a single filesystem. Across filesystems, `mv` falls back to `cp` + `unlink(src)`, leaving a window during which `settings.json` exists but is partially populated. The Claude Code file-watcher reads the file as soon as it changes; a partial read triggers session re-init.

### Bug B: No mutex on the autoapply hook

`hooks/profile-drift-autoapply.sh` (F8 from ADR-071, shipped 2026-04-27) read the hash file, compared, applied. Three concurrent invocations would each pass the hash check, each enter the apply, all racing on the same output file.

The bug was a TOCTOU: read hash (T1), call apply (T2). Between T1 and T2, another process could have already started its own apply. Only one apply can finish first; the rest do redundant work that may corrupt the partially-written settings.json.

## Fixes shipped (2026-05-01)

### Fix 1: dest-dir `mktemp` → atomic rename

`scripts/_lib/settings-driver-claude-code.sh`:

```bash
SETTINGS_DIR="$(dirname "$SETTINGS_FILE")"
TMP_OUT="$(mktemp "$SETTINGS_DIR/.settings.json.XXXXXX")"
...
mv "$TMP_OUT" "$SETTINGS_FILE"   # same FS → single rename(2), atomic
```

By placing the temp file inside the destination directory, the subsequent `mv` is guaranteed to be a single `rename(2)` syscall on the same filesystem. Readers (including the IDE watcher) always observe either the complete old file or the complete new file — never a partial state.

### Fix 2: non-blocking `flock` on autoapply

`hooks/profile-drift-autoapply.sh`:

```bash
exec 9>"$LOCK_FILE"
if command -v flock &>/dev/null; then
    if ! flock -n 9; then
        exit 0   # another process is applying; no-op
    fi
fi
# Re-read hash UNDER LOCK (TOCTOU prevention).
last_hash=$(cat "$HASH_FILE" 2>/dev/null || echo "")
if [ "$current_hash" = "$last_hash" ]; then exit 0; fi
# ... apply ...
```

`flock -n` returns immediately. The first invocation acquires the lock; concurrent invocations exit silently. After the winner re-reads the hash file under lock, it ensures TOCTOU safety: if a previous winner already applied between the initial check and lock acquisition, the second check catches it and exits without re-applying.

`flock` is unavailable on some macOS configurations (no `util-linux` installed). In that case the hook falls through to the unguarded path — accepted because the race window is now narrow enough (post-Fix 1) to be a soft hazard rather than a hard incident.

## Tests added

13 integration tests in two new files:

### `tests/integration/test_profile_drift_autoapply_flock.py` (5 tests)
- `test_single_invocation_applies_when_drift_detected` — baseline correctness.
- `test_no_apply_when_hash_matches` — no spurious re-applies.
- `test_concurrent_invocations_only_apply_once` — **the load-bearing test**: 5 parallel invocations against a stub apply that sleeps 1s; asserts exactly 1 apply occurred AND total wall time < 4s (i.e. flock is non-blocking, not serializing).
- `test_lock_released_after_completion` — the lock doesn't persist; sequential runs each apply.
- `test_optout_env_var_short_circuits` — `COS_DISABLE_PROFILE_AUTOAPPLY=1` bypasses both lock and apply.

### `tests/integration/test_settings_atomic_write.py` (8 tests)
- `test_driver_uses_dest_dir_mktemp` — structural invariant: source contains `mktemp "$SETTINGS_DIR/...XXXXXX"`.
- `test_driver_no_bare_mktemp_followed_by_mv_to_settings` — historic anti-pattern guard.
- `test_driver_documents_atomicity_rationale` — comment must explain WHY (regression prevention).
- `test_no_other_unsafe_mktemp_to_settings_patterns` — **codebase audit** scanning all bash files for the same anti-pattern (bare `mktemp` whose output is `mv`d to `.claude/`, `.codex/`, `settings.json`, or `hooks.json`). Currently 0 hits.
- `test_driver_writes_valid_json` — end-to-end smoke.
- `test_concurrent_reader_never_observes_partial_json` — **stress test**: a reader thread tails settings.json while the driver runs 20 times in quick succession. Reader must never observe empty or invalid JSON.
- `test_no_orphan_tmp_files_after_driver_run` — trap cleanup verified.
- `test_tmp_file_lives_on_same_filesystem_as_destination` — runtime check via `st_dev`: when a tmp file is captured, its filesystem device matches the destination's.

All 13 pass on the fixed code; the codebase audit confirms no other locations need the same fix.

## Operator workaround (during incident)

Until the fix lands in your local checkout:

```bash
pkill -f "claude code" 2>/dev/null
pkill -f "codex" 2>/dev/null
rm -f .git/index.lock
rm -f .cognitive-os/runtime/*.lock
rm -rf .cognitive-os/sessions/177764260*
# Then start ONE new session.
```

Defensive opt-out (skips the autoapply hook entirely):

```bash
export COS_DISABLE_PROFILE_AUTOAPPLY=1
```

## Follow-up hardening shipped (2026-05-01)

These changes are defense-in-depth on top of the initial mitigation. They address the screenshot symptom class where startup/resume/subagent churn can duplicate visible prompt context or stall the first turn.

### Fix 3: centralized subagent SessionStart gate

`scripts/hook-timing-wrapper.sh` now captures hook stdin once, parses the hook JSON, exports normalized context (`COGNITIVE_OS_SESSION_SOURCE`, `COGNITIVE_OS_HOOK_AGENT_TYPE`, `COGNITIVE_OS_HOOK_AGENT_ID`, `COGNITIVE_OS_SESSION_KIND`), and skips `SessionStart` hook bodies when the invocation is subagent-shaped. Detection is intentionally multi-signal:

- `agent_id` present in hook JSON.
- `transcript_path` contains `/subagents/`.
- `SessionStart` includes `agent_type`.
- `CLAUDE_SUBAGENT_ID` or `COS_SUBAGENT_ID` is present in env.

The skip is centralized in the wrapper instead of duplicated across 17 individual hooks. `SubagentStart` remains the intended subagent context path; `SessionStart` is treated as orchestrator-scope because it performs self-install, daemon launch, settings projection, recovery, and session registration. Operators can temporarily disable the skip with `COS_DISABLE_SUBAGENT_SESSIONSTART_SKIP=1`.

The timing log now includes `session_kind` and `skipped` fields so future RCA can distinguish real hook latency from intentional subagent suppression.

### Fix 4: stdout quarantine for context-bearing hook events

Claude Code treats `SessionStart` and `UserPromptSubmit` stdout as model context. Several COS hooks historically printed human diagnostics to stdout. When startup re-spawned or prompt submission retried, that stdout could become extra model context and amplify the duplicate-prompt symptom.

The wrapper now redirects stdout to stderr for diagnostic hooks on context-bearing events while preserving stdout for hooks that intentionally inject context:

- Allowed SessionStart context: `session-startup-protocol`, `session-resume`.
- Quarantined: other `SessionStart` hooks and `UserPromptSubmit:user-prompt-capture`.
- Direct script invocations keep historical stdout for tests/operator debugging.
- Emergency opt-out: `COS_DISABLE_HOOK_STDOUT_QUARANTINE=1`.

`hooks/user-prompt-capture.sh` also suppresses the JSON emitted by `lib/process_user_message.py`; that output is observability, not prompt context.

### Fix 5: non-blocking lock around self-install git config repair

`hooks/self-install.sh` now wraps the `git config core.hooksPath .githooks` repair with a non-blocking repo-local lock (`.git/cos-self-install-git-config.lock`). It uses `flock` when available and Python `fcntl` as the macOS fallback. Lock losers exit advisory-success rather than blocking session start.

### Tests added

`tests/integration/test_sessionstart_subagent_scope.py` verifies:

- Subagent-shaped `SessionStart` input is skipped centrally and records `session_kind=subagent`, `skipped=1`.
- Orchestrator `SessionStart` still runs and receives the original stdin, with diagnostic stdout quarantined from model context.


### Fix 6: startup circuit breaker / bounded safe mode (ADR-101)

`scripts/hook-timing-wrapper.sh` now detects `SessionStart` storms and activates bounded safe mode via `.cognitive-os/runtime/startup-safe-mode.json`. While active, `SessionStart` hook bodies are skipped before they can mutate watched settings, launch daemons, or write model-visible stdout. Operators can force recovery with `bash scripts/cos-startup-recover.sh` or a manual kill-switch file `.cognitive-os/runtime/disable-sessionstart-hooks`. Timing records include `safe_mode` and `skip_reason` for RCA.

## Remaining watch items

- **Atomic write across all settings/hooks projection scripts** — the audit test `test_no_other_unsafe_mktemp_to_settings_patterns` remains the regression guard; if a future change introduces a new unsafe pattern, CI catches it. Codex driver and any future harness drivers must follow the same invariant.
- **Empirical Claude Code subagent markers** — the wrapper uses all currently documented and observed signals, but if a future Claude Code release changes subagent hook input shape, update `test_sessionstart_subagent_scope.py` first, then the parser.

## Cross-references

- Engram: `incident/2026-05-01-session-3-spawn-hang` (full RCA report from SRE agent)
- ADR-071 §F8 (`profile-drift-autoapply.sh` design — should reference this incident in addendum)
- ADR-088 (provenance marker — helps trace concurrent sub-agent sessions)
- `docs/SESSION-HANDOFF-2026-05-01.md` §"Active incident" (operator-facing summary)
- `tests/integration/test_profile_drift_autoapply_flock.py`
- `tests/integration/test_settings_atomic_write.py`
- `scripts/_lib/settings-driver-claude-code.sh` lines 377-390 (the fix)
- `hooks/profile-drift-autoapply.sh` (the fix)
