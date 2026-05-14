# Primitive Scope Classifier Manual Review — 2026-05-14

## Context

A full repository run of `scripts/primitive_scope_classifier.py` was reviewed manually after the earlier broad `SCOPE: both` → `os-only` commits were reverted. The goal was to determine whether the classifier reveals real taxonomy debt or repeats the same grep-based mistake.

## Classifier correction made during review

The first full run reported 347 contradictions. Manual inspection found a classifier bug: it treated `manifests/primitive-scope-overrides.yaml` as an absolute override even though that manifest says the rules are fallback classifications and header markers remain preferred. It also treated paired portability proof as positive distribution evidence, when proof is necessary for `both` but not sufficient to infer distribution.

The classifier was corrected so that:

- scope override rules only provide evidence when the primitive has no explicit header marker;
- paired portability proof remains a proof gate, not weighted distribution evidence.

After correction, the full run reports:

```json
{
  "total": 1123,
  "by_suggested_scope": {
    "both": 77,
    "os-only": 1046
  },
  "contradictions": 195,
  "low_confidence": 605
}
```

## Manual triage buckets

| Bucket | Count | Manual reading | Recommended action |
|---|---:|---|---|
| lifecycle says `lab` | 68 | Mostly hooks declared `both`/`project` while lifecycle declares sandbox/lab. These are likely real contradictions unless lifecycle is stale. | Do not mass flip. For each row, either promote lifecycle distribution with projection proof or mark header `os-only`. |
| lifecycle says `maintainer` | 55 | Maintainer-only lifecycle rows declared as `both`. Many look like real SO-maintainer primitives. | Batch review by family. Header should usually become `os-only`, but first check whether consumer projection was intended and lifecycle is stale. |
| consumer availability says `os-only` | 48 | Strongest evidence bucket. `primitive-consumer-availability.yaml` explicitly says maintainer/local-only. | Treat as high-priority real debt. Align headers or update consumer availability if it is wrong. |
| protected install surface says `both` | 15 | Install/profile scripts declared `os-only`/`project` but protected install metadata says they are profile/bootstrap surfaces. | Review as likely `both` or split into wrapper `both` + implementation `os-only`. |
| lifecycle consumer distribution says `both` | 9 | Lifecycle says `core`/`team` but marker says `project`/`os-only`. | Likely marker stale; verify projection proof before changing to `both`. |

## Examples

### Strong `os-only` evidence

- `hooks/_lib/agent-context.sh`: declared `both`; evidence says consumer availability `so-local-only` and lifecycle `distribution=maintainer`.
- `hooks/network-egress-guard.sh`: declared `both`; evidence says consumer availability `so-local-only` and lifecycle `distribution=maintainer`.
- `skills/proof-drill/SKILL.md`: declared `both`; consumer availability says `maintainer-only`.

### Likely `both` / split-surface evidence

- `scripts/cos-bootstrap.sh`: declared `os-only`; protected install surface and lifecycle say bootstrap/core.
- `scripts/setup.sh`: declared `project`; protected install surface and lifecycle say bootstrap/core.
- `scripts/generate-project-settings.sh`: declared `os-only`; protected install surface says settings/profile projection.

## Conclusion

The taxonomy still has real debt, but the right response is not a repo-wide sed rewrite. The corrected classifier provides a review queue. The next safe migration should happen in small batches with explicit acceptance criteria:

1. Start with `consumer_availability_says_os_only` because it has the strongest explicit metadata.
2. Then review `protected_install_says_both` and decide wrapper-vs-implementation splits.
3. Then review lifecycle `lab`/`maintainer` contradictions.
4. Leave low-confidence rows as metadata debt, not automatic scope changes.

## Validation commands

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_scope_classifier.py tests/red_team/portability/test_cos_init.py -q
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir .
```


## Positive `both` review pass

A follow-up review tested whether the 77 rows suggested as `both` were false positives.

Additional classifier hardening found likely false positives:

- exact fallback overrides must beat broad `scripts/*` fallback rules;
- lifecycle states `demoted`, `archived`, and `deleted` must not infer `both` even when distribution is `team`;
- protected install surface membership means “review before demotion”, not automatically `both`; only direct projection/application surfaces (`bootstrap`, `settings-projection`, `profile-application`) count as positive `both` evidence.

After this hardening, suggested `both` rows dropped from 77 to 65.

Manual split of the 65:

| Category | Count | Reading |
|---|---:|---|
| Confirmed `both` marker + paired portability proof | 48 | Strong positive set. Marker, lifecycle/consumer evidence, and proof align. |
| Metadata says `both`, but marker/proof gap remains | 14 | Not safe to auto-change. These are candidates for paired proof + marker alignment, or metadata correction if lifecycle is stale. |
| Missing header but exact `both` override exists | 3 | Likely `both`, but should receive explicit header markers and proof where applicable. |

This means the classifier should not claim “77 are definitely both”. The defensible statement is: 48 are confirmed by current evidence, and 17 are review candidates with positive distribution metadata but incomplete marker/proof hygiene.

## Iteration doctrine update

The classifier now separates `suggested_scope` from `effective_scope`:

- `suggested_scope=unknown` means evidence is insufficient; it is not a final `os-only` claim.
- `effective_scope=os-only` is the safe enforcement fallback for unknown rows until metadata/projection proof exists.

Latest full run after this change:

```json
{
  "total": 1123,
  "by_suggested_scope": {
    "both": 65,
    "os-only": 453,
    "unknown": 605
  },
  "by_effective_scope": {
    "both": 65,
    "os-only": 1058
  },
  "contradictions": 191,
  "low_confidence": 605
}
```

This is the desired calibration behavior: the tool no longer pretends that insufficient evidence proves `os-only`; it reports pending taxonomy work separately while still keeping projection/install behavior safe.


## Package-skill inventory coverage

Re-reviewing `33682e2e` exposed a classifier coverage gap: package skills under `packages/*/skills/*/SKILL.md` were part of the bad commit but were not in the initial classifier inventory. The classifier now scans those package skills. Latest full-run summary after this coverage update:

```json
{
  "total": 1198,
  "by_suggested_scope": {
    "both": 65,
    "os-only": 453,
    "unknown": 680
  },
  "by_effective_scope": {
    "both": 65,
    "os-only": 1133
  },
  "contradictions": 262,
  "low_confidence": 680
}
```

The package-skill rows from `33682e2e` mostly classify as `unknown`, not proven `os-only`; they should become metadata/proof tasks rather than automatic demotions.

## Iteration 2 — consumer-availability `os-only` correction

Reviewing the `consumer-availability → os-only` bucket found that consumer availability cannot automatically override contradictory lifecycle metadata. Rows with `consumer-availability=os-only` and `lifecycle=team/core` are now `suggested_scope=unknown` with `decision_source=conflicting-distribution-evidence`.

Latest full-run summary after this adjustment:

```json
{
  "total": 1198,
  "by_suggested_scope": {
    "both": 65,
    "os-only": 414,
    "unknown": 719
  },
  "by_effective_scope": {
    "both": 65,
    "os-only": 1133
  },
  "contradictions": 230,
  "low_confidence": 719
}
```

The remaining consumer-availability `os-only` bucket has 51 rows; 39 rows moved to `unknown` pending metadata reconciliation.

## Iteration 3 — lifecycle-only `os-only`

The lifecycle-only `os-only` bucket has 211 rows. Because lifecycle metadata can be stale, no marker changes were made. The rows split as:

```json
{
  "lifecycle_os_only_rows": 211,
  "contradictions": 129,
  "categories": {
    "candidate-inactive-marker-alignment": 1,
    "candidate-lab-marker-alignment": 68,
    "candidate-maintainer-marker-alignment": 60,
    "confirmed-marker-aligned-lifecycle-os-only": 71,
    "missing-header-lifecycle-os-only": 11
  }
}
```

Decision: lifecycle-only contradictions are review candidates, not automatic marker edits. Next iteration should review `unknown` rows with `decision_source=conflicting-distribution-evidence`.

## Iteration 4 — `project` scope model

The classifier previously had no positive `project` model: 64 rows declared `project`, but 0 were suggested as `project`. It now preserves explicit project markers as low-confidence `suggested_scope=project` when no stronger metadata exists.

Latest full-run summary after this adjustment:

```json
{
  "total": 1198,
  "by_suggested_scope": {
    "both": 65,
    "os-only": 414,
    "project": 35,
    "unknown": 684
  },
  "by_effective_scope": {
    "both": 65,
    "os-only": 1098,
    "project": 35
  },
  "contradictions": 230,
  "low_confidence": 719
}
```

Decision: `project` is first-class but under-proven. The 35 project suggestions are pending positive project-only proof, not confirmed project-only classifications.
