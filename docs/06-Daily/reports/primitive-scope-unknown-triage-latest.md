# Primitive Scope Unknown Triage

This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.

## Summary

```json
{
  "by_bucket": {
    "conflicting-metadata": 4,
    "insufficient-metadata": 271,
    "os-only-semantic-candidate": 24,
    "project-only-semantic-candidate": 4
  },
  "by_declared_scope": {
    "both": 299,
    "os-only": 4
  },
  "by_gap": {
    "conflicting-distribution-evidence": 4,
    "missing-consumer-availability-row": 303,
    "missing-lifecycle-row": 303,
    "no-distribution-evidence": 299
  },
  "by_prefix": {
    "hooks": 62,
    "rules": 83,
    "scripts": 158
  },
  "total_unknown": 303
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

## insufficient-metadata (271)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/agent-control-inbound-guard.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Blocks hook-capable harnesses at tool/action boundaries when an inbound |
| `hooks/agent-prelaunch.sh` | both | os=4; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Register sub-agent tasks before launch |
| `hooks/agent-qwen-bridge.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse:Agent hook — ADR-056 Level 3: transparent Qwen bridge (per-skill opt-in) |
| `hooks/agent-working-dir-inject.sh` | both | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — injects a WORKING DIR directive into every sub-agent's |
| `hooks/auto-refine.sh` | both | os=3; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, refinement, piter-loop, phase-aware |
| `hooks/auto-repair-dispatcher.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Auto-Repair Dispatcher |
| `hooks/clarification-interceptor.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook on Agent — detects NEEDS_CLARIFICATION marker in agent output. |
| `hooks/cosd-auth-guard.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse guard for ADR-194: cosd remote API requires explicit remote opt-in |
| `hooks/cross-session-coordination-guard.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Guard high-risk multi-session operations with a shared coordination ledger. |
| `hooks/cross-session-peer-context.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-183: inject compact peer-session awareness on UserPromptSubmit. |
| `hooks/epic-task-detector.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Epic Task Detector |
| `hooks/error-learning.sh` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Error Learning |
| `hooks/error-pattern-detector.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Error Pattern Detector — PreToolUse for Agent |
| `hooks/error-pipeline.sh` | both | os=3; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: observability, recovery, logging |
| `hooks/inject-phase-context.sh` | both | os=4; generic=4; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — injects phase context from cognitive-os.yaml into agent prompts. |
| `hooks/memory-prefetch.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Memory Prefetch — UserPromptSubmit hook |
| `hooks/orchestrator-claim-gate.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | orchestrator-claim-gate.sh — Cross-IDE PreToolUse gate for high-stakes closure claims. |
| `hooks/orchestrator-decision-trace.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Orchestrator Decision Trace |
| `hooks/orchestrator-mode-detect.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @on-demand: sourced library helper — not registered independently, sourced by other hooks |
| `hooks/plan-claim-validator.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | plan-claim-validator.sh — PreToolUse hook for Edit/Write/MultiEdit on plan files. |
| `hooks/pre-compaction-flush.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreCompact hook: Reminds the agent to save durable memories to Engram |
| `hooks/query-tailored-context-inject.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Agent — injects semantically relevant ADRs, lib modules, |
| `hooks/rate-limit-protection.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `hooks/scope-marker-portability-gate.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | scope-marker-portability-gate.sh — PreToolUse Bash hook for KD6 portability proof. |
| `hooks/session-end-cleanup.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | session-end-cleanup.sh — runs `cos-cleanup --tier=1 --apply` quietly. |
| `hooks/session-init.sh` | both | os=4; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SessionStart hook: Initialize session isolation |
| `hooks/session-sanity.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @on-demand: advisory diagnostic; invoke manually when troubleshooting cos-status or missing .cognitive-os dir |
| `hooks/session-startup-protocol.sh` | both | os=4; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SessionStart hook: Startup Protocol Reminder |
| `hooks/session-summary-reminder.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Stop hook: ensures a session_summary observation lands in engram before |
| `hooks/session-wrapup-trigger.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | UserPromptSubmit hook — auto-suggest /session-wrapup when user signals close. |
| `hooks/state-retention-audit.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | state-retention-audit.sh — ADR-199 retention drift monitor. |
| `hooks/subagent-context-injector.sh` | both | os=1; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SubagentStart hook: Inject agent preamble + engram sidecar context into every subagent. |
| `hooks/task-completed.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | TaskCompleted hook: Verify completion criteria when a teammate marks a task done. |
| `hooks/task-created.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | TaskCreated hook: Validate task quality when created in the shared task list. |
| `hooks/task-recorder.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Stop hook: Record completed task info to task-history.jsonl |
| `hooks/teammate-idle.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | TeammateIdle hook: Check for unclaimed tasks when a teammate is about to go idle. |
| `hooks/user-prompt-capture.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `rules/RULES-COMPACT.md` | both | os=4; generic=8; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | COS Rules Index |
| `rules/adaptive-bypass.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Adaptive Bypass — Smart Orchestration |
| `rules/agent-audit-before-commit.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Audit Before Commit |
| `rules/agent-escalation.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Escalation Protocol |
| `rules/agent-identity.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Identity Protocol |
| `rules/agent-kpis.md` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent KPI Protocol |
| `rules/agent-output-reading.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Output Reading Protocol |
| `rules/agent-security.md` | both | os=1; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Security — Least Privilege Protocol |
| `rules/aguara-integration.md` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Aguara -- AI Agent Security Scanner |
| `rules/ai-provider-identity.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | AI Provider Identity Guard |
| `rules/anti-hallucination.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Anti-Hallucination Rule |
| `rules/assumption-tracking.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Assumption Tracking |
| `rules/audit-trail.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit Trail — Automated Work Tracking |
| … | … | … | … | … | 221 more rows in JSON report. |

## os-only-semantic-candidate (24)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/agent-bash-cwd-enforcer.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook on Bash — legacy main_worktree policy rewriter. |
| `hooks/agent-checkpoint.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: state, lifecycle, orchestration |
| `hooks/agent-launch-confirmed.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, agent-lifecycle, adr-222, adr-221 |
| `hooks/agent-message-inbox-context.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-185: inject pending directed agent messages on UserPromptSubmit. |
| `hooks/agent-message-inbox-guard.sh` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-185: warn/block risky Bash/git boundaries when this session has unacked block messages. |
| `hooks/agent-output-verifier.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Verify that files agents claim to have created actually exist |
| `hooks/audit-id-enricher.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | audit-id-enricher.sh — PostToolUse hook on Agent\|Bash |
| `hooks/consequence-evaluator.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | consequence-evaluator.sh — PostToolUse hook on Agent |
| `hooks/cross-session-event-emit.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-183: emit standardized cross-session events into .cognitive-os/sessions/events.jsonl. |
| `hooks/document-ingest-guard.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse Read guard: block direct PDF reads and route through cos-document-ingest. |
| `hooks/git-context-capture.sh` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | git-context-capture.sh — Stop hook |
| `hooks/host-tool-doctor.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SessionStart hook: cached host tooling doctor. |
| `hooks/orchestrator-skill-invocation-gate.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | orchestrator-skill-invocation-gate.sh — ADR-188 |
| `hooks/pending-truth-drift-detector.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: drift-prevention, pending-truth-ledger, anti-accumulation |
| `hooks/pending-truth-staleness-gate.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: pending-truth-ledger, anti-staleness, pre-commit-gate |
| `hooks/pending-truth-verify-weekly.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: pending-truth-ledger, weekly-verification, anti-staleness |
| `hooks/research-quality-validator.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: research-quality, audit-symmetry, evidence |
| `hooks/result-truncator.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: performance, quality, observability |
| `hooks/session-cleanup.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Stop hook: Clean up session on exit |
| `hooks/session-heartbeat.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | session-heartbeat.sh — Liveness signal for ADR-047 session lifecycle watchdog. |
| `hooks/session-learning.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Session Learning Hook — Stop hook (runs at session end) |
| `hooks/subagent-capability-preflight.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: subagent-contracts, launch-preflight, artifact-safety |
| `hooks/surface-fix-detector.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: quality, decision-depth, invariant-drift |
| `scripts/cos-governed-edit.sh` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Portable edit guard for harnesses without Edit/Write hook parity. |

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

