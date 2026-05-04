# Agent Capability Coverage — Latest

Generated: 2026-05-04T20:46:31Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.4814
- ACC effective: 0.5183
- Total weight: 1994
- Capabilities: 732
- Findings: 89
- Mapping weights: {'aligned': 960, 'missing': 0, 'overexposed': 0, 'partial': 147, 'stale': 0, 'unverified': 887}

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| consumer_projection | ok | `consumer_projection` | `{"by_harness_profile": {"claude/default": 58, "claude/full": 332, "codex/default": 58, "codex/full": 332}, "projected_primitives": 354}` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": {"done_weak_proof": 2, "planned": 1}, "docs/README.md": {"done_weak_proof": 9, "planned": 8, "proposed": 4}, "d` |
| harness_projection | ok | `manifests/harness-projection.yaml` | `{"implemented": 2, "planned": 10, "total": 12, "unsupported": 0}` |
| projection_profiles | ok | `manifests/primitive-projection-profiles.yaml` | `{"profile_driver_scripts": 19, "profiles": ["default", "full"], "projection_classes": ["default", "full", "maintainer-only", "profile-driver", "shared"]}` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 126, "medium": 85}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 114, "projected-consumer-surface": 11, "so-local-only": 85}, "roles": {"driver-specific": 12` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 43, "lab": 11}, "total": 112, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 137, "medium": 182}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 49, "lifecycle-declared-maintainer": 38, "skill-refer` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 51, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 86, "so-local-only": 4}, "roles": {"compatibility-wrapper": 51, "lab": 7, "project-extension": 16, "so-maintainer": 16}, "total": 90, "witho` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|
| `script:scripts/aspirational_audit.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/check_mcp_servers.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-coordination-status.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-release-check.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-smoke.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-status.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-usage-report.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-worktree-triage.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_cleanup_preserved_wip.py` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `script:scripts/cos_primitive_harvester.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_session_backlog.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_work_inventory.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_worktree_triage.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cost_predict.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/decision_triage.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/doc_review_personas.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/docs_execution_audit.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/document_feature_append.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/dogfood_score.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/domain_model.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/edit-coop.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/generate_compact_catalog.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook-stream-statusline.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook-timing-wrapper.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook_timing_report.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/invariant_check_helper.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/llm_status.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/merge-to-main.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/ops_runbook.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/primitive_surface_reduce.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/primitive_usage_map.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/project_scaffold.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/pytest-with-summary.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/radar_merge.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/redteam_aggregate.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/risk_register.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/rules_export.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/run-all-tests.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/run-redteam-scenario.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/security_audit_writer.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/smoke-doc-review-personas.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/smoke-multi-provider-fallback.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/smoke-qwen-fallback.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/so_vs_vanilla_benchmark.py` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `script:scripts/sprint-test-summary.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/test-all.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/test-cognitive-os-full.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/test_run_inventory.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/verify-archived.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/weekly-aspirational-audit.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `skill:skills/__contracts__/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/__contracts__/canonical-event-emitter/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-hook/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-mcp/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-rule/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-skill/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/agent-dashboard/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/agent-stress-test/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/audit-integrity/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/bump-version/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/cognitive-os-test/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/compat-test/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/component-classifier/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/component-reality-check/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/coordination-status/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/deps-update/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/detect-patterns/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/docs-execution-audit/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/dogfood-score/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/experimental/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/generate-changelog/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/hook-timing/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/memory-scan/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/pattern-audit/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/peer-card/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/primitive-surface-reduction/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/primitive-usage-map/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/push-release/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/queue-drain/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |

## Consumer Accessibility Counts

- lifecycle-declared-consumer-candidate: 49
- lifecycle-declared-maintainer: 74
- projected-consumer-surface: 297
- repo-skill-not-projectable: 38
- skill-referenced-not-projectable: 2
- so-local-only: 272

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
