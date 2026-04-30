# ADR-080: Hermes Cross-Harness Adoption (Umbrella)

<!-- SCOPE: OS -->

**Status**: Proposed
**Date**: 2026-04-30
**Author**: Maintainer
**Related**: ADR-057 (harness-agnostic core), ADR-064 (cross-harness authoring),
ADR-074 (Tier-0 learning loop), ADR-076 (skill-tier frontmatter), ADR-078 (mid-task memory tool)

---

## Status

Proposed. Blocked-by: ADR-081.

---

## Context

### Prior adoption and its implicit assumption

ADR-074 through ADR-078 ported several Hermes primitives into COS: the Tier-0
learning loop, the memory scanner, skill-tier frontmatter alignment, and the
mid-task memory tool. Each of those ADRs evaluated Hermes pieces against
Claude Code-as-the-only-harness. The remainder of the Hermes plugin
(`.claude/plugins/hermes-agent/`) was dismissed as "Claude Code-specific" after
that initial review.

That dismissal was wrong.

### The cross-harness lens

ADR-057 and ADR-064 establish that COS is harness-agnostic: the same cognitive
OS must run on Claude Code, Cursor, Windsurf, VS Code Agent, Cline, and any
future harness that executes the SKILLS + RULES surface. The practical
consequence is that features the Claude Code runtime provides for free —
automatic context compaction, native prompt caching, a single unified rate-limit
governor — are **not available** in other harnesses.

Re-evaluating the dismissed Hermes pieces through that lens reveals that several
of them are not Claude Code conveniences; they are the only portable
implementation of critical infrastructure for harnesses that lack those runtime
features.

### What makes a Hermes piece load-bearing under cross-harness

A piece is load-bearing if:

1. Non-Claude harnesses have no native equivalent, AND
2. The absence of the piece degrades correctness, reliability, or
   cost-predictability for real workloads in those harnesses.

Pieces that are Claude Code-specific convenience wrappers (already available via
the harness SDK) or out-of-domain (RL training, duplicate storage) do not meet
this bar.

### License

Hermes is MIT-licensed. Copy-verbatim porting is safe. This was established in
the ADR-078 adoption note and recorded in `.cognitive-os/adoption-registry.yaml`.
All future ports under this umbrella inherit that clearance — no new license
review is required per item.

---

## Decision

Hermes pieces are grouped into four tiers based on cross-harness necessity and
decision confidence.

### Prerequisite: Codex harness adapter (ADR-081)

Tier 1 of this ADR is **blocked** until ADR-081 (Codex harness adapter) ships
and produces byte-identical canonical events when compared against the existing
Claude Code adapter.

**Rationale.** ADR-064 (cross-harness authoring guide) is currently Proposed,
pending proof that a second real harness can satisfy the canonical event schema
defined in ADR-033. Claude Code is the only harness with a full adapter today;
Aider is a passive POC; Codex is operationally in use (`.codex/hooks.json` is
populated and hand-maintained) but lacks `lib/harness_adapter/codex.py`. Porting
Hermes pieces to satisfy a contract that no second harness has yet exercised
means building on an unverified abstraction boundary. If the abstraction turns out
to be wrong, every Tier 1 item must be reworked simultaneously.

**Exception — harness-independent items.** Items that can be designed without
coupling to the harness adapter surface MAY proceed in parallel with ADR-081
work. Specifically, the portable prompt caching layer (Tier 1 #2) is a candidate:
if `lib/prompt_caching.py` is structured as a pure provider abstraction with no
harness adapter dependency, it may land before ADR-081 closes. Each such item
must be explicitly marked harness-independent in its implementation ADR or SDD
before parallel work begins.

---

### Tier 1 — Critical cross-harness parity

These pieces close gaps that exist for every non-Claude-Code harness. Tier 1
items block each other in dependency order: item 1 (multi-provider adapters)
must land before items 2–4 can be wired to a provider surface.

**1. Multi-provider adapters**
Source: `.claude/plugins/hermes-agent/agent/*_adapter.py`
(gemini, bedrock, copilot, codex adapters)
Target: `lib/harness_adapter/`

COS's harness adapter layer (ADR-033) defines a canonical event schema but does
not implement provider-specific API adapters. Each non-Anthropic harness needs
a thin adapter to normalize model API calls, streaming deltas, and error codes.
Hermes implements exactly this. Porting completes the provider-normalization
surface and is a prerequisite for items 2–4 to function across providers.

**2. Portable prompt caching layer**
Source: `.claude/plugins/hermes-agent/agent/prompt_caching.py`
Target: `lib/prompt_caching.py`

Prompt caching in Claude Code is implicit (the harness manages cache-control
headers). Other providers expose different caching semantics or none at all.
This module provides a provider-agnostic abstraction: callers request caching
without knowing whether the underlying provider supports it, and the adapter
degrades gracefully. Without this, prompt-caching benefits are silently lost on
non-Anthropic harnesses and cost models become inaccurate.

**3. Context and trajectory compressors**
Source: `.claude/plugins/hermes-agent/agent/context_compressor.py`,
`trajectory_compressor.py`
Target: `lib/context_compressor.py`, `lib/trajectory_compressor.py`

Claude Code performs automatic compaction when context approaches the window
limit. No other harness does. In non-Claude harnesses, unchecked context growth
causes silent truncation or hard failures. These modules provide the only
portable compaction vehicle. They complement the existing `context-management`
rule, which governs when to compress but has no implementation to call.

**4. Rate-limit instrumentation**
Source: `.claude/plugins/hermes-agent/agent/rate_limit_tracker.py`,
`nous_rate_guard.py`
Target: `lib/rate_limit_tracker.py`, `lib/rate_guard.py`

The `rate-limiting` rule (RULES-COMPACT.md §4) documents policy but does not
measure or enforce it. These modules instrument actual token consumption and
provider rate-limit headers, enabling the `resource-governor` skill and
`non-blocking-retry` rule to act on real data rather than estimates. Without
measurement, rate-limit failures surface as opaque errors across all harnesses.

---

### Tier 2 — COS feature parity outside Claude Code

These pieces port COS features that currently depend on Claude Code-specific
scheduler or taxonomy primitives. They are not blockers for Tier 1.

**5. Batch runner and cron primitives**
Source: `.claude/plugins/hermes-agent/agent/batch_runner.py`,
`.claude/plugins/hermes-agent/cron/`
Target: `lib/batch_runner.py`, harness adapter event hooks

The `/schedule`, `/loop`, and `CronCreate` semantics work in Claude Code via
the harness scheduler. Non-Claude harnesses have no equivalent scheduler. The
`batch_runner.py` and cron primitives give COS a portable scheduling surface.
The existing `batch-runner` skill shells out to these; this tier makes that
skill cross-harness-functional.

**6. Error classifier and insights layer**
Source: `.claude/plugins/hermes-agent/agent/error_classifier.py`,
`insights.py`
Target: `lib/error_classifier.py`, `lib/insights.py`

`error-learning.jsonl` records raw error events (ADR-074 §2). There is no
semantic taxonomy on top: identical root causes appear as distinct error
strings, making deduplication and pattern detection unreliable. The Hermes
error classifier adds structured labeling (transient vs. permanent, provider vs.
tool vs. logic). The insights module aggregates classified events into
actionable summaries. Together they close the gap between error recording and
error learning.

---

### Sequencing

The mandatory execution order for this ADR is:

1. **ADR-081 Codex harness adapter (BLOCKER)** — separate ADR/change. Must ship
   and pass byte-identical canonical event comparison against the Claude Code
   adapter before any harness-coupled Tier 1 item begins.
2. **Tier 1 in dependency order**: context_compressor → prompt_caching →
   rate_limit_tracker → batch/cron. (Harness-independent items such as a
   decoupled prompt_caching layer may proceed in parallel with step 1 if
   explicitly marked as such in their implementation artifact.)
3. **Tier 2 only after Tier 1 stabilizes** — batch runner and error classifier
   build on top of the Tier 1 surface; starting them early creates re-work risk.
4. **Re-evaluate parking-lot items and Cursor/Continue/other Tier-C harnesses**
   based on observed demand after Tier 1 is stable. Claude Code and Codex are
   the two real targets; all others are Tier C / on-demand.

---

### Parking lot — investigate before deciding

These pieces require further investigation of COS's multi-agent communication
roadmap before a porting decision can be made. They are captured here to prevent
re-derivation but carry no commitment.

**7. `skill_commands.py`**
Question: Does this abstract cross-harness skill invocation in a way that is
not already covered by `lib/harness_adapter/` + SKILL.md convention? If yes,
it becomes Tier 1 or Tier 2. If no, it is a duplicate of existing routing.

**8. `acp_adapter` and `acp_registry`**
Question: Does COS intend to adopt the Agent Communication Protocol as its
multi-agent message bus? The answer depends on the multi-agent communication
vision (Valkey is currently OFF; ACP is an alternative). This investigation
should produce a dedicated ADR if adoption is warranted.

---

### Explicit discards

These pieces are evaluated and rejected. They must not be ported.

**9. Memory plugins (byterover, hindsight, mem0, supermemory)**
Location: `.claude/plugins/memory/`

Engram is COS's canonical memory backend. Each of these plugins offers an
alternative storage layer with its own API, credential surface, and data model.
Porting any of them would create duplicate storage paths and split the memory
surface across multiple backends. The risk of inconsistent recall across backends
outweighs any incremental feature benefit.

**10. tinker-atropos**
This module implements reinforcement learning for agent behavior tuning. RL
training is out of COS's operational scope and would introduce an unbounded
compute and data dependency.

---

## Consequences

### What gets unblocked

- **Any non-Claude harness becomes a first-class COS target.** Tier 1 is the
  prerequisite set: once the four items land, harnesses without compaction,
  caching, or unified rate-limiting can run COS workloads with the same
  reliability guarantees as Claude Code.
- **The `resource-governor` skill gets real data.** Rate-limit instrumentation
  (Tier 1 #4) feeds actual consumption numbers to the existing policy layer.
- **`/schedule` and `/loop` are no longer Claude Code-only.** Tier 2 #5 makes
  the scheduling surface portable.
- **Error deduplication becomes semantic.** Tier 2 #6 closes the gap between
  recording errors and learning from them.

### Risks and trade-offs

- **Tier 1 is sequentially coupled.** Multi-provider adapters (item 1) must land
  before the others can be wired. If adapter porting stalls, items 2–4 cannot
  reach their full cross-harness benefit.
- **Test surface expands.** Each Tier 1 module needs unit tests with provider
  mocks. Existing test infrastructure (`tests/unit/`) covers the pattern, but
  the adapter matrix (gemini × bedrock × copilot × codex) grows the mock
  maintenance burden.
- **Parking lot items carry uncertainty cost.** Leaving items 7 and 8 unresolved
  means the skill invocation and multi-agent communication surfaces remain
  partially undefined. Follow-up investigation should close these within two
  sprints of Tier 1 landing.

---

## Open questions

1. **Target harness priority list — resolved.** Claude Code (full adapter) and
   Codex (ADR-081, in progress) are the two real targets. Cursor, Windsurf,
   Cline, and VS Code Agent are Tier C / on-demand; they will be addressed based
   on observed demand after Tier 1 stabilizes. No separate harness-validation
   report is needed to unblock this ADR.

2. **Parking lot resolution cadence.** Items 7 and 8 should be triaged once
   Tier 1 item 1 lands (because adapter porting clarifies what
   `skill_commands.py` would need to abstract). A 2-sprint deadline is
   recommended.

3. **Embedding stack.** Not addressed here. Embedding decisions are relevant
   only if a peer-card ADR (scoped around ADR-077) is opened. This ADR is
   strictly about the Hermes operational primitives.

---

## Implementation notes

This ADR is the umbrella decision. It does not contain implementation details
or task lists for individual items. Each Tier 1 item should be driven by its
own follow-up ADR or SDD change:

| Item | Suggested follow-up artifact |
|------|------------------------------|
| Tier 1 #1 — multi-provider adapters | ADR-081 or `sdd-new hermes-provider-adapters` |
| Tier 1 #2 — prompt caching layer | ADR or SDD task under #1's umbrella |
| Tier 1 #3 — context/trajectory compressors | ADR or SDD task |
| Tier 1 #4 — rate-limit instrumentation | ADR or SDD task |
| Tier 2 #5 — batch runner / cron | SDD change once Tier 1 is stable |
| Tier 2 #6 — error classifier / insights | SDD change |
| Parking lot #7, #8 | Investigation report → dedicated ADR if adopted |

The ordering within Tier 1 is fixed: item 1 first, items 2–4 in any order after
item 1 lands.

---

## Alternatives rejected

- **Port everything now as a single batch.** Rejected because the parking lot
  items have unresolved design questions, and the explicit descarts must not be
  included. A single batch would require resolving all questions before any
  value lands.
- **Re-evaluate on an item-by-item basis without an umbrella ADR.** Rejected
  because the original dismissal was wrong precisely because individual items
  were not evaluated through the cross-harness lens. The umbrella ensures
  consistent framing and prevents re-derivation of the same context.
- **Implement a custom cross-harness adapter layer from scratch instead of
  porting Hermes adapters.** Rejected because Hermes has already solved the
  provider normalization problem with a battle-tested implementation under MIT
  license. Reinvention would duplicate work with no advantage.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q --tb=short
python3 -m pytest tests/contracts/test_session_start_tooling_contract.py -q --tb=short
```

---

## Cross-references

- ADR-033: Harness-agnostic event capture (canonical schema, `lib/harness_adapter/`)
- ADR-057: Harness-agnostic core
- ADR-064: Cross-harness authoring guide
- ADR-074: Tier-0 learning loop closure
- ADR-076: Skill-tier frontmatter alignment (Hermes tier model)
- ADR-078: Mid-task memory tool (port from Hermes)
- Hermes plugin: `.claude/plugins/hermes-agent/` (MIT)
- Adoption registry: `.cognitive-os/adoption-registry.yaml`
- Engram topic: `adr-080-hermes-cross-harness`
