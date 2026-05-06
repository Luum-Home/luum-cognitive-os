# Manual Test: Primitive Harness Coverage

Purpose: prove that scope classification and harness implementation coverage are separate, inspectable axes.

## Preconditions

- Run from the Cognitive OS repository root.
- Python dependencies are installed.

## Steps

1. Regenerate the report:

   ```bash
   python3 scripts/primitive_harness_coverage.py --project-dir .
   ```

2. Inspect the JSON summary:

   ```bash
   python3 - <<'PY'
   import json
   data = json.load(open('docs/reports/primitive-harness-coverage-latest.json'))
   print(data['summary'])
   assert data['schema_version'] == 'primitive-harness-coverage.v1'
   assert data['summary']['harness_wired_hooks']['claude'] > data['summary']['harness_wired_hooks']['codex']
   assert data['summary']['unclassified_gaps'] == 0
   PY
   ```

3. Inspect concrete examples:

   ```bash
   python3 - <<'PY'
   import json
   rows = {row['primitive']: row for row in json.load(open('docs/reports/primitive-harness-coverage-latest.json'))['items']}
   for name in [
       'hooks/session-init.sh',
       'hooks/pre-compaction-flush.sh',
       'hooks/concurrent-write-guard-codex-proxy.sh',
       'rules/RULES-COMPACT.md',
       'scripts/cos-status.sh',
   ]:
       row = rows.get(name)
       print('\n', name)
       print(row and {'scope': row['scope'], 'coverage': row['coverage'], 'gap': row['gap'], 'harnesses': row['harnesses']})
   PY
   ```

4. Inspect the Markdown report:

   ```bash
   head -40 docs/reports/primitive-harness-coverage-latest.md
   ```

5. Run automated contracts:

   ```bash
   python3 -m pytest tests/unit/test_primitive_harness_coverage.py tests/contracts/test_primitive_harness_coverage_contract.py -q
   ```

## Expected Result

- JSON and Markdown reports exist.
- Claude and Codex hook coverage are visibly different.
- `SCOPE: both` rows can still show harness gaps.
- Runtime hooks, context surfaces, and command surfaces are not collapsed into one misleading support claim.

## Non-Claims

This manual test does not prove every future IDE has native lifecycle support. It proves the current report prevents confusing scope intent with implementation evidence.
