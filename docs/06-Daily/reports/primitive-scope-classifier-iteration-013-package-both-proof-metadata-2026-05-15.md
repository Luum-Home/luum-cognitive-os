# Primitive Scope Classifier — Iteration 013: package `both` proof + metadata

Date: 2026-05-15

## Goal

Resolve the full `declared-both-needs-proof-and-metadata` bucket. The bucket had 70 rows.

## Finding

All 70 rows were package skills under:

```text
packages/<package>/skills/<skill>/SKILL.md
```

They were not necessarily semantically wrong. They were blocked by two missing pieces:

1. `lib/portability_proof_paths.py` treated package skills as plain `SKILL.md`, collapsing them to the unusable `test_SKILL.py` proof path.
2. They had no lifecycle / consumer-availability metadata, so the classifier had no durable distribution evidence.

## Fixes

### 1. Package skill proof paths

`lib/portability_proof_paths.py` now recognizes package skill paths and supports:

- specific proof: `tests/red_team/portability/test_package_skill_<package>_<skill>.py`
- aggregate proof: `tests/red_team/portability/test_package_skills.py`

The aggregate proof validates package skill structural portability without requiring 70 trivial one-file proofs.

### 2. Aggregate package skill portability proof

Added:

```text
tests/red_team/portability/test_package_skills.py
```

It verifies all `packages/*/skills/*/SKILL.md` files:

- are discovered as package skill surfaces;
- parse as primitives;
- have no parser structural findings;
- can be parsed without relying on current working directory.

### 3. Durable metadata

Added 70 `shared-surface` rows to:

```text
manifests/primitive-consumer-availability.yaml
```

Added 70 lifecycle rows to:

```text
manifests/primitive-lifecycle.yaml
```

## Decision

All 70 original rows remain `both` because package skills are modular portable surfaces intended for COS source use and adopter-project use. This iteration did not blanket-classify all package primitives: two `os-only` package skills remain unknown because they were not in the declared-`both` bucket:

- `packages/verification-audit/skills/cognitive-os-benchmark/SKILL.md`
- `packages/verification-audit/skills/harness-audit/SKILL.md`

## Result

The `declared-both-needs-proof-and-metadata` bucket is now empty.

```json
{
  "by_suggested_scope": {
    "both": 176,
    "os-only": 536,
    "project": 91,
    "unknown": 385
  },
  "unknown_delta": -70,
  "declared_both_needs_proof_and_metadata_bucket": 0,
  "package_unknown_remaining": 2
}
```

## Next iteration

Recommended next target: `os-only-semantic-candidate` (41 rows). Those are likely a mix of:

1. true COS-internal primitives that need metadata;
2. stale `both` markers that should demote;
3. generic primitives with misleading OS-internal references.
