# Graphify Real Token Telemetry Tooling Audit — 2026-05-22

## Question

Do we already have tools for measuring real token usage in agent runs before
adding a new Graphify-specific measurement layer?

## Verdict

Yes, partially. Cognitive OS already has real-token and cost telemetry primitives,
but they are fragmented by harness and purpose. We should reuse them instead of
inventing a new token parser.

The missing piece is not raw token parsing. The missing piece is a comparison
adapter that joins existing run/session telemetry with Graphify preload decisions
so we can measure before/after runs.

## Existing Tools Found

| Tool | Location | What it measures | Scope | Graphify relevance |
|---|---|---|---|---|
| Session parser | `lib/session_parser.py`, `packages/session-parser/lib/session_parser.py` | Real Claude Code session tokens, cache tokens, tools, models, subagents, duration | Claude Code native JSONL | Strongest existing primitive for real session totals. |
| Usage monitor | `lib/claude_usage_reader.py`, `packages/usage-monitor/lib/claude_usage_reader.py` | Ground-truth cost reconciliation from Claude session usage entries | Claude Code flattened/top-level usage entries | Useful for cost reconciliation, but less complete than `session_parser` for nested `message.usage`. |
| Record completion | `lib/record_completion.py` | Reads real Claude Code token usage for a matching `tool_call_id` and appends cost events | Claude Code Agent completion | Useful for per-Agent completion rows when hook payload has `tool_call_id`. |
| Canonical token event | `lib/harness_adapter/base.py`, `packages/agent-lifecycle/lib/harness_adapter/base.py` | `TokenUsage` canonical event shape | Harness-agnostic schema | Target schema for normalized token usage. |
| Claude Code adapter | `packages/agent-lifecycle/lib/harness_adapter/claude_code.py` | Emits `TokenUsage` when Claude hook payload includes usage | Claude Code hooks | Already bridges real usage into canonical events for supported payloads. |
| Codex adapter | `packages/agent-lifecycle/lib/harness_adapter/codex.py` | Codex sessions/tools, not token usage | Codex Desktop/CLI session rows and hooks | Useful for run boundaries/tools, but current adapter does not emit token usage. |
| Cost events ledger | `.cognitive-os/metrics/cost-events.jsonl` | Estimated and sometimes actual cost/token rows | Runtime metrics | Existing cost ledger, but schema has historical drift and mixed estimates/actuals. |
| Context budget metrics | `lib/context_budget.py`, `hooks/context-budget-meter.sh`, `.cognitive-os/metrics/context-budget.jsonl` | Context token estimates for hook-added context | Hook/context hygiene | Good for context budget proxy, not real provider usage. |
| Token budget monitor | `hooks/token-budget-monitor.sh` | Hourly token guard from cost/resource ledgers | PreToolUse Agent guard | Enforcement primitive, not enough for before/after Graphify analysis. |
| Graphify token footprint | `scripts/cos-graphify-token-footprint` | Deterministic local token proxy for preload vs broad slice | Graphify context selection | Good proxy, not real run telemetry. |
| Graphify run telemetry | `scripts/cos-graphify-run-telemetry` | Joins Graphify preload selections with real session totals from `lib.session_parser.py` | Explicit operator-provided session JSONL | Implemented joiner for before/after reporting without single-run causality claims. |
| Graphify token-reduction smoke | `scripts/cos-graphify-token-reduction-smoke` | Deterministic controlled baseline/current token reduction through synthetic Claude JSONL fixtures | Offline smoke test | Proves the causal-measurement harness without live model calls. |
| Graphify context replay benchmark | `scripts/cos-graphify-context-replay-benchmark` | Controlled prompt-token replay using real repository file content | Offline benchmark | Simulates broad-context versus Graphify-preload savings without provider billing. |

## Evidence

Validation command:

```bash
.venv/bin/python -m pytest packages/session-parser/tests/test_session_parser.py packages/usage-monitor/tests/test_claude_usage_reader.py tests/unit/test_record_completion.py::TestGetRealTokenUsageFromJsonl tests/unit/test_record_completion.py::TestRealCostCalculationOpus tests/unit/test_record_completion.py::TestRealCostCalculationSonnet tests/unit/test_harness_adapter_base.py tests/unit/test_harness_adapter_claude_code.py -q
```

Result:

```text
68 passed in 0.51s
```

## What We Should Reuse

Use `lib/session_parser.py` as the first source for actual Claude Code run totals
because it reads nested `message.usage` fields and reports:

- `total_input_tokens`;
- `total_output_tokens`;
- `cache_creation_tokens`;
- `cache_read_tokens`;
- `tool_use_count`;
- `models_used`;
- `subagent_count`;
- `duration_minutes`.

Use `lib/record_completion.py` for per-Agent completion telemetry when a
`tool_call_id` is available.

Use the canonical `TokenUsage` event shape as the cross-harness target.

## Gaps

### Gap 1 — No Graphify before/after joiner

No existing tool answers:

> For this run, did using `cos-graphify-preload-matrix` reduce real session input
> tokens versus comparable runs without Graphify preload?

We need a small joiner that records:

- run/session id;
- Graphify matrix command and selected bundles;
- preload files selected;
- actual session token totals from `session_parser` or harness token events;
- comparison baseline or previous run cohort.

### Gap 2 — Codex token usage is not normalized

The Codex adapter currently normalizes sessions and tool events from
`~/.codex/sessions` fixtures, but it does not emit canonical `TokenUsage`. That
may be because the available sanitized fixture set does not expose provider token
usage. Codex support for real token deltas therefore remains unproven.

### Gap 3 — Cost ledgers mix estimates and actuals

`cost-events.jsonl` contains estimated rows and actual rows. It is useful for
budget enforcement, but before/after Graphify claims should prefer real session
parser totals when available and label cost-ledger rows by `is_estimate`.

### Gap 4 — Context budget metrics are estimates

`context-budget.jsonl` measures injected context and prompt/context surfaces with
a token estimator. It helps explain why Graphify may save context, but it is not
actual provider token billing.

## Implemented Next Step

We did not create a new token parser. `scripts/cos-graphify-run-telemetry` now reuses
existing primitives:

```bash
scripts/cos-graphify-run-telemetry --session <claude-session-jsonl> --matrix-json <preload-matrix-output.json> --out docs/06-Daily/reports/graphify-run-telemetry-YYYY-MM-DD.md
```

The operator can either pass `--session` directly or explicitly opt into latest-session discovery with `--latest-claude-session`. Latest-session discovery may be narrowed with `--project-filter`, `--since-hours`, and `--sessions-dir`; there is still no implicit scan when neither `--session` nor `--latest-claude-session` is present.

Minimum output implemented:

1. selected Graphify preload bundles;
2. preload estimated tokens using the same deterministic `ceil(characters / 4)` estimator as the footprint proxy;
3. actual session input/output/cache tokens from `lib/session_parser.py`;
4. tool-use and duration stats;
5. whether the row is actual, estimated, or mixed;
6. comparison guidance without claiming causality from one run.

## Validation

```bash
.venv/bin/python -m pytest tests/unit/test_cos_graphify_run_telemetry.py tests/unit/test_cos_graphify_preload_matrix.py tests/unit/test_cos_graphify_token_footprint.py packages/session-parser/tests/test_session_parser.py tests/unit/test_harness_adapter_base.py -q
```

Result: `48 passed in 1.95s`.

## Controlled Causal-Measurement Smoke — 2026-05-22

`script/cos-graphify-token-reduction-smoke` creates paired Claude Code JSONL fixtures with the same task, model, tool policy, prompt policy, and cache values. It then calls `scripts/cos-graphify-run-telemetry` and asserts that the Graphify-preload fixture reduces input+output tokens by at least the configured threshold.

Latest smoke result:

- status: `pass`;
- threshold: 20%;
- measured reduction: 56.25%;
- baseline fixture: 12,800 input+output tokens;
- Graphify-preload fixture: 5,600 input+output tokens;
- saved fixture tokens: 7,200.

This closes the test-harness gap for causal measurement mechanics. It still does not claim live production savings because it uses deterministic fixtures rather than model calls.

## Real-Context Replay Benchmark — 2026-05-22

`script/cos-graphify-context-replay-benchmark` builds two controlled prompt contexts from actual repository files: a broad baseline rooted at the selected bundle's slice and a Graphify preload bundle. It excludes generated artifacts and caches such as `graphify-out`, `__pycache__`, `.pytest_cache`, `.venv`, `node_modules`, `dist`, and `build`.

Latest replay result for `lib/harness_adapter/base.py`:

- status: `pass`;
- baseline root: `lib`;
- baseline files: 362;
- preload files: 7;
- baseline input tokens: 1,113,942;
- preload input tokens: 21,228;
- simulated reduction: 98.09%;
- saved input tokens: 1,092,714.

This is stronger than a synthetic smoke because it uses real repo content, but it is still not live provider billing.

## Real Paired Measurement Run — 2026-05-22

A real paired telemetry report was generated at `docs/06-Daily/reports/graphify-run-telemetry-real-paired-2026-05-22.md` using two operator-authorized Claude Code session JSONL files from the Cognitive OS project and the `harness-events` preload matrix.

Result summary:

- metric label: `mixed`;
- preload estimate: 21,111 tokens;
- baseline session total: 59,614 input+output tokens;
- current session total: 1,206,427 input+output tokens;
- delta: +1,146,813 tokens;
- interpretation: directional only, because these historical sessions were not controlled equivalents.

This closes the tooling gap and provides real telemetry evidence, but it does not prove Graphify token reduction. A causal claim still requires a controlled pair with the same task, model, prompt policy, tool policy, and comparable cache state.

## Acceptance Criteria

1. Reuse existing `session_parser` and `TokenUsage` concepts.
2. Do not read live `~/.claude` or `~/.codex` stores unless an operator explicitly
   passes a session path or opts into `--latest-claude-session` local scanning.
3. Label actual versus estimated metrics.
4. Keep Graphify as context-selection evidence, not verification evidence.
