# Primitive Scope Classification

`SCOPE` is a distribution claim, not a source-location or grep claim. It answers where an agentic primitive is meant to be available:

- `os-only` — maintainer/self-construction surface for building, validating, or operating Cognitive OS itself.
- `project` — consumer-project-only surface.
- `both` — portable surface valid in this repository and in downstream projects.

## Root rule

Never classify by path mentions alone. References to `.cognitive-os/`, `manifests/`, `docs/02-Decisions/`, `scripts/cos-*`, or ADRs can be legitimate implementation or validation details for a portable primitive. Those references are signals to inspect, not proof of `os-only`.

## Automatic classifier

Use `scripts/primitive_scope_classifier.py` when creating or changing primitives. Pre-commit/PR lanes should pass explicit staged primitive paths with `--paths` so unrelated dirty worktree rows do not hide or block the change under review. The classifier computes an evidence-weighted suggested scope from durable distribution metadata:

1. `manifests/primitive-scope-overrides.yaml`
2. `manifests/primitive-readiness-protected-install-surfaces.yaml`
3. `manifests/primitive-consumer-availability.yaml`
4. `manifests/primitive-lifecycle.yaml`
5. paired portability/falsification tests from `lib.portability_proof_paths`

The classifier is intentionally conservative. A new primitive with no export/projection evidence is treated as `os-only` with low confidence and a next action to add lifecycle/projection/consumer-availability metadata before relying on the classification.

## Authoring workflow

When adding a primitive:

1. Start with the safest claim:
   - no consumer projection/export evidence yet → `os-only`
   - intended for consumer projects and this repo → add lifecycle/projection evidence, then `both`
   - intended only for generated consumer projects → add explicit projection/profile evidence, then `project`
2. Run:

   ```bash
   .venv/bin/python scripts/primitive_scope_classifier.py --project-dir . --paths <changed-primitive> --fail-contradictions
   ```

3. If the classifier disagrees with the marker, fix the evidence or the marker. Do not override the classifier with prose.
4. If declaring `both`, add or update the paired portability/falsification proof suggested by the report.

## Why this prevents the bad reclassification pattern

The failed reclassification pattern treated OS-internal strings as sufficient evidence. The classifier separates:

- implementation detail: source paths, docs references, COS commands;
- distribution evidence: lifecycle distribution, consumer availability, install/profile surfaces, scope overrides, projection proof;
- proof evidence: paired portability tests.

Only the latter two can justify `project` or `both`. Source mentions alone cannot demote a portable primitive to `os-only`.

## Acceptance criteria

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_scope_classifier.py -q
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir . --paths <changed-primitive> --fail-contradictions
```
