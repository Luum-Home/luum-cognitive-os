---
type: quality-synthesis
source: docs/09-Quality/manual-tests/kimi-code-cli-structural-projection.md
provenance: "Manual test proving Cognitive OS can project Kimi Code CLI project context without requiring a Kimi account or mutating global ~/.kimi configuration."
---

## What it is
A manual test validating structural (non-account-backed) projection of Cognitive OS into Kimi Code CLI projects: generated `AGENTS.md`, `.kimi/mcp.json`, and `.kimi/README.md`, plus ACC (Adopter Capability Catalog) projection-count proof and an optional real-CLI smoke test.

## Key mechanics
- Source-backed surfaces: `kimi` CLI supports `--work-dir`, `--config-file`, and `--mcp-config-file`; Kimi project-level context lives in `AGENTS.md`; MCP config is provided via a config file.
- Test 1 (installer projection): runs `cos_init.py --default --harness kimi-code` in a temp dir and asserts creation of `AGENTS.md`, `.kimi/mcp.json`, `.kimi/README.md`, `.cognitive-os/rules/cos/RULES-COMPACT.md`, `.cognitive-os/skills/cos/cos-status/SKILL.md`; validates `.kimi/mcp.json` as JSON; greps for the `COGNITIVE_OS_KIMI_START` marker in `AGENTS.md` and the `--mcp-config-file .kimi/mcp.json` invocation snippet in `.kimi/README.md`.
- Test 2 (ACC projection counts): `scripts/acc_pipeline.py --project-dir . --brief --fail-new` must report gate=`pass` and `new_debt.count`=0; a targeted query reads `docs/07-Capabilities/acc/latest.json` and expects positive counts for `kimi-code/default` and `kimi-code/full`, with harness-projection status `implemented`.
- Test 3 (optional, account-backed smoke): if Kimi CLI is installed/authenticated, run `kimi --work-dir . --mcp-config-file .kimi/mcp.json --prompt ...` and expect a response using the projected `AGENTS.md` context; explicitly optional and must not block default CI.
- Non-claims: no Kimi account-backed runtime behavior is proven by automated tests; no global `~/.kimi` config is modified; no native COS lifecycle hook parity is claimed; no real MCP servers are configured by default.
- Acceptance criteria (4 items): installer creates the three files; existing `AGENTS.md` content outside the marked COS block is preserved; automated behavior tests validate generated Kimi files; ACC reports both default/full projection counts.

## Relations & where used
Depends on `scripts/cos_init.py --harness kimi-code`, `scripts/acc_pipeline.py`, and `docs/07-Capabilities/acc/latest.json`. Sibling to `multi-ide-structural-projection.md`, which runs the same structural-projection pattern across five other harnesses (Claude, Codex, OpenCode, VS Code Copilot, Cursor) in a single loop.

## Status / caveats
No dated snapshot; consistent with the multi-IDE sibling doc's proof pattern. Test 3's real-CLI smoke depends on optional local tooling availability and is explicitly not CI-gated.
