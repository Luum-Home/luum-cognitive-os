# Manual Test: Consumer Project Primitive Accessibility

Purpose: prove that primitive readiness claims are grounded in downstream project projection, not only in SO-local documentation.

## Steps

1. Run automated consumer projection checks:

   ```bash
   python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
   ```

2. Regenerate all readiness ledgers:

   ```bash
   python3 scripts/primitive_readiness_ledger.py --project-dir . --fail-low-confidence
   for family in hooks skills rules; do
     python3 scripts/primitive_family_readiness_ledger.py --project-dir . --target-family "$family"
   done
   ```

3. Inspect consumer accessibility summaries:

   ```bash
   python3 - <<'PY'
   import json
   for family in ('scripts', 'hooks', 'skills', 'rules'):
       path = f'docs/reports/primitive-readiness-ledger-{family}-latest.json'
       data = json.load(open(path))
       print(family, data['summary']['consumer_accessibility'])
       assert 'consumer_accessibility' in data['summary']
   PY
   ```

4. Create temporary consumer projects manually if investigating an install regression:

   ```bash
   tmp=$(mktemp -d)
   (cd "$tmp" && python3 /path/to/luum-agent-os/scripts/cos_init.py --default --harness claude)
   find "$tmp/.cognitive-os" -maxdepth 3 -type f | sort | head -40
   rm -rf "$tmp"
   ```

5. For any new IDE/harness claim, repeat step 4 with that harness driver or wrapper and record the exact files projected.

## Expected result

- Claude Code and Codex default projection are proven by automated temp-project tests.
- Family ledgers expose consumer accessibility metadata.
- Any unproved IDE remains documented as not signed rather than implied by SO-local docs.
