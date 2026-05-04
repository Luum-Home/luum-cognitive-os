# Manual Test: Agent Capability Coverage Pipeline

Purpose: prove that the ACC pipeline can regenerate the unified coverage report without relying on chat context.

## Steps

1. Refresh the ACC pipeline:

   ```bash
   python3 scripts/acc_pipeline.py --project-dir . --refresh
   ```

2. Inspect JSON invariants:

   ```bash
   python3 - <<'PY'
   import json
   data = json.load(open('docs/acc/latest.json'))
   print(data['summary'])
   assert data['schema_version'] == 'acc.report.v1'
   assert data['capabilities']
   assert 'acc_effective' in data['summary']
   assert {'aligned', 'partial', 'missing', 'stale', 'overexposed', 'unverified'} <= set(data['mapping_statuses'])
   assert 'persistence' in data
   PY
   ```

3. Inspect the Markdown summary:

   ```bash
   head -80 docs/acc/latest.md
   ```

4. Confirm adapter reports are not silently dropped:

   ```bash
   python3 - <<'PY'
   import json
   data = json.load(open('docs/acc/latest.json'))
   for name, status in data['adapters'].items():
       print(name, status['status'])
       assert status['status'] in {'ok', 'unverified', 'failed'}
   PY
   ```

5. Run automated tests:

   ```bash
   python3 -m pytest tests/unit/test_acc_pipeline.py tests/contracts/test_acc_pipeline_contract.py -q
   ```

## Expected Result

- `docs/acc/latest.json` and `docs/acc/latest.md` exist.
- The report includes capabilities, findings, adapter status, consumer accessibility, scores, and persistence status.
- Local history is appended under `.cognitive-os/metrics/acc-pipeline-history.jsonl`.
- Engram status is honest: unavailable unless a real bridge/tool exists.
