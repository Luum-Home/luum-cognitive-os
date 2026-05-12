# DX Assessment — Cognitive OS vs Vanilla Harnesses (2026-05-02)

**Date**: 2026-05-02
**Commit**: 91e02d53 (`feat(governance): add architecture readiness surface`)
**Method**: 6 parallel research-only agents (Explore, sonnet) over the working tree.
**Audience**: SR engineers / solutions architects evaluating COS adoption or maintenance.
**Purpose**: Snapshot baseline against which the in-flight DX-tax-reduction work
(commits `b141b868`, `3cee951f`, `397df374`, `b295e855`, `564d3b9d`, `4cdb30bd`)
can be measured.

This is a **frozen snapshot**. Counts and percentages reflect HEAD at the date
above and will drift. Re-run the assessment to compare.

## Scope

Six axes investigated by independent agents:

1. Governance — hooks, gates, trust scoring, advisory vs blocking
2. Cost / Dispatch — Qwen cascade, predictor, rate limiting, observability
3. Onboarding — cold start, daemons, error surface, time-to-first-task
4. Cross-harness — Claude Code, Codex, Cursor, Aider, Continue parity
5. SDD pipeline — coordinator, fast/full path, retry loop, real change cycles
6. Engram / memory — decay math, upsert, search quality, daemon dependency

Per-agent raw findings follow. Synthesis is at the end.

---

## 1. Governance

**Verdict**: 30–35% real bloqueante / 65–70% advisory or theatre.

**Real and blocking** (`exit 2`):
- `clarification-gate.sh` — 1 BLOCK in 70 events recorded
- `destructive-git-blocker.sh`, `secret-detector.sh`, `concurrent-write-guard.sh`,
  `lethal-trifecta-gate.sh` — PreToolUse on Bash/Edit
- `token-budget-monitor.sh` — blocks when hourly tokens >95% of `RATE_LIMIT_HOURLY_TOKENS`

**Advisory only or theatre**:
- `trust-score-validator.sh` parses output but **never `exit 2`**; in phase
  `reconstruction` confidence-gate likewise only warns. `trust-scores.jsonl`
  does not exist.
- `blast-radius.jsonl` — 524 events, **0 blocks**. `additionalContext` only.
- `adversarial-review` — markdown rule with no enforcer; `review-spawner.sh`
  fires stochastically at 20% sample rate.
- `apply-efficiency-profile.sh` — profiles `lean`/`standard`/`minimal` were
  collapsed into `default` by ADR-093. Script silently remaps and continues.

**Silent-failure surface**: 103 of 186 hook scripts (~55%) use
`2>/dev/null || true`. Hooks with the most occurrences are governance hooks:
`pre-agent-snapshot.sh` (22), `post-agent-snapshot-restore.sh` (18),
`destructive-git-blocker.sh` (14), `secret-detector.sh` (10),
`completion-gate.sh` (9). Errors in dependencies (`jq`, `python3`) are absorbed
and the hook reports success.

**Observability that does work**:
- `hook-timing.jsonl` — 45,397 entries
- `clarification-events.jsonl` — 70 entries (45 PASS, 24 WARN, 1 BLOCK)
- `blast-radius.jsonl` — 524 entries (160 CRITICAL, 163 HIGH, 171 LOW)
- `aspirational-audit.jsonl` — 6,235 entries classifying components

---

## 2. Cost / Dispatch

**Verdict**: dispatch and cost-prediction code is real; production data is empty;
no savings dashboard exists.

| Item | Code | Data |
|------|------|------|
| Qwen → OpenRouter → Gemini → Ollama → Claude cascade in `lib/dispatch.py` | REAL | `llm-dispatch.jsonl` is **0 bytes** — never invoked |
| Cost predictor (Jaccard over `task-history.jsonl`) | REAL | History file is **0 bytes** — falls back to hard-coded heuristic per phase |
| Model directive (`MODEL_DIRECTIVE` / `MODEL_DISABLED`) via `dispatch-gate.sh` | PARTIAL | 503 entries in `dispatch-gate.jsonl`, all `action: "allow"`; `dispatch.py` does not parse the directive |
| Token-bucket rate limiter (`hooks/rate-limiter.sh`, base 15 tokens/min, burst 33) | REAL | Active and observed firing during this assessment |
| Token-budget monitor blocks at 95% hourly | REAL | — |
| Context watchdog (PostToolUse) | LOG ONLY | Last entry shows `usage_pct: 167, level: urgent` — never `exit 2` |
| Savings comparison vs Claude-only baseline | NONE | No `friction-dashboard`, no `agent-bus-metrics` savings field |

**Cost-events**: 458 entries totalling ~$4.14 — **all marked `is_estimate: true`**,
computed via heuristic (15 tokens per word of description), not from API
metering.

**OS overhead per turn** (from `rules/context-optimization.md` lines 63–64):
- Current: ~17,500 tokens session-start, ~8,000 tokens per agent
- Target: <5,000 / <3,000
- At Claude Sonnet input rates ($3/M): ≈ **$0.025–0.035 per turn in preamble alone**.

---

## 3. Onboarding

**Verdict**: ~1 day for an SR who reads docs carefully; multi-day trial-and-error
otherwise. No "minimal viable" profile exists.

**Cold-start latency** (from `.cognitive-os/metrics/hook-timing.jsonl`,
n=98 SessionStart invocations):

| Stat | per-hook ms |
|------|-------------|
| p50  | 448 |
| p95  | 2,516 |
| max  | 6,237 |
| mean | 637 |

20 hooks chained at SessionStart. Async hooks reduce wall-clock but the user
perceives delay until first prompt is responsive.

**Daemons fail silently**: `engram-daemon-launcher.sh`, `reaper-daemon-launcher.sh`,
`session-watchdog-launcher.sh`, `cos-executor-daemon-launcher.sh` all
`exit 0` when binary is absent or health-check fails. Engram reinforcement
calls return `False` without logging. Cross-session memory simply does not
persist and the developer gets no signal.

**Test suite drift**: `error-learning.jsonl` shows **54 identical
`TEST_FAILURE` entries** (same fingerprint `17fa05a3fca8cc07600deb9c500eac97`,
all `go test ./...`) since 2026-04-25. A new developer running `test-all.sh`
sees failures from day zero.

**Doc inconsistency** (live as of this snapshot):
- `docs/00-MOCs/entrypoints/faq.md` — "72 skills"
- `skills/CATALOG.md` — 145 entries
- `docs/04-Concepts/root/onboarding-wizard-design.md` — "94 skills"
- README — 4-step quick start
- `docs/00-MOCs/entrypoints/getting-started.md` — 8–10 prerequisite steps
- `pyproject.toml` — version 0.12.0
- `CHANGELOG.md` — v0.22.0 (2026-04-30)

**Profiles deprecated, docs not updated**: `lean`, `standard`, `minimal` were
collapsed into `default` by ADR-093. Several docs and the wizard design still
reference the old names. The script remaps silently to stderr.

**Onboarding wizard**: status `DESIGN`, dated 2026-03-29; not implemented.

---

## 4. Cross-Harness

**Verdict**: Claude Code is first-class; Codex is a working second; Cursor /
Continue / OpenCode exist only as enum values.

**Adapters under `lib/harness_adapter/`**:

| Adapter | File | Status |
|---------|------|--------|
| `ClaudeCodeAdapter` | `claude_code.py` | Production |
| `CodexAdapter` | `codex.py` | Production with documented gaps |
| `AiderAdapter` | `aider.py` | POC — passive file-watcher |
| `BareCliAdapter` | `bare_cli.py` | Production fallback |
| `cursor`, `continue`, `opencode` | — | Enum-only in `HarnessName`, no adapter |

**Codex coverage gap**: Codex v0.124–v0.126-alpha.8 only emits `PreToolUse` /
`PostToolUse` for the `Bash` tool. Non-Bash tool events raise
`ParseError(reason="codex_tool_coverage_gap")`. `PreCompact` and subagent
lifecycle events are not available in Codex — features that depend on them
are Claude-only.

**Lock-in surfaces** (high-risk to CC schema/env changes):
- ~150 hooks reference `$CLAUDE_PROJECT_DIR` and CC-specific env vars
- `ClaudeCodeAdapter.parse_event()` hard-codes `tool_name`, `tool_use_id`,
  `tool_response`, `tool_input` at top-level of the payload
- `.claude/settings.json` schema is generated by `apply-efficiency-profile.sh`;
  Codex needs `.codex/hooks.json` with a different shape

**Genuine COS-only features** (none of CC, Codex, Cursor, Aider has them):
- Ebbinghaus memory decay + reinforcement + 2-hop graph walk
- Pre-agent snapshot / post-verify with auto-rollback package
- Reasoning-cycle counter (cap of 20 per agent)
- Canonical event stream across harnesses
- Multi-provider model router with kill-switches
- Concurrent-write guard with cross-agent mutex
- ADR detector with frontmatter validation

**Vanilla features not replicated**:
- Cursor Composer parallel workers (native)
- Aider architect/editor dual-model
- `/clear` conversation reset
- CC native web search tool

---

## 5. SDD Pipeline

**Verdict**: backbone is real and tested; execution layer depends on
orchestrator behaviour rather than deterministic code; no full cycle has
been completed end-to-end.

**Real**:
- `lib/sdd_pipeline.py` (304 LOC) — `is_fast_path()`, `get_phases()`,
  `next_phase()`, model tiering opus/sonnet/haiku/free.
- Fast path (5 phases) vs full path (8 phases) configurable in
  `cognitive-os.yaml` under `sdd.fast_path`.
- ADR-014 documented and committed (`e5552d1`, `389628c`, `a866fdb1`).
- `lib/sdd_resume.py` (386 LOC) — `SDDState` dataclass, `save_state()`,
  `resume()`, `max_retries: int = 3`.

**Gaps**:
- 7 of 9 SDD skills (`sdd-apply`, `sdd-verify`, `sdd-archive`, `sdd-propose`,
  `sdd-spec`, `sdd-design`, `sdd-tasks`) have no local `SKILL.md` — they
  resolve to external plugin skills.
- DAG state persistence requires the orchestrator to call `mem_save()`
  manually; there is no automatic hook firing on phase transition.
- Apply-verify retry loop is described in markdown rules; no Python code
  re-launches a fresh sub-agent on failure.
- Topic-key inconsistency: `sdd/{change}/...` (sdd-continue),
  `planning/{change}/...` (sdd-resume, lib/sdd_resume.py), and
  `openspec/changes/{change}/...` (rules/context-optimization.md) all coexist.
- No `archive-report`, `verify-report`, or `sdd-timings.jsonl` files exist
  in the repo. **Zero complete SDD cycles** evidenced.

**Origin**: homegrown, inspired by BMAD v6 patterns 1/5/7/8/11
(see `docs/06-Daily/root/complexity-audit.md`). Not a fork.

---

## 6. Engram / Memory

**Verdict**: decay maths are correct and tested; plumbing has three
blocking bugs that significantly degrade the value proposition.

**Real**:
- Ebbinghaus retention `R(t) = exp(-t / τ)` in `lib/engram_lifecycle.py:101`
- Confidence reinforcement `c' = c + (1 - c) * 0.15` in line 116
- Adjusted score `base * 0.7 + confidence * retention * 0.3` in line 141
- τ per type (days): architecture=365, decision=180, pattern=180,
  discovery=90, bugfix=60, manual=90
- 18 unit tests in `test_engram_lifecycle.py` covering decay monotonicity,
  reinforcement convergence, adjusted-score bounds (1,000 random iterations).
- MCP server local: `mcp-server/cos_mcp.py`, `MemoryScanner` guard before
  writes.
- 544 observations in `.engram/exports/luum-cognitive-os.jsonl`,
  total 1.5 MB. All have `topic_key` populated.

**Blocking bugs**:
1. **Upsert is broken**. The first two lines of the JSONL have identical
   `topic_key`, `title`, `content`, and `created_at`. The `engram save`
   binary creates a new record on every call, irrespective of `topic_key`.
2. **Reinforcement silently fails** when the daemon at port 7437 is down.
   `reinforce()` returns `False`. No CLI fallback. `engram-reinforce-on-access.sh`
   emits no warning to the user.
3. **Score base defaults to 1.0** — `obs.get("score", 1.0)` in line 266.
   When the binary does not return a normalised score (the common case),
   all observations re-rank with base=1.0, collapsing the differential
   ranking down to `confidence * retention * 0.3`.

**Other gaps**:
- No expiration / purge — decay only affects ranking.
- No latency metrics; `mem_capture_passive` is a black box not auditable
  from the repo.

---

## Synthesis

**What COS does that no vanilla harness offers** (and that justifies the
project's existence):

1. Persistent memory with mathematically correct decay and reinforcement
2. Pre/post-agent snapshot with rollback
3. Multi-provider dispatch with kill-switches
4. Hard-governance hooks (secrets, destructive git, concurrency, lethal trifecta)
5. SDD pipeline backbone with phase tiering

**What is fragile or theatrical today**:

1. Soft-governance gates that never block (trust score, blast radius,
   confidence in `reconstruction` phase)
2. ~55% of hooks swallow errors via `2>/dev/null || true`
3. Cost predictor and dispatch with empty production datasets
4. Engram upsert duplicates and base-score-1.0 ranking collapse
5. Doc / version drift (skills count discrepancies, deprecated profiles
   referenced, pyproject vs CHANGELOG version skew)
6. `go test ./...` failing for 7+ days unaddressed in `error-learning.jsonl`
7. Cross-harness story is one production adapter (Codex with gaps) plus
   three unimplemented enum values

**What is ahead of all vanilla harnesses regardless of the above**:
adoption of **all five governance principles simultaneously** — observability,
reproducibility, cost transparency, blast-radius awareness, and rollback
safety — is unique to this project. No vanilla harness has any of them
end-to-end.

## Cross-references

In-flight commits already addressing items in this report:

- `b141b868 docs: plan DX tax reduction phases` — overhead reduction
- `3cee951f feat(governance): add ROI friction dashboard` — savings tracking
- `397df374 feat(governance): add lifecycle demotion recommendations` — theatre layer
- `b295e855 docs: add adoption-tiers.md` — distribution boundary
- `564d3b9d docs: plan operational stability friction reduction` — silent failures
- `4cdb30bd docs: define foundation hardening program` — overall

Items **not** clearly covered by current work, candidates for new ADR:

- Engram upsert duplicates
- Engram base-score 1.0 ranking collapse
- SDD topic-key reconciliation (`sdd/` vs `planning/` vs `openspec/`)
- Long-running `go test ./...` failure in `error-learning.jsonl`
- `pyproject.toml` vs `CHANGELOG.md` version skew

See [ADR-128: Data-Layer Integrity Fixes](../adrs/ADR-128-data-layer-integrity-fixes.md).
