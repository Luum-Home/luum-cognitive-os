# Consumer Project Primitive Accessibility

> Contract for distinguishing SO-local primitive evidence from primitives that are actually installed or projected into downstream projects.

## Why this exists

A downstream project that implements Cognitive OS does not automatically have access to every document, script, hook, skill, or rule in this repository. A primitive is consumer-accessible only when an install, profile, settings driver, package, or wrapper projects it into that project for a declared harness.

## Current automated proof

The current automated consumer projection proof covers the default install path for implemented native and structural harnesses:

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
```

That behavior test runs `scripts/cos_init.py --default --harness <harness>` inside temporary consumer projects and verifies that each implemented harness receives its declared project-local projection surface. Native lifecycle harnesses (`claude`, `codex`) receive hook/rule/skill projection plus harness settings. Structural harnesses receive instruction/config/context files, MCP placeholders, or Shell/CI command/workflow projection as declared by the harness driver.

The proof currently covers:

- native/settings lifecycle projection: `claude`, `codex`;
- AGENTS/instruction-file structural projection: `agents-md`, `kimi-code`, `warp`, `amp-code`, `qoder`, `goose`, `aider`;
- IDE/config structural projection: `opencode`, `vscode-copilot`, `cursor`, `qwen-code`, `gemini-cli`, `jetbrains-junie`, `factory-droid`, `cline`, `continue-dev`, `kilo-code`, `zed-ai`, `augment-code`;
- shell/CI structural projection: `shell-ci`.

The ACC consumer-projection adapter additionally runs implemented harness/profile checks when `python3 scripts/acc_pipeline.py --project-dir . --refresh` is used. Structural projection proves project-local files are generated; it does not claim runtime enforcement parity or availability of every SO-local primitive.

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

## Explicit availability overrides

`manifests/primitive-consumer-availability.yaml` is the explicit classification layer for lifecycle-declared consumer candidates that are not directly resolved by projection output. It prevents ACC from treating every lifecycle candidate as a consumer-project file.

Allowed statuses:

- `shell-ci-candidate`: intended consumer CLI/shell surface, but still needs shell/CI projection proof.
- `projectable-needs-driver`: intended consumer surface, but no harness/profile driver exists yet.
- `maintainer-only`: SO maintainer primitive; represented and documented, not consumer-project debt.
- `so-local-only`: local helper/context surface; not consumer-project debt.

Only `shell-ci-candidate` and `projectable-needs-driver` should remain partial. `maintainer-only` and `so-local-only` are considered aligned when explicitly declared with rationale.

`shell-ci-candidate` rows are resolved by `manifests/shell-ci-projection.yaml` plus `scripts/project_shell_ci.py`. The shell/CI projection path writes canonical command copies under `.cognitive-os/scripts/cos/`, driver symlinks under `scripts/`, and a workflow at `.github/workflows/cognitive-os-shell-ci.yml`.

## Harness registry

The machine-readable registry is `manifests/harness-projection.yaml`. ACC treats only `status: implemented` harnesses as executable projection proof. Planned harnesses stay visible as `unverified` rather than silently disappearing or being implied by Claude/Codex support.

## Harness support matrix

| Harness / IDE | Current consumer proof | Current safe claim | Next proof needed |
|---|---|---|---|
| Claude Code | Implemented native lifecycle/settings projection. | Default/full profiles project hooks, rules, skills, and `.claude/settings.json` into consumer projects. | Selected runtime parity and candidate promotion proof. |
| OpenAI Codex | Implemented native lifecycle/settings projection. | Default/full profiles project hooks, rules, skills, and `.codex/hooks.json` into consumer projects. | Runtime parity proof beyond file projection for Codex-limited event shapes. |
| Cursor | Implemented structural projection. | Project-local `.cursor/rules/cognitive-os.mdc` and MCP placeholder are generated; no native runtime enforcement claimed. | Native/runtime adapter proof if Cursor lifecycle support is adopted. |
| VS Code Copilot | Implemented structural projection. | Project-local `.github/copilot-instructions.md` and `.vscode/mcp.json` are generated; no runtime enforcement claimed. | Runtime-capable proof only if host support exists. |
| Agents.md-native tools | Implemented structural projection. | Bounded `AGENTS.md` block points agents to projected `.cognitive-os` rules and skills. | Tool-specific native adapter proof where available. |
| OpenCode | Implemented structural projection, with separate signed plugin smoke for a runtime subset. | `opencode.json` is generated; runtime enforcement is limited to primitives covered by the OpenCode adapter smoke. | Expand signed plugin smoke before claiming broader runtime enforcement. |
| Qwen Code | Implemented structural projection. | `QWEN.md` and `.qwen/settings.json` are generated; no native runtime enforcement claimed. | Native runtime proof if Qwen exposes enforceable lifecycle events. |
| Kimi Code | Implemented structural projection. | Bounded `AGENTS.md` block plus `.kimi/mcp.json`/README are generated. | Native runtime proof if available. |
| Gemini CLI | Implemented structural projection. | `GEMINI.md` and `.gemini/settings.json` are generated. | Native runtime proof if available. |
| Warp / Amp / Qoder / Factory Droid / Cline / Continue / Kilo / Zed / Augment / Goose / Aider | Implemented structural projection. | Project-local instruction/config files are generated per harness driver; no runtime enforcement parity is implied. | Harness-specific native/runtime proof. |
| Shell/CI | Implemented structural command/workflow projection. | Declared commands are copied to `.cognitive-os/scripts/cos/`, symlinked from `scripts/`, and wired into `.github/workflows/cognitive-os-shell-ci.yml`. | Behavioral side-effect proof for each projected command under real arguments. |
| Windsurf / Google Antigravity / MiniMax MaxClaw / DeepSeek provider / Kiro | Planned. | Roadmap-only; no consumer availability inherited from implemented harnesses. | Add explicit projection driver and temp-project proof. |

## Acceptance criteria for future claims

A primitive can be described as available to consumer projects only when all are true:

1. The primitive row has lifecycle metadata or explicit package/profile projection metadata.
2. The row declares supported harnesses or has a documented unsupported-harness fallback.
3. A temp consumer project proof installs/projects the primitive or its family.
4. The generated readiness ledger no longer marks the row as SO-local only.
5. Manual documentation names the exact harnesses proved, not all IDEs by default.
