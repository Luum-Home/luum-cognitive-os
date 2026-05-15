# Cognitive OS -- Frequently Asked Questions

> 65 questions. Every answer is a capability you did not know existed.
> Component counts: 57 hooks, 55 rules, 72 skills, 22 lib modules, 1714 tests.

---

## 1. What Is This?

### What is Cognitive OS?

An operating system for AI coding agents. It wraps Claude Code with 57 hooks, 55 rules, 72 skills, 22 Python library modules, and a persistent memory layer -- turning a general-purpose LLM into a governed, self-correcting, self-improving engineering organization that remembers everything across sessions and learns from every failure.

### What problem does it solve?

Without structure, AI agents do the minimum viable work, forget everything between sessions, ship incomplete features, and repeat the same mistakes. Cognitive OS fixes every one of these with mandatory acceptance criteria on every prompt, adversarial reviews that prohibit "looks good," persistent memory via Engram, error learning that captures every failure to JSONL, trust scoring that forces agents to admit uncertainty, and a self-correcting loop that retries failures up to 3 times before escalating to a human. The system is validated by 1714 automated tests across 64 test files.

### How is it different from just using Claude Code?

Claude Code is a runtime. Cognitive OS is the kernel, filesystem, and application layer running on top of it. Without Cognitive OS, Claude Code has no memory between sessions, no quality enforcement, no cost tracking, no structured pipeline, and no way to learn from its mistakes. Cognitive OS adds 57 hooks that intercept every single tool call, 55 rules that constrain behavior in real time, 72 skills that encode domain knowledge, and Engram for persistent memory that survives across sessions and context compactions.

### Can I use it with any project?

Yes. The core system is language-agnostic and framework-agnostic. Run `/cognitive-os-init` and it auto-detects your stack -- package.json, go.mod, Cargo.toml, pyproject.toml, docker-compose.yml -- and generates project-specific rules, patterns, and configuration. The universal layer (hooks, rules, skills) handles governance; the generated project layer handles language specifics. Python ML project, Go microservices, React SPA, Java monolith -- it works on all of them.

### What are the three technology layers?


### What does "agent operating system" mean?

Traditional OS: process management, file systems, device drivers. Cognitive OS: session management (57 hooks), persistent memory (Engram with SQLite WAL), and skills (device drivers for domains). Hooks are the kernel intercepting every tool call. Rules are security policies enforced in real time. Skills are installed programs. Engram is the filesystem that persists across reboots. Metrics are the system logs.

---

## 2. Zero-Touch Engineering

### What is Zero-Touch Engineering?

The north star: the codebase ships itself. A GitHub issue is opened, the webhook server detects trigger keywords, the issue pipeline classifies it, creates a git worktree, runs the full SDD pipeline (explore through verify), opens a pull request, posts status comments on the issue, and sends you a Telegram notification -- all without a single human keystroke. You review the PR when you are ready.

### How does the issue-to-PR pipeline work?

`python lib/issue_pipeline.py 42` takes a GitHub issue number and produces a pull request in 7 automated steps: fetch issue via `gh` CLI, classify (feature/bug/chore) using labels and title heuristics, create an isolated git worktree with deterministic port allocation, run all 7 SDD phases inside the worktree, push the branch, create a PR with `gh pr create` referencing `Closes #42`, and post status comments on the original issue. The entire chain is a single function call.

### How do webhooks trigger pipelines automatically?

The webhook server (`lib/webhook_trigger.py`) is a FastAPI endpoint that receives GitHub webhook events. When an issue is opened, labeled, or commented with trigger keywords (`[sdd-auto]`, `[ai-workflow]`, `@luum-bot`), it validates the HMAC-SHA256 signature, classifies the issue, generates a change name, and launches the SDD pipeline in a background thread. It posts real-time status comments on the GitHub issue as each phase completes or fails.

### What is the Singularity controller?

The autonomous brain of Cognitive OS. It implements a continuous MAPE-K loop (Monitor-Analyze-Plan-Execute-Knowledge) that polls 7 event sources -- GitHub issues, error patterns, stale docs, KPI degradation, skill failures, coverage drops, and circuit breaker states -- classifies and prioritizes them, respects budget limits and cooldowns, and launches the appropriate pipeline via `ClaudeExecutor`. Run it as a one-shot (`python lib/singularity.py run`), a cron job, or a daemon (`python lib/singularity.py daemon --interval 300`).

### What is batch execution?

The batch runner (`lib/batch_runner.py`) executes multiple SDD changes sequentially: `python lib/batch_runner.py add-auth refactor-payments fix-cache --fast-forward`. It supports per-change phase overrides via YAML batch files, continue-on-failure mode, dry-run preview, cost tracking per phase, and JSON report output for CI/CD consumption. Failed changes print resume commands so you can restart exactly where they stopped.

### What cascade does a single GitHub issue trigger?

Issue opened with `[sdd-auto]` -> webhook validates HMAC -> issue classified as feature/bug/chore -> worktree created with unique branch -> 7 SDD phases execute (explore, propose, spec, design, tasks, apply, verify) -> each phase saves artifacts to Engram -> apply runs the PITER loop (implement, test, evaluate, refine) -> verify runs adversarial review -> on CRITICAL failures, verify-apply retries up to 3 times -> PR created -> status comments posted on issue -> Telegram notification sent -> lessons learned archived to Engram. One label, twelve autonomous actions.

### How does the domain router customize verification?

The domain router (`lib/domain_router.py`) analyzes affected file paths to classify changes into 6 domains -- backend, frontend, infrastructure, database, security, API -- each with weighted evaluation criteria, domain-specific red flags, and verification commands. A change touching `/auth/` paths gets security-focused review (token handling, access control, OWASP compliance). A change touching `/migrations/` gets database-focused review (rollback safety, index strategy, backward compatibility). Security domains always take priority even as a minority of changed files.

### How safe is autonomous mode?

Seven safety boundaries are always enforced. Circuit breaker OPEN events always escalate to humans -- never auto-resolved. Daily budget caps stop all pipelines at the configured limit. Concurrency is capped at 3 parallel executions. Event cooldowns prevent thrashing (1 hour per event type). Phase-dependent restrictions limit what auto-executes in production/maintenance. Auto-repair never touches database migrations, authentication code, payment logic, `.env` files, or git history. The model downgrade chain (opus -> sonnet -> haiku) activates automatically under budget pressure.

---

## 3. The SDD Pipeline

### What is SDD?

Spec-Driven Development: an 8-core-phase pipeline, with optional init/bootstrap helpers, that transforms an idea into verified, archived code. Every phase produces a persistent artifact stored in Engram. Every decision is traceable. Every phase has acceptance criteria. If verification fails, the system retries up to 3 times before escalating to a human. It is the antidote to "the agent wrote something, I hope it works."

### What are the eight phases?

**Explore** (analyze codebase), **Propose** (formal proposal with scope and risks), **Spec** (detailed requirements with test scenarios), **Design** (architecture and component decisions), **Tasks** (granular implementation breakdown), **Apply** (sub-agent implements the tasks), **Verify** (adversarial review against the spec), **Archive** (permanent record with lessons learned). Each phase produces an artifact. The dependency graph enforces that spec requires proposal, tasks require spec + design, apply requires tasks, and verify requires apply.

### What is the generator-evaluator loop?

When `/sdd-verify` returns FAIL with CRITICAL issues, the system enters an automatic retry loop: it re-launches `/sdd-apply` with the specific failure context (which tests failed, which requirements are unmet, which files have errors), then re-runs `/sdd-verify`. This loop repeats up to 3 times. Each retry gets a fresh sub-agent with only the failure context -- no accumulated noise. After 3 failures, the system stops and escalates with a full diagnosis report.

### What happens if my session dies mid-pipeline?

All SDD state is persisted in Engram under `planning/{change-name}/state` with the current phase, retry count, and full attempt history. Run `/sdd-continue {change-name}` and it loads the state, identifies the last completed phase, and continues from there. `/sdd-resume` without arguments shows all in-progress pipelines with timing data, cost estimates, and next recommended actions. Session death is a non-event.

### What is `/sdd-ff` (fast-forward)?

One command runs all planning phases in sequence: propose -> spec -> design -> tasks. It is the fastest path from idea to implementation-ready task breakdown. After fast-forward, run `/sdd-apply` to implement. Typical use: `/sdd-ff add-user-authentication` followed by `/sdd-apply add-user-authentication`. The planning phases that would take a human hours complete in minutes.

### How does conflict detection work?

When multiple SDD changes are in progress simultaneously, the system detects overlapping file modifications between proposals. If two changes both target the same service files, a conflict is flagged before apply begins -- preventing merge conflicts and architectural inconsistencies that would be painful to untangle after implementation. Concurrent SDD pipelines are a first-class concept, not an afterthought.

### What are sprint contracts?

The `/sprint` skill provides lightweight agent-managed sprint tracking: plan sprints with goals and stories, track status across sessions, run retrospectives, and course-correct. Sprint state persists in Engram, so agents know what they are working toward across multiple sessions. Sprint task verification validates that acceptance criteria pass before marking stories as complete -- not "I think it's done" but "these commands all returned 0."

### How does SDD governance work?

Compliance scoring evaluates each SDD change against governance criteria. Rollback decision logic determines when to discard failed implementations. Phase timing tracks wall-clock duration and estimated costs per phase with ASCII table rendering. The `sdd_resume.py` module manages the full state machine with phase dependencies, artifact topic keys, and Engram persistence. Every SDD change has a complete audit trail.

---

## 4. Self-Healing & Auto-Repair

### What is the MAPE-K loop?

Monitor-Analyze-Plan-Execute-Knowledge -- an autonomous control loop from systems engineering. Hooks **Monitor** and capture metrics in real time. Pattern detectors **Analyze** events (3+ same error = pattern). The singularity controller **Plans** which pipeline to run. `ClaudeExecutor` **Executes** the pipeline via CLI subprocess. Engram stores the **Knowledge** (outcomes) for future reference. This loop runs continuously when the singularity daemon is active, checking 7 event sources per cycle.

### How does auto-repair work?

Error detected -> `error-learning.sh` captures to JSONL -> `auto-repair-dispatcher.sh` classifies the error type -> remediation registry checked for known fixes -> fix applied in an isolated git worktree (not your working branch) -> tests run in the worktree to verify -> success merges the fix, failure discards it. The circuit breaker prevents runaway repairs: 2 consecutive failures open the breaker, global cap of 10 repairs per hour, 1-hour cooldown before retrying. The remediation registry grows with every successful fix.

### What is the error learning system?

Every test, lint, and build failure across every session is automatically captured by `error-learning.sh` to `metrics/error-learning.jsonl`, deduplicated within 60 seconds by fingerprint. When the same error type hits 3+ times in 24 hours, `error-pattern-detector.sh` injects a warning into the next sub-agent's context: "WARNING: KNOWN ERROR PATTERN: {service} has had {N} {type} errors. Common cause: {X}." Running `/error-analyzer` groups patterns by root cause and proposes skill updates. The system literally learns from its failures.

### What is the circuit breaker?

A state machine with three states: CLOSED (normal operation), OPEN (repairs blocked after 2 consecutive failures for the same error type and service), and HALF-OPEN (1 hour cooldown elapsed, allows a single repair attempt). The global cap of 10 repairs per hour prevents resource exhaustion. Circuit breaker OPEN events always escalate to humans through the Singularity controller -- they are never auto-resolved. The state machine, transitions, and thresholds are all covered by unit tests.

### What does the remediation registry contain?

A growing database of known fixes indexed by error type, service, and language. When auto-repair encounters a new error and successfully fixes it, the fix is recorded in the registry. Next time the same error pattern appears, the fix is applied without the LLM needing to reason about it from scratch. The registry supports CRUD operations, semantic search for similar errors, and language detection heuristics.

### What can never be auto-repaired?

Database migrations, authentication/authorization changes, payment/billing code, `.env` files, docker-compose configuration, git history (rebase, force push), security-sensitive files, and third-party API integration changes. These require human judgment by definition. In production/maintenance phases, auto-repair is further restricted to infrastructure-only actions (container restart, cache clear, disk cleanup). Code changes in production always require human approval.

---

## 5. Memory & Intelligence

### What is Engram?

Persistent memory backed by SQLite (via MCP) that survives across sessions and context compactions. It stores architectural decisions, bug fixes, SDD artifacts, session summaries, skill feedback, and per-agent sidecar memory. Memory is organized by prefixed topic keys: `planning/` for SDD artifacts, `implementation/` for code decisions, `architecture/` for system-wide patterns, `bugfix/` for investigations, `agent/` for per-agent sidecars, `config/` for configuration, `sre/` for operational learnings, `sprint/` for goals. SQLite WAL mode supports concurrent readers across multiple sessions.

### What happens when the context window fills up?

A 4-threshold protocol manages graceful degradation. At 50%: efficiency mode (concise responses, targeted reads). At 70%: mandatory save point -- all decisions, bugs, state saved to Engram immediately via `mem_save`. At 85%: finish and handoff -- stop new work, checkpoint current task, call `mem_session_summary`. At 95%: emergency pre-compaction flush via hook. After compaction, the next session recovers full state by calling `mem_context` and `mem_search`. Context death is a managed event, not a catastrophe.

### How does agent sidecar memory work?

Each agent accumulates learnings, preferences, and patterns across sessions in an Engram-backed sidecar stored under `agent/{agent-name}/sidecar`. When an agent launches, the orchestrator searches Engram for its sidecar and injects relevant content into the prompt. After completing work, the agent saves new discoveries back. A code reviewer remembers past review patterns across sessions. An SRE agent remembers incident resolutions. A spec writer remembers your project's conventions. Agents develop institutional knowledge.

### What is the context optimization protocol?

Three-level progressive loading reduces session startup from ~17,500 tokens to ~3,500 tokens -- an 80% reduction. Level 1: CATALOG.md (1-line skill summaries, ~2K tokens) loaded at session start. Level 2: full SKILL.md loaded on demand when invoked (~1-3K tokens each). Level 3: reference files loaded only when detailed examples are needed. Maximum 5 skills loaded simultaneously with automatic unloading after 5 minutes of inactivity. The dual-search protocol checks complete files, then sharded versions, then Engram in sequence.

### How does session resume work?

At session start, `session-resume.sh` checks `active-tasks.json` for tasks that were in-progress when the last session ended. Tasks with verified outputs (checked via `checkCommand`) are auto-marked complete. Tasks with missing outputs generate a warning recommending re-launch. For SDD pipelines, `/sdd-continue` loads state from Engram and picks up at the next incomplete phase with timing data and cost estimates. For long-running phases, step files break work into discrete resumable checkpoints.

### What happens when a session crashes mid-work?

The session state persistence layer (`lib/session_state.py`) writes a JSON snapshot to `.cognitive-os/session-state.json` containing all running agents, pending tasks, completed tasks, and a checkpoint note. The `session-state-save.sh` Stop hook writes a final checkpoint before shutdown, and individual operations (record_agent, mark_agent_complete, add_pending_task) checkpoint after every mutation. Writes are atomic (temp file plus rename) so a crash mid-write cannot corrupt the file. When a new session starts, `load_state()` reads the previous snapshot and the orchestrator can see which agents were still running, which tasks were pending, and what the last checkpoint note said. Combined with Engram memory and `session-resume.sh`, the new session has full context to continue where the old one stopped.

### Can multiple Claude Code sessions share memory safely?

Yes. Engram uses SQLite WAL mode (concurrent readers, single writer). Sessions share skills, rules, and Engram while isolating tasks and metrics in per-session directories (`sessions/{id}/`). Advisory file locking via `concurrent-write-guard.sh` warns when two sessions edit the same file -- it does not block, but alerts you. Up to 10 concurrent sessions supported. Session init creates unique IDs; session cleanup merges per-session metrics into global state.

### How is memory organized?

Nine prefixed topic key namespaces prevent collisions: `planning/` (SDD artifacts), `implementation/` (code decisions), `architecture/` (system-wide patterns), `bugfix/` (investigations), `agent/` (per-agent sidecars), `config/` (configuration), `sre/` (operational learnings), `sprint/` (goals and retros), `docs/` (documentation decisions). Legacy flat `sdd/` keys from older versions are automatically migrated to the `planning/` prefix when read. The search strategy tries the prefixed key first, falls back to legacy, then falls back to keyword search.

---

## 6. Quality Gates

### What is the trust score?

Every agent completion includes a Trust Report scored 0-100 from four components: verification evidence (40% -- did the agent run commands and show output?), acceptance criteria (30% -- were measurable criteria defined and met?), self-awareness (20% -- did the agent admit uncertainties?), and proportionality (10% -- is the solution appropriate?). The critical rule: every report must list at least one uncertainty. "100% confident" is a red flag that triggers alerts. The `trust-score-validator.sh` hook enforces this on every agent completion.

### What is the adversarial review protocol?

Every review MUST produce at least one finding. "Looks good" and "no issues found" are prohibited responses -- the orchestrator halts and re-launches the reviewer. Findings are classified into four severity tiers: BLOCKER (prevents shipping), CONCERN (likely to cause problems), SUGGESTION (improvement opportunity), QUESTION (needs clarification). Every finding requires location, description, reasoning, and recommendation. If a reviewer returns zero findings after 2 retries, it escalates to a human. Rubber-stamp reviews are structurally impossible.

### What is Definition of Done?

Five complexity levels each have escalating completion criteria. **Trivial** (< 20 lines): compilation + lint. **Small** (1-3 files): + unit tests pass. **Medium** (multi-file feature): + new tests written + coverage maintained + docs updated. **Large** (multi-service): + readiness check + 80% coverage + integration tests + adversarial review. **Critical** (security, payments, migrations): + security review + idempotency verification + audit trail + tested rollback procedures. Agents must classify complexity before starting and cannot mark done without passing ALL criteria. The `dod-gate.sh` hook enforces this automatically.

### What are acceptance criteria?

Every agent prompt must include numbered, measurable, verifiable checks: `grep -rl 'old-name' src/ | wc -l = 0`, `go test ./... exits 0`, `coverage >= 80%`. If the orchestrator does not provide criteria, the agent must define them before starting work. The `auto-verify.sh` hook extracts and runs these commands automatically on completion. The `completeness-check.sh` hook fires before agent launch and warns when prompts contain red flags like "all files" without listing them or "follow patterns" without specifying which.

### How does contract drift detection work?

The `/contract-drift` skill scans source code for HTTP call patterns (fetch, axios, http.Get, requests.post) across Go, TypeScript, and Python files, extracts URLs and methods, normalizes them, compares against OpenAPI/Swagger specifications, and identifies undocumented API calls, unused contract entries, and method mismatches. It catches the gap between what the code actually does and what the contract says -- before production discovers the discrepancy.

### What is the harness audit?

The `/harness-audit` skill performs periodic self-assessment of Cognitive OS itself. It evaluates hooks, rules, and skills for continued relevance by cross-referencing activity data from metrics files. Components that are never triggered, always pass trivially, or have been superseded are flagged as retirement candidates. It produces recommendations for human review -- it never auto-removes anything. The OS monitors its own obsolescence.

### What are the project phases and how do they change behavior?

Four lifecycle phases alter all agent behavior globally. **Reconstruction**: rewrite over patch, break backwards compatibility freely, auto-remediate architecture violations as blockers. **Stabilization**: standards enforced strictly, remaining issues cleaned up. **Production**: feature flags required, no breaking changes, human approval for risky operations, auto-repair restricted to infrastructure-only. **Maintenance**: bug fixes and security patches only, every change requires human approval. Set in `cognitive-os.yaml` under `project.phase`. One config value, 55 rules respond.

### What is the readiness check?

Before any `/sdd-apply` phase, the `/readiness-check` skill validates prerequisites: specs complete, design reviewed, tasks broken down, dependencies identified, mocks configured, tests planned. Three verdicts: PASS (proceed), CONCERNS (proceed with caution), FAIL (must fix first). On FAIL, the orchestrator blocks apply and reports blockers. The `/resolve-blockers` skill can automatically resolve common blockers identified by readiness-check.

---

## 7. Self-Improvement

### How does the OS improve itself?

Closed loop: `error-learning.sh` captures every failure -> `error-pattern-detector.sh` identifies recurring patterns (3+ same error in 24h) -> `/error-analyzer` groups by root cause -> `/self-improve` proposes concrete updates to rules, skills, and templates. Safe improvements (template updates, acceptance criteria, model routing) auto-apply. Risky improvements (rule rewrites, hook modifications) require human approval. After applying, `/cognitive-os-test` validates nothing broke -- failures trigger automatic `git revert`. Max 5 improvements per run, 24-hour cooldown, improvement blocklist for failed attempts.

### What is dogfooding?

Cognitive OS uses itself to build itself. The `luum-agent-os` repo is self-hosted: `.claude/rules/` symlinks to `rules/`, all 57 hooks run on this project, and every substantial change goes through the SDD pipeline. The `self-install.sh` hook runs at every session start, syncing all 55 rules and 57 hooks automatically. The first dogfooded change (`quinotospec-patterns`) found 3 real bugs in the pipeline -- sub-agent tool access, skill path resolution, and JSON corruption from shell arithmetic -- all fixed during the verify-apply retry loop.

### What is skill adaptation?

Before executing any skill, the system searches Engram for feedback from prior failures: `skill-feedback/{skill-name}`. If feedback exists, execution adapts accordingly. After a skill fails, feedback is immediately saved. After 3+ failures of the same skill, the system announces the pattern and invokes `/skill-creator` with full failure context to rewrite the skill. Skills are living documents that improve over time based on real usage data, not static instructions.

### How does auto-skill generation work?

When a sub-agent completes a complex task successfully (10+ tool uses or 8000+ character response), the `auto-skill-generator.sh` hook automatically extracts the procedure into a reusable `SKILL.md` file saved to `skills/auto-generated/`. This is the Act-Learn-Reuse cycle: agents act on tasks, the system learns by extracting procedures, future similar tasks reuse the generated skill. Each cycle makes the agent more capable. Auto-generated skills are drafts that improve via the skill adaptation protocol.

### How does metrics calibration work?

Static thresholds decay -- what was challenging last month may be trivially easy today. The `/metrics-calibrator` analyzes 30-day KPI distributions weekly. Thresholds below the 10th percentile (too easy, always passing) are raised to the 25th percentile. Thresholds above the 90th percentile (too hard, always failing) are lowered to the 75th percentile. It proposes derived metrics: cost_per_fix, repair_roi, skill_efficiency, error_velocity, and a composite health_score. The system tunes itself.

### What is the capability snapshot?

Before any cleanup or refactor of Cognitive OS itself, you must run `/capability-snapshot save`. After changes, `/capability-snapshot diff` compares current state against the snapshot. Every removed capability requires explicit justification: replaced, deprecated, or duplicate. The `pre-cleanup-snapshot.sh` hook auto-detects cleanup intent on agent launches and advises taking a snapshot. You cannot accidentally lose a capability -- the system makes you prove the removal was intentional.

### What are agent KPIs?

Calculated at session end and on demand via `/agent-kpis`. Six OKR categories: quality (> 90% composite), efficiency (-20% month-over-month), self-improvement (measurable weekly), developer velocity (> 3x vs manual), security (0 violations), and resource efficiency (> 80% composite). KPIs include trust score accuracy, self-awareness rate, first-attempt success rate, error recurrence, token efficiency, and architecture compliance. When thresholds breach, specific remediation actions trigger automatically: `/trust-audit` for low trust, `/error-analyzer` for recurring failures, `/model-optimizer` for token waste.

---

## 8. Testing Infrastructure

### How many tests exist?

1714 tests across 64 test files in 4 categories. Unit tests (698 tests, 22 files): pure functions, state machines, parsers. Behavior tests (926 tests, 28 files): hook contracts, skill structures, protocol logic. Integration tests (62 tests, 8 files): real Docker services via testcontainers. System tests (25 tests, 5 files): configuration and runtime consistency. The behavior layer carries the majority because it validates contracts without Docker overhead, keeping the feedback loop fast.

### What is cos-test?

A Go binary built with Cobra (CLI), Bubbletea (TUI), and Lipgloss (styling). It wraps pytest with `--json-report` and renders results in a terminal dashboard with color-coded pass/fail indicators, timing data, and filter controls. Watch mode provides continuous test monitoring during development. Compiles to a single binary with no runtime dependencies. Run `./cos-test dashboard` for the full TUI or `./cos-test watch` for continuous mode.

### How do testcontainers work?


### What evaluation frameworks are integrated?

Three LLM evaluation frameworks. **DeepEval**: LLM unit testing with 60+ metrics, trajectory evaluation, and red teaming -- validates agent reasoning quality. **RAGAS**: memory quality testing, retrieval evaluation, and synthetic test generation -- validates that Engram retrieval returns relevant results. **Promptfoo**: prompt regression testing and red teaming in CI/CD pipelines -- validates that prompt changes do not degrade output quality. Integration tests verify SDK imports and API endpoints against running services.

### What do behavior tests cover specifically?

29 hooks (dod-gate, secret-detector, auto-verify, auto-skill-generator, session-resume, etc.), 44 skills (structural validation of frontmatter and required sections), SDD phase transitions across the full dependency graph, generator-evaluator loop verdict handling, sprint contracts and task verification, harness audit classification, self-install auto-sync (50 tests alone), phase detection and constitutional gate enforcement, self-improvement KPI triggers, file locking correctness, private mode, resource budget enforcement, session isolation, contract drift detection (54 tests), proposal conflict detection, batch application, staleness tracking, sprint planning, and SDD governance compliance scoring.

### What does the Singularity controller test suite cover?

92 behavior tests for the Singularity controller alone: event detection across all 7 sources, deduplication with MD5 hashing, cooldown enforcement, phase-gated event filtering, priority queue ordering, budget limit enforcement, concurrency caps, pipeline routing, success rate tracking, notification dispatch, circuit breaker escalation, daemon lifecycle with SIGTERM handling, and dry-run mode. The autonomous brain is the most thoroughly tested component in the system.

### How do I run tests?

`uv run pytest tests/ -v` for the full suite. `uv run pytest tests/unit/ tests/behavior/ -v` for fast feedback without Docker. `uv run pytest tests/ -v -m docker` for integration tests. `/cognitive-os-test` from within Claude Code runs everything and reports results. `/cognitive-os-compat-test` provides a quick 8-check smoke test verifying your model handles Cognitive OS correctly. Bash infrastructure tests run separately: `bash tests/infra/test-hooks.sh`.

---

## 9. Infrastructure

### What Docker services are included?


### What is the ClaudeExecutor?

The Python module (`lib/claude_executor.py`) that makes programmatic Claude Code invocation possible. It runs `claude -p <prompt> --output-format stream-json --verbose` as a subprocess, parses the JSONL stream in real time to extract tool calls, assistant text, token usage, and the final result. It provides structured `ClaudeResult` objects with cost estimation, retry logic with exponential backoff, timeout management with process group killing, and a filtered environment allowlist for security. Every autonomous pipeline runs through this executor.

### What is the notification system?

Three providers (Telegram, Slack, generic webhook) configured via environment variables. Uses only Python stdlib (urllib) -- zero external dependencies. Set `NOTIFY_PROVIDER=telegram`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` and notifications fire automatically from the singularity controller, issue pipeline, and notification hook. Pipeline completions, failures, circuit breaker openings, and budget alerts all produce notifications. You know what the OS is doing even when you are not watching.

### How do I monitor agents in real time?

The Agent Communication Bus (`lib/agent_bus.py`) provides bidirectional real-time monitoring via Valkey pub/sub. Set `AGENT_BUS_ENABLED=true` and pass `agent_id` to `ClaudeExecutor`. Agents automatically publish heartbeats every 5 seconds and progress events on each tool use. The orchestrator subscribes to all channels to detect active agents, dead agents (no heartbeat for 15s), and pending clarification questions. Run `python lib/agent_dashboard.py` for a terminal dashboard showing live agent status. When Valkey is unavailable, everything falls back to file-based signaling under `.cognitive-os/agent-bus/` with no crashes or data loss.

### What is the GPU sandbox?

The `/gpu-sandbox` skill executes Python code in a Jupyter runtime for compute-heavy tasks -- ML model inference, data analysis, financial calculations, scientific computing. The Jupyter container runs as part of the Docker stack with persistent data volumes. Agents can offload heavy computation without consuming Claude Code's context window or risking timeout on long-running calculations.



### What is Opik?

An LLM observability platform for tracing, evaluation, and experiment tracking. The `/opik-setup` skill configures it. It provides trace-level visibility into every agent execution -- what tools were called, what tokens were consumed, where time was spent. Integration tests validate the Opik SDK against the running backend and frontend services. Run experiments, compare results, and identify performance bottlenecks.

### How does model routing and cost control work?

The routing table in `rules/model-routing.md` assigns each skill to the optimal model: Opus ($15/$75 per 1M tokens) for reasoning tasks (propose, design, debug), Sonnet ($3/$15) for implementation (spec, tasks, apply, verify), Haiku ($0.25/$1.25) for documentation (archive). The resource governor enforces daily and monthly budget limits. At 80% budget: force Sonnet for everything. At 95%: force Haiku. At 100%: block all agent launches. The `/model-optimizer` skill analyzes actual cost data and updates the routing table.

### What web crawling capabilities does Cognitive OS have?

The `lib/web_crawler.py` module wraps Crawl4AI (Apache 2.0) to provide LLM-ready web content extraction. Three functions cover the common cases: `fetch_markdown` fetches a single URL and returns clean markdown with boilerplate removed, `fetch_structured` extracts structured data using CSS/XPath schemas (prices, listings, tables), and `crawl_site` deep-crawls up to 50 pages on the same domain. When Crawl4AI is not installed, single-page fetch falls back to `urllib` with basic HTML stripping -- no JS rendering but functional for simple pages. Structured extraction and site crawling require Crawl4AI. A synchronous wrapper `fetch_markdown_sync` is available for hooks and scripts where `async/await` is not practical.

---

## 10. Getting Started

### How do I install Cognitive OS?

One command: `curl -fsSL https://raw.githubusercontent.com/luum-home/luum-cognitive-os/main/install.sh | bash`. Then open Claude Code and run `/cognitive-os-init`. The init skill auto-detects your stack, generates project-specific rules and settings, and creates `cognitive-os.yaml`. Optional infrastructure: `docker compose -f docker-compose.cognitive-os.yml up -d`. The entire installation is non-destructive and fully reversible.

### What happens on first session?

Six hooks fire automatically: `self-install.sh` syncs rules and hooks (in dogfooding repos), `session-init.sh` creates a unique session ID, `session-resume.sh` checks for incomplete tasks, `stack-detector.sh` identifies project languages and frameworks, `inject-phase-context.sh` loads phase-specific behavior rules, and `engram-auto-import.sh` loads persistent memory. A status line confirms health: "Self-hosting: OK (55 rules, 57 hooks synced)." Your session starts with full context from all previous sessions.

### How do I run my first pipeline?

Start with `/sdd-new add-user-authentication`. This runs explore (analyzes your codebase) and propose (generates a formal proposal with scope, risks, and approach). Then `/sdd-continue add-user-authentication` advances through each subsequent phase. Or fast-track everything: `/sdd-ff add-user-authentication` runs all planning phases at once, then `/sdd-apply add-user-authentication` implements. If anything fails mid-pipeline, `/sdd-continue` picks up exactly where you left off.

### What prerequisites do I need?

Claude Code (latest), Python 3.9+, Git 2.30+, and `gh` CLI for GitHub integration. Go 1.21+ only if you want the `cos-test` TUI binary. Docker 24+ for integration tests and optional infrastructure services. `uv` recommended for Python package management. Optional: `devbox` for reproducible environments. The core system (hooks, rules, skills, Engram protocol, local JSONL metrics, and budget gates) works without Docker; optional infrastructure services add dashboards, external observability backends, guardrails, or compute isolation when a project explicitly needs them.

### How do I verify everything works?

Three verification levels. `/cognitive-os-status`: full health report showing hooks registered, rules loaded, skills available, squads configured, and metrics state. `/cognitive-os-test`: runs the full test suite across all 4 categories. `/cognitive-os-compat-test`: quick 8-check smoke test verifying your model handles Cognitive OS correctly. All three provide clear pass/fail output. If the test suite passes, the OS is healthy.

### How do I enable autonomous mode?

Three options. **One-shot**: `python lib/singularity.py run` scans all event sources once and executes pending pipelines. **Cron**: `*/5 * * * * python lib/singularity.py run` checks every 5 minutes. **Daemon**: `python lib/singularity.py daemon --interval 300 --budget 10.0` runs continuously with built-in budget enforcement. Start with `dry-run` to preview what would execute: `python lib/singularity.py dry-run`. Check status anytime: `python lib/singularity.py status`. The controller is inactive by default -- you choose when to hand over the keys.
