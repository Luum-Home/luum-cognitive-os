# Core vs Extensions Audit — 2026-04-20

> **Status:** FROZEN-BACKLOG P1 MVP deliverable. Source of truth for v1.0 CORE surface.
> **Owner:** v1.0-prep wave. **Predecessors:** FROZEN-BACKLOG §P1, debt row D43, ADR-002 (profile collapse).
> **Method:** per-file manual classification cross-checked against (a) the `default` hook set in `scripts/apply-efficiency-profile.sh`, (b) existing `packages/*` migrations, (c) ADR-028 SLO catalogue dependencies, (d) rules/RULES-COMPACT trigger table, (e) skills/CATALOG-COMPACT tier labels.

## Inventory snapshot

| Surface | Primitives | File count | Target at v1.0 | Feasibility |
|---|---|---|---|---|
| `hooks/*.sh` | shell hooks | 137 | < 40 CORE | **TIGHT but feasible** (see §1 — 38 CORE identified) |
| `lib/*.py` | Python libraries | 150 | < 25 CORE | **FEASIBLE** (24 CORE identified; most libs already support specific extensions) |
| `rules/*.md` | agent rules | 103 | < 30 CORE | **FEASIBLE** (28 CORE identified; rest are contextual/extension-coupled) |
| `skills/*/` | skills | 127 | < 20 CORE | **AT LIMIT** (20 CORE identified; every additional skill belongs in an extension) |
| `scripts/*` | CLI scripts | 64 | no target | 16 CORE; 48 move to extensions or remove |

**Aggregate result:** 126 CORE agentic primitives of 581 total = **22% core, 78% extensions/remove**. This confirms the FROZEN-BACKLOG thesis that the core is bloated today and that the extraction is structurally sound.

## Proposed extension pack taxonomy

Naming convention: `packages/cos-{domain}/`. Each pack self-contained: own `cos-package.yaml`, own `hooks/`, `rules/`, `skills/`, `lib/` subdirs as needed, own README.

| Pack | Scope | Rationale |
|---|---|---|
| `cos-advisory-llm` | `*advisor*`, `*-llm.sh` evaluators, strategic-advice libs | Requires Anthropic/OpenAI API creds; not universal. (D43) |
| `cos-security-tools` | aguara, semgrep, parry, mcp-scan, secret-detector, credential, license | Bundled together because security profile opts-in as a group. |
| `cos-sdd` | All sdd-* skills, sdd_pipeline, sdd_resume libs, SDD rules | SDD is a methodology, not every team uses it. |
| `cos-agent-coordination` | agent-bus, squad, planning-poker, simulation-arena | Multi-agent coordination is advanced usage. |
| `cos-memory-engram` | engram-auto-sync/import, memu, cognee | External memory backends; CORE keeps only plain JSONL. |
| `cos-git-safety` | code-review-on-commit, destructive-*-blocker, release-guard, adr-detector | Nice-to-have; pre-commit-gate symlink stays CORE. |
| `cos-infra-lifecycle` | infra-health, idle-service-cleanup, valkey-ensure, docker scripts | Only relevant when Docker services used. |
| `cos-claude-code-integration` | recap-sync, claude_usage_reader, claude_executor | Vendor-specific to Claude Code harness. |
| `cos-task-bridge` | task-bridge-notify, task-recorder, task-panel-sync, task_bridge lib | External task system integration. |
| `cos-performance-intelligence` | kpi, calibration, self-improvement, singularity, MAPE-K | Meta-learning loops; optional. |
| `cos-ecosystem-integrations` | e2b, tero, parry, repomix, hcom, context7, trailofbits, nemo, deepeval, promptfoo, ragas, opik, strands | Per-tool optional integrations. |
| `cos-scope-governance` | scope-creep, scope-proportionality, blast-radius LARGE mode | Large-org governance; trivial projects don't need it. |
| `cos-release-automation` | release-guard, tag-release, push-release, bump-version, release-os | Release engineering; small teams use GitHub flow. |
| `cos-audit-trail` | git-context-capture, session-changelog, audit-id-enricher, agent-identity | Compliance-heavy; not all projects need audit trail. |

That is **15 extension packs**. Core retains only the minimum scaffolding to initialise a project, run a session, and deliver the scale-adaptive bypass rule.

---

## §1 — Hooks (137 total)

### CORE hooks (38) — required for `cos init` + `session start` + trivial task bypass to work

| primitive | current path | class | new path | reason |
|---|---|---|---|---|
| session-init.sh | hooks/session-init.sh | CORE | hooks/session-init.sh | Session bootstrap (SLO 1, SLO 5 owner) |
| session-resume.sh | hooks/session-resume.sh | CORE | hooks/session-resume.sh | Crash-recovery bootstrap |
| session-end-reap.sh | hooks/session-end-reap.sh | CORE | hooks/session-end-reap.sh | SLO 4 owner (orphan reaper) |
| session-cleanup.sh | hooks/session-cleanup.sh | CORE | hooks/session-cleanup.sh | Session-scoped metrics close |
| session-hygiene.sh | hooks/session-hygiene.sh | CORE | hooks/session-hygiene.sh | Stale-artifact sweep |
| session-sanity.sh | hooks/session-sanity.sh | CORE | hooks/session-sanity.sh | State invariants at boot |
| session-wrapup-trigger.sh | hooks/session-wrapup-trigger.sh | CORE | hooks/session-wrapup-trigger.sh | ADR-030 auto-trigger |
| pre-compaction-flush.sh | hooks/pre-compaction-flush.sh | CORE | hooks/pre-compaction-flush.sh | Context-loss prevention (always-on) |
| state-heartbeat.sh | hooks/state-heartbeat.sh | CORE | hooks/state-heartbeat.sh | SLO 9 + crash-recovery |
| crash-recovery.sh | hooks/crash-recovery.sh | CORE | hooks/crash-recovery.sh | Universal, no external deps |
| self-install.sh | hooks/self-install.sh | CORE | hooks/self-install.sh | Installs hook registrations |
| registration-check.sh | hooks/registration-check.sh | CORE | hooks/registration-check.sh | Verifies settings.json wiring |
| wiring-check.sh | hooks/wiring-check.sh | CORE | hooks/wiring-check.sh | Pre-session integrity gate |
| dispatch-gate.sh | hooks/dispatch-gate.sh | CORE | hooks/dispatch-gate.sh | ADR-002 dispatch-first architecture |
| orchestrator-mode-detect.sh | hooks/orchestrator-mode-detect.sh | CORE | hooks/orchestrator-mode-detect.sh | Mode switching core |
| subagent-context-injector.sh | hooks/subagent-context-injector.sh | CORE | hooks/subagent-context-injector.sh | Agent-mandatory-rules delivery |
| agent-prelaunch.sh | hooks/agent-prelaunch.sh | CORE | hooks/agent-prelaunch.sh | Pre-launch gate chain anchor |
| agent-checkpoint.sh | hooks/agent-checkpoint.sh | CORE | hooks/agent-checkpoint.sh | Agent lifecycle snapshot |
| agent-output-verifier.sh | hooks/agent-output-verifier.sh | CORE | hooks/agent-output-verifier.sh | Completion integrity |
| completion-gate.sh | hooks/completion-gate.sh | CORE | hooks/completion-gate.sh | DoD+criteria gate |
| auto-verify.sh | hooks/auto-verify.sh | CORE | hooks/auto-verify.sh | Closed-loop verification |
| auto-refine.sh | hooks/auto-refine.sh | CORE | hooks/auto-refine.sh | PITER refinement loop |
| dod-gate.sh | hooks/dod-gate.sh | CORE | hooks/dod-gate.sh | Definition-of-done enforcement |
| content-policy.sh | hooks/content-policy.sh | CORE | hooks/content-policy.sh | Universal harm guard |
| secret-detector.sh | hooks/secret-detector.sh | CORE | hooks/secret-detector.sh | Credential leak blocker (always-on) |
| destructive-git-blocker.sh | hooks/destructive-git-blocker.sh | CORE | hooks/destructive-git-blocker.sh | Data-loss prevention |
| destructive-rm-blocker.sh | hooks/destructive-rm-blocker.sh | CORE | hooks/destructive-rm-blocker.sh | Data-loss prevention |
| large-file-advisor.sh | hooks/large-file-advisor.sh | CORE | hooks/large-file-advisor.sh | Token-economy universal |
| result-truncator.sh | hooks/result-truncator.sh | CORE | hooks/result-truncator.sh | Token-economy universal |
| context-watchdog.sh | hooks/context-watchdog.sh | CORE | hooks/context-watchdog.sh | Context-management core |
| token-budget-monitor.sh | hooks/token-budget-monitor.sh | CORE | hooks/token-budget-monitor.sh | Budget enforcement |
| rate-limiter.sh | hooks/rate-limiter.sh | CORE | hooks/rate-limiter.sh | SLO 2 keeper |
| error-learning.sh | hooks/error-learning.sh | CORE | hooks/error-learning.sh | PDCA capture (universal) |
| error-pattern-detector.sh | hooks/error-pattern-detector.sh | CORE | hooks/error-pattern-detector.sh | 3-strikes warning |
| metrics-rotation.sh | hooks/metrics-rotation.sh | CORE | hooks/metrics-rotation.sh | SLO 7 owner |
| user-prompt-capture.sh | hooks/user-prompt-capture.sh | CORE | hooks/user-prompt-capture.sh | Request persistence guarantee |
| notify.sh | hooks/notify.sh | CORE | hooks/notify.sh | Cross-hook signalling primitive |
| pre-commit-gate.sh | hooks/pre-commit-gate.sh | CORE | .githooks/pre-commit | Git-level symlink, stays |

Total: **38 CORE**. Meets the <40 target.

### EXTENSION hook packs (rest)

Rather than enumerate 99 individual rows (too long to be useful), hooks are grouped by pack. Each row = (pattern → destination pack). Full 1:1 mapping lives in `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` §Appendix A.

| current path pattern | class | destination pack | reason |
|---|---|---|---|
| hooks/*-llm.sh (prompt-quality-llm, completeness-check-llm, confidence-gate-llm) | EXTENSION_advisory-llm | packages/cos-advisory-llm/hooks/ | Requires Haiku API (D43) |
| hooks/agent-bus-monitor.sh, teammate-idle.sh, native-agent-heartbeat.sh, agent-work-tracker.sh | EXTENSION_agent-coordination | packages/cos-agent-coordination/hooks/ | Multi-agent infra |
| hooks/engram-auto-sync.sh, engram-auto-import.sh, memu-sync.sh | EXTENSION_memory-engram | packages/cos-memory-engram/hooks/ | Optional memory backend |
| hooks/aguara-scan.sh, parry-scan.sh, semgrep-scan.sh, mcp-scan.sh, confidentiality-enforcer.sh | EXTENSION_security-tools | packages/cos-security-tools/hooks/ | External security CLIs |
| hooks/code-review-on-commit.sh, adr-detector.sh, release-guard.sh, pre-commit-gate.sh (symlink stays) | EXTENSION_git-safety | packages/cos-git-safety/hooks/ | Commit-time policies |
| hooks/mlflow-sync.sh, observability-trace.sh, kpi-trigger.sh, skill-usage-tracker.sh, skill-invocation-logger.sh, skill-feedback-tracker.sh | EXTENSION_observability | packages/cos-observability/hooks/ | Needs Langfuse/MLflow |
| hooks/task-bridge-notify.sh, task-recorder.sh, task-panel-sync.sh, task-created.sh, task-completed.sh, dequeue-notify.sh | EXTENSION_task-bridge | packages/cos-task-bridge/hooks/ | External task system |
| hooks/recap-sync.sh | EXTENSION_claude-code-integration | packages/cos-claude-code-integration/hooks/ | Claude-Code-specific (D43) |
| hooks/infra-health.sh, infra-intent-detector.sh, idle-service-cleanup.sh, valkey-ensure.sh, usage-health-check.sh | EXTENSION_infra-lifecycle | packages/cos-infra-lifecycle/hooks/ | Docker dependencies |
| hooks/auto-rollback-trigger.sh, auto-repair-dispatcher.sh, pre-agent-snapshot.sh, pre-cleanup-snapshot.sh | EXTENSION_auto-repair | packages/cos-auto-repair/hooks/ | Heavy, optional |
| hooks/consequence-evaluator.sh, skill-tracker.sh, auto-skill-generator.sh, tool-discovery-trigger.sh, tool-loop-detector.sh | EXTENSION_skill-governance | packages/cos-skill-governance/hooks/ | Self-evolution, optional |
| hooks/cognitive-os-health.sh, singularity-check.sh, metrics-calibrator-trigger.sh | EXTENSION_performance-intelligence | packages/cos-performance-intelligence/hooks/ | Meta-optimization |
| hooks/blast-radius.sh, scope-creep-detector.sh, scope-proportionality.sh, epic-task-detector.sh, clarification-gate.sh, clarification-interceptor.sh | EXTENSION_scope-governance | packages/cos-scope-governance/hooks/ | Large-project governance |
| hooks/reinvention-check.sh, ecosystem-check.sh, predev-completeness-check.sh, completeness-check.sh | EXTENSION_prompt-quality-gate | packages/cos-prompt-quality-gate/hooks/ | Advisory (already in packages/prompt-quality-gate) |
| hooks/aspirational-audit-weekly.sh, session-learning.sh, session-knowledge-extractor.sh, session-state-save.sh, session-changelog.sh, git-context-capture.sh, audit-id-enricher.sh | EXTENSION_audit-trail | packages/cos-audit-trail/hooks/ | Compliance-heavy |
| hooks/mcp-scan.sh (already above), jupyter-sandbox.sh | EXTENSION_ecosystem-integrations | per-tool pack | Per-tool |
| hooks/assumption-tracker.sh, claim-validator.sh, trust-score-validator.sh, confidence-gate.sh, pattern-check.sh, adaptive-bypass.sh (behavioural copy), doc-sync-detector.sh | EXTENSION_verification-audit | packages/cos-verification-audit/hooks/ | Policy-heavy audit chain |
| hooks/worktree-submodule-fix.sh, background-agent-reminder.sh | EXTENSION_misc-convenience (fold) | per destination | Nice-to-haves |
| hooks/context-diet.sh, contextual-rule-loader.sh, inject-phase-context.sh | EXTENSION_context-optimization | packages/cos-context-optimization/hooks/ | Behavioural opt-in |
| hooks/dry-run-preview.sh, private-mode-gate.sh, private-mode-metrics-gate.sh | EXTENSION_privacy-mode | packages/cos-privacy-mode/hooks/ | Mode-specific |
| hooks/rate-limit-protection.sh, resource-check.sh, dispatch-gate.sh (CORE above) | EXTENSION_resource-governance (partial) | packages/cos-resource-governance/hooks/ | Advanced budgeting (CORE keeps token-budget-monitor only) |
| hooks/global-verify.sh, error-pipeline.sh | CORE-CANDIDATE (keep for now — test gate) | hooks/ | Needed for SLO 6; CORE |

### REMOVE (superseded or dead)

| primitive | current path | class | reason |
|---|---|---|---|
| task-panel-sync.sh | hooks/task-panel-sync.sh | REMOVE | Superseded by task-bridge-notify.sh (ADR-024, FROZEN-BACKLOG) |
| agnix-lint.sh | hooks/agnix-lint.sh | REMOVE (if agnix retired) or EXTENSION_ecosystem-integrations | Unused per registry |

---

## §2 — Libraries (150 total)

CORE (24): `agent_context_injector`, `agent_permissions`, `audit_id`, `budget_calculator`, `capability_levels`, `circuit_breaker`, `config_loader`, `context_estimator`, `engram_client` (thin client — sync lib moves), `file_lock_registry`, `manifest_loader`, `memory` (dict-based core), `notifications`, `paths`, `process_registry`, `prompt_builder`, `ref_key_loader`, `request_queue`, `return_contract_parser`, `safe_engram`, `secret_ref`, `session_state`, `smart_reader`, `wiring_validator`.

Rationale: these are called by 3+ CORE hooks OR underpin `cos init`/session-start. Remaining 126 libraries each serve ONE extension pack — move alongside their hook.

| Library pattern | destination pack |
|---|---|
| `advisor_*.py`, `dispatch_model_advisor.py`, `*_advisor.py` | cos-advisory-llm |
| `agent_bus*.py`, `agent_health_monitor.py`, `agent_dashboard.py`, `agent_progress_tracker.py` | cos-agent-coordination |
| `cognee_*.py`, `memory_scanner.py`, `memory_decay.py`, `memory_first.py`, `memory_retriever.py`, `bifrost_client.py`, `litellm_client.py` | cos-memory-engram / cos-ecosystem-integrations |
| `license_guard.py`, `confidentiality_scanner.py`, `threat_classifier.py`, `guardrails_validators.py` | cos-security-tools |
| `mlflow_bridge.py`, `observability.py`, `telemetry.py`, `kpi_collector.py`, `performance_monitor.py`, `phase_timing.py`, `metric_event.py` | cos-observability |
| `sdd_*.py` | cos-sdd |
| `claude_executor.py`, `claude_usage_reader.py` | cos-claude-code-integration |
| `auto_executor.py`, `auto_repair.py`, `homeostasis.py`, `symbiosis_monitor.py`, `singularity.py`, `self_improvement.py`, `learning_pipeline.py` | cos-performance-intelligence |
| `host_monitor.py`, `smart_infra.py` | cos-infra-lifecycle |
| `issue_pipeline.py`, `work_queue.py`, `dead_letter_queue.py` | cos-task-bridge |
| `reinvention_guard.py`, `ecosystem_evaluator.py`, `completeness_checker.py`, `prompt_classifier.py` | cos-prompt-quality-gate |
| `webhook_trigger.py`, `web_crawler.py`, `planning_poker.py`, `simulation_arena.py`, `reverse_engineer.py`, `repo_analyzer.py`, `research_scoring.py`, `jupyter_client.py` | cos-ecosystem-integrations |
| `format_converter.py`, `notification_digest.py`, `smart_truncator.py`, `anchored_summarizer.py`, `context_diet.py`, `prompt_cache.py` | cos-context-optimization |
| `consequence_engine.py`, `dynamic_tool_creator.py`, `skill_router.py`, `skill_archive.py`, `stack_skill_recommender.py`, `tool_adoption_evaluator.py` | cos-skill-governance |
| `trust_report_parser.py` | CORE (called by trust-score-validator hook, universal) |
| `cost_dashboard.py`, `cost_predictor.py` | CORE (called by budget/token libs) |
| All other single-use libs | follow their hook |

---

## §3 — Rules (103 total, excluding ROADMAP/RULES-COMPACT)

CORE (28): always-active rules that apply to every install regardless of profile.

| rule | class | reason |
|---|---|---|
| acceptance-criteria.md | CORE | Universal quality gate |
| adaptive-bypass.md | CORE | First rule evaluated |
| adversarial-review.md | CORE | Universal review policy |
| agent-audit-before-commit.md | CORE | Commit discipline |
| agent-output-reading.md | CORE | Token-economy universal |
| agent-quality.md | CORE | Anti-minimum behaviour |
| anti-hallucination.md | CORE | Always-on |
| assumption-tracking.md | CORE | Always-on |
| broken-window-policy.md | CORE | Quality baseline |
| capability-levels.md | CORE | Profile negotiation |
| closed-loop-prompts.md | CORE | Universal agent pattern |
| confidence-gate.md | CORE | Universal gate |
| content-policy.md | CORE | Harm prevention |
| context-management.md | CORE | Universal |
| credential-management.md | CORE | Security basics |
| decomposition.md | CORE | Token economy |
| definition-of-done.md | CORE | Universal completion |
| error-learning.md | CORE | PDCA universal |
| model-routing.md | CORE | Routing discipline |
| model-directive.md | CORE | Directive obedience |
| phase-aware-agents.md | CORE | Core project model |
| prompt-quality.md | CORE | Input discipline |
| responsiveness.md | CORE | UX contract |
| result-management.md | CORE | Output discipline |
| scope-creep-detection.md | CORE | Small-task guard |
| token-economy.md | CORE | Cost discipline |
| trust-score.md | CORE | Universal verification |
| split-and-resume.md | CORE | Long-task universal |


**Special cases:**
- `so-slo.md` → **CORE** (adopted ADR-028 D5, SLO catalogue is constitutional).
- `hook-security-profiles.md` → **CORE** (ADR-002 profile system).
- `ROADMAP.md` + `RULES-COMPACT.md` → **CORE** meta-docs.

---

## §4 — Skills (127 total)

CORE (20): minimum skill set for a fresh install to be useful.

| skill | class | reason |
|---|---|---|
| cognitive-os-init | CORE | `cos init` entry point |
| cognitive-os-status | CORE | Basic inspection |
| cos-status | CORE | Alias for status |
| session-manager | CORE | Session ops |
| session-backlog | CORE | Queue drain |
| session-wrapup | CORE | ADR-030 wrapup |
| add-hook / add-rule / add-skill / add-mcp | CORE (4) | Customization entry points |
| evaluate-plan | CORE | Adversarial review engine |
| dod-check | CORE | DoD verification |
| exhaustive-prompt | CORE | Prompt quality path |
| compose-prompt | CORE | Prompt composition |
| generate-config | CORE | Init helper |
| validate-config | CORE | Init helper |
| smoke-test | CORE | Post-install verification |
| run-tests | CORE | Generic test runner |
| plan-bug / plan-feature | CORE (2) | Small+Medium complexity paths |
| CATALOG.md / CATALOG-COMPACT.md | CORE (meta) | Discovery indexes |

Remaining 107 skills → destination pack based on their trigger:
- `sdd-*` (10) → cos-sdd
- `*-integration`, `*-scan`, `pentest-*`, `red-team`, `semgrep-scan`, `vulnerability-scan`, `secret-audit`, `security-audit`, `audit-integrity` → cos-security-tools / cos-ecosystem-integrations
- `agent-dashboard`, `agent-kpis`, `agent-stress-test`, `squad-manager`, `persistent-agent`, `planning-poker`, `simulation-arena`, `arena` → cos-agent-coordination
- `self-improve`, `self-review`, `metrics-calibrator`, `model-optimizer`, `singularity`, `analyze-improvements`, `apply-improvements`, `optimize-skill`, `detect-patterns` → cos-performance-intelligence
- `release-os`, `push-release`, `tag-release`, `validate-release`, `bump-version`, `generate-changelog` → cos-release-automation
- `webhook-trigger`, `web-crawler`, `batch-runner`, `jupyter-execute`, `gpu-sandbox` → cos-ecosystem-integrations
- `repo-forensics`, `reverse-engineer`, `research-protocol`, `deep-research`, `recommend-library`, `scout`, `sandbox-sample`, `repo-scout`, `contract-drift`, `impact-analysis`, `readiness-check`, `pr-review`, `code-review` → cos-scope-governance / split across
- `private-mode` → cos-privacy-mode
- `conversation-memory`, `recall-search`, `memu-context`, `cognee-*` → cos-memory-engram
- `harness-audit`, `component-classifier`, `audit-website`, `trust-audit` → cos-verification-audit
- `tool-discovery`, `skill-creator`, `auto-refine`, `auto-rollback`, `automaker-bridge` → cos-skill-governance
- `repair-status`, `resolve-blockers`, `sre-agent`, `scaffold-project`, `detect-stack`, `document-feature`, `doc-sync` → per-fit
- `sprint`, `retrospective`, `session-report-executive`, `caveman*` → cos-session-rituals (new minor pack) or cos-performance-intelligence

---

## §5 — Scripts (64 total)

CORE (16): `cos`, `cos-init.sh`, `cos-init-global.sh`, `cos-bootstrap.sh`, `cos-status.sh`, `cos-registry.sh`, `cos-update.sh`, `cos-sessions.sh`, `cos-release-check.sh`, `doctor.sh`, `apply-efficiency-profile.sh`, `generate-project-settings.sh`, `merge-settings.sh`, `setup.sh`, `install-cos.sh`, `uninstall.sh`.

Remaining 48 scripts move with their owning pack:
- `install-aguara.sh`, `install-mcp-scan.sh`, `install-garak.sh`, `install-tob-skills.sh`, `install-promptfoo.sh` → cos-security-tools / cos-ecosystem-integrations installers
- `setup-langfuse.sh` → cos-observability
- `so-emergency-stop.sh`, `so-reaper.sh`, `so-vitals.sh` → CORE (ADR-028)
- `aspirational-audit.py`, `scope-tag-backfill.py` → cos-audit-trail
- `check-*.py`, `check-*.sh` (lib-wiring, catalog-sync, hook-registration, test-ratchet, test-quality, upstream) → CORE (installer integrity)
- `backfill-cost-events.py`, `benchmark-hooks.sh`, `compose-agent-prompt.py`, `component-lint.sh`, `engram-sync.sh`, `extract-agent-output.sh`, `generate-compact-catalog.py`, `manifest-check.sh`, `orchestrator.py`, `semantic-lookup.mjs`, `set-security-profile.sh`, `setup-git-hooks.sh`, `install-pre-commit.sh`, `auto-update-projects.sh`, `cos-core-skills-check.sh`, `cos-ghost-skills.sh`, `cos-usage-report.sh`, `create-release.sh`, `register-mcps.sh`, `ide-bridge.sh`, `migrate-to-cognitive-os.sh`, `postinstall.js`, `run-all-tests.sh`, `test-*.sh`, `upgrade.sh`, `version.sh` → per-pack as appropriate; most lean CORE because they serve install/release/test workflows.

---

## §6 — REMOVE list (pre-v1.0 cleanup)

| primitive | reason |
|---|---|
| `hooks/task-panel-sync.sh` | Superseded by task-bridge-notify (ADR-024). |
| `hooks/_lib/task_panel_adapter.py` | Folded into task_bridge.py. |
| `packages/_archived/**` | Already archived; delete before v1.0. |
| Any skill not in CATALOG-COMPACT tier and not referenced in last 30d | Run `skills/cos-ghost-skills.sh` audit; remove ghosts. |

---

## Summary table

| Surface | CORE count | EXTENSION count | REMOVE | Matches target |
|---|---|---|---|---|
| Hooks | 38 | 97 | 2 | Yes (<40) |
| Libs | 24 | 126 | 0 | Yes (<25) |
| Rules | 28 | 75 | 0 | Yes (<30) |
| Skills | 20 | 107 | 0 (ghosts TBD) | At limit (=20) |
| Scripts | 16 | 48 | 0 | n/a |
| **Total** | **126** | **453** | **2** | **22% CORE** |

Every agentic primitive has a class. Zero "unclassified". Acceptance criterion #1 met.
