<!--
RECONCILIATION STATUS: DONE — All 4 phases complete. Verified 2026-05-02.
Superseded for Phases 1-2 by: ADR-031 (aspirational-audit), ws6 commits (3f6a5c1 "SCOPE tags to 380 components", 5acb797 "171 additional SCOPE tags"), scripts/apply-efficiency-profile.sh scope-filter (commit 1f5911c)
Reconciled: 2026-04-21 (Phases 1-2 only)
Re-audited: 2026-04-27 — Phase 1 (skills) and Phase 2 (hooks + libs) confirmed complete: 506+ components carry SCOPE tags. Phase 3 (rules) COMPLETED 2026-04-27: all 110 rules/*.md files now carry `<!-- SCOPE: ... -->` tag (108 both, 2 os-only). Templates still pending. Phase 4 (self-install.sh scope filtering and `cos install` filtering) also remains pending. The 5 DoD items at the end of this plan are quality gates that span all phases — none are fully achievable until templates + Phase 4 ship.
Reason for original SUPERSEDED tag: the classification mechanism (SCOPE tag convention + tagging at scale) shipped. The completion gate over all 433+ components and the installer-side filtering have not.
-->

# Component Scope Classification

## What

Classify every Cognitive OS component (rules, hooks, skills, templates, lib modules) by
installation scope: **os-only**, **project**, or **both**.

## Why

Currently `self-install.sh` and `cos install` install everything or nothing. This means:
- Target projects receive OS-internal tools (e.g. `release-os`, `cognitive-os-test`)
- The OS repo during development receives project-facing scaffolding it doesn't need
- There is no machine-readable way to filter components by audience

Adding a scope tag to every component's frontmatter / header makes this filterable.

## Scope Definitions

| Scope | Meaning | Install behavior |
|---|---|---|
| **os-only** | Only relevant when developing the OS itself | Never installed in target projects |
| **project** | Only relevant in target projects | Always installed in target projects |
| **both** | Universal — useful everywhere | Always installed (OS repo + projects) |

---

## 1. Rules Classification

### rules/*.md

| Component | Scope | Rationale |
|---|---|---|
| rules/RULES-COMPACT.md | both | Master index loaded by all sessions |
| rules/acceptance-criteria.md | both | Universal quality principle |
| rules/adaptive-bypass.md | both | Universal orchestration principle |
| rules/adversarial-review.md | both | Universal review principle |
| rules/agent-communication.md | both | Agent bus useful in any orchestrated project |
| rules/agent-customization.md | both | Per-agent overrides useful everywhere |
| rules/agent-escalation.md | both | Universal escalation protocol |
| rules/agent-identity.md | both | Universal audit trail |
| rules/agent-kpis.md | both | Universal agent health metrics |
| rules/agent-output-reading.md | both | Universal agent output parsing |
| rules/agent-quality.md | both | Universal quality standards |
| rules/agent-security.md | both | Universal least-privilege |
| rules/agent-sidecars.md | both | Universal sidecar memory pattern |
| rules/aguara-integration.md | both | Security scanning useful in any project |
| rules/anti-hallucination.md | both | Universal verification principle |
| rules/assumption-tracking.md | both | Universal quality gate |
| rules/audit-trail.md | both | Universal session audit |
| rules/auto-repair.md | both | Universal error recovery |
| rules/auto-rollback.md | both | Universal SDD rollback |
| rules/auto-skill-generation.md | both | Universal skill lifecycle |
| rules/blast-radius.md | both | Universal impact estimation |
| rules/broken-window-policy.md | both | Universal quality principle |
| rules/capability-levels.md | both | Universal model capability scaling |
| rules/capability-protection.md | os-only | Snapshot before OS cleanup/refactor — irrelevant in projects |
| rules/clarification-gate.md | both | Universal gate |
| rules/closed-loop-prompts.md | both | Universal prompt pattern |
| rules/cognitive-load.md | both | Universal context monitoring |
| rules/cognitive-os-changes.md | os-only | Plan-first for OS modifications only |
| rules/component-classification.md | os-only | CORE vs PACKAGE decision only applies to OS development |
| rules/confidence-gate.md | both | Universal trust gate |
| rules/confidentiality-protection.md | both | IP leak prevention useful in any project |
| rules/consequence-system.md | both | Universal OKR feedback loop |
| rules/content-policy.md | both | Universal content enforcement |
| rules/context-management.md | both | Universal context window management |
| rules/context-optimization.md | both | Universal token efficiency |
| rules/context7-auto-trigger.md | both | Library doc lookup useful everywhere |
| rules/cost-prediction.md | both | Universal cost estimation |
| rules/crash-recovery.md | both | Universal WAL recovery |
| rules/credential-management.md | both | Universal security |
| rules/decomposition.md | both | Universal cost decomposition |
| rules/definition-of-done.md | both | Universal DoD |
| rules/doc-sync.md | both | Universal doc freshness |
| rules/dogfooding.md | os-only | Self-hosting requirement only for OS repo |
| rules/dry-run.md | both | Universal dry-run mode |
| rules/dynamic-tool-creation.md | both | Universal mid-task tooling |
| rules/e2b-integration.md | both | Sandbox execution useful in any project |
| rules/ecosystem-tools.md | both | Tool integration docs useful everywhere |
| rules/engram-organization.md | both | Universal memory organization |
| rules/error-learning.md | both | Universal error capture |
| rules/estimation-calibration.md | both | Universal estimation |
| rules/fault-tolerance.md | both | Universal resilience |
| rules/hcom-integration.md | both | Multi-session comms useful anywhere |
| rules/hook-security-profiles.md | both | Security profiles useful in any project |
| rules/impact-analysis.md | both | Universal blast radius analysis |
| rules/infra-health.md | both | Docker health useful in any project |
| rules/infra-intent.md | both | Universal infra keyword detection |
| rules/library-selection.md | both | Universal library evaluation |
| rules/license-policy.md | both | Universal license enforcement |
| rules/model-compatibility.md | both | Universal model baseline docs |
| rules/model-directive.md | both | Universal dispatch routing |
| rules/model-routing.md | both | Universal model routing |
| rules/non-blocking-retry.md | both | Universal retry pattern |
| rules/orchestrator-mode.md | both | Universal subprocess delegation |
| rules/os-vs-project.md | both | Helps developers understand separation |
| rules/parry-integration.md | both | Security scanning useful anywhere |
| rules/pentesting-readiness.md | both | Security testing useful in any project |
| rules/performance-monitoring.md | both | Universal performance tracking |
| rules/phase-aware-agents.md | both | Universal phase awareness |
| rules/plan-first.md | both | Universal planning discipline |
| rules/pre-commit-gate.md | both | Universal commit gate |
| rules/pre-dev-readiness-gate.md | project | Pre-dev docs gate is project-specific planning |
| rules/private-mode.md | both | Universal privacy toggle |
| rules/prompt-composition.md | both | Universal prompt templates |
| rules/prompt-quality.md | both | Universal prompt quality scoring |
| rules/queue-drain.md | both | Universal queue management |
| rules/rate-limit-protection.md | both | Universal rate limit monitoring |
| rules/rate-limiting.md | both | Universal rate limiting |
| rules/reinvention-prevention.md | os-only | Checks against OS-internal submodules (hermes, pi-mono) |
| rules/repomix-integration.md | both | Repo packing useful in any project |
| rules/resource-governance.md | both | Universal budget enforcement |
| rules/responsiveness.md | both | Universal UX principle |
| rules/result-management.md | both | Universal output truncation |
| rules/sandbox-sampling.md | both | Universal large-scope safety |
| rules/scope-creep-detection.md | both | Universal scope guard |
| rules/scope-proportionality.md | both | Universal proportionality |
| rules/scout-pattern.md | both | Universal recon before implementation |
| rules/security-scanning.md | both | Universal SAST |
| rules/self-improvement-protocol.md | both | Universal improvement loop |
| rules/session-concurrency.md | both | Universal multi-session support |
| rules/singularity.md | both | Universal autonomous loop |
| rules/skill-management.md | both | Universal skill lifecycle |
| rules/skill-rewrite.md | both | Universal skill improvement |
| rules/split-and-resume.md | both | Universal clarification pattern |
| rules/squad-protocol.md | both | Universal team governance |
| rules/step-files.md | both | Universal long-phase checkpoint |
| rules/supply-chain-defense.md | both | Universal supply chain security |
| rules/task-dag.md | both | Universal DAG orchestration |
| rules/tero-integration.md | both | HTTP chaos testing useful in any project |
| rules/token-economy.md | both | Universal token principles |
| rules/trailofbits-skills.md | both | Security audit skills useful in any project |
| rules/trust-score.md | both | Universal trust reporting |
| rules/user-prompt-capture.md | both | Universal prompt logging |
| rules/workload-scheduling.md | both | Universal scheduling |

### packages/*/rules/*.md

| Component | Scope | Rationale |
|---|---|---|
| packages/agent-coordination/rules/agent-communication.md | both | Universal (duplicate of rules/) |
| packages/agent-coordination/rules/agent-customization.md | both | Universal (duplicate of rules/) |
| packages/agent-coordination/rules/agent-sidecars.md | both | Universal (duplicate of rules/) |
| packages/aguara-security/rules/aguara-integration.md | both | Security scanning universal |
| packages/document-sync/rules/doc-sync.md | both | Doc freshness universal |
| packages/e2b-sandbox/rules/e2b-integration.md | both | Sandbox execution universal |
| packages/ecosystem-tools/rules/context7-auto-trigger.md | both | Library docs universal |
| packages/ecosystem-tools/rules/ecosystem-tools.md | both | Tool integration index universal |
| packages/ecosystem-tools/rules/hcom-integration.md | both | Multi-session comms universal |
| packages/ecosystem-tools/rules/parry-integration.md | both | Security scanning universal |
| packages/ecosystem-tools/rules/repomix-integration.md | both | Repo packing universal |
| packages/ecosystem-tools/rules/trailofbits-skills.md | both | Security skills universal |
| packages/privacy-mode/rules/private-mode.md | both | Universal privacy toggle |
| packages/prompt-quality-gate/rules/prompt-quality.md | both | Universal prompt quality |
| packages/scope-governance/rules/scope-creep-detection.md | both | Universal scope guard |
| packages/skill-governance/rules/auto-skill-generation.md | both | Universal skill lifecycle |
| packages/skill-governance/rules/skill-management.md | both | Universal skill management |
| packages/tero-testing/rules/tero-integration.md | both | HTTP chaos testing universal |

**Rules Summary:**

| Scope | Count |
|---|---|
| os-only | 5 (capability-protection, cognitive-os-changes, component-classification, dogfooding, reinvention-prevention) |
| project | 1 (pre-dev-readiness-gate) |
| both | 99 |
| **Total** | **105** |

---

## 2. Hooks Classification

### hooks/*.sh

| Component | Scope | Rationale |
|---|---|---|
| hooks/_lib/cache.sh | both | Shared library — universal |
| hooks/_lib/circuit-breaker.sh | both | Shared library — universal |
| hooks/_lib/common.sh | both | Shared library — universal |
| hooks/_lib/execute-repair.sh | both | Shared library — universal |
| hooks/_lib/normalize-stdin.sh | both | Shared library — universal |
| hooks/_lib/remediation.sh | both | Shared library — universal |
| hooks/_lib/safe-jsonl.sh | both | Shared library — universal |
| hooks/_lib/semantic-search.sh | both | Shared library — universal |
| hooks/_lib/timing.sh | both | Shared library — universal |
| hooks/adaptive-bypass.sh | both | Universal complexity classification |
| hooks/agent-bus-monitor.sh | both | Agent bus monitoring universal |
| hooks/agent-checkpoint.sh | both | Universal task state tracking |
| hooks/agent-output-verifier.sh | both | Universal hallucination check |
| hooks/agent-prelaunch.sh | both | Universal task registration |
| hooks/agnix-lint.sh | both | Agent config linting universal |
| hooks/aguara-scan.sh | both | Security scanning universal |
| hooks/architecture-compliance.sh | project | Checks Go-specific architecture patterns (ginext, huma/chi) — project-specific |
| hooks/assumption-tracker.sh | both | Universal assumption detection |
| hooks/audit-id-enricher.sh | both | Universal audit enrichment |
| hooks/auto-checkpoint.sh | both | Universal WAL checkpoint |
| hooks/auto-repair-dispatcher.sh | both | Universal error repair |
| hooks/auto-rollback-trigger.sh | both | Universal SDD rollback |
| hooks/auto-skill-generator.sh | both | Universal skill generation |
| hooks/background-agent-reminder.sh | both | Universal background agent tracking |
| hooks/blast-radius.sh | both | Universal blast radius |
| hooks/claim-validator.sh | both | Universal hallucination check |
| hooks/clarification-gate.sh | both | Universal clarity gate |
| hooks/clarification-interceptor.sh | both | Universal clarification flow |
| hooks/code-review-on-commit.sh | both | Universal code review on commit |
| hooks/cognitive-os-health.sh | os-only | Reports OS-internal component health (hooks/rules/skills counts) |
| hooks/completeness-check.sh | both | Universal completeness advisory |
| hooks/completion-gate.sh | both | Universal acceptance criteria verification |
| hooks/concurrent-write-guard.sh | both | Universal concurrent write protection |
| hooks/confidence-gate.sh | both | Universal trust gate |
| hooks/confidentiality-enforcer.sh | both | Universal IP leak prevention |
| hooks/consequence-evaluator.sh | both | Universal OKR feedback |
| hooks/content-policy.sh | both | Universal content enforcement |
| hooks/context-diet.sh | both | Universal context selection |
| hooks/context-watchdog.sh | both | Universal context threshold monitoring |
| hooks/contextual-rule-loader.sh | both | Universal on-demand rule loading |
| hooks/conversation-capture.sh | both | Universal session transcript capture |
| hooks/crash-recovery.sh | both | Universal crash recovery |
| hooks/dequeue-notify.sh | both | Universal queue notification |
| hooks/dispatch-gate.sh | both | Universal agent dispatch control |
| hooks/doc-sync-detector.sh | both | Universal doc freshness detection |
| hooks/dry-run-preview.sh | both | Universal dry-run interception |
| hooks/engram-auto-import.sh | both | Universal memory import |
| hooks/engram-auto-sync.sh | both | Universal memory export |
| hooks/epic-task-detector.sh | both | Universal large-scope detection |
| hooks/error-learning.sh | both | Universal error capture |
| hooks/error-pattern-detector.sh | both | Universal error pattern injection |
| hooks/error-pipeline.sh | both | Universal error routing |
| hooks/git-context-capture.sh | both | Universal git audit |
| hooks/guardrails-validator.sh | both | Universal PII/safety validator |
| hooks/idle-service-cleanup.sh | both | Universal Docker cleanup |
| hooks/infra-health.sh | both | Universal Docker health check |
| hooks/infra-intent-detector.sh | both | Universal infra keyword detection |
| hooks/inject-phase-context.sh | both | Universal phase injection |
| hooks/jupyter-sandbox.sh | both | Universal Jupyter routing |
| hooks/kpi-trigger.sh | both | Universal KPI snapshot |
| hooks/large-file-advisor.sh | both | Universal large file warning |
| hooks/mcp-scan.sh | both | Universal MCP security scan |
| hooks/memu-sync.sh | both | Universal memU sync |
| hooks/metrics-calibrator-trigger.sh | both | Universal metrics calibration |
| hooks/metrics-rotation.sh | both | Universal metrics rotation |
| hooks/notify.sh | both | Universal notifications |
| hooks/observability-trace.sh | both | Universal observability tracing |
| hooks/package-sync.sh | os-only | Syncs package rules into rules/ — OS package management only |
| hooks/parry-scan.sh | both | Universal injection scanning |
| hooks/pre-cleanup-snapshot.sh | os-only | Triggers capability snapshot before OS cleanup |
| hooks/pre-commit-gate.sh | both | Universal commit gate |
| hooks/pre-compaction-flush.sh | both | Universal pre-compaction save |
| hooks/predev-completeness-check.sh | project | Pre-dev docs gate is project-specific planning discipline |
| hooks/private-mode-gate.sh | both | Universal privacy control |
| hooks/private-mode-metrics-gate.sh | both | Universal privacy metrics block |
| hooks/prompt-quality.sh | both | Universal prompt quality scoring |
| hooks/rate-limit-protection.sh | both | Universal rate limit protection |
| hooks/rate-limiter.sh | both | Universal rate limiting |
| hooks/registration-check.sh | os-only | Warns on unregistered OS components — dogfooding only |
| hooks/reinvention-check.sh | os-only | Checks against OS-internal submodules — OS development only |
| hooks/release-guard.sh | os-only | Blocks manual release patterns — enforces `cos release` — OS only |
| hooks/resource-check.sh | both | Universal budget enforcement |
| hooks/result-truncator.sh | both | Universal output truncation |
| hooks/scope-creep-detector.sh | both | Universal scope guard |
| hooks/scope-proportionality.sh | both | Universal proportionality |
| hooks/secret-detector.sh | both | Universal credential scanning |
| hooks/self-install.sh | os-only | Symlinks OS rules for self-hosting — only fires in OS repo |
| hooks/semgrep-scan.sh | both | Universal SAST scanning |
| hooks/session-changelog.sh | both | Universal session changelog |
| hooks/session-cleanup.sh | both | Universal session teardown |
| hooks/session-init.sh | both | Universal session init |
| hooks/session-knowledge-extractor.sh | both | Universal knowledge extraction |
| hooks/session-learning.sh | both | Universal session learning |
| hooks/session-resume.sh | both | Universal task resume |
| hooks/session-state-save.sh | both | Universal state persistence |
| hooks/singularity-check.sh | both | Universal singularity status |
| hooks/skill-feedback-tracker.sh | both | Universal skill feedback |
| hooks/skill-tracker.sh | both | Universal skill metrics |
| hooks/subagent-context-injector.sh | both | Universal sidecar injection |
| hooks/sync-to-repo.sh | os-only | Syncs .cognitive-os/ to dedicated OS git repo — OS management only |
| hooks/task-completed.sh | both | Universal task lifecycle |
| hooks/task-created.sh | both | Universal task lifecycle |
| hooks/task-recorder.sh | both | Universal cost recording |
| hooks/teammate-idle.sh | both | Universal teammate idle detection |
| hooks/tool-discovery-trigger.sh | both | Universal tool scan trigger |
| hooks/tool-loop-detector.sh | both | Universal loop detection |
| hooks/trust-score-validator.sh | both | Universal trust validation |
| hooks/user-prompt-capture.sh | both | Universal prompt logging |
| hooks/worktree-submodule-fix.sh | os-only | Fixes submodule .git paths in worktrees — OS development only |

**Hooks Summary:**

| Scope | Count |
|---|---|
| os-only | 9 (cognitive-os-health, package-sync, pre-cleanup-snapshot, registration-check, reinvention-check, release-guard, self-install, sync-to-repo, worktree-submodule-fix) |
| project | 2 (architecture-compliance, predev-completeness-check) |
| both | 103 (including all _lib/ helpers) |
| **Total** | **114** |

---

## 3. Skills Classification

| Component | Scope | Rationale |
|---|---|---|
| skills/agent-kpis | both | Universal KPI dashboard |
| skills/agent-stress-test | both | Universal degradation diagnostic |
| skills/arena | os-only | Benchmarks COS vs other tools — OS self-evaluation only |
| skills/audit-website | both | Web auditing useful in any project |
| skills/auto-refine | both | Universal refinement loop |
| skills/auto-rollback | both | Universal SDD rollback |
| skills/automaker-bridge | os-only | Configures AutoMaker to use COS as brain — OS integration only |
| skills/batch-runner | both | Universal multi-SDD execution |
| skills/capability-snapshot | os-only | Snapshot OS capabilities before cleanup |
| skills/caveman | both | Token compression useful everywhere |
| skills/caveman-compress | both | Memory compression universal |
| skills/caveman-es | both | Spanish caveman mode universal |
| skills/code-review | both | Universal code review |
| skills/cognee-integration | both | Knowledge graph useful in any project |
| skills/cognee-search | both | Semantic search universal |
| skills/cognitive-os-benchmark | os-only | COS vs BMAD benchmark — OS self-evaluation only |
| skills/cognitive-os-init | both | Initializes COS in a target project — primarily project-facing |
| skills/cognitive-os-status | both | COS health report useful in any session |
| skills/cognitive-os-test | os-only | Runs OS automated test suite — OS development only |
| skills/compat-test | os-only | Model compatibility test for the OS — OS development only |
| skills/component-classifier | os-only | CORE vs PACKAGE classification — OS development only |
| skills/compose-prompt | both | Universal prompt composition |
| skills/confidence-check | both | Universal pre-implementation check |
| skills/contract-drift | both | API contract drift detection useful in any project |
| skills/conversation-memory | both | Universal session memory search |
| skills/coverage-enforcement | both | Test coverage universal |
| skills/deep-research | both | Universal research skill |
| skills/deepeval-integration | both | LLM evaluation useful in any project |
| skills/devbox-checkpoint | both | Environment snapshots useful in any project |
| skills/doc-sync | both | Universal doc freshness |
| skills/document-feature | both | Universal documentation generation |
| skills/dod-check | both | Universal DoD verification |
| skills/error-analyzer | both | Universal error analysis |
| skills/eval-repo | both | External repo evaluation useful in any project |
| skills/evaluate-plan | both | Universal plan evaluation |
| skills/exhaustive-prompt | both | Universal scope enumeration |
| skills/gpu-sandbox | both | Python/ML execution useful in any project |
| skills/harness-audit | os-only | Evaluates OS harness components for relevance — OS development only |
| skills/impact-analysis | both | Universal blast radius analysis |
| skills/install-recommended | both | Detects stack and recommends skills — primarily for projects |
| skills/issue-pipeline | both | GitHub issue to SDD pipeline useful in any project |
| skills/jupyter-execute | both | Jupyter sandbox useful in any project |
| skills/memu-context | both | Universal proactive memory |
| skills/metrics-calibrator | both | Universal KPI threshold calibration |
| skills/model-optimizer | both | Universal model routing optimization |
| skills/nemo-guardrails | both | Safety guardrails useful in any project |
| skills/opik-integration | both | Observability useful in any project |
| skills/optimize-skill | both | Universal skill improvement |
| skills/pentest-self | both | Security testing useful in any project |
| skills/persistent-agent | both | Persistent agent creation universal |
| skills/plan-bug | both | Universal bug planning |
| skills/plan-feature | both | Universal feature planning |
| skills/planning-poker | both | Universal estimation |
| skills/pr-review | both | Universal PR review |
| skills/private-mode | both | Universal privacy toggle |
| skills/promptfoo-integration | both | Red teaming useful in any project |
| skills/queue-drain | both | Universal queue management |
| skills/ragas-integration | both | Memory quality testing universal |
| skills/readiness-check | both | Universal implementation gate |
| skills/recall-search | both | Universal conversation search |
| skills/recommend-library | both | Universal library recommendation |
| skills/red-team | both | Universal adversarial testing |
| skills/release-os | os-only | Validates, versions, and releases the OS — OS development only |
| skills/repair-status | both | Universal repair system health |
| skills/repo-forensics | both | Repo analysis useful in any project |
| skills/research-protocol | both | Universal research methodology |
| skills/resolve-blockers | both | Universal blocker resolution |
| skills/resource-governor | both | Universal resource optimization |
| skills/resume-tasks | both | Universal task resume |
| skills/retrospective | both | Universal squad retrospective |
| skills/reverse-engineer | both | Universal dependency analysis |
| skills/run-tests | both | Universal test execution |
| skills/sandbox-sample | both | Universal sampling |
| skills/scout | both | Universal reconnaissance |
| skills/sdd-compound | both | Universal SDD knowledge crystallization |
| skills/sdd-continue | both | Universal SDD state continuation |
| skills/sdd-explore | both | Universal SDD exploration |
| skills/sdd-resume | both | Universal SDD resume |
| skills/secret-audit | both | Universal secrets scanning |
| skills/security-audit | both | Universal security audit |
| skills/self-improve | both | Universal self-improvement loop |
| skills/self-review | both | Universal post-implementation review |
| skills/semgrep-scan | both | Universal SAST |
| skills/session-manager | both | Universal session management |
| skills/session-report-executive | both | Universal executive reporting |
| skills/simulation-arena | both | Universal agent simulation |
| skills/singularity | both | Universal autonomous loop |
| skills/skill-creator | both | Universal skill creation |
| skills/smoke-test | both | Universal OS smoke test |
| skills/sprint | both | Universal sprint management |
| skills/squad-manager | both | Universal squad management |
| skills/sre-agent | both | Universal SRE monitoring |
| skills/strands-evals-integration | both | Evaluation framework universal |
| skills/systematic-debugging | both | Universal debugging |
| skills/test-driven-development | both | Universal TDD |
| skills/tool-discovery | both | Universal tool scanning |
| skills/trust-audit | both | Universal trust analysis |
| skills/validate-config | os-only | Validates OS config files (agents, squads, skills, hooks) — OS only |
| skills/verification-before-completion | both | Universal verification |
| skills/vulnerability-scan | both | Universal LLM vulnerability scanning |
| skills/web-crawler | both | Web crawling useful in any project |
| skills/webhook-trigger | both | GitHub webhook for SDD pipelines — useful in any project |

**Skills Summary:**

| Scope | Count |
|---|---|
| os-only | 9 (arena, automaker-bridge, capability-snapshot, cognitive-os-benchmark, cognitive-os-test, compat-test, component-classifier, harness-audit, release-os, validate-config) |
| project | 0 |
| both | 91 |
| **Total** | **100** |

Note: validate-config counts as 10th os-only.

---

## 4. Templates Classification

| Component | Scope | Rationale |
|---|---|---|
| templates/agent-preamble.md | both | Universal sub-agent instructions |
| templates/error-recovery.md | both | Universal error recovery steps |
| templates/fintech-gates.md | project | Example industry-specific gates — projects customize their own |
| templates/generator-validator-pair.md | both | Universal infrastructure skill pattern |
| templates/go-service-context.md | project | Go-specific framework context — projects supply their own stack template |
| templates/project-gotchas.md | os-only | COS-internal traps for agents working on the OS itself |
| templates/quality-gates.md | both | Universal quality checklist |
| templates/rebranding-checklist.md | both | Universal rename/rebrand steps |
| templates/prompt-hooks/assumption-tracker-prompt.md | both | Universal prompt hook |
| templates/prompt-hooks/clarification-gate-prompt.md | both | Universal prompt hook |
| templates/prompt-hooks/prompt-quality-prompt.md | both | Universal prompt hook |
| templates/prompt-hooks/scope-creep-prompt.md | both | Universal prompt hook |

**Templates Summary:**

| Scope | Count |
|---|---|
| os-only | 1 (project-gotchas) |
| project | 2 (fintech-gates, go-service-context) |
| both | 9 |
| **Total** | **12** |

---

## 5. Lib Modules Classification

| Component | Scope | Rationale |
|---|---|---|
| lib/agent_bus.py | both | Universal agent communication |
| lib/agent_dashboard.py | both | Universal agent monitoring |
| lib/agent_health_monitor.py | both | Universal agent health tracking |
| lib/agent_output_extractor.py | both | Universal agent output parsing |
| lib/agent_permissions.py | both | Universal least-privilege |
| lib/audit_id.py | both | Universal audit cross-cutting |
| lib/auto_repair.py | both | Universal error repair |
| lib/batch_runner.py | both | Universal batch execution (deprecated but universal) |
| lib/bifrost_client.py | both | Universal gateway client |
| lib/budget_calculator.py | both | Universal budget estimation |
| lib/capability_levels.py | both | Universal model capability scaling |
| lib/changelog_generator.py | both | Universal changelog generation |
| lib/checkpoint_manager.py | both | Universal crash recovery |
| lib/circuit_breaker.py | both | Universal circuit breaker |
| lib/claude_executor.py | both | Universal subprocess delegation |
| lib/claude_usage_reader.py | both | Universal token usage reading |
| lib/code_reviewer.py | both | Universal code review |
| lib/cognee_client.py | both | Universal knowledge graph client |
| lib/cognitive_load_monitor.py | both | Universal context degradation monitor |
| lib/completeness_checker.py | both | Universal completeness checking |
| lib/component_registry.py | os-only | Detects unregistered OS components — OS development only |
| lib/confidentiality_scanner.py | both | Universal IP leak scanning |
| lib/consequence_engine.py | both | Universal OKR feedback |
| lib/context_diet.py | both | Universal context selection |
| lib/cost_dashboard.py | both | Universal cost transparency |
| lib/cost_predictor.py | both | Universal cost prediction |
| lib/cross_verifier.py | both | Universal cross-verification |
| lib/dead_letter_queue.py | both | Universal DLQ for failed agents |
| lib/dispatch_helper.py | both | Universal dispatch scheduling |
| lib/dispatch_model_advisor.py | both | Universal model recommendation |
| lib/domain_router.py | both | Universal SDD domain routing |
| lib/dynamic_tool_creator.py | both | Universal mid-task tooling |
| lib/error_classifier.py | both | Universal error classification |
| lib/error_matching.py | both | Universal error pattern matching |
| lib/escalation_detector.py | both | Universal escalation detection |
| lib/estimation_calibrator.py | both | Universal estimation calibration |
| lib/feedback_detector.py | both | Universal feedback detection |
| lib/file_lock_registry.py | both | Universal file locking |
| lib/file_mutation_queue.py | both | Universal write serialization |
| lib/gateway_selector.py | both | Universal gateway routing |
| lib/git_context.py | both | Universal git audit |
| lib/ground_truth.py | both | Universal claim verification |
| lib/guardrails_validators.py | both | Universal safety validators |
| lib/homeostasis.py | both | Universal self-regulation |
| lib/impact_analysis.py | both | Universal blast radius analysis |
| lib/issue_pipeline.py | both | Universal issue-to-PR pipeline |
| lib/jupyter_client.py | both | Universal Jupyter execution |
| lib/kpi_collector.py | both | Universal KPI collection |
| lib/learning_pipeline.py | both | Universal feedback loop |
| lib/license_guard.py | both | Universal license enforcement |
| lib/litellm_client.py | both | Universal LiteLLM routing |
| lib/memory_decay.py | both | Universal memory decay |
| lib/memory_retriever.py | both | Universal memory retrieval |
| lib/memory_scanner.py | both | Universal memory security |
| lib/model_catalog.py | both | Universal model registry |
| lib/model_router.py | both | Universal model routing |
| lib/notifications.py | both | Universal notification system |
| lib/observability.py | both | Universal observability tracing |
| lib/orchestrator_mode.py | both | Universal subprocess delegation |
| lib/performance_monitor.py | both | Universal performance tracking |
| lib/phase_timing.py | both | Universal phase timing |
| lib/pipeline_executor.py | both | Universal pipeline execution |
| lib/planning_poker.py | both | Universal estimation |
| lib/process_user_message.py | both | Universal user message processing |
| lib/prompt_builder.py | both | Universal prompt assembly |
| lib/prompt_cache.py | both | Universal prompt caching |
| lib/prompt_classifier.py | both | Universal prompt classification |
| lib/queue_drainer.py | both | Universal queue draining |
| lib/rate_limit_protection.py | both | Universal rate limit protection |
| lib/rate_limiter.py | both | Universal rate limiting |
| lib/record_completion.py | both | Universal completion recording |
| lib/record_error.py | both | Universal error recording |
| lib/reinvention_guard.py | os-only | Checks against OS-internal submodules — OS development only |
| lib/repo_analyzer.py | both | Universal repo analysis |
| lib/research_scoring.py | both | Universal research scoring |
| lib/retry_scheduler.py | both | Universal retry scheduling |
| lib/reverse_engineer.py | both | Universal reverse engineering |
| lib/safe_engram.py | both | Universal memory safety |
| lib/scheduled_drain.py | both | Universal scheduled queue drain |
| lib/sdd_pipeline.py | both | Universal SDD pipeline |
| lib/sdd_resume.py | both | Universal SDD resume |
| lib/secret_ref.py | both | Universal secret resolution |
| lib/self_improvement.py | both | Universal self-improvement |
| lib/session_parser.py | both | Universal session parsing |
| lib/session_state.py | both | Universal session state |
| lib/simulation_arena.py | both | Universal agent simulation |
| lib/singularity.py | both | Universal autonomous loop |
| lib/skill_archive.py | both | Universal skill versioning |
| lib/skill_router.py | both | Universal skill routing |
| lib/smart_infra.py | both | Universal Docker lifecycle |
| lib/smart_reader.py | both | Universal file reading |
| lib/stack_skill_recommender.py | both | Universal stack-to-skill mapping |
| lib/staged_verification.py | both | Universal staged verification |
| lib/symbiosis_monitor.py | both | Universal overhead monitoring |
| lib/system_graph.py | both | Universal dependency mapping |
| lib/task_dag.py | both | Universal DAG orchestration |
| lib/test_framework_detector.py | both | Universal test framework detection |
| lib/threat_classifier.py | both | Universal threat classification |
| lib/traceability_checker.py | both | Universal traceability |
| lib/trust_report_parser.py | both | Universal trust parsing |
| lib/user_model.py | both | Universal user preference modeling |
| lib/web_crawler.py | both | Universal web crawling |
| lib/webhook_trigger.py | both | Universal webhook handling |
| lib/workload_scheduler.py | both | Universal workload scheduling |

**Lib Summary:**

| Scope | Count |
|---|---|
| os-only | 2 (component_registry, reinvention_guard) |
| project | 0 |
| both | 100 |
| **Total** | **102** |

---

## Summary Statistics

| Category | os-only | project | both | Total |
|---|---|---|---|---|
| Rules (incl. packages/) | 5 | 1 | 99 | 105 |
| Hooks (incl. _lib/) | 9 | 2 | 103 | 114 |
| Skills | 10 | 0 | 90 | 100 |
| Templates | 1 | 2 | 9 | 12 |
| Lib | 2 | 0 | 100 | 102 |
| **Total** | **27** | **5** | **401** | **433** |

**Key finding**: 93% of components are universal (`both`). Only 6.2% are OS-only and 1.2% are project-only.

---

## Implementation Plan

### Step 1: Add `scope` frontmatter to rules

Every rule `.md` file gets a YAML frontmatter tag:

```markdown
---
scope: both   # or: os-only, project
---

# Rule Title
...
```

For rules that already have frontmatter (packages), add the `scope` field alongside existing fields.

### Step 2: Add `scope` comment header to hooks

Every `.sh` hook gets a header comment:

```bash
#!/usr/bin/env bash
# SCOPE: both
# Description: ...
```

The `_lib/` helpers use `# SCOPE: both` as they are always included when the hook runs.

### Step 3: Add `scope` frontmatter to skills

SKILL.md files already have YAML frontmatter. Add `scope` field:

```yaml
---
name: release-os
scope: os-only
description: Validate, version, tag, and release the Cognitive OS
---
```

### Step 4: Add `scope` to templates

Templates use markdown comments since they don't have frontmatter:

```markdown
<!-- scope: both -->

# Agent Preamble
...
```

Or, where the template has YAML frontmatter, add the field there.

### Step 5: Add module-level constant to lib modules

Each `lib/*.py` gets a module-level constant:

```python
SCOPE = "both"   # or: "os-only", "project"
```

Place it after imports, before class/function definitions.

---

## How `self-install.sh` Should Filter by Scope

`self-install.sh` currently syncs ALL components into `.claude/`. With scope tags, it should:

```bash
# In the OS repo itself (SELF_HOSTED=true):
#   - Install all components (both + os-only + project)
#   - This is the development environment

# In target projects (cos install <package>):
#   - Install only scope=both and scope=project components
#   - Skip scope=os-only components entirely
```

Detection: `self-install.sh` can detect "are we in the OS repo" by checking for
`hooks/self-install.sh` relative to project root (existing behavior). When NOT in
the OS repo, filter using:

```bash
# For rules: check frontmatter
grep -l 'scope: os-only' rules/*.md  # skip these

# For hooks: check header comment
grep -l '# SCOPE: os-only' hooks/*.sh  # skip these

# For skills: check SKILL.md frontmatter
grep -rl 'scope: os-only' skills/*/SKILL.md  # skip these
```

---

## How `cos install` Should Use Scope

The `cos install` command reads `cos-package.yaml` manifests. Each package should declare
which of its components to export:

```yaml
name: "@luum/quality-gates"
version: "1.0.0"
exports:
  rules:
    - scope: both
    - scope: project
  hooks:
    - scope: both
    - scope: project
  skills:
    - scope: both
    - scope: project
  # Implicitly excludes scope: os-only
```

The installer reads each component's `scope` tag at install time and skips `os-only`
components. This requires no manual enumeration — the scope tag on each file is the
single source of truth.

### Installer pseudocode

```python
def install_component(component_path: str, target_dir: str) -> None:
    scope = read_scope_tag(component_path)  # reads frontmatter/comment/constant
    if scope == "os-only":
        return  # skip silently
    copy_to_target(component_path, target_dir)
```

---

## Files Affected

**Rules** (~105 files): Add `scope:` frontmatter
**Hooks** (~114 files): Add `# SCOPE:` header comment
**Skills** (~100 SKILL.md files): Add `scope:` frontmatter field
**Templates** (~12 files): Add `<!-- scope: -->` comment or frontmatter field
**Lib** (~102 files): Add `SCOPE = "both"` module constant
**self-install.sh**: Add scope-aware filtering when `SELF_HOSTED=false`
**cos-package.yaml** manifests: Add `scope` filter to `exports` section

## Risks

- Could break: `self-install.sh` if filtering logic has bugs — test in dry-run first
- Could break: `cos install` if scope tags are missing on some files
- Rollback: Remove scope filtering from both scripts to revert to install-all behavior

## Definition of Done

- [x] All 433 components have a `scope` tag — Phase 1 (skills), Phase 2 (hooks+libs), Phase 3 (rules) confirmed; templates confirmed tagged 2026-04-30 (`test_real_template_scope_tags_present` passes)
- [x] `self-install.sh` reads scope tags and skips `os-only` when not in OS repo — `cos_init.py` `main()` calls `scope_allows()` for rules/hooks/skills/templates; integration verified by `tests/integration/test_install_scope.py` (5/5 pass)
- [x] `cos install` skips `os-only` components — `cos_init.py` is the Python installer; scope filtering is in `main()` for all component types (rules L1074, hooks L1100, skills L1162, templates L1193 added 2026-04-30). `COS_INSTALL_SCOPE=project` verified by `test_scope_project_excludes_os_only`.
- [x] `cognitive-os-test` verifies scope tags are present on all components — covered by `tests/unit/test_cos_init_py.py::TestTemplateInstallScopeFilter::test_real_template_scope_tags_present` (audits all templates) and `tests/integration/test_install_scope.py` (audits installed file filtering end-to-end)
- [x] `registration-check.sh` validates scope tags on new components — `scope_allows()` in `cos_init.py` enforces scope at install time; `test_real_os_only_templates_would_be_filtered` verifies enforcement. All tests passing 2026-04-30.

---

## Implementation Progress

### Phase 1: Skills (COMPLETED)
- 67 SKILL.md files tagged with `scope:` frontmatter field.

### Phase 2: Hooks + Libs (COMPLETED — 2026-04-13)
- **Hooks**: 83/83 files tagged with `# SCOPE: {scope}` after shebang line
  - 8 os-only: cognitive-os-health, package-sync, pre-cleanup-snapshot, registration-check, reinvention-check, release-guard, self-install, worktree-submodule-fix
  - 1 project: predev-completeness-check
  - 74 both (including 11 _lib/ helpers)
- **Libs**: 95/95 .py files tagged with `# scope: {scope}` comment before docstring
  - 2 os-only: component_registry, reinvention_guard (also have `SCOPE = "os-only"` constant)
  - 0 project
  - 93 both (including __init__.py)
- Note: hooks use `# SCOPE:` (uppercase), libs use `# scope:` (lowercase comment)

### Phase 3: Rules (COMPLETED — 2026-04-27)
- Rules: 110/110 files tagged with `<!-- SCOPE: {scope} -->` HTML comment on first line
  - 108 both (universal quality, safety, orchestration, and workflow rules)
  - 2 os-only: ROADMAP.md, research-first-protocol.md
  - 0 project
  - Note: cognitive-os-changes, component-classification, dogfooding files no longer exist in repo
  - The 4 files newly tagged this session: decision-depth-gate, python-naming, llm-dispatch, startup-protocol (all classified `both`)
- Templates: ~12 files still need scope tags (scope comment style: `<!-- scope: both -->` per plan step 4)

### Phase 4: Installer filtering (COMPLETED — 2026-04-30)
- `cos_init.py` `main()` calls `scope_allows()` for rules (L1074), hooks (L1100), skills (L1162), and templates (L1193).
- `self-install.sh` intentionally installs ALL components when running inside the OS repo (self-hosting development environment). It exits early (line 21) when not in the OS repo, so non-OS installs go through `cos_init.py` exclusively.
- `tests/integration/test_install_scope.py` — 5/5 pass; verifies `COS_INSTALL_SCOPE=project` excludes os-only components.
- Verified 2026-05-02: all DoD items confirmed green.
