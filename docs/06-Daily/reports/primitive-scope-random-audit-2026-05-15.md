# Primitive Scope Random Audit

Deterministic manual-review sample generated from `scripts/primitive_scope_classifier.py`. This report is a review queue, not an automatic reclassification result.

## Run metadata

- Seed: `20260515`
- Sampled rows: `12`

## Classifier summary

```json
{
  "by_confidence": {
    "high": 986,
    "medium": 223
  },
  "by_effective_scope": {
    "both": 531,
    "os-only": 623,
    "project": 55
  },
  "by_suggested_scope": {
    "both": 531,
    "os-only": 623,
    "project": 55
  },
  "contradictions": 0,
  "low_confidence": 0,
  "safe_fallback_os_only_from_unknown": 0,
  "total": 1209
}
```

## Sample summary

```json
{
  "by_confidence": {
    "high": 10,
    "medium": 2
  },
  "by_effective_scope": {
    "both": 4,
    "os-only": 4,
    "project": 4
  },
  "total": 12
}
```

## Manual review checklist

For each row, check: (1) real projection/runtime surface, (2) content semantics, (3) required metadata/proofs, (4) whether classifier rules should be strengthened before changing markers.

| Path | Declared | Effective | Confidence | Source | Paired proof | Evidence | Review prompt |
|---|---|---|---|---|---|---|---|
| `hooks/protected-config-write-guard.sh` | `both` | `both` | `high` | `consumer-availability+lifecycle+semantic-pattern` | `tests/red_team/portability/test_protected-config-write-guard.py` | consumer-availability, lifecycle, semantic-pattern | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/topology-discover.sh` | `both` | `both` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_topology-discover.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/host-tool-doctor.sh` | `both` | `both` | `high` | `consumer-availability+lifecycle+semantic-pattern` | `tests/red_team/portability/test_host-tool-doctor.py` | consumer-availability, lifecycle, semantic-pattern | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `packages/verification-audit/skills/verification-before-completion/SKILL.md` | `both` | `both` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_package_skills.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/cos-record-onboarding.sh` | `os-only` | `os-only` | `high` | `scope-override+consumer-availability+lifecycle` | `tests/red_team/portability/test_cos-record-onboarding.py` | scope-override, consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/install-goreleaser.sh` | `os-only` | `os-only` | `high` | `scope-override` | `` | scope-override | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/cos-tool-inventory` | `os-only` | `os-only` | `high` | `scope-override` | `` | scope-override | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/cos-portable-ai-real-consumer-smoke` | `os-only` | `os-only` | `high` | `scope-override` | `tests/red_team/portability/test_cos-portable-ai-real-consumer-smoke.py` | scope-override | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/cos` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/jupyter-sandbox.sh` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/sprint-test-summary.sh` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/security-profiles/paranoid.json` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
