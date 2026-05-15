# Primitive Scope Random Audit

Deterministic manual-review sample generated from `scripts/primitive_scope_classifier.py`. This report is a review queue, not an automatic reclassification result.

## Run metadata

- Seed: `20260515`
- Sampled rows: `40`

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
    "medium": 40
  },
  "by_effective_scope": {
    "both": 11,
    "os-only": 27,
    "project": 2
  },
  "total": 40
}
```

## Manual review checklist

For each row, check: (1) real projection/runtime surface, (2) content semantics, (3) required metadata/proofs, (4) whether classifier rules should be strengthened before changing markers.

| Path | Declared | Effective | Confidence | Source | Paired proof | Evidence | Review prompt |
|---|---|---|---|---|---|---|---|
| `hooks/dependency-license-classifier.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/singularity-check.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/post-agent-snapshot-restore.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/global-verify.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/tool-discovery-trigger.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/pattern-check.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/session-changelog.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/install-garak.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/guardrails-validator.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/agent-stress-test/SKILL.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `tests/red_team/portability/test_skill_agent_stress_test.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/install-syft-grype.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/session-watchdog-launcher.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `rules/cross-harness-authoring.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `tests/red_team/portability/test_cross-harness-authoring.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `rules/capability-protection.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/background-agent-reminder.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `tests/red_team/portability/test_background-agent-reminder.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/idle-service-cleanup.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/install-aguara.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/ecosystem-check.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/hook-header-validator.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/semgrep-scan.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/python/cognitive-os.yaml.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/rule-template.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/ai-provider-identity-guard.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/external-pattern-cleanroom-gate.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/work-queue-sync.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/license-audit-syft-grype.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/mlflow-sync.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/license-audit-trivy.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/reaper-daemon-launcher.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/engram-auto-sync.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `packages/skill-governance/skills/self-improve/SKILL.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `tests/red_team/portability/test_package_skills.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/deps-update/SKILL.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/parry-scan.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/counsel-outreach/review-request.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/agent-preamble.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/git-commit-scope-guard.sh` | `both` | `both` | `medium` | `consumer-availability` | `tests/red_team/portability/test_low_confidence_scope_batch.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/memory-scan/SKILL.md` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/task-panel-sync.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `tests/red_team/portability/test_task-panel-sync.py` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/lib-symlink-divergence-detector.sh` | `os-only` | `os-only` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/CLAUDE.md.template` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
