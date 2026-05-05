# Agent Capability Coverage — Latest

Generated: 2026-05-05T17:37:53Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.9973
- ACC effective: 0.9986
- Total weight: 2196
- Capabilities: 802
- Findings: 2
- Mapping weights: {'aligned': 2190, 'missing': 0, 'overexposed': 0, 'partial': 6, 'stale': 0, 'unverified': 0}
- New debt gate: not_evaluated (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 88, "patterns": 6, "statuses": {"lifecycle-declared-maintainer": 3, "maintainer-only": 57, "pattern:so-local-only": 6, "shell-ci-candidate": 15, "so-local-only": 13}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"aider/default": 73, "aider/full": 352, "amp-code/default": 73, "amp-code/full": 352, "augment-code/default": 73, "augment-code/full": 352, "claude/default": 73, "claude/full": 352, "cline/default": 73, "cline/full":` |
| cos_coverage | ok | `cos_coverage` | `{"aspirational": 38, "coverage_pct": 54.3, "dormant": 160, "generated_at": "2026-05-05T17:35:52Z", "mapped": 268, "metadata": 56, "on_demand": 287, "project": "<repo-root>", "real": 235, "tiers": {"A": 2, "B": 4, "C": 39, "D": 155}, "trend"` |
| docs_execution | ok | `docs_execution` | `{"items": 2778, "json": "<repo-root>/docs/reports/docs-execution-latest.json", "markdown": "<repo-root>/docs/reports/docs-execution-latest.md"}` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": {"done_weak_proof": 2, "planned": 1}, "docs/README.md": {"done_weak_proof": 16, "planned": 19, "proposed": 6}, ` |
| family_readiness_hooks | ok | `family_readiness_hooks` | `{"confidence": {"high": 132, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 120, "projected-consumer-surface": 11, "so-local-only": 86}, "json": "<repo-root>/docs/repor` |
| family_readiness_rules | ok | `family_readiness_rules` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "json": "<repo-root>/docs/reports/primitive-readiness-ledger-rules-latest.json", "markdown": "<repo-root>/docs/reports/primitive-readiness-ledger-rules-latest` |
| family_readiness_skills | ok | `family_readiness_skills` | `{"confidence": {"high": 53, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 88, "so-local-only": 4}, "json": "<repo-root>/docs/reports/primitive-readiness-ledger-skills-latest.json", "markdown": "<repo-root>/docs/rep` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 21, "planned": 5, "total": 26, "unsupported": 0}` |
| primitive_duplication | ok | `primitive_duplication` | `{"by_common_home": {"lib/": 5}, "by_consumer_relevance": {"so-local-first": 5}, "by_kind": {"python-function-repeat": 5}, "files_scanned": 772, "findings": 5}` |
| primitive_gap_snapshot | ok | `primitive_gap_snapshot` | `{"families": [{"aspirational_signal": 3, "evidence": "row-audit proven=100 partial_nonblocking=135 actionable_gaps=3", "family": "hooks", "next_action": "close actionable rows", "partial_signal": 135, "proven_signal": 100, "severity": "high` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| proof_drill_evidence | ok | `docs/reports/proof-drill-evidence-latest.json` | `{"claim_map": {"claims": 4, "proof_status_counts": {"passed": 4}}, "rows": 5, "status_counts": {"passed": 5}}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 132, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 120, "projected-consumer-surface": 11, "so-local-only": 86}, "roles": {"driver-specific": 13` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 43, "lab": 11}, "total": 112, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 154, "low": 8, "medium": 209}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 53, "lifecycle-declared-maintainer": 51, "s` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 53, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 88, "so-local-only": 4}, "roles": {"compatibility-wrapper": 53, "lab": 7, "project-extension": 16, "so-maintainer": 16}, "total": 92, "witho` |
| script_readiness_refresh | failed | `script_readiness_refresh` | `{}` |
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
- so-local-only: 708

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
