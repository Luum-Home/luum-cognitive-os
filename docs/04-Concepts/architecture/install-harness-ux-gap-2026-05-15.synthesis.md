---
type: concept-synthesis
source: docs/04-Concepts/architecture/install-harness-ux-gap-2026-05-15.md
status: active
provenance: "install.sh under-claimed the multi-IDE projection work already supported by scripts/cos_init.py (originally accepted only claude|codex)."
---

## What it is
Architecture-gap review (2026-05-15) of whether the top-level installer communicates the same multi-IDE ambition as `scripts/cos_init.py`. Answer: partially, closing over successive slices.

## Key mechanics
- `cos_init.py` owns supported harness identifiers, settings/instruction output paths, native vs structural split, canonical copy into `.cognitive-os/{hooks,rules,skills,templates}/cos`, Claude-only driver projections, and install metadata (`harness`, `settings_driver`).
- `install.sh` now accepts 21 harnesses: claude, codex, agents-md, opencode, vscode-copilot, cursor, qwen-code, kimi-code, gemini-cli, warp, amp-code, jetbrains-junie, qoder, factory-droid, cline, continue-dev, kilo-code, zed-ai, augment-code, goose, aider, shell-ci.
- Drift test: `tests/integration/test_installer.py` compares `install.sh`'s `SUPPORTED_HARNESSES` against `cos_init.py::SUPPORTED_HARNESSES`, failing CI on divergence.
- Shared registry: source manifest `manifests/harness-projection.yaml` -> generator `scripts/generate_harness_projection_registry.py` -> runtime registry `manifests/harness-projection-registry.json`, consumed by `cos_init.py` and `cmd/cos/internal/cli/harness_projection.go`.
- `generate-project-settings.sh` intentionally stays `claude|codex` only (native lifecycle hook emitters); structural harnesses go through `cos_init.py` instruction/rule/MCP-placeholder writes.
- Devin remains planned-but-unsupported in `manifests/harness-projection.yaml` and `cos_init.py` — an explicit honest error, not silent fallback.
- Apply-mode primitives: `cos install primitive <family/name> --harness <id>` writes into `.cognitive-os/{skills,hooks,rules}/cos/`, backs up existing targets + harness projection file, emits JSON receipt under `.cognitive-os/receipts/`. `cos install profile default|full --harness <id>` and `cos project --harness <id> --profile ...` delegate to `cos_init.py`. All support `--dry-run`; `--runtime-smoke` is opt-in for cursor/qwen-code/gemini-cli/opencode.
- JSON settings merge: existing settings captured before projection, `cos_init.py` emits COS shape, then structural recursive merge with array union by stable identity; JSONC backed up but not parsed.
- `cos doctor harness` reports active/selected harness, projection path, proof level, settings paths, receipt/backup/runtime-smoke counts, next action (`--json` supported).
- Canonical primitive catalog lockfile: `manifests/agentic-primitive-registry.lock.yaml` (generated/locked; harness dirs remain projection targets, not source of truth).

## Relations & where used
`install.sh`, `scripts/cos_init.py`, `scripts/generate-project-settings.sh`, `scripts/_lib/settings-driver.sh`, `manifests/harness-projection.yaml`, `manifests/primitive-projection-profiles.yaml`, `manifests/harness-driver-capabilities.yaml`, `manifests/agentic-primitive-registry.lock.yaml`, `tests/integration/test_installer.py`, `tests/behavior/test_consumer_project_projection.py`, `davila7/claude-code-templates` pattern extraction table.

## Status / caveats
Remaining open items: `install.sh --help` render from generated registry; helper scripts resolve `settings_driver` for every harness; deeper structured JSON merge; `cos primitive stats --harness <id>`; bounded COS blocks idempotency. Slice A/most of B/C/D closed per checklist; Slice E partial.
