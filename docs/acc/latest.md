# Agent Capability Coverage — Latest

Generated: 2026-05-12T18:44:49Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.9839
- ACC effective: 0.9902
- Total weight: 6201
- Capabilities: 2962
- Findings: 71
- Mapping weights: {'aligned': 6101, 'missing': 0, 'overexposed': 0, 'partial': 78, 'stale': 0, 'unverified': 22}
- Primitive fitness reports: 0
- New debt gate: pass (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| authority_write_effects | ok | `docs/reports/primitive-authority-latest.json` | `{"block_count": 0, "by_mode": {"observe-only": 233, "os-maintainer-write": 265, "profile-projection-write": 35, "propose-only": 3}, "by_status": {"pass": 527, "warn": 9}, "dynamic_blocks": 0, "dynamic_smokes": 4, "total_scripts": 536}` |
| codebase_itinerary | ok | `.cognitive-os/metrics/codebase-itinerary.jsonl` | `{"categories": {"read": 744}, "rows": 744, "sessions": 742, "tools": {"Read": 744}}` |
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 91, "patterns": 6, "statuses": {"lifecycle-declared-maintainer": 3, "maintainer-only": 60, "pattern:so-local-only": 6, "shell-ci-candidate": 15, "so-local-only": 13}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"agents-md/default": 73, "agents-md/full": 396, "aider/default": 73, "aider/full": 396, "amp-code/default": 73, "amp-code/full": 396, "augment-code/default": 73, "augment-code/full": 396, "claude/default": 73, "claud` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 2}, "docs/00-MOCs/architecture.md": {"proposed": 2}, "docs/00-MOCs/decisions.md": {"done_with_proof": 1}, "docs/00-MOCs/operations.md": {"don` |
| documentation_truth | ok | `docs/reports/documentation-truth-latest.json` | `{"block_count": 0, "by_claim": {"consumer_projection_harnesses": {"pass": 17}, "documentation_truth_control": {"pass": 8}, "primitive_authority_write_effects": {"pass": 16}, "session_pending_protocol": {"pass": 75}, "subprocess_timeout_disc` |
| harness_coverage | ok | `docs/reports/primitive-harness-coverage-latest.json` | `{"by_family": {"hooks": 266, "rules": 120, "scripts": 537, "skills": 101, "templates": 22}, "by_scope": {"both": 578, "os-only": 404, "project": 64}, "gap_policies": {"acceptable-claude-only": 4, "acceptable-codex-limited-tool-events": 6, "` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 22, "planned": 5, "total": 27, "unsupported": 0}` |
| primitive_fitness_ledger | ok | `docs/reports/primitive-fitness-ledger-latest.json` | `{"families": {}, "mapping_statuses": {}, "reports": 0, "verdicts": {}}` |
| primitive_interventions | ok | `.cognitive-os/metrics/primitive-interventions.jsonl` | `{"actions": {"advise": 4, "allow": 125, "block": 58, "suggest": 346, "warn": 92}, "primitive_count": 7}` |
| projection_fidelity | ok | `docs/reports/primitive-projection-fidelity-latest.json` | `{"contracts": 308, "statuses": {"aligned": 308, "gap": 3}}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/reports/proof-drill-evidence-latest.json` | `{"claim_map": {"claims": 4, "proof_status_counts": {"passed": 4}}, "rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 159, "medium": 107}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 141, "projected-consumer-surface": 17, "so-local-only": 107}, "roles": {"driver-specific": ` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 120}, "consumer_accessibility": {"so-local-only": 120}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 52, "hook-enforced": 47, "lab": 11}, "total": 120, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 181, "low": 23, "medium": 333}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 73, "lifecycle-declared-maintainer": 58, "` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 62, "medium": 39}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 2, "repo-skill-not-projectable": 94, "so-local-only": 5}, "roles": {"compatibility-wrapper": 62, "lab": 8, "project-extension": 1` |
| readiness:templates | ok | `docs/reports/primitive-readiness-ledger-templates-latest.json` | `{"confidence": {"medium": 22}, "consumer_accessibility": {"so-local-only": 22}, "roles": {"agent-preamble": 1, "prompt-composition": 11, "quality-gate": 9, "recovery": 1}, "total": 22, "without_consumers": 4, "without_lifecycle": 22}` |
| shell_ci_projection | ok | `manifests/shell-ci-projection.yaml` | `{"commands": 15, "profiles": ["default", "full"], "workflows": 1}` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|
| `script:scripts/cos-key-learnings-capture` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/security-red-team` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `harness_coverage:hooks/agent-control-inbound-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-launch-confirmed.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/ai-provider-identity-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/contextual-rule-loader.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/cosd-auth-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/doc-sync-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/dod-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/dry-run-preview.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/ecosystem-check.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/edit-lock-drain-parked.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/edit-lock-pre-tool.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/engram-reinforce-on-access.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/epic-task-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/error-pattern-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/global-verify.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/guardrails-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/infra-intent-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/inject-phase-context.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/jupyter-sandbox.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/large-file-advisor.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/notify.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/orchestrator-decision-trace.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/orchestrator-mode-detect.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/parry-scan.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/pending-truth-drift-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/plan-claim-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/post-agent-verify.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/pre-agent-snapshot.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/pre-cleanup-snapshot.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/pre-commit-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/predev-completeness-check.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/private-mode-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/private-mode-metrics-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/project-docs-convention.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/prompt-quality-llm.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/protected-config-write-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/query-tailored-context-inject.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/rate-limit-protection.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/reinvention-check.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/research-quality-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/resource-check.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/scope-creep-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/scope-proportionality.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/secret-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/semgrep-scan.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/session-end-cleanup.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/skill-frontmatter-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/skill-post-execution-analysis.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/state-retention-audit.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/subagent-capability-preflight.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/surface-fix-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/task-completed.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/task-panel-sync.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/task-recorder.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/token-budget-monitor.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/tool-loop-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/trust-score-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/valkey-ensure.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/worktree-submodule-fix.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/credibility-audit.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-credibility-tools.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-git-filter-repo.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-syft-grype.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-trivy.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/license-audit-syft-grype.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/license-audit-trivy.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `projection_fidelity:auto-verify` | medium | partial | Primitive projection fidelity has harness gaps | repair harness projection or downgrade declared fidelity |
| `projection_fidelity:auto-refine` | medium | partial | Primitive projection fidelity has harness gaps | repair harness projection or downgrade declared fidelity |
| `projection_fidelity:dod-gate` | medium | partial | Primitive projection fidelity has harness gaps | repair harness projection or downgrade declared fidelity |

## New Debt

| Capability | Status | Reason |
|---|---|---|
| none | pass | no new debt |

## Consumer Accessibility Counts

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 65
- lifecycle-declared-maintainer: 58
- maintainer-only: 60
- profile-driver: 19
- projected-consumer-surface: 1356
- runtime-evidence: 8
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 12
- so-local-only: 1350

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
