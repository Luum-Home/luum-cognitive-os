# Primitive Scope Unknown Triage

This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.

## Summary

```json
{
  "by_bucket": {
    "declared-both-needs-proof-and-metadata": 70,
    "insufficient-metadata": 344,
    "os-only-semantic-candidate": 41
  },
  "by_declared_scope": {
    "both": 390,
    "os-only": 65
  },
  "by_gap": {
    "declared-both-missing-paired-proof": 70,
    "missing-consumer-availability-row": 455,
    "missing-lifecycle-row": 455,
    "no-distribution-evidence": 455
  },
  "by_prefix": {
    "hooks": 58,
    "packages": 72,
    "rules": 92,
    "scripts": 140,
    "skills": 75,
    "templates": 18
  },
  "total_unknown": 455
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

## insufficient-metadata (344)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/_lib/artifact-status.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Shared artifact status loaders for governance hooks. |
| `hooks/_lib/cache.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | cache.sh — SHA-256 file cache for hook scans |
| `hooks/_lib/circuit-breaker.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | circuit-breaker.sh — Per-error-type circuit breaker for auto-repair |
| `hooks/_lib/common.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | common.sh — Shared utility functions for Cognitive OS hooks |
| `hooks/_lib/context_budget_lib.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Shared ADR-186 context-budget accountant for hooks that emit additionalContext. |
| `hooks/_lib/dispatch_gate_check.py` | both | os=2; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Single-pass dispatch gate check — consolidates all python3 invocations from dispatch-gate.sh. |
| `hooks/_lib/execute-repair.sh` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | execute-repair.sh — Core execution engine for auto-repair system |
| `hooks/_lib/file_checker.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Symlink-aware file existence checker. |
| `hooks/_lib/hook-pipe.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | hook-pipe.sh — Inter-hook data sharing within an event chain |
| `hooks/_lib/normalize-stdin.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | normalize-stdin.sh — Stdin normalization layer for Cognitive OS hooks |
| `hooks/_lib/portable.sh` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | portable.sh — Cross-platform shell helpers for macOS (BSD userland, bash 3.2) |
| `hooks/_lib/push-collision-check.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | push-collision-check.sh — ADR-116 P4.2: subject collision detection at push time. |
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
| `hooks/adr-detector.sh` | both | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: architecture, governance, documentation |
| `hooks/agent-quota-redirect.sh` | os-only | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | agent-quota-redirect.sh — PreToolUse:Agent hook (ADR-056 Level 2) |
| `hooks/agent-qwen-bridge.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse:Agent hook — ADR-056 Level 3: transparent Qwen bridge (per-skill opt-in) |
| `hooks/agnix-lint.sh` | os-only | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | agnix-lint.sh — PostToolUse hook on Edit\|Write |
| `hooks/clean-room-ast-similarity-gate.sh` | os-only | os=4; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | clean-room-ast-similarity-gate.sh — ADR-271 Hook #8. |
| `hooks/completeness-check-llm.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Completeness Check (LLM-evaluated, ADR-022) |
| `hooks/confidence-gate-llm.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Confidence Gate (LLM-evaluated, ADR-022) |
| `hooks/context-diet.sh` | both | os=3; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Context Diet — Task-aware rule selection advisory |
| `hooks/conversation-capture.sh` | os-only | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | conversation-capture.sh — Capture session transcript for conversation memory |
| `hooks/engram-auto-import.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Hook: Engram Auto-Import (SessionStart) |
| `hooks/engram-auto-sync.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Hook: Engram Auto-Sync (Stop/SessionEnd) |
| `hooks/idle-service-cleanup.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @manual-trigger: run by cron or operator on demand; not a default Claude event hook |
| `hooks/memu-sync.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | memu-sync.sh — Sync session context to memU proactive memory |
| `hooks/metrics-rotation.sh` | os-only | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | metrics-rotation.sh — Rotate JSONL metrics files to prevent unbounded growth |
| `hooks/mlflow-sync.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `hooks/orchestrator-mode-detect.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @on-demand: sourced library helper — not registered independently, sourced by other hooks |
| `hooks/package-sync.sh` | os-only | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @manual-trigger: CI or developer-triggered; not a Claude event hook default |
| `hooks/pattern-check.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Pattern check — lightweight session-start scan for critical issues. |
| `hooks/rate-limit-protection.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `hooks/registration-check.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | registration-check.sh — PreToolUse hook on Agent (advisory) |
| `hooks/session-end-cleanup.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | session-end-cleanup.sh — runs `cos-cleanup --tier=1 --apply` quietly. |
| `hooks/singularity-check.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SessionStart hook: Quick singularity status check |
| `hooks/state-retention-audit.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | state-retention-audit.sh — ADR-199 retention drift monitor. |
| `hooks/task-recorder.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Stop hook: Record completed task info to task-history.jsonl |
| `hooks/tool-discovery-trigger.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | tool-discovery-trigger.sh — Check if tool discovery scan is due |
| … | … | … | … | … | 294 more rows in JSON report. |

## declared-both-needs-proof-and-metadata (70)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `packages/adaptive-workflow/skills/self-review/SKILL.md` | both | os=0; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: self-review |
| `packages/agent-coordination/skills/retrospective/SKILL.md` | both | os=0; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: retrospective |
| `packages/agent-coordination/skills/squad-manager/SKILL.md` | both | os=0; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: squad-manager |
| `packages/agent-lifecycle/skills/persistent-agent/SKILL.md` | both | os=0; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: persistent-agent |
| `packages/agent-lifecycle/skills/resume-tasks/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: resume-tasks |
| `packages/auto-repair-rollback/skills/auto-rollback/SKILL.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: auto-rollback |
| `packages/context-optimization/skills/compose-prompt/SKILL.md` | both | os=2; generic=2; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: compose-prompt |
| `packages/context-optimization/skills/exhaustive-prompt/SKILL.md` | both | os=0; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: exhaustive-prompt |
| `packages/document-sync/skills/doc-sync/SKILL.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: doc-sync |
| `packages/document-sync/skills/document-feature/SKILL.md` | both | os=2; generic=4; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: document-feature |
| `packages/dry-run-simulation/skills/arena/SKILL.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: arena |
| `packages/dry-run-simulation/skills/simulation-arena/SKILL.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: simulation-arena |
| `packages/ecosystem-tools/skills/audit-website/SKILL.md` | both | os=0; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: audit-website |
| `packages/ecosystem-tools/skills/automaker-bridge/SKILL.md` | both | os=2; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: automaker-bridge |
| `packages/ecosystem-tools/skills/cognee-integration/SKILL.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: cognee-integration |
| `packages/ecosystem-tools/skills/cognee-search/SKILL.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: cognee-search |
| `packages/ecosystem-tools/skills/deepeval-integration/SKILL.md` | both | os=0; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: deepeval-integration |
| `packages/ecosystem-tools/skills/jupyter-execute/SKILL.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: jupyter-execute |
| `packages/ecosystem-tools/skills/promptfoo-integration/SKILL.md` | both | os=0; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: promptfoo-integration |
| `packages/ecosystem-tools/skills/ragas-integration/SKILL.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: ragas-integration |
| `packages/ecosystem-tools/skills/recommend-library/SKILL.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: recommend-library |
| `packages/ecosystem-tools/skills/secret-audit/SKILL.md` | both | os=2; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: secret-audit |
| `packages/ecosystem-tools/skills/semgrep-scan/SKILL.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: semgrep-scan |
| `packages/ecosystem-tools/skills/strands-evals-integration/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: strands-evals-integration |
| `packages/ecosystem-tools/skills/tool-discovery/SKILL.md` | both | os=0; generic=6; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: tool-discovery |
| `packages/ecosystem-tools/skills/web-crawler/SKILL.md` | both | os=0; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: web-crawler |
| `packages/infra-lifecycle/skills/devbox-checkpoint/SKILL.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: devbox-checkpoint |
| `packages/infra-lifecycle/skills/gpu-sandbox/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: gpu-sandbox |
| `packages/infra-lifecycle/skills/repair-status/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: repair-status |
| `packages/infra-lifecycle/skills/sre-agent/SKILL.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: sre-agent |
| `packages/privacy-mode/skills/private-mode/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: private-mode |
| `packages/quality-gates/skills/confidence-check/SKILL.md` | both | os=0; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: confidence-check |
| `packages/quality-gates/skills/dod-check/SKILL.md` | both | os=0; generic=5; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: dod-check |
| `packages/quality-gates/skills/nemo-guardrails/SKILL.md` | both | os=0; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: nemo-guardrails |
| `packages/quality-gates/skills/pentest-self/SKILL.md` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: pentest-self |
| `packages/quality-gates/skills/readiness-check/SKILL.md` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: readiness-check |
| `packages/quality-gates/skills/resolve-blockers/SKILL.md` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: resolve-blockers |
| `packages/quality-gates/skills/security-audit/SKILL.md` | both | os=1; generic=4; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: security-audit |
| `packages/recall-search/skills/conversation-memory/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: conversation-memory |
| `packages/recall-search/skills/memu-context/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: memu-context |
| `packages/recall-search/skills/recall-search/SKILL.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: recall-search |
| `packages/scope-governance/skills/contract-drift/SKILL.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: contract-drift |
| `packages/scope-governance/skills/deep-research/SKILL.md` | both | os=0; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: deep-research |
| `packages/scope-governance/skills/planning-poker/SKILL.md` | both | os=1; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: planning-poker |
| `packages/scope-governance/skills/repo-scout/SKILL.md` | both | os=1; generic=7; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: repo-scout |
| `packages/scope-governance/skills/research-protocol/SKILL.md` | both | os=1; generic=7; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: research-protocol |
| `packages/scope-governance/skills/sandbox-sample/SKILL.md` | both | os=0; generic=4; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: sandbox-sample |
| `packages/sdd-compound/skills/auto-refine/SKILL.md` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: auto-refine |
| `packages/sdd-compound/skills/batch-runner/SKILL.md` | both | os=0; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: batch-runner |
| `packages/sdd-compound/skills/evaluate-plan/SKILL.md` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: evaluate-plan |
| … | … | … | … | … | 20 more rows in JSON report. |

## os-only-semantic-candidate (41)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/_lib/bypass-resolver.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-241 shared bypass resolver. |
| `hooks/_lib/killswitch_check.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | killswitch_check.sh — ADR-028 D5 |
| `hooks/_lib/primitive-intervention.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | primitive-intervention.sh — ADR-256 Phase 2 best-effort runtime evidence ledger |
| `hooks/_lib/safe-worktree-remove.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | safe-worktree-remove.sh — shared helper for safe git worktree removal. |
| `hooks/_lib/validation-lock.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | validation-lock.sh — shared validation capsule lock helpers. |
| `hooks/background-agent-reminder.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | background-agent-reminder.sh — UserPromptSubmit hook |
| `hooks/concurrent-write-guard-codex-proxy.sh` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | concurrent-write-guard-codex-proxy.sh — UserPromptSubmit (prompt) Codex |
| `rules/agent-communication.md` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Communication Bus Protocol |
| `rules/agent-customization.md` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Customization via Override Files (BMAD v6 Pattern 9) |
| `rules/cosd-secure-api.md` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | cosd Secure API |
| `rules/infra-health.md` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Infrastructure Health Check |
| `rules/infra-intent.md` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Infrastructure Intent Detection Rules |
| `rules/orchestrator-prompt-compose.md` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Orchestrator Prompt Compose — Trap Preview Before Agent Launch |
| `scripts/backfill_cost_events.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Backfill cost-events.jsonl to MetricEvent schema (ADR-028 D1.A.1). |
| `scripts/cos-adr-implementation-audit.py` | both | os=4; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-281 — ADR implementation reality audit. |
| `scripts/cos-audit-archive` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Copy old audit rows into compressed archive files without truncating source evidence. |
| `scripts/cos-claims.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | cos-claims.sh — CLI for engram-backed task claims (P5.1 / ADR-116). |
| `scripts/cos-engram-cloud-enroll` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Enroll a project-scoped Engram Cloud sync target without leaking tokens. |
| `scripts/cos-events.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | scope: both |
| `scripts/cos-locks.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | cos-locks.sh — CLI for engram-backed cross-session advisory locks (P5.2 / ADR-116). |
| `scripts/cos-portable-ai-real-consumer-smoke` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Smoke the generated `.ai` overlay against registered consumer shadows. |
| `scripts/cos-root` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PURPOSE: Resolve Cognitive OS project/install roots without requiring a Git checkout. |
| `scripts/cos_claim_signature_audit.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit whether COS product claims are signed by mechanical evidence. |
| `scripts/cos_cross_instance_drill.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Manual drills for cross-instance learning without mutating real evidence. |
| `scripts/cos_demotion_loop_audit.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit whether ADR-126 demotion has become a loop, not a one-off proof. |
| `scripts/cos_doctrine_proposer.py` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Generate proposed doctrine amendments from control-plane evidence. |
| `scripts/cos_governance_roi.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Governance ROI/friction dashboard for Cognitive OS. |
| `scripts/cos_manifest_tier_claim_audit.py` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit primitive lifecycle manifest tier claims for ADR-132/133 portability. |
| `scripts/cos_self_improvement_loop.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Headless propose-only self-improvement loop for Cognitive OS. |
| `scripts/derived_artifact_gate.py` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Gate derived Cognitive OS artifacts before commit or merge. |
| `scripts/lab_first_promotion_gate.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-133 lab-first promotion gate for agentic primitives. |
| `scripts/orphan_commit_scan.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | orphan_commit_scan.py — Scan git reflog for commits now unreachable from any ref. |
| `scripts/portable_ai_real_consumer_smoke.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Smoke the generated `.ai` overlay against registered consumer shadows. |
| `scripts/primitive_fitness_ledger.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Aggregate primitive fitness reports by agentic primitive family. |
| `scripts/runtime_hook_reality.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit projected Claude hooks against lifecycle metadata and observable runtime behavior. |
| `scripts/so-reaper.sh` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | so-reaper.sh — ADR-028 D1.B reaper |
| `scripts/startup-benchmark.sh` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | startup-benchmark.sh — ADR-028 D-stream: session startup latency + payload benchmark |
| `scripts/verify_plan_claims.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Verify high-stakes plan checkbox claims. |
| `skills/cos-status/SKILL.md` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: cos-status |
| `skills/decision-triage/SKILL.md` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: decision-triage |
| `skills/phoenix-trace-ui/SKILL.md` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: phoenix-trace-ui |

