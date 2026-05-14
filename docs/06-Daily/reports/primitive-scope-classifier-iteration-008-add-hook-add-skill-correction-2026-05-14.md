# Primitive Scope Classifier Iteration 8 — `add-hook` / `add-skill` Scope Correction

## Input

Iteration 7 categorized these rows as `split-or-os-only`:

- `skills/add-hook/SKILL.md`
- `skills/add-skill/SKILL.md`

## Manual finding

Both primitives currently teach how to modify Cognitive OS itself:

- Cognitive OS hook and skill source paths;
- Cognitive OS catalogs/registry/routing metadata;
- harness projection files;
- COS-specific portability and projection gates.

The generic concepts are portable, but the current artifacts are not generic. A repository-agnostic hook-authoring or SKILL.md-authoring primitive would need to be split into a separate `both` primitive with its own proof.

## Changes made

- Changed both `SCOPE` markers from `both` to `os-only`.
- Added explicit scope notes to both skill bodies explaining why the current artifact is OS-specific and when a separate portable primitive would be appropriate.
- Added `maintainer-only` consumer-availability metadata.
- Added lifecycle metadata with `distribution: maintainer` and `owner_adr: ADR-314`.
- Updated the skill registry lock hashes for the changed skill files.
- Reworded the old red-team load checks so they no longer claim to be `both` portability proofs.
- Added lifecycle/consumer metadata for the new unknown-triage script so this iteration does not introduce a fresh unclassified primitive.

## Scoped classifier result

```bash
.venv/bin/python scripts/primitive_scope_classifier.py \
  --project-dir . \
  --paths skills/add-hook/SKILL.md skills/add-skill/SKILL.md \
  --fail-contradictions
```

Observed:

```json
{
  "total": 2,
  "by_suggested_scope": {"os-only": 2},
  "by_effective_scope": {"os-only": 2},
  "by_confidence": {"high": 2},
  "contradictions": 0
}
```

Row evidence:

| Path | Declared | Suggested | Evidence |
|---|---|---|---|
| `skills/add-hook/SKILL.md` | os-only | os-only | consumer-availability `maintainer-only`; lifecycle `distribution=maintainer; state=advisory` |
| `skills/add-skill/SKILL.md` | os-only | os-only | consumer-availability `maintainer-only`; lifecycle `distribution=maintainer; state=advisory` |

## Full classifier delta

After adding metadata for the new triage script too:

```json
{
  "total": 1199,
  "by_suggested_scope": {
    "both": 50,
    "os-only": 417,
    "project": 50,
    "unknown": 682
  },
  "by_effective_scope": {
    "both": 50,
    "os-only": 1099,
    "project": 50
  },
  "contradictions": 238
}
```

Unknown triage now reports `declared-both-os-internal-heavy: 90` instead of 92.

## Decision

The current `add-hook` and `add-skill` artifacts are confirmed `os-only`. Do not treat the old structural load checks as evidence that the procedures are portable. If we want reusable authoring guidance for any repository, create separate `both` primitives rather than overloading these COS maintainer skills.
