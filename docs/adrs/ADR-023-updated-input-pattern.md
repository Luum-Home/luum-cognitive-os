---
adr: 23
title: Mutate, Don't Block — `updatedInput` for PreToolUse Hooks
status: accepted
implementation_status: not-applicable
date: '2026-04-15'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted decision/policy record with no explicit implementation
  surface
---

# ADR-023: Mutate, Don't Block — `updatedInput` for PreToolUse Hooks

**Date:** 2026-04-15
**Status:** Accepted
**Supersedes:** None
**Related:** ADR-010 (Hook Architecture v2), ADR-013 (Security Stack), ADR-022 (Prompt-Type Hooks Adoption)

## Context

Several PreToolUse hooks in the Cognitive OS interrupt agent execution
with a hard block (`exit 2`) the moment they observe a single suspect
token in the tool input. The two canonical examples:

1. **`secret-detector.sh`** historically ran *after* a write
   (PostToolUse on `Edit|Write`) and only emitted a stderr WARNING about
   missing env-var definitions. There was no PreToolUse path at all, so
   when an agent pasted a literal AWS key into a `Bash` command the
   credential was silently echoed into shell history before any hook saw
   it. The natural fix was a PreToolUse block — which immediately broke
   the workflow with `BLOCKED: secret detected` and forced the agent to
   restart from scratch.
2. **`blast-radius.sh`** writes a multi-paragraph `=== BLAST RADIUS ===`
   banner to stdout/stderr whenever it sees broad-scope keywords. The
   banner is advisory — the hook always exits 0 — but the formatting
   makes it look like a tool error in the transcript and the orchestrator
   has no structured way to surface the warning to the user.

Claude Code 2.x added a richer PreToolUse return contract:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": { ...modified tool_input... }
  },
  "additionalContext": "human-readable warning"
}
```

`updatedInput` lets the hook **mutate** the tool input before the tool
runs. `additionalContext` lets the hook attach a structured advisory
message that the orchestrator can render distinctly from regular tool
output. Together they enable a much better UX than `exit 2`:

- Secrets are **redacted in place** — the agent's intent (`aws s3 ls`,
  `curl https://api.github.com/user`) is preserved, only the literal
  credential is replaced with `[REDACTED]`. The agent does not have to
  retry; the call proceeds with a safe payload.
- Advisory hooks emit a structured `additionalContext` string that the
  orchestrator can fold into the next system reminder, rather than
  cluttering the transcript with banner art that looks like an error.

## Decision

**For PreToolUse hooks where the *correct* response is "let this
proceed, but adjust the payload or warn the operator", we MUST emit
`hookSpecificOutput.updatedInput` and/or `additionalContext` instead of
returning a non-zero exit code.**

Concretely:

1. **`secret-detector.sh`** becomes a dual-mode hook:
   - When invoked as PreToolUse on `Bash | Edit | Write | MultiEdit`, it
     scans `tool_input.command`, `tool_input.content`, and
     `tool_input.new_string` for high-confidence credential patterns
     (`AKIA…`, `ASIA…`, `ghp_…`, `gho_…`, `ghu_…`, `ghs_…`, `ghr_…`,
     `xox[abprs]-…`, `sk_live_…`, `sk-…`). Every match is replaced with
     `[REDACTED]`; the redacted input is emitted as `updatedInput`;
     `additionalContext` lists which credential prefixes were redacted
     (first 8 chars only) and tells the agent to switch to environment
     variables.
   - When invoked as PostToolUse on `Edit | Write`, the legacy
     env-var-definition scan runs unchanged (logs to
     `.cognitive-os/metrics/missing-secrets.jsonl`).
   - Mode is dispatched on the `hook_event_name` field that Claude Code
     puts in the stdin payload. Absent that field, the hook defaults to
     PostToolUse for backward compatibility.

2. **Blocking is reserved as a fallback**, not the default. The hook
   only returns `exit 2` when redaction would leave the command
   meaningless — e.g. the entire `tool_input.command` is one secret with
   no surrounding shell. In that case, blocking is the right answer
   because letting `[REDACTED]` execute would be more confusing than
   refusing.

3. **`blast-radius.sh`** stops printing banner art and emits a single
   JSON object with `permissionDecision: "allow"` and the warning text
   in `additionalContext`. The internal classification logic
   (HIGH/CRITICAL thresholds, infra/security keyword detection, signal
   collection) is unchanged. The metrics log still receives one entry
   per call.

4. **Auditability is preserved.** Every redaction is appended to
   `.cognitive-os/metrics/secret-redactions.jsonl` with timestamp, tool,
   and detected-prefix list. Operators can grep this file to see which
   secrets were caught; the literal credential is never written to
   disk.

5. **Both hooks are registered in `apply-efficiency-profile.sh` AND
   `set-security-profile.sh`** so the pre-commit gate that requires
   parity between the two profile scripts stays green.

## Why mutation over blocking

| Concern | `exit 2` block | `updatedInput` redact |
|---|---|---|
| Agent retry cost | Full retry, often re-derives the same secret | None — the call proceeds |
| Operator surprise | "Why did this fail again?" | "Secret was redacted, command ran" |
| Audit trail | Stderr line lost in log noise | Structured JSONL entry |
| Developer ergonomics | Hard to debug — no payload to inspect | `updatedInput` shows exactly what ran |
| Defense depth | Same — secret is still kept off the wire | Same — secret is still kept off the wire |

Mutation gives us all the safety of blocking without the workflow
disruption. The only loss is "the agent learned not to paste secrets",
but that lesson is delivered just as effectively by the
`additionalContext` message.

## When to still block

- Redaction would yield an empty / structurally meaningless payload
  (the entire command IS the secret).
- The secret is *also* a destructive action — e.g. a `rm -rf` paired
  with a real key. In that case a separate destructive-command hook
  should block on the destructive intent, independently of secret
  detection.
- The secret pattern matched is one we cannot safely redact in place
  (rare — only relevant if the surrounding syntax depends on the
  secret's exact length, which is not the case for any pattern in our
  current list).

## Consequences

**Positive:**
- Agent flow is no longer interrupted when a literal credential slips
  in. The agent learns from `additionalContext` and naturally moves to
  env-var references.
- Secrets are caught one step *earlier* (PreToolUse) rather than after
  the file has been written.
- Blast-radius warnings are now machine-readable, which lets the
  orchestrator surface them in a dedicated UI element.

**Negative / risks:**
- We rely on Claude Code honoring `permissionDecision: "allow"` plus
  `updatedInput`. If a future version of Claude Code changes the
  contract, both hooks need to be updated. Mitigation: behavioral tests
  in `tests/unit/test_secret_detector_updated_input.py` and
  `tests/unit/test_blast_radius_additional_context.py` lock the
  contract from our side.
- Pattern coverage is finite. Mitigation: the pattern list is centralized
  in one bash array (`SECRET_PATTERNS`) so adding a new vendor takes one
  line.

## References

- `hooks/secret-detector.sh`
- `hooks/blast-radius.sh`
- `tests/unit/test_secret_detector_updated_input.py`
- `tests/unit/test_blast_radius_additional_context.py`
- `scripts/apply-efficiency-profile.sh`
- `scripts/set-security-profile.sh`
- ADR-010, ADR-013, ADR-022
