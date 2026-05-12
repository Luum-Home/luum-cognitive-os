---

adr: 159
title: AGENTS.md-native Structural Harness Batch and Kiro Lifecycle Investigation
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos_init.py
  - manifests/harness-projection.yaml
  - manifests/harness-implementation-phases.yaml
  - manifests/ai-agent-harness-landscape.yaml
  - tests/behavior/test_consumer_project_projection.py
  - tests/contracts/test_acc_pipeline_contract.py
  - tests/contracts/test_harness_implementation_phases.py
  - tests/contracts/test_ai_agent_harness_landscape.py
  - docs/09-Quality/manual-tests/agents-md-native-structural-projection.md
tier: maintainer
tags: [harness, portability, agents-md, gemini, warp, amp, junie, qoder, factory, kiro]
---

# ADR-159: AGENTS.md-native Structural Harness Batch and Kiro Lifecycle Investigation

## Status

**Accepted** — 2026-05-05

## Context

ADR-158 created a broad landscape backlog but intentionally did not promote candidates without projection proof. The next requested slice was Gemini CLI structural projection, Kiro lifecycle-hook investigation, and AGENTS.md-native structural projection for Warp, Amp, JetBrains Junie, Qoder, and Factory Droid.

Official documentation signs enough account-free project-local surfaces for structural projection:

- Gemini CLI documents project `.gemini/settings.json`, `contextFileName`, `includeDirectories`, `loadMemoryFromIncludeDirectories`, and `mcpServers`.
- Warp documents project rules in root `AGENTS.md` and `WARP.md`, with `WARP.md` precedence when both exist.
- Amp documents `AGENTS.md`, workspace `.amp/settings.json`, and `amp.mcpServers`, with workspace MCP trust/approval.
- JetBrains Junie documents project guidelines under `.junie/AGENTS.md` and MCP through IDE settings.
- Qoder CLI documents project `AGENTS.md`, project `.mcp.json`, and project `.qoder/settings.json` permissions.
- Factory Droid documents project `AGENTS.md`, `.factory/skills/`, `.factory/mcp.json`, and `.factory/settings.json` hooks.

Kiro documentation signs lifecycle and tool hooks (`AgentSpawn`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`) and MCP/steering surfaces, but we have not mapped COS hook payloads into a generated Kiro agent configuration or run Kiro itself.

## Decision

Promote these harnesses to implemented **structural** projection:

- `gemini-cli`
- `warp`
- `amp-code`
- `jetbrains-junie`
- `qoder`
- `factory-droid`

Keep `kiro` as `planned`/`none` with lifecycle-investigation status in the landscape manifest. Kiro may become a future native-lifecycle candidate only after an explicit event-mapping adapter and runtime smoke exist.

Generated project-local files:

| Harness | Files |
|---|---|
| Gemini CLI | `GEMINI.md`, `.gemini/settings.json` |
| Warp | `AGENTS.md`, `.warp/README.md` |
| Amp | `AGENTS.md`, `.amp/settings.json` |
| JetBrains Junie | `.junie/AGENTS.md`, `.junie/README.md` |
| Qoder CLI | `AGENTS.md`, `.mcp.json`, `.qoder/settings.json` |
| Factory Droid | `AGENTS.md`, `.factory/mcp.json`, `.factory/settings.json`, `.factory/skills/cognitive-os/SKILL.md` |

All generated MCP settings are empty placeholders. COS does not write user-global config or credentials.

## Consequences

### Positive

- The ACC consumer-projection adapter now proves six additional structural harnesses through temp-project installs.
- AGENTS.md-native surfaces share a consistent bounded COS block rather than duplicating full docs.
- Factory Droid gains a project skill shim without wiring COS hooks into Factory runtime prematurely.
- Kiro's stronger hook surface is tracked separately from structural projection so native-lifecycle promotion remains evidence-gated.

### Negative

- No account-backed runtime smoke was performed for these tools.
- Structural files may need adjustment if vendors change project config paths.
- Factory and Kiro both expose hook systems, but COS native lifecycle parity remains unimplemented until event payload mapping and runtime smoke are done.

## Operational Guide

### What changes for the operator

Before this ADR, `scripts/cos_init.py` could project structural harness files only for the harnesses already listed in `manifests/harness-projection.yaml`. Six new harnesses (Gemini CLI, Warp, Amp, JetBrains Junie, Qoder, Factory Droid) had no projection entry. After this ADR:

- `scripts/cos_init.py` accepts the six new harness IDs and writes only project-local files — no user-global config or credentials are touched.
- `manifests/harness-projection.yaml` marks all six as `implemented` with `structural` proof level.
- `manifests/ai-agent-harness-landscape.yaml` marks Kiro as `lifecycle-investigation` (not implemented projection), preventing premature promotion.
- The `manifests/harness-implementation-phases.yaml` tracks the Kiro lifecycle path separately so native-lifecycle promotion stays evidence-gated.

Generated files are limited to the paths listed in §Decision. No account-backed runtime smoke was performed; structural files may need adjustment if vendors change project config paths.

### What this answers (and what it doesn't)

**Answers:**
- "Does COS project structural files for Warp / Amp / JetBrains Junie / Qoder / Factory Droid / Gemini CLI?" — yes; run `python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new` to verify projection counts.
- "What proof level does each harness have?" — read `manifests/harness-projection.yaml`; these six are `structural`.
- "Is Kiro implemented?" — `manifests/ai-agent-harness-landscape.yaml` shows `planned`/`none` with `lifecycle-investigation` status.

**Does not answer:**
- Whether the projected files work at runtime in these tools — no account-backed smoke was run. Structural projection proves files are generated; runtime proof requires a separate smoke lane.

### Reading guide for cold readers

1. Run `python3 -m pytest tests/behavior/test_consumer_project_projection.py -q` to verify structural projection counts.
2. Read `manifests/harness-projection.yaml` to see which harnesses are `implemented`, `planned`, or `blocked`.
3. Read `manifests/ai-agent-harness-landscape.yaml` for Kiro's lifecycle-investigation status and the evidence required before native-lifecycle promotion.
4. The generated files for each harness are listed in §Decision; inspect them in a temp-project install to see what COS writes.
5. `docs/09-Quality/manual-tests/agents-md-native-structural-projection.md` contains the manual proof checklist for this batch.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Promote Kiro directly to native-lifecycle | Official docs are promising, but COS has no adapter mapping or runtime smoke yet. |
| Generate user-global configs | Violates project-local projection and may touch credentials or personal IDE state. |
| Copy all COS skills into `.factory/skills/` | Too much duplication; the Factory shim references projected `.cognitive-os/skills/cos/` instead. |
| Use `WARP.md` for Warp | Warp documents `WARP.md` precedence over `AGENTS.md`; generating it would override the shared AGENTS.md path unnecessarily. |

## Verification

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
python3 -m pytest tests/contracts/test_acc_pipeline_contract.py tests/contracts/test_harness_implementation_phases.py tests/contracts/test_ai_agent_harness_landscape.py -q
python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Implementation Evidence

- `scripts/cos_init.py` accepts the six new harness IDs and writes only project-local files.
- `manifests/harness-projection.yaml` marks the six new harnesses as implemented structural projection.
- `manifests/ai-agent-harness-landscape.yaml` marks Kiro as lifecycle investigation rather than implemented projection.
- Behavior and contract tests assert generated files, ACC projection counts, proof levels, and backlog state.
