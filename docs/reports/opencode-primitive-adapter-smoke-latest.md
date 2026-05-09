# OpenCode Primitive Adapter Smoke — Latest

Generated: 2026-05-09T21:07:37+00:00
Status: `pass`
OpenCode: `1.14.20` at `/opt/homebrew/bin/opencode`
Plugin: `packages/opencode-adapter/plugins/cos-primitive-guard.js`

## Checks

- plugin_loaded: `True`
- blocking_event_threw: `True`
- destructive_git_ledger_row: `True`
- destructive_rm_ledger_row: `True`
- skill_router_ledger_row: `True`
- large_file_advisory_ledger_row: `True`
- content_free_rows: `True`

This smoke invokes the documented OpenCode project-plugin `tool.execute.before` event shape without model calls. It does not run a paid LLM session.
