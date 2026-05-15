# Primitive Scope Unknown Triage

This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.

## Summary

```json
{
  "by_bucket": {
    "insufficient-metadata": 231
  },
  "by_declared_scope": {
    "both": 231
  },
  "by_gap": {
    "missing-consumer-availability-row": 231,
    "missing-lifecycle-row": 231,
    "no-distribution-evidence": 231
  },
  "by_prefix": {
    "hooks": 36,
    "rules": 80,
    "scripts": 115
  },
  "total_unknown": 231
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

## insufficient-metadata (231)

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
| `hooks/agent-qwen-bridge.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse:Agent hook — ADR-056 Level 3: transparent Qwen bridge (per-skill opt-in) |
| `hooks/completeness-check-llm.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Completeness Check (LLM-evaluated, ADR-022) |
| `hooks/confidence-gate-llm.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PostToolUse hook: Confidence Gate (LLM-evaluated, ADR-022) |
| `hooks/context-diet.sh` | both | os=3; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | PreToolUse hook: Context Diet — Task-aware rule selection advisory |
| `hooks/orchestrator-mode-detect.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @on-demand: sourced library helper — not registered independently, sourced by other hooks |
| `hooks/rate-limit-protection.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `hooks/session-end-cleanup.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | session-end-cleanup.sh — runs `cos-cleanup --tier=1 --apply` quietly. |
| `hooks/state-retention-audit.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | state-retention-audit.sh — ADR-199 retention drift monitor. |
| `hooks/task-recorder.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Stop hook: Record completed task info to task-history.jsonl |
| `hooks/tool-loop-detector.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | CONCERNS: safety, quality, observability |
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
| `rules/auto-rollback.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Rollback Planning Protocol |
| … | … | … | … | … | 181 more rows in JSON report. |

