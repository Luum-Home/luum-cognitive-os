# Kimi Code CLI Structural Projection Manual Test

## Purpose

Prove that Cognitive OS can project Kimi Code CLI project context without requiring a Kimi account or mutating global `~/.kimi` configuration.

## Source-backed surfaces

- `kimi` CLI supports `--work-dir`.
- `kimi` CLI supports `--config-file` and `--mcp-config-file`.
- Kimi project-level context can live in `AGENTS.md`.
- MCP configuration can be provided through an MCP config file.

## Test 1 — Installer projection

```bash
tmp="$(mktemp -d)"
(cd "$tmp" && python3 /ABS/PATH/TO/luum-agent-os/scripts/cos_init.py --default --harness kimi-code)

test -f "$tmp/AGENTS.md"
test -f "$tmp/.kimi/mcp.json"
test -f "$tmp/.kimi/README.md"
test -f "$tmp/.cognitive-os/rules/cos/RULES-COMPACT.md"
test -f "$tmp/.cognitive-os/skills/cos/cos-status/SKILL.md"
python3 -m json.tool "$tmp/.kimi/mcp.json" >/dev/null
grep -q 'COGNITIVE_OS_KIMI_START' "$tmp/AGENTS.md"
grep -q -- '--mcp-config-file .kimi/mcp.json' "$tmp/.kimi/README.md"
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
print('kimi-code/default=', counts['kimi-code/default'])
print('kimi-code/full=', counts['kimi-code/full'])
print('status=', payload['harness_projection']['kimi-code']['status'])
PY
```

Expected: both Kimi counts are positive and status is `implemented`.

## Test 3 — Optional account-backed runtime smoke

If Kimi Code CLI is installed and authenticated, run from the temp project:

```bash
kimi --work-dir . --mcp-config-file .kimi/mcp.json --prompt "Summarize the Cognitive OS instructions for this project."
```

Expected: Kimi responds using the projected `AGENTS.md` context. Record results under `docs/reports/` if performed.

This test is optional and must not block default CI.

## Non-claims

- No Kimi account-backed runtime behavior is proven by automated tests.
- No global `~/.kimi` config is modified.
- No native COS lifecycle hook parity is claimed.
- No real MCP servers are configured by default.

## Acceptance criteria

1. `cos_init.py --harness kimi-code` creates `AGENTS.md`, `.kimi/mcp.json`, and `.kimi/README.md`.
2. Existing `AGENTS.md` content is preserved outside the marked COS Kimi block.
3. Automated behavior tests validate generated Kimi files.
4. ACC reports `kimi-code/default` and `kimi-code/full` projection counts.
