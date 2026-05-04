# Agent Capability Coverage — Latest

Generated: 2026-05-04T19:33:19Z
Phase: reconstruction
Gate: pass

## Summary

- ACC: 0.2441
- ACC effective: 0.2933
- Total weight: 1979
- Capabilities: 725
- Findings: 160
- Mapping weights: {'aligned': 483, 'missing': 0, 'overexposed': 0, 'partial': 207, 'stale': 6, 'unverified': 1283}

## Adapter Status

| Adapter | Status | Source | Summary |
|---|---|---|---|
| cos_coverage | ok | `cos_coverage` | `{"aspirational": 38, "coverage_pct": 54.3, "dormant": 160, "generated_at": "2026-05-04T19:32:31Z", "mapped": 268, "metadata": 56, "on_demand": 287, "project": "<repo-root>", "real": 235, "tiers": {"A": 2, "B": 4, "C": 39, "D": 155}, "trend"` |
| docs_execution | ok | `docs_execution` | `{"items": 2434, "json": "<repo-root>/docs/reports/docs-execution-latest.json", "markdown": "<repo-root>/docs/reports/docs-execution-latest.md"}` |
| docs_execution_report | ok | `docs/reports/docs-execution-latest.json` | `{"documents": {"AGENTS.md": {"done_weak_proof": 1, "planned": 1}, "README.md": {"done_weak_proof": 1}, "docs/HOW-TO-USE-COS.md": {"done_weak_proof": 2, "planned": 1}, "docs/README.md": {"done_weak_proof": 9, "planned": 8, "proposed": 4}, "d` |
| family_readiness_hooks | ok | `family_readiness_hooks` | `{"confidence": {"high": 126, "medium": 85}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 114, "projected-consumer-surface": 11, "so-local-only": 85}, "json": "<repo-root>/docs/repor` |
| family_readiness_rules | ok | `family_readiness_rules` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "json": "<repo-root>/docs/reports/primitive-readiness-ledger-rules-latest.json", "markdown": "<repo-root>/docs/reports/primitive-readiness-ledger-rules-latest` |
| family_readiness_skills | ok | `family_readiness_skills` | `{"confidence": {"high": 51, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 86, "so-local-only": 4}, "json": "<repo-root>/docs/reports/primitive-readiness-ledger-skills-latest.json", "markdown": "<repo-root>/docs/rep` |
| primitive_gap_snapshot | ok | `primitive_gap_snapshot` | `{"families": [{"aspirational_signal": 2, "evidence": "row-audit proven=99 partial_nonblocking=133 actionable_gaps=2", "family": "hooks", "next_action": "close actionable rows", "partial_signal": 133, "proven_signal": 99, "severity": "high",` |
| readiness:hooks | ok | `docs/reports/primitive-readiness-ledger-hooks-latest.json` | `{"confidence": {"high": 126, "medium": 85}, "consumer_accessibility": {"lifecycle-declared-consumer-candidate": 1, "lifecycle-declared-maintainer": 114, "projected-consumer-surface": 11, "so-local-only": 85}, "roles": {"driver-specific": 12` |
| readiness:rules | ok | `docs/reports/primitive-readiness-ledger-rules-latest.json` | `{"confidence": {"medium": 112}, "consumer_accessibility": {"so-local-only": 112}, "roles": {"context-only": 6, "doctrine": 4, "driver-specific": 48, "hook-enforced": 43, "lab": 11}, "total": 112, "without_consumers": 0, "without_lifecycle":` |
| readiness:scripts | ok | `docs/reports/primitive-readiness-ledger-scripts-latest.json` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 135, "medium": 177}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 49, "lifecycle-declared-maintainer": 36, "skill-refer` |
| readiness:skills | ok | `docs/reports/primitive-readiness-ledger-skills-latest.json` | `{"confidence": {"high": 51, "medium": 39}, "consumer_accessibility": {"repo-skill-not-projectable": 86, "so-local-only": 4}, "roles": {"compatibility-wrapper": 51, "lab": 7, "project-extension": 16, "so-maintainer": 16}, "total": 90, "witho` |
| script_readiness_refresh | ok | `script_readiness_refresh` | `{"agentic_primitives_without_lifecycle": 0, "confidence": {"high": 135, "medium": 177}, "consumer_accessibility": {"install-profile-managed": 19, "lifecycle-declared-consumer-candidate": 49, "lifecycle-declared-maintainer": 36, "skill-refer` |

## Findings

| Capability | Severity | Status | Message | Next action |
|---|---|---|---|---|
| `script:scripts/apply-efficiency-profile.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/aspirational_audit.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/check_mcp_servers.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-bootstrap.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-config-audit.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-coordination-status.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-core-skills-check.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-doctor-harness.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-doctor-memory-lifecycle.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-doctor-tools.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-init.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-release-check.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-smoke.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-status.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-usage-report.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-weekly-config-audit.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos-worktree-triage.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_cleanup_preserved_wip.py` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `script:scripts/cos_init.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_primitive_harvester.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_session_backlog.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_work_inventory.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cos_worktree_triage.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/cost_predict.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/create-release.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/decision_triage.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/deps-update.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/doc_review_personas.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/docs_execution_audit.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/document_feature_append.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/dogfood_score.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/domain_model.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/edit-coop.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/generate-project-settings.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/generate_compact_catalog.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook-stream-statusline.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook-timing-wrapper.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/hook_timing_report.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/install-garak.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/install-promptfoo.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
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
| `script:scripts/set-security-profile.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/setup.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/smoke-doc-review-personas.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/smoke-multi-provider-fallback.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/smoke-qwen-fallback.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/so_vs_vanilla_benchmark.py` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `script:scripts/sprint-test-summary.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/test-all.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/test-cognitive-os-full.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/test_run_inventory.py` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/uninstall.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/upgrade.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/verify-archived.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `script:scripts/weekly-aspirational-audit.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `hook:hooks/task-completed.sh` | medium | partial | Candidate/projectable surface needs consumer projection proof | add harness projection proof before promotion |
| `skill:skills/__contracts__/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/__contracts__/canonical-event-emitter/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-hook/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-mcp/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-rule/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/add-skill/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/agent-dashboard/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/agent-stress-test/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |
| `skill:skills/analyze-improvements/SKILL.md` | medium | unverified | Represented locally but not proven projectable | add package/profile projection metadata |

## Consumer Accessibility Counts

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 50
- lifecycle-declared-maintainer: 150
- projected-consumer-surface: 11
- repo-skill-not-projectable: 86
- skill-referenced-not-projectable: 2
- so-local-only: 407

## Persistence

- Local history: `.cognitive-os/metrics/acc-pipeline-history.jsonl`
- Engram: unavailable
