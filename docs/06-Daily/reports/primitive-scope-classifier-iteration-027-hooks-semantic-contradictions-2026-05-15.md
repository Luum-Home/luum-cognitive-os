# Primitive SCOPE classifier — Iteration 027 hooks semantic contradictions

Date: 2026-05-15

## Goal

Review hooks where the classifier's learned semantic pattern disagreed with a declared `SCOPE: both` marker, and feed false-positive discoveries back into the classifier before changing markers.

## Manual review result

The initial semantic-pattern contradiction list had 13 hooks. Manual review split them into two groups:

### Reclassified to `os-only`

These 4 hooks are COS-maintainer/control-plane surfaces, not repository-agnostic construction guidance:

- `hooks/control-plane-audit.sh`
- `hooks/control-plane-audit-hourly.sh`
- `hooks/profile-drift-autoapply.sh`
- `hooks/skill-post-execution-analysis.sh`

Evidence:

- control-plane audit hooks execute `scripts/cos-control-plane-audit` and enforce COS primitive/coherence findings;
- profile drift auto-apply re-applies the COS efficiency profile when COS hook projection scripts change and writes harness settings;
- skill post-execution analysis records COS SkillStore data and propose-only skill evolution artifacts under COS reports.

For these 4 paths, this iteration changed `SCOPE: both` to `SCOPE: os-only`, added `maintainer-only` consumer availability, and added lifecycle `consumer_accessibility: lifecycle-declared-maintainer`.

### Kept as potential `both`; classifier refined

The broad `adr-*`, `rule-*`, `skill-*`, and `engram-*` semantic prefixes were too aggressive. Manual review found several are shared runtime/governance surfaces when installed in COS and adopter repos:

- ADR relevance/detection can be repository architecture governance;
- Engram lifecycle hooks support persistent agent memory for COS and adopter project sessions;
- rule/skill routers and skill frontmatter validation can operate on projected/shared agent primitives.

The classifier was refined to stop demoting these by broad prefix alone. It now uses exact shared patterns for these reviewed hooks and keeps narrow COS-only patterns for control-plane/profile/skill-evolution cases.

## Before / after

Before this iteration:

```json
{
  "semantic_hook_contradictions": 13,
  "classifier_contradictions": 40,
  "total_unknown": 320,
  "hooks_unknown": 79
}
```

After this iteration:

```json
{
  "semantic_hook_contradictions": 0,
  "classifier_contradictions": 36,
  "total_unknown": 320,
  "hooks_unknown": 79
}
```

Unknown count does not change because these rows were already classifier-visible through semantic evidence; this iteration resolves contradictory markers and classifier false positives.

## Guardrails preserved

- No `distribution` tier was used as SCOPE evidence.
- Shared semantic patterns require declared `SCOPE: both`.
- COS-only semantic patterns require COS internal tokens in the hook body.
- New exact matching avoids substring false positives.

## Validation

Run targeted parser/classifier/triage/portability tests, py_compile, registry lock audit, and primitive inventory before commit.
