# Manual test — AI agent harness landscape review

## Purpose

Verify that the broad AI coding IDE/CLI/hosted-agent landscape stays useful without claiming unsupported runtime compatibility.

## Preconditions

- Run from the repository root.
- Network access is available for optional source spot checks.
- No paid IDE/CLI accounts are required.

## Steps

1. Inspect the candidate manifest:

   ```bash
   python3 - <<'PY'
   import yaml
   data = yaml.safe_load(open('manifests/ai-agent-harness-landscape.yaml'))
   print(len(data['candidates']))
   print(sorted(c['id'] for c in data['candidates'] if c['status'] in {'candidate', 'hosted-candidate', 'provider-candidate'}))
   PY
   ```

2. Confirm implemented projection is still sourced from `manifests/harness-projection.yaml`, not from the landscape backlog:

   ```bash
   python3 -m pytest tests/contracts/test_ai_agent_harness_landscape.py -q
   ```

3. Spot-check at least five official source URLs from different categories:

   - one CLI candidate;
   - one IDE candidate;
   - one hosted-agent candidate;
   - one provider/tooling candidate;
   - one implemented structural harness.

4. Confirm stale compatibility labels are absent:

   ```bash
   ! grep -nE '\bFULL COMPATIBILITY\b|\bHIGH COMPATIBILITY\b|COS Coverage|70-90%|100%' docs/04-Concepts/root/ide-compatibility.md
   ```

5. Run the ACC ratchet:

   ```bash
   python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
   ```

## Expected result

- The landscape manifest lists candidates, but only `manifests/harness-projection.yaml` declares implemented projection.
- Every candidate has a proof level and availability boundary.
- No documentation claims universal IDE/CLI runtime support.
- ACC fail-new still passes.

## Notes

If an official URL disappears or changes semantics, downgrade the candidate to `research-candidate` or remove the URL. Do not promote a candidate without tests.
