# Manual Test: Agent Capability Coverage Pipeline

Purpose: prove that the ACC pipeline can regenerate the unified coverage report without relying on chat context.

## Steps

1. Refresh the ACC pipeline:

   ```bash
   python3 scripts/acc_pipeline.py --project-dir . --refresh
   ```

2. Inspect compact context-diet output:

   ```bash
   python3 scripts/acc_pipeline.py --project-dir . --brief
   head -80 docs/acc/latest-compact.md
   ```

3. Inspect JSON invariants:

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

4. Inspect the Markdown summary:

   ```bash
   head -80 docs/acc/latest.md
   ```

5. Confirm adapter reports are not silently dropped:

   ```bash
   python3 - <<'PY'
   import json
   data = json.load(open('docs/acc/latest.json'))
   for name, status in data['adapters'].items():
       print(name, status['status'])
       assert status['status'] in {'ok', 'unverified', 'failed'}
   PY
   ```

6. Run automated tests:

   ```bash
   python3 -m pytest tests/unit/test_acc_pipeline.py tests/contracts/test_acc_pipeline_contract.py -q
   ```

## Expected Result

- `docs/acc/latest-compact.md`, `docs/acc/latest.json`, and `docs/acc/latest.md` exist.
- The report includes capabilities, findings, adapter status, consumer accessibility, scores, and persistence status.
- Local history is appended under `.cognitive-os/metrics/acc-pipeline-history.jsonl`.
- Engram status is honest: unavailable unless a real bridge/tool exists.

## Consumer Projection Check

After refresh, confirm the projection adapter ran:

```bash
python3 - <<'PY'
import json
data = json.load(open('docs/acc/latest.json'))
projection = data['adapters']['consumer_projection']
print(projection)
assert projection['status'] == 'ok'
assert projection['summary']['projected_primitives'] > 0
assert data['summary']['stale_weight'] == 0
PY
```

Expected result: Claude/Codex default projection rows are counted as `projected-consumer-surface`; unproved IDEs remain unsigned.

## Harness Registry Check

Confirm all named IDEs are declared and only implemented harnesses are signed:

```bash
python3 - <<'PY'
import json, yaml
manifest = yaml.safe_load(open('manifests/harness-projection.yaml'))
ids = {item['id'] for item in manifest['harnesses']}
required = {'claude', 'codex', 'cursor', 'windsurf', 'vscode-copilot', 'opencode', 'google-antigravity', 'shell-ci'}
assert required <= ids
acc = json.load(open('docs/acc/latest.json'))
assert acc['harness_projection']['claude']['status'] == 'implemented'
assert acc['harness_projection']['codex']['status'] == 'implemented'
assert acc['harness_projection']['cursor']['status'] == 'planned'
PY
```
