# Harness Proof Levels

Generated: 2026-05-04

## Purpose

Prevent structural projection from being misread as “Cognitive OS works at runtime in every IDE/CLI”. Most external development tools require accounts, local installs, GUI state, or provider-specific credentials that are not available in normal repository CI.

## Levels

| Level | Meaning | What ACC may claim | What ACC must not claim |
|---|---|---|---|
| `structural` | COS generated project-local files/configs from official public docs and tests assert their shape. | The consumer project contains the expected instruction/config/MCP placeholder files. | The target IDE/CLI was installed, authenticated, launched, or successfully executed COS behavior. |
| `host-plugin-lifecycle` | The host exposes plugin/tool lifecycle events that can plausibly enforce COS primitives, but COS has not signed a runtime adapter smoke yet. | The host has an official runtime surface worth targeting with a native adapter. | That COS primitives already executed, blocked, warned, or emitted comparable evidence in that host. |
| `runtime-smoke` | An optional manual or account-backed smoke test ran the target CLI/IDE enough to observe projected context/config. | A dated runtime smoke exists for a specific host/account/tool version. | Universal runtime success across users, versions, OSes, or project stacks. |
| `native-lifecycle` | The harness exposes native lifecycle hooks/events/settings and COS projects them into a temp consumer project. | Native lifecycle projection exists for the tested profile(s). | Full behavioral parity beyond tested events/profiles. |
| `none` | No projection proof exists. | Roadmap/planned only. | Support. |

## Current boundary

`manifests/harness-projection.yaml` is authoritative. `status: implemented` means ACC can execute a projection proof, but the strength of that proof is determined by `proof_level`:

- `native-lifecycle`: Claude Code and Codex.
- `structural`: Cursor, VS Code Copilot, Qwen Code, Kimi Code, Shell/CI, and current OpenCode config projection.
- `host-plugin-lifecycle`: OpenCode plugin/permission surfaces are runtime-capable candidates for a COS adapter, but are not counted as runtime enforcement until smoke-tested.
- `none`: planned/provider/hosted candidates.

## Required language

When discussing structural harnesses, use language like:

- “structural projection implemented”;
- “project-local config/instruction files are generated and tested”;
- “runtime smoke remains optional/account-backed”.

Do not write:

- “the SO works in all IDEs”;
- “runtime support is complete”;
- “Kimi/OpenCode/Cursor/etc. are fully supported”;
- “MCP tools are configured” when only empty placeholders are generated.

## Promotion rules

1. `planned → structural`: requires official docs for project-local config/instructions, installer support, temp-project tests, ADR, and manual test.
2. `structural → host-plugin-lifecycle`: requires official docs for plugin/tool lifecycle events and an adapter design that maps COS primitive events without inventing a parallel host layer.
3. `host-plugin-lifecycle → runtime-smoke`: requires a COS adapter plus dated manual/optional report with tool version, host OS, auth boundary, command/UI path, and result.
4. `runtime-smoke → native-lifecycle`: only possible if the target exposes real lifecycle event hooks/settings comparable to the native contract.
5. Normal CI must not require accounts or GUI installs unless a dedicated optional lane is explicitly selected.
