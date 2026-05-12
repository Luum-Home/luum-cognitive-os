# cos-dispatch: Migration Plan

## Current State

48 hooks in `.claude/settings.json` (28 sync, 20 async), adding ~36.5s/session overhead.

## Migration Tiers

### Tier 1: Native Go Validators (17 hooks)

CPU-bound, stateless checks that benefit most from Go's speed. Eliminates subprocess overhead entirely.

| Hook | Why Native | Category |
|------|-----------|----------|
| secret-detector.sh | Regex-heavy, runs on every edit. Go regex is 10-50x faster than bash grep | CPU |
| dispatch-gate.sh | 9 Python cold starts → 1 Go function. Biggest single win | CPU |
| rate-limiter.sh | Counter + time window. Runs on every Bash call (70x/session) | CPU |
| rate-limit-protection.sh | O(n) Python subprocess loop → single file read | CPU |
| clarification-gate.sh | Pure shell + jq pattern matching | CPU |
| blast-radius.sh | File counting + scope analysis | CPU |
| content-policy.sh | Text pattern matching against YAML policy | CPU |
| architecture-compliance.sh | Path matching + pattern rules | CPU |
| claim-validator.sh | Text analysis in agent output | CPU |
| trust-score-validator.sh | Score comparison — trivial | CPU |
| completeness-check.sh | Pattern matching on prompt text | CPU |
| prompt-quality.sh | Scoring text on 5 dimensions | CPU |
| epic-task-detector.sh | Keyword matching for bulk operations | CPU |
| agent-prelaunch.sh | Task file management with jq | CPU |
| agent-checkpoint.sh | Task state update | CPU |
| aguara-scan.sh | External tool invocation (graceful skip if absent) | IO |
| error-pattern-detector.sh | JSONL tail + pattern matching | CPU |

### Tier 2: Native Go Transformers (5 hooks)

These modify data rather than allow/deny.

| Hook | Phase | Priority | What it does |
|------|-------|----------|-------------|
| result-truncator.sh | Post | 10 | Truncate large tool outputs |
| inject-phase-context.sh | Pre | 20 | Add phase rules to agent prompts |
| subagent-context-injector.sh | Pre | 30 | Inject context into sub-agent prompts |
| context-diet.sh | Post | 15 | Compress context to save tokens |
| audit-id-enricher.sh | Pre | 5 | Add audit IDs to requests |

### Tier 3: Bash Plugins (14 hooks)

These invoke external tools or have complex bash logic. The plugin adapter wraps them with JSON stdin/stdout subprocess protocol.

| Hook | Why Plugin |
|------|-----------|
| semgrep-scan.sh | Invokes semgrep binary |
| parry-scan.sh | Invokes parry-guard binary |
| error-pipeline.sh | Complex error handling with remediation |
| code-review-on-commit.sh | Complex git + diff analysis |
| infra-health.sh | Docker/service health checks |
| mcp-scan.sh | MCP config scanning |
| auto-checkpoint.sh | Git stash operations |
| auto-repair-dispatcher.sh | Error classification + repair dispatch |
| dequeue-notify.sh | Agent queue management |
| consequence-evaluator.sh | Consequence engine Python calls |
| scope-creep-detector.sh | Scope analysis with task context |
| doc-sync-detector.sh | Documentation sync detection |
| auto-skill-generator.sh | Skill file generation |
| state-heartbeat.sh | State snapshot to disk |

### Tier 4: Lifecycle Hooks (8 hooks)

Called once per session. Keep as bash, invoke via plugin adapter.

| Hook | When Called |
|------|-----------|
| self-install.sh | SessionStart |
| session-init.sh | SessionStart |
| session-resume.sh | SessionStart |
| crash-recovery.sh | SessionStart |
| pre-compaction-flush.sh | PreCompact |
| session-learning.sh | Stop |
| session-cleanup.sh | Stop |
| user-prompt-capture.sh | UserPromptSubmit |

### Tier 5: Migrate to CLAUDE.md Rules (4 hooks)

Purely advisory hooks better served as prompt-time rules.

| Hook | CLAUDE.md Rule |
|------|---------------|
| completeness-check.sh | "Agent prompts must list ALL files, item counts, and verification commands" |
| prompt-quality.sh | "Agent prompts must include: file paths, action verb, context, acceptance criteria, bounded scope" |
| assumption-tracker.sh | "Agents should not assume. If uncertain, ask for clarification" |
| scope-proportionality.sh | "Fix/bug tasks should patch, not rewrite or delete files" |

### Tier 6: Replaced by Pattern Tracker (~10 hooks)

These are subsumed by the dispatcher's built-in pattern tracking and auto-improvement pipeline.

| Hook | Replaced By |
|------|------------|
| error-pattern-detector.sh | PatternDetector |
| error-learning.sh | PatternTracker |
| session-learning.sh | PatternDetector.AnalyzeSession() |
| session-knowledge-extractor.sh | PatternDetector + engram |
| observability-trace.sh | ExecutionRecord logging |
| kpi-trigger.sh | PatternTracker metrics |
| task-recorder.sh | ExecutionRecord logging |
| context-watchdog.sh | Dispatcher timeout management |
| guardrails-validator.sh | Native Go validator |
| skill-feedback-tracker.sh | FeedbackDecision tracking |

## Migration Order

### Phase 1 (Weeks 1-2): Foundation

Ship `cos-dispatch` binary alongside existing hooks. No hooks removed yet.

1. Core binary with CLI, config loading, provider detection
2. Validator and Transformer interfaces
3. Plugin adapter (wrap ALL existing hooks as plugins — zero behavior change)
4. Sequential executor
5. Claude Code provider adapter
6. Register `cos-dispatch` as single PreToolUse + PostToolUse hook in settings.json
7. Existing hooks run as plugins through the dispatcher

### Phase 2 (Week 3): Parallel Execution + Providers

1. Parallel executor with CPU/IO/Git category pools
2. Codex + Gemini provider adapters
3. Response builders for all three providers
4. Config merging (TOML + cognitive-os.yaml)

### Phase 3 (Weeks 4-5): Native Validators

1. Port Tier 1 hooks to native Go validators (17 hooks)
2. Port Tier 2 hooks to native Go transformers (5 hooks)
3. Remove ported bash hooks from plugin path
4. Benchmark and validate performance improvement

### Phase 4 (Week 6): Pattern Tracking

1. SQLite schema and Tracker implementation
2. Instrument dispatcher to record every execution
3. Detector implementation (6 pattern types)
4. Session-end analysis trigger

### Phase 5 (Weeks 7-8): Auto-Generator + More Providers

1. Generator implementation (template-based code generation)
2. Feedback loop tracking
3. Cursor + Windsurf provider adapters
4. `cos-dispatch review` CLI for generated artifact review
5. Migrate Tier 5 hooks to CLAUDE.md rules
6. Remove Tier 6 hooks (replaced by pattern tracker)
