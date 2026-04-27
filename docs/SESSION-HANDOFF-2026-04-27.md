# Session Handoff — 2026-04-27

> Topic key: `session/2026-04-27/handoff`. Project: `luum-cognitive-os`.

## Goal

Build out engram lifecycle (LLM Wiki v2 patterns) end-to-end, audit and resolve as much accumulated backlog as practical in one session, and document honest limitations for everything shipped.

Result: **one minor release** (v0.20.0) covering ADR-071 Phases 1+2+3, plus operational hooks F7+F8 in a follow-up commit.

## Operator instructions (still active from prior handoff)

- **Avoid `ANTHROPIC_API_KEY` billing**: provider cascade unchanged.
- **Provider-agnostic AND harness-agnostic** (ADR-062 + ADR-064 — ADR-064 reviewed today, kept Proposed).
- **Engram is the source of truth for memory**; lifecycle metadata lives in observation `content` as a `<engram-lifecycle>{...}</engram-lifecycle>` trailer.
- **Production engram daemon is read-only-friendly only**: do not `PATCH/POST/DELETE` for API exploration. See `rules/engram-api-safety.md`. (Real incident this session: obs #13283 was overwritten during HTTP discovery and reconstructed from git + session preview.)

## What shipped this session

### v0.19.0 — ADR-068 Phase 1: Adaptive Pytest (commit `02fc3b8`, released `d736875`)

- `scripts/detect_runner_capacity.py` — 6-row heuristic (cores, load, memory, battery, CI, default).
- `scripts/pytest-with-summary.sh` injects `-n <value>` adaptively when no explicit flag.
- 9 unit tests cover heuristic + override precedence.

### v0.20.0 — ADR-071 Engram Lifecycle Evolution Phases 1–3 (commits `d48dcb8`, `f2cd0aa`, `b551a2a`, `82415cb`, `9a7fb36`)

- **Phase 1**: `lib/engram_lifecycle.py` — confidence + Ebbinghaus decay + asymptotic reinforcement (β=0.15) + ranking formula `adjusted = base × (1−α) + confidence × R(t) × α` with α=0.3. Six decay classes.
- **HTTP correction**: `lib/engram_http_client.py` (the Phase 1 caveat about CLI lacking `get`/`update` was wrong — port 7437 exposes both). `rules/engram-api-safety.md` ratified after the #13283 incident.
- **Phase 2**: `lib/engram_crystallizer.py` — deterministic synthesis (no LLM in v1). Stop hook `hooks/engram-crystallize-on-session-end.sh`.
- **Phase 3**: `lib/engram_graph_walker.py` — BFS over `memory_relations` SQLite (read-only). `EngramLifecycle.search(graph_walk=True)` integrates.
- **F7+F8** (operational gotchas closed): `hooks/engram-daemon-launcher.sh` (auto-starts engram serve) + `hooks/profile-drift-autoapply.sh` (re-applies profile on script change). F8 ran during commit prep and **the 4 ADR-071 hooks are now active in `.claude/settings.json`**.
- **Tests**: 135 pass (121 unit + 14 e2e against a real sandboxed engram daemon).

### Documentation

- `docs/research/llm-wiki-v2-engram-evolution-2026-04-27.md` — analysis of the LLM Wiki v2 gist + 14 sources.
- `docs/adrs/ADR-071-engram-lifecycle-evolution.md` — full decision + addendum (HTTP discovery + Phase 2/3 shipped) + **Honest Limitations** (12 items) + **Future Work** (F1–F6 + F7–F8 with triggers).
- `docs/upstream-blockers.md` — durable tracking for `default_backend()` (cryptography 49.0.0), `rich 14→15` (cognee unpin), `wrapt 1→2` (OTel transitive).
- `docs/adrs/ADR-064-harness-agnostic-cognitive-os.md` — status review note 2026-04-27. Kept Proposed (Surfaces 2-4 unimplemented, verification suite missing). Codex/Cursor hook vocabularies confirmed compatible (web evidence).

### Plan audit (5 plans triaged, headers updated)

| Plan | Verdict |
|---|---|
| `so-existential-validation-2026-04-24` | ALIVE — 0/42, target 2026-05-15 (left as-is) |
| `hook-architecture-v2` | PARTIAL_DONE — Phase 1 shipped, Phases 2-5 real work |
| `component-scope-classification` | PARTIAL_DONE — Phases 1-2 shipped, Phases 3-4 mechanical work |
| `agent-escalation-capabilities` | ON ICE — zero implementation, no commit momentum |
| `workflow-engine` | ON ICE — zero implementation, no commit momentum |

## Pending work (not blockers)

### 1-session sized
- **`hook-architecture-v2` Phase 2** — `set-security-profile.sh` lacks SubagentStart/UserPromptSubmit/PreCompact event coverage. Mechanical extension. Highest ROI of remaining items.
- **`component-scope-classification` Phase 3** — add `scope:` tag to ~100 rules/*.md files. Mechanical, agent-friendly.
- **20+ install-test flakes under `-n auto`** — investigate root cause. Needs the suite run repeatedly with diagnostics.

### Multi-session (sprint-scope)
- `so-existential-validation` 42 tasks (target 2026-05-15)
- `component-scope-classification` Phase 4 (installer scope filtering — refactor)
- `hook-architecture-v2` Phases 3-5 (timing, hook-pipe, disable env vars)

### Conditional / triggered
- **ADR-071 F1**: Crystallizer LLM upgrade — when 30+ heuristic digests reviewed and judged low signal.
- **ADR-071 F2**: `mem_judge` writes — when engram exposes `POST /relations` or operator decides to spawn MCP subprocess.
- **ADR-071 F3**: Cross-device reinforcement — when two devices reading same `topic_key` show divergent counts.
- **ADR-071 F4**: Threshold calibration — after ≥4 weeks of `crystallization-events.jsonl` accumulated.
- **ADR-071 F5**: Phase 4 Obsidian export — when memory crosses ~500 obs and `mem_search` alone feels insufficient.
- **ADR-071 F6**: Cloud sync e2e test — when F3 lands or sync bug reported.

### Soft / deferred
- **87 decisiones pending en triage** — operator-tagged "no urgente". Spawn dedicated agent when ready.
- **ADR-064 flip to Accepted** — when Phase 2 ships and a non-CC harness produces byte-identical canonical events for a reference skill.

### Upstream-blocked (no action from us)
- `default_backend()` cleanup in hermes-agent — waits cryptography 49.0.0
- `rich 14→15` — waits cognee unpin
- `wrapt 1→2` — waits OTel transitive validation

## Honest caveats from this session

- **Crystallizer uses no LLM** — heuristic concat + dedup. Browsable digests, not smart summaries.
- **`mem_judge` supersedes is not written** — engram HTTP doesn't expose `/relations`. Phase 2 stores `crystallized:true` + `superseded_obs_ids` in trailer.
- **Reinforcement is local-only** — engram cloud sync replicates `content` but does not aggregate counters.
- **Graph walker couples to engram SQLite schema** — read-only mode is a safety floor.
- **`revision_count` is a save-count proxy**, not a distinct-event count.
- **Threshold tuning is unvalidated** — N≥5/30d, N≥10 total, τ values are defensible defaults pending real-data calibration.
- **Cloud sync compat is structurally sound but not e2e-tested** — see F6.
- **Production daemon mutation incident** (#13283) — reconstructed from git + preview. Policy now codified in `rules/engram-api-safety.md`.

## Engram session summary

Save this handoff under topic_key `session/2026-04-27/handoff`. Cross-references: `adr-071/engram-lifecycle-evolution`, `adr-068/adaptive-runner-capacity`, `adr-064/harness-agnostic`, `bugfix/13283-overwrite-incident`.

## Next-session quick start

1. Run `bash scripts/apply-efficiency-profile.sh default` if `.claude/settings.json` is missing the 4 ADR-071 hooks (F8 should auto-apply on SessionStart now, but verify).
2. Confirm `engram serve` is up: `curl -s http://127.0.0.1:7437/health` (F7 launches it on SessionStart, but verify).
3. If picking up `hook-architecture-v2 Phase 2`: open `scripts/set-security-profile.sh`, add `SubagentStart`, `UserPromptSubmit`, `PreCompact` event groups (currently only `SessionStart`/`PreToolUse`/`PostToolUse`/`Stop` are wired).
4. If picking up `component-scope-classification Phase 3`: spawn an agent with `for f in rules/*.md; do head -5 "$f"; done` to see which lack `scope:` and bulk-add via `templates/rule-template.md` pattern.

## Releases shipped today

- v0.19.0 — ADR-068 Phase 1: Adaptive Pytest
- v0.20.0 — ADR-071: Engram Lifecycle Evolution (Phases 1–3)
