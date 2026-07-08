---
type: quality-synthesis
source: docs/09-Quality/manual-tests/agents-md-native-structural-projection.md
provenance: "Manual test verifying account-free structural projection of AGENTS.md-native config into 6 IDE/CLI harnesses (Gemini CLI, Warp, Amp, JetBrains Junie, Qoder CLI, Factory Droid), while confirming Kiro stays investigation-only."
---

## What it is
A manual procedure that scaffolds a temp project for each of 6 harnesses via `cos_init.py --harness <name>`, checks that the expected project-local files land, and confirms Kiro's lifecycle-hooks integration remains explicitly `planned`/`proof_level: none` rather than claimed as implemented.

## Key mechanics
- Preconditions: run from repo root; no paid IDE/CLI account required; vendor CLIs should not be launched except for explicitly optional smoke tests.
- Structural projection step: loops over `gemini-cli warp amp-code jetbrains-junie qoder factory-droid`, running `cos_init.py --default --harness "$harness"` in a fresh temp dir and listing which of `AGENTS.md`/`GEMINI.md`/`settings.json`/`mcp.json`/`.mcp.json`/`SKILL.md` were created.
- Expected file table per harness: Gemini CLI → `GEMINI.md` + `.gemini/settings.json`; Warp → `AGENTS.md` + `.warp/README.md`; Amp → `AGENTS.md` + `.amp/settings.json`; JetBrains Junie → `.junie/AGENTS.md` + `.junie/README.md`; Qoder CLI → `AGENTS.md` + `.mcp.json` + `.qoder/settings.json`; Factory Droid → `AGENTS.md` + `.factory/mcp.json` + `.factory/settings.json` + `.factory/skills/cognitive-os/SKILL.md`.
- Kiro check: reads `manifests/harness-projection.yaml` and `manifests/ai-agent-harness-landscape.yaml`, expecting Kiro's projection status `planned` with `proof_level: none`, and landscape status `lifecycle-investigation`.
- Automated validation: `tests/behavior/test_consumer_project_projection.py`, `tests/contracts/test_acc_pipeline_contract.py`, `tests/contracts/test_harness_implementation_phases.py`, `tests/contracts/test_ai_agent_harness_landscape.py`, plus `scripts/acc_pipeline.py --refresh --fail-new`.
- Optional runtime smoke (account-gated, not required): per-harness live checks (e.g., run `gemini` and confirm `GEMINI.md` is picked up, or `droid exec` and confirm the COS skill shim loads) — explicitly must not be marked passed unless the account-backed command was actually executed, and any promotion beyond `structural` proof level requires a dated report.

## Relations & where used
Drives `scripts/cos_init.py --harness`, `manifests/harness-projection.yaml`, `manifests/ai-agent-harness-landscape.yaml`. Sibling to `docs/09-Quality/manual-tests/ai-agent-harness-landscape-review.md` (broader candidate landscape review) and `docs/09-Quality/manual-tests/acc-fail-new-gate.md` (implemented-vs-planned harness gating).

## Status / caveats
Procedural manual-test document, not a dated execution report — no recorded pass/fail outcome for a specific run. Explicitly separates unverified "structural" scaffolding proof from account-gated "runtime" proof, and instructs against inflating one into the other.
