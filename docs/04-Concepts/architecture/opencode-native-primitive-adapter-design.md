# OpenCode Native Primitive Adapter Design

## Status

Implemented for OpenCode's native plugin/config surface, with scoped runtime proof:

- lifecycle and prompt events are projected by `scripts/_lib/settings-driver-opencode.sh` into `.opencode/cos-hooks.json` and executed by `packages/opencode-adapter/plugins/cos-primitive-guard.js`;
- tool gating still promotes only the signed smoke slice of registry-backed primitives through `tool.execute.before` / `tool.execute.after`;
- `lib/harness_adapter/opencode.py` normalizes OpenCode/plugin payloads for post-hoc COS event capture;
- remaining registry-backed primitives stay `structural-advisory` for OpenCode until their own runtime smoke is signed.

## Purpose

Close the ADR-256 / ADR-257 OpenCode gap without inventing a parallel COS-only enforcement layer. COS remains the authority for canonical agentic primitives; OpenCode receives a harness-specific projection through native project config and plugins. The smoke is model-free and verifies plugin load, lifecycle hook projection, blocking behavior, and COS ledger emission.

## Design

```text
canonical primitive contract
  -> harness capability mapping
  -> settings-driver-opencode.sh
  -> opencode.json + .opencode/cos-hooks.json + .opencode/plugins/cos-primitive-guard.js
  -> OpenCode plugin events
  -> COS primitive-interventions.jsonl receipt
  -> lib/harness_adapter/opencode.py post-hoc normalization
  -> projection fidelity report
```

## Capability mapping

| COS capability | OpenCode surface | Notes |
|---|---|---|
| `SessionStart` | plugin `session.created` | Executes projected SessionStart hooks from `.opencode/cos-hooks.json`. |
| `UserPromptSubmit` | plugin `tui.prompt.append` | Executes prompt gates without persisting private prompt text in COS rows. |
| `PreToolUse` | plugin `tool.execute.before` for shell/bash tool input | Read command metadata only; do not persist raw command content in COS ledger. |
| `PostToolUse` | plugin `tool.execute.after` | Emits post-tool receipts and keeps post-hoc adapter parity. |
| `Stop` | plugin `session.idle` | Executes projected Stop hooks. |
| `PreCompact` | plugin `session.compacted`; legacy `experimental.session.compacting` accepted | Kept limited until OpenCode compaction semantics are stable across builds. |
| `block_tool_call` | plugin pre-tool return/deny path plus OpenCode permission deny/ask | Blocking is claimable only after smoke proves the host stops the tool. |
| `warn` / `advise` | plugin message/metadata plus COS receipt | Advisory actions must not be labeled enforcement. |
| `emit_metric` | existing COS JSONL helper via plugin bridge | Best-effort; plugin failure must fail closed only for blocking primitives. |
| `emit_intervention` | `.cognitive-os/metrics/primitive-interventions.jsonl` | Required for comparable ADR-256 evidence. |
| read/write inspection | plugin pre/post tool metadata | Must not store file contents, grep patterns, or raw tool output. |

## Adapter artifacts

The OpenCode adapter now generates or validates:

- `opencode.json` advisory/profile settings with the project plugin configured;
- `.opencode/cos-hooks.json` native-event projection generated from `cognitive-os.yaml`;
- OpenCode permission entries for coarse allow/ask/deny;
- `packages/opencode-adapter/plugins/cos-primitive-guard.js` as the canonical plugin source;
- `.opencode/plugins/cos-primitive-guard.js` projected into OpenCode consumer installs;
- `lib/harness_adapter/opencode.py` for OpenCode payload normalization in `lib/harness_adapter/dispatch.py`;
- `.cognitive-os/metrics/primitive-interventions.jsonl` rows;
- `docs/06-Daily/reports/opencode-primitive-adapter-smoke-latest.md`.

## Runtime smoke acceptance

A signed smoke must include all of the following before any primitive is promoted from advisory/plugin-capable design to enforced in OpenCode. The current signed tool-gating slice satisfies this for the signed plugin primitives such as `destructive-git-blocker`, `destructive-rm-blocker`, `large-file-advisor`, and `skill-router`; lifecycle projection is separately proven by smoke rows for `session.created`, `tui.prompt.append`, `session.idle`, and `session.compacted`.

1. OpenCode version and operating system.
2. Fixture repo path and disposable branch/worktree.
3. Primitive id and source contract.
4. Tool/action or lifecycle event attempted.
5. Evidence that OpenCode prevented, allowed, or projected the event as expected.
6. Matching `primitive-interventions.jsonl` row with `session_id`, `tool_use_id` or native event reference, `primitive_id`, `action_kind`, and `reason_code`.
7. Proof that no raw command, file content, grep pattern, prompt text, or secret was persisted.
8. Rollback path for disabling the plugin/permission/hook projection.

## Non-goals

- Do not claim OpenCode runtime enforcement from `opencode.json` alone.
- Do not replace OpenCode permissions/plugins with an unrelated COS wrapper before using the native surface.
- Do not store private tool payloads or prompt contents in COS metrics.
- Do not promote all primitives at once; promote only the signed smoke slice.
- Do not mark `SubagentStart` as fully equivalent: OpenCode uses task permissions instead of the Claude Code lifecycle event.
- Do not mark `PreCompact` as fully stable until the OpenCode event shape remains consistent across supported builds.

## Current fidelity

Current fidelity is split:

```text
OpenCode lifecycle/prompt/tool projection: native-driver-projected
OpenCode signed tool runtime slice: governed-wrapper-enforced
OpenCode remaining primitives: structural-advisory until signed runtime smoke
```

The signed runtime slice is `governed-wrapper-enforced` because COS owns the plugin bridge while OpenCode supplies the native project-plugin event surface. Do not promote additional primitives until their plugin behavior and ledger rows are covered by smoke evidence.

## Current sources checked

- [OpenCode Plugins](https://opencode.ai/docs/plugins/) documents project-level `.opencode/plugins/` loading and plugin events including `session.created`, `session.idle`, `session.compacted`, `tool.execute.before`, `tool.execute.after`, and `tui.prompt.append`; it also documents the `experimental.session.compacting` compaction hook example.
- [OpenCode Permissions](https://opencode.ai/docs/permissions/) documents `permission` actions `allow`, `ask`, and `deny`.
