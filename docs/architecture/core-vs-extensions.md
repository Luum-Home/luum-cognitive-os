# Core vs Extensions — Design Criteria

> **Status:** ACTIVE design reference for Phase 3 of `so-existential-validation`.
> **Source audit:** `docs/architecture/core-vs-extensions-audit-2026-04-20.md` (126 CORE / 581 total).
> **Migration plan:** `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md`.
> **Last updated:** 2026-05-02 (distilled from 2026-04-20 audit; no new classifications made here).

---

## Purpose

This document defines the stable criteria for classifying every OS primitive (hook, lib, rule, skill, script) as CORE or EXTENSION. It exists so future contributors and agents can apply the classification consistently without re-reading the full audit.

---

## Classification Criteria

### CORE — all conditions must hold

1. **Zero external service dependencies.** No Docker, Valkey, MLflow, Langfuse, Aguara, Parry, NeMo, Paperclip, cognee, e2b, tero, repomix, hcom, or any API credential beyond the base Claude/Anthropic key.
2. **Required for `cos init` or session-start to succeed.** Removing it would break the bootstrapped state invariant or the crash-recovery path.
3. **Called by ≥3 CORE hooks OR underpins the scale-adaptive bypass rule.** Single-purpose primitives that serve only one optional workflow belong in an extension pack.
4. **No harness-specific integration.** Code that only works with Claude Code (not portable to other harnesses) → EXTENSION unless it is the harness adapter itself.
5. **No methodology-specific scope.** SDD, multi-agent coordination, release automation — all optional methodologies → their own extension packs.

### EXTENSION — any condition sufficient

- Requires an external service or API credential beyond base Claude key
- Conditional on an environment variable flag (`AGUARA_ENABLED`, `LANGFUSE_HOST`, etc.)
- Serves a single integration (per-tool hooks: semgrep, parry, aguara, cognee, e2b, etc.)
- Implements an optional methodology (SDD, simulation arena, planning poker, MAPE-K, etc.)
- Classified ASPIRATIONAL in Phase 1 triage (no observable production invocations AND no explicit future marker)
- Explicitly a compliance / governance add-on not universally needed (audit-trail, scope-governance, release-automation)

---

## Counts per surface (2026-04-20 baseline)

| Surface | CORE | EXTENSION | Total | CORE target |
|---|---:|---:|---:|---|
| Hooks (`hooks/*.sh`) | 38 | 97 | 135 | <40 (met) |
| Libs (`lib/*.py`) | 24 | 126 | 150 | <25 (met) |
| Rules (`rules/*.md`) | 28 | 75 | 103 | <30 (met) |
| Skills (`skills/*/`) | 20 | 107 | 127 | ≤20 (at limit) |
| Scripts (`scripts/*`) | 16 | 48 | 64 | no target |
| **Total** | **126** | **453** | **581** | **22% CORE** |

---

## Extension pack taxonomy (15 packs)

| Pack | `packages/` name | Primary surface | Opt-in signal |
|---|---|---|---|
| Advisory LLM evaluators | `cos-advisory-llm` | `*-llm.sh` hooks, `advisor_*.py` | Anthropic/OpenAI API creds present |
| Observability | `cos-observability` | mlflow, langfuse, paperclip hooks+libs | `LANGFUSE_HOST` or `MLFLOW_TRACKING_URI` |
| Security tools | `cos-security-tools` | aguara, semgrep, parry, mcp-scan | External security CLIs installed |
| Spec-Driven Development | `cos-sdd` | sdd-* skills, sdd_*.py libs, SDD rules | Operator opt-in |
| Agent coordination | `cos-agent-coordination` | agent-bus, squad, arena, planning-poker | Multi-agent workflows |
| Memory / Engram backends | `cos-memory-engram` | engram-auto-sync/import, memu, cognee | External memory backend in use |
| Git safety | `cos-git-safety` | code-review-on-commit, adr-detector, release-guard | Commit-time policies desired |
| Infra lifecycle | `cos-infra-lifecycle` | infra-health, idle-service-cleanup, valkey-ensure | Docker services present |
| Claude Code integration | `cos-claude-code-integration` | recap-sync, claude_executor, claude_usage_reader | Claude Code harness only |
| Task bridge | `cos-task-bridge` | task-bridge-notify, task-recorder, task_bridge lib | External task system |
| Performance intelligence | `cos-performance-intelligence` | kpi, calibration, singularity, MAPE-K | Meta-learning loops desired |
| Ecosystem integrations | `cos-ecosystem-integrations` | e2b, tero, repomix, hcom, context7, trailofbits, nemo, deepeval, opik, ragas, strands | Per-tool |
| Scope governance | `cos-scope-governance` | scope-creep, blast-radius LARGE mode | Large-org compliance |
| Release automation | `cos-release-automation` | release-guard, tag-release, bump-version | Release engineering |
| Audit trail | `cos-audit-trail` | git-context-capture, session-changelog, audit-id-enricher | Compliance-heavy projects |

---

## CORE hook list (38)

Full 1:1 list from 2026-04-20 audit. These stay in `hooks/` root:

`session-init.sh`, `session-resume.sh`, `session-end-reap.sh`, `session-cleanup.sh`, `session-hygiene.sh`, `session-sanity.sh`, `session-wrapup-trigger.sh`, `pre-compaction-flush.sh`, `state-heartbeat.sh`, `crash-recovery.sh`, `self-install.sh`, `registration-check.sh`, `wiring-check.sh`, `dispatch-gate.sh`, `orchestrator-mode-detect.sh`, `subagent-context-injector.sh`, `agent-prelaunch.sh`, `agent-checkpoint.sh`, `agent-output-verifier.sh`, `completion-gate.sh`, `auto-verify.sh`, `auto-refine.sh`, `dod-gate.sh`, `content-policy.sh`, `secret-detector.sh`, `destructive-git-blocker.sh`, `destructive-rm-blocker.sh`, `large-file-advisor.sh`, `result-truncator.sh`, `context-watchdog.sh`, `token-budget-monitor.sh`, `rate-limiter.sh`, `error-learning.sh`, `error-pattern-detector.sh`, `metrics-rotation.sh`, `user-prompt-capture.sh`, `notify.sh`, `pre-commit-gate.sh` (symlink to `.githooks/pre-commit`).

---

## CORE skill list (20)

`cognitive-os-init`, `cognitive-os-status`, `cos-status`, `session-manager`, `session-backlog`, `session-wrapup`, `add-hook`, `add-rule`, `add-skill`, `add-mcp`, `evaluate-plan`, `dod-check`, `exhaustive-prompt`, `compose-prompt`, `generate-config`, `validate-config`, `smoke-test`, `run-tests`, `plan-bug`, `plan-feature`.

---

## Migration sequencing

See `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` for:
- One-pack-per-wave rule
- Backward-compat symlink protocol (N+1 shim, N+2 removal)
- `cognitive-os.yaml extensions:` key schema
- `cos-package.yaml hook_registrations:` schema for extension packs

Default install enables: `cos-advisory-llm` (if API creds present), `cos-git-safety`, `cos-security-tools` (advisory only), `cos-observability` (if Langfuse/MLflow detected). All other packs explicit opt-in.

---

## Governance

- A primitive MUST NOT be promoted from EXTENSION to CORE unless it meets all 5 CORE criteria above AND the operator approves via ADR or plan update.
- New primitives default to EXTENSION until proven CORE by usage data (≥3 REAL invocations across ≥3 sessions).
- The CORE counts are hard targets: hooks <40, libs <25, rules <30, skills ≤20. Adding to CORE requires removing one or reclassifying one.
