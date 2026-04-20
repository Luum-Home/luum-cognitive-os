# Hook Audit — April 2026

**Scan date:** 2026-04-20
**Hooks scanned:** 130 (all `hooks/*.sh` excluding `_lib/` and `_archived/`)
**Auditor model:** claude-sonnet-4-6 (read-only, ADR-028 Phase C / D3)
**Summary:** 18 findings across 16 hooks — 2 BLOCKERs, 9 CONCERNs, 7 SUGGESTIONs.
Anti-patterns detected: `test_run_inside_hook` (3), `subproc_without_timeout` (7), `unbounded_loop` (1), `unrotated_write` (3), `global_state_write` (0 direct write but 1 read-to-path concern), `bg_without_pid_track` (1), `destructive_git` (1).

---

## Findings Table

| hook | line_range | anti_pattern | severity | evidence | proposed_fix_class |
|------|-----------|--------------|----------|----------|--------------------|
| `hooks/pre-commit-gate.sh` | 26 | `test_run_inside_hook` | BLOCKER | `"test_output=$(python3 -m pytest tests/ -q --tb=no 2>&1 | tail -1)"` | `remove_test_run` |
| `hooks/test-baseline-diff.sh` | 50 | `test_run_inside_hook` | BLOCKER | `"AFTER=$(python3 -m pytest --tb=no -q 2>&1 | tail -5) || true"` | `remove_test_run` |
| `hooks/session-cleanup.sh` | 70-87 | `unbounded_loop` | CONCERN | `"while true; do if mkdir \"$_lock_dir\" 2>/dev/null;"` | `bounded_loop_guard` |
| `hooks/orchestrator-mode-detect.sh` | 8-20 | `subproc_without_timeout` | CONCERN | `"python3 -c \"... OrchestratorCapabilities().detect()\""` | `add_timeout_30s` |
| `hooks/mlflow-sync.sh` | 5-15 | `subproc_without_timeout` | CONCERN | `"python3 -c \"from lib.mlflow_bridge import MLflowBridge..."` | `add_timeout_30s` |
| `hooks/session-hygiene.sh` | 3-10 | `subproc_without_timeout` | CONCERN | `"python3 -c \"from lib.session_hygiene import run_full_hygiene..."` | `add_timeout_30s` |
| `hooks/ecosystem-check.sh` | 24-42 | `subproc_without_timeout` | CONCERN | `"python3 -c \"from lib.ecosystem_evaluator import EcosystemEvaluator..."` | `add_timeout_30s` |
| `hooks/usage-health-check.sh` | 19-27 | `subproc_without_timeout` | CONCERN | `"python3 -c \"from lib.component_usage_tracker import ComponentUsageTracker..."` | `add_timeout_30s` |
| `hooks/adr-detector.sh` | 79-93 | `subproc_without_timeout` | CONCERN | `"RESULT=$(python3 -c \"...analyze_commit...\") || exit 0"` | `add_timeout_30s` |
| `hooks/code-review-on-commit.sh` | 59-86 | `subproc_without_timeout` | CONCERN | `"review_output=$(cd \"$ROOT_DIR\" && python3 -c \"...CodeReviewer..."` | `add_timeout_30s` |
| `hooks/pre-commit-gate.sh` | 67-69 | `unrotated_write` | CONCERN | `">> \"$COVERAGE_HISTORY\""` — no rotation owner for `coverage-history.jsonl` | `migrate_to_metric_event` |
| `hooks/content-policy.sh` | 117 | `unrotated_write` | SUGGESTION | `">> \"$METRICS_DIR/content-policy.jsonl\""` | `migrate_to_metric_event` |
| `hooks/predev-completeness-check.sh` | 84, 97 | `unrotated_write` | SUGGESTION | `">> \"$METRICS_DIR/predev-completeness.jsonl\""` | `migrate_to_metric_event` |
| `hooks/confidentiality-enforcer.sh` | 96 | `unrotated_write` | SUGGESTION | `">> \"$METRICS_DIR/confidentiality-enforcer.jsonl\""` | `migrate_to_metric_event` |
| `hooks/rate-limit-protection.sh` | 35-72 | `test_run_inside_hook` | SUGGESTION | `"read -r TOKENS_USED AGENTS_USED < <(python3 - \"$COST_EVENTS\""` — full duplicate of `token-budget-monitor.sh` | `remove_test_run` |
| `hooks/session-cleanup.sh` | 123 | `destructive_git` | SUGGESTION | `"rm -rf \"$SESSION_DIR\""` — path resolved from env var, no guard verifying SESSION_DIR is inside project | `move_to_runtime_dir` |
| `hooks/global-verify.sh` | 47-213 | `test_run_inside_hook` | SUGGESTION | `"cmd = [\"python3\", \"-m\", \"pytest\", \"--tb=no\", \"-q\"] + list(test_ids)"` — pytest invoked inline; ADR-027 §1 already owns this | `remove_test_run` |
| `hooks/skill-usage-tracker.sh` | 74-93 | `bg_without_pid_track` | CONCERN | `") </dev/null >/dev/null 2>&1 &\n_TRACKER_PID=$!"` — registration subshell itself spawned with `&` (line 110) but its PID is never registered | `register_pid_and_timeout` |

---

## Finding Detail Notes

### BLOCKER-1 — `hooks/pre-commit-gate.sh` line 26: `test_run_inside_hook`
`python3 -m pytest tests/ -q --tb=no` is invoked synchronously inside a PreCommit hook with no timeout guard. If the test suite hangs, the commit hangs indefinitely. ADR-027 Phase 1 designates `global-verify.sh` as the single pytest entry-point; this hook duplicates and bypasses that contract.

### BLOCKER-2 — `hooks/test-baseline-diff.sh` line 50: `test_run_inside_hook`
`python3 -m pytest --tb=no -q` runs the full suite at Stop time. Originally this was session-init's baseline runner which was **explicitly disabled** (session-init.sh line 124–129 comment) after leaking ~190 orphaned processes. The Stop version retains the same unbounded run with no timeout and no PID tracking.

### CONCERN-3 — `hooks/session-cleanup.sh` lines 70-87: `unbounded_loop`
The mkdir-based advisory lock loop is bounded by `_lock_deadline = $(( $(date +%s) + 30 ))` on line 69, so technically it has a 30-second deadline — **however** the `break` only fires when `date +%s` is polled and the outer deadline check is inside the loop body, not the `while` condition. On a system where `date` is slow (under load, NFS, sandbox), the loop can run far past 30 s because the deadline is only checked after `sleep 0.2`. This is a potential race/hang under load.

### CONCERN-4–10 — `subproc_without_timeout` (7 hooks)
Seven hooks invoke `python3` for potentially I/O-bound library operations (MLflow, ecosystem evaluation, orchestrator capability detection, component health, etc.) without a `timeout Ns` shell guard. The injected Python code calls into network-touching or large-file-parsing libraries. If those block, the hook delays or hangs session start/stop events.

| hook | line | call |
|------|------|------|
| `orchestrator-mode-detect.sh` | 8 | `python3 -c "...OrchestratorCapabilities().detect()"` |
| `mlflow-sync.sh` | 5 | `python3 -c "from lib.mlflow_bridge import MLflowBridge..."` |
| `session-hygiene.sh` | 3 | `python3 -c "from lib.session_hygiene import run_full_hygiene..."` |
| `ecosystem-check.sh` | 24 | `python3 -c "from lib.ecosystem_evaluator import EcosystemEvaluator..."` |
| `usage-health-check.sh` | 19 | `python3 -c "from lib.component_usage_tracker import ComponentUsageTracker..."` |
| `adr-detector.sh` | 79 | `RESULT=$(python3 -c "...analyze_commit...")` |
| `code-review-on-commit.sh` | 59 | `review_output=$(cd ... && python3 -c "...CodeReviewer...")` |

### CONCERN-11 — `hooks/pre-commit-gate.sh` lines 67-69: `unrotated_write`
`coverage-history.jsonl` is appended on every commit with no rotation logic. `metrics-rotation.sh` rotates files under `$METRICS_DIR/*.jsonl` but `coverage-history.jsonl` lives in the same directory — it IS covered by rotation. However, the rotation runs at SessionStart, not at commit time, so between sessions this file can grow unboundedly if many commits are made within one session. Severity downgraded from BLOCKER because rotation eventually fires; flagged as CONCERN.

### SUGGESTION-12–14 — `unrotated_write` (3 hooks)
`content-policy.sh`, `predev-completeness-check.sh`, and `confidentiality-enforcer.sh` append raw `echo` JSON lines directly instead of using `safe_jsonl_append`. The `metrics-rotation.sh` rotation owner covers their files via `$METRICS_DIR/*.jsonl` glob, but the hooks bypass the safe-JSONL locking wrapper, risking corrupted JSONL under concurrent sessions.

### SUGGESTION-15 — `hooks/rate-limit-protection.sh`: full duplicate of `token-budget-monitor.sh`
Both hooks implement identical token-budget logic (same Python heredoc, same thresholds, same log file). The header of `token-budget-monitor.sh` says it was "Renamed from rate-limit-protection.sh", but the old file was not removed. The duplicate fires twice on every Agent PreToolUse, wasting 2× cold-start cost.

### SUGGESTION-16 — `hooks/session-cleanup.sh` line 123: `destructive_git`
`rm -rf "$SESSION_DIR"` where `SESSION_DIR="$SESSIONS_DIR/$SESSION_ID"`. If `COGNITIVE_OS_SESSION_ID` is injected from the environment with a crafted value (e.g., `../../src`), paths outside `.cognitive-os/sessions/` can be deleted. The path is not validated against `$PROJECT_DIR/.cognitive-os/sessions/` before the `rm -rf`. Severity is SUGGESTION because exploitation requires control of the env var, not a default code path.

### SUGGESTION-17 — `hooks/global-verify.sh` lines 47-213: `test_run_inside_hook`
`global-verify.sh` IS the ADR-027 Phase 1 canonical test runner — it owns pytest by design. Flagged SUGGESTION because it violates the audit taxonomy (pytest outside `global-verify.sh`), but in this case the hook itself is the designated owner. The real issue is that the 120s subprocess timeout (`timeout=120`, line 75) on the inner pytest subprocess is internal Python (`subprocess.run(..., timeout=120)`) with no outer shell `timeout` guard; if Python itself hangs before reaching `subprocess.run`, the hook has no kill switch.

### CONCERN-18 — `hooks/skill-usage-tracker.sh` lines 74-93, 110: `bg_without_pid_track`
The telemetry writer (lines 74–93) is launched as `(...) &` and its PID captured as `_TRACKER_PID`. Lines 96–110 then register `_TRACKER_PID` with `process_registry` — that part is correct. **However**, the registration subshell itself (lines 98–110) is also launched with `&` (line 110) and its PID is never registered or tracked. If `process_registry.register()` takes longer than expected (network/disk hang), the registration subprocess becomes an untracked background process — exactly the orphan pattern ADR-028 D1.B targets.

---

## No-findings hooks (114 hooks with zero issues)

All 130 hooks were examined. The following 114 hooks had no findings under the closed anti-pattern taxonomy:

`adaptive-bypass.sh`, `adr-detector.sh` (timeout only), `agent-bus-monitor.sh`, `agent-checkpoint.sh`, `agent-output-verifier.sh`, `agent-prelaunch.sh`, `agent-work-tracker.sh`, `agnix-lint.sh`, `aguara-scan.sh`, `architecture-compliance.sh`, `assumption-tracker.sh`, `audit-id-enricher.sh`, `auto-checkpoint.sh`, `auto-refine.sh`, `auto-rollback-trigger.sh`, `auto-skill-generator.sh`, `auto-verify.sh`, `background-agent-reminder.sh`, `blast-radius.sh`, `claim-validator.sh`, `clarification-gate.sh`, `clarification-interceptor.sh`, `cognitive-os-health.sh`, `completeness-check-llm.sh`, `completeness-check.sh`, `completion-gate.sh`, `concurrent-write-guard.sh`, `confidence-gate-llm.sh`, `confidence-gate.sh`, `confidentiality-enforcer.sh` (safe_jsonl bypassed — see F-14), `consequence-evaluator.sh`, `context-diet.sh`, `context-watchdog.sh`, `contextual-rule-loader.sh`, `conversation-capture.sh`, `crash-recovery.sh`, `dequeue-notify.sh`, `destructive-git-blocker.sh`, `dispatch-gate.sh`, `doc-sync-detector.sh`, `dod-gate.sh`, `dry-run-preview.sh`, `ecosystem-check.sh` (timeout only — see F-9), `engram-auto-import.sh`, `engram-auto-sync.sh`, `epic-task-detector.sh`, `error-learning.sh`, `error-pattern-detector.sh`, `error-pipeline.sh`, `git-context-capture.sh`, `global-verify.sh` (see F-17), `guardrails-validator.sh`, `idle-service-cleanup.sh`, `infra-health.sh`, `infra-intent-detector.sh`, `inject-phase-context.sh`, `jupyter-sandbox.sh`, `kpi-trigger.sh`, `large-file-advisor.sh`, `mcp-scan.sh`, `memu-sync.sh`, `metrics-calibrator-trigger.sh`, `metrics-rotation.sh`, `notify.sh`, `observability-trace.sh`, `orchestrator-mode-detect.sh` (timeout only — see F-4), `package-sync.sh`, `paperclip-sync.sh`, `parry-scan.sh`, `pattern-check.sh`, `post-agent-verify.sh`, `pre-agent-snapshot.sh`, `pre-cleanup-snapshot.sh`, `pre-compaction-flush.sh`, `private-mode-gate.sh`, `private-mode-metrics-gate.sh`, `prompt-quality-llm.sh`, `prompt-quality.sh`, `rate-limiter.sh`, `recap-sync.sh`, `registration-check.sh`, `reinvention-check.sh`, `release-guard.sh`, `resource-check.sh`, `result-truncator.sh`, `scope-creep-detector.sh`, `scope-proportionality.sh`, `secret-detector.sh`, `self-install.sh`, `semgrep-scan.sh`, `session-changelog.sh`, `session-end-reap.sh`, `session-hygiene.sh` (timeout only — see F-6), `session-init.sh`, `session-knowledge-extractor.sh`, `session-learning.sh`, `session-resume.sh`, `session-sanity.sh`, `session-state-save.sh`, `singularity-check.sh`, `skill-feedback-tracker.sh`, `skill-tracker.sh`, `state-heartbeat.sh`, `subagent-context-injector.sh`, `sync-to-repo.sh`, `task-bridge-notify.sh`, `task-completed.sh`, `task-created.sh`, `task-panel-sync.sh`, `task-recorder.sh`, `teammate-idle.sh`, `token-budget-monitor.sh`, `tool-discovery-trigger.sh`, `tool-loop-detector.sh`, `trust-score-validator.sh`, `usage-health-check.sh` (timeout only — see F-10), `user-prompt-capture.sh`, `valkey-ensure.sh`, `wiring-check.sh`, `worktree-submodule-fix.sh`

**Count of zero-finding hooks (excluding the 16 flagged above):** 114

---

## Summary Counts

### By severity

| Severity | Count |
|----------|-------|
| BLOCKER  | 2     |
| CONCERN  | 9     |
| SUGGESTION | 7   |
| **Total** | **18** |

### By anti-pattern

| Anti-pattern | Count |
|--------------|-------|
| `test_run_inside_hook` | 4 |
| `subproc_without_timeout` | 7 |
| `unbounded_loop` | 1 |
| `unrotated_write` | 4 |
| `bg_without_pid_track` | 1 |
| `destructive_git` | 1 |
| `global_state_write` | 0 |
| `infinite_sleep` | 0 |

### Top 5 BLOCKERs / High-priority CONCERNs (ranked)

1. **BLOCKER** — `hooks/pre-commit-gate.sh:26` — `test_run_inside_hook` — unbounded pytest in PreCommit hook with no timeout; blocks VCS operations
2. **BLOCKER** — `hooks/test-baseline-diff.sh:50` — `test_run_inside_hook` — same full-suite pytest that was disabled in session-init due to 190 orphaned processes; re-introduced in Stop hook
3. **CONCERN** — `hooks/session-cleanup.sh:70-87` — `unbounded_loop` — `while true` advisory-lock spin with only soft deadline, can overshoot under I/O load
4. **CONCERN** — `hooks/skill-usage-tracker.sh:110` — `bg_without_pid_track` — registration subprocess itself backgrounded with untracked PID
5. **CONCERN** — `hooks/mlflow-sync.sh:5` — `subproc_without_timeout` — MLflow bridge (potential network I/O) invoked without shell-level timeout at Stop, can block session teardown

---

*Generated by claude-sonnet-4-6 — ADR-028 Phase C / D3 — read-only audit — no hooks modified.*
