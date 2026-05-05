# Agent Capability Coverage — Latest

Generated: 2026-05-05T19:21:42Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.9973
- ACC effective: 0.9986
- Total weight: 2208
- Capabilities: 806
- Findings: 2
- Mapping weights: {'aligned': 2202, 'missing': 0, 'overexposed': 0, 'partial': 6, 'stale': 0, 'unverified': 0}
- Primitive fitness reports: 0
- New debt gate: pass (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 88, "patterns": 6, "statuses": {"lifecycle-declared-maintainer": 3, "maintainer-only": 57, "pattern:so-local-only": 6, "shell-ci-candidate": 15, "so-local-only": 13}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"aider/default": 73, "aider/full": 352, "amp-code/default": 73, "amp-code/full": 352, "augment-code/default": 73, "augment-code/full": 352, "claude/default": 73, "claude/full": 352, "cline/default": 73, "cline/full":` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {".cognitive-os/plans/research/cognitive-os-security-assessment-plan.md": {"done_weak_proof": 1, "planned": 2}, "AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": ` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 21, "planned": 5, "total": 26, "unsupported": 0}` |
| primitive_fitness_ledger | ok | `docs/reports/primitive-fitness-ledger-latest.json` | `{"families": {}, "mapping_statuses": {}, "reports": 0, "verdicts": {}}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/reports/proof-drill-evidence-latest.json` | `{"claim_map": {"claims": 4, "proof_status_counts": {"passed": 4}}, "rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 132, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 120, "projected-consumer-surface": 11, "so-local-only": 86}, "roles": {"driver-specific": 13` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 43, "lab": 11}, "total": 112, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 154, "low": 8, "medium": 213}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 53, "lifecycle-declared-maintainer": 51, "s` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 53, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 88, "so-local-only": 4}, "roles": {"compatibility-wrapper": 53, "lab": 7, "project-extension": 16, "so-maintainer": 16}, "total": 92, "witho` |
| shell_ci_projection | ok | `manifests/shell-ci-projection.yaml` | `{"commands": 15, "profiles": ["default", "full"], "workflows": 1}` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|
| `script:scripts/cos-key-learnings-capture` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/security-red-team` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |

## New Debt

| Capability | Status | Reason |
|---|---|---|
| none | pass | no new debt |

## Consumer Accessibility Counts

- lifecycle-declared-consumer-candidate: 2
- lifecycle-declared-maintainer: 1
- maintainer-only: 57
- profile-driver: 19
- shell-ci-candidate: 15
- so-local-only: 712

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
