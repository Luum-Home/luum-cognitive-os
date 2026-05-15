# Primitive Scope Random Audit

Deterministic manual-review sample generated from `scripts/primitive_scope_classifier.py`. This report is a review queue, not an automatic reclassification result.

## Run metadata

- Seed: `20260515`
- Sampled rows: `55`

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
    "high": 21,
    "medium": 34
  },
  "by_effective_scope": {
    "project": 55
  },
  "total": 55
}
```

## Manual review checklist

For each row, check: (1) real projection/runtime surface, (2) content semantics, (3) required metadata/proofs, (4) whether classifier rules should be strengthened before changing markers.

| Path | Declared | Effective | Confidence | Source | Paired proof | Evidence | Review prompt |
|---|---|---|---|---|---|---|---|
| `scripts/check_mcp_servers.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/domain_model.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/minimal/cognitive-os.yaml.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/rules_export.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_rules_export.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/typescript/cognitive-os.yaml.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/docs_execution_audit.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/external-tools-overlay.yaml` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/settings.json.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/python/cognitive-os.yaml.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/domain-model/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_domain_model.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/detect-stack/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_detect_stack.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/verification-commands.example.yaml` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/go-service-context.md` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/security-profiles/paranoid.json` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/ops_runbook.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/python/README.md.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/blocked-strings.example.txt` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/go/main.go.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/go/gitignore.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/typescript/README.md.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/jupyter-sandbox.sh` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/risk_register.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_risk_register.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/CLAUDE.md.template` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/python/pyproject.toml.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/llm_status.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/security_audit_writer.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_security_audit_writer.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/install-recommended/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_install_recommended.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/adoption-tiers.md.j2` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/security-profiles/minimal.json` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/python/gitignore.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/architecture-compliance.sh` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/go/cognitive-os.yaml.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/cos` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/typescript/gitignore.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/minimal/README.md.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/go/go.mod.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/project_scaffold.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/ops-runbook/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_ops_runbook.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/minimal/gitignore.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/generate-config/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_generate_config.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/sprint-test-summary.sh` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/dry-run-preview.sh` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/document_feature_append.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/rules-export/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_rules_export.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/scaffold-project/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_scaffold_project.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/project-scaffold/SKILL.md` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `hooks/infra-intent-detector.sh` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/service-map.example.yaml` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/typescript/package.json.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `skills/risk-register/SKILL.md` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `tests/red_team/portability/test_skill_risk_register.py` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/security-profiles/standard.json` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/typescript/tsconfig.json.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/fintech-gates.md` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `scripts/radar_merge.py` | `project` | `project` | `high` | `consumer-availability+lifecycle` | `` | consumer-availability, lifecycle | Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
| `templates/project-templates/go/README.md.tmpl` | `project` | `project` | `medium` | `consumer-availability` | `` | consumer-availability | MEDIUM/LOW confidence: Verify that the declared/effective scope matches real runtime surface, consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes. |
