# OpenCode Native Primitive Adapter Design

## Status

Draft — adapter design complete, runtime smoke not signed yet.

## Purpose

Close the ADR-256 / ADR-257 OpenCode gap without inventing a parallel COS-only
enforcement layer. OpenCode remains `host-plugin-lifecycle-capable` until this
design is implemented and a dated runtime smoke proves enforcement plus COS
ledger emission.

## Design

```text
primitive contract
  -> capability mapping
  -> OpenCode permission rule
  -> OpenCode plugin tool.execute.before / tool.execute.after
  -> COS primitive-interventions.jsonl receipt
  -> projection fidelity report
```

## Capability mapping

| COS capability | OpenCode surface | Notes |
|---|---|---|
| `inspect_shell_command` | plugin `tool.execute.before` for shell/bash tool input | Read command metadata only; do not persist raw command content in COS ledger. |
| `block_tool_call` | plugin pre-tool return/deny path plus OpenCode permission deny/ask | Blocking is claimable only after smoke proves the host stops the tool. |
| `warn` / `advise` | plugin message/metadata plus COS receipt | Advisory actions must not be labeled enforcement. |
| `emit_metric` | existing COS JSONL helper via plugin bridge | Best-effort; plugin failure must fail closed only for blocking primitives. |
| `emit_intervention` | `.cognitive-os/metrics/primitive-interventions.jsonl` | Required for comparable ADR-256 evidence. |
| read/write inspection | plugin pre/post tool metadata | Must not store file contents, grep patterns, or raw tool output. |

## Adapter artifacts

The future adapter implementation should generate or validate:

- `opencode.json` advisory/profile settings;
- OpenCode permission entries for coarse allow/ask/deny;
- `.opencode/plugins/cos-primitive-guard.*` or equivalent plugin bridge;
- `.cognitive-os/metrics/primitive-interventions.jsonl` rows;
- `docs/reports/opencode-primitive-adapter-smoke-YYYY-MM-DD.md`.

## Runtime smoke acceptance

A signed smoke must include all of the following before any primitive is promoted
from `host-plugin-lifecycle-capable` to enforced in OpenCode:

1. OpenCode version and operating system.
2. Fixture repo path and disposable branch/worktree.
3. Primitive id and source contract.
4. Tool/action attempted.
5. Evidence that OpenCode prevented or allowed the tool as expected.
6. Matching `primitive-interventions.jsonl` row with `session_id`, `tool_use_id`,
   `primitive_id`, `action_kind`, and `reason_code`.
7. Proof that no raw command, file content, grep pattern, or secret was persisted.
8. Rollback path for disabling the plugin/permission projection.

## Non-goals

- Do not claim current OpenCode runtime enforcement from `opencode.json` alone.
- Do not replace OpenCode permissions/plugins with an unrelated COS wrapper before
  trying the native surface.
- Do not store private tool payloads in COS metrics.
- Do not promote all primitives at once; start with `destructive-git-blocker` and
  `destructive-rm-blocker`.

## Current fidelity

Current fidelity remains:

```text
OpenCode: host-plugin-lifecycle-capable
```

Promotion target after smoke:

```text
OpenCode: native-lifecycle-enforced or governed-wrapper-enforced
```

The promotion label depends on whether the final implementation is purely native
OpenCode plugin/permissions or a COS-governed plugin bridge.
