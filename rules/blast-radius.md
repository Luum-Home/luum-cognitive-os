<!-- SCOPE: both -->
# Blast Radius Estimation

## Purpose

Estimates the impact scope of agent tasks before execution. High blast radius tasks (many files, infrastructure, security) need extra caution, sampling, and review. This is an awareness tool — it does not block execution but ensures the orchestrator and user know the scope of what they are launching.

## How It Works

The `blast-radius.sh` PreToolUse hook fires on every Agent tool use and classifies the task's blast radius based on file scope, infrastructure impact, and security sensitivity.

### Classification

| Radius | File Score | Condition | Action |
|--------|-----------|-----------|--------|
| LOW | 1-5 | Small, well-scoped task | Silent. Logged only. |
| MEDIUM | 6-20 | Multi-file within a service | Silent. Logged only. |
| HIGH | 21-50 | Cross-service or bulk operation | Warning output with scope estimate. |
| CRITICAL | 50+ or infra/security | Large scope, infrastructure, or security-sensitive | Strong warning with recommendations. |

Infrastructure or security keywords automatically escalate to CRITICAL regardless of file score.

### Scoring Signals

| Signal | Points | Description |
|--------|--------|-------------|
| Explicit file paths | +1 per file | Count of unique file references (`.go`, `.ts`, `.py`, etc.) |
| Directory references | +5 per dir | Each directory reference implies ~5 files |
| Cross-service keywords | +50 | "all services", "every endpoint", "across the project" |
| Bulk operation keywords | +30 | "rebrand", "migrate all", "global replace", "bulk update" |
| Explicit count in prompt | uses count | If prompt says "47 endpoints", uses that number |

### Infrastructure Keywords

Detected keywords: `docker`, `docker-compose`, `container`, `kubernetes`, `deploy`, `pipeline`, `database`, `migration`, `schema`, `alter table`, `sql`

### Security Keywords

Detected keywords: `auth`, `authentication`, `authorization`, `permission`, `credential`, `secret`, `token`, `jwt`, `oauth`, `api key`, `password`, `encrypt`, `certificate`, `cors`, `csrf`, `rbac`, `acl`

## Examples

### LOW (1-5 files)
```
"Fix the typo in internal/users/domain/entities/user.go"
```
- 1 file path -> score 1 -> LOW (silent)

### MEDIUM (6-20 files)
```
"Refactor the DTOs in internal/orders/application/dtos/ to use the new naming convention"
```
- 1 directory reference -> score 5 -> MEDIUM (silent)

### HIGH (21-50 files)
```
"Update all controllers in internal/ to use the new error handling pattern.
There are 25 controller files."
```
- 1 directory + 25 explicit count -> score 25 -> HIGH (warning)

### CRITICAL (50+ or infra/security)
```
"Add JWT authentication across all services"
```
- Security keyword (jwt, authentication) -> CRITICAL regardless of file count

## Integration with Other Rules

| Rule | Relationship |
|------|-------------|
| Sandbox Sampling (`sandbox-sampling`) | HIGH/CRITICAL blast radius tasks should use `/sandbox-sample` |
| Epic Task Detector (`epic-task-detector`) | Complementary. Epic detector looks at scope language. Blast radius quantifies impact. |
| Clarification Gate (`clarification-gate`) | Blast radius runs alongside clarification. A task can be clear but have high blast radius. |
| Acceptance Criteria (`acceptance-criteria`) | HIGH/CRITICAL tasks especially need exhaustive acceptance criteria. |
| HALT Protocol (`closed-loop-prompts`) | CRITICAL blast radius aligns with HALT triggers for multi-service and security changes. |

## Metrics

Events are logged to `.cognitive-os/metrics/blast-radius.jsonl`:
```json
{
  "timestamp": "ISO-8601",
  "radius": "HIGH",
  "file_score": 35,
  "infra": false,
  "security": true,
  "signals": 3,
  "agent": "first 100 chars of prompt..."
}
```

Use these metrics to track the distribution of task sizes and identify patterns where HIGH/CRITICAL tasks are launched without adequate preparation.

## Contextual Trigger

This rule is always active. It applies to every agent launch via the PreToolUse hook.
