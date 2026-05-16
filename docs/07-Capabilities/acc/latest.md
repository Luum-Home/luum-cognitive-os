# Agent Capability Coverage — Latest

Generated: 2026-05-16T00:42:49Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.9322
- ACC effective: 0.9661
- Total weight: 6537
- Capabilities: 3138
- Findings: 184
- Mapping weights: {'aligned': 6094, 'missing': 0, 'overexposed': 0, 'partial': 443, 'stale': 0, 'unverified': 0}
- Primitive fitness reports: 0
- New debt gate: pass (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| authority_write_effects | ok | `docs/06-Daily/reports/primitive-authority-latest.json` | `{"block_count": 0, "by_mode": {"observe-only": 233, "os-maintainer-write": 265, "profile-projection-write": 35, "propose-only": 3}, "by_status": {"pass": 527, "warn": 9}, "dynamic_blocks": 0, "dynamic_smokes": 4, "total_scripts": 536}` |
| codebase_itinerary | unverified | `.cognitive-os/metrics/codebase-itinerary.jsonl` | `{}` |
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 905, "patterns": 6, "statuses": {"lifecycle-declared-maintainer": 1, "maintainer-only": 322, "pattern:so-local-only": 6, "projected-consumer-surface": 51, "shared-surface": 509, "shell-ci-candidate": 15, "so-local-only": 8}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"agents-md/default": 75, "agents-md/full": 384, "aider/default": 75, "aider/full": 384, "amp-code/default": 75, "amp-code/full": 384, "augment-code/default": 75, "augment-code/full": 384, "claude/default": 75, "claud` |
| docs_execution_report | ok | `docs/06-Daily/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 2}, "docs/00-MOCs/architecture.md": {"proposed": 2}, "docs/00-MOCs/decisions.md": {"done_with_proof": 1}, "docs/00-MOCs/entrypoints/HOW-TO-US` |
| documentation_truth | ok | `docs/06-Daily/reports/documentation-truth-latest.json` | `{"block_count": 0, "by_claim": {"consumer_projection_harnesses": {"pass": 17}, "documentation_truth_control": {"pass": 8}, "primitive_authority_write_effects": {"pass": 16}, "session_pending_protocol": {"pass": 75}, "subprocess_timeout_disc` |
| harness_coverage | ok | `docs/06-Daily/reports/primitive-harness-coverage-latest.json` | `{"by_family": {"hooks": 274, "rules": 123, "scripts": 603, "skills": 113, "templates": 23}, "by_scope": {"both": 468, "os-only": 640, "project": 28}, "gap_policies": {"acceptable-claude-only": 4, "acceptable-codex-limited-tool-events": 6, "` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 22, "planned": 5, "total": 27, "unsupported": 0}` |
| primitive_fitness_ledger | ok | `docs/06-Daily/reports/primitive-fitness-ledger-latest.json` | `{"families": {}, "mapping_statuses": {}, "reports": 0, "verdicts": {}}` |
| primitive_interventions | ok | `.cognitive-os/metrics/primitive-interventions.jsonl` | `{"actions": {"block": 3, "warn": 45}, "primitive_count": 4}` |
| projection_fidelity | ok | `docs/06-Daily/reports/primitive-projection-fidelity-latest.json` | `{"contracts": 308, "statuses": {"aligned": 308, "gap": 3}}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/06-Daily/reports/proof-drill-evidence-latest.json` | `{"claim_map": {"claims": 4, "proof_status_counts": {"passed": 4}}, "rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/06-Daily/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 264, "medium": 10}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 23, "lifecycle-declared-maintainer": 172, "projected-consumer-surface": 69, "so-local-only": 10}, "roles": {"driver-specific": 2` |
| readiness:rules | ok | `docs/06-Daily/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"high": 104, "medium": 19}, "consumer_accessibility": {"lifecycle-declared-maintainer": 117, "projected-consumer-surface": 5, "so-local-only": 1}, "roles": {"context-only": 1, "driver-specific": 11, "hook-enforced": 7, "lab"` |
| readiness:scripts | ok | `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 332, "low": 1, "medium": 270}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 149, "lifecycle-declared-maintainer": 138, ` |
| readiness:skills | ok | `docs/06-Daily/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 101, "medium": 12}, "consumer_accessibility": {"lifecycle-declared-maintainer": 98, "projected-consumer-surface": 7, "repo-skill-not-projectable": 3, "so-local-only": 5}, "roles": {"compatibility-wrapper": 46, "lab":` |
| readiness:templates | ok | `docs/06-Daily/reports/primitive-readiness-ledger-templates-latest.json` | `{"confidence": {"high": 10, "medium": 13}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 2, "lifecycle-declared-maintainer": 19, "projected-consumer-surface": 1, "so-local-only": 1}, "roles": {"agent-preamble": 1, "lab` |
| shell_ci_projection | ok | `manifests/shell-ci-projection.yaml` | `{"commands": 15, "profiles": ["default", "full"], "workflows": 1}` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|
| `script:scripts/adr_implementation_ledger.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/adr_tombstone.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/agent_work_ledger.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/approval_ledger.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/check_absolute_paths.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/check_test_quality.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/check_test_ratchet.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/claim_task.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-action-receipt` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-adapter-compile` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-adapters` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-adr-tombstone` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-agent-daemon` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-doctor-concurrency.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-doctor-preserve.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-doctor-work-inventory.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-document-ingest` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-fingerprint.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-gate-stack.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-git-sync.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-governed-agent.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-governed-edit.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-headless-pipeline` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-headless-safe-mode` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-key-learnings-capture` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-merge-queue-bench.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-merge-queue.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-orphan-process-audit.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-policy-settings-projection` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-portable-ai-consumer-impact` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-portable-ai-consumer-package-smoke` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-portable-ai-overlay` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-postgres-local.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-provider-call` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-remote-branch-triage` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-repair` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-repo-map` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-run-task` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-safe-clean` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-session-branch.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-team` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-validate` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-validation-capsule.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-valkey-local.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-wiki-ingest` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_agent_message.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_branch_lock.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_cleanup_preserved_wip.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_concurrent_status.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_coordination_status.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_key_learnings_capture.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_preamble_budget.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_remote_branch_triage.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_run_task.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_session_backlog.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_session_coordination.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_task_claims.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_test_quality_audit.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_wip_safety_score.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_work_inventory.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_worktree_sweeper.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_worktree_triage.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cost_predict.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/credibility-audit.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cross_session_reconciler.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/doc_review_personas.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/doctor.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/document_feature_append.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/documentation_truth_audit.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/domain_model.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/eas_validate.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/edit-coop.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/extract-agent-output.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook-timing-wrapper.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook_timing_report.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/ide-bridge.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/install-aguara.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/install-credibility-tools.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/install-mcp-scan.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/install-syft-grype.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |

## New Debt

| Capability | Status | Reason |
|---|---|---|
| none | pass | no new debt |

## Consumer Accessibility Counts

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 193
- lifecycle-declared-maintainer: 76
- maintainer-only: 315
- profile-driver: 19
- projected-consumer-surface: 1751
- runtime-evidence: 4
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 12
- so-local-only: 734

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
