---
name: rules-export
description: 'Use when you need this Cognitive OS skill: Export a snapshot of Cognitive
  OS rules/ (so-slo, definition-of-done, credential-management, etc.) into an adopting
  project''s docs/08-estandares/ directory. Follows the 10-category convention (ADR-054/055).;
  do not use when a narrower skill directly matches the task.'
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-04-21
license: Apache-2.0
metadata:
  author: luum
  category: standards
audience: project
summary_line: Export SO rules/ as a point-in-time snapshot into docs/08-estandares/.
model: haiku
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \brules[- ]?export\b
  confidence: 0.95
- pattern: \bexport\s+rules?\b
  confidence: 0.85
routing_intents:
- intent: export_os_rules_snapshot
  description: User wants to copy Cognitive OS governance rules into an adopting project's standards documentation as a point-in-time snapshot.
  confidence: 0.9
- intent: seed_project_standards_from_rules
  description: User asks to populate project standards docs from existing OS rules, distinct from creating new rules or scaffolding all docs.
  confidence: 0.86
triggers:
- rules-export
- /rules-export
- Smoke test in tmp dir
- Export SO rules/ as a point-in-time snapshot into docs/08-estandares/
---
<!-- SCOPE: project -->
## Purpose

Adopting projects commit to a set of SO rules as their own standards.
This skill writes a consolidated markdown snapshot of those rules into
`docs/08-estandares/rules-snapshot-<DATE>.md` so new contributors can
read the rules without needing direct access to the SO repo.

The snapshot is a point-in-time copy — the authoritative source stays
in the SO repo. Re-run `/rules-export` periodically to refresh.

## Invocation

```
/rules-export --project-dir <path>                  # default rule set
/rules-export --project-dir <path> --rules so-slo definition-of-done
```

The underlying CLI is `scripts/rules_export.py`, invoked via `uv run`.

## CLI

```bash
uv run python3 scripts/rules_export.py \
    --project-dir /path/to/adopting-project \
    [--rules so-slo definition-of-done credential-management] \
    [--so-root /path/to/cognitive-os-repo] \
    [--json]
```

### Default rule set

If `--rules` is not given, these rules are exported:

- `so-slo` — SLO catalogue (ADR-028)
- `definition-of-done` — DoD by complexity
- `credential-management` — secret handling
- `acceptance-criteria` — prompt criteria
- `responsiveness` — communication protocol
- `adversarial-review` — zero-findings halt

## Output

`docs/08-estandares/rules-snapshot-<YYYY-MM-DD>-<HHMMSS>.md` with:

1. Header: export timestamp + SO git SHA (for traceability)
2. Table of contents (links to each rule section)
3. Each rule body, preceded by `## <name>` and a source-path note,
   separated by horizontal rules.

## Success Criteria

- [ ] File created under `<project>/docs/08-estandares/`.
- [ ] File contains a ToC listing every rule passed in `--rules` (or
      the 6 defaults).
- [ ] Header notes the SO git SHA (or "unknown" when running outside a
      git checkout).
- [ ] CLI exits 0 on success, 1 on missing rule or missing `--project-dir`.

## Verification

```bash
# Smoke test in tmp dir
TMPDIR=$(mktemp -d)
uv run python3 scripts/rules_export.py --project-dir "$TMPDIR" --json
ls "$TMPDIR/docs/08-estandares/"        # exactly one .md file
grep -q "Rules Snapshot" "$TMPDIR"/docs/08-estandares/*.md
```

## Notes

- READ-ONLY against the SO repo — only writes to the adopting project.
- Does NOT modify the SO rules themselves.
- Writes are additive: each run produces a new timestamped file, so
  history is preserved. Prune manually when desired.
- For complete 10-category scaffold first, run `/project-scaffold` (ADR-054).
