# Primitive Readiness Ledger — Scripts

Total scripts: 310
Roles: agentic-primitive:103, driver-specific:10, lab:13, maintainer-tool:173, migration-only:11
Low confidence rows: 0
Agentic primitives without lifecycle metadata: 58

| Script | Role | Source | Confidence | Consumer Access | Lifecycle | Harnesses | Consumers | Next action |
|---|---|---|---|---|---|---|---:|---|
| `scripts/_lib/settings-driver-bare.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 4 | declare supported harnesses and fallback behavior |
| `scripts/_lib/settings-driver-claude-code.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 21 | declare supported harnesses and fallback behavior |
| `scripts/_lib/settings-driver-codex.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 15 | declare supported harnesses and fallback behavior |
| `scripts/_lib/settings-driver.sh` | driver-specific | heuristic:path | medium | so-local-only |  |  | 28 | declare supported harnesses and fallback behavior |
| `scripts/active_primitive_index.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/adr100_live_headroom_check.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/adr_implementation_ledger.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/adr_reserve.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 5 | add sunset criteria and archive after retention window |
| `scripts/agent_work_ledger.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/agentic-tool-license-matrix.sh` | maintainer-tool | override | high | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/agentic_mastery_summary.py` | maintainer-tool | override | high | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/agentic_tool_license_matrix.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/align_skill_frontmatter.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 2 | add sunset criteria and archive after retention window |
| `scripts/apply-efficiency-profile.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 106 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/approval_ledger.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/aspirational_audit.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 16 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/audit_adrs.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/auto-update-projects.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 19 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/backfill_cost_events.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 1 | add sunset criteria and archive after retention window |
| `scripts/backfill_session_decisions.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 1 | add sunset criteria and archive after retention window |
| `scripts/benchmark-hooks.sh` | lab | heuristic:path | medium | so-local-only |  |  | 4 | keep non-default until tests and operator value justify promotion |
| `scripts/chaos/snapshot-concurrent-race.sh` | lab | heuristic:path | medium | so-local-only |  |  | 1 | keep non-default until tests and operator value justify promotion |
| `scripts/chaos/snapshot-crash-rollback.sh` | lab | heuristic:path | medium | so-local-only |  |  | 1 | keep non-default until tests and operator value justify promotion |
| `scripts/chaos/snapshot-vanishing-untracked.sh` | lab | heuristic:path | medium | so-local-only |  |  | 1 | keep non-default until tests and operator value justify promotion |
| `scripts/check-upstream-changes.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_absolute_paths.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_catalog_sync.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_hook_registration.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_lazy_catalog_health.py` | maintainer-tool | override | high | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_lib_wiring.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_mcp_servers.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/check_test_quality.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/check_test_ratchet.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ci-setup.sh` | maintainer-tool | override | high | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/ci-smoke-linux.sh` | maintainer-tool | override | high | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/claim_proof_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/claim_task.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 13 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cleanup-snapshots.sh` | migration-only | heuristic:path | medium | so-local-only |  |  | 2 | add sunset criteria and archive after retention window |
| `scripts/commit_provenance.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/component-lint.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/compose_agent_prompt.py` | maintainer-tool | override | high | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 1053 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-active-primitive-index` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 5 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-adoption-profile` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-architecture-readiness` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 5 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-bootstrap.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 21 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-boring-reliability` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 20 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-branch-lease` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-ci-local.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | blocking | shell | 17 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-claim-signature-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-claims.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 0 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-closure-discipline-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | blocking | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-cloud-worker-bootstrap.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-config-audit.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 19 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-coordination-status.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-core-skills-check.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 7 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-coverage` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-cross-instance-drill` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-default-visible-reducer` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-demotion-loop-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-dispatch-smoke` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-doctor-concurrency.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-doctor-harness.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 7 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-doctor-memory-lifecycle.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 18 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-doctor-preserve.sh` | migration-only | heuristic:path | medium | so-local-only |  |  | 10 | add sunset criteria and archive after retention window |
| `scripts/cos-doctor-tools.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 17 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-doctor-work-inventory.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-doctrine-proposer` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-engram-bundle` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 12 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-engram-import-propose` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-events.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-export-consumer-evidence` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-false-positive-ledger` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-federation-trigger-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-fingerprint.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 0 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-flow-register.sh` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-gate-stack.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-ghost-skills.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-git-sync.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-governance-roi` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-governed-agent.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-governed-edit.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-headless-publication` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-headless-safe-mode` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-import-consumer-evidence` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 10 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-init-global.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-init.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 45 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-lab-first-gate` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | blocking | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-locks.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 0 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-manifest-tier-claim-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-merge-queue-bench.sh` | lab | heuristic:path | medium | so-local-only |  |  | 1 | keep non-default until tests and operator value justify promotion |
| `scripts/cos-merge-queue-worker.sh` | agentic-primitive | wrapper | medium | so-local-only |  |  | 2 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-merge-queue.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-paperclip-local.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-postgres-local.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-pr-review.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-preamble-budget` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 6 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-project-registry-prune.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 0 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-python-stdin-antipattern-audit` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-recovery-drill` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-registry-lock` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | blocking | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-registry.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 14 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-release-check.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 6 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-run-task` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-runtime-hook-reality` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 5 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-self-improvement-discipline-gate` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | blocking | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-self-improvement-loop` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-session-branch.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-session-spawn.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-session-start-budget` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 7 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-sessions.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-silent-failure-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 9 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-smoke.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 7 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-startup-recover.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-status.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 22 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-tier-claim-audit` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | blocking | shell | 8 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-update.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 30 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-usage-report.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-validation-break.sh` | agentic-primitive | wrapper | medium | so-local-only |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-validation-capsule.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-validation-status.sh` | agentic-primitive | wrapper | medium | so-local-only |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos-valkey-local.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-weekly-config-audit.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 4 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos-weekly-primitive-gap.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-weekly-public-metrics.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-wip-safety-score` | agentic-primitive | lifecycle | high | lifecycle-declared-maintainer | advisory | shell | 5 | keep lifecycle evidence and supported harness declarations current |
| `scripts/cos-worktree-sweeper.sh` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos-worktree-triage.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_adoption_profile.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_architecture_readiness.py` | agentic-primitive | wrapper | medium | so-local-only |  |  | 11 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_boring_reliability.py` | agentic-primitive | wrapper | medium | so-local-only |  |  | 3 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_branch_lease.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_build_self_knowledge.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_chaos_template.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_claim_signature_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_classify_coverage.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_cleanup_preserved_wip.py` | migration-only | heuristic:path | medium | skill-referenced-not-projectable |  |  | 6 | add sunset criteria and archive after retention window |
| `scripts/cos_closure_discipline_audit.py` | agentic-primitive | wrapper | medium | so-local-only |  |  | 6 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_codex_guard.py` | driver-specific | heuristic:path | medium | so-local-only |  |  | 5 | declare supported harnesses and fallback behavior |
| `scripts/cos_concurrent_status.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_coordination_status.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_coverage.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_cross_instance_drill.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_cross_instance_learning.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_default_visible_reducer.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_demotion_loop_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_dispatch_smoke.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_doctrine_proposer.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_executor.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_false_positive_ledger.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_flow_register.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_governance_roi.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_governed_runner.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_governed_self_improvement.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_headless_publication.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_headless_safe_mode.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_init.py` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 13 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cos_manifest_tier_claim_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_preamble_budget.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_primitive_harvester.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 8 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_profile_bootstrap.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_recovery_drill.py` | agentic-primitive | wrapper | medium | so-local-only |  |  | 1 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_run_task.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_self_improvement_loop.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_session_backlog.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_sprint.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_task_claims.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_test_artifact_status.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_test_quality_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_tier_claim_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_watch.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_wip_safety_score.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_work_inventory.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 24 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cos_work_queue.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_worktree_sweeper.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/cos_worktree_triage.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/cost_predict.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 3 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/create-release.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 5 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/cross_session_reconciler.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/decision_triage.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 10 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/demo-first-run-onboarding.sh` | agentic-primitive | wrapper | medium | so-local-only |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/demo-governance.sh` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/demo-portability-proof.sh` | agentic-primitive | wrapper | medium | so-local-only |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/dependency-lane.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/deps-update.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 10 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/derived_artifact_gate.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/detect_runner_capacity.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/doc_review_personas.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/docs_duplicate_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/docs_execution_audit.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 7 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/doctor.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 29 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/document_feature_append.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 3 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/dogfood_score.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 9 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/domain_model.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 3 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/edit-coop.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 20 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/engram-sync.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/extract-agent-output.sh` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/generate-project-settings.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 20 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/generate_adversarial_scenario.py` | lab | override | high | so-local-only |  |  | 2 | keep non-default until tests and operator value justify promotion |
| `scripts/generate_compact_catalog.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 12 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/git-coop.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/harness-parity-audit` | driver-specific | override | high | so-local-only |  |  | 1 | declare supported harnesses and fallback behavior |
| `scripts/harness_parity_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/hook-stream-statusline.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 3 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/hook-timing-wrapper.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 18 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/hook_quality_audit.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/hook_timing_report.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/ide-bridge.sh` | driver-specific | override | high | so-local-only |  |  | 6 | declare supported harnesses and fallback behavior |
| `scripts/install-aguara.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-cos.sh` | maintainer-tool | override | high | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-garak.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 8 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/install-git-hooks.sh` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-launchd-jobs.sh` | driver-specific | override | high | so-local-only |  |  | 3 | declare supported harnesses and fallback behavior |
| `scripts/install-mcp-scan.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-pre-commit.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-promptfoo.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 10 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/install-timing-test.sh` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/install-tob-skills.sh` | maintainer-tool | override | high | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/invariant_check_helper.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/lab_first_promotion_gate.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/lint-shell.sh` | maintainer-tool | override | high | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/llm_status.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 6 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/manifest-check.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/measure_expansion.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/measure_harness_profiles.py` | driver-specific | heuristic:path | medium | so-local-only |  |  | 5 | declare supported harnesses and fallback behavior |
| `scripts/merge-settings.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/merge-to-main.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 9 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/migrate-to-cognitive-os.sh` | migration-only | heuristic:path | medium | so-local-only |  |  | 2 | add sunset criteria and archive after retention window |
| `scripts/ops_runbook.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 3 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/orchestrator.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 22 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/orchestrator_claim_gate.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/orphan_commit_scan.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/orphan_overwrite_detector.py` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/parity_harness.py` | driver-specific | heuristic:path | medium | so-local-only |  |  | 3 | declare supported harnesses and fallback behavior |
| `scripts/postinstall.js` | maintainer-tool | override | high | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/precommit_content_hash.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_backend_benchmark.py` | lab | heuristic:path | medium | so-local-only |  |  | 2 | keep non-default until tests and operator value justify promotion |
| `scripts/primitive_coverage.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_gap_snapshot.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 7 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_lifecycle.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_readiness_ledger.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_row_audit.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/primitive_surface_reduce.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 6 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/primitive_usage_map.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 8 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/project_scaffold.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 6 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/push_collision_detect.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/pytest-with-summary.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 28 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/python_stdin_antipattern_audit.py` | maintainer-tool | override | high | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/queue_throughput_bench.py` | lab | heuristic:path | medium | so-local-only |  |  | 3 | keep non-default until tests and operator value justify promotion |
| `scripts/radar_merge.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 4 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/redteam_aggregate.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/reduction_backlog.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/regen_catalog_bullets.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 2 | add sunset criteria and archive after retention window |
| `scripts/register-mcps.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 16 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/render_adoption_tiers.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/reserve_adr_slot.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 3 | add sunset criteria and archive after retention window |
| `scripts/resource_lease.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/review_pending_sweeper.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/risk_register.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 3 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/rules_export.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/run-adversarial-generalization.sh` | lab | override | high | so-local-only |  |  | 3 | keep non-default until tests and operator value justify promotion |
| `scripts/run-all-tests.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 11 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/run-redteam-scenario.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 8 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/run-runtime-benchmark.sh` | lab | heuristic:path | medium | so-local-only |  |  | 2 | keep non-default until tests and operator value justify promotion |
| `scripts/run_skill_efficacy_smoke.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/runtime_benchmark_report.py` | lab | heuristic:path | medium | so-local-only |  |  | 2 | keep non-default until tests and operator value justify promotion |
| `scripts/runtime_hook_reality.py` | maintainer-tool | override | high | so-local-only |  |  | 10 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/scope_tag_backfill.py` | migration-only | heuristic:path | medium | so-local-only |  |  | 1 | add sunset criteria and archive after retention window |
| `scripts/security_audit_writer.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/self_improvement_discipline_gate.py` | maintainer-tool | heuristic:self-evolution | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/semantic-lookup.mjs` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/session-leak-diagnostic.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/session_event_bus.py` | maintainer-tool | override | high | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/session_start_budget.py` | maintainer-tool | override | high | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/set-security-profile.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 42 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/setup-git-hooks.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/setup.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 22 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/shellcheck-baseline.txt` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/silent_failure_audit.py` | maintainer-tool | override | high | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/skill_efficacy_report.py` | maintainer-tool | override | high | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/smoke-agent-quota-advisor.sh` | maintainer-tool | override | high | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/smoke-agent-quota-redirect.sh` | maintainer-tool | override | high | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/smoke-doc-review-personas.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 1 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/smoke-multi-provider-fallback.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 2 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/smoke-qwen-fallback.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 5 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/so-emergency-stop.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/so-reaper.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 23 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/so-vitals.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 11 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/so_session_watchdog.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 9 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/so_vs_vanilla_benchmark.py` | lab | heuristic:path | medium | skill-referenced-not-projectable |  |  | 3 | keep non-default until tests and operator value justify promotion |
| `scripts/sprint-test-summary.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 2 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/startup-benchmark.sh` | lab | heuristic:path | medium | so-local-only |  |  | 6 | keep non-default until tests and operator value justify promotion |
| `scripts/stash-leak-alarm.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/statusline-coverage.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 2 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test-agent-teams-hooks.sh` | maintainer-tool | override | high | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test-all.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 8 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/test-cognitive-os-full.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 6 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/test-cognitive-os.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 6 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test-mcp-server.sh` | maintainer-tool | override | high | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/test_run_inventory.py` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 7 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/topology-discover.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 1 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/uninstall.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 18 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/update_readme_badges.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 3 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/upgrade.sh` | agentic-primitive | lifecycle | high | install-profile-managed | candidate | shell | 8 | profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive |
| `scripts/validate_tier_filter.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 4 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/verify-archived.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 11 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/verify_plan_claims.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 8 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/version.sh` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 5 | keep out of default user surface unless promoted through lifecycle metadata |
| `scripts/weekly-aspirational-audit.sh` | agentic-primitive | usage:skill | high | skill-referenced-not-projectable |  |  | 1 | add lifecycle metadata or explicit package boundary before claiming shared-agent support |
| `scripts/write_context_marker.py` | maintainer-tool | usage:repo | medium | so-local-only |  |  | 12 | keep out of default user surface unless promoted through lifecycle metadata |
