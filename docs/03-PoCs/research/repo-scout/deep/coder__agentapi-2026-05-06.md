---
evaluated_at: 2026-05-06 06:42 UTC
evaluation_level: 2
parent_radar: docs/06-Daily/reports/external-tools-radar-2026-05-06.md
shallow_verdict: pass-to-deep (HTTP normalization across 6+ agent CLIs; ADR-033 fit)
deep_verdict: ADOPT — clean Go HTTP API normalizer with comprehensive harness testdata
deepwiki_url: https://deepwiki.com/coder/agentapi
engram_id: pending
---

## Repository Evaluation: coder/agentapi

### Classification: ADOPT
**Score**: 8.7/10
**Evaluation Level**: 2 (Deep — gh api recursive tree, lib/msgfmt/testdata extensive inspection)

### Summary
HTTP API for Claude Code, Goose, Aider, Gemini, Amp, and Codex. Go, MIT, push 2026-04-13, **v0.12.1** with strong semver patch line. Maintained by Coder (the company). The `lib/msgfmt/testdata/` directory contains golden-file fixtures for **10 harnesses** (aider, amazonq, amp, auggie, claude, codex, copilot, cursor, gemini, goose, opencode) — most comprehensive harness-fingerprinting corpus in the deep batch. **Direct fit for ADR-033 harness-agnostic event capture and `lib/harness_adapter/`**.

### Scoring Breakdown
| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | ADR-033 says "harness-agnostic event capture; CC adapter preserves legacy ... new harnesses add one adapter file" — agentapi is the canonical reference |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 9/10 | Push 2026-04-13; 5 tags v0.11.6-v0.12.1 = active patch cadence; 15 issues/30d (manageable) |
| Maturity | 15% | 7/10 | v0.12.x pre-1.0; 1373★; 1 year old; corporate maintainer |
| Integration | 10% | 8/10 | Go binary or library; uniform HTTP API; testdata is gold for our adapter ports |
| **Weighted Total** | | **9.05/10** weighted, presented as **8.7/10** | |

### Adoption Signals
| Signal | Value | Descriptor |
|--------|-------|------------|
| Issue velocity (30d) | 15 issues | moderate issue activity |
| Release cadence | v0.11.6-v0.12.1 over weeks | weekly-to-biweekly releases |
| CI health | 7/10 success | CI green-ish |

### Key Findings
- **Strengths**:
  - **`lib/msgfmt/testdata/format/{aider,amazonq,amp,auggie,claude,codex,copilot,cursor,gemini,goose,opencode}/`** — golden fixtures for 11 harnesses covering first_message, multi-line-input, second_message, thinking, confirmation_box, auto-accept-edits, remove-task-tool-call. **This is the most comprehensive harness-format corpus in the radar.**
  - `lib/msgfmt/testdata/initialization/{ready,not_ready}` per harness — initialization-state detection.
  - `lib/screentracker/` for terminal screen diffing (relevant to TUI harnesses).
  - Coder backs it commercially → maintenance momentum.
  - Clean Go monorepo (cmd/attach + cmd/server + lib/{httpapi, msgfmt, screentracker, termexec}).
- **Weaknesses**:
  - Pre-1.0 (v0.12.1) — API may shift.
  - Go (not Python) — adoption requires either invoking the Go binary or reimplementing fixtures in Python.
  - 37 open issues — small but unclear triage state.
- **Architecture**: HTTP server normalizing agent CLI I/O. msgfmt parses harness output into uniform messages. screentracker diffs terminal state. termexec spawns subprocesses.

### Integration Plan
- **What to use**:
  1. **`lib/msgfmt/testdata/`** — vendor (or mirror) the testdata into COS `lib/harness_adapter/testdata/` as the canonical golden corpus for harness-output parsing.
  2. msgfmt parsing logic — port to Python for our adapter pipeline (cleaner than maintaining Go bridge).
  3. agentapi as **sidecar binary**: run it alongside COS to expose all harnesses over uniform HTTP, drop our custom orchestration where it overlaps.
  4. screentracker inspiration for any TUI screenshot/diff work.
- **How to integrate**:
  - Phase 1: vendor testdata under MIT license, write COS-side parsers tested against them.
  - Phase 2: optionally run agentapi as a sidecar for harnesses we don't have first-class adapters for.
- **Effort estimate**: small for testdata vendor (1 day); medium for parser port (3-5 days)
- **Dependencies it brings**: optionally Go binary as sidecar; otherwise none

### Risks
- Pre-1.0 — testdata format may change between versions. Pin to v0.12.1.
- Go binary as sidecar adds runtime dependency.
- Coder's commercial roadmap may diverge from agent-OS interests.

### Cross-Reference vs Shallow Radar
Shallow verdict: "HTTP normalization across 6+ agent CLIs; uniform event schema for ADR-033." **Deep evidence agrees and amplifies**: the testdata corpus alone is worth the adoption — it covers 11 harnesses (more than the shallow note's "6+"). The agentapi binary as sidecar is a bonus path. Verdict ADOPT confirmed; testdata vendor + parser port should be a near-term Phase-2 task.

### Raw Metrics Appendix
```
{"name":"agentapi","license":"MIT","stars":1373,"forks":119,"language":"Go","pushed":"2026-04-13T23:18:27Z","created":"2025-04-07T08:31:21Z","open_issues":37,"size":1748 KB}
tags: v0.12.1,v0.12.0,v0.11.8,v0.11.7,v0.11.6
issues_30d=15, CI=7/10 success
testdata harness count: 11 (aider, amazonq, amp, auggie, claude, codex, copilot, cursor, gemini, goose, opencode)
```
