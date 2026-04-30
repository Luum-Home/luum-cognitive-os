# ADR-081 — Codex Harness Adapter

<!-- SCOPE: OS -->

**Status**: Proposed
**Date**: 2026-04-30
**Author**: Matias Nahuel Améndola

---

## Status

Proposed.

Blocks ADR-064 advancement (Harness-Agnostic Cognitive OS cannot exit Proposed
until a second harness produces byte-identical canonical events). Also blocks
ADR-080 Tier 1 (Hermes cross-harness adoption, whose `context_compressor` port
assumes a working Codex adapter).

## Context

### The portability gap

ADR-033 delivered the `HarnessAdapter` ABC and canonical event schema.
ADR-064 extended the vision to four surfaces (event capture, hook registration,
skill invocation, sub-agent spawning) and declared the OS harness-agnostic in
design. In practice, only `lib/harness_adapter/claude_code.py` has full
coverage: 14/14 unit tests and 4/4 integration tests pass. `aider.py` is a
passive file-watcher POC. No other adapter exists.

This means the OS remains **"portable in principle, Claude Code in practice"**
— exactly the state ADR-064 committed to exit.

### Codex is the operator's live secondary harness

The operator runs both Claude Code and Codex CLI daily. Evidence:
`.codex/hooks.json` exists in the repo and is hand-maintained. As of the date
of this ADR it registers 28 hooks across three Codex lifecycle events:

| Event | Hooks registered |
|---|---|
| `SessionStart` | 17 |
| `UserPromptSubmit` | 4 |
| `Stop` | 7 |

Every entry exports `COGNITIVE_OS_HARNESS=codex` and delegates to the same
`hooks/*.sh` scripts used by Claude Code. The hooks themselves are already
harness-neutral; what is missing is the adapter that canonicalises Codex's
native event payloads and the generation pipeline that produces
`.codex/hooks.json` from a single source of truth.

Hand-maintenance of 28 entries is unsustainable: adding a new hook requires
two identical edits (`.claude/settings.json` + `.codex/hooks.json`). A missed
sync has already caused observable drift. The file is proof that Codex is an
**operational surface**, not an aspiration.

### What ADR-064 gated on

ADR-064 §Status review 2026-04-27 states verbatim: *"Flip to Accepted when
Phase 2 ships and at least one non-CC harness produces byte-identical canonical
events for a reference skill."* Codex is the natural candidate. Until this
adapter ships, that condition cannot be satisfied.

### What ADR-080 gated on

ADR-080 (Hermes cross-harness adoption) Tier 1 requires a portable
`context_compressor` module. The design of that module assumes a working
`CodexAdapter` — context management on Codex depends on knowing which harness
is running and what events it can emit. Shipping ADR-081 first is the shortest
critical path.

### Codex v0.124.0 capability constraints

Codex CLI as of v0.124.0 fires `PreToolUse` and `PostToolUse` only for the
Bash tool (github.com/openai/codex#16732). This is a Codex implementation
choice, not a COS design flaw. The full implications are documented in the
Capability gaps section below.

## Decision

### 1. Implement `lib/harness_adapter/codex.py`

Create `packages/agent-lifecycle/lib/harness_adapter/codex.py` implementing
the same `HarnessAdapter` abstract base class contract as `claude_code.py`.
The adapter must:

- Parse the Codex hook stdin payload and emit a canonical `HarnessEvent` for
  each supported lifecycle event.
- Map Codex's native event names to canonical names:

  | Codex native | Canonical |
  |---|---|
  | `SessionStart` | `session_start` |
  | `UserPromptSubmit` | `user_prompt_submit` |
  | `PreToolUse` (Bash only) | `pre_tool_use` |
  | `PostToolUse` (Bash only) | `post_tool_use` |
  | `Stop` | `session_end` |

- Emit `None` (not an error) for events the harness physically cannot produce
  (`pre_compact`, native scheduling events). Callers must handle `None` as
  "event not available on this harness."
- Expose `SUPPORTED_EVENTS: frozenset[str]` as a class attribute listing only
  the events this adapter can produce. `dispatch.handle_event` must consult
  this set before routing.

### 2. Update `manifests/harness-driver-capabilities.yaml`

Add a `codex` entry to the capability matrix referenced by ADR-064. The entry
must honestly reflect v0.124.0 capabilities. Minimal required shape:

```yaml
codex:
  version_baseline: "0.124.0"
  events:
    session_start: true
    user_prompt_submit: true
    pre_tool_use: bash_only   # fires only for Bash tool; see ADR-081
    post_tool_use: bash_only  # fires only for Bash tool; see ADR-081
    session_end: true
    pre_compact: false        # no equivalent; requires portable compressor
  scheduling:
    native: false             # CronCreate semantics not available
    workaround: "ADR-080 Tier 2 batch/cron port"
  prompt_caching:
    native: false
  sub_agent_spawning: "cos-agent (ADR-064 Surface 4)"
```

The `claude_code` entry must also be present for comparison. Both entries are
the source of truth for any tooling that routes hook logic per harness.

### 3. Generate `.codex/hooks.json` from a single source of truth

`hooks/self-install.sh` already generates `.claude/settings.json` hook
registrations from the canonical hook list. Extend
`scripts/_lib/settings-driver-codex.sh` (introduced in ADR-064 §Surface 2) to
project the same canonical list into `.codex/hooks.json`.

After this change:
- `.codex/hooks.json` is a generated artifact, checked in but not manually
  edited.
- A `# DO NOT EDIT — generated by scripts/_lib/settings-driver-codex.sh`
  header is prepended to the file.
- A pre-commit hook (or `cos doctor harness`) detects drift between the
  canonical list and the generated file.
- The 28 existing entries are reproduced exactly, validating that the generator
  is a no-op for the current hook set before any new hooks are added.

**Deferral gate**: if `settings-driver-codex.sh` is not ready to ship alongside
the adapter, the generation may be deferred to a follow-up, provided that:
(a) this ADR documents the deferral explicitly, (b) a TODO comment is added to
`.codex/hooks.json`, and (c) the follow-up is tracked as a blocking item for
ADR-064 advancement.

### 4. Test parity

**Unit tests** — `tests/unit/test_harness_adapter_codex.py`:
Mirror the structure of the existing `test_harness_adapter_claude_code.py`
test suite. Must cover:
- Canonical event emission for each supported event type.
- `None` return for unsupported events (`pre_compact`, etc.).
- Payload fields from Codex's stdin schema are correctly mapped.
- `SUPPORTED_EVENTS` correctly excludes unsupported events.
- Adapter instantiation is idempotent.

**Integration tests** — `tests/integration/test_harness_agnostic_skill_run.py`
(referenced in ADR-064 but not yet created):
Parameterize over `(claude_code, codex)` adapters. For each shared supported
event (`session_start`, `user_prompt_submit`, `session_end`), run a reference
skill and assert that the canonical event dicts are byte-identical except for
the fields explicitly allowed to differ (timestamps, session IDs, harness name).
This is the concrete test ADR-064 requires for its acceptance condition.

## Capability gaps

The following gaps are real harness constraints. They are documented here so
that operators and tooling can make informed decisions. They are **not** COS
bugs to paper over.

### Tool-event coverage limited to Bash

Codex v0.124.0 fires `PreToolUse` and `PostToolUse` only when the model
invokes the Bash tool. Hooks that rely on these events to intercept other tool
calls (file edits, MCP calls, etc.) will not fire on Codex. Affected COS hooks
must document their Codex behavior in their own headers:

```
# CODEX: fires only on Bash tool invocations (ADR-081).
```

Rules or workflows that depend on full tool-event coverage are classified as
**Claude Code-only** in `manifests/harness-driver-capabilities.yaml` until
Codex closes parity. COS does not implement a workaround for this because doing
so (polling, syscall tracing, etc.) would be brittle and unsanctioned.

### No PreCompact equivalent

Codex has no event analogous to Claude Code's `PreCompact`. Context management
hooks (`context-management.sh`, `caveman-compress.sh`) that fire on
`PreCompact` in Claude Code are silent on Codex. The portable
`context_compressor` module from ADR-080 Tier 1 addresses this by running
compression logic via `UserPromptSubmit` and `Stop` events, which Codex does
support. This is a mutual dependency: ADR-081 unblocks the ADR-080 compressor
design, and the compressor closes the Codex context-management gap.

### No native scheduling

Codex has no equivalent to Claude Code's `CronCreate` tool or `/schedule`
skill. The `ScheduleWakeup` and `/loop` semantics available on Claude Code
are not portable to Codex without the `cos-agent` runner (ADR-064 Surface 4)
and the batch/cron port defined in ADR-080 Tier 2.

### Feature availability matrix

| COS feature | Claude Code | Codex |
|---|---|---|
| Session lifecycle hooks | Full | Full |
| Tool-use hooks (all tools) | Yes | Bash only |
| Context compaction hooks | Yes (PreCompact) | No (use ADR-080 compressor) |
| Native scheduling (/schedule, /loop) | Yes | No (ADR-080 Tier 2) |
| Prompt caching | Native | Not native |
| Sub-agent spawning | Agent() native | cos-agent (ADR-064 Surface 4) |
| Skill invocation | /skill-name | cos-skill run (ADR-064 Surface 3) |
| Canonical event capture | Full | Session + UserPrompt + Bash tools |

This matrix must be updated in `manifests/harness-driver-capabilities.yaml`
when Codex changes its hook surface. It is not projected from code; it is
maintained alongside the adapter.

## Consequences

### Positive

- **Unblocks ADR-064**: a second harness producing byte-identical canonical
  events satisfies the only remaining condition for ADR-064 to advance from
  Proposed to Accepted.
- **Unblocks ADR-080 Tier 1**: the `context_compressor` design in ADR-080
  depends on knowing Codex's event surface; this ADR provides the authoritative
  source.
- **Eliminates hand-maintenance**: `.codex/hooks.json` generation removes the
  current 2× edit burden and drift risk. The 28-entry file can grow via
  `self-install.sh` without operator intervention.
- **Forces honest portability accounting**: the feature matrix makes
  Claude Code-only features explicit rather than discovered at runtime.
- **Stress-tests the ADR-033 abstraction early**: two adapters with materially
  different capabilities will surface any abstraction leaks before the
  surface area widens to Cursor, CI, or other harnesses.

### Negative / Trade-offs

- Real engineering work. The adapter, tests, manifest, and generation pipeline
  together represent approximately 1–2 sonnet sessions of focused implementation.
- `test_harness_agnostic_skill_run.py` requires a test fixture that can
  simulate Codex's hook invocation model without the Codex binary itself.
  Mocking the stdin contract faithfully is non-trivial.
- Some COS hooks will remain Claude Code-only for the foreseeable future. This
  creates a documented two-tier system, which some operators may find
  surprising.

### Risks

- If Codex changes its hook schema (stdin shape, event names, matcher
  semantics) in a future version, the adapter must be updated. The
  `version_baseline` field in the manifest is the canary; it should be
  validated in CI.
- The `bash_only` coverage for `PreToolUse`/`PostToolUse` may mislead hook
  authors who assume full parity with Claude Code unless the limitation is
  surfaced clearly in tooling and documentation.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep `.codex/hooks.json` hand-maintained indefinitely | Already causing drift and 2× edit burden at 28 entries. The count grows with every new hook; the cost compounds. |
| Implement a polling shim for non-Bash tool events on Codex | Brittle (requires syscall tracing or Codex internals), unsanctioned, and creates a false sense of parity. Better to document the gap honestly. |
| Wait for Codex to close tool-event parity before implementing | ADR-064 and ADR-080 are blocked today. The gap is a known Codex limitation, not an implementation blocker for the adapter itself. |
| Implement Cursor adapter before Codex | Operator identified Codex as the primary non-CC harness. Cursor is lower priority (ADR-064 §Open questions). |
| Inline the Codex event mapping into `dispatch.py` without a separate adapter file | Violates the ADR-033 pattern (one file per harness); harder to test in isolation; coupling grows as mapping rules accumulate. |

## Acceptance criteria

The following must all pass before this ADR advances to Accepted:

1. `packages/agent-lifecycle/lib/harness_adapter/codex.py` exists and
   implements the full `HarnessAdapter` ABC contract from `base.py`.

2. `tests/unit/test_harness_adapter_codex.py` passes with at minimum the same
   number of test cases as `test_harness_adapter_claude_code.py`.

3. `tests/integration/test_harness_agnostic_skill_run.py` exists, is
   parameterized over `(claude_code, codex)`, and asserts byte-identical
   canonical events (modulo allowed-diff fields) for at least one shared
   lifecycle event.

4. `manifests/harness-driver-capabilities.yaml` contains a `codex` entry
   matching the schema described in this ADR.

5. `.codex/hooks.json` is either: (a) generated by
   `scripts/_lib/settings-driver-codex.sh` with a `DO NOT EDIT` header, or
   (b) carries an explicit deferral note in this ADR with a linked tracking
   item.

6. The Claude Code regression suite (`pytest tests/unit/test_harness_adapter_claude_code.py
   tests/integration/`) remains green — no existing test may regress.

## Verification

This ADR is Proposed; the implementation is not complete yet. While it remains
Proposed, verification is limited to document-contract and projection-safety
checks:

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q --tb=short
python3 -m pytest tests/contracts/test_canonical_projection_behavior.py::test_codex_projection_commands_point_to_installed_hooks -q --tb=short
```

When the ADR is implemented, the required acceptance verification expands to:

```bash
python3 -m pytest tests/unit/test_harness_adapter_codex.py -q --tb=short
python3 -m pytest tests/integration/test_harness_agnostic_skill_run.py -q --tb=short
python3 -m pytest tests/unit/test_harness_adapter_claude_code.py tests/integration/ -q --tb=short
```

## Open questions

1. **`.codex/hooks.json` generation scope**: should the generation pipeline
   (`settings-driver-codex.sh`) be part of this ADR's delivery or deferred to
   a follow-up? Delivering it together closes the drift risk immediately but
   widens scope. Deferring keeps the adapter scope tight but leaves 28 entries
   hand-maintained.

2. **Testing `PreToolUse`/`PostToolUse` without the Codex binary**: the
   integration test must simulate Codex's stdin for these events. The canonical
   approach is a JSON fixture matching Codex's documented hook schema. If
   Codex's schema is not publicly documented for the full hook payload, a
   session capture from a live Codex run should be used as the fixture source.

3. **Fallback event schema for physically absent events**: when a harness
   cannot emit a given canonical event (e.g., `pre_compact` on Codex), the
   adapter returns `None`. Should `dispatch.handle_event` log a structured
   warning to `canonical-events.jsonl` as `event_type: skipped, reason:
   harness_unsupported`? Or silently skip? A structured skip aids
   observability but creates noise in the event stream. Decision deferred to
   implementation.

4. **Capability matrix ownership**: `manifests/harness-driver-capabilities.yaml`
   must reflect each harness's actual version, not a static declaration.
   Should `cos doctor harness` read the installed Codex CLI version and
   compare against `version_baseline`, warning on mismatch? Likely yes; scope
   in ADR-064 Phase 3 follow-up.

## Related

- ADR-033 — Harness-agnostic event capture (foundation; `HarnessAdapter` ABC)
- ADR-033b — Harness-agnostic event capture extensions
- ADR-057 — Settings driver projection (hook generation per harness)
- ADR-064 — Harness-Agnostic Cognitive OS (this ADR delivers ADR-064 Phase 3
  entry condition)
- ADR-080 — Hermes cross-harness adoption (blocked on this ADR; ADR-080 Tier 1
  `context_compressor` depends on Codex event surface being defined here)
- `lib/harness_adapter/claude_code.py` — reference implementation
- `lib/harness_adapter/base.py` — ABC contract this adapter must satisfy
- `.codex/hooks.json` — existing hand-maintained hook registration (to be
  generated)
- `manifests/harness-driver-capabilities.yaml` — capability matrix (to be
  extended)
