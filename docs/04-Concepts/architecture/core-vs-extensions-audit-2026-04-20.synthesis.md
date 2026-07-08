---
type: concept-synthesis
source: docs/04-Concepts/architecture/core-vs-extensions-audit-2026-04-20.md
status: "FROZEN-BACKLOG P1 MVP deliverable"
provenance: "Manual audit motivated by FROZEN-BACKLOG P1 and debt row D43 to define the v1.0 CORE surface before splitting the bloated core into extension packages."
---

## What it is
Per-file manual classification of every hooks/libs/rules/skills/scripts primitive into CORE (ships in v1.0 core), EXTENSION (moves to a `packages/cos-*` pack), or REMOVE, cross-checked against the default hook set, existing package migrations, ADR-028 SLO deps, RULES-COMPACT triggers, and CATALOG-COMPACT tiers.

## Key mechanics
- Targets vs results: hooks 137 total, target <40 CORE, achieved 38; libs 150 total, target <25, achieved 24; rules 103 total, target <30, achieved 28; skills 127 total, target <20, achieved 20 (at limit); scripts 64 total, no target, 16 CORE.
- Aggregate: 126 CORE of 581 total primitives = 22% core, 78% extension/remove.
- 15 proposed extension packs (`packages/cos-{domain}/`): cos-advisory-llm, cos-security-tools, cos-sdd, cos-agent-coordination, cos-memory-engram, cos-git-safety, cos-infra-lifecycle, cos-claude-code-integration, cos-task-bridge, cos-performance-intelligence, cos-ecosystem-integrations, cos-scope-governance, cos-release-automation, cos-audit-trail.
- CORE hooks (38) include session lifecycle (session-init/resume/end-reap/cleanup/hygiene/sanity/wrapup-trigger), pre-compaction-flush, state-heartbeat, crash-recovery, self-install, registration-check, wiring-check, dispatch-gate, orchestrator-mode-detect, subagent-context-injector, agent-prelaunch/checkpoint/output-verifier, completion-gate, auto-verify, auto-refine, dod-gate, content-policy, secret-detector, destructive-git/rm-blocker, large-file-advisor, result-truncator, context-watchdog, token-budget-monitor, rate-limiter, error-learning/pattern-detector, metrics-rotation, user-prompt-capture, notify, pre-commit-gate (symlinked).
- CORE libs (24): agent_context_injector, agent_permissions, audit_id, budget_calculator, capability_levels, circuit_breaker, config_loader, context_estimator, engram_client, file_lock_registry, manifest_loader, memory, notifications, paths, process_registry, prompt_builder, ref_key_loader, request_queue, return_contract_parser, safe_engram, secret_ref, session_state, smart_reader, wiring_validator.
- CORE rules (28): acceptance-criteria, adaptive-bypass, adversarial-review, agent-audit-before-commit, agent-output-reading, agent-quality, anti-hallucination, assumption-tracking, broken-window-policy, capability-levels, closed-loop-prompts, confidence-gate, content-policy, context-management, credential-management, decomposition, definition-of-done, error-learning, model-routing, model-directive, phase-aware-agents, prompt-quality, responsiveness, result-management, scope-creep-detection, token-economy, trust-score, split-and-resume; plus so-slo.md and hook-security-profiles.md as special-case CORE.
- CORE skills (20): cognitive-os-init, cognitive-os-status, cos-status, session-manager, session-backlog, session-wrapup, add-hook/add-rule/add-skill/add-mcp, evaluate-plan, dod-check, exhaustive-prompt, compose-prompt, generate-config, validate-config, smoke-test, run-tests, plan-bug/plan-feature, CATALOG.md/CATALOG-COMPACT.md.
- REMOVE list: hooks/task-panel-sync.sh (superseded by task-bridge-notify.sh, ADR-024), hooks/_lib/task_panel_adapter.py, packages/_archived/**, ghost skills per `skills/cos-ghost-skills.sh` audit.
- Full 1:1 hook mapping lives in `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` Appendix A.

## Relations & where used
ADR-002 (profile collapse), ADR-028 (SLO catalogue), FROZEN-BACKLOG P1 debt row D43, `scripts/apply-efficiency-profile.sh`, `rules/RULES-COMPACT.md`, `skills/CATALOG-COMPACT.md`.

## Status / caveats
Every primitive classified, zero "unclassified" (acceptance criterion #1 met per doc). Skills surface is "AT LIMIT" (exactly 20 CORE, no headroom for additions without moving one out).
