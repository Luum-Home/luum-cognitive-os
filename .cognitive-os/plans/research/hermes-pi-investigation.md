# Hermes & Pi Investigation — Consolidated Research Report

Generated: 2026-04-08
Investigation scope: 11 agents across 2 rounds
Repositories: NousResearch/hermes-agent, badlogic/pi-mono
Licenses: Both MIT — code AND patterns fully adoptable

---

## Executive Summary

11 agents ran across 2 rounds of investigation into Hermes Agent (Nous Research) and Pi coding agent (Mario Zechner / badlogic). Both repositories are MIT licensed, meaning Cognitive OS can adopt code directly, not just patterns.

Key finding: COS is approximately 30% real and 70% aspirational. Seven of 8 compared features are WORSE than the corresponding Hermes or Pi implementation.

Root cause: 137 commits in 5 days (March 27-31, 2026), with design-first development that never completed bottom-up integration. The result is a well-documented system that largely does not integrate at runtime.

---

## 1. Hermes Agent — Architecture & Key Features

### 1.1 Overview

- Python 3.10+, monolithic AIAgent class (9,431 lines in run_agent.py)
- Built by Nous Research, 33K+ GitHub stars, MIT license
- Self-reinforcing learning loop, persistent memory, 15-platform gateway
- Production-deployed and actively maintained

### 1.2 Self-Reinforcing Learning Loop

The learning loop is Hermes's most distinctive feature. It runs continuously in the background and is the mechanism by which the agent improves itself without user intervention.

- Skill nudge counter: `_skill_nudge_interval=10`, configurable per instance
- Background review agent: daemon thread, full AIAgent fork, max 8 iterations per review cycle
- Three review prompts: skill review, memory review, combined (all three run on rotation)
- Skills guidance in system prompt: auto-patch stale or underperforming skills in-place
- The review agent has direct access to the `skill_manage` tool (full CRUD on skills)

The nudge counter increments on every turn. When it reaches the threshold, the background agent wakes, reviews recent interactions, and rewrites skills that underperformed. This is a real LLM evaluating context, not regex or heuristics.

### 1.3 Memory System

Hermes uses a two-file model with strict size limits and multiple safety mechanisms:

- Two-file model: MEMORY.md (2200 char limit) + USER.md (1375 char limit), `§` delimiter for sections
- Frozen snapshot pattern: memory loaded once at session start only, preserves prefix cache hit rates
- File locking: `fcntl.flock` on sidecar `.lock` files, atomic `os.replace()` for crash safety
- Injection defense: `<memory-context>` XML fencing, sanitize any fence tags before writing

**Holographic plugin** (advanced retrieval):
- SQLite + FTS5 for full-text search
- HRR (Holographic Reduced Representations) vectors for semantic similarity
- 3-score hybrid retrieval: FTS5 40% + Jaccard 30% + HRR 30%
- Trust-weighted results (observations have credibility scores)
- Temporal decay (recent memories score higher)

**Honcho plugin** (external API):
- External memory API with dialectic reasoning (contradiction detection)
- User profiles with long-term preference tracking
- Auto-sync per turn (not per session)

### 1.4 Security

Hermes has a multi-layer security model that goes well beyond what COS currently implements.

**Memory content scanning:**
- 12 threat patterns covering prompt injection, privilege escalation, exfiltration
- Invisible Unicode detection (zero-width characters, homograph substitution)
- Runs before any memory is persisted to disk

**Context file scanning:**
- 10 patterns applied to AGENTS.md and HERMES.md before file content is injected into prompts
- Catches malicious instructions embedded in project-level config files

**Skills guard:**
- Trust tiers: builtin / trusted / community / agent-created
- Quarantine workflow: suspicious skills are isolated before execution
- Agent-created skills (from the background review agent) run at the lowest trust tier by default

**Tirith pre-execution scanner:**
- Homograph URL detection (IDN confusables)
- Pipe-to-interpreter pattern detection (`curl | bash`, `wget | sh`)
- Terminal escape injection detection
- Runs before any shell command is executed

### 1.5 Hidden Features (Second Pass)

Features discovered in the second round of investigation that were missed in the first pass:

**Prompt caching:**
- Uses `system_and_3` cache type (Anthropic extended prompt caching)
- Approximately 75% reduction in input token cost on long sessions
- Works by keeping the system prompt + first 3 turns in the prefix cache

**Shadow git checkpoints:**
- Uses `GIT_DIR` environment variable redirect to a separate `.hermes-checkpoints/` directory
- Creates checkpoints without any `.git` pollution in the working tree
- Does not interfere with the project's own git history

**Cron with script injection:**
- Cron jobs can reference external scripts rather than inline prompts
- Script stdout is injected as additional context when the job fires
- At-most-once crash semantics: job is marked in-flight before execution, cleared on success

**ACP adapter:**
- Agent Communication Protocol implementation for agent-to-agent interoperability
- Enables Hermes instances to communicate with other ACP-compatible agents

**Credential pool:**
- 4 rotation strategies: `fill_first`, `round_robin`, `random`, `least_used`
- Supports multiple API keys per provider, auto-rotates on rate limit
- Pool state persisted across sessions

**Delegate tool:**
- `MAX_CONCURRENT_CHILDREN=3`, `MAX_DEPTH=2`
- Parent can block specific tools from being available to child delegates
- Children cannot create further children beyond the depth limit

**Insights engine:**
- Analyzes historical session data (not just current session)
- Identifies patterns across sessions: recurring failures, frequently used skills, cost trends

**Context compressor:**
- Triggers at 50% context usage (not 70% or 85% like COS targets)
- Two-phase: cheap heuristic pruning first, then LLM summarization if still over budget
- Iterative summaries: each compaction builds on the previous summary
- 600 second cooldown between compactions to prevent thrashing

**Cost tracking:**
- `CanonicalUsage` dataclass with `Decimal` precision (avoids float rounding errors)
- Multi-provider normalization: maps OpenAI, Anthropic, Gemini, etc. to a common schema
- `cost_status` taxonomy: `nominal`, `elevated`, `high`, `critical`
- Actual cost attached to every agent completion record

**Smart model routing:**
- Per-turn cheap-route heuristic: classifies message complexity before choosing model
- Simple messages (greetings, short queries) automatically route to cheaper model
- Classification is fast (rule-based), not an LLM call

**Other:**
- 13 built-in personalities (not just system prompt variations — affects tool availability)
- Browser recording: saves browser automation sessions for replay
- Worktree isolation: each long-running task gets its own git worktree

---

## 2. Pi Coding Agent — Architecture & Key Features

### 2.1 Overview

- TypeScript monorepo, 7 packages in clearly defined layers
- Created by Mario Zechner (badlogic), powers OpenClaw (160K+ GitHub stars), MIT license
- Radically minimal core: 7 tools only (read, bash, edit, write, grep, find, ls)
- No MCP in core — MCP is an extension

Pi's design philosophy is the inverse of COS: start with the minimum that actually works, then extend. The core is small enough to be fully understood. Extensions add capabilities without modifying core.

### 2.2 Agent Loop

Pi uses a double-while pattern with two injection queues:

- **Outer loop**: manages session lifetime and compaction triggers
- **Inner loop**: processes turns until agent stops
- **Steering messages**: mid-turn corrections injected by extensions (user input, test results)
- **Follow-up messages**: injected after agent would otherwise stop, to continue work
- **beforeToolCall / afterToolCall hooks**: allow extensions to intercept, modify, or block tool calls

The injection queue design means extensions can add real-time feedback without interrupting the conversation structure.

### 2.3 Tool System

Pi's tool system has a clean separation between definition and runtime:

- **Dual-form tools**: `ToolDefinition` (contains rendering hints for UI) → `AgentTool` (runtime executor)
- **Pluggable BashOperations / EditOperations**: the bash and edit implementations can be swapped for remote execution (e.g., SSH into a container)
- **BashSpawnHook**: extensions can rewrite commands or inject environment variables before execution
- **withFileMutationQueue**: per-file promise-based serialization — all writes to the same file are serialized; symlink-aware so `file.ts → ../src/file.ts` resolves to the same queue slot

The mutation queue is the key correctness mechanism. Without it, concurrent tool calls to the same file produce non-deterministic results.

### 2.4 Extension System

Pi's extension system is the most flexible of the two agents investigated:

- 26+ lifecycle events covering: session, agent, turn, message, tool, and control flow
- Extensions can: register new tools, add slash commands, bind keyboard shortcuts, register models
- Full UI primitive API: `select`, `confirm`, `input`, `notify`, `setStatus` — extensions can prompt the user
- **No hardcoded system prompt** — the system prompt is entirely assembled by extensions at session start

This means the core agent has no opinions about how it should behave. All behavior is injected by extensions. This is architecturally cleaner than COS's approach of hard-coding behavior in rules files.

### 2.5 Compaction

Pi's compaction is structurally aware, not just length-based:

- **Structural cut-points**: the compaction algorithm never cuts in the middle of a tool call / tool result pair
- **LLM summarization template**: Goal / Constraints / Progress / Decisions / Next Steps / Critical Context / Files
- **Iterative update via UPDATE_SUMMARIZATION_PROMPT**: each new compaction updates the previous summary rather than regenerating from scratch
- **Split-turn handling**: if compaction is triggered mid-turn (between tool call and result), the algorithm handles the incomplete state correctly
- **File operation tracking**: reads and writes are tracked as XML tags in the summary (`<read-files>`, `<modified-files>`) so the agent always knows what it touched
- **Extension hooks**: `session_before_compact` fires before compaction, allowing extensions to save state

### 2.6 Hidden Features (Second Pass)

**pi-mom:**
- Slack bot implementation built on Pi
- Two-file context: structured JSONL (machine-readable state) + plaintext log (human-readable history)
- Demonstrates that Pi's architecture works for async, non-interactive use cases

**pi-pods:**
- GPU pod lifecycle manager for running open-source LLMs
- Supports vLLM, multi-GPU configurations
- Manages container startup, health checking, and teardown

**Web UI:**
- Built with Lit-element web components
- 4-backend model discovery: lists available models from Anthropic, OpenAI, local Ollama, custom endpoints
- JavaScript REPL sandbox: safe execution of agent-generated JavaScript
- Artifact renderers: code, markdown, HTML, images rendered inline

**Session branching:**
- Full DAG session structure with `parentId` on each session node
- `navigateTree()` for jumping between branches
- Fork support: create a new branch from any point in session history

**19 built-in slash commands**, including branching, compaction control, and model switching.

**Self-documenting:**
- Injects its own documentation file paths into the system prompt
- Agent reads documentation on-demand rather than loading all docs upfront
- Reduces baseline context cost

**Compaction with reasoning:**
- Passes `reasoning="high"` to capable models during summarization
- Better summaries at the cost of slightly more compute

**Retry with regression guard:**
- Specific test for the retry → tool_use → await → full loop cycle
- Guards against the case where retry logic breaks the tool response awaiting

**Pluggable settings storage:**
- Three backends: file (default), in-memory (for tests), workspace (per-project)
- Settings are not global — can be scoped to a workspace

---

## 3. Cross-Reference Analysis

### 3.1 Best of Both (Combine)

For each of these 10 dimensions, the correct approach is to combine techniques from both agents rather than choosing one:

| Dimension | From Hermes | From Pi |
|-----------|-------------|---------|
| Context Management | Iterative summaries, 2-phase pruning, 600s cooldown | Structural cut-points, file-op tracking, split-turn handling |
| Tool Safety | Path overlap detection, destructive command heuristic | withFileMutationQueue (real serialization, symlink-aware) |
| Prompt Construction | Security scanning, invisible Unicode, model-family guidance | Compositional buildSystemPrompt, tool-conditional guidelines |
| Session Persistence | Cost accounting, FTS5, jitter write safety | UUID-chained JSONL, typed entries, firstKeptEntryId |
| Extensions | on_pre_compress hook, background prefetch | 26-event typed bus, UI primitives, tool registration |
| Error Handling | Decorrelated jitter backoff, compressor cooldown | Proactive reserve-token compaction before hitting limit |
| Cost Tracking | Full system: CanonicalUsage, Decimal, multi-provider | Per-model cost config, deep-merge overrides |
| Security | Trust-tier skill gate, quarantine, injection patterns | (COS already has: Semgrep, Aguara, content-policy) |
| Model Fallback | Per-turn cheap-route heuristic, silent fallback | model_select event, typed model registry |
| Events / Streaming | Memory provider lifecycle hooks | 26-event typed bus with interceptors |

The pattern: Hermes excels at backend mechanisms (cost tracking, security scanning, learning loops). Pi excels at architectural cleanliness (extension bus, mutation queues, compaction structure). COS should adopt both.

---

## 4. COS Reality Audit

### 4.1 The Numbers

| Metric | Value |
|--------|-------|
| Total commits | 137 |
| Time period | March 27-31, 2026 (5 days) |
| Average commits per day | 27.4 |
| Maximum commits in a single day | 47 (day 2) |
| Features committed in first 2h 38m | 12 |

This commit velocity is not sustainable engineering. It is feature scaffolding.

### 4.2 Classification of Current COS State

| Category | Count | Percentage |
|----------|-------|------------|
| Hooks registered AND running | 25 of 84 | 30% |
| Rules with automated enforcement (hooks exist) | ~20 of 94 | 21% |
| Rules purely aspirational (LLM behavioral guidance only) | ~48 of 94 | 51% |
| Learning loop connections that exist (cross-imports) | 0 of 5 | 0% |
| Token overhead vs stated target of 3,500 tokens | 93,700 tokens | 2,677% over target |

### 4.3 Missing Hooks (Described in Rules, Do Not Exist on Disk)

The following 7 hooks are referenced in rules documentation but have no corresponding `.sh` file:

1. `hooks/auto-refine.sh` — referenced in closed-loop-prompts.md and phase-aware-agents.md
2. `hooks/auto-repair-dispatcher.sh` — referenced in auto-repair.md
3. `hooks/auto-verify.sh` — referenced in agent-quality.md
4. `hooks/dod-gate.sh` — referenced in definition-of-done.md
5. `hooks/error-learning.sh` — referenced in error-learning.md
6. `hooks/parry-scan.sh` — referenced in parry-integration.md
7. `hooks/skill-feedback-tracker.sh` — referenced in skill-management.md

Rules describing these hooks as "always active" are factually incorrect. The behavior they describe does not run.

### 4.4 Dead Code (Hooks Exist But Are Not Registered)

59 of 84 hooks (70%) exist on disk but are not registered in `settings.local.json`. They never execute. Some examples:

- `hooks/adversarial-review.sh`
- `hooks/blast-radius.sh`
- `hooks/consequence-evaluator.sh`
- `hooks/scope-proportionality.sh`
- `hooks/trust-score-validator.sh`

The rules for these hooks say "always active via PostToolUse hook." This is false. They are never invoked.

### 4.5 Disconnected Systems (Zero Integration)

The "self-reinforcing learning loop" described in COS involves these 5 components:

1. `lib/error_classifier.py` — classifies errors
2. `lib/consequence_engine.py` — evaluates agent performance
3. `lib/skill_archive.py` — archives skill versions
4. `lib/prompt_classifier.py` — classifies user prompts
5. `hooks/auto-skill-generator.sh` — generates skills from complex tasks

Cross-import analysis: **zero imports between these files**. Each module is an island. No data flows between them. The "loop" does not loop.

### 4.6 Root Cause Analysis

The failure mode is consistent across all discovered gaps:

1. **Speed over depth**: 27 commits/day average means features were described faster than they were built
2. **Tests verify structure, not integration**: tests check that files exist and have expected sections, not that the systems connect
3. **Top-down design without bottom-up integration**: the rules and documentation were written first, implementation was left for later
4. **Framework effect**: the impressive catalog of 94 rules and 84 hooks creates the appearance of a complete system
5. **Rules self-justify**: the phrase "always active" in a rule file means "loaded into LLM context," not "enforced at runtime"

The distinction matters: a rule that says "agents MUST classify complexity before starting" is a behavioral instruction to an LLM. A hook that blocks agent launch when complexity is not classified is enforcement. COS has mostly the former and very little of the latter.

---

## 5. Head-to-Head Quality Comparison

### 5.1 Verdicts

| Feature | COS vs Hermes | COS vs Pi | Why COS Loses |
|---------|--------------|-----------|---------------|
| Skill nudge / review counter | WORSE | N/A | Hermes: real LLM review agent in background daemon. COS: regex-based extraction, no LLM evaluation of skill quality |
| Session logs | WORSE | WORSE | Both: native DB or typed JSONL with full metadata. COS: read-only parser over Claude's native logs, limited control |
| Dynamic tool registration | EQUAL | WORSE | Pi: native `registerTool()` API in extension system. COS: bash scripts in `dynamic-tools/`, no extension bus |
| Background review agent | WORSE | N/A | Hermes: full AIAgent fork in daemon thread, 8 iterations. COS: `background-agent-reminder.sh` outputs text, does not launch any agent |
| Implicit feedback | WORSE | N/A | Hermes: LLM evaluates context for feedback signals. COS: `prompt_classifier.py` uses regex only, misses semantic meaning |
| Hybrid retrieval | WORSE | N/A | Hermes: 3-score FTS5+Jaccard+HRR. COS: Jaccard used only in cost_predictor.py, not connected to Engram |
| File mutation queue | WORSE | WORSE | Both: real serialization. COS: `concurrent-write-guard.sh` is advisory, prints a warning, does not serialize |
| Structured compaction | WORSE | WORSE | Both: LLM-driven with structured templates. COS: `context-management.md` is a reminder to the LLM, not a compaction engine |

### 5.2 Where COS Is Differentiated (Not Compared Above)

These features exist in COS without equivalent in Hermes or Pi:

- **Trust scoring**: multidimensional (verification evidence, acceptance criteria, self-awareness, proportionality) with machine-parseable header
- **Adversarial review protocol**: mandatory finding requirement, severity tiers (BLOCKER/CONCERN/SUGGESTION/QUESTION)
- **Safety mesh multi-layer**: 10-layer defense stack with phase-aware enforcement
- **Engram topic key prefix system**: `planning/`, `implementation/`, `docs/`, `agent/`, `sre/`, `architecture/`, `sprint/`, `config/`, `bugfix/`
- **Multi-model routing table**: per-skill model assignment with confidence levels and cost data
- **Phase-aware behavior**: reconstruction / stabilization / production / maintenance phases with different enforcement levels
- **SDD pipeline**: spec-driven development with proposal → spec → design → tasks → apply → verify → archive

These are genuine COS contributions that neither Hermes nor Pi have. The trust scoring and adversarial review in particular are more sophisticated than anything in the investigated repos.

---

## 6. What We Already Have (Do Not Reinvent)

Before building anything, verify these existing COS components. They cover some of the same ground as Hermes/Pi features:

| Feature | COS Status | File |
|---------|-----------|------|
| Skill nudge counter (basic) | EXISTS — but regex-only, not LLM | `hooks/auto-skill-generator.sh` |
| Append-only session logs | EXISTS — native Claude JSONL + parser | `lib/session_parser.py` |
| Dynamic tool registration | EXISTS — bash scripts, not typed | `lib/dynamic_tool_creator.py` |
| Jaccard similarity | PARTIAL — cost prediction only, not Engram | `lib/cost_predictor.py` |
| Implicit feedback | PARTIAL — regex classification, no LLM | `lib/prompt_classifier.py` |
| File mutation advisory | PARTIAL — warning only, not serialization | `hooks/concurrent-write-guard.sh` |
| Structured compaction | PARTIAL — LLM instruction, not engine | `rules/context-management.md` |
| Background review | PARTIAL — text reminder, no agent launch | `hooks/background-agent-reminder.sh` |

The pattern: COS has the concept described but not the implementation completed.

---

## 7. What We Must Build

### 7.1 Missing — Build from Scratch

Features that do not exist in any form in COS:

1. **User modeling**: no user preference aggregation across sessions, no `USER.md` equivalent
2. **Trust per memory item**: Engram observations have no credibility rating; all memories are treated equally
3. **Content security scanning for memory**: nothing scans memory content for injection patterns before `mem_save`
4. **Context injection fencing**: memories are injected raw into prompts; no `<memory-context>` or equivalent fencing
5. **LLM-driven compaction summarization**: `pre-compaction-flush.sh` saves state but does not summarize; the compaction itself is handled by Claude's native mechanism without structured templates
6. **Parallel tool execution categorization**: no mechanism to identify which tools can safely run in parallel vs. which must serialize
7. **Session branching**: COS sessions are linear; no fork or DAG structure

### 7.2 From Hermes to Adopt

Priority-ordered list of Hermes features to bring into COS:

1. **Background review sub-agent** — this is the core of Hermes's learning loop. A real LLM evaluating skill performance on a nudge counter. COS's version outputs text; Hermes's version actually rewrites skills.
2. **Prompt caching system_and_3** — approximately 75% reduction in input token cost on long sessions. Zero behavioral change required. High ROI, low risk.
3. **Shadow git checkpoints** — cleaner than `git stash` (which pollutes git history). Use `GIT_DIR` redirect to a separate checkpoint directory.
4. **Skills guard trust-tier model** — builtin / trusted / community / agent-created with quarantine workflow. COS has no trust tiers for skills.
5. **CanonicalUsage cost tracking with Decimal precision** — COS uses float arithmetic for costs. Hermes uses `Decimal`. On accumulated multi-session cost tracking, float drift compounds.
6. **Cron script injection pattern** — jobs can reference external scripts; stdout injected as context. More flexible than inline prompts.
7. **Context injection fencing** — wrap memory content in `<memory-context>` tags before injection. Simple to implement, meaningful security improvement.
8. **Invisible Unicode detection** — add to `hooks/secret-detector.sh` or create a new `hooks/unicode-sanitizer.sh`. Hermes's implementation is ~30 lines.

### 7.3 From Pi to Adopt

Priority-ordered list of Pi features to bring into COS:

1. **Structural compaction cut-points** — never cut at a toolResult. COS's compaction has no structural awareness; it can cut mid-tool-call and corrupt the conversation structure.
2. **withFileMutationQueue** — replace `concurrent-write-guard.sh` (which only warns) with real per-file promise-based serialization. This is a correctness fix, not an optimization.
3. **Compaction with iterative summary updates** — each compaction should update the previous summary rather than regenerating from scratch. Reduces LLM cost on long sessions.
4. **File operation tracking in compaction summaries** — track `<read-files>` and `<modified-files>` across compactions so the agent always knows what it touched even after multiple compactions.
5. **Self-documenting system prompt** — inject doc file paths into the system prompt, read on-demand. Reduces baseline context from ~93,700 tokens to potentially under 10,000.
6. **Pluggable settings storage** — file / in-memory / workspace backends. Enables proper test isolation and per-project configuration without global state.

---

## Sources

- Hermes Agent repository: https://github.com/NousResearch/hermes-agent (MIT License)
- Pi Mono repository: https://github.com/badlogic/pi-mono (MIT License)
- Hermes documentation: https://hermes-agent.nousresearch.com/docs/
- Pi site: https://shittycodingagent.ai/
- OpenClaw security analysis: https://dev.to/jahanzaibai/openclaws-security-crisis
- Persistent AI agents comparison: https://thenewstack.io/persistent-ai-agents-compared/
