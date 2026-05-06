# ADR-197: Surface 5 Operable Actions

## Status

Accepted — 2026-05-06

## Context

ADR-195 accepted a read-only Bubble Tea Surface 5 MVP and deferred mutation
until confirmation and receipts were proven. Operators still need a narrow set of
safe local actions from the same surface: refresh coverage, ask `cosd` to process
one batch, and acknowledge directed inbox messages.

## Decision

Add a small CLI-backed Surface 5 action runner behind `cos tui --operate`.

Supported actions are allowlisted:

- `refresh-coverage` — runs `scripts/cos-coverage --json --refresh`.
- `cosd-process-once` — runs `scripts/cosd --json process-once` for the selected
  project root.
- `inbox-ack` — runs `scripts/cos_agent_message.py ack` for an explicit
  `--message-id`.

Every operable action must include `--confirm`. Without confirmation, the command
returns a rejected result and writes no receipt. Confirmed actions append
`.cognitive-os/metrics/tui-actions.jsonl` with `schema_version`, `surface_kind`,
`surface_id`, `mode=operable`, `whitelisted=true`, the command list, and bounded
stdout/stderr tails.

## Consequences

- Surface 5 can perform useful local operator work without becoming an open
  command runner.
- The action path is deterministic enough for CLI and package tests.
- Future interactive keybindings must delegate to the same allowlist/confirm/
  receipt runner instead of bypassing it.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. Unknown `cos tui --operate` actions are rejected.
2. Allowlisted actions without `--confirm` are rejected and write no receipt.
3. Confirmed actions write a `cos-tui-action-receipt.v1` row.
4. `inbox-ack` requires `--message-id`.
5. Tests cover allowlist rejection, confirmation gating, receipt writing, and CLI behavior.
```
