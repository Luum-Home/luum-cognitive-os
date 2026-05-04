# Agent Capability Coverage — Latest

Generated: 2026-05-04T22:29:02Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 1.0000
- ACC effective: 1.0000
- Total weight: 2000
- Capabilities: 734
- Findings: 0
- Mapping weights: {'aligned': 2000, 'missing': 0, 'overexposed': 0, 'partial': 0, 'stale': 0, 'unverified': 0}
- New debt gate: pass (0)

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_availability | ok | `manifests/primitive-consumer-availability.yaml` | `{"items": 49, "patterns": 6, "statuses": {"maintainer-only": 34, "pattern:so-local-only": 6, "shell-ci-candidate": 15}}` |
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"claude/default": 73, "claude/full": 347, "codex/default": 73, "codex/full": 347, "cursor/default": 73, "cursor/full": 347, "kimi-code/default": 73, "kimi-code/full": 347, "opencode/default": 73, "opencode/full": 347` |
| cos_coverage | ok | `cos_coverage` | `{"aspirational": 38, "coverage_pct": 54.3, "dormant": 160, "generated_at": "2026-05-04T22:27:43Z", "mapped": 268, "metadata": 56, "on_demand": 287, "project": "<repo-root>", "real": 235, "tiers": {"A": 2, "B": 4, "C": 39, "D": 155}, "trend"` |
| docs_execution | ok | `docs_execution` | `{"items": 2612, "json": "<repo-root>/docs/reports/docs-execution-latest.json", "markdown": "<repo-root>/docs/reports/docs-execution-latest.md"}` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": {"done_weak_proof": 2, "planned": 1}, "docs/README.md": {"done_weak_proof": 13, "planned": 14, "proposed": 4}, ` |
| family_readiness_hooks | ok | `family_readiness_hooks` | `{"confidence": {"high": 126, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 114, "projected-consumer-surface": 11, "so-local-only": 86}, "json": "<repo-root>/docs/repor` |
| family_readiness_rules | ok | `family_readiness_rules` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "json": "<repo-root>/docs/reports/primitive-readiness-ledger-rules-latest.json", "markdown": "<repo-root>/docs/reports/primitive-readiness-ledger-rules-latest` |
| family_readiness_skills | ok | `family_readiness_skills` | `{"confidence": {"high": 51, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 86, "so-local-only": 4}, "json": "<repo-root>/docs/reports/primitive-readiness-ledger-skills-latest.json", "markdown": "<repo-root>/docs/rep` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 8, "planned": 4, "total": 12, "unsupported": 0}` |
| primitive_duplication | ok | `primitive_duplication` | `{"by_common_home": {"hooks/_lib/": 4, "lib/": 40, "scripts/_lib/": 4, "templates/ or lib/": 1}, "by_consumer_relevance": {"consumer-project-relevant": 7, "so-local-first": 42}, "by_kind": {"bash-function-repeat": 8, "exact-copy": 1, "python` |
| primitive_gap_snapshot | ok | `primitive_gap_snapshot` | `{"families": [{"aspirational_signal": 2, "evidence": "row-audit proven=99 partial_nonblocking=133 actionable_gaps=2", "family": "hooks", "next_action": "close actionable rows", "partial_signal": 133, "proven_signal": 99, "severity": "high",` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 126, "medium": 86}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 114, "projected-consumer-surface": 11, "so-local-only": 86}, "roles": {"driver-specific": 12` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 43, "lab": 11}, "total": 112, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 137, "medium": 183}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 49, "lifecycle-declared-maintainer": 38, "skill-refer` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 51, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 86, "so-local-only": 4}, "roles": {"compatibility-wrapper": 51, "lab": 7, "project-extension": 16, "so-maintainer": 16}, "total": 90, "witho` |
| script_readiness_refresh | ok | `script_readiness_refresh` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 137, "medium": 183}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 49, "lifecycle-declared-maintainer": 38, "skill-refer` |
| shell_ci_projection | ok | `manifests/shell-ci-projection.yaml` | `{"commands": 15, "profiles": ["default", "full"], "workflows": 1}` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|

## New Debt

| Capability | Status | Reason |
|---|---|---|
| none | pass | no new debt |

## Consumer Accessibility Counts

- maintainer-only: 34
- profile-driver: 19
- shell-ci-candidate: 15
- so-local-only: 666

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
