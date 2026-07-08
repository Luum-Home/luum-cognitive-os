---
type: quality-synthesis
source: docs/09-Quality/manual-tests/qwen-code-structural-projection.md
provenance: "Proves Cognitive OS can project Qwen Code project-local settings and context files without requiring a Qwen account or CLI runtime, while enumerating the gaps still separating structural projection from proven runtime delegation."
---

## What it is
A manual test validating account-free structural projection of Qwen Code settings (`.qwen/settings.json`, `QWEN.md`, MCP server declarations) by the Cognitive OS installer, plus an explicit list of what is still unproven about real Qwen-backed runtime delegation.

## Key mechanics
- **Test 1 — Installer projection**: run `cos_init.py --default --harness qwen-code` in a temp dir; assert `.qwen/settings.json`, `QWEN.md`, `.cognitive-os/rules/cos/RULES-COMPACT.md`, and `.cognitive-os/skills/cos/cos-status/SKILL.md` exist; assert `context.fileName[0] == 'QWEN.md'`, `.cognitive-os/skills/cos` is in `includeDirectories`, `mcpServers == {}`, and `tools.approvalMode == 'default'`.
- **Test 2 — ACC projection counts**: `python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new` must report gate `pass` and `new_debt.count == 0`; a targeted query against `docs/07-Capabilities/acc/latest.json` confirms `qwen-code/default` and `qwen-code/full` counts are positive and status is `implemented`.
- **Test 3 — Optional account-backed smoke**: only run with a real authenticated Qwen Code install; not required for default CI.
- **Runtime delegation proof gaps** (six items still required before claiming proven delegation): an API auth probe (`cos-auth-probe --provider qwen --mode api-key`), a separate CLI/account auth probe for `qwen-code`/`account-session` mode, a temp-repo smoke with redacted evidence artifacts, a real `lib/qwen_agent_loop.py` round trip (read_file/edit_file/run_bash) against a live Qwen client, a dispatch metric row with `provider_used` actually `qwen`/`qwen-code` (not `offline_dispatch_smoke`), and an explicit runtime-boundary statement identifying which auth path was tested.
- **Non-claims**: no account-backed runtime behavior is proven by automated tests; no native COS lifecycle hook parity; no real MCP servers configured by default.

## Relations & where used
Parallels `shell-ci-formal-harness.md` and `rules-mcp-structural-projection.md` as harness-projection proofs feeding the ACC (`scripts/acc_pipeline.py`) harness-implementation-phase reporting.

## Status / caveats
The doc itself is explicit that the "supported claim" is narrower than full delegation: structural projection is implemented, Qwen API fallback has code and a live smoke script, but real account-backed Qwen delegation remains unproven until all six listed gap items are closed. Not a dated snapshot — a living gap-tracking test spec.
