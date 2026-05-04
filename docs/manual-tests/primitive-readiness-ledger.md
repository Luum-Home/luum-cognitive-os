# Manual Test: Primitive Readiness Ledger

Purpose: prove that a future agent/operator can regenerate and use the machine-readable script readiness ledger without relying on conversation context.

## Preconditions

- Run from repository root.
- Python dependencies are installed.
- Working tree can contain unrelated changes; this test only writes latest reports under `docs/reports/`.

## Steps

1. Regenerate the ledger:

   ```bash
   python3 scripts/primitive_readiness_ledger.py --project-dir .
   ```

2. Inspect the JSON summary:

   ```bash
   python3 - <<'PY'
   import json
   data = json.load(open('docs/reports/primitive-readiness-ledger-scripts-latest.json'))
   print(data['summary'])
   assert data['target_family'] == 'scripts'
   assert data['summary']['total_scripts'] > 0
   assert not [row for row in data['scripts'] if row['role'] not in data['allowed_roles']]
   PY
   ```

3. Inspect the lifecycle backlog:

   ```bash
   python3 - <<'PY'
   import json
   data = json.load(open('docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.json'))
   print(data['summary'])
   assert data['purpose'] == 'agentic primitives missing ADR-126 lifecycle metadata'
   PY
   ```

4. Inspect the Markdown report:

   ```bash
   head -40 docs/reports/primitive-readiness-ledger-scripts-latest.md
   ```

5. Pick three rows, one each from `agentic-primitive`, `maintainer-tool`, and either `driver-specific` or `migration-only`. Confirm the row has a believable `role_source`, `confidence`, evidence, consumers, and next action.

6. Run the automated contract:

   ```bash
   python3 -m pytest tests/unit/test_primitive_readiness_ledger.py tests/contracts/test_primitive_readiness_ledger_contract.py -q
   ```

## Expected Result

- JSON and Markdown reports exist.
- Every script row has an allowed role.
- Low-confidence rows remain visible but do not fail the default command.
- Optional fail flags can be used later as a ratchet, not as the initial adoption gate.

## Non-Claims

This manual test does not prove every script is correctly promoted or retired. It proves the ledger exists, is complete, and is usable as the next triage surface.
