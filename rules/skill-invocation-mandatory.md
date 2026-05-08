<!-- SCOPE: both -->
<!-- TIER: 0 -->
# Skill Invocation Mandatory at High Router Confidence (ADR-188)

## Mandate

High-confidence skill-router matches are mandatory orchestration contracts, not optional hints. When the router is at or above the ADR-188 threshold, the orchestrator must invoke the matching skill, invoke a strictly stronger skill, or emit an auditable bypass reason before launching bespoke work.

## Threshold

When `lib/skill_router.last_suggestion(session_id)` returns a suggestion with
**confidence >= 0.90** for the current user prompt, the orchestrator MUST
choose one of the three responses below. Below 0.90 the suggestion is
advisory only — the existing `skill-router-prompt-suggest.sh` hint already
surfaces it.

## The Three Allowed Responses

1. **Invoke the suggested skill** — preferred. Launch the skill via the Skill
   tool, or pass `Load skills/<skill-name>/SKILL.md` to a sub-agent prompt.
   The hook detects this signal automatically (also via a `skill-invoked`
   event on the session events stream — exact storage path is harness-specific
   and resolved by the active adapter; see `lib/harness_adapter/`).

2. **Invoke a strictly stronger skill** that subsumes the suggested one
   (e.g. `/research-protocol` instead of `/repo-scout` when the contract is
   richer). Justify in one line in the agent prompt or commit message. The
   gate considers any matching `Load skills/<name>/SKILL.md` as satisfying
   the threshold; the choice of which skill is the operator's.

3. **Bypass with explicit annotation** — emit a one-line annotation in the
   tool input (agent prompt or bash command):

   ```
   SKILL_BYPASS: <skill-name> confidence=<N.NN> reason=<short justification>
   ```

   Example:
   `SKILL_BYPASS: repo-scout confidence=0.95 reason=already-evaluated-batch-during-prior-session`

   The hook records this in `.cognitive-os/metrics/skill-bypass.jsonl` for
   later audit. Annotation is sufficient — the gate does not validate the
   reason text, but operators reviewing the audit log will.

## Enforcement

`hooks/orchestrator-skill-invocation-gate.sh` runs on `PreToolUse` for the
`Agent` and `Bash` matchers:

- 1st un-annotated bespoke launch at high confidence -> WARN to stderr.
- 2nd un-annotated bespoke launch -> WARN to stderr.
- 3rd un-annotated bespoke launch -> **BLOCK** (exit 2).

The counter is per `session_id`, persisted at
`.cognitive-os/runtime/skill-bypass-counter-<session_id>`.

## Emergency Env Override

When the gate is wrong (broken skill, false positive, or operator-known
exception), set both:

```
COS_ALLOW_SKILL_BYPASS=1
COS_SKILL_BYPASS_REASON='<short text describing why>'
```

before launching the Agent/Bash tool. The override audits an `env-override:
<reason>` entry to `skill-bypass.jsonl`. If `COS_ALLOW_SKILL_BYPASS=1` is set
without `COS_SKILL_BYPASS_REASON`, the gate exits 2 (no silent bypass).

## When Override is Permitted

Reserved for:
- Demonstrably broken or misconfigured skill (the bypass + reason serves as
  the bug report).
- One-off pattern false positives (the routing pattern, not the prompt,
  needs the fix — see ADR-188 §Border Cases).
- Cross-session continuation where the skill already ran in a prior session
  and re-running would duplicate work.

NOT a substitute for fixing routing-pattern over-fits. Repeated overrides
for the same skill are a signal to lower the routing confidence in
`skills/<name>/SKILL.md`.

## Killswitch

`DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE=1` disables the gate
entirely. Use only when investigating a hook regression — never as a
permanent posture.

## See Also

- `docs/adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md`
- `hooks/orchestrator-skill-invocation-gate.sh`
- `hooks/skill-router-prompt-suggest.sh` (advisory layer)
- `lib/skill_router.py` — `last_suggestion(session_id)`
- `tests/contracts/test_skill_invocation_gate.py`
