<!--
RECONCILIATION STATUS: SUPERSEDED
Superseded by: ADR-028 (SO Reliability Framework — covers the MAPE-K pillars), ADR-031 (aspirational-audit), ADR-041 (exercised coverage pipeline); ws1-ws13 shipment log in status-report-april-11 + git log
Reconciled: 2026-04-21
Reason: the workstreams (WS1–WS13) substantially shipped; ADR-028 replaced the MAPE-K framing with a reliability/SLO framework. Individual workstreams remaining are tracked under their own plans (skill-atomicity-audit) or ADRs (ADR-041).
-->

# Master Plan: Self-Optimizing Agentic Primitive Pipeline

**Date**: 2026-04-10
**Status**: APPROVED
**Scope**: Cognitive OS recursive self-optimization infrastructure
**Estimated total effort**: ~15-20 sessions across 10 workstreams
**Prerequisite**: All audits completed (rules-to-hooks, skill atomicity, docs-to-skills, hook architecture, context compaction, agentic primitive scope)

---

## Vision

A Cognitive OS that recursively optimizes its own agentic primitives using its own optimization tools. The MAPE-K loop (Monitor, Analyze, Plan, Execute, Knowledge) drives continuous improvement without human intervention for safe changes.

```
MONITOR: hooks observe agentic primitive performance (tokens, latency, failures)
    |
ANALYZE: skills detect degradation patterns (fat skills, stale docs, drift)
    |
PLAN: orchestrator proposes splits, migrations, rewrites
    |
EXECUTE: SDD pipeline applies changes with verify-rollback safety net
    |
KNOWLEDGE: Engram records what worked, consequence system scores results
    |
    +---> feeds back into MONITOR (recursive loop)
```

## 6 Governing Principles

1. **"como=skill, por que=doc, no hagas X=hook"** -- Procedures are skills (active, on-demand). Knowledge is docs (passive, reference). Prohibitions are hooks (automatic, zero-token enforcement).
2. **Proactive > Reactive** -- Rules in agent context enable anticipation. Hooks enforce after the fact. Both together = defense in depth. Never remove one layer without confirming the other covers it (ref: engram #2977).
3. **Atomicity** -- One skill = one concern = one output artifact. Fat skills get split. Sub-commands become separate skills composed by the orchestrator.
4. **Recursive self-improvement** -- The OS uses /optimize-skill to improve skills, /self-improve to improve rules, and the consequence system to promote/degrade/disable agentic primitives automatically.
5. **Defense in depth** -- Security profiles (minimal/standard/paranoid) control hook registration. Capability levels auto-disable redundant gates. Neither replaces the other.
6. **Decision broadcast** -- Architectural decisions saved to Engram propagate to all future sessions and sub-agents. No decision lives only in conversation context.

---

## 10 Workstreams

### WS1: Rules-to-Hooks Phase 3-4

**Ref**: `.cognitive-os/plans/features/rules-to-hooks-refactor.md`, engram #2968

**What**: Complete the refactor by (Phase 3) building an EXCLUDED_RULES mechanism so hook-enforced rules are not loaded into agent context, and (Phase 4) slimming RULES-COMPACT.md to under 1.5K tokens.

**Current state**: Phase 1 (audit) and Phase 2 (hook registration corrections) are done. 2 hooks registered (doc-sync-detector, large-file-advisor). 3 hooks need decision (auto-refine, auto-verify, dod-gate) -- ref engram #2974.

**Remaining work**:
- Phase 3: Add `EXCLUDED_RULES` array to `self-install.sh` listing 14 rules safe to exclude (anti-hallucination, blast-radius, clarification-gate, content-policy, crash-recovery, prompt-quality, rate-limiting, skill-rewrite, auto-skill-generation, auto-repair, pre-dev-readiness-gate, audit-trail, pre-commit-gate, confidentiality-protection)
- Phase 3: Decide on auto-refine.sh, auto-verify.sh, dod-gate.sh registration (standard vs paranoid)
- Phase 4: Regenerate RULES-COMPACT.md at ~1.5K tokens (currently ~2.1K) by removing hook-covered entries

**Files affected**:
- `hooks/self-install.sh` -- add EXCLUDED_RULES array + filtering logic
- `rules/RULES-COMPACT.md` -- regenerate, trimmed
- `.claude/settings.json` -- possibly register 3 undecided hooks

**Effort**: ~1 session
**Dependencies**: None (audits complete)
**Success metric**: RULES-COMPACT < 1.5K tokens; 14 rules excluded from context load

---

### WS2: Context Compaction — Sub-Agent Return Contract + Smart Truncation

**Ref**: `.cognitive-os/plans/features/intelligent-context-compaction.md`, engram #2971

**What**: Implement WS1 (sub-agent return contract) and WS3 (smart result truncation) from the context compaction plan. These are the quick wins with highest ROI.

**Current state**: Research complete. 6 techniques identified. Projected 60-75% token savings.

**Remaining work**:
- WS1: Add structured return format to `templates/agent-preamble.md` with 1K token target
- WS1: Add `lib/return_contract_validator.py` to extract/validate structured returns
- WS3: Replace dumb head+tail truncation in `hooks/result-truncator.sh` with command-type-aware extraction (test output -> extract PASS/FAIL/counts; build -> extract errors; docker -> extract status)
- WS3: Add `lib/smart_truncator.py` with per-command-type extraction strategies

**Files affected**:
- `templates/agent-preamble.md` -- add structured return contract
- `lib/return_contract_validator.py` -- new
- `hooks/result-truncator.sh` -- rewrite truncation logic
- `lib/smart_truncator.py` -- new

**Effort**: ~2 sessions
**Dependencies**: None
**Success metric**: Sub-agent returns < 1K tokens average; result truncation preserves error/count data

---

### WS3: Context Compaction — Prompt Cache + Compaction API

**Ref**: `.cognitive-os/plans/features/intelligent-context-compaction.md` WS2+WS4, engram #2971

**What**: Implement prompt caching for executor mode sub-agents (90% input cost reduction on cached prefixes) and integrate Anthropic Compaction API for anchored iterative summarization.

**Current state**: Research complete. Requires `ORCHESTRATOR_MODE=executor` for prompt caching.

**Remaining work**:
- Add `cache_control` breakpoints to `lib/claude_executor.py` for system prompt and rules sections
- Integrate Anthropic Compaction API (beta) into `hooks/pre-compaction-flush.sh` for server-side summarization
- Add anchored iterative summarization to preserve file paths and decisions across compaction
- Filter Engram observations before injection (summarize with Haiku)

**Files affected**:
- `lib/claude_executor.py` -- add cache_control breakpoints
- `hooks/pre-compaction-flush.sh` -- integrate Compaction API
- `lib/context_compressor.py` -- new, anchored summarization
- `lib/engram_filter.py` -- new, pre-injection summarization

**Effort**: ~3 sessions
**Dependencies**: WS2 (return contract reduces what needs caching)
**Success metric**: 60-70% input cost reduction for executor mode; decisions survive compaction

---

### WS4: Skill Atomicity — 21 Remaining Splits

**Ref**: `.cognitive-os/plans/features/skill-atomicity-audit.md`

**What**: Split 25 SPLIT-CANDIDATE skills into atomic units following the 4-phase plan from the audit. Priority 1 done (how-to-extend -> 4 skills). 21 remaining.

**Current state**: Audit complete (103 skills classified). 4 skills already split from docs-to-skills Priority 1.

**Remaining work by phase**:

Phase 1 (high-impact, 4 splits):
- `release-os` -> `validate-release`, `bump-version`, `generate-changelog`, `tag-release`, `push-release`
- `cognitive-os-init` -> `detect-stack`, `generate-config`, `scaffold-project`
- `self-improve` -> `analyze-improvements`, `propose-improvements`, `apply-improvements`
- `issue-pipeline` -> delete, replace with DAG orchestration + `gh-issue-fetch` + `gh-pr-create`

Phase 2 (knowledge extraction, 4 parameterizations):
- `coverage-enforcement` -> read service root from config
- `readiness-check` + `evaluate-plan` -> read architecture criteria from `.claude/rules/`
- `secret-audit` -> discover paths from docker-compose
- `plan-feature` + `plan-bug` -> externalize architecture references

Phase 3 (composability, 2 splits):
- `agent-kpis` -> per-OKR atomic skills + META aggregator
- `singularity` -> `singularity-run`, `singularity-status`, `singularity-daemon`

Phase 4 (template dedup, 11 integrations):
- Standardize `cognee-integration`, `deepeval-integration`, `opik-integration`, `promptfoo-integration`, `ragas-integration`, `strands-evals-integration` with shared `tool-integration-template`
- Split remaining: `resource-governor`, `arena`, `webhook-trigger`, `repo-forensics`, `cognitive-os-status`

**Files affected**: 25+ skill directories under `skills/` and `packages/*/skills/`
**Effort**: ~4 sessions (1 per phase)
**Dependencies**: None (each phase is independent)
**Success metric**: SPLIT-CANDIDATE count drops from 25 to 0; no capability lost (verified via /capability-snapshot)

---

### WS5: Docs-to-Skills — 10 Conversions + 7 Pointer Trims

**Ref**: `.cognitive-os/plans/features/docs-to-skills-audit.md`, engram #3153, #3251

**What**: Convert 10 SKILL-CANDIDATE docs into atomic skills. Trim 8 SKILL-EXISTS docs to pointer stubs. Remove 2 OBSOLETE docs.

**Current state**: Priority 1 done (how-to-extend.md -> 4 skills). 9 SKILL-CANDIDATE conversions remaining. 8 SKILL-EXISTS trims remaining. 2 OBSOLETE removals remaining.

**Remaining conversions** (priority order):
1. `docs/getting-started.md` -> `/cos-setup`
2. `docs/getting-started-quick.md` -> `/cos-install`
3. `docs/quickstart.md` -> `/cos-quickstart`
4. `docs/hook-security-profiles.md` -> `/switch-security-profile`
5. `docs/plug-and-play.md` -> `/cos-docker-setup`
6. `docs/benchmarking.md` -> `/run-benchmark`
7. `docs/configurable-quality-gates.md` -> `/configure-quality-gates`
8. `docs/dogfooding.md` -> `/dogfood-check`
9. `docs/agent-teams-testing.md` -> `/test-agent-teams`

**SKILL-EXISTS trims** (8 docs -> pointer stubs):
- auto-library.md, automation-doc-sync.md, capability-snapshot.md, competitive-arena.md, definition-of-done.md, gpu-sandbox.md, health-monitoring.md, plan-system.md

**OBSOLETE removals**: benchmark-results.md, cleanup-verification.md

**Files affected**: 9 new skill directories, 8 docs trimmed, 2 docs deleted, `skills/CATALOG.md` updated
**Effort**: ~2 sessions
**Dependencies**: None
**Success metric**: ~57,500 tokens moved from always-loaded to on-demand; 0 SKILL-CANDIDATE docs remaining

---

### WS6: Agentic Primitive Scope Tags

**Ref**: `.cognitive-os/plans/features/component-scope-classification.md`, engram #3086

**What**: Add `scope: os-only|project|both` to every agentic primitive's frontmatter/header. Modify `self-install.sh` and `cos install` to filter by scope.

**Current state**: Classification audit complete (all ~400 agentic primitives classified in plan doc). Implementation deferred to refactor phase.

**Remaining work**:
- Add `scope:` frontmatter to all 103 SKILL.md files
- Add `# SCOPE:` comment header to all ~60 hook .sh files
- Add `scope:` frontmatter to all ~100 rule .md files
- Modify `hooks/self-install.sh` to read scope and skip `os-only` in target projects
- Modify `cmd/cos/` installer to filter by scope during `cos install`
- Add scope validation to `/register-component`

**Files affected**: ~260 files (frontmatter additions), `hooks/self-install.sh`, `cmd/cos/`
**Effort**: ~2 sessions (bulk frontmatter addition is mechanical)
**Dependencies**: WS1 (EXCLUDED_RULES mechanism informs scope filtering)
**Success metric**: Every agentic primitive has a scope tag; target projects receive only `project` + `both` agentic primitives

---

### WS7: Hook Architecture v2

**Ref**: `.cognitive-os/plans/features/hook-architecture-v2.md`, engram #3191

**What**: Sync `scripts/set-security-profile.sh` to emit all 7 event types (currently only 4), add 15 missing hooks to profile JSONs, add timing instrumentation, implement hook pipe composition.

**Current state**: Phase 1 done (new event hooks created). Phase 2-5 pending. Live settings.json has 21 hooks/4 events; should have 31/7 (standard) or 47/7 (paranoid).

**Remaining work by phase**:
- Phase 2 (HIGH): Sync generator script to emit TeammateIdle, TaskCreated, TaskCompleted, SubagentStart, UserPromptSubmit, PreCompact + add 15 missing hooks to profiles
- Phase 3 (MEDIUM): Add `hooks/_lib/timing.sh` instrumentation to top-10 overhead hooks
- Phase 4 (LOW): Hook pipe composition via `.hook-pipe/` files
- Phase 5 (LOW): Dynamic disable env vars (COS_SKIP_HOOKS, COS_PROFILE_OVERRIDE)

**Files affected**:
- `scripts/set-security-profile.sh` -- rewrite to emit all 7 events
- `.cognitive-os/plans/features/hook-architecture-v2-settings*.json` -- update reference profiles
- 10+ hooks under `hooks/` -- add timing instrumentation
- `hooks/_lib/hook-pipe.sh` -- new composition library

**Effort**: ~2 sessions (Phase 2 is 1 session, Phases 3-5 are 1 session)
**Dependencies**: None
**Success metric**: Generator script and live settings.json parity; all 7 events registered; top-10 hooks instrumented

---

### WS8: Auto-Classification Detector

**What**: A PostToolUse hook that detects when a new agentic primitive (skill, hook, rule, lib module) is created WITHOUT a scope tag or CORE/PACKAGE classification. Nudges the agent to classify before committing.

**Current state**: Concept only. `/register-component` exists for manual consistency checking. No automated detection on file creation.

**Remaining work**:
- Create `hooks/component-classification-detector.sh` (PostToolUse on Edit|Write)
- Detect creation of new files matching `skills/*/SKILL.md`, `hooks/*.sh`, `rules/*.md`, `lib/*.py`
- Check for `scope:` frontmatter (skills/rules) or `# SCOPE:` header (hooks)
- If missing: advisory warning suggesting `/register-component` or manual tagging
- Register in standard profile

**Files affected**:
- `hooks/component-classification-detector.sh` -- new
- `scripts/set-security-profile.sh` -- register in standard profile

**Effort**: ~0.5 sessions
**Dependencies**: WS6 (scope tags must exist to validate against)
**Success metric**: Zero new agentic primitives committed without scope tags

---

### WS9: Test Error Ratchet

**Ref**: engram #3404

**What**: Extend `hooks/pre-commit-gate.sh` to track test ERRORS (not just FAILURES) with a ratcheting baseline that only decreases.

**Current state**: pre-commit-gate.sh blocks on test failures but ignores 292 test errors (collection errors, import failures, missing fixtures).

**Remaining work**:
- Classify 292 errors: infra-dependent (skip), outdated references (fix), import errors (fix)
- Fix all fixable errors (~2-3 sessions of cleanup)
- Modify `hooks/pre-commit-gate.sh` to parse error count from pytest output
- Create `.cognitive-os/metrics/test-error-baseline.json` with initial baseline
- Implement ratchet: `current_errors > baseline` -> BLOCK commit
- On error fix: automatically decrease baseline (ratchet down)

**Files affected**:
- `hooks/pre-commit-gate.sh` -- add error tracking
- `.cognitive-os/metrics/test-error-baseline.json` -- new baseline file
- Multiple test files -- fix fixable errors

**Effort**: ~3 sessions (2 for error cleanup, 1 for ratchet mechanism)
**Dependencies**: None
**Success metric**: Error baseline decreasing over time; zero new errors introduced per commit

---

### WS10: Security Tool Activation

**What**: Move security tools from EVALUATE/WATCH to ADOPT by configuring and testing them in the standard development workflow.

**Current state**: Semgrep OFF by default. Aguara installed but unregistered. Garak skill exists but untested. mcp-scan exists but unregistered. Promptfoo exists but not integrated into CI.

**Remaining work**:
- Enable `SEMGREP_ENABLED=true` and validate with a test scan
- Register `aguara-scan.sh` in paranoid profile (already exists, just unregistered)
- Run `/vulnerability-scan` (garak) against agent preamble and validate findings format
- Run `/red-team` (promptfoo) against top-5 skills and validate findings format
- Configure `mcp-scan.sh` to run on SessionStart in paranoid profile
- Document activation status in ecosystem-tools.md

**Files affected**:
- `.env` or `cognitive-os.yaml` -- enable semgrep
- `scripts/set-security-profile.sh` -- register aguara-scan, mcp-scan in paranoid
- `packages/ecosystem-tools/rules/ecosystem-tools.md` -- update status

**Effort**: ~1 session
**Dependencies**: None
**Success metric**: Semgrep active; aguara registered; garak and promptfoo validated with real findings

---

### WS7b: Repetition Detector — Auto-Skill Generation from Patterns

**What**: A monitor that detects repetitive patterns across sessions and proposes automatic skill creation. Skills are "compiled knowledge" — they prevent models from reading base code to learn what to do, saving thousands of tokens per invocation.

**Why**: Every missing skill = code that a model must read to deduce a pattern. Without skills, the model consumes 5K+ tokens "learning" from source code each time. With a skill, it consumes ~500 tokens executing steps directly. The repetition detector closes the loop: detect pattern → generate skill → future sessions never re-learn.

**Principle**: "Skills replace code reading. The model should EXECUTE skills, not INTERPRET code."

**Three types of repetition to detect**:

1. **Cross-session tool call sequences** — Same sequence of Grep→Read→Edit→Bash appears 3+ times across sessions. Source: `skill-metrics.jsonl` tool call logs.
   - Example: "grep for test file, read it, add test case, run pytest" → `/add-test-case` skill

2. **Code boilerplate repetition** — Agent writes the same structure 3+ times in different files. Source: Edit/Write tool inputs in session transcripts.
   - Example: "create handler with error handling, DTO mapping, use case call" → `/scaffold-handler` skill

3. **Skill chain repetition** — Same skills invoked in sequence 3+ times. Source: `skill-metrics.jsonl` invocation order.
   - Example: `/detect-stack` → `/generate-config` → `/scaffold-project` always together → `/cos-init` meta-skill (already done manually this session)

**Implementation**:
- `lib/repetition_detector.py` — analyzes metrics JSONL files for repeated tool sequences, code patterns, skill chains
- `hooks/repetition-monitor.sh` — PostToolUse hook that feeds data to the detector
- Integration with `auto-skill-generator.sh` — when repetition detected, generate SKILL.md proposal
- Human gate: propose skill, don't auto-create structural skills

**Token savings model**:
- Average "read code to understand pattern": ~5K tokens
- Average skill execution: ~500 tokens
- Per detected pattern: 4.5K tokens saved per future invocation
- 10 patterns detected × 5 invocations/month = 225K tokens/month saved

**Effort**: ~2 sessions (1 for detector, 1 for integration + tests)
**Dependencies**: WS7 (auto-classifier) — shares detection infrastructure
**Success metric**: Number of auto-generated skills per month; token savings from skill usage vs code reading

---

### WS7c: Hook False Positive Auto-Tuning

**What**: Track false positive rates per hook and auto-tune thresholds when hooks block legitimate work too often.

**Why**: Hooks that block legitimate work are worse than no hooks. The clarification-gate false positive this session cost a wasted agent launch + orchestrator retry. Any heuristic hook (pattern matching, scoring) can produce false positives. Without feedback, thresholds never improve.

**Three mechanisms**:

1. **False positive tracking** — When a hook BLOCKs (exit 2) and the orchestrator re-launches with a modified prompt that succeeds, record: `{hook, block_count, retry_success_count, false_positive_rate}`. Source: correlate block events in `metrics/` with subsequent successful launches.

2. **Auto-tune thresholds** — If a hook's false positive rate exceeds 10% over 50+ samples, automatically adjust its threshold:
   - Scoring hooks (clarification-gate, blast-radius, prompt-quality): increase BLOCK threshold by 10 points
   - Pattern hooks (epic-task-detector, completeness-check): reduce sensitivity by removing weakest signal
   - Log every auto-tune to `metrics/hook-tuning.jsonl`
   - Cap: max 3 auto-tunes per hook (beyond that, hook needs human review/rewrite)

3. **User override feedback** — When the orchestrator retries after a block, the retry-success is implicit negative feedback. When the user says "that block was wrong", explicit negative feedback. Both feed into the false positive rate.

**Files**:
- `lib/hook_tuner.py` — false positive tracker + auto-tune logic
- `hooks/_lib/tuning.sh` — shared function hooks call to check if they should adjust thresholds
- `metrics/hook-false-positives.jsonl` — per-hook block/retry/success tracking
- `metrics/hook-tuning.jsonl` — auto-tune event log

**Integration with consequence system**: The consequence system degrades/promotes SKILLS. This extends it to HOOKS. Same pattern: poor performance → auto-adjust → if still poor → suggest rewrite.

**Effort**: ~1-2 sessions
**Dependencies**: None (can start immediately)
**Success metric**: False positive rate < 5% per hook after tuning stabilizes

---

### WS13: Continuous State Persistence — Preventive Crash Protection

**What**: A heartbeat system that continuously persists session state so that ANY interruption (suspend, crash, compaction, timeout) loses at most 2 minutes of work.

**Why**: Today, state persistence is reactive (save when compaction happens) or periodic but incomplete (git stash every 5 min only covers code). User requests, agent status, decisions, and plan progress are only in the context window — if the session dies, they die.

**What gets persisted every N tool calls (or every 2 min)**:
1. **In-progress work** — current todos, active agents and their descriptions
2. **Pending user requests** — from request_queue.py (already on disk per-request)
3. **Decisions made** — any `mem_save` with type "decision" that hasn't been flushed
4. **Agent status** — which agents are running, what they're doing, expected completion
5. **Plan progress** — which workstreams advanced this session

**Phase 0 (REQUIRED before implementation): State Surface Audit for Heartbeat**

Before building the heartbeat, audit ALL existing session state surfaces to determine which need heartbeat integration. For each state surface, ask: "If the session dies right now, would this state be lost?"

| State surface | State to persist? | Currently persisted? | Needs heartbeat? |
|---|---|---|---|
| `TodoWrite` state | Current task list | NO (context only) | **YES** |
| Active sub-agents | Agent IDs, descriptions, prompts | NO (context only) | **YES** |
| `request_queue.py` | Pending user requests | YES (JSONL on disk) | No (already on disk) |
| `auto-checkpoint.sh` | Uncommitted code | YES (git stash) | No (already periodic) |
| `dispatch-queue.json` | Queued agent launches | YES (JSON on disk) | No (already on disk) |
| `active-tasks.json` | Task lifecycle | YES (JSON on disk) | No (already on disk) |
| Engram saves | Decisions, discoveries | PARTIAL (saved on explicit call) | **YES** (flush unsaved) |
| Context-watchdog state | Tool call counter, threshold alerts | NO (hook internal) | **YES** |
| Conversation decisions | "We decided X mid-conversation" | NO (context only) | **YES** |
| Cost tracking | Session spend so far | PARTIAL (cost-events.jsonl) | No (already logged) |
| Test baseline | Pre-session test counts | NO (not captured yet, see WS11) | **YES** |
| Plan statuses | Which WS advanced this session | NO (only updated at wrapup) | **YES** |
| Queue advisor state | Last scoring, reorder decisions | NO (ephemeral) | Low priority |
| Hook tuning state | False positive rates | NO (not built yet, see WS7c) | Future |

This audit must be RE-RUN when new stateful surfaces or collectors are added. The heartbeat's `register()` mechanism makes this extensible — each new collector registers the state it owns.

**Implementation**:
- `lib/state_heartbeat.py` — pluggable collector architecture, writes snapshot
- `hooks/state-heartbeat.sh` — PostToolUse hook (every 10th tool call, checked via counter)
- `.cognitive-os/sessions/{id}/state-snapshot.json` — latest snapshot (overwritten each time)
- On session resume: `crash-recovery.sh` reads the snapshot and injects into context
- Each collector is a function: `def collect_X() -> dict` registered via `heartbeat.register(collect_X)`

**Anti-suspend protection**:
- macOS `caffeinate` integration: detect if battery is low → force save
- Write snapshot to BOTH local file AND engram (belt + suspenders)
- Engram save is async (non-blocking) — `mem_save` in background

**Integration with existing session lifecycle surfaces**:
- Extends `auto-checkpoint.sh` (code) with state checkpoint (context)
- Extends `pre-compaction-flush.sh` (last resort) with continuous protection
- Extends `crash-recovery.sh` (detection) with rich state to recover from
- Feeds into `session-backlog` (the snapshot IS the input for next-session inventory)

**Recovery flow**:
```
Session dies (any cause)
    ↓
Next session starts → crash-recovery.sh detects orphaned snapshot
    ↓
Loads state-snapshot.json → injects into context:
  "Previous session was working on X. Agents A, B were running.
   User had requested Y, Z which were not completed.
   Plan WS3 was in progress. Resume from here."
    ↓
Agent has full context without needing to search engram
```

**Effort**: ~2 sessions
**Dependencies**: WS2 (anchored summary), WS11 (test baseline)
**Success metric**: After ANY interruption, next session resumes with <2 min of lost context

---

### WS12: Smart Commit — Thematic Commit Splitting

**What**: A `/smart-commit` skill that analyzes staged changes and proposes thematic commit splits automatically. Classifies files by theme (lib, skills, hooks, tests, docs, config), detects dependencies between groups (test for a lib = same commit), and proposes N commits with messages.

**Audience**: both — useful for OS and any project.

**Effort**: ~1 session
**Dependencies**: None
**Success metric**: Sessions end with clean thematic commits instead of monolith commits

---

### WS11: Test Baseline Diff — Anti-Confirmation-Bias Mechanism

**Ref**: engram `pattern/orchestrator-confirmation-bias`

**What**: Automatic test-diff that captures test baseline at session start, compares after changes, and attributes new failures to the current session — removing orchestrator interpretation from the loop.

**Why**: The orchestrator repeatedly assumed test failures were "pre-existing" before verifying. This happened 3 times in one session (+12 failures attributed to "probably pre-existing" when they were all ours). The orchestrator has the same minimum-output bias as sub-agents — quality gates must apply to the orchestrator too.

**Implementation**:
- At SessionStart (`hooks/session-init.sh`): run `pytest --tb=no -q 2>&1 | tail -1` → save to `.cognitive-os/sessions/{id}/test-baseline.txt`
- New hook `hooks/test-baseline-diff.sh` (PreToolUse on Agent for commits, or Stop hook):
  - Run pytest again, compare against baseline
  - Parse: `{passed_before} vs {passed_after}`, `{failed_before} vs {failed_after}`, `{errors_before} vs {errors_after}`
  - If `failed_after > failed_before` OR `errors_after > errors_before`: **BLOCK** with "These N failures were introduced this session: {list}"
  - If `passed_after > passed_before`: report as positive (new tests added)
- Never allow the orchestrator to claim "pre-existing" without the diff proving it

**Files affected**:
- `hooks/session-init.sh` — add baseline capture (1 line: pytest summary → file)
- `hooks/test-baseline-diff.sh` — new hook (PreToolUse for git commit, or Stop)
- `.cognitive-os/sessions/{id}/test-baseline.txt` — per-session baseline
- `tests/behavior/test_baseline_diff.py` — tests for the mechanism itself

**Principle**: "Guilty until proven innocent" — any failure not in baseline is assumed ours.

**Effort**: ~1 session
**Dependencies**: WS9 (test ratchet) — complementary, not blocking
**Success metric**: Zero sessions where new failures are incorrectly attributed to "pre-existing"

---

## Implementation DAG

```
            WS1 (rules-to-hooks P3-4)
           / |
          /  v
WS2 (return contract)    WS6 (scope tags)
    |                      |
    v                      v
WS3 (prompt cache)       WS8 (auto-classifier)
                           |
                           v
              WS7 (hook arch v2) ----+
                                     |
                                     v
                            WS9 (test ratchet)

WS4 (skill atomicity)  -- independent, 4 phases
WS5 (docs-to-skills)   -- independent
WS10 (security tools)  -- independent
WS11 (test baseline diff) -- independent, complements WS9
WS12 (smart-commit) -- independent, audience: both
WS13 (continuous state persistence) -- complements WS2 + WS11
```

**Critical path**: WS1 -> WS2 -> WS3 (context optimization chain)
**Parallel tracks**: WS4, WS5, WS10 can run anytime
**Sequential**: WS6 -> WS8 (scope tags before auto-classifier)
**Sequential**: WS7 after WS1 (hook registration settled before architecture v2)

## Execution Priority

| Priority | Workstream | Effort | Impact | Rationale |
|----------|-----------|--------|--------|-----------|
| P0 | WS1: Rules-to-Hooks P3-4 | 1 session | HIGH | Unblocks WS2, WS7; immediate token savings |
| P0 | WS2: Return Contract + Smart Truncation | 2 sessions | HIGH | Biggest context savings; no dependencies |
| P1 | WS4-Phase1: High-Impact Splits | 1 session | HIGH | 4 critical skills split; immediate composability |
| P1 | WS9: Test Error Ratchet | 3 sessions | HIGH | Broken window policy violation; 292 errors |
| P2 | WS5: Docs-to-Skills | 2 sessions | MEDIUM | 57K tokens to on-demand loading |
| P2 | WS7: Hook Arch v2 | 2 sessions | MEDIUM | Generator parity; timing instrumentation |
| P2 | WS10: Security Tools | 1 session | MEDIUM | Defense in depth activation |
| P3 | WS3: Prompt Cache + Compaction | 3 sessions | HIGH | 60-70% cost reduction (needs executor mode) |
| P3 | WS6: Scope Tags | 2 sessions | MEDIUM | Cleaner installs; bulk mechanical work |
| P3 | WS4-Phase2-4: Remaining Splits | 3 sessions | MEDIUM | Incremental atomicity improvements |
| P4 | WS8: Auto-Classifier | 0.5 sessions | LOW | Prevention; needs WS6 first |

## Success Metrics (Overall)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Agent context overhead at session start | ~97K tokens | < 40K tokens | Sum of loaded rules + catalog |
| RULES-COMPACT size | ~2.1K tokens | < 1.5K tokens | Token count of RULES-COMPACT.md |
| Sub-agent return size (avg) | ~5K tokens | < 1K tokens | Mean from completion-gate metrics |
| SPLIT-CANDIDATE skills | 25 | 0 | Count from skill atomicity audit |
| SKILL-CANDIDATE docs | 10 | 0 | Count from docs-to-skills audit |
| Test errors baseline | 292 | < 50 | pytest error count |
| Agentic primitives without scope tag | ~400 | 0 | /register-component audit |
| Hook profile generator parity | 4/7 events | 7/7 events | set-security-profile.sh event count |
| Security tools active | 1 (content-policy) | 5+ | ecosystem-tools status check |

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Capability loss during rule exclusion | MEDIUM | HIGH | /capability-snapshot before and after every WS1 change |
| Skill split breaks existing workflows | LOW | MEDIUM | SDD verify phase validates each split; META wrappers preserve backward compat |
| Scope tags bulk edit introduces errors | LOW | LOW | Mechanical operation; /register-component validates |
| Test error cleanup takes longer than estimated | HIGH | LOW | Ratchet mechanism works incrementally; baseline decreases over time |
| Prompt cache requires executor mode adoption | MEDIUM | MEDIUM | WS3 is P3 priority; WS2 delivers value without executor mode |

## Relationship to Existing Plans

| Plan | Relationship |
|------|-------------|
| `rules-to-hooks-refactor.md` | WS1 completes phases 3-4 of this plan |
| `hook-architecture-v2.md` | WS7 implements this plan |
| `intelligent-context-compaction.md` | WS2+WS3 implement workstreams from this plan |
| `skill-atomicity-audit.md` | WS4 executes the priority refactoring plan from this audit |
| `docs-to-skills-audit.md` | WS5 executes the conversion backlog from this audit |
| `component-scope-classification.md` | WS6 implements the scope system from this plan |
