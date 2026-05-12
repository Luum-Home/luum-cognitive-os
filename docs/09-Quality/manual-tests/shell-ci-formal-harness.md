# Shell CI Formal Harness Manual Test

## Purpose

Prove that Shell/CI is a first-class implemented harness that can be installed into a temp consumer project without IDE accounts.

## Test 1 — Installer projection

```bash
tmp="$(mktemp -d)"
(cd "$tmp" && python3 /ABS/PATH/TO/luum-agent-os/scripts/cos_init.py --default --harness shell-ci)

test -f "$tmp/.cognitive-os/install-meta.json"
test -f "$tmp/.cognitive-os/shell-ci-projection.json"
test -f "$tmp/.cognitive-os/scripts/cos/cos-status.sh"
test -L "$tmp/scripts/cos-status.sh"
test -f "$tmp/.github/workflows/cognitive-os-shell-ci.yml"
python3 -m json.tool "$tmp/.cognitive-os/shell-ci-projection.json" >/dev/null
bash -n "$tmp/.cognitive-os/scripts/cos/cos-status.sh"
rm -rf "$tmp"
```

Replace `/ABS/PATH/TO/luum-agent-os` with the local absolute repo path.

Expected: all checks exit `0`.

## Test 2 — ACC projection counts

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new
```

Expected:

- gate is `pass`;
- `new_debt.count` is `0`.

Targeted proof query:

```bash
python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('docs/acc/latest.json').read_text())
counts = payload['adapters']['consumer_projection']['summary']['by_harness_profile']
print('shell-ci/default=', counts['shell-ci/default'])
print('shell-ci/full=', counts['shell-ci/full'])
print('status=', payload['harness_projection']['shell-ci']['status'])
PY
```

Expected: both shell/CI counts are positive and status is `implemented`.

## Test 3 — Workflow syntax baseline

```bash
python3 -m pytest tests/unit/test_project_shell_ci.py -q
```

Expected: generated workflow includes syntax checks for Bash and Python projected commands.

## Non-claims

- This does not prove every projected command succeeds in every consumer stack.
- This does not re-enable disabled repository CI workflows.
- This does not require a GitHub account or hosted runner.

## Acceptance criteria

1. `cos_init.py --harness shell-ci` creates command drivers and workflow files.
2. ACC reports `shell-ci/default` and `shell-ci/full` projection counts.
3. Automated tests verify generated files, executable bits, and workflow syntax commands.
4. Runtime command smoke remains optional and stack-specific.
