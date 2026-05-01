# Hooks — Runtime Interceptors

Hooks are shell scripts that fire at specific points in the Claude Code session lifecycle. They are configured in `.claude/settings.json` and live in `hooks/` (94 scripts total; 46 registered in `settings.json`).

## Summary

46 hooks are registered across 8 lifecycle events. The full hook scripts directory (`hooks/`) contains 94 scripts; the remainder load on-demand or are utility scripts.

### SessionStart (3)

| Hook | File | Purpose |
|------|------|---------|
| Self-Install | `self-install.sh` | Syncs core rule symlinks; framework auto-sync for self-hosted dev |
| Session Init | `session-init.sh` | Session ID, isolation, active-sessions.json |
| Crash Recovery | `crash-recovery.sh` | Detects orphaned checkpoint stashes from prior crashes |

### PreToolUse (9)

| Hook | File | Matcher | Purpose |
|------|------|---------|---------|
| Rate Limiter | `rate-limiter.sh` | `Bash\|Agent\|Edit\|Write` | Enforces per-minute/hour tool call limits |
| Release Guard | `release-guard.sh` | `Bash` | Blocks destructive commands in production |
| Large File Advisor | `large-file-advisor.sh` | `Read` | Advises on reads of files >40KB |
| Concurrent Write Guard | `concurrent-write-guard.sh` | `Edit\|Write` | Advisory file locking for multi-session |
| Clarification Gate | `clarification-gate.sh` | `Agent` | Blocks vague prompts (ambiguity score >60) |
| Blast Radius | `blast-radius.sh` | `Agent` | Estimates task scope before launch |
| Error Pattern Detector | `error-pattern-detector.sh` | `Agent` | Injects warnings when 3+ similar errors detected |
| Parry Scan | `parry-scan.sh` | `Agent` | ML-based prompt injection scanning |
| Aguara Scan | `aguara-scan.sh` | `Agent` | 189-rule deterministic security scan |

### PostToolUse (24)

| Hook | File | Matcher | Purpose |
|------|------|---------|---------|
| Error Pipeline | `error-pipeline.sh` | `Bash` | Captures test/lint/build failures |
| Result Truncator | `result-truncator.sh` | `Bash` | Truncates large command output (>5000 chars) |
| Tool Loop Detector | `tool-loop-detector.sh` | `Bash` | Detects repetitive tool-call loops |
| Secret Detector | `secret-detector.sh` | `Edit\|Write` | Scans written files for credential leaks |
| Content Policy | `content-policy.sh` | `Edit\|Write` | Enforces prohibited terms policy |
| Doc Sync Detector | `doc-sync-detector.sh` | `Edit\|Write` | Flags stale docs after code edits |
| Scope Creep Detector | `scope-creep-detector.sh` | `Edit\|Write` | Warns when edits fall outside approved task scope |
| Auto-Checkpoint | `auto-checkpoint.sh` | `Bash\|Edit\|Write` | Creates git stash every 5 min (WAL for crashes) |
| Claim Validator | `claim-validator.sh` | `Agent` | Validates agent file-creation claims against filesystem |
| Completion Gate | `completion-gate.sh` | `Agent` | Runs acceptance criteria commands on completion |
| Clarification Interceptor | `clarification-interceptor.sh` | `Agent` | Detects NEEDS_CLARIFICATION: markers |
| Agent Checkpoint | `agent-checkpoint.sh` | `Agent` | Marks tasks completed/failed in active-tasks.json |
| Auto-Skill Generator | `auto-skill-generator.sh` | `Agent` | Creates SKILL.md from complex completed tasks |
| Trust Score Validator | `trust-score-validator.sh` | `Agent` | Extracts and logs Trust Report scores |
| Confidence Gate | `confidence-gate.sh` | `Agent` | Blocks low-confidence results in production phase |
| Consequence Evaluator | `consequence-evaluator.sh` | `Agent` | OKR-driven consequence (promote/degrade/disable) |
| Scope Proportionality | `scope-proportionality.sh` | `Agent` | Detects disproportionate response scope |
| Assumption Tracker | `assumption-tracker.sh` | `Agent` | Counts assumption language in agent output |
| Skill Feedback Tracker | `skill-feedback-tracker.sh` | `Agent` | Tracks skill failures in Engram |
| **Auto-Refine** | `auto-refine.sh` | `Agent` | Auto-retry loop on failure (max 3 attempts) — **new in v0.4.0** |
| **Auto-Verify** | `auto-verify.sh` | `Agent` | Runs acceptance criteria commands after completion — **new in v0.4.0** |
| **DoD Gate** | `dod-gate.sh` | `Agent` | Enforces Definition of Done criteria — **new in v0.4.0** |
| **Auto-Repair Dispatcher** | `auto-repair-dispatcher.sh` | `Agent` | MAPE-K repair brain — dispatches fixes — **new in v0.4.0** |
| **Error Learning** | `error-learning.sh` | `Bash` | Error pattern accumulation and dedup — **new in v0.4.0** |

### Stop (5)

| Hook | File | Purpose |
|------|------|---------|
| Session Learning | `session-learning.sh` | Captures session errors, failed skills, iteration counts |
| Session Cleanup | `session-cleanup.sh` | Merges session metrics, deregisters session |
| Task Recorder | `task-recorder.sh` | Records completed task costs for cost prediction |
| Session State Save | `session-state-save.sh` | Persists session state to disk |
| KPI Trigger | `kpi-trigger.sh` | KPI snapshot and weekly self-improve flag |

### Other (4)

| Hook | File | Trigger | Purpose |
|------|------|---------|---------|
| Teammate Idle | `teammate-idle.sh` | TeammateIdle | Handles idle teammate notifications |
| Task Created | `task-created.sh` | TaskCreated | Registers newly created tasks |
| Task Completed | `task-completed.sh` | TaskCompleted | Records task completion events |
| Background Agent Reminder | `background-agent-reminder.sh` | UserPromptSubmit | Reminds about running background agents |
| User Prompt Capture | `user-prompt-capture.sh` | UserPromptSubmit | Captures actionable user prompts to Engram |

### New in v0.4.0

8 hooks were added in v0.4.0 to close the self-improvement loop:

| Hook | Trigger | Purpose |
|------|---------|---------|
| `auto-refine.sh` | PostToolUse (Agent) | Auto-retry loop: detects failures, retries up to 3 times |
| `auto-verify.sh` | PostToolUse (Agent) | Runs acceptance criteria verification commands post-completion |
| `dod-gate.sh` | PostToolUse (Agent) | Enforces complexity-appropriate Definition of Done |
| `error-learning.sh` | PostToolUse (Bash) | Accumulates and deduplicates error patterns to JSONL |
| `auto-repair-dispatcher.sh` | PostToolUse (Agent) | MAPE-K brain: classifies errors, dispatches worktree repairs |
| `skill-feedback-tracker.sh` | PostToolUse (Agent) | Saves skill failures to Engram for skill-adaptation loop |
| `parry-scan.sh` | PreToolUse (Agent) | ML-based prompt injection detection (DeBERTa) |
| `reinvention-check.sh` | PostToolUse (Agent) | Prevents re-inventing already-solved problems |

---

## 1. Stack Detector (`stack-detector.sh`)

**When**: Runs once at session start.

**What it does**: Scans the project directory for technology markers and generates `.claude/detected-stack.json`.

**Detection logic**:

| Technology | How Detected |
|------------|-------------|
| Node.js | `package.json` exists or `mobile/` directory |
| TypeScript | `tsconfig.json` found (max depth 3) |
| NestJS | `@nestjs/core` in any package.json |
| Express | `"express"` in any package.json |
| React Native / Expo | `react-native` or `expo` in `mobile/app/package.json` |
| Jest | `"jest"` in any package.json |
| Go | `go.mod` found (max depth 3) |
| Java / Spring Boot | `build.gradle` or `pom.xml` found; `spring-boot` in gradle files |
| Solidity / Hardhat | `hardhat.config.*` found |
| Docker | `docker-compose.yml` at root |
| MongoDB, MySQL, Redis, RabbitMQ | Referenced in `docker-compose*.yml` |
| Clean Architecture | `domain/` + `infrastructure/` or `usecases/` directories |
| WireMock, TestContainers | Referenced in `<consumer-service-5>` |

**Output**: JSON file at `.claude/detected-stack.json` with boolean flags per technology.

**How to modify**: Add new detection blocks following the existing pattern: check for files/patterns, set `DETECTED[key]=true`.

---

## 2. Block Production URLs (`block-prod-urls.sh`)

**When**: Before every Bash command execution (PreToolUse).

**What it does**: Inspects the command string for production domain patterns. If found, returns a JSON deny decision that blocks the command.

**Blocked patterns**:
- `example.com` (and `api.example.com`, `admin.example.com`)
- `prod.example.*`
- `production.example.*`
- `example.com.ar`

**Response on match**:
```json
{"decision": "deny", "reason": "Blocked: production URL detected. Use localhost for local development."}
```

**How to modify**: Edit the `grep -qiE` regex on line 14 to add/remove patterns.

---

## 3. Auto Test on Edit (`auto-test-on-edit.sh`)

**When**: After every Edit or Write tool use (PostToolUse).

**What it does**: Detects which service was affected by the file edit and runs (or suggests running) the appropriate tests.

**Behavior per service**:

| Service | Path Pattern | Action |
|---------|-------------|--------|
| <consumer-codename-b> | `<consumer-service-5><consumer-codename-b>/` | Reminder only (Java too slow for auto-run) |
| <consumer-codename-c> | `<consumer-service-5><consumer-codename-c>/` | Reminder only (Java too slow for auto-run) |
| onboarding | `<consumer-service-5>onboarding/` | `npx jest --changedSince=HEAD` |
| <consumer-codename-a> | `mobile/<consumer-codename-a>/` | `npx jest --changedSince=HEAD` |
| <consumer-service> | `services/<consumer-service>/` | `npx jest --changedSince=HEAD` |
| <consumer-service-2> | `wallet/<consumer-service-2>/` | `go test ./... -short` |
| mobile app | `mobile/app/` | Reminder only |

**Skipped files**: `.md`, `.json`, `.yml`, `.yaml`, `.env`, `.lock`, `.gitignore`

**How to modify**: Add new `elif` blocks matching file path patterns to service-specific test commands.

---

## 4. Skill Feedback Tracker (`skill-feedback-tracker.sh`)

**When**: After every Agent or Skill tool use (PostToolUse).

**What it does**: Reads the tool result via stdin (JSON). If the exit code is non-zero or the result contains error keywords, saves a feedback observation to Engram.

**Failure detection**:
1. Non-zero exit code
2. Result text contains: `error`, `failed`, `rejected`, `exception`, `timed out`, `permission denied`

**On failure**: POSTs to Engram HTTP API (`localhost:7437`) with:
- Title: `Skill feedback: {skill-name} failed`
- Type: `discovery`
- Topic key: `skill-feedback/{skill-name}`
- Content: skill name, failure reason, result excerpt (first 500 chars)

**Integration with skill-adaptation rule**: The `skill-adaptation.md` rule reads these Engram observations before running any skill. After 3+ failures for the same skill, it recommends running `/skill-creator` to rewrite the skill.

**How to modify**: Adjust the grep patterns for failure detection or change the Engram port via `ENGRAM_PORT` env var.

---

## Hook Configuration in settings.json

46 hooks are registered in `.claude/settings.json`. The structure groups hooks by lifecycle event and matcher. Example showing selected hooks:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/self-install.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/session-init.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/crash-recovery.sh\""}
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash|Agent|Edit|Write",
        "hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/rate-limiter.sh\""}]
      },
      {
        "matcher": "Agent",
        "hooks": [
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/clarification-gate.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/blast-radius.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/error-pattern-detector.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/parry-scan.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/aguara-scan.sh\""}
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/error-pipeline.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/error-learning.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/result-truncator.sh\""}
        ]
      },
      {
        "matcher": "Agent",
        "hooks": [
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/skill-feedback-tracker.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/auto-refine.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/auto-verify.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/dod-gate.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/auto-repair-dispatcher.sh\""}
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/session-cleanup.sh\""},
          {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/kpi-trigger.sh\""}
        ]
      }
    ]
  }
}
```

See `.claude/settings.json` for the complete 46-hook registration.

---

## Hook Composition (Inter-Hook Data Sharing)

Hooks within the same event chain can pass structured data to downstream hooks
via `hooks/_lib/hook-pipe.sh`. This enables context-aware decisions: for
example, `clarification-gate.sh` emits its ambiguity score so that
`blast-radius.sh` can lower its HIGH-radius threshold when the prompt is vague.

### Library: `hooks/_lib/hook-pipe.sh`

Source this library in any hook that needs to produce or consume pipe data:

```bash
source "$(dirname "$0")/_lib/hook-pipe.sh"
```

**Functions**:

| Function | Signature | Description |
|----------|-----------|-------------|
| `hook_emit` | `hook_emit <key> <value> [event]` | Write a value for downstream hooks in the same event |
| `hook_read` | `hook_read <key> [default] [event]` | Read a value emitted by a prior hook; returns default if absent |
| `hook_pipe_clear` | `hook_pipe_clear [event]` | Clear pipe values (all events, or a specific event) |

**Storage**: Values are written to `.cognitive-os/.hook-pipe/<event>-<key>.val`.
Each file holds one line (newlines in values are collapsed to spaces).

**Key naming**: Keys must match `^[a-zA-Z_][a-zA-Z0-9_]*$`. Use descriptive
names like `clarification_score`, `blast_radius_level`.

**Lifecycle**: Pipe files persist for the duration of the session. They are
NOT automatically cleared between invocations — hooks that need a clean slate
should call `hook_pipe_clear` at the start of each PreToolUse invocation.

### Active pipe data flows

| Producer | Key | Event | Consumer | Effect |
|----------|-----|-------|----------|--------|
| `clarification-gate.sh` | `clarification_score` | `PreToolUse` | `blast-radius.sh` | Lowers HIGH threshold from 40→20 when score ≥ 30 |

### Adding a new pipe data flow

1. In the producer hook, source hook-pipe.sh and call `hook_emit`:
   ```bash
   source "$(dirname "$0")/_lib/hook-pipe.sh"
   hook_emit "my_score" "$MY_SCORE" "PreToolUse"
   ```
2. In the consumer hook (must run after the producer), source and call `hook_read`:
   ```bash
   source "$(dirname "$0")/_lib/hook-pipe.sh"
   MY_SCORE=$(hook_read "my_score" "0" "PreToolUse")
   ```
3. Ensure the producer is registered before the consumer in `settings.json`.
4. Document the new flow in the table above.
