# Context Rot and Token Budget Controls

> Current map of how Cognitive OS prevents long-session context degradation,
> token multiplication, overgrown startup instructions, and compaction data loss.

## Why this document exists

Long coding-agent sessions accumulate prompt history, tool output, retrieved
context, and startup instructions. Even when a model supports a large context
window, quality can degrade as the window fills: the agent may forget earlier
constraints, over-weight stale failed attempts, contradict itself, or spend more
on every subsequent turn. Cognitive OS treats this as an operational risk, not
as a model quirk.

This document answers one operator question: **how do we avoid context rot and
unbounded token tax today, and where are the remaining gaps?**

## Operator checklist

Use this checklist before claiming Cognitive OS is protected against context
rot or token waste:

1. Measure current prompt/context budget:
   `scripts/cos-context-budget-report --json`.
2. Measure startup hook surface:
   `scripts/cos-session-start-budget --profile core --json` and
   `scripts/cos-session-start-budget --profile current --json`.
3. Keep mandatory startup instruction files compact. In this repo,
   `AGENTS.md` is part of the real preamble tax and is included in the core
   preamble budget.
4. Prefer progressive context loading: compact rule index, compact skill
   catalog, targeted file reads, and query-tailored context injection.
5. Save durable state before context pressure becomes urgent: Engram memories,
   session summaries, local changelogs, and anchored summaries.
6. Convert noisy inputs, especially HTML and large copied content, into
   LLM-ready text before feeding them to the agent.
7. Treat failed attempts as contamination: diagnose and escalate instead of
   repeating the same retry loop.

## Current controls by risk

| Risk from long sessions | Current COS control | Primary files | Current status |
|---|---|---|---|
| Silent token growth per prompt | Runtime budget accounting | `lib/context_budget.py`, `hooks/context-budget-meter.sh`, `hooks/_lib/context_budget_lib.sh`, `docs/02-Decisions/adrs/ADR-186-context-budget-enforcement.md` | Implemented and registered for Claude settings; metrics available in `.cognitive-os/metrics/context-budget.jsonl`. |
| Large static startup preamble | Runtime diet and preamble accounting | `scripts/cos-session-start-budget`, `scripts/session_start_budget.py`, `docs/04-Concepts/architecture/session-start-runtime-diet.md`, `scripts/cos_preamble_budget.py` | Implemented; core profile is small, maintainer/current profile may remain heavier for self-hosting. |
| Loading every rule/skill by default | Progressive context loading | `rules/context-optimization.md`, `skills/CATALOG-MICRO.md`, `skills/CATALOG-COMPACT.md`, `rules/RULES-COMPACT.md`, `lib/context_diet.py`, `hooks/context-diet.sh` | Active in Claude Code Agent launches; micro catalog is Level-1, compact catalog is Level-1.5, and Codex degrades safely when Agent payloads are unavailable. |
| Irrelevant ADR/rule/context injection | Query-tailored context | `hooks/query-tailored-context-inject.sh`, `lib/context_injector.py`, `docs/02-Decisions/adrs/ADR-040-query-tailored-context-injection.md` | Implemented and registered for Agent-like launches in Claude settings. |
| Forgetting decisions before compaction | Pre-compaction flush and durable summaries | `hooks/pre-compaction-flush.sh`, `lib/anchored_summarizer.py`, `hooks/session-summary-reminder.sh`, `docs/04-Concepts/architecture/memory-lifecycle.md` | Implemented; backed by behavior, contract, and integration tests. |
| Re-discovering known facts | Memory-first retrieval | `hooks/memory-prefetch.sh`, `lib/memory_manager.py`, Engram MCP tools, `rules/token-economy.md` | Implemented as best-effort memory prefetch and required agent behavior. |
| Failed retries polluting the active thread | Escalation and rollback planning | `rules/agent-escalation.md`, `rules/auto-rollback.md`, `hooks/auto-rollback-trigger.sh` | Doctrine and hooks exist; this is not equivalent to Claude `/rewind`, but it reduces repeated failed-loop contamination. |
| HTML/web pages pasted directly into context | LLM-ready web extraction | `lib/web_crawler.py`, `skills/web-crawler/SKILL.md` | Implemented for web pages via Crawl4AI when installed, with stdlib fallback. |
| Sub-agent result bloat | Compact result contracts | `docs/04-Concepts/architecture/token-efficient-agent-messaging.md` | Documented; use bounded digests and JSONL/event extraction for large agent output. |

## Budget layers

ADR-186 activates the ADR-038 budget layers from `cognitive-os.yaml`:

| Layer | Default limit | Meaning |
|---|---:|---|
| `static` | 4,000 tokens | Preamble, known traps, working directory, injected static context. |
| `turn` | 8,000 tokens | Per tool-use round. |
| `user` | 12,000 tokens | Accumulated user-facing task content. |
| `cache` | 32,000 tokens | MCP, Engram, and retrieval cache context. |

The first implementation estimates tokens with `len(text) / 4` unless a real
tokenizer is explicitly enabled. This makes the system portable and avoids a
mandatory dependency for hook execution.

## Current measurement snapshot

The following local commands were run during the 2026-05-09 review that created
this document:

```bash
wc -l AGENTS.md
scripts/cos-session-start-budget --profile current --json
scripts/cos-session-start-budget --profile core --json
scripts/cos-context-budget-report --json
```

Observed state after the 2026-05-22 token-tax hardening pass:

| Measurement | Result | Interpretation |
|---|---:|---|
| `AGENTS.md` length | 199 lines after hardening | Under the external 200-line heuristic while still preserving the mandatory instruction content. |
| Current/maintainer SessionStart hooks | 20 SessionStart hooks | Meets the maintainer budget while preserving runtime safety barriers; non-critical startup probes were kept lazy/opt-in. |
| Core SessionStart hooks | 4 hooks | Passes the core budget of 5 hooks. |
| Team SessionStart hooks | 6 hooks | Passes the team budget of 8 hooks. |
| Preamble budget | core/team/maintainer/lab PASS | `cos-preamble-budget` now charges actual projected startup primitives and the compact runtime config projection, not the full lifecycle inventory. |
| Runtime config context | ~2.2K tokens | `.cognitive-os/generated/runtime-config.compact.yaml` replaces full `cognitive-os.yaml` (~18K token estimate) for preamble budgeting. |
| Skill Level-1 catalog | ~3.6K tokens | `skills/CATALOG-MICRO.md` is the always-load index; `CATALOG-COMPACT.md` moved to Level 1.5. |
| Context budget entries | 385 entries in latest 30d report | Enough recent local data for a first budget-health view. |
| Budget pass rate | 100% PASS | User/context payloads are within configured budget. |
| Budget warnings | 0 WARN, 0 BLOCK | No recent hard overrun. |
| `context-budget-meter` p99 | Historical report showed 140.6 ms before stdlib fast-path | The hook now avoids project imports on the normal path; keep measuring until old samples age out. |
| `subagent-context-injector` average ratio | 0.5982 | Sub-agent static context fits the configured budget but consumes a meaningful share. |

The key distinction: **consumer core is small; maintainer self-hosting is heavier
by design**. Do not use the active maintainer hook count as proof that a
consumer install is bloated. Use the `projection_source` and profile fields from
`cos-session-start-budget`.

## How each common anti-pattern is handled

### “Every message gets more expensive”

Handled by budget accounting, compact startup profiles, context-diet doctrine,
and token-economy rules. Operators should inspect
`.cognitive-os/metrics/context-budget.jsonl` via
`scripts/cos-context-budget-report --json` instead of guessing.

### “The instruction file charges tokens every session”

Handled by startup/runtime diet work and preamble budget checks. `AGENTS.md` is
not free: it is mandatory session context and must remain compact. ADR-044 also
records a startup-slim strategy: compress global instructions into short
pointers and load expanded protocols on demand. Prior work completed skill
`summary_line` migration and compact catalog regeneration, while slash-command
expansion remained a separate unblock item.

### “Context rot near the window limit”

Handled by `rules/context-management.md` thresholds and the pre-compaction
flush path:

- 50%: efficiency mode.
- 70%: save and summarize.
- 85%: stop new work and hand off.
- 95%: pre-compaction emergency flush.

The durable safety net is `hooks/pre-compaction-flush.sh` plus Engram/session
summary discipline. `hooks/context-watchdog.sh` is projected as a real PostToolUse hook in the Claude settings generated by the maintainer profile. It emits one-shot warnings so the default projection gains protection without repeating warnings on every later tool call.

### “Use rewind instead of retrying failed attempts”

Cognitive OS does not currently expose a literal `/rewind` primitive. The nearest
controls are escalation and rollback planning: agents should stop mechanical
retry loops, emit a diagnosis, and preserve or revert safely with human approval
when destructive git operations are involved.

### “Convert PDFs and HTML to Markdown first”

HTML/web extraction is covered by `lib/web_crawler.py` and the web-crawler skill.
PDF-to-Markdown is now covered by `scripts/cos-document-ingest` and `lib/document_ingest.py`. `hooks/document-ingest-guard.sh` blocks direct Read-tool access to `.pdf` files and routes operators through the Markdown conversion path before model-context ingestion.

## Known gaps and hardening candidates

| Gap | Why it matters | Candidate fix |
|---|---|---|
| `context-budget-meter` p99 needs post-change calibration | Old metrics include project-import samples and can overstate current hook cost. | Keep the stdlib-only fast path, let old samples age out, and re-run `scripts/cos-context-budget-report --json`. |
| Early checkpoint needs ongoing calibration | COS now emits a 15% lightweight checkpoint, but model/context-size differences may require tuning. | Keep `CONTEXT_WATCHDOG_THRESHOLD_*` overrides and monitor `context-watchdog.jsonl`. |
| PDF ingestion coverage is first-pass | The primitive handles text PDFs and optional local extractors; scanned/OCR-only PDFs still need an OCR extension. | Add OCR only behind an explicit dependency/license review. |
| No literal `/rewind` equivalent | Failed turns remain in chat context unless the harness supports rewind. | Add a portable “attempt reset” workflow: checkpoint, summarize failure, open fresh subtask/session, and quarantine failed-output context. |
| Codex Agent lifecycle remains partial | Codex may not expose the same Agent/SubagentStart payloads as Claude Code. | Keep `context-diet.sh` and subagent budgeting as safe no-op/partial projections in Codex, and prefer prompt-time/task-level adapters when Codex emits richer events. |

## Verification commands

Run these after changing context, memory, startup, or token-related primitives:

```bash
bash -n hooks/context-budget-meter.sh hooks/pre-compaction-flush.sh hooks/context-watchdog.sh hooks/token-budget-monitor.sh
python3 -m pytest tests/unit/test_context_budget.py -q
python3 -m pytest tests/contracts/test_context_budget_enforcement.py -q
python3 -m pytest tests/contracts/test_context_budget_hook_wiring.py -q
python3 -m pytest tests/behavior/test_compaction_protection.py -q
python3 -m pytest tests/contracts/test_memory_lifecycle_docs.py -q
scripts/cos-context-budget-report --json
scripts/cos-session-start-budget --profile core --json
scripts/cos-session-start-budget --profile team --json
scripts/cos-session-start-budget --profile maintainer --json
scripts/cos-preamble-budget --profile core
scripts/cos-preamble-budget --profile team
scripts/cos-preamble-budget --profile maintainer
```

For cross-harness memory proof, use:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-memory-lifecycle.sh --harness codex
```

## Acceptance criteria for this control surface

A change that claims to improve context-rot or token-budget protection should
satisfy at least one of these measurable outcomes:

1. `scripts/cos-context-budget-report --json` keeps PASS rate at or above 90%,
   WARN rate at or below 8%, BLOCK rate at or below 2%, and override use below
   5%.
2. `context-budget-meter` p99 is below its documented target or the target is
   recalibrated with evidence.
3. `scripts/cos-session-start-budget --profile core --json` stays within the
   core SessionStart hook budget.
4. Mandatory startup instruction files stay compact or are included in a
   documented preamble budget.
5. Compaction recovery tests continue to prove state survives pre-compaction
   flush and post-compaction retrieval.
6. Large external artifacts are converted, summarized, or rejected before being
   injected into active model context; PDFs must pass through `scripts/cos-document-ingest`.

## Related documents

- `docs/02-Decisions/adrs/ADR-016-context-diet.md`
- `docs/02-Decisions/adrs/ADR-040-query-tailored-context-injection.md`
- `docs/02-Decisions/adrs/ADR-044-context-payload-slimming.md`
- `docs/02-Decisions/adrs/ADR-047-session-lifecycle-management.md`
- `docs/02-Decisions/adrs/ADR-078-mid-task-memory-tool.md`
- `docs/02-Decisions/adrs/ADR-186-context-budget-enforcement.md`
- `docs/04-Concepts/architecture/context-budget-observability.md`
- `docs/04-Concepts/architecture/memory-lifecycle.md`
- `docs/04-Concepts/architecture/session-start-runtime-diet.md`
- `docs/04-Concepts/architecture/token-efficient-agent-messaging.md`
- `docs/03-PoCs/research/minimal-context-principle.md`
- `rules/context-management.md`
- `rules/context-optimization.md`
- `rules/token-economy.md`
- `scripts/cos-document-ingest`
- `hooks/document-ingest-guard.sh`
