# Primitive Readiness Ledger — Scripts

Total scripts: 625
Roles: agentic-primitive:198, archive:12, driver-specific:12, lab:97, maintainer-tool:291, migration-only:15
Low confidence rows: 5
Agentic primitives without lifecycle metadata: 0

| Script | Role | Source | Confidence | Consumer Access | Lifecycle | Harnesses | Consumers | Next action |
|---|---|---|---|---|---|---|---:|---|
| `scripts/_lib/local-service.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 4 | declare supported harnesses and fallback behavior |
| `scripts/_lib/session-id.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/_lib/settings-driver-bare.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 6 | declare supported harnesses and fallback behavior |
| `scripts/_lib/settings-driver-claude-code.sh` | driver-specific | heuristic:path | medium | skill-referenced-not-projectable |  |  | 47 | declare supported harnesses and fallback behavior |
| `scripts/_lib/settings-driver-codex.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 19 | declare supported harnesses and fallback behavior |
| `scripts/_lib/settings-driver.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 29 | declare supported harnesses and fallback behavior |
| `scripts/acc_pipeline.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 49 | keep lifecycle evidence and supported harness declarations current |
| `scripts/active_primitive_index.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 20 | keep lifecycle evidence and supported harness declarations current |
| `scripts/adr100_live_headroom_check.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/adr_implementation_ledger.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 18 | keep non-default until tests and operator value justify promotion |
| `scripts/adr_reserve.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 8 | add sunset criteria and archive after retention window |
| `scripts/adr_tombstone.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | blocking | claude, codex, shell | 21 | keep lifecycle evidence and supported harness declarations current |
| `scripts/adr_verification_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/agent-orchestration-benchmark.py` | lab | heuristic:path | medium | so-local-only |  |  | 7 | keep non-default until tests and operator value justify promotion |
| `scripts/agent-orchestration-boundary-audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/agent_work_ledger.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 17 | keep non-default until tests and operator value justify promotion |
| `scripts/agentic-tool-license-matrix.sh` | maintainer-tool | override | high | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/agentic_mastery_summary.py` | maintainer-tool | override | high | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/agentic_tool_license_matrix.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ai-budget-preflight` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ai-provider-identity-guard` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 17 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ai-resource-economy-audit` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ai_budget_preflight.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ai_resource_economy_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/align_skill_frontmatter.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 4 | add sunset criteria and archive after retention window |
| `scripts/apply-efficiency-profile.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 130 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/approval_ledger.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 14 | keep non-default until tests and operator value justify promotion |
| `scripts/aspirational_audit.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 31 | keep non-default until tests and operator value justify promotion |
| `scripts/audit-consumer-dependence.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/audit-routing-intents` | maintainer-tool | usage:doc-rule | low | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/audit_adrs.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/audit_engram_topic_keys.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/auto-tune-routing` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/auto-update-projects.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 25 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/auto_tune_routing.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/backfill_cost_events.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 4 | add sunset criteria and archive after retention window |
| `scripts/backfill_session_decisions.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 3 | add sunset criteria and archive after retention window |
| `scripts/benchmark-hooks.sh` | lab | heuristic:path | medium | so-local-only |  |  | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/benchmark-providers` | lab | heuristic:path | medium | so-local-only |  |  | 5 | keep non-default until tests and operator value justify promotion |
| `scripts/benchmark_providers.py` | lab | heuristic:path | medium | so-local-only |  |  | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/chaos/snapshot-concurrent-race.sh` | lab | heuristic:path | medium | so-local-only |  |  | 3 | keep non-default until tests and operator value justify promotion |
| `scripts/chaos/snapshot-crash-rollback.sh` | lab | heuristic:path | medium | so-local-only |  |  | 3 | keep non-default until tests and operator value justify promotion |
| `scripts/chaos/snapshot-vanishing-untracked.sh` | lab | heuristic:path | medium | so-local-only |  |  | 3 | keep non-default until tests and operator value justify promotion |
| `scripts/check-upstream-changes.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_absolute_paths.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/check_catalog_sync.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/check_entrypoint_adr_links.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_hook_registration.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/check_lazy_catalog_health.py` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_lib_wiring.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/check_mcp_servers.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/check_test_quality.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 16 | keep lifecycle evidence and supported harness declarations current |
| `scripts/check_test_ratchet.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/ci-setup.sh` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ci-smoke-linux.sh` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/claim_enforcer.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/claim_proof_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/claim_task.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 20 | keep non-default until tests and operator value justify promotion |
| `scripts/cleanup-snapshots.sh` | migration-only | heuristic:path | medium | so-local-only |  |  | 4 | add sunset criteria and archive after retention window |
| `scripts/commit_provenance.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/component-lint.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/compose_agent_prompt.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 2104 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-action-receipt` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 14 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-active-primitive-index` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-adapter-compile` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-adapters` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-adoption-profile` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-adoption-unfreeze` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-adr-close` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 21 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-adr-implementation-audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-adr-partial-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-adr-partial-ledger` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-adr-resolve` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-adr-tombstone` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | blocking | claude, codex, shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-agent-daemon` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-agent-message` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | pending-sunset | claude, codex, shell | 16 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-agent-spawn-benchmark` | lab | heuristic:path | medium | so-local-only |  |  | 7 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-agent-worktree-prepare` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-architecture-readiness` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-audit-archive` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-auth-probe` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 17 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-bootstrap.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 30 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-boring-reliability` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 40 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-branch-lease` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-branch-lock` | archive | override | high | so-local-only |  |  | 4 | archive-first and remove active references |
| `scripts/cos-branch-release` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-branch-task-check` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-capability-matrix` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-ci-local.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | blocking | shell | 27 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-claim-signature-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-claims.sh` | archive | override | high | so-local-only |  |  | 2 | archive-first and remove active references |
| `scripts/cos-cleanup.sh` | migration-only | heuristic:path | medium | so-local-only |  |  | 5 | add sunset criteria and archive after retention window |
| `scripts/cos-closure-discipline-audit` | maintainer-tool | override | high | lifecycle-declared-maintainer | blocking | shell | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-closure-trust-signal.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-cloud-worker-bootstrap.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 18 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-config-audit.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 25 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-consumer-fleet-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-context-budget-report` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-control-plane-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 21 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-coordination-status.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-core-skills-check.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 13 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-counsel-outreach-draft` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-counsel-packet` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-coverage` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 18 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-credential-safe-run` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-cross-instance-drill` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 18 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-cross-stack-adoption-truth` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-cross-stack-license-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-cross-stack-secret-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-default-visible-reducer` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-deferred-tool-plan` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-demotion-loop-audit` | lab | override | high | lifecycle-declared-maintainer | advisory | shell | 13 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-demotion-proposer` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-dependency-adoption-gate` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-deps-coverage-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-deps-install.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 17 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-deps-maintain` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-deps-profile-ratchet` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-deps-triage` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-dispatch-smoke` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-doc-cross-reference-audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-doc-path-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-doctor-concurrency.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-doctor-harness.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 14 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-doctor-memory-lifecycle.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 25 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-doctor-preserve.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-doctor-tools.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 27 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-doctor-work-inventory.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-doctrine-proposer` | lab | override | high | lifecycle-declared-maintainer | advisory | shell | 17 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-document-ingest` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-documentation-truth-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-dspy-pilot` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 5 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-english-only-content-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-engram-bundle` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 17 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-engram-cloud-docker-smoke` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 19 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-engram-cloud-enroll` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 14 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-engram-command-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-engram-import-propose` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-engram-wave2-schema-migrate` | migration-only | heuristic:path | medium | so-local-only |  |  | 3 | add sunset criteria and archive after retention window |
| `scripts/cos-events.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-exercised-coverage` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-export-consumer-evidence` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 15 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-export-consumer-improvement-proposals` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-external-source-fetch` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-false-positive-ledger` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-falsification-benchmark` | lab | heuristic:path | medium | so-local-only |  |  | 7 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-feature-tool-scan` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-feature-vs-tool-benchmark` | lab | heuristic:path | medium | so-local-only |  |  | 5 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-federation-trigger-audit` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 15 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-filter-repo-wrap.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-fingerprint.sh` | archive | override | high | lifecycle-declared-consumer-candidate | sandbox | shell | 6 | archive-first and remove active references |
| `scripts/cos-fleet-confidence-export` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-flow-register.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-friction-report` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-gate-stack.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 7 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-generate-notices.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-ghost-skills.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-git-sync.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-goal` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | claude, codex, shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-governance-roi` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-governed-agent.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-governed-edit.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-headless-pipeline` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 11 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-headless-publication` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-headless-runtime-contract` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-headless-safe-mode` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-headless-service-drill` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 26 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-history-rewrite-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-history-sanitization` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 22 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-history-sanitization-smoke.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-homebrew-local-canary` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-import-consumer-evidence` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 16 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-import-consumer-improvement-proposals` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-imported-pattern-closure-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-init-global.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-init.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 52 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-install-hook` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | claude, codex, shell | 5 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-install-projection-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell, github-actions | 16 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-install-scope-dev-smoke` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-install-skill` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | claude, codex, shell | 4 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-instance-init` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 17 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-integration-shard-plan` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 5 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-key-learnings-capture` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-lab-first-gate` | maintainer-tool | override | high | lifecycle-declared-maintainer | blocking | shell | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-language-dependence-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-lean-core-5min-proof` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-legal-approve` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-locks.sh` | archive | override | high | so-local-only |  |  | 2 | archive-first and remove active references |
| `scripts/cos-maintainer-agent` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-maintainer-impact` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-manifest-tier-claim-audit` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 14 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-mcp-registration-plan` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-memory-benchmark` | lab | heuristic:path | medium | so-local-only |  |  | 4 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-memory-benchmark-compare` | lab | heuristic:path | medium | so-local-only |  |  | 3 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-merge-queue-bench.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 5 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-merge-queue-worker.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-merge-queue.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 12 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-new-adr` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-observe-primitives` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-opencode-primitive-adapter-smoke` | driver-specific | heuristic:path | medium | so-local-only |  |  | 5 | declare supported harnesses and fallback behavior |
| `scripts/cos-operational-guide-audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-operational-status` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-orphan-process-audit.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-pending-truth-aggregator` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 19 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-pending-truth-close` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 16 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-pending-truth-verify` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 19 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-performance-ledger` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-plan-closure-disposition-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-policy-eval` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-policy-settings-projection` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-portability-proof-scaffold` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-portable-ai-consumer-impact` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 7 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-portable-ai-consumer-package-smoke` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-portable-ai-consumer-smoke` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-portable-ai-overlay` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-portable-ai-real-consumer-smoke` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-postgres-local.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-postmortem-regression-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-pr-review.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-pre-public-risk-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-preamble-budget` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-primitive-authority-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-primitive-closure-ratchet` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-primitive-fitness` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-primitive-fitness-ledger` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-primitive-projection-fidelity` | archive | override | high | lifecycle-declared-maintainer | candidate | shell | 6 | archive-first and remove active references |
| `scripts/cos-primitive-service-headless-smoke` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-private-content-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-product-answer` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 17 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-product-answer-refresh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-profile-explain` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-project-registry-prune.sh` | archive | override | high | so-local-only |  |  | 3 | archive-first and remove active references |
| `scripts/cos-promote-from-telemetry` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-promotion-proposer` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-provider-call` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 7 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-public-claim-gate` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-pyrefly-pilot` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell, github-actions | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-pytest-serial-repair` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-python-stdin-antipattern-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-queue-drain` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 13 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-record-onboarding.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-recovery-drill` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-registry-lock` | maintainer-tool | override | high | lifecycle-declared-maintainer | blocking | shell | 15 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-registry.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 19 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-release-check.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-release-external-readiness` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-release-freeze` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-remote-branch-triage` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-repair` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 7 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-repo-map` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-reward-signal-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-rollback` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-root` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 31 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-routing-benchmark` | lab | heuristic:path | medium | skill-referenced-not-projectable |  |  | 13 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-routing-corpus-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-routing-max-gate` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-routing-quality-gate` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-run-task` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-run-trace` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-runtime-hook-reality` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-rust-transpiler-eval` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-safe-clean` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-sandbox-run` | lab | heuristic:path | medium | so-local-only |  |  | 8 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-scope-both-portability-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-scope-projection-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-script-exposure-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-self-improvement-discipline-gate` | maintainer-tool | override | high | lifecycle-declared-maintainer | blocking | shell | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-self-improvement-loop` | lab | override | high | lifecycle-declared-maintainer | advisory | shell | 19 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-self-improvement-runner` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-self-programming-pattern-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-service-readiness-gate` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-session-branch.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 14 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-session-coordination` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | claude, codex, shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-session-spawn.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-session-start-budget` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-session-start-projector` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 27 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-sessions.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-silent-failure-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-skill-description-enrich` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-skill-performance-ledger` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-smoke.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-startup-recover.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-status.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 51 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-strict-maintainer-concurrency-proof` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-subprocess-timeout-audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-subprocess-timeout-backfill` | migration-only | heuristic:path | medium | so-local-only |  |  | 2 | add sunset criteria and archive after retention window |
| `scripts/cos-task-submit` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 14 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-team` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-telemetry-aggregate` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-test-efficiency-plan` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-test-repair-loop` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-tier-claim-audit` | maintainer-tool | override | high | lifecycle-declared-maintainer | blocking | shell | 24 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-tool-adoption-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-tool-discovery-preuse` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-tool-inventory` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-tool-radar-render` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-tool-research-check` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-tui` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-update.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 35 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-usage-report.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-uspto-patent-search` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-uspto-trademark-search` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-validate` | archive | override | high | lifecycle-declared-consumer-candidate | sandbox | shell | 7 | archive-first and remove active references |
| `scripts/cos-validation-break.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-validation-capsule.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 16 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-validation-status.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-valkey-local.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-vs-ai-slop-two-repo-smoke` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-weekly-config-audit.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 10 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-weekly-primitive-gap.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-weekly-public-metrics.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-wiki-ingest` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 5 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-wip-safety-score` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-worker-run-once` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 15 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-worktree-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-worktree-sweeper.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-worktree-triage.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_adoption_profile.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_agent_message.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_architecture_readiness.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | active | shell | 15 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_auth_probe.py` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 11 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_boring_reliability.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_branch_lease.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_branch_lock.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_build_self_knowledge.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_chaos_template.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_claim_signature_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_classify_coverage.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_clean_room_ast_similarity.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_cleanup_preserved_wip.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 13 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_closure_discipline_audit.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | sandbox | shell | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_codex_guard.py` | driver-specific | heuristic:path | medium | so-local-only |  |  | 8 | declare supported harnesses and fallback behavior |
| `scripts/cos_concurrent_status.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 8 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_consumer_fleet_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_consumer_improvement_proposals.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_context_budget_report.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_coordination_status.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_coverage.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_credential_safe_run.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_cross_instance_drill.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_cross_instance_learning.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_daemon.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 19 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_default_visible_reducer.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_demotion_loop_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_demotion_proposer.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_deps_install.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_dispatch_smoke.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_doc_path_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_doctrine_proposer.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_engram_command_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_evolve_tick.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_executor.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 15 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_false_positive_ledger.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_falsification_benchmark.py` | lab | heuristic:path | medium | so-local-only |  |  | 4 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_flow_register.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_friction_report.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_goal.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_governance_roi.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_governed_runner.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_governed_self_improvement.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_headless_publication.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_headless_safe_mode.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_init.py` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 81 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos_install_projection_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_install_scope_dev_smoke.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_instance_init.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_key_learnings_capture.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 8 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_lib_symlink_invariant_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_manifest_tier_claim_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_new_adr.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_operational_status.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_preamble_budget.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_primitive_fitness.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_primitive_harvester.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 16 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_profile_bootstrap.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_profile_explain.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_promotion_proposer.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_recovery_drill.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_remote_branch_triage.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_repair.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_run_task.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_rust_transpiler_eval.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_self_improvement_loop.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_service_control_plane.py` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 16 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_session_backlog.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_session_coordination.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_sprint.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_task_claims.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 18 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_task_event_watcher.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_test_artifact_status.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_test_quality_audit.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 13 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_tier_claim_audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_validate.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_verbatim_copy_detector.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_vs_ai_slop_two_repo_smoke.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_watch.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_wip_safety_score.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_work_inventory.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 39 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos_work_queue.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_worktree_sweeper.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 11 | keep non-default until tests and operator value justify promotion |
| `scripts/cos_worktree_triage.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cosd` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 91 | keep non-default until tests and operator value justify promotion |
| `scripts/cost_predict.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/create-release.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 12 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/credibility-audit.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cross_session_reconciler.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 12 | keep non-default until tests and operator value justify promotion |
| `scripts/dangerous_env_flag_detector.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/decision_triage.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/demo-consumer-sdd-lane.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/demo-first-run-onboarding.sh` | lab | override | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep non-default until tests and operator value justify promotion |
| `scripts/demo-governance.sh` | maintainer-tool | override | high | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/demo-portability-proof.sh` | lab | override | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep non-default until tests and operator value justify promotion |
| `scripts/dependency-lane.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/deps-update.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 19 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/derived_artifact_gate.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/detect_runner_capacity.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/doc_review_personas.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/docs_duplicate_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/docs_execution_audit.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 18 | keep non-default until tests and operator value justify promotion |
| `scripts/doctor.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 37 | keep lifecycle evidence and supported harness declarations current |
| `scripts/document_feature_append.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/documentation_truth_audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 20 | keep lifecycle evidence and supported harness declarations current |
| `scripts/dogfood_score.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 19 | keep lifecycle evidence and supported harness declarations current |
| `scripts/domain_model.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/eas_validate.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 21 | keep lifecycle evidence and supported harness declarations current |
| `scripts/edit-coop.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 28 | keep lifecycle evidence and supported harness declarations current |
| `scripts/english_only_content_audit.py` | maintainer-tool | default | low | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/engram-sync.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 21 | keep lifecycle evidence and supported harness declarations current |
| `scripts/export-engram-to-obsidian.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/extract-agent-output.sh` | maintainer-tool | override | high | lifecycle-declared-consumer-candidate | advisory | claude, shell | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/generate-project-settings.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 29 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/generate_adr_index.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/generate_adversarial_scenario.py` | lab | override | high | so-local-only |  |  | 4 | keep non-default until tests and operator value justify promotion |
| `scripts/generate_compact_catalog.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 18 | keep lifecycle evidence and supported harness declarations current |
| `scripts/generate_harness_projection_registry.py` | driver-specific | heuristic:path | medium | so-local-only |  |  | 4 | declare supported harnesses and fallback behavior |
| `scripts/git-coop.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/harness-parity-audit` | driver-specific | override | high | lifecycle-declared-maintainer | advisory | shell | 6 | declare supported harnesses and fallback behavior |
| `scripts/harness_parity_audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/hook-stream-statusline.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/hook-timing-wrapper.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 27 | keep non-default until tests and operator value justify promotion |
| `scripts/hook_quality_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/hook_timing_report.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/ide-bridge.sh` | driver-specific | override | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | declare supported harnesses and fallback behavior |
| `scripts/install-aguara.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 18 | keep lifecycle evidence and supported harness declarations current |
| `scripts/install-cos.sh` | maintainer-tool | override | high | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-credibility-tools.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/install-garak.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 17 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/install-git-filter-repo.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-git-hooks.sh` | maintainer-tool | override | high | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-goreleaser.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-launchd-jobs.sh` | driver-specific | override | high | so-local-only |  |  | 6 | declare supported harnesses and fallback behavior |
| `scripts/install-mcp-scan.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 17 | keep lifecycle evidence and supported harness declarations current |
| `scripts/install-obsidian-local.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/install-pre-commit.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-promptfoo.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 19 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/install-syft-grype.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/install-timing-test.sh` | maintainer-tool | override | high | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-tob-skills.sh` | maintainer-tool | override | high | lifecycle-declared-consumer-candidate | active | shell | 14 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-trivy.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/invariant_check_helper.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 9 | keep non-default until tests and operator value justify promotion |
| `scripts/lab_first_promotion_gate.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/license-audit-syft-grype.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/license-audit-trivy.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/lint-shell.sh` | maintainer-tool | override | high | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/llm_status.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/manifest-check.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 14 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/mcp_tofu_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/measure_expansion.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/measure_harness_profiles.py` | driver-specific | heuristic:path | medium | so-local-only |  |  | 9 | declare supported harnesses and fallback behavior |
| `scripts/merge-settings.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/merge-to-main.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 18 | keep lifecycle evidence and supported harness declarations current |
| `scripts/metrics_tamper_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/migrate-to-cognitive-os.sh` | migration-only | heuristic:path | medium | so-local-only |  |  | 4 | add sunset criteria and archive after retention window |
| `scripts/migrate_event_log_to_v2.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 4 | add sunset criteria and archive after retention window |
| `scripts/migrate_skill_archive_to_store.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 4 | add sunset criteria and archive after retention window |
| `scripts/migrate_skill_descriptions_use_when.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 2 | add sunset criteria and archive after retention window |
| `scripts/network_egress_guard.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/network_sandbox_run.py` | lab | heuristic:path | medium | so-local-only |  |  | 8 | keep non-default until tests and operator value justify promotion |
| `scripts/opencode_primitive_adapter_smoke.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 4 | keep lifecycle evidence and supported harness declarations current |
| `scripts/ops_runbook.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/orchestrator.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 38 | keep lifecycle evidence and supported harness declarations current |
| `scripts/orchestrator_claim_gate.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 22 | keep non-default until tests and operator value justify promotion |
| `scripts/orphan_commit_scan.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/orphan_overwrite_detector.py` | maintainer-tool | override | high | lifecycle-declared-consumer-candidate | sandbox | shell | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/parity_harness.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/plan-lock.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/plan_closure_disposition_audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | claude, codex, shell | 3 | keep lifecycle evidence and supported harness declarations current |
| `scripts/portable_ai_consumer_impact.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/portable_ai_consumer_package.py` | archive | override | high | lifecycle-declared-consumer-candidate | sandbox | shell | 6 | archive-first and remove active references |
| `scripts/portable_ai_consumer_smoke.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/portable_ai_overlay.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/portable_ai_real_consumer_smoke.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/postinstall.js` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/precommit_content_hash.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 12 | keep non-default until tests and operator value justify promotion |
| `scripts/prelaunch-apply-rewrite` | archive | override | high | so-local-only |  |  | 4 | archive-first and remove active references |
| `scripts/prelaunch-history-audit` | archive | override | high | so-local-only |  |  | 4 | archive-first and remove active references |
| `scripts/prelaunch-message-audit` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/prelaunch-rewrite-plan` | archive | override | high | so-local-only |  |  | 4 | archive-first and remove active references |
| `scripts/primitive-behavior-audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-behavior-depth-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-coherence-audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 14 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-balance-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-dependency-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-false-both-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-generic-os-only-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-health` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-plane-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-proof-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive-scope-random-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_authority_audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 17 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_backend_benchmark.py` | lab | heuristic:path | medium | so-local-only |  |  | 4 | keep non-default until tests and operator value justify promotion |
| `scripts/primitive_behavior_depth_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_closure_ratchet.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_coverage.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_duplication_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_family_readiness_ledger.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 16 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_fitness_ledger.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_gap_snapshot.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_harness_coverage.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | claude, codex, shell | 21 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_harness_partials.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_lifecycle.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_parse_inventory.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_projection_fidelity.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 19 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_readiness_ledger.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 19 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_row_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_scope_classifier.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell, github-actions | 51 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_scope_dependency_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_scope_health.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 14 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_scope_random_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_scope_unknown_triage.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_service_headless_smoke.py` | archive | override | high | lifecycle-declared-maintainer | candidate | shell | 5 | archive-first and remove active references |
| `scripts/primitive_structure_standardizer.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_surface_reduce.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/primitive_usage_map.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/private_content_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/project_scaffold.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/project_shell_ci.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 17 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/promote_lifecycle_primitives_to_contracts.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/proof-drill-evidence-record` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/proof-drill-select` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/proof_drill_evidence_record.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/proof_drill_select.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/provider_spoof_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/push_collision_detect.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 13 | keep non-default until tests and operator value justify promotion |
| `scripts/pytest-with-summary.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 41 | keep lifecycle evidence and supported harness declarations current |
| `scripts/python_stdin_antipattern_audit.py` | maintainer-tool | override | high | lifecycle-declared-consumer-candidate | sandbox | shell | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/queue_throughput_bench.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/radar_merge.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/redteam_aggregate.py` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/reduction_backlog.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/regen_catalog_bullets.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 6 | add sunset criteria and archive after retention window |
| `scripts/register-mcps.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 20 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/render_adoption_tiers.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/reserve_adr_slot.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 5 | add sunset criteria and archive after retention window |
| `scripts/resource_lease.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 17 | keep non-default until tests and operator value justify promotion |
| `scripts/review_pending_sweeper.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/risk_register.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 8 | keep non-default until tests and operator value justify promotion |
| `scripts/routing_corpus_audit.py` | maintainer-tool | default | low | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/routing_intent_audit.py` | maintainer-tool | default | low | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/routing_quality_gate.py` | maintainer-tool | default | low | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/rules_export.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/run-adversarial-generalization.sh` | lab | override | high | so-local-only |  |  | 5 | keep non-default until tests and operator value justify promotion |
| `scripts/run-all-tests.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | active | shell | 17 | keep lifecycle evidence and supported harness declarations current |
| `scripts/run-redteam-scenario.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 13 | keep non-default until tests and operator value justify promotion |
| `scripts/run-runtime-benchmark.sh` | lab | heuristic:path | medium | so-local-only |  |  | 4 | keep non-default until tests and operator value justify promotion |
| `scripts/run_skill_efficacy_smoke.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/run_skill_lifecycle_promotion_smoke.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/runtime_benchmark_report.py` | lab | heuristic:path | medium | so-local-only |  |  | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/runtime_hook_reality.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 17 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/scope_tag_backfill.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 3 | add sunset criteria and archive after retention window |
| `scripts/security-red-team` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 23 | keep lifecycle evidence and supported harness declarations current |
| `scripts/security_audit_writer.py` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/security_red_team.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/self_improvement_discipline_gate.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/self_programming_pattern_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/semantic-lookup.mjs` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/session-leak-diagnostic.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/session_event_bus.py` | maintainer-tool | override | high | lifecycle-declared-consumer-candidate | sandbox | shell | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/session_start_budget.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | active | shell | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/set-security-profile.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 48 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/setup-git-hooks.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 21 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/setup.sh` | agentic-primitive | lifecycle | high | install-profile-managed | active | shell | 35 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/shellcheck-baseline.txt` | maintainer-tool | override | high | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/silent_failure_audit.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | active | shell | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/skill-router-benchmark.py` | lab | heuristic:path | medium | so-local-only |  |  | 8 | keep non-default until tests and operator value justify promotion |
| `scripts/skill-router-retrieval-audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/skill_efficacy_report.py` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/skill_platform_support_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/smoke-agent-quota-advisor.sh` | maintainer-tool | override | high | lifecycle-declared-maintainer | candidate | shell | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/smoke-agent-quota-redirect.sh` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/smoke-doc-review-personas.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/smoke-multi-provider-fallback.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/smoke-qwen-fallback.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 24 | keep lifecycle evidence and supported harness declarations current |
| `scripts/so-emergency-stop.sh` | lab | lifecycle | high | lifecycle-declared-maintainer | sandbox | shell | 11 | keep non-default until tests and operator value justify promotion |
| `scripts/so-reaper.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 32 | keep lifecycle evidence and supported harness declarations current |
| `scripts/so-vitals.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 16 | keep lifecycle evidence and supported harness declarations current |
| `scripts/so_session_watchdog.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/so_vs_vanilla_benchmark.py` | lab | heuristic:path | medium | skill-referenced-not-projectable |  |  | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/sprint-test-summary.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/startup-benchmark.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 11 | keep lifecycle evidence and supported harness declarations current |
| `scripts/stash-leak-alarm.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 10 | keep non-default until tests and operator value justify promotion |
| `scripts/stash_quarantine_audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | advisory | claude, codex, shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/state_retention_audit.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | active | shell | 16 | keep lifecycle evidence and supported harness declarations current |
| `scripts/statusline-coverage.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | candidate | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/subagent_launch_preflight.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test-agent-teams-hooks.sh` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test-all.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/test-cognitive-os-full.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/test-cognitive-os.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test-mcp-server.sh` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test_run_inventory.py` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 13 | keep lifecycle evidence and supported harness declarations current |
| `scripts/test_skip_registry.py` | maintainer-tool | override | high | lifecycle-declared-maintainer | advisory | shell | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/topology-discover.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/uninstall.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 24 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/update_readme_badges.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/upgrade.sh` | agentic-primitive | lifecycle | high | install-profile-managed | advisory | shell | 15 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/validate_substrate_consumers.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/validate_tier_filter.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/verify-archived.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-consumer-candidate | candidate | shell | 15 | keep lifecycle evidence and supported harness declarations current |
| `scripts/verify_plan_claims.py` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | claude, codex, shell | 14 | keep lifecycle evidence and supported harness declarations current |
| `scripts/version.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/weekly-aspirational-audit.sh` | lab | lifecycle | high | lifecycle-declared-consumer-candidate | sandbox | shell | 8 | keep non-default until tests and operator value justify promotion |
| `scripts/workstation_container_benchmark_report.py` | lab | heuristic:path | medium | so-local-only |  |  | 2 | keep non-default until tests and operator value justify promotion |
| `scripts/write_context_marker.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 15 | keep out of default user surface unless promoted through lifecycle metadata |
