---
type: concept-synthesis
source: docs/04-Concepts/architecture/cos-dispatch/README.md
status: "Phases 1-4 DONE, Phase 5 pending"
provenance: "Cognitive OS has 48 hooks (28 sync, 20 async) adding ~36.5s per session overhead, with 3 hooks alone responsible for ~34s of process-spawn and cold-start cost; hooks are also locked to Claude Code's settings.json format."
---

## What it is
`cos-dispatch` is a single Go binary hook dispatcher that replaces N per-hook process spawns with one process per event, abstracts hook logic across 5+ AI coding tools (Claude Code, Codex, Gemini CLI, Cursor, Devin), and adds a transformer pipeline plus pattern-tracking/auto-generation of validators.

## Key mechanics
- Worst offenders: `rate-limit-protection.sh` spawns python3 per line of cost-events.jsonl (O(n) subprocesses); `dispatch-gate.sh` runs 9 sequential Python cold starts (~2.1s); `completion-gate.sh` EXIT trap runs 2 Python processes on every tool call.
- Inspired by klaudiush (MIT, Go, 724 commits, 59-112ms benchmarked on M3 Max).
- 5 of 7 tools (Claude Code, Codex, Gemini CLI, Cursor, Devin) share shell command hooks, JSON stdin, exit-code-2-blocks, JSON stdout response; differences are event names, config paths, and stdin field names (~50-80 lines of adapter code each).
- Pipeline: Provider Detector -> Transformer Pre-Pipeline (secret-redactor, symlink-resolver) -> Validator Dispatch (Registry + sequential/parallel Executor by category pools) -> Transformer Post-Pipeline (result-truncator, inject-phase-context) -> Pattern Tracker (SQLite, async) -> Response Builder.
- Layout: `cmd/cos-dispatch/main.go`; `internal/{dispatcher,validator,transformer,provider,executor,plugin,pattern,config,response}`; `pkg/hook`, `pkg/plugin`; `generated/` (auto-generated validators/transformers, disabled per ADR-004).
- Phase status: Phase 1 Foundation DONE (10 Go packages); Phase 2 Parallel+Providers DONE (Codex+Gemini adapters, Task Panel adapter); Phase 3 Native Validators DONE partial (6 of 17 hooks ported to Go: rate-limiter, rate-limit-protection, secret-detector, content-policy, completeness-checker, prompt-quality; remaining 11 stay bash plugins); Phase 4 Pattern Tracking DONE partial (SQLite SQLTracker/SQLDetector, 3 of 6 detector types: RepeatedFailure, PerfRegression, ErrorCluster; 11 tests passing); Phase 5 Auto-Generator + remaining providers PENDING (sub-phase order in ADR-011).
- Timeline: 8 weeks / 39 days total, ~80% effort complete as of 2026-04-16.

## Relations & where used
ADR-001 (reuse klaudiush predicates) through ADR-011 (Phase 5 sub-phase ordering, 5.0 first); ADR-021 (vendor-agnostic state with provider adapters). Sibling docs in this batch: interfaces.md, adr-detection.md, test-strategy.md.

## Status / caveats
Phase 5 (auto-generator, Cursor/Devin providers, remaining 3 detector types) is the open item; sub-phase breakdown and ordering governed by ADR-011.
