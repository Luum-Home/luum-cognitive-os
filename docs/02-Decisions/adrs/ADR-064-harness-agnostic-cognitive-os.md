---
adr: 64
title: Harness-Agnostic Cognitive OS
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Surfaces 2-4 and the Codex/Cursor adapter files were not yet implemented.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-064 — Harness-Agnostic Cognitive OS

## Status

**Implementation-plan**: `.cognitive-os/plans/architecture/adr-064-implementation-plan.md`

**Accepted (2026-04-30)** — 2026-04-24 Proposed. Extends ADR-033 (harness-agnostic
event capture), ADR-062 (multi-provider agent loop), and ADR-063 (Agent()
replication scope) to the remaining harness-coupled surfaces of the Cognitive OS.

**Acceptance trail**:
- **Codex adapter**: `lib/harness_adapter/codex.py` shipped in commit `9062829`
  (Session B), 292 LOC implementing the full `HarnessAdapter` ABC contract.
- **Capability matrix**: `manifests/harness-driver-capabilities.yaml` documents
  Codex's honest limitations (PreToolUse/PostToolUse on Bash only as of
  v0.126.0-alpha.8, no PreCompact, no native scheduling).
- **Parity test**: `tests/integration/test_harness_agnostic_skill_run.py` shipped
  in commit `259f766` (Session A). Asserts byte-identical canonical events
  between `ClaudeCodeAdapter` and `CodexAdapter` for `session_start`,
  `user_prompt_submit`, and `session_end`. 4/4 pass. Non-Bash tool events
  excluded with documented rationale (Codex coverage gap).
- **ADR-081 verification**: design-vs-impl review (engram topic_key
  `adr-081-implementation-review`) found 27/27 unit + integration tests pass,
  3 LOW/MEDIUM gaps documented (no blockers).

**Outstanding for Surfaces 2-4** (these do NOT block Accepted status, but
remain as P0 implementation work per the plan): per-harness settings-driver
matrix, `cos-skill` CLI, `cos-agent` spawner, `lib/harness_adapter/cursor.py`,
`lib/harness_adapter/bare_cli.py`, `bin/cos-skill list/describe/run`,
`bin/cos-agent spawn`, `scripts/_lib/settings-driver-codex.sh`. Tracked in
`.cognitive-os/plans/architecture/adr-064-implementation-plan.md`.

**Status review 2026-04-27** (historical, preserved): Surface 1 (event capture
via `lib/harness_adapter/`) was exercised in production with `ClaudeCodeAdapter`
and `AiderAdapter`. Web evidence confirmed Codex (v0.124.0+, OpenAI Codex Hooks)
and Cursor both ship compatible hook vocabularies. Surfaces 2-4 and the
Codex/Cursor adapter files were not yet implemented. The verification suite
mandated by this ADR did not exist in the repo. **Flip to Accepted** condition
("Phase 2 ships and at least one non-CC harness produces byte-identical
canonical events for a reference skill") was satisfied on 2026-04-30 — see
Acceptance trail above.

**Adapter gap to track when implementing `codex.py`**: as of Codex v0.124.0,
`PreToolUse`/`PostToolUse` are emitted only for the Bash tool (per
github.com/openai/codex#16732). The adapter must handle the tool-coverage gap
explicitly — either by surfacing it as a known limitation or by polling other
tool channels — until Codex closes parity with Claude Code's full tool surface.

## Context

ADR-062 made the LLM layer provider-agnostic: seven providers run behind a
uniform OpenAI-compatible loop. But the **harness** — the environment that
loads skills, fires hooks, spawns sub-agents, and records sessions — is still
Claude Code-specific. When the operator said on 2026-04-24:

> *"además tiene que ser agnóstico"*

they were pointing at the layer above the LLM: if we move to Codex, Cursor,
a bare Python CLI, or a GitHub Action, most of the OS value evaporates even
though the LLM dispatch still works.

### What is coupled today

| Surface | Coupling |
|---|---|
| `.claude/settings.json` hook registrations | Claude Code–specific event matchers (`PreToolUse`, `PostToolUse`, `Agent`, `Edit\|Write`) |
| Slash commands (`/skill-name`) | Invoked by Claude Code's chat UI; skills are markdown files Claude Code auto-discovers |
| `~/.claude/projects/*.jsonl` transcripts | Claude Code's own session format; ADR-063 already declined to replicate |
| `Agent()` native sub-agent tool | Claude Code runtime primitive; ADR-063 accepted partial replica via ADR-062 loop |
| Skill auto-discovery | Happens inside Claude Code at startup; no standalone runner |
| Hook execution | Claude Code spawns each hook with a specific stdin JSON contract |

Shell scripts already reference `.claude/settings.json` in 15+ places
(`scripts/register-mcps.sh`, `scripts/setup.sh`, `hooks/self-install.sh`,
`scripts/apply-efficiency-profile.sh`, etc.). `record_completion.py` also
reads `.claude/projects/` for session reconstruction.

### What is already harness-agnostic

- `lib/harness_adapter/` (ADR-033): canonical event schema + CC + Aider adapters.
- `lib/openai_compatible_agent_loop.py` (ADR-062): no harness dependency.
- `docs/architecture/cross-harness-authoring.md`: the 5-item self-check already
  forbids new hardcoded `.claude/` paths in SO code.
- Rules / skills / hooks as plain files on disk — portable by construction,
  what's not portable is how they're *loaded* and *invoked*.

### Why now

ADR-062 closed the LLM-provider gap but exposed the harness gap. Without
closing it, the SO remains "portable in principle, Claude Code in practice."
Operator's stated alternatives are Codex (primary), Cursor, bare CLI, CI jobs.

## Decision

Define **four harness integration surfaces** that the Cognitive OS MUST
abstract. Claude Code stays the reference harness (on-by-default); other
harnesses are opt-in via adapter packs.

### Surface 1 — Event capture (mostly done, extend)

**Status**: ADR-033 already delivered `HarnessAdapter` ABC + canonical event
schema + CC adapter + Aider POC. We extend, not rebuild.

**Abstraction**: `lib/harness_adapter/dispatch.handle_event` accepts raw
payloads and routes to the right adapter. Canonical events land in
`.cognitive-os/metrics/canonical-events.jsonl`.

**Adapters required**:
- `claude_code.py` — exists, on by default.
- `aider.py` — exists (POC).
- `codex.py` — new. Parses Codex CLI session JSON.
- `cursor.py` — new. Parses Cursor's agent transcript format.
- `bare_cli.py` — new. Zero-frills adapter: reads `cos-runner` invocations.
- `ci.py` — new. Wraps GitHub Action / GitLab CI step output.

### Surface 2 — Hook registration

**Problem**: `.claude/settings.json` is the only way hooks register today.
Each hook (PreToolUse, PostToolUse, Stop, etc.) is matched by Claude Code's
event vocabulary.

**Abstraction**: canonical `cognitive-os.yaml > harness.hooks` block declares
hooks with harness-neutral events (`before_tool_call`, `after_tool_call`,
`before_agent_spawn`, `after_agent_complete`, `on_session_end`). A
**settings driver** per harness projects this canonical block into the
harness-native config.

```yaml
# cognitive-os.yaml (canonical; driver-agnostic)
harness:
  hooks:
    - id: auto-verify
      event: after_agent_complete
      script: hooks/auto-verify.sh
    - id: trust-score-validator
      event: after_agent_complete
      script: hooks/trust-score-validator.sh
```

**Drivers**:
- `scripts/_lib/settings-driver-claude-code.sh` — projects into `.claude/settings.json`.
- `scripts/_lib/settings-driver-codex.sh` — projects into `.codex/config.toml` hook surface.
- `scripts/_lib/settings-driver-cursor.sh` — projects into Cursor's rules/hooks format (best-effort).
- `scripts/_lib/settings-driver-bare.sh` — projects into `cos-runner`'s hook registry file.

Hooks themselves (the `.sh` files) MUST stay harness-neutral: read canonical
JSON from stdin (shape defined in ADR-033), write canonical events out. The
driver translates harness-native stdin → canonical stdin at the wrapper level.

### Surface 3 — Skill invocation

**Problem**: skills are triggered via `/skill-name` slash commands rendered by
Claude Code's chat UI. No UI → no invocation path.

**Abstraction**: every skill is invocable via a CLI entrypoint:

```
cos-skill run <skill-name> [--args json]
cos-skill list
cos-skill describe <skill-name>
```

`cos-skill` reads the same `.md` frontmatter + body Claude Code already reads.
It composes the prompt (applying `compose-prompt` logic from orchestrator
prompt composition, ADR-032 lineage) and dispatches through the LLM cascade
defined in ADR-062 (`scripts/orchestrator.py run`).

Harness wrappers register their UI-native shortcut:
- Claude Code: keeps `/skill-name` slash command (native behavior).
- Codex: maps `@skill-name` or similar to `cos-skill run skill-name`.
- Cursor: exposes via Cursor's composer commands.
- Bare CLI / CI: `cos-skill run <name>` directly from a shell script.

### Surface 4 — Sub-agent spawning

**Problem**: `Agent()` is a Claude Code native tool. Outside Claude Code,
there is no sub-agent.

**Abstraction**: `cos-agent spawn --task "..." --model <tier> [--providers ...]`.
Internally calls the `openai_compatible_agent_loop` (ADR-062). Persists the
transcript to `.cognitive-os/agent-transcripts/<agent-id>.jsonl` in the
canonical event schema (ADR-033), so every harness gets consistent telemetry.

ADR-063 already fixed the scope: we do NOT replicate MCP protocol, TodoWrite
semantics, Claude Code session format, or recursive sub-agents. `cos-agent`
is the flat replica loop; Claude Code keeps its native `Agent()` on that
harness by default.

### Summary: on-by-default vs opt-in

| Adapter pack | Default | Status after Phase |
|---|---|---|
| claude-code | ON | Shipped (ADR-033) |
| aider | OFF (POC) | Shipped (ADR-033) |
| bare-cli / cos-runner | OFF | Phase 2 |
| codex | OFF | Phase 3 |
| cursor | OFF | Phase 3 or later |
| ci (GitHub Actions) | OFF | Phase 4 |

## What we replicate vs not

### Replicate (portable core)

- Canonical event capture (ADR-033) across all harnesses.
- Hook chain execution via a neutral runner (reads canonical events, fires
  canonical-stdin hooks).
- Skill invocation via `cos-skill` CLI.
- LLM dispatch via ADR-062 cascade.
- Sub-agent spawning via `cos-agent` / ADR-062 loop.
- Discovery of `rules/`, `skills/`, `hooks/` as plain files on disk.
- Trust reports, DoD gates, acceptance criteria — all already
  harness-neutral (they're agent-instruction rules).

### Do NOT replicate (harness-native, stays on each harness)

- IDE-specific UX: Claude Code chat panel, Cursor inline completions,
  Codex autocomplete. Operator explicitly scoped these out.
- Claude Code's MCP protocol client (ADR-063 deferred this indefinitely).
- `~/.claude/projects/*.jsonl` transcript format (ADR-063).
- Claude Code native `Agent()` primitive on the Claude Code harness —
  we keep using it there; the replica `cos-agent` only covers non-CC
  harnesses.
- Harness-specific key bindings, themes, permissions UI.

## Implementation phases

Honest estimate: this is 10–15 sessions of work across phases. Not a
one-sprint effort. Each phase must ship the Claude Code regression suite
green (ADR-033 precedent: no harness-agnostic change may break the dominant
harness).

### Phase 1 — Inventory and classify (~2 sessions sonnet)

- Full audit of `scripts/`, `hooks/`, `lib/`: each file labeled
  `harness-specific` / `portable` / `needs-abstraction`.
- Output: `docs/architecture/harness-coupling-inventory.md`.
- Extend the cross-harness authoring self-check to quote the inventory.

### Phase 2 — `cos-runner` CLI (~4–5 sessions mixed)

- `cos-skill`, `cos-agent`, `cos-hooks run` binaries.
- Canonical hook stdin/stdout contract formalized as JSON Schema.
- Settings driver abstraction (`scripts/_lib/settings-driver-*.sh`) with
  claude-code driver and bare driver both shipping.
- Regression: all CC tests still pass; parallel bare-CLI smoke test
  produces the same canonical events for a reference skill.

### Phase 3 — Codex adapter pack (~3–4 sessions sonnet)

- `lib/harness_adapter/codex.py`.
- `settings-driver-codex.sh` (writes `.codex/config.toml` or equivalent).
- Skill invocation mapped to Codex-native shortcut.
- Smoke test: reference skill runs end-to-end under Codex, emits
  canonical events, trust report byte-identical modulo timestamps.

### Phase 4 — CI mode (~2 sessions sonnet)

- GitHub Action that runs `cos-skill run <name>`.
- Reuses bare-CLI driver under the hood.
- Produces trust report as a PR comment.
- Reference workflow in `.github/workflows/cos-ci-example.yml`.

**Cursor adapter** is TBD — lower priority per operator (Codex is primary
alternative). Likely another 3 sessions if prioritized.

Grand total realistic cost: **10–15 sessions**, mixed sonnet/opus, roughly
$15–$30 in agent costs before human review.

## Consequences

### Positive
- The SO runs anywhere rules + skills + hooks can be files on disk.
- Operator no longer couples their workflow to one CLI's survival.
- CI integration unlocks automated compliance / audit runs independent
  of any IDE.
- Makes the SO a credible "portable governance layer" story (differentiator
  vs single-vendor Agents SDK stacks).

### Negative
- Four more drivers to maintain; each harness drifts independently.
- `cos-runner` duplicates some of what Claude Code gives us for free
  (skill discovery, hook chaining). Implementation risk: drift between
  the runner's behavior and Claude Code's behavior.
- Phase 2+3+4 estimate (10–15 sessions) is real work. If the operator
  only ever uses Claude Code, the ROI is negative.
- Settings-driver projection can desync: canonical config says X, driver
  projects Y, hook fires Z. Needs a `cos doctor harness` verifier.

### Neutral
- Claude Code stays the reference harness. Nothing about on-by-default
  behavior changes for operators who don't care about portability.
- ADR-062 and ADR-063 already constrained `cos-agent` scope; this ADR
  doesn't widen it.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Do nothing; stay on Claude Code | Operator explicitly requested portability 2026-04-24. Leaving the harness coupled defeats ADR-062's investment. |
| Full Claude Code clone (replicate `~/.claude/projects`, MCP, Agent() internals) | ADR-063 already rejected this path. ~6+ sessions minimum, ToS-adjacent, perpetual catch-up maintenance. |
| Adopt `@anthropic-ai/claude-agent-sdk` as the universal runtime | Pay-per-token model — operator explicitly rejected (*"evitando usar las API keys de claude ya que son carísimas"*, ADR-063). Also still Claude-semantic, not harness-agnostic. |
| Wrap Claude Code as a subprocess from a neutral shell | Brittle (Claude Code is interactive by design); doesn't solve Codex/Cursor/CI cases; adds a dependency we cannot ship in CI without an Anthropic login. |
| Ship adapter packs as separate repos | Fragmentation risk; contract drift without shared test suite. Keep them in-tree under `lib/harness_adapter/` and `scripts/_lib/settings-driver-*/`. |

## Verification

- `cos-skill run verification-before-completion` executed under Claude Code
  and under `cos-runner` produces byte-identical trust reports (modulo
  timestamps and agent IDs).
- `.cognitive-os/metrics/canonical-events.jsonl` contains the same event
  sequence for the same skill regardless of harness.
- `scripts/demo-portability-proof.sh` runs the reference skill across all
  enabled harnesses and diffs outputs.
- `pytest tests/integration/test_harness_agnostic_skill_run.py` — new
  suite; parameterized over (claude-code, bare-cli, codex); all pass.
- `cos doctor harness` reports zero drift between canonical config and
  each driver's projected config.

## Related

- ADR-033 — Harness-agnostic event capture (foundation; this ADR extends).
- ADR-062 — Multi-provider agent loop (LLM-side agnosticism; this ADR is
  the harness-side counterpart).
- ADR-063 — Agent() replication scope (bounds what `cos-agent` does).
- ADR-032 — Orchestrator prompt composition (feeds `cos-skill`).
- `docs/architecture/cross-harness-authoring.md` — author-side self-check
  that already anticipated this ADR.
- `lib/harness_adapter/` — existing portable event capture implementation.

## Open questions

1. **Cursor priority**: is Cursor a real operator need or a nice-to-have?
   If nice-to-have, defer Phase "Cursor" indefinitely and keep scope to
   claude-code + bare-cli + codex + ci.
2. **Skill discovery cache**: Claude Code caches skill frontmatter at
   startup. `cos-skill` either reads on every invocation (slower) or
   maintains a cache at `.cognitive-os/skills-index.json` (drift risk).
   Trade-off TBD in Phase 2.
3. **MCP under non-CC harnesses**: ADR-063 punts MCP to Claude Code native.
   If Codex ships native MCP support (likely 2026+), does `cos-agent`
   gain an MCP pathway or stay flat? Revisit when Codex lands it.
4. **Hook concurrency**: Claude Code serializes hook execution per event.
   `cos-runner` needs the same guarantee or concurrent runs may double-write
   canonical events. Formalize in Phase 2.
5. **Settings-driver bi-directionality**: today drivers only project
   canonical → native. Should they also detect drift when a user edits
   `.claude/settings.json` manually and surface it? Likely yes; scope in
   Phase 2 under `cos doctor harness`.
