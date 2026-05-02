# Aspirational Audit — 2026-05-02

## Summary

| Metric | Value |
|--------|-------|
| Total components | 688 |
| REAL | 167 |
| DORMANT | 180 |
| ASPIRATIONAL | 11 |
| METADATA | 88 |
| DORMANT + ASPIRATIONAL ratio | 27.8% |

## Worst Offenders (ASPIRATIONAL + DORMANT)

- `hooks/auto-refine.sh`
- `hooks/auto-verify.sh`
- `hooks/destructive-git-blocker.sh`
- `hooks/dod-gate.sh`
- `hooks/error-learning.sh`
- `hooks/session-sanity.sh`
- `lib/jupyter_client.py`
- `scripts/align_skill_frontmatter.py`
- `scripts/backfill_session_decisions.py`
- `scripts/check-upstream-changes.sh`

## Component Detail

| component | classification | signal | reason |
|-----------|---------------|--------|--------|
| `hooks/_lib/cache.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/circuit-breaker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/common.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/execute-repair.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/file_checker.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/hook-pipe.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/killswitch_check.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/normalize-stdin.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/paperclip-notify.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/portable.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/register-bg.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/remediation.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/resolve-main-worktree.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/safe-jsonl.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/semantic-search.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/singularity-suggestion.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/timing.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/_lib/tuning.sh` | METADATA | registered=False, library=True | helper in _lib/ — sourced by other hooks, not a standalone hook |
| `hooks/adaptive-bypass.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: logic merged into agent-prelaunch.sh and orchestrator rules; kept for reference | whitelisted exclusion: DEPRECATED: logic merged into agent-prelaunch.sh and orchestrator rules; kept for reference |
| `hooks/adr-detector.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — UserPromptSubmit pattern-matcher design pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — UserPromptSubmit pattern-matcher design pending; see prune-triage-2026-05-01.md |
| `hooks/adr-section-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-bash-cwd-enforcer.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/agent-bus-monitor.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 3 — requires Valkey service activation; CONDITIONAL on ORCHESTRATOR_MODE=executor; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 3 — requires Valkey service activation; CONDITIONAL on ORCHESTRATOR_MODE=executor; see prune-triage-2026-05-01.md |
| `hooks/agent-checkpoint.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-output-verifier.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — completion-gate gap analysis pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — completion-gate gap analysis pending; see prune-triage-2026-05-01.md |
| `hooks/agent-prelaunch.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agent-quota-advisor.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — ADR-056 Level 1; requires quota-aware dispatch enabled; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — ADR-056 Level 1; requires quota-aware dispatch enabled; see prune-triage-2026-05-01.md |
| `hooks/agent-quota-redirect.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 3 — ADR-056 Level 2; high blast radius; requires explicit operator sign-off; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 3 — ADR-056 Level 2; high blast radius; requires explicit operator sign-off; see prune-triage-2026-05-01.md |
| `hooks/agent-qwen-bridge.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — ADR-056 Level 3; requires LLM dispatch infrastructure validated; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — ADR-056 Level 3; requires LLM dispatch infrastructure validated; see prune-triage-2026-05-01.md |
| `hooks/agent-working-dir-inject.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/agnix-lint.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: superseded by architecture-compliance.sh for lint enforcement | whitelisted exclusion: DEPRECATED: superseded by architecture-compliance.sh for lint enforcement |
| `hooks/aguara-scan.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — requires AGUARA_ENABLED=true; service not confirmed active; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — requires AGUARA_ENABLED=true; service not confirmed active; see prune-triage-2026-05-01.md |
| `hooks/architecture-compliance.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — performance baseline required before global wiring; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — performance baseline required before global wiring; see prune-triage-2026-05-01.md |
| `hooks/aspirational-audit-weekly.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/assumption-tracker.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — deduplication design with clarification-gate pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — deduplication design with clarification-gate pending; see prune-triage-2026-05-01.md |
| `hooks/audit-id-enricher.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/auto-checkpoint.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/auto-refine.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.3 — built by UX2 sprint; registration status unverified | planned but not wired: FUTURE: per rules/ROADMAP.md §2.3 — built by UX2 sprint; registration status unverified |
| `hooks/auto-repair-dispatcher.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/auto-rollback-trigger.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/auto-skill-generator.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: invoked by /auto-skill skill, not a hook matcher | whitelisted exclusion: MANUAL_TRIGGER: invoked by /auto-skill skill, not a hook matcher |
| `hooks/auto-verify.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.1 — built by UX2 sprint but registration not yet verified | planned but not wired: FUTURE: per rules/ROADMAP.md §2.1 — built by UX2 sprint but registration not yet verified |
| `hooks/background-agent-reminder.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — low urgency, orchestrator rules partially cover; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — low urgency, orchestrator rules partially cover; see prune-triage-2026-05-01.md |
| `hooks/blast-radius.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/claim-validator.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-gate.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/clarification-interceptor.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference | whitelisted exclusion: DEPRECATED: functionality merged into clarification-gate.sh; kept for backward-compat reference |
| `hooks/code-review-on-commit.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — cost governance analysis required; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — cost governance analysis required; see prune-triage-2026-05-01.md |
| `hooks/cognitive-os-health.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status | whitelisted exclusion: MANUAL_TRIGGER: health-check report for the full OS; run on demand via /cos-status |
| `hooks/completeness-check-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version | whitelisted exclusion: DEPRECATED: LLM-based variant; completeness-check.sh (rule-based) is the registered version |
| `hooks/completion-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/concurrent-write-guard.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 3 — requires session-concurrency infrastructure; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 3 — requires session-concurrency infrastructure; see prune-triage-2026-05-01.md |
| `hooks/confidence-gate-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement | whitelisted exclusion: DEPRECATED: LLM-based variant; confidence-gate.sh (rule-based) is the planned replacement |
| `hooks/confidence-gate.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/confidentiality-enforcer.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/consequence-evaluator.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: invoked by /consequence skill | whitelisted exclusion: MANUAL_TRIGGER: invoked by /consequence skill |
| `hooks/content-policy.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/context-diet.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — isolated testing required before wiring; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — isolated testing required before wiring; see prune-triage-2026-05-01.md |
| `hooks/context-watchdog.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/contextual-rule-loader.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — rule-loading design review pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — rule-loading design review pending; see prune-triage-2026-05-01.md |
| `hooks/conversation-capture.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — engram duplication evaluation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — engram duplication evaluation pending; see prune-triage-2026-05-01.md |
| `hooks/cos-executor-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/cos-executor-heartbeat.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: compatibility alias for cos-executor-daemon-launcher.sh; registering both would launch duplicate daemon checks | whitelisted exclusion: DEPRECATED: compatibility alias for cos-executor-daemon-launcher.sh; registering both would launch duplicate daemon checks |
| `hooks/crash-recovery.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/dequeue-notify.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/destructive-git-blocker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: blocks destructive git commands; planned for PreToolUse Bash — not yet wired | planned but not wired: FUTURE: blocks destructive git commands; planned for PreToolUse Bash — not yet wired |
| `hooks/destructive-rm-blocker.sh` | REAL | fire_count_7d=191, registered=True | fires actively (191 rows in hook-health.jsonl last 7d) |
| `hooks/dispatch-gate.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/doc-sync-detector.sh` | REAL | fire_count_7d=18, registered=True | fires actively (18 rows in hook-health.jsonl last 7d) |
| `hooks/docker-drift-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/dod-gate.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.2 — built by UX2 sprint; registration status unverified | planned but not wired: FUTURE: per rules/ROADMAP.md §2.2 — built by UX2 sprint; registration status unverified |
| `hooks/dry-run-preview.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — dry-run mode adoption pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — dry-run mode adoption pending; see prune-triage-2026-05-01.md |
| `hooks/ecosystem-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — completeness verification pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — completeness verification pending; see prune-triage-2026-05-01.md |
| `hooks/edit-lock-drain-parked.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-pre-tool.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-process-negotiations.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/edit-lock-session-end.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/engram-auto-import.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — mem_context duplication risk evaluation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — mem_context duplication risk evaluation pending; see prune-triage-2026-05-01.md |
| `hooks/engram-auto-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — mem_save duplication risk evaluation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — mem_save duplication risk evaluation pending; see prune-triage-2026-05-01.md |
| `hooks/engram-crystallize-on-session-end.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/engram-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/engram-reinforce-on-access.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/epic-task-detector.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — prompt-classifier integration design pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — prompt-classifier integration design pending; see prune-triage-2026-05-01.md |
| `hooks/error-learning.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: captures test/lint/build errors; planned PostToolUse Bash alongside error-pipeline.sh | planned but not wired: FUTURE: captures test/lint/build errors; planned PostToolUse Bash alongside error-pipeline.sh |
| `hooks/error-pattern-detector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/error-pipeline.sh` | REAL | fire_count_7d=176, registered=True | fires actively (176 rows in hook-health.jsonl last 7d) |
| `hooks/git-commit-scope-guard.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/git-context-capture.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/global-verify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: wired conditionally by apply-efficiency-profile.sh; not a global default — registered only when a profile is active — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: wired conditionally by apply-efficiency-profile.sh; not a global default — registered only when a profile is active — @on-demand |
| `hooks/guardrails-validator.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: NeMo Guardrails integration; fires via /guardrails skill on demand, GUARDRAILS_ENABLED=true required — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: NeMo Guardrails integration; fires via /guardrails skill on demand, GUARDRAILS_ENABLED=true required — @on-demand |
| `hooks/hook-header-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/host-tool-doctor.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/idle-service-cleanup.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: cleans up idle Docker services; run by cron or operator on demand, not a Claude event hook — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: cleans up idle Docker services; run by cron or operator on demand, not a Claude event hook — @manual-trigger |
| `hooks/infra-health.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/infra-intent-detector.sh` | METADATA | registered=False, excluded=True, category=INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently | whitelisted exclusion: INFRA: detects infrastructure-intent in prompts; called by agent-prelaunch.sh, not registered independently |
| `hooks/inject-phase-context.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/jupyter-sandbox.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 3 — requires Jupyter integration active; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 3 — requires Jupyter integration active; see prune-triage-2026-05-01.md |
| `hooks/kpi-trigger.sh` | REAL | fire_count_7d=7, registered=True | fires actively (7 rows in hook-health.jsonl last 7d) |
| `hooks/large-file-advisor.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: advises on large file reads; planned PreToolUse Read — not yet wired | planned but not wired: FUTURE: advises on large file reads; planned PreToolUse Read — not yet wired |
| `hooks/mcp-scan.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/memory-prefetch.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/memu-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — engram overlap evaluation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — engram overlap evaluation pending; see prune-triage-2026-05-01.md |
| `hooks/metrics-calibrator-trigger.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — metrics-calibrator skill must be wired first; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — metrics-calibrator skill must be wired first; see prune-triage-2026-05-01.md |
| `hooks/metrics-rotation.sh` | METADATA | registered=False, excluded=True, category=INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event | whitelisted exclusion: INFRA: rotates JSONL metrics files to prevent unbounded growth; invoked by cron or manually, not on every event |
| `hooks/mlflow-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — requires mlflow package active; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — requires mlflow package active; see prune-triage-2026-05-01.md |
| `hooks/native-agent-heartbeat.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly | whitelisted exclusion: MANUAL_TRIGGER: generic desktop notification wrapper; invoked by other hooks, not registered directly |
| `hooks/orchestrator-mode-detect.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sourced library helper; not registered independently, sourced by other hooks on demand — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: sourced library helper; not registered independently, sourced by other hooks on demand — @on-demand |
| `hooks/package-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs package dependencies; triggered by CI or developer on demand, not by Claude hooks — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: syncs package dependencies; triggered by CI or developer on demand, not by Claude hooks — @manual-trigger |
| `hooks/paperclip-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — requires Paperclip service active; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — requires Paperclip service active; see prune-triage-2026-05-01.md |
| `hooks/parry-scan.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — requires Parry service confirmed active; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — requires Parry service confirmed active; see prune-triage-2026-05-01.md |
| `hooks/pattern-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — implementation completeness verification pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — implementation completeness verification pending; see prune-triage-2026-05-01.md |
| `hooks/pre-agent-snapshot.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/pre-cleanup-snapshot.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: snapshot before cleanup operations; invoked manually or by admin scripts on demand — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: snapshot before cleanup operations; invoked manually or by admin scripts on demand — @manual-trigger |
| `hooks/pre-commit-gate.sh` | METADATA | registered=False, excluded=True, category=GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) | whitelisted exclusion: GIT_HOOK: symlinked to .git/hooks/pre-commit; not a Claude hook (per rules/ROADMAP.md Section 1.8) |
| `hooks/pre-compaction-flush.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/predev-completeness-check.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/private-mode-gate.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: gates operations in private mode; planned for PreToolUse — not yet wired | planned but not wired: FUTURE: gates operations in private mode; planned for PreToolUse — not yet wired |
| `hooks/private-mode-metrics-gate.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: gates metrics emission in private mode; planned for PostToolUse — not yet wired | planned but not wired: FUTURE: gates metrics emission in private mode; planned for PostToolUse — not yet wired |
| `hooks/profile-drift-autoapply.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/project-docs-convention.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/prompt-quality-llm.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: LLM-based variant; prompt-quality.sh (rule-based) is the registered version | whitelisted exclusion: DEPRECATED: LLM-based variant; prompt-quality.sh (rule-based) is the registered version |
| `hooks/query-tailored-context-inject.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rate-limit-detector.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/rate-limit-drain.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/rate-limit-precheck.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/rate-limit-protection.sh` | METADATA | deprecated_shim=True | DEPRECATED shim — short file with DEPRECATED marker |
| `hooks/rate-limiter.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/reaper-daemon-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/reaper-heartbeat.sh` | METADATA | registered=False, excluded=True, category=DEPRECATED: compatibility alias for reaper-daemon-launcher.sh; registering both would duplicate daemon scheduling | whitelisted exclusion: DEPRECATED: compatibility alias for reaper-daemon-launcher.sh; registering both would duplicate daemon scheduling |
| `hooks/recap-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — target system identification pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — target system identification pending; see prune-triage-2026-05-01.md |
| `hooks/registration-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI | whitelisted exclusion: MANUAL_TRIGGER: checks hook registration state; invoked manually or by CI |
| `hooks/reinvention-check.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/release-guard.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — release workflow definition pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — release workflow definition pending; see prune-triage-2026-05-01.md |
| `hooks/resource-check.sh` | METADATA | registered=False, excluded=True, category=INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook | whitelisted exclusion: INFRA: checks resource limits before spawning; called programmatically by rate-limiter.sh, not registered as independent hook |
| `hooks/result-truncator.sh` | REAL | fire_count_7d=176, registered=True | fires actively (176 rows in hook-health.jsonl last 7d) |
| `hooks/review-spawner.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/rule-frontmatter-validator.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/scope-creep-detector.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — scope-proportionality duplication evaluation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — scope-proportionality duplication evaluation pending; see prune-triage-2026-05-01.md |
| `hooks/scope-proportionality.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — scope-creep-detector duplication evaluation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — scope-creep-detector duplication evaluation pending; see prune-triage-2026-05-01.md |
| `hooks/secret-detector.sh` | REAL | fire_count_7d=18, registered=True | fires actively (18 rows in hook-health.jsonl last 7d) |
| `hooks/self-install.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/self-knowledge-refresh.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/semgrep-scan.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: fires via /semgrep-scan skill on demand; not a global default hook — @on-demand | whitelisted exclusion: MANUAL_TRIGGER: fires via /semgrep-scan skill on demand; not a global default hook — @on-demand |
| `hooks/session-changelog.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-cleanup.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/session-end-reap.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: reaps stale session artefacts at Stop; ADR-028 Phase B work item — not yet wired | planned but not wired: FUTURE: reaps stale session artefacts at Stop; ADR-028 Phase B work item — not yet wired |
| `hooks/session-heartbeat.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-hygiene.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand | whitelisted exclusion: MANUAL_TRIGGER: cleanup script for stale session artefacts; run on demand |
| `hooks/session-init.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-knowledge-extractor.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — mem_session_summary overlap evaluation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — mem_session_summary overlap evaluation pending; see prune-triage-2026-05-01.md |
| `hooks/session-learning.sh` | REAL | fire_count_7d=7, registered=True | fires actively (7 rows in hook-health.jsonl last 7d) |
| `hooks/session-resume.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-sanity.sh` | DORMANT | fire_count_7d=0, registered=True | registered in settings.json but no fire events in last 7 days + no test/marker |
| `hooks/session-start-worktree-nudge.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-startup-protocol.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-state-save.sh` | METADATA | registered=False, excluded=True, category=INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook | whitelisted exclusion: INFRA: saves session state to disk; invoked by session-cleanup.sh or manually; not a standalone registered hook |
| `hooks/session-summary-reminder.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-watchdog-launcher.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/session-wrapup-trigger.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/singularity-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: checks MAPE-K loop state; invoked by /singularity skill, not by Claude events |
| `hooks/skill-failure-monitor.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-feedback-tracker.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/skill-frontmatter-validator.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/skill-invocation-logger.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/skill-synthesis-scanner.sh` | REAL | fire_count_7d=7, registered=True | fires actively (7 rows in hook-health.jsonl last 7d) |
| `hooks/skill-tracker.sh` | ASPIRATIONAL | registered=False, excluded=True, category=FUTURE: tracks skill invocations for model-optimizer; planned for PostToolUse Agent — not yet wired | planned but not wired: FUTURE: tracks skill invocations for model-optimizer; planned for PostToolUse Agent — not yet wired |
| `hooks/skill-usage-tracker.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/state-heartbeat.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/subagent-context-injector.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/surface-fix-detector.sh` | REAL | fire_count_7d=18, registered=True | fires actively (18 rows in hook-health.jsonl last 7d) |
| `hooks/sync-to-repo.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer | whitelisted exclusion: MANUAL_TRIGGER: syncs local OS changes to the luum-agent-os repo; invoked manually by developer |
| `hooks/task-bridge-notify.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks | whitelisted exclusion: MANUAL_TRIGGER: sends task events to external bridge; invoked programmatically by task lifecycle hooks |
| `hooks/task-completed.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/task-created.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/task-panel-sync.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events | whitelisted exclusion: MANUAL_TRIGGER: syncs task panel state; invoked programmatically, not by Claude events |
| `hooks/task-recorder.sh` | METADATA | registered=False, excluded=True, category=LIBRARY: sourced by dispatch-gate; not a standalone matcher | whitelisted exclusion: LIBRARY: sourced by dispatch-gate; not a standalone matcher |
| `hooks/teammate-idle.sh` | ON_DEMAND | fire_count_7d=0, registered=True, has_test=True | registered + covered by test — legit sleeper (fires when triggered) |
| `hooks/token-budget-monitor.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — performance and sampling design required; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — performance and sampling design required; see prune-triage-2026-05-01.md |
| `hooks/tool-discovery-trigger.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 3 — dynamic tool discovery design pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 3 — dynamic tool discovery design pending; see prune-triage-2026-05-01.md |
| `hooks/tool-loop-detector.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 2 — loop-detection algorithm validation pending; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 2 — loop-detection algorithm validation pending; see prune-triage-2026-05-01.md |
| `hooks/tool-sequence-capture.sh` | REAL | fire_count_7d=269, registered=True | fires actively (269 rows in hook-health.jsonl last 7d) |
| `hooks/trust-score-validator.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/usage-health-check.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event | whitelisted exclusion: MANUAL_TRIGGER: reports token/rate usage; invoked on demand, not on every event |
| `hooks/user-prompt-capture.sh` | REAL | fire_count_7d=0, registered=True, writes_jsonl=True | registered + writes metrics JSONL (fires may be outside 7d window) |
| `hooks/valkey-ensure.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: deferred to Phase 3 — requires Valkey adoption; see prune-triage-2026-05-01.md | whitelisted exclusion: MANUAL_TRIGGER: deferred to Phase 3 — requires Valkey adoption; see prune-triage-2026-05-01.md |
| `hooks/work-queue-sync.sh` | REAL | fire_count_7d=10, registered=True | fires actively (10 rows in hook-health.jsonl last 7d) |
| `hooks/worktree-submodule-fix.sh` | METADATA | registered=False, excluded=True, category=MANUAL_TRIGGER: fixes git submodule state in worktrees; invoked manually after worktree operations — @manual-trigger | whitelisted exclusion: MANUAL_TRIGGER: fixes git submodule state in worktrees; invoked manually after worktree operations — @manual-trigger |
| `lib/adr_detector.py` | REAL | callers=1, size_bytes=17303 | imported by 1 non-test caller(s) |
| `lib/agent_bus.py` | REAL | callers=1, size_bytes=31800 | imported by 1 non-test caller(s) |
| `lib/agent_bus_metrics.py` | REAL | callers=6, size_bytes=14987 | imported by 6 non-test caller(s) |
| `lib/agent_context_injector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4733 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_dashboard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8242 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_health_monitor.py` | REAL | callers=2, size_bytes=17001 | imported by 2 non-test caller(s) |
| `lib/agent_output_extractor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8556 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_output_monitor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12766 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_output_to_bus.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4550 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_permissions.py` | REAL | callers=1, size_bytes=16890 | imported by 1 non-test caller(s) |
| `lib/agent_progress_tracker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3899 | covered by test — legit sleeper (imported by test only) |
| `lib/agent_redirect_protocol.py` | REAL | callers=3, size_bytes=6152 | imported by 3 non-test caller(s) |
| `lib/agent_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11181 | covered by test — legit sleeper (imported by test only) |
| `lib/anchored_summarizer.py` | REAL | callers=1, size_bytes=11865 | imported by 1 non-test caller(s) |
| `lib/anchored_summary.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12951 | covered by test — legit sleeper (imported by test only) |
| `lib/anthropic_direct_policy.py` | REAL | callers=5, size_bytes=2193 | imported by 5 non-test caller(s) |
| `lib/audit_id.py` | REAL | callers=1, size_bytes=3522 | imported by 1 non-test caller(s) |
| `lib/auto_executor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=912 | covered by test — legit sleeper (imported by test only) |
| `lib/auto_repair.py` | REAL | callers=2, size_bytes=23892 | imported by 2 non-test caller(s) |
| `lib/batch_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23076 | covered by test — legit sleeper (imported by test only) |
| `lib/bifrost_client.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10418 | covered by test — legit sleeper (imported by test only) |
| `lib/budget_calculator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5529 | covered by test — legit sleeper (imported by test only) |
| `lib/capability_levels.py` | REAL | callers=1, size_bytes=7125 | imported by 1 non-test caller(s) |
| `lib/changelog_generator.py` | REAL | callers=1, size_bytes=11063 | imported by 1 non-test caller(s) |
| `lib/checkpoint_manager.py` | REAL | callers=0, writes_jsonl=True, size_bytes=17752 | writes to an existing metrics JSONL file |
| `lib/circuit_breaker.py` | REAL | callers=3, size_bytes=8226 | imported by 3 non-test caller(s) |
| `lib/claude_executor.py` | REAL | callers=7, size_bytes=32520 | imported by 7 non-test caller(s) |
| `lib/claude_usage_reader.py` | REAL | callers=1, size_bytes=6744 | imported by 1 non-test caller(s) |
| `lib/code_reviewer.py` | REAL | callers=1, size_bytes=30101 | imported by 1 non-test caller(s) |
| `lib/cognee_client.py` | REAL | callers=1, size_bytes=9071 | imported by 1 non-test caller(s) |
| `lib/cognitive_load_monitor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20893 | covered by test — legit sleeper (imported by test only) |
| `lib/commit_classifier.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7442 | covered by test — legit sleeper (imported by test only) |
| `lib/compatibility_layer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8909 | covered by test — legit sleeper (imported by test only) |
| `lib/completeness_checker.py` | REAL | callers=1, size_bytes=4766 | imported by 1 non-test caller(s) |
| `lib/component_registry.py` | REAL | callers=1, size_bytes=6200 | imported by 1 non-test caller(s) |
| `lib/component_usage_tracker.py` | REAL | callers=1, size_bytes=17025 | imported by 1 non-test caller(s) |
| `lib/confidentiality_scanner.py` | REAL | callers=1, size_bytes=11990 | imported by 1 non-test caller(s) |
| `lib/config_loader.py` | REAL | callers=3, size_bytes=7390 | imported by 3 non-test caller(s) |
| `lib/consequence_engine.py` | REAL | callers=7, size_bytes=26433 | imported by 7 non-test caller(s) |
| `lib/context_compressor.py` | REAL | callers=1, size_bytes=22526 | imported by 1 non-test caller(s) |
| `lib/context_diet.py` | REAL | callers=1, size_bytes=19972 | imported by 1 non-test caller(s) |
| `lib/context_estimator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2925 | covered by test — legit sleeper (imported by test only) |
| `lib/context_injector.py` | REAL | callers=3, size_bytes=16403 | imported by 3 non-test caller(s) |
| `lib/cost_dashboard.py` | REAL | callers=0, writes_jsonl=True, size_bytes=20362 | writes to an existing metrics JSONL file |
| `lib/cost_predictor.py` | REAL | callers=1, size_bytes=26052 | imported by 1 non-test caller(s) |
| `lib/cross_verifier.py` | REAL | callers=1, size_bytes=10720 | imported by 1 non-test caller(s) |
| `lib/dead_letter_queue.py` | REAL | callers=2, size_bytes=6889 | imported by 2 non-test caller(s) |
| `lib/decision_tracker.py` | REAL | callers=3, size_bytes=4251 | imported by 3 non-test caller(s) |
| `lib/dispatch.py` | REAL | callers=6, size_bytes=24825 | imported by 6 non-test caller(s) |
| `lib/dispatch_helper.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7804 | covered by test — legit sleeper (imported by test only) |
| `lib/dispatch_model_advisor.py` | REAL | callers=1, size_bytes=20374 | imported by 1 non-test caller(s) |
| `lib/doc_review_personas.py` | REAL | callers=1, size_bytes=21891 | imported by 1 non-test caller(s) |
| `lib/docs_writer.py` | REAL | callers=2, size_bytes=3099 | imported by 2 non-test caller(s) |
| `lib/document_feature_writer.py` | REAL | callers=1, size_bytes=3500 | imported by 1 non-test caller(s) |
| `lib/dogfood_scorer.py` | REAL | callers=1, size_bytes=21566 | imported by 1 non-test caller(s) |
| `lib/domain_model.py` | REAL | callers=1, size_bytes=4265 | imported by 1 non-test caller(s) |
| `lib/domain_router.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21345 | covered by test — legit sleeper (imported by test only) |
| `lib/dynamic_tool_creator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13500 | covered by test — legit sleeper (imported by test only) |
| `lib/ecosystem_evaluator.py` | REAL | callers=1, size_bytes=11916 | imported by 1 non-test caller(s) |
| `lib/engram_client.py` | REAL | callers=3, size_bytes=6605 | imported by 3 non-test caller(s) |
| `lib/engram_crystallizer.py` | REAL | callers=1, size_bytes=16832 | imported by 1 non-test caller(s) |
| `lib/engram_graph_walker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11182 | covered by test — legit sleeper (imported by test only) |
| `lib/engram_http_client.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12040 | covered by test — legit sleeper (imported by test only) |
| `lib/engram_lifecycle.py` | REAL | callers=1, size_bytes=19094 | imported by 1 non-test caller(s) |
| `lib/error_classifier.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21120 | covered by test — legit sleeper (imported by test only) |
| `lib/error_insights.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14219 | covered by test — legit sleeper (imported by test only) |
| `lib/error_matching.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6249 | covered by test — legit sleeper (imported by test only) |
| `lib/escalation_detector.py` | REAL | callers=4, size_bytes=21324 | imported by 4 non-test caller(s) |
| `lib/estimation_calibrator.py` | REAL | callers=1, size_bytes=15391 | imported by 1 non-test caller(s) |
| `lib/execution_profile.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8790 | covered by test — legit sleeper (imported by test only) |
| `lib/feedback_consumer.py` | REAL | callers=0, writes_jsonl=True, size_bytes=7472 | writes to an existing metrics JSONL file |
| `lib/feedback_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12110 | covered by test — legit sleeper (imported by test only) |
| `lib/file_mutation_queue.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3378 | covered by test — legit sleeper (imported by test only) |
| `lib/format_converter.py` | REAL | callers=2, size_bytes=7714 | imported by 2 non-test caller(s) |
| `lib/gateway_selector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8093 | covered by test — legit sleeper (imported by test only) |
| `lib/git_context.py` | REAL | callers=1, size_bytes=6688 | imported by 1 non-test caller(s) |
| `lib/governed_self_improvement.py` | REAL | callers=1, size_bytes=9926 | imported by 1 non-test caller(s) |
| `lib/ground_truth.py` | REAL | callers=1, size_bytes=16358 | imported by 1 non-test caller(s) |
| `lib/guardrails_validators.py` | REAL | callers=2, size_bytes=11981 | imported by 2 non-test caller(s) |
| `lib/homeostasis.py` | REAL | callers=1, size_bytes=27020 | imported by 1 non-test caller(s) |
| `lib/hook_tuner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6037 | covered by test — legit sleeper (imported by test only) |
| `lib/host_monitor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10808 | covered by test — legit sleeper (imported by test only) |
| `lib/impact_analysis.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21872 | covered by test — legit sleeper (imported by test only) |
| `lib/install_timing.py` | REAL | callers=0, writes_jsonl=True, size_bytes=3963 | writes to an existing metrics JSONL file |
| `lib/issue_pipeline.py` | REAL | callers=1, size_bytes=26115 | imported by 1 non-test caller(s) |
| `lib/jupyter_client.py` | DORMANT | callers=0, size_bytes=9418 | no non-test callers found, no test coverage, no on-demand marker |
| `lib/kpi_collector.py` | REAL | callers=0, writes_jsonl=True, size_bytes=11669 | writes to an existing metrics JSONL file |
| `lib/learning_pipeline.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16152 | covered by test — legit sleeper (imported by test only) |
| `lib/license_guard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9749 | covered by test — legit sleeper (imported by test only) |
| `lib/litellm_client.py` | REAL | callers=1, size_bytes=9140 | imported by 1 non-test caller(s) |
| `lib/manifest_loader.py` | REAL | callers=1, size_bytes=12975 | imported by 1 non-test caller(s) |
| `lib/memory.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2593 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_decay.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4668 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_first.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3973 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_manager.py` | REAL | callers=1, size_bytes=23781 | imported by 1 non-test caller(s) |
| `lib/memory_retriever.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9406 | covered by test — legit sleeper (imported by test only) |
| `lib/memory_scanner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4476 | covered by test — legit sleeper (imported by test only) |
| `lib/metric_event.py` | REAL | callers=11, size_bytes=6064 | imported by 11 non-test caller(s) |
| `lib/mlflow_bridge.py` | REAL | callers=1, size_bytes=10492 | imported by 1 non-test caller(s) |
| `lib/model_catalog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=17399 | covered by test — legit sleeper (imported by test only) |
| `lib/model_recommender.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4210 | covered by test — legit sleeper (imported by test only) |
| `lib/model_router.py` | REAL | callers=1, size_bytes=22628 | imported by 1 non-test caller(s) |
| `lib/notification_digest.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4920 | covered by test — legit sleeper (imported by test only) |
| `lib/notifications.py` | REAL | callers=1, size_bytes=12174 | imported by 1 non-test caller(s) |
| `lib/observability.py` | REAL | callers=1, size_bytes=7388 | imported by 1 non-test caller(s) |
| `lib/openai_compatible_agent_loop.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=23621 | covered by test — legit sleeper (imported by test only) |
| `lib/ops_runbook.py` | REAL | callers=1, size_bytes=6698 | imported by 1 non-test caller(s) |
| `lib/orchestrator_capabilities.py` | REAL | callers=1, size_bytes=8626 | imported by 1 non-test caller(s) |
| `lib/orchestrator_mode.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5682 | covered by test — legit sleeper (imported by test only) |
| `lib/orchestrator_mode_activator.py` | REAL | callers=1, size_bytes=4271 | imported by 1 non-test caller(s) |
| `lib/outcome_metrics.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2091 | covered by test — legit sleeper (imported by test only) |
| `lib/paperclip_client.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20387 | covered by test — legit sleeper (imported by test only) |
| `lib/paths.py` | REAL | callers=1, size_bytes=7957 | imported by 1 non-test caller(s) |
| `lib/pattern_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=26908 | covered by test — legit sleeper (imported by test only) |
| `lib/performance_monitor.py` | REAL | callers=2, size_bytes=24847 | imported by 2 non-test caller(s) |
| `lib/persona_library.py` | REAL | callers=2, size_bytes=11862 | imported by 2 non-test caller(s) |
| `lib/phase_timing.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9593 | covered by test — legit sleeper (imported by test only) |
| `lib/planning_poker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19285 | covered by test — legit sleeper (imported by test only) |
| `lib/process_registry.py` | REAL | callers=8, size_bytes=9356 | imported by 8 non-test caller(s) |
| `lib/process_user_message.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1462 | covered by test — legit sleeper (imported by test only) |
| `lib/project_profile_bootstrap.py` | REAL | callers=2, size_bytes=12802 | imported by 2 non-test caller(s) |
| `lib/project_scaffolder.py` | REAL | callers=1, size_bytes=17021 | imported by 1 non-test caller(s) |
| `lib/prompt_builder.py` | REAL | callers=1, size_bytes=11288 | imported by 1 non-test caller(s) |
| `lib/prompt_cache.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19987 | covered by test — legit sleeper (imported by test only) |
| `lib/prompt_classifier.py` | REAL | callers=1, size_bytes=9683 | imported by 1 non-test caller(s) |
| `lib/queue_advisor.py` | REAL | callers=0, writes_jsonl=True, size_bytes=27198 | writes to an existing metrics JSONL file |
| `lib/queue_drainer.py` | REAL | callers=3, size_bytes=20114 | imported by 3 non-test caller(s) |
| `lib/quota_pressure.py` | REAL | callers=6, size_bytes=7247 | imported by 6 non-test caller(s) |
| `lib/qwen_agent_loop.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2112 | covered by test — legit sleeper (imported by test only) |
| `lib/qwen_context_injector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4832 | covered by test — legit sleeper (imported by test only) |
| `lib/qwen_provider.py` | REAL | callers=4, size_bytes=12727 | imported by 4 non-test caller(s) |
| `lib/rate_limit_protection.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=863 | covered by test — legit sleeper (imported by test only) |
| `lib/rate_limit_queue_migration.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3513 | covered by test — legit sleeper (imported by test only) |
| `lib/rate_limit_tracker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21996 | covered by test — legit sleeper (imported by test only) |
| `lib/rate_limiter.py` | REAL | callers=4, size_bytes=57844 | imported by 4 non-test caller(s) |
| `lib/record_completion.py` | REAL | callers=1, size_bytes=19375 | imported by 1 non-test caller(s) |
| `lib/record_error.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=688 | covered by test — legit sleeper (imported by test only) |
| `lib/ref_key_loader.py` | REAL | callers=3, size_bytes=7729 | imported by 3 non-test caller(s) |
| `lib/reinvention_guard.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12450 | covered by test — legit sleeper (imported by test only) |
| `lib/reinvention_semantic.py` | REAL | callers=4, size_bytes=22337 | imported by 4 non-test caller(s) |
| `lib/release_analyzer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19825 | covered by test — legit sleeper (imported by test only) |
| `lib/repetition_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6093 | covered by test — legit sleeper (imported by test only) |
| `lib/repo_analyzer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=51731 | covered by test — legit sleeper (imported by test only) |
| `lib/request_queue.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4288 | covered by test — legit sleeper (imported by test only) |
| `lib/research_scoring.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7750 | covered by test — legit sleeper (imported by test only) |
| `lib/retry_scheduler.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5440 | covered by test — legit sleeper (imported by test only) |
| `lib/retry_tracker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3385 | covered by test — legit sleeper (imported by test only) |
| `lib/return_contract_parser.py` | REAL | callers=2, size_bytes=8180 | imported by 2 non-test caller(s) |
| `lib/return_contract_validator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1498 | covered by test — legit sleeper (imported by test only) |
| `lib/reverse_engineer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=43887 | covered by test — legit sleeper (imported by test only) |
| `lib/review_agent.py` | REAL | callers=8, size_bytes=19210 | imported by 8 non-test caller(s) |
| `lib/risk_register.py` | REAL | callers=1, size_bytes=4010 | imported by 1 non-test caller(s) |
| `lib/safe_engram.py` | REAL | callers=1, size_bytes=7390 | imported by 1 non-test caller(s) |
| `lib/scheduled_drain.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5771 | covered by test — legit sleeper (imported by test only) |
| `lib/sdd_pipeline.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10141 | covered by test — legit sleeper (imported by test only) |
| `lib/sdd_resume.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11873 | covered by test — legit sleeper (imported by test only) |
| `lib/secret_ref.py` | REAL | callers=1, size_bytes=4680 | imported by 1 non-test caller(s) |
| `lib/self_improvement.py` | REAL | callers=0, writes_jsonl=True, size_bytes=8252 | writes to an existing metrics JSONL file |
| `lib/self_knowledge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10009 | covered by test — legit sleeper (imported by test only) |
| `lib/session_hygiene.py` | REAL | callers=2, size_bytes=6999 | imported by 2 non-test caller(s) |
| `lib/session_parser.py` | REAL | callers=1, size_bytes=16900 | imported by 1 non-test caller(s) |
| `lib/session_state.py` | REAL | callers=1, size_bytes=8945 | imported by 1 non-test caller(s) |
| `lib/session_watchdog_lib.py` | REAL | callers=1, size_bytes=27011 | imported by 1 non-test caller(s) |
| `lib/simulation_arena.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=31030 | covered by test — legit sleeper (imported by test only) |
| `lib/singularity.py` | REAL | callers=1, size_bytes=49372 | imported by 1 non-test caller(s) |
| `lib/skill_archive.py` | REAL | callers=0, writes_jsonl=True, size_bytes=15250 | writes to an existing metrics JSONL file |
| `lib/skill_failure_repair.py` | REAL | callers=1, size_bytes=7670 | imported by 1 non-test caller(s) |
| `lib/skill_router.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=46141 | covered by test — legit sleeper (imported by test only) |
| `lib/skill_routing.py` | REAL | callers=1, size_bytes=12573 | imported by 1 non-test caller(s) |
| `lib/skill_runner.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16846 | covered by test — legit sleeper (imported by test only) |
| `lib/skill_synthesizer.py` | REAL | callers=1, size_bytes=11679 | imported by 1 non-test caller(s) |
| `lib/smart_access.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7404 | covered by test — legit sleeper (imported by test only) |
| `lib/smart_infra.py` | REAL | callers=1, size_bytes=23593 | imported by 1 non-test caller(s) |
| `lib/smart_reader.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=24454 | covered by test — legit sleeper (imported by test only) |
| `lib/smart_truncator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20833 | covered by test — legit sleeper (imported by test only) |
| `lib/snapshot_manager.py` | REAL | callers=7, size_bytes=12906 | imported by 7 non-test caller(s) |
| `lib/sprint_orchestrator.py` | REAL | callers=1, size_bytes=16876 | imported by 1 non-test caller(s) |
| `lib/sprint_test_aggregator.py` | REAL | callers=2, size_bytes=15973 | imported by 2 non-test caller(s) |
| `lib/stack_skill_recommender.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=18329 | covered by test — legit sleeper (imported by test only) |
| `lib/staged_verification.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=15214 | covered by test — legit sleeper (imported by test only) |
| `lib/state_heartbeat.py` | REAL | callers=2, size_bytes=9842 | imported by 2 non-test caller(s) |
| `lib/symbiosis_monitor.py` | REAL | callers=0, writes_jsonl=True, size_bytes=15958 | writes to an existing metrics JSONL file |
| `lib/system_graph.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=39900 | covered by test — legit sleeper (imported by test only) |
| `lib/targeted_test_resolver.py` | REAL | callers=1, size_bytes=5288 | imported by 1 non-test caller(s) |
| `lib/telemetry.py` | REAL | callers=5, size_bytes=11012 | imported by 5 non-test caller(s) |
| `lib/test_framework_detector.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16521 | covered by test — legit sleeper (imported by test only) |
| `lib/threat_classifier.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7186 | covered by test — legit sleeper (imported by test only) |
| `lib/token_budget_monitor.py` | REAL | callers=1, size_bytes=12982 | imported by 1 non-test caller(s) |
| `lib/tool_adoption_evaluator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=20000 | covered by test — legit sleeper (imported by test only) |
| `lib/traceability_checker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12240 | covered by test — legit sleeper (imported by test only) |
| `lib/trust_report_parser.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7690 | covered by test — legit sleeper (imported by test only) |
| `lib/user_model.py` | REAL | callers=1, size_bytes=9798 | imported by 1 non-test caller(s) |
| `lib/web_crawler.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9723 | covered by test — legit sleeper (imported by test only) |
| `lib/webhook_trigger.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14410 | covered by test — legit sleeper (imported by test only) |
| `lib/wiring_validator.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14785 | covered by test — legit sleeper (imported by test only) |
| `lib/work_queue.py` | REAL | callers=3, size_bytes=6414 | imported by 3 non-test caller(s) |
| `scripts/adr100_live_headroom_check.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8343 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/adr_reserve.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9517 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/align_skill_frontmatter.py` | DORMANT | callers=0, size_bytes=3184 | no observable production use, no test, no on-demand marker |
| `scripts/apply-efficiency-profile.sh` | REAL | writes_jsonl=True, size_bytes=10115 | writes to an existing metrics JSONL file |
| `scripts/aspirational_audit.py` | REAL | writes_jsonl=True, size_bytes=34707 | writes to an existing metrics JSONL file |
| `scripts/auto-update-projects.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10914 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/backfill_cost_events.py` | REAL | writes_jsonl=True, size_bytes=2862 | writes to an existing metrics JSONL file |
| `scripts/backfill_session_decisions.py` | DORMANT | callers=0, size_bytes=6010 | no observable production use, no test, no on-demand marker |
| `scripts/benchmark-hooks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6102 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check-upstream-changes.sh` | DORMANT | callers=0, size_bytes=851 | no observable production use, no test, no on-demand marker |
| `scripts/check_absolute_paths.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7707 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_catalog_sync.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5750 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_hook_registration.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4187 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_lazy_catalog_health.py` | DORMANT | callers=0, size_bytes=5378 | no observable production use, no test, no on-demand marker |
| `scripts/check_lib_wiring.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=3690 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_mcp_servers.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10684 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_test_quality.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12113 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/check_test_ratchet.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4258 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/ci-setup.sh` | DORMANT | callers=0, size_bytes=5637 | no observable production use, no test, no on-demand marker |
| `scripts/ci-smoke-linux.sh` | DORMANT | callers=0, size_bytes=5941 | no observable production use, no test, no on-demand marker |
| `scripts/claim_proof_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6255 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cleanup-snapshots.sh` | DORMANT | callers=0, size_bytes=3707 | no observable production use, no test, no on-demand marker |
| `scripts/commit_provenance.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10620 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/component-lint.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9923 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/compose_agent_prompt.py` | DORMANT | callers=0, size_bytes=7540 | no observable production use, no test, no on-demand marker |
| `scripts/cos-bootstrap.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=15555 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-config-audit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=34332 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-core-skills-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8654 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-harness.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4611 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-doctor-memory-lifecycle.sh` | REAL | writes_jsonl=True, size_bytes=12581 | writes to an existing metrics JSONL file |
| `scripts/cos-doctor-tools.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9778 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-ghost-skills.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3683 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-init-global.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4626 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-init.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=294 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-paperclip-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9914 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-postgres-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=12036 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-project-registry-prune.sh` | DORMANT | callers=0, size_bytes=4293 | no observable production use, no test, no on-demand marker |
| `scripts/cos-registry.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8761 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-release-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=22089 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-session-spawn.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6770 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-sessions.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5570 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-smoke.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1587 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-startup-recover.sh` | REAL | writes_jsonl=True, size_bytes=3201 | writes to an existing metrics JSONL file |
| `scripts/cos-status.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=24123 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-update.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=28552 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos-usage-report.sh` | REAL | writes_jsonl=True, size_bytes=9385 | writes to an existing metrics JSONL file |
| `scripts/cos-valkey-local.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9587 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_build_self_knowledge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14449 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_chaos_template.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14967 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_classify_coverage.py` | REAL | writes_jsonl=True, size_bytes=9296 | writes to an existing metrics JSONL file |
| `scripts/cos_executor.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14660 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_governed_self_improvement.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2629 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_init.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=50832 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_profile_bootstrap.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2860 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_sprint.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=14519 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_test_artifact_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9088 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_test_quality_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=21934 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_watch.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=12194 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cos_work_queue.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6151 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/cost_predict.py` | REAL | writes_jsonl=True, size_bytes=2245 | writes to an existing metrics JSONL file |
| `scripts/create-release.sh` | DORMANT | callers=0, size_bytes=5274 | no observable production use, no test, no on-demand marker |
| `scripts/decision_triage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=32342 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/demo-first-run-onboarding.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5802 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/demo-governance.sh` | REAL | writes_jsonl=True, size_bytes=12835 | writes to an existing metrics JSONL file |
| `scripts/demo-portability-proof.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4891 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/deps-update.sh` | DORMANT | callers=0, size_bytes=24390 | no observable production use, no test, no on-demand marker |
| `scripts/detect_runner_capacity.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6794 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/doc_review_personas.py` | REAL | callers=1, size_bytes=3933 | referenced by 1 other component(s) |
| `scripts/docs_duplicate_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8786 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/docs_execution_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=11343 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/doctor.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=9702 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/document_feature_append.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2127 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/dogfood_score.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4022 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/domain_model.py` | REAL | callers=1, size_bytes=1495 | referenced by 1 other component(s) |
| `scripts/edit-coop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=13970 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/engram-sync.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4387 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/extract-agent-output.sh` | DORMANT | callers=0, size_bytes=4369 | no observable production use, no test, no on-demand marker |
| `scripts/generate-project-settings.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8376 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/generate_compact_catalog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=6764 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/git-coop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11298 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/harness_parity_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7669 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/hook-stream-statusline.sh` | DORMANT | callers=0, size_bytes=3967 | no observable production use, no test, no on-demand marker |
| `scripts/hook-timing-wrapper.sh` | REAL | writes_jsonl=True, size_bytes=16551 | writes to an existing metrics JSONL file |
| `scripts/hook_timing_report.py` | REAL | writes_jsonl=True, size_bytes=16542 | writes to an existing metrics JSONL file |
| `scripts/ide-bridge.sh` | DORMANT | callers=0, size_bytes=15015 | no observable production use, no test, no on-demand marker |
| `scripts/install-aguara.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1527 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-cos.sh` | DORMANT | callers=0, size_bytes=4985 | no observable production use, no test, no on-demand marker |
| `scripts/install-garak.sh` | DORMANT | callers=0, size_bytes=1277 | no observable production use, no test, no on-demand marker |
| `scripts/install-mcp-scan.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1545 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-pre-commit.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1099 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-promptfoo.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=1204 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/install-timing-test.sh` | REAL | writes_jsonl=True, size_bytes=6299 | writes to an existing metrics JSONL file |
| `scripts/install-tob-skills.sh` | DORMANT | callers=0, size_bytes=578 | no observable production use, no test, no on-demand marker |
| `scripts/invariant_check_helper.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9745 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/lint-shell.sh` | DORMANT | callers=0, size_bytes=5538 | no observable production use, no test, no on-demand marker |
| `scripts/llm_status.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=10576 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/manifest-check.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5671 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/measure_expansion.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4760 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/measure_harness_profiles.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5612 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/merge-settings.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=3190 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/migrate-to-cognitive-os.sh` | DORMANT | callers=0, size_bytes=3232 | no observable production use, no test, no on-demand marker |
| `scripts/ops_runbook.py` | REAL | callers=1, size_bytes=2044 | referenced by 1 other component(s) |
| `scripts/orchestrator.py` | REAL | writes_jsonl=True, size_bytes=14617 | writes to an existing metrics JSONL file |
| `scripts/parity_harness.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=22872 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_backend_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=19330 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_coverage.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=1996 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_gap_snapshot.py` | REAL | writes_jsonl=True, size_bytes=19164 | writes to an existing metrics JSONL file |
| `scripts/primitive_row_audit.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13292 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_surface_reduce.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9750 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/primitive_usage_map.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8982 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/project_scaffold.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2690 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/pytest-with-summary.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=18631 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/radar_merge.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=30391 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/reduction_backlog.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=4235 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/regen_catalog_bullets.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2656 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/register-mcps.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=16935 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/reserve_adr_slot.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=7770 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/risk_register.py` | REAL | callers=1, size_bytes=1499 | referenced by 1 other component(s) |
| `scripts/rules_export.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=5476 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/run-all-tests.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=4227 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/scope_tag_backfill.py` | DORMANT | callers=0, size_bytes=4137 | no observable production use, no test, no on-demand marker |
| `scripts/security_audit_writer.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=2851 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/session-leak-diagnostic.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5866 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/set-security-profile.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=10727 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/setup-git-hooks.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8628 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/setup.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11200 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/smoke-agent-quota-advisor.sh` | REAL | writes_jsonl=True, size_bytes=4127 | writes to an existing metrics JSONL file |
| `scripts/smoke-agent-quota-redirect.sh` | REAL | writes_jsonl=True, size_bytes=2646 | writes to an existing metrics JSONL file |
| `scripts/smoke-doc-review-personas.sh` | DORMANT | callers=0, size_bytes=2540 | no observable production use, no test, no on-demand marker |
| `scripts/smoke-multi-provider-fallback.sh` | DORMANT | callers=0, size_bytes=3901 | no observable production use, no test, no on-demand marker |
| `scripts/smoke-qwen-fallback.sh` | DORMANT | callers=0, size_bytes=4133 | no observable production use, no test, no on-demand marker |
| `scripts/so-emergency-stop.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5790 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/so-reaper.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5921 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/so-vitals.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8164 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/so_session_watchdog.py` | REAL | writes_jsonl=True, size_bytes=13243 | writes to an existing metrics JSONL file |
| `scripts/so_vs_vanilla_benchmark.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=16117 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/sprint-test-summary.sh` | DORMANT | callers=0, size_bytes=2035 | no observable production use, no test, no on-demand marker |
| `scripts/startup-benchmark.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=11968 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-agent-teams-hooks.sh` | DORMANT | callers=0, size_bytes=4384 | no observable production use, no test, no on-demand marker |
| `scripts/test-all.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=8403 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-cognitive-os-full.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6690 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-cognitive-os.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2021 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test-mcp-server.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=2889 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/test_run_inventory.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=13058 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/uninstall.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6475 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/update_readme_badges.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=9591 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/upgrade.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=6760 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/validate_tier_filter.py` | REAL | writes_jsonl=True, size_bytes=22633 | writes to an existing metrics JSONL file |
| `scripts/version.sh` | ON_DEMAND | callers=0, has_test=True, size_bytes=5907 | covered by test — legit sleeper (test proves it works when called) |
| `scripts/weekly-aspirational-audit.sh` | DORMANT | callers=0, size_bytes=998 | no observable production use, no test, no on-demand marker |
| `scripts/write_context_marker.py` | ON_DEMAND | callers=0, has_test=True, size_bytes=8757 | covered by test — legit sleeper (test proves it works when called) |
| `skills/__contracts__/SKILL.md` | ASPIRATIONAL | invocations_30d=0, referenced_in_docs=False | no invocations and not referenced in rules or docs |
| `skills/add-hook/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/add-mcp/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/add-rule/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/add-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/agent-dashboard/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/agent-kpis/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/agent-stress-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/analyze-improvements/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/apply-improvements/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/arena/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/audit-integrity/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/audit-website/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/auto-refine/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/auto-rollback/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/automaker-bridge/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/batch-runner/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/bump-version/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/capability-snapshot/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/catalog-full/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/caveman/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/caveman-compress/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/caveman-es/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/code-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognee-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognee-search/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-benchmark/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-init/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cognitive-os-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/compat-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/component-classifier/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/component-reality-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/compose-prompt/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/confidence-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/contract-drift/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/conversation-memory/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/coordination-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cos-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/cost-predictor/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/coverage-enforcement/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/decision-triage/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deep-research/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deepeval-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/deps-update/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/detect-patterns/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/detect-stack/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/devbox-checkpoint/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/doc-review-personas/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/doc-sync/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/docs-execution-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/document-feature/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/dod-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/dogfood-score/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/domain-model/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/error-analyzer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/eval-repo/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/evaluate-plan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/exhaustive-prompt/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/experimental/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/generate-changelog/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/generate-config/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/gpu-sandbox/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/harness-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/hook-timing/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/impact-analysis/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/install-recommended/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/invariant-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/issue-pipeline/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/jupyter-execute/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/llm-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/memory-scan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/memu-context/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/metrics-calibrator/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/model-optimizer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/nemo-guardrails/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/ops-runbook/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/optimize-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/paperclip-dashboard/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pattern-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pentest-self/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/persistent-agent/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/phoenix-trace-ui/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/plan-bug/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/plan-feature/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/planning-poker/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/pr-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/primitive-surface-reduction/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/primitive-usage-map/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/private-mode/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/project-scaffold/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/promptfoo-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/push-release/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/queue-drain/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/radar-update/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/ragas-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/readiness-check/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/recall-search/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/recommend-library/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/red-team/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/release-os/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repair-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repair-status/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repo-forensics/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/repo-scout/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/research-protocol/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resolve-blockers/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resource-governor/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/resume-tasks/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/retrospective/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/reverse-engineer/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/review-output/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/risk-register/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/rules-export/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/run-tests/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sandbox-sample/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/scaffold-project/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/scout/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-compound/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-continue/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-explore/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sdd-resume/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/secret-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/security-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/self-improve/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/self-review/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/semgrep-scan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-backlog/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-manager/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-report-executive/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/session-wrapup/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/simulation-arena/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/singularity/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/skill-creator/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/smoke-test/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/so-vs-vanilla/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sprint/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/squad-manager/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/sre-agent/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/strands-evals-integration/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/synthesize-skill/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/systematic-debugging/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/tag-release/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/test-contract-repair/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/test-driven-development/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/tool-discovery/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/trust-audit/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/validate-config/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/validate-release/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/verification-before-completion/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/vulnerability-scan/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/web-crawler/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
| `skills/webhook-trigger/SKILL.md` | DORMANT | invocations_30d=0, referenced_in_docs=True | referenced in rules/docs but no recorded invocations in 30 days |
