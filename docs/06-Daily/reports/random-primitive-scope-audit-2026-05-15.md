# Random primitive scope audit — 2026-05-15

## Method

Random but reproducible sample with seed `20260515`, stratified across `os-only`, `both`, and `project`, then manually reviewed against the session taxonomy.

## Result

- 11/12 sampled primitives were correctly classified.
- 1/12 was misclassified: `templates/project-gotchas.md` was `project` but its content is COS-maintainer trap context for symlinks, generated settings, hooks/packages, and `.cognitive-os` internals. It is now `os-only`.
- The classifier now has semantic-pattern evidence for COS-internal templates, so similar future templates are flagged without relying only on exact manifest rows.
- Primitive authoring skills now require running `primitive_scope_classifier.py --paths ... --fail-contradictions --fail-low-confidence` and adding consumer/behavior evidence instead of guessing SCOPE.

## Sample

| Primitive | Reviewed classification | Manual finding | Action |
|---|---:|---|---|
| `hooks/completeness-check.sh` | `os-only` | Compatibility entrypoint for COS capability-level completeness gating; delegates to canonical hook but is an OS-maintainer alias. | No change. |
| `rules/research-first-protocol.md` | `os-only` | Explicit os-dev rule for high-risk SO implementation flow. | No change. |
| `templates/agent-mandatory-rules.md` | `os-only` | Mandatory subagent rules for this SO, with COS-specific symlink/hook/settings guidance. | No change. |
| `scripts/upgrade.sh` | `os-only` | Upgrades installed Cognitive OS from source metadata. | No change. |
| `packages/quality-gates/skills/nemo-guardrails/SKILL.md` | `both` | Package quality-gate skill maps portable safety policies to NeMo; shared-surface/lifecycle evidence exists. | No change. |
| `templates/eas.md` | `both` | Evidence/acceptance spec template is repo-agnostic and useful in COS and adopters. | No change. |
| `hooks/orchestrator-decision-trace.sh` | `both` | Generic orchestrator observability for agent decisions; paired proof exists. | No change. |
| `skills/wiki-ingest/SKILL.md` | `both` | Generic raw-source ingestion workflow with shared evidence and proof. | No change. |
| `scripts/radar_merge.py` | `project` | Consumer radar merge writer/scaffolder; project-only evidence exists. | No change. |
| `hooks/infra-intent-detector.sh` | `project` | Reads adopter project infrastructure intent from cognitive-os.yaml; not needed for COS construction. | No change. |
| `templates/project-gotchas.md` | `os-only` | Was project; content is COS-internal maintainer trap context. | Reclassified to os-only; added maintainer evidence and classifier semantic-pattern for COS-internal templates. |
| `skills/domain-model/SKILL.md` | `project` | Scaffolds adopter project DDD doc under project docs. | No change. |

## Tooling changes

- `scripts/primitive_scope_classifier.py` now emits `os-only` semantic-pattern evidence for templates that carry COS-internal maintainer context.
- `skills/add-hook/SKILL.md` and `skills/add-skill/SKILL.md` now require explicit SCOPE taxonomy checks, evidence manifests, paired portability proof for `both`, and classifier validation for the created primitive.

## Validation

```bash
python3 scripts/primitive_scope_classifier.py --project-dir . --fail-contradictions --fail-low-confidence
```

Result after this iteration: `low_confidence=0`, `contradictions=0`.
