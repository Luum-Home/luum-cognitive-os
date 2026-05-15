# Primitive low-confidence surgical review — 2026-05-15

## Context

Classifier state before this review: 49 low-confidence primitives, all caused by `declared-project-pending-proof`. The problem is not missing SCOPE markers; it is missing evidence strong enough to trust the `project` declaration.

This review applies the taxonomy agreed in-session:

- `os-only`: construction/operation internals of Cognitive OS, or paths/config that should not exist in every consumer project.
- `both`: repo-agnostic agent/repository governance useful in COS itself and in adopter repositories.
- `project`: adopter-project-only surfaces that COS does not need to contemplate for its own construction.

## Summary recommendation

- `both`: 38
- `project`: 4
- `os-only`: 7

Important: `both` rows should not be flipped mechanically. The classifier currently requires paired portability proof for `both`; the safe next implementation batch is to add proof/evidence first, then change headers.

## Surgical table

| Primitive | Current | Recommended | Evidence observed | Reason |
|---|---:|---:|---|---|
| `hooks/aguara-scan.sh` | `project` | `both` | templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/ai-provider-identity-guard.sh` | `project` | `both` | templates/security-profiles/minimal.json, templates/security-profiles/standard.json, templates/security-profiles/paranoid.json, manifests/script-exposure-dispositions.yaml | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/architecture-compliance.sh` | `project` | `project` | templates/security-profiles/paranoid.json | Checks adopter application architecture patterns, Go files, framework choices and cognitive-os.yaml phase; not required to construct COS. |
| `hooks/code-review-on-commit.sh` | `project` | `both` | no projection reference found | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/confidentiality-enforcer.sh` | `project` | `both` | .claude/settings.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/content-policy.sh` | `project` | `both` | .claude/settings.json, templates/security-profiles/minimal.json, templates/security-profiles/standard.json, templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/destructive-rm-blocker.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/doc-sync-detector.sh` | `project` | `both` | .claude/settings.json, templates/security-profiles/standard.json, templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/dry-run-preview.sh` | `project` | `project` | no projection reference found | Project pipeline preview for DRY_RUN SDD flows; consumer workflow surface, not COS construction primitive. |
| `hooks/ecosystem-check.sh` | `project` | `os-only` | no projection reference found | COS ecosystem/plugin/tool-evaluation monitor; uses lib/ecosystem_evaluator.py which is os-only. |
| `hooks/git-commit-scope-guard.sh` | `project` | `both` | templates/security-profiles/minimal.json, templates/security-profiles/standard.json, templates/security-profiles/paranoid.json, manifests/script-exposure-dispositions.yaml | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/global-verify.sh` | `project` | `both` | no projection reference found | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/guardrails-validator.sh` | `project` | `both` | templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/infra-intent-detector.sh` | `project` | `project` | no projection reference found | Reads project infrastructure intent from cognitive-os.yaml and suggests project-local infra. |
| `hooks/jupyter-sandbox.sh` | `project` | `project` | no projection reference found | Opt-in project execution sandbox for Python/Jupyter workflows. |
| `hooks/mcp-scan.sh` | `project` | `both` | .claude/settings.json, .codex/hooks.json, templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/parry-scan.sh` | `project` | `both` | templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/pre-cleanup-snapshot.sh` | `project` | `os-only` | no projection reference found | Cleanup detector explicitly targets cognitive-os internals such as hooks/skills/rules/.cognitive-os. |
| `hooks/pre-commit-gate.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/predev-completeness-check.sh` | `project` | `both` | .claude/settings.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/private-mode-gate.sh` | `project` | `both` | .claude/settings.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/private-mode-metrics-gate.sh` | `project` | `both` | .claude/settings.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/rate-limit-drain.sh` | `project` | `both` | .claude/settings.json, .codex/hooks.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/rate-limit-precheck.sh` | `project` | `both` | no projection reference found | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/rate-limiter.sh` | `project` | `both` | templates/security-profiles/minimal.json, templates/security-profiles/standard.json, templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/reinvention-check.sh` | `project` | `both` | .claude/settings.json, templates/security-profiles/standard.json, templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/release-guard.sh` | `project` | `both` | templates/security-profiles/standard.json, templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/semgrep-scan.sh` | `project` | `both` | templates/security-profiles/paranoid.json | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/valkey-ensure.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `hooks/worktree-submodule-fix.sh` | `project` | `both` | no projection reference found | Generic repo/agent safety, quality, privacy, security, release, runtime, or git/worktree governance useful in COS and adopter repos when projected. |
| `scripts/cos-cloud-worker-bootstrap.sh` | `project` | `os-only` | tests/contracts/test_projectable_script_surface_evidence.py, manifests/script-exposure-dispositions.yaml; disposition=documented_maintainer_tool | ADR-140 COS worker Compose bootstrap; source-runtime operator surface, not a default consumer primitive. |
| `scripts/cos-postgres-local.sh` | `project` | `both` | tests/contracts/test_projectable_script_surface_evidence.py, manifests/script-exposure-dispositions.yaml; disposition=documented_maintainer_tool | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/cos-valkey-local.sh` | `project` | `both` | tests/contracts/test_projectable_script_surface_evidence.py, manifests/script-exposure-dispositions.yaml; disposition=documented_route | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/credibility-audit.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml; disposition=operator_workflow | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/dependency-lane.sh` | `project` | `os-only` | tests/contracts/test_projectable_script_surface_evidence.py | Manages COS requirements/dependency-lanes and invokes cos-deps coverage audit. |
| `scripts/deps-update.sh` | `project` | `os-only` | tests/contracts/test_projectable_script_surface_evidence.py | Maintainer dependency updater for this repository/toolchain, including Engram maintenance paths. |
| `scripts/doctor.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml; disposition=operator_workflow | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-aguara.sh` | `project` | `both` | tests/contracts/test_projectable_script_surface_evidence.py, manifests/script-exposure-dispositions.yaml; disposition=documented_maintainer_tool | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-credibility-tools.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml; disposition=operator_workflow | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-garak.sh` | `project` | `both` | tests/contracts/test_projectable_script_surface_evidence.py | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-git-filter-repo.sh` | `project` | `os-only` | manifests/script-exposure-dispositions.yaml; disposition=documented_maintainer_tool | ADR-218 COS history-sanitization dependency installer; destructive rewrite support for SO maintenance. |
| `scripts/install-mcp-scan.sh` | `project` | `both` | tests/contracts/test_projectable_script_surface_evidence.py, manifests/script-exposure-dispositions.yaml; disposition=documented_maintainer_tool | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-promptfoo.sh` | `project` | `both` | tests/contracts/test_projectable_script_surface_evidence.py | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-syft-grype.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml; disposition=operator_workflow | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-tob-skills.sh` | `project` | `both` | tests/contracts/test_projectable_script_surface_evidence.py | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/install-trivy.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml; disposition=operator_workflow | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/license-audit-syft-grype.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml; disposition=documented_maintainer_tool | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/license-audit-trivy.sh` | `project` | `both` | manifests/script-exposure-dispositions.yaml; disposition=operator_workflow | Portable operator/project quality or optional-tool surface useful for COS dogfooding and consumer repositories; needs explicit paired proof before header flip. |
| `scripts/setup-git-hooks.sh` | `project` | `os-only` | tests/contracts/test_projectable_script_surface_evidence.py, manifests/script-exposure-dispositions.yaml; disposition=documented_maintainer_tool | Installs COS source-repo post-merge auto-update hooks for registered COS installations. |

## Immediate implementation order

1. Flip the 7 clear `os-only` rows first: they have COS-internal evidence and should stop pretending to be consumer project primitives.
2. Add project evidence for the 4 true `project` hooks.
3. For the 38 recommended `both` rows, add paired portability proof and shared-surface metadata before changing headers. This prevents the exact failure mode that triggered this audit: taxonomy changes without proof.

## Guardrail

Do not use `script-exposure-dispositions.yaml` as automatic truth for SCOPE. It is useful evidence, but its `operator_workflow` and `documented_route` labels mix routing/exposure with semantic scope. The classifier should keep SCOPE, projection, distribution, and exposure as separate dimensions.

## Implementation — iteration 041

Implemented after this review:

- The 7 clear `os-only` primitives were reclassified with maintainer-only evidence.
- The 4 true `project` hooks kept `SCOPE: project` and gained `projected-consumer-surface` evidence.
- The 38 shared primitives were reclassified to `SCOPE: both` only after adding paired portability evidence through `tests/red_team/portability/test_low_confidence_scope_batch.py` and `manifests/primitive-behavior-evidence.yaml`.
- The classifier now accepts paired portability proof from explicit behavior-evidence rows when the referenced test lives under `tests/red_team/portability/`.
- The classifier and contract tests now reject exact behavior-evidence rows accidentally nested under `patterns:`, mirroring the earlier consumer-availability guardrail.

Validation after implementation:

```bash
python3 scripts/primitive_scope_classifier.py --project-dir . --fail-contradictions --fail-low-confidence
python3 scripts/primitive_parse_inventory.py --project-dir . --output /tmp/primitive-inventory-041.json
.venv/bin/python -m pytest tests/red_team/portability/test_low_confidence_scope_batch.py tests/contracts/test_primitive_scope_governance.py::test_consumer_availability_exact_paths_are_not_nested_under_patterns tests/contracts/test_primitive_scope_governance.py::test_behavior_evidence_exact_primitives_are_not_nested_under_patterns tests/contracts/test_projectable_script_surface_evidence.py tests/contracts/test_primitive_scope_classification.py tests/behavior/test_consumer_project_projection.py::test_codex_project_install_has_closed_hook_runtime_dependencies -q
```

Result:

- `low_confidence`: 0
- `contradictions`: 0
- `structural_findings`: `{}`
