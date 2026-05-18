---
date: 2026-05-16
topic: goal-features-internals
status: research
engram_obs_codex: 20986
engram_obs_claude: 20987
topic_key_codex: research/codex-goals-internals
topic_key_claude: research/claude-code-goal-internals
---

# Goal Feature Internals: OpenAI Codex vs Claude Code

**Research date:** 2026-05-16
**Author:** Consolidated from two sub-agent deep-research sessions (engram obs #20986 and #20987)
**Retrieval status:** Both engram entries retrieved successfully — full content used below.

---

## Executive Summary

1. **Both systems implement a "goal" as explicit persistent state**, not a prompt pattern. Codex stores goals in SQLite (`thread_goals` table, Rust struct); Claude Code stores the condition in session state and applies it via a Stop hook. Neither is just a repeated system prompt.

2. **The evaluator architecture diverges sharply.** Codex uses LLM self-evaluation: the main model calls `update_goal(status="complete")` after performing a rigorous in-prompt completion audit. Claude Code uses a *separate* small model (Haiku by default) as an independent evaluator — the primary design motivation is preventing rationalization bias.

3. **Budget handling is explicit in Codex, implicit in Claude Code.** Codex has structured `token_budget` and `time_used_seconds` fields, a distinct `budget_limited` state, and a `budget_limit.md` template injected at exhaustion. Claude Code has no built-in token cap; users must embed stop conditions in the condition text (e.g., "or stop after 20 turns").

4. **Pause/resume is native to Codex, absent from the Claude Code built-in.** Codex ships `/goal pause`, `/goal resume`, and a dedicated paused state. Claude Code's built-in lacks this; community re-implementations add it via PostCompact and SessionStart hooks.

5. **The primary prompt-injection defense is different in each system.** Codex wraps the user objective in `<untrusted_objective>` XML tags in every injected template. Claude Code's approach is architectural: the condition is out-of-band and evaluated by a separate model that cannot be influenced by content placed in the conversation.

6. **Compaction resilience is a known gap in both systems, with confirmed bugs.** Codex Issue #19910 (open as of 2026-05-16): mid-turn compaction can drop the continuation prompt, leading to premature false completion. Claude Code: the built-in resets turn count and token-spend baseline on `--resume`; community impls use PostCompact hooks to preserve full goal state.

7. **Feature maturity is similar but Codex is earlier.** Codex goals shipped April 30, 2026 (v0.128.0), still behind a feature flag. Claude Code /goal shipped May 12, 2026 (v2.1.139) and received two bug-fix releases within days (v2.1.140, v2.1.141). Both are experimental.

---

## Section 1: OpenAI Codex `goals` Internals

*Source: engram obs #20986 — 29 URLs, CONFIRMED from official docs and Rust source code.*

### Storage

Goals are stored in a SQLite table `thread_goals` (migration 0029, PR #18073). There is one row per thread maximum. The data is a Rust struct `ThreadGoal`, persisted via the app-server — it is NOT a YAML file, NOT a JSON file, NOT in the system prompt.

**Schema fields:**

| Field | Type | Notes |
|-------|------|-------|
| `goal_id` | UUID | Regenerated on every replacement; stale-update protection via `expected_goal_id` check |
| `objective` | String | Max 4,000 chars (`MAX_THREAD_GOAL_OBJECTIVE_CHARS`) |
| `status` | Enum | See states below |
| `token_budget` | Optional i64 | `None` = unlimited |
| `tokens_used` | i64 | Running counter, updated at turn/tool/mutation boundaries |
| `time_used_seconds` | i64 | Wall-clock elapsed via `GoalWallClockAccountingSnapshot` |

### Goal States

The internal Rust enum uses: `active` / `paused` / `budget_limited` / `complete`.
The CLI-facing names are: `pursuing` / `paused` / `achieved` / `unmet` / `budget-limited`.

**NOTE:** This is a confirmed inconsistency — see Section 4 (Adversarial Findings).

### Iteration Loop

A runtime event `MaybeContinueIfIdle` fires after each turn. If: goal is `active`, budget allows, thread is idle, no user input is queued, and at least one tool call was made in the last turn — the runtime appends the `continuation.md` template and re-invokes the model. This is process-internal; it is NOT a bash wrapper or an external cron job.

**Spin guard:** An `AtomicBool continuation_suppressed` is set to `true` when a continuation turn produces zero tool calls, preventing infinite planning-only loops. Only reset by user input, explicit tool calls, or external mutations.

**Concurrency:** `accounting_lock: Semaphore(1)` serializes token accounting updates.

### Done-Decision

The model is the sole decision-maker for completion. It calls the `update_goal` structured tool with `status="complete"`. This is a structured tool call, NOT free-text. The `continuation.md` template injects a rigorous multi-step completion audit protocol:

1. Restate the objective as concrete deliverables
2. Build a prompt-to-artifact checklist
3. Inspect actual files, command output, test results, PR state
4. Verify any manifest/verifier/test suite covers all requirements
5. Reject proxy signals alone (passing tests only count if they cover every requirement)
6. Treat uncertainty as "not achieved"
7. Only call `update_goal` when the audit fully passes

### Budget Cap

When `tokens_used` approaches `token_budget`, the runtime injects `budget_limit.md` (suppressed during goal-completion turns to avoid confusing the model). The `budget_limit.md` template explicitly forbids calling `update_goal` and instructs graceful wrap-up. Budget exhaustion transitions to `budget_limited`, NOT `complete`.

### Prompt-Injection Defense

Both `continuation.md` and `budget_limit.md` wrap the user objective in `<untrusted_objective>{{ objective }}</untrusted_objective>` tags, preventing the goal text from being treated as higher-priority instructions than the system's audit directives.

### Model Tools Exposed to Agent

The goal-facing model tools are exactly three: `get_goal` (read), `create_goal` (only when none exists), `update_goal` (mark complete only). Pause, resume, budget-limit, and clear transitions are system/user-controlled exclusively — the model cannot pause itself.

### Feature Configuration

Goals require `goals = true` under `[features]` in `~/.codex/config.toml` (or `/experimental` in TUI). Clients must also set `capabilities.experimentalApi: true` for goal JSON-RPC.

### Implementation Timeline

Five PRs by `etraut-openai`, ~15K additions, April 16–25, 2026:

| PR | Component |
|----|-----------|
| #18073 | Persistence foundation (SQLite, Rust model, state APIs) |
| #18074 | App-server JSON-RPC (`thread/goal/set`, `get`, `clear`, notifications) |
| #18075 | Model tools (`get_goal`, `create_goal`, `update_goal`) |
| #18076 | Runtime behavior (continuation, accounting, budget steering) |
| #18077 | TUI controls (slash commands, status display) |

Shipped in Codex CLI 0.128.0 (April 30, 2026). Made discoverable in 0.129.0 (May 7, 2026).

### Known Bugs

1. **Mid-turn compaction drops audit context (Issue #19910, OPEN):** The continuation prompt and audit requirements can be lost after mid-turn compaction. Agent may falsely mark complete after inspecting git status alone ("confirmation bias"). Proposed fix: re-inject ~462-token continuation prompt during mid-turn compaction. Not confirmed merged as of 2026-05-16.

2. **Long input rejection (Issue #21477):** Raw `/goal` text exceeding 4,000 chars is rejected before model can normalize. Fix proposed; status unclear.

3. **Goal degradation (community behavioral):** Model produces a "degraded version of the deliverable" — technically satisfies part of the goal but not the actual intent. Observed in community testing.

---

## Section 2: Claude Code `/goal` Internals

*Source: engram obs #20987 — 22+ URLs + local app.asar inspection, CONFIRMED from official docs and changelog.*

### Implementation

`/goal` is a built-in CLI command shipped in Claude Code v2.1.139 (2026-05-12). It is NOT a skill file, NOT a user-defined Stop hook, and NOT an external plugin. Internally it is implemented as a **session-scoped wrapper around a prompt-based Stop hook**.

The Electron app bundle (`/Applications/Claude.app/Contents/Resources/app.asar`, 24MB) is minified/obfuscated; direct source inspection via `strings` returned no readable function names.

### Goal Data Structure

**Confirmed (official docs):**
- One goal active per session maximum
- Condition: natural language string, up to 4,000 characters
- Persisted across `--resume`/`--continue`: condition survives, but turn count, timer, and token-spend baseline reset on resume
- Cleared goals NOT restored on resume

**Inferred (from community re-implementations `jthack/claude-goal` and `chrischabot/claude-code-goal`):**

```
State (markdown with YAML frontmatter):
  version
  session_id         (adopted by first hook execution)
  status: pursuing | paused | achieved | cleared
  iteration          (current turn)
  max_iterations     (optional)
  completion_promise (sentinel)

Sections: Objective, Continuation Notes, Iteration Log, Compact Summaries
```

Community file path: `.claude/goals/current.goal.md` and `.claude/goals/<session-id>.goal.md`.
Built-in likely uses in-memory session state + settings persistence, not markdown files.

### Evaluator

**This is the key architectural difference from Codex.** Claude Code uses a **separate evaluator model** — not the main agent judging itself. Official docs: "completion is decided by a fresh model rather than the one doing the work."

- Evaluator model: Haiku by default (configurable)
- Evaluator is tool-free: reads only what Claude surfaced in the conversation transcript
- Returns: binary yes/no + short reason string
- Reason is displayed in status view and passed as guidance to the next turn if "no"
- Evaluation tokens billed separately on Haiku — described as "typically negligible"

### Iteration Loop

Per-turn Stop hook loop:

1. Claude completes a turn (edits, runs commands, etc.)
2. Stop hook fires
3. Condition + full conversation transcript → Haiku evaluator
4. Evaluator returns yes/no + reason
5. **NO:** Stop hook returns `decision: "block"` with reason as guidance → Claude starts new turn
6. **YES:** goal clears, "achieved" entry recorded in transcript, control returns to user

**v2.1.141 fix:** Evaluator now waits for all concurrent tool calls and background shells to complete before checking condition. (Previously fired prematurely.)

### Condition / Success Criteria Format

Natural language string. Docs recommend including:
- One measurable end state (test result, build exit code, file count, empty queue)
- A stated check ("npm test exits 0", "git status is clean")
- Constraints that must not change
- Optional: turn/time bound ("or stop after 20 turns")

### Persistence

- Session-scoped (vs Stop hooks which apply to all sessions via settings file)
- Survives `--resume`: condition carries over; turn count, timer, token-spend baseline reset
- Cleared goals NOT restored on resume
- Cleared by: `/goal clear` (aliases: stop, off, reset, none, cancel) or `/clear`

**Inferred:** Not compaction-resilient at the turn-count level. Community impls use PostCompact hook to preserve full goal state.

### Comparison Advantages vs Codex

Per official docs, structural differences over a plain "keep iterating until X" prompt:

| Aspect | Plain prompt | /goal |
|--------|-------------|-------|
| Continuation enforcer | Claude self-decides | Separate Haiku evaluator |
| Evaluator bias | Rationalization risk | Fresh model, no prior work context |
| Visibility | None | Live overlay: turns/time/tokens |
| Persistence | In context window (compaction risk) | Out-of-band, survives compaction |
| Non-interactive | Requires re-prompting | `claude -p "/goal ..."` runs to completion |

### Known Bugs

1. **Silent failure when hooks disabled (v2.1.140 fix):** Prior to v2.1.140, `/goal` silently failed if hooks were disabled or `disableAllHooks: true` was set. Fixed: now shows clear error explaining why.

2. **Premature evaluator firing (v2.1.141 fix):** Evaluator previously fired while background shells or delegated subagents were still running. Fixed: evaluator waits for all concurrent tool calls to complete.

3. **Compaction resets metrics:** Turn count, timer, and token-spend baseline all reset on `--resume`. The condition itself is preserved, but progress metrics are lost.

4. **No native pause/resume:** The built-in implementation lacks pause/resume. Community demand is high; multiple third-party reimplementations add this via Stop + SessionStart hook pairs.

---

## Section 3: Side-by-Side Comparison Table

| Axis | Claude Code `/goal` | OpenAI Codex `/goal` |
|------|--------------------|--------------------|
| **Storage** | Session state (in-memory + resume file, likely `~/.claude/projects/<hash>/`) | SQLite `thread_goals` table, one row per thread |
| **Storage format** | Internal (obfuscated); community uses markdown + YAML frontmatter | Rust struct `ThreadGoal` persisted via app-server |
| **Evaluator** | Separate model (Haiku by default), tool-free, reads transcript only | LLM self-evaluation by the main model via structured tool call |
| **Done decision** | Evaluator returns yes → Stop hook unblocks | Main model calls `update_goal(status="complete")` structured tool |
| **Loop driver** | Per-turn Stop hook — external to the model | Internal runtime event `MaybeContinueIfIdle` — process-internal |
| **Budget cap** | Implicit: include in condition text ("or stop after 20 turns") | Explicit: `token_budget` field (optional i64), `time_used_seconds` tracked |
| **Budget-exhausted state** | None built-in | Distinct `budget_limited` state; `budget_limit.md` template injected |
| **Goal states** | active / achieved / cleared (built-in); pursuing / paused / achieved / cleared (community) | pursuing / paused / achieved / unmet / budget-limited (CLI); active / paused / budget_limited / complete (internal Rust enum) |
| **Prompt-injection defense** | Architectural: condition out-of-band, evaluated by separate model | Syntactic: `<untrusted_objective>` XML wrapper in both templates |
| **Pause/resume** | Not built-in; community impls add via hooks | Native: `/goal pause`, `/goal resume`, paused state persists across restarts |
| **Compaction resilience** | Condition preserved; metrics reset on resume | Known bug (#19910): continuation prompt can be dropped during mid-turn compaction |
| **Known bugs** | Silent failure (fixed v2.1.140), premature eval (fixed v2.1.141), no native pause | Mid-turn compaction drops audit context (#19910, open), long input rejection (#21477) |
| **Tools exposed to agent** | None — agent uses normal tools; evaluator has no tools | `get_goal`, `create_goal`, `update_goal` (complete only); pause/resume/clear are user-controlled only |
| **Feature flag required** | No — available after workspace trust dialog | Yes — `goals = true` in `~/.codex/config.toml` |
| **Non-interactive mode** | `claude -p "/goal ..."` runs to completion | `codex --approval-mode full-auto` |
| **UI indicator** | `◎ /goal active` overlay with elapsed time | Desktop app UI with pause button; status shows pursuing/paused/complete |
| **Telemetry** | Turns evaluated, elapsed time, token spend, last evaluator reason | Time used, tokens used, token budget remaining |
| **Shipped** | v2.1.139, 2026-05-12 | v0.128.0, 2026-04-30 |
| **Status** | Experimental (hooks-dependent) | Experimental (feature flag required) |

---

## Section 4: Adversarial Findings

### Inconsistency A: Codex Goal State Names

The Codex sub-agent report (engram obs #20986) lists two distinct sets of state names for the same feature:

- **Internal Rust enum (from `goals.rs`):** `active` / `paused` / `budget_limited` / `complete`
- **CLI-facing names (from Issue #20536):** `pursuing` / `paused` / `achieved` / `unmet` / `budget-limited`

The two sets do not map 1:1. The CLI exposes `unmet` which does not appear in the Rust enum, and the Rust enum uses `active` where the CLI says `pursuing` and `complete` where the CLI says `achieved`. The sub-agent flagged this at source level (linking to Issue #20536) and stated it as CONFIRMED. However, the exact mapping between `unmet` and any internal enum variant was not resolved.

**Assessment:** The discrepancy is real and likely reflects a presentation layer translation in the TUI/CLI output layer that renames internal states. It is NOT a contradiction between the two sub-agent research sessions — it is a confirmed internal inconsistency in the Codex source that was accurately surfaced by the researcher. However, the mapping of `unmet` to an internal Rust state remains an **open question**.

Additionally, the Claude Code sub-agent report (engram obs #20987) cross-referenced the Codex state table as: `pursuing / paused / achieved / unmet / budget-limited`, which matches the CLI-facing names but was pulled from the GitHub Issue reference (issue #56085 — the Claude Code feature request referencing Codex parity), not directly from the Rust source. This is consistent but not independently verified against `goals.rs`.

### Inconsistency B: Codex Separate Validator Model Claim

One source (`explainx.ai`) claims: "a small, fast validator model runs after every step" in Codex — which would mean Codex also uses a separate evaluator model. The Codex sub-agent report explicitly marked this as **UNCONFIRMED/possibly inferred**, noting it is NOT confirmed by official source or Rust source analysis. The Rust runtime shows only LLM self-evaluation via `continuation.md` prompt.

This creates an apparent surface similarity between the two systems that is NOT confirmed. Claude Code's separate evaluator (Haiku) is CONFIRMED by official docs. Codex's equivalent is NOT confirmed and should not be assumed.

### Inconsistency C: Cross-Topic Retrieval Behavior

The Claude Code sub-agent report (obs #20987) contains an internal note: "no prior engram entry found for `research/codex-goals-internals`" — suggesting that at the time of writing, the Claude Code research agent could not cross-retrieve the Codex entry. This is expected behavior (the two research sessions were launched concurrently or in close sequence), but it means the cross-system comparison table embedded in obs #20987 was constructed from the same agent's independent Codex knowledge, not from the Codex engram entry. The consolidated table in this report supersedes and reconciles both.

**No fabrication occurred in either sub-agent report** — both marked claims as CONFIRMED/INFERRED/UNCONFIRMED with source citations. The inconsistencies documented above are attribution and state-naming issues, not invented claims.

---

## Section 5: Design Implications for a COS-Native `/goal` Skill

The following open decisions must be resolved before a COS `/goal` skill can be specified.

### 5.1 Evaluator Architecture: Self-Eval vs Separate-Eval

**Decision:** Should the COS `/goal` use self-evaluation (Codex pattern) or a separate evaluator model (Claude Code pattern)?

- **Self-eval (Codex):** Lower cost per evaluation (no separate model call), requires heavily structured audit prompt, known rationalization bias risk, cannot audit tools it didn't call.
- **Separate-eval (Claude Code):** Eliminates rationalization bias, evaluator is tool-free (reads transcript only), adds Haiku call latency per turn, requires condition to be verifiable from transcript evidence alone.

**Recommendation signal:** The Claude Code research explicitly positions separate-eval as "the key architectural innovation." The Codex approach relies on prompt engineering discipline in `continuation.md`. A COS implementation that leverages Haiku for evaluation is consistent with our model routing rules (haiku = evaluation/formatting tasks).

**Open:** Should the evaluator be configurable (default haiku, allow sonnet for complex multi-step conditions)?

### 5.2 Budget Specification: Structured Budget vs Natural Language Clause

**Decision:** Should COS `/goal` support a structured token/turn budget (Codex pattern) or require users to embed stop conditions in the condition text (Claude Code pattern)?

- **Structured (Codex):** Explicit `token_budget` field, distinct `budget_limited` state, auto-injected wind-down template. More reliable for cost governance.
- **NL clause (Claude Code):** Simpler API, requires evaluator to parse and track turn counts from transcript. Fragile for exact numeric bounds.

**Recommendation signal:** COS has a resource governance rule (>80% triggers sonnet, >95% triggers haiku, >100% BLOCK). A structured budget field integrates with `lib/rate_limiter.py` and `resource_governor`. A natural-language-only approach does not.

**Open:** Should a `--max-turns` CLI flag be added alongside the condition string?

### 5.3 Loop Driver: Stop Hook vs Internal Loop

**Decision:** Should COS `/goal` use the Claude Code Stop hook pattern or implement a process-internal loop (Codex `MaybeContinueIfIdle` pattern)?

- **Stop hook:** Composable with existing hook infrastructure, no new runtime code, transparent to users. Depends on hooks being enabled.
- **Internal loop:** More reliable (not subject to hook disabling), but requires changes to the Claude Code harness adapter (`lib/harness_adapter/`), and we cannot modify Claude Code's internal runtime.

**Constraint:** COS runs on the Claude Code harness. We cannot implement a `MaybeContinueIfIdle` equivalent without hook access. **The Stop hook pattern is the only viable option for COS.**

**Open:** Should the Stop hook be registered via `add-hook` skill at `/goal` invocation time, or pre-registered in settings?

### 5.4 Persistence Layer: Session-Scoped vs Engram-Backed

**Decision:** Should COS goal state be session-scoped (Claude Code built-in) or persisted to engram (enabling cross-session goal resumption)?

- **Session-scoped:** Simple, no engram dependency, but goal is lost if session ends.
- **Engram-backed:** Goals survive session end and compaction, can be resumed by name, supports a backlog of pending goals. Consistent with how COS persists all other task state.

**Recommendation signal:** COS's session-close documentation discipline and session handoff pattern strongly favor engram persistence. The `--resume` pattern's weakness (turn count reset) is a known limitation that engram could address.

**Open:** Should goal state be stored under `goal/<session-id>/current` or `goal/<project>/<name>`? Named goals would allow `pending goal queue` patterns.

### 5.5 Pause/Resume: Required at Launch or Deferred

**Decision:** Should COS `/goal` ship pause/resume at launch (Codex native pattern) or ship without it and add later (Claude Code built-in pattern)?

Community demand for pause/resume in Claude Code is documented (multiple GitHub issues, forum threads). Codex added it natively. Given COS uses engram for persistence, pause = "save state to engram, clear active hook"; resume = "restore from engram, re-register hook."

**Open:** Minimum viable: pause via `/goal pause` writing to engram + deregistering hook. Resume via `/goal resume` reading engram + re-registering hook.

### 5.6 Prompt-Injection Defense

**Decision:** Should the condition be wrapped in XML tags (Codex pattern) or isolated architecturally via separate evaluator (Claude Code pattern)?

If COS uses a separate evaluator (recommendation in 5.1), architectural isolation is the primary defense. XML wrapping can be added as defense-in-depth when passing the condition to the evaluator prompt.

**Open:** Define the evaluator prompt template. Should it include a completion audit checklist (Codex style) or be minimal (Claude Code style)?

---

## Section 6: Sources

### Codex Sources (25+ URLs from engram obs #20986)

1. https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
2. https://github.com/openai/codex
3. https://github.com/openai/codex/blob/main/codex-rs/core/src/goals.rs
4. https://github.com/openai/codex/blob/rust-v0.128.0/codex-rs/core/src/goals.rs
5. https://github.com/openai/codex/blob/main/codex-rs/core/templates/goals/continuation.md
6. https://github.com/openai/codex/blob/6014b6679ffbd92eeddffa3ad7b4402be6a7fefe/codex-rs/core/templates/goals/continuation.md
7. https://github.com/openai/codex/blob/6014b6679ffbd92eeddffa3ad7b4402be6a7fefe/codex-rs/core/templates/goals/budget_limit.md
8. https://github.com/openai/codex/pull/18073
9. https://github.com/openai/codex/pull/18075
10. https://github.com/openai/codex/issues/19910
11. https://github.com/openai/codex/issues/20536
12. https://github.com/openai/codex/issues/21477
13. https://github.com/openai/codex/discussions/21764
14. https://gist.github.com/patleeman/b1b5768393f9bf2f60865b1defeeb819
15. https://developers.openai.com/codex/use-cases/follow-goals
16. https://developers.openai.com/codex/app-server
17. https://developers.openai.com/codex/changelog
18. https://simonwillison.net/2026/Apr/30/codex-goals/
19. https://www.agentupdate.ai/news/openai-codex-cli-goal-feature-0-128-0/
20. https://ralphable.com/blog/codex-goal-command-ralph-loop-openai-built-in-autonomous-coding-agent-2026
21. https://www.mindstudio.ai/blog/codex-goal-ralph-loop-14-hour-autonomous-task
22. https://www.jdhodges.com/blog/codex-goal-feature-review/
23. https://help.apiyi.com/en/codex-goal-mode-autonomous-task-guide-en.html
24. https://community.openai.com/t/experimenting-with-codex-deciding-its-own-next-steps/1380898
25. https://devtoolpicks.com/blog/codex-goal-command-vs-claude-code-agents-2026
26. https://explainx.ai/blog/goal-mode-ai-agents-complete-guide-2026
27. https://www.howdoiuseai.com/blog/2026-05-05-openai-codex-goal-the-new-long-horizon-mode-for
28. https://www.developersdigest.tech/blog/codex-changelog-april-2026
29. https://kingy.ai/ai/openai-codex-goal-the-new-long-horizon-mode-for-agentic-coding/

### Claude Code Sources (22+ URLs from engram obs #20987)

1. https://code.claude.com/docs/en/goal — OFFICIAL DOCS (primary)
2. https://code.claude.com/docs/en/hooks — OFFICIAL stop hook schema
3. https://code.claude.com/docs/en/plugins-reference — OFFICIAL plugin system
4. https://github.com/anthropics/claude-code/releases/tag/v2.1.139 — Release notes
5. https://raw.githubusercontent.com/anthropics/claude-code/refs/heads/main/CHANGELOG.md — Changelog
6. https://github.com/anthropics/claude-code/issues/56085 — Feature request (Codex parity)
7. https://github.com/anthropics/cwc-long-running-agents — Official Anthropic primitives repo
8. https://github.com/jthack/claude-goal — Community re-implementation
9. https://github.com/chrischabot/claude-code-goal — Community re-implementation (detailed state docs)
10. https://github.com/itsuzef/goalkeeper — Subagent judge pattern
11. https://venturebeat.com/orchestration/claude-codes-goals-separates-the-agent-that-works-from-the-one-that-decides-its-done
12. https://explainx.ai/blog/claude-code-goal-command-long-running-agents-2026
13. https://www.mindstudio.ai/blog/claude-code-goal-command-autonomous-tasks
14. https://apidog.com/blog/goal-command-codex-claude-code-autonomous-agents/
15. https://help.apiyi.com/en/claude-code-goal-mode-keep-working-until-done-guide-en.html
16. https://blog.dailydoseofds.com/p/claude-codes-goal-command
17. https://devtoolpicks.com/blog/codex-goal-command-vs-claude-code-agents-2026
18. https://developertoolkit.ai/en/claude-code/advanced-techniques/goal-workflows/
19. https://claudefa.st/blog/tools/hooks/hooks-guide
20. https://wmedia.es/en/tips/claude-code-goal-stop-condition
21. https://findskill.ai/blog/claude-code-goal-command/
22. https://forum.cursor.com/t/add-autonomous-goal-mode-similar-to-claude-code-s-goal/160374
23. https://alex000kim.com/posts/2026-03-31-claude-code-source-leak/
24. https://dev.to/kolkov/we-reverse-engineered-12-versions-of-claude-code-then-it-leaked-its-own-source-code-pij
25. https://news.ycombinator.com/item?id=47609294
26. Local: /Applications/Claude.app/Contents/Resources/app.asar (24MB, strings-searched)
27. Local: ~/.claude/ directory listing

---

## Section 7: Engram References

| Field | Codex Entry | Claude Code Entry |
|-------|------------|-------------------|
| Topic key | `research/codex-goals-internals` | `research/claude-code-goal-internals` |
| Observation ID | #20986 | #20987 |
| Type | discovery | discovery |
| Project | luum-cognitive-os | luum-cognitive-os |
| Created | 2026-05-16 18:47:47 | 2026-05-16 18:48:26 |
| Retrieval status | **FULL CONTENT RETRIEVED** | **FULL CONTENT RETRIEVED** |

Both entries retrieved successfully via `mem_search` followed by `mem_get_observation`. No content was fabricated. All CONFIRMED/INFERRED/UNCONFIRMED tags from the original sub-agent research are preserved in the section summaries above.
