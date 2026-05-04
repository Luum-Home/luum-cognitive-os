# Manual Test — Primitive Duplication Audit

## Purpose

Verify that the primitive duplication audit runs locally, emits reports, and produces actionable common-home recommendations.

## Steps

```bash
python3 scripts/primitive_duplication_audit.py --project-root . --json
python3 - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('docs/reports/primitive-duplication-latest.json').read_text())
print(report['summary'])
assert report['schema_version'] == 'primitive-duplication-audit.v1'
assert 'findings' in report['summary']
PY
python3 scripts/acc_pipeline.py --project-dir . --refresh --brief | python3 -m json.tool | grep primitive_duplication
```

## Expected result

- The JSON report exists at `docs/reports/primitive-duplication-latest.json`.
- The Markdown report exists at `docs/reports/primitive-duplication-latest.md`.
- Findings include `recommendation`, `common_home`, and `consumer_relevance` fields.
- ACC refresh includes the `primitive_duplication` adapter.

## Triage notes

Do not extract every finding automatically. First classify each top candidate as:

- extract now;
- intentional duplication;
- needs owner review;
- false positive;
- blocked by harness/projection semantics.
