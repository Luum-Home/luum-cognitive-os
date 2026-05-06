# Agent Capability Coverage — Latest

Generated: 2026-05-06T07:50:28Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.9974
- ACC effective: 0.9987
- Total weight: 2331
- Capabilities: 848
- Findings: 2
- Mapping weights: {'aligned': 2325, 'missing': 0, 'overexposed': 0, 'partial': 6, 'stale': 0, 'unverified': 0}
- Primitive fitness reports: 0
- New debt gate: pass (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 88, "patterns": 6, "statuses": {"lifecycle-declared-maintainer": 3, "maintainer-only": 57, "pattern:so-local-only": 6, "shell-ci-candidate": 15, "so-local-only": 13}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"aider/default": 73, "aider/full": 373, "amp-code/default": 73, "amp-code/full": 373, "augment-code/default": 73, "augment-code/full": 373, "claude/default": 73, "claude/full": 373, "cline/default": 73, "cline/full":` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"docs/adrs/ADR-044-context-payload-slimming.md": {"done_weak_proof": 2, "proposed": 1}, "docs/adrs/ADR-045-postgres-local-daemon.md": {"done_weak_proof": 2, "planned": 2}, "docs/adrs/ADR-047-session-lifecycle-management.md": {"done_weak_pr` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 21, "planned": 5, "total": 26, "unsupported": 0}` |
| primitive_fitness_ledger | ok | `docs/reports/primitive-fitness-ledger-latest.json` | `{"families": {}, "mapping_statuses": {}, "reports": 0, "verdicts": {}}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/reports/proof-drill-evidence-latest.json` | `{"claim_map": {"claims": 4, "proof_status_counts": {"passed": 4}}, "rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 152, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 138, "projected-consumer-surface": 13, "so-local-only": 86}, "roles": {"driver-specific": 14` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 113}, "consumer_accessibility": {"so-local-only": 113}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 44, "lab": 11}, "total": 113, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 159, "low": 8, "medium": 227}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 56, "lifecycle-declared-maintainer": 53, "s` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 55, "medium": 39}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "repo-skill-not-projectable": 89, "so-local-only": 4}, "roles": {"compatibility-wrapper": 55, "lab": 7, "project-extension": 1` |
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
- so-local-only: 754

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
