# Primitive Scope Unknown Triage

This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.

## Summary

```json
{
  "by_bucket": {
    "conflicting-metadata": 4,
    "insufficient-metadata": 315,
    "os-only-semantic-candidate": 70,
    "project-only-semantic-candidate": 4
  },
  "by_declared_scope": {
    "both": 354,
    "os-only": 39
  },
  "by_gap": {
    "conflicting-distribution-evidence": 4,
    "missing-consumer-availability-row": 393,
    "missing-lifecycle-row": 393,
    "no-distribution-evidence": 389
  },
  "by_prefix": {
    "hooks": 152,
    "rules": 83,
    "scripts": 158
  },
  "total_unknown": 393
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

## insufficient-metadata (315)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/adaptive-bypass.sh` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Adaptive Bypass — Automatic Complexity Classification |
| `hooks/adr-detector.sh` | both | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: architecture, governance, documentation |
| `hooks/adr-relevance-suggest.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | UserPromptSubmit hook: ADR Relevance Suggest |
| `hooks/agent-control-inbound-guard.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Blocks hook-capable harnesses at tool/action boundaries when an inbound |
| `hooks/agent-prelaunch.sh` | both | os=4; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Register sub-agent tasks before launch |
| `hooks/agent-qwen-bridge.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse:Agent hook — ADR-056 Level 3: transparent Qwen bridge (per-skill opt-in) |
| `hooks/agent-working-dir-inject.sh` | both | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — injects a WORKING DIR directive into every sub-agent's |
| `hooks/auto-refine.sh` | both | os=3; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, refinement, piter-loop, phase-aware |
| `hooks/auto-repair-dispatcher.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Auto-Repair Dispatcher |
| `hooks/auto-rollback-trigger.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook on Agent — detects verify-apply retry exhaustion and requests |
| `hooks/auto-verify.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, verification, acceptance-criteria |
| `hooks/blast-radius.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Blast Radius Estimation |
| `hooks/branch-ownership-lock.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-182: acquire/enforce per-branch single-writer locks for destructive git operations. |
| `hooks/claim-validator.sh` | both | os=3; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, hallucination, verification |
| `hooks/clarification-gate.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Clarification Gate |
| `hooks/clarification-interceptor.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook on Agent — detects NEEDS_CLARIFICATION marker in agent output. |
| `hooks/completeness-check-llm.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Completeness Check (LLM-evaluated, ADR-022) |
| `hooks/concurrent-write-guard.sh` | both | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: File locking for concurrent sessions |
| `hooks/confidence-gate-llm.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Confidence Gate (LLM-evaluated, ADR-022) |
| `hooks/context-diet.sh` | both | os=3; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Context Diet — Task-aware rule selection advisory |
| `hooks/context-watchdog.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Context Watchdog — estimates context usage and emits one-shot checkpoint warnings. |
| `hooks/control-plane-audit.sh` | both | os=4; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: primitive-coherence, postmortem-regression, control-plane-loop |
| `hooks/cosd-auth-guard.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse guard for ADR-194: cosd remote API requires explicit remote opt-in |
| `hooks/cross-session-coordination-guard.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Guard high-risk multi-session operations with a shared coordination ledger. |
| `hooks/cross-session-peer-context.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-183: inject compact peer-session awareness on UserPromptSubmit. |
| `hooks/destructive-git-blocker.sh` | both | os=5; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, git-ops, adr-003-mechanism-c |
| `hooks/dod-gate.sh` | both | os=3; generic=7; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, definition-of-done, phase-aware |
| `hooks/engram-crystallize-on-session-end.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Crystallise over-represented topic_keys at session end |
| `hooks/engram-reinforce-on-access.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Reinforce engram observations on mem_search and mem_get_observation access |
| `hooks/epic-task-detector.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Epic Task Detector |
| `hooks/error-learning.sh` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Error Learning |
| `hooks/error-pattern-detector.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Error Pattern Detector — PreToolUse for Agent |
| `hooks/error-pipeline.sh` | both | os=3; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: observability, recovery, logging |
| `hooks/inject-phase-context.sh` | both | os=4; generic=4; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — injects phase context from cognitive-os.yaml into agent prompts. |
| `hooks/kpi-trigger.sh` | os-only | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | KPI Trigger Hook — Stop hook (runs at session end) |
| `hooks/lethal-trifecta-gate.sh` | os-only | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: blocks private data + untrusted content + external communication. |
| `hooks/memory-prefetch.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Memory Prefetch — UserPromptSubmit hook |
| `hooks/orchestrator-claim-gate.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | orchestrator-claim-gate.sh — Cross-IDE PreToolUse gate for high-stakes closure claims. |
| `hooks/orchestrator-decision-trace.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Orchestrator Decision Trace |
| `hooks/orchestrator-mode-detect.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @on-demand: sourced library helper — not registered independently, sourced by other hooks |
| `hooks/plan-claim-validator.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | plan-claim-validator.sh — PreToolUse hook for Edit/Write/MultiEdit on plan files. |
| `hooks/pre-compaction-flush.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreCompact hook: Reminds the agent to save durable memories to Engram |
| `hooks/prompt-quality-llm.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Prompt Quality (LLM-evaluated, ADR-022) |
| `hooks/query-tailored-context-inject.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — injects semantically relevant ADRs, lib modules, |
| `hooks/rate-limit-detector.sh` | os-only | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | rate-limit-detector.sh — PostToolUse advisory |
| `hooks/rate-limit-protection.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `hooks/resource-check.sh` | both | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — checks resource budget before agent launches. |
| `hooks/review-spawner.sh` | os-only | os=3; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, learning-loop, audit |
| `hooks/scope-marker-portability-gate.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | scope-marker-portability-gate.sh — PreToolUse Bash hook for KD6 portability proof. |
| `hooks/scope-proportionality.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Scope Proportionality Check |
| … | … | … | … | … | 265 more rows in JSON report. |

## os-only-semantic-candidate (70)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
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
| `hooks/confidence-gate.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook on Agent — enforces confidence thresholds from Trust Reports. |
| `hooks/consequence-evaluator.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | consequence-evaluator.sh — PostToolUse hook on Agent |
| `hooks/context-budget-meter.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-186: last-in-chain UserPromptSubmit context-budget meter. |
| `hooks/control-plane-audit-hourly.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: primitive-coherence, postmortem-regression, periodic-drift |
| `hooks/crash-recovery.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: fault-tolerance, recovery |
| `hooks/cross-session-event-emit.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-183: emit standardized cross-session events into .cognitive-os/sessions/events.jsonl. |
| `hooks/direct-main-guard.sh` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | direct-main-guard.sh — ADR-116 P2.1/P2.2 local branch-isolation policy. |
| `hooks/document-ingest-guard.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse Read guard: block direct PDF reads and route through cos-document-ingest. |
| `hooks/edit-lock-drain-parked.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-drain-parked.sh — ADR-098 Phase D1: parked-edit drain notification |
| `hooks/edit-lock-pre-tool.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-pre-tool.sh — ADR-098 PreToolUse[Edit\|Write] enforcement |
| `hooks/edit-lock-process-negotiations.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-process-negotiations.sh — ADR-098 Phase D2: surface incoming lock negotiations |
| `hooks/edit-lock-session-end.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | edit-lock-session-end.sh — ADR-098 Phase C: release this session's edit locks on Stop. |
| `hooks/engram-daemon-launcher.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Ensure engram serve daemon (port 7437) is running for ADR-071 lifecycle hooks |
| `hooks/git-context-capture.sh` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | git-context-capture.sh — Stop hook |
| `hooks/host-tool-doctor.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SessionStart hook: cached host tooling doctor. |
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
| `hooks/pre-commit-content-hash-dedupe.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | pre-commit-content-hash-dedupe.sh — P4.1 (ADR-116) |
| `hooks/profile-drift-autoapply.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Auto-reapply efficiency profile when apply-efficiency-profile.sh changes |
| `hooks/promotion-proposer-weekly.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | promotion-proposer-weekly.sh — SessionStart hook (ADR-178) |
| `hooks/reaper-daemon-launcher.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | reaper-daemon-launcher.sh — SessionStart hook: schedule periodic process reaper (ADR-028 D1.B) |
| `hooks/research-quality-validator.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: research-quality, audit-symmetry, evidence |
| `hooks/research-to-runtime-firewall.sh` | os-only | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | research-to-runtime-firewall.sh — ADR-267 Hook #6. |
| `hooks/result-truncator.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: performance, quality, observability |
| `hooks/rule-frontmatter-validator.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Validate field contract for rules/*.md on Write/Edit (ADR-067 Phase 2) |
| `hooks/rule-md-routing-validator.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse Write hook: rules/*.md Routing Pattern Validator (ADR-179) |
| `hooks/rule-router-prompt-suggest.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | UserPromptSubmit hook: Rule Router Prompt Suggest (ADR-179) |
| `hooks/scope-creep-detector.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Scope Creep Detection |
| `hooks/session-changelog.sh` | os-only | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | session-changelog.sh — Stop hook |
| `hooks/session-cleanup.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Stop hook: Clean up session on exit |
| … | … | … | … | … | 20 more rows in JSON report. |

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

