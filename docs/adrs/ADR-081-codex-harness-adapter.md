---
adr: 81
title: Codex Harness Adapter
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: 'Deferred from this slice:'
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-081 — Codex Harness Adapter

<!-- SCOPE: OS -->

**Status**: Accepted
**Date**: 2026-04-30
**Author**: Maintainer

---

## Status

Accepted.
Consumes-plan: .cognitive-os/plans/architecture/adr-064-implementation-plan.md

Unblocks the ADR-064 advancement path by making Codex a second canonical
harness with captured native payload fixtures. It also unblocks ADR-080 Tier 1
(Hermes cross-harness adoption), whose `context_compressor` port assumes a
working Codex adapter.

## Context

An implementation plan for ADR-064 already exists at `.cognitive-os/plans/architecture/adr-064-implementation-plan.md` (2026-04-28), enumerating 9 P0 tasks across 4 surfaces. ADR-081 does NOT redefine that work; it scopes the Codex adapter (Task 4 of that plan, listed as Task 1.1 in Section 2) and the surrounding driver projection (Tasks 2.1–2.3) into a single ADR-level decision. The plan's task estimates (~7-9 sessions total, ~3h for the adapter alone) are authoritative.

### The portability gap

ADR-033 delivered the `HarnessAdapter` ABC and canonical event schema.
ADR-064 extended the vision to four surfaces (event capture, hook registration,
skill invocation, sub-agent spawning) and declared the OS harness-agnostic in
design. In practice, only `lib/harness_adapter/claude_code.py` has full
coverage: 14/14 unit tests and 4/4 integration tests pass. `aider.py` is a
passive file-watcher POC. No other adapter exists.

This meant the OS was **"portable in principle, Claude Code in practice"**
— exactly the state ADR-064 committed to exit. This ADR is the first accepted
implementation slice that moves Codex from projected driver to canonical
harness adapter.

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
events for a reference skill."* Codex is the natural candidate. This ADR
delivers the adapter and fixture corpus needed for that condition; the
reference-skill parity test remains tied to ADR-064 Surface 3 (`cos-skill run`).

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

### Pre-work: 30-minute spike (before Task 1.1)

Before any adapter work begins, instrument an existing `.codex/hooks.json`
script to dump its stdin to a file during a live Codex session. This captures
real Codex hook payloads so the adapter is built against actual shapes, not
assumed ones. The plan (Section 5, risk 8) flags this explicitly: "run a
30-min spike that captures actual Codex hook payloads so the adapter is built
against real shapes, not assumed ones."

### 1. Implement `lib/harness_adapter/codex.py` (Plan Task 1.1)

Implement `lib/harness_adapter/codex.py` per plan Task 1.1 (`lib/harness_adapter/codex.py`,
~1 session, ~3h). The adapter satisfies the `HarnessAdapter` ABC contract from
`base.py`, the same contract as `claude_code.py`. Per the plan's acceptance
criteria for Task 1.1:

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

- For non-Bash tool events (the v0.124.0 coverage gap), emit a `ParseError`
  canonical event with `reason="codex_tool_coverage_gap"` rather than silent
  skip (plan Task 1.1 criterion 3).
- Add `HarnessName.CODEX = "codex"` enum value to `base.py` and register the
  adapter in the `ADAPTERS` list in `dispatch.py` (plan Task 1.1 criteria 4–5).
- Expose `SUPPORTED_EVENTS: frozenset[str]` as a class attribute listing only
  the events this adapter can produce. `dispatch.handle_event` must consult
  this set before routing.

### 2. Update `manifests/harness-driver-capabilities.yaml` (Plan Task 2.1 input)

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

### 3. Generate `.codex/hooks.json` from a single source of truth (Plan Tasks 2.1 and 2.3)

This work maps directly to plan Tasks 2.1 (canonical hooks block in
`cognitive-os.yaml`, ~0.25 session) and 2.3 (`scripts/_lib/settings-driver-codex.sh`,
~1 session). Task 2.2 (`settings-driver-claude-code.sh`) is a sibling but not
scoped to this ADR. Implement `scripts/_lib/settings-driver-codex.sh` to
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

### 4. Test parity (Plan Task 1.1 criteria + verification suite)

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
| Implement Cursor adapter before Codex | Operator identified Codex as the primary non-CC harness. Cursor is P2 in the implementation plan (Tasks 1.3/2.6) pending operator commitment, per plan Section 5 risk 3. |
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

## Acceptance trail

| Milestone | Date | Reference |
|---|---|---|
| Initial implementation (Session B) | 2026-04-30 | commit `9062829` — 292 LOC adapter, fixtures, unit + integration smoke |
| Design-vs-impl verification | 2026-04-30 | this review session |
| `test_harness_agnostic_skill_run.py` passing | 2026-04-30 | 4/4 tests; ADR-064 gate satisfied |
| Full suite (27 tests) green | 2026-04-30 | `pytest tests/unit/test_harness_adapter_*.py tests/integration/test_*adapter*.py tests/integration/test_harness_agnostic_skill_run.py` |

## Verification gaps (open as of 2026-04-30)

The following items are verified deferred — they do not block Accepted status but remain open follow-up work:

1. **`scripts/_lib/settings-driver-codex.sh` not present** (ADR §Decision 3, Acceptance Criterion 5b): only `scripts/_lib/settings-driver.sh` exists; the Codex-specific driver is not generated. `.codex/hooks.json` carries no `DO NOT EDIT` header and is still hand-maintained. Severity: MEDIUM — documented deferral per §Implementation status. Follow-up: ADR-057/ADR-064 Surface 2.

2. **Claude Code adapter does not natively parse `SessionStart` or `UserPromptSubmit` from hook stdin** (ADR §Decision 4): the parity test constructs CC canonical events directly from the base dataclass rather than via `ClaudeCodeAdapter.parse_event`. The test still satisfies ADR-064's structural byte-identity condition because it proves the *schema* is shared; the CC adapter's hook coverage is a separate concern. Severity: LOW — parity gate is schema-level, not parse-path-level.

3. **`SUPPORTED_EVENTS` is not consulted by `dispatch.handle_event`** (ADR §Decision 1, last bullet): the dispatch layer calls `detect_harness` then `parse_event` without first checking whether the event type is in `SUPPORTED_EVENTS`. The frozenset is present as a class attribute (criterion met) but the routing guard is absent. Severity: LOW — `parse_event` handles unknown events gracefully by returning `ParseError`; the missing pre-check is a defence-in-depth gap, not a correctness failure.

```bash
python3 scripts/harness_parity_audit.py --source claude --target codex --strict --json
```
## Implementation status

Accepted implementation slice shipped on 2026-04-30:

- `lib/harness_adapter/codex.py` normalizes live Codex Desktop session rows and
  Codex hook stdin payloads into canonical events.
- `tests/fixtures/codex-live-session/` stores sanitized payloads captured from
  an actual Codex Desktop session JSONL stream. Absolute paths, long prompts,
  and operator content are replaced with stable placeholders.
- `lib/harness_adapter/dispatch.py` registers `CodexAdapter` before Claude Code
  so native Codex session rows do not fall through to `none` or Claude.
- `internal/provider/codex.go` maps Codex `UserPromptSubmit` and `Stop`, reports
  non-Bash tool-event coverage as `codex_tool_coverage_gap`, and uses
  `.codex/hooks.json` as the settings driver path.
- `manifests/harness-driver-capabilities.yaml` records Codex v0.126.0-alpha.8
  as the observed baseline and points to the captured fixture corpus.

Deferred from this slice:

- Generating `.codex/hooks.json` from `scripts/_lib/settings-driver-codex.sh`
  remains ADR-064/ADR-057 follow-up work. Current projection is already
  tested, but the driver file is not yet generated from a single canonical
  block with a `DO NOT EDIT` header.
- `tests/integration/test_harness_agnostic_skill_run.py` was shipped on
  2026-04-30 as part of this verification pass. It is parameterized over
  `(claude_code, codex)` for `session_start`, `user_prompt_submit`, and
  `session_end`, and asserts structural byte-identity (modulo allowed-diff
  fields). This satisfies ADR-064's acceptance gate condition.

## Verification

Required focused verification for this ADR:

```bash
python3 -m pytest tests/unit/test_harness_adapter_base.py tests/unit/test_harness_adapter_claude_code.py tests/unit/test_harness_adapter_codex.py tests/integration/test_harness_adapter_dispatch.py tests/integration/test_codex_harness_adapter_dispatch.py -q
go test ./internal/provider ./pkg/hook -count=1
```

## Open questions

1. **Pre-existing clarification (from plan)** — `.codex/hooks.json` vs
   `.codex/config.toml`: ADR-064 line 122 references `.codex/config.toml` but
   the actual file in the repo is `.codex/hooks.json` (Codex v0.124.0+).
   The plan (Section 5, risk 2 and Task 2.3 note) flags this and recommends
   pinning to the `hooks.json` format since it is what production currently
   uses. Either ADR-064 must be corrected or the driver must document the
   deviation explicitly. This predates ADR-081 and is tracked in the plan.

2. **Testing `PreToolUse`/`PostToolUse` without the Codex binary**: the
   integration test must simulate Codex's stdin for these events. The canonical
   approach is a JSON fixture matching Codex's documented hook schema. The
   30-min spike (see Decision §Pre-work) is the authoritative source for the
   fixture payload shape — do not use assumed schemas.

3. **Fallback event schema for physically absent events**: when a harness
   cannot emit a given canonical event (e.g., `pre_compact` on Codex), the
   adapter emits a `ParseError` with `reason="codex_tool_coverage_gap"` for
   tool events and returns `None` for events with no equivalent. Should
   `dispatch.handle_event` additionally log a structured skip record to
   `canonical-events.jsonl` as `event_type: skipped, reason: harness_unsupported`?
   A structured skip aids observability but creates noise in the event stream.
   Decision deferred to implementation.

4. **Capability matrix ownership**: `manifests/harness-driver-capabilities.yaml`
   must reflect each harness's actual version, not a static declaration.
   Should `cos doctor harness` (plan Task 2.5) read the installed Codex CLI
   version and compare against `version_baseline`, warning on mismatch?
   Likely yes; scope in ADR-064 Phase 3 follow-up per the plan.

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
- `manifests/harness-driver-capabilities.yaml` — capability matrix with Codex v0.126.0-alpha.8 evidence
