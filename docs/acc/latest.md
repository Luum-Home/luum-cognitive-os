# Agent Capability Coverage — Latest

Generated: 2026-05-12T17:37:47Z
Phase: reconstruction
Gate: block

## Summary

- ACC: 0.9833
- ACC effective: 0.9899
- Total weight: 6180
- Capabilities: 2954
- Findings: 74
- Mapping weights: {'aligned': 6077, 'missing': 0, 'overexposed': 0, 'partial': 81, 'stale': 0, 'unverified': 22}
- Primitive fitness reports: 0
- New debt gate: block (14)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| authority_write_effects | ok | `docs/reports/primitive-authority-latest.json` | `{"block_count": 0, "by_mode": {"observe-only": 229, "os-maintainer-write": 264, "profile-projection-write": 35, "propose-only": 3}, "by_status": {"pass": 522, "warn": 9}, "dynamic_blocks": 0, "dynamic_smokes": 4, "total_scripts": 531}` |
| codebase_itinerary | ok | `.cognitive-os/metrics/codebase-itinerary.jsonl` | `{"categories": {"read": 686}, "rows": 686, "sessions": 685, "tools": {"Read": 686}}` |
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 90, "patterns": 6, "statuses": {"lifecycle-declared-maintainer": 3, "maintainer-only": 59, "pattern:so-local-only": 6, "shell-ci-candidate": 15, "so-local-only": 13}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"agents-md/default": 73, "agents-md/full": 396, "aider/default": 73, "aider/full": 396, "amp-code/default": 73, "amp-code/full": 396, "augment-code/default": 73, "augment-code/full": 396, "claude/default": 73, "claud` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": {"done_weak_proof": 2, "planned": 1}, "docs/README.md": {"done_weak_proof": 16, "planned": 19, "proposed": 7}, ` |
| documentation_truth | ok | `docs/reports/documentation-truth-latest.json` | `{"block_count": 0, "by_claim": {"consumer_projection_harnesses": {"pass": 17}, "documentation_truth_control": {"pass": 8}, "primitive_authority_write_effects": {"pass": 16}, "session_pending_protocol": {"pass": 75}}, "by_status": {"pass": 1` |
| harness_coverage | ok | `docs/reports/primitive-harness-coverage-latest.json` | `{"by_family": {"hooks": 266, "rules": 120, "scripts": 536, "skills": 101, "templates": 22}, "by_scope": {"None": 3, "both": 574, "os-only": 404, "project": 64}, "gap_policies": {"acceptable-claude-only": 4, "acceptable-codex-limited-tool-ev` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 22, "planned": 5, "total": 27, "unsupported": 0}` |
| primitive_fitness_ledger | ok | `docs/reports/primitive-fitness-ledger-latest.json` | `{"families": {}, "mapping_statuses": {}, "reports": 0, "verdicts": {}}` |
| primitive_interventions | ok | `.cognitive-os/metrics/primitive-interventions.jsonl` | `{"actions": {"advise": 4, "allow": 112, "block": 58, "suggest": 262, "warn": 86}, "primitive_count": 7}` |
| projection_fidelity | ok | `docs/reports/primitive-projection-fidelity-latest.json` | `{"contracts": 308, "statuses": {"aligned": 308, "gap": 3}}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/reports/proof-drill-evidence-latest.json` | `{"claim_map": {"claims": 4, "proof_status_counts": {"passed": 4}}, "rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 159, "medium": 107}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 141, "projected-consumer-surface": 17, "so-local-only": 107}, "roles": {"driver-specific": ` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 120}, "consumer_accessibility": {"so-local-only": 120}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 52, "hook-enforced": 47, "lab": 11}, "total": 120, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 11, "confidence": {"high": 180, "low": 23, "medium": 333}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 63, "lifecycle-declared-maintainer": 57, ` |
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
| `harness_coverage:rules/memory-governance.md` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:rules/recommendation-grounding.md` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/credibility-audit.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-credibility-tools.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-git-filter-repo.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-syft-grype.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/install-trivy.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/license-audit-syft-grype.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:scripts/license-audit-trivy.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:skills/deep-tool-research/SKILL.md` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `projection_fidelity:auto-verify` | medium | partial | Primitive projection fidelity has harness gaps | repair harness projection or downgrade declared fidelity |
| `projection_fidelity:auto-refine` | medium | partial | Primitive projection fidelity has harness gaps | repair harness projection or downgrade declared fidelity |
| `projection_fidelity:dod-gate` | medium | partial | Primitive projection fidelity has harness gaps | repair harness projection or downgrade declared fidelity |

## New Debt

| Capability | Status | Reason |
|---|---|---|
| `script:scripts/cos-documentation-truth-audit` | unreviewed-local-default | new capability matched a broad local-surface default instead of an explicit row or projection proof |
| `script:scripts/cos-portable-ai-consumer-package-smoke` | unreviewed-local-default | new capability matched a broad local-surface default instead of an explicit row or projection proof |
| `script:scripts/documentation_truth_audit.py` | unreviewed-local-default | new capability matched a broad local-surface default instead of an explicit row or projection proof |
| `script:scripts/portable_ai_consumer_package.py` | unreviewed-local-default | new capability matched a broad local-surface default instead of an explicit row or projection proof |
| `rule:rules/session-close-doc-truth.md` | unreviewed-local-default | new capability matched a broad local-surface default instead of an explicit row or projection proof |
| `template:templates/counsel-outreach/clean-room-permission.md` | unverified | new mapping debt |
| `template:templates/counsel-outreach/license-clarification.md` | unverified | new mapping debt |
| `template:templates/counsel-outreach/review-request.md` | unverified | new mapping debt |
| `projection_fidelity:auto-verify` | partial | new mapping debt |
| `projection_fidelity:auto-refine` | partial | new mapping debt |
| `projection_fidelity:dod-gate` | partial | new mapping debt |
| `projection_fidelity:auto-verify` | partial | Primitive projection fidelity has harness gaps |
| `projection_fidelity:auto-refine` | partial | Primitive projection fidelity has harness gaps |
| `projection_fidelity:dod-gate` | partial | Primitive projection fidelity has harness gaps |

## Consumer Accessibility Counts

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 65
- lifecycle-declared-maintainer: 58
- maintainer-only: 59
- profile-driver: 19
- projected-consumer-surface: 1355
- runtime-evidence: 8
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 2
- so-local-only: 1354

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
