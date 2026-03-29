# Self-Building Protocol -- COS Builds Itself

## Principle

The OS that builds itself is the strongest validation of its own value. If the orchestrator ignores its own tools, those tools are either broken or unnecessary. Neither is acceptable.

COS has 25+ library modules (skill_router, workload_scheduler, escalation_detector, reverse_engineer, repo_analyzer, code_reviewer, trust_report_parser, cognitive_load_monitor, cost_dashboard, prompt_classifier, and more). The orchestrator MUST use them as a first-class part of every session. An orchestrator that bypasses its own tooling is a cobbler whose children have no shoes.

## ADR-SBP-001: Mandatory Self-Usage

### Status
Accepted

### Context
The orchestrator has access to sophisticated libraries (skill_router, WorkloadScheduler, EscalationDetector, etc.) but relies on manual judgment for tasks these tools were designed to automate. This creates two problems: (1) the tools are never battle-tested in real usage, and (2) the orchestrator makes worse decisions than the tools would.

### Decision
The orchestrator MUST use its own tools at defined integration points. These are MUST rules, not SHOULD.

### Consequences
- Orchestrator responses take marginally longer due to tool invocations
- Tool bugs surface immediately (good -- dogfooding)
- Sessions produce richer metrics for self-improvement
- Tools that prove useless will be identified and removed

---

## Mandatory Self-Usage Protocol (ALWAYS ACTIVE)

### Phase 1: Message Reception

Before responding to ANY user message that contains actionable intent:

| Step | Tool | Purpose | When to Skip |
|------|------|---------|-------------|
| 1 | `prompt_classifier.classify_prompt(message)` | Classify intent and capture to engram if actionable | Never -- always runs |
| 2 | `skill_router.best_match(message)` | Suggest the right skill for the task | Never -- always runs |

**Protocol**:
1. Run `classify_prompt(message)` from `lib/prompt_classifier.py`. If `result.should_capture` is True, call `mem_save_prompt`.
2. Run `skill_router.best_match(message)`. If confidence >= 0.80, suggest the skill to the user before proceeding. If confidence 0.50-0.79, mention as a possibility. Below 0.50, proceed without suggestion.

### Phase 2: Task Planning

Before launching sub-agents:

| Step | Tool | Condition | Purpose |
|------|------|-----------|---------|
| 3 | `WorkloadScheduler.plan(tasks)` | Launching > 3 agents | Distribute across rate limit windows |
| 4 | Report plan to user | Always when scheduler runs | Transparency -- user sees dispatch order |

**Protocol**:
1. When launching more than 3 agents in a batch, construct `TaskRequest` objects with priority, estimated tokens, and model.
2. Call `scheduler.plan(tasks)` and report the plan summary to the user before dispatching.
3. Dispatch `plan.dispatch_now` immediately, queue `plan.queued` for later.

### Phase 3: Pre-Implementation Investigation

Before implementing or debugging unfamiliar code:

| Step | Tool | Condition | Purpose |
|------|------|-----------|---------|
| 5 | `/reverse-engineer` | Investigating any dependency or unfamiliar module | Structured analysis before trial-and-error |
| 6 | `/repo-forensics` | Evaluating any external repository | Surface-level evaluation with metrics |
| 7 | `repo_analyzer` | Analyzing codebase structure | Understand project shape |

**Protocol**:
1. When investigating a dependency, an unfamiliar module, or debugging a complex system: use `/reverse-engineer` FIRST. Trial-and-error without understanding the system wastes tokens.
2. When evaluating an external repository (e.g., a GitHub URL in the user's message): use `/repo-forensics` for surface evaluation.
3. Never skip structured investigation in favor of "I will just read the code."

### Phase 4: During Agent Execution

While sub-agents are running:

| Step | Tool | Condition | Purpose |
|------|------|-----------|---------|
| 8 | `EscalationDetector` | Every agent run | Detect loops, no-progress, error repeats |
| 9 | `CognitiveLoadMonitor` | Context usage > 50% | Track quality degradation |

**Protocol**:
1. Sub-agent prompts MUST include the escalation protocol instructions (from `rules/agent-escalation.md`).
2. When context usage exceeds 50%, monitor quality snapshots. At 70%, save to engram. At 85%, stop new work.
3. If an agent's output contains `ESCALATION:`, follow the orchestrator response protocol (suggest/recommend/urgent).

### Phase 5: Post-Completion

After every agent completes:

| Step | Tool | Condition | Purpose |
|------|------|-----------|---------|
| 10 | Trust Report validation | Every agent completion | Verify trust score exists and meets thresholds |
| 11 | `code_reviewer.review_files()` | Agent wrote or modified code | Catch quality issues |
| 12 | Auto-skill generation check | Complex completions (10+ tools, 8K+ chars) | Extract reusable skills |
| 13 | `CostDashboard` | Session end | Report actual cost |

**Protocol**:
1. Every agent completion MUST include a Trust Report. If missing, the orchestrator treats verification as FAILED.
2. If the agent wrote code, run `code_reviewer.review_files()` on the changed files.
3. Check if the completion meets the auto-skill generation threshold (10+ tool uses OR 8K+ character response). If so, generate a skill.
4. At session end, use `CostDashboard.format_session_report()` to report costs.

### Phase 6: When Stuck

When the orchestrator or an agent is stuck on the same problem for > 15 minutes (approximately > 20 tool calls without progress):

| Step | Tool | Purpose |
|------|------|---------|
| 14 | `EscalationDetector.check_should_escalate()` | Formalize the stuck diagnosis |
| 15 | Try different approach or model | Break the deadlock |
| 16 | Save what was tried to engram | Prevent future agents from repeating the same dead end |

**Protocol**:
1. Detect stuck state via escalation signals: `loop_detected` (same file edited 3+ times), `error_repeat` (same error 2+ times), `no_progress` (> 10 tool calls without progress), or `confidence_drop` (error rate > 50%).
2. Try a different approach: switch model (sonnet to opus for debugging), change strategy, or decompose differently.
3. If still stuck after one approach change: escalate to the user with a structured diagnosis.
4. Save the diagnosis and what was tried to engram under `bugfix/{service}/{issue-slug}`.

---

## Tool-to-Integration-Point Map

Complete mapping of every COS library to its mandatory usage point:

| Library | File | Integration Point | Frequency |
|---------|------|-------------------|-----------|
| `skill_router` | `lib/skill_router.py` | Phase 1: message reception | Every message |
| `prompt_classifier` | `lib/prompt_classifier.py` | Phase 1: message reception | Every message |
| `workload_scheduler` | `lib/workload_scheduler.py` | Phase 2: task planning | When > 3 agents |
| `reverse_engineer` | `lib/reverse_engineer.py` | Phase 3: investigation | Before trial-and-error |
| `repo_analyzer` | `lib/repo_analyzer.py` | Phase 3: investigation | Codebase analysis |
| `escalation_detector` | `lib/escalation_detector.py` | Phase 4: execution + Phase 6: stuck | Every agent run |
| `cognitive_load_monitor` | `lib/cognitive_load_monitor.py` | Phase 4: execution | Context > 50% |
| `trust_report_parser` | `lib/trust_report_parser.py` | Phase 5: completion | Every agent completion |
| `code_reviewer` | `lib/code_reviewer.py` | Phase 5: completion | Code-writing agents |
| `cost_dashboard` | `lib/cost_dashboard.py` | Phase 5: session end | Every session |
| `model_router` | `lib/model_router.py` | Phase 2: agent launch | Every agent launch |
| `rate_limiter` | `lib/rate_limiter.py` | Phase 2: agent launch | Every agent launch |
| `smart_reader` | `lib/smart_reader.py` | Phase 3: large file reads | Files > 40KB |
| `consequence_engine` | `lib/consequence_engine.py` | Phase 5: completion | Trust score evaluation |
| `skill_archive` | `lib/skill_archive.py` | Phase 5: completion | Skill performance tracking |
| `checkpoint_manager` | `lib/checkpoint_manager.py` | Phase 4: periodic | Every 5 minutes |
| `retry_scheduler` | `lib/retry_scheduler.py` | Phase 6: rate limited | Rate limit blocks |
| `singularity` | `lib/singularity.py` | Autonomous loop | When activated |
| `dynamic_tool_creator` | `lib/dynamic_tool_creator.py` | Phase 5: complex tasks | Auto-skill threshold met |
| `smart_infra` | `lib/smart_infra.py` | Phase 3: service needs | Docker service required |
| `bifrost_client` | `lib/bifrost_client.py` | Phase 2: gateway routing | LLM gateway calls |
| `gateway_selector` | `lib/gateway_selector.py` | Phase 2: gateway routing | Provider selection |
| `test_framework_detector` | `lib/test_framework_detector.py` | Phase 3: test tasks | Writing/running tests |

---

## Self-Usage KPI

### What to Measure

Track the percentage of available tools that were actually used during each session, relative to how many were relevant.

| Metric | Target | Alert Threshold | Data Source |
|--------|--------|-----------------|-------------|
| Relevant tool usage rate | > 50% per session | < 30% means orchestrator is "going manual" | `metrics/self-usage.jsonl` |
| Skill router invocations | 1 per user message | 0 for any message with actionable intent | `metrics/skill-routing.jsonl` |
| Prompt classifier invocations | 1 per user message | 0 for any actionable message | `metrics/prompt-captures.jsonl` |
| WorkloadScheduler invocations | 1 per batch of > 3 agents | 0 for any batch dispatch | `metrics/workload-schedule.jsonl` |
| Escalation detection active | 100% of agent runs | Any agent run without escalation protocol | `metrics/escalation-events.jsonl` |
| Trust report presence | 100% of agent completions | Any completion without trust report | `metrics/trust-scores.jsonl` |
| reverse-engineer before trial-and-error | 100% of investigation tasks | Any investigation that starts with trial-and-error | `metrics/investigation-methods.jsonl` |

### How to Calculate

```
relevant_tools = tools whose integration point was triggered during the session
used_tools = tools that were actually invoked
self_usage_rate = len(used_tools) / len(relevant_tools) * 100
```

### Reporting

At session end, the orchestrator SHOULD include a self-usage summary:

```
SELF-USAGE REPORT:
  Tools available: 25
  Tools relevant this session: 8
  Tools actually used: 6 (75%)
  Missed opportunities:
    - WorkloadScheduler: launched 5 agents without scheduling
    - code_reviewer: 3 code changes without review
```

### Integration with Agent KPIs

The self-usage rate feeds into the Agent Efficiency OKR:
- Self-usage rate > 50%: healthy dogfooding
- Self-usage rate 30-50%: WARNING -- orchestrator bypassing its own tools
- Self-usage rate < 30%: ALERT -- tools are being ignored, defeating the purpose of COS

---

## CLAUDE.md Integration

The following block MUST be added to `~/.claude/CLAUDE.md` under the orchestrator rules:

```markdown
## MANDATORY Self-Usage Protocol (ALWAYS ACTIVE)

### Before EVERY user message response
1. Run `prompt_classifier.classify_prompt(message)` -- capture actionable intent to engram
2. Run `skill_router.best_match(message)` -- suggest the right skill if confidence >= 0.80

### Before launching > 3 agents
3. Run `WorkloadScheduler.plan(tasks)` -- distribute across rate limit windows
4. Report the plan to the user before dispatching

### During agent execution
5. Include `EscalationDetector` protocol in every sub-agent prompt
6. Monitor `CognitiveLoadMonitor` when context > 50%

### After EVERY agent completion
7. Validate Trust Report exists and score meets threshold
8. Run `code_reviewer.review_files()` if code was written
9. Check auto-skill generation threshold (10+ tools OR 8K+ chars)

### When investigating any dependency or unfamiliar code
10. Use `/reverse-engineer` FIRST -- never trial-and-error without structured analysis
11. Use `/repo-forensics` for external repository evaluation

### When stuck > 15 minutes on same problem
12. Run `EscalationDetector.check_should_escalate()` to formalize diagnosis
13. Try different approach (model switch, strategy change, decomposition)
14. Save what was tried to engram -- prevent future dead ends
15. If still stuck after approach change: escalate to user with structured report
```

---

## Trade-Off Analysis

### Option A: Behavioral Rules Only (chosen)

The protocol is enforced through CLAUDE.md rules and session-level behavioral expectations. No new hooks are created.

**Advantages**:
- Zero additional latency per tool call
- No hook registration overhead
- Works immediately without infrastructure changes
- Adapts to context (rules can be selectively applied)

**Disadvantages**:
- Relies on the orchestrator following its own rules (no enforcement mechanism)
- Self-usage metrics require manual tracking
- Violations are invisible unless audited

### Option B: Hook-Enforced Protocol (deferred)

Create PreToolUse and PostToolUse hooks that enforce each integration point programmatically.

**Advantages**:
- Automated enforcement -- violations are impossible
- Metrics are captured automatically
- Consistent across sessions

**Disadvantages**:
- Adds 100-500ms per tool call for enforcement checks
- Hook chain is already 61 hooks in paranoid mode
- Risk of hook conflicts with existing quality gates

### Decision

Start with Option A (behavioral rules). After 2-4 weeks of usage data, evaluate whether violations are frequent enough to warrant Option B. The self-usage KPI provides the measurement mechanism.

---

## Relationship to Existing Rules

| Existing Rule | How Self-Building Protocol Extends It |
|---------------|--------------------------------------|
| `dogfooding.md` | Dogfooding says "use SDD to build COS." Self-building says "use ALL COS tools, not just SDD." |
| `adaptive-bypass.md` | Bypass determines the WORKFLOW. Self-building determines the TOOLS used within that workflow. |
| `agent-quality.md` | Quality says agents must do the maximum. Self-building says the orchestrator must use its full toolbox. |
| `skill-management.md` | Skill management routes tasks to skills. Self-building ensures the router is actually called. |
| `token-economy.md` | Token economy says check memory first. Self-building says check ALL tools first. |
| `agent-escalation.md` | Escalation defines the protocol. Self-building mandates the detector is always active. |
| `trust-score.md` | Trust score defines the report format. Self-building mandates validation on every completion. |
| `workload-scheduling.md` | Scheduling defines the algorithm. Self-building mandates the scheduler is called for batches. |

---

## Implementation Phases

### Phase 1: Behavioral Adoption (Week 1-2)
1. Add the MANDATORY Self-Usage Protocol section to `~/.claude/CLAUDE.md`
2. Create `metrics/self-usage.jsonl` tracking format
3. Start manually tracking self-usage at session end

### Phase 2: Metric Instrumentation (Week 3-4)
1. Add self-usage tracking to the session summary protocol
2. Create a `/self-usage-report` skill that calculates the KPI from metrics files
3. Integrate self-usage rate into Agent KPIs

### Phase 3: Enforcement (Week 5+, if needed)
1. If self-usage rate < 30% for 2+ consecutive weeks, create enforcement hooks
2. `self-usage-checker.sh` PostToolUse hook: verifies skill_router was called before Agent launches
3. `investigation-method.sh` PreToolUse hook: suggests /reverse-engineer when investigation patterns are detected

---

## Contextual Trigger

This rule is loaded when: self-building, dogfooding, tool usage, COS builds itself, orchestrator tools, self-usage.
