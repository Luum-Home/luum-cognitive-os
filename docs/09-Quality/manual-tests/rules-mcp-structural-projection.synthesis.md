---
type: quality-synthesis
source: docs/09-Quality/manual-tests/rules-mcp-structural-projection.md
provenance: "Verifies account-free structural projection of Cognitive OS rules/MCP configuration into seven additional harnesses: Cline, Continue.dev, Kilo Code, Zed AI, Augment/Auggie, Goose, and Aider."
---

## What it is
A manual test proving `scripts/cos_init.py` can project harness-specific rule/MCP configuration files for seven IDE/CLI harnesses without requiring paid accounts, and listing the exact expected file per harness.

## Key mechanics
- **Structural projection loop**: for each of `cline`, `continue-dev`, `kilo-code`, `zed-ai`, `augment-code`, `goose`, `aider`, run `cos_init.py --default --harness <harness>` in a temp dir and `find` for the expected marker files (`AGENTS.md`, `CONVENTIONS.md`, `.aider.conf.yml`, `.rules`, `.goosehints`, `settings.json`, `mcp.json`, `cognitive-os.md`, `cognitive-os.json`, `kilo.jsonc`).
- **Expected files table**: Cline → `.clinerules/cognitive-os.md`, `.cline/README.md`; Continue.dev → `.continue/rules/cognitive-os.md`, `.continue/mcpServers/cognitive-os.json`; Kilo Code → `AGENTS.md`, `.kilocode/rules/cognitive-os.md`, `.kilo/kilo.jsonc`; Zed AI → `.rules`, `.zed/settings.json`; Augment/Auggie → `.augment/rules/cognitive-os.md`, `.augment/mcp.json`, `.augment/README.md`; Goose → `.goosehints`; Aider → `CONVENTIONS.md`, `.aider.conf.yml`.
- **Automated validation**: `python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py`; `tests/behavior/test_consumer_project_projection.py`; `tests/contracts/test_acc_pipeline_contract.py`, `test_harness_implementation_phases.py`, `test_ai_agent_harness_landscape.py`; `scripts/acc_pipeline.py --project-dir . --refresh --fail-new`.
- **Optional runtime smoke**: only with the real CLI/IDE and credentials available — open each project and confirm the harness actually loads its rule/config file; results should be recorded before promoting proof past "structural."

## Relations & where used
Sibling proof to `qwen-code-structural-projection.md` and `shell-ci-formal-harness.md`; all three feed the same ACC harness-implementation-phase reporting pipeline (`scripts/acc_pipeline.py`).

## Status / caveats
No dated evidence block is embedded — this is a repeatable procedure spec, not a logged historical run. Runtime (account-backed) confirmation for each harness is explicitly optional and unproven by default.
