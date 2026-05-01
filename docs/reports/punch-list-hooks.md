# Punch List — hooks bucket

> Generated 2026-05-01 from `.cognitive-os/reports/prune-baseline.json` and `docs/reports/aspirational-audit-2026-05-01.md`.
> Baseline: total=667, ASPIRATIONAL=69, dormant_aspirational_ratio=0.3538.
> Scope: all ASPIRATIONAL hooks detected in the audit run.

| path | dormant signal | recommended action |
|------|---------------|-------------------|
| `hooks/adr-detector.sh` | registered=False, excluded=True, category=FUTURE: detects ADR references in prompts; planned for UserPromptSubmit — not yet wired | WIRE: register in settings.json UserPromptSubmit, or PRUNE if feature is shelved |
| `hooks/agent-bus-monitor.sh` | registered=False, excluded=True, category=CONDITIONAL: monitors Valkey agent bus; only active when ORCHESTRATOR_MODE=executor and Valkey is running | DOCUMENT: add @on-demand marker + condition guard; wire when Valkey enabled |
| `hooks/agent-output-verifier.sh` | registered=False, excluded=True, category=FUTURE: verifies agent output files exist; planned for PostToolUse Agent — not yet wired | WIRE: register in settings.json PostToolUse Agent alongside completion-gate.sh, or PRUNE |
| `hooks/agent-quota-advisor.sh` | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 1 advisory is only enabled when quota-aware dispatch control is turned on | DOCUMENT: add @on-demand marker; wire when quota dispatch enabled |
| `hooks/agent-quota-redirect.sh` | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 2 intentionally remains opt-in because it blocks native Agent launches | DOCUMENT: add @on-demand marker; keep opt-in by design |
| `hooks/agent-qwen-bridge.sh` | registered=False, excluded=True, category=CONDITIONAL: ADR-056 Level 3 is a per-skill transparent bridge, not a global default hook | DOCUMENT: add @on-demand marker; per-skill invocation only |
| `hooks/aguara-scan.sh` | registered=False, excluded=True, category=CONDITIONAL: fires only when AGUARA_ENABLED=true | DOCUMENT: add @on-demand marker with AGUARA_ENABLED guard |
| `hooks/architecture-compliance.sh` | registered=False, excluded=True, category=FUTURE: PostToolUse Edit\|Write — planned but not yet wired | WIRE: register in PostToolUse Edit\|Write, or PRUNE if supplanted by other hooks |
| `hooks/assumption-tracker.sh` | registered=False, excluded=True, category=FUTURE: PreToolUse Agent — ADR-022 variant, not in default profile | WIRE: register in PreToolUse Agent, or PRUNE |
| `hooks/auto-refine.sh` | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.3 — built by UX2 sprint; registration status unverified | WIRE: verify registration; add to settings.json if missing |
| `hooks/auto-verify.sh` | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.1 — built by UX2 sprint but registration not yet verified | WIRE: verify registration; add to settings.json if missing |
| `hooks/background-agent-reminder.sh` | registered=False, excluded=True, category=FUTURE: reminds about background agents; planned for PostToolUse Agent — not yet wired | WIRE: register in PostToolUse Agent, or PRUNE |
| `hooks/code-review-on-commit.sh` | registered=False, excluded=True, category=FUTURE: triggers LLM code review on git commit; uses pre-commit-gate.sh pathway — not yet wired to Claude events | WIRE: register in PreToolUse Bash (git commit pattern), or PRUNE |
| `hooks/completeness-check.sh` | registered=False, excluded=True, category=FUTURE: regex variant superseded by completeness-check-llm.sh | PRUNE: superseded; archive to docs/archive/hooks/ |
| `hooks/concurrent-write-guard.sh` | registered=False, excluded=True, category=FUTURE: prevents concurrent file writes; planned for PreToolUse Edit\|Write — not yet wired | WIRE: register in PreToolUse Edit\|Write, or PRUNE |
| `hooks/context-diet.sh` | registered=False, excluded=True, category=FUTURE: enforces context diet; planned PostToolUse Agent — not yet wired | WIRE: register in PostToolUse Agent, or PRUNE |
| `hooks/contextual-rule-loader.sh` | registered=False, excluded=True, category=FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired | WIRE: register in SubagentStart, or PRUNE |
| `hooks/conversation-capture.sh` | registered=False, excluded=True, category=FUTURE: captures conversation turns; planned for UserPromptSubmit — not yet wired | WIRE: register in UserPromptSubmit, or PRUNE |
| `hooks/destructive-git-blocker.sh` | registered=False, excluded=True, category=FUTURE: blocks destructive git commands; planned for PreToolUse Bash — not yet wired | WIRE: register in PreToolUse Bash, or PRUNE |
| `hooks/dod-gate.sh` | registered=False, excluded=True, category=FUTURE: per rules/ROADMAP.md §2.2 — built by UX2 sprint; registration status unverified | WIRE: verify registration; add to settings.json if missing |
| `hooks/dry-run-preview.sh` | registered=False, excluded=True, category=FUTURE: previews destructive operations in dry-run mode; planned for PreToolUse Bash — not yet wired | WIRE: register in PreToolUse Bash, or PRUNE |
| `hooks/ecosystem-check.sh` | registered=False, excluded=True, category=FUTURE: checks library ecosystem before adoption; planned for PreToolUse Agent — not yet wired | WIRE: register in PreToolUse Agent, or PRUNE |
| `hooks/edit-lock-pre-tool.sh` | registered=False, excluded=False (not in EXCLUDED_HOOKS), fire_count_7d=0 | WIRE or PRUNE: not excluded, not registered — either register in PreToolUse Edit or delete |
| `hooks/engram-auto-import.sh` | registered=False, excluded=True, category=FUTURE: auto-imports engram context; planned for SessionStart or SubagentStart — not yet wired | WIRE: register in SessionStart/SubagentStart, or PRUNE |
| `hooks/engram-auto-sync.sh` | registered=False, excluded=True, category=FUTURE: auto-syncs changes to engram; planned for PostToolUse — not yet wired | WIRE: register in PostToolUse, or PRUNE |
| `hooks/epic-task-detector.sh` | registered=False, excluded=True, category=FUTURE: heuristic detector, not yet wired to any matcher | WIRE: add matcher in settings.json UserPromptSubmit, or PRUNE |
| `hooks/error-learning.sh` | registered=False, excluded=True, category=FUTURE: captures test/lint/build errors; planned PostToolUse Bash alongside error-pipeline.sh | WIRE: register in PostToolUse Bash, or PRUNE |
| `hooks/global-verify.sh` | registered=False, excluded=True, category=CONDITIONAL: registered at apply-efficiency-profile.sh:365 (PreToolUse Agent) and line 370 (PostToolUse Agent) | DOCUMENT: audit apply-efficiency-profile.sh lines 365+370; confirm profile activation wires it correctly |
| `hooks/guardrails-validator.sh` | registered=False, excluded=True, category=CONDITIONAL: NeMo Guardrails integration, fires via /guardrails skill | DOCUMENT: add @on-demand marker; fired by skill, not a global hook |
| `hooks/idle-service-cleanup.sh` | registered=False, excluded=True, category=CONDITIONAL: cleans up idle Docker services; run by cron or manually | DOCUMENT: add @on-demand marker + @manual-trigger |
| `hooks/jupyter-sandbox.sh` | registered=False, excluded=True, category=FUTURE: sandboxes Jupyter tool calls; planned for PreToolUse Jupyter — not yet wired | WIRE: register in PreToolUse Jupyter, or PRUNE |
| `hooks/large-file-advisor.sh` | registered=False, excluded=True, category=FUTURE: advises on large file reads; planned PreToolUse Read — not yet wired | WIRE: register in PreToolUse Read, or PRUNE |
| `hooks/memu-sync.sh` | registered=False, excluded=True, category=FUTURE: syncs memu state; planned for Stop or PostToolUse — not yet wired | WIRE: register in Stop event, or PRUNE |
| `hooks/metrics-calibrator-trigger.sh` | registered=False, excluded=True, category=FUTURE: triggers metrics-calibrator skill; planned for Stop event — not yet wired | WIRE: register in Stop event, or PRUNE |
| `hooks/mlflow-sync.sh` | registered=False, excluded=True, category=CONDITIONAL: syncs metrics to MLflow at session end; only active when mlflow package is installed | DOCUMENT: add @on-demand marker with mlflow guard |
| `hooks/orchestrator-mode-detect.sh` | registered=False, excluded=True, category=CONDITIONAL: sourced by other hooks, not registered independently | DOCUMENT: add @on-demand marker; it is a sourced library, not a standalone hook |
| `hooks/package-sync.sh` | registered=False, excluded=True, category=CONDITIONAL: triggered by CI or developer, not by Claude hooks | DOCUMENT: add @on-demand/@manual-trigger marker |
| `hooks/paperclip-sync.sh` | registered=False, excluded=True, category=CONDITIONAL: syncs to Paperclip; only active when Paperclip service is running | DOCUMENT: add @on-demand marker with Paperclip guard |
| `hooks/parry-scan.sh` | registered=False, excluded=True, category=CONDITIONAL: Parry security integration | DOCUMENT: add @on-demand marker with Parry guard |
| `hooks/pattern-check.sh` | registered=False, excluded=True, category=FUTURE: checks for known anti-patterns; planned for PreToolUse Edit\|Write — not yet wired | WIRE: register in PreToolUse Edit\|Write, or PRUNE |
| `hooks/post-agent-verify.sh` | registered=False, excluded=True, category=FUTURE: superseded by completion-gate.sh | PRUNE: superseded; archive to docs/archive/hooks/ |
| `hooks/pre-agent-snapshot.sh` | registered=False, excluded=True, category=FUTURE: snapshot before agent launch; planned for PreToolUse Agent — not yet wired | WIRE: register in PreToolUse Agent, or PRUNE |
| `hooks/pre-cleanup-snapshot.sh` | registered=False, excluded=True, category=FUTURE: snapshot before cleanup operations; invoked manually or by admin scripts | DOCUMENT: add @on-demand/@manual-trigger marker |
| `hooks/private-mode-gate.sh` | registered=False, excluded=True, category=FUTURE: gates operations in private mode; planned for PreToolUse — not yet wired | WIRE: register in PreToolUse, or PRUNE |
| `hooks/private-mode-metrics-gate.sh` | registered=False, excluded=True, category=FUTURE: gates metrics emission in private mode; planned for PostToolUse — not yet wired | WIRE: register in PostToolUse, or PRUNE |
| `hooks/prompt-quality.sh` | registered=False, excluded=True, category=FUTURE: regex variant superseded by prompt-quality-llm.sh | PRUNE: superseded; archive to docs/archive/hooks/ |
| `hooks/recap-sync.sh` | registered=False, excluded=True, category=FUTURE: syncs session recap; planned for Stop event — not yet wired | WIRE: register in Stop event, or PRUNE |
| `hooks/release-guard.sh` | registered=False, excluded=True, category=FUTURE: guards release operations; planned for PreToolUse Bash — not yet wired | WIRE: register in PreToolUse Bash, or PRUNE |
| `hooks/scope-creep-detector.sh` | registered=False, excluded=True, category=FUTURE: PostToolUse Agent, planned but not wired | WIRE: register in PostToolUse Agent, or PRUNE |
| `hooks/scope-proportionality.sh` | registered=False, excluded=True, category=FUTURE: PostToolUse Agent, planned | WIRE: register in PostToolUse Agent, or PRUNE |
| `hooks/semgrep-scan.sh` | registered=False, excluded=True, category=CONDITIONAL: fires via /semgrep-scan skill | DOCUMENT: add @on-demand marker; fired by skill, not a global hook |
| `hooks/session-end-reap.sh` | registered=False, excluded=True, category=FUTURE: reaps stale session artefacts at Stop; ADR-028 Phase B — not yet wired | WIRE: register in Stop event per ADR-028, or PRUNE |
| `hooks/session-knowledge-extractor.sh` | registered=False, excluded=True, category=FUTURE: extracts learnings at session end; planned for Stop event — not yet wired | WIRE: register in Stop event, or PRUNE |
| `hooks/skill-tracker.sh` | registered=False, excluded=True, category=FUTURE: tracks skill invocations; planned for PostToolUse Agent — not yet wired | WIRE: register in PostToolUse Agent, or PRUNE |
| `hooks/token-budget-monitor.sh` | registered=False, excluded=True, category=FUTURE: monitors token budget mid-session; planned for PostToolUse — not yet wired | WIRE: register in PostToolUse, or PRUNE |
| `hooks/tool-discovery-trigger.sh` | registered=False, excluded=True, category=FUTURE: triggers dynamic tool discovery; planned for PostToolUse Agent — not yet wired | WIRE: register in PostToolUse Agent, or PRUNE |
| `hooks/tool-loop-detector.sh` | registered=False, excluded=True, category=FUTURE: detects infinite tool-call loops; planned for PreToolUse — not yet wired | WIRE: register in PreToolUse, or PRUNE |
| `hooks/valkey-ensure.sh` | registered=False, excluded=True, category=CONDITIONAL: starts Valkey on demand; invoked by agent-bus-monitor.sh or manually | DOCUMENT: add @on-demand marker with Valkey guard |
| `hooks/worktree-submodule-fix.sh` | registered=False, excluded=True, category=CONDITIONAL: fixes git submodule state in worktrees; invoked manually after worktree operations | DOCUMENT: add @on-demand/@manual-trigger marker |

## Action Summary

| action | count |
|--------|-------|
| WIRE (register in settings.json) | 32 |
| DOCUMENT (add @on-demand marker) | 14 |
| PRUNE (archive — superseded) | 3 |

Candidates for immediate pruning (clearly superseded):
- `hooks/completeness-check.sh` — superseded by `completeness-check-llm.sh`
- `hooks/post-agent-verify.sh` — superseded by `completion-gate.sh`
- `hooks/prompt-quality.sh` — superseded by `prompt-quality-llm.sh`
