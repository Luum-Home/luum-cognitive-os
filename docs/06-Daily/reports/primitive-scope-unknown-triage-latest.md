# Primitive Scope Unknown Triage

This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.

## Summary

```json
{
  "by_bucket": {
    "declared-both-needs-proof-and-metadata": 364,
    "declared-both-os-internal-heavy": 81,
    "insufficient-metadata": 65
  },
  "by_declared_scope": {
    "both": 445,
    "os-only": 65
  },
  "by_gap": {
    "declared-both-missing-paired-proof": 445,
    "missing-consumer-availability-row": 510,
    "missing-lifecycle-row": 510,
    "no-distribution-evidence": 510
  },
  "by_prefix": {
    "hooks": 65,
    "packages": 73,
    "rules": 115,
    "scripts": 146,
    "skills": 90,
    "templates": 21
  },
  "total_unknown": 510
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

## declared-both-needs-proof-and-metadata (364)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/_lib/artifact-status.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Shared artifact status loaders for governance hooks. |
| `hooks/_lib/cache.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | cache.sh — SHA-256 file cache for hook scans |
| `hooks/_lib/circuit-breaker.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | circuit-breaker.sh — Per-error-type circuit breaker for auto-repair |
| `hooks/_lib/common.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | common.sh — Shared utility functions for Cognitive OS hooks |
| `hooks/_lib/context_budget_lib.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Shared ADR-186 context-budget accountant for hooks that emit additionalContext. |
| `hooks/_lib/execute-repair.sh` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | execute-repair.sh — Core execution engine for auto-repair system |
| `hooks/_lib/file_checker.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Symlink-aware file existence checker. |
| `hooks/_lib/hook-pipe.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | hook-pipe.sh — Inter-hook data sharing within an event chain |
| `hooks/_lib/normalize-stdin.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | normalize-stdin.sh — Stdin normalization layer for Cognitive OS hooks |
| `hooks/_lib/portable.sh` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | portable.sh — Cross-platform shell helpers for macOS (BSD userland, bash 3.2) |
| `hooks/_lib/push-collision-check.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | push-collision-check.sh — ADR-116 P4.2: subject collision detection at push time. |
| `hooks/_lib/register-bg.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | register-bg.sh — ADR-028 D1.B  Process Registry helper |
| `hooks/_lib/remediation.sh` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | remediation.sh — Shared library for remediation registry operations |
| `hooks/_lib/resolve-main-worktree.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | resolve-main-worktree.sh — Shared library: resolve the main worktree path. |
| `hooks/_lib/safe-jsonl.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | safe-jsonl.sh — Shared library for safe JSONL writes + hook health heartbeats |
| `hooks/_lib/semantic-search.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | semantic-search.sh — Fuzzy error matching via vector similarity |
| `hooks/_lib/session-fs-reap.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Archive-first filesystem reaper for .cognitive-os/sessions. |
| `hooks/_lib/session_init_helper.py` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Consolidated helper for session-init.sh. |
| `hooks/_lib/singularity-suggestion.sh` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | _singularity_suggestion — Advisory singularity run suggestion. |
| `hooks/_lib/stash-lock.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | stash-lock.sh — Flock coordinator library for git stash operations. |
| `hooks/_lib/task-identity.sh` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Resolve one canonical task id for cross-session claim coordination. |
| `hooks/_lib/task_bridge.py` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Task Bridge — correlates COS task_id with Claude Code tool_use_id. |
| `hooks/_lib/timing.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | timing.sh — Hook timing wrapper for Cognitive OS performance monitoring |
| `hooks/_lib/tuning.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | tuning.sh — Shared helper for hooks with tunable thresholds. |
| `hooks/agent-qwen-bridge.sh` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PreToolUse:Agent hook — ADR-056 Level 3: transparent Qwen bridge (per-skill opt-in) |
| `hooks/completeness-check-llm.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PreToolUse hook: Completeness Check (LLM-evaluated, ADR-022) |
| `hooks/confidence-gate-llm.sh` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PostToolUse hook: Confidence Gate (LLM-evaluated, ADR-022) |
| `hooks/context-diet.sh` | both | os=3; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PreToolUse hook: Context Diet — Task-aware rule selection advisory |
| `hooks/orchestrator-mode-detect.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | @on-demand: sourced library helper — not registered independently, sourced by other hooks |
| `hooks/rate-limit-protection.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `hooks/session-end-cleanup.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | session-end-cleanup.sh — runs `cos-cleanup --tier=1 --apply` quietly. |
| `hooks/state-retention-audit.sh` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | state-retention-audit.sh — ADR-199 retention drift monitor. |
| `hooks/tool-loop-detector.sh` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | CONCERNS: safety, quality, observability |
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
| … | … | … | … | … | 314 more rows in JSON report. |

## declared-both-os-internal-heavy (81)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/_lib/bypass-resolver.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | ADR-241 shared bypass resolver. |
| `hooks/_lib/dispatch_gate_check.py` | both | os=2; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Single-pass dispatch gate check — consolidates all python3 invocations from dispatch-gate.sh. |
| `hooks/_lib/killswitch_check.sh` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | killswitch_check.sh — ADR-028 D5 |
| `hooks/_lib/primitive-intervention.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | primitive-intervention.sh — ADR-256 Phase 2 best-effort runtime evidence ledger |
| `hooks/_lib/recap_adapter.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Recap Adapter — exposes COS session state to Claude Code's native /recap UI. |
| `hooks/_lib/safe-worktree-remove.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | safe-worktree-remove.sh — shared helper for safe git worktree removal. |
| `hooks/_lib/task_panel_adapter.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Task Panel Adapter — mirrors COS task state to Claude Code's native UI. |
| `hooks/_lib/validation-lock.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | validation-lock.sh — shared validation capsule lock helpers. |
| `hooks/adr-detector.sh` | both | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | CONCERNS: architecture, governance, documentation |
| `hooks/agent-bus-monitor.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Hook: agent-bus-monitor (SessionStart) |
| `hooks/agent-quota-advisor.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PreToolUse:Agent hook — Adaptive dispatch quota advisor (ADR-056 L1). |
| `hooks/background-agent-reminder.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | background-agent-reminder.sh — UserPromptSubmit hook |
| `hooks/concurrent-write-guard-codex-proxy.sh` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | concurrent-write-guard-codex-proxy.sh — UserPromptSubmit (prompt) Codex |
| `hooks/contextual-rule-loader.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | contextual-rule-loader.sh — PreToolUse hook on Agent |
| `hooks/notify.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PostToolUse hook: Send notifications for SDD phase completions |
| `hooks/task-panel-sync.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Task Panel Sync — exposes COS task state to Claude Code's native UI. |
| `hooks/task-recorder.sh` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Stop hook: Record completed task info to task-history.jsonl |
| `packages/skill-governance/skills/self-improve/SKILL.md` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | name: self-improve |
| `rules/agent-communication.md` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Agent Communication Bus Protocol |
| `rules/agent-customization.md` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Agent Customization via Override Files (BMAD v6 Pattern 9) |
| `rules/cosd-secure-api.md` | both | os=4; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | cosd Secure API |
| `rules/engram-api-safety.md` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Engram API Safety — Never Mutate Production Daemon for Discovery |
| `rules/infra-health.md` | both | os=3; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Infrastructure Health Check |
| `rules/infra-intent.md` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Infrastructure Intent Detection Rules |
| `rules/orchestrator-prompt-compose.md` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Orchestrator Prompt Compose — Trap Preview Before Agent Launch |
| `rules/queue-advisor.md` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Queue Advisor — Dynamic Dispatch Prioritization |
| `rules/rate-limiting.md` | both | os=4; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Rate Limiting Protocol |
| `rules/skill-invocation-mandatory.md` | both | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Skill Invocation Mandatory at High Router Confidence (ADR-188) |
| `rules/startup-protocol.md` | both | os=5; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Session Startup Protocol |
| `scripts/backfill_cost_events.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Backfill cost-events.jsonl to MetricEvent schema (ADR-028 D1.A.1). |
| `scripts/compose_agent_prompt.py` | both | os=4; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | @on-demand: pipe agent prompt draft through before Agent calls touching settings.json/lib/*.py (ADR-032 orchestrator-prompt-compose) |
| `scripts/cos-adr-implementation-audit.py` | both | os=4; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | ADR-281 — ADR implementation reality audit. |
| `scripts/cos-audit-archive` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PURPOSE: Copy old audit rows into compressed archive files without truncating source evidence. |
| `scripts/cos-claims.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | cos-claims.sh — CLI for engram-backed task claims (P5.1 / ADR-116). |
| `scripts/cos-doctor-concurrency.sh` | both | os=4; generic=2; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | @manual-trigger: diagnostic tool; invoke manually to inspect concurrent-agent safety primitive state |
| `scripts/cos-doctor-preserve.sh` | both | os=4; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Read-only doctor for codex/preserve-* branch governance (ADR-110). |
| `scripts/cos-engram-cloud-enroll` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PURPOSE: Enroll a project-scoped Engram Cloud sync target without leaking tokens. |
| `scripts/cos-events.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | scope: both |
| `scripts/cos-locks.sh` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | cos-locks.sh — CLI for engram-backed cross-session advisory locks (P5.2 / ADR-116). |
| `scripts/cos-opencode-primitive-adapter-smoke` | both | os=5; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Smoke the native OpenCode COS primitive guard plugin without model calls. |
| `scripts/cos-portable-ai-consumer-smoke` | both | os=2; generic=0; project=2 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Smoke generated `.ai` overlay projection into a disposable consumer project. |
| `scripts/cos-portable-ai-real-consumer-smoke` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Smoke the generated `.ai` overlay against registered consumer shadows. |
| `scripts/cos-root` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | PURPOSE: Resolve Cognitive OS project/install roots without requiring a Git checkout. |
| `scripts/cos-tui` | both | os=2; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Operable terminal surface for Cognitive OS primitive coverage reports. |
| `scripts/cos-validation-capsule.sh` | both | os=3; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | cos-validation-capsule.sh — run validation in an isolated git worktree. |
| `scripts/cos_claim_signature_audit.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Audit whether COS product claims are signed by mechanical evidence. |
| `scripts/cos_coverage.py` | both | os=3; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | cos-coverage — Agent Capability Coverage (ACC) metric CLI. |
| `scripts/cos_cross_instance_drill.py` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Manual drills for cross-instance learning without mutating real evidence. |
| `scripts/cos_demotion_loop_audit.py` | both | os=2; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Audit whether ADR-126 demotion has become a loop, not a one-off proof. |
| `scripts/cos_doctrine_proposer.py` | both | os=3; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row, declared-both-missing-paired-proof |  | Generate proposed doctrine amendments from control-plane evidence. |
| … | … | … | … | … | 31 more rows in JSON report. |

## insufficient-metadata (65)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `hooks/agent-quota-redirect.sh` | os-only | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | agent-quota-redirect.sh — PreToolUse:Agent hook (ADR-056 Level 2) |
| `hooks/agnix-lint.sh` | os-only | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | agnix-lint.sh — PostToolUse hook on Edit\|Write |
| `hooks/clean-room-ast-similarity-gate.sh` | os-only | os=4; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | clean-room-ast-similarity-gate.sh — ADR-271 Hook #8. |
| `hooks/conversation-capture.sh` | os-only | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | conversation-capture.sh — Capture session transcript for conversation memory |
| `hooks/engram-auto-import.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Hook: Engram Auto-Import (SessionStart) |
| `hooks/engram-auto-sync.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Hook: Engram Auto-Sync (Stop/SessionEnd) |
| `hooks/idle-service-cleanup.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @manual-trigger: run by cron or operator on demand; not a default Claude event hook |
| `hooks/memu-sync.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | memu-sync.sh — Sync session context to memU proactive memory |
| `hooks/metrics-rotation.sh` | os-only | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | metrics-rotation.sh — Rotate JSONL metrics files to prevent unbounded growth |
| `hooks/mlflow-sync.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set. |
| `hooks/package-sync.sh` | os-only | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | @manual-trigger: CI or developer-triggered; not a Claude event hook default |
| `hooks/pattern-check.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Pattern check — lightweight session-start scan for critical issues. |
| `hooks/registration-check.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | registration-check.sh — PreToolUse hook on Agent (advisory) |
| `hooks/singularity-check.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | SessionStart hook: Quick singularity status check |
| `hooks/tool-discovery-trigger.sh` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | tool-discovery-trigger.sh — Check if tool discovery scan is due |
| `packages/verification-audit/skills/cognitive-os-benchmark/SKILL.md` | os-only | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: cognitive-os-benchmark |
| `packages/verification-audit/skills/harness-audit/SKILL.md` | os-only | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: harness-audit |
| `rules/capability-protection.md` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Capability Protection |
| `rules/clean-room-detection-limits.md` | os-only | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: clean-room-detection-limits |
| `rules/cross-harness-authoring.md` | os-only | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Cross-Harness Authoring |
| `rules/lane-taxonomy.md` | os-only | os=3; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Test Lane Taxonomy |
| `rules/pre-dev-readiness-gate.md` | os-only | os=1; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Pre-Development Readiness Gate |
| `rules/reinvention-prevention.md` | os-only | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Reinvention Prevention |
| `skills/__contracts__/SKILL.md` | os-only | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: __contracts__ |
| `skills/__contracts__/canonical-event-emitter/SKILL.md` | os-only | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: canonical-event-emitter |
| `skills/adr-tombstone/SKILL.md` | os-only | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: adr-tombstone |
| `skills/architecture-map-answer/SKILL.md` | os-only | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: architecture-map-answer |
| `skills/audit-integrity/SKILL.md` | os-only | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: audit-integrity |
| `skills/browser-task/SKILL.md` | os-only | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: browser-task |
| `skills/bump-version/SKILL.md` | os-only | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: bump-version |
| `skills/cognitive-os-init/SKILL.md` | os-only | os=2; generic=2; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: cognitive-os-init |
| `skills/cognitive-os-status/SKILL.md` | os-only | os=2; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: cognitive-os-status |
| `skills/cognitive-os-test/SKILL.md` | os-only | os=2; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: cognitive-os-test |
| `skills/component-reality-check/SKILL.md` | os-only | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: component-reality-check |
| `skills/coordination-status/SKILL.md` | os-only | os=3; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: coordination-status |
| `skills/cos-maintainer-operations/SKILL.md` | os-only | os=1; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: cos-maintainer-operations |
| `skills/deps-update/SKILL.md` | os-only | os=1; generic=3; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: deps-update |
| `skills/docs-execution-audit/SKILL.md` | os-only | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: docs-execution-audit |
| `skills/dogfood-score/SKILL.md` | os-only | os=3; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: dogfood-score |
| `skills/experimental/SKILL.md` | os-only | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: experimental |
| `skills/experimental/auto-bash-agent-bash-9c6b89/SKILL.md` | os-only | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: auto-bash-agent-bash-9c6b89 |
| `skills/generate-changelog/SKILL.md` | os-only | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: generate-changelog |
| `skills/memory-scan/SKILL.md` | os-only | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: memory-scan |
| `skills/pattern-audit/SKILL.md` | os-only | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: pattern-audit |
| `skills/primitive-surface-reduction/SKILL.md` | os-only | os=1; generic=1; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: primitive-surface-reduction |
| `skills/primitive-usage-map/SKILL.md` | os-only | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: primitive-usage-map |
| `skills/product-answer/SKILL.md` | os-only | os=4; generic=4; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: product-answer |
| `skills/push-release/SKILL.md` | os-only | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: push-release |
| `skills/radar-update/SKILL.md` | os-only | os=3; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: radar-update |
| `skills/release-os/SKILL.md` | os-only | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | name: release-os |
| … | … | … | … | … | 15 more rows in JSON report. |

