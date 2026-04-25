# Python Script Naming — Snake Case Required

## Rule

Python scripts in `scripts/`, `lib/`, `packages/*/lib/`, and `tests/` MUST use snake_case
filenames (underscores, not hyphens).

## Rationale

Hyphens are not valid Python identifiers. Importing `scripts/foo-bar.py` from pytest or
another module requires `importlib` hacks (`spec_from_file_location`, `sys.modules`
registration) that:

- Break under Python 3.14 dataclass type resolution
- Fail under pytest collection intermittently (confirmed via commit 23b2ff5: hyphenated
  names prevented direct import and broke pytest collection in some environments)
- Add boilerplate to every consumer

Snake-case names are directly importable with `import foo_bar` — no wiring needed.

## Scope

| Path pattern | Rule | Notes |
|---|---|---|
| `scripts/*.py` | **MUST** use snake_case | Enforced by audit test |
| `lib/*.py` | **MUST** use snake_case | Enforced by audit test |
| `packages/*/lib/*.py` | **MUST** use snake_case | Enforced by audit test |
| `scripts/*.sh` | MAY use hyphens | Bash idiomatic — not Python-imported |
| `hooks/*.sh` | MAY use hyphens | Bash idiomatic — not Python-imported |

## Enforcement

- `tests/audit/test_python_naming.py` — greps `scripts/*-*.py` and `lib/*-*.py`, fails CI
  if any exist
- Any skill or hook that generates Python scripts (`skills/add-skill`, `skills/skill-creator`,
  etc.) MUST emit underscore-named files

## Generators

When a skill or hook writes a new Python script, the filename MUST be derived as:

```python
# CORRECT
script_name = feature_name.replace("-", "_") + ".py"

# WRONG — will fail audit test
script_name = feature_name + ".py"  # if feature_name contains hyphens
```

## Migration (2026-04-24)

35 scripts renamed from hyphen to underscore in commit containing this rule file.
All callers updated in the same commit. No backward-compat aliases.

Old → New mapping (full list):

| Old | New |
|---|---|
| `aspirational-audit.py` | `aspirational_audit.py` |
| `backfill-cost-events.py` | `backfill_cost_events.py` |
| `check-catalog-sync.py` | `check_catalog_sync.py` |
| `check-hook-registration.py` | `check_hook_registration.py` |
| `check-lib-wiring.py` | `check_lib_wiring.py` |
| `check-test-quality.py` | `check_test_quality.py` |
| `check-test-ratchet.py` | `check_test_ratchet.py` |
| `compose-agent-prompt.py` | `compose_agent_prompt.py` |
| `cos-build-self-knowledge.py` | `cos_build_self_knowledge.py` |
| `cos-chaos-template.py` | `cos_chaos_template.py` |
| `cos-classify-coverage.py` | `cos_classify_coverage.py` |
| `cos-executor.py` | `cos_executor.py` |
| `cos-sprint.py` | `cos_sprint.py` |
| `cos-test-quality-audit.py` | `cos_test_quality_audit.py` |
| `cos-watch.py` | `cos_watch.py` |
| `cos-work-queue.py` | `cos_work_queue.py` |
| `cost-predict.py` | `cost_predict.py` |
| `doc-review-personas.py` | `doc_review_personas.py` |
| `document-feature-append.py` | `document_feature_append.py` |
| `dogfood-score.py` | `dogfood_score.py` |
| `domain-model.py` | `domain_model.py` |
| `generate-compact-catalog.py` | `generate_compact_catalog.py` |
| `invariant-check-helper.py` | `invariant_check_helper.py` |
| `llm-status.py` | `llm_status.py` |
| `ops-runbook.py` | `ops_runbook.py` |
| `parity-harness.py` | `parity_harness.py` |
| `project-scaffold.py` | `project_scaffold.py` |
| `risk-register.py` | `risk_register.py` |
| `rules-export.py` | `rules_export.py` |
| `scope-tag-backfill.py` | `scope_tag_backfill.py` |
| `security-audit-writer.py` | `security_audit_writer.py` |
| `so-session-watchdog.py` | `so_session_watchdog.py` |
| `so-vs-vanilla-benchmark.py` | `so_vs_vanilla_benchmark.py` |
| `test-run-inventory.py` | `test_run_inventory.py` |
| `update-readme-badges.py` | `update_readme_badges.py` |

## Bash scripts exemption

`scripts/*.sh` and `hooks/*.sh` CAN use hyphens (e.g., `cos-bootstrap.sh`,
`aspirational-audit-weekly.sh`) — they are shell scripts, not Python modules.
