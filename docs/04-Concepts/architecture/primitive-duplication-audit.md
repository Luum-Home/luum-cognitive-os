# Primitive Duplication Audit

The Primitive Duplication Audit detects repeated implementation and configuration patterns across Cognitive OS surfaces and turns them into refactor candidates with SO-specific recommendations.

## Why this exists

Generic clone detectors can say “these files are similar.” Cognitive OS also needs to know:

- whether repeated behavior belongs in `lib/`, `hooks/_lib/`, `scripts/_lib/`, `manifests/`, `templates/`, `rules/`, or `skills/`;
- whether the duplicated surface is SO-local or consumer-project relevant;
- whether refactoring could affect Claude/Codex or future harness projection;
- whether duplication is intentional because of portability, isolation, or harness-specific behavior.

## Existing pieces it complements

| Existing tool | Scope | Gap covered by primitive duplication audit |
|---|---|---|
| `scripts/docs_duplicate_audit.py` | Markdown duplicates | Adds Bash/Python/YAML/config/primitive surfaces. |
| `scripts/component-lint.sh` | selected catalog description duplicates | Adds cross-file behavior/config repetition. |
| `scripts/primitive_lifecycle.py` | duplicate primitive IDs | Adds repeated primitive behavior/procedure detection. |
| `scripts/precommit_content_hash.py` | duplicate commits/content | Adds source-level refactor candidates. |
| `scripts/cos_primitive_harvester.py` | existing primitive reuse suggestions | Adds repository-wide duplicate scan reports. |
| `scripts/lint-shell.sh` | Bash correctness | Provides normalized shell quality before extracting helpers. |

## Finding kinds

| Kind | Meaning | Suggested destination |
|---|---|---|
| `exact-copy` | normalized files match exactly | `templates/ or lib/` |
| `near-copy` | token shingles are highly similar | `templates/ or lib/` |
| `yaml-structural-repeat` | YAML/config has repeated schema shape | `manifests/` |
| `bash-function-repeat` | repeated shell functions | `hooks/_lib/` or `scripts/_lib/` |
| `python-function-repeat` | repeated Python AST bodies | `lib/` |
| `primitive-overlap` | similar rule/skill text | `skills/ or rules/` |

## Output contract

The script writes:

- `docs/06-Daily/reports/primitive-duplication-latest.json`
- `docs/06-Daily/reports/primitive-duplication-latest.md`

Each JSON finding includes:

- `kind`
- `classification`
- `left` / `right`
- `similarity`
- `recommendation`
- `common_home`
- `consumer_relevance`
- `rationale`

## False-positive controls

The audit avoids known false positives before producing refactor candidates:

- file aliases are deduplicated by resolved path, so compatibility symlinks do not appear as `exact-copy` debt;
- shell function detection requires real shell function syntax (`name() {` or `function name {`) and does not treat embedded AWK blocks such as `found { ... }` as Bash helpers;
- trivial Python CLI dispatch wrappers named `main` are ignored when they only call `args.func(args)`;
- optional allowlist entries in `manifests/primitive-duplication-allowlist.yaml` can suppress or reclassify intentional findings with an explicit reason.

## Triage policy

1. Extract repeated Python behavior to `lib/` only when call sites share semantics, not just syntax.
2. Extract repeated shell helpers to `hooks/_lib/` when hook-specific, otherwise `scripts/_lib/`.
3. Extract repeated YAML shapes to `manifests/` when the shape represents policy, profile, lifecycle, or projection contract.
4. Merge overlapping skills/rules only when their triggers and operational boundaries match.
5. Keep duplication when isolation is intentional; document the reason in the relevant ADR, manifest, or source comment.

## ACC integration

`scripts/acc_pipeline.py --refresh` runs the audit as the `primitive_duplication` adapter. In reconstruction this is advisory. Later phases can compare against a baseline and block new high-confidence duplication.
