# ACC Fail-New Gate Manual Test

## Purpose

Prove that ACC can ratchet from the current baseline without letting broad local-surface defaults hide new agentic primitive debt, and without treating planned IDE/provider harnesses as implemented support.

## Preconditions

- Run from the repository root.
- `docs/07-Capabilities/acc/latest.json` exists as the current baseline.
- Do not open the full JSON in agent context; use `--brief` or targeted queries.

## Test 1 — Current baseline passes fail-new

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new
```

Expected:

- exit code `0`;
- `new_debt.status` is `pass`;
- `new_debt.count` is `0`.

Targeted query if needed:

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["new_debt"])'
```

## Test 2 — Missing baseline blocks

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new --baseline /tmp/cos-missing-acc-baseline.json
```

Expected:

- exit code `1`;
- `gate.status` is `block`;
- `gate.blocks` includes `missing_fail_new_baseline`.

## Test 3 — Broad local defaults are not a silent escape hatch

Use the automated unit test as the canonical safe mutation proof:

```bash
python3 -m pytest tests/unit/test_acc_pipeline.py -q
```

Expected:

- `test_fail_new_strictly_blocks_new_broad_local_default` passes;
- a new row aligned only by `availability_match:pattern` becomes `unreviewed-local-default` debt under strict fail-new.

## Test 4 — Planned harnesses remain roadmap-only

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
manifest = yaml.safe_load(Path('manifests/harness-projection.yaml').read_text())
implemented = sorted(item['id'] for item in manifest['harnesses'] if item['status'] == 'implemented')
planned = sorted(item['id'] for item in manifest['harnesses'] if item['status'] == 'planned')
print('implemented=', implemented)
print('planned_count=', len(planned))
assert implemented == ['claude', 'codex']
assert 'cursor' in planned and 'opencode' in planned and 'qwen-code' in planned
PY
```

Expected:

- only `claude` and `codex` are implemented;
- all other named IDE/provider harnesses remain planned until projection drivers and temp-project proofs exist.

## Acceptance Criteria

1. `python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new` exits `0` on the current baseline.
2. Missing baseline exits non-zero under `--fail-new`.
3. Unit tests prove new debt and new broad-local-default rows block.
4. Planned harnesses are visible in the registry but never counted as implemented support.
