---
type: concept-synthesis
source: docs/04-Concepts/architecture/graphify-real-token-telemetry-tooling-audit-2026-05-22.md
provenance: "Question before building new tooling: does COS already have real token-usage measurement primitives, to avoid inventing a duplicate Graphify-specific token parser?"
---

## What it is
Audit concluding COS already has fragmented real-token/cost telemetry primitives that should be reused; the actual gap is a joiner that correlates Graphify preload selections with real session token totals for before/after comparison — not a new parser.

## Key mechanics
- Reusable primitives found: `lib/session_parser.py` (nested `message.usage`, strongest real-session-totals source), `lib/claude_usage_reader.py`, `lib/record_completion.py`, canonical `TokenUsage` shape in `lib/harness_adapter/base.py`, Claude Code adapter emits `TokenUsage`; Codex adapter does not (Gap 2).
- Gaps: (1) no Graphify before/after joiner existed; (2) Codex token usage not normalized; (3) `cost-events.jsonl` mixes estimates/actuals; (4) `context-budget.jsonl` is an estimate, not real billing.
- Implemented: `scripts/cos-graphify-run-telemetry --session <jsonl> --matrix-json <preload-matrix> --out <report.md>` joins preload selections with real session totals via `lib/session_parser.py`; supports `--latest-claude-session`, `--project-filter`, `--since-hours`, `--sessions-dir` for explicit opt-in discovery (no implicit scanning).
- Validation commands ran green: `48 passed in 1.95s` for telemetry/preload-matrix/footprint tests.
- `scripts/cos-graphify-token-reduction-smoke`: controlled paired fixtures, threshold 20%, measured 56.25% reduction (12,800 → 5,600 tokens).
- `scripts/cos-graphify-context-replay-benchmark`: real repo-file replay for `lib/harness_adapter/base.py` — baseline 362 files/1,113,942 tokens vs preload 7 files/21,228 tokens = 98.09% simulated reduction.
- Real paired run (`docs/06-Daily/reports/graphify-run-telemetry-real-paired-2026-05-22.md`): baseline 59,614 vs current 1,206,427 input+output tokens — labeled directional only (uncontrolled historical sessions), not a causal claim.
- 2026-06-12 hardening: `lib/token_usage.py` normalized schema; `scripts/aggregate_session_tokens.py` writes `telemetry_schema: token-usage-normalized.v1` into `cost-events.jsonl`; `scripts/token_report.py` preserves `providers_seen`/`harnesses_seen`.

## Relations & where used
Feeds the Graphify controlled-trial line of work (`graphify-integration-assessment-2026-05-22.md`, `graphify-next-step-decision-2026-05-22.md`).

## Status / caveats
Proves portable telemetry ingestion and controlled-smoke measurement; does NOT prove live production savings for a specific provider/IDE unless paired real sessions with matching task/model/prompt/tool/cache state are supplied.
