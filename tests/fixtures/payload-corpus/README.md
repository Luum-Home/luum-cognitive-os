# Harness payload corpus

Frozen *shape* of the tool-result payloads the harness sends, so the payload
canary can run as a deterministic test instead of only on the machine that
happens to have transcripts.

- **File**: `harness-payloads.jsonl` — one record per (tool, result state, key
  shape), transcript-shaped so the canary reads it through the exact same code
  path as live transcripts.
- **Captured by**: `scripts/capture_payload_corpus.py`
- **Consumed by**: `scripts/audit_payload_field_contracts.py --canary` (default
  source) and `tests/audit/test_payload_field_contracts.py`

## What is in a record, and what is deliberately not

```json
{"_corpus": {"tool": "Bash", "state": "object", "event": "PostToolUse", "seen": 1441},
 "toolUseResult": {"interrupted": false, "stdout": "<str>", ...}}
```

Keys and types are the payload contract; **values are the privacy hazard**.
Every scalar is replaced by a token (`<str>`, `0`, `0.0`); booleans survive
because a boolean is shape; keys that are not plain identifiers become `<key>`,
because a key can smuggle a value (`answers` is keyed by the operator's own
question text). The corpus therefore carries no paths, no usernames, no project
names, no file content.

Both privacy guards are expected to pass over this directory:

```bash
bash scripts/check-local-privacy.sh tests/fixtures/payload-corpus
python3 scripts/check_absolute_paths.py tests/fixtures/payload-corpus
```

## The corpus comes from what the harness sent, not from what hooks read

A corpus assembled out of the fields hooks already read would agree with the
hooks by construction and could never fail. This one is grouped by every key of
every observed `toolUseResult`: 71 keys, of which 67 are read by no hook at all.
`test_corpus_is_harness_derived_not_hook_derived` guards that surplus.

## When to re-capture

The corpus ages; the live mode is what notices. Re-run the capture when:

- **The harness version changes** (a release that touches tool results), or a
  new tool/MCP server starts being used regularly — new payload shapes exist
  that the corpus has never seen.
- **`--canary --live` disagrees with `--canary`** on the same commit. Live
  finding *more* phantom fields than the corpus means the harness dropped a
  field the corpus still remembers: fix the hook, then re-capture. Live finding
  *fewer* means the harness added a field: re-capture, and the ratchet in
  `tests/audit/test_payload_field_contracts.py` goes down.
- **A phantom dependency is fixed** — re-capture is not needed, but the ratchet
  set must shrink in the same commit.

Drift check, and the command whose disagreement is the trigger:

```bash
scripts/audit_payload_field_contracts.py --canary        # in-repo corpus
scripts/audit_payload_field_contracts.py --canary --live # this machine's transcripts
scripts/capture_payload_corpus.py                        # re-capture
```

Re-capture is deterministic per input set, but the input set is per-machine:
expect the record count to move when captured somewhere else. What must not
move silently is the phantom ratchet.
