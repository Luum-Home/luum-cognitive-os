# Qwen Code Structural Projection Manual Test

## Purpose

Prove that Cognitive OS can project Qwen Code project-local settings and context without requiring a Qwen account or CLI runtime.

## Source-backed surfaces

- `.qwen/settings.json` is Qwen Code's project settings file.
- `mcpServers` is the Qwen Code MCP server declaration object.
- `QWEN.md` and configurable context filenames provide hierarchical instructional context.

## Test 1 — Installer projection

```bash
tmp="$(mktemp -d)"
(cd "$tmp" && python3 /ABS/PATH/TO/luum-agent-os/scripts/cos_init.py --default --harness qwen-code)

test -f "$tmp/.qwen/settings.json"
test -f "$tmp/QWEN.md"
test -f "$tmp/.cognitive-os/rules/cos/RULES-COMPACT.md"
test -f "$tmp/.cognitive-os/skills/cos/cos-status/SKILL.md"
python3 -m json.tool "$tmp/.qwen/settings.json" >/dev/null
python3 - <<PY
import json
from pathlib import Path
settings = json.loads(Path('$tmp/.qwen/settings.json').read_text())
assert settings['context']['fileName'][0] == 'QWEN.md'
assert '.cognitive-os/skills/cos' in settings['context']['includeDirectories']
assert settings['mcpServers'] == {}
assert settings['tools']['approvalMode'] == 'default'
PY
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

Targeted query:

```bash
python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('docs/acc/latest.json').read_text())
counts = payload['adapters']['consumer_projection']['summary']['by_harness_profile']
print('qwen-code/default=', counts['qwen-code/default'])
print('qwen-code/full=', counts['qwen-code/full'])
print('status=', payload['harness_projection']['qwen-code']['status'])
PY
```

Expected: both Qwen counts are positive and status is `implemented`.

## Test 3 — Optional account-backed runtime smoke

If an operator has Qwen Code installed and authenticated, open the temp project or run Qwen Code from the temp project and verify it recognizes `QWEN.md`/settings context. Record results under `docs/reports/` if performed.

This is optional and must not block default CI.

## Non-claims

- No Qwen account-backed runtime behavior is proven by automated tests.
- No native COS lifecycle hook parity is claimed.
- No real MCP servers are configured by default.

## Acceptance criteria

1. `cos_init.py --harness qwen-code` creates `.qwen/settings.json` and `QWEN.md`.
2. Automated behavior tests validate settings shape and conservative MCP/tool defaults.
3. ACC reports `qwen-code/default` and `qwen-code/full` projection counts.
4. Runtime smoke remains optional and account-dependent.
