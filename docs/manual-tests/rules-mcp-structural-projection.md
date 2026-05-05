# Manual test — Rules/MCP structural harness projection

## Purpose

Verify account-free structural projection for Cline, Continue.dev, Kilo Code, Zed AI, Augment/Auggie, Goose, and Aider.

## Preconditions

- Run from the Cognitive OS repository root.
- No paid IDE/CLI accounts are required.
- Do not launch vendor CLIs/IDEs unless running optional smoke tests.

## Structural projection steps

```bash
for harness in cline continue-dev kilo-code zed-ai augment-code goose aider; do
  tmp="$(mktemp -d)"
  (cd "$tmp" && python3 <repo-root>/scripts/cos_init.py --default --harness "$harness")
  echo "== $harness =="
  find "$tmp" -maxdepth 4 \
    \( -name 'AGENTS.md' -o -name 'CONVENTIONS.md' -o -name '.aider.conf.yml' -o -name '.rules' -o -name '.goosehints' -o -name 'settings.json' -o -name 'mcp.json' -o -name 'cognitive-os.md' -o -name 'cognitive-os.json' -o -name 'kilo.jsonc' \) \
    -print | sort
  rm -rf "$tmp"
done
```

## Expected files

| Harness | Expected files |
|---|---|
| Cline | `.clinerules/cognitive-os.md`, `.cline/README.md` |
| Continue.dev | `.continue/rules/cognitive-os.md`, `.continue/mcpServers/cognitive-os.json` |
| Kilo Code | `AGENTS.md`, `.kilocode/rules/cognitive-os.md`, `.kilocode/mcp.json`, `.kilo/kilo.jsonc` |
| Zed AI | `.rules`, `.zed/settings.json` |
| Augment/Auggie | `.augment/rules/cognitive-os.md`, `.augment/settings.json` |
| Goose | `.goosehints`, `.goose/config.json` |
| Aider | `CONVENTIONS.md`, `.aider.conf.yml` |

## Automated validation

```bash
python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
python3 -m pytest tests/contracts/test_acc_pipeline_contract.py tests/contracts/test_harness_implementation_phases.py tests/contracts/test_ai_agent_harness_landscape.py -q
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Optional runtime smoke

Only run if the relevant CLI/IDE and account credentials are available. Record a dated report before promoting proof beyond `structural`.

- Cline: open the project and confirm `.clinerules/cognitive-os.md` is loaded.
- Continue.dev: open the project and confirm the rule/MCP placeholder is recognized.
- Kilo Code: run/open Kilo and confirm AGENTS/rules/settings are loaded.
- Zed AI: open the project and confirm `.rules` is loaded.
- Augment/Auggie: run Auggie and confirm `.augment` rules/settings are recognized.
- Goose: run Goose from the project and confirm `.goosehints` is used.
- Aider: run Aider and confirm `.aider.conf.yml` reads `CONVENTIONS.md`.
