# Hook payload envelope

The **field set** the harness puts on a hook's stdin, per event, captured from
real sessions. `tests/utils/harness_payload.py` builds test payloads from this
file, so a hook test can no longer invent its own two-field payload.

- **File**: `envelope.json` — per event, `{field: value_kind}`; plus
  `tool_input_keys`, the key set each tool's `tool_input` carries; plus
  `observed`, how many payloads of each event the capture saw.
- **Captured by**: `scripts/audit_hook_payload_fidelity.py --capture`
- **Consumed by**: `tests/utils/harness_payload.py`,
  `tests/audit/test_hook_payload_fidelity.py`

## Why this is not "the documentation, retyped"

The capture reconstructs each payload from the harness's own transcripts — the
file the harness wrote while it was running — through the documented projection:
`session_id` = `sessionId`, `cwd` = `cwd`, `tool_name`/`tool_input` = the
assistant `tool_use` block, `tool_response` = the matching `toolUseResult`,
`prompt` = the user message content. 4,354 payloads across three events on the
capture that produced the file in tree.

The manifests are the cross-check, not the source: of the ten events this repo
registers, `manifests/claude-code-hooks-schema.yaml` writes down `stdin_fields`
for exactly two (SubagentStart, TaskCreated). The input contract mostly is not
written down anywhere, which is why it had to be measured.

## What is deliberately not in here

**Keys and kinds are the contract; values are the privacy hazard.** No path, no
username, no project name, no command text, no prompt, no file content ever
reaches this file — `--capture` refuses to write an envelope containing the
home directory, the repo path or `$USER`, and both repo guards pass over the
directory:

```bash
bash scripts/check-local-privacy.sh tests/fixtures/hook-payload-envelope
python3 scripts/check_absolute_paths.py tests/fixtures/hook-payload-envelope
```

The cost of that choice, stated plainly: this fixture gives a test the harness's
**field presence and shape**, not the operator's real command strings. Field
presence is what was actually missing — the ablation in
`docs/06-Daily/reports/payloads-que-el-arnes-manda-2026-08-20.md` shows a hook
verdict flipping on the *presence* of `session_id`, with the command unchanged.
A test that needs real content calls `harness_payload.live_payloads()`, which
rebuilds payloads with real values from the local transcript at test time and
returns `[]` where there is none, so those payloads are never versioned.

## When to re-capture

- After a harness release that changes hook input, or the first session that
  fires an event the envelope has never seen (`fields_sent()` raises
  `UnknownEvent`, which is the signal).
- When `--census --live` and `--census` disagree on the same commit: live
  showing a field the envelope lacks means the harness added one (re-capture);
  live missing one the envelope has means the harness dropped it (fix the hooks
  that read it, then re-capture).

```bash
scripts/audit_hook_payload_fidelity.py --census          # frozen envelope
scripts/audit_hook_payload_fidelity.py --census --live   # this machine now
scripts/audit_hook_payload_fidelity.py --capture         # re-capture
```

The record count moves between machines; what must not move silently is the
field set.
