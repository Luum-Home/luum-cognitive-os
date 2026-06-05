# Duplicate Findings Triage — 2026-06-05

## Scope

This report records the Cognitive OS self-scan triage after adding the portable duplicate-quality primitive. It intentionally avoids enumerating consumer project names or project-specific local lanes.

## Inputs

Two scanners were used:

1. `scripts/cos-quality-duplicates` — portable consumer-facing scanner.
2. `scripts/primitive_duplication_audit.py` — SO-local primitive/config/code duplication audit.

Initial self-scan observations:

- Portable scanner: 66 normalized function repeats before threshold correction.
- SO-local primitive audit: 40 Python function repeats before helper extraction.

## Triage outcome

The 66 portable-scanner findings were split into two classes:

- **False-positive amplification:** the function lane did not honor `--min-tokens`, so tiny wrappers and helper bodies were reported even when the caller requested a larger threshold. Fix: the shared function scanner now respects `min_tokens`.
- **Real repeated helper logic:** shared helper extraction was warranted for script IO, path resolution, primitive file inventory, smoke-report CLI flow, local service status/metric emission, and scanner shingles/function detection.

The 40 SO-local findings were handled by extracting shared helpers rather than allowlisting current debt.

## Extracted shared homes

- `lib/duplicate_scanner.py` — scanner mechanics shared by the portable duplicate-quality primitive and the SO-local primitive duplication audit.
- `lib/script_helpers.py` — common script helpers for timestamps, YAML/JSON loading, git commands, path resolution, payload shaping, hashing, text classification, and shingling.
- `lib/primitive_file_inventory.py` — shared primitive file discovery.
- `lib/smoke_report_cli.py` — shared CLI wrapper for smoke report scripts.
- `scripts/_lib/local-service.sh` — shared local service status and metric emission.

## Verification

```bash
scripts/cos-quality-duplicates \
  --project-root . \
  --include scripts \
  --include lib \
  --include hooks \
  --include rules \
  --include skills \
  --min-tokens 80 \
  --shingle-size 40 \
  --threshold 0.90
```

Result: `findings=0`.

```bash
python3 scripts/primitive_duplication_audit.py \
  --project-root . \
  --json-out /tmp/primitive-duplication.json \
  --markdown /tmp/primitive-duplication.md \
  --fail-on-new
```

Result: `findings=0`.

## Isolation policy

No duplicate finding from this triage was closed by documenting intentional isolation. If a future duplicate is intentionally retained, the justification must state one of:

- harness-specific behavior requires separate code;
- portability boundary would be weakened by extraction;
- test fixture duplication is intentional and local to the fixture;
- generated or vendored content is excluded from scanner scope.
