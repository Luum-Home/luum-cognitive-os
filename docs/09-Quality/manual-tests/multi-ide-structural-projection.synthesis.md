---
type: quality-synthesis
source: docs/09-Quality/manual-tests/multi-ide-structural-projection.md
provenance: "Manual test verifying Cognitive OS can project into consumer projects across five implemented IDE harnesses without requiring account-backed GUI sessions."
---

## What it is
A manual test proving structural (file/config-based) projection of Cognitive OS across five implemented harnesses — Claude Code, OpenAI Codex, OpenCode, VS Code Copilot, and Cursor — via a single loop that initializes a temp project per harness and asserts the expected driver files exist, plus an ACC projection-count proof.

## Key mechanics
- Harnesses covered and their projection artifacts: Claude Code (native settings), Codex (hooks/settings), OpenCode (structural `opencode.json`), VS Code Copilot (`.github/copilot-instructions.md` + `.vscode/mcp.json`), Cursor (`.cursor/rules/cognitive-os.mdc` + `.cursor/mcp.json`).
- Test 1: loops over all five harness names, runs `cos_init.py --default --harness <h>` in a fresh temp dir each time, asserts common files (`.cognitive-os/install-meta.json`, `RULES-COMPACT.md`, `cos-status/SKILL.md`) plus the harness-specific file(s) via a case statement. Expected: every harness exits 0.
- Test 2: ACC projection proof — `scripts/acc_pipeline.py --project-dir . --brief --fail-new` must report gate=`pass` and `new_debt.count`=0; a targeted query against `docs/07-Capabilities/acc/latest.json` confirms default/full counts exist for all five harnesses and prints each harness's projection status (remaining/unlisted harnesses stay `planned`).
- Test 3: account-backed runtime smoke is explicitly optional and non-CI-blocking — an operator manually confirms the generated instruction/config file is visible inside a real IDE session; absence of this proof must not downgrade the structural projection proof.
- Acceptance criteria (4 items): automated behavior tests pass per implemented harness; ACC reports structural projection counts per implemented harness/profile; planned harnesses stay planned until they get their own temp-project proof; documentation must clearly state structural projection is not native lifecycle hook parity.

## Relations & where used
Depends on `scripts/cos_init.py`, `scripts/acc_pipeline.py`, `docs/07-Capabilities/acc/latest.json`. Direct sibling of `kimi-code-cli-structural-projection.md`, which applies the identical proof pattern to a sixth harness (Kimi Code CLI) documented separately because Kimi lacks a native hook lifecycle.

## Status / caveats
No dated snapshot or inconsistency found. The doc is careful to distinguish "structural projection proven" from "native lifecycle hook parity" (not claimed) and from "account-backed GUI proof" (explicitly optional).
