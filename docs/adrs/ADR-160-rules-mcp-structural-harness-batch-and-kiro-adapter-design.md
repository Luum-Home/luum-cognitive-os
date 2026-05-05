---
adr: 160
title: Rules/MCP Structural Harness Batch and Kiro Adapter Design
status: implemented
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
  - docs/manual-tests/rules-mcp-structural-projection.md
  - docs/architecture/kiro-lifecycle-adapter-design.md
tier: maintainer
tags: [harness, portability, rules, mcp, cline, continue, kilo, zed, augment, goose, aider, kiro]
---

# ADR-160: Rules/MCP Structural Harness Batch and Kiro Adapter Design

## Status

**Implemented for structural projection and Kiro design scope** — 2026-05-05. The seven rules/MCP harness projections and Kiro adapter design artifacts exist and are tested; Kiro native lifecycle runtime remains planned.

## Context

ADR-159 promoted Gemini CLI and several AGENTS.md-native harnesses to structural projection. The next requested slice was Cline, Continue.dev, Kilo Code, Zed AI, Augment/Auggie, Goose, and Aider, plus a Kiro lifecycle adapter design path toward possible future `native-lifecycle`.

The seven new harnesses expose project-local rules, hints, conventions, or config surfaces, but none were account-backed runtime-smoked in this environment.

Kiro exposes lifecycle-like hook events, but COS still lacks an event adapter, generated project config, and runtime smoke.

## Decision

Promote these harnesses to implemented **structural** projection:

- `cline`
- `continue-dev`
- `kilo-code`
- `zed-ai`
- `augment-code`
- `goose`
- `aider`

Generated project-local files:

| Harness | Files |
|---|---|
| Cline | `.clinerules/cognitive-os.md`, `.cline/README.md` |
| Continue.dev | `.continue/rules/cognitive-os.md`, `.continue/mcpServers/cognitive-os.json` |
| Kilo Code | `AGENTS.md`, `.kilocode/rules/cognitive-os.md`, `.kilo/kilo.jsonc` |
| Zed AI | `.rules`, `.zed/settings.json` |
| Augment/Auggie | `.augment/rules/cognitive-os.md`, `.augment/mcp.json`, `.augment/README.md` |
| Goose | `.goosehints` |
| Aider | `CONVENTIONS.md`, `.aider.conf.yml` |

Generated MCP/settings placeholders contain no credentials and grant no tools by default. Kilo stores the MCP placeholder inside `.kilo/kilo.jsonc`; Augment files are intended for explicit `auggie --rules ... --mcp-config ...` invocation; Goose remains `.goosehints` only.

Kiro remains `planned` with `proof_level: none`. The Kiro path is now documented as an adapter design, not an implementation claim.

## Consequences

### Positive

- The ACC projection adapter now covers the next rules/MCP/context batch across default and full profiles.
- Consumer projects can receive project-local guidance for these tools without requiring global IDE settings.
- Kiro lifecycle work has a concrete event-mapping plan before any native-lifecycle promotion.

### Negative

- No account-backed runtime execution was performed for these tools.
- Some vendors may change config paths; structural proof must be refreshed when official docs change.
- Aider remains context-only; it has no COS hook/MCP projection in this slice.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Generate user-global MCP/settings files | Violates project-local projection and can touch credentials or personal IDE state. |
| Promote Cline/Kilo/Factory/Kiro hooks to native-lifecycle immediately | Hook-like docs are not enough without payload mapping and runtime smoke. |
| Skip placeholders entirely | Empty placeholders make boundaries explicit and are easy for ACC to verify. |
| Force all tools through AGENTS.md only | Several tools have more specific project rule/config surfaces that are better structural targets. |

## Verification

```bash
python3 -m py_compile scripts/cos_init.py scripts/acc_pipeline.py
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
python3 -m pytest tests/contracts/test_acc_pipeline_contract.py tests/contracts/test_harness_implementation_phases.py tests/contracts/test_ai_agent_harness_landscape.py -q
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Implementation Evidence

- `scripts/cos_init.py` accepts the seven new harness IDs and writes project-local files only.
- `manifests/harness-projection.yaml` marks the seven new harnesses as implemented structural projection.
- `docs/architecture/kiro-lifecycle-adapter-design.md` records the staged Kiro adapter path.
- Behavior and contract tests assert generated files, ACC projection counts, proof levels, and landscape status.
