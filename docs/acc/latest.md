# Agent Capability Coverage — Latest

Generated: 2026-05-06T08:02:28Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.9320
- ACC effective: 0.9631
- Total weight: 3208
- Capabilities: 1725
- Findings: 195
- Mapping weights: {'aligned': 2990, 'missing': 0, 'overexposed': 0, 'partial': 199, 'stale': 0, 'unverified': 19}
- Primitive fitness reports: 0
- New debt gate: pass (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 88, "patterns": 6, "statuses": {"lifecycle-declared-maintainer": 3, "maintainer-only": 57, "pattern:so-local-only": 6, "shell-ci-candidate": 15, "so-local-only": 13}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"aider/default": 73, "aider/full": 373, "amp-code/default": 73, "amp-code/full": 373, "augment-code/default": 73, "augment-code/full": 373, "claude/default": 73, "claude/full": 373, "cline/default": 73, "cline/full":` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"docs/adrs/ADR-044-context-payload-slimming.md": {"done_weak_proof": 2, "proposed": 1}, "docs/adrs/ADR-045-postgres-local-daemon.md": {"done_weak_proof": 2, "planned": 2}, "docs/adrs/ADR-047-session-lifecycle-management.md": {"done_weak_pr` |
| harness_coverage | ok | `docs/reports/primitive-harness-coverage-latest.json` | `{"by_family": {"hooks": 238, "rules": 113, "scripts": 394, "skills": 94, "templates": 19}, "by_scope": {"both": 501, "os-only": 301, "project": 56}, "gap_policies": {"acceptable-claude-only": 4, "behavior-proof-needed": 89, "codex-adapter":` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 21, "planned": 5, "total": 26, "unsupported": 0}` |
| primitive_fitness_ledger | ok | `docs/reports/primitive-fitness-ledger-latest.json` | `{"families": {}, "mapping_statuses": {}, "reports": 0, "verdicts": {}}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/reports/proof-drill-evidence-latest.json` | `{"claim_map": {"claims": 4, "proof_status_counts": {"passed": 4}}, "rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 152, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 138, "projected-consumer-surface": 13, "so-local-only": 86}, "roles": {"driver-specific": 14` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 113}, "consumer_accessibility": {"so-local-only": 113}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 44, "lab": 11}, "total": 113, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 159, "low": 8, "medium": 227}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 56, "lifecycle-declared-maintainer": 53, "s` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 55, "medium": 39}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "repo-skill-not-projectable": 89, "so-local-only": 4}, "roles": {"compatibility-wrapper": 55, "lab": 7, "project-extension": 1` |
| readiness:templates | ok | `docs/reports/primitive-readiness-ledger-templates-latest.json` | `{"confidence": {"medium": 19}, "consumer_accessibility": {"so-local-only": 19}, "roles": {"agent-preamble": 1, "prompt-composition": 8, "quality-gate": 9, "recovery": 1}, "total": 19, "without_consumers": 4, "without_lifecycle": 19}` |
| shell_ci_projection | ok | `manifests/shell-ci-projection.yaml` | `{"commands": 15, "profiles": ["default", "full"], "workflows": 1}` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|
| `script:scripts/cos-key-learnings-capture` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/security-red-team` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `harness_coverage:hooks/aci-observation-capture.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/adaptive-bypass.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/adr-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/adr-relevance-suggest.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/adr-section-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-bash-cwd-enforcer.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-bus-monitor.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-checkpoint.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-message-inbox-context.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-message-inbox-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-output-verifier.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-prelaunch.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-quota-advisor.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-qwen-bridge.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/agent-working-dir-inject.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/aguara-scan.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/architecture-compliance.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/aspirational-audit-weekly.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/assumption-tracker.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/audit-id-enricher.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/auto-checkpoint.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/auto-refine.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/auto-repair-dispatcher.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/auto-rollback-trigger.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/auto-skill-generator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/auto-verify.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/background-agent-reminder.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/blast-radius.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/branch-ownership-lock.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/branch-ownership-release.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/claim-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/clarification-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/clarification-interceptor.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/code-review-on-commit.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/completeness-check-llm.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/completeness-check.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/completion-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/concurrent-write-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/confidence-gate-llm.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/confidence-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/confidentiality-enforcer.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/consequence-evaluator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/content-policy.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/context-budget-meter.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/context-diet.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/context-watchdog.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/contextual-rule-loader.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/cos-executor-daemon-launcher.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/crash-recovery.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/cross-session-coordination-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/cross-session-event-emit.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/cross-session-peer-context.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/dangerous-env-flag-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/dequeue-notify.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/destructive-rm-blocker.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/direct-main-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/dispatch-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/doc-sync-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/docker-drift-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/dod-gate.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/dry-run-preview.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/ecosystem-check.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/edit-lock-drain-parked.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/edit-lock-pre-tool.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/edit-lock-process-negotiations.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/edit-lock-session-end.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/engram-crystallize-on-session-end.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/engram-daemon-launcher.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/engram-obsidian-export-on-stop.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/engram-reinforce-on-access.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/epic-task-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/error-learning.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/error-pattern-detector.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/error-pipeline.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/git-commit-scope-guard.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/git-context-capture.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/global-verify.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |
| `harness_coverage:hooks/guardrails-validator.sh` | medium | partial | Harness implementation coverage gap | classify the gap policy or add the missing harness projection/proof |

## New Debt

| Capability | Status | Reason |
|---|---|---|
| none | pass | no new debt |

## Consumer Accessibility Counts

- lifecycle-declared-consumer-candidate: 2
- lifecycle-declared-maintainer: 1
- maintainer-only: 57
- profile-driver: 19
- projected-consumer-surface: 347
- shell-ci-candidate: 15
- so-local-only: 1284

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
