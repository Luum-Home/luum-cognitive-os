# Cognitive OS Component Audit — Core vs Package Classification

> Source of truth for the package restructure. Generated 2026-03-28.
> 355+ components audited. 82 CORE, 273 PACKAGE.

## Summary

| Category | Total | CORE | PACKAGE |
|---|---|---|---|
| Skills | 85 | 9 | 76 |
| Hooks | 72 | 24 | 48 |
| Rules | 81 | 38 | 43 |
| Python libs | 51 | 8 | 43 |
| Agents | 3 | 0 | 3 |
| Templates | 7 | 3 | 4 |
| Go CLI | 56 | ALL | -- |
| **Total** | **355+** | **82** | **273** |

## Classification Criteria

**CORE** = Required for the OS to function. Session lifecycle, error capture, security, basic governance, resource management, and the Go CLI tooling.

**PACKAGE** = Valuable but optional. Integrations, advanced quality gates, observability, specialized skills, ecosystem tools. Can be installed/removed via `cos install`/`cos remove`.

---

## CORE Components

### CORE Skills (9)

| Skill | Purpose |
|---|---|
| `cognitive-os-init` | Initialize COS in any project |
| `cognitive-os-status` | Report COS health and state |
| `cognitive-os-test` | Run COS test suite |
| `compat-test` | Model compatibility validation |
| `validate-config` | Validate cognitive-os.yaml |
| `sdd-continue` | Resume next SDD phase |
| `sdd-resume` | Resume interrupted SDD pipeline |
| `resource-governor` | Budget and resource optimization |
| `session-manager` | Session lifecycle management |

### CORE Hooks (24)

| Hook | Type | Purpose |
|---|---|---|
| `session-init.sh` | SessionStart | Initialize session, generate ID |
| `session-resume.sh` | SessionStart | Detect and recover interrupted tasks |
| `session-cleanup.sh` | Stop | Merge metrics, deregister session |
| `session-state-save.sh` | Stop | Persist session state |
| `session-knowledge-extractor.sh` | Stop | Extract learnings from session |
| `session-learning.sh` | PostToolUse | Capture session errors and patterns |
| `crash-recovery.sh` | SessionStart | Detect orphaned stashes |
| `secret-detector.sh` | PreToolUse | Block secret exposure |
| `content-policy.sh` | PostToolUse | Block prohibited terms in writes |
| `resource-check.sh` | PreToolUse | Budget enforcement |
| `rate-limiter.sh` | PreToolUse | Rate limit enforcement |
| `rate-limit-protection.sh` | PreToolUse | Token consumption monitoring |
| `error-pipeline.sh` | PostToolUse | Capture errors to JSONL |
| `error-pattern-detector.sh` | PreToolUse | Inject warnings for recurring errors |
| `cognitive-os-health.sh` | SessionStart | Overall health check |
| `infra-health.sh` | SessionStart | Docker service health |
| `inject-phase-context.sh` | PreToolUse | Phase-aware context injection |
| `pre-commit-gate.sh` | PreToolUse | Block commits on test failure |
| `private-mode-gate.sh` | PreToolUse | Block persistence in private mode |
| `private-mode-metrics-gate.sh` | PreToolUse | Block metrics in private mode |
| `concurrent-write-guard.sh` | PreToolUse | Advisory file locking |
| `auto-checkpoint.sh` | PostToolUse | Periodic git stash checkpoints |
| `guardrails-validator.sh` | PostToolUse | NeMo Guardrails content validation |
| `self-install.sh` | SessionStart | Self-hosting dogfood sync |

### CORE Rules (38)

| # | Rule | Category |
|---|---|---|
| 1 | `RULES-COMPACT.md` | Index -- thematic rule summary |
| 2 | `phase-aware-agents.md` | Governance -- phase-dependent behavior |
| 3 | `definition-of-done.md` | Quality -- DoD by complexity |
| 4 | `acceptance-criteria.md` | Quality -- mandatory verifiable criteria |
| 5 | `closed-loop-prompts.md` | Quality -- self-correcting execution |
| 6 | `agent-quality.md` | Quality -- maximum output enforcement |
| 7 | `trust-score.md` | Quality -- mandatory trust reports |
| 8 | `agent-identity.md` | Security -- agent audit trail |
| 9 | `agent-security.md` | Security -- least privilege |
| 10 | `credential-management.md` | Security -- never in code |
| 11 | `content-policy.md` | Security -- prohibited terms |
| 12 | `license-policy.md` | Security -- dependency license gates |
| 13 | `security-scanning.md` | Security -- Semgrep SAST |
| 14 | `pentesting-readiness.md` | Security -- testing surface |
| 15 | `supply-chain-defense.md` | Security -- Docker digest pinning |
| 16 | `plan-first.md` | Governance -- plan before implement |
| 17 | `adaptive-bypass.md` | Governance -- smart orchestration |
| 18 | `agent-kpis.md` | Governance -- performance metrics |
| 19 | `estimation-calibration.md` | Governance -- estimation feedback |
| 20 | `self-improvement-protocol.md` | Governance -- self-healing evolution |
| 21 | `squad-protocol.md` | Governance -- team organization |
| 22 | `blast-radius.md` | Safety -- impact estimation |
| 23 | `scope-proportionality.md` | Safety -- proportional changes |
| 24 | `impact-analysis.md` | Safety -- change impact |
| 25 | `anti-hallucination.md` | Safety -- claim validation |
| 26 | `confidence-gate.md` | Safety -- minimum confidence |
| 27 | `error-learning.md` | Resilience -- error capture |
| 28 | `auto-repair.md` | Resilience -- auto-fix known errors |
| 29 | `auto-rollback.md` | Resilience -- revert failed changes |
| 30 | `crash-recovery.md` | Resilience -- survive crashes |
| 31 | `fault-tolerance.md` | Resilience -- 4-tier model |
| 32 | `consequence-system.md` | Resilience -- OKR-driven feedback |
| 33 | `resource-governance.md` | Cost -- budget enforcement |
| 34 | `rate-limiting.md` | Cost -- rate limits |
| 35 | `rate-limit-protection.md` | Cost -- token monitoring |
| 36 | `token-economy.md` | Cost -- 5 principles |
| 37 | `decomposition.md` | Cost -- break down expensive tasks |
| 38 | `model-routing.md` | Cost -- task-to-model mapping |

> Note: The CORE rules list above includes the 38 most essential rules. Additional rules listed in RULES-COMPACT.md sections (model-compatibility, cost-prediction, capability-levels, context-management, context-optimization, result-management, engram-organization, session-concurrency, infra-health, infra-intent, orchestrator-mode, performance-monitoring, singularity, sandbox-sampling, dry-run, clarification-gate, adversarial-review, assumption-tracking, step-files, split-and-resume, responsiveness, prompt-composition, library-selection, prompt-quality, cognitive-os-changes, os-vs-project, dogfooding, capability-protection, private-mode, doc-sync, agent-communication, agent-customization, agent-sidecars, scope-creep-detection, skill-management, auto-skill-generation) are classified as CORE or PACKAGE based on their functional necessity. All rules referenced by RULES-COMPACT.md are considered CORE since they define the behavioral contract.

### CORE Python Libs (8)

| Library | Purpose |
|---|---|
| `model_router.py` | Multi-provider model selection |
| `smart_infra.py` | Infrastructure auto-scaling |
| `cost_dashboard.py` | Cost tracking and reporting |
| `rate_limiter.py` | Rate limit enforcement |
| `checkpoint_manager.py` | Crash recovery checkpoints |
| `skill_archive.py` | Evolutionary skill snapshots |
| `consequence_engine.py` | OKR-driven consequence evaluation |
| `singularity.py` | Autonomous MAPE-K controller |

### CORE Templates (3)

| Template | Purpose |
|---|---|
| `agent-preamble.md` | Standard sub-agent instructions |
| `quality-gates.md` | Quality gate checklist |
| `error-recovery.md` | Error recovery procedures |

### Go CLI (56 files -- ALL CORE)

All Go source files under `cmd/cos/` and `cmd/cos-test/` are CORE. They implement the `cos` package manager CLI.

**cmd/cos/** (40 files):
- `main.go` -- entrypoint
- `internal/cli/` -- root.go, init.go, install.go, remove.go, list.go, search.go, update.go, validate.go, publish.go, audit.go, map.go, perf.go, cli_test.go
- `internal/installer/` -- installer.go, hooks.go, export.go, installer_test.go
- `internal/lockfile/` -- lockfile.go, lockfile_test.go
- `internal/manifest/` -- parse.go, types.go, validate.go, parse_test.go, validate_test.go
- `internal/project/` -- root.go, root_test.go
- `internal/registry/` -- github.go, registry_test.go
- `internal/resolver/` -- source.go, github.go, resolver_test.go
- `internal/security/` -- audit.go, injection.go, license.go, secrets.go, audit_test.go
- `internal/ui/` -- config.go, progress.go, styles.go

**cmd/cos-test/** (16 files):
- `main.go` -- entrypoint
- `internal/cli/` -- root.go, run.go, watch.go, coverage.go, dashboard.go
- `internal/config/` -- config.go
- `internal/runner/` -- discovery.go, pytest.go, results.go
- `internal/ui/` -- config.go, dashboard.go, messages.go, progress.go, styles.go, summary.go

---

## PACKAGE Components -- Grouped by Target Package

### @luum/sdd-pipeline

**Type**: bundle -- Spec-Driven Development pipeline phases and support tools
**Components** (37):
- skills/sdd-compound/
- skills/evaluate-plan/
- skills/readiness-check/
- skills/dod-check/
- skills/exhaustive-prompt/
- skills/compose-prompt/
- skills/planning-poker/
- skills/sandbox-sample/
- skills/confidence-check/
- skills/verification-before-completion/
- skills/self-review/
- skills/impact-analysis/
- hooks/completeness-check.sh
- hooks/completion-gate.sh
- hooks/scope-creep-detector.sh
- hooks/scope-proportionality.sh
- hooks/epic-task-detector.sh
- hooks/adaptive-bypass.sh
- hooks/dry-run-preview.sh
- hooks/pre-compaction-flush.sh
- hooks/contextual-rule-loader.sh
- rules/skill-management.md
- rules/auto-skill-generation.md
- rules/private-mode.md
- rules/doc-sync.md
- rules/agent-communication.md
- rules/agent-customization.md
- rules/agent-sidecars.md
- rules/scope-creep-detection.md
- lib/estimation_calibrator.py
- lib/planning_poker.py
- lib/impact_analysis.py
- lib/staged_verification.py
- lib/cross_verifier.py
- lib/ground_truth.py
- lib/phase_timing.py
- lib/sdd_resume.py

### @luum/quality-gates

**Type**: bundle -- Advanced quality validation hooks
**Components** (18):
- hooks/clarification-gate.sh
- hooks/clarification-interceptor.sh
- hooks/confidence-gate.sh
- hooks/claim-validator.sh
- hooks/trust-score-validator.sh
- hooks/assumption-tracker.sh
- hooks/blast-radius.sh
- hooks/consequence-evaluator.sh
- hooks/prompt-quality.sh
- hooks/tool-loop-detector.sh
- hooks/pre-cleanup-snapshot.sh
- hooks/architecture-compliance.sh
- hooks/auto-skill-generator.sh
- hooks/kpi-trigger.sh
- hooks/task-recorder.sh
- hooks/skill-tracker.sh
- lib/capability_levels.py
- lib/performance_monitor.py

### @luum/error-recovery

**Type**: bundle -- Error learning, auto-repair, rollback
**Components** (9):
- skills/error-analyzer/
- skills/auto-refine/
- skills/auto-rollback/
- skills/repair-status/
- skills/resolve-blockers/
- skills/systematic-debugging/
- hooks/auto-rollback-trigger.sh
- lib/error_classifier.py
- lib/error_matching.py

### @luum/agent-governance

**Type**: bundle -- Agent KPIs, squads, self-improvement
**Components** (27):
- skills/agent-kpis/
- skills/squad-manager/
- skills/retrospective/
- skills/sprint/
- skills/self-improve/
- skills/trust-audit/
- skills/optimize-skill/
- skills/metrics-calibrator/
- skills/batch-runner/
- hooks/agent-bus-monitor.sh
- hooks/agent-checkpoint.sh
- hooks/agent-prelaunch.sh
- hooks/metrics-calibrator-trigger.sh
- hooks/metrics-rotation.sh
- lib/agent_permissions.py
- lib/agent_bus.py
- lib/agent_dashboard.py
- lib/batch_runner.py
- lib/homeostasis.py
- lib/symbiosis_monitor.py
- lib/system_graph.py
- lib/domain_router.py
- lib/memory_decay.py
- agents/service-health-checker.md
- agents/stack-validator.md
- agents/test-coverage-enforcer.md

### @luum/cost-management

**Type**: bundle -- Cost prediction, model optimization
**Components** (4):
- skills/model-optimizer/
- lib/cost_predictor.py
- lib/claude_usage_reader.py
- lib/rate_limit_protection.py

### @luum/security-audit

**Type**: bundle -- Security scanning, secret audit, pentesting
**Components** (7):
- skills/semgrep-scan/
- skills/secret-audit/
- skills/security-audit/
- skills/pentest-self/
- hooks/semgrep-scan.sh
- lib/license_guard.py
- lib/secret_ref.py

### @luum/observability

**Type**: bundle -- Tracing, monitoring, notifications
**Components** (6):
- skills/opik-integration/
- hooks/observability-trace.sh
- hooks/notify.sh
- lib/observability.py
- lib/notifications.py
- lib/litellm_client.py

### @luum/infrastructure

**Type**: bundle -- SRE agent, smoke tests, infra management
**Components** (12):
- skills/sre-agent/
- skills/smoke-test/
- skills/devbox-checkpoint/
- hooks/idle-service-cleanup.sh
- hooks/infra-intent-detector.sh
- hooks/singularity-check.sh
- lib/orchestrator_mode.py
- lib/claude_executor.py
- lib/file_lock_registry.py
- lib/session_state.py
- lib/session_parser.py
- lib/webhook_trigger.py

### @luum/documentation

**Type**: bundle -- Doc sync, feature docs, research
**Components** (10):
- skills/doc-sync/
- skills/document-feature/
- skills/deep-research/
- skills/research-protocol/
- skills/repo-scout/
- skills/recommend-library/
- hooks/doc-sync-detector.sh
- lib/research_scoring.py
- lib/web_crawler.py
- templates/rebranding-checklist.md

### @luum/testing

**Type**: bundle -- TDD, coverage, test tools
**Components** (3):
- skills/test-driven-development/
- skills/coverage-enforcement/
- skills/harness-audit/

### @luum/planning

**Type**: bundle -- Plan features, bugs, capability snapshots
**Components** (3):
- skills/plan-feature/
- skills/plan-bug/
- skills/capability-snapshot/

### @luum/ecosystem-tools

**Type**: bundle -- External tool integrations
**Components** (9):
- rules/ecosystem-tools.md
- rules/parry-integration.md
- rules/hcom-integration.md
- rules/repomix-integration.md
- rules/trailofbits-skills.md
- rules/context7-auto-trigger.md
- hooks/agnix-lint.sh
- skills/tool-discovery/
- hooks/tool-discovery-trigger.sh

### @luum/cognee-integration

**Type**: addon -- Cognee knowledge graph
**Components** (3):
- skills/cognee-integration/
- skills/cognee-search/
- lib/cognee_client.py


**Components** (3):

### @luum/nemo-guardrails

**Type**: addon -- NeMo Guardrails content safety
**Components** (2):
- skills/nemo-guardrails/
- lib/guardrails_validators.py

### @luum/jupyter-integration

**Type**: addon -- Jupyter notebook execution
**Components** (3):
- skills/jupyter-execute/
- hooks/jupyter-sandbox.sh
- lib/jupyter_client.py

### @luum/memu-integration

**Type**: addon -- Memory management service
**Components** (6):
- skills/memu-context/
- skills/conversation-memory/
- skills/recall-search/
- hooks/memu-sync.sh
- hooks/engram-auto-import.sh
- hooks/engram-auto-sync.sh

### @luum/eval-framework

**Type**: bundle -- Evaluation and benchmarking
**Components** (8):
- skills/deepeval-integration/
- skills/promptfoo-integration/
- skills/ragas-integration/
- skills/strands-evals-integration/
- skills/cognitive-os-benchmark/
- skills/arena/
- skills/simulation-arena/
- lib/simulation_arena.py

### @luum/automation

**Type**: bundle -- Issue pipelines, webhooks, automaker
**Components** (10):
- skills/issue-pipeline/
- skills/webhook-trigger/
- skills/automaker-bridge/
- skills/persistent-agent/
- skills/singularity/
- skills/private-mode/
- skills/contract-drift/
- hooks/conversation-capture.sh
- hooks/sync-to-repo.sh
- lib/issue_pipeline.py

### @luum/advanced-templates

**Type**: addon -- Specialized prompt templates
**Components** (4):
- templates/fintech-gates.md
- templates/generator-validator-pair.md
- templates/go-service-context.md
- templates/CLAUDE.md.template

### @luum/gpu-sandbox

**Type**: addon -- GPU sandbox for ML workloads
**Components** (1):
- skills/gpu-sandbox/

### @luum/web-tools

**Type**: addon -- Website auditing and crawling
**Components** (2):
- skills/audit-website/
- skills/web-crawler/

### @luum/resume-tasks

**Type**: addon -- Task recovery
**Components** (1):
- skills/resume-tasks/

---

## Migration Checklist

For each package:
- [ ] Create `packages/{name}/cos-package.yaml`
- [ ] Move component files to `packages/{name}/`
- [ ] Update imports/references in CORE components
- [ ] Update test paths
- [ ] Update docs references
- [ ] Verify `cos install ./packages/{name}` works
- [ ] Verify `cos remove {name}` cleans up correctly

### Per-Package Checklist

- [ ] @luum/sdd-pipeline (37 components)
- [ ] @luum/quality-gates (18 components)
- [ ] @luum/error-recovery (9 components)
- [ ] @luum/agent-governance (27 components)
- [ ] @luum/cost-management (4 components)
- [ ] @luum/security-audit (7 components)
- [ ] @luum/observability (6 components)
- [ ] @luum/infrastructure (12 components)
- [ ] @luum/documentation (10 components)
- [ ] @luum/testing (3 components)
- [ ] @luum/planning (3 components)
- [ ] @luum/ecosystem-tools (9 components)
- [ ] @luum/cognee-integration (3 components)
- [ ] @luum/nemo-guardrails (2 components)
- [ ] @luum/jupyter-integration (3 components)
- [ ] @luum/memu-integration (6 components)
- [ ] @luum/eval-framework (8 components)
- [ ] @luum/automation (10 components)
- [ ] @luum/advanced-templates (4 components)
- [ ] @luum/gpu-sandbox (1 component)
- [ ] @luum/web-tools (2 components)
- [ ] @luum/resume-tasks (1 component)

### Post-Migration Verification

- [ ] All CORE components function without any packages installed
- [ ] `cos install` installs each package cleanly
- [ ] `cos remove` removes each package without affecting CORE
- [ ] No circular dependencies between packages
- [ ] CATALOG.md auto-generated from installed packages
- [ ] RULES-COMPACT.md reflects only installed rules
- [ ] settings.json hooks reflect only installed hooks
- [ ] All tests pass with full install
- [ ] All tests pass with CORE-only install
