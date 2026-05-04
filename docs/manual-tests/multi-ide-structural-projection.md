# Multi-IDE Structural Projection Manual Test

## Purpose

Verify that Cognitive OS can project into consumer projects for implemented IDE harnesses without requiring account-backed GUI sessions.

## Harnesses covered

- Claude Code: native settings projection.
- OpenAI Codex: hooks/settings projection.
- OpenCode: structural `opencode.json` instruction/MCP projection.
- VS Code Copilot: structural `.github/copilot-instructions.md` and `.vscode/mcp.json` projection.
- Cursor: structural `.cursor/rules/cognitive-os.mdc` and `.cursor/mcp.json` projection.

## Test 1 — Temp project projection matrix

```bash
for harness in claude codex opencode vscode-copilot cursor; do
  tmp="$(mktemp -d)"
  (cd "$tmp" && python3 /ABS/PATH/TO/luum-agent-os/scripts/cos_init.py --default --harness "$harness")
  test -f "$tmp/.cognitive-os/install-meta.json"
  test -f "$tmp/.cognitive-os/rules/cos/RULES-COMPACT.md"
  test -f "$tmp/.cognitive-os/skills/cos/cos-status/SKILL.md"
  case "$harness" in
    claude) test -f "$tmp/.claude/settings.json" ;;
    codex) test -f "$tmp/.codex/hooks.json" ;;
    opencode) test -f "$tmp/opencode.json" ;;
    vscode-copilot) test -f "$tmp/.github/copilot-instructions.md" && test -f "$tmp/.vscode/mcp.json" ;;
    cursor) test -f "$tmp/.cursor/rules/cognitive-os.mdc" && test -f "$tmp/.cursor/mcp.json" ;;
  esac
  rm -rf "$tmp"
done
```

Replace `/ABS/PATH/TO/luum-agent-os` with the local absolute repo path.

Expected: every harness exits `0` and creates its driver files.

## Test 2 — ACC projection proof

```bash
python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new
```

Expected:

- gate is `pass`;
- `new_debt.count` is `0`.

For detailed proof without loading the full JSON into agent context:

```bash
python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('docs/acc/latest.json').read_text())
print(payload['adapters']['consumer_projection']['summary']['by_harness_profile'])
print({k: v['status'] for k, v in payload['harness_projection'].items()})
PY
```

Expected: default/full counts exist for `claude`, `codex`, `cursor`, `opencode`, and `vscode-copilot`; remaining harnesses stay `planned`.

## Test 3 — Account-backed runtime smoke remains optional

If an operator has the IDE/account installed, manually open the temp project and verify the generated instruction/config file is visible to the IDE. Do not make this a required CI step.

Expected: manual notes are stored under `docs/reports/` if performed. Absence of account-backed proof must not downgrade structural projection proof.

## Acceptance criteria

1. Automated behavior tests pass for every implemented harness.
2. ACC reports structural projection counts for every implemented harness/profile.
3. Planned harnesses remain planned until they receive their own temp-project proof.
4. Documentation clearly states that structural projection is not native lifecycle hook parity.
