# Manual Test: Primitive Surface Coverage

Purpose: prove that scope classification and surface implementation coverage are separate, inspectable axes across IDE harnesses, CLI, shell-CI, UI, and reports.

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
   assert 'surfaces' in data
   assert {'ide-harness', 'cli', 'shell-ci', 'ui', 'report'} <= set(data['surface_kinds'])
   assert data['summary']['harness_wired_hooks']['claude'] >= data['summary']['harness_wired_hooks']['codex']
   assert data['summary']['unclassified_gaps'] == 0
   PY
   ```

3. Prove CLI JSON and exit-code contracts:

   ```bash
   bash scripts/cos status --json >/tmp/cos-status.json
   bash scripts/cos coverage --json >/tmp/cos-coverage.json
   bash scripts/cos primitive harness-coverage --print-json >/tmp/primitive-surface-coverage.json
   python3 -m json.tool /tmp/cos-status.json >/dev/null
   python3 -m json.tool /tmp/cos-coverage.json >/dev/null
   python3 -m json.tool /tmp/primitive-surface-coverage.json >/dev/null
   ```

4. Inspect concrete examples:

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
       'scripts/cos-coverage',
       'scripts/primitive_harness_coverage.py',
   ]:
       row = rows.get(name)
       print('\n', name)
       print(row and {'scope': row['scope'], 'coverage': row['coverage'], 'gap': row['gap'], 'cos-cli': row['surfaces'].get('cos-cli'), 'dashboard': row['surfaces'].get('dashboard')})
   PY
   ```

5. Inspect the dashboard coverage consumer:

   ```bash
   grep -R "primitive-harness-coverage-latest.json\|Primitive Surface Coverage\|observe-only" dashboard/lib dashboard/app
   ```

6. Run automated contracts:

   ```bash
   python3 -m pytest tests/unit/test_primitive_harness_coverage.py tests/contracts/test_primitive_harness_coverage_contract.py tests/contracts/test_cos_cli_surface_contract.py -q
   ```

## Expected Result

- JSON and Markdown reports exist.
- Claude and Codex hook coverage are visibly different.
- `SCOPE: both` rows can still show surface gaps.
- CLI commands prove exit-code and JSON contracts without pretending to be hooks.
- Dashboard consumes the same report in observe-only mode.
- Runtime hooks, context surfaces, command surfaces, UI surfaces, and report surfaces are not collapsed into one misleading support claim.

## Non-Claims

This manual test does not prove every future IDE has native lifecycle support, and it does not claim a TUI exists. It proves the current report prevents confusing scope intent with implementation evidence and can add a TUI later as a real `ui` surface.
