---
adr: 22
title: Prompt-Type Hooks Adoption (Haiku-Evaluated Advisories)
status: accepted
implementation_status: partial
date: '2026-04-15'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
---

# ADR-022: Prompt-Type Hooks Adoption (Haiku-Evaluated Advisories)

**Date:** 2026-04-15
**Status:** Accepted
**Supersedes:** None
**Related:** ADR-008 (Multi-Tool Support), ADR-012 (Prompt-Driven Governance), ADR-021 (Vendor-Agnostic with Adapters)

## Context

The Cognitive OS ships several **advisory hooks** that judge the *quality* of an
agent prompt or response — for example:

- `prompt-quality.sh` — scores agent prompts on 5 dimensions (specificity,
  actionability, context, measurability, scope clarity).
- `completeness-check.sh` — flags vague prompts ("all files", "everything")
  that lack explicit enumeration.
- `confidence-gate.sh` — verifies an agent response includes a Trust Report
  with a numerical confidence score.

These hooks are written in pure Bash + Python regex. They have several known
weaknesses:

1. **Brittle pattern matching.** A prompt that lists files in a code fence
   triggers different patterns than one that lists files in prose. The regex
   library has to grow indefinitely to keep up.
2. **Slow cold start.** Each hook spawns Bash + Python + jq. On a cold cache
   that's ~80–250 ms per hook, and they run on **every** Agent invocation.
3. **No semantic awareness.** The hook can't tell that "process the entire
   request queue (currently 4 items: A, B, C, D)" is *exhaustive* even though
   it contains the word "entire".
4. **Maintenance cost.** Every false positive ends in another `grep -qiE`
   exception added to the script. The scripts have grown faster than they've
   improved precision.

Claude Code added a `type: "prompt"` hook handler. Instead of running a Bash
script, the hook returns a small system prompt + user prompt + model name
(typically `claude-haiku-4-5`), and Claude Code runs that prompt against the
model and uses the structured response as the hook's verdict. Latency is
~120–400 ms (one Haiku call) and the verdict is a real semantic judgment.

## Decision

**Convert the three advisory hooks listed above to `type: "prompt"` hooks
backed by Haiku, while keeping the original Bash hooks as fallback.**

Concretely:

1. Add three new hooks alongside the originals:
   - `hooks/prompt-quality-llm.sh`
   - `hooks/completeness-check-llm.sh`
   - `hooks/confidence-gate-llm.sh`
2. Each new hook emits a `hookSpecificOutput` JSON payload of type `"prompt"`
   with a small instruction asking Haiku to return a JSON verdict.
3. Each new hook **gracefully degrades** if Haiku is unreachable (hook exits 0,
   no block, no noise). The legacy Bash hook still runs in parallel as the
   safety net.
4. Once telemetry shows the LLM hook is at parity or better (≥ 14 days, no
   critical regressions), the Bash variant is moved to `hooks/_legacy/` and
   eventually deleted.

The new hooks are wired into the **standard** profile of both
`scripts/apply-efficiency-profile.sh` and `scripts/set-security-profile.sh` so
the pre-commit gate (Gate 3a) does not block them.

## Alternatives Considered

### Alt 1: Keep Python regex (status quo)

- Pro: No vendor coupling, no LLM cost.
- Pro: Deterministic.
- Con: ~80–250 ms cold start per hook, on every Agent call.
- Con: Brittle — false positives accumulate.
- Con: No semantic awareness (can't read the prompt the way a human would).
- **Rejected**: latency + maintenance cost outweigh determinism.

### Alt 2: Single shared Haiku call (one prompt judges all 3 dimensions)

- Pro: One LLM round-trip instead of three.
- Pro: Cheaper.
- Con: Couples three independent advisory concerns into one prompt — harder to
  reason about, harder to disable individually, harder to A/B test.
- Con: A single regression in one dimension regresses all three.
- **Rejected for v1** — revisit once the three hooks have stabilised. May
  consolidate in v2 behind a feature flag.

### Alt 3: Use Sonnet/Opus instead of Haiku

- Pro: Higher quality semantic judgment.
- Con: 5–10× the latency and 30× the cost on a path that runs every Agent call.
- **Rejected**: advisory hooks must stay in the hot path budget (< 500 ms).
  Haiku is sufficient for "does this prompt list files?" or "is there a Trust
  Report here?".

## Consequences

### Positive

- **Faster on warm path.** A Haiku call is ~120–400 ms; the regex script can
  spike to 250 ms cold. Net: parity to small win.
- **Better signal.** Haiku catches semantically-exhaustive prompts that the
  regex flags as vague, and catches semantically-vague prompts the regex
  misses (e.g., "do the usual thing").
- **Less maintenance.** No more "add another grep pattern" cycle.
- **Composable.** Future advisory hooks can adopt the same pattern with ~30
  lines of shell.

### Negative

- **Vendor coupling.** `type: "prompt"` is a Claude Code extension. Other
  harnesses (Codex/Gemini/Cursor/Windsurf) don't natively support it.
- **LLM dependency.** If Haiku is unreachable, the hook degrades to a no-op.
  Acceptable because these are *advisory* hooks — they never block.
- **Cost.** ~$0.0003 per Haiku call × N agent invocations per session.
  Negligible at current usage; should be tracked in `cognitive-os.yaml` cost
  budgets.

### Vendor lock-in mitigation (per ADR-021)

ADR-021 establishes that COS state is canonical, with thin per-provider
adapters. The same pattern applies here:

- The **canonical advisory logic** lives in the legacy Bash hook (works
  everywhere).
- The **Claude Code adapter** is the new `*-llm.sh` hook (faster, smarter,
  Claude Code-specific).
- For Codex/Gemini/Cursor/Windsurf the legacy Bash hook continues to run.
- If another harness adds an equivalent of `type: "prompt"`, an adapter for
  that harness can be written by copying the LLM hook and changing the JSON
  envelope.

This means **adopting prompt-type hooks does not break multi-tool support**.

## Implementation

### Files added in this ADR

| File | Purpose |
|---|---|
| `hooks/prompt-quality-llm.sh` | Haiku-backed prompt-quality scorer |
| `hooks/completeness-check-llm.sh` | Haiku-backed completeness checker |
| `hooks/confidence-gate-llm.sh` | Haiku-backed Trust Report verifier |
| `tests/unit/test_prompt_hooks.py` | Behavioral tests for the three hooks |

### Profile registration

Both new hooks must be added to the `standard` and `paranoid` tiers of
`scripts/apply-efficiency-profile.sh` and `scripts/set-security-profile.sh`
**before** committing — Gate 3a of `.githooks/pre-commit` blocks otherwise.

### Migration plan

- **Week 1–2**: Run LLM and Bash hooks in parallel. Compare verdicts in
  `.cognitive-os/metrics/prompt-quality.jsonl` vs. a new
  `prompt-quality-llm.jsonl`.
- **Week 3+**: If LLM hook ≥ 95 % agreement on the regex's "high-quality"
  verdicts and finds ≥ 10 % more genuine low-quality prompts, promote LLM as
  primary and move Bash hooks to `hooks/_legacy/`.
- **Quarter end**: delete legacy hooks, update profile scripts.

## References

- [Claude Code Hooks — `type: "prompt"`](https://code.claude.com/docs/en/hooks)
- ADR-008: Multi-Tool Support — why we keep a vendor-agnostic fallback
- ADR-012: Prompt-Driven Governance — semantic gates over regex gates
- ADR-021: Vendor-Agnostic State with Provider Adapters — same pattern,
  different surface
