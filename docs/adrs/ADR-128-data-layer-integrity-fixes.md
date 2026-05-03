# ADR-128 — Data Layer Integrity Fixes

## Status

Proposed — 2026-05-03

## Context

The latest DX assessment found a more serious problem than "theater" in the
Cognitive OS governance layer: several data-layer claims could not be trusted as
stores or gates.

The P0 failures are:

1. Engram topic-key persistence is not proven as a reliable upsert store.
2. Engram ranking can collapse when search results omit native scores.
3. Engram reinforcement can fail silently when the daemon is down.
4. Active primitive readiness can undercount runtime reality by reading only the
   lifecycle manifest while the generated runtime projection registers many more
   hooks.
5. Package version claims can drift between `pyproject.toml` and `CHANGELOG.md`.
6. SDD state/artifact topic keys use multiple namespaces.

A readiness report must not look green if it only validates a small curated
manifest while runtime settings execute a much larger hook surface.

## Decision

Implement an **Integrity and De-Theater Sprint** before adding more governance
surface.

### 1. Engram topic-key writes are wrapper-level upserts

Internal `lib.engram_client.save_observation()` treats a supplied `topic_key` as
an upsert key. Before appending, it searches for an exact topic-key/project match
and updates that observation through the HTTP client. If the update path fails,
the wrapper returns `None` instead of appending a duplicate.

### 2. Engram score fallback preserves rank without dominating lifecycle

`lib.engram_lifecycle` uses a deterministic rank-derived fallback when Engram
results do not include a numeric `score`. The fallback range is intentionally
narrow (`1.0` for the first result down to `0.9` for the last result) so provider
rank remains visible but confidence/retention can still reorder stale matches.

### 3. Engram daemon-down reinforcement is visible

When reinforcement cannot run because the Engram daemon is unavailable,
`lib.engram_lifecycle` writes a best-effort metric to
`.cognitive-os/metrics/engram-daemon-down.jsonl`. The method still returns
`False`, but failure is no longer invisible.

### 4. Active primitive index includes runtime coverage

`scripts/active_primitive_index.py` compares hooks registered in
`.claude/settings.json` with hooks represented in
`manifests/primitive-lifecycle.yaml`. Architecture readiness fails when runtime
hooks are not covered by lifecycle metadata.

This makes the current gap explicit: a seed lifecycle manifest cannot represent a
large runtime hook projection and still pass readiness.

### 5. Product-facing claims are audited

`scripts/cos_architecture_readiness.py` fails if product-facing docs contain
missing README hook/script claims, legacy model-branded readiness names, or direct
model IDs in product claims.

### 6. SDD topic keys canonicalize to `planning/*`

Canonical SDD Engram topic keys are:

```text
planning/{change-name}/explore
planning/{change-name}/proposal
planning/{change-name}/spec
planning/{change-name}/design
planning/{change-name}/tasks
planning/{change-name}/apply-progress
planning/{change-name}/verify-report
planning/{change-name}/archive-report
planning/{change-name}/state
```

Legacy `sdd/{change}/...` keys remain read fallbacks only, as documented in
`rules/engram-organization.md`. We explicitly reject switching the canonical
namespace back to `sdd/*` because the current memory organization rule already
uses `planning/*` for proposals/specs/designs and documents legacy migration.

### 7. Version consistency is an audit contract

`tests/audit/test_version_consistency.py` requires the package version in
`pyproject.toml` to match the latest released heading in `CHANGELOG.md`, ignoring
`[Unreleased]`.

## Consequences

Positive:

- Engram duplicate writes become test-covered at the wrapper boundary.
- Score-less search results retain useful order without erasing lifecycle state.
- Daemon outages leave an operator-visible trail.
- Readiness cannot pass while undercounting projected hooks.
- SDD state recovery uses one canonical topic-key namespace.
- Version drift becomes an early audit failure.

Negative / trade-offs:

- `cos architecture readiness` may fail more often until the lifecycle manifest
  covers the actual runtime surface.
- Wrapper-level upsert depends on search finding exact topic-key matches before
  update.
- Legacy SDD keys need fallback support during migration.

## Alternatives rejected

- **Accept ADR-128 with `sdd/*` as canonical**: rejected because it contradicts
  the existing Engram organization rule and would add a fourth round of namespace
  churn.
- **Keep readiness manifest-only**: rejected because it can hide a large runtime
  hook surface behind a small curated manifest.
- **Append when Engram update fails**: rejected because it preserves the duplicate
  topic-key bug and makes memory harder to reason about.
- **Treat trust/blast advisory labels as blocking claims**: rejected until there
  is executable evidence that those primitives block.

## Verification

```bash
python3 -m pytest \
  tests/unit/test_engram_client.py \
  tests/unit/test_engram_lifecycle.py \
  tests/unit/test_active_primitive_index.py \
  tests/unit/test_cos_architecture_readiness.py \
  tests/audit/test_version_consistency.py \
  tests/audit/test_sdd_topic_keys.py -q

python3 -m py_compile \
  lib/engram_client.py \
  lib/engram_lifecycle.py \
  scripts/active_primitive_index.py \
  scripts/cos_architecture_readiness.py
```

## Implementation files

- `lib/engram_client.py`
- `lib/engram_lifecycle.py`
- `scripts/active_primitive_index.py`
- `scripts/cos_architecture_readiness.py`
- `manifests/governance-maturity.yaml`
- `.cognitive-os/plans/architecture/integrity-and-de-theater-sprint.md`
- `tests/unit/test_engram_client.py`
- `tests/unit/test_engram_lifecycle.py`
- `tests/unit/test_active_primitive_index.py`
- `tests/unit/test_cos_architecture_readiness.py`
- `tests/audit/test_version_consistency.py`
- `tests/audit/test_sdd_topic_keys.py`
- `skills/sdd-continue/SKILL.md`
- `docs/engram-namespaces.md`
- `docs/automation.md`
