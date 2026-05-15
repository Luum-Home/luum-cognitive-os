# Manifest Tier Warning Backlog — 2026-05-15

## Purpose

Track the non-blocking but adoption-relevant warnings from `scripts/cos-manifest-tier-claim-audit --json` so manifest-driven governance is not marketed as universal primitive coverage before evidence catches up.

## Current Baseline

Command:

```bash
scripts/cos-manifest-tier-claim-audit --json
```

Baseline captured during the promise-compliance remediation pass:

| Metric | Count |
|---|---:|
| Primitive rows audited | 607 |
| Findings | 790 |
| Warnings | 474 |
| Info findings | 316 |
| `core_team_without_strong_evidence` | 237 |
| `candidate_to_lab_or_advisory` | 229 |
| `maintainer_knowledge_dependent` | 262 |
| `candidate_second_demote` | 62 |

## Interpretation

These findings do not mean the primitives are broken. They mean distribution and lifecycle claims are not yet evidence-complete enough for broad external adoption language.

The public/product wording must therefore say:

> Schema-versioned manifests and audits cover promoted governance surfaces; primitive-level coverage is ratcheted and not claimed universal until audits prove it.

## Remediation Policy

1. Treat `core_team_without_strong_evidence` as the first reduction target.
2. For each core/team primitive, either add durable `promotion_evidence` or demote the distribution to maintainer/lab/advisory.
3. Treat `candidate_to_lab_or_advisory` as profile-slimming input, not as a defect.
4. Treat `maintainer_knowledge_dependent` as documentation debt: the primitive may remain maintainer-only, but its rationale must be externalized before any promotion.
5. Treat `candidate_second_demote` as a follow-up review queue after sustained ROI is visible.

## Closure Targets

| Stage | Target |
|---|---|
| Stage 1 | `features.md` and public docs no longer claim “every primitive declares YAML.” |
| Stage 2 | `core_team_without_strong_evidence` reduced below 100 or each remaining row linked to explicit promotion rationale. |
| Stage 3 | Warning count reduced below 200 or split by accepted profile-specific backlog. |
| Stage 4 | Universal manifest-driven governance claims allowed only when strict audit exits clean or documented exceptions are machine-readable. |

## Validation

Use:

```bash
scripts/cos-manifest-tier-claim-audit --json > /tmp/manifest-tier.json || true
python3 - <<'PY'
import json
report = json.load(open('/tmp/manifest-tier.json'))
print(report['status'], report['finding_count'], report.get('counts_by_category'))
PY
```
