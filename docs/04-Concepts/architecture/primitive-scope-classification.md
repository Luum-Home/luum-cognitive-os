# Primitive Scope Classification

`SCOPE` is an audience/applicability claim, not a source-location, grep, or
distribution-tier claim. It answers where an agentic primitive is semantically
needed:

- `os-only` — primitive whose principle, procedure, or implementation is only required to construct, validate, explain, or operate Cognitive OS itself.
- `project` — primitive that affects downstream projects only, and that Cognitive OS does not need to contemplate as part of constructing or validating itself.
- `both` — repository-construction guidance that is agnostic enough to apply to Cognitive OS and to any downstream repository.

## Semantic rubric

Use this rubric before trusting metadata:

| Scope | Positive semantic evidence | Negative semantic evidence |
|---|---|---|
| `os-only` | Explains Cognitive OS internals, maintainer-only construction, governance of the OS itself, or repo-specific machinery that downstream projects will not contain. | Generic engineering advice, repo-agnostic build/test/review rules, or consumer-project projection. |
| `both` | Describes agnostic repository construction practices: code review, testing discipline, documentation quality, safety patterns, scaffolding patterns, or governance rules usable in any repo including this one. | Depends on paths, manifests, docs, scripts, lifecycle states, or architecture that exist only in the Cognitive OS repo. |
| `project` | Only modifies, scaffolds, validates, or constrains downstream projects, and is not required for Cognitive OS self-construction. | Needed to build, release, validate, repair, or explain Cognitive OS itself. |

## Root rule

Never classify by path mentions alone. References to `.cognitive-os/`, `manifests/`, `docs/02-Decisions/`, `scripts/cos-*`, or ADRs can be legitimate implementation or validation details for a portable primitive. Those references are signals to inspect against the rubric, not proof by themselves. They become strong `os-only` evidence when the primitive's core value proposition depends on those Cognitive OS-specific paths or internals.

## Automatic classifier

Use `scripts/primitive_scope_classifier.py` when creating or changing primitives. Pre-commit/PR lanes should pass explicit staged primitive paths with `--paths` so unrelated dirty worktree rows do not hide or block the change under review. The classifier computes an evidence-weighted suggested scope from durable distribution metadata:

1. `manifests/primitive-scope-overrides.yaml`
2. `manifests/primitive-readiness-protected-install-surfaces.yaml`
3. `manifests/primitive-consumer-availability.yaml`
4. `manifests/primitive-lifecycle.yaml`
5. paired portability/falsification tests from `lib.portability_proof_paths`

The classifier is intentionally conservative. A new primitive with no export/projection evidence is reported as `unknown` with safe `effective_scope=os-only` and low confidence and a next action to add lifecycle/projection/consumer-availability metadata before relying on the classification.

Manual review findings must feed back into the classifier as explainable semantic patterns when the same pattern can recur. These patterns are lower-priority evidence than manifests and do not replace portability proof. Current learned hook patterns cover:

- shared-surface hooks: generic repository safety, git/secret safety, prompt/task quality gates, Trust Report validation, context/resource hygiene, scope/claim governance, ADR relevance, memory lifecycle, rule/skill routing, and tool-loop detection;
- maintainer-only hooks: COS control-plane audits, profile auto-application, primitive governance, pending-truth ledgers, self-maintenance, and skill-evolution hooks when the body is bound to COS internals such as `.cognitive-os/`, `docs/02-Decisions/`, or `manifests/`.

This feedback loop prevents repeated manual rediscovery while preserving the root rule: semantic patterns are evidence, not distribution-tier shortcuts.

`distribution: core | team | maintainer | lab` is orthogonal metadata. It says
which adoption/profile tier should receive the primitive by default. It must not
be used as scope evidence by itself:

- `distribution: lab` does not mean `os-only`;
- `distribution: core` does not mean `both`;
- a reusable `both` primitive may still be `lab` if it is opt-in, experimental,
  or too heavy for default projection;
- an `os-only` primitive may still be important without being part of the
  default `core` surface.

Lifecycle scope evidence comes from explicit `consumer_accessibility` values
such as `lifecycle-declared-shared-surface`,
`lifecycle-declared-consumer-candidate`, or
`lifecycle-declared-maintainer`, not from distribution tier alone.

Project-facing candidate evidence is not the same as `both` evidence. `shell-ci-candidate`, `projectable-needs-driver`, `projected-consumer-surface`, and lifecycle `consumer_accessibility: lifecycle-declared-consumer-candidate` make a primitive visible as a `project` candidate. A `both` claim still needs evidence that the primitive is valid as a COS/core surface and as a downstream project surface.

## Unknown triage before AI/manual review

Use `scripts/primitive_scope_unknown_triage.py` after a full classifier run to turn the large `unknown` bucket into reviewable groups:

```bash
.venv/bin/python scripts/primitive_scope_unknown_triage.py --project-dir .
```

The triage report is deterministic. It groups missing evidence, metadata conflicts, likely OS-internal rows, likely agnostic `both` rows, and project-only candidates. It must not change markers by itself; it is the queue for manual or AI-assisted adjudication.

## Authoring workflow

When adding a primitive:

1. Start with the safest claim:
   - no consumer projection/export evidence yet → `unknown` / safe effective `os-only`
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
- scope/distribution evidence: lifecycle `consumer_accessibility`, consumer availability, install/profile surfaces, scope overrides, projection proof;
- proof evidence: paired portability tests.

Only the latter two can justify `project` or `both`. Source mentions alone cannot demote a portable primitive to `os-only`.

## Acceptance criteria

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_scope_classifier.py -q
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir . --paths <changed-primitive> --fail-contradictions
```
