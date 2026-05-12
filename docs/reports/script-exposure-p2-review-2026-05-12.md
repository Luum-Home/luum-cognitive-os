# Script Exposure P2 Review — 2026-05-12

Source: `scripts/cos-script-exposure-audit --json` after P0/P1 closure, runtime-route dispositions, and Python backend internalization.

## Result

| Bucket | Count | Meaning |
|---|---:|---|
| `OK-classified-maintainer` | 48 | Maintainer tools already have lifecycle metadata or override rationale; no skill required by default. |
| `OK-documented-route` | 91 | Hook/router/operator route has an explicit manual disposition; no skill required by default. |
| `OK-internal-backend` | 73 | Python backend helper is owned by wrapper/orchestrator consumers; direct skill surface would be noise. |
| `P2-script-orchestrated` | 34 | Remaining top-level or shell/no-extension workflows called by scripts but not yet classified/promoted. |
| `P2-evidence-only` | 68 | Docs/tests evidence, no runtime route. |
| `P2-doc-only` | 27 | Documentation-only references. |
| `P2-test-only` | 17 | Test-only references. |

Total remaining P2: **146**.

## What changed in this slice

- Resolved the 81 `P2-runtime-route-undocumented` rows through explicit `documented_route` dispositions.
- Added `internal_backend` as an ADR-283 disposition for maintainer tools that are implementation backends, not agent-facing skills.
- Classified 73 Python `P2-script-orchestrated` rows as `OK-internal-backend`; these are consumed by wrappers/orchestrators and should not become individual skills by default.
- Left the 34 remaining `P2-script-orchestrated` rows unresolved because they are mostly shell/no-extension operator workflows and need a promote-vs-internal decision, not a blind backend label.
- Left doc/test/evidence-only rows unresolved; the safe next step is to inspect the owning docs/tests before deleting or archiving anything.

## Remaining P2-script-orchestrated candidates

- `scripts/auto-update-projects.sh` — consumers: .claude/settings.local.json, docs/adrs/ADR-093-simplify-profiles.md, docs/architecture/bootstrap-portability.md
- `scripts/component-lint.sh` — consumers: docs/adrs/ADR-149-primitive-duplication-audit.md, docs/architecture/bootstrap-portability.md, docs/architecture/core-vs-extensions-audit-2026-04-20.md
- `scripts/cos-branch-lease` — consumers: docs/adrs/ADR-116-multi-session-coordination-primitives.md, docs/architecture/harness-action-receipts.md, scripts/cos_architecture_readiness.py
- `scripts/cos-demotion-proposer` — consumers: docs/adrs/ADR-180-lifecycle-promotion-activation.md, scripts/cos_demotion_proposer.py
- `scripts/cos-doctor-work-inventory.sh` — consumers: docs/adrs/ADR-111-core-consumer-concurrency-safety-boundary.md, docs/architecture/concurrency-safety-core-consumer-contract.md, scripts/cos-doctor-concurrency.sh
- `scripts/cos-engram-cloud-enroll` — consumers: docs/SESSION-HANDOFF-2026-05-04.md, docs/adrs/ADR-139-account-agnostic-multi-provider-runtime.md, docs/adrs/ADR-141-engram-cloud-cross-instance-replication.md
- `scripts/cos-gate-stack.sh` — consumers: scripts/cos-merge-queue-worker.sh, tests/red_team/portability/test_cos-gate-stack.py
- `scripts/cos-governed-agent.sh` — consumers: docs/adrs/ADR-118-multi-ide-swarm-testbed.md, scripts/cos_architecture_readiness.py, tests/behavior/test_phase2_wiring.py
- `scripts/cos-headless-publication` — consumers: scripts/cos_architecture_readiness.py, tests/behavior/test_headless_protected_publication.py
- `scripts/cos-headless-runtime-contract` — consumers: scripts/cos-headless-pipeline, tests/contracts/test_headless_runtime_contract.py
- `scripts/cos-headless-safe-mode` — consumers: docs/architecture/surface-5-and-secure-cosd-roadmap.md, scripts/cos-headless-pipeline, scripts/cos_architecture_readiness.py
- `scripts/cos-instance-init` — consumers: manifests/cos-instance-implementation-phases.yaml, manifests/cos-instance-profiles.yaml, manifests/primitive-consumer-availability.yaml
- `scripts/cos-python-stdin-antipattern-audit` — consumers: docs/architecture/python-stdin-heredoc-trap.md, scripts/cos-ci-local.sh
- `scripts/cos-registry.sh` — consumers: .claude/settings.local.json, docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/architecture/harness-adoption-gap/scripts-audit-B-init-bootstrap.md
- `scripts/cos-repair` — consumers: scripts/cos_repair.py
- `scripts/cos-run-task` — consumers: scripts/cos_architecture_readiness.py, scripts/cos_run_task.py, tests/behavior/test_phase2_wiring.py
- `scripts/cos-update.sh` — consumers: manifests/adr-closure-metadata.yaml, docs/SESSION-ADR-CLOSURE-2026-05-04.md, docs/SESSION-HANDOFF-2026-04-17.md
- `scripts/cos-validation-capsule.sh` — consumers: docs/adrs/ADR-109-validation-capsule-worktree-isolation.md, docs/adrs/ADR-113-validation-capsule-liveness.md, docs/adrs/ADR-129-safe-worktree-removal.md
- `scripts/cos-weekly-primitive-gap.sh` — consumers: docs/adrs/ADR-131-local-ci-migration.md, scripts/install-launchd-jobs.sh
- `scripts/cos-weekly-public-metrics.sh` — consumers: docs/adrs/ADR-131-local-ci-migration.md, scripts/install-launchd-jobs.sh
- `scripts/credibility-audit.sh` — consumers: docs/acc/latest.md, scripts/install-credibility-tools.sh
- `scripts/doctor.sh` — consumers: .claude/settings.json, .codex/hooks.json, cognitive-os.yaml
- `scripts/git-coop.sh` — consumers: docs/adrs/ADR-089-multi-session-git-coordination.md, docs/adrs/ADR-098-multi-agent-file-coordination.md, docs/adrs/ADR-190-harness-action-receipts.md
- `scripts/install-credibility-tools.sh` — consumers: docs/acc/latest.md, scripts/credibility-audit.sh
- `scripts/install-syft-grype.sh` — consumers: docs/acc/latest.md, docs/adrs/ADR-212-cross-stack-license-audit-toolchain.md, docs/manual-tests/cross-stack-license-audit-cli.md
- `scripts/install-trivy.sh` — consumers: manifests/tool-discovery-preuse.yaml, docs/acc/latest.md, docs/adrs/ADR-212-cross-stack-license-audit-toolchain.md
- `scripts/license-audit-trivy.sh` — consumers: manifests/tool-discovery-preuse.yaml, docs/acc/latest.md, docs/adrs/ADR-212-cross-stack-license-audit-toolchain.md
- `scripts/manifest-check.sh` — consumers: docs/adrs/ADR-168-cross-device-dependency-installation.md, docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/manual-tests/local-connected-systems-validation.md
- `scripts/merge-settings.sh` — consumers: manifests/dependencies.yaml, docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/architecture/harness-adoption-gap/scripts-audit-B-init-bootstrap.md
- `scripts/proof-drill-evidence-record` — consumers: docs/adrs/ADR-167-proof-drill-selector-and-acc-evidence-adapter.md, docs/architecture/proof-drill-and-smoke-opt-in-primitives.md, docs/manual-tests/headless-docker-service-runtime.md
- `scripts/register-mcps.sh` — consumers: manifests/adr-closure-metadata.yaml, manifests/product-zones.yaml, docs/SESSION-ADR-CLOSURE-2026-05-04.md
- `scripts/so-emergency-stop.sh` — consumers: docs/adrs/ADR-028.md, docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/architecture/driver-specific-script-surfaces.md
- `scripts/stash-leak-alarm.sh` — consumers: docs/architecture/concurrency-safety-core-consumer-contract.md, docs/architecture/multi-session-orchestration-audit-2026-05-02.md, scripts/cos-doctor-concurrency.sh
- `scripts/test-cognitive-os.sh` — consumers: docs/adrs/ADR-072-test-lane-taxonomy.md, docs/adrs/ADR-073-test-architecture-role-registry.md, docs/testing-cognitive-os-suite.md

## Remaining doc/test/evidence-only cleanup backlog

### P2-evidence-only (68)

- `scripts/adr100_live_headroom_check.py` — evidence: docs/adrs/ADR-100-resource-governed-test-execution.md, tests/integration/test_adr100_live_headroom_check.py
- `scripts/adr_verification_audit.py` — evidence: manifests/primitive-consumer-availability.yaml, docs/architecture/adr-verification-evidence-contract.md, tests/audit/test_adr_contracts.py
- `scripts/agent-orchestration-boundary-audit.py` — evidence: manifests/capability-coverage.yaml, manifests/control-plane-audits.yaml, docs/adrs/ADR-251-agent-orchestration-adapter-boundary.md
- `scripts/check_absolute_paths.py` — evidence: docs/architecture/path-portability-and-privacy.md, tests/unit/test_check_absolute_paths.py
- `scripts/check_lib_wiring.py` — evidence: docs/quality/test-coverage-report.md, rules/python-naming.md, tests/architecture/test_wiring.py
- `scripts/cos-adr-implementation-audit.py` — evidence: manifests/adr-implementation-runtime-allowlist.yaml, manifests/control-plane-audits.yaml, docs/adrs/ADR-281-adr-implementation-reality-audit.md
- `scripts/cos-adr-partial-audit` — evidence: manifests/control-plane-audits.yaml, docs/00-MOCs/operations.md, docs/adrs/ADR-275-closure-and-projection-primitives.md
- `scripts/cos-audit-archive` — evidence: docs/SESSION-HANDOFF-2026-05-04.md, docs/adrs/ADR-142-compliance-audit-air-gapped-surface.md, docs/architecture/gdpr-erasure-procedure.md
- `scripts/cos-capability-matrix` — evidence: manifests/capability-coverage.yaml, manifests/control-plane-audits.yaml, docs/adrs/ADR-252-capability-coverage-matrix-and-feature-reality-ledger.md
- `scripts/cos-cloud-worker-bootstrap.sh` — evidence: manifests/primitive-behavior-evidence.yaml, README.md, docs/adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md
- `scripts/cos-counsel-outreach-draft` — evidence: docs/adrs/ADR-270-legal-compliance-workflow-automation.md, docs/runbooks/legal-review-workflow.md, tests/unit/test_cos_counsel_outreach_draft.py
- `scripts/cos-deferred-tool-plan` — evidence: docs/adrs/ADR-236-deferred-tool-loading-and-toolsearch.md, tests/behavior/test_deferred_tool_plan_cli.py
- `scripts/cos-deps-install.sh` — evidence: manifests/tool-discovery-preuse.yaml, docs/adrs/ADR-168-cross-device-dependency-installation.md, docs/adrs/ADR-216-tool-discovery-pre-use-gate.md
- `scripts/cos-events.sh` — evidence: manifests/adr-closure-metadata.yaml, docs/SESSION-ADR-CLOSURE-2026-05-04.md, tests/red_team/portability/test_cos-events.py
- `scripts/cos-external-source-fetch` — evidence: docs/adrs/ADR-255-feature-to-external-tool-due-diligence.md, tests/unit/test_feature_tool_due_diligence_cli.py
- `scripts/cos-feature-tool-scan` — evidence: docs/adrs/ADR-255-feature-to-external-tool-due-diligence.md, tests/unit/test_feature_tool_due_diligence_cli.py
- `scripts/cos-filter-repo-wrap.sh` — evidence: manifests/capability-coverage.yaml, manifests/history-rewrite-ledger.yaml, manifests/postmortem-regression-audit.yaml
- `scripts/cos-ghost-skills.sh` — evidence: docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/architecture/functional-audit/sprint-5-observability.md, tests/behavior/test_ghost_skills_check.py
- `scripts/cos-governed-edit.sh` — evidence: docs/adrs/ADR-118-multi-ide-swarm-testbed.md, tests/chaos/test_multi_ide_swarm_safety.py, tests/unit/test_governed_wrappers.py
- `scripts/cos-headless-pipeline` — evidence: docs/architecture/standalone-ship-readiness-2026-05-06.md, docs/architecture/surface-5-and-secure-cosd-roadmap.md, docs/business/master-plan-checklist.md
- `scripts/cos-history-sanitization-smoke.sh` — evidence: manifests/primitive-coherence.yaml, docs/legal/pre-public-readiness-checklist.md, docs/onboarding/walkthrough.md
- `scripts/cos-homebrew-local-canary` — evidence: docs/architecture/standalone-ship-readiness-2026-05-06.md, docs/release/v1.0-release-criteria.md, tests/contracts/test_standalone_distribution_contract.py
- `scripts/cos-init-global.sh` — evidence: docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/architecture/functional-audit/scorecard-install-scripts.md, docs/architecture/harness-adoption-gap/scripts-audit-B-init-bootstrap.md
- `scripts/cos-orphan-process-audit.py` — evidence: docs/adrs/ADR-279-orphan-repo-scan-process-audit.md, docs/business/master-plan-checklist.md, tests/audit/test_python_naming.py
- `scripts/cos-policy-settings-projection` — evidence: manifests/policy-as-code.yaml, docs/adrs/ADR-234-approval-policies-as-code.md, docs/architecture/provenance.md
- `scripts/cos-portable-ai-consumer-package-smoke` — evidence: docs/architecture/portable-ai-consumer-package-spec.md, docs/business/master-plan-checklist.md, tests/contracts/test_portable_ai_consumer_package.py
- `scripts/cos-portable-ai-real-consumer-smoke` — evidence: manifests/primitive-authority.yaml, docs/adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md, tests/contracts/test_primitive_closure_smokes.py
- `scripts/cos-postgres-local.sh` — evidence: manifests/primitive-behavior-evidence.yaml, docs/adrs/ADR-045-postgres-local-daemon.md, tests/contracts/test_projectable_script_surface_evidence.py
- `scripts/cos-postmortem-regression-audit` — evidence: manifests/capability-coverage.yaml, manifests/control-plane-audits.yaml, docs/adrs/ADR-247-manifest-driven-postmortem-regression-audits.md
- `scripts/cos-pre-public-risk-audit` — evidence: manifests/control-plane-audits.yaml, manifests/primitive-behavior-contracts.yaml, manifests/primitive-coherence.yaml
- `scripts/cos-primitive-authority-audit` — evidence: docs/adrs/ADR-276-primitive-authority-write-effects.md, docs/adrs/ADR-281-adr-implementation-reality-audit.md, tests/red_team/portability/test_cos-primitive-authority-audit.py
- `scripts/cos-primitive-fitness` — evidence: docs/architecture/primitive-fitness-evaluation-contract.md, docs/architecture/ssr-agentic-primitive-enablement-gaps.md, docs/business/master-plan-checklist.md
- `scripts/cos-private-content-audit` — evidence: docs/adrs/ADR-202-private-content-cross-harness-portability-boundary.md, docs/business/master-plan-checklist.md, tests/behavior/test_private_content_projection_guard.py
- `scripts/cos-release-external-readiness` — evidence: docs/adrs/ADR-198-release-external-readiness-gate.md, tests/contracts/test_release_external_readiness.py
- `scripts/cos-script-exposure-audit` — evidence: docs/adrs/ADR-283-script-exposure-audit-and-invocation-ratchet.md, tests/behavior/test_script_exposure_audit_cli.py
- `scripts/cos-sessions.sh` — evidence: docs/architecture/bootstrap-portability.md, docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/runbooks/so-incident-runbook.md
- `scripts/cos-startup-recover.sh` — evidence: docs/adrs/ADR-104-startup-circuit-breaker.md, docs/incidents/2026-05-01-session-multi-spawn-hang.md, docs/manual-tests/claude-code-startup-hang-regression.md
- `scripts/cos-subprocess-timeout-audit.py` — evidence: manifests/control-plane-audits.yaml, manifests/documentation-truth-claims.yaml, manifests/primitive-consumer-availability.yaml
- `scripts/cos-tool-adoption-audit` — evidence: manifests/external-tools-adoption.yaml, docs/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md, docs/architecture/external-tool-intelligence-plane.md
- `scripts/cos-tool-inventory` — evidence: docs/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md, tests/behavior/test_external_tool_intelligence_cli.py
- `scripts/cos-tool-radar-render` — evidence: docs/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md, docs/architecture/external-tool-intelligence-plane.md, tests/behavior/test_external_tool_intelligence_cli.py
- `scripts/cos-tool-research-check` — evidence: docs/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md, docs/architecture/external-tool-intelligence-plane.md, tests/behavior/test_external_tool_intelligence_cli.py
- `scripts/cos-uspto-patent-search` — evidence: docs/adrs/ADR-270-legal-compliance-workflow-automation.md, docs/runbooks/legal-review-workflow.md, tests/unit/test_uspto_patent_search.py
- `scripts/cos-uspto-trademark-search` — evidence: docs/adrs/ADR-270-legal-compliance-workflow-automation.md, docs/runbooks/legal-review-workflow.md, tests/unit/test_uspto_trademark_search.py
- `scripts/cos_chaos_template.py` — evidence: docs/adrs/ADR-041.md, rules/python-naming.md, tests/unit/test_chaos_template.py
- `scripts/cos_concurrent_status.py` — evidence: docs/adrs/ADR-238-tier-1-4-followup-bug-tracking.md, docs/architecture/multi-session-orchestration-audit-2026-05-02.md, tests/red_team/portability/cos_concurrent_status_test.py
- `scripts/cos_evolve_tick.py` — evidence: docs/adrs/ADR-262-evolve-loop-spike.md, tests/unit/test_cos_evolve_tick.py
- `scripts/cos_governed_self_improvement.py` — evidence: docs/adrs/ADR-262-evolve-loop-spike.md, docs/architecture/key-learnings-capture-self-improvement.md, docs/architecture/primitive-fitness-evaluation-contract.md
- `scripts/cos_profile_bootstrap.py` — evidence: docs/architecture/memory-lifecycle.md, tests/behavior/test_profile_bootstrap_cli.py
- `scripts/cos_test_quality_audit.py` — evidence: docs/adrs/ADR-072-test-lane-taxonomy.md, docs/adrs/ADR-073-test-architecture-role-registry.md, docs/business/conversation-reality-audit-2026-04-30.md
- `scripts/cos_watch.py` — evidence: manifests/adr-closure-metadata.yaml, docs/SESSION-ADR-CLOSURE-2026-05-04.md, docs/adrs/ADR-034-harness-agnostic-live-streaming.md
- `scripts/install-aguara.sh` — evidence: .claude/settings.local.json, manifests/primitive-behavior-evidence.yaml, docs/adrs/ADR-168-cross-device-dependency-installation.md
- `scripts/install-goreleaser.sh` — evidence: manifests/dependencies.yaml, docs/adrs/ADR-191-cos-binary-release-pipeline.md, docs/architecture/standalone-ship-readiness-2026-05-06.md
- `scripts/install-mcp-scan.sh` — evidence: .claude/settings.local.json, manifests/primitive-behavior-evidence.yaml, docs/adrs/ADR-168-cross-device-dependency-installation.md
- `scripts/install-pre-commit.sh` — evidence: docs/architecture/core-vs-extensions-audit-2026-04-20.md, docs/architecture/harness-adoption-gap/scripts-audit.md, docs/onboarding-wizard-design.md
- `scripts/measure_expansion.py` — evidence: docs/measurements/stage2-expansion-baseline.md, tests/unit/test_measure_expansion.py
- `scripts/plan-lock.sh` — evidence: docs/SESSION-HANDOFF-2026-05-04.md, docs/adrs/ADR-106-multi-session-safety-primitives.md, tests/behavior/test_plan_lock_cli.py
- `scripts/portable_ai_real_consumer_smoke.py` — evidence: manifests/primitive-authority.yaml, docs/adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md, docs/architecture/primitive-authority-write-effects.md
- `scripts/primitive-behavior-audit.py` — evidence: manifests/capability-coverage.yaml, manifests/control-plane-audits.yaml, docs/adrs/ADR-249-primitive-behavioral-proof-anti-overfit-tests.md
- `scripts/primitive-coherence-audit.py` — evidence: manifests/capability-coverage.yaml, manifests/control-plane-audits.yaml, manifests/primitive-behavior-contracts.yaml
- `scripts/run_skill_efficacy_smoke.py` — evidence: docs/architecture/agentic-mastery-operations.md, tests/unit/test_run_skill_efficacy_smoke.py
- `scripts/session-leak-diagnostic.sh` — evidence: docs/adrs/ADR-047-session-lifecycle-management.md, docs/architecture/bootstrap-portability.md, tests/behavior/test_secondary_script_portability.py
- `scripts/setup-git-hooks.sh` — evidence: .claude/settings.local.json, manifests/dependencies.yaml, manifests/primitive-behavior-evidence.yaml
- `scripts/skill-router-retrieval-audit.py` — evidence: manifests/capability-coverage.yaml, manifests/control-plane-audits.yaml, docs/adrs/ADR-250-skill-router-retrieval-adapter-boundary.md
- `scripts/so-vitals.sh` — evidence: docs/adrs/ADR-028.md, docs/adrs/ADR-028a.md, docs/adrs/ADR-028b.md
- `scripts/statusline-coverage.sh` — evidence: docs/agent-capability-coverage.md, tests/red_team/portability/test_statusline-coverage.py
- `scripts/validate_tier_filter.py` — evidence: manifests/hook-quality.yaml, docs/legal/operator-data-scan.md, docs/measurements/tier-filter-validation-2026-05-01.md
- `scripts/version.sh` — evidence: .claude/settings.local.json, docs/architecture/core-vs-extensions-audit-2026-04-20.md, tests/unit/test_bump_version.py

### P2-doc-only (27)

- `scripts/audit-consumer-dependence.sh` — evidence: docs/legal/operator-data-scan.md, docs/legal/pre-public-readiness-checklist.md
- `scripts/audit_engram_topic_keys.py` — evidence: docs/adrs/ADR-246-release-transaction-freeze.md
- `scripts/auto-tune-routing` — evidence: manifests/primitive-consumer-availability.yaml, docs/adrs/ADR-053-dispatch-auto-optimizer.md
- `scripts/cos-adoption-unfreeze` — evidence: docs/adrs/ADR-270-legal-compliance-workflow-automation.md, docs/runbooks/legal-review-workflow.md
- `scripts/cos-branch-release` — evidence: docs/adrs/ADR-182-branch-ownership-lock.md
- `scripts/cos-claim-signature-audit` — evidence: docs/adrs/ADR-134-headless-self-improvement-proposer.md, docs/architecture/claim-signature-audit.md, docs/architecture/consumer-fleet-audit.md
- `scripts/cos-context-budget-report` — evidence: docs/architecture/context-budget-observability.md, docs/architecture/context-rot-token-budget-controls.md
- `scripts/cos-default-visible-reducer` — evidence: docs/architecture/boring-reliability-control-plane.md, docs/architecture/cognitive-prosthesis.md
- `scripts/cos-doctor-concurrency.sh` — evidence: docs/adrs/ADR-108-concurrent-agent-safety-layer.md, docs/adrs/ADR-111-core-consumer-concurrency-safety-boundary.md, docs/architecture/concurrency-safety-core-consumer-contract.md
- `scripts/cos-documentation-truth-audit` — evidence: docs/adrs/ADR-277-documentation-truth-control.md, docs/architecture/documentation-truth-control.md
- `scripts/cos-engram-import-propose` — evidence: manifests/agentic-primitive-registry.lock.yaml, manifests/flow-contract-schema.yaml, manifests/primitive-contracts.yaml
- `scripts/cos-export-consumer-improvement-proposals` — evidence: manifests/primitive-authority.yaml, docs/architecture/consumer-fleet-audit.md, docs/architecture/cross-instance-learning-runway.md
- `scripts/cos-false-positive-ledger` — evidence: docs/adrs/ADR-134-headless-self-improvement-proposer.md, docs/architecture/boring-reliability-control-plane.md, docs/architecture/cognitive-prosthesis.md
- `scripts/cos-fleet-confidence-export` — evidence: docs/adrs/ADR-210-fleet-aggregated-confidence-boundary.md
- `scripts/cos-import-consumer-improvement-proposals` — evidence: manifests/primitive-authority.yaml, docs/architecture/consumer-fleet-audit.md, docs/architecture/cross-instance-learning-runway.md
- `scripts/cos-pr-review.sh` — evidence: README.md, docs/adrs/ADR-130-suspend-claude-api-workflows.md, docs/adrs/ADR-131-local-ci-migration.md
- `scripts/cos-primitive-fitness-ledger` — evidence: docs/architecture/primitive-fitness-evaluation-contract.md, docs/architecture/ssr-agentic-primitive-enablement-gaps.md, docs/business/master-plan-checklist.md
- `scripts/cos-provider-call` — evidence: docs/adrs/ADR-232-sandbox-adapter-tiers.md
- `scripts/cos-recovery-drill` — evidence: manifests/primitive-contracts.yaml, docs/adrs/ADR-170-operator-cli-as-primary-ui-surface.md, docs/adrs/ADR-172-multi-surface-ui-architecture.md
- `scripts/cos-self-programming-pattern-audit` — evidence: docs/architecture/opensage-self-programming-patterns.md, docs/architecture/primitive-contract-registry-implementation-plan.md, docs/business/master-plan-checklist.md
- `scripts/cos-worktree-sweeper.sh` — evidence: manifests/agent-orchestration-adapters.yaml, docs/adrs/ADR-115-safe-worktree-sweeper.md, docs/architecture/worktree-sweeper.md
- `scripts/install-git-filter-repo.sh` — evidence: manifests/dependencies.yaml, manifests/history-sanitization.yaml, docs/acc/latest.md
- `scripts/install-obsidian-local.sh` — evidence: docs/adrs/ADR-168-cross-device-dependency-installation.md, docs/manual-tests/engram-obsidian-export.md, docs/setup/cross-device-dependencies.md
- `scripts/license-audit-syft-grype.sh` — evidence: manifests/tool-discovery-preuse.yaml, docs/acc/latest.md, docs/adrs/ADR-212-cross-stack-license-audit-toolchain.md
- `scripts/portable_ai_consumer_smoke.py` — evidence: docs/adrs/ADR-258-portable-ai-overlay-for-agentic-primitives.md
- `scripts/run_skill_lifecycle_promotion_smoke.py` — evidence: docs/adrs/ADR-177-activate-skill-lifecycle-promotion-ladder.md
- `scripts/validate_substrate_consumers.py` — evidence: docs/business/case-study.md, docs/business/durable-product-master-plan.md, docs/business/master-plan-checklist.md

### P2-test-only (17)

- `scripts/check-upstream-changes.sh` — evidence: tests/behavior/test_check_upstream_changes.py
- `scripts/check_catalog_sync.py` — evidence: rules/python-naming.md, tests/architecture/test_wiring.py
- `scripts/check_test_ratchet.py` — evidence: rules/python-naming.md, tests/architecture/test_wiring.py
- `scripts/cos-dspy-pilot` — evidence: tests/red_team/portability/test_cos-dspy-pilot.py
- `scripts/cos-engram-command-audit` — evidence: manifests/primitive-consumer-availability.yaml, tests/audit/test_engram_command_contract.py
- `scripts/cos-friction-report` — evidence: tests/behavior/test_cos_friction_report.py
- `scripts/cos-generate-notices.py` — evidence: tests/audit/test_python_naming.py, tests/unit/test_cos_generate_notices.py
- `scripts/cos-integration-shard-plan` — evidence: tests/red_team/portability/test_cos-integration-shard-plan.py
- `scripts/cos-operational-status` — evidence: tests/unit/test_cos_operational_status.py
- `scripts/cos-portable-ai-consumer-impact` — evidence: tests/contracts/test_portable_ai_completion.py
- `scripts/cos-portable-ai-consumer-smoke` — evidence: tests/contracts/test_primitive_closure_smokes.py
- `scripts/cos-primitive-service-headless-smoke` — evidence: tests/contracts/test_primitive_closure_smokes.py
- `scripts/cos-profile-explain` — evidence: tests/unit/test_profile_resolver.py
- `scripts/cos-repo-map` — evidence: tests/red_team/portability/test_cos-repo-map.py
- `scripts/cos-session-spawn.sh` — evidence: tests/unit/test_cos_session_spawn.py
- `scripts/cos_work_queue.py` — evidence: rules/python-naming.md, tests/unit/test_work_queue_sync.py
- `scripts/prelaunch-message-audit` — evidence: tests/unit/test_prelaunch_audit.py

## Recommended next slices

1. Promote or classify the 34 remaining script-orchestrated shell/no-extension workflows.
2. For the 112 doc/test/evidence-only rows, check whether the referenced docs/tests still describe active behavior; archive only after evidence is stale.
3. Add lifecycle/role metadata for recurring maintainer workflows that survive the cleanup.

## Validation

```bash
python3 -m py_compile lib/script_exposure_audit.py scripts/cos-script-exposure-audit
python3 -m pytest tests/unit/test_script_exposure_audit.py tests/behavior/test_script_exposure_audit_cli.py -q
scripts/cos-script-exposure-audit --json
```
