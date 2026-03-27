# Hooks — Runtime Interceptors

Hooks are shell scripts that fire at specific points in the Claude Code session lifecycle. They are configured in `.claude/settings.json` and live in `.claude/hooks/`.

## Summary

| Hook | File | Trigger | Matcher |
|------|------|---------|---------|
| Stack Detector | `stack-detector.sh` | SessionStart | (none) |
| Session Init | `session-init.sh` | SessionStart | (none) |
| Block Prod URLs | `block-prod-urls.sh` | PreToolUse | `Bash` |
| Concurrent Write Guard | `concurrent-write-guard.sh` | PreToolUse | `Edit\|Write` |
| Auto Test on Edit | `auto-test-on-edit.sh` | PostToolUse | `Edit\|Write` |
| Skill Feedback Tracker | `skill-feedback-tracker.sh` | PostToolUse | `Agent\|Skill` |
| Session Cleanup | `session-cleanup.sh` | Stop | (none) |
| Auto-Repair Dispatcher | `auto-repair-dispatcher.sh` | PostToolUse | `Bash` |
| Metrics Rotation | `metrics-rotation.sh` | SessionStart | (none) |
| Metrics Calibrator Trigger | `metrics-calibrator-trigger.sh` | SessionStart | (none) |
| Tool Discovery Trigger | `tool-discovery-trigger.sh` | SessionStart | (none) |
| Conversation Capture | `conversation-capture.sh` | Stop | (none) |
| Session Knowledge Extractor | `session-knowledge-extractor.sh` | Stop | (none) |

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

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/block-prod-urls.sh\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/auto-test-on-edit.sh\""
          }
        ]
      },
      {
        "matcher": "Agent|Skill",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/skill-feedback-tracker.sh\""
          }
        ]
      }
    ]
  }
}
```
