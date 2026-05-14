# Primitive Scope Classifier Iteration 5 — Project vs Both Evidence Review

## Input

```bash
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir .
```

Target bucket from Iteration 4: declared `SCOPE: project` rows that the classifier suggested as `both`.

## Hypothesis

The `project-marker-conflicts-with-both-evidence` bucket mixed two different cases:

1. real `both` candidates where the primitive is a COS/core runtime or install surface and is also projected/usable by consumers;
2. false-positive `both` suggestions where `shell-ci-candidate` or `lifecycle-declared-consumer-candidate` only proves project-facing availability, not shared OS+project use.

## Classifier adjustment in this iteration

- `primitive-consumer-availability.yaml` statuses such as `shell-ci-candidate`, `projectable-needs-driver`, and `projected-consumer-surface` now contribute `project` evidence, not `both` evidence.
- `primitive-lifecycle.yaml` rows with `consumer_accessibility: lifecycle-declared-consumer-candidate` now contribute `project` evidence, not `both` evidence.
- `both` remains reserved for direct bootstrap/profile surfaces, core/team lifecycle rows without consumer-candidate caveats, or other future paired OS+project evidence.

## Summary after adjustment

Full classifier summary:

```json
{
  "total": 1198,
  "by_suggested_scope": {
    "both": 50,
    "os-only": 414,
    "project": 50,
    "unknown": 684
  },
  "by_effective_scope": {
    "both": 50,
    "os-only": 1098,
    "project": 50
  },
  "contradictions": 238,
  "low_confidence": 719
}
```

Declared `project` rows now split as:

| Suggested | Confidence | Source | Rows |
|---|---|---|---:|
| project | high | consumer-availability+lifecycle | 3 |
| project | low | declared-project-pending-proof | 35 |
| both | high | protected-install-surface+lifecycle | 1 |
| both | medium | lifecycle | 2 |
| os-only | medium | lifecycle | 16 |
| unknown | low | conflicting-distribution-evidence | 7 |

## Row-level review of original project-vs-both bucket

| Path | Before | After | Manual finding | Action |
|---|---|---|---|---|
| `hooks/destructive-rm-blocker.sh` | both | both | This is an agent-context destructive-file-erasure safety hook with `distribution=core`, `runtime_projection: true`, projection into `.claude/settings.json`, and blocking lifecycle. The `project` marker is likely stale or too narrow. | Keep as unresolved marker-vs-lifecycle contradiction; do not auto-edit marker until portability/projection proof is checked. |
| `scripts/check_mcp_servers.py` | both | project | `shell-ci-candidate` plus `lifecycle-declared-consumer-candidate` means consumer-project doctor candidate, not shared OS+project proof. | Classifier false positive fixed. Add projection proof if this is meant to be confirmed project-only. |
| `scripts/dependency-lane.sh` | both | both | Lifecycle says `distribution=team` and `consumer_accessibility=lifecycle-declared-team`; body manages this repo's dependency lanes. The `project` marker may be stale, or lifecycle needs finer semantics. | Leave as contradiction; inspect ADR-145 before changing marker or lifecycle. |
| `scripts/docs_execution_audit.py` | both | project | Candidate consumer documentation audit; needs package/profile projection proof. Not `both` yet. | Classifier false positive fixed. |
| `scripts/project_scaffold.py` | both | project | Its CLI targets an external `--project-dir` and scaffolds a consumer project's docs tree. This is strong semantic support for `project`. | Classifier false positive fixed; add positive project-only proof. |
| `scripts/setup.sh` | both | both | Protected `bootstrap` install surface plus `distribution=core`. The `project` marker conflicts with bootstrap/profile evidence. | Leave as contradiction; inspect whether this is OS-dev setup, consumer bootstrap, or needs split wrappers. |

## Decision

The high number of apparent `both` conflicts was partly classifier debt, not necessarily bad original taxonomy. The main correction is semantic: project-facing evidence is not `both` evidence. After this adjustment, project-only is visible as a first-class outcome:

- confirmed/high project candidates: 3;
- low-confidence project pending proof: 35;
- unresolved project-marker contradictions: 19 total (`both`/`os-only`/`unknown`), to be handled in smaller evidence-family batches.

No `SCOPE` markers were changed in this iteration.

## Validation

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_scope_classifier.py -q
.venv/bin/python scripts/primitive_scope_classifier.py --project-dir .
.venv/bin/python -m pytest \
  tests/unit/test_primitive_scope_classifier.py \
  tests/red_team/portability/test_cos_init.py \
  tests/contracts/test_primitive_scope_classification.py \
  tests/unit/test_primitive_scope_governance.py \
  tests/unit/test_scope_both_portability_audit.py \
  tests/contracts/test_adr_numbering_integrity.py \
  tests/contracts/test_adr_status_taxonomy.py -q
```

Observed:

```text
11 passed
42 passed
```
