# Primitive Coverage Report

Adapter: `cognitive-os`
Targets: 976
Average score: 58.5
Actionable gap rows: 0
Actionable gaps: 0

## Families

| Family | Count | Average Score | Statuses |
|---|---:|---:|---|
| config | 5 | 55.0 | dormant:5 |
| doc | 395 | 46.86 | dormant:305, partial:90 |
| hook | 233 | 71.85 | dormant:16, partial:217 |
| rule | 112 | 65.0 | partial:112 |
| script | 64 | 52.73 | dormant:63, partial:1 |
| skill | 156 | 65.0 | partial:156 |
| workflow | 11 | 70.91 | dormant:2, partial:9 |

## Rows

| Primitive | Score | Status | Actionable Gaps | Evidence Gaps |
|---|---:|---|---|---|
| `config:.claude/launch.json` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `config:.claude/plugins/cos-monitors/plugin.json` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `config:.claude/settings.json` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `config:cognitive-os.yaml` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `config:manifests/reduction-demotions.json` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `doc:AGENTS.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/HOW-TO-USE-COS.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/INDEX.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/01-Build-Log/SESSION-HANDOFF-2026-04-17.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/01-Build-Log/SESSION-HANDOFF-2026-04-25.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/01-Build-Log/SESSION-HANDOFF-2026-04-27.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/01-Build-Log/SESSION-HANDOFF-2026-05-01.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-006-agpl-license-compliance.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-007-cognitive-os-rebrand.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-008-multi-tool-support.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-009-package-architecture.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-010-hook-architecture-v2.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-011-dual-gateway-bifrost-litellm.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-012-prompt-driven-governance.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-013-security-stack.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-014-sdd-fast-path.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-015-rules-to-hooks-migration.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-016-context-diet.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-017-stabilization-freeze.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-018-docker-to-pip-migration.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-019-scope-tagging.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-020-contamination-fix.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-021-vendor-agnostic-with-adapters.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-022-prompt-type-hooks-adoption.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-023-updated-input-pattern.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-024-task-panel-bridge.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-025-install-update-loop.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-026-r2-r3-design-review.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-026a-decisions.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-027.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-027a.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-028.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-028a.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-028b.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-028c.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-029.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-029b-reinvention-phase-b-semantic.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-030.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-031.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-032-orchestrator-trap-preview.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-033-harness-agnostic-event-capture.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-033b-duration-correlation-and-aider-hardening.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-034-harness-agnostic-live-streaming.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-035-worktree-cwd-enforcement.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-036-sprint-orchestration-primitives.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-037-self-knowledge-base.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-038-preamble-v2-industry-aligned.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-039-reinvention-phase-b-beta.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-040-query-tailored-context-injection.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-041.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-042-valkey-local-daemon.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-044-context-payload-slimming.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-045-postgres-local-daemon.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-047-session-lifecycle-management.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-048-docker-container-image-freshness.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-050-per-skill-routing-policy.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-051-qwen-agent-loop.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-052-provider-benchmark-harness.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-053-dispatch-auto-optimizer.md` | 25 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-054-project-docs-convention.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-055-docs-convention-enforcement.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-055b-destructive-git-block.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-056-adaptive-agent-dispatch.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-057-cross-harness-authoring-and-driver-projection.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-059-so-existential-validation.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-060-local-only-optional-services.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-061-focus-narrative-and-external-evidence.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-062-multi-provider-agent-loop.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-063-agent-tool-replication-strategy.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-064-harness-agnostic-cognitive-os.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-065-radar-update-curation-pipeline.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-066-polyglot-language-boundaries.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-067-frontmatter-defense-in-depth.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-068-adaptive-test-runner-capacity.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-069-research-first-protocol.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-070-convention-enforcement-mechanism.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-072-test-lane-taxonomy.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-073-test-architecture-role-registry.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-074-tier-0-learning-loop-closure.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-075-stage2-selective-expansion.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-076-skill-frontmatter-alignment.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-077-peer-card-local-model.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-078-mid-task-memory-tool.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-079-corerules-applies-to-self-hosting.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-080-hermes-cross-harness-adoption.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-081-codex-harness-adapter.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-082-plan-location-convention.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-083-governed-self-improvement-loop.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-084-headless-clustered-runtime-shape.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-086-hook-execution-observability.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-087-adr-namespace-consolidation.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-088-provenance-trailer-ppid-chain.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-089-multi-session-git-coordination.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-090-auto-skill-repair.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-091-headless-clustered-runtime-direction.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-092-harness-skills-sync-path.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-093-simplify-profiles.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-094-agent-git-safety.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-095-skill-synthesis-success-patterns.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-096-review-agent-pattern.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-097-documentation-execution-audit.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-097-task-tracker-lifecycle.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/ADR-098-multi-agent-file-coordination.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-099-pre-agent-snapshot-copy-on-untracked.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-100-resource-governed-test-execution.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/02-Decisions/adrs/ADR-101-intent-aware-rate-limiter.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/02-Decisions/adrs/README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/root/adw-patterns.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/07-Capabilities/root/agent-efficiency-strategy.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/07-Capabilities/root/agent-quality.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/07-Capabilities/root/agent-teams-testing.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/07-Capabilities/root/agent-teams.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/anti-hallucination.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture-principles.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/FROZEN-BACKLOG.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/LESSONS-LEARNED.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/POST-MORTEM-2026-04.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/006-agpl-license-compliance.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/007-cognitive-os-rebrand.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/008-multi-tool-support.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/009-package-architecture.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/010-hook-architecture-v2.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/011-dual-gateway-bifrost-litellm.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/012-prompt-driven-governance.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/013-security-stack.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/014-sdd-fast-path.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/015-rules-to-hooks-migration.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/016-context-diet.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/017-stabilization-freeze.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/018-docker-to-pip-migration.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/019-scope-tagging.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/020-contamination-fix.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/021-vendor-agnostic-with-adapters.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/022-prompt-type-hooks-adoption.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/023-updated-input-pattern.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/024-task-panel-bridge.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/025-install-update-loop.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/026-r2-r3-design-review.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/026a-decisions.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/027-headless-clustered-runtime-direction.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/ADR-001-abc-parallel-dedup-fix-broken-infra-add-global-verify.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/ADR-002-docker-pip-localhost-envs-targetedtestresolver-redis-dep.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/adrs/README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/behavioral-test-contracts.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/bootstrap-portability.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/capability-centric-runtime-enforcement.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/core-vs-extensions-audit-2026-04-20.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adr-detection.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-001-reuse-klaudiush-predicates.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-002-transformer-separate-interface.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-003-sqlite-over-jsonl.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-004-generated-artifacts-disabled.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-005-typed-provider-adapters.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-006-override-result-type.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-007-eager-failure-sequences.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-008-review-subcommand.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-009-go-only-auto-generation.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-010-real-behavior-tests.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/CD-011-phase-5-sub-phase-ordering.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/adrs/README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/config.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/interfaces.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/migration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-dispatch/phase-5.0-notes.md` | 25 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/cos-dispatch/phase-5.3-notes.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/cos-dispatch/phase-5.4-notes.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/cos-dispatch/test-strategy.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-update-vs-cos-cli-responsibility-analysis.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cos-vs-project-overlap-analysis.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cross-harness-authoring.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cross-platform-ci.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/cross-runtime-portability.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/cross-tool-landscape.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/documentation-execution-audit.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/driver-specific-script-surfaces.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/functional-audit/f1-cleanup.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/functional-audit/scorecard-hooks.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/functional-audit/scorecard-install-scripts.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/functional-audit/scorecard-rules.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/functional-audit/scorecard-skills.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/functional-audit/sprint-2a-orphan-fate.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/functional-audit/sprint-5-observability.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/functional-audit/startup-baseline-2026-04-20.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/functional-audit/ux2-hook-hygiene.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/functional-audit/ux6-idempotent-update.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/ADR-002-simplify-profiles.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/ADR-003-agent-git-safety.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/adr-003-hook-registration-pending.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/diagnosis.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-A-root-installers.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-B-init-bootstrap.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-C-updaters.md` | 25 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-D-profile-uninstall.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-adoption-gap/ux1-install-usability.md` | 25 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/architecture/harness-driver-parity.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/harness-transparency-status.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/infrastructure-service-catalog.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/memory-lifecycle.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/observability-backend-evaluation-2026-04-24.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/parser-coverage-audit-2026-04-24.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/path-portability-and-privacy.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/plans-reconciliation-2026-04-21.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/primitive-coverage-spike-plan-2026-04.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/primitive-coverage-tooling-research-2026-04.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/project-consumption-patterns.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/rate-limiter-flow-control.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/reality-audit.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/runtime-hardcoding-discipline.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/skills-rules-canonicalization-risk-analysis.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/skills-rules-portability-gap.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/tac-course-reference.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/tooling-stack-rationalization.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/validation-nervous-system.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/architecture/why-skills-and-rules-became-claude-centered.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archive/plans/dead-weight-audit.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archive/plans/docs-hook-rule-candidates.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archive/plans/docs-rescan-results.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archive/plans/intelligent-context-compaction.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archive/plans/self-optimizing-pipeline.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archive/plans/status-report-april-11.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archived/benchmark-results.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/99-Archive/archived/cleanup-verification.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/auto-library.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/auto-repair-system.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/automation-doc-sync.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/05-Methodology/root/automation.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/root/benchmarking.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/blocked-tools.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/root/bmad-v6-patterns.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/case-study.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/competitive-reassessment-openclaw-hermes-2026-04.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/business/conversation-reality-audit-2026-04-30.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/developer-confidence.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/business/durable-product-master-plan.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/business/execution-discipline.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/executive-summary.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/feature-reality-audit.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/features.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/business/kubernetes-for-agents.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/master-plan-checklist.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/business/master-plan-execution-requirements.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/open-source-design.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/openclaw-implementation-roadmap.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/openclaw-remaining-patterns.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/portability-plan.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/business/product-messaging.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/business/roadmap.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/business/value-proposition.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/07-Capabilities/root/capability-snapshot.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/08-References/root/competitive-analysis.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/root/competitive-arena.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/08-References/root/competitive-landscape.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/06-Daily/root/complexity-audit.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/06-Daily/root/component-audit.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/component-sources.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/configurable-quality-gates.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/07-Capabilities/root/cos-package-manager.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/dashboard-architecture.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/definition-of-done.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/design-philosophy.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/distributed-architecture.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/dogfooding.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/ecosystem-comparison.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/engram-namespaces.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/execution-backends.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/faq.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/fault-tolerance.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/gateway-architecture.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/getting-started-quick.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/getting-started.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/global-vs-project-config.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/gpu-sandbox.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/05-Methodology/guides/adding-a-harness-adapter.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/guides/queue-classes-routing.md` | 25 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen, no_static_consumers |
| `doc:docs/04-Concepts/root/health-monitoring.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/09-Quality/root/hook-security-profiles.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/root/hooks.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/root/how-to-extend.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/ide-compatibility.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/identity-stack.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/01-Build-Log/root/implementation-phases.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/06-Daily/incidents/2026-05-01-session-multi-spawn-hang.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/infra-intent.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/integrations/cursor-cloud-agents.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/kernel-contract.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/01-Build-Log/root/launch-strategy.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/leverage-points.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/manual-tests/codex-host-tooling-verification.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/manual-tests/durable-product-verification.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/09-Quality/manual-tests/first-run-onboarding.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/09-Quality/manual-tests/five-minute-demo.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/manual-tests/local-connected-systems-validation.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/09-Quality/manual-tests/lote-2-mcp-loop.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/manual-tests/proof-paths.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/06-Daily/measurements/cos-adr-namespace-audit-2026-04-30.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/06-Daily/measurements/cos-duplication-audit-2026-04-30.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/06-Daily/measurements/hook-timing-runbook.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/06-Daily/measurements/sessionstart-baseline.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/06-Daily/measurements/snapshot-chaos-runbook.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/06-Daily/measurements/stage2-expansion-baseline.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/migration-from/from-hermes.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/migration-from/from-vanilla-claude-code.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/model-evolution-resilience.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/multi-model-factory.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/onboarding-wizard-design.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/root/open-source-strategy.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/root/openclaw-patterns.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/organizational-model.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/os-vs-project-separation.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/overview.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/package-manager-design.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/root/patterns-adopted.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/cognitive-os-changes.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/component-classification.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/cross-harness-authoring.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/dogfooding.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/ecosystem-tools.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/library-selection.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/os-vs-project.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/patterns/plan-first.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/performance.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/persistence-map.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/phase-system.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/root/piter-framework.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/plan-system.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/plug-and-play.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/product-principles.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/product-zones.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/root/prompt-driven-governance.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/prompt-templates.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/00-MOCs/entrypoints/quickstart.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/08-References/root/recommended-stack.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/01-Build-Log/release/roadmap-v1.0-full-e2e.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/01-Build-Log/release/v1.0-release-criteria.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/03-PoCs/root/research-log.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/03-PoCs/research/archon-evaluation.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/03-PoCs/research/claude-code-router-evaluation-2026-04-21.md` | 30 | dormant |  | missing_wired, missing_tested, runtime_not_seen, no_static_consumers |
| `doc:docs/03-PoCs/research/engram-mcp-sharing-feasibility-2026-04-20.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/03-PoCs/research/llm-wiki-v2-engram-evolution-2026-04-27.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/03-PoCs/research/minimal-context-principle.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/03-PoCs/research/wisc-framework-analysis.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/01-Build-Log/root/roadmap.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/root/rules-consolidation-plan.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/rules-loading-architecture.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/rules.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/runbooks/llm-dispatch.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/runbooks/so-incident-runbook.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/safety-mesh.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/sandbox-sampling.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/09-Quality/root/secret-detection.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/security-stack.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/self-building-protocol.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/self-improvement-loop.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/self-repair-guide.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/06-Daily/root/self-usage-audit.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/session-concurrency.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/setup/dependencies.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/singularity.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/root/skills.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/state-snapshots.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/root/stress-test-strategy.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/root/testing-cognitive-os-suite.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/root/testing-cognitive-os.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/root/testing.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/09-Quality/testing/README.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/09-Quality/testing/mutation-testing.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/testing/suite-signal-triage-2026-04-29.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/09-Quality/testing/test-runner-roles.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/tool-stack.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/root/tooling-update-protocol.md` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `doc:docs/04-Concepts/root/trust-model.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/trust-score.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/04-Concepts/root/ui-platforms-evaluation.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/root/upstream-blockers.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/05-Methodology/usage/cos-status.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `doc:docs/05-Methodology/usage/skill-authoring.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/ux-principles.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/01-Build-Log/root/versioning-strategy.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/08-References/root/vs-alternatives.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `doc:docs/04-Concepts/root/zero-touch-engineering.md` | 45 | dormant |  | missing_wired, missing_tested, runtime_not_seen |
| `hook:hooks/_lib/cache.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/circuit-breaker.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/common.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/execute-repair.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/file_checker.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/hook-pipe.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/killswitch_check.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/normalize-stdin.sh` | 15 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen, no_static_consumers |
| `hook:hooks/_lib/portable.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/register-bg.sh` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `hook:hooks/_lib/remediation.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/resolve-main-worktree.sh` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `hook:hooks/_lib/safe-jsonl.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/semantic-search.sh` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `hook:hooks/_lib/singularity-suggestion.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/timing.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/_lib/tuning.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/adaptive-bypass.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/adr-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/adr-section-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/agent-bash-cwd-enforcer.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/agent-bus-monitor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/agent-checkpoint.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/agent-output-verifier.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/agent-prelaunch.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/agent-quota-advisor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/agent-quota-redirect.sh` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `hook:hooks/agent-qwen-bridge.sh` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `hook:hooks/agent-working-dir-inject.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/agnix-lint.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/aguara-scan.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/architecture-compliance.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/aspirational-audit-weekly.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/assumption-tracker.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/audit-id-enricher.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/auto-checkpoint.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/auto-refine.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/auto-repair-dispatcher.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/auto-rollback-trigger.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/auto-skill-generator.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/auto-verify.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/background-agent-reminder.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/blast-radius.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/claim-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/clarification-gate.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/clarification-interceptor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/code-review-on-commit.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/cognitive-os-health.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/completeness-check-llm.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/completion-gate.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/concurrent-write-guard.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/confidence-gate-llm.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/confidence-gate.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/confidentiality-enforcer.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/consequence-evaluator.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/content-policy.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/context-diet.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/context-watchdog.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/contextual-rule-loader.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/conversation-capture.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/cos-executor-daemon-launcher.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/cos-executor-heartbeat.sh` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `hook:hooks/crash-recovery.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/dequeue-notify.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/destructive-git-blocker.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/destructive-rm-blocker.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/dispatch-gate.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/doc-sync-detector.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/docker-drift-detector.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/dod-gate.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/dry-run-preview.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/ecosystem-check.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/edit-lock-drain-parked.sh` | 75 | partial |  | missing_documented, runtime_not_seen |
| `hook:hooks/edit-lock-pre-tool.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/edit-lock-process-negotiations.sh` | 75 | partial |  | missing_documented, runtime_not_seen |
| `hook:hooks/edit-lock-session-end.sh` | 75 | partial |  | missing_documented, runtime_not_seen |
| `hook:hooks/engram-auto-import.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/engram-auto-sync.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/engram-crystallize-on-session-end.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/engram-daemon-launcher.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/engram-reinforce-on-access.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/epic-task-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/error-learning.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/error-pattern-detector.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/error-pipeline.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/git-commit-scope-guard.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/git-context-capture.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/global-verify.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/guardrails-validator.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/hook-header-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/host-tool-doctor.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/idle-service-cleanup.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/infra-health.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/infra-intent-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/inject-phase-context.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/jupyter-sandbox.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/kpi-trigger.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/large-file-advisor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/mcp-scan.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/memory-prefetch.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/memu-sync.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/metrics-calibrator-trigger.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/metrics-rotation.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/mlflow-sync.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/native-agent-heartbeat.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/notify.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/orchestrator-mode-detect.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/package-sync.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/parry-scan.sh` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `hook:hooks/pattern-check.sh` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `hook:hooks/pre-agent-snapshot.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/pre-cleanup-snapshot.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/pre-commit-gate.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/pre-compaction-flush.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/predev-completeness-check.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/private-mode-gate.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/private-mode-metrics-gate.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/profile-drift-autoapply.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/project-docs-convention.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/prompt-quality-llm.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/query-tailored-context-inject.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/rate-limit-detector.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/rate-limit-drain.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/rate-limit-precheck.sh` | 75 | partial |  | missing_documented, runtime_not_seen |
| `hook:hooks/rate-limit-protection.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/rate-limiter.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/reaper-daemon-launcher.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/reaper-heartbeat.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/recap-sync.sh` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `hook:hooks/registration-check.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/reinvention-check.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/release-guard.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/resource-check.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/result-truncator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/review-spawner.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/rule-frontmatter-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/scope-creep-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/scope-proportionality.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/secret-detector.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/self-install.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/self-knowledge-refresh.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/semgrep-scan.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/session-changelog.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-cleanup.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-end-reap.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/session-heartbeat.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-hygiene.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/session-init.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-knowledge-extractor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/session-learning.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-resume.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-start-worktree-nudge.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-startup-protocol.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-state-save.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/session-summary-reminder.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-watchdog-launcher.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/session-wrapup-trigger.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/singularity-check.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/skill-failure-monitor.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/skill-feedback-tracker.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/skill-frontmatter-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/skill-invocation-logger.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/skill-synthesis-scanner.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/skill-tracker.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/skill-usage-tracker.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/state-heartbeat.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/subagent-context-injector.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/surface-fix-detector.sh` | 75 | partial |  | missing_documented, runtime_not_seen |
| `hook:hooks/sync-to-repo.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/task-bridge-notify.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/task-completed.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/task-created.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/task-panel-sync.sh` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `hook:hooks/task-recorder.sh` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `hook:hooks/teammate-idle.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/token-budget-monitor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/tool-discovery-trigger.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/tool-loop-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/tool-sequence-capture.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/trust-score-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/usage-health-check.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/user-prompt-capture.sh` | 85 | partial |  | runtime_not_seen |
| `hook:hooks/valkey-ensure.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:hooks/work-queue-sync.sh` | 75 | partial |  | missing_documented, runtime_not_seen |
| `hook:hooks/worktree-submodule-fix.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/adaptive-workflow/hooks/adaptive-bypass.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/agent-lifecycle/hooks/agent-checkpoint.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/agent-lifecycle/hooks/agent-prelaunch.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/agent-lifecycle/hooks/review-spawner.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/auto-repair-rollback/hooks/auto-rollback-trigger.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/consequence-system/hooks/auto-skill-generator.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/consequence-system/hooks/consequence-evaluator.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/consequence-system/hooks/trust-score-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/context-optimization/hooks/contextual-rule-loader.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/context-optimization/hooks/metrics-calibrator-trigger.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/context-optimization/hooks/metrics-rotation.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/cos-advisory-llm/hooks/completeness-check-llm.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/cos-advisory-llm/hooks/confidence-gate-llm.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/cos-advisory-llm/hooks/prompt-quality-llm.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/document-sync/hooks/doc-sync-detector.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/document-sync/hooks/sync-to-repo.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/dry-run-simulation/hooks/dry-run-preview.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/ecosystem-tools/hooks/agnix-lint.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/engram-sync/hooks/engram-auto-import.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/engram-sync/hooks/engram-auto-sync.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/engram-sync/hooks/memu-sync.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/infra-lifecycle/hooks/idle-service-cleanup.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/prompt-quality-gate/hooks/prompt-quality.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/quality-gates/hooks/claim-validator.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/quality-gates/hooks/clarification-gate.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/quality-gates/hooks/clarification-interceptor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/quality-gates/hooks/completion-gate.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/quality-gates/hooks/confidence-gate.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/scope-governance/hooks/scope-proportionality.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/skill-governance/hooks/agent-bus-monitor.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/skill-governance/hooks/kpi-trigger.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/skill-governance/hooks/skill-tracker.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/task-management/hooks/blast-radius.sh` | 85 | partial |  | runtime_not_seen |
| `hook:packages/task-management/hooks/epic-task-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/task-management/hooks/scope-creep-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/task-management/hooks/task-recorder.sh` | 40 | dormant |  | missing_wired, missing_tested, missing_proof, runtime_not_seen |
| `hook:packages/task-management/hooks/tool-loop-detector.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/verification-audit/hooks/architecture-compliance.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/verification-audit/hooks/assumption-tracker.sh` | 65 | partial |  | missing_wired, runtime_not_seen |
| `hook:packages/verification-audit/hooks/result-truncator.sh` | 85 | partial |  | runtime_not_seen |
| `rule:rules/ROADMAP.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/RULES-COMPACT.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/acceptance-criteria.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/adaptive-bypass.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/adversarial-review.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-audit-before-commit.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-communication.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-customization.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-escalation.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-identity.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-kpis.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-output-reading.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-quality.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-security.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/agent-sidecars.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/aguara-integration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/anti-hallucination.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/assumption-tracking.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/audit-trail.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/auto-repair.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/auto-rollback.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/auto-skill-generation.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/bash-naming.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/blast-radius.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/broken-window-policy.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/capability-levels.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/capability-protection.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/clarification-gate.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/closed-loop-prompts.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/cognitive-load.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/confidence-gate.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/confidentiality-protection.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/consequence-system.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/content-policy.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/context-management.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/context-optimization.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/context7-auto-trigger.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/cost-prediction.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/crash-recovery.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/credential-management.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/cross-harness-authoring.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/decision-depth-gate.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/decomposition.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/definition-of-done.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/doc-sync.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/dry-run.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/dynamic-tool-creation.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/e2b-integration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/engram-api-safety.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/engram-organization.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/error-learning.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/estimation-calibration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/fault-tolerance.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/hcom-integration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/hook-security-profiles.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/impact-analysis.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/infra-health.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/infra-intent.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/lane-taxonomy.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/license-policy.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/llm-dispatch.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/model-compatibility.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/model-directive.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/model-routing.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/non-blocking-retry.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/observability.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/orchestrator-mode.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/orchestrator-prompt-compose.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/parry-integration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/pentesting-readiness.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/performance-monitoring.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/phase-aware-agents.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/pre-commit-gate.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/pre-dev-readiness-gate.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/private-mode.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/prompt-composition.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/prompt-quality.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/python-naming.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/queue-advisor.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/queue-drain.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/rate-limit-protection.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/rate-limiting.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/reinvention-prevention.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/repomix-integration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/research-first-protocol.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/resource-governance.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/response-compression.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/responsiveness.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/result-management.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/sandbox-sampling.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/scope-creep-detection.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/scope-proportionality.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/scout-pattern.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/security-scanning.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/self-improvement-protocol.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/session-concurrency.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/singularity.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/skill-management.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/skill-rewrite.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/so-slo.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/split-and-resume.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/squad-protocol.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/startup-protocol.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/step-files.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/supply-chain-defense.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/task-dag.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/tero-integration.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/token-economy.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/trailofbits-skills.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/trust-score.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/user-prompt-capture.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `rule:rules/workload-scheduling.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `script:scripts/adr_reserve.py` | 60 | partial |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/align_skill_frontmatter.py` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `script:scripts/aspirational_audit.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/backfill_cost_events.py` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `script:scripts/backfill_session_decisions.py` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `script:scripts/check_absolute_paths.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/check_catalog_sync.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/check_hook_registration.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/check_lib_wiring.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/check_mcp_servers.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/check_test_quality.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/check_test_ratchet.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/claim_proof_audit.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/commit_provenance.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/compose_agent_prompt.py` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `script:scripts/cos_build_self_knowledge.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_chaos_template.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_classify_coverage.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_executor.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_governed_self_improvement.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_init.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_profile_bootstrap.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_sprint.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_test_artifact_status.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_test_quality_audit.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_watch.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cos_work_queue.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/cost_predict.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/decision_triage.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/detect_runner_capacity.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/doc_review_personas.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/docs_duplicate_audit.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/docs_execution_audit.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/document_feature_append.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/dogfood_score.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/domain_model.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/generate_compact_catalog.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/harness_parity_audit.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/hook_timing_report.py` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `script:scripts/invariant_check_helper.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/llm_status.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/measure_expansion.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/ops_runbook.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/orchestrator.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/parity_harness.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/primitive_coverage.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/primitive_gap_snapshot.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/primitive_row_audit.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/primitive_surface_reduce.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/primitive_usage_map.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/project_scaffold.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/radar_merge.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/reduction_backlog.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/regen_catalog_bullets.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/reserve_adr_slot.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/risk_register.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/rules_export.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/scope_tag_backfill.py` | 30 | dormant |  | missing_wired, missing_tested, missing_documented, missing_proof, runtime_not_seen |
| `script:scripts/security_audit_writer.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/so_session_watchdog.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/so_vs_vanilla_benchmark.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/test_run_inventory.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/update_readme_badges.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `script:scripts/write_context_marker.py` | 55 | dormant |  | missing_wired, missing_documented, runtime_not_seen |
| `skill:.codex/skills/docs-to-artifact/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:.codex/skills/portability-work/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:.codex/skills/repo-map/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:.codex/skills/test-matrix/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/adaptive-workflow/skills/self-review/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/agent-coordination/skills/retrospective/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/agent-coordination/skills/squad-manager/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/agent-lifecycle/skills/persistent-agent/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/agent-lifecycle/skills/resume-tasks/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/agent-lifecycle/skills/review-output/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/auto-repair-rollback/skills/auto-rollback/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/context-optimization/skills/compose-prompt/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/context-optimization/skills/exhaustive-prompt/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/document-sync/skills/doc-sync/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/document-sync/skills/document-feature/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/dry-run-simulation/skills/arena/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/dry-run-simulation/skills/simulation-arena/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/audit-website/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/automaker-bridge/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/cognee-integration/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/cognee-search/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/deepeval-integration/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/jupyter-execute/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/promptfoo-integration/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/ragas-integration/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/recommend-library/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/secret-audit/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/semgrep-scan/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/strands-evals-integration/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/tool-discovery/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/ecosystem-tools/skills/web-crawler/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/infra-lifecycle/skills/devbox-checkpoint/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/infra-lifecycle/skills/gpu-sandbox/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/infra-lifecycle/skills/repair-status/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/infra-lifecycle/skills/sre-agent/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/privacy-mode/skills/private-mode/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/quality-gates/skills/confidence-check/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/quality-gates/skills/dod-check/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/quality-gates/skills/nemo-guardrails/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/quality-gates/skills/pentest-self/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/quality-gates/skills/readiness-check/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/quality-gates/skills/resolve-blockers/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/quality-gates/skills/security-audit/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/recall-search/skills/conversation-memory/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/recall-search/skills/memu-context/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/recall-search/skills/recall-search/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/scope-governance/skills/contract-drift/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/scope-governance/skills/deep-research/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/scope-governance/skills/planning-poker/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/scope-governance/skills/repo-scout/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/scope-governance/skills/research-protocol/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/scope-governance/skills/sandbox-sample/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/auto-refine/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/batch-runner/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/evaluate-plan/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/impact-analysis/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/issue-pipeline/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/plan-bug/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/plan-feature/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/sdd-compound/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/singularity/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/sdd-compound/skills/webhook-trigger/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/skill-governance/skills/error-analyzer/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/skill-governance/skills/metrics-calibrator/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/skill-governance/skills/model-optimizer/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/skill-governance/skills/optimize-skill/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/skill-governance/skills/self-improve/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/task-management/skills/agent-kpis/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/task-management/skills/capability-snapshot/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/task-management/skills/sprint/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/cognitive-os-benchmark/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/coverage-enforcement/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/harness-audit/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/smoke-test/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/systematic-debugging/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/test-driven-development/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/trust-audit/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:packages/verification-audit/skills/verification-before-completion/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/__contracts__/canonical-event-emitter/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/add-hook/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/add-mcp/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/add-rule/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/add-skill/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/agent-dashboard/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/agent-stress-test/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/analyze-improvements/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/apply-improvements/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/audit-integrity/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/bump-version/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/catalog-full/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/caveman-compress/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/caveman/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/caveman/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/code-review/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/cognitive-os-init/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/cognitive-os-status/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/cognitive-os-test/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/compat-test/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/component-classifier/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/component-reality-check/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/coordination-status/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/cos-status/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/cost-predictor/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/decision-triage/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/deps-update/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/detect-patterns/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/detect-stack/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/doc-review-personas/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/docs-execution-audit/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/dogfood-score/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/domain-model/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/eval-repo/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/generate-changelog/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/generate-config/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/hook-timing/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/install-recommended/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/invariant-check/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/llm-status/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/memory-scan/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/ops-runbook/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/pattern-audit/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/phoenix-trace-ui/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/pr-review/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/primitive-surface-reduction/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/primitive-usage-map/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/project-scaffold/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/push-release/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/queue-drain/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/radar-update/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/red-team/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/release-os/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/repair-skill/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/repo-forensics/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/resource-governor/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/reverse-engineer/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/risk-register/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/rules-export/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/run-tests/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/scaffold-project/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/scout/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/sdd-continue/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/sdd-explore/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/sdd-resume/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/session-backlog/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/session-manager/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/session-report-executive/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/session-wrapup/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/skill-creator/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/so-vs-vanilla/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/synthesize-skill/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/tag-release/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/test-contract-repair/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/validate-config/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/validate-release/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `skill:skills/vulnerability-scan/SKILL.md` | 65 | partial |  | missing_wired, runtime_not_seen |
| `workflow:.github/workflows/ci.yml` | 85 | partial |  | runtime_not_seen |
| `workflow:.github/workflows/claude-interactive.yml` | 45 | dormant |  | missing_tested, missing_proof, runtime_not_seen, no_static_consumers |
| `workflow:.github/workflows/claude-issue-triage.yml` | 60 | partial |  | missing_tested, missing_proof, runtime_not_seen |
| `workflow:.github/workflows/claude-pr-review.yml` | 60 | partial |  | missing_tested, missing_proof, runtime_not_seen |
| `workflow:.github/workflows/cos-config-audit.yml` | 85 | partial |  | runtime_not_seen |
| `workflow:.github/workflows/cross-platform.yml` | 85 | partial |  | runtime_not_seen |
| `workflow:.github/workflows/go-quality.yml` | 60 | partial |  | missing_tested, missing_proof, runtime_not_seen |
| `workflow:.github/workflows/primitive-gap-audit.yml` | 85 | partial |  | runtime_not_seen |
| `workflow:.github/workflows/test-lanes.yml` | 85 | partial |  | runtime_not_seen |
| `workflow:.github/workflows/test-quality.yml` | 85 | partial |  | runtime_not_seen |
| `workflow:.github/workflows/weekly-public-metrics.yml` | 45 | dormant |  | missing_tested, missing_proof, runtime_not_seen, no_static_consumers |
