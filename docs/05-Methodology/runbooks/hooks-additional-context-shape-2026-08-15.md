# Runbook — fix the `additionalContext` output shape and the injector's `async`

**Date**: 2026-08-15
**Why a runbook**: `hooks/**` is write-protected for agents. The diagnosis, the
contract and the tests landed directly; the hook edits and the one
`.claude/settings.json` edit need an operator.
**Contract**: `manifests/claude-code-hooks-schema.yaml`
**Report**: `docs/06-Daily/reports/contrato-salida-hooks-2026-08-15.md`

---

## What is broken

Two independent defects, both silent.

**1. Wrong shape (2 hooks).** Claude Code reads `additionalContext` only from
inside `hookSpecificOutput`, alongside `hookEventName`. There is no top-level
form. A hook printing `{"additionalContext": "..."}` at the root emits valid
JSON, so the host parses it, finds no recognized field, and discards it. There
is no fallback to plain text either: stdout starting with `{` that parses as
valid JSON is never re-read as prose. No error, no warning, no context.

**2. `async: true` on the injector (1 registration).** `hooks/subagent-context-injector.sh`
emits the correct shape on the correct event, and still delivers nothing,
because `.claude/settings.json` registers it with `"async": true`. Async hooks
run in the background; their output is delivered "on the next conversation
turn", while `SubagentStart`'s `additionalContext` must land "at the start of
the conversation, before its first prompt". Those cannot both hold.

Plus one incomplete object found in passing: `hooks/eas-validation-gate.sh`
nests correctly but omits the required `hookEventName`.

Measured impact, reproducible:

```bash
python3 scripts/check_subagent_context_arrival.py
# transcripts      : 149
# genuine arrivals : 0
# exit 1
```

---

## Step 1 — apply the hook patch

```bash
cd <repo>
git apply --check docs/05-Methodology/runbooks/patches/hooks-additional-context-shape-2026-08-15.patch
git apply           docs/05-Methodology/runbooks/patches/hooks-additional-context-shape-2026-08-15.patch
```

Touches three files, output shape only — no logic, no control flow:

| File | Change |
|---|---|
| `hooks/cross-session-peer-context.sh` | root `additionalContext` → nested, `hookEventName: "UserPromptSubmit"` |
| `hooks/agent-message-inbox-context.sh` | same |
| `hooks/eas-validation-gate.sh` | add missing `hookEventName: "Stop"` |

Verify each still emits parseable JSON:

```bash
echo '{}' | bash hooks/cross-session-peer-context.sh   | python3 -m json.tool
echo '{}' | bash hooks/agent-message-inbox-context.sh  | python3 -m json.tool
```

Empty output is fine — both exit 0 early when there is nothing to report.

## Step 2 — drop `async` from the SubagentStart registration

**This is the one that fixes the 0/149.** Not in the patch, because
`.claude/settings.json` is machine-managed and may be regenerated; edit it in
whatever way this repo considers authoritative.

In `.claude/settings.json`, under `hooks.SubagentStart`, on the
`subagent-context-injector.sh` handler:

```diff
   {
     "type": "command",
     "command": ".../hooks/subagent-context-injector.sh",
-    "async": true
   }
```

Removing the key restores the default (`false` = blocking), which is what the
hook's own header has claimed all along (`# Async: false (completes before
subagent starts)`).

**Before removing it, check the cost.** Blocking means every `Agent` launch
waits for this hook. Measure it:

```bash
time (echo '{"prompt":"x","hook_event_name":"SubagentStart"}' \
      | CLAUDE_PROJECT_DIR=$PWD bash hooks/subagent-context-injector.sh >/dev/null)
```

The existing test asserts under 3 seconds
(`test_completes_under_3_seconds`). If it is near that ceiling, the fix is to
make the hook faster, not to put `async` back — async is the setting that
guarantees the context never arrives.

## Step 3 — reconcile the two `# Async:` headers

Both hooks disagree with their own registration:

- `hooks/subagent-context-injector.sh` — header says `false`, registered `true`.
  Step 2 makes the header true; no edit needed.
- `hooks/skill-md-routing-validator.sh:12` — header says `true`, registered
  with no `async` key (so `false`). Either correct the header to `false` or
  add `"async": true` to its registration. It is a `PreToolUse` validator that
  the header says "NEVER blocks writes", so the header is probably describing
  intent that the registration never implemented — decide which is right, then
  make them agree.

## Step 4 — empty the baselines

The conformance test carries four exact-match baselines. After Steps 1-3 they
must be **emptied, not adjusted** — a baseline above reality is slack that a
future regression lands in for free.

In `tests/contracts/test_claude_code_hooks_schema_conformance.py`:

- `KNOWN_ROOT_LEVEL_VIOLATIONS` → `set()`
- `KNOWN_MISSING_HOOK_EVENT_NAME` → `set()`
- `KNOWN_ASYNC_ON_CONTEXT_EMITTER` → `set()`
- `KNOWN_ASYNC_HEADER_MISMATCHES` → `set()`

Each has a `stale` assertion that fails if an entry is fixed but still listed,
so the test tells you which to remove.

## Step 5 — verify

```bash
python3 -m pytest tests/contracts/test_claude_code_hooks_schema_conformance.py \
                  tests/hooks/test_subagent_context_injector.py -q
```

Then, **after launching at least one new sub-agent** (the check reads real
transcripts, so it cannot confirm a fix that has not run yet):

```bash
python3 scripts/check_subagent_context_arrival.py -v
# expect: genuine arrivals >= 1, exit 0
```

## Rollback

```bash
git apply -R docs/05-Methodology/runbooks/patches/hooks-additional-context-shape-2026-08-15.patch
```

and restore `"async": true` in `.claude/settings.json`. Rolling back returns to
the state where sub-agents receive no injected rules — it is a rollback of a
fix, not of a risk.

---

## What was ruled out, so nobody re-runs it

Recorded because the discarded readings cost most of the investigation.

- **"The native channel is dead."** False. `rules/RULES-COMPACT.md` reaches
  sub-agents (83 of 147 transcripts mention it). The channel works; this
  specific payload does not travel on it.
- **"The hook emits nothing / exits early."** False. It emits 10,253 bytes,
  correctly nested, containing the full template. Emission was never the
  problem, which is why 18 emission tests could pass against 0 arrivals.
- **"The two shapes might both be valid."** False, and this was the reading
  worth killing: the docs are unambiguous that `additionalContext` goes inside
  `hookSpecificOutput`. Had it been ambiguous, the correct move was to change
  nothing.
- **"`docs.claude.com` 301s to `code.claude.com`."** Only for some prefixes.
  `code.claude.com/docs/en/sdk/sdk-typescript` 301s the *other* way, to
  `docs.claude.com`. Neither host is canonical for everything. Use the `.md`
  suffix on `code.claude.com` — it returns full source instead of a truncated
  page.
- **"Fetch the docs with a summarizing fetch."** Wasted three passes. The HTML
  page truncates before the section that answers the question, and each pass
  confidently reported the answer was "not in the provided content". `curl` the
  `.md` and grep it.
