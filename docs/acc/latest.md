# Agent Capability Coverage — Latest

Generated: 2026-05-05T16:47:00Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 1.0000
- ACC effective: 1.0000
- Total weight: 2102
- Capabilities: 770
- Findings: 0
- Mapping weights: {'aligned': 2102, 'missing': 0, 'overexposed': 0, 'partial': 0, 'stale': 0, 'unverified': 0}
- New debt gate: pass (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 76, "patterns": 6, "statuses": {"maintainer-only": 57, "pattern:so-local-only": 6, "shell-ci-candidate": 15, "so-local-only": 4}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"aider/default": 73, "aider/full": 348, "amp-code/default": 73, "amp-code/full": 348, "augment-code/default": 73, "augment-code/full": 348, "claude/default": 73, "claude/full": 348, "cline/default": 73, "cline/full":` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": {"done_weak_proof": 2, "planned": 1}, "docs/README.md": {"done_weak_proof": 15, "planned": 17, "proposed": 6}, ` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 21, "planned": 5, "total": 26, "unsupported": 0}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/reports/proof-drill-evidence-latest.json` | `{"rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 128, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 116, "projected-consumer-surface": 11, "so-local-only": 86}, "roles": {"driver-specific": 12` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 43, "lab": 11}, "total": 112, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 151, "low": 6, "medium": 191}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 51, "lifecycle-declared-maintainer": 50, "s` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 52, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 87, "so-local-only": 4}, "roles": {"compatibility-wrapper": 52, "lab": 7, "project-extension": 16, "so-maintainer": 16}, "total": 91, "witho` |
| shell_ci_projection | ok | `manifests/shell-ci-projection.yaml` | `{"commands": 15, "profiles": ["default", "full"], "workflows": 1}` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|

## New Debt

| Capability | Status | Reason |
|---|---|---|
| none | pass | no new debt |

## Consumer Accessibility Counts

- maintainer-only: 57
- profile-driver: 19
- shell-ci-candidate: 15
- so-local-only: 679

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
