# Hook Security Profiles

> Defines which hooks are active at each security level. Profiles control the trade-off between safety overhead and development speed. Unlike efficiency profiles (lean/standard/full in `scripts/apply-efficiency-profile.sh`), security profiles focus specifically on defense-in-depth layering.

## Relationship to Efficiency Profiles

The `efficiency.profile` in `cognitive-os.yaml` (lean/standard/full) controls token overhead and governance weight. Security profiles (minimal/standard/paranoid) control which safety mesh layers and security hooks are active. They are complementary but independent axes:

| Axis | Values | Controls |
|------|--------|----------|
| Efficiency | lean, standard, full | Token overhead, governance weight, capability level |
| Security | minimal, standard, paranoid | Safety mesh depth, security scanning, quality gates |

Use `scripts/set-security-profile.sh` to switch security profiles. Use `scripts/apply-efficiency-profile.sh` to switch efficiency profiles.

## Capability Level Interaction

Hooks check `model_capability.auto_disable` internally. At capability level 3 (current default), `context-management` is auto-disabled. At level 4, `clarification-gate`, `assumption-tracking`, `confidence-gate`, `model-routing`, and `blast-radius` self-disable even if registered. The security profile determines what is **registered**; the capability level determines what **self-disables** at runtime.

---

## Profile: minimal

**Use case**: Development, rapid prototyping, exploration, solo coding sessions
**Overhead**: ~100-200ms per tool call
**Active hooks**: 11
**Safety mesh layers**: 0 of 12 (no safety mesh hooks registered)
**Security posture**: Error capture and secret detection only -- no quality gates, no agent governance

### Rationale

Strips all quality gates and agent governance hooks. Retains only: session lifecycle (boot/shutdown), error capture (learn from failures), secret detection (never leak credentials), crash recovery (never lose work), and auto-checkpoint (periodic git stash). Suitable for experienced developers on capable models doing exploratory work where speed matters more than governance.

### Hooks

| Event | Matcher | Hook | Purpose | Profile Justification |
|-------|---------|------|---------|----------------------|
| SessionStart | (all) | `self-install.sh` | Symlink rules for dogfooding repo | Required for OS self-hosting |
| SessionStart | (all) | `session-init.sh` | Create session directory, generate session ID | Core lifecycle -- sessions break without this |
| SessionStart | (all) | `crash-recovery.sh` | Detect orphaned stashes from crashed sessions | Prevents silent work loss |
| PreToolUse | Bash\|Agent\|Edit\|Write | `rate-limiter.sh` | Prevent token flooding and runaway loops | Last-resort cost protection -- always needed |
| PostToolUse | Bash | `error-pipeline.sh` | Capture test/build/lint failures to JSONL | Foundation for error learning across sessions |
| PostToolUse | Edit\|Write | `secret-detector.sh` | Block writes containing credentials/API keys | Security non-negotiable -- credential leaks are irreversible |
| PostToolUse | Bash\|Edit\|Write | `auto-checkpoint.sh` | Periodic git stash for crash recovery | Prevents work loss on session crash |
| PostToolUse | Agent | `agent-checkpoint.sh` | Update task status in active-tasks.json | Enables task resumption across sessions |
| PreCompact | (all) | `pre-compaction-flush.sh` | Remind agent to save state to Engram before compaction | Data safety -- never lose context on compaction |
| Stop | (all) | `session-learning.sh` | Capture session errors and patterns | Feeds self-improvement across sessions |
| Stop | (all) | `session-cleanup.sh` | Merge metrics, release locks, clean up | Required for clean session teardown |

### What is NOT active

- No safety mesh layers (clarification-gate, blast-radius, claim-validator, etc.)
- No content policy enforcement on writes
- No doc-sync detection
- No quality gates (completion-gate, trust-score, confidence-gate)
- No prompt quality or completeness checks
- No scope governance (proportionality, creep detection)
- No observability tracing
- No infrastructure health checks

---

## Profile: standard (recommended)

**Use case**: Normal development with safety nets, team environments, daily coding
**Overhead**: ~300-500ms per tool call
**Active hooks**: 26
**Safety mesh layers**: 5 of 12 (layers 1, 2, 4, 6, 10)
**Security posture**: Critical safety gates active, content policy enforced, quality gates on agent output

### Rationale

Adds the most impactful safety gates from the 12-layer mesh without activating every possible check. Prioritizes hooks that catch the highest-severity failure modes: vague prompts (clarification-gate), credential leaks (secret-detector + content-policy), hallucinated claims (claim-validator), and scope awareness (blast-radius). Skips hooks that add overhead without proportional benefit for standard development: assumption tracking, trust score validation, confidence gates, prompt quality scoring, scope proportionality, auto-rollback, consequence evaluation.

### Hooks

| Event | Matcher | Hook | Purpose | Profile Justification |
|-------|---------|------|---------|----------------------|
| SessionStart | (all) | `self-install.sh` | Symlink rules for dogfooding repo | Required for OS self-hosting |
| SessionStart | (all) | `session-init.sh` | Create session directory, generate session ID | Core lifecycle |
| SessionStart | (all) | `crash-recovery.sh` | Detect orphaned stashes from crashed sessions | Prevents silent work loss |
| PreToolUse | Bash\|Agent\|Edit\|Write | `rate-limiter.sh` | Prevent token flooding and runaway loops | Cost protection |
| PreToolUse | Read | `large-file-advisor.sh` | Warn before reading very large files | Prevents context waste |
| PreToolUse | Agent | `clarification-gate.sh` | Block vague/ambiguous agent prompts (score > 60) | **Safety mesh layer 1** -- prevents wasted agent runs on unclear tasks |
| PreToolUse | Agent | `blast-radius.sh` | Warn on HIGH/CRITICAL impact tasks | **Safety mesh layer 2** -- awareness before launching large-scope work |
| PreToolUse | Agent | `error-pattern-detector.sh` | Inject warnings for repeated error patterns | Prevents repeating known failures |
| PostToolUse | Bash | `error-pipeline.sh` | Capture test/build/lint failures to JSONL | Foundation for error learning |
| PostToolUse | Bash | `result-truncator.sh` | Truncate large command outputs | Prevents context flooding from verbose commands |
| PostToolUse | Edit\|Write | `secret-detector.sh` | Block writes containing credentials/API keys | Security non-negotiable |
| PostToolUse | Edit\|Write | `content-policy.sh` | Block prohibited terms/patterns in written files | Prevents policy violations in committed code |
| PostToolUse | Edit\|Write | `doc-sync-detector.sh` | Detect when code changes make docs stale | Prevents documentation drift |
| PostToolUse | Bash\|Edit\|Write | `auto-checkpoint.sh` | Periodic git stash for crash recovery | Prevents work loss |
| PostToolUse | Agent | `claim-validator.sh` | Verify agent file creation/modification claims exist | **Safety mesh layer 6** -- catches hallucinated outputs |
| PostToolUse | Agent | `completion-gate.sh` | Check acceptance criteria + DoD + auto-refine | Quality gate on agent output |
| PostToolUse | Agent | `agent-checkpoint.sh` | Update task status in active-tasks.json | Task lifecycle tracking |
| PostToolUse | Agent | `clarification-interceptor.sh` | Detect NEEDS_CLARIFICATION signals from agents | **Safety mesh layer 10** -- enables mid-task clarification |
| PreCompact | (all) | `pre-compaction-flush.sh` | Remind agent to save state to Engram before compaction | Data safety |
| SubagentStart | (all) | `subagent-context-injector.sh` | Inject agent preamble + engram sidecar context | Consistent subagent context |
| UserPromptSubmit | (all) | `user-prompt-capture.sh` | Capture user prompts to engram (async) | Intent preservation |
| TeammateIdle | (all) | `teammate-idle.sh` | Check for unclaimed tasks before teammate goes idle | Task throughput |
| TaskCreated | (all) | `task-created.sh` | Validate task quality and prevent duplicates | Task governance |
| TaskCompleted | (all) | `task-completed.sh` | Verify completion criteria on task done | Quality gate |
| Stop | (all) | `session-learning.sh` | Capture session errors and patterns | Self-improvement data |
| Stop | (all) | `session-cleanup.sh` | Merge metrics, release locks, clean up | Clean session teardown |

### What is NOT active (compared to paranoid)

- No prompt quality scoring (advisory, low impact at standard level)
- No completeness check (advisory, covered by clarification-gate for blocking cases)
- No assumption tracking (advisory, low signal-to-noise for most development)
- No trust score validation (advisory only -- does not block)
- No confidence gate (blocks only in production phase -- less relevant during reconstruction)
- No consequence evaluator (OKR-driven feedback -- more relevant for long-running projects)
- No scope proportionality (catches edge cases, not high-frequency failures)
- No scope creep detector (requires active task scope metadata)
- No auto-rollback trigger (relevant only for SDD pipeline failures)
- No auto-skill generator (optimization, not safety)
- No external scanners (semgrep); aguara is registered in paranoid only — the library-level memory_scanner.py runs regardless of profile

- No observability tracing (langfuse/opik)
- No architecture compliance checks

---

## Profile: paranoid

**Use case**: Production deployments, compliance audits, security-sensitive work, multi-agent orchestration
**Overhead**: ~2-5s per tool call
**Active hooks**: 61
**Safety mesh layers**: 12 of 12 (all layers active)
**Security posture**: Maximum defense-in-depth. Every quality gate, every security scanner, every governance check.

### Rationale

Activates the complete 12-layer safety mesh plus all governance, observability, and security hooks. Every agent prompt is scored for quality and completeness. Every agent output is checked for assumptions, confidence, proportionality, and hallucinations. Scope creep is detected in real-time. Architecture compliance is enforced. External security scanners run on code changes. The overhead is significant (2-5s per tool call) but acceptable when the cost of a defect exceeds the cost of delay.

### Hooks

| Event | Matcher | Hook | Purpose | Profile Justification |
|-------|---------|------|---------|----------------------|
| **SessionStart** | | | | |
| SessionStart | (all) | `self-install.sh` | Symlink rules for dogfooding repo | Required for OS self-hosting |
| SessionStart | (all) | `session-init.sh` | Create session directory, generate session ID | Core lifecycle |
| SessionStart | (all) | `crash-recovery.sh` | Detect orphaned stashes from crashed sessions | Work loss prevention |
| SessionStart | (all) | `session-resume.sh` | Detect incomplete tasks from previous sessions | Task continuity |
| SessionStart | (all) | `cognitive-os-health.sh` | 1-line health summary (phase, budget, services) | Situational awareness at session start |
| SessionStart | (all) | `infra-health.sh` | Check Docker service availability | Infrastructure readiness verification |
| SessionStart | (all) | `metrics-rotation.sh` | Rotate large JSONL metrics files | Prevents metrics file bloat |
| SessionStart | (all) | `engram-auto-import.sh` | Import latest team memory from exports | Cross-session knowledge continuity |
| **PreCompact** | | | | |
| PreCompact | (all) | `pre-compaction-flush.sh` | Remind agent to save state to Engram before compaction | Data safety -- prevents context loss on compaction |
| **PreToolUse** | | | | |
| PreToolUse | Bash\|Agent\|Edit\|Write | `rate-limiter.sh` | Prevent token flooding and runaway loops | Cost protection |
| PreToolUse | Read | `large-file-advisor.sh` | Warn before reading very large files | Context waste prevention |
| PreToolUse | Agent | `clarification-gate.sh` | Block vague/ambiguous agent prompts | **Safety mesh layer 1** |
| PreToolUse | Agent | `blast-radius.sh` | Warn on HIGH/CRITICAL impact tasks | **Safety mesh layer 2** |
| PreToolUse | Agent | `dry-run-preview.sh` | Block execution when DRY_RUN=true | **Safety mesh layer 3** |
| PreToolUse | Agent | `aguara-scan.sh` | Rule-based agent prompt security scan | External security scanner |
| PreToolUse | Agent | `error-pattern-detector.sh` | Inject warnings for repeated error patterns | Error prevention |
| PreToolUse | Agent | `completeness-check.sh` | Warn if agent prompt lacks exhaustive scope | Quality advisory |
| PreToolUse | Agent | `prompt-quality.sh` | Score prompt on 5 quality dimensions | Quality advisory |
| PreToolUse | Agent | `agent-prelaunch.sh` | Register task in active-tasks.json before launch | Task governance |
| PreToolUse | Agent | `inject-phase-context.sh` | Inject phase context from config | Phase-aware behavior |
| PreToolUse | Agent | `contextual-rule-loader.sh` | Load full rules matching contextual triggers | Dynamic rule loading |
| PreToolUse | Agent | `rate-limit-protection.sh` | Check rate limit headroom before agent launch | Rate limit protection |
| PreToolUse | Agent | `resource-check.sh` | Check budget before agent launch | Budget governance |
| PreToolUse | Agent | `infra-intent-detector.sh` | Suggest infra components for agent tasks | Infrastructure awareness |
| PreToolUse | Agent | `pre-cleanup-snapshot.sh` | Detect cleanup intent, suggest capability snapshot | Capability protection |
| PreToolUse | Edit\|Write | `concurrent-write-guard.sh` | Advisory file locking for concurrent sessions | Multi-session safety |
| PreToolUse | Bash | `jupyter-sandbox.sh` | Route Python to Jupyter when JUPYTER_SANDBOX=true | Sandboxed execution |
| **SubagentStart** | | | | |
| SubagentStart | (all) | `subagent-context-injector.sh` | Inject agent preamble + engram sidecar context | Consistent subagent context and governance |
| **UserPromptSubmit** | | | | |
| UserPromptSubmit | (all) | `user-prompt-capture.sh` | Capture user prompts to engram (async, never blocks) | Intent preservation across sessions |
| **TeammateIdle** | | | | |
| TeammateIdle | (all) | `teammate-idle.sh` | Check for unclaimed tasks before teammate goes idle | Task throughput optimization |
| **TaskCreated** | | | | |
| TaskCreated | (all) | `task-created.sh` | Validate task quality and prevent duplicates | Task governance |
| **TaskCompleted** | | | | |
| TaskCompleted | (all) | `task-completed.sh` | Verify completion criteria on task done | Quality gate on task completion |
| **PostToolUse** | | | | |
| PostToolUse | Bash | `error-pipeline.sh` | Capture test/build/lint failures to JSONL | Error learning |
| PostToolUse | Bash | `result-truncator.sh` | Truncate large command outputs | Context protection |
| PostToolUse | Bash\|Edit\|Write | `auto-checkpoint.sh` | Periodic git stash for crash recovery | Work loss prevention |
| PostToolUse | Edit\|Write | `secret-detector.sh` | Block writes containing credentials/API keys | Security non-negotiable |
| PostToolUse | Edit\|Write | `content-policy.sh` | Block prohibited terms/patterns in written files | Policy enforcement |
| PostToolUse | Edit\|Write | `doc-sync-detector.sh` | Detect when code changes make docs stale | Documentation freshness |
| PostToolUse | Edit\|Write | `scope-creep-detector.sh` | Detect edits outside approved task scope | **Scope governance** |
| PostToolUse | Edit\|Write | `agnix-lint.sh` | Lint agent configuration files | Config quality (external tool) |
| PostToolUse | Agent | `scope-proportionality.sh` | Check if response is proportional to task | **Safety mesh layer 5** |
| PostToolUse | Agent | `claim-validator.sh` | Verify agent file claims against filesystem | **Safety mesh layer 6** |
| PostToolUse | Agent | `assumption-tracker.sh` | Track assumption language in agent output | **Safety mesh layer 7** (reassigned from layer 6 in doc) |
| PostToolUse | Agent | `trust-score-validator.sh` | Validate Trust Report presence and log scores | **Safety mesh layer 8** |
| PostToolUse | Agent | `confidence-gate.sh` | Block low-confidence results in production | **Safety mesh layer 9** |
| PostToolUse | Agent | `clarification-interceptor.sh` | Detect NEEDS_CLARIFICATION signals | **Safety mesh layer 10** |
| PostToolUse | Agent | `auto-rollback-trigger.sh` | Trigger rollback on verify-apply exhaustion | **Safety mesh layer 11** |
| PostToolUse | Agent | `reinvention-check.sh` | Detect re-solving already-solved problems; suggest reuse | **Safety mesh layer 13** |
| PostToolUse | Agent | `completion-gate.sh` | Check acceptance criteria + DoD + auto-refine | Quality gate |
| PostToolUse | Agent | `consequence-evaluator.sh` | OKR-driven promote/degrade/disable feedback | Agent governance |
| PostToolUse | Agent | `auto-skill-generator.sh` | Auto-generate skills from complex completions | Skill lifecycle |
| PostToolUse | Agent | `architecture-compliance.sh` | Check Go architecture violations | Architecture enforcement |
| PostToolUse | Agent | `tool-loop-detector.sh` | Detect repetitive tool usage patterns | Loop prevention |
| PostToolUse | Agent | `skill-tracker.sh` | Track skill execution metrics and feedback | Skill observability |
| PostToolUse | Agent | `semgrep-scan.sh` | SAST scan on changed files after sdd-apply | Security scanning (external tool) |
| PostToolUse | Agent | `observability-trace.sh` | Send traces to Langfuse/Opik | Observability |
| PostToolUse | Agent | `notify.sh` | Notify on SDD phase completions | Communication |
| PostToolUse | Agent | `agent-checkpoint.sh` | Update task status in active-tasks.json | Task lifecycle |
| **Stop** | | | | |
| Stop | (all) | `session-learning.sh` | Capture session errors and patterns | Self-improvement |
| Stop | (all) | `kpi-trigger.sh` | Calculate KPI snapshot, check thresholds | Performance tracking |
| Stop | (all) | `task-recorder.sh` | Record task completion data for cost prediction | Cost prediction data |
| Stop | (all) | `conversation-capture.sh` | Capture session transcript | Conversation memory |
| Stop | (all) | `engram-auto-sync.sh` | Export Engram observations to git | Memory persistence |
| Stop | (all) | `session-state-save.sh` | Persist session state checkpoint | State recovery |
| Stop | (all) | `idle-service-cleanup.sh` | Stop idle Docker services | Resource cleanup |
| Stop | (all) | `session-cleanup.sh` | Merge metrics, release locks, clean up | Clean teardown |

### Hooks NOT included (even in paranoid)

These hooks are excluded because they serve niche use cases or require explicit opt-in:

| Hook | Why excluded |
|------|-------------|
| `mcp-scan.sh` | SessionStart -- requires mcp-scan installation, niche use case |
| `singularity-check.sh` | SessionStart -- OFF by default, requires SINGULARITY_CHECK=true |
| `agent-bus-monitor.sh` | SessionStart -- requires AGENT_BUS_ENABLED=true + Valkey |
| `metrics-calibrator-trigger.sh` | SessionStart -- internal optimization, not security-relevant |
| `tool-discovery-trigger.sh` | SessionStart -- internal optimization |
| `adaptive-bypass.sh` | PreToolUse Agent -- advisory complexity classification, orthogonal to security |
| `private-mode-gate.sh` | PreToolUse -- only relevant when private mode is active |
| `private-mode-metrics-gate.sh` | PostToolUse -- only relevant when private mode is active |
| `guardrails-validator.sh` | PostToolUse Agent -- requires GUARDRAILS_ENABLED=true + NeMo |
| `paperclip-sync.sh` | Stop -- requires Paperclip dashboard running |
| `memu-sync.sh` | Stop -- requires memU service running |
| `sync-to-repo.sh` | Stop -- syncs to dedicated repo, org-specific |
| `session-knowledge-extractor.sh` | Stop -- knowledge extraction, not security |
| `pre-commit-gate.sh` | Git pre-commit -- not a Claude hook, separate installation |

---

## Profile Comparison Matrix

| Hook | Minimal | Standard | Paranoid | Safety Mesh Layer |
|------|---------|----------|----------|-------------------|
| self-install.sh | Y | Y | Y | -- |
| session-init.sh | Y | Y | Y | -- |
| crash-recovery.sh | Y | Y | Y | -- |
| session-resume.sh | -- | -- | Y | -- |
| cognitive-os-health.sh | -- | -- | Y | -- |
| infra-health.sh | -- | -- | Y | -- |
| metrics-rotation.sh | -- | -- | Y | -- |
| engram-auto-import.sh | -- | -- | Y | -- |
| rate-limiter.sh | Y | Y | Y | Layer 4 |
| large-file-advisor.sh | -- | Y | Y | -- |
| clarification-gate.sh | -- | Y | Y | Layer 1 |
| blast-radius.sh | -- | Y | Y | Layer 2 |
| dry-run-preview.sh | -- | -- | Y | Layer 3 |
| aguara-scan.sh | -- | -- | Y | -- |
| error-pattern-detector.sh | -- | Y | Y | -- |
| completeness-check.sh | -- | -- | Y | -- |
| prompt-quality.sh | -- | -- | Y | -- |
| agent-prelaunch.sh | -- | -- | Y | -- |
| inject-phase-context.sh | -- | -- | Y | -- |
| contextual-rule-loader.sh | -- | -- | Y | -- |
| rate-limit-protection.sh | -- | -- | Y | -- |
| resource-check.sh | -- | -- | Y | -- |
| infra-intent-detector.sh | -- | -- | Y | -- |
| pre-cleanup-snapshot.sh | -- | -- | Y | -- |
| concurrent-write-guard.sh | -- | -- | Y | -- |
| jupyter-sandbox.sh | -- | -- | Y | -- |
| error-pipeline.sh | Y | Y | Y | -- |
| result-truncator.sh | -- | Y | Y | -- |
| auto-checkpoint.sh | Y | Y | Y | -- |
| secret-detector.sh | Y | Y | Y | -- |
| content-policy.sh | -- | Y | Y | -- |
| doc-sync-detector.sh | -- | Y | Y | -- |
| scope-creep-detector.sh | -- | -- | Y | -- |
| agnix-lint.sh | -- | -- | Y | -- |
| scope-proportionality.sh | -- | -- | Y | Layer 5 |
| claim-validator.sh | -- | Y | Y | Layer 6 |
| assumption-tracker.sh | -- | -- | Y | Layer 7 |
| trust-score-validator.sh | -- | -- | Y | Layer 8 |
| confidence-gate.sh | -- | -- | Y | Layer 9 |
| clarification-interceptor.sh | -- | Y | Y | Layer 10 |
| auto-rollback-trigger.sh | -- | -- | Y | Layer 11 |
| reinvention-check.sh | -- | -- | Y | Layer 13 |
| completion-gate.sh | -- | Y | Y | -- |
| consequence-evaluator.sh | -- | -- | Y | -- |
| auto-skill-generator.sh | -- | -- | Y | -- |
| architecture-compliance.sh | -- | -- | Y | -- |
| tool-loop-detector.sh | -- | -- | Y | -- |
| skill-tracker.sh | -- | -- | Y | -- |
| semgrep-scan.sh | -- | -- | Y | -- |
| observability-trace.sh | -- | -- | Y | -- |
| notify.sh | -- | -- | Y | -- |
| agent-checkpoint.sh | Y | Y | Y | -- |
| session-learning.sh | Y | Y | Y | -- |
| kpi-trigger.sh | -- | -- | Y | -- |
| task-recorder.sh | -- | -- | Y | -- |
| conversation-capture.sh | -- | -- | Y | -- |
| engram-auto-sync.sh | -- | -- | Y | -- |
| session-state-save.sh | -- | -- | Y | -- |
| idle-service-cleanup.sh | -- | -- | Y | -- |
| pre-compaction-flush.sh | Y | Y | Y | -- |
| subagent-context-injector.sh | -- | Y | Y | -- |
| user-prompt-capture.sh | -- | Y | Y | -- |
| teammate-idle.sh | -- | Y | Y | -- |
| task-created.sh | -- | Y | Y | -- |
| task-completed.sh | -- | Y | Y | -- |
| session-cleanup.sh | Y | Y | Y | -- |
| **Total** | **11** | **26** | **62** | |

---

## Switching Profiles

```bash
# Switch to minimal (fast iteration)
bash scripts/set-security-profile.sh minimal

# Switch to standard (recommended)
bash scripts/set-security-profile.sh standard

# Switch to paranoid (maximum security)
bash scripts/set-security-profile.sh paranoid

# Show current profile
bash scripts/set-security-profile.sh --current
```

The script backs up the current `settings.json` before overwriting and reports what changed.
