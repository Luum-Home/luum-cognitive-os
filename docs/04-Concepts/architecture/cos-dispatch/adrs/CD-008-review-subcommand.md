# ADR-008: `cos-dispatch review` as Subcommand in Same Binary

## Status

Accepted — 2026-04-16

## Context

ADR-004 specifies that generated artifacts start with `enabled: false` and require a human to review and enable them. A CLI is needed to list pending artifacts, inspect their source pattern and generated code, and record a feedback decision (`enabled`, `disabled`, `modified`, `deleted`).

`cmd/cos-dispatch/main.go` today reads JSON from stdin and exits — it has no subcommand dispatch. A review UX needs to be added without breaking the existing vendor-harness invocation contract (providers pipe JSON to `cos-dispatch` with no arguments).

## Decision

Refactor `cmd/cos-dispatch/main.go` to support subcommands. With no subcommand, behaviour is unchanged: read stdin, dispatch hooks, exit. A new `review` subcommand handles artifact feedback:

```
cos-dispatch review                       # list pending artifacts
cos-dispatch review --enable <name>       # feedback: enabled
cos-dispatch review --disable <name>      # feedback: disabled
cos-dispatch review --show <name>         # print generated code + source pattern
```

All new flags are namespaced under the subcommand, leaving the bare invocation untouched.

## Alternatives Considered

1. **Separate `cmd/cos-dispatch-review/` binary** — two artifacts to distribute, two places to keep config/DB path logic in sync, and duplicated log/metrics setup. Rejected: the maintenance tax outweighs the clarity benefit.
2. **REPL** — interactive shell for browsing artifacts. Rejected: CI and scripted workflows need non-interactive flags; a REPL can be layered on later if demand emerges.
3. **HTTP API** — service endpoint for a future web UI. Rejected: out of scope for Phase 5; premature given there is no consumer.

## Consequences

- One-time refactor during Phase 5.3: introduce subcommand dispatch, move current behaviour into a default path.
- Vendor integrations that invoke `cos-dispatch` with no args continue to work unchanged.
- The feedback loop from ADR-004 gains its concrete CLI surface. ADR-006's `override` signal and the review feedback column close the learning loop for the generator (see ADR-009 for scope limits).
- Adding future subcommands (`cos-dispatch stats`, `cos-dispatch doctor`) follows the same pattern with no further refactor.
