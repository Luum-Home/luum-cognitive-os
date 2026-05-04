# Agent Capability Coverage — Latest

Generated: 2026-05-04T21:09:31Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 1.0000
- ACC effective: 1.0000
- Total weight: 2000
- Capabilities: 734
- Findings: 0
- Mapping weights: {'aligned': 2000, 'missing': 0, 'overexposed': 0, 'partial': 0, 'stale': 0, 'unverified': 0}

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 49, "patterns": 6, "statuses": {"maintainer-only": 34, "pattern:so-local-only": 6, "shell-ci-candidate": 15}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"claude/default": 73, "claude/full": 347, "codex/default": 73, "codex/full": 347}, "projected_primitives": 369}` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": {"done_weak_proof": 2, "planned": 1}, "docs/README.md": {"done_weak_proof": 9, "planned": 8, "proposed": 4}, "d` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 2, "planned": 10, "total": 12, "unsupported": 0}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 126, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 114, "projected-consumer-surface": 11, "so-local-only": 86}, "roles": {"driver-specific": 12` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 43, "lab": 11}, "total": 112, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 137, "medium": 183}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 49, "lifecycle-declared-maintainer": 38, "skill-refer` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 51, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 86, "so-local-only": 4}, "roles": {"compatibility-wrapper": 51, "lab": 7, "project-extension": 16, "so-maintainer": 16}, "total": 90, "witho` |
| shell_ci_projection | ok | `manifests/shell-ci-projection.yaml` | `{"commands": 15, "profiles": ["default", "full"], "workflows": 1}` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|

## Consumer Accessibility Counts

- maintainer-only: 34
- profile-driver: 19
- shell-ci-candidate: 15
- so-local-only: 666

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
