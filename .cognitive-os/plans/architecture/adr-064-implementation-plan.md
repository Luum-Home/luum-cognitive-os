# ADR-064 Implementation Plan

> Status: Drafted 2026-04-28. Source ADR: [`docs/adrs/ADR-064-harness-agnostic-cognitive-os.md`](../../adrs/ADR-064-harness-agnostic-cognitive-os.md). Reference adapter pattern: `lib/harness_adapter/`. Reference cross-harness hook: `hooks/session-summary-reminder.sh`.
>
> Authored by Plan agent (research-only). Persisted by orchestrator. P0 sequence below is what flips ADR-064 → Accepted.

## Implementation Status

| Task | Status | Completed | Notes |
|------|--------|-----------|-------|
| 2.1 — canonical hooks block in cognitive-os.yaml | ✅ DONE | 2026-04-30 | `cognitive-os.yaml > harness.hooks` block, 70 entries; test: `tests/unit/test_cognitive_os_yaml_harness_hooks.py` (15/15 pass) |
| 2.2 — settings-driver-claude-code.sh | ✅ DONE | 2026-04-30 | `scripts/_lib/settings-driver-claude-code.sh`; CC driver --check confirms byte-identical output |
| 2.3 — settings-driver-codex.sh | ✅ DONE | 2026-04-30 | `scripts/_lib/settings-driver-codex.sh`; improves .codex/hooks.json (adds PreToolUse:Bash + PostToolUse:Bash, expands SessionStart coverage) |
| apply-efficiency-profile.sh refactor | ✅ DONE | 2026-04-30 | Now delegates to both drivers; `--harness=claude-code\|codex\|all` flag added |
| 1.1 — codex.py adapter | pending | — | — |
| 1.2 — bare_cli.py adapter | pending | — | — |
| 1.3 — cursor.py / ci.py | pending | — | P2 |
| 2.4 — settings-driver-bare.sh | pending | — | P1, depends on 3.1 |
| 2.5 — cos doctor harness | pending | — | P1, depends on 2.2/2.3 |
| 3.1 — cos-skill list/describe | pending | — | — |
| 3.2 — cos-skill run | pending | — | — |
| 4.1 — cos-agent spawn | pending | — | — |
| Verification suite | pending | — | depends on 1.1, 3.2, 4.1 |

## Caveat

One ADR claim already needs revision: Codex IS partially wired today. `.codex/hooks.json` projects the same hook scripts CC uses, and `scripts/_lib/settings-driver.sh` already detects `codex` vs `claude`. This means Surface 2 is "partial," not "missing." See Section 1.

## Section 1 — Inventory of remaining surfaces

ADR-064 declares **four surfaces**. Surface 1 is shipped via ADR-033. Surfaces 2, 3, 4 remain.

### Surface 1 — Event capture (mostly shipped, minor extension work)
- **What it is**: Canonical event schema + per-harness adapters that translate native hook payloads into `CanonicalEvent` JSONL.
- **Current state**: **Shipped** for CC and Aider. Files: `lib/harness_adapter/base.py` (309 lines, defines `CanonicalEvent` registry + `HarnessAdapter` ABC), `lib/harness_adapter/claude_code.py`, `lib/harness_adapter/aider.py`, `lib/harness_adapter/aider_streaming.py`, `lib/harness_adapter/dispatch.py` (registry list at line 41–44 currently includes only CC and Aider), `lib/harness_adapter/tool_use_correlation.py`. Tests: `tests/unit/test_harness_adapter_{base,claude_code,aider}.py` and `tests/integration/test_harness_adapter_dispatch.py`.
- **Remaining work for ADR-064 closure**: New adapter files `lib/harness_adapter/codex.py`, `lib/harness_adapter/cursor.py`, `lib/harness_adapter/bare_cli.py`, `lib/harness_adapter/ci.py`. Each must be added to the `ADAPTERS` list in `dispatch.py:41`. ADR-064 lines 24–27 explicitly flag the Codex tool-coverage gap (Pre/Post emitted only for Bash as of v0.124.0).
- **Why it matters**: Without a Codex adapter, every hook fires on Codex but emits zero canonical events — dashboards show a flat line on the secondary harness even though work is happening.

### Surface 2 — Hook registration (partial, needs canonical→native projection)
- **What it is**: Canonical declaration of hooks under `cognitive-os.yaml > harness.hooks` plus per-harness "settings drivers" that project that block into `.claude/settings.json`, `.codex/hooks.json`, Cursor's format, and `cos-runner`'s registry.
- **Current state**: **Partial.**
  - `.claude/settings.json` is the active CC config (events: `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `PreCompact`, `PreToolUse`, `PostToolUse`, `Stop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`).
  - `.codex/hooks.json` exists and already mirrors most CC hooks for `SessionStart`, `UserPromptSubmit`, `Stop` (verified by inspection — same scripts, prefixed with `COGNITIVE_OS_HARNESS=codex` env exports).
  - A shared helper exists: `scripts/_lib/settings-driver.sh` — but it only does *harness detection*, not *canonical→native projection*. There is no `cognitive-os.yaml > harness.hooks` block (verify; ADR-064 specifies but file may not have section).
  - Prior art exists in `manifests/harness-driver-capabilities.yaml`: it records driver settings paths, native shapes, supported/limited/unsupported events, and parity policy. It is not the canonical hook source, but Task 2.1 should consume it as the capability input when defining the canonical hooks block.
  - The four ADR-064 drivers (`scripts/_lib/settings-driver-claude-code.sh`, `…-codex.sh`, `…-cursor.sh`, `…-bare.sh`) DO NOT EXIST.
  - Drift between `.claude/settings.json` and `.codex/hooks.json` is currently maintained by hand; nothing prevents them desynchronizing.
- **Why it matters**: Without canonical→native projection, every new hook must be added in N harness configs by hand. Today's `session-summary-reminder.sh` registration in `.codex/hooks.json` was a manual edit; that won't scale.

### Surface 3 — Skill invocation (`cos-skill` CLI)
- **What it is**: A CLI entrypoint that lets any harness invoke a skill the same way CC's `/skill-name` does today: `cos-skill run <name> [--args json]`, `cos-skill list`, `cos-skill describe <name>`. Reads `.md` frontmatter + body from `skills/`, composes the prompt via `scripts/compose_agent_prompt.py`, dispatches through ADR-062's LLM cascade.
- **Current state**: **Missing.**
  - No `cos-skill` binary exists in `bin/` (current contents: `cos`, `cos-dispatch`, `cos-test`).
  - `scripts/compose_agent_prompt.py` exists (the prompt composition logic is reusable).
  - Skills live in `skills/` as `.md` files with frontmatter and are discoverable on disk — the data layer is portable, only the entrypoint is missing.
- **Why it matters**: Outside CC's chat UI, today there is no way to run `verification-before-completion` or any skill from a CI job, a Codex session, or a bare shell. Without this, ADR-064's verification clause ("`cos-skill run verification-before-completion` produces byte-identical trust reports") is not even runnable.

### Surface 4 — Sub-agent spawning (`cos-agent`)
- **What it is**: `cos-agent spawn --task "..." --model <tier> [--providers ...]` — a flat, non-MCP, non-recursive sub-agent spawner that wraps `lib/openai_compatible_agent_loop.py` (ADR-062), persists its transcript to `.cognitive-os/agent-transcripts/<agent-id>.jsonl` in canonical event schema (ADR-033).
- **Current state**: **Missing.**
  - `lib/openai_compatible_agent_loop.py` exists per ADR-064 line 61; verify path before Task 4.1.
  - No `cos-agent` binary in `bin/`.
  - ADR-063 already constrains scope: NO MCP replication, NO TodoWrite semantics, NO `~/.claude/projects/*.jsonl` format, NO recursive sub-agents. `cos-agent` is the flat replica only.
- **Why it matters**: On Codex/bare-CLI/CI today, "spawn a sub-agent" silently does nothing. A skill that calls `Agent()` is a dead branch outside CC. With `cos-agent`, the same skill produces useful work on every harness.

## Section 2 — Task breakdown per surface

### Surface 1 — Adapter completion (3 tasks)

**Task 1.1 — `lib/harness_adapter/codex.py`** (1 session, ~3h)
- Acceptance criteria:
  1. `pytest tests/unit/test_harness_adapter_codex.py` (new) passes ≥10 cases covering SessionStart, UserPromptSubmit, PreToolUse:Bash, PostToolUse:Bash, Stop. Verification: `pytest tests/unit/test_harness_adapter_codex.py -v`.
  2. `CodexAdapter.detect_harness` returns `HarnessName.CODEX` for payloads carrying `codex_session_id` or env-tagged `COGNITIVE_OS_HARNESS=codex`, else `None`. Verification: covered by unit test.
  3. The adapter handles the documented gap (Codex emits Pre/Post only for Bash per ADR-064 lines 24–27): non-Bash tools produce a `ParseError` canonical event with `reason="codex_tool_coverage_gap"` rather than silent skip. Verification: `grep -c "codex_tool_coverage_gap" lib/harness_adapter/codex.py` ≥ 1.
  4. Added to `dispatch.py:41` `ADAPTERS` list; existing CC dispatch tests still pass. Verification: `pytest tests/integration/test_harness_adapter_dispatch.py -v`.
  5. New `HarnessName.CODEX = "codex"` enum value in `base.py:30`. Verification: `python -c "from lib.harness_adapter.base import HarnessName; assert HarnessName.CODEX.value == 'codex'"`.
- Files touched: `lib/harness_adapter/codex.py` (new), `lib/harness_adapter/base.py` (enum addition), `lib/harness_adapter/dispatch.py` (registry), `tests/unit/test_harness_adapter_codex.py` (new).
- Files NOT touched: `claude_code.py`, `aider.py`, all `.claude/` and `.codex/` configs.

**Task 1.2 — `lib/harness_adapter/bare_cli.py`** (0.5 session, ~2h)
- Acceptance criteria:
  1. Adapter parses `cos-runner` invocation events (a JSON shape TBD in Task 3.1; this task may produce a stub that gates on Task 3.1).
  2. `BareCliAdapter.detect_harness` returns `HarnessName.BARE_CLI` when payload has `harness: bare_cli`. Verification: unit test.
  3. Emits `AgentStart` + `AgentEnd` per skill invocation, optionally `ToolUse` events if cos-runner instruments. Verification: unit test fixture + assertion.
- Files touched: `lib/harness_adapter/bare_cli.py` (new), `base.py` (enum), `dispatch.py`, `tests/unit/test_harness_adapter_bare_cli.py`.
- Dependency: blocks on Task 3.1 finalizing the cos-runner stdin schema.

**Task 1.3 — `lib/harness_adapter/cursor.py` and `ci.py`** (1 session each, deferrable)
- Same shape as 1.1 but P2. Cursor's transcript format must be reverse-engineered from current Cursor exports; CI adapter wraps GitHub Actions step output. Files: `cursor.py`, `ci.py`, two new test files. Cursor unblocked only when operator commits to it (ADR-064 open question 1).

### Surface 2 — Settings drivers (5+1 tasks)

**Task 2.1 — Define canonical hooks block in `cognitive-os.yaml`** (0.25 session, ~1h)
- Inputs:
  - `manifests/harness-driver-capabilities.yaml` for driver settings paths, native settings shapes, supported event coverage, limited event caveats, and unsupported-event policy.
- Acceptance criteria:
  1. `cognitive-os.yaml` gains a `harness.hooks` block listing every hook currently registered in `.claude/settings.json` (verify via `python3 -c "import json; print(len(json.load(open('.claude/settings.json'))['hooks']))"`).
  2. Each entry has `id`, `event` (canonical name from `before_tool_call|after_tool_call|before_agent_spawn|after_agent_complete|on_session_start|on_session_end|on_user_prompt`), `script`, optional `matcher`.
  3. `yamllint cognitive-os.yaml` passes.
  4. Documented mapping between canonical event names and CC's native names (`PreToolUse → before_tool_call`, etc.) in a comment block at the top of the section.
- Files touched: `cognitive-os.yaml` only.

**Task 2.2 — `scripts/_lib/settings-driver-claude-code.sh`** (1 session, ~3h)
- Reads `cognitive-os.yaml > harness.hooks`, projects to `.claude/settings.json`, idempotent.
- Acceptance criteria:
  1. Running `bash scripts/_lib/settings-driver-claude-code.sh` against the canonical block produces a `.claude/settings.json` byte-identical to the current committed file (modulo key ordering). Verification: diff against current settings.json after sorting keys.
  2. Adding a new entry under `cognitive-os.yaml > harness.hooks` and re-running the driver inserts it correctly. Verification: integration test.
  3. Driver respects `.claude/settings.local.json` overrides (does not overwrite). Verification: shell test.
  4. `bash scripts/_lib/settings-driver-claude-code.sh --check` exits 0 when in sync, 1 when drift detected. Verification: `make doctor-harness` (Task 2.5) consumes this.
  5. CC regression: full hook chain still fires after projection (smoke). Verification: `bash hooks/self-install.sh && claude --check`.
- Files touched: `scripts/_lib/settings-driver-claude-code.sh` (new); `.claude/settings.json` may be regenerated.

**Task 2.3 — `scripts/_lib/settings-driver-codex.sh`** (1 session, ~3h)
- Acceptance criteria: same shape as 2.2, target `.codex/hooks.json`. Notes:
  1. Codex hook events to map: `SessionStart` (matcher: `startup`), `UserPromptSubmit` (matcher: `prompt`), `Stop` (matcher: `shutdown`) — observed in `.codex/hooks.json`. ADR-064 line 122 says `.codex/config.toml`; **ADR clarification needed**: actual format is `.codex/hooks.json` per Codex v0.124.0+. Plan assumes JSON.
  2. Driver MUST inject `export COGNITIVE_OS_HARNESS=codex` and `export COGNITIVE_OS_PROJECT_DIR=…` wrappers per the existing pattern in `.codex/hooks.json` lines 7–11.
  3. Re-running against current canonical config produces byte-identical `.codex/hooks.json` (after sort).
- Files touched: `scripts/_lib/settings-driver-codex.sh` (new); `.codex/hooks.json` regenerated.

**Task 2.4 — `scripts/_lib/settings-driver-bare.sh`** (0.5 session)
- Generates `.cognitive-os/cos-runner-hooks.json` consumed by Task 3.1. P1 — needed by bare-CLI verification.

**Task 2.5 — `cos doctor harness` drift verifier** (0.5 session)
- Acceptance criteria:
  1. New subcommand `bin/cos doctor harness` runs each driver in `--check` mode, reports drift per harness, exits non-zero if any drift.
  2. Documentation in `docs/architecture/cross-harness-authoring.md` updated to include the doctor invocation.
- Files touched: `bin/cos`, `docs/architecture/cross-harness-authoring.md`. Depends on 2.2/2.3/2.4.

**Task 2.6 (optional, P2) — `scripts/_lib/settings-driver-cursor.sh`** — TBD pending operator commitment.

### Surface 3 — `cos-skill` CLI (3 tasks)

**Task 3.1 — `bin/cos-skill` core: `list` + `describe`** (0.5 session, ~2h)
- Acceptance criteria:
  1. `bin/cos-skill list` enumerates every `skills/*.md` file with frontmatter `description`. Verification: `bin/cos-skill list | wc -l` ≈ count of skills/*.md.
  2. `bin/cos-skill describe <name>` prints frontmatter + first 20 body lines.
  3. JSON output mode: `--json` flag emits machine-readable output. Verification: `bin/cos-skill list --json | python3 -c "import sys,json; json.load(sys.stdin)"`.
  4. Decision recorded for ADR-064 open question 2 (cache vs no cache): `--cache` flag opt-in; default no cache for now.
  5. Idempotent and stateless.
- Files touched: `bin/cos-skill` (new); `scripts/cos_skill.py` (new helper, optional).

**Task 3.2 — `bin/cos-skill run <name>` end-to-end** (1 session, ~4h)
- Acceptance criteria:
  1. Reuses `scripts/compose_agent_prompt.py` for prompt assembly (no duplication of compose logic).
  2. Dispatches through ADR-062's `lib/openai_compatible_agent_loop.py` (verify path).
  3. Emits canonical events to `.cognitive-os/metrics/canonical-events.jsonl` via `lib/harness_adapter/dispatch.py` with `harness: bare_cli` payload.
  4. Reference skill verification: `bin/cos-skill run verification-before-completion` produces a trust report byte-identical to CC's invocation modulo timestamps and `agent_id`. Verification command: `diff <(bin/cos-skill run verification-before-completion --canonicalize) <(claude exec verification-before-completion --canonicalize)`.
  5. Exit status 0 on skill success, non-zero on skill failure.
- Files touched: `bin/cos-skill`, `scripts/cos_skill.py`. May import but not modify `lib/harness_adapter/`, `scripts/compose_agent_prompt.py`.
- Depends on: Task 1.2 (bare_cli adapter for canonical event emission).

**Task 3.3 — `bin/cos-skill` harness-native shortcuts** (0.5 session, P1)
- Codex: register `@skill-name` → `cos-skill run skill-name` mapping (mechanism TBD per Codex command extension API).
- Cursor: P2.

### Surface 4 — `cos-agent` (2 tasks)

**Task 4.1 — `bin/cos-agent spawn` minimum-viable** (1 session, ~4h)
- Acceptance criteria:
  1. `bin/cos-agent spawn --task "summarize this file" --model haiku` returns the agent's final message to stdout.
  2. Wraps `lib/openai_compatible_agent_loop.py` directly; does not re-implement the loop. Verification: `grep "openai_compatible_agent_loop" bin/cos-agent` ≥ 1.
  3. Persists transcript to `.cognitive-os/agent-transcripts/<agent-id>.jsonl` in canonical event schema. Verification: `python3 -c "import json; [json.loads(l) for l in open('.cognitive-os/agent-transcripts/<id>.jsonl')]"` succeeds and entries match `CanonicalEvent` registry.
  4. Honors ADR-063 negative scope: no MCP, no TodoWrite, no recursive sub-agents (max depth = 1, enforced by env guard).
  5. Exit code reflects agent success/failure, not just dispatch success.
- Files touched: `bin/cos-agent` (new), `scripts/cos_agent.py` (new).
- Files NOT touched: `lib/openai_compatible_agent_loop.py` (must remain harness-neutral; consume only).

**Task 4.2 — `cos-agent` reference smoke** (0.5 session)
- Add `tests/integration/test_cos_agent_smoke.py` running a 1-shot fixture against a stubbed provider; assert canonical events emitted and transcript file shape.

## Section 3 — Verification suite design

### Operational definition of "harness-agnostic"
For a given reference skill `S`, executing `S` on harness `H1` and harness `H2` MUST produce a canonical event JSONL stream `E1, E2` such that:
- `len(E1) == len(E2)` (same number of canonical events, modulo retries).
- For every index `i`, `E1[i].event_type == E2[i].event_type`.
- The set of `(event_type, tool_name, exit_status)` tuples is identical between runs.
- Trust reports — when produced — are byte-identical after canonicalization (strip timestamps, agent_ids, durations, absolute paths).

This definition treats Codex's tool-coverage gap (ADR-064 lines 24–27) as a known, scoped exception: a `ParseError` canonical event with `reason="codex_tool_coverage_gap"` is emitted instead of `ToolUse` for non-Bash tools on Codex. The verification suite asserts presence of these markers rather than full parity until Codex closes the gap.

### Minimal test fixture
A new reference skill `skills/__contracts__/canonical-event-emitter.md` (P0) that:
1. Calls `Bash` once (covered on every harness).
2. Calls `Read` once (covered on CC, not on Codex pre-gap-close → produces `ParseError`).
3. Emits a `PROGRESS:` marker (covered by `aider_streaming` and CC).
4. Returns a fixed string (so trust reports are deterministic).

### Test placement
- `tests/contracts/` — already exists in the tree. New file: `tests/contracts/test_harness_parity.py`. Rationale: this directory is the conventional home for cross-implementation contract tests.
- `tests/integration/test_harness_agnostic_skill_run.py` — the file ADR-064 line 19 specifies. Parameterized over `(claude_code, bare_cli, codex)` using the canonical-event-emitter fixture.
- `scripts/demo-portability-proof.sh` — ADR-mandated; runs the reference skill across all enabled harnesses and diffs canonical events.

### Harnesses in scope
| Harness | Scope today | Verification level |
|---|---|---|
| Claude Code | full | full canonical-event parity (reference) |
| Aider | partial | passive file-watcher events; no Bash-tool gap |
| Codex | new (Task 1.1) | Bash-only canonical events; non-Bash tools logged as `codex_tool_coverage_gap` ParseError |
| Bare CLI | new (Task 1.2) | full when `cos-runner` invokes a skill |
| CI | new (Task 1.3) | smoke only (Phase 4) |
| Cursor | deferred | TBD — open question 1 |

## Section 4 — Sequencing

| Order | Task | Tag | Deps |
|---|---|---|---|
| 1 | 2.1 — canonical hooks block in cognitive-os.yaml | P0 | none |
| 2 | 2.2 — settings-driver-claude-code.sh | P0 | 2.1 |
| 3 | 2.3 — settings-driver-codex.sh | P0 | 2.1 |
| 4 | 1.1 — codex.py adapter | P0 | none (parallel with 2.x) |
| 5 | 3.1 — cos-skill list/describe | P1 | none |
| 6 | 1.2 — bare_cli.py adapter | P0 | 3.1 stdin schema |
| 7 | 3.2 — cos-skill run | P0 | 1.2, 3.1 |
| 8 | 4.1 — cos-agent spawn | P0 | 1.2 |
| 9 | Verification suite (tests/contracts/test_harness_parity.py + scripts/demo-portability-proof.sh + tests/integration/test_harness_agnostic_skill_run.py) | P0 | 1.1, 3.2, 4.1 |
| 10 | 2.4 — settings-driver-bare.sh | P1 | 3.1 |
| 11 | 2.5 — cos doctor harness | P1 | 2.2, 2.3 |
| 12 | 3.3 — codex `@skill-name` shortcut | P1 | 3.2 |
| 13 | 4.2 — cos-agent smoke | P1 | 4.1 |
| 14 | 1.3 — ci.py adapter | P2 | 1.2 |
| 15 | 2.6 — settings-driver-cursor.sh | P2 | 2.1 |
| 16 | cursor.py adapter | P2 | 2.6 |

**P0 to flip ADR-064 → Accepted**: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 4.1, and the verification suite (item 9). Roughly **7–9 sessions** of work, in line with ADR-064's 10–15 estimate but trimmed because ADR-033 already paid down a chunk of Surface 1 and `.codex/hooks.json` already exists as a manual projection.

## Section 5 — Risks and unknowns

1. **Codex tool-coverage gap is moving** (ADR-064 lines 24–27). Plan freezes today's behavior (Bash-only Pre/Post). If Codex ships expanded tool hooks before Phase 3 lands, the `codex_tool_coverage_gap` ParseError emission needs revisiting and the parity suite needs to widen its expectations.
2. **ADR clarification needed: Codex config file format**. ADR-064 line 122 says `.codex/config.toml`; the repo has `.codex/hooks.json`. Driver design must confirm which Codex versions accept which file. Recommend pinning to the `hooks.json` format since it is what production currently uses.
3. **ADR clarification needed: Cursor priority** (open question 1). Without operator commitment, Tasks 1.3-cursor / 2.6 / cursor-shortcut are P2 indefinitely. Recommend deferring until at least one operator workflow on Cursor exists.
4. **Skill discovery cache trade-off** (open question 2 in ADR). Plan defaults to no cache (slower but no drift risk). If `cos-skill list` is called repeatedly in a tight loop (CI), revisit and add `--cache` opt-in.
5. **Hook concurrency on `cos-runner`** (open question 4). CC serializes hooks per event; bare-CLI may not. Plan does not yet design a lock file. Risk: double-write to canonical-events.jsonl. Mitigation: add `flock` around `dispatch.handle_event`'s emit step in `cos-runner`.
6. **Settings-driver bi-directionality** (open question 5). Plan only does canonical → native. If a user manually edits `.claude/settings.json`, drift is detected by 2.5 (`cos doctor harness`) but not auto-repaired. Acceptable for v1; revisit in Phase 4.
7. **`lib/openai_compatible_agent_loop.py` shape unknown**. ADR-064 line 61 references it; the planner did not verify the file exists or expose its API. Task 4.1 may need a preceding 0.5h spike to confirm the loop's entry point and adjust the wrapper accordingly.
8. **Web evidence for Codex/Cursor hook vocabularies** (ADR status review 2026-04-27) is not source-of-truth. Before Task 1.1 lands, run a 30-min spike that captures actual Codex hook payloads (instrument an existing `.codex/hooks.json` script to dump stdin) so the adapter is built against real shapes, not assumed ones.
9. **Trust report canonicalization is undefined**. Acceptance criterion 3.2.4 ("byte-identical modulo timestamps and agent IDs") needs a `--canonicalize` flag that strips those — undocumented today. **ADR clarification needed**: define the canonicalization algorithm explicitly before writing the parity test.
10. **`.codex/hooks.json` already partially mirrors `.claude/settings.json`** but without canonical authority. Until Task 2.1 + 2.3 land, every hook addition must be made in two files by hand; expect ongoing drift bugs.

## Critical files for implementation
- `lib/harness_adapter/base.py`
- `lib/harness_adapter/dispatch.py`
- `scripts/_lib/settings-driver.sh`
- `cognitive-os.yaml`
- `.codex/hooks.json`
- `scripts/compose_agent_prompt.py`
- `lib/openai_compatible_agent_loop.py` (verify exists)
