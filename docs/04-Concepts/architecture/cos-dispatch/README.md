# cos-dispatch: Vendor-Agnostic Hook Dispatcher

## Problem

Cognitive OS has 48 hooks (28 sync, 20 async) adding ~36.5s/session overhead. Each hook spawns a separate bash process with its own jq parsing, library sourcing, and Python cold starts. The 3 worst hooks alone account for ~34s:

- `rate-limit-protection.sh`: spawns python3 PER LINE of cost-events.jsonl (O(n) subprocesses)
- `dispatch-gate.sh`: 9 sequential Python cold starts (~2.1s)
- `completion-gate.sh`: EXIT trap runs 2 Python processes on EVERY tool call, not just Agent

Additionally, hooks are configured via Claude Code's `.claude/settings.json`, creating vendor lock-in. 5 of 7 major AI coding tools share the same hook protocol but use different config formats and event names.

## Solution

A single Go binary (`cos-dispatch`) that:

1. Replaces N process spawns with 1 process per hook event
2. Abstracts across providers (Claude Code, Codex, Gemini CLI, Cursor, Windsurf)
3. Adds a Transformer pipeline for hooks that modify input/output
4. Tracks execution patterns and auto-generates validators from recurring issues

Inspired by [klaudiush](https://github.com/smykla-skalski/klaudiush) (MIT, Go, 724 commits, 59-112ms benchmarked on M3 Max).

## The Emerging Standard

5 of 7 AI coding tools share the same hook protocol:

| Feature | Claude Code | Codex | Gemini CLI | Cursor | Windsurf | Continue | OpenCode |
|---------|-------------|-------|------------|--------|----------|----------|----------|
| Shell command hooks | Yes | Yes | Yes | Yes | Yes | Yes | No (JS) |
| JSON stdin | Yes | Yes | Yes | Yes | Yes | Yes | No |
| Exit code 2 = block | Yes | Yes | Yes | Yes | Yes | ? | No |
| JSON stdout response | Yes | Yes | Yes | Yes | Yes | ? | No |
| Regex matchers | Yes | Yes | Yes | Yes | Partial | Yes | N/A |

Differences are trivial: event names (`PreToolUse` vs `BeforeTool` vs `beforeShellExecution`), config paths (`.claude/` vs `.gemini/` vs `.cursor/`), and stdin JSON field names. Each requires ~50-80 lines of Go adapter code.

## Component Architecture

```
+------------------------------------------------------------------+
|                        cos-dispatch binary                       |
|                                                                  |
|  +-----------+    +------------+    +-----------+    +----------+ |
|  | Provider  |--->| Transformer|--->| Validator |--->| Response | |
|  | Detector  |    | Pre-Pipeline|   | Dispatch  |    | Builder  | |
|  |           |    |            |    |           |    |          | |
|  | claude    |    | secret-    |    | Registry  |    | claude   | |
|  | codex     |    |   redactor |    |   + preds |    | codex    | |
|  | gemini    |    | symlink-   |    |           |    | gemini   | |
|  | cursor    |    |   resolver |    | Sequential|    | cursor   | |
|  | windsurf  |    |            |    | Parallel  |    | windsurf | |
|  +-----------+    +-----+------+    | Executor  |    +----+-----+ |
|       |                 |           +-----+-----+         |      |
|       |                 |                 |               |      |
|       v                 v                 v               v      |
|  +----+------+    +-----+------+    +-----+-----+    +---+----+ |
|  | Config    |    | Transformer|    | Plugin    |    | Pattern | |
|  | Loader    |    | Post-Pipe  |    | Adapter   |    | Tracker | |
|  |           |    |            |    |           |    |         | |
|  | TOML      |    | result-    |    | bash hook |    | SQLite  | |
|  | YAML      |    |   truncator|    | wrapper   |    | Recorder| |
|  | cognitive-|    | inject-    |    |           |    | Detector| |
|  |   os.yaml |    |   phase-ctx|    |           |    | AutoGen | |
|  +-----------+    +------------+    +-----------+    +---------+ |
+------------------------------------------------------------------+
         |                                                  |
    stdin/stdout                                    .cognitive-os/
    (JSON)                                          patterns.db
```

## Data Flow

```
stdin (raw JSON from AI agent)
  |
  v
1. Provider Detection (env vars / CLI flag / JSON sniffing)
  |
  v
2. Provider Adapter: normalize raw JSON --> hook.Context (canonical)
  |
  v
3. Transformer Pre-Pipeline (ordered by priority, ascending):
   - SymlinkResolver: resolve file paths in ToolInput
   - SecretRedactor: strip secrets before validators see them
  |
  v
4. Validator Dispatch:
   a. Registry.FindValidators(ctx) -- predicate matching
   b. Executor.Execute(ctx, validators) -- parallel by category pools
   c. Override filtering (disabled error codes)
  |
  v
5. Transformer Post-Pipeline (ordered by priority, ascending):
   - ResultTruncator: truncate large tool output
   - InjectPhaseContext: add phase rules to agent prompt context
  |
  v
6. Pattern Tracker: record execution to SQLite (async, non-blocking)
  |
  v
7. Response Builder: build provider-specific JSON
  |
  v
stdout (JSON response to AI agent)
```

## Project Structure

```
cmd/
  cos-dispatch/
    main.go                        # Entry point
internal/
  dispatcher/                      # Core orchestrator
  validator/                       # Validator interface, Registry, predicates
  transformer/                     # Transformer interface, pipeline
  provider/                        # Provider adapters (claude, codex, gemini, cursor, windsurf)
  executor/                        # Sequential + Parallel executors with category pools
  plugin/                          # Bash plugin loader and adapter
  pattern/                         # Pattern tracker, detector, auto-generator
  config/                          # TOML config loader
  response/                        # Provider-specific response builders
pkg/
  hook/                            # Shared types: Context, ToolInput, EventType, ToolType
  plugin/                          # Plugin API types (for external plugins)
generated/                         # Auto-generated validators/transformers
```

## Status

**Phase 1 (Foundation):** DONE — 2026-04-15. Core binary, interfaces, plugin adapter, Claude provider. 10 Go packages, all tests passing.

**Phase 2 (Parallel + Providers):** DONE — 2026-04-16. Executor with parallel category pools, Codex + Gemini provider adapters. Task Panel adapter added as first ADR-021 implementation.

**Phase 3 (Native Validators, partial):** DONE — 2026-04-16. 6 of 17 high-value hooks ported to Go validators in `internal/validator/impl/`: rate-limiter, rate-limit-protection, secret-detector, content-policy, completeness-checker, prompt-quality. The remaining 11 stay as bash plugins (acceptable — plugin adapter exists).

**Phase 4 (Pattern Tracking):** DONE — 2026-04-16. SQLite-backed `SQLTracker` + `SQLDetector` in `internal/pattern/`. 3 of 6 detector types implemented (RepeatedFailure, PerfRegression, ErrorCluster). Dispatcher instrumented via `WithTracker()` option. 11 tests passing.

**Phase 5 (Auto-Generator + Remaining Providers):** Pending — next session. Also pending: FalsePositive, MissingCoverage, SequenceCorrelation detectors. Sub-phase breakdown is captured in [ADR-011](adrs/011-phase-5-sub-phase-ordering.md); the constituent decisions live in ADR-006 through ADR-009.

## Timeline

| Phase | Weeks | Days | What | Status |
|-------|-------|------|------|--------|
| 1. Foundation | 1-2 | 8 | Core binary, interfaces, plugin adapter, Claude provider | **DONE** |
| 2. Parallel + Providers | 3 | 5 | Executor, Codex + Gemini adapters | **DONE** |
| 3. Native Validators | 4-5 | 11 | Port 17 hooks → Go (6 of 17 done, rest as plugins) | **DONE (partial, acceptable)** |
| 4. Pattern Tracking | 6 | 7 | SQLite tracker + detector with 3 of 6 pattern types | **DONE (partial)** |
| 5. Auto-Gen + Providers | 7-8 | 8 | Generator, feedback, Cursor + Windsurf, remaining 3 detectors | Pending |
| **Total** | **8** | **39** | ~80% effort complete as of 2026-04-16 | |

## Related Documents

- [Interface Definitions](interfaces.md)
- [Configuration Schema](config.md)
- [Migration Plan](migration.md)
- [Database Schema](schema.sql)
- [ADR Auto-Detection Design](adr-detection.md)
- [ADR-001: Reuse klaudiush predicates](adrs/001-reuse-klaudiush-predicates.md)
- [ADR-002: Transformer separate interface](adrs/002-transformer-separate-interface.md)
- [ADR-003: SQLite over JSONL](adrs/003-sqlite-over-jsonl.md)
- [ADR-004: Generated artifacts disabled](adrs/004-generated-artifacts-disabled.md)
- [ADR-005: Typed provider adapters](adrs/005-typed-provider-adapters.md)
- [ADR-006: `override` result type in executions](adrs/006-override-result-type.md)
- [ADR-007: Eager population of `failure_sequences`](adrs/007-eager-failure-sequences.md)
- [ADR-008: `cos-dispatch review` as subcommand in same binary](adrs/008-review-subcommand.md)
- [ADR-009: Go-only auto-generation in Phase 5](adrs/009-go-only-auto-generation.md)
- [ADR-010: Real-behavior tests required for every Phase 5 sub-phase](adrs/010-real-behavior-tests.md)
- [ADR-011: Phase 5 sub-phase ordering (5.0 first)](adrs/011-phase-5-sub-phase-ordering.md)
- [ADR-021: Vendor-Agnostic State with Provider Adapters](../adrs/021-vendor-agnostic-with-adapters.md)

## References

- [klaudiush](https://github.com/smykla-skalski/klaudiush) — MIT, Go dispatcher we're basing this on
- [Claude Code Hooks docs](https://code.claude.com/docs/en/hooks)
- [Codex Hooks docs](https://developers.openai.com/codex/hooks)
- [Gemini CLI Hooks](https://geminicli.com/docs/hooks/)
- [Cursor Hooks](https://cursor.com/docs/hooks)
- [Windsurf Cascade Hooks](https://docs.windsurf.com/windsurf/cascade/hooks)
