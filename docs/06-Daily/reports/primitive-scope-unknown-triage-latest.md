# Primitive Scope Unknown Triage

This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.

## Summary

```json
{
  "by_bucket": {
    "conflicting-metadata": 4,
    "insufficient-metadata": 335,
    "os-only-semantic-candidate": 83,
    "project-only-semantic-candidate": 4
  },
  "by_declared_scope": {
    "both": 367,
    "os-only": 59
  },
  "by_gap": {
    "conflicting-distribution-evidence": 4,
    "missing-consumer-availability-row": 426,
    "missing-lifecycle-row": 426,
    "no-distribution-evidence": 422
  },
  "by_prefix": {
    "hooks": 185,
    "rules": 83,
    "scripts": 158
  },
  "total_unknown": 426
}
```

## Bucket meanings

| Bucket | Meaning | Default action |
|---|---|---|
| `conflicting-metadata` | Durable metadata disagrees. | Reconcile lifecycle/consumer metadata before marker changes. |
| `declared-both-needs-proof-and-metadata` | Marker says `both`, but distribution/proof evidence is absent or incomplete. | Add paired proof and lifecycle/consumer evidence, or demote after semantic review. |
| `declared-both-os-internal-heavy` | Marker says `both`, but content is dominated by SO-internal concepts. | Prioritize manual review for likely stale marker. |
| `missing-scope-marker` | Parser/classifier found no explicit marker and not enough evidence. | Add marker only after semantic review. |
| `project-only-semantic-candidate` | Text suggests downstream-project-only behavior. | Add project-only metadata/proof if confirmed. |
| `both-semantic-candidate` | Text looks repo-agnostic and generic. | Add portability proof and distribution metadata if confirmed. |
| `os-only-semantic-candidate` | Text looks SO-internal. | Add os-only lifecycle/consumer metadata if confirmed. |
| `insufficient-metadata` | No clear deterministic semantic direction. | Needs manual or AI-assisted adjudication. |

## insufficient-metadata (335)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/_lib/register-bg.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | register-bg.sh — ADR-028 D1.B  Process Registry helper |
| `hooks/_lib/remediation.sh` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | remediation.sh — Shared library for remediation registry operations |
| `hooks/_lib/resolve-main-worktree.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | resolve-main-worktree.sh — Shared library: resolve the main worktree path. |
| `hooks/_lib/safe-jsonl.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | safe-jsonl.sh — Shared library for safe JSONL writes + hook health heartbeats |
| `hooks/_lib/semantic-search.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | semantic-search.sh — Fuzzy error matching via vector similarity |
| `hooks/_lib/session-fs-reap.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Archive-first filesystem reaper for .cognitive-os/sessions. |
| `hooks/_lib/session_init_helper.py` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Consolidated helper for session-init.sh. |
| `hooks/_lib/singularity-suggestion.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | _singularity_suggestion — Advisory singularity run suggestion. |
| `hooks/_lib/stash-lock.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | stash-lock.sh — Flock coordinator library for git stash operations. |
| `hooks/_lib/task-identity.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Resolve one canonical task id for cross-session claim coordination. |
| `hooks/_lib/task_bridge.py` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Task Bridge — correlates COS task_id with Claude Code tool_use_id. |
| `hooks/_lib/timing.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | timing.sh — Hook timing wrapper for Cognitive OS performance monitoring |
| `hooks/_lib/tuning.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | tuning.sh — Shared helper for hooks with tunable thresholds. |
| `hooks/aci-observation-capture.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: normalize tool output into ACI observations and trajectory rows. |
| `hooks/adaptive-bypass.sh` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Adaptive Bypass — Automatic Complexity Classification |
| `hooks/adoption-freeze-gate.sh` | os-only | os=4; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | adoption-freeze-gate.sh — ADR-267 Hook #3 (Layer 1 — kill-switch). |
| `hooks/adr-detector.sh` | both | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: architecture, governance, documentation |
| `hooks/adr-relevance-suggest.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | UserPromptSubmit hook: ADR Relevance Suggest |
| `hooks/agent-control-inbound-guard.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Blocks hook-capable harnesses at tool/action boundaries when an inbound |
| `hooks/agent-prelaunch.sh` | both | os=4; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Register sub-agent tasks before launch |
| `hooks/agent-qwen-bridge.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse:Agent hook — ADR-056 Level 3: transparent Qwen bridge (per-skill opt-in) |
| `hooks/agent-working-dir-inject.sh` | both | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — injects a WORKING DIR directive into every sub-agent's |
| `hooks/aspirational-audit-weekly.sh` | os-only | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | aspirational-audit-weekly.sh — SessionStart hook |
| `hooks/attribution-completeness-validator.sh` | os-only | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | attribution-completeness-validator.sh — ADR-267 Hook #5. |
| `hooks/auto-refine.sh` | both | os=3; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, refinement, piter-loop, phase-aware |
| `hooks/auto-repair-dispatcher.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Auto-Repair Dispatcher |
| `hooks/auto-rollback-trigger.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook on Agent — detects verify-apply retry exhaustion and requests |
| `hooks/auto-skill-generator.sh` | os-only | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Auto-generate SKILL.md from complex agent completions |
| `hooks/auto-verify.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, verification, acceptance-criteria |
| `hooks/blast-radius.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Blast Radius Estimation |
| `hooks/branch-ownership-lock.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-182: acquire/enforce per-branch single-writer locks for destructive git operations. |
| `hooks/claim-validator.sh` | both | os=3; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, hallucination, verification |
| `hooks/clarification-gate.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Clarification Gate |
| `hooks/clarification-interceptor.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook on Agent — detects NEEDS_CLARIFICATION marker in agent output. |
| `hooks/completeness-check-llm.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Completeness Check (LLM-evaluated, ADR-022) |
| `hooks/completeness-check.sh` | os-only | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | completeness-check.sh — Compatibility entrypoint for level-5 completeness gating. |
| `hooks/concurrent-write-guard.sh` | both | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: File locking for concurrent sessions |
| `hooks/confidence-gate-llm.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Confidence Gate (LLM-evaluated, ADR-022) |
| `hooks/context-diet.sh` | both | os=3; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Context Diet — Task-aware rule selection advisory |
| `hooks/context-watchdog.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Context Watchdog — estimates context usage and emits one-shot checkpoint warnings. |
| `hooks/control-plane-audit.sh` | both | os=4; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: primitive-coherence, postmortem-regression, control-plane-loop |
| `hooks/cosd-auth-guard.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse guard for ADR-194: cosd remote API requires explicit remote opt-in |
| `hooks/cross-session-coordination-guard.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Guard high-risk multi-session operations with a shared coordination ledger. |
| `hooks/cross-session-peer-context.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-183: inject compact peer-session awareness on UserPromptSubmit. |
| `hooks/decision-depth-gate.sh` | os-only | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, verification, decision-depth |
| `hooks/destructive-git-blocker.sh` | both | os=5; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, git-ops, adr-003-mechanism-c |
| `hooks/dod-gate.sh` | both | os=3; generic=7; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, definition-of-done, phase-aware |
| `hooks/engram-crystallize-on-session-end.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Crystallise over-represented topic_keys at session end |
| `hooks/engram-reinforce-on-access.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Reinforce engram observations on mem_search and mem_get_observation access |
| `hooks/epic-task-detector.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Epic Task Detector |
| … | … | … | … | … | 285 more rows in JSON report. |

## os-only-semantic-candidate (83)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/adr-section-validator.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Validate section contract for docs/02-Decisions/adrs/ADR-*.md on Write/Edit (ADR-067 Phase 2) |
| `hooks/agent-bash-cwd-enforcer.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Bash — legacy main_worktree policy rewriter. |
| `hooks/agent-checkpoint.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: state, lifecycle, orchestration |
| `hooks/agent-launch-confirmed.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, agent-lifecycle, adr-222, adr-221 |
| `hooks/agent-message-inbox-context.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-185: inject pending directed agent messages on UserPromptSubmit. |
| `hooks/agent-message-inbox-guard.sh` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-185: warn/block risky Bash/git boundaries when this session has unacked block messages. |
| `hooks/agent-output-verifier.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Verify that files agents claim to have created actually exist |
| `hooks/assumption-tracker.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Assumption Tracker |
| `hooks/audit-id-enricher.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | audit-id-enricher.sh — PostToolUse hook on Agent\|Bash |
| `hooks/auto-checkpoint.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: fault-tolerance, recovery, checkpoints |
| `hooks/branch-ownership-release.sh` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-182: release all branch locks held by this session on Stop. |
| `hooks/codebase-itinerary-capture.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Codebase Itinerary Capture |
| `hooks/confidence-gate.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook on Agent — enforces confidence thresholds from Trust Reports. |
| `hooks/consequence-evaluator.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | consequence-evaluator.sh — PostToolUse hook on Agent |
| `hooks/context-budget-meter.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-186: last-in-chain UserPromptSubmit context-budget meter. |
| `hooks/control-plane-audit-hourly.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: primitive-coherence, postmortem-regression, periodic-drift |
| `hooks/cos-executor-daemon-launcher.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | cos-executor-daemon-launcher.sh — SessionStart hook: start cos-executor daemon (ADR-034). |
| `hooks/cos-session-start-projector.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-275 — Wrapper invoking scripts/cos-session-start-projector (Python). |
| `hooks/crash-recovery.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: fault-tolerance, recovery |
| `hooks/cross-session-event-emit.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-183: emit standardized cross-session events into .cognitive-os/sessions/events.jsonl. |
| `hooks/dependency-license-classifier.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | dependency-license-classifier.sh — ADR-267 Hook #1. |
| `hooks/dequeue-notify.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Dequeue Notify — notifies orchestrator when agent slots free up after completion. |
| `hooks/direct-main-guard.sh` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | direct-main-guard.sh — ADR-116 P2.1/P2.2 local branch-isolation policy. |
| `hooks/dispatch-gate.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: concurrency, resource-protection, workload-scheduling |
| `hooks/docker-drift-detector.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | docker-drift-detector.sh — SessionStart advisory |
| `hooks/document-ingest-guard.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse Read guard: block direct PDF reads and route through cos-document-ingest. |
| `hooks/edit-lock-drain-parked.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-drain-parked.sh — ADR-098 Phase D1: parked-edit drain notification |
| `hooks/edit-lock-pre-tool.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-pre-tool.sh — ADR-098 PreToolUse[Edit\|Write] enforcement |
| `hooks/edit-lock-process-negotiations.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-process-negotiations.sh — ADR-098 Phase D2: surface incoming lock negotiations |
| `hooks/edit-lock-session-end.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-session-end.sh — ADR-098 Phase C: release this session's edit locks on Stop. |
| `hooks/engram-daemon-launcher.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Ensure engram serve daemon (port 7437) is running for ADR-071 lifecycle hooks |
| `hooks/external-cache-content-leak.sh` | os-only | os=5; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | external-cache-content-leak.sh — ADR-267 Hook #2. |
| `hooks/external-pattern-cleanroom-gate.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | external-pattern-cleanroom-gate.sh — Pre-commit clean-room gate for external-pattern adoptions |
| `hooks/git-context-capture.sh` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | git-context-capture.sh — Stop hook |
| `hooks/history-rewrite-documented.sh` | os-only | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-269 Primitive 2 — SessionStart hook warning operators about |
| `hooks/hook-header-validator.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Validate header contract for hooks/*.sh on Write/Edit (ADR-067 Phase 2) |
| `hooks/host-tool-doctor.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SessionStart hook: cached host tooling doctor. |
| `hooks/infra-health.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Infrastructure Health Check — SessionStart hook |
| `hooks/large-file-advisor.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, observability |
| `hooks/legal-review-required-on-runtime-import.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | legal-review-required-on-runtime-import.sh — Pre-commit gate (ADR-270 primitive #8) |
| `hooks/lib-symlink-divergence-detector.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | lib-symlink-divergence-detector.sh — PreToolUse Bash hook. |
| `hooks/native-agent-heartbeat.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | native-agent-heartbeat.sh — PreToolUse:Agent + PostToolUse:Agent hook |
| `hooks/orchestrator-skill-invocation-gate.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | orchestrator-skill-invocation-gate.sh — ADR-188 |
| `hooks/pending-truth-drift-detector.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: drift-prevention, pending-truth-ledger, anti-accumulation |
| `hooks/pending-truth-staleness-gate.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: pending-truth-ledger, anti-staleness, pre-commit-gate |
| `hooks/pending-truth-verify-weekly.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: pending-truth-ledger, weekly-verification, anti-staleness |
| `hooks/post-agent-snapshot-restore.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, agent-lifecycle, adr-003-mechanism-a, adr-099, adr-221 |
| `hooks/post-agent-verify.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, agent-lifecycle, adr-003-mechanism-b, adr-099 |
| `hooks/post-git-orphan-notifier.sh` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | post-git-orphan-notifier.sh — PostToolUse Bash |
| `hooks/pre-agent-snapshot.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, agent-lifecycle, adr-003-mechanism-a, adr-099 |
| … | … | … | … | … | 33 more rows in JSON report. |

## conflicting-metadata (4)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `scripts/apply-efficiency-profile.sh` | os-only | os=3; generic=2; project=0 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | Apply Efficiency Profile — Delegates hook projection to per-harness settings drivers. |
| `scripts/cos-bootstrap.sh` | os-only | os=3; generic=0; project=0 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | ============================================================================= |
| `scripts/generate-project-settings.sh` | os-only | os=2; generic=3; project=0 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | generate-project-settings.sh — Generate harness-aware hook settings for external projects |
| `scripts/set-security-profile.sh` | os-only | os=2; generic=1; project=1 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | Set Security Profile — Applies the selected security profile to Claude settings |

## project-only-semantic-candidate (4)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/completion-gate.sh` | both | os=3; generic=7; project=2 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, verification, testing |
| `hooks/project-docs-convention.sh` | both | os=2; generic=1; project=2 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: documentation, governance |
| `scripts/cos-adapter-compile` | both | os=0; generic=0; project=2 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Compile COS primitive contracts into native consumer-project IDE files. |
| `scripts/documentation_truth_audit.py` | both | os=4; generic=1; project=2 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit volatile documentation claims against generated truth sources. |

