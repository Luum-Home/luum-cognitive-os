# Medium Scope Debt Closure — 2026-05-15

## Scope

Follow-up pass for the remaining classification debt:

1. Review medium-confidence `install-*.sh` and `cos-*-local.sh` scripts.
2. Add hook/rule asymmetry detector.
3. Add secondary evidence for project-only templates.
4. Calibrate batch portability proof weight.

## Decisions

- Batch portability proof is accepted as a temporary proof gate, but it caps `SCOPE: both` classifier confidence at `medium` until there is a primitive-specific or family-specific portability proof.
- Optional security/eval installers are `both` only when backed by shared-surface metadata plus family-specific portability proof; they are not `both` merely because they are useful tools.
- `cos-postgres-local.sh` and `cos-valkey-local.sh` remain `both` because they operate on the active project runtime directory and are useful for COS self-development and consumer installs.
- Project templates are `project` when they are emitted/adapted into consumer repos and not required for COS self-construction; lifecycle rows now provide the second evidence source.

## Implemented

- Added `scripts/primitive_scope_dependency_audit.py` and wrapper `scripts/primitive-scope-dependency-audit`.
- Added family-specific portability tests:
  - `tests/red_team/portability/test_shared_tool_installers.py`
  - `tests/red_team/portability/test_shared_local_service_scripts.py`
- Replaced weak batch-only proof for reviewed installers/local-service scripts with the family-specific tests.
- Added lifecycle evidence for the 29 project templates.
- Added lifecycle evidence for reviewed shared installers/local-service scripts.
- Added CI/local-CI ratchet for hook/rule dependency asymmetry.

## Current results

Classifier summary:

```json
{
  "by_confidence": {
    "high": 1027,
    "medium": 184
  },
  "by_effective_scope": {
    "both": 531,
    "os-only": 625,
    "project": 55
  },
  "by_suggested_scope": {
    "both": 531,
    "os-only": 625,
    "project": 55
  },
  "contradictions": 0,
  "low_confidence": 0,
  "safe_fallback_os_only_from_unknown": 0,
  "total": 1211
}
```

Dependency audit summary:

```json
{
  "findings": 0
}
```

## Remaining review queue

- Continue reducing the remaining medium-confidence rows by adding a second independent evidence source or a primitive-specific portability proof.
- The batch proof policy is now encoded in the classifier, so high confidence requires stronger proof than `test_low_confidence_scope_batch.py`.
