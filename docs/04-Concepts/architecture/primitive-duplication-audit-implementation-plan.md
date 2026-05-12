# Primitive Duplication Audit Implementation Plan

## Goal

Create a unified duplication audit that finds repeated Bash, Python, YAML/config, and agentic primitive behavior and recommends where to extract common behavior.

## Phase 1 — Advisory audit

- Implement `scripts/primitive_duplication_audit.py`.
- Emit JSON and Markdown reports under `docs/06-Daily/reports/`.
- Cover Python function repeats, Bash function repeats, YAML structural repeats, exact/near file copies, and primitive overlap.
- Add unit tests with small fixtures.
- Add ACC refresh adapter.

## Phase 2 — Baseline and triage

- Run the audit on the full repo.
- Review top findings by `common_home`.
- Create a baseline once intentional duplication is marked.
- Convert highest-confidence candidates into refactor tasks.

## Phase 3 — Extraction

- Move Python common logic to `lib/`.
- Move shell common logic to `hooks/_lib/` or `scripts/_lib/`.
- Move repeated YAML/config schema to `manifests/` or profile manifests.
- Merge or separate overlapping rules/skills with explicit boundaries.

## Phase 4 — Gate

- Add `--baseline` / `--fail-new` semantics if needed.
- In stabilization, warn on new high-confidence duplicates.
- In production, block only new exact-copy or repeated helper findings unless explicitly allowlisted.

## Acceptance criteria

1. `python3 -m pytest tests/unit/test_primitive_duplication_audit.py -q` passes.
2. `python3 scripts/primitive_duplication_audit.py --project-root . --json` writes JSON/Markdown reports.
3. `python3 -m py_compile scripts/primitive_duplication_audit.py scripts/acc_pipeline.py` passes.
4. `scripts/acc_pipeline.py --refresh` reports a `primitive_duplication` adapter status.
