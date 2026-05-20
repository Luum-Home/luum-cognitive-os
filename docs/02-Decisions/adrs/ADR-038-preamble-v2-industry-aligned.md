---
adr: 38
title: 'Preamble v2: Industry-Aligned Contract'
status: accepted
implementation_status: implemented
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files:
- templates/agent-preamble.md
- templates/agent-planning.md
- lib/agent_input_validator.py
- lib/trust_report_schema.py
- lib/trust_report_parser.py
- lib/prompt_builder.py
- hooks/subagent-input-schema-validator.sh
- hooks/trust-score-validator.sh
- hooks/task-completed.sh
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-038 — Preamble v2: Industry-Aligned Contract

> Originally drafted in `.cognitive-os/pending-tasks/adr-038-preamble-v2-industry-aligned.md`; canonical location is `docs/02-Decisions/adrs/`.

## Status

Accepted — implemented through Wave 4 as of 2026-05-20.

Close the 8 gaps identified in orchestrator research (2026-04-20, engram topic `research/orchestrator-prompt-composition-survey`).

## Gaps addressed (from industry comparison)
1. Typed input variable contract (no schema for fields sub-agent receives)
2. Token/context budget explícito (only `max 50 tool calls`, no `max_tokens` or layers)
3. Typed output schema (TRUST_REPORT is text convention, not Pydantic/JSON)
4. Iteration cap (reasoning cycles, separate from tool-call cap)
5. Escalation routing spec (text-only, no typed handoff like AutoGen)
6. Separate planning template (smolagents-unique, enables pre-computation)
7. Retry diversity protocol (each retry must use different approach)
8. Memory scope declaration (SEARCH_PERMISSION binary, no tiers)

## Rollout waves

### Wave 1 (~3h, sonnet) — quick wins
- #4 `max_reasoning_cycles` field
- #7 retry-approach hashing + enforcement
- #8 memory tiers: `public | project | personal | none`

### Wave 2 (~4h, sonnet) — medium
- #1 `input_schema: {field: type}` in preamble
- #2 4-layer context budget (static|turn|user|cache) per ADK model

### Wave 3 (~1 session, opus) — breaking
- #3 Pydantic `TrustReport` schema, validate on completion, reject malformed
- #5 Typed handoff: `{handoff: {to, context, reason}}`

### Wave 4 (~2h, optional)
- #6 Separate planning template (smolagents pattern)

## Effort
~2-3 sessions total.

## Acceptance per wave
Each wave has its own AC; full v2 preamble when all 4 merged.

## Dependencies
- Wave 3 touches ADR-033 harness_adapter base schema (breaking)
- Wave 4 optional — only if precomputation benefit justifies complexity

---

## Wave 2 — Implemented (2026-04-30)

Closed Gap #1 (typed input schema) and Gap #2 (4-layer context budget).

### Gap #1 — Typed input variable contract (`INPUT SCHEMA:`)

**Problem**: Sub-agents had no machine-readable schema for the fields they receive.
Peer frameworks (Semantic Kernel, LlamaIndex) declare typed `input_variables[]`.

**Solution**: `templates/agent-preamble.md` now contains an `INPUT SCHEMA:` block
(lines added after the CONTEXT BUDGET block) that:
- Documents the canonical fields (`task_description`, `acceptance_criteria`,
  `blast_radius`, `working_dir`) with types and required/optional markers.
- States the validation rule: missing `required` fields → `ESCALATION:` and stop.
- Allows per-launch custom fields declared by the orchestrator.

No library changes required for Wave 2; enforcement is convention-based until
Wave 3 ships Pydantic validation.

### Gap #2 — 4-layer context budget (`CONTEXT BUDGET:`)

**Problem**: Only `MAX 50 tool calls` existed. Google ADK uses 4 layers:
static / turn / user / cache.

**Solution**:
- `cognitive-os.yaml` — new top-level `context_budget:` block with four integer keys:
  `static_max_tokens: 4000`, `turn_max_tokens: 8000`,
  `user_max_tokens: 12000`, `cache_max_tokens: 32000`.
- `templates/agent-preamble.md` — new `CONTEXT BUDGET:` block surfaces these
  values to sub-agents and instructs them to summarise + save to Engram when
  context grows large.

Enforcement (Pydantic, hard stop) is **out of scope** — deferred to Wave 3.

### Verification

```
grep -c "INPUT SCHEMA" templates/agent-preamble.md   # >= 1
grep -c "CONTEXT BUDGET" templates/agent-preamble.md  # >= 1
grep -c "context_budget" cognitive-os.yaml            # >= 1
pytest tests/integration/test_preamble_v2_wave2.py -v # 4+ pass
pytest tests/integration/test_preamble_v2_wave1.py -v # all pass (no regression)
```

### Files changed
- `templates/agent-preamble.md` — INPUT SCHEMA block + CONTEXT BUDGET block
- `cognitive-os.yaml` — `context_budget:` section (before `sessions:`)
- `docs/02-Decisions/adrs/ADR-038-preamble-v2-industry-aligned.md` — this section
- `tests/integration/test_preamble_v2_wave2.py` — new test file (4 tests)
---

## Wave 3 — Implemented (2026-05-20)

Closed Gap #3 (typed TrustReport output schema) for agent completions. Gap #5
(typed handoff) remains covered by existing escalation/handoff conventions and is
not expanded by this ADR slice.

### Gap #3 — Pydantic TrustReport schema

**Solution**:
- `lib/trust_report_schema.py` defines the canonical `TrustReport` Pydantic v2 model.
- `lib/trust_report_parser.py` parses the ADR-038 `TRUST_REPORT:` header and validates score range, status band consistency, and `UNCERTAINTIES >= 1`.
- Legacy `TRUST REPORT:` blocks remain best-effort parseable for migration compatibility, but new agents must emit the machine-readable header.

### Verification

```bash
python3 -m pytest tests/unit/test_trust_report_schema.py tests/unit/test_trust_report_parser.py -q
```

## Wave 4 — Implemented (2026-05-20)

Closed Gap #6 (separate planning template) and wired the Wave-3 TrustReport
parser into runtime hooks.

### Gap #6 — Separate planning template

**Solution**:
- `templates/agent-planning.md` defines a plan-only output contract with slices,
  assumptions, acceptance criteria, risks, and a required `TRUST_REPORT` block.
- `lib/prompt_builder.py` injects the planning template only for planning/design/
  architecture/research-first task types, keeping implementation prompts lean.

### Hook wiring and grading policy

**Solution**:
- `hooks/trust-score-validator.sh` now calls `lib.trust_report_parser` instead
  of extracting scores with shell regexes. Structured malformed reports block
  with exit 2; missing reports remain advisory to preserve graceful degradation.
- Legacy reports are accepted with a warning and logged with `format=legacy`. This
  resolves the fallback question conservatively: compatibility is allowed, but
  the grading signal records that the agent did not use the ADR-038 header.
- `hooks/task-completed.sh` uses the same parser in production/maintenance phases
  so malformed TrustReports cannot satisfy the completion gate.
- `cognitive-os.yaml` documents the Codex projection gap for `PostToolUse[Agent]`: 
  the hook is wired for Claude Code and shell tests, while Codex parity awaits
  upstream Agent PostToolUse coverage.

### Verification

```bash
python3 -m pytest tests/hooks/test_trust_score_validator.py tests/hooks/test_agent_teams_hooks.py::TestTaskCompletedHook -q
python3 -m pytest tests/unit/test_prompt_integration.py -q
```
