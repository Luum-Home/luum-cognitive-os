# Kiro lifecycle adapter design

## Purpose

Define the work required before Kiro can be considered for Cognitive OS `native-lifecycle` proof.

This document is a design, not an implementation claim. Current Kiro status remains:

- `manifests/harness-projection.yaml`: `status: planned`, `proof_level: none`
- `manifests/ai-agent-harness-landscape.yaml`: `status: lifecycle-investigation`, `proof_level: none`

## Official surface observed

Kiro documentation exposes lifecycle/tool hook events relevant to COS:

| Kiro event | COS candidate |
|---|---|
| `AgentSpawn` | SessionStart / context injection |
| `UserPromptSubmit` | prompt capture, clarification, context diet |
| `PreToolUse` | blockers, policy gates, scope gates |
| `PostToolUse` | validation, metrics, drift detection |
| `Stop` | completion gate, session wrap-up |

Kiro also documents JSON event input on STDIN and exit code `2` blocking behavior for `PreToolUse`.

## Adapter shape

A future adapter should add a small driver layer rather than changing COS hooks directly:

```text
Kiro event JSON
  -> scripts/kiro_hook_adapter.py
  -> normalized COS hook envelope
  -> existing hooks/*.sh or a small hook runner
  -> Kiro-compatible stdout/stderr/exit code
```

## Required files before promotion

| File | Purpose |
|---|---|
| `scripts/kiro_hook_adapter.py` | Translate Kiro event payloads to COS hook envelopes and exit semantics. |
| `scripts/cos_init.py` Kiro driver | Generate project-local Kiro config only after the config path/syntax is signed. |
| `tests/unit/test_kiro_hook_adapter.py` | Contract-test event mapping and exit code behavior without Kiro installed. |
| `tests/behavior/test_consumer_project_projection.py` | Assert generated Kiro files in a temp consumer project. |
| `docs/manual-tests/kiro-lifecycle-runtime-smoke.md` | Optional account-backed smoke path. |

## Promotion gates

Kiro may move from `proof_level: none` to `structural` only when:

1. project-local Kiro config path/syntax is pinned;
2. `cos_init.py --harness kiro` generates that config;
3. behavior tests assert the generated files;
4. no runtime claim is made.

Kiro may move from `structural` to `native-lifecycle` only when:

1. the adapter maps at least SessionStart, PreToolUse, PostToolUse, and Stop;
2. unit tests prove payload translation and blocking semantics;
3. an account-backed Kiro CLI/IDE runtime smoke is recorded;
4. ACC reflects the stronger proof level.

## Non-goals

- Do not rewrite existing COS hooks for Kiro.
- Do not write user-global Kiro configuration.
- Do not claim lifecycle parity from documentation alone.
