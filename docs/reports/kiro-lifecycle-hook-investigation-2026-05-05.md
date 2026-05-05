# Kiro lifecycle-hook investigation — 2026-05-05

## Finding

Kiro is a legitimate lifecycle-hook investigation candidate, but not yet an implemented COS harness.

Official documentation signs several surfaces relevant to COS:

- project workflows with steering files, hooks, and MCP;
- CLI invocation from a project directory via `kiro .`;
- hook events for agent and tool lifecycle: `AgentSpawn`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`;
- JSON hook event payloads delivered on STDIN;
- exit code `2` blocking behavior for `PreToolUse`;
- MCP tool matching.

## Boundary

This is stronger than a simple AGENTS.md/rules projection surface, but it is still not enough to claim native lifecycle parity for COS.

Missing proof before promotion:

1. exact project-local agent configuration path and syntax for generated hook registration;
2. deterministic mapping from Kiro hook event payloads to COS hook input expectations;
3. adapter/wrapper scripts for at least SessionStart, PreToolUse, PostToolUse, and Stop;
4. temp-project structural tests for generated Kiro config;
5. optional account-backed Kiro CLI/IDE runtime smoke.

## Decision

Keep `kiro` as:

- `manifests/harness-projection.yaml`: `status: planned`, `proof_level: none`;
- `manifests/ai-agent-harness-landscape.yaml`: `status: lifecycle-investigation`, `proof_level: none`.

Factory Droid also exposes hook events, but this slice only implements Factory structural project files. Factory hook parity needs the same adapter-and-smoke discipline before promotion.

## Next adapter sketch

| COS event | Candidate Kiro event | Notes |
|---|---|---|
| SessionStart | `AgentSpawn` | Need context-injection behavior and event casing confirmation. |
| UserPromptSubmit | `UserPromptSubmit` | Candidate for prompt-capture/context gates. |
| PreToolUse | `PreToolUse` | Candidate for blockers; exit code 2 semantics are promising. |
| PostToolUse | `PostToolUse` | Candidate for result validation/metrics. |
| Stop | `Stop` | Candidate for completion/session wrap-up. |

No adapter should be generated until the config path is signed and tests can assert event mapping.
