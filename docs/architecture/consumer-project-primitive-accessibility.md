# Consumer Project Primitive Accessibility

> Contract for distinguishing SO-local primitive evidence from primitives that are actually installed or projected into downstream projects.

## Why this exists

A downstream project that implements Cognitive OS does not automatically have access to every document, script, hook, skill, or rule in this repository. A primitive is consumer-accessible only when an install, profile, settings driver, package, or wrapper projects it into that project for a declared harness.

## Current automated proof

The current automated consumer projection proof covers the default install path for Claude Code and OpenAI Codex:

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
```

That behavior test runs `scripts/cos_init.py --default --harness claude` and `scripts/cos_init.py --default --harness codex` inside temporary consumer projects and verifies that the project receives:

- `.cognitive-os/install-meta.json`
- harness settings (`.claude/settings.json` or `.codex/hooks.json`)
- projected hooks under `.cognitive-os/hooks/cos/`
- projected rules under `.cognitive-os/rules/cos/`
- projected skills under `.cognitive-os/skills/cos/`

The ACC consumer-projection adapter additionally runs both `--default` and `--full` for implemented harnesses when `python3 scripts/acc_pipeline.py --project-dir . --refresh` is used. This proves projected hooks/rules/skills for Claude Code and OpenAI Codex across those two profiles. It does not prove third-party IDE native integration or availability of every SO-local primitive.

## Current ledger evidence

Regenerate all family ledgers:

```bash
python3 scripts/primitive_readiness_ledger.py --project-dir . --fail-low-confidence
for family in hooks skills rules; do
  python3 scripts/primitive_family_readiness_ledger.py --project-dir . --target-family "$family"
done
```

Generated reports:

- `docs/reports/primitive-readiness-ledger-scripts-latest.json`
- `docs/reports/primitive-readiness-ledger-hooks-latest.json`
- `docs/reports/primitive-readiness-ledger-skills-latest.json`
- `docs/reports/primitive-readiness-ledger-rules-latest.json`

Each row includes `consumer_accessibility` and `consumer_access_next_action`. Treat `so-local-only`, `repo-skill-not-projectable`, and `skill-referenced-not-projectable` as not available to consumer projects until an install/profile/package path proves otherwise.

## Harness registry

The machine-readable registry is `manifests/harness-projection.yaml`. ACC treats only `status: implemented` harnesses as executable projection proof. Planned harnesses stay visible as `unverified` rather than silently disappearing or being implied by Claude/Codex support.

## Harness support matrix

| Harness / IDE | Current consumer proof | Current safe claim | Next proof needed |
|---|---|---|---|
| Claude Code | Automated default/full install projection proof passes in ACC. | Default and full profiles project hooks, rules, and skills into consumer projects. | Selected lifecycle candidate promotion proof. |
| OpenAI Codex | Automated default/full install projection proof passes in ACC. | Default and full profiles project Codex settings plus COS hooks/rules/skills into consumer projects. | Codex runtime parity proof beyond file projection. |
| Cursor | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native consumer projection. | Define Cursor settings/rules/MCP projection driver and temp-project proof. |
| Windsurf | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native consumer projection. | Define Windsurf settings/rules/MCP projection driver and temp-project proof. |
| VS Code Copilot | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native consumer projection. | Define instruction/task/MCP projection surface and temp-project proof. |
| Google Antigravity | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native consumer projection. | Audit supported config/tool format and add projection proof. |
| OpenCode | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native consumer projection. | Define wrapper or native config projection and temp-project proof. |
| Qwen Code | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native consumer projection. | Define Qwen Code settings/skills/hooks/MCP projection and temp-project proof. |
| Kimi Code | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native consumer projection. | Research local config surface, then add projection proof. |
| MiniMax MaxClaw / MiniMax Agent | Declared in `manifests/harness-projection.yaml` as `planned`. | Not signed as native local projection; may be hosted-agent/provider surface instead. | Decide harness-vs-provider boundary before implementation. |
| DeepSeek provider integrations | Declared in `manifests/harness-projection.yaml` as `planned`. | Track as provider compatibility, not first-party IDE support. | Promote only if a first-party coding harness/project config is identified. |
| Shell/CI | CLI scripts are available in the SO repo; consumer projection depends on install/profile. | Use deterministic CLI entrypoints only when project install path exposes them. | Add temp-project shell/CI projection test. |

## Acceptance criteria for future claims

A primitive can be described as available to consumer projects only when all are true:

1. The primitive row has lifecycle metadata or explicit package/profile projection metadata.
2. The row declares supported harnesses or has a documented unsupported-harness fallback.
3. A temp consumer project proof installs/projects the primitive or its family.
4. The generated readiness ledger no longer marks the row as SO-local only.
5. Manual documentation names the exact harnesses proved, not all IDEs by default.
