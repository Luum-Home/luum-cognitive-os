# Phase 5.4 — Cursor/Devin Provider Hardening + Dispatch Flags

## What Changed

### 1. Cursor provider (`internal/provider/cursor.go`)

**Vendor signal**: `CURSOR_SESSION_ID` (primary) or `CURSOR_PROJECT_DIR` (secondary);
`.cursor/` directory in CWD as last-resort heuristic.

**Event mapping**: camelCase (`beforeShellExecution` → `before_tool`,
`afterFileEdit` / `afterFileWrite` / `afterShellExecution` → `after_tool`).

**Response envelope**: `{"action":"allow"|"deny","message":"..."}` — Cursor hooks
do NOT use `hookSpecificOutput`. This is a vendor-conformant divergence from the
Claude/Codex/Gemini format.

**Extra field**: `model_id` from the payload is preserved in `Context.Metadata`
under `"cursor_model_id"` for downstream validators.

**ProjectDir**: populated from `CURSOR_PROJECT_DIR`; falls back to
`CLAUDE_PROJECT_DIR` for sessions where both runtimes are active.

### 2. Devin provider (`internal/provider/devin.go`)

**Vendor signal**: `DEVIN_SESSION_ID` (primary) or `CASCADE_CONTEXT` (secondary).

**Event mapping**: `PreCascadeAction` / `PreToolUse` → `before_tool`;
`PostCascadeAction` / `PostToolUse` → `after_tool`.

**Response envelope**: `{"cascadeDecision":"allow"|"deny","reason":"..."}` — Devin
Cascade uses `cascadeDecision` not `permissionDecision`.

**Cascade context**: The `cascade_context` object from the payload (containing
`workspace` and `active_file`) is preserved in `Context.Metadata` under
`"cascade_workspace"` and `"cascade_active_file"`.

**ProjectDir**: populated from `DEVIN_PROJECT_DIR` (env var, highest priority),
falling back to `cascade_context.workspace` when available.

### 3. Validator Registry (`internal/validator/registry.go`)

Added exported `Registration` struct and `Registrations() []Registration` method so
`dispatch.go` can iterate over registered validators for the `--disable` filter
without importing internal details.

### 4. `--dry-run` flag (`cmd/cos-dispatch/dispatch.go`)

When `--dry-run` is set:
- The full dispatch pipeline runs normally (validators execute, tracker records).
- If the response contains a deny decision, it is replaced with an allow response.
- The replacement response includes `"dryRun":true` and `"dryRunDeniedReason"` for
  observability.
- Handles all three vendor envelopes: `permissionDecision` (Claude/Codex/Gemini),
  `action` (Cursor), `cascadeDecision` (Devin).
- Exit code is always 0 when `--dry-run` is active.

### 5. `--disable NAME1,NAME2` flag (`cmd/cos-dispatch/dispatch.go`)

When `--disable` is set:
- The comma-separated list is parsed by `parseDisabledNames`.
- A filtered `validator.Registry` is constructed via `filterValidators`, which
  removes the named validators and logs each skip.
- The dispatcher receives the filtered registry; disabled validators are not
  executed and do not appear in the tracker.

## Test Artifacts

- `internal/provider/testdata/providers/` — fixture JSON payloads and golden
  response files for Cursor and Devin.
- `internal/provider/cursor_test.go` — unit tests for Detect, Parse, BuildResponse.
- `internal/provider/devin_test.go` — unit tests for Detect, Parse, BuildResponse.
- `cmd/cos-dispatch/dispatch_test.go` — integration tests for `--dry-run` and
  `--disable` (including CSV parsing, multi-envelope coverage, full dispatch path).

## Decisions

- **Cursor/Devin use different response envelopes** than Claude/Codex/Gemini.
  This is the correct ADR-005 interpretation: vendor quirks are handled per-adapter.
  The pre-existing `TestAllProviders_BuildResponse_Format` test was wrong for these
  two providers and has been replaced with per-provider assertions.
- **`containsDeny` was extended** to detect deny decisions across all three envelopes
  so `--dry-run` works regardless of which provider is active.
- **No dispatcher.go changes** were required. Both flags are handled entirely in
  `dispatch.go` at the composition layer. The dispatcher remains unaware of
  dry-run and per-request disable semantics.
