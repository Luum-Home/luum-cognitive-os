# COS Self-Usage Audit

**Date**: 2026-03-29
**Auditor**: Orchestrator self-assessment
**Scope**: All skills, hooks, libs, and rules in luum-agent-os

## Executive Summary

- **Total skills**: 106 (97 universal + ~9 project-generated templates)
- **Total hooks**: ~88 (44 in hooks/ + 44 in packages/**/hooks/)
- **Total rules**: 94 (per RULES-COMPACT.md)
- **Total libs**: 25 Python modules in lib/
- **Hooks registered in settings.json**: 28 of ~88 (**32%**)
- **Skills the orchestrator proactively triggers**: ~5 of 106 (**5%**)
- **Libs the orchestrator calls programmatically**: 0 of 25 (**0%**)
- **Rules the orchestrator consistently follows**: ~15 of 94 (**16%**)
- **Overall self-usage rate**: approximately **13%**
- **Gap**: ~87% of built capabilities are never applied by the orchestrator

---

## 1. Hooks Audit

### Registered (28 hooks in settings.json)

| Hook | Event | Matcher |
|------|-------|---------|
| self-install.sh | SessionStart | -- |
| session-init.sh | SessionStart | -- |
| crash-recovery.sh | SessionStart | -- |
| paperclip-squad-sync.sh | SessionStart | async |
| paperclip-task-sync.sh | SessionStart | async |
| rate-limiter.sh | PreToolUse | Bash\|Agent\|Edit\|Write |
| large-file-advisor.sh | PreToolUse | Read |
| clarification-gate.sh | PreToolUse | Agent |
| blast-radius.sh | PreToolUse | Agent |
| error-pattern-detector.sh | PreToolUse | Agent |
| error-pipeline.sh | PostToolUse | Bash |
| result-truncator.sh | PostToolUse | Bash |
| secret-detector.sh | PostToolUse | Edit\|Write |
| content-policy.sh | PostToolUse | Edit\|Write |
| doc-sync-detector.sh | PostToolUse | Edit\|Write |
| package-sync.sh | PostToolUse | Edit\|Write (async) |
| auto-checkpoint.sh | PostToolUse | Bash\|Edit\|Write |
| claim-validator.sh | PostToolUse | Agent |
| completion-gate.sh | PostToolUse | Agent |
| clarification-interceptor.sh | PostToolUse | Agent |
| agent-checkpoint.sh | PostToolUse | Agent |
| paperclip-agent-status.sh | PostToolUse | Agent (async) |
| paperclip-sdd-sync.sh | PostToolUse | Agent (async) |
| session-learning.sh | Stop | -- |
| session-cleanup.sh | Stop | -- |
| teammate-idle.sh | TeammateIdle | -- |
| task-created.sh | TaskCreated | -- |
| task-completed.sh | TaskCompleted | -- |

### NOT Registered (Critical Gaps)

These hooks exist but are NOT in settings.json. Sorted by criticality.

#### CRITICAL -- Should Be Registered

| Hook | Event | Why It Matters | Impact of Absence |
|------|-------|----------------|-------------------|
| `hooks/infra-health.sh` | SessionStart | Detects missing Docker services at session start | Orchestrator never knows if infrastructure is degraded |
| `hooks/session-resume.sh` | SessionStart | Auto-checks active-tasks.json for incomplete work | Previous session work is never auto-resumed |
| `hooks/mcp-scan.sh` | SessionStart | Scans MCP server configs for tool poisoning | MCP supply chain vulnerabilities go undetected |
| `hooks/pre-compaction-flush.sh` | PostToolUse | Saves state to Engram before context compaction | State is lost on compaction -- the ONE safety net that should never be missing |
| `hooks/scope-proportionality.sh` (pkg) | PostToolUse/Agent | Detects disproportionate changes (fix deleting files) | Agents can silently over-scope their changes |
| `hooks/trust-score-validator.sh` (pkg) | PostToolUse/Agent | Extracts and logs trust scores from agent output | Trust scores are never tracked -- the entire trust system is dead |
| `hooks/confidence-gate.sh` (pkg) | PostToolUse/Agent | Blocks low-confidence results in production | Low-quality agent results propagate unchecked |
| `hooks/assumption-tracker.sh` (pkg) | PostToolUse/Agent | Detects when agents make excessive assumptions | Agent guesswork goes unmonitored |
| `hooks/auto-rollback-trigger.sh` (pkg) | PostToolUse/Agent | Detects verify-apply exhaustion and triggers rollback | Failed SDD pipelines leave broken code without rollback |
| `hooks/agent-prelaunch.sh` (pkg) | PreToolUse/Agent | Registers tasks in active-tasks.json before launch | Task tracking (fault tolerance Tier 4) is broken |
| `hooks/tool-loop-detector.sh` (pkg) | PostToolUse | Detects infinite tool call loops | Agents can spin indefinitely without detection |

#### HIGH -- Should Be Registered

| Hook | Event | Why It Matters |
|------|-------|----------------|
| `hooks/completeness-check.sh` | PreToolUse/Agent | Warns when agent prompts are vague/incomplete |
| `hooks/scope-creep-detector.sh` (pkg) | PostToolUse/Edit\|Write | Detects edits outside approved task scope |
| `hooks/prompt-quality.sh` (pkg) | PreToolUse/Agent | Scores prompt quality on 5 dimensions |
| `hooks/consequence-evaluator.sh` (pkg) | PostToolUse/Agent | Evaluates agent performance for promotion/degradation |
| `hooks/auto-skill-generator.sh` (pkg) | PostToolUse/Agent | Auto-generates skills from complex successful tasks |
| `hooks/skill-tracker.sh` (pkg) | PostToolUse | Tracks skill execution metrics |
| `hooks/epic-task-detector.sh` (pkg) | PreToolUse/Agent | Detects large-scope tasks that need sampling |
| `hooks/architecture-compliance.sh` (pkg) | PostToolUse/Agent | Detects architecture violations in agent output |
| `hooks/task-recorder.sh` (pkg) | Stop | Records completed task costs for future prediction |
| `hooks/kpi-trigger.sh` (pkg) | Stop | Calculates KPI snapshot, flags self-improvement |

#### MEDIUM -- Nice to Have

| Hook | Event | Why It Matters |
|------|-------|----------------|
| `hooks/dry-run-preview.sh` (pkg) | PreToolUse/Agent | DRY_RUN mode support |
| `hooks/adaptive-bypass.sh` (pkg) | PreToolUse/Agent | Auto-classifies task complexity |
| `hooks/contextual-rule-loader.sh` (pkg) | PreToolUse | Loads rules based on file type context |
| `hooks/observability-trace.sh` (pkg) | PostToolUse | Sends traces to Langfuse |
| `hooks/idle-service-cleanup.sh` (pkg) | Stop | Cleans up idle Docker services |
| `hooks/metrics-rotation.sh` (pkg) | SessionStart | Rotates old metrics files |
| `hooks/agnix-lint.sh` (pkg) | PostToolUse/Edit\|Write | Lints agent config files |
| `hooks/semgrep-scan.sh` | PostToolUse/Agent | SAST security scanning |
| `hooks/aguara-scan.sh` | PreToolUse/Agent | AI agent security scanning |
| `hooks/conversation-capture.sh` | PostToolUse | Captures conversation context |
| `hooks/user-prompt-capture.sh` | PreToolUse | Captures user prompts to Engram |
| `hooks/singularity-check.sh` | SessionStart | Checks singularity controller status |
| `hooks/cognitive-os-health.sh` | SessionStart | Overall COS health check |

**Registration gap**: 60 hooks are NOT registered. Many of these are the enforcement mechanisms for rules that claim to be "always active" -- meaning those rules are effectively dead.

---

## 2. Skills Audit

### Skills the Orchestrator Should Auto-Trigger But Does Not

| Skill | Should Trigger When | Currently Happens |
|-------|--------------------|--------------------|
| `/resume-tasks` | Session start (incomplete tasks exist) | Never triggered -- session-resume.sh not registered |
| `/agent-kpis` | Session end (enough data in metrics) | Never triggered |
| `/dod-check` | After any agent claims "done" | Never triggered -- orchestrator skips DoD verification |
| `/exhaustive-prompt` | Before medium+ agent launches | Never triggered -- prompts are ad-hoc |
| `/readiness-check` | Before sdd-apply on large+ tasks | Never triggered |
| `/scout` | Before implementation on medium+ tasks | Never triggered |
| `/impact-analysis` | Before multi-file changes | Never triggered |
| `/self-review` | After non-SDD implementation work | Never triggered |
| `/resource-governor` | Session end or budget alert | Never triggered |
| `/cost-predict` | Before medium+ tasks | Never triggered |
| `/estimation-report` | After medium+ task completion | Never triggered |
| `/doc-sync` | Session end (stale docs exist) | Never triggered |
| `/error-analyzer` | 3+ same error type in 24h | Never triggered |
| `/cognitive-os-status` | Session start (health check) | Never triggered |
| `/self-improve` | Weekly or KPI breach | Never triggered |
| `/compose-prompt` | Before any sub-agent launch | Never triggered -- prompts are inline |
| `/confidence-check` | Before implementation on large+ tasks | Never triggered |
| `/sandbox-sample` | Before changes touching 100+ files | Never triggered |
| `/planning-poker` | Before large/critical task estimation | Never triggered |
| `/trust-audit` | Weekly or trust score < 75 | Never triggered |
| `/repair-status` | After auto-repair circuit breaker events | Never triggered |
| `/secret-audit` | Before production deployments | Never triggered |
| `/security-audit` | Weekly schedule | Never triggered |
| `/conversation-memory` | When user references past sessions | Never triggered |
| `/coverage-report` | After test runs | Never triggered |

### Skills That Work When Manually Invoked (User Types the Command)

| Skill | Works When Invoked | Auto-Trigger Missing |
|-------|-------------------|---------------------|
| `/sdd-new`, `/sdd-ff`, `/sdd-continue` | Yes | -- (meta-commands, orchestrator handles) |
| `/sdd-explore`, `/sdd-apply`, `/sdd-verify` | Yes | -- (SDD phases, launched by orchestrator) |
| `/plan-feature`, `/plan-bug` | Yes | Should auto-suggest for medium+ tasks |
| `/recommend-library` | Yes | Should auto-trigger on new dependency detection |
| `/deep-research` | Yes | Should auto-trigger on unknown topics |
| `/repo-scout` | Yes | Should auto-trigger on GitHub URLs |
| `/run-tests` | Yes | Should auto-trigger after code changes |

### Skills Never Used (Likely Dead Code)

| Skill | Why It Appears Dead |
|-------|---------------------|
| `/arena` | Benchmarking tool -- no automated trigger |
| `/simulate` | Simulation arena -- no automated trigger |
| `/opik-setup`, `/cognee-setup`, `/deepeval-setup`, `/ragas-setup`, `/strands-setup`, `/promptfoo-setup` | Integration setup skills -- one-time use |
| `/automaker-bridge` | Integration -- one-time use |
| `/nemo-guardrails` | Configuration -- one-time use |
| `/paperclip-dashboard` | Dashboard -- on-demand only |
| `/harness-audit` | Maintenance -- on-demand only |
| `/webhook-trigger` | Infrastructure -- runs independently |
| `/gpu-sandbox`, `/jupyter-exec` | Compute sandbox -- on-demand only |
| `/persistent-agent` | Agent creation -- on-demand only |
| `/web-crawler` | Web fetching -- on-demand only |
| `/audit-website` | Website audit -- on-demand only |
| `/devbox-checkpoint` | Environment snapshots -- on-demand only |

---

## 3. Libs Audit

### Python Libraries the Orchestrator Should Call But Does Not

| Lib | Should Be Called When | Currently Called? |
|-----|----------------------|------------------|
| `lib/skill_router.py` | Every user message (auto-select skill) | NO -- rule says "on every user message, call router.best_match()" but orchestrator never does |
| `lib/prompt_classifier.py` | Every user message (capture actionable prompts) | NO -- rule says "orchestrator MUST call classify_prompt()" but never does |
| `lib/cost_dashboard.py` | Session end (report costs) | NO -- rule says "session cost MUST be reported" but never is |
| `lib/model_router.py` | Before every sub-agent launch (select model) | NO -- orchestrator uses default model always |
| `lib/workload_scheduler.py` | Before launching 3+ agents in parallel | NO -- no scheduling applied |
| `lib/escalation_detector.py` | During agent execution (detect stuck agents) | NO -- sub-agents have instructions but detector is not wired |
| `lib/trust_report_parser.py` | After every agent completion (extract trust score) | NO -- trust scores are not parsed or tracked |
| `lib/cognitive_load_monitor.py` | At 50%+ context usage (track quality degradation) | NO -- no cognitive load monitoring active |
| `lib/consequence_engine.py` | After every agent completion (evaluate consequence) | NO -- consequence system is fully inactive |
| `lib/checkpoint_manager.py` | Every 5 minutes (auto-checkpoint) | PARTIAL -- hook exists and is registered, but Python lib unused |
| `lib/rate_limiter.py` | Before every tool call (check limits) | PARTIAL -- bash hook is registered, Python lib unused |
| `lib/smart_reader.py` | Before reading large files | NO -- orchestrator uses raw Read tool |
| `lib/smart_infra.py` | Before skills needing Docker services | NO -- no smart start/lazy loading |
| `lib/retry_scheduler.py` | When rate-limited (schedule deferred retry) | NO -- orchestrator would sleep instead |
| `lib/skill_archive.py` | After skill execution (snapshot for evolution) | NO -- skill archive completely inactive |
| `lib/bifrost_client.py` | For gateway communication | NO -- gateway not typically active |
| `lib/gateway_selector.py` | For multi-provider model routing | NO -- single provider used |
| `lib/code_reviewer.py` | For automated code review | NO -- not called by orchestrator |
| `lib/repo_analyzer.py` | For repository analysis tasks | NO -- not called by orchestrator |
| `lib/singularity.py` | For autonomous monitoring loop | NO -- singularity is opt-in |
| `lib/test_framework_detector.py` | Before running tests (detect framework) | NO -- not called |
| `lib/dynamic_tool_creator.py` | For creating tools at runtime | NO -- not called |
| `lib/reverse_engineer.py` | For dependency analysis | NO -- not called |
| `lib/claude_executor.py` | When ORCHESTRATOR_MODE=executor | NO -- executor mode not active |

**Lib usage rate: 0%** (no Python lib is called programmatically by the orchestrator)

Note: The orchestrator (Claude) cannot directly import and execute Python. However, the rules expect the orchestrator to call these via Bash (`python3 -c "from lib.X import Y; ..."`) or delegate to sub-agents that use them. Neither happens.

---

## 4. Rules Audit

### Rules the Orchestrator Consistently Follows

| Rule | Evidence of Compliance |
|------|----------------------|
| Engram saves (mem_save, mem_session_summary) | Orchestrator does save to Engram when explicitly reminded |
| SDD pipeline phases | Orchestrator correctly orchestrates SDD when user invokes /sdd-* |
| Delegation to sub-agents | Orchestrator delegates via Agent tool |
| Agent preamble | Templates are referenced in sub-agent prompts |
| Content policy | Hook is registered and enforces automatically |
| Secret detection | Hook is registered and enforces automatically |
| Rate limiting | Hook is registered and enforces automatically |

### Rules Claimed "Always Active" But Actually Ignored

| Rule | Claims | Actually Done? | Why Ignored |
|------|--------|---------------|-------------|
| `user-prompt-capture` | "Orchestrator MUST call mem_save_prompt for every actionable user message" | NO | Hook not registered, orchestrator never calls classify_prompt() |
| `token-economy` | "Session cost MUST be reported in session summary" | NO | cost_dashboard.py never called, no cost tracking |
| `acceptance-criteria` | "Before launching ANY agent, orchestrator MUST define acceptance criteria" | RARELY | Orchestrator sometimes includes criteria, usually skips |
| `trust-score` | "Every agent completion MUST include a Trust Report" | PARTIALLY | Preamble instructs agents to include it, but trust-score-validator.sh is not registered so scores are never tracked |
| `closed-loop-prompts` | "Every agent prompt MUST include success criteria + verification command + fallback action" | RARELY | Orchestrator sends ad-hoc prompts without structured criteria |
| `model-routing` | "Orchestrator checks this table before delegating" | NO | All sub-agents use default model |
| `definition-of-done` | "Agents MUST classify complexity BEFORE starting" | NO | No complexity classification happens |
| `adaptive-bypass` | "Orchestrator MUST classify CURRENT task's complexity" | NO | No classification step before tasks |
| `scout-pattern` | "Require structured reconnaissance before implementation on medium+ tasks" | NO | No scouting happens |
| `estimation-calibration` | "Pre-task estimate required for medium+ tasks" | NO | No estimation happens |
| `cost-prediction` | "Run cost prediction before medium+ tasks" | NO | No cost prediction happens |
| `blast-radius` | "Estimates impact scope before execution" | PARTIAL | Hook is registered but orchestrator ignores its output |
| `context-management` | "At 70% MUST save to Engram immediately" | NO | Context thresholds not monitored |
| `cognitive-load` | "Start tracking quality metrics at 50%" | NO | No monitoring active |
| `agent-quality` | "Never launch an agent without acceptance criteria" | NO | Agents launched without criteria routinely |
| `workload-scheduling` | "Before launching 3+ agents, use WorkloadScheduler" | NO | No scheduling used |
| `resource-governance` | "Before launching ANY sub-agent, check daily/monthly spend" | NO | No budget checking happens |
| `prompt-composition` | "Compose sub-agent prompts from reusable templates" | RARELY | Templates exist but are rarely assembled |
| `agent-security` | "Orchestrator MUST grant scoped permissions before launching sub-agents" | NO | No permission system active |
| `agent-identity` | "Every agent must be identifiable with WHO/WHAT/WHEN/WHERE/WHY" | NO | No identity tracking |
| `agent-kpis` | "Calculate KPIs at end of every session" | NO | Never calculated |
| `agent-sidecars` | "Search engram for agent's sidecar on launch" | NO | Never injected |
| `error-learning` | "Auto-captured to JSONL" | PARTIAL | Hook registered (error-pipeline.sh), but pattern detection and feedback loop are broken |
| `consequence-system` | "Every agent completion evaluated for consequences" | NO | consequence-evaluator.sh not registered |
| `impact-analysis` | "MUST run before sdd-apply on large/critical" | NO | Never invoked automatically |
| `plan-first` | "Plans required for medium+ tasks in production" | NO | Plans rarely created except for explicit /plan-* invocations |
| `responsiveness` | "Never appear stuck, report what you're running" | PARTIAL | Orchestrator sometimes reports, often doesn't |
| `broken-window-policy` | "If you find something broken, you fix it" | NO | Pre-existing issues are routinely noted and ignored |
| `phase-aware-agents` | "ALL agents MUST follow phase rules" | PARTIAL | Preamble includes phase, but enforcement hooks are not registered |

### Rules That Are Enforced (via registered hooks)

| Rule | Enforced By |
|------|------------|
| Rate limiting | `hooks/rate-limiter.sh` (registered) |
| Content policy | `hooks/content-policy.sh` (registered) |
| Secret detection | `hooks/secret-detector.sh` (registered) |
| Large file advisory | `hooks/large-file-advisor.sh` (registered) |
| Result truncation | `hooks/result-truncator.sh` (registered) |
| Auto-checkpoint | `hooks/auto-checkpoint.sh` (registered) |
| Crash recovery | `hooks/crash-recovery.sh` (registered) |
| Error capture | `hooks/error-pipeline.sh` (registered) |
| Clarification gate | `hooks/clarification-gate.sh` (registered) |
| Blast radius | `hooks/blast-radius.sh` (registered) |
| Error pattern detection | `hooks/error-pattern-detector.sh` (registered) |
| Claim validation | `hooks/claim-validator.sh` (registered) |
| Completion gate | `hooks/completion-gate.sh` (registered) |
| Clarification interceptor | `hooks/clarification-interceptor.sh` (registered) |
| Doc sync detection | `hooks/doc-sync-detector.sh` (registered) |

---

## 5. The Biggest Gaps (Ranked by Impact)

### Gap 1: Trust Score System is Dead

The entire trust and consequence system is non-functional:
- `trust-score-validator.sh` -- NOT registered
- `confidence-gate.sh` -- NOT registered
- `consequence-evaluator.sh` -- NOT registered
- `lib/trust_report_parser.py` -- never called
- `lib/consequence_engine.py` -- never called
- `lib/skill_archive.py` -- never called

**Impact**: Agent quality is completely unmonitored. The promote/degrade/disable cycle never fires. OKR tracking is impossible.

### Gap 2: No Pre-Task Assessment

The orchestrator never runs any pre-task assessment:
- No complexity classification (`adaptive-bypass`)
- No cost prediction (`cost-predict`)
- No estimation (`estimation-calibration`)
- No scout report (`scout-pattern`)
- No readiness check (`readiness-check`)
- No impact analysis before sdd-apply

**Impact**: Every task gets the same treatment regardless of size. Large tasks are under-governed, trivial tasks are over-governed.

### Gap 3: No Post-Task Verification

The orchestrator never verifies completion:
- No DoD check (`/dod-check`)
- No self-review (`/self-review`)
- No KPI calculation (`/agent-kpis`)
- No cost reporting (`cost_dashboard.py`)

**Impact**: "Done" means whatever the agent says it means. No accountability.

### Gap 4: Python Libs Are Completely Unused

25 Python libraries exist, 0 are called. Key unused capabilities:
- `skill_router.py` -- skill auto-selection
- `prompt_classifier.py` -- user intent capture
- `model_router.py` -- multi-model routing
- `workload_scheduler.py` -- parallel agent scheduling
- `cognitive_load_monitor.py` -- quality degradation detection

**Impact**: Sophisticated decision-making logic is built but never invoked. The orchestrator operates on instinct rather than data.

### Gap 5: 60 Hooks Are Not Registered

Of ~88 hooks, only 28 are in settings.json. Critical missing hooks include the entire scope governance, trust validation, assumption tracking, consequence evaluation, and auto-rollback systems.

**Impact**: Rules that claim to be "always active" via hooks are actually dead. The safety mesh has major holes.

### Gap 6: Session Lifecycle is Incomplete

- `session-resume.sh` -- NOT registered (incomplete tasks never auto-detected)
- `task-recorder.sh` -- NOT registered (task costs never recorded)
- `kpi-trigger.sh` -- NOT registered (KPI thresholds never checked)
- `infra-health.sh` -- NOT registered (infrastructure health unknown)
- `pre-compaction-flush.sh` -- NOT registered (state lost on compaction)

**Impact**: Sessions start blind and end without learning. The feedback loop is broken.

### Gap 7: User Prompt Capture Never Happens

`user-prompt-capture` rule says the orchestrator MUST call `mem_save_prompt` for actionable user messages. The hook (`user-prompt-capture.sh`) is NOT registered and `prompt_classifier.py` is never called.

**Impact**: User intent is lost between sessions. Future sessions know what was built but not WHY.

---

## 6. Recommendations

### Immediate (This Week)

1. **Register critical missing hooks in settings.json**:
   - `pre-compaction-flush.sh` (prevents state loss -- highest priority)
   - `trust-score-validator.sh` (enables trust tracking)
   - `confidence-gate.sh` (blocks low-confidence results)
   - `scope-proportionality.sh` (prevents over-scoped changes)
   - `assumption-tracker.sh` (monitors agent guesswork)
   - `agent-prelaunch.sh` (enables task tracking)
   - `tool-loop-detector.sh` (prevents infinite loops)
   - `infra-health.sh` (session start health check)
   - `session-resume.sh` (resume incomplete tasks)
   - `task-recorder.sh` (record task costs)
   - `kpi-trigger.sh` (trigger KPI checks)

2. **Update CLAUDE.md to REQUIRE tool usage**:
   - Add: "Before ANY sub-agent launch, check model-routing table"
   - Add: "After ANY agent completion, verify trust score is present"
   - Add: "At session end, MUST call /agent-kpis if 5+ agent completions"
   - Add: "At session end, MUST report costs via cost_dashboard"

### Short-Term (This Month)

3. **Create a pre-flight checklist for agent launches**:
   - Classify complexity (trivial/small/medium/large/critical)
   - Select model from routing table
   - Include acceptance criteria
   - Include verification commands
   - For medium+: run /scout first

4. **Create a post-flight checklist for agent completions**:
   - Parse trust report (trust_report_parser.py)
   - Run /dod-check for the task's complexity level
   - Log to consequence system
   - Record cost event

5. **Wire up the Python libs** via orchestrator behavioral rules:
   - `skill_router.py` -- call on every user message
   - `prompt_classifier.py` -- call on every user message
   - `model_router.py` -- call before every agent launch
   - `cost_dashboard.py` -- call at session end

### Medium-Term (Next Quarter)

6. **Monitor self-usage rate as a KPI**:
   - Track: hooks registered / hooks available
   - Track: skills auto-triggered / skills that should auto-trigger
   - Track: rules enforced / rules claimed "always active"
   - Target: 80% self-usage rate

7. **Automate the feedback loop**:
   - Wire consequence system (promote/degrade/disable)
   - Wire skill archive (evolutionary improvement)
   - Wire self-improvement protocol (weekly auto-run)

8. **Create integration tests for self-usage**:
   - Test: "Does the orchestrator call skill_router on user message?"
   - Test: "Does the orchestrator include acceptance criteria in agent prompts?"
   - Test: "Does the orchestrator report costs at session end?"
   - Test: "Are trust scores logged after agent completions?"

---

## 7. Root Cause Analysis

### Why Does the Orchestrator Not Use Its Own Tools?

1. **Behavioral rules have no enforcement mechanism**. Rules in CLAUDE.md say "MUST" but there is no hook to verify compliance. The orchestrator's LLM layer optimizes for task completion speed, not rule compliance.

2. **Python libs require Bash execution**. The orchestrator cannot `import` Python directly. Calling `python3 -c "..."` adds friction. Most libs are never called because the orchestrator does not think to shell out to Python.

3. **Hook registration is manual and incomplete**. Adding a hook requires editing settings.json. There is no automated sync between available hooks and registered hooks. The self-install.sh hook syncs rules but NOT hook registrations.

4. **Skills are passive**. Skills wait to be invoked. There is no mechanism to auto-invoke skills based on context (skill_router.py exists but is never called).

5. **Rules are loaded but not actionable**. RULES-COMPACT.md is loaded at session start (~1500 tokens) but it is a reference document, not executable logic. The orchestrator reads it but does not systematically check each rule before/after actions.

6. **No meta-monitoring**. There is no hook or skill that checks whether the orchestrator is following its own rules. The system monitors agent quality but not orchestrator quality.

### Systemic Fix

The fundamental issue is that the orchestrator is a **language model following behavioral instructions**, not a **deterministic system executing a checklist**. The fix is to move enforcement from "rules the LLM should follow" to "hooks that run automatically":

- Every "MUST" rule should have a corresponding hook that enforces it
- Every "always active" rule should be verifiable by a registered hook
- The gap between "rules written" and "hooks registered" should be tracked as a KPI
- A self-audit hook should run at session end and report compliance

---

## Appendix: Complete Hook Registration Status

### hooks/ Directory (44 files)

| Hook | Registered? |
|------|------------|
| auto-checkpoint.sh | YES |
| clarification-gate.sh | YES (via packages symlink) |
| blast-radius.sh | YES (via packages symlink) |
| cognitive-os-health.sh | NO |
| completeness-check.sh | NO |
| concurrent-write-guard.sh | NO |
| content-policy.sh | YES |
| conversation-capture.sh | NO |
| crash-recovery.sh | YES |
| doc-sync-detector.sh | YES (via packages symlink) |
| error-pattern-detector.sh | YES |
| error-pipeline.sh | YES |
| guardrails-validator.sh | NO |
| infra-health.sh | NO |
| infra-intent-detector.sh | NO |
| inject-phase-context.sh | NO |
| jupyter-sandbox.sh | NO |
| large-file-advisor.sh | YES |
| mcp-scan.sh | NO |
| notify.sh | NO |
| package-sync.sh | YES |
| pre-cleanup-snapshot.sh | NO |
| pre-commit-gate.sh | NO (git hook, not Claude hook) |
| pre-compaction-flush.sh | NO |
| private-mode-gate.sh | NO |
| private-mode-metrics-gate.sh | NO |
| rate-limit-protection.sh | NO |
| rate-limiter.sh | YES |
| resource-check.sh | NO |
| result-truncator.sh | YES (via packages symlink) |
| secret-detector.sh | YES |
| self-install.sh | YES |
| semgrep-scan.sh | NO |
| aguara-scan.sh | NO |
| session-cleanup.sh | YES |
| session-init.sh | YES |
| session-knowledge-extractor.sh | NO |
| session-learning.sh | YES |
| session-resume.sh | NO |
| session-state-save.sh | NO |
| singularity-check.sh | NO |
| subagent-context-injector.sh | NO |
| teammate-idle.sh | YES |
| tool-discovery-trigger.sh | NO |
| user-prompt-capture.sh | NO |
| code-review-on-commit.sh | NO |
| task-created.sh | YES |
| task-completed.sh | YES |

### packages/**/hooks/ (44 files)

| Hook | Registered? |
|------|------------|
| agent-prelaunch.sh | NO |
| auto-rollback-trigger.sh | NO |
| clarification-interceptor.sh | YES (registered from packages path) |
| doc-sync-detector.sh | YES (registered from hooks/ symlink) |
| dry-run-preview.sh | NO |
| engram-auto-import.sh | NO |
| engram-auto-sync.sh | NO |
| kpi-trigger.sh | NO |
| memu-sync.sh | NO |
| metrics-calibrator-trigger.sh | NO |
| metrics-rotation.sh | NO |
| sync-to-repo.sh | NO |
| agent-checkpoint.sh | YES |
| result-truncator.sh | YES |
| skill-tracker.sh | NO |
| agent-bus-monitor.sh | NO |
| observability-trace.sh | NO |
| task-recorder.sh | NO |
| paperclip-sync.sh | NO |
| adaptive-bypass.sh | NO |
| contextual-rule-loader.sh | NO |
| idle-service-cleanup.sh | NO |
| agnix-lint.sh | NO |
| scope-creep-detector.sh | NO |
| auto-skill-generator.sh | NO |
| consequence-evaluator.sh | NO |
| trust-score-validator.sh | NO |
| prompt-quality.sh | NO |
| clarification-gate.sh | YES (registered from hooks/ symlink) |
| scope-proportionality.sh | NO |
| blast-radius.sh | YES (registered from hooks/ symlink) |
| epic-task-detector.sh | NO |
| tool-loop-detector.sh | NO |
| architecture-compliance.sh | NO |
| assumption-tracker.sh | NO |
| paperclip-agent-status.sh | YES |
| paperclip-sdd-sync.sh | YES |
| paperclip-squad-sync.sh | YES |
| claim-validator.sh | YES (registered from hooks/ symlink) |
| completion-gate.sh | YES (registered from hooks/ symlink) |
| confidence-gate.sh | NO |
| paperclip-cost-stream.sh | NO |
| paperclip-task-sync.sh | YES |
